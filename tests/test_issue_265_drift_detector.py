# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for Configuration Drift Detection functionality - Issue #265."""

import pytest
from datetime import datetime
from typing import Any, Dict, List

# These imports will fail initially (RED phase of TDD)
from violentutf_api.fastapi_app.app.services.config_monitoring import (
    DriftDetector,
    DriftResult,
    DriftChange,
)


class TestDriftDetector:
    """Test DriftDetector class functionality."""

    def test_detect_no_drift(self):
        """Test drift detection when no changes occurred."""
        # GIVEN: Baseline and identical current configuration
        baseline_config = {"host": "postgres", "port": 5432}
        current_config = {"host": "postgres", "port": 5432}

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: No drift should be detected
        assert drift_result.has_drift is False
        assert len(drift_result.changes) == 0
        assert drift_result.severity == "none"

    def test_detect_value_modification(self):
        """Test drift detection for modified values."""
        # GIVEN: Baseline and modified configuration
        baseline_config = {"host": "postgres", "port": 5432}
        current_config = {"host": "postgres", "port": 5433}

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: Drift should be detected
        assert drift_result.has_drift is True
        assert len(drift_result.changes) == 1
        assert drift_result.changes[0].change_type == "modified"
        assert drift_result.changes[0].field_path == "port"
        assert drift_result.changes[0].old_value == 5432
        assert drift_result.changes[0].new_value == 5433

    def test_detect_added_configuration(self):
        """Test drift detection for added configurations."""
        # GIVEN: Baseline and configuration with added values
        baseline_config = {"host": "postgres"}
        current_config = {"host": "postgres", "port": 5432}

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: Addition should be detected
        assert drift_result.has_drift is True
        assert len(drift_result.changes) == 1
        assert drift_result.changes[0].change_type == "added"
        assert drift_result.changes[0].field_path == "port"
        assert drift_result.changes[0].old_value is None
        assert drift_result.changes[0].new_value == 5432

    def test_detect_removed_configuration(self):
        """Test drift detection for removed configurations."""
        # GIVEN: Baseline and configuration with removed values
        baseline_config = {"host": "postgres", "port": 5432}
        current_config = {"host": "postgres"}

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: Removal should be detected
        assert drift_result.has_drift is True
        assert len(drift_result.changes) == 1
        assert drift_result.changes[0].change_type == "removed"
        assert drift_result.changes[0].field_path == "port"
        assert drift_result.changes[0].old_value == 5432
        assert drift_result.changes[0].new_value is None

    def test_detect_nested_configuration_drift(self):
        """Test drift detection for nested configuration changes."""
        # GIVEN: Nested configuration with changes
        baseline_config = {
            "database": {
                "host": "postgres",
                "connection": {
                    "timeout": 30,
                    "pool_size": 10
                }
            }
        }
        current_config = {
            "database": {
                "host": "postgres",
                "connection": {
                    "timeout": 60,
                    "pool_size": 10
                }
            }
        }

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: Nested change should be detected
        assert drift_result.has_drift is True
        assert len(drift_result.changes) == 1
        assert drift_result.changes[0].field_path == "database.connection.timeout"
        assert drift_result.changes[0].old_value == 30
        assert drift_result.changes[0].new_value == 60

    def test_detect_multiple_changes(self):
        """Test drift detection for multiple configuration changes."""
        # GIVEN: Configuration with multiple changes
        baseline_config = {
            "host": "postgres",
            "port": 5432,
            "timeout": 30,
            "ssl": False
        }
        current_config = {
            "host": "new_postgres",  # Modified
            "port": 5432,           # Unchanged
            "timeout": 60,          # Modified
            "ssl": False,           # Unchanged
            "retries": 3            # Added
            # removed_setting removed
        }
        baseline_config["removed_setting"] = "value"

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: All changes should be detected
        assert drift_result.has_drift is True
        assert len(drift_result.changes) == 4  # 2 modified + 1 added + 1 removed

        change_types = [change.change_type for change in drift_result.changes]
        assert "modified" in change_types
        assert "added" in change_types
        assert "removed" in change_types

    def test_severity_classification(self):
        """Test drift severity classification."""
        # GIVEN: Different types of configuration changes
        detector = DriftDetector()

        # WHEN/THEN: Testing different severity levels
        # Critical: Security-related changes
        assert detector.classify_severity("KC_DB_PASSWORD", "password123", "newpass") == "critical"
        assert detector.classify_severity("SECRET_KEY", "old_secret", "new_secret") == "critical"
        assert detector.classify_severity("JWT_SECRET_KEY", "old_jwt", "new_jwt") == "critical"

        # High: Performance-impacting changes
        assert detector.classify_severity("KC_DB_URL_PORT", 5432, 3306) == "high"
        assert detector.classify_severity("timeout", 30, 300) == "high"
        assert detector.classify_severity("pool_size", 10, 100) == "high"

        # Medium: Functional changes
        assert detector.classify_severity("KC_HOSTNAME", "localhost", "example.com") == "medium"
        assert detector.classify_severity("DEBUG", True, False) == "medium"
        assert detector.classify_severity("ENVIRONMENT", "dev", "prod") == "medium"

        # Low: Non-critical changes
        assert detector.classify_severity("DESCRIPTION", "old desc", "new desc") == "low"
        assert detector.classify_severity("VERSION", "1.0.0", "1.0.1") == "low"
        assert detector.classify_severity("comment", "old", "new") == "low"

    def test_drift_result_aggregation(self):
        """Test aggregation of drift results."""
        # GIVEN: Multiple changes with different severities
        changes = [
            DriftChange("modified", "SECRET_KEY", "old", "new", "critical"),
            DriftChange("modified", "timeout", 30, 60, "high"),
            DriftChange("modified", "description", "old", "new", "low")
        ]

        # WHEN: Creating drift result
        drift_result = DriftResult(
            has_drift=True,
            changes=changes,
            detected_at=datetime.utcnow()
        )

        # THEN: Overall severity should be highest individual severity
        assert drift_result.severity == "critical"
        assert drift_result.change_count == 3
        assert drift_result.has_critical_changes is True

    def test_ignore_unchanged_values(self):
        """Test that unchanged values are ignored in drift detection."""
        # GIVEN: Large configuration with few changes
        baseline_config = {f"key_{i}": f"value_{i}" for i in range(100)}
        current_config = baseline_config.copy()

        # Only change one value
        current_config["key_50"] = "new_value_50"

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: Only the changed value should be detected
        assert drift_result.has_drift is True
        assert len(drift_result.changes) == 1
        assert drift_result.changes[0].field_path == "key_50"
        assert drift_result.changes[0].old_value == "value_50"
        assert drift_result.changes[0].new_value == "new_value_50"

    def test_complex_nested_drift_detection(self):
        """Test drift detection in complex nested structures."""
        # GIVEN: Complex nested configuration
        baseline_config = {
            "services": {
                "keycloak": {
                    "database": {
                        "host": "postgres",
                        "port": 5432,
                        "credentials": {
                            "username": "keycloak",
                            "password": "secret123"
                        }
                    },
                    "network": {
                        "ports": [8080, 8443],
                        "health_check": {
                            "interval": 30,
                            "timeout": 5
                        }
                    }
                },
                "fastapi": {
                    "database": {
                        "url": "sqlite:///app.db",
                        "echo": False
                    }
                }
            }
        }

        current_config = {
            "services": {
                "keycloak": {
                    "database": {
                        "host": "postgres",
                        "port": 5433,  # Changed
                        "credentials": {
                            "username": "keycloak",
                            "password": "newsecret456"  # Changed - critical
                        }
                    },
                    "network": {
                        "ports": [8080, 8443, 9080],  # Added port
                        "health_check": {
                            "interval": 30,
                            "timeout": 10  # Changed
                        }
                    }
                },
                "fastapi": {
                    "database": {
                        "url": "sqlite:///app.db",
                        "echo": True  # Changed
                    }
                }
            }
        }

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: All changes should be detected with correct paths
        assert drift_result.has_drift is True
        assert len(drift_result.changes) >= 4  # At least 4 changes detected

        # Check that nested paths are correctly identified
        field_paths = [change.field_path for change in drift_result.changes]
        assert "services.keycloak.database.port" in field_paths
        assert "services.keycloak.database.credentials.password" in field_paths
        assert "services.keycloak.network.health_check.timeout" in field_paths
        assert "services.fastapi.database.echo" in field_paths

    def test_drift_detection_with_arrays(self):
        """Test drift detection with array/list changes."""
        # GIVEN: Configuration with arrays
        baseline_config = {
            "allowed_origins": ["localhost", "127.0.0.1"],
            "enabled_features": ["auth", "api", "monitoring"]
        }
        current_config = {
            "allowed_origins": ["localhost", "127.0.0.1", "example.com"],  # Added item
            "enabled_features": ["auth", "api"]  # Removed item
        }

        # WHEN: Running drift detection
        detector = DriftDetector()
        drift_result = detector.detect_drift(baseline_config, current_config)

        # THEN: Array changes should be detected
        assert drift_result.has_drift is True
        assert len(drift_result.changes) == 2

        # Check specific array changes
        change_paths = [change.field_path for change in drift_result.changes]
        assert "allowed_origins" in change_paths
        assert "enabled_features" in change_paths


