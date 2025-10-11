#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Validate Change Management Procedures.

Validates change management workflows, approval processes, and rollback procedures.

Usage:
    python3 validate_change_procedures.py --test-workflows
    python3 validate_change_procedures.py --test-workflows --config-dir /path/to/config
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def test_workflows(config_dir: Path = None) -> Dict[str, Any]:
    """
    Test change management workflows.

    Args:
        config_dir: Configuration directory

    Returns:
        Validation results
    """
    if config_dir is None:
        config_dir = Path("workflows/change-approval")

    config_dir = Path(config_dir)

    validation_results: Dict[str, Any] = {
        "overall_status": "pass",
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "test_details": [],
    }

    # Test 1: Validate approval workflow
    approval_result = validate_approval_workflow(config_dir)
    validation_results["tests_run"] += 1
    if approval_result["valid"]:
        validation_results["tests_passed"] += 1
    else:
        validation_results["tests_failed"] += 1
        validation_results["overall_status"] = "fail"

    validation_results["test_details"].append(
        {
            "test_name": "Approval Workflow Validation",
            "status": "pass" if approval_result["valid"] else "fail",
            "details": approval_result,
        }
    )

    # Test 2: Validate stakeholder registry
    stakeholder_result = _validate_stakeholder_registry(config_dir)
    validation_results["tests_run"] += 1
    if stakeholder_result["valid"]:
        validation_results["tests_passed"] += 1
    else:
        validation_results["tests_failed"] += 1
        validation_results["overall_status"] = "fail"

    validation_results["test_details"].append(
        {
            "test_name": "Stakeholder Registry Validation",
            "status": "pass" if stakeholder_result["valid"] else "fail",
            "details": stakeholder_result,
        }
    )

    # Test 3: Validate maintenance windows
    maintenance_result = _validate_maintenance_windows(config_dir)
    validation_results["tests_run"] += 1
    if maintenance_result["valid"]:
        validation_results["tests_passed"] += 1
    else:
        validation_results["tests_failed"] += 1
        validation_results["overall_status"] = "fail"

    validation_results["test_details"].append(
        {
            "test_name": "Maintenance Windows Validation",
            "status": "pass" if maintenance_result["valid"] else "fail",
            "details": maintenance_result,
        }
    )

    return validation_results


def validate_approval_workflow(config_dir: Path) -> Dict[str, Any]:
    """
    Validate approval workflow configuration.

    Args:
        config_dir: Configuration directory

    Returns:
        Validation result
    """
    approval_matrix_path = config_dir / "approval_matrix.yml"

    if not approval_matrix_path.exists():
        return {
            "valid": False,
            "error": "approval_matrix.yml not found",
        }

    try:
        with open(approval_matrix_path, "r", encoding="utf-8") as f:
            approval_matrix = yaml.safe_load(f)

        # Validate required change types
        required_types = ["emergency", "standard", "normal", "major"]
        missing_types = [t for t in required_types if t not in approval_matrix]

        if missing_types:
            return {
                "valid": False,
                "error": f"Missing change types: {missing_types}",
            }

        # Validate each change type has required fields
        for change_type, config in approval_matrix.items():
            required_fields = ["approvers_required", "notification"]
            missing_fields = [f for f in required_fields if f not in config]

            if missing_fields:
                return {
                    "valid": False,
                    "error": (f"Change type '{change_type}' missing fields: {missing_fields}"),
                }

        return {
            "valid": True,
            "change_types_configured": len(approval_matrix),
        }

    except Exception as e:
        return {"valid": False, "error": f"Error loading approval matrix: {str(e)}"}


def _validate_stakeholder_registry(config_dir: Path) -> Dict[str, Any]:
    """Validate stakeholder registry."""
    stakeholder_path = config_dir / "stakeholder_registry.yml"

    if not stakeholder_path.exists():
        return {
            "valid": False,
            "error": "stakeholder_registry.yml not found",
        }

    try:
        with open(stakeholder_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f)

        # Validate required stakeholder groups
        required_groups = ["dba_team", "oncall", "management"]
        missing_groups = [g for g in required_groups if g not in registry]

        if missing_groups:
            return {
                "valid": False,
                "error": f"Missing stakeholder groups: {missing_groups}",
            }

        # Validate each group has contacts
        for group, contacts in registry.items():
            if not isinstance(contacts, list) or len(contacts) == 0:
                return {
                    "valid": False,
                    "error": f"Group '{group}' has no contacts",
                }

        return {
            "valid": True,
            "stakeholder_groups": len(registry),
        }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Error loading stakeholder registry: {str(e)}",
        }


def _validate_maintenance_windows(config_dir: Path) -> Dict[str, Any]:
    """Validate maintenance windows."""
    maintenance_path = config_dir / "maintenance_windows.yml"

    if not maintenance_path.exists():
        return {
            "valid": False,
            "error": "maintenance_windows.yml not found",
        }

    try:
        with open(maintenance_path, "r", encoding="utf-8") as f:
            maintenance_data = yaml.safe_load(f)

        if "windows" not in maintenance_data:
            return {
                "valid": False,
                "error": "No maintenance windows defined",
            }

        windows = maintenance_data["windows"]
        if not windows or len(windows) == 0:
            return {
                "valid": False,
                "error": "No maintenance windows configured",
            }

        # Validate each window has required fields
        for window in windows:
            required_fields = ["id", "name", "schedule"]
            missing_fields = [f for f in required_fields if f not in window]

            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Maintenance window missing fields: {missing_fields}",
                }

        return {
            "valid": True,
            "maintenance_windows": len(windows),
        }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Error loading maintenance windows: {str(e)}",
        }


