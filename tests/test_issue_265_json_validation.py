# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for JSON Validation Schema functionality - Issue #265."""

import json
from typing import Any, Dict, List

import pytest

# These imports will fail initially (RED phase of TDD)
from violentutf_api.fastapi_app.app.services.config_monitoring import (
    ConfigurationValidator,
    ValidationError,
    ValidationResult,
)


class TestConfigurationValidator:
    """Test ConfigurationValidator class functionality."""

    def test_create_validator_with_schema(self):
        """Test creating validator with JSON schema."""
        # GIVEN: A JSON schema for PostgreSQL configuration
        postgresql_schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string", "minLength": 1},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "database": {"type": "string", "minLength": 1},
                "username": {"type": "string", "minLength": 1}
            },
            "required": ["host", "port", "database", "username"],
            "additionalProperties": False
        }
        
        # WHEN: Creating validator
        validator = ConfigurationValidator(
            schema_name="postgresql",
            schema=postgresql_schema
        )
        
        # THEN: Validator should be created successfully
        assert validator.schema_name == "postgresql"
        assert validator.schema == postgresql_schema

    def test_validate_valid_postgresql_config(self):
        """Test validation of valid PostgreSQL configuration."""
        # GIVEN: Valid PostgreSQL configuration and schema
        postgresql_schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string", "minLength": 1},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "database": {"type": "string", "minLength": 1},
                "username": {"type": "string", "minLength": 1}
            },
            "required": ["host", "port", "database", "username"],
            "additionalProperties": False
        }
        
        valid_config = {
            "host": "postgres",
            "port": 5432,
            "database": "keycloak",
            "username": "keycloak"
        }
        
        validator = ConfigurationValidator("postgresql", postgresql_schema)
        
        # WHEN: Validating configuration
        result = validator.validate(valid_config)
        
        # THEN: Validation should pass
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.severity == "none"

    def test_validate_invalid_postgresql_config_missing_required(self):
        """Test validation of invalid PostgreSQL configuration with missing required fields."""
        # GIVEN: Invalid PostgreSQL configuration (missing required fields)
        postgresql_schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string", "minLength": 1},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "database": {"type": "string", "minLength": 1},
                "username": {"type": "string", "minLength": 1}
            },
            "required": ["host", "port", "database", "username"],
            "additionalProperties": False
        }
        
        invalid_config = {
            "host": "postgres",
            "port": 5432
            # Missing database and username
        }
        
        validator = ConfigurationValidator("postgresql", postgresql_schema)
        
        # WHEN: Validating configuration
        result = validator.validate(invalid_config)
        
        # THEN: Validation should fail
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Missing database and username
        assert result.severity == "critical"  # Missing required fields is critical

    def test_validate_invalid_postgresql_config_wrong_type(self):
        """Test validation of invalid PostgreSQL configuration with wrong data types."""
        # GIVEN: Invalid PostgreSQL configuration (wrong types)
        postgresql_schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string", "minLength": 1},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "database": {"type": "string", "minLength": 1},
                "username": {"type": "string", "minLength": 1}
            },
            "required": ["host", "port", "database", "username"],
            "additionalProperties": False
        }
        
        invalid_config = {
            "host": "postgres",
            "port": "not_a_number",  # Should be integer
            "database": 123,         # Should be string
            "username": "keycloak"
        }
        
        validator = ConfigurationValidator("postgresql", postgresql_schema)
        
        # WHEN: Validating configuration
        result = validator.validate(invalid_config)
        
        # THEN: Validation should fail
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Wrong type for port and database
        assert result.severity == "high"  # Type errors are high severity

    def test_validate_sqlite_configuration(self):
        """Test validation of SQLite configuration."""
        # GIVEN: SQLite configuration schema
        sqlite_schema = {
            "type": "object",
            "properties": {
                "database_url": {
                    "type": "string",
                    "pattern": "^sqlite(\\+aiosqlite)?://"
                },
                "echo": {"type": "boolean"},
                "future": {"type": "boolean"},
                "pool_size": {"type": "integer", "minimum": 1, "maximum": 100}
            },
            "required": ["database_url"],
            "additionalProperties": True
        }
        
        valid_config = {
            "database_url": "sqlite+aiosqlite:///./app_data/violentutf_api.db",
            "echo": True,
            "future": True,
            "pool_size": 20
        }
        
        validator = ConfigurationValidator("sqlite", sqlite_schema)
        
        # WHEN: Validating configuration
        result = validator.validate(valid_config)
        
        # THEN: Validation should pass
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_duckdb_configuration(self):
        """Test validation of DuckDB configuration."""
        # GIVEN: DuckDB configuration schema
        duckdb_schema = {
            "type": "object",
            "properties": {
                "db_path": {
                    "type": "string",
                    "pattern": ".*\\.db$"
                },
                "salt": {"type": "string", "minLength": 8},
                "app_data_dir": {"type": "string", "minLength": 1}
            },
            "required": ["db_path", "salt"],
            "additionalProperties": True
        }
        
        valid_config = {
            "db_path": "/app/app_data/violentutf/pyrit_memory_abc123.db",
            "salt": "default_salt_2025",
            "app_data_dir": "/app/app_data/violentutf"
        }
        
        validator = ConfigurationValidator("duckdb", duckdb_schema)
        
        # WHEN: Validating configuration
        result = validator.validate(valid_config)
        
        # THEN: Validation should pass
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_application_configuration(self):
        """Test validation of application configuration."""
        # GIVEN: Application configuration schema
        app_schema = {
            "type": "object",
            "properties": {
                "PROJECT_NAME": {"type": "string", "minLength": 1},
                "ENVIRONMENT": {
                    "type": "string",
                    "enum": ["development", "staging", "production"]
                },
                "DEBUG": {"type": "boolean"},
                "DATABASE_URL": {
                    "oneOf": [
                        {"type": "null"},
                        {"type": "string", "minLength": 1}
                    ]
                }
            },
            "required": ["PROJECT_NAME", "ENVIRONMENT"],
            "additionalProperties": True
        }
        
        valid_config = {
            "PROJECT_NAME": "ViolentUTF API",
            "ENVIRONMENT": "development",
            "DEBUG": True,
            "DATABASE_URL": None
        }
        
        validator = ConfigurationValidator("application", app_schema)
        
        # WHEN: Validating configuration
        result = validator.validate(valid_config)
        
        # THEN: Validation should pass
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_security_validation_rules(self):
        """Test security-specific validation rules."""
        # GIVEN: Security validation schema
        security_schema = {
            "type": "object",
            "properties": {
                "passwords": {
                    "type": "object",
                    "patternProperties": {
                        ".*_PASSWORD$": {
                            "type": "string",
                            "minLength": 1,  # Allow environment variables
                            "pattern": "^(\\$\\{[A-Z_]+\\}|.{16,})$"  # Either env var or 16+ chars
                        }
                    }
                },
                "secrets": {
                    "type": "object",
                    "patternProperties": {
                        ".*_SECRET.*": {
                            "type": "string",
                            "minLength": 1,  # Allow environment variables
                            "pattern": "^(\\$\\{[A-Z_]+\\}|.{32,})$"  # Either env var or 32+ chars
                        }
                    }
                }
            },
            "additionalProperties": True
        }
        
        # Valid security config (using environment variables)
        valid_security_config = {
            "passwords": {
                "KC_DB_PASSWORD": "${KC_DB_PASSWORD}"  # Environment variable
            },
            "secrets": {
                "JWT_SECRET_KEY": "${JWT_SECRET_KEY}"  # Environment variable
            }
        }
        
        # Invalid security config
        invalid_security_config = {
            "passwords": {
                "KC_DB_PASSWORD": "weak"  # Too short and weak
            },
            "secrets": {
                "JWT_SECRET_KEY": "short"  # Too short
            }
        }
        
        validator = ConfigurationValidator("security", security_schema)
        
        # WHEN: Validating valid security config
        valid_result = validator.validate(valid_security_config)
        
        # Debug: Print errors if validation fails
        if not valid_result.is_valid:
            print(f"Validation errors: {[e.to_dict() for e in valid_result.errors]}")
        
        # THEN: Should pass
        assert valid_result.is_valid is True
        
        # WHEN: Validating invalid security config
        invalid_result = validator.validate(invalid_security_config)
        
        # THEN: Should fail
        assert invalid_result.is_valid is False
        assert invalid_result.severity == "critical"

    def test_nested_configuration_validation(self):
        """Test validation of nested configuration structures."""
        # GIVEN: Nested configuration schema
        nested_schema = {
            "type": "object",
            "properties": {
                "services": {
                    "type": "object",
                    "properties": {
                        "keycloak": {
                            "type": "object",
                            "properties": {
                                "database": {
                                    "type": "object",
                                    "properties": {
                                        "host": {"type": "string"},
                                        "port": {"type": "integer", "minimum": 1, "maximum": 65535}
                                    },
                                    "required": ["host", "port"]
                                }
                            },
                            "required": ["database"]
                        }
                    },
                    "required": ["keycloak"]
                }
            },
            "required": ["services"]
        }
        
        valid_nested_config = {
            "services": {
                "keycloak": {
                    "database": {
                        "host": "postgres",
                        "port": 5432
                    }
                }
            }
        }
        
        validator = ConfigurationValidator("nested", nested_schema)
        
        # WHEN: Validating nested configuration
        result = validator.validate(valid_nested_config)
        
        # THEN: Validation should pass
        assert result.is_valid is True
        assert len(result.errors) == 0


