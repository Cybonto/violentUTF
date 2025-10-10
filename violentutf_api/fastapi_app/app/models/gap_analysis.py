# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Gap Analysis Data Models for Issue #281.

This module defines the SQLAlchemy models for gap identification, analysis,
and reporting functionality.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship


# Enumerations
class GapType(PyEnum):
    """Types of gaps that can be identified."""

    MISSING_DOCUMENTATION = "missing_documentation"
    OUTDATED_DOCUMENTATION = "outdated_documentation"
    UNCLEAR_OWNERSHIP = "unclear_ownership"
    UNREFERENCED_ASSET = "unreferenced_asset"
    UNUSED_ASSET = "unused_asset"
    INSUFFICIENT_SECURITY_CONTROLS = "insufficient_security_controls"
    INSUFFICIENT_ACCESS_CONTROLS = "insufficient_access_controls"
    MISSING_BACKUP_PROCEDURES = "missing_backup_procedures"
    MISSING_RETENTION_POLICY = "missing_retention_policy"
    MISSING_DATA_SUBJECT_RIGHTS = "missing_data_subject_rights"
    INSUFFICIENT_MONITORING = "insufficient_monitoring"
    POLICY_VIOLATION = "policy_violation"
    UNDOCUMENTED_TABLE = "undocumented_table"
    UNDOCUMENTED_COLUMN = "undocumented_column"
    MISSING_COMPLIANCE_DOCUMENTATION = "missing_compliance_documentation"


class GapSeverity(PyEnum):
    """Severity levels for identified gaps."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ComplianceFramework(PyEnum):
    """Supported compliance frameworks."""

    GDPR = "GDPR"
    SOC2 = "SOC2"
    NIST = "NIST"
    HIPAA = "HIPAA"
    PCI_DSS = "PCI_DSS"


class PriorityLevel(PyEnum):
    """Priority levels for gap remediation."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DocumentationType(PyEnum):
    """Types of documentation required for assets."""

    BASIC_INFO = "basic_info"
    TECHNICAL_SPECS = "technical_specs"
    SECURITY_PROCEDURES = "security_procedures"
    ACCESS_CONTROLS = "access_controls"
    DATA_CLASSIFICATION = "data_classification"
    BACKUP_PROCEDURES = "backup_procedures"
    DISASTER_RECOVERY = "disaster_recovery"
    MONITORING_SETUP = "monitoring_setup"
    RUNBOOKS = "runbooks"
    ESCALATION_PROCEDURES = "escalation_procedures"
    CAPACITY_PLANNING = "capacity_planning"


# Pydantic Models for API Schemas
class PriorityScore(BaseModel):
    """Priority score calculation result."""

    score: float = Field(..., description="Overall priority score (0-375)")
    severity_component: float = Field(..., description="Severity score component (1-10)")
    criticality_component: float = Field(..., description="Asset criticality multiplier (1.0-3.0)")
    regulatory_component: float = Field(..., description="Regulatory impact multiplier (1.0-2.5)")
    security_component: float = Field(..., description="Security impact multiplier (1.0-2.0)")
    business_component: float = Field(..., description="Business impact multiplier (1.0-2.5)")
    priority_level: PriorityLevel = Field(..., description="Derived priority level")

    def __gt__(self, other: "PriorityScore") -> bool:
        """Compare priority scores (greater than)."""
        return self.score > other.score

    def __lt__(self, other: "PriorityScore") -> bool:
        """Compare priority scores (less than)."""
        return self.score < other.score


class Gap(BaseModel):
    """Base class for all gap types."""

    gap_id: Optional[str] = Field(None, description="Unique gap identifier")
    asset_id: str = Field(..., description="Asset this gap relates to")
    gap_type: GapType = Field(..., description="Type of gap identified")
    severity: GapSeverity = Field(..., description="Severity level of the gap")
    description: str = Field(..., description="Human-readable description of the gap")
    recommendations: List[str] = Field(default_factory=list, description="Recommended remediation actions")
    discovered_date: datetime = Field(default_factory=datetime.now, description="When the gap was discovered")
    priority_score: Optional[PriorityScore] = Field(None, description="Calculated priority score")

    class Config:
        """Pydantic configuration for Gap model."""

        use_enum_values = True


class OrphanedAssetGap(Gap):
    """Gap representing orphaned or unreferenced assets."""

    gap_type: GapType = Field(default=GapType.UNCLEAR_OWNERSHIP)
    last_activity_date: Optional[datetime] = Field(None, description="Last known activity on the asset")
    code_references: List[str] = Field(default_factory=list, description="Code files that reference this asset")
    usage_score: Optional[float] = Field(None, description="Asset usage score (0.0-1.0)")


