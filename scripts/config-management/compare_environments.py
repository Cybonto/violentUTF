#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Configuration Comparison Tool for ViolentUTF - Issue #266.

Compares configurations across environments and identifies inconsistencies.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Union

import yaml
from deepdiff import DeepDiff

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConfigurationDifference:
    """Represents a difference between configurations."""

    path: str
    difference_type: str  # 'added', 'removed', 'changed', 'type_changed'
    environment_a: str
    environment_b: str
    value_a: Any
    value_b: Any
    severity: str  # 'low', 'medium', 'high', 'critical'
    impact_description: str
    service: str
    category: str = "functional"  # 'functional', 'security', 'performance'


@dataclass
class ComparisonReport:
    """Comprehensive comparison report between environments."""

    environment_a: str
    environment_b: str
    service: str
    comparison_timestamp: str
    total_differences: int
    differences_by_severity: Dict[str, int] = field(default_factory=dict)
    differences_by_category: Dict[str, int] = field(default_factory=dict)
    differences: List[ConfigurationDifference] = field(default_factory=list)
    security_issues: List[ConfigurationDifference] = field(default_factory=list)
    performance_impacts: List[ConfigurationDifference] = field(default_factory=list)
    compatibility_issues: List[ConfigurationDifference] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ConfigurationComparator:
    """Main configuration comparison engine."""

    def __init__(self, database_path: str = "config_comparison.db") -> None:
        """Initialize the configuration comparison tool.

        Args:
            database_path: Path to SQLite database for storing comparison results
        """
        self.database_path = database_path
        self.security_keywords = {
            "ssl",
            "tls",
            "https",
            "certificate",
            "key",
            "secret",
            "password",
            "token",
            "auth",
            "security",
            "encryption",
            "cipher",
            "protocol",
        }
        self.performance_keywords = {
            "timeout",
            "pool",
            "cache",
            "memory",
            "cpu",
            "thread",
            "worker",
            "connection",
            "buffer",
            "queue",
            "limit",
            "max",
            "min",
        }
        self._setup_database()

    def _setup_database(self) -> None:
        """Set up SQLite database for storing comparison results."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS comparison_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                environment_a TEXT NOT NULL,
                environment_b TEXT NOT NULL,
                service TEXT NOT NULL,
                total_differences INTEGER NOT NULL,
                high_severity_count INTEGER NOT NULL,
                critical_severity_count INTEGER NOT NULL,
                security_issues_count INTEGER NOT NULL,
                comparison_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS configuration_differences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comparison_run_id INTEGER,
                path TEXT NOT NULL,
                difference_type TEXT NOT NULL,
                environment_a TEXT NOT NULL,
                environment_b TEXT NOT NULL,
                value_a TEXT,
                value_b TEXT,
                severity TEXT NOT NULL,
                impact_description TEXT,
                service TEXT NOT NULL,
                category TEXT NOT NULL,
                FOREIGN KEY (comparison_run_id) REFERENCES comparison_runs (id)
            )
        """
        )

        conn.commit()
        conn.close()

    def compare_environments(
        self, config_a: Dict[str, Any], config_b: Dict[str, Any], env_a: str, env_b: str, service: str = "unknown"
    ) -> ComparisonReport:
        """Compare configurations between two environments.

        Args:
            config_a: Configuration from environment A
            config_b: Configuration from environment B
            env_a: Name of environment A
            env_b: Name of environment B
            service: Service name

        Returns:
            ComparisonReport with detailed differences
        """
        logger.info("Comparing %s configurations: %s vs %s", service, env_a, env_b)

        # Perform deep comparison
        diff = DeepDiff(config_a, config_b, ignore_order=True, verbose_level=2)

        # Convert differences to structured format
        differences = self._process_deep_diff(diff, env_a, env_b, service)

        # Categorize and analyze differences
        security_issues = [d for d in differences if d.category == "security"]
        performance_impacts = [d for d in differences if d.category == "performance"]
        compatibility_issues = self._find_compatibility_issues(differences)

        # Generate recommendations
        recommendations = self._generate_recommendations(differences, env_a, env_b)

        # Create comparison report
        report = ComparisonReport(
            environment_a=env_a,
            environment_b=env_b,
            service=service,
            comparison_timestamp=datetime.now().isoformat(),
            total_differences=len(differences),
            differences=differences,
            security_issues=security_issues,
            performance_impacts=performance_impacts,
            compatibility_issues=compatibility_issues,
            recommendations=recommendations,
        )

        # Calculate statistics
        report.differences_by_severity = self._count_by_severity(differences)
        report.differences_by_category = self._count_by_category(differences)

        # Store results in database
        self._store_comparison_results(report)

        logger.info("Comparison completed: %d differences found", len(differences))
        return report

    def _process_deep_diff(self, diff: DeepDiff, env_a: str, env_b: str, service: str) -> List[ConfigurationDifference]:
        """Process DeepDiff results into structured differences.

        Args:
            diff: DeepDiff result object
            env_a: Environment A name
            env_b: Environment B name
            service: Service name

        Returns:
            List of ConfigurationDifference objects
        """
        differences = []

        # Process dictionary item added
        if "dictionary_item_added" in diff:
            for item in diff["dictionary_item_added"]:
                path = str(item).replace("root", "").replace("['", ".").replace("']", "").strip(".")
                differences.append(
                    ConfigurationDifference(
                        path=path,
                        difference_type="added",
                        environment_a=env_a,
                        environment_b=env_b,
                        value_a=None,
                        value_b=diff["dictionary_item_added"][item],
                        severity=self._determine_severity(path, "added"),
                        impact_description=f"Configuration key '{path}' added in {env_b}",
                        service=service,
                        category=self._categorize_difference(path),
                    )
                )

        # Process dictionary item removed
        if "dictionary_item_removed" in diff:
            for item in diff["dictionary_item_removed"]:
                path = str(item).replace("root", "").replace("['", ".").replace("']", "").strip(".")
                differences.append(
                    ConfigurationDifference(
                        path=path,
                        difference_type="removed",
                        environment_a=env_a,
                        environment_b=env_b,
                        value_a=diff["dictionary_item_removed"][item],
                        value_b=None,
                        severity=self._determine_severity(path, "removed"),
                        impact_description=f"Configuration key '{path}' removed from {env_b}",
                        service=service,
                        category=self._categorize_difference(path),
                    )
                )

        # Process values changed
        if "values_changed" in diff:
            for item in diff["values_changed"]:
                path = str(item).replace("root", "").replace("['", ".").replace("']", "").strip(".")
                value_a = diff["values_changed"][item]["old_value"]
                value_b = diff["values_changed"][item]["new_value"]

                differences.append(
                    ConfigurationDifference(
                        path=path,
                        difference_type="changed",
                        environment_a=env_a,
                        environment_b=env_b,
                        value_a=value_a,
                        value_b=value_b,
                        severity=self._determine_severity(path, "changed", value_a, value_b),
                        impact_description=self._describe_change_impact(path, value_a, value_b),
                        service=service,
                        category=self._categorize_difference(path),
                    )
                )

        # Process type changes
        if "type_changes" in diff:
            for item in diff["type_changes"]:
                path = str(item).replace("root", "").replace("['", ".").replace("']", "").strip(".")
                value_a = diff["type_changes"][item]["old_value"]
                value_b = diff["type_changes"][item]["new_value"]

                differences.append(
                    ConfigurationDifference(
                        path=path,
                        difference_type="type_changed",
                        environment_a=env_a,
                        environment_b=env_b,
                        value_a=value_a,
                        value_b=value_b,
                        severity="high",  # Type changes are generally serious
                        impact_description=(
                            f"Configuration '{path}' type changed from "
                            f"{type(value_a).__name__} to {type(value_b).__name__}"
                        ),
                        service=service,
                        category=self._categorize_difference(path),
                    )
                )

        return differences

    def _determine_severity(
        self,
        path: str,
        change_type: str,
        value_a: Union[str, int, bool, None] = None,
        value_b: Union[str, int, bool, None] = None,
    ) -> str:
        """Determine the severity of a configuration difference.

        Args:
            path: Configuration path
            change_type: Type of change
            value_a: Original value
            value_b: New value

        Returns:
            Severity level string
        """
        path_lower = path.lower()

        # Critical severity conditions
        if any(keyword in path_lower for keyword in ["ssl", "security", "auth", "password", "secret", "key"]):
            if change_type in ["removed", "type_changed"]:
                return "critical"
            if change_type == "changed":
                # SSL/Security downgrades are critical
                if isinstance(value_a, bool) and isinstance(value_b, bool) and value_a is True and value_b is False:
                    return "critical"
                if (
                    isinstance(value_a, str)
                    and isinstance(value_b, str)
                    and value_a.lower() in ["all", "required", "enabled"]
                    and value_b.lower() in ["none", "disabled", "false"]
                ):
                    return "critical"

        # High severity conditions
        if any(keyword in path_lower for keyword in ["database", "connection", "host", "port"]):
            if change_type in ["removed", "changed"]:
                return "high"

        # Medium severity conditions
        if any(keyword in path_lower for keyword in ["timeout", "limit", "pool", "cache"]):
            return "medium"

        # Low severity (default)
        return "low"

    def _categorize_difference(self, path: str) -> str:
        """Categorize a configuration difference.

        Args:
            path: Configuration path

        Returns:
            Category string
        """
        path_lower = path.lower()

        if any(keyword in path_lower for keyword in self.security_keywords):
            return "security"
        elif any(keyword in path_lower for keyword in self.performance_keywords):
            return "performance"
        else:
            return "functional"

    def _describe_change_impact(
        self, path: str, value_a: Union[str, int, bool, None], value_b: Union[str, int, bool, None]
    ) -> str:
        """Describe the impact of a configuration change.

        Args:
            path: Configuration path
            value_a: Original value
            value_b: New value

        Returns:
            Impact description string
        """
        path_lower = path.lower()

        # Security-related changes
        if "ssl" in path_lower or "tls" in path_lower:
            if value_a != value_b:
                return f"SSL/TLS configuration changed from '{value_a}' to '{value_b}' - may affect security posture"

        # Authentication changes
        if "auth" in path_lower or "password" in path_lower:
            return "Authentication configuration changed - may affect access control"

        # Performance-related changes
        if any(keyword in path_lower for keyword in ["timeout", "pool", "cache", "memory"]):
            return f"Performance configuration changed from '{value_a}' to '{value_b}' - may affect system performance"

        # Database changes
        if "database" in path_lower or "connection" in path_lower:
            return f"Database configuration changed from '{value_a}' to '{value_b}' - may affect data access"

        # Generic change description
        return f"Configuration changed from '{value_a}' to '{value_b}'"

    def _find_compatibility_issues(self, differences: List[ConfigurationDifference]) -> List[ConfigurationDifference]:
        """Find compatibility issues among differences.

        Args:
            differences: List of configuration differences

        Returns:
            List of compatibility issues
        """
        compatibility_issues = []

        # Check for SSL/TLS compatibility issues
        ssl_diffs = [d for d in differences if "ssl" in d.path.lower() or "tls" in d.path.lower()]
        if ssl_diffs:
            for diff in ssl_diffs:
                if diff.severity in ["high", "critical"]:
                    compatibility_issues.append(diff)

        # Check for version compatibility issues
        version_diffs = [d for d in differences if "version" in d.path.lower()]
        for diff in version_diffs:
            if isinstance(diff.value_a, str) and isinstance(diff.value_b, str):
                # Simple version comparison logic
                if self._compare_versions(diff.value_a, diff.value_b) != 0:
                    compatibility_issues.append(diff)

        return compatibility_issues

    def _compare_versions(self, version_a: str, version_b: str) -> int:
        """Compare two version strings.

        Args:
            version_a: First version string
            version_b: Second version string

        Returns:
            -1 if a < b, 0 if equal, 1 if a > b
        """
        try:
            parts_a = [int(x) for x in version_a.split(".")]
            parts_b = [int(x) for x in version_b.split(".")]

            # Pad with zeros to make equal length
            max_len = max(len(parts_a), len(parts_b))
            parts_a.extend([0] * (max_len - len(parts_a)))
            parts_b.extend([0] * (max_len - len(parts_b)))

            for a, b in zip(parts_a, parts_b):
                if a < b:
                    return -1
                elif a > b:
                    return 1
            return 0
        except (ValueError, AttributeError):
            # If version parsing fails, just compare strings
            if version_a < version_b:
                return -1
            elif version_a > version_b:
                return 1
            return 0

    def _generate_recommendations(
        self, differences: List[ConfigurationDifference], env_a: str, env_b: str
    ) -> List[str]:
        """Generate recommendations based on differences.

        Args:
            differences: List of configuration differences
            env_a: Environment A name
            env_b: Environment B name

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Security recommendations
        security_diffs = [d for d in differences if d.category == "security"]
        if security_diffs:
            critical_security = [d for d in security_diffs if d.severity == "critical"]
            if critical_security:
                recommendations.append(
                    f"URGENT: Address {len(critical_security)} critical security "
                    f"configuration differences between {env_a} and {env_b}"
                )

            recommendations.append("Review and standardize security configurations across environments")

        # Performance recommendations
        performance_diffs = [d for d in differences if d.category == "performance"]
        if performance_diffs:
            recommendations.append(f"Optimize performance configurations - {len(performance_diffs)} differences found")

        # SSL/TLS recommendations
        ssl_diffs = [d for d in differences if "ssl" in d.path.lower()]
        if ssl_diffs:
            recommendations.append("Standardize SSL/TLS configurations across all environments")

        # Database recommendations
        db_diffs = [d for d in differences if "database" in d.path.lower()]
        if db_diffs:
            recommendations.append("Review database connection configurations for consistency")

        # General recommendations
        high_severity_count = len([d for d in differences if d.severity == "high"])
        if high_severity_count > 5:
            recommendations.append(
                f"Consider implementing configuration templates to reduce "
                f"{high_severity_count} high-severity differences"
            )

        return recommendations

    def _count_by_severity(self, differences: List[ConfigurationDifference]) -> Dict[str, int]:
        """Count differences by severity level.

        Args:
            differences: List of configuration differences

        Returns:
            Dictionary with severity counts
        """
        counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for diff in differences:
            if diff.severity in counts:
                counts[diff.severity] += 1
        return counts

    def _count_by_category(self, differences: List[ConfigurationDifference]) -> Dict[str, int]:
        """Count differences by category.

        Args:
            differences: List of configuration differences

        Returns:
            Dictionary with category counts
        """
        counts = {"functional": 0, "security": 0, "performance": 0}
        for diff in differences:
            if diff.category in counts:
                counts[diff.category] += 1
        return counts

    def _store_comparison_results(self, report: ComparisonReport) -> None:
        """Store comparison results in database.

        Args:
            report: Comparison report to store
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        # Store comparison run
        cursor.execute(
            """
            INSERT INTO comparison_runs
            (environment_a, environment_b, service, total_differences,
             high_severity_count, critical_severity_count, security_issues_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                report.environment_a,
                report.environment_b,
                report.service,
                report.total_differences,
                report.differences_by_severity.get("high", 0),
                report.differences_by_severity.get("critical", 0),
                len(report.security_issues),
            ),
        )

        comparison_run_id = cursor.lastrowid

        # Store individual differences
        for diff in report.differences:
            cursor.execute(
                """
                INSERT INTO configuration_differences
                (comparison_run_id, path, difference_type, environment_a, environment_b,
                 value_a, value_b, severity, impact_description, service, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    comparison_run_id,
                    diff.path,
                    diff.difference_type,
                    diff.environment_a,
                    diff.environment_b,
                    str(diff.value_a) if diff.value_a is not None else None,
                    str(diff.value_b) if diff.value_b is not None else None,
                    diff.severity,
                    diff.impact_description,
                    diff.service,
                    diff.category,
                ),
            )

        conn.commit()
        conn.close()

    def compare_multiple_environments(
        self, configurations: Dict[str, Dict[str, Any]], service: str = "unknown"
    ) -> Dict[str, ComparisonReport]:
        """Compare configurations across multiple environments.

        Args:
            configurations: Dictionary mapping environment names to their configurations
            service: Service name

        Returns:
            Dictionary of comparison reports
        """
        reports = {}
        environments = list(configurations.keys())

        # Compare each pair of environments
        for i, env_a in enumerate(environments):
            for env_b in environments[i + 1 :]:
                comparison_key = f"{env_a}_vs_{env_b}"
                reports[comparison_key] = self.compare_environments(
                    configurations[env_a], configurations[env_b], env_a, env_b, service
                )

        return reports

    def generate_summary_report(self, reports: Dict[str, ComparisonReport]) -> Dict[str, Any]:
        """Generate a summary report from multiple comparison reports.

        Args:
            reports: Dictionary of comparison reports

        Returns:
            Summary report dictionary
        """
        total_differences = sum(report.total_differences for report in reports.values())
        total_critical = sum(report.differences_by_severity.get("critical", 0) for report in reports.values())
        total_security_issues = sum(len(report.security_issues) for report in reports.values())

        # Collect all recommendations
        all_recommendations = []
        for report in reports.values():
            all_recommendations.extend(report.recommendations)

        # Remove duplicates while preserving order
        unique_recommendations = list(dict.fromkeys(all_recommendations))

        return {
            "summary_timestamp": datetime.now().isoformat(),
            "total_comparisons": len(reports),
            "total_differences": total_differences,
            "critical_differences": total_critical,
            "security_issues": total_security_issues,
            "environments_compared": list(
                set(env for report in reports.values() for env in [report.environment_a, report.environment_b])
            ),
            "recommendations": unique_recommendations,
            "comparison_details": {
                key: {
                    "total_differences": report.total_differences,
                    "severity_breakdown": report.differences_by_severity,
                    "category_breakdown": report.differences_by_category,
                    "security_issues_count": len(report.security_issues),
                }
                for key, report in reports.items()
            },
        }


