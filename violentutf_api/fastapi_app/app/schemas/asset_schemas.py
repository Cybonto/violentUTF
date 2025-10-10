# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for Asset Management API for Issue #280.

This module contains all the Pydantic models for request/response validation
in the asset management API endpoints.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.models.asset_inventory import (
    AssetType,
    ChangeType,
    CriticalityLevel,
    Environment,
    RelationshipStrength,
    RelationshipType,
    SecurityClassification,
    ValidationStatus,
)


# Base schemas for asset management
class AssetBase(BaseModel):
    """Base schema for asset data."""

    name: str = Field(..., min_length=3, max_length=255, description="Asset name")
    asset_type: AssetType = Field(..., description="Type of the asset")
    unique_identifier: str = Field(..., min_length=1, max_length=512, description="Unique identifier for the asset")
    location: str = Field(..., description="Asset location (server, file path, etc.)")
    connection_string: Optional[str] = Field(None, description="Connection string (encrypted)")
    network_location: Optional[str] = Field(None, description="Network location (IP:port)")
    file_path: Optional[str] = Field(None, description="File system path")

    # Classification and security
    security_classification: SecurityClassification = Field(..., description="Security classification level")
    criticality_level: CriticalityLevel = Field(..., description="Business criticality level")
    environment: Environment = Field(..., description="Environment (dev, test, staging, prod)")
    encryption_enabled: Optional[bool] = Field(False, description="Whether encryption is enabled")
    access_restricted: Optional[bool] = Field(True, description="Whether access is restricted")

    # Technical metadata
    database_version: Optional[str] = Field(None, max_length=100, description="Database version")
    schema_version: Optional[str] = Field(None, max_length=100, description="Schema version")
    estimated_size_mb: Optional[int] = Field(None, ge=0, description="Estimated size in MB")
    table_count: Optional[int] = Field(None, ge=0, description="Number of tables")
    last_modified: Optional[datetime] = Field(None, description="Last modification timestamp")

    # Operational metadata
    owner_team: Optional[str] = Field(None, max_length=100, description="Owning team")
    technical_contact: Optional[str] = Field(None, max_length=255, description="Technical contact email")
    business_contact: Optional[str] = Field(None, max_length=255, description="Business contact email")
    purpose_description: Optional[str] = Field(None, description="Purpose and description")

    # Discovery metadata
    discovery_method: str = Field(..., max_length=100, description="How the asset was discovered")
    confidence_score: int = Field(..., ge=1, le=100, description="Confidence score (1-100)")

    # Compliance and governance
    backup_configured: Optional[bool] = Field(False, description="Whether backup is configured")
    backup_last_verified: Optional[datetime] = Field(None, description="Last backup verification")
    compliance_requirements: Optional[Dict[str, Any]] = Field(None, description="Compliance requirements")
    documentation_url: Optional[str] = Field(None, max_length=512, description="Documentation URL")

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls: Type["AssetBase"], v: int) -> int:
        """Validate confidence score is within range."""
        if not 1 <= v <= 100:
            raise ValueError("Confidence score must be between 1 and 100")
        return v

    @field_validator("technical_contact", "business_contact")
    @classmethod
    def validate_email_format(cls: Type["AssetBase"], v: Optional[str]) -> Optional[str]:
        """Validate basic email format."""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""

    # Discovery timestamp will be set automatically
    # Validation status will default to PENDING


