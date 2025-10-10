# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for Backup System Core functionality - Issue #267."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# These imports will fail initially (RED phase of TDD)
from scripts.backup_management.backup_system import (
    BackupArchive,
    BackupCompressor,
    BackupIntegrityValidator,
    BackupManager,
    BackupMetadata,
    BackupRetentionManager,
    BackupTier,
)


class TestBackupTier:
    """Test BackupTier enumeration and classification."""

    def test_backup_tier_classification(self):
        """Test backup tier classification logic."""
        # GIVEN: Different database types
        # THEN: Should classify correctly to tiers
        assert BackupTier.classify_database("postgresql") == BackupTier.TIER_1_CRITICAL
        assert BackupTier.classify_database("sqlite") == BackupTier.TIER_2_IMPORTANT
        assert BackupTier.classify_database("duckdb") == BackupTier.TIER_3_USER_SPECIFIC
        assert BackupTier.classify_database("file_config") == BackupTier.TIER_4_REPLACEABLE

    def test_backup_tier_retention_policies(self):
        """Test tier-based retention policies."""
        # GIVEN: Different backup tiers
        tier1 = BackupTier.TIER_1_CRITICAL
        tier2 = BackupTier.TIER_2_IMPORTANT
        tier3 = BackupTier.TIER_3_USER_SPECIFIC
        tier4 = BackupTier.TIER_4_REPLACEABLE
        
        # THEN: Should have appropriate retention periods
        assert tier1.retention_days == 30
        assert tier2.retention_days == 14
        assert tier3.retention_days == 7
        assert tier4.retention_days == 30  # Weekly backups, monthly retention

    def test_backup_tier_frequency(self):
        """Test tier-based backup frequency."""
        # GIVEN: Different backup tiers
        tier1 = BackupTier.TIER_1_CRITICAL
        tier2 = BackupTier.TIER_2_IMPORTANT
        tier3 = BackupTier.TIER_3_USER_SPECIFIC
        tier4 = BackupTier.TIER_4_REPLACEABLE
        
        # THEN: Should have appropriate backup frequencies
        assert tier1.backup_frequency == "daily"
        assert tier2.backup_frequency == "daily"
        assert tier3.backup_frequency == "configurable"
        assert tier4.backup_frequency == "weekly"


class TestBackupMetadata:
    """Test BackupMetadata class functionality."""

    def test_create_backup_metadata(self):
        """Test creating backup metadata with all fields."""
        # GIVEN: Backup metadata parameters
        metadata = BackupMetadata(
            backup_id="backup_267_001",
            service_name="keycloak",
            database_type="postgresql",
            backup_tier=BackupTier.TIER_1_CRITICAL,
            backup_type="full",
            created_by="backup_system",
            description="Automated daily PostgreSQL backup",
            tags=["production", "daily", "tier1"],
            source_host="postgres",
            source_database="keycloak",
            backup_size_bytes=1024000,
            compression_ratio=0.65
        )
        
        # THEN: Metadata should be created correctly
        assert metadata.backup_id == "backup_267_001"
        assert metadata.service_name == "keycloak"
        assert metadata.database_type == "postgresql"
        assert metadata.backup_tier == BackupTier.TIER_1_CRITICAL
        assert metadata.backup_type == "full"
        assert metadata.created_by == "backup_system"
        assert metadata.description == "Automated daily PostgreSQL backup"
        assert metadata.tags == ["production", "daily", "tier1"]
        assert metadata.source_host == "postgres"
        assert metadata.source_database == "keycloak"
        assert metadata.backup_size_bytes == 1024000
        assert metadata.compression_ratio == 0.65
        assert metadata.created_at is not None

    def test_backup_metadata_validation(self):
        """Test backup metadata validation."""
        # GIVEN: Valid metadata
        valid_metadata = BackupMetadata(
            backup_id="backup_valid",
            service_name="keycloak",
            database_type="postgresql",
            backup_tier=BackupTier.TIER_1_CRITICAL,
            backup_type="full",
            created_by="system"
        )
        
        # THEN: Valid metadata should validate
        assert valid_metadata.is_valid()
        assert valid_metadata.validation_errors == []

    def test_backup_metadata_validation_errors(self):
        """Test backup metadata validation with errors."""
        # GIVEN: Invalid metadata
        invalid_metadata = BackupMetadata(
            backup_id="",  # Empty ID
            service_name="keycloak",
            database_type="invalid_type",  # Invalid database type
            backup_tier=BackupTier.TIER_1_CRITICAL,
            backup_type="invalid_type",  # Invalid backup type
            created_by=""  # Empty creator
        )
        
        # THEN: Invalid metadata should not validate
        assert not invalid_metadata.is_valid()
        assert len(invalid_metadata.validation_errors) > 0
        assert "backup_id cannot be empty" in invalid_metadata.validation_errors
        assert "invalid database_type" in " ".join(invalid_metadata.validation_errors)
        assert "invalid backup_type" in " ".join(invalid_metadata.validation_errors)

    def test_backup_metadata_serialization(self):
        """Test backup metadata serialization and deserialization."""
        # GIVEN: Backup metadata
        original = BackupMetadata(
            backup_id="backup_serialize_test",
            service_name="fastapi",
            database_type="sqlite",
            backup_tier=BackupTier.TIER_2_IMPORTANT,
            backup_type="incremental",
            created_by="test_system"
        )
        
        # WHEN: Serializing and deserializing
        serialized = original.to_dict()
        deserialized = BackupMetadata.from_dict(serialized)
        
        # THEN: Data should be preserved
        assert deserialized.backup_id == original.backup_id
        assert deserialized.service_name == original.service_name
        assert deserialized.database_type == original.database_type
        assert deserialized.backup_tier == original.backup_tier
        assert deserialized.backup_type == original.backup_type
        assert deserialized.created_by == original.created_by


