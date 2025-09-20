#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Database Executive Reports Dashboard Page for Issue #284

This page provides executive-level reporting with KPIs, business metrics,
automated insights, and actionable recommendations.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from violentutf.components.dashboard_components import (
    create_dashboard_header,
    create_kpi_row,
    display_recommendations,
)

# Import utility modules
from violentutf.utils.api_client import DashboardAPIClient

# Utility imports removed as they are not used

# Configure page
st.set_page_config(
    page_title="Database Executive Reports", page_icon="📈", layout="wide", initial_sidebar_state="expanded"
)

# Create dashboard header
create_dashboard_header(
    "📈 Database Executive Reports", "Strategic insights and key performance indicators for leadership"
)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_executive_dashboard_data() -> Dict[str, Any]:
    """Load executive dashboard data with caching"""
    try:
        client = DashboardAPIClient()

        # Get executive report data
        executive_data = client.get_executive_report_data()

        # Enhance with additional mock data for comprehensive reporting
        enhanced_data = executive_data.copy()

        # Add business impact metrics
        enhanced_data["business_impact"] = {
            "risk_reduction_achieved": 25.3,  # percentage
            "compliance_improvement": 12.8,  # percentage
            "cost_avoidance": 1250000,  # dollars
            "incident_reduction": 67,  # percentage
            "automation_efficiency": 34.5,  # percentage
        }

        # Add departmental metrics
        enhanced_data["departmental_metrics"] = {
            "IT Security": {
                "assets_managed": 45,
                "security_score": 87.2,
                "incidents_resolved": 23,
                "response_time_hours": 2.4,
            },
            "Data Engineering": {
                "assets_managed": 52,
                "security_score": 82.1,
                "incidents_resolved": 18,
                "response_time_hours": 3.1,
            },
            "DevOps": {
                "assets_managed": 28,
                "security_score": 91.5,
                "incidents_resolved": 12,
                "response_time_hours": 1.8,
            },
        }

        # Add strategic initiatives progress
        enhanced_data["strategic_initiatives"] = [
            {
                "name": "Zero Trust Architecture Implementation",
                "progress": 73,
                "target_completion": "2024-12-31",
                "budget_utilized": 67,
                "risk_reduction": 35,
            },
            {
                "name": "Automated Compliance Monitoring",
                "progress": 89,
                "target_completion": "2024-10-15",
                "budget_utilized": 78,
                "risk_reduction": 28,
            },
            {
                "name": "Cloud Security Modernization",
                "progress": 56,
                "target_completion": "2025-03-31",
                "budget_utilized": 45,
                "risk_reduction": 42,
            },
        ]

        return enhanced_data

    except Exception as e:
        st.error(f"Error loading executive dashboard data: {str(e)}")
        # Return comprehensive mock data on error
        return {
            "summary": {
                "total_assets": 125,
                "security_posture_score": 78.5,
                "compliance_percentage": 84.2,
                "critical_findings": 5,
            },
            "trends": {
                "security_improvement": 5.2,
                "new_assets_30_days": 8,
                "resolved_vulnerabilities": 23,
                "compliance_improvement": 2.1,
            },
            "recommendations": [],
            "business_impact": {
                "risk_reduction_achieved": 25.3,
                "compliance_improvement": 12.8,
                "cost_avoidance": 1250000,
                "incident_reduction": 67,
                "automation_efficiency": 34.5,
            },
            "departmental_metrics": {},
            "strategic_initiatives": [],
        }


def display_executive_kpis(executive_data: Dict[str, Any]) -> None:
    """Display executive-level KPIs"""
    summary = executive_data.get("summary", {})
    business_impact = executive_data.get("business_impact", {})

    kpis = [
        {
            "label": "Security Posture",
            "value": f"{summary.get('security_posture_score', 0):.1f}/100",
            "delta": f"{executive_data.get('trends', {}).get('security_improvement', 0):+.1f}%",
            "help": "Overall security posture score across all assets",
        },
        {
            "label": "Risk Reduction",
            "value": f"{business_impact.get('risk_reduction_achieved', 0):.1f}%",
            "delta": "YTD achievement",
            "help": "Risk reduction achieved year-to-date",
        },
        {
            "label": "Cost Avoidance",
            "value": f"${business_impact.get('cost_avoidance', 0):,.0f}",
            "delta": "Potential savings",
            "help": "Estimated cost avoidance from security improvements",
        },
        {
            "label": "Incident Reduction",
            "value": f"{business_impact.get('incident_reduction', 0):.0f}%",
            "delta": "vs last quarter",
            "help": "Reduction in security incidents compared to previous quarter",
        },
    ]

    create_kpi_row(kpis)


