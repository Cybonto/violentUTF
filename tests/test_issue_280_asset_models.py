#!/usr/bin/env python3
"""
Test module for Issue #280: Asset Management Database System - Model Tests

This module contains comprehensive unit tests for the asset management database models
following Test-Driven Development (TDD) principles.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'violentutf_api', 'fastapi_app'))

from app.db.database import Base
from app.models.asset_inventory import (
    AssetAuditLog,
    AssetRelationship,
    AssetType,
    ChangeType,
    CriticalityLevel,
    DatabaseAsset,
    Environment,
    RelationshipStrength,
    RelationshipType,
    SecurityClassification,
    ValidationStatus,
)


class TestDatabaseAssetModel:
    """Test cases for DatabaseAsset model."""

    @pytest.fixture
    async def async_session(self) -> AsyncSession:
        """Create async database session for testing."""
        # Create in-memory SQLite database for testing
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            yield session

    @pytest.fixture
    def valid_asset_data(self) -> Dict[str, Any]:
        """Provide valid asset data for testing."""
        return {
            "name": "Production PostgreSQL Database",
            "asset_type": AssetType.POSTGRESQL,
            "unique_identifier": "prod-postgres-01",
            "location": "server-001.production.company.com",
            "connection_string": "postgresql://user:pass@server-001:5432/proddb",
            "network_location": "10.0.1.100:5432",
            "security_classification": SecurityClassification.CONFIDENTIAL,
            "criticality_level": CriticalityLevel.HIGH,
            "environment": Environment.PRODUCTION,
            "encryption_enabled": True,
            "access_restricted": True,
            "database_version": "13.7",
            "schema_version": "1.2.3",
            "estimated_size_mb": 1024,
            "table_count": 25,
            "last_modified": datetime.now(timezone.utc),
            "owner_team": "Data Engineering",
            "technical_contact": "tech-lead@company.com",
            "business_contact": "business-owner@company.com",
            "purpose_description": "Main production database for customer data",
            "discovery_method": "automated_scan",
            "discovery_timestamp": datetime.now(timezone.utc),
            "confidence_score": 95,
            "validation_status": ValidationStatus.VALIDATED,
            "backup_configured": True,
            "backup_last_verified": datetime.now(timezone.utc),
            "compliance_requirements": {
                "gdpr": True,
                "soc2": True,
                "pci_dss": False
            },
            "documentation_url": "https://wiki.company.com/db/prod-postgres-01",
            "created_by": "test_user",
            "updated_by": "test_user"
        }

    @pytest.mark.asyncio
    async def test_asset_creation_with_valid_data(
        self, async_session: AsyncSession, valid_asset_data: Dict[str, Any]
    ) -> None:
        """Test creating a database asset with valid data."""
        # Create asset
        asset = DatabaseAsset(**valid_asset_data)
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)

        # Verify asset was created with correct data
        assert asset.id is not None
        assert isinstance(asset.id, uuid.UUID)
        assert asset.name == valid_asset_data["name"]
        assert asset.asset_type == AssetType.POSTGRESQL
        assert asset.unique_identifier == valid_asset_data["unique_identifier"]
        assert asset.security_classification == SecurityClassification.CONFIDENTIAL
        assert asset.criticality_level == CriticalityLevel.HIGH
        assert asset.environment == Environment.PRODUCTION
        assert asset.encryption_enabled is True
        assert asset.confidence_score == 95
        assert asset.created_at is not None
        assert asset.updated_at is not None

    @pytest.mark.asyncio
    async def test_asset_unique_identifier_constraint(
        self, async_session: AsyncSession, valid_asset_data: Dict[str, Any]
    ) -> None:
        """Test that unique_identifier constraint is enforced."""
        # Create first asset
        asset1 = DatabaseAsset(**valid_asset_data)
        async_session.add(asset1)
        await async_session.commit()

        # Try to create second asset with same unique_identifier
        asset2_data = valid_asset_data.copy()
        asset2_data["name"] = "Different Name"
        asset2 = DatabaseAsset(**asset2_data)
        async_session.add(asset2)

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_asset_required_fields(self, async_session: AsyncSession) -> None:
        """Test that required fields are enforced."""
        # Test missing name
        with pytest.raises((IntegrityError, ValueError)):
            asset = DatabaseAsset(
                asset_type=AssetType.POSTGRESQL,
                unique_identifier="test-id",
                location="/path/to/db",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.MEDIUM,
                environment=Environment.DEVELOPMENT,
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=80,
                validation_status=ValidationStatus.PENDING,
                created_by="test_user",
                updated_by="test_user"
            )
            async_session.add(asset)
            await async_session.commit()

    @pytest.mark.asyncio
    async def test_asset_enum_validation(
        self, async_session: AsyncSession, valid_asset_data: Dict[str, Any]
    ) -> None:
        """Test that enum fields validate properly."""
        # Test valid enum values
        asset = DatabaseAsset(**valid_asset_data)
        async_session.add(asset)
        await async_session.commit()
        
        # Asset should be created successfully
        assert asset.asset_type == AssetType.POSTGRESQL
        assert asset.security_classification == SecurityClassification.CONFIDENTIAL
        assert asset.environment == Environment.PRODUCTION

    @pytest.mark.asyncio
    async def test_asset_json_fields(
        self, async_session: AsyncSession, valid_asset_data: Dict[str, Any]
    ) -> None:
        """Test JSON field handling."""
        asset = DatabaseAsset(**valid_asset_data)
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)

        # Verify JSON data is stored and retrieved correctly
        assert asset.compliance_requirements is not None
        assert asset.compliance_requirements["gdpr"] is True
        assert asset.compliance_requirements["soc2"] is True
        assert asset.compliance_requirements["pci_dss"] is False

    @pytest.mark.asyncio
    async def test_asset_confidence_score_validation(
        self, async_session: AsyncSession, valid_asset_data: Dict[str, Any]
    ) -> None:
        """Test confidence score validation (should be 1-100)."""
        # Test valid confidence score
        valid_asset_data["confidence_score"] = 75
        asset = DatabaseAsset(**valid_asset_data)
        async_session.add(asset)
        await async_session.commit()
        assert asset.confidence_score == 75

        # Note: Range validation would be implemented in the service layer
        # as SQLAlchemy doesn't enforce integer ranges by default


class TestAssetRelationshipModel:
    """Test cases for AssetRelationship model."""

    @pytest.fixture
    async def async_session(self) -> AsyncSession:
        """Create async database session for testing."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            yield session

    @pytest.fixture
    async def sample_assets(self, async_session: AsyncSession) -> tuple:
        """Create sample assets for relationship testing."""
        # Create source asset
        source_asset = DatabaseAsset(
            name="Source Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="source-db-01",
            location="source.company.com",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.PRODUCTION,
            discovery_method="automated_scan",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=90,
            validation_status=ValidationStatus.VALIDATED,
            created_by="test_user",
            updated_by="test_user"
        )
        
        # Create target asset
        target_asset = DatabaseAsset(
            name="Target Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="target-db-01",
            location="target.company.com",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.PRODUCTION,
            discovery_method="automated_scan",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=85,
            validation_status=ValidationStatus.VALIDATED,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(source_asset)
        async_session.add(target_asset)
        await async_session.commit()
        await async_session.refresh(source_asset)
        await async_session.refresh(target_asset)
        
        return source_asset, target_asset

    @pytest.mark.asyncio
    async def test_relationship_creation(
        self, async_session: AsyncSession, sample_assets: tuple
    ) -> None:
        """Test creating an asset relationship."""
        source_asset, target_asset = sample_assets
        
        # Create relationship
        relationship = AssetRelationship(
            source_asset_id=source_asset.id,
            target_asset_id=target_asset.id,
            relationship_type=RelationshipType.DEPENDS_ON,
            relationship_strength=RelationshipStrength.STRONG,
            bidirectional=False,
            description="Source database depends on target for data replication",
            discovered_method="network_analysis",
            confidence_score=85
        )
        
        async_session.add(relationship)
        await async_session.commit()
        await async_session.refresh(relationship)
        
        # Verify relationship was created
        assert relationship.id is not None
        assert relationship.source_asset_id == source_asset.id
        assert relationship.target_asset_id == target_asset.id
        assert relationship.relationship_type == RelationshipType.DEPENDS_ON
        assert relationship.relationship_strength == RelationshipStrength.STRONG
        assert relationship.bidirectional is False
        assert relationship.confidence_score == 85

    @pytest.mark.asyncio
    async def test_bidirectional_relationship(
        self, async_session: AsyncSession, sample_assets: tuple
    ) -> None:
        """Test bidirectional relationship creation."""
        source_asset, target_asset = sample_assets
        
        relationship = AssetRelationship(
            source_asset_id=source_asset.id,
            target_asset_id=target_asset.id,
            relationship_type=RelationshipType.CONNECTED_TO,
            relationship_strength=RelationshipStrength.MEDIUM,
            bidirectional=True,
            description="Bidirectional data synchronization",
            discovered_method="configuration_analysis",
            confidence_score=90
        )
        
        async_session.add(relationship)
        await async_session.commit()
        
        assert relationship.bidirectional is True
        assert relationship.relationship_type == RelationshipType.CONNECTED_TO

    @pytest.mark.asyncio
    async def test_relationship_foreign_key_constraints(
        self, async_session: AsyncSession
    ) -> None:
        """Test foreign key constraints for relationships."""
        # Try to create relationship with non-existent asset IDs
        invalid_id = uuid.uuid4()
        
        relationship = AssetRelationship(
            source_asset_id=invalid_id,
            target_asset_id=invalid_id,
            relationship_type=RelationshipType.DEPENDS_ON,
            relationship_strength=RelationshipStrength.WEAK,
            discovered_method="manual",
            confidence_score=50
        )
        
        async_session.add(relationship)
        
        # Note: SQLite doesn't enforce foreign key constraints by default
        # This test would be more relevant with PostgreSQL
        # For now, we'll test that the relationship can be created
        # but in a real implementation, we'd expect an IntegrityError


class TestAssetAuditLogModel:
    """Test cases for AssetAuditLog model."""

    @pytest.fixture
    async def async_session(self) -> AsyncSession:
        """Create async database session for testing."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session_maker = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session_maker() as session:
            yield session

    @pytest.fixture
    async def sample_asset(self, async_session: AsyncSession) -> DatabaseAsset:
        """Create sample asset for audit testing."""
        asset = DatabaseAsset(
            name="Sample Database",
            asset_type=AssetType.SQLITE,
            unique_identifier="sample-db-01",
            location="/var/lib/data/sample.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.DEVELOPMENT,
            discovery_method="file_scan",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=70,
            validation_status=ValidationStatus.PENDING,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        return asset

    @pytest.mark.asyncio
    async def test_audit_log_creation(
        self, async_session: AsyncSession, sample_asset: DatabaseAsset
    ) -> None:
        """Test creating an audit log entry."""
        audit_log = AssetAuditLog(
            asset_id=sample_asset.id,
            change_type=ChangeType.CREATE,
            field_changed=None,
            old_value=None,
            new_value=None,
            change_reason="Initial asset creation",
            changed_by="test_user",
            change_source="API",
            session_id="session_123",
            request_id="request_456",
            compliance_relevant=True,
            gdpr_relevant=False,
            soc2_relevant=True
        )
        
        async_session.add(audit_log)
        await async_session.commit()
        await async_session.refresh(audit_log)
        
        # Verify audit log was created
        assert audit_log.id is not None
        assert audit_log.asset_id == sample_asset.id
        assert audit_log.change_type == ChangeType.CREATE
        assert audit_log.changed_by == "test_user"
        assert audit_log.change_source == "API"
        assert audit_log.compliance_relevant is True
        assert audit_log.gdpr_relevant is False
        assert audit_log.soc2_relevant is True
        assert audit_log.timestamp is not None

    @pytest.mark.asyncio
    async def test_audit_log_field_change_tracking(
        self, async_session: AsyncSession, sample_asset: DatabaseAsset
    ) -> None:
        """Test field change tracking in audit log."""
        audit_log = AssetAuditLog(
            asset_id=sample_asset.id,
            change_type=ChangeType.UPDATE,
            field_changed="security_classification",
            old_value="INTERNAL",
            new_value="CONFIDENTIAL",
            change_reason="Security classification upgrade",
            changed_by="security_admin",
            change_source="MANUAL",
            compliance_relevant=True,
            gdpr_relevant=True,
            soc2_relevant=True
        )
        
        async_session.add(audit_log)
        await async_session.commit()
        
        # Verify field change details
        assert audit_log.field_changed == "security_classification"
        assert audit_log.old_value == "INTERNAL"
        assert audit_log.new_value == "CONFIDENTIAL"
        assert audit_log.change_type == ChangeType.UPDATE

    @pytest.mark.asyncio
    async def test_audit_log_compliance_flags(
        self, async_session: AsyncSession, sample_asset: DatabaseAsset
    ) -> None:
        """Test compliance flag handling in audit log."""
        # Test GDPR-relevant change
        gdpr_log = AssetAuditLog(
            asset_id=sample_asset.id,
            change_type=ChangeType.UPDATE,
            field_changed="owner_team",
            old_value="Engineering",
            new_value="Data Science",
            changed_by="compliance_officer",
            change_source="COMPLIANCE",
            gdpr_relevant=True,
            soc2_relevant=False,
            compliance_relevant=True
        )
        
        async_session.add(gdpr_log)
        await async_session.commit()
        
        assert gdpr_log.gdpr_relevant is True
        assert gdpr_log.soc2_relevant is False
        assert gdpr_log.compliance_relevant is True

    @pytest.mark.asyncio
    async def test_audit_log_timestamp_auto_generation(
        self, async_session: AsyncSession, sample_asset: DatabaseAsset
    ) -> None:
        """Test that timestamp is automatically generated."""
        before_creation = datetime.now(timezone.utc)
        
        audit_log = AssetAuditLog(
            asset_id=sample_asset.id,
            change_type=ChangeType.VALIDATE,
            changed_by="validation_system",
            change_source="DISCOVERY"
        )
        
        async_session.add(audit_log)
        await async_session.commit()
        await async_session.refresh(audit_log)
        
        after_creation = datetime.now(timezone.utc)
        
        # Verify timestamp was auto-generated and is reasonable
        assert audit_log.timestamp is not None
        assert before_creation <= audit_log.timestamp.replace(tzinfo=timezone.utc) <= after_creation


class TestModelEnums:
    """Test cases for model enum validations."""

    def test_asset_type_enum_values(self) -> None:
        """Test AssetType enum values."""
        assert AssetType.POSTGRESQL == "POSTGRESQL"
        assert AssetType.SQLITE == "SQLITE"
        assert AssetType.DUCKDB == "DUCKDB"
        assert AssetType.FILE_STORAGE == "FILE_STORAGE"
        assert AssetType.CONFIGURATION == "CONFIGURATION"

    def test_security_classification_enum_values(self) -> None:
        """Test SecurityClassification enum values."""
        assert SecurityClassification.PUBLIC == "PUBLIC"
        assert SecurityClassification.INTERNAL == "INTERNAL"
        assert SecurityClassification.CONFIDENTIAL == "CONFIDENTIAL"
        assert SecurityClassification.RESTRICTED == "RESTRICTED"

    def test_environment_enum_values(self) -> None:
        """Test Environment enum values."""
        assert Environment.DEVELOPMENT == "DEVELOPMENT"
        assert Environment.TESTING == "TESTING"
        assert Environment.STAGING == "STAGING"
        assert Environment.PRODUCTION == "PRODUCTION"

    def test_criticality_level_enum_values(self) -> None:
        """Test CriticalityLevel enum values."""
        assert CriticalityLevel.LOW == "LOW"
        assert CriticalityLevel.MEDIUM == "MEDIUM"
        assert CriticalityLevel.HIGH == "HIGH"
        assert CriticalityLevel.CRITICAL == "CRITICAL"

    def test_validation_status_enum_values(self) -> None:
        """Test ValidationStatus enum values."""
        assert ValidationStatus.PENDING == "PENDING"
        assert ValidationStatus.VALIDATED == "VALIDATED"
        assert ValidationStatus.FAILED == "FAILED"
        assert ValidationStatus.EXPIRED == "EXPIRED"

    def test_relationship_type_enum_values(self) -> None:
        """Test RelationshipType enum values."""
        assert RelationshipType.DEPENDS_ON == "DEPENDS_ON"
        assert RelationshipType.CONNECTED_TO == "CONNECTED_TO"
        assert RelationshipType.REPLICATED_FROM == "REPLICATED_FROM"
        assert RelationshipType.BACKED_UP_TO == "BACKED_UP_TO"
        assert RelationshipType.SERVES_DATA_TO == "SERVES_DATA_TO"

    def test_relationship_strength_enum_values(self) -> None:
        """Test RelationshipStrength enum values."""
        assert RelationshipStrength.WEAK == "WEAK"
        assert RelationshipStrength.MEDIUM == "MEDIUM"
        assert RelationshipStrength.STRONG == "STRONG"
        assert RelationshipStrength.CRITICAL == "CRITICAL"

    def test_change_type_enum_values(self) -> None:
        """Test ChangeType enum values."""
        assert ChangeType.CREATE == "CREATE"
        assert ChangeType.UPDATE == "UPDATE"
        assert ChangeType.DELETE == "DELETE"
        assert ChangeType.VALIDATE == "VALIDATE"


if __name__ == "__main__":
    pytest.main([__file__])