class TestBackupArchive:
    """Test BackupArchive class functionality."""

    def test_create_backup_archive(self):
        """Test creating backup archive."""
        # GIVEN: Backup archive parameters
        metadata = BackupMetadata(
            backup_id="archive_test_001",
            service_name="keycloak",
            database_type="postgresql",
            backup_tier=BackupTier.TIER_1_CRITICAL,
            backup_type="full",
            created_by="system"
        )
        
        backup_data = {
            "pg_dump_version": "15.4",
            "database_size": 1024000,
            "tables": ["users", "roles", "sessions"],
            "dump_format": "custom"
        }
        
        archive = BackupArchive(
            metadata=metadata,
            backup_data=backup_data,
            file_path="/backups/postgresql/archive_test_001.backup",
            compression=True,
            encryption=True
        )
        
        # THEN: Archive should be created correctly
        assert archive.metadata == metadata
        assert archive.backup_data == backup_data
        assert archive.file_path == "/backups/postgresql/archive_test_001.backup"
        assert archive.compression is True
        assert archive.encryption is True
        assert archive.checksum is None  # Not calculated yet

    def test_backup_archive_checksum_generation(self):
        """Test backup archive checksum generation."""
        # GIVEN: Backup archive with data
        metadata = BackupMetadata(
            backup_id="checksum_test",
            service_name="fastapi",
            database_type="sqlite",
            backup_tier=BackupTier.TIER_2_IMPORTANT,
            backup_type="full",
            created_by="system"
        )
        
        backup_data = {"database_file": "violentutf_api.db", "size": 512000}
        archive = BackupArchive(metadata=metadata, backup_data=backup_data)
        
        # WHEN: Generating checksum
        checksum1 = archive.generate_checksum()
        checksum2 = archive.generate_checksum()
        
        # THEN: Checksum should be consistent
        assert checksum1 == checksum2
        assert len(checksum1) == 64  # SHA-256 hex digest
        assert archive.checksum == checksum1

    def test_backup_archive_compression(self):
        """Test backup archive compression."""
        # GIVEN: Large backup data
        metadata = BackupMetadata(
            backup_id="compression_test",
            service_name="duckdb_user",
            database_type="duckdb",
            backup_tier=BackupTier.TIER_3_USER_SPECIFIC,
            backup_type="full",
            created_by="system"
        )
        
        # Large repetitive data that should compress well
        backup_data = {
            "memory_data": "x" * 50000,  # 50KB of repeated data
            "conversations": [{"message": "test message"} for _ in range(1000)]
        }
        
        archive = BackupArchive(
            metadata=metadata,
            backup_data=backup_data,
            compression=True
        )
        
        # WHEN: Compressing data
        compressed_data = archive.compress_data()
        
        # THEN: Compressed data should be smaller
        original_size = len(json.dumps(backup_data).encode())
        compressed_size = len(compressed_data)
        
        assert compressed_size < original_size
        assert archive.compression_ratio > 0
        assert archive.compression_ratio < 1.0


