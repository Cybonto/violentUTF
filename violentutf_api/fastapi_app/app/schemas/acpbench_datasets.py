# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""ACPBench Dataset Schema Definitions (Issue #125).

Defines data structures for ACPBench dataset conversion including planning domains,
question types, complexity levels, and conversion configurations for planning
reasoning tasks across 7 domains.

SECURITY: All data structures include proper validation for defensive security research.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class PlanningDomain(Enum):
    """Enum for planning domain categories."""

    LOGISTICS = "logistics"
    BLOCKS_WORLD = "blocks_world"
    SCHEDULING = "scheduling"
    GENERAL_PLANNING = "general_planning"
    GRAPH_PLANNING = "graph_planning"
    ROUTE_PLANNING = "route_planning"
    RESOURCE_ALLOCATION = "resource_allocation"


class PlanningComplexity(Enum):
    """Enum for planning task complexity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PlanningQuestionType(Enum):
    """Enum for ACPBench question types."""

    BOOLEAN = "boolean"
    MULTIPLE_CHOICE = "multiple_choice"
    GENERATION = "generation"


class ACPBenchConversionConfig(BaseModel):
    """Configuration for ACPBench dataset conversion."""

    enable_context_preservation: bool = Field(
        default=True, description="Whether to preserve planning context information"
    )
    enable_domain_classification: bool = Field(default=True, description="Whether to enable domain classification")
    enable_complexity_analysis: bool = Field(default=True, description="Whether to analyze planning complexity")
    max_processing_time_seconds: int = Field(default=120, description="Maximum processing time in seconds")
    batch_size: int = Field(default=100, description="Batch size for processing")
    performance_logging: bool = Field(default=True, description="Whether to enable performance logging")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class QuestionAnsweringEntry(BaseModel):
    """PyRIT-compatible QuestionAnsweringEntry for planning reasoning tasks."""

    question: str = Field(..., description="Complete question text with context")
    answer_type: str = Field(..., description="Type of answer (bool, int, str)")
    correct_answer: Any = Field(..., description="Correct answer value")
    choices: List[str] = Field(default_factory=list, description="Choice options for MCQ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Question metadata")

    @validator("answer_type")
    def validate_answer_type(cls, v: str) -> str:  # pylint: disable=no-self-argument
        """Validate answer type is supported."""
        if v not in ["bool", "int", "str"]:
            raise ValueError(f"Answer type must be bool, int, or str, got: {v}")
        return v

    @validator("correct_answer")
    def validate_correct_answer(cls, v: Any, values: dict) -> Any:  # noqa: ANN401 # pylint: disable=no-self-argument
        """Validate correct answer matches answer type."""
        answer_type = values.get("answer_type")
        if answer_type == "bool" and not isinstance(v, bool):
            raise ValueError("Correct answer must be boolean for answer_type='bool'")
        elif answer_type == "int" and not isinstance(v, int):
            raise ValueError("Correct answer must be integer for answer_type='int'")
        elif answer_type == "str" and not isinstance(v, str):
            raise ValueError("Correct answer must be string for answer_type='str'")
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class QuestionAnsweringDataset(BaseModel):
    """PyRIT-compatible QuestionAnsweringDataset for ACPBench planning tasks."""

    name: str = Field(..., description="Dataset name")
    version: str = Field(default="1.0", description="Dataset version")
    description: str = Field(..., description="Dataset description")
    author: str = Field(default="ACPBench-IBM", description="Dataset author")
    group: str = Field(default="planning_reasoning", description="Dataset group")
    source: str = Field(default="ACPBench-IBM", description="Dataset source")
    questions: List[QuestionAnsweringEntry] = Field(..., description="List of questions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dataset metadata")

    @validator("questions")
    def validate_questions_not_empty(  # pylint: disable=no-self-argument
        cls, v: List[QuestionAnsweringEntry]
    ) -> List[QuestionAnsweringEntry]:
        """Validate questions list is not empty."""
        if not v:
            raise ValueError("Questions list cannot be empty")
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class PlanningDomainInfo(BaseModel):
    """Information about a planning domain."""

    domain: PlanningDomain
    description: str
    complexity: PlanningComplexity
    key_concepts: List[str]
    confidence_score: float = Field(ge=0.0, le=1.0)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class PlanningAnalysisResult(BaseModel):
    """Result of planning domain and complexity analysis."""

    domain: PlanningDomain
    domain_confidence: float = Field(ge=0.0, le=1.0)
    complexity: PlanningComplexity
    complexity_confidence: float = Field(ge=0.0, le=1.0)
    key_concepts: List[str]
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict)
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ACPBenchFileInfo(BaseModel):
    """Information about an ACPBench JSON file."""

    file_type: PlanningQuestionType
    file_path: str
    question_count: int
    planning_domains: List[str]
    processing_time_seconds: float
    file_size_bytes: int

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ACPBenchConversionResult(BaseModel):
    """Result of ACPBench dataset conversion."""

    dataset_name: str
    success: bool
    dataset: Optional[QuestionAnsweringDataset] = None
    file_info: List[ACPBenchFileInfo] = Field(default_factory=list)
    total_questions: int
    conversion_time_seconds: float
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    conversion_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class PlanningScenarioContext(BaseModel):
    """Context information for a planning scenario."""

    scenario_id: str
    planning_group: str
    domain: PlanningDomain
    complexity: PlanningComplexity
    context_text: str
    question_text: str
    key_concepts: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ConversionValidationResult(BaseModel):
    """Result of conversion validation."""

    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    quality_score: float = Field(ge=0.0, le=1.0)
    metadata_completeness: float = Field(ge=0.0, le=1.0)
    context_preservation_rate: float = Field(ge=0.0, le=1.0)
    validation_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