class TestValidationResult:
    """Test ValidationResult class functionality."""

    def test_validation_result_success(self):
        """Test creating successful validation result."""
        # GIVEN: No validation errors
        result = ValidationResult(
            is_valid=True,
            errors=[],
            validated_at=None
        )
        
        # THEN: Result should indicate success
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.severity == "none"
        assert result.error_count == 0

    def test_validation_result_with_errors(self):
        """Test creating validation result with errors."""
        # GIVEN: Validation errors
        errors = [
            ValidationError(
                field_path="host",
                error_type="missing_required",
                message="Required field 'host' is missing",
                severity="critical"
            ),
            ValidationError(
                field_path="port",
                error_type="invalid_type",
                message="Field 'port' must be an integer",
                severity="high"
            )
        ]
        
        result = ValidationResult(
            is_valid=False,
            errors=errors,
            validated_at=None
        )
        
        # THEN: Result should aggregate correctly
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert result.severity == "critical"  # Highest severity among errors
        assert result.error_count == 2

    def test_validation_result_summary(self):
        """Test validation result summary generation."""
        # GIVEN: Validation result with multiple errors
        errors = [
            ValidationError(
                field_path="password",
                error_type="security_violation",
                message="Password does not meet security requirements",
                severity="critical"
            ),
            ValidationError(
                field_path="timeout",
                error_type="invalid_range",
                message="Timeout value is outside valid range",
                severity="medium"
            )
        ]
        
        result = ValidationResult(
            is_valid=False,
            errors=errors,
            validated_at=None
        )
        
        # WHEN: Generating summary
        summary = result.generate_summary()
        
        # THEN: Summary should contain key information
        assert "2 validation errors" in summary
        assert "critical" in summary.lower()
        assert "password" in summary
        assert "timeout" in summary


