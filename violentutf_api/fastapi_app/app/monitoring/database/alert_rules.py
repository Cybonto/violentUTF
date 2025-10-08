# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Alert Rules Processor for Issue #270

Processes alert rules for database performance monitoring, evaluates metrics
against thresholds, and triggers alerts when rules are violated.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class AlertRule:
    """Represents a single alert rule."""

    def __init__(
        self,
        name: str,
        metric: str,
        threshold: float,
        operator: str,
        severity: str,
        message: str,
        description: str = "",
        enabled: bool = True,
    ) -> None:
        """Initialize alert rule."""
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.operator = operator
        self.severity = severity
        self.message = message
        self.description = description
        self.enabled = enabled
        self.violation_count = 0

    def evaluate(self, metric_value: float) -> bool:
        """
        Evaluate if metric value violates the rule.

        Args:
            metric_value: Current metric value

        Returns:
            True if rule is violated, False otherwise
        """
        if not self.enabled:
            return False

        if self.operator == "greater_than":
            return metric_value > self.threshold
        elif self.operator == "less_than":
            return metric_value < self.threshold
        elif self.operator == "equals":
            return metric_value == self.threshold
        elif self.operator == "not_equals":
            return metric_value != self.threshold
        else:
            logger.warning("Unknown operator: %s", self.operator)
            return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "name": self.name,
            "metric": self.metric,
            "threshold": self.threshold,
            "operator": self.operator,
            "severity": self.severity,
            "message": self.message,
            "description": self.description,
            "enabled": self.enabled,
        }


class AlertRuleProcessor:
    """
    Processes alert rules and evaluates metrics against configured thresholds.

    Loads rules from YAML configuration and provides methods to evaluate
    metrics and generate alerts.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize alert rule processor.

        Args:
            config_path: Path to alert rules YAML file
        """
        if config_path is None:
            # Default config path
            config_path = Path(__file__).parents[5] / "configs" / "monitoring" / "alert_rules.yaml"

        self.config_path = config_path
        self.rules: Dict[str, Dict[str, AlertRule]] = {}
        self.settings: Dict[str, Any] = {}
        self.violation_history: Dict[str, List[datetime]] = {}
        self.load_rules()

    def load_rules(self) -> None:
        """Load alert rules from YAML configuration file."""
        try:
            if not self.config_path.exists():
                logger.warning("Alert rules config not found: %s", self.config_path)
                self._load_default_rules()
                return

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # Load alert settings
            self.settings = config.get("alert_settings", {})

            # Load database-specific rules
            for category in ["postgresql_alerts", "sqlite_alerts", "storage_alerts", "service_availability_alerts"]:
                if category not in config:
                    continue

                db_type = category.split("_")[0]
                self.rules[db_type] = {}

                for rule_name, rule_config in config[category].items():
                    rule = AlertRule(
                        name=rule_name,
                        metric=rule_config["metric"],
                        threshold=rule_config["threshold"],
                        operator=rule_config["operator"],
                        severity=rule_config["severity"],
                        message=rule_config["message"],
                        description=rule_config.get("description", ""),
                        enabled=rule_config.get("enabled", True),
                    )
                    self.rules[db_type][rule_name] = rule

            logger.info("Loaded %d alert rules", sum(len(rules) for rules in self.rules.values()))

        except Exception as e:
            logger.error("Error loading alert rules: %s", e)
            self._load_default_rules()

    def _load_default_rules(self) -> None:
        """Load minimal default rules if config file not available."""
        self.rules = {
            "postgresql": {
                "connection_pool_exhaustion": AlertRule(
                    name="connection_pool_exhaustion",
                    metric="connection_pool_usage_percent",
                    threshold=80.0,
                    operator="greater_than",
                    severity="critical",
                    message="PostgreSQL connection pool usage above 80%",
                ),
            },
            "sqlite": {
                "file_size_critical": AlertRule(
                    name="file_size_critical",
                    metric="database_size_mb",
                    threshold=1000.0,
                    operator="greater_than",
                    severity="critical",
                    message="SQLite database size exceeds 1GB",
                ),
            },
        }
        self.settings = {
            "consecutive_violations_required": 2,
            "alert_cooldown_seconds": 300,
            "max_alerts_per_hour": 20,
        }

    def evaluate_metric(self, db_type: str, metric_name: str, metric_value: float) -> List[Dict[str, Any]]:
        """
        Evaluate a metric against all applicable rules.

        Args:
            db_type: Database type (postgresql, sqlite, etc.)
            metric_name: Metric name
            metric_value: Current metric value

        Returns:
            List of triggered alerts
        """
        triggered_alerts = []

        if db_type not in self.rules:
            return triggered_alerts

        for rule_name, rule in self.rules[db_type].items():
            if rule.metric == metric_name and rule.evaluate(metric_value):
                # Check consecutive violations requirement
                violation_key = f"{db_type}:{rule_name}"
                if violation_key not in self.violation_history:
                    self.violation_history[violation_key] = []

                self.violation_history[violation_key].append(datetime.now(timezone.utc))

                # Keep only recent violations
                cutoff = datetime.now(timezone.utc).timestamp() - 3600  # 1 hour
                self.violation_history[violation_key] = [
                    ts for ts in self.violation_history[violation_key] if ts.timestamp() > cutoff
                ]

                # Check if meets consecutive violations requirement
                consecutive_required = self.settings.get("consecutive_violations_required", 1)
                recent_violations = len(self.violation_history[violation_key])

                if recent_violations >= consecutive_required:
                    alert = {
                        "rule_name": rule_name,
                        "metric": metric_name,
                        "current_value": metric_value,
                        "threshold": rule.threshold,
                        "operator": rule.operator,
                        "severity": rule.severity,
                        "message": rule.message,
                        "description": rule.description,
                        "db_type": db_type,
                        "timestamp": datetime.now(timezone.utc),
                        "violation_count": recent_violations,
                    }
                    triggered_alerts.append(alert)
            else:
                # Clear violation history if metric is within threshold
                violation_key = f"{db_type}:{rule_name}"
                if violation_key in self.violation_history:
                    self.violation_history[violation_key] = []

        return triggered_alerts

    def evaluate_all_metrics(self, db_type: str, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Evaluate multiple metrics at once.

        Args:
            db_type: Database type
            metrics: Dictionary of metric_name -> value

        Returns:
            List of all triggered alerts
        """
        all_alerts = []

        for metric_name, metric_value in metrics.items():
            alerts = self.evaluate_metric(db_type, metric_name, metric_value)
            all_alerts.extend(alerts)

        return all_alerts

    def get_rules_for_db_type(self, db_type: str) -> Dict[str, AlertRule]:
        """
        Get all rules for a specific database type.

        Args:
            db_type: Database type

        Returns:
            Dictionary of rule_name -> AlertRule
        """
        return self.rules.get(db_type, {})

    def get_all_rules(self) -> Dict[str, Dict[str, AlertRule]]:
        """Get all loaded rules."""
        return self.rules

    def get_settings(self) -> Dict[str, Any]:
        """Get alert settings."""
        return self.settings

    def reload_rules(self) -> None:
        """Reload rules from configuration file."""
        self.rules = {}
        self.settings = {}
        self.violation_history = {}
        self.load_rules()
