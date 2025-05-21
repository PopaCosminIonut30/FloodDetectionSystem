import requests
import csv
import datetime
import os  
import cv2
import pandas as pd
import zipfile
import numpy as np
import scipy
import xarray as xr
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdates
from matplotlib.path import Path
from shapely.geometry import box
import csv
import sys
sys.path.insert(0, "C:/Users/popac/PycharmProjects/PythonProject1")
import h5py
import re
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import scipy.ndimage

def compute_aoi(center_lon, center_lat, side_length_m):
    """Compute the bounding box (AOI) around a central point with a given side length in meters."""
    half_side_m = side_length_m / 2  # Half of the total side length

    # Convert meters to degrees (approximate conversion)
    lat_offset = half_side_m / 111000  # 1 degree latitude ≈ 111 km
    lon_offset = half_side_m / (111000 * np.cos(np.radians(center_lat)))  # Adjust for Earth's curvature

    # Compute min/max longitude and latitude
    min_lon, max_lon = center_lon - lon_offset, center_lon + lon_offset
    min_lat, max_lat = center_lat - lat_offset, center_lat + lat_offset

    return box(min_lon, min_lat, max_lon, max_lat)  # Return bounding box
# Parameters
center_lat = 53.562762
center_lon = 9.573723
user_type = "tier3"
api_key = "JLXL9D6SF43DJ4QB6CRCYHBAH"
#api_key = "QZ86MFK3JA7LV9DTNSACGUQEY"

# # === Get start and end dates based on user type ===
if user_type == "tier1":
    end_date = datetime.datetime.today().strftime("%Y-%m-%d")
    start_date = datetime.timedelta(days = -90) +  datetime.datetime.today()
    start_date = start_date.strftime("%Y-%m-%d")
elif user_type == "tier2":
    end_date = datetime.datetime.today().strftime("%Y-%m-%d")
    start_date = datetime.timedelta(days = -365) +  datetime.datetime.today()
    start_date = start_date.strftime("%Y-%m-%d")
elif user_type == "tier3":
    start_date = input("Enter start date (YYYY-MM-DD): ")
    end_date = input("Enter end date (YYYY-MM-DD): ")
else:
    raise ValueError("Invalid user type. Must be 'tier1', 'tier2', or 'tier3'.")

def normalize_coords(lat, lon):
    return f"{float(lat):.5f}", f"{float(lon):.5f}"

def parse_csv_filename(filename):
    parts = filename.replace(".csv", "").split("_")
    start = pd.to_datetime(parts[1])
    end = pd.to_datetime(parts[3])
    lat = parts[4]
    lon = parts[5]
    return start, end, lat, lon

def find_covering_csv(start_date, end_date, lat, lon, directory):
    lat, lon = normalize_coords(lat, lon)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    covering_files = []

    for file in os.listdir(directory):
        if file.endswith(".csv") and "WeatherData" in file:
            try:
                s, e, f_lat, f_lon = parse_csv_filename(file)
                if f_lat == lat and f_lon == lon:
                    if (s <= start_date <= e) or (s <= end_date <= e) or (start_date <= s and end_date >= e):
                        covering_files.append((s, e, file))
            except Exception as ex:
                continue  # Skip malformed files

    return covering_files

def load_and_slice_csv(file_path, start_date, end_date):
    df = pd.read_csv(file_path, parse_dates=['datetime'])
    df = df[(df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))]
    return df


data_dir = "C:/Users/popac/PycharmProjects/PythonProject1"
lat, lon = normalize_coords(center_lat, center_lon)
covering_files = find_covering_csv(start_date, end_date, lat, lon, data_dir)

# === Construct file name dynamically ===
filename = f"WeatherData_{start_date}_to_{end_date}_{center_lat:.5f}_{center_lon:.5f}.csv"
csv_path = f"{data_dir}/{filename}"

