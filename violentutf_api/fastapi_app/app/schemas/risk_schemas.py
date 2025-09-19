# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for Risk Assessment API for Issue #282.

This module contains all the Pydantic models for request/response validation
in the risk assessment API endpoints. Supports NIST RMF-compliant risk scoring,
vulnerability assessment, security control evaluation, and compliance risk management.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


# Enums for risk assessment
class RiskLevel(str, Enum):
    """Risk level categories based on NIST RMF scoring (1-25 scale)"""

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


class ImpactLevel(str, Enum):
    """NIST RMF impact levels for system categorization"""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class AssessmentMethod(str, Enum):
    """Risk assessment methods"""

    AUTOMATED = "automated"
    MANUAL = "manual"
    HYBRID = "hybrid"


# Base schemas for risk assessment
class RiskFactorsBase(BaseModel):
    """Base schema for risk assessment factors"""

    likelihood_score: float = Field(..., ge=1.0, le=5.0, description="Threat likelihood (1-5 scale)")
    impact_score: float = Field(..., ge=1.0, le=5.0, description="Business impact (1-5 scale)")
    exposure_factor: float = Field(..., ge=0.1, le=1.0, description="Exposure factor based on controls (0.1-1.0)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in assessment (0.0-1.0)")


class SystemCategorizationBase(BaseModel):
    """Base schema for NIST RMF system categorization"""

    confidentiality_impact: ImpactLevel = Field(..., description="Confidentiality impact level")
    integrity_impact: ImpactLevel = Field(..., description="Integrity impact level")
    availability_impact: ImpactLevel = Field(..., description="Availability impact level")
    overall_categorization: ImpactLevel = Field(..., description="Overall system categorization")
    data_types: List[str] = Field(default_factory=list, description="Types of data processed")
    rationale: str = Field(..., description="Categorization rationale")


class VulnerabilityBase(BaseModel):
    """Base schema for vulnerability information"""

    cve_id: str = Field(..., description="CVE identifier")
    description: str = Field(..., description="Vulnerability description")
    cvss_score: float = Field(..., ge=0.0, le=10.0, description="CVSS score (0-10)")
    severity: VulnerabilitySeverity = Field(..., description="Vulnerability severity")
    published_date: datetime = Field(..., description="Publication date")
    last_modified: datetime = Field(..., description="Last modification date")
    cpe_matches: List[str] = Field(default_factory=list, description="Matching CPE identifiers")
    references: List[str] = Field(default_factory=list, description="Reference URLs")
    cwe_ids: List[str] = Field(default_factory=list, description="CWE identifiers")
    exploit_available: bool = Field(default=False, description="Whether exploits are available")


class RemediationRecommendationBase(BaseModel):
    """Base schema for remediation recommendations"""

    priority: int = Field(..., ge=1, description="Priority level (1=highest)")
    action: str = Field(..., description="Recommended action type")
    description: str = Field(..., description="Detailed description")
    affected_vulnerabilities: List[str] = Field(default_factory=list, description="Affected CVE IDs")
    estimated_effort_hours: int = Field(..., ge=0, description="Estimated effort in hours")
    business_impact: str = Field(..., description="Business impact level")
    technical_complexity: str = Field(..., description="Technical complexity level")


# Request schemas
class RiskAssessmentRequest(BaseModel):
    """Request schema for triggering risk assessment"""

    asset_id: uuid.UUID = Field(..., description="Asset UUID to assess")
    assessment_method: AssessmentMethod = Field(default=AssessmentMethod.AUTOMATED, description="Assessment method")
    include_vulnerabilities: bool = Field(default=True, description="Include vulnerability assessment")
    include_controls: bool = Field(default=True, description="Include control assessment")
    include_compliance: bool = Field(default=True, description="Include compliance assessment")
    force_refresh: bool = Field(default=False, description="Force refresh of cached data")


class BulkRiskAssessmentRequest(BaseModel):
    """Request schema for bulk risk assessment"""

    asset_ids: List[uuid.UUID] = Field(..., min_length=1, max_length=100, description="Asset UUIDs to assess")
    assessment_method: AssessmentMethod = Field(default=AssessmentMethod.AUTOMATED, description="Assessment method")
    include_vulnerabilities: bool = Field(default=True, description="Include vulnerability assessment")
    include_controls: bool = Field(default=True, description="Include control assessment")
    include_compliance: bool = Field(default=True, description="Include compliance assessment")
    force_refresh: bool = Field(default=False, description="Force refresh of cached data")


