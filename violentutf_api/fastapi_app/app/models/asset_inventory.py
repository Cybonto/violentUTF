# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Asset Management Database Models for Issue #280.

This module contains the database models for the comprehensive asset management system,
including asset inventory, relationships, and audit trail functionality.
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.database import Base


class AssetType(str, Enum):
    """Asset type enumeration."""

    POSTGRESQL = "POSTGRESQL"
    MYSQL = "MYSQL"
    SQLITE = "SQLITE"
    DUCKDB = "DUCKDB"
    FILE_STORAGE = "FILE_STORAGE"
    CONFIGURATION = "CONFIGURATION"
    OTHER = "OTHER"


class SecurityClassification(str, Enum):
    """Security classification enumeration."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class CriticalityLevel(str, Enum):
    """Criticality level enumeration."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Environment enumeration."""

    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class ValidationStatus(str, Enum):
    """Validation status enumeration."""

    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class RelationshipType(str, Enum):
    """Relationship type enumeration."""

    DEPENDS_ON = "DEPENDS_ON"
    CONNECTED_TO = "CONNECTED_TO"
    REPLICATED_FROM = "REPLICATED_FROM"
    BACKED_UP_TO = "BACKED_UP_TO"
    SERVES_DATA_TO = "SERVES_DATA_TO"


class RelationshipStrength(str, Enum):
    """Relationship strength enumeration."""

    WEAK = "WEAK"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"
    CRITICAL = "CRITICAL"


class ChangeType(str, Enum):
    """Change type enumeration for audit log."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VALIDATE = "VALIDATE"


class DatabaseAsset(Base):
    """Database model for asset inventory.

    This model stores comprehensive information about all database assets
    discovered and managed within the ViolentUTF infrastructure.
    """

    __tablename__ = "database_assets"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    asset_type = Column(SQLEnum(AssetType), nullable=False, index=True)
    unique_identifier = Column(String(512), nullable=False, unique=True, index=True)

    # Location and access
    location = Column(Text, nullable=False)
    connection_string = Column(Text, nullable=True)  # Encrypted in practice
    network_location = Column(String(255), nullable=True)
    file_path = Column(Text, nullable=True)

    # Classification and security
    security_classification = Column(SQLEnum(SecurityClassification), nullable=False, index=True)
    criticality_level = Column(SQLEnum(CriticalityLevel), nullable=False, index=True)
    environment = Column(SQLEnum(Environment), nullable=False, index=True)
    encryption_enabled = Column(Boolean, default=False)
    access_restricted = Column(Boolean, default=True)

    # Technical metadata
    database_version = Column(String(100), nullable=True)
    schema_version = Column(String(100), nullable=True)
    estimated_size_mb = Column(Integer, nullable=True)
    table_count = Column(Integer, nullable=True)
    last_modified = Column(DateTime(timezone=True), nullable=True)

    # Operational metadata
    owner_team = Column(String(100), nullable=True)
    technical_contact = Column(String(255), nullable=True)
    business_contact = Column(String(255), nullable=True)
    purpose_description = Column(Text, nullable=True)

    # Discovery and validation
    discovery_method = Column(String(100), nullable=False)
    discovery_timestamp = Column(DateTime(timezone=True), nullable=False)
    confidence_score = Column(Integer, nullable=False)  # 1-100
    last_validated = Column(DateTime(timezone=True), nullable=True)
    validation_status = Column(SQLEnum(ValidationStatus), nullable=False, default=ValidationStatus.PENDING)

    # Compliance and governance
    backup_configured = Column(Boolean, default=False)
    backup_last_verified = Column(DateTime(timezone=True), nullable=True)
    compliance_requirements = Column(JSON, nullable=True)
    documentation_url = Column(String(512), nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=False)
    updated_by = Column(String(100), nullable=False)

    # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(100), nullable=True)

    # Relationships
    source_relationships = relationship(
        "AssetRelationship",
        foreign_keys="AssetRelationship.source_asset_id",
        back_populates="source_asset",
        cascade="all, delete-orphan",
    )
    target_relationships = relationship(
        "AssetRelationship", foreign_keys="AssetRelationship.target_asset_id", back_populates="target_asset"
    )
    audit_logs = relationship("AssetAuditLog", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """Return string representation of the asset."""
        return f"<DatabaseAsset(id={self.id}, name='{self.name}', type='{self.asset_type}')>"


class AssetRelationship(Base):
    """Database model for asset relationships.

    This model stores relationships and dependencies between different assets,
    enabling dependency mapping and impact analysis.
    """

    __tablename__ = "asset_relationships"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    source_asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)
    target_asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)

    # Relationship details
    relationship_type = Column(SQLEnum(RelationshipType), nullable=False, index=True)
    relationship_strength = Column(SQLEnum(RelationshipStrength), nullable=False)
    bidirectional = Column(Boolean, default=False)

    # Metadata
    description = Column(Text, nullable=True)
    discovered_method = Column(String(100), nullable=False)
    confidence_score = Column(Integer, nullable=False)  # 1-100

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=False, default="system")
    updated_by = Column(String(100), nullable=False, default="system")

    # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(100), nullable=True)

    # Relationships
    source_asset = relationship("DatabaseAsset", foreign_keys=[source_asset_id], back_populates="source_relationships")
    target_asset = relationship("DatabaseAsset", foreign_keys=[target_asset_id], back_populates="target_relationships")

    def __repr__(self) -> str:
        """Return string representation of the relationship."""
        return (
            f"<AssetRelationship(id={self.id}, type='{self.relationship_type}', "
            f"strength='{self.relationship_strength}')>"
        )


class AssetAuditLog(Base):
    """Database model for asset audit trail.

    This model provides comprehensive audit logging for all asset changes,
    supporting compliance requirements and change tracking.
    """

    __tablename__ = "asset_audit_log"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("database_assets.id"), nullable=False, index=True)

    # Change details
    change_type = Column(SQLEnum(ChangeType), nullable=False, index=True)
    field_changed = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_reason = Column(String(255), nullable=True)

    # Attribution and context
    changed_by = Column(String(100), nullable=False, index=True)
    change_source = Column(String(100), nullable=False)  # API, DISCOVERY, MANUAL
    session_id = Column(String(100), nullable=True)
    request_id = Column(String(100), nullable=True)

    # Compliance metadata
    compliance_relevant = Column(Boolean, default=False, index=True)
    gdpr_relevant = Column(Boolean, default=False, index=True)
    soc2_relevant = Column(Boolean, default=False, index=True)

    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    effective_date = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    asset = relationship("DatabaseAsset", back_populates="audit_logs")

    def __repr__(self) -> str:
        """Return string representation of the audit log."""
        return f"<AssetAuditLog(id={self.id}, asset_id={self.asset_id}, change_type='{self.change_type}')>"
