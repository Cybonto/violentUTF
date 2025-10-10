#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Dashboard API Endpoints for Issue #284

This module provides REST API endpoints for dashboard metrics and KPIs
for the database asset management dashboard system.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.database import get_session
from app.services.dashboard_metrics_service import DashboardMetricsService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(db: AsyncSession = Depends(get_session)) -> DashboardMetricsService:
    """Get dashboard metrics service instance with dependencies."""
    return DashboardMetricsService(db)


@router.get("/asset-inventory-metrics")
async def get_asset_inventory_metrics(
    service: DashboardMetricsService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get comprehensive asset inventory dashboard metrics.

    Returns:
        Dictionary containing:
        - total_assets: Total number of assets
        - assets_by_type: Breakdown by asset type
        - assets_by_environment: Breakdown by environment
        - critical_assets: Count of critical assets
        - high_risk_assets: Count of high-risk assets
        - compliance_score: Average compliance score
        - monitoring_coverage: Percentage of monitored assets
    """
    try:
        metrics = await service.get_asset_inventory_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get asset inventory metrics: {str(e)}"
        ) from e


@router.get("/risk-metrics")
async def get_risk_dashboard_metrics(
    service: DashboardMetricsService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get risk dashboard metrics and trends.

    Returns:
        Dictionary containing:
        - average_risk_score: Overall average risk score
        - risk_distribution: Count by risk level
        - risk_velocity: Risk change rate per day
        - predicted_30_day_change: Predicted risk change
        - high_priority_vulnerabilities: Count of high-priority vulns
        - assets_requiring_attention: List of high-risk assets
    """
    try:
        metrics = await service.get_risk_dashboard_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get risk dashboard metrics: {str(e)}"
        ) from e


@router.get("/executive-report")
async def get_executive_report_data(
    service: DashboardMetricsService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get executive-level dashboard data and KPIs.

    Returns:
        Dictionary containing:
        - summary: High-level metrics summary
        - trends: Trend analysis data
        - recommendations: Actionable recommendations
        - cost_impact: Cost and ROI analysis
    """
    try:
        # Check if user has executive access
        user_roles = current_user.get("roles", [])
        if "admin" not in user_roles and "executive" not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Executive dashboard access requires admin or executive role",
            )

        report_data = await service.get_executive_report_data()
        return report_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get executive report data: {str(e)}"
        ) from e


@router.get("/operational-metrics")
async def get_operational_dashboard_metrics(
    service: DashboardMetricsService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get operational dashboard metrics for system monitoring.

    Returns:
        Dictionary containing:
        - system_health: System health indicators
        - alerts: Current system alerts
        - performance_metrics: Performance monitoring data
    """
    try:
        metrics = await service.get_operational_dashboard_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get operational dashboard metrics: {str(e)}",
        ) from e


@router.get("/compliance-summary")
async def get_compliance_dashboard_summary(
    framework: Optional[str] = Query(None, description="Filter by compliance framework"),
    service: DashboardMetricsService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get compliance dashboard summary data.

    Args:
        framework: Optional filter by compliance framework

    Returns:
        Dictionary containing compliance summary metrics
    """
    try:
        # For now, return basic compliance data from executive report
        # In a full implementation, this would have its own service method
        exec_data = await service.get_executive_report_data()

        compliance_summary = {
            "overall_compliance_score": exec_data["summary"]["compliance_percentage"],
            "frameworks": {
                "SOC2": {"score": 85.5, "compliant": True, "gaps": 2},
                "GDPR": {"score": 78.1, "compliant": False, "gaps": 5},
                "NIST": {"score": 83.7, "compliant": True, "gaps": 1},
            },
            "trending": {
                "direction": "improving" if exec_data["trends"]["compliance_improvement"] > 0 else "declining",
                "change_percentage": exec_data["trends"]["compliance_improvement"],
                "period": "30_days",
            },
            "high_priority_gaps": 3,
            "total_assets_assessed": exec_data["summary"]["total_assets"],
        }

        # Filter by framework if specified
        if framework and framework in compliance_summary["frameworks"]:
            compliance_summary["frameworks"] = {framework: compliance_summary["frameworks"][framework]}

        return compliance_summary

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get compliance dashboard summary: {str(e)}",
        ) from e


@router.get("/real-time-status")
async def get_real_time_dashboard_status(
    service: DashboardMetricsService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get real-time dashboard status for live updates.

    Returns:
        Dictionary containing:
        - last_updated: Timestamp of last data update
        - active_alerts: Current active alerts count
        - system_status: Overall system status
        - data_freshness: Age of data in seconds
    """
    try:
        operational_metrics = await service.get_operational_dashboard_metrics()

        real_time_status = {
            "last_updated": datetime.utcnow().isoformat(),
            "active_alerts": len(operational_metrics["alerts"]),
            "system_status": (
                "healthy" if operational_metrics["system_health"]["uptime_percentage"] > 99.0 else "degraded"
            ),
            "data_freshness": 30,  # seconds - in real implementation would calculate actual freshness
            "refresh_interval": 30,  # seconds
            "next_refresh": (datetime.utcnow() + timedelta(seconds=30)).isoformat(),
        }

        return real_time_status

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get real-time dashboard status: {str(e)}",
        ) from e


@router.get("/performance-metrics")
async def get_dashboard_performance_metrics(
    service: DashboardMetricsService = Depends(get_dashboard_service),
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get dashboard performance metrics for monitoring dashboard itself.

    Returns:
        Dictionary containing dashboard performance data
    """
    try:
        # Mock performance data - in real implementation would come from APM tools
        performance_metrics = {
            "page_load_times": {
                "asset_inventory": 2.1,  # seconds
                "risk_dashboard": 2.8,
                "compliance_dashboard": 2.3,
                "executive_dashboard": 1.9,
                "operational_dashboard": 2.5,
            },
            "api_response_times": {
                "asset_metrics": 0.15,  # seconds
                "risk_metrics": 0.22,
                "compliance_metrics": 0.18,
                "executive_metrics": 0.12,
            },
            "user_activity": {"active_sessions": 25, "page_views_last_hour": 156, "unique_users_today": 12},
            "system_resources": {"cpu_usage": 45.2, "memory_usage": 68.1, "disk_usage": 72.5},  # percentage
        }

        return performance_metrics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard performance metrics: {str(e)}",
        ) from e
