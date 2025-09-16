# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for LegalBench dataset converter (Issue #126).

Implements LegalBench converter schemas for transforming legal reasoning tasks
from TSV format into PyRIT QuestionAnsweringDataset format across 166 directories.

SECURITY: Enhanced with comprehensive input validation to prevent injection attacks.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, field_validator

from app.core.validation import (
    SecurityLimits,
    sanitize_string,
    validate_json_data,
)


class LegalCategory(str, Enum):
    """Legal domain categories for task classification."""

    CONTRACT = "contract"
    REGULATORY = "regulatory"
    JUDICIAL = "judicial"
    CIVIL = "civil"
    CRIMINAL = "criminal"
    CONSTITUTIONAL = "constitutional"
    CORPORATE = "corporate"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    GENERAL = "general"


class LegalTaskType(str, Enum):
    """Legal task type categories for specialized scoring."""

    REASONING = "reasoning"
    CLASSIFICATION = "classification"
    ANALYSIS = "analysis"
    INTERPRETATION = "interpretation"
    APPLICATION = "application"
    SYNTHESIS = "synthesis"
    EVALUATION = "evaluation"


class LegalComplexity(str, Enum):
    """Legal complexity levels for task assessment."""

    BASIC = "basic"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class QuestionFormat(str, Enum):
    """Legal question format types."""

    MULTIPLE_CHOICE = "multiple_choice"
    BINARY = "binary"
    SHORT_ANSWER = "short_answer"
    EXPLANATION = "explanation"
    ANALYSIS = "analysis"


class LegalSpecialization(BaseModel):
    """Legal specialization information."""

    area: str = Field(..., description="Legal specialization area")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    keywords_matched: List[str] = Field(..., description="Keywords that triggered classification")

    @field_validator("area")
    @classmethod
    def validate_area(cls: Type["LegalSpecialization"], v: str) -> str:
        """Validate specialization area."""
        v = sanitize_string(v)
        if len(v) > 100:
            raise ValueError("Specialization area too long")
        return v

    @field_validator("keywords_matched")
    @classmethod
    def validate_keywords(cls: Type["LegalSpecialization"], v: List[str]) -> List[str]:
        """Validate matched keywords."""
        if len(v) > 20:
            raise ValueError("Too many keywords matched")
        validated = []
        for keyword in v:
            if not isinstance(keyword, str):
                raise ValueError("Keywords must be strings")
            sanitized = sanitize_string(keyword)
            if len(sanitized) > 50:
                raise ValueError("Keyword too long")
            validated.append(sanitized)
        return validated


class LegalClassification(BaseModel):
    """Complete legal domain classification result."""

    primary_category: LegalCategory = Field(..., description="Primary legal category")
    specializations: List[LegalSpecialization] = Field(default=[], description="Legal specialization areas")
    complexity: LegalComplexity = Field(..., description="Legal complexity assessment")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall classification confidence")
    classification_method: str = Field(
        default="keyword_and_content_analysis", description="Classification methodology used"
    )

    @field_validator("specializations")
    @classmethod
    def validate_specializations(
        cls: Type["LegalClassification"], v: List[LegalSpecialization]
    ) -> List[LegalSpecialization]:
        """Validate specializations list."""
        if len(v) > 5:
            raise ValueError("Too many specializations")
        return v


class ProfessionalValidation(BaseModel):
    """Professional validation metadata for legal tasks."""

    validated: bool = Field(default=True, description="Whether professionally validated")
    validator_count: str = Field(default="40+", description="Number of legal professionals involved")
    validation_method: str = Field(default="expert_legal_professional_review", description="Validation methodology")
    validation_scope: str = Field(default="task_design_and_answer_verification", description="Scope of validation")
    expertise_areas: List[str] = Field(default=[], description="Legal expertise areas of validators")
    confidence: str = Field(default="high", description="Validation confidence level")
    institution: str = Field(default="Stanford University", description="Academic institution")
    validation_year: str = Field(default="2023", description="Year of validation")
    peer_reviewed: bool = Field(default=True, description="Whether peer reviewed")

    @field_validator("expertise_areas")
    @classmethod
    def validate_expertise_areas(cls: Type["ProfessionalValidation"], v: List[str]) -> List[str]:
        """Validate expertise areas."""
        if len(v) > 10:
            raise ValueError("Too many expertise areas")
        validated = []
        for area in v:
            if not isinstance(area, str):
                raise ValueError("Expertise area must be string")
            sanitized = sanitize_string(area)
            if len(sanitized) > 100:
                raise ValueError("Expertise area too long")
            validated.append(sanitized)
        return validated


