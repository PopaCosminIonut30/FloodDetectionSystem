import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import os
import h5py
import re
import random


def get_data_file_paths(lat, lon, start_date, end_date):
    """
    Returns file paths for weather data and LST data for the Hamburg location.

    Since we're focusing specifically on the one location with prepared data,
    this function hardcodes the paths to make it easier to find the files.
    """
    # Format coordinates for filename pattern matching
    normalized_lat = f"{float(lat):.5f}"
    normalized_lon = f"{float(lon):.5f}"

    # Hardcoded filenames for the Hamburg location
    weather_csv = f"WeatherData_20230101_to_20241231_{normalized_lat}_{normalized_lon}.csv"
    lst_h5 = f"LST_2024-05-01_to_2024-09-30_{normalized_lat}_{normalized_lon}.h5"

    # Possible locations to look for the files
    possible_dirs = [
        ".",  # Current directory
        "./data",  # Data subdirectory
        os.path.dirname(os.path.abspath(__file__)),  # Script directory
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")  # Script data subdirectory
    ]

    # Look for the CSV file
    weather_csv_path = None
    for directory in possible_dirs:
        test_path = os.path.join(directory, weather_csv)
        if os.path.exists(test_path):
            weather_csv_path = test_path
            break

    # Look for the H5 file
    lst_h5_path = None
    for directory in possible_dirs:
        test_path = os.path.join(directory, lst_h5)
        if os.path.exists(test_path):
            lst_h5_path = test_path
            break

    return weather_csv_path, lst_h5_path


def load_weather_data(lat, lon, start_date, end_date, data_dir="."):
    """
    Load weather data from CSV file for the given coordinates and date range.
    Falls back to mock data if real data is not available.
    """
    # For Hamburg location, use the get_data_file_paths function
    if abs(float(lat) - 53.562762) < 0.001 and abs(float(lon) - 9.573723) < 0.001:
        weather_csv_path, _ = get_data_file_paths(lat, lon, start_date, end_date)

        if weather_csv_path and os.path.exists(weather_csv_path):
            # Load the file and filter to the requested date range
            df = pd.read_csv(weather_csv_path, parse_dates=['datetime'])
            df = df[(df['datetime'] >= pd.to_datetime(start_date)) &
                    (df['datetime'] <= pd.to_datetime(end_date))]
            return df, "real"

    # If not the Hamburg location or file not found, try standard approach
    # Normalize coordinates for filename matching
    normalized_lat = f"{float(lat):.5f}"
    normalized_lon = f"{float(lon):.5f}"

    # Construct filename
    filename = f"WeatherData_{start_date}_to_{end_date}_{normalized_lat}_{normalized_lon}.csv"
    filepath = os.path.join(data_dir, filename)

    # Try to load the exact file
    if os.path.exists(filepath):
        df = pd.read_csv(filepath, parse_dates=["datetime"])
        return df, "real"

    # Try to find a file that covers the date range
    covering_files = find_covering_csv(start_date, end_date, lat, lon, data_dir)
    if covering_files:
        # Sort by coverage (start date ascending, end date descending)
        covering_files.sort(key=lambda x: (x[0], -x[1].toordinal()))
        s, e, filename_existing = covering_files[0]
        full_path = os.path.join(data_dir, filename_existing)

        # Load the file and filter to the requested date range
        df = pd.read_csv(full_path, parse_dates=['datetime'])
        df = df[(df['datetime'] >= pd.to_datetime(start_date)) &
                (df['datetime'] <= pd.to_datetime(end_date))]
        return df, "real"

    # Fall back to mock data
    return generate_mock_weather_data(start_date, end_date), "mock"


def normalize_coords(lat, lon):
    """Normalize coordinates to 5 decimal places as strings"""
    return f"{float(lat):.5f}", f"{float(lon):.5f}"


def parse_csv_filename(filename):
    """Parse date range and coordinates from a weather data CSV filename"""
    parts = filename.replace(".csv", "").split("_")
    start = pd.to_datetime(parts[1])
    end = pd.to_datetime(parts[3])
    lat = parts[4]
    lon = parts[5]
    return start, end, lat, lon


def find_covering_csv(start_date, end_date, lat, lon, directory):
    """Find CSV files that cover the given date range and coordinates"""
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
            except Exception:
                continue  # Skip malformed files

    return covering_files


