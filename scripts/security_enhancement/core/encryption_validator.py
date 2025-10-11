# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Encryption Validator

Validates encryption status across PostgreSQL, SQLite, file storage,
and Docker volumes.

Issue #273: Phase 6.2 - Database Encryption and Security Enhancement
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

import psycopg2


class EncryptionValidator:
    """Validates encryption across all database systems"""

    def __init__(self) -> None:
        """Initialize encryption validator"""
        self.validation_results: Dict[str, Any] = {}

    def validate_postgresql_encryption(self, connection_string: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate PostgreSQL encryption status

        Args:
            connection_string: Optional PostgreSQL connection string

        Returns:
            Dictionary containing encryption validation results
        """
        result = {
            "database": "postgresql",
            "ssl_enabled": "unknown",
            "pgcrypto_available": "unknown",
            "connection_encryption": "unknown",
        }

        if connection_string is None:
            connection_string = os.getenv(
                "POSTGRES_CONNECTION",
                "postgresql://keycloak:keycloak@localhost:5432/keycloak",
            )

        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()

            # Check SSL status
            try:
                cursor.execute("SHOW ssl")
                ssl_status = cursor.fetchone()
                result["ssl_enabled"] = ssl_status[0] == "on" if ssl_status else False
            except Exception as e:
                result["ssl_enabled"] = f"error: {str(e)}"

            # Check pgcrypto extension
            try:
                cursor.execute("SELECT * FROM pg_available_extensions WHERE name='pgcrypto'")
                pgcrypto = cursor.fetchone()
                result["pgcrypto_available"] = pgcrypto is not None
            except Exception as e:
                result["pgcrypto_available"] = f"error: {str(e)}"

            # Check connection encryption
            try:
                cursor.execute("SELECT ssl_is_used()")
                ssl_used = cursor.fetchone()
                result["connection_encryption"] = ssl_used[0] if ssl_used else False
            except Exception:
                # Function may not exist in all PostgreSQL versions
                result["connection_encryption"] = result["ssl_enabled"]

            cursor.close()
            conn.close()
            result["status"] = "validated"

        except psycopg2.OperationalError as e:
            result["status"] = "error"
            result["error"] = f"Connection failed: {str(e)}"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def validate_sqlite_encryption(self, db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate SQLite encryption status

        Args:
            db_path: Optional path to SQLite database file

        Returns:
            Dictionary containing encryption validation results
        """
        result = {
            "database": "sqlite",
            "file_permissions": "unknown",
            "encryption_method": "unknown",
            "secure_delete": "unknown",
        }

        if db_path is None:
            db_path = "/Users/tamnguyen/Documents/GitHub/violentUTF/app_data/violentutf_api.db"

        if not os.path.exists(db_path):
            result["status"] = "error"
            result["error"] = f"Database file not found: {db_path}"
            result["accessible"] = False
            return result

        try:
            # Check file permissions
            try:
                st = os.stat(db_path)
                octal_perms = oct(st.st_mode)[-3:]
                result["file_permissions"] = octal_perms

                # Check if file has no permissions (000)
                if octal_perms == "000":
                    result["status"] = "error"
                    result["error"] = "File has no permissions (000)"
                    result["accessible"] = False
                    return result

                if octal_perms == "600":
                    result["file_permissions"] = "secure"
            except PermissionError:
                result["status"] = "error"
                result["error"] = "Permission denied accessing file"
                result["accessible"] = False
                return result

            # Try to detect SQLCipher
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Check for secure_delete pragma
                try:
                    cursor.execute("PRAGMA secure_delete")
                    secure_delete = cursor.fetchone()
                    result["secure_delete"] = "ON" if secure_delete and secure_delete[0] == 1 else "OFF"
                except Exception:
                    result["secure_delete"] = "unknown"

                # Try to detect encryption
                try:
                    cursor.execute("PRAGMA cipher_version")
                    cipher_version = cursor.fetchone()
                    if cipher_version:
                        result["encryption_method"] = "sqlcipher"
                    else:
                        result["encryption_method"] = "none"
                except Exception:
                    # No SQLCipher, check for file-level encryption
                    result["encryption_method"] = "none"

                cursor.close()
                conn.close()

            except sqlite3.DatabaseError:
                # Database might be encrypted with SQLCipher
                result["encryption_method"] = "possibly_encrypted"

            result["status"] = "validated"

        except PermissionError:
            result["status"] = "error"
            result["error"] = "Permission denied"
            result["accessible"] = False
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def validate_file_encryption(self) -> Dict[str, Any]:
        """
        Validate file storage encryption

        Returns:
            Dictionary containing file encryption validation results
        """
        result = {"file_storage": True, "env_files": [], "certificates": []}

        base_path = Path("/Users/tamnguyen/Documents/GitHub/violentUTF")

        # Check .env files
        env_files = list(base_path.rglob("*.env"))
        for env_file in env_files:
            if ".vitutf" in str(env_file) or "node_modules" in str(env_file):
                continue

            try:
                st = os.stat(env_file)
                perms = oct(st.st_mode)[-3:]
                result["env_files"].append(
                    {
                        "path": str(env_file),
                        "permissions": perms,
                        "secure": perms == "600",
                    }
                )
            except Exception as e:
                result["env_files"].append({"path": str(env_file), "error": str(e), "secure": False})

        # Check certificate files
        cert_dirs = [base_path / "certs", base_path / "violentutf_api" / "certs"]
        for cert_dir in cert_dirs:
            if cert_dir.exists():
                cert_files = list(cert_dir.rglob("*.pem")) + list(cert_dir.rglob("*.crt"))
                for cert_file in cert_files:
                    try:
                        st = os.stat(cert_file)
                        perms = oct(st.st_mode)[-3:]
                        result["certificates"].append(
                            {
                                "path": str(cert_file),
                                "permissions": perms,
                                "secure": perms == "600",
                            }
                        )
                    except Exception as e:
                        result["certificates"].append({"path": str(cert_file), "error": str(e), "secure": False})

        result["status"] = "validated"
        return result

    def validate_volume_encryption(self) -> Dict[str, Any]:
        """
        Validate Docker volume encryption

        Returns:
            Dictionary containing volume encryption validation results
        """
        result = {"volumes": {}, "status": "validated"}

        try:
            import docker

            client = docker.from_env()
            volumes = client.volumes.list()

            for volume in volumes:
                if "violentutf" in volume.name or "postgres" in volume.name:
                    result["volumes"][volume.name] = {
                        "name": volume.name,
                        "driver": volume.attrs.get("Driver", "unknown"),
                        "mountpoint": volume.attrs.get("Mountpoint", "unknown"),
                        "encryption": "unknown",  # Docker doesn't expose this easily
                    }

        except ImportError:
            result["status"] = "error"
            result["error"] = "Docker SDK not available"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def validate_key_management(self) -> Dict[str, Any]:
        """
        Validate encryption key management

        Returns:
            Dictionary containing key management validation results
        """
        result = {"key_storage": [], "rotation_readiness": "unknown"}

        # Check for common key storage locations
        base_path = Path("/Users/tamnguyen/Documents/GitHub/violentUTF")
        key_patterns = ["*.key", "*.pem", "*_key", "*secret*"]

        for pattern in key_patterns:
            key_files = list(base_path.rglob(pattern))
            for key_file in key_files:
                if ".vitutf" in str(key_file) or "node_modules" in str(key_file) or ".git" in str(key_file):
                    continue

                try:
                    st = os.stat(key_file)
                    perms = oct(st.st_mode)[-3:]
                    result["key_storage"].append(
                        {
                            "path": str(key_file),
                            "permissions": perms,
                            "secure": perms in ["600", "400"],
                        }
                    )
                except Exception:
                    pass

        result["status"] = "validated"
        return result

    def generate_encryption_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive encryption validation report

        Returns:
            Comprehensive encryption validation report
        """
        report = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "postgresql": self.validate_postgresql_encryption(),
            "sqlite": self.validate_sqlite_encryption(),
            "file_storage": self.validate_file_encryption(),
            "volume_encryption": self.validate_volume_encryption(),
            "key_management": self.validate_key_management(),
        }

        # Generate summary
        summary = {
            "total_checks": 5,
            "successful_checks": 0,
            "failed_checks": 0,
            "warnings": [],
        }

        for key, value in report.items():
            if key == "timestamp":
                continue
            if isinstance(value, dict) and value.get("status") == "validated":
                summary["successful_checks"] += 1
            elif isinstance(value, dict) and value.get("status") == "error":
                summary["failed_checks"] += 1
                summary["warnings"].append(f"{key}: {value.get('error', 'Unknown error')}")

        report["summary"] = summary
        return report
