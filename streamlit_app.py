# streamlit_app.py
"""Main entry point - redirects to public home page."""
import logging
import sys

import streamlit as st

from app.db import init_ai_picks, init_db, init_prompt_context_db
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

# Redirect to public home page (no auth required)
st.switch_page("pages/home_page.py")
