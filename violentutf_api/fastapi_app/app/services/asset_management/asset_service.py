# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Asset Service for Issue #280 Asset Management System.

This module provides core business logic for asset management operations,
including CRUD operations, duplicate detection, and data validation.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import ChangeType, DatabaseAsset
from app.schemas.asset_schemas import AssetCreate, AssetResponse, AssetUpdate
from app.services.asset_management.audit_service import AuditService


class DuplicateAssetError(Exception):
    """Exception raised when attempting to create a duplicate asset."""


class AssetNotFoundError(Exception):
    """Exception raised when an asset is not found."""


class AssetService:
    """Service class for asset management operations."""

    def __init__(self, db: AsyncSession, audit_service: AuditService) -> None:
        """Initialize the asset service.

        Args:
            db: Database session
            audit_service: Audit service for change tracking
        """
        self.db = db
        self.audit_service = audit_service

    async def create_asset(self, asset_data: AssetCreate, created_by: str) -> AssetResponse:
        """Create a new asset with validation and audit logging.

        Args:
            asset_data: Asset creation data
            created_by: User creating the asset

        Returns:
            Created asset response

        Raises:
            DuplicateAssetError: If asset with same identifier already exists
        """
        # Check for duplicate assets
        existing = await self.find_duplicate_asset(asset_data)
        if existing:
            raise DuplicateAssetError(f"Asset already exists: {existing.unique_identifier}")

        # Create asset instance
        db_asset = DatabaseAsset(
            **asset_data.model_dump(),
            discovery_timestamp=datetime.now(timezone.utc),
            created_by=created_by,
            updated_by=created_by,
        )

        # Save to database
        self.db.add(db_asset)
        await self.db.commit()
        await self.db.refresh(db_asset)

        # Log creation in audit trail
        await self.audit_service.log_asset_change(
            asset_id=db_asset.id, change_type=ChangeType.CREATE, changed_by=created_by, change_source="API"
        )

        return AssetResponse.model_validate(db_asset)

    async def get_asset(self, asset_id: uuid.UUID) -> Optional[AssetResponse]:
        """Retrieve an asset by ID.

        Args:
            asset_id: Asset UUID

        Returns:
            Asset response or None if not found
        """
        result = await self.db.execute(
            select(DatabaseAsset).where(and_(DatabaseAsset.id == asset_id, DatabaseAsset.is_deleted.is_(False)))
        )
        asset = result.scalar_one_or_none()

        if asset:
            return AssetResponse.model_validate(asset)
        return None

    async def list_assets(
        self, skip: int = 0, limit: int = 100, filters: Optional[Dict[str, Any]] = None
    ) -> List[AssetResponse]:
        """List assets with optional filtering and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply

        Returns:
            List of asset responses
        """
        query = select(DatabaseAsset).where(DatabaseAsset.is_deleted.is_(False))

        # Apply filters if provided
        if filters:
            if filters.get("asset_type"):
                query = query.where(DatabaseAsset.asset_type == filters["asset_type"])
            if filters.get("security_classification"):
                query = query.where(DatabaseAsset.security_classification == filters["security_classification"])
            if filters.get("environment"):
                query = query.where(DatabaseAsset.environment == filters["environment"])
            if filters.get("search"):
                search_term = f"%{filters['search']}%"
                query = query.where(
                    or_(
                        DatabaseAsset.name.ilike(search_term),
                        DatabaseAsset.purpose_description.ilike(search_term),
                        DatabaseAsset.unique_identifier.ilike(search_term),
                    )
                )

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await self.db.execute(query)
        assets = result.scalars().all()

        return [AssetResponse.model_validate(asset) for asset in assets]

    async def update_asset(self, asset_id: uuid.UUID, asset_data: AssetUpdate, updated_by: str) -> AssetResponse:
        """Update an existing asset.

        Args:
            asset_id: Asset UUID
            asset_data: Update data
            updated_by: User updating the asset

        Returns:
            Updated asset response

        Raises:
            AssetNotFoundError: If asset is not found
        """
        # Get existing asset
        existing_asset = await self.get_asset(asset_id)
        if not existing_asset:
            raise AssetNotFoundError(f"Asset not found: {asset_id}")

        # Get database object
        result = await self.db.execute(select(DatabaseAsset).where(DatabaseAsset.id == asset_id))
        db_asset = result.scalar_one()

        # Update fields that are provided
        update_data = asset_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_asset, field):
                old_value = getattr(db_asset, field)
                setattr(db_asset, field, value)

                # Log field change if value actually changed
                if old_value != value:
                    await self.audit_service.log_asset_change(
                        asset_id=asset_id,
                        change_type=ChangeType.UPDATE,
                        field_changed=field,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(value) if value is not None else None,
                        changed_by=updated_by,
                        change_source="API",
                    )

        # Update metadata
        db_asset.updated_by = updated_by
        db_asset.updated_at = datetime.now(timezone.utc)

        # Save changes
        await self.db.commit()
        await self.db.refresh(db_asset)

        return AssetResponse.model_validate(db_asset)

    async def delete_asset(self, asset_id: uuid.UUID, deleted_by: str) -> bool:
        """Soft delete an asset.

        Args:
            asset_id: Asset UUID
            deleted_by: User deleting the asset

        Returns:
            True if deleted, False if not found
        """
        # Get existing asset
        result = await self.db.execute(
            select(DatabaseAsset).where(and_(DatabaseAsset.id == asset_id, DatabaseAsset.is_deleted.is_(False)))
        )
        db_asset = result.scalar_one_or_none()

        if not db_asset:
            return False

        # Perform soft delete
        db_asset.is_deleted = True
        db_asset.deleted_at = datetime.now(timezone.utc)
        db_asset.deleted_by = deleted_by

        # Save changes
        await self.db.commit()

        # Log deletion
        await self.audit_service.log_asset_change(
            asset_id=asset_id, change_type=ChangeType.DELETE, changed_by=deleted_by, change_source="API"
        )

        return True

    async def find_duplicate_asset(self, asset_data: AssetCreate) -> Optional[DatabaseAsset]:
        """Find potential duplicate assets using multiple criteria.

        Args:
            asset_data: Asset data to check for duplicates

        Returns:
            Existing asset if duplicate found, None otherwise
        """
        # Check by unique identifier (exact match)
        result = await self.db.execute(
            select(DatabaseAsset).where(
                and_(
                    DatabaseAsset.unique_identifier == asset_data.unique_identifier, DatabaseAsset.is_deleted.is_(False)
                )
            )
        )
        exact_match = result.scalar_one_or_none()
        if exact_match:
            return exact_match

        # Check by name, location, and type (similar match)
        result = await self.db.execute(
            select(DatabaseAsset).where(
                and_(
                    DatabaseAsset.name == asset_data.name,
                    DatabaseAsset.location == asset_data.location,
                    DatabaseAsset.asset_type == asset_data.asset_type,
                    DatabaseAsset.is_deleted.is_(False),
                )
            )
        )
        similar_match = result.scalar_one_or_none()
        return similar_match

    async def find_by_identifier(self, unique_identifier: str) -> Optional[DatabaseAsset]:
        """Find asset by unique identifier.

        Args:
            unique_identifier: Unique identifier to search for

        Returns:
            Asset if found, None otherwise
        """
        result = await self.db.execute(
            select(DatabaseAsset).where(
                and_(DatabaseAsset.unique_identifier == unique_identifier, DatabaseAsset.is_deleted.is_(False))
            )
        )
        return result.scalar_one_or_none()

    async def update_from_discovery(
        self, asset_id: uuid.UUID, asset_data: AssetCreate, discovery_metadata: Dict[str, Any]
    ) -> AssetResponse:
        """Update asset from discovery system data.

        Args:
            asset_id: Asset UUID
            asset_data: Discovery asset data
            discovery_metadata: Additional discovery metadata

        Returns:
            Updated asset response
        """
        # Get existing asset
        result = await self.db.execute(select(DatabaseAsset).where(DatabaseAsset.id == asset_id))
        db_asset = result.scalar_one()

        # Update from discovery data
        discovery_fields = [
            "name",
            "location",
            "estimated_size_mb",
            "table_count",
            "database_version",
            "confidence_score",
        ]

        for field in discovery_fields:
            if hasattr(asset_data, field):
                new_value = getattr(asset_data, field)
                if new_value is not None:
                    old_value = getattr(db_asset, field)
                    if old_value != new_value:
                        setattr(db_asset, field, new_value)

                        # Log change
                        await self.audit_service.log_asset_change(
                            asset_id=asset_id,
                            change_type=ChangeType.UPDATE,
                            field_changed=field,
                            old_value=str(old_value) if old_value is not None else None,
                            new_value=str(new_value),
                            changed_by="discovery-system",
                            change_source="DISCOVERY",
                        )

        # Update discovery metadata
        db_asset.discovery_timestamp = datetime.now(timezone.utc)
        db_asset.updated_by = "discovery-system"
        db_asset.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(db_asset)

        return AssetResponse.model_validate(db_asset)

    async def count_assets(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count total number of assets with optional filters.

        Args:
            filters: Optional filters to apply

        Returns:
            Total count of assets
        """
        from sqlalchemy import func

        query = select(func.count(DatabaseAsset.id)).where(DatabaseAsset.is_deleted.is_(False))

        # Apply filters if provided
        if filters:
            if filters.get("asset_type"):
                query = query.where(DatabaseAsset.asset_type == filters["asset_type"])
            if filters.get("security_classification"):
                query = query.where(DatabaseAsset.security_classification == filters["security_classification"])
            if filters.get("environment"):
                query = query.where(DatabaseAsset.environment == filters["environment"])

        result = await self.db.execute(query)
        return result.scalar()

    async def search_assets(self, search_term: str, limit: int = 50, offset: int = 0) -> List[AssetResponse]:
        """Search assets by name, description, or identifier.

        Args:
            search_term: Search term
            limit: Maximum results
            offset: Results offset

        Returns:
            List of matching assets
        """
        search_pattern = f"%{search_term}%"

        query = (
            select(DatabaseAsset)
            .where(
                and_(
                    DatabaseAsset.is_deleted.is_(False),
                    or_(
                        DatabaseAsset.name.ilike(search_pattern),
                        DatabaseAsset.purpose_description.ilike(search_pattern),
                        DatabaseAsset.unique_identifier.ilike(search_pattern),
                        DatabaseAsset.location.ilike(search_pattern),
                    ),
                )
            )
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        assets = result.scalars().all()

        return [AssetResponse.model_validate(asset) for asset in assets]
