# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Monitoring Database Models for Issue #283.

This module contains the database models for the continuous monitoring system,
including container monitoring, schema change tracking, performance metrics,
and alerting functionality.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class MonitoringEventType(str, Enum):
    """Monitoring event type enumeration."""

    CONTAINER_START = "CONTAINER_START"
    CONTAINER_STOP = "CONTAINER_STOP"
    CONTAINER_RESTART = "CONTAINER_RESTART"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"
    FILE_MODIFIED = "FILE_MODIFIED"
    PERFORMANCE_THRESHOLD = "PERFORMANCE_THRESHOLD"
    CONNECTIVITY_LOST = "CONNECTIVITY_LOST"
    CONNECTIVITY_RESTORED = "CONNECTIVITY_RESTORED"
    SSL_CERTIFICATE_EXPIRING = "SSL_CERTIFICATE_EXPIRING"
    DATABASE_SIZE_GROWTH = "DATABASE_SIZE_GROWTH"


class AlertSeverity(str, Enum):
    """Alert severity enumeration."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    """Alert status enumeration."""

    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    SUPPRESSED = "SUPPRESSED"


class NotificationChannel(str, Enum):
    """Notification channel enumeration."""

    SLACK_MONITORING = "SLACK_MONITORING"
    SLACK_CRITICAL = "SLACK_CRITICAL"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"
    SMS = "SMS"


class SchemaChangeType(str, Enum):
    """Schema change type enumeration."""

    TABLE_ADDED = "TABLE_ADDED"
    TABLE_DROPPED = "TABLE_DROPPED"
    TABLE_MODIFIED = "TABLE_MODIFIED"
    COLUMN_ADDED = "COLUMN_ADDED"
    COLUMN_DROPPED = "COLUMN_DROPPED"
    COLUMN_MODIFIED = "COLUMN_MODIFIED"
    INDEX_ADDED = "INDEX_ADDED"
    INDEX_DROPPED = "INDEX_DROPPED"
    CONSTRAINT_ADDED = "CONSTRAINT_ADDED"
    CONSTRAINT_DROPPED = "CONSTRAINT_DROPPED"
    PROCEDURE_ADDED = "PROCEDURE_ADDED"
    PROCEDURE_MODIFIED = "PROCEDURE_MODIFIED"
    PROCEDURE_DROPPED = "PROCEDURE_DROPPED"


class RiskLevel(str, Enum):
    """Risk level enumeration."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MetricType(str, Enum):
    """Performance metric type enumeration."""

    CONNECTION_COUNT = "CONNECTION_COUNT"
    QUERY_RESPONSE_TIME = "QUERY_RESPONSE_TIME"
    CPU_USAGE = "CPU_USAGE"
    MEMORY_USAGE = "MEMORY_USAGE"
    DISK_IO = "DISK_IO"
    DATABASE_SIZE = "DATABASE_SIZE"
    LOCK_WAITS = "LOCK_WAITS"
    DEADLOCKS = "DEADLOCKS"
    CACHE_HIT_RATIO = "CACHE_HIT_RATIO"
    NETWORK_LATENCY = "NETWORK_LATENCY"


