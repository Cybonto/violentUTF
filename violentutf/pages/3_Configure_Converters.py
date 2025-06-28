import asyncio
import json
import os
import pathlib
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# Load environment variables from .env file
from dotenv import load_dotenv

# Get the path to the .env file relative to this script
env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Use the centralized logging setup
from utils.logging import get_logger

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
    "database_stats": f"{API_BASE_URL}/api/v1/database/stats",
    # Converter endpoints
    "converters": f"{API_BASE_URL}/api/v1/converters",
    "converter_types": f"{API_BASE_URL}/api/v1/converters/types",
    "converter_params": f"{API_BASE_URL}/api/v1/converters/params/{{converter_type}}",
    "converter_preview": f"{API_BASE_URL}/api/v1/converters/{{converter_id}}/preview",
    "converter_apply": f"{API_BASE_URL}/api/v1/converters/{{converter_id}}/apply",
    "converter_delete": f"{API_BASE_URL}/api/v1/converters/{{converter_id}}",
    # Generator endpoints (for converter testing)
    "generators": f"{API_BASE_URL}/api/v1/generators",
    # Dataset endpoints (for converter application)
    "datasets": f"{API_BASE_URL}/api/v1/datasets",
    # Session endpoints
    "sessions": f"{API_BASE_URL}/api/v1/sessions",
    "sessions_update": f"{API_BASE_URL}/api/v1/sessions",
}

# Initialize session state for API-backed converters
if "api_converters" not in st.session_state:
    st.session_state.api_converters = {}
if "api_converter_types" not in st.session_state:
    st.session_state.api_converter_types = {}
if "api_datasets" not in st.session_state:
    st.session_state.api_datasets = {}
if "api_token" not in st.session_state:
    st.session_state.api_token = None
if "api_user_info" not in st.session_state:
    st.session_state.api_user_info = {}
if "current_converter" not in st.session_state:
    st.session_state.current_converter = None
if "converter_preview_results" not in st.session_state:
    st.session_state.converter_preview_results = []

# --- API Helper Functions ---


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    try:
        from utils.jwt_manager import jwt_manager

        # Get valid token (automatically handles refresh if needed)
        token = jwt_manager.get_valid_token()

        # If no valid JWT token, try to create one
        if not token:
            token = st.session_state.get("api_token") or st.session_state.get(
                "access_token"
            )

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
        logger.warning("No authentication token available for API request")
        return None

    try:
        logger.debug(f"Making {method} request to {url} through APISIX Gateway")
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 201:
            return response.json()
        elif response.status_code == 401:
            logger.error(f"401 Unauthorized: {response.text}")
            return None
        elif response.status_code == 403:
            logger.error(f"403 Forbidden: {response.text}")
            return None
        elif response.status_code == 404:
            logger.error(f"404 Not Found: {url} - {response.text}")
            return None
        elif response.status_code == 422:
            logger.error(f"422 Unprocessable Entity: {url} - {response.text}")
            # Try to parse validation error details
            try:
                error_detail = response.json()
                logger.error(f"Validation error details: {error_detail}")
                # Store error details for display
                st.session_state["last_api_error"] = error_detail
            except:
                st.session_state["last_api_error"] = response.text
            return None
        elif response.status_code == 502:
            logger.error(f"502 Bad Gateway: {response.text}")
            return None
        elif response.status_code == 503:
            logger.error(f"503 Service Unavailable: {response.text}")
            return None
        else:
            logger.error(f"API Error {response.status_code}: {url} - {response.text}")
            return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error to {url}: {e}")
        return None
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error to {url}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception to {url}: {e}")
        return None


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


# --- API Backend Functions ---


def load_converter_types_from_api():
    """Load available converter types from API"""
    data = api_request("GET", API_ENDPOINTS["converter_types"])
    if data:
        st.session_state.api_converter_types = data.get("categories", {})
        return data.get("categories", {})
    return {}


def load_converters_from_api():
    """Load existing converters from API"""
    data = api_request("GET", API_ENDPOINTS["converters"])
    if data:
        converters_dict = {conv["name"]: conv for conv in data.get("converters", [])}
        st.session_state.api_converters = converters_dict
        return converters_dict
    return {}


def get_converter_params_from_api(converter_type: str):
    """Get parameter definitions for a converter type from API"""
    url = API_ENDPOINTS["converter_params"].format(converter_type=converter_type)
    data = api_request("GET", url)
    if data:
        return data.get("parameters", []), data.get("requires_target", False)
    return [], False


