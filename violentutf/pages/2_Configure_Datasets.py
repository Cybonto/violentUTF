# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Dataset configuration page for ViolentUTF.

Provides interface for configuring datasets used in red-teaming and adversarial testing.
"""

import base64
import json
import os
import pathlib
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

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
    "database_stats": f"{API_BASE_URL}/api/v1/database/stats",
    # Dataset endpoints
    "datasets": f"{API_BASE_URL}/api/v1/datasets",
    "dataset_types": f"{API_BASE_URL}/api/v1/datasets/types",
    "dataset_preview": f"{API_BASE_URL}/api/v1/datasets/preview",
    "dataset_memory": f"{API_BASE_URL}/api/v1/datasets/memory",
    "dataset_field_mapping": f"{API_BASE_URL}/api/v1/datasets/field-mapping",
    "dataset_transform": f"{API_BASE_URL}/api/v1/datasets/{{dataset_id}}/transform",
    "dataset_delete": f"{API_BASE_URL}/api/v1/datasets/{{dataset_id}}",
    # Generator endpoints (for testing datasets)
    "generators": f"{API_BASE_URL}/api/v1/generators",
    # Orchestrator endpoints
    "orchestrators": f"{API_BASE_URL}/api/v1/orchestrators",
    "orchestrator_create": f"{API_BASE_URL}/api/v1/orchestrators",
    "orchestrator_types": f"{API_BASE_URL}/api/v1/orchestrators/types",
    "orchestrator_execute": f"{API_BASE_URL}/api/v1/orchestrators/{{orchestrator_id}}/executions",
    "orchestrator_memory": f"{API_BASE_URL}/api/v1/orchestrators/{{orchestrator_id}}/memory",
    # Session endpoints
    "sessions": f"{API_BASE_URL}/api/v1/sessions",
    "sessions_update": f"{API_BASE_URL}/api/v1/sessions",
}

# Initialize session state for API-backed datasets
if "api_datasets" not in st.session_state:
    st.session_state.api_datasets = {}
if "api_dataset_types" not in st.session_state:
    st.session_state.api_dataset_types = []
if "api_token" not in st.session_state:
    st.session_state.api_token = None
if "api_user_info" not in st.session_state:
    st.session_state.api_user_info = {}
if "current_dataset" not in st.session_state:
    st.session_state.current_dataset = None
if "dataset_source_selection" not in st.session_state:
    st.session_state.dataset_source_selection = None

# --- API Helper Functions ---


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    try:
        from utils.jwt_manager import jwt_manager

        # Get valid token (automatically handles refresh if needed)
        token = jwt_manager.get_valid_token()

        # If no valid JWT token, try to create one
        if not token:
            token = st.session_state.get("api_token") or st.session_state.get("access_token")

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
        logger.error(f"Failed to get auth headers: {e}")
        return {}


def api_request(method: str, url: str, **kwargs: Any) -> Optional[Dict[str, Any]]:  # noqa: ANN401
    """Make an authenticated API request through APISIX Gateway"""
    headers = get_auth_headers()
    if not headers.get("Authorization"):
        logger.warning("No authentication token available for API request")
        return None

    try:
        logger.debug(f"Making {method} request to {url} through APISIX Gateway")
        response = requests.request(method, url, headers=headers, timeout=30, **cast(Any, kwargs))

        # Debug: always log the response for troubleshooting
        logger.info(f"API Request: {method} {url} -> {response.status_code}")
        if response.status_code not in [200, 201]:
            logger.error(f"API Error Response: {response.text}")

        if response.status_code == 200:
            result = response.json()

            return cast(Dict[str, Any], result)
        elif response.status_code == 201:
            return cast(Dict[str, Any], response.json())
        elif response.status_code == 401:
            logger.error(f"401 Unauthorized: {response.text}")
            return None
        elif response.status_code == 403:
            logger.error(f"403 Forbidden: {response.text}")
            return None
        elif response.status_code == 404:
            logger.error(f"404 Not Found: {url} - {response.text}")
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
            # Store the token in session state for API calls
            st.session_state["api_token"] = api_token
            return cast(str, api_token)
        else:
            st.error(
                "🚨 Security Error: JWT secret key not configured. Please set JWT_SECRET_KEY environment variable."
            )
            logger.error("Failed to create API token - JWT secret key not available")
            return None

    except Exception as e:
        st.error("❌ Failed to generate API token. Please try refreshing the page.")
        logger.error(f"Token creation failed: {e}")
        return None


# --- API Backend Functions ---


def load_dataset_types_from_api() -> List[str]:
    """Load available dataset types from API"""
    data = api_request("GET", API_ENDPOINTS["dataset_types"])
    if data:
        st.session_state.api_dataset_types = data.get("dataset_types", [])
        return cast(List[str], data.get("dataset_types", []))
    return []


def load_datasets_from_api() -> List[Dict[str, Any]]:
    """Load existing datasets from API"""
    data = api_request("GET", API_ENDPOINTS["datasets"])
    if data:
        datasets_list = cast(List[Dict[str, Any]], data.get("datasets", []))
        datasets_dict = {ds["name"]: ds for ds in datasets_list}
        st.session_state.api_datasets = datasets_dict
        return datasets_list
    return []


def create_dataset_via_api(name: str, source_type: str, config: Dict[str, Any]) -> bool:
    """Create a new dataset via API"""
    payload = {"name": name, "source_type": source_type, "config": config}

    # Add source-specific fields
    if source_type == "native" and "dataset_type" in config:
        payload["dataset_type"] = config["dataset_type"]
    elif source_type == "online" and "url" in config:
        payload["url"] = config["url"]
    elif source_type == "local" and "file_content" in config:
        payload["file_content"] = config["file_content"]
        payload["file_type"] = config.get("file_type", "csv")
        payload["field_mappings"] = config.get("field_mappings", {})

    data = api_request("POST", API_ENDPOINTS["datasets"], json=payload)
    if data:
        # Update local state
        dataset_info = data.get("dataset", {})
        st.session_state.api_datasets[name] = dataset_info
        st.session_state.current_dataset = dataset_info
        return True
    return False


def load_memory_datasets_from_api() -> List[Dict[str, Any]]:
    """Load datasets from PyRIT memory via API"""
    data = api_request("GET", API_ENDPOINTS["dataset_memory"])
    if data:
        return cast(List[Dict[str, Any]], data.get("datasets", []))
    return []


def auto_load_datasets() -> None:
    """
    Automatically load existing datasets on page load

    This ensures that previously configured datasets are immediately visible
    when the page loads, without requiring manual refresh.
    """
    # Only load if not already loaded or if forced reload
    if not st.session_state.api_datasets or st.session_state.get("force_reload_datasets", False):
        with st.spinner("Loading existing datasets..."):
            datasets_data = load_datasets_from_api()
            if datasets_data:
                logger.info("Auto-loaded datasets for display")
            else:
                logger.info("No existing datasets found during auto-load")

        # Clear force reload flag
        if "force_reload_datasets" in st.session_state:
            del st.session_state["force_reload_datasets"]


def auto_load_generators() -> None:
    """
    Automatically load existing generators on page load

    This ensures that generators are available for dataset testing
    without requiring manual refresh.
    """
    # Only load if not already loaded in session state
    if "api_generators_cache" not in st.session_state or st.session_state.get("force_reload_generators", False):
        with st.spinner("Loading generators for testing..."):
            generators = get_generators(use_cache=False)
            if generators:
                st.session_state.api_generators_cache = generators
                logger.info(f"Auto-loaded {len(generators)} generators for dataset testing")
            else:
                st.session_state.api_generators_cache = []
                logger.info("No generators found during auto-load for dataset testing")

        # Clear force reload flag
        if "force_reload_generators" in st.session_state:
            del st.session_state["force_reload_generators"]


def get_generators(use_cache: bool = True) -> List[Dict[str, Any]]:
    """Get generators from cache or API

    Args:
        use_cache: If True, returns cached generators if available.
                  If False, always fetches from API.

    Returns:
        List of generator configurations
    """
    if use_cache and "api_generators_cache" in st.session_state:
        return cast(List[Dict[str, Any]], st.session_state.api_generators_cache)

    # Load from API
    data = api_request("GET", API_ENDPOINTS["generators"])
    generators = data.get("generators", []) if data else []

    # Cache for future use
    st.session_state.api_generators_cache = generators
    return generators


def run_orchestrator_dataset_test(
    dataset: Dict[str, Any], generator: Dict[str, Any], num_prompts: int, test_mode: str
) -> bool:
    """
    Run dataset test using orchestrator API

    Args:
        dataset: Selected dataset configuration
        generator: Selected generator configuration
        num_prompts: Number of prompts to test
        test_mode: Either "Quick Test" or "Detailed Test"

    Returns:
        bool: True if test successful, False otherwise
    """
    try:
        # Create orchestrator configuration

        # Prepare orchestrator parameters
        # Pass generator configuration as a reference that the orchestrator can resolve
        orchestrator_params: Dict[str, Any] = {
            "objective_target": {  # Correct parameter name for PromptSendingOrchestrator
                "type": "configured_generator",
                "generator_name": generator["name"],  # Use generator name for lookup
            }
            # Note: PromptSendingOrchestrator doesn't use scorer_configs
        }

        # Add test mode specific configurations
        if test_mode == "Detailed Test":
            orchestrator_params["verbose"] = True
            orchestrator_params["batch_size"] = 1  # Process one at a time for detailed analysis
        else:
            orchestrator_params["batch_size"] = min(num_prompts, 5)  # Process in small batches

        # Create orchestrator configuration via API
        orchestrator_payload = {
            "name": f"test_orchestrator_{dataset['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "orchestrator_type": "PromptSendingOrchestrator",  # Basic orchestrator for dataset testing
            "description": f"Testing dataset '{dataset['name']}' with generator '{generator['name']}'",
            "parameters": orchestrator_params,
            "tags": ["dataset_test", dataset["name"], generator["name"]],
        }

        # Get current user context for generator resolution
        user_info = api_request("GET", API_ENDPOINTS["auth_token_info"])
        user_context = user_info.get("username") if user_info else "unknown_user"
        logger.info(f"Using user context for generator resolution: {user_context}")
        logger.info(f"User info from API: {user_info}")

        # Also debug the generator being tested
        logger.info(f"Generator being tested: {generator['name']}")
        logger.info(f"Generator details: {generator}")
        logger.info(f"Dataset being tested: {dataset['name']}")
        logger.info(f"Dataset details: {dataset}")

        # Add user context to orchestrator parameters for generator resolution
        orchestrator_params["user_context"] = str(user_context) if user_context else "unknown_user"

        # Make API request to create orchestrator
        logger.info(f"Creating orchestrator with payload: {orchestrator_payload}")
        logger.info(f"Orchestrator create URL: {API_ENDPOINTS['orchestrator_create']}")
        logger.info(f"Available generators for context: {[gen.get('name') for gen in get_generators()]}")

        # Show payload structure for debugging
        with st.expander("🔍 Debug Info - Orchestrator Payload", expanded=False):
            st.json(orchestrator_payload)
            st.write(f"**API Endpoint:** `{API_ENDPOINTS['orchestrator_create']}`")
            st.write(f"**User Context:** `{user_context}`")

        try:
            orchestrator_response = api_request("POST", API_ENDPOINTS["orchestrator_create"], json=orchestrator_payload)
        except Exception as e:
            logger.error(f"Exception during orchestrator creation: {e}")
            st.error(f"❌ Exception during orchestrator creation: {str(e)}")
            return False

        if not orchestrator_response:
            logger.error("Failed to create orchestrator - no response from API")
            # Try to get more detailed error information
            try:
                headers = get_auth_headers()
                debug_response = requests.post(
                    API_ENDPOINTS["orchestrator_create"], json=orchestrator_payload, headers=headers, timeout=30
                )
                logger.error(f"Debug response status: {debug_response.status_code}")
                logger.error(f"Debug response text: {debug_response.text}")

                # Try to parse JSON error for more details
                try:
                    error_details = debug_response.json()
                    error_msg = error_details.get("detail", debug_response.text)
                    st.error(f"❌ Orchestrator creation failed: {error_msg}")
                except Exception:
                    st.error(
                        f"❌ Failed to create orchestrator - API returned {debug_response.status_code}: "
                        f"{debug_response.text}"
                    )
            except Exception as debug_error:
                logger.error(f"Debug request also failed: {debug_error}")
                st.error("❌ Failed to create orchestrator - check API connectivity and authentication")
            return False

        logger.info(f"Orchestrator creation response: {orchestrator_response}")

        orchestrator_id = orchestrator_response.get("orchestrator_id")
        # st.success(f"✅ Orchestrator created: {orchestrator_id}")

        # Execute orchestrator with dataset

        # Prepare execution request
        execution_payload = {
            "execution_name": f"test_{dataset['name']}_{datetime.now().strftime('%H%M%S')}",
            "execution_type": "dataset",
            "input_data": {"dataset_id": dataset["id"], "sample_size": num_prompts, "randomize": True},
        }

        # Execute orchestrator
        with st.spinner(f"Testing {num_prompts} prompts from '{dataset['name']}' using '{generator['name']}'..."):
            execution_url = API_ENDPOINTS["orchestrator_execute"].format(orchestrator_id=orchestrator_id)
            execution_response = api_request("POST", execution_url, json=execution_payload)

        if not execution_response:
            st.error("❌ Failed to execute orchestrator")
            return False

        # Display results

        execution_status = execution_response.get("status")

        if execution_status == "completed":
            st.info("ℹ️ Orchestrator execution marked as completed. Analyzing results...")

            # Results should be at the top level (spread from **results in the API)
            results_data = execution_response

            # Display execution summary
            if "execution_summary" in results_data:
                summary = results_data["execution_summary"]

                st.markdown("### 📊 Execution Summary")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Prompts", summary.get("total_prompts", num_prompts))
                with col2:
                    st.metric("Successful", summary.get("successful_prompts", 0))
                with col3:
                    success_rate = summary.get("success_rate", 0) * 100
                    st.metric("Success Rate", f"{success_rate:.1f}%")
                with col4:
                    avg_time = summary.get("avg_response_time_ms", 0)
                    st.metric("Avg Time", f"{avg_time:.0f}ms" if avg_time > 0 else "N/A")

                # Additional summary details
                if summary.get("total_time_seconds", 0) > 0:
                    st.info(f"⏱️ Total execution time: {summary['total_time_seconds']:.2f} seconds")
            else:
                st.warning(
                    "⚠️ No execution summary found. The orchestrator completed but didn't return summary statistics."
                )

            # Display detailed results if available
            prompt_responses = results_data.get("prompt_request_responses", [])

            if prompt_responses:
                responses = prompt_responses
                st.write("**📊 Detailed Test Results:**")

                # Show statistics
                total_responses = len(responses)
                # Calculate average response length safely
                response_lengths = []
                for r in responses:
                    content = r.get("response", {}).get("content")
                    if content and isinstance(content, str):
                        response_lengths.append(len(content))
                    else:
                        response_lengths.append(0)
                avg_response_length = sum(response_lengths) / total_responses if total_responses > 0 else 0

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Responses", total_responses)
                with col2:
                    st.metric("Avg Response Length", f"{avg_response_length:.0f} chars")
                with col3:
                    # Calculate response time if available
                    response_times = []
                    for r in responses:
                        if "metadata" in r and r["metadata"]:
                            time_ms = r["metadata"].get("response_time_ms")
                            if time_ms is not None and isinstance(time_ms, (int, float)):
                                response_times.append(time_ms)
                    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                    st.metric("Avg Response Time", f"{avg_response_time:.0f}ms" if avg_response_time > 0 else "N/A")

                # Show only one sample result
                st.write(f"\n**📝 Sample Result (from {len(responses)} total responses):**")

                # Show only the first response
                if responses:
                    response = responses[0]
                    with st.container():
                        try:
                            # Prompt section
                            if "request" in response and response["request"]:
                                st.markdown("**📤 Prompt:**")
                                prompt_text = response["request"].get("prompt", "N/A")
                                if prompt_text is None:
                                    prompt_text = "N/A"
                                st.code(prompt_text, language="text")
                                st.caption(f"Length: {len(str(prompt_text))} characters")

                            # Response section
                            if "response" in response and response["response"]:
                                st.markdown("**📥 Response:**")
                                response_content = response["response"].get("content", "N/A")
                                if response_content is None:
                                    response_content = "No response content"

                                # Show full response in detailed mode, truncated in quick mode
                                if test_mode == "Detailed Test":
                                    st.text_area(
                                        "Full Response", response_content, height=200, disabled=True, key="response_1"
                                    )
                                else:
                                    display_content = str(response_content)[:500]
                                    if len(str(response_content)) > 500:
                                        display_content += "..."
                                    st.text(display_content)

                                st.caption(f"Length: {len(str(response_content))} characters")
                        except Exception as e:
                            st.error(f"Error displaying result: {str(e)}")

                        # Metadata section
                        if "metadata" in response and response["metadata"]:
                            st.markdown("**🔧 Metadata:**")
                            metadata = response["metadata"]

                            # Display key metadata in a formatted way
                            col1, col2 = st.columns(2)
                            with col1:
                                if "response_time_ms" in metadata:
                                    st.write(f"⏱️ **Response Time:** {metadata['response_time_ms']}ms")
                                if "model" in metadata:
                                    st.write(f"🤖 **Model:** {metadata['model']}")
                                if "provider" in metadata:
                                    st.write(f"☁️ **Provider:** {metadata['provider']}")

                            with col2:
                                if "tokens_used" in metadata:
                                    st.write(f"🎯 **Tokens Used:** {metadata['tokens_used']}")
                                if "timestamp" in metadata:
                                    st.write(f"🕐 **Timestamp:** {metadata['timestamp']}")

                            # Show full metadata in detailed mode
                            if test_mode == "Detailed Test":
                                with st.expander("View Full Metadata"):
                                    st.json(metadata)

                # Export option for detailed test
                if test_mode == "Detailed Test" and len(responses) > 0:
                    st.markdown("---")
                    st.markdown("**💾 Export Results:**")

                    # Prepare export data
                    export_data = {
                        "test_info": {
                            "dataset": dataset["name"],
                            "generator": generator["name"],
                            "num_prompts": num_prompts,
                            "test_mode": test_mode,
                            "timestamp": datetime.now().isoformat(),
                        },
                        "summary": results_data.get("execution_summary", {}),
                        "results": responses,
                    }

                    # JSON export
                    json_str = json.dumps(export_data, indent=2)
                    st.download_button(
                        label="📥 Download Results (JSON)",
                        data=json_str,
                        file_name=f"dataset_test_{dataset['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                    )
            else:
                # No prompt responses available
                st.error("❌ No prompt/response data returned by the orchestrator")

                # Show what we have
                st.markdown("**🔍 Investigation:**")

                # Check specific issues
                issues = []
                if "prompt_request_responses" not in results_data:
                    issues.append("• No 'prompt_request_responses' field in the response")
                if "execution_summary" not in results_data:
                    issues.append("• No 'execution_summary' field in the response")
                if not results_data.get("prompt_request_responses"):
                    issues.append("• 'prompt_request_responses' exists but is empty")

                if issues:
                    st.write("**Issues found:**")
                    for issue in issues:
                        st.write(issue)

                # Try to show any available data
                if execution_response:
                    st.markdown("**📋 Response Data:**")

                    # Show execution ID and status
                    if "execution_id" in execution_response:
                        st.write(f"**Execution ID:** `{execution_response['execution_id']}`")

                    # Show any error information
                    if "error" in execution_response:
                        st.error(f"**Error:** {execution_response['error']}")

                # Possible reasons
                st.markdown("**🤔 Possible reasons for missing data:**")
                st.write(
                    "1. **Orchestrator didn't execute prompts** - The orchestrator was created "
                    "but didn't actually run the dataset test"
                )
                st.write(
                    "2. **Memory synchronization issue** - Results are stored in PyRIT memory "
                    "but not returned in the response"
                )
                st.write(
                    "3. **Response serialization issue** - Results exist but weren't properly "
                    "formatted for the API response"
                )
                st.write(
                    "4. **Generator execution failure** - The generator failed to process prompts "
                    "but the error wasn't propagated"
                )

                # Next steps
                st.markdown("**🔧 Troubleshooting steps:**")
                st.write("1. Check the Docker logs: `docker compose logs fastapi --tail=100`")
                st.write("2. Verify the generator is working by testing it directly")
                st.write("3. Try with a smaller number of prompts (1-2) to isolate the issue")
                st.write("4. Check if the dataset has valid prompts")

            return True

        elif execution_status == "failed":
            st.error("❌ Dataset test failed")
            if "error" in execution_response:
                st.error(f"Error: {execution_response['error']}")
            return False

        else:
            # For async execution, we'd need to poll for results
            st.info(f"⏳ Test status: {execution_status}")
            st.info("Test is running asynchronously. Results will be available shortly.")
            return True

    except Exception as e:
        logger.error(f"Error running dataset test: {e}")
        st.error(f"❌ Test error: {str(e)}")

        # Provide helpful debugging information
        if "connection" in str(e).lower():
            st.info(
                "💡 **Connection Issue**: Check that the FastAPI service is running and "
                "accessible through APISIX gateway"
            )
        elif "404" in str(e):
            st.info(
                "💡 **Endpoint Not Found**: The orchestrator endpoints may not be fully configured. "
                "Please check the API routes."
            )
        elif "authentication" in str(e).lower() or "401" in str(e):
            st.info("💡 **Authentication Issue**: Your session may have expired. Try refreshing the page.")

        return False


# --- Main Page Function ---
def main() -> None:
    """Render the Configure Datasets page content with API backend."""
    logger.debug("Configure Datasets page (API-backed) loading.")
    st.set_page_config(page_title="Configure Datasets", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

    # --- Authentication and Sidebar ---
    handle_authentication_and_sidebar("Configure Datasets")

    # --- Page Content ---
    st.title("📊 Configure Datasets")
    st.markdown("*Configure datasets for red-teaming prompts and attack strategies*")

    # Check if user is authenticated
    if not st.session_state.get("access_token"):
        return

    # Clear any cached inconsistent username to force re-evaluation with corrected logic
    # The system should use 'violentutf.web' (account name) as the unique identifier
    if "consistent_username" in st.session_state:
        cached_username = st.session_state["consistent_username"]
        # Clear any display name cached as username to force account name usage
        if " " in cached_username:  # Display names like "Tam Nguyen" contain spaces
            logger.info(f"Clearing cached display name '{cached_username}' to use account name instead")
            del st.session_state["consistent_username"]

    # Automatically generate API token if not present
    if not st.session_state.get("api_token"):
        api_token = create_compatible_api_token()
        if not api_token:
            return

    # Auto-load datasets and generators
    auto_load_datasets()
    auto_load_generators()

    # Show current configuration first
    display_configured_datasets()

    # Main content in two columns
    col1, col2 = st.columns([1, 1])

    with col1:
        display_dataset_source_selection()

    with col2:
        handle_dataset_source_flow()

    # Full width sections
    test_dataset_section()
    proceed_to_next_step()


def display_dataset_source_selection() -> None:
    """Display dataset source selection options"""
    st.subheader("➕ Configure a New Dataset")
    st.write("Select the source of your dataset:")

    options = [
        "Select Natively Supported Datasets",
        "Upload Local Dataset File",
        "Fetch from Online Dataset",
        "Load from PyRIT Memory",
        "Combining Datasets",
        "Transforming Dataset",
    ]

    selected_source = st.radio("Dataset Source", options, key="dataset_source_selection")

    # Map selected option to internal value
    source_mapping = {
        "Select Natively Supported Datasets": "native",
        "Upload Local Dataset File": "local",
        "Fetch from Online Dataset": "online",
        "Load from PyRIT Memory": "memory",
        "Combining Datasets": "combination",
        "Transforming Dataset": "transform",
    }

    if selected_source and selected_source in source_mapping:
        st.session_state["dataset_source"] = source_mapping[selected_source]
        logger.info(f"Dataset source selected: {st.session_state['dataset_source']}")


def display_configured_datasets() -> None:
    """Display configured datasets and generators"""
    # Display configured datasets
    datasets = st.session_state.api_datasets
    if datasets:
        with st.expander(f"📁 Datasets ({len(datasets)} configured)", expanded=True):
            for name, dataset in datasets.items():
                prompt_count = dataset.get("prompt_count", 0)
                source_type = dataset.get("source_type", "unknown")
                st.write(f"• **{name}** ({prompt_count} prompts) - Source: {source_type}")

        # Manual refresh option
        if st.button("🔄 Refresh Datasets", help="Refresh dataset list from API", key="refresh_datasets_btn"):
            with st.spinner("Refreshing datasets..."):
                load_datasets_from_api()
                st.rerun()
    else:
        st.info("🆕 No datasets configured yet. Create your first dataset below.")

    st.markdown("---")


def handle_dataset_source_flow() -> None:
    """Handle the flow based on selected dataset source"""
    source = st.session_state.get("dataset_source")
    logger.debug(f"Handling dataset source flow for: {source}")

    if source == "native":
        flow_native_datasets()
    elif source == "local":
        flow_upload_local_dataset()
    elif source == "online":
        flow_fetch_online_dataset()
    elif source == "memory":
        flow_load_from_memory()
    elif source == "combination":
        flow_combine_datasets()
    elif source == "transform":
        flow_transform_datasets()
    else:
        st.error("Invalid dataset source selected.")


def flow_native_datasets() -> None:
    """Handle native dataset selection and creation with enhanced UI"""
    # Import the new components
    try:
        from components.dataset_configuration import SpecializedConfigurationInterface
        from components.dataset_preview import DatasetPreviewComponent
        from components.dataset_selector import NativeDatasetSelector
        from utils.dataset_ui_components import LargeDatasetUIOptimization
        from utils.specialized_workflows import UserGuidanceSystem

        # Initialize components
        dataset_selector = NativeDatasetSelector()
        preview_component = DatasetPreviewComponent()
        config_interface = SpecializedConfigurationInterface()
        guidance_system = UserGuidanceSystem()
        ui_optimizer = LargeDatasetUIOptimization()

        # Render guidance toggle
        guidance_system.render_guidance_toggle()

        # Show guidance if enabled
        if st.session_state.user_guidance_state.get("guidance_enabled", True):
            guidance_system.render_contextual_help("dataset_selection")

            # Show onboarding tour for new users
            if not st.session_state.user_guidance_state.get("onboarding_completed", False):
                guidance_system.render_onboarding_tour()
            else:
                guidance_system.render_quick_start_guide()

        # Main dataset selection interface
        dataset_selector.render_dataset_selection_interface()

        # Show selected dataset details
        selected_dataset = dataset_selector.get_selected_dataset()
        selected_category = dataset_selector.get_selected_category()

        if selected_dataset and selected_category:
            st.success(f"✅ Selected: {selected_dataset} ({selected_category})")

            # Show configuration options
            with st.expander("⚙️ Configure Selected Dataset", expanded=True):
                config_result = config_interface.render_configuration_interface(selected_dataset, selected_category)

                if st.button("Save Configuration", key="save_selected_config"):
                    config_interface.save_configuration(selected_dataset, config_result)
                    st.success("Configuration saved!")

            # Show dataset preview
            if st.button("📋 Preview Dataset", key="preview_selected_dataset"):
                with st.spinner("Loading dataset preview..."):
                    metadata = dataset_selector.get_dataset_metadata(selected_dataset)
                    preview_component.render_dataset_preview(selected_dataset, metadata)

            # Create dataset button
            if st.button("🚀 Create Dataset for Evaluation", key="create_selected_dataset", type="primary"):
                config = dataset_selector.get_dataset_configuration(selected_dataset)
                if not config:
                    config = config_result if "config_result" in locals() else {}

                create_config = {"dataset_type": selected_dataset, **config}

                with st.spinner(f"Creating {selected_dataset} dataset..."):
                    success = create_dataset_via_api(f"{selected_dataset}_configured", "native", create_config)

                if success:
                    st.success(f"✅ Dataset '{selected_dataset}_configured' created successfully!")
                    guidance_system.update_user_progress("dataset_created")
                    st.rerun()
                else:
                    st.error("❌ Failed to create dataset")

        # Performance monitoring
        ui_optimizer.optimize_ui_responsiveness()

    except ImportError as e:
        logger.warning(f"Enhanced UI components not available, falling back to basic interface: {e}")

        # Fallback to original implementation
        st.subheader("Select Native Dataset")

        # Load dataset types if not already loaded
        if not st.session_state.api_dataset_types:
            with st.spinner("Loading dataset types..."):
                types = load_dataset_types_from_api()
                if not types:
                    st.error("❌ Failed to load dataset types")
                    return

        dataset_types = st.session_state.api_dataset_types
        type_names = [dt["name"] for dt in dataset_types]

        if not type_names:
            st.warning("No native dataset types available.")
            return

        # Dataset type selection
        selected_type = st.selectbox(
            "Select a native dataset type", ["-- Select --"] + type_names, key="native_dataset_select"
        )

        if selected_type != "-- Select --":
            # Find dataset type info
            type_info = next((dt for dt in dataset_types if dt["name"] == selected_type), None)
            if type_info:
                st.info(f"**{type_info['name']}**\n\n{type_info['description']}")

                # Configuration if required
                config = {}
                if type_info.get("config_required"):
                    st.write("**Configuration Required:**")
                    available_configs = type_info.get("available_configs", {})

                    for config_key, options in available_configs.items():
                        if options:
                            selected_option = st.selectbox(
                                f"Select {config_key}", options, key=f"native_config_{config_key}"
                            )
                            config[config_key] = selected_option

                # Dataset name
                dataset_name = st.text_input(
                    "Dataset Name*", value=f"{selected_type}_dataset", key="native_dataset_name"
                )

                # Create button
                if st.button("Create Dataset", key="create_native_dataset"):
                    if dataset_name:
                        create_config = {"dataset_type": selected_type, **config}

                        with st.spinner(f"Creating {selected_type} dataset..."):
                            success = create_dataset_via_api(dataset_name, "native", create_config)

                        if success:
                            st.success(f"✅ Dataset '{dataset_name}' created successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to create dataset")
                    else:
                        st.warning("Please enter a dataset name.")


def flow_upload_local_dataset() -> None:
    """Handle local file upload and dataset creation"""
    st.subheader("Upload Local Dataset File")

    uploaded_file = st.file_uploader(
        "Upload Dataset File", type=["csv", "tsv", "json", "yaml", "txt"], key="local_dataset_uploader"
    )

    if uploaded_file is not None:
        st.write("**File Information:**")
        st.write(f"- Name: {uploaded_file.name}")
        st.write(f"- Size: {uploaded_file.size} bytes")
        st.write(f"- Type: {uploaded_file.type}")

        # Read and encode file content
        file_content = uploaded_file.read()
        encoded_content = base64.b64encode(file_content).decode()
        file_type = uploaded_file.name.split(".")[-1].lower()

        # Dataset name
        dataset_name = st.text_input(
            "Dataset Name*", value=f"uploaded_{uploaded_file.name.split('.')[0]}", key="local_dataset_name"
        )

        # Simple field mapping (for now, assume 'value' field exists)
        st.write("**Field Mapping:**")
        st.info(
            "Automatic field mapping will be applied. The system will look for 'prompt', 'value', or 'text' fields."
        )

        field_mappings = {"auto": "value"}  # Simplified for API

        if st.button("Create Dataset from File", key="create_local_dataset"):
            if dataset_name:
                create_config = {
                    "file_content": encoded_content,
                    "file_type": file_type,
                    "field_mappings": field_mappings,
                }

                with st.spinner("Processing uploaded file..."):
                    success = create_dataset_via_api(dataset_name, "local", create_config)

                if success:
                    st.success(f"✅ Dataset '{dataset_name}' created from uploaded file!")
                    st.rerun()
                else:
                    st.error("❌ Failed to create dataset from file")
            else:
                st.warning("Please enter a dataset name.")


def flow_fetch_online_dataset() -> None:
    """Handle online dataset fetching"""
    st.subheader("Fetch Online Dataset")

    dataset_url = st.text_input("Dataset URL*", placeholder="https://example.com/dataset.csv", key="online_dataset_url")

    dataset_name = st.text_input("Dataset Name*", value="online_dataset", key="online_dataset_name")

    if dataset_url and dataset_name:
        if st.button("Fetch Dataset", key="fetch_online_dataset"):
            create_config = {"url": dataset_url}

            with st.spinner(f"Fetching dataset from {dataset_url}..."):
                success = create_dataset_via_api(dataset_name, "online", create_config)

            if success:
                st.success(f"✅ Dataset '{dataset_name}' fetched successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to fetch dataset")


def flow_load_from_memory() -> None:
    """Handle loading datasets from PyRIT memory"""
    st.subheader("Load from PyRIT Memory")

    if st.button("🔄 Refresh Memory Datasets", key="refresh_memory_datasets"):
        with st.spinner("Loading datasets from PyRIT memory..."):
            memory_datasets = load_memory_datasets_from_api()

        if memory_datasets:
            st.success(f"✅ Found {len(memory_datasets)} datasets in memory")

            # Display available datasets
            st.write("**Available Memory Datasets:**")
            for dataset in memory_datasets:
                with st.expander(f"📦 {dataset['dataset_name']} ({dataset['prompt_count']} prompts)"):
                    st.write(f"**Creator:** {dataset.get('created_by', 'Unknown')}")
                    if dataset.get("first_prompt_preview"):
                        st.write(f"**Preview:** {dataset['first_prompt_preview'][:100]}...")

                    if st.button(f"Load {dataset['dataset_name']}", key=f"load_memory_{dataset['dataset_name']}"):
                        # Create a dataset entry for the memory dataset
                        config = {"source_dataset_name": dataset["dataset_name"]}
                        success = create_dataset_via_api(dataset["dataset_name"], "memory", config)

                        if success:
                            st.success(f"✅ Loaded '{dataset['dataset_name']}' from memory!")
                            st.rerun()
        else:
            st.info("No datasets found in PyRIT memory.")


def flow_combine_datasets() -> None:
    """Handle dataset combination"""
    st.subheader("Combine Datasets")

    datasets = st.session_state.api_datasets
    if not datasets:
        st.warning("No datasets available to combine. Please create datasets first.")
        return

    dataset_names = list(datasets.keys())
    selected_datasets = st.multiselect("Select datasets to combine", dataset_names, key="combine_datasets_select")

    if len(selected_datasets) >= 2:
        combined_name = st.text_input("Combined Dataset Name*", value="combined_dataset", key="combined_dataset_name")

        if st.button("Combine Datasets", key="combine_datasets_button"):
            if combined_name:
                # Get dataset IDs
                dataset_ids = [datasets[name]["id"] for name in selected_datasets if name in datasets]

                create_config = {"dataset_ids": dataset_ids}

                with st.spinner("Combining datasets..."):
                    success = create_dataset_via_api(combined_name, "combination", create_config)

                if success:
                    st.success(f"✅ Combined dataset '{combined_name}' created!")
                    st.rerun()
                else:
                    st.error("❌ Failed to combine datasets")
            else:
                st.warning("Please enter a name for the combined dataset.")
    else:
        st.info("Select at least 2 datasets to combine.")


def flow_transform_datasets() -> None:
    """Handle dataset transformation"""
    st.subheader("Transform Dataset")

    datasets = st.session_state.api_datasets
    if not datasets:
        st.warning("No datasets available to transform. Please create datasets first.")
        return

    dataset_names = list(datasets.keys())
    selected_dataset = st.selectbox(
        "Select dataset to transform", ["-- Select --"] + dataset_names, key="transform_dataset_select"
    )

    if selected_dataset != "-- Select --":
        template = st.text_area(
            "Transformation Template*",
            placeholder="Enter your template here, use {{value}} to reference the original prompt",
            height=150,
            key="transform_template",
        )

        transformed_name = st.text_input(
            "Transformed Dataset Name*", value=f"{selected_dataset}_transformed", key="transformed_dataset_name"
        )

        if template and transformed_name:
            if st.button("Apply Transformation", key="apply_transformation"):
                dataset_id = datasets[selected_dataset]["id"]

                # Use the transform endpoint
                url = API_ENDPOINTS["dataset_transform"].format(dataset_id=dataset_id)
                payload = {"template": template, "template_type": "custom"}

                with st.spinner("Applying transformation..."):
                    data = api_request("POST", url, json=payload)

                if data:
                    st.success("✅ Transformed dataset created!")
                    # Update local state with transformed dataset
                    transformed_dataset = data.get("transformed_dataset", {})
                    st.session_state.api_datasets[transformed_name] = transformed_dataset
                    st.rerun()
                else:
                    st.error("❌ Failed to apply transformation")


def test_dataset_section() -> None:
    """Section for testing datasets with generators"""
    st.divider()
    st.subheader("🧪 Test Dataset")

    # Manual refresh option
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("Test your datasets with configured generators")
    with col2:
        if st.button("🔄 Refresh Generators", key="refresh_generators_test", help="Reload generators from API"):
            st.session_state["force_reload_generators"] = True
            auto_load_generators()
            st.rerun()

    # Get configured datasets
    datasets = st.session_state.api_datasets
    generators = get_generators()

    if not datasets:
        st.warning("📊 No datasets configured yet. Please create a dataset first.")
        return

    if not generators:
        st.warning("⚙️ No generators available for testing. Please configure a generator first.")

        # Debug information
        with st.expander("🔍 Debug Information", expanded=False):
            st.write("**Generator loading debug:**")
            st.write(f"- Cached generators: {st.session_state.get('api_generators_cache', 'Not set')}")
            st.write(f"- Session state keys: {list(st.session_state.keys())}")

            # Test API call directly
            if st.button("🔄 Test Generator API Call", key="debug_generators"):
                with st.spinner("Testing generator API..."):
                    try:
                        fresh_generators = get_generators(use_cache=False)
                        st.success(f"✅ API call successful: Found {len(fresh_generators)} generators")
                        if fresh_generators:
                            st.json(fresh_generators[0])  # Show first generator
                    except Exception as e:
                        st.error(f"❌ API call failed: {e}")
        return

    # Dataset selection for testing
    dataset_names = list(datasets.keys())
    selected_dataset_name = st.selectbox(
        "Select Dataset to Test*",
        ["-- Select Dataset --"] + dataset_names,
        key="test_dataset_select",
        help="Choose which dataset to test with a generator",
    )

    if selected_dataset_name == "-- Select Dataset --":
        st.info("👆 Please select a dataset to test.")
        return

    # Get the selected dataset
    selected_dataset = datasets[selected_dataset_name]
    st.write(f"**Selected Dataset:** {selected_dataset.get('name', 'Unknown')}")
    st.write(f"**Prompts:** {selected_dataset.get('prompt_count', 0)}")
    st.write(f"**Source:** {selected_dataset.get('source_type', 'Unknown')}")

    # Generator selection for testing
    generator_names = [gen["name"] for gen in generators]
    selected_generator_name = st.selectbox(
        "Select Generator for Testing*",
        ["-- Select Generator --"] + generator_names,
        key="test_generator_select",
        help="Choose which generator to test the dataset with",
    )

    if selected_generator_name == "-- Select Generator --":
        st.info("👆 Please select a generator for testing.")
        return

    # Get the selected generator
    selected_generator = next(gen for gen in generators if gen["name"] == selected_generator_name)
    st.write(
        f"**Selected Generator:** {selected_generator.get('name', 'Unknown')} "
        f"({selected_generator.get('type', 'Unknown')})"
    )

    # Test parameters
    col1, col2 = st.columns([1, 1])

    with col1:
        num_prompts = st.slider(
            "Number of prompts to test",
            min_value=1,
            max_value=min(10, selected_dataset.get("prompt_count", 1)),
            value=3,
            key="test_num_prompts",
            help="How many prompts from the dataset to test",
        )

    with col2:
        test_mode = st.radio(
            "Test Mode",
            ["Quick Test", "Detailed Test"],
            key="test_mode",
            help="Quick: basic functionality. Detailed: comprehensive analysis",
        )

    # Test button and results
    if st.button("🚀 Run Dataset Test", key="run_dataset_test", type="primary"):
        try:
            with st.spinner("Testing dataset with generator..."):
                success = run_orchestrator_dataset_test(selected_dataset, selected_generator, num_prompts, test_mode)

                if not success:
                    st.error("❌ Dataset test failed. Please check the configuration and try again.")
                    st.info("💡 **Common issues:**")
                    st.write(
                        "• **Generator not configured**: Go to 'Configure Generators' page to set up a generator first"
                    )
                    st.write("• **API connection issues**: Check that APISIX gateway and FastAPI service are running")
                    st.write("• **Authentication issues**: Ensure you're properly logged in with valid tokens")
        except Exception as e:
            st.error(f"❌ Test execution error: {str(e)}")
            logger.error(f"Dataset test error: {e}", exc_info=True)
            st.info(
                "💡 This error suggests there might be an issue with the response data format. "
                "Try running in 'Detailed Test' mode to see more information."
            )

    # Show available generators summary
    st.markdown("---")
    st.markdown("**📋 Testing Summary:**")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.write(f"**Available Datasets:** {len(datasets)}")
        for name, dataset in list(datasets.items())[:3]:  # Show first 3
            st.write(f"• {name} ({dataset.get('prompt_count', 0)} prompts)")
        if len(datasets) > 3:
            st.write(f"• ... and {len(datasets) - 3} more")

    with col2:
        st.write(f"**Available Generators:** {len(generators)}")
        for gen in generators[:3]:  # Show first 3
            name = gen.get("name", "Unknown")
            gen_type = gen.get("type", "Unknown")
            status = gen.get("status", "unknown")
            status_icon = "✅" if status == "ready" else "⚠️"
            st.write(f"• {name} ({gen_type}) {status_icon}")
        if len(generators) > 3:
            st.write(f"• ... and {len(generators) - 3} more")


def proceed_to_next_step() -> None:
    """Provide navigation to next step"""
    st.divider()
    st.header("🚀 Proceed to Next Step")
    st.markdown("*Continue to converter configuration once datasets are ready*")

    datasets = st.session_state.api_datasets

    # Check if at least one dataset is configured
    proceed_disabled = len(datasets) == 0

    if datasets:
        st.success(f"✅ {len(datasets)} dataset(s) configured and ready")
        # Show configured datasets
        for name, dataset in list(datasets.items())[:3]:  # Show first 3
            st.write(f"• **{name}** ({dataset.get('prompt_count', 0)} prompts)")
        if len(datasets) > 3:
            st.write(f"• ... and {len(datasets) - 3} more datasets")
    else:
        st.warning("⚠️ No datasets configured yet. Create at least one dataset to proceed.")

    if st.button(
        "Next: Configure Converters",
        disabled=proceed_disabled,
        type="primary",
        use_container_width=True,
        help="Proceed to configure converters for prompt transformation",
    ):
        logger.info("User proceeded to next step after configuring datasets.")

        # Save session progress
        session_update = {
            "ui_preferences": {"last_page": "Configure Datasets"},
            "workflow_state": {"current_step": "datasets_configured", "dataset_count": len(datasets)},
            "temporary_data": {"last_dataset_configured": list(datasets.keys())[-1] if datasets else None},
        }
        api_request("PUT", API_ENDPOINTS["sessions_update"], json=session_update)

        st.switch_page("pages/3_Configure_Converters.py")


# --- Run Main Function ---
if __name__ == "__main__":
    main()
