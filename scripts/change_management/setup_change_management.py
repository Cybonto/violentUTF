#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Setup Change Management System.

Configures change management workflows, approval processes, and system integration.

Usage:
    python3 setup_change_management.py --configure-workflows
    python3 setup_change_management.py --configure-workflows --output-dir /path/to/workflows
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def configure_workflows(output_dir: Path = None, update: bool = False) -> Dict[str, Any]:
    """
    Configure change management workflows.

    Args:
        output_dir: Output directory for workflow files
        update: Whether to update existing configuration

    Returns:
        Result dictionary
    """
    if output_dir is None:
        output_dir = Path("workflows/change-approval")

    output_dir = Path(output_dir)

    # Handle non-existent directory
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create directory: {str(e)}",
        }

    workflows_configured = 0

    # Create approval_matrix.yml
    approval_matrix = {
        "emergency": {
            "approvers_required": 0,
            "post_review": True,
            "notification": ["oncall", "dba_team"],
        },
        "standard": {
            "approvers_required": 0,
            "pre_approved": True,
            "notification": ["dba_team"],
        },
        "normal": {
            "approvers_required": 1,
            "approver_roles": ["dba", "tech_lead"],
            "notification": ["dba_team", "submitter"],
        },
        "major": {
            "approvers_required": 2,
            "approver_roles": ["dba", "tech_lead", "architect"],
            "notification": ["all_engineering", "management"],
            "additional_requirements": ["adr", "testing_plan"],
        },
    }

    approval_matrix_path = output_dir / "approval_matrix.yml"
    with open(approval_matrix_path, "w", encoding="utf-8") as f:
        yaml.dump(approval_matrix, f, default_flow_style=False)
    workflows_configured += 1

    # Create stakeholder_registry.yml
    stakeholder_registry = {
        "dba_team": ["dba1@example.com", "dba2@example.com"],
        "tech_lead": ["techlead@example.com"],
        "architect": ["architect@example.com"],
        "oncall": ["oncall@example.com"],
        "security_team": ["security@example.com"],
        "all_engineering": ["engineering@example.com"],
        "management": ["mgmt@example.com"],
    }

    stakeholder_path = output_dir / "stakeholder_registry.yml"
    with open(stakeholder_path, "w", encoding="utf-8") as f:
        yaml.dump(stakeholder_registry, f, default_flow_style=False)
    workflows_configured += 1

    # Create maintenance_windows.yml
    maintenance_windows = {
        "windows": [
            {
                "id": "MW-WEEKLY",
                "name": "Weekly Maintenance Window",
                "schedule": "Sunday 02:00-04:00 UTC",
                "recurring": True,
                "day_of_week": "Sunday",
                "start_hour": 2,
                "duration_hours": 2,
            },
            {
                "id": "MW-MONTHLY",
                "name": "Monthly Major Maintenance",
                "schedule": "First Sunday 00:00-06:00 UTC",
                "recurring": True,
                "frequency": "monthly",
                "duration_hours": 6,
            },
        ]
    }

    maintenance_path = output_dir / "maintenance_windows.yml"
    with open(maintenance_path, "w", encoding="utf-8") as f:
        yaml.dump(maintenance_windows, f, default_flow_style=False)
    workflows_configured += 1

    return {
        "success": True,
        "workflows_configured": workflows_configured,
        "updated": update,
        "output_dir": str(output_dir),
        "files_created": [
            str(approval_matrix_path),
            str(stakeholder_path),
            str(maintenance_path),
        ],
    }


def verify_configuration(config_dir: Path = None) -> Dict[str, Any]:
    """
    Verify workflow configuration.

    Args:
        config_dir: Configuration directory

    Returns:
        Validation result
    """
    if config_dir is None:
        config_dir = Path("workflows/change-approval")

    config_dir = Path(config_dir)

    required_files = [
        "approval_matrix.yml",
        "stakeholder_registry.yml",
        "maintenance_windows.yml",
    ]

    missing_files = []
    for filename in required_files:
        if not (config_dir / filename).exists():
            missing_files.append(filename)

    valid = len(missing_files) == 0

    return {
        "valid": valid,
        "missing_files": missing_files,
        "config_dir": str(config_dir),
    }


def parse_arguments(args: Optional[list] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Setup Change Management System")
    parser.add_argument(
        "--configure-workflows",
        action="store_true",
        help="Configure change management workflows",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="workflows/change-approval",
        help="Output directory for workflow files",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing configuration",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing configuration",
    )

    return parser.parse_args(args)


def main() -> int:
    """Execute main program logic."""
    args = parse_arguments()

    if args.configure_workflows:
        print("Configuring change management workflows...")
        result = configure_workflows(output_dir=Path(args.output_dir), update=args.update)

        if result["success"]:
            print(f"✓ Successfully configured {result['workflows_configured']} workflows")
            print(f"  Output directory: {result['output_dir']}")
            print("  Files created:")
            for file in result["files_created"]:
                print(f"    - {file}")
            return 0
        else:
            print(f"✗ Configuration failed: {result.get('error', 'Unknown error')}")
            return 1

    elif args.verify:
        print("Verifying workflow configuration...")
        result = verify_configuration(config_dir=Path(args.output_dir))

        if result["valid"]:
            print("✓ Configuration is valid")
            return 0
        else:
            print("✗ Configuration is invalid")
            print(f"  Missing files: {', '.join(result['missing_files'])}")
            return 1

    else:
        print("No action specified. Use --configure-workflows or --verify")
        return 1


if __name__ == "__main__":
    sys.exit(main())
