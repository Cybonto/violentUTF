# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Dashboard and Report schemas for API requests/responses"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Existing dashboard schemas can be added here as needed


# Report-specific schemas for enhanced browsing
class DataBrowseRequest(BaseModel):
    """Request model for browsing scan data with enhanced filters"""

    start_date: Optional[datetime] = Field(None, description="Start date for filtering scan data")
    end_date: Optional[datetime] = Field(None, description="End date for filtering scan data")
    scanner_types: Optional[List[str]] = Field(None, description="Filter by scanner types (pyrit, garak)")
    orchestrator_types: Optional[List[str]] = Field(None, description="Filter by specific orchestrator types")
    # These filters are optional and will be ignored if the data doesn't contain these fields
    generators: Optional[List[str]] = Field(
        None, description="Filter by generator names (if available in score metadata)"
    )
    min_severity: Optional[str] = Field(
        None,
        description="Minimum severity level (if severity data is available)",
        pattern="^(critical|high|medium|low|minimal)$",
    )
    score_categories: Optional[List[str]] = Field(
        None, description="Filter by score categories (if available in score data)"
    )
    execution_ids: Optional[List[UUID]] = Field(None, description="Specific execution IDs to include")
    page: int = Field(1, ge=1, description="Page number for pagination")
    page_size: int = Field(50, ge=1, le=200, description="Number of items per page")
    include_test: bool = Field(False, description="Include test executions in results")
    sort_by: Optional[str] = Field(
        "date", description="Sort field (date, severity, model)", pattern="^(date|severity|model)$"
    )
    sort_order: Optional[str] = Field("desc", description="Sort order (asc, desc)", pattern="^(asc|desc)$")

    class Config:
        """Pydantic model configuration."""

        schema_extra = {
            "example": {
                "start_date": "2024-01-01T00:00:00Z",
                "end_date": "2024-01-31T23:59:59Z",
                "scanner_types": ["pyrit"],
                "orchestrator_types": ["RedTeamingOrchestrator"],
                "generators": ["gpt-4"],
                "min_severity": "medium",
                "score_categories": ["toxicity", "jailbreak"],
                "page": 1,
                "page_size": 50,
                "include_test": False,
                "sort_by": "date",
                "sort_order": "desc",
            }
        }


class ScanDataSummary(BaseModel):
    """Summary of a scan execution for browsing"""

    execution_id: UUID = Field(..., description="Unique execution identifier")
    execution_name: str = Field(..., description="Name of the execution")
    orchestrator_name: str = Field(..., description="Name of the orchestrator")
    orchestrator_type: str = Field(..., description="Type of orchestrator")
    scanner_type: str = Field(..., description="Scanner type (pyrit/garak)")
    generator: Optional[str] = Field(None, description="Generator used in the execution")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    duration_seconds: Optional[int] = Field(None, description="Execution duration in seconds")

    # Metrics
    total_tests: int = Field(0, description="Total number of tests/prompts")
    total_scores: int = Field(0, description="Total number of scores generated")

    # Severity distribution
    severity_distribution: Dict[str, int] = Field(
        default_factory=dict, description="Count of findings by severity level"
    )

    # Score categories found
    score_categories: List[str] = Field(default_factory=list, description="Categories of scores in this execution")

    # Key findings preview
    key_findings: List[Dict[str, Any]] = Field(
        default_factory=list, description="Preview of key findings (top severity)"
    )

    # Metadata
    is_test_execution: bool = Field(False, description="Whether this is a test execution")
    tags: Optional[List[str]] = Field(None, description="Execution tags")

    class Config:
        """Pydantic model configuration."""

        schema_extra = {
            "example": {
                "execution_id": "123e4567-e89b-12d3-a456-426614174000",
                "execution_name": "GPT-4 Toxicity Test",
                "orchestrator_name": "Toxicity Scanner",
                "orchestrator_type": "RedTeamingOrchestrator",
                "scanner_type": "pyrit",
                "generator": "gpt-4",
                "started_at": "2024-01-15T10:00:00Z",
                "completed_at": "2024-01-15T10:45:00Z",
                "duration_seconds": 2700,
                "total_tests": 100,
                "total_scores": 100,
                "severity_distribution": {"critical": 2, "high": 15, "medium": 30, "low": 53},
                "score_categories": ["toxicity", "bias"],
                "key_findings": [
                    {"severity": "critical", "category": "toxicity", "description": "Model generated harmful content"}
                ],
                "is_test_execution": False,
                "tags": ["production", "scheduled"],
            }
        }


class DataBrowseResponse(BaseModel):
    """Response model for scan data browsing"""

    results: List[ScanDataSummary] = Field(..., description="List of scan execution summaries")
    total_count: int = Field(..., description="Total number of results matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages are available")

    # Filter summary
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Summary of filters that were applied")

    # Aggregated statistics
    aggregate_stats: Optional[Dict[str, Any]] = Field(
        None, description="Aggregate statistics across all matching results"
    )

    class Config:
        """Pydantic model configuration."""

        schema_extra = {
            "example": {
                "results": [ScanDataSummary.Config.schema_extra["example"]],
                "total_count": 150,
                "page": 1,
                "page_size": 50,
                "has_more": True,
                "filters_applied": {
                    "start_date": "2024-01-01T00:00:00Z",
                    "end_date": "2024-01-31T23:59:59Z",
                    "scanner_types": ["pyrit"],
                },
                "aggregate_stats": {
                    "total_executions": 150,
                    "total_tests": 15000,
                    "avg_tests_per_execution": 100,
                    "severity_totals": {"critical": 10, "high": 150, "medium": 500, "low": 1000},
                },
            }
        }
