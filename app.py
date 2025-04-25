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
from io import BytesIO
import random
from branca.colormap import LinearColormap
from folium.plugins import Draw, HeatMap
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from auth import login_user, register_user, update_user_tier, db, hash_password

# Setup page config
st.set_page_config(page_title="Satellite Risk Assessment", page_icon="🛰️", layout="wide")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "tier" not in st.session_state:
    st.session_state.tier = None
if "page" not in st.session_state:
    st.session_state.page = "welcome"
if "location" not in st.session_state:
    st.session_state.location = None
if "selected" not in st.session_state:
    st.session_state.selected = False

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


# Welcome page
def welcome_page():
    st.title("🛰️ Welcome to Satellite Risk Assessment")
    st.subheader("Analyze environmental risks for your selected areas")

    st.write("""
    Our application provides detailed risk assessments using satellite data, helping you 
    make informed decisions about your agricultural, urban planning, or environmental projects.
    """)

    # Preview image/video could go here
    st.image(r"C:\Users\popac\PycharmProjects\PythonProject1\Free-Satellite-Imagery.jpg", use_column_width=True)

    # Pricing tiers
    st.header("Choose Your Plan")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Basic")
        st.write("Free / 5€ per use")
        st.write("✓ 3-month temperature data")
        st.write("✓ Monthly rainfall analysis")
        st.write("✓ Soil temperature averages")
        st.write("✓ Drought period identification")
        st.write("✓ Basic map visualization")

    with col2:
        st.subheader("Standard")
        st.write("15€ per use")
        st.write("✓ All Basic features")
        st.write("✓ 12-month historical data")
        st.write("✓ Year-to-year comparisons")
        st.write("✓ Thermal stress indicators")
        st.write("✓ PDF report exports")
        st.write("✓ Expanded map visualization")

    with col3:
        st.subheader("Premium")
        st.write("30€ per use")
        st.write("✓ All Standard features")
        st.write("✓ Automatic risk alerts")
        st.write("✓ Crop-specific impact analysis")
        st.write("✓ Weather forecast integration")
        st.write("✓ 30-day predictions")
        st.write("✓ Personalized recommendations")
        st.write("✓ Expert consultation access")

    # Login/Register buttons
    st.header("Get Started")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login", key="welcome_login"):
            st.session_state.page = "login"
            st.rerun()

    with col2:
        if st.button("Register", key="welcome_register"):
            st.session_state.page = "register"
            st.rerun()

    # Demo version
    st.markdown("---")
    if st.button("Try Demo Version"):
        st.session_state.authenticated = True
        st.session_state.username = "demo_user"
        st.session_state.tier = "basic"
        st.session_state.page = "location"
        st.rerun()


# Login page
def login_page():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):
            # Check credentials against database
            if username and password:
                user = login_user(username, password)
                if user:
                    # Set session state
                    st.session_state.authenticated = True
                    st.session_state.username = user["username"]
                    st.session_state.tier = user["tier"]

                    # Check if subscription has expired
                    if user["subscription_end"] and datetime.date.fromisoformat(user["subscription_end"]) < datetime.date.today():
                        st.warning("Your subscription has expired. You have been downgraded to the basic tier.")
                        st.session_state.tier = "basic"
                        # Update user tier in database
                        update_user_tier(username, "basic")

                    # Redirect to location selection page
                    st.session_state.page = "location"
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")
            else:
                st.error("Please enter both username and password.")

    with col2:
        if st.button("Register"):
            st.session_state.page = "register"
            st.rerun()

    # Forgot password option
    st.markdown("---")
    forgot_pass = st.expander("Forgot Password?")
    with forgot_pass:
        recovery_email = st.text_input("Enter your recovery email")
        if st.button("Reset Password"):
            if recovery_email:
                # In a real app, this would send a password reset email
                st.success("If this email is associated with an account, a password reset link has been sent.")
            else:
                st.error("Please enter your recovery email.")

    # Demo access
    st.markdown("---")
    st.write("Don't have an account? Try our demo version.")
    if st.button("Try Demo Version"):
        st.session_state.authenticated = True
        st.session_state.username = "demo_user"
        st.session_state.tier = "basic"
        st.session_state.page = "location"
        st.rerun()

    # Back to home
    if st.button("Back to Home"):
        st.session_state.page = "welcome"
        st.rerun()


