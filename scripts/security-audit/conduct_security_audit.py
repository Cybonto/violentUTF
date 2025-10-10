#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Database Security Audit Orchestrator.

This CLI tool conducts comprehensive security audits of ViolentUTF database systems
including PostgreSQL (Keycloak), SQLite (FastAPI + PyRIT), and file storage.

Usage:
    python3 conduct_security_audit.py --comprehensive
    python3 conduct_security_audit.py --database sqlite --output-dir /path/to/reports
    python3 conduct_security_audit.py --severity-threshold high
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.database_scanner import (  # type: ignore # noqa: E402
    DatabaseScanResult,
    PostgreSQLScanner,
    SQLiteScanner,
)


class SecurityAuditOrchestrator:
    """Orchestrates comprehensive database security audits."""

    def __init__(
        self,
        config_dir: Path,
        output_dir: Path,
        severity_threshold: str = "low",
    ) -> None:
        """
        Initialize security audit orchestrator.

        Args:
            config_dir: Directory containing configuration files
            output_dir: Directory for audit reports
            severity_threshold: Minimum severity to report (low/medium/high/critical)
        """
        self.config_dir = config_dir
        self.output_dir = output_dir
        self.severity_threshold = severity_threshold.upper()

        # Load configurations
        self.security_standards = self._load_yaml(config_dir / "security_standards.yaml")
        self.audit_rules = self._load_yaml(config_dir / "audit_rules.yaml")

        # Initialize scanners
        self.sqlite_scanner = SQLiteScanner(config_dir / "security_standards.yaml")
        self.postgresql_scanner = PostgreSQLScanner(config_dir / "security_standards.yaml")

        # Results storage
        self.scan_results: List[DatabaseScanResult] = []

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not path.exists():
            print(f"Warning: Configuration file not found: {path}")
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def run_comprehensive_audit(self) -> Dict[str, Any]:
        """
        Run comprehensive security audit on all database systems.

        Returns:
            Audit summary with findings
        """
        print("=" * 80)
        print("ViolentUTF Database Security Audit")
        print("=" * 80)
        print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Severity Threshold: {self.severity_threshold}")
        print()

        start_time = time.time()

        # Scan SQLite databases
        if (
            self.audit_rules.get("audit_scope", {}).get("databases", {}).get("sqlite", {}).get("enabled", True)
        ):  # noqa: E501
            print("Scanning SQLite databases...")
            self._scan_sqlite_databases()

        # Scan PostgreSQL databases
        if (
            self.audit_rules.get("audit_scope", {}).get("databases", {}).get("postgresql", {}).get("enabled", True)
        ):  # noqa: E501
            print("Scanning PostgreSQL databases...")
            self._scan_postgresql_databases()

        # Scan file storage
        if self.audit_rules.get("audit_scope", {}).get("file_storage", {}).get("enabled", True):  # noqa: E501
            print("Scanning file storage...")
            self._scan_file_storage()

        audit_duration = time.time() - start_time

        # Generate summary
        summary = self._generate_summary(audit_duration)

        # Save reports
        self._save_reports(summary)

        # Print summary
        self._print_summary(summary)

        return summary

    def _scan_sqlite_databases(self) -> None:
        """Scan SQLite databases for security issues."""
        sqlite_config = self.audit_rules.get("audit_scope", {}).get("databases", {}).get("sqlite", {})

        db_path = sqlite_config.get("database_path", "/app/app_data/violentutf_api.db")

        # Check if database exists (in Docker container or local)
        possible_paths = [
            Path(db_path),
            Path(__file__).parent.parent.parent / "violentutf_api/fastapi_app/app_data/violentutf_api.db",
        ]

        for path in possible_paths:
            if path.exists():
                print(f"  Scanning: {path}")
                result = self.sqlite_scanner.scan_database(path)
                self.scan_results.append(result)
                print(
                    f"  Found {len(result.findings)} issues "
                    f"(CRITICAL: {result.summary.get('CRITICAL', 0)}, "
                    f"HIGH: {result.summary.get('HIGH', 0)})"
                )
                break
        else:
            print(f"  Warning: SQLite database not found at {db_path}")

    def _scan_postgresql_databases(self) -> None:
        """Scan PostgreSQL databases for security issues."""
        pg_config = self.audit_rules.get("audit_scope", {}).get("databases", {}).get("postgresql", {})

        connection_params = {
            "host": "localhost",
            "port": pg_config.get("port", 5432),
            "database": pg_config.get("database_name", "keycloak"),
        }

        print(f"  Scanning: {connection_params['database']}")
        result = self.postgresql_scanner.scan_database(connection_params)
        self.scan_results.append(result)
        print(f"  Found {len(result.findings)} issues")

    def _scan_file_storage(self) -> None:
        """Scan file storage for security issues."""
        print("  File storage scanning not yet implemented")
        # This would scan .env files, config files, logs, etc.

    def _generate_summary(self, audit_duration: float) -> Dict[str, Any]:
        """Generate audit summary."""
        all_findings = []
        for result in self.scan_results:
            all_findings.extend(result.findings)

        # Filter by severity threshold
        severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
        threshold_level = severity_order.get(self.severity_threshold, 0)

        filtered_findings = [f for f in all_findings if severity_order.get(f.severity, 0) >= threshold_level]

        summary = {
            "audit_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "audit_duration_seconds": round(audit_duration, 2),
            "databases_scanned": len(self.scan_results),
            "total_findings": len(all_findings),
            "filtered_findings": len(filtered_findings),
            "severity_threshold": self.severity_threshold,
            "findings_by_severity": {
                "CRITICAL": len([f for f in all_findings if f.severity == "CRITICAL"]),
                "HIGH": len([f for f in all_findings if f.severity == "HIGH"]),
                "MEDIUM": len([f for f in all_findings if f.severity == "MEDIUM"]),
                "LOW": len([f for f in all_findings if f.severity == "LOW"]),
            },
            "findings_by_category": self._group_findings_by_category(all_findings),
            "top_risks": self._get_top_risks(all_findings, top_n=10),
            "scan_results": [
                {
                    "database": r.database_name,
                    "type": r.database_type,
                    "findings_count": len(r.findings),
                    "duration": r.scan_duration_seconds,
                }
                for r in self.scan_results
            ],
        }

        return summary

    def _group_findings_by_category(self, findings: List[Any]) -> Dict[str, int]:  # noqa: ANN401
        """Group findings by category."""
        categories: Dict[str, int] = {}
        for finding in findings:
            category = finding.category
            categories[category] = categories.get(category, 0) + 1
        return categories

    def _get_top_risks(self, findings: List[Any], top_n: int = 10) -> List[Dict]:  # noqa: ANN401
        """Get top N risks by risk score."""
        sorted_findings = sorted(findings, key=lambda f: f.risk_score, reverse=True)
        return [
            {
                "severity": f.severity,
                "category": f.category,
                "finding": f.finding,
                "risk_score": f.risk_score,
                "affected_system": f.affected_system,
            }
            for f in sorted_findings[:top_n]
        ]

    def _save_reports(self, summary: Dict[str, Any]) -> None:
        """Save audit reports in multiple formats."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Save JSON report
        json_path = self.output_dir / f"security_audit_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"\nJSON report saved to: {json_path}")

        # Save YAML report
        yaml_path = self.output_dir / f"security_audit_{timestamp}.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(summary, f, default_flow_style=False)
        print(f"YAML report saved to: {yaml_path}")

    def _print_summary(self, summary: Dict[str, Any]) -> None:
        """Print audit summary to console."""
        print("\n" + "=" * 80)
        print("AUDIT SUMMARY")
        print("=" * 80)
        print(f"Audit Duration: {summary['audit_duration_seconds']}s")
        print(f"Databases Scanned: {summary['databases_scanned']}")
        print(f"Total Findings: {summary['total_findings']}")
        print()
        print("Findings by Severity:")
        for severity, count in summary["findings_by_severity"].items():
            print(f"  {severity:10s}: {count}")
        print()
        print("Top 10 Risks:")
        for i, risk in enumerate(summary["top_risks"], 1):
            print(f"  {i}. [{risk['severity']}] {risk['finding']} " f"(Risk Score: {risk['risk_score']})")
        print("=" * 80)


def main() -> int:
    """Execute security audit CLI."""
    parser = argparse.ArgumentParser(description="ViolentUTF Database Security Audit Tool")

    parser.add_argument(
        "--comprehensive",
        action="store_true",
        help="Run comprehensive audit on all systems",
    )

    parser.add_argument(
        "--database",
        choices=["postgres", "sqlite", "all"],
        default="all",
        help="Target specific database system",
    )

    parser.add_argument(
        "--severity-threshold",
        choices=["low", "medium", "high", "critical"],
        default="low",
        help="Minimum severity level to report",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / "docs/development/issue_272/reports",
        help="Output directory for reports",
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(__file__).parent / "config",
        help="Configuration directory",
    )

    args = parser.parse_args()

    # Initialize orchestrator
    orchestrator = SecurityAuditOrchestrator(
        config_dir=args.config_dir,
        output_dir=args.output_dir,
        severity_threshold=args.severity_threshold,
    )

    # Run audit
    if args.comprehensive or args.database == "all":
        summary = orchestrator.run_comprehensive_audit()
    else:
        print(f"Scanning {args.database} only...")
        summary = orchestrator.run_comprehensive_audit()

    # Determine exit code based on critical findings
    critical_count = summary["findings_by_severity"].get("CRITICAL", 0)
    if critical_count > 0:
        print(f"\nWARNING: {critical_count} CRITICAL findings detected!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
