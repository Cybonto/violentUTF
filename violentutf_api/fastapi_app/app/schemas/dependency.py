# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for dependency mapping and impact analysis."""

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.fields import FieldInfo

from app.models.dependency import CriticalityLevel, DependencyType, DiscoveryMethod, HealthStatus


class DependencyRelationshipBase(BaseModel):
    """Base schema for dependency relationships."""

    source_service: str = Field(..., description="Source service name")
    target_service: Optional[str] = Field(None, description="Target service name")
    target_database: Optional[str] = Field(None, description="Target database identifier")
    dependency_type: DependencyType = Field(..., description="Type of dependency")
    criticality: CriticalityLevel = Field(..., description="Criticality level")
    discovery_method: DiscoveryMethod = Field(..., description="How dependency was discovered")
    connection_string: Optional[str] = Field(None, description="Connection string (sanitized)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("target_service", "target_database")
    @classmethod
    def validate_target(cls: Type["DependencyRelationshipBase"], v: Optional[str], info: FieldInfo) -> Optional[str]:
        """Ensure at least one target is specified."""
        values = info.data if info.data else {}
        target_service = values.get("target_service")
        target_database = v if info.field_name == "target_database" else values.get("target_database")

        if not target_service and not target_database:
            raise ValueError("Either target_service or target_database must be specified")
        return v


class DependencyRelationshipCreate(DependencyRelationshipBase):
    """Schema for creating dependency relationships."""


class DependencyRelationshipUpdate(BaseModel):
    """Schema for updating dependency relationships."""

    criticality: Optional[CriticalityLevel] = None
    connection_string: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DependencyRelationship(DependencyRelationshipBase):
    """Complete dependency relationship schema."""

    id: str
    last_verified: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceHealthBase(BaseModel):
    """Base schema for service health."""

    service_name: str = Field(..., description="Service name")
    health_status: HealthStatus = Field(..., description="Current health status")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    dependencies_status: Optional[Dict[str, Any]] = Field(None, description="Dependency health status")
    endpoint_url: Optional[str] = Field(None, description="Health check endpoint URL")


class ServiceHealthCreate(ServiceHealthBase):
    """Schema for creating service health records."""


class ServiceHealthUpdate(BaseModel):
    """Schema for updating service health."""

    health_status: Optional[HealthStatus] = None
    response_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    dependencies_status: Optional[Dict[str, Any]] = None


class ServiceHealth(ServiceHealthBase):
    """Complete service health schema."""

    id: str
    last_check: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChangeRequest(BaseModel):
    """Schema for change impact analysis requests."""

    change_type: str = Field(..., description="Type of change (schema, service, configuration)")
    change_description: str = Field(..., description="Detailed description of the change")
    affected_components: List[str] = Field(..., description="List of components to be changed")
    proposed_changes: Dict[str, Any] = Field(..., description="Detailed change specifications")
    requestor: str = Field(..., description="Person requesting the change")
    urgency: str = Field(default="medium", description="Change urgency (low, medium, high, critical)")

    @field_validator("change_type")
    @classmethod
    def validate_change_type(cls: Type["ChangeRequest"], v: str) -> str:
        """Validate change type."""
        allowed_types = [
            "schema_change",
            "service_change",
            "configuration_change",
            "network_change",
            "security_change",
            "deployment_change",
        ]
        if v not in allowed_types:
            raise ValueError(f"Change type must be one of: {allowed_types}")
        return v


class ImpactAnalysisResult(BaseModel):
    """Schema for impact analysis results."""

    analysis_id: str = Field(..., description="Unique analysis identifier")
    change_request: ChangeRequest = Field(..., description="Original change request")
    risk_score: int = Field(..., ge=1, le=10, description="Risk score (1-10)")
    affected_services: List[str] = Field(..., description="Services that will be affected")
    affected_dependencies: List[str] = Field(..., description="Dependencies that will be affected")
    impact_severity: str = Field(..., description="Overall impact severity")
    estimated_downtime: Optional[str] = Field(None, description="Estimated downtime duration")
    rollback_complexity: str = Field(..., description="Rollback complexity level")
    rollback_plan: List[Dict[str, Any]] = Field(..., description="Step-by-step rollback plan")
    deployment_sequence: List[Dict[str, Any]] = Field(..., description="Recommended deployment sequence")
    recommendations: List[str] = Field(..., description="Implementation recommendations")
    warnings: List[str] = Field(default_factory=list, description="Warnings and concerns")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DependencyGraph(BaseModel):
    """Schema for dependency graph visualization."""

    nodes: List[Dict[str, Any]] = Field(..., description="Graph nodes")
    edges: List[Dict[str, Any]] = Field(..., description="Graph edges")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Graph metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nodes": [
                    {"id": "streamlit-app", "type": "service", "criticality": "high"},
                    {"id": "fastapi-app", "type": "service", "criticality": "critical"},
                    {"id": "violentutf_api.db", "type": "database", "criticality": "critical"},
                ],
                "edges": [
                    {"source": "streamlit-app", "target": "fastapi-app", "type": "api"},
                    {"source": "fastapi-app", "target": "violentutf_api.db", "type": "database"},
                ],
                "metadata": {"generated_at": "2025-01-09T10:30:00Z", "total_nodes": 3, "total_edges": 2},
            }
        }
    )


