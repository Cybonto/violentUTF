# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Unit tests for Asset Management Database Models (Issue #280).

This module provides comprehensive unit tests for all database models
including DatabaseAsset, AssetRelationship, and AssetAuditLog.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

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
    
    @pytest.mark.asyncio
    async def test_create_database_asset_success(self, async_session: AsyncSession):
        """Test successful creation of a database asset."""
        # Arrange
        asset_data = {
            "name": "Test PostgreSQL",
            "asset_type": AssetType.POSTGRESQL,
            "unique_identifier": "test-postgres-001",
            "location": "localhost:5432",
            "security_classification": SecurityClassification.INTERNAL,
            "criticality_level": CriticalityLevel.MEDIUM,
            "environment": Environment.DEVELOPMENT,
            "discovery_method": "manual",
            "discovery_timestamp": datetime.now(timezone.utc),
            "confidence_score": 95,
            "created_by": "test_user",
            "updated_by": "test_user"
        }
        
        # Act
        asset = DatabaseAsset(**asset_data)
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        # Assert
        assert asset.id is not None
        assert isinstance(asset.id, uuid.UUID)
        assert asset.name == "Test PostgreSQL"
        assert asset.asset_type == AssetType.POSTGRESQL
        assert asset.unique_identifier == "test-postgres-001"
        assert asset.is_deleted is False
        assert asset.created_at is not None
        assert asset.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_database_asset_required_fields(self, async_session: AsyncSession):
        """Test that required fields are enforced."""
        # Test missing name
        with pytest.raises(IntegrityError):
            asset = DatabaseAsset(
                asset_type=AssetType.POSTGRESQL,
                unique_identifier="test-001",
                location="localhost:5432",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.MEDIUM,
                environment=Environment.DEVELOPMENT,
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=95,
                created_by="test_user",
                updated_by="test_user"
            )
            async_session.add(asset)
            await async_session.commit()
    
    @pytest.mark.asyncio
    async def test_database_asset_unique_identifier_constraint(self, async_session: AsyncSession):
        """Test unique identifier constraint."""
        # Create first asset
        asset1 = DatabaseAsset(
            name="Asset 1",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="duplicate-id",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        async_session.add(asset1)
        await async_session.commit()
        
        # Try to create second asset with same unique_identifier
        with pytest.raises(IntegrityError):
            asset2 = DatabaseAsset(
                name="Asset 2",
                asset_type=AssetType.SQLITE,
                unique_identifier="duplicate-id",  # Same as asset1
                location="/tmp/test.db",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.LOW,
                environment=Environment.TESTING,
                discovery_method="manual",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=90,
                created_by="test_user",
                updated_by="test_user"
            )
            async_session.add(asset2)
            await async_session.commit()
    
    @pytest.mark.asyncio
    async def test_database_asset_enum_validation(self, async_session: AsyncSession):
        """Test enum field validation."""
        asset = DatabaseAsset(
            name="Test Asset",
            asset_type=AssetType.DUCKDB,
            unique_identifier="test-duckdb-001",
            location="/data/test.duckdb",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=98,
            validation_status=ValidationStatus.VALIDATED,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        assert asset.asset_type == AssetType.DUCKDB
        assert asset.security_classification == SecurityClassification.CONFIDENTIAL
        assert asset.criticality_level == CriticalityLevel.HIGH
        assert asset.environment == Environment.PRODUCTION
        assert asset.validation_status == ValidationStatus.VALIDATED
    
    @pytest.mark.asyncio
    async def test_database_asset_optional_fields(self, async_session: AsyncSession):
        """Test that optional fields can be None."""
        asset = DatabaseAsset(
            name="Minimal Asset",
            asset_type=AssetType.SQLITE,
            unique_identifier="minimal-001",
            location="/tmp/minimal.db",
            security_classification=SecurityClassification.PUBLIC,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=85,
            created_by="test_user",
            updated_by="test_user",
            # Optional fields as None
            connection_string=None,
            network_location=None,
            file_path=None,
            database_version=None,
            schema_version=None,
            estimated_size_mb=None,
            table_count=None,
            last_modified=None,
            owner_team=None,
            technical_contact=None,
            business_contact=None,
            purpose_description=None,
            last_validated=None,
            backup_last_verified=None,
            compliance_requirements=None,
            documentation_url=None
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        assert asset.connection_string is None
        assert asset.estimated_size_mb is None
        assert asset.technical_contact is None
    
    @pytest.mark.asyncio
    async def test_database_asset_json_field(self, async_session: AsyncSession):
        """Test JSON field for compliance requirements."""
        compliance_data = {
            "gdpr": True,
            "soc2": False,
            "pci_dss": True,
            "custom_requirements": ["encryption", "audit_trail"]
        }
        
        asset = DatabaseAsset(
            name="Compliance Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="compliance-001",
            location="secure-db.company.com:5432",
            security_classification=SecurityClassification.RESTRICTED,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=100,
            compliance_requirements=compliance_data,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        assert asset.compliance_requirements == compliance_data
        assert asset.compliance_requirements["gdpr"] is True
        assert asset.compliance_requirements["custom_requirements"] == ["encryption", "audit_trail"]
    
    @pytest.mark.asyncio
    async def test_database_asset_soft_delete(self, async_session: AsyncSession):
        """Test soft delete functionality."""
        asset = DatabaseAsset(
            name="To Delete Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="delete-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=85,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        # Perform soft delete
        asset.is_deleted = True
        asset.deleted_at = datetime.now(timezone.utc)
        asset.deleted_by = "admin_user"
        
        await async_session.commit()
        await async_session.refresh(asset)
        
        assert asset.is_deleted is True
        assert asset.deleted_at is not None
        assert asset.deleted_by == "admin_user"
    
    def test_database_asset_repr(self):
        """Test string representation of DatabaseAsset."""
        asset = DatabaseAsset(
            name="Test Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="test-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        
        repr_str = repr(asset)
        assert "DatabaseAsset" in repr_str
        assert "Test Asset" in repr_str
        assert "POSTGRESQL" in repr_str


class TestAssetRelationshipModel:
    """Test cases for AssetRelationship model."""
    
    @pytest.mark.asyncio
    async def test_create_asset_relationship_success(self, async_session: AsyncSession):
        """Test successful creation of an asset relationship."""
        # Create two assets first
        source_asset = DatabaseAsset(
            name="Source Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="source-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        
        target_asset = DatabaseAsset(
            name="Target Asset",
            asset_type=AssetType.SQLITE,
            unique_identifier="target-001",
            location="/tmp/target.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=90,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(source_asset)
        async_session.add(target_asset)
        await async_session.commit()
        await async_session.refresh(source_asset)
        await async_session.refresh(target_asset)
        
        # Create relationship
        relationship = AssetRelationship(
            source_asset_id=source_asset.id,
            target_asset_id=target_asset.id,
            relationship_type=RelationshipType.DEPENDS_ON,
            relationship_strength=RelationshipStrength.STRONG,
            description="Source depends on target for data",
            discovered_method="automated",
            confidence_score=88,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(relationship)
        await async_session.commit()
        await async_session.refresh(relationship)
        
        # Assert
        assert relationship.id is not None
        assert relationship.source_asset_id == source_asset.id
        assert relationship.target_asset_id == target_asset.id
        assert relationship.relationship_type == RelationshipType.DEPENDS_ON
        assert relationship.relationship_strength == RelationshipStrength.STRONG
        assert relationship.confidence_score == 88
        assert relationship.is_deleted is False
    
    @pytest.mark.asyncio
    async def test_asset_relationship_foreign_key_constraints(self, async_session: AsyncSession):
        """Test foreign key constraints for asset relationships."""
        fake_uuid = uuid.uuid4()
        
        # Try to create relationship with non-existent asset IDs
        with pytest.raises(IntegrityError):
            relationship = AssetRelationship(
                source_asset_id=fake_uuid,
                target_asset_id=fake_uuid,
                relationship_type=RelationshipType.CONNECTED_TO,
                relationship_strength=RelationshipStrength.WEAK,
                discovered_method="test",
                confidence_score=50
            )
            async_session.add(relationship)
            await async_session.commit()
    
    @pytest.mark.asyncio
    async def test_asset_relationship_enum_values(self, async_session: AsyncSession):
        """Test all enum values for relationships."""
        # Create assets for testing
        source_asset = DatabaseAsset(
            name="Source", asset_type=AssetType.POSTGRESQL,
            unique_identifier="rel-source", location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual", discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95, created_by="test", updated_by="test"
        )
        
        target_asset = DatabaseAsset(
            name="Target", asset_type=AssetType.DUCKDB,
            unique_identifier="rel-target", location="/data/target.duckdb",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual", discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=90, created_by="test", updated_by="test"
        )
        
        async_session.add(source_asset)
        async_session.add(target_asset)
        await async_session.commit()
        await async_session.refresh(source_asset)
        await async_session.refresh(target_asset)
        
        # Test different relationship types
        relationship_types = [
            RelationshipType.DEPENDS_ON,
            RelationshipType.CONNECTED_TO,
            RelationshipType.REPLICATED_FROM,
            RelationshipType.BACKED_UP_TO,
            RelationshipType.SERVES_DATA_TO
        ]
        
        relationship_strengths = [
            RelationshipStrength.WEAK,
            RelationshipStrength.MEDIUM,
            RelationshipStrength.STRONG,
            RelationshipStrength.CRITICAL
        ]
        
        for i, (rel_type, rel_strength) in enumerate(zip(relationship_types, relationship_strengths)):
            relationship = AssetRelationship(
                source_asset_id=source_asset.id,
                target_asset_id=target_asset.id,
                relationship_type=rel_type,
                relationship_strength=rel_strength,
                discovered_method=f"test_{i}",
                confidence_score=80 + i
            )
            async_session.add(relationship)
        
        await async_session.commit()
        
        # Verify all relationships were created
        from sqlalchemy import select
        result = await async_session.execute(
            select(AssetRelationship).where(AssetRelationship.source_asset_id == source_asset.id)
        )
        relationships = result.scalars().all()
        assert len(relationships) == 5
    
    @pytest.mark.asyncio
    async def test_asset_relationship_bidirectional_flag(self, async_session: AsyncSession):
        """Test bidirectional relationship flag."""
        # Create assets
        asset1 = DatabaseAsset(
            name="Asset 1", asset_type=AssetType.POSTGRESQL,
            unique_identifier="bidir-1", location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual", discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95, created_by="test", updated_by="test"
        )
        
        asset2 = DatabaseAsset(
            name="Asset 2", asset_type=AssetType.SQLITE,
            unique_identifier="bidir-2", location="/tmp/asset2.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual", discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=90, created_by="test", updated_by="test"
        )
        
        async_session.add(asset1)
        async_session.add(asset2)
        await async_session.commit()
        await async_session.refresh(asset1)
        await async_session.refresh(asset2)
        
        # Create bidirectional relationship
        relationship = AssetRelationship(
            source_asset_id=asset1.id,
            target_asset_id=asset2.id,
            relationship_type=RelationshipType.CONNECTED_TO,
            relationship_strength=RelationshipStrength.MEDIUM,
            bidirectional=True,
            discovered_method="network_scan",
            confidence_score=85
        )
        
        async_session.add(relationship)
        await async_session.commit()
        await async_session.refresh(relationship)
        
        assert relationship.bidirectional is True
    
    def test_asset_relationship_repr(self):
        """Test string representation of AssetRelationship."""
        relationship = AssetRelationship(
            source_asset_id=uuid.uuid4(),
            target_asset_id=uuid.uuid4(),
            relationship_type=RelationshipType.DEPENDS_ON,
            relationship_strength=RelationshipStrength.STRONG,
            discovered_method="test",
            confidence_score=95
        )
        
        repr_str = repr(relationship)
        assert "AssetRelationship" in repr_str
        assert "DEPENDS_ON" in repr_str
        assert "STRONG" in repr_str


class TestAssetAuditLogModel:
    """Test cases for AssetAuditLog model."""
    
    @pytest.mark.asyncio
    async def test_create_audit_log_success(self, async_session: AsyncSession):
        """Test successful creation of an audit log entry."""
        # Create asset first
        asset = DatabaseAsset(
            name="Audited Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="audit-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        # Create audit log
        audit_log = AssetAuditLog(
            asset_id=asset.id,
            change_type=ChangeType.CREATE,
            field_changed="name",
            new_value="Audited Asset",
            change_reason="Initial asset creation",
            changed_by="test_user",
            change_source="API",
            session_id="test_session_123",
            request_id="req_456",
            compliance_relevant=True,
            gdpr_relevant=False,
            soc2_relevant=True
        )
        
        async_session.add(audit_log)
        await async_session.commit()
        await async_session.refresh(audit_log)
        
        # Assert
        assert audit_log.id is not None
        assert audit_log.asset_id == asset.id
        assert audit_log.change_type == ChangeType.CREATE
        assert audit_log.field_changed == "name"
        assert audit_log.new_value == "Audited Asset"
        assert audit_log.changed_by == "test_user"
        assert audit_log.change_source == "API"
        assert audit_log.compliance_relevant is True
        assert audit_log.timestamp is not None
    
    @pytest.mark.asyncio
    async def test_audit_log_all_change_types(self, async_session: AsyncSession):
        """Test all change types in audit log."""
        # Create asset
        asset = DatabaseAsset(
            name="Change Tracking Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="change-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        # Test all change types
        change_types = [ChangeType.CREATE, ChangeType.UPDATE, ChangeType.DELETE, ChangeType.VALIDATE]
        
        for i, change_type in enumerate(change_types):
            audit_log = AssetAuditLog(
                asset_id=asset.id,
                change_type=change_type,
                field_changed=f"field_{i}",
                old_value=f"old_value_{i}" if change_type == ChangeType.UPDATE else None,
                new_value=f"new_value_{i}",
                change_reason=f"Testing {change_type.value}",
                changed_by="test_user",
                change_source="TEST"
            )
            async_session.add(audit_log)
        
        await async_session.commit()
        
        # Verify all audit logs were created
        from sqlalchemy import select
        result = await async_session.execute(
            select(AssetAuditLog).where(AssetAuditLog.asset_id == asset.id)
        )
        audit_logs = result.scalars().all()
        assert len(audit_logs) == 4
        
        created_change_types = {log.change_type for log in audit_logs}
        assert created_change_types == set(change_types)
    
    @pytest.mark.asyncio
    async def test_audit_log_compliance_flags(self, async_session: AsyncSession):
        """Test compliance-related flags in audit log."""
        # Create asset
        asset = DatabaseAsset(
            name="Compliance Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="compliance-audit-001",
            location="localhost:5432",
            security_classification=SecurityClassification.RESTRICTED,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=100,
            created_by="compliance_user",
            updated_by="compliance_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        # Create audit log with all compliance flags
        audit_log = AssetAuditLog(
            asset_id=asset.id,
            change_type=ChangeType.UPDATE,
            field_changed="security_classification",
            old_value="CONFIDENTIAL",
            new_value="RESTRICTED",
            change_reason="Elevated to restricted due to data sensitivity",
            changed_by="compliance_officer",
            change_source="MANUAL",
            compliance_relevant=True,
            gdpr_relevant=True,
            soc2_relevant=True
        )
        
        async_session.add(audit_log)
        await async_session.commit()
        await async_session.refresh(audit_log)
        
        assert audit_log.compliance_relevant is True
        assert audit_log.gdpr_relevant is True
        assert audit_log.soc2_relevant is True
    
    @pytest.mark.asyncio
    async def test_audit_log_foreign_key_constraint(self, async_session: AsyncSession):
        """Test foreign key constraint for audit log."""
        fake_asset_id = uuid.uuid4()
        
        # Try to create audit log with non-existent asset ID
        with pytest.raises(IntegrityError):
            audit_log = AssetAuditLog(
                asset_id=fake_asset_id,
                change_type=ChangeType.CREATE,
                changed_by="test_user",
                change_source="API"
            )
            async_session.add(audit_log)
            await async_session.commit()
    
    @pytest.mark.asyncio
    async def test_audit_log_timestamp_auto_generation(self, async_session: AsyncSession):
        """Test that timestamp is automatically generated."""
        # Create asset
        asset = DatabaseAsset(
            name="Timestamp Test Asset",
            asset_type=AssetType.SQLITE,
            unique_identifier="timestamp-001",
            location="/tmp/timestamp.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=85,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        # Create audit log without explicit timestamp
        before_creation = datetime.now(timezone.utc)
        
        audit_log = AssetAuditLog(
            asset_id=asset.id,
            change_type=ChangeType.CREATE,
            changed_by="test_user",
            change_source="API"
        )
        
        async_session.add(audit_log)
        await async_session.commit()
        await async_session.refresh(audit_log)
        
        after_creation = datetime.now(timezone.utc)
        
        # Verify timestamp was auto-generated and is within expected range
        assert audit_log.timestamp is not None
        assert before_creation <= audit_log.timestamp <= after_creation
    
    def test_audit_log_repr(self):
        """Test string representation of AssetAuditLog."""
        asset_id = uuid.uuid4()
        audit_log = AssetAuditLog(
            asset_id=asset_id,
            change_type=ChangeType.UPDATE,
            changed_by="test_user",
            change_source="API"
        )
        
        repr_str = repr(audit_log)
        assert "AssetAuditLog" in repr_str
        assert str(asset_id) in repr_str
        assert "UPDATE" in repr_str


class TestModelRelationships:
    """Test relationships between models."""
    
    @pytest.mark.asyncio
    async def test_asset_relationships_navigation(self, async_session: AsyncSession):
        """Test navigation through asset relationships."""
        # Create assets
        source_asset = DatabaseAsset(
            name="Source Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="nav-source",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        
        target_asset = DatabaseAsset(
            name="Target Asset",
            asset_type=AssetType.SQLITE,
            unique_identifier="nav-target",
            location="/tmp/target.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=90,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(source_asset)
        async_session.add(target_asset)
        await async_session.commit()
        await async_session.refresh(source_asset)
        await async_session.refresh(target_asset)
        
        # Create relationship
        relationship = AssetRelationship(
            source_asset_id=source_asset.id,
            target_asset_id=target_asset.id,
            relationship_type=RelationshipType.DEPENDS_ON,
            relationship_strength=RelationshipStrength.MEDIUM,
            discovered_method="test",
            confidence_score=85
        )
        
        async_session.add(relationship)
        await async_session.commit()
        await async_session.refresh(relationship)
        
        # Test relationship navigation
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Load source asset with relationships
        result = await async_session.execute(
            select(DatabaseAsset)
            .options(selectinload(DatabaseAsset.source_relationships))
            .where(DatabaseAsset.id == source_asset.id)
        )
        loaded_source = result.scalar_one()
        
        assert len(loaded_source.source_relationships) == 1
        assert loaded_source.source_relationships[0].target_asset_id == target_asset.id
    
    @pytest.mark.asyncio
    async def test_asset_audit_logs_navigation(self, async_session: AsyncSession):
        """Test navigation to audit logs from asset."""
        # Create asset
        asset = DatabaseAsset(
            name="Audit Navigation Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="audit-nav",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=95,
            created_by="test_user",
            updated_by="test_user"
        )
        
        async_session.add(asset)
        await async_session.commit()
        await async_session.refresh(asset)
        
        # Create multiple audit logs
        for i in range(3):
            audit_log = AssetAuditLog(
                asset_id=asset.id,
                change_type=ChangeType.UPDATE,
                field_changed=f"field_{i}",
                new_value=f"value_{i}",
                changed_by="test_user",
                change_source="API"
            )
            async_session.add(audit_log)
        
        await async_session.commit()
        
        # Test audit log navigation
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        result = await async_session.execute(
            select(DatabaseAsset)
            .options(selectinload(DatabaseAsset.audit_logs))
            .where(DatabaseAsset.id == asset.id)
        )
        loaded_asset = result.scalar_one()
        
        assert len(loaded_asset.audit_logs) == 3
        
        # Verify all audit logs belong to this asset
        for audit_log in loaded_asset.audit_logs:
            assert audit_log.asset_id == asset.id