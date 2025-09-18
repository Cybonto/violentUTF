# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Unit tests for AssetService (Issue #280).

This module provides comprehensive unit tests for the AssetService class,
covering all CRUD operations, business logic, and error handling scenarios.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import (
    DatabaseAsset,
    AssetType,
    SecurityClassification,
    CriticalityLevel,
    Environment,
    ValidationStatus
)
from app.schemas.asset_schemas import AssetCreate, AssetUpdate
from app.services.asset_management.asset_service import AssetService, AssetNotFoundError, DuplicateAssetError
from app.services.asset_management.audit_service import AuditService


class TestAssetService:
    """Test cases for AssetService class."""
    
    @pytest.mark.asyncio
    async def test_create_asset_success(self, async_session: AsyncSession, sample_asset_data: AssetCreate):
        """Test successful asset creation."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Act
        created_asset = await asset_service.create_asset(sample_asset_data, "test_user")
        
        # Assert
        assert created_asset is not None
        assert created_asset.id is not None
        assert created_asset.name == sample_asset_data.name
        assert created_asset.asset_type == sample_asset_data.asset_type
        assert created_asset.unique_identifier == sample_asset_data.unique_identifier
        assert created_asset.created_by == "test_user"
        assert created_asset.updated_by == "test_user"
        assert created_asset.is_deleted is False
    
    @pytest.mark.asyncio
    async def test_create_asset_duplicate_identifier(self, async_session: AsyncSession, sample_asset_data: AssetCreate):
        """Test asset creation with duplicate unique identifier."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Create first asset
        await asset_service.create_asset(sample_asset_data, "test_user")
        
        # Try to create duplicate
        duplicate_data = AssetCreate(
            name="Different Name",
            asset_type=AssetType.SQLITE,
            unique_identifier=sample_asset_data.unique_identifier,  # Same identifier
            location="/tmp/different.db",
            security_classification=SecurityClassification.PUBLIC,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            confidence_score=80
        )
        
        # Act & Assert
        with pytest.raises(DuplicateAssetError):
            await asset_service.create_asset(duplicate_data, "test_user")
    
    @pytest.mark.asyncio
    async def test_get_asset_success(self, async_session: AsyncSession, sample_database_asset: DatabaseAsset):
        """Test successful asset retrieval."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Act
        retrieved_asset = await asset_service.get_asset(sample_database_asset.id)
        
        # Assert
        assert retrieved_asset is not None
        assert retrieved_asset.id == sample_database_asset.id
        assert retrieved_asset.name == sample_database_asset.name
        assert retrieved_asset.asset_type == sample_database_asset.asset_type
    
    @pytest.mark.asyncio
    async def test_get_asset_not_found(self, async_session: AsyncSession):
        """Test asset retrieval with non-existent ID."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        fake_id = uuid.uuid4()
        
        # Act
        result = await asset_service.get_asset(fake_id)
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_asset_soft_deleted(self, async_session: AsyncSession, sample_database_asset: DatabaseAsset):
        """Test that soft-deleted assets are not returned by default."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Soft delete the asset
        sample_database_asset.is_deleted = True
        sample_database_asset.deleted_at = datetime.now(timezone.utc)
        sample_database_asset.deleted_by = "test_user"
        await async_session.commit()
        
        # Act
        result = await asset_service.get_asset(sample_database_asset.id)
        
        # Assert
        assert result is None  # Should not return soft-deleted assets
    
    @pytest.mark.asyncio
    async def test_update_asset_success(self, async_session: AsyncSession, sample_database_asset: DatabaseAsset):
        """Test successful asset update."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        update_data = AssetUpdate(
            name="Updated Asset Name",
            purpose_description="Updated description",
            estimated_size_mb=2048,
            technical_contact="updated@example.com"
        )
        
        # Act
        updated_asset = await asset_service.update_asset(
            sample_database_asset.id, 
            update_data, 
            "update_user"
        )
        
        # Assert
        assert updated_asset is not None
        assert updated_asset.name == "Updated Asset Name"
        assert updated_asset.purpose_description == "Updated description"
        assert updated_asset.estimated_size_mb == 2048
        assert updated_asset.technical_contact == "updated@example.com"
        assert updated_asset.updated_by == "update_user"
        # Unchanged fields should remain the same
        assert updated_asset.asset_type == sample_database_asset.asset_type
        assert updated_asset.unique_identifier == sample_database_asset.unique_identifier
    
    @pytest.mark.asyncio
    async def test_update_asset_not_found(self, async_session: AsyncSession):
        """Test asset update with non-existent ID."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        fake_id = uuid.uuid4()
        
        update_data = AssetUpdate(name="Updated Name")
        
        # Act & Assert
        with pytest.raises(AssetNotFoundError):
            await asset_service.update_asset(fake_id, update_data, "test_user")
    
    @pytest.mark.asyncio
    async def test_delete_asset_success(self, async_session: AsyncSession, sample_database_asset: DatabaseAsset):
        """Test successful asset soft deletion."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Act
        result = await asset_service.delete_asset(sample_database_asset.id, "delete_user")
        
        # Assert
        assert result is True
        
        # Verify asset is soft deleted
        await async_session.refresh(sample_database_asset)
        assert sample_database_asset.is_deleted is True
        assert sample_database_asset.deleted_by == "delete_user"
        assert sample_database_asset.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_delete_asset_not_found(self, async_session: AsyncSession):
        """Test asset deletion with non-existent ID."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        fake_id = uuid.uuid4()
        
        # Act
        result = await asset_service.delete_asset(fake_id, "test_user")
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_assets_success(self, async_session: AsyncSession, sample_asset_data_list: list):
        """Test successful asset listing with pagination."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Create multiple assets
        for asset_data in sample_asset_data_list:
            await asset_service.create_asset(asset_data, "test_user")
        
        # Act
        assets = await asset_service.list_assets(skip=0, limit=10, filters={})
        
        # Assert
        assert len(assets) == 3  # All three assets from sample_asset_data_list
        assert all(not asset.is_deleted for asset in assets)
    
    @pytest.mark.asyncio
    async def test_list_assets_with_filters(self, async_session: AsyncSession, sample_asset_data_list: list):
        """Test asset listing with various filters."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Create multiple assets
        for asset_data in sample_asset_data_list:
            await asset_service.create_asset(asset_data, "test_user")
        
        # Test filter by asset type
        postgresql_assets = await asset_service.list_assets(
            skip=0, limit=10, 
            filters={"asset_type": AssetType.POSTGRESQL}
        )
        assert len(postgresql_assets) == 1
        assert postgresql_assets[0].asset_type == AssetType.POSTGRESQL
        
        # Test filter by environment
        production_assets = await asset_service.list_assets(
            skip=0, limit=10, 
            filters={"environment": Environment.PRODUCTION}
        )
        assert len(production_assets) == 2  # PostgreSQL and DuckDB from sample data
        
        # Test filter by security classification
        confidential_assets = await asset_service.list_assets(
            skip=0, limit=10, 
            filters={"security_classification": SecurityClassification.CONFIDENTIAL}
        )
        assert len(confidential_assets) == 1
        assert confidential_assets[0].security_classification == SecurityClassification.CONFIDENTIAL
    
    @pytest.mark.asyncio
    async def test_list_assets_pagination(self, async_session: AsyncSession):
        """Test asset listing pagination."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Create 5 assets
        for i in range(5):
            asset_data = AssetCreate(
                name=f"Asset {i:02d}",
                asset_type=AssetType.SQLITE,
                unique_identifier=f"asset-{i:02d}",
                location=f"/tmp/asset-{i:02d}.db",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.LOW,
                environment=Environment.TESTING,
                discovery_method="manual",
                confidence_score=85
            )
            await asset_service.create_asset(asset_data, "test_user")
        
        # Test first page
        first_page = await asset_service.list_assets(skip=0, limit=2, filters={})
        assert len(first_page) == 2
        
        # Test second page
        second_page = await asset_service.list_assets(skip=2, limit=2, filters={})
        assert len(second_page) == 2
        
        # Test third page
        third_page = await asset_service.list_assets(skip=4, limit=2, filters={})
        assert len(third_page) == 1
        
        # Ensure no overlap
        first_page_ids = {asset.id for asset in first_page}
        second_page_ids = {asset.id for asset in second_page}
        third_page_ids = {asset.id for asset in third_page}
        
        assert len(first_page_ids & second_page_ids) == 0
        assert len(second_page_ids & third_page_ids) == 0
        assert len(first_page_ids & third_page_ids) == 0
    
    @pytest.mark.asyncio
    async def test_search_assets_success(self, async_session: AsyncSession):
        """Test asset search functionality."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Create assets with searchable content
        searchable_assets = [
            AssetCreate(
                name="Production PostgreSQL Database",
                asset_type=AssetType.POSTGRESQL,
                unique_identifier="prod-pg-001",
                location="prod-db.company.com:5432",
                security_classification=SecurityClassification.CONFIDENTIAL,
                criticality_level=CriticalityLevel.CRITICAL,
                environment=Environment.PRODUCTION,
                discovery_method="automated",
                confidence_score=98,
                purpose_description="Main production database for customer data"
            ),
            AssetCreate(
                name="Analytics DuckDB",
                asset_type=AssetType.DUCKDB,
                unique_identifier="analytics-duck-001",
                location="/data/analytics.duckdb",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.HIGH,
                environment=Environment.PRODUCTION,
                discovery_method="automated",
                confidence_score=95,
                purpose_description="Analytics database for reporting"
            ),
            AssetCreate(
                name="Test SQLite",
                asset_type=AssetType.SQLITE,
                unique_identifier="test-sqlite-001",
                location="/tmp/test.db",
                security_classification=SecurityClassification.PUBLIC,
                criticality_level=CriticalityLevel.LOW,
                environment=Environment.TESTING,
                discovery_method="manual",
                confidence_score=80,
                purpose_description="Simple test database"
            )
        ]
        
        for asset_data in searchable_assets:
            await asset_service.create_asset(asset_data, "test_user")
        
        # Test search by name
        production_results = await asset_service.search_assets("Production", limit=10, offset=0)
        assert len(production_results) == 1
        assert "Production" in production_results[0].name
        
        # Test search by purpose description
        analytics_results = await asset_service.search_assets("analytics", limit=10, offset=0)
        assert len(analytics_results) == 1
        assert "Analytics" in analytics_results[0].name
        
        # Test search by asset type in name
        postgres_results = await asset_service.search_assets("PostgreSQL", limit=10, offset=0)
        assert len(postgres_results) == 1
        assert postgres_results[0].asset_type == AssetType.POSTGRESQL
        
        # Test search with no results
        no_results = await asset_service.search_assets("nonexistent", limit=10, offset=0)
        assert len(no_results) == 0
    
    @pytest.mark.asyncio
    async def test_find_duplicate_asset_exact_match(self, async_session: AsyncSession, sample_asset_data: AssetCreate):
        """Test duplicate detection with exact identifier match."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Create original asset
        await asset_service.create_asset(sample_asset_data, "test_user")
        
        # Test duplicate detection
        duplicate = await asset_service.find_duplicate_asset(sample_asset_data)
        
        # Assert
        assert duplicate is not None
        assert duplicate.unique_identifier == sample_asset_data.unique_identifier
    
    @pytest.mark.asyncio
    async def test_find_duplicate_asset_similar_attributes(self, async_session: AsyncSession):
        """Test duplicate detection with similar attributes."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Create original asset
        original_data = AssetCreate(
            name="Test Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="original-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            confidence_score=95
        )
        await asset_service.create_asset(original_data, "test_user")
        
        # Test with similar but not identical data
        similar_data = AssetCreate(
            name="Test Database",  # Same name
            asset_type=AssetType.POSTGRESQL,  # Same type
            unique_identifier="similar-001",  # Different identifier
            location="localhost:5432",  # Same location
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated",  # Different discovery method
            confidence_score=90
        )
        
        duplicate = await asset_service.find_duplicate_asset(similar_data)
        
        # Assert - should find the similar asset
        assert duplicate is not None
        assert duplicate.name == similar_data.name
        assert duplicate.location == similar_data.location
        assert duplicate.asset_type == similar_data.asset_type
    
    @pytest.mark.asyncio
    async def test_find_duplicate_asset_no_match(self, async_session: AsyncSession, sample_asset_data: AssetCreate):
        """Test duplicate detection with no matches."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Create original asset
        await asset_service.create_asset(sample_asset_data, "test_user")
        
        # Test with completely different data
        different_data = AssetCreate(
            name="Completely Different Database",
            asset_type=AssetType.DUCKDB,
            unique_identifier="different-001",
            location="/data/different.duckdb",
            security_classification=SecurityClassification.PUBLIC,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="automated",
            confidence_score=80
        )
        
        duplicate = await asset_service.find_duplicate_asset(different_data)
        
        # Assert
        assert duplicate is None
    
    @pytest.mark.asyncio
    async def test_get_asset_by_identifier_success(self, async_session: AsyncSession, sample_database_asset: DatabaseAsset):
        """Test successful asset retrieval by unique identifier."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Act
        found_asset = await asset_service.get_asset_by_identifier(sample_database_asset.unique_identifier)
        
        # Assert
        assert found_asset is not None
        assert found_asset.id == sample_database_asset.id
        assert found_asset.unique_identifier == sample_database_asset.unique_identifier
    
    @pytest.mark.asyncio
    async def test_get_asset_by_identifier_not_found(self, async_session: AsyncSession):
        """Test asset retrieval by non-existent identifier."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Act
        result = await asset_service.get_asset_by_identifier("non-existent-identifier")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_from_discovery_success(self, async_session: AsyncSession, sample_database_asset: DatabaseAsset):
        """Test asset update from discovery data."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        discovery_metadata = {
            "discovery_source": "automated_scan",
            "scan_timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence_improvement": 5
        }
        
        update_data = AssetUpdate(
            database_version="15.2",
            estimated_size_mb=3072,
            table_count=42,
            last_validated=datetime.now(timezone.utc)
        )
        
        # Act
        updated_asset = await asset_service.update_from_discovery(
            sample_database_asset.id,
            update_data,
            discovery_metadata
        )
        
        # Assert
        assert updated_asset is not None
        assert updated_asset.database_version == "15.2"
        assert updated_asset.estimated_size_mb == 3072
        assert updated_asset.table_count == 42
        assert updated_asset.last_validated is not None
    
    @pytest.mark.asyncio
    async def test_asset_service_with_audit_logging(self, async_session: AsyncSession, sample_asset_data: AssetCreate):
        """Test that asset operations are properly audited."""
        # Arrange
        audit_service = AuditService(async_session)
        asset_service = AssetService(async_session, audit_service)
        
        # Act - Create asset
        created_asset = await asset_service.create_asset(sample_asset_data, "test_user")
        
        # Verify audit log was created
        from sqlalchemy import select
        from app.models.asset_inventory import AssetAuditLog, ChangeType
        
        result = await async_session.execute(
            select(AssetAuditLog).where(AssetAuditLog.asset_id == created_asset.id)
        )
        audit_logs = result.scalars().all()
        
        assert len(audit_logs) >= 1  # At least one audit log for creation
        creation_log = next((log for log in audit_logs if log.change_type == ChangeType.CREATE), None)
        assert creation_log is not None
        assert creation_log.changed_by == "test_user"
        assert creation_log.change_source == "API"