def generate_mock_weather_data(start_date, end_date):
    """Generate mock weather data for the given date range"""
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    days = (end_date - start_date).days + 1
    dates = [start_date + datetime.timedelta(days=i) for i in range(days)]

    # Create dataframe with similar structure to the CSV
    data = {
        "datetime": dates,
        "tempmax": [random.uniform(15, 35) for _ in range(days)],
        "tempmin": [random.uniform(5, 20) for _ in range(days)],
        "temp": [random.uniform(10, 28) for _ in range(days)],
        "precip": [random.uniform(0, 15) for _ in range(days)],
        "precipprob": [random.randint(0, 100) for _ in range(days)],
        "precipcover": [random.uniform(0, 100) for _ in range(days)],
        "humidity": [random.uniform(30, 95) for _ in range(days)],
        "cloudcover": [random.uniform(0, 100) for _ in range(days)],
        "visibility": [random.uniform(0, 10) for _ in range(days)],
        "solarradiation": [random.uniform(0, 300) for _ in range(days)],
        "uvindex": [random.randint(0, 10) for _ in range(days)]
    }

    # Add precipitation type
    precip_types = [None, "rain", "snow"]
    data["preciptype"] = [random.choice(precip_types) if p > 0.1 else None for p in data["precip"]]

    return pd.DataFrame(data)


def load_lst_data(lat, lon, start_date, end_date, data_dir="."):
    """
    Load Land Surface Temperature data from H5 file for the given coordinates and date range.
    Falls back to mock data if real data is not available.
    """
    # Generate intervals for May-September (when LST data is available)
    intervals = generate_may_september_intervals(start_date, end_date)

    # For Hamburg location, use the get_data_file_paths function
    if abs(float(lat) - 53.562762) < 0.001 and abs(float(lon) - 9.573723) < 0.001:
        _, lst_h5_path = get_data_file_paths(lat, lon, start_date, end_date)

        if lst_h5_path and os.path.exists(lst_h5_path):
            return lst_h5_path, "real", intervals

    # If not the Hamburg location or file not found, try standard approach
    normalized_lat = f"{float(lat):.5f}"
    normalized_lon = f"{float(lon):.5f}"

    # Try to find matching H5 files
    h5_files = find_lst_h5_files(lat, lon, data_dir)

    if h5_files:
        # Find the file with the best coverage
        best_file = None
        best_coverage = 0

        for file_start, file_end, filepath in h5_files:
            coverage_days = 0
            for interval_start, interval_end in intervals:
                if file_start <= interval_end and file_end >= interval_start:
                    overlap_start = max(file_start, interval_start)
                    overlap_end = min(file_end, interval_end)
                    coverage_days += (overlap_end - overlap_start).days + 1

            if coverage_days > best_coverage:
                best_coverage = coverage_days
                best_file = filepath

        if best_file:
            return best_file, "real", intervals

    # Fall back to mock data
    mock_path = os.path.join(data_dir, f"mock_LST_{normalized_lat}_{normalized_lon}.h5")
    return mock_path, "mock", intervals


def find_lst_h5_files(lat, lon, directory):
    """Find LST H5 files for the given coordinates"""
    lat, lon = normalize_coords(lat, lon)
    h5_files = []

    for file in os.listdir(directory):
        if file.endswith(".h5") and "LST" in file:
            try:
                match = re.match(r"LST_(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})_.*\.h5", file)
                if match:
                    file_start = pd.to_datetime(match.group(1))
                    file_end = pd.to_datetime(match.group(2))

                    # Extract coordinates from filename
                    parts = file.replace(".h5", "").split("_")
                    file_lat = parts[-2]
                    file_lon = parts[-1]

                    if file_lat == lat and file_lon == lon:
                        h5_files.append((file_start, file_end, os.path.join(directory, file)))
            except Exception:
                continue

    return h5_files


def generate_may_september_intervals(start_date, end_date):
    """Generate intervals for May-September periods between start_date and end_date"""
    intervals = []
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

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


