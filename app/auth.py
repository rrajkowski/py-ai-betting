# app/auth.py
"""
Authentication wrapper for st-paywall that handles both local and cloud environments.
"""
import streamlit as st


def check_authentication():
    """
    Check if user is authenticated and subscribed.

    Returns:
        bool: True if user is authenticated and subscribed, False otherwise
    """
    # Check if st.user is available AND has the required attributes
    # (Streamlit Cloud with native auth enabled)
    try:
        # Try to access st.user.is_logged_in
        # This will raise AttributeError if not available
        _ = st.user.is_logged_in

        # If we get here, st.user is properly configured
        # Import and use st-paywall
        from st_paywall import add_auth

        # This will handle authentication and subscription check
        add_auth(required=True)
        return True

    except AttributeError:
        # st.user is not available or not properly configured
        # This is expected in local development
        # Local development mode - show warning and allow access
        if st.session_state.get('show_auth_warning', True):
            st.warning("""
            ⚠️ **Development Mode**: Authentication is disabled for local testing.

            """)
            st.session_state.show_auth_warning = False

        return True

    except Exception as e:
        # Some other error occurred
        st.error(f"⚠️ Authentication error: {e}")
        st.info(
            "Running in development mode. See AUTHENTICATION_FIX.md for setup instructions.")
        return True


def add_auth_to_page():
    """
    Add authentication to a page. Call this at the top of each page that requires auth.
    """
    return check_authentication()