if covering_files:
    # Pick the file with the widest coverage (or first match)
    covering_files.sort(key=lambda x: (x[0], -x[1].toordinal()))  # sort by start ASC, end DESC
    s, e, filename_existing = covering_files[0]
    full_path = os.path.join(data_dir, filename_existing)

    if s <= pd.to_datetime(start_date) and e >= pd.to_datetime(end_date):
        print("✅ Using cached data")
        df = load_and_slice_csv(full_path, start_date, end_date)
        df.to_csv(csv_path, index=False)
    else:
        print("🧩 Partial match – extracting missing dates")
        df_existing = pd.read_csv(full_path, parse_dates=['datetime'])

        # Determine missing date ranges
        missing_ranges = []
        if pd.to_datetime(start_date) < s:
            missing_ranges.append((start_date, s - pd.Timedelta(days=1)))
        if pd.to_datetime(end_date) > e:
            missing_ranges.append((e + pd.Timedelta(days=1), end_date))

        # Fetch only missing
        dfs = [df_existing[(df_existing['datetime'] >= pd.to_datetime(start_date)) & 
                           (df_existing['datetime'] <= pd.to_datetime(end_date))]]

        for r_start, r_end in missing_ranges:
            url = (
                f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
                f"{center_lat},{center_lon}/{r_start.strftime('%Y-%m-%d')}/{r_end.strftime('%Y-%m-%d')}?unitGroup=metric&include=days&key={api_key}&contentType=csv"
            )
            response = requests.get(url)
            if response.status_code != 200:
                print(f"❌ Failed API call for {r_start} to {r_end}")
                continue

            df_new = pd.read_csv(pd.compat.StringIO(response.text), parse_dates=['datetime'])
            dfs.append(df_new)

        df_final = pd.concat(dfs).sort_values("datetime")
        df_final.to_csv(csv_path, index=False)
        print(f"✅ Saved combined data to {csv_path}")
else:
    print("📡 No local match — fetching full range from API")
    url = (
    f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
    f"{center_lat},{center_lon}/{start_date}/{end_date}?unitGroup=metric&include=days&key={api_key}&contentType=csv"
    )
    # Fetch data
    response = requests.get(url)
    if response.status_code != 200:
        print("❌ Failed:", response.status_code)
        sys.exit()

    # Save to CSV
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in csv.reader(response.text.splitlines(), delimiter=',', quotechar='"'):
            writer.writerow(row)
    print(f"✅ Weather data saved to '{filename}'")


