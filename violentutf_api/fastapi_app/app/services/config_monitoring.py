# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Configuration Monitoring Service for Issue #265.

This module implements database configuration baseline and drift detection
for all ViolentUTF database configurations including PostgreSQL, SQLite, and DuckDB.
"""

import gzip
import hashlib
import json
import logging
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
import jsonschema
from jsonschema import ValidationError as JsonSchemaValidationError
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Database models for configuration baselines
Base = declarative_base()


class ConfigurationBaselineModel(Base):
    """Database model for configuration baselines."""

    __tablename__ = "config_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    baseline_id = Column(String(100), unique=True, nullable=False)
    service_name = Column(String(100), nullable=False)
    config_type = Column(String(50), nullable=False)
    config_path = Column(String(500), nullable=False)
    baseline_hash = Column(String(64), nullable=False)
    baseline_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ConfigurationDriftHistoryModel(Base):
    """Database model for configuration drift history."""

    __tablename__ = "config_drift_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    baseline_id = Column(String(100), nullable=False)
    drift_type = Column(String(50), nullable=False)
    field_path = Column(String(500))
    old_value = Column(Text)
    new_value = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow)
    severity = Column(String(20), default="medium")


class DriftChange:
    """Represents a single configuration drift change."""

    def __init__(
        self,
        change_type: str,
        field_path: str,
        old_value: Any,  # noqa: ANN401
        new_value: Any,  # noqa: ANN401
        severity: str = "medium",  # noqa: ANN401
    ) -> None:
        """Initialize drift change.

        Args:
            change_type: Type of change (added, removed, modified)
            field_path: Path to the changed field (dot notation for nested)
            old_value: Previous value (None for added)
            new_value: New value (None for removed)
            severity: Severity level (critical, high, medium, low)
        """
        self.change_type = change_type
        self.field_path = field_path
        self.old_value = old_value
        self.new_value = new_value
        self.severity = severity
        self.detected_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "change_type": self.change_type,
            "field_path": self.field_path,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "severity": self.severity,
            "detected_at": self.detected_at.isoformat(),
        }

    def severity_priority(self) -> int:
        """Get numeric priority for severity (higher = more critical)."""
        severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
        return severity_map.get(self.severity, 0)


class DriftResult:
    """Represents the result of a drift detection operation."""

    def __init__(self, has_drift: bool, changes: List[DriftChange], detected_at: Optional[datetime] = None) -> None:
        """Initialize drift result.

        Args:
            has_drift: Whether any drift was detected
            changes: List of detected changes
            detected_at: When the detection was performed
        """
        self.has_drift = has_drift
        self.changes = changes
        self.detected_at = detected_at or datetime.utcnow()

    @property
    def severity(self) -> str:
        """Return the highest severity level among all changes."""
        if not self.changes:
            return "none"

        severities = [change.severity for change in self.changes]
        if "critical" in severities:
            return "critical"
        elif "high" in severities:
            return "high"
        elif "medium" in severities:
            return "medium"
        elif "low" in severities:
            return "low"
        return "none"

    @property
    def change_count(self) -> int:
        """Get total number of changes."""
        return len(self.changes)

    @property
    def has_critical_changes(self) -> bool:
        """Check if any changes are critical."""
        return any(change.severity == "critical" for change in self.changes)

    def generate_summary(self) -> str:
        """Generate a human-readable summary of the drift."""
        if not self.has_drift:
            return "No configuration drift detected."

        summary_parts = [f"{self.change_count} changes detected", f"Overall severity: {self.severity}"]

        # Add details about critical changes
        critical_changes = [c for c in self.changes if c.severity == "critical"]
        if critical_changes:
            critical_fields = [c.field_path for c in critical_changes]
            summary_parts.append(f"Critical changes in: {', '.join(critical_fields)}")

        # Add details about all changes
        if len(self.changes) <= 5:  # Only for small numbers of changes
            all_fields = [c.field_path for c in self.changes]
            summary_parts.append(f"Changed fields: {', '.join(all_fields)}")

        return ". ".join(summary_parts) + "."


class ValidationError:
    """Represents a single configuration validation error."""

    def __init__(self, field_path: str, error_type: str, message: str, severity: str = "medium") -> None:
        """Initialize validation error.

        Args:
            field_path: Path to the field with error (dot notation for nested)
            error_type: Type of validation error (missing_required, invalid_type, etc.)
            message: Human-readable error message
            severity: Error severity (critical, high, medium, low)
        """
        self.field_path = field_path
        self.error_type = error_type
        self.message = message
        self.severity = severity
        self.detected_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "field_path": self.field_path,
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity,
            "detected_at": self.detected_at.isoformat(),
        }

    def severity_priority(self) -> int:
        """Get numeric priority for severity (higher = more critical)."""
        severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
        return severity_map.get(self.severity, 0)


class ValidationResult:
    """Represents the result of a configuration validation operation."""

    def __init__(self, is_valid: bool, errors: List[ValidationError], validated_at: Optional[datetime] = None) -> None:
        """Initialize validation result.

        Args:
            is_valid: Whether the configuration is valid
            errors: List of validation errors
            validated_at: When the validation was performed
        """
        self.is_valid = is_valid
        self.errors = errors
        self.validated_at = validated_at or datetime.utcnow()

    @property
    def severity(self) -> str:
        """Return the highest severity level among all errors."""
        if not self.errors:
            return "none"

        severities = [error.severity for error in self.errors]
        if "critical" in severities:
            return "critical"
        elif "high" in severities:
            return "high"
        elif "medium" in severities:
            return "medium"
        elif "low" in severities:
            return "low"
        return "none"

    @property
    def error_count(self) -> int:
        """Get total number of errors."""
        return len(self.errors)

    @property
    def has_critical_errors(self) -> bool:
        """Check if any errors are critical."""
        return any(error.severity == "critical" for error in self.errors)

    def generate_summary(self) -> str:
        """Generate a human-readable summary of the validation result."""
        if self.is_valid:
            return "Configuration validation passed successfully."

        summary_parts = [f"{self.error_count} validation errors detected", f"Overall severity: {self.severity}"]

        # Add details about critical errors
        critical_errors = [e for e in self.errors if e.severity == "critical"]
        if critical_errors:
            critical_fields = [e.field_path for e in critical_errors]
            summary_parts.append(f"Critical errors in: {', '.join(critical_fields)}")

        # Add details about all errors (if not too many)
        if len(self.errors) <= 5:
            all_fields = [e.field_path for e in self.errors]
            summary_parts.append(f"Error fields: {', '.join(all_fields)}")

        return ". ".join(summary_parts) + "."


class ConfigurationValidator:
    """Validates configuration data against JSON schemas."""

    def __init__(self, schema_name: str, schema: Dict[str, Any]) -> None:
        """Initialize configuration validator.

        Args:
            schema_name: Name of the schema (postgresql, sqlite, etc.)
            schema: JSON schema for validation
        """
        self.schema_name = schema_name
        self.schema = schema
        self._validator = jsonschema.Draft7Validator(schema)

    def validate(self, config_data: Dict[str, Any]) -> ValidationResult:
        """Validate configuration data against the schema.

        Args:
            config_data: Configuration data to validate

        Returns:
            ValidationResult containing validation status and errors
        """
        errors = []

        try:
            # Validate against JSON schema
            schema_errors = list(self._validator.iter_errors(config_data))

            for schema_error in schema_errors:
                # Convert jsonschema error to our ValidationError
                field_path = (
                    ".".join(str(p) for p in schema_error.absolute_path) if schema_error.absolute_path else "root"
                )

                # Determine error type and severity
                error_type = self._get_error_type(schema_error)
                severity = self._get_error_severity(schema_error, field_path)

                validation_error = ValidationError(
                    field_path=field_path, error_type=error_type, message=schema_error.message, severity=severity
                )
                errors.append(validation_error)

            # Additional custom validations
            custom_errors = self._perform_custom_validations(config_data)
            errors.extend(custom_errors)

        except Exception as e:
            # Handle unexpected validation errors
            logger.error("Unexpected error during validation: %s", str(e))
            errors.append(
                ValidationError(
                    field_path="validation",
                    error_type="validation_error",
                    message=f"Validation failed with error: {str(e)}",
                    severity="high",
                )
            )

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors)

    def _get_error_type(self, schema_error: JsonSchemaValidationError) -> str:
        """Determine error type from jsonschema error."""
        if schema_error.validator == "required":
            return "missing_required"
        elif schema_error.validator == "type":
            return "invalid_type"
        elif schema_error.validator in ["minimum", "maximum", "minLength", "maxLength"]:
            return "invalid_range"
        elif schema_error.validator == "pattern":
            return "invalid_format"
        elif schema_error.validator == "enum":
            return "invalid_value"
        elif schema_error.validator == "additionalProperties":
            return "unexpected_property"
        else:
            return "schema_violation"

    def _get_error_severity(self, schema_error: JsonSchemaValidationError, field_path: str) -> str:
        """Determine error severity based on field and error type."""
        field_lower = field_path.lower()

        # Critical: Security-related fields or missing required fields
        if schema_error.validator == "required" or any(
            key in field_lower for key in ["password", "secret", "key", "token", "credential"]
        ):
            return "critical"

        # High: Type errors or range violations on important fields
        if schema_error.validator in ["type", "minimum", "maximum"] or any(
            key in field_lower for key in ["port", "timeout", "host", "database"]
        ):
            return "high"

        # Medium: Format or enum violations
        if schema_error.validator in ["pattern", "enum", "format"]:
            return "medium"

        # Low: Everything else
        return "low"

    def _perform_custom_validations(self, config_data: Dict[str, Any]) -> List[ValidationError]:
        """Perform additional custom validations beyond JSON schema."""
        errors = []

        # Security validations
        errors.extend(self._validate_security_requirements(config_data))

        # Performance validations
        errors.extend(self._validate_performance_requirements(config_data))

        return errors

    def _validate_security_requirements(self, config_data: Dict[str, Any]) -> List[ValidationError]:
        """Validate security-specific requirements."""
        errors = []

        # Check for hardcoded passwords or secrets
        self._check_for_hardcoded_secrets(config_data, "", errors)

        # Check password strength requirements
        self._check_password_strength(config_data, "", errors)

        return errors

    def _check_for_hardcoded_secrets(
        self, data: Union[Dict[str, Any], Any], path: str, errors: List[ValidationError]
    ) -> None:
        """Recursively check for hardcoded secrets in configuration."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                # Check if this looks like a secret field with a hardcoded value
                if (
                    any(secret_key in key.lower() for secret_key in ["password", "secret", "key", "token"])
                    and isinstance(value, str)
                    and value
                    and not value.startswith("${")  # Not an environment variable
                    and not value.startswith("file:")
                ):  # Not a file reference

                    errors.append(
                        ValidationError(
                            field_path=current_path,
                            error_type="hardcoded_secret",
                            message=(
                                f"Hardcoded secret detected in '{current_path}'. " "Use environment variables instead."
                            ),
                            severity="critical",
                        )
                    )

                self._check_for_hardcoded_secrets(value, current_path, errors)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                self._check_for_hardcoded_secrets(item, current_path, errors)

    def _check_password_strength(
        self, data: Union[Dict[str, Any], Any], path: str, errors: List[ValidationError]
    ) -> None:
        """Check password strength requirements."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if (
                    "password" in key.lower()
                    and isinstance(value, str)
                    and value
                    and not value.startswith("${")
                    and not value.startswith("file:")
                ):

                    # Check minimum length
                    if len(value) < 16:
                        errors.append(
                            ValidationError(
                                field_path=current_path,
                                error_type="weak_password",
                                message=f"Password in '{current_path}' must be at least 16 characters long.",
                                severity="critical",
                            )
                        )

                    # Check for complexity (basic check)
                    has_upper = any(c.isupper() for c in value)
                    has_lower = any(c.islower() for c in value)
                    has_digit = any(c.isdigit() for c in value)
                    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in value)

                    if not all([has_upper, has_lower, has_digit, has_special]):
                        errors.append(
                            ValidationError(
                                field_path=current_path,
                                error_type="weak_password",
                                message=(
                                    f"Password in '{current_path}' must contain uppercase, "
                                    "lowercase, digit, and special characters."
                                ),
                                severity="high",
                            )
                        )

                self._check_password_strength(value, current_path, errors)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                self._check_password_strength(item, current_path, errors)

    def _validate_performance_requirements(self, config_data: Dict[str, Any]) -> List[ValidationError]:
        """Validate performance-related requirements."""
        errors = []

        # Check connection pool sizes
        self._check_connection_pools(config_data, "", errors)

        # Check timeout values
        self._check_timeout_values(config_data, "", errors)

        return errors

    def _check_connection_pools(
        self, data: Union[Dict[str, Any], Any], path: str, errors: List[ValidationError]
    ) -> None:
        """Check connection pool configuration."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if "pool_size" in key.lower() and isinstance(value, int):
                    if value < 1:
                        errors.append(
                            ValidationError(
                                field_path=current_path,
                                error_type="invalid_pool_size",
                                message=f"Pool size in '{current_path}' must be at least 1.",
                                severity="high",
                            )
                        )
                    elif value > 100:
                        errors.append(
                            ValidationError(
                                field_path=current_path,
                                error_type="invalid_pool_size",
                                message=(
                                    f"Pool size in '{current_path}' is unusually high ({value}). "
                                    "Consider reducing to improve performance."
                                ),
                                severity="medium",
                            )
                        )

                self._check_connection_pools(value, current_path, errors)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                self._check_connection_pools(item, current_path, errors)

    def _check_timeout_values(self, data: Union[Dict[str, Any], Any], path: str, errors: List[ValidationError]) -> None:
        """Check timeout configuration values."""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if "timeout" in key.lower() and isinstance(value, (int, float)):
                    if value <= 0:
                        errors.append(
                            ValidationError(
                                field_path=current_path,
                                error_type="invalid_timeout",
                                message=f"Timeout in '{current_path}' must be greater than 0.",
                                severity="high",
                            )
                        )
                    elif value > 300:  # 5 minutes
                        errors.append(
                            ValidationError(
                                field_path=current_path,
                                error_type="long_timeout",
                                message=(
                                    f"Timeout in '{current_path}' is very long ({value}s). "
                                    "Consider reducing for better responsiveness."
                                ),
                                severity="medium",
                            )
                        )

                self._check_timeout_values(value, current_path, errors)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                self._check_timeout_values(item, current_path, errors)


