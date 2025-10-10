# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Unit tests for ValidationService (Issue #280).

This module provides comprehensive unit tests for the ValidationService class,
covering all validation rules, business logic, and edge cases.
"""

from typing import List

import pytest

from app.models.asset_inventory import AssetType, CriticalityLevel, Environment, SecurityClassification
from app.schemas.asset_schemas import AssetCreate
from app.services.asset_management.validation_service import (
    ValidationError,
    ValidationResult,
    ValidationService,
    ValidationWarning,
)


class TestValidationService:
    """Test cases for ValidationService class."""
    
    def test_validate_asset_data_success(self, validation_service: ValidationService):
        """Test successful validation of valid asset data."""
        # Arrange
        valid_asset = AssetCreate(
            name="Valid PostgreSQL Database",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="valid-postgres-001",
            location="prod-db.company.com:5432",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            confidence_score=95,
            connection_string="postgresql://user:pass@prod-db.company.com:5432/maindb",
            technical_contact="dba-team@company.com",
            encryption_enabled=True,
            access_restricted=True,
            backup_configured=True,
            compliance_requirements={"gdpr": True, "soc2": True}
        )
        
        # Act
        result = validation_service.validate_asset_data(valid_asset)
        
        # Assert
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
    
    def test_validate_asset_name_too_short(self, validation_service: ValidationService):
        """Test validation fails for asset name too short."""
        # Arrange
        invalid_asset = AssetCreate(
            name="AB",  # Too short (< 3 characters)
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="test-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            confidence_score=95
        )
        
        # Act
        result = validation_service.validate_asset_data(invalid_asset)
        
        # Assert
        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert any("name must be at least 3 characters" in error.message for error in result.errors)
    
    def test_validate_asset_name_empty(self, validation_service: ValidationService):
        """Test validation fails for empty asset name."""
        # Arrange
        invalid_asset = AssetCreate(
            name="",  # Empty name
            asset_type=AssetType.SQLITE,
            unique_identifier="test-002",
            location="/tmp/test.db",
            security_classification=SecurityClassification.PUBLIC,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            confidence_score=85
        )
        
        # Act
        result = validation_service.validate_asset_data(invalid_asset)
        
        # Assert
        assert result.is_valid is False
        assert any("name must be at least 3 characters" in error.message for error in result.errors)
    
    def test_validate_asset_name_whitespace_only(self, validation_service: ValidationService):
        """Test validation fails for whitespace-only asset name."""
        # Arrange
        invalid_asset = AssetCreate(
            name="   ",  # Whitespace only
            asset_type=AssetType.DUCKDB,
            unique_identifier="test-003",
            location="/data/test.duckdb",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated",
            confidence_score=90
        )
        
        # Act
        result = validation_service.validate_asset_data(invalid_asset)
        
        # Assert
        assert result.is_valid is False
        assert any("name must be at least 3 characters" in error.message for error in result.errors)
    
    def test_validate_restricted_classification_requires_encryption(self, validation_service: ValidationService):
        """Test validation for restricted assets requiring encryption."""
        # Arrange
        invalid_asset = AssetCreate(
            name="Restricted Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="restricted-001",
            location="secure-db.company.com:5432",
            security_classification=SecurityClassification.RESTRICTED,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="manual",
            confidence_score=100,
            encryption_enabled=False,  # This should trigger error
            technical_contact="security@company.com"
        )
        
        # Act
        result = validation_service.validate_asset_data(invalid_asset)
        
        # Assert
        assert result.is_valid is False
        assert any("Restricted assets must have encryption enabled" in error.message for error in result.errors)
    
    def test_validate_restricted_classification_requires_technical_contact(self, validation_service: ValidationService):
        """Test validation for restricted assets requiring technical contact."""
        # Arrange
        invalid_asset = AssetCreate(
            name="Restricted Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="restricted-002",
            location="secure-db.company.com:5432",
            security_classification=SecurityClassification.RESTRICTED,
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="manual",
            confidence_score=100,
            encryption_enabled=True,
            technical_contact=None  # This should trigger error
        )
        
        # Act
        result = validation_service.validate_asset_data(invalid_asset)
        
        # Assert
        assert result.is_valid is False
        assert any("Restricted assets must have technical contact" in error.message for error in result.errors)
    
    def test_validate_production_environment_public_classification_warning(self, validation_service: ValidationService):
        """Test warning for production assets with public classification."""
        # Arrange
        warning_asset = AssetCreate(
            name="Production Public Asset",
            asset_type=AssetType.SQLITE,
            unique_identifier="prod-public-001",
            location="/app/public.db",
            security_classification=SecurityClassification.PUBLIC,  # Should trigger warning
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            confidence_score=90,
            backup_configured=True
        )
        
        # Act
        result = validation_service.validate_asset_data(warning_asset)
        
        # Assert
        assert result.is_valid is True  # Valid but with warnings
        assert len(result.warnings) >= 1
        assert any("Production assets should not be classified as public" in warning.message for warning in result.warnings)
    
    def test_validate_production_environment_requires_backup(self, validation_service: ValidationService):
        """Test validation for production assets requiring backup."""
        # Arrange
        invalid_asset = AssetCreate(
            name="Production Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="prod-no-backup-001",
            location="prod-db.company.com:5432",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            confidence_score=98,
            backup_configured=False  # This should trigger error
        )
        
        # Act
        result = validation_service.validate_asset_data(invalid_asset)
        
        # Assert
        assert result.is_valid is False
        assert any("Production assets must have backup configured" in error.message for error in result.errors)
    
    def test_validate_postgresql_connection_string_valid(self, validation_service: ValidationService):
        """Test validation of valid PostgreSQL connection string."""
        # Arrange
        valid_asset = AssetCreate(
            name="PostgreSQL with Valid Connection",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="pg-valid-conn-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            confidence_score=95,
            connection_string="postgresql://user:password@localhost:5432/dbname"
        )
        
        # Act
        result = validation_service.validate_asset_data(valid_asset)
        
        # Assert
        assert result.is_valid is True
        assert not any("Invalid PostgreSQL connection string" in error.message for error in result.errors)
    
    def test_validate_postgresql_connection_string_invalid(self, validation_service: ValidationService):
        """Test validation of invalid PostgreSQL connection string."""
        # Arrange
        invalid_asset = AssetCreate(
            name="PostgreSQL with Invalid Connection",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="pg-invalid-conn-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            confidence_score=95,
            connection_string="invalid-connection-string"
        )
        
        # Act
        result = validation_service.validate_asset_data(invalid_asset)
        
        # Assert
        assert result.is_valid is False
        assert any("Invalid PostgreSQL connection string format" in error.message for error in result.errors)
    
    def test_validate_confidence_score_range(self, validation_service: ValidationService):
        """Test validation of confidence score range."""
        # Test confidence score too low
        low_confidence_asset = AssetCreate(
            name="Low Confidence Asset",
            asset_type=AssetType.SQLITE,
            unique_identifier="low-conf-001",
            location="/tmp/test.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            confidence_score=0  # Invalid (too low)
        )
        
        result = validation_service.validate_asset_data(low_confidence_asset)
        assert result.is_valid is False
        assert any("Confidence score must be between 1 and 100" in error.message for error in result.errors)
        
        # Test confidence score too high
        high_confidence_asset = AssetCreate(
            name="High Confidence Asset",
            asset_type=AssetType.SQLITE,
            unique_identifier="high-conf-001",
            location="/tmp/test.db",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            confidence_score=101  # Invalid (too high)
        )
        
        result = validation_service.validate_asset_data(high_confidence_asset)
        assert result.is_valid is False
        assert any("Confidence score must be between 1 and 100" in error.message for error in result.errors)
    
    def test_validate_email_format_valid(self, validation_service: ValidationService):
        """Test validation of valid email formats."""
        # Arrange
        valid_asset = AssetCreate(
            name="Asset with Valid Email",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="valid-email-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            confidence_score=95,
            technical_contact="valid.email@company.com",
            business_contact="business-owner@company.com"
        )
        
        # Act
        result = validation_service.validate_asset_data(valid_asset)
        
        # Assert
        assert result.is_valid is True
        assert not any("Invalid email format" in error.message for error in result.errors)
    
    def test_validate_email_format_invalid(self, validation_service: ValidationService):
        """Test validation of invalid email formats."""
        # Arrange
        invalid_asset = AssetCreate(
            name="Asset with Invalid Email",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="invalid-email-001",
            location="localhost:5432",
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="manual",
            confidence_score=95,
            technical_contact="invalid-email-format",  # Invalid email
            business_contact="another.invalid.email"   # Invalid email
        )
        
        # Act
        result = validation_service.validate_asset_data(invalid_asset)
        
        # Assert
        assert result.is_valid is False
        assert any("Invalid email format for technical_contact" in error.message for error in result.errors)
        assert any("Invalid email format for business_contact" in error.message for error in result.errors)
    
    def test_validate_file_path_consistency(self, validation_service: ValidationService):
        """Test validation of file path consistency for file-based assets."""
        # Valid file path for SQLite
        valid_sqlite = AssetCreate(
            name="Valid SQLite",
            asset_type=AssetType.SQLITE,
            unique_identifier="valid-sqlite-001",
            location="/data/valid.db",
            file_path="/data/valid.db",  # Consistent with location
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            confidence_score=85
        )
        
        result = validation_service.validate_asset_data(valid_sqlite)
        assert result.is_valid is True
        
        # Inconsistent file path
        inconsistent_sqlite = AssetCreate(
            name="Inconsistent SQLite",
            asset_type=AssetType.SQLITE,
            unique_identifier="inconsistent-sqlite-001",
            location="/data/db1.db",
            file_path="/data/db2.db",  # Different from location
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.TESTING,
            discovery_method="manual",
            confidence_score=85
        )
        
        result = validation_service.validate_asset_data(inconsistent_sqlite)
        assert result.is_valid is False
        assert any("file_path should match location for file-based assets" in error.message for error in result.errors)
    
    def test_validate_network_location_format(self, validation_service: ValidationService):
        """Test validation of network location format."""
        # Valid network location
        valid_asset = AssetCreate(
            name="Valid Network Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="valid-network-001",
            location="db.company.com:5432",
            network_location="10.0.1.100:5432",  # Valid IP:port
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated",
            confidence_score=95
        )
        
        result = validation_service.validate_asset_data(valid_asset)
        assert result.is_valid is True
        
        # Invalid network location
        invalid_asset = AssetCreate(
            name="Invalid Network Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="invalid-network-001",
            location="db.company.com:5432",
            network_location="invalid-ip-format",  # Invalid format
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.DEVELOPMENT,
            discovery_method="automated",
            confidence_score=95
        )
        
        result = validation_service.validate_asset_data(invalid_asset)
        assert result.is_valid is False
        assert any("Invalid network location format" in error.message for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_validate_batch_success(self, validation_service: ValidationService, sample_asset_data_list: List[AssetCreate]):
        """Test successful batch validation."""
        # Act
        result = await validation_service.validate_batch(sample_asset_data_list)
        
        # Assert
        assert result["valid_count"] == 3  # All assets in sample_asset_data_list should be valid
        assert result["invalid_count"] == 0
        assert len(result["validation_errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_batch_with_errors(self, validation_service: ValidationService):
        """Test batch validation with some invalid assets."""
        # Arrange - Mix of valid and invalid assets
        mixed_assets = [
            # Valid asset
            AssetCreate(
                name="Valid Asset",
                asset_type=AssetType.POSTGRESQL,
                unique_identifier="valid-001",
                location="localhost:5432",
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.MEDIUM,
                environment=Environment.DEVELOPMENT,
                discovery_method="manual",
                confidence_score=95
            ),
            # Invalid asset - name too short
            AssetCreate(
                name="AB",  # Too short
                asset_type=AssetType.SQLITE,
                unique_identifier="invalid-001",
                location="/tmp/test.db",
                security_classification=SecurityClassification.PUBLIC,
                criticality_level=CriticalityLevel.LOW,
                environment=Environment.TESTING,
                discovery_method="manual",
                confidence_score=85
            ),
            # Invalid asset - restricted without encryption
            AssetCreate(
                name="Restricted Asset",
                asset_type=AssetType.POSTGRESQL,
                unique_identifier="restricted-001",
                location="secure-db.company.com:5432",
                security_classification=SecurityClassification.RESTRICTED,
                criticality_level=CriticalityLevel.CRITICAL,
                environment=Environment.PRODUCTION,
                discovery_method="manual",
                confidence_score=100,
                encryption_enabled=False  # Should trigger error
            )
        ]
        
        # Act
        result = await validation_service.validate_batch(mixed_assets)
        
        # Assert
        assert result["valid_count"] == 1
        assert result["invalid_count"] == 2
        assert len(result["validation_errors"]) == 2
    
    def test_validate_compliance_requirements_format(self, validation_service: ValidationService):
        """Test validation of compliance requirements format."""
        # Valid compliance requirements
        valid_asset = AssetCreate(
            name="Compliant Asset",
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="compliant-001",
            location="localhost:5432",
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION,
            discovery_method="automated",
            confidence_score=98,
            compliance_requirements={
                "gdpr": True,
                "soc2": False,
                "pci_dss": True,
                "custom_policy": "internal-security-policy-v2"
            }
        )
        
        result = validation_service.validate_asset_data(valid_asset)
        assert result.is_valid is True
    
    def test_validation_result_aggregation(self, validation_service: ValidationService):
        """Test that validation results properly aggregate errors and warnings."""
        # Arrange - Asset with multiple validation issues
        problematic_asset = AssetCreate(
            name="X",  # Too short (error)
            asset_type=AssetType.POSTGRESQL,
            unique_identifier="prob-001",
            location="localhost:5432",
            security_classification=SecurityClassification.PUBLIC,  # Warning for production
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION,
            discovery_method="manual",
            confidence_score=0,  # Invalid range (error)
            connection_string="invalid-connection",  # Invalid format (error)
            technical_contact="invalid-email",  # Invalid email (error)
            backup_configured=False  # Required for production (error)
        )
        
        # Act
        result = validation_service.validate_asset_data(problematic_asset)
        
        # Assert
        assert result.is_valid is False
        assert len(result.errors) >= 5  # Multiple errors
        assert len(result.warnings) >= 1  # At least the public classification warning
        
        # Verify specific error messages are present
        error_messages = [error.message for error in result.errors]
        assert any("name must be at least 3 characters" in msg for msg in error_messages)
        assert any("Confidence score must be between 1 and 100" in msg for msg in error_messages)
        assert any("Invalid PostgreSQL connection string format" in msg for msg in error_messages)
        assert any("Invalid email format for technical_contact" in msg for msg in error_messages)
        assert any("Production assets must have backup configured" in msg for msg in error_messages)
        
        # Verify warning message is present
        warning_messages = [warning.message for warning in result.warnings]
        assert any("Production assets should not be classified as public" in msg for msg in warning_messages)