def main() -> None:
    """Run configuration comparison from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="ViolentUTF Configuration Comparison Tool")
    parser.add_argument("config_a", help="Path to first configuration file")
    parser.add_argument("config_b", help="Path to second configuration file")
    parser.add_argument("--env-a", default="env_a", help="Name of first environment")
    parser.add_argument("--env-b", default="env_b", help="Name of second environment")
    parser.add_argument("--service", default="unknown", help="Service name")
    parser.add_argument("--output", help="Output file for comparison results (JSON)")
    parser.add_argument("--database", default="config_comparison.db", help="Database file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration files
    def load_config(path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            if path.endswith(".yaml") or path.endswith(".yml"):
                return yaml.safe_load(f)
            elif path.endswith(".json"):
                return json.load(f)
            else:
                # Try to parse as JSON first, then YAML
                content = f.read()
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return yaml.safe_load(content)

    config_a = load_config(args.config_a)
    config_b = load_config(args.config_b)

    # Initialize comparison tool
    comparator = ConfigurationComparator(args.database)

    # Perform comparison
    report = comparator.compare_environments(config_a, config_b, args.env_a, args.env_b, args.service)

    # Convert to dictionary for JSON serialization
    report_dict = {
        "environment_a": report.environment_a,
        "environment_b": report.environment_b,
        "service": report.service,
        "comparison_timestamp": report.comparison_timestamp,
        "total_differences": report.total_differences,
        "differences_by_severity": report.differences_by_severity,
        "differences_by_category": report.differences_by_category,
        "security_issues_count": len(report.security_issues),
        "performance_impacts_count": len(report.performance_impacts),
        "recommendations": report.recommendations,
        "differences": [
            {
                "path": d.path,
                "type": d.difference_type,
                "severity": d.severity,
                "category": d.category,
                "impact": d.impact_description,
                "value_a": d.value_a,
                "value_b": d.value_b,
            }
            for d in report.differences
        ],
    }

    # Output results
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2)
        print(f"Comparison report saved to {args.output}")
    else:
        print(json.dumps(report_dict, indent=2))


if __name__ == "__main__":
    main()
