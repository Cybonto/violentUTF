#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Database Risk Dashboard Page for Issue #284

This page provides comprehensive risk assessment visualization with trend analysis,
predictive insights, and risk management capabilities.
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
    create_filter_sidebar,
    create_kpi_row,
    display_risk_predictions,
)

# Import utility modules
from violentutf.utils.api_client import DashboardAPIClient
from violentutf.utils.visualization_utils import (
    create_risk_heatmap,
    create_risk_trend_chart,
)

# Configure page
st.set_page_config(
    page_title="Database Risk Dashboard",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Create dashboard header
create_dashboard_header("⚠️ Database Risk Assessment Dashboard", "Comprehensive risk monitoring and trend analysis")


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_risk_dashboard_data(time_range: str = "Last 30 days") -> Dict[str, Any]:
    """Load risk dashboard data with caching"""
    try:
        client = DashboardAPIClient()
        # risk_api = RiskAssessmentAPI()  # Unused for now

        # Get risk metrics
        risk_metrics = client.get_risk_dashboard_metrics()

        # Mock risk trend data
        days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "Last 6 months": 180, "Last year": 365}
        days = days_map.get(time_range, 30)

        # Generate mock risk trend data
        risk_trend_data = []
        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            risk_trend_data.append(
                {
                    "assessment_date": date.isoformat(),
                    "risk_score": 12.0 + (i % 10) + (i * 0.05),
                    "asset_name": f"asset-{i % 10}",
                    "vulnerability_count": 2 + (i % 5),
                    "risk_level": "HIGH" if (12.0 + i % 10) > 15 else "MEDIUM",
                }
            )

        # Mock high-risk assets
        high_risk_assets = [
            {
                "asset_id": f"asset-{i}",
                "asset_name": f"critical-db-{i}",
                "risk_score": 18.0 + i,
                "risk_level": "HIGH",
                "vulnerability_count": 5 + i,
                "environment": ["PRODUCTION", "STAGING"][i % 2],
                "last_assessment": (datetime.now() - timedelta(days=i)).isoformat(),
            }
            for i in range(1, 6)
        ]

        return {"metrics": risk_metrics, "trend_data": risk_trend_data, "high_risk_assets": high_risk_assets}

    except Exception as e:
        st.error(f"Error loading risk dashboard data: {str(e)}")
        # Return mock data on error
        return {
            "metrics": {
                "average_risk_score": 12.5,
                "risk_distribution": {"LOW": 85, "MEDIUM": 25, "HIGH": 12, "CRITICAL": 3},
                "risk_velocity": 0.05,
                "predicted_30_day_change": 1.2,
                "high_priority_vulnerabilities": 15,
                "assets_requiring_attention": [],
            },
            "trend_data": [],
            "high_risk_assets": [],
        }


def display_risk_kpis(metrics: Dict[str, Any]) -> None:
    """Display key risk performance indicators"""
    kpis = [
        {
            "label": "Average Risk Score",
            "value": f"{metrics.get('average_risk_score', 0):.1f}",
            "delta": f"{metrics.get('risk_trend', 0):+.1f}",
            "help": "Average risk score across all assets (1-25 scale)",
        },
        {
            "label": "Critical Risk Assets",
            "value": metrics.get("risk_distribution", {}).get("CRITICAL", 0),
            "delta": f"{metrics.get('critical_delta', 0):+d}",
            "help": "Assets with critical risk levels (>20)",
        },
        {
            "label": "Risk Velocity",
            "value": f"{metrics.get('risk_velocity', 0):.3f}/day",
            "delta": "Higher is worse" if metrics.get("risk_velocity", 0) > 0 else "Lower is better",
            "help": "Rate of risk score change per day",
        },
        {
            "label": "30-Day Forecast",
            "value": f"{metrics.get('predicted_30_day_change', 0):+.1f}",
            "delta": "Risk score change prediction",
            "help": "Predicted risk score change in next 30 days",
        },
    ]

    create_kpi_row(kpis)


