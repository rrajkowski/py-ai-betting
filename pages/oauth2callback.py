# pages/oauth2callback.py
"""
OAuth2 callback handler page.
This page receives the redirect from Google OAuth after user authentication.
It exchanges the auth code for user info, stores it in session state,
then uses st.switch_page() to redirect to the intended page (preserving session).
"""
import streamlit as st

from app.auth import handle_oauth_callback
from app.utils.branding import render_mobile_web_app_meta_tags

# --- Page Configuration ---
st.set_page_config(
    page_title="Logging in...",
    page_icon="img/favicon.ico",
    layout="wide"
)

# --- Mobile Web App Meta Tags ---
render_mobile_web_app_meta_tags()

# Hide default navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# Show loading message
st.info("🔄 Completing login... Please wait.")

# Handle OAuth callback - this will set session state and st.switch_page()
if "code" in st.query_params:
    result = handle_oauth_callback()
    if not result:
        st.error("❌ Login failed. Please try again.")
        st.markdown("[← Back to Home](./home)")
else:
    # No code in query params - redirect to home
    st.warning("⚠️ No authentication code found.")
    st.switch_page("pages/home.py")
