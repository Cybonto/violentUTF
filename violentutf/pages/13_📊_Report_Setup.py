"""
Advanced Dashboard Report Setup Page

This page provides a comprehensive interface for generating reports from scan data.
It follows the same patterns as the Dashboard page for consistency.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

# Import utilities
from utils.auth_utils import handle_authentication_and_sidebar
from utils.jwt_manager import jwt_manager
from utils.logging import get_logger

load_dotenv()
logger = get_logger(__name__)

# Page configuration
st.set_page_config(page_title="Report Setup - ViolentUTF", page_icon="📊", layout="wide")

# API Configuration - Following Dashboard pattern
_raw_api_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
API_BASE_URL = _raw_api_url.rstrip("/api").rstrip("/")
if not API_BASE_URL:
    API_BASE_URL = "http://localhost:9080"

API_ENDPOINTS = {
    # Reuse dashboard endpoints
    "dashboard_summary": f"{API_BASE_URL}/api/v1/dashboard/summary",
    "dashboard_scores": f"{API_BASE_URL}/api/v1/dashboard/scores",
    "dashboard_browse": f"{API_BASE_URL}/api/v1/dashboard/browse",  # New enhanced endpoint
    # Future report-specific endpoints
    "report_templates": f"{API_BASE_URL}/api/v1/reports/templates",
    "report_generate": f"{API_BASE_URL}/api/v1/reports/generate",
}

# --- Authentication and Setup ---
username = handle_authentication_and_sidebar()
if not username:
    st.warning("Please log in to access the Report Setup page.")
    st.stop()

# --- Helper Functions (Following Dashboard Pattern) ---


def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers for API requests through APISIX Gateway"""
    try:
        token = jwt_manager.get_valid_token()
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
        st.error("🔐 Authentication required. Please refresh the page.")
        return None

    try:
        logger.debug(f"Making {method} request to {url} through APISIX Gateway")
        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

        if response.status_code in [200, 201]:
            return response.json()
        else:
            logger.error(f"API Error {response.status_code}: {url} - {response.text}")

            # User-friendly error messages
            if response.status_code == 401:
                st.error("🔐 Authentication expired. Please refresh the page.")
            elif response.status_code == 403:
                st.error("🚫 Access denied to this resource.")
            elif response.status_code == 404:
                st.error("❌ Resource not found.")
            else:
                st.error(f"❌ API Error: {response.status_code}")

            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception to {url}: {e}")
        st.error("❌ Connection error. Please check if services are running.")
        return None


# --- Session State Management ---
if "report_setup_state" not in st.session_state:
    st.session_state.report_setup_state = {
        "selected_scans": [],  # List of selected scan IDs
        "current_tab": 0,  # Current tab index
        "filters": {  # Filter state
            "date_range": (datetime.now() - timedelta(days=7), datetime.now() + timedelta(days=1)),  # Include today
            "scanner_type": "All",
            "include_test": True,  # Default to True to match Dashboard behavior
        },
        "template_id": None,  # Selected template
        "configuration": {},  # Report configuration
    }

# Shorthand for state
state = st.session_state.report_setup_state


# --- Main UI ---
st.title("📊 Advanced Dashboard - Report Setup")
st.markdown("Generate comprehensive security assessment reports from your scan data.")

# Tab navigation
tabs = st.tabs(
    [
        "📁 Data Selection",
        "📝 Template Selection",
        "⚙️ Configuration",
        "👁️ Preview",
        "🚀 Generate",
        "📚 Template Management",
    ]
)

