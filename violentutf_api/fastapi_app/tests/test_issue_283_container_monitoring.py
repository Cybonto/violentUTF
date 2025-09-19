# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""Test Suite for Issue #283 Container Lifecycle Monitoring.

This module contains comprehensive tests for the container lifecycle monitoring
system that detects database services and monitors their lifecycle events.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import schemas that we know exist
from app.schemas.monitoring_schemas import ContainerInfo, EndpointStatus

# Import the actual container monitoring service classes
from app.services.monitoring.container_monitor import (
    ContainerEventHandler,
    ContainerLifecycleMonitor,
    NetworkMonitor,
)

# Mock the notification enums
class AlertSeverity:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class NotificationChannel:
    SLACK_MONITORING = "SLACK_MONITORING"
    SLACK_CRITICAL = "SLACK_CRITICAL"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"
    SMS = "SMS"

# Mock asset schemas
class AssetCreate:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class AssetResponse:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        # Ensure id exists
        if not hasattr(self, 'id'):
            self.id = uuid.uuid4()
        # Mock metadata as dict
        if not hasattr(self, 'metadata'):
            self.metadata = {}


class TestContainerInfo:
    """Test ContainerInfo data structure."""

    def test_container_info_creation(self):
        """Test ContainerInfo creation with all fields."""
        container_info = ContainerInfo(
            id="test-container-id",
            name="test-postgres",
            image="postgres:13",
            status="running",
            ports={"5432/tcp": [{"HostPort": "5432"}]},
            environment={"POSTGRES_DB": "testdb"},
            labels={"service.type": "database"},
            created=datetime.now(timezone.utc),
        )

        assert container_info.id == "test-container-id"
        assert container_info.name == "test-postgres"
        assert container_info.image == "postgres:13"
        assert container_info.status == "running"
        assert "5432/tcp" in container_info.ports
        assert container_info.environment["POSTGRES_DB"] == "testdb"

    def test_container_info_serialization(self):
        """Test ContainerInfo JSON serialization."""
        container_info = ContainerInfo(
            id="test-id",
            name="test-container",
            image="postgres:13",
            status="running",
            ports={},
            environment={},
            labels={},
            created=datetime.now(timezone.utc),
        )

        # Should be able to convert to dict
        info_dict = container_info.__dict__
        assert info_dict["id"] == "test-id"
        assert info_dict["name"] == "test-container"