class ConfigurationBaseline:
    """Represents a configuration baseline for drift detection."""

    def __init__(self, service_name: str, config_type: str, config_path: str, config_data: Dict[str, Any]) -> None:
        """Initialize configuration baseline.

        Args:
            service_name: Name of the service (e.g., keycloak, fastapi)
            config_type: Type of configuration (postgresql, sqlite, duckdb, application)
            config_path: Path to the configuration file
            config_data: The configuration data as a dictionary

        Raises:
            ValueError: If any required parameter is empty or invalid
        """
        if not service_name:
            raise ValueError("Service name cannot be empty")
        if not config_type:
            raise ValueError("Config type cannot be empty")
        if not config_path:
            raise ValueError("Config path cannot be empty")
        if not config_data:
            raise ValueError("Config data cannot be empty")

        self.baseline_id = str(uuid.uuid4())
        self.service_name = service_name
        self.config_type = config_type
        self.config_path = config_path
        self.config_data = config_data
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        # Generate hash of configuration data for quick comparison
        self.baseline_hash = self._generate_hash(config_data)

    def _generate_hash(self, data: Dict[str, Any]) -> str:
        """Generate SHA-256 hash of configuration data."""
        # Sort keys for consistent hashing
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "baseline_id": self.baseline_id,
            "service_name": self.service_name,
            "config_type": self.config_type,
            "config_path": self.config_path,
            "config_data": self.config_data,
            "baseline_hash": self.baseline_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls: type["ConfigurationBaseline"], data: Dict[str, Any]) -> "ConfigurationBaseline":
        """Create baseline from dictionary."""
        baseline = cls(
            service_name=data["service_name"],
            config_type=data["config_type"],
            config_path=data["config_path"],
            config_data=data["config_data"],
        )
        baseline.baseline_id = data["baseline_id"]
        baseline.baseline_hash = data["baseline_hash"]
        baseline.created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        baseline.updated_at = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        return baseline


class DriftDetector:
    """Detects configuration drift between baseline and current configurations."""

    # Security-sensitive configuration keys that require critical severity
    CRITICAL_KEYS = {
        "password",
        "secret",
        "key",
        "token",
        "credential",
        "auth",
        "KC_DB_PASSWORD",
        "SECRET_KEY",
        "JWT_SECRET_KEY",
        "API_KEY",
        "KEYCLOAK_CLIENT_SECRET",
        "APISIX_ADMIN_KEY",
    }

    # Performance-impacting configuration keys that require high severity
    HIGH_IMPACT_KEYS = {
        "port",
        "timeout",
        "pool_size",
        "max_connections",
        "memory",
        "KC_DB_URL_PORT",
        "DATABASE_URL",
        "connection",
    }

    # Functional configuration keys that require medium severity
    MEDIUM_IMPACT_KEYS = {"host", "hostname", "debug", "environment", "enabled", "KC_HOSTNAME", "DEBUG", "ENVIRONMENT"}

    def detect_drift(self, baseline_config: Dict[str, Any], current_config: Dict[str, Any]) -> DriftResult:
        """Detect drift between baseline and current configuration.

        Args:
            baseline_config: The baseline configuration
            current_config: The current configuration

        Returns:
            DriftResult containing detected changes
        """
        changes = []

        # Detect changes using recursive comparison
        self._detect_changes_recursive(baseline_config, current_config, "", changes)

        # Calculate overall result
        has_drift = len(changes) > 0

        return DriftResult(has_drift=has_drift, changes=changes)

    def _detect_changes_recursive(
        self, baseline: Dict[str, Any], current: Dict[str, Any], path_prefix: str, changes: List[DriftChange]
    ) -> None:
        """Recursively detect changes in nested dictionaries."""
        # Check for removed keys
        for key in baseline:
            current_path = f"{path_prefix}.{key}" if path_prefix else key

            if key not in current:
                # Key was removed
                severity = self.classify_severity(key, baseline[key], None)
                changes.append(
                    DriftChange(
                        change_type="removed",
                        field_path=current_path,
                        old_value=baseline[key],
                        new_value=None,
                        severity=severity,
                    )
                )
            elif isinstance(baseline[key], dict) and isinstance(current[key], dict):
                # Recursively check nested dictionaries
                self._detect_changes_recursive(baseline[key], current[key], current_path, changes)
            elif baseline[key] != current[key]:
                # Value was modified
                severity = self.classify_severity(key, baseline[key], current[key])
                changes.append(
                    DriftChange(
                        change_type="modified",
                        field_path=current_path,
                        old_value=baseline[key],
                        new_value=current[key],
                        severity=severity,
                    )
                )

        # Check for added keys
        for key in current:
            current_path = f"{path_prefix}.{key}" if path_prefix else key

            if key not in baseline:
                # Key was added
                severity = self.classify_severity(key, None, current[key])
                changes.append(
                    DriftChange(
                        change_type="added",
                        field_path=current_path,
                        old_value=None,
                        new_value=current[key],
                        severity=severity,
                    )
                )

    def classify_severity(self, field_name: str, old_value: Any, new_value: Any) -> str:  # noqa: ANN401
        """Classify the severity of a configuration change.

        Args:
            field_name: Name of the changed field
            old_value: Previous value
            new_value: New value

        Returns:
            Severity level: critical, high, medium, or low
        """
        field_lower = field_name.lower()

        # Critical: Security-related changes
        if any(key in field_lower for key in self.CRITICAL_KEYS):
            return "critical"

        # High: Performance-impacting changes
        if any(key in field_lower for key in self.HIGH_IMPACT_KEYS):
            return "high"

        # Medium: Functional changes
        if any(key in field_lower for key in self.MEDIUM_IMPACT_KEYS):
            return "medium"

        # Low: Everything else (documentation, comments, etc.)
        return "low"