def extract_lst_data(h5_path, intervals, data_type="real"):
    """Extract LST data from H5 file for the given intervals"""
    daily_surface_temps = {}

    if data_type == "real":
        try:
            with h5py.File(h5_path, "r") as h5_file:
                for key in h5_file.keys():
                    try:
                        date_str, time_str = key.split(",")
                        date_obj = pd.to_datetime(date_str)

                        # Check if date is within any of the intervals
                        for interval_start, interval_end in intervals:
                            if interval_start <= date_obj <= interval_end:
                                temp = h5_file[key]["Median_Temperature"][()]
                                daily_surface_temps.setdefault(date_obj.date(), []).append(temp)
                                break
                    except Exception:
                        continue
        except Exception as e:
            st.warning(f"Error reading LST data: {e}. Using simulated data.")
            return generate_mock_lst_data(intervals)
    else:
        # If mock data is requested, generate it
        return generate_mock_lst_data(intervals)

    return daily_surface_temps


def generate_mock_lst_data(intervals):
    """Generate mock LST data for the given intervals"""
    daily_surface_temps = {}

    for interval_start, interval_end in intervals:
        dates = pd.date_range(start=interval_start, end=interval_end, freq="D")
        for date in dates:
            # Generate 1-3 readings per day
            n_readings = random.randint(1, 3)
            temperatures = [random.uniform(20, 35) for _ in range(n_readings)]
            daily_surface_temps[date.date()] = temperatures

    return daily_surface_temps


# Weather analysis functions (from TemperaturesAutomated.py)
def plot_min_temps(df, start_date, end_date):
    """Generate plot for minimum temperatures"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    sub_df = df[(df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))]

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
    return fig


def plot_max_temps(df, start_date, end_date):
    """Generate plot for maximum temperatures"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    sub_df = df[(df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))]

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
    return fig


def plot_min_max_temps_overlayed(df, start_date, end_date):
    """Generate plot for overlayed min-max temperatures"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    sub_df = df[(df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))]

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
    return fig


def rainy_days_per_month(df, start_date, end_date):
    """Generate plot for rainy days per month"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df["month"] = df["datetime"].dt.to_period("M")
    df["rainy"] = df["precipprob"] > 0
    filtered = df[(df["datetime"] >= pd.to_datetime(start_date)) & (df["datetime"] <= pd.to_datetime(end_date))]
    rainy_counts = filtered.groupby("month")["rainy"].sum()

    fig = px.bar(
        x=rainy_counts.index.astype(str),
        y=rainy_counts.values,
        labels={"x": "Month", "y": "Rainy Days"},
        title="Number of Rainy Days Per Month"
    )
    return fig


def rain_hours_per_day(df, start_date, end_date):
    """Generate plot for rain hours per day"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    sub_df = df[(df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))].copy()
    sub_df['rain_hours'] = (sub_df['precipcover'] / 100) * 24

    fig = px.bar(
        sub_df, x='datetime', y='rain_hours',
        labels={"datetime": "Date", "rain_hours": "Rain Hours"},
        title=f"Estimated Rain Hours per Day ({start_date} to {end_date})"
    )
    return fig


def total_rain_and_coverage(df, start_date, end_date):
    """Calculate total rain and coverage statistics"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    mask = (df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))
    sub_df = df.loc[mask]

    if sub_df.empty:
        return None, None, None, None

    max_precip = sub_df['precip'].max()
    max_precip_date = sub_df[sub_df['precip'] == max_precip]['datetime'].iloc[0]
    avg_precipcover = sub_df['precipcover'].mean()
    total_precip = sub_df['precip'].sum()

    return max_precip, max_precip_date, avg_precipcover, total_precip


