# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Risk Assessment Database Models

This module defines SQLAlchemy models for the comprehensive risk assessment automation framework.
Models support NIST RMF-compliant risk scoring, vulnerability assessment, security control evaluation,
and compliance risk management.

Models include:
- DatabaseAsset: Core database asset information
- RiskAssessment: NIST RMF risk assessment results
- VulnerabilityAssessment: Vulnerability scan results and CVE data
- SecurityControlAssessment: NIST SP 800-53 control evaluation
- RiskAlert: Risk alerting and notification management
- ComplianceAssessment: Multi-framework compliance evaluation
"""

import uuid
from enum import Enum

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class AssetType(str, Enum):
    """Database asset types supported by the risk assessment framework"""

    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class SecurityClassification(str, Enum):
    """Data security classification levels"""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class CriticalityLevel(str, Enum):
    """Asset criticality levels for impact assessment"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    """Risk level categories based on NIST RMF scoring"""

    LOW = "low"  # 1-5
    MEDIUM = "medium"  # 6-10
    HIGH = "high"  # 11-15
    VERY_HIGH = "very_high"  # 16-20
    CRITICAL = "critical"  # 21-25


class VulnerabilitySeverity(str, Enum):
    """Vulnerability severity levels based on CVSS scoring"""

    NONE = "none"  # 0.0
    LOW = "low"  # 0.1-3.9
    MEDIUM = "medium"  # 4.0-6.9
    HIGH = "high"  # 7.0-8.9
    CRITICAL = "critical"  # 9.0-10.0


class AlertLevel(str, Enum):
    """Risk alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class DatabaseAsset(Base):
    """
    Database asset model for risk assessment targets

    Represents database assets that undergo risk assessment including
    metadata, configuration, and security classification information.
    """

    __tablename__ = "database_assets"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)

    # Asset technical details
    asset_type = Column(String(50), nullable=False, index=True)
    database_version = Column(String(50))
    location = Column(String(255))  # Geographic location or environment
    file_path = Column(String(1024))  # For file-based databases
    connection_string = Column(String(1024))  # For network databases (encrypted)

    # Security and risk classification
    security_classification = Column(String(50), nullable=False, default="internal")
    criticality_level = Column(String(50), nullable=False, default="medium")
    access_restricted = Column(Boolean, default=False)
    encryption_enabled = Column(Boolean, default=False)

    # Organizational information
    technical_contact = Column(String(255))
    business_owner = Column(String(255))
    department = Column(String(255))
    environment = Column(String(50))  # dev, staging, prod

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_assessed = Column(DateTime(timezone=True))

    # Relationships
    risk_assessments = relationship("RiskAssessment", back_populates="asset", cascade="all, delete-orphan")
    vulnerability_assessments = relationship(
        "VulnerabilityAssessment", back_populates="asset", cascade="all, delete-orphan"
    )
    control_assessments = relationship(
        "SecurityControlAssessment", back_populates="asset", cascade="all, delete-orphan"
    )
    compliance_assessments = relationship("ComplianceAssessment", back_populates="asset", cascade="all, delete-orphan")
    risk_alerts = relationship("RiskAlert", back_populates="asset", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('postgresql', 'sqlite', 'duckdb', 'mysql', 'mongodb')", name="check_asset_type"
        ),
        CheckConstraint(
            "security_classification IN ('public', 'internal', 'confidential', 'restricted')",
            name="check_security_classification",
        ),
        CheckConstraint("criticality_level IN ('low', 'medium', 'high', 'critical')", name="check_criticality_level"),
        Index("idx_asset_type_classification", "asset_type", "security_classification"),
        Index("idx_criticality_location", "criticality_level", "location"),
    )