class ConfigurationMonitoringService:
    """Service for managing configuration baselines and drift detection."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        """Initialize the configuration monitoring service.

        Args:
            database_url: Database URL for storing baselines
        """
        self.database_url = database_url or "sqlite:///:memory:"  # Use in-memory DB for tests
        self.engine = create_engine(self.database_url)
        Base.metadata.create_all(self.engine)

        self.Session = sessionmaker(bind=self.engine)
        self.drift_detector = DriftDetector()

        # In-memory store for testing (will be replaced with database)
        self._baselines: Dict[str, ConfigurationBaseline] = {}

    async def create_baseline(
        self, service_name: str, config_type: str, config_path: str, config_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new configuration baseline.

        Args:
            service_name: Name of the service
            config_type: Type of configuration
            config_path: Path to configuration file
            config_data: Configuration data (if None, will be extracted from path)

        Returns:
            The baseline ID
        """
        if config_data is None:
            config_data = await self._extract_config_data(config_path, config_type)

        baseline = ConfigurationBaseline(
            service_name=service_name, config_type=config_type, config_path=config_path, config_data=config_data
        )

        # Store in memory for testing
        self._baselines[baseline.baseline_id] = baseline

        # Store in database
        session = self.Session()
        try:
            db_baseline = ConfigurationBaselineModel(
                baseline_id=baseline.baseline_id,
                service_name=baseline.service_name,
                config_type=baseline.config_type,
                config_path=baseline.config_path,
                baseline_hash=baseline.baseline_hash,
                baseline_content=json.dumps(baseline.config_data),
            )
            session.add(db_baseline)
            session.commit()
        finally:
            session.close()

        logger.info(
            "Created configuration baseline %s for service %s (%s)", baseline.baseline_id, service_name, config_type
        )

        return baseline.baseline_id

    async def get_baseline(self, baseline_id: str) -> Optional[ConfigurationBaseline]:
        """Get configuration baseline by ID.

        Args:
            baseline_id: The baseline ID

        Returns:
            The configuration baseline or None if not found
        """
        # Check in-memory store first
        if baseline_id in self._baselines:
            return self._baselines[baseline_id]

        # Check database
        session = self.Session()
        try:
            db_baseline = session.query(ConfigurationBaselineModel).filter_by(baseline_id=baseline_id).first()

            if db_baseline:
                config_data = json.loads(db_baseline.baseline_content)
                baseline = ConfigurationBaseline(
                    service_name=db_baseline.service_name,
                    config_type=db_baseline.config_type,
                    config_path=db_baseline.config_path,
                    config_data=config_data,
                )
                baseline.baseline_id = db_baseline.baseline_id
                baseline.baseline_hash = db_baseline.baseline_hash
                baseline.created_at = db_baseline.created_at
                baseline.updated_at = db_baseline.updated_at

                # Cache in memory
                self._baselines[baseline_id] = baseline
                return baseline
        finally:
            session.close()

        return None

    async def list_baselines_for_service(self, service_name: str) -> List[ConfigurationBaseline]:
        """List all baselines for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            List of configuration baselines
        """
        # Filter in-memory baselines
        service_baselines = [baseline for baseline in self._baselines.values() if baseline.service_name == service_name]

        # Also check database
        session = self.Session()
        try:
            db_baselines = session.query(ConfigurationBaselineModel).filter_by(service_name=service_name).all()

            for db_baseline in db_baselines:
                if db_baseline.baseline_id not in self._baselines:
                    config_data = json.loads(db_baseline.baseline_content)
                    baseline = ConfigurationBaseline(
                        service_name=db_baseline.service_name,
                        config_type=db_baseline.config_type,
                        config_path=db_baseline.config_path,
                        config_data=config_data,
                    )
                    baseline.baseline_id = db_baseline.baseline_id
                    baseline.baseline_hash = db_baseline.baseline_hash
                    baseline.created_at = db_baseline.created_at
                    baseline.updated_at = db_baseline.updated_at

                    service_baselines.append(baseline)
                    self._baselines[baseline.baseline_id] = baseline
        finally:
            session.close()

        return service_baselines

    async def update_baseline(self, baseline_id: str, new_config_data: Dict[str, Any]) -> bool:
        """Update an existing baseline with new configuration data.

        Args:
            baseline_id: The baseline ID
            new_config_data: New configuration data

        Returns:
            True if update was successful, False otherwise
        """
        baseline = await self.get_baseline(baseline_id)
        if not baseline:
            return False

        # Update baseline
        baseline.config_data = new_config_data
        # Generate new hash using the same method that created the baseline originally
        hasher = hashlib.sha256()
        hasher.update(json.dumps(new_config_data, sort_keys=True).encode("utf-8"))
        baseline.baseline_hash = hasher.hexdigest()
        baseline.updated_at = datetime.utcnow()

        # Update in database
        session = self.Session()
        try:
            db_baseline = session.query(ConfigurationBaselineModel).filter_by(baseline_id=baseline_id).first()

            if db_baseline:
                db_baseline.baseline_hash = baseline.baseline_hash
                db_baseline.baseline_content = json.dumps(new_config_data)
                db_baseline.updated_at = baseline.updated_at
                session.commit()
                return True
        finally:
            session.close()

        return False

    async def delete_baseline(self, baseline_id: str) -> bool:
        """Delete a configuration baseline.

        Args:
            baseline_id: The baseline ID

        Returns:
            True if deletion was successful, False otherwise
        """
        # Remove from memory
        if baseline_id in self._baselines:
            del self._baselines[baseline_id]

        # Remove from database
        session = self.Session()
        try:
            deleted_count = session.query(ConfigurationBaselineModel).filter_by(baseline_id=baseline_id).delete()
            session.commit()
            return deleted_count > 0
        finally:
            session.close()

    async def get_baseline_statistics(self) -> Dict[str, Any]:
        """Get statistics about configuration baselines.

        Returns:
            Dictionary containing baseline statistics
        """
        session = self.Session()
        try:
            total_baselines = session.query(ConfigurationBaselineModel).count()

            # Get unique services
            services = session.query(ConfigurationBaselineModel.service_name).distinct().all()
            services_count = len(services)

            # Get config types distribution
            config_types = session.query(ConfigurationBaselineModel.config_type).distinct().all()
            config_types_list = [ct[0] for ct in config_types]

            return {
                "total_baselines": total_baselines,
                "services_count": services_count,
                "config_types": config_types_list,
                "in_memory_baselines": len(self._baselines),
            }
        finally:
            session.close()

    async def _extract_config_data(self, config_path: str, config_type: str) -> Dict[str, Any]:
        """Extract configuration data from a file path.

        Args:
            config_path: Path to configuration file
            config_type: Type of configuration

        Returns:
            Extracted configuration data
        """
        # For now, return empty dict - this will be implemented
        # to actually read configuration files in a future iteration
        logger.warning("Configuration extraction not yet implemented for %s (%s)", config_path, config_type)
        return {}


class AlertRule:
    """Represents an alert rule for configuration drift detection."""

    def __init__(
        self,
        rule_id: str,
        name: str,
        description: str,
        severity_threshold: str,
        service_filter: Optional[List[str]] = None,
        enabled: bool = True,
        channel_ids: Optional[List[str]] = None,
    ) -> None:
        """Initialize alert rule.

        Args:
            rule_id: Unique identifier for the rule
            name: Human-readable name
            description: Description of what triggers this rule
            severity_threshold: Minimum severity to trigger (critical, high, medium, low)
            service_filter: List of services to monitor (None = all services)
            enabled: Whether the rule is active
            channel_ids: List of channel IDs to send alerts to
        """
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity_threshold = severity_threshold
        self.service_filter = service_filter or []
        self.enabled = enabled
        self.channel_ids = channel_ids or []
        self.created_at = datetime.utcnow()

    def matches_drift(self, drift_result: DriftResult, service_name: str) -> bool:
        """Check if drift result matches this alert rule.

        Args:
            drift_result: The drift detection result
            service_name: Name of the service

        Returns:
            True if the rule should trigger an alert
        """
        if not self.enabled:
            return False

        # Check service filter
        if self.service_filter and service_name not in self.service_filter:
            return False

        # Check severity threshold
        if not self._meets_severity_threshold(drift_result.severity):
            return False

        return True

    def _meets_severity_threshold(self, severity: str) -> bool:
        """Check if severity meets the threshold."""
        severity_levels = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
        threshold_level = severity_levels.get(self.severity_threshold, 0)
        actual_level = severity_levels.get(severity, 0)
        return actual_level >= threshold_level

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "severity_threshold": self.severity_threshold,
            "service_filter": self.service_filter,
            "enabled": self.enabled,
            "channel_ids": self.channel_ids,
            "created_at": self.created_at.isoformat(),
        }


class AlertChannel:
    """Represents a notification channel for alerts."""

    def __init__(
        self, channel_id: str, name: str, channel_type: str, configuration: Dict[str, Any], enabled: bool = True
    ) -> None:
        """Initialize alert channel.

        Args:
            channel_id: Unique identifier for the channel
            name: Human-readable name
            channel_type: Type of channel (email, slack, webhook, etc.)
            configuration: Channel-specific configuration
            enabled: Whether the channel is active
        """
        self.channel_id = channel_id
        self.name = name
        self.channel_type = channel_type
        self.configuration = configuration
        self.enabled = enabled
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "channel_id": self.channel_id,
            "name": self.name,
            "channel_type": self.channel_type,
            "configuration": self.configuration,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
        }


