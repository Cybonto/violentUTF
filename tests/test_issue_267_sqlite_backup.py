# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for SQLite Backup functionality - Issue #267."""

import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.backup_management.backup_system import (
    BackupArchive,
    BackupMetadata,
    BackupTier,
)

# These imports will fail initially (RED phase of TDD)  
from scripts.backup_management.sqlite_backup import (
    FileCopyResult,
    IntegrityCheckResult,
    SQLiteBackupConfig,
    SQLiteBackupManager,
    SQLiteFileManager,
    SQLiteIntegrityChecker,
    SQLiteRestoreManager,
    WALModeBackupHandler,
)


class TestSQLiteBackupConfig:
    """Test SQLite backup configuration."""

    def test_create_sqlite_config(self):
        """Test creating SQLite backup configuration."""
        # GIVEN: SQLite configuration parameters
        config = SQLiteBackupConfig(
            database_path="/app/app_data/violentutf_api.db",
            backup_format="file_copy",
            wal_mode=True,
            vacuum_before_backup=True,
            verify_integrity=True,
            temp_directory="/tmp/sqlite_backups"
        )
        
        # THEN: Configuration should be created correctly
        assert config.database_path == "/app/app_data/violentutf_api.db"
        assert config.backup_format == "file_copy"
        assert config.wal_mode is True
        assert config.vacuum_before_backup is True
        assert config.verify_integrity is True
        assert config.temp_directory == "/tmp/sqlite_backups"

    def test_sqlite_config_validation(self):
        """Test SQLite configuration validation."""
        # GIVEN: Valid configuration
        valid_config = SQLiteBackupConfig(
            database_path="/valid/path/database.db",
            backup_format="file_copy"
        )
        
        # THEN: Valid configuration should validate
        assert valid_config.is_valid()
        assert len(valid_config.validation_errors) == 0

    def test_sqlite_config_validation_errors(self):
        """Test SQLite configuration validation with errors."""
        # GIVEN: Invalid configuration
        invalid_config = SQLiteBackupConfig(
            database_path="",  # Empty path
            backup_format="invalid_format"  # Invalid format
        )
        
        # THEN: Invalid configuration should not validate
        assert not invalid_config.is_valid()
        assert len(invalid_config.validation_errors) > 0

    def test_sqlite_config_from_fastapi_env(self):
        """Test creating configuration from FastAPI environment."""
        # GIVEN: FastAPI environment variables
        env_vars = {
            "DATABASE_URL": "sqlite+aiosqlite:///app/app_data/violentutf_api.db",
            "SQLITE_WAL_MODE": "true",
            "BACKUP_TEMP_DIR": "/app/temp"
        }
        
        with patch.dict(os.environ, env_vars):
            # WHEN: Creating config from environment
            config = SQLiteBackupConfig.from_fastapi_environment()
            
            # THEN: Configuration should be extracted correctly
            assert "/app/app_data/violentutf_api.db" in config.database_path
            assert config.wal_mode is True
            assert config.temp_directory == "/app/temp"