class MonitoringEvent(Base):
    """Database model for monitoring events.

    This model stores all monitoring events detected by the continuous
    monitoring system, providing a comprehensive audit trail.
    """

    __tablename__ = "monitoring_events"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=True, index=True)
    event_type = Column(SQLEnum(MonitoringEventType), nullable=False, index=True)

    # Event details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)  # container-monitor, schema-monitor, etc.
    event_metadata = Column(JSON, nullable=True)

    # Detection details
    detected_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    detection_latency_ms = Column(Integer, nullable=True)  # Time from occurrence to detection
    confidence_score = Column(Integer, nullable=False, default=100)  # 1-100

    # Processing status
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    processing_error = Column(Text, nullable=True)

    # Relationships
    asset = relationship("DatabaseAsset", backref="monitoring_events")
    alerts = relationship("MonitoringAlert", back_populates="event", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """Return string representation of the monitoring event."""
        return f"<MonitoringEvent(id={self.id}, type='{self.event_type}', title='{self.title}')>"


class SchemaChangeEvent(Base):
    """Database model for schema change events.

    This model stores detailed information about database schema changes
    detected by the schema monitoring system.
    """

    __tablename__ = "schema_change_events"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)
    monitoring_event_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_events.id"), nullable=True, index=True)

    # Change details
    change_type = Column(SQLEnum(SchemaChangeType), nullable=False, index=True)
    object_name = Column(String(255), nullable=False)
    object_type = Column(String(50), nullable=False)  # TABLE, INDEX, CONSTRAINT, etc.
    schema_name = Column(String(100), nullable=True)

    # Change content
    previous_definition = Column(Text, nullable=True)
    current_definition = Column(Text, nullable=True)
    change_details = Column(JSON, nullable=True)

    # Impact assessment
    impact_assessment = Column(JSON, nullable=True)
    risk_level = Column(SQLEnum(RiskLevel), nullable=False, default=RiskLevel.MEDIUM)
    breaking_change = Column(Boolean, default=False, index=True)

    # Detection metadata
    detected_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    detection_method = Column(String(100), nullable=False)  # event-trigger, file-monitor, periodic-scan
    schema_hash_before = Column(String(64), nullable=True)
    schema_hash_after = Column(String(64), nullable=True)

    # Validation status
    validated = Column(Boolean, default=False, index=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    validation_errors = Column(JSON, nullable=True)

    # Relationships
    asset = relationship("DatabaseAsset", backref="schema_changes")
    monitoring_event = relationship("MonitoringEvent", backref="schema_change")

    def __repr__(self) -> str:
        """Return string representation of the schema change event."""
        return f"<SchemaChangeEvent(id={self.id}, type='{self.change_type}', object='{self.object_name}')>"


class PerformanceMetric(Base):
    """Database model for performance metrics.

    This model stores performance metrics collected from monitored
    database assets for trend analysis and alerting.
    """

    __tablename__ = "performance_metrics"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)
    metric_type = Column(SQLEnum(MetricType), nullable=False, index=True)

    # Metric data
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)  # ms, MB, %, count, etc.
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    # Collection metadata
    collection_method = Column(String(100), nullable=False)
    collection_interval_seconds = Column(Integer, nullable=True)
    metric_metadata = Column(JSON, nullable=True)

    # Threshold information
    threshold_warning = Column(Float, nullable=True)
    threshold_critical = Column(Float, nullable=True)
    threshold_exceeded = Column(Boolean, default=False, index=True)

    # Relationships
    asset = relationship("DatabaseAsset", backref="performance_metrics")

    def __repr__(self) -> str:
        """Return string representation of the performance metric."""
        return f"<PerformanceMetric(id={self.id}, type='{self.metric_type}', value={self.value})>"


class MonitoringAlert(Base):
    """Database model for monitoring alerts.

    This model stores alerts generated by the monitoring system
    with escalation and notification tracking.
    """

    __tablename__ = "monitoring_alerts"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_events.id"), nullable=False, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=True, index=True)

    # Alert details
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True)
    status = Column(SQLEnum(AlertStatus), nullable=False, default=AlertStatus.ACTIVE, index=True)

    # Timing and escalation
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    first_notification_at = Column(DateTime(timezone=True), nullable=True)
    last_notification_at = Column(DateTime(timezone=True), nullable=True)
    escalation_level = Column(Integer, default=0, index=True)
    auto_resolve_at = Column(DateTime(timezone=True), nullable=True)

    # Status tracking
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(100), nullable=True)
    resolution_reason = Column(String(255), nullable=True)

    # Alert configuration
    notification_channels = Column(JSON, nullable=True)  # List of channels to notify
    escalation_rules = Column(JSON, nullable=True)
    correlation_key = Column(String(255), nullable=True, index=True)  # For alert deduplication

    # Relationships
    event = relationship("MonitoringEvent", back_populates="alerts")
    asset = relationship("DatabaseAsset", backref="monitoring_alerts")
    notifications = relationship("NotificationLog", back_populates="alert", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """Return string representation of the monitoring alert."""
        return f"<MonitoringAlert(id={self.id}, severity='{self.severity}', status='{self.status}')>"


class NotificationLog(Base):
    """Database model for notification delivery tracking.

    This model tracks all notification attempts and their delivery status
    for monitoring alerts.
    """

    __tablename__ = "notification_logs"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_alerts.id"), nullable=False, index=True)

    # Notification details
    channel = Column(SQLEnum(NotificationChannel), nullable=False, index=True)
    recipient = Column(String(255), nullable=False)  # email, slack channel, webhook URL
    subject = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)

    # Delivery tracking
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    delivery_status = Column(String(50), nullable=False, default="PENDING")  # PENDING, SENT, DELIVERED, FAILED
    delivery_error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Response tracking
    response_received = Column(Boolean, default=False)
    response_time = Column(DateTime(timezone=True), nullable=True)
    response_data = Column(JSON, nullable=True)

    # Relationships
    alert = relationship("MonitoringAlert", back_populates="notifications")

    def __repr__(self) -> str:
        """Return string representation of the notification log."""
        return f"<NotificationLog(id={self.id}, channel='{self.channel}', status='{self.delivery_status}')>"


