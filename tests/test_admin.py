#!/usr/bin/env python3
"""
Quick test to verify is_admin() function works correctly locally
"""
import streamlit as st
from app.auth import is_admin

st.set_page_config(page_title="Admin Test", layout="wide")

st.title("🧪 Admin Function Test")

# Display secrets
st.subheader("Secrets Check")
try:
    is_local = st.secrets["IS_LOCAL"]
    st.success(f"✅ IS_LOCAL = {is_local}")
except Exception as e:
    st.error(f"❌ Error reading IS_LOCAL: {e}")

# Test is_admin()
st.subheader("is_admin() Function Test")
admin_status = is_admin()
if admin_status:
    st.success(f"✅ is_admin() returned: {admin_status}")
    st.info("Admin features should be visible in the sidebar!")
else:
    st.error(f"❌ is_admin() returned: {admin_status}")
    st.warning("Admin features will NOT be visible")

# Display st.user info
st.subheader("st.user Information")
try:
    st.write(f"st.user.is_logged_in: {st.user.is_logged_in}")
    st.write(f"st.user.email: {st.user.email}")
except AttributeError as e:
    st.info(f"st.user not available (expected locally): {e}")

