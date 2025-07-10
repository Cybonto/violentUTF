import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Load environment variables from .env file
from dotenv import load_dotenv
from plotly.subplots import make_subplots

# Import utilities
from utils.auth_utils import handle_authentication_and_sidebar
from utils.jwt_manager import jwt_manager
from utils.logging import get_logger

load_dotenv()

logger = get_logger(__name__)

# API Configuration - MUST go through APISIX Gateway
_raw_api_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = _raw_api_url.rstrip("/api").rstrip("/")
if not API_BASE_URL:
    API_BASE_URL = "http://localhost:9080"

API_ENDPOINTS = {
    # Authentication endpoints
    "auth_token_info": f"{API_BASE_URL}/api/v1/auth/token/info",
    # Orchestrator endpoints for actual results
    "orchestrators": f"{API_BASE_URL}/api/v1/orchestrators",
    "orchestrator_executions": f"{API_BASE_URL}/api/v1/orchestrators/executions",  # List all executions
    "execution_results": f"{API_BASE_URL}/api/v1/orchestrators/executions/{{execution_id}}/results",
    # Scorer endpoints
    "scorers": f"{API_BASE_URL}/api/v1/scorers",
    "scorer_test": f"{API_BASE_URL}/api/v1/scorers/{{scorer_id}}/test",
    "scorer_analytics": f"{API_BASE_URL}/api/v1/scorers/{{scorer_id}}/analytics",
    # Generator and dataset endpoints
    "generators": f"{API_BASE_URL}/api/v1/generators",
    "datasets": f"{API_BASE_URL}/api/v1/datasets",
}

# Score type mappings from API analysis
SCORE_TYPE_MAP = {"true_false": "Boolean", "float_scale": "Scale", "str": "Category"}

# Severity mapping for different scorer types
SEVERITY_MAP = {
    # Boolean scorers - violation = high severity
    "true_false": lambda val: "high" if val else "low",
    # Scale scorers - map float to severity
    "float_scale": lambda val: (
        (
            "critical"
            if float(val) >= 0.8
            else (
                "high"
                if float(val) >= 0.6
                else "medium" if float(val) >= 0.4 else "low" if float(val) >= 0.2 else "minimal"
            )
        )
        if val is not None and str(val).replace(".", "").replace("-", "").isdigit()
        else "unknown"
    ),
    # Category scorers - map categories to severity
    "str": lambda val: {
        "prompt_injection": "critical",
        "jailbreak": "critical",
        "data_extraction": "high",
        "hate_speech": "high",
        "violence": "high",
        "self_harm": "critical",
        "sexual_content": "medium",
        "misinformation": "medium",
        "unauthorized_access": "critical",
        "privilege_escalation": "critical",
        "system_manipulation": "high",
        "role_play_manipulation": "medium",
        "compliant": "minimal",
        "safe": "minimal",
    }.get(str(val).lower() if val else "", "unknown"),
}

# Color schemes
SEVERITY_COLORS = {
    "critical": "#8B0000",  # Dark red
    "high": "#DC143C",  # Crimson
    "medium": "#FF8C00",  # Dark orange
    "low": "#FFD700",  # Gold
    "minimal": "#32CD32",  # Lime green
    "unknown": "#808080",  # Gray
}

# --- API Helper Functions ---


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    try:
        # Use jwt_manager for automatic token refresh
        token = jwt_manager.get_valid_token()

        # Fallback token creation if needed
        if not token and st.session_state.get("access_token"):
            token = create_compatible_api_token()

        if not token:
            return {}

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

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


