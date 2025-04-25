import streamlit as st
import pandas as pd
import hashlib
import sqlite3
import datetime
import json


# Database setup function
from pymongo import MongoClient
import datetime
import hashlib
import streamlit as st

# MongoDB Atlas URI
MONGO_URI = "mongodb+srv://cosminionutpopa30:<db_password>@cluster0.pfxrhcv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["satellite_app"]
users_collection = db["users"]


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username, password):
    if users_collection.find_one({"username": username}):
        return False, "Username already exists"

    user = {
        "username": username,
        "password": hash_password(password),
        "tier": "basic",
        "subscription_end": str(datetime.date.today() + datetime.timedelta(days=30)),
        "last_login": str(datetime.date.today()),
        "usage_count": 1
    }
    users_collection.insert_one(user)
    return True, "User registered successfully"


def login_user(username, password):
    user = users_collection.find_one({
        "username": username,
        "password": hash_password(password)
    })

    if user:
        users_collection.update_one(
            {"username": username},
            {"$set": {"last_login": str(datetime.date.today())},
             "$inc": {"usage_count": 1}}
        )
        return user
    return None


# Set page config for the entire app
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


# Welcome page
def welcome_page():
    st.title("🛰️ Welcome to Satellite Risk Assessment")
    st.subheader("Analyze environmental risks for your selected areas")

    st.write("""
    Our application provides detailed risk assessments using satellite data, helping you 
    make informed decisions about your agricultural, urban planning, or environmental projects.
    """)

    # Preview image/video could go here
    st.image("https://via.placeholder.com/800x400?text=Satellite+Data+Preview", use_column_width=True)

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
                c = conn.cursor()
                c.execute("SELECT username, tier, subscription_end FROM users WHERE username = ? AND password = ?",
                          (username, hash_password(password)))
                user = c.fetchone()

                if user:
                    # Update last login and usage count
                    c.execute("UPDATE users SET last_login = ?, usage_count = usage_count + 1 WHERE username = ?",
                              (datetime.date.today(), username))
                    conn.commit()

                    # Set session state
                    st.session_state.authenticated = True
                    st.session_state.username = user[0]
                    st.session_state.tier = user[1]
                    st.session_state.page = "location"
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")

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

    # Tier selection with descriptions
    tier_options = {
        "Basic (Free / 5€)": "basic",
        "Standard (15€)": "standard",
        "Premium (30€)": "premium"
    }

    selected_tier_display = st.selectbox(
        "Select Subscription Tier",
        options=list(tier_options.keys())
    )

    selected_tier = tier_options[selected_tier_display]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Register"):
            if username and password and confirm_password:
                if password == confirm_password:
                    try:
                        c = conn.cursor()
                        # Check if username exists
                        c.execute("SELECT username FROM users WHERE username = ?", (username,))
                        if c.fetchone():
                            st.error("Username already exists")
                        else:
                            # Set subscription end date (30 days from now)
                            subscription_end = datetime.date.today() + datetime.timedelta(days=30)

                            # Insert new user
                            c.execute(
                                "INSERT INTO users (username, password, tier, subscription_end, last_login, usage_count) VALUES (?, ?, ?, ?, ?, ?)",
                                (username, hash_password(password), selected_tier, subscription_end,
                                 datetime.date.today(), 1)
                            )
                            conn.commit()

                            # If using a real payment system, this is where you'd redirect to payment

                            st.success("Registration successful!")

                            # Set session state
                            st.session_state.authenticated = True
                            st.session_state.username = username
                            st.session_state.tier = selected_tier
                            st.session_state.page = "payment"
                            st.rerun()
                    except Exception as e:
                        st.error(f"Registration error: {e}")
                else:
                    st.error("Passwords do not match")
            else:
                st.warning("Please fill in all fields")

    with col2:
        if st.button("Back to Welcome"):
            st.session_state.page = "welcome"
            st.rerun()


