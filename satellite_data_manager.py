import pandas as pd
import numpy as np
import datetime
import random
import math
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from fpdf import FPDF
from io import BytesIO
import base64
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import h5py
import os
import sys

# Integrate with your existing temperature functions
from TemperatureFunctions_Interactive import (
    plot_min_temps,
    plot_max_temps,
    plot_min_max_temps_overlayed,
    rainy_days_per_month,
    longest_dry_streak,
    rain_hours_per_day,
    total_rain_and_coverage,
    compare_periods,
    plot_land_surface_temperature,
    compare_surface_and_air_temperatures
)


class SatelliteDataManager:
    def __init__(self):
        """Initialize the SatelliteDataManager with tier-specific functionality"""
        self.data_path = "Temperatures"  # Base path for data files

    def load_data(self, username, tier="basic", location=None):
        """
        Load appropriate data based on user tier.

        Parameters:
        - username: user identifier
        - tier: subscription tier (basic, standard, premium)
        - location: dictionary with coordinates

        Returns:
        - Dictionary with loaded dataframes and tier information
        """
        # Extract location info
        if location and "coordinates" in location:
            lat = location["coordinates"][1]
            lon = location["coordinates"][0]
        else:
            # Default coordinates (fallback to values in your example)
            lat = 53.562762
            lon = 9.573723

        # Set date ranges based on tier
        end_date = datetime.date.today()

        if tier == "basic":
            # Basic tier: 3 months of data
            start_date = end_date - datetime.timedelta(days=90)
            months_of_data = 3
        elif tier == "standard":
            # Standard tier: 12 months of data
            start_date = end_date - datetime.timedelta(days=365)
            months_of_data = 12
        else:  # premium
            # Premium tier: 24 months (2 years) of data
            start_date = end_date - datetime.timedelta(days=730)
            months_of_data = 24

        # Format dates for filenames
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # Simulate previous year for comparison (standard and premium tiers)
        prev_year_start = start_date.replace(year=start_date.year - 1)
        prev_year_end = end_date.replace(year=end_date.year - 1)
        prev_start_str = prev_year_start.strftime("%Y-%m-%d")
        prev_end_str = prev_year_end.strftime("%Y-%m-%d")

        # Construct filenames to match your existing format
        current_filename = f"WeatherData_{start_date_str}_to_{end_date_str}_{lat:.5f}_{lon:.5f}.csv"
        previous_filename = f"WeatherData_{prev_start_str}_to_{prev_end_str}_{lat:.5f}_{lon:.5f}.csv"

        # Set paths for data files
        # In a real implementation, these would be actual file paths
        base_path = self.data_path
        current_path = f"{base_path}/{current_filename}"
        previous_path = f"{base_path}/{previous_filename}"

        # For LST data (premium tier)
        lst_start = end_date - datetime.timedelta(days=30)  # Last month for LST data
        lst_end = end_date
        lst_start_str = lst_start.strftime("%Y-%m-%d")
        lst_end_str = lst_end.strftime("%Y-%m-%d")
        lst_filename = f"LST_{lst_start_str}_to_{lst_end_str}_{lat:.5f}_{lon:.5f}.h5"
        lst_path = f"{base_path}/{lst_filename}"

        try:
            # Try to load actual CSV data - if file exists, use it, otherwise generate mock data
            try:
                # For demo/testing - check if file exists before trying to read it
                current_data = self._load_weather_data(current_path, start_date, end_date)
                file_loaded = True
            except Exception as e:
                st.warning(f"Weather data file not found, using simulated data instead: {e}")
                current_data = self._mock_weather_data(start_date, end_date, months_of_data)
                file_loaded = False

            result = {
                "tier": tier,
                "current_data": current_data,
                "months_of_data": months_of_data,
                "location": {"lat": lat, "lon": lon},
                "data_source": "real" if file_loaded else "mock",
                "dates": {
                    "start": start_date_str,
                    "end": end_date_str
                }
            }

            # Add comparison data for standard and premium tiers
            if tier in ["standard", "premium"]:
                try:
                    result["previous_data"] = self._load_weather_data(previous_path, prev_year_start, prev_year_end)
                    result["comparison_available"] = True
                except:
                    # Fallback to mock data if previous year file is not available
                    result["previous_data"] = self._mock_weather_data(prev_year_start, prev_year_end, months_of_data)
                    result["comparison_available"] = True
            else:
                result["comparison_available"] = False

            # Add LST data and forecasts for premium tier
            if tier == "premium":
                try:
                    result["lst_data"] = self._load_lst_data(lst_path, lst_start, lst_end)
                except:
                    result["lst_data"] = self._mock_lst_data(lst_start, lst_end)

                result["forecast_data"] = self._generate_forecast_data(end_date, 30)  # 30-day forecast
                result["alerts"] = self._generate_weather_alerts(current_data)

            return result

        except Exception as e:
            # If any error occurs in loading real data, fall back to mock data
            st.error(f"Error loading data: {str(e)}")
            return self._generate_mock_data_package(tier, start_date, end_date, months_of_data, lat, lon)

    def _load_weather_data(self, file_path, start_date, end_date):
        """Load weather data from CSV file"""
        try:
            # Try to load with exact path first
            df = pd.read_csv(file_path)
        except:
            # If not found, try alternative locations
            # This would need to be adapted to your file structure
            alternate_paths = [
                file_path,
                f"C:/Users/popac/Downloads/Floods-20250424T154640Z-001/Floods/.venv/Final/{file_path}",
                f".venv/Final/{file_path}",
                os.path.basename(file_path)
            ]

            for path in alternate_paths:
                try:
                    df = pd.read_csv(path)
                    break
                except:
                    continue
            else:
                raise FileNotFoundError(f"Could not find weather data file in any location")

        # Convert datetime column
        df['datetime'] = pd.to_datetime(df['datetime'])

        # Filter to date range
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]

        return df

    def _load_lst_data(self, file_path, start_date, end_date):
        """Load land surface temperature data from H5 file"""
        try:
            # Try different possible locations for the file
            alternate_paths = [
                file_path,
                f"C:/Users/popac/Downloads/Floods-20250424T154640Z-001/Floods/.venv/Final/{file_path}",
                f".venv/Final/{file_path}",
                os.path.basename(file_path)
            ]

            h5_file = None
            for path in alternate_paths:
                try:
                    h5_file = h5py.File(path, 'r')
                    break
                except:
                    continue

            if h5_file is None:
                raise FileNotFoundError(f"Could not find LST data file in any location")

            # Extract data from H5 file
            dates = []
            times = []
            temperatures = []

            for key in h5_file.keys():
                try:
                    date_str, time_str = key.split(",")
                    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

                    # Check if date is in range
                    if date_obj >= start_date.date() and date_obj <= end_date.date():
                        median_temp = h5_file[key]["Median_Temperature"][()]

                        dates.append(date_obj)
                        times.append(time_str)
                        temperatures.append(median_temp)
                except:
                    continue

            h5_file.close()

            # Create DataFrame from extracted data
            lst_df = pd.DataFrame({
                "datetime": [datetime.datetime.combine(d, datetime.datetime.strptime(t, "%H:%M:%S").time())
                             for d, t in zip(dates, times)],
                "lst_mean": temperatures
            })

            # Add day/night approximation
            lst_df["hour"] = lst_df["datetime"].dt.hour
            lst_df["lst_day"] = lst_df.apply(lambda x: x["lst_mean"] if 6 <= x["hour"] < 18 else np.nan, axis=1)
            lst_df["lst_night"] = lst_df.apply(lambda x: x["lst_mean"] if x["hour"] < 6 or x["hour"] >= 18 else np.nan,
                                               axis=1)

            return lst_df

        except Exception as e:
            st.warning(f"Error loading LST data: {str(e)}. Using simulated data instead.")
            return self._mock_lst_data(start_date, end_date)

    def _generate_mock_data_package(self, tier, start_date, end_date, months_of_data, lat, lon):
        """Generate a complete mock data package when real data can't be loaded"""
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        prev_year_start = start_date.replace(year=start_date.year - 1)
        prev_year_end = end_date.replace(year=end_date.year - 1)

        lst_start = end_date - datetime.timedelta(days=30)
        lst_end = end_date

        result = {
            "tier": tier,
            "current_data": self._mock_weather_data(start_date, end_date, months_of_data),
            "months_of_data": months_of_data,
            "location": {"lat": lat, "lon": lon},
            "data_source": "mock",
            "dates": {
                "start": start_date_str,
                "end": end_date_str
            }
        }

        if tier in ["standard", "premium"]:
            result["previous_data"] = self._mock_weather_data(prev_year_start, prev_year_end, months_of_data)
            result["comparison_available"] = True
        else:
            result["comparison_available"] = False

        if tier == "premium":
            result["lst_data"] = self._mock_lst_data(lst_start, lst_end)
            result["forecast_data"] = self._generate_forecast_data(end_date, 30)
            result["alerts"] = self._generate_weather_alerts(result["current_data"])

        return result

    def _mock_weather_data(self, start_date, end_date, months):
        """Generate mock weather data similar to the CSV structure"""
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

    def _mock_lst_data(self, start_date, end_date):
        """Generate mock land surface temperature data"""
        days = (end_date - start_date).days + 1

        # Generate several observations per day, to mimic satellite passes
        num_observations = days * 2  # 2 observations per day on average

        # Random timestamps throughout the period
        timestamps = []
        for i in range(days):
            day = start_date + datetime.timedelta(days=i)

            # Morning observation (roughly 10 AM)
            morning_hour = random.randint(9, 11)
            morning_minute = random.randint(0, 59)
            morning_time = datetime.time(morning_hour, morning_minute)
            morning_datetime = datetime.datetime.combine(day, morning_time)
            timestamps.append(morning_datetime)

            # Afternoon observation (roughly 2 PM) for some days
            if random.random() > 0.3:  # 70% chance of afternoon observation
                afternoon_hour = random.randint(13, 15)
                afternoon_minute = random.randint(0, 59)
                afternoon_time = datetime.time(afternoon_hour, afternoon_minute)
                afternoon_datetime = datetime.datetime.combine(day, afternoon_time)
                timestamps.append(afternoon_datetime)

        # Sort timestamps
        timestamps.sort()

        # Generate LST values
        data = {
            "datetime": timestamps,
            "lst_mean": [random.uniform(15, 30) for _ in range(len(timestamps))],
        }

        # Add day/night classification based on hour
        data["hour"] = [dt.hour for dt in timestamps]
        data["lst_day"] = [temp if 6 <= hour < 18 else np.nan for temp, hour in zip(data["lst_mean"], data["hour"])]
        data["lst_night"] = [temp if hour < 6 or hour >= 18 else np.nan for temp, hour in
                             zip(data["lst_mean"], data["hour"])]

        return pd.DataFrame(data)

    def _generate_forecast_data(self, start_date, days):
        """Generate forecast data for specified number of days"""
        dates = [start_date + datetime.timedelta(days=i) for i in range(days)]

        data = {
            "datetime": dates,
            "tempmax": [random.uniform(15, 35) for _ in range(days)],
            "tempmin": [random.uniform(5, 20) for _ in range(days)],
            "temp": [random.uniform(10, 28) for _ in range(days)],
            "precip": [random.uniform(0, 15) for _ in range(days)],
            "precipprob": [random.randint(0, 100) for _ in range(days)],
            "humidity": [random.uniform(30, 95) for _ in range(days)],
            "conditions": [random.choice(["Clear", "Partially cloudy", "Cloudy", "Rain"]) for _ in range(days)]
        }

        return pd.DataFrame(data)

    def _generate_weather_alerts(self, df):
        """Generate weather alerts based on data patterns"""
        alerts = []

        # Check for high temperatures
        high_temp_days = df[df["tempmax"] > 30]
        if len(high_temp_days) > 0:
            alerts.append({
                "type": "Heat Alert",
                "message": f"High temperatures detected on {len(high_temp_days)} days, exceeding 30°C",
                "severity": "High" if len(high_temp_days) > 5 else "Medium"
            })

        # Check for heavy rainfall
        heavy_rain_days = df[df["precip"] > 10]
        if len(heavy_rain_days) > 0:
            alerts.append({
                "type": "Heavy Rainfall",
                "message": f"Heavy rainfall detected on {len(heavy_rain_days)} days, exceeding 10mm",
                "severity": "High" if len(heavy_rain_days) > 3 else "Medium"
            })

        # Check for drought periods
        dry_days = df[df["precip"] < 0.5]
        if len(dry_days) >= 10:
            alerts.append({
                "type": "Drought Risk",
                "message": f"Low precipitation detected over {len(dry_days)} days",
                "severity": "High" if len(dry_days) > 20 else "Medium"
            })

        return alerts

    def analyze_temperature_data(self, data, tier="basic"):
        """
        Analyze temperature data based on tier level
        Uses the existing temperature functions where possible
        Returns plots and metrics relevant to the tier
        """
        results = {}

        # Basic tier: Min-max temperature for 3 months
        df = data["current_data"]
        start_date = data["dates"]["start"]
        end_date = data["dates"]["end"]

        # Create monthly summaries for easier analysis
        df["month"] = pd.to_datetime(df["datetime"]).dt.strftime('%Y-%m')
        monthly_data = df.groupby("month").agg({
            "tempmin": "min",
            "tempmax": "max",
            "temp": "mean",
            "precip": "sum"
        }).reset_index()

        # Min-max temperature chart (basic tier)
        min_max_temp_fig = go.Figure()
        min_max_temp_fig.add_trace(go.Scatter(
            x=df["datetime"],
            y=df["tempmax"],
            mode="lines",
            name="Max Temperature",
            line=dict(color="red")
        ))
        min_max_temp_fig.add_trace(go.Scatter(
            x=df["datetime"],
            y=df["tempmin"],
            mode="lines",
            name="Min Temperature",
            line=dict(color="blue")
        ))
        min_max_temp_fig.update_layout(
            title="Minimum and Maximum Temperatures",
            xaxis_title="Date",
            yaxis_title="Temperature (°C)"
        )
        results["min_max_temp_chart"] = min_max_temp_fig

        # Monthly rainfall (basic tier)
        monthly_rain_fig = px.bar(
            monthly_data,
            x="month",
            y="precip",
            labels={"month": "Month", "precip": "Total Rainfall (mm)"},
            title="Monthly Rainfall"
        )
        results["monthly_rain_chart"] = monthly_rain_fig

        # Calculate rainy days per month (basic tier)
        rainy_days = df[df["precip"] > 0].groupby(
            pd.to_datetime(df["datetime"]).dt.strftime('%Y-%m')).size().reset_index()
        rainy_days.columns = ["month", "rainy_days"]

        rainy_days_fig = px.bar(
            rainy_days,
            x="month",
            y="rainy_days",
            labels={"month": "Month", "rainy_days": "Number of Rainy Days"},
            title="Rainy Days per Month"
        )
        results["rainy_days_chart"] = rainy_days_fig

        # Longest dry period (basic tier)
        # Group consecutive dry days
        df["is_dry"] = df["precip"] < 0.1
        df["dry_group"] = (df["is_dry"] != df["is_dry"].shift()).cumsum()
        dry_periods = df[df["is_dry"]].groupby("dry_group").size().reset_index()
        dry_periods.columns = ["group", "consecutive_dry_days"]

        if not dry_periods.empty:
            longest_dry = dry_periods["consecutive_dry_days"].max()
            results["longest_dry_period"] = longest_dry
        else:
            results["longest_dry_period"] = 0

        # Soil temperature approximation (basic tier)
        # For real data this would come from actual measurements
        # For now, we'll estimate soil temp as slightly lower than air temp
        df["soil_temp"] = df["temp"] - random.uniform(2, 5)
        soil_temp_fig = px.line(
            df,
            x="datetime",
            y="soil_temp",
            labels={"datetime": "Date", "soil_temp": "Soil Temperature (°C)"},
            title="Estimated Soil Temperature"
        )
        results["soil_temp_chart"] = soil_temp_fig

        # Standard tier features
        if tier in ["standard", "premium"]:
            # Year comparison
            if data["comparison_available"]:
                prev_df = data["previous_data"]

                # Create a proper comparison chart using our existing functions
                # Prepare data for comparison
                current_year_data = df.copy()
                current_year_data["year"] = "Current Year"
                current_year_data["month_only"] = pd.to_datetime(current_year_data["datetime"]).dt.strftime('%m-%d')

                prev_year_data = prev_df.copy()
                prev_year_data["year"] = "Previous Year"
                prev_year_data["month_only"] = pd.to_datetime(prev_year_data["datetime"]).dt.strftime('%m-%d')

                # Combine for comparison
                comparison_df = pd.concat([
                    current_year_data[["month_only", "year", "temp", "tempmin", "tempmax", "precip"]],
                    prev_year_data[["month_only", "year", "temp", "tempmin", "tempmax", "precip"]]
                ])

                # Create comparison charts
                temp_comparison_fig = px.line(
                    comparison_df,
                    x="month_only",
                    y="temp",
                    color="year",
                    labels={"month_only": "Date", "temp": "Average Temperature (°C)", "year": "Year"},
                    title="Temperature Comparison: Current vs. Previous Year"
                )
                results["temp_comparison_chart"] = temp_comparison_fig

                # Safely process month data without datetime conversion
                comparison_df["month_num"] = comparison_df["month_only"].apply(
                    lambda x: x.split("-")[0] if isinstance(x, str) and "-" in x else "01"
                )

                rain_comparison_fig = px.bar(
                    comparison_df.groupby(["year", "month_num"]).agg({
                        "precip": "sum"
                    }).reset_index(),
                    x="month_num",
                    y="precip",
                    color="year",
                    barmode="group",
                    labels={"month_num": "Month", "precip": "Total Rainfall (mm)", "year": "Year"},
                    title="Monthly Rainfall Comparison: Current vs. Previous Year"
                )
                results["rain_comparison_chart"] = rain_comparison_fig

            # Heat stress analysis
            df["heat_stress"] = df["tempmax"] > 30
            heat_stress_days = df[df["heat_stress"]].groupby(
                pd.to_datetime(df["datetime"]).dt.strftime('%Y-%m')).size().reset_index()
            heat_stress_days.columns = ["month", "heat_stress_days"]

            if not heat_stress_days.empty:
                heat_stress_fig = px.bar(
                    heat_stress_days,
                    x="month",
                    y="heat_stress_days",
                    labels={"month": "Month", "heat_stress_days": "Days with Heat Stress"},
                    title="Heat Stress Analysis"
                )
                results["heat_stress_chart"] = heat_stress_fig

        # Premium tier features
        if tier == "premium":
            # LST data analysis
            if "lst_data" in data:
                lst_df = data["lst_data"]

                # Combine air and land surface temperatures
                # First ensure we have common datetime format
                lst_df["date"] = lst_df["datetime"].dt.date
                df["date"] = pd.to_datetime(df["datetime"]).dt.date

                # Create a figure comparing air temp and LST
                lst_comparison = pd.merge(
                    df[["date", "temp"]],
                    lst_df.groupby("date")["lst_mean"].mean().reset_index(),
                    on="date",
                    how="inner"
                )

                if not lst_comparison.empty:
                    lst_fig = go.Figure()
                    lst_fig.add_trace(go.Scatter(
                        x=lst_comparison["date"],
                        y=lst_comparison["temp"],
                        mode="lines+markers",
                        name="Air Temperature"
                    ))
                    lst_fig.add_trace(go.Scatter(
                        x=lst_comparison["date"],
                        y=lst_comparison["lst_mean"],
                        mode="lines+markers",
                        name="Land Surface Temperature"
                    ))
                    lst_fig.update_layout(
                        title="Comparison of Air Temperature and Land Surface Temperature",
                        xaxis_title="Date",
                        yaxis_title="Temperature (°C)"
                    )
                    results["lst_comparison_chart"] = lst_fig

            # Weather forecasts
            if "forecast_data" in data:
                forecast_df = data["forecast_data"]

                forecast_fig = go.Figure()
                forecast_fig.add_trace(go.Scatter(
                    x=forecast_df["datetime"],
                    y=forecast_df["tempmax"],
                    mode="lines",
                    name="Forecast Max Temperature",
                    line=dict(color="red")
                ))
                forecast_fig.add_trace(go.Scatter(
                    x=forecast_df["datetime"],
                    y=forecast_df["tempmin"],
                    mode="lines",
                    name="Forecast Min Temperature",
                    line=dict(color="blue")
                ))
                forecast_fig.update_layout(
                    title="30-Day Temperature Forecast",
                    xaxis_title="Date",
                    yaxis_title="Temperature (°C)"
                )
                results["forecast_temp_chart"] = forecast_fig

                forecast_rain_fig = px.bar(
                    forecast_df,
                    x="datetime",
                    y="precip",
                    labels={"datetime": "Date", "precip": "Forecast Rainfall (mm)"},
                    title="30-Day Rainfall Forecast"
                )
                results["forecast_rain_chart"] = forecast_rain_fig

            # Alerts
            if "alerts" in data:
                results["weather_alerts"] = data["alerts"]

        return results

    def get_crop_recommendations(self, data, crop_type):
        """Generate crop-specific recommendations based on analyzed data"""
        if data["tier"] != "premium":
            return []

        df = data["current_data"]
        recommendations = []

        # Basic recommendations for any crop
        recommendations.append("Based on soil moisture trends, adjust irrigation accordingly")

        # Temperature analysis for stress periods
        high_temp_days = len(df[df["tempmax"] > 30])
        if high_temp_days > 3:
            recommendations.append(f"High temperature stress detected on {high_temp_days} days - monitor crop health")

        # Check rainfall patterns
        total_rain = df["precip"].sum()
        if total_rain < 50:  # Low rainfall
            recommendations.append("Low rainfall detected - consider irrigation planning")
        elif total_rain > 200:  # High rainfall
            recommendations.append("High rainfall detected - monitor for disease pressure")

        # Crop-specific recommendations
        if crop_type == "Wheat":
            if any(df["tempmax"] > 32):
                recommendations.append("Temperature exceeding 32°C may affect grain filling - monitor closely")
            if df["humidity"].mean() > 70:
                recommendations.append("Higher humidity levels detected - monitor for fungal diseases")

        elif crop_type == "Corn":
            if any(df["tempmax"] > 35):
                recommendations.append(
                    "Temperature exceeding 35°C may affect pollination - consider heat stress management")
            recommendations.append("Monitor soil moisture closely during the critical silking stage")

        elif crop_type == "Rice":
            if df["humidity"].mean() < 60:
                recommendations.append("Lower humidity levels detected - maintain water levels in paddy")
            recommendations.append("Maintain optimal water depth for current growth stage")

        elif crop_type == "Soybeans":
            if any(df["tempmax"] > 35):
                recommendations.append("High temperatures may affect pod development - monitor closely")
            if df["precip"].sum() < 80:
                recommendations.append("Consider irrigation during pod filling stage")

        elif crop_type == "Potatoes":
            if any(df["tempmax"] > 30):
                recommendations.append(
                    "High temperatures may affect tuber development - consider additional irrigation")
            if df["humidity"].mean() > 75:
                recommendations.append("Higher humidity increases late blight risk - consider preventative fungicide")

        return recommendations

    def create_pdf_report(self, data, analysis_results, name="Satellite Analysis"):
        """Generate a PDF report based on user tier"""
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(200, 10, f"Satellite Data Analysis: {name}", ln=True, align="C")
        pdf.set_font("Arial", size=12)

        # Add date and location information
        pdf.cell(200, 10, f"Generated on {datetime.date.today().strftime('%Y-%m-%d')}", ln=True)
        pdf.cell(200, 10, f"Analysis Period: {data['dates']['start']} to {data['dates']['end']}", ln=True)
        pdf.cell(200, 10, f"Location: Lat {data['location']['lat']:.5f}, Lon {data['location']['lon']:.5f}", ln=True)

        # Basic tier - Weather Summary section
        pdf.set_font("Arial", "B", 14)
        pdf.cell(200, 10, "Weather Summary", ln=True)
        pdf.set_font("Arial", size=12)

        df = data["current_data"]
        pdf.cell(200, 10, f"Average Temperature: {df['temp'].mean():.1f}°C", ln=True)
        pdf.cell(200, 10, f"Temperature Range: {df['tempmin'].min():.1f}°C to {df['tempmax'].max():.1f}°C", ln=True)
        pdf.cell(200, 10, f"Total Rainfall: {df['precip'].sum():.1f}mm", ln=True)
        pdf.cell(200, 10, f"Rainy Days: {len(df[df['precip'] > 0])}", ln=True)

        if "longest_dry_period" in analysis_results:
            pdf.cell(200, 10, f"Longest Dry Period: {analysis_results['longest_dry_period']} days", ln=True)

        # Standard and Premium tier content
        if data["tier"] in ["standard", "premium"]:
            pdf.set_font("Arial", "B", 14)
            pdf.cell(200, 10, "Extended Analysis", ln=True)
            pdf.set_font("Arial", size=12)

            if data["comparison_available"]:
                prev_df = data["previous_data"]
                pdf.cell(200, 10, "Year-to-Year Comparison:", ln=True)

                # Temperature comparison
                temp_diff = df["temp"].mean() - prev_df["temp"].mean()
                pdf.cell(200, 10, f"Temperature Change: {temp_diff:+.1f}°C from previous year", ln=True)

                # Rainfall comparison
                rain_diff = df["precip"].sum() - prev_df["precip"].sum()
                pdf.cell(200, 10, f"Rainfall Change: {rain_diff:+.1f}mm from previous year", ln=True)

                # Heat stress comparison
                current_heat_days = len(df[df["tempmax"] > 30])
                prev_heat_days = len(prev_df[prev_df["tempmax"] > 30])
                pdf.cell(200, 10, f"Heat Stress Days: {current_heat_days} (Current) vs {prev_heat_days} (Previous)",
                         ln=True)

        # Premium tier content
        if data["tier"] == "premium":
            pdf.set_font("Arial", "B", 14)
            pdf.cell(200, 10, "Premium Analysis", ln=True)
            pdf.set_font("Arial", size=12)

            # Land Surface Temperature
            if "lst_data" in data:
                lst_df = data["lst_data"]
                lst_mean = lst_df["lst_mean"].mean()
                pdf.cell(200, 10, f"Average Land Surface Temperature: {lst_mean:.1f}°C", ln=True)

                if "lst_day" in lst_df.columns and "lst_night" in lst_df.columns:
                    day_mean = lst_df["lst_day"].mean()
                    night_mean = lst_df["lst_night"].mean()
                    if not np.isnan(day_mean) and not np.isnan(night_mean):
                        pdf.cell(200, 10, f"Day/Night Temperature Difference: {day_mean - night_mean:.1f}°C", ln=True)

            # Alerts
            if "weather_alerts" in data:
                pdf.cell(200, 10, "Weather Alerts:", ln=True)
                for alert in data["weather_alerts"]:
                    pdf.cell(200, 10, f"• {alert['type']} ({alert['severity']}): {alert['message']}", ln=True)

            # Forecast summary
            if "forecast_data" in data:
                forecast_df = data["forecast_data"]
                pdf.cell(200, 10, "30-Day Forecast Summary:", ln=True)
                pdf.cell(200, 10, f"• Forecast Avg. Temp: {forecast_df['temp'].mean():.1f}°C", ln=True)
                pdf.cell(200, 10, f"• Forecast Total Rain: {forecast_df['precip'].sum():.1f}mm", ln=True)
                pdf.cell(200, 10, f"• Expected Rainy Days: {len(forecast_df[forecast_df['precipprob'] > 50])}", ln=True)

        stream = BytesIO()
        pdf.output(stream)
        return stream.getvalue()