def api_request(method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Make an authenticated API request through APISIX Gateway"""
    headers = get_auth_headers()
    if not headers.get("Authorization"):
        logger.warning("No authentication token available for API request")
        return None

    try:
        logger.debug(f"Making {method} request to {url} through APISIX Gateway")
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"API Error {response.status_code}: {url} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception to {url}: {e}")
        return None


def create_compatible_api_token():
    """Create a FastAPI-compatible token using JWT manager"""
    try:
        from utils.user_context import get_user_context_for_token

        # Get consistent user context regardless of authentication source
        user_context = get_user_context_for_token()
        logger.info(f"Creating API token for consistent user: {user_context['preferred_username']}")

        # Create token with consistent user context
        api_token = jwt_manager.create_token(user_context)

        if api_token:
            logger.info("Successfully created API token using JWT manager")
            st.session_state["api_token"] = api_token
            return api_token
        else:
            st.error("🚨 Security Error: JWT secret key not configured.")
            logger.error("Failed to create API token - JWT secret key not available")
            return None

    except Exception as e:
        st.error("❌ Failed to generate API token.")
        logger.error(f"Token creation failed: {e}")
        return None


# --- Data Loading Functions ---


@st.cache_data(ttl=60)  # 1-minute cache for real-time updates
def load_orchestrator_executions_with_results(days_back: int = 30) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load orchestrator executions with their results from API - same approach as Dashboard_4"""
    try:
        # Calculate time range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # First get all orchestrators
        orchestrators_response = api_request("GET", API_ENDPOINTS["orchestrators"])
        if not orchestrators_response:
            return [], []

        # API returns list directly, not wrapped in 'orchestrators' key
        orchestrators = (
            orchestrators_response
            if isinstance(orchestrators_response, list)
            else orchestrators_response.get("orchestrators", [])
        )
        all_executions = []
        all_results = []

        # For each orchestrator, get its executions AND their results
        for orchestrator in orchestrators:
            orch_id = orchestrator.get("orchestrator_id")  # Use correct field name
            if not orch_id:
                continue

            # Get executions for this orchestrator
            exec_url = f"{API_BASE_URL}/api/v1/orchestrators/{orch_id}/executions"
            exec_response = api_request("GET", exec_url)

            if exec_response and "executions" in exec_response:
                for execution in exec_response["executions"]:
                    # Add orchestrator info to execution
                    execution["orchestrator_name"] = orchestrator.get("name", "")
                    execution["orchestrator_type"] = orchestrator.get("type", "")
                    all_executions.append(execution)

                    # Load results for this execution immediately (Dashboard_4 approach)
                    # Only try to load results for completed executions
                    execution_id = execution.get("id")
                    execution_status = execution.get("status", "")

                    if not execution_id or execution_status != "completed":
                        continue

                    url = API_ENDPOINTS["execution_results"].format(execution_id=execution_id)
                    details = api_request("GET", url)

                    # Extract scores directly from the response
                    if details and "scores" in details:
                        for score in details["scores"]:
                            try:
                                # Parse metadata if it's a JSON string
                                metadata = score.get("score_metadata", "{}")
                                if isinstance(metadata, str):
                                    metadata = json.loads(metadata)

                                # Create unified result object
                                result = {
                                    "execution_id": execution_id,
                                    "orchestrator_name": execution.get("orchestrator_name", "Unknown"),
                                    "timestamp": score.get("timestamp", execution.get("created_at")),
                                    "score_value": score.get("score_value"),
                                    "score_type": score.get("score_type", "unknown"),
                                    "score_category": score.get("score_category", "unknown"),
                                    "score_rationale": score.get("score_rationale", ""),
                                    "scorer_type": metadata.get("scorer_type", "Unknown"),
                                    "scorer_name": metadata.get("scorer_name", "Unknown"),
                                    "generator_name": metadata.get("generator_name", "Unknown"),
                                    "generator_type": metadata.get("generator_type", "Unknown"),
                                    "dataset_name": metadata.get("dataset_name", "Unknown"),
                                    "test_mode": metadata.get("test_mode", "unknown"),
                                    "batch_index": metadata.get("batch_index", 0),
                                    "total_batches": metadata.get("total_batches", 1),
                                }

                                # Calculate severity
                                score_type = result["score_type"]
                                if score_type in SEVERITY_MAP:
                                    result["severity"] = SEVERITY_MAP[score_type](result["score_value"])
                                else:
                                    result["severity"] = "unknown"

                                all_results.append(result)

                            except Exception as e:
                                logger.error(f"Failed to parse score result: {e}")
                                continue

        # Filter executions by time range
        filtered_executions = []

        for execution in all_executions:
            created_at_str = execution.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if start_date.date() <= created_at.date() <= end_date.date():
                        filtered_executions.append(execution)
                except Exception as e:
                    logger.error(f"Failed to parse date {created_at_str}: {e}")
            else:
                filtered_executions.append(execution)  # Include executions without timestamps

        # Filter results by time range too
        filtered_results = []
        for result in all_results:
            timestamp_str = result.get("timestamp", "")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if start_date.date() <= timestamp.date() <= end_date.date():
                        filtered_results.append(result)
                except Exception as e:
                    logger.error(f"Failed to parse result timestamp {timestamp_str}: {e}")

        return filtered_executions, filtered_results
    except Exception as e:
        logger.error(f"Failed to load orchestrator executions: {e}")
        return [], []


@st.cache_data(ttl=60)
def load_execution_results(execution_id: str) -> Dict[str, Any]:
    """Load detailed results for a specific execution"""
    try:
        url = API_ENDPOINTS["execution_results"].format(execution_id=execution_id)
        response = api_request("GET", url)
        return response or {}
    except Exception as e:
        logger.error(f"Failed to load execution results: {e}")
        return {}


def parse_scorer_results(executions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse scorer results from orchestrator executions"""
    all_results = []

    for execution in executions:
        execution_id = execution.get("id")
        if not execution_id:
            continue

        # Load detailed results
        details = load_execution_results(execution_id)
        if not details:
            continue

        # Extract scorer results directly from the response
        scores = details.get("scores", [])

        for score in scores:
            try:
                # Parse metadata if it's a JSON string
                metadata = score.get("score_metadata", "{}")
                if isinstance(metadata, str):
                    metadata = json.loads(metadata)

                # Create unified result object
                result = {
                    "execution_id": execution_id,
                    "orchestrator_name": execution.get("name", "Unknown"),
                    "timestamp": score.get("timestamp", execution.get("created_at")),
                    "score_value": score.get("score_value"),
                    "score_type": score.get("score_type", "unknown"),
                    "score_category": score.get("score_category", "unknown"),
                    "score_rationale": score.get("score_rationale", ""),
                    "scorer_type": metadata.get("scorer_type", "Unknown"),
                    "scorer_name": metadata.get("scorer_name", "Unknown"),
                    "generator_name": metadata.get("generator_name", "Unknown"),
                    "generator_type": metadata.get("generator_type", "Unknown"),
                    "dataset_name": metadata.get("dataset_name", "Unknown"),
                    "test_mode": metadata.get("test_mode", "unknown"),
                    "batch_index": metadata.get("batch_index", 0),
                    "total_batches": metadata.get("total_batches", 1),
                }

                # Calculate severity
                score_type = result["score_type"]
                if score_type in SEVERITY_MAP:
                    result["severity"] = SEVERITY_MAP[score_type](result["score_value"])
                else:
                    result["severity"] = "unknown"

                all_results.append(result)

            except Exception as e:
                logger.error(f"Failed to parse score result: {e}")
                continue

    return all_results


# --- Dynamic Filtering Functions ---


def initialize_filter_state():
    """Initialize filter state in session state"""
    if "filter_state" not in st.session_state:
        st.session_state.filter_state = {
            "time": {"preset": "all_time", "custom_start": None, "custom_end": None},
            "entities": {"executions": [], "datasets": [], "generators": [], "scorers": []},
            "results": {
                "severity": [],
                "score_type": "all",
                "violation_only": False,
                "score_range": {"min": 0.0, "max": 1.0},
            },
            "comparison_mode": False,
            "active": False,
        }


def apply_time_filter(
    results: List[Dict[str, Any]],
    preset: str,
    custom_start: Optional[datetime] = None,
    custom_end: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Apply time-based filtering to results"""
    if preset == "all_time":
        return results

    now = datetime.now()

    # Define time ranges for presets
    time_ranges = {
        "last_hour": now - timedelta(hours=1),
        "last_4h": now - timedelta(hours=4),
        "last_24h": now - timedelta(hours=24),
        "last_7d": now - timedelta(days=7),
        "last_30d": now - timedelta(days=30),
    }

    if preset == "custom":
        if not custom_start or not custom_end:
            return results
        start_time = custom_start
        end_time = custom_end
    else:
        start_time = time_ranges.get(preset, now - timedelta(days=30))
        end_time = now

    # Filter results by timestamp
    filtered = []
    for r in results:
        timestamp = r.get("timestamp")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                if isinstance(timestamp, datetime) and start_time <= timestamp <= end_time:
                    filtered.append(r)
            except (ValueError, AttributeError) as e:
                logger.error(f"Failed to parse timestamp in apply_time_filter: {timestamp}, error: {e}")
                continue

    return filtered


def apply_entity_filters(
    results: List[Dict[str, Any]], executions: List[str], datasets: List[str], generators: List[str], scorers: List[str]
) -> List[Dict[str, Any]]:
    """Apply entity-based filters"""
    filtered = results.copy()

    if executions:
        filtered = [r for r in filtered if r.get("execution_id") in executions or r.get("execution_name") in executions]

    if datasets:
        filtered = [r for r in filtered if r.get("dataset_name") in datasets]

    if generators:
        filtered = [r for r in filtered if r.get("generator_name") in generators]

    if scorers:
        filtered = [r for r in filtered if r.get("scorer_name") in scorers]

    return filtered


def apply_result_filters(
    results: List[Dict[str, Any]],
    severity: List[str],
    score_type: str,
    violation_only: bool,
    score_range: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Apply result-based filters"""
    filtered = results.copy()

    if severity:
        filtered = [r for r in filtered if r.get("severity") in severity]

    if score_type != "all":
        filtered = [r for r in filtered if r.get("score_type") == score_type]

    if violation_only:
        violation_filtered = []
        for r in filtered:
            score_type = r.get("score_type")
            score_value = r.get("score_value")
            severity = r.get("severity")

            if score_type == "true_false" and score_value is True:
                violation_filtered.append(r)
            elif score_type == "float_scale" and score_value is not None:
                try:
                    if float(score_value) >= 0.6:
                        violation_filtered.append(r)
                except (TypeError, ValueError):
                    # Skip non-numeric scores
                    pass
            elif severity in ["high", "critical"]:
                violation_filtered.append(r)
        filtered = violation_filtered

    # Apply score range filter for float scores
    min_score = score_range.get("min", 0.0)
    max_score = score_range.get("max", 1.0)
    if min_score > 0.0 or max_score < 1.0:
        range_filtered = []
        for r in filtered:
            if r.get("score_type") == "float_scale":
                score_val = r.get("score_value", 0)
                # Ensure score_val is numeric
                try:
                    score_val = float(score_val)
                    if min_score <= score_val <= max_score:
                        range_filtered.append(r)
                except (TypeError, ValueError):
                    # Skip non-numeric scores
                    pass
            else:
                # Include non-float scores
                range_filtered.append(r)
        filtered = range_filtered

    return filtered


def get_unique_entities(results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Extract unique entity values from results for filter options"""
    entities = {"executions": [], "datasets": [], "generators": [], "scorers": []}

    # Collect unique values
    exec_set = set()
    dataset_set = set()
    generator_set = set()
    scorer_set = set()

    for r in results:
        # Collect both ID and name for executions
        exec_id = r.get("execution_id")
        if exec_id:
            exec_set.add(exec_id)
        exec_name = r.get("execution_name")
        if exec_name:
            exec_set.add(exec_name)

        dataset_name = r.get("dataset_name")
        if dataset_name:
            dataset_set.add(dataset_name)

        generator_name = r.get("generator_name")
        if generator_name:
            generator_set.add(generator_name)

        scorer_name = r.get("scorer_name")
        if scorer_name:
            scorer_set.add(scorer_name)

    entities["executions"] = sorted(list(exec_set))
    entities["datasets"] = sorted(list(dataset_set))
    entities["generators"] = sorted(list(generator_set))
    entities["scorers"] = sorted(list(scorer_set))

    return entities


def count_active_filters() -> int:
    """Count number of active filters"""
    if "filter_state" not in st.session_state:
        return 0

    count = 0
    fs = st.session_state.filter_state

    # Time filter
    if fs.get("time", {}).get("preset", "all_time") != "all_time":
        count += 1

    # Entity filters
    entities = fs.get("entities", {})
    for entity_list in entities.values():
        if entity_list:
            count += 1

    # Result filters
    results = fs.get("results", {})
    if results.get("severity", []):
        count += 1
    if results.get("score_type", "all") != "all":
        count += 1
    if results.get("violation_only", False):
        count += 1
    score_range = fs.get("results", {}).get("score_range", {})
    if score_range.get("min", 0.0) > 0.0 or score_range.get("max", 1.0) < 1.0:
        count += 1

    return count


def apply_all_filters(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply all active filters to results"""
    if "filter_state" not in st.session_state or not st.session_state.filter_state.get("active", False):
        return results

    fs = st.session_state.filter_state
    filtered = results.copy()

    # Apply time filter
    time_config = fs.get("time", {})
    filtered = apply_time_filter(
        filtered, time_config.get("preset", "all_time"), time_config.get("custom_start"), time_config.get("custom_end")
    )

    # Apply entity filters
    entities_config = fs.get("entities", {})
    filtered = apply_entity_filters(
        filtered,
        entities_config.get("executions", []),
        entities_config.get("datasets", []),
        entities_config.get("generators", []),
        entities_config.get("scorers", []),
    )

    # Apply result filters
    results_config = fs.get("results", {})
    filtered = apply_result_filters(
        filtered,
        results_config.get("severity", []),
        results_config.get("score_type", "all"),
        results_config.get("violation_only", False),
        results_config.get("score_range", {"min": 0.0, "max": 1.0}),
    )

    return filtered


def render_dynamic_filters(results: List[Dict[str, Any]], key_prefix: str = "main"):
    """Render the complete dynamic filtering UI"""
    initialize_filter_state()

    # Get unique entities for filter options
    entities = get_unique_entities(results)

    # Filter header with count
    active_filter_count = count_active_filters()
    header_text = "🔍 Filters"
    if active_filter_count > 0:
        header_text += f" ({active_filter_count} active)"

    with st.expander(header_text, expanded=active_filter_count > 0):
        # Quick actions
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            if st.button("🔄 Apply All", key=f"{key_prefix}_apply_all"):
                st.session_state.filter_state["active"] = True
                st.rerun()

        with col2:
            if st.button("🗑️ Clear All", key=f"{key_prefix}_clear_all"):
                # Reset filter state
                st.session_state.filter_state = {
                    "time": {"preset": "all_time", "custom_start": None, "custom_end": None},
                    "entities": {"executions": [], "datasets": [], "generators": [], "scorers": []},
                    "results": {
                        "severity": [],
                        "score_type": "all",
                        "violation_only": False,
                        "score_range": {"min": 0.0, "max": 1.0},
                    },
                    "comparison_mode": False,
                    "active": False,
                }
                st.rerun()

        with col3:
            st.session_state.filter_state["comparison_mode"] = st.checkbox(
                "📊 Enable Comparison Mode",
                value=st.session_state.filter_state["comparison_mode"],
                key=f"{key_prefix}_comparison_mode",
                help="Compare filtered metrics against baseline (all data)",
            )

        # Time filters section
        st.markdown("### ⏱️ Time Range")
        time_col1, time_col2 = st.columns([1, 2])

        with time_col1:
            time_preset = st.selectbox(
                "Quick Select",
                [
                    "All Time",
                    "Last Hour",
                    "Last 4 Hours",
                    "Last 24 Hours",
                    "Last 7 Days",
                    "Last 30 Days",
                    "Custom Range",
                ],
                index=(
                    ["all_time", "last_hour", "last_4h", "last_24h", "last_7d", "last_30d", "custom"].index(
                        st.session_state.filter_state.get("time", {}).get("preset", "all_time")
                    )
                    if st.session_state.filter_state.get("time", {}).get("preset", "all_time")
                    in ["all_time", "last_hour", "last_4h", "last_24h", "last_7d", "last_30d", "custom"]
                    else 0
                ),
                key=f"{key_prefix}_time_preset",
            )

            # Map display text back to internal values
            preset_map = {
                "All Time": "all_time",
                "Last Hour": "last_hour",
                "Last 4 Hours": "last_4h",
                "Last 24 Hours": "last_24h",
                "Last 7 Days": "last_7d",
                "Last 30 Days": "last_30d",
                "Custom Range": "custom",
            }
            if "time" not in st.session_state.filter_state:
                st.session_state.filter_state["time"] = {}
            st.session_state.filter_state["time"]["preset"] = preset_map.get(time_preset, "all_time")

        with time_col2:
            if time_preset == "Custom Range":
                date_col1, date_col2 = st.columns(2)
                with date_col1:
                    start_date = st.date_input(
                        "Start Date",
                        value=st.session_state.filter_state.get("time", {}).get("custom_start")
                        or datetime.now() - timedelta(days=7),
                        key=f"{key_prefix}_start_date",
                    )
                    if "time" not in st.session_state.filter_state:
                        st.session_state.filter_state["time"] = {}
                    st.session_state.filter_state["time"]["custom_start"] = datetime.combine(
                        start_date, datetime.min.time()
                    )

                with date_col2:
                    end_date = st.date_input(
                        "End Date",
                        value=st.session_state.filter_state.get("time", {}).get("custom_end") or datetime.now(),
                        key=f"{key_prefix}_end_date",
                    )
                    if "time" not in st.session_state.filter_state:
                        st.session_state.filter_state["time"] = {}
                    st.session_state.filter_state["time"]["custom_end"] = datetime.combine(
                        end_date, datetime.max.time()
                    )

        # Entity filters section
        st.markdown("### 🎯 Entity Filters")
        entity_col1, entity_col2 = st.columns(2)

        with entity_col1:
            # Executions filter
            if "entities" not in st.session_state.filter_state:
                st.session_state.filter_state["entities"] = {}
            st.session_state.filter_state["entities"]["executions"] = st.multiselect(
                "Executions",
                options=entities.get("executions", []),
                default=st.session_state.filter_state.get("entities", {}).get("executions", []),
                key=f"{key_prefix}_execution_filter",
                help="Filter by specific test executions",
            )

            # Generators filter
            if "entities" not in st.session_state.filter_state:
                st.session_state.filter_state["entities"] = {}
            st.session_state.filter_state["entities"]["generators"] = st.multiselect(
                "Generators",
                options=entities.get("generators", []),
                default=st.session_state.filter_state.get("entities", {}).get("generators", []),
                key=f"{key_prefix}_generator_filter",
                help="Filter by AI model/generator",
            )

        with entity_col2:
            # Datasets filter
            if "entities" not in st.session_state.filter_state:
                st.session_state.filter_state["entities"] = {}
            st.session_state.filter_state["entities"]["datasets"] = st.multiselect(
                "Datasets",
                options=entities.get("datasets", []),
                default=st.session_state.filter_state.get("entities", {}).get("datasets", []),
                key=f"{key_prefix}_dataset_filter",
                help="Filter by dataset used",
            )

            # Scorers filter
            if "entities" not in st.session_state.filter_state:
                st.session_state.filter_state["entities"] = {}
            st.session_state.filter_state["entities"]["scorers"] = st.multiselect(
                "Scorers",
                options=entities.get("scorers", []),
                default=st.session_state.filter_state.get("entities", {}).get("scorers", []),
                key=f"{key_prefix}_scorer_filter",
                help="Filter by security scorer",
            )

        # Result filters section
        st.markdown("### 📊 Result Filters")
        result_col1, result_col2, result_col3 = st.columns(3)

        with result_col1:
            if "results" not in st.session_state.filter_state:
                st.session_state.filter_state["results"] = {}
            st.session_state.filter_state["results"]["severity"] = st.multiselect(
                "Severity Levels",
                options=["critical", "high", "medium", "low", "minimal"],
                default=st.session_state.filter_state.get("results", {}).get("severity", []),
                key=f"{key_prefix}_severity_filter",
                help="Filter by severity level",
            )

        with result_col2:
            score_types = ["All Types", "True/False", "Float Scale", "String"]
            score_type_map = {
                "All Types": "all",
                "True/False": "true_false",
                "Float Scale": "float_scale",
                "String": "str",
            }

            display_type = st.selectbox(
                "Score Type",
                options=score_types,
                index=(
                    0
                    if st.session_state.filter_state.get("results", {}).get("score_type", "all") == "all"
                    else (
                        list(score_type_map.values()).index(
                            st.session_state.filter_state.get("results", {}).get("score_type", "all")
                        )
                        if st.session_state.filter_state.get("results", {}).get("score_type", "all")
                        in score_type_map.values()
                        else 0
                    )
                ),
                key=f"{key_prefix}_score_type_filter",
            )
            if "results" not in st.session_state.filter_state:
                st.session_state.filter_state["results"] = {}
            st.session_state.filter_state["results"]["score_type"] = score_type_map.get(display_type, "all")

        with result_col3:
            if "results" not in st.session_state.filter_state:
                st.session_state.filter_state["results"] = {}
            st.session_state.filter_state["results"]["violation_only"] = st.checkbox(
                "Violations Only",
                value=st.session_state.filter_state.get("results", {}).get("violation_only", False),
                key=f"{key_prefix}_violation_only",
                help="Show only results that indicate violations",
            )

        # Score range filter (only for float scores)
        if st.session_state.filter_state.get("results", {}).get("score_type", "all") in ["all", "float_scale"]:
            score_range = st.slider(
                "Score Range (for float scores)",
                min_value=0.0,
                max_value=1.0,
                value=(
                    st.session_state.filter_state.get("results", {}).get("score_range", {}).get("min", 0.0),
                    st.session_state.filter_state.get("results", {}).get("score_range", {}).get("max", 1.0),
                ),
                step=0.1,
                key=f"{key_prefix}_score_range",
            )
            if "results" not in st.session_state.filter_state:
                st.session_state.filter_state["results"] = {}
            if "score_range" not in st.session_state.filter_state["results"]:
                st.session_state.filter_state["results"]["score_range"] = {}
            st.session_state.filter_state["results"]["score_range"]["min"] = score_range[0]
            st.session_state.filter_state["results"]["score_range"]["max"] = score_range[1]

        # Show quick presets
        st.markdown("### 🚀 Quick Presets")
        preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)

        with preset_col1:
            if st.button("🔴 Critical Only", key=f"{key_prefix}_preset_critical"):
                if "results" not in st.session_state.filter_state:
                    st.session_state.filter_state["results"] = {}
                st.session_state.filter_state["results"]["severity"] = ["critical"]
                st.session_state.filter_state["active"] = True
                st.rerun()

        with preset_col2:
            if st.button("⚠️ High Risk", key=f"{key_prefix}_preset_high_risk"):
                if "results" not in st.session_state.filter_state:
                    st.session_state.filter_state["results"] = {}
                st.session_state.filter_state["results"]["severity"] = ["critical", "high"]
                st.session_state.filter_state["active"] = True
                st.rerun()

        with preset_col3:
            if st.button("🕒 Recent Activity", key=f"{key_prefix}_preset_recent"):
                if "time" not in st.session_state.filter_state:
                    st.session_state.filter_state["time"] = {}
                st.session_state.filter_state["time"]["preset"] = "last_24h"
                st.session_state.filter_state["active"] = True
                st.rerun()

        with preset_col4:
            if st.button("🚨 Violations", key=f"{key_prefix}_preset_violations"):
                if "results" not in st.session_state.filter_state:
                    st.session_state.filter_state["results"] = {}
                st.session_state.filter_state["results"]["violation_only"] = True
                st.session_state.filter_state["active"] = True
                st.rerun()


def render_filter_summary(results: List[Dict[str, Any]], filtered_results: List[Dict[str, Any]]):
    """Show summary of filter impact"""
    if st.session_state.get("filter_state", {}).get("active", False):
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            reduction_pct = ((len(results) - len(filtered_results)) / len(results) * 100) if results else 0
            st.info(
                f"📊 Showing **{len(filtered_results):,}** of **{len(results):,}** results ({reduction_pct:.1f}% filtered)"
            )

        with col2:
            active_count = count_active_filters()
            if active_count > 0:
                st.success(f"✅ {active_count} filter{'s' if active_count > 1 else ''} active")

        with col3:
            if st.button("❌ Clear Filters", key="clear_filters_summary"):
                st.session_state.filter_state["active"] = False
                st.rerun()


# --- Metrics Calculation Functions ---


def calculate_hierarchical_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate hierarchical metrics accounting for batch operations.

    This function properly counts test runs, batches, and scores while
    handling edge cases like missing batch metadata.
    """
    if not results:
        return {
            "test_runs": 0,
            "total_batches": 0,
            "total_scores": 0,
            "completion_rate": 0.0,
            "avg_batches_per_run": 0.0,
            "avg_scores_per_batch": 0.0,
            "execution_details": {},
            "incomplete_executions": [],
        }

    # Group results by execution_id
    execution_groups = defaultdict(list)
    for result in results:
        exec_id = result.get("execution_id")
        if exec_id:
            execution_groups[exec_id].append(result)

    # Calculate metrics for each execution
    execution_details = {}
    total_batches = 0
    completed_executions = 0
    incomplete_executions = []

    for exec_id, exec_results in execution_groups.items():
        # Identify unique batches in this execution
        batch_info = {}
        execution_name = (
            exec_results[0].get("execution_name", "Unknown") if exec_results and len(exec_results) > 0 else "Unknown"
        )

        for r in exec_results:
            # Handle missing batch metadata gracefully
            batch_idx = r.get("batch_index", 0)
            total_b = r.get("total_batches", 1)
            batch_key = (batch_idx, total_b)

            if batch_key not in batch_info:
                batch_info[batch_key] = {
                    "scores": 0,
                    "first_timestamp": r.get("timestamp"),
                    "last_timestamp": r.get("timestamp"),
                    "scorers": set(),
                    "generators": set(),
                }

            batch_info[batch_key]["scores"] += 1
            batch_info[batch_key]["scorers"].add(r.get("scorer_name", "Unknown"))
            batch_info[batch_key]["generators"].add(r.get("generator_name", "Unknown"))

            # Update timestamps
            if r.get("timestamp"):
                current_ts = r["timestamp"]
                if isinstance(current_ts, str):
                    try:
                        current_ts = datetime.fromisoformat(current_ts.replace("Z", "+00:00"))
                    except (ValueError, AttributeError) as e:
                        logger.error(f"Failed to parse timestamp: {current_ts}, error: {e}")
                        continue

                first_ts = batch_info[batch_key].get("first_timestamp")
                if first_ts is None:
                    batch_info[batch_key]["first_timestamp"] = current_ts
                elif isinstance(first_ts, str):
                    try:
                        batch_info[batch_key]["first_timestamp"] = datetime.fromisoformat(
                            first_ts.replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError) as e:
                        logger.error(f"Failed to parse first_timestamp: {first_ts}, error: {e}")
                        batch_info[batch_key]["first_timestamp"] = current_ts

                # Safe comparison with first_timestamp
                first_ts_value = batch_info[batch_key].get("first_timestamp")
                if first_ts_value and isinstance(first_ts_value, datetime) and current_ts < first_ts_value:
                    batch_info[batch_key]["first_timestamp"] = current_ts

                # Also convert last_timestamp if it's a string
                last_ts = batch_info[batch_key].get("last_timestamp")
                if isinstance(last_ts, str):
                    try:
                        batch_info[batch_key]["last_timestamp"] = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                    except (ValueError, AttributeError) as e:
                        logger.error(f"Failed to parse last_timestamp: {last_ts}, error: {e}")
                        batch_info[batch_key]["last_timestamp"] = current_ts

                # Safe comparison with last_timestamp
                last_ts_value = batch_info[batch_key].get("last_timestamp")
                if last_ts_value and isinstance(last_ts_value, datetime) and current_ts > last_ts_value:
                    batch_info[batch_key]["last_timestamp"] = current_ts

        # Calculate execution-level metrics
        unique_batches = len(batch_info)
        # Safely extract expected batches
        batch_totals = [
            b[1] for b in batch_info.keys() if isinstance(b, tuple) and len(b) > 1 and isinstance(b[1], int)
        ]
        expected_batches = max(batch_totals, default=1)
        # Safely extract actual batch indices
        actual_batch_indices = set([b[0] for b in batch_info.keys() if isinstance(b, tuple) and len(b) > 0])
        completed = len(actual_batch_indices) == expected_batches

        # Calculate execution duration if timestamps available
        all_timestamps = []
        for bi in batch_info.values():
            first_ts = bi.get("first_timestamp")
            if first_ts and isinstance(first_ts, datetime):
                all_timestamps.append(first_ts)
            last_ts = bi.get("last_timestamp")
            if last_ts and isinstance(last_ts, datetime):
                all_timestamps.append(last_ts)

        execution_duration = None
        if all_timestamps:
            execution_duration = max(all_timestamps) - min(all_timestamps)

        execution_details[exec_id] = {
            "name": execution_name,
            "unique_batches": unique_batches,
            "expected_batches": expected_batches,
            "completed": completed,
            "completion_percentage": (
                (len(actual_batch_indices) / expected_batches * 100) if expected_batches > 0 else 0
            ),
            "batch_info": {
                str(k): {"scores": v["scores"], "scorers": list(v["scorers"]), "generators": list(v["generators"])}
                for k, v in batch_info.items()
            },
            "total_scores": len(exec_results),
            "execution_duration": str(execution_duration) if execution_duration else None,
        }

        total_batches += unique_batches
        if completed:
            completed_executions += 1
        else:
            incomplete_executions.append(
                {
                    "execution_id": exec_id,
                    "name": execution_name,
                    "completed_batches": len(actual_batch_indices),
                    "expected_batches": expected_batches,
                    "completion_percentage": execution_details[exec_id]["completion_percentage"],
                }
            )

    # Calculate aggregate metrics
    test_runs = len(execution_groups)
    total_scores = len(results)
    completion_rate = (completed_executions / test_runs * 100) if test_runs > 0 else 0.0
    avg_batches_per_run = total_batches / test_runs if test_runs > 0 else 0.0
    avg_scores_per_batch = total_scores / total_batches if total_batches > 0 else 0.0

    # Calculate throughput if we have timing data
    total_duration_seconds = 0
    executions_with_duration = 0
    for details in execution_details.values():
        if details.get("execution_duration"):
            try:
                # Parse duration string back to timedelta
                duration_str = details["execution_duration"]
                if ":" in duration_str:
                    parts = duration_str.split(":")
                    hours = int(parts[0]) if len(parts) > 2 else 0
                    minutes = int(parts[1] if len(parts) > 2 else parts[0])
                    seconds = float(parts[2] if len(parts) > 2 else parts[1])
                    total_seconds = hours * 3600 + minutes * 60 + seconds
                    total_duration_seconds += total_seconds
                    executions_with_duration += 1
            except:
                pass

    avg_throughput = None
    if total_duration_seconds > 0 and executions_with_duration > 0:
        avg_duration_per_execution = total_duration_seconds / executions_with_duration
        # Scores per minute
        avg_throughput = (
            (total_scores / executions_with_duration) / (avg_duration_per_execution / 60)
            if avg_duration_per_execution > 0
            else None
        )

    return {
        "test_runs": test_runs,
        "total_batches": total_batches,
        "total_scores": total_scores,
        "completion_rate": completion_rate,
        "completed_executions": completed_executions,
        "incomplete_executions_count": len(incomplete_executions),
        "avg_batches_per_run": avg_batches_per_run,
        "avg_scores_per_batch": avg_scores_per_batch,
        "avg_throughput_per_minute": avg_throughput,
        "execution_details": execution_details,
        "incomplete_executions": incomplete_executions,
    }


def calculate_comprehensive_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate comprehensive metrics from scorer results"""
    # First, get hierarchical metrics
    hierarchical_metrics = calculate_hierarchical_metrics(results)

    if not results:
        return {
            "total_executions": 0,
            "total_scores": 0,
            "unique_scorers": 0,
            "unique_generators": 0,
            "unique_datasets": 0,
            "violation_rate": 0.0,
            "severity_breakdown": {},
            "scorer_performance": {},
            "generator_risk_profile": {},
            "temporal_patterns": {},
            "hierarchical_metrics": hierarchical_metrics,
        }

    # Basic counts
    total_scores = len(results)
    unique_scorers = len(set(r.get("scorer_name", "Unknown") for r in results))
    unique_generators = len(set(r.get("generator_name", "Unknown") for r in results))
    unique_datasets = len(set(r.get("dataset_name", "Unknown") for r in results))
    unique_executions = hierarchical_metrics.get("test_runs", 0)  # Use hierarchical count

    # Violation analysis
    violations = 0
    for result in results:
        score_type = result.get("score_type")
        score_value = result.get("score_value")
        severity = result.get("severity")

        if score_type == "true_false" and score_value is True:
            violations += 1
        elif score_type == "float_scale" and score_value is not None:
            try:
                if float(score_value) >= 0.6:
                    violations += 1
            except (TypeError, ValueError):
                pass
        elif score_type == "str" and severity in ["high", "critical"]:
            violations += 1

    violation_rate = (violations / total_scores * 100) if total_scores > 0 else 0

    # Severity breakdown
    severity_counts = Counter(r.get("severity", "unknown") for r in results)
    severity_breakdown = dict(severity_counts)

    # Scorer performance
    scorer_performance = defaultdict(lambda: {"total": 0, "violations": 0, "avg_score": 0})
    for result in results:
        scorer = result.get("scorer_name", "Unknown")
        score_type = result.get("score_type")
        score_value = result.get("score_value")

        scorer_performance[scorer]["total"] += 1

        if score_type == "true_false" and score_value is True:
            scorer_performance[scorer]["violations"] += 1
        elif score_type == "float_scale" and score_value is not None:
            try:
                scorer_performance[scorer]["avg_score"] += float(score_value)
            except (TypeError, ValueError):
                pass

    # Calculate averages
    for scorer, stats in scorer_performance.items():
        if stats["total"] > 0:
            stats["violation_rate"] = stats["violations"] / stats["total"] * 100
            if stats["avg_score"] > 0:
                stats["avg_score"] /= stats["total"]

    # Generator risk profile
    generator_risk = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0})
    for result in results:
        generator = result.get("generator_name", "Unknown")
        severity = result.get("severity", "unknown")

        generator_risk[generator]["total"] += 1
        if severity == "critical":
            generator_risk[generator]["critical"] += 1
        elif severity == "high":
            generator_risk[generator]["high"] += 1

    # Temporal patterns
    temporal_patterns = analyze_temporal_patterns(results)

    return {
        "total_executions": unique_executions,
        "total_scores": total_scores,
        "unique_scorers": unique_scorers,
        "unique_generators": unique_generators,
        "unique_datasets": unique_datasets,
        "violation_rate": violation_rate,
        "severity_breakdown": severity_breakdown,
        "scorer_performance": dict(scorer_performance),
        "generator_risk_profile": dict(generator_risk),
        "temporal_patterns": temporal_patterns,
        "hierarchical_metrics": hierarchical_metrics,
    }


def analyze_temporal_patterns(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze temporal patterns in scorer results"""
    if not results:
        return {}

    # Convert timestamps and sort
    valid_results = []
    for r in results:
        timestamp = r.get("timestamp")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    r["timestamp"] = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    valid_results.append(r)
                elif isinstance(timestamp, datetime):
                    valid_results.append(r)
            except (ValueError, AttributeError) as e:
                logger.error(f"Failed to parse timestamp in analyze_temporal_patterns: {timestamp}, error: {e}")
                continue

    if not valid_results:
        return {}

    results_sorted = sorted(valid_results, key=lambda x: x.get("timestamp", datetime.min))

    # Hourly distribution
    hourly_violations = defaultdict(int)
    hourly_total = defaultdict(int)

    for result in results_sorted:
        timestamp = result.get("timestamp")
        if timestamp and isinstance(timestamp, datetime):
            hour = timestamp.hour
            hourly_total[hour] += 1
            if result.get("severity") in ["high", "critical"]:
                hourly_violations[hour] += 1

    # Daily trends
    daily_data = defaultdict(lambda: {"total": 0, "violations": 0})
    for result in results_sorted:
        timestamp = result.get("timestamp")
        if timestamp and isinstance(timestamp, datetime):
            day = timestamp.date()
            daily_data[day]["total"] += 1
            if result.get("severity") in ["high", "critical"]:
                daily_data[day]["violations"] += 1

    return {
        "hourly_violations": dict(hourly_violations),
        "hourly_total": dict(hourly_total),
        "daily_trends": {str(k): v for k, v in daily_data.items()},
    }


# --- Visualization Functions ---


def render_executive_dashboard(metrics: Dict[str, Any]):
    """Render executive-level dashboard with key metrics"""
    st.header("📊 Executive Summary")

    # Get hierarchical metrics if available
    hierarchical_metrics = metrics.get("hierarchical_metrics", {})

    if hierarchical_metrics:
        # First row - Core hierarchical metrics
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "🎯 Test Runs",
                f"{hierarchical_metrics['test_runs']:,}",
                help="Number of unique security testing campaigns executed",
            )

        with col2:
            st.metric(
                "📦 Batch Operations",
                f"{hierarchical_metrics['total_batches']:,}",
                delta=f"~{hierarchical_metrics['avg_batches_per_run']:.1f} per run",
                help="Total processing batches across all test runs",
            )

        with col3:
            st.metric(
                "📊 Score Results",
                f"{hierarchical_metrics['total_scores']:,}",
                delta=f"~{hierarchical_metrics['avg_scores_per_batch']:.0f} per batch",
                help="Individual security assessments performed",
            )

        with col4:
            completion_rate = hierarchical_metrics.get("completion_rate", 0.0)
            color = "🟢" if completion_rate >= 95 else "🟡" if completion_rate >= 80 else "🔴"
            incomplete_count = hierarchical_metrics.get("incomplete_executions_count", 0)
            st.metric(
                "⚡ Completion Rate",
                f"{color} {completion_rate:.1f}%",
                delta=(f"{incomplete_count} incomplete" if incomplete_count > 0 else "All complete"),
                delta_color="inverse" if incomplete_count > 0 else "off",
                help="Percentage of test runs that completed all expected batches",
            )

        with col5:
            if hierarchical_metrics.get("avg_throughput_per_minute"):
                st.metric(
                    "⚙️ Throughput",
                    f"{hierarchical_metrics['avg_throughput_per_minute']:.0f}/min",
                    help="Average scores processed per minute",
                )
            else:
                # Fall back to violation rate
                violation_rate = metrics.get("violation_rate", 0.0)
                st.metric(
                    "Violation Rate",
                    f"{violation_rate:.1f}%",
                    delta=f"{violation_rate - 50:.1f}%" if violation_rate != 0 else None,
                    delta_color="inverse",
                    help="Percentage of tests that detected violations",
                )

        # Second row - Additional insights
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Unique Scorers", f"{metrics['unique_scorers']:,}", help="Number of different security scorers used"
            )

        with col2:
            st.metric(
                "Unique Generators", f"{metrics['unique_generators']:,}", help="Number of different AI models tested"
            )

        with col3:
            defense_score = 100 - metrics.get("violation_rate", 0)
            color = "🟢" if defense_score >= 80 else "🟡" if defense_score >= 60 else "🔴"
            st.metric("Defense Score", f"{color} {defense_score:.0f}/100", help="Overall system defense effectiveness")

        with col4:
            critical_count = metrics.get("severity_breakdown", {}).get("critical", 0)
            high_count = metrics.get("severity_breakdown", {}).get("high", 0)
            st.metric(
                "Critical/High",
                f"{critical_count + high_count:,}",
                help="Number of critical and high severity findings",
            )

        # Show incomplete executions if any
        if hierarchical_metrics.get("incomplete_executions"):
            with st.expander(f"⚠️ Incomplete Executions ({len(hierarchical_metrics['incomplete_executions'])})"):
                incomplete_df = pd.DataFrame(hierarchical_metrics["incomplete_executions"])
                incomplete_df["completion_bar"] = incomplete_df["completion_percentage"].apply(
                    lambda x: f"{'█' * int(x/10)}{'░' * (10-int(x/10))} {x:.0f}%"
                )
                st.dataframe(
                    incomplete_df[["name", "execution_id", "completed_batches", "expected_batches", "completion_bar"]],
                    hide_index=True,
                    use_container_width=True,
                )
    else:
        # Fallback to original metrics display if hierarchical metrics not available
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total Executions", f"{metrics['total_executions']:,}", help="Number of unique test executions")

        with col2:
            st.metric("Total Scores", f"{metrics['total_scores']:,}", help="Total number of scores generated")

        with col3:
            violation_rate = metrics["violation_rate"]
            st.metric(
                "Violation Rate",
                f"{violation_rate:.1f}%",
                delta=f"{violation_rate - 50:.1f}%" if violation_rate != 0 else None,
                delta_color="inverse",
                help="Percentage of tests that detected violations",
            )

        with col4:
            defense_score = 100 - violation_rate
            color = "🟢" if defense_score >= 80 else "🟡" if defense_score >= 60 else "🔴"
            st.metric("Defense Score", f"{color} {defense_score:.0f}/100", help="Overall system defense effectiveness")

        with col5:
            critical_count = metrics["severity_breakdown"].get("critical", 0)
            high_count = metrics["severity_breakdown"].get("high", 0)
            st.metric(
                "Critical/High",
                f"{critical_count + high_count:,}",
                help="Number of critical and high severity findings",
            )

    # Severity distribution
    st.subheader("🎯 Severity Distribution")

    if metrics["severity_breakdown"]:
        # Create donut chart
        severity_data = []
        colors = []
        for severity in ["critical", "high", "medium", "low", "minimal"]:
            if severity in metrics["severity_breakdown"]:
                severity_data.append(
                    {"Severity": severity.capitalize(), "Count": metrics["severity_breakdown"][severity]}
                )
                colors.append(SEVERITY_COLORS[severity])

        if severity_data:
            df_severity = pd.DataFrame(severity_data)
            fig = px.pie(
                df_severity,
                values="Count",
                names="Severity",
                hole=0.4,
                color_discrete_sequence=colors,
                title="Finding Severity Distribution",
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)


def render_scorer_performance(results: List[Dict[str, Any]], metrics: Dict[str, Any]):
    """Render scorer performance analysis"""
    st.header("🔍 Scorer Performance Analysis")

    scorer_perf = metrics.get("scorer_performance", {})
    if not scorer_perf:
        st.info("No scorer performance data available")
        return

    # Create performance dataframe
    perf_data = []
    for scorer, stats in scorer_perf.items():
        perf_data.append(
            {
                "Scorer": scorer,
                "Total Tests": stats["total"],
                "Violations": stats["violations"],
                "Violation Rate": stats.get("violation_rate", 0),
                "Avg Score": stats.get("avg_score", 0),
            }
        )

    df_perf = pd.DataFrame(perf_data).sort_values("Violation Rate", ascending=False)

    # Performance bar chart
    fig = px.bar(
        df_perf,
        x="Scorer",
        y="Violation Rate",
        color="Violation Rate",
        color_continuous_scale="Reds",
        title="Scorer Detection Rates",
        labels={"Violation Rate": "Detection Rate (%)"},
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

    # Detailed metrics table
    st.subheader("📋 Detailed Scorer Metrics")

    # Format the dataframe for display
    df_display = df_perf.copy()
    df_display["Violation Rate"] = df_display["Violation Rate"].apply(lambda x: f"{x:.1f}%")
    df_display["Avg Score"] = df_display["Avg Score"].apply(lambda x: f"{x:.3f}" if x > 0 else "N/A")

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Scorer": st.column_config.TextColumn("Scorer Name", width="large"),
            "Total Tests": st.column_config.NumberColumn("Total Tests", format="%d"),
            "Violations": st.column_config.NumberColumn("Violations Detected", format="%d"),
            "Violation Rate": st.column_config.TextColumn("Detection Rate"),
            "Avg Score": st.column_config.TextColumn("Average Score"),
        },
    )


def render_generator_risk_analysis(metrics: Dict[str, Any]):
    """Render generator risk analysis"""
    st.header("⚠️ Generator Risk Analysis")

    gen_risk = metrics.get("generator_risk_profile", {})
    if not gen_risk:
        st.info("No generator risk data available")
        return

    # Calculate risk scores
    risk_data = []
    for generator, stats in gen_risk.items():
        total = stats["total"]
        if total > 0:
            risk_score = (stats["critical"] * 10 + stats["high"] * 5) / total
            risk_data.append(
                {
                    "Generator": generator,
                    "Total Tests": total,
                    "Critical": stats["critical"],
                    "High": stats["high"],
                    "Risk Score": risk_score,
                }
            )

    if risk_data:
        df_risk = pd.DataFrame(risk_data).sort_values("Risk Score", ascending=False)

        # Risk heatmap
        fig = px.treemap(
            df_risk,
            path=["Generator"],
            values="Total Tests",
            color="Risk Score",
            color_continuous_scale="Reds",
            title="Generator Risk Heatmap",
            hover_data={"Critical": True, "High": True},
        )
        st.plotly_chart(fig, use_container_width=True)

        # Risk table
        st.subheader("🔢 Risk Metrics by Generator")

        # Add risk level classification
        df_risk["Risk Level"] = df_risk["Risk Score"].apply(
            lambda x: "🔴 Critical" if x >= 8 else "🟠 High" if x >= 5 else "🟡 Medium" if x >= 2 else "🟢 Low"
        )

        st.dataframe(
            df_risk[["Generator", "Risk Level", "Total Tests", "Critical", "High", "Risk Score"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Generator": st.column_config.TextColumn("Generator", width="large"),
                "Risk Level": st.column_config.TextColumn("Risk Level"),
                "Risk Score": st.column_config.NumberColumn("Risk Score", format="%.2f"),
            },
        )


def render_temporal_analysis(results: List[Dict[str, Any]], metrics: Dict[str, Any]):
    """Render temporal analysis of results"""
    st.header("📈 Temporal Analysis")

    temporal = metrics.get("temporal_patterns", {})
    if not temporal:
        st.info("No temporal data available")
        return

    col1, col2 = st.columns(2)

    with col1:
        # Hourly pattern heatmap
        hourly_violations = temporal.get("hourly_violations", {})
        hourly_total = temporal.get("hourly_total", {})

        if hourly_violations and hourly_total:
            # Calculate violation rates by hour
            hours = list(range(24))
            rates = []
            for hour in hours:
                total = hourly_total.get(hour, 0)
                violations = hourly_violations.get(hour, 0)
                rate = (violations / total * 100) if total > 0 else 0
                rates.append(rate)

            # Create heatmap data
            heatmap_data = pd.DataFrame({"Hour": hours, "Violation Rate": rates})

            fig = px.bar(
                heatmap_data,
                x="Hour",
                y="Violation Rate",
                color="Violation Rate",
                color_continuous_scale="Reds",
                title="Violation Rate by Hour of Day",
                labels={"Violation Rate": "Rate (%)"},
            )
            fig.update_layout(xaxis=dict(dtick=1))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Daily trend line
        daily_trends = temporal.get("daily_trends", {})
        if daily_trends:
            trend_data = []
            for date_str, stats in sorted(daily_trends.items()):
                violation_rate = (stats["violations"] / stats["total"] * 100) if stats["total"] > 0 else 0
                trend_data.append(
                    {
                        "Date": datetime.fromisoformat(date_str).date(),
                        "Tests": stats["total"],
                        "Violations": stats["violations"],
                        "Rate": violation_rate,
                    }
                )

            df_trend = pd.DataFrame(trend_data)

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_trend["Date"],
                    y=df_trend["Rate"],
                    mode="lines+markers",
                    name="Violation Rate",
                    line=dict(color="red", width=2),
                    marker=dict(size=8),
                )
            )

            fig.update_layout(
                title="Daily Violation Rate Trend",
                xaxis_title="Date",
                yaxis_title="Violation Rate (%)",
                hovermode="x unified",
            )
            st.plotly_chart(fig, use_container_width=True)