def longest_dry_streak(df, start_date, end_date):
    """Calculate longest dry streak"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    mask = (df['datetime'] >= pd.to_datetime(start_date)) & (df['datetime'] <= pd.to_datetime(end_date))
    sub_df = df.loc[mask].sort_values('datetime').copy()

    is_dry = sub_df['precip'] == 0

    max_streak = 0
    current_streak = 0
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

    return max_streak, longest_range


def compare_periods(df, period1_start, period1_end, period2_start, period2_end):
    """Compare two time periods"""
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])

    # Filter data for both periods
    period1 = df[(df['datetime'] >= pd.to_datetime(period1_start)) & (df['datetime'] <= pd.to_datetime(period1_end))]
    period2 = df[(df['datetime'] >= pd.to_datetime(period2_start)) & (df['datetime'] <= pd.to_datetime(period2_end))]

    if period1.empty or period2.empty:
        return None

    # Calculate monthly statistics for temperature and precipitation
    period1['month'] = period1['datetime'].dt.strftime('%b')
    period2['month'] = period2['datetime'].dt.strftime('%b')

    period1_monthly = period1.groupby('month').agg({
        'temp': 'mean',
        'tempmin': 'mean',
        'tempmax': 'mean',
        'precip': 'sum'
    }).reset_index()
    period1_monthly['period'] = f"{period1_start[:4]}"

    period2_monthly = period2.groupby('month').agg({
        'temp': 'mean',
        'tempmin': 'mean',
        'tempmax': 'mean',
        'precip': 'sum'
    }).reset_index()
    period2_monthly['period'] = f"{period2_start[:4]}"

    # Combine data
    comparison_df = pd.concat([period1_monthly, period2_monthly])

    # Create comparison charts
    fig_temp = go.Figure()
    for period, color in zip([f"{period1_start[:4]}", f"{period2_start[:4]}"], ['blue', 'red']):
        df_period = comparison_df[comparison_df['period'] == period]
        fig_temp.add_trace(go.Scatter(
            x=df_period['month'],
            y=df_period['temp'],
            mode='lines+markers',
            name=f"{period} Avg Temp",
            line=dict(color=color)
        ))

    fig_temp.update_layout(
        title=f"Average Temperature Comparison: {period1_start[:4]} vs {period2_start[:4]}",
        xaxis_title="Month",
        yaxis_title="Temperature (°C)",
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )

    fig_precip = go.Figure()
    for period, color in zip([f"{period1_start[:4]}", f"{period2_start[:4]}"], ['skyblue', 'indianred']):
        df_period = comparison_df[comparison_df['period'] == period]
        fig_precip.add_trace(go.Bar(
            x=df_period['month'],
            y=df_period['precip'],
            name=f"{period} Precipitation",
            marker_color=color
        ))

    fig_precip.update_layout(
        title=f"Monthly Precipitation Comparison: {period1_start[:4]} vs {period2_start[:4]}",
        xaxis_title="Month",
        yaxis_title="Precipitation (mm)",
        barmode='group',
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )

    return fig_temp, fig_precip


def plot_land_surface_temperature(weather_df, lst_data, intervals):
    """Generate plot for land surface temperature"""
    weather_df = weather_df.copy()
    weather_df["date"] = pd.to_datetime(weather_df["datetime"]).dt.date

    # Create lookup for air temperatures
    temp_lookup = weather_df.groupby("date")[["tempmin", "tempmax"]].mean().to_dict("index")

    # Process surface temperature data
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

        if date in lst_data and lst_data[date]:
            mean_lst = sum(lst_data[date]) / len(lst_data[date])
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
    return fig


def compare_surface_and_air_temperatures(weather_df, lst_data, intervals):
    """Generate plot comparing surface and air temperatures"""
    weather_df = weather_df.copy()
    weather_df["date"] = pd.to_datetime(weather_df["datetime"]).dt.date

    # Create lookup for air temperatures
    temp_lookup = weather_df.groupby("date")[["tempmin", "tempmax"]].mean().to_dict("index")

    # Create date list from intervals
    all_dates = []
    for interval_start, interval_end in intervals:
        dates = pd.date_range(start=interval_start, end=interval_end, freq="D")
        all_dates.extend(dates.date)

    # Prepare data for plotting
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
        if date in lst_data and lst_data[date]:
            mean_lst = sum(lst_data[date]) / len(lst_data[date])
            if mean_lst >= tempmin:
                final_surface_temps.append(mean_lst)
            else:
                final_surface_temps.append(avg_air_temp)
        else:
            final_surface_temps.append(avg_air_temp)

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=all_dates,
        y=daily_min,
        mode='lines+markers',
        name="Min Temp (°C)",
        line=dict(color="skyblue")
    ))
    fig.add_trace(go.Scatter(
        x=all_dates,
        y=daily_max,
        mode='lines+markers',
        name="Max Temp (°C)",
        line=dict(color="tomato")
    ))
    fig.add_trace(go.Scatter(
        x=all_dates,
        y=final_surface_temps,
        mode='lines+markers',
        name="Surface Temp (LST °C)",
        line=dict(color="black")
    ))

    fig.update_layout(
        title="Comparison of Air and Surface Temperatures (May–September only)",
        xaxis_title="Date",
        yaxis_title="Temperature (°C)",
        xaxis=dict(tickangle=45),
        template="plotly_white",
        height=500
    )
    return fig


# Integration function to update the climate_analysis_page
def enhanced_climate_analysis_page():
    st.title(f"📊 Climate Analysis: {st.session_state.analysis_name}")

    # Always use the predefined coordinates with prepared data
    lat = 53.562762
    lon = 9.573723

    # Show notice about using predefined location
    st.info(
        "This analysis is using high-quality weather and temperature data from the Hamburg Area (53.562762°N, 9.573723°E).")

    # Get location information from session state (for display purposes only)
    custom_location = False
    if "location" in st.session_state and st.session_state.location:
        location = st.session_state.location
        if "coordinates" in location:
            selected_lat = location["coordinates"][1]
            selected_lon = location["coordinates"][0]

            # If user selected a different location, show notice
            if abs(selected_lat - lat) > 0.001 or abs(selected_lon - lon) > 0.001:
                custom_location = True
                st.warning(
                    f"You selected a different location (approximately {selected_lat:.4f}°N, {selected_lon:.4f}°E), but we're showing data for our reference location with complete historical records.")

    if custom_location:
        st.write("For accurate analysis at your selected location, please contact us to prepare site-specific data.")

    # Determine date range based on user tier
    today = datetime.datetime.today()
    if st.session_state.tier == "basic":
        end_date = today.strftime("%Y-%m-%d")
        start_date = (today - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    elif st.session_state.tier == "standard":
        end_date = today.strftime("%Y-%m-%d")
        start_date = (today - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    else:  # premium
        end_date = today.strftime("%Y-%m-%d")
        start_date = (today - datetime.timedelta(days=730)).strftime("%Y-%m-%d")

    # Date range selection with appropriate limits
    st.sidebar.subheader("Date Range")
    custom_start = st.sidebar.date_input(
        "Start Date",
        value=pd.to_datetime(start_date),
        min_value=pd.to_datetime(start_date),
        max_value=pd.to_datetime(end_date) - datetime.timedelta(days=1)
    )
    custom_end = st.sidebar.date_input(
        "End Date",
        value=pd.to_datetime(end_date),
        min_value=custom_start + datetime.timedelta(days=1),
        max_value=pd.to_datetime(end_date)
    )

    # Format dates for use in the analysis
    custom_start_str = custom_start.strftime("%Y-%m-%d")
    custom_end_str = custom_end.strftime("%Y-%m-%d")

    # Load weather data
    with st.spinner("Loading weather data..."):
        weather_df, data_source = load_weather_data(lat, lon, start_date, end_date, data_dir=".")

        # If using custom date range, filter the data
        weather_df = weather_df[(weather_df['datetime'] >= pd.to_datetime(custom_start_str)) &
                                (weather_df['datetime'] <= pd.to_datetime(custom_end_str))]

    # Display data source information
    if data_source == "mock":
        st.info("Note: Using simulated weather data for this location.")

    # Create tabs for different analysis sections
    tab1, tab2, tab3, tab4 = st.tabs(["Temperature", "Precipitation", "Comparison", "Advanced Analysis"])

    # Temperature tab
    with tab1:
        st.subheader("Temperature Analysis")

        # Min-max temperature chart
        min_max_fig = plot_min_max_temps_overlayed(weather_df, custom_start_str, custom_end_str)
        st.plotly_chart(min_max_fig, use_container_width=True)

        # Temperature statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_temp = weather_df['temp'].mean()
            st.metric("Average Temperature", f"{avg_temp:.1f}°C")
        with col2:
            min_temp = weather_df['tempmin'].min()
            st.metric("Minimum Temperature", f"{min_temp:.1f}°C")
        with col3:
            max_temp = weather_df['tempmax'].max()
            st.metric("Maximum Temperature", f"{max_temp:.1f}°C")

    # Precipitation tab
    with tab2:
        st.subheader("Precipitation Analysis")

        # Rainy days per month
        rainy_days_fig = rainy_days_per_month(weather_df, custom_start_str, custom_end_str)
        st.plotly_chart(rainy_days_fig, use_container_width=True)

        # Rain hours per day
        rain_hours_fig = rain_hours_per_day(weather_df, custom_start_str, custom_end_str)
        st.plotly_chart(rain_hours_fig, use_container_width=True)

        # Precipitation statistics
        max_precip, max_precip_date, avg_precipcover, total_precip = total_rain_and_coverage(
            weather_df, custom_start_str, custom_end_str
        )

        # Display statistics in columns
        if max_precip is not None:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Rainfall", f"{total_precip:.1f} mm")
            with col2:
                st.metric("Maximum Daily Rainfall", f"{max_precip:.1f} mm")
                if max_precip_date:
                    st.caption(f"on {max_precip_date.date()}")
            with col3:
                st.metric("Average Rain Coverage", f"{avg_precipcover:.1f}%")

        # Longest dry streak
        max_streak, longest_range = longest_dry_streak(weather_df, custom_start_str, custom_end_str)
        if max_streak > 0:
            st.subheader("Dry Periods")
            st.metric("Longest Dry Streak", f"{max_streak} days")
            if longest_range[0] is not None:
                st.caption(f"From {longest_range[0].date()} to {longest_range[1].date()}")

    # Comparison tab (for standard and premium tiers)
    with tab3:
        if st.session_state.tier in ["standard", "premium"]:
            st.subheader("Historical Comparison")

            # For standard tier, compare current year with previous year
            if len(pd.date_range(start=start_date, end=end_date).year.unique()) > 1:
                # Get the two most recent years in the data
                years = sorted(weather_df['datetime'].dt.year.unique(), reverse=True)
                if len(years) >= 2:
                    year1, year2 = years[0], years[1]

                    period1_end = custom_end_str
                    period1_start = max(pd.to_datetime(start_date),
                                        pd.to_datetime(f"{year1}-01-01")).strftime("%Y-%m-%d")

                    period2_end = f"{year2}-12-31"
                    period2_start = max(pd.to_datetime(start_date),
                                        pd.to_datetime(f"{year2}-01-01")).strftime("%Y-%m-%d")

                    # Generate comparison charts
                    comparison_figs = compare_periods(weather_df, period1_start, period1_end,
                                                      period2_start, period2_end)

                    if comparison_figs:
                        temp_fig, precip_fig = comparison_figs
                        st.plotly_chart(temp_fig, use_container_width=True)
                        st.plotly_chart(precip_fig, use_container_width=True)
                    else:
                        st.warning("Not enough data for comparison between years.")
                else:
                    st.info("Only one year of data available. Can't generate comparison.")
            else:
                st.info("Need data from multiple years for comparison. Adjust your subscription or date range.")
        else:
            st.info("🔒 Year-to-year comparison requires Standard or Premium tier.")

    # Advanced analysis tab (for premium tier)
    with tab4:
        if st.session_state.tier == "premium":
            st.subheader("Advanced Temperature Analysis")

            # Load LST data for premium users
            with st.spinner("Loading land surface temperature data..."):
                lst_path, lst_source, intervals = load_lst_data(lat, lon, start_date, end_date, data_dir=".")
                lst_data = extract_lst_data(lst_path, intervals, data_type=lst_source)

            if lst_source == "mock":
                st.info("Note: Using simulated land surface temperature data for this location.")

            # Surface temperature analysis
            st.subheader("Land Surface Temperature")
            lst_fig = plot_land_surface_temperature(weather_df, lst_data, intervals)
            st.plotly_chart(lst_fig, use_container_width=True)

            # Comparison of air and surface temperatures
            st.subheader("Air vs. Surface Temperature")
            compare_fig = compare_surface_and_air_temperatures(weather_df, lst_data, intervals)
            st.plotly_chart(compare_fig, use_container_width=True)

            # Temperature anomaly analysis
            st.subheader("Temperature Anomaly")

            # Calculate anomalies compared to average
            weather_df['month'] = pd.to_datetime(weather_df['datetime']).dt.month
            monthly_avg = weather_df.groupby('month')['temp'].mean().to_dict()

            # Generate anomaly data
            weather_df['temp_anomaly'] = weather_df.apply(
                lambda x: x['temp'] - monthly_avg[x['month']], axis=1
            )

            # Plot anomalies
            anomaly_fig = go.Figure()
            anomaly_fig.add_trace(go.Scatter(
                x=weather_df['datetime'],
                y=weather_df['temp_anomaly'],
                mode='lines+markers',
                line=dict(color='purple'),
                name='Temperature Anomaly'
            ))
            anomaly_fig.update_layout(
                title="Temperature Anomaly (Deviation from Monthly Average)",
                xaxis_title="Date",
                yaxis_title="Temperature Anomaly (°C)",
                template="plotly_white"
            )

            st.plotly_chart(anomaly_fig, use_container_width=True)
        else:
            st.info("🔒 Advanced analysis requires Premium tier.")

            if st.button("Upgrade to Premium"):
                st.session_state.page = "upgrade"
                st.rerun()