class TaskMetadata(BaseModel):
    """Metadata for individual legal tasks."""

    task_name: str = Field(..., description="Legal task directory name")
    task_id: str = Field(..., description="Unique task identifier")
    legal_classification: LegalClassification = Field(..., description="Legal domain classification")
    split: str = Field(..., description="Train/test split designation")
    row_number: int = Field(..., ge=0, description="Row number in TSV file")
    professional_validation: ProfessionalValidation = Field(..., description="Professional validation metadata")
    question_format: QuestionFormat = Field(..., description="Question format type")
    legal_context: Dict[str, str] = Field(default={}, description="Legal context information")
    source_file: str = Field(..., description="Source TSV file path")
    processing_timestamp: datetime = Field(..., description="Processing timestamp")

    @field_validator("task_name")
    @classmethod
    def validate_task_name(cls: Type["TaskMetadata"], v: str) -> str:
        """Validate task name."""
        v = sanitize_string(v)
        if not v:
            raise ValueError("Task name cannot be empty")
        if len(v) > 200:
            raise ValueError("Task name too long")
        return v

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls: Type["TaskMetadata"], v: str) -> str:
        """Validate task ID."""
        v = sanitize_string(v)
        if not v:
            raise ValueError("Task ID cannot be empty")
        if len(v) > 100:
            raise ValueError("Task ID too long")
        return v

    @field_validator("split")
    @classmethod
    def validate_split(cls: Type["TaskMetadata"], v: str) -> str:
        """Validate split designation."""
        v = sanitize_string(v).lower()
        if v not in ["train", "test"]:
            raise ValueError("Split must be 'train' or 'test'")
        return v

    @field_validator("legal_context")
    @classmethod
    def validate_legal_context(cls: Type["TaskMetadata"], v: Dict[str, str]) -> Dict[str, str]:
        """Validate legal context."""
        if len(v) > 20:
            raise ValueError("Too many context fields")
        validated = {}
        for key, value in v.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Context keys and values must be strings")
            key = sanitize_string(key)
            value = sanitize_string(value)
            if len(key) > 100 or len(value) > 500:
                raise ValueError("Context field too long")
            validated[key] = value
        return validated

    @field_validator("source_file")
    @classmethod
    def validate_source_file(cls: Type["TaskMetadata"], v: str) -> str:
        """Validate source file path."""
        v = sanitize_string(v)
        if not v:
            raise ValueError("Source file cannot be empty")
        if len(v) > 500:
            raise ValueError("Source file path too long")
        return v


