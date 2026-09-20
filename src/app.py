"""
app.py - KrishiAI: AI & IoT Powered Smart Agricultural Equipment Rental System

Main Streamlit entry point. Run from the src/ folder:

    streamlit run app.py

Structure
---------
app.py              page setup, login gate, sidebar, navigation   (this file)
views/*.py          one module per page, each exposing render()
advisory_service.py, database.py, auth.py ...   application logic
api.py              REST API for weather advisories (run separately, see README)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

import auth
import database
import icons
import nav
import theme
import ui
from crop_recommendation import train_model
from views import (auth_screen, bookings, crop, dashboard, disease, equipment, iot,
                   uploads, weather)

st.set_page_config(
    page_title="KrishiAI",
    page_icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "favicon.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)
theme.inject()
database.init_db()


@st.cache_resource(show_spinner="Preparing AI models...")
def _warm_up_models():
    train_model()  # trains once (a few seconds) the first time, then loads from disk
    return True


# ------------------------------------------------------------ login gate ---
if st.session_state.get("user") is None:
    theme.hide_sidebar()
    auth_screen.render()
    st.stop()

user = st.session_state["user"]
_warm_up_models()

# ------------------------------------------------------------- navigation ---
PAGES = {
    "dashboard": st.Page(dashboard.render, title="Dashboard", icon=":material/dashboard:",
                         url_path="dashboard", default=True),
    "crop": st.Page(crop.render, title="Crop recommendation", icon=":material/psychiatry:", url_path="crop"),
    "disease": st.Page(disease.render, title="Disease detection", icon=":material/document_scanner:", url_path="disease"),
    "weather": st.Page(weather.render, title="Weather advisory", icon=":material/partly_cloudy_day:", url_path="weather"),
    "equipment": st.Page(equipment.render, title="Rental marketplace", icon=":material/agriculture:", url_path="equipment"),
    "iot": st.Page(iot.render, title="IoT monitor", icon=":material/sensors:", url_path="iot"),
    "bookings": st.Page(bookings.render, title="Bookings", icon=":material/event_available:", url_path="bookings"),
    "uploads": st.Page(uploads.render, title="My uploads", icon=":material/photo_library:", url_path="uploads"),
}
NAV_SECTIONS = [
    ("Overview", ["dashboard"]),
    ("Farm intelligence", ["crop", "disease", "weather"]),
    ("Equipment", ["equipment", "iot", "bookings"]),
    ("Account", ["uploads"]),
]

nav.register(PAGES)
current = st.navigation(list(PAGES.values()), position="hidden")
theme.mark_active_nav(current.url_path)  # "" for the default page

with st.sidebar:
    ui.html(
        '<div class="ka-brand">'
        f'<div class="ka-brand-mark">{icons.svg("sprout", 22, stroke=2)}</div>'
        '<div><div class="ka-brand-name">KrishiAI</div>'
        '<div class="ka-brand-tag">Smart farming platform</div></div></div>'
    )
    for heading, keys in NAV_SECTIONS:
        ui.html(f'<div class="ka-nav-heading">{heading}</div>')
        for key in keys:
            st.page_link(PAGES[key])

    place = user.get("location") or "Location not set"
    ui.html(
        '<div class="ka-usercard">'
        f'<div class="ka-avatar">{ui.esc(ui.initials(user["name"]))}</div>'
        f'<div><div class="ka-usercard-name">{ui.esc(user["name"])}</div>'
        f'<div class="ka-usercard-meta">{ui.esc(user["role"].title())}, {ui.esc(place)}</div></div></div>'
    )
    if st.button("Log out", key="logout", icon=":material/logout:", width="stretch"):
        st.session_state["user"] = None
        st.rerun()

ui.show_flash()
current.run()
