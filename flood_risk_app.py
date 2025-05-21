import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import sys
import importlib
import subprocess
import tempfile
import numpy as np
from io import StringIO

# Import the authentication modules
from auth import login_user, register_user, update_user_tier

# Import SatelliteDataManager from satellite_data_manager.py
from satellite_data_manager import SatelliteDataManager

# Page config
st.set_page_config(page_title="Flood & Drought Risk Assessment", page_icon="🌊", layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    .main-title {
        font-size: 3rem !important;
        color: #2E86C1;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .subtitle {
        font-size: 1.5rem !important;
        color: #5D6D7E;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    .stButton>button {
        background-color: #2E86C1;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #1A5276;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .prediction-card {
        background-color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .risk-high {
        color: #E74C3C;
        font-weight: bold;
    }
    .risk-medium {
        color: #F39C12;
        font-weight: bold;
    }
    .risk-low {
        color: #27AE60;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
for key in ["authenticated", "username", "tier", "page", "selected_location"]:
    if key not in st.session_state:
        if key == "authenticated":
            st.session_state[key] = False
        elif key == "page":
            st.session_state[key] = "welcome"
        else:
            st.session_state[key] = None

# Predefined locations
PREDEFINED_LOCATIONS = [
    {"name": "Cologne, Germany", "lat": 50.9375, "lon": 6.9603, "country": "Germany"},
    {"name": "Frankfurt, Germany", "lat": 50.1109, "lon": 8.6821, "country": "Germany"},
    {"name": "Passau, Germany", "lat": 48.5667, "lon": 13.4667, "country": "Germany"},
    {"name": "Koblenz, Germany", "lat": 50.3569, "lon": 7.5890, "country": "Germany"},
    {"name": "Würzburg, Germany", "lat": 49.7913, "lon": 9.9534, "country": "Germany"}
]


# Helper function to run the prediction script and get results
def run_prediction_for_location(lat, lon):
    """
    Simulate running the ExtractFilterFeatures.py script for a specific location
    and return the prediction results
    """
    # In a real implementation, you would modify the input parameters
    # for ExtractFilterFeatures.py based on the location and run it

    # For demo purposes, let's create sample predictions that match
    # the expected output format with location-specific variations

    # Create random but consistent predictions for each location
    np.random.seed(int(lat * 100 + lon * 10))  # Make it consistent for the same location

    # Base prediction values with some randomness
    flood_prob = np.random.beta(2, 5) if lat < 49.5 else np.random.beta(5, 2)
    drought_prob = np.random.beta(2, 5)

    # Determine labels based on probability thresholds
    flood_label = 1 if flood_prob > 0.5 else 0
    drought_label = 1 if drought_prob > 0.5 else 0

    # Create a single-row DataFrame with the prediction results
    results = pd.DataFrame({
        'lat': [lat],
        'lon': [lon],
        'flood_predicted_label': [flood_label],
        'flood_probability': [flood_prob],
        'drought_predicted_label': [drought_label],
        'drought_probability': [drought_prob]
    })

    return results


def run_predictions_for_nearby_areas(center_lat, center_lon, radius=0.5, num_points=5):
    """
    Generate predictions for points around the specified center coordinates
    """
    results_list = []

    # Add the center point
    center_result = run_prediction_for_location(center_lat, center_lon)
    results_list.append(center_result)

    # Generate points in a grid around the center
    for i in range(num_points - 1):
        # Create variations around the center point
        lat_offset = np.random.uniform(-radius, radius)
        lon_offset = np.random.uniform(-radius, radius)

        new_lat = round(center_lat + lat_offset, 5)
        new_lon = round(center_lon + lon_offset, 5)

        result = run_prediction_for_location(new_lat, new_lon)
        results_list.append(result)

    # Combine all results
    all_results = pd.concat(results_list, ignore_index=True)
    return all_results


def go_to_page(new_page):
    """Change the current page in the session state"""
    st.session_state.page = new_page
    st.rerun()


# Welcome page
def welcome_page():
    st.markdown('<h1 class="main-title">🌊 Flood & Drought Risk Assessment</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced environmental monitoring for disaster prevention</p>',
                unsafe_allow_html=True)

    # Hero image
    st.image("Free-Satellite-Imagery.jpg", use_column_width=True)

    # Brief intro
    st.markdown("""
    ### Welcome to the Flood & Drought Risk Assessment Platform

    Our platform uses satellite data to analyze environmental conditions and predict 
    potential risks of floods and droughts across different regions. By combining multiple 
    satellite data sources and advanced machine learning models, we provide actionable 
    insights for disaster prevention and planning.
    """)

    # Key features in three columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🛰️ Satellite Analysis")
        st.markdown("""
        - Multi-band satellite imagery
        - SAR and optical data fusion
        - Historical data comparison
        - High-precision risk assessment
        """)

    with col2:
        st.markdown("### 🌧️ Risk Prediction")
        st.markdown("""
        - ML-based flood prediction
        - Drought severity assessment
        - Interactive risk maps
        - Probability-based alerts
        """)

    with col3:
        st.markdown("### 📊 Data Visualization")
        st.markdown("""
        - Interactive heatmaps
        - Time-series analysis
        - Export capabilities
        - Decision support tools
        """)

    # Get started section
    st.markdown("---")
    st.markdown("### Get Started")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("Login"):
            st.session_state.page = "login"
            st.rerun()

    with col2:
        if st.button("Register"):
            st.session_state.page = "register"
            st.rerun()

    with col3:
        if st.button("Try Demo"):
            st.session_state.update(authenticated=True, username="demo_user", tier="basic", page="dashboard")
            st.rerun()


# Login page
def login_page():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("Login") and username and password:
            user = login_user(username, password)
            if user:
                st.session_state.update(authenticated=True, username=user["username"], tier=user["tier"],
                                        page="dashboard")
                st.rerun()
            else:
                st.error("Invalid username or password")

    with col2:
        if st.button("Back to Welcome"):
            st.session_state.page = "welcome"
            st.rerun()


# Registration page
def register_page():
    st.title("📝 Register")

    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    tier_options = ["basic", "standard", "premium"]
    selected_tier = st.selectbox("Choose Your Plan", tier_options)

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("Register"):
            if password != confirm_password:
                st.error("Passwords do not match")
            else:
                success, message = register_user(username, password, tier=selected_tier)
                if success:
                    st.success("Registration successful!")
                    st.session_state.update(authenticated=True, username=username, tier=selected_tier, page="dashboard")
                    st.rerun()
                else:
                    st.error(message)

    with col2:
        if st.button("Back to Welcome"):
            st.session_state.page = "welcome"
            st.rerun()


# Dashboard page
def dashboard_page():
    st.title(f"Dashboard: Flood & Drought Risk Assessment")

    # User info in sidebar
    st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
    st.sidebar.markdown(f"**Subscription:** {st.session_state.tier.capitalize()}")

    # Location selection
    st.subheader("Select a Location")

    # Create two tabs: Predefined Locations and Custom Location
    tab1, tab2 = st.tabs(["Predefined Locations", "Custom Location"])

    with tab1:
        # Create a selection for predefined locations
        location_names = [loc["name"] for loc in PREDEFINED_LOCATIONS]
        selected_name = st.selectbox("Choose a location:", location_names)

        # Find the selected location data
        selected_location = next((loc for loc in PREDEFINED_LOCATIONS if loc["name"] == selected_name), None)

        if selected_location:
            st.write(f"Selected: {selected_location['name']}, {selected_location['country']}")
            st.write(f"Coordinates: Lat {selected_location['lat']}, Lon {selected_location['lon']}")

            # Display a map with the selected location
            m = folium.Map(location=[selected_location['lat'], selected_location['lon']], zoom_start=10)
            folium.Marker(
                [selected_location['lat'], selected_location['lon']],
                popup=selected_location['name'],
                tooltip=selected_location['name']
            ).add_to(m)

            # Add a circle to represent the analysis area
            folium.Circle(
                radius=5000,  # 5km radius
                location=[selected_location['lat'], selected_location['lon']],
                color="blue",
                fill=True,
                fill_opacity=0.2
            ).add_to(m)

            # Display the map
            st_folium(m, width=700, height=400)

            # Save the selected location to session state
            st.session_state.selected_location = selected_location

            # Button to run analysis
            if st.button("Run Risk Analysis"):
                st.session_state.page = "analysis"
                st.rerun()

    with tab2:
        # Custom location input
        st.write("Enter custom coordinates:")

        col1, col2 = st.columns(2)
        with col1:
            custom_lat = st.number_input("Latitude", value=50.0, min_value=-90.0, max_value=90.0, format="%.4f")
        with col2:
            custom_lon = st.number_input("Longitude", value=8.0, min_value=-180.0, max_value=180.0, format="%.4f")

        custom_name = st.text_input("Location Name (optional)", value="Custom Location")

        # Display a map with the custom location
        m_custom = folium.Map(location=[custom_lat, custom_lon], zoom_start=10)
        folium.Marker(
            [custom_lat, custom_lon],
            popup=custom_name,
            tooltip=custom_name
        ).add_to(m_custom)

        # Add a circle to represent the analysis area
        folium.Circle(
            radius=5000,  # 5km radius
            location=[custom_lat, custom_lon],
            color="blue",
            fill=True,
            fill_opacity=0.2
        ).add_to(m_custom)

        # Display the map
        st_folium(m_custom, width=700, height=400)

        # Save the custom location to session state
        custom_location = {
            "name": custom_name,
            "lat": custom_lat,
            "lon": custom_lon,
            "country": "Unknown"
        }

        # Button to run analysis
        if st.button("Run Risk Analysis for Custom Location"):
            st.session_state.selected_location = custom_location
            st.session_state.page = "analysis"
            st.rerun()

    # Option to logout
    if st.sidebar.button("Logout"):
        for key in ["authenticated", "username", "tier", "selected_location"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.page = "welcome"
        st.rerun()


# Analysis page
def analysis_page():
    if "selected_location" not in st.session_state:
        st.error("No location selected. Please go back and select a location.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()
        return

    location = st.session_state.selected_location

    st.title(f"Risk Analysis for {location['name']}")

    # Display location info
    st.write(f"Coordinates: Lat {location['lat']}, Lon {location['lon']}")

    # Run prediction
    with st.spinner("Running prediction model..."):
        # Get predictions for the selected location and surrounding areas
        predictions = run_predictions_for_nearby_areas(location['lat'], location['lon'])

    # Show results in tabs
    tab1, tab2, tab3 = st.tabs(["Prediction Results", "Risk Map", "Detailed Analysis"])

    with tab1:
        st.subheader("Flood & Drought Prediction Results")

        # Display the prediction table
        st.dataframe(predictions.style.format({
            'lat': '{:.5f}',
            'lon': '{:.5f}',
            'flood_probability': '{:.6f}',
            'drought_probability': '{:.6f}'
        }))

        # Summary of predictions
        st.subheader("Risk Summary")

        col1, col2 = st.columns(2)

        with col1:
            # Flood risk summary
            flood_high_risk = (predictions['flood_probability'] > 0.7).sum()
            flood_medium_risk = ((predictions['flood_probability'] > 0.3) &
                                 (predictions['flood_probability'] <= 0.7)).sum()
            flood_low_risk = (predictions['flood_probability'] <= 0.3).sum()

            st.markdown("### Flood Risk")
            st.markdown(f"<span class='risk-high'>High Risk Areas:</span> {flood_high_risk}", unsafe_allow_html=True)
            st.markdown(f"<span class='risk-medium'>Medium Risk Areas:</span> {flood_medium_risk}",
                        unsafe_allow_html=True)
            st.markdown(f"<span class='risk-low'>Low Risk Areas:</span> {flood_low_risk}", unsafe_allow_html=True)

        with col2:
            # Drought risk summary
            drought_high_risk = (predictions['drought_probability'] > 0.7).sum()
            drought_medium_risk = ((predictions['drought_probability'] > 0.3) &
                                   (predictions['drought_probability'] <= 0.7)).sum()
            drought_low_risk = (predictions['drought_probability'] <= 0.3).sum()

            st.markdown("### Drought Risk")
            st.markdown(f"<span class='risk-high'>High Risk Areas:</span> {drought_high_risk}", unsafe_allow_html=True)
            st.markdown(f"<span class='risk-medium'>Medium Risk Areas:</span> {drought_medium_risk}",
                        unsafe_allow_html=True)
            st.markdown(f"<span class='risk-low'>Low Risk Areas:</span> {drought_low_risk}", unsafe_allow_html=True)

    with tab2:
        st.subheader("Risk Visualization Map")

        # Create a risk map using Folium
        risk_map = folium.Map(location=[location['lat'], location['lon']], zoom_start=10)

        # Add markers for each prediction point with color based on risk
        for i, row in predictions.iterrows():
            # Determine flood risk color
            if row['flood_probability'] > 0.7:
                flood_color = 'red'
                flood_risk = 'High'
            elif row['flood_probability'] > 0.3:
                flood_color = 'orange'
                flood_risk = 'Medium'
            else:
                flood_color = 'green'
                flood_risk = 'Low'

            # Determine drought risk color
            if row['drought_probability'] > 0.7:
                drought_color = 'red'
                drought_risk = 'High'
            elif row['drought_probability'] > 0.3:
                drought_color = 'orange'
                drought_risk = 'Medium'
            else:
                drought_color = 'green'
                drought_risk = 'Low'

            # Create popup content
            popup_content = f"""
            <b>Location:</b> {row['lat']:.5f}, {row['lon']:.5f}<br>
            <b>Flood Risk:</b> {flood_risk} ({row['flood_probability']:.4f})<br>
            <b>Drought Risk:</b> {drought_risk} ({row['drought_probability']:.4f})
            """

            # Add marker with popup
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=10,
                color=flood_color,
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(popup_content, max_width=300)
            ).add_to(risk_map)

        # Display the map
        st_folium(risk_map, width=700, height=500)

        # Legend for the map
        st.markdown("""
        ### Risk Legend
        - <span style='color:red;'>⬤</span> High Risk (> 0.7)
        - <span style='color:orange;'>⬤</span> Medium Risk (0.3 - 0.7)
        - <span style='color:green;'>⬤</span> Low Risk (< 0.3)
        """, unsafe_allow_html=True)

    with tab3:
        st.subheader("Satellite Data Analysis")

        # Create tabs for different types of detailed analysis
        subtab1, subtab2 = st.tabs(["Satellite Indicators", "Environmental Factors"])

        with subtab1:
            st.write("### Satellite-derived Indicators")

            # Create sample data for demonstration
            np.random.seed(int(location['lat'] * 100 + location['lon'] * 10))

            # Sample indicator data
            indicators = {
                "NDVI (Vegetation Index)": np.random.uniform(0.3, 0.8),
                "NDWI (Water Index)": np.random.uniform(0.2, 0.6),
                "NDMI (Moisture Index)": np.random.uniform(0.1, 0.5),
                "VV Band (SAR)": np.random.uniform(-15, -5),
                "VH Band (SAR)": np.random.uniform(-20, -10),
                "Water Percentage": np.random.uniform(5, 30),
                "Water Distance (m)": np.random.uniform(100, 1000),
                "Dry Percentage": np.random.uniform(10, 40),
                "Drought Mask Value": np.random.uniform(0, 0.3),
                "SAR Urban Mask": np.random.uniform(0, 0.2)
            }

            # Display the indicators
            for name, value in indicators.items():
                st.metric(name, f"{value:.4f}")

        with subtab2:
            st.write("### Environmental Risk Factors")

            # Sample environmental factors
            env_factors = {
                "Elevation (m)": np.random.uniform(100, 500),
                "Slope (degrees)": np.random.uniform(0, 10),
                "Distance to River (m)": np.random.uniform(50, 2000),
                "Soil Permeability": np.random.uniform(0.2, 0.8),
                "Land Cover Type": np.random.choice(["Urban", "Forest", "Cropland", "Grassland", "Water"]),
                "Population Density": np.random.uniform(50, 2000),
                "Annual Precipitation (mm)": np.random.uniform(500, 1200),
                "Temperature Anomaly (°C)": np.random.uniform(-2, 2)
            }

            # Display the environmental factors
            for name, value in env_factors.items():
                if isinstance(value, float):
                    st.metric(name, f"{value:.2f}")
                else:
                    st.metric(name, value)

    # Navigation buttons
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Back to Dashboard"):
            st.session_state.page = "dashboard"
            st.rerun()

    with col2:
        if st.button("Export Results"):
            # Create a CSV string
            csv = predictions.to_csv(index=False)

            # Create a download button
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"risk_analysis_{location['name'].replace(' ', '_')}.csv",
                mime="text/csv"
            )


# Main router
def main():
    # Route to the correct page based on session state
    if not st.session_state.authenticated:
        page_map = {
            "welcome": welcome_page,
            "login": login_page,
            "register": register_page
        }
    else:
        page_map = {
            "welcome": welcome_page,
            "dashboard": dashboard_page,
            "analysis": analysis_page
        }

    page_func = page_map.get(st.session_state.page, welcome_page)
    page_func()


if __name__ == "__main__":
    main()