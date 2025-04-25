# Import the necessary libraries
import streamlit as st
import folium
import numpy as np
import pandas as pd
from streamlit_folium import st_folium
from folium.plugins import Draw, HeatMap
import requests
import json
import os
import datetime
from branca.colormap import LinearColormap
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import base64
from fpdf import FPDF
import matplotlib.pyplot as plt
import random

# Google Maps API Key
GOOGLE_MAPS_API_KEY = "AIzaSyBW1YE7uSlLvYFrpwXSsljEJU_dTVQFrG0"  # Replace with your actual API key


# Function to check if feature is available for current tier
def feature_available(feature_tier):
    """Check if a feature is available for the current user tier"""
    tier_levels = {"basic": 1, "standard": 2, "premium": 3}
    user_tier_level = tier_levels.get(st.session_state.tier, 0)
    required_tier_level = tier_levels.get(feature_tier, 3)

    return user_tier_level >= required_tier_level


# Function to show locked feature message
def show_locked_feature(required_tier):
    st.warning(f"⚠️ This feature requires {required_tier.title()} tier. Please upgrade your subscription to access it.")
    if st.button("Upgrade Now"):
        st.session_state.page = "upgrade"
        st.rerun()


# Funcție pentru a obține coordonatele localității
def get_location_coordinates(city_name):
    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": city_name,
        "key": GOOGLE_MAPS_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()

        if "results" in data and len(data["results"]) > 0:
            location = data["results"][0]["geometry"]["location"]
            lat, lon = location["lat"], location["lng"]
            return lat, lon
        else:
            st.error("⚠️ Localitate invalidă sau serverul nu a returnat date corecte.")
            return None

    except Exception as e:
        st.error(f"⚠️ Eroare: {e}")
        return None


# Generate sample temperature data
def generate_temperature_data(months=3):
    """Generate sample temperature data for the specified number of months"""
    today = datetime.date.today()

    # Generate daily data
    dates = []
    for i in range(months * 30, 0, -1):
        date = today - datetime.timedelta(days=i)
        dates.append(date)

    # Generate min and max temperatures
    min_temps = [random.uniform(5, 15) for _ in range(len(dates))]
    max_temps = [t + random.uniform(5, 15) for t in min_temps]

    # Generate soil temperatures
    soil_temps = [t - random.uniform(2, 5) for t in min_temps]

    # Generate rainfall data (binary: rain or no rain)
    rainfall = [random.randint(0, 10) for _ in range(len(dates))]

    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'min_temp': min_temps,
        'max_temp': max_temps,
        'soil_temp': soil_temps,
        'rainfall_mm': rainfall
    })

    return df


# Function to generate PDF report
def generate_pdf_report(risk_data, polygon_coordinates, city_name):
    """Generate a PDF report of risk assessment"""
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Risk Assessment Report", ln=True, align="C")
    pdf.ln(5)

    # Location info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Location: {city_name}", ln=True)
    pdf.cell(0, 10, f"Report generated on: {datetime.date.today().strftime('%d-%m-%Y')}", ln=True)
    pdf.ln(5)

    # Risk summary
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Risk Summary", ln=True)
    pdf.set_font("Arial", "", 10)

    risk_types = ["Overall Risk", "Flood Risk", "Drought Risk", "Water Sources", "Extreme Temperatures"]
    risk_values = [0.45, 0.38, 0.62, 0.31, 0.57]  # Example values

    for i, risk_type in enumerate(risk_types):
        pdf.cell(80, 10, f"{risk_type}:", 0)
        pdf.cell(0, 10, f"{risk_values[i]:.2f}", 0, ln=True)

    pdf.ln(5)

    # Weather data summary
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Weather Data Summary", ln=True)

    # Add recommendations based on tier
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Recommendations", ln=True)
    pdf.set_font("Arial", "", 10)

    recommendations = [
        "Monitor soil moisture levels regularly.",
        "Consider implementing irrigation system for dry periods.",
        "Plant drought-resistant crops in areas with high drought risk."
    ]

    for rec in recommendations:
        pdf.cell(0, 10, f"• {rec}", ln=True)

    # Save the PDF to a BytesIO object
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)

    return pdf_output


