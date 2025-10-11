#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Create Incident Response Runbooks.

Creates comprehensive incident response runbooks in YAML format.

Usage:
    python3 create_incident_runbooks.py --comprehensive
    python3 create_incident_runbooks.py --comprehensive --output-dir /path/to/runbooks
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

RUNBOOK_TEMPLATES = {
    "data_integrity_incident": {
        "title": "Data Integrity Incident Response",
        "database_type": "all",
        "severity": "high",
        "rto_target": 60,
        "rpo_target": 120,
        "detection": {
            "symptoms": [
                "Data corruption detected",
                "Referential integrity violations",
                "Unexpected NULL values in required fields",
                "Data inconsistency across related tables",
            ],
            "monitoring_commands": [
                "SELECT COUNT(*) FROM table WHERE expected_field IS NULL",
                "PRAGMA integrity_check (SQLite)",
                "SELECT * FROM pg_stat_database (PostgreSQL)",
            ],
        },
        "recovery_steps": [
            {
                "step_number": 1,
                "title": "Identify scope of corruption",
                "commands": ["Run integrity checks", "Compare with backups"],
                "estimated_time_minutes": 10,
            },
            {
                "step_number": 2,
                "title": "Isolate affected data",
                "commands": ["Mark corrupted records", "Prevent further corruption"],
                "estimated_time_minutes": 5,
            },
            {
                "step_number": 3,
                "title": "Restore from backup",
                "commands": ["python3 implement_rollback_procedures.py --test-automation"],
                "estimated_time_minutes": 30,
            },
            {
                "step_number": 4,
                "title": "Validate data integrity",
                "commands": ["Run integrity checks", "Verify data consistency"],
                "estimated_time_minutes": 15,
            },
        ],
        "escalation": {
            "immediate": ["dba_team", "data_team"],
            "after_30_min": ["tech_lead", "management"],
        },
    },
    "security_incident_database": {
        "title": "Database Security Incident Response",
        "database_type": "all",
        "severity": "critical",
        "rto_target": 15,
        "rpo_target": 60,
        "detection": {
            "symptoms": [
                "Unauthorized access detected",
                "Multiple failed authentication attempts",
                "Suspicious SQL queries",
                "Unusual data access patterns",
            ],
            "monitoring_commands": [
                "Review authentication logs",
                "Check active connections",
                "Audit query logs",
            ],
        },
        "recovery_steps": [
            {
                "step_number": 1,
                "title": "Contain the incident",
                "commands": [
                    "Terminate suspicious connections",
                    "Disable compromised accounts",
                ],
                "estimated_time_minutes": 5,
            },
            {
                "step_number": 2,
                "title": "Assess impact",
                "commands": [
                    "Review audit logs",
                    "Identify accessed/modified data",
                ],
                "estimated_time_minutes": 10,
            },
            {
                "step_number": 3,
                "title": "Preserve evidence",
                "commands": ["Backup logs", "Document timeline"],
                "estimated_time_minutes": 10,
            },
            {
                "step_number": 4,
                "title": "Restore security",
                "commands": [
                    "Reset credentials",
                    "Apply security patches",
                    "Review access controls",
                ],
                "estimated_time_minutes": 20,
            },
        ],
        "escalation": {
            "immediate": ["oncall", "security_team", "management"],
            "notify": ["legal", "compliance"],
        },
    },
    "configuration_incident": {
        "title": "Configuration Error Incident Response",
        "database_type": "all",
        "severity": "medium",
        "rto_target": 240,
        "rpo_target": 480,
        "detection": {
            "symptoms": [
                "Configuration mismatch detected",
                "Service startup failures",
                "Invalid connection parameters",
                "Performance degradation after config change",
            ],
            "monitoring_commands": [
                "Review recent configuration changes",
                "Compare with known-good configuration",
                "Check service logs",
            ],
        },
        "recovery_steps": [
            {
                "step_number": 1,
                "title": "Identify configuration issue",
                "commands": [
                    "Review recent changes",
                    "Compare with baseline",
                ],
                "estimated_time_minutes": 15,
            },
            {
                "step_number": 2,
                "title": "Rollback configuration",
                "commands": ["Restore previous configuration", "Restart services"],
                "estimated_time_minutes": 10,
            },
            {
                "step_number": 3,
                "title": "Validate services",
                "commands": ["./check_services.sh", "Run health checks"],
                "estimated_time_minutes": 5,
            },
        ],
        "escalation": {
            "immediate": ["dba_team"],
            "after_2_hours": ["tech_lead"],
        },
    },
    "performance_degradation": {
        "title": "Database Performance Degradation Response",
        "database_type": "all",
        "severity": "high",
        "rto_target": 60,
        "rpo_target": 120,
        "detection": {
            "symptoms": [
                "Slow query performance",
                "High CPU usage",
                "High memory usage",
                "Elevated response times",
            ],
            "monitoring_commands": [
                "Check system resources",
                "Review slow query log",
                "Analyze query execution plans",
            ],
        },
        "recovery_steps": [
            {
                "step_number": 1,
                "title": "Identify bottleneck",
                "commands": [
                    "Analyze slow queries",
                    "Check system resources",
                    "Review connection pool",
                ],
                "estimated_time_minutes": 15,
            },
            {
                "step_number": 2,
                "title": "Apply immediate fixes",
                "commands": [
                    "Kill long-running queries",
                    "Increase connection pool",
                    "Enable query cache",
                ],
                "estimated_time_minutes": 10,
            },
            {
                "step_number": 3,
                "title": "Optimize queries",
                "commands": [
                    "Add missing indexes",
                    "Optimize query plans",
                    "Update statistics",
                ],
                "estimated_time_minutes": 30,
            },
        ],
        "escalation": {
            "immediate": ["dba_team"],
            "after_1_hour": ["tech_lead", "infrastructure_team"],
        },
    },
    "cross_service_incident": {
        "title": "Cross-Service Database Incident Response",
        "database_type": "multiple",
        "severity": "critical",
        "rto_target": 30,
        "rpo_target": 60,
        "detection": {
            "symptoms": [
                "Multiple services affected",
                "Cascading failures",
                "Service dependency issues",
            ],
            "monitoring_commands": [
                "./check_services.sh",
                "Review service dependencies",
                "Check database connections",
            ],
        },
        "recovery_steps": [
            {
                "step_number": 1,
                "title": "Identify root cause",
                "commands": [
                    "Map service dependencies",
                    "Identify failing component",
                ],
                "estimated_time_minutes": 10,
            },
            {
                "step_number": 2,
                "title": "Isolate failure",
                "commands": [
                    "Stop cascade",
                    "Implement circuit breakers",
                ],
                "estimated_time_minutes": 5,
            },
            {
                "step_number": 3,
                "title": "Restore services sequentially",
                "commands": [
                    "Restore database layer first",
                    "Then API layer",
                    "Finally frontend",
                ],
                "estimated_time_minutes": 20,
            },
        ],
        "escalation": {
            "immediate": ["oncall", "dba_team", "infrastructure_team", "management"],
        },
    },
}


