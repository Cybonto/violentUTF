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

from sqlalchemy import and_, desc, func, or_, select
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

    # Database Monitoring Methods for Issue #270

    async def store_database_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Store database performance metrics.

        Args:
            metrics_data: Dictionary containing database metrics including:
                - db_type: Database type (postgresql, sqlite)
                - db_id: Database identifier
                - timestamp: Measurement timestamp
                - metrics: Dictionary of metric_name -> value

        Returns:
            True if metrics stored successfully
        """
        try:
            db_type = metrics_data.get("db_type")
            db_id = metrics_data.get("db_id")
            timestamp = metrics_data.get("timestamp", datetime.now(timezone.utc))
            metrics = metrics_data.get("metrics", {})

            # Store each metric as a PerformanceMetric record
            for metric_name, metric_value in metrics.items():
                metric = PerformanceMetric(
                    asset_id=db_id,
                    metric_type=f"db_{db_type}_{metric_name}",
                    metric_value=float(metric_value),
                    timestamp=timestamp,
                    metadata={"db_type": db_type, "db_id": db_id, "original_metric": metric_name},
                )
                self.db.add(metric)

            await self.db.commit()
            return True

        except Exception as e:
            logger.error("Error storing database metrics: %s", e)
            await self.db.rollback()
            return False

    async def store_database_metrics_batch(self, batch_data: List[Dict[str, Any]]) -> int:
        """Store a batch of database metrics.

        Args:
            batch_data: List of metrics_data dictionaries

        Returns:
            Number of metrics successfully stored
        """
        stored_count = 0

        for metrics_data in batch_data:
            if await self.store_database_metrics(metrics_data):
                stored_count += 1

        return stored_count

    async def get_database_metrics(
        self,
        db_type: str,
        hours_back: int = 24,
        metric_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get database metrics for a specific database type.

        Args:
            db_type: Database type (postgresql, sqlite)
            hours_back: Hours of historical data to retrieve
            metric_types: Optional list of specific metric types to retrieve

        Returns:
            List of metrics dictionaries
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        query = (
            select(PerformanceMetric)
            .where(
                and_(
                    PerformanceMetric.timestamp >= since,
                    PerformanceMetric.metric_type.like(f"db_{db_type}_%"),
                )
            )
            .order_by(desc(PerformanceMetric.timestamp))
        )

        # Filter by specific metric types if provided
        if metric_types:
            metric_filters = [PerformanceMetric.metric_type == f"db_{db_type}_{mt}" for mt in metric_types]
            query = query.where(or_(*metric_filters))

        result = await self.db.execute(query)
        metrics = result.scalars().all()

        # Format results
        formatted_metrics = []
        for metric in metrics:
            formatted_metrics.append(
                {
                    "timestamp": metric.timestamp,
                    "metric_type": metric.metadata.get("original_metric", metric.metric_type),
                    "value": metric.metric_value,
                    "unit": self._get_metric_unit(metric.metadata.get("original_metric", "")),
                }
            )

        return formatted_metrics

    def _get_metric_unit(self, metric_type: str) -> str:
        """Get the unit for a metric type.

        Args:
            metric_type: Metric type name

        Returns:
            Unit string
        """
        unit_map = {
            "connection_pool_usage": "percent",
            "avg_query_latency_ms": "milliseconds",
            "database_size_mb": "megabytes",
            "cache_hit_ratio": "ratio",
            "transaction_rate": "transactions/second",
            "wal_size_mb": "megabytes",
            "avg_query_time_ms": "milliseconds",
        }
        return unit_map.get(metric_type, "value")

    async def store_baseline(self, baseline_data: Dict[str, Any]) -> Optional[str]:
        """Store a calculated performance baseline.

        Args:
            baseline_data: Dictionary containing baseline information:
                - baseline_id: Unique identifier (optional, generated if not provided)
                - db_type: Database type
                - metric_type: Metric type
                - baseline_value: Calculated baseline value
                - std_deviation: Standard deviation
                - min_value: Minimum observed value
                - max_value: Maximum observed value
                - sample_size: Number of samples used
                - calculation_window_hours: Time window for calculation
                - valid_until: Baseline validity timestamp

        Returns:
            Baseline ID if stored successfully, None otherwise
        """
        try:
            import uuid

            baseline_id = baseline_data.get("baseline_id") or str(uuid.uuid4())

            # Store as metadata in a PerformanceMetric with special marker
            baseline_metric = PerformanceMetric(
                asset_id=f"baseline_{baseline_data['db_type']}",
                metric_type=f"baseline_{baseline_data['db_type']}_{baseline_data['metric_type']}",
                metric_value=baseline_data["baseline_value"],
                timestamp=datetime.now(timezone.utc),
                metadata={
                    "baseline_id": baseline_id,
                    "db_type": baseline_data["db_type"],
                    "metric_type": baseline_data["metric_type"],
                    "std_deviation": baseline_data.get("std_deviation"),
                    "min_value": baseline_data.get("min_value"),
                    "max_value": baseline_data.get("max_value"),
                    "sample_size": baseline_data.get("sample_size"),
                    "calculation_window_hours": baseline_data.get("calculation_window_hours"),
                    "valid_until": (
                        baseline_data.get("valid_until", "").isoformat() if baseline_data.get("valid_until") else None
                    ),
                    "is_baseline": True,
                },
            )

            self.db.add(baseline_metric)
            await self.db.commit()

            return baseline_id

        except Exception as e:
            logger.error("Error storing baseline: %s", e)
            await self.db.rollback()
            return None

    async def get_database_baselines(
        self,
        db_type: Optional[str] = None,
        metric_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get performance baselines for database metrics.

        Args:
            db_type: Optional filter by database type
            metric_types: Optional list of metric types to filter

        Returns:
            List of baseline dictionaries
        """
        query = (
            select(PerformanceMetric)
            .where(PerformanceMetric.asset_id.like("baseline_%"))
            .order_by(desc(PerformanceMetric.timestamp))
        )

        if db_type:
            query = query.where(PerformanceMetric.asset_id == f"baseline_{db_type}")

        result = await self.db.execute(query)
        baselines = result.scalars().all()

        # Format and filter results
        formatted_baselines = []
        for baseline in baselines:
            metadata = baseline.metadata
            if not metadata.get("is_baseline"):
                continue

            metric_type = metadata.get("metric_type")
            if metric_types and metric_type not in metric_types:
                continue

            # Check if baseline is still valid
            valid_until_str = metadata.get("valid_until")
            if valid_until_str:
                valid_until = datetime.fromisoformat(valid_until_str)
                if valid_until < datetime.now(timezone.utc):
                    continue  # Skip expired baselines

            formatted_baselines.append(
                {
                    "db_type": metadata.get("db_type"),
                    "metric_type": metric_type,
                    "baseline_value": baseline.metric_value,
                    "std_deviation": metadata.get("std_deviation"),
                    "normal_range": {
                        "min": metadata.get("min_value"),
                        "max": metadata.get("max_value"),
                    },
                    "sample_size": metadata.get("sample_size"),
                    "calculation_window_hours": metadata.get("calculation_window_hours"),
                    "valid_until": valid_until if valid_until_str else None,
                }
            )

        return formatted_baselines

    async def update_baseline(
        self,
        db_type: str,
        metric_type: str,
        baseline_data: Dict[str, Any],
    ) -> bool:
        """Update an existing baseline.

        Args:
            db_type: Database type
            metric_type: Metric type
            baseline_data: New baseline data

        Returns:
            True if updated successfully
        """
        # Store new baseline (which effectively updates by being the latest)
        full_baseline_data = {
            "db_type": db_type,
            "metric_type": metric_type,
            **baseline_data,
        }

        baseline_id = await self.store_baseline(full_baseline_data)
        return baseline_id is not None

    async def recalculate_baselines(
        self,
        db_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Trigger baseline recalculation.

        Args:
            db_type: Optional specific database type to recalculate

        Returns:
            Job information dictionary
        """
        import uuid

        job_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        # Check if a recalculation is already running (simple check)
        # In a full implementation, this would check a job queue
        return {
            "job_id": job_id,
            "status": "queued",
            "message": "Baseline recalculation job queued" + (f" for {db_type}" if db_type else ""),
            "started_at": started_at,
        }

    async def aggregate_metrics(
        self,
        db_type: str,
        hours_back: int = 24,
        interval: str = "hourly",
    ) -> List[Dict[str, Any]]:
        """Aggregate metrics over time intervals.

        Args:
            db_type: Database type
            hours_back: Hours of data to aggregate
            interval: Aggregation interval (hourly, daily)

        Returns:
            List of aggregated metrics
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        # Simplified aggregation - group by metric type and time bucket
        # In production, this would use proper SQL window functions
        query = (
            select(PerformanceMetric)
            .where(
                and_(
                    PerformanceMetric.timestamp >= since,
                    PerformanceMetric.metric_type.like(f"db_{db_type}_%"),
                )
            )
            .order_by(PerformanceMetric.timestamp)
        )

        result = await self.db.execute(query)
        metrics = result.scalars().all()

        # Group and aggregate
        aggregated = {}
        for metric in metrics:
            # Determine time bucket
            ts = metric.timestamp
            if interval == "hourly":
                bucket = ts.replace(minute=0, second=0, microsecond=0)
            else:  # daily
                bucket = ts.replace(hour=0, minute=0, second=0, microsecond=0)

            key = (bucket, metric.metadata.get("original_metric", metric.metric_type))

            if key not in aggregated:
                aggregated[key] = {
                    "values": [],
                    "timestamp": bucket,
                    "metric_type": metric.metadata.get("original_metric", metric.metric_type),
                }

            aggregated[key]["values"].append(metric.metric_value)

        # Calculate statistics
        result_list = []
        for key, data in aggregated.items():
            values = data["values"]
            result_list.append(
                {
                    interval[:-2]: data["timestamp"],  # "hour" or "day"
                    "metric_type": data["metric_type"],
                    "avg_value": sum(values) / len(values),
                    "min_value": min(values),
                    "max_value": max(values),
                    "sample_count": len(values),
                }
            )

        return result_list
