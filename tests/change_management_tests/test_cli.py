"""
Tests for change management CLI scripts.
Tests CLI commands, argument parsing, and command execution.
"""

import pytest
import subprocess
from pathlib import Path


class TestSetupChangeManagementCLI:
    """Test setup_change_management.py CLI."""

    def test_configure_workflows_command(self, tmp_path):
        """Test --configure-workflows command."""
        # This test will run once implementation exists
        from scripts.change_management import setup_change_management

        result = setup_change_management.configure_workflows(
            output_dir=tmp_path
        )

        assert result["success"] is True
        assert result["workflows_configured"] >= 1

    def test_configure_workflows_creates_files(self, tmp_path):
        """Test that workflow configuration creates necessary files."""
        from scripts.change_management import setup_change_management

        result = setup_change_management.configure_workflows(
            output_dir=tmp_path
        )

        # Check that workflow files were created
        assert (tmp_path / "approval_matrix.yml").exists()
        assert (tmp_path / "stakeholder_registry.yml").exists()

    def test_setup_with_existing_config(self, tmp_path):
        """Test setup with existing configuration."""
        from scripts.change_management import setup_change_management

        # Create initial config
        setup_change_management.configure_workflows(output_dir=tmp_path)

        # Run again, should update not overwrite
        result = setup_change_management.configure_workflows(
            output_dir=tmp_path, update=True
        )

        assert result["success"] is True
        assert result["updated"] is True


class TestImplementRollbackProceduresCLI:
    """Test implement_rollback_procedures.py CLI."""

    def test_test_automation_command(self, tmp_path, temp_sqlite_db):
        """Test --test-automation command."""
        from scripts.change_management import implement_rollback_procedures

        result = implement_rollback_procedures.test_automation(
            database_type="sqlite",
            database_path=str(temp_sqlite_db),
            backup_location=tmp_path,
        )

        assert result["success"] is True
        assert "test_results" in result
        assert len(result["test_results"]) > 0

    def test_rollback_automation_postgresql(self, tmp_path):
        """Test rollback automation for PostgreSQL."""
        from scripts.change_management import implement_rollback_procedures

        # Mock PostgreSQL test
        result = implement_rollback_procedures.test_automation(
            database_type="postgresql",
            backup_location=tmp_path,
            dry_run=True,
        )

        assert result is not None

    def test_rollback_automation_sqlite(self, tmp_path, temp_sqlite_db):
        """Test rollback automation for SQLite."""
        from scripts.change_management import implement_rollback_procedures

        result = implement_rollback_procedures.test_automation(
            database_type="sqlite",
            database_path=str(temp_sqlite_db),
            backup_location=tmp_path,
        )

        assert result["success"] is True
        assert result["database_type"] == "sqlite"


class TestCreateIncidentRunbooksCLI:
    """Test create_incident_runbooks.py CLI."""

    def test_comprehensive_command(self, tmp_path):
        """Test --comprehensive command."""
        from scripts.change_management import create_incident_runbooks

        result = create_incident_runbooks.create_comprehensive_runbooks(
            output_dir=tmp_path
        )

        assert result["success"] is True
        assert result["runbooks_created"] >= 5

    def test_runbooks_created_with_correct_format(self, tmp_path):
        """Test that runbooks are created in YAML format."""
        from scripts.change_management import create_incident_runbooks

        result = create_incident_runbooks.create_comprehensive_runbooks(
            output_dir=tmp_path
        )

        # Check for specific runbooks
        runbook_dir = tmp_path
        assert (runbook_dir / "data_integrity_incident.yml").exists()
        assert (runbook_dir / "security_incident_database.yml").exists()
        assert (runbook_dir / "performance_degradation.yml").exists()

    def test_runbook_validation(self, tmp_path):
        """Test runbook validation."""
        from scripts.change_management import create_incident_runbooks

        # Create runbooks
        create_incident_runbooks.create_comprehensive_runbooks(
            output_dir=tmp_path
        )

        # Validate them
        result = create_incident_runbooks.validate_runbooks(output_dir=tmp_path)

        assert result["success"] is True
        assert result["valid_runbooks"] > 0
        assert result["invalid_runbooks"] == 0