# Function to find longest drought period
def find_longest_drought(df):
    """Find the longest period without rain in the dataset"""
    drought_periods = []
    current_drought = 0

    for rain in df['rainfall_mm'].values:
        if rain < 1:  # Less than 1mm is considered no rain
            current_drought += 1
        else:
            if current_drought > 0:
                drought_periods.append(current_drought)
            current_drought = 0

    # Add the last drought period if it's ongoing
    if current_drought > 0:
        drought_periods.append(current_drought)

    return max(drought_periods) if drought_periods else 0


# Generate or load risk data
def generate_risk_data_if_needed():
    """Generate or load risk data for the selected polygon"""
    if not os.path.exists("risk_data.json"):
        if "selected_polygon" in st.session_state:
            try:
                # Create sample risk data
                risk_data = {
                    "overall_risk": [],
                    "flood_risk": [],
                    "drought_risk": [],
                    "water_source_risk": [],
                    "temperature_risk": []
                }

                # Generate points within the polygon
                for _ in range(100):
                    # Generate random points within bounding box
                    lats = [p[1] for p in st.session_state.selected_polygon]
                    lons = [p[0] for p in st.session_state.selected_polygon]

                    min_lat, max_lat = min(lats), max(lats)
                    min_lon, max_lon = min(lons), max(lons)

                    lat = min_lat + (max_lat - min_lat) * random.random()
                    lon = min_lon + (max_lon - min_lon) * random.random()

                    # Generate risk levels for each type
                    for risk_type in risk_data:
                        risk_level = random.random()  # 0 to 1
                        risk_data[risk_type].append({
                            "coordinates": [lon, lat],
                            "risk_level": risk_level
                        })

                # Save data to file
                with open("risk_data.json", "w") as f:
                    json.dump(risk_data, f)

                # Create CSV files
                all_data = []
                for risk_type in risk_data:
                    df = pd.DataFrame(risk_data[risk_type])
                    df['risk_type'] = risk_type
                    df.to_csv(f"{risk_type}.csv", index=False)
                    all_data.append(df)

                # Combine all data
                combined_df = pd.concat(all_data)
                combined_df.to_csv("all_risk_data.csv", index=False)

                return risk_data
            except Exception as e:
                st.error(f"Error generating risk data: {e}")
                return None
    else:
        try:
            with open("risk_data.json", "r") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading risk data: {e}")
            return None
    return None


def get_risk_category(risk_level):
    """Convert numeric risk level to category"""
    if risk_level < 0.2:
        return "foarte scăzut"
    elif risk_level < 0.4:
        return "scăzut"
    elif risk_level < 0.6:
        return "moderat"
    elif risk_level < 0.8:
        return "ridicat"
    else:
        return "foarte ridicat"


# Location page
def location_page():
    st.title("🏙️ Alege Localitatea")

    # Display user tier info
    tier_info = {
        "basic": "Basic (3-month data)",
        "standard": "Standard (12-month data)",
        "premium": "Premium (Complete + Forecasts)"
    }

    st.info(f"Current Plan: **{tier_info.get(st.session_state.tier, 'Basic')}**")

    # Input pentru localitate
    city_name = st.text_input("Introdu numele localității:")

    if st.button("Mergi la Hartă"):
        if city_name:
            coordinates = get_location_coordinates(city_name)
            if coordinates:
                st.session_state.city_name = city_name
                st.session_state.location = coordinates
                st.session_state.page = "map"
                st.rerun()
            else:
                st.error("Localitate invalidă. Încearcă din nou!")
        else:
            st.warning("Te rog să introduci o localitate.")


