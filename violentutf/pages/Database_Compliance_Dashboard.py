#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Database Compliance Dashboard Page for Issue #284

This page provides comprehensive compliance monitoring with framework tracking,
gap analysis, and remediation guidance.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from violentutf.components.dashboard_components import (
    create_dashboard_header,
    create_kpi_row,
    display_compliance_framework_status,
)

# Import utility modules
from violentutf.utils.api_client import DashboardAPIClient

# Utility imports removed as they are not used

# Configure page
st.set_page_config(
    page_title="Database Compliance Dashboard", page_icon="📋", layout="wide", initial_sidebar_state="expanded"
)

# Create dashboard header
create_dashboard_header("📋 Database Compliance Dashboard", "Regulatory framework compliance tracking and gap analysis")


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_compliance_dashboard_data() -> Dict[str, Any]:
    """Load compliance dashboard data with caching"""
    try:
        client = DashboardAPIClient()
        # compliance_api = ComplianceMonitoringAPI()  # Unused for now

        # Get compliance summary
        compliance_summary = client.get_compliance_summary()

        # Mock compliance data
        compliance_data = [
            {
                "asset_id": f"asset-{i}",
                "asset_name": f"database-{i}",
                "framework": ["SOC2", "GDPR", "NIST"][i % 3],
                "overall_score": 75 + (i % 25),
                "compliant": (75 + (i % 25)) >= 80,
                "gaps": (
                    [
                        {
                            "control_id": f"CC{i % 9 + 1}.{i % 3 + 1}",
                            "description": f"Control requirement {i}",
                            "severity": ["LOW", "MEDIUM", "HIGH"][i % 3],
                            "status": "NON_COMPLIANT" if i % 3 == 0 else "PARTIAL_COMPLIANCE",
                        }
                    ]
                    if (75 + (i % 25)) < 80
                    else []
                ),
                "last_assessment": (datetime.now() - timedelta(days=i % 30)).isoformat(),
            }
            for i in range(1, 21)
        ]

        # Mock gap analysis data
        gap_analysis = {
            "high_priority_gaps": [
                {
                    "asset_id": "asset-1",
                    "framework": "GDPR",
                    "control_id": "Article 32",
                    "description": "Security of processing",
                    "severity": "HIGH",
                    "remediation_steps": [
                        "Implement encryption at rest",
                        "Enable network security controls",
                        "Conduct security assessments",
                    ],
                    "estimated_effort": "2-4 weeks",
                }
            ],
            "medium_priority_gaps": [
                {
                    "asset_id": "asset-2",
                    "framework": "SOC2",
                    "control_id": "CC6.1",
                    "description": "Logical access controls",
                    "severity": "MEDIUM",
                    "remediation_steps": ["Implement multi-factor authentication", "Review user access permissions"],
                    "estimated_effort": "1-2 weeks",
                }
            ],
        }

        return {"summary": compliance_summary, "compliance_data": compliance_data, "gap_analysis": gap_analysis}

    except Exception as e:
        st.error(f"Error loading compliance dashboard data: {str(e)}")
        # Return mock data on error
        return {
            "summary": {
                "overall_compliance_score": 82.3,
                "frameworks": {
                    "SOC2": {"score": 85.5, "compliant": True, "gaps": 2},
                    "GDPR": {"score": 78.1, "compliant": False, "gaps": 5},
                    "NIST": {"score": 83.7, "compliant": True, "gaps": 1},
                },
                "high_priority_gaps": 3,
                "total_assets_assessed": 15,
            },
            "compliance_data": [],
            "gap_analysis": {"high_priority_gaps": [], "medium_priority_gaps": []},
        }


def display_compliance_kpis(summary: Dict[str, Any]) -> None:
    """Display key compliance performance indicators"""
    kpis: List[Dict[str, Any]] = [
        {
            "label": "Overall Compliance",
            "value": f"{summary.get('overall_compliance_score', 0):.1f}%",
            "delta": f"{summary.get('compliance_trend', 0):+.1f}%",
            "help": "Average compliance score across all frameworks",
        },
        {
            "label": "Compliant Frameworks",
            "value": f"{len([f for f in summary.get('frameworks', {}).values() if f.get('compliant', False)])}/3",
            "delta": None,
            "help": "Number of frameworks meeting compliance thresholds",
        },
        {
            "label": "High Priority Gaps",
            "value": summary.get("high_priority_gaps", 0),
            "delta": f"{summary.get('gap_trend', 0):+d}",
            "help": "Number of high-priority compliance gaps",
        },
        {
            "label": "Assets Assessed",
            "value": summary.get("total_assets_assessed", 0),
            "delta": f"{summary.get('assessment_growth', 0):+d}",
            "help": "Total number of assets with compliance assessments",
        },
    ]

    create_kpi_row(kpis)


