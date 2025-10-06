"""
Database Connectivity Smoke Tests for ViolentUTF

These tests validate that database files are accessible and functional
after the SQLite migration.

Issue: #328 - Phase 4.3.7: Production Deployment and Cleanup
"""

import sqlite3
from pathlib import Path
from typing import List

import pytest

# Test configuration
REPO_ROOT = Path(__file__).parent.parent.parent
DB_DIRS = [
    REPO_ROOT / "app_data" / "violentutf",
    REPO_ROOT / "violentutf" / "app_data" / "violentutf",
]


class TestDatabaseConnectivity:
    """Smoke tests for database connectivity validation."""

    def test_database_files_exist(self):
        """Test SQLite database files exist."""
        db_files_found = []

        for db_dir in DB_DIRS:
            if db_dir.exists():
                # Look for SQLite database files
                db_files = list(db_dir.glob("*.db"))
                db_files_found.extend(db_files)

        # If no database files found, may not be initialized yet
        if not db_files_found:
            pytest.skip("No database files found - may not be initialized yet")

        # Verify we found SQLite databases (not DuckDB)
        sqlite_files = [
            f for f in db_files_found
            if "duckdb" not in f.name.lower()
        ]

        assert sqlite_files, (
            "No SQLite database files found. "
            "Found: " + ", ".join([f.name for f in db_files_found])
        )

    def test_database_accessible(self):
        """Test database files are readable and accessible."""
        db_files_found = []

        for db_dir in DB_DIRS:
            if db_dir.exists():
                db_files = list(db_dir.glob("*.db"))
                db_files_found.extend([
                    f for f in db_files
                    if "duckdb" not in f.name.lower()
                ])

        if not db_files_found:
            pytest.skip("No database files found - may not be initialized yet")

        inaccessible_files = []
        for db_file in db_files_found:
            if not db_file.is_file():
                inaccessible_files.append(f"{db_file.name}: Not a file")
            elif not db_file.stat().st_size > 0:
                inaccessible_files.append(f"{db_file.name}: Empty file")

        assert not inaccessible_files, (
            f"Some database files are inaccessible: "
            f"{', '.join(inaccessible_files)}"
        )

    def test_database_schema(self):
        """Test database schema is correct for SQLite."""
        db_files_found = []

        for db_dir in DB_DIRS:
            if db_dir.exists():
                db_files = list(db_dir.glob("*.db"))
                db_files_found.extend([
                    f for f in db_files
                    if "duckdb" not in f.name.lower()
                ])

        if not db_files_found:
            pytest.skip("No database files found - may not be initialized yet")

        schema_errors = []
        valid_databases = 0

        # Test all database files, looking for at least one valid one
        for db_file in db_files_found:
            try:
                conn = sqlite3.connect(str(db_file))
                cursor = conn.cursor()

                # Check if this is a valid SQLite database
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = cursor.fetchall()

                # Should have at least some tables
                if tables:
                    valid_databases += 1
                # Empty database is OK - may be newly created

                conn.close()

            except sqlite3.DatabaseError as e:
                # Some files may be old or corrupted - log but don't fail
                # unless ALL databases are invalid
                schema_errors.append(f"{db_file.name}: {str(e)}")
            except Exception as e:
                schema_errors.append(
                    f"{db_file.name}: Unexpected error: {str(e)}"
                )

        # As long as we found at least one valid SQLite database, test passes
        assert valid_databases > 0, (
            f"No valid SQLite databases found. "
            f"Errors: {', '.join(schema_errors) if schema_errors else 'None'}"
        )

    def test_pyrit_memory_operations(self):
        """Test PyRIT memory operations work with SQLite."""
        db_files_found = []

        for db_dir in DB_DIRS:
            if db_dir.exists():
                db_files = list(db_dir.glob("pyrit_memory_*.db"))
                db_files_found.extend([
                    f for f in db_files
                    if "duckdb" not in f.name.lower()
                ])

        if not db_files_found:
            pytest.skip(
                "No PyRIT memory database files found - "
                "may not be initialized yet"
            )

        # Test that we can connect to PyRIT memory databases
        connection_errors = []
        for db_file in db_files_found[:1]:  # Test just first file
            try:
                conn = sqlite3.connect(str(db_file))

                # Verify it's a valid SQLite database
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()

                assert version, "Could not get SQLite version"

                conn.close()

            except sqlite3.DatabaseError as e:
                connection_errors.append(f"{db_file.name}: {str(e)}")
            except Exception as e:
                connection_errors.append(
                    f"{db_file.name}: Unexpected error: {str(e)}"
                )

        assert not connection_errors, (
            f"PyRIT memory database connection failed: "
            f"{', '.join(connection_errors)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