class TestValidateChangeProceduresCLI:
    """Test validate_change_procedures.py CLI."""

    def test_test_workflows_command(self, tmp_path):
        """Test --test-workflows command."""
        from scripts.change_management import validate_change_procedures

        result = validate_change_procedures.test_workflows(
            config_dir=tmp_path
        )

        assert result is not None
        assert "test_details" in result

    def test_validate_approval_workflow(
        self, tmp_path, approval_matrix, stakeholder_registry
    ):
        """Test validation of approval workflow."""
        from scripts.change_management import validate_change_procedures
        import yaml

        # Create config files
        with open(tmp_path / "approval_matrix.yml", "w") as f:
            yaml.dump(approval_matrix, f)
        with open(tmp_path / "stakeholder_registry.yml", "w") as f:
            yaml.dump(stakeholder_registry, f)

        result = validate_change_procedures.validate_approval_workflow(
            config_dir=tmp_path
        )

        assert result["valid"] is True

    def test_validate_rollback_procedures(self, tmp_path, temp_sqlite_db):
        """Test validation of rollback procedures."""
        from scripts.change_management import validate_change_procedures

        result = validate_change_procedures.validate_rollback_procedures(
            database_type="sqlite",
            database_path=str(temp_sqlite_db),
            backup_location=tmp_path,
        )

        assert result is not None

    def test_validate_incident_response(self, tmp_path):
        """Test validation of incident response procedures."""
        from scripts.change_management import validate_change_procedures

        result = validate_change_procedures.validate_incident_response(
            runbook_dir=tmp_path
        )

        assert result is not None


class TestCLIIntegration:
    """Test CLI integration and end-to-end workflows."""

    def test_complete_setup_workflow(self, tmp_path):
        """Test complete setup workflow."""
        from scripts.change_management import setup_change_management

        # Configure workflows
        result1 = setup_change_management.configure_workflows(
            output_dir=tmp_path
        )
        assert result1["success"] is True

        # Verify configuration
        result2 = setup_change_management.verify_configuration(
            config_dir=tmp_path
        )
        assert result2["valid"] is True

    def test_rollback_testing_workflow(self, tmp_path, temp_sqlite_db):
        """Test rollback testing workflow."""
        from scripts.change_management import implement_rollback_procedures

        # Test rollback procedures
        result = implement_rollback_procedures.test_automation(
            database_type="sqlite",
            database_path=str(temp_sqlite_db),
            backup_location=tmp_path,
        )

        assert result["success"] is True
        assert result["test_results"][0]["passed"] is True

    def test_incident_runbook_workflow(self, tmp_path):
        """Test incident runbook creation and validation workflow."""
        from scripts.change_management import create_incident_runbooks

        # Create runbooks
        result1 = create_incident_runbooks.create_comprehensive_runbooks(
            output_dir=tmp_path
        )
        assert result1["success"] is True

        # Validate runbooks
        result2 = create_incident_runbooks.validate_runbooks(
            output_dir=tmp_path
        )
        assert result2["success"] is True

    def test_complete_validation_workflow(self, tmp_path):
        """Test complete validation workflow."""
        from scripts.change_management import (
            setup_change_management,
            validate_change_procedures,
        )

        # Setup
        setup_change_management.configure_workflows(output_dir=tmp_path)

        # Validate
        result = validate_change_procedures.test_workflows(
            config_dir=tmp_path
        )

        assert result is not None


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_invalid_database_type(self, tmp_path):
        """Test error handling for invalid database type."""
        from scripts.change_management import implement_rollback_procedures

        with pytest.raises(ValueError):
            implement_rollback_procedures.test_automation(
                database_type="invalid_db",
                backup_location=tmp_path,
            )

    def test_missing_required_argument(self):
        """Test error handling for missing required argument."""
        from scripts.change_management import validate_change_procedures

        # Function should handle missing config_dir gracefully
        result = validate_change_procedures.test_workflows()
        assert result is not None
        assert "overall_status" in result

    def test_nonexistent_directory(self):
        """Test error handling for nonexistent directory."""
        from scripts.change_management import setup_change_management

        result = setup_change_management.configure_workflows(
            output_dir="/nonexistent/path/that/does/not/exist"
        )

        assert result["success"] is False
        assert "error" in result


class TestCLIArgumentParsing:
    """Test CLI argument parsing."""

    def test_parse_setup_arguments(self):
        """Test parsing of setup arguments."""
        from scripts.change_management import setup_change_management

        args = setup_change_management.parse_arguments(
            ["--configure-workflows", "--output-dir", "/tmp/test"]
        )

        assert args.configure_workflows is True
        assert args.output_dir == "/tmp/test"

    def test_parse_rollback_arguments(self):
        """Test parsing of rollback arguments."""
        from scripts.change_management import implement_rollback_procedures

        args = implement_rollback_procedures.parse_arguments(
            ["--test-automation", "--database-type", "postgresql"]
        )

        assert args.test_automation is True
        assert args.database_type == "postgresql"

    def test_parse_runbook_arguments(self):
        """Test parsing of runbook arguments."""
        from scripts.change_management import create_incident_runbooks

        args = create_incident_runbooks.parse_arguments(
            ["--comprehensive", "--output-dir", "/tmp/runbooks"]
        )

        assert args.comprehensive is True
        assert args.output_dir == "/tmp/runbooks"

    def test_parse_validation_arguments(self):
        """Test parsing of validation arguments."""
        from scripts.change_management import validate_change_procedures

        args = validate_change_procedures.parse_arguments(
            ["--test-workflows", "--config-dir", "/tmp/config"]
        )

        assert args.test_workflows is True
        assert args.config_dir == "/tmp/config"