# Batch process Sentinel-3 data  
#############################################################################################################################################
if user_type == "tier3":
    def generate_may_september_intervals(start_date, end_date):
        intervals = []
        start_year = start_date.year
        end_year = end_date.year

        for year in range(start_year, end_year + 1):
            interval_start = pd.Timestamp(year=year, month=5, day=1)
            interval_end = pd.Timestamp(year=year, month=9, day=30)

            # Clip the interval inside user-specified range
            if interval_start < start_date:
                interval_start = start_date
            if interval_end > end_date:
                interval_end = end_date

            if interval_start <= interval_end:
                intervals.append((interval_start, interval_end))
        
        return intervals
    
    
    def find_existing_h5_files(data_dir=".venv/Final/Temperatures"):
        existing_files = []
        for file in os.listdir(data_dir):
            if file.endswith(".h5") and "LST" in file:
                match = re.match(r"LST_(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})_.*\.h5", file)
                if match:
                    file_start = pd.to_datetime(match.group(1))
                    file_end = pd.to_datetime(match.group(2))
                    existing_files.append((file_start, file_end, os.path.join(data_dir, file)))
        return existing_files


    def copy_existing_data(existing_h5_paths, intervals, target_h5_path):
        copied_dates = set()
        with h5py.File(target_h5_path, "a") as target_hf:
            for file_start, file_end, file_path in existing_h5_paths:
                with h5py.File(file_path, "r") as source_hf:
                    for key in source_hf.keys():
                        date_str, _ = key.split(",")
                        date_obj = pd.to_datetime(date_str)

                        for interval_start, interval_end in intervals:
                            if interval_start <= date_obj <= interval_end and key not in target_hf:
                                source_hf.copy(key, target_hf)
                                copied_dates.add(date_obj)

        return copied_dates

    #######################################################################
    # 2. Token Management
    #######################################################################    
    BASE_URL = "https://catalogue.dataspace.copernicus.eu/resto/api/collections/Sentinel2/search.json"
    TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    USERNAME = "vladkoblicica1@gmail.com"
    PASSWORD = "CopernicusPassword1234!"
    CLIENT_ID = "cdse-public"

    DOWNLOAD_DIR = ".venv/Final/Temperatures/copernicus_temperature_data"
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

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

    def get_tokens():
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "username": USERNAME,
                "password": PASSWORD,
                "grant_type": "password"
            }
        )
        if response.status_code == 200:
            tokens = response.json()
            return tokens["access_token"], tokens["refresh_token"]
        else:
            raise Exception("Failed to get tokens", response.text)

    def refresh_access_token(refresh_token):
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            raise Exception("Failed to refresh token", response.text)

    #######################################################################
    # 3. LST Data Download (for missing dates)
    #######################################################################

    def download_lst_data(interval_start, interval_end, aoi_wkt, access_token):
        headers = {"Authorization": f"Bearer {access_token}"}
        query_params = {
            "startDate": interval_start.strftime("%Y-%m-%d"),
            "completionDate": interval_end.strftime("%Y-%m-%d"),
            "productType": "SL_2_LST___",
            "geometry": aoi_wkt,
            "maxRecords": 2000,
        }
        response = requests.get(BASE_URL, params=query_params, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to query Sentinel-3 API: {response.text}")
        
        products = response.json().get("features", [])
        print(f"🛰 Found {len(products)} products for {interval_start.strftime('%Y-%m-%d')} to {interval_end.strftime('%Y-%m-%d')}")
        
        session = requests.Session()
        session.headers.update(headers)
        
        for product in products:
            title = product["properties"]["title"]
            product_id = product["id"]
            download_url = f"https://download.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"

            zip_file_path = os.path.join(DOWNLOAD_DIR, f"{title}.zip")
            if os.path.exists(zip_file_path):
                print(f"📦 {title} already downloaded.")
                continue
            
            download_response = session.get(download_url, stream=True)
            if download_response.status_code == 401:
                access_token = refresh_access_token(access_token)
                session.headers.update({"Authorization": f"Bearer {access_token}"})
                download_response = session.get(download_url, stream=True)

            if download_response.status_code == 200:
                with open(zip_file_path, "wb") as f:
                    for chunk in download_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ Downloaded {title}.")
                with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                    zip_ref.extractall(os.path.join(DOWNLOAD_DIR, title))
            else:
                print(f"❌ Failed to download {title}: {download_response.status_code}")

    #######################################################################
    # 4. Full Processing Pipeline
    #######################################################################
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
        
    def combine_cloud_masks(flag_ds, shape):
        """Combine all relevant cloud masks into a single binary mask."""
        combined = np.zeros(shape, dtype=bool)
        for flag in CLOUD_FLAGS:
            if flag in flag_ds.variables:
                data = flag_ds[flag].values
                if data.shape == shape:
                    combined |= (data != 0)
        return combined.astype(np.uint8)
        
    def fast_aoi_mask(lon, lat, aoi_polygon):
        """
        Fast AOI mask creation using matplotlib.path.Path.
        """
        poly_path = Path(aoi_polygon.exterior.coords)
        points = np.vstack((lon.ravel(), lat.ravel())).T
        mask_flat = poly_path.contains_points(points)
        return mask_flat.reshape(lon.shape)
        
    def process_downloaded_lst_files(h5_save_path, csv_save_path, download_dir, aoi, center_lat, center_lon, start_date, end_date):
        
        all_median_temperatures = []
        all_clear_sky_percentages = []
        all_dates = []
        all_times = []

        hf = h5py.File(h5_save_path, "a")  # a = append mode

        for root, _, files in os.walk(download_dir):
            if "LST_in.nc" in files and "flags_in.nc" in files:
                lst_path = os.path.join(root, "LST_in.nc")
                flags_path = os.path.join(root, "flags_in.nc")
                geo_path = os.path.join(root, "geodetic_in.nc")

                with xr.open_dataset(lst_path) as lst_ds, xr.open_dataset(flags_path) as flag_ds, xr.open_dataset(geo_path) as geo_ds:
                    if 'LST' in lst_ds.variables and 'cloud_in' in flag_ds.variables:
                        lst_full = lst_ds['LST'].values - 273.15
                        shape = lst_full.shape
                        lat = geo_ds['latitude_in'].values
                        lon = geo_ds['longitude_in'].values
                        aoi_mask = fast_aoi_mask(lon, lat, aoi)

                        combined_cloud = np.zeros(shape, dtype=bool)
                        for flag in CLOUD_FLAGS:
                            if flag in flag_ds.variables:
                                data = flag_ds[flag].values
                                if data.shape == shape:
                                    combined_cloud |= (data != 0)

                        lst_cropped = np.where(aoi_mask, lst_full, np.nan)
                        cloud_mask = np.where(aoi_mask, combined_cloud, 0).astype(np.uint8)
                        dilated = dilate_cloud_mask(cloud_mask, dilation_pixels=7)
                        valid_mask = (dilated == 0)
                        filtered = np.where(valid_mask, lst_cropped, np.nan)

                        if np.isnan(filtered).all():
                            continue

                        median_value = np.nanmedian(filtered)
                        filled = np.nan_to_num(filtered, nan=median_value)
                        smoothed = scipy.ndimage.median_filter(filled, size=5)
                        filtered_lst = np.where(np.isnan(filtered), np.nan, smoothed)

                        clear_sky = 100 * np.sum(valid_mask) / valid_mask.size
                        if clear_sky >= 1:
                            valid_temperatures = filtered_lst[~np.isnan(filtered_lst)]

                            if valid_temperatures.size > 0:
                                median_temperature = np.median(valid_temperatures)

                                raw_name = os.path.basename(root)
                                date_str, time_str = extract_date_time(raw_name)
                                if date_str is None or time_str is None:
                                    continue

                                group_name = f"{date_str},{time_str}"
                                if group_name not in hf:
                                    group = hf.create_group(group_name)
                                    group.create_dataset("Median_Temperature", data=median_temperature)

                                    all_dates.append(date_str)
                                    all_times.append(time_str)
                                    all_median_temperatures.append(median_temperature)

        hf.close()

        # === Save CSV summary ===
        with open(csv_save_path, mode='w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Time", "Median_Temperature (°C)"])
            for date, time, temp in zip(all_dates, all_times, all_median_temperatures):
                writer.writerow([date, time, temp])

        print(f"✅ Final LST saved to {h5_save_path} and summary to {csv_save_path}")

    
    def full_lst_processing_pipeline(start_date, end_date, center_lat, center_lon, user_type="tier3"):
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        intervals = generate_may_september_intervals(start_date, end_date)
        print(f"📅 Target intervals: {[ (s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')) for s,e in intervals]}")

        aoi = compute_aoi(center_lon, center_lat, 5000)
        aoi_wkt = aoi.wkt

        # Create new h5 file
        LST_filename = f"LST_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}_{center_lat:.5f}_{center_lon:.5f}.h5"
        target_h5_path = os.path.join(data_dir, LST_filename)

        existing_h5_files = find_existing_h5_files()
        copied_dates = copy_existing_data(existing_h5_files, intervals, target_h5_path)
        print(f"✅ Copied {len(copied_dates)} dates from existing files.")

        access_token, refresh_token = get_tokens()

        for interval_start, interval_end in intervals:
            download_lst_data(interval_start, interval_end, aoi_wkt, access_token)
            
        process_downloaded_lst_files(
            h5_save_path=target_h5_path,
            csv_save_path=target_h5_path.replace(".h5", ".csv"),
            download_dir=DOWNLOAD_DIR,
            aoi=aoi,
            center_lat=center_lat,
            center_lon=center_lon,
            start_date=start_date,
            end_date=end_date
        )    

        return target_h5_path
    
# Graphs and Analysis
# Functions
#############################################################################################################################################
def plot_min_temps(df, start_date, end_date):
    df['datetime'] = pd.to_datetime(df['datetime'])
    sub_df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub_df['datetime'], y=sub_df['tempmin'], mode='lines+markers',
        name='Min Temp (°C)'
    ))

    fig.update_layout(
        title=f"Minimum Daily Temperatures ({start_date} to {end_date})",
        xaxis_title="Date",
        yaxis_title="Temperature (°C)",
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    fig.show()
    

def plot_max_temps(df, start_date, end_date):
    df['datetime'] = pd.to_datetime(df['datetime'])
    sub_df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sub_df['datetime'], y=sub_df['tempmax'], mode='lines+markers',
        name='Max Temp (°C)', line=dict(color='tomato')
    ))

    fig.update_layout(
        title=f"Maximum Daily Temperatures ({start_date} to {end_date})",
        xaxis_title="Date",
        yaxis_title="Temperature (°C)",
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    fig.show()
 
 
def plot_min_max_temps_overlayed(df, start_date, end_date):
    df['datetime'] = pd.to_datetime(df['datetime'])
    sub_df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sub_df['datetime'], y=sub_df['tempmin'],
                             mode='lines+markers', name='Min Temp (°C)', line=dict(color='dodgerblue')))
    fig.add_trace(go.Scatter(x=sub_df['datetime'], y=sub_df['tempmax'],
                             mode='lines+markers', name='Max Temp (°C)', line=dict(color='tomato')))

    fig.update_layout(
        title=f"Min & Max Daily Temperatures ({start_date} to {end_date})",
        xaxis_title="Date",
        yaxis_title="Temperature (°C)",
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    fig.show()
 
 
def rainy_days_per_month(df, start_date, end_date):
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df["month"] = df["datetime"].dt.to_period("M")
    df["rainy"] = df["precipprob"] > 0
    filtered = df[(df["datetime"] >= start_date) & (df["datetime"] <= end_date)]
    rainy_counts = filtered.groupby("month")["rainy"].sum()

    fig = px.bar(
        x=rainy_counts.index.astype(str),
        y=rainy_counts.values,
        labels={"x": "Month", "y": "Rainy Days"},
        title="Number of Rainy Days Per Month"
    )
    fig.show()


def rain_hours_per_day(df, start_date, end_date):
    df['datetime'] = pd.to_datetime(df['datetime'])
    sub_df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].copy()
    sub_df['rain_hours'] = (sub_df['precipcover'] / 100) * 24

    fig = px.bar(
        sub_df, x='datetime', y='rain_hours',
        labels={"datetime": "Date", "rain_hours": "Rain Hours"},
        title=f"Estimated Rain Hours per Day ({start_date} to {end_date})"
    )
    fig.show()
  
  