class DocumentationGap(Gap):
    """Gap representing missing or inadequate documentation."""

    gap_type: GapType = Field(default=GapType.MISSING_DOCUMENTATION)
    documentation_type: Optional[DocumentationType] = Field(None, description="Type of missing documentation")
    last_updated: Optional[datetime] = Field(None, description="When documentation was last updated")
    completeness_score: Optional[float] = Field(None, description="Documentation completeness score (0.0-1.0)")
    quality_issues: List[str] = Field(default_factory=list, description="Specific quality issues identified")


class ComplianceGap(Gap):
    """Gap representing compliance violations."""

    gap_type: GapType = Field(default=GapType.INSUFFICIENT_SECURITY_CONTROLS)
    framework: ComplianceFramework = Field(..., description="Compliance framework this gap violates")
    requirement: str = Field(..., description="Specific requirement that is not met")
    compliance_deadline: Optional[datetime] = Field(None, description="Deadline for compliance")
    regulatory_risk_level: Optional[str] = Field(None, description="Level of regulatory risk")


class SchemaDocumentationGap(Gap):
    """Gap representing missing database schema documentation."""

    gap_type: GapType = Field(default=GapType.UNDOCUMENTED_TABLE)
    table_name: Optional[str] = Field(None, description="Name of undocumented table")
    column_name: Optional[str] = Field(None, description="Name of undocumented column")
    schema_element_type: str = Field(..., description="Type of schema element (table, column, view, etc.)")


class PolicyGap(Gap):
    """Gap representing organizational policy violations."""

    gap_type: GapType = Field(default=GapType.POLICY_VIOLATION)
    policy_id: str = Field(..., description="ID of the violated policy")
    policy_name: str = Field(..., description="Name of the violated policy")
    violations: List[Dict[str, Any]] = Field(default_factory=list, description="Specific policy violations")


class GapAnalysisConfig(BaseModel):
    """Configuration for gap analysis execution."""

    include_orphaned_detection: bool = Field(default=True, description="Include orphaned resource detection")
    include_documentation_analysis: bool = Field(default=True, description="Include documentation gap analysis")
    include_compliance_assessment: bool = Field(default=True, description="Include compliance gap assessment")
    compliance_frameworks: List[str] = Field(
        default=["GDPR", "SOC2", "NIST"], description="Compliance frameworks to assess"
    )
    max_execution_time_seconds: int = Field(default=180, ge=1, le=600, description="Maximum execution time")
    max_memory_usage_mb: int = Field(default=256, ge=1, le=2048, description="Maximum memory usage")
    asset_filters: Optional[Dict[str, List[str]]] = Field(None, description="Filters to apply to asset selection")
    include_trend_analysis: bool = Field(default=False, description="Include historical trend analysis")
    real_time_monitoring: bool = Field(default=False, description="Enable real-time monitoring integration")
    monitoring_interval_minutes: int = Field(default=60, ge=1, le=1440, description="Monitoring check interval")


class GapAnalysisResult(BaseModel):
    """Result of gap analysis execution."""

    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    execution_time_seconds: float = Field(..., description="Total execution time")
    total_gaps_found: int = Field(..., description="Total number of gaps identified")
    assets_analyzed: int = Field(..., description="Number of assets analyzed")
    gaps: List[Gap] = Field(default_factory=list, description="All identified gaps")
    gaps_by_type: Dict[str, int] = Field(default_factory=dict, description="Gap count by type")
    gaps_by_severity: Dict[str, int] = Field(default_factory=dict, description="Gap count by severity")
    performance_breakdown: Optional[Dict[str, float]] = Field(None, description="Performance timing breakdown")
    memory_usage_mb: Optional[float] = Field(None, description="Peak memory usage during analysis")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during analysis")
    trend_analysis: Optional[Dict[str, Any]] = Field(None, description="Trend analysis results")

    @property
    def all_gaps(self) -> List[Gap]:
        """Return all gaps as a unified list."""
        return self.gaps

    @property
    def high_severity_gaps(self) -> int:
        """Count of high severity gaps."""
        return self.gaps_by_severity.get(GapSeverity.HIGH.value, 0)

    @property
    def medium_severity_gaps(self) -> int:
        """Count of medium severity gaps."""
        return self.gaps_by_severity.get(GapSeverity.MEDIUM.value, 0)

    @property
    def low_severity_gaps(self) -> int:
        """Count of low severity gaps."""
        return self.gaps_by_severity.get(GapSeverity.LOW.value, 0)

    @property
    def average_priority_score(self) -> float:
        """Average priority score of all gaps."""
        if not self.gaps:
            return 0.0

        scores = [gap.priority_score.score for gap in self.gaps if gap.priority_score]
        return sum(scores) / len(scores) if scores else 0.0


