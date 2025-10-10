# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""1 Configure Generators module."""

import json
import math
import os
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

import requests
import streamlit as st

# Load environment variables from .env file
from dotenv import load_dotenv
from utils.auth_utils import handle_authentication_and_sidebar

# Import utilities
from utils.logging import get_logger

# Get the path to the .env file relative to this script
env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = get_logger(__name__)

# API Configuration - MUST go through APISIX Gateway
_raw_api_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = _raw_api_url.rstrip("/api").rstrip("/")  # Remove /api suffix if present
if not API_BASE_URL:
    API_BASE_URL = "http://localhost:9080"  # Fallback if URL becomes empty

API_ENDPOINTS = {
    # Authentication endpoints
    "auth_token_info": f"{API_BASE_URL}/api/v1/auth/token/info",
    "auth_token_validate": f"{API_BASE_URL}/api/v1/auth/token/validate",
    # Database endpoints
    "database_status": f"{API_BASE_URL}/api/v1/database/status",
    # Generator endpoints
    "generators": f"{API_BASE_URL}/api/v1/generators",
    "generator_types": f"{API_BASE_URL}/api/v1/generators/types",
    "generator_params": f"{API_BASE_URL}/api/v1/generators/types/{{generator_type}}/params",
    "apisix_models": f"{API_BASE_URL}/api/v1/generators/apisix/models",
    "openapi_providers": f"{API_BASE_URL}/api/v1/generators/apisix/openapi-providers",
    "openapi_models": f"{API_BASE_URL}/api/v1/generators/apisix/openapi-models",
    # Orchestrator endpoints for generator testing
    "orchestrators": f"{API_BASE_URL}/api/v1/orchestrators",
    "orchestrator_create": f"{API_BASE_URL}/api/v1/orchestrators",
    "orchestrator_execute": f"{API_BASE_URL}/api/v1/orchestrators/{{orchestrator_id}}/executions",
    # Session endpoints
    "sessions": f"{API_BASE_URL}/api/v1/sessions",
    "sessions_update": f"{API_BASE_URL}/api/v1/sessions",
}

# Initialize session state for API-backed generators
if "api_generators" not in st.session_state:
    st.session_state.api_generators = {}
if "api_generator_types" not in st.session_state:
    st.session_state.api_generator_types = []
if "api_token" not in st.session_state:
    st.session_state.api_token = None
if "api_user_info" not in st.session_state:
    st.session_state.api_user_info = {}
if "api_session_data" not in st.session_state:
    st.session_state.api_session_data = {}

# --- API Helper Functions ---


def get_auth_headers() -> Dict[str, str]:
    """Get authentication header for API requests through APISIX Gateway."""
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
            os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY") or os.getenv("AI_GATEWAY_API_KEY")
        )
        if apisix_api_key:
            headers["apikey"] = apisix_api_key

        return headers
    except Exception as e:
        logger.error("Failed to get auth headers: %s", e)
        return {}