class TestContainerLifecycleMonitor:
    """Test ContainerLifecycleMonitor functionality."""

    @pytest.fixture
    def mock_docker_client(self):
        """Mock Docker client for testing."""
        client = Mock()
        client.events = Mock()
        client.containers = Mock()
        return client

    @pytest.fixture
    def mock_event_handler(self):
        """Mock event handler for testing."""
        return AsyncMock(spec=ContainerEventHandler)

    @pytest.fixture
    def mock_asset_service(self):
        """Mock asset service for testing."""
        service = AsyncMock()
        service.find_by_container_id = AsyncMock(return_value=None)
        service.create_asset = AsyncMock()
        service.update_asset_status = AsyncMock()
        return service

    @pytest.fixture
    def container_monitor(self, mock_docker_client, mock_event_handler, mock_asset_service):
        """Create ContainerLifecycleMonitor instance for testing."""
        return ContainerLifecycleMonitor(
            docker_client=mock_docker_client,
            event_handler=mock_event_handler,
            asset_service=mock_asset_service,
        )

    @pytest.mark.asyncio
    async def test_container_monitor_initialization(self, container_monitor):
        """Test ContainerLifecycleMonitor initialization."""
        assert container_monitor.monitoring_active is False
        assert container_monitor.monitored_containers == {}
        assert container_monitor.docker_client is not None
        assert container_monitor.event_handler is not None
        assert container_monitor.asset_service is not None

    @pytest.mark.asyncio
    async def test_is_database_container_postgres(self, container_monitor):
        """Test database container detection for PostgreSQL."""
        # Mock container with PostgreSQL image
        mock_container = Mock()
        mock_container.image.tags = ["postgres:13"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"5432/tcp": [{"HostPort": "5432"}]}},
            "Config": {"Env": ["POSTGRES_DB=testdb", "POSTGRES_USER=test"]},
        }
        mock_container.labels = {}

        result = await container_monitor.is_database_container(mock_container)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_database_container_mysql(self, container_monitor):
        """Test database container detection for MySQL."""
        mock_container = Mock()
        mock_container.image.tags = ["mysql:8.0"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"3306/tcp": [{"HostPort": "3306"}]}},
            "Config": {"Env": ["MYSQL_DATABASE=testdb", "MYSQL_USER=test"]},
        }
        mock_container.labels = {}

        result = await container_monitor.is_database_container(mock_container)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_database_container_by_port(self, container_monitor):
        """Test database container detection by port configuration."""
        mock_container = Mock()
        mock_container.image.tags = ["custom-db:latest"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"5432/tcp": [{"HostPort": "5432"}]}},
            "Config": {"Env": []},
        }
        mock_container.labels = {}

        result = await container_monitor.is_database_container(mock_container)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_database_container_by_environment(self, container_monitor):
        """Test database container detection by environment variables."""
        mock_container = Mock()
        mock_container.image.tags = ["custom-app:latest"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {}},
            "Config": {"Env": ["POSTGRES_DB=testdb", "APP_ENV=production"]},
        }
        mock_container.labels = {}

        result = await container_monitor.is_database_container(mock_container)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_database_container_by_label(self, container_monitor):
        """Test database container detection by labels."""
        mock_container = Mock()
        mock_container.image.tags = ["custom-service:latest"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {}},
            "Config": {"Env": []},
        }
        mock_container.labels = {"service.type": "database"}

        result = await container_monitor.is_database_container(mock_container)
        assert result is True

    @pytest.mark.asyncio
    async def test_is_not_database_container(self, container_monitor):
        """Test non-database container rejection."""
        mock_container = Mock()
        mock_container.image.tags = ["nginx:latest"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"80/tcp": [{"HostPort": "80"}]}},
            "Config": {"Env": ["NGINX_HOST=localhost"]},
        }
        mock_container.labels = {"service.type": "web"}

        result = await container_monitor.is_database_container(mock_container)
        assert result is False

    @pytest.mark.asyncio
    async def test_extract_container_info(self, container_monitor):
        """Test container information extraction."""
        # Mock container object
        mock_container = Mock()
        mock_container.id = "container-123"
        mock_container.name = "test-postgres"
        mock_container.image.tags = ["postgres:13"]
        mock_container.status = "running"
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"5432/tcp": [{"HostPort": "5432"}]}},
            "Config": {
                "Env": ["POSTGRES_DB=testdb", "POSTGRES_USER=test"],
                "ExposedPorts": {"5432/tcp": {}},
            },
            "Created": "2023-01-01T00:00:00.000000000Z",
        }
        mock_container.labels = {"service.type": "database"}

        container_info = await container_monitor.extract_container_info(mock_container)

        assert container_info.id == "container-123"
        assert container_info.name == "test-postgres"
        assert container_info.image == "postgres:13"
        assert container_info.status == "running"
        assert "5432/tcp" in container_info.ports
        assert container_info.environment["POSTGRES_DB"] == "testdb"

    @pytest.mark.asyncio
    async def test_process_container_start_event_new_service(self, container_monitor, mock_asset_service):
        """Test processing container start event for new database service."""
        # Mock container start event
        event = {
            "id": "container-123",
            "Action": "start",
            "Type": "container",
            "from": "postgres:13",
        }

        # Mock container object
        mock_container = Mock()
        mock_container.id = "container-123"
        mock_container.name = "test-postgres"
        mock_container.image.tags = ["postgres:13"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"5432/tcp": [{"HostPort": "5432"}]}},
            "Config": {"Env": ["POSTGRES_DB=testdb"]},
        }
        mock_container.labels = {}

        # Configure mocks
        container_monitor.docker_client.containers.get.return_value = mock_container
        mock_asset_service.find_by_container_id.return_value = None  # New service

        with patch.object(container_monitor, "is_database_container", return_value=True):
            with patch.object(container_monitor, "extract_container_info") as mock_extract:
                mock_extract.return_value = ContainerInfo(
                    id="container-123",
                    name="test-postgres",
                    image="postgres:13",
                    status="running",
                    ports={"5432/tcp": [{"HostPort": "5432"}]},
                    environment={"POSTGRES_DB": "testdb"},
                    labels={},
                    created=datetime.now(timezone.utc),
                )

                with patch.object(container_monitor, "handle_container_start") as mock_handle:
                    await container_monitor.process_container_event(event)

                    mock_handle.assert_called_once()
                    container_info = mock_handle.call_args[0][0]
                    assert container_info.id == "container-123"
                    assert container_info.name == "test-postgres"

    @pytest.mark.asyncio
    async def test_process_container_stop_event(self, container_monitor):
        """Test processing container stop event."""
        event = {
            "id": "container-123",
            "Action": "stop",
            "Type": "container",
            "from": "postgres:13",
        }

        mock_container = Mock()
        mock_container.id = "container-123"
        mock_container.name = "test-postgres"
        mock_container.image.tags = ["postgres:13"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"5432/tcp": [{"HostPort": "5432"}]}},
            "Config": {"Env": ["POSTGRES_DB=testdb"]},
        }
        mock_container.labels = {}

        container_monitor.docker_client.containers.get.return_value = mock_container

        with patch.object(container_monitor, "is_database_container", return_value=True):
            with patch.object(container_monitor, "extract_container_info") as mock_extract:
                mock_extract.return_value = ContainerInfo(
                    id="container-123",
                    name="test-postgres",
                    image="postgres:13",
                    status="exited",
                    ports={"5432/tcp": [{"HostPort": "5432"}]},
                    environment={"POSTGRES_DB": "testdb"},
                    labels={},
                    created=datetime.now(timezone.utc),
                )

                with patch.object(container_monitor, "handle_container_stop") as mock_handle:
                    await container_monitor.process_container_event(event)

                    mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_container_restart_event(self, container_monitor):
        """Test processing container restart event."""
        event = {
            "id": "container-123",
            "Action": "restart",
            "Type": "container",
            "from": "postgres:13",
        }

        mock_container = Mock()
        mock_container.id = "container-123"
        mock_container.image.tags = ["postgres:13"]
        mock_container.attrs = {
            "NetworkSettings": {"Ports": {"5432/tcp": [{"HostPort": "5432"}]}},
            "Config": {"Env": ["POSTGRES_DB=testdb"]},
        }

        container_monitor.docker_client.containers.get.return_value = mock_container

        with patch.object(container_monitor, "is_database_container", return_value=True):
            with patch.object(container_monitor, "extract_container_info") as mock_extract:
                mock_extract.return_value = ContainerInfo(
                    id="container-123",
                    name="test-postgres",
                    image="postgres:13",
                    status="running",
                    ports={"5432/tcp": [{"HostPort": "5432"}]},
                    environment={"POSTGRES_DB": "testdb"},
                    labels={},
                    created=datetime.now(timezone.utc),
                )

                with patch.object(container_monitor, "handle_container_restart") as mock_handle:
                    await container_monitor.process_container_event(event)

                    mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_container_start_new_asset_creation(self, container_monitor, mock_asset_service):
        """Test handling container start with new asset creation."""
        container_info = ContainerInfo(
            id="container-123",
            name="test-postgres",
            image="postgres:13",
            status="running",
            ports={"5432/tcp": [{"HostPort": "5432"}]},
            environment={"POSTGRES_DB": "testdb"},
            labels={},
            created=datetime.now(timezone.utc),
        )

        # Mock no existing asset
        mock_asset_service.find_by_container_id.return_value = None
        mock_asset_service.create_asset.return_value = AssetResponse(
            id=uuid.uuid4(),
            name="test-postgres_PostgreSQL",
            asset_type="POSTGRESQL",
            unique_identifier="container:container-123",
            location="docker://test-postgres",
            discovery_timestamp=datetime.now(timezone.utc),
            created_by="container-monitor",
        )

        with patch.object(container_monitor, "create_asset_from_container") as mock_create:
            mock_create.return_value = AssetCreate(
                name="test-postgres_PostgreSQL",
                asset_type="POSTGRESQL",
                unique_identifier="container:container-123",
                location="docker://test-postgres",
                connection_string="postgresql://localhost:5432/testdb",
                discovery_method="container_monitoring",
                confidence_score=85,
            )

            await container_monitor.handle_container_start(container_info)

            mock_asset_service.find_by_container_id.assert_called_once_with("container-123")
            mock_create.assert_called_once_with(container_info)
            mock_asset_service.create_asset.assert_called_once()
            container_monitor.event_handler.handle_new_database_detected.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_container_start_existing_asset_restart(self, container_monitor, mock_asset_service):
        """Test handling container start for existing asset restart."""
        container_info = ContainerInfo(
            id="container-123",
            name="test-postgres",
            image="postgres:13",
            status="running",
            ports={"5432/tcp": [{"HostPort": "5432"}]},
            environment={"POSTGRES_DB": "testdb"},
            labels={},
            created=datetime.now(timezone.utc),
        )

        # Mock existing asset
        existing_asset = Mock()
        existing_asset.id = uuid.uuid4()
        mock_asset_service.find_by_container_id.return_value = existing_asset

        await container_monitor.handle_container_start(container_info)

        mock_asset_service.find_by_container_id.assert_called_once_with("container-123")
        mock_asset_service.update_asset_status.assert_called_once_with(existing_asset.id, "RUNNING")
        container_monitor.event_handler.handle_database_restart.assert_called_once_with(
            existing_asset, container_info
        )

    @pytest.mark.asyncio
    async def test_determine_asset_type_postgres(self, container_monitor):
        """Test asset type determination for PostgreSQL."""
        asset_type = container_monitor.determine_asset_type("postgres:13")
        assert asset_type.value == "POSTGRESQL"

    @pytest.mark.asyncio
    async def test_determine_asset_type_mysql(self, container_monitor):
        """Test asset type determination for MySQL."""
        asset_type = container_monitor.determine_asset_type("mysql:8.0")
        assert asset_type.value == "MYSQL"

    @pytest.mark.asyncio
    async def test_determine_asset_type_unknown(self, container_monitor):
        """Test asset type determination for unknown database."""
        asset_type = container_monitor.determine_asset_type("custom-db:latest")
        assert asset_type.value == "OTHER"


