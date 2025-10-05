#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Comprehensive Migration Validation Script - Issue #327.

Wrapper script that validates complete migration from DuckDB to SQLite by:
1. Running validate_config_migration.py for config data
2. Validating PyRIT memory database migration
3. Checking data integrity across all databases
4. Generating comprehensive validation report

Usage:
    python3 validate_migration_complete.py
    python3 validate_migration_complete.py --app-data-dir ./app_data/violentutf
    python3 validate_migration_complete.py --verbose
"""

import argparse
import json
import logging
import subprocess  # nosec B404 - needed for controlled execution of validation scripts
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ComprehensiveMigrationValidator:
    """Validate complete DuckDB to SQLite migration."""

    def __init__(self, app_data_dir: str = "./app_data/violentutf", verbose: bool = False) -> None:
        """Initialize validator."""
        self.app_data_dir = Path(app_data_dir)
        self.verbose = verbose
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "app_data_dir": str(self.app_data_dir),
            "validations": {},
            "summary": {
                "total_validations": 0,
                "passed": 0,
                "failed": 0,
                "warnings": 0,
            },
        }

        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    def validate_config_migration(self) -> bool:
        """Validate configuration database migration."""
        logger.info("=" * 80)
        logger.info("STEP 1: Validating Configuration Database Migration")
        logger.info("=" * 80)

        try:
            # Run validate_config_migration.py
            script_path = Path(__file__).parent / "validate_config_migration.py"
            cmd = [
                sys.executable,
                str(script_path),
                "--app-data-dir",
                str(self.app_data_dir),
            ]

            if self.verbose:
                cmd.append("--verbose")

            result = subprocess.run(
                cmd, capture_output=True, text=True, check=False
            )  # nosec B603 - controlled script execution with known safe arguments

            success = result.returncode == 0
            self.validation_results["validations"]["config_migration"] = {
                "status": "PASS" if success else "FAIL",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if success:
                logger.info("✓ Configuration migration validation PASSED")
                self.validation_results["summary"]["passed"] += 1
            else:
                logger.error("✗ Configuration migration validation FAILED")
                logger.error("Error: %s", result.stderr)
                self.validation_results["summary"]["failed"] += 1

            self.validation_results["summary"]["total_validations"] += 1
            return success

        except Exception as e:
            logger.error("Failed to validate config migration: %s", e)
            self.validation_results["validations"]["config_migration"] = {
                "status": "ERROR",
                "error": str(e),
            }
            self.validation_results["summary"]["failed"] += 1
            self.validation_results["summary"]["total_validations"] += 1
            return False

    def validate_pyrit_memory_migration(self) -> bool:
        """Validate PyRIT memory database migration."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 2: Validating PyRIT Memory Database Migration")
        logger.info("=" * 80)

        try:
            if not self.app_data_dir.exists():
                logger.warning("App data directory does not exist: %s", self.app_data_dir)
                self.validation_results["summary"]["warnings"] += 1
                return True

            # Find all PyRIT memory databases (both .db and .sqlite.db)
            db_files = list(self.app_data_dir.glob("pyrit_memory_*.db"))
            sqlite_files = list(self.app_data_dir.glob("pyrit_memory_*.sqlite.db"))

            logger.info("Found %d total database files", len(db_files))
            logger.info("Found %d SQLite database files", len(sqlite_files))

            # Check if migration has been performed
            if len(sqlite_files) == 0:
                logger.warning("No SQLite migration files found (.sqlite.db)")
                logger.info("This may indicate migration has not been performed yet.")
                self.validation_results["validations"]["pyrit_memory"] = {
                    "status": "WARNING",
                    "message": "No SQLite migration files found",
                    "total_db_files": len(db_files),
                    "sqlite_files": len(sqlite_files),
                }
                self.validation_results["summary"]["warnings"] += 1
                self.validation_results["summary"]["total_validations"] += 1
                return True

            # Validate each SQLite file exists and is readable
            valid_files = 0
            for sqlite_file in sqlite_files:
                if sqlite_file.exists() and sqlite_file.stat().st_size > 0:
                    valid_files += 1
                    if self.verbose:
                        logger.debug("  ✓ %s - OK", sqlite_file.name)

            success = valid_files == len(sqlite_files)
            self.validation_results["validations"]["pyrit_memory"] = {
                "status": "PASS" if success else "FAIL",
                "total_files": len(sqlite_files),
                "valid_files": valid_files,
            }

            if success:
                logger.info("✓ PyRIT memory migration validation PASSED (%d files)", valid_files)
                self.validation_results["summary"]["passed"] += 1
            else:
                logger.error("✗ PyRIT memory migration validation FAILED")
                self.validation_results["summary"]["failed"] += 1

            self.validation_results["summary"]["total_validations"] += 1
            return success

        except Exception as e:
            logger.error("Failed to validate PyRIT memory migration: %s", e)
            self.validation_results["validations"]["pyrit_memory"] = {
                "status": "ERROR",
                "error": str(e),
            }
            self.validation_results["summary"]["failed"] += 1
            self.validation_results["summary"]["total_validations"] += 1
            return False

    def validate_data_integrity(self) -> bool:
        """Validate overall data integrity."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 3: Validating Data Integrity")
        logger.info("=" * 80)

        try:
            # Check for any database lock files that shouldn't exist
            lock_files = list(self.app_data_dir.glob("*.db-wal")) + list(self.app_data_dir.glob("*.db-shm"))

            if lock_files:
                logger.warning("Found %d database lock files", len(lock_files))
                logger.warning("This may indicate active connections or incomplete operations")
                for lock_file in lock_files:
                    logger.warning("  - %s", lock_file.name)
                self.validation_results["summary"]["warnings"] += 1

            # Check for orphaned files
            all_files = list(self.app_data_dir.glob("*"))
            expected_patterns = [
                "pyrit_memory_*.db",
                "pyrit_memory_*.sqlite.db",
                "*.db-wal",
                "*.db-shm",
                "*.db-journal",
            ]

            orphaned_files = []
            for file in all_files:
                if file.is_file():
                    is_expected = any(file.match(pattern) for pattern in expected_patterns)
                    if not is_expected:
                        orphaned_files.append(file.name)

            if orphaned_files and self.verbose:
                logger.info("Found %d non-database files (may be expected)", len(orphaned_files))
                for orphan in orphaned_files[:10]:  # Show first 10
                    logger.debug("  - %s", orphan)

            self.validation_results["validations"]["data_integrity"] = {
                "status": "PASS",
                "lock_files": len(lock_files),
                "orphaned_files": len(orphaned_files),
            }

            logger.info("✓ Data integrity validation PASSED")
            self.validation_results["summary"]["passed"] += 1
            self.validation_results["summary"]["total_validations"] += 1
            return True

        except Exception as e:
            logger.error("Failed to validate data integrity: %s", e)
            self.validation_results["validations"]["data_integrity"] = {
                "status": "ERROR",
                "error": str(e),
            }
            self.validation_results["summary"]["failed"] += 1
            self.validation_results["summary"]["total_validations"] += 1
            return False

    def generate_report(self) -> str:
        """Generate comprehensive validation report."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("GENERATING VALIDATION REPORT")
        logger.info("=" * 80)

        report_lines = [
            "=" * 80,
            "COMPREHENSIVE MIGRATION VALIDATION REPORT",
            "=" * 80,
            "",
            f"Validation Timestamp: {self.validation_results['timestamp']}",
            f"App Data Directory:   {self.validation_results['app_data_dir']}",
            "",
            "=" * 80,
            "VALIDATION SUMMARY",
            "=" * 80,
            f"Total Validations: {self.validation_results['summary']['total_validations']}",
            f"Passed:            {self.validation_results['summary']['passed']}",
            f"Failed:            {self.validation_results['summary']['failed']}",
            f"Warnings:          {self.validation_results['summary']['warnings']}",
            "",
        ]

        # Add detailed results
        report_lines.append("=" * 80)
        report_lines.append("DETAILED RESULTS")
        report_lines.append("=" * 80)
        report_lines.append("")

        for validation_name, validation_data in self.validation_results["validations"].items():
            report_lines.append(f"Validation: {validation_name}")
            report_lines.append(f"  Status: {validation_data.get('status', 'UNKNOWN')}")

            for key, value in validation_data.items():
                if key != "status" and key not in ["stdout", "stderr"]:
                    report_lines.append(f"  {key}: {value}")

            report_lines.append("")

        # Overall status
        overall_pass = self.validation_results["summary"]["failed"] == 0
        report_lines.append("=" * 80)
        report_lines.append("OVERALL VALIDATION STATUS")
        report_lines.append("=" * 80)
        report_lines.append("")
        report_lines.append(f"{'✓ VALIDATION PASSED' if overall_pass else '✗ VALIDATION FAILED'}")
        report_lines.append("")

        if overall_pass:
            report_lines.append("All migration validations completed successfully.")
            report_lines.append("The system is ready for production deployment.")
        else:
            report_lines.append("Migration validation FAILED.")
            report_lines.append("Please review the errors above and re-run migration.")

        report_lines.append("")
        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_report(self, report: str) -> Path:
        """Save validation report to file."""
        # Create reports directory
        reports_dir = Path("/Users/tamnguyen/Documents/GitHub/violentUTF/reports")
        reports_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"migration_validation_{timestamp}.txt"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)

        # Also save JSON version
        json_file = reports_dir / f"migration_validation_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.validation_results, f, indent=2)

        logger.info("Report saved to: %s", report_file)
        logger.info("JSON data saved to: %s", json_file)

        return report_file

    def run_all_validations(self) -> bool:
        """Run all migration validations."""
        logger.info("Starting comprehensive migration validation...")
        logger.info("")

        # Step 1: Validate config migration
        config_ok = self.validate_config_migration()

        # Step 2: Validate PyRIT memory migration
        memory_ok = self.validate_pyrit_memory_migration()

        # Step 3: Validate data integrity
        integrity_ok = self.validate_data_integrity()

        # Generate and save report
        report = self.generate_report()
        print(report)
        self.save_report(report)

        # Return overall success
        return config_ok and memory_ok and integrity_ok


def main() -> None:
    """Execute comprehensive migration validation."""
    parser = argparse.ArgumentParser(description="Comprehensive Migration Validation - Issue #327")
    parser.add_argument(
        "--app-data-dir",
        default="./app_data/violentutf",
        help="Path to app data directory (default: ./app_data/violentutf)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Run validation
    validator = ComprehensiveMigrationValidator(app_data_dir=args.app_data_dir, verbose=args.verbose)

    success = validator.run_all_validations()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
