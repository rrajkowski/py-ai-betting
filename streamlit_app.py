# streamlit_app.py
"""Main entry point - redirects to public home page."""
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


# -----------------------------
# Page Configuration (MUST be first Streamlit command)
# -----------------------------
st.set_page_config(
    page_title="RAGE Sports Picks - AI vs Vegas",
    page_icon="img/favicon.ico",
    layout="wide"
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
st.switch_page("pages/home_page.py")
