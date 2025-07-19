"""
Streamlit page for Advanced Dashboard Report Setup
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


# Helper functions
def show_error(message: str):
    """Show error message"""
    st.error(message)


def show_success(message: str):
    """Show success message"""
    st.success(message)


def show_warning(message: str):
    """Show warning message"""
    st.warning(message)


def show_info(message: str):
    """Show info message"""
    st.info(message)


# Authentication check
handle_authentication_and_sidebar()

# Initialize session state
if "report_setup" not in st.session_state:
    st.session_state.report_setup = {
        "selected_template": None,
        "selected_scan_data": [],
        "template_config": {},
        "preview_data": None,
        "current_tab": "browse",
        "filter_state": {},
    }


class APIClient:
    """Simple API client for making authenticated requests"""

    def __init__(self):
        self.base_url = os.getenv("APISIX_BASE_URL", "http://localhost:9080")
        self.token = st.session_state.get("jwt_token", "")

    def _get_headers(self):
        """Get headers with JWT token"""
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request"""
        response = requests.get(f"{self.base_url}{endpoint}", headers=self._get_headers(), params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Dict) -> Dict:
        """Make POST request"""
        response = requests.post(f"{self.base_url}{endpoint}", headers=self._get_headers(), json=data)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint: str, data: Dict) -> Dict:
        """Make PUT request"""
        response = requests.put(f"{self.base_url}{endpoint}", headers=self._get_headers(), json=data)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str) -> Dict:
        """Make DELETE request"""
        response = requests.delete(f"{self.base_url}{endpoint}", headers=self._get_headers())
        response.raise_for_status()
        return response.json()