def render_detailed_results_table(results: List[Dict[str, Any]]):
    """Render detailed results table with filtering"""
    st.header("🔎 Detailed Results Explorer")

    if not results:
        st.info("No results available")
        return

    # Filter controls
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        scorer_filter = st.multiselect(
            "Filter by Scorer", options=sorted(set(r["scorer_name"] for r in results)), default=[]
        )

    with col2:
        generator_filter = st.multiselect(
            "Filter by Generator", options=sorted(set(r["generator_name"] for r in results)), default=[]
        )

    with col3:
        severity_filter = st.multiselect(
            "Filter by Severity", options=["critical", "high", "medium", "low", "minimal"], default=[]
        )

    with col4:
        score_type_filter = st.selectbox(
            "Filter by Score Type", options=["All"] + list(SCORE_TYPE_MAP.values()), index=0
        )

    # Apply filters
    filtered_results = results.copy()

    if scorer_filter:
        filtered_results = [r for r in filtered_results if r["scorer_name"] in scorer_filter]

    if generator_filter:
        filtered_results = [r for r in filtered_results if r["generator_name"] in generator_filter]

    if severity_filter:
        filtered_results = [r for r in filtered_results if r["severity"] in severity_filter]

    if score_type_filter != "All":
        type_key = [k for k, v in SCORE_TYPE_MAP.items() if v == score_type_filter][0]
        filtered_results = [r for r in filtered_results if r["score_type"] == type_key]

    # Display count
    st.info(f"Showing {len(filtered_results)} of {len(results)} results")

    # Create dataframe for display
    if filtered_results:
        display_data = []
        for r in filtered_results:
            # Add batch information
            batch_info = f"{r.get('batch_index', 0) + 1}/{r.get('total_batches', 1)}"

            display_data.append(
                {
                    "Timestamp": r["timestamp"],
                    "Execution": r.get("execution_name", "Unknown"),
                    "Batch": batch_info,
                    "Scorer": r["scorer_name"],
                    "Generator": r["generator_name"],
                    "Dataset": r["dataset_name"],
                    "Score Type": SCORE_TYPE_MAP.get(r["score_type"], "Unknown"),
                    "Score Value": str(r["score_value"]),
                    "Severity": r["severity"].capitalize(),
                    "Category": r["score_category"],
                    "Rationale": (
                        r["score_rationale"][:100] + "..." if len(r["score_rationale"]) > 100 else r["score_rationale"]
                    ),
                }
            )

        df_display = pd.DataFrame(display_data)

        # Configure column display
        column_config = {
            "Timestamp": st.column_config.DatetimeColumn("Time", format="DD/MM/YYYY HH:mm:ss"),
            "Execution": st.column_config.TextColumn("Execution", width="medium"),
            "Batch": st.column_config.TextColumn("Batch", width="small", help="Current batch / Total batches"),
            "Severity": st.column_config.TextColumn("Severity", width="small"),
            "Rationale": st.column_config.TextColumn("Rationale", width="large"),
        }

        st.dataframe(df_display, use_container_width=True, hide_index=True, column_config=column_config)

        # Export options
        col1, col2 = st.columns(2)

        with col1:
            csv = df_display.to_csv(index=False)
            st.download_button(
                "📥 Download Results (CSV)",
                csv,
                f"scorer_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
            )

        with col2:
            json_data = json.dumps(filtered_results, indent=2, default=str)
            st.download_button(
                "📥 Download Results (JSON)",
                json_data,
                f"scorer_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json",
            )


