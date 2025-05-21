import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium
import hashlib
import datetime
import json
import os
import requests
import base64
import random
import math
from io import BytesIO
from branca.colormap import LinearColormap
from folium.plugins import Draw, HeatMap
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from auth import login_user, register_user, update_user_tier, hash_password
import h5py
from shapely.geometry import Polygon
import random  # Make sure to add this if not already imported
from weather_integration_functions import (
    load_weather_data, load_lst_data, extract_lst_data,
    plot_min_max_temps_overlayed, rainy_days_per_month,
    rain_hours_per_day, total_rain_and_coverage,
    longest_dry_streak, compare_periods,
    plot_land_surface_temperature, compare_surface_and_air_temperatures,
    enhanced_climate_analysis_page
)

# Import the SatelliteDataManager and analysis_page from satellite_data_manager
from satellite_data_manager import SatelliteDataManager, analysis_page

# Google Maps API key
GOOGLE_MAPS_API_KEY = "AIzaSyBW1YE7uSlLvYFrpwXSsljEJU_dTVQFrG0"

# Page config
st.set_page_config(page_title="CropSecure", page_icon="🛰️", layout="wide")

# Custom CSS for a more appealing home page
st.markdown("""
<style>
    .main-title {
        font-size: 3.5rem !important;
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
        margin-bottom: 3rem;
        font-weight: 300;
    }
    .tier-header {
        background-color: #f0f8ff;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 10px;
        font-weight: 600;
        color: #2874A6;
    }
    .tier-price {
        font-size: 1.8rem !important;
        font-weight: 700;
        color: #16A085;
        text-align: center;
        margin: 10px 0;
    }
    .tier-feature {
        padding: 5px 0;
        border-bottom: 1px solid #eee;
    }
    .tier-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        height: 100%;
        transition: transform 0.3s ease;
    }
    .tier-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .get-started-section {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin-top: 3rem;
        text-align: center;
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
    .benefit-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        color: #3498DB;
    }
    .benefit-title {
        font-weight: 600;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        color: #2C3E50;
    }
    .benefit-description {
        color: #7F8C8D;
        font-size: 0.9rem;
    }
    .benefit-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
        height: 100%;
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
for key in ["authenticated", "username", "tier", "page", "location", "selected", "page_history", "selected_polygon",
            "selected_location", "active_tab"]:
    if key not in st.session_state:
        if key == "authenticated":
            st.session_state[key] = False
        elif key == "page":
            st.session_state[key] = "welcome"
        elif key == "page_history":
            st.session_state[key] = []
        elif key == "active_tab":
            st.session_state[key] = "Home"
        else:
            st.session_state[key] = None

# Predefined locations for the flood risk analysis
PREDEFINED_LOCATIONS = [
    {"name": "Hamburg Area (Weather Data Available)", "lat": 53.562762, "lon": 9.573723, "country": "Germany", "has_weather_data": True},
    {"name": "Cologne, Germany", "lat": 50.9375, "lon": 6.9603, "country": "Germany"},
    {"name": "Frankfurt, Germany", "lat": 50.1109, "lon": 8.6821, "country": "Germany"},
    {"name": "Passau, Germany", "lat": 48.5667, "lon": 13.4667, "country": "Germany"},
    {"name": "Koblenz, Germany", "lat": 50.3569, "lon": 7.5890, "country": "Germany"},
    {"name": "Würzburg, Germany", "lat": 49.7913, "lon": 9.9534, "country": "Germany"}
]


# Set tab
def set_tab(tab_name):
    st.session_state.active_tab = tab_name


# Go to page function
def go_to_page(new_page):
    st.session_state.page_history.append(st.session_state.page)
    st.session_state.page = new_page
    st.rerun()


# Function to get location coordinates from Google Maps API
def get_location_coordinates(city_name):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
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
            st.error("⚠️ Invalid location or server did not return correct data.")
            return None

    except requests.exceptions.Timeout:
        st.error("⏳ Request took too long! Check your internet connection.")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Network error: {e}")
    except Exception as e:
        st.error(f"⚠️ Unknown error: {e}")

    return None


# Calculate center of a polygon
def calculate_polygon_center(polygon_coordinates):
    try:
        if not polygon_coordinates:
            return None

        # Create a Shapely polygon
        polygon = Polygon(polygon_coordinates)

        # Get the centroid
        centroid = polygon.centroid

        # Return the coordinates [lat, lon]
        return [centroid.y, centroid.x]
    except Exception as e:
        st.error(f"Error calculating polygon center: {e}")
        return None


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


# Welcome page
def welcome_page():
    # Main title with custom styling
    st.markdown('<h1 class="main-title">🛰️ CropSecure</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced environmental monitoring for agriculture and disaster prevention</p>',
                unsafe_allow_html=True)

    # Hero image
    st.image("Imagine_fundal.jpg", use_container_width=True)

    # Key benefits section
    st.markdown("## Why Choose Our Platform")

    benefit_col1, benefit_col2, benefit_col3 = st.columns(3)

    with benefit_col1:
        st.markdown('<div class="benefit-card">', unsafe_allow_html=True)
        st.markdown('<div class="benefit-icon">🌡️</div>', unsafe_allow_html=True)
        st.markdown('<div class="benefit-title">Real-time Climate Monitoring</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="benefit-description">Access up-to-date temperature, rainfall, and soil data collected from satellites.</div>',
            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with benefit_col2:
        st.markdown('<div class="benefit-card">', unsafe_allow_html=True)
        st.markdown('<div class="benefit-icon">📊</div>', unsafe_allow_html=True)
        st.markdown('<div class="benefit-title">Data-Driven Insights</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="benefit-description">Make informed decisions based on comprehensive analysis and visualizations.</div>',
            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with benefit_col3:
        st.markdown('<div class="benefit-card">', unsafe_allow_html=True)
        st.markdown('<div class="benefit-icon">🌊</div>', unsafe_allow_html=True)
        st.markdown('<div class="benefit-title">Flood & Drought Risk Analysis</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="benefit-description">Predict environmental risks with advanced satellite data processing.</div>',
            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Subscription tiers
    st.markdown("## Choose Your Plan", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Basic</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">60 €</div>', unsafe_allow_html=True)

        features = [
            "Min/max temperatures (3 months)",
            "Monthly rainfall analysis",
            "Rainfall days per month",
            "Longest dry period",
            "Soil temperature estimates",
            "Basic flood risk assessment",
            "Basic maps"
        ]

        for feature in features:
            st.markdown(f'<div class="tier-feature">✓ {feature}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Standard</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">95 €</div>', unsafe_allow_html=True)

        features = [
            "All Basic features",
            "12 months of historical data",
            "Year-to-year comparison",
            "Heat stress indicators",
            "Temperature heatmaps",
            "Detailed flood & drought analysis",
            "PDF report exports"
        ]

        for feature in features:
            st.markdown(f'<div class="tier-feature">✓ {feature}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Premium</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">160 €</div>', unsafe_allow_html=True)

        features = [
            "All Standard features",
            "Weather alerts",
            "Land surface temperature data",
            "Crop-specific impact analysis",
            "Advanced risk prediction models",
            "30-day weather predictions",
            "Expert recommendations",
            "AI Agronom Assistant"
        ]

        for feature in features:
            st.markdown(f'<div class="tier-feature">✓ {feature}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Get started section
    st.markdown('<div class="get-started-section">', unsafe_allow_html=True)
    st.markdown("### Get Started Today", unsafe_allow_html=True)

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

    st.markdown('</div>', unsafe_allow_html=True)


# Login page
def login_page():
    st.title("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login") and username and password:
        user = login_user(username, password)
        if user:
            st.session_state.update(authenticated=True, username=user["username"], tier=user["tier"], page="dashboard")
            st.rerun()
        else:
            st.error("Invalid username or password")
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
    if st.button("Back to Welcome"):
        st.session_state.page = "welcome"
        st.rerun()


# Upgrade subscription page
def upgrade_page():
    st.title("⬆️ Upgrade Your Plan")

    st.write(f"Current plan: **{st.session_state.tier.title()}**")

    st.subheader("Choose a New Plan")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Basic</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">60 €</div>', unsafe_allow_html=True)

        features = [
            "Min/max temperatures (3 months)",
            "Monthly rainfall analysis",
            "Rainfall days per month",
            "Longest dry period",
            "Soil temperature estimates",
            "Basic flood risk assessment"
        ]

        for feature in features:
            st.markdown(f'<div class="tier-feature">✓ {feature}</div>', unsafe_allow_html=True)

        if st.session_state.tier != "basic" and st.button("Select Basic", key="select_basic"):
            if update_user_tier(st.session_state.username, "basic"):
                st.session_state.tier = "basic"
                # Clear any existing analysis data to reflect new tier capabilities
                if "satellite_data" in st.session_state:
                    del st.session_state.satellite_data
                if "analysis_results" in st.session_state:
                    del st.session_state.analysis_results
                st.success("Plan updated to Basic!")
                st.rerun()
            else:
                st.error("Failed to update plan. Please try again.")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Standard</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">95 €</div>', unsafe_allow_html=True)

        features = [
            "All Basic features",
            "12 months of historical data",
            "Year-to-year comparison",
            "Heat stress indicators",
            "Detailed flood & drought analysis",
            "PDF report exports"
        ]

        for feature in features:
            st.markdown(f'<div class="tier-feature">✓ {feature}</div>', unsafe_allow_html=True)

        if st.session_state.tier != "standard" and st.button("Select Standard", key="select_standard"):
            # Here you might integrate with a payment processor
            if update_user_tier(st.session_state.username, "standard"):
                st.session_state.tier = "standard"
                # Clear any existing analysis data to reflect new tier capabilities
                if "satellite_data" in st.session_state:
                    del st.session_state.satellite_data
                if "analysis_results" in st.session_state:
                    del st.session_state.analysis_results
                st.success("Plan updated to Standard!")
                st.rerun()
            else:
                st.error("Failed to update plan. Please try again.")

        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Premium</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">160 €</div>', unsafe_allow_html=True)

        features = [
            "All Standard features",
            "Weather alerts",
            "Land surface temperature data",
            "Crop-specific impact analysis",
            "Advanced risk prediction models",
            "30-day weather predictions",
            "Expert recommendations"
        ]

        for feature in features:
            st.markdown(f'<div class="tier-feature">✓ {feature}</div>', unsafe_allow_html=True)

        if st.session_state.tier != "premium" and st.button("Select Premium", key="select_premium"):
            # Here you might integrate with a payment processor
            if update_user_tier(st.session_state.username, "premium"):
                st.session_state.tier = "premium"
                # Clear any existing analysis data to reflect new tier capabilities
                if "satellite_data" in st.session_state:
                    del st.session_state.satellite_data
                if "analysis_results" in st.session_state:
                    del st.session_state.analysis_results
                st.success("Plan updated to Premium!")
                st.rerun()
            else:
                st.error("Failed to update plan. Please try again.")

        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Back to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()


def location_page():
    st.title("🗺️ Select Assessment Location")

    # User instruction
    st.write("Please select a location to analyze by searching for an address or drawing a polygon on the map.")

    tab1, tab2 = st.tabs(["Search by Address", "Select on Map"])

    with tab1:
        # Address search using Google Maps API
        st.subheader("Search by Address")
        address = st.text_input("Enter address or location")
        search_col1, search_col2 = st.columns([3, 1])

        with search_col1:
            if st.button("Search") and address:
                try:
                    # Use Google Maps API to find coordinates
                    coordinates = get_location_coordinates(address)
                    if coordinates:
                        lat, lon = coordinates
                        st.success(f"Location found: {address} (Lat: {lat:.4f}, Lon: {lon:.4f})")

                        # Store coordinates in session state
                        st.session_state.location = {"type": "Point", "coordinates": [lon, lat]}
                        st.session_state.selected = True

                        # Show a small preview map
                        m = folium.Map(location=[lat, lon], zoom_start=13)
                        folium.Marker([lat, lon], popup=address).add_to(m)
                        st_folium(m, width=600, height=300)
                    else:
                        st.error("Location not found. Please try a different address.")
                except Exception as e:
                    st.error(f"Error finding location: {str(e)}")

    with tab2:
        # Map selection with drawing tools
        st.subheader("Draw Area on Map")

        # Default map center (if no location selected yet)
        default_lat, default_lon = 48.8566, 2.3522  # Paris by default

        # If we already have a location, center the map there
        if st.session_state.location and "coordinates" in st.session_state.location:
            map_lon = st.session_state.location["coordinates"][0]
            map_lat = st.session_state.location["coordinates"][1]
        else:
            map_lat, map_lon = default_lat, default_lon

        # Initialize map
        m = folium.Map(location=[map_lat, map_lon], zoom_start=10)

        # Add drawing tools
        draw = Draw(
            draw_options={
                'polyline': False,
                'rectangle': True,
                'polygon': True,
                'circle': False,
                'marker': True,
                'circlemarker': False
            },
            edit_options={'edit': True}
        )
        draw.add_to(m)

        # Display the map
        map_data = st_folium(m, width=700, height=500)

        # Process map selection
        if map_data and map_data.get("last_active_drawing"):
            drawing = map_data["last_active_drawing"]
            st.session_state.location = drawing
            st.session_state.selected = True

            # If it's a polygon, store the coordinates and calculate center
            if drawing["type"] in ["Polygon", "Rectangle"]:
                polygon_coords = drawing["coordinates"][0]
                st.session_state.selected_polygon = polygon_coords

                # Calculate and store the polygon center
                center = calculate_polygon_center(polygon_coords)
                if center:
                    st.success(f"Polygon center: Lat {center[0]:.4f}, Lon {center[1]:.4f}")
                    # Update location to use the polygon center
                    st.session_state.location = {"type": "Point", "coordinates": [center[1], center[0]]}

    # Selected location information
    if st.session_state.selected:
        st.success("✅ Location selected successfully!")

        if isinstance(st.session_state.location, dict):
            location_type = st.session_state.location.get("type", "Unknown")

            if location_type == "Point":
                st.write(
                    f"Selected Point at approximately: {st.session_state.location['coordinates'][1]:.4f}, {st.session_state.location['coordinates'][0]:.4f}")
            elif location_type in ["Polygon", "Rectangle"]:
                st.write(f"Selected Area: {location_type}")
                # Calculate approximate size in sq km
                area_size = random.uniform(0.5, 10.0)  # In a real app, calculate from coordinates
                st.write(f"Approximate size: {area_size:.2f} sq km")

        # Provide name for the analysis
        st.subheader("Name Your Analysis")
        analysis_name = st.text_input("Enter a name for this location analysis",
                                      value=f"Analysis {datetime.datetime.now().strftime('%Y-%m-%d')}")

        if st.button("Proceed to Analysis"):
            # Save the location and name to session state
            st.session_state.analysis_name = analysis_name
            # Clear any existing analysis data since we have a new location
            if "satellite_data" in st.session_state:
                del st.session_state.satellite_data
            if "analysis_results" in st.session_state:
                del st.session_state.analysis_results
            if "weather_data" in st.session_state:
                del st.session_state.weather_data
            if "lst_data" in st.session_state:
                del st.session_state.lst_data
            st.session_state.active_tab = "Climate Analysis"
            st.rerun()


# Flood risk location selection page
def flood_risk_location_page():
    st.title("🌊 Flood & Drought Risk Assessment")
    st.subheader("Select Location for Analysis")

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
                st.session_state.active_tab = "Flood Risk Analysis"
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
            st.session_state.active_tab = "Flood Risk Analysis"
            st.rerun()


# Flood risk analysis page
def flood_risk_analysis_page():
    if "selected_location" not in st.session_state:
        st.error("No location selected. Please go back and select a location.")
        if st.button("Back to Location Selection"):
            st.session_state.active_tab = "Flood Risk Selection"
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

    # Export functionality
    st.markdown("---")
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

    # Button to go back to location selection
    if st.button("Back to Location Selection"):
        st.session_state.active_tab = "Flood Risk Selection"
        st.rerun()


# Profile page
def profile_page():
    st.title("👤 User Profile")

    # Display user information
    st.subheader("Account Information")
    st.write(f"**Username:** {st.session_state.username}")
    st.write(f"**Subscription Tier:** {st.session_state.tier.capitalize()}")
    st.write(f"**Joined Date:** {datetime.date.today().strftime('%B %d, %Y')}")

    # Divider
    st.markdown("---")

    # Subscription details
    st.subheader("Subscription Details")

    # Different information based on tier
    if st.session_state.tier == "basic":
        st.info("You are currently on the Basic tier. Upgrade to access more features!")
        expiry_date = datetime.date.today() + datetime.timedelta(days=30)
        st.write(f"**Next billing date:** {expiry_date.strftime('%B %d, %Y')}")

        if st.button("Upgrade Subscription"):
            st.session_state.page = "upgrade"
            st.rerun()

    elif st.session_state.tier == "standard":
        st.success("You are on the Standard tier with enhanced analytics capabilities.")
        expiry_date = datetime.date.today() + datetime.timedelta(days=30)
        st.write(f"**Next billing date:** {expiry_date.strftime('%B %d, %Y')}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Downgrade to Basic"):
                # Downgrade logic
                if update_user_tier(st.session_state.username, "basic"):
                    st.session_state.tier = "basic"
                    st.success("Subscription downgraded to Basic!")
                    st.rerun()

        with col2:
            if st.button("Upgrade to Premium"):
                st.session_state.page = "upgrade"
                st.rerun()

    else:  # premium
        st.success("You are on our Premium tier with full access to all features!")
        expiry_date = datetime.date.today() + datetime.timedelta(days=30)
        st.write(f"**Next billing date:** {expiry_date.strftime('%B %d, %Y')}")

        if st.button("Manage Subscription"):
            st.session_state.page = "upgrade"
            st.rerun()

    # Usage statistics
    st.markdown("---")
    st.subheader("Usage Statistics")

    # Mock usage data
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Analyses Run", "12")

    with col2:
        st.metric("Locations Saved", "5")

    with col3:
        st.metric("Reports Generated", "7")

    # Mock usage chart
    dates = pd.date_range(start=datetime.date.today() - datetime.timedelta(days=30),
                          end=datetime.date.today(), freq='D')

    usage = [random.randint(0, 3) for _ in range(len(dates))]
    usage_df = pd.DataFrame({'Date': dates, 'Usage': usage})

    st.subheader("Recent Activity")
    fig = px.bar(usage_df, x='Date', y='Usage',
                 title='Platform Usage (Last 30 Days)',
                 labels={'Usage': 'Number of Analyses', 'Date': 'Date'})
    st.plotly_chart(fig)

    # Account management
    st.markdown("---")
    st.subheader("Account Management")

    if st.button("Change Password"):
        st.warning("Password change functionality would be implemented here.")

    if st.button("Delete Account"):
        st.error("Warning: This action cannot be undone!")
        confirm_delete = st.checkbox("I understand this will permanently delete my account")

        if confirm_delete and st.button("Confirm Delete Account"):
            st.warning("Account deletion functionality would be implemented here.")
            # In a real app, you would delete the user from your database
            # and then log them out
            st.success("Account deleted successfully!")
            for key in ["authenticated", "username", "tier"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.page = "welcome"
            st.rerun()


# Help page
def help_page():
    st.title("❓ Help & Support")

    # FAQ Section
    st.header("Frequently Asked Questions")

    faq_items = [
        {
            "question": "How accurate are the flood and drought predictions?",
            "answer": "Our predictions are based on multiple satellite data sources and advanced machine "
                      "learning models. Accuracy varies by region but generally ranges from 75-90% for "
                      "flood prediction and 70-85% for drought prediction."
        },
        {
            "question": "What satellite data sources do you use?",
            "answer": "We use a combination of optical and radar satellite data, including Sentinel-1 SAR, "
                      "Sentinel-2 multispectral imagery, and MODIS for temperature and vegetation data. "
                      "Our models extract various indices like NDVI, NDWI, and VV/VH backscatter."
        },
        {
            "question": "How often is the data updated?",
            "answer": "Data is updated every 6-12 days, depending on satellite revisit times and "
                      "cloud coverage for the region of interest."
        },
        {
            "question": "What does the subscription cover?",
            "answer": "Subscriptions provide access to different levels of analysis, historical data, "
                      "and reporting capabilities. Higher tiers offer more detailed analysis, longer "
                      "historical data access, and advanced features like crop-specific recommendations."
        },
        {
            "question": "Can I export the results?",
            "answer": "Yes, you can export results in CSV format on all subscription tiers. Standard and "
                      "Premium tiers also allow PDF report exports and GIS-compatible formats."
        }
    ]

    # Use expanders for each FAQ item
    for i, item in enumerate(faq_items):
        with st.expander(item["question"]):
            st.write(item["answer"])

    # User Guide
    st.header("User Guide")

    tab1, tab2, tab3 = st.tabs(["Getting Started", "Climate Analysis", "Flood Risk Assessment"])

    with tab1:
        st.subheader("Getting Started")
        st.markdown("""
        1. **Create an Account**: Register with your email and choose a subscription tier.
        2. **Select a Location**: Navigate to either Climate Analysis or Flood Risk Selection tab.
        3. **Run Analysis**: Process the satellite data for your selected location.
        4. **View Results**: Explore the various tabs to see different analysis outputs.
        5. **Export Data**: Download your results for external use.
        """)

    with tab2:
        st.subheader("Climate Analysis")
        st.markdown("""
        The Climate Analysis feature provides detailed temperature and precipitation data:

        - **Temperature Analysis**: View min/max temperatures over time
        - **Rainfall Analysis**: Analyze precipitation patterns
        - **Historical Comparison**: Compare current data with previous periods
        - **Heat Maps**: Visualize spatial distribution of climate variables
        - **Reports**: Generate comprehensive PDF reports
        """)

    with tab3:
        st.subheader("Flood Risk Assessment")
        st.markdown("""
        The Flood Risk Assessment feature evaluates potential flood and drought dangers:

        - **Prediction Results**: View raw probability data for flood and drought risk
        - **Risk Maps**: Visualize the spatial distribution of risk
        - **Detailed Analysis**: Explore the satellite indicators driving the predictions
        - **Environmental Factors**: Understand the contextual factors affecting risk
        """)

    # Contact Support
    st.header("Contact Support")

    st.markdown("""
    Need additional help? Our support team is ready to assist you.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Send a Message")
        name = st.text_input("Your Name")
        email = st.text_input("Your Email")
        issue = st.text_area("Describe your issue")

        if st.button("Submit"):
            if name and email and issue:
                st.success("Thank you! Your support request has been submitted. We'll respond within 24 hours.")
            else:
                st.error("Please fill out all fields.")

    with col2:
        st.subheader("Contact Information")
        st.markdown("""
        **Email**: support@CropSecure.com

        **Phone**: +(40) 731 321 412

        **Hours**: Monday-Friday, 9am-5pm CET

        **Address**:  
        CropSecure
        Tech Innovation Center  
        1234 Some Street  
        Cluj-Napoca, Romania
        """)


# About page
def about_page():
    st.title("ℹ️ About Us")

    st.markdown("""
    ## Our Mission

    At CropSecure, we are dedicated to making advanced satellite data analysis 
    accessible to everyone. Our mission is to provide timely, accurate, and actionable environmental insights 
    that help communities and organizations prepare for and mitigate the impacts of climate change and natural disasters.
    """)

    # Team section
    st.header("Our Team")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.image("https://via.placeholder.com/150", width=150)
        st.subheader("Antonia Szecsi")
        st.write("Data Scientist")

    with col2:
        st.image("https://via.placeholder.com/150", width=150)
        st.subheader("Vlad Koblicica")
        st.write("Backend Developer")


    with col3:
        st.image("https://via.placeholder.com/150", width=150)
        st.subheader("Cosmin Ionut Popa")
        st.write("Frontend Developer")


    # Technology section
    st.header("Our Technology")

    st.markdown("""
    ### Satellite Data Sources

    We leverage multiple satellite platforms to provide comprehensive environmental monitoring:

    - **Sentinel-1**: C-band synthetic aperture radar (SAR) for all-weather, day-and-night observations
    - **Sentinel-2**: High-resolution multispectral imagery for vegetation and water indices
    - **Landsat**: Historical data for long-term trend analysis

    ### Advanced Analytics

    Our platform combines traditional remote sensing techniques with cutting-edge machine learning:

    - **Computer Vision**: For feature extraction and pattern recognition
    - **Time Series Analysis**: For trend detection and anomaly identification
    - **Ensemble Models**: For robust and accurate prediction of environmental risks
    - **Spatial Statistics**: For understanding geographic patterns and relationships
    """)

    # Partners section
    st.header("Our Partners")

    st.markdown("""
    We collaborate with leading academic institutions, government agencies, and private organizations:

    - European Space Agency (ESA)
    """)

    # Publications section
    st.header("Research & Publications")

    st.markdown("""
    Our team regularly contributes to academic research in remote sensing and environmental monitoring:

    """)

    # Company info
    st.markdown("---")
    st.markdown("""
    **CropSecure**  
    Established 2025 | Cluj-Napoca, Romania 

    [Terms of Service](#) | [Privacy Policy](#) | [Data Security](#)
    """)


# Dashboard with tabs
def dashboard_page():
    # User info in sidebar
    st.sidebar.markdown(f"**Logged in as:** {st.session_state.username}")
    st.sidebar.markdown(f"**Subscription:** {st.session_state.tier.capitalize()}")

    # Sidebar navigation
    st.sidebar.markdown("## Navigation")

    # Define all tabs
    tabs = [
        "Home",
        "Location Selection",
        "Climate Analysis",
        "Flood Risk Selection",
        "Flood Risk Analysis",
        "Profile",
        "Help",
        "About"
    ]

    # Get current active tab or set default
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Home"

    # Create tab buttons in sidebar
    for tab in tabs:
        if st.sidebar.button(tab, key=f"tab_{tab}",
                             help=f"Go to {tab}",
                             use_container_width=True,
                             type="primary" if st.session_state.active_tab == tab else "secondary"):
            st.session_state.active_tab = tab
            st.rerun()

    # Logout button
    if st.sidebar.button("Logout", key="logout"):
        for key in ["authenticated", "username", "tier", "selected_location", "active_tab"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.page = "welcome"
        st.rerun()

    # Display the selected tab content
    if st.session_state.active_tab == "Home":
        home_page()
    elif st.session_state.active_tab == "Location Selection":
        location_page()
    elif st.session_state.active_tab == "Climate Analysis":
        # Use our enhanced climate analysis page that uses real data
        enhanced_climate_analysis_page()
    elif st.session_state.active_tab == "Flood Risk Selection":
        flood_risk_location_page()
    elif st.session_state.active_tab == "Flood Risk Analysis":
        flood_risk_analysis_page()
    elif st.session_state.active_tab == "Profile":
        profile_page()
    elif st.session_state.active_tab == "Help":
        help_page()
    elif st.session_state.active_tab == "About":
        about_page()


# Home page inside dashboard
def home_page():
    st.title(f"Welcome, {st.session_state.username}!")

    # Quick stats overview
    st.subheader("Dashboard Overview")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Locations", "5", "+2")

    with col2:
        st.metric("Analyses", "12", "+3")

    with col3:
        st.metric("Reports", "7", "+1")

    with col4:
        st.metric("Days Left", "22", "-8")

    # Quick links section
    st.markdown("---")
    st.subheader("Quick Links")

    quick_col1, quick_col2 = st.columns(2)

    with quick_col1:
        st.markdown("### Climate Analysis")
        st.markdown("""
        - Temperature trends
        - Rainfall patterns
        - Soil moisture
        - Historical comparison
        """)

        if st.button("Go to Climate Analysis"):
            st.session_state.active_tab = "Location Selection"
            st.rerun()

    with quick_col2:
        st.markdown("### Flood & Drought Risk")
        st.markdown("""
        - Flood prediction
        - Drought assessment
        - Satellite indicators
        - Environmental factors
        """)

        if st.button("Go to Flood Risk Analysis"):
            st.session_state.active_tab = "Flood Risk Selection"
            st.rerun()

    # Recent analyses
    st.markdown("---")
    st.subheader("Recent Analyses")

    # Mock data for recent analyses
    recent_analyses = [
        {"name": "Frankfurt Region", "date": "2025-04-21", "type": "Climate", "risk": "Low"},
        {"name": "Cologne Area", "date": "2025-04-18", "type": "Flood Risk", "risk": "High"},
        {"name": "Munich Surroundings", "date": "2025-04-15", "type": "Climate", "risk": "Medium"},
        {"name": "Berlin Region", "date": "2025-04-10", "type": "Drought Risk", "risk": "Medium"}
    ]

    # Convert to DataFrame for display
    recent_df = pd.DataFrame(recent_analyses)

    # Style the dataframe
    def color_risk(val):
        color = 'green' if val == "Low" else 'orange' if val == "Medium" else 'red'
        return f'background-color: {color}; color: white'

    # Display the styled dataframe
    st.dataframe(recent_df.style.map(color_risk, subset=['risk']))

    # News and updates
    st.markdown("---")
    st.subheader("News & Updates")

    with st.expander("🆕 New Flood Risk Model Released", expanded=True):
        st.markdown("""
        **April 25, 2025**

        We've just released a major update to our flood risk prediction model! This new version offers:

        - 15% improved accuracy across all regions
        - Better handling of flash flood scenarios
        - Enhanced incorporation of terrain data
        - More precise water level predictions

        All users now have access to this improved model when running new analyses.
        """)

    with st.expander("🔄 Premium Tier Features Enhanced"):
        st.markdown("""
        **April 15, 2025**

        Premium subscribers now have access to:

        - 30-day forecast extension (up from 14 days)
        - Crop-specific impact modeling for 12 new crop types
        - Integration with weather station data for improved calibration
        - Custom alert thresholds to match your specific needs
        """)

    with st.expander("📊 New Visualization Tools"):
        st.markdown("""
        **April 5, 2025**

        We've added several new visualization options for your data:

        - 3D terrain visualizations with risk overlay
        - Time-lapse animations of changing conditions
        - Comparative side-by-side map views
        - Exportable interactive charts
        """)


# Main router
def main():
    if "page_history" not in st.session_state:
        st.session_state.page_history = []

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
            "upgrade": upgrade_page
        }

    page_func = page_map.get(st.session_state.page, welcome_page)
    page_func()


if __name__ == "__main__":
    main()