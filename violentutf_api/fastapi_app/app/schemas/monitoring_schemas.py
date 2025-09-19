# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Monitoring Pydantic Schemas for Issue #283.

This module contains Pydantic schemas for the continuous monitoring system,
providing request/response models and data validation.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from app.models.monitoring import (
    AlertSeverity,
    AlertStatus,
    MetricType,
    MonitoringEventType,
    NotificationChannel,
    SchemaChangeType,
)


class ContainerInfo(BaseModel):
    """Container information data structure."""

    id: str = Field(..., description="Container ID")
    name: str = Field(..., description="Container name")
    image: str = Field(..., description="Container image")
    status: str = Field(..., description="Container status")
    ports: Dict[str, Any] = Field(default_factory=dict, description="Exposed ports configuration")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    labels: Dict[str, str] = Field(default_factory=dict, description="Container labels")
    created: datetime = Field(..., description="Container creation timestamp")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class EndpointStatus(BaseModel):
    """Network endpoint status information."""

    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    host: str = Field(..., description="Endpoint host")
    port: int = Field(..., description="Endpoint port")
    accessible: bool = Field(..., description="Whether endpoint is accessible")
    ssl_status: Optional[Dict[str, Any]] = Field(None, description="SSL certificate status")
    service_banner: Optional[str] = Field(None, description="Service banner information")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    last_check: datetime = Field(..., description="Last check timestamp")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class SchemaSnapshot(BaseModel):
    """Database schema snapshot information."""

    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
    schema_info: Dict[str, Any] = Field(..., description="Schema structure information")
    schema_hash: str = Field(..., description="Schema hash for quick comparison")
    table_count: int = Field(..., description="Number of tables")
    index_count: int = Field(..., description="Number of indexes")
    constraint_count: int = Field(..., description="Number of constraints")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class SchemaChange(BaseModel):
    """Individual schema change information."""

    change_type: SchemaChangeType = Field(..., description="Type of schema change")
    object_name: str = Field(..., description="Name of changed object")
    object_type: str = Field(..., description="Type of object (TABLE, INDEX, etc.)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed change information")


class SchemaChangeEvent(BaseModel):
    """Schema change event information."""

    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    timestamp: datetime = Field(..., description="Change timestamp")
    previous_snapshot: SchemaSnapshot = Field(..., description="Previous schema snapshot")
    current_snapshot: SchemaSnapshot = Field(..., description="Current schema snapshot")
    changes: List[SchemaChange] = Field(..., description="List of detected changes")
    change_type: SchemaChangeType = Field(..., description="Primary change type")
    impact_assessment: Dict[str, Any] = Field(..., description="Impact assessment results")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class PerformanceMetricCreate(BaseModel):
    """Schema for creating performance metrics."""

    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    metric_type: MetricType = Field(..., description="Type of metric")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit")
    collection_method: str = Field(..., description="How the metric was collected")
    collection_interval_seconds: Optional[int] = Field(None, description="Collection interval")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    threshold_warning: Optional[float] = Field(None, description="Warning threshold")
    threshold_critical: Optional[float] = Field(None, description="Critical threshold")

    @validator("value")
    @classmethod
    def validate_value(cls: type, v: float) -> float:  # noqa: ANN102
        """Validate metric value is non-negative."""
        if v < 0:
            raise ValueError("Metric value must be non-negative")
        return v