class AssetUpdate(BaseModel):
    """Schema for updating an existing asset."""

    name: Optional[str] = Field(None, min_length=3, max_length=255)
    location: Optional[str] = Field(None)
    connection_string: Optional[str] = Field(None)
    network_location: Optional[str] = Field(None)
    file_path: Optional[str] = Field(None)

    security_classification: Optional[SecurityClassification] = Field(None)
    criticality_level: Optional[CriticalityLevel] = Field(None)
    environment: Optional[Environment] = Field(None)
    encryption_enabled: Optional[bool] = Field(None)
    access_restricted: Optional[bool] = Field(None)

    database_version: Optional[str] = Field(None, max_length=100)
    schema_version: Optional[str] = Field(None, max_length=100)
    estimated_size_mb: Optional[int] = Field(None, ge=0)
    table_count: Optional[int] = Field(None, ge=0)
    last_modified: Optional[datetime] = Field(None)

    owner_team: Optional[str] = Field(None, max_length=100)
    technical_contact: Optional[str] = Field(None, max_length=255)
    business_contact: Optional[str] = Field(None, max_length=255)
    purpose_description: Optional[str] = Field(None)

    confidence_score: Optional[int] = Field(None, ge=1, le=100)
    backup_configured: Optional[bool] = Field(None)
    backup_last_verified: Optional[datetime] = Field(None)
    compliance_requirements: Optional[Dict[str, Any]] = Field(None)
    documentation_url: Optional[str] = Field(None, max_length=512)

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls: Type["AssetBase"], v: Optional[int]) -> Optional[int]:
        """Validate confidence score is within range."""
        if v is not None and not 1 <= v <= 100:
            raise ValueError("Confidence score must be between 1 and 100")
        return v


class AssetResponse(AssetBase):
    """Schema for asset response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Asset unique ID")
    discovery_timestamp: datetime = Field(..., description="Discovery timestamp")
    validation_status: ValidationStatus = Field(..., description="Validation status")
    last_validated: Optional[datetime] = Field(None, description="Last validation timestamp")

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="Created by user")
    updated_by: str = Field(..., description="Last updated by user")

    is_deleted: bool = Field(False, description="Soft delete flag")


class AssetListResponse(BaseModel):
    """Schema for asset list response with pagination."""

    assets: List[AssetResponse] = Field(..., description="List of assets")
    total_count: int = Field(..., description="Total number of assets")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items per page")


# Relationship schemas
class RelationshipBase(BaseModel):
    """Base schema for asset relationships."""

    source_asset_id: uuid.UUID = Field(..., description="Source asset ID")
    target_asset_id: uuid.UUID = Field(..., description="Target asset ID")
    relationship_type: RelationshipType = Field(..., description="Type of relationship")
    relationship_strength: RelationshipStrength = Field(..., description="Strength of relationship")
    bidirectional: bool = Field(False, description="Whether relationship is bidirectional")
    description: Optional[str] = Field(None, description="Relationship description")
    discovered_method: str = Field(..., max_length=100, description="How relationship was discovered")
    confidence_score: int = Field(..., ge=1, le=100, description="Confidence score (1-100)")

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls: Type["AssetBase"], v: int) -> int:
        """Validate confidence score is within range."""
        if not 1 <= v <= 100:
            raise ValueError("Confidence score must be between 1 and 100")
        return v

    @field_validator("source_asset_id", "target_asset_id")
    @classmethod
    def validate_different_assets(cls: Type["RelationshipBase"], v: uuid.UUID, info: ValidationInfo) -> uuid.UUID:
        """Validate that source and target assets are different."""
        if hasattr(info, "data") and "source_asset_id" in info.data:
            if v == info.data["source_asset_id"]:
                raise ValueError("Source and target assets must be different")
        return v


class RelationshipCreate(RelationshipBase):
    """Schema for creating a new relationship."""


class RelationshipResponse(RelationshipBase):
    """Schema for relationship response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Relationship unique ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="Created by user")
    updated_by: str = Field(..., description="Last updated by user")


class RelationshipGraph(BaseModel):
    """Schema for relationship graph visualization."""

    nodes: List[Dict[str, Any]] = Field(..., description="Graph nodes (assets)")
    edges: List[Dict[str, Any]] = Field(..., description="Graph edges (relationships)")
    metadata: Dict[str, Any] = Field(..., description="Graph metadata")


# Bulk operations schemas
class BulkAssetImport(BaseModel):
    """Schema for individual asset in bulk import."""

    name: str = Field(..., min_length=3, max_length=255)
    asset_type: AssetType = Field(...)
    unique_identifier: str = Field(..., min_length=1, max_length=512)
    location: str = Field(...)
    security_classification: SecurityClassification = Field(...)
    criticality_level: CriticalityLevel = Field(...)
    environment: Environment = Field(...)
    discovery_method: str = Field(..., max_length=100)
    confidence_score: int = Field(..., ge=1, le=100)

    # Optional fields
    connection_string: Optional[str] = Field(None)
    technical_contact: Optional[str] = Field(None)
    backup_configured: Optional[bool] = Field(False)
    compliance_requirements: Optional[Dict[str, Any]] = Field(None)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional discovery metadata")


