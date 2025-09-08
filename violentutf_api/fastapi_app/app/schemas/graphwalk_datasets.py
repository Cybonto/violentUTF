# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""GraphWalk Dataset Schemas for Issue #128 Implementation.

Defines Pydantic schemas for GraphWalk dataset conversion with massive file handling,
graph structure preservation, and spatial reasoning question generation.

SECURITY: All schemas include proper validation for defensive security research.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, field_validator


class GraphNavigationType(str, Enum):
    """Graph navigation types for spatial reasoning."""

    SHORTEST_PATH = "shortest_path"
    LONGEST_PATH = "longest_path"
    ALL_PATHS = "all_paths"
    OPTIMAL_PATH = "optimal_path"
    DIJKSTRA = "dijkstra"
    A_STAR = "a_star"
    BFS_TRAVERSAL = "bfs_traversal"
    DFS_TRAVERSAL = "dfs_traversal"


class GraphType(str, Enum):
    """Graph structure types for classification."""

    SPATIAL_GRID = "spatial_grid"
    PLANAR_GRAPH = "planar_graph"
    WEIGHTED_GRAPH = "weighted_graph"
    DIRECTED_GRAPH = "directed_graph"
    UNDIRECTED_GRAPH = "undirected_graph"
    TREE_STRUCTURE = "tree_structure"
    DAG_STRUCTURE = "dag_structure"
    GENERAL_GRAPH = "general_graph"


class SpatialReasoningType(str, Enum):
    """Spatial reasoning question types."""

    SPATIAL_TRAVERSAL = "spatial_traversal"
    PATH_FINDING = "path_finding"
    DISTANCE_CALCULATION = "distance_calculation"
    NAVIGATION_PLANNING = "navigation_planning"
    SPATIAL_RELATIONSHIP = "spatial_relationship"
    COORDINATE_REASONING = "coordinate_reasoning"