def create_risk_distribution_chart(risk_data: Dict[str, Any]) -> go.Figure:
    """Create risk distribution pie chart"""
    risk_distribution = risk_data.get("risk_distribution", {})

    if not risk_distribution:
        fig = go.Figure()
        fig.add_annotation(text="No risk distribution data available", showarrow=False)
        return fig

    fig = px.pie(
        values=list(risk_distribution.values()),
        names=list(risk_distribution.keys()),
        title="Risk Distribution",
        color=list(risk_distribution.keys()),
        color_discrete_map={
            "LOW": "#28A745",
            "MEDIUM": "#FFC107",
            "HIGH": "#FD7E14",
            "VERY_HIGH": "#DC3545",
            "CRITICAL": "#6F1E51",
        },
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
    )

    fig.update_layout(height=400)

    return fig


def create_risk_factor_breakdown(risk_data: List[Dict[str, Any]]) -> go.Figure:
    """Create risk factor breakdown chart"""
    # Mock risk factors for demonstration
    risk_factors = {
        "Outdated Components": 35,
        "Network Exposure": 28,
        "Insufficient Monitoring": 22,
        "Access Control Issues": 18,
        "Configuration Errors": 15,
        "Missing Patches": 12,
    }

    fig = px.bar(
        x=list(risk_factors.values()),
        y=list(risk_factors.keys()),
        orientation="h",
        title="Risk Factor Contribution",
        color=list(risk_factors.values()),
        color_continuous_scale="Reds",
    )

    fig.update_layout(xaxis_title="Risk Contribution", yaxis_title="Risk Factors", height=400, showlegend=False)

    fig.update_traces(
        texttemplate="%{x}", textposition="outside", hovertemplate="<b>%{y}</b><br>Contribution: %{x}<extra></extra>"
    )

    return fig


def display_high_risk_assets_table(high_risk_assets: List[Dict[str, Any]]) -> None:
    """Display high-risk assets requiring attention"""
    st.subheader("🔥 High-Risk Assets Requiring Attention")

    if not high_risk_assets:
        st.success("No high-risk assets identified!")
        return

    # Create DataFrame
    df_high_risk = pd.DataFrame(high_risk_assets)

    # Display interactive table
    st.dataframe(
        df_high_risk,
        use_container_width=True,
        hide_index=True,
        column_config={
            "risk_score": st.column_config.ProgressColumn(
                "Risk Score", min_value=1, max_value=25, format="%.1f", help="Current risk score"
            ),
            "vulnerability_count": st.column_config.NumberColumn(
                "Vulnerabilities", help="Number of identified vulnerabilities"
            ),
            "environment": st.column_config.TextColumn("Environment", help="Deployment environment"),
        },
    )

    # Show summary statistics
    col1, col2, col3 = st.columns(3)

    with col1:
        avg_risk = df_high_risk["risk_score"].mean()
        st.metric("Average Risk Score", f"{avg_risk:.1f}")

    with col2:
        total_vulns = df_high_risk["vulnerability_count"].sum()
        st.metric("Total Vulnerabilities", total_vulns)

    with col3:
        prod_assets = len(df_high_risk[df_high_risk["environment"] == "PRODUCTION"])
        st.metric("Production Assets", prod_assets)


def create_risk_predictions_section(risk_data: Dict[str, Any]) -> None:
    """Create risk predictions and recommendations section"""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔮 Risk Predictions")

        # Mock predictions
        predictions = [
            {"asset_name": "prod-db-1", "current_risk": 18.5, "predicted_risk": 21.2, "confidence": 0.85},
            {"asset_name": "api-server-2", "current_risk": 16.3, "predicted_risk": 19.1, "confidence": 0.78},
            {"asset_name": "data-warehouse", "current_risk": 14.8, "predicted_risk": 17.5, "confidence": 0.92},
        ]

        display_risk_predictions(predictions)

    with col2:
        st.subheader("💡 Risk Mitigation Recommendations")

        recommendations = [
            {
                "priority": "HIGH",
                "title": "Update critical security patches",
                "impact": "Reduce risk by 25%",
                "effort": "1-2 weeks",
            },
            {
                "priority": "MEDIUM",
                "title": "Implement network segmentation",
                "impact": "Reduce risk by 15%",
                "effort": "3-4 weeks",
            },
            {
                "priority": "MEDIUM",
                "title": "Enhance monitoring coverage",
                "impact": "Improve detection by 40%",
                "effort": "2-3 weeks",
            },
        ]

        for i, rec in enumerate(recommendations, 1):
            priority = rec["priority"]

            if priority == "HIGH":
                st.error(f"**{i}. {rec['title']}**")
            else:
                st.warning(f"**{i}. {rec['title']}**")

            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"**Impact:** {rec['impact']}")
            with col_b:
                st.write(f"**Effort:** {rec['effort']}")

            st.write("---")