class ReportSetupPage:
    """Report Setup page implementation"""

    def __init__(self):
        self.api_client = APIClient()
        self.setup_state = st.session_state.report_setup

    def render(self):
        """Render the Report Setup page"""
        st.title("📊 Report Generation")
        st.markdown("Create professional security assessment reports from your scan results")

        # Main navigation tabs
        tabs = st.tabs(
            [
                "📁 Data Selection",
                "📋 Template Selection",
                "⚙️ Configuration",
                "👁️ Preview",
                "🚀 Generate",
                "📚 Template Management",
            ]
        )

        with tabs[0]:
            self.render_data_selection()

        with tabs[1]:
            self.render_template_selection()

        with tabs[2]:
            self.render_configuration()

        with tabs[3]:
            self.render_preview()

        with tabs[4]:
            self.render_generation()

        with tabs[5]:
            self.render_template_management()

    def render_data_selection(self):
        """Render scan data selection interface"""
        st.header("Select Scan Data")
        st.markdown("Choose the scan results to include in your report")

        # Filters
        with st.expander("🔍 Filters", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                scanner_type = st.selectbox("Scanner Type", ["All", "PyRIT", "Garak"], key="data_scanner_filter")

                date_range = st.date_input(
                    "Date Range", value=(datetime.now() - timedelta(days=30), datetime.now()), key="data_date_range"
                )

            with col2:
                models = st.multiselect("Target Models", self._get_available_models(), key="data_model_filter")

                min_severity = st.slider("Minimum Severity", 0.0, 10.0, 0.0, key="data_severity_filter")

            with col3:
                datasets = st.multiselect("Datasets", self._get_available_datasets(), key="data_dataset_filter")

                sort_by = st.selectbox(
                    "Sort By", ["Date (Newest)", "Date (Oldest)", "Severity (High)", "Model"], key="data_sort"
                )

        # Browse scan data
        if st.button("🔄 Search Scan Data", type="primary"):
            self._search_scan_data()

        # Display results
        if "scan_results" in self.setup_state:
            self._display_scan_results()

        # Selected data summary
        if self.setup_state["selected_scan_data"]:
            st.divider()
            st.subheader("Selected Scan Data")
            self._display_selected_data_summary()

    def render_template_selection(self):
        """Render template selection interface"""
        st.header("Select Report Template")

        # Check if data is selected
        if not self.setup_state["selected_scan_data"]:
            show_warning("Please select scan data first in the Data Selection tab")
            return

        # Get template recommendations
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📝 Recommended Templates")
            recommendations = self._get_template_recommendations()

            if recommendations:
                for rec in recommendations:
                    with st.container():
                        cols = st.columns([3, 1, 1])
                        with cols[0]:
                            st.markdown(f"**{rec['template_name']}**")
                            st.caption(rec.get("description", ""))

                            # Match reasons
                            reasons = rec.get("match_reasons", [])
                            if reasons:
                                st.markdown("✅ " + " • ".join(reasons))

                        with cols[1]:
                            match_score = rec.get("match_score", 0)
                            st.metric("Match Score", f"{match_score:.0%}")

                        with cols[2]:
                            if st.button("Select", key=f"select_rec_{rec['template_id']}"):
                                self._select_template(rec["template_id"])
                                st.rerun()

                        st.divider()

        with col2:
            st.subheader("🔍 Browse All Templates")

            # Template filters
            category_filter = st.selectbox(
                "Category", ["All", "Security", "Safety", "Reliability", "Compliance"], key="template_category"
            )

            complexity_filter = st.selectbox(
                "Complexity", ["All", "Basic", "Intermediate", "Advanced"], key="template_complexity"
            )

            if st.button("Browse Templates"):
                self._browse_templates(category_filter, complexity_filter)

        # Display selected template
        if self.setup_state["selected_template"]:
            st.divider()
            st.subheader("✅ Selected Template")
            self._display_selected_template()

    def render_configuration(self):
        """Render report configuration interface"""
        st.header("Configure Report")

        # Check prerequisites
        if not self.setup_state["selected_template"]:
            show_warning("Please select a template first")
            return

        template = self.setup_state["selected_template"]

        # Report settings
        col1, col2 = st.columns(2)

        with col1:
            report_name = st.text_input(
                "Report Name", value=f"Security Assessment - {datetime.now().strftime('%Y-%m-%d')}", key="report_name"
            )

            output_formats = st.multiselect(
                "Output Formats", ["PDF", "JSON", "Markdown", "HTML"], default=["PDF", "JSON"], key="output_formats"
            )

        with col2:
            priority = st.select_slider("Priority", ["Low", "Normal", "High"], value="Normal", key="report_priority")

            include_raw_data = st.checkbox("Include Raw Data", value=False, key="include_raw_data")

        st.divider()

        # Block configuration
        st.subheader("📦 Report Blocks Configuration")

        blocks = template.get("config", {}).get("blocks", [])

        for idx, block in enumerate(blocks):
            with st.expander(f"{block.get('title', 'Untitled Block')} ({block['type']})", expanded=False):
                self._render_block_configuration(block, idx)

        # Save configuration
        if st.button("💾 Save Configuration", type="primary"):
            self._save_configuration()
            show_success("Configuration saved successfully")

    def render_preview(self):
        """Render report preview interface"""
        st.header("Preview Report")

        # Check prerequisites
        if not self.setup_state["selected_template"] or not self.setup_state["selected_scan_data"]:
            show_warning("Please complete data and template selection first")
            return

        # Preview options
        col1, col2, col3 = st.columns(3)

        with col1:
            preview_format = st.selectbox("Preview Format", ["HTML", "Markdown"], key="preview_format")

        with col2:
            preview_block = st.selectbox(
                "Preview Block",
                ["All Blocks"]
                + [
                    b.get("title", f"Block {i}")
                    for i, b in enumerate(self.setup_state["selected_template"]["config"]["blocks"])
                ],
                key="preview_block",
            )

        with col3:
            if st.button("🔄 Generate Preview", type="primary"):
                self._generate_preview(preview_format, preview_block)

        # Display preview
        if self.setup_state.get("preview_data"):
            st.divider()
            self._display_preview()

    def render_generation(self):
        """Render report generation interface"""
        st.header("Generate Report")

        # Check prerequisites
        if not self._validate_generation_ready():
            return

        # Generation summary
        st.subheader("📋 Report Summary")

        col1, col2 = st.columns(2)

        with col1:
            st.info(f"**Template:** {self.setup_state['selected_template']['name']}")
            st.info(f"**Data Sources:** {len(self.setup_state['selected_scan_data'])} scan results")
            st.info(f"**Output Formats:** {', '.join(st.session_state.get('output_formats', ['PDF']))}")

        with col2:
            estimated_time = self._estimate_generation_time()
            st.metric("Estimated Time", f"{estimated_time} seconds")

            total_findings = sum(d.get("total_tests", 0) for d in self.setup_state["selected_scan_data"])
            st.metric("Total Findings", total_findings)

        st.divider()

        # Generation options
        col1, col2 = st.columns([3, 1])

        with col1:
            # Notification settings
            st.subheader("🔔 Notifications")

            email_notify = st.checkbox("Email notification on completion", key="email_notify")
            if email_notify:
                email_address = st.text_input(
                    "Email Address", value=st.session_state.get("user_email", ""), key="notify_email"
                )

        with col2:
            st.subheader("🚀 Actions")

            if st.button("Generate Report", type="primary", use_container_width=True):
                self._generate_report()

            if st.button("Schedule Report", use_container_width=True):
                self._show_schedule_dialog()

        # Recent reports
        st.divider()
        st.subheader("📚 Recent Reports")
        self._display_recent_reports()

    def render_template_management(self):
        """Render template management interface"""
        st.header("Template Management")

        tab1, tab2, tab3 = st.tabs(["Browse Templates", "Create Template", "Import/Export"])

        with tab1:
            self._render_template_browser()

        with tab2:
            self._render_template_creator()

        with tab3:
            self._render_template_import_export()

    # Helper methods for data selection

    def _get_available_models(self) -> List[str]:
        """Get list of available models from scan data"""
        try:
            response = self.api_client.get("/api/v1/models")
            return [m["name"] for m in response.get("models", [])]
        except:
            return ["gpt-4", "gpt-3.5-turbo", "claude-3", "llama-2"]

    def _get_available_datasets(self) -> List[str]:
        """Get list of available datasets"""
        try:
            response = self.api_client.get("/api/v1/datasets")
            return [d["name"] for d in response.get("datasets", [])]
        except:
            return ["OWASP Top 10", "Custom Prompts", "Safety Benchmark"]

    def _search_scan_data(self):
        """Search for scan data based on filters"""
        try:
            # Build request
            request = {
                "scanner_type": st.session_state.get("data_scanner_filter", "All"),
                "date_range": {
                    "start": st.session_state["data_date_range"][0].isoformat(),
                    "end": st.session_state["data_date_range"][1].isoformat(),
                },
                "model_filter": st.session_state.get("data_model_filter", []),
                "severity_filter": (
                    ["High", "Critical"] if st.session_state.get("data_severity_filter", 0) > 7 else None
                ),
                "limit": 50,
            }

            # Clean up request
            request = {k: v for k, v in request.items() if v}

            response = self.api_client.post("/api/v1/reports/scan-data/browse", request)
            self.setup_state["scan_results"] = response.get("results", [])

        except Exception as e:
            show_error(f"Error searching scan data: {str(e)}")

    def _display_scan_results(self):
        """Display scan data search results"""
        results = self.setup_state.get("scan_results", [])

        if not results:
            st.info("No scan data found matching your criteria")
            return

        # Create dataframe for display
        df_data = []
        for result in results:
            df_data.append(
                {
                    "Select": False,
                    "ID": result["execution_id"][:8] + "...",
                    "Scanner": result["scanner_type"],
                    "Model": result["target_model"],
                    "Date": result["scan_date"],
                    "Tests": result["total_tests"],
                    "Risk Score": result.get("score_summary", {}).get("risk_score", 0),
                    "Critical": result.get("severity_distribution", {}).get("Critical", 0),
                }
            )

        df = pd.DataFrame(df_data)

        # Display with selection
        edited_df = st.data_editor(
            df,
            column_config={
                "Select": st.column_config.CheckboxColumn(
                    "Select",
                    help="Select scan data to include in report",
                    default=False,
                ),
                "Risk Score": st.column_config.NumberColumn(
                    "Risk Score",
                    format="%.1f",
                ),
            },
            disabled=["ID", "Scanner", "Model", "Date", "Tests", "Risk Score", "Critical"],
            hide_index=True,
            key="scan_data_selection",
        )

        # Update selected data
        selected_indices = edited_df[edited_df["Select"]].index.tolist()
        self.setup_state["selected_scan_data"] = [results[i] for i in selected_indices]

        # Selection summary
        if selected_indices:
            st.success(f"Selected {len(selected_indices)} scan results")

    def _display_selected_data_summary(self):
        """Display summary of selected scan data"""
        selected = self.setup_state["selected_scan_data"]

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Selected Scans", len(selected))

        with col2:
            total_tests = sum(d.get("total_tests", 0) for d in selected)
            st.metric("Total Tests", total_tests)

        with col3:
            avg_risk = sum(d.get("score_summary", {}).get("risk_score", 0) for d in selected) / len(selected)
            st.metric("Avg Risk Score", f"{avg_risk:.1f}")

        with col4:
            scanners = list(set(d["scanner_type"] for d in selected))
            st.metric("Scanner Types", ", ".join(scanners))

        # Details expander
        with st.expander("View Details"):
            for idx, scan in enumerate(selected):
                st.markdown(f"**{idx + 1}. {scan['target_model']}** - {scan['scanner_type']}")
                st.caption(f"Date: {scan['scan_date']} | Tests: {scan['total_tests']}")

    # Helper methods for template selection

    def _get_template_recommendations(self) -> List[Dict]:
        """Get template recommendations based on selected data"""
        try:
            # Aggregate scan data for recommendations
            scan_summary = {
                "scanner_type": list(set(d["scanner_type"] for d in self.setup_state["selected_scan_data"])),
                "vulnerabilities": [],
                "total_tests": sum(d.get("total_tests", 0) for d in self.setup_state["selected_scan_data"]),
                "has_toxicity_data": any(
                    "toxicity" in str(d.get("key_findings", [])).lower() for d in self.setup_state["selected_scan_data"]
                ),
            }

            response = self.api_client.post("/api/v1/reports/templates/recommend", scan_summary)

            return response.get("recommendations", [])[:5]

        except Exception as e:
            show_error(f"Error getting recommendations: {str(e)}")
            return []

    def _select_template(self, template_id: str):
        """Select a template"""
        try:
            template = self.api_client.get(f"/api/v1/reports/templates/{template_id}")
            self.setup_state["selected_template"] = template
            self.setup_state["template_config"] = template.get("config", {}).copy()
            show_success(f"Selected template: {template['name']}")
        except Exception as e:
            show_error(f"Error selecting template: {str(e)}")

    def _browse_templates(self, category: str, complexity: str):
        """Browse all templates with filters"""
        try:
            params = {}
            if category != "All":
                params["testing_category"] = category
            if complexity != "All":
                params["complexity_level"] = complexity

            response = self.api_client.get("/api/v1/reports/templates", params=params)
            templates = response.get("templates", [])

            # Display templates in a grid
            for template in templates:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])

                    with col1:
                        st.markdown(f"**{template['name']}**")
                        st.caption(template.get("description", ""))

                        # Metadata badges
                        metadata = template.get("metadata", {})
                        badges = []
                        if metadata.get("testing_category"):
                            badges.extend(metadata["testing_category"])
                        if metadata.get("complexity_level"):
                            badges.append(metadata["complexity_level"])

                        if badges:
                            st.markdown(" ".join([f"`{b}`" for b in badges]))

                    with col2:
                        usage = metadata.get("usage_count", 0)
                        st.metric("Uses", usage)

                    with col3:
                        if st.button("Select", key=f"select_browse_{template['id']}"):
                            self._select_template(template["id"])
                            st.rerun()

                    st.divider()

        except Exception as e:
            show_error(f"Error browsing templates: {str(e)}")

    def _display_selected_template(self):
        """Display selected template details"""
        template = self.setup_state["selected_template"]

        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**{template['name']}**")
            st.caption(template.get("description", ""))

            # Show blocks
            blocks = template.get("config", {}).get("blocks", [])
            st.markdown(f"**Blocks:** {len(blocks)}")
            block_names = [b.get("title", b["type"]) for b in blocks]
            st.markdown("• " + " • ".join(block_names))

        with col2:
            if st.button("Change Template"):
                self.setup_state["selected_template"] = None
                st.rerun()

    # Helper methods for configuration

    def _render_block_configuration(self, block: Dict, idx: int):
        """Render configuration UI for a block"""
        block_type = block["type"]
        config = block.get("configuration", {})

        # Common settings
        col1, col2 = st.columns(2)

        with col1:
            new_title = st.text_input("Title", value=block.get("title", ""), key=f"block_title_{idx}")
            block["title"] = new_title

        with col2:
            enabled = st.checkbox("Enabled", value=block.get("enabled", True), key=f"block_enabled_{idx}")
            block["enabled"] = enabled

        # Block-specific configuration
        if block_type == "executive_summary":
            self._config_executive_summary(config, idx)
        elif block_type == "ai_analysis":
            self._config_ai_analysis(config, idx)
        elif block_type == "security_metrics":
            self._config_security_metrics(config, idx)
        elif block_type == "toxicity_heatmap":
            self._config_toxicity_heatmap(config, idx)
        elif block_type == "custom_content":
            self._config_custom_content(config, idx)

    def _config_executive_summary(self, config: Dict, idx: int):
        """Configure executive summary block"""
        components = st.multiselect(
            "Components to Include",
            [
                "Overall Risk Score",
                "Critical Vulnerabilities Count",
                "Model Performance",
                "Compliance Score",
                "Key Findings Summary",
            ],
            default=config.get("components", ["Overall Risk Score", "Critical Vulnerabilities Count"]),
            key=f"exec_components_{idx}",
        )
        config["components"] = components

        threshold = st.select_slider(
            "Highlight Threshold",
            ["Critical Only", "High and Above", "Medium and Above", "All"],
            value=config.get("highlight_threshold", "High and Above"),
            key=f"exec_threshold_{idx}",
        )
        config["highlight_threshold"] = threshold

        max_findings = st.number_input(
            "Maximum Findings to Show",
            min_value=1,
            max_value=20,
            value=config.get("max_findings", 5),
            key=f"exec_findings_{idx}",
        )
        config["max_findings"] = max_findings

    def _config_ai_analysis(self, config: Dict, idx: int):
        """Configure AI analysis block"""
        focus_areas = st.multiselect(
            "Analysis Focus Areas",
            [
                "Vulnerability Assessment",
                "Attack Pattern Analysis",
                "Defense Recommendations",
                "Compliance Gaps",
                "Risk Mitigation",
            ],
            default=config.get("analysis_focus", ["Vulnerability Assessment", "Defense Recommendations"]),
            key=f"ai_focus_{idx}",
        )
        config["analysis_focus"] = focus_areas

        col1, col2 = st.columns(2)

        with col1:
            model = st.selectbox(
                "AI Model",
                ["gpt-4", "gpt-3.5-turbo", "claude-3"],
                index=["gpt-4", "gpt-3.5-turbo", "claude-3"].index(config.get("ai_model", "gpt-4")),
                key=f"ai_model_{idx}",
            )
            config["ai_model"] = model

        with col2:
            include_rec = st.checkbox(
                "Include Recommendations", value=config.get("include_recommendations", True), key=f"ai_rec_{idx}"
            )
            config["include_recommendations"] = include_rec

        # Custom prompt
        if st.checkbox("Use Custom Prompt", key=f"ai_custom_{idx}"):
            prompt = st.text_area(
                "Custom Prompt Template",
                value=config.get("prompt", ""),
                help="Use {{variable_name}} for variables",
                key=f"ai_prompt_{idx}",
            )
            config["prompt"] = prompt

    def _config_security_metrics(self, config: Dict, idx: int):
        """Configure security metrics block"""
        visualizations = st.multiselect(
            "Visualizations",
            ["Metric Cards", "Risk Heatmap", "Trend Charts", "Distribution Charts", "Compliance Matrix"],
            default=config.get("visualizations", ["Metric Cards", "Risk Heatmap"]),
            key=f"metrics_viz_{idx}",
        )
        config["visualizations"] = visualizations

        col1, col2 = st.columns(2)

        with col1:
            source = st.selectbox(
                "Metric Source",
                ["PyRIT", "Garak", "Combined"],
                index=["PyRIT", "Garak", "Combined"].index(config.get("metric_source", "Combined")),
                key=f"metrics_source_{idx}",
            )
            config["metric_source"] = source

        with col2:
            benchmarks = st.checkbox(
                "Include Benchmarks", value=config.get("include_benchmarks", True), key=f"metrics_bench_{idx}"
            )
            config["include_benchmarks"] = benchmarks

    def _config_toxicity_heatmap(self, config: Dict, idx: int):
        """Configure toxicity heatmap block"""
        categories = st.multiselect(
            "Toxicity Categories",
            ["hate", "harassment", "violence", "self-harm", "sexual", "profanity", "derogatory", "threat"],
            default=config.get("categories", ["hate", "harassment", "violence", "self-harm"]),
            key=f"tox_categories_{idx}",
        )
        config["categories"] = categories

        col1, col2 = st.columns(2)

        with col1:
            aggregation = st.selectbox(
                "Aggregation Method",
                ["mean", "max", "min", "p95"],
                index=["mean", "max", "min", "p95"].index(config.get("aggregation", "mean")),
                key=f"tox_agg_{idx}",
            )
            config["aggregation"] = aggregation

        with col2:
            color_scheme = st.selectbox(
                "Color Scheme",
                ["red_scale", "blue_scale", "diverging", "traffic_light"],
                index=["red_scale", "blue_scale", "diverging", "traffic_light"].index(
                    config.get("color_scheme", "red_scale")
                ),
                key=f"tox_color_{idx}",
            )
            config["color_scheme"] = color_scheme

    def _config_custom_content(self, config: Dict, idx: int):
        """Configure custom content block"""
        content_type = st.selectbox(
            "Content Type",
            ["General", "Disclaimer", "Methodology", "References", "Appendix"],
            index=["General", "Disclaimer", "Methodology", "References", "Appendix"].index(
                config.get("content_type", "General")
            ),
            key=f"custom_type_{idx}",
        )
        config["content_type"] = content_type

        content = st.text_area(
            "Markdown Content",
            value=config.get("content", ""),
            height=200,
            help="Use {{variable_name}} for variables",
            key=f"custom_content_{idx}",
        )
        config["content"] = content

        # Show available variables
        if st.checkbox("Show Available Variables", key=f"custom_vars_{idx}"):
            self._show_available_variables()

    def _show_available_variables(self):
        """Show available report variables"""
        try:
            variables = self.api_client.get("/api/v1/reports/variables")

            # Group by category
            categories = {}
            for var in variables:
                cat = var["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(var)

            # Display
            for cat, vars in categories.items():
                with st.expander(f"{cat.title()} Variables"):
                    for var in vars:
                        st.markdown(f"**{{{{ {var['variable_name']} }}}}** - {var['description']}")
                        st.caption(f"Type: {var['data_type']} | Example: {var['example_value']}")

        except Exception as e:
            show_error(f"Error loading variables: {str(e)}")

    def _save_configuration(self):
        """Save report configuration"""
        self.setup_state["report_config"] = {
            "name": st.session_state.get("report_name", "Untitled Report"),
            "output_formats": st.session_state.get("output_formats", ["PDF"]),
            "priority": st.session_state.get("report_priority", "Normal"),
            "include_raw_data": st.session_state.get("include_raw_data", False),
            "template_config": self.setup_state["template_config"],
        }

    # Helper methods for preview

    def _generate_preview(self, format: str, block: str):
        """Generate report preview"""
        try:
            # Prepare sample data
            sample_data = self._prepare_sample_data()

            # Build preview request
            request = {
                "template_config": self.setup_state["template_config"],
                "sample_data": sample_data,
                "output_format": format,
            }

            # Add specific block if selected
            if block != "All Blocks":
                block_idx = int(block.split()[-1]) if block.split()[-1].isdigit() else 0
                blocks = self.setup_state["template_config"].get("blocks", [])
                if 0 <= block_idx < len(blocks):
                    request["block_id"] = blocks[block_idx].get("id")

            response = self.api_client.post("/api/v1/reports/preview", request)
            self.setup_state["preview_data"] = response

        except Exception as e:
            show_error(f"Error generating preview: {str(e)}")

    def _prepare_sample_data(self) -> Dict:
        """Prepare sample data for preview"""
        # Use first selected scan data or generate sample
        if self.setup_state["selected_scan_data"]:
            return self.setup_state["selected_scan_data"][0]

        return {
            "scanner_type": "pyrit",
            "target_model": "gpt-4",
            "scan_date": datetime.now().isoformat(),
            "total_tests": 100,
            "successful_attacks": 15,
            "failure_rate": 15.0,
            "risk_score": 7.5,
            "compliance_score": 85.0,
            "total_vulnerabilities": 12,
            "critical_count": 2,
            "high_count": 5,
            "medium_count": 3,
            "low_count": 2,
            "vulnerabilities": [
                {"type": "Prompt Injection", "severity": "High", "count": 5},
                {"type": "Jailbreak", "severity": "Critical", "count": 2},
            ],
        }

    def _display_preview(self):
        """Display report preview"""
        preview = self.setup_state["preview_data"]

        # Preview metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Estimated Pages", preview.get("estimated_pages", 1))

        with col2:
            st.metric("Processing Time", f"{preview.get('processing_time', 0):.2f}s")

        with col3:
            warnings = preview.get("warnings", [])
            st.metric("Warnings", len(warnings))

        # Show warnings if any
        if warnings:
            with st.expander("⚠️ Warnings"):
                for warning in warnings:
                    st.warning(warning)

        # Display content
        st.divider()

        if preview.get("html_content"):
            st.markdown("### Preview (HTML)")
            st.components.v1.html(preview["html_content"], height=800, scrolling=True)
        elif preview.get("markdown_content"):
            st.markdown("### Preview (Markdown)")
            st.markdown(preview["markdown_content"])

    # Helper methods for generation

    def _validate_generation_ready(self) -> bool:
        """Validate if ready to generate report"""
        if not self.setup_state["selected_scan_data"]:
            show_error("Please select scan data")
            return False

        if not self.setup_state["selected_template"]:
            show_error("Please select a template")
            return False

        if not st.session_state.get("output_formats"):
            show_error("Please select at least one output format")
            return False

        return True

    def _estimate_generation_time(self) -> int:
        """Estimate report generation time"""
        base_time = 10

        # Add time for data
        data_time = len(self.setup_state["selected_scan_data"]) * 2

        # Add time for formats
        format_time = len(st.session_state.get("output_formats", [])) * 5

        # Add time for complexity
        template = self.setup_state["selected_template"]
        complexity = template.get("metadata", {}).get("complexity_level", "Intermediate")
        complexity_multiplier = {"Basic": 1, "Intermediate": 1.5, "Advanced": 2}.get(complexity, 1.5)

        return int((base_time + data_time + format_time) * complexity_multiplier)

    def _generate_report(self):
        """Generate the report"""
        try:
            # Build request
            request = {
                "template_id": self.setup_state["selected_template"]["id"],
                "scan_data_ids": [d["execution_id"] for d in self.setup_state["selected_scan_data"]],
                "output_formats": st.session_state.get("output_formats", ["PDF"]),
                "report_name": st.session_state.get("report_name", "Untitled Report"),
                "priority": st.session_state.get("report_priority", "Normal").lower(),
                "configuration_overrides": self._get_config_overrides(),
            }

            # Add notification config if enabled
            if st.session_state.get("email_notify"):
                request["notification_config"] = {
                    "email": {
                        "enabled": True,
                        "recipients": [st.session_state.get("notify_email", "")],
                        "on_success": True,
                        "on_failure": True,
                        "include_report": True,
                    }
                }

            response = self.api_client.post("/api/v1/reports/generate", request)

            # Show success and report info
            show_success(f"Report generation started! Report ID: {response['report_id']}")

            # Display generation info
            with st.expander("Generation Details", expanded=True):
                st.json(
                    {
                        "report_id": response["report_id"],
                        "status": response["status"],
                        "estimated_time": f"{response['estimated_time']} seconds",
                        "queue_position": response.get("queue_position"),
                    }
                )

            # Add to recent reports
            if "recent_reports" not in st.session_state:
                st.session_state.recent_reports = []

            st.session_state.recent_reports.insert(
                0,
                {
                    "report_id": response["report_id"],
                    "name": request["report_name"],
                    "created_at": datetime.now(),
                    "status": "pending",
                },
            )

        except Exception as e:
            show_error(f"Error generating report: {str(e)}")

    def _get_config_overrides(self) -> Dict:
        """Get configuration overrides from UI"""
        overrides = {}

        # Compare current config with original template config
        original = self.setup_state["selected_template"]["config"]
        current = self.setup_state["template_config"]

        # Check for block-level changes
        for idx, block in enumerate(current.get("blocks", [])):
            orig_block = original["blocks"][idx] if idx < len(original["blocks"]) else {}

            if block.get("configuration") != orig_block.get("configuration"):
                block_id = block.get("id", f"block_{idx}")
                overrides[block_id] = block["configuration"]

        return overrides

    def _show_schedule_dialog(self):
        """Show report scheduling dialog"""
        with st.expander("📅 Schedule Report", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                frequency = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"], key="schedule_frequency")

                time = st.time_input("Time", value=datetime.now().time(), key="schedule_time")

            with col2:
                if frequency == "Weekly":
                    day = st.selectbox(
                        "Day of Week",
                        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                        key="schedule_day",
                    )
                elif frequency == "Monthly":
                    day = st.number_input("Day of Month", min_value=1, max_value=28, value=1, key="schedule_day_month")

                timezone = st.selectbox(
                    "Timezone", ["UTC", "US/Eastern", "US/Pacific", "Europe/London"], key="schedule_timezone"
                )

            if st.button("Create Schedule", type="primary"):
                self._create_schedule()

    def _create_schedule(self):
        """Create report schedule"""
        try:
            # Build schedule request
            frequency_config = {"time": st.session_state["schedule_time"].strftime("%H:%M")}

            if st.session_state["schedule_frequency"] == "Weekly":
                frequency_config["day_of_week"] = st.session_state.get("schedule_day", "Monday")
            elif st.session_state["schedule_frequency"] == "Monthly":
                frequency_config["day_of_month"] = st.session_state.get("schedule_day_month", 1)

            request = {
                "name": f"Scheduled: {st.session_state.get('report_name', 'Report')}",
                "template_id": self.setup_state["selected_template"]["id"],
                "frequency": st.session_state["schedule_frequency"].lower(),
                "frequency_config": frequency_config,
                "target_config": {
                    "scan_data_selection": {
                        "strategy": "latest",
                        "filters": {"models": [d["target_model"] for d in self.setup_state["selected_scan_data"]]},
                    }
                },
                "timezone": st.session_state.get("schedule_timezone", "UTC"),
            }

            response = self.api_client.post("/api/v1/reports/schedules", request)
            show_success(f"Schedule created successfully! ID: {response['id']}")

        except Exception as e:
            show_error(f"Error creating schedule: {str(e)}")

    def _display_recent_reports(self):
        """Display recent reports"""
        recent = st.session_state.get("recent_reports", [])

        if not recent:
            st.info("No recent reports")
            return

        # Display reports
        for report in recent[:5]:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                with col1:
                    st.markdown(f"**{report['name']}**")
                    st.caption(f"ID: {report['report_id'][:8]}...")

                with col2:
                    st.caption(report["created_at"].strftime("%Y-%m-%d %H:%M"))

                with col3:
                    # Get current status
                    status = self._get_report_status(report["report_id"])
                    if status == "completed":
                        st.success("Completed")
                    elif status == "processing":
                        st.info("Processing")
                    elif status == "failed":
                        st.error("Failed")
                    else:
                        st.warning("Pending")

                with col4:
                    if status == "completed":
                        if st.button("Download", key=f"download_{report['report_id']}"):
                            self._download_report(report["report_id"])

                st.divider()

    def _get_report_status(self, report_id: str) -> str:
        """Get report status"""
        try:
            response = self.api_client.get(f"/api/v1/reports/status/{report_id}")
            return response.get("status", "unknown")
        except:
            return "unknown"

    def _download_report(self, report_id: str):
        """Download completed report"""
        try:
            # Get download links
            response = self.api_client.get(f"/api/v1/reports/download/{report_id}")
            if response:
                download_data = response
                formats = download_data.get("formats", {})

                if formats:
                    st.subheader("📥 Download Options")

                    # Create download buttons
                    cols = st.columns(min(len(formats), 4))
                    for idx, (format_type, format_info) in enumerate(formats.items()):
                        with cols[idx % len(cols)]:
                            if format_info.get("available", False):
                                file_size = format_info.get("size", 0)
                                size_mb = file_size / (1024 * 1024) if file_size > 0 else 0

                                download_url = (
                                    f"{self.api_client.base_url}/api/v1/reports/download/{report_id}/{format_type}"
                                )

                                st.markdown(
                                    f"""
                                <a href="{download_url}" target="_blank">
                                    <button style="
                                        background-color: #4CAF50;
                                        border: none;
                                        color: white;
                                        padding: 12px 16px;
                                        text-align: center;
                                        text-decoration: none;
                                        display: inline-block;
                                        font-size: 14px;
                                        margin: 4px 2px;
                                        cursor: pointer;
                                        border-radius: 4px;
                                        width: 100%;
                                    ">
                                        📄 {format_type.upper()}<br>
                                        <small>({size_mb:.1f} MB)</small>
                                    </button>
                                </a>
                                """,
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.warning(f"{format_type.upper()} not available")
                else:
                    show_error("No outputs available for this report")
            else:
                show_error("Could not retrieve download information")

        except Exception as e:
            show_error(f"Error downloading report: {str(e)}")

    # Template management methods

    def _render_template_browser(self):
        """Render template browser"""
        # Search and filters
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            search_query = st.text_input(
                "Search Templates", placeholder="Search by name or description...", key="template_search"
            )

        with col2:
            category_filter = st.selectbox(
                "Category", ["All", "Security", "Safety", "Reliability", "Compliance"], key="browse_category"
            )

        with col3:
            if st.button("Search", type="primary"):
                self._search_templates(search_query, category_filter)

        # Results
        if "template_search_results" in st.session_state:
            templates = st.session_state.template_search_results

            if not templates:
                st.info("No templates found")
            else:
                for template in templates:
                    with st.expander(template["name"]):
                        self._display_template_details(template)

    def _render_template_creator(self):
        """Render template creation interface"""
        st.subheader("Create New Template")

        # Basic info
        name = st.text_input("Template Name", key="create_name")
        description = st.text_area("Description", key="create_description")

        # Metadata
        col1, col2 = st.columns(2)

        with col1:
            categories = st.multiselect(
                "Testing Categories",
                ["Security", "Safety", "Reliability", "Robustness", "Compliance"],
                key="create_categories",
            )

            attack_types = st.multiselect(
                "Attack Categories",
                [
                    "Prompt Injection",
                    "Jailbreak",
                    "Data Leakage",
                    "Hallucination",
                    "Bias",
                    "Toxicity",
                    "Harmful Content",
                ],
                key="create_attacks",
            )

        with col2:
            complexity = st.select_slider(
                "Complexity Level", ["Basic", "Intermediate", "Advanced"], value="Intermediate", key="create_complexity"
            )

            output_formats = st.multiselect(
                "Supported Formats", ["PDF", "JSON", "Markdown", "HTML"], default=["PDF", "JSON"], key="create_formats"
            )

        # Block builder
        st.divider()
        st.subheader("Template Blocks")

        if "create_blocks" not in st.session_state:
            st.session_state.create_blocks = []

        # Add block button
        col1, col2 = st.columns([2, 1])

        with col1:
            block_type = st.selectbox(
                "Add Block",
                ["executive_summary", "ai_analysis", "security_metrics", "toxicity_heatmap", "custom_content"],
                key="add_block_type",
            )

        with col2:
            if st.button("Add Block", type="primary"):
                self._add_template_block(block_type)

        # Display blocks
        for idx, block in enumerate(st.session_state.create_blocks):
            with st.expander(f"{block['title']} ({block['type']})"):
                self._render_template_block_editor(block, idx)

        # Save template
        st.divider()
        if st.button("💾 Save Template", type="primary", disabled=not name):
            self._save_new_template()

    def _render_template_import_export(self):
        """Render template import/export interface"""
        tab1, tab2 = st.tabs(["Export", "Import"])

        with tab1:
            st.subheader("Export Templates")

            # Select templates to export
            templates = self._get_all_templates()
            selected = st.multiselect(
                "Select Templates to Export",
                [f"{t['name']} (v{t['version']})" for t in templates],
                key="export_templates",
            )

            if selected and st.button("Export Selected", type="primary"):
                self._export_templates(selected)

        with tab2:
            st.subheader("Import Templates")

            uploaded = st.file_uploader("Upload Template File", type=["json"], key="import_file")

            if uploaded:
                try:
                    content = json.loads(uploaded.read())
                    st.json(content)

                    if st.button("Import Templates", type="primary"):
                        self._import_templates(content)
                except Exception as e:
                    show_error(f"Error reading file: {str(e)}")

    def _search_templates(self, query: str, category: str):
        """Search templates"""
        try:
            if query:
                response = self.api_client.get("/api/v1/reports/templates/search", params={"q": query})
                templates = response
            else:
                params = {}
                if category != "All":
                    params["testing_category"] = category

                response = self.api_client.get("/api/v1/reports/templates", params=params)
                templates = response.get("templates", [])

            st.session_state.template_search_results = templates

        except Exception as e:
            show_error(f"Error searching templates: {str(e)}")

    def _display_template_details(self, template: Dict):
        """Display detailed template information"""
        st.markdown(f"**Description:** {template.get('description', 'N/A')}")
        st.markdown(f"**Version:** {template.get('version', '1.0.0')}")

        # Metadata
        metadata = template.get("metadata", {})
        if metadata:
            st.json(metadata)

        # Actions
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Use Template", key=f"use_{template['id']}"):
                self._select_template(template["id"])
                st.rerun()

        with col2:
            if st.button("Duplicate", key=f"dup_{template['id']}"):
                self._duplicate_template(template["id"])

        with col3:
            if st.button("Version History", key=f"hist_{template['id']}"):
                self._show_version_history(template["id"])

    def _add_template_block(self, block_type: str):
        """Add a block to template being created"""
        block = {
            "id": f"{block_type}_{len(st.session_state.create_blocks) + 1}",
            "type": block_type,
            "title": block_type.replace("_", " ").title(),
            "configuration": self._get_default_block_config(block_type),
            "order": len(st.session_state.create_blocks) + 1,
        }

        st.session_state.create_blocks.append(block)

    def _get_default_block_config(self, block_type: str) -> Dict:
        """Get default configuration for block type"""
        defaults = {
            "executive_summary": {
                "components": ["Overall Risk Score", "Critical Vulnerabilities Count"],
                "highlight_threshold": "High and Above",
                "max_findings": 5,
            },
            "ai_analysis": {
                "analysis_focus": ["Vulnerability Assessment"],
                "ai_model": "gpt-4",
                "include_recommendations": True,
            },
            "security_metrics": {"visualizations": ["Metric Cards", "Risk Heatmap"], "metric_source": "Combined"},
            "toxicity_heatmap": {"categories": ["hate", "harassment", "violence"], "aggregation": "mean"},
            "custom_content": {"content": "", "content_type": "General"},
        }

        return defaults.get(block_type, {})

    def _render_template_block_editor(self, block: Dict, idx: int):
        """Render block editor in template creator"""
        # Block settings
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            block["title"] = st.text_input("Title", value=block["title"], key=f"create_block_title_{idx}")

        with col2:
            block["order"] = st.number_input(
                "Order", min_value=1, value=block["order"], key=f"create_block_order_{idx}"
            )

        with col3:
            if st.button("Remove", key=f"remove_block_{idx}"):
                st.session_state.create_blocks.pop(idx)
                st.rerun()

        # Block configuration (simplified)
        st.json(block["configuration"])

    def _save_new_template(self):
        """Save newly created template"""
        try:
            # Build template data
            template_data = {
                "name": st.session_state.get("create_name"),
                "description": st.session_state.get("create_description", ""),
                "config": {"blocks": st.session_state.create_blocks},
                "metadata": {
                    "testing_category": st.session_state.get("create_categories", []),
                    "attack_categories": st.session_state.get("create_attacks", []),
                    "complexity_level": st.session_state.get("create_complexity", "Intermediate"),
                    "output_formats": st.session_state.get("create_formats", ["PDF", "JSON"]),
                },
            }

            response = self.api_client.post("/api/v1/reports/templates", template_data)

            show_success(f"Template created successfully! ID: {response['id']}")

            # Clear form
            st.session_state.create_blocks = []
            for key in [
                "create_name",
                "create_description",
                "create_categories",
                "create_attacks",
                "create_complexity",
                "create_formats",
            ]:
                if key in st.session_state:
                    del st.session_state[key]

        except Exception as e:
            show_error(f"Error creating template: {str(e)}")

    def _get_all_templates(self) -> List[Dict]:
        """Get all templates"""
        try:
            response = self.api_client.get("/api/v1/reports/templates", params={"limit": 100})
            return response.get("templates", [])
        except:
            return []

    def _export_templates(self, selected: List[str]):
        """Export selected templates"""
        try:
            templates = self._get_all_templates()
            export_data = {"version": "1.0", "exported_at": datetime.now().isoformat(), "templates": []}

            # Filter selected templates
            for template in templates:
                template_label = f"{template['name']} (v{template['version']})"
                if template_label in selected:
                    export_data["templates"].append(template)

            # Download
            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                label="Download Export",
                data=json_str,
                file_name=f"templates_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

        except Exception as e:
            show_error(f"Error exporting templates: {str(e)}")

    def _import_templates(self, data: Dict):
        """Import templates from file"""
        try:
            imported = 0

            for template in data.get("templates", []):
                # Remove ID to create new
                template.pop("id", None)
                template.pop("created_at", None)
                template.pop("updated_at", None)

                try:
                    self.api_client.post("/api/v1/reports/templates", template)
                    imported += 1
                except Exception as e:
                    show_warning(f"Failed to import '{template['name']}': {str(e)}")

            show_success(f"Successfully imported {imported} templates")

        except Exception as e:
            show_error(f"Error importing templates: {str(e)}")

    def _duplicate_template(self, template_id: str):
        """Duplicate a template"""
        try:
            # Get template
            template = self.api_client.get(f"/api/v1/reports/templates/{template_id}")

            # Modify for duplication
            template["name"] = f"{template['name']} (Copy)"
            template.pop("id", None)

            # Create new
            response = self.api_client.post("/api/v1/reports/templates", template)

            show_success(f"Template duplicated successfully! ID: {response['id']}")

        except Exception as e:
            show_error(f"Error duplicating template: {str(e)}")

    def _show_version_history(self, template_id: str):
        """Show template version history"""
        try:
            versions = self.api_client.get(f"/api/v1/reports/templates/{template_id}/versions")

            if versions:
                with st.expander("Version History", expanded=True):
                    for version in versions:
                        col1, col2, col3 = st.columns([2, 2, 1])

                        with col1:
                            st.markdown(f"**v{version['version']}**")
                            st.caption(version["created_at"])

                        with col2:
                            st.caption(version.get("change_notes", "No notes"))

                        with col3:
                            if st.button("Restore", key=f"restore_{version['id']}"):
                                self._restore_template_version(template_id, version["id"])
            else:
                st.info("No version history available")

        except Exception as e:
            show_error(f"Error loading version history: {str(e)}")

    def _restore_template_version(self, template_id: str, version_id: str):
        """Restore template to previous version"""
        try:
            response = self.api_client.post(f"/api/v1/reports/templates/{template_id}/versions/{version_id}/restore")

            show_success("Template restored successfully!")
            st.rerun()

        except Exception as e:
            show_error(f"Error restoring version: {str(e)}")


# Main execution
if __name__ == "__main__":
    page = ReportSetupPage()
    page.render()