# Map page
def map_page():
    st.title("🌍 Selectează Poligonul")

    # Display user tier info
    tier_info = {
        "basic": "Basic (3-month data)",
        "standard": "Standard (12-month data)",
        "premium": "Premium (Complete + Forecasts)"
    }

    st.info(f"Current Plan: **{tier_info.get(st.session_state.tier, 'Basic')}**")

    # Check if we have coordinates
    if "location" not in st.session_state or st.session_state.location is None:
        st.warning("⚠️ Te rog să selectezi mai întâi o localitate!")
        if st.button("Înapoi la Selectare Localitate"):
            st.session_state.page = "location"
            st.rerun()
        return

    # Get coordinates
    lat, lon = st.session_state.location

    # Create map centered on location
    m = folium.Map(location=[lat, lon], zoom_start=13)

    # Add drawing plugin
    draw = Draw(
        draw_options={"polyline": False, "rectangle": False, "circle": False, "marker": False},
        edit_options={"edit": True, "remove": True}
    )
    draw.add_to(m)

    # Display interactive map
    map_data = st_folium(m, width=700, height=500)

    # Extract selected polygon
    if map_data and "all_drawings" in map_data:
        selected_polygons = map_data["all_drawings"]
        if selected_polygons:
            st.session_state.selected_polygon = selected_polygons[0]["geometry"]["coordinates"][0]
            st.success("✅ Poligon salvat!")

    # Display polygon coordinates if available
    if "selected_polygon" in st.session_state:
        st.write("🔹 **Coordonatele Poligonului:**")
        st.json(st.session_state.selected_polygon)

    # Reset button
    if st.button("Resetează Poligonul"):
        st.session_state.pop("selected_polygon", None)
        st.rerun()

    # Back button
    if st.button("Înapoi la Selectare Localitate"):
        st.session_state.page = "location"
        st.rerun()

    # Risk assessment button
    if st.button("Vezi zonele de Risc"):
        if "selected_polygon" in st.session_state:
            st.session_state.page = "analysis"
            st.rerun()
        else:
            st.warning("⚠️ Trebuie să selectezi un poligon înainte de a continua!")


