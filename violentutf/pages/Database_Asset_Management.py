#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Database Asset Management Dashboard Page for Issue #284

This page provides a comprehensive asset inventory dashboard with real-time
visualization, filtering, and management capabilities.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from violentutf.components.dashboard_components import display_asset_details

# Import utility modules
from violentutf.utils.api_client import DashboardAPIClient
from violentutf.utils.dashboard_utils import apply_asset_filters, format_asset_data_for_display

# Configure page
st.set_page_config(
    page_title="Database Asset Management", page_icon="🗄️", layout="wide", initial_sidebar_state="expanded"
)

st.title("🗄️ Database Asset Management Dashboard")
st.markdown("Real-time inventory and management of all database assets")


@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_dashboard_data() -> Dict[str, Any]:
    """Load dashboard data with caching"""
    try:
        client = DashboardAPIClient()

        # Load asset inventory metrics
        asset_metrics = client.get_asset_inventory_metrics()

        # Load asset list (mock data for now)
        assets_data = [
            {
                "id": f"asset-{i}",
                "name": f"database-{i}",
                "asset_type": ["POSTGRESQL", "SQLITE", "DUCKDB"][i % 3],
                "environment": ["PRODUCTION", "STAGING", "DEVELOPMENT"][i % 3],
                "risk_score": 10 + (i % 15),
                "compliance_score": 80 + (i % 20),
                "criticality_level": ["LOW", "MEDIUM", "HIGH", "CRITICAL"][i % 4],
                "owner_team": f"team-{i % 3}",
                "technical_contact": f"admin{i}@example.com",
                "last_updated": datetime.now() - timedelta(days=i % 30),
            }
            for i in range(1, 26)  # 25 sample assets
        ]

        return {"metrics": asset_metrics, "assets": assets_data}
    except Exception as e:
        st.error(f"Error loading dashboard data: {str(e)}")
        # Return mock data on error
        return {
            "metrics": {"total_assets": 25, "critical_assets": 5, "high_risk_assets": 8, "compliance_score": 84.2},
            "assets": [],
        }


def create_asset_filters() -> Dict[str, Any]:
    """Create sidebar filter controls"""
    with st.sidebar:
        st.header("🔍 Filter Assets")

        filters: Dict[str, Any] = {}

        # Asset type filter
        asset_types = st.multiselect(
            "Asset Types",
            options=["POSTGRESQL", "SQLITE", "DUCKDB", "FILE_STORAGE"],
            default=["POSTGRESQL", "SQLITE", "DUCKDB", "FILE_STORAGE"],
            help="Select asset types to display",
        )
        filters["asset_types"] = asset_types

        # Environment filter
        environments = st.multiselect(
            "Environments",
            options=["DEVELOPMENT", "TESTING", "STAGING", "PRODUCTION"],
            default=["DEVELOPMENT", "TESTING", "STAGING", "PRODUCTION"],
            help="Select environments to display",
        )
        filters["environments"] = environments

        # Risk level filter
        risk_levels = st.multiselect(
            "Risk Levels",
            options=["LOW", "MEDIUM", "HIGH", "VERY_HIGH", "CRITICAL"],
            default=["LOW", "MEDIUM", "HIGH", "VERY_HIGH", "CRITICAL"],
            help="Select risk levels to display",
        )
        filters["risk_levels"] = risk_levels

        # Criticality filter
        criticality_levels = st.multiselect(
            "Criticality Levels",
            options=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            default=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            help="Select criticality levels to display",
        )
        filters["criticality_levels"] = criticality_levels

        # Date range filter
        st.subheader("Date Range")
        date_range = st.date_input(
            "Last Updated Range",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            max_value=datetime.now(),
            help="Filter by last update date",
        )
        filters["date_range"] = date_range

        # Search box
        search_term = st.text_input(
            "Search Assets",
            placeholder="Enter asset name or description...",
            help="Search across asset names and descriptions",
        )
        filters["search"] = search_term

        return filters


