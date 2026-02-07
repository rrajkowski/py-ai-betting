# app/auth.py
"""
Authentication wrapper with custom Google OAuth and Stripe integration.
Uses environment variables instead of Streamlit's native auth for Railway compatibility.
"""
import streamlit as st
import os
from dotenv import load_dotenv
from authlib.integrations.requests_client import OAuth2Session
import secrets
import hashlib
import base64

# Load environment variables
load_dotenv()

# Force deployment refresh - v4


def get_oauth_config():
    """Get OAuth configuration from environment variables or secrets."""
    try:
        # Try environment variables first (Railway), then secrets.toml (local)
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

        # Fallback to secrets.toml if env vars not set (local development)
        if not client_id:
            try:
                client_id = st.secrets.get("GOOGLE_CLIENT_ID")
            except (KeyError, FileNotFoundError):
                pass

        if not client_secret:
            try:
                client_secret = st.secrets.get("GOOGLE_CLIENT_SECRET")
            except (KeyError, FileNotFoundError):
                pass

        if not redirect_uri:
            try:
                redirect_uri = st.secrets.get(
                    "GOOGLE_REDIRECT_URI", "https://ragepicks.com/oauth2callback")
            except (KeyError, FileNotFoundError):
                redirect_uri = "https://ragepicks.com/oauth2callback"

        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "scope": "openid email profile",
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo"
        }
    except Exception as e:
        st.error(f"OAuth configuration error: {e}")
        return None


def generate_state_token():
    """Generate a secure random state token for CSRF protection."""
    return secrets.token_urlsafe(32)


def init_oauth_session():
    """Initialize OAuth session with Google."""
    config = get_oauth_config()
    if not config or not config["client_id"] or not config["client_secret"]:
        return None

    return OAuth2Session(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        redirect_uri=config["redirect_uri"],
        scope=config["scope"]
    )


def handle_oauth_callback():
    """Handle OAuth callback from Google."""
    # Get authorization code from URL params
    query_params = st.query_params

    if "code" in query_params:
        code = query_params["code"]
        state = query_params.get("state", "")

        # Verify state token (CSRF protection)
        if state != st.session_state.get("oauth_state", ""):
            st.error("Invalid state token. Please try logging in again.")
            st.session_state.clear()
            st.rerun()
            return False

        # Exchange code for token
        oauth = init_oauth_session()
        if not oauth:
            st.error("OAuth configuration error")
            return False

        try:
            config = get_oauth_config()
            token = oauth.fetch_token(
                config["token_endpoint"],
                code=code,
                grant_type="authorization_code"
            )

            # Get user info
            resp = oauth.get(config["userinfo_endpoint"])
            user_info = resp.json()

            # Store user info in session
            st.session_state["user_email"] = user_info.get("email")
            st.session_state["user_name"] = user_info.get("name")
            st.session_state["user_picture"] = user_info.get("picture")
            st.session_state["is_logged_in"] = True

            # Clear query params and rerun
            st.query_params.clear()
            st.rerun()
            return True

        except Exception as e:
            st.error(f"Authentication failed: {e}")
            st.session_state.clear()
            return False

    return False