class PerformanceMetricResponse(BaseModel):
    """Schema for performance metric responses."""

    id: uuid.UUID = Field(..., description="Metric UUID")
    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    metric_type: MetricType = Field(..., description="Type of metric")
    value: float = Field(..., description="Metric value")
    unit: str = Field(..., description="Metric unit")
    timestamp: datetime = Field(..., description="Metric timestamp")
    collection_method: str = Field(..., description="How the metric was collected")
    collection_interval_seconds: Optional[int] = Field(None, description="Collection interval")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    threshold_warning: Optional[float] = Field(None, description="Warning threshold")
    threshold_critical: Optional[float] = Field(None, description="Critical threshold")
    threshold_exceeded: bool = Field(..., description="Whether threshold was exceeded")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class MonitoringEventCreate(BaseModel):
    """Schema for creating monitoring events."""

    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    event_type: MonitoringEventType = Field(..., description="Type of monitoring event")
    title: str = Field(..., max_length=255, description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    source: str = Field(..., max_length=100, description="Event source")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event metadata")
    detection_latency_ms: Optional[int] = Field(None, description="Detection latency")
    confidence_score: int = Field(100, ge=1, le=100, description="Detection confidence score")


class MonitoringEventResponse(BaseModel):
    """Schema for monitoring event responses."""

    id: uuid.UUID = Field(..., description="Event UUID")
    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    event_type: MonitoringEventType = Field(..., description="Type of monitoring event")
    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    source: str = Field(..., description="Event source")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Event metadata")
    detected_at: datetime = Field(..., description="Detection timestamp")
    detection_latency_ms: Optional[int] = Field(None, description="Detection latency")
    confidence_score: int = Field(..., description="Detection confidence score")
    processed: bool = Field(..., description="Whether event has been processed")
    processed_at: Optional[datetime] = Field(None, description="Processing timestamp")
    processing_error: Optional[str] = Field(None, description="Processing error message")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class MonitoringAlertCreate(BaseModel):
    """Schema for creating monitoring alerts."""

    event_id: uuid.UUID = Field(..., description="Event UUID")
    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    title: str = Field(..., max_length=255, description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: AlertSeverity = Field(..., description="Alert severity")
    notification_channels: Optional[List[NotificationChannel]] = Field(None, description="Notification channels")
    escalation_rules: Optional[Dict[str, Any]] = Field(None, description="Escalation rules")
    correlation_key: Optional[str] = Field(None, description="Alert correlation key")
    auto_resolve_at: Optional[datetime] = Field(None, description="Auto-resolution timestamp")


class MonitoringAlertResponse(BaseModel):
    """Schema for monitoring alert responses."""

    id: uuid.UUID = Field(..., description="Alert UUID")
    event_id: uuid.UUID = Field(..., description="Event UUID")
    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    severity: AlertSeverity = Field(..., description="Alert severity")
    status: AlertStatus = Field(..., description="Alert status")
    created_at: datetime = Field(..., description="Creation timestamp")
    first_notification_at: Optional[datetime] = Field(None, description="First notification timestamp")
    last_notification_at: Optional[datetime] = Field(None, description="Last notification timestamp")
    escalation_level: int = Field(..., description="Current escalation level")
    auto_resolve_at: Optional[datetime] = Field(None, description="Auto-resolution timestamp")
    acknowledged_at: Optional[datetime] = Field(None, description="Acknowledgment timestamp")
    acknowledged_by: Optional[str] = Field(None, description="Acknowledged by user")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    resolved_by: Optional[str] = Field(None, description="Resolved by user")
    resolution_reason: Optional[str] = Field(None, description="Resolution reason")
    notification_channels: Optional[List[NotificationChannel]] = Field(None, description="Notification channels")
    escalation_rules: Optional[Dict[str, Any]] = Field(None, description="Escalation rules")
    correlation_key: Optional[str] = Field(None, description="Alert correlation key")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AlertAcknowledgment(BaseModel):
    """Schema for alert acknowledgment."""

    acknowledged_by: str = Field(..., max_length=100, description="User acknowledging the alert")
    acknowledgment_reason: Optional[str] = Field(None, description="Reason for acknowledgment")


class AlertResolution(BaseModel):
    """Schema for alert resolution."""

    resolved_by: str = Field(..., max_length=100, description="User resolving the alert")
    resolution_reason: str = Field(..., max_length=255, description="Reason for resolution")


class NotificationCreate(BaseModel):
    """Schema for creating notifications."""

    alert_id: uuid.UUID = Field(..., description="Alert UUID")
    channel: NotificationChannel = Field(..., description="Notification channel")
    recipient: str = Field(..., max_length=255, description="Notification recipient")
    subject: Optional[str] = Field(None, max_length=255, description="Notification subject")
    message: str = Field(..., description="Notification message")


class NotificationResponse(BaseModel):
    """Schema for notification responses."""

    id: uuid.UUID = Field(..., description="Notification UUID")
    alert_id: uuid.UUID = Field(..., description="Alert UUID")
    channel: NotificationChannel = Field(..., description="Notification channel")
    recipient: str = Field(..., description="Notification recipient")
    subject: Optional[str] = Field(None, description="Notification subject")
    message: str = Field(..., description="Notification message")
    attempted_at: datetime = Field(..., description="Attempt timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    delivery_status: str = Field(..., description="Delivery status")
    delivery_error: Optional[str] = Field(None, description="Delivery error message")
    retry_count: int = Field(..., description="Number of retry attempts")
    next_retry_at: Optional[datetime] = Field(None, description="Next retry timestamp")
    response_received: bool = Field(..., description="Whether response was received")
    response_time: Optional[datetime] = Field(None, description="Response timestamp")
    response_data: Optional[Dict[str, Any]] = Field(None, description="Response data")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ContainerMonitoringLogCreate(BaseModel):
    """Schema for creating container monitoring logs."""

    container_id: str = Field(..., max_length=64, description="Container ID")
    container_name: Optional[str] = Field(None, max_length=255, description="Container name")
    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    image_name: str = Field(..., max_length=255, description="Container image name")
    image_tag: Optional[str] = Field(None, max_length=100, description="Container image tag")
    container_status: str = Field(..., max_length=50, description="Container status")
    event_action: str = Field(..., max_length=50, description="Event action")
    exposed_ports: Optional[Dict[str, Any]] = Field(None, description="Exposed ports")
    network_settings: Optional[Dict[str, Any]] = Field(None, description="Network settings")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    container_labels: Optional[Dict[str, str]] = Field(None, description="Container labels")
    is_database_container: bool = Field(..., description="Whether container is a database")
    detection_confidence: int = Field(100, ge=1, le=100, description="Detection confidence")
    health_status: Optional[str] = Field(None, max_length=50, description="Health status")
    restart_count: int = Field(0, ge=0, description="Restart count")
    uptime_seconds: Optional[int] = Field(None, ge=0, description="Uptime in seconds")


class ContainerMonitoringLogResponse(BaseModel):
    """Schema for container monitoring log responses."""

    id: uuid.UUID = Field(..., description="Log UUID")
    container_id: str = Field(..., description="Container ID")
    container_name: Optional[str] = Field(None, description="Container name")
    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    image_name: str = Field(..., description="Container image name")
    image_tag: Optional[str] = Field(None, description="Container image tag")
    container_status: str = Field(..., description="Container status")
    event_action: str = Field(..., description="Event action")
    exposed_ports: Optional[Dict[str, Any]] = Field(None, description="Exposed ports")
    network_settings: Optional[Dict[str, Any]] = Field(None, description="Network settings")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    container_labels: Optional[Dict[str, str]] = Field(None, description="Container labels")
    detected_at: datetime = Field(..., description="Detection timestamp")
    is_database_container: bool = Field(..., description="Whether container is a database")
    detection_confidence: int = Field(..., description="Detection confidence")
    monitoring_enabled: bool = Field(..., description="Whether monitoring is enabled")
    health_status: Optional[str] = Field(None, description="Health status")
    last_health_check: Optional[datetime] = Field(None, description="Last health check timestamp")
    restart_count: int = Field(..., description="Restart count")
    uptime_seconds: Optional[int] = Field(None, description="Uptime in seconds")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class MonitoringConfigurationCreate(BaseModel):
    """Schema for creating monitoring configurations."""

    name: str = Field(..., max_length=255, description="Configuration name")
    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    configuration_type: str = Field(..., max_length=100, description="Configuration type")
    priority: int = Field(100, ge=1, le=1000, description="Configuration priority")
    monitoring_enabled: bool = Field(True, description="Whether monitoring is enabled")
    monitoring_interval_seconds: int = Field(300, ge=1, description="Monitoring interval")
    monitoring_rules: Optional[Dict[str, Any]] = Field(None, description="Monitoring rules")
    threshold_configurations: Optional[Dict[str, Any]] = Field(None, description="Threshold configurations")
    escalation_rules: Optional[Dict[str, Any]] = Field(None, description="Escalation rules")
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")
    monitoring_schedule: Optional[Dict[str, Any]] = Field(None, description="Monitoring schedule")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Application conditions")
    created_by: str = Field(..., max_length=100, description="Created by user")


class MonitoringConfigurationResponse(BaseModel):
    """Schema for monitoring configuration responses."""

    id: uuid.UUID = Field(..., description="Configuration UUID")
    name: str = Field(..., description="Configuration name")
    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    configuration_type: str = Field(..., description="Configuration type")
    is_active: bool = Field(..., description="Whether configuration is active")
    priority: int = Field(..., description="Configuration priority")
    monitoring_enabled: bool = Field(..., description="Whether monitoring is enabled")
    monitoring_interval_seconds: int = Field(..., description="Monitoring interval")
    monitoring_rules: Optional[Dict[str, Any]] = Field(None, description="Monitoring rules")
    threshold_configurations: Optional[Dict[str, Any]] = Field(None, description="Threshold configurations")
    escalation_rules: Optional[Dict[str, Any]] = Field(None, description="Escalation rules")
    notification_preferences: Optional[Dict[str, Any]] = Field(None, description="Notification preferences")
    monitoring_schedule: Optional[Dict[str, Any]] = Field(None, description="Monitoring schedule")
    conditions: Optional[Dict[str, Any]] = Field(None, description="Application conditions")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    created_by: str = Field(..., description="Created by user")
    updated_by: str = Field(..., description="Updated by user")

    class Config:
        """Pydantic configuration."""

        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class MonitoringDashboardData(BaseModel):
    """Schema for monitoring dashboard data."""

    total_monitored_assets: int = Field(..., description="Total number of monitored assets")
    active_alerts: int = Field(..., description="Number of active alerts")
    critical_alerts: int = Field(..., description="Number of critical alerts")
    recent_events: List[MonitoringEventResponse] = Field(..., description="Recent monitoring events")
    asset_health_summary: Dict[str, int] = Field(..., description="Asset health summary")
    performance_trends: Dict[str, List[float]] = Field(..., description="Performance trend data")
    alert_summary_by_severity: Dict[AlertSeverity, int] = Field(..., description="Alert summary by severity")
    notification_delivery_stats: Dict[str, int] = Field(..., description="Notification delivery statistics")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class TrendAnalysisRequest(BaseModel):
    """Schema for trend analysis requests."""

    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    metric_types: List[MetricType] = Field(..., description="Metric types to analyze")
    time_range_hours: int = Field(24, ge=1, le=8760, description="Time range in hours")  # Max 1 year
    aggregation_interval_minutes: int = Field(60, ge=1, le=1440, description="Aggregation interval")  # Max 1 day
    include_predictions: bool = Field(False, description="Whether to include trend predictions")


class TrendAnalysisResponse(BaseModel):
    """Schema for trend analysis responses."""

    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID")
    metric_type: MetricType = Field(..., description="Metric type")
    time_range_start: datetime = Field(..., description="Analysis start time")
    time_range_end: datetime = Field(..., description="Analysis end time")
    data_points: List[Dict[str, Any]] = Field(..., description="Trend data points")
    trend_direction: str = Field(..., description="Trend direction (UP, DOWN, STABLE)")
    anomalies_detected: List[Dict[str, Any]] = Field(..., description="Detected anomalies")
    predictions: Optional[List[Dict[str, Any]]] = Field(None, description="Trend predictions")
    statistics: Dict[str, float] = Field(..., description="Statistical summary")

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