def total_rain_and_coverage(df, start_date, end_date):
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    mask = (df['datetime'] >= start_date) & (df['datetime'] <= end_date)
    sub_df = df.loc[mask]

    if sub_df.empty:
        print(f"No data available between {start_date} and {end_date}.")
        return

    max_precip = sub_df['precip'].max()
    max_precip_date = sub_df[sub_df['precip'] == max_precip]['datetime'].iloc[0]
    avg_precipcover = sub_df['precipcover'].mean()

    print(f"📦 Max daily rainfall: {max_precip:.2f} mm/m² on {max_precip_date.date()}")
    print(f"☔ Avg rain coverage: {avg_precipcover:.2f}%")


def longest_dry_streak(df, start_date, end_date):
    df['datetime'] = pd.to_datetime(df['datetime'])
    mask = (df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))
    sub_df = df.loc[mask].sort_values('datetime').copy()

    is_dry = sub_df['precip'] == 0

    max_streak = 0
    current_streak = 0
    start_streak_date = None
    longest_range = (None, None)

    for i, dry in enumerate(is_dry):
        if dry:
            if current_streak == 0:
                temp_start = sub_df.iloc[i]['datetime']
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
                longest_range = (temp_start, sub_df.iloc[i]['datetime'])
        else:
            current_streak = 0

    if longest_range[0]:
        print(f"🌵 Longest dry streak: {max_streak} days")
        print(f"📆 From {longest_range[0].date()} to {longest_range[1].date()}")
    else:
        print("No dry streak found.")
    
        
