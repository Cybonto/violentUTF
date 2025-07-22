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
    # Report endpoints
    "report_templates": f"{API_BASE_URL}/api/v1/reports/templates",
    "report_templates_init": f"{API_BASE_URL}/api/v1/reports/templates/initialize",
    "report_generate": f"{API_BASE_URL}/api/v1/reports/generate",
    "report_preview": f"{API_BASE_URL}/api/v1/reports/preview",
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