class DriftAlert:
    """Represents a configuration drift alert."""

    def __init__(
        self,
        alert_id: str,
        service_name: str,
        baseline_id: str,
        drift_result: DriftResult,
        rule_id: str,
        triggered_at: Optional[datetime] = None,
    ) -> None:
        """Initialize drift alert.

        Args:
            alert_id: Unique identifier for the alert
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            drift_result: The drift detection result
            rule_id: ID of the rule that triggered this alert
            triggered_at: When the alert was triggered
        """
        self.alert_id = alert_id
        self.service_name = service_name
        self.baseline_id = baseline_id
        self.drift_result = drift_result
        self.rule_id = rule_id
        self.triggered_at = triggered_at or datetime.utcnow()

    @property
    def severity(self) -> str:
        """Get alert severity from drift result."""
        return self.drift_result.severity

    @property
    def change_count(self) -> int:
        """Get number of changes from drift result."""
        return self.drift_result.change_count

    def generate_title(self) -> str:
        """Generate alert title."""
        return (
            f"Configuration Drift Alert - {self.service_name} ({self.severity.upper()}) - {self.change_count} changes"
        )

    def generate_message(self) -> str:
        """Generate detailed alert message."""
        lines = [
            f"Configuration drift detected for service: {self.service_name}",
            f"Baseline ID: {self.baseline_id}",
            f"Severity: {self.severity.upper()}",
            f"Number of changes: {self.change_count}",
            f"Detected at: {self.triggered_at.isoformat()}",
            "",
            "Changes:",
        ]

        for change in self.drift_result.changes:
            lines.append(f"  - {change.change_type.upper()}: {change.field_path}")
            if change.old_value is not None:
                lines.append(f"    Old: {change.old_value}")
            if change.new_value is not None:
                lines.append(f"    New: {change.new_value}")
            lines.append(f"    Severity: {change.severity}")
            lines.append("")

        lines.append(f"Summary: {self.drift_result.generate_summary()}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "alert_id": self.alert_id,
            "service_name": self.service_name,
            "baseline_id": self.baseline_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "change_count": self.change_count,
            "triggered_at": self.triggered_at.isoformat(),
            "drift_result": {
                "has_drift": self.drift_result.has_drift,
                "changes": [change.to_dict() for change in self.drift_result.changes],
                "detected_at": self.drift_result.detected_at.isoformat(),
            },
        }


class NotificationResult:
    """Represents the result of sending a notification."""

    def __init__(self, channel_id: str, success: bool, message: str, sent_at: Optional[datetime] = None) -> None:
        """Initialize notification result.

        Args:
            channel_id: ID of the channel the notification was sent to
            success: Whether the notification was sent successfully
            message: Success or error message
            sent_at: When the notification was sent
        """
        self.channel_id = channel_id
        self.success = success
        self.message = message
        self.sent_at = sent_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "channel_id": self.channel_id,
            "success": self.success,
            "message": self.message,
            "sent_at": self.sent_at.isoformat(),
        }


class AlertManager:
    """Manages alert rules, channels, and notification sending."""

    def __init__(self) -> None:
        """Initialize alert manager."""
        self.rules: Dict[str, AlertRule] = {}
        self.channels: Dict[str, AlertChannel] = {}
        self._alert_history: List[DriftAlert] = []

    async def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule.

        Args:
            rule: The alert rule to add
        """
        self.rules[rule.rule_id] = rule
        logger.info("Added alert rule: %s", rule.rule_id)

    async def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule.

        Args:
            rule_id: ID of the rule to remove

        Returns:
            True if rule was removed, False if not found
        """
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info("Removed alert rule: %s", rule_id)
            return True
        return False

    async def add_channel(self, channel: AlertChannel) -> None:
        """Add an alert channel.

        Args:
            channel: The alert channel to add
        """
        self.channels[channel.channel_id] = channel
        logger.info("Added alert channel: %s (%s)", channel.channel_id, channel.channel_type)

    async def remove_channel(self, channel_id: str) -> bool:
        """Remove an alert channel.

        Args:
            channel_id: ID of the channel to remove

        Returns:
            True if channel was removed, False if not found
        """
        if channel_id in self.channels:
            del self.channels[channel_id]
            logger.info("Removed alert channel: %s", channel_id)
            return True
        return False

    async def process_drift_detection(
        self, service_name: str, baseline_id: str, drift_result: DriftResult
    ) -> List[NotificationResult]:
        """Process drift detection and send alerts if rules match.

        Args:
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            drift_result: The drift detection result

        Returns:
            List of notification results
        """
        results = []

        # Check each rule to see if it matches
        for rule in self.rules.values():
            if rule.matches_drift(drift_result, service_name):
                # Create alert
                alert = DriftAlert(
                    alert_id=str(uuid.uuid4()),
                    service_name=service_name,
                    baseline_id=baseline_id,
                    drift_result=drift_result,
                    rule_id=rule.rule_id,
                )

                # Store alert in history
                self._alert_history.append(alert)

                logger.info(
                    "Alert triggered: %s for service %s (severity: %s)", alert.alert_id, service_name, alert.severity
                )

                # Send notifications to all channels configured for this rule
                for channel_id in rule.channel_ids:
                    if channel_id in self.channels:
                        channel = self.channels[channel_id]
                        if channel.enabled:
                            try:
                                result = await self._send_notification(channel, alert)
                                results.append(result)
                            except Exception as e:
                                logger.error("Failed to send notification to channel %s: %s", channel_id, str(e))
                                results.append(
                                    NotificationResult(
                                        channel_id=channel_id,
                                        success=False,
                                        message=f"Failed to send notification: {str(e)}",
                                    )
                                )
                        else:
                            logger.warning("Channel %s is disabled", channel_id)
                    else:
                        logger.warning("Channel %s not found", channel_id)

        return results

    async def _send_notification(self, channel: AlertChannel, alert: DriftAlert) -> NotificationResult:
        """Send notification through the specified channel.

        Args:
            channel: The alert channel
            alert: The drift alert

        Returns:
            NotificationResult indicating success or failure
        """
        try:
            if channel.channel_type == "email":
                return await self._send_email_notification(channel, alert)
            elif channel.channel_type == "slack":
                return await self._send_slack_notification(channel, alert)
            elif channel.channel_type == "webhook":
                return await self._send_webhook_notification(channel, alert)
            elif channel.channel_type == "test":
                # Test channel for unit tests
                return NotificationResult(
                    channel_id=channel.channel_id, success=True, message="Test notification sent successfully"
                )
            else:
                return NotificationResult(
                    channel_id=channel.channel_id,
                    success=False,
                    message=f"Unsupported channel type: {channel.channel_type}",
                )
        except Exception as e:
            logger.error("Error sending notification: %s", str(e))
            return NotificationResult(
                channel_id=channel.channel_id, success=False, message=f"Error sending notification: {str(e)}"
            )

    async def _send_email_notification(self, channel: AlertChannel, alert: DriftAlert) -> NotificationResult:
        """Send email notification.

        Args:
            channel: Email channel configuration
            alert: The drift alert

        Returns:
            NotificationResult
        """
        try:
            config = channel.configuration

            # Create email message
            msg = MIMEMultipart()
            msg["From"] = config.get("from_address", config.get("username", "alerts@violentutf.com"))
            msg["To"] = ", ".join(config["recipients"])
            msg["Subject"] = alert.generate_title()

            # Create email body
            body = alert.generate_message()
            msg.attach(MIMEText(body, "plain"))

            # Send email
            with smtplib.SMTP(config["smtp_server"], config.get("smtp_port", 587)) as server:
                if config.get("use_tls", True):
                    server.starttls()

                if "username" in config and "password" in config:
                    # Handle environment variable passwords
                    password = config["password"]
                    if password.startswith("${") and password.endswith("}"):
                        import os

                        env_var = password[2:-1]
                        password = os.getenv(env_var, "")

                    server.login(config["username"], password)

                server.send_message(msg)

            return NotificationResult(
                channel_id=channel.channel_id,
                success=True,
                message=f"Email sent to {len(config['recipients'])} recipients",
            )
        except Exception as e:
            logger.error("Failed to send email notification: %s", str(e))
            return NotificationResult(
                channel_id=channel.channel_id, success=False, message=f"Failed to send email: {str(e)}"
            )

    async def _send_slack_notification(self, channel: AlertChannel, alert: DriftAlert) -> NotificationResult:
        """Send Slack notification.

        Args:
            channel: Slack channel configuration
            alert: The drift alert

        Returns:
            NotificationResult
        """
        try:
            config = channel.configuration

            # Create Slack message payload
            payload = {
                "channel": config.get("channel", "#general"),
                "username": config.get("username", "ConfigBot"),
                "icon_emoji": config.get("icon_emoji", ":warning:"),
                "text": alert.generate_title(),
                "attachments": [
                    {
                        "color": self._get_slack_color(alert.severity),
                        "fields": [
                            {"title": "Service", "value": alert.service_name, "short": True},
                            {"title": "Severity", "value": alert.severity.upper(), "short": True},
                            {"title": "Changes", "value": str(alert.change_count), "short": True},
                            {"title": "Baseline ID", "value": alert.baseline_id, "short": True},
                        ],
                        "text": alert.generate_message(),
                        "footer": "ViolentUTF Configuration Monitor",
                        "ts": int(alert.triggered_at.timestamp()),
                    }
                ],
            }

            # Send Slack message
            async with aiohttp.ClientSession() as session:
                async with session.post(config["webhook_url"], json=payload) as response:
                    response_text = await response.text()

                    if response.status == 200 and response_text == "ok":
                        return NotificationResult(
                            channel_id=channel.channel_id, success=True, message="Slack message sent successfully"
                        )
                    else:
                        return NotificationResult(
                            channel_id=channel.channel_id,
                            success=False,
                            message=f"Slack API error: {response.status} - {response_text}",
                        )
        except Exception as e:
            logger.error("Failed to send Slack notification: %s", str(e))
            return NotificationResult(
                channel_id=channel.channel_id, success=False, message=f"Failed to send Slack message: {str(e)}"
            )

    async def _send_webhook_notification(self, channel: AlertChannel, alert: DriftAlert) -> NotificationResult:
        """Send webhook notification.

        Args:
            channel: Webhook channel configuration
            alert: The drift alert

        Returns:
            NotificationResult
        """
        try:
            config = channel.configuration

            # Create webhook payload
            payload = {
                "alert": alert.to_dict(),
                "timestamp": alert.triggered_at.isoformat(),
                "source": "violentutf-config-monitor",
            }

            headers = config.get("headers", {})
            headers["Content-Type"] = "application/json"

            # Send webhook
            async with aiohttp.ClientSession() as session:
                method = config.get("method", "POST").upper()

                if method == "POST":
                    async with session.post(config["url"], json=payload, headers=headers) as response:
                        response_text = await response.text()

                        if 200 <= response.status < 300:
                            return NotificationResult(
                                channel_id=channel.channel_id,
                                success=True,
                                message=f"Webhook sent successfully: {response.status}",
                            )
                        else:
                            return NotificationResult(
                                channel_id=channel.channel_id,
                                success=False,
                                message=f"Webhook error: {response.status} - {response_text}",
                            )
                else:
                    return NotificationResult(
                        channel_id=channel.channel_id, success=False, message=f"Unsupported HTTP method: {method}"
                    )
        except Exception as e:
            logger.error("Failed to send webhook notification: %s", str(e))
            return NotificationResult(
                channel_id=channel.channel_id, success=False, message=f"Failed to send webhook: {str(e)}"
            )

    def _get_slack_color(self, severity: str) -> str:
        """Get Slack attachment color based on severity."""
        colors = {"critical": "danger", "high": "warning", "medium": "good", "low": "#808080", "none": "#808080"}
        return colors.get(severity, "#808080")

    async def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert manager statistics.

        Returns:
            Dictionary containing alert statistics
        """
        enabled_rules = sum(1 for rule in self.rules.values() if rule.enabled)
        enabled_channels = sum(1 for channel in self.channels.values() if channel.enabled)

        # Get recent alerts (last 24 hours)
        recent_cutoff = datetime.utcnow().timestamp() - (24 * 60 * 60)
        recent_alerts = [alert for alert in self._alert_history if alert.triggered_at.timestamp() > recent_cutoff]

        return {
            "total_rules": len(self.rules),
            "enabled_rules": enabled_rules,
            "total_channels": len(self.channels),
            "enabled_channels": enabled_channels,
            "recent_alerts_24h": len(recent_alerts),
            "total_alerts": len(self._alert_history),
        }


class AuditEntry:
    """Represents a single audit trail entry for configuration changes."""

    def __init__(
        self,
        entry_id: str,
        event_type: str,
        service_name: str,
        baseline_id: str,
        user_id: str,
        change_summary: str,
        user_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        change_details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Initialize audit entry.

        Args:
            entry_id: Unique identifier for the entry
            event_type: Type of event (configuration_changed, baseline_created, etc.)
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            user_id: ID of the user who made the change
            change_summary: Brief summary of the change
            user_ip: IP address of the user
            user_agent: User agent string
            change_details: Detailed information about the change
            metadata: Additional metadata
            timestamp: When the change occurred
        """
        self.entry_id = entry_id
        self.event_type = event_type
        self.service_name = service_name
        self.baseline_id = baseline_id
        self.user_id = user_id
        self.user_ip = user_ip
        self.user_agent = user_agent
        self.change_summary = change_summary
        self.change_details = change_details or {}
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.utcnow()

        # Sanitize sensitive data in change_details
        self._sanitize_sensitive_data()

    @property
    def severity(self) -> str:
        """Get severity based on the type of change."""
        if not self.change_details:
            return "low"

        field = self.change_details.get("field", "").lower()

        # Critical: Security-related changes
        if any(key in field for key in ["password", "secret", "key", "token", "credential"]):
            return "critical"

        # High: Important configuration changes
        if any(key in field for key in ["host", "port", "database", "url", "timeout"]):
            return "high"

        # Medium: Functional changes
        if any(key in field for key in ["debug", "environment", "enabled", "config"]):
            return "medium"

        # Low: Everything else
        return "low"

    def _sanitize_sensitive_data(self) -> None:
        """Sanitize sensitive data in change details."""
        if not self.change_details:
            return

        # Hash sensitive values instead of storing them
        for key in ["old_value", "new_value"]:
            if key in self.change_details:
                value = self.change_details[key]
                if isinstance(value, str) and value:
                    # Create hash of the value
                    hash_obj = hashlib.sha256(value.encode())
                    self.change_details[f"{key}_hash"] = hash_obj.hexdigest()
                    # Remove the original value
                    del self.change_details[key]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type,
            "service_name": self.service_name,
            "baseline_id": self.baseline_id,
            "user_id": self.user_id,
            "user_ip": self.user_ip,
            "user_agent": self.user_agent,
            "change_summary": self.change_summary,
            "change_details": self.change_details,
            "metadata": self.metadata,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
        }