def create_comprehensive_runbooks(output_dir: Path = None) -> Dict[str, Any]:
    """
    Create comprehensive incident response runbooks.

    Args:
        output_dir: Output directory for runbooks

    Returns:
        Creation result
    """
    if output_dir is None:
        output_dir = Path("docs/runbooks")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_runbooks = []

    for runbook_name, runbook_data in RUNBOOK_TEMPLATES.items():
        filename = f"{runbook_name}.yml"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(runbook_data, f, default_flow_style=False, sort_keys=False)

        created_runbooks.append(str(filepath))

    return {
        "success": True,
        "runbooks_created": len(created_runbooks),
        "output_dir": str(output_dir),
        "runbooks": created_runbooks,
    }


def validate_runbooks(output_dir: Path = None) -> Dict[str, Any]:
    """
    Validate existing runbooks.

    Args:
        output_dir: Directory containing runbooks

    Returns:
        Validation result
    """
    if output_dir is None:
        output_dir = Path("docs/runbooks")

    output_dir = Path(output_dir)

    if not output_dir.exists():
        return {
            "success": False,
            "error": f"Runbook directory not found: {output_dir}",
            "valid_runbooks": 0,
            "invalid_runbooks": 0,
        }

    valid_runbooks = 0
    invalid_runbooks = 0
    validation_errors = []

    for runbook_file in output_dir.glob("*.yml"):
        try:
            with open(runbook_file, "r", encoding="utf-8") as f:
                runbook_data = yaml.safe_load(f)

            # Validate required fields
            required_fields = ["title", "severity", "rto_target", "recovery_steps"]
            missing_fields = [field for field in required_fields if field not in runbook_data]

            if missing_fields:
                invalid_runbooks += 1
                validation_errors.append(f"{runbook_file.name}: Missing fields {missing_fields}")
            else:
                valid_runbooks += 1

        except Exception as e:
            invalid_runbooks += 1
            validation_errors.append(f"{runbook_file.name}: {str(e)}")

    return {
        "success": invalid_runbooks == 0,
        "valid_runbooks": valid_runbooks,
        "invalid_runbooks": invalid_runbooks,
        "validation_errors": validation_errors,
    }


def parse_arguments(args: Optional[list] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Create incident response runbooks")
    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Create comprehensive runbook set",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/runbooks",
        help="Output directory for runbooks",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing runbooks",
    )

    return parser.parse_args(args)


def main() -> int:
    """Execute main program logic."""
    args = parse_arguments()

    if args.comprehensive:
        print("Creating comprehensive incident response runbooks...")
        result = create_comprehensive_runbooks(output_dir=Path(args.output_dir))

        if result["success"]:
            print(f"✓ Successfully created {result['runbooks_created']} runbooks")
            print(f"  Output directory: {result['output_dir']}")
            print("  Runbooks:")
            for runbook in result["runbooks"]:
                print(f"    - {Path(runbook).name}")
            return 0
        else:
            print(f"✗ Failed to create runbooks: {result.get('error', 'Unknown error')}")
            return 1

    elif args.validate:
        print("Validating incident response runbooks...")
        result = validate_runbooks(output_dir=Path(args.output_dir))

        if result["success"]:
            print(f"✓ All runbooks are valid ({result['valid_runbooks']} runbooks)")
            return 0
        else:
            print("✗ Validation failed:")
            print(f"  Valid runbooks: {result['valid_runbooks']}")
            print(f"  Invalid runbooks: {result['invalid_runbooks']}")
            if result.get("validation_errors"):
                print("  Errors:")
                for error in result["validation_errors"]:
                    print(f"    - {error}")
            return 1

    else:
        print("No action specified. Use --comprehensive or --validate")
        return 1


if __name__ == "__main__":
    sys.exit(main())
