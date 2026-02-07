# pages/oauth2callback.py
"""
OAuth2 callback handler page.
This page handles the redirect from Google OAuth after user authentication.
"""
import streamlit as st
from app.auth import handle_oauth_callback

# --- Page Configuration ---
st.set_page_config(
    page_title="Logging in...",
    page_icon="img/favicon.png",
    layout="wide"
)

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

# Handle OAuth callback
if "code" in st.query_params:
    success = handle_oauth_callback()
    
    if success:
        # Get the intended destination page from session state
        intended_page = st.session_state.get("intended_page", "pages/rage_picks_page.py")
        
        st.success("✅ Login successful! Redirecting...")
        
        # Redirect to intended page
        st.switch_page(intended_page)
    else:
        st.error("❌ Login failed. Please try again.")
        if st.button("Return to Home"):
            st.switch_page("pages/home_page.py")
else:
    # No code in query params - redirect to home
    st.warning("⚠️ No authentication code found.")
    st.switch_page("pages/home_page.py")

