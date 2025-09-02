# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# utils/auth_utils.py
"""Common authentication utilities for ViolentUTF pages.

Provides consistent token management and authentication handling.
"""
import logging
import os
from typing import Optional, cast

import requests
import streamlit as st
from utils.token_manager import token_manager

logger = logging.getLogger(__name__)

# API Configuration for status checks
_raw_api_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = _raw_api_url.rstrip("/api").rstrip("/")
if not API_BASE_URL:
    API_BASE_URL = "http://localhost:9080"


def get_compact_api_status() -> tuple:
    """Get compact API status for sidebar display.

    Returns:
        tuple: (status_text, status_type, icon) where status_type is 'success', 'warning', or 'error'

    """
    try:

        # Use JWT manager to get valid token (with auto-refresh)
        from utils.jwt_manager import jwt_manager

        token = jwt_manager.get_valid_token()

        if not token:
            # Check if refresh is in progress
            refresh_status = jwt_manager.get_refresh_status()
            if refresh_status["refresh_in_progress"]:
                return ("API: Refreshing...", "warning", "🔄")
            elif refresh_status.get("last_error"):
                return ("API: Refresh Failed", "error", "🔑")
            else:
                return ("API: No Token", "warning", "🔑")

        # Quick API health check with auto-refreshed token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # SECURITY FIX: Remove hardcoded IP headers that can be used for spoofing
            # Only include gateway identification header
            "X-API-Gateway": "APISIX",
        }
        response = requests.get(f"{API_BASE_URL}/api/v1/auth/token/info", headers=headers, timeout=5)

        if response.status_code == 200:
            return ("API: Ready", "success", "🔑")
        elif response.status_code == 401:
            return ("API: Auth Failed", "error", "🔑")
        else:
            return ("API: Error", "error", "🔑")
    except Exception as e:
        logger.warning("API status check failed: %s", e)
        return ("API: Offline", "error", "🔑")


