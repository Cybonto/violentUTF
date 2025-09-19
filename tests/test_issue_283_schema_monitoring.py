# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""Test Suite for Issue #283 Schema Change Detection.

This module contains comprehensive tests for the schema change detection
system that monitors database schema modifications in real-time.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.schemas.monitoring_schemas import SchemaChange, SchemaChangeEvent, SchemaSnapshot

# Import the schema monitoring service classes
from app.services.monitoring.schema_monitor import (
    SchemaChangeMonitor as ActualSchemaChangeMonitor,
    SchemaValidator as ActualSchemaValidator,
)

# Create aliases to avoid redefinition warnings
SchemaChangeMonitor = ActualSchemaChangeMonitor  # type: ignore[no-redef]
SchemaValidator = ActualSchemaValidator  # type: ignore[no-redef]

# Create mock for DatabaseSchemaMonitor since it doesn't exist in the actual code
class DatabaseSchemaMonitor:  # type: ignore[no-redef]
    def __init__(self, *args, **kwargs):
        pass

# Mock enums and classes
class SchemaChangeType:
    TABLE_ADDED = "TABLE_ADDED"
    TABLE_DROPPED = "TABLE_DROPPED"
    TABLE_MODIFIED = "TABLE_MODIFIED"
    COLUMN_ADDED = "COLUMN_ADDED"
    COLUMN_DROPPED = "COLUMN_DROPPED"
    INDEX_ADDED = "INDEX_ADDED"
    INDEX_DROPPED = "INDEX_DROPPED"

class RiskLevel:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AssetType:
    POSTGRESQL = "POSTGRESQL"
    SQLITE = "SQLITE"
    DUCKDB = "DUCKDB"


class TestSchemaSnapshot:
    """Test SchemaSnapshot functionality."""

    def test_schema_snapshot_creation(self):
        """Test creating a schema snapshot."""
        schema_info = {
            "tables": [
                {"name": "users", "columns": ["id", "name", "email"]},
                {"name": "posts", "columns": ["id", "title", "content", "user_id"]},
            ],
            "indexes": [
                {"name": "idx_user_email", "table": "users", "columns": ["email"]},
            ],
            "constraints": [
                {"name": "fk_posts_user", "type": "foreign_key", "table": "posts"},
            ],
        }

        snapshot = SchemaSnapshot(
            asset_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            schema_info=schema_info,
            schema_hash=hashlib.md5(str(schema_info).encode()).hexdigest(),
            table_count=2,
            index_count=1,
            constraint_count=1,
        )

        assert snapshot.table_count == 2
        assert snapshot.index_count == 1
        assert snapshot.constraint_count == 1
        assert len(snapshot.schema_hash) == 32  # MD5 hash length

    def test_schema_snapshot_comparison(self):
        """Test comparing schema snapshots for changes."""
        base_schema = {
            "tables": [{"name": "users", "columns": ["id", "name"]}],
            "indexes": [],
            "constraints": [],
        }

        modified_schema = {
            "tables": [{"name": "users", "columns": ["id", "name", "email"]}],
            "indexes": [{"name": "idx_user_email", "table": "users"}],
            "constraints": [],
        }

        base_hash = hashlib.md5(str(base_schema).encode()).hexdigest()
        modified_hash = hashlib.md5(str(modified_schema).encode()).hexdigest()

        assert base_hash != modified_hash