class AuditTrail:
    """Represents an audit trail for a specific service/baseline combination."""

    def __init__(self, service_name: str, baseline_id: str) -> None:
        """Initialize audit trail.

        Args:
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
        """
        self.service_name = service_name
        self.baseline_id = baseline_id
        self.entries: List[AuditEntry] = []
        self.created_at = datetime.utcnow()

    def add_entry(self, entry: AuditEntry) -> None:
        """Add an audit entry to the trail.

        Args:
            entry: The audit entry to add
        """
        self.entries.append(entry)
        # Keep entries sorted by timestamp (newest first)
        self.entries.sort(key=lambda e: e.timestamp, reverse=True)

    def get_entries_by_user(self, user_id: str) -> List[AuditEntry]:
        """Get all entries for a specific user.

        Args:
            user_id: ID of the user

        Returns:
            List of audit entries for the user
        """
        return [entry for entry in self.entries if entry.user_id == user_id]

    def get_entries_by_severity(self, severity: str) -> List[AuditEntry]:
        """Get all entries with a specific severity.

        Args:
            severity: Severity level to filter by

        Returns:
            List of audit entries with the specified severity
        """
        return [entry for entry in self.entries if entry.severity == severity]

    def get_entries_by_date_range(self, start_date: datetime, end_date: datetime) -> List[AuditEntry]:
        """Get entries within a date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            List of audit entries within the date range
        """
        return [entry for entry in self.entries if start_date <= entry.timestamp <= end_date]

    def generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of the audit trail.

        Returns:
            Dictionary containing trail summary
        """
        if not self.entries:
            return {"total_entries": 0, "unique_users": 0, "users": [], "event_types": [], "date_range": None}

        users = list(set(entry.user_id for entry in self.entries))
        event_types = list(set(entry.event_type for entry in self.entries))

        timestamps = [entry.timestamp for entry in self.entries]
        date_range = {"earliest": min(timestamps).isoformat(), "latest": max(timestamps).isoformat()}

        return {
            "total_entries": len(self.entries),
            "unique_users": len(users),
            "users": users,
            "event_types": event_types,
            "date_range": date_range,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "service_name": self.service_name,
            "baseline_id": self.baseline_id,
            "created_at": self.created_at.isoformat(),
            "entries": [entry.to_dict() for entry in self.entries],
            "summary": self.generate_summary(),
        }


class ChangeTracker:
    """Tracks configuration changes and creates audit entries."""

    def track_change(
        self,
        service_name: str,
        baseline_id: str,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        user_context: Dict[str, Any],
    ) -> List[AuditEntry]:
        """Track changes between old and new configuration.

        Args:
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            old_config: Previous configuration
            new_config: New configuration
            user_context: User context information

        Returns:
            List of audit entries for the changes
        """
        entries = []
        changes = self._detect_changes(old_config, new_config)

        for change in changes:
            entry = AuditEntry(
                entry_id=str(uuid.uuid4()),
                event_type="configuration_changed",
                service_name=service_name,
                baseline_id=baseline_id,
                user_id=user_context.get("user_id", "unknown"),
                user_ip=user_context.get("user_ip"),
                user_agent=user_context.get("user_agent"),
                change_summary=f"{change['change_type'].title()} {change['field']}",
                change_details=change,
                metadata={"session_id": user_context.get("session_id"), "request_id": user_context.get("request_id")},
            )
            entries.append(entry)

        return entries

    def track_baseline_creation(
        self, service_name: str, baseline_id: str, config_data: Dict[str, Any], user_context: Dict[str, Any]
    ) -> AuditEntry:
        """Track baseline creation.

        Args:
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            config_data: Configuration data
            user_context: User context information

        Returns:
            Audit entry for the creation
        """
        return AuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type="baseline_created",
            service_name=service_name,
            baseline_id=baseline_id,
            user_id=user_context.get("user_id", "unknown"),
            user_ip=user_context.get("user_ip"),
            user_agent=user_context.get("user_agent"),
            change_summary=f"Created baseline for {service_name}",
            change_details={"config_size": len(str(config_data)), "config_keys": list(config_data.keys())},
            metadata={"session_id": user_context.get("session_id"), "baseline_type": user_context.get("baseline_type")},
        )

    def track_baseline_deletion(self, service_name: str, baseline_id: str, user_context: Dict[str, Any]) -> AuditEntry:
        """Track baseline deletion.

        Args:
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            user_context: User context information

        Returns:
            Audit entry for the deletion
        """
        return AuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type="baseline_deleted",
            service_name=service_name,
            baseline_id=baseline_id,
            user_id=user_context.get("user_id", "unknown"),
            user_ip=user_context.get("user_ip"),
            user_agent=user_context.get("user_agent"),
            change_summary=f"Deleted baseline for {service_name}",
            change_details={"deletion_reason": user_context.get("reason", "Not specified")},
            metadata={"session_id": user_context.get("session_id"), "reason": user_context.get("reason")},
        )

    def calculate_change_impact(self, changes: List[Dict[str, Any]]) -> float:
        """Calculate the impact score of configuration changes.

        Args:
            changes: List of change details

        Returns:
            Impact score (0-10, where 10 is highest impact)
        """
        if not changes:
            return 0.0

        total_impact = 0.0

        for change in changes:
            field = change.get("field", "").lower()
            change_type = change.get("change_type", "")

            # Base impact by change type
            if change_type == "removed":
                base_impact = 3.0
            elif change_type == "added":
                base_impact = 2.0
            elif change_type == "modified":
                base_impact = 2.5
            else:
                base_impact = 1.0

            # Multiply by field importance
            if any(key in field for key in ["password", "secret", "key", "token"]):
                multiplier = 4.0  # Critical
            elif any(key in field for key in ["host", "port", "database", "url"]):
                multiplier = 3.0  # High
            elif any(key in field for key in ["debug", "environment", "timeout"]):
                multiplier = 2.0  # Medium
            else:
                multiplier = 1.0  # Low

            total_impact += base_impact * multiplier

        # Cap at 10.0 and return average impact per change
        return min(10.0, total_impact / len(changes))

    def _detect_changes(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any], path_prefix: str = ""
    ) -> List[Dict[str, Any]]:
        """Detect changes between two configuration dictionaries.

        Args:
            old_config: Previous configuration
            new_config: New configuration
            path_prefix: Current path prefix for nested keys

        Returns:
            List of change details
        """
        changes = []

        # Check for removed keys
        for key in old_config:
            current_path = f"{path_prefix}.{key}" if path_prefix else key

            if key not in new_config:
                changes.append(
                    {"field": current_path, "change_type": "removed", "old_value": old_config[key], "new_value": None}
                )
            elif isinstance(old_config[key], dict) and isinstance(new_config[key], dict):
                # Recursively check nested dictionaries
                nested_changes = self._detect_changes(old_config[key], new_config[key], current_path)
                changes.extend(nested_changes)
            elif old_config[key] != new_config[key]:
                changes.append(
                    {
                        "field": current_path,
                        "change_type": "modified",
                        "old_value": old_config[key],
                        "new_value": new_config[key],
                    }
                )

        # Check for added keys
        for key in new_config:
            current_path = f"{path_prefix}.{key}" if path_prefix else key

            if key not in old_config:
                changes.append(
                    {"field": current_path, "change_type": "added", "old_value": None, "new_value": new_config[key]}
                )

        return changes


class ConfigurationAuditor:
    """Manages audit trails and provides audit functionality."""

    def __init__(self) -> None:
        """Initialize configuration auditor."""
        self.audit_trails: Dict[tuple, AuditTrail] = {}  # (service_name, baseline_id) -> trail
        self.change_tracker = ChangeTracker()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}  # session_id -> session_info

    async def start_audit_session(self, user_id: str, user_ip: str, user_agent: Optional[str] = None) -> str:
        """Start a new audit session.

        Args:
            user_id: ID of the user
            user_ip: IP address of the user
            user_agent: User agent string

        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())

        self.active_sessions[session_id] = {
            "user_id": user_id,
            "user_ip": user_ip,
            "user_agent": user_agent,
            "started_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
        }

        logger.info("Started audit session %s for user %s", session_id, user_id)
        return session_id

    async def end_audit_session(self, session_id: str) -> bool:
        """End an audit session.

        Args:
            session_id: ID of the session to end

        Returns:
            True if session was ended successfully
        """
        if session_id in self.active_sessions:
            session_info = self.active_sessions[session_id]
            duration = datetime.utcnow() - session_info["started_at"]

            logger.info(
                "Ended audit session %s for user %s (duration: %s)", session_id, session_info["user_id"], duration
            )

            del self.active_sessions[session_id]
            return True

        return False

    async def audit_configuration_change(
        self,
        session_id: str,
        service_name: str,
        baseline_id: str,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        change_reason: Optional[str] = None,
    ) -> List[AuditEntry]:
        """Audit a configuration change.

        Args:
            session_id: Active session ID
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            old_config: Previous configuration
            new_config: New configuration
            change_reason: Reason for the change

        Returns:
            List of audit entries created
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Invalid or expired session: {session_id}")

        session_info = self.active_sessions[session_id]
        session_info["last_activity"] = datetime.utcnow()

        # Create user context
        user_context = {
            "user_id": session_info["user_id"],
            "user_ip": session_info["user_ip"],
            "user_agent": session_info["user_agent"],
            "session_id": session_id,
            "change_reason": change_reason,
        }

        # Track changes
        entries = self.change_tracker.track_change(
            service_name=service_name,
            baseline_id=baseline_id,
            old_config=old_config,
            new_config=new_config,
            user_context=user_context,
        )

        # Add entries to audit trail
        trail_key = (service_name, baseline_id)
        if trail_key not in self.audit_trails:
            self.audit_trails[trail_key] = AuditTrail(service_name, baseline_id)

        for entry in entries:
            self.audit_trails[trail_key].add_entry(entry)

        logger.info(
            "Audited %d configuration changes for %s/%s by user %s",
            len(entries),
            service_name,
            baseline_id,
            session_info["user_id"],
        )

        return entries

    async def audit_baseline_creation(
        self, session_id: str, service_name: str, baseline_id: str, config_data: Dict[str, Any]
    ) -> AuditEntry:
        """Audit baseline creation.

        Args:
            session_id: Active session ID
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            config_data: Configuration data

        Returns:
            Audit entry for the creation
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Invalid or expired session: {session_id}")

        session_info = self.active_sessions[session_id]
        session_info["last_activity"] = datetime.utcnow()

        user_context = {
            "user_id": session_info["user_id"],
            "user_ip": session_info["user_ip"],
            "user_agent": session_info["user_agent"],
            "session_id": session_id,
        }

        entry = self.change_tracker.track_baseline_creation(
            service_name=service_name, baseline_id=baseline_id, config_data=config_data, user_context=user_context
        )

        # Add to audit trail
        trail_key = (service_name, baseline_id)
        if trail_key not in self.audit_trails:
            self.audit_trails[trail_key] = AuditTrail(service_name, baseline_id)

        self.audit_trails[trail_key].add_entry(entry)

        logger.info(
            "Audited baseline creation for %s/%s by user %s", service_name, baseline_id, session_info["user_id"]
        )

        return entry

    async def audit_baseline_deletion(
        self, session_id: str, service_name: str, baseline_id: str, reason: Optional[str] = None
    ) -> AuditEntry:
        """Audit baseline deletion.

        Args:
            session_id: Active session ID
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            reason: Reason for deletion

        Returns:
            Audit entry for the deletion
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Invalid or expired session: {session_id}")

        session_info = self.active_sessions[session_id]
        session_info["last_activity"] = datetime.utcnow()

        user_context = {
            "user_id": session_info["user_id"],
            "user_ip": session_info["user_ip"],
            "user_agent": session_info["user_agent"],
            "session_id": session_id,
            "reason": reason,
        }

        entry = self.change_tracker.track_baseline_deletion(
            service_name=service_name, baseline_id=baseline_id, user_context=user_context
        )

        # Add to audit trail
        trail_key = (service_name, baseline_id)
        if trail_key not in self.audit_trails:
            self.audit_trails[trail_key] = AuditTrail(service_name, baseline_id)

        self.audit_trails[trail_key].add_entry(entry)

        logger.info(
            "Audited baseline deletion for %s/%s by user %s", service_name, baseline_id, session_info["user_id"]
        )

        return entry

    async def search_audit_entries(
        self,
        service_name: Optional[str] = None,
        user_id: Optional[str] = None,
        severity: Optional[str] = None,
        event_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditEntry]:
        """Search audit entries with filters.

        Args:
            service_name: Filter by service name
            user_id: Filter by user ID
            severity: Filter by severity
            event_type: Filter by event type
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of matching audit entries
        """
        results = []

        for trail in self.audit_trails.values():
            for entry in trail.entries:
                # Apply filters
                if service_name and entry.service_name != service_name:
                    continue
                if user_id and entry.user_id != user_id:
                    continue
                if severity and entry.severity != severity:
                    continue
                if event_type and entry.event_type != event_type:
                    continue
                if start_date and entry.timestamp < start_date:
                    continue
                if end_date and entry.timestamp > end_date:
                    continue

                results.append(entry)

        # Sort by timestamp (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results

    async def generate_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate compliance audit report.

        Args:
            start_date: Start of the reporting period
            end_date: End of the reporting period

        Returns:
            Compliance report
        """
        entries = await self.search_audit_entries(start_date=start_date, end_date=end_date)

        if not entries:
            return {
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_events": 0,
                "compliance_score": 100.0,
                "summary": "No audit events in reporting period",
            }

        # Calculate metrics
        services_modified = set(entry.service_name for entry in entries)
        users_active = set(entry.user_id for entry in entries)
        event_types = set(entry.event_type for entry in entries)

        # Calculate compliance score based on various factors
        critical_events = len([e for e in entries if e.severity == "critical"])
        total_events = len(entries)

        # Simple compliance score: 100 - (critical_events / total_events * 50)
        # This gives a score between 50-100, where more critical events = lower score
        compliance_score = max(50.0, 100.0 - (critical_events / total_events * 50))

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "total_events": total_events,
            "services_modified": list(services_modified),
            "users_active": list(users_active),
            "event_types": list(event_types),
            "severity_breakdown": {
                "critical": len([e for e in entries if e.severity == "critical"]),
                "high": len([e for e in entries if e.severity == "high"]),
                "medium": len([e for e in entries if e.severity == "medium"]),
                "low": len([e for e in entries if e.severity == "low"]),
            },
            "compliance_score": compliance_score,
            "recommendations": self._generate_compliance_recommendations(entries),
        }

    async def export_audit_trail(
        self, service_name: str, baseline_id: str, export_format: str = "json"
    ) -> Dict[str, Any]:
        """Export audit trail for a specific service/baseline.

        Args:
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            format: Export format (json, csv)

        Returns:
            Exported audit trail data
        """
        trail_key = (service_name, baseline_id)

        if trail_key not in self.audit_trails:
            raise ValueError(f"No audit trail found for {service_name}/{baseline_id}")

        trail = self.audit_trails[trail_key]

        if export_format.lower() == "json":
            return trail.to_dict()
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

    async def get_audit_statistics(self) -> Dict[str, Any]:
        """Get comprehensive audit statistics.

        Returns:
            Dictionary containing audit statistics
        """
        total_entries = sum(len(trail.entries) for trail in self.audit_trails.values())
        services_tracked = set(trail.service_name for trail in self.audit_trails.values())

        # Calculate recent activity (last 24 hours)
        recent_cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0)
        recent_entries = await self.search_audit_entries(start_date=recent_cutoff)

        return {
            "total_trails": len(self.audit_trails),
            "total_entries": total_entries,
            "active_sessions": len(self.active_sessions),
            "services_tracked": list(services_tracked),
            "recent_activity_24h": len(recent_entries),
            "session_info": {
                session_id: {
                    "user_id": info["user_id"],
                    "started_at": info["started_at"].isoformat(),
                    "last_activity": info["last_activity"].isoformat(),
                }
                for session_id, info in self.active_sessions.items()
            },
        }

    def _generate_compliance_recommendations(self, entries: List[AuditEntry]) -> List[str]:
        """Generate compliance recommendations based on audit entries.

        Args:
            entries: List of audit entries to analyze

        Returns:
            List of compliance recommendations
        """
        recommendations = []

        critical_count = len([e for e in entries if e.severity == "critical"])
        total_count = len(entries)

        if critical_count > 0:
            recommendations.append(f"Review {critical_count} critical configuration changes for security compliance")

        if critical_count / total_count > 0.2:  # More than 20% critical
            recommendations.append(
                "High percentage of critical changes detected - consider implementing additional approval workflows"
            )

        # Check for changes outside business hours
        business_hour_changes = 0
        for entry in entries:
            hour = entry.timestamp.hour
            if 9 <= hour <= 17:  # Business hours 9 AM - 5 PM
                business_hour_changes += 1

        after_hours_ratio = (total_count - business_hour_changes) / total_count
        if after_hours_ratio > 0.3:  # More than 30% after hours
            recommendations.append(
                "High number of after-hours changes detected - ensure proper authorization procedures"
            )

        # Check for users with many changes
        user_changes = {}
        for entry in entries:
            user_changes[entry.user_id] = user_changes.get(entry.user_id, 0) + 1

        high_activity_users = [user for user, count in user_changes.items() if count > 10]
        if high_activity_users:
            recommendations.append(
                (
                    f"Users with high activity detected: {', '.join(high_activity_users)} - "
                    "review for potential automation opportunities"
                )
            )

        if not recommendations:
            recommendations.append("No compliance issues detected in audit trail")

        return recommendations