class DependencyMatrix(BaseModel):
    """Schema for complete dependency matrix."""

    matrix_version: str = Field(..., description="Matrix version identifier")
    services: List[str] = Field(..., description="List of all services")
    databases: List[str] = Field(..., description="List of all databases")
    dependencies: List[DependencyRelationship] = Field(..., description="All dependency relationships")
    service_health: List[ServiceHealth] = Field(..., description="Current service health status")
    matrix_metadata: Dict[str, Any] = Field(default_factory=dict, description="Matrix metadata")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "matrix_version": "v1.0.0",
                "services": ["streamlit-app", "fastapi-app", "keycloak"],
                "databases": ["violentutf_api.db", "keycloak.db", "pyrit_memory.db"],
                "dependencies": [],
                "service_health": [],
                "matrix_metadata": {
                    "discovery_methods": ["code_analysis", "runtime_trace"],
                    "total_dependencies": 15,
                    "critical_dependencies": 8,
                },
            }
        }
    )


class DiscoveryResult(BaseModel):
    """Schema for dependency discovery results."""

    discovery_id: str = Field(..., description="Unique discovery session ID")
    discovery_method: DiscoveryMethod = Field(..., description="Discovery method used")
    started_at: datetime = Field(..., description="Discovery start time")
    completed_at: Optional[datetime] = Field(None, description="Discovery completion time")
    status: str = Field(..., description="Discovery status (running, completed, failed)")
    discovered_dependencies: int = Field(default=0, description="Number of dependencies discovered")
    new_dependencies: int = Field(default=0, description="Number of new dependencies found")
    updated_dependencies: int = Field(default=0, description="Number of updated dependencies")
    errors: List[str] = Field(default_factory=list, description="Discovery errors")
    warnings: List[str] = Field(default_factory=list, description="Discovery warnings")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Discovery metadata")


class SystemHealthStatus(BaseModel):
    """Schema for overall system health status."""

    overall_health: HealthStatus = Field(..., description="Overall system health")
    total_services: int = Field(..., description="Total number of services")
    healthy_services: int = Field(..., description="Number of healthy services")
    degraded_services: int = Field(..., description="Number of degraded services")
    down_services: int = Field(..., description="Number of down services")
    critical_dependencies_healthy: int = Field(..., description="Critical dependencies that are healthy")
    total_critical_dependencies: int = Field(..., description="Total critical dependencies")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
    services_status: List[ServiceHealth] = Field(..., description="Individual service status")
    issues: List[str] = Field(default_factory=list, description="Current system issues")

    @field_validator("overall_health", mode="before")
    @classmethod
    def determine_overall_health(
        cls: Type["SystemHealthStatus"], v: Optional[HealthStatus], info: FieldInfo
    ) -> HealthStatus:
        """Determine overall health based on service status."""
        values = info.data if info.data else {}
        down_services = values.get("down_services", 0)
        degraded_services = values.get("degraded_services", 0)

        if down_services > 0:
            return HealthStatus.DOWN
        elif degraded_services > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY


class DependencyDiscoveryConfig(BaseModel):
    """Configuration for dependency discovery."""

    discovery_methods: List[DiscoveryMethod] = Field(
        default=[DiscoveryMethod.CODE_ANALYSIS, DiscoveryMethod.RUNTIME_TRACE], description="Discovery methods to use"
    )
    scan_paths: List[str] = Field(
        default=["./violentutf", "./violentutf_api"], description="Paths to scan for dependencies"
    )
    exclude_patterns: List[str] = Field(
        default=["*.pyc", "__pycache__", ".git", "node_modules"], description="Patterns to exclude from scanning"
    )
    runtime_trace_duration: int = Field(default=300, description="Runtime tracing duration in seconds")
    health_check_timeout: int = Field(default=30, description="Health check timeout in seconds")
    enable_deep_analysis: bool = Field(default=True, description="Enable deep dependency analysis")