class VulnerabilityScanRequest(BaseModel):
    """Request schema for vulnerability scanning"""

    asset_id: uuid.UUID = Field(..., description="Asset UUID to scan")
    scan_depth: str = Field(default="standard", description="Scan depth: basic, standard, comprehensive")
    include_exploit_check: bool = Field(default=True, description="Check for available exploits")
    force_refresh: bool = Field(default=False, description="Force refresh of cached vulnerability data")


class ControlAssessmentRequest(BaseModel):
    """Request schema for security control assessment"""

    asset_id: uuid.UUID = Field(..., description="Asset UUID to assess")
    control_families: Optional[List[str]] = Field(None, description="Specific control families to assess")
    assessment_depth: str = Field(default="standard", description="Assessment depth: basic, standard, comprehensive")


class RiskAlertConfigRequest(BaseModel):
    """Request schema for configuring risk alerts"""

    asset_id: Optional[uuid.UUID] = Field(None, description="Asset UUID (null for global)")
    risk_threshold: float = Field(..., ge=1.0, le=25.0, description="Risk score threshold for alerts")
    alert_level: AlertLevel = Field(..., description="Alert level to trigger")
    notification_channels: List[str] = Field(..., description="Notification channels: email, sms, webhook")
    escalation_rules: Optional[Dict[str, Any]] = Field(None, description="Escalation rules")
    enabled: bool = Field(default=True, description="Whether alerts are enabled")


# Response schemas
class RiskFactorsResponse(RiskFactorsBase):
    """Response schema for risk factors"""

    model_config = ConfigDict(from_attributes=True)


class SystemCategorizationResponse(SystemCategorizationBase):
    """Response schema for system categorization"""

    model_config = ConfigDict(from_attributes=True)


class VulnerabilityResponse(VulnerabilityBase):
    """Response schema for vulnerability"""

    model_config = ConfigDict(from_attributes=True)


class RemediationRecommendationResponse(RemediationRecommendationBase):
    """Response schema for remediation recommendation"""

    model_config = ConfigDict(from_attributes=True)


class VulnerabilityAssessmentResponse(BaseModel):
    """Response schema for vulnerability assessment"""

    id: uuid.UUID = Field(..., description="Assessment UUID")
    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    assessment_date: datetime = Field(..., description="Assessment timestamp")

    # Vulnerability statistics
    total_vulnerabilities: int = Field(..., description="Total vulnerabilities found")
    critical_vulnerabilities: int = Field(..., description="Critical vulnerabilities")
    high_vulnerabilities: int = Field(..., description="High vulnerabilities")
    medium_vulnerabilities: int = Field(..., description="Medium vulnerabilities")
    low_vulnerabilities: int = Field(..., description="Low vulnerabilities")

    # Scoring and recommendations
    vulnerability_score: float = Field(..., ge=1.0, le=5.0, description="Overall vulnerability score")
    vulnerabilities: List[VulnerabilityResponse] = Field(default_factory=list, description="Detailed vulnerabilities")
    remediation_recommendations: List[RemediationRecommendationResponse] = Field(
        default_factory=list, description="Remediation recommendations"
    )

    # Metadata
    scan_duration_seconds: Optional[int] = Field(None, description="Scan duration")
    next_scan_date: datetime = Field(..., description="Next scheduled scan")

    model_config = ConfigDict(from_attributes=True)


class ControlAssessmentResponse(BaseModel):
    """Response schema for security control assessment"""

    id: uuid.UUID = Field(..., description="Assessment UUID")
    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    assessment_date: datetime = Field(..., description="Assessment timestamp")

    # Control statistics
    total_controls_assessed: int = Field(..., description="Total controls assessed")
    implemented_controls: int = Field(..., description="Implemented controls")
    partially_implemented_controls: int = Field(..., description="Partially implemented controls")
    not_implemented_controls: int = Field(..., description="Not implemented controls")

    # Effectiveness scoring
    overall_effectiveness: float = Field(..., ge=0.0, le=1.0, description="Overall effectiveness score")
    gaps_identified: int = Field(..., description="Number of gaps identified")

    # Control family scores
    access_control_score: Optional[float] = Field(None, description="Access Control (AC) family score")
    audit_accountability_score: Optional[float] = Field(None, description="Audit & Accountability (AU) family score")
    security_assessment_score: Optional[float] = Field(None, description="Security Assessment (CA) family score")
    configuration_management_score: Optional[float] = Field(
        None, description="Configuration Management (CM) family score"
    )
    contingency_planning_score: Optional[float] = Field(None, description="Contingency Planning (CP) family score")
    identification_auth_score: Optional[float] = Field(
        None, description="Identification & Authentication (IA) family score"
    )
    system_protection_score: Optional[float] = Field(None, description="System Protection (SC) family score")

    # Detailed results
    control_results: Dict[str, Any] = Field(default_factory=dict, description="Detailed control results")
    gap_analysis: Dict[str, Any] = Field(default_factory=dict, description="Gap analysis")
    improvement_recommendations: List[str] = Field(default_factory=list, description="Improvement recommendations")

    # Metadata
    next_assessment_date: datetime = Field(..., description="Next assessment date")

    model_config = ConfigDict(from_attributes=True)


