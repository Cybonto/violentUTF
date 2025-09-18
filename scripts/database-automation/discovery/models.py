# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Data models for database discovery system.

Shared between standalone scripts and FastAPI integration.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class DatabaseType(str, Enum):
    """Supported database types in ViolentUTF environment."""

    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    DUCKDB = "duckdb"
    FILE_STORAGE = "file_storage"
    UNKNOWN = "unknown"


class DiscoveryMethod(str, Enum):
    """Methods used for database discovery."""

    CONTAINER = "container"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    CODE_ANALYSIS = "code_analysis"
    SECURITY_SCAN = "security_scan"


class ConfidenceLevel(str, Enum):
    """Confidence levels for discovery results."""

    HIGH = "high"  # 90-100% confidence
    MEDIUM = "medium"  # 70-89% confidence
    LOW = "low"  # 50-69% confidence
    VERY_LOW = "very_low"  # <50% confidence


@dataclass
class NetworkService:
    """Network service discovery result."""

    host: str
    port: int
    protocol: str
    service_name: Optional[str] = None
    banner: Optional[str] = None
    response_time_ms: Optional[float] = None
    is_database: bool = False
    database_type: Optional[DatabaseType] = None


@dataclass
class ContainerInfo:
    """Docker container information."""

    container_id: str
    name: str
    image: str
    status: str
    ports: List[Dict[str, Any]] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    volumes: List[Dict[str, Any]] = field(default_factory=list)
    networks: List[str] = field(default_factory=list)
    is_database: bool = False
    database_type: Optional[DatabaseType] = None


@dataclass
class DatabaseFile:
    """Database file discovery result."""

    file_path: str
    file_size: int
    last_modified: datetime
    file_type: str
    database_type: DatabaseType
    is_accessible: bool = True
    schema_info: Optional[Dict[str, Any]] = None
    connection_string: Optional[str] = None


@dataclass
class CodeReference:
    """Database reference found in source code."""

    file_path: str
    line_number: int
    code_snippet: str
    reference_type: str  # import, connection, query, etc.
    database_type: Optional[DatabaseType] = None
    connection_string: Optional[str] = None
    is_credential: bool = False


@dataclass
class SecurityFinding:
    """Security-related discovery finding."""

    file_path: str
    line_number: Optional[int]
    finding_type: str  # credential, vulnerability, insecure_pattern
    severity: str  # high, medium, low
    description: str
    recommendation: str
    is_false_positive: bool = False