def validate_rollback_procedures(
    database_type: str = "sqlite",
    database_path: Optional[str] = None,
    backup_location: Path = None,
) -> Dict[str, Any]:
    """
    Validate rollback procedures.

    Args:
        database_type: Type of database
        database_path: Path to database (for SQLite)
        backup_location: Backup storage location

    Returns:
        Validation result
    """
    if backup_location is None:
        import tempfile

        backup_location = Path(tempfile.mkdtemp(prefix="rollback_validation_"))

    backup_location = Path(backup_location)
    backup_location.mkdir(parents=True, exist_ok=True)

    try:
        if database_type == "sqlite":
            from scripts.change_management.rollback.sqlite_rollback import (
                SQLiteRollbackManager,
            )

            SQLiteRollbackManager(backup_location=backup_location)

            return {
                "valid": True,
                "message": "SQLite rollback manager initialized successfully",
            }

        elif database_type == "postgresql":
            from scripts.change_management.rollback.postgresql_rollback import (
                PostgreSQLRollbackManager,
            )

            PostgreSQLRollbackManager(backup_location=backup_location)

            return {
                "valid": True,
                "message": "PostgreSQL rollback manager initialized successfully",
            }

        else:
            return {
                "valid": False,
                "error": f"Unsupported database type: {database_type}",
            }

    except Exception as e:
        return {
            "valid": False,
            "error": f"Error validating rollback procedures: {str(e)}",
        }


def validate_incident_response(runbook_dir: Path = None) -> Dict[str, Any]:
    """
    Validate incident response procedures.

    Args:
        runbook_dir: Directory containing runbooks

    Returns:
        Validation result
    """
    if runbook_dir is None:
        runbook_dir = Path("docs/runbooks")

    runbook_dir = Path(runbook_dir)

    if not runbook_dir.exists():
        return {
            "valid": False,
            "error": f"Runbook directory not found: {runbook_dir}",
        }

    runbook_files = list(runbook_dir.glob("*.yml"))

    if len(runbook_files) == 0:
        return {
            "valid": False,
            "error": "No runbooks found",
        }

    # Validate required runbooks exist
    required_runbooks = [
        "data_integrity_incident.yml",
        "security_incident_database.yml",
        "performance_degradation.yml",
    ]

    missing_runbooks = []
    for required in required_runbooks:
        if not (runbook_dir / required).exists():
            missing_runbooks.append(required)

    if missing_runbooks:
        return {
            "valid": False,
            "error": f"Missing required runbooks: {missing_runbooks}",
        }

    return {
        "valid": True,
        "runbooks_found": len(runbook_files),
    }


def parse_arguments(args: Optional[list] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Validate change management procedures")
    parser.add_argument(
        "--test-workflows",
        action="store_true",
        help="Test change management workflows",
    )
    parser.add_argument(
        "--config-dir",
        type=str,
        default="workflows/change-approval",
        help="Configuration directory",
    )
    parser.add_argument(
        "--validate-rollback",
        action="store_true",
        help="Validate rollback procedures",
    )
    parser.add_argument(
        "--database-type",
        type=str,
        choices=["postgresql", "sqlite"],
        default="sqlite",
        help="Database type for rollback validation",
    )
    parser.add_argument(
        "--validate-incident-response",
        action="store_true",
        help="Validate incident response procedures",
    )
    parser.add_argument(
        "--runbook-dir",
        type=str,
        default="docs/runbooks",
        help="Runbook directory",
    )

    return parser.parse_args(args)


def main() -> int:
    """Execute main program logic."""
    args = parse_arguments()

    exit_code = 0

    if args.test_workflows:
        print("Testing change management workflows...")
        results = test_workflows(config_dir=Path(args.config_dir))

        print("\nWorkflow Validation Results:")
        print(f"  Status: {results['overall_status'].upper()}")
        print(f"  Tests Run: {results['tests_run']}")
        print(f"  Tests Passed: {results['tests_passed']}")
        print(f"  Tests Failed: {results['tests_failed']}")
        print("\nTest Details:")

        for test in results["test_details"]:
            status_symbol = "✓" if test["status"] == "pass" else "✗"
            print(f"  {status_symbol} {test['test_name']}: {test['status'].upper()}")

        if results["overall_status"] != "pass":
            exit_code = 1

    if args.validate_rollback:
        print(f"\nValidating {args.database_type} rollback procedures...")
        result = validate_rollback_procedures(database_type=args.database_type)

        if result["valid"]:
            print(f"  ✓ {result['message']}")
        else:
            print(f"  ✗ {result['error']}")
            exit_code = 1

    if args.validate_incident_response:
        print("\nValidating incident response procedures...")
        result = validate_incident_response(runbook_dir=Path(args.runbook_dir))

        if result["valid"]:
            print(f"  ✓ Found {result['runbooks_found']} runbooks")
        else:
            print(f"  ✗ {result['error']}")
            exit_code = 1

    if not (args.test_workflows or args.validate_rollback or args.validate_incident_response):
        print("No validation action specified.")
        print("Use --test-workflows, --validate-rollback, or --validate-incident-response")
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