class RiskAssessmentResponse(BaseModel):
    """Response schema for comprehensive risk assessment"""

    id: uuid.UUID = Field(..., description="Assessment UUID")
    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    assessment_date: datetime = Field(..., description="Assessment timestamp")

    # NIST RMF risk scoring
    risk_score: float = Field(..., ge=1.0, le=25.0, description="Risk score (1-25 scale)")
    risk_level: RiskLevel = Field(..., description="Risk level category")

    # Risk components
    risk_factors: RiskFactorsResponse = Field(..., description="Risk factor components")

    # NIST RMF process results
    system_categorization: SystemCategorizationResponse = Field(..., description="System categorization")
    selected_controls: List[str] = Field(default_factory=list, description="Selected security controls")
    control_assessment: Optional[ControlAssessmentResponse] = Field(None, description="Control assessment results")
    monitoring_plan: Dict[str, Any] = Field(default_factory=dict, description="Continuous monitoring plan")

    # Related assessments
    vulnerability_assessment: Optional[VulnerabilityAssessmentResponse] = Field(
        None, description="Vulnerability assessment"
    )

    # Assessment metadata
    assessment_method: AssessmentMethod = Field(..., description="Assessment method used")
    assessment_duration_ms: Optional[int] = Field(None, description="Assessment duration in milliseconds")
    assessor_id: Optional[str] = Field(None, description="Assessor identifier")
    next_assessment_due: datetime = Field(..., description="Next assessment due date")

    model_config = ConfigDict(from_attributes=True)


class RiskAlertResponse(BaseModel):
    """Response schema for risk alerts"""

    id: uuid.UUID = Field(..., description="Alert UUID")
    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    risk_assessment_id: Optional[uuid.UUID] = Field(None, description="Risk assessment UUID")

    # Alert details
    alert_level: AlertLevel = Field(..., description="Alert level")
    alert_type: str = Field(..., description="Alert type")
    message: str = Field(..., description="Alert message")

    # Alert lifecycle
    triggered_at: datetime = Field(..., description="Alert triggered timestamp")
    acknowledged_at: Optional[datetime] = Field(None, description="Alert acknowledged timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Alert resolved timestamp")
    escalated: bool = Field(..., description="Whether alert was escalated")
    escalation_count: int = Field(..., description="Number of escalations")

    # Notification details
    notification_channels: List[str] = Field(default_factory=list, description="Notification channels")
    notification_sent: bool = Field(..., description="Whether notification was sent")
    notification_attempts: int = Field(..., description="Number of notification attempts")

    # Context
    triggering_condition: Dict[str, Any] = Field(default_factory=dict, description="Triggering condition")
    risk_context: Dict[str, Any] = Field(default_factory=dict, description="Risk context")
    severity_score: Optional[float] = Field(None, description="Numeric severity score")

    model_config = ConfigDict(from_attributes=True)