class TestContainerEventHandler:
    """Test ContainerEventHandler functionality."""

    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service for testing."""
        service = AsyncMock()
        service.send_notification = AsyncMock()
        service.send_alert = AsyncMock()
        return service

    @pytest.fixture
    def mock_asset_service(self):
        """Mock asset service for testing."""
        service = AsyncMock()
        service.update_asset_metadata = AsyncMock()
        return service

    @pytest.fixture
    def event_handler(self, mock_notification_service, mock_asset_service):
        """Create ContainerEventHandler instance for testing."""
        return ContainerEventHandler(
            notification_service=mock_notification_service,
            asset_service=mock_asset_service,
        )

    @pytest.mark.asyncio
    async def test_handle_new_database_detected(self, event_handler, mock_notification_service):
        """Test handling new database detection."""
        asset = AssetResponse(
            id=uuid.uuid4(),
            name="test-postgres",
            asset_type="POSTGRESQL",
            unique_identifier="container:container-123",
            location="docker://test-postgres",
            discovery_timestamp=datetime.now(timezone.utc),
            created_by="container-monitor",
        )

        container_info = ContainerInfo(
            id="container-123",
            name="test-postgres",
            image="postgres:13",
            status="running",
            ports={"5432/tcp": [{"HostPort": "5432"}]},
            environment={"POSTGRES_DB": "testdb"},
            labels={},
            created=datetime.now(timezone.utc),
        )

        with patch.object(event_handler, "trigger_asset_discovery") as mock_trigger:
            await event_handler.handle_new_database_detected(asset, container_info)

            mock_notification_service.send_notification.assert_called_once()
            call_args = mock_notification_service.send_notification.call_args[1]
            assert call_args["channel"] == NotificationChannel.SLACK_MONITORING
            assert call_args["subject"] == "New Database Service Detected"
            assert "test-postgres" in call_args["message"]
            assert call_args["priority"] == "MEDIUM"

            mock_trigger.assert_called_once_with(asset)

    @pytest.mark.asyncio
    async def test_handle_database_restart_unplanned(self, event_handler, mock_notification_service, mock_asset_service):
        """Test handling unplanned database restart."""
        asset = Mock()
        asset.id = uuid.uuid4()
        asset.name = "test-postgres"
        asset.metadata = {"restart_count": 2}

        container_info = ContainerInfo(
            id="container-123",
            name="test-postgres",
            image="postgres:13",
            status="running",
            ports={"5432/tcp": [{"HostPort": "5432"}]},
            environment={"POSTGRES_DB": "testdb"},
            labels={},
            created=datetime.now(timezone.utc),
        )

        with patch.object(event_handler, "check_planned_restart", return_value=None):
            await event_handler.handle_database_restart(asset, container_info)

            mock_notification_service.send_alert.assert_called_once()
            call_args = mock_notification_service.send_alert.call_args[1]
            assert call_args["severity"] == AlertSeverity.MEDIUM
            assert call_args["title"] == "Unplanned Database Restart"
            assert "test-postgres" in call_args["message"]

            mock_asset_service.update_asset_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_database_restart_planned(self, event_handler, mock_notification_service, mock_asset_service):
        """Test handling planned database restart."""
        asset = Mock()
        asset.id = uuid.uuid4()
        asset.name = "test-postgres"
        asset.metadata = {"restart_count": 1}

        container_info = ContainerInfo(
            id="container-123",
            name="test-postgres",
            image="postgres:13",
            status="running",
            ports={"5432/tcp": [{"HostPort": "5432"}]},
            environment={"POSTGRES_DB": "testdb"},
            labels={},
            created=datetime.now(timezone.utc),
        )

        # Mock planned restart
        restart_info = {"planned": True, "scheduled_time": datetime.now(timezone.utc)}

        with patch.object(event_handler, "check_planned_restart", return_value=restart_info):
            await event_handler.handle_database_restart(asset, container_info)

            # Should not send unplanned restart alert
            mock_notification_service.send_alert.assert_not_called()
            # Should still update metadata
            mock_asset_service.update_asset_metadata.assert_called_once()


class TestNetworkMonitor:
    """Test NetworkMonitor functionality."""

    @pytest.fixture
    def mock_port_scanner(self):
        """Mock port scanner for testing."""
        scanner = AsyncMock()
        scanner.check_port = AsyncMock(return_value=True)
        return scanner

    @pytest.fixture
    def mock_ssl_checker(self):
        """Mock SSL checker for testing."""
        checker = AsyncMock()
        checker.check_certificate = AsyncMock()
        return checker

    @pytest.fixture
    def network_monitor(self, mock_port_scanner, mock_ssl_checker):
        """Create NetworkMonitor instance for testing."""
        return NetworkMonitor(
            port_scanner=mock_port_scanner,
            ssl_checker=mock_ssl_checker,
        )

    @pytest.mark.asyncio
    async def test_check_endpoint_status_accessible(self, network_monitor, mock_port_scanner):
        """Test endpoint status check for accessible endpoint."""
        # Mock asset with endpoint
        asset = Mock()
        asset.id = uuid.uuid4()
        asset.connection_string = "postgresql://localhost:5432/testdb"

        with patch.object(network_monitor, "extract_endpoint_info") as mock_extract:
            mock_endpoint_info = Mock()
            mock_endpoint_info.host = "localhost"
            mock_endpoint_info.port = 5432
            mock_endpoint_info.uses_ssl = False
            mock_endpoint_info.response_time = 50
            mock_extract.return_value = mock_endpoint_info

            with patch.object(network_monitor, "get_service_banner", return_value="PostgreSQL 13"):
                endpoint_status = await network_monitor.check_endpoint_status(asset)

                assert endpoint_status.asset_id == asset.id
                assert endpoint_status.host == "localhost"
                assert endpoint_status.port == 5432
                assert endpoint_status.accessible is True
                assert endpoint_status.service_banner == "PostgreSQL 13"

                mock_port_scanner.check_port.assert_called_once_with("localhost", 5432, timeout=5)

    @pytest.mark.asyncio
    async def test_check_endpoint_status_with_ssl(self, network_monitor, mock_port_scanner, mock_ssl_checker):
        """Test endpoint status check with SSL certificate validation."""
        asset = Mock()
        asset.id = uuid.uuid4()
        asset.connection_string = "postgresql://localhost:5432/testdb?sslmode=require"

        ssl_status = Mock()
        ssl_status.valid = True
        ssl_status.expires_at = datetime.now(timezone.utc)
        mock_ssl_checker.check_certificate.return_value = ssl_status

        with patch.object(network_monitor, "extract_endpoint_info") as mock_extract:
            mock_endpoint_info = Mock()
            mock_endpoint_info.host = "localhost"
            mock_endpoint_info.port = 5432
            mock_endpoint_info.uses_ssl = True
            mock_endpoint_info.response_time = 75
            mock_extract.return_value = mock_endpoint_info

            with patch.object(network_monitor, "get_service_banner", return_value="PostgreSQL 13"):
                endpoint_status = await network_monitor.check_endpoint_status(asset)

                assert endpoint_status.ssl_status == ssl_status
                mock_ssl_checker.check_certificate.assert_called_once_with("localhost", 5432)

    @pytest.mark.asyncio
    async def test_check_endpoint_status_inaccessible(self, network_monitor, mock_port_scanner):
        """Test endpoint status check for inaccessible endpoint."""
        asset = Mock()
        asset.id = uuid.uuid4()
        asset.connection_string = "postgresql://localhost:5432/testdb"

        # Mock port as inaccessible
        mock_port_scanner.check_port.return_value = False

        with patch.object(network_monitor, "extract_endpoint_info") as mock_extract:
            mock_endpoint_info = Mock()
            mock_endpoint_info.host = "localhost"
            mock_endpoint_info.port = 5432
            mock_endpoint_info.uses_ssl = False
            mock_endpoint_info.response_time = None
            mock_extract.return_value = mock_endpoint_info

            with patch.object(network_monitor, "get_service_banner", return_value=None):
                endpoint_status = await network_monitor.check_endpoint_status(asset)

                assert endpoint_status.accessible is False
                assert endpoint_status.service_banner is None

    @pytest.mark.asyncio
    async def test_handle_endpoint_status_change(self, network_monitor):
        """Test handling endpoint status changes."""
        asset = Mock()
        asset.id = uuid.uuid4()
        asset.name = "test-postgres"

        previous_status = Mock()
        previous_status.accessible = True

        current_status = Mock()
        current_status.accessible = False

        with patch.object(network_monitor, "send_connectivity_alert") as mock_alert:
            await network_monitor.handle_endpoint_status_change(asset, previous_status, current_status)

            mock_alert.assert_called_once_with(asset, previous_status, current_status)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])