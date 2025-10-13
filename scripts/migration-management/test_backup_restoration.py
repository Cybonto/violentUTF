#!/usr/bin/env python3
"""
DuckDB Backup Restoration Testing for ViolentUTF Migration
Issue: #322 - Phase 4.3.1: DuckDB Data Inventory and Backup Strategy

This script validates backup integrity through restoration testing:
- Creates isolated test environment
- Restores backups to temporary directory
- Verifies checksums match original files
- Tests DuckDB file accessibility and queries
- Validates schema integrity
- Cleans up test environment

Usage:
    python3 test_backup_restoration.py --validate
    python3 test_backup_restoration.py --backup-dir backups/duckdb_backup_20251005_120000
    python3 test_backup_restoration.py --full-test --verbose
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb library not found. Install with: pip install duckdb")
    sys.exit(1)

# Configure logging
LOG_FILE = "logs/restoration_test.log"
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class BackupRestorationTester:
    """Tester for DuckDB backup restoration and integrity validation."""

    def __init__(self, backup_dir: str, verbose: bool = False):
        """Initialize the restoration tester.

        Args:
            backup_dir: Path to backup directory to test
            verbose: Enable verbose logging
        """
        self.backup_dir = Path(backup_dir).resolve()
        self.verbose = verbose
        self.test_dir: Optional[Path] = None
        self.test_results: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "backup_tested": str(backup_dir),
            "tests_passed": 0,
            "tests_failed": 0,
            "test_details": [],
        }

        if verbose:
            logger.setLevel(logging.DEBUG)

        logger.info("Initialized Backup Restoration Tester for %s", self.backup_dir)

    def create_test_environment(self) -> Path:
        """Create isolated test environment for restoration.

        Returns:
            Path to test directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_dir = Path(tempfile.gettempdir()) / f"duckdb_restore_test_{timestamp}"
        test_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Created test environment: %s", test_dir)
        self.test_dir = test_dir
        return test_dir

    def cleanup_test_environment(self) -> None:
        """Clean up test environment."""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            logger.info("Cleaned up test environment: %s", self.test_dir)

    def verify_backup_structure(self) -> Tuple[bool, str]:
        """Verify backup directory has required structure.

        Returns:
            Tuple of (success, message)
        """
        required_files = ["checksums.sha256", "backup_manifest.json"]

        for req_file in required_files:
            file_path = self.backup_dir / req_file
            if not file_path.exists():
                msg = f"Missing required file: {req_file}"
                logger.error(msg)
                return False, msg

        logger.info("✓ Backup structure verified")
        return True, "Backup structure valid"

    def load_backup_manifest(self) -> Optional[Dict[str, Any]]:
        """Load and parse backup manifest.

        Returns:
            Manifest dictionary or None on error
        """
        manifest_path = self.backup_dir / "backup_manifest.json"

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            logger.info("✓ Loaded backup manifest")
            return manifest
        except Exception as e:
            logger.error("Failed to load manifest: %s", e)
            return None

    def calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum for a file.

        Args:
            file_path: Path to file

        Returns:
            SHA256 checksum as hex string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def verify_checksums(self) -> Tuple[bool, Dict[str, Any]]:
        """Verify all file checksums match stored checksums.

        Returns:
            Tuple of (success, results_dict)
        """
        logger.info("Verifying checksums...")

        checksum_file = self.backup_dir / "checksums.sha256"
        if not checksum_file.exists():
            return False, {"error": "Checksum file not found"}

        results: Dict[str, Any] = {
            "total_files": 0,
            "verified": 0,
            "failed": 0,
            "missing": 0,
            "failures": [],
        }

        try:
            with open(checksum_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split(None, 1)
                    if len(parts) != 2:
                        continue

                    expected_checksum, relative_path = parts
                    file_path = self.backup_dir / relative_path

                    results["total_files"] += 1

                    if not file_path.exists():
                        results["missing"] += 1
                        results["failures"].append({"file": relative_path, "reason": "File not found"})
                        continue

                    actual_checksum = self.calculate_file_checksum(file_path)

                    if actual_checksum == expected_checksum:
                        results["verified"] += 1
                        logger.debug("✓ Checksum match: %s", relative_path)
                    else:
                        results["failed"] += 1
                        results["failures"].append(
                            {
                                "file": relative_path,
                                "reason": "Checksum mismatch",
                                "expected": expected_checksum,
                                "actual": actual_checksum,
                            }
                        )
                        logger.error("✗ Checksum mismatch: %s", relative_path)

            success = results["failed"] == 0 and results["missing"] == 0
            if success:
                logger.info("✓ All checksums verified: %s/%s", results["verified"], results["total_files"])
            else:
                logger.error(
                    "✗ Checksum verification failed: %d failed, %d missing", results["failed"], results["missing"]
                )

            return success, results

        except Exception as e:
            logger.error("Checksum verification error: %s", e)
            return False, {"error": str(e)}

    def restore_single_file(self, source_file: Path, dest_dir: Path) -> bool:
        """Restore a single file to test directory.

        Args:
            source_file: Source file in backup
            dest_dir: Destination directory

        Returns:
            True if restoration successful
        """
        try:
            # Preserve relative path structure
            relative_path = source_file.relative_to(self.backup_dir)
            dest_file = dest_dir / relative_path

            # Create parent directories
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_file, dest_file)

            # Verify checksum
            source_checksum = self.calculate_file_checksum(source_file)
            dest_checksum = self.calculate_file_checksum(dest_file)

            if source_checksum == dest_checksum:
                logger.debug("✓ Restored: %s", relative_path)
                return True
            else:
                logger.error("✗ Checksum mismatch after restore: %s", relative_path)
                return False

        except Exception as e:
            logger.error("Failed to restore %s: %s", source_file, e)
            return False

    def test_full_restoration(self) -> Tuple[bool, Dict[str, Any]]:
        """Test full backup restoration to test directory.

        Returns:
            Tuple of (success, results_dict)
        """
        logger.info("Testing full backup restoration...")

        if not self.test_dir:
            self.create_test_environment()

        results: Dict[str, Any] = {
            "files_restored": 0,
            "files_failed": 0,
            "failures": [],
        }

        # Find all .db files in backup
        db_files = list(self.backup_dir.rglob("*.db"))

        # Ensure test_dir is set
        if not self.test_dir:
            return False, {"error": "Test directory not initialized"}

        for db_file in db_files:
            if self.restore_single_file(db_file, self.test_dir):
                results["files_restored"] += 1
            else:
                results["files_failed"] += 1
                results["failures"].append(str(db_file))

        success = results["files_failed"] == 0
        if success:
            logger.info("✓ Full restoration successful: %s files", results["files_restored"])
        else:
            logger.error("✗ Restoration failed: %s failures", results["files_failed"])

        return success, results

    def test_duckdb_accessibility(self, db_file: Path) -> Tuple[bool, Dict[str, Any]]:
        """Test if DuckDB file can be opened and queried.

        Args:
            db_file: Path to DuckDB file

        Returns:
            Tuple of (success, results_dict)
        """
        results = {
            "file": str(db_file),
            "readable": False,
            "tables": [],
            "query_success": False,
            "error": None,
        }

        try:
            # Try to open DuckDB file
            conn = duckdb.connect(str(db_file), read_only=True)
            results["readable"] = True

            # Get list of tables
            tables_result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()

            tables = [row[0] for row in tables_result]
            results["tables"] = tables

            # Try basic query on first table
            if tables:
                # Table name from DuckDB schema, not user input
                test_query = f"SELECT COUNT(*) FROM {tables[0]}"  # nosec B608
                count_result = conn.execute(test_query).fetchone()
                results["query_success"] = True
                results["sample_count"] = count_result[0] if count_result else 0

            conn.close()

            logger.debug("✓ DuckDB accessible: %s", db_file.name)
            return True, results

        except Exception as e:
            results["error"] = str(e)
            logger.error("✗ DuckDB access failed for %s: %s", db_file.name, e)
            return False, results

    def test_all_restored_databases(self) -> Tuple[bool, Dict[str, Any]]:
        """Test accessibility of all restored DuckDB files.

        Returns:
            Tuple of (success, results_dict)
        """
        logger.info("Testing DuckDB accessibility...")

        if not self.test_dir:
            logger.error("Test directory not initialized")
            return False, {"error": "Test directory not initialized"}

        results: Dict[str, Any] = {
            "total_databases": 0,
            "accessible": 0,
            "inaccessible": 0,
            "test_details": [],
        }

        # Find all restored .db files
        db_files = list(self.test_dir.rglob("*.db"))
        results["total_databases"] = len(db_files)

        for db_file in db_files:
            accessible, test_result = self.test_duckdb_accessibility(db_file)

            results["test_details"].append(test_result)

            if accessible:
                results["accessible"] += 1
            else:
                results["inaccessible"] += 1

        success = results["inaccessible"] == 0
        if success:
            logger.info("✓ All databases accessible: %s/%s", results["accessible"], results["total_databases"])
        else:
            logger.error("✗ Some databases inaccessible: %s", results["inaccessible"])

        return success, results

    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete test suite.

        Returns:
            Complete test results dictionary
        """
        logger.info("Starting complete restoration test suite")

        # Test 1: Verify backup structure
        logger.info("\n[Test 1/5] Verifying backup structure...")
        success, message = self.verify_backup_structure()
        self.test_results["test_details"].append({"test": "backup_structure", "success": success, "message": message})
        if success:
            self.test_results["tests_passed"] += 1
        else:
            self.test_results["tests_failed"] += 1

        # Test 2: Load manifest
        logger.info("\n[Test 2/5] Loading backup manifest...")
        manifest = self.load_backup_manifest()
        success = manifest is not None
        self.test_results["test_details"].append(
            {
                "test": "load_manifest",
                "success": success,
                "manifest": manifest if success else None,
            }
        )
        if success:
            self.test_results["tests_passed"] += 1
        else:
            self.test_results["tests_failed"] += 1

        # Test 3: Verify checksums
        logger.info("\n[Test 3/5] Verifying checksums...")
        success, checksum_results = self.verify_checksums()
        self.test_results["test_details"].append(
            {
                "test": "verify_checksums",
                "success": success,
                "results": checksum_results,
            }
        )
        if success:
            self.test_results["tests_passed"] += 1
        else:
            self.test_results["tests_failed"] += 1

        # Test 4: Full restoration
        logger.info("\n[Test 4/5] Testing full restoration...")
        self.create_test_environment()
        success, restoration_results = self.test_full_restoration()
        self.test_results["test_details"].append(
            {
                "test": "full_restoration",
                "success": success,
                "results": restoration_results,
            }
        )
        if success:
            self.test_results["tests_passed"] += 1
        else:
            self.test_results["tests_failed"] += 1

        # Test 5: Database accessibility
        logger.info("\n[Test 5/5] Testing database accessibility...")
        success, db_results = self.test_all_restored_databases()
        self.test_results["test_details"].append(
            {
                "test": "database_accessibility",
                "success": success,
                "results": db_results,
            }
        )
        if success:
            self.test_results["tests_passed"] += 1
        else:
            self.test_results["tests_failed"] += 1

        # Cleanup
        logger.info("\nCleaning up test environment...")
        self.cleanup_test_environment()

        # Finalize results
        self.test_results["end_time"] = datetime.now().isoformat()
        self.test_results["all_tests_passed"] = self.test_results["tests_failed"] == 0

        return self.test_results

    def save_test_results(self, output_path: str) -> None:
        """Save test results to JSON file.

        Args:
            output_path: Path to save results
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        logger.info("Test results saved to: %s", output_file)


