import hashlib
import json
import os
import pathlib
import shutil
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional

import jwt
import pandas as pd
import requests
import streamlit as st
import yaml

# Load environment variables from .env file
from dotenv import load_dotenv

# Get the path to the .env file relative to this script
env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Use the centralized logging setup
from utils.logging import get_logger

logger = get_logger(__name__)

# App configuration
app_version = "0.2"
app_title = "ViolentUTF"
app_description = "Configure and launch AI red-teaming"
app_icon = "🚀"

# API Configuration - MUST go through APISIX Gateway
# Fix the API base URL - remove any trailing /api path
_raw_api_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = _raw_api_url.rstrip("/api").rstrip("/")  # Remove /api suffix if present
if not API_BASE_URL:
    API_BASE_URL = "http://localhost:9080"  # Fallback if URL becomes empty
API_ENDPOINTS = {
    "auth_token_info": f"{API_BASE_URL}/api/v1/auth/token/info",
    "auth_token_validate": f"{API_BASE_URL}/api/v1/auth/token/validate",
    "database_initialize": f"{API_BASE_URL}/api/v1/database/initialize",
    "database_status": f"{API_BASE_URL}/api/v1/database/status",
    "database_stats": f"{API_BASE_URL}/api/v1/database/stats",
    "database_reset": f"{API_BASE_URL}/api/v1/database/reset",
    "sessions": f"{API_BASE_URL}/api/v1/sessions",
    "sessions_reset": f"{API_BASE_URL}/api/v1/sessions/reset",
    "config_parameters": f"{API_BASE_URL}/api/v1/config/parameters",
    "config_environment": f"{API_BASE_URL}/api/v1/config/environment",
    "config_generate_salt": f"{API_BASE_URL}/api/v1/config/environment/generate-salt",
    "files_upload": f"{API_BASE_URL}/api/v1/files/upload",
    "files_list": f"{API_BASE_URL}/api/v1/files",
}

# Initialize session state for API-backed parameters
if "api_config_params" not in st.session_state:
    st.session_state.api_config_params = {}
if "api_db_initialized" not in st.session_state:
    st.session_state.api_db_initialized = False
if "api_token" not in st.session_state:
    st.session_state.api_token = None
if "api_user_info" not in st.session_state:
    st.session_state.api_user_info = {}
if "api_session_data" not in st.session_state:
    st.session_state.api_session_data = {}


# --- API Helper Functions ---


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    try:
        from utils.jwt_manager import jwt_manager

        # Get valid token (automatically handles refresh if needed)
        token = jwt_manager.get_valid_token()

        # If no valid JWT token, try to create one
        if not token and st.session_state.get("access_token"):
            token = create_compatible_api_token()

        if not token:
            return {}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            # SECURITY FIX: Remove hardcoded IP headers that can be used for spoofing
            # Only include gateway identification header
            "X-API-Gateway": "APISIX",
        }

        # Add APISIX API key for AI model access
        apisix_api_key = (
            os.getenv("VIOLENTUTF_API_KEY")
            or os.getenv("APISIX_API_KEY")
            or os.getenv("AI_GATEWAY_API_KEY")
        )
        if apisix_api_key:
            headers["apikey"] = apisix_api_key

        return headers
    except Exception as e:
        logger.error(f"Failed to get auth headers: {e}")
        return {}