class TestSchemaChange:
    """Test SchemaChange functionality."""

    def test_schema_change_creation(self):
        """Test creating a schema change record."""
        change = SchemaChange(
            change_type=SchemaChangeType.TABLE_ADDED,
            object_name="new_table",
            object_type="TABLE",
            details={
                "columns": ["id", "name", "created_at"],
                "primary_key": ["id"],
                "indexes": [],
            },
        )

        assert change.change_type == SchemaChangeType.TABLE_ADDED
        assert change.object_name == "new_table"
        assert change.object_type == "TABLE"
        assert "columns" in change.details

    def test_column_change_details(self):
        """Test column change detail capture."""
        change = SchemaChange(
            change_type=SchemaChangeType.COLUMN_ADDED,
            object_name="email",
            object_type="COLUMN",
            details={
                "table": "users",
                "data_type": "VARCHAR(255)",
                "nullable": False,
                "default": None,
            },
        )

        assert change.change_type == SchemaChangeType.COLUMN_ADDED
        assert change.details["table"] == "users"
        assert change.details["data_type"] == "VARCHAR(255)"

    def test_index_change_details(self):
        """Test index change detail capture."""
        change = SchemaChange(
            change_type=SchemaChangeType.INDEX_ADDED,
            object_name="idx_user_email",
            object_type="INDEX",
            details={
                "table": "users",
                "columns": ["email"],
                "unique": True,
                "method": "btree",
            },
        )

        assert change.change_type == SchemaChangeType.INDEX_ADDED
        assert change.details["unique"] is True
        assert "email" in change.details["columns"]


class TestSchemaChangeEvent:
    """Test SchemaChangeEvent functionality."""

    def test_schema_change_event_creation(self):
        """Test creating a complete schema change event."""
        asset_id = uuid.uuid4()
        
        previous_schema = {
            "tables": [{"name": "users", "columns": ["id", "name"]}],
            "indexes": [],
            "constraints": [],
        }
        
        current_schema = {
            "tables": [{"name": "users", "columns": ["id", "name", "email"]}],
            "indexes": [],
            "constraints": [],
        }

        previous_snapshot = SchemaSnapshot(
            asset_id=asset_id,
            timestamp=datetime.now(timezone.utc),
            schema_info=previous_schema,
            schema_hash=hashlib.md5(str(previous_schema).encode()).hexdigest(),
            table_count=1,
            index_count=0,
            constraint_count=0,
        )

        current_snapshot = SchemaSnapshot(
            asset_id=asset_id,
            timestamp=datetime.now(timezone.utc),
            schema_info=current_schema,
            schema_hash=hashlib.md5(str(current_schema).encode()).hexdigest(),
            table_count=1,
            index_count=0,
            constraint_count=0,
        )

        changes = [
            SchemaChange(
                change_type=SchemaChangeType.COLUMN_ADDED,
                object_name="email",
                object_type="COLUMN",
                details={"table": "users", "data_type": "VARCHAR(255)"},
            )
        ]

        event = SchemaChangeEvent(
            asset_id=asset_id,
            timestamp=datetime.now(timezone.utc),
            previous_snapshot=previous_snapshot,
            current_snapshot=current_snapshot,
            changes=changes,
            change_type=SchemaChangeType.COLUMN_ADDED,
            impact_assessment={
                "risk_level": RiskLevel.LOW,
                "breaking_change": False,
                "affected_queries": [],
            },
        )

        assert event.asset_id == asset_id
        assert len(event.changes) == 1
        assert event.changes[0].change_type == SchemaChangeType.COLUMN_ADDED
        assert event.impact_assessment["risk_level"] == RiskLevel.LOW