def longest_dry_streak(df, start_date, end_date):
    df['datetime'] = pd.to_datetime(df['datetime'])
    mask = (df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))
    sub_df = df.loc[mask].sort_values('datetime').copy()

    is_dry = sub_df['precip'] == 0

    max_streak = 0
    current_streak = 0
    start_streak_date = None
    longest_range = (None, None)

    for i, dry in enumerate(is_dry):
        if dry:
            if current_streak == 0:
                temp_start = sub_df.iloc[i]['datetime']
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
                longest_range = (temp_start, sub_df.iloc[i]['datetime'])
        else:
            current_streak = 0

    if longest_range[0] is not None:
        print(f"🌵 Longest dry streak: {max_streak} days")
        print(f"📆 From {longest_range[0].date()} to {longest_range[1].date()}")
    else:
        print("No dry streak found in the selected period.")
    
    
def compare_years(df):
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['year'] = df['datetime'].dt.year.astype(str)  # Use string years for better x-axis

    yearly_summary = df.groupby('year').agg(
        avg_min_temp=('tempmin', 'mean'),
        avg_max_temp=('tempmax', 'mean'),
        min_temp=('tempmin', 'min'),
        max_temp=('tempmax', 'max'),
        rainy_days=('precip', lambda x: (x > 0).sum())
    ).reset_index()

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.15,
        subplot_titles=("Temperature Statistics", "Rainy Days")
    )

    # --- Temperature bars ---
    metrics = ['avg_min_temp', 'avg_max_temp', 'min_temp', 'max_temp']
    colors = ['royalblue', 'orangered', 'mediumvioletred', 'darkorange']
    names = ['Avg Min Temp', 'Avg Max Temp', 'Min Temp', 'Max Temp']

    for metric, color, name in zip(metrics, colors, names):
        fig.add_trace(go.Bar(
            x=yearly_summary['year'],
            y=yearly_summary[metric],
            name=name,
            marker_color=color,
            text=yearly_summary[metric].round(1),
            textposition='outside'
        ), row=1, col=1)

    # --- Rainy days bar ---
    fig.add_trace(go.Bar(
        x=yearly_summary['year'],
        y=yearly_summary['rainy_days'],
        name='Rainy Days',
        marker_color='skyblue',
        text=yearly_summary['rainy_days'],
        textposition='outside'
    ), row=2, col=1)

    # Layout & style
    fig.update_layout(
        title="Yearly Weather Statistics Comparison",
        barmode='group',
        height=700,
        template="plotly_white",
        legend_title="Metrics",
        uniformtext_minsize=8,
        uniformtext_mode='show'
    )

    fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
    fig.update_yaxes(title_text="Rainy Days", row=2, col=1)

    fig.update_traces(cliponaxis=False)

    fig.show()
    
    
