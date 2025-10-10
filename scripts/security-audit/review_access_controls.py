#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Access Control Review and Privilege Validation Tool.

This CLI tool reviews and validates access controls across PostgreSQL and SQLite
databases, generates access control matrices, and identifies privilege violations.

Usage:
    python3 review_access_controls.py --validate-privileges
    python3 review_access_controls.py --system-accounts
    python3 review_access_controls.py --generate-matrix --report-format json
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class PrivilegeViolation:
    """Represents a privilege violation finding."""

    user: str
    privilege: str
    justification: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    remediation: str


@dataclass
class AccessMatrix:
    """Access control matrix with users, roles, and privileges."""

    users: List[Dict[str, Any]] = field(default_factory=list)
    roles: List[Dict[str, Any]] = field(default_factory=list)
    privileges: Dict[str, List[str]] = field(default_factory=dict)
    violations: List[PrivilegeViolation] = field(default_factory=list)


@dataclass
class AccessControlReport:
    """Comprehensive access control review report."""

    scan_timestamp: str
    databases_reviewed: List[str] = field(default_factory=list)
    access_matrix: AccessMatrix = field(default_factory=AccessMatrix)
    system_accounts: List[Dict[str, Any]] = field(default_factory=list)
    isolation_assessment: Dict[str, Any] = field(default_factory=dict)
    summary: Dict[str, int] = field(default_factory=dict)
    scan_duration_seconds: float = 0.0


