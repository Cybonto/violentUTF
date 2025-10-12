# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for PostgreSQL Backup functionality - Issue #267."""

import pytest
import tempfile
import os
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

# These imports will fail initially (RED phase of TDD)
from scripts.backup_management.postgresql_backup import (
    PostgreSQLBackupManager,
    PostgreSQLBackupConfig,
    PostgreSQLRestoreManager,
    PgDumpExecutor,
    PostgreSQLConnectionManager,
    BackupExecutionResult,
    ConnectionTestResult,
)
from scripts.backup_management.backup_system import (
    BackupTier,
    BackupMetadata,
    BackupArchive,
)


class TestPostgreSQLBackupConfig:
    """Test PostgreSQL backup configuration."""

    def test_create_postgresql_config(self):
        """Test creating PostgreSQL backup configuration."""
        # GIVEN: PostgreSQL configuration parameters
        config = PostgreSQLBackupConfig(
            host="postgres",
            port=5432,
            database="keycloak",
            username="keycloak",
            password="secure_password",
            backup_format="custom",
            compression_level=6,
            parallel_jobs=2
        )

        # THEN: Configuration should be created correctly
        assert config.host == "postgres"
        assert config.port == 5432
        assert config.database == "keycloak"
        assert config.username == "keycloak"
        assert config.password == "secure_password"
        assert config.backup_format == "custom"
        assert config.compression_level == 6
        assert config.parallel_jobs == 2

    def test_postgresql_config_validation(self):
        """Test PostgreSQL configuration validation."""
        # GIVEN: Valid configuration
        valid_config = PostgreSQLBackupConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password="test_pass"
        )

        # THEN: Valid configuration should validate
        assert valid_config.is_valid()
        assert len(valid_config.validation_errors) == 0

    def test_postgresql_config_validation_errors(self):
        """Test PostgreSQL configuration validation with errors."""
        # GIVEN: Invalid configuration
        invalid_config = PostgreSQLBackupConfig(
            host="",  # Empty host
            port=0,   # Invalid port
            database="",  # Empty database
            username="",  # Empty username
            password=""   # Empty password
        )

        # THEN: Invalid configuration should not validate
        assert not invalid_config.is_valid()
        assert len(invalid_config.validation_errors) > 0

    def test_postgresql_config_connection_string(self):
        """Test PostgreSQL connection string generation."""
        # GIVEN: Configuration
        config = PostgreSQLBackupConfig(
            host="postgres",
            port=5432,
            database="keycloak",
            username="keycloak",
            password="secret"
        )

        # WHEN: Generating connection string
        conn_str = config.get_connection_string()

        # THEN: Connection string should be formatted correctly
        expected = "postgresql://keycloak:secret@postgres:5432/keycloak"
        assert conn_str == expected

    def test_postgresql_config_from_env(self):
        """Test creating configuration from environment variables."""
        # GIVEN: Environment variables
        env_vars = {
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "keycloak",
            "POSTGRES_USER": "keycloak",
            "POSTGRES_PASSWORD": "env_password"
        }

        with patch.dict(os.environ, env_vars):
            # WHEN: Creating config from environment
            config = PostgreSQLBackupConfig.from_environment()

            # THEN: Configuration should match environment
            assert config.host == "postgres"
            assert config.port == 5432
            assert config.database == "keycloak"
            assert config.username == "keycloak"
            assert config.password == "env_password"


