# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Main dashboard page for ViolentUTF.

Provides central control panel and status overview for AI red-teaming operations.
"""

import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Load environment variables from .env file
from dotenv import load_dotenv

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
        "critical"
        if val >= 0.8
        else "high" if val >= 0.6 else "medium" if val >= 0.4 else "low" if val >= 0.2 else "minimal"
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
    }.get(val, "unknown"),
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


def api_request(method: str, url: str, **kwargs: object) -> Optional[Dict[str, Any]]:
    """Make an authenticated API request through APISIX Gateway"""
    headers = get_auth_headers()
    if not headers.get("Authorization"):
        logger.warning("No authentication token available for API request")
        return None

    try:
        logger.debug(f"Making {method} request to {url} through APISIX Gateway")
        response = requests.request(method, url, headers=headers, timeout=30, **cast(Any, kwargs))

        if response.status_code in [200, 201]:
            return cast(Dict[str, Any], response.json())
        else:
            logger.error(f"API Error {response.status_code}: {url} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception to {url}: {e}")
        return None


def create_compatible_api_token() -> Optional[str]:
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
            return cast(str, api_token)
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
        # Cast response to handle both list and dict formats from API
        if hasattr(orchestrators_response, "get"):
            orchestrators = cast(List[Dict[str, Any]], orchestrators_response.get("orchestrators", []))
        else:
            orchestrators = cast(List[Dict[str, Any]], orchestrators_response)
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


# --- Metrics Calculation Functions ---


def calculate_comprehensive_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate comprehensive metrics from scorer results"""
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
        }

    # Basic counts
    total_scores = len(results)
    unique_scorers = len(set(r["scorer_name"] for r in results))
    unique_generators = len(set(r["generator_name"] for r in results))
    unique_datasets = len(set(r["dataset_name"] for r in results))
    unique_executions = len(set(r["execution_id"] for r in results))

    # Violation analysis
    violations = 0
    for result in results:
        if result["score_type"] == "true_false" and result["score_value"] is True:
            violations += 1
        elif result["score_type"] == "float_scale" and result["score_value"] >= 0.6:
            violations += 1
        elif result["score_type"] == "str" and result["severity"] in ["high", "critical"]:
            violations += 1

    violation_rate = (violations / total_scores * 100) if total_scores > 0 else 0

    # Severity breakdown
    severity_counts = Counter(r["severity"] for r in results)
    severity_breakdown = dict(severity_counts)

    # Scorer performance
    scorer_performance: Dict[str, Dict[str, Union[int, float]]] = defaultdict(
        lambda: {"total": 0, "violations": 0, "avg_score": 0}
    )
    for result in results:
        scorer = result["scorer_name"]
        scorer_performance[scorer]["total"] += 1

        if result["score_type"] == "true_false" and result["score_value"] is True:
            scorer_performance[scorer]["violations"] += 1
        elif result["score_type"] == "float_scale":
            scorer_performance[scorer]["avg_score"] += result["score_value"]

    # Calculate averages
    for scorer, stats in scorer_performance.items():
        if stats["total"] > 0:
            stats["violation_rate"] = float(cast(int, stats["violations"])) / cast(int, stats["total"]) * 100
            if stats["avg_score"] > 0:
                stats["avg_score"] = stats["avg_score"] / cast(int, stats["total"])

    # Generator risk profile
    generator_risk: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0})
    for result in results:
        generator = result["generator_name"]
        generator_risk[generator]["total"] += 1
        if result["severity"] == "critical":
            generator_risk[generator]["critical"] += 1
        elif result["severity"] == "high":
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
    }


def analyze_temporal_patterns(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze temporal patterns in scorer results"""
    if not results:
        return {}

    # Convert timestamps and sort
    for r in results:
        if isinstance(r["timestamp"], str):
            r["timestamp"] = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))

    results_sorted = sorted(results, key=lambda x: x["timestamp"])

    # Hourly distribution
    hourly_violations: Dict[int, int] = defaultdict(int)
    hourly_total: Dict[int, int] = defaultdict(int)

    for result in results_sorted:
        hour = result["timestamp"].hour
        hourly_total[hour] += 1
        if result["severity"] in ["high", "critical"]:
            hourly_violations[hour] += 1

    # Daily trends
    daily_data: Dict[Any, Dict[str, int]] = defaultdict(lambda: {"total": 0, "violations": 0})
    for result in results_sorted:
        day = result["timestamp"].date()
        daily_data[day]["total"] += 1
        if result["severity"] in ["high", "critical"]:
            daily_data[day]["violations"] += 1

    return {
        "hourly_violations": dict(hourly_violations),
        "hourly_total": dict(hourly_total),
        "daily_trends": {str(k): v for k, v in daily_data.items()},
    }


# --- Visualization Functions ---


def render_executive_dashboard(metrics: Dict[str, Any]) -> None:
    """Render executive-level dashboard with key metrics"""
    st.header("📊 Executive Summary")

    # Key metrics row
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
            "Critical/High", f"{critical_count + high_count:,}", help="Number of critical and high severity findings"
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


def render_scorer_performance(results: List[Dict[str, Any]], metrics: Dict[str, Any]) -> None:
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


def render_generator_risk_analysis(metrics: Dict[str, Any]) -> None:
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


def render_temporal_analysis(results: List[Dict[str, Any]], metrics: Dict[str, Any]) -> None:
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


def render_detailed_results_table(results: List[Dict[str, Any]]) -> None:
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
            display_data.append(
                {
                    "Timestamp": r["timestamp"],
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


def main() -> None:
    """Run the main API-integrated dashboard."""
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

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(results)

    # Display success message
    st.success(f"✅ Loaded {len(results)} scorer results from {len(executions)} executions")

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
        render_executive_dashboard(metrics)

    with tabs[1]:
        render_scorer_performance(results, metrics)

    with tabs[2]:
        render_generator_risk_analysis(metrics)

    with tabs[3]:
        render_temporal_analysis(results, metrics)

    with tabs[4]:
        render_detailed_results_table(results)


if __name__ == "__main__":
    main()