class BulkImportRequest(BaseModel):
    """Schema for bulk import request."""

    source: str = Field(..., max_length=100, description="Import source identifier")
    assets: List[BulkAssetImport] = Field(..., min_length=1, max_length=1000, description="Assets to import")
    import_options: Optional[Dict[str, Any]] = Field(None, description="Import configuration options")


class BulkImportResponse(BaseModel):
    """Schema for bulk import response."""

    job_id: str = Field(..., description="Import job ID")
    status: str = Field(..., description="Import status")
    assets_count: int = Field(..., description="Number of assets to import")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")


class ImportJobStatus(BaseModel):
    """Schema for import job status."""

    job_id: str = Field(..., description="Import job ID")
    status: str = Field(..., description="Current status")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress percentage (0.0-1.0)")
    assets_processed: int = Field(..., description="Number of assets processed")
    assets_created: int = Field(..., description="Number of assets created")
    assets_updated: int = Field(..., description="Number of assets updated")
    assets_failed: int = Field(..., description="Number of assets that failed")
    errors: List[str] = Field(..., description="List of error messages")
    started_at: datetime = Field(..., description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")


class BulkUpdateItem(BaseModel):
    """Schema for individual asset update in bulk operation."""

    asset_id: uuid.UUID = Field(..., description="Asset ID to update")
    fields: Dict[str, Any] = Field(..., description="Fields to update")


class BulkUpdateRequest(BaseModel):
    """Schema for bulk update request."""

    updates: List[BulkUpdateItem] = Field(..., min_length=1, max_length=1000, description="Updates to apply")


class ValidationBatchRequest(BaseModel):
    """Schema for batch validation request."""

    assets: List[BulkAssetImport] = Field(..., min_length=1, max_length=1000, description="Assets to validate")


class ValidationResult(BaseModel):
    """Schema for validation result."""

    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(..., description="Validation errors")
    warnings: List[str] = Field(..., description="Validation warnings")


class ValidationBatchResponse(BaseModel):
    """Schema for batch validation response."""

    valid_count: int = Field(..., description="Number of valid assets")
    invalid_count: int = Field(..., description="Number of invalid assets")
    validation_errors: Dict[str, List[str]] = Field(..., description="Errors by asset identifier")
    validation_warnings: Dict[str, List[str]] = Field(..., description="Warnings by asset identifier")


# Conflict resolution schemas
class ConflictType(str, Enum):
    """Conflict type enumeration."""

    EXACT_IDENTIFIER = "EXACT_IDENTIFIER"
    SIMILAR_ATTRIBUTES = "SIMILAR_ATTRIBUTES"
    LOCATION_OVERLAP = "LOCATION_OVERLAP"


class ResolutionAction(str, Enum):
    """Resolution action enumeration."""

    MERGE = "MERGE"
    CREATE_SEPARATE = "CREATE_SEPARATE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    UPDATE_EXISTING = "UPDATE_EXISTING"


class ConflictCandidate(BaseModel):
    """Schema for conflict candidate."""

    existing_asset_id: uuid.UUID = Field(..., description="Existing asset ID")
    conflict_type: ConflictType = Field(..., description="Type of conflict")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Conflict confidence score")
    details: Dict[str, Any] = Field(..., description="Conflict details")


class ConflictResolution(BaseModel):
    """Schema for conflict resolution."""

    action: ResolutionAction = Field(..., description="Recommended action")
    automatic: bool = Field(..., description="Whether resolution can be automatic")
    reason: str = Field(..., description="Reason for the resolution")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional resolution metadata")


# Discovery integration schemas
class DiscoveredAsset(BaseModel):
    """Schema for discovered asset from external systems."""

    identifier: str = Field(..., description="Asset identifier from discovery system")
    name: str = Field(..., description="Asset name")
    type: str = Field(..., description="Asset type")
    location: str = Field(..., description="Asset location")
    confidence: int = Field(..., ge=1, le=100, description="Discovery confidence")
    metadata: Dict[str, Any] = Field(..., description="Additional discovery metadata")
    discovery_timestamp: datetime = Field(..., description="When asset was discovered")


class DiscoveryReport(BaseModel):
    """Schema for discovery report from external systems."""

    source: str = Field(..., description="Discovery system identifier")
    timestamp: datetime = Field(..., description="Report generation timestamp")
    assets: List[DiscoveredAsset] = Field(..., description="Discovered assets")
    report_metadata: Optional[Dict[str, Any]] = Field(None, description="Report metadata")


class ImportResult(BaseModel):
    """Schema for import processing result."""

    created_count: int = Field(..., description="Number of assets created")
    updated_count: int = Field(..., description="Number of assets updated")
    error_count: int = Field(..., description="Number of assets with errors")
    skipped_count: int = Field(..., description="Number of assets skipped")
    conflicts: List[ConflictCandidate] = Field(..., description="Detected conflicts")
    errors: Dict[str, List[str]] = Field(..., description="Errors by asset identifier")
    processing_duration: float = Field(..., description="Processing duration in seconds")


# Audit log schemas
class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Audit log ID")
    asset_id: uuid.UUID = Field(..., description="Associated asset ID")
    change_type: ChangeType = Field(..., description="Type of change")
    field_changed: Optional[str] = Field(None, description="Field that was changed")
    old_value: Optional[str] = Field(None, description="Previous value")
    new_value: Optional[str] = Field(None, description="New value")
    change_reason: Optional[str] = Field(None, description="Reason for change")
    changed_by: str = Field(..., description="User who made the change")
    change_source: str = Field(..., description="Source of the change")
    compliance_relevant: bool = Field(..., description="Whether change is compliance relevant")
    gdpr_relevant: bool = Field(..., description="Whether change is GDPR relevant")
    soc2_relevant: bool = Field(..., description="Whether change is SOC2 relevant")
    timestamp: datetime = Field(..., description="Change timestamp")


class AuditTrailResponse(BaseModel):
    """Schema for asset audit trail response."""

    asset_id: uuid.UUID = Field(..., description="Asset ID")
    audit_logs: List[AuditLogResponse] = Field(..., description="Audit log entries")
    total_changes: int = Field(..., description="Total number of changes")


# Filter and search schemas
class AssetFilters(BaseModel):
    """Schema for asset filtering options."""

    asset_type: Optional[AssetType] = Field(None, description="Filter by asset type")
    security_classification: Optional[SecurityClassification] = Field(
        None, description="Filter by security classification"
    )
    criticality_level: Optional[CriticalityLevel] = Field(None, description="Filter by criticality level")
    environment: Optional[Environment] = Field(None, description="Filter by environment")
    validation_status: Optional[ValidationStatus] = Field(None, description="Filter by validation status")
    owner_team: Optional[str] = Field(None, description="Filter by owner team")
    search: Optional[str] = Field(None, description="Search term for name/description")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    updated_after: Optional[datetime] = Field(None, description="Filter by update date")
    include_deleted: Optional[bool] = Field(False, description="Include soft-deleted assets")


class AssetSearchRequest(BaseModel):
    """Schema for asset search request."""

    query: str = Field(..., min_length=1, description="Search query")
    filters: Optional[AssetFilters] = Field(None, description="Additional filters")
    limit: int = Field(50, ge=1, le=1000, description="Maximum results")
    offset: int = Field(0, ge=0, description="Results offset")
    sort_by: Optional[str] = Field("created_at", description="Sort field")
    sort_order: Optional[str] = Field("desc", description="Sort order (asc/desc)")


class AssetSearchResponse(BaseModel):
    """Schema for asset search response."""

    results: List[AssetResponse] = Field(..., description="Search results")
    total_matches: int = Field(..., description="Total number of matches")
    query: str = Field(..., description="Search query used")
    execution_time: float = Field(..., description="Search execution time in seconds")
