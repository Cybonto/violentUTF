# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for OllaGen1 dataset converter (Issue #123).

Implements Strategy 1 converter schemas for transforming OllaGen1 cognitive behavioral
assessment data into PyRIT QuestionAnsweringDataset format.

SECURITY: Enhanced with comprehensive input validation to prevent injection attacks.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from app.core.validation import (
    SecurityLimits,
    ValidationPatterns,
    sanitize_string,
    validate_json_data,
)
from pydantic import BaseModel, Field, field_validator


class QuestionType(str, Enum):
    """OllaGen1 question types for cognitive assessment."""

    WCP = "WCP"  # Which Cognitive Path
    WHO = "WHO"  # Compliance Comparison
    TEAM_RISK = "TeamRisk"  # Team Dynamics
    TARGET_FACTOR = "TargetFactor"  # Intervention


class AssessmentCategory(str, Enum):
    """Assessment categories for question types."""

    COGNITIVE_ASSESSMENT = "cognitive_assessment"
    RISK_EVALUATION = "risk_evaluation"
    TEAM_ASSESSMENT = "team_assessment"
    INTERVENTION_ASSESSMENT = "intervention_assessment"


class PersonProfile(BaseModel):
    """Person profile data from OllaGen1 scenarios."""

    name: str = Field(..., description="Person name")
    cognitive_path: str = Field(..., description="Cognitive approach pattern")
    profile: str = Field(..., description="Behavioral profile description")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk assessment score")
    risk_profile: str = Field(..., description="Risk profile category")

    @field_validator("name", "cognitive_path", "profile", "risk_profile")
    @classmethod
    def validate_string_fields(cls: Type["PersonProfile"], v: str) -> str:
        """Validate and sanitize string fields."""
        if not v:
            raise ValueError("Field cannot be empty")
        sanitized = sanitize_string(v)
        if len(sanitized) > 100:
            raise ValueError("Field too long")
        return sanitized


class ScenarioMetadata(BaseModel):
    """Complete scenario metadata from OllaGen1 CSV row."""

    scenario_id: str = Field(..., description="Unique scenario identifier")
    person_1: PersonProfile = Field(..., description="First person profile")
    person_2: PersonProfile = Field(..., description="Second person profile")
    shared_risk_factor: str = Field(..., description="Shared risk factor between persons")
    targeted_factor: str = Field(..., description="Targeted factor for intervention")
    combined_risk_score: float = Field(..., ge=0.0, le=100.0, description="Combined risk assessment")
    conversion_timestamp: datetime = Field(..., description="Conversion processing timestamp")
    conversion_strategy: str = Field(
        default="strategy_1_cognitive_assessment", description="Conversion strategy identifier"
    )

    @field_validator("scenario_id")
    @classmethod
    def validate_scenario_id(cls: Type["ScenarioMetadata"], v: str) -> str:
        """Validate scenario ID format."""
        v = sanitize_string(v)
        if not re.match(r"^SC\d{3,6}$", v):
            raise ValueError("Scenario ID must match format SC### (e.g., SC001)")
        return v

    @field_validator("shared_risk_factor", "targeted_factor")
    @classmethod
    def validate_factor_fields(cls: Type["ScenarioMetadata"], v: str) -> str:
        """Validate risk factor fields."""
        if not v:
            raise ValueError("Factor field cannot be empty")
        sanitized = sanitize_string(v)
        if len(sanitized) > 200:
            raise ValueError("Factor description too long")
        return sanitized


