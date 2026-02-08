"""Branding utilities for consistent logo and favicon across all pages."""
import streamlit as st
from pathlib import Path


def get_favicon_path():
    """Get the path to the favicon file."""
    return "img/favicon.ico"


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


def render_global_css_overrides():
    """
    Render global CSS overrides to fix spacing issues.
    Should be called early in the page, after st.set_page_config()
    """
    st.markdown("""
    <style>
        /* Remove gap from vertical block containers */
        .st-emotion-cache-tn0cau {
            gap: 0 !important;
        }

        /* Force padding for main block container */
        .stMainBlockContainer {
            padding: 2rem 1rem 10rem !important;
        }

        /* Remove padding from sidebar user content */
        [data-testid="stSidebarUserContent"] {
            padding-top: 0 !important;
        }

        /* Remove margin from sidebar header */
        [data-testid="stSidebarHeader"] {
            margin-bottom: 0 !important;
        }

        /* Add padding to sidebar navigation */
        [data-testid="stSidebarNav"] {
            padding-top: 1.5rem !important;
        }

        /* Add padding to sidebar content sections */
        [data-testid="stSidebar"] > div {
            padding-top: 1rem !important;
        }
    </style>
    """, unsafe_allow_html=True)


def render_mobile_web_app_meta_tags():
    """
    Render comprehensive meta tags for mobile web app functionality.

    This enables:
    - "Add to Home Screen" on iOS (Safari) with apple-touch-icon
    - "Install App" on Android (Chrome) with multiple icon sizes
    - Custom app title and icon
    - Status bar styling
    - Theme color
    - Favicon support across all browsers and platforms

    Should be called early in the page, after st.set_page_config()
    """

    st.markdown("""
    <!-- Favicon for all browsers -->
    <link rel="icon" type="image/x-icon" href="img/favicon.ico">
    <link rel="icon" type="image/png" sizes="32x32" href="img/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="img/favicon-16x16.png">

    <!-- Apple Touch Icon for iOS home screen -->
    <link rel="apple-touch-icon" href="img/apple-touch-icon.png">

    <!-- Android Chrome icons for PWA -->
    <link rel="icon" type="image/png" sizes="192x192" href="img/android-chrome-192x192.png">
    <link rel="icon" type="image/png" sizes="512x512" href="img/android-chrome-512x512.png">

    <!-- Web App Manifest for PWA support -->
    <link rel="manifest" href="img/site.webmanifest">

    <!-- Mobile Web App Meta Tags -->
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="RAGE Sports Picks">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#1f77b4">
    <meta name="msapplication-TileColor" content="#1f77b4">
    <meta name="msapplication-config" content="img/browserconfig.xml">
    """, unsafe_allow_html=True)
