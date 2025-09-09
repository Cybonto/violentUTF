# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for JudgeBench Meta-Evaluation Converter (Issue #130).

This module defines comprehensive data structures for the JudgeBench meta-evaluation
converter implementation, supporting judge-the-judge assessment capabilities with
multi-model evaluation hierarchy preservation.

SECURITY: All schemas include comprehensive input validation and sanitization to
prevent injection attacks and ensure data integrity.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Type

from app.core.validation import sanitize_string, validate_json_data
from pydantic import BaseModel, Field, field_validator


class JudgeType(str, Enum):
    """Supported judge types for meta-evaluation."""

    ARENA_HARD = "arena_hard"
    REWARD_MODEL = "reward_model"
    PROMETHEUS_2 = "prometheus_2"


class MetaEvaluationType(str, Enum):
    """Meta-evaluation assessment types."""

    JUDGE_ASSESSMENT = "judge_assessment"
    COMPARATIVE_RANKING = "comparative_ranking"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    BIAS_DETECTION = "bias_detection"


class EvaluationDifficulty(str, Enum):
    """Evaluation difficulty levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class JudgeFileInfo:
    """Information extracted from judge output filename patterns."""

    judge_name: str
    judge_model: str
    response_model: str
    file_path: str
    file_size_mb: float

    def __post_init__(self) -> None:
        """Validate file info after initialization."""
        if not self.judge_name or not self.judge_model or not self.response_model:
            raise ValueError("Judge name, model, and response model are required")
        if self.file_size_mb < 0:
            raise ValueError("File size must be non-negative")


@dataclass
class JudgeAnalysis:
    """Comprehensive judge performance analysis results."""

    performance_indicators: Dict[str, Any]
    evaluation_dimensions: List[str]
    reasoning_quality: Dict[str, float]
    score_appropriateness: Dict[str, Any]
    consistency_indicators: Dict[str, Any]
    judge_characteristics: Dict[str, str]

    def __post_init__(self) -> None:
        """Validate analysis after initialization."""
        # Ensure reasoning quality scores are between 0 and 1
        for key, value in self.reasoning_quality.items():
            if not isinstance(value, (int, float)) or not (0 <= value <= 1):
                raise ValueError(f"Reasoning quality score '{key}' must be between 0 and 1")


class JudgeEvaluationEntry(BaseModel):
    """JSONL entry structure for judge evaluations."""

    id: str = Field(..., description="Unique evaluation identifier")
    original_task: str = Field(..., description="Original task prompt")
    model_response: str = Field(..., description="Model response being evaluated")
    judge_name: str = Field(..., description="Name of the judging system")
    judge_model: str = Field(..., description="Model used for judging")
    judge_response: str = Field(..., description="Judge's evaluation response")
    score: float = Field(..., ge=0.0, le=10.0, description="Judge's numerical score (0-10)")
    reasoning: str = Field(..., description="Judge's reasoning for the score")
    evaluation_criteria: List[str] = Field(..., description="Criteria used for evaluation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator(
        "id", "original_task", "model_response", "judge_name", "judge_model", "judge_response", "reasoning"
    )
    @classmethod
    def sanitize_text_fields(cls: Type["JudgeEvaluationEntry"], v: str) -> str:
        """Sanitize text fields to prevent injection attacks."""
        if isinstance(v, str):
            return sanitize_string(v)
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls: Type["JudgeEvaluationEntry"], v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata JSON structure."""
        if not validate_json_data(v):
            raise ValueError("Invalid metadata JSON structure")
        return v

    @field_validator("evaluation_criteria")
    @classmethod
    def validate_criteria(cls: Type["JudgeEvaluationEntry"], v: List[str]) -> List[str]:
        """Validate evaluation criteria list."""
        if not v:
            raise ValueError("At least one evaluation criterion is required")
        return [sanitize_string(criterion) for criterion in v]


class MetaEvaluationCriteria(BaseModel):
    """Meta-evaluation criteria configuration."""

    judge_type: JudgeType = Field(..., description="Type of judge being evaluated")
    base_criteria: Dict[str, str] = Field(..., description="Base evaluation criteria")
    specific_criteria: Dict[str, str] = Field(default_factory=dict, description="Judge-specific criteria")
    scoring_weights: Dict[str, float] = Field(..., description="Scoring weights for each criterion")

    @field_validator("scoring_weights")
    @classmethod
    def validate_weights(cls: Type["MetaEvaluationCriteria"], v: Dict[str, float]) -> Dict[str, float]:
        """Validate scoring weights sum to 1.0."""
        total_weight = sum(v.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight}")
        return v