class QuestionAnsweringEntry(BaseModel):
    """PyRIT-compliant QuestionAnsweringEntry for OllaGen1 conversion."""

    question: str = Field(..., description="Question text with multiple choice options")
    answer_type: str = Field(default="int", description="Answer type (always 'int' for multiple choice indices)")
    correct_answer: int = Field(..., ge=0, le=3, description="Index of correct choice (0-3)")
    choices: List[str] = Field(..., min_length=2, max_length=4, description="Multiple choice options")
    metadata: Dict[str, Any] = Field(..., description="Question and scenario metadata")

    @field_validator("question")
    @classmethod
    def validate_question(cls: Type["QuestionAnsweringEntry"], v: str) -> str:
        """Validate question text."""
        if not v or len(v.strip()) < 10:
            raise ValueError("Question too short")
        sanitized = sanitize_string(v)
        if len(sanitized) > SecurityLimits.MAX_DESCRIPTION_LENGTH:
            raise ValueError("Question too long")
        return sanitized

    @field_validator("answer_type")
    @classmethod
    def validate_answer_type(cls: Type["QuestionAnsweringEntry"], v: str) -> str:
        """Validate answer type (must be 'int' for multiple choice)."""
        if v != "int":
            raise ValueError("Answer type must be 'int' for multiple choice questions")
        return v

    @field_validator("choices")
    @classmethod
    def validate_choices(cls: Type["QuestionAnsweringEntry"], v: List[str]) -> List[str]:
        """Validate multiple choice options."""
        if len(v) < 2 or len(v) > 4:
            raise ValueError("Must have 2-4 choice options")

        validated = []
        for choice in v:
            if not isinstance(choice, str) or not choice.strip():
                raise ValueError("All choices must be non-empty strings")
            sanitized = sanitize_string(choice)
            if len(sanitized) > 200:
                raise ValueError("Choice option too long")
            validated.append(sanitized)

        return validated

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls: Type["QuestionAnsweringEntry"], v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata structure."""
        if not v:
            raise ValueError("Metadata cannot be empty")

        # Required metadata fields for OllaGen1
        required_fields = ["scenario_id", "question_type", "category", "conversion_strategy", "conversion_timestamp"]

        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required metadata field: {field}")

        return validate_json_data(v, max_depth=4)

    def model_post_init(self, __context: object) -> None:
        """Post-initialization validation."""
        # Verify correct_answer is within choices range
        if self.correct_answer >= len(self.choices):
            raise ValueError(
                f"Correct answer index {self.correct_answer} is out of range " f"for {len(self.choices)} choices"
            )


class MultipleChoiceExtractionResult(BaseModel):
    """Result of multiple choice extraction from question text."""

    choices: List[str] = Field(..., description="Extracted choice options")
    extraction_successful: bool = Field(..., description="Whether extraction succeeded")
    extraction_method: str = Field(..., description="Method used for extraction")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence")
    malformed_patterns: List[str] = Field(default_factory=list, description="Any malformed patterns detected")


class AnswerMappingResult(BaseModel):
    """Result of mapping answer text to choice index."""

    mapped_index: int = Field(..., ge=0, description="Mapped choice index")
    mapping_successful: bool = Field(..., description="Whether mapping succeeded")
    mapping_method: str = Field(..., description="Method used for mapping")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Mapping confidence")
    original_answer_text: str = Field(..., description="Original answer text")


class OllaGen1ConversionResult(BaseModel):
    """Result of converting a single OllaGen1 CSV row."""

    scenario_id: str = Field(..., description="Source scenario ID")
    success: bool = Field(..., description="Whether conversion succeeded")
    qa_entries: List[QuestionAnsweringEntry] = Field(
        default_factory=list, description="Generated QuestionAnswering entries"
    )
    conversion_time_seconds: float = Field(..., description="Time taken for conversion")
    scenario_metadata: Optional[ScenarioMetadata] = Field(default=None, description="Extracted scenario metadata")
    error_message: Optional[str] = Field(default=None, description="Error message if conversion failed")
    quality_metrics: Dict[str, Any] = Field(default_factory=dict, description="Quality metrics for the conversion")

    @field_validator("qa_entries")
    @classmethod
    def validate_qa_entries(
        cls: Type["OllaGen1ConversionResult"], v: List[QuestionAnsweringEntry]
    ) -> List[QuestionAnsweringEntry]:
        """Validate Q&A entries list."""
        if len(v) > 4:
            raise ValueError("Cannot have more than 4 Q&A entries per scenario")

        # Check for duplicate question types
        question_types = []
        for entry in v:
            q_type = entry.metadata.get("question_type")
            if q_type in question_types:
                raise ValueError(f"Duplicate question type: {q_type}")
            question_types.append(q_type)

        return v


class OllaGen1BatchConversionResult(BaseModel):
    """Result of batch conversion of OllaGen1 scenarios."""

    total_scenarios_processed: int = Field(..., description="Total scenarios processed")
    successful_conversions: int = Field(..., description="Number of successful conversions")
    failed_conversions: int = Field(..., description="Number of failed conversions")
    total_qa_entries_generated: int = Field(..., description="Total Q&A entries created")
    batch_conversion_time_seconds: float = Field(..., description="Total batch processing time")
    average_scenarios_per_second: float = Field(..., description="Processing throughput")
    memory_peak_mb: float = Field(..., description="Peak memory usage in MB")
    quality_summary: Dict[str, Any] = Field(..., description="Overall quality metrics")
    error_summary: Dict[str, List[str]] = Field(default_factory=dict, description="Summary of errors by type")

    success_rate: Optional[float] = Field(default=None, description="Conversion success rate")

    def model_post_init(self, __context: object) -> None:
        """Calculate derived metrics."""
        if self.total_scenarios_processed > 0:
            self.success_rate = self.successful_conversions / self.total_scenarios_processed
        else:
            self.success_rate = 0.0


class OllaGen1ValidationResult(BaseModel):
    """Validation result for OllaGen1 conversion quality."""

    integrity_check_passed: bool = Field(..., description="Data integrity validation")
    data_preservation_rate: float = Field(..., ge=0.0, le=1.0, description="Data preservation score")
    metadata_completeness_score: float = Field(..., ge=0.0, le=1.0, description="Metadata completeness")
    choice_extraction_accuracy: float = Field(..., ge=0.0, le=1.0, description="Choice extraction accuracy")
    answer_mapping_accuracy: float = Field(..., ge=0.0, le=1.0, description="Answer mapping accuracy")
    pyrit_format_compliance: bool = Field(..., description="PyRIT format compliance")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors")
    validation_warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    validation_timestamp: datetime = Field(..., description="Validation timestamp")


class OllaGen1ManifestInfo(BaseModel):
    """Manifest file information for OllaGen1 split files."""

    dataset_name: str = Field(..., description="Dataset name")
    version: str = Field(..., description="Dataset version")
    total_scenarios: int = Field(..., gt=0, description="Total number of scenarios")
    expected_qa_entries: int = Field(..., gt=0, description="Expected Q&A entries count")
    split_files: List[Dict[str, Any]] = Field(..., description="Split file information")
    schema: Dict[str, Any] = Field(..., description="Data schema definition")
    question_types: Dict[str, Any] = Field(..., description="Question type specifications")
    conversion_requirements: Optional[Dict[str, Any]] = Field(default=None, description="Conversion requirements")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")

    @field_validator("dataset_name")
    @classmethod
    def validate_dataset_name(cls: Type["OllaGen1ManifestInfo"], v: str) -> str:
        """Validate dataset name."""
        if not v or not v.startswith("OllaGen1"):
            raise ValueError("Dataset name must start with 'OllaGen1'")
        return sanitize_string(v)

    @field_validator("expected_qa_entries")
    @classmethod
    def validate_qa_entries_count(cls: Type["OllaGen1ManifestInfo"], v: int, info: object) -> int:
        """Validate expected Q&A entries count."""
        values = info.data if info else {}
        total_scenarios = values.get("total_scenarios", 0)
        if total_scenarios > 0 and v != total_scenarios * 4:
            raise ValueError(f"Expected Q&A entries ({v}) should be 4x scenarios ({total_scenarios})")
        return v


class OllaGen1ConversionConfig(BaseModel):
    """Configuration for OllaGen1 conversion process."""

    batch_size: int = Field(default=1000, gt=0, le=10000, description="Batch processing size")
    enable_progress_tracking: bool = Field(default=True, description="Enable progress updates")
    enable_validation: bool = Field(default=True, description="Enable conversion validation")
    max_memory_usage_gb: float = Field(default=2.0, gt=0, le=16, description="Maximum memory usage")
    target_throughput_per_second: int = Field(default=300, gt=0, description="Target processing speed")
    quality_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "min_choice_extraction_accuracy": 0.95,
            "min_answer_mapping_accuracy": 0.98,
            "min_data_preservation_rate": 1.0,
            "min_metadata_completeness": 0.95,
        },
        description="Quality threshold requirements",
    )
    output_format_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "answer_type": "int",
            "choices_per_question": 4,
            "qa_entries_per_scenario": 4,
            "preserve_original_text": True,
        },
        description="Output format configuration",
    )


class OllaGen1ConversionRequest(BaseModel):
    """Request for OllaGen1 dataset conversion."""

    manifest_file_path: str = Field(..., description="Path to manifest file")
    output_dataset_name: str = Field(..., description="Name for converted dataset")
    conversion_config: Optional[OllaGen1ConversionConfig] = Field(
        default_factory=OllaGen1ConversionConfig, description="Conversion configuration"
    )
    save_to_memory: bool = Field(default=True, description="Save to PyRIT memory")
    overwrite_existing: bool = Field(default=False, description="Overwrite if dataset exists")

    @field_validator("manifest_file_path")
    @classmethod
    def validate_manifest_path(cls: Type["OllaGen1ConversionRequest"], v: str) -> str:
        """Validate manifest file path."""
        if not v.endswith((".json", ".yml", ".yaml")):
            raise ValueError("Manifest file must be JSON or YAML format")
        return sanitize_string(v)

    @field_validator("output_dataset_name")
    @classmethod
    def validate_output_name(cls: Type["OllaGen1ConversionRequest"], v: str) -> str:
        """Validate output dataset name."""
        sanitized = sanitize_string(v)
        if not ValidationPatterns.SAFE_NAME.match(sanitized):
            raise ValueError("Dataset name contains invalid characters")
        return sanitized


class OllaGen1ConversionResponse(BaseModel):
    """Response for OllaGen1 dataset conversion."""

    conversion_id: str = Field(..., description="Unique conversion job ID")
    success: bool = Field(..., description="Overall conversion success")
    dataset_name: str = Field(..., description="Name of converted dataset")
    conversion_result: OllaGen1BatchConversionResult = Field(..., description="Detailed results")
    validation_result: Optional[OllaGen1ValidationResult] = Field(
        default=None, description="Validation results if enabled"
    )
    saved_to_memory: bool = Field(..., description="Whether saved to PyRIT memory")
    conversion_timestamp: datetime = Field(..., description="Completion timestamp")
    message: str = Field(..., description="Human-readable result message")
