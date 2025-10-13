# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Change Validation System.

Validates change requests, schema changes, configuration changes,
and performs dependency analysis.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import yaml


@dataclass
class ValidationResult:
    """Change request validation result."""

    valid: bool
    missing_fields: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    checks_performed: List[str] = field(default_factory=list)
    approval_requirements: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyAnalysis:
    """Dependency analysis result."""

    services: List[str] = field(default_factory=list)
    databases: List[str] = field(default_factory=list)
    configurations: List[str] = field(default_factory=list)
    circular_dependencies: bool = False
    conflicts_detected: bool = False
    conflict_details: List[str] = field(default_factory=list)


class ChangeValidator:
    """Validates change requests and performs pre-change checks."""

    REQUIRED_FIELDS = [
        "title",
        "description",
        "change_type",
        "database",
    ]

    VALID_DATABASES = ["postgresql", "sqlite", "multiple", "none"]
    VALID_CHANGE_TYPES = ["emergency", "standard", "normal", "major"]

    # Sensitive data patterns
    SENSITIVE_PATTERNS = [
        r"password\s*[=:]",
        r"secret\s*[=:]",
        r"api[_-]?key\s*[=:]",
        r"token\s*[=:]",
        r"private[_-]?key",
    ]

    def __init__(self) -> None:
        """Initialize change validator."""

    def validate_change_request(self, change_request: Dict[str, Any]) -> ValidationResult:
        """
        Validate change request completeness and correctness.

        Args:
            change_request: Change request data

        Returns:
            ValidationResult
        """
        missing_fields = []
        errors = {}
        warnings = []

        # Check required fields
        for req_field in self.REQUIRED_FIELDS:
            if req_field not in change_request or not change_request[req_field]:
                missing_fields.append(req_field)

        # Validate database type
        database = change_request.get("database", "")
        if database and database not in self.VALID_DATABASES:
            errors["database"] = f"Invalid database type: {database}. " f"Must be one of {self.VALID_DATABASES}"

        # Validate change type
        change_type = change_request.get("change_type", "")
        if change_type and change_type not in self.VALID_CHANGE_TYPES:
            errors["change_type"] = f"Invalid change type: {change_type}. " f"Must be one of {self.VALID_CHANGE_TYPES}"

        valid = len(missing_fields) == 0 and len(errors) == 0

        return ValidationResult(
            valid=valid,
            missing_fields=missing_fields,
            errors=errors,
            warnings=warnings,
        )

    def validate_schema_change(self, database: str, migration_file: Path) -> ValidationResult:
        """
        Validate database schema change.

        Args:
            database: Database type
            migration_file: Path to migration file

        Returns:
            ValidationResult
        """
        errors = {}
        warnings = []

        # Check file exists
        if not Path(migration_file).exists():
            errors["migration_file"] = "Migration file not found"
            return ValidationResult(valid=False, errors=errors)

        # Read migration file
        content = Path(migration_file).read_text(encoding="utf-8")

        # Check for dangerous operations
        dangerous_ops = ["DROP TABLE", "TRUNCATE", "DELETE FROM"]
        for op in dangerous_ops:
            if op in content.upper():
                warnings.append(f"Potentially destructive operation: {op}")

        # Database-specific validation
        if database == "postgresql":
            # Check for transaction controls
            if "BEGIN" not in content.upper():
                warnings.append("Migration should use transactions")

        valid = len(errors) == 0
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    def validate_sqlite_schema_change(self, schema_change: Dict[str, Any]) -> ValidationResult:
        """
        Validate SQLite schema change.

        Args:
            schema_change: Schema change data

        Returns:
            ValidationResult
        """
        errors = {}
        warnings = []

        # Validate database path
        db_path = schema_change.get("database_path")
        if not db_path or not Path(db_path).exists():
            errors["database_path"] = "Database file not found"

        # Check migration syntax
        migration = schema_change.get("migration", "")
        if "ALTER TABLE" in migration.upper():
            if "ADD COLUMN" in migration.upper():
                # Valid ALTER TABLE operation
                pass
            else:
                warnings.append("SQLite has limited ALTER TABLE support")

        valid = len(errors) == 0
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    def validate_schema_change_impact(self, schema_change: Dict[str, Any]) -> ValidationResult:
        """
        Validate impact of schema change.

        Args:
            schema_change: Schema change data

        Returns:
            ValidationResult
        """
        warnings = []

        # Check if breaking change
        if schema_change.get("breaking"):
            warnings.append("This is a breaking change. Ensure all dependent services are updated.")

        # Check for data migration
        migration = schema_change.get("migration", "")
        if "DROP COLUMN" in migration.upper():
            warnings.append("Dropping column may cause data loss. Ensure data is backed up.")

        return ValidationResult(valid=True, warnings=warnings)

    def validate_configuration_change(self, config_file: Path) -> ValidationResult:
        """
        Validate configuration file change.

        Args:
            config_file: Path to configuration file

        Returns:
            ValidationResult
        """
        errors = {}
        warnings = []

        if not Path(config_file).exists():
            errors["config_file"] = "Configuration file not found"
            return ValidationResult(valid=False, errors=errors)

        content = Path(config_file).read_text(encoding="utf-8")

        # Check for sensitive data
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potential sensitive data detected: {pattern}")

        # Validate file format
        suffix = Path(config_file).suffix.lower()
        try:
            if suffix in [".yml", ".yaml"]:
                yaml.safe_load(content)
            elif suffix == ".json":
                json.loads(content)
            elif suffix == ".env":
                # Basic .env validation
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" not in line:
                            warnings.append(f"Invalid .env line format: {line}")
        except Exception as e:
            errors["format"] = f"Invalid file format: {str(e)}"

        valid = len(errors) == 0
        return ValidationResult(valid=valid, errors=errors, warnings=warnings)

    def validate_dependencies(self, change_request: Dict[str, Any]) -> DependencyAnalysis:
        """
        Validate and analyze dependencies.

        Args:
            change_request: Change request data

        Returns:
            DependencyAnalysis
        """
        services = []
        databases = []
        configurations = []

        # Extract affected services
        impact_scope = change_request.get("impact_scope", [])
        if isinstance(impact_scope, list):
            services.extend(impact_scope)

        # Extract affected databases
        database = change_request.get("database", "")
        if database == "multiple":
            databases.extend(["postgresql", "sqlite"])
        elif database != "none":
            databases.append(database)

        # Check for circular dependencies
        circular = False  # Simplified for now

        # Check for conflicts
        conflicts = False
        conflict_details = []

        return DependencyAnalysis(
            services=services,
            databases=databases,
            configurations=configurations,
            circular_dependencies=circular,
            conflicts_detected=conflicts,
            conflict_details=conflict_details,
        )

    def detect_conflicts(self, changes: List[Dict[str, Any]]) -> DependencyAnalysis:
        """
        Detect conflicts between multiple changes.

        Args:
            changes: List of changes to check

        Returns:
            DependencyAnalysis with conflict information
        """
        conflicts = False
        conflict_details = []

        # Check for conflicting operations on same table
        operations = {}
        for change in changes:
            table = change.get("table")
            operation = change.get("operation")
            if table:
                if table in operations:
                    # Check for conflicts
                    existing_op = operations[table]
                    if (
                        (existing_op == "create" and operation == "drop")
                        or (existing_op == "drop" and operation == "create")
                        or (existing_op == "alter" and operation == "drop")
                    ):
                        conflicts = True
                        conflict_details.append(
                            f"Conflicting operations on table {table}: " f"{existing_op} vs {operation}"
                        )
                else:
                    operations[table] = operation

        return DependencyAnalysis(
            conflicts_detected=conflicts,
            conflict_details=conflict_details,
        )

    def validate_rollback_procedure(self, change_request: Dict[str, Any]) -> ValidationResult:
        """
        Validate rollback procedure availability.

        Args:
            change_request: Change request data

        Returns:
            ValidationResult
        """
        warnings = []

        rollback_available = change_request.get("rollback_available", False)
        if not rollback_available:
            warnings.append("No rollback procedure available. Ensure manual rollback process is documented.")

        rollback_procedure = change_request.get("rollback_procedure", "")
        if rollback_available and not rollback_procedure:
            warnings.append("Rollback is marked as available but no procedure documented.")

        return ValidationResult(valid=True, warnings=warnings)

    def perform_pre_change_checks(self, change_request: Dict[str, Any]) -> ValidationResult:
        """
        Perform comprehensive pre-change checks.

        Args:
            change_request: Change request data

        Returns:
            Consolidated ValidationResult
        """
        checks_performed = []
        all_warnings = []
        all_errors = {}
        all_missing = []

        # 1. Validate change request
        validation = self.validate_change_request(change_request)
        checks_performed.append("validation")
        all_warnings.extend(validation.warnings)
        all_errors.update(validation.errors)
        all_missing.extend(validation.missing_fields)

        # 2. Validate dependencies
        dependencies = self.validate_dependencies(change_request)
        checks_performed.append("dependencies")
        if dependencies.conflicts_detected:
            all_warnings.append("Dependency conflicts detected: " + "; ".join(dependencies.conflict_details))

        # 3. Validate rollback
        rollback_check = self.validate_rollback_procedure(change_request)
        checks_performed.append("rollback")
        all_warnings.extend(rollback_check.warnings)

        # 4. Risk assessment warnings
        classified_risk = change_request.get("classified_risk", "")
        if classified_risk in ["high", "critical"]:
            all_warnings.append(f"High risk change ({classified_risk}). " "Ensure thorough testing and approval.")

        # Determine approval requirements
        change_type = change_request.get("classified_type") or change_request.get("change_type", "normal")
        approval_requirements = self._determine_approval_requirements(change_type)

        valid = len(all_missing) == 0 and len(all_errors) == 0

        return ValidationResult(
            valid=valid,
            missing_fields=all_missing,
            errors=all_errors,
            warnings=all_warnings,
            checks_performed=checks_performed,
            approval_requirements=approval_requirements,
        )

    def _determine_approval_requirements(self, change_type: str) -> Dict[str, Any]:
        """Determine approval requirements based on change type."""
        requirements = {
            "emergency": {
                "approvers_required": 0,
                "post_review": True,
            },
            "standard": {
                "approvers_required": 0,
                "pre_approved": True,
            },
            "normal": {
                "approvers_required": 1,
                "approver_roles": ["dba"],
            },
            "major": {
                "approvers_required": 2,
                "approver_roles": ["dba", "tech_lead"],
                "adr_required": True,
            },
        }

        return requirements.get(change_type, requirements["normal"])