def create_framework_comparison_chart(frameworks: Dict[str, Any]) -> go.Figure:
    """Create framework comparison chart"""
    if not frameworks:
        fig = go.Figure()
        fig.add_annotation(text="No framework data available", showarrow=False)
        return fig

    framework_names = list(frameworks.keys())
    scores = [frameworks[fw].get("score", 0) for fw in framework_names]
    gaps = [frameworks[fw].get("gaps", 0) for fw in framework_names]

    fig = go.Figure()

    # Add compliance scores
    fig.add_trace(
        go.Bar(
            name="Compliance Score",
            x=framework_names,
            y=scores,
            text=[f"{score:.1f}%" for score in scores],
            textposition="outside",
            marker_color=["green" if score >= 80 else "orange" if score >= 70 else "red" for score in scores],
            hovertemplate="<b>%{x}</b><br>Score: %{y:.1f}%<extra></extra>",
        )
    )

    # Add gaps on secondary y-axis
    fig.add_trace(
        go.Scatter(
            name="Compliance Gaps",
            x=framework_names,
            y=gaps,
            mode="markers+text",
            text=[f"{gap} gaps" for gap in gaps],
            textposition="top center",
            marker=dict(size=15, color="red", symbol="diamond"),
            yaxis="y2",
            hovertemplate="<b>%{x}</b><br>Gaps: %{y}<extra></extra>",
        )
    )

    # Update layout
    fig.update_layout(
        title="Compliance Framework Comparison",
        xaxis_title="Framework",
        yaxis=dict(title="Compliance Score (%)", range=[0, 100]),
        yaxis2=dict(title="Number of Gaps", overlaying="y", side="right"),
        height=400,
        hovermode="x unified",
    )

    # Add compliance threshold line
    fig.add_hline(y=80, line_dash="dash", line_color="orange", annotation_text="Target Threshold (80%)")

    return fig


def display_compliance_gaps_analysis(gap_analysis: Dict[str, Any]) -> None:
    """Display compliance gaps analysis"""
    st.subheader("🔍 Compliance Gaps Analysis")

    # High priority gaps
    high_priority_gaps = gap_analysis.get("high_priority_gaps", [])
    if high_priority_gaps:
        st.error(f"**{len(high_priority_gaps)} High Priority Gap(s)**")

        for gap in high_priority_gaps:
            with st.expander(f"🔴 {gap['framework']} - {gap['control_id']}: {gap['description']}", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Asset:** {gap['asset_id']}")
                    st.write(f"**Framework:** {gap['framework']}")
                    st.write(f"**Severity:** {gap['severity']}")
                    st.write(f"**Estimated Effort:** {gap['estimated_effort']}")

                with col2:
                    st.write("**Remediation Steps:**")
                    for i, step in enumerate(gap["remediation_steps"], 1):
                        st.write(f"{i}. {step}")

    # Medium priority gaps
    medium_priority_gaps = gap_analysis.get("medium_priority_gaps", [])
    if medium_priority_gaps:
        st.warning(f"**{len(medium_priority_gaps)} Medium Priority Gap(s)**")

        for gap in medium_priority_gaps:
            with st.expander(f"🟡 {gap['framework']} - {gap['control_id']}: {gap['description']}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Asset:** {gap['asset_id']}")
                    st.write(f"**Framework:** {gap['framework']}")
                    st.write(f"**Severity:** {gap['severity']}")
                    st.write(f"**Estimated Effort:** {gap['estimated_effort']}")

                with col2:
                    st.write("**Remediation Steps:**")
                    for i, step in enumerate(gap["remediation_steps"], 1):
                        st.write(f"{i}. {step}")

    if not high_priority_gaps and not medium_priority_gaps:
        st.success("✅ No critical compliance gaps identified!")


def create_compliance_trend_visualization(compliance_data: List[Dict[str, Any]]) -> go.Figure:
    """Create compliance trend visualization"""
    if not compliance_data:
        fig = go.Figure()
        fig.add_annotation(text="No compliance trend data available", showarrow=False)
        return fig

    # Mock historical trend data
    dates = []
    soc2_scores = []
    gdpr_scores = []
    nist_scores = []

    for i in range(30):
        date = datetime.now() - timedelta(days=29 - i)
        dates.append(date)

        # Mock trending scores with some variation
        soc2_scores.append(80 + 5 * np.sin(i * 0.2) + np.random.normal(0, 2))
        gdpr_scores.append(75 + 3 * np.sin(i * 0.15) + np.random.normal(0, 1.5))
        nist_scores.append(82 + 4 * np.sin(i * 0.25) + np.random.normal(0, 1))

    fig = go.Figure()

    # Add trend lines for each framework
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=soc2_scores,
            mode="lines+markers",
            name="SOC2",
            line=dict(color="blue", width=2),
            hovertemplate="<b>SOC2</b><br>Date: %{x}<br>Score: %{y:.1f}%<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=gdpr_scores,
            mode="lines+markers",
            name="GDPR",
            line=dict(color="green", width=2),
            hovertemplate="<b>GDPR</b><br>Date: %{x}<br>Score: %{y:.1f}%<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=nist_scores,
            mode="lines+markers",
            name="NIST",
            line=dict(color="orange", width=2),
            hovertemplate="<b>NIST</b><br>Date: %{x}<br>Score: %{y:.1f}%<extra></extra>",
        )
    )

    # Add compliance threshold
    fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Compliance Threshold (80%)")

    fig.update_layout(
        title="Compliance Score Trends (Last 30 Days)",
        xaxis_title="Date",
        yaxis_title="Compliance Score (%)",
        yaxis=dict(range=[60, 100]),
        height=400,
        hovermode="x unified",
    )

    return fig


