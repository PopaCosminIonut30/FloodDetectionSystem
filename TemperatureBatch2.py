import os
import cv2
import pandas as pd
import requests
import zipfile
import numpy as np
import scipy
import xarray as xr
from shapely.geometry import box
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import csv
import sys

sys.path.insert(0, '.venv/Final')
from Functions import compute_aoi
import h5py
import re
import datetime
import matplotlib.dates as mdates
import pyproj
from shapely.ops import transform as shapely_transform
from affine import Affine
from rasterio.windows import from_bounds
from shapely.geometry import Point
from matplotlib.path import Path

BASE_URL = "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json"
TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
DOWNLOAD_DIR = "./sentinel_data"
USERNAME = "vladkoblicica1@gmail.com"
PASSWORD = "CopernicusPassword1234!"
CLIENT_ID = "cdse-public"

DOWNLOAD_DIR = ".venv/Final/Temperatures/copernicus_temperature_data"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

start_date = "2024-05-01"
end_date = "2024-05-31"

center_lat, center_lon = 53.562762, 9.573723
side_length_m = 5000
aoi = compute_aoi(center_lon, center_lat, side_length_m)
aoi_wkt = aoi.wkt


def get_tokens():
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    response = requests.post(
        token_url,
        data={
            "client_id": CLIENT_ID,
            "username": USERNAME,
            "password": PASSWORD,
            "grant_type": "password"
        }
    )
    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"], token_data["refresh_token"]
    else:
        raise Exception("Failed to retrieve tokens:", response.status_code, response.text)


def refresh_access_token(refresh_token):
    token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    response = requests.post(
        token_url,
        data={
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception("Failed to refresh access token:", response.status_code, response.text)


access_token, refresh_token = get_tokens()
headers = {"Authorization": f"Bearer {access_token}"}

BASE_URL = "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel3/search.json"
query_params = {
    "startDate": start_date,
    "completionDate": end_date,
    "productType": "SL_2_LST___",
    "geometry": aoi_wkt,
    "maxRecords": 200,
}

response = requests.get(BASE_URL, params=query_params, headers=headers)
if response.status_code == 200:
    results = response.json()
    products = results.get("features", [])

    if products:
        print(f"Found {len(products)} LST products for the specified criteria.")
        for product in products:
            title = product["properties"]["title"]
            product_id = product["id"]
            download_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
            session = requests.Session()
            session.headers.update(headers)

            download_response = session.get(download_url, stream=True)
            if download_response.status_code == 401:
                access_token = refresh_access_token(refresh_token)
                session.headers.update({"Authorization": f"Bearer {access_token}"})
                download_response = session.get(download_url, stream=True)

            if download_response.status_code == 200:
                zip_file_path = os.path.join(DOWNLOAD_DIR, f"{title}.zip")
                if os.path.exists(zip_file_path):
                    print(f"📦 File {title}.zip already exists, skipping download.")
                else:
                    with open(zip_file_path, "wb") as file:
                        for chunk in download_response.iter_content(chunk_size=8192):
                            file.write(chunk)
                    extract_path = os.path.join(DOWNLOAD_DIR, title)
                    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_path)
                    print(f"Downloaded and extracted {title}.")
            else:
                print(f"Failed to download {title}. Status code: {download_response.status_code}")
    else:
        print("No products found for the specified criteria.")
else:
    print(f"Search request failed with status code: {response.status_code} and message: {response.text}")


def extract_date_time(folder_name):
    """Extract date and time from Sentinel-3 folder names."""
    match = re.search(r'(\d{8})T(\d{6})', folder_name)
    if match:
        date_raw = match.group(1)
        time_raw = match.group(2)

        date_formatted = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:8]}"  # YYYY-MM-DD
        time_formatted = f"{time_raw[:2]}:{time_raw[2:4]}:{time_raw[4:6]}"  # HH:MM:SS

        return date_formatted, time_formatted
    return None, None  # fallback if pattern not found


def dilate_cloud_mask(cloud_mask, dilation_pixels=7):
    """Expand cloud mask by a few pixels (to eliminate cloud edges)."""
    # Step 1: Binary dilation (logical)
    cloud_mask = scipy.ndimage.binary_dilation(cloud_mask != 0, iterations=dilation_pixels)
    cloud_mask = cloud_mask.astype(np.uint8)
    cloud_mask = cv2.dilate(cloud_mask, np.ones((3, 3), np.uint8), iterations=3)
    # ⚡ Step 4: Normalize back to 0–1 binary mask
    cloud_mask = np.where(cloud_mask > 0, 1, 0).astype(np.uint8)
    return cloud_mask


