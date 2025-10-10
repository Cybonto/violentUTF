#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Validation Script for DuckDB to SQLite Migration.

Validates that migration was successful by:
- Verifying row counts match
- Validating JSON column parsing
- Checking foreign key relationships
- Generating validation report

Usage:
    python3 validate_config_migration.py
    python3 validate_config_migration.py --app-data-dir ./app_data/violentutf
    python3 validate_config_migration.py --duckdb-file <path>
"""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import duckdb

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MigrationValidator:
    """Validate DuckDB to SQLite migration."""

    TABLES = [
        "generators",
        "datasets",
        "dataset_prompts",
        "converters",
        "scorers",
        "user_sessions",
    ]

    JSON_COLUMNS = {
        "generators": ["parameters", "test_results"],
        "datasets": ["configuration", "metadata"],
        "dataset_prompts": ["metadata"],
        "converters": ["parameters", "test_results"],
        "scorers": ["parameters", "test_results"],
        "user_sessions": ["session_data"],
    }

    def __init__(self, app_data_dir: str = "./app_data/violentutf") -> None:
        """Initialize validator."""
        self.app_data_dir = Path(app_data_dir)
        self.validation_report: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "validations": [],
            "errors": [],
            "summary": {
                "total_databases": 0,
                "validated": 0,
                "failed": 0,
                "total_rows_checked": 0,
            },
        }

    def find_database_pairs(self) -> List[Tuple[Path, Path]]:
        """Find DuckDB and corresponding SQLite database pairs."""
        pairs = []

        if not self.app_data_dir.exists():
            logger.warning("App data directory does not exist: %s", self.app_data_dir)
            return pairs

        # Find all DuckDB files
        duckdb_files = list(self.app_data_dir.glob("pyrit_memory_*.db"))

        for duckdb_file in duckdb_files:
            # Check if it's actually DuckDB (not SQLite)
            if self._is_sqlite_db(duckdb_file):
                continue

            # Look for corresponding SQLite file
            sqlite_file = duckdb_file.with_suffix(".sqlite.db")

            if sqlite_file.exists():
                pairs.append((duckdb_file, sqlite_file))
            else:
                logger.warning("No SQLite migration found for %s", duckdb_file.name)

        logger.info("Found %d database pairs to validate", len(pairs))
        return pairs

    def _is_sqlite_db(self, db_path: Path) -> bool:
        """Check if a database file is SQLite format."""
        try:
            with open(db_path, "rb") as f:
                header = f.read(16)
                return header.startswith(b"SQLite format 3")
        except Exception:
            return False

    def validate_database_pair(self, duckdb_path: Path, sqlite_path: Path) -> Tuple[bool, Dict[str, Any]]:
        """Validate a DuckDB/SQLite database pair."""
        logger.info("Validating: %s → %s", duckdb_path.name, sqlite_path.name)

        validation_result = {
            "duckdb_path": str(duckdb_path),
            "sqlite_path": str(sqlite_path),
            "table_validations": {},
            "json_validations": {},
            "total_rows_checked": 0,
            "passed": False,
        }

        try:
            # Connect to both databases
            duckdb_conn = duckdb.connect(str(duckdb_path), read_only=True)
            sqlite_conn = sqlite3.connect(str(sqlite_path))

            # Validate each table
            all_tables_valid = True

            for table in self.TABLES:
                table_valid, stats = self._validate_table(duckdb_conn, sqlite_conn, table)

                validation_result["table_validations"][table] = {
                    "valid": table_valid,
                    "stats": stats,
                }

                if not table_valid:
                    all_tables_valid = False

                validation_result["total_rows_checked"] += stats.get("duckdb_count", 0)

                # Validate JSON columns
                if table in self.JSON_COLUMNS:
                    json_valid = self._validate_json_columns(sqlite_conn, table, self.JSON_COLUMNS[table])
                    validation_result["json_validations"][table] = json_valid

                    if not json_valid:
                        all_tables_valid = False

            # Validate foreign key relationships
            fk_valid = self._validate_foreign_keys(sqlite_conn)
            validation_result["foreign_keys_valid"] = fk_valid

            if not fk_valid:
                all_tables_valid = False

            validation_result["passed"] = all_tables_valid

            # Close connections
            duckdb_conn.close()
            sqlite_conn.close()

            return validation_result["passed"], validation_result

        except Exception as e:
            logger.error("Validation failed: %s", e)
            validation_result["error"] = str(e)
            validation_result["passed"] = False
            return False, validation_result

    def _validate_table(
        self,
        duckdb_conn: duckdb.DuckDBPyConnection,
        sqlite_conn: sqlite3.Connection,
        table: str,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate row counts for a table."""
        stats = {"table": table}

        try:
            # Check if table exists in DuckDB
            result = duckdb_conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
                [table],
            ).fetchone()

            if not result or result[0] == 0:
                logger.info("Table %s does not exist in DuckDB", table)
                stats["duckdb_count"] = 0
                stats["sqlite_count"] = 0
                return True, stats

            # Get DuckDB count
            # Table name is from TABLES constant - safe to use in query
            duckdb_result = duckdb_conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()  # nosec B608
            stats["duckdb_count"] = duckdb_result[0] if duckdb_result else 0

            # Get SQLite count
            # Table name is from TABLES constant - safe to use in query
            sqlite_cursor = sqlite_conn.execute(f'SELECT COUNT(*) FROM "{table}"')  # nosec B608
            sqlite_result = sqlite_cursor.fetchone()
            stats["sqlite_count"] = sqlite_result[0] if sqlite_result else 0

            # Compare counts
            if stats["duckdb_count"] == stats["sqlite_count"]:
                logger.info("✓ Table %s: %d rows match", table, stats["duckdb_count"])
                return True, stats
            else:
                logger.error(
                    "✗ Table %s: DuckDB=%d, SQLite=%d (MISMATCH)",
                    table,
                    stats["duckdb_count"],
                    stats["sqlite_count"],
                )
                return False, stats

        except Exception as e:
            logger.error("Failed to validate table %s: %s", table, e)
            stats["error"] = str(e)
            return False, stats

    def _validate_json_columns(
        self,
        sqlite_conn: sqlite3.Connection,
        table: str,
        columns: List[str],
    ) -> bool:
        """Validate JSON columns can be parsed."""
        all_valid = True

        for column in columns:
            try:
                # Column and table names are from JSON_COLUMNS constant - safe
                cursor = sqlite_conn.execute(
                    f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'  # nosec B608
                )

                for row in cursor.fetchall():
                    json_text = row[0]
                    if json_text:
                        try:
                            json.loads(json_text)
                        except json.JSONDecodeError as e:
                            logger.error(
                                "✗ Invalid JSON in %s.%s: %s",
                                table,
                                column,
                                e,
                            )
                            all_valid = False

                if all_valid:
                    logger.info("✓ JSON validation passed for %s.%s", table, column)

            except Exception as e:
                logger.error(
                    "Failed to validate JSON column %s.%s: %s",
                    table,
                    column,
                    e,
                )
                all_valid = False

        return all_valid

    def _validate_foreign_keys(self, sqlite_conn: sqlite3.Connection) -> bool:
        """Validate foreign key relationships."""
        try:
            # Check dataset_prompts -> datasets relationship
            cursor = sqlite_conn.execute(
                """
                SELECT COUNT(*) FROM dataset_prompts dp
                LEFT JOIN datasets d ON dp.dataset_id = d.id
                WHERE d.id IS NULL
                """
            )
            orphaned_prompts = cursor.fetchone()[0]

            if orphaned_prompts > 0:
                logger.error("✗ Found %d orphaned dataset_prompts", orphaned_prompts)
                return False

            logger.info("✓ Foreign key relationships validated")
            return True

        except Exception as e:
            logger.error("Failed to validate foreign keys: %s", e)
            return False

    def validate_all(self) -> Dict[str, Any]:
        """Validate all database pairs."""
        logger.info("Starting validation process")

        database_pairs = self.find_database_pairs()

        if not database_pairs:
            logger.warning("No database pairs found to validate")
            return self.validation_report

        self.validation_report["summary"]["total_databases"] = len(database_pairs)

        for duckdb_path, sqlite_path in database_pairs:
            passed, result = self.validate_database_pair(duckdb_path, sqlite_path)

            if passed:
                self.validation_report["validations"].append(result)
                self.validation_report["summary"]["validated"] += 1
                self.validation_report["summary"]["total_rows_checked"] += result["total_rows_checked"]
            else:
                self.validation_report["errors"].append(result)
                self.validation_report["summary"]["failed"] += 1

        # Generate summary
        self._print_summary()

        return self.validation_report

    def _print_summary(self) -> None:
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Timestamp: {self.validation_report['timestamp']}")
        print(f"Total Databases: {self.validation_report['summary']['total_databases']}")
        print(f"Validated: {self.validation_report['summary']['validated']}")
        print(f"Failed: {self.validation_report['summary']['failed']}")
        print(f"Total Rows Checked: {self.validation_report['summary']['total_rows_checked']}")

        if self.validation_report["validations"]:
            print("\nSuccessfully Validated:")
            for validation in self.validation_report["validations"]:
                print(f"  - {Path(validation['duckdb_path']).name}")
                print(f"    Rows checked: {validation['total_rows_checked']}")

        if self.validation_report["errors"]:
            print("\nValidation Errors:")
            for error in self.validation_report["errors"]:
                print(f"  - {Path(error['duckdb_path']).name}")
                if "error" in error:
                    print(f"    Error: {error['error']}")
                else:
                    print("    Row count mismatches found")

        # Determine overall status
        if self.validation_report["summary"]["failed"] == 0:
            print("\n✓ ALL VALIDATIONS PASSED")
        else:
            print(f"\n✗ {self.validation_report['summary']['failed']} " "VALIDATION(S) FAILED")

        print("=" * 70 + "\n")