def api_request(method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Make an authenticated API request through APISIX Gateway"""
    headers = get_auth_headers()
    if not headers.get("Authorization"):
        st.error("No authentication token available. Please log in.")
        return None

    try:
        logger.debug(f"Making {method} request to {url} through APISIX Gateway")
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            # Attempt to refresh token and retry once
            logger.warning("401 Unauthorized - attempting token refresh")
            try:
                # Clear existing tokens
                if "api_token" in st.session_state:
                    del st.session_state["api_token"]

                # Force JWT manager to refresh secret from environment
                from utils.jwt_manager import jwt_manager

                jwt_manager._cached_secret = None  # Clear cached secret
                jwt_manager._secret_cache_time = None
                jwt_manager._load_environment()  # Reload environment variables

                # Create new token
                new_token = create_compatible_api_token()
                if new_token:
                    st.session_state["api_token"] = new_token

                    # Retry the request with new token
                    fresh_headers = get_auth_headers()
                    if fresh_headers.get("Authorization"):
                        logger.info("Retrying request with refreshed token")
                        retry_response = requests.request(
                            method, url, headers=fresh_headers, timeout=30, **kwargs
                        )
                        if retry_response.status_code == 200:
                            st.success("🔄 Token refreshed successfully!")
                            return retry_response.json()
                        else:
                            logger.error(
                                f"Retry failed with status {retry_response.status_code}"
                            )

            except Exception as e:
                logger.error(f"Token refresh failed: {e}")

            st.error("Authentication failed. Please refresh your token.")
            logger.error(f"401 Unauthorized: {response.text}")
            return None
        elif response.status_code == 403:
            st.error("Access forbidden. Check your permissions or APISIX routing.")
            logger.error(f"403 Forbidden: {response.text}")
            return None
        elif response.status_code == 404:
            st.error(f"Endpoint not found. Check APISIX routing configuration.")
            logger.error(f"404 Not Found: {url} - {response.text}")
            return None
        elif response.status_code == 502:
            st.error("Bad Gateway. APISIX cannot reach the FastAPI service.")
            logger.error(f"502 Bad Gateway: {response.text}")
            return None
        elif response.status_code == 503:
            st.error("Service Unavailable. FastAPI service may be down.")
            logger.error(f"503 Service Unavailable: {response.text}")
            return None
        else:
            st.error(f"API request failed: {response.status_code} - {response.text}")
            logger.error(f"API Error {response.status_code}: {url} - {response.text}")
            return None
    except requests.exceptions.ConnectionError as e:
        st.error(
            f"Connection error: Cannot reach APISIX Gateway at {API_BASE_URL}. Is it running?"
        )
        logger.error(f"Connection error to {url}: {e}")
        return None
    except requests.exceptions.Timeout as e:
        st.error(
            "Request timeout. APISIX Gateway or backend service is slow to respond."
        )
        logger.error(f"Timeout error to {url}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"API request error: {e}")
        logger.error(f"Request exception to {url}: {e}")
        return None


def load_user_session_from_api():
    """Load user session data from API"""
    data = api_request("GET", API_ENDPOINTS["sessions"])
    if data:
        st.session_state.api_session_data = data
        return True
    return False


def save_user_session_to_api(session_update: Dict[str, Any]):
    """Save user session data to API"""
    data = api_request("PUT", API_ENDPOINTS["sessions"], json=session_update)
    if data:
        st.session_state.api_session_data = data
        return True
    return False


def create_compatible_api_token():
    """Create a FastAPI-compatible token using JWT manager"""
    try:
        from utils.jwt_manager import jwt_manager
        from utils.user_context import get_user_context_for_token

        # Get consistent user context regardless of authentication source
        user_context = get_user_context_for_token()
        logger.info(
            f"Creating API token for consistent user: {user_context['preferred_username']}"
        )

        # Create token with consistent user context
        api_token = jwt_manager.create_token(user_context)

        if api_token:
            logger.info("Successfully created API token using JWT manager")
            return api_token
        else:
            st.error(
                "🚨 Security Error: JWT secret key not configured. Please set JWT_SECRET_KEY environment variable."
            )
            logger.error("Failed to create API token - JWT secret key not available")
            return None

    except Exception as e:
        st.error(f"❌ Failed to generate API token. Please try refreshing the page.")
        logger.error(f"Token creation failed: {e}")
        return None


def get_token_info_from_api():
    """Get token information from API"""
    data = api_request("GET", API_ENDPOINTS["auth_token_info"])
    if data:
        st.session_state.api_user_info = data
        return data
    return None


def get_database_status_from_api():
    """Get database status from API"""
    return api_request("GET", API_ENDPOINTS["database_status"])


def initialize_database_via_api(custom_salt: Optional[str] = None):
    """Initialize database via API"""
    payload = {"force_recreate": False, "backup_existing": True}
    if custom_salt:
        payload["custom_salt"] = custom_salt

    return api_request("POST", API_ENDPOINTS["database_initialize"], json=payload)


def reset_database_via_api():
    """Reset database via API"""
    payload = {
        "confirmation": True,
        "backup_before_reset": True,
        "preserve_user_data": False,
    }
    return api_request("POST", API_ENDPOINTS["database_reset"], json=payload)


def get_database_stats_from_api():
    """Get database statistics from API"""
    return api_request("GET", API_ENDPOINTS["database_stats"])


def load_config_from_api():
    """Load configuration parameters from API"""
    return api_request("GET", API_ENDPOINTS["config_parameters"])


def get_environment_config_from_api():
    """Get environment configuration from API"""
    return api_request("GET", API_ENDPOINTS["config_environment"])


def generate_salt_via_api():
    """Generate new salt via API"""
    return api_request("POST", API_ENDPOINTS["config_generate_salt"])


# --- Main Page Function ---
def main():
    """Renders the Start page content with API backend."""
    logger.debug("Start page (API-backed) loading.")
    st.set_page_config(
        page_title=app_title,
        page_icon=app_icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- Authentication and Sidebar ---
    handle_authentication_and_sidebar("Start (API)")

    # --- Page Content ---
    display_header()

    # Check authentication status - allow both Keycloak SSO and environment-based auth
    has_keycloak_token = bool(st.session_state.get("access_token"))
    has_env_credentials = bool(os.getenv("KEYCLOAK_USERNAME"))

    if not has_keycloak_token and not has_env_credentials:
        st.warning(
            "⚠️ Authentication required: Please log in via Keycloak SSO or configure KEYCLOAK_USERNAME in environment."
        )
        st.info(
            "💡 For local development, you can set KEYCLOAK_USERNAME and KEYCLOAK_PASSWORD in your .env file"
        )
        return

    # Automatically generate API token if not present
    if not st.session_state.get("api_token"):
        with st.spinner("Generating API token..."):
            api_token = create_compatible_api_token()
            if not api_token:
                st.error(
                    "❌ Failed to generate API token. Please try refreshing the page."
                )
                return

    # Load user information automatically on first load
    if not st.session_state.get("api_user_info"):
        get_token_info_from_api()

    # --- Load Configuration Parameters ---
    config_data = load_config_from_api()
    if config_data:
        st.session_state.api_config_params = config_data.get("parameters", {})

    # Display loaded configuration
    if st.session_state.api_config_params:
        with st.expander("View Loaded Configuration Parameters"):
            st.json(st.session_state.api_config_params)

    # --- Database Management ---
    # st.subheader("🗄️ PyRIT Memory Database")
    # st.markdown("*Manages conversation history, prompts, and scoring results*")

    # # Get database status and auto-initialize if needed
    db_status = get_database_status_from_api()

    if db_status:
        if db_status.get("is_initialized"):
            st.session_state.api_db_initialized = True
        else:
            # Auto-initialize database
            with st.spinner("Setting up database..."):
                result = initialize_database_via_api()
                if result:
                    if result.get("initialization_status") in [
                        "success",
                        "already_exists",
                    ]:
                        st.session_state.api_db_initialized = True
                    else:
                        st.session_state.api_db_initialized = False
                else:
                    st.session_state.api_db_initialized = False
    else:
        st.session_state.api_db_initialized = False

    # Database statistics button
    if st.session_state.api_db_initialized:
        if st.button(
            "📊 View DB Statistics",
            key="view_stats",
            help="Shows database usage statistics including total records, size, and table information",
        ):
            with st.spinner("Fetching database statistics..."):
                stats = get_database_stats_from_api()
                if stats:
                    st.write(f"**Total Records:** {stats.get('total_records', 0)}")
                    st.write(
                        f"**Database Size:** {stats.get('database_size_mb', 0):.2f} MB"
                    )

                    # Display table statistics
                    tables = stats.get("tables", [])
                    if tables:
                        df = pd.DataFrame(tables)
                        st.dataframe(df, use_container_width=True)

    # --- Session Management ---
    # st.subheader("👤 Session Management")
    # st.markdown("*Preserve your workflow state and preferences across sessions*")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "📥 Load Session",
            key="load_session",
            help="Restores your previous session data including UI preferences, workflow state, and temporary configurations",
        ):
            with st.spinner("Loading session from API..."):
                if load_user_session_from_api():
                    st.success("Session loaded successfully!")
                    st.rerun()

    with col2:
        if st.button(
            "💾 Save Session",
            key="save_session",
            help="Saves your current session state to preserve settings and progress for future use",
        ):
            session_update = {
                "ui_preferences": {"last_page": "Start"},
                "workflow_state": {"current_step": "configuration"},
                "temporary_data": {
                    "config_loaded": bool(st.session_state.api_config_params)
                },
            }
            with st.spinner("Saving session to API..."):
                if save_user_session_to_api(session_update):
                    st.success("Session saved successfully!")

    # Display session data
    if st.session_state.api_session_data:
        with st.expander("View Session Data"):
            st.json(st.session_state.api_session_data)

    # --- File Management ---
    # st.subheader("📁 File Management")
    # st.markdown("*Upload configuration files, datasets, and custom parameters for AI testing*")

    # uploaded_file = st.file_uploader(
    #     "Upload configuration files:",
    #     type=['yaml', 'yml', 'json', 'txt'],
    #     key="api_file_upload",
    #     help="Upload configuration files like YAML parameters, JSON settings, or text datasets that will be stored in the system"
    # )

    # if uploaded_file is not None:
    #     if st.button("📤 Upload File", key="upload_file", help="Uploads the selected file to the ViolentUTF system storage for use in configurations and datasets"):
    #         with st.spinner("Uploading file..."):
    #             files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    #             headers = get_auth_headers()
    #             headers.pop("Content-Type", None)  # Remove content-type for file upload

    #             try:
    #                 logger.debug(f"Uploading file {uploaded_file.name}")
    #                 response = requests.post(
    #                     API_ENDPOINTS["files_upload"],
    #                     headers=headers,
    #                     files=files,
    #                     timeout=60  # Longer timeout for file uploads
    #                 )
    #                 if response.status_code == 200:
    #                     result = response.json()
    #                     st.success(f"File uploaded successfully! ID: {result.get('file_id')}")
    #                     logger.info(f"File upload successful: {result.get('file_id')}")
    #                 elif response.status_code == 413:
    #                     st.error("File too large. Check upload size limits.")
    #                 else:
    #                     st.error(f"Upload failed: {response.status_code} - {response.text}")
    #                     logger.error(f"File upload failed: {response.status_code} - {response.text}")
    #             except requests.exceptions.Timeout:
    #                 st.error("Upload timeout. File may be too large or network is slow.")
    #             except Exception as e:
    #                 st.error(f"Upload error: {e}")
    #                 logger.error(f"File upload exception: {e}")

    # --- Start Button ---
    st.divider()
    start_disabled = not st.session_state.api_db_initialized

    if st.button(
        "🚀 Start Configuration Workflow",
        type="primary",
        disabled=start_disabled,
        help="Begin the AI red-teaming workflow by configuring generators, datasets, converters, and scoring engines",
    ):
        st.session_state["started"] = True
        logger.info(f"User clicked 'Start'. Navigating to Configure Generators.")
        st.switch_page("pages/1_Configure_Generators.py")


# --- Helper Functions ---

# Import centralized auth utility
from utils.auth_utils import handle_authentication_and_sidebar


def display_header():
    """Displays the main header for the page."""
    st.title(f"{app_icon} {app_title}")
    st.markdown(app_description)
    st.write(f"Version: {app_version}")


# --- Run Main Function ---
if __name__ == "__main__":
    main()
