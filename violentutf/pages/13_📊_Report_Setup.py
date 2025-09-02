# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

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

# Additional imports for Configuration tab
try:
    import pytz
except ImportError:
    pytz = None

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
    # Report endpoints
    "report_templates": f"{API_BASE_URL}/api/v1/reports/templates",
    "report_templates_init": f"{API_BASE_URL}/api/v1/reports/templates/initialize",
    "report_generate": f"{API_BASE_URL}/api/v1/reports/generate",
    "report_preview": f"{API_BASE_URL}/api/v1/reports/preview",
    "report_blocks_registry": f"{API_BASE_URL}/api/v1/reports/blocks/registry",
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
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Params: {kwargs.get('params', {})}")

        response = requests.request(method, url, headers=headers, timeout=30, **kwargs)

        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")

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
                st.error(f"❌ Resource not found: {url}")
                st.info("Debug: Check if the API service is running and routes are configured.")
            else:
                st.error(f"❌ API Error: {response.status_code}")

            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception to {url}: {e}")
        st.error("❌ Connection error. Please check if services are running.")
        return None


# --- Helper function to ensure templates exist ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def ensure_templates_initialized():
    """Ensure default templates are initialized"""
    try:
        # Try to initialize templates
        init_response = api_request("POST", API_ENDPOINTS["report_templates_init"])
        if init_response:
            logger.info(f"Template initialization: {init_response.get('message', 'Unknown')}")
        return True
    except Exception as e:
        logger.warning(f"Template initialization check failed: {e}")
        return False


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
                key="data_filter_scanner_type",
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

    # Advanced search and filters
    with st.container():
        st.markdown("### 🔍 Find Templates")

        # Template selection
        # First, load all templates to populate the selectbox
        all_templates_response = api_request(
            "GET", API_ENDPOINTS["report_templates"], params={"limit": 100, "is_active": True}
        )

        if all_templates_response and "templates" in all_templates_response:
            template_names = ["All Templates"] + [t["name"] for t in all_templates_response["templates"]]
            template_map = {t["name"]: t for t in all_templates_response["templates"]}
        else:
            template_names = ["All Templates"]
            template_map = {}

        selected_template_name = st.selectbox(
            "Select Template",
            options=template_names,
            key="template_select",
            help="Choose a specific template or view all templates",
        )

        # Filter columns
        filter_cols = st.columns([1, 1, 1, 1])

        with filter_cols[0]:
            # Testing category filter - must match API enum values
            testing_categories = ["All", "Security", "Safety", "Reliability", "Robustness", "Compliance"]
            testing_category = st.selectbox(
                "Testing Category", options=testing_categories, key="filter_testing_category"
            )

        with filter_cols[1]:
            # Attack category filter - must match API enum values
            attack_categories = [
                "All",
                "Prompt Injection",
                "Jailbreak",
                "Data Leakage",
                "Hallucination",
                "Bias",
                "Toxicity",
                "Harmful Content",
                "Privacy Violation",
                "Misinformation",
            ]
            attack_category = st.selectbox("Attack Category", options=attack_categories, key="filter_attack_category")

        with filter_cols[2]:
            # Scanner type filter - convert display values to API values
            scanner_display = ["All", "PyRIT", "Garak", "Both"]
            scanner_type_display = st.selectbox(
                "Scanner Type", options=scanner_display, key="template_filter_scanner_type"
            )
            # Map display values to API values
            scanner_type_map = {"PyRIT": "pyrit", "Garak": "garak", "Both": "both", "All": "All"}
            scanner_type = scanner_type_map.get(scanner_type_display, scanner_type_display)

        with filter_cols[3]:
            # Complexity filter
            complexity_levels = ["All", "Basic", "Intermediate", "Advanced", "Expert"]
            complexity = st.selectbox("Complexity", options=complexity_levels, key="filter_complexity")

        # Sort options
        sort_cols = st.columns([2, 1])
        with sort_cols[0]:
            sort_by = st.selectbox(
                "Sort by",
                options=["name", "updated_at", "created_at", "usage_count"],
                format_func=lambda x: {
                    "name": "Name (A-Z)",
                    "updated_at": "Recently Updated",
                    "created_at": "Newest First",
                    "usage_count": "Most Used",
                }[x],
                key="template_sort",
                index=0,  # Default to "name"
            )

        with sort_cols[1]:
            # View toggle
            view_mode = st.radio("View", options=["Grid", "List"], horizontal=True, key="template_view_mode", index=0)

    st.divider()

    # Load templates with filters
    with st.spinner("Loading templates..."):
        # Build query parameters
        params = {
            "skip": 0,
            "limit": 50,  # Load more templates
            "sort_by": sort_by,
            "sort_order": "desc" if sort_by != "name" else "asc",
            # "is_active": True,  # Temporarily removed to see all templates
        }

        # Apply filters - send exact values that match the API enums
        if testing_category != "All":
            params["testing_category"] = testing_category  # API expects single value

        if attack_category != "All":
            params["attack_category"] = attack_category  # API expects single value

        if scanner_type != "All":
            params["scanner_type"] = scanner_type  # Already mapped to API value

        if complexity != "All":
            params["complexity_level"] = complexity  # Send as-is

        # Get templates based on selection
        if selected_template_name != "All Templates" and selected_template_name in template_map:
            # Show only the selected template
            selected_template = template_map[selected_template_name]
            templates = [selected_template]

            # Apply filters to the single template
            if testing_category != "All":
                template_categories = selected_template.get("metadata", {}).get("testing_categories", [])
                # Check if category matches (case-insensitive)
                if not any(cat.lower() == testing_category.lower() for cat in template_categories):
                    templates = []

            if attack_category != "All" and templates:
                template_attacks = selected_template.get("metadata", {}).get("attack_categories", [])
                # Check if attack category matches (case-insensitive)
                if not any(cat.lower() == attack_category.lower() for cat in template_attacks):
                    templates = []

            if scanner_type != "All" and templates:
                template_scanner = selected_template.get("metadata", {}).get("scanner_type", "")
                if template_scanner.lower() != scanner_type.lower():
                    templates = []

            if complexity != "All" and templates:
                template_complexity = selected_template.get("metadata", {}).get("complexity_level", "")
                if template_complexity.lower() != complexity.lower():
                    templates = []

            response = {"templates": templates, "total": len(templates), "page": 1, "pages": 1}
        else:
            # Show all templates with filters
            response = api_request("GET", API_ENDPOINTS["report_templates"], params=params)

        if response and "templates" in response:
            templates = response["templates"]
            total_count = response.get("total", len(templates))

            # Display results count
            if templates:
                st.info(
                    f"Found {len(templates)} templates{f' (showing {len(templates)} of {total_count})' if total_count > len(templates) else ''}"
                )

            if templates:
                # Get view mode
                view_mode = st.session_state.get("template_view_mode", "Grid")

                # Display based on view mode
                if view_mode == "Grid":
                    # Grid view with cards
                    cols_per_row = 2 if len(templates) > 1 else 1

                    for i in range(0, len(templates), cols_per_row):
                        cols = st.columns(cols_per_row)

                        for j, col in enumerate(cols):
                            if i + j < len(templates):
                                template = templates[i + j]

                                with col:
                                    # Template card
                                    with st.container():
                                        # Card styling with custom CSS
                                        st.markdown(
                                            f"""
                                            <style>
                                            .template-card {{
                                                border: 1px solid #ddd;
                                                border-radius: 8px;
                                                padding: 16px;
                                                margin-bottom: 16px;
                                                transition: all 0.3s ease;
                                            }}
                                            .template-card:hover {{
                                                border-color: #1f77b4;
                                                box-shadow: 0 2px 8px rgba(31, 119, 180, 0.2);
                                            }}
                                            .template-selected {{
                                                border-color: #1f77b4;
                                                background-color: rgba(31, 119, 180, 0.05);
                                            }}
                                            </style>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                        # Template header
                                        # Check if system template (created_by == "system" or has is_system flag)
                                        is_system = template.get("created_by") == "system" or template.get(
                                            "metadata", {}
                                        ).get("is_system", False)
                                        type_badge = "🏢" if is_system else "👤"

                                        st.markdown(f"### {type_badge} {template['name']}")

                                        # Template description
                                        st.caption(template.get("description", "No description available"))

                                        # Template metadata
                                        metadata_cols = st.columns(2)
                                        with metadata_cols[0]:
                                            # Extract categories from metadata
                                            metadata = template.get("metadata", {})
                                            testing_cats = metadata.get("testing_categories", [])
                                            if testing_cats:
                                                category_text = (
                                                    testing_cats[0]
                                                    if isinstance(testing_cats, list)
                                                    else str(testing_cats)
                                                )
                                                st.text(f"📁 {category_text.title()}")
                                            else:
                                                st.text("📁 General")

                                            # Count blocks from config
                                            config = template.get("config", {})
                                            blocks = config.get("blocks", [])
                                            st.text(f"📄 {len(blocks)} sections")

                                        with metadata_cols[1]:
                                            updated = template.get("updated_at", "")
                                            if updated:
                                                try:
                                                    # Handle different date formats
                                                    if isinstance(updated, str):
                                                        updated_date = datetime.fromisoformat(
                                                            updated.replace("Z", "+00:00")
                                                        )
                                                    else:
                                                        updated_date = updated
                                                    st.text(f"📅 {updated_date.strftime('%Y-%m-%d')}")
                                                except:
                                                    st.text("📅 Recently updated")

                                            # Tags from metadata
                                            tags = metadata.get("tags", [])
                                            if tags:
                                                st.text(f"🏷️ {', '.join(tags[:2])}")

                                        # Action buttons
                                        button_cols = st.columns(2)

                                        with button_cols[0]:
                                            # Preview button
                                            if st.button(
                                                "👁️ Preview", key=f"preview_{template['id']}", use_container_width=True
                                            ):
                                                # Store template for preview
                                                st.session_state["preview_template"] = template
                                                st.session_state["show_preview"] = True

                                        with button_cols[1]:
                                            # Selection state
                                            is_selected = state.get("template_id") == template["id"]

                                            # Select button
                                            if st.button(
                                                "✅ Selected" if is_selected else "Select",
                                                key=f"select_{template['id']}",
                                                type="primary" if is_selected else "secondary",
                                                use_container_width=True,
                                                disabled=is_selected,
                                            ):
                                                # Update state with selected template
                                                state["template_id"] = template["id"]
                                                state["template_name"] = template["name"]
                                                state["template_details"] = template
                                                st.rerun()
                else:
                    # List view
                    for template in templates:
                        # List item container
                        with st.container():
                            cols = st.columns([3, 1, 1, 1])

                            with cols[0]:
                                # Name and description
                                metadata = template.get("metadata", {})
                                is_system = template.get("created_by") == "system" or metadata.get("is_system", False)
                                badge = "🏢" if is_system else "👤"
                                st.markdown(f"**{badge} {template['name']}**")
                                st.caption(template.get("description", ""))

                            with cols[1]:
                                # Key metadata
                                testing_cats = metadata.get("testing_categories", [])
                                if testing_cats:
                                    st.text(f"🎯 {testing_cats[0].title()}")

                                scanner = metadata.get("scanner_type", "")
                                if scanner:
                                    st.text(f"🔧 {scanner.upper()}")

                            with cols[2]:
                                # Stats
                                config = template.get("config", {})
                                blocks = config.get("blocks", [])
                                st.text(f"📄 {len(blocks)} sections")

                                usage = metadata.get("usage_stats", {}).get("total_uses", 0)
                                st.text(f"📊 {usage} uses")

                            with cols[3]:
                                # Actions
                                is_selected = state.get("template_id") == template["id"]
                                button_cols = st.columns(2)

                                with button_cols[0]:
                                    if st.button("👁️", key=f"preview_list_{template['id']}", help="Preview"):
                                        st.session_state["preview_template"] = template
                                        st.session_state["show_preview"] = True

                                with button_cols[1]:
                                    if st.button(
                                        "✅" if is_selected else "Select",
                                        key=f"select_list_{template['id']}",
                                        type="primary" if not is_selected else "secondary",
                                        disabled=is_selected,
                                        help="Selected" if is_selected else "Select this template",
                                    ):
                                        state["template_id"] = template["id"]
                                        state["template_name"] = template["name"]
                                        state["template_details"] = template
                                        st.rerun()

                            st.divider()

                # Show selected template summary
                if state.get("template_id"):
                    st.divider()
                    st.success(f"✅ **Selected Template:** {state.get('template_name', 'Unknown')}")
                    st.info("💡 Proceed to the **Configuration** tab to customize the report settings.")

            else:
                # No templates found
                st.warning("No templates found matching your criteria.")

                # Suggest actions
                st.markdown("### 💡 Suggestions")
                suggestions = []

                if selected_template_name != "All Templates":
                    suggestions.append("- Try selecting 'All Templates' to see the full list")

                if any(
                    [testing_category != "All", attack_category != "All", scanner_type != "All", complexity != "All"]
                ):
                    suggestions.append("- Remove some filters to see more results")

                suggestions.append("- Initialize default templates using the button below")
                suggestions.append("- Check the Template Management tab to create a new template")

                for suggestion in suggestions:
                    st.markdown(suggestion)

                # Add initialize templates button
                st.divider()
                if st.button("🚀 Initialize Default Templates", type="primary", use_container_width=True):
                    with st.spinner("Initializing templates..."):
                        init_response = api_request("POST", API_ENDPOINTS["report_templates_init"])
                        if init_response:
                            st.success(f"✅ Initialized {init_response.get('templates_created', 0)} templates!")
                            st.rerun()
                        else:
                            st.error("Failed to initialize templates. Please check the logs.")
        else:
            st.error("Failed to load templates. Please try again.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Retry", use_container_width=True):
                    st.rerun()
            with col2:
                if st.button("🚀 Initialize Templates", type="primary", use_container_width=True):
                    with st.spinner("Initializing templates..."):
                        init_response = api_request("POST", API_ENDPOINTS["report_templates_init"])
                        if init_response:
                            st.success(f"✅ Initialized {init_response.get('templates_created', 0)} templates!")
                            st.rerun()
                        else:
                            st.error("Failed to initialize templates. Please check the logs.")

    # Template Preview Modal
    if st.session_state.get("show_preview", False) and st.session_state.get("preview_template"):
        template = st.session_state["preview_template"]

        # Create a modal-like experience with expander
        with st.expander("📋 Template Preview", expanded=True):
            # Preview header
            preview_cols = st.columns([3, 1])
            with preview_cols[0]:
                st.subheader(template["name"])
            with preview_cols[1]:
                if st.button("❌ Close", key="close_preview"):
                    st.session_state["show_preview"] = False
                    st.session_state["preview_template"] = None
                    st.rerun()

            # Template details
            st.markdown(f"**Description:** {template.get('description', 'N/A')}")

            # Extract category from metadata
            metadata = template.get("metadata", {})
            testing_cats = metadata.get("testing_categories", [])
            if testing_cats:
                category_text = testing_cats[0] if isinstance(testing_cats, list) else str(testing_cats)
                st.markdown(f"**Category:** {category_text.title()}")
            else:
                st.markdown("**Category:** General")

            # Template type
            is_system = template.get("created_by") == "system"
            st.markdown(f"**Type:** {'System' if is_system else 'Custom'}")

            # Preview sections/blocks
            st.markdown("### Report Structure")

            # Get blocks from template config
            config = template.get("config", {})
            blocks = config.get("blocks", [])

            if blocks:
                for idx, block in enumerate(blocks, 1):
                    block_type = block.get("block_type", "unknown")
                    config = block.get("config", {})

                    # Show block info
                    st.markdown(f"**{idx}. {block_type.replace('_', ' ').title()}**")

                    # Show block configuration details
                    if block_type == "title":
                        st.caption(f"   Title: {config.get('title', 'Report Title')}")
                        st.caption(f"   Subtitle: {config.get('subtitle', '')}")
                    elif block_type == "executive_summary":
                        st.caption("   Provides high-level overview of findings")
                    elif block_type == "findings_by_severity":
                        st.caption("   Groups findings by severity level")
                        st.caption(f"   Include evidence: {config.get('include_evidence', False)}")
                    elif block_type == "technical_details":
                        st.caption("   Detailed technical analysis")
                        st.caption(f"   Evidence limit: {config.get('max_evidence_per_finding', 5)}")
                    elif block_type == "recommendations":
                        st.caption("   Actionable recommendations")
                        st.caption(f"   Group by: {config.get('group_by', 'severity')}")
                    elif block_type == "metrics":
                        st.caption("   Visual metrics and statistics")
                        metrics = config.get("metrics", [])
                        if metrics:
                            st.caption(f"   Metrics: {', '.join(metrics)}")
                    else:
                        st.caption(f"   Configuration: {json.dumps(config, indent=2)}")

                # Show data requirements
                st.markdown("### Data Requirements")
                requirements = template.get("metadata", {})

                if requirements.get("min_scans", 1) > 1:
                    st.info(f"📊 Requires at least {requirements['min_scans']} scan executions")

                if requirements.get("requires_evidence"):
                    st.info("📝 Requires prompt/response evidence data")

                if requirements.get("requires_severity"):
                    st.info("🎯 Requires severity scoring data")

                # Compatibility check with selected data
                st.markdown("### Compatibility Check")

                selected_count = len(state.get("selected_scans", []))
                min_required = requirements.get("min_scans", 1)

                if selected_count >= min_required:
                    st.success(f"✅ Selected data ({selected_count} scans) meets requirements")
                else:
                    st.error(f"❌ Need at least {min_required} scans (currently {selected_count})")

            # Select from preview
            st.divider()
            if st.button("Select This Template", key="select_from_preview", type="primary", use_container_width=True):
                state["template_id"] = template["id"]
                state["template_name"] = template["name"]
                state["template_details"] = template
                st.session_state["show_preview"] = False
                st.session_state["preview_template"] = None
                st.rerun()

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

    # Initialize configuration state if not exists
    if "configuration" not in state or not state["configuration"]:
        state["configuration"] = {
            "blocks": [],
            "output_formats": ["PDF", "JSON"],
            "schedule": None,
            "notifications": {
                "email": {"enabled": False, "recipients": []},
                "webhook": {"enabled": False, "url": None},
            },
            "report_name_template": "Report_{date}_{time}",
            "priority": "normal",
        }

    # Create subtabs for different configuration sections
    config_subtabs = st.tabs(["📦 Blocks", "📅 Schedule", "🔔 Notifications", "📄 Output", "⚙️ Advanced"])

    # --- Blocks Configuration ---
    with config_subtabs[0]:
        st.markdown("### Report Blocks Configuration")
        st.markdown("Configure which blocks to include in your report and their settings.")

        # Load available blocks from API
        blocks_response = api_request("GET", API_ENDPOINTS["report_blocks_registry"])

        if blocks_response and "blocks" in blocks_response:
            # Convert blocks dictionary to list format
            available_blocks = []
            for block_type, block_data in blocks_response["blocks"].items():
                block_def = block_data["definition"]
                block_def["block_type"] = block_type
                available_blocks.append(block_def)

            # Load template configuration to get default blocks
            if state["template_id"]:
                template_config_response = api_request(
                    "GET", f"{API_ENDPOINTS['report_templates']}/{state['template_id']}"
                )

                if template_config_response:
                    template_blocks = template_config_response.get("config", {}).get("blocks", [])

                    # Initialize blocks in configuration if not set
                    if not state["configuration"]["blocks"]:
                        state["configuration"]["blocks"] = template_blocks

                    # Block management section
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown("#### Active Blocks")
                    with col2:
                        if st.button("➕ Add Block", use_container_width=True):
                            st.session_state.show_add_block = True

                    # Show add block dialog
                    if getattr(st.session_state, "show_add_block", False):
                        with st.expander("Add New Block", expanded=True):
                            available_types = [
                                b["block_type"]
                                for b in available_blocks
                                if b["block_type"]
                                not in [block.get("block_type") for block in state["configuration"]["blocks"]]
                            ]

                            if available_types:
                                selected_type = st.selectbox("Select block type:", available_types)
                                block_info = next(b for b in available_blocks if b["block_type"] == selected_type)

                                st.info(f"**{block_info['display_name']}**: {block_info['description']}")

                                if st.button("Add Block"):
                                    new_block = {
                                        "block_type": selected_type,
                                        "config": block_info.get("default_config", {}),
                                        "enabled": True,
                                    }
                                    state["configuration"]["blocks"].append(new_block)
                                    st.session_state.show_add_block = False
                                    st.rerun()
                            else:
                                st.info("All available blocks are already added.")

                            if st.button("Cancel"):
                                st.session_state.show_add_block = False
                                st.rerun()

                    # Display and configure active blocks
                    if state["configuration"]["blocks"]:
                        for idx, block in enumerate(state["configuration"]["blocks"]):
                            block_type = block.get("block_type", "unknown")
                            block_info = next((b for b in available_blocks if b["block_type"] == block_type), None)

                            if block_info:
                                with st.container():
                                    # Block header with controls
                                    col1, col2, col3, col4, col5 = st.columns([0.5, 4, 1, 1, 1])

                                    with col1:
                                        # Enable/disable toggle
                                        enabled = st.checkbox(
                                            "", value=block.get("enabled", True), key=f"block_enabled_{idx}"
                                        )
                                        block["enabled"] = enabled

                                    with col2:
                                        st.markdown(f"**{block_info['display_name']}**")
                                        st.caption(block_info["description"])

                                    with col3:
                                        # Move up button
                                        if idx > 0 and st.button("⬆️", key=f"move_up_{idx}", help="Move up"):
                                            (
                                                state["configuration"]["blocks"][idx],
                                                state["configuration"]["blocks"][idx - 1],
                                            ) = (
                                                state["configuration"]["blocks"][idx - 1],
                                                state["configuration"]["blocks"][idx],
                                            )
                                            st.rerun()

                                    with col4:
                                        # Move down button
                                        if idx < len(state["configuration"]["blocks"]) - 1 and st.button(
                                            "⬇️", key=f"move_down_{idx}", help="Move down"
                                        ):
                                            (
                                                state["configuration"]["blocks"][idx],
                                                state["configuration"]["blocks"][idx + 1],
                                            ) = (
                                                state["configuration"]["blocks"][idx + 1],
                                                state["configuration"]["blocks"][idx],
                                            )
                                            st.rerun()

                                    with col5:
                                        # Remove button
                                        if st.button("🗑️", key=f"remove_{idx}", help="Remove block"):
                                            state["configuration"]["blocks"].pop(idx)
                                            st.rerun()

                                    # Block configuration (only if enabled)
                                    if enabled and block_info.get("configuration_schema"):
                                        with st.expander("Configuration", expanded=False):
                                            block_config = block.get("config", {})
                                            schema = block_info["configuration_schema"]

                                            # Generate configuration UI based on schema
                                            if "properties" in schema:
                                                for prop_name, prop_schema in schema["properties"].items():
                                                    prop_type = prop_schema.get("type", "string")
                                                    prop_desc = prop_schema.get("description", "")

                                                    if prop_type == "boolean":
                                                        block_config[prop_name] = st.checkbox(
                                                            prop_name.replace("_", " ").title(),
                                                            value=block_config.get(
                                                                prop_name, prop_schema.get("default", False)
                                                            ),
                                                            help=prop_desc,
                                                            key=f"block_{idx}_{prop_name}",
                                                        )
                                                    elif prop_type == "number":
                                                        min_val = prop_schema.get("minimum", 0)
                                                        max_val = prop_schema.get("maximum", 100)
                                                        default_val = prop_schema.get("default", min_val)

                                                        # Determine if we should use int or float based on schema and values
                                                        # If any value has a decimal part, use float for all
                                                        values_to_check = [
                                                            min_val,
                                                            max_val,
                                                            default_val,
                                                            block_config.get(prop_name, default_val),
                                                        ]
                                                        use_float = any(
                                                            isinstance(v, float) and v != int(v)
                                                            for v in values_to_check
                                                        )

                                                        # Convert all values to the same type
                                                        if use_float:
                                                            min_val = float(min_val)
                                                            max_val = float(max_val)
                                                            default_val = float(default_val)
                                                        else:
                                                            min_val = int(min_val)
                                                            max_val = int(max_val)
                                                            default_val = int(default_val)

                                                        # Ensure default value respects min/max constraints
                                                        default_val = max(min_val, min(max_val, default_val))
                                                        current_val = block_config.get(prop_name, default_val)

                                                        # Convert current value to the same type
                                                        if use_float:
                                                            current_val = float(current_val)
                                                        else:
                                                            current_val = int(current_val)

                                                        # Ensure current value respects min/max constraints
                                                        current_val = max(min_val, min(max_val, current_val))

                                                        block_config[prop_name] = st.number_input(
                                                            prop_name.replace("_", " ").title(),
                                                            value=current_val,
                                                            min_value=min_val,
                                                            max_value=max_val,
                                                            help=prop_desc,
                                                            key=f"block_{idx}_{prop_name}",
                                                        )
                                                    elif prop_type == "string" and "enum" in prop_schema:
                                                        block_config[prop_name] = st.selectbox(
                                                            prop_name.replace("_", " ").title(),
                                                            options=prop_schema["enum"],
                                                            index=prop_schema["enum"].index(
                                                                block_config.get(prop_name, prop_schema["enum"][0])
                                                            ),
                                                            help=prop_desc,
                                                            key=f"block_{idx}_{prop_name}",
                                                        )
                                                    elif (
                                                        prop_type == "string"
                                                        and prop_schema.get("x-dynamic-enum") == "generators"
                                                    ):
                                                        # Fetch generators list for AI model selection
                                                        generators_response = api_request(
                                                            "GET", f"{API_BASE_URL}/api/v1/generators"
                                                        )
                                                        if generators_response and "generators" in generators_response:
                                                            generator_names = [
                                                                g["name"] for g in generators_response["generators"]
                                                            ]
                                                            if generator_names:
                                                                current_value = block_config.get(
                                                                    prop_name, generator_names[0]
                                                                )
                                                                # Ensure current value is in the list
                                                                if current_value not in generator_names:
                                                                    current_value = generator_names[0]
                                                                block_config[prop_name] = st.selectbox(
                                                                    prop_name.replace("_", " ").title(),
                                                                    options=generator_names,
                                                                    index=generator_names.index(current_value),
                                                                    help=f"{prop_desc} (Available generators from your configuration)",
                                                                    key=f"block_{idx}_{prop_name}",
                                                                )
                                                            else:
                                                                st.warning(
                                                                    "No generators configured. Please configure generators first."
                                                                )
                                                                block_config[prop_name] = st.text_input(
                                                                    prop_name.replace("_", " ").title(),
                                                                    value=block_config.get(prop_name, "gpt-4"),
                                                                    help=prop_desc,
                                                                    key=f"block_{idx}_{prop_name}",
                                                                )
                                                        else:
                                                            st.error("Failed to fetch generators list")
                                                            block_config[prop_name] = st.text_input(
                                                                prop_name.replace("_", " ").title(),
                                                                value=block_config.get(prop_name, "gpt-4"),
                                                                help=prop_desc,
                                                                key=f"block_{idx}_{prop_name}",
                                                            )
                                                    elif prop_type == "array":
                                                        # Handle array types (like components selection)
                                                        current_values = block_config.get(
                                                            prop_name, prop_schema.get("default", [])
                                                        )
                                                        if "enum" in prop_schema.get("items", {}):
                                                            block_config[prop_name] = st.multiselect(
                                                                prop_name.replace("_", " ").title(),
                                                                options=prop_schema["items"]["enum"],
                                                                default=current_values,
                                                                help=prop_desc,
                                                                key=f"block_{idx}_{prop_name}",
                                                            )
                                                    else:
                                                        # Default text input
                                                        block_config[prop_name] = st.text_input(
                                                            prop_name.replace("_", " ").title(),
                                                            value=block_config.get(
                                                                prop_name, prop_schema.get("default", "")
                                                            ),
                                                            help=prop_desc,
                                                            key=f"block_{idx}_{prop_name}",
                                                        )

                                            block["config"] = block_config

                                    st.divider()
                    else:
                        st.info("No blocks configured. Click 'Add Block' to get started.")
        else:
            st.error("Failed to load available blocks.")

    # --- Schedule Configuration ---
    with config_subtabs[1]:
        st.markdown("### Schedule Configuration")
        st.markdown("Set up automated report generation on a schedule.")

        # Enable/disable scheduling
        enable_schedule = st.checkbox(
            "Enable Scheduled Report Generation", value=state["configuration"]["schedule"] is not None
        )

        if enable_schedule:
            if state["configuration"]["schedule"] is None:
                state["configuration"]["schedule"] = {
                    "frequency": "weekly",
                    "timezone": "UTC",
                    "time": "09:00",
                    "days_of_week": [1],  # Monday
                    "day_of_month": 1,
                    "target_config": {},
                }

            schedule = state["configuration"]["schedule"]

            col1, col2 = st.columns(2)

            with col1:
                # Frequency selection
                schedule["frequency"] = st.selectbox(
                    "Frequency",
                    options=["daily", "weekly", "monthly", "custom"],
                    index=["daily", "weekly", "monthly", "custom"].index(schedule.get("frequency", "weekly")),
                )

                # Time selection
                schedule["time"] = st.time_input(
                    "Time", value=datetime.strptime(schedule.get("time", "09:00"), "%H:%M").time()
                ).strftime("%H:%M")

            with col2:
                # Timezone selection
                if pytz:
                    timezones = pytz.common_timezones
                    schedule["timezone"] = st.selectbox(
                        "Timezone",
                        options=timezones,
                        index=(
                            timezones.index(schedule.get("timezone", "UTC"))
                            if schedule.get("timezone", "UTC") in timezones
                            else 0
                        ),
                    )
                else:
                    schedule["timezone"] = st.text_input(
                        "Timezone",
                        value=schedule.get("timezone", "UTC"),
                        help="Install pytz for timezone selection support",
                    )

            # Frequency-specific options
            if schedule["frequency"] == "weekly":
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                current_days = schedule.get("days_of_week", [0])
                selected_days = st.multiselect(
                    "Days of Week", options=days, default=[days[i] for i in current_days if i < len(days)]
                )
                schedule["days_of_week"] = [days.index(day) for day in selected_days]

            elif schedule["frequency"] == "monthly":
                schedule["day_of_month"] = st.number_input(
                    "Day of Month", min_value=1, max_value=31, value=schedule.get("day_of_month", 1)
                )

            # Target configuration
            st.markdown("#### Target Configuration")
            st.info("Specify which models or endpoints to test for scheduled reports.")

            target_type = st.radio(
                "Target Type", options=["Latest Scan Data", "Specific Models", "All Active Models"], index=0
            )

            schedule["target_config"]["type"] = target_type

            if target_type == "Specific Models":
                # TODO: Load available models from API
                schedule["target_config"]["models"] = st.multiselect(
                    "Select Models",
                    options=["Model A", "Model B", "Model C"],  # Replace with API call
                    default=schedule["target_config"].get("models", []),
                )
        else:
            state["configuration"]["schedule"] = None

    # --- Notifications Configuration ---
    with config_subtabs[2]:
        st.markdown("### Notification Settings")
        st.markdown("Configure how you'll be notified about report generation.")

        # Email notifications
        st.markdown("#### Email Notifications")
        email_config = state["configuration"]["notifications"]["email"]

        email_enabled = st.checkbox("Enable Email Notifications", value=email_config.get("enabled", False))
        email_config["enabled"] = email_enabled

        if email_enabled:
            # Recipients
            recipients_text = st.text_area(
                "Recipients (one per line)",
                value="\n".join(email_config.get("recipients", [])),
                help="Enter email addresses, one per line",
            )
            email_config["recipients"] = [email.strip() for email in recipients_text.split("\n") if email.strip()]

            # Notification triggers
            col1, col2, col3 = st.columns(3)
            with col1:
                email_config["on_success"] = st.checkbox("On Success", value=email_config.get("on_success", True))
            with col2:
                email_config["on_failure"] = st.checkbox("On Failure", value=email_config.get("on_failure", True))
            with col3:
                email_config["include_report"] = st.checkbox(
                    "Attach Report", value=email_config.get("include_report", True)
                )

        st.divider()

        # Webhook notifications
        st.markdown("#### Webhook Notifications")
        webhook_config = state["configuration"]["notifications"]["webhook"]

        webhook_enabled = st.checkbox("Enable Webhook Notifications", value=webhook_config.get("enabled", False))
        webhook_config["enabled"] = webhook_enabled

        if webhook_enabled:
            webhook_config["url"] = st.text_input(
                "Webhook URL", value=webhook_config.get("url", ""), placeholder="https://example.com/webhook"
            )

            # Headers
            with st.expander("Headers (Optional)"):
                headers_text = st.text_area(
                    "Custom Headers (JSON format)",
                    value=json.dumps(webhook_config.get("headers", {}), indent=2),
                    help="Enter headers in JSON format",
                )
                try:
                    webhook_config["headers"] = json.loads(headers_text) if headers_text else {}
                except json.JSONDecodeError:
                    st.error("Invalid JSON format for headers")

            # Advanced settings
            col1, col2 = st.columns(2)
            with col1:
                webhook_config["retry_count"] = st.number_input(
                    "Retry Count", min_value=0, max_value=5, value=webhook_config.get("retry_count", 3)
                )
            with col2:
                webhook_config["timeout"] = st.number_input(
                    "Timeout (seconds)", min_value=5, max_value=300, value=webhook_config.get("timeout", 30)
                )

    # --- Output Configuration ---
    with config_subtabs[3]:
        st.markdown("### Output Format Configuration")
        st.markdown("Select which formats to generate for your report.")

        # Format selection
        available_formats = ["PDF", "JSON", "Markdown", "HTML", "CSV", "Excel"]
        selected_formats = []

        col1, col2 = st.columns(2)
        for i, format_name in enumerate(available_formats):
            with col1 if i % 2 == 0 else col2:
                if st.checkbox(
                    format_name,
                    value=format_name in state["configuration"].get("output_formats", ["PDF", "JSON"]),
                    key=f"format_{format_name}",
                ):
                    selected_formats.append(format_name)

        state["configuration"]["output_formats"] = selected_formats

        if not selected_formats:
            st.warning("Please select at least one output format.")

        # Format-specific options
        if "PDF" in selected_formats:
            with st.expander("PDF Options"):
                pdf_options = state["configuration"].get("pdf_options", {})
                pdf_options["include_toc"] = st.checkbox(
                    "Include Table of Contents", value=pdf_options.get("include_toc", True)
                )
                pdf_options["include_charts"] = st.checkbox(
                    "Include Charts and Visualizations", value=pdf_options.get("include_charts", True)
                )
                pdf_options["page_size"] = st.selectbox(
                    "Page Size",
                    options=["A4", "Letter", "Legal"],
                    index=["A4", "Letter", "Legal"].index(pdf_options.get("page_size", "A4")),
                )
                state["configuration"]["pdf_options"] = pdf_options

        if "CSV" in selected_formats:
            with st.expander("CSV Options"):
                csv_options = state["configuration"].get("csv_options", {})
                csv_options["delimiter"] = st.selectbox(
                    "Delimiter",
                    options=[",", ";", "|", "\\t"],
                    index=[",", ";", "|", "\\t"].index(csv_options.get("delimiter", ",")),
                )
                csv_options["include_headers"] = st.checkbox(
                    "Include Headers", value=csv_options.get("include_headers", True)
                )
                state["configuration"]["csv_options"] = csv_options

    # --- Advanced Configuration ---
    with config_subtabs[4]:
        st.markdown("### Advanced Settings")

        # Report naming
        st.markdown("#### Report Naming")
        state["configuration"]["report_name_template"] = st.text_input(
            "Report Name Template",
            value=state["configuration"].get("report_name_template", "Report_{date}_{time}"),
            help="Available variables: {date}, {time}, {template_name}, {scanner_type}",
        )

        # Priority
        st.markdown("#### Processing Priority")
        state["configuration"]["priority"] = st.select_slider(
            "Priority", options=["low", "normal", "high"], value=state["configuration"].get("priority", "normal")
        )

        # Data retention
        st.markdown("#### Data Retention")
        retention_days = st.number_input(
            "Keep reports for (days)",
            min_value=1,
            max_value=365,
            value=state["configuration"].get("retention_days", 30),
            help="Reports older than this will be automatically deleted",
        )
        state["configuration"]["retention_days"] = retention_days

        # Custom metadata
        st.markdown("#### Custom Metadata")
        with st.expander("Add custom metadata to your report"):
            metadata_text = st.text_area(
                "Metadata (JSON format)",
                value=json.dumps(state["configuration"].get("custom_metadata", {}), indent=2),
                help="Add any custom key-value pairs",
            )
            try:
                state["configuration"]["custom_metadata"] = json.loads(metadata_text) if metadata_text else {}
            except json.JSONDecodeError:
                st.error("Invalid JSON format for metadata")

    # Save configuration button
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 Save Configuration", type="primary", use_container_width=True):
            # Validate configuration
            validation_errors = []

            # Check at least one block is enabled
            enabled_blocks = [b for b in state["configuration"]["blocks"] if b.get("enabled", True)]
            if not enabled_blocks:
                validation_errors.append("At least one block must be enabled")

            # Check output formats
            if not state["configuration"]["output_formats"]:
                validation_errors.append("At least one output format must be selected")

            # Check email recipients if enabled
            if state["configuration"]["notifications"]["email"]["enabled"]:
                if not state["configuration"]["notifications"]["email"]["recipients"]:
                    validation_errors.append("Email notifications enabled but no recipients specified")

            # Check webhook URL if enabled
            if state["configuration"]["notifications"]["webhook"]["enabled"]:
                if not state["configuration"]["notifications"]["webhook"]["url"]:
                    validation_errors.append("Webhook notifications enabled but no URL specified")

            if validation_errors:
                for error in validation_errors:
                    st.error(f"❌ {error}")
            else:
                st.success("✅ Configuration saved successfully!")

                # If schedule is enabled, create/update schedule
                if state["configuration"]["schedule"]:
                    # TODO: Call API to create/update schedule
                    pass

    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            if st.session_state.get("confirm_reset", False):
                # Reset configuration
                state["configuration"] = {
                    "blocks": [],
                    "output_formats": ["PDF", "JSON"],
                    "schedule": None,
                    "notifications": {
                        "email": {"enabled": False, "recipients": []},
                        "webhook": {"enabled": False, "url": None},
                    },
                    "report_name_template": "Report_{date}_{time}",
                    "priority": "normal",
                }
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("Click again to confirm reset")

    # Configuration summary
    with st.expander("📋 Configuration Summary", expanded=False):
        st.json(state["configuration"])

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