class TestBackupIntegrityValidator:
    """Test backup integrity validation functionality."""

    @pytest.fixture
    def temp_backup_file(self):
        """Create temporary backup file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.backup', delete=False) as f:
            test_data = {"test": "backup_data", "timestamp": datetime.now().isoformat()}
            json.dump(test_data, f)
            f.flush()
            yield f.name
        os.unlink(f.name)

    def test_create_integrity_validator(self):
        """Test creating integrity validator."""
        # GIVEN: Integrity validator initialization
        validator = BackupIntegrityValidator()
        
        # THEN: Validator should be initialized
        assert validator is not None
        assert hasattr(validator, 'validate_backup')
        assert hasattr(validator, 'verify_checksum')

    def test_validate_backup_file_exists(self, temp_backup_file):
        """Test validating backup file existence."""
        # GIVEN: Integrity validator and backup file
        validator = BackupIntegrityValidator()
        
        # WHEN: Validating existing file
        result = validator.validate_file_exists(temp_backup_file)
        
        # THEN: Validation should pass
        assert result.is_valid is True
        assert result.error_message is None

    def test_validate_backup_file_missing(self):
        """Test validating missing backup file."""
        # GIVEN: Integrity validator
        validator = BackupIntegrityValidator()
        
        # WHEN: Validating non-existent file
        result = validator.validate_file_exists("/non/existent/backup.file")
        
        # THEN: Validation should fail
        assert result.is_valid is False
        assert "file not found" in result.error_message.lower()

    def test_verify_backup_checksum(self, temp_backup_file):
        """Test backup checksum verification."""
        # GIVEN: Backup file and expected checksum
        validator = BackupIntegrityValidator()
        
        # Calculate expected checksum
        with open(temp_backup_file, 'rb') as f:
            content = f.read()
            expected_checksum = hashlib.sha256(content).hexdigest()
        
        # WHEN: Verifying checksum
        result = validator.verify_checksum(temp_backup_file, expected_checksum)
        
        # THEN: Verification should pass
        assert result.is_valid is True
        assert result.calculated_checksum == expected_checksum

    def test_verify_backup_checksum_mismatch(self, temp_backup_file):
        """Test backup checksum verification with mismatch."""
        # GIVEN: Backup file and incorrect checksum
        validator = BackupIntegrityValidator()
        wrong_checksum = "0" * 64  # Invalid checksum
        
        # WHEN: Verifying checksum
        result = validator.verify_checksum(temp_backup_file, wrong_checksum)
        
        # THEN: Verification should fail
        assert result.is_valid is False
        assert "checksum mismatch" in result.error_message.lower()


class TestBackupCompressor:
    """Test backup compression functionality."""

    def test_create_backup_compressor(self):
        """Test creating backup compressor."""
        # GIVEN: Compressor initialization
        compressor = BackupCompressor(compression_level=6)
        
        # THEN: Compressor should be initialized
        assert compressor.compression_level == 6
        assert hasattr(compressor, 'compress_data')
        assert hasattr(compressor, 'decompress_data')

    def test_compress_json_data(self):
        """Test compressing JSON data."""
        # GIVEN: Large JSON data
        compressor = BackupCompressor()
        test_data = {
            "large_string": "A" * 10000,
            "repeated_list": ["item"] * 1000,
            "nested": {"data": "B" * 5000}
        }
        
        # WHEN: Compressing data
        compressed = compressor.compress_data(test_data)
        
        # THEN: Data should be compressed
        original_size = len(json.dumps(test_data).encode())
        compressed_size = len(compressed)
        
        assert compressed_size < original_size
        assert compressor.last_compression_ratio > 0
        assert compressor.last_compression_ratio < 1.0

    def test_compress_decompress_roundtrip(self):
        """Test compression and decompression roundtrip."""
        # GIVEN: Test data and compressor
        compressor = BackupCompressor()
        original_data = {
            "backup_id": "roundtrip_test",
            "data": {"key1": "value1", "key2": "value2"},
            "timestamp": datetime.now().isoformat()
        }
        
        # WHEN: Compressing and decompressing
        compressed = compressor.compress_data(original_data)
        decompressed = compressor.decompress_data(compressed)
        
        # THEN: Data should be identical
        assert decompressed == original_data


@pytest.mark.asyncio
class TestBackupRetentionManager:
    """Test backup retention management functionality."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    async def test_create_retention_manager(self, temp_backup_dir):
        """Test creating retention manager."""
        # GIVEN: Retention manager initialization
        manager = BackupRetentionManager(backup_directory=temp_backup_dir)
        
        # THEN: Manager should be initialized
        assert str(manager.backup_directory) == temp_backup_dir
        assert hasattr(manager, 'enforce_retention_policy')
        assert hasattr(manager, 'get_expired_backups')

    async def test_enforce_tier1_retention_policy(self, temp_backup_dir):
        """Test enforcing Tier 1 retention policy (30 days)."""
        # GIVEN: Retention manager with Tier 1 backups
        manager = BackupRetentionManager(backup_directory=temp_backup_dir)
        
        # Create mock backups with different ages
        current_time = datetime.now()
        backups = [
            # Recent backup (keep)
            self._create_mock_backup("recent", current_time - timedelta(days=1),
                                   BackupTier.TIER_1_CRITICAL),
            # Old but within retention (keep)
            self._create_mock_backup("within_retention", current_time - timedelta(days=25),
                                   BackupTier.TIER_1_CRITICAL),
            # Expired backup (delete)
            self._create_mock_backup("expired", current_time - timedelta(days=35),
                                   BackupTier.TIER_1_CRITICAL)
        ]
        
        # WHEN: Enforcing retention policy
        deleted_backups = await manager.enforce_retention_policy(
            backups, BackupTier.TIER_1_CRITICAL
        )
        
        # THEN: Only expired backup should be deleted
        assert len(deleted_backups) == 1
        assert deleted_backups[0].backup_id == "expired"

    async def test_get_expired_backups(self, temp_backup_dir):
        """Test getting list of expired backups."""
        # GIVEN: Retention manager with mixed backup ages
        manager = BackupRetentionManager(backup_directory=temp_backup_dir)
        
        current_time = datetime.now()
        backups = [
            self._create_mock_backup("backup1", current_time - timedelta(days=5),
                                   BackupTier.TIER_2_IMPORTANT),
            self._create_mock_backup("backup2", current_time - timedelta(days=20),
                                   BackupTier.TIER_2_IMPORTANT)  # Expired (14-day retention)
        ]
        
        # WHEN: Getting expired backups
        expired = await manager.get_expired_backups(backups, BackupTier.TIER_2_IMPORTANT)
        
        # THEN: Should identify expired backup
        assert len(expired) == 1
        assert expired[0].backup_id == "backup2"

    def _create_mock_backup(self, backup_id: str, created_at: datetime, 
                           tier: BackupTier) -> BackupMetadata:
        """Create mock backup metadata for testing."""
        return BackupMetadata(
            backup_id=backup_id,
            service_name="test_service",
            database_type="postgresql",
            backup_tier=tier,
            backup_type="full",
            created_by="test",
            created_at=created_at
        )


