# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Unit tests for DiscoveryIntegrationService (Issue #280).

This module provides comprehensive unit tests for the DiscoveryIntegrationService class,
covering integration with Issue #279 discovery system, data mapping, and validation workflows.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset_inventory import (
    DatabaseAsset,
    AssetType,
    SecurityClassification,
    CriticalityLevel,
    Environment
)
from app.schemas.asset_schemas import AssetCreate
from app.services.asset_management.discovery_integration_service import (
    DiscoveryIntegrationService,
    DiscoveryReport,
    DiscoveredAsset,
    ImportResult,
    DiscoveryMetadata
)
from app.services.asset_management.asset_service import AssetService
from app.services.asset_management.validation_service import ValidationService, ValidationResult
from app.services.asset_management.audit_service import AuditService


class TestDiscoveryIntegrationService:
    """Test cases for DiscoveryIntegrationService class."""
    
    @pytest.fixture
    def mock_asset_service(self) -> AsyncMock:
        """Create mock asset service."""
        mock = AsyncMock(spec=AssetService)
        mock.find_by_identifier = AsyncMock()
        mock.create_asset = AsyncMock()
        mock.update_from_discovery = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_validation_service(self) -> MagicMock:
        """Create mock validation service."""
        mock = MagicMock(spec=ValidationService)
        mock.validate_asset_data = MagicMock()
        return mock
    
    @pytest.fixture
    def discovery_service(
        self, 
        mock_asset_service: AsyncMock, 
        mock_validation_service: MagicMock
    ) -> DiscoveryIntegrationService:
        """Create discovery integration service with mocked dependencies."""
        return DiscoveryIntegrationService(mock_asset_service, mock_validation_service)
    
    @pytest.fixture
    def sample_discovered_asset(self) -> DiscoveredAsset:
        """Create sample discovered asset for testing."""
        return DiscoveredAsset(
            identifier="discovered-postgres-001",
            name="Discovered PostgreSQL Database",
            asset_type="POSTGRESQL",
            location="discovered-db.company.com:5432",
            security_classification="CONFIDENTIAL",
            criticality_level="HIGH",
            environment="PRODUCTION",
            discovery_metadata=DiscoveryMetadata(
                discovery_method="network_scan",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=92,
                scanner_version="1.2.3",
                scan_source="automated_discovery",
                additional_properties={
                    "database_version": "14.5",
                    "estimated_size_mb": 5120,
                    "connection_verified": True,
                    "ssl_enabled": True
                }
            ),
            connection_details={
                "host": "discovered-db.company.com",
                "port": 5432,
                "database": "maindb",
                "ssl_mode": "require"
            },
            metadata={
                "discovery_source": "Issue #279",
                "scan_duration_seconds": 12.5,
                "last_activity": "2025-01-15T10:30:00Z"
            }
        )
    
    @pytest.fixture
    def sample_discovery_report(self, sample_discovered_asset: DiscoveredAsset) -> DiscoveryReport:
        """Create sample discovery report for testing."""
        return DiscoveryReport(
            report_id="discovery_report_001",
            scan_timestamp=datetime.now(timezone.utc),
            scan_source="automated_discovery",
            scan_duration_seconds=120.5,
            assets=[
                sample_discovered_asset,
                DiscoveredAsset(
                    identifier="discovered-sqlite-001",
                    name="Discovered SQLite Database",
                    asset_type="SQLITE",
                    location="/app/data/app.db",
                    security_classification="INTERNAL",
                    criticality_level="MEDIUM",
                    environment="DEVELOPMENT",
                    discovery_metadata=DiscoveryMetadata(
                        discovery_method="file_scan",
                        discovery_timestamp=datetime.now(timezone.utc),
                        confidence_score=88,
                        scanner_version="1.2.3",
                        scan_source="automated_discovery"
                    )
                )
            ],
            scan_summary={
                "total_assets_found": 2,
                "new_assets": 2,
                "updated_assets": 0,
                "scan_coverage": "100%"
            }
        )
    
    @pytest.mark.asyncio
    async def test_process_discovery_report_new_assets(
        self,
        discovery_service: DiscoveryIntegrationService,
        sample_discovery_report: DiscoveryReport,
        mock_asset_service: AsyncMock,
        mock_validation_service: MagicMock
    ):
        """Test processing discovery report with new assets."""
        # Arrange
        mock_validation_service.validate_asset_data.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        mock_asset_service.find_by_identifier.return_value = None  # No existing assets
        mock_asset_service.create_asset.return_value = MagicMock(id=uuid.uuid4(), name="Created Asset")
        
        # Act
        result = await discovery_service.process_discovery_report(sample_discovery_report)
        
        # Assert
        assert result.total_processed == 2
        assert result.created_count == 2
        assert result.updated_count == 0
        assert result.error_count == 0
        assert len(result.created_assets) == 2
        assert len(result.updated_assets) == 0
        assert len(result.errors) == 0
        
        # Verify asset service calls
        assert mock_asset_service.find_by_identifier.call_count == 2
        assert mock_asset_service.create_asset.call_count == 2
        assert mock_validation_service.validate_asset_data.call_count == 2
    
    @pytest.mark.asyncio
    async def test_process_discovery_report_existing_assets_update(
        self,
        discovery_service: DiscoveryIntegrationService,
        sample_discovery_report: DiscoveryReport,
        mock_asset_service: AsyncMock,
        mock_validation_service: MagicMock
    ):
        """Test processing discovery report with existing assets that should be updated."""
        # Arrange
        existing_asset = MagicMock()
        existing_asset.id = uuid.uuid4()
        existing_asset.name = "Existing Asset"
        existing_asset.confidence_score = 80  # Lower than discovery confidence
        
        mock_validation_service.validate_asset_data.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        mock_asset_service.find_by_identifier.return_value = existing_asset
        mock_asset_service.update_from_discovery.return_value = existing_asset
        
        # Act
        result = await discovery_service.process_discovery_report(sample_discovery_report)
        
        # Assert
        assert result.total_processed == 2
        assert result.created_count == 0
        assert result.updated_count == 2
        assert result.error_count == 0
        assert len(result.created_assets) == 0
        assert len(result.updated_assets) == 2
        
        # Verify asset service calls
        assert mock_asset_service.find_by_identifier.call_count == 2
        assert mock_asset_service.update_from_discovery.call_count == 2
        assert mock_asset_service.create_asset.call_count == 0
    
    @pytest.mark.asyncio
    async def test_process_discovery_report_validation_errors(
        self,
        discovery_service: DiscoveryIntegrationService,
        sample_discovery_report: DiscoveryReport,
        mock_asset_service: AsyncMock,
        mock_validation_service: MagicMock
    ):
        """Test processing discovery report with validation errors."""
        # Arrange
        from app.services.asset_management.validation_service import ValidationError
        
        # First asset has validation errors, second is valid
        validation_results = [
            ValidationResult(
                is_valid=False,
                errors=[ValidationError(field="name", message="Name too short")],
                warnings=[]
            ),
            ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[]
            )
        ]
        
        mock_validation_service.validate_asset_data.side_effect = validation_results
        mock_asset_service.find_by_identifier.return_value = None
        mock_asset_service.create_asset.return_value = MagicMock(id=uuid.uuid4(), name="Created Asset")
        
        # Act
        result = await discovery_service.process_discovery_report(sample_discovery_report)
        
        # Assert
        assert result.total_processed == 2
        assert result.created_count == 1  # Only valid asset created
        assert result.updated_count == 0
        assert result.error_count == 1  # One validation error
        assert len(result.errors) == 1
        assert "Name too short" in result.errors[0]
        
        # Verify only valid asset was processed
        assert mock_asset_service.create_asset.call_count == 1
    
    @pytest.mark.asyncio
    async def test_process_discovery_report_service_exceptions(
        self,
        discovery_service: DiscoveryIntegrationService,
        sample_discovery_report: DiscoveryReport,
        mock_asset_service: AsyncMock,
        mock_validation_service: MagicMock
    ):
        """Test processing discovery report with service exceptions."""
        # Arrange
        mock_validation_service.validate_asset_data.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        mock_asset_service.find_by_identifier.return_value = None
        
        # First asset creation succeeds, second fails
        mock_asset_service.create_asset.side_effect = [
            MagicMock(id=uuid.uuid4(), name="Created Asset"),
            Exception("Database connection failed")
        ]
        
        # Act
        result = await discovery_service.process_discovery_report(sample_discovery_report)
        
        # Assert
        assert result.total_processed == 2
        assert result.created_count == 1
        assert result.updated_count == 0
        assert result.error_count == 1
        assert len(result.errors) == 1
        assert "Database connection failed" in result.errors[0]
    
    def test_map_discovery_to_asset(
        self,
        discovery_service: DiscoveryIntegrationService,
        sample_discovered_asset: DiscoveredAsset
    ):
        """Test mapping discovered asset to asset creation schema."""
        # Act
        asset_create = discovery_service.map_discovery_to_asset(sample_discovered_asset)
        
        # Assert
        assert isinstance(asset_create, AssetCreate)
        assert asset_create.name == sample_discovered_asset.name
        assert asset_create.asset_type == AssetType.POSTGRESQL
        assert asset_create.unique_identifier == sample_discovered_asset.identifier
        assert asset_create.location == sample_discovered_asset.location
        assert asset_create.security_classification == SecurityClassification.CONFIDENTIAL
        assert asset_create.criticality_level == CriticalityLevel.HIGH
        assert asset_create.environment == Environment.PRODUCTION
        assert asset_create.discovery_method == sample_discovered_asset.discovery_metadata.discovery_method
        assert asset_create.confidence_score == sample_discovered_asset.discovery_metadata.confidence_score
    
    def test_map_discovery_to_asset_with_metadata_extraction(
        self,
        discovery_service: DiscoveryIntegrationService
    ):
        """Test mapping with metadata extraction from additional properties."""
        # Arrange
        discovered_asset = DiscoveredAsset(
            identifier="metadata-test-001",
            name="Metadata Test Database",
            asset_type="POSTGRESQL",
            location="meta-db.company.com:5432",
            security_classification="INTERNAL",
            criticality_level="MEDIUM",
            environment="DEVELOPMENT",
            discovery_metadata=DiscoveryMetadata(
                discovery_method="automated_scan",
                discovery_timestamp=datetime.now(timezone.utc),
                confidence_score=95,
                scanner_version="1.2.3",
                scan_source="discovery_system",
                additional_properties={
                    "database_version": "13.7",
                    "estimated_size_mb": 2048,
                    "table_count": 15,
                    "technical_contact": "dba-team@company.com",
                    "backup_configured": True,
                    "encryption_enabled": True
                }
            )
        )
        
        # Act
        asset_create = discovery_service.map_discovery_to_asset(discovered_asset)
        
        # Assert
        assert asset_create.database_version == "13.7"
        assert asset_create.estimated_size_mb == 2048
        assert asset_create.table_count == 15
        assert asset_create.technical_contact == "dba-team@company.com"
        assert asset_create.backup_configured is True
        assert asset_create.encryption_enabled is True
    
    def test_should_update_asset_newer_discovery(
        self,
        discovery_service: DiscoveryIntegrationService,
        sample_discovered_asset: DiscoveredAsset
    ):
        """Test should_update_asset with newer discovery data."""
        # Arrange
        existing_asset = MagicMock()
        existing_asset.confidence_score = 85
        existing_asset.discovery_timestamp = datetime.now(timezone.utc) - timedelta(days=1)
        
        # Sample discovered asset has confidence_score = 92 and newer timestamp
        
        # Act
        should_update = discovery_service.should_update_asset(existing_asset, sample_discovered_asset)
        
        # Assert
        assert should_update is True
    
    def test_should_update_asset_older_discovery(
        self,
        discovery_service: DiscoveryIntegrationService,
        sample_discovered_asset: DiscoveredAsset
    ):
        """Test should_update_asset with older discovery data."""
        # Arrange
        existing_asset = MagicMock()
        existing_asset.confidence_score = 98  # Higher than discovery
        existing_asset.discovery_timestamp = datetime.now(timezone.utc)  # Newer
        
        # Act
        should_update = discovery_service.should_update_asset(existing_asset, sample_discovered_asset)
        
        # Assert
        assert should_update is False
    
    def test_should_update_asset_significant_confidence_improvement(
        self,
        discovery_service: DiscoveryIntegrationService,
        sample_discovered_asset: DiscoveredAsset
    ):
        """Test should_update_asset with significant confidence improvement."""
        # Arrange
        existing_asset = MagicMock()
        existing_asset.confidence_score = 70  # Significantly lower
        existing_asset.discovery_timestamp = datetime.now(timezone.utc)
        
        # Discovery has confidence_score = 92 (22 point improvement)
        
        # Act
        should_update = discovery_service.should_update_asset(existing_asset, sample_discovered_asset)
        
        # Assert
        assert should_update is True
    
    @pytest.mark.asyncio
    async def test_process_discovery_report_mixed_results(
        self,
        discovery_service: DiscoveryIntegrationService,
        mock_asset_service: AsyncMock,
        mock_validation_service: MagicMock
    ):
        """Test processing discovery report with mixed results (new, updated, errors)."""
        # Arrange
        from app.services.asset_management.validation_service import ValidationError
        
        # Create discovery report with 4 assets
        discovered_assets = [
            DiscoveredAsset(  # Will be created (new)
                identifier="new-asset-001",
                name="New Asset",
                asset_type="POSTGRESQL",
                location="new-db:5432",
                security_classification="INTERNAL",
                criticality_level="MEDIUM",
                environment="DEVELOPMENT",
                discovery_metadata=DiscoveryMetadata(
                    discovery_method="scan",
                    discovery_timestamp=datetime.now(timezone.utc),
                    confidence_score=90,
                    scanner_version="1.0",
                    scan_source="test"
                )
            ),
            DiscoveredAsset(  # Will be updated (existing)
                identifier="existing-asset-001",
                name="Existing Asset",
                asset_type="SQLITE",
                location="/data/existing.db",
                security_classification="INTERNAL",
                criticality_level="HIGH",
                environment="PRODUCTION",
                discovery_metadata=DiscoveryMetadata(
                    discovery_method="scan",
                    discovery_timestamp=datetime.now(timezone.utc),
                    confidence_score=95,
                    scanner_version="1.0",
                    scan_source="test"
                )
            ),
            DiscoveredAsset(  # Will have validation error
                identifier="invalid-asset-001",
                name="X",  # Too short name
                asset_type="DUCKDB",
                location="/data/invalid.duckdb",
                security_classification="PUBLIC",
                criticality_level="LOW",
                environment="TESTING",
                discovery_metadata=DiscoveryMetadata(
                    discovery_method="scan",
                    discovery_timestamp=datetime.now(timezone.utc),
                    confidence_score=80,
                    scanner_version="1.0",
                    scan_source="test"
                )
            ),
            DiscoveredAsset(  # Will have service error
                identifier="error-asset-001",
                name="Error Asset",
                asset_type="POSTGRESQL",
                location="error-db:5432",
                security_classification="INTERNAL",
                criticality_level="MEDIUM",
                environment="DEVELOPMENT",
                discovery_metadata=DiscoveryMetadata(
                    discovery_method="scan",
                    discovery_timestamp=datetime.now(timezone.utc),
                    confidence_score=85,
                    scanner_version="1.0",
                    scan_source="test"
                )
            )
        ]
        
        discovery_report = DiscoveryReport(
            report_id="mixed_results_report",
            scan_timestamp=datetime.now(timezone.utc),
            scan_source="test",
            scan_duration_seconds=60.0,
            assets=discovered_assets,
            scan_summary={"total_assets_found": 4}
        )
        
        # Configure mocks
        validation_results = [
            ValidationResult(is_valid=True, errors=[], warnings=[]),  # new asset - valid
            ValidationResult(is_valid=True, errors=[], warnings=[]),  # existing asset - valid
            ValidationResult(  # invalid asset - validation error
                is_valid=False,
                errors=[ValidationError(field="name", message="Name too short")],
                warnings=[]
            ),
            ValidationResult(is_valid=True, errors=[], warnings=[])   # error asset - valid but will fail in service
        ]
        mock_validation_service.validate_asset_data.side_effect = validation_results
        
        # Mock asset service responses
        existing_asset = MagicMock()
        existing_asset.id = uuid.uuid4()
        existing_asset.confidence_score = 80  # Lower than discovery
        
        def find_by_identifier_side_effect(identifier):
            if identifier == "existing-asset-001":
                return existing_asset
            return None
        
        mock_asset_service.find_by_identifier.side_effect = find_by_identifier_side_effect
        
        # Mock create_asset to succeed for new asset, fail for error asset
        def create_asset_side_effect(asset_data, created_by):
            if asset_data.unique_identifier == "error-asset-001":
                raise Exception("Service error occurred")
            return MagicMock(id=uuid.uuid4(), name=asset_data.name)
        
        mock_asset_service.create_asset.side_effect = create_asset_side_effect
        mock_asset_service.update_from_discovery.return_value = existing_asset
        
        # Act
        result = await discovery_service.process_discovery_report(discovery_report)
        
        # Assert
        assert result.total_processed == 4
        assert result.created_count == 1    # One new asset created
        assert result.updated_count == 1    # One existing asset updated
        assert result.error_count == 2      # One validation error + one service error
        assert len(result.created_assets) == 1
        assert len(result.updated_assets) == 1
        assert len(result.errors) == 2
        
        # Verify error messages
        error_messages = result.errors
        assert any("Name too short" in error for error in error_messages)
        assert any("Service error occurred" in error for error in error_messages)
    
    def test_extract_metadata_from_discovery(
        self,
        discovery_service: DiscoveryIntegrationService
    ):
        """Test metadata extraction from discovery metadata."""
        # Arrange
        discovery_metadata = DiscoveryMetadata(
            discovery_method="network_scan",
            discovery_timestamp=datetime.now(timezone.utc),
            confidence_score=94,
            scanner_version="2.1.0",
            scan_source="automated_discovery",
            additional_properties={
                "database_version": "15.1",
                "schema_version": "1.2.3",
                "estimated_size_mb": 8192,
                "table_count": 47,
                "owner_team": "platform-team",
                "technical_contact": "platform@company.com",
                "business_contact": "product@company.com",
                "purpose_description": "Main application database",
                "network_location": "10.0.2.50:5432",
                "encryption_enabled": True,
                "access_restricted": True,
                "backup_configured": True,
                "documentation_url": "https://wiki.company.com/db-001",
                "compliance_requirements": {
                    "gdpr": True,
                    "soc2": True,
                    "pci_dss": False
                }
            }
        )
        
        # Act
        metadata = discovery_service.extract_metadata_from_discovery(discovery_metadata)
        
        # Assert
        assert metadata["database_version"] == "15.1"
        assert metadata["schema_version"] == "1.2.3"
        assert metadata["estimated_size_mb"] == 8192
        assert metadata["table_count"] == 47
        assert metadata["owner_team"] == "platform-team"
        assert metadata["technical_contact"] == "platform@company.com"
        assert metadata["business_contact"] == "product@company.com"
        assert metadata["purpose_description"] == "Main application database"
        assert metadata["network_location"] == "10.0.2.50:5432"
        assert metadata["encryption_enabled"] is True
        assert metadata["access_restricted"] is True
        assert metadata["backup_configured"] is True
        assert metadata["documentation_url"] == "https://wiki.company.com/db-001"
        assert metadata["compliance_requirements"] == {"gdpr": True, "soc2": True, "pci_dss": False}
    
    def test_import_result_aggregation(self):
        """Test ImportResult aggregation functionality."""
        # Arrange
        result = ImportResult()
        
        # Act - Add various results
        result.add_created(MagicMock(id=uuid.uuid4(), name="Asset 1"))
        result.add_created(MagicMock(id=uuid.uuid4(), name="Asset 2"))
        result.add_updated(MagicMock(id=uuid.uuid4(), name="Asset 3"))
        result.add_error("asset-error-001", "Validation failed")
        result.add_error("asset-error-002", "Service unavailable")
        
        # Assert
        assert result.total_processed == 5
        assert result.created_count == 2
        assert result.updated_count == 1
        assert result.error_count == 2
        assert len(result.created_assets) == 2
        assert len(result.updated_assets) == 1
        assert len(result.errors) == 2
        
        # Verify error format
        assert "asset-error-001: Validation failed" in result.errors
        assert "asset-error-002: Service unavailable" in result.errors