def display_key_metrics(metrics: Dict[str, Any]) -> None:
    """Display key asset metrics in columns"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Assets",
            value=metrics.get("total_assets", 0),
            delta=f"+{metrics.get('new_assets_30_days', 0)} this month",
            help="Total number of assets in inventory",
        )

    with col2:
        critical_assets = metrics.get("critical_assets", 0)
        st.metric(
            label="Critical Assets",
            value=critical_assets,
            delta=metrics.get("critical_delta", 0),
            delta_color="inverse",
            help="Assets with critical importance level",
        )

    with col3:
        high_risk_assets = metrics.get("high_risk_assets", 0)
        st.metric(
            label="High Risk Assets",
            value=high_risk_assets,
            delta=metrics.get("risk_delta", 0),
            delta_color="inverse",
            help="Assets with high risk scores (>15)",
        )

    with col4:
        compliance_score = metrics.get("compliance_score", 0)
        st.metric(
            label="Compliance Score",
            value=f"{compliance_score:.1f}%",
            delta=f"{metrics.get('compliance_delta', 0):+.1f}%",
            help="Average compliance score across all assets",
        )


def create_asset_distribution_charts(assets_data: List[Dict[str, Any]]) -> None:
    """Create asset distribution visualization charts"""
    st.subheader("📊 Asset Distribution Analysis")

    if not assets_data:
        st.warning("No asset data available for visualization")
        return

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        # Asset type distribution pie chart
        asset_type_df = pd.DataFrame(assets_data)
        type_counts = asset_type_df["asset_type"].value_counts()

        fig_type = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            title="Assets by Type",
            color_discrete_map={
                "POSTGRESQL": "#336791",
                "SQLITE": "#003B57",
                "DUCKDB": "#FFC61A",
                "FILE_STORAGE": "#28A745",
            },
        )
        fig_type.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_type, use_container_width=True)

    with chart_col2:
        # Risk level distribution bar chart
        if "risk_score" in asset_type_df.columns:
            # Create risk level bins
            asset_type_df["risk_level"] = pd.cut(
                asset_type_df["risk_score"],
                bins=[0, 5, 10, 15, 20, 25],
                labels=["LOW", "MEDIUM", "HIGH", "VERY_HIGH", "CRITICAL"],
            )
            risk_counts = asset_type_df["risk_level"].value_counts()

            fig_risk = px.bar(
                x=risk_counts.index,
                y=risk_counts.values,
                title="Assets by Risk Level",
                color=risk_counts.index,
                color_discrete_map={
                    "LOW": "#28A745",
                    "MEDIUM": "#FFC107",
                    "HIGH": "#FD7E14",
                    "VERY_HIGH": "#DC3545",
                    "CRITICAL": "#6F1E51",
                },
            )
            fig_risk.update_layout(xaxis_title="Risk Level", yaxis_title="Number of Assets", showlegend=False)
            st.plotly_chart(fig_risk, use_container_width=True)


def create_interactive_asset_table(assets_data: List[Dict[str, Any]], filters: Dict[str, Any]) -> None:
    """Create interactive asset table with filtering"""
    st.subheader("📋 Asset Inventory")

    if not assets_data:
        st.warning("No assets found matching current filters")
        return

    # Apply filters
    filtered_assets = apply_asset_filters(assets_data, filters)

    if not filtered_assets:
        st.warning("No assets match the selected filters")
        return

    # Create DataFrame
    df_assets = pd.DataFrame(filtered_assets)

    # Format data for display
    display_df = format_asset_data_for_display(df_assets)

    # Display interactive dataframe
    selected_data = st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "risk_score": st.column_config.ProgressColumn(
                "Risk Score", help="Current risk score (1-25 scale)", min_value=1, max_value=25, format="%.1f"
            ),
            "compliance_score": st.column_config.ProgressColumn(
                "Compliance", help="Compliance percentage", min_value=0, max_value=100, format="%.1f%%"
            ),
            "asset_type": st.column_config.TextColumn("Type", help="Database asset type"),
            "environment": st.column_config.TextColumn(
                "Environment",
                help="Deployment environment",
            ),
        },
        on_select="rerun",
        selection_mode="single-row",
    )

    # Show asset details if selected
    try:
        # Type: ignore for mypy since DataframeState selection structure isn't well-typed
        # Check if data is selected (type: ignore for mypy compatibility)
        if (
            hasattr(selected_data, "selection")
            and hasattr(selected_data.selection, "rows")
            and selected_data.selection.rows  # type: ignore
        ):
            selected_idx = selected_data.selection.rows[0]  # type: ignore
            selected_asset = filtered_assets[selected_idx]

            with st.expander(f"🔍 Asset Details: {selected_asset['name']}", expanded=True):
                display_asset_details(selected_asset)
    except (AttributeError, IndexError):
        pass  # Handle cases where selection is not available


def display_asset_summary_stats(assets_data: List[Dict[str, Any]]) -> None:
    """Display summary statistics for current asset view"""
    if not assets_data:
        return

    st.subheader("📈 Current View Summary")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_shown = len(assets_data)
        st.metric("Assets Shown", total_shown)

    with col2:
        avg_risk = sum(asset.get("risk_score", 0) for asset in assets_data) / len(assets_data)
        st.metric("Avg Risk Score", f"{avg_risk:.1f}")

    with col3:
        avg_compliance = sum(asset.get("compliance_score", 0) for asset in assets_data) / len(assets_data)
        st.metric("Avg Compliance", f"{avg_compliance:.1f}%")

    with col4:
        critical_count = sum(1 for asset in assets_data if asset.get("criticality_level") == "CRITICAL")
        st.metric("Critical Assets", critical_count)


def main() -> None:
    """Run main dashboard function"""
    try:
        # Load data
        dashboard_data = load_dashboard_data()
        metrics = dashboard_data["metrics"]
        assets_data = dashboard_data["assets"]

        # Create filters
        filters = create_asset_filters()

        # Display key metrics
        display_key_metrics(metrics)

        # Add separator
        st.divider()

        # Apply filters to assets
        filtered_assets = apply_asset_filters(assets_data, filters)

        # Asset distribution charts
        create_asset_distribution_charts(filtered_assets)

        # Add separator
        st.divider()

        # Display summary stats for current view
        display_asset_summary_stats(filtered_assets)

        # Interactive asset table
        create_interactive_asset_table(filtered_assets, filters)

        # Add refresh info
        st.sidebar.divider()
        st.sidebar.info(
            f"🔄 Last updated: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"Data refreshes every 5 minutes automatically."
        )

    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    main()
