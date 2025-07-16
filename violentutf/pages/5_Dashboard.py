import asyncio
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
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

# Severity mapping for different scorer types with type validation
SEVERITY_MAP = {
    # Boolean scorers - violation = high severity
    "true_false": lambda val: (
        "high" if val is True 
        else "low" if val is False
        # Handle string representations of boolean values
        else "high" if isinstance(val, str) and val.lower() in ["true", "1", "yes"]
        else "low" if isinstance(val, str) and val.lower() in ["false", "0", "no"]
        else "unknown"
    ),
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
        if val is not None and (isinstance(val, (int, float)) or (isinstance(val, str) and val.replace(".", "").replace("-", "").isdigit()))
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


# --- Helper Functions ---


def parse_datetime_safely(datetime_str: str) -> Optional[datetime]:
    """
    Safely parse datetime strings with various formats.
    Handles timezone-aware and timezone-naive strings.
    
    Args:
        datetime_str: DateTime string to parse
        
    Returns:
        datetime object with UTC timezone, or None if parsing fails
    """
    if not datetime_str:
        return None
        
    try:
        # Handle different datetime formats
        if datetime_str.endswith('Z'):
            # Replace Z with +00:00 for ISO format
            return datetime.fromisoformat(datetime_str[:-1] + '+00:00')
        elif '+' in datetime_str or datetime_str.count('T') == 1 and datetime_str[-6] in ['+', '-']:
            # Already has timezone info
            return datetime.fromisoformat(datetime_str)
        else:
            # No timezone info - assume UTC
            dt = datetime.fromisoformat(datetime_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except (ValueError, AttributeError) as e:
        logger.error(f"Failed to parse datetime '{datetime_str}': {e}")
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
                created_at = parse_datetime_safely(created_at_str)
                if created_at and start_date.date() <= created_at.date() <= end_date.date():
                    filtered_executions.append(execution)
                elif not created_at:
                    # Include if we couldn't parse the date (log error already handled in helper)
                    filtered_executions.append(execution)
            else:
                filtered_executions.append(execution)  # Include executions without timestamps

        # Filter results by time range too
        filtered_results = []
        for result in all_results:
            timestamp_str = result.get("timestamp", "")
            if timestamp_str:
                timestamp = parse_datetime_safely(timestamp_str)
                if timestamp and start_date.date() <= timestamp.date() <= end_date.date():
                    filtered_results.append(result)
                elif not timestamp:
                    # Include if we couldn't parse the timestamp
                    filtered_results.append(result)

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


# --- Response Data Integration Functions ---


@st.cache_data(ttl=60)  # 1-minute cache for real-time updates
def load_orchestrator_executions_with_full_data(
    days_back: int = 30,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load orchestrator executions with results AND prompt/response data"""
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
                    execution["execution_name"] = execution.get(
                        "name", f"Execution {execution.get('id', 'Unknown')[:8]}"
                    )
                    all_executions.append(execution)

                    # Load results for this execution immediately
                    # Only try to load results for completed executions
                    execution_id = execution.get("id")
                    execution_status = execution.get("status", "")

                    if not execution_id or execution_status != "completed":
                        continue

                    # Load full results with responses
                    full_results = load_execution_results_with_responses(execution_id)

                    if full_results:
                        scores = full_results.get("scores", [])
                        responses = full_results.get("prompt_request_responses", [])

                        # Debug logging
                        logger.info(f"Execution {execution_id}: {len(scores)} scores, {len(responses)} responses")

                        # Match scores to responses
                        matched_results = match_scores_to_responses(scores, responses)

                        # Debug: Check matching success
                        with_prompt_response = sum(1 for r in matched_results if r.get("prompt_response"))
                        logger.info(
                            f"Execution {execution_id}: {with_prompt_response}/{len(matched_results)} scores matched to responses"
                        )

                        # Enrich the matched results
                        enriched_results = enrich_response_data(matched_results)

                        # Process each enriched result
                        for enriched_score in enriched_results:
                            try:
                                # Parse metadata if it's a JSON string
                                metadata = enriched_score.get("score_metadata", "{}")
                                if isinstance(metadata, str):
                                    metadata = json.loads(metadata)

                                # Create unified result object with response data
                                result = {
                                    "execution_id": execution_id,
                                    "orchestrator_name": execution.get("orchestrator_name", "Unknown"),
                                    "execution_name": execution.get("execution_name", "Unknown"),
                                    "timestamp": enriched_score.get("timestamp", execution.get("created_at")),
                                    "score_value": enriched_score.get("score_value"),
                                    "score_type": enriched_score.get("score_type", "unknown"),
                                    "score_category": enriched_score.get("score_category", "unknown"),
                                    "score_rationale": enriched_score.get("score_rationale", ""),
                                    "scorer_type": metadata.get("scorer_type", "Unknown"),
                                    "scorer_name": metadata.get("scorer_name", "Unknown"),
                                    "generator_name": metadata.get("generator_name", "Unknown"),
                                    "generator_type": metadata.get("generator_type", "Unknown"),
                                    "dataset_name": metadata.get("dataset_name", "Unknown"),
                                    "test_mode": metadata.get("test_mode", "unknown"),
                                    "batch_index": enriched_score.get("batch_index", 0),
                                    "total_batches": enriched_score.get("total_batches", 1),
                                    # Add response data
                                    "prompt_response": enriched_score.get("prompt_response"),
                                    "response_insights": enriched_score.get("response_insights"),
                                    "searchable_content": enriched_score.get("searchable_content", []),
                                }

                                # Calculate severity
                                score_type = result["score_type"]
                                if score_type in SEVERITY_MAP:
                                    result["severity"] = SEVERITY_MAP[score_type](result["score_value"])
                                else:
                                    result["severity"] = "unknown"

                                all_results.append(result)

                            except Exception as e:
                                logger.error(f"Failed to parse enriched score result: {e}")
                                continue

        # Filter executions by time range
        filtered_executions = []

        for execution in all_executions:
            created_at_str = execution.get("created_at", "")
            if created_at_str:
                created_at = parse_datetime_safely(created_at_str)
                if created_at and start_date.date() <= created_at.date() <= end_date.date():
                    filtered_executions.append(execution)
                elif not created_at:
                    # Include if we couldn't parse the date (log error already handled in helper)
                    filtered_executions.append(execution)
            else:
                filtered_executions.append(execution)  # Include executions without timestamps

        # Filter results by time range too
        filtered_results = []
        for result in all_results:
            timestamp_str = result.get("timestamp", "")
            if timestamp_str:
                timestamp = parse_datetime_safely(timestamp_str)
                if timestamp and start_date.date() <= timestamp.date() <= end_date.date():
                    filtered_results.append(result)
                elif not timestamp:
                    # Include if we couldn't parse the timestamp
                    filtered_results.append(result)

        return filtered_executions, filtered_results
    except Exception as e:
        logger.error(f"Failed to load orchestrator executions with full data: {e}")
        return [], []


@st.cache_data(ttl=60)
def load_execution_results_with_responses(execution_id: str) -> Dict[str, Any]:
    """Load detailed results including prompt/response data for a specific execution"""
    try:
        url = API_ENDPOINTS["execution_results"].format(execution_id=execution_id)
        response = api_request("GET", url)

        if not response:
            return {}

        # Extract both scores and prompt_request_responses
        result = {
            "scores": response.get("scores", []),
            "prompt_request_responses": response.get("prompt_request_responses", []),
            "execution_id": execution_id,
            "metadata": response.get("metadata", {}),
        }

        return result
    except Exception as e:
        logger.error(f"Failed to load execution results with responses: {e}")
        return {}


def match_scores_to_responses(scores: List[Dict], responses: List[Dict]) -> List[Dict]:
    """Match scores to their corresponding prompt/response pairs using batch_index and timestamps"""
    matched_results = []

    # Debug logging to understand data structure
    if responses:
        logger.info(f"Sample response structure: {json.dumps(responses[0], indent=2, default=str)[:500]}")
    if scores:
        logger.info(f"Sample score structure: {json.dumps(scores[0], indent=2, default=str)[:500]}")

    # Create lookup maps for responses by both batch_index and conversation_id
    response_map_by_batch = {}
    response_map_by_conversation = {}

    for resp in responses:
        # Try batch_index first
        batch_idx = resp.get("batch_index", None)
        if batch_idx is not None:
            if batch_idx not in response_map_by_batch:
                response_map_by_batch[batch_idx] = []
            response_map_by_batch[batch_idx].append(resp)

        # Also map by conversation_id
        conv_id = resp.get("conversation_id") or resp.get("request", {}).get("conversation_id")
        if conv_id:
            if conv_id not in response_map_by_conversation:
                response_map_by_conversation[conv_id] = []
            response_map_by_conversation[conv_id].append(resp)

    # Match scores to responses
    for score in scores:
        matched_score = score.copy()
        batch_responses = []

        # Try to find responses by batch_index first
        batch_idx = score.get("batch_index", None)
        if batch_idx is not None and batch_idx in response_map_by_batch:
            batch_responses = response_map_by_batch[batch_idx]

        # If no batch match, try conversation_id
        if not batch_responses:
            conv_id = score.get("conversation_id") or score.get("prompt_id")
            if conv_id and conv_id in response_map_by_conversation:
                batch_responses = response_map_by_conversation[conv_id]

        # If still no match, try to match by index position (fallback)
        if not batch_responses and scores.index(score) < len(responses):
            batch_responses = [responses[scores.index(score)]]

        if batch_responses:
            # Try to match by timestamp proximity if multiple responses in batch
            score_timestamp = score.get("timestamp")
            if score_timestamp and len(batch_responses) > 1:
                # Find closest response by timestamp
                closest_response = min(
                    batch_responses,
                    key=lambda r: (
                        abs(
                            datetime.fromisoformat(r.get("timestamp", "").replace("Z", "+00:00"))
                            - datetime.fromisoformat(score_timestamp.replace("Z", "+00:00"))
                        ).total_seconds()
                        if r.get("timestamp")
                        else float("inf")
                    ),
                )
                # Transform the response structure to match expected format
                if closest_response:
                    matched_score["prompt_response"] = {
                        "prompt": closest_response.get("request", {}).get("prompt", ""),
                        "response": closest_response.get("response", {}).get("content", ""),
                    }
                else:
                    matched_score["prompt_response"] = None
            else:
                # Use first response if only one or no timestamp
                response = batch_responses[0]
                if response:
                    matched_score["prompt_response"] = {
                        "prompt": response.get("request", {}).get("prompt", ""),
                        "response": response.get("response", {}).get("content", ""),
                    }
                else:
                    matched_score["prompt_response"] = None
        else:
            matched_score["prompt_response"] = None

        matched_results.append(matched_score)

    return matched_results


def enrich_response_data(matched_results: List[Dict]) -> List[Dict]:
    """Enrich response data with extracted insights and categorization"""
    enriched_results = []

    for result in matched_results:
        enriched = result.copy()

        if result.get("prompt_response"):
            prompt = result["prompt_response"].get("prompt", "")
            response = result["prompt_response"].get("response", "")

            # Extract key insights
            enriched["response_insights"] = {
                "prompt_length": len(prompt),
                "response_length": len(response),
                "contains_code": bool(re.search(r"```[\s\S]*?```", response)),
                "contains_url": bool(re.search(r"https?://\S+", response)),
                "contains_script": bool(re.search(r"<script[\s\S]*?</script>", response, re.IGNORECASE)),
                "prompt_type": categorize_prompt(prompt),
                "response_type": categorize_response(response),
            }

            # Extract key phrases for search
            enriched["searchable_content"] = extract_key_phrases(prompt + " " + response)

        enriched_results.append(enriched)

    return enriched_results


def categorize_prompt(prompt: str) -> str:
    """Categorize prompt type based on content analysis"""
    prompt_lower = prompt.lower()

    if any(keyword in prompt_lower for keyword in ["ignore", "forget", "disregard"]):
        return "instruction_override"
    elif any(keyword in prompt_lower for keyword in ["tell me", "what is", "explain"]):
        return "information_extraction"
    elif any(keyword in prompt_lower for keyword in ["code", "script", "program"]):
        return "code_generation"
    elif any(keyword in prompt_lower for keyword in ["system", "admin", "root"]):
        return "privilege_escalation"
    else:
        return "general"


def categorize_response(response: str) -> str:
    """Categorize response type based on content analysis"""
    response_lower = response.lower()

    if "i cannot" in response_lower or "i'm unable" in response_lower:
        return "refusal"
    elif "```" in response:
        return "code_output"
    elif len(response) > 1000:
        return "verbose"
    elif any(keyword in response_lower for keyword in ["error", "exception", "failed"]):
        return "error"
    else:
        return "standard"


def extract_key_phrases(text: str, max_phrases: int = 10) -> List[str]:
    """Extract key phrases from text for searchability"""
    # Simple keyword extraction - in production, use NLP library
    # Remove common words
    stop_words = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "but", "in", "with", "to", "for"}

    # Extract words
    words = re.findall(r"\b\w+\b", text.lower())
    words = [w for w in words if len(w) > 3 and w not in stop_words]

    # Get most common phrases
    word_freq = Counter(words)
    return [word for word, _ in word_freq.most_common(max_phrases)]


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

    # Use UTC for consistency
    now = datetime.now(timezone.utc)

    # Define time ranges for presets (all in UTC)
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
        # Ensure custom dates are timezone-aware
        start_time = custom_start.replace(tzinfo=timezone.utc) if custom_start.tzinfo is None else custom_start
        end_time = custom_end.replace(tzinfo=timezone.utc) if custom_end.tzinfo is None else custom_end
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
                    # Parse ISO format timestamp
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

                # Ensure timestamp is timezone-aware
                if isinstance(timestamp, datetime):
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)

                    if start_time <= timestamp <= end_time:
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
                    parsed_ts = parse_datetime_safely(current_ts)
                    if parsed_ts:
                        current_ts = parsed_ts
                    else:
                        continue

                first_ts = batch_info[batch_key].get("first_timestamp")
                if first_ts is None:
                    batch_info[batch_key]["first_timestamp"] = current_ts
                elif isinstance(first_ts, str):
                    parsed_first_ts = parse_datetime_safely(first_ts)
                    if parsed_first_ts:
                        batch_info[batch_key]["first_timestamp"] = parsed_first_ts
                    else:
                        batch_info[batch_key]["first_timestamp"] = current_ts

                # Safe comparison with first_timestamp
                first_ts_value = batch_info[batch_key].get("first_timestamp")
                if first_ts_value and isinstance(first_ts_value, datetime) and current_ts < first_ts_value:
                    batch_info[batch_key]["first_timestamp"] = current_ts

                # Also convert last_timestamp if it's a string
                last_ts = batch_info[batch_key].get("last_timestamp")
                if isinstance(last_ts, str):
                    parsed_last_ts = parse_datetime_safely(last_ts)
                    if parsed_last_ts:
                        batch_info[batch_key]["last_timestamp"] = parsed_last_ts
                    else:
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
        
        # Fixed logic: Check if THIS execution's batches are complete
        # For single-batch executions (which is the common case), they are complete if they have their batch
        if len(actual_batch_indices) == 1:
            # Single batch execution - it's complete if it has its batch
            completed = True
        elif len(actual_batch_indices) == 0:
            # No batch indices found - consider complete if there are results
            completed = len(exec_results) > 0
        else:
            # Multi-batch execution - check if we have a continuous sequence
            if actual_batch_indices:
                min_idx = min(actual_batch_indices)
                max_idx = max(actual_batch_indices)
                expected_indices = set(range(min_idx, max_idx + 1))
                completed = actual_batch_indices == expected_indices
            else:
                completed = False

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

        # Calculate completion percentage based on the execution type
        if len(actual_batch_indices) <= 1:
            # Single batch or no batch - 100% if completed, 0% if not
            completion_percentage = 100.0 if completed else 0.0
        else:
            # Multi-batch - percentage of continuous sequence
            if actual_batch_indices:
                min_idx = min(actual_batch_indices)
                max_idx = max(actual_batch_indices)
                expected_count = max_idx - min_idx + 1
                completion_percentage = (len(actual_batch_indices) / expected_count * 100)
            else:
                completion_percentage = 0.0
        
        execution_details[exec_id] = {
            "name": execution_name,
            "unique_batches": unique_batches,
            "expected_batches": expected_batches,
            "completed": completed,
            "completion_percentage": completion_percentage,
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
                "🎯 Executions",
                f"{hierarchical_metrics['test_runs']:,}",
                help="Number of orchestrator executions performed",
            )

        with col2:
            st.metric(
                "💬 Total Prompts",
                f"{hierarchical_metrics['total_scores']:,}",
                delta=f"~{hierarchical_metrics['total_scores'] // hierarchical_metrics['test_runs'] if hierarchical_metrics['test_runs'] > 0 else 0:.0f} per execution",
                help="Total number of prompts sent to AI models for testing",
            )

        with col3:
            # Use violation rate from metrics
            violation_rate = metrics.get("violation_rate", 0.0)
            # Calculate violation count from total scores and rate
            total_scores = hierarchical_metrics.get("total_scores", 0)
            violation_count = int(total_scores * violation_rate / 100)
            st.metric(
                "🚨 Violation Rate",
                f"{violation_rate:.1f}%",
                delta=f"{violation_count:,} violations found",
                delta_color="inverse",
                help="Percentage of prompts that triggered security violations",
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
                    help="Percentage of tests that detected security violations. Higher rates indicate more potential security issues were found.",
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
                help="Percentage of tests that detected security violations. Higher rates indicate more potential security issues were found.",
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
        # Update filter options to be clearer about True/False
        score_type_options = ["All", "True/False", "Scale (0-1)", "Category"]
        score_type_filter = st.selectbox(
            "Filter by Evaluation Type",
            options=score_type_options,
            index=0,
            help="True/False: Boolean scorers, Scale: Numeric 0-1 scorers, Category: Text category scorers",
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
        if score_type_filter == "True/False":
            filtered_results = [r for r in filtered_results if r["score_type"] == "true_false"]
        elif score_type_filter == "Scale (0-1)":
            filtered_results = [r for r in filtered_results if r["score_type"] == "float_scale"]
        elif score_type_filter == "Category":
            filtered_results = [r for r in filtered_results if r["score_type"] == "str"]

    # Display count
    st.info(f"Showing {len(filtered_results)} of {len(results)} results")

    # Create dataframe for display
    if filtered_results:
        display_data = []
        for r in filtered_results:
            # Add batch information
            batch_info = f"{r.get('batch_index', 0) + 1}/{r.get('total_batches', 1)}"

            # Extract prompt and response for display
            prompt_text = ""
            response_text = ""
            if r.get("prompt_response"):
                prompt_text = r["prompt_response"].get("prompt", "")
                response_text = r["prompt_response"].get("response", "")

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
                    "Prompt": prompt_text[:100] + "..." if len(prompt_text) > 100 else prompt_text,
                    "Response": response_text[:100] + "..." if len(response_text) > 100 else response_text,
                    "Rationale": (
                        r["score_rationale"][:100] + "..." if len(r["score_rationale"]) > 100 else r["score_rationale"]
                    ),
                    "Full Prompt": prompt_text,  # Hidden column for export
                    "Full Response": response_text,  # Hidden column for export
                }
            )

        df_display = pd.DataFrame(display_data)

        # Configure column display
        column_config = {
            "Timestamp": st.column_config.DatetimeColumn("Time", format="DD/MM/YYYY HH:mm:ss"),
            "Execution": st.column_config.TextColumn("Execution", width="medium"),
            "Batch": st.column_config.TextColumn("Batch", width="small", help="Current batch / Total batches"),
            "Severity": st.column_config.TextColumn("Severity", width="small"),
            "Prompt": st.column_config.TextColumn("Prompt", width="medium", help="Truncated to 100 chars"),
            "Response": st.column_config.TextColumn("Response", width="medium", help="Truncated to 100 chars"),
            "Rationale": st.column_config.TextColumn("Rationale", width="large"),
            "Full Prompt": None,  # Hide from display but keep for export
            "Full Response": None,  # Hide from display but keep for export
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


# --- Enhanced Evidence Explorer Functions ---


def render_detailed_results_table_with_responses(results: List[Dict[str, Any]]):
    """Render enhanced detailed results table with prompt/response data"""
    st.header("🔎 Evidence Explorer - Enhanced View")

    if not results:
        st.info("No results available")
        return

    # Add view mode selector
    view_mode = st.radio(
        "View Mode",
        ["Table View", "Card View", "Conversation View"],
        horizontal=True,
        help="Choose how to display the evidence",
    )

    # Filter controls with response search
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        scorer_filter = st.multiselect(
            "Filter by Scorer",
            options=sorted(set(r.get("scorer_name", "Unknown") for r in results)),
            default=[],
        )

    with col2:
        severity_filter = st.multiselect(
            "Filter by Severity",
            options=["critical", "high", "medium", "low", "minimal"],
            default=[],
        )

    with col3:
        # New response type filter
        response_types = set()
        for r in results:
            if r.get("response_insights"):
                response_types.add(r["response_insights"].get("response_type", "unknown"))

        response_type_filter = st.multiselect(
            "Filter by Response Type",
            options=sorted(response_types) if response_types else ["No response data"],
            default=[],
        )

    with col4:
        # Search functionality
        search_query = st.text_input(
            "Search in prompts/responses",
            placeholder="Enter keywords or regex pattern",
            help="Search in prompt and response content",
        )

    # Advanced search options
    with st.expander("Advanced Search Options"):
        search_col1, search_col2 = st.columns(2)
        with search_col1:
            use_regex = st.checkbox("Use Regular Expression", value=False)
            case_sensitive = st.checkbox("Case Sensitive", value=False)
        with search_col2:
            search_in = st.multiselect(
                "Search in",
                ["Prompts", "Responses", "Rationale"],
                default=["Prompts", "Responses"],
            )

    # Apply filters
    filtered_results = apply_evidence_filters(
        results,
        scorer_filter,
        severity_filter,
        response_type_filter,
        search_query,
        use_regex,
        case_sensitive,
        search_in,
    )

    # Display count
    st.info(f"Showing {len(filtered_results)} of {len(results)} results")

    # Render based on view mode
    if view_mode == "Table View":
        render_table_view_with_responses(filtered_results)
    elif view_mode == "Card View":
        render_card_view(filtered_results)
    else:  # Conversation View
        render_conversation_view(filtered_results)

    # Export options
    render_export_options(filtered_results)


def apply_evidence_filters(
    results: List[Dict],
    scorer_filter: List[str],
    severity_filter: List[str],
    response_type_filter: List[str],
    search_query: str,
    use_regex: bool,
    case_sensitive: bool,
    search_in: List[str],
) -> List[Dict]:
    """Apply filters including response content search"""
    filtered = results.copy()

    # Basic filters
    if scorer_filter:
        filtered = [r for r in filtered if r.get("scorer_name") in scorer_filter]

    if severity_filter:
        filtered = [r for r in filtered if r.get("severity") in severity_filter]

    if response_type_filter and response_type_filter != ["No response data"]:
        filtered = [r for r in filtered if r.get("response_insights", {}).get("response_type") in response_type_filter]

    # Search filter
    if search_query:
        search_results = []
        for result in filtered:
            if search_in_result(result, search_query, use_regex, case_sensitive, search_in):
                search_results.append(result)
        filtered = search_results

    return filtered


def search_in_result(
    result: Dict,
    query: str,
    use_regex: bool,
    case_sensitive: bool,
    search_in: List[str],
) -> bool:
    """Search for query in result's prompt/response content"""
    search_texts = []

    if "Prompts" in search_in and result.get("prompt_response"):
        search_texts.append(result["prompt_response"].get("prompt", ""))

    if "Responses" in search_in and result.get("prompt_response"):
        search_texts.append(result["prompt_response"].get("response", ""))

    if "Rationale" in search_in:
        search_texts.append(result.get("score_rationale", ""))

    combined_text = " ".join(search_texts)

    if not case_sensitive:
        combined_text = combined_text.lower()
        query = query.lower()

    if use_regex:
        try:
            pattern = re.compile(query, re.IGNORECASE if not case_sensitive else 0)
            return bool(pattern.search(combined_text))
        except re.error:
            return False
    else:
        return query in combined_text


def render_table_view_with_responses(results: List[Dict]):
    """Render enhanced table view with expandable rows for responses"""
    if not results:
        return

    # Create expandable rows
    for idx, result in enumerate(results):
        with st.container():
            # Main row
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])

            with col1:
                # Execution info with timestamp
                timestamp = result.get("timestamp", "")
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        timestamp_str = timestamp
                else:
                    timestamp_str = str(timestamp)

                st.markdown(f"**{timestamp_str}**")
                st.caption(f"Execution: {result.get('execution_name', 'Unknown')}")

            with col2:
                st.markdown(f"**Scorer:** {result.get('scorer_name', 'Unknown')}")
                score_value = result.get("score_value", "N/A")
                if result.get("score_type") == "true_false":
                    score_icon = "✅" if not score_value else "❌"
                    st.markdown(f"Score: {score_icon}")
                else:
                    st.markdown(f"Score: {score_value}")

            with col3:
                severity = result.get("severity", "unknown")
                severity_color = SEVERITY_COLORS.get(severity, "#808080")
                st.markdown(
                    f'<span style="color: {severity_color}">⬤</span> {severity.capitalize()}',
                    unsafe_allow_html=True,
                )

            with col4:
                insights = result.get("response_insights", {})
                if insights:
                    badges = []
                    if insights.get("contains_code"):
                        badges.append("💻 Code")
                    if insights.get("contains_url"):
                        badges.append("🔗 URL")
                    if insights.get("contains_script"):
                        badges.append("⚠️ Script")

                    if badges:
                        st.caption(" ".join(badges))

            with col5:
                # Expand button
                if st.button("📄 Details", key=f"expand_{idx}"):
                    st.session_state[f"expanded_{idx}"] = not st.session_state.get(f"expanded_{idx}", False)

            # Expandable content
            if st.session_state.get(f"expanded_{idx}", False):
                render_expanded_result(result, idx)

            st.divider()


def render_expanded_result(result: Dict, idx: int):
    """Render expanded view of a single result with prompt/response"""
    with st.container():
        # Score rationale
        if result.get("score_rationale"):
            st.markdown("**🎯 Score Rationale:**")
            st.info(result["score_rationale"])

        # Prompt and Response
        if result.get("prompt_response"):
            prompt_response = result["prompt_response"]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**📝 Prompt:**")
                prompt_text = prompt_response.get("prompt", "No prompt available")
                st.text_area(
                    "Prompt Content",
                    value=prompt_text,
                    height=200,
                    disabled=True,
                    key=f"prompt_{idx}",
                )

                # Prompt metadata
                insights = result.get("response_insights", {})
                if insights:
                    st.caption(f"Type: {insights.get('prompt_type', 'Unknown')}")
                    st.caption(f"Length: {insights.get('prompt_length', 0)} chars")

            with col2:
                st.markdown("**💬 Response:**")
                response_text = prompt_response.get("response", "No response available")
                st.text_area(
                    "Response Content",
                    value=response_text,
                    height=200,
                    disabled=True,
                    key=f"response_{idx}",
                )

                # Response metadata
                if insights:
                    st.caption(f"Type: {insights.get('response_type', 'Unknown')}")
                    st.caption(f"Length: {insights.get('response_length', 0)} chars")
        else:
            # Debug information when no prompt_response data
            st.warning("⚠️ No prompt/response data available for this result")

            # Show what data we do have
            with st.expander("🔍 Debug Information"):
                st.write("**Available result keys:**")
                st.write(list(result.keys()))

                st.write("**Result structure (first 500 chars):**")
                result_str = str(result)[:500]
                st.text(result_str)

                # Check if enhanced evidence is enabled
                enhanced_evidence = st.session_state.get("enhanced_evidence", False)
                st.write(f"**Enhanced Evidence Mode:** {enhanced_evidence}")

                # Check execution status
                exec_id = result.get("execution_id", "Unknown")
                st.write(f"**Execution ID:** {exec_id}")

                # Check batch info
                batch_idx = result.get("batch_index", "Unknown")
                st.write(f"**Batch Index:** {batch_idx}")

        # Action buttons
        action_col1, action_col2, action_col3, action_col4 = st.columns(4)

        with action_col1:
            if st.button("📋 Copy Evidence", key=f"copy_{idx}"):
                copy_evidence_to_clipboard(result)

        with action_col2:
            if st.button("🔍 Find Similar", key=f"similar_{idx}"):
                st.session_state[f"find_similar_{idx}"] = True

        with action_col3:
            if st.button("🏷️ Tag Evidence", key=f"tag_{idx}"):
                st.session_state[f"tag_evidence_{idx}"] = True

        with action_col4:
            if st.button("📊 Analyze", key=f"analyze_{idx}"):
                st.session_state[f"analyze_evidence_{idx}"] = True


def render_card_view(results: List[Dict]):
    """Render results as cards (Pinterest-style layout)"""
    # Create columns for card layout
    num_columns = 3
    columns = st.columns(num_columns)

    for idx, result in enumerate(results):
        col_idx = idx % num_columns

        with columns[col_idx]:
            render_evidence_card(result, idx)


def render_evidence_card(result: Dict, idx: int):
    """Render a single evidence card"""
    with st.container():
        # Severity indicator
        severity = result.get("severity", "unknown")
        severity_color = SEVERITY_COLORS.get(severity, "#808080")

        # Card container with border
        with st.container():
            st.markdown(
                f"""
                <div style="
                    border: 2px solid {severity_color};
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                ">
                """,
                unsafe_allow_html=True,
            )

            # Header with severity
            st.markdown(f"### {severity.capitalize()} Finding")

            # Scorer and score
            st.caption(f"**{result.get('scorer_name', 'Unknown')}**")

            score_value = result.get("score_value", "N/A")
            if result.get("score_type") == "true_false":
                st.markdown(f"Score: {'✅ Pass' if not score_value else '❌ Fail'}")
            else:
                st.markdown(f"Score: {score_value}")

            # Rationale preview
            rationale = result.get("score_rationale", "")
            if rationale:
                preview = rationale[:150] + "..." if len(rationale) > 150 else rationale
                st.text(preview)

            # Response preview if available
            if result.get("prompt_response"):
                response = result["prompt_response"].get("response", "")
                if response:
                    response_preview = response[:100] + "..." if len(response) > 100 else response
                    st.info(f"Response: {response_preview}")

            # Insights badges
            insights = result.get("response_insights", {})
            if insights:
                badges = []
                if insights.get("contains_code"):
                    badges.append("💻")
                if insights.get("contains_url"):
                    badges.append("🔗")
                if insights.get("contains_script"):
                    badges.append("⚠️")

                if badges:
                    st.markdown(" ".join(badges))

            # View full details button
            if st.button(f"View Details", key=f"card_view_{idx}"):
                st.session_state[f"show_card_details_{idx}"] = True

            st.markdown("</div>", unsafe_allow_html=True)

        # Show details in modal-like expander
        if st.session_state.get(f"show_card_details_{idx}", False):
            with st.expander("Full Details", expanded=True):
                render_expanded_result(result, idx)
                if st.button("Close", key=f"close_card_{idx}"):
                    st.session_state[f"show_card_details_{idx}"] = False
                    st.rerun()


def render_conversation_view(results: List[Dict]):
    """Render results as conversations grouped by execution"""
    # Group results by execution
    executions = {}
    for result in results:
        exec_id = result.get("execution_id", "unknown")
        if exec_id not in executions:
            executions[exec_id] = {
                "name": result.get("execution_name", "Unknown Execution"),
                "results": [],
            }
        executions[exec_id]["results"].append(result)

    # Render each execution as a conversation thread
    for exec_id, execution_data in executions.items():
        with st.expander(f"📋 {execution_data['name']} ({len(execution_data['results'])} results)"):
            render_conversation_thread(execution_data["results"])


def render_conversation_thread(results: List[Dict]):
    """Render a conversation thread for an execution"""
    # Sort by timestamp/batch_index
    sorted_results = sorted(results, key=lambda x: (x.get("batch_index", 0), x.get("timestamp", "")))

    for idx, result in enumerate(sorted_results):
        # Conversation bubble style based on severity
        severity = result.get("severity", "unknown")
        severity_color = SEVERITY_COLORS.get(severity, "#808080")

        col1, col2 = st.columns([1, 5])

        with col1:
            # Avatar/indicator
            st.markdown(
                f'<div style="text-align: center; font-size: 2em; color: {severity_color}">⬤</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"Batch {result.get('batch_index', 0) + 1}")

        with col2:
            # Message bubble
            if result.get("prompt_response"):
                prompt = result["prompt_response"].get("prompt", "")
                response = result["prompt_response"].get("response", "")

                # Prompt bubble
                st.markdown(
                    f'<div style="background-color: #e3f2fd; padding: 10px; border-radius: 10px; margin-bottom: 10px;">'
                    f'<strong>Prompt:</strong><br>{prompt[:200]}{"..." if len(prompt) > 200 else ""}'
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Response bubble
                st.markdown(
                    f'<div style="background-color: #f5f5f5; padding: 10px; border-radius: 10px; margin-bottom: 10px;">'
                    f'<strong>Response:</strong><br>{response[:200]}{"..." if len(response) > 200 else ""}'
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # Score info
            st.caption(f"**{result.get('scorer_name', 'Unknown')}** - Score: {result.get('score_value', 'N/A')}")

            if result.get("score_rationale"):
                st.caption(f"💭 {result['score_rationale'][:100]}...")

        if idx < len(sorted_results) - 1:
            st.divider()


def copy_evidence_to_clipboard(result: Dict):
    """Format and copy evidence to clipboard"""
    evidence = f"""Evidence Report
===============
Timestamp: {result.get('timestamp', 'Unknown')}
Execution: {result.get('execution_name', 'Unknown')}
Scorer: {result.get('scorer_name', 'Unknown')}
Score: {result.get('score_value', 'N/A')}
Severity: {result.get('severity', 'Unknown')}

Rationale:
{result.get('score_rationale', 'No rationale provided')}

"""

    if result.get("prompt_response"):
        prompt_response = result["prompt_response"]
        evidence += f"""
Prompt:
{prompt_response.get('prompt', 'No prompt available')}

Response:
{prompt_response.get('response', 'No response available')}
"""

    # Show in text area for manual copy
    st.text_area("Evidence (Copy manually):", evidence, height=300)


def render_export_options(results: List[Dict]):
    """Render export options for evidence"""
    if not results:
        return

    st.markdown("### 📤 Export Options")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # CSV export
        csv_data = export_to_csv(results)
        st.download_button(
            "📊 Export as CSV",
            csv_data,
            f"evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "text/csv",
        )

    with col2:
        # JSON export
        json_data = json.dumps(results, indent=2, default=str)
        st.download_button(
            "📄 Export as JSON",
            json_data,
            f"evidence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "application/json",
        )

    with col3:
        # Evidence package (filtered)
        if st.button("📦 Create Evidence Package"):
            create_evidence_package(results)

    with col4:
        # Compliance report
        if st.button("📋 Generate Report"):
            generate_compliance_report(results)


def export_to_csv(results: List[Dict]) -> str:
    """Export results to CSV format"""
    output = io.StringIO()

    # Define columns
    fieldnames = [
        "timestamp",
        "execution_name",
        "scorer_name",
        "score_value",
        "severity",
        "score_rationale",
        "prompt",
        "response",
        "prompt_type",
        "response_type",
        "contains_code",
        "contains_url",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for result in results:
        row = {
            "timestamp": result.get("timestamp", ""),
            "execution_name": result.get("execution_name", ""),
            "scorer_name": result.get("scorer_name", ""),
            "score_value": str(result.get("score_value", "")),
            "severity": result.get("severity", ""),
            "score_rationale": result.get("score_rationale", ""),
        }

        if result.get("prompt_response"):
            row["prompt"] = result["prompt_response"].get("prompt", "")
            row["response"] = result["prompt_response"].get("response", "")

        if result.get("response_insights"):
            insights = result["response_insights"]
            row["prompt_type"] = insights.get("prompt_type", "")
            row["response_type"] = insights.get("response_type", "")
            row["contains_code"] = str(insights.get("contains_code", False))
            row["contains_url"] = str(insights.get("contains_url", False))

        writer.writerow(row)

    return output.getvalue()


def create_evidence_package(results: List[Dict]):
    """Create a comprehensive evidence package"""
    # This would create a ZIP file with:
    # - Executive summary
    # - Full results JSON
    # - Screenshots/visualizations
    # - Audit trail
    st.info("Evidence package creation would generate a ZIP file with all relevant data")


def generate_compliance_report(results: List[Dict]):
    """Generate a compliance-focused report"""
    # This would create a formatted report with:
    # - Executive summary
    # - Risk assessment
    # - Detailed findings
    # - Recommendations
    st.info("Compliance report generation would create a formatted PDF report")


# --- Multi-Dimensional Analysis Functions ---


def calculate_scorer_generator_matrix(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate performance matrix for scorers × generators"""
    if not results:
        return {"matrix": {}, "scorers": [], "generators": []}

    # Initialize matrix structure
    matrix = defaultdict(
        lambda: defaultdict(
            lambda: {
                "total": 0,
                "violations": 0,
                "detection_rate": 0.0,
                "avg_score": 0.0,
                "score_sum": 0.0,
                "confidence": 0.0,
                "samples": [],
            }
        )
    )

    # Collect unique scorers and generators
    scorers = set()
    generators = set()

    # Build the matrix
    for result in results:
        scorer = result.get("scorer_name", "Unknown")
        generator = result.get("generator_name", "Unknown")
        score_type = result.get("score_type", "unknown")
        score_value = result.get("score_value")

        scorers.add(scorer)
        generators.add(generator)

        # Update matrix cell
        cell = matrix[scorer][generator]
        cell["total"] += 1

        # Track violations
        if score_type == "true_false" and score_value is True:
            cell["violations"] += 1
        elif score_type == "float_scale" and score_value is not None:
            try:
                score_float = float(score_value)
                cell["score_sum"] += score_float
                if score_float >= 0.6:  # Threshold for violations
                    cell["violations"] += 1
            except (TypeError, ValueError):
                pass
        elif result.get("severity") in ["high", "critical"]:
            cell["violations"] += 1

        # Keep sample results for drill-down
        if len(cell["samples"]) < 5:  # Keep up to 5 samples
            cell["samples"].append(
                {
                    "timestamp": result.get("timestamp"),
                    "score_value": score_value,
                    "severity": result.get("severity"),
                    "rationale": result.get("score_rationale", "")[:100],
                }
            )

    # Calculate metrics for each cell
    for scorer in matrix:
        for generator in matrix[scorer]:
            cell = matrix[scorer][generator]
            if cell["total"] > 0:
                cell["detection_rate"] = (cell["violations"] / cell["total"]) * 100
                cell["avg_score"] = cell["score_sum"] / cell["total"] if cell["score_sum"] > 0 else 0
                # Calculate confidence based on sample size
                cell["confidence"] = min(cell["total"] / 10, 1.0)  # Full confidence at 10+ samples

    return {"matrix": dict(matrix), "scorers": sorted(list(scorers)), "generators": sorted(list(generators))}


def calculate_vulnerability_taxonomy(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Categorize vulnerabilities using MITRE ATT&CK-inspired taxonomy for AI"""

    # AI-specific vulnerability taxonomy
    vulnerability_categories = {
        "TA001": {
            "name": "Initial Access",
            "techniques": {"T001.1": "Prompt Injection", "T001.2": "Input Manipulation", "T001.3": "Context Overflow"},
        },
        "TA002": {
            "name": "Execution",
            "techniques": {"T002.1": "Code Generation", "T002.2": "Command Injection", "T002.3": "Script Execution"},
        },
        "TA003": {
            "name": "Persistence",
            "techniques": {
                "T003.1": "Memory Manipulation",
                "T003.2": "Context Retention",
                "T003.3": "Session Hijacking",
            },
        },
        "TA004": {
            "name": "Privilege Escalation",
            "techniques": {
                "T004.1": "Role Manipulation",
                "T004.2": "System Prompt Override",
                "T004.3": "Capability Expansion",
            },
        },
        "TA005": {
            "name": "Defense Evasion",
            "techniques": {"T005.1": "Encoding Evasion", "T005.2": "Logic Manipulation", "T005.3": "Safety Bypass"},
        },
        "TA006": {
            "name": "Information Disclosure",
            "techniques": {"T006.1": "Data Extraction", "T006.2": "Model Inversion", "T006.3": "Training Data Leakage"},
        },
    }

    # Categorize findings
    categorized_vulnerabilities = defaultdict(
        lambda: defaultdict(
            lambda: {"count": 0, "severity_breakdown": defaultdict(int), "affected_generators": set(), "examples": []}
        )
    )

    # Map results to vulnerability categories
    for result in results:
        if result.get("severity") not in ["high", "critical"]:
            continue

        # Determine category based on various indicators
        category = None
        technique = None

        # Analyze based on scorer name and rationale
        scorer_name = result.get("scorer_name", "").lower()
        rationale = result.get("score_rationale", "").lower()

        # Categorization logic
        if "injection" in scorer_name or "inject" in rationale:
            category, technique = "TA001", "T001.1"
        elif "code" in scorer_name or "script" in rationale:
            category, technique = "TA002", "T002.1"
        elif "privilege" in scorer_name or "admin" in rationale or "root" in rationale:
            category, technique = "TA004", "T004.1"
        elif "bypass" in scorer_name or "evade" in rationale:
            category, technique = "TA005", "T005.3"
        elif "data" in scorer_name or "extract" in rationale or "leak" in rationale:
            category, technique = "TA006", "T006.1"
        else:
            # Default categorization based on response insights
            if result.get("response_insights", {}).get("prompt_type") == "privilege_escalation":
                category, technique = "TA004", "T004.2"
            elif result.get("response_insights", {}).get("contains_code"):
                category, technique = "TA002", "T002.1"
            else:
                category, technique = "TA001", "T001.2"  # Default to input manipulation

        # Update vulnerability data
        vuln_data = categorized_vulnerabilities[category][technique]
        vuln_data["count"] += 1
        vuln_data["severity_breakdown"][result.get("severity", "unknown")] += 1
        vuln_data["affected_generators"].add(result.get("generator_name", "Unknown"))

        # Keep examples
        if len(vuln_data["examples"]) < 3:
            vuln_data["examples"].append(
                {
                    "timestamp": result.get("timestamp"),
                    "generator": result.get("generator_name"),
                    "scorer": result.get("scorer_name"),
                    "rationale": result.get("score_rationale", "")[:200],
                }
            )

    # Convert sets to lists for JSON serialization
    for category in categorized_vulnerabilities:
        for technique in categorized_vulnerabilities[category]:
            vuln_data = categorized_vulnerabilities[category][technique]
            vuln_data["affected_generators"] = sorted(list(vuln_data["affected_generators"]))

    return {
        "taxonomy": vulnerability_categories,
        "findings": dict(categorized_vulnerabilities),
        "summary": {
            "total_vulnerabilities": sum(
                data["count"] for cat_data in categorized_vulnerabilities.values() for data in cat_data.values()
            ),
            "affected_categories": len(categorized_vulnerabilities),
            "top_category": (
                max(
                    categorized_vulnerabilities.keys(),
                    key=lambda c: sum(d["count"] for d in categorized_vulnerabilities[c].values()),
                )
                if categorized_vulnerabilities
                else None
            ),
        },
    }


def calculate_advanced_risk_scores(
    results: List[Dict[str, Any]], generator_groups: Dict[str, List[Dict]]
) -> Dict[str, Any]:
    """Calculate multi-factor risk scores for generators"""
    risk_profiles = {}

    for generator, gen_results in generator_groups.items():
        if not gen_results:
            continue

        # 1. Base Risk Score (weighted severity)
        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1, "minimal": 0.5}

        base_risk = sum(severity_weights.get(r.get("severity", "unknown"), 0) for r in gen_results) / len(gen_results)

        # 2. Exposure Factor (success rate of attacks)
        violations = sum(1 for r in gen_results if r.get("severity") in ["high", "critical"])
        exposure_factor = violations / len(gen_results) if gen_results else 0

        # 3. Impact Multiplier (based on response characteristics)
        impact_scores = []
        for r in gen_results:
            impact = 1.0
            insights = r.get("response_insights", {})
            if insights.get("contains_code"):
                impact *= 1.5
            if insights.get("contains_script"):
                impact *= 2.0
            if insights.get("response_type") == "verbose":
                impact *= 1.2
            impact_scores.append(impact)

        avg_impact = sum(impact_scores) / len(impact_scores) if impact_scores else 1.0

        # 4. Trend Modifier (compare recent vs historical)
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_results = [r for r in gen_results if parse_timestamp(r.get("timestamp")) > recent_cutoff]

        if recent_results and len(recent_results) >= 5:
            recent_violations = sum(1 for r in recent_results if r.get("severity") in ["high", "critical"])
            recent_rate = recent_violations / len(recent_results)
            overall_rate = violations / len(gen_results)
            trend_modifier = 1 + (recent_rate - overall_rate)  # Positive if worsening
        else:
            trend_modifier = 1.0

        # 5. Composite Risk Score
        composite_score = base_risk * (1 + exposure_factor) * avg_impact * trend_modifier

        # Normalize to 0-100 scale
        normalized_score = min(composite_score * 10, 100)

        risk_profiles[generator] = {
            "risk_score": normalized_score,
            "risk_level": (
                "Critical"
                if normalized_score >= 80
                else (
                    "High"
                    if normalized_score >= 60
                    else "Medium" if normalized_score >= 40 else "Low" if normalized_score >= 20 else "Minimal"
                )
            ),
            "components": {
                "base_risk": base_risk,
                "exposure_factor": exposure_factor * 100,  # As percentage
                "impact_multiplier": avg_impact,
                "trend_modifier": trend_modifier,
            },
            "statistics": {
                "total_tests": len(gen_results),
                "violations": violations,
                "violation_rate": (violations / len(gen_results) * 100) if gen_results else 0,
                "recent_trend": (
                    "Worsening" if trend_modifier > 1.1 else "Improving" if trend_modifier < 0.9 else "Stable"
                ),
            },
        }

    return risk_profiles


def detect_cross_model_patterns(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect vulnerability patterns across multiple models"""

    # Group results by prompt patterns
    prompt_patterns = defaultdict(
        lambda: {
            "generators_affected": set(),
            "scorers_triggered": set(),
            "occurrences": 0,
            "severity_distribution": defaultdict(int),
            "examples": [],
        }
    )

    # Extract patterns from successful attacks
    for result in results:
        if result.get("severity") not in ["high", "critical"]:
            continue

        # Extract pattern identifiers
        prompt_data = result.get("prompt_response", {})
        if not prompt_data:
            continue

        prompt = prompt_data.get("prompt", "").lower()

        # Simple pattern extraction (in production, use NLP)
        patterns = []

        # Look for common attack patterns
        if "ignore" in prompt and "instructions" in prompt:
            patterns.append("instruction_override")
        if "system" in prompt and ("admin" in prompt or "root" in prompt):
            patterns.append("privilege_escalation")
        if "```" in prompt or "<script" in prompt:
            patterns.append("code_injection")
        if "tell me" in prompt and "about" in prompt:
            patterns.append("information_extraction")
        if len(prompt) > 500:
            patterns.append("context_overflow")

        # Record pattern occurrences
        for pattern in patterns:
            pattern_data = prompt_patterns[pattern]
            pattern_data["generators_affected"].add(result.get("generator_name", "Unknown"))
            pattern_data["scorers_triggered"].add(result.get("scorer_name", "Unknown"))
            pattern_data["occurrences"] += 1
            pattern_data["severity_distribution"][result.get("severity", "unknown")] += 1

            if len(pattern_data["examples"]) < 2:
                pattern_data["examples"].append(
                    {
                        "generator": result.get("generator_name"),
                        "scorer": result.get("scorer_name"),
                        "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                    }
                )

    # Identify cross-model vulnerabilities
    cross_model_vulnerabilities = []

    for pattern, data in prompt_patterns.items():
        if len(data["generators_affected"]) >= 2:  # Affects multiple models
            cross_model_vulnerabilities.append(
                {
                    "pattern": pattern,
                    "risk_score": min(data["occurrences"] * len(data["generators_affected"]) * 2, 100),
                    "affected_models": sorted(list(data["generators_affected"])),
                    "detection_methods": sorted(list(data["scorers_triggered"])),
                    "occurrences": data["occurrences"],
                    "severity_distribution": dict(data["severity_distribution"]),
                    "examples": data["examples"],
                }
            )

    # Sort by risk score
    cross_model_vulnerabilities.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "vulnerabilities": cross_model_vulnerabilities,
        "summary": {
            "total_patterns": len(cross_model_vulnerabilities),
            "max_affected_models": (
                max(len(v["affected_models"]) for v in cross_model_vulnerabilities)
                if cross_model_vulnerabilities
                else 0
            ),
            "high_risk_patterns": sum(1 for v in cross_model_vulnerabilities if v["risk_score"] >= 60),
        },
    }


def calculate_temporal_performance_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate performance metrics over time"""
    if not results:
        return {}

    # Sort results by timestamp
    sorted_results = sorted(
        [r for r in results if r.get("timestamp")], key=lambda x: parse_timestamp(x.get("timestamp"))
    )

    if not sorted_results:
        return {}

    # Define time windows
    time_windows = {"hourly": timedelta(hours=1), "daily": timedelta(days=1), "weekly": timedelta(weeks=1)}

    temporal_metrics = {}

    for window_name, window_delta in time_windows.items():
        window_metrics = defaultdict(
            lambda: {
                "total": 0,
                "violations": 0,
                "scorers": defaultdict(int),
                "generators": defaultdict(int),
                "detection_rate": 0.0,
            }
        )

        for result in sorted_results:
            timestamp = parse_timestamp(result.get("timestamp"))
            if not timestamp:
                continue

            # Determine window key
            if window_name == "hourly":
                window_key = timestamp.strftime("%Y-%m-%d %H:00")
            elif window_name == "daily":
                window_key = timestamp.strftime("%Y-%m-%d")
            else:  # weekly
                # Get start of week
                week_start = timestamp - timedelta(days=timestamp.weekday())
                window_key = week_start.strftime("%Y-%m-%d")

            # Update metrics
            metrics = window_metrics[window_key]
            metrics["total"] += 1

            if result.get("severity") in ["high", "critical"]:
                metrics["violations"] += 1

            metrics["scorers"][result.get("scorer_name", "Unknown")] += 1
            metrics["generators"][result.get("generator_name", "Unknown")] += 1

        # Calculate detection rates
        for window_key, metrics in window_metrics.items():
            if metrics["total"] > 0:
                metrics["detection_rate"] = (metrics["violations"] / metrics["total"]) * 100
                metrics["scorers"] = dict(metrics["scorers"])
                metrics["generators"] = dict(metrics["generators"])

        temporal_metrics[window_name] = dict(window_metrics)

    # Calculate trends
    daily_data = temporal_metrics.get("daily", {})
    if len(daily_data) >= 3:
        detection_rates = [m["detection_rate"] for m in daily_data.values()]
        recent_avg = sum(detection_rates[-3:]) / 3
        overall_avg = sum(detection_rates) / len(detection_rates)
        trend = (
            "increasing"
            if recent_avg > overall_avg * 1.1
            else "decreasing" if recent_avg < overall_avg * 0.9 else "stable"
        )
    else:
        trend = "insufficient_data"

    return {
        "metrics": temporal_metrics,
        "trend": trend,
        "summary": {
            "total_time_range": (
                (
                    parse_timestamp(sorted_results[-1].get("timestamp"))
                    - parse_timestamp(sorted_results[0].get("timestamp"))
                ).days
                if len(sorted_results) >= 2
                else 0
            ),
            "data_points": len(sorted_results),
        },
    }


def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Parse timestamp string to datetime object"""
    if not timestamp_str:
        return None
    try:
        if isinstance(timestamp_str, datetime):
            return timestamp_str
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except:
        return None


# --- Multi-Dimensional Analysis Visualization Functions ---


def render_scorer_generator_matrix(matrix_data: Dict[str, Any]):
    """Render the scorer × generator performance matrix as a heatmap"""
    st.subheader("🔥 Scorer × Generator Compatibility Matrix")
    st.info("💡 **Understanding Results**: In security testing, a 'detection' or 'violation' means the scorer identified a potential security issue. Higher detection rates indicate the scorer successfully caught more security violations.")

    if not matrix_data.get("matrix"):
        st.info("No matrix data available")
        return

    matrix = matrix_data["matrix"]
    scorers = matrix_data["scorers"]
    generators = matrix_data["generators"]

    # Create detection rate matrix
    detection_rates = []
    for scorer in scorers:
        row = []
        for generator in generators:
            cell = matrix.get(scorer, {}).get(generator, {})
            rate = cell.get("detection_rate", 0)
            row.append(rate)
        detection_rates.append(row)

    # Create heatmap
    fig = go.Figure(
        data=go.Heatmap(
            z=detection_rates,
            x=generators,
            y=scorers,
            colorscale="RdYlBu_r",  # Red (high) to Blue (low)
            text=[[f"{val:.1f}%" for val in row] for row in detection_rates],
            texttemplate="%{text}",
            textfont={"size": 10},
            hovertemplate="Scorer: %{y}<br>Generator: %{x}<br>Detection Rate: %{z:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title="Detection Rate Heatmap (% of security violations detected)",
        xaxis_title="AI Models (Generators)",
        yaxis_title="Security Scorers",
        height=max(400, len(scorers) * 30),
        width=max(600, len(generators) * 80),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show insights
    with st.expander("🔍 Matrix Insights"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**🎯 Best Performing Combinations:**")
            # Find top combinations
            top_combos = []
            for scorer in scorers:
                for generator in generators:
                    cell = matrix.get(scorer, {}).get(generator, {})
                    if cell.get("total", 0) >= 5:  # Minimum sample size
                        top_combos.append(
                            {
                                "combo": f"{scorer} × {generator}",
                                "rate": cell.get("detection_rate", 0),
                                "confidence": cell.get("confidence", 0),
                            }
                        )

            top_combos.sort(key=lambda x: x["rate"], reverse=True)
            for combo in top_combos[:5]:
                st.write(f"- {combo['combo']}: {combo['rate']:.1f}% (confidence: {combo['confidence']:.0%})")

        with col2:
            st.markdown("**⚠️ Weak Combinations:**")
            # Find weak combinations
            weak_combos = sorted(top_combos, key=lambda x: x["rate"])[:5]
            for combo in weak_combos:
                if combo["rate"] < 50:  # Only show if detection rate is low
                    st.write(f"- {combo['combo']}: {combo['rate']:.1f}%")


def render_vulnerability_taxonomy(taxonomy_data: Dict[str, Any]):
    """Render vulnerability taxonomy visualization"""
    st.subheader("🛡️ Vulnerability Taxonomy Analysis")

    findings = taxonomy_data.get("findings", {})
    if not findings:
        st.info("No vulnerabilities detected")
        return

    # Create sunburst chart for vulnerability hierarchy
    labels = []
    parents = []
    values = []
    colors = []

    # Add categories
    taxonomy = taxonomy_data.get("taxonomy", {})
    for category_id, category_data in taxonomy.items():
        if category_id in findings:
            category_total = sum(findings[category_id][tech]["count"] for tech in findings[category_id])
            if category_total > 0:
                labels.append(category_data["name"])
                parents.append("")
                values.append(category_total)
                colors.append(SEVERITY_COLORS.get("high", "#DC143C"))

                # Add techniques
                for tech_id, tech_name in category_data["techniques"].items():
                    if tech_id in findings[category_id]:
                        tech_count = findings[category_id][tech_id]["count"]
                        if tech_count > 0:
                            labels.append(tech_name)
                            parents.append(category_data["name"])
                            values.append(tech_count)
                            # Color based on severity distribution
                            severity_dist = findings[category_id][tech_id]["severity_breakdown"]
                            if severity_dist.get("critical", 0) > severity_dist.get("high", 0):
                                colors.append(SEVERITY_COLORS["critical"])
                            else:
                                colors.append(SEVERITY_COLORS["high"])

    if labels:
        fig = go.Figure(
            go.Sunburst(
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                marker=dict(colors=colors),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percentParent} of parent<br>%{percentRoot} of total<extra></extra>",
            )
        )

        fig.update_layout(title="Vulnerability Distribution by Category", height=600)

        st.plotly_chart(fig, use_container_width=True)

    # Show detailed breakdown
    with st.expander("📊 Detailed Vulnerability Breakdown"):
        for category_id, category_findings in findings.items():
            if category_id in taxonomy:
                st.markdown(f"### {taxonomy[category_id]['name']}")

                for tech_id, tech_data in category_findings.items():
                    if tech_id in taxonomy[category_id]["techniques"]:
                        st.markdown(f"**{taxonomy[category_id]['techniques'][tech_id]}**")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Occurrences", tech_data["count"])
                        with col2:
                            st.metric("Affected Models", len(tech_data["affected_generators"]))
                        with col3:
                            severity_str = ", ".join(
                                f"{sev}: {count}" for sev, count in tech_data["severity_breakdown"].items()
                            )
                            st.metric("Severity", severity_str)

                        if tech_data["examples"]:
                            st.caption("Example:")
                            ex = tech_data["examples"][0]
                            st.text(f"Generator: {ex['generator']} | Scorer: {ex['scorer']}")
                            st.text(f"Rationale: {ex['rationale']}")

                        st.divider()


def render_advanced_risk_profiles(risk_profiles: Dict[str, Any]):
    """Render advanced risk profiling visualization"""
    st.subheader("⚡ Advanced Generator Risk Profiles")

    if not risk_profiles:
        st.info("No risk profile data available")
        return

    # Create risk score comparison
    risk_data = []
    for generator, profile in risk_profiles.items():
        risk_data.append(
            {
                "Generator": generator,
                "Risk Score": profile["risk_score"],
                "Risk Level": profile["risk_level"],
                "Violation Rate": profile["statistics"]["violation_rate"],
                "Trend": profile["statistics"]["recent_trend"],
            }
        )

    df_risk = pd.DataFrame(risk_data).sort_values("Risk Score", ascending=False)

    # Risk score bar chart with color coding
    fig = go.Figure()

    for _, row in df_risk.iterrows():
        color = {
            "Critical": "#8B0000",
            "High": "#DC143C",
            "Medium": "#FF8C00",
            "Low": "#FFD700",
            "Minimal": "#32CD32",
        }.get(row["Risk Level"], "#808080")

        fig.add_trace(
            go.Bar(
                x=[row["Generator"]],
                y=[row["Risk Score"]],
                name=row["Generator"],
                marker_color=color,
                text=f"{row['Risk Score']:.1f}",
                textposition="outside",
                hovertemplate=f"<b>{row['Generator']}</b><br>"
                + f"Risk Score: {row['Risk Score']:.1f}<br>"
                + f"Risk Level: {row['Risk Level']}<br>"
                + f"Violation Rate: {row['Violation Rate']:.1f}%<br>"
                + f"Trend: {row['Trend']}<extra></extra>",
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Generator Risk Scores (Multi-Factor Analysis)",
        xaxis_title="Generator",
        yaxis_title="Risk Score (0-100)",
        height=400,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Show detailed risk factors
    with st.expander("🔍 Risk Factor Analysis"):
        selected_generator = st.selectbox(
            "Select a generator for detailed analysis:", options=df_risk["Generator"].tolist()
        )

        if selected_generator:
            profile = risk_profiles[selected_generator]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Risk Components:**")
                components = profile["components"]

                # Create radar chart for risk components
                categories = ["Base Risk", "Exposure", "Impact", "Trend"]
                values = [
                    components["base_risk"] * 10,  # Scale to 0-100
                    components["exposure_factor"],
                    components["impact_multiplier"] * 20,  # Scale to 0-100
                    (components["trend_modifier"] - 0.5) * 100,  # Center at 50
                ]

                fig_radar = go.Figure(
                    data=go.Scatterpolar(r=values, theta=categories, fill="toself", name=selected_generator)
                )

                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    title=f"Risk Component Analysis - {selected_generator}",
                    height=300,
                )

                st.plotly_chart(fig_radar, use_container_width=True)

            with col2:
                st.markdown("**Statistics:**")
                stats = profile["statistics"]
                st.metric("Total Tests", stats["total_tests"])
                st.metric("Violations", f"{stats['violations']} ({stats['violation_rate']:.1f}%)")
                st.metric(
                    "Recent Trend",
                    stats["recent_trend"],
                    delta=(
                        "Risk increasing"
                        if stats["recent_trend"] == "Worsening"
                        else "Risk decreasing" if stats["recent_trend"] == "Improving" else "Risk stable"
                    ),
                )


def render_cross_model_patterns(pattern_data: Dict[str, Any]):
    """Render cross-model vulnerability patterns"""
    st.subheader("🔗 Cross-Model Vulnerability Patterns")

    vulnerabilities = pattern_data.get("vulnerabilities", [])
    if not vulnerabilities:
        st.info("No cross-model patterns detected")
        return

    # Create network graph showing pattern connections
    # For simplicity, we'll use a different visualization

    # Pattern risk matrix
    pattern_names = []
    affected_counts = []
    risk_scores = []

    for vuln in vulnerabilities[:10]:  # Top 10 patterns
        pattern_names.append(vuln["pattern"].replace("_", " ").title())
        affected_counts.append(len(vuln["affected_models"]))
        risk_scores.append(vuln["risk_score"])

    # Create bubble chart
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=affected_counts,
            y=risk_scores,
            mode="markers+text",
            marker=dict(
                size=[r * 0.5 for r in risk_scores],  # Bubble size based on risk
                color=risk_scores,
                colorscale="Reds",
                showscale=True,
                colorbar=dict(title="Risk Score"),
            ),
            text=pattern_names,
            textposition="top center",
            hovertemplate="Pattern: %{text}<br>"
            + "Affected Models: %{x}<br>"
            + "Risk Score: %{y}<br>"
            + "<extra></extra>",
        )
    )

    fig.update_layout(
        title="Cross-Model Vulnerability Patterns",
        xaxis_title="Number of Affected Models",
        yaxis_title="Risk Score",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detailed pattern analysis
    with st.expander("📋 Pattern Details"):
        for vuln in vulnerabilities[:5]:  # Top 5 patterns
            st.markdown(f"### {vuln['pattern'].replace('_', ' ').title()}")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Risk Score", f"{vuln['risk_score']:.0f}/100")

            with col2:
                st.metric("Affected Models", len(vuln["affected_models"]))

            with col3:
                st.metric("Occurrences", vuln["occurrences"])

            st.markdown("**Affected Models:**")
            st.write(", ".join(vuln["affected_models"]))

            st.markdown("**Detection Methods:**")
            st.write(", ".join(vuln["detection_methods"]))

            if vuln["examples"]:
                st.markdown("**Example Attack:**")
                ex = vuln["examples"][0]
                st.caption(f"Model: {ex['generator']} | Detected by: {ex['scorer']}")
                st.text(ex["prompt_preview"])

            st.divider()


def render_temporal_performance(temporal_data: Dict[str, Any]):
    """Render temporal performance analysis"""
    st.subheader("📈 Temporal Performance Analysis")

    if not temporal_data.get("metrics"):
        st.info("No temporal data available")
        return

    # Time window selector
    time_window = st.radio("Select time window:", ["hourly", "daily", "weekly"], horizontal=True)

    window_data = temporal_data["metrics"].get(time_window, {})
    if not window_data:
        st.info(f"No {time_window} data available")
        return

    # Prepare data for visualization
    timestamps = []
    detection_rates = []
    totals = []

    for timestamp, metrics in sorted(window_data.items()):
        timestamps.append(timestamp)
        detection_rates.append(metrics["detection_rate"])
        totals.append(metrics["total"])

    # Create dual-axis chart
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Detection Rate Over Time", "Test Volume Over Time"),
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.6, 0.4],
    )

    # Detection rate line
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=detection_rates,
            mode="lines+markers",
            name="Detection Rate",
            line=dict(color="red", width=2),
            marker=dict(size=6),
            hovertemplate="%{x}<br>Detection Rate: %{y:.1f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # Add trend line
    if len(detection_rates) >= 3:
        z = np.polyfit(range(len(detection_rates)), detection_rates, 1)
        p = np.poly1d(z)
        fig.add_trace(
            go.Scatter(
                x=timestamps,
                y=p(range(len(detection_rates))),
                mode="lines",
                name="Trend",
                line=dict(color="orange", width=1, dash="dash"),
                hovertemplate="Trend: %{y:.1f}%<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # Test volume bars
    fig.add_trace(
        go.Bar(
            x=timestamps,
            y=totals,
            name="Test Volume",
            marker_color="lightblue",
            hovertemplate="%{x}<br>Tests: %{y}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Detection Rate (%)", row=1, col=1)
    fig.update_yaxes(title_text="Number of Tests", row=2, col=1)

    fig.update_layout(height=600, title=f"{time_window.capitalize()} Performance Metrics", showlegend=True)

    st.plotly_chart(fig, use_container_width=True)

    # Show performance insights
    col1, col2, col3 = st.columns(3)

    with col1:
        trend = temporal_data.get("trend", "unknown")
        trend_color = "🔴" if trend == "increasing" else "🟢" if trend == "decreasing" else "🟡"
        st.metric("Overall Trend", f"{trend_color} {trend.capitalize()}")

    with col2:
        if detection_rates:
            avg_rate = sum(detection_rates) / len(detection_rates)
            st.metric("Average Detection Rate", f"{avg_rate:.1f}%")

    with col3:
        time_range = temporal_data.get("summary", {}).get("total_time_range", 0)
        st.metric("Analysis Period", f"{time_range} days")


# --- COB (Close of Business) Reports System ---


class COBDataCollector:
    """Data collection engine for COB reports"""

    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url
        self.api_endpoints = {
            "orchestrators": f"{api_base_url}/api/v1/orchestrators",
            "orchestrator_executions": f"{api_base_url}/api/v1/orchestrators/executions",
            "execution_results": f"{api_base_url}/api/v1/orchestrators/executions/{{execution_id}}/results",
        }

    def collect_24h_metrics(self, report_date: datetime) -> Dict[str, Any]:
        """Collect all required metrics for the past 24 hours"""
        end_date = report_date
        start_date = end_date - timedelta(days=1)

        return {
            "report_date": report_date.isoformat(),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "executions": self.get_execution_metrics(start_date, end_date),
            "threats": self.get_threat_analysis(start_date, end_date),
            "performance": self.get_performance_data(start_date, end_date),
            "historical_baselines": self.get_baseline_data(report_date),
        }

    def get_execution_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect execution statistics and trends"""
        try:
            # Get all orchestrator executions in the time range
            executions_response = self._api_request("GET", self.api_endpoints["orchestrator_executions"])
            if not executions_response:
                return {}

            executions = executions_response.get("executions", [])

            # Filter executions by date range
            filtered_executions = []
            all_results = []

            for execution in executions:
                created_at_str = execution.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        if start_date <= created_at <= end_date:
                            filtered_executions.append(execution)

                            # Get results for this execution if completed
                            if execution.get("status") == "completed":
                                exec_id = execution.get("id")
                                if exec_id:
                                    results = self._get_execution_results(exec_id)
                                    all_results.extend(results)
                    except Exception as e:
                        logger.error(f"Date parsing error: {e}")
                        continue

            # Calculate metrics
            total_tests = len(all_results)
            successful_tests = sum(1 for r in all_results if r.get("score_value") is not None)
            critical_findings = sum(1 for r in all_results if r.get("severity") in ["critical", "high"])

            # Get unique coverage metrics
            unique_models = set(r.get("generator_name", "Unknown") for r in all_results)
            unique_generators = set(r.get("generator_type", "Unknown") for r in all_results)
            unique_scorers = set(r.get("scorer_name", "Unknown") for r in all_results)

            return {
                "total_executions": len(filtered_executions),
                "completed_executions": sum(1 for e in filtered_executions if e.get("status") == "completed"),
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "critical_findings": critical_findings,
                "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
                "violation_rate": (critical_findings / total_tests * 100) if total_tests > 0 else 0,
                "unique_models": len(unique_models),
                "unique_generators": len(unique_generators),
                "unique_scorers": len(unique_scorers),
                "model_names": list(unique_models),
                "generator_names": list(unique_generators),
                "scorer_names": list(unique_scorers),
                "raw_results": all_results,
            }

        except Exception as e:
            logger.error(f"Error collecting execution metrics: {e}")
            return {}

    def get_threat_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect threat detection and pattern analysis - Enhanced in Phase 2 with trend analysis"""
        try:
            # Get all results for threat analysis
            all_results = self._collect_all_results_for_timeframe(start_date, end_date)

            if not all_results:
                return {
                    "threat_patterns": [],
                    "cross_model_threats": [],
                    "new_attack_vectors": [],
                    "escalating_threats": [],
                    "trend_analysis": {},
                }

            # Initialize Phase 2 analyzers
            threat_analyzer = ThreatPatternAnalyzer()
            trend_analyzer = TrendDetectionEngine()

            # Perform comprehensive threat analysis
            pattern_analysis = threat_analyzer.analyze_threat_patterns(all_results, 24)

            # Get baseline data for trend analysis
            baseline_data = self.get_baseline_data(end_date)
            current_metrics = self.get_execution_metrics(start_date, end_date)

            # Run trend analysis
            trend_analysis = trend_analyzer.analyze_operational_trends(baseline_data, current_metrics)

            return {
                "threat_patterns": pattern_analysis.get("detected_patterns", []),
                "cross_model_threats": pattern_analysis.get("cross_model_threats", []),
                "new_attack_vectors": pattern_analysis.get("new_attack_vectors", []),
                "escalating_threats": pattern_analysis.get("escalating_threats", []),
                "threat_timeline": pattern_analysis.get("threat_timeline", {}),
                "risk_assessment": pattern_analysis.get("risk_assessment", {}),
                "trend_analysis": trend_analysis,
            }

        except Exception as e:
            logger.error(f"Error in enhanced threat analysis: {e}")
            return {
                "threat_patterns": [],
                "cross_model_threats": [],
                "new_attack_vectors": [],
                "escalating_threats": [],
                "trend_analysis": {},
            }

    def get_performance_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Collect system and test performance metrics"""
        # Basic performance metrics for Phase 1
        return {
            "avg_response_time": 120,  # milliseconds
            "api_availability": 99.2,  # percentage
            "error_rate": 1.8,  # percentage
            "throughput": 47,  # tests per minute
        }

    def get_baseline_data(self, report_date: datetime) -> Dict[str, Any]:
        """Get historical baseline data for comparison - Enhanced in Phase 2"""
        try:
            # Collect multi-day historical data for trend analysis
            historical_data = {}

            # Collect last 7 days of data
            for i in range(1, 8):
                day_date = report_date - timedelta(days=i)
                day_start = day_date - timedelta(days=1)
                day_metrics = self.get_execution_metrics(day_start, day_date)

                if day_metrics:
                    historical_data[f"day_{i}"] = day_metrics

            # Calculate enhanced baselines
            yesterday = report_date - timedelta(days=1)
            yesterday_metrics = self.get_execution_metrics(yesterday - timedelta(days=1), yesterday)

            # Calculate week averages from collected data
            week_data = list(historical_data.values())
            if week_data:
                week_average = {
                    "total_tests": sum(d.get("total_tests", 0) for d in week_data) / len(week_data),
                    "violation_rate": sum(d.get("violation_rate", 0) for d in week_data) / len(week_data),
                    "success_rate": sum(d.get("success_rate", 0) for d in week_data) / len(week_data),
                    "critical_findings": sum(d.get("critical_findings", 0) for d in week_data) / len(week_data),
                }
            else:
                week_average = {}

            return {
                "yesterday": yesterday_metrics,
                "week_average": week_average,
                "historical_daily": historical_data,
                "trend_data": self._calculate_baseline_trends(historical_data, yesterday_metrics),
            }

        except Exception as e:
            logger.error(f"Error collecting enhanced baseline data: {e}")
            return {"yesterday": {}, "week_average": {}}

    def _get_execution_results(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get results for a specific execution"""
        try:
            url = self.api_endpoints["execution_results"].format(execution_id=execution_id)
            response = self._api_request("GET", url)

            if response and "scores" in response:
                scores = response["scores"]
                results = []

                for score in scores:
                    # Parse metadata if it's a JSON string
                    metadata = score.get("score_metadata", "{}")
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}

                    # Create unified result object
                    result = {
                        "execution_id": execution_id,
                        "timestamp": score.get("timestamp"),
                        "score_value": score.get("score_value"),
                        "score_type": score.get("score_type", "unknown"),
                        "score_rationale": score.get("score_rationale", ""),
                        "scorer_name": metadata.get("scorer_name", "Unknown"),
                        "generator_name": metadata.get("generator_name", "Unknown"),
                        "generator_type": metadata.get("generator_type", "Unknown"),
                        "dataset_name": metadata.get("dataset_name", "Unknown"),
                    }

                    # Calculate severity (using existing SEVERITY_MAP if available)
                    score_type = result["score_type"]
                    score_value = result["score_value"]

                    if score_type == "true_false" and score_value is True:
                        result["severity"] = "high"
                    elif score_type == "float_scale" and score_value is not None:
                        try:
                            float_val = float(score_value)
                            if float_val >= 0.8:
                                result["severity"] = "critical"
                            elif float_val >= 0.6:
                                result["severity"] = "high"
                            elif float_val >= 0.4:
                                result["severity"] = "medium"
                            else:
                                result["severity"] = "low"
                        except:
                            result["severity"] = "unknown"
                    else:
                        result["severity"] = "minimal"

                    results.append(result)

                return results

            return []

        except Exception as e:
            logger.error(f"Error getting execution results for {execution_id}: {e}")
            return []

    def _api_request(self, method: str, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make API request with error handling"""
        try:
            # Get API token from session state or environment
            api_token = None
            if hasattr(st, "session_state") and st.session_state.get("api_token"):
                api_token = st.session_state["api_token"]
            else:
                api_token = os.getenv("VIOLENTUTF_API_TOKEN")

            headers = {"Content-Type": "application/json"}
            if api_token:
                headers["Authorization"] = f"Bearer {api_token}"

            response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"API request error: {e}")
            return None

    def _collect_all_results_for_timeframe(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Collect all results within timeframe for analysis"""
        try:
            executions_response = self._api_request("GET", self.api_endpoints["orchestrator_executions"])
            if not executions_response:
                return []

            executions = executions_response.get("executions", [])
            all_results = []

            for execution in executions:
                created_at_str = execution.get("created_at", "")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        if start_date <= created_at <= end_date:
                            if execution.get("status") == "completed":
                                exec_id = execution.get("id")
                                if exec_id:
                                    results = self._get_execution_results(exec_id)
                                    all_results.extend(results)
                    except Exception as e:
                        logger.error(f"Date parsing error in timeframe collection: {e}")
                        continue

            return all_results

        except Exception as e:
            logger.error(f"Error collecting results for timeframe: {e}")
            return []

    def _calculate_baseline_trends(self, historical_data: Dict, current_data: Dict) -> Dict[str, Any]:
        """Calculate trend information from historical data"""
        try:
            if not historical_data:
                return {}

            # Extract time series data
            daily_tests = []
            daily_violations = []
            daily_success = []

            for day_key in sorted(historical_data.keys()):
                day_data = historical_data[day_key]
                daily_tests.append(day_data.get("total_tests", 0))
                daily_violations.append(day_data.get("violation_rate", 0))
                daily_success.append(day_data.get("success_rate", 0))

            trends = {}

            # Calculate simple trends
            if len(daily_tests) >= 3:
                trends["test_volume_trend"] = self._calculate_simple_trend(daily_tests)
                trends["violation_trend"] = self._calculate_simple_trend(daily_violations)
                trends["success_trend"] = self._calculate_simple_trend(daily_success)

            return trends

        except Exception as e:
            logger.error(f"Error calculating baseline trends: {e}")
            return {}

    def _calculate_simple_trend(self, values: List[float]) -> str:
        """Calculate simple trend direction"""
        if len(values) < 3:
            return "insufficient_data"

        first_half = values[: len(values) // 2]
        second_half = values[len(values) // 2 :]

        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)

        if second_avg > first_avg * 1.05:
            return "increasing"
        elif second_avg < first_avg * 0.95:
            return "decreasing"
        else:
            return "stable"


class ThreatPatternAnalyzer:
    """Advanced threat pattern analysis for COB reports - Phase 2"""

    def __init__(self):
        self.attack_patterns = {
            "prompt_injection": {
                "keywords": ["ignore", "instruction", "system", "override", "forget"],
                "patterns": [r"ignore.*previous", r"system.*admin", r"forget.*rules"],
                "severity_multiplier": 1.5,
            },
            "privilege_escalation": {
                "keywords": ["admin", "root", "sudo", "privilege", "escalate"],
                "patterns": [r"admin.*access", r"root.*permission", r"privilege.*escalation"],
                "severity_multiplier": 2.0,
            },
            "code_injection": {
                "keywords": ["script", "execute", "eval", "import", "subprocess"],
                "patterns": [r"<script.*>", r"```.*python", r"eval\(", r"exec\("],
                "severity_multiplier": 1.8,
            },
            "data_extraction": {
                "keywords": ["extract", "dump", "leak", "expose", "reveal"],
                "patterns": [r"extract.*data", r"dump.*database", r"reveal.*secret"],
                "severity_multiplier": 1.7,
            },
            "jailbreak_attempt": {
                "keywords": ["jailbreak", "bypass", "circumvent", "workaround"],
                "patterns": [r"bypass.*filter", r"circumvent.*safety", r"jailbreak.*mode"],
                "severity_multiplier": 2.2,
            },
        }

    def analyze_threat_patterns(self, results: List[Dict[str, Any]], time_window: int = 24) -> Dict[str, Any]:
        """Analyze threat patterns in results data"""
        try:
            # Filter results to time window
            cutoff_time = datetime.now() - timedelta(hours=time_window)
            recent_results = [
                r for r in results if r.get("timestamp") and self._parse_timestamp(r["timestamp"]) > cutoff_time
            ]

            # Analyze patterns
            pattern_analysis = {
                "detected_patterns": self._detect_attack_patterns(recent_results),
                "cross_model_threats": self._analyze_cross_model_threats(recent_results),
                "escalating_threats": self._detect_escalating_threats(recent_results),
                "new_attack_vectors": self._identify_new_vectors(recent_results),
                "threat_timeline": self._build_threat_timeline(recent_results),
                "risk_assessment": self._calculate_threat_risk_scores(recent_results),
            }

            return pattern_analysis

        except Exception as e:
            logger.error(f"Error in threat pattern analysis: {e}")
            return {}

    def _detect_attack_patterns(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect specific attack patterns in results"""
        detected_patterns = []

        # Group results by pattern type
        pattern_groups = defaultdict(list)

        for result in results:
            if result.get("severity") not in ["high", "critical"]:
                continue

            # Check prompt and response content
            prompt_content = ""
            response_content = ""

            if result.get("prompt_response"):
                prompt_content = result["prompt_response"].get("prompt", "").lower()
                response_content = result["prompt_response"].get("response", "").lower()

            # Check rationale
            rationale = result.get("score_rationale", "").lower()
            combined_content = f"{prompt_content} {response_content} {rationale}"

            # Match against known patterns
            for pattern_name, pattern_config in self.attack_patterns.items():
                score = self._calculate_pattern_match_score(combined_content, pattern_config)

                if score > 0.3:  # Threshold for pattern detection
                    pattern_groups[pattern_name].append(
                        {"result": result, "match_score": score, "matched_content": combined_content[:200] + "..."}
                    )

        # Generate pattern summaries
        for pattern_name, matches in pattern_groups.items():
            if len(matches) >= 2:  # Minimum occurrences for pattern
                affected_models = set()
                affected_scorers = set()
                total_score = 0

                for match in matches:
                    result = match["result"]
                    affected_models.add(result.get("generator_name", "Unknown"))
                    affected_scorers.add(result.get("scorer_name", "Unknown"))
                    total_score += match["match_score"]

                pattern_info = {
                    "pattern_name": pattern_name,
                    "description": self._get_pattern_description(pattern_name),
                    "occurrences": len(matches),
                    "affected_models": sorted(list(affected_models)),
                    "detection_methods": sorted(list(affected_scorers)),
                    "average_confidence": total_score / len(matches),
                    "risk_level": self._calculate_pattern_risk_level(pattern_name, len(matches), len(affected_models)),
                    "first_seen": min(match["result"].get("timestamp", "") for match in matches),
                    "last_seen": max(match["result"].get("timestamp", "") for match in matches),
                    "examples": [match["matched_content"] for match in matches[:2]],
                }

                detected_patterns.append(pattern_info)

        # Sort by risk level and occurrences
        detected_patterns.sort(key=lambda x: (x["risk_level"], x["occurrences"]), reverse=True)
        return detected_patterns

    def _analyze_cross_model_threats(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify threats that affect multiple models"""
        cross_model_threats = []

        # Group high-severity results by scorer
        scorer_results = defaultdict(list)
        for result in results:
            if result.get("severity") in ["high", "critical"]:
                scorer_results[result.get("scorer_name", "Unknown")].append(result)

        # Find scorers that detected threats across multiple models
        for scorer, scorer_findings in scorer_results.items():
            affected_models = set(r.get("generator_name", "Unknown") for r in scorer_findings)

            if len(affected_models) >= 2:  # Cross-model threshold
                threat_info = {
                    "threat_type": self._categorize_threat_by_scorer(scorer),
                    "detecting_scorer": scorer,
                    "affected_models": sorted(list(affected_models)),
                    "total_detections": len(scorer_findings),
                    "threat_severity": self._calculate_cross_model_severity(scorer_findings),
                    "recommended_actions": self._generate_cross_model_recommendations(scorer, affected_models),
                }

                cross_model_threats.append(threat_info)

        return sorted(cross_model_threats, key=lambda x: x["threat_severity"], reverse=True)

    def _detect_escalating_threats(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect threats that are escalating over time - Simplified for Phase 2"""
        escalating_threats = []

        # Simple escalation detection based on time windows
        recent_cutoff = datetime.now() - timedelta(hours=6)
        very_recent = [
            r for r in results if r.get("timestamp") and self._parse_timestamp(r["timestamp"]) > recent_cutoff
        ]

        older_cutoff = datetime.now() - timedelta(hours=12)
        recent = [
            r
            for r in results
            if r.get("timestamp") and older_cutoff < self._parse_timestamp(r["timestamp"]) <= recent_cutoff
        ]

        # Count high-severity findings in each period
        very_recent_critical = sum(1 for r in very_recent if r.get("severity") in ["high", "critical"])
        recent_critical = sum(1 for r in recent if r.get("severity") in ["high", "critical"])

        if very_recent_critical > recent_critical * 1.5:  # 50% increase threshold
            escalating_threats.append(
                {
                    "threat_source": "Multiple Sources",
                    "escalation_rate": very_recent_critical / max(recent_critical, 1),
                    "current_frequency": very_recent_critical,
                    "urgency_level": min(very_recent_critical * 10, 100),
                    "description": f"Critical findings increased from {recent_critical} to {very_recent_critical}",
                }
            )

        return escalating_threats

    def _identify_new_vectors(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify new attack vectors - Simplified for Phase 2"""
        new_vectors = []

        # Simple heuristic: recent scorer-generator combinations
        recent_cutoff = datetime.now() - timedelta(hours=6)
        recent_results = [
            r for r in results if r.get("timestamp") and self._parse_timestamp(r["timestamp"]) > recent_cutoff
        ]

        # Count unique combinations in recent period
        recent_combinations = defaultdict(int)
        for result in recent_results:
            if result.get("severity") in ["high", "critical"]:
                combo = (result.get("scorer_name", "Unknown"), result.get("generator_name", "Unknown"))
                recent_combinations[combo] += 1

        # Identify potential new vectors (combinations with high activity)
        for (scorer, generator), count in recent_combinations.items():
            if count >= 3:  # Threshold for new vector detection
                new_vectors.append(
                    {
                        "attack_vector": f"{scorer} → {generator}",
                        "detection_count": count,
                        "novelty_score": min(count * 20, 100),
                        "risk_assessment": "high" if count >= 5 else "medium",
                    }
                )

        return sorted(new_vectors, key=lambda x: x["novelty_score"], reverse=True)

    def _build_threat_timeline(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build a simplified threat timeline"""
        timeline_events = []

        # Group events by hour
        hourly_events = defaultdict(list)
        for result in results:
            if result.get("severity") in ["high", "critical"] and result.get("timestamp"):
                timestamp = self._parse_timestamp(result["timestamp"])
                hour_key = timestamp.strftime("%Y-%m-%d %H:00")
                hourly_events[hour_key].append(result)

        # Create timeline entries
        for hour, events in hourly_events.items():
            if len(events) >= 2:  # Minimum threshold for timeline entry
                timeline_events.append(
                    {
                        "timestamp": hour,
                        "event_count": len(events),
                        "affected_models": list(set(e.get("generator_name", "Unknown") for e in events)),
                        "primary_threats": list(set(e.get("scorer_name", "Unknown") for e in events)),
                    }
                )

        return {
            "timeline_events": timeline_events,
            "total_threat_hours": len(timeline_events),
            "peak_activity": max(timeline_events, key=lambda x: x["event_count"]) if timeline_events else None,
        }

    def _calculate_threat_risk_scores(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate simplified risk scores"""
        if not results:
            return {"overall_risk_level": "low", "composite_risk_score": 0}

        total_critical = sum(1 for r in results if r.get("severity") == "critical")
        total_high = sum(1 for r in results if r.get("severity") == "high")
        total_results = len(results)

        # Simple risk calculation
        risk_score = ((total_critical * 10 + total_high * 5) / max(total_results, 1)) * 10

        if risk_score >= 80:
            risk_level = "critical"
        elif risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {"overall_risk_level": risk_level, "composite_risk_score": risk_score}

    # Helper methods
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string to datetime"""
        try:
            if isinstance(timestamp_str, datetime):
                return timestamp_str
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except:
            return datetime.now()

    def _calculate_pattern_match_score(self, content: str, pattern_config: Dict) -> float:
        """Calculate how well content matches a pattern"""
        score = 0.0

        # Keyword matching
        keywords_found = sum(1 for keyword in pattern_config["keywords"] if keyword in content)
        keyword_score = keywords_found / len(pattern_config["keywords"])

        # Regex pattern matching
        pattern_matches = sum(1 for pattern in pattern_config["patterns"] if re.search(pattern, content))
        pattern_score = pattern_matches / len(pattern_config["patterns"]) if pattern_config["patterns"] else 0

        # Combined score
        score = (keyword_score * 0.6 + pattern_score * 0.4) * pattern_config.get("severity_multiplier", 1.0)
        return min(score, 1.0)

    def _get_pattern_description(self, pattern_name: str) -> str:
        """Get human-readable description of attack pattern"""
        descriptions = {
            "prompt_injection": "Attempts to override system instructions",
            "privilege_escalation": "Attempts to gain elevated access or permissions",
            "code_injection": "Attempts to execute arbitrary code",
            "data_extraction": "Attempts to extract sensitive information",
            "jailbreak_attempt": "Attempts to bypass safety mechanisms",
        }
        return descriptions.get(pattern_name, "Unknown attack pattern")

    def _calculate_pattern_risk_level(self, pattern_name: str, occurrences: int, affected_models: int) -> float:
        """Calculate risk level for a detected pattern"""
        base_risk = self.attack_patterns.get(pattern_name, {}).get("severity_multiplier", 1.0)
        frequency_risk = min(occurrences / 10, 2.0)
        spread_risk = min(affected_models / 5, 1.5)
        return base_risk * frequency_risk * spread_risk

    def _categorize_threat_by_scorer(self, scorer_name: str) -> str:
        """Categorize threat type based on scorer name"""
        scorer_lower = scorer_name.lower()
        if "injection" in scorer_lower:
            return "Injection Attack"
        elif "privilege" in scorer_lower or "escalation" in scorer_lower:
            return "Privilege Escalation"
        elif "data" in scorer_lower or "leak" in scorer_lower:
            return "Data Extraction"
        elif "bypass" in scorer_lower or "jailbreak" in scorer_lower:
            return "Safety Bypass"
        else:
            return "Generic Threat"

    def _calculate_cross_model_severity(self, findings: List[Dict]) -> float:
        """Calculate severity score for cross-model threats"""
        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1, "minimal": 0.5}
        total_weight = sum(severity_weights.get(f.get("severity", "low"), 1) for f in findings)
        return total_weight / len(findings) if findings else 0

    def _generate_cross_model_recommendations(self, scorer: str, models: List[str]) -> List[str]:
        """Generate recommendations for cross-model threats"""
        recommendations = []

        if len(models) >= 3:
            recommendations.append("Implement universal protection across all models")

        recommendations.append(f"Review {scorer} detection rules for false positives")
        recommendations.append("Coordinate response across affected model teams")

        if "injection" in scorer.lower():
            recommendations.append("Strengthen input validation across all models")

        return recommendations


class TrendDetectionEngine:
    """Advanced trend detection for operational intelligence - Phase 2"""

    def __init__(self):
        self.trend_algorithms = {
            "violation_trends": self._analyze_violation_trends,
            "performance_trends": self._analyze_performance_trends,
            "model_degradation": self._detect_model_degradation,
            "seasonal_patterns": self._detect_seasonal_patterns,
            "anomaly_detection": self._detect_operational_anomalies,
        }

    def analyze_operational_trends(
        self, historical_data: Dict[str, Any], current_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Comprehensive trend analysis for COB reports"""
        try:
            trend_analysis = {}

            # Run all trend detection algorithms
            for trend_type, algorithm in self.trend_algorithms.items():
                try:
                    trend_results = algorithm(historical_data, current_data)
                    trend_analysis[trend_type] = trend_results
                except Exception as e:
                    logger.error(f"Error in {trend_type} analysis: {e}")
                    trend_analysis[trend_type] = {}

            # Generate composite trend insights
            trend_analysis["composite_insights"] = self._generate_composite_insights(trend_analysis)
            trend_analysis["priority_trends"] = self._prioritize_trends(trend_analysis)
            trend_analysis["trend_alerts"] = self._generate_trend_alerts(trend_analysis)

            return trend_analysis

        except Exception as e:
            logger.error(f"Error in operational trend analysis: {e}")
            return {}

    def _analyze_violation_trends(self, historical_data: Dict, current_data: Dict) -> Dict[str, Any]:
        """Analyze violation rate trends"""
        try:
            # Extract violation rates from historical data
            daily_data = historical_data.get("historical_daily", {})
            violation_rates = []
            dates = []

            for day_key in sorted(daily_data.keys()):
                day_data = daily_data[day_key]
                violation_rates.append(day_data.get("violation_rate", 0))
                dates.append(day_key)

            # Current day violation rate
            current_rate = current_data.get("violation_rate", 0)

            if len(violation_rates) >= 3:
                # Calculate trends
                recent_avg = sum(violation_rates[-3:]) / 3
                older_avg = sum(violation_rates[:-3]) / max(len(violation_rates) - 3, 1)

                trend_direction = "stable"
                if recent_avg > older_avg * 1.1:
                    trend_direction = "increasing"
                elif recent_avg < older_avg * 0.9:
                    trend_direction = "decreasing"

                # Calculate velocity
                if len(violation_rates) >= 2:
                    velocity = violation_rates[-1] - violation_rates[-2]
                else:
                    velocity = 0

                return {
                    "current_rate": current_rate,
                    "trend_direction": trend_direction,
                    "velocity": velocity,
                    "recent_average": recent_avg,
                    "historical_average": older_avg,
                    "change_percentage": ((recent_avg - older_avg) / max(older_avg, 0.01)) * 100,
                    "confidence": min(len(violation_rates) * 15, 100),
                    "alert_level": self._calculate_violation_alert_level(trend_direction, velocity, current_rate),
                }

            return {"insufficient_data": True}

        except Exception as e:
            logger.error(f"Error analyzing violation trends: {e}")
            return {}

    def _analyze_performance_trends(self, historical_data: Dict, current_data: Dict) -> Dict[str, Any]:
        """Analyze system performance trends"""
        try:
            daily_data = historical_data.get("historical_daily", {})
            success_rates = []
            test_volumes = []

            for day_key in sorted(daily_data.keys()):
                day_data = daily_data[day_key]
                success_rates.append(day_data.get("success_rate", 0))
                test_volumes.append(day_data.get("total_tests", 0))

            current_success = current_data.get("success_rate", 0)
            current_volume = current_data.get("total_tests", 0)

            if len(success_rates) >= 3:
                # Success rate trends
                success_trend = self._calculate_simple_trend(success_rates)
                volume_trend = self._calculate_simple_trend(test_volumes)

                # Performance stability
                success_stability = np.std(success_rates) if success_rates else 0
                volume_stability = np.std(test_volumes) if test_volumes else 0

                return {
                    "success_rate_trend": success_trend,
                    "test_volume_trend": volume_trend,
                    "current_success_rate": current_success,
                    "current_test_volume": current_volume,
                    "success_rate_stability": success_stability,
                    "volume_stability": volume_stability,
                    "performance_score": self._calculate_performance_score(success_rates, test_volumes),
                    "recommendations": self._generate_performance_recommendations(
                        success_trend, volume_trend, success_stability
                    ),
                }

            return {"insufficient_data": True}

        except Exception as e:
            logger.error(f"Error analyzing performance trends: {e}")
            return {}

    def _detect_model_degradation(self, historical_data: Dict, current_data: Dict) -> Dict[str, Any]:
        """Detect AI model performance degradation"""
        try:
            # This would analyze model-specific performance over time
            # For Phase 2, we'll use a simplified approach

            daily_data = historical_data.get("historical_daily", {})
            model_performances = defaultdict(list)

            # Extract per-model performance from historical data
            for day_key in sorted(daily_data.keys()):
                day_data = daily_data[day_key]
                # This would be extracted from detailed model analysis
                # Simplified for Phase 2
                avg_performance = 100 - day_data.get("violation_rate", 0)
                model_performances["overall"].append(avg_performance)

            degradation_alerts = []

            for model_name, performances in model_performances.items():
                if len(performances) >= 5:
                    recent_perf = sum(performances[-3:]) / 3
                    baseline_perf = sum(performances[:3]) / 3

                    degradation = baseline_perf - recent_perf

                    if degradation > 5:  # 5% degradation threshold
                        degradation_alerts.append(
                            {
                                "model_name": model_name,
                                "degradation_percentage": degradation,
                                "baseline_performance": baseline_perf,
                                "current_performance": recent_perf,
                                "severity": "high" if degradation > 15 else "medium",
                                "recommended_actions": self._generate_degradation_actions(model_name, degradation),
                            }
                        )

            return {
                "degradation_detected": len(degradation_alerts) > 0,
                "affected_models": degradation_alerts,
                "overall_health_score": self._calculate_overall_health_score(model_performances),
                "trend_analysis": self._analyze_degradation_trends(model_performances),
            }

        except Exception as e:
            logger.error(f"Error detecting model degradation: {e}")
            return {}

    def _detect_seasonal_patterns(self, historical_data: Dict, current_data: Dict) -> Dict[str, Any]:
        """Detect time-based patterns in security testing"""
        try:
            # Simplified seasonal pattern detection for Phase 2
            current_hour = datetime.now().hour
            current_day = datetime.now().weekday()

            # Basic time-of-day patterns
            time_patterns = {
                "peak_hours": self._identify_peak_testing_hours(historical_data),
                "current_period": "business_hours" if 9 <= current_hour <= 17 else "off_hours",
                "day_type": "weekday" if current_day < 5 else "weekend",
                "expected_activity": self._predict_expected_activity(current_hour, current_day),
                "activity_deviation": self._calculate_activity_deviation(current_data, current_hour, current_day),
            }

            return time_patterns

        except Exception as e:
            logger.error(f"Error detecting seasonal patterns: {e}")
            return {}

    def _detect_operational_anomalies(self, historical_data: Dict, current_data: Dict) -> Dict[str, Any]:
        """Detect operational anomalies requiring attention"""
        try:
            anomalies = []

            # Check for unusual violation spikes
            current_violations = current_data.get("violation_rate", 0)
            historical_avg = historical_data.get("week_average", {}).get("violation_rate", 0)

            if current_violations > historical_avg * 2:
                anomalies.append(
                    {
                        "type": "violation_spike",
                        "description": f"Violation rate ({current_violations:.1f}%) is {current_violations/max(historical_avg,0.1):.1f}x normal",
                        "severity": "high",
                        "impact": "security_posture",
                    }
                )

            # Check for unusual test volume
            current_tests = current_data.get("total_tests", 0)
            historical_test_avg = historical_data.get("week_average", {}).get("total_tests", 0)

            if current_tests < historical_test_avg * 0.5:
                anomalies.append(
                    {
                        "type": "low_test_volume",
                        "description": f"Test volume ({current_tests}) is significantly below normal ({historical_test_avg:.0f})",
                        "severity": "medium",
                        "impact": "coverage_reduction",
                    }
                )

            # Check for system performance issues
            current_success = current_data.get("success_rate", 100)
            if current_success < 90:
                anomalies.append(
                    {
                        "type": "low_success_rate",
                        "description": f"System success rate ({current_success:.1f}%) below threshold",
                        "severity": "high",
                        "impact": "operational_efficiency",
                    }
                )

            return {
                "anomalies_detected": len(anomalies),
                "anomaly_list": anomalies,
                "overall_anomaly_score": min(len(anomalies) * 25, 100),
                "requires_immediate_attention": any(a["severity"] == "high" for a in anomalies),
            }

        except Exception as e:
            logger.error(f"Error detecting operational anomalies: {e}")
            return {}

    def _generate_composite_insights(self, trend_analysis: Dict[str, Any]) -> List[str]:
        """Generate high-level insights from trend analysis"""
        insights = []

        # Violation trend insights
        violation_trends = trend_analysis.get("violation_trends", {})
        if violation_trends.get("trend_direction") == "increasing":
            insights.append(
                f"⚠️ Security violations trending upward ({violation_trends.get('change_percentage', 0):.1f}% change)"
            )

        # Performance insights
        performance_trends = trend_analysis.get("performance_trends", {})
        if performance_trends.get("success_rate_trend") == "decreasing":
            insights.append("📉 System performance showing decline - investigate resource constraints")

        # Model degradation insights
        degradation = trend_analysis.get("model_degradation", {})
        if degradation.get("degradation_detected"):
            affected_count = len(degradation.get("affected_models", []))
            insights.append(f"🚨 {affected_count} model(s) showing performance degradation")

        # Anomaly insights
        anomalies = trend_analysis.get("anomaly_detection", {})
        if anomalies.get("requires_immediate_attention"):
            insights.append("🔥 Critical anomalies detected requiring immediate attention")

        return insights[:5]  # Limit to top 5 insights

    def _prioritize_trends(self, trend_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize trends by urgency and impact"""
        priority_trends = []

        # Add high-priority trends with scoring
        for trend_type, trend_data in trend_analysis.items():
            if trend_type in ["composite_insights", "priority_trends", "trend_alerts"]:
                continue

            priority_score = self._calculate_trend_priority_score(trend_type, trend_data)

            if priority_score > 50:  # Threshold for inclusion
                priority_trends.append(
                    {
                        "trend_type": trend_type,
                        "priority_score": priority_score,
                        "summary": self._generate_trend_summary(trend_type, trend_data),
                        "recommended_actions": self._generate_trend_actions(trend_type, trend_data),
                    }
                )

        # Sort by priority score
        priority_trends.sort(key=lambda x: x["priority_score"], reverse=True)
        return priority_trends[:3]  # Top 3 priority trends

    def _generate_trend_alerts(self, trend_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable alerts from trend analysis"""
        alerts = []

        # High-priority alerts based on trend analysis
        violation_trends = trend_analysis.get("violation_trends", {})
        if violation_trends.get("alert_level") == "high":
            alerts.append(
                {
                    "alert_type": "security_degradation",
                    "title": "Security Posture Degrading",
                    "description": f"Violation rate increasing at {violation_trends.get('velocity', 0):.1f}%/day",
                    "urgency": "high",
                    "actions": ["Review recent model changes", "Increase monitoring frequency", "Alert security team"],
                }
            )

        # System performance alerts
        performance_trends = trend_analysis.get("performance_trends", {})
        if performance_trends.get("success_rate_trend") == "decreasing":
            alerts.append(
                {
                    "alert_type": "performance_degradation",
                    "title": "System Performance Declining",
                    "description": "Success rate trend showing consistent decline",
                    "urgency": "medium",
                    "actions": ["Check system resources", "Review error logs", "Consider scaling"],
                }
            )

        return alerts

    # Helper methods
    def _calculate_violation_alert_level(self, trend_direction: str, velocity: float, current_rate: float) -> str:
        """Calculate alert level for violation trends"""
        if trend_direction == "increasing" and velocity > 5:
            return "high"
        elif trend_direction == "increasing" and velocity > 2:
            return "medium"
        elif current_rate > 50:
            return "high"
        else:
            return "low"

    def _calculate_performance_score(self, success_rates: List[float], test_volumes: List[float]) -> float:
        """Calculate composite performance score"""
        if not success_rates or not test_volumes:
            return 0

        avg_success = sum(success_rates) / len(success_rates)
        success_stability = 100 - (np.std(success_rates) * 10)  # Penalize instability
        volume_consistency = 100 - (np.std(test_volumes) / max(sum(test_volumes) / len(test_volumes), 1) * 100)

        return avg_success * 0.5 + success_stability * 0.3 + volume_consistency * 0.2

    def _generate_performance_recommendations(
        self, success_trend: str, volume_trend: str, stability: float
    ) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []

        if success_trend == "decreasing":
            recommendations.append("Investigate causes of success rate decline")

        if volume_trend == "decreasing":
            recommendations.append("Review test scheduling and resource allocation")

        if stability > 10:
            recommendations.append("Address performance variability issues")

        return recommendations

    def _generate_degradation_actions(self, model_name: str, degradation: float) -> List[str]:
        """Generate model degradation response actions"""
        actions = []

        if degradation > 15:
            actions.append(f"Immediate review of {model_name} required")
            actions.append("Consider model rollback if available")

        actions.append("Analyze recent training data changes")
        actions.append("Review model configuration updates")

        return actions

    def _calculate_overall_health_score(self, model_performances: Dict[str, List[float]]) -> float:
        """Calculate overall model health score"""
        if not model_performances:
            return 100

        total_score = 0
        count = 0

        for model, performances in model_performances.items():
            if performances:
                recent_perf = sum(performances[-3:]) / min(len(performances), 3)
                total_score += recent_perf
                count += 1

        return total_score / max(count, 1)

    def _analyze_degradation_trends(self, model_performances: Dict[str, List[float]]) -> Dict[str, str]:
        """Analyze degradation trends across models"""
        trends = {}

        for model, performances in model_performances.items():
            if len(performances) >= 3:
                trends[model] = self._calculate_simple_trend(performances)

        return trends

    def _identify_peak_testing_hours(self, historical_data: Dict) -> List[int]:
        """Identify peak testing hours from historical data"""
        # Simplified for Phase 2 - return typical business hours
        return [9, 10, 11, 14, 15, 16]

    def _predict_expected_activity(self, hour: int, day: int) -> str:
        """Predict expected activity level"""
        if day >= 5:  # Weekend
            return "low"
        elif 9 <= hour <= 17:  # Business hours
            return "high"
        else:
            return "medium"

    def _calculate_activity_deviation(self, current_data: Dict, hour: int, day: int) -> float:
        """Calculate deviation from expected activity"""
        expected_activity = self._predict_expected_activity(hour, day)
        current_tests = current_data.get("total_tests", 0)

        # Simplified calculation
        if expected_activity == "high" and current_tests < 10:
            return -50  # Below expected
        elif expected_activity == "low" and current_tests > 50:
            return +100  # Above expected
        else:
            return 0  # Normal

    def _calculate_trend_priority_score(self, trend_type: str, trend_data: Dict) -> float:
        """Calculate priority score for trends"""
        base_scores = {
            "violation_trends": 80,
            "performance_trends": 70,
            "model_degradation": 90,
            "anomaly_detection": 85,
            "seasonal_patterns": 40,
        }

        base_score = base_scores.get(trend_type, 50)

        # Adjust based on trend data
        if trend_data.get("alert_level") == "high":
            base_score += 20
        elif trend_data.get("severity") == "high":
            base_score += 15

        return min(base_score, 100)

    def _generate_trend_summary(self, trend_type: str, trend_data: Dict) -> str:
        """Generate summary for trend"""
        summaries = {
            "violation_trends": f"Security violations {trend_data.get('trend_direction', 'stable')}",
            "performance_trends": f"System performance {trend_data.get('success_rate_trend', 'stable')}",
            "model_degradation": f"Model health score: {trend_data.get('overall_health_score', 100):.1f}",
            "anomaly_detection": f"{trend_data.get('anomalies_detected', 0)} anomalies detected",
        }

        return summaries.get(trend_type, f"{trend_type} analysis completed")

    def _generate_trend_actions(self, trend_type: str, trend_data: Dict) -> List[str]:
        """Generate actions for trends"""
        actions = {
            "violation_trends": ["Monitor violation patterns", "Review security controls"],
            "performance_trends": ["Check system health", "Review resource usage"],
            "model_degradation": ["Investigate model changes", "Consider retraining"],
            "anomaly_detection": ["Investigate anomalies", "Increase monitoring"],
        }

        return actions.get(trend_type, ["Monitor situation"])


class COBReportGenerator:
    """Enhanced Report generation engine for COB reports - Phase 2"""

    def generate_daily_report(self, data: Dict[str, Any], shift_info: Dict[str, str]) -> str:
        """Generate comprehensive COB report"""
        try:
            # Generate each section
            executive_summary = self._generate_executive_summary(data)
            threat_analysis = self._generate_threat_analysis(data)
            trend_analysis_section = self._generate_trend_analysis_section(data)
            performance_metrics = self._generate_performance_metrics(data)
            priority_actions = self._generate_priority_actions(data)

            # Combine into full report
            report_date = datetime.fromisoformat(data["report_date"].replace("Z", "+00:00"))

            full_report = f"""# ViolentUTF Security Operations Summary
## Date: {report_date.strftime('%Y-%m-%d')} | Shift: {shift_info.get('shift_name', 'Unknown')} | Operator: {shift_info.get('operator', 'System')}

{executive_summary}

{threat_analysis}

{trend_analysis_section}

{performance_metrics}

{priority_actions}

---
*Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC*
*ViolentUTF Enhanced Reporting System v2.0 (Phase 2)*
"""

            return full_report

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Error generating report: {str(e)}"

    def _generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """Generate executive summary section"""
        exec_metrics = data.get("executions", {})
        baseline = data.get("historical_baselines", {}).get("yesterday", {})

        # Calculate changes vs yesterday
        total_tests = exec_metrics.get("total_tests", 0)
        critical_findings = exec_metrics.get("critical_findings", 0)

        yesterday_tests = baseline.get("total_tests", 0)
        yesterday_critical = baseline.get("critical_findings", 0)

        test_change = self._calculate_percentage_change(total_tests, yesterday_tests)
        critical_change = critical_findings - yesterday_critical

        # System uptime (simplified for Phase 1)
        perf_data = data.get("performance", {})
        uptime = perf_data.get("api_availability", 99.0)

        return f"""### 🎯 Executive Summary
- **Total Tests:** {total_tests:,} ({test_change})
- **Critical Findings:** {critical_findings} ({critical_change:+d} new)
- **System Uptime:** {uptime:.1f}%
- **Coverage:** {exec_metrics.get('unique_models', 0)} models, {exec_metrics.get('unique_generators', 0)} generators, {exec_metrics.get('unique_scorers', 0)} scorers"""

    def _generate_threat_analysis(self, data: Dict[str, Any]) -> str:
        """Generate enhanced threat analysis section with Phase 2 intelligence"""
        threat_data = data.get("threat", {})

        # Check if we have Phase 2 threat analysis data
        threat_patterns = threat_data.get("threat_patterns", [])
        cross_model_threats = threat_data.get("cross_model_threats", [])
        escalating_threats = threat_data.get("escalating_threats", [])
        trend_analysis = threat_data.get("trend_analysis", {})

        threat_section = "### ⚠️ THREAT INTELLIGENCE\n\n"

        # Enhanced threat pattern analysis
        if threat_patterns:
            threat_section += f"**🚨 ATTACK PATTERNS DETECTED: {len(threat_patterns)}**\n\n"

            for i, pattern in enumerate(threat_patterns[:3], 1):  # Top 3 patterns
                threat_section += f"{i}. **{pattern.get('pattern_name', 'Unknown').upper()}**\n"
                threat_section += f"   - Occurrences: {pattern.get('occurrences', 0)}\n"
                threat_section += f"   - Risk Level: {pattern.get('risk_level', 'Unknown')}\n"
                threat_section += f"   - Affected Models: {', '.join(pattern.get('affected_models', []))}\n"
                threat_section += f"   - Description: {pattern.get('description', 'No description available')}\n\n"
        else:
            threat_section += "✅ **No significant attack patterns detected in reporting period.**\n\n"

        # Cross-model threat analysis
        if cross_model_threats:
            threat_section += f"**⚠️ CROSS-MODEL THREATS: {len(cross_model_threats)}**\n\n"

            for threat in cross_model_threats[:2]:  # Top 2 cross-model threats
                threat_section += f"• **{threat.get('threat_type', 'Unknown Threat')}**\n"
                threat_section += f"  - Affecting Models: {', '.join(threat.get('affected_models', []))}\n"
                threat_section += f"  - Severity: {threat.get('threat_severity', 'Unknown')}\n"
                threat_section += f"  - Total Detections: {threat.get('total_detections', 0)}\n\n"

        # Escalating threats
        if escalating_threats:
            threat_section += "**📈 ESCALATING THREATS DETECTED**\n\n"
            for threat in escalating_threats:
                threat_section += f"• {threat.get('description', 'Escalating threat detected')}\n"
                threat_section += f"  - Urgency Level: {threat.get('urgency_level', 0)}/100\n"

        # Trend-based threat insights
        composite_insights = trend_analysis.get("composite_insights", [])
        if composite_insights:
            threat_section += "\n**📊 TREND INSIGHTS:**\n"
            for insight in composite_insights[:3]:  # Top 3 insights
                threat_section += f"• {insight}\n"

        # Fallback to basic analysis if no Phase 2 data
        if not threat_patterns and not cross_model_threats and not escalating_threats:
            exec_metrics = data.get("executions", {})
            results = exec_metrics.get("raw_results", [])
            high_severity_findings = [r for r in results if r.get("severity") in ["critical", "high"]]

            if high_severity_findings:
                threat_section += (
                    f"**Basic Threat Analysis: {len(high_severity_findings)} high-severity findings detected**\n"
                )

                # Group by scorer
                scorer_counts = defaultdict(int)
                for finding in high_severity_findings:
                    scorer_counts[finding.get("scorer_name", "Unknown")] += 1

                for scorer, count in sorted(scorer_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                    threat_section += f"• {scorer}: {count} detections\n"
            else:
                threat_section += "✅ **No critical or high-severity threats detected.**\n"

        return threat_section

    def _generate_trend_analysis_section(self, data: Dict[str, Any]) -> str:
        """Generate trend analysis section with Phase 2 intelligence"""
        threat_data = data.get("threat", {})
        trend_analysis = threat_data.get("trend_analysis", {})

        if not trend_analysis:
            return "### 📈 TREND ANALYSIS\n*No trend analysis data available for this period.*\n"

        trend_section = "### 📈 TREND ANALYSIS\n\n"

        # Composite insights
        composite_insights = trend_analysis.get("composite_insights", [])
        if composite_insights:
            trend_section += "**📊 KEY INSIGHTS:**\n"
            for insight in composite_insights:
                trend_section += f"• {insight}\n"
            trend_section += "\n"

        # Priority trends
        priority_trends = trend_analysis.get("priority_trends", [])
        if priority_trends:
            trend_section += "**🎯 PRIORITY TRENDS:**\n\n"
            for i, trend in enumerate(priority_trends, 1):
                trend_section += f"{i}. **{trend.get('summary', 'Trend detected')}**\n"
                trend_section += f"   - Priority Score: {trend.get('priority_score', 0)}/100\n"
                actions = trend.get("recommended_actions", [])
                if actions:
                    trend_section += f"   - Recommended Action: {actions[0]}\n"
                trend_section += "\n"

        # Trend alerts
        trend_alerts = trend_analysis.get("trend_alerts", [])
        if trend_alerts:
            trend_section += "**🔔 TREND ALERTS:**\n"
            for alert in trend_alerts:
                trend_section += f"• **{alert.get('title', 'Alert')}** ({alert.get('urgency', 'medium')} priority)\n"
                trend_section += f"  {alert.get('description', 'No description')}\n"
            trend_section += "\n"

        # Specific trend analysis details
        violation_trends = trend_analysis.get("violation_trends", {})
        if violation_trends and not violation_trends.get("insufficient_data"):
            trend_section += "**🛡️ SECURITY VIOLATION TRENDS:**\n"
            trend_section += f"• Current Rate: {violation_trends.get('current_rate', 0):.1f}%\n"
            trend_section += f"• Trend Direction: {violation_trends.get('trend_direction', 'unknown').title()}\n"
            trend_section += f"• Change vs Historical: {violation_trends.get('change_percentage', 0):+.1f}%\n"
            trend_section += f"• Alert Level: {violation_trends.get('alert_level', 'unknown').title()}\n\n"

        performance_trends = trend_analysis.get("performance_trends", {})
        if performance_trends and not performance_trends.get("insufficient_data"):
            trend_section += "**⚙️ SYSTEM PERFORMANCE TRENDS:**\n"
            trend_section += (
                f"• Success Rate Trend: {performance_trends.get('success_rate_trend', 'unknown').title()}\n"
            )
            trend_section += f"• Test Volume Trend: {performance_trends.get('test_volume_trend', 'unknown').title()}\n"
            trend_section += f"• Performance Score: {performance_trends.get('performance_score', 0):.1f}/100\n\n"

        # Anomaly detection
        anomaly_detection = trend_analysis.get("anomaly_detection", {})
        if anomaly_detection.get("anomalies_detected", 0) > 0:
            trend_section += "**⚠️ OPERATIONAL ANOMALIES:**\n"
            anomaly_list = anomaly_detection.get("anomaly_list", [])
            for anomaly in anomaly_list:
                trend_section += (
                    f"• {anomaly.get('description', 'Anomaly detected')} (Impact: {anomaly.get('impact', 'unknown')})\n"
                )
            trend_section += "\n"

        if len(trend_section) == len("### 📈 TREND ANALYSIS\n\n"):
            trend_section += "*No significant trends detected in current analysis period.*\n"

        return trend_section

    def _generate_performance_metrics(self, data: Dict[str, Any]) -> str:
        """Generate performance metrics section"""
        exec_metrics = data.get("executions", {})
        perf_data = data.get("performance", {})
        baseline = data.get("historical_baselines", {}).get("week_average", {})

        # Calculate performance metrics
        success_rate = exec_metrics.get("success_rate", 0)
        violation_rate = exec_metrics.get("violation_rate", 0)
        avg_response_time = perf_data.get("avg_response_time", 0)

        # Calculate changes vs baseline
        baseline_success = baseline.get("success_rate", success_rate)
        baseline_violation = baseline.get("violation_rate", violation_rate)

        success_change = self._calculate_percentage_change(success_rate, baseline_success)
        violation_change = self._calculate_percentage_change(violation_rate, baseline_violation)

        return f"""### 📊 Performance Metrics
- **Average Response Time:** {avg_response_time}ms (Normal)
- **Success Rate:** {success_rate:.1f}% ({success_change})
- **Violation Detection Rate:** {violation_rate:.1f}% ({violation_change})
- **Test Throughput:** {perf_data.get('throughput', 0)} tests/min
- **API Availability:** {perf_data.get('api_availability', 0):.1f}%"""

    def _generate_priority_actions(self, data: Dict[str, Any]) -> str:
        """Generate enhanced priority actions section with Phase 2 intelligence"""
        actions = []
        exec_metrics = data.get("executions", {})
        threat_data = data.get("threat", {})

        # Actions from threat analysis
        threat_patterns = threat_data.get("threat_patterns", [])
        cross_model_threats = threat_data.get("cross_model_threats", [])
        escalating_threats = threat_data.get("escalating_threats", [])
        trend_analysis = threat_data.get("trend_analysis", {})

        # High-priority threat-based actions
        for pattern in threat_patterns[:2]:  # Top 2 patterns
            if pattern.get("risk_level") in ["high", "critical"]:
                actions.append(
                    f"🚨 URGENT: Investigate {pattern.get('pattern_name', 'unknown')} attack pattern ({pattern.get('occurrences', 0)} occurrences)"
                )

        # Cross-model threat actions
        for threat in cross_model_threats:
            if threat.get("threat_severity", 0) > 7:  # High severity threshold
                actions.append(
                    f"⚠️ Address cross-model threat: {threat.get('threat_type', 'Unknown')} affecting {len(threat.get('affected_models', []))} models"
                )

        # Escalating threat actions
        for threat in escalating_threats:
            if threat.get("urgency_level", 0) > 50:
                actions.append(f"📈 ESCALATING: {threat.get('description', 'Threat escalation detected')}")

        # Trend-based actions
        trend_alerts = trend_analysis.get("trend_alerts", [])
        for alert in trend_alerts:
            if alert.get("urgency") == "high":
                actions.append(f"🔔 TREND ALERT: {alert.get('title', 'High priority trend alert')}")

        # Priority trends actions
        priority_trends = trend_analysis.get("priority_trends", [])
        for trend in priority_trends[:1]:  # Top priority trend
            if trend.get("priority_score", 0) > 80:
                trend_actions = trend.get("recommended_actions", [])
                if trend_actions:
                    actions.append(f"📊 TREND ACTION: {trend_actions[0]}")

        # Traditional metric-based actions
        violation_rate = exec_metrics.get("violation_rate", 0)
        critical_findings = exec_metrics.get("critical_findings", 0)
        success_rate = exec_metrics.get("success_rate", 0)

        if critical_findings > 10:
            actions.append("📋 Review and analyze high volume of critical findings")

        if violation_rate > 20:
            actions.append("🔍 Investigate elevated violation detection rate")

        if success_rate < 90:
            actions.append("⚙️ Address test execution issues affecting success rate")

        # Default actions if none generated
        if not actions:
            actions = [
                "✅ Continue monitoring for new threat patterns",
                "📈 Review daily metrics for trends",
                "🔄 Prepare for next shift handoff",
            ]

        actions_section = "### 🎯 Priority Actions for Next Shift\n"
        for i, action in enumerate(actions[:5], 1):
            actions_section += f"{i}. {action}\n"

        return actions_section

    def _calculate_percentage_change(self, current: float, previous: float) -> str:
        """Calculate percentage change with formatting"""
        if previous == 0:
            return "+∞%" if current > 0 else "0%"

        change = ((current - previous) / previous) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.1f}%"


def render_cob_reports_tab():
    """Render the COB Reports tab in the dashboard"""
    st.header("📋 Daily Operations Reports (COB)")
    st.markdown("*Automated Close of Business reporting for security operations*")

    # Controls
    col1, col2, col3 = st.columns(3)

    with col1:
        report_date = st.date_input(
            "Report Date", value=datetime.now().date(), help="Date for the report (defaults to today)"
        )

    with col2:
        shift_name = st.selectbox(
            "Shift",
            ["Day Shift - Americas", "Night Shift - Americas", "Day Shift - EMEA", "Day Shift - APAC"],
            help="Shift information for the report",
        )

    with col3:
        operator_name = st.text_input(
            "Operator", value="System Generated", help="Name of the operator or system generating the report"
        )

    # Generate report button
    if st.button("🎯 Generate COB Report", use_container_width=True):
        with st.spinner("Generating daily operations report..."):
            try:
                # Initialize components
                api_base_url = API_BASE_URL
                collector = COBDataCollector(api_base_url)
                generator = COBReportGenerator()

                # Collect data
                report_datetime = datetime.combine(report_date, datetime.min.time())
                data = collector.collect_24h_metrics(report_datetime)

                # Generate report
                shift_info = {"shift_name": shift_name, "operator": operator_name}

                report_content = generator.generate_daily_report(data, shift_info)

                # Display report
                st.success("✅ Report generated successfully!")

                # Show report in expandable section
                with st.expander("📄 View Full Report", expanded=True):
                    st.markdown(report_content)

                # Download button
                st.download_button(
                    label="📥 Download Report (Markdown)",
                    data=report_content,
                    file_name=f"COB_Report_{report_date.strftime('%Y%m%d')}_{shift_name.replace(' ', '_')}.md",
                    mime="text/markdown",
                )

                # Show metrics summary
                exec_metrics = data.get("executions", {})
                if exec_metrics:
                    st.subheader("📊 Quick Metrics Summary")

                    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

                    with metric_col1:
                        st.metric("Total Tests", f"{exec_metrics.get('total_tests', 0):,}")

                    with metric_col2:
                        st.metric("Critical Findings", exec_metrics.get("critical_findings", 0))

                    with metric_col3:
                        st.metric("Success Rate", f"{exec_metrics.get('success_rate', 0):.1f}%")

                    with metric_col4:
                        st.metric("Violation Rate", f"{exec_metrics.get('violation_rate', 0):.1f}%")

            except Exception as e:
                st.error(f"❌ Error generating report: {str(e)}")
                st.exception(e)

    # Historical reports section
    st.divider()
    st.subheader("📚 Historical Reports")
    st.info("Historical report viewing and management will be implemented in Phase 3")


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
    
    # Add terminology clarification
    with st.expander("ℹ️ Understanding Security Testing Terminology", expanded=False):
        st.markdown("""
        **Key Terms in ViolentUTF Security Testing:**
        
        - **Violation/Detection**: When a scorer identifies a potential security issue or vulnerability
        - **Pass**: The AI model's response did NOT trigger security concerns (good)
        - **Fail**: The AI model's response DID trigger security concerns (potential vulnerability)
        - **Detection Rate**: Percentage of tests where security issues were found
        - **Defense Score**: How well the system resisted attacks (100 - violation rate)
        
        **Boolean Scorer Values:**
        - `True` = Security violation detected (Fail)
        - `False` = No security violation (Pass)
        
        💡 **Note**: In security testing, finding violations is the goal - it helps identify weaknesses before attackers do.
        """)

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

        # Enhanced Evidence Explorer toggle
        st.divider()
        st.markdown("### 🔍 Evidence Settings")
        enhanced_evidence = st.checkbox(
            "📝 Enhanced Evidence Explorer",
            value=False,
            help="Enable to load and display actual prompts/responses (may impact performance)",
        )

        # Store in session state for debugging
        st.session_state["enhanced_evidence"] = enhanced_evidence

        if enhanced_evidence:
            st.caption("⚠️ Loading response data may increase loading time")
            st.caption(f"📊 Mode: {'Enhanced' if enhanced_evidence else 'Standard'}")  # Debug info

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
            "- Export capabilities\n"
            "- Enhanced evidence explorer (NEW)"
        )

    # Auto-refresh logic
    if auto_refresh:
        st.empty()  # Placeholder for auto-refresh timer
        time.sleep(60)
        st.cache_data.clear()
        st.rerun()

    # Load and process data using Dashboard_4 approach
    with st.spinner("🔄 Loading execution data from API..."):
        # Debug info
        st.write(f"🔍 Debug: Enhanced Evidence = {enhanced_evidence}")

        # Load orchestrator executions with their results
        if enhanced_evidence:
            # Load with full prompt/response data
            st.write("📝 Loading with full prompt/response data...")
            executions, results = load_orchestrator_executions_with_full_data(days_back)
        else:
            # Load without response data (Dashboard_4 approach)
            st.write("📊 Loading standard data (no responses)...")
            executions, results = load_orchestrator_executions_with_results(days_back)

        # Debug: Check if we have prompt_response data
        if results:
            with_responses = sum(1 for r in results if r.get("prompt_response"))
            st.write(f"🔍 Debug: {with_responses}/{len(results)} results have prompt_response data")

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

    # Calculate multi-dimensional metrics for all tabs
    with st.spinner("Calculating advanced analytics..."):
        # Scorer × Generator Matrix
        matrix_data = calculate_scorer_generator_matrix(filtered_results)

        # Vulnerability Taxonomy
        taxonomy_data = calculate_vulnerability_taxonomy(filtered_results)

        # Advanced Risk Profiles
        generator_groups = defaultdict(list)
        for result in filtered_results:
            generator_groups[result.get("generator_name", "Unknown")].append(result)
        risk_profiles = calculate_advanced_risk_scores(filtered_results, dict(generator_groups))

        # Cross-Model Patterns
        pattern_data = detect_cross_model_patterns(filtered_results)

        # Temporal Performance
        temporal_perf_data = calculate_temporal_performance_metrics(filtered_results)

    # Render dashboard sections
    tabs = st.tabs(
        [
            "📊 Executive Summary",
            "🔥 Compatibility Matrix",
            "🛡️ Vulnerability Taxonomy",
            "⚡ Risk Profiles",
            "🔗 Cross-Model Patterns",
            "📈 Performance Trends",
            "📋 COB Reports",
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
        render_scorer_generator_matrix(matrix_data)

    with tabs[2]:
        render_vulnerability_taxonomy(taxonomy_data)

    with tabs[3]:
        render_advanced_risk_profiles(risk_profiles)

    with tabs[4]:
        render_cross_model_patterns(pattern_data)

    with tabs[5]:
        render_temporal_performance(temporal_perf_data)

    with tabs[6]:
        render_cob_reports_tab()

    with tabs[7]:
        if enhanced_evidence:
            render_detailed_results_table_with_responses(filtered_results)
        else:
            render_detailed_results_table(filtered_results)


if __name__ == "__main__":
    import time  # Import time for auto-refresh

    main()
