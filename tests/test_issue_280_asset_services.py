#!/usr/bin/env python3
"""
Test module for Issue #280: Asset Management Database System - Service Tests

This module contains comprehensive unit tests for the asset management service layer
following Test-Driven Development (TDD) principles.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'violentutf_api', 'fastapi_app'))

from app.models.asset_inventory import (
    AssetType,
    ChangeType,
    CriticalityLevel,
    DatabaseAsset,
    Environment,
    SecurityClassification,
    ValidationStatus,
)
from app.schemas.asset_schemas import (
    AssetCreate,
    AssetResponse,
    AssetUpdate,
    BulkImportRequest,
    BulkImportResponse,
    ConflictCandidate,
    ConflictResolution,
    ConflictType,
    DiscoveryReport,
    ImportResult,
    ResolutionAction,
    ValidationResult,
)
from app.services.asset_management.asset_service import (
    AssetService,
    DuplicateAssetError,
)
from app.services.asset_management.audit_service import (
    AuditService,
)
from app.services.asset_management.conflict_resolution import (
    ConflictResolutionService,
)
from app.services.asset_management.discovery_integration import (
    DiscoveryIntegrationService,
)
from app.services.asset_management.validation_service import (
    ValidationService,
)


class TestAssetService:
    """Test cases for AssetService."""

    @pytest.fixture
    def mock_db_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def mock_audit_service(self) -> AsyncMock:
        """Create mock audit service."""
        return AsyncMock(spec=AuditService)

    @pytest.fixture
    def asset_service(
        self, mock_db_session: AsyncMock, mock_audit_service: AsyncMock
    ) -> AssetService:
        """Create AssetService instance with mocked dependencies."""
        return AssetService(db=mock_db_session, audit_service=mock_audit_service)

    @pytest.fixture
    def valid_asset_create_data(self) -> AssetCreate:
        """Provide valid AssetCreate data for testing."""
        return AssetCreate(
            name="Test Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="test-db-01",
            location="test.company.com",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated_scan",
            confidence_score=85
        )

    @pytest.mark.asyncio
    async def test_create_asset_success(
        self,
        asset_service: AssetService,
        mock_db_session: AsyncMock,
        mock_audit_service: AsyncMock,
        valid_asset_create_data: AssetCreate,
    ) -> None:
        """Test successful asset creation."""
        # Mock no duplicate found
        asset_service.find_duplicate_asset = AsyncMock(return_value=None)
        
        # Mock database operations
        mock_db_asset = MagicMock()
        mock_db_asset.id = uuid.uuid4()
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        # Mock audit logging
        mock_audit_service.log_asset_change.return_value = None
        
        # Execute
        with patch(
            'violentutf_api.fastapi_app.app.services.asset_management.asset_service.DatabaseAsset'
        ) as mock_asset_class:
            mock_asset_class.return_value = mock_db_asset
            result = await asset_service.create_asset(valid_asset_create_data, "test_user")
        
        # Verify
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()
        mock_audit_service.log_asset_change.assert_called_once_with(
            asset_id=mock_db_asset.id,
            change_type=ChangeType.CREATE,
            changed_by="test_user",
            change_source="API"
        )

    @pytest.mark.asyncio
    async def test_create_asset_duplicate_error(
        self,
        asset_service: AssetService,
        valid_asset_create_data: AssetCreate,
    ) -> None:
        """Test asset creation with duplicate identifier."""
        # Mock duplicate found
        existing_asset = MagicMock()
        existing_asset.unique_identifier = "test-db-01"
        asset_service.find_duplicate_asset = AsyncMock(return_value=existing_asset)
        
        # Execute and verify exception
        with pytest.raises(DuplicateAssetError) as exc_info:
            await asset_service.create_asset(valid_asset_create_data, "test_user")
        
        assert "Asset already exists: test-db-01" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_find_duplicate_asset_by_identifier(
        self,
        asset_service: AssetService,
        mock_db_session: AsyncMock,
        valid_asset_create_data: AssetCreate,
    ) -> None:
        """Test duplicate detection by unique identifier."""
        # Mock database query result
        existing_asset = MagicMock()
        existing_asset.unique_identifier = "test-db-01"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_asset
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await asset_service.find_duplicate_asset(valid_asset_create_data)
        
        # Verify
        assert result == existing_asset
        mock_db_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_find_duplicate_asset_by_similar_attributes(
        self,
        asset_service: AssetService,
        mock_db_session: AsyncMock,
        valid_asset_create_data: AssetCreate,
    ) -> None:
        """Test duplicate detection by similar attributes."""
        # Mock no exact match found
        mock_result_exact = MagicMock()
        mock_result_exact.scalar_one_or_none.return_value = None
        
        # Mock similar asset found
        similar_asset = MagicMock()
        similar_asset.name = "Test Database"
        mock_result_similar = MagicMock()
        mock_result_similar.scalar_one_or_none.return_value = similar_asset
        
        # Configure mock to return different results for different queries
        mock_db_session.execute.side_effect = [mock_result_exact, mock_result_similar]
        
        # Execute
        result = await asset_service.find_duplicate_asset(valid_asset_create_data)
        
        # Verify
        assert result == similar_asset
        assert mock_db_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_assets_with_filters(
        self,
        asset_service: AssetService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test listing assets with filtering."""
        # Mock database query result
        mock_assets = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_assets
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        filters = {
            "asset_type": "POSTGRESQL",
            "environment": "PRODUCTION",
            "search": "database"
        }
        result = await asset_service.list_assets(skip=0, limit=10, filters=filters)
        
        # Verify query was executed
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_asset_by_id(
        self,
        asset_service: AssetService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test retrieving asset by ID."""
        # Mock database query result
        asset_id = uuid.uuid4()
        mock_asset = MagicMock()
        mock_asset.id = asset_id
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_asset
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await asset_service.get_asset(asset_id)
        
        # Verify
        assert result == mock_asset
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_asset(
        self,
        asset_service: AssetService,
        mock_db_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """Test asset update functionality."""
        # Mock existing asset
        asset_id = uuid.uuid4()
        existing_asset = MagicMock()
        existing_asset.id = asset_id
        existing_asset.name = "Old Name"
        
        asset_service.get_asset = AsyncMock(return_value=existing_asset)
        
        # Mock update data
        update_data = AssetUpdate(name="New Name", confidence_score=95)
        
        # Execute
        result = await asset_service.update_asset(asset_id, update_data, "test_user")
        
        # Verify
        mock_db_session.commit.assert_called_once()
        mock_audit_service.log_asset_change.assert_called()

    @pytest.mark.asyncio
    async def test_delete_asset_soft_delete(
        self,
        asset_service: AssetService,
        mock_db_session: AsyncMock,
        mock_audit_service: AsyncMock,
    ) -> None:
        """Test soft delete functionality."""
        # Mock existing asset
        asset_id = uuid.uuid4()
        existing_asset = MagicMock()
        existing_asset.id = asset_id
        
        asset_service.get_asset = AsyncMock(return_value=existing_asset)
        
        # Execute
        result = await asset_service.delete_asset(asset_id, "test_user")
        
        # Verify audit logging for deletion
        mock_audit_service.log_asset_change.assert_called_with(
            asset_id=asset_id,
            change_type=ChangeType.DELETE,
            changed_by="test_user",
            change_source="API"
        )


class TestValidationService:
    """Test cases for ValidationService."""

    @pytest.fixture
    def validation_service(self) -> ValidationService:
        """Create ValidationService instance."""
        return ValidationService()

    @pytest.fixture
    def valid_asset_data(self) -> AssetCreate:
        """Provide valid asset data for testing."""
        return AssetCreate(
            name="Valid Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="valid-db-01",
            location="valid.company.com",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated_scan",
            confidence_score=85,
            technical_contact="tech@company.com",
            encryption_enabled=False
        )

    @pytest.mark.asyncio
    async def test_validate_asset_data_success(
        self,
        validation_service: ValidationService,
        valid_asset_data: AssetCreate,
    ) -> None:
        """Test successful asset data validation."""
        result = await validation_service.validate_asset_data(valid_asset_data)
        
        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_validate_asset_name_too_short(
        self,
        validation_service: ValidationService,
        valid_asset_data: AssetCreate,
    ) -> None:
        """Test validation failure for short asset name."""
        valid_asset_data.name = "Ab"  # Too short
        
        result = await validation_service.validate_asset_data(valid_asset_data)
        
        assert result.is_valid is False
        assert any("at least 3 characters" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_validate_restricted_asset_requirements(
        self,
        validation_service: ValidationService,
        valid_asset_data: AssetCreate,
    ) -> None:
        """Test validation for restricted asset requirements."""
        valid_asset_data.security_classification = SecurityClassification.RESTRICTED
        valid_asset_data.encryption_enabled = False  # Should require encryption
        valid_asset_data.technical_contact = None  # Should require contact
        
        result = await validation_service.validate_asset_data(valid_asset_data)
        
        assert result.is_valid is False
        assert any("encryption enabled" in error for error in result.errors)
        assert any("technical contact" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_validate_production_environment_requirements(
        self,
        validation_service: ValidationService,
        valid_asset_data: AssetCreate,
    ) -> None:
        """Test validation for production environment requirements."""
        valid_asset_data.environment = Environment.PRODUCTION
        valid_asset_data.security_classification = SecurityClassification.PUBLIC
        valid_asset_data.backup_configured = False
        
        result = await validation_service.validate_asset_data(valid_asset_data)
        
        assert result.is_valid is False
        assert any("backup configured" in error for error in result.errors)
        assert any("should not be classified as public" in warning for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_validate_postgres_connection_string(
        self,
        validation_service: ValidationService,
        valid_asset_data: AssetCreate,
    ) -> None:
        """Test PostgreSQL connection string validation."""
        valid_asset_data.asset_type = AssetType.POSTGRESQL
        valid_asset_data.connection_string = "invalid_connection_string"
        
        # Mock the connection string validation method
        validation_service.validate_postgres_connection_string = MagicMock(return_value=False)
        
        result = await validation_service.validate_asset_data(valid_asset_data)
        
        assert result.is_valid is False
        assert any("Invalid PostgreSQL connection string" in error for error in result.errors)


class TestConflictResolutionService:
    """Test cases for ConflictResolutionService."""

    @pytest.fixture
    def conflict_service(self) -> ConflictResolutionService:
        """Create ConflictResolutionService instance."""
        return ConflictResolutionService(similarity_threshold=0.85)

    @pytest.fixture
    def new_asset_data(self) -> AssetCreate:
        """Provide new asset data for conflict testing."""
        return AssetCreate(
            name="Test Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="test-db-01",
            location="test.company.com",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated_scan",
            confidence_score=85
        )

    @pytest.mark.asyncio
    async def test_detect_exact_identifier_conflict(
        self,
        conflict_service: ConflictResolutionService,
        new_asset_data: AssetCreate,
    ) -> None:
        """Test exact identifier conflict detection."""
        # Mock existing asset with same identifier
        existing_asset = MagicMock()
        existing_asset.unique_identifier = "test-db-01"
        
        conflict_service.find_exact_identifier_match = AsyncMock(return_value=existing_asset)
        conflict_service.find_similar_assets = AsyncMock(return_value=[])
        
        # Execute
        conflicts = await conflict_service.detect_conflicts(new_asset_data)
        
        # Verify
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.EXACT_IDENTIFIER
        assert conflicts[0].confidence_score == 1.0

    @pytest.mark.asyncio
    async def test_detect_similar_attributes_conflict(
        self,
        conflict_service: ConflictResolutionService,
        new_asset_data: AssetCreate,
    ) -> None:
        """Test similar attributes conflict detection."""
        # Mock no exact match
        conflict_service.find_exact_identifier_match = AsyncMock(return_value=None)
        
        # Mock similar asset
        similar_asset = MagicMock()
        similar_asset.name = "Test Database"
        similar_asset.location = "test.company.com"
        conflict_service.find_similar_assets = AsyncMock(return_value=[similar_asset])
        
        # Mock high similarity score
        conflict_service.calculate_similarity_score = MagicMock(return_value=0.90)
        
        # Execute
        conflicts = await conflict_service.detect_conflicts(new_asset_data)
        
        # Verify
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.SIMILAR_ATTRIBUTES
        assert conflicts[0].confidence_score == 0.90

    def test_resolve_conflict_high_confidence_exact_match(
        self,
        conflict_service: ConflictResolutionService,
        new_asset_data: AssetCreate,
    ) -> None:
        """Test automatic resolution for high confidence exact match."""
        conflict = ConflictCandidate(
            existing_asset=MagicMock(),
            conflict_type=ConflictType.EXACT_IDENTIFIER,
            confidence_score=0.95
        )
        
        resolution = conflict_service.resolve_conflict_automatically(conflict, new_asset_data)
        
        assert resolution.action == ResolutionAction.MERGE
        assert resolution.automatic is True
        assert "Exact identifier match" in resolution.reason

    def test_resolve_conflict_high_similarity_manual_review(
        self,
        conflict_service: ConflictResolutionService,
        new_asset_data: AssetCreate,
    ) -> None:
        """Test manual review for high similarity."""
        conflict = ConflictCandidate(
            existing_asset=MagicMock(),
            conflict_type=ConflictType.SIMILAR_ATTRIBUTES,
            confidence_score=0.92
        )
        
        resolution = conflict_service.resolve_conflict_automatically(conflict, new_asset_data)
        
        assert resolution.action == ResolutionAction.MANUAL_REVIEW
        assert resolution.automatic is False
        assert "manual review" in resolution.reason

    def test_resolve_conflict_low_confidence_create_separate(
        self,
        conflict_service: ConflictResolutionService,
        new_asset_data: AssetCreate,
    ) -> None:
        """Test create separate for low confidence."""
        conflict = ConflictCandidate(
            existing_asset=MagicMock(),
            conflict_type=ConflictType.SIMILAR_ATTRIBUTES,
            confidence_score=0.70
        )
        
        resolution = conflict_service.resolve_conflict_automatically(conflict, new_asset_data)
        
        assert resolution.action == ResolutionAction.CREATE_SEPARATE
        assert resolution.automatic is True
        assert "separate asset" in resolution.reason


class TestDiscoveryIntegrationService:
    """Test cases for DiscoveryIntegrationService."""

    @pytest.fixture
    def mock_asset_service(self) -> AsyncMock:
        """Create mock asset service."""
        return AsyncMock(spec=AssetService)

    @pytest.fixture
    def mock_validation_service(self) -> AsyncMock:
        """Create mock validation service."""
        return AsyncMock(spec=ValidationService)

    @pytest.fixture
    def discovery_service(
        self,
        mock_asset_service: AsyncMock,
        mock_validation_service: AsyncMock,
    ) -> DiscoveryIntegrationService:
        """Create DiscoveryIntegrationService instance."""
        return DiscoveryIntegrationService(
            asset_service=mock_asset_service,
            validation_service=mock_validation_service
        )

    @pytest.fixture
    def sample_discovery_report(self) -> DiscoveryReport:
        """Provide sample discovery report for testing."""
        return DiscoveryReport(
            source="automated_scanner",
            timestamp=datetime.now(timezone.utc),
            assets=[
                {
                    "identifier": "discovered-db-01",
                    "name": "Discovered Database",
                    "type": "POSTGRESQL",
                    "location": "discovered.company.com",
                    "confidence": 90,
                    "metadata": {
                        "size_mb": 512,
                        "table_count": 15
                    }
                }
            ]
        )

    @pytest.mark.asyncio
    async def test_process_discovery_report_create_new_asset(
        self,
        discovery_service: DiscoveryIntegrationService,
        mock_asset_service: AsyncMock,
        mock_validation_service: AsyncMock,
        sample_discovery_report: DiscoveryReport,
    ) -> None:
        """Test processing discovery report to create new asset."""
        # Mock validation success
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        mock_validation_service.validate_asset_data.return_value = validation_result
        
        # Mock no existing asset found
        mock_asset_service.find_by_identifier.return_value = None
        
        # Mock asset creation
        created_asset = MagicMock()
        created_asset.id = uuid.uuid4()
        mock_asset_service.create_asset.return_value = created_asset
        
        # Mock data mapping
        discovery_service.map_discovery_to_asset = MagicMock(return_value=MagicMock())
        
        # Execute
        result = await discovery_service.process_discovery_report(sample_discovery_report)
        
        # Verify
        assert result.created_count == 1
        assert result.updated_count == 0
        assert result.error_count == 0
        mock_asset_service.create_asset.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_discovery_report_update_existing_asset(
        self,
        discovery_service: DiscoveryIntegrationService,
        mock_asset_service: AsyncMock,
        mock_validation_service: AsyncMock,
        sample_discovery_report: DiscoveryReport,
    ) -> None:
        """Test processing discovery report to update existing asset."""
        # Mock validation success
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        mock_validation_service.validate_asset_data.return_value = validation_result
        
        # Mock existing asset found
        existing_asset = MagicMock()
        existing_asset.id = uuid.uuid4()
        mock_asset_service.find_by_identifier.return_value = existing_asset
        
        # Mock should update decision
        discovery_service.should_update_asset = MagicMock(return_value=True)
        
        # Mock asset update
        updated_asset = MagicMock()
        mock_asset_service.update_from_discovery.return_value = updated_asset
        
        # Mock data mapping
        discovery_service.map_discovery_to_asset = MagicMock(return_value=MagicMock())
        
        # Execute
        result = await discovery_service.process_discovery_report(sample_discovery_report)
        
        # Verify
        assert result.created_count == 0
        assert result.updated_count == 1
        assert result.error_count == 0
        mock_asset_service.update_from_discovery.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_discovery_report_validation_failure(
        self,
        discovery_service: DiscoveryIntegrationService,
        mock_validation_service: AsyncMock,
        sample_discovery_report: DiscoveryReport,
    ) -> None:
        """Test processing discovery report with validation failure."""
        # Mock validation failure
        validation_result = ValidationResult(
            is_valid=False,
            errors=["Invalid asset type"],
            warnings=[]
        )
        mock_validation_service.validate_asset_data.return_value = validation_result
        
        # Mock data mapping
        discovery_service.map_discovery_to_asset = MagicMock(return_value=MagicMock())
        
        # Execute
        result = await discovery_service.process_discovery_report(sample_discovery_report)
        
        # Verify
        assert result.created_count == 0
        assert result.updated_count == 0
        assert result.error_count == 1
        assert len(result.errors) == 1

    def test_map_discovery_to_asset(
        self,
        discovery_service: DiscoveryIntegrationService,
    ) -> None:
        """Test mapping discovery data to asset schema."""
        discovered_asset = {
            "identifier": "test-db-01",
            "name": "Test Database",
            "type": "POSTGRESQL",
            "location": "test.company.com",
            "confidence": 85,
            "metadata": {
                "size_mb": 256,
                "table_count": 10
            }
        }
        
        # Execute
        asset_data = discovery_service.map_discovery_to_asset(discovered_asset)
        
        # Verify mapping
        assert asset_data.unique_identifier == "test-db-01"
        assert asset_data.name == "Test Database"
        assert asset_data.asset_type == AssetType.POSTGRESQL
        assert asset_data.location == "test.company.com"
        assert asset_data.confidence_score == 85

    def test_should_update_asset_newer_discovery(
        self,
        discovery_service: DiscoveryIntegrationService,
    ) -> None:
        """Test should update decision for newer discovery data."""
        existing_asset = MagicMock()
        existing_asset.discovery_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)
        existing_asset.confidence_score = 80
        
        discovered_asset = MagicMock()
        discovered_asset.discovery_metadata = {
            "timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc),
            "confidence": 90
        }
        
        # Execute
        should_update = discovery_service.should_update_asset(existing_asset, discovered_asset)
        
        # Should update because discovery is newer and has higher confidence
        assert should_update is True


class TestAuditService:
    """Test cases for AuditService."""

    @pytest.fixture
    def mock_db_session(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def audit_service(self, mock_db_session: AsyncMock) -> AuditService:
        """Create AuditService instance."""
        return AuditService(db=mock_db_session)

    @pytest.mark.asyncio
    async def test_log_asset_change(
        self,
        audit_service: AuditService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test logging asset changes."""
        asset_id = uuid.uuid4()
        
        # Execute
        await audit_service.log_asset_change(
            asset_id=asset_id,
            change_type=ChangeType.UPDATE,
            changed_by="test_user",
            change_source="API",
            field_changed="name",
            old_value="Old Name",
            new_value="New Name"
        )
        
        # Verify
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_asset_audit_trail(
        self,
        audit_service: AuditService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test retrieving asset audit trail."""
        asset_id = uuid.uuid4()
        
        # Mock query result
        mock_audit_logs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_audit_logs
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await audit_service.get_asset_audit_trail(asset_id)
        
        # Verify
        assert result == mock_audit_logs
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_compliance_audit_logs(
        self,
        audit_service: AuditService,
        mock_db_session: AsyncMock,
    ) -> None:
        """Test retrieving compliance-relevant audit logs."""
        # Mock query result
        mock_compliance_logs = [MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_compliance_logs
        mock_db_session.execute.return_value = mock_result
        
        # Execute
        result = await audit_service.get_compliance_audit_logs(gdpr_relevant=True)
        
        # Verify
        assert result == mock_compliance_logs
        mock_db_session.execute.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])