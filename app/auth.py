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

        # Only show warning on localhost (not on Streamlit Cloud)
        # Use multiple methods to detect if running locally
        import os

        # Method 1: Check secrets for IS_LOCAL flag (most reliable)
        # Add IS_LOCAL = true to your local .streamlit/secrets.toml
        # Do NOT add it to Streamlit Cloud secrets
        is_localhost = st.secrets.get('IS_LOCAL', False)

        # Method 2: If IS_LOCAL not set, try environment detection
        if not is_localhost:
            # Check for Streamlit Cloud environment variables
            is_cloud = bool(os.getenv('STREAMLIT_SHARING_MODE') or
                            os.getenv('STREAMLIT_CLOUD') or
                            os.getenv('STREAMLIT_SERVER_HEADLESS'))

            # Check if hostname contains 'streamlit'
            hostname = os.getenv('HOSTNAME', '')
            if 'streamlit' in hostname.lower():
                is_cloud = True

            # Check server address from config
            try:
                from streamlit import config
                server_address = config.get_option('server.address')
                if server_address and server_address not in ['localhost', '127.0.0.1', '0.0.0.0', '']:
                    is_cloud = True
            except Exception:
                pass

            is_localhost = not is_cloud

        if is_localhost and st.session_state.get('show_auth_warning', True):
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