class TestDriftChange:
    """Test DriftChange data class functionality."""

    def test_drift_change_creation(self):
        """Test creating a drift change."""
        # GIVEN: Change parameters
        change = DriftChange(
            change_type="modified",
            field_path="database.port",
            old_value=5432,
            new_value=5433,
            severity="medium"
        )

        # THEN: Change should be created correctly
        assert change.change_type == "modified"
        assert change.field_path == "database.port"
        assert change.old_value == 5432
        assert change.new_value == 5433
        assert change.severity == "medium"

    def test_drift_change_serialization(self):
        """Test drift change serialization."""
        # GIVEN: Drift change
        change = DriftChange(
            change_type="added",
            field_path="new_setting",
            old_value=None,
            new_value="new_value",
            severity="low"
        )

        # WHEN: Serializing
        serialized = change.to_dict()

        # THEN: Serialization should preserve all data
        assert serialized["change_type"] == "added"
        assert serialized["field_path"] == "new_setting"
        assert serialized["old_value"] is None
        assert serialized["new_value"] == "new_value"
        assert serialized["severity"] == "low"

    def test_drift_change_comparison(self):
        """Test drift change comparison for sorting."""
        # GIVEN: Multiple changes with different severities
        critical_change = DriftChange("modified", "password", "old", "new", "critical")
        high_change = DriftChange("modified", "port", 5432, 5433, "high")
        low_change = DriftChange("modified", "desc", "old", "new", "low")

        # WHEN: Sorting changes by severity
        changes = [low_change, critical_change, high_change]
        sorted_changes = sorted(changes, key=lambda x: x.severity_priority(), reverse=True)

        # THEN: Critical changes should come first
        assert sorted_changes[0].severity == "critical"
        assert sorted_changes[1].severity == "high"
        assert sorted_changes[2].severity == "low"


