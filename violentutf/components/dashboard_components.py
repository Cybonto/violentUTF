#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Dashboard Components for Issue #284

Provides reusable dashboard components for asset management, risk assessment,
compliance monitoring, and executive reporting.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def create_filter_sidebar() -> Dict[str, Any]:
    """Create a reusable filter sidebar component"""
    with st.sidebar:
        st.header("🔍 Dashboard Filters")

        filters: Dict[str, Any] = {}

        # Time range filter
        time_range = st.selectbox(
            "Time Range",
            options=["Last 7 days", "Last 30 days", "Last 90 days", "Last 6 months", "Last year"],
            index=1,
            help="Select time range for data analysis",
        )
        filters["time_range"] = time_range

        # Asset type filter
        asset_types = st.multiselect(
            "Asset Types",
            options=["POSTGRESQL", "SQLITE", "DUCKDB", "FILE_STORAGE"],
            default=["POSTGRESQL", "SQLITE", "DUCKDB"],
            help="Filter by asset types",
        )
        filters["asset_types"] = asset_types

        # Environment filter
        environments = st.multiselect(
            "Environments",
            options=["DEVELOPMENT", "TESTING", "STAGING", "PRODUCTION"],
            default=["PRODUCTION", "STAGING"],
            help="Filter by deployment environments",
        )
        filters["environments"] = environments

        # Risk threshold
        risk_threshold = st.slider(
            "Risk Threshold", min_value=1.0, max_value=25.0, value=15.0, step=0.5, help="Minimum risk score to display"
        )
        filters["risk_threshold"] = risk_threshold

        return filters


def display_asset_details(asset: Dict[str, Any]) -> None:
    """Display detailed asset information in an expandable format"""
    # Asset overview
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Basic Information**")
        st.write(f"**Name:** {asset.get('name', 'N/A')}")
        st.write(f"**Type:** {asset.get('asset_type', 'N/A')}")
        st.write(f"**Environment:** {asset.get('environment', 'N/A')}")
        st.write(f"**Classification:** {asset.get('security_classification', 'N/A')}")

    with col2:
        st.markdown("**Risk & Compliance**")
        risk_score = asset.get("risk_score", 0)
        compliance_score = asset.get("compliance_score", 0)
        st.write(f"**Risk Score:** {risk_score}/25")
        st.write(f"**Risk Level:** {_get_risk_level(risk_score)}")
        st.write(f"**Compliance:** {compliance_score:.1f}%")
        st.write(f"**Criticality:** {asset.get('criticality_level', 'N/A')}")

    with col3:
        st.markdown("**Operational Status**")
        st.write(f"**Owner:** {asset.get('owner_team', 'Unassigned')}")
        st.write(f"**Contact:** {asset.get('technical_contact', 'None')}")
        st.write(f"**Monitoring:** {asset.get('monitoring_status', 'Unknown')}")
        st.write(f"**Last Updated:** {asset.get('last_updated', 'Unknown')}")

    # Risk trend chart (if data is available)
    if asset.get("risk_history"):
        st.markdown("**Risk Trend Analysis**")
        risk_history_df = pd.DataFrame(asset["risk_history"])

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=risk_history_df["date"],
                y=risk_history_df["risk_score"],
                mode="lines+markers",
                name="Risk Score",
                line=dict(color="red", width=2),
            )
        )

        fig.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="High Risk Threshold")

        fig.update_layout(
            title="Risk Score Trend (Last 90 Days)", xaxis_title="Date", yaxis_title="Risk Score", height=300
        )

        st.plotly_chart(fig, use_container_width=True)

    # Asset relationships (if available)
    if asset.get("relationships"):
        st.markdown("**Asset Relationships**")
        relationships_df = pd.DataFrame(asset["relationships"])
        st.dataframe(relationships_df, use_container_width=True, hide_index=True)


