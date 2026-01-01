# streamlit_app.py
"""
Main entry point - redirects to AI Picks page (home page)
"""
import streamlit as st
from app.db import init_db, init_ai_picks
from app.utils.db import init_prompt_context_db

# -----------------------------
# Page Configuration (MUST be first Streamlit command)
# -----------------------------
st.set_page_config(
    page_title="RAGE Sports Picks",
    page_icon="🏆",
    layout="wide"
)

# --- DBs init ---
init_db()
init_ai_picks()
init_prompt_context_db()

# Redirect to AI Picks page (home page)
st.switch_page("pages/ai_picks_page.py")
