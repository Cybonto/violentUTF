# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Schema Change Detection and Monitoring for Issue #283.

This module implements comprehensive schema change detection that monitors
database schema modifications in real-time and assesses their impact.
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, text

from app.models.asset_inventory import AssetType
from app.models.monitoring import AlertSeverity, RiskLevel, SchemaChangeType
from app.schemas.monitoring_schemas import SchemaChange, SchemaChangeEvent, SchemaSnapshot
from app.services.asset_management.asset_service import AssetService
from app.services.monitoring.notifications import NotificationService

logger = logging.getLogger(__name__)


class SchemaInfo:
    """Container for database schema information."""

    def __init__(self, tables: List[Dict], indexes: List[Dict], constraints: List[Dict]) -> None:
        """Initialize schema information.

        Args:
            tables: List of table definitions
            indexes: List of index definitions
            constraints: List of constraint definitions
        """
        self.tables = tables
        self.indexes = indexes
        self.constraints = constraints


class SchemaChangeMonitor:
    """Service for monitoring database schema changes.

    This service monitors database schemas and detects changes in real-time,
    providing impact assessment and validation capabilities.
    """

    def __init__(
        self,
        asset_service: AssetService,
        schema_validator: "SchemaValidator",
        notification_service: NotificationService,
    ) -> None:
        """Initialize the schema change monitor.

        Args:
            asset_service: Service for asset management operations
            schema_validator: Service for schema validation
            notification_service: Service for sending notifications
        """
        self.asset_service = asset_service
        self.schema_validator = schema_validator
        self.notification_service = notification_service
        self.schema_snapshots: Dict[str, SchemaSnapshot] = {}
        self.monitoring_connections: Dict[str, Any] = {}

    async def start_schema_monitoring(self) -> None:
        """Start schema monitoring for all database assets."""
        logger.info("Starting schema change monitoring")

        # Get all database assets that support schema monitoring
        database_assets = await self.asset_service.get_schema_monitorable_assets()

        for asset in database_assets:
            try:
                await self.setup_asset_schema_monitoring(asset)
            except Exception as e:
                logger.error("Error setting up schema monitoring for %s: %s", asset.name, e)

    async def setup_asset_schema_monitoring(self, asset: Any) -> None:  # noqa: ANN401
        """Set up schema monitoring for specific database asset.

        Args:
            asset: Database asset to monitor
        """
        logger.info("Setting up schema monitoring for %s", asset.name)

        if asset.asset_type == AssetType.POSTGRESQL:
            await self.setup_postgresql_monitoring(asset)
        elif asset.asset_type == AssetType.SQLITE:
            await self.setup_sqlite_monitoring(asset)
        elif asset.asset_type == AssetType.DUCKDB:
            await self.setup_duckdb_monitoring(asset)

        # Create initial schema snapshot
        await self.create_schema_snapshot(asset)

    async def setup_postgresql_monitoring(self, asset: Any) -> None:  # noqa: ANN401
        """Set up PostgreSQL schema change monitoring.

        Args:
            asset: PostgreSQL asset to monitor
        """
        try:
            # Create monitoring connection
            engine = create_engine(asset.connection_string)

            # Install event trigger for schema changes (if permissions allow)
            await self.install_postgres_event_trigger(engine, str(asset.id))

            # Start periodic schema checking
            await self.schedule_periodic_schema_check(asset, interval_minutes=15)

            self.monitoring_connections[str(asset.id)] = engine

        except Exception as e:
            logger.warning("Could not setup PostgreSQL monitoring for %s: %s", asset.name, e)
            # Fallback to periodic checking only
            await self.schedule_periodic_schema_check(asset, interval_minutes=30)

    async def install_postgres_event_trigger(self, engine: Any, asset_id: str) -> None:  # noqa: ANN401
        """Install PostgreSQL event trigger for schema changes.

        Args:
            engine: SQLAlchemy engine
            asset_id: Asset ID for trigger naming
        """
        trigger_function = f"""
        CREATE OR REPLACE FUNCTION notify_schema_change_{asset_id.replace('-', '_')}()
        RETURNS event_trigger AS $$
        BEGIN
            -- Send notification about schema change
            PERFORM pg_notify(
                'schema_change_{asset_id}',
                json_build_object(
                    'event', TG_EVENT,
                    'tag', TG_TAG,
                    'object_type', TG_OBJECT_TYPE,
                    'timestamp', NOW()
                )::text
            );
        END;
        $$ LANGUAGE plpgsql;
        """

        event_trigger = f"""
        DROP EVENT TRIGGER IF EXISTS schema_change_trigger_{asset_id.replace('-', '_')};
        CREATE EVENT TRIGGER schema_change_trigger_{asset_id.replace('-', '_')}
        ON ddl_command_end
        EXECUTE FUNCTION notify_schema_change_{asset_id.replace('-', '_')}();
        """

        try:
            with engine.connect() as conn:
                conn.execute(text(trigger_function))
                conn.execute(text(event_trigger))
                conn.commit()

                # Listen for notifications
                await self.start_postgres_notification_listener(engine, asset_id)

        except Exception as e:
            logger.warning("Could not install PostgreSQL event trigger: %s", e)
            # This is expected if user doesn't have superuser privileges

    async def start_postgres_notification_listener(self, engine: Any, asset_id: str) -> None:  # noqa: ANN401
        """Start PostgreSQL notification listener.

        Args:
            engine: SQLAlchemy engine
            asset_id: Asset ID for notifications
        """
        # This would start a background task to listen for PostgreSQL notifications
        # For now, just log that it would be started
        logger.info("Starting PostgreSQL notification listener for asset %s", asset_id)

    async def setup_sqlite_monitoring(self, asset: Any) -> None:  # noqa: ANN401
        """Set up SQLite schema change monitoring.

        Args:
            asset: SQLite asset to monitor
        """
        # SQLite monitoring through file system watching
        if asset.file_path:
            await self.setup_file_system_monitoring(asset.file_path, str(asset.id))

        # Periodic schema checking
        await self.schedule_periodic_schema_check(asset, interval_minutes=10)

    async def setup_duckdb_monitoring(self, asset: Any) -> None:  # noqa: ANN401
        """Set up DuckDB schema change monitoring.

        Args:
            asset: DuckDB asset to monitor
        """
        # Similar to SQLite, DuckDB uses file-based monitoring
        if asset.file_path:
            await self.setup_file_system_monitoring(asset.file_path, str(asset.id))

        # Periodic schema checking
        await self.schedule_periodic_schema_check(asset, interval_minutes=10)

    async def setup_file_system_monitoring(self, file_path: str, asset_id: str) -> None:
        """Set up file system monitoring for database files.

        Args:
            file_path: Path to database file
            asset_id: Asset ID for monitoring
        """
        # This would integrate with the file system monitor
        logger.info("Setting up file system monitoring for %s", file_path)

    async def schedule_periodic_schema_check(self, asset: Any, interval_minutes: int = 15) -> None:  # noqa: ANN401
        """Schedule periodic schema checking.

        Args:
            asset: Asset to check
            interval_minutes: Check interval in minutes
        """
        # This would schedule periodic schema checks
        logger.info("Scheduling periodic schema check for %s every %s minutes", asset.name, interval_minutes)

        # Start background task for periodic checking
        asyncio.create_task(self.periodic_schema_check_task(asset, interval_minutes))

    async def periodic_schema_check_task(self, asset: Any, interval_minutes: int) -> None:  # noqa: ANN401
        """Background task for periodic schema checking.

        Args:
            asset: Asset to check
            interval_minutes: Check interval in minutes
        """
        while True:
            try:
                await asyncio.sleep(interval_minutes * 60)  # Convert to seconds
                await self.detect_schema_changes(asset)
            except Exception as e:
                logger.error("Error in periodic schema check for %s: %s", asset.name, e)

    async def create_schema_snapshot(self, asset: Any) -> SchemaSnapshot:  # noqa: ANN401
        """Create current schema snapshot for comparison.

        Args:
            asset: Database asset

        Returns:
            SchemaSnapshot with current schema state
        """
        if asset.asset_type == AssetType.POSTGRESQL:
            schema_info = await self.get_postgresql_schema(asset)
        elif asset.asset_type == AssetType.SQLITE:
            schema_info = await self.get_sqlite_schema(asset)
        elif asset.asset_type == AssetType.DUCKDB:
            schema_info = await self.get_duckdb_schema(asset)
        else:
            schema_info = SchemaInfo(tables=[], indexes=[], constraints=[])

        # Create schema hash for quick comparison
        schema_hash = self.calculate_schema_hash(schema_info)

        snapshot = SchemaSnapshot(
            asset_id=asset.id,
            timestamp=datetime.now(timezone.utc),
            schema_info={
                "tables": schema_info.tables,
                "indexes": schema_info.indexes,
                "constraints": schema_info.constraints,
            },
            schema_hash=schema_hash,
            table_count=len(schema_info.tables),
            index_count=len(schema_info.indexes),
            constraint_count=len(schema_info.constraints),
        )

        self.schema_snapshots[str(asset.id)] = snapshot
        return snapshot

    def calculate_schema_hash(self, schema_info: SchemaInfo) -> str:
        """Calculate hash of schema information for comparison.

        Args:
            schema_info: Schema information object

        Returns:
            MD5 hash of schema structure
        """
        schema_dict = {
            "tables": schema_info.tables,
            "indexes": schema_info.indexes,
            "constraints": schema_info.constraints,
        }
        schema_str = json.dumps(schema_dict, sort_keys=True)
        return hashlib.md5(schema_str.encode(), usedforsecurity=False).hexdigest()

    async def detect_schema_changes(self, asset: Any) -> Optional[SchemaChangeEvent]:  # noqa: ANN401
        """Detect schema changes by comparing current schema with snapshot.

        Args:
            asset: Database asset to check

        Returns:
            SchemaChangeEvent if changes detected, None otherwise
        """
        current_snapshot = await self.create_schema_snapshot(asset)
        previous_snapshot = self.schema_snapshots.get(str(asset.id))

        if not previous_snapshot:
            # First time monitoring - no changes to detect
            logger.info("First schema snapshot created for %s", asset.name)
            return None

        # Quick hash comparison
        if current_snapshot.schema_hash == previous_snapshot.schema_hash:
            # No changes detected
            return None

        logger.info("Schema changes detected for %s", asset.name)

        # Detailed change analysis
        changes = await self.analyze_schema_differences(previous_snapshot, current_snapshot)

        if changes:
            change_event = SchemaChangeEvent(
                asset_id=asset.id,
                timestamp=datetime.now(timezone.utc),
                previous_snapshot=previous_snapshot,
                current_snapshot=current_snapshot,
                changes=changes,
                change_type=self.classify_change_type(changes),
                impact_assessment=await self.assess_change_impact(asset, changes),
            )

            # Update snapshot cache
            self.schema_snapshots[str(asset.id)] = current_snapshot

            # Process the change event
            await self.process_schema_change_event(change_event)

            return change_event

        return None

    async def analyze_schema_differences(self, previous: SchemaSnapshot, current: SchemaSnapshot) -> List[SchemaChange]:
        """Analyze detailed differences between schema snapshots.

        Args:
            previous: Previous schema snapshot
            current: Current schema snapshot

        Returns:
            List of detected schema changes
        """
        changes = []

        # Table changes
        prev_tables = {t["name"]: t for t in previous.schema_info["tables"]}
        curr_tables = {t["name"]: t for t in current.schema_info["tables"]}

        # New tables
        for table_name in curr_tables.keys() - prev_tables.keys():
            changes.append(
                SchemaChange(
                    change_type=SchemaChangeType.TABLE_ADDED,
                    object_name=table_name,
                    object_type="TABLE",
                    details={"table_info": curr_tables[table_name]},
                )
            )

        # Dropped tables
        for table_name in prev_tables.keys() - curr_tables.keys():
            changes.append(
                SchemaChange(
                    change_type=SchemaChangeType.TABLE_DROPPED,
                    object_name=table_name,
                    object_type="TABLE",
                    details={"table_info": prev_tables[table_name]},
                )
            )

        # Modified tables
        for table_name in prev_tables.keys() & curr_tables.keys():
            table_changes = await self.compare_tables(prev_tables[table_name], curr_tables[table_name])
            changes.extend(table_changes)

        # Index changes
        prev_indexes = {i["name"]: i for i in previous.schema_info["indexes"]}
        curr_indexes = {i["name"]: i for i in current.schema_info["indexes"]}

        # New indexes
        for index_name in curr_indexes.keys() - prev_indexes.keys():
            changes.append(
                SchemaChange(
                    change_type=SchemaChangeType.INDEX_ADDED,
                    object_name=index_name,
                    object_type="INDEX",
                    details={"index_info": curr_indexes[index_name]},
                )
            )

        # Dropped indexes
        for index_name in prev_indexes.keys() - curr_indexes.keys():
            changes.append(
                SchemaChange(
                    change_type=SchemaChangeType.INDEX_DROPPED,
                    object_name=index_name,
                    object_type="INDEX",
                    details={"index_info": prev_indexes[index_name]},
                )
            )

        return changes

    async def compare_tables(self, prev_table: Dict, curr_table: Dict) -> List[SchemaChange]:
        """Compare two table definitions for changes.

        Args:
            prev_table: Previous table definition
            curr_table: Current table definition

        Returns:
            List of changes detected in the table
        """
        changes = []
        table_name = prev_table["name"]

        # Compare columns if available
        if "columns" in prev_table and "columns" in curr_table:
            prev_columns = set(prev_table["columns"])
            curr_columns = set(curr_table["columns"])

            # New columns
            for column in curr_columns - prev_columns:
                changes.append(
                    SchemaChange(
                        change_type=SchemaChangeType.COLUMN_ADDED,
                        object_name=column,
                        object_type="COLUMN",
                        details={"table": table_name},
                    )
                )

            # Dropped columns
            for column in prev_columns - curr_columns:
                changes.append(
                    SchemaChange(
                        change_type=SchemaChangeType.COLUMN_DROPPED,
                        object_name=column,
                        object_type="COLUMN",
                        details={"table": table_name},
                    )
                )

        return changes

    def classify_change_type(self, changes: List[SchemaChange]) -> SchemaChangeType:
        """Classify the primary type of schema change.

        Args:
            changes: List of schema changes

        Returns:
            Primary change type
        """
        if not changes:
            return SchemaChangeType.TABLE_MODIFIED

        # Prioritize by severity
        change_types = [change.change_type for change in changes]

        if SchemaChangeType.TABLE_DROPPED in change_types:
            return SchemaChangeType.TABLE_DROPPED
        elif SchemaChangeType.COLUMN_DROPPED in change_types:
            return SchemaChangeType.COLUMN_DROPPED
        elif SchemaChangeType.TABLE_ADDED in change_types:
            return SchemaChangeType.TABLE_ADDED
        elif SchemaChangeType.COLUMN_ADDED in change_types:
            return SchemaChangeType.COLUMN_ADDED
        else:
            return changes[0].change_type

    async def assess_change_impact(self, asset: Any, changes: List[SchemaChange]) -> Dict[str, Any]:  # noqa: ANN401
        """Assess the impact of schema changes.

        Args:
            asset: Database asset
            changes: List of schema changes

        Returns:
            Impact assessment dictionary
        """
        risk_level = RiskLevel.LOW
        breaking_change = False
        affected_queries = []

        for change in changes:
            # Assess individual change impact
            if change.change_type in [SchemaChangeType.TABLE_DROPPED, SchemaChangeType.COLUMN_DROPPED]:
                risk_level = RiskLevel.HIGH
                breaking_change = True
            elif change.change_type in [SchemaChangeType.INDEX_DROPPED]:
                risk_level = max(risk_level, RiskLevel.MEDIUM)
            elif change.change_type in [SchemaChangeType.TABLE_ADDED, SchemaChangeType.COLUMN_ADDED]:
                risk_level = max(risk_level, RiskLevel.LOW)

        return {
            "risk_level": risk_level,
            "breaking_change": breaking_change,
            "affected_queries": affected_queries,
            "recommendation": self.generate_change_recommendation(changes),
        }

    def generate_change_recommendation(self, changes: List[SchemaChange]) -> str:
        """Generate recommendation for schema changes.

        Args:
            changes: List of schema changes

        Returns:
            Recommendation string
        """
        if any(c.change_type == SchemaChangeType.TABLE_DROPPED for c in changes):
            return "Review all dependent applications before proceeding with table deletion"
        elif any(c.change_type == SchemaChangeType.COLUMN_DROPPED for c in changes):
            return "Verify that dropped columns are not used by any applications"
        else:
            return "Schema changes appear to be additive and low-risk"

    async def process_schema_change_event(self, event: SchemaChangeEvent) -> None:
        """Process detected schema change event.

        Args:
            event: Schema change event to process
        """
        logger.info("Processing schema change event for asset %s: %s changes", event.asset_id, len(event.changes))

        # Classify change severity
        severity = self.assess_change_severity(event.changes)

        # Send notification
        await self.send_schema_change_notification(event, severity)

        # Update asset metadata
        await self.update_asset_schema_metadata(event)

        # Trigger validation if high impact
        if event.impact_assessment["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            await self.trigger_schema_validation(event)

    def assess_change_severity(self, changes: List[SchemaChange]) -> AlertSeverity:
        """Assess alert severity for schema changes.

        Args:
            changes: List of schema changes

        Returns:
            Alert severity level
        """
        for change in changes:
            if change.change_type in [SchemaChangeType.TABLE_DROPPED]:
                return AlertSeverity.CRITICAL
            elif change.change_type in [SchemaChangeType.COLUMN_DROPPED]:
                return AlertSeverity.HIGH
            elif change.change_type in [SchemaChangeType.INDEX_DROPPED]:
                return AlertSeverity.MEDIUM

        return AlertSeverity.LOW

    async def send_schema_change_notification(self, event: SchemaChangeEvent, severity: AlertSeverity) -> None:
        """Send notification about schema change.

        Args:
            event: Schema change event
            severity: Alert severity
        """
        asset = await self.asset_service.get_asset(event.asset_id)
        if not asset:
            logger.error("Asset not found for schema change event: %s", event.asset_id)
            return

        change_summary = self.create_change_summary(event.changes)

        await self.notification_service.send_notification(
            channel="SLACK_MONITORING",  # Would use proper enum
            subject=f"Schema Change Detected: {asset.name}",
            message=f"Database schema changes detected:\n\n"
            f"Asset: {asset.name}\n"
            f"Change Count: {len(event.changes)}\n"
            f"Change Type: {event.change_type.value}\n"
            f"Impact Level: {event.impact_assessment['risk_level'].value}\n\n"
            f"Changes:\n{change_summary}",
            priority=severity.value,
            metadata={
                "asset_id": str(event.asset_id),
                "change_count": len(event.changes),
                "impact_level": event.impact_assessment["risk_level"].value,
            },
        )

    def create_change_summary(self, changes: List[SchemaChange]) -> str:
        """Create summary of schema changes for notifications.

        Args:
            changes: List of schema changes

        Returns:
            Summary string
        """
        summary_lines = []
        for change in changes:
            summary_lines.append(f"- {change.change_type.value}: {change.object_name} ({change.object_type})")

        return "\n".join(summary_lines)

    async def update_asset_schema_metadata(self, event: SchemaChangeEvent) -> None:
        """Update asset metadata with schema change information.

        Args:
            event: Schema change event
        """
        metadata_update = {
            "last_schema_change": event.timestamp.isoformat(),
            "schema_change_count": len(event.changes),
            "schema_hash": event.current_snapshot.schema_hash,
            "table_count": event.current_snapshot.table_count,
            "index_count": event.current_snapshot.index_count,
        }

        await self.asset_service.update_asset_metadata(event.asset_id, metadata_update)

    async def trigger_schema_validation(self, event: SchemaChangeEvent) -> bool:
        """Trigger schema validation for high-impact changes.

        Args:
            event: Schema change event

        Returns:
            True if validation passed
        """
        logger.info("Triggering schema validation for high-impact changes on asset %s", event.asset_id)

        try:
            validation_result = await self.schema_validator.validate_schema_change(event)

            if not validation_result:
                # Send validation failure alert
                await self.notification_service.send_alert(
                    severity=AlertSeverity.CRITICAL,
                    title="Schema Validation Failed",
                    message=f"Schema validation failed for asset {event.asset_id}\n"
                    f"Changes may break application compatibility",
                    affected_assets=[str(event.asset_id)],
                )

            return validation_result
        except Exception as e:
            logger.error("Error during schema validation: %s", e)
            return False

    async def get_postgresql_schema(self, asset: Any) -> SchemaInfo:  # noqa: ANN401
        """Extract PostgreSQL schema information.

        Args:
            asset: PostgreSQL asset

        Returns:
            SchemaInfo object with extracted schema
        """
        try:
            engine = create_engine(asset.connection_string)

            with engine.connect() as conn:
                # Get tables
                tables_query = text(
                    """
                    SELECT schemaname, tablename
                    FROM pg_tables
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                """
                )
                tables_result = conn.execute(tables_query).fetchall()
                tables = [{"name": row[1], "schema": row[0]} for row in tables_result]

                # Get indexes
                indexes_query = text(
                    """
                    SELECT indexname, tablename, schemaname
                    FROM pg_indexes
                    WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
                """
                )
                indexes_result = conn.execute(indexes_query).fetchall()
                indexes = [{"name": row[0], "table": row[1], "schema": row[2]} for row in indexes_result]

                # Get constraints (simplified)
                constraints = []  # Would implement constraint extraction

                return SchemaInfo(tables=tables, indexes=indexes, constraints=constraints)

        except Exception as e:
            logger.error("Error extracting PostgreSQL schema: %s", e)
            return SchemaInfo(tables=[], indexes=[], constraints=[])

    async def get_sqlite_schema(self, asset: Any) -> SchemaInfo:  # noqa: ANN401
        """Extract SQLite schema information.

        Args:
            asset: SQLite asset

        Returns:
            SchemaInfo object with extracted schema
        """
        try:
            conn = sqlite3.connect(asset.file_path)
            cursor = conn.cursor()

            # Get tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables_result = cursor.fetchall()
            tables = [{"name": row[0]} for row in tables_result]

            # Get indexes
            cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index'")
            indexes_result = cursor.fetchall()
            indexes = [{"name": row[0], "table": row[1]} for row in indexes_result]

            # Get constraints (simplified)
            constraints = []  # Would implement constraint extraction

            conn.close()

            return SchemaInfo(tables=tables, indexes=indexes, constraints=constraints)

        except Exception as e:
            logger.error("Error extracting SQLite schema: %s", e)
            return SchemaInfo(tables=[], indexes=[], constraints=[])

    async def get_duckdb_schema(self, asset: Any) -> SchemaInfo:  # noqa: ANN401
        """Extract DuckDB schema information.

        Args:
            asset: DuckDB asset

        Returns:
            SchemaInfo object with extracted schema
        """
        try:
            # DuckDB schema extraction would be implemented here
            # For now, return empty schema
            return SchemaInfo(tables=[], indexes=[], constraints=[])
        except Exception as e:
            logger.error("Error extracting DuckDB schema: %s", e)
            return SchemaInfo(tables=[], indexes=[], constraints=[])


class SchemaValidator:
    """Service for validating schema changes against application requirements."""

    def __init__(self) -> None:
        """Initialize the schema validator."""
        # No initialization required for stateless validator

    async def validate_schema_change(self, change_event: SchemaChangeEvent) -> bool:
        """Validate schema change against application compatibility.

        Args:
            change_event: Schema change event to validate

        Returns:
            True if changes are valid and safe
        """
        try:
            # Validate each change
            for change in change_event.changes:
                if not await self.validate_individual_change(change):
                    return False

            # Validate overall impact
            if change_event.impact_assessment.get("breaking_change", False):
                return await self.validate_breaking_change(change_event)

            return True

        except Exception as e:
            logger.error("Error during schema validation: %s", e)
            return False

    async def validate_individual_change(self, change: SchemaChange) -> bool:
        """Validate individual schema change.

        Args:
            change: Schema change to validate

        Returns:
            True if change is valid
        """
        # Implement validation logic based on change type
        if change.change_type == SchemaChangeType.TABLE_DROPPED:
            return await self.validate_table_drop(change)
        elif change.change_type == SchemaChangeType.COLUMN_DROPPED:
            return await self.validate_column_drop(change)
        else:
            # Most other changes are considered safe
            return True

    async def validate_table_drop(self, change: SchemaChange) -> bool:
        """Validate table drop operation.

        Args:
            change: Table drop change

        Returns:
            True if table drop is safe
        """
        # Check if table is referenced by other tables or applications
        # This would involve analyzing foreign keys, application code, etc.
        logger.warning("Table drop validation for %s", change.object_name)
        return False  # Conservative approach - require manual approval

    async def validate_column_drop(self, change: SchemaChange) -> bool:
        """Validate column drop operation.

        Args:
            change: Column drop change

        Returns:
            True if column drop is safe
        """
        # Check if column is used by applications, queries, etc.
        logger.warning("Column drop validation for %s", change.object_name)
        return False  # Conservative approach - require manual approval

    async def validate_breaking_change(self, change_event: SchemaChangeEvent) -> bool:
        """Validate breaking schema changes.

        Args:
            change_event: Schema change event with breaking changes

        Returns:
            True if breaking changes are acceptable
        """
        # Breaking changes require additional validation
        logger.warning("Breaking schema changes detected for asset %s", change_event.asset_id)

        # Check if there's approval for breaking changes
        # This would integrate with change management systems
        return False  # Require explicit approval for breaking changes
