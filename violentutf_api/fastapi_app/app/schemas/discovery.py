# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for database discovery API."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DatabaseType(str, Enum):
    """Database types supported by the discovery system."""

    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    FILE_STORAGE = "file_storage"
    UNKNOWN = "unknown"


class DiscoveryMethod(str, Enum):
    """Discovery methods used by the system."""

    CONTAINER = "container"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    CODE_ANALYSIS = "code_analysis"
    SECURITY_SCAN = "security_scan"


class ConfidenceLevel(str, Enum):
    """Confidence levels for discovery results."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


# Base schemas
class ContainerInfoBase(BaseModel):
    """Base schema for container information."""

    container_id: str
    name: str
    image: str
    status: str
    ports: List[Dict[str, Any]] = Field(default_factory=list)
    environment: Dict[str, str] = Field(default_factory=dict)
    volumes: List[Dict[str, Any]] = Field(default_factory=list)
    networks: List[str] = Field(default_factory=list)
    is_database: bool = False
    database_type: Optional[DatabaseType] = None


class NetworkServiceBase(BaseModel):
    """Base schema for network service information."""

    host: str
    port: int
    protocol: str = "tcp"
    service_name: Optional[str] = None
    banner: Optional[str] = None
    response_time_ms: Optional[float] = None
    is_database: bool = False
    database_type: Optional[DatabaseType] = None


class DatabaseFileBase(BaseModel):
    """Base schema for database file information."""

    file_path: str
    file_size: int
    last_modified: datetime
    file_type: str
    database_type: DatabaseType
    is_accessible: bool = True
    schema_info: Optional[Dict[str, Any]] = None
    connection_string: Optional[str] = None


class CodeReferenceBase(BaseModel):
    """Base schema for code references."""

    file_path: str
    line_number: Optional[int] = None
    code_snippet: str
    reference_type: str
    database_type: Optional[DatabaseType] = None
    connection_string: Optional[str] = None
    is_credential: bool = False


class SecurityFindingBase(BaseModel):
    """Base schema for security findings."""

    file_path: str
    line_number: Optional[int] = None
    finding_type: str
    severity: str
    description: str
    recommendation: str
    is_false_positive: bool = False


# Create schemas (for API requests)
class ContainerInfoCreate(ContainerInfoBase):
    """Schema for creating container information."""


class NetworkServiceCreate(NetworkServiceBase):
    """Schema for creating network service information."""


class DatabaseFileCreate(DatabaseFileBase):
    """Schema for creating database file information."""


class CodeReferenceCreate(CodeReferenceBase):
    """Schema for creating code references."""


class SecurityFindingCreate(SecurityFindingBase):
    """Schema for creating security findings."""


# Response schemas (with IDs and timestamps)
class ContainerInfo(ContainerInfoBase):
    """Schema for container information responses."""

    id: int
    database_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NetworkService(NetworkServiceBase):
    """Schema for network service responses."""

    id: int
    database_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DatabaseFile(DatabaseFileBase):
    """Schema for database file responses."""

    id: int
    database_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CodeReference(CodeReferenceBase):
    """Schema for code reference responses."""

    id: int
    database_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityFinding(SecurityFindingBase):
    """Schema for security finding responses."""

    id: int
    database_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Main database discovery schemas
class DiscoveredDatabaseBase(BaseModel):
    """Base schema for discovered databases."""

    database_id: str
    name: str
    description: Optional[str] = None
    database_type: DatabaseType
    host: Optional[str] = None
    port: Optional[int] = None
    file_path: Optional[str] = None
    connection_string: Optional[str] = None
    discovery_method: DiscoveryMethod
    confidence_level: ConfidenceLevel
    confidence_score: float = Field(ge=0.0, le=1.0)
    version: Optional[str] = None
    size_mb: Optional[float] = None
    is_active: bool = True
    is_accessible: bool = True
    is_validated: bool = False
    validation_errors: Optional[List[str]] = None
    tags: List[str] = Field(default_factory=list)
    custom_properties: Dict[str, Any] = Field(default_factory=dict)


class DiscoveredDatabaseCreate(DiscoveredDatabaseBase):
    """Schema for creating discovered databases."""

    container_info: Optional[ContainerInfoCreate] = None
    network_service: Optional[NetworkServiceCreate] = None
    database_files: List[DatabaseFileCreate] = Field(default_factory=list)
    code_references: List[CodeReferenceCreate] = Field(default_factory=list)
    security_findings: List[SecurityFindingCreate] = Field(default_factory=list)


class DiscoveredDatabaseUpdate(BaseModel):
    """Schema for updating discovered databases."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_accessible: Optional[bool] = None
    is_validated: Optional[bool] = None
    validation_errors: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    custom_properties: Optional[Dict[str, Any]] = None


class DiscoveredDatabase(DiscoveredDatabaseBase):
    """Schema for discovered database responses."""

    id: int
    discovered_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Related data
    container_info: Optional[ContainerInfo] = None
    network_service: Optional[NetworkService] = None
    database_files: List[DatabaseFile] = Field(default_factory=list)
    code_references: List[CodeReference] = Field(default_factory=list)
    security_findings: List[SecurityFinding] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# Discovery report schemas
class DiscoveryReportBase(BaseModel):
    """Base schema for discovery reports."""

    report_id: str
    execution_time_seconds: float
    total_discoveries: int
    type_counts: Dict[DatabaseType, int] = Field(default_factory=dict)
    method_counts: Dict[DiscoveryMethod, int] = Field(default_factory=dict)
    confidence_distribution: Dict[ConfidenceLevel, int] = Field(default_factory=dict)
    scan_targets: Dict[str, int] = Field(default_factory=dict)
    processing_stats: Dict[str, float] = Field(default_factory=dict)
    security_findings_count: int = 0
    credential_exposures: int = 0
    high_severity_findings: int = 0
    validated_discoveries: int = 0
    validation_errors: int = 0
    discovery_scope: List[str] = Field(default_factory=list)
    excluded_paths: List[str] = Field(default_factory=list)
    configuration: Dict[str, Any] = Field(default_factory=dict)


