# streamlit_app.py
"""
Main entry point - redirects to public home page.

SEO OPTIMIZATION NOTES:
- Page title is keyword-rich: "RAGE Sports Picks - AI vs Vegas" (50 chars)
- Includes primary keywords: "sports picks", "AI", "Vegas"
- Favicon set for branding in search results
- Layout set to "wide" for better content presentation
- Mobile meta tags added for mobile search visibility
- Note: Full removal of "You need to enable JavaScript" message requires patching
  Streamlit's static/index.html (not possible in pure Python code). However, the
  descriptive text in home.py overrides this in most search result snippets.
"""
import logging
import sys
from datetime import UTC, datetime

import streamlit as st

from app.db import backup_db, init_ai_picks, init_db, init_prompt_context_db
from app.utils.branding import render_mobile_web_app_meta_tags

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)


# ============================================================================
# PAGE CONFIGURATION (MUST be first Streamlit command after imports)
# ============================================================================
# SEO-optimized page config with keyword-rich title and proper metadata
st.set_page_config(
    page_title="RAGE Sports Picks - AI vs Vegas | Free AI Betting Picks",
    page_icon="img/favicon.ico",  # Favicon for better visual in browser tabs
    layout="wide",
    initial_sidebar_state="auto"
)

# --- Mobile Web App Meta Tags ---
render_mobile_web_app_meta_tags()

# --- DBs init ---
init_db()
init_ai_picks()
init_prompt_context_db()

# --- Daily auto-backup (runs once per day per server restart) ---

today = datetime.now(UTC).strftime("%Y-%m-%d")
if st.session_state.get("_last_backup_date") != today:
    backup_path = backup_db(tag="daily")
    if backup_path:
        logging.getLogger(__name__).info("Daily auto-backup: %s", backup_path)
    st.session_state["_last_backup_date"] = today

# Redirect to public home page (no auth required)
st.switch_page("pages/home.py")