@pytest.mark.asyncio
class TestBackupManager:
    """Test comprehensive backup management functionality."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    async def test_create_backup_manager(self, temp_backup_dir):
        """Test creating backup manager with all components."""
        # GIVEN: Backup manager initialization
        manager = BackupManager(backup_directory=temp_backup_dir)
        
        # THEN: Manager should be initialized with all components
        assert str(manager.backup_directory) == temp_backup_dir
        assert manager.integrity_validator is not None
        assert manager.compressor is not None
        assert manager.retention_manager is not None

    async def test_backup_manager_integration(self, temp_backup_dir):
        """Test backup manager integration with all components."""
        # GIVEN: Backup manager
        manager = BackupManager(backup_directory=temp_backup_dir)
        
        # WHEN: Creating a comprehensive backup
        backup_result = await manager.create_comprehensive_backup(
            service_name="keycloak",
            database_type="postgresql",
            backup_data={"test": "integration_data"},
            backup_tier=BackupTier.TIER_1_CRITICAL,
            compression=True,
            validation=True
        )
        
        # THEN: Backup should be created successfully
        assert backup_result.success is True
        assert backup_result.backup_id is not None
        assert backup_result.backup_metadata.backup_tier == BackupTier.TIER_1_CRITICAL
        assert backup_result.integrity_check_passed is True
        assert backup_result.compression_applied is True

    async def test_backup_manager_failure_handling(self, temp_backup_dir):
        """Test backup manager failure handling."""
        # GIVEN: Backup manager with simulated failure
        manager = BackupManager(backup_directory=temp_backup_dir)
        
        # Mock a failure in the compression component
        with patch.object(manager.compressor, 'compress_data', side_effect=Exception("Compression failed")):
            # WHEN: Attempting to create backup with compression
            backup_result = await manager.create_comprehensive_backup(
                service_name="test_service",
                database_type="sqlite",
                backup_data={"test": "failure_data"},
                backup_tier=BackupTier.TIER_2_IMPORTANT,
                compression=True
            )
            
            # THEN: Backup should fail gracefully
            assert backup_result.success is False
            assert "compression failed" in backup_result.error_message.lower()