class TestPgDumpExecutor:
    """Test pg_dump command execution and management."""

    def test_create_pgdump_executor(self):
        """Test creating pg_dump executor."""
        # GIVEN: Executor initialization
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password"
        )
        executor = PgDumpExecutor(config)

        # THEN: Executor should be initialized
        assert executor.config == config
        assert hasattr(executor, 'execute_backup')
        assert hasattr(executor, 'build_pgdump_command')

    def test_build_pgdump_command_custom_format(self):
        """Test building pg_dump command for custom format."""
        # GIVEN: Configuration with custom format
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password",
            backup_format="custom", compression_level=6
        )
        executor = PgDumpExecutor(config)

        # WHEN: Building command
        output_file = "/backups/keycloak_backup.custom"
        command = executor.build_pgdump_command(output_file)

        # THEN: Command should be formatted correctly
        expected_parts = [
            "pg_dump",
            "-h", "postgres",
            "-p", "5432",
            "-U", "keycloak",
            "-d", "keycloak",
            "-f", output_file,
            "-F", "c",  # custom format
            "-Z", "6",  # compression level
            "--verbose"
        ]

        assert all(part in command for part in expected_parts)

    def test_build_pgdump_command_plain_format(self):
        """Test building pg_dump command for plain SQL format."""
        # GIVEN: Configuration with plain format
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password",
            backup_format="plain"
        )
        executor = PgDumpExecutor(config)

        # WHEN: Building command
        output_file = "/backups/keycloak_backup.sql"
        command = executor.build_pgdump_command(output_file)

        # THEN: Command should include plain format options
        assert "-F p" in " ".join(command) or "-Fp" in " ".join(command)

    def test_build_pgdump_command_with_parallel(self):
        """Test building pg_dump command with parallel jobs."""
        # GIVEN: Configuration with parallel jobs
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password",
            parallel_jobs=4
        )
        executor = PgDumpExecutor(config)

        # WHEN: Building command for directory format (required for parallel)
        output_dir = "/backups/keycloak_parallel"
        command = executor.build_pgdump_command(output_dir, use_parallel=True)

        # THEN: Command should include parallel options
        assert "-F d" in " ".join(command) or "-Fd" in " ".join(command)  # Directory format
        assert "-j 4" in " ".join(command) or "-j4" in " ".join(command)  # Parallel jobs

    @pytest.mark.asyncio
    async def test_execute_backup_success(self):
        """Test successful pg_dump execution."""
        # GIVEN: Executor with mocked subprocess
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password"
        )
        executor = PgDumpExecutor(config)

        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Backup completed", b"")

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            # WHEN: Executing backup
            result = await executor.execute_backup("/backups/test.backup")

            # THEN: Backup should succeed
            assert result.success is True
            assert result.output_file == "/backups/test.backup"
            assert result.error_message is None

    @pytest.mark.asyncio
    async def test_execute_backup_failure(self):
        """Test failed pg_dump execution."""
        # GIVEN: Executor with mocked failed subprocess
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password"
        )
        executor = PgDumpExecutor(config)

        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b"", b"Connection failed")

        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            # WHEN: Executing backup
            result = await executor.execute_backup("/backups/test.backup")

            # THEN: Backup should fail
            assert result.success is False
            assert "Connection failed" in result.error_message

    def test_build_environment_variables(self):
        """Test building environment variables for pg_dump."""
        # GIVEN: Executor
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="secret_password"
        )
        executor = PgDumpExecutor(config)

        # WHEN: Building environment
        env_vars = executor.build_environment()

        # THEN: Environment should include password
        assert env_vars["PGPASSWORD"] == "secret_password"
        assert "PGPASSWORD" in env_vars


@pytest.mark.asyncio
class TestPostgreSQLConnectionManager:
    """Test PostgreSQL connection management."""

    async def test_create_connection_manager(self):
        """Test creating connection manager."""
        # GIVEN: Connection manager initialization
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password"
        )
        manager = PostgreSQLConnectionManager(config)

        # THEN: Manager should be initialized
        assert manager.config == config
        assert hasattr(manager, 'test_connection')
        assert hasattr(manager, 'get_database_info')

    async def test_test_connection_success(self):
        """Test successful database connection test."""
        # GIVEN: Connection manager with mocked successful connection
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password"
        )
        manager = PostgreSQLConnectionManager(config)

        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn
            mock_conn.fetchval.return_value = 1

            # WHEN: Testing connection
            result = await manager.test_connection()

            # THEN: Connection test should succeed
            assert result.success is True
            assert result.error_message is None

    async def test_test_connection_failure(self):
        """Test failed database connection test."""
        # GIVEN: Connection manager with mocked failed connection
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password"
        )
        manager = PostgreSQLConnectionManager(config)

        with patch('asyncpg.connect', side_effect=Exception("Connection refused")):
            # WHEN: Testing connection
            result = await manager.test_connection()

            # THEN: Connection test should fail
            assert result.success is False
            assert "Connection refused" in result.error_message

    async def test_get_database_info(self):
        """Test getting database information."""
        # GIVEN: Connection manager with mocked database queries
        config = PostgreSQLBackupConfig(
            host="postgres", port=5432, database="keycloak",
            username="keycloak", password="password"
        )
        manager = PostgreSQLConnectionManager(config)

        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value.__aenter__.return_value = mock_conn

            # Mock database info queries
            mock_conn.fetchval.side_effect = [
                "15.4",  # PostgreSQL version
                1024000,  # Database size
                25       # Table count
            ]

            # WHEN: Getting database info
            info = await manager.get_database_info()

            # THEN: Database info should be collected
            assert info["postgresql_version"] == "15.4"
            assert info["database_size_bytes"] == 1024000
            assert info["table_count"] == 25