class UsageMetrics(BaseModel):
    """Asset usage metrics for orphaned detection."""

    asset_id: str = Field(..., description="Asset identifier")
    connection_count: int = Field(..., description="Number of connections in period")
    last_activity_date: datetime = Field(..., description="Last recorded activity")
    days_since_last_activity: int = Field(..., description="Days since last activity")
    activity_score: float = Field(..., ge=0.0, le=1.0, description="Activity score (0.0-1.0)")
    seasonal_pattern: bool = Field(default=False, description="Whether asset shows seasonal usage")
    last_season_activity: Optional[datetime] = Field(None, description="Last seasonal activity")

    def is_active(self) -> bool:
        """Determine if asset is considered active."""
        return self.activity_score > 0.5 and self.days_since_last_activity < 30


class CodeReference(BaseModel):
    """Reference to an asset found in code."""

    file_path: str = Field(..., description="Path to file containing reference")
    line_number: int = Field(..., description="Line number of reference")
    context: str = Field(..., description="Code context containing the reference")
    reference_type: str = Field(..., description="Type of reference (name, connection_string, file_path)")

    def __eq__(self, other: object) -> bool:
        """Compare code references for equality."""
        if not isinstance(other, CodeReference):
            return False
        return (
            self.file_path == other.file_path
            and self.line_number == other.line_number
            and self.context == other.context
        )


class ConfigurationDrift(BaseModel):
    """Configuration drift between environments."""

    asset_id: str = Field(..., description="Asset identifier")
    differences: List[Dict[str, Any]] = Field(default_factory=list, description="Configuration differences")
    drift_score: float = Field(..., ge=0.0, le=1.0, description="Drift score (0.0-1.0)")


class QualityIssue(BaseModel):
    """Documentation quality issue."""

    severity: GapSeverity = Field(..., description="Issue severity")
    description: str = Field(..., description="Issue description")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations to fix issue")

    def __eq__(self, other: object) -> bool:
        """Compare quality issues for equality."""
        if not isinstance(other, QualityIssue):
            return False
        return (
            self.severity == other.severity
            and self.description == other.description
            and self.recommendations == other.recommendations
        )


class PolicyViolation(BaseModel):
    """Specific policy violation details."""

    rule_id: str = Field(..., description="Policy rule identifier")
    rule_description: str = Field(..., description="Description of violated rule")
    actual_value: Any = Field(..., description="Actual asset value")
    expected_value: Any = Field(..., description="Expected value per policy")
    impact: str = Field(..., description="Impact level of violation")


class PolicyAssessment(BaseModel):
    """Assessment of asset against policy."""

    compliant: bool = Field(..., description="Whether asset is compliant")
    violations: List[PolicyViolation] = Field(default_factory=list, description="Policy violations found")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for compliance")


class ResourceAllocationRecommendation(BaseModel):
    """Resource allocation recommendations for gap remediation."""

    immediate_action_gaps: int = Field(..., description="Gaps requiring immediate action")
    scheduled_action_gaps: int = Field(..., description="Gaps for scheduled remediation")
    estimated_effort_hours: int = Field(..., description="Total estimated effort in hours")
    team_assignments: Dict[str, int] = Field(default_factory=dict, description="Recommended team assignments")
    recommended_timeline_weeks: int = Field(..., description="Recommended timeline in weeks")
    budget_estimate: Optional[float] = Field(None, description="Estimated budget requirement")

    @property
    def total_gaps(self) -> int:
        """Total number of gaps to remediate."""
        return self.immediate_action_gaps + self.scheduled_action_gaps

    @property
    def average_effort_per_gap(self) -> float:
        """Average effort per gap in hours."""
        return self.estimated_effort_hours / self.total_gaps if self.total_gaps > 0 else 0.0

    @property
    def weekly_budget(self) -> float:
        """Weekly budget requirement."""
        return (
            self.budget_estimate / self.recommended_timeline_weeks
            if self.budget_estimate and self.recommended_timeline_weeks > 0
            else 0.0
        )


class BusinessImpactAssessment(BaseModel):
    """Business impact assessment for gaps."""

    financial_impact: float = Field(..., description="Estimated financial impact")
    operational_impact: str = Field(..., description="Operational impact description")
    reputation_impact: str = Field(..., description="Reputation impact level")
    compliance_impact: str = Field(..., description="Compliance impact level")
    overall_risk_score: float = Field(..., ge=0.0, le=10.0, description="Overall risk score (0-10)")


# Exception classes
class GapAnalysisError(Exception):
    """Base exception for gap analysis operations."""


class GapAnalysisTimeout(GapAnalysisError):
    """Exception raised when gap analysis exceeds time limit."""


class GapAnalysisMemoryLimit(GapAnalysisError):
    """Exception raised when gap analysis exceeds memory limit."""