def create_converter_via_api(
    name: str, converter_type: str, parameters: Dict[str, Any], generator_id: str = None
):
    """Create a new converter configuration via API"""
    payload = {"name": name, "converter_type": converter_type, "parameters": parameters}
    if generator_id:
        payload["generator_id"] = generator_id

    logger.info(f"Creating converter: {name} of type {converter_type}")
    logger.debug(f"Parameters: {parameters}")

    data = api_request("POST", API_ENDPOINTS["converters"], json=payload)
    if data:
        # Update local state
        converter_info = data.get("converter", {})
        if not converter_info:
            logger.error("API returned success but no converter data")
            st.error("API returned incomplete converter data")
            return False

        # Ensure we have an ID
        if "id" not in converter_info:
            logger.error(f"Converter created but missing ID field: {converter_info}")
            st.error("Converter created but missing ID field")
            return False

        st.session_state.api_converters[name] = converter_info
        st.session_state.current_converter = converter_info
        logger.info(f"Converter created successfully with ID: {converter_info['id']}")
        return True
    else:
        logger.error("Failed to create converter - no response from API")
        return False


def preview_converter_via_api(
    converter_id: str,
    sample_prompts: List[str] = None,
    dataset_id: str = None,
    num_samples: int = 1,
):
    """Preview converter effect via API"""
    url = API_ENDPOINTS["converter_preview"].format(converter_id=converter_id)
    payload = {"num_samples": num_samples}
    if sample_prompts:
        payload["sample_prompts"] = sample_prompts
    elif dataset_id:
        payload["dataset_id"] = dataset_id

    data = api_request("POST", url, json=payload)
    if data:
        return True, data.get("preview_results", [])
    return False, []


def apply_converter_via_api(
    converter_id: str, dataset_id: str, mode: str, new_dataset_name: str = None
):
    """Apply converter to dataset via API"""
    url = API_ENDPOINTS["converter_apply"].format(converter_id=converter_id)
    payload = {
        "dataset_id": dataset_id,
        "mode": mode,
        "save_to_memory": True,
        "save_to_session": True,
    }
    if new_dataset_name:
        payload["new_dataset_name"] = new_dataset_name

    logger.info(
        f"Applying converter {converter_id} to dataset {dataset_id} with mode {mode}"
    )
    logger.debug(f"Request URL: {url}")
    logger.debug(f"Request payload: {payload}")

    data = api_request("POST", url, json=payload)
    if data:
        return True, data
    else:
        logger.error(f"Failed to apply converter - no data returned from API")
        return False, {"error": "No response from API"}


def auto_load_generators():
    """
    Automatically load existing generators on page load

    This ensures that generators are available for converter testing
    without requiring manual refresh.
    """
    # Only load if not already loaded in session state
    if "api_generators_cache" not in st.session_state or st.session_state.get(
        "force_reload_generators", False
    ):
        with st.spinner("Loading generators for testing..."):
            generators = get_generators_from_api()
            if generators:
                st.session_state.api_generators_cache = generators
                logger.info(
                    f"Auto-loaded {len(generators)} generators for converter testing"
                )
            else:
                st.session_state.api_generators_cache = []
                logger.info(
                    "No generators found during auto-load for converter testing"
                )

        # Clear force reload flag
        if "force_reload_generators" in st.session_state:
            del st.session_state["force_reload_generators"]


def get_generators_from_api():
    """Get available generators for testing"""
    data = api_request("GET", API_ENDPOINTS["generators"])
    if data:
        return data.get("generators", [])
    return []


def get_cached_generators():
    """Get generators from cache or load them if not cached"""
    if "api_generators_cache" not in st.session_state:
        auto_load_generators()
    return st.session_state.get("api_generators_cache", [])


def auto_load_datasets():
    """
    Automatically load existing datasets on page load

    This ensures that previously configured datasets are immediately visible
    when the page loads, without requiring manual refresh.
    """
    # Only load if not already loaded or if forced reload
    if not st.session_state.api_datasets or st.session_state.get(
        "force_reload_datasets", False
    ):
        with st.spinner("Loading existing datasets..."):
            datasets_data = load_datasets_from_api()
            if datasets_data:
                logger.info(f"Auto-loaded datasets for display")
            else:
                logger.info("No existing datasets found during auto-load")

        # Clear force reload flag
        if "force_reload_datasets" in st.session_state:
            del st.session_state["force_reload_datasets"]


def load_datasets_from_api():
    """Load existing datasets from API"""
    data = api_request("GET", API_ENDPOINTS["datasets"])
    if data:
        datasets_dict = {ds["name"]: ds for ds in data.get("datasets", [])}
        st.session_state.api_datasets = datasets_dict
        return data
    return None