def api_request(method: str, url: str, **kwargs: Any) -> Optional[Dict[str, object]]:  # noqa: ANN401
    """Make an authenticated API request through APISIX Gateway"""
    headers = get_auth_headers()

    if not headers.get("Authorization"):
        logger.warning("No authentication token available for API request")
        st.error("❌ No authentication token available. Please refresh the page.")
        return None

    try:
        logger.debug("Making %s request to %s through APISIX Gateway", method, url)
        response = requests.request(method, url, headers=headers, timeout=30, **cast(Any, kwargs))

        if response.status_code == 200:
            json_data = response.json()
            # Handle both dict and list responses
            if isinstance(json_data, dict):
                return json_data
            else:
                # For list responses (like OpenAPI providers), return as-is
                return json_data
        elif response.status_code == 201:
            json_data = response.json()
            # Handle both dict and list responses
            if isinstance(json_data, dict):
                return json_data
            else:
                # For list responses, return as-is
                return json_data
        elif response.status_code == 400:
            logger.error("400 Bad Request: %s", response.text)
            try:
                error_detail = response.json().get("detail", response.text)
                st.error(f"❌ Request validation failed: {error_detail}")
            except Exception:
                st.error(f"❌ Bad request: {response.text}")
            return None
        elif response.status_code == 401:
            logger.error("401 Unauthorized: %s", response.text)
            st.error("❌ Authentication failed. Please refresh your token.")
            return None
        elif response.status_code == 403:
            logger.error("403 Forbidden: %s", response.text)
            st.error("❌ Access forbidden. Check your permissions.")
            return None
        elif response.status_code == 404:
            logger.error("404 Not Found: %s - %s", url, response.text)
            st.error("❌ API endpoint not found. Check APISIX configuration.")
            return None
        elif response.status_code == 422:
            logger.error("422 Validation Error: %s", response.text)
            try:
                error_detail = response.json().get("detail", response.text)
                st.error(f"❌ Validation error: {error_detail}")
            except Exception:
                st.error(f"❌ Validation failed: {response.text}")
            return None
        elif response.status_code == 500:
            logger.error("500 Internal Server Error: %s", response.text)
            st.error("❌ Server error. Check FastAPI logs.")
            return None
        elif response.status_code == 502:
            logger.error("502 Bad Gateway: %s", response.text)
            st.error("❌ Bad Gateway. APISIX cannot reach FastAPI service.")
            return None
        elif response.status_code == 503:
            logger.error("503 Service Unavailable: %s", response.text)
            st.error("❌ Service unavailable. FastAPI service may be down.")
            return None
        else:
            logger.error("API Error %s: %s - %s", response.status_code, url, response.text)
            st.error(f"❌ API request failed: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError as e:
        logger.error("Connection error to %s: %s", url, e)
        st.error(f"❌ Connection error: Cannot reach APISIX Gateway at {url}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error("Timeout error to %s: %s", url, e)
        st.error("❌ Request timeout. Gateway or backend service is slow.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error("Request exception to %s: %s", url, e)
        st.error(f"❌ Request error: {e}")
        return None


def create_compatible_api_token() -> Optional[str]:
    """Create a FastAPI-compatible token using JWT manager"""
    try:

        from utils.jwt_manager import jwt_manager
        from utils.user_context import get_user_context_for_token

        # Get consistent user context regardless of authentication source
        user_context = get_user_context_for_token()
        logger.info(f"Creating API token for consistent user: {user_context['preferred_username']}")

        # Create token with consistent user context
        api_token = jwt_manager.create_token(user_context)

        if api_token:
            logger.info("Successfully created API token using JWT manager")
            return str(api_token)
        else:
            st.error(
                "🚨 Security Error: JWT secret key not configured. Please set JWT_SECRET_KEY environment variable."
            )
            logger.error("Failed to create API token - JWT secret key not available")
            return None

    except Exception as e:
        st.error("❌ Failed to generate API token. Please try refreshing the page.")
        logger.error("Token creation failed: %s", e)
        return None


# --- API Backend Functions ---


def load_generator_types_from_api() -> List[str]:
    """Load available generator type from API."""
    logger.debug(f"Loading generator types from: {API_ENDPOINTS['generator_types']}")

    data = api_request("GET", API_ENDPOINTS["generator_types"])
    if data:
        generator_types_data = cast(List[str], data.get("generator_types", []))
        generator_types = list(generator_types_data)
        st.session_state.api_generator_types = generator_types
        logger.info("Loaded %s generator types: %s", len(generator_types), generator_types)
        return generator_types
    else:
        logger.warning("Failed to load generator types from API")
        return []


def load_generators_from_api() -> List[Dict[str, object]]:
    """Load existing generator from API."""
    data = api_request("GET", API_ENDPOINTS["generators"])

    if data:
        data_dict = cast(Dict[str, Any], data)
        generators_list = cast(List[Dict[str, Any]], data_dict.get("generators", []))
        st.session_state.api_generators = {gen["name"]: gen for gen in generators_list}
        return list(generators_list)
    return []


def get_generator_params_from_api(generator_type: str) -> List[Dict[str, object]]:
    """Get parameter definition for a generator type from API."""
    url = API_ENDPOINTS["generator_params"].format(generator_type=generator_type)

    data = api_request("GET", url)
    if data:
        return list(cast(List[Dict[str, object]], cast(Dict[str, Any], data).get("parameters", [])))
    return []


def save_generator_to_api(name: str, generator_type: str, parameters: Dict[str, object]) -> bool:
    """Save a new generator configuration to API"""
    logger.info(f"Saving generator: name='{name}', type='{generator_type}', params={parameters}")

    payload = {"name": name, "type": generator_type, "parameters": parameters}

    logger.debug("API payload: %s", payload)
    logger.debug(f"API endpoint: {API_ENDPOINTS['generators']}")

    data = api_request("POST", API_ENDPOINTS["generators"], json=payload)
    if data:
        # Update local state - API returns generator object directly, not wrapped
        st.session_state.api_generators[name] = data
        logger.info(f"Generator '{name}' saved successfully with ID: {data.get('id')}")
        return True
    else:
        logger.error(f"Failed to save generator '{name}' - no data returned from API")
        return False


def test_generator_via_orchestrator(generator_name: str, custom_prompt: Optional[str] = None) -> Dict[str, object]:
    """Test a generator via orchestrator API (replacing removed test endpoint)"""
    # Find generator from name

    generator = st.session_state.api_generators.get(generator_name)
    if not generator:
        return {"success": False, "error": "Generator not found"}

    generator_id = generator.get("id")
    if not generator_id:
        return {"success": False, "error": "Generator ID not found"}

    test_prompt = custom_prompt or "Hello, this is a test prompt for AI red-teaming configuration."

    try:
        # Get current user context for generator resolution
        user_info = api_request("GET", API_ENDPOINTS["auth_token_info"])
        user_context = user_info.get("username") if user_info else "unknown_user"
        logger.info("User info from API: %s", user_info)
        logger.info("Using user context: %s", user_context)

        # Also debug the generator being tested
        logger.info("Generator being tested: %s", generator_name)
        logger.info("Generator details: %s", generator)
        logger.info(
            "Available generators in session: %s",
            list(st.session_state.api_generators.keys()),
        )

        # Create temporary orchestrator for testing
        orchestrator_params = {
            "objective_target": {
                "type": "configured_generator",
                "generator_name": generator_name,
            },
            "user_context": user_context,  # Add user context for generator resolution
        }

        orchestrator_payload = {
            "name": f"test_generator_{generator_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "orchestrator_type": "PromptSendingOrchestrator",
            "description": f"Testing generator '{generator_name}' for user {user_context}",
            "parameters": orchestrator_params,
            "tags": ["generator_test", generator_name, user_context],
        }

        logger.info("Creating test orchestrator with payload: %s", orchestrator_payload)
        logger.info(f"Orchestrator create URL: {API_ENDPOINTS['orchestrator_create']}")

        # Create orchestrator
        try:
            orchestrator_response = api_request("POST", API_ENDPOINTS["orchestrator_create"], json=orchestrator_payload)
        except Exception as e:
            logger.error("Exception during orchestrator creation: %s", e)
            return {
                "success": False,
                "error": f"Exception during orchestrator creation: {str(e)}",
            }

        if not orchestrator_response:
            logger.error("Failed to create orchestrator - no response from API")
            # Try to get more detailed error information
            try:

                headers = get_auth_headers()
                debug_response = requests.post(
                    API_ENDPOINTS["orchestrator_create"],
                    json=orchestrator_payload,
                    headers=headers,
                    timeout=30,
                )
                logger.error("Debug response status: %s", debug_response.status_code)
                logger.error("Debug response text: %s", debug_response.text)

                # Try to parse JSON error for more details
                try:
                    error_details = debug_response.json()
                    error_msg = error_details.get("message", debug_response.text)
                    error_id = error_details.get("error_id", "unknown")
                    return {
                        "success": False,
                        "error": (
                            f"Orchestrator creation failed (ID: {error_id}): {error_msg}. "
                            "This suggests an issue with the orchestrator service or generator lookup."
                        ),
                    }
                except Exception:
                    return {
                        "success": False,
                        "error": (
                            f"Failed to create test orchestrator - API returned "
                            f"{debug_response.status_code}: {debug_response.text}"
                        ),
                    }
            except Exception as debug_error:
                logger.error("Debug request also failed: %s", debug_error)
                return {
                    "success": False,
                    "error": "Failed to create test orchestrator - check API connectivity and authentication",
                }

        logger.info("Orchestrator creation response: %s", orchestrator_response)

        orchestrator_id = orchestrator_response.get("orchestrator_id")

        # Execute orchestrator with test prompt
        execution_payload = {
            "execution_name": f"test_{generator_name}_{datetime.now().strftime('%H%M%S')}",
            "execution_type": "prompt_list",
            "input_data": {"prompt_list": [test_prompt]},
        }

        execution_url = API_ENDPOINTS["orchestrator_execute"].format(orchestrator_id=orchestrator_id)
        logger.info(
            "Executing orchestrator %s with payload: %s",
            orchestrator_id,
            execution_payload,
        )
        logger.info("Execution URL: %s", execution_url)

        start_time = datetime.now()
        execution_response = api_request("POST", execution_url, json=execution_payload)
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        if not execution_response:
            logger.error("Failed to execute orchestrator - no response from API")
            # Try to get more detailed error information
            try:

                headers = get_auth_headers()
                debug_response = requests.post(execution_url, json=execution_payload, headers=headers, timeout=30)
                logger.error("Debug execution response status: %s", debug_response.status_code)
                logger.error("Debug execution response text: %s", debug_response.text)
                return {
                    "success": False,
                    "error": (
                        f"Failed to execute test orchestrator - API returned "
                        f"{debug_response.status_code}: {debug_response.text}"
                    ),
                    "duration_ms": duration_ms,
                }
            except Exception as debug_error:
                logger.error("Debug execution request also failed: %s", debug_error)
                return {
                    "success": False,
                    "error": "Failed to execute test orchestrator - check API connectivity and orchestrator status",
                    "duration_ms": duration_ms,
                }

        logger.info("Execution response: %s", execution_response)

        execution_status = execution_response.get("status")

        if execution_status == "completed":
            # Extract response from orchestrator results
            execution_dict = cast(Dict[str, Any], execution_response)
            prompt_responses = cast(List[Dict[str, Any]], execution_dict.get("prompt_request_responses", []))
            if prompt_responses and len(prompt_responses) > 0:
                response_data = prompt_responses[0]
                response_content = cast(Dict[str, Any], response_data.get("response", {}))
                if response_content:
                    actual_response = str(response_content.get("content", "No response content"))
                    return {
                        "success": True,
                        "response": actual_response,
                        "test_time": datetime.now().isoformat(),
                        "duration_ms": duration_ms,
                    }

            return {
                "success": False,
                "error": "No response received from generator",
                "duration_ms": duration_ms,
            }

        elif execution_status == "failed":
            error_msg = execution_response.get("error", "Unknown execution error")
            return {
                "success": False,
                "error": f"Test execution failed: {error_msg}",
                "duration_ms": duration_ms,
            }

        else:
            return {
                "success": False,
                "error": f"Unexpected execution status: {execution_status}",
                "duration_ms": duration_ms,
            }

    except Exception as e:
        logger.error("Error testing generator via orchestrator: %s", e)
        # Show the actual exception in the UI for debugging
        import traceback

        error_details = f"Test error: {str(e)}\n\nFull traceback:\n{traceback.format_exc()}"
        return {"success": False, "error": error_details, "duration_ms": 0}


def delete_generator_via_api(generator_name: str) -> bool:
    """Delete a generator via API"""
    generator = st.session_state.api_generators.get(generator_name)

    if not generator:
        logger.warning(f"Generator '{generator_name}' not found in local state")
        return False

    generator_id = generator.get("id")
    if not generator_id:
        logger.error(f"Generator '{generator_name}' has no ID")
        return False

    url = f"{API_ENDPOINTS['generators']}/{generator_id}"

    try:
        response = requests.delete(url, headers=get_auth_headers(), timeout=30)

        if response.status_code in [204, 200]:
            # Remove from local state
            if generator_name in st.session_state.api_generators:
                del st.session_state.api_generators[generator_name]
            logger.info(f"Successfully deleted generator '{generator_name}' (ID: {generator_id})")
            return True
        elif response.status_code == 404:
            # Generator already deleted, remove from local state
            if generator_name in st.session_state.api_generators:
                del st.session_state.api_generators[generator_name]
            logger.info(f"Generator '{generator_name}' was already deleted, removing from local state")
            return True
        else:
            logger.error(f"Failed to delete generator '{generator_name}': {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception deleting generator '{generator_name}': {e}")
        return False


def get_apisix_models_from_api(provider: str) -> List[str]:
    """Get available model for a provider from APISIX Gateway."""
    url = f"{API_ENDPOINTS['apisix_models']}?provider={provider}"

    data = api_request("GET", url)
    if data:
        models_data = cast(List[str], data.get("models", []))
        return list(models_data)
    return []


def get_provider_display_name(provider: str) -> str:
    """Get user-friendly display name for provider"""
    provider_names = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "ollama": "Ollama (Local)",
        "webui": "Open WebUI",
        "openapi-gsai": "GSAi (Government Services AI)",
    }
    return provider_names.get(provider, provider)


def save_session_to_api(session_update: Dict[str, object]) -> bool:
    """Save session state to API"""
    data = api_request("PUT", API_ENDPOINTS["sessions_update"], json=session_update)

    if data:
        st.session_state.api_session_data = data
        return True
    return False


# --- Main Page Function ---
def main() -> None:
    """Render the Configure Generators page content with API backend.."""
    logger.debug("Configure Generators page (API-backed) loading.")

    st.set_page_config(
        page_title="Configure Generators",
        # page_icon="⚙️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- Authentication and Sidebar ---
    handle_authentication_and_sidebar("Configure Generators")

    # --- Page Content ---
    display_header()

    # Check authentication status - allow both Keycloak SSO and environment-based auth
    has_keycloak_token = bool(st.session_state.get("access_token"))
    has_env_credentials = bool(os.getenv("KEYCLOAK_USERNAME"))

    if not has_keycloak_token and not has_env_credentials:
        st.warning(
            "⚠️ Authentication required: Please log in via Keycloak SSO or configure KEYCLOAK_USERNAME in environment."
        )
        st.info("💡 For local development, you can set KEYCLOAK_USERNAME and KEYCLOAK_PASSWORD in your .env file")
        return

    # Automatically generate API token if not present
    if not st.session_state.get("api_token"):
        with st.spinner("Generating API token..."):
            api_token = create_compatible_api_token()
            if not api_token:
                st.error("❌ Failed to generate API token. Please try refreshing the page.")
                return

    # Status is handled in the sidebar - no need for duplicate status blocks here

    # Load existing generators automatically on page load
    auto_load_existing_generators()

    # Main content sections
    display_main_content()


def display_main_content() -> None:
    """Display the main content with clean organization"""
    # Single column layout - Existing generators first, then add new generator

    # Show existing generators first (without subtitle)
    manage_existing_generators_clean()

    # Add new generator section
    st.divider()
    st.subheader("📝 Add New Generator")
    add_new_generator_form()

    # Interactive chat section (full width, only shows if generators exist)
    st.divider()
    display_interactive_chat_test_section()

    # Next steps
    proceed_to_next_step()


def display_header() -> None:
    """Display the main header for the page.."""
    st.title("⚙️ Configure Generators")

    st.markdown("*Configure AI model generators for red-teaming conversations*")


def auto_load_existing_generators() -> None:
    """Automatically load existing generators on page load

    This ensures that previously configured generators are immediately visible
    when the page loads, without requiring manual refresh.
    """
    # Only load if not already loaded or if forced reload

    if not st.session_state.api_generators or st.session_state.get("force_reload_generators", False):
        with st.spinner("Loading existing generators..."):
            generators = load_generators_from_api()
            if generators:
                logger.info("Auto-loaded %s existing generators", len(generators))
            else:
                logger.info("No existing generators found during auto-load")

        # Clear force reload flag
        if "force_reload_generators" in st.session_state:
            del st.session_state["force_reload_generators"]


def manage_existing_generators_clean() -> None:
    """Clean display of existing generators"""
    generators = st.session_state.api_generators

    if not generators:
        st.info("🆕 No generators configured yet")
        st.markdown("💡 Use the form below to add your first generator")
        return

    # Display generators in 3-column format
    st.write(f"**{len(generators)} Configured:**")

    # Create 3 columns
    num_cols = 3
    cols = st.columns(num_cols)
    gen_list = sorted(generators.keys())

    for i, gen_name in enumerate(gen_list):
        col_index = i % num_cols
        with cols[col_index]:
            try:
                gen_data = generators.get(gen_name)
                if gen_data:
                    gen_type = gen_data.get("type", "Unknown")
                    status = gen_data.get("status", "Unknown")

                    # Compact status indicator
                    status_icon = "✅" if status == "ready" else "❌" if status == "failed" else "⚠️"

                    # Compact display format
                    st.markdown(f"**{gen_name}** {status_icon}")
                    st.caption(f"`{gen_type}`")
                else:
                    st.markdown(f"**{gen_name}** ❌")
                    st.caption("*Invalid data*")
                    logger.warning(f"Invalid generator data found for '{gen_name}'.")
            except Exception as e:
                st.markdown(f"**{gen_name}** ⚠️")
                st.caption("*Error loading*")
                logger.error(f"Error displaying details for generator '{gen_name}': {e}")

    # Management actions
    with st.expander("🔧 Management Actions", expanded=False):
        manage_existing_generators_actions()


def manage_existing_generators_actions() -> None:
    """Clean management action for generators."""
    generators = st.session_state.api_generators

    generator_names = list(generators.keys())

    # Refresh button
    if st.button("🔄 Refresh Generators", help="Reload generators from API"):
        st.session_state["force_reload_generators"] = True
        st.rerun()

    # Delete generators
    if generator_names:
        st.markdown("**Delete Generators:**")
        selected_generators = st.multiselect(
            "Select generators to delete",
            generator_names,
            key="delete_gen_select_clean",
            help="Select one or more generators to remove",
        )
        if st.button("🗑️ Delete Selected", key="delete_gen_button_clean", type="primary"):
            if selected_generators:
                delete_generators_action(selected_generators)
                st.rerun()
            else:
                st.warning("Select at least one generator to delete.")


def delete_generators_action(selected_generators: List[str]) -> None:
    """Handle deletion of selected generators"""
    logger.info("Processing deletion for: %s", selected_generators)

    success_count = 0
    total_count = len(selected_generators)

    # Process deletions
    for gen_name in selected_generators:
        try:
            deleted = delete_generator_via_api(gen_name)
            if deleted:
                st.toast(f"`{gen_name}` deleted successfully.", icon="✅")
                logger.info(f"'{gen_name}' deleted successfully.")
                success_count += 1
            else:
                st.error(f"Failed to delete `{gen_name}`. Check API connectivity and permissions.")
                logger.error(f"'{gen_name}' deletion failed.")
        except Exception as e:
            st.error(f"Error deleting `{gen_name}`: {e}")
            logger.exception(f"Error deleting '{gen_name}'.")

    # Clear the multiselect to prevent confusion - use del instead of assignment
    if "delete_gen_select_clean" in st.session_state:
        del st.session_state.delete_gen_select_clean

    # Show summary
    if success_count == total_count:
        st.success(f"✅ All {total_count} generators deleted successfully!")
    elif success_count > 0:
        st.warning(f"⚠️ {success_count}/{total_count} generators deleted successfully.")
    else:
        st.error(f"❌ Failed to delete any of the {total_count} selected generators.")

    logger.info("Deletion complete: %s/%s successful", success_count, total_count)


def add_new_generator_form() -> None:
    """Clean form for adding new generators"""
    # Load generator types if not already loaded

    if not st.session_state.api_generator_types:
        with st.spinner("Loading generator types..."):
            load_generator_types_from_api()

    available_types = st.session_state.api_generator_types
    if not available_types:
        st.error("❌ No generator types available. Check API connectivity.")
        return

    # Set AI Gateway as default if available
    default_index = 0
    if "AI Gateway" in available_types:
        default_index = available_types.index("AI Gateway")

    # Basic configuration section
    col1, col2 = st.columns([1, 1])

    with col1:
        st.text_input(
            "Unique Generator Name*",
            key="new_generator_name",
            help="A unique identifier for this generator configuration - used for referencing in workflows",
        )

    with col2:
        st.selectbox(
            "Generator Technology*",
            available_types,
            index=default_index,
            key="generator_type_select",
            help="Choose the AI provider or model technology for prompt generation",
            on_change=lambda: st.session_state.update(
                {"form_key_counter": st.session_state.get("form_key_counter", 0) + 1}
            ),
        )

    # Parameters form
    generator_type = st.session_state.get("generator_type_select")
    form_key = f"add_generator_form_{st.session_state.get('form_key_counter', 0)}"

    # Special handling for AI Gateway - provider selection outside form
    if generator_type == "AI Gateway":
        handle_ai_gateway_provider_selection()

    with st.form(key=form_key):
        params_rendered = False
        param_defs_for_render = []

        if generator_type:
            try:
                param_defs_for_render = get_generator_params_from_api(generator_type)
                if param_defs_for_render:
                    configure_generator_parameters(generator_type, param_defs_for_render)
                    params_rendered = True
                else:
                    st.warning(f"No parameters defined for {generator_type} or API unavailable.")
            except Exception as e:
                st.error(f"Error getting params for {generator_type}: {e}")
                logger.exception("Error getting params for %s.", generator_type)
        else:
            st.info("Select a Generator Technology to see parameters.")

        submitted = st.form_submit_button(
            "💾 Save Generator",
            disabled=not params_rendered,
            use_container_width=True,
            help="Save the generator configuration",
        )

        if submitted:
            save_generator_form_submission(param_defs_for_render)


def handle_ai_gateway_provider_selection() -> None:
    """Handle AI Gateway provider selection outside the form to enable dynamic model loading"""
    try:

        # Add refresh button for debugging
        _, col_debug = st.columns([3, 1])
        with col_debug:
            if st.button("🔄 Refresh Providers", help="Refresh provider list from API"):
                st.session_state.pop("ai_gateway_param_cache", None)
                st.rerun()

        param_defs = get_generator_params_from_api("AI Gateway")
        provider_param = next(
            (cast(Dict[str, Any], p) for p in param_defs if cast(Dict[str, Any], p)["name"] == "provider"), None
        )

        # Debug information
        with st.expander("🔍 Debug Info", expanded=False):
            st.write("**API Response Debug:**")
            st.write(f"Total parameters found: {len(param_defs)}")
            st.write("**Raw param_defs structure:**")
            st.json(param_defs)

            if provider_param:
                st.write("**Provider parameter details:**")
                st.write(f"Type: {type(provider_param)}")
                st.json(provider_param)

                try:
                    provider_dict = provider_param
                    if "options" in provider_dict:
                        st.write(f"Provider options: {provider_dict['options']}")
                        st.write(f"Options type: {type(provider_dict['options'])}")
                        st.write(f"Total providers: {len(cast(List[str], provider_dict['options']))}")
                        # Highlight OpenAPI providers
                        openapi_providers = [
                            str(p) for p in cast(List[str], provider_dict["options"]) if str(p).startswith("openapi-")
                        ]
                        if openapi_providers:
                            st.success(f"✅ OpenAPI providers found: {openapi_providers}")
                        else:
                            st.warning("⚠️ No OpenAPI providers found in options")
                    else:
                        st.error("❌ No 'options' key found in provider parameter")
                except Exception as debug_error:
                    st.error(f"❌ Error processing provider parameter: {debug_error}")
            else:
                st.error("❌ No provider parameter found")

            # Direct API test for OpenAPI providers
            st.write("**Direct OpenAPI Providers Test:**")
            try:
                openapi_data = api_request("GET", API_ENDPOINTS["openapi_providers"])
                st.write(f"Raw API response type: {type(openapi_data)}")
                st.write(f"Raw API response: {openapi_data}")

                if openapi_data:
                    # The OpenAPI providers endpoint returns List[str] directly
                    data_as_list: List[object] = []
                    if isinstance(openapi_data, list):
                        # It's a list of provider strings
                        data_as_list = openapi_data
                        st.success(f"✅ Direct API call found {len(data_as_list)} OpenAPI providers: {data_as_list}")
                    elif isinstance(openapi_data, dict):
                        # If it's a dict, it might be an error response or wrapped data
                        if "providers" in openapi_data:
                            providers_data = openapi_data["providers"]
                            data_as_list = providers_data if isinstance(providers_data, list) else []
                            st.success(f"✅ Found providers in dict: {data_as_list}")
                        elif "error" in openapi_data:
                            st.error(f"❌ API Error: {openapi_data.get('message', 'Unknown error')}")
                            data_as_list = []
                        else:
                            # Unknown dict format, show all keys for debugging
                            st.warning(f"⚠️ Unknown dict format with keys: {list(openapi_data.keys())}")
                            data_as_list = []
                    else:
                        # Unknown format, show what we got
                        st.warning(f"⚠️ Unknown response format: {type(openapi_data)} - {repr(openapi_data)}")
                        data_as_list = []

                    if len(data_as_list) == 0:
                        st.warning("⚠️ Direct API call returned empty list")
                else:
                    st.error("❌ Direct API call failed - no data returned")
            except Exception as e:
                st.error(f"❌ Direct API call error: {e}")
                import traceback

                st.code(traceback.format_exc(), language="python")

            # Additional debug: Check backend configuration
            # NOTE: debug-openapi endpoint removed as it's not needed
            # The debug information can be obtained from the generator params endpoint below

            # Check the generator params endpoint directly
            st.write("**Generator Params Endpoint Debug:**")
            try:
                params_url = API_ENDPOINTS["generator_params"].format(generator_type="AI Gateway")
                st.write(f"Calling: {params_url}")
                raw_params = api_request("GET", params_url)
                if raw_params:
                    st.write("✅ Raw generator params response:")
                    st.json(raw_params)
                else:
                    st.error("❌ Generator params endpoint returned no data")
            except Exception as params_e:
                st.error(f"❌ Generator params debug error: {params_e}")
                import traceback

                st.code(traceback.format_exc(), language="python")

        if provider_param:
            st.markdown("**🔧 AI Gateway Configuration**")

            col1, col2 = st.columns([1, 1])
            with col1:
                selected_provider = st.selectbox(
                    f"{provider_param['description']}*",
                    options=provider_param["options"],
                    index=(
                        provider_param["options"].index(provider_param["default"])
                        if provider_param["default"] in provider_param["options"]
                        else 0
                    ),
                    key="ai_gateway_provider_external",
                    help=provider_param["description"] + " (Required)",
                    on_change=lambda: st.session_state.update(
                        {
                            "ai_gateway_provider_changed": True,
                            "form_key_counter": st.session_state.get("form_key_counter", 0) + 1,
                        }
                    ),
                )

                # Store the selected provider for use in form
                st.session_state["AI Gateway_provider"] = selected_provider

            with col2:
                # Show model preview outside form
                try:
                    models = get_apisix_models_from_api(selected_provider)
                    provider_display = get_provider_display_name(selected_provider)
                    if models:
                        if selected_provider == "openapi-gsai":
                            st.info(f"🏛️ **GSAi Models**: Found {len(models)} models for {provider_display}")
                        else:
                            st.info(f"📡 **Live Discovery**: Found {len(models)} models for {provider_display}")
                        st.session_state["ai_gateway_available_models"] = models
                    else:
                        st.warning(f"⚠️ No models found for {provider_display}")
                        st.session_state["ai_gateway_available_models"] = []
                except Exception as e:
                    st.error(f"Error loading models: {e}")
                    st.session_state["ai_gateway_available_models"] = []

    except Exception as e:
        st.error(f"Error setting up AI Gateway provider selection: {e}")
        logger.error("Error in handle_ai_gateway_provider_selection: %s", e)


def configure_generator_parameters(generator_type: str, param_defs: List[Dict[str, object]]) -> None:
    """Display input field for configuring parameters."""
    with st.expander(f"Configure Parameters for `{generator_type}`", expanded=True):

        if not param_defs:
            st.caption("No parameters defined for this generator type.")
            return

        # Special handling for AI Gateway dynamic model loading and column layout
        if generator_type == "AI Gateway":
            configure_ai_gateway_parameters(param_defs)
        else:
            configure_standard_parameters(generator_type, param_defs)


def should_show_parameter(param_name: str, provider: str) -> bool:
    """Determine if a parameter should be shown based on provider selection"""
    # For standard cloud providers, hide API key and custom endpoint

    # These are handled by the APISIX gateway configuration
    cloud_providers = ["openai", "anthropic"]

    if provider in cloud_providers:
        # Hide API key and endpoint for cloud providers - gateway handles this
        if param_name in ["api_key", "endpoint"]:
            return False

    # For local providers (ollama, webui), show endpoint but hide api_key
    local_providers = ["ollama", "webui"]
    if provider in local_providers:
        if param_name == "api_key":
            return False  # Local providers typically don't need API keys
        # endpoint is shown for local providers to configure custom URLs

    # Show all other parameters
    return True


def configure_ai_gateway_parameters(param_defs: List[Dict[str, object]]) -> None:
    """Configure AI Gateway parameter with dynamic model loading and two-column layout."""
    # Split parameters by category

    config_params = [p for p in param_defs if p.get("category") == "configuration"]
    model_params = [p for p in param_defs if p.get("category") == "model"]

    # Create two columns within the expander
    param_col1, param_col2 = st.columns([1, 1])

    with param_col1:
        st.markdown("**🔧 Configuration**")

        # Handle model selection using available models from session state
        model_param = next((p for p in config_params if p["name"] == "model"), None)
        if model_param:
            available_models = st.session_state.get("ai_gateway_available_models", [])
            selected_provider = st.session_state.get("AI Gateway_provider", "openai")

            if available_models:
                # Create model selectbox with available models
                model_key = "AI Gateway_model"

                default_index = 0
                current_model = st.session_state.get(model_key)
                if current_model and current_model in available_models:
                    default_index = available_models.index(current_model)
                provider_display = get_provider_display_name(selected_provider)
                help_text = f"Available models for {provider_display} (Required)"
                if selected_provider == "openapi-gsai":
                    help_text += " - Uses static authentication like OpenAI/Anthropic"

                st.selectbox(
                    f"{model_param['description']}*",
                    options=available_models,
                    index=default_index,
                    key=model_key,
                    help=help_text,
                )
            else:
                provider_display = get_provider_display_name(selected_provider)
                st.warning(f"⚠️ No models available for {provider_display}")
                st.session_state["AI Gateway_model"] = None

        # Render other configuration parameters based on provider selection
        selected_provider = st.session_state.get("AI Gateway_provider", "openai")
        for param in config_params:
            if param["name"] not in ["provider", "model"]:
                # Skip API key and endpoint for standard cloud providers
                if should_show_parameter(str(param["name"]), selected_provider):
                    render_parameter_widget("AI Gateway", param)

    with param_col2:
        st.markdown("**⚙️ Model Parameters**")

        # Render model parameters
        for param in model_params:
            render_parameter_widget("AI Gateway", param)


def configure_standard_parameters(generator_type: str, param_defs: List[Dict[str, object]]) -> None:
    """Configure standard generator parameters"""
    for param in param_defs:

        render_parameter_widget(generator_type, param)


def render_parameter_widget(generator_type: str, param: Dict[str, object]) -> None:
    """Render a single parameter widget"""
    param_name = param["name"]

    param_type = param["type"]
    param_required = param["required"]
    param_description = param["description"]
    param_default = param.get("default")
    param_options = param.get("options")
    label = f"{param_description}{'*' if param_required else ''}"
    key = f"{generator_type}_{param_name}"
    help_text = str(param_description) + (" (Required)" if param_required else " (Optional)")

    if generator_type in ["OpenAIDALLETarget", "OpenAITTSTarget"] and param_name in [
        "deployment_name",
        "api_version",
        "use_aad_auth",
    ]:
        help_text += " - Used ONLY for Azure OpenAI endpoints."
        if param_name == "api_version":
            help_text += " Leave BLANK/default for standard OpenAI."

    try:
        if param_type == "selectbox":
            if not param_options or not isinstance(param_options, list):
                st.error(f"Config Error for '{param_name}': 'options' list missing/invalid.")
                return
            try:
                default_index = param_options.index(param_default) if param_default in param_options else 0
            except ValueError:
                default_index = 0
            st.selectbox(
                label,
                options=param_options,
                index=default_index,
                key=key,
                help=help_text,
            )
        elif param_type == "bool":
            st.checkbox(
                label,
                value=bool(param_default) if param_default is not None else False,
                key=key,
                help=help_text,
            )
        elif param_type == "str":
            default_value = param_default or ""
            if (
                "key" in str(param_name).lower()
                or "secret" in str(param_name).lower()
                or "token" in str(param_name).lower()
            ):
                st.text_input(label, value=default_value, key=key, type="password", help=help_text)
            else:
                st.text_input(label, value=default_value, key=key, help=help_text)
        elif param_type == "dict":
            default_json_str = (
                json.dumps(param_default, indent=2) if isinstance(param_default, dict) else (param_default or "")
            )
            st.text_area(
                label + " (Enter as JSON)",
                value=default_json_str,
                key=key,
                help=help_text,
                height=100,
            )
        elif param_type == "int":
            num_default = int(cast(Union[str, int, float], param_default)) if param_default is not None else 0
            st.number_input(label, value=num_default, step=1, key=key, help=help_text)
        elif param_type == "float":
            float_default = float(cast(Union[str, int, float], param_default)) if param_default is not None else 0.0
            step = float(cast(Union[str, int, float], param.get("step", 0.01)))
            precision = max(0, -int(math.log10(step))) if step > 0 and step != 1 else 2
            st.number_input(
                label,
                value=float_default,
                step=step,
                format=f"%.{precision}f",
                key=key,
                help=help_text,
            )
        elif param_type == "list":
            default_str = (
                ",".join(map(str, param_default)) if isinstance(param_default, list) else (param_default or "")
            )
            st.text_input(label + " (comma-separated)", value=default_str, key=key, help=help_text)
        else:
            logger.warning(f"Unsupported param type '{param_type}' for '{param_name}' in UI. Rendering as text.")
            st.text_input(
                label + f" (Type: {param_type})",
                value=str(param_default) if param_default is not None else "",
                key=key,
                help=help_text,
            )
    except Exception as e:
        st.error(f"Error rendering widget for '{param_name}': {e}")
        logger.exception(f"Error rendering widget '{param_name}' for type '{generator_type}'.")


def save_generator_form_submission(param_defs_for_render: List[Dict[str, object]]) -> None:
    """Save the generator form submission directly without testing"""
    submitted_generator_name = st.session_state.get("new_generator_name")

    submitted_generator_type = st.session_state.get("generator_type_select")
    logger.info(
        f"Save Generator form submitted for name: '{submitted_generator_name}' type: '{submitted_generator_type}'"
    )

    if not submitted_generator_name:
        st.warning("Generator name is required.")
        logger.warning("Form submitted without generator name.")
        return
    if not submitted_generator_type:
        st.warning("Generator technology type must be selected.")
        logger.warning("Form submitted without generator type selection.")
        return

    # Check if generator name already exists
    if submitted_generator_name in st.session_state.api_generators:
        st.error(f"Generator name '{submitted_generator_name}' already exists. Please choose a different name.")
        return

    try:
        parameters = {}
        validation_passed = True
        missing_required_fields = []

        for param in param_defs_for_render:
            param_name = param["name"]
            param_required = param["required"]
            param_type = param["type"]
            param_default = param.get("default")
            param_description = param.get("description", param_name)
            widget_key = f"{submitted_generator_type}_{param_name}"

            processed_value: Any = None
            if widget_key in st.session_state:
                raw_value = st.session_state[widget_key]
                if isinstance(raw_value, str):
                    cleaned_value = raw_value.strip() if raw_value and raw_value.strip() else None
                    if param_type == "list" and cleaned_value:
                        processed_value = [item.strip() for item in cleaned_value.split(",") if item.strip()]
                    else:
                        # Use Any type for processed_value to handle multiple types
                        processed_value = cleaned_value
                        if not processed_value:
                            processed_value = None
                elif (
                    param_name == "headers"
                    and param_type == "dict"
                    and isinstance(raw_value, str)
                    and raw_value.strip()
                ):
                    try:
                        parsed_json = json.loads(raw_value.strip())
                        processed_value = parsed_json if isinstance(parsed_json, dict) else None
                        if processed_value is None and raw_value.strip() != "{}":
                            raise ValueError("Parsed JSON is not a dictionary.")
                    except (json.JSONDecodeError, ValueError) as json_err:
                        st.error(f"Invalid JSON dictionary format for 'Headers': {json_err}")
                        logger.error(f"Invalid JSON headers for '{submitted_generator_name}': {raw_value}")
                        validation_passed = False
                        processed_value = None
                elif param_type == "int" and raw_value is not None:
                    try:
                        processed_value = int(raw_value)
                    except (ValueError, TypeError):
                        validation_passed = False
                        st.error(f"Invalid integer for '{param_description}'.")
                        logger.error(f"Invalid int '{raw_value}' for '{param_name}'")
                        processed_value = None
                elif param_type == "float" and raw_value is not None:
                    try:
                        processed_value = float(raw_value)
                    except (ValueError, TypeError):
                        validation_passed = False
                        st.error(f"Invalid decimal for '{param_description}'.")
                        logger.error(f"Invalid float '{raw_value}' for '{param_name}'")
                        processed_value = None
                elif param_type == "selectbox":
                    if param_required and (
                        raw_value is None or raw_value not in cast(List[Any], param.get("options", []))
                    ):
                        validation_passed = False
                        st.error(f"Please select a valid option for '{param_description}'.")
                        logger.error(f"Invalid selection for '{param_name}'")
                        processed_value = None
                    else:
                        processed_value = raw_value
                else:
                    processed_value = raw_value

                if not param_required and processed_value is not None and param_default is not None:
                    is_default = False
                    if param_type == "float":
                        is_default = math.isclose(processed_value, float(cast(Union[str, int, float], param_default)))
                    elif param_type == "selectbox":
                        is_default = processed_value == param_default
                    elif processed_value == param_default:
                        is_default = True

                    if is_default:
                        logger.debug(
                            f"Optional parameter '{param_name}' value '{processed_value}' "
                            f"matches default '{param_default}'. Excluding."
                        )
                        processed_value = None
            else:
                if param_required:
                    missing_required_fields.append(param_description)
                    validation_passed = False

            if param_required:
                is_missing = processed_value is None
                if isinstance(processed_value, (list, dict)) and not processed_value:
                    is_missing = True
                if is_missing:
                    if param_type != "selectbox":
                        missing_required_fields.append(param_description)
                        validation_passed = False
                else:
                    parameters[param_name] = processed_value
            elif processed_value is not None:
                if param_name == "headers":
                    if isinstance(processed_value, dict) and processed_value:
                        parameters[param_name] = processed_value
                elif isinstance(processed_value, list):
                    if processed_value:
                        parameters[param_name] = processed_value
                else:
                    parameters[param_name] = processed_value

        if missing_required_fields:
            st.error(
                f"The following required fields are missing: "
                f"{', '.join([str(field) for field in missing_required_fields])}"
            )
            logger.error(
                f"Required fields missing for '{submitted_generator_name}': "
                f"{', '.join([str(field) for field in missing_required_fields])}"
            )
            return

        # Handle Azure specifics (Only for PyRIT OpenAI Targets)
        if submitted_generator_type.startswith("OpenAI"):
            endpoint_value = parameters.get("endpoint", "").lower()
            is_azure_endpoint = "openai.azure.com" in endpoint_value
            if not is_azure_endpoint:
                parameters["api_version"] = None
                parameters.pop("deployment_name", None)
                parameters["is_azure_target"] = False  # Explicitly set flag if needed by target
                if (
                    f"{submitted_generator_type}_deployment_name" in st.session_state
                    and st.session_state[f"{submitted_generator_type}_deployment_name"]
                ):
                    st.warning("Deployment Name ignored for non-Azure endpoint.", icon="⚠️")
            else:  # Is Azure
                parameters["is_azure_target"] = True
                if "deployment_name" not in parameters or not parameters["deployment_name"]:
                    st.error("Azure Deployment Name is required for Azure endpoint.")
                    validation_passed = False
                if "api_version" not in parameters or not parameters["api_version"]:
                    azure_api_version_default = next(
                        (p.get("default") for p in param_defs_for_render if p["name"] == "api_version"),
                        None,
                    )
                    if azure_api_version_default:
                        parameters["api_version"] = azure_api_version_default
                        logger.info(
                            f"Using default API version '{azure_api_version_default}' "
                            f"for Azure target '{submitted_generator_name}'."
                        )

        if not validation_passed:
            logger.warning(f"Validation failed for '{submitted_generator_name}'. Aborting save.")
            return

        log_params = parameters.copy()
        for key in list(log_params.keys()):
            if "key" in str(key).lower() or "token" in str(key).lower() or "secret" in str(key).lower():
                log_params[key] = "****"
        logger.debug(f"Final parameters collected for '{submitted_generator_name}': {log_params}")

        # Save the generator directly
        save_generator_directly(submitted_generator_name, submitted_generator_type, parameters)

    except KeyError as e:
        st.error(f"Error processing parameters for type '{submitted_generator_type}': {e}")
        logger.exception(f"KeyError during parameter collection for '{submitted_generator_type}'.")
    except Exception as e:
        st.error(f"An unexpected error occurred while processing parameters: {e}")
        logger.exception(f"Unexpected error during parameter collection for '{submitted_generator_name}'.")


def save_generator_directly(generator_name: str, generator_type: str, parameters: Dict) -> None:
    """Save generator directly without opening test interface"""
    log_params_received = parameters.copy()

    for key in list(log_params_received.keys()):
        if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
            log_params_received[key] = "****"
    logger.info(f"Saving generator '{generator_name}' with params: {log_params_received}")

    try:
        # Save the generator to API
        saved = save_generator_to_api(generator_name, generator_type, parameters)

        if saved:
            st.success(f"✅ Generator '{generator_name}' saved successfully!")

            # Save session state
            session_update = {
                "ui_preferences": {"last_page": "Configure Generators"},
                "workflow_state": {
                    "current_step": "generators_configured",
                    "generator_count": len(st.session_state.api_generators),
                },
                "temporary_data": {"last_generator_added": generator_name},
            }
            save_session_to_api(session_update)

            logger.info(f"Generator '{generator_name}' saved successfully")
            st.toast(f"Generator '{generator_name}' saved!", icon="✅")

            # Trigger page refresh to show the new generator and clear form
            st.rerun()

        else:
            st.error(f"Failed to save generator '{generator_name}'. Please try again.")

    except Exception as e:
        st.error(f"Error saving generator: {e}")
        logger.error(f"Error saving generator '{generator_name}': {e}")


def display_interactive_chat_test_section() -> None:
    """Display interactive chat test section for existing generators"""
    generators = st.session_state.api_generators

    if not generators:
        return  # Don't show if no generators exist

    st.subheader("🧪 Test Your Generators")
    st.markdown("*Interactive chat testing for configured generators*")

    # Generator selection
    generator_names = list(generators.keys())
    selected_generator_name = st.selectbox(
        "Select Generator to Test*",
        ["-- Select Generator --"] + generator_names,
        key="test_generator_select",
        help="Choose which generator to test with interactive chat",
    )

    if selected_generator_name == "-- Select Generator --":
        st.info("👆 Please select a generator to test.")
        return

    # Get the selected generator
    selected_generator = generators[selected_generator_name]
    st.write(
        f"**Selected Generator:** {selected_generator.get('name', 'Unknown')} "
        f"({selected_generator.get('type', 'Unknown')})"
    )

    # Display chat interface for selected generator
    # Check if generator name exists and call chat interface
    display_generator_test_chat(selected_generator_name)


def display_generator_test_chat(generator_name: Optional[str] = None) -> None:
    """Display the interactive chat interface for testing generator"""
    if not generator_name:

        return

    # Initialize chat history for this generator if not exists
    chat_key = f"generator_chat_{generator_name}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    generator = st.session_state.api_generators.get(generator_name)
    if not generator:
        st.error(f"Generator '{generator_name}' not found")
        return

    chat_history = st.session_state[chat_key]

    # Chat history display
    if chat_history:
        with st.container():
            # Header with options
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("**💬 Conversation:**")
            with col2:
                show_technical = st.checkbox("🔧 Show technical details", key=f"show_tech_{generator_name}")

            # Display chat in a clean format
            for user_msg, ai_msg, duration in chat_history:
                # User message
                with st.chat_message("user"):
                    st.markdown(user_msg)

                # AI response
                with st.chat_message("assistant"):
                    if ai_msg.startswith("❌"):
                        # Error message - display as is
                        st.error(ai_msg)
                    else:
                        if show_technical:
                            # Show raw response with technical details
                            st.markdown("**Raw API Response:**")
                            st.code(ai_msg, language="text")
                        else:
                            # Clean response - extract just the actual AI response
                            clean_response = extract_clean_response(ai_msg)
                            st.markdown(clean_response)

                        # Show response time
                        if duration > 0:
                            st.caption(f"⏱️ Response time: {duration}ms")

    # Chat input
    with st.form(key=f"chat_form_{generator_name}"):
        user_input = st.text_area(
            "💬 Enter your test message:",
            placeholder=(
                "Type a message to test the generator (e.g., 'Tell me a joke', " "'Explain quantum physics', etc.)..."
            ),
            height=80,
            key=f"chat_input_{generator_name}",
            help="Test your generator with any message to see how it responds",
        )

        # Action buttons in a more intuitive layout
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            send_button = st.form_submit_button("🚀 Send Message", use_container_width=True, type="primary")

        with col2:
            clear_button = st.form_submit_button("🗑️ Clear Chat", use_container_width=True)

        with col3:
            # No save button needed - generator is already saved
            pass

    # Handle form submissions
    if send_button and user_input.strip():
        send_test_message_to_generator(generator_name, user_input.strip())
        st.rerun()

    elif clear_button:
        st.session_state[chat_key] = []
        st.rerun()


def extract_clean_response(ai_msg: str) -> str:
    """Extract clean AI response from technical details

    The API response may contain technical information like configuration details,
    endpoints, etc. This function extracts just the actual AI model response.
    """
    if ai_msg.startswith("❌"):

        return ai_msg

    # For API errors from GSAi, show the full error message
    if ai_msg.startswith("API Error:"):
        return ai_msg

    # For direct AI responses (like from GSAi), the message is usually the complete response
    # Check if this looks like a complete AI response (not technical details)
    if not any(
        indicator in ai_msg.lower()
        for indicator in [
            "🤖 real ai response",
            "🔧 generator configuration",
            "apisix endpoint:",
            "📥 test prompt:",
            "✅ test status:",
            "⏱️ successfully called",
        ]
    ):
        # This looks like a direct AI response, return it as-is
        return ai_msg.strip()

    # Look for common patterns in the response that indicate the actual AI response
    lines = ai_msg.split("\n")
    clean_lines = []
    in_response_section = False

    for line in lines:
        line = line.strip()

        # Skip technical headers and configuration details
        if any(
            indicator in line.lower()
            for indicator in [
                "🤖 real ai response",
                "━━━━",
                "🔧 generator configuration",
                "provider:",
                "model:",
                "temperature:",
                "max tokens:",
                "apisix endpoint:",
                "📥 test prompt:",
                "✅ test status:",
                "⏱️ successfully called",
            ]
        ):
            continue

        # Look for the actual AI response section
        if "🤖 ai model response:" in line.lower():
            in_response_section = True
            continue

        # If we're in the response section, collect the content
        if in_response_section:
            # Stop if we hit another technical section
            if line.startswith("✅") or line.startswith("⏱️") or line.startswith("🔧"):
                break
            # Remove quote markers from the response
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            if line:
                clean_lines.append(line)

    # If we found clean response lines, join them
    if clean_lines:
        return "\n".join(clean_lines)

    # Last resort: return the original message but try to clean obvious technical parts

    import re

    cleaned = ai_msg
    for pattern in [
        r"🤖 REAL AI Response from [^:]+:",
        r"━+",
        r"🔧 Generator Configuration:.*?(?=🤖|$)",
        r"📥 Test Prompt:.*?(?=🤖|$)",
        r"✅ Test Status:.*?(?=⏱️|$)",
        r"⏱️ Successfully called.*",
    ]:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    return cleaned.strip() or ai_msg


def send_test_message_to_generator(generator_name: str, message: str) -> None:
    """Send a test message to a specific generator"""
    chat_key = f"generator_chat_{generator_name}"

    try:
        import time

        start_time = time.time()

        # Test the selected generator using orchestrator
        test_result = test_generator_via_orchestrator(generator_name, message)

        duration_ms = int((time.time() - start_time) * 1000)

        if test_result.get("success"):
            response = test_result.get("response", "No response received")
            st.session_state[chat_key].append((message, response, duration_ms))
            logger.info(f"Test message sent successfully to '{generator_name}'")
        else:
            error_msg = test_result.get("error", "Unknown error occurred")
            st.session_state[chat_key].append((message, f"❌ Error: {error_msg}", duration_ms))
            logger.error(f"Test message failed for '{generator_name}': {error_msg}")
            # Show detailed error in UI for debugging
            st.error(f"🔍 Debug - Test Error: {error_msg}")

    except Exception as e:
        st.session_state[chat_key].append((message, f"❌ Exception: {str(e)}", 0))
        logger.error(f"Exception during test message for '{generator_name}': {e}")
        # Show detailed exception in UI for debugging
        st.error(f"🔍 Debug - Exception: {str(e)}")


# Removed save_tested_generator - generators are now saved directly without testing first

# Removed: test_generator_via_api_with_prompt - replaced with orchestrator-based testing
# The old /generators/{id}/test endpoint has been retired in favor of orchestrator workflows


def proceed_to_next_step() -> None:
    """Provide button to proceed to next step"""
    st.divider()

    st.header("🚀 Proceed to Next Step")
    st.markdown("*Continue to dataset configuration once generators are ready*")

    generators = st.session_state.api_generators

    # Check if at least one generator is ready
    ready_generators = [name for name, gen in generators.items() if gen.get("status") == "ready"]
    proceed_disabled = len(ready_generators) == 0

    if ready_generators:
        st.success(f"✅ {len(ready_generators)} generator(s) ready: {', '.join(ready_generators)}")
    else:
        st.warning("⚠️ No generators ready yet. Configure and test at least one generator to proceed.")

    if st.button(
        "Next: Configure Datasets",
        disabled=proceed_disabled,
        type="primary",
        help="Proceed to configure datasets for AI red-teaming operations",
    ):
        user_info = st.session_state.get("api_user_info", {})
        username = user_info.get("username", "User")
        logger.info(f"User '{username}' proceeded to 'Configure Datasets'.")

        # Save progress to session
        session_update = {
            "workflow_state": {
                "current_step": "proceeding_to_datasets",
                "generators_ready": len(ready_generators),
            },
            "temporary_data": {"transition_time": datetime.now().isoformat()},
        }
        save_session_to_api(session_update)

        st.switch_page("pages/2_Configure_Datasets.py")


# --- Helper Functions ---

# --- Run Main Function ---
if __name__ == "__main__":
    main()