def compare_months(df, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Filter the date range
    mask = (df['datetime'] >= start_date) & (df['datetime'] <= end_date)
    df = df.loc[mask]

    # Create a label like "Oct 2023", "Jan 2024", etc.
    df['month_label'] = df['datetime'].dt.strftime('%b %Y')
    df['month_sort'] = df['datetime'].dt.to_period('M')  # for sorting

    # Group by month label
    monthly_summary = df.groupby(['month_label', 'month_sort']).agg(
        avg_min_temp=('tempmin', 'mean'),
        avg_max_temp=('tempmax', 'mean'),
        min_temp=('tempmin', 'min'),
        max_temp=('tempmax', 'max'),
        rainy_days=('precip', lambda x: (x > 0).sum())
    ).reset_index().sort_values('month_sort')

    fig = make_subplots(rows=2, cols=3, subplot_titles=[
        "Average Min Temp", "Average Max Temp", "Rainy Days",
        "Minimum Temp", "Maximum Temp", ""
    ])

    months = monthly_summary['month_label']

    fig.add_trace(go.Bar(x=months, y=monthly_summary['avg_min_temp'], name="Avg Min Temp"), row=1, col=1)
    fig.add_trace(go.Bar(x=months, y=monthly_summary['avg_max_temp'], name="Avg Max Temp"), row=1, col=2)
    fig.add_trace(go.Bar(x=months, y=monthly_summary['rainy_days'], name="Rainy Days"), row=1, col=3)

    fig.add_trace(go.Bar(x=months, y=monthly_summary['min_temp'], name="Min Temp"), row=2, col=1)
    fig.add_trace(go.Bar(x=months, y=monthly_summary['max_temp'], name="Max Temp"), row=2, col=2)

    fig.update_layout(
        title=f"Monthly Weather Statistics from {start_date.strftime('%b %Y')} to {end_date.strftime('%b %Y')}",
        barmode="group",
        template="plotly_white",
        height=600
    )
    fig.show()
 
 
def compare_months_for_each_year(df, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    for year in range(start_date.year, end_date.year + 1):
        year_start = pd.Timestamp(f"{year}-01-01")
        year_end = pd.Timestamp(f"{year}-12-31")

        # Limit to valid range
        year_start = max(year_start, start_date)
        year_end = min(year_end, end_date)

        compare_months(df, year_start, year_end)
 
def generate_may_september_intervals_2(start_date, end_date):
        intervals = []
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        start_year = start_date.year
        end_year = end_date.year
        for year in range(start_year, end_year + 1):
            interval_start = pd.Timestamp(year=year, month=5, day=1)
            interval_end = pd.Timestamp(year=year, month=9, day=30)
            if interval_start < start_date:
                interval_start = start_date
            if interval_end > end_date:
                interval_end = end_date
            if interval_start <= interval_end:
                intervals.append((interval_start, interval_end))
        return intervals
     
def plot_land_surface_temperature(csv_path, h5_path, start_date, end_date):
    weather_df = pd.read_csv(csv_path, parse_dates=["datetime"])
    weather_df["date"] = weather_df["datetime"].dt.date

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    intervals = generate_may_september_intervals_2(start_date, end_date)

    temp_lookup = weather_df.groupby("date")[["tempmin", "tempmax"]].mean().to_dict("index")

    daily_surface_temps = {}
    with h5py.File(h5_path, "r") as h5_file:
        for key in h5_file.keys():
            try:
                date_str, time_str = key.split(",")
                date_obj = pd.to_datetime(date_str)
                if any(interval_start <= date_obj <= interval_end for interval_start, interval_end in intervals):
                    if date_obj.date() not in temp_lookup:
                        continue
                    h5_temp = h5_file[key]["Median_Temperature"][()]
                    daily_surface_temps.setdefault(date_obj.date(), []).append(h5_temp)
            except Exception:
                continue

    all_dates = []
    for interval_start, interval_end in intervals:
        dates = pd.date_range(start=interval_start, end=interval_end, freq="D")
        all_dates.extend(dates.date)

    final_temps = []
    for date in all_dates:
        temp_data = temp_lookup.get(date)
        if not temp_data:
            final_temps.append(None)
            continue

        tempmin = temp_data["tempmin"]
        tempmax = temp_data["tempmax"]
        avg_air_temp = (tempmin + tempmax) / 2

        if date in daily_surface_temps and daily_surface_temps[date]:
            mean_lst = sum(daily_surface_temps[date]) / len(daily_surface_temps[date])
            if mean_lst >= tempmin:
                final_temps.append(mean_lst)
            else:
                final_temps.append(avg_air_temp)
        else:
            final_temps.append(avg_air_temp)

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(all_dates),
        y=final_temps,
        mode='lines+markers',
        line=dict(color='orange'),
        name='Surface Temp (°C)'
    ))

    fig.update_layout(
        title="Daily Surface Temperature Variation (May–September only)",
        xaxis_title="Date",
        yaxis_title="Surface Temperature (°C)",
        xaxis=dict(tickangle=45),
        template="plotly_white"
    )
    fig.show()


