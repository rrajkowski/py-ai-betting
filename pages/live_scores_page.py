# pages/live_scores_page.py
import streamlit as st

from app.db import init_ai_picks
from app.live_scores import display_live_scores
from app.utils.branding import render_global_css_overrides, render_logo_in_sidebar, render_mobile_web_app_meta_tags
from app.utils.sidebar import render_admin_section, render_sidebar_navigation

# --- Page Configuration ---
st.set_page_config(
    page_title="Live Scores - RAGE Sports Picks",
    page_icon="img/favicon.ico",
    layout="wide"
)

# --- INITIALIZATION ---
# Ensure database tables exist
init_ai_picks()

# --- Global CSS Overrides ---
render_global_css_overrides()

# --- Mobile Web App Meta Tags ---
render_mobile_web_app_meta_tags()

# --- Hide Streamlit's default page navigation ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Logo ---
render_logo_in_sidebar()

# --- Sidebar Navigation ---
render_sidebar_navigation()

# --- Admin Section ---
render_admin_section()

# Live scores page is public - no authentication required
display_live_scores()