# Helper function to check if a feature is available for the current tier
def feature_available(current_tier, required_tier):
    """Check if a feature is available for the current subscription tier"""
    tier_levels = {"basic": 1, "standard": 2, "premium": 3}
    return tier_levels.get(current_tier, 0) >= tier_levels.get(required_tier, 3)


# Updated analysis page that uses the new SatelliteDataManager
def analysis_page():
    st.title(f"📊 Analysis: {st.session_state.analysis_name}")

    # Initialize data manager if not already in session state
    if "data_manager" not in st.session_state:
        st.session_state.data_manager = SatelliteDataManager()

    # Load data based on user tier if not already loaded
    if "satellite_data" not in st.session_state:
        with st.spinner("Loading satellite data..."):
            st.session_state.satellite_data = st.session_state.data_manager.load_data(
                st.session_state.username,
                st.session_state.tier,
                st.session_state.location
            )

            # Analyze the data
            st.session_state.analysis_results = st.session_state.data_manager.analyze_temperature_data(
                st.session_state.satellite_data,
                st.session_state.tier
            )

    # Display data source information
    if st.session_state.satellite_data.get("data_source") == "mock":
        st.info("Note: Using simulated data for demonstration purposes.")

    # Tabs for different analysis views
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Detailed Analysis", "Maps", "Reports"])

    # Summary tab - available to all tiers
    with tab1:
        st.subheader("Weather Data Summary")

        # Basic tier: Temperature charts
        st.plotly_chart(st.session_state.analysis_results["min_max_temp_chart"])

        # Monthly rainfall chart
        st.plotly_chart(st.session_state.analysis_results["monthly_rain_chart"])

        # Key findings section
        st.subheader("Key Findings")

        # Get data for calculations
        df = st.session_state.satellite_data["current_data"]

        # Display basic metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Average Temperature", f"{df['temp'].mean():.1f}°C")
            st.metric("Total Rainfall", f"{df['precip'].sum():.1f}mm")

        with col2:
            st.metric("Rainy Days", f"{len(df[df['precip'] > 0])}")
            st.metric("Longest Dry Period", f"{st.session_state.analysis_results['longest_dry_period']} days")

        # Show alerts for premium users
        if st.session_state.tier == "premium" and "weather_alerts" in st.session_state.satellite_data:
            st.subheader("⚠️ Weather Alerts")

            for alert in st.session_state.satellite_data["weather_alerts"]:
                severity_color = "red" if alert["severity"] == "High" else "orange" if alert[
                                                                                           "severity"] == "Medium" else "blue"
                st.warning(f"**{alert['type']}** ({alert['severity']}): {alert['message']}")

    # Detailed Analysis tab
    with tab2:
        st.subheader("Temperature Analysis")

        # Soil temperature chart (basic)
        st.plotly_chart(st.session_state.analysis_results["soil_temp_chart"])

        # Rainy days chart (basic)
        st.plotly_chart(st.session_state.analysis_results["rainy_days_chart"])

        # Year-to-year comparison (standard and premium)
        if feature_available(st.session_state.tier, "standard"):
            if st.session_state.satellite_data["comparison_available"]:
                st.subheader("Year-to-Year Comparison")
                st.plotly_chart(st.session_state.analysis_results["temp_comparison_chart"])
                st.plotly_chart(st.session_state.analysis_results["rain_comparison_chart"])

                # Heat stress analysis
                if "heat_stress_chart" in st.session_state.analysis_results:
                    st.subheader("Heat Stress Analysis")
                    st.plotly_chart(st.session_state.analysis_results["heat_stress_chart"])
            else:
                st.info("Year-to-year comparison data not available for this location.")
        else:
            st.warning("🔒 Year-to-year comparison requires Standard or Premium tier.")

        # Premium features
        if feature_available(st.session_state.tier, "premium"):
            # LST comparison
            if "lst_comparison_chart" in st.session_state.analysis_results:
                st.subheader("Land Surface Temperature Analysis")
                st.plotly_chart(st.session_state.analysis_results["lst_comparison_chart"])

            # Weather forecast
            if "forecast_temp_chart" in st.session_state.analysis_results:
                st.subheader("30-Day Weather Forecast")
                st.plotly_chart(st.session_state.analysis_results["forecast_temp_chart"])
                st.plotly_chart(st.session_state.analysis_results["forecast_rain_chart"])

                # Crop-specific analysis
                st.subheader("Crop Impact Analysis")

                crop_options = ["Wheat", "Corn", "Rice", "Soybeans", "Potatoes"]
                selected_crop = st.selectbox("Select crop type:", crop_options)

                # Generate crop recommendations
                crop_recommendations = st.session_state.data_manager.get_crop_recommendations(
                    st.session_state.satellite_data,
                    selected_crop
                )

                st.subheader(f"{selected_crop} Recommendations")
                if crop_recommendations:
                    for rec in crop_recommendations:
                        st.write(f"• {rec}")
                else:
                    st.write("No specific recommendations available for this crop and conditions.")
        else:
            st.warning("🔒 Advanced analysis features require Premium tier.")

    # Maps tab
    with tab3:
        st.subheader("Spatial Analysis")

        # Get location coordinates
        lat = st.session_state.satellite_data["location"]["lat"]
        lon = st.session_state.satellite_data["location"]["lon"]

        # Create base map centered on the selected location
        m = folium.Map(location=[lat, lon], zoom_start=10)

        # Add marker for selected point
        folium.Marker(
            [lat, lon],
            popup="Selected Location",
            tooltip="Analysis Center Point"
        ).add_to(m)

        # Add circle representing analysis area
        folium.Circle(
            radius=5000,  # 5km radius
            location=[lat, lon],
            color="blue",
            fill=True,
            fill_opacity=0.2
        ).add_to(m)

        # Display map
        st_data = st_folium(m, width=700, height=400)

        # Advanced maps for standard and premium tiers
        if feature_available(st.session_state.tier, "standard"):
            st.subheader("Temperature Heatmap")

            # Create heatmap data
            df = st.session_state.satellite_data["current_data"]

            # Generate points around the center for heatmap visualization
            num_points = 200
            radius = 0.1  # Roughly 10km
            heat_data = []

            for _ in range(num_points):
                # Random point within radius
                angle = random.uniform(0, 2 * 3.14159)
                distance = random.uniform(0, radius)
                dlat = distance * math.cos(angle)
                dlon = distance * math.sin(angle)

                point_lat = lat + dlat
                point_lon = lon + dlon

                # Temperature value (weighted by distance from center)
                temp_factor = 1 - (distance / radius) ** 0.5
                temp_value = df["temp"].mean() * temp_factor + random.uniform(-2, 2)

                heat_data.append([point_lat, point_lon, temp_value])

            # Create heatmap
            m2 = folium.Map(location=[lat, lon], zoom_start=10)
            HeatMap(heat_data).add_to(m2)

            # Display heatmap
            st_folium(m2, width=700, height=400)
        else:
            st.warning("🔒 Advanced map visualizations require Standard or Premium tier.")

        # Premium-specific visualizations
        if feature_available(st.session_state.tier, "premium"):
            st.subheader("Crop Suitability Map")

            # Create crop suitability map
            m3 = folium.Map(location=[lat, lon], zoom_start=10)

            # Add marker for selected point
            folium.Marker([lat, lon], popup="Selected Location").add_to(m3)

            # Generate crop suitability zones
            crop_options = ["Wheat", "Corn", "Rice", "Soybeans", "Potatoes"]
            selected_crop = st.selectbox("Select crop for suitability analysis:", crop_options, key="map_crop_select")

            # Generate concentric zones around center with different suitability
            zone_colors = ["green", "lightgreen", "yellow", "orange", "red"]
            zone_labels = ["Excellent", "Good", "Moderate", "Marginal", "Poor"]
            zone_radii = [1000, 2000, 3000, 4000, 5000]  # in meters

            for radius, color, label in zip(zone_radii, zone_colors, zone_labels):
                folium.Circle(
                    radius=radius,
                    location=[lat, lon],
                    color=color,
                    fill=True,
                    fill_opacity=0.2,
                    tooltip=f"{label} Suitability for {selected_crop}"
                ).add_to(m3)

            # Add legend as a custom HTML
            legend_html = """
            <div style="position: fixed; bottom: 50px; left: 50px; background-color: white; 
                        border: 2px solid grey; z-index: 9999; padding: 10px;">
                <h4>Crop Suitability</h4>
                <p><i style="background: green; width: 15px; height: 15px; display: inline-block;"></i> Excellent</p>
                <p><i style="background: lightgreen; width: 15px; height: 15px; display: inline-block;"></i> Good</p>
                <p><i style="background: yellow; width: 15px; height: 15px; display: inline-block;"></i> Moderate</p>
                <p><i style="background: orange; width: 15px; height: 15px; display: inline-block;"></i> Marginal</p>
                <p><i style="background: red; width: 15px; height: 15px; display: inline-block;"></i> Poor</p>
            </div>
            """
            m3.get_root().html.add_child(folium.Element(legend_html))

            # Display crop suitability map
            st_folium(m3, width=700, height=400)
        else:
            st.warning("🔒 Crop suitability analysis requires Premium tier.")

    # Reports tab
    with tab4:
        st.subheader("Report Generation")

        # Basic summary for all tiers
        st.write("### Basic Summary")
        st.write(
            f"Analysis period: {st.session_state.satellite_data['dates']['start']} to {st.session_state.satellite_data['dates']['end']}")

        df = st.session_state.satellite_data["current_data"]
        st.write(f"Average temperature: {df['temp'].mean():.1f}°C")
        st.write(f"Temperature range: {df['tempmin'].min():.1f}°C to {df['tempmax'].max():.1f}°C")
        st.write(f"Total rainfall: {df['precip'].sum():.1f}mm")
        st.write(f"Number of rainy days: {len(df[df['precip'] > 0])}")

        # PDF export for standard and premium tiers
        if feature_available(st.session_state.tier, "standard"):
            st.write("### PDF Report")
            st.write("Generate a comprehensive PDF report with all analysis data and recommendations.")

            if st.button("Generate PDF Report"):
                with st.spinner("Generating PDF report..."):
                    pdf_data = st.session_state.data_manager.create_pdf_report(
                        st.session_state.satellite_data,
                        st.session_state.analysis_results,
                        st.session_state.analysis_name
                    )

                    # Create download link
                    b64_pdf = base64.b64encode(pdf_data).decode()
                    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{st.session_state.analysis_name}_report.pdf">Download PDF Report</a>'
                    st.markdown(href, unsafe_allow_html=True)
        else:
            st.warning("🔒 PDF report generation requires Standard or Premium tier.")

        # Expert recommendations for premium tier
        if feature_available(st.session_state.tier, "premium"):
            st.write("### Expert Recommendations")

            crop_options = ["Wheat", "Corn", "Rice", "Soybeans", "Potatoes"]
            selected_crop = st.selectbox("Select crop for expert recommendations:", crop_options,
                                         key="report_crop_select")

            # Display expert recommendations
            st.info(f"Expert recommendations for {selected_crop}:")

            crop_recommendations = st.session_state.data_manager.get_crop_recommendations(
                st.session_state.satellite_data,
                selected_crop
            )

            for rec in crop_recommendations:
                st.write(f"• {rec}")

            # AI Assistant option
            st.write("### AI Agronom Assistant")
            st.write("Premium tier users can ask specific questions about their crops and conditions.")

            user_question = st.text_input("Ask a question about your crop:")
            if st.button("Get Answer") and user_question:
                # Simulate AI response
                responses = [
                    f"Based on the current conditions for {selected_crop}, I recommend adjusting irrigation to maintain optimal soil moisture.",
                    f"The recent temperature patterns indicate potential {selected_crop} stress. Consider applying protective measures.",
                    f"Your {selected_crop} may benefit from additional nutrients based on the current growth stage and soil conditions.",
                    f"Based on the weather forecast, the optimal planting time for {selected_crop} would be in approximately 7-10 days.",
                    f"The current conditions show moderate risk of disease pressure for {selected_crop}. Consider preventative fungicide application."
                ]

                st.write(f"**AI Agronom Assistant:** {random.choice(responses)}")
        else:
            st.warning("🔒 Expert recommendations require Premium tier.")

    # Navigation buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Change Location"):
            st.session_state.page = "location"
            # Clear analysis data
            if "satellite_data" in st.session_state:
                del st.session_state.satellite_data
            if "analysis_results" in st.session_state:
                del st.session_state.analysis_results
            st.rerun()

    with col2:
        if st.button("Upgrade Plan"):
            st.session_state.page = "upgrade"
            st.rerun()

    with col3:
        if st.button("Logout"):
            # Clear session state
            for key in ["authenticated", "username", "tier", "satellite_data", "analysis_results", "data_manager"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.page = "welcome"
            st.rerun()