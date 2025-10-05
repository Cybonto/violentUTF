#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""DuckDB Inventory Analyzer for ViolentUTF Migration.

Issue: #322 - Phase 4.3.1: DuckDB Data Inventory and Backup Strategy

This script performs comprehensive analysis of DuckDB files:
- Scans app_data directories recursively
- Extracts file metadata and user hash from filenames
- Inspects DuckDB schema (tables, row counts, columns)
- Generates detailed JSON inventory report

Usage:
    python3 analyze_duckdb_inventory.py --comprehensive
    python3 analyze_duckdb_inventory.py --scan-only
    python3 analyze_duckdb_inventory.py --verbose
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb library not found. Install with: pip install duckdb")
    sys.exit(1)

# Configure logging
LOG_FILE = "logs/inventory_analysis.log"
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


class DuckDBInventoryAnalyzer:
    """Analyzer for DuckDB files inventory and metadata extraction."""

    # Directories to scan for DuckDB files
    SCAN_DIRECTORIES = [
        "app_data/violentutf/",
        "violentutf/app_data/violentutf/",
    ]

    # Pattern for PyRIT memory database files
    PYRIT_MEMORY_PATTERN = re.compile(r"pyrit_memory_([a-f0-9]+)\.db$")

    def __init__(self, base_path: str = ".", verbose: bool = False) -> None:
        """Initialize the analyzer.

        Args:
            base_path: Base directory for scanning (default: current directory)
            verbose: Enable verbose logging
        """
        self.base_path = Path(base_path).resolve()
        self.verbose = verbose
        if verbose:
            logger.setLevel(logging.DEBUG)

        logger.info("Initialized DuckDB Inventory Analyzer at %s", self.base_path)

    def scan_for_duckdb_files(self) -> List[Path]:
        """Scan configured directories for DuckDB files.

        Returns:
            List of Path objects for found DuckDB files
        """
        found_files: List[Path] = []

        for scan_dir in self.SCAN_DIRECTORIES:
            full_path = self.base_path / scan_dir
            if not full_path.exists():
                logger.warning("Directory does not exist: %s", full_path)
                continue

            logger.info("Scanning directory: %s", full_path)

            # Recursively find all .db files
            for db_file in full_path.rglob("*.db"):
                if db_file.is_file():
                    found_files.append(db_file)
                    logger.debug("Found DuckDB file: %s", db_file)

        logger.info("Total DuckDB files found: %d", len(found_files))
        return found_files

    def extract_user_hash(self, filename: str) -> Optional[str]:
        """Extract user hash from PyRIT memory filename.

        Args:
            filename: The database filename

        Returns:
            User hash if pattern matches, None otherwise
        """
        match = self.PYRIT_MEMORY_PATTERN.search(filename)
        if match:
            return match.group(1)
        return None

    def get_file_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from a file.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with file metadata
        """
        stat = file_path.stat()
        return {
            "path": str(file_path),
            "filename": file_path.name,
            "size_bytes": stat.st_size,
            "modified_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "user_hash": self.extract_user_hash(file_path.name),
        }

    def inspect_duckdb_schema(self, file_path: Path) -> Dict[str, Any]:
        """Inspect DuckDB file schema and extract table information.

        Args:
            file_path: Path to DuckDB file

        Returns:
            Dictionary with schema information
        """
        schema_info: Dict[str, Any] = {
            "tables": [],
            "row_counts": {},
            "columns": {},
            "error": None,
        }

        try:
            # Connect to DuckDB file (read-only)
            conn = duckdb.connect(str(file_path), read_only=True)

            # Get list of tables
            tables_result = conn.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
            ).fetchall()

            tables = [row[0] for row in tables_result]
            schema_info["tables"] = tables

            # Get row counts and column information for each table
            for table in tables:
                try:
                    # Get row count (table name from schema, not user input)
                    count_result = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # nosec B608
                    schema_info["row_counts"][table] = count_result[0] if count_result else 0

                    # Get column information
                    columns_result = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
                    schema_info["columns"][table] = [{"name": col[1], "type": col[2]} for col in columns_result]

                except Exception as table_error:
                    logger.warning("Error analyzing table %s in %s: %s", table, file_path, table_error)
                    schema_info["row_counts"][table] = None
                    schema_info["columns"][table] = []

            conn.close()
            logger.debug("Successfully inspected schema for %s", file_path)

        except Exception as e:
            error_msg = f"Error inspecting DuckDB file {file_path}: {str(e)}"
            logger.error(error_msg)
            schema_info["error"] = str(e)

        return schema_info

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Perform comprehensive analysis on a single DuckDB file.

        Args:
            file_path: Path to the DuckDB file

        Returns:
            Complete analysis dictionary
        """
        logger.info("Analyzing file: %s", file_path)

        analysis = self.get_file_metadata(file_path)
        analysis["schema"] = self.inspect_duckdb_schema(file_path)

        return analysis

    def generate_directory_summary(self, file_analyses: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Generate summary statistics by directory.

        Args:
            file_analyses: List of file analysis dictionaries

        Returns:
            Directory summary with counts and sizes
        """
        summary: Dict[str, Dict[str, Any]] = {}

        for analysis in file_analyses:
            file_path = Path(analysis["path"])

            # Determine which scan directory this file belongs to
            for scan_dir in self.SCAN_DIRECTORIES:
                full_scan_path = self.base_path / scan_dir
                try:
                    file_path.relative_to(full_scan_path)
                    # File is within this scan directory
                    if scan_dir not in summary:
                        summary[scan_dir] = {"count": 0, "size_bytes": 0, "files": []}

                    summary[scan_dir]["count"] += 1
                    summary[scan_dir]["size_bytes"] += analysis["size_bytes"]
                    summary[scan_dir]["files"].append(analysis["filename"])
                    break
                except ValueError:
                    # File not in this directory, continue checking
                    continue

        return summary

    def generate_inventory_report(self, comprehensive: bool = True) -> Dict[str, Any]:
        """Generate complete inventory report.

        Args:
            comprehensive: If True, include full schema analysis

        Returns:
            Complete inventory report as dictionary
        """
        logger.info("Starting inventory report generation")

        # Scan for all DuckDB files
        duckdb_files = self.scan_for_duckdb_files()

        # Analyze each file
        file_analyses = []
        for db_file in duckdb_files:
            if comprehensive:
                analysis = self.analyze_file(db_file)
            else:
                analysis = self.get_file_metadata(db_file)
                analysis["schema"] = None

            file_analyses.append(analysis)

        # Calculate totals
        total_size = sum(f["size_bytes"] for f in file_analyses)

        # Generate directory summary
        directory_summary = self.generate_directory_summary(file_analyses)

        # Build final report
        report = {
            "scan_timestamp": datetime.now().isoformat(),
            "base_path": str(self.base_path),
            "comprehensive_analysis": comprehensive,
            "total_files": len(file_analyses),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "files": file_analyses,
            "directory_summary": directory_summary,
        }

        logger.info("Inventory report generated: %d files analyzed", len(file_analyses))
        return report

    def save_report(self, report: Dict[str, Any], output_path: str) -> None:
        """Save inventory report to JSON file.

        Args:
            report: The inventory report dictionary
            output_path: Path to save the JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("Report saved to: %s", output_file)
        print(f"\n✓ Inventory report saved: {output_file}")


def main() -> int:
    """Run DuckDB inventory analysis.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description="Analyze DuckDB files inventory for ViolentUTF migration")
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Perform comprehensive schema analysis (default: True)",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan for files, skip schema analysis",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/duckdb_inventory.json",
        help="Output JSON file path (default: reports/duckdb_inventory.json)",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        default=".",
        help="Base directory for scanning (default: current directory)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    try:
        # Initialize analyzer
        analyzer = DuckDBInventoryAnalyzer(base_path=args.base_path, verbose=args.verbose)

        # Determine analysis mode
        comprehensive = not args.scan_only
        if args.comprehensive:
            comprehensive = True

        # Generate report
        print("\nDuckDB Inventory Analysis")
        print("=" * 50)
        print(f"Base Path: {analyzer.base_path}")
        print(f"Mode: {'Comprehensive' if comprehensive else 'Scan Only'}")
        print(f"Output: {args.output}")
        print("=" * 50 + "\n")

        report = analyzer.generate_inventory_report(comprehensive=comprehensive)

        # Display summary
        print("\nInventory Summary")
        print("-" * 50)
        print(f"Total Files: {report['total_files']}")
        print(f"Total Size: {report['total_size_mb']} MB")
        print("\nBy Directory:")
        for directory, summary in report["directory_summary"].items():
            size_mb = round(summary["size_bytes"] / (1024 * 1024), 2)
            print(f"  {directory}: {summary['count']} files, {size_mb} MB")
        print("-" * 50)

        # Save report
        analyzer.save_report(report, args.output)

        print("\n✓ Analysis completed successfully")
        return 0

    except Exception as e:
        logger.error("Analysis failed: %s", str(e), exc_info=True)
        print(f"\n✗ Analysis failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
