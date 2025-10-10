# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for OllaGen1 split manifest structures."""

# pylint: disable=no-self-argument  # Pydantic validators use cls, not self

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ScenarioRangeInfo(BaseModel):
    """Information about scenario range in a split part."""

    start: int = Field(..., ge=1, description="Starting scenario number")
    end: int = Field(..., ge=1, description="Ending scenario number")

    @validator("end")
    def end_must_be_greater_than_start(cls, v: int, values: Dict[str, int]) -> int:
        """Validate that end is greater than or equal to start."""
        if "start" in values and v < values["start"]:
            raise ValueError("end must be greater than or equal to start")
        return v

    def count(self) -> int:
        """Calculate the number of scenarios in this range."""
        return self.end - self.start + 1


class CognitiveFrameworkMetadata(BaseModel):
    """Metadata about the cognitive framework used in OllaGen1."""

    question_types: List[str] = Field(..., description="Types of questions in the framework")
    behavioral_constructs: int = Field(..., ge=0, description="Number of behavioral constructs")
    person_profiles: int = Field(..., ge=1, description="Number of person profiles")
    qa_pairs_per_scenario: int = Field(4, description="Q&A pairs per scenario")

    @validator("question_types")
    def validate_question_types(cls, v: List[str]) -> List[str]:
        """Validate question types match expected OllaGen1 framework."""
        expected_types = {"WCP", "WHO", "TeamRisk", "TargetFactor"}
        if set(v) != expected_types:
            raise ValueError(f"question_types must contain exactly: {expected_types}")
        return v


class ColumnSchema(BaseModel):
    """Schema information for CSV columns."""

    columns: List[str] = Field(..., description="Column names")
    column_count: int = Field(..., ge=1, description="Number of columns")
    column_types: Dict[str, str] = Field(..., description="Column name to type mapping")
    encoding: str = Field("utf-8", description="File encoding")

    @validator("column_count")
    def validate_column_count(cls, v: int, values: Dict[str, List[str]]) -> int:
        """Validate column count matches columns list length."""
        if "columns" in values and v != len(values["columns"]):
            raise ValueError("column_count must match length of columns list")
        return v


class PartInfo(BaseModel):
    """Information about a single split part."""

    part_number: int = Field(..., ge=1, description="Part number in sequence")
    filename: str = Field(..., description="Filename of the part")
    size: int = Field(..., ge=0, description="File size in bytes")
    checksum: str = Field(..., description="SHA-256 checksum with sha256: prefix")
    row_range: Dict[str, int] = Field(..., description="Row range (start, end)")
    scenario_range: Dict[str, int] = Field(..., description="Scenario range (start, end)")
    scenario_count: int = Field(..., ge=0, description="Number of scenarios in this part")
    qa_pairs: int = Field(..., ge=0, description="Number of Q&A pairs in this part")

    @validator("checksum")
    def validate_checksum(cls, v: str) -> str:
        """Validate checksum format and content."""
        if not v.startswith("sha256:"):
            raise ValueError('checksum must start with "sha256:"')
        # Check if the remaining part is a valid hex string
        hex_part = v[7:]  # Remove 'sha256:' prefix
        if len(hex_part) != 64:
            raise ValueError("SHA-256 checksum must be 64 hex characters")
        try:
            int(hex_part, 16)
        except ValueError as exc:
            raise ValueError("checksum must be valid hexadecimal") from exc
        return v

    @validator("qa_pairs")
    def validate_qa_pairs(cls, v: int, values: Dict[str, int]) -> int:
        """Validate qa_pairs equals 4 times scenario_count."""
        if "scenario_count" in values:
            expected_qa = values["scenario_count"] * 4  # 4 Q&A pairs per scenario
            if v != expected_qa:
                raise ValueError(f"qa_pairs must be 4 times scenario_count (expected {expected_qa}, got {v})")
        return v


