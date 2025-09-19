# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Central Monitoring Service for Issue #283.

This module provides a central service for managing all monitoring operations,
aggregating data from various monitoring components, and providing unified access.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import (
    AlertSeverity,
    AlertStatus,
    MetricType,
    MonitoringAlert,
    MonitoringEvent,
    NotificationLog,
    PerformanceMetric,
)
from app.schemas.monitoring_schemas import (
    MonitoringDashboardData,
    TrendAnalysisResponse,
)

logger = logging.getLogger(__name__)


class MonitoringService:
    """Central service for monitoring operations and data aggregation."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the monitoring service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_events(
        self,
        skip: int = 0,
        limit: int = 100,
        event_type: Optional[str] = None,
        asset_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[MonitoringEvent]:
        """Get monitoring events with filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            event_type: Filter by event type
            asset_id: Filter by asset ID
            since: Filter events since this timestamp

        Returns:
            List of monitoring events
        """
        query = select(MonitoringEvent).order_by(desc(MonitoringEvent.detected_at))

        # Apply filters
        conditions = []

        if event_type:
            conditions.append(MonitoringEvent.event_type == event_type)

        if asset_id:
            conditions.append(MonitoringEvent.asset_id == asset_id)

        if since:
            conditions.append(MonitoringEvent.detected_at >= since)

        if conditions:
            query = query.where(and_(*conditions))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_event(self, event_id: str) -> Optional[MonitoringEvent]:
        """Get specific monitoring event by ID.

        Args:
            event_id: Event UUID

        Returns:
            MonitoringEvent if found
        """
        result = await self.db.execute(select(MonitoringEvent).where(MonitoringEvent.id == event_id))
        return result.scalar_one_or_none()

    async def get_alerts(
        self,
        skip: int = 0,
        limit: int = 100,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        asset_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[MonitoringAlert]:
        """Get monitoring alerts with filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            severity: Filter by alert severity
            status: Filter by alert status
            asset_id: Filter by asset ID
            since: Filter alerts since this timestamp

        Returns:
            List of monitoring alerts
        """
        query = select(MonitoringAlert).order_by(desc(MonitoringAlert.created_at))

        # Apply filters
        conditions = []

        if severity:
            conditions.append(MonitoringAlert.severity == severity)

        if status:
            conditions.append(MonitoringAlert.status == status)

        if asset_id:
            conditions.append(MonitoringAlert.asset_id == asset_id)

        if since:
            conditions.append(MonitoringAlert.created_at >= since)

        if conditions:
            query = query.where(and_(*conditions))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_alert(self, alert_id: str) -> Optional[MonitoringAlert]:
        """Get specific monitoring alert by ID.

        Args:
            alert_id: Alert UUID

        Returns:
            MonitoringAlert if found
        """
        result = await self.db.execute(select(MonitoringAlert).where(MonitoringAlert.id == alert_id))
        return result.scalar_one_or_none()

    async def acknowledge_alert(
        self, alert_id: str, acknowledged_by: str, reason: Optional[str] = None
    ) -> Optional[MonitoringAlert]:
        """Acknowledge a monitoring alert.

        Args:
            alert_id: Alert UUID
            acknowledged_by: User acknowledging the alert
            reason: Optional acknowledgment reason

        Returns:
            Updated MonitoringAlert if found
        """
        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.acknowledged_by = acknowledged_by

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_reason: str) -> Optional[MonitoringAlert]:
        """Resolve a monitoring alert.

        Args:
            alert_id: Alert UUID
            resolved_by: User resolving the alert
            resolution_reason: Reason for resolution

        Returns:
            Updated MonitoringAlert if found
        """
        alert = await self.get_alert(alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        alert.resolved_by = resolved_by
        alert.resolution_reason = resolution_reason

        await self.db.commit()
        await self.db.refresh(alert)

        return alert

    async def get_metrics(
        self,
        skip: int = 0,
        limit: int = 1000,
        asset_id: Optional[str] = None,
        metric_type: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[PerformanceMetric]:
        """Get performance metrics with filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records
            asset_id: Filter by asset ID
            metric_type: Filter by metric type
            since: Filter metrics since this timestamp

        Returns:
            List of performance metrics
        """
        query = select(PerformanceMetric).order_by(desc(PerformanceMetric.timestamp))

        # Apply filters
        conditions = []

        if asset_id:
            conditions.append(PerformanceMetric.asset_id == asset_id)

        if metric_type:
            conditions.append(PerformanceMetric.metric_type == metric_type)

        if since:
            conditions.append(PerformanceMetric.timestamp >= since)

        if conditions:
            query = query.where(and_(*conditions))

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def analyze_metric_trends(
        self,
        asset_id: Optional[str] = None,
        metric_types: List[MetricType] = None,
        time_range_hours: int = 24,
        aggregation_interval_minutes: int = 60,
        include_predictions: bool = False,
    ) -> List[TrendAnalysisResponse]:
        """Analyze performance metric trends.

        Args:
            asset_id: Optional asset ID filter
            metric_types: List of metric types to analyze
            time_range_hours: Time range for analysis
            aggregation_interval_minutes: Aggregation interval
            include_predictions: Whether to include trend predictions

        Returns:
            List of trend analysis results
        """
        results = []

        if not metric_types:
            metric_types = list(MetricType)

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=time_range_hours)

        for metric_type in metric_types:
            try:
                # Get metrics for this type
                query = select(PerformanceMetric).where(
                    and_(
                        PerformanceMetric.metric_type == metric_type,
                        PerformanceMetric.timestamp >= start_time,
                        PerformanceMetric.timestamp <= end_time,
                    )
                )

                if asset_id:
                    query = query.where(PerformanceMetric.asset_id == asset_id)

                query = query.order_by(PerformanceMetric.timestamp)

                result = await self.db.execute(query)
                metrics = result.scalars().all()

                # Perform trend analysis
                trend_analysis = await self.perform_trend_analysis(
                    metrics, metric_type, start_time, end_time, aggregation_interval_minutes, include_predictions
                )

                results.append(trend_analysis)

            except Exception as e:
                logger.error("Error analyzing trends for %s: %s", metric_type, e)

        return results

    async def perform_trend_analysis(
        self,
        metrics: List[PerformanceMetric],
        metric_type: MetricType,
        start_time: datetime,
        end_time: datetime,
        aggregation_interval_minutes: int,
        include_predictions: bool,
    ) -> TrendAnalysisResponse:
        """Perform trend analysis on metric data.

        Args:
            metrics: List of performance metrics
            metric_type: Type of metric being analyzed
            start_time: Analysis start time
            end_time: Analysis end time
            aggregation_interval_minutes: Aggregation interval
            include_predictions: Whether to include predictions

        Returns:
            Trend analysis result
        """
        # Aggregate data by interval
        data_points = []
        anomalies = []

        if metrics:
            # Simple aggregation by time buckets
            interval_delta = timedelta(minutes=aggregation_interval_minutes)
            current_time = start_time

            while current_time < end_time:
                bucket_end = current_time + interval_delta

                # Get metrics in this time bucket
                bucket_metrics = [m for m in metrics if current_time <= m.timestamp < bucket_end]

                if bucket_metrics:
                    avg_value = sum(m.value for m in bucket_metrics) / len(bucket_metrics)
                    max_value = max(m.value for m in bucket_metrics)
                    min_value = min(m.value for m in bucket_metrics)

                    data_points.append(
                        {
                            "timestamp": current_time.isoformat(),
                            "value": avg_value,
                            "min_value": min_value,
                            "max_value": max_value,
                            "count": len(bucket_metrics),
                        }
                    )

                current_time = bucket_end

        # Determine trend direction
        trend_direction = "STABLE"
        if len(data_points) >= 2:
            first_half = data_points[: len(data_points) // 2]
            second_half = data_points[len(data_points) // 2 :]

            if first_half and second_half:
                first_avg = sum(dp["value"] for dp in first_half) / len(first_half)
                second_avg = sum(dp["value"] for dp in second_half) / len(second_half)

                if second_avg > first_avg * 1.1:
                    trend_direction = "UP"
                elif second_avg < first_avg * 0.9:
                    trend_direction = "DOWN"

        # Calculate basic statistics
        values = [dp["value"] for dp in data_points]
        statistics = {}

        if values:
            statistics = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
            }

        # Generate predictions if requested
        predictions = []
        if include_predictions and len(data_points) >= 3:
            # Simple linear trend prediction
            last_value = data_points[-1]["value"]
            prediction_time = end_time + timedelta(hours=1)

            predictions.append(
                {
                    "timestamp": prediction_time.isoformat(),
                    "predicted_value": last_value,  # Simplified prediction
                    "confidence": 0.5,
                }
            )

        return TrendAnalysisResponse(
            asset_id=None,  # Would be set if filtering by asset
            metric_type=metric_type,
            time_range_start=start_time,
            time_range_end=end_time,
            data_points=data_points,
            trend_direction=trend_direction,
            anomalies_detected=anomalies,
            predictions=predictions,
            statistics=statistics,
        )

    async def get_dashboard_data(self, time_range_hours: int = 24) -> MonitoringDashboardData:
        """Get comprehensive monitoring dashboard data.

        Args:
            time_range_hours: Time range for dashboard data

        Returns:
            Dashboard data aggregation
        """
        # Calculate time range
        since = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)

        # Get total monitored assets (placeholder)
        total_monitored_assets = 0

        # Get active alerts count
        active_alerts_result = await self.db.execute(
            select(func.count(MonitoringAlert.id)).where(MonitoringAlert.status == AlertStatus.ACTIVE)
        )
        active_alerts = active_alerts_result.scalar() or 0

        # Get critical alerts count
        critical_alerts_result = await self.db.execute(
            select(func.count(MonitoringAlert.id)).where(
                and_(
                    MonitoringAlert.status == AlertStatus.ACTIVE,
                    MonitoringAlert.severity == AlertSeverity.CRITICAL,
                )
            )
        )
        critical_alerts = critical_alerts_result.scalar() or 0

        # Get recent events
        recent_events = await self.get_events(limit=10, since=since)

        # Get alert summary by severity
        alert_summary = {}
        for severity in AlertSeverity:
            count_result = await self.db.execute(
                select(func.count(MonitoringAlert.id)).where(
                    and_(
                        MonitoringAlert.severity == severity,
                        MonitoringAlert.created_at >= since,
                    )
                )
            )
            alert_summary[severity] = count_result.scalar() or 0

        # Get notification delivery stats
        notification_stats = {
            "total_sent": 0,
            "successful": 0,
            "failed": 0,
        }

        return MonitoringDashboardData(
            total_monitored_assets=total_monitored_assets,
            active_alerts=active_alerts,
            critical_alerts=critical_alerts,
            recent_events=recent_events,
            asset_health_summary={"healthy": 0, "warning": 0, "critical": 0},
            performance_trends={},
            alert_summary_by_severity=alert_summary,
            notification_delivery_stats=notification_stats,
        )

    async def get_health_status(self) -> Dict[str, str]:
        """Get monitoring system health status.

        Returns:
            Health status dictionary
        """
        health_status = {
            "overall": "healthy",
            "container_monitoring": "healthy",
            "schema_monitoring": "healthy",
            "performance_monitoring": "healthy",
            "alerting": "healthy",
            "notifications": "healthy",
        }

        try:
            # Check recent events
            recent_events = await self.get_events(limit=1, since=datetime.now(timezone.utc) - timedelta(hours=1))

            # Check active alerts
            active_alerts = await self.get_alerts(limit=1, status=AlertStatus.ACTIVE.value)

            # Set status based on findings
            if len(active_alerts) > 10:
                health_status["alerting"] = "warning"
                health_status["overall"] = "warning"

            # Include recent events count in health assessment
            if len(recent_events) == 0:
                health_status["event_monitoring"] = "inactive"

        except Exception as e:
            logger.error("Error checking health status: %s", e)
            health_status["overall"] = "unhealthy"

        return health_status

    async def get_alert_notifications(self, alert_id: str) -> List[NotificationLog]:
        """Get notifications for a specific alert.

        Args:
            alert_id: Alert UUID

        Returns:
            List of notification logs
        """
        result = await self.db.execute(
            select(NotificationLog)
            .where(NotificationLog.alert_id == alert_id)
            .order_by(desc(NotificationLog.attempted_at))
        )
        return result.scalars().all()

    async def get_asset_monitoring_status(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Get monitoring status for a specific asset.

        Args:
            asset_id: Asset UUID

        Returns:
            Asset monitoring status data
        """
        # Get recent events for this asset
        recent_events = await self.get_events(asset_id=asset_id, limit=10)

        # Get recent alerts for this asset
        recent_alerts = await self.get_alerts(asset_id=asset_id, limit=5)

        # Get recent metrics for this asset
        recent_metrics = await self.get_metrics(asset_id=asset_id, limit=100)

        return {
            "asset_id": asset_id,
            "monitoring_enabled": True,  # Would check actual status
            "last_event": recent_events[0] if recent_events else None,
            "active_alerts": [alert for alert in recent_alerts if alert.status == AlertStatus.ACTIVE],
            "recent_metrics_count": len(recent_metrics),
            "health_status": "healthy",  # Would calculate based on recent data
        }

    async def enable_asset_monitoring(self, asset_id: str, config: Dict[str, Any], enabled_by: str) -> bool:
        """Enable monitoring for a specific asset.

        Args:
            asset_id: Asset UUID
            config: Monitoring configuration
            enabled_by: User enabling monitoring

        Returns:
            True if successful
        """
        # Implementation would create monitoring configuration
        logger.info("Enabling monitoring for asset %s by %s", asset_id, enabled_by)
        return True

    async def disable_asset_monitoring(self, asset_id: str, reason: str, disabled_by: str) -> bool:
        """Disable monitoring for a specific asset.

        Args:
            asset_id: Asset UUID
            reason: Reason for disabling
            disabled_by: User disabling monitoring

        Returns:
            True if successful
        """
        # Implementation would disable monitoring configuration
        logger.info("Disabling monitoring for asset %s by %s: %s", asset_id, disabled_by, reason)
        return True

    async def get_monitoring_statistics(self, time_range_hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics.

        Args:
            time_range_hours: Time range for statistics

        Returns:
            Statistics dictionary
        """
        since = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)

        # Get event counts
        total_events_result = await self.db.execute(
            select(func.count(MonitoringEvent.id)).where(MonitoringEvent.detected_at >= since)
        )
        total_events = total_events_result.scalar() or 0

        # Get alert counts
        total_alerts_result = await self.db.execute(
            select(func.count(MonitoringAlert.id)).where(MonitoringAlert.created_at >= since)
        )
        total_alerts = total_alerts_result.scalar() or 0

        # Get metrics count
        total_metrics_result = await self.db.execute(
            select(func.count(PerformanceMetric.id)).where(PerformanceMetric.timestamp >= since)
        )
        total_metrics = total_metrics_result.scalar() or 0

        return {
            "time_range_hours": time_range_hours,
            "total_events": total_events,
            "total_alerts": total_alerts,
            "total_metrics": total_metrics,
            "events_per_hour": total_events / time_range_hours if time_range_hours > 0 else 0,
            "alerts_per_hour": total_alerts / time_range_hours if time_range_hours > 0 else 0,
            "metrics_per_hour": total_metrics / time_range_hours if time_range_hours > 0 else 0,
        }
