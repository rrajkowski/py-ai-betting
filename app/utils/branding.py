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
    Render global CSS overrides to fix spacing issues and improve UX/UI.
    Should be called early in the page, after st.set_page_config()
    """
    st.markdown("""
    <style>
        /* ===== LAYOUT & SPACING ===== */

        /* Remove gap from vertical block containers */
        .st-emotion-cache-tn0cau {
            gap: 0 !important;
        }

        /* Force padding for main block container */
        .stMainBlockContainer {
            padding: 2rem 1.5rem 10rem !important;
        }

        /* Fix alert/warning banners at top of page */
        [data-testid="stAlertContentWarning"],
        [data-testid="stAlertContentInfo"],
        [data-testid="stAlertContentError"],
        [data-testid="stAlertContentSuccess"] {
            margin-top: 0 !important;
            position: relative !important;
            z-index: 999999 !important;
        }

        /* Ensure first element in main container has no negative margin */
        .stMainBlockContainer > div:first-child {
            margin-top: 0 !important;
        }

        /* Adjust header z-index to not overlay alerts */
        [data-testid="stHeader"] {
            z-index: 999998 !important;
        }

        /* Add top padding to main block when alerts are present */
        .stMainBlockContainer {
            padding-top: 2rem !important;
        }

        /* Remove padding from sidebar user content */
        [data-testid="stSidebarUserContent"] {
            padding-top: 0 !important;
        }

        /* Remove margin from sidebar header */
        [data-testid="stSidebarHeader"] {
            margin-bottom: 0 !important;
        }

        /* ===== SIDEBAR NAVIGATION ===== */

        /* Add padding to sidebar navigation container */
        [data-testid="stSidebarNav"] {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }

        /* Remove margin from navigation element containers */
        .st-emotion-cache-1vo6xi6:has(> .stPageLink) {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }

        /* Style navigation links with reduced spacing */
        [data-testid="stSidebarNav"] a {
            padding: 0.5rem 1rem !important;
            margin-bottom: 0.25rem !important;
            border-radius: 0.5rem !important;
            transition: all 0.2s ease !important;
            border: none !important;
            background-color: transparent !important;
        }

        /* Add hover effect to navigation links */
        [data-testid="stSidebarNav"] a:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
            transform: translateX(4px) !important;
        }

        /* Add padding to sidebar content sections */
        [data-testid="stSidebar"] > div {
            padding-top: 1rem !important;
        }

        /* Improve sidebar button spacing and height */
        [data-testid="stSidebar"] .stButton > button {
            padding: 0.5rem 1rem !important;
            margin-bottom: 0.5rem !important;
            min-height: 2.5rem !important;
            width: 100% !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }

        /* Add spacing between sidebar sections */
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            margin-top: 1rem !important;
            margin-bottom: 0.75rem !important;
            font-size: 1rem !important;
        }

        /* Reduce spacing for sidebar dividers */
        [data-testid="stSidebar"] hr {
            margin: 1rem 0 !important;
        }

        /* Improve file uploader in sidebar */
        [data-testid="stSidebar"] [data-testid="stFileUploader"] {
            margin-top: 0.5rem !important;
            margin-bottom: 0.5rem !important;
        }

        /* Add spacing to sidebar expanders */
        [data-testid="stSidebar"] [data-testid="stExpander"] {
            margin-bottom: 0.75rem !important;
        }

        /* Style Admin section page links like buttons */
        [data-testid="stSidebar"] .stPageLink {
            display: block !important;
            padding: 0.5rem 1rem 0 !important;
            margin-bottom: 0 !important;
            border: 0 !important;
            border-radius: 0 !important;
            background-color: transparent !important;
            transition: all 0.2s ease !important;
        }

        /* Hover effect for admin page links */
        [data-testid="stSidebar"] .stPageLink:hover {
            background-color: rgba(255, 255, 255, 0.1) !important;
            transform: translateX(2px) !important;
        }

        /* ===== TYPOGRAPHY & HEADERS ===== */

        /* Main page title styling */
        h1 {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            margin-bottom: 1rem !important;
            line-height: 1.2 !important;
        }

        /* Section headers with better spacing */
        h2 {
            font-size: 1.75rem !important;
            font-weight: 600 !important;
            margin-top: 3rem !important;
            margin-bottom: 1.5rem !important;
            padding-bottom: 0.5rem !important;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1) !important;
        }

        /* Subsection headers */
        h3 {
            font-size: 1.25rem !important;
            font-weight: 600 !important;
            margin-top: 2rem !important;
            margin-bottom: 1rem !important;
        }

        /* ===== CONTENT SECTIONS ===== */

        /* Add margin between main content sections */
        .stMarkdown {
            margin-bottom: 1.5rem !important;
        }

        /* Better spacing for horizontal blocks (stats, buttons) */
        [data-testid="stHorizontalBlock"] {
            gap: 1rem !important;
            margin-bottom: 1.5rem !important;
        }

        /* Reduce spacing in vertical blocks within columns (for sport stats) */
        .stColumn [data-testid="stVerticalBlock"] {
            gap: 0.25rem !important;
        }

        /* Remove extra margin from markdown in columns */
        .stColumn .stMarkdown {
            margin-bottom: 0 !important;
            margin-top: 0 !important;
        }

        /* Tighten element containers in columns */
        .stColumn .element-container {
            margin-bottom: 0.25rem !important;
        }

        /* ===== BUTTONS ===== */

        /* Primary button styling */
        .stButton > button {
            border-radius: 0.5rem !important;
            padding: 0.75rem 1.5rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }

        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        }

        /* ===== METRICS & STATS ===== */

        /* Metric containers with better spacing */
        [data-testid="stMetric"] {
            background-color: rgba(255, 255, 255, 0.05) !important;
            padding: 1rem !important;
            border-radius: 0.5rem !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }

        /* Metric labels */
        [data-testid="stMetricLabel"] {
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            opacity: 0.8 !important;
        }

        /* Metric values */
        [data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }

        /* ===== EXPANDERS ===== */

        /* Expander styling */
        [data-testid="stExpander"] {
            border-radius: 0.5rem !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            margin-bottom: 1rem !important;
        }

        /* ===== TABLES ===== */

        /* Table styling */
        .stDataFrame {
            border-radius: 0.5rem !important;
            overflow: hidden !important;
        }

        /* ===== SPACING UTILITIES ===== */

        /* Add spacing after dividers */
        hr {
            margin: 2rem 0 !important;
            opacity: 0.2 !important;
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
