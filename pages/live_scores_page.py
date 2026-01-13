# pages/live_scores_page.py
import streamlit as st
from app.live_scores import display_live_scores
from app.utils.sidebar import render_sidebar_navigation, render_admin_section

# --- Hide Streamlit's default page navigation ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation ---
render_sidebar_navigation()

# --- Admin Section ---
render_admin_section()

# Live scores page is public - no authentication required
display_live_scores()
