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

# Force deployment refresh - v3


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

    # User is logged in - show logout button in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **Logged in as:**  \n{st.user.email}")

    if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
        st.logout()

    st.sidebar.markdown("---")

    # Now check subscription with custom Stripe integration
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
            # Get all 3 pricing tier links
            try:
                stripe_1_month_link = st.secrets["STRIPE_1_MONTH_LINK_TEST"]
            except (KeyError, FileNotFoundError):
                stripe_1_month_link = os.getenv('STRIPE_1_MONTH_LINK_TEST')
            try:
                stripe_3_month_link = st.secrets["STRIPE_3_MONTH_LINK_TEST"]
            except (KeyError, FileNotFoundError):
                stripe_3_month_link = os.getenv('STRIPE_3_MONTH_LINK_TEST')
            try:
                stripe_1_year_link = st.secrets["STRIPE_1_YEAR_LINK_TEST"]
            except (KeyError, FileNotFoundError):
                stripe_1_year_link = os.getenv('STRIPE_1_YEAR_LINK_TEST')
        else:
            try:
                stripe_api_key = st.secrets["STRIPE_API_KEY"]
            except (KeyError, FileNotFoundError):
                stripe_api_key = os.getenv('STRIPE_API_KEY')
            # Get all 3 pricing tier links
            try:
                stripe_1_month_link = st.secrets["STRIPE_1_MONTH_LINK"]
            except (KeyError, FileNotFoundError):
                stripe_1_month_link = os.getenv('STRIPE_1_MONTH_LINK')
            try:
                stripe_3_month_link = st.secrets["STRIPE_3_MONTH_LINK"]
            except (KeyError, FileNotFoundError):
                stripe_3_month_link = os.getenv('STRIPE_3_MONTH_LINK')
            try:
                stripe_1_year_link = st.secrets["STRIPE_1_YEAR_LINK"]
            except (KeyError, FileNotFoundError):
                stripe_1_year_link = os.getenv('STRIPE_1_YEAR_LINK')

        if not stripe_api_key:
            st.error("⚠️ Stripe API key not configured")
            st.info("""
            **Setup Required:**

            Add these environment variables to Streamlit Cloud:
            - `STRIPE_API_KEY` (for production)
            - `STRIPE_1_MONTH_LINK` (for production)
            - `STRIPE_3_MONTH_LINK` (for production)
            - `STRIPE_1_YEAR_LINK` (for production)
            - `STRIPE_API_KEY_TEST` (for testing)
            - `STRIPE_1_MONTH_LINK_TEST` (for testing)
            - `STRIPE_3_MONTH_LINK_TEST` (for testing)
            - `STRIPE_1_YEAR_LINK_TEST` (for testing)
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
            st.warning(
                "👋 Welcome! Please choose a subscription plan to access the app.")

            st.markdown("### 💎 Choose Your Plan")

            # Create 3 columns for pricing tiers
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("""
                <div style="
                    border: 2px solid #ddd;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    background-color: #f9f9f9;
                ">
                    <h3>📅 Monthly</h3>
                    <h2 style="color: #FF4B4B;">$10</h2>
                    <p style="color: #666;">per month</p>
                    <p style="font-size: 14px; color: #888;">Perfect for trying out</p>
                </div>
                """, unsafe_allow_html=True)

                if stripe_1_month_link:
                    st.markdown(f"""
                    <a href="{stripe_1_month_link}?prefilled_email={user_email}" target="_blank">
                        <button style="
                            background-color: #FF4B4B;
                            color: white;
                            padding: 0.5rem 1rem;
                            border: none;
                            border-radius: 0.25rem;
                            cursor: pointer;
                            font-size: 16px;
                            font-weight: 500;
                            width: 100%;
                            margin-top: 10px;
                        ">
                            Subscribe Monthly
                        </button>
                    </a>
                    """, unsafe_allow_html=True)

            with col2:
                st.markdown("""
                <div style="
                    border: 3px solid #4CAF50;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    background-color: #f0f8f0;
                    position: relative;
                ">
                    <div style="
                        position: absolute;
                        top: -12px;
                        left: 50%;
                        transform: translateX(-50%);
                        background-color: #4CAF50;
                        color: white;
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: bold;
                    ">BEST VALUE</div>
                    <h3>📆 Quarterly</h3>
                    <h2 style="color: #4CAF50;">$25</h2>
                    <p style="color: #666;">every 3 months</p>
                    <p style="font-size: 14px; color: #888;">Save 17% vs monthly</p>
                </div>
                """, unsafe_allow_html=True)

                if stripe_3_month_link:
                    st.markdown(f"""
                    <a href="{stripe_3_month_link}?prefilled_email={user_email}" target="_blank">
                        <button style="
                            background-color: #4CAF50;
                            color: white;
                            padding: 0.5rem 1rem;
                            border: none;
                            border-radius: 0.25rem;
                            cursor: pointer;
                            font-size: 16px;
                            font-weight: 500;
                            width: 100%;
                            margin-top: 10px;
                        ">
                            Subscribe Quarterly
                        </button>
                    </a>
                    """, unsafe_allow_html=True)

            with col3:
                st.markdown("""
                <div style="
                    border: 2px solid #ddd;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    background-color: #f9f9f9;
                ">
                    <h3>📅 Yearly</h3>
                    <h2 style="color: #FF4B4B;">$100</h2>
                    <p style="color: #666;">per year</p>
                    <p style="font-size: 14px; color: #888;">Save 17% vs monthly</p>
                </div>
                """, unsafe_allow_html=True)

                if stripe_1_year_link:
                    st.markdown(f"""
                    <a href="{stripe_1_year_link}?prefilled_email={user_email}" target="_blank">
                        <button style="
                            background-color: #FF4B4B;
                            color: white;
                            padding: 0.5rem 1rem;
                            border: none;
                            border-radius: 0.25rem;
                            cursor: pointer;
                            font-size: 16px;
                            font-weight: 500;
                            width: 100%;
                            margin-top: 10px;
                        ">
                            Subscribe Yearly
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
            st.warning(
                "👋 Welcome back! Your subscription has expired. Please renew to continue.")

            st.markdown("### 💎 Choose Your Plan")

            # Create 3 columns for pricing tiers
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("""
                <div style="
                    border: 2px solid #ddd;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    background-color: #f9f9f9;
                ">
                    <h3>📅 Monthly</h3>
                    <h2 style="color: #FF4B4B;">$10</h2>
                    <p style="color: #666;">per month</p>
                    <p style="font-size: 14px; color: #888;">Perfect for trying out</p>
                </div>
                """, unsafe_allow_html=True)

                if stripe_1_month_link:
                    st.markdown(f"""
                    <a href="{stripe_1_month_link}?prefilled_email={user_email}" target="_blank">
                        <button style="
                            background-color: #FF4B4B;
                            color: white;
                            padding: 0.5rem 1rem;
                            border: none;
                            border-radius: 0.25rem;
                            cursor: pointer;
                            font-size: 16px;
                            font-weight: 500;
                            width: 100%;
                            margin-top: 10px;
                        ">
                            Renew Monthly
                        </button>
                    </a>
                    """, unsafe_allow_html=True)

            with col2:
                st.markdown("""
                <div style="
                    border: 3px solid #4CAF50;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    background-color: #f0f8f0;
                    position: relative;
                ">
                    <div style="
                        position: absolute;
                        top: -12px;
                        left: 50%;
                        transform: translateX(-50%);
                        background-color: #4CAF50;
                        color: white;
                        padding: 4px 12px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: bold;
                    ">BEST VALUE</div>
                    <h3>📆 Quarterly</h3>
                    <h2 style="color: #4CAF50;">$25</h2>
                    <p style="color: #666;">every 3 months</p>
                    <p style="font-size: 14px; color: #888;">Save 17% vs monthly</p>
                </div>
                """, unsafe_allow_html=True)

                if stripe_3_month_link:
                    st.markdown(f"""
                    <a href="{stripe_3_month_link}?prefilled_email={user_email}" target="_blank">
                        <button style="
                            background-color: #4CAF50;
                            color: white;
                            padding: 0.5rem 1rem;
                            border: none;
                            border-radius: 0.25rem;
                            cursor: pointer;
                            font-size: 16px;
                            font-weight: 500;
                            width: 100%;
                            margin-top: 10px;
                        ">
                            Renew Quarterly
                        </button>
                    </a>
                    """, unsafe_allow_html=True)

            with col3:
                st.markdown("""
                <div style="
                    border: 2px solid #ddd;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    background-color: #f9f9f9;
                ">
                    <h3>📅 Yearly</h3>
                    <h2 style="color: #FF4B4B;">$100</h2>
                    <p style="color: #666;">per year</p>
                    <p style="font-size: 14px; color: #888;">Save 17% vs monthly</p>
                </div>
                """, unsafe_allow_html=True)

                if stripe_1_year_link:
                    st.markdown(f"""
                    <a href="{stripe_1_year_link}?prefilled_email={user_email}" target="_blank">
                        <button style="
                            background-color: #FF4B4B;
                            color: white;
                            padding: 0.5rem 1rem;
                            border: none;
                            border-radius: 0.25rem;
                            cursor: pointer;
                            font-size: 16px;
                            font-weight: 500;
                            width: 100%;
                            margin-top: 10px;
                        ">
                            Renew Yearly
                        </button>
                    </a>
                    """, unsafe_allow_html=True)

            st.stop()
            return False

        # User has active subscription!
        st.sidebar.success(f"✅ Subscribed")

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


def is_admin():
    """
    Check if the current logged-in user is an admin.

    Returns:
        bool: True if user is admin, False otherwise
    """
    try:
        # Check if user is logged in
        if not st.user.is_logged_in:
            return False

        # List of admin emails
        ADMIN_EMAILS = [
            "ruben.rajkowski@gmail.com"
        ]

        user_email = st.user.email
        return user_email in ADMIN_EMAILS
    except AttributeError:
        # st.user not available
        return False


def add_auth_to_page():
    """
    Add authentication to a page. Call this at the top of each page that requires auth.
    """
    return check_authentication()
