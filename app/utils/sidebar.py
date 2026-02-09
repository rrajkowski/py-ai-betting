# app/utils/sidebar.py
"""
Shared sidebar navigation component for all pages.
Provides consistent navigation across the application.
"""
import streamlit as st

from app.auth import is_admin


def render_sidebar_navigation():
    """
    Render the main navigation sidebar with links to all public pages.
    This should be called on every page to maintain consistent navigation.
    """
    # --- Sidebar Navigation (Public) ---
    st.sidebar.markdown("### Navigation")
    st.sidebar.page_link("pages/home_page.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/rage_picks_page.py",
                         label="RAGE Picks", icon="🤖")
    st.sidebar.page_link("pages/live_scores_page.py",
                         label="Live Scores", icon="📊")
    st.sidebar.markdown("---")


def render_admin_section():
    """
    Render the admin section in the sidebar.
    Only displays if the current user is an admin.
    """
    if is_admin():
        st.sidebar.markdown("### ⚙️ Admin")
        if st.sidebar.button("🔧 Manual Picks", use_container_width=True):
            st.switch_page("pages/admin_manual_picks.py")
