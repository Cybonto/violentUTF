# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Monitoring API Endpoints for Issue #283.

This module provides RESTful API endpoints for the continuous monitoring system,
including events, alerts, metrics, and dashboard data access.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.monitoring_schemas import (
    AlertAcknowledgment,
    AlertResolution,
    MonitoringAlertResponse,
    MonitoringDashboardData,
    MonitoringEventResponse,
    NotificationResponse,
    PerformanceMetricResponse,
    TrendAnalysisRequest,
    TrendAnalysisResponse,
)
from app.services.monitoring.monitoring_service import MonitoringService

router = APIRouter()


@router.get("/events", response_model=List[MonitoringEventResponse])
async def get_monitoring_events(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    asset_id: Optional[uuid.UUID] = Query(None, description="Filter by asset ID"),
    hours_back: int = Query(24, ge=1, le=8760, description="Hours back to search"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> List[MonitoringEventResponse]:
    """Get monitoring events with optional filtering.

    Returns a list of monitoring events filtered by the specified criteria.
    Events are ordered by detection time (newest first).
    """
    monitoring_service = MonitoringService(db)

    try:
        # Calculate time filter
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        events = await monitoring_service.get_events(
            skip=skip,
            limit=limit,
            event_type=event_type,
            asset_id=asset_id,
            since=since,
        )

        return [MonitoringEventResponse.model_validate(event) for event in events]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving monitoring events: {str(e)}",
        ) from e


@router.get("/events/{event_id}", response_model=MonitoringEventResponse)
async def get_monitoring_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> MonitoringEventResponse:
    """Get specific monitoring event by ID."""
    monitoring_service = MonitoringService(db)

    event = await monitoring_service.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring event {event_id} not found",
        )

    return MonitoringEventResponse.model_validate(event)


@router.get("/alerts", response_model=List[MonitoringAlertResponse])
async def get_monitoring_alerts(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    severity: Optional[str] = Query(None, description="Filter by alert severity"),
    alert_status: Optional[str] = Query(None, description="Filter by alert status"),
    asset_id: Optional[uuid.UUID] = Query(None, description="Filter by asset ID"),
    hours_back: int = Query(24, ge=1, le=8760, description="Hours back to search"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> List[MonitoringAlertResponse]:
    """Get monitoring alerts with optional filtering.

    Returns a list of monitoring alerts filtered by the specified criteria.
    Alerts are ordered by creation time (newest first).
    """
    monitoring_service = MonitoringService(db)

    try:
        # Calculate time filter
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        alerts = await monitoring_service.get_alerts(
            skip=skip,
            limit=limit,
            severity=severity,
            status=alert_status,
            asset_id=asset_id,
            since=since,
        )

        return [MonitoringAlertResponse.model_validate(alert) for alert in alerts]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving monitoring alerts: {str(e)}",
        ) from e


@router.get("/alerts/{alert_id}", response_model=MonitoringAlertResponse)
async def get_monitoring_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> MonitoringAlertResponse:
    """Get specific monitoring alert by ID."""
    monitoring_service = MonitoringService(db)

    alert = await monitoring_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitoring alert {alert_id} not found",
        )

    return MonitoringAlertResponse.model_validate(alert)


@router.post("/alerts/{alert_id}/acknowledge", response_model=MonitoringAlertResponse)
async def acknowledge_alert(
    alert_id: uuid.UUID,
    acknowledgment: AlertAcknowledgment,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> MonitoringAlertResponse:
    """Acknowledge a monitoring alert."""
    monitoring_service = MonitoringService(db)

    try:
        # Use current user info for acknowledgment
        acknowledged_by = getattr(current_user, "username", "unknown")

        alert = await monitoring_service.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by=acknowledged_by,
            reason=acknowledgment.acknowledgment_reason,
        )

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring alert {alert_id} not found",
            )

        return MonitoringAlertResponse.model_validate(alert)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error acknowledging alert: {str(e)}",
        ) from e


@router.post("/alerts/{alert_id}/resolve", response_model=MonitoringAlertResponse)
async def resolve_alert(
    alert_id: uuid.UUID,
    resolution: AlertResolution,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> MonitoringAlertResponse:
    """Resolve a monitoring alert."""
    monitoring_service = MonitoringService(db)

    try:
        # Use current user info for resolution
        resolved_by = getattr(current_user, "username", "unknown")

        alert = await monitoring_service.resolve_alert(
            alert_id=alert_id,
            resolved_by=resolved_by,
            resolution_reason=resolution.resolution_reason,
        )

        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring alert {alert_id} not found",
            )

        return MonitoringAlertResponse.model_validate(alert)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resolving alert: {str(e)}",
        ) from e


