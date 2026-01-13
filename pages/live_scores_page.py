# pages/live_scores_page.py
import streamlit as st
from app.live_scores import display_live_scores
from app.auth import is_admin

# --- Hide Streamlit's default page navigation ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# --- Inline Navigation (Public) ---
st.markdown("""
<div style="text-align: center; margin-bottom: 2em; font-size: 1.05em; font-weight: 500;">
    Navigation: Home | RAGE Picks | Live Scores
</div>
""", unsafe_allow_html=True)

# --- Admin Section (if logged in) ---
if is_admin():
    st.sidebar.markdown("### ⚙️ Admin")
    st.sidebar.page_link("pages/admin_manual_picks.py",
                         label="Manual Picks", icon="🔧")

# Live scores page is public - no authentication required
display_live_scores()
