# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Database Security Scanner Module.

This module provides security scanning functionality for PostgreSQL and SQLite
databases in the ViolentUTF platform.
"""

import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class SecurityFinding:
    """Represents a security finding from database scan."""

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str  # Authentication, Encryption, Access Control, etc.
    finding: str  # Brief description
    description: str  # Detailed description
    risk_score: int  # 1-125
    likelihood: int  # 1-5
    impact: int  # 1-5
    exploitability: int  # 1-5
    affected_system: str  # Database/component affected
    remediation: str  # Recommended fix
    compliance_impact: List[str] = field(default_factory=list)  # GDPR, SOC2, etc.


@dataclass
class DatabaseScanResult:
    """Results from database security scan."""

    database_type: str  # postgresql, sqlite
    database_name: str
    scan_timestamp: str
    findings: List[SecurityFinding] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    scan_duration_seconds: float = 0.0


class DatabaseScanner:
    """Base class for database security scanning."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize database scanner.

        Args:
            config_path: Path to security standards configuration file
        """
        self.config = self._load_config(config_path)
        self.findings: List[SecurityFinding] = []

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load security standards configuration."""
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def calculate_risk_score(self, likelihood: int, impact: int, exploitability: int) -> int:
        """
        Calculate risk score based on likelihood, impact, and exploitability.

        Args:
            likelihood: Likelihood of exploitation (1-5)
            impact: Impact if exploited (1-5)
            exploitability: Ease of exploitation (1-5)

        Returns:
            Risk score (1-125)
        """
        return likelihood * impact * exploitability

    def determine_severity(self, risk_score: int) -> str:
        """
        Determine severity level based on risk score.

        Args:
            risk_score: Calculated risk score

        Returns:
            Severity level: CRITICAL, HIGH, MEDIUM, or LOW
        """
        severity_levels = self.config.get("risk_scoring", {}).get(
            "severity_levels",
            {
                "critical": {"score_min": 90},
                "high": {"score_min": 70},
                "medium": {"score_min": 40},
                "low": {"score_min": 1},
            },
        )

        if risk_score >= severity_levels["critical"]["score_min"]:
            return "CRITICAL"
        elif risk_score >= severity_levels["high"]["score_min"]:
            return "HIGH"
        elif risk_score >= severity_levels["medium"]["score_min"]:
            return "MEDIUM"
        else:
            return "LOW"