class TestSQLiteFileManager:
    """Test SQLite file operations and management."""

    @pytest.fixture
    def temp_db_file(self):
        """Create temporary SQLite database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
            
        # Create a simple database with test data
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute("INSERT INTO test_table (name) VALUES ('test_data')")
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_create_file_manager(self):
        """Test creating SQLite file manager."""
        # GIVEN: File manager initialization
        config = SQLiteBackupConfig(
            database_path="/app/data/test.db",
            backup_format="file_copy"
        )
        manager = SQLiteFileManager(config)
        
        # THEN: Manager should be initialized
        assert manager.config == config
        assert hasattr(manager, 'copy_database_file')
        assert hasattr(manager, 'get_database_size')

    def test_get_database_size(self, temp_db_file):
        """Test getting SQLite database file size."""
        # GIVEN: File manager and database
        config = SQLiteBackupConfig(
            database_path=temp_db_file,
            backup_format="file_copy"
        )
        manager = SQLiteFileManager(config)
        
        # WHEN: Getting database size
        size = manager.get_database_size()
        
        # THEN: Should return valid size
        assert size > 0
        assert isinstance(size, int)

    def test_copy_database_file(self, temp_db_file):
        """Test copying SQLite database file."""
        # GIVEN: File manager and destination
        config = SQLiteBackupConfig(
            database_path=temp_db_file,
            backup_format="file_copy"
        )
        manager = SQLiteFileManager(config)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = Path(temp_dir) / "backup.db"
            
            # WHEN: Copying database file
            copy_result = manager.copy_database_file(str(backup_path))
            
            # THEN: Copy should succeed
            assert copy_result.success is True
            assert backup_path.exists()
            assert backup_path.stat().st_size > 0

    def test_get_wal_and_shm_files(self, temp_db_file):
        """Test getting WAL and SHM files."""
        # GIVEN: Database in WAL mode
        config = SQLiteBackupConfig(
            database_path=temp_db_file,
            wal_mode=True
        )
        manager = SQLiteFileManager(config)
        
        # Enable WAL mode
        conn = sqlite3.connect(temp_db_file)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("INSERT INTO test_table (name) VALUES ('wal_test')")
        conn.commit()
        conn.close()
        
        # WHEN: Getting associated files
        associated_files = manager.get_associated_files()
        
        # THEN: Should include database file and potentially WAL/SHM
        assert temp_db_file in associated_files
        assert len(associated_files) >= 1

    def test_verify_file_integrity(self, temp_db_file):
        """Test verifying SQLite file integrity."""
        # GIVEN: File manager
        config = SQLiteBackupConfig(
            database_path=temp_db_file,
            verify_integrity=True
        )
        manager = SQLiteFileManager(config)
        
        # WHEN: Verifying integrity
        integrity_result = manager.verify_file_integrity()
        
        # THEN: Integrity check should pass
        assert integrity_result.is_valid is True
        assert integrity_result.error_message is None


class TestSQLiteIntegrityChecker:
    """Test SQLite integrity checking functionality."""

    @pytest.fixture
    def temp_db_file(self):
        """Create temporary SQLite database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
            
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE integrity_test (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            )
        ''')
        conn.execute("INSERT INTO integrity_test (data) VALUES ('test')")
        conn.commit()
        conn.close()
        
        yield db_path
        os.unlink(db_path)

    def test_create_integrity_checker(self):
        """Test creating integrity checker."""
        # GIVEN: Integrity checker initialization
        checker = SQLiteIntegrityChecker("/path/to/database.db")
        
        # THEN: Checker should be initialized
        assert checker.database_path == "/path/to/database.db"
        assert hasattr(checker, 'check_integrity')
        assert hasattr(checker, 'quick_check')

    def test_check_integrity_success(self, temp_db_file):
        """Test successful integrity check."""
        # GIVEN: Integrity checker with valid database
        checker = SQLiteIntegrityChecker(temp_db_file)
        
        # WHEN: Checking integrity
        result = checker.check_integrity()
        
        # THEN: Check should pass
        assert result.is_valid is True
        assert result.check_type == "full_integrity"
        assert result.error_message is None

    def test_quick_check_success(self, temp_db_file):
        """Test successful quick check."""
        # GIVEN: Integrity checker
        checker = SQLiteIntegrityChecker(temp_db_file)
        
        # WHEN: Performing quick check
        result = checker.quick_check()
        
        # THEN: Quick check should pass
        assert result.is_valid is True
        assert result.check_type == "quick_check"

    def test_check_corrupted_database(self):
        """Test integrity check on corrupted database."""
        # GIVEN: Corrupted database file
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            # Write invalid SQLite data
            f.write(b"This is not a valid SQLite database")
            corrupted_db = f.name
        
        try:
            checker = SQLiteIntegrityChecker(corrupted_db)
            
            # WHEN: Checking integrity
            result = checker.check_integrity()
            
            # THEN: Check should fail
            assert result.is_valid is False
            assert result.error_message is not None
        finally:
            os.unlink(corrupted_db)

    def test_pragma_integrity_check(self, temp_db_file):
        """Test PRAGMA integrity_check execution."""
        # GIVEN: Integrity checker
        checker = SQLiteIntegrityChecker(temp_db_file)
        
        # WHEN: Running PRAGMA integrity_check
        pragma_result = checker.run_pragma_integrity_check()
        
        # THEN: Should return integrity status
        assert pragma_result is not None
        assert isinstance(pragma_result, list)


@pytest.mark.asyncio
class TestWALModeBackupHandler:
    """Test WAL mode backup handling."""

    @pytest.fixture
    def wal_db_file(self):
        """Create SQLite database in WAL mode."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute('''
            CREATE TABLE wal_test (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        ''')
        conn.execute("INSERT INTO wal_test (data) VALUES ('wal_data')")
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup all associated files
        for ext in ['', '-wal', '-shm']:
            file_path = db_path + ext
            if os.path.exists(file_path):
                os.unlink(file_path)

    async def test_create_wal_backup_handler(self):
        """Test creating WAL mode backup handler."""
        # GIVEN: WAL backup handler initialization
        config = SQLiteBackupConfig(
            database_path="/app/data/wal_test.db",
            wal_mode=True
        )
        handler = WALModeBackupHandler(config)
        
        # THEN: Handler should be initialized
        assert handler.config == config
        assert hasattr(handler, 'create_consistent_backup')
        assert hasattr(handler, 'checkpoint_wal')

    async def test_checkpoint_wal(self, wal_db_file):
        """Test WAL checkpointing."""
        # GIVEN: WAL backup handler
        config = SQLiteBackupConfig(
            database_path=wal_db_file,
            wal_mode=True
        )
        handler = WALModeBackupHandler(config)
        
        # WHEN: Checkpointing WAL
        checkpoint_result = await handler.checkpoint_wal()
        
        # THEN: Checkpointing should succeed
        assert checkpoint_result.success is True
        assert checkpoint_result.pages_checkpointed >= 0

    async def test_create_consistent_backup(self, wal_db_file):
        """Test creating consistent backup with WAL mode."""
        # GIVEN: WAL backup handler
        config = SQLiteBackupConfig(
            database_path=wal_db_file,
            wal_mode=True
        )
        handler = WALModeBackupHandler(config)
        
        with tempfile.TemporaryDirectory() as backup_dir:
            backup_path = Path(backup_dir) / "consistent_backup.db"
            
            # WHEN: Creating consistent backup
            backup_result = await handler.create_consistent_backup(str(backup_path))
            
            # THEN: Backup should be created consistently
            assert backup_result.success is True
            assert backup_path.exists()
            assert backup_result.consistency_verified is True


@pytest.mark.asyncio
class TestSQLiteBackupManager:
    """Test comprehensive SQLite backup management."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def sample_db(self):
        """Create sample SQLite database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
            
        conn = sqlite3.connect(db_path)
        conn.execute('''
            CREATE TABLE orchestrator_configurations (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                config_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE orchestrator_executions (
                id INTEGER PRIMARY KEY,
                config_id INTEGER,
                status TEXT,
                results TEXT,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (config_id) REFERENCES orchestrator_configurations (id)
            )
        ''')
        conn.execute(
            "INSERT INTO orchestrator_configurations (name, config_json) VALUES (?, ?)",
            ("test_config", '{"param": "value"}')
        )
        conn.commit()
        conn.close()
        
        yield db_path
        os.unlink(db_path)

    async def test_create_sqlite_backup_manager(self, temp_backup_dir, sample_db):
        """Test creating SQLite backup manager."""
        # GIVEN: Backup manager initialization
        config = SQLiteBackupConfig(
            database_path=sample_db,
            backup_format="file_copy"
        )
        manager = SQLiteBackupManager(
            config=config,
            backup_directory=temp_backup_dir
        )
        
        # THEN: Manager should be initialized
        assert manager.config == config
        assert str(manager.backup_directory) == temp_backup_dir
        assert manager.file_manager is not None
        assert manager.integrity_checker is not None

    async def test_create_full_backup(self, temp_backup_dir, sample_db):
        """Test creating full SQLite backup."""
        # GIVEN: Backup manager
        config = SQLiteBackupConfig(
            database_path=sample_db,
            backup_format="file_copy",
            verify_integrity=True
        )
        manager = SQLiteBackupManager(
            config=config,
            backup_directory=temp_backup_dir
        )
        
        # WHEN: Creating full backup
        backup_result = await manager.create_full_backup(
            backup_id="sqlite_full_001",
            created_by="automated_system"
        )
        
        # THEN: Backup should be created successfully
        assert backup_result.success is True
        assert backup_result.backup_metadata.backup_type == "full"
        assert backup_result.backup_metadata.backup_tier == BackupTier.TIER_2_IMPORTANT
        assert backup_result.backup_metadata.database_type == "sqlite"
        assert backup_result.integrity_verified is True

    async def test_create_incremental_backup(self, temp_backup_dir, sample_db):
        """Test creating incremental SQLite backup."""
        # GIVEN: Backup manager with previous full backup
        config = SQLiteBackupConfig(
            database_path=sample_db,
            backup_format="file_copy"
        )
        manager = SQLiteBackupManager(
            config=config,
            backup_directory=temp_backup_dir
        )
        
        # Create full backup first
        full_backup_result = await manager.create_full_backup(
            backup_id="sqlite_full_base",
            created_by="system"
        )
        
        # Add more data to database
        conn = sqlite3.connect(sample_db)
        conn.execute(
            "INSERT INTO orchestrator_configurations (name, config_json) VALUES (?, ?)",
            ("incremental_config", '{"incremental": "data"}')
        )
        conn.commit()
        conn.close()
        
        # WHEN: Creating incremental backup
        incremental_result = await manager.create_incremental_backup(
            backup_id="sqlite_incremental_001",
            base_backup_id="sqlite_full_base",
            created_by="system"
        )
        
        # THEN: Incremental backup should be created
        assert incremental_result.success is True
        assert incremental_result.backup_metadata.backup_type == "incremental"
        assert incremental_result.backup_metadata.parent_backup_id == "sqlite_full_base"

    async def test_backup_with_vacuum(self, temp_backup_dir, sample_db):
        """Test backup with VACUUM operation."""
        # GIVEN: Backup manager with vacuum enabled
        config = SQLiteBackupConfig(
            database_path=sample_db,
            backup_format="file_copy",
            vacuum_before_backup=True
        )
        manager = SQLiteBackupManager(
            config=config,
            backup_directory=temp_backup_dir
        )
        
        # WHEN: Creating backup with vacuum
        backup_result = await manager.create_full_backup(
            backup_id="sqlite_vacuum_001",
            created_by="system"
        )
        
        # THEN: Backup should succeed with vacuum optimization
        assert backup_result.success is True
        assert backup_result.vacuum_performed is True
        assert backup_result.backup_metadata.backup_size_bytes > 0

    async def test_backup_wal_mode_database(self, temp_backup_dir):
        """Test backing up database in WAL mode."""
        # GIVEN: Database in WAL mode
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            wal_db_path = f.name
        
        try:
            conn = sqlite3.connect(wal_db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE wal_table (id INTEGER PRIMARY KEY, data TEXT)")
            conn.execute("INSERT INTO wal_table (data) VALUES ('wal_test')")
            conn.commit()
            conn.close()
            
            config = SQLiteBackupConfig(
                database_path=wal_db_path,
                backup_format="file_copy",
                wal_mode=True
            )
            manager = SQLiteBackupManager(
                config=config,
                backup_directory=temp_backup_dir
            )
            
            # WHEN: Creating backup
            backup_result = await manager.create_full_backup(
                backup_id="sqlite_wal_001",
                created_by="system"
            )
            
            # THEN: WAL backup should succeed
            assert backup_result.success is True
            assert backup_result.wal_handled is True
            
        finally:
            for ext in ['', '-wal', '-shm']:
                file_path = wal_db_path + ext
                if os.path.exists(file_path):
                    os.unlink(file_path)

    async def test_validate_backup_integrity(self, temp_backup_dir, sample_db):
        """Test backup integrity validation."""
        # GIVEN: Backup manager and backup
        config = SQLiteBackupConfig(
            database_path=sample_db,
            verify_integrity=True
        )
        manager = SQLiteBackupManager(
            config=config,
            backup_directory=temp_backup_dir
        )
        
        backup_result = await manager.create_full_backup(
            backup_id="sqlite_integrity_test",
            created_by="system"
        )
        
        # WHEN: Validating backup integrity
        validation_result = await manager.validate_backup_integrity(
            backup_result.backup_file_path
        )
        
        # THEN: Validation should pass
        assert validation_result.is_valid is True
        assert validation_result.check_type == "full_integrity"


@pytest.mark.asyncio
class TestSQLiteRestoreManager:
    """Test SQLite restoration functionality."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def sample_backup(self, temp_backup_dir):
        """Create sample SQLite backup file."""
        backup_path = Path(temp_backup_dir) / "sample_backup.db"
        
        conn = sqlite3.connect(str(backup_path))
        conn.execute('''
            CREATE TABLE restored_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        ''')
        conn.execute("INSERT INTO restored_table (name) VALUES ('restored_data')")
        conn.commit()
        conn.close()
        
        return str(backup_path)

    async def test_create_restore_manager(self, temp_backup_dir):
        """Test creating SQLite restore manager."""
        # GIVEN: Restore manager initialization
        config = SQLiteBackupConfig(
            database_path="/app/data/restored.db",
            backup_format="file_copy"
        )
        manager = SQLiteRestoreManager(
            config=config,
            backup_directory=temp_backup_dir
        )
        
        # THEN: Manager should be initialized
        assert manager.config == config
        assert str(manager.backup_directory) == temp_backup_dir
        assert hasattr(manager, 'restore_from_backup')
        assert hasattr(manager, 'validate_restore')

    async def test_restore_from_backup(self, temp_backup_dir, sample_backup):
        """Test restoring from SQLite backup."""
        # GIVEN: Restore manager
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            restore_path = f.name
        
        try:
            config = SQLiteBackupConfig(
                database_path=restore_path,
                backup_format="file_copy"
            )
            manager = SQLiteRestoreManager(
                config=config,
                backup_directory=temp_backup_dir
            )
            
            # WHEN: Restoring from backup
            restore_result = await manager.restore_from_backup(
                backup_file_path=sample_backup,
                restored_by="admin"
            )
            
            # THEN: Restore should succeed
            assert restore_result.success is True
            assert os.path.exists(restore_path)
            assert os.path.getsize(restore_path) > 0
            
        finally:
            if os.path.exists(restore_path):
                os.unlink(restore_path)

    async def test_validate_restore(self, temp_backup_dir, sample_backup):
        """Test restore validation."""
        # GIVEN: Restored database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            restore_path = f.name
        
        try:
            # Copy backup to restore location
            shutil.copy2(sample_backup, restore_path)
            
            config = SQLiteBackupConfig(
                database_path=restore_path,
                verify_integrity=True
            )
            manager = SQLiteRestoreManager(
                config=config,
                backup_directory=temp_backup_dir
            )
            
            # WHEN: Validating restore
            validation_result = await manager.validate_restore()
            
            # THEN: Validation should pass
            assert validation_result.is_valid is True
            assert validation_result.table_count > 0
            
        finally:
            if os.path.exists(restore_path):
                os.unlink(restore_path)

    async def test_restore_with_verification(self, temp_backup_dir, sample_backup):
        """Test restore with integrity verification."""
        # GIVEN: Restore manager with verification enabled
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            restore_path = f.name
        
        try:
            config = SQLiteBackupConfig(
                database_path=restore_path,
                verify_integrity=True
            )
            manager = SQLiteRestoreManager(
                config=config,
                backup_directory=temp_backup_dir
            )
            
            # WHEN: Restoring with verification
            restore_result = await manager.restore_from_backup(
                backup_file_path=sample_backup,
                restored_by="admin",
                verify_integrity=True
            )
            
            # THEN: Restore should succeed with verification
            assert restore_result.success is True
            assert restore_result.integrity_verified is True
            
        finally:
            if os.path.exists(restore_path):
                os.unlink(restore_path)