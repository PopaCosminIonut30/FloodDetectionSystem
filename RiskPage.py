import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import json
import os
from branca.colormap import LinearColormap


def generate_risk_data_if_needed():
    """Generate sample risk data if it doesn't exist yet"""
    if not os.path.exists("risk_data.json"):
        if "selected_polygon" in st.session_state:
            from SampleRiskData import generate_sample_risk_data
            risk_data = generate_sample_risk_data(st.session_state.selected_polygon)
            with open("risk_data.json", "w") as f:
                json.dump(risk_data, f, indent=2)
            return risk_data
    else:
        with open("risk_data.json", "r") as f:
            return json.load(f)
    return None


def risk_analysis_page():
    st.title("📊 Analiza Zonelor de Risc")

    # Check if polygon exists
    if "selected_polygon" not in st.session_state:
        st.warning("⚠️ Trebuie să selectezi un poligon înainte de a continua!")
        if st.button("Înapoi la Hartă"):
            st.session_state.page = "map"
            st.rerun()
        return

    # Generate or load risk data
    risk_data = generate_risk_data_if_needed()

    if not risk_data:
        st.error("Nu s-au putut încărca datele de risc!")
        if st.button("Înapoi la Hartă"):
            st.session_state.page = "map"
            st.rerun()
        return

    # Creăm tab-urile pentru fiecare vizualizare
    tabs = st.tabs(["Overall Risk", "Flood Risk", "Drought Risk", "Water Sources", "Extreme Temperatures"])

    # Color maps for each risk type
    color_maps = {
        "Overall Risk": LinearColormap(['green', 'yellow', 'orange', 'red'], vmin=0, vmax=1),
        "Flood Risk": LinearColormap(['lightblue', 'blue', 'darkblue', 'navy'], vmin=0, vmax=1),
        "Drought Risk": LinearColormap(['yellow', 'orange', 'orangered', 'darkred'], vmin=0, vmax=1),
        "Water Sources": LinearColormap(['lightgreen', 'green', 'darkgreen', 'forestgreen'], vmin=0, vmax=1),
        "Extreme Temperatures": LinearColormap(['lavender', 'violet', 'purple', 'indigo'], vmin=0, vmax=1)
    }

    # Risk data keys
    risk_keys = ["overall_risk", "flood_risk", "drought_risk", "water_source_risk", "temperature_risk"]

    for i, tab in enumerate(tabs):
        with tab:
            st.subheader(f"Vizualizare: {tab._label}")

            # Create base map
            m = folium.Map(location=st.session_state.location, zoom_start=13)

            # Add polygon boundary
            folium.Polygon(
                locations=st.session_state.selected_polygon,
                color='gray',
                weight=2,
                fill=False,
            ).add_to(m)

            # Get risk data for this tab
            risk_key = risk_keys[i]
            tab_risk_data = risk_data[risk_key]

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
                gradient={0.0: 'transparent', 0.2: color_maps[tab._label].rgb_hex_str(0.2),
                          0.5: color_maps[tab._label].rgb_hex_str(0.5), 0.8: color_maps[tab._label].rgb_hex_str(0.8),
                          1.0: color_maps[tab._label].rgb_hex_str(1.0)},
                min_opacity=0.3,
                max_opacity=0.9,
                blur=10
            ).add_to(m)

            # Add individual risk markers
            for point in tab_risk_data:
                lat, lon = point['coordinates'][1], point['coordinates'][0]
                risk_level = point['risk_level']
                color = color_maps[tab._label](risk_level)

                folium.CircleMarker(
                    location=[lat, lon],
                    radius=5,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.7,
                    popup=f"Risk Level: {risk_level}",
                ).add_to(m)

            # Add legend
            color_maps[tab._label].caption = f'{tab._label} Level'
            m.add_child(color_maps[tab._label])

            # Display the map
            st_folium(m, width=700, height=500)

            # Add statistics
            risk_levels = [point['risk_level'] for point in tab_risk_data]
            avg_risk = sum(risk_levels) / len(risk_levels)
            max_risk = max(risk_levels)
            min_risk = min(risk_levels)

            st.write(f"📊 **Statistici {tab._label}:**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Risc mediu", f"{avg_risk:.2f}")
            col2.metric("Risc maxim", f"{max_risk:.2f}")
            col3.metric("Risc minim", f"{min_risk:.2f}")

            # Add more detailed analysis based on the tab
            if tab._label == "Overall Risk":
                st.write("🔍 **Analiză generală:**")
                st.write(f"Zona selectată prezintă un nivel de risc general **{get_risk_category(avg_risk)}**.")
                if avg_risk > 0.7:
                    st.warning("⚠️ Această zonă prezintă un risc ridicat și necesită atenție sporită!")
                elif avg_risk > 0.4:
                    st.info("ℹ️ Această zonă prezintă un risc moderat și ar trebui monitorizată.")
                else:
                    st.success("✅ Această zonă prezintă un risc scăzut.")

            elif tab._label == "Flood Risk":
                st.write("🔍 **Analiză risc inundații:**")
                if avg_risk > 0.7:
                    st.warning("⚠️ Risc ridicat de inundații! Zonă cu probabilitate mare de inundații.")
                elif avg_risk > 0.4:
                    st.info("ℹ️ Risc moderat de inundații. Recomandăm măsuri de prevenție.")
                else:
                    st.success("✅ Risc scăzut de inundații în această zonă.")

            # Similar analysis for other tabs

    if st.button("Înapoi la Hartă"):
        st.session_state.page = "map"
        st.rerun()


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