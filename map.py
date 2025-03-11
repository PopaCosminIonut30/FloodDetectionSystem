import folium
import requests
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import Draw

st.session_state.map = "Map"

def map_page():
    st.title("🌍 Selectează Poligonul")

    # Verificăm dacă avem coordonatele localității
    #if "location" not in st.session_state or st.session_state.location is None:
     #   st.warning("⚠️ Te rog să selectezi mai întâi o localitate!")
      #  if st.button("Înapoi la Selectare Localitate"):
       #     st.session_state.page = "location"
        #    st.rerun()
        #return

    # Obținem coordonatele localității selectate
    lat, lon = 52.510885, 13.3989367

    # Creăm harta centrată pe localitate
    m = folium.Map(location=[lat, lon], zoom_start=13)

    # Adăugăm plugin pentru desenarea poligonului
    draw = Draw(
        draw_options={"polyline": False, "rectangle": False, "circle": False, "marker": False},
        edit_options={"edit": True, "remove": True}
    )
    draw.add_to(m)

    # Afișăm harta interactivă
    map_data = st_folium(m, width=700, height=500)

    # Extragem poligonul selectat
    if map_data and "all_drawings" in map_data:
        selected_polygons = map_data["all_drawings"]
        if selected_polygons:
            st.session_state.selected_polygon = selected_polygons[0]["geometry"]["coordinates"][0]
            st.success("✅ Poligon salvat!")

    # Afișăm coordonatele poligonului selectat
    if "selected_polygon" in st.session_state:
        st.write("🔹 **Coordonatele Poligonului:**")
        st.json(st.session_state.selected_polygon)

    # Buton pentru a reseta selecția
    if st.button("Resetează Poligonul"):
        st.session_state.pop("selected_polygon", None)
        st.rerun()

    # Buton pentru a reveni la selectarea localității
    if st.button("Înapoi la Selectare Localitate"):
        st.session_state.page = "location"
        st.rerun()

map_page()