def main() -> int:
    """Execute validation process based on command-line arguments."""
    parser = argparse.ArgumentParser(description="Validate DuckDB to SQLite migration")
    parser.add_argument(
        "--app-data-dir",
        type=str,
        default="./app_data/violentutf",
        help="Path to app data directory",
    )
    parser.add_argument(
        "--duckdb-file",
        type=str,
        help="Validate specific DuckDB file",
    )
    parser.add_argument(
        "--sqlite-file",
        type=str,
        help="Corresponding SQLite file (required with --duckdb-file)",
    )

    args = parser.parse_args()

    # Create validator
    validator = MigrationValidator(app_data_dir=args.app_data_dir)

    if args.duckdb_file:
        if not args.sqlite_file:
            parser.error("--sqlite-file required when using --duckdb-file")

        duckdb_path = Path(args.duckdb_file)
        sqlite_path = Path(args.sqlite_file)

        if not duckdb_path.exists():
            logger.error("DuckDB file not found: %s", duckdb_path)
            return 1

        if not sqlite_path.exists():
            logger.error("SQLite file not found: %s", sqlite_path)
            return 1

        passed, result = validator.validate_database_pair(duckdb_path, sqlite_path)
        validator.validation_report["validations"].append(result)
        validator._print_summary()  # pylint: disable=protected-access

        return 0 if passed else 1
    else:
        # Validate all database pairs
        report = validator.validate_all()

        # Save report
        report_path = Path(args.app_data_dir) / "validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info("Validation report saved to %s", report_path)

        # Return exit code
        if report["summary"]["failed"] > 0:
            return 1
        return 0


if __name__ == "__main__":
    sys.exit(main())
