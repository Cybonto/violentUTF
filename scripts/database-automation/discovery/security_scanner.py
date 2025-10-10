# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Security-focused database discovery integration.

Uses detect-secrets and bandit for credential and vulnerability scanning.
"""

import json
import logging
import subprocess  # nosec B404 # Needed for security tool execution (detect-secrets, bandit)
from pathlib import Path
from typing import Dict, List

from .models import CodeReference, DatabaseDiscovery, DiscoveryConfig, SecurityFinding
from .utils import measure_execution_time


class SecurityScanner:
    """Security scanning integration for database discovery."""

    def __init__(self, config: DiscoveryConfig) -> None:
        """Initialize the security scanner with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Security patterns for database credentials
        self.credential_patterns = {
            "postgresql_url": r"postgresql://[^:]+:[^@]+@[^/]+/\w+",
            "postgres_url": r"postgres://[^:]+:[^@]+@[^/]+/\w+",
            "mysql_url": r"mysql://[^:]+:[^@]+@[^/]+/\w+",
            "database_password": r'(db_password|database_password|postgres_password)\s*=\s*["\'][^"\']+["\']',
            "connection_string": r'(connection_string|conn_str|database_url)\s*=\s*["\'][^"\']+["\']',
        }

        # High-risk security patterns
        self.vulnerability_patterns = {
            "sql_injection": [
                r"execute\([^)]*%[^)]*\)",  # String formatting in SQL
                r"cursor\.execute\([^)]*\+[^)]*\)",  # String concatenation
                r"query.*\+.*request\.",  # Query concatenation with request data
            ],
            "hardcoded_credentials": [
                r'password\s*=\s*["\'][^"\']{8,}["\']',  # Hardcoded passwords
                r'secret_key\s*=\s*["\'][^"\']{16,}["\']',  # Hardcoded secret keys
            ],
            "insecure_connection": [
                r"ssl\s*=\s*False",  # Disabled SSL
                r"sslmode\s*=\s*disable",  # Disabled SSL mode
                r"verify_ssl\s*=\s*False",  # Disabled SSL verification
            ],
        }

    @measure_execution_time
    def scan_for_database_secrets(self, discoveries: List[DatabaseDiscovery]) -> List[DatabaseDiscovery]:
        """
        Scan discovered databases for security issues and credential exposure.

        Args:
            discoveries: List of database discoveries to scan

        Returns:
            Updated discoveries with security findings
        """
        if not self.config.enable_security_scanning:
            self.logger.info("Security scanning disabled in configuration")
            return discoveries

        try:
            # Scan with detect-secrets
            self.logger.info("Scanning for database credentials with detect-secrets")
            secrets_findings = self._run_detect_secrets()

            # Scan with bandit for security vulnerabilities
            self.logger.info("Scanning for security vulnerabilities with bandit")
            bandit_findings = self._run_bandit_scan()

            # Apply findings to discoveries
            updated_discoveries = self._apply_security_findings(discoveries, secrets_findings, bandit_findings)

            # Log security summary
            total_findings = sum(len(d.security_findings) for d in updated_discoveries)
            credential_findings = sum(
                1
                for d in updated_discoveries
                for finding in d.security_findings
                if finding.finding_type == "credential"
            )

            self.logger.info(
                "Security scan completed: %d findings, %d credential exposures", total_findings, credential_findings
            )

            return updated_discoveries

        except Exception as e:
            self.logger.error("Security scanning failed: %s", e)
            # Return original discoveries rather than failing completely
            return discoveries

    def _run_detect_secrets(self) -> List[Dict]:
        """Run detect-secrets scan and return findings."""
        try:
            # Prepare scan paths
            scan_paths = []
            for path in self.config.scan_paths:
                path_obj = Path(path)
                if path_obj.exists():
                    scan_paths.append(str(path_obj))

            if not scan_paths:
                self.logger.warning("No valid paths to scan with detect-secrets")
                return []

            # Build detect-secrets command
            cmd = ["detect-secrets", "scan"]

            # Add baseline if configured
            if self.config.secrets_baseline_file:
                baseline_path = Path(self.config.secrets_baseline_file)
                if baseline_path.exists():
                    cmd.extend(["--baseline", str(baseline_path)])

            # Add paths to scan
            cmd.extend(scan_paths)

            # Add exclusions
            for exclude_path in self.config.exclude_security_paths:
                cmd.extend(["--exclude-files", exclude_path])

            # Run detect-secrets
            self.logger.debug("Running detect-secrets: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)  # nosec B603

            if result.returncode != 0:
                self.logger.warning("detect-secrets failed with return code %d", result.returncode)
                self.logger.debug("detect-secrets stderr: %s", result.stderr)
                return []

            # Parse results
            try:
                scan_results = json.loads(result.stdout)
                findings = []

                for file_path, secrets in scan_results.get("results", {}).items():
                    for secret in secrets:
                        finding = {
                            "tool": "detect-secrets",
                            "type": "credential",
                            "file_path": file_path,
                            "line_number": secret.get("line_number"),
                            "secret_type": secret.get("type", "unknown"),
                            "severity": self._map_secret_severity(secret.get("type", "")),
                            "description": f"Potential {secret.get('type', 'secret')} found",
                            "is_verified": secret.get("is_secret", False),
                        }
                        findings.append(finding)

                self.logger.info("detect-secrets found %d potential secrets", len(findings))
                return findings

            except json.JSONDecodeError as e:
                self.logger.error("Failed to parse detect-secrets output: %s", e)
                return []

        except subprocess.TimeoutExpired:
            self.logger.error("detect-secrets scan timed out")
            return []
        except subprocess.CalledProcessError as e:
            self.logger.error("detect-secrets scan failed: %s", e)
            return []
        except Exception as e:
            self.logger.error("Error running detect-secrets: %s", e)
            return []

    def _run_bandit_scan(self) -> List[Dict]:
        """Run bandit security scan and return findings."""
        try:
            # Prepare scan paths (only Python files for bandit)
            python_paths = []
            for path in self.config.scan_paths:
                path_obj = Path(path)
                if path_obj.exists():
                    # Find Python files
                    if path_obj.is_file() and path_obj.suffix == ".py":
                        python_paths.append(str(path_obj))
                    elif path_obj.is_dir():
                        python_paths.append(str(path_obj))

            if not python_paths:
                self.logger.warning("No valid Python paths to scan with bandit")
                return []

            # Build bandit command
            cmd = ["bandit", "-r", "-f", "json"]

            # Add configuration if available
            if self.config.bandit_config_file:
                config_path = Path(self.config.bandit_config_file)
                if config_path.exists():
                    cmd.extend(["-c", str(config_path)])

            # Add exclusions
            exclude_patterns = []
            for exclude_path in self.config.exclude_security_paths:
                exclude_patterns.append(exclude_path.rstrip("/") + "/*")

            if exclude_patterns:
                cmd.extend(["--exclude", ",".join(exclude_patterns)])

            # Add paths
            cmd.extend(python_paths)

            # Run bandit
            self.logger.debug("Running bandit: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)  # nosec B603

            # Bandit returns non-zero on findings, which is expected
            if result.returncode > 2:  # Only error on severe failures
                self.logger.warning("bandit failed with return code %d", result.returncode)
                self.logger.debug("bandit stderr: %s", result.stderr)
                return []

            # Parse results
            try:
                scan_results = json.loads(result.stdout)
                findings = []

                for result_item in scan_results.get("results", []):
                    finding = {
                        "tool": "bandit",
                        "type": "vulnerability",
                        "file_path": result_item.get("filename"),
                        "line_number": result_item.get("line_number"),
                        "test_id": result_item.get("test_id"),
                        "test_name": result_item.get("test_name"),
                        "severity": result_item.get("issue_severity", "medium").lower(),
                        "confidence": result_item.get("issue_confidence", "medium").lower(),
                        "description": result_item.get("issue_text", "Security issue found"),
                        "code": result_item.get("code", ""),
                    }
                    findings.append(finding)

                self.logger.info("bandit found %d potential vulnerabilities", len(findings))
                return findings

            except json.JSONDecodeError as e:
                self.logger.error("Failed to parse bandit output: %s", e)
                return []

        except subprocess.TimeoutExpired:
            self.logger.error("bandit scan timed out")
            return []
        except subprocess.CalledProcessError as e:
            self.logger.error("bandit scan failed: %s", e)
            return []
        except Exception as e:
            self.logger.error("Error running bandit: %s", e)
            return []

    def _map_secret_severity(self, secret_type: str) -> str:
        """Map detect-secrets secret type to severity level."""
        high_risk_types = ["AWS Access Key", "Azure Storage Account access key", "Private Key", "Slack Token"]

        medium_risk_types = ["Base64 High Entropy String", "Hex High Entropy String"]

        if secret_type in high_risk_types:
            return "high"
        elif secret_type in medium_risk_types:
            return "medium"
        else:
            return "low"

    def _apply_security_findings(
        self, discoveries: List[DatabaseDiscovery], secrets_findings: List[Dict], bandit_findings: List[Dict]
    ) -> List[DatabaseDiscovery]:
        """Apply security findings to database discoveries."""

        # Create mapping of file paths to discoveries
        file_to_discoveries = {}
        for discovery in discoveries:
            # Add file paths from code references
            for code_ref in discovery.code_references:
                file_path = Path(code_ref.file_path).resolve()
                if file_path not in file_to_discoveries:
                    file_to_discoveries[file_path] = []
                file_to_discoveries[file_path].append(discovery)

            # Add database file paths
            for db_file in discovery.database_files:
                file_path = Path(db_file.file_path).resolve()
                if file_path not in file_to_discoveries:
                    file_to_discoveries[file_path] = []
                file_to_discoveries[file_path].append(discovery)

        # Process secrets findings
        for finding in secrets_findings:
            file_path = Path(finding["file_path"]).resolve()

            # Skip if not related to our discoveries
            if file_path not in file_to_discoveries:
                continue

            # Create SecurityFinding
            security_finding = SecurityFinding(
                file_path=str(file_path),
                line_number=finding.get("line_number"),
                finding_type="credential",
                severity=finding["severity"],
                description=finding["description"],
                recommendation=self._get_credential_recommendation(finding["secret_type"]),
                is_false_positive=not finding.get("is_verified", True),
            )

            # Add to related discoveries
            for discovery in file_to_discoveries[file_path]:
                discovery.security_findings.append(security_finding)

        # Process bandit findings
        for finding in bandit_findings:
            file_path = Path(finding["file_path"]).resolve()

            # Skip if not related to our discoveries
            if file_path not in file_to_discoveries:
                continue

            # Only include database-related vulnerabilities
            if not self._is_database_related_vulnerability(finding):
                continue

            # Create SecurityFinding
            security_finding = SecurityFinding(
                file_path=str(file_path),
                line_number=finding.get("line_number"),
                finding_type="vulnerability",
                severity=finding["severity"],
                description=finding["description"],
                recommendation=self._get_vulnerability_recommendation(finding["test_id"]),
            )

            # Add to related discoveries
            for discovery in file_to_discoveries[file_path]:
                discovery.security_findings.append(security_finding)

        return discoveries

    def _is_database_related_vulnerability(self, finding: Dict) -> bool:
        """Check if a bandit finding is database-related."""
        db_related_tests = [
            "B608",  # Possible SQL injection
            "B104",  # Hardcoded bind to all interfaces
            "B506",  # Test for use of yaml load
            "B201",  # Flask app run with debug=True
        ]

        test_id = finding.get("test_id", "")
        description = finding.get("description", "").lower()
        code = finding.get("code", "").lower()

        # Check test ID
        if test_id in db_related_tests:
            return True

        # Check description and code for database keywords
        db_keywords = ["sql", "database", "connection", "query", "execute", "cursor"]

        text_to_check = f"{description} {code}"
        return any(keyword in text_to_check for keyword in db_keywords)

    def _get_credential_recommendation(self, secret_type: str) -> str:
        """Get recommendation for credential findings."""
        recommendations = {
            "AWS Access Key": "Move AWS credentials to environment variables or AWS credential files",
            "Private Key": "Store private keys securely outside of source code",
            "Base64 High Entropy String": "Review if this is a hardcoded secret and move to secure storage",
            "Hex High Entropy String": "Review if this is a hardcoded secret and move to secure storage",
        }

        return recommendations.get(secret_type, "Move sensitive data to environment variables or secure configuration")

    def _get_vulnerability_recommendation(self, test_id: str) -> str:
        """Get recommendation for vulnerability findings."""
        recommendations = {
            "B608": "Use parameterized queries to prevent SQL injection",
            "B104": "Avoid binding to all interfaces (0.0.0.0) in production",
            "B506": "Use yaml.safe_load() instead of yaml.load()",
            "B201": "Disable debug mode in production",
        }

        return recommendations.get(test_id, "Review and remediate security vulnerability")

    def validate_discovered_credentials(self, discoveries: List[DatabaseDiscovery]) -> List[DatabaseDiscovery]:
        """
        Validate discovered database credentials for exposure risk.

        Args:
            discoveries: List of database discoveries

        Returns:
            Updated discoveries with credential validation
        """
        try:
            for discovery in discoveries:
                # Check connection strings for credential exposure
                if discovery.connection_string:
                    self._validate_connection_string(discovery)

                # Check code references for credential patterns
                for code_ref in discovery.code_references:
                    if code_ref.is_credential:
                        self._validate_code_credential(discovery, code_ref)

                # Check for environment variable usage
                self._check_environment_variable_usage(discovery)

            return discoveries

        except Exception as e:
            self.logger.error("Credential validation failed: %s", e)
            return discoveries

    def _validate_connection_string(self, discovery: DatabaseDiscovery) -> None:
        """Validate a connection string for security issues."""
        conn_str = discovery.connection_string

        # Check for embedded credentials
        if "@" in conn_str and ":" in conn_str:
            # Extract potential password part
            try:
                # Simple pattern: protocol://user:password@host/db
                if "://" in conn_str:
                    after_protocol = conn_str.split("://", 1)[1]
                    if "@" in after_protocol:
                        user_pass = after_protocol.split("@", 1)[0]
                        if ":" in user_pass:
                            password_part = user_pass.split(":", 1)[1]

                            # Check if password looks hardcoded (not a variable)
                            if not (password_part.startswith("${") or password_part.startswith("$(")):
                                finding = SecurityFinding(
                                    file_path=(
                                        discovery.database_files[0].file_path if discovery.database_files else "unknown"
                                    ),
                                    line_number=None,
                                    finding_type="credential",
                                    severity="high",
                                    description="Hardcoded password in connection string",
                                    recommendation="Use environment variables for database passwords",
                                )
                                discovery.security_findings.append(finding)

            except Exception as e:
                self.logger.debug("Error validating connection string: %s", e)

    def _validate_code_credential(self, discovery: DatabaseDiscovery, code_ref: CodeReference) -> None:
        """Validate a code reference that contains credentials."""
        finding = SecurityFinding(
            file_path=code_ref.file_path,
            line_number=code_ref.line_number,
            finding_type="credential",
            severity="medium",
            description="Database credentials found in source code",
            recommendation="Move database credentials to environment variables or secure configuration",
        )
        discovery.security_findings.append(finding)

    def _check_environment_variable_usage(self, discovery: DatabaseDiscovery) -> None:
        """Check if discovery uses proper environment variable patterns."""
        # This is a positive check - if we see good patterns, note them
        good_patterns = ["os.getenv", "os.environ", "getenv", "env.get"]

        env_usage_found = False
        for code_ref in discovery.code_references:
            code_snippet = code_ref.code_snippet.lower()
            if any(pattern in code_snippet for pattern in good_patterns):
                env_usage_found = True
                break

        if env_usage_found:
            # Add positive security note
            discovery.custom_properties["uses_environment_variables"] = True
        else:
            # Add recommendation if no env usage found
            if discovery.connection_string or any(ref.is_credential for ref in discovery.code_references):
                finding = SecurityFinding(
                    file_path="general",
                    line_number=None,
                    finding_type="insecure_pattern",
                    severity="low",
                    description="No environment variable usage detected for database configuration",
                    recommendation="Consider using environment variables for database configuration",
                )
                discovery.security_findings.append(finding)
