# app/auth.py
"""
Authentication wrapper with Streamlit native OIDC and Stripe integration.
Uses st.login(), st.user, and st.logout() for authentication.
"""
import os
from datetime import UTC

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_config(key: str, default=None):
    """
    Get a configuration value from environment variables first, then st.secrets.

    This eliminates the repetitive pattern of:
        value = os.getenv('KEY')
        if not value:
            try:
                value = st.secrets.get("KEY")
            except (KeyError, FileNotFoundError, AttributeError):
                pass

    Args:
        key: The configuration key to look up.
        default: Default value if not found in either source.

    Returns:
        The configuration value, or default if not found.
    """
    value = os.getenv(key)
    if value is not None:
        return value
    try:
        value = st.secrets.get(key)
        if value is not None:
            return value
    except (KeyError, FileNotFoundError, AttributeError):
        pass
    return default


@st.cache_data(ttl=300, show_spinner=False)
def _get_stripe_subscription_status(stripe_api_key: str, user_email: str) -> dict:
    """
    Cached Stripe subscription lookup. Avoids ~500ms API calls on every page load.

    Results are cached for 5 minutes (ttl=300) per user_email.

    Returns:
        dict with keys: has_customer, customer_id, has_subscription, subscription
    """
    import stripe
    stripe.api_key = stripe_api_key

    customers = stripe.Customer.list(email=user_email)
    if not customers.data:
        return {"has_customer": False, "customer_id": None, "has_subscription": False, "subscription": None}

    customer = customers.data[0]
    subscriptions = stripe.Subscription.list(customer=customer["id"])

    if len(subscriptions.data) == 0:
        return {"has_customer": True, "customer_id": customer["id"], "has_subscription": False, "subscription": None}

    # Convert subscription to a plain dict so it's serializable for caching
    sub = subscriptions.data[0]
    return {
        "has_customer": True,
        "customer_id": customer["id"],
        "has_subscription": True,
        "subscription": dict(sub),
    }


def check_authentication():
    """
    Check if user is authenticated and subscribed using Streamlit native OIDC + Stripe.

    Uses st.login(), st.user, and st.logout() for authentication.
    Stripe subscription check is performed after authentication.

    Returns:
        bool: True if user is authenticated and subscribed, False otherwise
    """

    # Check if we're running locally using IS_LOCAL flag
    is_localhost = str(get_config("IS_LOCAL", "")).lower() == "true"

    # LOCALHOST: Skip authentication for development
    if is_localhost:
        return True

    # Check if user is logged in using Streamlit native auth
    if not st.user.is_logged_in:
        # Show login UI
        st.info("🔐 **Please log in to access this app**")

        # Create a centered login button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
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

    # ADMIN: Skip subscription check for admin users
    ADMIN_EMAILS = ["ruben.rajkowski@gmail.com"]
    if st.user.email in ADMIN_EMAILS:
        st.sidebar.success("✅ **Admin Access**")
        st.sidebar.caption("Subscription check bypassed")
        return True

    # Check if we're running locally - skip Stripe check for localhost
    is_localhost = str(get_config("IS_LOCAL", "")).lower() == "true"

    # LOCALHOST: Skip Stripe subscription check for development
    if is_localhost:
        st.sidebar.success("✅ **Development Mode**")
        st.sidebar.caption("Stripe subscription check disabled")
        return True

    # Now check subscription with custom Stripe integration
    try:
        import stripe

        # Get configuration using get_config() helper (env vars first, then secrets.toml)
        testing_mode = str(get_config(
            "TESTING_MODE", "false")).lower() == "true"

        # Determine key suffix based on mode
        suffix = "_TEST" if testing_mode else ""

        # Get Stripe API key (try SECRET_KEY first, then API_KEY for legacy support)
        stripe_api_key = get_config(f"STRIPE_SECRET_KEY{suffix}") or get_config(
            f"STRIPE_API_KEY{suffix}")

        # Get all 3 pricing tier links
        stripe_1_month_link = get_config(f"STRIPE_1_MONTH_LINK{suffix}")
        stripe_3_month_link = get_config(f"STRIPE_3_MONTH_LINK{suffix}")
        stripe_1_year_link = get_config(f"STRIPE_1_YEAR_LINK{suffix}")

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

        # Use cached Stripe lookup to avoid ~500ms API calls on every page load
        sub_status = _get_stripe_subscription_status(
            stripe_api_key, user_email)

        if not sub_status["has_customer"]:
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
        customer_id = sub_status["customer_id"]

        if not sub_status["has_subscription"]:
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
        subscription = sub_status["subscription"]

        # Get subscription details
        from datetime import datetime

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
                    current_period_end, tz=UTC)
                now = datetime.now(UTC)
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
                    customer=customer_id,
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
            st.sidebar.caption(f"Debug: {e!s}")
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
    is_localhost = str(get_config("IS_LOCAL", "")).lower() == "true"

    # LOCALHOST: Enable admin for local development without auth
    if is_localhost:
        return True

    # Check if user is logged in using native auth
    try:
        if not st.user.is_logged_in:
            return False

        ADMIN_EMAILS = ["ruben.rajkowski@gmail.com"]
        return st.user.email in ADMIN_EMAILS
    except AttributeError:
        return False


def add_auth_to_page():
    """
    Add authentication to a page. Call this at the top of each page that requires auth.
    """
    return check_authentication()