def display_compliance_assets_table(compliance_data: List[Dict[str, Any]]) -> None:
    """Display compliance status for all assets"""
    st.subheader("📊 Asset Compliance Status")

    if not compliance_data:
        st.warning("No compliance data available")
        return

    # Create DataFrame
    df_compliance = pd.DataFrame(compliance_data)

    # Add compliance status text
    df_compliance["compliance_status"] = df_compliance["compliant"].apply(
        lambda x: "✅ Compliant" if x else "❌ Non-Compliant"
    )

    # Add gap count
    df_compliance["gap_count"] = df_compliance["gaps"].apply(len)

    # Filter controls
    col1, col2 = st.columns(2)

    with col1:
        selected_framework = st.selectbox(
            "Filter by Framework", options=["All"] + list(df_compliance["framework"].unique()), index=0
        )

    with col2:
        compliance_filter = st.selectbox("Compliance Status", options=["All", "Compliant", "Non-Compliant"], index=0)

    # Apply filters
    filtered_df = df_compliance.copy()

    if selected_framework != "All":
        filtered_df = filtered_df[filtered_df["framework"] == selected_framework]

    if compliance_filter == "Compliant":
        filtered_df = filtered_df[filtered_df["compliant"] is True]
    elif compliance_filter == "Non-Compliant":
        filtered_df = filtered_df[filtered_df["compliant"] is False]

    # Display table
    display_columns = ["asset_name", "framework", "overall_score", "compliance_status", "gap_count", "last_assessment"]

    st.dataframe(
        filtered_df[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "overall_score": st.column_config.ProgressColumn(
                "Compliance Score", min_value=0, max_value=100, format="%.1f%%"
            ),
            "gap_count": st.column_config.NumberColumn("Gaps", help="Number of compliance gaps"),
            "last_assessment": st.column_config.DatetimeColumn("Last Assessment", format="YYYY-MM-DD"),
        },
    )

    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        compliant_count = len(filtered_df[filtered_df["compliant"] is True])
        st.metric("Compliant Assets", compliant_count)

    with col2:
        avg_score = filtered_df["overall_score"].mean()
        st.metric("Average Score", f"{avg_score:.1f}%")

    with col3:
        total_gaps = filtered_df["gap_count"].sum()
        st.metric("Total Gaps", total_gaps)

    with col4:
        frameworks_count = filtered_df["framework"].nunique()
        st.metric("Frameworks", frameworks_count)


def main() -> None:
    """Run main compliance dashboard function"""
    try:
        # Create filters
        # filters = create_filter_sidebar()  # Unused for now

        # Load data
        dashboard_data = load_compliance_dashboard_data()
        summary = dashboard_data["summary"]
        compliance_data = dashboard_data["compliance_data"]
        gap_analysis = dashboard_data["gap_analysis"]

        # Display KPIs
        display_compliance_kpis(summary)

        # Add separator
        st.divider()

        # Framework status overview
        st.subheader("🏛️ Compliance Framework Overview")
        display_compliance_framework_status(summary.get("frameworks", {}))

        # Framework comparison chart
        col1, col2 = st.columns(2)

        with col1:
            fig_comparison = create_framework_comparison_chart(summary.get("frameworks", {}))
            st.plotly_chart(fig_comparison, use_container_width=True)

        with col2:
            # Compliance distribution pie chart
            frameworks = summary.get("frameworks", {})
            if frameworks:
                compliant_count = len([f for f in frameworks.values() if f.get("compliant", False)])
                non_compliant_count = len(frameworks) - compliant_count

                fig_pie = px.pie(
                    values=[compliant_count, non_compliant_count],
                    names=["Compliant", "Non-Compliant"],
                    title="Compliance Status Distribution",
                    color_discrete_map={"Compliant": "green", "Non-Compliant": "red"},
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        # Add separator
        st.divider()

        # Compliance trends
        st.subheader("📈 Compliance Trends")
        fig_trends = create_compliance_trend_visualization(compliance_data)
        st.plotly_chart(fig_trends, use_container_width=True)

        # Add separator
        st.divider()

        # Compliance gaps analysis
        display_compliance_gaps_analysis(gap_analysis)

        # Add separator
        st.divider()

        # Asset compliance table
        display_compliance_assets_table(compliance_data)

        # Add refresh info
        st.sidebar.divider()
        st.sidebar.info(
            f"🔄 Last updated: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"Data refreshes every 5 minutes automatically.\n\n"
            f"📊 Compliance assessments run daily at 2 AM UTC"
        )

    except Exception as e:
        st.error(f"Compliance dashboard error: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