def compare_surface_and_air_temperatures(csv_path, h5_path, start_date, end_date):
    # Load air temperature data
    weather_df = pd.read_csv(csv_path, parse_dates=["datetime"])
    weather_df["date"] = weather_df["datetime"].dt.date

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    intervals = generate_may_september_intervals_2(start_date, end_date)

    temp_lookup = weather_df.groupby("date")[["tempmin", "tempmax"]].mean().to_dict("index")

    daily_surface_temps = {}
    with h5py.File(h5_path, "r") as h5_file:
        for key in h5_file.keys():
            try:
                date_str, _ = key.split(",")
                date_obj = pd.to_datetime(date_str)
                if any(interval_start <= date_obj <= interval_end for interval_start, interval_end in intervals):
                    h5_temp = h5_file[key]["Median_Temperature"][()]
                    daily_surface_temps.setdefault(date_obj.date(), []).append(h5_temp)
            except Exception:
                continue

    all_dates = []
    for interval_start, interval_end in intervals:
        dates = pd.date_range(start=interval_start, end=interval_end, freq="D")
        all_dates.extend(dates.date)

    daily_min = []
    daily_max = []
    final_surface_temps = []

    for date in all_dates:
        temp_data = temp_lookup.get(date)
        if not temp_data:
            # No air temp data -> fallback None
            daily_min.append(None)
            daily_max.append(None)
            final_surface_temps.append(None)
            continue

        tempmin = temp_data["tempmin"]
        tempmax = temp_data["tempmax"]
        avg_air_temp = (tempmin + tempmax) / 2

        daily_min.append(tempmin)
        daily_max.append(tempmax)

        # Apply fallback logic
        if date in daily_surface_temps and daily_surface_temps[date]:
            mean_lst = sum(daily_surface_temps[date]) / len(daily_surface_temps[date])
            if mean_lst >= tempmin:
                final_surface_temps.append(mean_lst)
            else:
                final_surface_temps.append(avg_air_temp)
        else:
            final_surface_temps.append(avg_air_temp)

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=all_dates, y=daily_min, mode='lines+markers', name="Min Temp (°C)", line=dict(color="skyblue")))
    fig.add_trace(go.Scatter(x=all_dates, y=daily_max, mode='lines+markers', name="Max Temp (°C)", line=dict(color="tomato")))
    fig.add_trace(go.Scatter(x=all_dates, y=final_surface_temps, mode='lines+markers', name="Surface Temp (LST °C)", line=dict(color="black")))

    fig.update_layout(
        title="Comparison of Air and Surface Temperatures (May–September only)",
        xaxis_title="Date",
        yaxis_title="Temperature (°C)",
        xaxis=dict(tickangle=45),
        template="plotly_white",
        height=500
    )
    fig.show()
    
# Implementation
#############################################################################################################################################    

filename1 = f"WeatherData_{start_date}_to_{end_date}_{center_lat:.5f}_{center_lon:.5f}.csv"
weather_csv_path1 = f"C:/Users/popac/PycharmProjects/PythonProject1/{filename1}"
df1 = pd.read_csv(weather_csv_path1, parse_dates=["datetime"])

# Graphs
plot_min_temps(df1, start_date, end_date)
plot_min_max_temps_overlayed(df1, start_date, end_date)
rainy_days_per_month(df1, start_date, end_date)
rain_hours_per_day(df1, start_date, end_date)
total_rain_and_coverage(df1, start_date, end_date)
longest_dry_streak(df1, start_date, end_date)

if user_type == "tier2" or user_type == "tier3":
  compare_months(df1, start_date, end_date)
  
if user_type == "tier3":
    combined_h5_path = full_lst_processing_pipeline(start_date, end_date, center_lat, center_lon)
    
    plot_land_surface_temperature(weather_csv_path1, combined_h5_path, start_date, end_date)
    compare_surface_and_air_temperatures(weather_csv_path1, combined_h5_path, start_date, end_date)
    compare_months_for_each_year(df1, start_date, end_date)