class ContainerMonitoringLog(Base):
    """Database model for container monitoring events.

    This model stores container lifecycle events and monitoring
    data specific to Docker container management.
    """

    __tablename__ = "container_monitoring_logs"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    container_id = Column(String(64), nullable=False, index=True)
    container_name = Column(String(255), nullable=True, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=True, index=True)

    # Container details
    image_name = Column(String(255), nullable=False)
    image_tag = Column(String(100), nullable=True)
    container_status = Column(String(50), nullable=False)  # running, stopped, restarting, etc.
    event_action = Column(String(50), nullable=False)  # start, stop, restart, create, destroy

    # Network configuration
    exposed_ports = Column(JSON, nullable=True)
    network_settings = Column(JSON, nullable=True)
    environment_variables = Column(JSON, nullable=True)
    container_labels = Column(JSON, nullable=True)

    # Monitoring metadata
    detected_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    is_database_container = Column(Boolean, nullable=False, index=True)
    detection_confidence = Column(Integer, nullable=False, default=100)  # 1-100
    monitoring_enabled = Column(Boolean, default=True, index=True)

    # Health status
    health_status = Column(String(50), nullable=True)  # healthy, unhealthy, starting
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    restart_count = Column(Integer, default=0)
    uptime_seconds = Column(Integer, nullable=True)

    # Relationships
    asset = relationship("DatabaseAsset", backref="container_logs")

    def __repr__(self) -> str:
        """Return string representation of the container monitoring log."""
        return (
            f"<ContainerMonitoringLog(id={self.id}, container='{self.container_name}', "
            f"action='{self.event_action}')>"
        )


class MonitoringConfiguration(Base):
    """Database model for monitoring configuration.

    This model stores configuration settings for the monitoring system,
    including thresholds, notification preferences, and monitoring rules.
    """

    __tablename__ = "monitoring_configurations"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=True, index=True)

    # Configuration scope
    configuration_type = Column(String(100), nullable=False, index=True)  # global, asset-specific, group
    is_active = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=100)  # Higher priority configurations override lower ones

    # Monitoring settings
    monitoring_enabled = Column(Boolean, default=True)
    monitoring_interval_seconds = Column(Integer, default=300)  # 5 minutes default
    monitoring_rules = Column(JSON, nullable=True)

    # Alert thresholds
    threshold_configurations = Column(JSON, nullable=True)
    escalation_rules = Column(JSON, nullable=True)
    notification_preferences = Column(JSON, nullable=True)

    # Schedule and conditions
    monitoring_schedule = Column(JSON, nullable=True)  # When monitoring is active
    conditions = Column(JSON, nullable=True)  # Conditions for applying this configuration

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=False)
    updated_by = Column(String(100), nullable=False)

    # Relationships
    asset = relationship("DatabaseAsset", backref="monitoring_configurations")

    def __repr__(self) -> str:
        """Return string representation of the monitoring configuration."""
        return f"<MonitoringConfiguration(id={self.id}, name='{self.name}', type='{self.configuration_type}')>"