@pytest.mark.asyncio
class TestPostgreSQLBackupManager:
    """Test comprehensive PostgreSQL backup management."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def sample_config(self):
        """Create sample PostgreSQL configuration."""
        return PostgreSQLBackupConfig(
            host="postgres",
            port=5432,
            database="keycloak",
            username="keycloak",
            password="password"
        )

    async def test_create_postgresql_backup_manager(self, temp_backup_dir, sample_config):
        """Test creating PostgreSQL backup manager."""
        # GIVEN: Backup manager initialization
        manager = PostgreSQLBackupManager(
            config=sample_config,
            backup_directory=temp_backup_dir
        )

        # THEN: Manager should be initialized
        assert manager.config == sample_config
        assert str(manager.backup_directory) == temp_backup_dir
        assert manager.pg_dump_executor is not None
        assert manager.connection_manager is not None

    async def test_create_full_backup(self, temp_backup_dir, sample_config):
        """Test creating full PostgreSQL backup."""
        # GIVEN: Backup manager
        manager = PostgreSQLBackupManager(
            config=sample_config,
            backup_directory=temp_backup_dir
        )

        # Mock successful pg_dump execution
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output_file = f"{temp_backup_dir}/keycloak_full_backup.custom"
        mock_result.backup_size_bytes = 1024000

        with patch.object(manager.pg_dump_executor, 'execute_backup', return_value=mock_result):
            # WHEN: Creating full backup
            backup_result = await manager.create_full_backup(
                backup_id="postgresql_full_001",
                created_by="automated_system"
            )

            # THEN: Backup should be created successfully
            assert backup_result.success is True
            assert backup_result.backup_metadata.backup_type == "full"
            assert backup_result.backup_metadata.backup_tier == BackupTier.TIER_1_CRITICAL
            assert backup_result.backup_metadata.database_type == "postgresql"

    async def test_create_incremental_backup(self, temp_backup_dir, sample_config):
        """Test creating incremental PostgreSQL backup."""
        # GIVEN: Backup manager with previous full backup
        manager = PostgreSQLBackupManager(
            config=sample_config,
            backup_directory=temp_backup_dir
        )

        # Mock successful pg_dump execution for incremental backup
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output_file = f"{temp_backup_dir}/keycloak_incremental_backup.custom"
        mock_result.backup_size_bytes = 256000

        with patch.object(manager.pg_dump_executor, 'execute_backup', return_value=mock_result):
            with patch.object(manager, '_get_last_backup_lsn', return_value="ABC123"):
                # WHEN: Creating incremental backup
                backup_result = await manager.create_incremental_backup(
                    backup_id="postgresql_incremental_001",
                    base_backup_id="postgresql_full_001",
                    created_by="automated_system"
                )

                # THEN: Incremental backup should be created
                assert backup_result.success is True
                assert backup_result.backup_metadata.backup_type == "incremental"
                assert backup_result.backup_metadata.parent_backup_id == "postgresql_full_001"

    async def test_validate_backup_integrity(self, temp_backup_dir, sample_config):
        """Test backup integrity validation."""
        # GIVEN: Backup manager and backup file
        manager = PostgreSQLBackupManager(
            config=sample_config,
            backup_directory=temp_backup_dir
        )

        # Create mock backup file
        backup_file = Path(temp_backup_dir) / "test_backup.custom"
        backup_file.write_bytes(b"Mock PostgreSQL backup data")

        # WHEN: Validating backup integrity
        validation_result = await manager.validate_backup_integrity(str(backup_file))

        # THEN: Validation should complete
        assert validation_result is not None
        assert hasattr(validation_result, 'is_valid')

    async def test_estimate_backup_size(self, sample_config):
        """Test backup size estimation."""
        # GIVEN: Backup manager with mocked database info
        manager = PostgreSQLBackupManager(
            config=sample_config,
            backup_directory="/tmp"
        )

        with patch.object(manager.connection_manager, 'get_database_info') as mock_info:
            mock_info.return_value = {
                "database_size_bytes": 2048000,
                "table_count": 30
            }

            # WHEN: Estimating backup size
            estimated_size = await manager.estimate_backup_size("full")

            # THEN: Size should be estimated
            assert estimated_size > 0
            assert isinstance(estimated_size, int)

    async def test_backup_with_retention_policy(self, temp_backup_dir, sample_config):
        """Test backup creation with retention policy enforcement."""
        # GIVEN: Backup manager with retention policy
        manager = PostgreSQLBackupManager(
            config=sample_config,
            backup_directory=temp_backup_dir,
            max_backups=3
        )

        # Create multiple backups to test retention
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.backup_size_bytes = 1024000

        with patch.object(manager.pg_dump_executor, 'execute_backup', return_value=mock_result):
            backup_ids = []
            for i in range(5):  # Create more backups than retention limit
                mock_result.output_file = f"{temp_backup_dir}/backup_{i}.custom"
                result = await manager.create_full_backup(
                    backup_id=f"backup_{i}",
                    created_by="test"
                )
                if result.success:
                    backup_ids.append(result.backup_metadata.backup_id)

            # WHEN: Checking retained backups
            retained_backups = await manager.list_backups()

            # THEN: Should enforce retention policy
            assert len(retained_backups) <= 3


@pytest.mark.asyncio
class TestPostgreSQLRestoreManager:
    """Test PostgreSQL restoration functionality."""

    @pytest.fixture
    def temp_backup_dir(self):
        """Create temporary backup directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def sample_config(self):
        """Create sample PostgreSQL configuration."""
        return PostgreSQLBackupConfig(
            host="postgres",
            port=5432,
            database="keycloak",
            username="keycloak",
            password="password"
        )

    async def test_create_restore_manager(self, temp_backup_dir, sample_config):
        """Test creating PostgreSQL restore manager."""
        # GIVEN: Restore manager initialization
        manager = PostgreSQLRestoreManager(
            config=sample_config,
            backup_directory=temp_backup_dir
        )

        # THEN: Manager should be initialized
        assert manager.config == sample_config
        assert str(manager.backup_directory) == temp_backup_dir
        assert hasattr(manager, 'restore_from_backup')
        assert hasattr(manager, 'validate_restore')

    async def test_restore_from_full_backup(self, temp_backup_dir, sample_config):
        """Test restoring from full backup."""
        # GIVEN: Restore manager and backup file
        manager = PostgreSQLRestoreManager(
            config=sample_config,
            backup_directory=temp_backup_dir
        )

        # Create mock backup file
        backup_file = Path(temp_backup_dir) / "keycloak_backup.custom"
        backup_file.write_bytes(b"Mock backup data")

        # Mock successful pg_restore execution
        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (b"Restore completed", b"")
            mock_exec.return_value = mock_process

            # WHEN: Restoring from backup
            restore_result = await manager.restore_from_backup(
                backup_file_path=str(backup_file),
                target_database="keycloak_restored",
                restored_by="admin"
            )

            # THEN: Restore should succeed
            assert restore_result.success is True
            assert restore_result.target_database == "keycloak_restored"

    async def test_validate_restore(self, temp_backup_dir, sample_config):
        """Test restore validation."""
        # GIVEN: Restore manager
        manager = PostgreSQLRestoreManager(
            config=sample_config,
            backup_directory=temp_backup_dir
        )

        # Mock connection and validation queries
        with patch.object(manager.connection_manager, 'test_connection') as mock_conn:
            mock_conn.return_value.success = True

            with patch.object(manager.connection_manager, 'get_database_info') as mock_info:
                mock_info.return_value = {
                    "table_count": 25,
                    "database_size_bytes": 1024000
                }

                # WHEN: Validating restore
                validation_result = await manager.validate_restore("restored_db")

                # THEN: Validation should complete
                assert validation_result is not None
                assert hasattr(validation_result, 'is_valid')

    async def test_point_in_time_recovery(self, temp_backup_dir, sample_config):
        """Test point-in-time recovery functionality."""
        # GIVEN: Restore manager with WAL archives
        manager = PostgreSQLRestoreManager(
            config=sample_config,
            backup_directory=temp_backup_dir,
            wal_archive_directory=f"{temp_backup_dir}/wal_archives"
        )

        # Create mock WAL archive directory
        wal_dir = Path(temp_backup_dir) / "wal_archives"
        wal_dir.mkdir()

        # Mock base backup and WAL files
        base_backup = Path(temp_backup_dir) / "base_backup.tar"
        base_backup.write_bytes(b"Base backup data")

        # WHEN: Performing point-in-time recovery
        target_time = datetime.now() - timedelta(hours=1)

        with patch('asyncio.create_subprocess_exec') as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_exec.return_value = mock_process

            recovery_result = await manager.point_in_time_recovery(
                base_backup_path=str(base_backup),
                target_time=target_time,
                recovery_database="keycloak_pitr",
                restored_by="admin"
            )

            # THEN: Recovery should complete
            assert recovery_result is not None
            assert hasattr(recovery_result, 'success')
