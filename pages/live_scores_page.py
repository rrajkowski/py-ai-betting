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

# --- Sidebar Navigation (Public) ---
st.sidebar.markdown("### Navigation")
st.sidebar.page_link("pages/home_page.py", label="Home", icon="🏠")
st.sidebar.page_link("pages/rage_picks_page.py",
                     label="RAGE Picks", icon="🤖")
st.sidebar.page_link("pages/live_scores_page.py",
                     label="Live Scores", icon="📊")
st.sidebar.markdown("---")

# --- Admin Section (if logged in) ---
if is_admin():
    st.sidebar.markdown("### ⚙️ Admin")
    st.sidebar.page_link("pages/admin_manual_picks.py",
                         label="Manual Picks", icon="🔧")

# Live scores page is public - no authentication required
display_live_scores()