# Simple payment simulation page
def payment_page():
    st.title("💳 Payment")

    tier_prices = {
        "basic": "5€",
        "standard": "15€",
        "premium": "30€"
    }

    st.write(f"Selected Plan: **{st.session_state.tier.title()}**")
    st.write(f"Price: **{tier_prices[st.session_state.tier]}** per use")

    # Payment form (simulated)
    st.subheader("Payment Details")

    payment_method = st.selectbox("Payment Method", ["Credit Card", "PayPal", "Bank Transfer"])

    if payment_method == "Credit Card":
        st.text_input("Card Number")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Expiry Date")
        with col2:
            st.text_input("CVV", max_chars=3)

    st.text_input("Cardholder Name")

    if st.button("Complete Payment"):
        st.success("Payment successful!")
        st.session_state.page = "location"
        st.rerun()

    if st.button("Back to Register"):
        st.session_state.page = "register"
        st.rerun()


# Main routing logic
def main():
    # Check if the user is authenticated
    if not st.session_state.authenticated:
        if st.session_state.page == "welcome":
            welcome_page()
        elif st.session_state.page == "login":
            login_page()
        elif st.session_state.page == "register":
            register_page()
        elif st.session_state.page == "payment":
            payment_page()
        else:
            welcome_page()
    else:
        # Add a sidebar with user info and logout option
        with st.sidebar:
            st.write(f"Logged in as: **{st.session_state.username}**")
            st.write(f"Current tier: **{st.session_state.tier.title()}**")

            # Upgrade subscription button
            if st.session_state.tier != "premium":
                if st.button("Upgrade Subscription"):
                    st.session_state.page = "upgrade"
                    st.rerun()

            # Logout button
            if st.button("Logout"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.authenticated = False
                st.session_state.page = "welcome"
                st.rerun()

        # Route to the appropriate app page
        if st.session_state.page == "location":
            location_page()
        elif st.session_state.page == "map":
            map_page()
        elif st.session_state.page == "analysis":
            risk_analysis_page()
        elif st.session_state.page == "upgrade":
            upgrade_page()
        else:
            location_page()  # Default to location page


# Tier upgrade page
def upgrade_page():
    st.title("⬆️ Upgrade Your Subscription")

    current_tier = st.session_state.tier

    tier_descriptions = {
        "basic": {
            "name": "Basic",
            "price": "5€ per use",
            "features": [
                "3-month temperature data",
                "Monthly rainfall analysis",
                "Soil temperature averages",
                "Drought period identification",
                "Basic map visualization"
            ]
        },
        "standard": {
            "name": "Standard",
            "price": "15€ per use",
            "features": [
                "12-month historical data",
                "Year-to-year comparisons",
                "Thermal stress indicators",
                "PDF report exports",
                "Expanded map visualization"
            ]
        },
        "premium": {
            "name": "Premium",
            "price": "30€ per use",
            "features": [
                "Automatic risk alerts",
                "Crop-specific impact analysis",
                "Weather forecast integration",
                "30-day predictions",
                "Personalized recommendations",
                "Expert consultation access"
            ]
        }
    }

    # Show available upgrades
    if current_tier == "basic":
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Standard Plan")
            st.write(tier_descriptions["standard"]["price"])
            for feature in tier_descriptions["standard"]["features"]:
                st.write(f"✓ {feature}")
            if st.button("Upgrade to Standard"):
                # Here you'd handle the payment process
                st.session_state.tier = "standard"
                st.success("Upgraded to Standard tier!")
                st.session_state.page = "location"
                st.rerun()

        with col2:
            st.subheader("Premium Plan")
            st.write(tier_descriptions["premium"]["price"])
            for feature in tier_descriptions["premium"]["features"]:
                st.write(f"✓ {feature}")
            if st.button("Upgrade to Premium"):
                # Here you'd handle the payment process
                st.session_state.tier = "premium"
                st.success("Upgraded to Premium tier!")
                st.session_state.page = "location"
                st.rerun()

    elif current_tier == "standard":
        st.subheader("Premium Plan")
        st.write(tier_descriptions["premium"]["price"])
        for feature in tier_descriptions["premium"]["features"]:
            st.write(f"✓ {feature}")
        if st.button("Upgrade to Premium"):
            # Here you'd handle the payment process
            st.session_state.tier = "premium"
            st.success("Upgraded to Premium tier!")
            st.session_state.page = "location"
            st.rerun()

    if st.button("Back to App"):
        st.session_state.page = "location"
        st.rerun()


# If this file is run directly, execute the main function
if __name__ == "__main__":
    main()