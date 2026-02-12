# pages/scores.py
"""
Live scores page for RAGE Sports Picks.

SEO OPTIMIZATION STRATEGY:
1. Page title: "Live Scores - RAGE Sports Picks | Real-Time Game Results"
   - Includes primary keywords: "live scores", "game results", "real-time"
   - Length: ~60 chars (optimal for Google SERP)

2. Visible H1 title with keyword-rich description
   - Helps crawlers understand page purpose

3. Real-time data updates
   - Encourages longer dwell time (positive ranking signal)
   - Improves user engagement metrics
"""
import streamlit as st

from app.db import init_ai_picks
from app.live_scores import display_live_scores
from app.utils.branding import render_global_css_overrides, render_logo_in_sidebar, render_mobile_web_app_meta_tags
from app.utils.sidebar import render_admin_section, render_sidebar_navigation

# ============================================================================
# PAGE CONFIGURATION (MUST be first Streamlit command after imports)
# ============================================================================
# SEO-optimized page config with keyword-rich title for search engines
st.set_page_config(
    page_title="Live Scores - RAGE Sports Picks | Real-Time Game Results",
    page_icon="img/favicon.ico",
    layout="wide",
    initial_sidebar_state="auto"
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

# ============================================================================
# SEO-OPTIMIZED VISIBLE TITLE & DESCRIPTION
# ============================================================================
# This text is crawled by search engines and often appears in search snippets.
# Keywords: "live scores", "real-time", "game results", "sports"
st.title("Live Scores - Real-Time Game Results")
st.markdown(
    "**Real-time live scores** for all major sports including NBA, NFL, NCAAB, NHL, MLB, and UFC. "
    "Track game results as they happen and see how RAGE Sports Picks are performing."
)

# Live scores page is public - no authentication required
display_live_scores()
