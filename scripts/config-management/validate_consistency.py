#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Configuration Validation Tool for ViolentUTF - Issue #266.

Validates configuration consistency and detects drift from baseline.
"""

import hashlib
import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jsonschema
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Represents validation results for a configuration."""

    configuration_path: str
    service: str
    environment: str
    validation_timestamp: str
    schema_valid: bool
    schema_errors: List[str] = field(default_factory=list)
    schema_warnings: List[str] = field(default_factory=list)
    dependency_valid: bool = True
    dependency_errors: List[str] = field(default_factory=list)
    security_compliant: bool = True
    security_issues: List[str] = field(default_factory=list)
    drift_detected: bool = False
    drift_details: List[str] = field(default_factory=list)
    overall_valid: bool = True
    validation_score: float = 100.0  # 0-100 scale


@dataclass
class DriftDetectionResult:
    """Represents drift detection results."""

    baseline_checksum: str
    current_checksum: str
    drift_detected: bool
    drift_percentage: float
    changes_detected: List[Dict[str, Any]] = field(default_factory=list)
    change_categories: Dict[str, int] = field(default_factory=dict)
    risk_level: str = "low"  # 'low', 'medium', 'high', 'critical'


class ConfigurationValidator:
    """Main configuration validation engine."""

    def __init__(self, schemas_path: str = "schemas", database_path: str = "config_validation.db") -> None:
        """Initialize the configuration validation tool.

        Args:
            schemas_path: Path to directory containing validation schemas
            database_path: Path to SQLite database for storing validation results
        """
        self.schemas_path = Path(schemas_path)
        self.database_path = database_path
        self.loaded_schemas = {}
        self.validation_rules = self._load_validation_rules()
        self._setup_database()
        self._load_schemas()

    def _setup_database(self) -> None:
        """Set up SQLite database for storing validation results."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS validation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                configuration_path TEXT NOT NULL,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                schema_valid BOOLEAN NOT NULL,
                dependency_valid BOOLEAN NOT NULL,
                security_compliant BOOLEAN NOT NULL,
                drift_detected BOOLEAN NOT NULL,
                overall_valid BOOLEAN NOT NULL,
                validation_score REAL NOT NULL,
                validation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuration_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                configuration_checksum TEXT NOT NULL,
                configuration_data TEXT NOT NULL,
                baseline_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(service, environment)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS drift_detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                baseline_checksum TEXT NOT NULL,
                current_checksum TEXT NOT NULL,
                drift_percentage REAL NOT NULL,
                risk_level TEXT NOT NULL,
                changes_count INTEGER NOT NULL,
                detection_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def _load_validation_rules(self) -> Dict[str, Any]:
        """Load validation rules for different services."""
        return {
            "apisix": {
                "required_fields": ["deployment.admin.admin_key", "apisix.node_listen"],
                "security_fields": ["deployment.admin.admin_key", "apisix.ssl", "deployment.admin.admin_key_required"],
                "performance_fields": [
                    "nginx_config.event.worker_connections",
                    "nginx_config.http.upstream.keepalive_timeout",
                ],
            },
            "keycloak": {
                "required_fields": ["realm", "enabled", "accessTokenLifespan"],
                "security_fields": ["sslRequired", "bruteForceProtected", "accessTokenLifespan"],
                "performance_fields": ["ssoSessionIdleTimeout", "ssoSessionMaxLifespan"],
            },
            "postgres": {
                "required_fields": ["host", "port", "database"],
                "security_fields": ["ssl", "password", "connection_limit"],
                "performance_fields": ["max_connections", "shared_buffers", "work_mem"],
            },
        }

    def _load_schemas(self) -> None:
        """Load JSON schemas for configuration validation."""
        if not self.schemas_path.exists():
            logger.warning("Schemas directory %s not found", self.schemas_path)
            return

        for schema_file in self.schemas_path.glob("*.json"):
            service_name = schema_file.stem
            try:
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema = json.load(f)
                self.loaded_schemas[service_name] = schema
                logger.debug("Loaded schema for %s", service_name)
            except Exception as e:
                logger.error("Error loading schema %s: %s", schema_file, e)

    def validate_configuration(
        self, config: Dict[str, Any], service: str, environment: str, config_path: str = "unknown"
    ) -> ValidationResult:
        """Validate a configuration against schemas and rules.

        Args:
            config: Configuration dictionary to validate
            service: Service name
            environment: Environment name
            config_path: Path to configuration file

        Returns:
            ValidationResult with detailed validation information
        """
        logger.info("Validating %s configuration for %s", service, environment)

        result = ValidationResult(
            configuration_path=config_path,
            service=service,
            environment=environment,
            validation_timestamp=datetime.now().isoformat(),
            schema_valid=False,
        )

        # Schema validation
        schema_result = self._validate_schema(config, service)
        result.schema_valid = schema_result["valid"]
        result.schema_errors = schema_result["errors"]
        result.schema_warnings = schema_result["warnings"]

        # Dependency validation
        dependency_result = self._validate_dependencies(config, service)
        result.dependency_valid = dependency_result["valid"]
        result.dependency_errors = dependency_result["errors"]

        # Security compliance validation
        security_result = self._validate_security_compliance(config, service, environment)
        result.security_compliant = security_result["compliant"]
        result.security_issues = security_result["issues"]

        # Drift detection
        drift_result = self._detect_drift(config, service, environment)
        result.drift_detected = drift_result.drift_detected
        result.drift_details = [f"{change['type']}: {change['path']}" for change in drift_result.changes_detected]

        # Calculate overall validity and score
        result.overall_valid = (
            result.schema_valid and result.dependency_valid and result.security_compliant and not result.drift_detected
        )
        result.validation_score = self._calculate_validation_score(result)

        # Store validation results
        self._store_validation_results(result)

        logger.info("Validation completed - Score: %.1f/100", result.validation_score)
        return result

    def _validate_schema(self, config: Dict[str, Any], service: str) -> Dict[str, Any]:
        """Validate configuration against JSON schema.

        Args:
            config: Configuration to validate
            service: Service name

        Returns:
            Dictionary with validation results
        """
        if service not in self.loaded_schemas:
            return {
                "valid": True,  # No schema available, assume valid
                "errors": [],
                "warnings": [f"No schema available for service {service}"],
            }

        schema = self.loaded_schemas[service]
        errors = []
        warnings = []

        try:
            jsonschema.validate(config, schema)
            return {"valid": True, "errors": [], "warnings": warnings}
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            return {"valid": False, "errors": errors, "warnings": warnings}
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")
            return {"valid": False, "errors": errors, "warnings": warnings}

    def _validate_dependencies(self, config: Dict[str, Any], service: str) -> Dict[str, Any]:
        """Validate configuration dependencies.

        Args:
            config: Configuration to validate
            service: Service name

        Returns:
            Dictionary with dependency validation results
        """
        errors = []

        if service not in self.validation_rules:
            return {"valid": True, "errors": []}

        rules = self.validation_rules[service]
        required_fields = rules.get("required_fields", [])

        # Check required fields
        for field_path in required_fields:
            if not self._get_nested_value(config, field_path):
                errors.append(f"Required field missing: {field_path}")

        # Service-specific dependency checks
        if service == "apisix":
            errors.extend(self._validate_apisix_dependencies(config))
        elif service == "keycloak":
            errors.extend(self._validate_keycloak_dependencies(config))
        elif service == "postgres":
            errors.extend(self._validate_postgres_dependencies(config))

        return {"valid": len(errors) == 0, "errors": errors}

    def _validate_apisix_dependencies(self, config: Dict[str, Any]) -> List[str]:
        """Validate APISIX-specific dependencies."""
        errors = []

        # Check if admin key is properly configured
        admin_key = self._get_nested_value(config, "deployment.admin.admin_key")
        if admin_key:
            if len(str(admin_key)) < 16:
                errors.append("Admin key too short - should be at least 16 characters")

        # Check if SSL is properly configured if enabled
        ssl_enabled = self._get_nested_value(config, "apisix.ssl.enable")
        if ssl_enabled:
            ssl_cert = self._get_nested_value(config, "apisix.ssl.ssl_trusted_certificate")
            if not ssl_cert:
                errors.append("SSL enabled but no trusted certificate configured")

        # Check plugin configuration
        plugins = self._get_nested_value(config, "plugins")
        if plugins and isinstance(plugins, list):
            if "jwt-auth" in plugins:
                # JWT auth plugin requires specific configuration
                plugin_attr = self._get_nested_value(config, "plugin_attr")
                if not plugin_attr or "jwt-auth" not in plugin_attr:
                    errors.append("JWT auth plugin enabled but not configured in plugin_attr")

        return errors

    def _validate_keycloak_dependencies(self, config: Dict[str, Any]) -> List[str]:
        """Validate Keycloak-specific dependencies."""
        errors = []

        # Check token lifespan consistency
        access_token_lifespan = self._get_nested_value(config, "accessTokenLifespan")
        sso_idle_timeout = self._get_nested_value(config, "ssoSessionIdleTimeout")

        if access_token_lifespan and sso_idle_timeout:
            if access_token_lifespan > sso_idle_timeout:
                errors.append("Access token lifespan should not exceed SSO session idle timeout")

        # Check SSL requirements
        ssl_required = self._get_nested_value(config, "sslRequired")
        if ssl_required == "none":
            errors.append("SSL should be required for production environments")

        # Check brute force protection
        brute_force_protected = self._get_nested_value(config, "bruteForceProtected")
        if not brute_force_protected:
            errors.append("Brute force protection should be enabled")

        return errors

    def _validate_postgres_dependencies(self, config: Dict[str, Any]) -> List[str]:
        """Validate PostgreSQL-specific dependencies."""
        errors = []

        # Check connection limits
        max_connections = self._get_nested_value(config, "max_connections")
        if max_connections and max_connections < 10:
            errors.append("Max connections too low - should be at least 10")

        # Check SSL configuration
        ssl_mode = self._get_nested_value(config, "ssl_mode")
        if ssl_mode == "disable":
            errors.append("SSL should be enabled for database connections")

        return errors

    def _validate_security_compliance(self, config: Dict[str, Any], service: str, environment: str) -> Dict[str, Any]:
        """Validate security compliance of configuration.

        Args:
            config: Configuration to validate
            service: Service name
            environment: Environment name

        Returns:
            Dictionary with security compliance results
        """
        issues = []

        if service not in self.validation_rules:
            return {"compliant": True, "issues": []}

        rules = self.validation_rules[service]
        security_fields = rules.get("security_fields", [])

        # Check security-related fields
        for field_path in security_fields:
            value = self._get_nested_value(config, field_path)
            issue = self._check_security_field(field_path, value, environment)
            if issue:
                issues.append(issue)

        # Service-specific security checks
        if service == "apisix":
            issues.extend(self._check_apisix_security(config, environment))
        elif service == "keycloak":
            issues.extend(self._check_keycloak_security(config, environment))
        elif service == "postgres":
            issues.extend(self._check_postgres_security(config, environment))

        return {"compliant": len(issues) == 0, "issues": issues}

    def _check_security_field(
        self, field_path: str, value: Union[str, int, bool, None], environment: str
    ) -> Optional[str]:
        """Check a specific security field for compliance.

        Args:
            field_path: Path to the security field
            value: Value of the field
            environment: Environment name

        Returns:
            Security issue string or None if compliant
        """
        field_lower = field_path.lower()

        # SSL/TLS checks
        if "ssl" in field_lower:
            if environment.lower() in ["prod", "production", "staging"]:
                if value in [False, "none", "disable", "disabled"]:
                    return f"SSL should be enabled in {environment} environment"

        # Password/secret checks
        if any(keyword in field_lower for keyword in ["password", "secret", "key"]):
            if isinstance(value, str) and len(value) < 8:
                return f"Security credential too short: {field_path}"

        # Token lifespan checks
        if "token" in field_lower and "lifespan" in field_lower:
            if isinstance(value, int):
                if environment.lower() in ["prod", "production"]:
                    if value > 3600:  # 1 hour
                        return f"Token lifespan too long for production: {value}s"
                else:
                    if value > 86400:  # 24 hours
                        return f"Token lifespan too long: {value}s"

        return None

    def _check_apisix_security(self, config: Dict[str, Any], environment: str) -> List[str]:
        """Check APISIX-specific security configurations."""
        issues = []

        # Check admin key strength
        admin_key = self._get_nested_value(config, "deployment.admin.admin_key")
        if admin_key and isinstance(admin_key, str):
            if len(admin_key) < 32:
                issues.append("APISIX admin key should be at least 32 characters")
            if not re.search(r"[A-Za-z]", admin_key) or not re.search(r"[0-9]", admin_key):
                issues.append("APISIX admin key should contain both letters and numbers")

        # Check if admin API is restricted
        allow_admin = self._get_nested_value(config, "deployment.admin.allow_admin")
        if allow_admin and "0.0.0.0/0" in allow_admin:
            issues.append("Admin API should not be accessible from all IPs")

        return issues

    def _check_keycloak_security(self, config: Dict[str, Any], environment: str) -> List[str]:
        """Check Keycloak-specific security configurations."""
        issues = []

        # Check token lifespan for production
        if environment.lower() in ["prod", "production"]:
            token_lifespan = self._get_nested_value(config, "accessTokenLifespan")
            if token_lifespan and token_lifespan > 900:  # 15 minutes
                issues.append("Access token lifespan too long for production environment")

        # Check remember me settings
        remember_me = self._get_nested_value(config, "rememberMe")
        if remember_me and environment.lower() in ["prod", "production"]:
            issues.append("Remember me feature should be disabled in production")

        return issues

    def _check_postgres_security(self, config: Dict[str, Any], environment: str) -> List[str]:
        """Check PostgreSQL-specific security configurations."""
        issues = []

        # Check for default passwords
        password = self._get_nested_value(config, "password")
        if password and password in ["postgres", "password", "123456", "admin"]:
            issues.append("Default or weak database password detected")

        return issues

    def _detect_drift(self, config: Dict[str, Any], service: str, environment: str) -> DriftDetectionResult:
        """Detect configuration drift from baseline.

        Args:
            config: Current configuration
            service: Service name
            environment: Environment name

        Returns:
            DriftDetectionResult with drift information
        """
        # Calculate current configuration checksum
        config_str = json.dumps(config, sort_keys=True)
        current_checksum = hashlib.sha256(config_str.encode()).hexdigest()

        # Get baseline configuration
        baseline_checksum = self._get_baseline_checksum(service, environment)

        if not baseline_checksum:
            # No baseline exists, create one
            self._store_baseline(service, environment, current_checksum, config_str)
            return DriftDetectionResult(
                baseline_checksum=current_checksum,
                current_checksum=current_checksum,
                drift_detected=False,
                drift_percentage=0.0,
            )

        if baseline_checksum == current_checksum:
            return DriftDetectionResult(
                baseline_checksum=baseline_checksum,
                current_checksum=current_checksum,
                drift_detected=False,
                drift_percentage=0.0,
            )

        # Drift detected, analyze changes
        baseline_config = self._get_baseline_config(service, environment)
        if baseline_config:
            changes = self._analyze_configuration_changes(baseline_config, config)
            drift_percentage = self._calculate_drift_percentage(changes, config)
            risk_level = self._assess_drift_risk_level(changes, drift_percentage)

            # Store drift detection results
            self._store_drift_detection(
                service, environment, baseline_checksum, current_checksum, drift_percentage, risk_level, len(changes)
            )

            return DriftDetectionResult(
                baseline_checksum=baseline_checksum,
                current_checksum=current_checksum,
                drift_detected=True,
                drift_percentage=drift_percentage,
                changes_detected=changes,
                risk_level=risk_level,
            )

        return DriftDetectionResult(
            baseline_checksum=baseline_checksum,
            current_checksum=current_checksum,
            drift_detected=True,
            drift_percentage=100.0,
            risk_level="high",
        )

    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Union[str, int, bool, None]:
        """Get value from nested dictionary using dot notation path.

        Args:
            config: Configuration dictionary
            path: Dot-separated path to value

        Returns:
            Value at path or None if not found
        """
        try:
            keys = path.split(".")
            value = config
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        except (KeyError, TypeError):
            return None

    def _calculate_validation_score(self, result: ValidationResult) -> float:
        """Calculate overall validation score (0-100).

        Args:
            result: ValidationResult object

        Returns:
            Validation score as float
        """
        score = 100.0

        # Schema validation penalties
        if not result.schema_valid:
            score -= 30.0  # Major penalty for schema violations

        score -= min(len(result.schema_errors) * 5.0, 20.0)  # Up to 20 points for errors
        score -= min(len(result.schema_warnings) * 2.0, 10.0)  # Up to 10 points for warnings

        # Dependency validation penalties
        if not result.dependency_valid:
            score -= 25.0

        score -= min(len(result.dependency_errors) * 3.0, 15.0)

        # Security compliance penalties
        if not result.security_compliant:
            score -= 35.0  # Major penalty for security issues

        score -= min(len(result.security_issues) * 5.0, 20.0)

        # Drift detection penalties
        if result.drift_detected:
            score -= 10.0  # Moderate penalty for drift

        return max(score, 0.0)

    def _get_baseline_checksum(self, service: str, environment: str) -> Optional[str]:
        """Get baseline configuration checksum."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT configuration_checksum FROM configuration_baselines
            WHERE service = ? AND environment = ?
            ORDER BY baseline_timestamp DESC LIMIT 1
        """,
            (service, environment),
        )

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def _get_baseline_config(self, service: str, environment: str) -> Optional[Dict[str, Any]]:
        """Get baseline configuration data."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT configuration_data FROM configuration_baselines
            WHERE service = ? AND environment = ?
            ORDER BY baseline_timestamp DESC LIMIT 1
        """,
            (service, environment),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            try:
                return json.loads(result[0])
            except json.JSONDecodeError:
                return None

        return None

    def _store_baseline(self, service: str, environment: str, checksum: str, config_data: str) -> None:
        """Store baseline configuration."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO configuration_baselines
            (service, environment, configuration_checksum, configuration_data)
            VALUES (?, ?, ?, ?)
        """,
            (service, environment, checksum, config_data),
        )

        conn.commit()
        conn.close()

    def _analyze_configuration_changes(self, baseline: Dict[str, Any], current: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze changes between baseline and current configuration."""
        from deepdiff import DeepDiff

        diff = DeepDiff(baseline, current, ignore_order=True, verbose_level=2)
        changes = []

        # Process different types of changes
        for change_type, change_data in diff.items():
            if change_type == "values_changed":
                for path, change_info in change_data.items():
                    changes.append(
                        {
                            "type": "modified",
                            "path": str(path).replace("root", "").replace("['", ".").replace("']", "").strip("."),
                            "old_value": change_info["old_value"],
                            "new_value": change_info["new_value"],
                        }
                    )
            elif change_type == "dictionary_item_added":
                for path in change_data:
                    changes.append(
                        {
                            "type": "added",
                            "path": str(path).replace("root", "").replace("['", ".").replace("']", "").strip("."),
                            "value": change_data[path],
                        }
                    )
            elif change_type == "dictionary_item_removed":
                for path in change_data:
                    changes.append(
                        {
                            "type": "removed",
                            "path": str(path).replace("root", "").replace("['", ".").replace("']", "").strip("."),
                            "value": change_data[path],
                        }
                    )

        return changes

    def _calculate_drift_percentage(self, changes: List[Dict[str, Any]], config: Dict[str, Any]) -> float:
        """Calculate drift percentage based on number of changes."""
        if not changes:
            return 0.0

        # Count total configuration keys (rough estimate)
        def count_keys(d: Dict[str, Any]) -> int:
            count = 0
            for _, value in d.items():
                count += 1
                if isinstance(value, dict):
                    count += count_keys(value)
            return count

        total_keys = count_keys(config)
        if total_keys == 0:
            return 0.0

        # Calculate percentage based on number of changes
        return min((len(changes) / total_keys) * 100, 100.0)

    def _assess_drift_risk_level(self, changes: List[Dict[str, Any]], drift_percentage: float) -> str:
        """Assess risk level of configuration drift."""
        # Check for critical security changes
        for change in changes:
            path_lower = change["path"].lower()
            if any(keyword in path_lower for keyword in ["ssl", "security", "auth", "password", "key"]):
                return "critical"

        # Assess based on drift percentage and change types
        if drift_percentage > 50:
            return "critical"
        elif drift_percentage > 25:
            return "high"
        elif drift_percentage > 10:
            return "medium"
        else:
            return "low"

    def _store_validation_results(self, result: ValidationResult) -> None:
        """Store validation results in database."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO validation_runs
            (configuration_path, service, environment, schema_valid, dependency_valid,
             security_compliant, drift_detected, overall_valid, validation_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result.configuration_path,
                result.service,
                result.environment,
                result.schema_valid,
                result.dependency_valid,
                result.security_compliant,
                result.drift_detected,
                result.overall_valid,
                result.validation_score,
            ),
        )

        conn.commit()
        conn.close()

    def _store_drift_detection(
        self,
        service: str,
        environment: str,
        baseline_checksum: str,
        current_checksum: str,
        drift_percentage: float,
        risk_level: str,
        changes_count: int,
    ) -> None:
        """Store drift detection results in database."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO drift_detections
            (service, environment, baseline_checksum, current_checksum,
             drift_percentage, risk_level, changes_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (service, environment, baseline_checksum, current_checksum, drift_percentage, risk_level, changes_count),
        )

        conn.commit()
        conn.close()

    def validate_multiple_configurations(
        self, configurations: Dict[str, Dict[str, Any]], service: str
    ) -> Dict[str, ValidationResult]:
        """Validate multiple environment configurations.

        Args:
            configurations: Dictionary mapping environment names to configurations
            service: Service name

        Returns:
            Dictionary of validation results by environment
        """
        results = {}

        for environment, config in configurations.items():
            results[environment] = self.validate_configuration(config, service, environment, f"{service}_{environment}")

        return results

    def create_baseline(self, config: Dict[str, Any], service: str, environment: str) -> None:
        """Create a new baseline configuration.

        Args:
            config: Configuration to use as baseline
            service: Service name
            environment: Environment name
        """
        config_str = json.dumps(config, sort_keys=True)
        checksum = hashlib.sha256(config_str.encode()).hexdigest()

        self._store_baseline(service, environment, checksum, config_str)
        logger.info("Created baseline for %s in %s environment", service, environment)