class ReconstructionInfo(BaseModel):
    """Information needed for file reconstruction."""

    merge_order: List[int] = Field(..., description="Order to merge parts")
    validation_checksums: List[str] = Field(..., description="Checksums for validation")
    total_validation_checksum: str = Field(..., description="Checksum of original complete file")
    reconstruction_instructions: str = Field(
        "Merge parts in order, removing duplicate headers", description="Instructions for reconstruction"
    )

    @validator("total_validation_checksum")
    def validate_total_checksum(cls, v: str) -> str:
        """Validate total validation checksum format."""
        if not v.startswith("sha256:"):
            raise ValueError('total_validation_checksum must start with "sha256:"')
        return v


class PerformanceMetadata(BaseModel):
    """Performance metrics for the split operation."""

    file_size_mb: str = Field(..., description="Original file size in human-readable format")
    estimated_split_time_seconds: Optional[float] = Field(None, description="Time taken for split")
    memory_efficient: bool = Field(True, description="Whether operation was memory efficient")
    peak_memory_mb: Optional[float] = Field(None, description="Peak memory usage during operation")


class OllaGen1ManifestSchema(BaseModel):
    """Complete schema for OllaGen1 split manifest."""

    # Basic file information
    original_file: str = Field(..., description="Original filename")
    dataset_type: str = Field("ollegen1_cognitive", description="Type of dataset")
    split_timestamp: datetime = Field(..., description="When the split was performed")

    # File metrics
    total_size: int = Field(..., ge=0, description="Total file size in bytes")
    total_rows: int = Field(..., ge=0, description="Total number of data rows")
    total_scenarios: int = Field(..., ge=0, description="Total number of scenarios")
    total_qa_pairs: int = Field(..., ge=0, description="Total number of Q&A pairs")
    total_parts: int = Field(..., ge=1, description="Number of split parts")
    chunk_size: int = Field(..., ge=1, description="Target chunk size in bytes")
    checksum: str = Field(..., description="Checksum of original file")

    # Schema and structure
    schema: ColumnSchema = Field(..., description="Column schema information")
    cognitive_framework: CognitiveFrameworkMetadata = Field(..., description="Cognitive framework metadata")

    # Parts and reconstruction
    parts: List[PartInfo] = Field(..., description="Information about split parts")
    reconstruction_info: ReconstructionInfo = Field(..., description="Reconstruction metadata")

    # Performance information
    split_performance: PerformanceMetadata = Field(..., description="Performance metrics")

    @validator("dataset_type")
    def validate_dataset_type(cls, v: str) -> str:
        """Validate dataset type is ollegen1_cognitive."""
        if v != "ollegen1_cognitive":
            raise ValueError('dataset_type must be "ollegen1_cognitive"')
        return v

    @validator("total_qa_pairs")
    def validate_total_qa_pairs(cls, v: int, values: Dict[str, int]) -> int:
        """Validate total qa_pairs equals 4 times total_scenarios."""
        if "total_scenarios" in values:
            expected_qa = values["total_scenarios"] * 4  # 4 Q&A pairs per scenario
            if v != expected_qa:
                raise ValueError("total_qa_pairs must be 4 times total_scenarios")
        return v

    @validator("total_parts")
    def validate_total_parts(cls, v: int, values: Dict[str, List]) -> int:
        """Validate total_parts matches parts list length."""
        if "parts" in values and v != len(values["parts"]):
            raise ValueError("total_parts must match length of parts list")
        return v

    @validator("parts")
    def validate_parts_sequence(cls, v: List) -> List:
        """Validate parts have sequential numbering starting from 1."""
        if not v:
            raise ValueError("parts list cannot be empty")

        # Check part numbers are sequential starting from 1
        part_numbers = [part.part_number for part in v]
        expected_numbers = list(range(1, len(v) + 1))

        if sorted(part_numbers) != expected_numbers:
            raise ValueError("part numbers must be sequential starting from 1")

        return v


class ManifestValidationResult(BaseModel):
    """Result of manifest validation."""

    is_valid: bool = Field(..., description="Whether manifest is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    manifest_version: str = Field("1.0", description="Manifest schema version")

    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)

    @property
    def has_issues(self) -> bool:
        """Check if there are any errors or warnings."""
        return bool(self.errors or self.warnings)