# --- Tab 1: Data Selection ---
with tabs[0]:
    st.markdown("Choose the scan results to include in your report.")

    # Filter Panel
    with st.expander("🔍 **Filters**", expanded=True):
        filter_cols = st.columns(4)

        with filter_cols[0]:
            # Date range filter
            st.subheader("Date Range")
            date_range = st.date_input(
                "Select date range",
                value=(
                    state["filters"].get(
                        "date_range", (datetime.now() - timedelta(days=7), datetime.now() + timedelta(days=1))
                    )[0],
                    state["filters"].get(
                        "date_range", (datetime.now() - timedelta(days=7), datetime.now() + timedelta(days=1))
                    )[1],
                ),
                max_value=datetime.now() + timedelta(days=1),
                key="filter_date_range",
                help="Filter scans by execution date",
            )

            # Include test executions
            include_test = st.checkbox(
                "Include test executions",
                value=state["filters"].get("include_test", True),
                key="filter_include_test",
                help="Include test/dry-run executions in results",
            )

        with filter_cols[1]:
            # Scanner type filter
            st.subheader("Scanner Type")
            scanner_type = st.radio(
                "Select scanner",
                options=["All", "PyRIT", "Garak"],
                index=0,
                key="filter_scanner_type",
                help="Filter by scanner type",
            )

            # Orchestrator type filter
            orchestrator_types = st.multiselect(
                "Orchestrator types",
                options=["RedTeamingOrchestrator", "PromptSendingOrchestrator", "CustomOrchestrator"],
                key="filter_orchestrator_types",
                help="Filter by specific orchestrator types",
            )

        with filter_cols[2]:
            # Execution Status Info
            st.subheader("Status Info")

            # Show available data info
            st.info(
                """
            **Note**: Current scorer data has limited metadata.
            Filters are based on available fields:
            - Execution name & type
            - Orchestrator info
            - Date ranges
            """
            )

            # Placeholder for future filters when data supports them
            st.caption("Additional filters will be enabled as scorer data is enhanced.")

        with filter_cols[3]:
            # Sort options
            st.subheader("Sort Options")
            sort_col1, sort_col2 = st.columns(2)
            with sort_col1:
                sort_by = st.selectbox("Sort by", options=["date", "severity", "model"], key="filter_sort_by")
            with sort_col2:
                sort_order = st.selectbox(
                    "Order",
                    options=["desc", "asc"],
                    format_func=lambda x: "Newest first" if x == "desc" else "Oldest first",
                    key="filter_sort_order",
                )

    # Search button
    col1, col2, col3 = st.columns([1, 1, 5])
    with col1:
        search_clicked = st.button("🔄 **Search**", type="primary", use_container_width=True)
    with col2:
        if st.button("🗑️ Clear Filters", use_container_width=True):
            # Reset filters
            state["filters"] = {
                "date_range": (datetime.now() - timedelta(days=7), datetime.now() + timedelta(days=1)),
                "scanner_type": "All",
                "include_test": True,
            }
            st.rerun()

    # Divider
    st.divider()

    # Data loading and display
    if search_clicked or "scan_data" not in st.session_state:
        with st.spinner("Searching for scan data..."):
            # Build request with basic filters
            request_data = {
                "start_date": date_range[0].isoformat() if isinstance(date_range, tuple) else None,
                "end_date": date_range[1].isoformat() if isinstance(date_range, tuple) else None,
                "include_test": include_test,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "page": 1,
                "page_size": 50,
            }

            # Add orchestrator type filter (this exists in the data)
            if orchestrator_types:
                request_data["orchestrator_types"] = orchestrator_types

            # These filters will be ignored by backend if data doesn't support them
            # if selected_generators:
            #     request_data["generators"] = selected_generators
            # if min_severity != "minimal":
            #     request_data["min_severity"] = min_severity

            # Make API request
            response = api_request("POST", API_ENDPOINTS["dashboard_browse"], json=request_data)

            if response:
                st.session_state["scan_data"] = response
                # Show success message
                total_found = response.get("total_count", 0)
                st.success(f"✅ Found {total_found} scan execution(s)")
            else:
                st.error("Failed to load scan data. Please check your connection and try again.")
                st.session_state["scan_data"] = None

    # Display results
    if st.session_state.get("scan_data"):
        scan_data = st.session_state["scan_data"]
        results = scan_data.get("results", [])

        if results:
            st.subheader(f"📊 Available Scans ({len(results)} shown)")

            # Selection summary at top
            if state["selected_scans"]:
                st.info(f"✅ **{len(state['selected_scans'])} scan(s) selected**")

            # Display scan cards
            for idx, scan in enumerate(results):
                with st.container():
                    # Create columns for layout
                    check_col, main_col, metrics_col = st.columns([0.5, 5, 2])

                    with check_col:
                        # Selection checkbox
                        scan_id = str(scan["execution_id"])
                        is_selected = st.checkbox(
                            "Select",
                            key=f"select_{scan_id}",
                            value=scan_id in state["selected_scans"],
                            label_visibility="collapsed",
                        )

                        # Update selection state
                        if is_selected and scan_id not in state["selected_scans"]:
                            state["selected_scans"].append(scan_id)
                        elif not is_selected and scan_id in state["selected_scans"]:
                            state["selected_scans"].remove(scan_id)

                    with main_col:
                        # Scan info
                        test_badge = " 🧪" if scan.get("is_test_execution", False) else ""
                        st.markdown(f"### {scan['execution_name']}{test_badge}")

                        # Metadata
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text(f"🔧 {scan['orchestrator_name']}")
                            st.text(f"📊 Type: {scan['orchestrator_type']}")
                        with col2:
                            st.text(f"📅 {scan['started_at'][:10]}")
                            duration = scan.get("duration_seconds", 0)
                            st.text(f"⏱️ Duration: {duration//60}m {duration%60}s")
                        with col3:
                            st.text(f"🧪 Tests: {scan['total_tests']}")
                            categories = ", ".join(scan.get("score_categories", [])[:3])
                            if categories:
                                st.text(f"📂 {categories}")

                    with metrics_col:
                        # Severity distribution
                        severity_dist = scan.get("severity_distribution", {})

                        # Show severity badges
                        if severity_dist.get("critical", 0) > 0:
                            st.error(f"🔴 Critical: {severity_dist['critical']}")
                        if severity_dist.get("high", 0) > 0:
                            st.warning(f"🟠 High: {severity_dist['high']}")
                        if severity_dist.get("medium", 0) > 0:
                            st.info(f"🟡 Medium: {severity_dist['medium']}")

                        # Expand for details
                        with st.expander("View details"):
                            # Key findings
                            findings = scan.get("key_findings", [])
                            if findings:
                                st.markdown("**Key Findings:**")
                                for finding in findings:
                                    st.markdown(
                                        f"- [{finding['severity']}] {finding['category']}: {finding['description']}"
                                    )
                            else:
                                st.text("No significant findings")

                    st.divider()

            # Pagination
            if scan_data.get("has_more", False):
                st.info("ℹ️ More results available. Refine your filters to see specific scans.")

        else:
            st.warning("No scan data found matching your criteria. Try adjusting the filters.")

    # Selection summary at bottom
    if state["selected_scans"]:
        st.divider()
        st.subheader("📋 Selection Summary")
        st.success(f"**{len(state['selected_scans'])} scan(s) selected for report generation**")

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Clear Selection", type="secondary", use_container_width=True):
                state["selected_scans"] = []
                st.rerun()
        with col2:
            st.info("💡 Proceed to the **Template Selection** tab to continue.")