class MetaScorerConfig(BaseModel):
    """Configuration for meta-evaluation scoring."""

    scorer_type: str = Field(default="meta_evaluation_judge_assessment")
    judge_name: str = Field(..., description="Name of judge being assessed")
    evaluation_focus: str = Field(..., description="Primary evaluation focus area")
    primary_dimensions: List[str] = Field(..., description="Primary evaluation dimensions")
    scoring_weight: Dict[str, float] = Field(..., description="Dimension scoring weights")
    meta_evaluation_mode: str = Field(default="judge_quality_assessment")

    @field_validator("primary_dimensions")
    @classmethod
    def validate_dimensions(cls: Type["MetaScorerConfig"], v: List[str]) -> List[str]:
        """Validate primary evaluation dimensions."""
        if len(v) < 2:
            raise ValueError("At least 2 primary evaluation dimensions required")
        return v


class JudgePerformanceMetrics(BaseModel):
    """Judge performance metrics and statistics."""

    total_evaluations: int = Field(ge=0, description="Total number of evaluations")
    score_statistics: Dict[str, float] = Field(..., description="Score distribution statistics")
    reasoning_statistics: Dict[str, float] = Field(..., description="Reasoning quality statistics")
    response_statistics: Dict[str, float] = Field(..., description="Response quality statistics")
    consistency_metrics: Dict[str, float] = Field(default_factory=dict, description="Consistency metrics")
    bias_indicators: Dict[str, float] = Field(default_factory=dict, description="Potential bias indicators")

    @field_validator("score_statistics", "reasoning_statistics", "response_statistics")
    @classmethod
    def validate_statistics(cls: Type["JudgePerformanceMetrics"], v: Dict[str, float]) -> Dict[str, float]:
        """Validate statistical measures."""
        required_stats = ["mean", "std", "min", "max"]
        for stat in required_stats:
            if stat not in v:
                raise ValueError(f"Missing required statistic: {stat}")
        return v


class JudgeMetadata(BaseModel):
    """Comprehensive judge metadata for dataset."""

    judge_name: str = Field(..., description="Name of the judge")
    judge_model: str = Field(..., description="Model used for judging")
    response_model: str = Field(..., description="Model that generated responses")
    evaluation_count: int = Field(ge=0, description="Number of evaluations")
    file_size_mb: float = Field(ge=0, description="Source file size in MB")
    evaluation_focus: str = Field(..., description="Primary evaluation focus")
    performance_analysis: JudgePerformanceMetrics = Field(..., description="Performance analysis results")
    processing_timestamp: datetime = Field(default_factory=datetime.now, description="Processing timestamp")

    @field_validator("judge_name", "judge_model", "response_model", "evaluation_focus")
    @classmethod
    def sanitize_judge_fields(cls: Type["JudgeMetadata"], v: str) -> str:
        """Sanitize judge-related text fields."""
        return sanitize_string(v)


class MetaEvaluationPromptTemplate(BaseModel):
    """Template for generating meta-evaluation prompts."""

    judge_type: JudgeType = Field(..., description="Type of judge being evaluated")
    template_structure: Dict[str, str] = Field(..., description="Template structure sections")
    evaluation_dimensions: List[str] = Field(..., description="Evaluation dimensions to assess")
    quality_requirements: Dict[str, str] = Field(..., description="Quality requirements for prompts")

    @field_validator("evaluation_dimensions")
    @classmethod
    def validate_evaluation_dimensions(cls: Type["MetaEvaluationPromptTemplate"], v: List[str]) -> List[str]:
        """Validate evaluation dimensions."""
        required_dimensions = [
            "Accuracy",
            "Consistency",
            "Completeness",
            "Reasoning Quality",
            "Bias Detection",
            "Score Appropriateness",
        ]
        for dim in required_dimensions:
            if dim not in v:
                raise ValueError(f"Missing required evaluation dimension: {dim}")
        return v


class ConversionProcessingResult(BaseModel):
    """Result of judge file processing."""

    file_path: str = Field(..., description="Path to processed file")
    judge_info: Dict[str, str] = Field(..., description="Judge information extracted")
    processing_time_seconds: float = Field(ge=0, description="Processing time in seconds")
    prompts_generated: int = Field(ge=0, description="Number of prompts generated")
    errors_encountered: int = Field(ge=0, description="Number of processing errors")
    memory_peak_mb: float = Field(ge=0, description="Peak memory usage in MB")

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls: Type["ConversionProcessingResult"], v: str) -> str:
        """Validate file path format."""
        if not v or not v.endswith(".jsonl"):
            raise ValueError("File path must end with .jsonl")
        return v