# --- Main Dashboard Function ---


def main():
    """Main API-integrated dashboard"""
    logger.debug("API-Integrated Red Team Dashboard loading.")
    st.set_page_config(
        page_title="ViolentUTF Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded"
    )

    # Authentication and sidebar
    handle_authentication_and_sidebar("Dashboard")

    # Check authentication
    has_keycloak_token = bool(st.session_state.get("access_token"))
    has_env_credentials = bool(os.getenv("KEYCLOAK_USERNAME"))

    if not has_keycloak_token and not has_env_credentials:
        st.warning(
            "⚠️ Authentication required: Please log in via Keycloak SSO or configure KEYCLOAK_USERNAME in environment."
        )
        st.info("💡 For local development, you can set KEYCLOAK_USERNAME and KEYCLOAK_PASSWORD in your .env file")
        return

    # Ensure API token exists
    if not st.session_state.get("api_token"):
        with st.spinner("Generating API token..."):
            api_token = create_compatible_api_token()
            if not api_token:
                st.error("❌ Failed to generate API token. Please try refreshing the page.")
                return

    # Page header
    st.title("📊 ViolentUTF Dashboard")
    st.markdown("*Real-time analysis of actual scorer execution results from the ViolentUTF API*")

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Dashboard Controls")

        # Time range selector (same as Dashboard_4)
        days_back = st.slider(
            "Analysis Time Range (days)",
            min_value=7,
            max_value=90,
            value=30,
            help="Number of days to include in analysis",
        )

        # Auto-refresh toggle
        auto_refresh = st.checkbox("🔄 Auto-refresh (60s)", value=False)

        # Manual refresh button
        if st.button("🔃 Refresh Now", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()

        # Info section
        st.info(
            "**Dashboard Features:**\n"
            "- Real-time API data integration\n"
            "- Comprehensive scorer analytics\n"
            "- Generator risk profiling\n"
            "- Temporal pattern analysis\n"
            "- Export capabilities"
        )

    # Auto-refresh logic
    if auto_refresh:
        st.empty()  # Placeholder for auto-refresh timer
        time.sleep(60)
        st.cache_data.clear()
        st.rerun()

    # Load and process data using Dashboard_4 approach
    with st.spinner("🔄 Loading execution data from API..."):
        # Load orchestrator executions with their results (Dashboard_4 approach)
        executions, results = load_orchestrator_executions_with_results(days_back)

        if not executions:
            st.warning("📊 No scorer executions found in the selected date range.")
            st.info(
                "To generate scorer data:\n"
                "1. Go to the **4_Configure_Scorers** page\n"
                "2. Configure and test your scorers\n"
                "3. Run full executions to generate results\n"
                "4. Return here to view the analysis"
            )
            return

        if not results:
            st.warning("⚠️ Executions found but no scorer results available.")
            return

        # Display success message
        st.success(f"✅ Loaded {len(results)} scorer results from {len(executions)} executions")

        # Add dynamic filters
        render_dynamic_filters(results)

        # Apply filters if active
        filtered_results = apply_all_filters(results)

        # Show filter summary if filters are active
        if st.session_state.get("filter_state", {}).get("active", False):
            render_filter_summary(results, filtered_results)

        # Calculate metrics on filtered or original results
        metrics = calculate_comprehensive_metrics(filtered_results)

        # If comparison mode is enabled, also calculate baseline metrics
        baseline_metrics = None
        if st.session_state.get("filter_state", {}).get("comparison_mode", False):
            baseline_metrics = calculate_comprehensive_metrics(results)

    # Render dashboard sections
    tabs = st.tabs(
        [
            "📊 Executive Summary",
            "🔍 Scorer Performance",
            "⚠️ Generator Risk",
            "📈 Temporal Analysis",
            "🔎 Detailed Results",
        ]
    )

    with tabs[0]:
        if baseline_metrics and st.session_state.get("filter_state", {}).get("comparison_mode", False):
            # Render comparison view
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 📊 Baseline Metrics")
                render_executive_dashboard(baseline_metrics)
            with col2:
                st.markdown("### 🔍 Filtered Metrics")
                render_executive_dashboard(metrics)
        else:
            render_executive_dashboard(metrics)

    with tabs[1]:
        render_scorer_performance(filtered_results, metrics)

    with tabs[2]:
        render_generator_risk_analysis(metrics)

    with tabs[3]:
        render_temporal_analysis(filtered_results, metrics)

    with tabs[4]:
        render_detailed_results_table(filtered_results)


if __name__ == "__main__":
    import time  # Import time for auto-refresh

    main()
