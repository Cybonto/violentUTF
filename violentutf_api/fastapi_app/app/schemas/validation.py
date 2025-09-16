# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for dataset validation API endpoints.

SECURITY: Enhanced with comprehensive input validation to prevent injection attacks.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, field_validator

from app.core.validation import SecurityLimits, ValidationPatterns, sanitize_string


class ValidationLevelEnum(str, Enum):
    """Validation level enumeration for API."""

    QUICK = "quick"
    FULL = "full"
    DEEP = "deep"


class ValidationStatusEnum(str, Enum):
    """Validation status enumeration for API."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIP = "SKIP"


class ValidationTypeEnum(str, Enum):
    """Validation type enumeration for API."""

    SOURCE_DATA = "source_data"
    CONVERSION_RESULT = "conversion_result"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"


class PerformanceMetrics(BaseModel):
    """Performance metrics for validation."""

    processing_time_seconds: float = Field(..., ge=0, description="Processing time in seconds")
    memory_usage_mb: float = Field(..., ge=0, description="Memory usage in MB")
    validation_time_seconds: float = Field(default=0.0, ge=0, description="Validation time in seconds")
    throughput_items_per_second: Optional[float] = Field(default=None, ge=0, description="Throughput rate")
    cpu_usage_percent: Optional[float] = Field(default=None, ge=0, le=100, description="CPU usage percentage")

    @field_validator("processing_time_seconds")
    @classmethod
    def validate_processing_time(cls: Type["PerformanceMetrics"], v: float) -> float:
        """Validate processing time is reasonable."""
        if v > 7200:  # 2 hours max
            raise ValueError("Processing time too long (max 2 hours)")
        return v

    @field_validator("memory_usage_mb")
    @classmethod
    def validate_memory_usage(cls: Type["PerformanceMetrics"], v: float) -> float:
        """Validate memory usage is reasonable."""
        if v > 8192:  # 8GB max
            raise ValueError("Memory usage too high (max 8GB)")
        return v


class ValidationBenchmarks(BaseModel):
    """Validation benchmarks for different dataset types."""

    max_time_seconds: float = Field(..., gt=0, description="Maximum allowed processing time")
    max_memory_mb: float = Field(..., gt=0, description="Maximum allowed memory usage")
    max_validation_overhead_percent: float = Field(default=5.0, ge=0, le=50, description="Max validation overhead")
    data_integrity_threshold: float = Field(default=0.99, ge=0, le=1, description="Data integrity threshold")

    @field_validator("max_time_seconds")
    @classmethod
    def validate_max_time(cls: Type["ValidationBenchmarks"], v: float) -> float:
        """Validate maximum time is reasonable."""
        if v > 3600:  # 1 hour max
            raise ValueError("Maximum time too long (max 1 hour)")
        return v


class ValidationDetailSchema(BaseModel):
    """Schema for validation detail results."""

    rule_name: str = Field(..., max_length=100, description="Validation rule name")
    status: ValidationStatusEnum = Field(..., description="Validation status")
    message: str = Field(..., max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH, description="Validation message")
    severity: str = Field(..., description="Severity level")
    remediation_suggestion: Optional[str] = Field(
        default=None, max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH, description="Suggested remediation"
    )
    execution_time_ms: Optional[float] = Field(default=None, ge=0, description="Execution time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("rule_name")
    @classmethod
    def validate_rule_name(cls: Type["ValidationDetailSchema"], v: str) -> str:
        """Validate rule name."""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Rule name must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @field_validator("message", "remediation_suggestion")
    @classmethod
    def validate_text_field(cls: Type["ValidationDetailSchema"], v: Optional[str]) -> Optional[str]:
        """Validate text fields."""
        if v is not None:
            return sanitize_string(v)
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls: Type["ValidationDetailSchema"], v: str) -> str:
        """Validate severity level."""
        v = sanitize_string(v).upper()
        allowed_severities = ["ERROR", "WARNING", "INFO"]
        if v not in allowed_severities:
            raise ValueError(f"Severity must be one of: {', '.join(allowed_severities)}")
        return v


class ValidationResultSchema(BaseModel):
    """Schema for validation results."""

    validation_type: str = Field(..., max_length=100, description="Type of validation performed")
    status: ValidationStatusEnum = Field(..., description="Overall validation status")
    details: List[ValidationDetailSchema] = Field(..., description="Detailed validation results")
    metrics: Dict[str, Any] = Field(..., description="Validation metrics")
    timestamp: datetime = Field(..., description="Validation timestamp")
    execution_time_ms: float = Field(..., ge=0, description="Total execution time in milliseconds")
    validator_name: str = Field(..., max_length=100, description="Name of the validator")

    @field_validator("validation_type", "validator_name")
    @classmethod
    def validate_names(cls: Type["ValidationResultSchema"], v: str) -> str:
        """Validate name fields."""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Name must contain only alphanumeric characters, underscores, and hyphens")
        return v


class ValidationRequest(BaseModel):
    """Request schema for dataset validation."""

    dataset_id: str = Field(
        ..., min_length=1, max_length=SecurityLimits.MAX_NAME_LENGTH, description="Dataset ID to validate"
    )
    validation_level: ValidationLevelEnum = Field(default=ValidationLevelEnum.FULL, description="Validation level")
    validation_types: List[ValidationTypeEnum] = Field(
        default=[ValidationTypeEnum.SOURCE_DATA], max_length=10, description="Types of validation to perform"
    )
    file_path: Optional[str] = Field(default=None, max_length=1000, description="File path for validation")
    dataset_type: str = Field(default="default", max_length=100, description="Dataset type for benchmarks")
    benchmarks: Optional[ValidationBenchmarks] = Field(default=None, description="Custom validation benchmarks")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional validation context")

    @field_validator("dataset_id")
    @classmethod
    def validate_dataset_id(cls: Type["ValidationRequest"], v: str) -> str:
        """Validate dataset ID."""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Dataset ID must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls: Type["ValidationRequest"], v: Optional[str]) -> Optional[str]:
        """Validate file path."""
        if v is not None:
            v = sanitize_string(v)
            # Basic path validation - no path traversal
            if ".." in v or v.startswith("/etc/") or v.startswith("/var/"):
                raise ValueError("Invalid file path")
        return v

    @field_validator("dataset_type")
    @classmethod
    def validate_dataset_type(cls: Type["ValidationRequest"], v: str) -> str:
        """Validate dataset type."""
        v = sanitize_string(v)
        allowed_types = ["default", "OllaGen1", "Garak", "DocMath", "GraphWalk", "ConfAIde", "JudgeBench", "custom"]
        if v not in allowed_types:
            raise ValueError(f"Dataset type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator("validation_types")
    @classmethod
    def validate_validation_types(
        cls: Type["ValidationRequest"], v: List[ValidationTypeEnum]
    ) -> List[ValidationTypeEnum]:
        """Validate validation types list."""
        if len(v) == 0:
            raise ValueError("At least one validation type must be specified")
        if len(v) > 10:
            raise ValueError("Too many validation types specified")
        # Remove duplicates while preserving order
        seen = set()
        result = []
        for x in v:
            if x not in seen:
                seen.add(x)
                result.append(x)
        return result


class ValidationResponse(BaseModel):
    """Response schema for dataset validation."""

    validation_id: str = Field(..., description="Unique validation ID")
    dataset_id: str = Field(..., description="Dataset ID that was validated")
    status: str = Field(..., description="Overall validation status")
    overall_result: ValidationStatusEnum = Field(..., description="Overall validation result")
    validation_level: ValidationLevelEnum = Field(..., description="Validation level used")
    results: List[ValidationResultSchema] = Field(..., description="Individual validation results")
    summary: str = Field(..., description="Validation summary")
    total_execution_time_ms: float = Field(..., ge=0, description="Total execution time")
    timestamp: datetime = Field(..., description="Validation completion timestamp")

    # Performance and statistics
    performance_metrics: Optional[PerformanceMetrics] = Field(default=None, description="Performance metrics")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Validation statistics")

    # Error information
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")

    @field_validator("validation_id", "dataset_id")
    @classmethod
    def validate_ids(cls: Type["ValidationResponse"], v: str) -> str:
        """Validate ID fields."""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("ID must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls: Type["ValidationResponse"], v: str) -> str:
        """Validate status field."""
        v = sanitize_string(v).lower()
        allowed_statuses = ["pending", "running", "completed", "failed", "cancelled"]
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of: {', '.join(allowed_statuses)}")
        return v

    @field_validator("summary")
    @classmethod
    def validate_summary(cls: Type["ValidationResponse"], v: str) -> str:
        """Validate summary field."""
        return sanitize_string(v)


class ValidationHistoryEntry(BaseModel):
    """Schema for validation history entries."""

    validation_id: str = Field(..., description="Validation ID")
    dataset_id: str = Field(..., description="Dataset ID")
    validation_level: ValidationLevelEnum = Field(..., description="Validation level")
    overall_result: ValidationStatusEnum = Field(..., description="Overall result")
    timestamp: datetime = Field(..., description="Validation timestamp")
    execution_time_ms: float = Field(..., ge=0, description="Execution time")
    validation_types: List[ValidationTypeEnum] = Field(..., description="Types validated")
    summary: str = Field(..., description="Brief summary")


class ValidationHistoryResponse(BaseModel):
    """Response schema for validation history."""

    validations: List[ValidationHistoryEntry] = Field(..., description="List of validation history entries")
    total: int = Field(..., ge=0, description="Total number of validations")
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=50, ge=1, le=1000, description="Page size")
    has_next: bool = Field(..., description="Whether there are more pages")


class ValidationStatsResponse(BaseModel):
    """Response schema for validation statistics."""

    total_validations: int = Field(..., ge=0, description="Total validations performed")
    successful_validations: int = Field(..., ge=0, description="Successful validations")
    failed_validations: int = Field(..., ge=0, description="Failed validations")
    warnings: int = Field(..., ge=0, description="Validations with warnings")

    average_execution_time_ms: float = Field(..., ge=0, description="Average execution time")
    peak_memory_usage_mb: float = Field(..., ge=0, description="Peak memory usage")

    validation_types: Dict[str, int] = Field(..., description="Count by validation type")
    dataset_types: Dict[str, int] = Field(..., description="Count by dataset type")
    status_distribution: Dict[str, int] = Field(..., description="Status distribution")

    last_updated: datetime = Field(..., description="Last statistics update")


class ValidationConfigRequest(BaseModel):
    """Request schema for validation configuration."""

    dataset_type: str = Field(..., max_length=100, description="Dataset type")
    benchmarks: ValidationBenchmarks = Field(..., description="Validation benchmarks")
    enabled_validators: List[str] = Field(..., max_length=20, description="Enabled validators")
    default_level: ValidationLevelEnum = Field(default=ValidationLevelEnum.FULL, description="Default validation level")

    @field_validator("dataset_type")
    @classmethod
    def validate_dataset_type(cls: Type["ValidationConfigRequest"], v: str) -> str:
        """Validate dataset type."""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Dataset type must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @field_validator("enabled_validators")
    @classmethod
    def validate_enabled_validators(cls: Type["ValidationConfigRequest"], v: List[str]) -> List[str]:
        """Validate enabled validators list."""
        validated = []
        for validator in v:
            validator = sanitize_string(validator)
            if not ValidationPatterns.SAFE_IDENTIFIER.match(validator):
                raise ValueError(f"Invalid validator name: {validator}")
            validated.append(validator)
        return validated


class ValidationConfigResponse(BaseModel):
    """Response schema for validation configuration."""

    dataset_type: str = Field(..., description="Dataset type")
    benchmarks: ValidationBenchmarks = Field(..., description="Current benchmarks")
    enabled_validators: List[str] = Field(..., description="Currently enabled validators")
    default_level: ValidationLevelEnum = Field(..., description="Default validation level")
    available_validators: List[str] = Field(..., description="Available validators")
    last_updated: datetime = Field(..., description="Last configuration update")


# Error response schemas


class ValidationError(BaseModel):
    """Error response for validation operations."""

    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(default=None, description="Additional error details")
    validation_id: Optional[str] = Field(default=None, description="Validation ID if applicable")
    dataset_id: Optional[str] = Field(default=None, description="Dataset ID if applicable")
    error_code: Optional[str] = Field(default=None, description="Error code for programmatic handling")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested fixes or alternatives")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class ValidationServiceStatus(BaseModel):
    """Status of the validation service."""

    status: str = Field(..., description="Service status")
    available_validators: List[str] = Field(..., description="Available validators")
    total_validations: int = Field(..., ge=0, description="Total validations performed")
    active_validations: int = Field(..., ge=0, description="Currently active validations")
    service_uptime_seconds: float = Field(..., ge=0, description="Service uptime")
    memory_usage_mb: float = Field(..., ge=0, description="Current memory usage")
    last_validation: Optional[datetime] = Field(default=None, description="Last validation timestamp")