class BackupMetadata:
    """Represents metadata for a configuration backup."""

    def __init__(
        self,
        backup_id: str,
        service_name: str,
        baseline_id: str,
        backup_type: str,
        created_by: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent_backup_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        """Initialize backup metadata.

        Args:
            backup_id: Unique identifier for the backup
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            backup_type: Type of backup (full, incremental, differential)
            created_by: User who created the backup
            description: Optional description
            tags: Optional tags for categorization
            parent_backup_id: Parent backup ID for incremental backups
            created_at: When the backup was created
        """
        self.backup_id = backup_id
        self.service_name = service_name
        self.baseline_id = baseline_id
        self.backup_type = backup_type
        self.created_by = created_by
        self.description = description
        self.tags = tags or []
        self.parent_backup_id = parent_backup_id
        self.created_at = created_at or datetime.utcnow()

    def is_valid(self) -> bool:
        """Validate backup metadata."""
        valid_backup_types = ["full", "incremental", "differential"]
        return self.backup_type in valid_backup_types

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "backup_id": self.backup_id,
            "service_name": self.service_name,
            "baseline_id": self.baseline_id,
            "backup_type": self.backup_type,
            "created_by": self.created_by,
            "description": self.description,
            "tags": self.tags,
            "parent_backup_id": self.parent_backup_id,
            "created_at": self.created_at.isoformat(),
        }