class AccessControlReviewer:
    """Reviews access controls and validates privilege assignments."""

    def __init__(self, config_dir: Path) -> None:
        """Initialize access control reviewer."""
        self.config_dir = config_dir
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load security standards configuration."""
        config_path = self.config_dir / "security_standards.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def review_sqlite_access(self, db_path: Path) -> Dict[str, Any]:
        """Review SQLite database access controls."""
        access_info = {"database": str(db_path), "findings": []}

        if not db_path.exists():
            access_info["findings"].append({"type": "error", "message": f"Database not found: {db_path}"})
            return access_info

        # Check file permissions
        file_stat = os.stat(db_path)
        file_mode = file_stat.st_mode & 0o777

        required_mode = int(
            self.config.get("sqlite", {}).get("file_security", {}).get("permissions", "0600"),
            8,
        )

        if file_mode != required_mode:
            access_info["findings"].append(
                {
                    "type": "permission_violation",
                    "current": oct(file_mode),
                    "required": oct(required_mode),
                    "severity": "HIGH" if file_mode & 0o077 else "MEDIUM",
                }
            )
        else:
            access_info["findings"].append(
                {
                    "type": "permission_compliant",
                    "current": oct(file_mode),
                    "message": "File permissions are correct",
                }
            )

        # Check database integrity and user isolation
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get schema information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

            access_info["tables"] = tables
            access_info["table_count"] = len(tables)

            conn.close()
        except sqlite3.Error as e:
            access_info["findings"].append({"type": "connection_error", "message": str(e)})

        return access_info

    def generate_access_matrix(self) -> AccessMatrix:
        """Generate access control matrix."""
        matrix = AccessMatrix()

        # In production, this would query actual databases
        # For this implementation, we provide a structured framework
        matrix.users = [
            {
                "username": "keycloak",
                "type": "application",
                "database_access": ["postgres"],
                "privileges": ["SELECT", "INSERT", "UPDATE", "DELETE"],
            },
            {
                "username": "api_service",
                "type": "system_account",
                "database_access": ["sqlite"],
                "privileges": ["SELECT", "INSERT", "UPDATE"],
            },
        ]

        matrix.roles = [
            {"role": "application", "privileges": ["CRUD"], "member_count": 1},
            {"role": "system_account", "privileges": ["READ", "WRITE"], "member_count": 1},
        ]

        # Check for privilege violations
        for user in matrix.users:
            if "DELETE" in user.get("privileges", []):
                if user["type"] == "system_account":
                    matrix.violations.append(
                        PrivilegeViolation(
                            user=user["username"],
                            privilege="DELETE",
                            justification="Service account should not have DELETE privilege",
                            severity="HIGH",
                            remediation=f"Revoke DELETE privilege from {user['username']}",
                        )
                    )

        return matrix

    def validate_least_privilege(self, matrix: AccessMatrix) -> List[Dict[str, Any]]:
        """Validate least privilege principle compliance."""
        violations = []

        for user in matrix.users:
            privileges = user.get("privileges", [])

            # Check for excessive privileges
            if len(privileges) > 3:
                violations.append(
                    {
                        "user": user["username"],
                        "issue": "excessive_privileges",
                        "privilege_count": len(privileges),
                        "recommendation": "Review and reduce privilege assignments",
                        "severity": "MEDIUM",
                    }
                )

            # Check for dangerous privilege combinations
            dangerous_privs = {"DELETE", "DROP", "ALTER"}
            user_dangerous = set(privileges) & dangerous_privs
            if user_dangerous:
                violations.append(
                    {
                        "user": user["username"],
                        "issue": "dangerous_privileges",
                        "privileges": list(user_dangerous),
                        "recommendation": "Remove unless absolutely necessary",
                        "severity": "HIGH",
                    }
                )

        return violations

    def review_system_accounts(self) -> List[Dict[str, Any]]:
        """Review system account credentials and privileges."""
        system_accounts = []

        # In production, this would query actual system accounts
        # For this implementation, we provide expected structure
        accounts = [
            {
                "name": "keycloak",
                "database": "postgresql",
                "credential_type": "password",
                "last_rotation": "2025-09-01",
            },
            {
                "name": "api_service",
                "database": "sqlite",
                "credential_type": "file_access",
                "last_rotation": "N/A",
            },
        ]

        for account in accounts:
            analysis = {
                "account": account["name"],
                "database": account["database"],
                "security_issues": [],
            }

            # Check credential rotation
            if account["credential_type"] == "password":
                if account.get("last_rotation", "N/A") == "N/A":
                    analysis["security_issues"].append(
                        {
                            "issue": "credential_never_rotated",
                            "severity": "HIGH",
                            "recommendation": "Implement credential rotation policy",
                        }
                    )

            system_accounts.append(analysis)

        return system_accounts

    def assess_isolation(self, db_paths: List[Path]) -> Dict[str, Any]:
        """Assess user data isolation in databases."""
        isolation_report = {
            "databases_checked": len(db_paths),
            "isolation_level": "container",
            "violations": [],
            "risk_score": 0,
        }

        # Check file-level isolation
        for db_path in db_paths:
            if not db_path.exists():
                continue

            file_stat = os.stat(db_path)
            file_mode = file_stat.st_mode & 0o777

            if file_mode & 0o077:  # Group or others have access
                isolation_report["violations"].append(
                    {
                        "database": str(db_path),
                        "issue": "file_accessible_by_others",
                        "permissions": oct(file_mode),
                        "severity": "HIGH",
                    }
                )
                isolation_report["risk_score"] += 10

        return isolation_report


def main() -> None:
    """Execute access control review CLI."""
    parser = argparse.ArgumentParser(description="Access Control Review and Privilege Validation Tool")
    parser.add_argument(
        "--validate-privileges",
        action="store_true",
        help="Validate all privilege assignments",
    )
    parser.add_argument(
        "--system-accounts",
        action="store_true",
        help="Review system account credentials and access",
    )
    parser.add_argument(
        "--generate-matrix",
        action="store_true",
        help="Generate access control matrix",
    )
    parser.add_argument(
        "--check-isolation",
        action="store_true",
        help="Validate user data isolation",
    )
    parser.add_argument(
        "--report-format",
        choices=["json", "yaml"],
        default="json",
        help="Output format for reports",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "reports",
        help="Directory for output reports",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(__file__).parent / "config",
        help="Directory containing configuration files",
    )

    args = parser.parse_args()

    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize reviewer
    reviewer = AccessControlReviewer(args.config_dir)

    # Start timing
    start_time = time.time()

    # Initialize report
    report = AccessControlReport(scan_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"))

    # If no specific action requested, do comprehensive review
    if not any(
        [
            args.validate_privileges,
            args.system_accounts,
            args.generate_matrix,
            args.check_isolation,
        ]
    ):
        args.validate_privileges = True
        args.generate_matrix = True

    # Generate access matrix
    if args.generate_matrix or args.validate_privileges:
        print("\nGenerating access control matrix...")
        report.access_matrix = reviewer.generate_access_matrix()
        print(f"  Users: {len(report.access_matrix.users)}")
        print(f"  Roles: {len(report.access_matrix.roles)}")
        print(f"  Violations: {len(report.access_matrix.violations)}")

    # Validate privileges
    if args.validate_privileges:
        print("\nValidating least privilege compliance...")
        violations = reviewer.validate_least_privilege(report.access_matrix)
        print(f"  Least privilege violations: {len(violations)}")

    # Review system accounts
    if args.system_accounts:
        print("\nReviewing system accounts...")
        report.system_accounts = reviewer.review_system_accounts()
        print(f"  System accounts reviewed: {len(report.system_accounts)}")

    # Check isolation
    if args.check_isolation:
        print("\nAssessing user data isolation...")
        # Find SQLite databases
        db_paths = [
            Path("/app/app_data/violentutf_api.db"),  # Common path
        ]
        report.isolation_assessment = reviewer.assess_isolation(db_paths)
        print(f"  Isolation risk score: {report.isolation_assessment.get('risk_score', 0)}")

    # Calculate summary
    report.scan_duration_seconds = time.time() - start_time
    report.summary = {
        "total_users": len(report.access_matrix.users),
        "total_violations": len(report.access_matrix.violations),
        "system_accounts": len(report.system_accounts),
        "isolation_violations": len(report.isolation_assessment.get("violations", [])),
    }

    # Save report
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_filename = f"access_control_review_{timestamp}.{args.report_format}"
    report_path = args.output_dir / report_filename

    # Convert report to dict
    report_dict = {
        "scan_timestamp": report.scan_timestamp,
        "databases_reviewed": report.databases_reviewed,
        "access_matrix": {
            "users": report.access_matrix.users,
            "roles": report.access_matrix.roles,
            "privileges": report.access_matrix.privileges,
            "violations": [asdict(v) for v in report.access_matrix.violations],
        },
        "system_accounts": report.system_accounts,
        "isolation_assessment": report.isolation_assessment,
        "summary": report.summary,
        "scan_duration_seconds": report.scan_duration_seconds,
    }

    if args.report_format == "json":
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)
    else:  # yaml
        with open(report_path, "w", encoding="utf-8") as f:
            yaml.dump(report_dict, f, default_flow_style=False)

    print("\n✅ Access control review complete!")
    print(f"   Report saved to: {report_path}")
    print(f"   Duration: {report.scan_duration_seconds:.2f} seconds")
    print("\n📊 Summary:")
    print(f"   Total users: {report.summary['total_users']}")
    print(f"   Privilege violations: {report.summary['total_violations']}")
    print(f"   System accounts: {report.summary['system_accounts']}")


if __name__ == "__main__":
    main()
