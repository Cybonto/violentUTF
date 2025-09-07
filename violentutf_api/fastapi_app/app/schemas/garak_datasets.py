# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for Garak dataset converter functionality.

Supports Issue #121 - Garak Dataset Converter implementation with
comprehensive data validation and type safety.

SECURITY: Enhanced with comprehensive input validation to prevent injection attacks.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from app.core.validation import (
    SecurityLimits,
    ValidationPatterns,
    sanitize_string,
)
from pydantic import BaseModel, Field, field_validator

# --- Enums ---


class GarakFileType(str, Enum):
    """Garak file types based on content analysis."""

    DAN_VARIANT = "dan_variant"
    RTP_CATEGORY = "rtp_category"
    INJECTION_ATTACK = "injection_attack"
    JAILBREAK_PROMPT = "jailbreak_prompt"
    UNKNOWN = "unknown"


class AttackType(str, Enum):
    """Attack types for prompt classification."""

    # Legacy naming for compatibility with tests
    DAN = "dan_variant"
    RTP = "rtp_category"
    INJECTION = "injection_attack"
    JAILBREAK = "jailbreak_prompt"

    # Detailed attack types
    ROLE_PLAYING = "role_playing"
    AUTHORITY_IMPERSONATION = "authority_impersonation"
    EMOTIONAL_MANIPULATION = "emotional_manipulation"
    TECHNICAL_JAILBREAK = "technical_jailbreak"
    SYSTEM_BYPASS = "system_bypass"
    INSTRUCTION_OVERRIDE = "instruction_override"
    SOCIAL_ENGINEERING = "social_engineering"
    UNKNOWN = "unknown"


class HarmCategory(str, Enum):
    """Harm categories for prompt classification."""

    # Legacy naming for compatibility with tests
    JAILBREAK = "jailbreak"

    # Detailed harm categories
    MANIPULATION = "manipulation"
    DECEPTION = "deception"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SYSTEM_BYPASS = "system_bypass"
    INSTRUCTION_OVERRIDE = "instruction_override"
    SOCIAL_ENGINEERING = "social_engineering"
    MALWARE = "malware"
    THREAT = "threat"
    TOXICITY = "toxicity"


class ConversionStrategy(str, Enum):
    """Conversion strategies for different file types."""

    SINGLE_PROMPT = "single_prompt"
    MULTI_PROMPT = "multi_prompt"
    TEMPLATE_BASED = "template_based"
    STRUCTURED_PARSING = "structured_parsing"


# --- Base Models ---


class FileAnalysisResult(BaseModel):
    """Result of Garak file structure analysis."""

    file_type: GarakFileType = Field(..., description="Detected file type")
    content_type: str = Field(..., description="Content classification")
    prompt_count: int = Field(..., ge=0, description="Number of prompts detected")
    has_template_variables: bool = Field(..., description="Whether file contains template variables")
    template_variables: List[str] = Field(default=[], description="List of detected template variables")
    detected_patterns: List[str] = Field(default=[], description="List of detected attack patterns")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence score")
    analysis_metadata: Dict[str, Any] = Field(default={}, description="Additional analysis metadata")


class TemplateInfo(BaseModel):
    """Information about template variables in prompts."""

    variables: List[str] = Field(..., description="List of template variables")
    variable_count: int = Field(..., ge=0, description="Number of template variables")
    extraction_success: bool = Field(..., description="Whether extraction succeeded")
    has_nested_variables: bool = Field(default=False, description="Whether nested variables detected")
    malformed_patterns: List[str] = Field(default=[], description="List of malformed variable patterns")
    variable_metadata: Dict[str, Any] = Field(default={}, description="Additional variable metadata")


class AttackMetadata(BaseModel):
    """Metadata about attack classification."""

    attack_type: AttackType = Field(..., description="Primary attack type")
    harm_categories: List[HarmCategory] = Field(..., description="List of harm categories")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    severity_level: int = Field(..., ge=1, le=5, description="Attack severity level (1-5)")
    detection_patterns: List[str] = Field(default=[], description="Patterns that triggered classification")
    classification_metadata: Dict[str, Any] = Field(default={}, description="Additional classification data")


class ValidationResult(BaseModel):
    """Result of conversion validation."""

    integrity_check_passed: bool = Field(..., description="Whether data integrity check passed")
    prompt_preservation_rate: float = Field(..., ge=0.0, le=1.0, description="Prompt preservation rate")
    data_loss_count: int = Field(..., ge=0, description="Number of prompts lost during conversion")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall conversion quality score")
    validation_errors: List[str] = Field(default=[], description="List of validation errors")
    validation_warnings: List[str] = Field(default=[], description="List of validation warnings")
    validation_metadata: Dict[str, Any] = Field(default={}, description="Additional validation data")


# --- Request/Response Models ---


