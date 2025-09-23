# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Database dependency tracking models."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.sql import func

from app.db.database import Base


class DependencyType(enum.Enum):
    """Types of dependencies in the system."""

    DATABASE = "database"
    SERVICE = "service"
    API = "api"
    AUTHENTICATION = "authentication"
    CONFIGURATION = "configuration"
    NETWORK = "network"


class CriticalityLevel(enum.Enum):
    """Criticality levels for dependencies."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class HealthStatus(enum.Enum):
    """Health status for services and dependencies."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class DiscoveryMethod(enum.Enum):
    """Methods used to discover dependencies."""

    CODE_ANALYSIS = "code_analysis"
    RUNTIME_TRACE = "runtime_trace"
    CONFIGURATION_SCAN = "configuration_scan"
    MANUAL = "manual"
    HEALTH_CHECK = "health_check"


class DependencyRelationship(Base):
    """Core dependency relationships in the system."""

    __tablename__ = "dependency_relationships"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    source_service = Column(String, nullable=False, index=True)
    target_service = Column(String, nullable=True, index=True)
    target_database = Column(String, nullable=True, index=True)
    dependency_type = Column(Enum(DependencyType), nullable=False)
    criticality = Column(Enum(CriticalityLevel), nullable=False)
    discovery_method = Column(Enum(DiscoveryMethod), nullable=False)
    connection_string = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON metadata
    last_verified = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        """Return string representation of dependency relationship."""
        target = self.target_service or self.target_database
        return f"<DependencyRelationship({self.source_service} -> {target})>"


class ServiceHealth(Base):
    """Service health and status tracking."""

    __tablename__ = "service_health"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    service_name = Column(String, nullable=False, unique=True, index=True)
    health_status = Column(Enum(HealthStatus), nullable=False)
    last_check = Column(DateTime(timezone=True), server_default=func.now())
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    dependencies_status = Column(Text, nullable=True)  # JSON of dependency health
    endpoint_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        """Return string representation of service health."""
        return f"<ServiceHealth({self.service_name}: {self.health_status.value})>"


class ImpactAnalysisRecord(Base):
    """Change impact analysis history and results."""

    __tablename__ = "impact_analyses"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    change_description = Column(Text, nullable=False)
    proposed_changes = Column(Text, nullable=False)  # JSON
    impact_assessment = Column(Text, nullable=False)  # JSON
    risk_score = Column(Integer, nullable=False)
    affected_services = Column(Text, nullable=True)  # JSON list
    rollback_plan = Column(Text, nullable=True)  # JSON
    deployment_sequence = Column(Text, nullable=True)  # JSON
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    implemented = Column(Boolean, default=False, nullable=False)
    implementation_date = Column(DateTime(timezone=True), nullable=True)
    implementation_notes = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """Return string representation of impact analysis."""
        status = "implemented" if self.implemented else "pending"
        return f"<ImpactAnalysis({self.id}: {status}, risk={self.risk_score})>"


class DependencyMatrix(Base):
    """Snapshot of complete dependency matrix for versioning."""

    __tablename__ = "dependency_matrices"
    __table_args__ = {"extend_existing": True}

    id = Column(String, primary_key=True)
    matrix_version = Column(String, nullable=False)
    matrix_data = Column(Text, nullable=False)  # JSON complete matrix
    services_snapshot = Column(Text, nullable=False)  # JSON services list
    databases_snapshot = Column(Text, nullable=False)  # JSON databases list
    discovery_metadata = Column(Text, nullable=True)  # JSON discovery info
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, nullable=False)
    is_current = Column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        """Return string representation of dependency matrix."""
        current = " (current)" if self.is_current else ""
        return f"<DependencyMatrix({self.matrix_version}{current})>"