# --- Tab 2: Template Selection ---
with tabs[1]:
    st.header("Select Report Template")

    # Check if data is selected
    if not state["selected_scans"]:
        st.warning("⚠️ Please select scan data first in the Data Selection tab.")
        st.stop()

    st.info("🚧 Template Selection functionality coming soon.")

# --- Tab 3: Configuration ---
with tabs[2]:
    st.header("Configure Report")

    # Check prerequisites
    if not state["selected_scans"]:
        st.warning("⚠️ Please select scan data first.")
        st.stop()

    if not state["template_id"]:
        st.warning("⚠️ Please select a template first.")
        st.stop()

    st.info("🚧 Configuration functionality coming soon.")

# --- Tab 4: Preview ---
with tabs[3]:
    st.header("Preview Report")

    # Check prerequisites
    if not state["configuration"]:
        st.warning("⚠️ Please configure the report first.")
        st.stop()

    st.info("🚧 Preview functionality coming soon.")

# --- Tab 5: Generate ---
with tabs[4]:
    st.header("Generate Report")

    # Check prerequisites
    if not all([state["selected_scans"], state["template_id"], state["configuration"]]):
        st.warning("⚠️ Please complete all previous steps first.")
        st.stop()

    st.info("🚧 Report generation functionality coming soon.")

# --- Tab 6: Template Management ---
with tabs[5]:
    st.header("Template Management")
    st.markdown("Create, edit, and manage report templates.")

    st.info("🚧 Template management functionality coming soon.")