class GarakConversionRequest(BaseModel):
    """Request for Garak dataset conversion."""

    file_paths: List[str] = Field(..., min_items=1, max_items=100, description="List of Garak file paths to convert")
    output_dataset_name: str = Field(
        ...,
        min_length=3,
        max_length=SecurityLimits.MAX_NAME_LENGTH,
        description="Name for the output SeedPromptDataset",
    )
    conversion_strategy: Optional[ConversionStrategy] = Field(None, description="Override automatic strategy detection")
    include_template_variables: bool = Field(default=True, description="Whether to preserve template variables")
    enable_attack_classification: bool = Field(default=True, description="Whether to classify attack types")
    enable_validation: bool = Field(default=True, description="Whether to validate conversion quality")
    batch_size: int = Field(default=10, ge=1, le=50, description="Number of files to process in parallel")

    @field_validator("file_paths")
    @classmethod
    def validate_file_paths(cls: Type["GarakConversionRequest"], v: List[str]) -> List[str]:
        """Validate file paths for security."""
        validated = []
        for path in v:
            if not isinstance(path, str):
                raise ValueError("File path must be a string")
            path = sanitize_string(path)
            if len(path) > SecurityLimits.MAX_PATH_LENGTH:
                raise ValueError("File path too long")
            # Additional path validation would go here
            validated.append(path)
        return validated

    @field_validator("output_dataset_name")
    @classmethod
    def validate_output_dataset_name(cls: Type["GarakConversionRequest"], v: str) -> str:
        """Validate dataset name."""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Dataset name must contain only safe characters")
        return v


class GarakConversionResult(BaseModel):
    """Result of Garak dataset conversion."""

    success: bool = Field(..., description="Whether conversion succeeded")
    dataset: Optional[Dict[str, Any]] = Field(None, description="Converted SeedPromptDataset")
    file_results: List[Dict[str, Any]] = Field(default=[], description="Per-file conversion results")
    total_prompts_converted: int = Field(..., ge=0, description="Total number of prompts converted")
    conversion_time_seconds: float = Field(..., ge=0.0, description="Total conversion time")
    metadata: Dict[str, Any] = Field(default={}, description="Conversion metadata")
    validation_result: Optional[ValidationResult] = Field(None, description="Validation results")
    errors: List[str] = Field(default=[], description="List of conversion errors")
    warnings: List[str] = Field(default=[], description="List of conversion warnings")


class SingleFileConversionResult(BaseModel):
    """Result of converting a single Garak file."""

    file_path: str = Field(..., description="Path to the converted file")
    success: bool = Field(..., description="Whether file conversion succeeded")
    dataset: Optional[Dict[str, Any]] = Field(None, description="Converted prompts from this file")
    file_analysis: FileAnalysisResult = Field(..., description="File analysis results")
    template_info: Optional[TemplateInfo] = Field(None, description="Template variable information")
    attack_classifications: List[AttackMetadata] = Field(default=[], description="Attack classifications")
    conversion_time_seconds: float = Field(..., ge=0.0, description="File conversion time")
    error_message: Optional[str] = Field(None, description="Error message if conversion failed")


class GarakBatchConversionRequest(BaseModel):
    """Request for batch conversion of Garak files."""

    directory_path: str = Field(
        ..., min_length=1, max_length=SecurityLimits.MAX_PATH_LENGTH, description="Directory containing Garak files"
    )
    file_pattern: str = Field(default="*.txt", description="File pattern to match")
    output_dataset_prefix: str = Field(..., min_length=3, max_length=50, description="Prefix for output dataset names")
    max_files_per_dataset: int = Field(default=25, ge=1, le=100, description="Maximum files per dataset")
    parallel_processing: bool = Field(default=True, description="Whether to process files in parallel")

    @field_validator("directory_path")
    @classmethod
    def validate_directory_path(cls: Type["GarakBatchConversionRequest"], v: str) -> str:
        """Validate directory path."""
        v = sanitize_string(v)
        if len(v) > SecurityLimits.MAX_PATH_LENGTH:
            raise ValueError("Directory path too long")
        return v

    @field_validator("output_dataset_prefix")
    @classmethod
    def validate_output_dataset_prefix(cls: Type["GarakBatchConversionRequest"], v: str) -> str:
        """Validate dataset prefix."""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Dataset prefix must contain only safe characters")
        return v


class GarakBatchConversionResult(BaseModel):
    """Result of batch Garak conversion."""

    success: bool = Field(..., description="Whether batch conversion succeeded")
    datasets_created: List[Dict[str, Any]] = Field(default=[], description="List of created datasets")
    total_files_processed: int = Field(..., ge=0, description="Total files processed")
    total_prompts_converted: int = Field(..., ge=0, description="Total prompts converted")
    processing_time_seconds: float = Field(..., ge=0.0, description="Total processing time")
    file_results: List[SingleFileConversionResult] = Field(default=[], description="Per-file results")
    summary_statistics: Dict[str, Any] = Field(default={}, description="Conversion statistics")
    errors: List[str] = Field(default=[], description="List of batch conversion errors")