class RiskTrendResponse(BaseModel):
    """Response schema for risk trend analysis"""

    id: uuid.UUID = Field(..., description="Trend UUID")
    asset_id: uuid.UUID = Field(..., description="Asset UUID")
    measurement_date: datetime = Field(..., description="Measurement timestamp")

    # Risk trend data
    risk_score: float = Field(..., ge=1.0, le=25.0, description="Risk score")
    risk_level: RiskLevel = Field(..., description="Risk level")
    trend_direction: Optional[str] = Field(None, description="Trend direction: increasing, decreasing, stable")
    trend_magnitude: Optional[float] = Field(None, description="Rate of change")

    # Predictive modeling
    predicted_risk_score: Optional[float] = Field(None, description="Predicted future risk score")
    prediction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Prediction confidence")
    prediction_horizon_days: Optional[int] = Field(None, description="Prediction time horizon")

    # Contributing factors
    vulnerability_trend: Optional[float] = Field(None, description="Vulnerability score trend")
    threat_landscape_change: Optional[float] = Field(None, description="Threat environment changes")
    control_effectiveness_trend: Optional[float] = Field(None, description="Control effectiveness trend")

    # Anomaly detection
    anomaly_detected: bool = Field(..., description="Whether anomaly was detected")
    anomaly_severity: Optional[float] = Field(None, description="Anomaly severity score")
    anomaly_description: Optional[str] = Field(None, description="Anomaly description")

    model_config = ConfigDict(from_attributes=True)


# Batch and search response schemas
class BulkRiskAssessmentResponse(BaseModel):
    """Response schema for bulk risk assessment"""

    job_id: str = Field(..., description="Bulk assessment job ID")
    status: str = Field(..., description="Job status: processing, completed, failed")
    total_assets: int = Field(..., description="Total assets to assess")
    completed_assessments: int = Field(default=0, description="Completed assessments")
    failed_assessments: int = Field(default=0, description="Failed assessments")
    started_at: datetime = Field(..., description="Job start time")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    results: List[RiskAssessmentResponse] = Field(default_factory=list, description="Assessment results")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class RiskSearchRequest(BaseModel):
    """Request schema for searching risk assessments"""

    query: Optional[str] = Field(None, description="Search query")
    risk_level: Optional[RiskLevel] = Field(None, description="Filter by risk level")
    min_risk_score: Optional[float] = Field(None, ge=1.0, le=25.0, description="Minimum risk score")
    max_risk_score: Optional[float] = Field(None, ge=1.0, le=25.0, description="Maximum risk score")
    assessment_date_from: Optional[datetime] = Field(None, description="Assessment date range start")
    assessment_date_to: Optional[datetime] = Field(None, description="Assessment date range end")
    asset_ids: Optional[List[uuid.UUID]] = Field(None, description="Filter by asset IDs")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")

    @field_validator("max_risk_score")
    @classmethod
    def validate_risk_score_range(cls: type, v: Optional[float], info: ValidationInfo) -> Optional[float]:
        """Validate risk score range"""
        if v is not None and info.data.get("min_risk_score") is not None:
            if v < info.data["min_risk_score"]:
                raise ValueError("max_risk_score must be greater than min_risk_score")
        return v


class RiskSearchResponse(BaseModel):
    """Response schema for risk assessment search"""

    results: List[RiskAssessmentResponse] = Field(..., description="Search results")
    total_matches: int = Field(..., description="Total matching records")
    query: Optional[str] = Field(None, description="Original search query")
    execution_time: float = Field(..., description="Search execution time in seconds")
    offset: int = Field(..., description="Result offset")
    limit: int = Field(..., description="Result limit")


class RiskAnalyticsResponse(BaseModel):
    """Response schema for risk analytics and reporting"""

    report_date: datetime = Field(..., description="Report generation date")
    total_assets: int = Field(..., description="Total assets assessed")

    # Risk distribution
    low_risk_count: int = Field(..., description="Low risk assets")
    medium_risk_count: int = Field(..., description="Medium risk assets")
    high_risk_count: int = Field(..., description="High risk assets")
    very_high_risk_count: int = Field(..., description="Very high risk assets")
    critical_risk_count: int = Field(..., description="Critical risk assets")

    # Risk statistics
    average_risk_score: float = Field(..., description="Average risk score")
    median_risk_score: float = Field(..., description="Median risk score")
    max_risk_score: float = Field(..., description="Maximum risk score")
    min_risk_score: float = Field(..., description="Minimum risk score")

    # Trend analysis
    risk_trends: List[RiskTrendResponse] = Field(default_factory=list, description="Risk trends")
    trend_summary: Dict[str, Any] = Field(default_factory=dict, description="Trend summary")

    # Top risks
    highest_risk_assets: List[RiskAssessmentResponse] = Field(
        default_factory=list, description="Assets with highest risk"
    )
    most_vulnerable_assets: List[RiskAssessmentResponse] = Field(
        default_factory=list, description="Most vulnerable assets"
    )

    # Recommendations
    priority_recommendations: List[str] = Field(default_factory=list, description="Priority recommendations")