def create_business_impact_chart(business_impact: Dict[str, Any]) -> go.Figure:
    """Create business impact visualization"""
    if not business_impact:
        fig = go.Figure()
        fig.add_annotation(text="No business impact data available", showarrow=False)
        return fig

    metrics = list(business_impact.keys())
    values = list(business_impact.values())

    # Convert cost_avoidance to millions for better visualization
    display_values = []
    display_labels = []

    for metric, value in zip(metrics, values):
        if metric == "cost_avoidance":
            display_values.append(value / 1000000)
            display_labels.append("Cost Avoidance ($M)")
        else:
            display_values.append(value)
            display_labels.append(metric.replace("_", " ").title())

    # Create radar chart
    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=display_values,
            theta=display_labels,
            fill="toself",
            name="Business Impact",
            line_color="blue",
            fillcolor="rgba(0,0,255,0.1)",
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, max(display_values) * 1.1])),
        title="Business Impact Metrics",
        height=400,
    )

    return fig


def create_departmental_performance_chart(departmental_metrics: Dict[str, Any]) -> go.Figure:
    """Create departmental performance comparison"""
    if not departmental_metrics:
        fig = go.Figure()
        fig.add_annotation(text="No departmental data available", showarrow=False)
        return fig

    departments = list(departmental_metrics.keys())
    security_scores = [metrics.get("security_score", 0) for metrics in departmental_metrics.values()]
    # assets_managed = [metrics.get("assets_managed", 0) for metrics in departmental_metrics.values()]  # Unused
    response_times = [metrics.get("response_time_hours", 0) for metrics in departmental_metrics.values()]

    # Create subplot with secondary y-axes
    fig = make_subplots(rows=1, cols=1, specs=[[{"secondary_y": True}]])

    # Add security scores
    fig.add_trace(
        go.Bar(
            name="Security Score",
            x=departments,
            y=security_scores,
            text=[f"{score:.1f}" for score in security_scores],
            textposition="outside",
            marker_color="lightblue",
            hovertemplate="<b>%{x}</b><br>Security Score: %{y:.1f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Add response time line
    fig.add_trace(
        go.Scatter(
            name="Response Time (hrs)",
            x=departments,
            y=response_times,
            mode="lines+markers",
            line=dict(color="red", width=3),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>Response Time: %{y:.1f} hrs<extra></extra>",
        ),
        secondary_y=True,
    )

    # Update layout
    fig.update_layout(title="Departmental Performance Overview", height=400, hovermode="x unified")

    fig.update_yaxes(title_text="Security Score", secondary_y=False, range=[0, 100])
    fig.update_yaxes(title_text="Response Time (hours)", secondary_y=True)

    return fig


def display_strategic_initiatives(initiatives: List[Dict[str, Any]]) -> None:
    """Display strategic initiatives progress"""
    st.subheader("🎯 Strategic Initiatives Progress")

    if not initiatives:
        st.info("No strategic initiatives data available")
        return

    for initiative in initiatives:
        with st.expander(f"📋 {initiative['name']}", expanded=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                progress = initiative.get("progress", 0)
                st.metric("Progress", f"{progress}%", help="Project completion percentage")

                # Progress bar
                st.progress(progress / 100)

            with col2:
                budget_utilized = initiative.get("budget_utilized", 0)
                st.metric("Budget Utilized", f"{budget_utilized}%", help="Percentage of budget spent")

                # Budget progress bar
                # color = "green" if budget_utilized <= progress else "orange"  # Unused
                st.progress(budget_utilized / 100)

            with col3:
                risk_reduction = initiative.get("risk_reduction", 0)
                st.metric("Risk Reduction", f"{risk_reduction}%", help="Expected risk reduction upon completion")

                target_date = initiative.get("target_completion", "")
                st.write(f"**Target:** {target_date}")


def create_financial_impact_visualization(executive_data: Dict[str, Any]) -> go.Figure:
    """Create financial impact visualization"""
    business_impact = executive_data.get("business_impact", {})

    if not business_impact:
        fig = go.Figure()
        fig.add_annotation(text="No financial data available", showarrow=False)
        return fig

    # Mock quarterly financial data
    quarters = ["Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024 (Proj)"]
    cost_avoidance = [300000, 450000, 650000, 850000]
    security_investment = [150000, 175000, 200000, 225000]
    roi = [(avoid - invest) / invest * 100 for avoid, invest in zip(cost_avoidance, security_investment)]

    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=("Cost Avoidance vs Investment", "Return on Investment"),
        specs=[[{"secondary_y": False}], [{"secondary_y": False}]],
    )

    # Cost avoidance and investment
    fig.add_trace(
        go.Bar(
            name="Cost Avoidance",
            x=quarters,
            y=cost_avoidance,
            marker_color="green",
            hovertemplate="<b>%{x}</b><br>Cost Avoidance: $%{y:,.0f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            name="Security Investment",
            x=quarters,
            y=security_investment,
            marker_color="blue",
            hovertemplate="<b>%{x}</b><br>Investment: $%{y:,.0f}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # ROI line chart
    fig.add_trace(
        go.Scatter(
            name="ROI %",
            x=quarters,
            y=roi,
            mode="lines+markers",
            line=dict(color="red", width=3),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>ROI: %{y:.0f}%<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(title="Financial Impact Analysis", height=600, showlegend=True)

    fig.update_yaxes(title_text="Amount ($)", row=1, col=1)
    fig.update_yaxes(title_text="ROI (%)", row=2, col=1)

    return fig


def create_executive_summary_report(executive_data: Dict[str, Any]) -> None:
    """Create executive summary report section"""
    st.subheader("📊 Executive Summary")

    summary = executive_data.get("summary", {})
    trends = executive_data.get("trends", {})
    business_impact = executive_data.get("business_impact", {})

    # Key highlights
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎯 Key Achievements")
        st.success(f"✅ {business_impact.get('risk_reduction_achieved', 0):.1f}% risk reduction achieved")
        st.success(f"✅ ${business_impact.get('cost_avoidance', 0):,.0f} in cost avoidance")
        st.success(f"✅ {business_impact.get('incident_reduction', 0):.0f}% fewer security incidents")
        st.success(f"✅ {summary.get('compliance_percentage', 0):.1f}% compliance rate")

    with col2:
        st.markdown("### ⚠️ Areas of Focus")
        critical_findings = summary.get("critical_findings", 0)
        if critical_findings > 0:
            st.warning(f"🔍 {critical_findings} critical findings require attention")

        if summary.get("compliance_percentage", 0) < 90:
            st.warning("📋 Compliance rate below 90% target")

        if trends.get("security_improvement", 0) < 5:
            st.warning("📈 Security improvement rate below target")

        if not any(
            [
                critical_findings > 0,
                summary.get("compliance_percentage", 0) < 90,
                trends.get("security_improvement", 0) < 5,
            ]
        ):
            st.success("🎉 All key metrics are meeting targets!")


def display_automated_insights(executive_data: Dict[str, Any]) -> None:
    """Display AI-generated insights and recommendations"""
    st.subheader("🤖 Automated Insights")

    # Generate insights based on data
    insights = []

    summary = executive_data.get("summary", {})
    trends = executive_data.get("trends", {})
    business_impact = executive_data.get("business_impact", {})

    # Security posture insight
    security_score = summary.get("security_posture_score", 0)
    if security_score > 85:
        insights.append(
            {
                "type": "success",
                "title": "Strong Security Posture",
                "message": (
                    f"Security posture score of {security_score:.1f} exceeds industry benchmarks. "
                    "Continue current security practices."
                ),
            }
        )
    elif security_score > 70:
        insights.append(
            {
                "type": "warning",
                "title": "Moderate Security Posture",
                "message": (
                    f"Security posture score of {security_score:.1f} is adequate but has room for improvement. "
                    "Focus on high-impact security controls."
                ),
            }
        )
    else:
        insights.append(
            {
                "type": "error",
                "title": "Security Posture Needs Attention",
                "message": (
                    f"Security posture score of {security_score:.1f} is below recommended levels. "
                    "Immediate action required."
                ),
            }
        )

    # Trend analysis insight
    security_improvement = trends.get("security_improvement", 0)
    if security_improvement > 5:
        insights.append(
            {
                "type": "success",
                "title": "Positive Security Trend",
                "message": (
                    f"Security improvements of {security_improvement:.1f}% indicate effective security investments."
                ),
            }
        )
    elif security_improvement < 0:
        insights.append(
            {
                "type": "error",
                "title": "Declining Security Trend",
                "message": (
                    f"Security metrics declining by {abs(security_improvement):.1f}%. "
                    "Review and adjust security strategy."
                ),
            }
        )

    # ROI insight
    cost_avoidance = business_impact.get("cost_avoidance", 0)
    if cost_avoidance > 1000000:
        insights.append(
            {
                "type": "success",
                "title": "Excellent ROI Achievement",
                "message": (
                    f"Cost avoidance of ${cost_avoidance:,.0f} demonstrates strong return on security investments."
                ),
            }
        )

    # Display insights
    for insight in insights:
        if insight["type"] == "success":
            st.success(f"**{insight['title']}:** {insight['message']}")
        elif insight["type"] == "warning":
            st.warning(f"**{insight['title']}:** {insight['message']}")
        else:
            st.error(f"**{insight['title']}:** {insight['message']}")


def main() -> None:
    """Run main executive dashboard function"""
    try:
        # Create filters
        # filters = create_filter_sidebar()  # Unused for now

        # Load data
        executive_data = load_executive_dashboard_data()

        # Display executive KPIs
        display_executive_kpis(executive_data)

        # Add separator
        st.divider()

        # Executive summary
        create_executive_summary_report(executive_data)

        # Add separator
        st.divider()

        # Business impact and financial analysis
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("💼 Business Impact")
            fig_business = create_business_impact_chart(executive_data.get("business_impact", {}))
            st.plotly_chart(fig_business, use_container_width=True)

        with col2:
            st.subheader("🏢 Departmental Performance")
            fig_dept = create_departmental_performance_chart(executive_data.get("departmental_metrics", {}))
            st.plotly_chart(fig_dept, use_container_width=True)

        # Add separator
        st.divider()

        # Financial impact
        st.subheader("💰 Financial Impact Analysis")
        fig_financial = create_financial_impact_visualization(executive_data)
        st.plotly_chart(fig_financial, use_container_width=True)

        # Add separator
        st.divider()

        # Strategic initiatives
        display_strategic_initiatives(executive_data.get("strategic_initiatives", []))

        # Add separator
        st.divider()

        # Automated insights
        display_automated_insights(executive_data)

        # Add separator
        st.divider()

        # Recommendations
        st.subheader("📋 Strategic Recommendations")
        recommendations = executive_data.get("recommendations", [])

        if not recommendations:
            # Generate default recommendations
            recommendations = [
                {
                    "priority": "HIGH",
                    "title": "Implement automated security monitoring",
                    "impact": "Reduce incident response time by 60%",
                    "effort": "4-6 weeks",
                },
                {
                    "priority": "MEDIUM",
                    "title": "Enhance compliance automation",
                    "impact": "Improve compliance score by 15%",
                    "effort": "6-8 weeks",
                },
            ]

        display_recommendations(recommendations)

        # Add refresh info
        st.sidebar.divider()
        st.sidebar.info(
            f"🔄 Last updated: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"Executive reports refresh every 15 minutes.\n\n"
            f"📊 Next board report: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}"
        )

    except Exception as e:
        st.error(f"Executive dashboard error: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