@router.get("/metrics", response_model=List[PerformanceMetricResponse])
async def get_performance_metrics(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(1000, ge=1, le=10000, description="Number of records to return"),
    asset_id: Optional[uuid.UUID] = Query(None, description="Filter by asset ID"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    hours_back: int = Query(24, ge=1, le=8760, description="Hours back to search"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> List[PerformanceMetricResponse]:
    """Get performance metrics with optional filtering.

    Returns a list of performance metrics filtered by the specified criteria.
    Metrics are ordered by timestamp (newest first).
    """
    monitoring_service = MonitoringService(db)

    try:
        # Calculate time filter
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        metrics = await monitoring_service.get_metrics(
            skip=skip,
            limit=limit,
            asset_id=asset_id,
            metric_type=metric_type,
            since=since,
        )

        return [PerformanceMetricResponse.model_validate(metric) for metric in metrics]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving performance metrics: {str(e)}",
        ) from e


@router.post("/metrics/trends", response_model=List[TrendAnalysisResponse])
async def analyze_metric_trends(
    request: TrendAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> List[TrendAnalysisResponse]:
    """Analyze performance metric trends.

    Performs trend analysis on the specified metrics over the given time range
    with optional anomaly detection and predictions.
    """
    monitoring_service = MonitoringService(db)

    try:
        trend_analyses = await monitoring_service.analyze_metric_trends(
            asset_id=request.asset_id,
            metric_types=request.metric_types,
            time_range_hours=request.time_range_hours,
            aggregation_interval_minutes=request.aggregation_interval_minutes,
            include_predictions=request.include_predictions,
        )

        return trend_analyses

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing metric trends: {str(e)}",
        ) from e


@router.get("/dashboard", response_model=MonitoringDashboardData)
async def get_dashboard_data(
    time_range_hours: int = Query(24, ge=1, le=168, description="Time range for dashboard data"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> MonitoringDashboardData:
    """Get comprehensive monitoring dashboard data.

    Returns aggregated monitoring data for dashboard display including
    asset counts, alert summaries, recent events, and performance trends.
    """
    monitoring_service = MonitoringService(db)

    try:
        dashboard_data = await monitoring_service.get_dashboard_data(time_range_hours)
        return dashboard_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard data: {str(e)}",
        ) from e


@router.get("/health", response_model=Dict[str, str])
async def get_monitoring_health(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> Dict[str, str]:
    """Get monitoring system health status.

    Returns the current health status of the monitoring system components
    including container monitoring, schema monitoring, and alerting.
    """
    monitoring_service = MonitoringService(db)

    try:
        health_status = await monitoring_service.get_health_status()
        return health_status

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving monitoring health: {str(e)}",
        ) from e


@router.get("/notifications/{alert_id}", response_model=List[NotificationResponse])
async def get_alert_notifications(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> List[NotificationResponse]:
    """Get notifications for a specific alert.

    Returns all notification attempts and their delivery status for the specified alert.
    """
    monitoring_service = MonitoringService(db)

    try:
        notifications = await monitoring_service.get_alert_notifications(alert_id)
        return [NotificationResponse.model_validate(notification) for notification in notifications]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving alert notifications: {str(e)}",
        ) from e


@router.get("/assets/{asset_id}/monitoring-status")
async def get_asset_monitoring_status(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> Dict[str, Any]:
    """Get monitoring status for a specific asset.

    Returns detailed monitoring status including enabled monitors,
    recent events, current metrics, and health status.
    """
    monitoring_service = MonitoringService(db)

    try:
        status_data = await monitoring_service.get_asset_monitoring_status(asset_id)

        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset {asset_id} not found or not monitored",
            )

        return status_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving asset monitoring status: {str(e)}",
        ) from e


@router.post("/assets/{asset_id}/monitoring/enable")
async def enable_asset_monitoring(
    asset_id: uuid.UUID,
    monitoring_config: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> Dict[str, str]:
    """Enable monitoring for a specific asset.

    Enables monitoring for the specified asset with optional custom configuration.
    """
    monitoring_service = MonitoringService(db)

    try:
        await monitoring_service.enable_asset_monitoring(
            asset_id=asset_id,
            config=monitoring_config or {},
            enabled_by=getattr(current_user, "username", "unknown"),
        )

        return {"status": "success", "message": f"Monitoring enabled for asset {asset_id}"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enabling asset monitoring: {str(e)}",
        ) from e


@router.post("/assets/{asset_id}/monitoring/disable")
async def disable_asset_monitoring(
    asset_id: uuid.UUID,
    reason: str = Query(..., description="Reason for disabling monitoring"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> Dict[str, str]:
    """Disable monitoring for a specific asset.

    Disables monitoring for the specified asset with a required reason.
    """
    monitoring_service = MonitoringService(db)

    try:
        await monitoring_service.disable_asset_monitoring(
            asset_id=asset_id,
            reason=reason,
            disabled_by=getattr(current_user, "username", "unknown"),
        )

        return {"status": "success", "message": f"Monitoring disabled for asset {asset_id}"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error disabling asset monitoring: {str(e)}",
        ) from e


@router.get("/statistics", response_model=Dict[str, Any])
async def get_monitoring_statistics(
    time_range_hours: int = Query(24, ge=1, le=8760, description="Time range for statistics"),
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),  # noqa: ANN401
) -> Dict[str, Any]:
    """Get comprehensive monitoring statistics.

    Returns detailed statistics about monitoring system performance,
    event counts, alert patterns, and system efficiency.
    """
    monitoring_service = MonitoringService(db)

    try:
        statistics = await monitoring_service.get_monitoring_statistics(time_range_hours)
        return statistics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving monitoring statistics: {str(e)}",
        ) from e