# Registration page
def register_page():
    st.title("📝 Create an Account")

    username = st.text_input("Choose a Username")
    password = st.text_input("Create Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if username and password and confirm_password:
            if password != confirm_password:
                st.error("Passwords do not match!")
            else:
                success, message = register_user(username, password)
                if success:
                    st.success("Registration successful! You can now log in.")
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.error("Please fill in all fields.")

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

    if st.button("Back to Home"):
        st.session_state.page = "welcome"
        st.rerun()


# Upgrade page
def upgrade_page():
    st.title("⬆️ Upgrade Your Plan")

    st.write(f"Current plan: **{st.session_state.tier.title()}**")

    st.subheader("Choose a New Plan")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Basic")
        st.write("Free / 5€ per use")
        st.write("✓ 3-month temperature data")
        st.write("✓ Monthly rainfall analysis")
        st.write("✓ Basic map visualization")

        if st.session_state.tier != "basic" and st.button("Select Basic", key="select_basic"):
            if update_user_tier(st.session_state.username, "basic"):
                st.session_state.tier = "basic"
                st.success("Plan updated to Basic!")
                st.rerun()
            else:
                st.error("Failed to update plan. Please try again.")

    with col2:
        st.markdown("### Standard")
        st.write("15€ per use")
        st.write("✓ All Basic features")
        st.write("✓ 12-month historical data")
        st.write("✓ PDF report exports")

        if st.session_state.tier != "standard" and st.button("Select Standard", key="select_standard"):
            # Here you might integrate with a payment processor
            if update_user_tier(st.session_state.username, "standard"):
                st.session_state.tier = "standard"
                st.success("Plan updated to Standard!")
                st.rerun()
            else:
                st.error("Failed to update plan. Please try again.")

    with col3:
        st.markdown("### Premium")
        st.write("30€ per use")
        st.write("✓ All Standard features")
        st.write("✓ Weather forecast integration")
        st.write("✓ 30-day predictions")

        if st.session_state.tier != "premium" and st.button("Select Premium", key="select_premium"):
            # Here you might integrate with a payment processor
            if update_user_tier(st.session_state.username, "premium"):
                st.session_state.tier = "premium"
                st.success("Plan updated to Premium!")
                st.rerun()
            else:
                st.error("Failed to update plan. Please try again.")

    if st.button("Back to Application"):
        st.session_state.page = "location"
        st.rerun()


# Location selection page
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
            st.session_state.page = "analysis"
            st.rerun()


# Function to generate mock satellite data
def generate_mock_data(location, months=3):
    # In a real app, this would fetch actual satellite data from an API
    data = {
        "dates": [(datetime.date.today() - datetime.timedelta(days=30 * i)).strftime("%Y-%m-%d") for i in
                  range(months)],
        "temperature": [random.uniform(15, 35) for _ in range(months)],
        "rainfall": [random.uniform(0, 100) for _ in range(months)],
        "soil_moisture": [random.uniform(0.2, 0.8) for _ in range(months)],
        "vegetation_index": [random.uniform(0.1, 0.9) for _ in range(months)],
        "risk_score": [random.uniform(1, 10) for _ in range(months)]
    }

    # Calculate drought periods (consecutive days with low rainfall)
    data["drought_periods"] = []
    current_drought = 0

    for i in range(months):
        if data["rainfall"][i] < 20:  # Arbitrary threshold
            current_drought += 30  # Each data point represents a month
        else:
            if current_drought > 0:
                data["drought_periods"].append(current_drought)
                current_drought = 0

    if current_drought > 0:
        data["drought_periods"].append(current_drought)

    return pd.DataFrame(data)


# Function to generate risk assessment
def calculate_risk_assessment(data):
    # In a real app, this would use more sophisticated algorithms
    risk_factors = {
        "temperature_risk": 0.0,
        "rainfall_risk": 0.0,
        "drought_risk": 0.0,
        "vegetation_risk": 0.0,
        "overall_risk": 0.0
    }

    # Temperature risk (high if consistently above 30°C)
    high_temp_count = sum(1 for temp in data["temperature"] if temp > 30)
    risk_factors["temperature_risk"] = high_temp_count / len(data["temperature"]) * 10

    # Rainfall risk (high if consistently below 30mm)
    low_rain_count = sum(1 for rain in data["rainfall"] if rain < 30)
    risk_factors["rainfall_risk"] = low_rain_count / len(data["rainfall"]) * 10

    # Drought risk (based on length of drought periods)
    if data["drought_periods"]:
        longest_drought = max(data["drought_periods"]) if data["drought_periods"] else 0
        risk_factors["drought_risk"] = min(longest_drought / 90 * 10, 10)  # Max 10 for droughts over 90 days

    # Vegetation risk (low vegetation index = higher risk)
    avg_vegetation = sum(data["vegetation_index"]) / len(data["vegetation_index"])
    risk_factors["vegetation_risk"] = (1 - avg_vegetation) * 10

    # Overall risk (weighted average)
    risk_factors["overall_risk"] = (
            risk_factors["temperature_risk"] * 0.25 +
            risk_factors["rainfall_risk"] * 0.25 +
            risk_factors["drought_risk"] * 0.3 +
            risk_factors["vegetation_risk"] * 0.2
    )

    return risk_factors


# Function to create PDF report
def create_pdf_report(analysis_name, data, risk_assessment):
    pdf = FPDF()
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Satellite Risk Assessment Report: {analysis_name}", ln=True, align="C")
    pdf.ln(10)

    # Summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Risk Assessment Summary:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Overall Risk Score: {risk_assessment['overall_risk']:.1f}/10", ln=True)

    risk_level = "Low" if risk_assessment['overall_risk'] < 3.5 else "Medium" if risk_assessment[
                                                                                     'overall_risk'] < 7 else "High"
    pdf.cell(0, 10, f"Risk Level: {risk_level}", ln=True)
    pdf.ln(5)

    # Individual risk factors
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Risk Factor Breakdown:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Temperature Risk: {risk_assessment['temperature_risk']:.1f}/10", ln=True)
    pdf.cell(0, 10, f"Rainfall Risk: {risk_assessment['rainfall_risk']:.1f}/10", ln=True)
    pdf.cell(0, 10, f"Drought Risk: {risk_assessment['drought_risk']:.1f}/10", ln=True)
    pdf.cell(0, 10, f"Vegetation Risk: {risk_assessment['vegetation_risk']:.1f}/10", ln=True)
    pdf.ln(10)

    # Data summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Data Summary:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 10, f"Analysis Period: {data['dates'].iloc[-1]} to {data['dates'].iloc[0]}", ln=True)
    pdf.cell(0, 10, f"Average Temperature: {data['temperature'].mean():.1f}°C", ln=True)
    pdf.cell(0, 10, f"Total Rainfall: {data['rainfall'].sum():.1f}mm", ln=True)

    # Drought periods
    if len(data["drought_periods"]) > 0:
        pdf.cell(0, 10, f"Longest Drought Period: {max(data['drought_periods']):.0f} days", ln=True)
    else:
        pdf.cell(0, 10, "No significant drought periods detected", ln=True)

    pdf.ln(5)

    # Recommendations
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Recommendations:", ln=True)
    pdf.set_font("Arial", "", 10)

    if risk_assessment['temperature_risk'] > 7:
        pdf.multi_cell(0, 10, "- Consider heat-resistant crops or increased irrigation due to high temperature risk")

    if risk_assessment['rainfall_risk'] > 7:
        pdf.multi_cell(0, 10, "- Implement water conservation strategies due to low rainfall conditions")

    if risk_assessment['drought_risk'] > 7:
        pdf.multi_cell(0, 10, "- Prepare drought contingency plans and consider drought-resistant crops")

    pdf.ln(10)

    # Footer
    pdf.set_font("Arial", "I", 8)
    pdf.cell(0, 10, f"Report generated on {datetime.datetime.now().strftime('%Y-%m-%d')} by Satellite Risk Assessment",
             ln=True, align="C")

    # Save to BytesIO
    output = BytesIO()
    pdf.output(output)
    return output.getvalue()

# Analysis page
def analysis_page():
    st.title(f"📊 Analysis: {st.session_state.analysis_name}")

    # Generate appropriate data based on user tier
    months = 3  # Basic tier
    if st.session_state.tier == "standard":
        months = 12
    elif st.session_state.tier == "premium":
        months = 24

    # Generate mock data
    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = generate_mock_data(st.session_state.location, months)
        st.session_state.risk_assessment = calculate_risk_assessment(st.session_state.analysis_data)

    # Tabs for different analysis views
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Detailed Analysis", "Maps", "Reports"])

    # Summary tab
    with tab1:
        st.subheader("Risk Assessment Summary")

        # Overall risk score with gauge
        overall_risk = st.session_state.risk_assessment["overall_risk"]

        # Create a gauge chart with Plotly
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=overall_risk,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Overall Risk Score"},
            gauge={
                'axis': {'range': [0, 10]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 3.5], 'color': "green"},
                    {'range': [3.5, 7], 'color': "yellow"},
                    {'range': [7, 10], 'color': "red"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': overall_risk
                }
            }
        ))

        st.plotly_chart(fig)

        # Risk level interpretation
        risk_level = "Low" if overall_risk < 3.5 else "Medium" if overall_risk < 7 else "High"
        st.info(f"Risk Level: **{risk_level}**")

        # Display individual risk factors
        st.subheader("Risk Factors")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Temperature Risk", f"{st.session_state.risk_assessment['temperature_risk']:.1f}/10")
            st.metric("Rainfall Risk", f"{st.session_state.risk_assessment['rainfall_risk']:.1f}/10")

        with col2:
            st.metric("Drought Risk", f"{st.session_state.risk_assessment['drought_risk']:.1f}/10")
            st.metric("Vegetation Risk", f"{st.session_state.risk_assessment['vegetation_risk']:.1f}/10")

        # Key findings
        st.subheader("Key Findings")

        findings = []

        # Temperature findings
        avg_temp = st.session_state.analysis_data["temperature"].mean()
        findings.append(f"Average temperature: {avg_temp:.1f}°C")

        # Rainfall findings
        total_rain = st.session_state.analysis_data["rainfall"].sum()
        findings.append(f"Total rainfall: {total_rain:.1f}mm")

        # Drought periods
        if len(st.session_state.analysis_data["drought_periods"]) > 0:
            longest_drought = max(st.session_state.analysis_data["drought_periods"])
            findings.append(f"Longest drought period: {longest_drought:.0f} days")

        # List findings
        for finding in findings:
            st.write(f"• {finding}")

    # Detailed Analysis tab
    with tab2:
        st.subheader("Historical Data Analysis")

        # Temperature chart
        st.write("### Temperature Trends")
        temp_fig = px.line(
            st.session_state.analysis_data,
            x="dates",
            y="temperature",
            labels={"dates": "Date", "temperature": "Temperature (°C)"},
            title="Temperature Over Time"
        )
        st.plotly_chart(temp_fig)

        # Rainfall chart
        st.write("### Rainfall Analysis")
        rain_fig = px.bar(
            st.session_state.analysis_data,
            x="dates",
            y="rainfall",
            labels={"dates": "Date", "rainfall": "Rainfall (mm)"},
            title="Monthly Rainfall"
        )
        st.plotly_chart(rain_fig)

        # Soil moisture if premium tier
        if feature_available("premium"):
            st.write("### Soil Conditions")
            soil_fig = px.line(
                st.session_state.analysis_data,
                x="dates",
                y="soil_moisture",
                labels={"dates": "Date", "soil_moisture": "Soil Moisture (%)"},
                title="Soil Moisture Over Time"
            )
            st.plotly_chart(soil_fig)
        else:
            show_locked_feature("premium")

        # Year-to-year comparison if standard or premium tier
        if feature_available("standard") and months >= 12:
            st.write("### Year-to-Year Comparison")

            # Group data by month for year-to-year comparison
            monthly_data = st.session_state.analysis_data.copy()
            monthly_data["month"] = pd.to_datetime(monthly_data["dates"]).dt.month_name()

            # Create comparison chart
            compare_fig = px.line(
                monthly_data,
                x="month",
                y="temperature",
                color=pd.to_datetime(monthly_data["dates"]).dt.year,
                labels={"month": "Month", "temperature": "Temperature (°C)", "color": "Year"},
                title="Temperature by Month (Year-to-Year)"
            )
            st.plotly_chart(compare_fig)
        elif not feature_available("standard"):
            show_locked_feature("standard")

    # Maps tab
    with tab3:
        st.subheader("Spatial Analysis")

        # Base map with selected area
        m2 = folium.Map(location=[48.8566, 2.3522], zoom_start=8)

        # If a location is selected, show it on the map
        if isinstance(st.session_state.location, dict):
            if st.session_state.location["type"] == "Point":
                folium.Marker(
                    [st.session_state.location["coordinates"][1], st.session_state.location["coordinates"][0]],
                    popup="Selected Location"
                ).add_to(m2)
            elif st.session_state.location["type"] in ["Polygon", "Rectangle"]:
                folium.GeoJson(
                    st.session_state.location,
                    style_function=lambda x: {"fillColor": "blue", "color": "blue"}
                ).add_to(m2)

        # Display the map
        st_folium(m2, width=700, height=400)

        # Risk heatmap (standard and premium tiers)
        if feature_available("standard"):
            st.write("### Risk Heatmap")

            # Generate mock heatmap data
            num_points = 500
            lat_range = 0.2
            lng_range = 0.2

            if isinstance(st.session_state.location, dict) and st.session_state.location["type"] == "Point":
                center_lat = st.session_state.location["coordinates"][1]
                center_lng = st.session_state.location["coordinates"][0]
            else:
                center_lat = 48.8566
                center_lng = 2.3522

            # Generate random points around the center
            heat_data = []
            for _ in range(num_points):
                lat = center_lat + (random.random() * 2 - 1) * lat_range
                lng = center_lng + (random.random() * 2 - 1) * lng_range

                # Higher risk near the center
                dist_from_center = ((lat - center_lat) ** 2 + (lng - center_lng) ** 2) ** 0.5
                risk = max(0, 1 - (dist_from_center / (lat_range + lng_range) * 2))

                heat_data.append([lat, lng, risk])

            # Create heatmap
            m3 = folium.Map(location=[center_lat, center_lng], zoom_start=12)
            HeatMap(heat_data).add_to(m3)

            # Display the heatmap
            st_folium(m3, width=700, height=400)
        else:
            show_locked_feature("standard")

        # Crop-specific impact analysis (premium tier only)
        if feature_available("premium"):
            st.write("### Crop Impact Analysis")

            crop_options = ["Wheat", "Corn", "Rice", "Soybeans", "Potatoes"]
            selected_crop = st.selectbox("Select crop type:", crop_options)

            # Generate mock crop-specific data
            crop_impact = {
                "factors": ["Temperature", "Rainfall", "Soil Moisture", "Pests"],
                "impact": [random.uniform(0, 10) for _ in range(4)]
            }

            # Create impact chart
            crop_fig = px.bar(
                crop_impact,
                x="factors",
                y="impact",
                labels={"factors": "Factor", "impact": "Impact Score"},
                title=f"{selected_crop} Impact Analysis"
            )

            st.plotly_chart(crop_fig)

            # Recommendations based on crop
            st.write("### Recommendations")
            st.info(f"Based on our analysis for {selected_crop}, we recommend the following actions:")

            recommendations = [
                f"Optimal planting time for {selected_crop}: {random.choice(['Early March', 'Late April', 'Mid-May'])}",
                f"Consider {random.choice(['additional irrigation', 'drought-resistant varieties', 'early harvesting'])} due to weather patterns",
                f"Risk of {random.choice(['fungal infections', 'pest outbreaks', 'heat stress'])} is {random.choice(['high', 'moderate', 'low'])}"
            ]

            for rec in recommendations:
                st.write(f"• {rec}")
        else:
            show_locked_feature("premium")

    # Reports tab
    with tab4:
        st.subheader("Report Generation")

        # Basic summary for free tier
        st.write("### Basic Summary")
        st.write(
            f"Analysis period: {st.session_state.analysis_data['dates'].iloc[-1]} to {st.session_state.analysis_data['dates'].iloc[0]}")
        st.write(f"Overall risk score: {st.session_state.risk_assessment['overall_risk']:.1f}/10 ({risk_level} risk)")

        # PDF export for standard and premium tiers
        if feature_available("standard"):
            st.write("### PDF Report")
            st.write("Generate a comprehensive PDF report with all analysis data and recommendations.")

            if st.button("Generate PDF Report"):
                pdf_data = create_pdf_report(
                    st.session_state.analysis_name,
                    st.session_state.analysis_data,
                    st.session_state.risk_assessment
                )

                # Create download link
                b64_pdf = base64.b64encode(pdf_data).decode()
                href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{st.session_state.analysis_name}_report.pdf">Download PDF Report</a>'
                st.markdown(href, unsafe_allow_html=True)
        else:
            show_locked_feature("standard")

        # Weather forecast integration (premium tier only)
        if feature_available("premium"):
            st.write("### 30-Day Forecast")
            st.write(
                "View weather predictions for the next 30 days based on historical patterns and current forecasts.")

            # Generate mock forecast data
            forecast_days = 30
            forecast_data = {
                "dates": [(datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in
                          range(forecast_days)],
                "temperature": [random.uniform(20, 35) for _ in range(forecast_days)],
                "rainfall": [random.uniform(0, 30) for _ in range(forecast_days)],
                "probability": [random.uniform(0, 1) for _ in range(forecast_days)]
            }

            forecast_df = pd.DataFrame(forecast_data)

            # Create forecast charts
            forecast_temp_fig = px.line(
                forecast_df,
                x="dates",
                y="temperature",
                labels={"dates": "Date", "temperature": "Temperature (°C)"},
                title="30-Day Temperature Forecast"
            )
            st.plotly_chart(forecast_temp_fig)

            forecast_rain_fig = px.bar(
                forecast_df,
                x="dates",
                y="rainfall",
                labels={"dates": "Date", "rainfall": "Rainfall (mm)"},
                title="30-Day Rainfall Forecast"
            )
            st.plotly_chart(forecast_rain_fig)

            # Expert recommendations
            st.write("### Expert Recommendations")
            st.info("Based on our forecast analysis, our experts recommend:")

            expert_recs = [
                f"Plan irrigation for {random.choice(['next week', 'the end of the month', 'mid-May'])} when rainfall is expected to be low",
                f"Consider {random.choice(['early harvesting', 'additional pest control', 'soil amendments'])} due to expected conditions",
                f"Optimal time for planting: {random.choice(['first week of May', 'mid-April', 'after the rainy period in late May'])}"
            ]

            for rec in expert_recs:
                st.write(f"• {rec}")
        else:
            show_locked_feature("premium")

    # Navigation buttons
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Change Location"):
            st.session_state.page = "location"
            # Clear analysis data
            if "analysis_data" in st.session_state:
                del st.session_state.analysis_data
            if "risk_assessment" in st.session_state:
                del st.session_state.risk_assessment
            st.rerun()

    with col2:
        if st.button("Upgrade Plan"):
            st.session_state.page = "upgrade"
            st.rerun()

    with col3:
        if st.button("Logout"):
            # Clear session state
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.tier = None
            st.session_state.page = "welcome"
            st.session_state.location = None
            st.session_state.selected = False
            if "analysis_data" in st.session_state:
                del st.session_state.analysis_data
            if "risk_assessment" in st.session_state:
                del st.session_state.risk_assessment
            st.rerun()


# Main app structure
def main():
    # Display navigation header if authenticated
    if st.session_state.authenticated:
        st.sidebar.title(f"👋 Hello, {st.session_state.username}")
        st.sidebar.write(f"Subscription tier: **{st.session_state.tier.title()}**")

        # Navigation menu
        st.sidebar.title("Navigation")

        if st.sidebar.button("Home"):
            st.session_state.page = "location"
            st.rerun()

        if st.sidebar.button("Change Location"):
            st.session_state.page = "location"
            # Clear analysis data
            if "analysis_data" in st.session_state:
                del st.session_state.analysis_data
            if "risk_assessment" in st.session_state:
                del st.session_state.risk_assessment
            st.rerun()

        if st.sidebar.button("Upgrade Plan"):
            st.session_state.page = "upgrade"
            st.rerun()

        if st.sidebar.button("Logout"):
            # Clear session state
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.tier = None
            st.session_state.page = "welcome"
            st.session_state.location = None
            st.session_state.selected = False
            if "analysis_data" in st.session_state:
                del st.session_state.analysis_data
            if "risk_assessment" in st.session_state:
                del st.session_state.risk_assessment
            st.rerun()

            # Display tier limitations
        if st.session_state.tier == "basic":
            st.sidebar.markdown("---")
            st.sidebar.info(
                "💡 **Basic Tier Limitations:**\n- 3-month historical data only\n- Limited map visualizations\n- No PDF reports")
            st.sidebar.markdown("[Upgrade for more features](#)")

            # App information
        st.sidebar.markdown("---")
        st.sidebar.info("🛰️ **Satellite Risk Assessment**\nv1.0.0\n\nHelping you make data-driven decisions.")

        # Route to correct page based on session state
    if not st.session_state.authenticated:
        if st.session_state.page == "welcome":
            welcome_page()
        elif st.session_state.page == "login":
            login_page()
        elif st.session_state.page == "register":
            register_page()
        else:
            welcome_page()
    else:
        if st.session_state.page == "welcome":
            st.session_state.page = "location"
            st.rerun()
        elif st.session_state.page == "location":
            location_page()
        elif st.session_state.page == "analysis":
            analysis_page()
        elif st.session_state.page == "upgrade":
            upgrade_page()
        else:
            location_page()

    # Weather forecast functionality - Premium tier feature
    def weather_forecast():
        # This would normally connect to a weather API
        # For demo purposes, we'll generate random forecast data
        forecast_days = 30
        base_temp = random.uniform(15, 25)
        base_rain = random.uniform(2, 5)

        forecast = []
        for i in range(forecast_days):
            date = (datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            # Add some randomness but keep a trend
            temp = base_temp + random.uniform(-5, 5) + (i / 10)  # Slight warming trend
            rain = max(0, base_rain + random.uniform(-2, 5) * (1 if random.random() > 0.7 else 0))  # Occasional rain

            forecast.append({
                "date": date,
                "temperature": temp,
                "rainfall": rain,
                "conditions": random.choice(["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Heavy Rain"])
            })

        return forecast

    # Risk alert system - Premium tier feature
    def generate_risk_alerts(data, risk_assessment):
        alerts = []

        # Temperature alerts
        if risk_assessment["temperature_risk"] > 7:
            alerts.append({
                "type": "Temperature",
                "severity": "High",
                "message": "Extreme temperature conditions detected. Risk of heat stress to crops."
            })
        elif risk_assessment["temperature_risk"] > 4:
            alerts.append({
                "type": "Temperature",
                "severity": "Medium",
                "message": "Elevated temperatures detected. Monitor conditions."
            })

        # Rainfall alerts
        if risk_assessment["rainfall_risk"] > 7:
            alerts.append({
                "type": "Rainfall",
                "severity": "High",
                "message": "Severe rainfall deficiency detected. Implement irrigation strategies."
            })
        elif risk_assessment["rainfall_risk"] > 4:
            alerts.append({
                "type": "Rainfall",
                "severity": "Medium",
                "message": "Below average rainfall detected. Monitor soil moisture."
            })

        # Drought alerts
        if risk_assessment["drought_risk"] > 7:
            alerts.append({
                "type": "Drought",
                "severity": "High",
                "message": f"Prolonged drought conditions detected. Urgent intervention recommended."
            })
        elif risk_assessment["drought_risk"] > 4:
            alerts.append({
                "type": "Drought",
                "severity": "Medium",
                "message": "Drought conditions developing. Prepare contingency plans."
            })

        return alerts

    # Crop-specific analysis - Premium tier feature
    def crop_specific_analysis(crop_type, data, risk_assessment):
        # Define crop characteristics and thresholds
        crop_data = {
            "Wheat": {
                "optimal_temp": (15, 25),
                "min_rainfall": 30,
                "drought_tolerance": "Medium",
                "growth_days": 110
            },
            "Corn": {
                "optimal_temp": (18, 32),
                "min_rainfall": 45,
                "drought_tolerance": "Low",
                "growth_days": 90
            },
            "Rice": {
                "optimal_temp": (20, 35),
                "min_rainfall": 150,
                "drought_tolerance": "Very Low",
                "growth_days": 120
            },
            "Soybeans": {
                "optimal_temp": (20, 30),
                "min_rainfall": 40,
                "drought_tolerance": "Medium",
                "growth_days": 100
            },
            "Potatoes": {
                "optimal_temp": (15, 20),
                "min_rainfall": 35,
                "drought_tolerance": "Medium-Low",
                "growth_days": 80
            }
        }

        # Default to Wheat if crop_type not found
        if crop_type not in crop_data:
            crop_type = "Wheat"

        # Calculate crop-specific risks
        analysis = {}

        # Temperature suitability
        avg_temp = data["temperature"].mean()
        optimal_low, optimal_high = crop_data[crop_type]["optimal_temp"]

        if optimal_low <= avg_temp <= optimal_high:
            temp_suitability = "Optimal"
            temp_risk = max(0, 3 - 3 * (
                        min(avg_temp - optimal_low, optimal_high - avg_temp) / (optimal_high - optimal_low)))
        elif avg_temp < optimal_low:
            temp_suitability = "Too Cold"
            temp_risk = 3 + min(7, 7 * (optimal_low - avg_temp) / 10)
        else:  # avg_temp > optimal_high
            temp_suitability = "Too Hot"
            temp_risk = 3 + min(7, 7 * (avg_temp - optimal_high) / 10)

        analysis["temperature"] = {
            "suitability": temp_suitability,
            "risk": temp_risk,
            "message": f"Average temperature of {avg_temp:.1f}°C is {temp_suitability.lower()} for {crop_type}."
        }

        # Rainfall suitability
        total_rainfall = data["rainfall"].sum()
        min_rainfall = crop_data[crop_type]["min_rainfall"] * (len(data["rainfall"]) / 4)  # Adjusting for period length

        if total_rainfall >= min_rainfall:
            rain_suitability = "Sufficient"
            rain_risk = max(0, 3 - 3 * (total_rainfall / min_rainfall))
        else:
            rain_suitability = "Insufficient"
            shortfall_ratio = (min_rainfall - total_rainfall) / min_rainfall
            rain_risk = 3 + min(7, 7 * shortfall_ratio)

        analysis["rainfall"] = {
            "suitability": rain_suitability,
            "risk": rain_risk,
            "message": f"Total rainfall of {total_rainfall:.1f}mm is {rain_suitability.lower()} for {crop_type}."
        }

        # Drought impact
        drought_tolerance = crop_data[crop_type]["drought_tolerance"]
        drought_multipliers = {
            "Very Low": 2.0,
            "Low": 1.5,
            "Medium-Low": 1.2,
            "Medium": 1.0,
            "Medium-High": 0.8,
            "High": 0.5,
            "Very High": 0.3
        }

        drought_multiplier = drought_multipliers.get(drought_tolerance, 1.0)
        drought_risk = min(10, risk_assessment["drought_risk"] * drought_multiplier)

        if drought_risk < 3:
            drought_impact = "Minimal"
        elif drought_risk < 6:
            drought_impact = "Moderate"
        else:
            drought_impact = "Severe"

        analysis["drought"] = {
            "impact": drought_impact,
            "risk": drought_risk,
            "message": f"Drought impact is {drought_impact.lower()} based on {crop_type}'s {drought_tolerance.lower()} drought tolerance."
        }

        # Overall suitability
        overall_risk = (analysis["temperature"]["risk"] * 0.4 +
                        analysis["rainfall"]["risk"] * 0.3 +
                        analysis["drought"]["risk"] * 0.3)

        if overall_risk < 3:
            overall_suitability = "Excellent"
        elif overall_risk < 5:
            overall_suitability = "Good"
        elif overall_risk < 7:
            overall_suitability = "Fair"
        else:
            overall_suitability = "Poor"

        analysis["overall"] = {
            "suitability": overall_suitability,
            "risk": overall_risk,
            "message": f"Overall suitability for {crop_type} cultivation is {overall_suitability.lower()}."
        }

        # Generate recommendations
        recommendations = []

        if analysis["temperature"]["risk"] > 6:
            if temp_suitability == "Too Hot":
                recommendations.append(f"Consider varieties of {crop_type} with better heat tolerance")
                recommendations.append("Implement shade structures or companion planting for heat reduction")
            else:  # Too Cold
                recommendations.append("Consider delayed planting until temperatures increase")
                recommendations.append("Use row covers or other temperature management techniques")

        if analysis["rainfall"]["risk"] > 6:
            recommendations.append("Implement irrigation system to compensate for rainfall deficiency")
            recommendations.append("Consider water-conserving cultivation techniques")

        if analysis["drought"]["risk"] > 6:
            recommendations.append("Implement mulching to reduce soil moisture evaporation")
            recommendations.append("Consider drought-resistant varieties of crops")

        if len(recommendations) == 0:
            recommendations.append(f"Continue standard {crop_type} cultivation practices")
            recommendations.append("Monitor conditions regularly")

        analysis["recommendations"] = recommendations

        return analysis

    # Run the main app
    if __name__ == "__main__":
        main()