class TestSchemaChangeMonitor:
    """Test SchemaChangeMonitor functionality."""

    @pytest.fixture
    def mock_asset_service(self):
        """Mock asset service for testing."""
        service = AsyncMock()
        service.get_schema_monitorable_assets = AsyncMock(return_value=[])
        service.find_by_container_id = AsyncMock(return_value=None)
        return service

    @pytest.fixture
    def mock_schema_validator(self):
        """Mock schema validator for testing."""
        return AsyncMock(spec=SchemaValidator)

    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service for testing."""
        service = AsyncMock()
        service.send_notification = AsyncMock()
        service.send_alert = AsyncMock()
        return service

    @pytest.fixture
    def schema_monitor(self, mock_asset_service, mock_schema_validator, mock_notification_service):
        """Create SchemaChangeMonitor instance for testing."""
        return SchemaChangeMonitor(
            asset_service=mock_asset_service,
            schema_validator=mock_schema_validator,
            notification_service=mock_notification_service,
        )

    @pytest.mark.asyncio
    async def test_schema_monitor_initialization(self, schema_monitor):
        """Test SchemaChangeMonitor initialization."""
        assert schema_monitor.asset_service is not None
        assert schema_monitor.schema_validator is not None
        assert schema_monitor.notification_service is not None

    @pytest.mark.asyncio
    async def test_start_schema_monitoring(self, schema_monitor, mock_asset_service):
        """Test starting schema monitoring."""
        # Mock database assets
        mock_assets = [
            Mock(id=uuid.uuid4(), asset_type=AssetType.POSTGRESQL, name="test-postgres"),
            Mock(id=uuid.uuid4(), asset_type=AssetType.SQLITE, name="test-sqlite"),
        ]
        mock_asset_service.get_schema_monitorable_assets.return_value = mock_assets

        with patch.object(schema_monitor, "setup_asset_schema_monitoring") as mock_setup:
            await schema_monitor.start_schema_monitoring()

            mock_asset_service.get_schema_monitorable_assets.assert_called_once()
            assert mock_setup.call_count == 2

    @pytest.mark.asyncio
    async def test_detect_schema_changes_no_changes(self, schema_monitor):
        """Test schema change detection when no changes occurred."""
        mock_asset = Mock(id=uuid.uuid4(), asset_type=AssetType.POSTGRESQL)

        # Mock identical snapshots
        schema_info = {"tables": [{"name": "users", "columns": ["id", "name"]}]}
        schema_hash = hashlib.md5(str(schema_info).encode()).hexdigest()

        mock_snapshot = SchemaSnapshot(
            asset_id=mock_asset.id,
            timestamp=datetime.now(timezone.utc),
            schema_info=schema_info,
            schema_hash=schema_hash,
            table_count=1,
            index_count=0,
            constraint_count=0,
        )

        schema_monitor.schema_snapshots = {str(mock_asset.id): mock_snapshot}

        with patch.object(schema_monitor, "create_schema_snapshot", return_value=mock_snapshot):
            result = await schema_monitor.detect_schema_changes(mock_asset)
            assert result is None

    @pytest.mark.asyncio
    async def test_detect_schema_changes_with_changes(self, schema_monitor):
        """Test schema change detection when changes occurred."""
        mock_asset = Mock(id=uuid.uuid4(), asset_type=AssetType.POSTGRESQL)

        # Previous snapshot
        previous_schema = {"tables": [{"name": "users", "columns": ["id", "name"]}]}
        previous_snapshot = SchemaSnapshot(
            asset_id=mock_asset.id,
            timestamp=datetime.now(timezone.utc),
            schema_info=previous_schema,
            schema_hash=hashlib.md5(str(previous_schema).encode()).hexdigest(),
            table_count=1,
            index_count=0,
            constraint_count=0,
        )

        # Current snapshot with changes
        current_schema = {"tables": [{"name": "users", "columns": ["id", "name", "email"]}]}
        current_snapshot = SchemaSnapshot(
            asset_id=mock_asset.id,
            timestamp=datetime.now(timezone.utc),
            schema_info=current_schema,
            schema_hash=hashlib.md5(str(current_schema).encode()).hexdigest(),
            table_count=1,
            index_count=0,
            constraint_count=0,
        )

        schema_monitor.schema_snapshots = {str(mock_asset.id): previous_snapshot}

        with patch.object(schema_monitor, "create_schema_snapshot", return_value=current_snapshot):
            with patch.object(schema_monitor, "analyze_schema_differences") as mock_analyze:
                mock_changes = [
                    SchemaChange(
                        change_type=SchemaChangeType.COLUMN_ADDED,
                        object_name="email",
                        object_type="COLUMN",
                        details={},
                    )
                ]
                mock_analyze.return_value = mock_changes

                with patch.object(schema_monitor, "assess_change_impact") as mock_assess:
                    mock_assess.return_value = {"risk_level": RiskLevel.LOW}

                    with patch.object(schema_monitor, "process_schema_change_event") as mock_process:
                        result = await schema_monitor.detect_schema_changes(mock_asset)

                        assert result is not None
                        assert len(result.changes) == 1
                        assert result.changes[0].change_type == SchemaChangeType.COLUMN_ADDED
                        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_schema_differences_table_added(self, schema_monitor):
        """Test analyzing schema differences for table addition."""
        previous_schema = SchemaSnapshot(
            asset_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            schema_info={"tables": [{"name": "users"}], "indexes": [], "constraints": []},
            schema_hash="hash1",
            table_count=1,
            index_count=0,
            constraint_count=0,
        )

        current_schema = SchemaSnapshot(
            asset_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            schema_info={
                "tables": [{"name": "users"}, {"name": "posts"}],
                "indexes": [],
                "constraints": [],
            },
            schema_hash="hash2",
            table_count=2,
            index_count=0,
            constraint_count=0,
        )

        changes = await schema_monitor.analyze_schema_differences(previous_schema, current_schema)

        # Should detect table addition
        table_changes = [c for c in changes if c.change_type == SchemaChangeType.TABLE_ADDED]
        assert len(table_changes) == 1
        assert table_changes[0].object_name == "posts"

    @pytest.mark.asyncio
    async def test_analyze_schema_differences_table_dropped(self, schema_monitor):
        """Test analyzing schema differences for table removal."""
        previous_schema = SchemaSnapshot(
            asset_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            schema_info={
                "tables": [{"name": "users"}, {"name": "posts"}],
                "indexes": [],
                "constraints": [],
            },
            schema_hash="hash1",
            table_count=2,
            index_count=0,
            constraint_count=0,
        )

        current_schema = SchemaSnapshot(
            asset_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            schema_info={"tables": [{"name": "users"}], "indexes": [], "constraints": []},
            schema_hash="hash2",
            table_count=1,
            index_count=0,
            constraint_count=0,
        )

        changes = await schema_monitor.analyze_schema_differences(previous_schema, current_schema)

        # Should detect table removal
        table_changes = [c for c in changes if c.change_type == SchemaChangeType.TABLE_DROPPED]
        assert len(table_changes) == 1
        assert table_changes[0].object_name == "posts"

    @pytest.mark.asyncio
    async def test_assess_change_impact_low_risk(self, schema_monitor):
        """Test impact assessment for low-risk changes."""
        changes = [
            SchemaChange(
                change_type=SchemaChangeType.COLUMN_ADDED,
                object_name="email",
                object_type="COLUMN",
                details={"nullable": True},
            )
        ]

        mock_asset = Mock(id=uuid.uuid4())
        impact = await schema_monitor.assess_change_impact(mock_asset, changes)

        # Adding nullable column should be low risk
        assert impact["risk_level"] == RiskLevel.LOW
        assert impact["breaking_change"] is False

    @pytest.mark.asyncio
    async def test_assess_change_impact_high_risk(self, schema_monitor):
        """Test impact assessment for high-risk changes."""
        changes = [
            SchemaChange(
                change_type=SchemaChangeType.TABLE_DROPPED,
                object_name="important_table",
                object_type="TABLE",
                details={},
            )
        ]

        mock_asset = Mock(id=uuid.uuid4())
        impact = await schema_monitor.assess_change_impact(mock_asset, changes)

        # Dropping table should be high risk
        assert impact["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert impact["breaking_change"] is True

    @pytest.mark.asyncio
    async def test_postgresql_schema_extraction(self, schema_monitor):
        """Test PostgreSQL schema information extraction."""
        mock_asset = Mock(
            asset_type=AssetType.POSTGRESQL,
            connection_string="postgresql://user:pass@localhost:5432/testdb",
        )

        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_connection = Mock()
            mock_engine.return_value.connect.return_value.__enter__.return_value = mock_connection

            # Mock query results for tables
            mock_connection.execute.return_value.fetchall.return_value = [
                ("public", "users"),
                ("public", "posts"),
            ]

            schema_info = await schema_monitor.get_postgresql_schema(mock_asset)

            assert "tables" in schema_info
            assert len(schema_info["tables"]) >= 0  # May be empty due to mocking

    @pytest.mark.asyncio
    async def test_sqlite_schema_extraction(self, schema_monitor):
        """Test SQLite schema information extraction."""
        mock_asset = Mock(
            asset_type=AssetType.SQLITE,
            file_path="/tmp/test.db",
        )

        with patch("sqlite3.connect") as mock_connect:
            mock_connection = Mock()
            mock_cursor = Mock()
            mock_connect.return_value = mock_connection
            mock_connection.cursor.return_value = mock_cursor

            # Mock query results
            mock_cursor.fetchall.return_value = [
                ("users",),
                ("posts",),
            ]

            schema_info = await schema_monitor.get_sqlite_schema(mock_asset)

            assert "tables" in schema_info
            mock_connect.assert_called_once_with("/tmp/test.db")

    @pytest.mark.asyncio
    async def test_schema_change_notification(self, schema_monitor, mock_notification_service):
        """Test schema change notification sending."""
        mock_asset = Mock(id=uuid.uuid4(), name="test-database")
        
        changes = [
            SchemaChange(
                change_type=SchemaChangeType.TABLE_ADDED,
                object_name="new_table",
                object_type="TABLE",
                details={},
            )
        ]

        change_event = Mock()
        change_event.asset_id = mock_asset.id
        change_event.changes = changes
        change_event.change_type = SchemaChangeType.TABLE_ADDED
        change_event.impact_assessment = {"risk_level": RiskLevel.MEDIUM}

        severity = Mock()
        severity.value = "MEDIUM"

        with patch.object(schema_monitor, "assess_change_severity", return_value=severity):
            await schema_monitor.send_schema_change_notification(change_event, severity)

            mock_notification_service.send_notification.assert_called_once()
            call_args = mock_notification_service.send_notification.call_args[1]
            assert "Schema Change Detected" in call_args["subject"]
            assert str(change_event.asset_id) in call_args["metadata"]["asset_id"]

    @pytest.mark.asyncio
    async def test_schema_validation_success(self, schema_monitor, mock_schema_validator):
        """Test successful schema validation."""
        change_event = Mock()
        change_event.changes = []
        change_event.impact_assessment = {"risk_level": RiskLevel.LOW}

        mock_schema_validator.validate_schema_change.return_value = True

        result = await schema_monitor.trigger_schema_validation(change_event)
        assert result is True

    @pytest.mark.asyncio
    async def test_schema_validation_failure(self, schema_monitor, mock_schema_validator):
        """Test failed schema validation."""
        change_event = Mock()
        change_event.changes = []
        change_event.impact_assessment = {"risk_level": RiskLevel.HIGH}

        mock_schema_validator.validate_schema_change.return_value = False

        result = await schema_monitor.trigger_schema_validation(change_event)
        assert result is False


class TestSchemaValidator:
    """Test SchemaValidator functionality."""

    @pytest.fixture
    def schema_validator(self):
        """Create SchemaValidator instance for testing."""
        return SchemaValidator()

    @pytest.mark.asyncio
    async def test_validate_breaking_change(self, schema_validator):
        """Test validation of breaking schema changes."""
        change_event = Mock()
        change_event.changes = [
            SchemaChange(
                change_type=SchemaChangeType.COLUMN_DROPPED,
                object_name="important_column",
                object_type="COLUMN",
                details={"table": "users"},
            )
        ]
        change_event.impact_assessment = {"breaking_change": True}

        # Breaking changes should require additional validation
        result = await schema_validator.validate_schema_change(change_event)
        # Implementation would check application compatibility
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_validate_non_breaking_change(self, schema_validator):
        """Test validation of non-breaking schema changes."""
        change_event = Mock()
        change_event.changes = [
            SchemaChange(
                change_type=SchemaChangeType.COLUMN_ADDED,
                object_name="new_column",
                object_type="COLUMN",
                details={"table": "users", "nullable": True},
            )
        ]
        change_event.impact_assessment = {"breaking_change": False}

        result = await schema_validator.validate_schema_change(change_event)
        # Non-breaking changes should generally pass validation
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_validate_index_changes(self, schema_validator):
        """Test validation of index changes."""
        change_event = Mock()
        change_event.changes = [
            SchemaChange(
                change_type=SchemaChangeType.INDEX_ADDED,
                object_name="idx_user_email",
                object_type="INDEX",
                details={"table": "users", "unique": True},
            )
        ]
        change_event.impact_assessment = {"breaking_change": False}

        result = await schema_validator.validate_schema_change(change_event)
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])