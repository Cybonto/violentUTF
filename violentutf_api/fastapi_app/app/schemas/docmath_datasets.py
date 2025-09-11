# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""DocMath Dataset Schema Definitions (Issue #127).

Defines data structures for DocMath dataset conversion including complexity tiers,
mathematical answer types, and conversion configurations for mathematical reasoning
tasks with large file handling support.

SECURITY: All data structures include proper validation for defensive security research.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class DocMathComplexityTier(Enum):
    """Enum for DocMath complexity tier categories."""

    SIMPSHORT = "simpshort"
    SIMPLONG = "simplong"
    COMPSHORT = "compshort"
    COMPLONG = "complong"


# Alias for backward compatibility
ComplexityTier = DocMathComplexityTier


class MathematicalAnswerType(Enum):
    """Enum for mathematical answer types."""

    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    EXPRESSION = "expression"


class MathematicalDomain(Enum):
    """Enum for mathematical domain categories."""

    ARITHMETIC = "arithmetic"
    ALGEBRA = "algebra"
    GEOMETRY = "geometry"
    STATISTICS = "statistics"
    CALCULUS = "calculus"
    FINANCIAL = "financial"
    MEASUREMENT = "measurement"
    WORD_PROBLEMS = "word_problems"
    GENERAL = "general"


class ProcessingStrategy(Enum):
    """Enum for file processing strategies."""

    STANDARD = "standard"
    STREAMING = "streaming"
    SPLITTING_WITH_STREAMING = "splitting_with_streaming"


class DocMathConversionConfig(BaseModel):
    """Configuration for DocMath dataset conversion."""

    enable_large_file_splitting: bool = Field(default=True, description="Whether to enable large file splitting")
    enable_streaming_processing: bool = Field(default=True, description="Whether to enable streaming processing")
    enable_mathematical_validation: bool = Field(
        default=True, description="Whether to enable mathematical answer validation"
    )
    enable_context_preservation: bool = Field(default=True, description="Whether to preserve mathematical context")
    enable_domain_classification: bool = Field(default=True, description="Whether to enable domain classification")
    max_processing_time_seconds: int = Field(default=1800, description="Maximum processing time in seconds")
    max_memory_usage_gb: float = Field(default=2.0, description="Maximum memory usage in GB")
    chunk_size_mb: int = Field(default=20, description="Chunk size for file splitting in MB")
    batch_size: int = Field(default=1000, description="Batch size for processing")
    performance_logging: bool = Field(default=True, description="Whether to enable performance logging")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class QuestionAnsweringEntry(BaseModel):
    """PyRIT-compatible QuestionAnsweringEntry for mathematical reasoning tasks."""

    question: str = Field(..., description="Complete question text with context")
    answer_type: str = Field(..., description="Type of answer (int, float, str)")
    correct_answer: Union[int, float, str] = Field(..., description="Correct answer value")
    choices: List[str] = Field(default_factory=list, description="Choice options for MCQ")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Question metadata")

    @validator("answer_type")
    def validate_answer_type(cls, v: str) -> str:  # pylint: disable=no-self-argument
        """Validate answer type is supported."""
        if v not in ["int", "float", "str", "bool"]:
            raise ValueError(f"Answer type must be int, float, str, or bool, got: {v}")
        return v

    @validator("correct_answer")
    def validate_correct_answer(  # pylint: disable=no-self-argument
        cls, v: Union[int, float, str, bool], values: dict
    ) -> Union[int, float, str, bool]:
        """Validate correct answer matches answer type."""
        answer_type = values.get("answer_type")
        if answer_type == "int" and not isinstance(v, int):
            try:
                return int(v)
            except (ValueError, TypeError):
                raise ValueError("Correct answer must be integer for answer_type='int'") from None
        elif answer_type == "float" and not isinstance(v, (int, float)):
            try:
                return float(v)
            except (ValueError, TypeError):
                raise ValueError("Correct answer must be numeric for answer_type='float'") from None
        elif answer_type == "str" and not isinstance(v, str):
            return str(v)
        elif answer_type == "bool" and not isinstance(v, bool):
            raise ValueError("Correct answer must be boolean for answer_type='bool'")
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class QuestionAnsweringDataset(BaseModel):
    """PyRIT-compatible QuestionAnsweringDataset for DocMath mathematical tasks."""

    name: str = Field(..., description="Dataset name")
    version: str = Field(default="1.0", description="Dataset version")
    description: str = Field(..., description="Dataset description")
    author: str = Field(default="Yale NLP", description="Dataset author")
    group: str = Field(default="mathematical_reasoning", description="Dataset group")
    source: str = Field(default="DocMath-Yale", description="Dataset source")
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


class DocMathEntry(BaseModel):
    """Individual DocMath dataset entry structure."""

    question_id: str = Field(..., description="Unique question identifier")
    question: str = Field(..., description="Question text")
    ground_truth: Union[int, float, str] = Field(..., description="Correct answer")
    context: Optional[str] = Field(None, description="Document context")
    paragraphs: Optional[List[str]] = Field(default_factory=list, description="Relevant paragraphs")
    table_evidence: Optional[List[str]] = Field(default_factory=list, description="Table evidence")
    python_solution: Optional[str] = Field(None, description="Python solution code")
    reasoning_steps: Optional[List[str]] = Field(default_factory=list, description="Reasoning steps")
    complexity_tier: Optional[DocMathComplexityTier] = Field(None, description="Complexity tier")
    split: Optional[str] = Field(None, description="Dataset split (test, testmini)")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class MathematicalDomainInfo(BaseModel):
    """Information about mathematical domain classification."""

    domain: MathematicalDomain
    confidence_score: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    key_concepts: List[str] = Field(default_factory=list, description="Identified concepts")
    complexity_indicators: List[str] = Field(default_factory=list, description="Complexity indicators")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class FileProcessingResult(BaseModel):
    """Result of file processing operation."""

    file_path: str = Field(..., description="Processed file path")
    processing_strategy: ProcessingStrategy = Field(..., description="Strategy used")
    questions_processed: int = Field(..., description="Number of questions processed")
    processing_time_seconds: float = Field(..., description="Processing time")
    peak_memory_mb: float = Field(..., description="Peak memory usage")
    errors: List[str] = Field(default_factory=list, description="Processing errors")
    warnings: List[str] = Field(default_factory=list, description="Processing warnings")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ConversionSummary(BaseModel):
    """Summary of DocMath dataset conversion."""

    total_questions: int = Field(..., description="Total questions converted")
    complexity_tier_counts: Dict[str, int] = Field(default_factory=dict, description="Questions per tier")
    domain_distribution: Dict[str, int] = Field(default_factory=dict, description="Questions per domain")
    processing_time_seconds: float = Field(..., description="Total processing time")
    peak_memory_mb: float = Field(..., description="Peak memory usage")
    files_processed: List[FileProcessingResult] = Field(default_factory=list, description="File processing results")
    conversion_config: DocMathConversionConfig = Field(..., description="Configuration used")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ValidationResult(BaseModel):
    """Result of mathematical validation."""

    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    validated_count: int = Field(default=0, description="Number of items validated")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
