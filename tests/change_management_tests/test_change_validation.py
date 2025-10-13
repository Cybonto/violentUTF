"""
Tests for change validation system.
Tests pre-change validation, schema validation, and dependency checking.
"""

import pytest
from typing import Dict, Any


class TestPreChangeValidation:
    """Test pre-change validation checks."""

    def test_validate_complete_change_request(self, sample_change_request):
        """Test validation of complete change request."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.validate_change_request(sample_change_request)

        assert result.valid is True
        assert len(result.missing_fields) == 0
        assert len(result.errors) == 0

    def test_validate_incomplete_change_request(self):
        """Test validation of incomplete change request."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        incomplete_request = {
            "title": "Test change",
            # Missing required fields
        }

        result = validator.validate_change_request(incomplete_request)

        assert result.valid is False
        assert len(result.missing_fields) > 0
        assert "description" in result.missing_fields
        assert "change_type" in result.missing_fields

    def test_validate_invalid_database_type(self, sample_change_request):
        """Test validation rejects invalid database type."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        sample_change_request["database"] = "invalid_database"

        result = validator.validate_change_request(sample_change_request)

        assert result.valid is False
        assert "database" in result.errors


class TestSchemaValidation:
    """Test schema change validation."""

    def test_validate_postgresql_schema_change(self, sample_migration_file):
        """Test validation of PostgreSQL schema migration."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.validate_schema_change("postgresql", sample_migration_file)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_sqlite_schema_change(self, temp_sqlite_db):
        """Test validation of SQLite schema change."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()

        # Test schema change validation
        schema_change = {
            "database_path": str(temp_sqlite_db),
            "migration": "ALTER TABLE users ADD COLUMN phone TEXT",
        }

        result = validator.validate_sqlite_schema_change(schema_change)
        assert result.valid is True

    def test_validate_breaking_schema_change(self):
        """Test detection of breaking schema changes."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()

        breaking_change = {
            "database": "postgresql",
            "migration": "ALTER TABLE users DROP COLUMN username",
            "breaking": True,
        }

        result = validator.validate_schema_change_impact(breaking_change)

        assert len(result.warnings) > 0
        assert any("breaking" in w.lower() for w in result.warnings)


class TestConfigurationValidation:
    """Test configuration change validation."""

    def test_validate_yaml_configuration(self, temp_config_files):
        """Test validation of YAML configuration file."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.validate_configuration_change(temp_config_files["yaml"])

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_env_configuration(self, temp_config_files):
        """Test validation of .env configuration file."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.validate_configuration_change(temp_config_files["env"])

        assert result.valid is True

    def test_detect_sensitive_data_in_config(self, temp_config_files):
        """Test detection of sensitive data in configuration."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.validate_configuration_change(temp_config_files["env"])

        # Should have warnings about sensitive data
        assert len(result.warnings) > 0

    def test_validate_json_configuration(self, temp_config_files):
        """Test validation of JSON configuration file."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.validate_configuration_change(temp_config_files["json"])

        assert result.valid is True


class TestDependencyValidation:
    """Test dependency checking and validation."""

    def test_validate_no_circular_dependencies(self, sample_change_request):
        """Test validation passes when no circular dependencies."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        dependencies = validator.validate_dependencies(sample_change_request)

        assert dependencies.circular_dependencies is False
        assert dependencies.conflicts_detected is False

    def test_detect_service_dependencies(self, sample_major_change):
        """Test detection of service dependencies."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        dependencies = validator.validate_dependencies(sample_major_change)

        assert len(dependencies.services) > 0
        assert "keycloak" in dependencies.services or "api" in dependencies.services

    def test_detect_database_dependencies(self, sample_major_change):
        """Test detection of database dependencies."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        dependencies = validator.validate_dependencies(sample_major_change)

        assert len(dependencies.databases) > 0

    def test_detect_conflicting_changes(self):
        """Test detection of conflicting changes."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()

        change1 = {
            "title": "Add user preferences table",
            "database": "postgresql",
            "table": "user_preferences",
            "operation": "create",
        }

        change2 = {
            "title": "Drop user preferences table",
            "database": "postgresql",
            "table": "user_preferences",
            "operation": "drop",
        }

        dependencies = validator.detect_conflicts([change1, change2])

        assert dependencies.conflicts_detected is True
        assert len(dependencies.conflict_details) > 0


class TestRollbackValidation:
    """Test rollback procedure validation."""

    def test_validate_rollback_available(self, sample_change_request):
        """Test validation checks if rollback is available."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        sample_change_request["rollback_available"] = True
        sample_change_request["rollback_procedure"] = "Restore from snapshot"

        result = validator.validate_rollback_procedure(sample_change_request)

        assert result.valid is True

    def test_validate_no_rollback_available(self, sample_change_request):
        """Test validation when rollback is not available."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        sample_change_request["rollback_available"] = False

        result = validator.validate_rollback_procedure(sample_change_request)

        assert len(result.warnings) > 0
        assert any("rollback" in w.lower() for w in result.warnings)


class TestPreChangeChecks:
    """Test comprehensive pre-change checks."""

    def test_perform_all_pre_change_checks(self, sample_change_request):
        """Test execution of all pre-change checks."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.perform_pre_change_checks(sample_change_request)

        assert result.valid is True
        assert "validation" in result.checks_performed
        assert "dependencies" in result.checks_performed
        assert "rollback" in result.checks_performed

    def test_pre_change_checks_fail_on_missing_data(self):
        """Test pre-change checks fail with incomplete data."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        incomplete_request = {"title": "Test"}

        result = validator.perform_pre_change_checks(incomplete_request)

        assert result.valid is False
        assert len(result.missing_fields) > 0

    def test_pre_change_checks_warn_on_high_risk(self, sample_major_change):
        """Test pre-change checks warn on high-risk changes."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.perform_pre_change_checks(sample_major_change)

        assert len(result.warnings) > 0


class TestValidationIntegration:
    """Test validation integration with other systems."""

    def test_validation_with_classifier(self, sample_change_request):
        """Test validation integration with change classifier."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )
        from scripts.change_management.core.change_classifier import (
            ChangeClassifier,
        )

        validator = ChangeValidator()
        classifier = ChangeClassifier()

        # Classify first
        change_type = classifier.classify_change(sample_change_request)
        risk = classifier.assess_risk(sample_change_request)

        # Add classification to request
        sample_change_request["classified_type"] = change_type.value
        sample_change_request["classified_risk"] = risk.value

        # Validate
        result = validator.perform_pre_change_checks(sample_change_request)

        assert result.valid is True

    def test_validation_generates_approval_requirements(self, sample_major_change):
        """Test validation generates approval requirements."""
        from scripts.change_management.core.change_validator import (
            ChangeValidator,
        )

        validator = ChangeValidator()
        result = validator.perform_pre_change_checks(sample_major_change)

        assert hasattr(result, "approval_requirements")
        assert result.approval_requirements.get("approvers_required", 0) >= 2
