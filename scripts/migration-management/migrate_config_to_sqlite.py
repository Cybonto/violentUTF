#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Data Migration Script: DuckDB to SQLite for ViolentUTF Configuration Storage.

Migrates all user configuration data from DuckDB to SQLite while preserving
all table schemas and relationships.

Usage:
    python3 migrate_config_to_sqlite.py --dry-run    # Test without changes
    python3 migrate_config_to_sqlite.py --execute    # Perform migration
    python3 migrate_config_to_sqlite.py --user-db <path>  # Migrate specific DB
"""

import argparse
import json
import logging
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DuckDBToSQLiteMigrator:
    """Migrate DuckDB configuration databases to SQLite."""

    # Tables to migrate in order (respecting dependencies)
    TABLES_TO_MIGRATE = [
        "generators",
        "datasets",
        "dataset_prompts",
        "converters",
        "scorers",
        "user_sessions",
    ]

    def __init__(
        self,
        app_data_dir: str = "./app_data/violentutf",
        dry_run: bool = True,
    ) -> None:
        """Initialize migrator."""
        self.app_data_dir = Path(app_data_dir)
        self.dry_run = dry_run
        self.migration_report: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "databases_migrated": [],
            "errors": [],
            "total_rows_migrated": 0,
        }

    def find_duckdb_files(self) -> List[Path]:
        """Find all DuckDB files in app data directory."""
        if not self.app_data_dir.exists():
            logger.warning("App data directory does not exist: %s", self.app_data_dir)
            return []

        duckdb_files = list(self.app_data_dir.glob("pyrit_memory_*.db"))
        # Exclude already migrated SQLite files
        duckdb_files = [f for f in duckdb_files if not self._is_sqlite_db(f)]

        logger.info("Found %d DuckDB files to migrate", len(duckdb_files))
        return duckdb_files

    def _is_sqlite_db(self, db_path: Path) -> bool:
        """Check if a database file is SQLite format."""
        try:
            with open(db_path, "rb") as f:
                header = f.read(16)
                # SQLite magic header
                return header.startswith(b"SQLite format 3")
        except Exception:
            return False

    def migrate_database(self, duckdb_path: Path) -> Tuple[bool, Dict[str, Any]]:
        """Migrate a single DuckDB file to SQLite."""
        logger.info("Starting migration of %s", duckdb_path)

        # Generate SQLite path
        sqlite_path = duckdb_path.with_suffix(".sqlite.db")

        if sqlite_path.exists():
            logger.warning("SQLite file already exists: %s", sqlite_path)
            if not self.dry_run:
                backup_path = sqlite_path.with_suffix(".sqlite.db.backup")
                shutil.copy2(sqlite_path, backup_path)
                logger.info("Created backup: %s", backup_path)

        migration_stats = {
            "duckdb_path": str(duckdb_path),
            "sqlite_path": str(sqlite_path),
            "tables": {},
            "total_rows": 0,
            "success": False,
        }

        try:
            # Connect to both databases
            duckdb_conn = duckdb.connect(str(duckdb_path))
            sqlite_conn = sqlite3.connect(str(sqlite_path)) if not self.dry_run else None

            if sqlite_conn:
                # Set SQLite pragmas for optimization
                sqlite_conn.execute("PRAGMA journal_mode=WAL")
                sqlite_conn.execute("PRAGMA synchronous=NORMAL")
                sqlite_conn.execute("PRAGMA cache_size=10000")
                sqlite_conn.execute("PRAGMA foreign_keys=ON")

                # Create tables in SQLite
                self._create_sqlite_tables(sqlite_conn)

            # Migrate each table
            for table in self.TABLES_TO_MIGRATE:
                rows_migrated = self._migrate_table(
                    duckdb_conn,
                    sqlite_conn,
                    table,
                )
                migration_stats["tables"][table] = rows_migrated
                migration_stats["total_rows"] += rows_migrated

            # Verify migration
            if sqlite_conn:
                verification_passed = self._verify_migration(
                    duckdb_conn,
                    sqlite_conn,
                )
                if verification_passed:
                    sqlite_conn.commit()
                    migration_stats["success"] = True
                    logger.info(
                        "Migration successful: %d rows migrated",
                        migration_stats["total_rows"],
                    )
                else:
                    sqlite_conn.rollback()
                    logger.error("Migration verification failed, rolled back")
                    migration_stats["success"] = False
            else:
                # Dry run - just report what would be migrated
                migration_stats["success"] = True
                logger.info(
                    "[DRY RUN] Would migrate %d rows",
                    migration_stats["total_rows"],
                )

            # Close connections
            duckdb_conn.close()
            if sqlite_conn:
                sqlite_conn.close()

            return migration_stats["success"], migration_stats

        except Exception as e:
            logger.error("Migration failed for %s: %s", duckdb_path, e)
            migration_stats["error"] = str(e)
            migration_stats["success"] = False
            return False, migration_stats

    def _create_sqlite_tables(self, conn: sqlite3.Connection) -> None:
        """Create SQLite tables matching DuckDB schema."""
        # Generators table
        conn.execute(
            """CREATE TABLE IF NOT EXISTS generators (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                test_results TEXT
            )
        """
        )

        # Datasets table
        conn.execute(
            """CREATE TABLE IF NOT EXISTS datasets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                configuration TEXT NOT NULL,
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                metadata TEXT
            )
        """
        )

        # Dataset prompts table
        conn.execute(
            """CREATE TABLE IF NOT EXISTS dataset_prompts (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                prompt_index INTEGER,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Converters table
        conn.execute(
            """CREATE TABLE IF NOT EXISTS converters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                test_results TEXT
            )
        """
        )

        # Scorers table
        conn.execute(
            """CREATE TABLE IF NOT EXISTS scorers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parameters TEXT NOT NULL,
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                test_results TEXT
            )
        """
        )

        # Sessions table
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_key TEXT NOT NULL,
                session_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(user_id, session_key)
            )
        """
        )

        conn.commit()

    def _migrate_table(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        sqlite_conn: Optional[sqlite3.Connection],
        table: str,
    ) -> int:
        """Migrate a single table from DuckDB to SQLite."""
        try:
            # Check if table exists in DuckDB
            result = duckdb_conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [table],
            ).fetchone()

            if not result or result[0] == 0:
                logger.info("Table %s does not exist in DuckDB, skipping", table)
                return 0

            # Get all rows from DuckDB
            # Table name is from TABLES_TO_MIGRATE constant - safe to use
            rows = duckdb_conn.execute(f'SELECT * FROM "{table}"').fetchall()  # nosec B608

            if not rows:
                logger.info("Table %s is empty, skipping", table)
                return 0

            # Get column names
            columns = [desc[0] for desc in duckdb_conn.description]

            logger.info(
                "Migrating table %s: %d rows, %d columns",
                table,
                len(rows),
                len(columns),
            )

            if sqlite_conn and not self.dry_run:
                # Insert into SQLite
                placeholders = ",".join(["?" for _ in columns])
                insert_query = f'INSERT OR REPLACE INTO "{table}" VALUES ({placeholders})'

                for row in rows:
                    sqlite_conn.execute(insert_query, row)

            return len(rows)

        except Exception as e:
            logger.error("Failed to migrate table %s: %s", table, e)
            raise

    def _verify_migration(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        sqlite_conn: sqlite3.Connection,
    ) -> bool:
        """Verify row counts match between DuckDB and SQLite."""
        all_verified = True

        for table in self.TABLES_TO_MIGRATE:
            try:
                # Get DuckDB count
                # Table name is from TABLES_TO_MIGRATE constant - safe to use
                duckdb_result = duckdb_conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()  # nosec B608
                duckdb_count = duckdb_result[0] if duckdb_result else 0

                # Get SQLite count
                # Table name is from TABLES_TO_MIGRATE constant - safe to use
                sqlite_cursor = sqlite_conn.execute(f'SELECT COUNT(*) FROM "{table}"')  # nosec B608
                sqlite_result = sqlite_cursor.fetchone()
                sqlite_count = sqlite_result[0] if sqlite_result else 0

                if duckdb_count == sqlite_count:
                    logger.info(
                        "✓ Table %s: %d rows verified",
                        table,
                        duckdb_count,
                    )
                else:
                    logger.error(
                        "✗ Table %s: DuckDB has %d rows, SQLite has %d rows",
                        table,
                        duckdb_count,
                        sqlite_count,
                    )
                    all_verified = False

            except Exception as e:
                logger.error("Verification failed for table %s: %s", table, e)
                all_verified = False

        return all_verified

    def migrate_all(self) -> Dict[str, Any]:
        """Migrate all DuckDB files to SQLite."""
        logger.info("Starting migration process (dry_run=%s)", self.dry_run)

        duckdb_files = self.find_duckdb_files()

        if not duckdb_files:
            logger.warning("No DuckDB files found to migrate")
            return self.migration_report

        for duckdb_file in duckdb_files:
            success, stats = self.migrate_database(duckdb_file)

            if success:
                self.migration_report["databases_migrated"].append(stats)
                self.migration_report["total_rows_migrated"] += stats["total_rows"]
            else:
                self.migration_report["errors"].append(stats)

        # Generate summary
        self._print_summary()

        return self.migration_report

    def _print_summary(self) -> None:
        """Print migration summary."""
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print(f"Dry Run: {self.migration_report['dry_run']}")
        print(f"Timestamp: {self.migration_report['timestamp']}")
        print(f"Databases Migrated: {len(self.migration_report['databases_migrated'])}")
        print(f"Total Rows Migrated: {self.migration_report['total_rows_migrated']}")
        print(f"Errors: {len(self.migration_report['errors'])}")

        if self.migration_report["databases_migrated"]:
            print("\nSuccessfully Migrated:")
            for db in self.migration_report["databases_migrated"]:
                print(f"  - {db['duckdb_path']}")
                print(f"    → {db['sqlite_path']}")
                print(f"    Rows: {db['total_rows']}")

        if self.migration_report["errors"]:
            print("\nErrors:")
            for error in self.migration_report["errors"]:
                print(f"  - {error.get('duckdb_path', 'Unknown')}")
                print(f"    Error: {error.get('error', 'Unknown error')}")

        print("=" * 70 + "\n")


def main() -> int:
    """Execute migration process based on command-line arguments."""
    parser = argparse.ArgumentParser(description="Migrate DuckDB configuration data to SQLite")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test migration without making changes",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute migration (writes to SQLite)",
    )
    parser.add_argument(
        "--app-data-dir",
        type=str,
        default="./app_data/violentutf",
        help="Path to app data directory",
    )
    parser.add_argument(
        "--user-db",
        type=str,
        help="Migrate specific database file",
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.dry_run and not args.execute:
        parser.error("Must specify either --dry-run or --execute")

    dry_run = args.dry_run

    # Create migrator
    migrator = DuckDBToSQLiteMigrator(
        app_data_dir=args.app_data_dir,
        dry_run=dry_run,
    )

    if args.user_db:
        # Migrate specific database
        user_db_path = Path(args.user_db)
        if not user_db_path.exists():
            logger.error("Database file not found: %s", user_db_path)
            return 1

        success, stats = migrator.migrate_database(user_db_path)
        migrator.migration_report["databases_migrated"].append(stats)
        migrator._print_summary()  # pylint: disable=protected-access
        return 0 if success else 1
    else:
        # Migrate all databases
        report = migrator.migrate_all()

        # Save report
        if not dry_run:
            report_path = Path(args.app_data_dir) / "migration_report.json"
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info("Migration report saved to %s", report_path)

        # Return exit code
        if report["errors"]:
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