class TestValidationError:
    """Test ValidationError class functionality."""

    def test_validation_error_creation(self):
        """Test creating validation error."""
        # GIVEN: Error parameters
        error = ValidationError(
            field_path="database.port",
            error_type="invalid_range",
            message="Port must be between 1 and 65535",
            severity="high"
        )
        
        # THEN: Error should be created correctly
        assert error.field_path == "database.port"
        assert error.error_type == "invalid_range"
        assert error.message == "Port must be between 1 and 65535"
        assert error.severity == "high"

    def test_validation_error_serialization(self):
        """Test validation error serialization."""
        # GIVEN: Validation error
        error = ValidationError(
            field_path="config.ssl.enabled",
            error_type="missing_required",
            message="SSL configuration is required in production",
            severity="critical"
        )
        
        # WHEN: Serializing
        serialized = error.to_dict()
        
        # THEN: Serialization should preserve all data
        assert serialized["field_path"] == "config.ssl.enabled"
        assert serialized["error_type"] == "missing_required"
        assert serialized["message"] == "SSL configuration is required in production"
        assert serialized["severity"] == "critical"

    def test_validation_error_severity_priority(self):
        """Test validation error severity priority."""
        # GIVEN: Errors with different severities
        critical_error = ValidationError("field", "type", "message", "critical")
        high_error = ValidationError("field", "type", "message", "high")
        medium_error = ValidationError("field", "type", "message", "medium")
        low_error = ValidationError("field", "type", "message", "low")
        
        # WHEN: Comparing severity priorities
        errors = [low_error, critical_error, medium_error, high_error]
        sorted_errors = sorted(errors, key=lambda x: x.severity_priority(), reverse=True)
        
        # THEN: Critical errors should come first
        assert sorted_errors[0].severity == "critical"
        assert sorted_errors[1].severity == "high"
        assert sorted_errors[2].severity == "medium"
        assert sorted_errors[3].severity == "low"


