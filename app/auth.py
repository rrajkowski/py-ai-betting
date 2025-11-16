# app/auth.py
"""
Authentication wrapper for st-paywall that handles both local and cloud environments.
st-paywall works WITH Streamlit's native authentication system.
"""
import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _inject_env_to_secrets():
    """
    Inject environment variables into st.secrets if they don't exist.
    This allows st-paywall to read from environment variables.
    """
    env_mappings = {
        "testing_mode": os.getenv("TESTING_MODE", os.getenv("testing_mode")),
        "payment_provider": os.getenv("PAYMENT_PROVIDER", os.getenv("payment_provider")),
        "stripe_api_key": os.getenv("STRIPE_API_KEY", os.getenv("stripe_api_key")),
        "stripe_api_key_test": os.getenv("STRIPE_API_KEY_TEST", os.getenv("stripe_api_key_test")),
        "stripe_link": os.getenv("STRIPE_LINK", os.getenv("stripe_link")),
        "stripe_link_test": os.getenv("STRIPE_LINK_TEST", os.getenv("stripe_link_test")),
    }

    for key, value in env_mappings.items():
        if value is not None and key not in st.secrets:
            # Handle boolean conversion for testing_mode
            if key == "testing_mode":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
            # Inject into secrets
            st.secrets[key] = value


def check_authentication():
    """
    Check if user is authenticated and subscribed using st-paywall.

    st-paywall requires Streamlit's native authentication to be enabled.
    It adds a subscription layer on top of the native auth.

    Returns:
        bool: True if user is authenticated and subscribed, False otherwise
    """
    # Inject environment variables into st.secrets for st-paywall
    _inject_env_to_secrets()

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
        # Show login UI
        st.info("🔐 **Please log in to access this app**")

        # Create a centered login button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Use on_click callback to trigger login
            # No provider name needed when using generic [auth] format
            st.button(
                "🔑 Log in with Google",
                type="primary",
                use_container_width=True,
                on_click=st.login
            )

        st.markdown("---")
        st.markdown("""
        **Note:** After clicking "Log in with Google", you'll be redirected to Google's login page.
        After logging in, you'll be redirected back to this app.
        """)
        st.stop()
        return False

    # User is logged in, now check subscription with st-paywall
    try:
        from st_paywall import add_auth

        # DEBUG: Check what secrets are available
        st.sidebar.write("🔍 **Debug Info:**")
        st.sidebar.write(
            f"testing_mode: {st.secrets.get('testing_mode', 'NOT FOUND')}")
        st.sidebar.write(
            f"payment_provider: {st.secrets.get('payment_provider', 'NOT FOUND')}")
        st.sidebar.write(
            f"Has stripe_api_key: {'stripe_api_key' in st.secrets}")
        st.sidebar.write(
            f"Has stripe_api_key_test: {'stripe_api_key_test' in st.secrets}")

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