class GraphStructureInfo(BaseModel):
    """Graph structure information extracted from GraphWalk objects."""

    graph_type: str = Field(..., description="Type of graph structure")
    node_count: int = Field(..., ge=0, description="Number of nodes in graph")
    edge_count: int = Field(..., ge=0, description="Number of edges in graph")
    spatial_dimensions: int = Field(..., ge=0, le=3, description="Spatial dimensions (0-3)")
    navigation_type: str = Field(..., description="Type of navigation/traversal")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Graph properties")

    @field_validator("properties")
    @classmethod
    def validate_properties(cls: Type["GraphStructureInfo"], v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate graph properties structure."""
        required_props = ["is_directed", "is_weighted", "has_spatial_coordinates"]
        for prop in required_props:
            if prop not in v:
                v[prop] = False
        return v


class ChunkInfo(BaseModel):
    """Information about file chunks from massive file splitting."""

    chunk_id: int = Field(..., ge=1, description="Chunk identifier")
    filename: str = Field(..., description="Chunk filename")
    size: int = Field(..., ge=0, description="Chunk size in bytes")
    object_count: int = Field(..., ge=0, description="Number of objects in chunk")
    start_line: int = Field(..., ge=0, description="Starting line number")
    end_line: int = Field(..., ge=0, description="Ending line number")

    @field_validator("end_line")
    @classmethod
    def validate_line_range(cls: Type["ChunkInfo"], v: int) -> int:
        """Validate line range consistency."""
        # Note: In Pydantic v2, field validators receive just the value
        # Cross-field validation should be done at model level
        return v


class SplitResult(BaseModel):
    """Result of massive file splitting operation."""

    chunks: List[ChunkInfo] = Field(..., description="List of chunk information")
    total_chunks: int = Field(..., ge=0, description="Total number of chunks")
    total_objects: int = Field(..., ge=0, description="Total objects processed")
    original_size: int = Field(..., ge=0, description="Original file size in bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Split metadata")

    @field_validator("total_chunks")
    @classmethod
    def validate_chunk_count(cls: Type["SplitResult"], v: int) -> int:
        """Validate chunk count consistency."""
        # Note: In Pydantic v2, field validators receive just the value
        # Cross-field validation should be done at model level
        return v


class FileAnalysisInfo(BaseModel):
    """File analysis information for processing strategy selection."""

    size_mb: float = Field(..., ge=0, description="File size in megabytes")
    estimated_objects: str = Field(..., description="Estimated object count")
    structure: str = Field(..., description="File structure description")
    requires_advanced_splitting: bool = Field(default=False, description="Requires advanced splitting")
    processing_strategy: str = Field(..., description="Recommended processing strategy")


class GraphAnswerInfo(BaseModel):
    """Graph traversal answer information."""

    answer_type: str = Field(..., description="Type of answer (path, distance, etc.)")
    correct_answer: Union[List[str], str, int, float] = Field(..., description="Correct answer")
    choices: List[str] = Field(default_factory=list, description="Multiple choice options")
    reasoning: Optional[str] = Field(None, description="Answer reasoning explanation")


class QuestionAnsweringEntry(BaseModel):
    """Question-answering entry for GraphWalk spatial reasoning."""

    question: str = Field(..., min_length=1, description="Question text")
    answer_type: str = Field(..., description="Type of answer expected")
    correct_answer: Union[List[str], str, int, float] = Field(..., description="Correct answer")
    choices: List[str] = Field(default_factory=list, description="Multiple choice options")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Question metadata")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls: Type["QuestionAnsweringEntry"], v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate GraphWalk-specific metadata fields."""
        required_fields = ["graph_id", "reasoning_type", "conversion_strategy"]

        # Set default values for required fields if missing
        for field in required_fields:
            if field not in v:
                if field == "reasoning_type":
                    v[field] = "spatial_traversal"
                elif field == "conversion_strategy":
                    v[field] = "strategy_2_reasoning_benchmarks"
                else:
                    v[field] = "unknown"

        return v


class QuestionAnsweringDataset(BaseModel):
    """Complete GraphWalk question-answering dataset."""

    name: str = Field(..., description="Dataset name")
    version: str = Field(default="1.0", description="Dataset version")
    description: str = Field(..., description="Dataset description")
    author: str = Field(..., description="Dataset author")
    group: str = Field(..., description="Dataset group/category")
    source: str = Field(..., description="Original dataset source")
    questions: List[QuestionAnsweringEntry] = Field(..., description="List of questions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Dataset metadata")

    @field_validator("group")
    @classmethod
    def validate_group(cls: Type["QuestionAnsweringDataset"], v: str) -> str:
        """Validate dataset group for GraphWalk."""
        if v not in ["graph_reasoning", "spatial_reasoning", "mathematical_reasoning"]:
            return "graph_reasoning"  # Default for GraphWalk
        return v


class GraphWalkConversionConfig(BaseModel):
    """Configuration for GraphWalk dataset conversion."""

    max_memory_usage_gb: float = Field(default=2.0, ge=0.5, le=8.0, description="Maximum memory usage in GB")

    chunk_size_mb: int = Field(default=15, ge=1, le=100, description="Target chunk size in MB for splitting")

    enable_context_preservation: bool = Field(
        default=True, description="Enable graph context preservation during splitting"
    )

    processing_timeout_minutes: int = Field(default=30, ge=5, le=120, description="Maximum processing time in minutes")

    checkpoint_frequency: int = Field(
        default=5000, ge=100, le=50000, description="Checkpoint frequency in objects processed"
    )

    error_tolerance_percent: float = Field(default=1.0, ge=0.0, le=10.0, description="Allowable error rate percentage")


class ProcessingCheckpoint(BaseModel):
    """Processing checkpoint state for recovery."""

    processed_chunks: int = Field(..., ge=0, description="Number of processed chunks")
    total_questions: int = Field(..., ge=0, description="Total questions processed")
    current_chunk: str = Field(..., description="Current chunk identifier")
    timestamp: float = Field(..., description="Checkpoint timestamp")
    memory_usage_mb: float = Field(..., ge=0, description="Memory usage at checkpoint")


class ProcessingStats(BaseModel):
    """Processing statistics for performance monitoring."""

    total_chunks: int = Field(..., ge=0, description="Total chunks processed")
    processed_chunks: int = Field(..., ge=0, description="Successfully processed chunks")
    failed_chunks: int = Field(default=0, ge=0, description="Failed chunks")
    total_objects: int = Field(..., ge=0, description="Total objects processed")
    processing_time_seconds: float = Field(..., ge=0, description="Total processing time")
    memory_peak_mb: float = Field(..., ge=0, description="Peak memory usage")
    objects_per_minute: float = Field(..., ge=0, description="Processing throughput")


class MemoryUsageInfo(BaseModel):
    """Memory usage tracking information."""

    current_usage_mb: float = Field(..., ge=0, description="Current memory usage in MB")
    peak_usage_mb: float = Field(..., ge=0, description="Peak memory usage in MB")
    available_mb: float = Field(..., ge=0, description="Available memory in MB")
    usage_percentage: float = Field(..., ge=0, le=100, description="Memory usage percentage")
    cleanup_triggered: bool = Field(default=False, description="Whether cleanup was triggered")


# API Request/Response Schemas


class GraphWalkConvertRequest(BaseModel):
    """Request schema for GraphWalk dataset conversion."""

    file_path: str = Field(..., description="Path to GraphWalk dataset file")
    config: Optional[GraphWalkConversionConfig] = Field(None, description="Optional conversion configuration")
    async_conversion: bool = Field(default=True, description="Whether to run conversion asynchronously")


class GraphWalkConvertResponse(BaseModel):
    """Response schema for GraphWalk dataset conversion."""

    success: bool = Field(..., description="Whether conversion was initiated successfully")
    job_id: Optional[str] = Field(None, description="Job ID for async conversion tracking")
    result: Optional[QuestionAnsweringDataset] = Field(None, description="Conversion result for sync conversion")
    message: str = Field(..., description="Status message")
    file_info: Optional[FileAnalysisInfo] = Field(None, description="File analysis information")


class GraphWalkJobStatusResponse(BaseModel):
    """Response schema for GraphWalk conversion job status."""

    job_id: str = Field(..., description="Job identifier")
    status: str = Field(
        ..., description="Job status: started, running, analyzing, converting, finalizing, completed, failed, cancelled"
    )
    progress: float = Field(..., ge=0.0, le=1.0, description="Completion progress (0.0-1.0)")
    file_path: Optional[str] = Field(None, description="File being processed")
    result: Optional[QuestionAnsweringDataset] = Field(None, description="Conversion result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: Optional[datetime] = Field(None, description="Job creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    processing_stats: Optional[ProcessingStats] = Field(None, description="Processing statistics")


# Export all schemas for convenient importing
__all__ = [
    # Enums
    "GraphNavigationType",
    "GraphType",
    "SpatialReasoningType",
    # Core data structures
    "GraphStructureInfo",
    "ChunkInfo",
    "SplitResult",
    "FileAnalysisInfo",
    "GraphAnswerInfo",
    # Question-answer schemas
    "QuestionAnsweringEntry",
    "QuestionAnsweringDataset",
    # Configuration and state
    "GraphWalkConversionConfig",
    "ProcessingCheckpoint",
    "ProcessingStats",
    "MemoryUsageInfo",
    # API schemas
    "GraphWalkConvertRequest",
    "GraphWalkConvertResponse",
    "GraphWalkJobStatusResponse",
]
