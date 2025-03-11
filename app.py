import folium
import requests
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import draw

# Setăm titlul aplicației
st.set_page_config(page_title="Login & Map", page_icon="🌍", layout="centered")

# Inițializăm variabila din session_state pentru autentificare
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "selected" not in st.session_state:
    st.session_state.selected = False

if "location" not in st.session_state:
    st.session_state.location = None




# Funcție pentru a afișa pagina de login
def login_page():
    st.title("🔐 Pagina de Login")
    st.write("Introduceți orice username și parolă pentru a continua.")

    # Form pentru autentificare
    username = st.text_input("Username")
    password = st.text_input("Parola", type="password")

    if st.button("Login"):
        # Simulăm login fără verificare reală
        st.session_state.authenticated = True
        st.session_state.page = "location"
        st.rerun()

# Funcție pentru a obține coordonatele localității
import requests
import streamlit as st

GOOGLE_MAPS_API_KEY = "AIzaSyBW1YE7uSlLvYFrpwXSsljEJU_dTVQFrG0"

def get_location_coordinates(city_name):
    url = f"https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": city_name,
        "key": GOOGLE_MAPS_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()  # Verifică dacă request-ul a avut succes

        data = response.json()  # Convertim răspunsul la JSON

        if "results" in data and len(data["results"]) > 0:
            location = data["results"][0]["geometry"]["location"]
            lat, lon = location["lat"], location["lng"]
            return lat, lon
        else:
            st.error("⚠️ Localitate invalidă sau serverul nu a returnat date corecte.")
            return None

    except requests.exceptions.Timeout:
        st.error("⏳ Cererea a durat prea mult! Verifică-ți conexiunea la internet.")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Eroare de rețea: {e}")
    except Exception as e:
        st.error(f"⚠️ Eroare necunoscută: {e}")

    return None  # Returnează None dacă ceva nu a funcționat

# Pagina 2: Selectare localitate
def location_page():
    st.title("🏙️ Alege Localitatea")

    # Input pentru localitate
    city_name = st.text_input("Introdu numele localității:")

    if st.button("Mergi la Hartă"):
        if city_name:
            coordinates = get_location_coordinates(city_name)
            if coordinates:
                st.session_state.location = coordinates
                st.session_state.page = "map"  # Schimbăm pagina
                st.rerun()
            else:
                st.error("Localitate invalidă. Încearcă din nou!")
        else:
            st.warning("Te rog să introduci o localitate.")

# Funcție pentru a afișa harta cu poligon
import folium
import requests
import streamlit as st
from streamlit_folium import st_folium
from folium.plugins import Draw

st.session_state.map = "Map"

def map_page():
    st.title("🌍 Selectează Poligonul")

    # Verificăm dacă avem coordonatele localității
    if "location" not in st.session_state or st.session_state.location is None:
        st.warning("⚠️ Te rog să selectezi mai întâi o localitate!")
        if st.button("Înapoi la Selectare Localitate"):
            st.session_state.page = "location"
            st.rerun()
        return

    # Obținem coordonatele localității selectate
    lat, lon = st.session_state.location

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

    if st.button("Vezi zonele de Risc"):
        st.session_state.map = "analysis"
        st.rerun()




def risk_analysis_page():
    if not st.session_state.selected_polygon:
        st.warning("⚠️ Trebuie să selectezi un poligon înainte de a continua!")
        if st.button("Înapoi la Hartă"):
            st.session_state.page = "map"
            st.rerun()
        return

        # Creăm tab-urile pentru fiecare vizualizare
    tabs = st.tabs(["Risk Zones", "Flood Zones", "Drought Zones", "Water Sources", "Extreme Temperatures"])

    for i, tab in enumerate(tabs):
        with tab:
            st.subheader(f"Vizualizare: {tab._label}")
            m = folium.Map(location=st.session_state.location, zoom_start=13)

            # Adăugăm poligonul selectat pe hartă
            folium.Polygon(
                locations=st.session_state.selected_polygon,
                color=["red", "blue", "yellow", "green", "purple"][i],  # Fiecare tab cu o altă culoare
                fill=True,
                fill_opacity=0.4
            ).add_to(m)

            st_folium(m, width=700, height=500)

    if st.button("Înapoi la Hartă"):
        st.session_state.page = "map"
        st.rerun()
# Alegem ce pagină să afișăm
# Inițializare session_state
if "page" not in st.session_state:
    st.session_state.page = "login"

# Schimbare între pagini
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "location":
    location_page()
elif st.session_state.page == "map":
    map_page()
elif st.session_state.page == "analysis":
    risk_analysis_page()
