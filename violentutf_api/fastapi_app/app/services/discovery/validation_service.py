# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Validation service for discovered databases."""

import logging
import socket
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ...schemas.discovery import DiscoveredDatabase, DiscoveryConfig


class ValidationService:
    """Service for validating discovered databases."""

    def __init__(self) -> None:
        """Initialize the validation service."""
        self.logger = logging.getLogger(__name__)

    async def validate_discovery(
        self, discovery: DiscoveredDatabase, config: Optional[DiscoveryConfig] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a discovered database.

        Args:
            discovery: Database discovery to validate
            config: Discovery configuration

        Returns:
            Tuple of (is_valid, validation_errors)
        """
        validation_errors = []

        try:
            # Basic validation
            if not discovery.database_type or discovery.database_type == "unknown":
                validation_errors.append("Unknown database type")

            if not discovery.name:
                validation_errors.append("Missing database name")

            # Connection validation
            if not any([discovery.host, discovery.file_path, discovery.connection_string]):
                validation_errors.append("No connection information available")

            # File-based database validation
            if discovery.file_path:
                file_errors = await self._validate_file_database(discovery)
                validation_errors.extend(file_errors)

            # Network-based database validation
            if discovery.host and discovery.port:
                network_errors = await self._validate_network_database(discovery, config)
                validation_errors.extend(network_errors)

            # Connection string validation
            if discovery.connection_string:
                conn_errors = await self._validate_connection_string(discovery)
                validation_errors.extend(conn_errors)

            # Security validation
            security_errors = await self._validate_security_aspects(discovery)
            validation_errors.extend(security_errors)

            is_valid = len(validation_errors) == 0

            self.logger.debug(
                "Validation completed for %s: %s (%s errors)",
                discovery.database_id,
                "valid" if is_valid else "invalid",
                len(validation_errors),
            )

            return is_valid, validation_errors

        except Exception as e:
            self.logger.error("Validation failed for %s: %s", discovery.database_id, e)
            return False, [f"Validation error: {e}"]

    async def _validate_file_database(self, discovery: DiscoveredDatabase) -> List[str]:
        """Validate file-based database."""
        errors = []

        try:
            file_path = Path(discovery.file_path)

            # Check if file exists
            if not file_path.exists():
                errors.append(f"Database file not found: {discovery.file_path}")
                return errors

            # Check if file is readable
            if not file_path.is_file():
                errors.append(f"Path is not a file: {discovery.file_path}")
                return errors

            # Check file permissions
            try:
                with open(file_path, "rb") as f:
                    f.read(1)  # Try to read one byte
            except PermissionError:
                errors.append(f"No read permission for file: {discovery.file_path}")
            except Exception as e:
                errors.append(f"Cannot read file {discovery.file_path}: {e}")

            # Check file size
            try:
                file_size = file_path.stat().st_size
                if file_size == 0:
                    errors.append(f"Database file is empty: {discovery.file_path}")
                elif file_size > 10 * 1024 * 1024 * 1024:  # 10GB
                    errors.append(f"Database file is very large: {discovery.file_path}")
            except OSError as e:
                errors.append(f"Cannot access file stats: {e}")

            # Database-specific validation
            if discovery.database_type == "sqlite":
                sqlite_errors = await self._validate_sqlite_file(file_path)
                errors.extend(sqlite_errors)
            elif discovery.database_type == "duckdb":
                duckdb_errors = await self._validate_duckdb_file(file_path)
                errors.extend(duckdb_errors)

        except Exception as e:
            errors.append(f"File validation error: {e}")

        return errors

    async def _validate_sqlite_file(self, file_path: Path) -> List[str]:
        """Validate SQLite database file."""
        errors = []

        try:
            import sqlite3

            # Try to connect to the database
            conn = sqlite3.connect(str(file_path))
            cursor = conn.cursor()

            # Check if it's a valid SQLite database
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()

                if not tables:
                    errors.append("SQLite database contains no tables")

            except sqlite3.DatabaseError as e:
                errors.append(f"SQLite database is corrupted: {e}")

            finally:
                conn.close()

        except sqlite3.Error as e:
            errors.append(f"SQLite validation failed: {e}")
        except Exception as e:
            errors.append(f"SQLite validation error: {e}")

        return errors

    async def _validate_duckdb_file(self, file_path: Path) -> List[str]:
        """Validate DuckDB database file."""
        errors = []

        try:
            # Check file header for DuckDB magic bytes
            with open(file_path, "rb") as f:
                header = f.read(16)
                if not header.startswith(b"DUCK") and b"duckdb" not in header.lower():
                    errors.append("File does not appear to be a valid DuckDB database")

            # Try to connect if DuckDB is available
            try:
                import duckdb

                conn = duckdb.connect(str(file_path), read_only=True)

                # Test basic query
                try:
                    result = conn.execute("SELECT 1").fetchone()
                    if result[0] != 1:
                        errors.append("DuckDB database connection test failed")
                except Exception as e:
                    errors.append(f"DuckDB query test failed: {e}")

                finally:
                    conn.close()

            except ImportError:
                # DuckDB not available for testing
                self.logger.debug("DuckDB not available for file validation")
            except Exception as e:
                errors.append(f"DuckDB validation failed: {e}")

        except Exception as e:
            errors.append(f"DuckDB file validation error: {e}")

        return errors

    async def _validate_network_database(
        self, discovery: DiscoveredDatabase, config: Optional[DiscoveryConfig]
    ) -> List[str]:
        """Validate network-accessible database."""
        errors = []

        try:
            # Test basic connectivity
            timeout = config.network_timeout_seconds if config else 5

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            try:
                result = sock.connect_ex((discovery.host, discovery.port))
                if result != 0:
                    errors.append(f"Cannot connect to {discovery.host}:{discovery.port}")
                else:
                    self.logger.debug("Successfully connected to %s:%s", discovery.host, discovery.port)

            finally:
                sock.close()

            # Database-specific validation
            if discovery.database_type == "postgresql":
                pg_errors = await self._validate_postgresql_connection(discovery)
                errors.extend(pg_errors)

        except socket.timeout:
            errors.append(f"Connection timeout to {discovery.host}:{discovery.port}")
        except socket.gaierror as e:
            errors.append(f"DNS resolution failed for {discovery.host}: {e}")
        except Exception as e:
            errors.append(f"Network validation error: {e}")

        return errors

    async def _validate_postgresql_connection(self, discovery: DiscoveredDatabase) -> List[str]:
        """Validate PostgreSQL connection."""
        errors = []

        try:
            # Try to import psycopg2 for more detailed validation
            try:
                import psycopg2

                # Build connection string
                conn_str = (
                    f"host={discovery.host} port={discovery.port} dbname=postgres user=postgres connect_timeout=5"
                )

                try:
                    conn = psycopg2.connect(conn_str)
                    cursor = conn.cursor()

                    # Test basic query
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]

                    self.logger.debug("PostgreSQL version: %s", version)

                    cursor.close()
                    conn.close()

                except psycopg2.OperationalError as e:
                    # Connection failed, but this might be expected (auth, etc.)
                    if "authentication failed" in str(e).lower():
                        # Authentication error means server is responding
                        self.logger.debug(
                            "PostgreSQL server responding (auth required): %s:%s", discovery.host, discovery.port
                        )
                    else:
                        errors.append(f"PostgreSQL connection failed: {e}")

            except ImportError:
                # psycopg2 not available, skip detailed validation
                self.logger.debug("psycopg2 not available for PostgreSQL validation")

        except Exception as e:
            errors.append(f"PostgreSQL validation error: {e}")

        return errors

    async def _validate_connection_string(self, discovery: DiscoveredDatabase) -> List[str]:
        """Validate database connection string."""
        errors = []

        try:
            conn_str = discovery.connection_string

            # Basic format validation
            if not conn_str or "://" not in conn_str:
                errors.append("Invalid connection string format")
                return errors

            # Extract protocol
            protocol = conn_str.split("://")[0].lower()

            # Protocol-specific validation
            if protocol in ["postgresql", "postgres"]:
                if "@" not in conn_str or "/" not in conn_str:
                    errors.append("PostgreSQL connection string missing required components")
            elif protocol.startswith("sqlite"):
                if not conn_str.startswith("sqlite:///"):
                    errors.append("SQLite connection string should start with sqlite:///")
                else:
                    # Extract file path
                    file_path = conn_str[10:]  # Remove 'sqlite:///'
                    if not Path(file_path).exists():
                        errors.append(f"SQLite file in connection string not found: {file_path}")

            # Check for credentials in connection string
            if "@" in conn_str and ":" in conn_str.split("@")[0]:
                # Connection string contains credentials
                if discovery.security_findings:
                    # Check if this is already flagged as a security issue
                    has_credential_finding = any(
                        finding.finding_type == "credential" for finding in discovery.security_findings
                    )
                    if not has_credential_finding:
                        errors.append("Connection string contains credentials but no security finding recorded")

        except Exception as e:
            errors.append(f"Connection string validation error: {e}")

        return errors

    async def _validate_security_aspects(self, discovery: DiscoveredDatabase) -> List[str]:
        """Validate security aspects of the discovery."""
        errors = []

        try:
            # Check for high-severity security findings
            high_severity_findings = [finding for finding in discovery.security_findings if finding.severity == "high"]

            if high_severity_findings:
                errors.append(f"High-severity security findings present: {len(high_severity_findings)}")

            # Check for credential exposure
            credential_findings = [
                finding for finding in discovery.security_findings if finding.finding_type == "credential"
            ]

            if credential_findings:
                errors.append(f"Credential exposure detected: {len(credential_findings)} findings")

            # Check for accessible database files with broad permissions
            if discovery.file_path:
                try:
                    file_path = Path(discovery.file_path)
                    if file_path.exists():
                        # Check file permissions (Unix-like systems)
                        import stat

                        file_stat = file_path.stat()

                        # Check if file is world-readable
                        if file_stat.st_mode & stat.S_IROTH:
                            errors.append("Database file is world-readable")

                        # Check if file is in a public directory
                        public_dirs = ["/tmp", "/var/tmp", "/usr/tmp"]
                        if any(str(file_path).startswith(pub_dir) for pub_dir in public_dirs):
                            errors.append("Database file is in a public directory")

                except Exception as e:
                    self.logger.debug("Security permission check failed: %s", e)

        except Exception as e:
            errors.append(f"Security validation error: {e}")

        return errors

    async def validate_discovery_consistency(self, discoveries: List[DiscoveredDatabase]) -> Dict[str, List[str]]:
        """
        Validate consistency across multiple discoveries.

        Args:
            discoveries: List of discoveries to validate

        Returns:
            Dict mapping database_id to consistency errors
        """
        consistency_errors = {}

        try:
            # Group discoveries by connection details
            connection_groups = {}

            for discovery in discoveries:
                # Create connection key
                key_parts = []

                if discovery.host and discovery.port:
                    key_parts.append(f"{discovery.host}:{discovery.port}")

                if discovery.file_path:
                    key_parts.append(f"file:{discovery.file_path}")

                if discovery.connection_string:
                    key_parts.append(f"conn:{discovery.connection_string}")

                if not key_parts:
                    continue

                connection_key = "|".join(key_parts)

                if connection_key not in connection_groups:
                    connection_groups[connection_key] = []
                connection_groups[connection_key].append(discovery)

            # Check for inconsistencies within groups
            for connection_key, group_discoveries in connection_groups.items():
                if len(group_discoveries) <= 1:
                    continue

                # Check database type consistency
                db_types = set(d.database_type for d in group_discoveries)
                if len(db_types) > 1:
                    for discovery in group_discoveries:
                        if discovery.database_id not in consistency_errors:
                            consistency_errors[discovery.database_id] = []
                        consistency_errors[discovery.database_id].append(
                            f"Inconsistent database types for same connection: {db_types}"
                        )

                # Check confidence score variations
                confidence_scores = [d.confidence_score for d in group_discoveries]
                max_score = max(confidence_scores)
                min_score = min(confidence_scores)

                if max_score - min_score > 0.5:  # Large variation
                    for discovery in group_discoveries:
                        if discovery.database_id not in consistency_errors:
                            consistency_errors[discovery.database_id] = []
                        consistency_errors[discovery.database_id].append(
                            f"Large confidence score variation: {min_score:.2f} - {max_score:.2f}"
                        )

            # Check for potential duplicates
            await self._check_for_duplicates(discoveries, consistency_errors)

        except Exception as e:
            self.logger.error("Consistency validation failed: %s", e)
            consistency_errors["global"] = [f"Consistency validation error: {e}"]

        return consistency_errors

    async def _check_for_duplicates(
        self, discoveries: List[DiscoveredDatabase], consistency_errors: Dict[str, List[str]]
    ) -> None:
        """Check for potential duplicate discoveries."""

        seen_databases = {}

        for discovery in discoveries:
            # Create a signature for the database
            signature_parts = []

            if discovery.host and discovery.port:
                signature_parts.append(f"net:{discovery.host}:{discovery.port}")

            if discovery.file_path:
                signature_parts.append(f"file:{Path(discovery.file_path).resolve()}")

            if discovery.connection_string:
                signature_parts.append(f"conn:{discovery.connection_string}")

            signature = "|".join(sorted(signature_parts))

            if signature in seen_databases:
                # Potential duplicate found
                other_discovery = seen_databases[signature]

                for db_id in [discovery.database_id, other_discovery.database_id]:
                    if db_id not in consistency_errors:
                        consistency_errors[db_id] = []
                    consistency_errors[db_id].append(
                        f"Potential duplicate database detected (matches "
                        f"{other_discovery.database_id if db_id == discovery.database_id else discovery.database_id})"
                    )
            else:
                seen_databases[signature] = discovery