class TestDriftResult:
    """Test DriftResult data class functionality."""

    def test_drift_result_no_changes(self):
        """Test drift result with no changes."""
        # GIVEN: No changes
        result = DriftResult(
            has_drift=False,
            changes=[],
            detected_at=datetime.utcnow()
        )

        # THEN: Result should reflect no drift
        assert result.has_drift is False
        assert result.severity == "none"
        assert result.change_count == 0
        assert result.has_critical_changes is False

    def test_drift_result_with_changes(self):
        """Test drift result with various changes."""
        # GIVEN: Changes with different severities
        changes = [
            DriftChange("modified", "port", 5432, 5433, "medium"),
            DriftChange("added", "timeout", None, 30, "low"),
            DriftChange("removed", "old_setting", "value", None, "low")
        ]

        # WHEN: Creating result
        result = DriftResult(
            has_drift=True,
            changes=changes,
            detected_at=datetime.utcnow()
        )

        # THEN: Result should aggregate correctly
        assert result.has_drift is True
        assert result.severity == "medium"  # Highest severity
        assert result.change_count == 3
        assert result.has_critical_changes is False

    def test_drift_result_summary(self):
        """Test drift result summary generation."""
        # GIVEN: Drift result with changes
        changes = [
            DriftChange("modified", "password", "old", "new", "critical"),
            DriftChange("modified", "port", 5432, 5433, "high"),
            DriftChange("added", "feature", None, "enabled", "low")
        ]
        result = DriftResult(has_drift=True, changes=changes, detected_at=datetime.utcnow())

        # WHEN: Generating summary
        summary = result.generate_summary()

        # THEN: Summary should contain key information
        assert "3 changes detected" in summary
        assert "critical" in summary.lower()
        assert "password" in summary
        assert "port" in summary
        assert "feature" in summary
