# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Network-based database discovery using port scanning and service fingerprinting.

Uses python-nmap for network scanning capabilities.
"""

import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

# Optional dependency with fallback
try:
    import nmap  # noqa: F401  # pylint: disable=unused-import

    HAS_PYTHON_NMAP = True
except ImportError:
    nmap = None
    HAS_PYTHON_NMAP = False

from .exceptions import NetworkDiscoveryError
from .models import DatabaseDiscovery, DatabaseType, DiscoveryConfig, DiscoveryMethod, NetworkService
from .utils import calculate_confidence_score, generate_database_id, measure_execution_time, normalize_host


class NetworkDiscovery:
    """Network-based database discovery through port scanning and fingerprinting."""

    def __init__(self, config: DiscoveryConfig) -> None:
        """Initialize the network discovery module with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Database service signatures
        self.database_signatures = {
            5432: {
                "type": DatabaseType.POSTGRESQL,
                "service": "postgresql",
                "banners": ["postgresql", "postgres"],
                "probes": [b"\x00\x00\x00\x08\x04\xd2\x16/"],  # PostgreSQL startup packet
            },
            3306: {
                "type": DatabaseType.POSTGRESQL,  # MySQL mapped to PostgreSQL for ViolentUTF
                "service": "mysql",
                "banners": ["mysql", "mariadb"],
                "probes": [b"\x0e\x00\x00\x01\x85\xa6\x03\x00\x00\x00\x00\x01"],  # MySQL handshake
            },
            1433: {
                "type": DatabaseType.POSTGRESQL,  # SQL Server mapped to PostgreSQL
                "service": "mssql",
                "banners": ["microsoft sql server", "mssql"],
                "probes": [b"\x12\x01\x00\x34\x00\x00\x00\x00"],  # SQL Server prelogin
            },
            27017: {
                "type": DatabaseType.POSTGRESQL,  # MongoDB mapped to PostgreSQL
                "service": "mongodb",
                "banners": ["mongodb", "mongo"],
                "probes": [b"\x3f\x00\x00\x00\x01\x00\x00\x00"],  # MongoDB OP_QUERY
            },
            6379: {
                "type": DatabaseType.POSTGRESQL,  # Redis mapped to PostgreSQL
                "service": "redis",
                "banners": ["redis"],
                "probes": [b"*1\r\n$4\r\nPING\r\n"],  # Redis PING command
            },
        }

        # Rate limiting
        self._scan_lock = threading.Lock()
        self._last_scan_time = 0
        self._min_scan_interval = 0.1  # 100ms between scans

    @measure_execution_time
    def discover_network_databases(self) -> List[DatabaseDiscovery]:
        """
        Discover databases through network scanning.

        Returns:
            List of database discoveries from network scanning
        """
        if not self.config.enable_network_discovery:
            self.logger.info("Network discovery disabled in configuration")
            return []

        discoveries = []

        try:
            # Scan all configured network ranges
            for network_range in self.config.network_ranges:
                self.logger.info("Scanning network range: %s", network_range)

                range_discoveries = self._scan_network_range(network_range)
                discoveries.extend(range_discoveries)

            self.logger.info("Discovered %d databases via network scanning", len(discoveries))
            return discoveries

        except Exception as e:
            raise NetworkDiscoveryError(f"Network discovery failed: {e}") from e

    def _scan_network_range(self, network_range: str) -> List[DatabaseDiscovery]:
        """Scan a specific network range for database services."""
        discoveries = []

        try:
            # Normalize the network range
            hosts = self._expand_network_range(network_range)

            self.logger.info("Scanning %d hosts in range %s", len(hosts), network_range)

            # Use ThreadPoolExecutor for concurrent scanning
            with ThreadPoolExecutor(max_workers=self.config.max_concurrent_scans) as executor:
                # Submit scanning tasks
                future_to_host = {executor.submit(self._scan_host_ports, host): host for host in hosts}

                # Collect results
                for future in as_completed(future_to_host):
                    host = future_to_host[future]
                    try:
                        host_discoveries = future.result(timeout=self.config.network_timeout_seconds)
                        discoveries.extend(host_discoveries)

                    except Exception as e:
                        self.logger.debug("Error scanning host %s: %s", host, e)
                        continue

            return discoveries

        except Exception as e:
            self.logger.error("Error scanning network range %s: %s", network_range, e)
            return []

    def _expand_network_range(self, network_range: str) -> List[str]:
        """Expand network range specification to list of hosts."""

        # Handle special cases
        if network_range.lower() in ["localhost", "127.0.0.1"]:
            return ["127.0.0.1"]

        # Handle CIDR notation (basic implementation)
        if "/" in network_range:
            # For ViolentUTF, we typically only scan localhost
            if network_range.startswith("127.0.0.1") or network_range.startswith("localhost"):
                return ["127.0.0.1"]
            else:
                self.logger.warning("CIDR scanning not fully implemented for %s", network_range)
                return []

        # Handle single host
        try:
            # Resolve hostname if needed
            resolved_ip = socket.gethostbyname(network_range)
            return [resolved_ip]
        except socket.gaierror:
            self.logger.warning("Could not resolve hostname: %s", network_range)
            return []

    def _scan_host_ports(self, host: str) -> List[DatabaseDiscovery]:
        """Scan database ports on a specific host."""
        discoveries = []

        # Rate limiting
        with self._scan_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_scan_time
            if time_since_last < self._min_scan_interval:
                time.sleep(self._min_scan_interval - time_since_last)
            self._last_scan_time = time.time()

        for port in self.config.database_ports:
            try:
                service = self._scan_port(host, port)
                if service and service.is_database:
                    discovery = self._create_discovery_from_network_service(service)
                    if discovery:
                        discoveries.append(discovery)
                        self.logger.info("Found %s on %s:%d", service.service_name, host, port)

            except Exception as e:
                self.logger.debug("Error scanning %s:%d: %s", host, port, e)
                continue

        return discoveries

    def _scan_port(self, host: str, port: int) -> Optional[NetworkService]:
        """Scan a specific port and identify the service."""
        try:
            # Basic TCP connection test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.network_timeout_seconds)

            start_time = time.time()
            result = sock.connect_ex((host, port))
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            if result == 0:  # Connection successful
                # Get service banner
                banner = self._get_service_banner(sock, port)
                sock.close()

                # Identify database type
                database_type = self._identify_database_type(port, banner)

                service = NetworkService(
                    host=normalize_host(host),
                    port=port,
                    protocol="tcp",
                    service_name=self.database_signatures.get(port, {}).get("service", "unknown"),
                    banner=banner,
                    response_time_ms=response_time,
                    is_database=(database_type != DatabaseType.UNKNOWN),
                    database_type=database_type if database_type != DatabaseType.UNKNOWN else None,
                )

                return service
            else:
                sock.close()
                return None

        except socket.timeout:
            self.logger.debug("Timeout scanning %s:%d", host, port)
            return None
        except Exception as e:
            self.logger.debug("Error scanning %s:%d: %s", host, port, e)
            return None

    def _get_service_banner(self, sock: socket.socket, port: int) -> Optional[str]:
        """Attempt to get service banner from the connection."""
        try:
            # Send probe if available
            if port in self.database_signatures:
                probes = self.database_signatures[port].get("probes", [])
                if probes:
                    sock.send(probes[0])

            # Try to receive banner
            sock.settimeout(2.0)  # Short timeout for banner
            data = sock.recv(1024)

            if data:
                # Convert bytes to string, handling encoding issues
                try:
                    banner = data.decode("utf-8", errors="ignore").strip()
                    return banner[:200]  # Limit banner length
                except Exception:
                    return data.hex()[:200]  # Return hex if decode fails

            return None

        except socket.timeout:
            return None
        except Exception as e:
            self.logger.debug("Error getting banner for port %d: %s", port, e)
            return None

    def _identify_database_type(self, port: int, banner: Optional[str]) -> DatabaseType:
        """Identify database type from port and banner information."""
        # Check port-based identification first
        if port in self.database_signatures:
            signature = self.database_signatures[port]
            database_type = signature["type"]

            # Verify with banner if available
            if banner:
                banner_lower = banner.lower()
                expected_banners = signature.get("banners", [])

                if any(expected in banner_lower for expected in expected_banners):
                    return database_type
                else:
                    # Port matches but banner doesn't - lower confidence
                    self.logger.debug("Port %d matches %s but banner '%s' doesn't match", port, database_type, banner)
                    return database_type  # Still return the type but with lower confidence

            return database_type

        # Check banner-only identification
        if banner:
            banner_lower = banner.lower()

            if any(keyword in banner_lower for keyword in ["postgresql", "postgres"]):
                return DatabaseType.POSTGRESQL
            elif any(keyword in banner_lower for keyword in ["mysql", "mariadb"]):
                return DatabaseType.POSTGRESQL  # Mapped to PostgreSQL
            elif any(keyword in banner_lower for keyword in ["microsoft sql", "mssql"]):
                return DatabaseType.POSTGRESQL  # Mapped to PostgreSQL
            elif any(keyword in banner_lower for keyword in ["mongodb", "mongo"]):
                return DatabaseType.POSTGRESQL  # Mapped to PostgreSQL
            elif "redis" in banner_lower:
                return DatabaseType.POSTGRESQL  # Mapped to PostgreSQL

        return DatabaseType.UNKNOWN

    def _create_discovery_from_network_service(self, service: NetworkService) -> Optional[DatabaseDiscovery]:
        """Create DatabaseDiscovery from NetworkService."""
        try:
            # Generate unique ID
            db_id = generate_database_id(service.database_type, f"network:{service.host}:{service.port}")

            # Calculate confidence score
            detection_methods = ["network_port", "network_banner"]
            validation_results = {
                "port_match": service.port in self.database_signatures,
                "banner_match": self._validate_banner_match(service),
                "response_time_valid": service.response_time_ms < 5000,  # Reasonable response time
            }

            confidence_score, confidence_level = calculate_confidence_score(detection_methods, validation_results)

            # Create discovery
            discovery = DatabaseDiscovery(
                database_id=db_id,
                database_type=service.database_type,
                name=f"{service.service_name} on {service.host}:{service.port}",
                description=f"Network-discovered {service.database_type.value} service",
                host=service.host,
                port=service.port,
                discovery_method=DiscoveryMethod.NETWORK,
                confidence_level=confidence_level,
                confidence_score=confidence_score,
                is_active=True,  # If we can connect, it's active
                network_service=service,
                tags=["network", "tcp", service.database_type.value],
                custom_properties={"response_time_ms": service.response_time_ms, "banner": service.banner},
            )

            return discovery

        except Exception as e:
            self.logger.error(
                "Failed to create discovery from network service %s:%d: %s", service.host, service.port, e
            )
            return None

    def _validate_banner_match(self, service: NetworkService) -> bool:
        """Validate that the service banner matches expected patterns."""
        if not service.banner or service.port not in self.database_signatures:
            return False

        signature = self.database_signatures[service.port]
        expected_banners = signature.get("banners", [])
        banner_lower = service.banner.lower()

        return any(expected in banner_lower for expected in expected_banners)

    @measure_execution_time
    def discover_localhost_services(self) -> List[DatabaseDiscovery]:
        """Focused discovery of database services on localhost.

        Optimized for ViolentUTF's typical deployment.

        Returns:
            List of localhost database discoveries
        """
        discoveries = []

        try:
            self.logger.info("Performing focused localhost database discovery")

            # Check ViolentUTF's typical database ports
            violentutf_ports = [
                5432,  # PostgreSQL (Keycloak)
                8080,  # Keycloak admin (indirect database indicator)
                9080,  # APISIX (routing to FastAPI with SQLite)
                8501,  # Streamlit (using SQLite)
            ]

            for port in violentutf_ports:
                try:
                    service = self._scan_port("127.0.0.1", port)
                    if service:
                        # Special handling for ViolentUTF services
                        if port == 8080:  # Keycloak
                            service.is_database = True
                            service.database_type = DatabaseType.POSTGRESQL
                            service.service_name = "keycloak-postgresql"
                        elif port == 9080:  # APISIX/FastAPI
                            service.is_database = True
                            service.database_type = DatabaseType.SQLITE
                            service.service_name = "violentutf-api-sqlite"
                        elif port == 8501:  # Streamlit
                            service.is_database = True
                            service.database_type = DatabaseType.SQLITE
                            service.service_name = "violentutf-streamlit-sqlite"

                        if service.is_database:
                            discovery = self._create_discovery_from_network_service(service)
                            if discovery:
                                discoveries.append(discovery)
                                self.logger.info("Found ViolentUTF service: %s", service.service_name)

                except Exception as e:
                    self.logger.debug("Error checking ViolentUTF port %d: %s", port, e)
                    continue

            # Also perform standard database port scanning
            standard_discoveries = self._scan_host_ports("127.0.0.1")

            # Merge and deduplicate
            all_discoveries = discoveries + standard_discoveries
            unique_discoveries = self._deduplicate_discoveries(all_discoveries)

            self.logger.info("Found %d unique database services on localhost", len(unique_discoveries))
            return unique_discoveries

        except Exception as e:
            self.logger.error("Localhost discovery failed: %s", e)
            return []

    def _deduplicate_discoveries(self, discoveries: List[DatabaseDiscovery]) -> List[DatabaseDiscovery]:
        """Remove duplicate discoveries based on host:port combinations."""
        seen = set()
        unique_discoveries = []

        for discovery in discoveries:
            key = f"{discovery.host}:{discovery.port}"
            if key not in seen:
                seen.add(key)
                unique_discoveries.append(discovery)
            else:
                self.logger.debug("Removing duplicate discovery: %s", key)

        return unique_discoveries

    def test_database_connectivity(self, discovery: DatabaseDiscovery) -> bool:
        """
        Test if we can actually connect to the discovered database.

        Args:
            discovery: Database discovery to test

        Returns:
            True if connection is successful
        """
        if not discovery.host or not discovery.port:
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.config.network_timeout_seconds)

            result = sock.connect_ex((discovery.host, discovery.port))
            sock.close()

            is_connected = result == 0
            if is_connected:
                self.logger.debug("Successfully connected to %s:%d", discovery.host, discovery.port)
            else:
                self.logger.debug("Failed to connect to %s:%d", discovery.host, discovery.port)

            return is_connected

        except Exception as e:
            self.logger.debug("Connection test failed for %s:%d: %s", discovery.host, discovery.port, e)
            return False