def display_executive_summary(summary_data: Dict[str, Any]) -> None:
    """Display executive summary metrics"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Assets", value=summary_data.get("total_assets", 0), help="Total number of assets in inventory"
        )

    with col2:
        security_score = summary_data.get("security_posture_score", 0)
        st.metric(
            label="Security Posture",
            value=f"{security_score:.1f}",
            delta=f"{security_score - 75:.1f} vs baseline",
            help="Overall security posture score",
        )

    with col3:
        compliance_pct = summary_data.get("compliance_percentage", 0)
        st.metric(
            label="Compliance",
            value=f"{compliance_pct:.1f}%",
            delta=f"{compliance_pct - 80:.1f}% vs target",
            help="Overall compliance percentage",
        )

    with col4:
        critical_findings = summary_data.get("critical_findings", 0)
        st.metric(
            label="Critical Findings",
            value=critical_findings,
            delta=-1 if critical_findings > 0 else 0,
            delta_color="inverse",
            help="Number of critical security findings",
        )


def display_recommendations(recommendations: List[Dict[str, Any]]) -> None:
    """Display actionable recommendations"""
    if not recommendations:
        st.info("No recommendations available at this time.")
        return

    for i, rec in enumerate(recommendations, 1):
        priority = rec.get("priority", "MEDIUM")
        title = rec.get("title", "Recommendation")
        impact = rec.get("impact", "Unknown impact")
        effort = rec.get("effort", "Unknown effort")

        # Color code by priority
        if priority == "HIGH":
            st.error(f"**{i}. {title}**")
        elif priority == "MEDIUM":
            st.warning(f"**{i}. {title}**")
        else:
            st.info(f"**{i}. {title}**")

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Impact:** {impact}")
        with col2:
            st.write(f"**Effort:** {effort}")

        st.write("---")


def display_risk_predictions(predictions: List[Dict[str, Any]]) -> None:
    """Display risk prediction component"""
    if not predictions:
        st.info("No risk predictions available.")
        return

    st.subheader("🔮 Risk Predictions (30-Day Forecast)")

    for pred in predictions[:5]:  # Show top 5 predictions
        asset_name = pred.get("asset_name", "Unknown Asset")
        current_risk = pred.get("current_risk", 0)
        predicted_risk = pred.get("predicted_risk", 0)
        confidence = pred.get("confidence", 0)

        delta = predicted_risk - current_risk

        col1, col2 = st.columns([3, 1])

        with col1:
            st.metric(
                label=asset_name,
                value=f"{predicted_risk:.1f}",
                delta=f"{delta:+.1f}",
                help=f"Confidence: {confidence:.1%}",
            )

        with col2:
            # Confidence indicator
            if confidence > 0.8:
                st.success("High Confidence")
            elif confidence > 0.6:
                st.warning("Medium Confidence")
            else:
                st.error("Low Confidence")


def display_system_health(health_data: Dict[str, Any]) -> None:
    """Display system health monitoring component"""
    st.subheader("🔧 System Health")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        api_time = health_data.get("api_response_time", 0)
        st.metric(
            label="API Response Time",
            value=f"{api_time}ms",
            delta=f"{api_time - 100:+d}ms vs target",
            delta_color="inverse",
            help="Average API response time",
        )

    with col2:
        db_conn = health_data.get("database_connections", 0)
        st.metric(label="DB Connections", value=db_conn, help="Active database connections")

    with col3:
        error_rate = health_data.get("error_rate", 0)
        st.metric(
            label="Error Rate",
            value=f"{error_rate:.2%}",
            delta=f"{error_rate - 0.01:+.2%} vs target",
            delta_color="inverse",
            help="System error rate",
        )

    with col4:
        uptime = health_data.get("uptime_percentage", 0)
        st.metric(
            label="Uptime", value=f"{uptime:.2f}%", delta=f"{uptime - 99:.2f}% vs SLA", help="System uptime percentage"
        )


def display_alerts(alerts: List[Dict[str, Any]]) -> None:
    """Display system alerts component"""
    if not alerts:
        st.success("No active alerts")
        return

    st.subheader("🚨 Active Alerts")

    # Group alerts by severity
    critical_alerts = [a for a in alerts if a.get("severity") == "CRITICAL"]
    high_alerts = [a for a in alerts if a.get("severity") == "HIGH"]
    medium_alerts = [a for a in alerts if a.get("severity") == "MEDIUM"]

    # Display critical alerts first
    if critical_alerts:
        st.error(f"**{len(critical_alerts)} Critical Alert(s)**")
        for alert in critical_alerts[:3]:  # Show first 3
            st.write(f"🔴 {alert.get('message', 'Alert message')}")

    if high_alerts:
        st.warning(f"**{len(high_alerts)} High Priority Alert(s)**")
        for alert in high_alerts[:3]:  # Show first 3
            st.write(f"🟠 {alert.get('message', 'Alert message')}")

    if medium_alerts:
        st.info(f"**{len(medium_alerts)} Medium Priority Alert(s)**")
        for alert in medium_alerts[:2]:  # Show first 2
            st.write(f"🟡 {alert.get('message', 'Alert message')}")

    # Show all alerts in a table
    if len(alerts) > 5:
        with st.expander("View All Alerts"):
            alerts_df = pd.DataFrame(alerts)
            st.dataframe(alerts_df, use_container_width=True, hide_index=True)


def create_metric_card(
    title: str, value: Union[str, int, float], delta: Optional[str] = None, help_text: Optional[str] = None
) -> None:
    """Create a custom metric card component"""
    with st.container():
        st.markdown(f"**{title}**")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown(f"### {value}")

        if delta:
            with col2:
                if delta.startswith("+"):
                    st.success(delta)
                elif delta.startswith("-"):
                    st.error(delta)
                else:
                    st.info(delta)

        if help_text:
            st.caption(help_text)


def create_status_indicator(status: str, label: str = "Status") -> None:
    """Create a status indicator component"""
    status_colors = {
        "HEALTHY": "🟢",
        "WARNING": "🟡",
        "ERROR": "🔴",
        "UNKNOWN": "⚪",
        "ACTIVE": "🟢",
        "INACTIVE": "🔴",
        "PENDING": "🟡",
    }

    indicator = status_colors.get(status.upper(), "⚪")
    st.write(f"{indicator} **{label}:** {status}")


def display_compliance_framework_status(frameworks: Dict[str, Any]) -> None:
    """Display compliance framework status"""
    st.subheader("📋 Compliance Framework Status")

    for framework, data in frameworks.items():
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.write(f"**{framework}**")

        with col2:
            score = data.get("score", 0)
            if score >= 90:
                st.success(f"{score:.1f}%")
            elif score >= 80:
                st.warning(f"{score:.1f}%")
            else:
                st.error(f"{score:.1f}%")

        with col3:
            compliant = data.get("compliant", False)
            if compliant:
                st.success("✅ Compliant")
            else:
                gaps = data.get("gaps", 0)
                st.error(f"❌ {gaps} gaps")


def create_real_time_status_bar() -> None:
    """Create a real-time status bar component"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.write("🔄 **Status:** Live")

    with col2:
        st.write(f"⏰ **Updated:** {datetime.now().strftime('%H:%M:%S')}")

    with col3:
        st.write("📡 **Connection:** Healthy")

    with col4:
        if st.button("🔄 Refresh Now"):
            st.rerun()


