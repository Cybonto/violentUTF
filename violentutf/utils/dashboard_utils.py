#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Dashboard Utilities for Issue #284

Provides utility functions for dashboard data processing, filtering, and calculations.
"""

from datetime import datetime
from typing import Any, Dict, List

import pandas as pd


def calculate_asset_metrics(assets_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate key asset metrics"""
    if not assets_data:
        return {"total_assets": 0, "critical_assets": 0, "avg_risk_score": 0.0, "avg_compliance_score": 0.0}

    total_assets = len(assets_data)
    critical_assets = sum(1 for asset in assets_data if asset.get("criticality_level") == "CRITICAL")
    high_assets = sum(1 for asset in assets_data if asset.get("criticality_level") == "HIGH")

    # Calculate average scores
    risk_scores = [asset.get("risk_score", 0) for asset in assets_data]
    compliance_scores = [asset.get("compliance_score", 0) for asset in assets_data]

    avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0
    avg_compliance_score = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0.0

    return {
        "total_assets": total_assets,
        "critical_assets": critical_assets,
        "high_assets": high_assets,
        "avg_risk_score": round(avg_risk_score, 1),
        "avg_compliance_score": round(avg_compliance_score, 1),
    }


def apply_asset_filters(assets_data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply filters to asset data"""
    if not assets_data or not filters:
        return assets_data

    filtered_assets = []

    for asset in assets_data:
        include_asset = True

        # Asset type filter
        if filters.get("asset_types") and asset.get("asset_type") not in filters["asset_types"]:
            include_asset = False

        # Environment filter
        if filters.get("environments") and asset.get("environment") not in filters["environments"]:
            include_asset = False

        # Criticality filter
        if filters.get("criticality_levels") and asset.get("criticality_level") not in filters["criticality_levels"]:
            include_asset = False

        # Risk level filter (convert risk_score to risk_level)
        if filters.get("risk_levels"):
            risk_score = asset.get("risk_score", 0)
            risk_level = get_risk_level_from_score(risk_score)
            if risk_level not in filters["risk_levels"]:
                include_asset = False

        # Search filter
        search_term = filters.get("search", "").lower()
        if search_term:
            searchable_text = (
                f"{asset.get('name', '')} {asset.get('description', '')} {asset.get('owner_team', '')}".lower()
            )
            if search_term not in searchable_text:
                include_asset = False

        # Date range filter
        if filters.get("date_range"):
            try:
                if isinstance(filters["date_range"], (tuple, list)) and len(filters["date_range"]) == 2:
                    start_date, end_date = filters["date_range"]
                    asset_date = asset.get("last_updated")

                    if isinstance(asset_date, str):
                        asset_date = datetime.fromisoformat(asset_date.replace("Z", "+00:00"))
                    elif isinstance(asset_date, datetime):
                        pass  # Already datetime
                    else:
                        continue  # Skip if date format is unknown

                    # Convert to date for comparison
                    asset_date = asset_date.date()

                    if not (start_date <= asset_date <= end_date):
                        include_asset = False
            except Exception:
                # Skip date filtering if there's an error
                pass

        if include_asset:
            filtered_assets.append(asset)

    return filtered_assets


def format_asset_data_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Format asset data for display in Streamlit dataframe"""
    display_df = df.copy()

    # Select and rename columns for display
    column_mapping = {
        "id": "Asset ID",
        "name": "Name",
        "asset_type": "Type",
        "environment": "Environment",
        "risk_score": "Risk Score",
        "compliance_score": "Compliance %",
        "criticality_level": "Criticality",
        "owner_team": "Owner Team",
        "technical_contact": "Contact",
    }

    # Select only columns that exist
    available_columns = [col for col in column_mapping.keys() if col in display_df.columns]
    display_df = display_df[available_columns]

    # Rename columns
    display_df = display_df.rename(columns={col: column_mapping[col] for col in available_columns})

    # Format numeric columns
    if "Risk Score" in display_df.columns:
        display_df["Risk Score"] = display_df["Risk Score"].round(1)

    if "Compliance %" in display_df.columns:
        display_df["Compliance %"] = display_df["Compliance %"].round(1)

    return display_df


def get_risk_level_from_score(risk_score: float) -> str:
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


def calculate_risk_metrics(risk_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate risk dashboard metrics"""
    if not risk_data:
        return {"average_risk_score": 0.0, "critical_count": 0, "risk_velocity": 0.0}

    # Calculate average risk score
    risk_scores = [item.get("risk_score", 0) for item in risk_data]
    average_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

    # Count critical assets
    critical_count = sum(1 for item in risk_data if item.get("risk_level") == "CRITICAL")

    # Calculate risk velocity (simplified)
    # In real implementation, this would compare with historical data
    risk_velocity = 0.05  # Mock value

    return {
        "average_risk_score": round(average_risk_score, 1),
        "critical_count": critical_count,
        "risk_velocity": risk_velocity,
    }


def filter_high_risk_assets(risk_data: List[Dict[str, Any]], threshold: float = 15.0) -> List[Dict[str, Any]]:
    """Filter assets with risk scores above threshold"""
    return [item for item in risk_data if item.get("risk_score", 0) > threshold]


def calculate_compliance_metrics(compliance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate compliance dashboard metrics"""
    if not compliance_data:
        return {"overall_compliance_score": 0.0, "compliant_assets": 0, "high_priority_gaps": 0}

    # Calculate overall compliance score
    scores = [item.get("overall_score", 0) for item in compliance_data]
    overall_compliance_score = sum(scores) / len(scores) if scores else 0.0

    # Count compliant assets
    compliant_assets = sum(1 for item in compliance_data if item.get("compliant", False))

    # Count high priority gaps
    high_priority_gaps = 0
    for item in compliance_data:
        gaps = item.get("gaps", [])
        high_priority_gaps += sum(1 for gap in gaps if gap.get("severity") == "HIGH")

    return {
        "overall_compliance_score": round(overall_compliance_score, 1),
        "compliant_assets": compliant_assets,
        "high_priority_gaps": high_priority_gaps,
    }


def analyze_compliance_gaps(compliance_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze compliance gaps across all data"""
    high_priority_gaps = []
    medium_priority_gaps = []
    low_priority_gaps = []

    for item in compliance_data:
        gaps = item.get("gaps", [])
        for gap in gaps:
            severity = gap.get("severity", "MEDIUM")
            if severity == "HIGH":
                high_priority_gaps.append(gap)
            elif severity == "MEDIUM":
                medium_priority_gaps.append(gap)
            else:
                low_priority_gaps.append(gap)

    return {
        "high_priority_gaps": high_priority_gaps,
        "medium_priority_gaps": medium_priority_gaps,
        "low_priority_gaps": low_priority_gaps,
    }


def calculate_executive_kpis(executive_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate executive KPIs from dashboard data"""
    trends = executive_data.get("trends", {})

    kpis = {
        "security_improvement_rate": trends.get("security_improvement", 0.0),
        "asset_growth_rate": trends.get("new_assets_30_days", 0),
        "vulnerability_resolution_rate": trends.get("resolved_vulnerabilities", 0),
    }

    return kpis


def process_monitoring_updates(current_health: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process real-time monitoring updates"""
    updated_health = current_health.copy()
    updated_health.update(new_data)

    # Add timestamp
    updated_health["last_updated"] = datetime.now().isoformat()

    return updated_health


def schedule_data_refresh(refresh_interval: int) -> None:
    """Schedule data refresh (mock implementation)"""
    # In real implementation, this would set up periodic refresh
    import time

    time.sleep(0.1)  # Simulate scheduling


def apply_responsive_layout(screen_size: str) -> Dict[str, Any]:
    """Apply responsive layout configuration"""
    layouts = {
        "mobile": {"columns": 1, "chart_height": 300, "table_height": 400},
        "tablet": {"columns": 2, "chart_height": 400, "table_height": 500},
        "desktop": {"columns": 4, "chart_height": 500, "table_height": 600},
    }

    return layouts.get(screen_size, layouts["desktop"])


def check_dashboard_permissions(user: Dict[str, Any], dashboard_type: str) -> bool:
    """Check if user has permissions for specific dashboard"""
    user_roles = user.get("roles", [])

    # Admin has access to everything
    if "admin" in user_roles:
        return True

    # Check specific dashboard permissions
    if dashboard_type == "executive_dashboard":
        return "executive" in user_roles or "admin" in user_roles
    elif dashboard_type == "operational_dashboard":
        return "operations" in user_roles or "admin" in user_roles
    else:
        # Basic dashboards accessible to all authenticated users
        return True


def format_metric_delta(current_value: float, previous_value: float) -> str:
    """Format metric delta for display"""
    if previous_value == 0:
        return "N/A"

    delta = current_value - previous_value
    percentage = (delta / previous_value) * 100

    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.1f} ({sign}{percentage:.1f}%)"


def create_trend_analysis(data: List[Dict[str, Any]], value_key: str, date_key: str) -> Dict[str, Any]:
    """Create trend analysis from time series data"""
    if len(data) < 2:
        return {"trend": "insufficient_data", "direction": "unknown", "slope": 0.0}

    # Sort by date
    sorted_data = sorted(data, key=lambda x: x[date_key])

    # Calculate simple linear trend
    values = [item[value_key] for item in sorted_data]
    x = list(range(len(values)))

    # Simple linear regression
    n = len(values)
    sum_x = sum(x)
    sum_y = sum(values)
    sum_xy = sum(x[i] * values[i] for i in range(n))
    sum_x2 = sum(xi**2 for xi in x)

    if n * sum_x2 - sum_x**2 != 0:
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
    else:
        slope = 0.0

    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"

    return {"trend": "linear", "direction": direction, "slope": slope}
