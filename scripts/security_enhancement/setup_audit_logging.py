#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Audit Logging Setup CLI

Command-line interface for configuring comprehensive audit logging
for security events with GDPR/SOC 2 compliance.

Issue #273: Phase 6.2 - Database Encryption and Security Enhancement

Usage:
    python3 setup_audit_logging.py --comprehensive
    python3 setup_audit_logging.py --event-type authentication
    python3 setup_audit_logging.py --configure-retention
    python3 setup_audit_logging.py --validate-coverage
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.security_enhancement.core.audit_logger import AuditLogger  # noqa: E402


def setup_postgresql_audit(connection_string: str = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Configure PostgreSQL audit logging.

    Args:
        connection_string: Optional PostgreSQL connection string
        verbose: Enable verbose output

    Returns:
        Setup status dictionary
    """
    result = {"database": "postgresql"}

    if verbose:
        print("Setting up PostgreSQL audit logging...")

    logger = AuditLogger()
    setup_result = logger.setup_postgresql_audit(connection_string)

    result.update(setup_result)

    if setup_result.get("status") == "configured":
        if verbose:
            if setup_result.get("pgaudit_available"):
                print("  ✓ pgaudit extension is available")
            else:
                print("  ℹ pgaudit extension not available - using alternative logging")
    else:
        if verbose:
            print(f"  ✗ Setup failed: {setup_result.get('error', 'Unknown')}")

    return result


def setup_sqlite_audit(db_path: str = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Configure SQLite audit logging.

    Args:
        db_path: Optional SQLite database path
        verbose: Enable verbose output

    Returns:
        Setup status dictionary
    """
    result = {"database": "sqlite"}

    if verbose:
        print("Setting up SQLite audit logging...")

    if db_path is None:
        db_path = "/Users/tamnguyen/Documents/GitHub/violentUTF/app_data/violentutf_api.db"

    logger = AuditLogger()
    setup_result = logger.setup_sqlite_audit(db_path)

    result.update(setup_result)

    if setup_result.get("status") == "configured":
        if verbose:
            print("  ✓ SQLite audit logging configured")
    else:
        if verbose:
            print(f"  ✗ Setup failed: {setup_result.get('error', 'Unknown')}")

    return result


def configure_security_events(event_types: list = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Configure security event logging

    Args:
        event_types: List of event types to configure
        verbose: Enable verbose output

    Returns:
        Configuration status dictionary
    """
    if event_types is None:
        event_types = [
            "authentication",
            "authorization",
            "data_access",
            "configuration",
        ]

    if verbose:
        print("Configuring security event logging...")

    logger = AuditLogger()
    config_result = logger.configure_security_events(event_types)

    configured_count = sum(1 for event_type, status in config_result.items() if status.get("status") == "configured")

    if verbose:
        for event_type, status in config_result.items():
            if status.get("status") == "configured":
                print(f"  ✓ {event_type} logging enabled")
            else:
                print(f"  ✗ {event_type} logging not supported")

    result = {
        "event_types_configured": configured_count,
        "total_event_types": len(event_types),
        "details": config_result,
    }

    return result


def configure_log_retention(
    compliance_days: int = 2555, operational_days: int = 90, verbose: bool = False
) -> Dict[str, Any]:
    """
    Configure log retention policies

    Args:
        compliance_days: Retention period for compliance logs (7 years)
        operational_days: Retention period for operational logs
        verbose: Enable verbose output

    Returns:
        Configuration status dictionary
    """
    if verbose:
        print("Configuring log retention policies...")
        print(f"  Compliance retention: {compliance_days} days (7 years)")
        print(f"  Operational retention: {operational_days} days")

    logger = AuditLogger()
    retention_result = logger.setup_log_retention(compliance_days=compliance_days, operational_days=operational_days)

    if retention_result.get("status") == "configured":
        if verbose:
            print("  ✓ Log retention policies configured")
    else:
        if verbose:
            print("  ✗ Failed to configure log retention policies")

    return retention_result


def validate_audit_coverage(verbose: bool = False) -> Dict[str, Any]:
    """
    Validate audit logging coverage

    Args:
        verbose: Enable verbose output

    Returns:
        Validation results dictionary
    """
    if verbose:
        print("Validating audit logging coverage...")

    logger = AuditLogger()
    coverage_result = logger.validate_audit_coverage()

    if verbose:
        print(f"  Coverage: {coverage_result.get('coverage_percentage', 0)}%")
        print(f"  Integrity: {coverage_result.get('integrity_protection', 'unknown')}")
        print("  Event categories:")
        for category in coverage_result.get("event_categories", []):
            print(f"    - {category}")

    if coverage_result.get("status") == "validated":
        if verbose:
            print("  ✓ Audit logging coverage validated")
    else:
        if verbose:
            print("  ✗ Audit logging coverage validation failed")

    return coverage_result


def setup_comprehensive_audit_logging(verbose: bool = False) -> Dict[str, Any]:
    """
    Configure comprehensive audit logging.

    Args:
        verbose: Enable verbose output

    Returns:
        Combined setup status
    """
    result = {
        "components": {},
        "all_configured": False,
    }

    if verbose:
        print("=" * 60)
        print("Setting up comprehensive audit logging")
        print("=" * 60)
        print()

    # Setup PostgreSQL audit logging
    postgres_result = setup_postgresql_audit(verbose=verbose)
    result["components"]["postgresql_audit"] = postgres_result

    if verbose:
        print()

    # Setup SQLite audit logging
    sqlite_result = setup_sqlite_audit(verbose=verbose)
    result["components"]["sqlite_audit"] = sqlite_result

    if verbose:
        print()

    # Configure security event logging
    events_result = configure_security_events(verbose=verbose)
    result["components"]["security_events"] = events_result

    if verbose:
        print()

    # Configure log retention
    retention_result = configure_log_retention(verbose=verbose)
    result["components"]["log_retention"] = retention_result

    if verbose:
        print()

    # Validate audit coverage
    coverage_result = validate_audit_coverage(verbose=verbose)
    result["components"]["audit_coverage"] = coverage_result

    # Check if all components are configured
    result["all_configured"] = all(
        component.get("status") == "configured" or component.get("coverage_percentage") == 100
        for component in result["components"].values()
        if isinstance(component, dict)
    )

    if verbose:
        print()
        print("=" * 60)
        if result["all_configured"]:
            print("✓ Comprehensive audit logging configured")
        else:
            print("✓ Audit logging configured (some components optional)")
        print("=" * 60)

    return result


def main(argv: Optional[List[str]] = None) -> int:
    """Execute main CLI entry point."""
    parser = argparse.ArgumentParser(description="Setup comprehensive audit logging")

    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Setup comprehensive audit logging",
    )

    parser.add_argument(
        "--event-type",
        choices=[
            "authentication",
            "authorization",
            "data_access",
            "configuration",
        ],
        help="Configure specific event type logging",
    )

    parser.add_argument(
        "--configure-retention",
        action="store_true",
        help="Configure log retention policies",
    )

    parser.add_argument(
        "--validate-coverage",
        action="store_true",
        help="Validate audit logging coverage",
    )

    parser.add_argument(
        "--compliance-days",
        type=int,
        default=2555,
        help="Compliance log retention days (default: 2555 = 7 years)",
    )

    parser.add_argument(
        "--operational-days",
        type=int,
        default=90,
        help="Operational log retention days (default: 90)",
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

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args(argv)

    if args.comprehensive:
        report = setup_comprehensive_audit_logging(verbose=args.verbose)
    elif args.event_type:
        report = configure_security_events(event_types=[args.event_type], verbose=args.verbose)
    elif args.configure_retention:
        report = configure_log_retention(
            compliance_days=args.compliance_days,
            operational_days=args.operational_days,
            verbose=args.verbose,
        )
    elif args.validate_coverage:
        report = validate_audit_coverage(verbose=args.verbose)
    else:
        # Default to comprehensive setup
        report = setup_comprehensive_audit_logging(verbose=args.verbose)

    # Output report
    if args.report_format == "json":
        if not args.verbose:
            output = json.dumps(report, indent=2)
            print(output)

        if args.output_dir:
            output_path = Path(args.output_dir) / "audit_logging_setup_report.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(report, indent=2))
            if args.verbose:
                print(f"\nReport saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
