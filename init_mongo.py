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

# Google Maps API key
GOOGLE_MAPS_API_KEY = "AIzaSyBW1YE7uSlLvYFrpwXSsljEJU_dTVQFrG0"

# Page config
st.set_page_config(page_title="Satellite Risk Assessment", page_icon="🛰️", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# Session state initialization
for key in ["authenticated", "username", "tier", "page", "location", "selected", "page_history", "selected_polygon"]:
    if key not in st.session_state:
        if key == "authenticated":
            st.session_state[key] = False
        elif key == "page":
            st.session_state[key] = "welcome"
        elif key == "page_history":
            st.session_state[key] = []
        else:
            st.session_state[key] = None


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


# Welcome page
def welcome_page():
    # Main title with custom styling
    st.markdown('<h1 class="main-title">🛰️ Satellite Risk Assessment</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Advanced environmental monitoring for agriculture using satellite data</p>',
                unsafe_allow_html=True)

    # Hero image
    st.image("Free-Satellite-Imagery.jpg", use_container_width=True)

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
        st.markdown('<div class="benefit-icon">🌾</div>', unsafe_allow_html=True)
        st.markdown('<div class="benefit-title">Crop-Specific Recommendations</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="benefit-description">Receive tailored advice for your specific crops and growing conditions.</div>',
            unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Subscription tiers
    st.markdown("## Choose Your Plan", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Basic</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">5 €</div>', unsafe_allow_html=True)

        features = [
            "Min/max temperatures (3 months)",
            "Monthly rainfall analysis",
            "Rainfall days per month",
            "Longest dry period",
            "Soil temperature estimates",
            "Basic maps"
        ]

        for feature in features:
            st.markdown(f'<div class="tier-feature">✓ {feature}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Standard</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">15 €</div>', unsafe_allow_html=True)

        features = [
            "All Basic features",
            "12 months of historical data",
            "Year-to-year comparison",
            "Heat stress indicators",
            "Temperature heatmaps",
            "PDF report exports"
        ]

        for feature in features:
            st.markdown(f'<div class="tier-feature">✓ {feature}</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="tier-card">', unsafe_allow_html=True)
        st.markdown('<div class="tier-header">Premium</div>', unsafe_allow_html=True)
        st.markdown('<div class="tier-price">30 €</div>', unsafe_allow_html=True)

        features = [
            "All Standard features",
            "Weather alerts",
            "Land surface temperature data",
            "Crop-specific impact analysis",
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
            st.session_state.update(authenticated=True, username="demo_user", tier="basic", page="location")
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
            st.session_state.update(authenticated=True, username=user["username"], tier=user["tier"], page="location")
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
                st.session_state.update(authenticated=True, username=username, tier=selected_tier, page="location")
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
        st.markdown('<div class="tier-price">5 €</div>', unsafe_allow_html=True)

        features = [
            "Min/max temperatures (3 months)",
            "Monthly rainfall analysis",
            "Rainfall days per month",
            "Longest dry period",
            "Soil temperature estimates"
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
        st.markdown('<div class="tier-price">15 €</div>', unsafe_allow_html=True)

        features = [
            "All Basic features",
            "12 months of historical data",
            "Year-to-year comparison",
            "Heat stress indicators",
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
        st.markdown('<div class="tier-price">30 €</div>', unsafe_allow_html=True)

        features = [
            "All Standard features",
            "Weather alerts",
            "Land surface temperature data",
            "Crop-specific impact analysis",
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

    if st.button("Back to Application"):
        st.session_state.page = "location"
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
            st.session_state.page = "analysis"
            st.rerun()


# Import the analysis_page function from satellite_data_manager
from satellite_data_manager import analysis_page


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
            "location": location_page,
            "analysis": analysis_page,
            "upgrade": upgrade_page
        }

    page_func = page_map.get(st.session_state.page, welcome_page)
    page_func()


if __name__ == "__main__":
    main()