class BackupArchive:
    """Represents a configuration backup archive."""

    def __init__(
        self,
        metadata: BackupMetadata,
        config_data: Dict[str, Any],
        file_path: Optional[str] = None,
        compression: bool = False,
    ) -> None:
        """Initialize backup archive.

        Args:
            metadata: Backup metadata
            config_data: Configuration data to backup
            file_path: Path to the backup file
            compression: Whether to compress the backup
        """
        self.metadata = metadata
        self.config_data = config_data
        self.file_path = file_path
        self.compression = compression
        self.size_bytes = 0
        self.checksum: Optional[str] = None

    def compress_data(self) -> bytes:
        """Compress the configuration data.

        Returns:
            Compressed data bytes
        """
        json_data = json.dumps(self.config_data, indent=2).encode("utf-8")

        if self.compression:
            return gzip.compress(json_data)
        else:
            return json_data

    def generate_checksum(self) -> str:
        """Generate SHA-256 checksum of the backup data.

        Returns:
            Hexadecimal checksum string
        """
        data = json.dumps(self.config_data, sort_keys=True).encode("utf-8")
        hash_obj = hashlib.sha256(data)
        self.checksum = hash_obj.hexdigest()
        return self.checksum

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "metadata": self.metadata.to_dict(),
            "config_data": self.config_data,
            "file_path": self.file_path,
            "compression": self.compression,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
        }


class BackupManager:
    """Manages configuration backups."""

    def __init__(self, backup_directory: str, max_backups_per_service: int = 10, compression: bool = True) -> None:
        """Initialize backup manager.

        Args:
            backup_directory: Directory to store backups
            max_backups_per_service: Maximum backups to keep per service
            compression: Whether to compress backups by default
        """
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        self.max_backups_per_service = max_backups_per_service
        self.compression = compression
        self.backups: Dict[str, BackupArchive] = {}

        # Load existing backups
        self._load_existing_backups()

    async def create_backup(
        self,
        service_name: str,
        baseline_id: str,
        config_data: Dict[str, Any],
        backup_type: str,
        created_by: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent_backup_id: Optional[str] = None,
    ) -> str:
        """Create a new configuration backup.

        Args:
            service_name: Name of the service
            baseline_id: ID of the configuration baseline
            config_data: Configuration data to backup
            backup_type: Type of backup (full, incremental, differential)
            created_by: User creating the backup
            description: Optional description
            tags: Optional tags
            parent_backup_id: Parent backup ID for incremental backups

        Returns:
            Backup ID
        """
        backup_id = str(uuid.uuid4())

        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            service_name=service_name,
            baseline_id=baseline_id,
            backup_type=backup_type,
            created_by=created_by,
            description=description,
            tags=tags,
            parent_backup_id=parent_backup_id,
        )

        # Process config data based on backup type
        if backup_type == "incremental" and parent_backup_id:
            config_data = self._create_incremental_data(config_data, parent_backup_id)

        # Create backup file path
        file_name = f"{backup_id}.json"
        if self.compression:
            file_name += ".gz"

        file_path = self.backup_directory / file_name

        # Create archive
        archive = BackupArchive(
            metadata=metadata, config_data=config_data, file_path=str(file_path), compression=self.compression
        )

        # Generate checksum
        archive.generate_checksum()

        # Save to file
        await self._save_backup_to_file(archive)

        # Store in memory
        self.backups[backup_id] = archive

        # Apply retention policy
        await self._apply_retention_policy(service_name)

        logger.info(
            "Created %s backup %s for %s/%s by %s", backup_type, backup_id, service_name, baseline_id, created_by
        )

        return backup_id

    async def list_backups(
        self, service_name: Optional[str] = None, backup_type: Optional[str] = None, created_by: Optional[str] = None
    ) -> List[BackupArchive]:
        """List backups with optional filters.

        Args:
            service_name: Filter by service name
            backup_type: Filter by backup type
            created_by: Filter by creator

        Returns:
            List of backup archives
        """
        backups = list(self.backups.values())

        # Apply filters
        if service_name:
            backups = [b for b in backups if b.metadata.service_name == service_name]
        if backup_type:
            backups = [b for b in backups if b.metadata.backup_type == backup_type]
        if created_by:
            backups = [b for b in backups if b.metadata.created_by == created_by]

        # Sort by creation time (newest first)
        backups.sort(key=lambda b: b.metadata.created_at, reverse=True)

        return backups

    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup.

        Args:
            backup_id: ID of the backup to delete

        Returns:
            True if deletion was successful
        """
        if backup_id not in self.backups:
            return False

        archive = self.backups[backup_id]

        # Delete file
        if archive.file_path and Path(archive.file_path).exists():
            Path(archive.file_path).unlink()

        # Remove from memory
        del self.backups[backup_id]

        logger.info("Deleted backup %s", backup_id)
        return True

    async def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics.

        Returns:
            Dictionary containing backup statistics
        """
        if not self.backups:
            return {"total_backups": 0, "services_count": 0, "services": [], "backup_types": {}, "total_size_mb": 0.0}

        services = set(archive.metadata.service_name for archive in self.backups.values())
        backup_types = {}
        total_size = 0

        for archive in self.backups.values():
            backup_type = archive.metadata.backup_type
            backup_types[backup_type] = backup_types.get(backup_type, 0) + 1
            total_size += archive.size_bytes

        return {
            "total_backups": len(self.backups),
            "services_count": len(services),
            "services": list(services),
            "backup_types": backup_types,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    def _load_existing_backups(self) -> None:
        """Load existing backups from disk."""
        if not self.backup_directory.exists():
            return

        for file_path in self.backup_directory.glob("*.json*"):
            try:
                # Extract backup ID from filename
                backup_id = file_path.stem
                if backup_id.endswith(".json"):
                    backup_id = backup_id[:-5]

                # Load backup metadata and data
                # This is a simplified version - in production you'd want
                # to store metadata separately for efficiency
                # TODO: Implement actual backup loading logic
            except Exception as e:
                logger.warning("Failed to load backup from %s: %s", file_path, str(e))

    def _create_incremental_data(self, current_config: Dict[str, Any], parent_backup_id: str) -> Dict[str, Any]:
        """Create incremental backup data (changes only).

        Args:
            current_config: Current configuration
            parent_backup_id: Parent backup ID

        Returns:
            Incremental backup data containing only changes
        """
        if parent_backup_id not in self.backups:
            logger.warning("Parent backup %s not found, creating full backup instead", parent_backup_id)
            return current_config

        parent_archive = self.backups[parent_backup_id]
        parent_config = parent_archive.config_data

        # Calculate differences
        changes = {}

        # Find modified and added keys
        for key, value in current_config.items():
            if key not in parent_config or parent_config[key] != value:
                changes[key] = value

        # Find removed keys
        removed_keys = []
        for key in parent_config:
            if key not in current_config:
                removed_keys.append(key)

        incremental_data = {"changes": changes, "removed_keys": removed_keys, "parent_backup_id": parent_backup_id}

        return incremental_data

    async def _save_backup_to_file(self, archive: BackupArchive) -> None:
        """Save backup archive to file.

        Args:
            archive: Backup archive to save
        """
        file_path = Path(archive.file_path)

        # Prepare data to save
        data_to_save = {"metadata": archive.metadata.to_dict(), "config_data": archive.config_data}

        # Compress and save
        # compressed_data = archive.compress_data()  # Not used currently

        if archive.compression:
            with gzip.open(file_path, "wb") as f:
                json_data = json.dumps(data_to_save, indent=2).encode("utf-8")
                f.write(json_data)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, indent=2)

        # Update size
        archive.size_bytes = file_path.stat().st_size

    async def _apply_retention_policy(self, service_name: str) -> None:
        """Apply backup retention policy for a service.

        Args:
            service_name: Name of the service
        """
        service_backups = await self.list_backups(service_name=service_name)

        if len(service_backups) > self.max_backups_per_service:
            # Keep the most recent backups, delete the oldest
            backups_to_delete = service_backups[self.max_backups_per_service :]

            for backup in backups_to_delete:
                await self.delete_backup(backup.metadata.backup_id)
                logger.info(
                    "Deleted old backup %s for service %s (retention policy)", backup.metadata.backup_id, service_name
                )