class GarakFileValidationRequest(BaseModel):
    """Request to validate Garak files before conversion."""

    file_paths: List[str] = Field(..., min_items=1, max_items=100, description="List of file paths to validate")
    validation_level: str = Field(default="standard", description="Validation level (basic, standard, strict)")

    @field_validator("file_paths")
    @classmethod
    def validate_file_paths(cls: Type["GarakFileValidationRequest"], v: List[str]) -> List[str]:
        """Validate file paths."""
        validated = []
        for path in v:
            path = sanitize_string(path)
            if len(path) > SecurityLimits.MAX_PATH_LENGTH:
                raise ValueError("File path too long")
            validated.append(path)
        return validated


class GarakFileValidationResult(BaseModel):
    """Result of Garak file validation."""

    file_path: str = Field(..., description="Validated file path")
    is_valid: bool = Field(..., description="Whether file is valid for conversion")
    file_type: GarakFileType = Field(..., description="Detected file type")
    estimated_prompts: int = Field(..., ge=0, description="Estimated number of prompts")
    validation_score: float = Field(..., ge=0.0, le=1.0, description="Validation score")
    issues_found: List[str] = Field(default=[], description="List of validation issues")
    recommendations: List[str] = Field(default=[], description="List of recommendations")
    validation_metadata: Dict[str, Any] = Field(default={}, description="Additional validation data")


class GarakConverterStats(BaseModel):
    """Statistics about Garak converter usage."""

    total_files_converted: int = Field(..., ge=0, description="Total files converted")
    total_prompts_generated: int = Field(..., ge=0, description="Total prompts generated")
    conversion_success_rate: float = Field(..., ge=0.0, le=1.0, description="Conversion success rate")
    average_conversion_time: float = Field(..., ge=0.0, description="Average conversion time per file")
    file_type_distribution: Dict[str, int] = Field(default={}, description="Distribution of file types")
    attack_type_distribution: Dict[str, int] = Field(default={}, description="Distribution of attack types")
    most_common_errors: List[Dict[str, Any]] = Field(default=[], description="Most common conversion errors")
    performance_metrics: Dict[str, Any] = Field(default={}, description="Performance metrics")


class GarakConverterConfig(BaseModel):
    """Configuration for Garak dataset converter."""

    max_file_size_mb: int = Field(default=10, ge=1, le=100, description="Maximum file size in MB")
    max_parallel_files: int = Field(default=5, ge=1, le=20, description="Maximum parallel file processing")
    template_variable_patterns: List[str] = Field(
        default=["{{.*?}}", "\\{\\{.*?\\}\\}"], description="Regex patterns for template variables"
    )
    attack_classification_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Minimum confidence for attack classification"
    )
    enable_performance_monitoring: bool = Field(default=True, description="Whether to monitor performance metrics")
    enable_detailed_logging: bool = Field(default=False, description="Whether to enable detailed logging")
    validation_strictness: str = Field(default="standard", description="Validation strictness level")


# --- Advanced Models ---


class GarakPromptMetadata(BaseModel):
    """Enhanced metadata for converted Garak prompts."""

    source_file: str = Field(..., description="Source file name")
    file_type: GarakFileType = Field(..., description="Source file type")
    attack_type: AttackType = Field(..., description="Classified attack type")
    harm_categories: List[HarmCategory] = Field(..., description="Harm categories")
    severity_level: int = Field(..., ge=1, le=5, description="Severity level")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    template_variables: List[str] = Field(default=[], description="Template variables found")
    conversion_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Conversion timestamp")
    conversion_strategy: ConversionStrategy = Field(..., description="Strategy used for conversion")
    prompt_index: int = Field(..., ge=0, description="Index within source file")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Prompt quality score")
    validation_passed: bool = Field(..., description="Whether prompt passed validation")


class GarakDatasetMetadata(BaseModel):
    """Enhanced metadata for converted Garak datasets."""

    dataset_name: str = Field(..., description="Dataset name")
    source_files: List[str] = Field(..., description="List of source files")
    total_prompts: int = Field(..., ge=0, description="Total number of prompts")
    conversion_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Conversion timestamp")
    converter_version: str = Field(default="1.0.0", description="Converter version")
    file_type_distribution: Dict[str, int] = Field(default={}, description="Distribution of source file types")
    attack_type_distribution: Dict[str, int] = Field(default={}, description="Distribution of attack types")
    quality_metrics: Dict[str, float] = Field(default={}, description="Quality metrics")
    validation_summary: Dict[str, Any] = Field(default={}, description="Validation summary")
    processing_time_seconds: float = Field(..., ge=0.0, description="Total processing time")


# --- Error Models ---


class GarakConversionError(BaseModel):
    """Error information for Garak conversion failures."""

    error_type: str = Field(..., description="Type of conversion error")
    error_message: str = Field(..., description="Detailed error message")
    file_path: Optional[str] = Field(None, description="File path where error occurred")
    error_code: str = Field(..., description="Error code for programmatic handling")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    recovery_suggestions: List[str] = Field(default=[], description="Suggested recovery actions")
    error_metadata: Dict[str, Any] = Field(default={}, description="Additional error context")
