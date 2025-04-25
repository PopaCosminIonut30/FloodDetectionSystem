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

# Import our new satellite data manager
from satellite_data_manager import SatelliteDataManager

# Page config
st.set_page_config(page_title="Satellite Risk Assessment", page_icon="🛰️", layout="wide")

# Session state initialization
for key in ["authenticated", "username", "tier", "page", "location", "selected", "page_history"]:
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


# Welcome page with tiered plans
def welcome_page():
    st.title("🛰️ Welcome to Satellite Risk Assessment")
    st.subheader("Analyze environmental risks for your agricultural land")
    st.image("Free-Satellite-Imagery.jpg", use_container_width=True)

    st.header("Choose Your Plan")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Basic")
        st.write("Free / 5€ per use")
        st.write("✓ Min/max temperatures (3 months)")
        st.write("✓ Monthly rainfall analysis")
        st.write("✓ Rainfall days per month")
        st.write("✓ Longest dry period")
        st.write("✓ Soil temperature estimates")
        st.write("✓ Basic maps")

    with col2:
        st.subheader("Standard")
        st.write("15€ per use")
        st.write("✓ All Basic features")
        st.write("✓ 12 months of historical data")
        st.write("✓ Year-to-year comparison")
        st.write("✓ Heat stress indicators")
        st.write("✓ Temperature heatmaps")
        st.write("✓ PDF report exports")

    with col3:
        st.subheader("Premium")
        st.write("30€ per use")
        st.write("✓ All Standard features")
        st.write("✓ Weather alerts")
        st.write("✓ Land surface temperature data")
        st.write("✓ Crop-specific impact analysis")
        st.write("✓ 30-day weather predictions")
        st.write("✓ Expert recommendations")
        st.write("✓ AI Agronom Assistant")

    st.header("Get Started")
    col1, col2 = st.columns(2)
    if col1.button("Login"):
        st.session_state.page = "login"
        st.rerun()
    if col2.button("Register"):
        st.session_state.page = "register"
        st.rerun()
    if st.button("Try Demo Version"):
        st.session_state.update(authenticated=True, username="demo_user", tier="basic", page="location")
        st.rerun()


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
        st.markdown("### Basic")
        st.write("Free / 5€ per use")
        st.write("✓ Min/max temperatures (3 months)")
        st.write("✓ Monthly rainfall analysis")
        st.write("✓ Rainfall days per month")
        st.write("✓ Longest dry period")
        st.write("✓ Soil temperature estimates")

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

    with col2:
        st.markdown("### Standard")
        st.write("15€ per use")
        st.write("✓ All Basic features")
        st.write("✓ 12 months of historical data")
        st.write("✓ Year-to-year comparison")
        st.write("✓ Heat stress indicators")
        st.write("✓ PDF report exports")

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

    with col3:
        st.markdown("### Premium")
        st.write("30€ per use")
        st.write("✓ All Standard features")
        st.write("✓ Weather alerts")
        st.write("✓ Land surface temperature data")
        st.write("✓ Crop-specific impact analysis")
        st.write("✓ 30-day weather predictions")
        st.write("✓ Expert recommendations")

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

    if st.button("Back to Application"):
        st.session_state.page = "location"
        st.rerun()


def location_page():
    st.title("🗺️ Select Assessment Location")

    # User instruction
    st.write("Please select a location to analyze by clicking on the map or searching for an address.")

    col1, col2 = st.columns([3, 1])

    with col1:
        # Initialize map centered on Europe
        m = folium.Map(location=[48.8566, 2.3522], zoom_start=4)

        # Add drawing tools to allow selection of regions
        draw = Draw(
            draw_options={
                'polyline': False,
                'rectangle': True,
                'polygon': True,
                'circle': False,
                'marker': True,
                'circlemarker': False
            },
            edit_options={'edit': False}
        )
        draw.add_to(m)

        # Display the map
        map_data = st_folium(m, width=700, height=500)

        # Process map selection
        if map_data["last_active_drawing"]:
            st.session_state.location = map_data["last_active_drawing"]
            st.session_state.selected = True

    with col2:
        # Address search
        st.subheader("Search by Address")
        address = st.text_input("Enter address or location")

        if st.button("Search") and address:
            try:
                # This would normally use Google Maps API for geocoding
                # For demo purposes, we'll just pretend it worked
                st.success(f"Location found: {address}")

                # In a real app, you would geocode the address and set the location
                st.session_state.location = {"type": "Point", "coordinates": [2.3522, 48.8566]}
                st.session_state.selected = True

            except Exception as e:
                st.error(f"Error finding location: {str(e)}")

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


# Import the analysis_page function from our updated implementation
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