class AssetDetailModal:
    """Asset detail modal component"""

    def __init__(self, asset_data: Dict[str, Any]) -> None:
        """Initialize asset detail modal with asset data."""
        self.asset_data = asset_data

    def render(self) -> None:
        """Render the asset detail modal"""
        with st.expander(f"Asset Details: {self.asset_data.get('name', 'Unknown')}", expanded=True):
            display_asset_details(self.asset_data)


def _get_risk_level(risk_score: float) -> str:
    """Convert risk score to risk level"""
    if risk_score >= 20:
        return "CRITICAL"
    elif risk_score >= 15:
        return "VERY_HIGH"
    elif risk_score >= 10:
        return "HIGH"
    elif risk_score >= 5:
        return "MEDIUM"
    else:
        return "LOW"


def create_dashboard_header(title: str, subtitle: str = "", last_updated: Optional[datetime] = None) -> None:
    """Create a standardized dashboard header"""
    col1, col2 = st.columns([3, 1])

    with col1:
        st.title(title)
        if subtitle:
            st.markdown(subtitle)

    with col2:
        if last_updated:
            st.info(f"Last updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            st.info(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def create_kpi_row(kpis: List[Dict[str, Any]]) -> None:
    """Create a row of KPI metrics"""
    if not kpis:
        return

    cols = st.columns(len(kpis))

    for i, kpi in enumerate(kpis):
        with cols[i]:
            st.metric(
                label=kpi.get("label", "KPI"),
                value=kpi.get("value", "N/A"),
                delta=kpi.get("delta"),
                help=kpi.get("help"),
            )