class RiskAssessment(Base):
    """
    NIST RMF-compliant risk assessment results

    Stores comprehensive risk assessment results including NIST RMF 6-step process
    outcomes, risk scoring (1-25 scale), and assessment metadata.
    """

    __tablename__ = "risk_assessments"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)

    # NIST RMF risk scoring (1-25 scale)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(50), nullable=False)

    # Risk factor components
    likelihood_score = Column(Float, nullable=False)  # 1-5 scale
    impact_score = Column(Float, nullable=False)  # 1-5 scale
    exposure_factor = Column(Float, nullable=False)  # 0.1-1.0 scale
    confidence_score = Column(Float, nullable=False)  # 0.0-1.0 confidence level

    # NIST RMF process results
    system_categorization = Column(JSONB)  # Step 1: Categorization results
    selected_controls = Column(JSONB)  # Step 2: Selected security controls
    control_implementation = Column(JSONB)  # Step 3: Control implementation status
    control_assessment = Column(JSONB)  # Step 4: Control assessment results
    authorization_decision = Column(JSONB)  # Step 5: Authorization decision data
    monitoring_plan = Column(JSONB)  # Step 6: Continuous monitoring plan

    # Assessment metadata
    assessment_method = Column(String(100), default="automated")
    assessment_duration_seconds = Column(Integer)
    assessor_id = Column(String(255))
    assessment_scope = Column(JSONB)

    # Temporal information
    assessment_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    next_assessment_due = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    asset = relationship("DatabaseAsset", back_populates="risk_assessments")
    risk_alerts = relationship("RiskAlert", back_populates="risk_assessment")

    # Constraints
    __table_args__ = (
        CheckConstraint("risk_score >= 1.0 AND risk_score <= 25.0", name="check_risk_score_range"),
        CheckConstraint("risk_level IN ('low', 'medium', 'high', 'very_high', 'critical')", name="check_risk_level"),
        CheckConstraint("likelihood_score >= 1.0 AND likelihood_score <= 5.0", name="check_likelihood_range"),
        CheckConstraint("impact_score >= 1.0 AND impact_score <= 5.0", name="check_impact_range"),
        CheckConstraint("exposure_factor >= 0.10 AND exposure_factor <= 1.00", name="check_exposure_range"),
        CheckConstraint("confidence_score >= 0.00 AND confidence_score <= 1.00", name="check_confidence_range"),
        Index("idx_risk_score_level", "risk_score", "risk_level"),
        Index("idx_assessment_date_asset", "assessment_date", "asset_id"),
        Index("idx_next_assessment_due", "next_assessment_due"),
    )


class VulnerabilityAssessment(Base):
    """
    Vulnerability assessment results with NIST NVD integration

    Stores vulnerability scan results, CVE data, CVSS scores, and remediation
    recommendations from NIST National Vulnerability Database integration.
    """

    __tablename__ = "vulnerability_assessments"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)

    # Vulnerability statistics
    total_vulnerabilities = Column(Integer, default=0)
    critical_vulnerabilities = Column(Integer, default=0)
    high_vulnerabilities = Column(Integer, default=0)
    medium_vulnerabilities = Column(Integer, default=0)
    low_vulnerabilities = Column(Integer, default=0)

    # Vulnerability scoring
    vulnerability_score = Column(Float, nullable=False)  # 1-5 scale

    # Assessment metadata
    scan_method = Column(String(100), default="nist_nvd")
    scan_duration_seconds = Column(Integer)
    cpe_identifiers = Column(ARRAY(String))  # CPE identifiers used in scan

    # Vulnerability details (stored as JSONB for flexibility)
    vulnerabilities_data = Column(JSONB)  # Detailed vulnerability information
    remediation_recommendations = Column(JSONB)  # Prioritized recommendations

    # Temporal information
    assessment_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    next_scan_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("DatabaseAsset", back_populates="vulnerability_assessments")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "vulnerability_score >= 1.0 AND vulnerability_score <= 5.0", name="check_vulnerability_score_range"
        ),
        CheckConstraint("total_vulnerabilities >= 0", name="check_total_vulnerabilities_positive"),
        CheckConstraint("critical_vulnerabilities >= 0", name="check_critical_vulnerabilities_positive"),
        CheckConstraint("high_vulnerabilities >= 0", name="check_high_vulnerabilities_positive"),
        CheckConstraint("medium_vulnerabilities >= 0", name="check_medium_vulnerabilities_positive"),
        CheckConstraint("low_vulnerabilities >= 0", name="check_low_vulnerabilities_positive"),
        Index("idx_vulnerability_score_date", "vulnerability_score", "assessment_date"),
        Index("idx_next_scan_date", "next_scan_date"),
    )