# Risk analysis page
def risk_analysis_page():
    st.title("📊 Analiza Zonelor de Risc")

    # Display user tier info
    tier_info = {
        "basic": "Basic (Limited Analysis)",
        "standard": "Standard (Extended Analysis)",
        "premium": "Premium (Complete Analysis)"
    }

    st.info(f"Current Plan: **{tier_info.get(st.session_state.tier, 'Basic')}**")

    # Check if polygon exists
    if "selected_polygon" not in st.session_state:
        st.warning("⚠️ Trebuie să selectezi un poligon înainte de a continua!")
        if st.button("Înapoi la Hartă"):
            st.session_state.page = "map"
            st.rerun()
        return

    # Generate or load risk data
    with st.spinner("Se încarcă datele de risc..."):
        risk_data = generate_risk_data_if_needed()

    if not risk_data:
        st.error("Nu s-au putut încărca datele de risc!")
        if st.button("Înapoi la Hartă"):
            st.session_state.page = "map"
            st.rerun()
        return

    # Create tabs for different visualizations
    tabs = st.tabs(["Overall Risk", "Weather Data", "Flood Risk", "Drought Risk", "Advanced Analysis"])

    # Color maps for each risk type
    color_maps = {
        "Overall Risk": LinearColormap(['green', 'yellow', 'orange', 'red'], vmin=0, vmax=1),
        "Flood Risk": LinearColormap(['lightblue', 'blue', 'darkblue', 'navy'], vmin=0, vmax=1),
        "Drought Risk": LinearColormap(['yellow', 'orange', 'orangered', 'darkred'], vmin=0, vmax=1),
        "Water Sources": LinearColormap(['lightgreen', 'green', 'darkgreen', 'forestgreen'], vmin=0, vmax=1),
        "Extreme Temperatures": LinearColormap(['lavender', 'violet', 'purple', 'indigo'], vmin=0, vmax=1)
    }

    # Overall Risk tab
    with tabs[0]:
        st.subheader("Overall Risk Assessment")

        # Create base map
        m = folium.Map(location=st.session_state.location, zoom_start=13)

        # Add polygon boundary
        folium.Polygon(
            locations=st.session_state.selected_polygon,
            color='gray',
            weight=2,
            fill=False,
        ).add_to(m)

        # Get risk data
        tab_risk_data = risk_data["overall_risk"]

        # Create heatmap data
        heat_data = []
        for point in tab_risk_data:
            lat, lon = point['coordinates'][1], point['coordinates'][0]
            risk_level = point['risk_level']
            heat_data.append([lat, lon, risk_level])

            # Add heatmap to map
            HeatMap(
                heat_data,
                radius=15,
                gradient={0.0: 'transparent', 0.2: color_maps["Overall Risk"].rgb_hex_str(0.2),
                          0.5: color_maps["Overall Risk"].rgb_hex_str(0.5),
                          0.8: color_maps["Overall Risk"].rgb_hex_str(0.8),
                          1.0: color_maps["Overall Risk"].rgb_hex_str(1.0)},
                min_opacity=0.3,
                max_opacity=0.9,
                blur=10
            ).add_to(m)

            # Add legend
            color_maps["Overall Risk"].caption = 'Overall Risk Level'
            m.add_child(color_maps["Overall Risk"])

            # Display the map
            st_folium(m, width=700, height=500)

            # Add statistics
            risk_levels = [point['risk_level'] for point in tab_risk_data]
            avg_risk = sum(risk_levels) / len(risk_levels)
            max_risk = max(risk_levels)
            min_risk = min(risk_levels)

            st.write(f"📊 **Risk Statistics:**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Average Risk", f"{avg_risk:.2f}")
            col2.metric("Maximum Risk", f"{max_risk:.2f}")
            col3.metric("Minimum Risk", f"{min_risk:.2f}")

            # General analysis
            st.write("🔍 **General Risk Analysis:**")
            st.write(f"The selected area shows a **{get_risk_category(avg_risk)}** overall risk level.")

            if avg_risk > 0.7:
                st.warning("⚠️ This area shows high risk and requires special attention!")
            elif avg_risk > 0.4:
                st.info("ℹ️ This area shows moderate risk and should be monitored.")
            else:
                st.success("✅ This area shows low risk.")

            # Weather Data tab
        with tabs[1]:
            st.subheader("Weather Data Analysis")

            # Get appropriate data based on tier
            months_data = 3  # Default for Basic tier

            if feature_available("standard"):
                months_data = 12
            elif feature_available("premium"):
                months_data = 24

            # Generate sample weather data
            weather_data = generate_temperature_data(months=months_data)

            # Show temperature graph
            st.write("🌡️ **Temperature Trends**")

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=weather_data['date'], y=weather_data['max_temp'], name='Max Temp',
                                     line=dict(color='crimson')))
            fig.add_trace(go.Scatter(x=weather_data['date'], y=weather_data['min_temp'], name='Min Temp',
                                     line=dict(color='royalblue')))

            # Add soil temperature if available (all tiers)
            fig.add_trace(go.Scatter(x=weather_data['date'], y=weather_data['soil_temp'], name='Soil Temp',
                                     line=dict(color='sienna', dash='dot')))

            fig.update_layout(
                title='Temperature Trends',
                xaxis_title='Date',
                yaxis_title='Temperature (°C)',
                legend_title='Temperature Type',
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)

            # Show rainfall data
            st.write("🌧️ **Rainfall Analysis**")

            # Calculate monthly rainfall
            weather_data['month'] = weather_data['date'].dt.strftime('%Y-%m')
            monthly_rain = weather_data.groupby('month')['rainfall_mm'].sum().reset_index()
            monthly_rain_days = weather_data.groupby('month').apply(lambda x: (x['rainfall_mm'] > 0).sum()).reset_index(
                name='rain_days')
            monthly_stats = pd.merge(monthly_rain, monthly_rain_days, on='month')

            # Display rainfall bar chart
            fig = go.Figure()
            fig.add_trace(go.Bar(x=monthly_stats['month'], y=monthly_stats['rainfall_mm'], name='Total Rainfall (mm)'))
            fig.add_trace(go.Bar(x=monthly_stats['month'], y=monthly_stats['rain_days'], name='Days with Rain'))

            fig.update_layout(
                title='Monthly Rainfall Statistics',
                xaxis_title='Month',
                yaxis_title='Value',
                barmode='group',
                legend_title='Measurement'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Find longest drought period
            longest_drought = find_longest_drought(weather_data)
            st.write(f"**Longest period without rain:** {longest_drought} days")

            # Year-to-year comparison (only for Standard and Premium)
            if feature_available("standard"):
                st.write("📅 **Year-to-Year Comparison**")

                # Create a toggle for different comparison views
                comparison_type = st.selectbox(
                    "Select comparison type:",
                    ["Temperature Comparison", "Rainfall Comparison"]
                )

                # For demo purposes, we'll just show a sample comparison chart
                fig = go.Figure()

                # Sample data for last year
                last_year_data = pd.DataFrame({
                    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                    'temp_last_year': [5, 7, 12, 15, 20, 24, 26, 25, 20, 15, 10, 7],
                    'temp_current_year': [6, 8, 11, 16, 21, 25, 27, 26, 21, 16, 11, 8],
                    'rain_last_year': [40, 35, 30, 50, 60, 30, 20, 25, 40, 70, 60, 50],
                    'rain_current_year': [45, 30, 40, 55, 50, 25, 15, 20, 45, 75, 65, 45]
                })

                if comparison_type == "Temperature Comparison":
                    fig.add_trace(
                        go.Bar(x=last_year_data['month'], y=last_year_data['temp_last_year'], name='Last Year'))
                    fig.add_trace(
                        go.Bar(x=last_year_data['month'], y=last_year_data['temp_current_year'], name='Current Year'))
                    fig.update_layout(title='Average Monthly Temperature Comparison', yaxis_title='Temperature (°C)')
                else:
                    fig.add_trace(
                        go.Bar(x=last_year_data['month'], y=last_year_data['rain_last_year'], name='Last Year'))
                    fig.add_trace(
                        go.Bar(x=last_year_data['month'], y=last_year_data['rain_current_year'], name='Current Year'))
                    fig.update_layout(title='Monthly Rainfall Comparison', yaxis_title='Rainfall (mm)')

                fig.update_layout(barmode='group', xaxis_title='Month')
                st.plotly_chart(fig, use_container_width=True)
            else:
                show_locked_feature("standard")

            # Flood Risk tab
        with tabs[2]:
            st.subheader("Flood Risk Analysis")

            # Create base map
            m = folium.Map(location=st.session_state.location, zoom_start=13)

            # Add polygon boundary
            folium.Polygon(
                locations=st.session_state.selected_polygon,
                color='gray',
                weight=2,
                fill=False,
            ).add_to(m)

            # Get risk data
            tab_risk_data = risk_data["flood_risk"]

            # Create heatmap data
            heat_data = []
            for point in tab_risk_data:
                lat, lon = point['coordinates'][1], point['coordinates'][0]
                risk_level = point['risk_level']
                heat_data.append([lat, lon, risk_level])

            # Add heatmap to map
            HeatMap(
                heat_data,
                radius=15,
                gradient={0.0: 'transparent', 0.2: color_maps["Flood Risk"].rgb_hex_str(0.2),
                          0.5: color_maps["Flood Risk"].rgb_hex_str(0.5),
                          0.8: color_maps["Flood Risk"].rgb_hex_str(0.8),
                          1.0: color_maps["Flood Risk"].rgb_hex_str(1.0)},
                min_opacity=0.3,
                max_opacity=0.9,
                blur=10
            ).add_to(m)

            # Add legend
            color_maps["Flood Risk"].caption = 'Flood Risk Level'
            m.add_child(color_maps["Flood Risk"])

            # Display the map
            st_folium(m, width=700, height=500)

            # Add statistics
            risk_levels = [point['risk_level'] for point in tab_risk_data]
            avg_risk = sum(risk_levels) / len(risk_levels)
            max_risk = max(risk_levels)
            min_risk = min(risk_levels)

            st.write(f"📊 **Flood Risk Statistics:**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Average Risk", f"{avg_risk:.2f}")
            col2.metric("Maximum Risk", f"{max_risk:.2f}")
            col3.metric("Minimum Risk", f"{min_risk:.2f}")

            # Analysis
            st.write("🔍 **Flood Risk Analysis:**")
            st.write(f"This area shows a **{get_risk_category(avg_risk)}** flood risk level.")

            if avg_risk > 0.7:
                st.warning("⚠️ High flood risk! Area with high probability of flooding.")
                st.write("Recommendations:")
                st.write("- Construction or reinforcement of dikes and drainage systems")
                st.write("- Implementation of an early warning system for floods")
                st.write("- Avoiding construction in low-lying areas")
            elif avg_risk > 0.4:
                st.info("ℹ️ Moderate flood risk. We recommend prevention measures.")
                st.write("Recommendations:")
                st.write("- Checking and maintaining drainage systems")
                st.write("- Evacuation plans in case of floods")
            else:
                st.success("✅ Low flood risk in this area.")

            # Drought Risk tab
        with tabs[3]:
            st.subheader("Drought Risk Analysis")

            # Create base map
            m = folium.Map(location=st.session_state.location, zoom_start=13)

            # Add polygon boundary
            folium.Polygon(
                locations=st.session_state.selected_polygon,
                color='gray',
                weight=2,
                fill=False,
            ).add_to(m)

            # Get risk data
            tab_risk_data = risk_data["drought_risk"]

            # Create heatmap data
            heat_data = []
            for point in tab_risk_data:
                lat, lon = point['coordinates'][1], point['coordinates'][0]
                risk_level = point['risk_level']
                heat_data.append([lat, lon, risk_level])

            # Add heatmap to map
            HeatMap(
                heat_data,
                radius=15,
                gradient={0.0: 'transparent', 0.2: color_maps["Drought Risk"].rgb_hex_str(0.2),
                          0.5: color_maps["Drought Risk"].rgb_hex_str(0.5),
                          0.8: color_maps["Drought Risk"].rgb_hex_str(0.8),
                          1.0: color_maps["Drought Risk"].rgb_hex_str(1.0)},
                min_opacity=0.3,
                max_opacity=0.9,
                blur=10
            ).add_to(m)

            # Add legend
            color_maps["Drought Risk"].caption = 'Drought Risk Level'
            m.add_child(color_maps["Drought Risk"])

            # Display the map
            st_folium(m, width=700, height=500)

            # Add statistics
            risk_levels = [point['risk_level'] for point in tab_risk_data]
            avg_risk = sum(risk_levels) / len(risk_levels)
            max_risk = max(risk_levels)
            min_risk = min(risk_levels)

            st.write(f"📊 **Drought Risk Statistics:**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Average Risk", f"{avg_risk:.2f}")
            col2.metric("Maximum Risk", f"{max_risk:.2f}")
            col3.metric("Minimum Risk", f"{min_risk:.2f}")

            # Analysis
            st.write("🔍 **Drought Risk Analysis:**")
            st.write(f"This area shows a **{get_risk_category(avg_risk)}** drought risk level.")

            if avg_risk > 0.7:
                st.warning("⚠️ High drought risk! Area with potential large water deficit.")
                st.write("Recommendations:")
                st.write("- Implementation of efficient irrigation systems")
                st.write("- Use of drought-resistant plant species")
                st.write("- Rainwater collection and storage systems")
            elif avg_risk > 0.4:
                st.info("ℹ️ Moderate drought risk.")
                st.write("Recommendations:")
                st.write("- Rational use of water resources")
                st.write("- Energy efficient irrigation systems")
            else:
                st.success("✅ Low drought risk in this area.")

            # Advanced Analysis tab (Premium only)
        with tabs[4]:
            st.subheader("Advanced Analysis")

            if feature_available("premium"):
                # Weather forecast integration
                st.write("🌦️ **Weather Forecast Integration**")

                # For demo, we'll create a simple forecast
                forecast_days = 30
                dates = [datetime.date.today() + datetime.timedelta(days=i) for i in range(forecast_days)]
                temp_highs = [random.uniform(15, 30) for _ in range(forecast_days)]
                temp_lows = [t - random.uniform(5, 10) for t in temp_highs]
                precip_prob = [random.uniform(0, 1) for _ in range(forecast_days)]

                forecast_df = pd.DataFrame({
                    'date': dates,
                    'temp_high': temp_highs,
                    'temp_low': temp_lows,
                    'precipitation_probability': precip_prob
                })

                # Weather forecast chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=forecast_df['date'], y=forecast_df['temp_high'], name='High Temp',
                                         line=dict(color='crimson')))
                fig.add_trace(go.Scatter(x=forecast_df['date'], y=forecast_df['temp_low'], name='Low Temp',
                                         line=dict(color='royalblue')))

                # Add precipitation probability
                fig.add_trace(go.Bar(x=forecast_df['date'], y=forecast_df['precipitation_probability'],
                                     name='Precipitation Probability',
                                     marker_color='lightblue',
                                     opacity=0.7,
                                     yaxis='y2'))

                fig.update_layout(
                    title='30-Day Weather Forecast',
                    xaxis_title='Date',
                    yaxis_title='Temperature (°C)',
                    legend_title='Weather Data',
                    hovermode="x unified",
                    yaxis2=dict(
                        title='Precipitation Probability',
                        titlefont=dict(color='lightblue'),
                        tickfont=dict(color='lightblue'),
                        overlaying='y',
                        side='right',
                        range=[0, 1]
                    )
                )
                st.plotly_chart(fig, use_container_width=True)

                # Crop specific impact analysis
                st.write("🌾 **Crop-Specific Impact Analysis**")

                crops = ["Wheat", "Corn", "Potatoes", "Soybeans", "Sunflower"]
                selected_crop = st.selectbox("Select crop type:", crops)

                # Generate crop impact data
                impact_data = {
                    "Temperature Stress": random.uniform(0.2, 0.8),
                    "Drought Impact": random.uniform(0.2, 0.8),
                    "Flood Impact": random.uniform(0.2, 0.8),
                    "Overall Yield Risk": random.uniform(0.2, 0.8)
                }

                # Create gauge charts for each impact factor
                col1, col2 = st.columns(2)

                with col1:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=impact_data["Temperature Stress"],
                        title={'text': "Temperature Stress"},
                        gauge={
                            'axis': {'range': [0, 1]},
                            'bar': {'color': "darkred"},
                            'steps': [
                                {'range': [0, 0.3], 'color': "green"},
                                {'range': [0.3, 0.7], 'color': "orange"},
                                {'range': [0.7, 1], 'color': "red"}
                            ]
                        }
                    ))
                    st.plotly_chart(fig, use_container_width=True)

                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=impact_data["Drought Impact"],
                        title={'text': "Drought Impact"},
                        gauge={
                            'axis': {'range': [0, 1]},
                            'bar': {'color': "darkorange"},
                            'steps': [
                                {'range': [0, 0.3], 'color': "green"},
                                {'range': [0.3, 0.7], 'color': "orange"},
                                {'range': [0.7, 1], 'color': "red"}
                            ]
                        }
                    ))
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=impact_data["Flood Impact"],
                        title={'text': "Flood Impact"},
                        gauge={
                            'axis': {'range': [0, 1]},
                            'bar': {'color': "darkblue"},
                            'steps': [
                                {'range': [0, 0.3], 'color': "green"},
                                {'range': [0.3, 0.7], 'color': "orange"},
                                {'range': [0.7, 1], 'color': "red"}
                            ]
                        }
                    ))
                    st.plotly_chart(fig, use_container_width=True)

                    fig = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=impact_data["Overall Yield Risk"],
                        title={'text': "Overall Yield Risk"},
                        gauge={
                            'axis': {'range': [0, 1]},
                            'bar': {'color': "darkgreen"},
                            'steps': [
                                {'range': [0, 0.3], 'color': "green"},
                                {'range': [0.3, 0.7], 'color': "orange"},
                                {'range': [0.7, 1], 'color': "red"}
                            ]
                        }
                    ))
                    st.plotly_chart(fig, use_container_width=True)

                # Personalized recommendations
                st.write("🔍 **Personalized Recommendations**")

                avg_impact = sum(impact_data.values()) / len(impact_data)

                if avg_impact > 0.6:
                    st.warning(f"⚠️ High risk for {selected_crop} cultivation in this area!")
                    st.write("Recommendations:")
                    st.write("- Consider alternative crops better suited for this climate")
                    st.write("- Implement advanced irrigation and drainage systems")
                    st.write("- Use resistant varieties adapted to stress conditions")
                    st.write("- Implement a comprehensive monitoring system")
                elif avg_impact > 0.3:
                    st.info(f"ℹ️ Moderate risk for {selected_crop} cultivation.")
                    st.write("Recommendations:")
                    st.write("- Regular monitoring of soil and climate conditions")
                    st.write("- Efficient water management")
                    st.write("- Consider crop rotation with more resistant varieties")
                else:
                    st.success(f"✅ Low risk for {selected_crop} cultivation in this area.")
                    st.write("Recommendations:")
                    st.write("- Standard monitoring and management practices")
                    st.write("- Optimize for maximum yield")

                # Expert consultation
                st.write("👨‍🌾 **Expert Consultation**")
                st.write(
                    "As a Premium user, you have access to expert consultation. Use the form below to send your questions:")

                expert_question = st.text_area("Enter your question for our agronomist or AI assistant:")
                if st.button("Send Question"):
                    st.success("Question sent! Our experts will respond within 24 hours.")
                    st.balloons()
            else:
                show_locked_feature("premium")

            # Option to download report (Standard and Premium only)
        st.subheader("📥 Export Report")

        if feature_available("standard"):
            if st.button("Generate PDF Report"):
                try:
                    # Generate PDF
                    pdf_report = generate_pdf_report(risk_data, st.session_state.selected_polygon,
                                                     st.session_state.city_name)

                    # Create download button
                    b64_pdf = base64.b64encode(pdf_report.read()).decode('utf-8')
                    href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="risk_assessment_report.pdf">Download PDF Report</a>'
                    st.markdown(href, unsafe_allow_html=True)

                    st.success("Report generated successfully!")
                except Exception as e:
                    st.error(f"Error generating report: {e}")
        else:
            if st.button("Export as PDF"):
                show_locked_feature("standard")

        # CSV export for everyone
        if os.path.exists("all_risk_data.csv"):
            with open("all_risk_data.csv", "rb") as file:
                btn = st.download_button(
                    label="Download CSV Data",
                    data=file,
                    file_name="risk_assessment_data.csv",
                    mime="text/csv",
                )

        # Add report generation timestamp
        if os.path.exists("risk_data.json"):
            file_timestamp = os.path.getmtime("risk_data.json")
            timestamp_str = datetime.datetime.fromtimestamp(file_timestamp).strftime('%d-%m-%Y %H:%M:%S')
            st.write(f"Report generated at: {timestamp_str}")

        # Navigation buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back to Map"):
                st.session_state.page = "map"
                st.rerun()
        with col2:
            if st.button("Generate New Data"):
                # Remove existing risk data files
                risk_keys = ["overall_risk", "flood_risk", "drought_risk", "water_source_risk", "temperature_risk"]
                for file in ["risk_data.json", "all_risk_data.csv"] + [f"{key}.csv" for key in risk_keys]:
                    if os.path.exists(file):
                        os.remove(file)
                st.rerun()