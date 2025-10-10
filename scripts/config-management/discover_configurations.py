#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Configuration Discovery Tool for ViolentUTF - Issue #266.

Discovers and catalogs configuration files across all environments.
"""

import configparser
import hashlib
import json
import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConfigurationFile:
    """Represents a discovered configuration file."""

    path: str
    file_type: str  # 'yaml', 'json', 'env', 'ini', 'toml'
    service: str
    environment: str
    size_bytes: int
    modified_time: str
    checksum: str
    content_preview: Optional[Dict[str, Any]] = None


class ConfigurationDiscovery:
    """Main configuration discovery engine."""

    def __init__(self, base_path: str, database_path: str = "config_discovery.db") -> None:
        """Initialize the configuration discovery tool.

        Args:
            base_path: Base directory path for ViolentUTF project
            database_path: Path to SQLite database for storing discovery results
        """
        self.base_path = Path(base_path)
        self.database_path = database_path
        self.supported_extensions = {
            ".yaml": "yaml",
            ".yml": "yaml",
            ".json": "json",
            ".env": "env",
            ".ini": "ini",
            ".toml": "toml",
            ".conf": "conf",
            ".config": "config",
        }
        self._setup_database()

    def _setup_database(self) -> None:
        """Set up SQLite database for storing discovery results."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS discovered_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                service TEXT NOT NULL,
                environment TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_time TEXT NOT NULL,
                checksum TEXT NOT NULL,
                content_preview TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS discovery_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_path TEXT NOT NULL,
                files_discovered INTEGER NOT NULL,
                environments_found INTEGER NOT NULL,
                services_found INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def discover_files(self, environments: List[str] = None) -> Dict[str, Any]:
        """Discover all configuration files across specified environments.

        Args:
            environments: List of environments to scan (e.g., ['dev', 'staging', 'prod'])
                        If None, auto-detect environments

        Returns:
            Dictionary containing discovery results
        """
        start_time = datetime.now()
        logger.info("Starting configuration discovery in %s", self.base_path)

        if environments is None:
            environments = self._detect_environments()

        discovered_files = {}
        total_files = 0
        services_found = set()

        for environment in environments:
            env_files = self._scan_environment(environment)
            discovered_files[environment] = env_files
            total_files += len(env_files)
            services_found.update(file.service for file in env_files)

        # Store discovery results in database
        duration = (datetime.now() - start_time).total_seconds()
        self._store_discovery_run(len(discovered_files), total_files, len(services_found), duration)

        logger.info("Discovery completed: %s files across %s environments", total_files, len(environments))

        return {
            "environments": list(discovered_files.keys()),
            "total_files": total_files,
            "services_discovered": list(services_found),
            "files_by_environment": {
                env: [self._file_to_dict(f) for f in files] for env, files in discovered_files.items()
            },
            "discovery_duration_seconds": duration,
            "discovery_timestamp": start_time.isoformat(),
        }

    def _detect_environments(self) -> List[str]:
        """Auto-detect available environments in the project."""
        potential_envs = []

        # Look for common environment indicators
        env_patterns = [
            "dev",
            "development",
            "test",
            "testing",
            "staging",
            "stage",
            "prod",
            "production",
            "qa",
            "quality",
        ]

        # Check for directories with environment names
        for item in self.base_path.iterdir():
            if item.is_dir():
                dir_name = item.name.lower()
                for pattern in env_patterns:
                    if pattern in dir_name:
                        potential_envs.append(item.name)
                        break

        # Check for .env files with environment suffixes
        env_files = list(self.base_path.glob("*.env*"))
        for env_file in env_files:
            parts = env_file.name.split(".")
            if len(parts) > 2:
                potential_envs.append(parts[-1])

        # Default environments if none detected
        if not potential_envs:
            potential_envs = ["dev", "staging", "prod"]
            logger.warning("No environments detected, using defaults: dev, staging, prod")

        return list(set(potential_envs))

    def _scan_environment(self, environment: str) -> List[ConfigurationFile]:
        """Scan a specific environment for configuration files.

        Args:
            environment: Environment name to scan

        Returns:
            List of discovered configuration files
        """
        discovered_files = []

        # Define search patterns for different services
        search_patterns = [
            # Service-specific directories
            f"*/{environment}/**/*",
            f"{environment}/**/*",
            # Service configs with environment suffix
            f"*/*{environment}*",
            # Environment files
            f"*.env.{environment}",
            f".env.{environment}",
            # Docker compose files
            f"docker-compose.{environment}.yml",
            f"docker-compose.{environment}.yaml",
        ]

        for pattern in search_patterns:
            for file_path in self.base_path.glob(pattern):
                if self._is_configuration_file(file_path):
                    config_file = self._analyze_configuration_file(file_path, environment)
                    if config_file:
                        discovered_files.append(config_file)

        # Remove duplicates based on file path
        seen_paths = set()
        unique_files = []
        for file in discovered_files:
            if file.path not in seen_paths:
                seen_paths.add(file.path)
                unique_files.append(file)

        return unique_files

    def _is_configuration_file(self, file_path: Path) -> bool:
        """Check if a file is a configuration file.

        Args:
            file_path: Path to the file

        Returns:
            True if the file is a configuration file
        """
        if not file_path.is_file():
            return False

        # Check by extension
        if file_path.suffix.lower() in self.supported_extensions:
            return True

        # Check by filename patterns
        config_patterns = ["config", "configuration", ".env", "settings", "docker-compose", "realm-export"]

        filename_lower = file_path.name.lower()
        return any(pattern in filename_lower for pattern in config_patterns)

    def _analyze_configuration_file(self, file_path: Path, environment: str) -> Optional[ConfigurationFile]:
        """Analyze a configuration file and create ConfigurationFile object.

        Args:
            file_path: Path to the configuration file
            environment: Environment this file belongs to

        Returns:
            ConfigurationFile object or None if analysis fails
        """
        try:
            stat = file_path.stat()
            file_size = stat.st_size
            modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()

            # Calculate file checksum
            checksum = self._calculate_checksum(file_path)

            # Determine file type
            file_type = self._determine_file_type(file_path)

            # Determine service
            service = self._determine_service(file_path)

            # Get content preview (first few configuration keys)
            content_preview = self._get_content_preview(file_path, file_type)

            return ConfigurationFile(
                path=str(file_path.relative_to(self.base_path)),
                file_type=file_type,
                service=service,
                environment=environment,
                size_bytes=file_size,
                modified_time=modified_time,
                checksum=checksum,
                content_preview=content_preview,
            )

        except Exception as e:
            logger.error("Error analyzing file %s: %s", file_path, e)
            return None

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 checksum as hex string
        """
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error("Error calculating checksum for %s: %s", file_path, e)
            return "error"

    def _determine_file_type(self, file_path: Path) -> str:
        """Determine the configuration file type.

        Args:
            file_path: Path to the file

        Returns:
            File type string
        """
        suffix = file_path.suffix.lower()
        if suffix in self.supported_extensions:
            return self.supported_extensions[suffix]

        # Special cases based on filename
        filename = file_path.name.lower()
        if filename.startswith(".env"):
            return "env"
        elif "docker-compose" in filename:
            return "yaml"
        elif "realm-export" in filename:
            return "json"

        return "unknown"

    def _determine_service(self, file_path: Path) -> str:
        """Determine which service a configuration file belongs to.

        Args:
            file_path: Path to the file

        Returns:
            Service name string
        """
        path_str = str(file_path).lower()

        # Service mapping based on path patterns
        service_patterns = {
            "apisix": ["apisix", "gateway"],
            "keycloak": ["keycloak", "auth", "sso"],
            "postgres": ["postgres", "postgresql", "database"],
            "violentutf_api": ["violentutf_api", "fastapi", "api"],
            "violentutf": ["violentutf", "streamlit"],
            "docker": ["docker", "compose"],
            "nginx": ["nginx", "web"],
            "redis": ["redis", "cache"],
        }

        for service, patterns in service_patterns.items():
            if any(pattern in path_str for pattern in patterns):
                return service

        # Try to determine from parent directory
        parent_dirs = file_path.parts
        for part in reversed(parent_dirs):
            part_lower = part.lower()
            for service, patterns in service_patterns.items():
                if any(pattern in part_lower for pattern in patterns):
                    return service

        return "unknown"

    def _get_content_preview(self, file_path: Path, file_type: str) -> Optional[Dict[str, Any]]:
        """Get a preview of configuration file content.

        Args:
            file_path: Path to the file
            file_type: Type of the configuration file

        Returns:
            Dictionary with preview of file content or None if unable to parse
        """
        try:
            if file_type == "yaml":
                return self._preview_yaml(file_path)
            elif file_type == "json":
                return self._preview_json(file_path)
            elif file_type == "env":
                return self._preview_env(file_path)
            elif file_type == "ini":
                return self._preview_ini(file_path)
            else:
                return None
        except Exception as e:
            logger.debug("Could not preview %s: %s", file_path, e)
            return None

    def _preview_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Get preview of YAML configuration file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if isinstance(data, dict):
            # Return top-level keys and their types
            preview = {}
            for key, value in list(data.items())[:10]:  # Limit to first 10 keys
                if isinstance(value, (str, int, float, bool)):
                    preview[key] = value
                else:
                    preview[key] = f"<{type(value).__name__}>"
            return preview

        return {"content_type": type(data).__name__}

    def _preview_json(self, file_path: Path) -> Dict[str, Any]:
        """Get preview of JSON configuration file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            # Return top-level keys and their types
            preview = {}
            for key, value in list(data.items())[:10]:  # Limit to first 10 keys
                if isinstance(value, (str, int, float, bool)):
                    preview[key] = value
                else:
                    preview[key] = f"<{type(value).__name__}>"
            return preview

        return {"content_type": type(data).__name__}

    def _preview_env(self, file_path: Path) -> Dict[str, Any]:
        """Get preview of environment file."""
        env_vars = {}
        with open(file_path, "r", encoding="utf-8") as f:
            for _, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # Mask sensitive values
                        if any(sensitive in key.upper() for sensitive in ["PASSWORD", "SECRET", "KEY", "TOKEN"]):
                            value = "[REDACTED]"
                        env_vars[key.strip()] = value.strip()

                if len(env_vars) >= 10:  # Limit preview
                    break

        return env_vars

    def _preview_ini(self, file_path: Path) -> Dict[str, Any]:
        """Get preview of INI configuration file."""
        config = configparser.ConfigParser()
        config.read(file_path)

        preview = {}
        for section_name in list(config.sections())[:5]:  # Limit sections
            section_preview = {}
            section = config[section_name]
            for key in list(section.keys())[:5]:  # Limit keys per section
                value = section[key]
                # Mask sensitive values
                if any(sensitive in key.upper() for sensitive in ["PASSWORD", "SECRET", "KEY", "TOKEN"]):
                    value = "[REDACTED]"
                section_preview[key] = value
            preview[section_name] = section_preview

        return preview

    def _file_to_dict(self, config_file: ConfigurationFile) -> Dict[str, Any]:
        """Convert ConfigurationFile to dictionary."""
        return {
            "path": config_file.path,
            "file_type": config_file.file_type,
            "service": config_file.service,
            "environment": config_file.environment,
            "size_bytes": config_file.size_bytes,
            "modified_time": config_file.modified_time,
            "checksum": config_file.checksum,
            "content_preview": config_file.content_preview,
        }

    def _store_discovery_run(self, environments: int, files: int, services: int, duration: float) -> None:
        """Store discovery run results in database."""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO discovery_runs
            (base_path, files_discovered, environments_found, services_found, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        """,
            (str(self.base_path), files, environments, services, duration),
        )

        conn.commit()
        conn.close()

    def get_discovery_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get history of discovery runs.

        Args:
            limit: Maximum number of runs to return

        Returns:
            List of discovery run records
        """
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM discovery_runs
            ORDER BY run_timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )

        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        conn.close()
        return results


def main() -> None:
    """Run configuration discovery from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="ViolentUTF Configuration Discovery Tool")
    parser.add_argument("--base-path", default=".", help="Base path for ViolentUTF project")
    parser.add_argument("--environments", nargs="*", help="Environments to scan")
    parser.add_argument("--output", help="Output file for discovery results (JSON)")
    parser.add_argument("--database", default="config_discovery.db", help="Database file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize discovery tool
    discovery = ConfigurationDiscovery(args.base_path, args.database)

    # Perform discovery
    results = discovery.discover_files(args.environments)

    # Output results
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {args.output}")
    else:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