def main() -> None:
    """Run configuration validation from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="ViolentUTF Configuration Validation Tool")
    parser.add_argument("config_file", help="Path to configuration file to validate")
    parser.add_argument("--service", required=True, help="Service name")
    parser.add_argument("--environment", required=True, help="Environment name")
    parser.add_argument("--schemas-path", default="schemas", help="Path to validation schemas")
    parser.add_argument("--create-baseline", action="store_true", help="Create baseline from this configuration")
    parser.add_argument("--output", help="Output file for validation results (JSON)")
    parser.add_argument("--database", default="config_validation.db", help="Database file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration file
    with open(args.config_file, "r", encoding="utf-8") as f:
        if args.config_file.endswith(".yaml") or args.config_file.endswith(".yml"):
            config = yaml.safe_load(f)
        elif args.config_file.endswith(".json"):
            config = json.load(f)
        else:
            # Try to parse as JSON first, then YAML
            content = f.read()
            try:
                config = json.loads(content)
            except json.JSONDecodeError:
                config = yaml.safe_load(content)

    # Initialize validator
    validator = ConfigurationValidator(args.schemas_path, args.database)

    # Create baseline if requested
    if args.create_baseline:
        validator.create_baseline(config, args.service, args.environment)
        print(f"Baseline created for {args.service} in {args.environment}")
        return

    # Perform validation
    result = validator.validate_configuration(config, args.service, args.environment, args.config_file)

    # Convert to dictionary for JSON serialization
    result_dict = {
        "configuration_path": result.configuration_path,
        "service": result.service,
        "environment": result.environment,
        "validation_timestamp": result.validation_timestamp,
        "overall_valid": result.overall_valid,
        "validation_score": result.validation_score,
        "schema_validation": {
            "valid": result.schema_valid,
            "errors": result.schema_errors,
            "warnings": result.schema_warnings,
        },
        "dependency_validation": {"valid": result.dependency_valid, "errors": result.dependency_errors},
        "security_compliance": {"compliant": result.security_compliant, "issues": result.security_issues},
        "drift_detection": {"drift_detected": result.drift_detected, "drift_details": result.drift_details},
    }

    # Output results
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2)
        print(f"Validation results saved to {args.output}")
    else:
        print(json.dumps(result_dict, indent=2))


if __name__ == "__main__":
    main()