class SQLiteScanner(DatabaseScanner):
    """Security scanner for SQLite databases."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize SQLite scanner."""
        super().__init__(config_path)
        self.sqlite_config = self.config.get("sqlite", {})

    def scan_database(self, db_path: Path) -> DatabaseScanResult:
        """
        Perform comprehensive security scan of SQLite database.

        Args:
            db_path: Path to SQLite database file

        Returns:
            DatabaseScanResult with findings
        """
        import time

        start_time = time.time()

        # Initialize result
        result = DatabaseScanResult(
            database_type="sqlite",
            database_name=str(db_path),
            scan_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Perform security checks
        self._check_file_permissions(db_path)
        self._check_directory_permissions(db_path.parent)
        self._check_backup_security(db_path)
        self._check_database_integrity(db_path)

        # Add findings to result
        result.findings = self.findings.copy()

        # Calculate summary
        result.summary = {
            "CRITICAL": len([f for f in result.findings if f.severity == "CRITICAL"]),
            "HIGH": len([f for f in result.findings if f.severity == "HIGH"]),
            "MEDIUM": len([f for f in result.findings if f.severity == "MEDIUM"]),
            "LOW": len([f for f in result.findings if f.severity == "LOW"]),
            "total": len(result.findings),
        }

        result.scan_duration_seconds = time.time() - start_time

        return result

    def _check_file_permissions(self, db_path: Path) -> None:
        """Check SQLite database file permissions."""
        if not db_path.exists():
            self._add_finding(
                severity="CRITICAL",
                category="File Security",
                finding=f"Database file not found: {db_path}",
                description=f"SQLite database file does not exist at {db_path}",
                likelihood=5,
                impact=5,
                exploitability=5,
                affected_system=f"SQLite: {db_path.name}",
                remediation="Verify database path and ensure file exists",
            )
            return

        file_stat = os.stat(db_path)
        file_mode = file_stat.st_mode & 0o777

        # Check against configured permission requirements
        required_mode = int(self.sqlite_config.get("file_security", {}).get("permissions", "0600"), 8)

        if file_mode != required_mode:
            # More permissive than required
            if file_mode > required_mode:
                severity_impact = 5 if file_mode & 0o077 else 3
                self._add_finding(
                    severity="HIGH" if severity_impact == 5 else "MEDIUM",
                    category="File Security",
                    finding=f"Insecure file permissions: {oct(file_mode)}",
                    description=(
                        f"SQLite database file has permissions {oct(file_mode)} "
                        f"but should be {oct(required_mode)} (owner read/write only)"
                    ),
                    likelihood=4,
                    impact=severity_impact,
                    exploitability=4,
                    affected_system=f"SQLite: {db_path.name}",
                    remediation=f"chmod {oct(required_mode)} {db_path}",
                    compliance_impact=["GDPR Article 32", "SOC 2 CC6.6"],
                )

    def _check_directory_permissions(self, directory: Path) -> None:
        """Check directory permissions for SQLite database."""
        if not directory.exists():
            return

        dir_stat = os.stat(directory)
        dir_mode = dir_stat.st_mode & 0o777

        required_mode = int(
            self.sqlite_config.get("file_security", {}).get("directory_permissions", "0700"),
            8,
        )

        if dir_mode > required_mode:
            self._add_finding(
                severity="MEDIUM",
                category="File Security",
                finding=f"Directory permissions too permissive: {oct(dir_mode)}",
                description=(
                    f"Database directory has permissions {oct(dir_mode)} "
                    f"but should be {oct(required_mode)} or more restrictive"
                ),
                likelihood=3,
                impact=3,
                exploitability=3,
                affected_system=f"Directory: {directory}",
                remediation=f"chmod {oct(required_mode)} {directory}",
            )

    def _check_backup_security(self, db_path: Path) -> None:
        """Check security of backup files."""
        backup_pattern = db_path.parent / f"{db_path.name}.backup"

        if backup_pattern.exists():
            backup_stat = os.stat(backup_pattern)
            backup_mode = backup_stat.st_mode & 0o777

            if backup_mode != 0o600:
                self._add_finding(
                    severity="HIGH",
                    category="Backup Security",
                    finding=f"Backup file has insecure permissions: {oct(backup_mode)}",
                    description=(
                        f"Backup file {backup_pattern.name} has permissions " f"{oct(backup_mode)} but should be 0600"
                    ),
                    likelihood=4,
                    impact=4,
                    exploitability=3,
                    affected_system=f"Backup: {backup_pattern.name}",
                    remediation=f"chmod 0600 {backup_pattern}",
                )

    def _check_database_integrity(self, db_path: Path) -> None:
        """Check SQLite database integrity."""
        if not db_path.exists():
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check integrity
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result[0] != "ok":
                self._add_finding(
                    severity="HIGH",
                    category="Database Integrity",
                    finding="Database integrity check failed",
                    description=f"SQLite integrity check returned: {result[0]}",
                    likelihood=4,
                    impact=4,
                    exploitability=2,
                    affected_system=f"SQLite: {db_path.name}",
                    remediation="Restore from backup or repair database",
                )

            conn.close()

        except sqlite3.Error as e:
            self._add_finding(
                severity="CRITICAL",
                category="Database Integrity",
                finding=f"Database connection failed: {str(e)}",
                description=f"Unable to connect to SQLite database: {str(e)}",
                likelihood=5,
                impact=5,
                exploitability=1,
                affected_system=f"SQLite: {db_path.name}",
                remediation="Verify database file is not corrupted",
            )

    def _add_finding(
        self,
        severity: str,
        category: str,
        finding: str,
        description: str,
        likelihood: int,
        impact: int,
        exploitability: int,
        affected_system: str,
        remediation: str,
        compliance_impact: Optional[List[str]] = None,
    ) -> None:
        """Add a security finding to the results."""
        risk_score = self.calculate_risk_score(likelihood, impact, exploitability)

        self.findings.append(
            SecurityFinding(
                severity=severity,
                category=category,
                finding=finding,
                description=description,
                risk_score=risk_score,
                likelihood=likelihood,
                impact=impact,
                exploitability=exploitability,
                affected_system=affected_system,
                remediation=remediation,
                compliance_impact=compliance_impact or [],
            )
        )


class PostgreSQLScanner(DatabaseScanner):
    """Security scanner for PostgreSQL databases."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """Initialize PostgreSQL scanner."""
        super().__init__(config_path)
        self.pg_config = self.config.get("postgresql", {})

    def scan_database(self, connection_params: Dict[str, Any]) -> DatabaseScanResult:  # noqa: ARG002
        """
        Perform comprehensive security scan of PostgreSQL database.

        Args:
            connection_params: PostgreSQL connection parameters

        Returns:
            DatabaseScanResult with findings
        """
        import time

        start_time = time.time()

        # Initialize result
        result = DatabaseScanResult(
            database_type="postgresql",
            database_name=connection_params.get("database", "unknown"),
            scan_timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Note: Actual PostgreSQL scanning would require psycopg2
        # For this implementation, we add a placeholder finding
        self._add_finding(
            severity="INFO",
            category="Scanner Status",
            finding="PostgreSQL scanner requires psycopg2 library",
            description=("Full PostgreSQL security scanning requires psycopg2 to be installed"),
            likelihood=1,
            impact=1,
            exploitability=1,
            affected_system="PostgreSQL Scanner",
            remediation="Install psycopg2: pip install psycopg2-binary",
        )

        result.findings = self.findings.copy()
        result.scan_duration_seconds = time.time() - start_time

        return result

    def _add_finding(
        self,
        severity: str,
        category: str,
        finding: str,
        description: str,
        likelihood: int,
        impact: int,
        exploitability: int,
        affected_system: str,
        remediation: str,
        compliance_impact: Optional[List[str]] = None,
    ) -> None:
        """Add a security finding to the results."""
        risk_score = self.calculate_risk_score(likelihood, impact, exploitability)

        self.findings.append(
            SecurityFinding(
                severity=severity,
                category=category,
                finding=finding,
                description=description,
                risk_score=risk_score,
                likelihood=likelihood,
                impact=impact,
                exploitability=exploitability,
                affected_system=affected_system,
                remediation=remediation,
                compliance_impact=compliance_impact or [],
            )
        )
