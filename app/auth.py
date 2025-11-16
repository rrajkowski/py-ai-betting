# app/auth.py
"""
Authentication wrapper with custom Stripe integration.
Works with Streamlit's native authentication system.
"""
import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Force deployment refresh - v2


def check_authentication():
    """
    Check if user is authenticated and subscribed using custom Stripe integration.

    Returns:
        bool: True if user is authenticated and subscribed, False otherwise
    """

    # Check if we're running locally using IS_LOCAL flag in secrets
    try:
        is_localhost = st.secrets["IS_LOCAL"]
    except (KeyError, FileNotFoundError):
        is_localhost = False

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

    # User is logged in, now check subscription with custom Stripe integration
    try:
        import stripe

        # Get configuration from st.secrets (Streamlit Cloud) or environment variables (fallback)
        try:
            testing_mode_str = st.secrets["TESTING_MODE"]
        except (KeyError, FileNotFoundError):
            testing_mode_str = os.getenv('TESTING_MODE', 'false')
        testing_mode = str(testing_mode_str).lower() == 'true'

        # Get Stripe API key based on mode
        if testing_mode:
            try:
                stripe_api_key = st.secrets["STRIPE_API_KEY_TEST"]
            except (KeyError, FileNotFoundError):
                stripe_api_key = os.getenv('STRIPE_API_KEY_TEST')
            try:
                stripe_link = st.secrets["STRIPE_LINK_TEST"]
            except (KeyError, FileNotFoundError):
                stripe_link = os.getenv('STRIPE_LINK_TEST')
        else:
            try:
                stripe_api_key = st.secrets["STRIPE_API_KEY"]
            except (KeyError, FileNotFoundError):
                stripe_api_key = os.getenv('STRIPE_API_KEY')
            try:
                stripe_link = st.secrets["STRIPE_LINK"]
            except (KeyError, FileNotFoundError):
                stripe_link = os.getenv('STRIPE_LINK')

        # DEBUG: Show configuration
        st.sidebar.write("🔍 **Stripe Config:**")
        st.sidebar.write(f"Testing mode: {testing_mode}")
        st.sidebar.write(f"Has API key: {stripe_api_key is not None}")
        st.sidebar.write(f"Has link: {stripe_link is not None}")
        if stripe_api_key:
            st.sidebar.write(f"API key starts with: {stripe_api_key[:15]}...")

        if not stripe_api_key:
            st.error("⚠️ Stripe API key not configured")
            st.info("""
            **Setup Required:**

            Add these environment variables to Streamlit Cloud:
            - `STRIPE_API_KEY` (for production)
            - `STRIPE_LINK` (for production)
            - `STRIPE_API_KEY_TEST` (for testing)
            - `STRIPE_LINK_TEST` (for testing)
            - `TESTING_MODE` (true/false)

            Go to: https://share.streamlit.io/ → Settings → Secrets
            """)
            st.stop()
            return False

        # Check if user has active subscription
        stripe.api_key = stripe_api_key
        user_email = st.user.email

        customers = stripe.Customer.list(email=user_email)

        if not customers.data:
            # No customer found - show subscribe button
            st.warning(f"� Welcome! Please subscribe to access the app.")

            if stripe_link:
                st.markdown(f"""
                <a href="{stripe_link}?prefilled_email={user_email}" target="_blank">
                    <button style="
                        background-color: #FF4B4B;
                        color: white;
                        padding: 0.5rem 1rem;
                        border: none;
                        border-radius: 0.25rem;
                        cursor: pointer;
                        font-size: 16px;
                        font-weight: 500;
                    ">
                        🚀 Subscribe Now
                    </button>
                </a>
                """, unsafe_allow_html=True)

            st.stop()
            return False

        # Check for active subscriptions
        customer = customers.data[0]
        subscriptions = stripe.Subscription.list(customer=customer["id"])

        if len(subscriptions.data) == 0:
            # No active subscription
            st.warning(f"👋 Welcome back! Your subscription has expired.")

            if stripe_link:
                st.markdown(f"""
                <a href="{stripe_link}?prefilled_email={user_email}" target="_blank">
                    <button style="
                        background-color: #FF4B4B;
                        color: white;
                        padding: 0.5rem 1rem;
                        border: none;
                        border-radius: 0.25rem;
                        cursor: pointer;
                        font-size: 16px;
                        font-weight: 500;
                    ">
                        🔄 Renew Subscription
                    </button>
                </a>
                """, unsafe_allow_html=True)

            st.stop()
            return False

        # User has active subscription!
        st.sidebar.success(f"✅ Subscribed: {user_email}")
        return True

    except Exception as e:
        # If subscription check fails, show error
        st.error(f"⚠️ Subscription check error: {e}")
        st.info("""
        **Troubleshooting:**
        1. Make sure Stripe environment variables are set in Streamlit Cloud
        2. Check that Stripe API keys are valid
        3. Verify that `stripe` package is installed (check requirements.txt)
        """)
        st.stop()
        return False


def add_auth_to_page():
    """
    Add authentication to a page. Call this at the top of each page that requires auth.
    """
    return check_authentication()
