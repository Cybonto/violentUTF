"""
Tests for PostgreSQL rollback procedures.
Tests snapshot creation, point-in-time recovery, rollback execution, and validation.
"""

import pytest
import time
from datetime import datetime
from pathlib import Path
from scripts.change_management.rollback.postgresql_rollback import (
    PostgreSQLRollbackManager,
    SnapshotResult,
    RollbackResult,
    ValidationResult,
)


class TestPostgreSQLSnapshot:
    """Test PostgreSQL snapshot creation."""

    def test_create_snapshot_success(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test successful creation of pg_dump snapshot."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)
        change_id = "CR-2025-001"
        database = "keycloak"

        result = manager.create_snapshot(database, change_id)

        assert isinstance(result, SnapshotResult)
        assert result.success is True
        assert result.snapshot_id is not None
        assert result.snapshot_path.exists()
        assert change_id in str(result.snapshot_path)

    def test_snapshot_integrity_verification(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that snapshot integrity is verified after creation."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)
        result = manager.create_snapshot("keycloak", "CR-2025-001")

        assert result.integrity_verified is True
        assert result.size_bytes > 0

    def test_snapshot_metadata_capture(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that snapshot metadata is captured correctly."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)
        result = manager.create_snapshot("keycloak", "CR-2025-002")

        assert result.metadata["database"] == "keycloak"
        assert result.metadata["change_id"] == "CR-2025-002"
        assert "timestamp" in result.metadata
        assert "pg_version" in result.metadata
        assert "size_bytes" in result.metadata

    def test_snapshot_storage_location(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that snapshot is stored in correct location."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)
        result = manager.create_snapshot("keycloak", "CR-2025-003")

        expected_dir = test_backup_location / "postgresql"
        assert result.snapshot_path.parent == expected_dir
        assert result.snapshot_path.suffix == ".sql"


class TestPostgreSQLPITR:
    """Test PostgreSQL point-in-time recovery."""

    def test_pitr_backup_creation(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test creation of PITR backup with WAL archiving."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)
        database = "keycloak"

        result = manager.create_pitr_backup(database)

        assert result.success is True
        assert result.pitr_enabled is True
        assert result.wal_archive_location is not None

    def test_pitr_wal_archiving(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that WAL archiving is properly enabled."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)
        result = manager.create_pitr_backup("keycloak")

        assert result.wal_archiving_enabled is True
        wal_dir = Path(result.wal_archive_location)
        assert wal_dir.exists()

    def test_pitr_restore_to_timestamp(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test restore to specific timestamp using PITR."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)
        target_time = datetime.utcnow()

        result = manager.rollback_to_point_in_time("keycloak", target_time)

        assert isinstance(result, RollbackResult)
        assert result.success is True
        assert result.restore_point == target_time

    def test_pitr_recovery_validation(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that PITR recovery is validated."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)
        target_time = datetime.utcnow()

        result = manager.rollback_to_point_in_time("keycloak", target_time)

        assert result.validation_passed is True
        assert result.validation_details is not None


class TestPostgreSQLRollback:
    """Test PostgreSQL rollback execution."""

    def test_rollback_from_snapshot(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test rollback using snapshot."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        # Create snapshot first
        snapshot = manager.create_snapshot("keycloak", "CR-2025-004")

        # Perform rollback
        result = manager.rollback_to_snapshot(snapshot.snapshot_id)

        assert result.success is True
        assert result.snapshot_id == snapshot.snapshot_id
        assert result.duration_seconds > 0

    def test_rollback_validation(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that database is validated after rollback."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        snapshot = manager.create_snapshot("keycloak", "CR-2025-005")
        rollback_result = manager.rollback_to_snapshot(snapshot.snapshot_id)

        validation = manager.validate_rollback("keycloak")

        assert isinstance(validation, ValidationResult)
        assert validation.valid is True
        assert validation.checks_passed > 0

    def test_rollback_timing_measurement(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that rollback execution time is measured."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        snapshot = manager.create_snapshot("keycloak", "CR-2025-006")

        start_time = time.time()
        result = manager.rollback_to_snapshot(snapshot.snapshot_id)
        end_time = time.time()

        assert result.duration_seconds > 0
        assert result.duration_seconds <= (end_time - start_time) + 1

    def test_rollback_data_integrity(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that data integrity is verified after rollback."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        snapshot = manager.create_snapshot("keycloak", "CR-2025-007")
        rollback_result = manager.rollback_to_snapshot(snapshot.snapshot_id)

        assert rollback_result.integrity_check_passed is True
        assert rollback_result.row_counts_match is True


class TestPostgreSQLNotification:
    """Test rollback notification system."""

    def test_rollback_notification_success(
        self,
        mock_postgresql_connection,
        test_backup_location,
        mock_notification_service,
    ):
        """Test notification on successful rollback."""
        manager = PostgreSQLRollbackManager(
            backup_location=test_backup_location,
            notification_service=mock_notification_service,
        )

        snapshot = manager.create_snapshot("keycloak", "CR-2025-008")
        result = manager.rollback_to_snapshot(snapshot.snapshot_id)

        notifications = mock_notification_service.get_sent_notifications()
        assert len(notifications) > 0

        success_notification = [
            n for n in notifications if "success" in n["subject"].lower()
        ]
        assert len(success_notification) > 0

    def test_rollback_notification_failure(
        self,
        mock_postgresql_connection,
        test_backup_location,
        mock_notification_service,
    ):
        """Test notification on failed rollback."""
        manager = PostgreSQLRollbackManager(
            backup_location=test_backup_location,
            notification_service=mock_notification_service,
        )

        # Try to rollback with invalid snapshot ID
        result = manager.rollback_to_snapshot("INVALID-SNAPSHOT-ID")

        assert result.success is False

        notifications = mock_notification_service.get_sent_notifications()
        failure_notification = [
            n for n in notifications if "failed" in n["subject"].lower()
        ]
        assert len(failure_notification) > 0

    def test_rollback_status_reporting(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test generation of rollback status report."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        snapshot = manager.create_snapshot("keycloak", "CR-2025-009")
        rollback_result = manager.rollback_to_snapshot(snapshot.snapshot_id)

        report = manager.generate_rollback_report(rollback_result)

        assert report is not None
        assert "snapshot_id" in report
        assert "success" in report
        assert "duration_seconds" in report
        assert "validation_results" in report


class TestPostgreSQLRollbackEdgeCases:
    """Test edge cases and error handling."""

    def test_rollback_nonexistent_snapshot(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test rollback with nonexistent snapshot ID."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        result = manager.rollback_to_snapshot("DOES-NOT-EXIST")

        assert result.success is False
        assert "not found" in result.error_message.lower()

    def test_snapshot_insufficient_disk_space(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test snapshot creation with insufficient disk space."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        # Mock insufficient disk space scenario
        manager.min_free_space_gb = 999999

        result = manager.create_snapshot("keycloak", "CR-2025-010")

        assert result.success is False
        assert "disk space" in result.error_message.lower()

    def test_rollback_during_active_connections(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test rollback with active database connections."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        snapshot = manager.create_snapshot("keycloak", "CR-2025-011")

        # Simulate active connections
        manager.force_disconnect = True
        result = manager.rollback_to_snapshot(snapshot.snapshot_id)

        assert result.success is True
        assert result.forced_disconnections is True

    def test_snapshot_corruption_detection(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test detection of corrupted snapshot."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        # Create snapshot and corrupt it
        snapshot = manager.create_snapshot("keycloak", "CR-2025-012")
        snapshot.snapshot_path.write_text("CORRUPTED DATA")

        result = manager.rollback_to_snapshot(snapshot.snapshot_id)

        assert result.success is False
        assert "corrupt" in result.error_message.lower()


class TestPostgreSQLRollbackPerformance:
    """Test rollback performance and timing."""

    def test_rollback_meets_rto_small_database(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test that rollback meets RTO for small database (< 1GB)."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        snapshot = manager.create_snapshot("keycloak", "CR-2025-013")
        result = manager.rollback_to_snapshot(snapshot.snapshot_id)

        # RTO target: 60 seconds for < 1GB database
        assert result.duration_seconds < 60

    def test_snapshot_creation_timing(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test snapshot creation timing."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        start_time = time.time()
        result = manager.create_snapshot("keycloak", "CR-2025-014")
        duration = time.time() - start_time

        assert result.creation_time_seconds > 0
        assert result.creation_time_seconds <= duration + 1

    def test_validation_timing(
        self, mock_postgresql_connection, test_backup_location
    ):
        """Test validation timing after rollback."""
        manager = PostgreSQLRollbackManager(backup_location=test_backup_location)

        validation = manager.validate_rollback("keycloak")

        # Validation should be quick (< 5 seconds)
        assert validation.duration_seconds < 5
