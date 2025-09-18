# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""File system-based database discovery for SQLite, DuckDB, and configuration files.

Scans directories for database files and extracts connection information.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .exceptions import FilesystemDiscoveryError
from .models import DatabaseDiscovery, DatabaseFile, DatabaseType, DiscoveryConfig, DiscoveryMethod
from .utils import (
    calculate_confidence_score,
    detect_database_type_from_content,
    detect_database_type_from_extension,
    format_file_size,
    generate_database_id,
    is_likely_test_file,
    measure_execution_time,
    parse_connection_string,
    validate_file_path,
    validate_sqlite_database,
)


class FilesystemDiscovery:
    """File system-based database discovery."""

    def __init__(self, config: DiscoveryConfig) -> None:
        """Initialize the filesystem discovery module with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # File patterns for database files
        self.database_patterns = {
            "*.db": DatabaseType.SQLITE,
            "*.sqlite": DatabaseType.SQLITE,
            "*.sqlite3": DatabaseType.SQLITE,
            "*.duckdb": DatabaseType.DUCKDB,
        }

        # Configuration file patterns
        self.config_patterns = {
            "docker-compose*.yml": "docker-compose",
            "docker-compose*.yaml": "docker-compose",
            "*.env": "environment",
            "config*.yml": "yaml-config",
            "config*.yaml": "yaml-config",
            "config*.json": "json-config",
            "database*.yml": "database-config",
            "database*.yaml": "database-config",
        }

        # Known ViolentUTF database locations
        self.violentutf_db_paths = [
            "violentutf_api/fastapi_app/app_data",
            "violentutf/app_data",
            "keycloak/data",
            "apisix/data",
            "data",
            "app_data",
            "*.db",
            "*.sqlite",
            "*.duckdb",
        ]

    @measure_execution_time
    def discover_database_files(self) -> List[DatabaseDiscovery]:
        """
        Discover database files in the file system.

        Returns:
            List of database discoveries from file system scanning
        """
        if not self.config.enable_filesystem_discovery:
            self.logger.info("Filesystem discovery disabled in configuration")
            return []

        discoveries = []

        try:
            # Scan all configured paths
            for scan_path in self.config.scan_paths:
                self.logger.info("Scanning path: %s", scan_path)

                path_discoveries = self._scan_directory(scan_path)
                discoveries.extend(path_discoveries)

            # Also scan known ViolentUTF database locations
            violentutf_discoveries = self._scan_violentutf_locations()
            discoveries.extend(violentutf_discoveries)

            # Deduplicate based on file paths
            unique_discoveries = self._deduplicate_file_discoveries(discoveries)

            self.logger.info("Discovered %d database files", len(unique_discoveries))
            return unique_discoveries

        except Exception as e:
            raise FilesystemDiscoveryError(f"Filesystem discovery failed: {e}") from e

    def _scan_directory(self, directory_path: str) -> List[DatabaseDiscovery]:
        """Scan a directory recursively for database files."""
        discoveries = []

        try:
            base_path = Path(directory_path)

            if not base_path.exists():
                self.logger.warning("Directory does not exist: %s", directory_path)
                return []

            if not base_path.is_dir():
                self.logger.warning("Path is not a directory: %s", directory_path)
                return []

            # Scan for database files
            for extension in self.config.file_extensions:
                pattern = f"**/*{extension}"

                try:
                    for file_path in base_path.rglob(pattern):
                        if self._should_process_file(file_path):
                            discovery = self._analyze_database_file(file_path)
                            if discovery:
                                discoveries.append(discovery)

                except Exception as e:
                    self.logger.warning("Error scanning for %s in %s: %s", pattern, directory_path, e)
                    continue

            self.logger.debug("Found %d database files in %s", len(discoveries), directory_path)
            return discoveries

        except Exception as e:
            self.logger.error("Error scanning directory %s: %s", directory_path, e)
            return []

    def _should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed for database discovery."""
        # Check file size limit
        try:
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.max_file_size_mb:
                self.logger.debug("Skipping large file %s: %.1fMB", file_path, file_size_mb)
                return False
        except OSError:
            return False

        # Check if it's a test file
        if is_likely_test_file(str(file_path)):
            self.logger.debug("Skipping test file: %s", file_path)
            return False

        # Check exclude patterns
        file_str = str(file_path).lower()
        for pattern in self.config.exclude_patterns:
            if pattern.lower() in file_str:
                self.logger.debug("Skipping excluded file: %s", file_path)
                return False

        # Check file accessibility
        if not validate_file_path(str(file_path)):
            self.logger.debug("File not accessible: %s", file_path)
            return False

        return True

    def _analyze_database_file(self, file_path: Path) -> Optional[DatabaseDiscovery]:
        """Analyze a potential database file and create discovery record."""
        try:
            # Get basic file information
            stat_info = file_path.stat()
            file_size = stat_info.st_size
            last_modified = datetime.fromtimestamp(stat_info.st_mtime)

            # Detect database type
            db_type_ext = detect_database_type_from_extension(str(file_path))
            db_type_content = detect_database_type_from_content(str(file_path))

            # Use content detection if available, fall back to extension
            database_type = db_type_content if db_type_content != DatabaseType.UNKNOWN else db_type_ext

            if database_type == DatabaseType.UNKNOWN:
                self.logger.debug("Could not determine database type for %s", file_path)
                return None

            # Create DatabaseFile record
            database_file = DatabaseFile(
                file_path=str(file_path.absolute()),
                file_size=file_size,
                last_modified=last_modified,
                file_type=file_path.suffix.lower(),
                database_type=database_type,
                is_accessible=True,
            )

            # Extract schema information for SQLite databases
            if database_type == DatabaseType.SQLITE:
                is_valid, schema_info = validate_sqlite_database(str(file_path))
                database_file.schema_info = schema_info
                if not is_valid:
                    self.logger.debug("Invalid SQLite file: %s", file_path)
                    return None

            # Generate discovery record
            discovery = self._create_discovery_from_file(database_file)
            return discovery

        except Exception as e:
            self.logger.warning("Error analyzing file %s: %s", file_path, e)
            return None

    def _create_discovery_from_file(self, database_file: DatabaseFile) -> DatabaseDiscovery:
        """Create DatabaseDiscovery from DatabaseFile."""
        # Generate unique ID
        db_id = generate_database_id(database_file.database_type, f"file:{database_file.file_path}")

        # Calculate confidence score
        detection_methods = ["file_extension", "file_content"]
        validation_results = {
            "file_accessible": database_file.is_accessible,
            "valid_content": (
                database_file.schema_info is not None if database_file.database_type == DatabaseType.SQLITE else True
            ),
            "reasonable_size": database_file.file_size > 0,
        }

        confidence_score, confidence_level = calculate_confidence_score(detection_methods, validation_results)

        # Determine if this is a ViolentUTF database
        file_path_lower = database_file.file_path.lower()
        is_violentutf = any(pattern in file_path_lower for pattern in ["violentutf", "pyrit", "keycloak", "apisix"])

        # Create discovery
        discovery = DatabaseDiscovery(
            database_id=db_id,
            database_type=database_file.database_type,
            name=Path(database_file.file_path).name,
            description=f"File-based {database_file.database_type.value} database",
            file_path=database_file.file_path,
            discovery_method=DiscoveryMethod.FILESYSTEM,
            confidence_level=confidence_level,
            confidence_score=confidence_score,
            size_mb=database_file.file_size / (1024 * 1024),
            is_active=self._is_file_recently_accessed(database_file),
            is_accessible=database_file.is_accessible,
            database_files=[database_file],
            tags=["file", database_file.database_type.value] + (["violentutf"] if is_violentutf else []),
            custom_properties={
                "file_size_formatted": format_file_size(database_file.file_size),
                "last_modified": database_file.last_modified.isoformat(),
                "file_extension": database_file.file_type,
                "schema_info": database_file.schema_info,
            },
        )

        return discovery

    def _is_file_recently_accessed(self, database_file: DatabaseFile) -> bool:
        """Determine if a database file has been recently accessed (indication of active use)."""
        try:
            # Consider file active if modified within last 30 days
            now = datetime.now()
            time_diff = now - database_file.last_modified
            return time_diff.days < 30
        except Exception:
            return False

    def _scan_violentutf_locations(self) -> List[DatabaseDiscovery]:
        """Scan known ViolentUTF database locations."""
        discoveries = []

        # Get the current working directory (should be ViolentUTF root)
        base_path = Path.cwd()

        self.logger.info("Scanning known ViolentUTF database locations")

        for location in self.violentutf_db_paths:
            try:
                if location.startswith("*"):
                    # Pattern search
                    for file_path in base_path.rglob(location):
                        if self._should_process_file(file_path):
                            discovery = self._analyze_database_file(file_path)
                            if discovery:
                                discoveries.append(discovery)
                else:
                    # Directory search
                    dir_path = base_path / location
                    if dir_path.exists() and dir_path.is_dir():
                        dir_discoveries = self._scan_directory(str(dir_path))
                        discoveries.extend(dir_discoveries)

            except Exception as e:
                self.logger.debug("Error scanning ViolentUTF location %s: %s", location, e)
                continue

        self.logger.info("Found %d databases in ViolentUTF locations", len(discoveries))
        return discoveries

    @measure_execution_time
    def discover_configuration_files(self) -> List[DatabaseDiscovery]:
        """
        Discover databases referenced in configuration files.

        Returns:
            List of database discoveries from configuration files
        """
        discoveries = []

        try:
            # Find configuration files
            config_files = self._find_configuration_files()
            self.logger.info("Found %d configuration files to analyze", len(config_files))

            for config_file in config_files:
                try:
                    file_discoveries = self._analyze_configuration_file(config_file)
                    discoveries.extend(file_discoveries)

                except Exception as e:
                    self.logger.warning("Error analyzing config file %s: %s", config_file, e)
                    continue

            self.logger.info("Discovered %d databases from configuration files", len(discoveries))
            return discoveries

        except Exception as e:
            self.logger.error("Configuration file discovery failed: %s", e)
            return []

    def _find_configuration_files(self) -> List[Path]:
        """Find configuration files in the project."""
        config_files = []
        base_path = Path.cwd()

        # Search for configuration files
        for pattern in self.config_patterns.keys():
            config_files.extend(base_path.rglob(pattern))

        # Filter out excluded paths
        filtered_files = []
        for file_path in config_files:
            if self._should_process_file(file_path):
                filtered_files.append(file_path)

        return filtered_files

    def _analyze_configuration_file(self, config_file: Path) -> List[DatabaseDiscovery]:
        """Analyze a configuration file for database references."""
        discoveries = []

        try:
            # Read file content
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse based on file type
            if config_file.suffix.lower() in [".yml", ".yaml"]:
                discoveries.extend(self._parse_yaml_config(config_file, content))
            elif config_file.suffix.lower() == ".json":
                discoveries.extend(self._parse_json_config(config_file, content))
            elif config_file.suffix.lower() == ".env":
                discoveries.extend(self._parse_env_config(config_file, content))
            else:
                # Generic text search for database patterns
                discoveries.extend(self._parse_generic_config(config_file, content))

        except Exception as e:
            self.logger.warning("Error reading config file %s: %s", config_file, e)

        return discoveries

    def _parse_yaml_config(self, config_file: Path, content: str) -> List[DatabaseDiscovery]:
        """Parse YAML configuration file for database references."""
        discoveries = []

        try:
            data = yaml.safe_load(content)
            if not data:
                return []

            # Look for database configurations
            database_refs = self._extract_database_references(data, str(config_file))

            for ref in database_refs:
                discovery = self._create_discovery_from_config_ref(ref, config_file)
                if discovery:
                    discoveries.append(discovery)

        except yaml.YAMLError as e:
            self.logger.warning("Invalid YAML in %s: %s", config_file, e)

        return discoveries

    def _parse_json_config(self, config_file: Path, content: str) -> List[DatabaseDiscovery]:
        """Parse JSON configuration file for database references."""
        discoveries = []

        try:
            data = json.loads(content)

            # Look for database configurations
            database_refs = self._extract_database_references(data, str(config_file))

            for ref in database_refs:
                discovery = self._create_discovery_from_config_ref(ref, config_file)
                if discovery:
                    discoveries.append(discovery)

        except json.JSONDecodeError as e:
            self.logger.warning("Invalid JSON in %s: %s", config_file, e)

        return discoveries

    def _parse_env_config(self, config_file: Path, content: str) -> List[DatabaseDiscovery]:
        """Parse environment file for database configurations."""
        discoveries = []

        try:
            lines = content.split("\n")

            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")

                    # Check if this looks like a database configuration
                    if self._is_database_environment_var(key, value):
                        ref = {
                            "type": "environment_variable",
                            "key": key,
                            "value": value,
                            "file": str(config_file),
                            "line": line_num,
                        }

                        discovery = self._create_discovery_from_config_ref(ref, config_file)
                        if discovery:
                            discoveries.append(discovery)

        except Exception as e:
            self.logger.warning("Error parsing env file %s: %s", config_file, e)

        return discoveries

    def _parse_generic_config(self, config_file: Path, content: str) -> List[DatabaseDiscovery]:
        """Parse generic configuration file for database patterns."""
        discoveries = []

        # Look for connection string patterns
        connection_patterns = [r"postgresql://\S+", r"sqlite:///\S+", r"mysql://\S+", r"mongodb://\S+"]

        import re

        for pattern in connection_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                connection_info = parse_connection_string(match)
                if connection_info:
                    ref = {
                        "type": "connection_string",
                        "connection_string": match,
                        "parsed": connection_info,
                        "file": str(config_file),
                    }

                    discovery = self._create_discovery_from_config_ref(ref, config_file)
                    if discovery:
                        discoveries.append(discovery)

        return discoveries

    def _extract_database_references(self, data: Dict[str, Any], file_path: str) -> List[Dict[str, Any]]:
        """Recursively extract database references from configuration data."""
        references = []

        if isinstance(data, dict):
            for key, value in data.items():
                # Check for database-related keys
                if self._is_database_config_key(key):
                    ref = {"type": "config_key", "key": key, "value": value, "file": file_path}
                    references.append(ref)

                # Check for connection strings
                if isinstance(value, str) and "://" in value:
                    connection_info = parse_connection_string(value)
                    if connection_info:
                        ref = {
                            "type": "connection_string",
                            "key": key,
                            "connection_string": value,
                            "parsed": connection_info,
                            "file": file_path,
                        }
                        references.append(ref)

                # Recurse into nested structures
                references.extend(self._extract_database_references(value, file_path))

        elif isinstance(data, list):
            for item in data:
                references.extend(self._extract_database_references(item, file_path))

        return references

    def _is_database_config_key(self, key: str) -> bool:
        """Check if a configuration key is database-related."""
        key_lower = key.lower()
        database_keywords = [
            "database",
            "db",
            "datasource",
            "connection",
            "postgres",
            "postgresql",
            "mysql",
            "sqlite",
            "mongo",
            "mongodb",
            "redis",
        ]

        return any(keyword in key_lower for keyword in database_keywords)

    def _is_database_environment_var(self, key: str, value: str) -> bool:
        """Check if an environment variable is database-related."""
        key_lower = key.lower()
        value_lower = value.lower()

        # Database-related environment variable patterns
        db_env_patterns = [
            "database_url",
            "db_url",
            "postgres_",
            "postgresql_",
            "mysql_",
            "sqlite_",
            "mongo_",
            "redis_",
        ]

        # Check key patterns
        if any(pattern in key_lower for pattern in db_env_patterns):
            return True

        # Check for connection string in value
        if "://" in value and any(db in value_lower for db in ["postgres", "mysql", "sqlite", "mongo"]):
            return True

        # Check for database file paths
        if value.endswith((".db", ".sqlite", ".sqlite3", ".duckdb")):
            return True

        return False

    def _create_discovery_from_config_ref(self, ref: Dict[str, Any], config_file: Path) -> Optional[DatabaseDiscovery]:
        """Create DatabaseDiscovery from configuration reference."""
        try:
            # Determine database type
            if "parsed" in ref and ref["parsed"]:
                parsed = ref["parsed"]
                db_type_str = parsed.get("type", "unknown")
                if db_type_str == "postgresql":
                    database_type = DatabaseType.POSTGRESQL
                elif db_type_str == "sqlite":
                    database_type = DatabaseType.SQLITE
                else:
                    database_type = DatabaseType.UNKNOWN
            else:
                # Try to infer from key or value
                ref_str = f"{ref.get('key', '')} {ref.get('value', '')}".lower()
                if "postgres" in ref_str:
                    database_type = DatabaseType.POSTGRESQL
                elif "sqlite" in ref_str:
                    database_type = DatabaseType.SQLITE
                elif "duckdb" in ref_str:
                    database_type = DatabaseType.DUCKDB
                else:
                    database_type = DatabaseType.UNKNOWN

            if database_type == DatabaseType.UNKNOWN:
                return None

            # Generate unique ID
            ref_identifier = f"config:{config_file.name}:{ref.get('key', 'unknown')}"
            db_id = generate_database_id(database_type, ref_identifier)

            # Calculate confidence score
            detection_methods = ["config_file"]
            validation_results = {
                "has_connection_string": "connection_string" in ref,
                "has_parsed_info": "parsed" in ref,
                "has_db_keywords": self._is_database_config_key(ref.get("key", "")),
            }

            confidence_score, confidence_level = calculate_confidence_score(
                detection_methods, validation_results, consistency_score=0.7
            )

            # Extract connection details
            host = None
            port = None
            file_path = None

            if "parsed" in ref and ref["parsed"]:
                parsed = ref["parsed"]
                host = parsed.get("host")
                port = int(parsed["port"]) if parsed.get("port") else None
                file_path = parsed.get("path")

            # Create discovery
            discovery = DatabaseDiscovery(
                database_id=db_id,
                database_type=database_type,
                name=f"Config: {ref.get('key', 'Database')}",
                description=f"Database referenced in {config_file.name}",
                host=host,
                port=port,
                file_path=file_path,
                connection_string=ref.get("connection_string"),
                discovery_method=DiscoveryMethod.FILESYSTEM,
                confidence_level=confidence_level,
                confidence_score=confidence_score,
                is_active=False,  # Can't determine from config alone
                tags=["configuration", database_type.value, config_file.suffix[1:]],
                custom_properties={
                    "config_file": str(config_file),
                    "config_key": ref.get("key"),
                    "reference_type": ref.get("type"),
                    "line_number": ref.get("line"),
                },
            )

            return discovery

        except Exception as e:
            self.logger.error("Failed to create discovery from config reference: %s", e)
            return None

    def _deduplicate_file_discoveries(self, discoveries: List[DatabaseDiscovery]) -> List[DatabaseDiscovery]:
        """Remove duplicate file-based discoveries."""
        seen_files = set()
        unique_discoveries = []

        for discovery in discoveries:
            # Use file path as unique identifier for file-based discoveries
            if discovery.file_path:
                file_key = Path(discovery.file_path).resolve()
                if file_key not in seen_files:
                    seen_files.add(file_key)
                    unique_discoveries.append(discovery)
                else:
                    self.logger.debug("Removing duplicate file discovery: %s", discovery.file_path)
            else:
                # For config-based discoveries without file paths, use database_id
                unique_discoveries.append(discovery)

        return unique_discoveries