@dataclass
class DatabaseDiscovery:
    """Complete database discovery result."""

    # Identification (required fields)
    database_id: str  # Unique identifier
    database_type: DatabaseType
    name: str
    discovery_method: DiscoveryMethod
    confidence_level: ConfidenceLevel
    confidence_score: float  # 0.0 - 1.0

    # Optional fields with defaults
    description: Optional[str] = None

    # Location and access
    host: Optional[str] = None
    port: Optional[int] = None
    file_path: Optional[str] = None
    connection_string: Optional[str] = None

    # Discovery metadata
    discovered_at: datetime = field(default_factory=datetime.utcnow)

    # Technical details
    version: Optional[str] = None
    size_mb: Optional[float] = None
    is_active: bool = True
    is_accessible: bool = True

    # Related findings
    container_info: Optional[ContainerInfo] = None
    network_service: Optional[NetworkService] = None
    database_files: List[DatabaseFile] = field(default_factory=list)
    code_references: List[CodeReference] = field(default_factory=list)
    security_findings: List[SecurityFinding] = field(default_factory=list)

    # Validation
    is_validated: bool = False
    validation_errors: List[str] = field(default_factory=list)

    # Additional metadata
    tags: List[str] = field(default_factory=list)
    custom_properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiscoveryReport:
    """Complete discovery report with all findings."""

    # Report metadata
    report_id: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    execution_time_seconds: float = 0.0

    # Discovery results
    databases: List[DatabaseDiscovery] = field(default_factory=list)
    total_discoveries: int = 0

    # Statistics by type
    type_counts: Dict[DatabaseType, int] = field(default_factory=dict)
    method_counts: Dict[DiscoveryMethod, int] = field(default_factory=dict)
    confidence_distribution: Dict[ConfidenceLevel, int] = field(default_factory=dict)

    # Performance metrics
    scan_targets: Dict[str, int] = field(default_factory=dict)  # containers, files, etc.
    processing_stats: Dict[str, float] = field(default_factory=dict)  # timing data

    # Security summary
    security_findings_count: int = 0
    credential_exposures: int = 0
    high_severity_findings: int = 0

    # Validation summary
    validated_discoveries: int = 0
    validation_errors: int = 0

    # Additional metadata
    discovery_scope: List[str] = field(default_factory=list)
    excluded_paths: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""

        def serialize_dataclass(obj):  # noqa: ANN001 ANN201
            if hasattr(obj, "__dataclass_fields__"):
                result = {}
                for field_name, field_value in obj.__dict__.items():
                    if isinstance(field_value, datetime):
                        result[field_name] = field_value.isoformat()
                    elif isinstance(field_value, list):
                        result[field_name] = [serialize_dataclass(item) for item in field_value]
                    elif hasattr(field_value, "__dataclass_fields__"):
                        result[field_name] = serialize_dataclass(field_value)
                    elif isinstance(field_value, Enum):
                        result[field_name] = field_value.value
                    else:
                        result[field_name] = field_value
                return result
            return obj

        return serialize_dataclass(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for the report."""
        return {
            "total_databases": self.total_discoveries,
            "active_databases": sum(1 for db in self.databases if db.is_active),
            "high_confidence": sum(1 for db in self.databases if db.confidence_level == ConfidenceLevel.HIGH),
            "security_findings": self.security_findings_count,
            "execution_time": self.execution_time_seconds,
            "validation_rate": self.validated_discoveries / max(self.total_discoveries, 1) * 100,
        }


@dataclass
class DiscoveryConfig:
    """Configuration for discovery execution."""

    # Scope configuration
    enable_container_discovery: bool = True
    enable_network_discovery: bool = True
    enable_filesystem_discovery: bool = True
    enable_code_discovery: bool = True
    enable_security_scanning: bool = True

    # Container discovery
    docker_socket_path: str = "/var/run/docker.sock"
    scan_compose_files: bool = True
    compose_file_patterns: List[str] = field(default_factory=lambda: ["docker-compose*.yml", "docker-compose*.yaml"])

    # Network discovery
    network_ranges: List[str] = field(default_factory=lambda: ["127.0.0.1", "localhost"])
    database_ports: List[int] = field(default_factory=lambda: [5432, 3306, 1433, 27017, 6379])
    network_timeout_seconds: int = 5
    max_concurrent_scans: int = 10

    # Filesystem discovery
    scan_paths: List[str] = field(
        default_factory=lambda: [
            "/Users/tamnguyen/Documents/GitHub/violentUTF",
            "./violentutf_api/fastapi_app/app_data",
            "./violentutf/app_data",
        ]
    )
    file_extensions: List[str] = field(default_factory=lambda: [".db", ".sqlite", ".sqlite3", ".duckdb"])
    max_file_size_mb: int = 1000  # Skip files larger than this

    # Code discovery
    code_extensions: List[str] = field(default_factory=lambda: [".py", ".yml", ".yaml", ".json", ".env"])
    exclude_patterns: List[str] = field(
        default_factory=lambda: ["__pycache__", ".git", "node_modules", ".venv", "venv", ".pytest_cache"]
    )

    # Security scanning
    secrets_baseline_file: Optional[str] = None
    bandit_config_file: Optional[str] = None
    exclude_security_paths: List[str] = field(default_factory=lambda: ["tests/", "test/"])

    # Performance limits
    max_execution_time_seconds: int = 300  # 5 minutes
    max_memory_usage_mb: int = 512
    enable_parallel_processing: bool = True
    max_workers: int = 4

    # Output configuration
    output_format: str = "json"  # json, yaml, markdown
    include_raw_data: bool = False
    include_security_details: bool = True
    validation_enabled: bool = True