def get_flag(flag_ds, name, shape):
    """Safely get a cloud flag, fallback to zeros if not found."""
    if name in flag_ds.variables:
        return flag_ds[name].values
    else:
        return np.zeros(shape, dtype=np.uint8)


# Process downloaded NetCDF files
all_median_temperatures = []
all_clear_sky_percentages = []
all_dates = []
all_times = []
date_counter = {}

# Cloud-related flags to combine
CLOUD_FLAGS = [
    'cloud_in',
    'cloud_in_1_37_threshold',
    'cloud_in_1_6_small_histogram',
    'cloud_in_1_6_large_histogram',
    'cloud_in_2_25_small_histogram',
    'cloud_in_2_25_large_histogram',
    'cloud_in_11_spatial_coherence',
    'cloud_in_gross_cloud',
    'cloud_in_thin_cirrus',
    'cloud_in_medium_high',
    'cloud_in_fog_low_stratus',
    'cloud_in_11_12_view_difference',
    'cloud_in_3_7_11_view_difference',
    'cloud_in_thermal_histogram',
    'cloud_in_visible',
    'cloud_in_spare_1',
    'cloud_in_spare_2'
]


def combine_cloud_masks(flag_ds, shape):
    """Combine all relevant cloud masks into a single binary mask."""
    combined = np.zeros(shape, dtype=bool)
    for flag in CLOUD_FLAGS:
        if flag in flag_ds.variables:
            data = flag_ds[flag].values
            if data.shape == shape:
                combined |= (data != 0)
    return combined.astype(np.uint8)


