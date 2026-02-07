"""Branding utilities for consistent logo and favicon across all pages."""
import streamlit as st
from pathlib import Path


def get_favicon_path():
    """Get the path to the favicon file."""
    return "img/favicon.png"


def get_logo_path():
    """Get the path to the logo file."""
    return "img/logo.png"


def render_logo_in_sidebar():
    """Render the RAGE Sports Picks logo in the sidebar."""
    logo_path = get_logo_path()
    
    # Check if logo exists
    if Path(logo_path).exists():
        st.sidebar.image(logo_path, use_container_width=True)
    else:
        # Fallback to text if logo doesn't exist
        st.sidebar.markdown("### 🏆 RAGE Sports Picks")