def get_compact_database_status() -> tuple:
    """Get compact database status for sidebar display.

    Returns:
        tuple: (status_text, status_type, icon) where status_type is 'success', 'warning', or 'error'

    """
    try:

        # Use JWT manager to get valid token (with auto-refresh)
        from utils.jwt_manager import jwt_manager

        token = jwt_manager.get_valid_token()

        if not token:
            return ("DB: No Token", "warning", "🗃️")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # SECURITY FIX: Remove hardcoded IP headers that can be used for spoofing
            # Only include gateway identification header
            "X-API-Gateway": "APISIX",
        }
        response = requests.get(f"{API_BASE_URL}/api/v1/database/status", headers=headers, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get("is_initialized"):
                return ("DB: Ready", "success", "🗃️")
            else:
                return ("DB: Not Init", "warning", "🗃️")
        else:
            return ("DB: Error", "error", "🗃️")
    except Exception as e:
        logger.warning("Database status check failed: %s", e)
        return ("DB: Offline", "error", "🗃️")


def handle_authentication_and_sidebar(page_name: str = "") -> Optional[str]:
    """Handle Standard authentication for all ViolentUTF pages.

    Args:
        page_name: Name of the current page for logging

    Returns:
        str: Username if authenticated, None otherwise
    """
    # Initialize session state for login tracking if not present

    if "previously_logged_in" not in st.session_state:
        st.session_state["previously_logged_in"] = False

    # Check if st.user is available (Streamlit Community Cloud)
    # If not, fallback to Keycloak authentication
    try:
        user_logged_in = st.user.is_logged_in
    except AttributeError:
        # st.user not available - use Keycloak authentication
        logger.info("st.user not available, using Keycloak authentication")
        from .auth_utils_keycloak import handle_authentication_and_sidebar as keycloak_auth

        return keycloak_auth(page_name)

    # Check if login state has changed since last run
    if user_logged_in != st.session_state["previously_logged_in"]:
        st.session_state["previously_logged_in"] = user_logged_in
        user_identifier = st.user.name or st.user.email or "Unknown User"
        log_action = "logged in" if user_logged_in else "logged out"
        page_info = f" on {page_name}" if page_name else ""
        logger.info("User %s%s: %s", log_action, page_info, user_identifier)

        if user_logged_in:
            # User just logged in - create API token using JWT manager
            try:
                from utils.jwt_manager import jwt_manager

                # Create mock Keycloak data from Streamlit user info
                keycloak_data = {
                    "preferred_username": st.user.name or st.user.email or "streamlit_user",
                    "email": st.user.email or "user@example.com",
                    "name": st.user.name or "Streamlit User",
                    "sub": st.user.email or "streamlit-user",
                    "roles": ["ai-api-access"],  # Grant AI access to Streamlit users
                }

                # Create API token for FastAPI access
                api_token = jwt_manager.create_token(keycloak_data)
                if api_token:
                    st.session_state["api_token"] = api_token
                    st.session_state["has_ai_access"] = True
                    logger.info("API token created for Streamlit user: %s", user_identifier)
                else:
                    logger.warning("Could not create API token for user: %s", user_identifier)
                    st.session_state["api_token"] = None
                    st.session_state["has_ai_access"] = False

                # Also try to get Keycloak token from token manager for compatibility
                token = token_manager.extract_user_token()
                if token:
                    st.session_state["access_token"] = token
                    logger.info("Keycloak token extracted for user: %s", user_identifier)
                else:
                    # Use API token as access token fallback
                    st.session_state["access_token"] = api_token
                    logger.info("Using API token as access token for user: %s", user_identifier)

            except Exception as e:
                logger.error("Error creating tokens for user %s: %s", user_identifier, e)
                st.session_state["access_token"] = None
                st.session_state["api_token"] = None
                st.session_state["has_ai_access"] = False
        else:
            # User logged out - clear all session state
            clear_user_session()

    # If user is not logged in, display login prompt and stop execution
    if not user_logged_in:
        st.title("Please Log In")
        info_message = (
            f"You need to log in to access {page_name}." if page_name else "You need to log in to access this page."
        )
        st.info(info_message)

        try:
            st.login("keycloak")
        except Exception as e:
            logger.error("Login provider issue or not configured: %s", e)
            st.login()  # Fallback to default login
        st.stop()  # Stop script execution for non-logged-in users
        return None  # This line won't be reached but satisfies mypy
    else:
        # If user is logged in, display sidebar greeting and logout button
        return show_authenticated_sidebar(page_name)


def show_authenticated_sidebar(page_name: str = "") -> str:
    """Display authenticated user sidebar with token status.

    Args:
        page_name: Name of current page for logout button key

    Returns:
        str: Username of authenticated user
    """
    with st.sidebar:

        user_name_raw = st.user.name or st.user.email or "User"
        user_name = str(user_name_raw)

        # Update user_name in session state if changed
        if st.session_state.get("user_name") != user_name:
            st.session_state["user_name"] = user_name
            # If username changes, DB needs re-initialization
            st.session_state["db_initialized"] = False
            st.session_state["db_path"] = None
            logger.info("User changed or logged in: %s. Resetting DB state.", user_name)

        st.success(f"Hello, {user_name}!")

        # Ensure API tokens are created for the logged-in user
        if not st.session_state.get("api_token"):
            try:
                from utils.jwt_manager import jwt_manager

                keycloak_data = {
                    "preferred_username": st.user.name or st.user.email or "streamlit_user",
                    "email": st.user.email or "user@example.com",
                    "name": st.user.name or "Streamlit User",
                    "sub": st.user.email or "streamlit-user",
                    "roles": ["ai-api-access"],  # Grant AI access to Streamlit users
                }

                api_token = jwt_manager.create_token(keycloak_data)
                if api_token:
                    st.session_state["api_token"] = api_token
                    st.session_state["has_ai_access"] = True
                    logger.info("API token created for Streamlit user: %s", user_name)
            except Exception as e:
                logger.error("Error creating API token for user %s: %s", user_name, e)

        # Display enhanced AI API access status with JWT info
        has_api_token = bool(st.session_state.get("api_token"))
        has_ai_access = st.session_state.get("has_ai_access", False)

        if has_api_token and has_ai_access:
            # Get JWT refresh status
            try:
                from utils.jwt_manager import jwt_manager

                refresh_status = jwt_manager.get_refresh_status()

                status = refresh_status["status"]
                minutes_remaining = refresh_status["time_remaining_minutes"]

                if status == "refreshing":
                    st.info("🔄 AI Gateway: Refreshing Token...")
                elif status == "expired":
                    st.error("⏰ AI Gateway: Token Expired")
                    if refresh_status.get("last_error"):
                        st.caption(f"Error: {refresh_status['last_error'][:50]}...")
                elif status == "expiring_soon":
                    st.warning(f"⚠️ AI Gateway: Expires in {minutes_remaining}m")
                    if refresh_status["refresh_in_progress"]:
                        st.caption("Auto-refresh in progress...")
                else:  # active
                    st.success(f"🚀 AI Gateway: Active ({minutes_remaining}m left)")

            except Exception:
                # Fallback to simple display
                st.success("🚀 AI Gateway Access: Enabled")
        else:
            st.warning("🔒 AI Gateway Access: Disabled")
            if not has_api_token:
                st.caption("No API token available")
            else:
                st.caption("Contact admin to enable ai-api-access role")

        # Display compact API and Database status
        try:
            api_text, api_type, api_icon = get_compact_api_status()
            db_text, db_type, db_icon = get_compact_database_status()

            # Display API status
            if api_type == "success":
                st.success(f"{api_icon} {api_text}")
            elif api_type == "warning":
                st.warning(f"{api_icon} {api_text}")
            else:
                st.error(f"{api_icon} {api_text}")

            # Display Database status
            if db_type == "success":
                st.success(f"{db_icon} {db_text}")
            elif db_type == "warning":
                st.warning(f"{db_icon} {db_text}")
            else:
                st.error(f"{db_icon} {db_text}")
        except Exception as e:
            # Fallback if status check fails
            logger.warning("Status check failed: %s", e)
            st.warning("🔑 API: Check Failed")
            st.warning("🗃️ DB: Check Failed")

        # JWT Token Display (collapsed by default)
        with st.expander("🔐 Developer Tools", expanded=False):
            st.subheader("JWT Token")
            if st.session_state.get("api_token"):
                st.code(st.session_state["api_token"], language=None)
                if st.button("📋 Copy Token", key=f"copy_jwt_{page_name}"):
                    st.write("Token copied! Use it with:")
                    st.code('curl -H "Authorization: Bearer <token>" ...', language="bash")
            else:
                st.warning("No JWT token available. Please ensure you're logged in.")

        st.divider()

        # Create unique logout button key
        logout_key = f"sidebar_logout_{page_name.lower().replace(' ', '_')}" if page_name else "sidebar_logout"

        if st.button("Logout", key=logout_key):
            logger.info("User '%s' clicked logout from %s.", user_name, page_name)
            st.session_state["previously_logged_in"] = False
            clear_user_session()
            st.logout()

    return user_name


def clear_user_session() -> None:
    """Clear all user-related session state."""
    st.session_state["user_name"] = None

    st.session_state["db_initialized"] = False
    st.session_state["db_path"] = None
    st.session_state["access_token"] = None
    st.session_state["has_ai_access"] = False
    # Clear API token and API-related session data
    st.session_state["api_token"] = None
    st.session_state["api_user_info"] = {}
    st.session_state["api_session_data"] = {}
    st.session_state["api_config_params"] = {}
    st.session_state["api_db_initialized"] = False


def get_current_token() -> Optional[str]:
    """Get current user's JWT token with validation.

    Returns:
        str: Valid JWT token or None if not available/expired
    """
    try:

        if not st.user.is_logged_in:
            return None
    except AttributeError:
        # st.user not available, check for API token instead
        return cast(Optional[str], st.session_state.get("api_token"))

    token = st.session_state.get("access_token")
    if token and token_manager._is_token_valid(token):  # pylint: disable=protected-access
        return cast(str, token)

    # Try to refresh token
    fresh_token = token_manager.extract_user_token()
    if fresh_token:
        st.session_state["access_token"] = fresh_token
        st.session_state["has_ai_access"] = token_manager.has_ai_access(fresh_token)
        return cast(str, fresh_token)

    # Fallback to API token
    api_token = st.session_state.get("api_token")
    if api_token:
        return cast(str, api_token)

    # No valid token available
    st.session_state["access_token"] = None
    st.session_state["has_ai_access"] = False
    return None


def check_ai_access() -> bool:
    """Check if current user has AI API access.

    Returns:
        bool: True if user has ai-api-access role
    """
    return cast(bool, st.session_state.get("has_ai_access", False))


def ensure_ai_access() -> None:
    """Ensure user has AI access or display error and stop.

    Use this in pages that require AI Gateway access.
    """
    if not check_ai_access():

        st.error("🔒 Access Denied")
        st.info("You need the 'ai-api-access' role to use AI Gateway features.")
        st.info("Please contact your administrator to request access.")
        st.stop()


def get_api_token() -> Optional[str]:
    """Get the current API token for FastAPI backend access.

    Returns:
        str: API token if available, None otherwise
    """
    return cast(Optional[str], st.session_state.get("api_token"))


def has_api_access() -> bool:
    """Check if current user has API backend access.

    Returns:
        bool: True if API token is available
    """
    return bool(st.session_state.get("api_token"))


def get_api_headers() -> dict:
    """Get authentication headers for API requests.

    Returns:
        dict: Headers with Authorization and other necessary fields
    """
    token = get_api_token()

    if not token:
        return {}

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        # SECURITY FIX: Remove hardcoded IP headers that can be used for spoofing
        # Only include gateway identification header
        "X-API-Gateway": "APISIX",
    }