# --- Main Page Function ---
def main():
    """Renders the Configure Converters page content with API backend."""
    logger.debug("Configure Converters page (API-backed) loading.")
    st.set_page_config(
        page_title="Configure Converters",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- Authentication and Sidebar ---
    handle_authentication_and_sidebar("Configure Converters")

    # --- Page Content ---
    display_header()

    # Check if user is authenticated
    if not st.session_state.get("access_token"):
        return

    # Automatically generate API token if not present
    if not st.session_state.get("api_token"):
        api_token = create_compatible_api_token()
        if not api_token:
            return

    # Auto-load generators and datasets for consistency
    auto_load_generators()
    auto_load_datasets()

    # Main content in two columns
    col1, col2 = st.columns([1, 1])

    with col1:
        select_generator_and_dataset()
        display_converter_selection()

    with col2:
        configure_converter_parameters()

    # Full width sections
    preview_and_apply_converter()
    proceed_to_next_step()


def display_header():
    """Displays the main header for the page."""
    st.title("🔄 Configure Converters")
    st.markdown(
        "*Configure prompt converters to transform and enhance red-teaming inputs*"
    )


def select_generator_and_dataset():
    """Allow users to select a generator and dataset from the configured ones"""
    st.subheader("Select Generator and Dataset")

    # Load generators from cache
    generators = get_cached_generators()
    # Use cached datasets from session state
    datasets = (
        list(st.session_state.api_datasets.values())
        if st.session_state.api_datasets
        else []
    )

    if not generators:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.warning(
                "⚠️ No generators configured. Please configure a generator first."
            )
        with col2:
            if st.button(
                "🔄 Refresh",
                help="Refresh generator list",
                key="refresh_generators_conv",
            ):
                st.session_state["force_reload_generators"] = True
                st.rerun()
        return

    if not datasets:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.warning("⚠️ No datasets configured. Please configure a dataset first.")
        with col2:
            if st.button(
                "🔄 Refresh", help="Refresh dataset list", key="refresh_datasets_conv"
            ):
                st.session_state["force_reload_datasets"] = True
                st.rerun()
        return

    # Generator selection
    generator_names = [gen["name"] for gen in generators]
    selected_generator_name = st.selectbox(
        "Select Generator*", generator_names, key="selected_generator_name"
    )

    if selected_generator_name:
        selected_generator = next(
            gen for gen in generators if gen["name"] == selected_generator_name
        )
        st.session_state["selected_generator"] = selected_generator
        st.caption(f"🎯 Type: {selected_generator.get('type', 'Unknown')}")

    # Dataset selection
    dataset_names = [ds["name"] for ds in datasets]
    selected_dataset_name = st.selectbox(
        "Select Dataset*", dataset_names, key="selected_dataset_name"
    )

    if selected_dataset_name:
        try:
            selected_dataset = next(
                ds for ds in datasets if ds["name"] == selected_dataset_name
            )
            st.session_state["selected_dataset"] = selected_dataset
            st.caption(f"🗂️ Prompts: {selected_dataset.get('prompt_count', 0)}")

            # Dataset selected successfully
        except StopIteration:
            st.error(
                f"❌ Dataset '{selected_dataset_name}' not found. Please refresh the dataset list."
            )
            return


def display_converter_selection():
    """Display converter category and class selection"""
    st.subheader("Select Converter Class")

    # Load converter types if not already loaded
    if not st.session_state.api_converter_types:
        with st.spinner("Loading converter types..."):
            types = load_converter_types_from_api()
            if not types:
                st.error("❌ Failed to load converter types")
                return

    converter_categories = st.session_state.api_converter_types
    if not converter_categories:
        st.warning("No converter categories available.")
        return

    # Category selection
    selected_category = st.selectbox(
        "Select Converter Category",
        list(converter_categories.keys()),
        key="converter_category_select",
    )

    if selected_category:
        converters_in_category = converter_categories[selected_category]
        selected_converter = st.selectbox(
            "Select Converter Class",
            converters_in_category,
            key="converter_class_select",
        )

        if selected_converter:
            st.session_state["current_converter_class"] = selected_converter
            logger.info(f"Converter class selected: {selected_converter}")

            # Get converter parameter info
            try:
                params, requires_target = get_converter_params_from_api(
                    selected_converter
                )
                st.session_state["converter_requires_target"] = requires_target
                st.session_state["converter_params_info"] = params

                if requires_target:
                    st.info("🎯 This converter requires a target")
                else:
                    st.info("⚙️ Standalone converter")
            except Exception as e:
                st.error(f"Failed to load converter parameters: {e}")
                logger.error(f"Error getting converter params: {e}")


def configure_converter_parameters():
    """Display parameter input fields for the selected converter"""
    if "current_converter_class" not in st.session_state:
        st.subheader("Converter Parameters")
        st.info("Select a converter class first")
        return

    converter_class = st.session_state["current_converter_class"]
    st.subheader("Converter Parameters")

    # Add converter name customization field
    st.markdown("**Converter Configuration Name**")

    # Generate default name based on converter class
    # Check if we need to generate a new default name
    if (
        "generated_converter_name" not in st.session_state
        or st.session_state.get("last_converter_class") != converter_class
    ):
        st.session_state["generated_converter_name"] = (
            f"{converter_class}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        st.session_state["last_converter_class"] = converter_class

    default_name = st.session_state.get(
        "custom_converter_name", st.session_state["generated_converter_name"]
    )
    custom_name = st.text_input(
        "Enter a unique name for this converter configuration*",
        value=default_name,
        key="converter_custom_name_input",
        help="Give this converter configuration a meaningful name for easy identification",
        placeholder=f"e.g., {converter_class}_production, {converter_class}_test",
    )

    # Validate the custom name
    if custom_name:
        # Check if name already exists in configured converters
        existing_converters = st.session_state.get("api_converters", {})
        if custom_name in existing_converters and custom_name != st.session_state.get(
            "editing_converter_name"
        ):
            st.error(
                f"❌ A converter with the name '{custom_name}' already exists. Please choose a different name."
            )
        else:
            st.session_state["custom_converter_name"] = custom_name
    else:
        st.error("❌ Converter name is required")

    params_info = st.session_state.get("converter_params_info", [])

    if not params_info:
        st.info(f"Converter '{converter_class}' requires no parameters.")
        if "current_converter_params" not in st.session_state:
            st.session_state["current_converter_params"] = {}
        # Still need to save the converter with custom name even if no parameters
        if custom_name and custom_name not in existing_converters:
            if st.button(
                "💾 Save Converter", type="primary", key="save_converter_no_params"
            ):
                _save_converter_configuration(custom_name, converter_class, {})
        return

    # Check if parameters are already configured
    existing_params = st.session_state.get("current_converter_params", {})
    if existing_params:
        st.success(
            f"✅ Parameters configured for {converter_class} ({len(existing_params)} parameters)"
        )

    with st.form(key=f"{converter_class}_params_form"):
        form_valid = True
        temp_params = {}

        # Filter out UI-skipped parameters
        ui_params = [p for p in params_info if not p.get("skip_in_ui", False)]

        for param_info in ui_params:
            param_name = param_info["name"]
            param_type = param_info["primary_type"]
            required = param_info["required"]
            default_value = param_info.get("default")
            description = param_info.get(
                "description", param_name.replace("_", " ").capitalize()
            )
            literal_choices = param_info.get("literal_choices")

            # Use existing value if available
            if existing_params and param_name in existing_params:
                default_value = existing_params[param_name]

            label = f"{description} ({param_type})" + ("*" if required else "")
            widget_key = f"param_{converter_class}_{param_name}"

            # Render appropriate widget based on parameter type
            if literal_choices:
                # Use selectbox for literal types
                try:
                    default_index = (
                        literal_choices.index(default_value)
                        if default_value in literal_choices
                        else 0
                    )
                except (ValueError, TypeError):
                    default_index = 0

                value = st.selectbox(
                    label,
                    options=literal_choices,
                    index=default_index,
                    key=widget_key,
                    help=f"Required: {required}",
                )
            elif param_type == "bool":
                value = st.checkbox(
                    label,
                    value=bool(default_value) if default_value is not None else False,
                    key=widget_key,
                )
            elif param_type == "int":
                value = st.number_input(
                    label,
                    value=int(default_value) if default_value is not None else 0,
                    step=1,
                    key=widget_key,
                )
            elif param_type == "float":
                value = st.number_input(
                    label,
                    value=float(default_value) if default_value is not None else 0.0,
                    format="%.5f",
                    key=widget_key,
                )
            elif param_type == "list":
                default_text = (
                    "\n".join(map(str, default_value))
                    if isinstance(default_value, list)
                    else (default_value or "")
                )
                raw_list_input = st.text_area(
                    label, value=default_text, key=widget_key, height=100
                )
                value = raw_list_input
            else:  # Default to text input for str and other types
                value = st.text_input(
                    label,
                    value=str(default_value) if default_value is not None else "",
                    key=widget_key,
                )

            temp_params[param_name] = value

        # Form submit button with same style as Save Converter
        submitted = st.form_submit_button("💾 Save Converter", type="primary")

        if submitted:
            logger.info(f"Parameter form submitted for {converter_class}")
            st.session_state["current_converter_params"] = {}

            # Process and validate parameters
            try:
                for param_info in ui_params:
                    param_name = param_info["name"]
                    raw_value = temp_params.get(param_name)
                    param_type = param_info["primary_type"]
                    required = param_info["required"]

                    # Handle empty/None values
                    if raw_value is None or (
                        isinstance(raw_value, str) and not raw_value.strip()
                    ):
                        if required:
                            st.error(f"Parameter '{param_name}' is required.")
                            form_valid = False
                            continue
                        else:
                            final_value = None
                    else:
                        # Type conversion
                        try:
                            if param_type == "bool":
                                final_value = bool(raw_value)
                            elif param_type == "int":
                                final_value = int(raw_value)
                            elif param_type == "float":
                                final_value = float(raw_value)
                            elif param_type == "list":
                                final_value = [
                                    line.strip()
                                    for line in raw_value.strip().split("\n")
                                    if line.strip()
                                ]
                            else:
                                final_value = str(raw_value)
                        except ValueError as ve:
                            st.error(f"Invalid value for '{param_name}': {raw_value}")
                            form_valid = False
                            continue

                    # Store the converted value
                    st.session_state["current_converter_params"][
                        param_name
                    ] = final_value

                if form_valid and custom_name:
                    # Validate custom name one more time
                    existing_converters = st.session_state.get("api_converters", {})
                    if (
                        custom_name in existing_converters
                        and custom_name
                        != st.session_state.get("editing_converter_name")
                    ):
                        st.error(
                            f"❌ A converter with the name '{custom_name}' already exists."
                        )
                        st.session_state["current_converter_params"] = {}
                    else:
                        logger.info(
                            f"Converter parameters processed and stored: {st.session_state['current_converter_params']}"
                        )
                        # Save the converter configuration immediately
                        _save_converter_configuration(
                            custom_name,
                            converter_class,
                            st.session_state["current_converter_params"],
                        )
                else:
                    st.session_state["current_converter_params"] = {}
                    if not custom_name:
                        st.error("❌ Converter name is required.")
                    logger.warning(
                        f"Parameter form for {converter_class} submitted with invalid entries."
                    )

            except Exception as e:
                st.error(f"Error processing submitted parameters: {e}")
                logger.exception(f"Error processing parameters for {converter_class}")
                st.session_state["current_converter_params"] = {}


def _save_converter_configuration(
    custom_name: str, converter_class: str, parameters: Dict[str, Any]
):
    """Helper function to save converter configuration with custom name"""
    # Get generator ID if converter requires target
    generator_id = None
    if st.session_state.get("converter_requires_target", False):
        selected_generator = st.session_state.get("selected_generator")
        if selected_generator:
            generator_id = selected_generator["id"]
        else:
            st.error(
                "This converter requires a target. Please select a generator first."
            )
            return

    with st.spinner(f"Creating converter '{custom_name}'..."):
        success = create_converter_via_api(
            name=custom_name,
            converter_type=converter_class,
            parameters=parameters,
            generator_id=generator_id,
        )

        if success:
            st.success(f"✅ Converter '{custom_name}' created successfully!")
            # Clear the custom name and generated name for next converter
            if "custom_converter_name" in st.session_state:
                del st.session_state["custom_converter_name"]
            if "generated_converter_name" in st.session_state:
                del st.session_state["generated_converter_name"]
            # Refresh converters list
            load_converters_from_api()
            st.rerun()
        else:
            st.error(f"❌ Failed to create converter '{custom_name}'")


def preview_and_apply_converter():
    """Preview converter effects and apply to datasets"""
    st.divider()
    st.subheader("🔄 Preview & Apply Converter")

    # Load existing converters from API
    converters_data = load_converters_from_api()
    converters_list = (
        list(st.session_state.api_converters.values())
        if st.session_state.api_converters
        else []
    )

    # Add converter selection box with refresh button
    col1, col2 = st.columns([3, 1])

    with col1:
        if converters_list:
            # Create list of converter names for selection
            converter_names = [conv["name"] for conv in converters_list]
            selected_converter_name = st.selectbox(
                "Select Converter",
                converter_names,
                key="preview_converter_select",
                help="Choose an existing converter to preview and apply",
            )

            # Find the selected converter
            if selected_converter_name:
                current_converter = next(
                    (
                        conv
                        for conv in converters_list
                        if conv["name"] == selected_converter_name
                    ),
                    None,
                )
                if current_converter:
                    st.session_state["current_converter"] = current_converter
                    st.caption(
                        f"🔧 Type: {current_converter.get('type', 'Unknown')} | ID: {current_converter.get('id', 'Unknown')}"
                    )
        else:
            st.info("No converters configured yet. Configure a converter above first.")

            # If a converter was just configured, try to use it
            if "current_converter_class" in st.session_state:
                converter_class = st.session_state["current_converter_class"]
                converter_params = st.session_state.get("current_converter_params", {})

                # Check if we can create a converter instance
                if converter_params or not st.session_state.get(
                    "converter_params_info"
                ):
                    # Use custom name if available, otherwise generate default
                    custom_name = st.session_state.get("custom_converter_name")
                    if not custom_name:
                        custom_name = f"{converter_class}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                    # Get generator ID if converter requires target
                    generator_id = None
                    if st.session_state.get("converter_requires_target", False):
                        selected_generator = st.session_state.get("selected_generator")
                        if selected_generator:
                            generator_id = selected_generator["id"]
                        else:
                            st.warning(
                                "This converter requires a target. Please select a generator first."
                            )
                            return

                    with st.spinner(f"Creating converter '{custom_name}'..."):
                        success = create_converter_via_api(
                            name=custom_name,
                            converter_type=converter_class,
                            parameters=converter_params,
                            generator_id=generator_id,
                        )

                    if success:
                        # Refresh converters list
                        load_converters_from_api()
                        st.rerun()
                    else:
                        st.error("Failed to create converter configuration.")
                        return
                else:
                    st.warning("Configure converter parameters first.")
                    return

    with col2:
        if st.button(
            "🔄 Refresh Converters",
            help="Refresh converter list",
            key="refresh_converters_preview",
        ):
            with st.spinner("Refreshing converters..."):
                load_converters_from_api()
                st.rerun()

    # Check if we have a converter selected
    current_converter = st.session_state.get("current_converter")
    if not current_converter:
        return

    # Check if converter has an ID
    if "id" not in current_converter:
        st.error("❌ Converter configuration is missing ID field")
        st.write("Debug - Current converter data:")
        st.json(current_converter)
        return

    converter_id = current_converter["id"]

    # Two-column layout for preview and application
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Preview")

        # Option to use custom text or pull from dataset
        preview_source = st.radio(
            "Preview Source",
            ["Custom Text", "From Dataset"],
            key="preview_source",
            help="Choose whether to enter custom text or use prompts from an existing dataset",
        )

        sample_prompts = []

        if preview_source == "Custom Text":
            # Let user input their own test text
            custom_text = st.text_area(
                "Enter text to preview conversion",
                value="",
                height=100,
                key="preview_custom_text",
                placeholder="Enter your text here to see how the converter will transform it...",
            )
            if custom_text:
                sample_prompts = [custom_text]
        else:
            # Use prompts from selected dataset (allow mock datasets for preview)
            preview_datasets = (
                list(st.session_state.api_datasets.values())
                if st.session_state.api_datasets
                else []
            )
            if preview_datasets:
                preview_dataset_names = [ds["name"] for ds in preview_datasets]
                selected_preview_dataset = st.selectbox(
                    "Select dataset for preview",
                    preview_dataset_names,
                    key="preview_dataset_select",
                )
                if selected_preview_dataset:
                    try:
                        dataset_info = next(
                            ds
                            for ds in preview_datasets
                            if ds["name"] == selected_preview_dataset
                        )
                        st.caption(
                            f"Using prompts from: {dataset_info['name']} ({dataset_info.get('prompt_count', 0)} prompts)"
                        )

                        # Dataset loaded for preview
                    except StopIteration:
                        st.error(
                            f"❌ Dataset '{selected_preview_dataset}' not found. Please refresh the dataset list."
                        )
                        return
            else:
                st.warning("No datasets available for preview")

        if preview_source == "Custom Text":
            # For custom text, we already have the prompts
            preview_enabled = bool(sample_prompts)
        else:
            # For dataset source, enable preview if dataset is selected
            preview_enabled = (
                "selected_preview_dataset" in locals() and selected_preview_dataset
            )

        if st.button(
            "🔍 Preview Converter",
            key="preview_converter",
            disabled=not preview_enabled,
        ):
            with st.spinner("Generating preview..."):
                if preview_source == "From Dataset":
                    # When using dataset, pass dataset_id instead of sample prompts
                    try:
                        dataset_for_preview = next(
                            ds
                            for ds in preview_datasets
                            if ds["name"] == selected_preview_dataset
                        )
                        success, preview_results = preview_converter_via_api(
                            converter_id=converter_id,
                            dataset_id=dataset_for_preview["id"],
                            num_samples=1,
                        )
                    except StopIteration:
                        st.error(
                            f"❌ Dataset '{selected_preview_dataset}' not found for preview."
                        )
                        return
                else:
                    # Use custom text
                    success, preview_results = preview_converter_via_api(
                        converter_id=converter_id,
                        sample_prompts=sample_prompts,
                        num_samples=1,
                    )

            if success:
                st.session_state.converter_preview_results = preview_results
                st.success("✅ Preview generated successfully!")

                for i, result in enumerate(preview_results):
                    with st.expander(f"Sample {i+1}", expanded=True):
                        st.caption("Original:")
                        st.text(result["original_value"])
                        st.caption("Converted:")
                        st.text(result["converted_value"])
            else:
                st.error("❌ Failed to generate preview")

    with col2:
        st.subheader("Apply to Dataset")

        # Get available datasets for converter application (exclude mock datasets)
        all_datasets = (
            list(st.session_state.api_datasets.values())
            if st.session_state.api_datasets
            else []
        )
        datasets = all_datasets  # Use all datasets - no filtering needed

        if not datasets:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.warning("⚠️ No datasets available for converter operations.")
                st.info("💡 Please create a dataset first before applying converters.")

                # Show helpful guidance
                st.markdown("**To create a dataset:**")
                st.markdown("1. Go to 'Configure Datasets' page")
                st.markdown(
                    "2. Choose a dataset source (Native, Local File, Online, etc.)"
                )
                st.markdown("3. Configure and save the dataset")
                st.markdown("4. Return here to apply converters")

                if st.button(
                    "📊 Go to Configure Datasets", key="go_to_datasets_no_real"
                ):
                    st.switch_page("pages/2_Configure_Datasets.py")
            with col2:
                if st.button(
                    "🔄 Refresh",
                    help="Refresh dataset list",
                    key="refresh_datasets_apply",
                ):
                    st.session_state["force_reload_datasets"] = True
                    st.rerun()
            return

        # Dataset selection dropdown
        dataset_names = [ds["name"] for ds in datasets]
        selected_dataset_name = st.selectbox(
            "Select Dataset to Convert*",
            dataset_names,
            key="converter_apply_dataset_select",
            help="Choose which dataset to apply the converter to",
        )

        if not selected_dataset_name:
            st.warning("Please select a dataset to apply the converter to.")
            return

        # Get the selected dataset object
        try:
            selected_dataset = next(
                ds for ds in datasets if ds["name"] == selected_dataset_name
            )
            st.caption(
                f"🗂️ Selected: {selected_dataset['name']} ({selected_dataset.get('prompt_count', 0)} prompts)"
            )
        except StopIteration:
            st.error(
                f"❌ Dataset '{selected_dataset_name}' not found. Please refresh the dataset list."
            )
            return

        # Application mode selection
        mode = st.radio(
            "Application Mode",
            ["overwrite", "copy"],
            key="application_mode",
            help="Overwrite: modifies original dataset. Copy: creates new dataset.",
        )

        new_dataset_name = None
        if mode == "copy":
            # Sanitize the dataset name to remove spaces and special characters
            default_name = selected_dataset["name"].replace(" ", "_").replace("-", "_")
            default_name = "".join(
                c if c.isalnum() or c == "_" else "" for c in default_name
            )
            new_dataset_name = st.text_input(
                "New Dataset Name*",
                value=f"{default_name}_converted",
                key="new_dataset_name",
                help="Only alphanumeric characters, underscores, and hyphens allowed",
            )

        if st.button("🚀 Apply Converter", key="apply_converter"):
            if mode == "copy" and not new_dataset_name:
                st.error("Please enter a name for the new dataset.")
                return

            # Dataset is valid for converter application

            # Validate dataset name format
            if new_dataset_name:
                import re

                if not re.match(r"^[a-zA-Z0-9_-]+$", new_dataset_name):
                    st.error(
                        "Dataset name can only contain alphanumeric characters, underscores, and hyphens (no spaces)."
                    )
                    return

            with st.spinner("Applying converter to dataset..."):
                success, result = apply_converter_via_api(
                    converter_id=converter_id,
                    dataset_id=selected_dataset["id"],
                    mode=mode,  # Use lowercase mode as API expects
                    new_dataset_name=new_dataset_name,
                )

            if success:
                st.success(f"✅ Converter applied successfully!")
                st.info(f"**Result:** {result.get('message', 'Conversion completed')}")

                # Debug: Show what the API returned
                with st.expander("🔍 API Response Details", expanded=False):
                    st.json(result)
                st.session_state["converter_applied"] = True
                st.session_state["converted_dataset"] = result

                # If copy mode, check if new dataset was created
                if mode == "copy" and new_dataset_name:
                    # Check the API response for new dataset info
                    if "dataset_id" in result and "dataset_name" in result:
                        st.success(
                            f"📊 Converter created new dataset: '{result['dataset_name']}'"
                        )
                        st.info(f"**New Dataset Details from API:**")
                        st.write(f"• Name: {result['dataset_name']}")
                        st.write(f"• ID: {result['dataset_id']}")
                        st.write(
                            f"• Converted Prompts: {result.get('converted_count', 0)}"
                        )

                    # Refresh datasets to check if it was actually created
                    with st.spinner("Checking if dataset was created..."):
                        import time

                        time.sleep(1)  # Give backend a moment to save
                        # Force reload datasets from API
                        st.session_state["force_reload_datasets"] = True
                        auto_load_datasets()
                        updated_datasets = (
                            list(st.session_state.api_datasets.values())
                            if st.session_state.api_datasets
                            else []
                        )
                        if updated_datasets:
                            # Check if the new dataset is in the list
                            new_dataset = next(
                                (
                                    ds
                                    for ds in updated_datasets
                                    if ds["name"] == new_dataset_name
                                ),
                                None,
                            )
                            if new_dataset:
                                st.success(
                                    f"✅ Verified: Dataset '{new_dataset_name}' is now available!"
                                )
                            else:
                                st.info(
                                    f"ℹ️ Dataset '{new_dataset_name}' was processed but is not yet visible in the datasets list. "
                                    "This indicates the backend is running in simulation mode."
                                )

            else:
                st.error("❌ Failed to apply converter")
                logger.error(
                    f"Failed to apply converter {converter_id} to dataset {selected_dataset['id']}"
                )

                # Check for validation error details
                api_error = st.session_state.get("last_api_error")
                if api_error:
                    st.error("**API Validation Error:**")
                    if isinstance(api_error, dict):
                        # Display validation error details
                        if "detail" in api_error:
                            if isinstance(api_error["detail"], list):
                                for error in api_error["detail"]:
                                    st.error(
                                        f"• {error.get('msg', 'Unknown error')} - Field: {error.get('loc', ['Unknown'])[-1]}"
                                    )
                            else:
                                st.error(f"• {api_error['detail']}")
                        else:
                            st.json(api_error)
                    else:
                        st.error(api_error)

                    # Clear the error after displaying
                    st.session_state.pop("last_api_error", None)

                # Show troubleshooting info
                with st.expander("🔍 Troubleshooting Information", expanded=True):
                    st.write("**Common causes:**")
                    st.write("• Converter not properly configured")
                    st.write("• Dataset not accessible or invalid")
                    st.write("• API connectivity issues")
                    st.write("• Missing required fields in request")
                    st.write("")
                    st.write("**Debug Info:**")
                    st.write(f"• Converter ID: {converter_id}")
                    st.write(
                        f"• Dataset: {selected_dataset['name']} (ID: {selected_dataset['id']})"
                    )
                    st.write(f"• Mode: {mode}")
                    if new_dataset_name:
                        st.write(f"• New Dataset Name: {new_dataset_name}")
                    st.write("")
                    st.write("**Request being sent:**")
                    request_data = {
                        "dataset_id": selected_dataset["id"],
                        "mode": mode,  # Show the actual mode being sent
                        "save_to_memory": True,
                        "save_to_session": True,
                    }
                    if new_dataset_name:
                        request_data["new_dataset_name"] = new_dataset_name
                    st.json(request_data)
                    st.write("")
                    st.write("**Check logs:** `docker compose logs fastapi --tail=50`")


def proceed_to_next_step():
    """Provide button to proceed to next step"""
    if not st.session_state.get("converter_applied", False):
        return

    st.divider()
    st.header("🚀 Proceed to Next Step")
    st.markdown("*Continue to scorer configuration once converters are ready*")

    if st.button(
        "Next: Configure Scorers",
        type="primary",
        use_container_width=True,
        help="Proceed to configure scorers for AI red-teaming evaluation",
    ):
        logger.info("User proceeded to next step after configuring converters.")

        # Save progress to session
        session_update = {
            "ui_preferences": {"last_page": "Configure Converters"},
            "workflow_state": {"current_step": "converters_configured"},
            "temporary_data": {
                "last_converter_configured": st.session_state.get(
                    "current_converter", {}
                ).get("name")
            },
        }
        api_request("PUT", API_ENDPOINTS["sessions_update"], json=session_update)

        st.switch_page("pages/4_Configure_Scorers.py")


# --- Helper Functions ---

# Import centralized auth utility
from utils.auth_utils import handle_authentication_and_sidebar

# --- Run Main Function ---
if __name__ == "__main__":
    main()
