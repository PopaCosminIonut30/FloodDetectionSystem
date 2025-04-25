import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
import h5py
from datetime import datetime
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.subplots as sp


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


def compare_periods(df1, start1, end1, df2, start2, end2):
    df1 = df1.copy()
    df2 = df2.copy()

    df1['datetime'] = pd.to_datetime(df1['datetime'])
    df2['datetime'] = pd.to_datetime(df2['datetime'])

    period1 = df1[(df1["datetime"] >= start1) & (df1["datetime"] <= end1)]
    period2 = df2[(df2["datetime"] >= start2) & (df2["datetime"] <= end2)]

    # === Temperature Metrics ===
    temp_data = {
        "Metric": ["Avg Min Temp (°C)", "Avg Max Temp (°C)"],
        "Period 1": [period1["tempmin"].mean(), period1["tempmax"].mean()],
        "Period 2": [period2["tempmin"].mean(), period2["tempmax"].mean()],
    }

    # === Rain Metrics ===
    rain_data = {
        "Metric": ["Rainy Days"],
        "Period 1": [period1[period1["precip"] > 0].shape[0]],
        "Period 2": [period2[period2["precip"] > 0].shape[0]],
    }

    temp_df = pd.DataFrame(temp_data)
    rain_df = pd.DataFrame(rain_data)

    # === Plotting ===
    fig = sp.make_subplots(
        rows=1, cols=2,
        subplot_titles=("Temperature Comparison", "Rainy Days Comparison")
    )

    # Add temperature bars
    for i, period in enumerate(["Period 1", "Period 2"]):
        fig.add_trace(go.Bar(
            x=temp_df["Metric"], y=temp_df[period], name=period
        ), row=1, col=1)

        fig.add_trace(go.Bar(
            x=rain_df["Metric"], y=rain_df[period], name=period, showlegend=False
        ), row=1, col=2)

    fig.update_layout(
        title_text=f"Comparison between {start1}–{end1} and {start2}–{end2}",
        barmode="group",
        template="plotly_white",
        height=500,
        showlegend=True
    )

    fig.show()


def plot_land_surface_temperature(csv_path, h5_path, start_date, end_date):
    weather_df = pd.read_csv(csv_path, parse_dates=["datetime"])
    weather_df["date"] = weather_df["datetime"].dt.date
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    weather_df = weather_df[(weather_df["date"] >= start_date) & (weather_df["date"] <= end_date)]
    temp_lookup = weather_df.groupby("date")[["tempmin", "tempmax"]].mean().to_dict("index")

    daily_surface_temps = {}
    with h5py.File(h5_path, "r") as h5_file:
        for key in h5_file.keys():
            try:
                date_str, time_str = key.split(",")
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_obj < start_date or date_obj > end_date:
                    continue
                if date_obj not in temp_lookup:
                    continue
                h5_temp = h5_file[key]["Median_Temperature"][()]
                if h5_temp >= temp_lookup[date_obj]["tempmin"]:
                    daily_surface_temps.setdefault(date_obj, []).append(h5_temp)
            except Exception:
                continue

    all_dates = pd.date_range(start=start_date, end=end_date, freq="D").date
    final_temps = []
    for date in all_dates:
        if date in daily_surface_temps and len(daily_surface_temps[date]) > 0:
            final_temps.append(sum(daily_surface_temps[date]) / len(daily_surface_temps[date]))
        elif date in temp_lookup:
            avg_temp = (temp_lookup[date]["tempmin"] + temp_lookup[date]["tempmax"]) / 2
            final_temps.append(avg_temp)
        else:
            final_temps.append(None)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(all_dates),
        y=final_temps,
        mode='lines+markers',
        line=dict(color='orange'),
        name='Surface Temp (°C)'
    ))

    fig.update_layout(
        title=f"Daily Surface Temperature Variation ({start_date} to {end_date})",
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

    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    weather_df = weather_df[(weather_df["date"] >= start_date) & (weather_df["date"] <= end_date)]
    temp_lookup = weather_df.groupby("date")[["tempmin", "tempmax"]].mean().to_dict("index")

    # Extract daily min and max as time series
    full_range = pd.date_range(start=start_date, end=end_date, freq="D")
    daily_min = [temp_lookup[d]["tempmin"] if d in temp_lookup else None for d in full_range.date]
    daily_max = [temp_lookup[d]["tempmax"] if d in temp_lookup else None for d in full_range.date]

    # Load surface temperature from HDF5 and apply same filtering logic
    daily_surface_temps = {}
    with h5py.File(h5_path, "r") as h5_file:
        for key in h5_file.keys():
            try:
                date_str, _ = key.split(",")
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

                if date_obj < start_date or date_obj > end_date:
                    continue
                if date_obj not in temp_lookup:
                    continue

                h5_temp = h5_file[key]["Median_Temperature"][()]
                if h5_temp >= temp_lookup[date_obj]["tempmin"]:
                    daily_surface_temps.setdefault(date_obj, []).append(h5_temp)
            except Exception:
                continue

    final_surface_temps = []
    for date in full_range.date:
        if date in daily_surface_temps and daily_surface_temps[date]:
            final_surface_temps.append(sum(daily_surface_temps[date]) / len(daily_surface_temps[date]))
        elif date in temp_lookup:
            avg_temp = (temp_lookup[date]["tempmin"] + temp_lookup[date]["tempmax"]) / 2
            final_surface_temps.append(avg_temp)
        else:
            final_surface_temps.append(None)

    # Plot with Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=full_range, y=daily_min,
        mode='lines+markers',
        name="Min Temp (°C)",
        line=dict(color="skyblue")
    ))
    fig.add_trace(go.Scatter(
        x=full_range, y=daily_max,
        mode='lines+markers',
        name="Max Temp (°C)",
        line=dict(color="tomato")
    ))
    fig.add_trace(go.Scatter(
        x=full_range, y=final_surface_temps,
        mode='lines+markers',
        name="Surface Temp (LST °C)",
        line=dict(color="black")
    ))

    fig.update_layout(
        title=f"Comparison of Air and Surface Temperatures ({start_date} to {end_date})",
        xaxis_title="Date",
        yaxis_title="Temperature (°C)",
        xaxis=dict(tickangle=45),
        template="plotly_white",
        height=500
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