def create_vulnerability_trends_chart(trend_data: List[Dict[str, Any]]) -> go.Figure:
    """Create vulnerability trends chart"""
    if not trend_data:
        fig = go.Figure()
        fig.add_annotation(text="No trend data available", showarrow=False)
        return fig

    # Convert to DataFrame
    df = pd.DataFrame(trend_data)
    df["date"] = pd.to_datetime(df["assessment_date"])
    df = df.sort_values("date")

    # Group by date and sum vulnerabilities
    daily_vulns = df.groupby(df["date"].dt.date)["vulnerability_count"].sum().reset_index()

    fig = go.Figure()

    # Add vulnerability count trend
    fig.add_trace(
        go.Scatter(
            x=daily_vulns["date"],
            y=daily_vulns["vulnerability_count"],
            mode="lines+markers",
            name="Total Vulnerabilities",
            line=dict(color="orange", width=3),
            marker=dict(size=6),
            hovertemplate="<b>Date:</b> %{x}<br><b>Vulnerabilities:</b> %{y}<extra></extra>",
        )
    )

    # Add trend line
    x_numeric = list(range(len(daily_vulns)))
    z = np.polyfit(x_numeric, daily_vulns["vulnerability_count"], 1)
    p = np.poly1d(z)

    fig.add_trace(
        go.Scatter(
            x=daily_vulns["date"],
            y=p(x_numeric),
            mode="lines",
            name="Trend",
            line=dict(color="red", width=2, dash="dash"),
            hovertemplate="<b>Trend Line</b><extra></extra>",
        )
    )

    fig.update_layout(
        title="Vulnerability Count Trends",
        xaxis_title="Date",
        yaxis_title="Vulnerability Count",
        height=400,
        hovermode="x unified",
    )

    return fig


def main() -> None:
    """Run main risk dashboard function"""
    try:
        # Create filters
        filters = create_filter_sidebar()
        time_range = filters.get("time_range", "Last 30 days")

        # Load data
        dashboard_data = load_risk_dashboard_data(time_range)
        metrics = dashboard_data["metrics"]
        trend_data = dashboard_data["trend_data"]
        high_risk_assets = dashboard_data["high_risk_assets"]

        # Display KPIs
        display_risk_kpis(metrics)

        # Add separator
        st.divider()

        # Risk trend visualization
        st.subheader("📈 Risk Trend Analysis")

        if trend_data:
            # Create risk trend chart
            fig_trend = create_risk_trend_chart(trend_data)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.warning("No trend data available for the selected time range")

        # Risk distribution and factor analysis
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Risk Distribution")
            fig_dist = create_risk_distribution_chart(metrics)
            st.plotly_chart(fig_dist, use_container_width=True)

        with col2:
            st.subheader("🔍 Risk Factor Analysis")
            fig_factors = create_risk_factor_breakdown(trend_data)
            st.plotly_chart(fig_factors, use_container_width=True)

        # Add separator
        st.divider()

        # Risk heatmap
        st.subheader("🌡️ Asset Risk Heatmap")
        if trend_data:
            fig_heatmap = create_risk_heatmap(trend_data)
            st.plotly_chart(fig_heatmap, use_container_width=True)

        # Add separator
        st.divider()

        # High-risk assets table
        display_high_risk_assets_table(high_risk_assets)

        # Add separator
        st.divider()

        # Vulnerability trends
        st.subheader("🐛 Vulnerability Trends")
        if trend_data:
            fig_vuln_trends = create_vulnerability_trends_chart(trend_data)
            st.plotly_chart(fig_vuln_trends, use_container_width=True)

        # Add separator
        st.divider()

        # Risk predictions and recommendations
        create_risk_predictions_section(metrics)

        # Add refresh info
        st.sidebar.divider()
        st.sidebar.info(
            f"🔄 Last updated: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"Data refreshes every 5 minutes automatically.\n\n"
            f"📊 Showing data for: {time_range}"
        )

    except Exception as e:
        st.error(f"Risk dashboard error: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