class QuestionAnsweringEntry(BaseModel):
    """PyRIT-compliant QuestionAnsweringEntry for LegalBench conversion."""

    question: str = Field(..., description="Legal question with context")
    answer_type: str = Field(..., description="Answer type (int, str, bool)")
    correct_answer: Any = Field(..., description="Correct answer (type depends on answer_type)")
    choices: Optional[List[str]] = Field(default=None, description="Multiple choice options if applicable")
    metadata: TaskMetadata = Field(..., description="Complete task and legal metadata")

    @field_validator("question")
    @classmethod
    def validate_question(cls: Type["QuestionAnsweringEntry"], v: str) -> str:
        """Validate legal question."""
        if not v or len(v.strip()) < 10:
            raise ValueError("Legal question too short")
        sanitized = sanitize_string(v)
        if len(sanitized) > SecurityLimits.MAX_DESCRIPTION_LENGTH:
            raise ValueError("Legal question too long")
        return sanitized

    @field_validator("answer_type")
    @classmethod
    def validate_answer_type(cls: Type["QuestionAnsweringEntry"], v: str) -> str:
        """Validate answer type."""
        v = sanitize_string(v).lower()
        allowed_types = ["int", "str", "bool", "float"]
        if v not in allowed_types:
            raise ValueError(f"Answer type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator("choices")
    @classmethod
    def validate_choices(cls: Type["QuestionAnsweringEntry"], v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate multiple choice options."""
        if v is None:
            return v

        if len(v) < 2 or len(v) > 6:
            raise ValueError("Must have 2-6 choice options for multiple choice")

        validated = []
        for choice in v:
            if not isinstance(choice, str) or not choice.strip():
                raise ValueError("All choices must be non-empty strings")
            sanitized = sanitize_string(choice)
            if len(sanitized) > 500:
                raise ValueError("Choice option too long")
            validated.append(sanitized)

        return validated


class QuestionAnsweringDataset(BaseModel):
    """Complete legal reasoning dataset."""

    name: str = Field(..., description="Dataset name")
    version: str = Field(..., description="Dataset version")
    description: str = Field(..., description="Dataset description")
    author: str = Field(..., description="Dataset author/creator")
    group: str = Field(default="legal_reasoning", description="Dataset group")
    source: str = Field(default="LegalBench-Stanford", description="Dataset source")
    questions: List[QuestionAnsweringEntry] = Field(..., description="Legal Q&A entries")
    metadata: Dict[str, Any] = Field(..., description="Dataset-level metadata")

    @field_validator("name", "version", "author", "group", "source")
    @classmethod
    def validate_string_fields(cls: Type["QuestionAnsweringDataset"], v: str) -> str:
        """Validate string fields."""
        v = sanitize_string(v)
        if not v:
            raise ValueError("Field cannot be empty")
        if len(v) > 200:
            raise ValueError("Field too long")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls: Type["QuestionAnsweringDataset"], v: str) -> str:
        """Validate description."""
        v = sanitize_string(v)
        if len(v) > SecurityLimits.MAX_DESCRIPTION_LENGTH:
            raise ValueError("Description too long")
        return v

    @field_validator("questions")
    @classmethod
    def validate_questions(
        cls: Type["QuestionAnsweringDataset"], v: List[QuestionAnsweringEntry]
    ) -> List[QuestionAnsweringEntry]:
        """Validate questions list."""
        if not v:
            raise ValueError("Dataset must contain questions")
        if len(v) > 100000:  # Reasonable limit for large legal datasets
            raise ValueError("Too many questions in dataset")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls: Type["QuestionAnsweringDataset"], v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate dataset metadata."""
        return validate_json_data(v, max_depth=4)


class LegalBenchConversionConfig(BaseModel):
    """Configuration for LegalBench dataset conversion."""

    parallel_processing: bool = Field(default=False, description="Enable parallel directory processing")
    max_workers: int = Field(default=4, ge=1, le=16, description="Maximum worker threads")
    batch_size: int = Field(default=1000, ge=1, le=10000, description="Batch processing size")
    skip_validation: bool = Field(default=False, description="Skip validation for performance")
    include_raw_content: bool = Field(default=False, description="Include raw TSV content in metadata")
    legal_classification_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Minimum confidence for legal classification"
    )
    preserve_original_format: bool = Field(
        default=True, description="Preserve original question/answer format where possible"
    )
    enable_progress_tracking: bool = Field(default=True, description="Enable processing progress tracking")


class LegalBenchConversionResult(BaseModel):
    """Result of single legal task conversion."""

    task_name: str = Field(..., description="Legal task name")
    success: bool = Field(..., description="Conversion success status")
    questions_generated: int = Field(..., ge=0, description="Number of Q&A entries generated")
    legal_category: LegalCategory = Field(..., description="Detected legal category")
    specializations: List[str] = Field(default=[], description="Legal specializations detected")
    processing_time_ms: int = Field(..., ge=0, description="Processing time in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    warnings: List[str] = Field(default=[], description="Conversion warnings")

    @field_validator("error_message")
    @classmethod
    def validate_error_message(cls: Type["LegalBenchConversionResult"], v: Optional[str]) -> Optional[str]:
        """Validate error message."""
        if v is not None:
            return sanitize_string(v)
        return v

    @field_validator("warnings")
    @classmethod
    def validate_warnings(cls: Type["LegalBenchConversionResult"], v: List[str]) -> List[str]:
        """Validate warnings list."""
        if len(v) > 50:
            raise ValueError("Too many warnings")
        validated = []
        for warning in v:
            if not isinstance(warning, str):
                raise ValueError("Warning must be string")
            sanitized = sanitize_string(warning)
            if len(sanitized) > 500:
                raise ValueError("Warning message too long")
            validated.append(sanitized)
        return validated


class LegalBenchBatchConversionResult(BaseModel):
    """Result of batch LegalBench conversion."""

    dataset: QuestionAnsweringDataset = Field(..., description="Generated dataset")
    conversion_results: List[LegalBenchConversionResult] = Field(..., description="Individual task conversion results")
    processing_stats: Dict[str, Any] = Field(..., description="Processing statistics")
    legal_category_summary: Dict[LegalCategory, int] = Field(..., description="Legal category distribution")
    total_processing_time_ms: int = Field(..., ge=0, description="Total processing time")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Conversion success rate")

    @field_validator("processing_stats")
    @classmethod
    def validate_processing_stats(cls: Type["LegalBenchBatchConversionResult"], v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate processing statistics."""
        return validate_json_data(v, max_depth=3)


class LegalBenchValidationResult(BaseModel):
    """Result of legal dataset validation."""

    dataset_valid: bool = Field(..., description="Overall dataset validity")
    question_count: int = Field(..., ge=0, description="Total questions validated")
    validation_errors: List[str] = Field(default=[], description="Validation error messages")
    validation_warnings: List[str] = Field(default=[], description="Validation warnings")
    legal_classification_accuracy: float = Field(..., ge=0.0, le=1.0, description="Legal classification accuracy")
    professional_validation_coverage: float = Field(..., ge=0.0, le=1.0, description="Professional validation coverage")
    split_preservation_accuracy: float = Field(
        ..., ge=0.0, le=1.0, description="Train/test split preservation accuracy"
    )
    validation_timestamp: datetime = Field(..., description="Validation timestamp")

    @field_validator("validation_errors", "validation_warnings")
    @classmethod
    def validate_message_lists(cls: Type["LegalBenchValidationResult"], v: List[str]) -> List[str]:
        """Validate error/warning message lists."""
        if len(v) > 100:
            raise ValueError("Too many validation messages")
        validated = []
        for message in v:
            if not isinstance(message, str):
                raise ValueError("Message must be string")
            sanitized = sanitize_string(message)
            if len(sanitized) > 1000:
                raise ValueError("Message too long")
            validated.append(sanitized)
        return validated
