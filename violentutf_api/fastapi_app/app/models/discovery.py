# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""SQLAlchemy models for database discovery system."""


from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class DiscoveredDatabase(Base):
    """SQLAlchemy model for discovered databases."""

    __tablename__ = "discovered_databases"

    # Primary key and identification
    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(32), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Database type and connection details
    database_type = Column(String(50), nullable=False, index=True)
    host = Column(String(255))
    port = Column(Integer)
    file_path = Column(String(500))
    connection_string = Column(Text)

    # Discovery metadata
    discovery_method = Column(String(50), nullable=False, index=True)
    confidence_level = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=False)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())

    # Technical details
    version = Column(String(50))
    size_mb = Column(Float)
    is_active = Column(Boolean, default=True)
    is_accessible = Column(Boolean, default=True)

    # Validation status
    is_validated = Column(Boolean, default=False)
    validation_errors = Column(JSON)

    # Additional metadata
    tags = Column(JSON)  # List of strings
    custom_properties = Column(JSON)  # Dict of key-value pairs

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    container_info = relationship("ContainerInfo", back_populates="database", uselist=False)
    network_service = relationship("NetworkService", back_populates="database", uselist=False)
    database_files = relationship("DatabaseFile", back_populates="database")
    code_references = relationship("CodeReference", back_populates="database")
    security_findings = relationship("SecurityFinding", back_populates="database")


class ContainerInfo(Base):
    """SQLAlchemy model for container information."""

    __tablename__ = "container_info"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(32), ForeignKey("discovered_databases.database_id"), unique=True)

    container_id = Column(String(64), nullable=False)
    name = Column(String(255), nullable=False)
    image = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)

    ports = Column(JSON)  # List of port mappings
    environment = Column(JSON)  # Dict of environment variables
    volumes = Column(JSON)  # List of volume mounts
    networks = Column(JSON)  # List of network names

    is_database = Column(Boolean, default=False)
    database_type = Column(String(50))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    database = relationship("DiscoveredDatabase", back_populates="container_info")


class NetworkService(Base):
    """SQLAlchemy model for network service information."""

    __tablename__ = "network_services"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(32), ForeignKey("discovered_databases.database_id"), unique=True)

    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    protocol = Column(String(10), nullable=False, default="tcp")
    service_name = Column(String(100))
    banner = Column(Text)
    response_time_ms = Column(Float)

    is_database = Column(Boolean, default=False)
    database_type = Column(String(50))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    database = relationship("DiscoveredDatabase", back_populates="network_service")


class DatabaseFile(Base):
    """SQLAlchemy model for database file information."""

    __tablename__ = "database_files"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(32), ForeignKey("discovered_databases.database_id"))

    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    last_modified = Column(DateTime(timezone=True), nullable=False)
    file_type = Column(String(20), nullable=False)
    database_type = Column(String(50), nullable=False)

    is_accessible = Column(Boolean, default=True)
    schema_info = Column(JSON)  # Database schema information
    connection_string = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    database = relationship("DiscoveredDatabase", back_populates="database_files")


class CodeReference(Base):
    """SQLAlchemy model for code references."""

    __tablename__ = "code_references"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(32), ForeignKey("discovered_databases.database_id"))

    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer)
    code_snippet = Column(Text, nullable=False)
    reference_type = Column(String(50), nullable=False)  # import, connection, query, etc.

    database_type = Column(String(50))
    connection_string = Column(Text)
    is_credential = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    database = relationship("DiscoveredDatabase", back_populates="code_references")


class SecurityFinding(Base):
    """SQLAlchemy model for security findings."""

    __tablename__ = "security_findings"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(32), ForeignKey("discovered_databases.database_id"))

    file_path = Column(String(500), nullable=False)
    line_number = Column(Integer)
    finding_type = Column(String(50), nullable=False)  # credential, vulnerability, insecure_pattern
    severity = Column(String(20), nullable=False)  # high, medium, low
    description = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)

    is_false_positive = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    database = relationship("DiscoveredDatabase", back_populates="security_findings")


class DiscoveryReport(Base):
    """SQLAlchemy model for discovery reports."""

    __tablename__ = "discovery_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(100), unique=True, index=True, nullable=False)

    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    execution_time_seconds = Column(Float, nullable=False)
    total_discoveries = Column(Integer, nullable=False)

    # Statistics
    type_counts = Column(JSON)  # Dict of database type counts
    method_counts = Column(JSON)  # Dict of discovery method counts
    confidence_distribution = Column(JSON)  # Dict of confidence level counts

    # Performance metrics
    scan_targets = Column(JSON)  # Dict of scan target counts
    processing_stats = Column(JSON)  # Dict of processing timing data

    # Security summary
    security_findings_count = Column(Integer, default=0)
    credential_exposures = Column(Integer, default=0)
    high_severity_findings = Column(Integer, default=0)

    # Validation summary
    validated_discoveries = Column(Integer, default=0)
    validation_errors = Column(Integer, default=0)

    # Configuration and scope
    discovery_scope = Column(JSON)  # List of enabled discovery methods
    excluded_paths = Column(JSON)  # List of excluded paths
    configuration = Column(JSON)  # Dict of configuration settings

    # Full report data (JSON)
    report_data = Column(JSON)  # Complete report as JSON

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DiscoveryExecution(Base):
    """SQLAlchemy model for tracking discovery executions."""

    __tablename__ = "discovery_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(100), unique=True, index=True, nullable=False)

    # Execution metadata
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    status = Column(String(20), nullable=False, default="running")  # running, completed, failed

    # Configuration used
    config_snapshot = Column(JSON)  # Configuration at time of execution

    # Results
    discoveries_found = Column(Integer, default=0)
    errors_encountered = Column(JSON)  # List of error messages
    execution_time_seconds = Column(Float)

    # Associated report
    report_id = Column(String(100), ForeignKey("discovery_reports.report_id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