def check_authentication():
    """
    Check if user is authenticated and subscribed using custom Google OAuth + Stripe.

    Returns:
        bool: True if user is authenticated and subscribed, False otherwise
    """

    # Check if we're running locally using IS_LOCAL flag
    is_localhost = os.getenv("IS_LOCAL", "").lower() == "true"
    if not is_localhost:
        try:
            is_localhost = st.secrets.get("IS_LOCAL", False)
        except (KeyError, FileNotFoundError, AttributeError):
            is_localhost = False

    # LOCALHOST: Skip authentication for development
    if is_localhost:
        if st.session_state.get('show_auth_warning', True):
            st.warning("""
            ⚠️ **Development Mode**: Authentication is disabled for local testing.
            """)
            st.session_state.show_auth_warning = False
        return True

    # Handle OAuth callback if present
    if "code" in st.query_params:
        handle_oauth_callback()

    # Check if user is logged in
    if not st.session_state.get("is_logged_in", False):
        # Show login UI
        st.info("🔐 **Please log in to access this app**")

        # Create a centered login button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔑 Log in with Google", type="primary", use_container_width=True):
                # Generate state token for CSRF protection
                state = generate_state_token()
                st.session_state["oauth_state"] = state

                # Initialize OAuth session
                oauth = init_oauth_session()
                if not oauth:
                    st.error(
                        "OAuth configuration error. Please check environment variables.")
                    st.stop()

                # Get authorization URL
                config = get_oauth_config()
                authorization_url, _ = oauth.create_authorization_url(
                    config["authorization_endpoint"],
                    state=state
                )

                # Redirect to Google login
                st.markdown(
                    f'<meta http-equiv="refresh" content="0;url={authorization_url}">', unsafe_allow_html=True)
                st.stop()

        st.markdown("---")
        st.markdown("""
        **Note:** After clicking "Log in with Google", you'll be redirected to Google's login page.
        After logging in, you'll be redirected back to this app.
        """)
        st.stop()
        return False

    # User is logged in - show logout button in sidebar
    st.sidebar.markdown("---")
    user_email = st.session_state.get("user_email", "Unknown")
    st.sidebar.markdown(f"👤 **Logged in as:**  \n{user_email}")

    if st.sidebar.button("🚪 Logout", type="secondary", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.sidebar.markdown("---")

    # ADMIN: Skip subscription check for admin users
    ADMIN_EMAILS = ["ruben.rajkowski@gmail.com"]
    user_email = st.session_state.get("user_email", "")
    if user_email in ADMIN_EMAILS:
        st.sidebar.success("✅ **Admin Access**")
        st.sidebar.caption("Subscription check bypassed")
        return True

    # Check if we're running locally - skip Stripe check for localhost
    is_localhost = os.getenv("IS_LOCAL", "").lower() == "true"
    if not is_localhost:
        try:
            is_localhost = st.secrets.get("IS_LOCAL", False)
        except (KeyError, FileNotFoundError, AttributeError):
            is_localhost = False

    # LOCALHOST: Skip Stripe subscription check for development
    if is_localhost:
        st.sidebar.success("✅ **Development Mode**")
        st.sidebar.caption("Stripe subscription check disabled")
        return True

    # Now check subscription with custom Stripe integration
    try:
        import stripe

        # Get configuration from environment variables first, then secrets.toml
        testing_mode_str = os.getenv('TESTING_MODE')
        if not testing_mode_str:
            try:
                testing_mode_str = st.secrets.get("TESTING_MODE", 'false')
            except (KeyError, FileNotFoundError, AttributeError):
                testing_mode_str = 'false'
        testing_mode = str(testing_mode_str).lower() == 'true'

        # Get Stripe API key based on mode (env vars first, then secrets.toml)
        if testing_mode:
            stripe_api_key = os.getenv('STRIPE_API_KEY_TEST')
            if not stripe_api_key:
                try:
                    stripe_api_key = st.secrets.get("STRIPE_API_KEY_TEST")
                except (KeyError, FileNotFoundError, AttributeError):
                    pass

            # Get all 3 pricing tier links
            stripe_1_month_link = os.getenv('STRIPE_1_MONTH_LINK_TEST')
            if not stripe_1_month_link:
                try:
                    stripe_1_month_link = st.secrets.get(
                        "STRIPE_1_MONTH_LINK_TEST")
                except (KeyError, FileNotFoundError, AttributeError):
                    pass

            stripe_3_month_link = os.getenv('STRIPE_3_MONTH_LINK_TEST')
            if not stripe_3_month_link:
                try:
                    stripe_3_month_link = st.secrets.get(
                        "STRIPE_3_MONTH_LINK_TEST")
                except (KeyError, FileNotFoundError, AttributeError):
                    pass

            stripe_1_year_link = os.getenv('STRIPE_1_YEAR_LINK_TEST')
            if not stripe_1_year_link:
                try:
                    stripe_1_year_link = st.secrets.get(
                        "STRIPE_1_YEAR_LINK_TEST")
                except (KeyError, FileNotFoundError, AttributeError):
                    pass
        else:
            stripe_api_key = os.getenv('STRIPE_API_KEY')
            if not stripe_api_key:
                try:
                    stripe_api_key = st.secrets.get("STRIPE_API_KEY")
                except (KeyError, FileNotFoundError, AttributeError):
                    pass

            # Get all 3 pricing tier links
            stripe_1_month_link = os.getenv('STRIPE_1_MONTH_LINK')
            if not stripe_1_month_link:
                try:
                    stripe_1_month_link = st.secrets.get("STRIPE_1_MONTH_LINK")
                except (KeyError, FileNotFoundError, AttributeError):
                    pass

            stripe_3_month_link = os.getenv('STRIPE_3_MONTH_LINK')
            if not stripe_3_month_link:
                try:
                    stripe_3_month_link = st.secrets.get("STRIPE_3_MONTH_LINK")
                except (KeyError, FileNotFoundError, AttributeError):
                    pass

            stripe_1_year_link = os.getenv('STRIPE_1_YEAR_LINK')
            if not stripe_1_year_link:
                try:
                    stripe_1_year_link = st.secrets.get("STRIPE_1_YEAR_LINK")
                except (KeyError, FileNotFoundError, AttributeError):
                    pass

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
        user_email = st.session_state.get("user_email", "")

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
        subscription = subscriptions.data[0]

        # Get subscription details
        from datetime import datetime, timezone

        try:
            # Get the product ID to determine tier
            product_id = subscription.get('items', {}).get('data', [{}])[
                0].get('price', {}).get('product', '')
            interval = subscription.get('items', {}).get('data', [{}])[0].get(
                'price', {}).get('recurring', {}).get('interval', '')
            interval_count = subscription.get('items', {}).get('data', [{}])[0].get(
                'price', {}).get('recurring', {}).get('interval_count', 1)

            # Map product IDs to tier names
            PRODUCT_TIERS = {
                'prod_TQLcQmFlr3W7T5': ('📅 Monthly', '$10/month'),
                'prod_TQLkZpTCY1p6pc': ('📆 Quarterly', '$25/3 months'),
                'prod_TRmeyctxe4nDsL': ('📅 Yearly', '$100/year'),
            }

            # Determine tier name based on product ID (fallback to interval)
            if product_id in PRODUCT_TIERS:
                tier_name, tier_cost = PRODUCT_TIERS[product_id]
            elif interval == 'month' and interval_count == 1:
                tier_name = "📅 Monthly"
                tier_cost = "$10/month"
            elif interval == 'month' and interval_count == 3:
                tier_name = "📆 Quarterly"
                tier_cost = "$25/3 months"
            elif interval == 'year':
                tier_name = "📅 Yearly"
                tier_cost = "$100/year"
            else:
                tier_name = "💎 Premium"
                tier_cost = ""

            # Calculate remaining time - use .get() with fallback
            current_period_end = subscription.get('current_period_end')

            if current_period_end:
                end_date = datetime.fromtimestamp(
                    current_period_end, tz=timezone.utc)
                now = datetime.now(timezone.utc)
                remaining = end_date - now

                days_remaining = remaining.days
                months_remaining = days_remaining // 30
                days_in_month = days_remaining % 30

                # Format duration display
                if days_remaining > 30:
                    duration_text = f"{months_remaining} month{'s' if months_remaining != 1 else ''}, {days_in_month} day{'s' if days_in_month != 1 else ''}"
                else:
                    duration_text = f"{days_remaining} day{'s' if days_remaining != 1 else ''}"

                # Format expiration date
                expiration_date = end_date.strftime("%b %d, %Y")
            else:
                # Fallback if no period end date
                duration_text = "Active"
                expiration_date = "N/A"

            # Check if subscription will auto-renew
            cancel_at_period_end = subscription.get(
                'cancel_at_period_end', False)

            # Display subscription info in sidebar
            st.sidebar.success("✅ **Active Subscription**")
            st.sidebar.markdown(f"**Plan:** {tier_name}")
            if tier_cost:
                st.sidebar.markdown(f"**Price:** {tier_cost}")

            # Create Stripe Customer Portal session for managing subscription
            try:
                # Get the return URL (current page)
                return_url = "https://ragepicks.com/"

                # Create a customer portal session
                portal_session = stripe.billing_portal.Session.create(
                    customer=customer["id"],
                    return_url=return_url,
                )

                # Add manage subscription link (aligned with other text)
                st.sidebar.markdown(
                    f"[⚙️ Manage Subscription]({portal_session.url})")
            except Exception:
                # Fallback if portal session creation fails
                pass

            # Show renewal/cancellation info if available
            if current_period_end:
                if cancel_at_period_end:
                    st.sidebar.warning(f"⚠️ **Cancels:** {expiration_date}")
                    st.sidebar.caption(f"({duration_text} remaining)")
                else:
                    st.sidebar.info(f"🔄 **Renews:** {expiration_date}")
                    st.sidebar.caption(f"({duration_text} remaining)")

        except Exception as e:
            # If we can't parse subscription details, just show basic info
            st.sidebar.success("✅ **Active Subscription**")
            st.sidebar.caption(f"Debug: {str(e)}")
            # Log the subscription object for debugging
            st.sidebar.caption(
                f"Subscription keys: {list(subscription.keys())}")

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
    # Check if we're running locally using IS_LOCAL flag
    is_localhost = os.getenv("IS_LOCAL", "").lower() == "true"
    if not is_localhost:
        try:
            is_localhost = st.secrets.get("IS_LOCAL", False)
        except (KeyError, FileNotFoundError, AttributeError):
            is_localhost = False

    # LOCALHOST: Enable admin for local development without auth
    if is_localhost:
        return True

    # Check if user is logged in
    if not st.session_state.get("is_logged_in", False):
        return False

    # List of admin emails
    ADMIN_EMAILS = [
        "ruben.rajkowski@gmail.com"
    ]

    user_email = st.session_state.get("user_email", "")
    return user_email in ADMIN_EMAILS


def add_auth_to_page():
    """
    Add authentication to a page. Call this at the top of each page that requires auth.
    """
    return check_authentication()