class SecurityControlAssessment(Base):
    """
    NIST SP 800-53 security control assessment results

    Stores security control implementation and effectiveness assessment results
    based on NIST SP 800-53 control catalog.
    """

    __tablename__ = "security_control_assessments"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)

    # Control assessment statistics
    total_controls_assessed = Column(Integer, default=0)
    implemented_controls = Column(Integer, default=0)
    partially_implemented_controls = Column(Integer, default=0)
    not_implemented_controls = Column(Integer, default=0)

    # Overall effectiveness scoring
    overall_effectiveness = Column(Float, nullable=False)  # 0.0-1.0 scale
    gaps_identified = Column(Integer, default=0)

    # Control family assessments (NIST SP 800-53 families)
    access_control_score = Column(Float)  # AC family
    audit_accountability_score = Column(Float)  # AU family
    security_assessment_score = Column(Float)  # CA family
    configuration_management_score = Column(Float)  # CM family
    contingency_planning_score = Column(Float)  # CP family
    identification_auth_score = Column(Float)  # IA family
    system_protection_score = Column(Float)  # SC family

    # Detailed control results (stored as JSONB)
    control_results = Column(JSONB)  # Individual control assessment results
    gap_analysis = Column(JSONB)  # Detailed gap analysis
    improvement_recommendations = Column(JSONB)  # Control improvement recommendations

    # Assessment metadata
    assessment_method = Column(String(100), default="automated")
    assessor_id = Column(String(255))
    assessment_scope = Column(JSONB)

    # Temporal information
    assessment_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    next_assessment_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("DatabaseAsset", back_populates="control_assessments")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "overall_effectiveness >= 0.0 AND overall_effectiveness <= 1.0", name="check_effectiveness_range"
        ),
        CheckConstraint("total_controls_assessed >= 0", name="check_total_controls_positive"),
        CheckConstraint("implemented_controls >= 0", name="check_implemented_controls_positive"),
        CheckConstraint("gaps_identified >= 0", name="check_gaps_positive"),
        Index("idx_effectiveness_date", "overall_effectiveness", "assessment_date"),
        Index("idx_next_assessment_date", "next_assessment_date"),
    )


class ComplianceAssessment(Base):
    """
    Multi-framework compliance assessment results

    Stores compliance assessment results for multiple regulatory frameworks
    including GDPR, SOC 2, NIST Cybersecurity Framework, and others.
    """

    __tablename__ = "compliance_assessments"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)

    # Framework-specific compliance scores (0.0-1.0 scale)
    gdpr_compliance_score = Column(Float)
    soc2_compliance_score = Column(Float)
    nist_csf_compliance_score = Column(Float)
    iso27001_compliance_score = Column(Float)
    pci_dss_compliance_score = Column(Float)

    # Overall compliance metrics
    overall_compliance_score = Column(Float, nullable=False)  # 0.0-1.0 scale
    compliance_accuracy = Column(Float, nullable=False)  # Assessment accuracy

    # Compliance gap analysis
    total_requirements_assessed = Column(Integer, default=0)
    compliant_requirements = Column(Integer, default=0)
    non_compliant_requirements = Column(Integer, default=0)
    partially_compliant_requirements = Column(Integer, default=0)

    # Detailed compliance data (stored as JSONB)
    framework_assessments = Column(JSONB)  # Per-framework detailed results
    gap_analysis = Column(JSONB)  # Compliance gaps and remediation
    regulatory_recommendations = Column(JSONB)  # Regulatory compliance recommendations

    # Assessment metadata
    frameworks_assessed = Column(ARRAY(String))  # List of assessed frameworks
    assessment_method = Column(String(100), default="automated")
    assessor_id = Column(String(255))

    # Temporal information
    assessment_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    next_assessment_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("DatabaseAsset", back_populates="compliance_assessments")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "overall_compliance_score >= 0.0 AND overall_compliance_score <= 1.0", name="check_compliance_score_range"
        ),
        CheckConstraint("compliance_accuracy >= 0.0 AND compliance_accuracy <= 1.0", name="check_accuracy_range"),
        CheckConstraint("total_requirements_assessed >= 0", name="check_total_requirements_positive"),
        Index("idx_compliance_score_date", "overall_compliance_score", "assessment_date"),
        Index("idx_frameworks_assessed", "frameworks_assessed"),
    )


