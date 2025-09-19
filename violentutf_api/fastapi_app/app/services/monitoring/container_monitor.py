# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Container Lifecycle Monitoring for Issue #283.

This module implements comprehensive container lifecycle monitoring that detects
database services and monitors their lifecycle events in real-time.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    from docker.errors import DockerException

    DOCKER_AVAILABLE = True
except ImportError:
    # Docker not available - monitoring will be disabled
    docker = None
    DockerException = Exception
    DOCKER_AVAILABLE = False
from app.models.asset_inventory import AssetType, CriticalityLevel, Environment, SecurityClassification
from app.models.monitoring import AlertSeverity, NotificationChannel
from app.schemas.asset_schemas import AssetCreate, AssetResponse
from app.schemas.monitoring_schemas import ContainerInfo, EndpointStatus
from app.services.asset_management.asset_service import AssetService
from app.services.monitoring.notifications import NotificationService

logger = logging.getLogger(__name__)


class ContainerLifecycleMonitor:
    """Service for monitoring Docker container lifecycle events.

    This service monitors Docker daemon events to detect database containers
    and manage their lifecycle within the asset management system.
    """

    def __init__(
        self,
        docker_client: Optional[Any],  # docker.DockerClient when available
        event_handler: "ContainerEventHandler",
        asset_service: AssetService,
    ) -> None:
        """Initialize the container lifecycle monitor.

        Args:
            docker_client: Docker client for container monitoring
            event_handler: Handler for container events
            asset_service: Service for asset management operations
        """
        self.docker_client = docker_client
        self.event_handler = event_handler
        self.asset_service = asset_service
        self.monitoring_active = False
        self.monitored_containers: Dict[str, ContainerInfo] = {}

    async def start_monitoring(self) -> None:
        """Start continuous container monitoring."""
        if not DOCKER_AVAILABLE:
            logger.warning("Docker not available - container monitoring disabled")
            return

        logger.info("Starting container lifecycle monitoring")
        self.monitoring_active = True

        try:
            # Initial discovery of existing containers
            await self.discover_existing_containers()

            # Start event monitoring
            await asyncio.create_task(self.monitor_container_events())
        except Exception as e:
            logger.error("Error starting container monitoring: %s", e)
            self.monitoring_active = False
            raise

    async def stop_monitoring(self) -> None:
        """Stop container monitoring."""
        logger.info("Stopping container lifecycle monitoring")
        self.monitoring_active = False

    async def discover_existing_containers(self) -> None:
        """Discover existing database containers."""
        logger.info("Discovering existing database containers")

        try:
            containers = self.docker_client.containers.list(all=True)

            for container in containers:
                if await self.is_database_container(container):
                    container_info = await self.extract_container_info(container)
                    self.monitored_containers[container.id] = container_info

                    # Check if asset exists
                    existing_asset = await self.asset_service.find_by_container_id(container.id)
                    if not existing_asset:
                        # Create new asset for discovered container
                        await self.handle_container_discovery(container_info)

            logger.info("Discovered %s database containers", len(self.monitored_containers))

        except DockerException as e:
            logger.error("Error discovering containers: %s", e)
            raise

    async def monitor_container_events(self) -> None:
        """Monitor Docker events for container lifecycle changes."""
        logger.info("Starting Docker event monitoring")

        event_filters = {
            "type": "container",
            "event": ["start", "stop", "restart", "die", "create", "destroy"],
        }

        try:
            for event in self.docker_client.events(filters=event_filters, decode=True):
                if not self.monitoring_active:
                    logger.info("Container monitoring stopped")
                    break

                await self.process_container_event(event)

        except Exception as e:
            logger.error("Error monitoring container events: %s", e)
            # Restart monitoring after brief delay
            await asyncio.sleep(10)
            if self.monitoring_active:
                logger.info("Restarting container event monitoring")
                await self.monitor_container_events()

    async def process_container_event(self, event: Dict[str, Any]) -> None:
        """Process individual container event.

        Args:
            event: Docker event data
        """
        container_id = event.get("id")
        event_action = event.get("Action")

        logger.debug("Processing container event: %s for %s", event_action, container_id)

        try:
            container = self.docker_client.containers.get(container_id)
            is_database_container = await self.is_database_container(container)

            if is_database_container:
                container_info = await self.extract_container_info(container)

                if event_action in ["start", "create"]:
                    await self.handle_container_start(container_info)
                elif event_action in ["stop", "die", "destroy"]:
                    await self.handle_container_stop(container_info)
                elif event_action == "restart":
                    await self.handle_container_restart(container_info)

                # Update monitoring cache
                self.monitored_containers[container_id] = container_info

        except Exception as e:
            logger.warning("Error processing container event %s for %s: %s", event_action, container_id, e)

    async def is_database_container(self, container: Any) -> bool:  # noqa: ANN401
        """Determine if container is a database service.

        Args:
            container: Docker container object

        Returns:
            True if container is identified as a database service
        """
        # Check image name patterns
        image_name = container.image.tags[0] if container.image.tags else ""
        database_images = ["postgres", "mysql", "redis", "mongodb", "sqlite", "duckdb", "mariadb", "oracle"]

        if any(db_name in image_name.lower() for db_name in database_images):
            return True

        # Check exposed ports
        port_config = container.attrs.get("NetworkSettings", {}).get("Ports", {})
        database_ports = ["5432", "3306", "1433", "27017", "6379", "1521", "5984"]

        for port in database_ports:
            if f"{port}/tcp" in port_config:
                return True

        # Check environment variables
        env_vars = container.attrs.get("Config", {}).get("Env", [])
        database_env_patterns = ["POSTGRES_", "MYSQL_", "MONGO_", "REDIS_", "ORACLE_", "MARIADB_"]

        for env_var in env_vars:
            if any(pattern in env_var for pattern in database_env_patterns):
                return True

        # Check container labels
        labels = container.labels or {}
        if "database" in labels.get("service.type", "").lower():
            return True

        return False

    async def extract_container_info(self, container: Any) -> ContainerInfo:  # noqa: ANN401
        """Extract container information for monitoring.

        Args:
            container: Docker container object

        Returns:
            ContainerInfo object with extracted data
        """
        attrs = container.attrs
        config = attrs.get("Config", {})
        network_settings = attrs.get("NetworkSettings", {})

        # Parse environment variables
        env_vars = {}
        for env_var in config.get("Env", []):
            if "=" in env_var:
                key, value = env_var.split("=", 1)
                env_vars[key] = value

        # Parse creation time
        created_str = attrs.get("Created", "")
        try:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created = datetime.now(timezone.utc)

        return ContainerInfo(
            id=container.id,
            name=container.name,
            image=container.image.tags[0] if container.image.tags else "unknown",
            status=container.status,
            ports=network_settings.get("Ports", {}),
            environment=env_vars,
            labels=container.labels or {},
            created=created,
        )

    async def handle_container_start(self, container_info: ContainerInfo) -> None:
        """Handle database container start event.

        Args:
            container_info: Container information
        """
        logger.info("Handling container start: %s", container_info.name)

        # Check if this is a new database service
        existing_asset = await self.asset_service.find_by_container_id(container_info.id)

        if not existing_asset:
            # New database service detected
            new_asset_data = await self.create_asset_from_container(container_info)
            asset = await self.asset_service.create_asset(new_asset_data, created_by="container-monitor")

            # Trigger discovery validation
            await self.event_handler.handle_new_database_detected(asset, container_info)
        else:
            # Existing service restarted
            await self.asset_service.update_asset_status(existing_asset.id, "RUNNING")
            await self.event_handler.handle_database_restart(existing_asset, container_info)

    async def handle_container_stop(self, container_info: ContainerInfo) -> None:
        """Handle database container stop event.

        Args:
            container_info: Container information
        """
        logger.info("Handling container stop: %s", container_info.name)

        existing_asset = await self.asset_service.find_by_container_id(container_info.id)
        if existing_asset:
            await self.asset_service.update_asset_status(existing_asset.id, "STOPPED")
            await self.event_handler.handle_database_stop(existing_asset, container_info)

    async def handle_container_restart(self, container_info: ContainerInfo) -> None:
        """Handle database container restart event.

        Args:
            container_info: Container information
        """
        logger.info("Handling container restart: %s", container_info.name)

        existing_asset = await self.asset_service.find_by_container_id(container_info.id)
        if existing_asset:
            await self.asset_service.update_asset_status(existing_asset.id, "RUNNING")
            await self.event_handler.handle_database_restart(existing_asset, container_info)

    async def handle_container_discovery(self, container_info: ContainerInfo) -> None:
        """Handle discovery of existing database container.

        Args:
            container_info: Container information
        """
        logger.info("Handling container discovery: %s", container_info.name)

        new_asset_data = await self.create_asset_from_container(container_info)
        asset = await self.asset_service.create_asset(new_asset_data, created_by="container-discovery")

        await self.event_handler.handle_existing_database_discovered(asset, container_info)

    async def create_asset_from_container(self, container_info: ContainerInfo) -> AssetCreate:
        """Create asset data structure from container information.

        Args:
            container_info: Container information

        Returns:
            AssetCreate data for new asset
        """
        # Determine asset type from container image
        asset_type = self.determine_asset_type(container_info.image)

        # Extract connection details
        connection_details = await self.extract_connection_details(container_info)

        return AssetCreate(
            name=f"{container_info.name}_{asset_type.value}",
            asset_type=asset_type,
            unique_identifier=f"container:{container_info.id}",
            location=f"docker://{container_info.name}",
            connection_string=connection_details.get("connection_string"),
            environment=self.determine_environment(container_info),
            security_classification=SecurityClassification.INTERNAL,  # Default, can be updated
            criticality_level=CriticalityLevel.MEDIUM,  # Default, can be updated
            discovery_method="container_monitoring",
            confidence_score=85,  # High confidence for container detection
            database_version=connection_details.get("version"),
            # Additional metadata
            metadata={
                "container_id": container_info.id,
                "container_image": container_info.image,
                "container_labels": container_info.labels,
                "exposed_ports": container_info.ports,
            },
        )

    def determine_asset_type(self, image_name: str) -> AssetType:
        """Determine asset type from container image name.

        Args:
            image_name: Container image name

        Returns:
            AssetType enum value
        """
        image_lower = image_name.lower()

        if "postgres" in image_lower:
            return AssetType.POSTGRESQL
        elif "mysql" in image_lower or "mariadb" in image_lower:
            return AssetType.MYSQL
        elif "sqlite" in image_lower:
            return AssetType.SQLITE
        elif "duckdb" in image_lower:
            return AssetType.DUCKDB
        else:
            return AssetType.OTHER

    def determine_environment(self, container_info: ContainerInfo) -> Environment:
        """Determine environment from container configuration.

        Args:
            container_info: Container information

        Returns:
            Environment enum value
        """
        # Check labels first
        env_label = container_info.labels.get("environment", "").lower()
        if env_label == "production":
            return Environment.PRODUCTION
        elif env_label == "staging":
            return Environment.STAGING
        elif env_label == "testing":
            return Environment.TESTING

        # Check environment variables
        env_vars = container_info.environment
        if env_vars.get("ENV", "").lower() == "production":
            return Environment.PRODUCTION
        elif env_vars.get("ENVIRONMENT", "").lower() == "production":
            return Environment.PRODUCTION

        # Default to development
        return Environment.DEVELOPMENT

    async def extract_connection_details(self, container_info: ContainerInfo) -> Dict[str, Any]:
        """Extract database connection details from container.

        Args:
            container_info: Container information

        Returns:
            Dictionary with connection details
        """
        details = {}
        env_vars = container_info.environment

        # PostgreSQL
        if "postgres" in container_info.image.lower():
            db_name = env_vars.get("POSTGRES_DB", "postgres")
            user = env_vars.get("POSTGRES_USER", "postgres")
            port = self.extract_port(container_info.ports, 5432)
            host = "localhost"  # Assuming local Docker

            details["connection_string"] = f"postgresql://{user}:***@{host}:{port}/{db_name}"
            details["version"] = self.extract_version_from_image(container_info.image)

        # MySQL
        elif "mysql" in container_info.image.lower() or "mariadb" in container_info.image.lower():
            db_name = env_vars.get("MYSQL_DATABASE", "mysql")
            user = env_vars.get("MYSQL_USER", "root")
            port = self.extract_port(container_info.ports, 3306)
            host = "localhost"

            details["connection_string"] = f"mysql://{user}:***@{host}:{port}/{db_name}"
            details["version"] = self.extract_version_from_image(container_info.image)

        return details

    def extract_port(self, ports_config: Dict[str, Any], default_port: int) -> int:
        """Extract exposed port from container configuration.

        Args:
            ports_config: Container ports configuration
            default_port: Default port if not found

        Returns:
            Exposed port number
        """
        port_key = f"{default_port}/tcp"
        if port_key in ports_config and ports_config[port_key]:
            host_port = ports_config[port_key][0].get("HostPort")
            if host_port:
                return int(host_port)
        return default_port

    def extract_version_from_image(self, image_name: str) -> Optional[str]:
        """Extract version from container image name.

        Args:
            image_name: Container image name

        Returns:
            Version string if found
        """
        if ":" in image_name:
            parts = image_name.split(":")
            if len(parts) == 2:
                tag = parts[1]
                if tag != "latest":
                    return tag
        return None


