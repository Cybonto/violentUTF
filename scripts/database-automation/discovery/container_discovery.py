# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Container-based database discovery using Docker inspection.

Uses python-on-whales for Docker API interaction.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Optional dependency with fallback
try:
    from python_on_whales import DockerClient
    from python_on_whales import exceptions as docker_exceptions

    HAS_PYTHON_ON_WHALES = True
except ImportError:
    # Fallback when python-on-whales is not installed
    DockerClient = None
    docker_exceptions = None
    HAS_PYTHON_ON_WHALES = False

from .exceptions import ContainerDiscoveryError, DiscoveryPermissionError
from .models import ContainerInfo, DatabaseDiscovery, DatabaseType, DiscoveryConfig, DiscoveryMethod
from .utils import calculate_confidence_score, generate_database_id, measure_execution_time, sanitize_for_logging


class ContainerDiscovery:
    """Docker container-based database discovery."""

    def __init__(self, config: DiscoveryConfig) -> None:
        """Initialize the container discovery module with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.docker_client = None

        # Database detection patterns
        self.database_images = {
            "postgres": DatabaseType.POSTGRESQL,
            "postgresql": DatabaseType.POSTGRESQL,
            "mysql": DatabaseType.POSTGRESQL,  # For compatibility
            "mariadb": DatabaseType.POSTGRESQL,
            "sqlite": DatabaseType.SQLITE,
            "duckdb": DatabaseType.DUCKDB,
        }

        self.database_ports = {
            5432: DatabaseType.POSTGRESQL,
            3306: DatabaseType.POSTGRESQL,  # MySQL/MariaDB
            1433: DatabaseType.POSTGRESQL,  # SQL Server
            27017: DatabaseType.POSTGRESQL,  # MongoDB (mapped to PostgreSQL for ViolentUTF)
        }

    def _initialize_docker_client(self) -> None:
        """Initialize Docker client with error handling."""
        if not HAS_PYTHON_ON_WHALES:
            self.logger.warning("python-on-whales not installed. Container discovery will use fallback methods.")
            self.logger.info("Install with: pip install python-on-whales")
            return

        try:
            # Try to connect to Docker daemon
            self.docker_client = DockerClient()

            # Test connection
            self.docker_client.system.info()
            self.logger.info("Successfully connected to Docker daemon")

        except docker_exceptions.DockerException as e:
            raise ContainerDiscoveryError(f"Failed to connect to Docker: {e}") from e
        except PermissionError as e:
            raise DiscoveryPermissionError(f"Insufficient permissions to access Docker: {e}") from e
        except Exception as e:
            raise ContainerDiscoveryError(f"Unexpected error connecting to Docker: {e}") from e

    @measure_execution_time
    def discover_containers(self) -> List[DatabaseDiscovery]:
        """
        Discover databases in running Docker containers.

        Returns:
            List of database discoveries from containers
        """
        if not self.config.enable_container_discovery:
            self.logger.info("Container discovery disabled in configuration")
            return []

        discoveries = []

        try:
            self._initialize_docker_client()

            # Check if Docker client is available
            if not self.docker_client:
                self.logger.warning("Docker client not available. Using fallback discovery methods.")
                return self._discover_containers_fallback()

            # Get all running containers
            containers = self.docker_client.container.list()
            self.logger.info("Found %d running containers", len(containers))

            for container in containers:
                try:
                    container_info = self._analyze_container(container)
                    if container_info and container_info.is_database:
                        discovery = self._create_discovery_from_container(container_info)
                        if discovery:
                            discoveries.append(discovery)

                except Exception as e:
                    self.logger.warning("Error analyzing container %s: %s", container.name, e)
                    continue

            self.logger.info("Discovered %d databases in containers", len(discoveries))
            return discoveries

        except ContainerDiscoveryError:
            raise
        except Exception as e:
            raise ContainerDiscoveryError(f"Container discovery failed: {e}") from e

    def _analyze_container(self, container) -> Optional[ContainerInfo]:  # noqa: ANN001
        """Analyze a single container for database indicators."""
        try:
            # Get container details
            container_data = container.inspect()

            container_info = ContainerInfo(
                container_id=container_data["Id"][:12],
                name=container_data["Name"][1:],  # Remove leading /
                image=container_data["Config"]["Image"],
                status=container_data["State"]["Status"],
                ports=self._extract_port_mappings(container_data),
                environment=self._extract_environment_vars(container_data),
                volumes=self._extract_volume_mounts(container_data),
                networks=list(container_data["NetworkSettings"]["Networks"].keys()),
            )

            # Check if this is a database container
            database_type = self._detect_database_type(container_info)
            if database_type != DatabaseType.UNKNOWN:
                container_info.is_database = True
                container_info.database_type = database_type

                self.logger.info("Detected %s database in container %s", database_type.value, container_info.name)

            return container_info

        except Exception as e:
            self.logger.warning("Failed to analyze container: %s", e)
            return None

    def _extract_port_mappings(self, container_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract port mappings from container data."""
        ports = []

        try:
            port_bindings = container_data.get("NetworkSettings", {}).get("Ports", {})

            for internal_port, bindings in port_bindings.items():
                if bindings:
                    for binding in bindings:
                        ports.append(
                            {
                                "internal_port": int(internal_port.split("/")[0]),
                                "external_port": int(binding.get("HostPort", 0)),
                                "protocol": internal_port.split("/")[1] if "/" in internal_port else "tcp",
                                "host_ip": binding.get("HostIp", "0.0.0.0"),
                            }
                        )
                else:
                    # Exposed but not bound
                    ports.append(
                        {
                            "internal_port": int(internal_port.split("/")[0]),
                            "external_port": None,
                            "protocol": internal_port.split("/")[1] if "/" in internal_port else "tcp",
                            "host_ip": None,
                        }
                    )

        except (ValueError, KeyError, TypeError) as e:
            self.logger.warning("Error extracting port mappings: %s", e)

        return ports

    def _extract_environment_vars(self, container_data: Dict[str, Any]) -> Dict[str, str]:
        """Extract environment variables from container data."""
        env_vars = {}

        try:
            env_list = container_data.get("Config", {}).get("Env", [])

            for env_var in env_list:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    # Sanitize sensitive values for logging
                    env_vars[key] = sanitize_for_logging(value)

        except (KeyError, TypeError) as e:
            self.logger.warning("Error extracting environment variables: %s", e)

        return env_vars

    def _extract_volume_mounts(self, container_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract volume mounts from container data."""
        volumes = []

        try:
            mounts = container_data.get("Mounts", [])

            for mount in mounts:
                volumes.append(
                    {
                        "source": mount.get("Source", ""),
                        "destination": mount.get("Destination", ""),
                        "type": mount.get("Type", ""),
                        "mode": mount.get("Mode", ""),
                        "rw": mount.get("RW", True),
                    }
                )

        except (KeyError, TypeError) as e:
            self.logger.warning("Error extracting volume mounts: %s", e)

        return volumes

    def _detect_database_type(self, container_info: ContainerInfo) -> DatabaseType:
        """Detect database type from container information."""
        # Check image name
        image_lower = container_info.image.lower()
        for image_pattern, db_type in self.database_images.items():
            if image_pattern in image_lower:
                return db_type

        # Check exposed ports
        for port_info in container_info.ports:
            internal_port = port_info["internal_port"]
            if internal_port in self.database_ports:
                return self.database_ports[internal_port]

        # Check environment variables for database indicators
        env_indicators = {
            "POSTGRES_DB": DatabaseType.POSTGRESQL,
            "POSTGRESQL_DATABASE": DatabaseType.POSTGRESQL,
            "MYSQL_DATABASE": DatabaseType.POSTGRESQL,
            "SQLITE_DATABASE": DatabaseType.SQLITE,
        }

        for env_var in container_info.environment.keys():
            for indicator, db_type in env_indicators.items():
                if indicator in env_var.upper():
                    return db_type

        # Check for known ViolentUTF database containers
        violentutf_patterns = [
            "keycloak",  # Keycloak uses PostgreSQL
            "violentutf-api",  # FastAPI uses SQLite
            "postgres",  # Direct PostgreSQL
        ]

        for pattern in violentutf_patterns:
            if pattern in container_info.name.lower() or pattern in image_lower:
                if pattern == "keycloak" or pattern == "postgres":
                    return DatabaseType.POSTGRESQL
                elif pattern == "violentutf-api":
                    return DatabaseType.SQLITE

        return DatabaseType.UNKNOWN

    def _create_discovery_from_container(self, container_info: ContainerInfo) -> Optional[DatabaseDiscovery]:
        """Create DatabaseDiscovery from ContainerInfo."""
        try:
            # Generate unique ID
            db_id = generate_database_id(container_info.database_type, f"container:{container_info.name}")

            # Extract connection details
            host = "localhost"  # Containers typically accessed via localhost
            port = None

            # Find database port
            for port_info in container_info.ports:
                if port_info["external_port"] and port_info["internal_port"] in self.database_ports:
                    port = port_info["external_port"]
                    break

            # Calculate confidence score
            detection_methods = ["container_image", "container_ports", "container_environment"]
            validation_results = {
                "has_image_match": any(
                    pattern in container_info.image.lower() for pattern in self.database_images.keys()
                ),
                "has_port_match": any(port["internal_port"] in self.database_ports for port in container_info.ports),
                "has_env_match": any("DB" in key or "DATABASE" in key for key in container_info.environment.keys()),
            }

            confidence_score, confidence_level = calculate_confidence_score(detection_methods, validation_results)

            # Create discovery
            discovery = DatabaseDiscovery(
                database_id=db_id,
                database_type=container_info.database_type,
                name=f"{container_info.name} ({container_info.database_type.value})",
                description=f"Database in Docker container {container_info.name}",
                host=host,
                port=port,
                discovery_method=DiscoveryMethod.CONTAINER,
                confidence_level=confidence_level,
                confidence_score=confidence_score,
                is_active=container_info.status == "running",
                container_info=container_info,
                tags=["docker", "container", container_info.database_type.value],
            )

            return discovery

        except Exception as e:
            self.logger.error("Failed to create discovery from container %s: %s", container_info.name, e)
            return None

    @measure_execution_time
    def discover_compose_files(self) -> List[DatabaseDiscovery]:
        """
        Discover databases defined in Docker Compose files.

        Returns:
            List of database discoveries from compose files
        """
        if not self.config.scan_compose_files:
            self.logger.info("Compose file scanning disabled in configuration")
            return []

        discoveries = []

        try:
            # Find all compose files
            compose_files = self._find_compose_files()
            self.logger.info("Found %d compose files to analyze", len(compose_files))

            for compose_file in compose_files:
                try:
                    file_discoveries = self._analyze_compose_file(compose_file)
                    discoveries.extend(file_discoveries)

                except Exception as e:
                    self.logger.warning("Error analyzing compose file %s: %s", compose_file, e)
                    continue

            self.logger.info("Discovered %d databases in compose files", len(discoveries))
            return discoveries

        except Exception as e:
            raise ContainerDiscoveryError(f"Compose file discovery failed: {e}") from e

    def _find_compose_files(self) -> List[Path]:
        """Find Docker Compose files in the project."""
        compose_files = []

        # Search in current directory and ViolentUTF subdirectories
        search_paths = [Path.cwd(), Path.cwd() / "violentutf_api", Path.cwd() / "keycloak", Path.cwd() / "apisix"]

        for search_path in search_paths:
            if search_path.exists():
                for pattern in self.config.compose_file_patterns:
                    compose_files.extend(search_path.glob(pattern))

        return list(set(compose_files))  # Remove duplicates

    def _analyze_compose_file(self, compose_file: Path) -> List[DatabaseDiscovery]:
        """Analyze a Docker Compose file for database services."""
        discoveries = []

        try:
            with open(compose_file, "r", encoding="utf-8") as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get("services", {})

            for service_name, service_config in services.items():
                database_type = self._detect_compose_database_type(service_config)

                if database_type != DatabaseType.UNKNOWN:
                    discovery = self._create_discovery_from_compose_service(
                        service_name, service_config, database_type, compose_file
                    )
                    if discovery:
                        discoveries.append(discovery)

            self.logger.debug("Found %d databases in %s", len(discoveries), compose_file)

        except yaml.YAMLError as e:
            self.logger.warning("Invalid YAML in compose file %s: %s", compose_file, e)
        except Exception as e:
            self.logger.warning("Error parsing compose file %s: %s", compose_file, e)

        return discoveries

    def _detect_compose_database_type(self, service_config: Dict[str, Any]) -> DatabaseType:
        """Detect database type from compose service configuration."""
        # Check image
        image = service_config.get("image", "").lower()
        for image_pattern, db_type in self.database_images.items():
            if image_pattern in image:
                return db_type

        # Check ports
        ports = service_config.get("ports", [])
        for port_spec in ports:
            if isinstance(port_spec, str):
                # Format: "external:internal" or just "port"
                if ":" in port_spec:
                    external, internal = port_spec.split(":")  # noqa: F841  # pylint: disable=unused-variable
                    port_num = int(internal)
                else:
                    port_num = int(port_spec)

                if port_num in self.database_ports:
                    return self.database_ports[port_num]

        # Check environment variables
        environment = service_config.get("environment", {})
        if isinstance(environment, list):
            # Convert list format to dict
            env_dict = {}
            for env_var in environment:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    env_dict[key] = value
            environment = env_dict

        env_indicators = {
            "POSTGRES_DB": DatabaseType.POSTGRESQL,
            "POSTGRESQL_DATABASE": DatabaseType.POSTGRESQL,
            "MYSQL_DATABASE": DatabaseType.POSTGRESQL,
        }

        for env_var in environment.keys():
            for indicator, db_type in env_indicators.items():
                if indicator in env_var.upper():
                    return db_type

        return DatabaseType.UNKNOWN

    def _create_discovery_from_compose_service(
        self, service_name: str, service_config: Dict[str, Any], database_type: DatabaseType, compose_file: Path
    ) -> Optional[DatabaseDiscovery]:
        """Create DatabaseDiscovery from compose service configuration."""
        try:
            # Generate unique ID
            db_id = generate_database_id(database_type, f"compose:{compose_file.name}:{service_name}")

            # Extract port information
            port = None
            ports = service_config.get("ports", [])
            for port_spec in ports:
                if isinstance(port_spec, str) and ":" in port_spec:
                    external_port = int(port_spec.split(":")[0])
                    port = external_port
                    break

            # Calculate confidence score
            detection_methods = ["compose_image", "compose_ports", "compose_environment"]
            validation_results = {
                "has_image_match": any(
                    pattern in service_config.get("image", "").lower() for pattern in self.database_images.keys()
                ),
                "has_port_match": port is not None,
                "has_env_match": bool(service_config.get("environment", {})),
            }

            confidence_score, confidence_level = calculate_confidence_score(detection_methods, validation_results)

            # Create discovery
            discovery = DatabaseDiscovery(
                database_id=db_id,
                database_type=database_type,
                name=f"{service_name} (compose: {database_type.value})",
                description=f"Database service in {compose_file.name}",
                host="localhost",
                port=port,
                discovery_method=DiscoveryMethod.CONTAINER,
                confidence_level=confidence_level,
                confidence_score=confidence_score,
                is_active=False,  # Can't determine if compose service is running
                tags=["docker-compose", "service", database_type.value],
                custom_properties={
                    "compose_file": str(compose_file),
                    "service_name": service_name,
                    "service_config": service_config,
                },
            )

            return discovery

        except Exception as e:
            self.logger.error("Failed to create discovery from compose service %s: %s", service_name, e)
            return None

    def _discover_containers_fallback(self) -> List[DatabaseDiscovery]:
        """Fallback container discovery when python-on-whales is not available.

        Uses docker-compose file analysis only.
        """
        self.logger.info("Using fallback container discovery (docker-compose files only)")
        discoveries = []

        try:
            # Only analyze docker-compose files since we can't inspect running containers
            compose_discoveries = self.discover_compose_files()
            discoveries.extend(compose_discoveries)

            if discoveries:
                self.logger.info("Fallback discovery found %d database services in compose files", len(discoveries))
            else:
                self.logger.info("No database services found in docker-compose files")

        except Exception as e:
            self.logger.error("Fallback container discovery failed: %s", e)

        return discoveries
