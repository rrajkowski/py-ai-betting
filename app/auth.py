# app/auth.py
"""
Authentication wrapper for st-paywall that handles both local and cloud environments.
st-paywall works WITH Streamlit's native authentication system.
"""
import streamlit as st


def check_authentication():
    """
    Check if user is authenticated and subscribed using st-paywall.

    st-paywall requires Streamlit's native authentication to be enabled.
    It adds a subscription layer on top of the native auth.

    Returns:
        bool: True if user is authenticated and subscribed, False otherwise
    """
    # Check if we're running locally using IS_LOCAL flag in secrets
    is_localhost = st.secrets.get('IS_LOCAL', False)

    # LOCALHOST: Skip authentication for development
    if is_localhost:
        if st.session_state.get('show_auth_warning', True):
            st.warning("""
            ⚠️ **Development Mode**: Authentication is disabled for local testing.
            """)
            st.session_state.show_auth_warning = False
        return True

    # STREAMLIT CLOUD: Handle native auth + subscription
    # First, check if Streamlit native auth is available
    try:
        # Try to access st.user.is_logged_in
        is_logged_in = st.user.is_logged_in
    except AttributeError:
        # st.user is not available - authentication is not configured
        st.error("🔒 **Authentication Not Configured**")
        st.info("""
        **Streamlit native authentication is not enabled.**

        To fix this, add the following to your Streamlit Cloud secrets:

        ```toml
        [auth.google]
        client_id = "your-client-id"
        client_secret = "your-client-secret"
        server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
        ```

        **Steps:**
        1. Go to your app settings on Streamlit Cloud
        2. Click "Secrets"
        3. Add the `[auth.google]` section with your Google OAuth credentials
        4. Save and redeploy

        **Note:** Make sure the section name is EXACTLY `[auth.google]` (not `[auth]` or `[google_auth]`)
        """)
        st.stop()
        return False

    # Check if user is logged in
    if not is_logged_in:
        st.info("🔐 **Please log in to access this app**")
        if st.button("Log in with Google"):
            st.login()
        st.stop()
        return False

    # User is logged in, now check subscription with st-paywall
    try:
        from st_paywall import add_auth

        # This checks if the logged-in user has an active Stripe subscription
        add_auth(required=True)
        return True

    except Exception as e:
        # If st-paywall fails, show error
        st.error(f"⚠️ Subscription check error: {e}")
        st.info("""
        **Troubleshooting:**
        1. Make sure your Streamlit Cloud secrets are configured correctly
        2. Check that Stripe API keys are valid
        3. Verify that `st-paywall` is installed (check requirements.txt)
        """)
        st.stop()
        return False


def add_auth_to_page():
    """
    Add authentication to a page. Call this at the top of each page that requires auth.
    """
    return check_authentication()