def find_latest_backup(backup_base_dir: str = "backups") -> Optional[Path]:
    """Find the most recent backup directory.

    Args:
        backup_base_dir: Base directory containing backups

    Returns:
        Path to latest backup or None if not found
    """
    backup_path = Path(backup_base_dir)
    if not backup_path.exists():
        return None

    backup_dirs = [d for d in backup_path.iterdir() if d.is_dir() and d.name.startswith("duckdb_backup_")]

    if not backup_dirs:
        return None

    # Sort by name (timestamp in name) and return latest
    latest = sorted(backup_dirs, reverse=True)[0]
    return latest


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description="Test DuckDB backup restoration and integrity")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run complete validation test suite",
    )
    parser.add_argument("--backup-dir", type=str, help="Specific backup directory to test")
    parser.add_argument(
        "--full-test",
        action="store_true",
        help="Run full test suite (same as --validate)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/restoration_test_results.json",
        help="Output JSON file for test results",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    try:
        # Determine backup directory
        if args.backup_dir:
            backup_dir = args.backup_dir
        else:
            latest_backup = find_latest_backup()
            if not latest_backup:
                logger.error("No backup directory found. Run backup script first.")
                return 1
            backup_dir = str(latest_backup)
            logger.info("Using latest backup: %s", backup_dir)

        # Verify backup exists
        if not Path(backup_dir).exists():
            logger.error("Backup directory not found: %s", backup_dir)
            return 1

        print("\nDuckDB Backup Restoration Testing")
        print("=" * 50)
        print(f"Backup: {backup_dir}")
        print(f"Output: {args.output}")
        print("=" * 50 + "\n")

        # Initialize tester
        tester = BackupRestorationTester(backup_dir, verbose=args.verbose)

        # Run tests
        results = tester.run_all_tests()

        # Save results
        tester.save_test_results(args.output)

        # Display summary
        print("\n" + "=" * 50)
        print("Test Results Summary")
        print("=" * 50)
        print(f"Tests Passed: {results['tests_passed']}")
        print(f"Tests Failed: {results['tests_failed']}")
        print(f"Overall: {'✓ PASSED' if results['all_tests_passed'] else '✗ FAILED'}")
        print("=" * 50 + "\n")

        if results["all_tests_passed"]:
            print("✓ All restoration tests passed successfully")
            return 0
        else:
            print("✗ Some restoration tests failed. Check logs for details.")
            return 1

    except Exception as e:
        logger.error("Testing failed: %s", str(e), exc_info=True)
        print(f"\n✗ Testing failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