class RestoreResult:
    """Represents the result of a configuration restore operation."""

    def __init__(
        self,
        success: bool,
        backup_id: str,
        service_name: str,
        baseline_id: str,
        restored_config: Optional[Dict[str, Any]],
        message: str,
        restored_by: Optional[str] = None,
        restored_at: Optional[datetime] = None,
    ) -> None:
        """Initialize restore result.

        Args:
            success: Whether the restore was successful
            backup_id: ID of the backup that was restored
            service_name: Name of the service
            baseline_id: ID of the baseline
            restored_config: The restored configuration data
            message: Result message
            restored_by: User who performed the restore
            restored_at: When the restore was performed
        """
        self.success = success
        self.backup_id = backup_id
        self.service_name = service_name
        self.baseline_id = baseline_id
        self.restored_config = restored_config
        self.message = message
        self.restored_by = restored_by
        self.restored_at = restored_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "backup_id": self.backup_id,
            "service_name": self.service_name,
            "baseline_id": self.baseline_id,
            "restored_config": self.restored_config,
            "message": self.message,
            "restored_by": self.restored_by,
            "restored_at": self.restored_at.isoformat(),
        }


class RestoreManager:
    """Manages configuration restore operations."""

    def __init__(self, backup_directory: str) -> None:
        """Initialize restore manager.

        Args:
            backup_directory: Directory containing backups
        """
        self.backup_directory = Path(backup_directory)
        self.restore_history: List[RestoreResult] = []
        self.backup_manager = BackupManager(backup_directory)

    async def restore_configuration(
        self,
        backup_id: str,
        target_service: str,
        target_baseline: str,
        restored_by: str,
        validate: bool = True,
        dry_run: bool = False,
    ) -> RestoreResult:
        """Restore configuration from a backup.

        Args:
            backup_id: ID of the backup to restore
            target_service: Target service name
            target_baseline: Target baseline ID
            restored_by: User performing the restore
            validate: Whether to validate the restored configuration
            dry_run: Whether to perform a dry run (preview only)

        Returns:
            RestoreResult indicating success or failure
        """
        # Check if backup exists
        if backup_id not in self.backup_manager.backups:
            return RestoreResult(
                success=False,
                backup_id=backup_id,
                service_name=target_service,
                baseline_id=target_baseline,
                restored_config=None,
                message=f"Backup {backup_id} not found",
                restored_by=restored_by,
            )

        try:
            archive = self.backup_manager.backups[backup_id]

            # Reconstruct full configuration
            restored_config = await self._reconstruct_configuration(archive)

            # Validate if requested
            if validate and not dry_run:
                is_valid = await self._validate_configuration(restored_config, target_service)
                if not is_valid:
                    return RestoreResult(
                        success=False,
                        backup_id=backup_id,
                        service_name=target_service,
                        baseline_id=target_baseline,
                        restored_config=None,
                        message="Configuration validation failed",
                        restored_by=restored_by,
                    )

            # Create result
            if dry_run:
                message = f"Dry run restore preview for backup {backup_id}"
            else:
                message = f"Configuration restored successfully from backup {backup_id}"
                # Add to history only for actual restores
                result = RestoreResult(
                    success=True,
                    backup_id=backup_id,
                    service_name=target_service,
                    baseline_id=target_baseline,
                    restored_config=restored_config,
                    message=message,
                    restored_by=restored_by,
                )
                self.restore_history.append(result)

            logger.info(
                "Restored configuration for %s/%s from backup %s by %s%s",
                target_service,
                target_baseline,
                backup_id,
                restored_by,
                " (dry run)" if dry_run else "",
            )

            return RestoreResult(
                success=True,
                backup_id=backup_id,
                service_name=target_service,
                baseline_id=target_baseline,
                restored_config=restored_config,
                message=message,
                restored_by=restored_by,
            )

        except Exception as e:
            logger.error("Failed to restore backup %s: %s", backup_id, str(e))
            return RestoreResult(
                success=False,
                backup_id=backup_id,
                service_name=target_service,
                baseline_id=target_baseline,
                restored_config=None,
                message=f"Restore failed: {str(e)}",
                restored_by=restored_by,
            )

    async def restore_to_point_in_time(
        self, service_name: str, baseline_id: str, target_time: datetime, restored_by: str
    ) -> RestoreResult:
        """Restore configuration to a specific point in time.

        Args:
            service_name: Name of the service
            baseline_id: ID of the baseline
            target_time: Target point in time
            restored_by: User performing the restore

        Returns:
            RestoreResult indicating success or failure
        """
        # Find the backup closest to the target time
        service_backups = await self.backup_manager.list_backups(service_name=service_name)

        # Filter backups that are before or at the target time
        eligible_backups = [backup for backup in service_backups if backup.metadata.created_at <= target_time]

        if not eligible_backups:
            return RestoreResult(
                success=False,
                backup_id="",
                service_name=service_name,
                baseline_id=baseline_id,
                restored_config=None,
                message=f"No backups found before {target_time.isoformat()}",
                restored_by=restored_by,
            )

        # Use the most recent backup before the target time
        selected_backup = max(eligible_backups, key=lambda b: b.metadata.created_at)

        return await self.restore_configuration(
            backup_id=selected_backup.metadata.backup_id,
            target_service=service_name,
            target_baseline=baseline_id,
            restored_by=restored_by,
        )

    async def get_restore_history(
        self, service_name: Optional[str] = None, restored_by: Optional[str] = None
    ) -> List[RestoreResult]:
        """Get restore operation history.

        Args:
            service_name: Filter by service name
            restored_by: Filter by user who performed restore

        Returns:
            List of restore results
        """
        history = self.restore_history.copy()

        # Apply filters
        if service_name:
            history = [r for r in history if r.service_name == service_name]
        if restored_by:
            history = [r for r in history if r.restored_by == restored_by]

        # Sort by restore time (newest first)
        history.sort(key=lambda r: r.restored_at, reverse=True)

        return history

    async def _reconstruct_configuration(self, archive: BackupArchive) -> Dict[str, Any]:
        """Reconstruct full configuration from backup archive.

        Args:
            archive: Backup archive

        Returns:
            Reconstructed configuration
        """
        if archive.metadata.backup_type == "full":
            return archive.config_data.copy()

        elif archive.metadata.backup_type == "incremental":
            # Reconstruct from parent backup and apply changes
            parent_backup_id = archive.metadata.parent_backup_id
            if not parent_backup_id or parent_backup_id not in self.backup_manager.backups:
                raise ValueError(f"Parent backup {parent_backup_id} not found for incremental restore")

            parent_archive = self.backup_manager.backups[parent_backup_id]
            base_config = await self._reconstruct_configuration(parent_archive)

            # Apply incremental changes
            changes = archive.config_data.get("changes", {})
            removed_keys = archive.config_data.get("removed_keys", [])

            # Apply changes
            for key, value in changes.items():
                base_config[key] = value

            # Remove deleted keys
            for key in removed_keys:
                if key in base_config:
                    del base_config[key]

            return base_config

        else:
            raise ValueError(f"Unsupported backup type: {archive.metadata.backup_type}")

    async def _validate_configuration(self, config_data: Dict[str, Any], service_name: str) -> bool:
        """Validate restored configuration.

        Args:
            config_data: Configuration data to validate
            service_name: Name of the service

        Returns:
            True if configuration is valid
        """
        # Placeholder for configuration validation
        # In a real implementation, this would validate against
        # service-specific schemas or rules

        # Basic validation: ensure config is not empty
        if not config_data:
            return False

        # Service-specific validation could be added here
        # For now, just return True for any non-empty config
        return True