@pytest.mark.asyncio
class TestConfigurationValidatorIntegration:
    """Test integration between validator and monitoring service."""

    async def test_validator_integration_with_monitoring_service(self):
        """Test validator integration with configuration monitoring service."""
        # GIVEN: Configuration monitoring service with validator
        from violentutf_api.fastapi_app.app.services.config_monitoring import ConfigurationMonitoringService
        
        monitoring_service = ConfigurationMonitoringService()
        
        # Create a baseline with configuration that should be validated
        baseline_id = await monitoring_service.create_baseline(
            service_name="test_validation",
            config_type="postgresql",
            config_path="/test/validation",
            config_data={
                "host": "postgres",
                "port": 5432,
                "database": "test",
                "username": "test"
            }
        )
        
        # WHEN: Validating the baseline configuration
        baseline = await monitoring_service.get_baseline(baseline_id)
        
        postgresql_schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string", "minLength": 1},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "database": {"type": "string", "minLength": 1},
                "username": {"type": "string", "minLength": 1}
            },
            "required": ["host", "port", "database", "username"],
            "additionalProperties": False
        }
        
        validator = ConfigurationValidator("postgresql", postgresql_schema)
        result = validator.validate(baseline.config_data)
        
        # THEN: Validation should pass for valid baseline
        assert result.is_valid is True
        assert len(result.errors) == 0

    async def test_validator_with_invalid_baseline_configuration(self):
        """Test validator with invalid baseline configuration."""
        # GIVEN: Configuration monitoring service
        from violentutf_api.fastapi_app.app.services.config_monitoring import ConfigurationMonitoringService
        
        monitoring_service = ConfigurationMonitoringService()
        
        # Create baseline with invalid configuration
        baseline_id = await monitoring_service.create_baseline(
            service_name="test_invalid",
            config_type="postgresql",
            config_path="/test/invalid",
            config_data={
                "host": "postgres",
                # Missing required fields: port, database, username
            }
        )
        
        # WHEN: Validating the invalid baseline
        baseline = await monitoring_service.get_baseline(baseline_id)
        
        postgresql_schema = {
            "type": "object",
            "properties": {
                "host": {"type": "string", "minLength": 1},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "database": {"type": "string", "minLength": 1},
                "username": {"type": "string", "minLength": 1}
            },
            "required": ["host", "port", "database", "username"],
            "additionalProperties": False
        }
        
        validator = ConfigurationValidator("postgresql", postgresql_schema)
        result = validator.validate(baseline.config_data)
        
        # THEN: Validation should fail
        assert result.is_valid is False
        assert len(result.errors) >= 3  # Missing port, database, username
        assert result.severity == "critical"