def plot_cloud_and_lst(cloud_mask, lst_filtered, aoi, title_prefix=""):
    """Plot cloud mask and filtered LST side by side, overlaying AOI."""
    fig, axs = plt.subplots(1, 2, figsize=(14, 6))

    # Plot cloud mask
    axs[0].imshow(cloud_mask, cmap="gray", extent=[aoi.bounds[0], aoi.bounds[2], aoi.bounds[1], aoi.bounds[3]])
    axs[0].set_title("Cloud Mask")
    axs[0].set_xlabel('Longitude')
    axs[0].set_ylabel('Latitude')

    # Plot AOI rectangle
    rect = patches.Rectangle(
        (aoi.bounds[0], aoi.bounds[1]),
        aoi.bounds[2] - aoi.bounds[0],
        aoi.bounds[3] - aoi.bounds[1],
        linewidth=2,
        edgecolor='red',
        facecolor='none'
    )
    axs[0].add_patch(rect)

    # Plot LST
    im = axs[1].imshow(lst_filtered, cmap="inferno",
                       extent=[aoi.bounds[0], aoi.bounds[2], aoi.bounds[1], aoi.bounds[3]])
    axs[1].set_title("Filtered LST (°C)")
    axs[1].set_xlabel('Longitude')
    axs[1].set_ylabel('Latitude')

    # Also add AOI rectangle on LST plot
    rect2 = patches.Rectangle(
        (aoi.bounds[0], aoi.bounds[1]),
        aoi.bounds[2] - aoi.bounds[0],
        aoi.bounds[3] - aoi.bounds[1],
        linewidth=2,
        edgecolor='red',
        facecolor='none'
    )
    axs[1].add_patch(rect2)

    plt.colorbar(im, ax=axs[1], fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.show()


def fast_aoi_mask(lon, lat, aoi_polygon):
    """
    Fast AOI mask creation using matplotlib.path.Path.
    """
    poly_path = Path(aoi_polygon.exterior.coords)
    points = np.vstack((lon.ravel(), lat.ravel())).T
    mask_flat = poly_path.contains_points(points)
    return mask_flat.reshape(lon.shape)


h5_filename = f"LST_{start_date}_to_{end_date}_{center_lat:.5f}_{center_lon:.5f}.h5"
csv_filename = f"LST_{start_date}_to_{end_date}_{center_lat:.5f}_{center_lon:.5f}.csv"
h5_path = f".venv/Final/Temperatures/{h5_filename}"
csv_path = f".venv/Final/Temperatures/{csv_filename}"
hf = h5py.File(h5_path, "w")  # open outside loop

for root, _, files in os.walk(DOWNLOAD_DIR):
    if "LST_in.nc" in files and "flags_in.nc" in files:
        lst_path = os.path.join(root, "LST_in.nc")
        flags_path = os.path.join(root, "flags_in.nc")
        geo_path = os.path.join(root, "geodetic_in.nc")

        with xr.open_dataset(lst_path) as lst_ds, \
                xr.open_dataset(flags_path) as flag_ds, \
                xr.open_dataset(geo_path) as geo_ds:
            if 'LST' in lst_ds.variables and 'cloud_in' in flag_ds.variables:
                lst_full = lst_ds['LST'].values - 273.15
                shape = lst_full.shape

                lat = geo_ds['latitude_in'].values
                lon = geo_ds['longitude_in'].values

                aoi_mask = fast_aoi_mask(lon, lat, aoi)

                # === Combine all cloud flags ===
                combined_cloud = np.zeros(shape, dtype=bool)
                for flag in CLOUD_FLAGS:
                    if flag in flag_ds.variables:
                        flag_data = flag_ds[flag].values
                        combined_cloud |= (flag_data > 0)

                lst_cropped = np.where(aoi_mask, lst_full, np.nan)
                cloud_mask = np.where(aoi_mask, combined_cloud, 0).astype(np.uint8)

                # Continue as usual
                dilated = dilate_cloud_mask(cloud_mask, dilation_pixels=7)
                valid_mask = (dilated == 0)
                filtered = np.where(valid_mask, lst_cropped, np.nan)

                if np.isnan(filtered).all():
                    # print("⚠️ All values are NaN after masking — skipping.")
                    continue  # or handle this case differently
                else:
                    median_value = np.nanmedian(filtered)
                    filled = np.nan_to_num(filtered, nan=median_value)
                smoothed = scipy.ndimage.median_filter(filled, size=5)
                filtered_lst = np.where(np.isnan(filtered), np.nan, smoothed)

                clear_sky = 100 * np.sum(valid_mask) / valid_mask.size

                # plot_cloud_and_lst(cloud_mask, filtered_lst, aoi, title_prefix=os.path.basename(root))

                if clear_sky >= 1:
                    valid_temperatures = filtered_lst[~np.isnan(filtered_lst)]

                    if valid_temperatures.size > 0:
                        median_temperature = np.median(valid_temperatures)

                        raw_name = os.path.basename(root)
                        date_str, time_str = extract_date_time(raw_name)
                        if date_str is None or time_str is None:
                            print(f"⚠️ Failed to extract date/time from {raw_name}")
                            continue

                        group_name = f"{date_str},{time_str}"

                        group = hf.create_group(group_name)
                        group.create_dataset("LST", data=filtered_lst)
                        group.create_dataset("Median_Temperature", data=median_temperature)
                        group.create_dataset("Clear_Sky_Percentage", data=clear_sky)

                        all_dates.append(date_str)
                        all_times.append(time_str)
                        all_median_temperatures.append(median_temperature)
                        all_clear_sky_percentages.append(clear_sky)

                else:
                    print(f"⚠️ {root}: Skipped (Clear sky {clear_sky:.2f}%)")

hf.close()
print(f"✅ All results saved to {h5_path}")

# === Save to CSV ===
with open(csv_path, mode='w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Date", "Time", "Median_Temperature (°C)", "Clear_Sky_Percentage (%)"])

    for date, time, temp, clear_sky in zip(all_dates, all_times, all_median_temperatures, all_clear_sky_percentages):
        writer.writerow([date, time, temp, clear_sky])

print(f"✅ Summary saved to {csv_path}")

# Step 1: Build a DataFrame
df_plot = pd.DataFrame({
    "Date": all_dates,
    "MedianTemperature": all_median_temperatures
})

# Step 2: Group by date and average if multiple scans
df_plot = df_plot.groupby("Date").mean().reset_index()

# Step 3: Create a full calendar for the period
start = pd.to_datetime(min(all_dates))
end = pd.to_datetime(max(all_dates))
full_range = pd.date_range(start=start, end=end, freq='D')

# Step 4: Reindex to full calendar (NaN where no data)
df_plot['Date'] = pd.to_datetime(df_plot['Date'])
df_plot = df_plot.set_index('Date').reindex(full_range).rename_axis('Date').reset_index()

# Now df_plot has missing dates as NaN for MedianTemperature
plt.figure(figsize=(12, 6))
plt.plot(df_plot['Date'], df_plot['MedianTemperature'], marker='o', linestyle='-')

plt.title("Daily Median Land Surface Temperature")
plt.xlabel("Date")
plt.ylabel("Median LST (°C)")

plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))  # every 2 days
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.gcf().autofmt_xdate()  # Rotate date labels

plt.grid(True)
plt.tight_layout()
plt.show()

