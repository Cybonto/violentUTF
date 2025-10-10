# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Gap Analysis API Schemas for Issue #281.

This module defines the Pydantic schemas for gap analysis API endpoints,
including request/response validation and serialization.
"""

from datetime import datetime

# from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, validator

from app.models.gap_analysis import (
    ComplianceFramework,
    PriorityLevel,
)


# Request Schemas
class GapAnalysisRequest(BaseModel):
    """Request schema for gap analysis."""

    include_orphaned_detection: bool = Field(default=True, description="Include orphaned resource detection")
    include_documentation_analysis: bool = Field(default=True, description="Include documentation gap analysis")
    include_compliance_assessment: bool = Field(default=True, description="Include compliance gap assessment")
    compliance_frameworks: List[str] = Field(
        default=["GDPR", "SOC2", "NIST"], description="Compliance frameworks to assess"
    )
    max_execution_time_seconds: int = Field(default=180, ge=1, le=600, description="Maximum execution time in seconds")
    max_memory_usage_mb: int = Field(default=256, ge=1, le=2048, description="Maximum memory usage in MB")
    asset_filters: Optional[Dict[str, List[str]]] = Field(None, description="Filters to apply to asset selection")
    include_trend_analysis: bool = Field(default=False, description="Include historical trend analysis")
    real_time_monitoring: bool = Field(default=False, description="Enable real-time monitoring integration")
    monitoring_interval_minutes: int = Field(
        default=60, ge=1, le=1440, description="Monitoring check interval in minutes"
    )

    @validator("compliance_frameworks")
    @classmethod
    def validate_compliance_frameworks(cls: Type["GapAnalysisRequest"], v: List[str]) -> List[str]:
        """Validate compliance framework names."""
        valid_frameworks = [f.value for f in ComplianceFramework]
        for framework in v:
            if framework not in valid_frameworks:
                raise ValueError(f"Invalid compliance framework: {framework}")
        return v

    @validator("asset_filters")
    @classmethod
    def validate_asset_filters(
        cls: Type["GapAnalysisRequest"], v: Optional[Dict[str, List[str]]]
    ) -> Optional[Dict[str, List[str]]]:
        """Validate asset filter parameters."""
        if v is None:
            return v

        valid_filters = {
            "environment",
            "criticality",
            "asset_type",
            "security_classification",
            "owner_team",
            "compliance_requirements",
        }

        for filter_key in v.keys():
            if filter_key not in valid_filters:
                raise ValueError(f"Invalid asset filter: {filter_key}")

        return v


class RemediationActionRequest(BaseModel):
    """Request schema for gap remediation action."""

    gap_id: str = Field(..., description="Gap identifier to remediate")
    action_type: str = Field(..., description="Type of remediation action")
    assigned_team: str = Field(..., description="Team assigned to perform remediation")
    priority: str = Field(..., description="Remediation priority level")
    description: str = Field(..., description="Description of remediation action")
    estimated_effort_hours: int = Field(..., ge=1, description="Estimated effort in hours")
    target_completion_date: Optional[datetime] = Field(None, description="Target completion date")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies for this action")

    @validator("action_type")
    @classmethod
    def validate_action_type(cls: Type["RemediationActionRequest"], v: str) -> str:
        """Validate remediation action type."""
        valid_types = {
            "documentation_creation",
            "documentation_update",
            "ownership_assignment",
            "security_control_implementation",
            "access_control_configuration",
            "backup_setup",
            "monitoring_configuration",
            "policy_compliance",
            "asset_decommission",
            "encryption_enablement",
        }
        if v not in valid_types:
            raise ValueError(f"Invalid action type: {v}")
        return v

    @validator("priority")
    @classmethod
    def validate_priority(cls: Type["RemediationActionRequest"], v: str) -> str:
        """Validate priority level."""
        valid_priorities = [p.value for p in PriorityLevel]
        if v not in valid_priorities:
            raise ValueError(f"Invalid priority: {v}")
        return v


# Response Schemas
class PriorityScoreResponse(BaseModel):
    """Response schema for priority score."""

    score: float = Field(..., description="Overall priority score (0-375)")
    severity_component: float = Field(..., description="Severity score component")
    criticality_component: float = Field(..., description="Asset criticality multiplier")
    regulatory_component: float = Field(..., description="Regulatory impact multiplier")
    security_component: float = Field(..., description="Security impact multiplier")
    business_component: float = Field(..., description="Business impact multiplier")
    priority_level: str = Field(..., description="Priority level")


class GapResponse(BaseModel):
    """Base response schema for gaps."""

    gap_id: Optional[str] = Field(None, description="Unique gap identifier")
    asset_id: str = Field(..., description="Asset this gap relates to")
    gap_type: str = Field(..., description="Type of gap identified")
    severity: str = Field(..., description="Severity level of the gap")
    description: str = Field(..., description="Human-readable description")
    recommendations: List[str] = Field(..., description="Recommended remediation actions")
    discovered_date: datetime = Field(..., description="When the gap was discovered")
    priority_score: Optional[PriorityScoreResponse] = Field(None, description="Priority score")


class OrphanedAssetGapResponse(GapResponse):
    """Response schema for orphaned asset gaps."""

    last_activity_date: Optional[datetime] = Field(None, description="Last known activity")
    code_references: List[str] = Field(..., description="Code files referencing this asset")
    usage_score: Optional[float] = Field(None, description="Asset usage score")


class DocumentationGapResponse(GapResponse):
    """Response schema for documentation gaps."""

    documentation_type: Optional[str] = Field(None, description="Type of missing documentation")
    last_updated: Optional[datetime] = Field(None, description="When documentation was last updated")
    completeness_score: Optional[float] = Field(None, description="Documentation completeness score")
    quality_issues: List[str] = Field(..., description="Specific quality issues")


class ComplianceGapResponse(GapResponse):
    """Response schema for compliance gaps."""

    framework: str = Field(..., description="Compliance framework")
    requirement: str = Field(..., description="Specific requirement not met")
    compliance_deadline: Optional[datetime] = Field(None, description="Compliance deadline")
    regulatory_risk_level: Optional[str] = Field(None, description="Regulatory risk level")


class GapAnalysisResponse(BaseModel):
    """Response schema for gap analysis results."""

    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    execution_time_seconds: float = Field(..., description="Total execution time")
    total_gaps_found: int = Field(..., description="Total number of gaps identified")
    assets_analyzed: int = Field(..., description="Number of assets analyzed")
    gaps_by_type: Dict[str, int] = Field(..., description="Gap count by type")
    gaps_by_severity: Dict[str, int] = Field(..., description="Gap count by severity")
    performance_breakdown: Optional[Dict[str, float]] = Field(None, description="Performance breakdown")
    memory_usage_mb: Optional[float] = Field(None, description="Peak memory usage")
    errors: List[str] = Field(..., description="Errors encountered")
    trend_analysis: Optional[Dict[str, Any]] = Field(None, description="Trend analysis results")

    # Summary statistics
    high_severity_gaps: int = Field(..., description="Count of high severity gaps")
    medium_severity_gaps: int = Field(..., description="Count of medium severity gaps")
    low_severity_gaps: int = Field(..., description="Count of low severity gaps")
    average_priority_score: float = Field(..., description="Average priority score")


class GapDetailsResponse(BaseModel):
    """Detailed response for individual gap with full information."""

    gap: Union[OrphanedAssetGapResponse, DocumentationGapResponse, ComplianceGapResponse]
    asset_details: Dict[str, Any] = Field(..., description="Related asset information")
    remediation_history: List[Dict[str, Any]] = Field(..., description="Previous remediation attempts")
    related_gaps: List[str] = Field(..., description="Related gap identifiers")
    impact_assessment: Dict[str, Any] = Field(..., description="Business impact assessment")


class GapListResponse(BaseModel):
    """Response schema for paginated gap lists."""

    gaps: List[GapResponse] = Field(..., description="List of gaps")
    pagination: Dict[str, Any] = Field(..., description="Pagination information")
    filters_applied: Dict[str, Any] = Field(..., description="Applied filters")
    sort_criteria: Dict[str, str] = Field(..., description="Sort criteria")


class GapReportResponse(BaseModel):
    """Response schema for gap analysis reports."""

    report_id: str = Field(..., description="Unique report identifier")
    analysis_id: str = Field(..., description="Associated analysis ID")
    generated_date: datetime = Field(..., description="Report generation date")
    report_type: str = Field(..., description="Type of report")
    total_gaps: int = Field(..., description="Total gaps in report")
    recommendations_count: int = Field(..., description="Number of recommendations")
    report_summary: str = Field(..., description="Executive summary")
    download_url: Optional[str] = Field(None, description="URL to download full report")
    report_sections: List[Dict[str, Any]] = Field(..., description="Report sections")


class TrendAnalysisResponse(BaseModel):
    """Response schema for gap trend analysis."""

    trend_id: str = Field(..., description="Unique trend analysis identifier")
    period_days: int = Field(..., description="Analysis period in days")
    total_gap_trend: float = Field(..., description="Total gap trend (-1.0 to 1.0)")
    critical_gap_trend: float = Field(..., description="Critical gap trend")
    high_gap_trend: float = Field(..., description="High severity gap trend")
    medium_gap_trend: float = Field(..., description="Medium severity gap trend")
    low_gap_trend: float = Field(..., description="Low severity gap trend")
    trend_summary: str = Field(..., description="Trend summary description")
    improvement_rate: float = Field(..., description="Overall improvement rate")
    historical_data: List[Dict[str, Any]] = Field(..., description="Historical data points")
    forecasted_gaps: Optional[Dict[str, int]] = Field(None, description="Forecasted gap counts")


class RemediationActionResponse(BaseModel):
    """Response schema for remediation actions."""

    action_id: str = Field(..., description="Unique action identifier")
    gap_id: str = Field(..., description="Associated gap ID")
    action_type: str = Field(..., description="Type of remediation action")
    assigned_team: str = Field(..., description="Assigned team")
    priority: str = Field(..., description="Priority level")
    status: str = Field(..., description="Current status")
    description: str = Field(..., description="Action description")
    estimated_effort_hours: int = Field(..., description="Estimated effort")
    actual_effort_hours: Optional[int] = Field(None, description="Actual effort spent")
    target_completion_date: Optional[datetime] = Field(None, description="Target completion")
    actual_completion_date: Optional[datetime] = Field(None, description="Actual completion")
    created_date: datetime = Field(..., description="Action creation date")
    last_updated: datetime = Field(..., description="Last update date")
    dependencies: List[str] = Field(..., description="Action dependencies")
    progress_percentage: int = Field(..., ge=0, le=100, description="Progress percentage")


class ResourceAllocationResponse(BaseModel):
    """Response schema for resource allocation recommendations."""

    immediate_action_gaps: int = Field(..., description="Gaps requiring immediate action")
    scheduled_action_gaps: int = Field(..., description="Gaps for scheduled remediation")
    total_gaps: int = Field(..., description="Total gaps to remediate")
    estimated_effort_hours: int = Field(..., description="Total estimated effort")
    average_effort_per_gap: float = Field(..., description="Average effort per gap")
    team_assignments: Dict[str, int] = Field(..., description="Recommended team assignments")
    recommended_timeline_weeks: int = Field(..., description="Recommended timeline")
    budget_estimate: Optional[float] = Field(None, description="Budget estimate")
    weekly_budget: Optional[float] = Field(None, description="Weekly budget requirement")
    resource_constraints: List[str] = Field(..., description="Identified resource constraints")


class ComplianceAccuracyResponse(BaseModel):
    """Response schema for compliance detection accuracy metrics."""

    framework: str = Field(..., description="Compliance framework")
    accuracy_percentage: float = Field(..., ge=0.0, le=100.0, description="Detection accuracy")
    true_positives: int = Field(..., description="Correctly identified violations")
    false_positives: int = Field(..., description="Incorrectly identified violations")
    true_negatives: int = Field(..., description="Correctly identified compliant assets")
    false_negatives: int = Field(..., description="Missed violations")
    precision: float = Field(..., description="Precision score")
    recall: float = Field(..., description="Recall score")
    f1_score: float = Field(..., description="F1 score")


class GapAnalysisStatusResponse(BaseModel):
    """Response schema for gap analysis status checks."""

    analysis_id: str = Field(..., description="Analysis identifier")
    status: str = Field(..., description="Current status")
    progress_percentage: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_phase: str = Field(..., description="Current analysis phase")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated completion")
    assets_processed: int = Field(..., description="Assets processed so far")
    total_assets: int = Field(..., description="Total assets to process")
    gaps_found_so_far: int = Field(..., description="Gaps identified so far")
    last_updated: datetime = Field(..., description="Last status update")


# Error Response Schemas
class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracing")


class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""

    error_type: str = Field(default="validation_error", description="Error type")
    errors: List[Dict[str, Any]] = Field(..., description="Validation error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# Health Check Schemas
class GapAnalysisHealthResponse(BaseModel):
    """Health check response for gap analysis services."""

    status: str = Field(..., description="Overall health status")
    services: Dict[str, str] = Field(..., description="Individual service statuses")
    last_successful_analysis: Optional[datetime] = Field(None, description="Last successful analysis")
    total_analyses_today: int = Field(..., description="Total analyses performed today")
    average_execution_time: float = Field(..., description="Average execution time")
    memory_usage_percentage: float = Field(..., description="Current memory usage")
    active_analyses: int = Field(..., description="Currently running analyses")


# Configuration Schemas
class GapAnalysisConfigResponse(BaseModel):
    """Response schema for gap analysis configuration."""

    max_concurrent_analyses: int = Field(..., description="Maximum concurrent analyses")
    default_timeout_seconds: int = Field(..., description="Default timeout")
    default_memory_limit_mb: int = Field(..., description="Default memory limit")
    supported_frameworks: List[str] = Field(..., description="Supported compliance frameworks")
    supported_asset_types: List[str] = Field(..., description="Supported asset types")
    performance_thresholds: Dict[str, float] = Field(..., description="Performance thresholds")
    feature_flags: Dict[str, bool] = Field(..., description="Feature availability flags")
