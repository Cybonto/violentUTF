#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Encryption Validation CLI

Command-line interface for validating encryption status across all
database systems.

Issue #273: Phase 6.2 - Database Encryption and Security Enhancement

Usage:
    python3 validate_encryption.py --test-all-systems
    python3 validate_encryption.py --database postgres
    python3 validate_encryption.py --check-keys
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.security_enhancement.core.encryption_validator import EncryptionValidator  # noqa: E402


def main(argv: Optional[List[str]] = None) -> int:
    """Execute main CLI entry point."""
    parser = argparse.ArgumentParser(description="Validate encryption status across database systems")

    parser.add_argument(
        "--test-all-systems",
        action="store_true",
        help="Validate all database systems",
    )

    parser.add_argument(
        "--database",
        choices=["postgres", "sqlite", "all"],
        default="all",
        help="Target specific database",
    )

    parser.add_argument(
        "--check-keys",
        action="store_true",
        help="Validate encryption key management",
    )

    parser.add_argument(
        "--report-format",
        choices=["json", "yaml", "html"],
        default="json",
        help="Output report format",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Report output directory",
    )

    args = parser.parse_args(argv)

    validator = EncryptionValidator()

    if args.test_all_systems or args.database == "all":
        print("Generating comprehensive encryption validation report...")
        report = validator.generate_encryption_report()
    elif args.database == "postgres":
        print("Validating PostgreSQL encryption...")
        report = validator.validate_postgresql_encryption()
    elif args.database == "sqlite":
        print("Validating SQLite encryption...")
        report = validator.validate_sqlite_encryption()
    else:
        report = validator.generate_encryption_report()

    # Output report
    if args.report_format == "json":
        output = json.dumps(report, indent=2)
        print(output)

        if args.output_dir:
            output_path = Path(args.output_dir) / "encryption_validation_report.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output)
            print(f"\nReport saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