class RiskAlert(Base):
    """
    Risk alerting and notification management

    Manages risk-based alerts, escalations, and multi-channel notifications
    for automated risk monitoring and response.
    """

    __tablename__ = "risk_alerts"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)
    risk_assessment_id = Column(UUID(as_uuid=True), ForeignKey("risk_assessments.id"), index=True)

    # Alert classification
    alert_level = Column(String(50), nullable=False)
    alert_type = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)

    # Alert context
    triggering_condition = Column(JSONB)  # Condition that triggered the alert
    risk_context = Column(JSONB)  # Risk assessment context

    # Alert lifecycle
    triggered_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    acknowledged_at = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))
    escalated = Column(Boolean, default=False)
    escalation_count = Column(Integer, default=0)

    # Notification management
    notification_channels = Column(ARRAY(String))  # email, sms, webhook, etc.
    notification_sent = Column(Boolean, default=False)
    notification_attempts = Column(Integer, default=0)
    notification_responses = Column(JSONB)  # Responses from notification channels

    # Alert metadata
    severity_score = Column(Float)  # Numeric severity for prioritization
    auto_resolve_eligible = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("DatabaseAsset", back_populates="risk_alerts")
    risk_assessment = relationship("RiskAssessment", back_populates="risk_alerts")

    # Constraints
    __table_args__ = (
        CheckConstraint("alert_level IN ('info', 'warning', 'critical', 'emergency')", name="check_alert_level"),
        CheckConstraint("escalation_count >= 0", name="check_escalation_count_positive"),
        CheckConstraint("notification_attempts >= 0", name="check_notification_attempts_positive"),
        Index("idx_alert_level_triggered", "alert_level", "triggered_at"),
        Index("idx_unresolved_alerts", "resolved_at"),  # NULL values for unresolved alerts
        Index("idx_escalated_alerts", "escalated", "triggered_at"),
    )


class RiskTrend(Base):
    """
    Risk trend analysis and predictive scoring data

    Stores historical risk data for trend analysis and predictive risk modeling
    to support 90% accurate risk trajectory predictions.
    """

    __tablename__ = "risk_trends"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)

    # Risk trend data
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(50), nullable=False)
    trend_direction = Column(String(50))  # increasing, decreasing, stable
    trend_magnitude = Column(Float)  # Rate of change

    # Predictive modeling data
    predicted_risk_score = Column(Float)  # Predicted future risk score
    prediction_confidence = Column(Float)  # Confidence in prediction (0.0-1.0)
    prediction_horizon_days = Column(Integer)  # Prediction time horizon

    # Contributing factors
    vulnerability_trend = Column(Float)  # Vulnerability score trend
    threat_landscape_change = Column(Float)  # Threat environment changes
    control_effectiveness_trend = Column(Float)  # Control effectiveness trend

    # Anomaly detection
    anomaly_detected = Column(Boolean, default=False)
    anomaly_severity = Column(Float)
    anomaly_description = Column(Text)

    # Temporal information
    measurement_date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("DatabaseAsset")

    # Constraints
    __table_args__ = (
        CheckConstraint("risk_score >= 1.0 AND risk_score <= 25.0", name="check_trend_risk_score_range"),
        CheckConstraint(
            "prediction_confidence >= 0.0 AND prediction_confidence <= 1.0", name="check_prediction_confidence_range"
        ),
        CheckConstraint("prediction_horizon_days > 0", name="check_prediction_horizon_positive"),
        Index("idx_measurement_date_asset", "measurement_date", "asset_id"),
        Index("idx_anomaly_detected", "anomaly_detected", "measurement_date"),
        Index("idx_trend_direction", "trend_direction", "measurement_date"),
    )