class DiscoveryReportCreate(DiscoveryReportBase):
    """Schema for creating discovery reports."""

    databases: List[DiscoveredDatabaseCreate] = Field(default_factory=list)
    report_data: Optional[Dict[str, Any]] = None


class DiscoveryReport(DiscoveryReportBase):
    """Schema for discovery report responses."""

    id: int
    generated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoveryReportWithDatabases(DiscoveryReport):
    """Schema for discovery report with full database data."""

    databases: List[DiscoveredDatabase] = Field(default_factory=list)


# Discovery execution schemas
class DiscoveryExecutionBase(BaseModel):
    """Base schema for discovery executions."""

    execution_id: str
    status: str = "running"
    config_snapshot: Dict[str, Any] = Field(default_factory=dict)
    discoveries_found: int = 0
    errors_encountered: List[str] = Field(default_factory=list)
    execution_time_seconds: Optional[float] = None
    report_id: Optional[str] = None


class DiscoveryExecutionCreate(DiscoveryExecutionBase):
    """Schema for creating discovery executions."""


class DiscoveryExecutionUpdate(BaseModel):
    """Schema for updating discovery executions."""

    status: Optional[str] = None
    discoveries_found: Optional[int] = None
    errors_encountered: Optional[List[str]] = None
    execution_time_seconds: Optional[float] = None
    report_id: Optional[str] = None
    completed_at: Optional[datetime] = None


class DiscoveryExecution(DiscoveryExecutionBase):
    """Schema for discovery execution responses."""

    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Configuration schemas
class DiscoveryConfigBase(BaseModel):
    """Base schema for discovery configuration."""

    enable_container_discovery: bool = True
    enable_network_discovery: bool = True
    enable_filesystem_discovery: bool = True
    enable_code_discovery: bool = True
    enable_security_scanning: bool = True

    # Container discovery
    scan_compose_files: bool = True
    compose_file_patterns: List[str] = Field(default_factory=lambda: ["docker-compose*.yml", "docker-compose*.yaml"])

    # Network discovery
    network_ranges: List[str] = Field(default_factory=lambda: ["127.0.0.1", "localhost"])
    database_ports: List[int] = Field(default_factory=lambda: [5432, 3306, 1433, 27017, 6379])
    network_timeout_seconds: int = 5
    max_concurrent_scans: int = 10

    # Filesystem discovery
    scan_paths: List[str] = Field(default_factory=list)
    file_extensions: List[str] = Field(default_factory=lambda: [".db", ".sqlite", ".sqlite3", ".duckdb"])
    max_file_size_mb: int = 1000

    # Code discovery
    code_extensions: List[str] = Field(default_factory=lambda: [".py", ".yml", ".yaml", ".json", ".env"])
    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["__pycache__", ".git", "node_modules", ".venv", "venv", ".pytest_cache"]
    )

    # Security scanning
    secrets_baseline_file: Optional[str] = None
    bandit_config_file: Optional[str] = None
    exclude_security_paths: List[str] = Field(default_factory=lambda: ["tests/", "test/"])

    # Performance
    max_execution_time_seconds: int = 300
    max_memory_usage_mb: int = 512
    enable_parallel_processing: bool = True
    max_workers: int = 4

    # Output
    output_format: str = "json"
    include_raw_data: bool = False
    include_security_details: bool = True
    validation_enabled: bool = True


class DiscoveryConfig(DiscoveryConfigBase):
    """Schema for discovery configuration."""


# API response schemas
class DiscoveryStats(BaseModel):
    """Schema for discovery statistics."""

    total_databases: int
    active_databases: int
    database_types: Dict[DatabaseType, int]
    discovery_methods: Dict[DiscoveryMethod, int]
    confidence_levels: Dict[ConfidenceLevel, int]
    security_findings: int
    last_discovery_at: Optional[datetime] = None


class DiscoveryHealthCheck(BaseModel):
    """Schema for discovery system health check."""

    status: str
    dependencies: Dict[str, str]  # dependency_name -> status
    last_execution: Optional[datetime] = None
    total_discoveries: int
    system_load: Dict[str, Any]


# Search and filter schemas
class DiscoveryFilter(BaseModel):
    """Schema for filtering discovered databases."""

    database_type: Optional[DatabaseType] = None
    discovery_method: Optional[DiscoveryMethod] = None
    confidence_level: Optional[ConfidenceLevel] = None
    is_active: Optional[bool] = None
    is_validated: Optional[bool] = None
    has_security_findings: Optional[bool] = None
    tags: Optional[List[str]] = None
    host: Optional[str] = None
    min_confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    discovered_after: Optional[datetime] = None
    discovered_before: Optional[datetime] = None


class DiscoverySearch(BaseModel):
    """Schema for searching discovered databases."""

    query: str
    filters: Optional[DiscoveryFilter] = None
    limit: int = Field(default=50, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: str = "discovered_at"
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# Bulk operation schemas
class BulkValidationRequest(BaseModel):
    """Schema for bulk validation requests."""

    database_ids: List[str]
    force_revalidation: bool = False


class BulkValidationResponse(BaseModel):
    """Schema for bulk validation responses."""

    validation_results: Dict[str, bool]  # database_id -> validation_success
    errors: Dict[str, str]  # database_id -> error_message
    processed_count: int
    success_count: int
    error_count: int