class ContainerEventHandler:
    """Handler for container lifecycle events."""

    def __init__(
        self,
        notification_service: NotificationService,
        asset_service: AssetService,
    ) -> None:
        """Initialize the container event handler.

        Args:
            notification_service: Service for sending notifications
            asset_service: Service for asset management operations
        """
        self.notification_service = notification_service
        self.asset_service = asset_service

    async def handle_new_database_detected(self, asset: AssetResponse, container_info: ContainerInfo) -> None:
        """Handle detection of new database service.

        Args:
            asset: Created asset response
            container_info: Container information
        """
        logger.info("New database service detected: %s", asset.name)

        # Send notification
        await self.notification_service.send_notification(
            channel=NotificationChannel.SLACK_MONITORING,
            subject="New Database Service Detected",
            message=f"New database container detected: {asset.name}\n"
            f"Type: {asset.asset_type.value}\n"
            f"Container: {container_info.name}\n"
            f"Image: {container_info.image}\n"
            f"Status: {container_info.status}",
            priority="MEDIUM",
            metadata={
                "asset_id": str(asset.id),
                "container_id": container_info.id,
                "detection_method": "container_monitoring",
            },
        )

        # Trigger comprehensive discovery
        await self.trigger_asset_discovery(asset)

    async def handle_existing_database_discovered(self, asset: AssetResponse, container_info: ContainerInfo) -> None:
        """Handle discovery of existing database service.

        Args:
            asset: Created asset response
            container_info: Container information
        """
        logger.info("Existing database service discovered: %s", asset.name)

        # Send notification for audit trail
        await self.notification_service.send_notification(
            channel=NotificationChannel.SLACK_MONITORING,
            subject="Database Service Registered",
            message=f"Existing database container registered: {asset.name}\n"
            f"Type: {asset.asset_type.value}\n"
            f"Container: {container_info.name}\n"
            f"Image: {container_info.image}",
            priority="LOW",
            metadata={
                "asset_id": str(asset.id),
                "container_id": container_info.id,
                "detection_method": "container_discovery",
            },
        )

    async def handle_database_restart(self, asset: AssetResponse, container_info: ContainerInfo) -> None:
        """Handle database service restart.

        Args:
            asset: Asset response
            container_info: Container information
        """
        logger.info("Database service restarted: %s", asset.name)

        # Check if restart was expected
        restart_info = await self.check_planned_restart(asset.id)

        if not restart_info:
            # Unplanned restart - send alert
            await self.notification_service.send_alert(
                severity=AlertSeverity.MEDIUM,
                title="Unplanned Database Restart",
                message=f"Database {asset.name} restarted unexpectedly\n"
                f"Container: {container_info.name}\n"
                f"Restart time: {datetime.now(timezone.utc).isoformat()}",
                affected_assets=[asset.id],
            )

        # Update asset metadata with restart information
        restart_metadata = {
            "last_restart": datetime.now(timezone.utc).isoformat(),
            "restart_count": (asset.metadata.get("restart_count", 0) + 1),
            "restart_planned": restart_info is not None,
        }

        await self.asset_service.update_asset_metadata(asset.id, restart_metadata)

    async def handle_database_stop(self, asset: AssetResponse, container_info: ContainerInfo) -> None:
        """Handle database service stop.

        Args:
            asset: Asset response
            container_info: Container information
        """
        logger.info("Database service stopped: %s", asset.name)

        # Check if stop was expected
        stop_info = await self.check_planned_stop(asset.id)

        if not stop_info:
            # Unplanned stop - send alert
            await self.notification_service.send_alert(
                severity=AlertSeverity.HIGH,
                title="Unplanned Database Stop",
                message=f"Database {asset.name} stopped unexpectedly\n"
                f"Container: {container_info.name}\n"
                f"Stop time: {datetime.now(timezone.utc).isoformat()}",
                affected_assets=[asset.id],
            )

        # Update asset status and metadata
        stop_metadata = {
            "last_stop": datetime.now(timezone.utc).isoformat(),
            "stop_planned": stop_info is not None,
        }

        await self.asset_service.update_asset_metadata(asset.id, stop_metadata)

    async def trigger_asset_discovery(self, asset: AssetResponse) -> None:
        """Trigger comprehensive asset discovery.

        Args:
            asset: Asset to discover
        """
        logger.info("Triggering comprehensive discovery for asset: %s", asset.name)

        # This would trigger the discovery service to perform
        # detailed analysis of the new database asset
        # Implementation would depend on the discovery service integration

    async def check_planned_restart(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Check if a restart was planned.

        Args:
            asset_id: Asset ID to check

        Returns:
            Restart information if planned, None otherwise
        """
        # This would check a maintenance schedule or planned operations
        # For now, return None (all restarts are unplanned)
        return None

    async def check_planned_stop(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """Check if a stop was planned.

        Args:
            asset_id: Asset ID to check

        Returns:
            Stop information if planned, None otherwise
        """
        # This would check a maintenance schedule or planned operations
        # For now, return None (all stops are unplanned)
        return None


class NetworkMonitor:
    """Service for monitoring network endpoints and connectivity."""

    def __init__(self, port_scanner: Any, ssl_checker: Any) -> None:  # noqa: ANN401
        """Initialize the network monitor.

        Args:
            port_scanner: Service for port scanning
            ssl_checker: Service for SSL certificate checking
        """
        self.port_scanner = port_scanner
        self.ssl_checker = ssl_checker
        self.monitored_endpoints: Dict[str, EndpointStatus] = {}

    async def monitor_database_endpoints(self, asset_service: AssetService) -> None:
        """Monitor database network endpoints continuously.

        Args:
            asset_service: Service for asset management
        """
        logger.info("Starting database endpoint monitoring")

        # Get all database assets with network endpoints
        database_assets = await asset_service.get_assets_with_network_endpoints()

        for asset in database_assets:
            try:
                endpoint_status = await self.check_endpoint_status(asset)

                # Compare with previous status
                previous_status = self.monitored_endpoints.get(str(asset.id))

                if previous_status and endpoint_status.accessible != previous_status.accessible:
                    await self.handle_endpoint_status_change(asset, previous_status, endpoint_status)

                # Update monitoring cache
                self.monitored_endpoints[str(asset.id)] = endpoint_status

            except Exception as e:
                logger.error("Error monitoring endpoint for asset %s: %s", asset.id, e)

    async def check_endpoint_status(self, asset: Any) -> EndpointStatus:  # noqa: ANN401
        """Check network endpoint status for database asset.

        Args:
            asset: Database asset to check

        Returns:
            EndpointStatus with current status information
        """
        endpoint_info = self.extract_endpoint_info(asset)

        # Port connectivity check
        port_accessible = await self.port_scanner.check_port(endpoint_info["host"], endpoint_info["port"], timeout=5)

        # SSL/TLS check (if applicable)
        ssl_status = None
        if endpoint_info.get("uses_ssl"):
            ssl_status = await self.ssl_checker.check_certificate(endpoint_info["host"], endpoint_info["port"])

        # Service banner check
        service_banner = await self.get_service_banner(endpoint_info)

        return EndpointStatus(
            asset_id=asset.id,
            host=endpoint_info["host"],
            port=endpoint_info["port"],
            accessible=port_accessible,
            ssl_status=ssl_status,
            service_banner=service_banner,
            response_time_ms=endpoint_info.get("response_time"),
            last_check=datetime.now(timezone.utc),
        )

    def extract_endpoint_info(self, asset: Any) -> Dict[str, Any]:  # noqa: ANN401
        """Extract endpoint information from asset.

        Args:
            asset: Database asset

        Returns:
            Dictionary with endpoint information
        """
        # Parse connection string to extract host/port
        connection_string = asset.connection_string or ""

        # Default values
        endpoint_info = {
            "host": "localhost",
            "port": 5432,
            "uses_ssl": False,
            "response_time": None,
        }

        # Parse PostgreSQL connection string
        if "postgresql://" in connection_string:
            # Extract host and port from postgresql://user:pass@host:port/db
            import re

            match = re.search(r"@([^:]+):(\d+)/", connection_string)
            if match:
                endpoint_info["host"] = match.group(1)
                endpoint_info["port"] = int(match.group(2))

            endpoint_info["uses_ssl"] = "sslmode=require" in connection_string

        # Parse MySQL connection string
        elif "mysql://" in connection_string:
            import re

            match = re.search(r"@([^:]+):(\d+)/", connection_string)
            if match:
                endpoint_info["host"] = match.group(1)
                endpoint_info["port"] = int(match.group(2))

        return endpoint_info

    async def get_service_banner(self, endpoint_info: Dict[str, Any]) -> Optional[str]:
        """Get service banner from endpoint.

        Args:
            endpoint_info: Endpoint information

        Returns:
            Service banner string if available
        """
        # This would attempt to connect and get the service banner
        # For now, return a placeholder
        return f"Database service on {endpoint_info['host']}:{endpoint_info['port']}"

    async def handle_endpoint_status_change(
        self, asset: Any, previous_status: EndpointStatus, current_status: EndpointStatus  # noqa: ANN401
    ) -> None:
        """Handle endpoint status changes.

        Args:
            asset: Database asset
            previous_status: Previous endpoint status
            current_status: Current endpoint status
        """
        logger.info(
            "Endpoint status changed for %s: %s -> %s",
            asset.name,
            previous_status.accessible,
            current_status.accessible,
        )

        await self.send_connectivity_alert(asset, previous_status, current_status)

    async def send_connectivity_alert(
        self, asset: Any, previous_status: EndpointStatus, current_status: EndpointStatus  # noqa: ANN401
    ) -> None:
        """Send connectivity change alert.

        Args:
            asset: Database asset
            previous_status: Previous endpoint status
            current_status: Current endpoint status
        """
        if not current_status.accessible and previous_status.accessible:
            # Connection lost
            logger.warning("Database connectivity lost for %s", asset.name)
            # Send alert via notification service
        elif current_status.accessible and not previous_status.accessible:
            # Connection restored
            logger.info("Database connectivity restored for %s", asset.name)
            # Send restoration notification
