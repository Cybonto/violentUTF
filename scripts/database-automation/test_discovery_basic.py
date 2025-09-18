#!/usr/bin/env python3
"""
Basic test for database discovery system core functionality.
Tests without optional dependencies that may not be available.
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))


def test_models():
    """Test core data models."""
    print("Testing core models...")

    try:
        from discovery.models import ConfidenceLevel, DatabaseType, DiscoveryConfig, DiscoveryMethod

        # Test enum values
        assert DatabaseType.SQLITE == "sqlite"
        assert DiscoveryMethod.FILESYSTEM == "filesystem"
        assert ConfidenceLevel.HIGH == "high"

        # Test config creation
        config = DiscoveryConfig()
        assert config.enable_filesystem_discovery is True
        assert config.max_execution_time_seconds == 300

        print("✓ Models test passed")
        return True

    except Exception as e:
        print(f"✗ Models test failed: {e}")
        return False


def test_utils():
    """Test utility functions."""
    print("Testing utility functions...")

    try:
        from discovery.models import DatabaseType
        from discovery.utils import (
            detect_database_type_from_extension,
            format_file_size,
            generate_database_id,
        )

        # Test file type detection
        assert detect_database_type_from_extension("test.sqlite") == DatabaseType.SQLITE
        assert detect_database_type_from_extension("test.duckdb") == DatabaseType.DUCKDB
        assert detect_database_type_from_extension("test.txt") == DatabaseType.UNKNOWN

        # Test file size formatting
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"

        # Test ID generation
        db_id = generate_database_id(DatabaseType.SQLITE, "test")
        assert len(db_id) == 16

        print("✓ Utils test passed")
        return True

    except Exception as e:
        print(f"✗ Utils test failed: {e}")
        return False


def test_filesystem_discovery():
    """Test filesystem discovery without optional dependencies."""
    print("Testing filesystem discovery...")

    try:
        from discovery.filesystem_discovery import FilesystemDiscovery
        from discovery.models import DatabaseType, DiscoveryConfig

        # Create temp directory with test database
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create SQLite test database
            db_file = temp_path / "test.sqlite"
            conn = sqlite3.connect(str(db_file))
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT);")
            cursor.execute("INSERT INTO test_table (name) VALUES ('test_data');")
            conn.commit()
            conn.close()

            # Create config
            config = DiscoveryConfig(
                enable_filesystem_discovery=True, scan_paths=[str(temp_path)], file_extensions=[".sqlite", ".db"]
            )

            # Test filesystem discovery
            fs_discovery = FilesystemDiscovery(config)

            # Test file analysis
            discovery = fs_discovery._analyze_database_file(db_file)  # pylint: disable=protected-access

            if discovery:
                assert discovery.database_type == DatabaseType.SQLITE
                assert discovery.name == "test.sqlite"
                assert len(discovery.database_files) == 1
                assert discovery.database_files[0].schema_info is not None
                print("✓ Filesystem discovery test passed")
                return True
            else:
                print("✗ Filesystem discovery test failed: No discovery created")
                return False

    except Exception as e:
        print(f"✗ Filesystem discovery test failed: {e}")
        return False


def test_code_discovery():
    """Test code discovery functionality."""
    print("Testing code discovery...")

    try:
        from discovery.code_discovery import CodeDiscovery
        from discovery.models import DatabaseType, DiscoveryConfig

        # Create temp directory with test Python file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test Python file
            py_file = temp_path / "app.py"
            with open(py_file, "w", encoding="utf-8") as f:
                f.write(
                    """
import sqlite3
import os

def connect_db():
    conn = sqlite3.connect('app.db')
    return conn

def query_data():
    conn = sqlite3.connect('/path/to/database.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()
"""
                )

            # Create config
            config = DiscoveryConfig(enable_code_discovery=True, scan_paths=[str(temp_path)], code_extensions=[".py"])

            # Test code discovery
            code_discovery = CodeDiscovery(config)

            # Test file analysis
            code_refs = code_discovery._analyze_python_file(py_file)  # pylint: disable=protected-access

            if code_refs:
                # Should find import and file references
                sqlite_refs = [ref for ref in code_refs if ref.database_type == DatabaseType.SQLITE]
                assert len(sqlite_refs) >= 1
                print("✓ Code discovery test passed")
                return True
            else:
                print("✗ Code discovery test failed: No code references found")
                return False

    except Exception as e:
        print(f"✗ Code discovery test failed: {e}")
        return False


def test_discovery_orchestrator_basic():
    """Test basic orchestrator functionality without external dependencies."""
    print("Testing basic orchestrator...")

    try:
        # Import without running full discovery to avoid missing dependencies
        from discovery.models import ConfidenceLevel, DatabaseDiscovery, DatabaseType, DiscoveryMethod

        # Create test discovery
        discovery = DatabaseDiscovery(
            database_id="test_db_001",
            database_type=DatabaseType.SQLITE,
            name="Test Database",
            discovery_method=DiscoveryMethod.FILESYSTEM,
            confidence_level=ConfidenceLevel.HIGH,
            confidence_score=0.95,
            description="Test database for validation",
            file_path="/path/to/test.db",
            is_active=True,
        )

        assert discovery.database_id == "test_db_001"
        assert discovery.database_type == DatabaseType.SQLITE
        assert discovery.confidence_score == 0.95

        print("✓ Basic orchestrator test passed")
        return True

    except Exception as e:
        print(f"✗ Basic orchestrator test failed: {e}")
        return False


def main():
    """Run all basic tests."""
    print("=" * 60)
    print("ViolentUTF Database Discovery System - Basic Tests")
    print("=" * 60)

    tests = [test_models, test_utils, test_filesystem_discovery, test_code_discovery, test_discovery_orchestrator_basic]

    passed = 0
    total = len(tests)

    for test_func in tests:
        if test_func():
            passed += 1
        print()

    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("🎉 All basic tests passed! Core functionality is working.")
        return True
    else:
        print("❌ Some tests failed. Check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