class JudgeBenchDatasetMetadata(BaseModel):
    """Comprehensive metadata for JudgeBench dataset conversion."""

    name: str = Field(default="JudgeBench_Meta_Evaluation", description="Dataset name")
    version: str = Field(default="1.0", description="Dataset version")
    description: str = Field(default="Meta-evaluation framework for AI judge assessment and comparison")
    author: str = Field(default="JudgeBench Team (ICLR 2025)", description="Dataset author")
    group: str = Field(default="meta_evaluation", description="Dataset group")
    source: str = Field(default="JudgeBench-ICLR25", description="Original data source")

    # Conversion-specific metadata
    evaluation_framework: str = Field(default="judge_meta_evaluation", description="Evaluation framework type")
    judge_count: int = Field(ge=0, description="Number of unique judges processed")
    total_evaluations: int = Field(ge=0, description="Total evaluation entries processed")
    total_files_processed: int = Field(ge=0, description="Number of JSONL files processed")

    # Model information
    response_models: List[str] = Field(default_factory=list, description="Models that generated responses")
    judge_models: List[str] = Field(default_factory=list, description="Models used for judging")

    # Processing metadata
    judge_metadata: Dict[str, JudgeMetadata] = Field(default_factory=dict, description="Per-judge metadata")
    meta_evaluation_types: List[str] = Field(default_factory=list, description="Types of meta-evaluation supported")
    conversion_strategy: str = Field(default="strategy_4_meta_evaluation", description="Conversion strategy used")
    processing_timestamp: datetime = Field(default_factory=datetime.now, description="Dataset processing timestamp")

    @field_validator("response_models", "judge_models", "meta_evaluation_types")
    @classmethod
    def validate_model_lists(cls: Type["JudgeBenchDatasetMetadata"], v: List[str]) -> List[str]:
        """Validate model lists are not empty."""
        if not v:
            raise ValueError("Model list cannot be empty after processing")
        return [sanitize_string(model) for model in v]


class ValidationResult(BaseModel):
    """Result of dataset validation."""

    is_valid: bool = Field(..., description="Whether validation passed")
    validation_errors: List[str] = Field(default_factory=list, description="Validation error messages")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    quality_score: float = Field(ge=0.0, le=1.0, description="Overall quality score (0-1)")

    # Quality metrics
    prompt_quality_score: float = Field(ge=0.0, le=1.0, description="Meta-evaluation prompt quality")
    metadata_completeness: float = Field(ge=0.0, le=1.0, description="Metadata completeness score")
    consistency_score: float = Field(ge=0.0, le=1.0, description="Data consistency score")

    @field_validator("validation_errors", "warnings")
    @classmethod
    def sanitize_messages(cls: Type["ValidationResult"], v: List[str]) -> List[str]:
        """Sanitize error and warning messages."""
        return [sanitize_string(msg) for msg in v]


# Judge-specific configurations
JUDGE_CONFIGURATIONS = {
    JudgeType.ARENA_HARD: {
        "description": "Arena-Hard benchmark judge evaluations",
        "typical_size_mb": "7-10",
        "evaluation_focus": "competitive_performance_assessment",
        "specific_criteria": {
            "difficulty_calibration": "Assess ability to calibrate scores for task difficulty",
            "comparative_ranking": "Evaluate consistency in relative performance rankings",
            "competitive_assessment": "Judge's ability to evaluate competitive performance scenarios",
        },
        "scoring_weights": {"accuracy": 0.4, "consistency": 0.3, "calibration": 0.3},
    },
    JudgeType.REWARD_MODEL: {
        "description": "Reward model judge evaluations",
        "typical_size_mb": "8-12",
        "evaluation_focus": "reward_signal_alignment",
        "specific_criteria": {
            "reward_alignment": "Assess alignment of scores with intended reward signals",
            "preference_consistency": "Evaluate consistency in preference-based evaluations",
            "value_alignment": "Judge's adherence to specified value systems",
        },
        "scoring_weights": {"alignment": 0.5, "consistency": 0.3, "accuracy": 0.2},
    },
    JudgeType.PROMETHEUS_2: {
        "description": "Prometheus-2 rubric-based judge evaluations",
        "typical_size_mb": "9-11",
        "evaluation_focus": "rubric_based_assessment",
        "specific_criteria": {
            "rubric_adherence": "Assess strict adherence to evaluation rubrics",
            "score_justification": "Evaluate quality of score justification against rubric",
            "criterion_coverage": "Judge's coverage of all specified evaluation criteria",
        },
        "scoring_weights": {"adherence": 0.4, "coverage": 0.3, "justification": 0.3},
    },
}

# Base meta-evaluation criteria (common to all judges)
BASE_META_EVALUATION_CRITERIA = {
    "accuracy_assessment": "Evaluate correctness of judge's evaluation relative to response quality",
    "consistency_check": "Assess consistency between score, reasoning, and stated criteria",
    "bias_detection": "Identify potential systematic biases in evaluation approach",
    "reasoning_quality": "Evaluate clarity, logic, and completeness of provided reasoning",
    "score_appropriateness": "Assess whether numerical scores match qualitative assessments",
}

# Judge file pattern configurations
JUDGE_FILE_PATTERNS = {
    "arena_hard": {
        "description": "Arena-Hard benchmark judge evaluations",
        "typical_size": "7-10MB",
        "evaluation_focus": "competitive_performance_ranking",
    },
    "reward_model": {
        "description": "Reward model judge evaluations",
        "typical_size": "8-12MB",
        "evaluation_focus": "reward_alignment_assessment",
    },
    "prometheus_2": {
        "description": "Prometheus-2 rubric-based judge evaluations",
        "typical_size": "9-11MB",
        "evaluation_focus": "rubric_adherence_evaluation",
    },
}
