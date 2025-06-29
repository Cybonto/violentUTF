"""
Test Configuration for ViolentUTF MCP Tests
============================================

This file configures the test environment for MCP integration tests.
It sets up proper mocking and environment configuration to test the
actual implementation without external dependencies.
"""

import asyncio
import os
import sys
from typing import Any, Dict, Generator
from unittest.mock import Mock, patch

import pytest

# Add the app directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_environment():
    """Mock environment variables for testing"""
    test_env = {
        # Basic MCP configuration
        "MCP_SERVER_NAME": "ViolentUTF-MCP-Test",
        "MCP_SERVER_VERSION": "1.0.0-test",
        "MCP_ENABLE_TOOLS": "true",
        "MCP_ENABLE_RESOURCES": "true",
        "MCP_TRANSPORT_TYPE": "sse",
        "MCP_SSE_ENDPOINT": "/mcp/sse",
        # Development/test settings
        "MCP_DEVELOPMENT_MODE": "true",
        "MCP_DEBUG_MODE": "true",
        "MCP_REQUIRE_AUTH": "false",
        "MCP_LOG_LEVEL": "DEBUG",
        # API configuration
        "VIOLENTUTF_API_URL": "http://violentutf-api:8000",
        "APISIX_BASE_URL": "http://apisix-apisix-1:9080",
        # Authentication (test values)
        "JWT_SECRET_KEY": "test_secret_key_for_mcp_testing_only",
        "ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        # Keycloak (test values)
        "KEYCLOAK_URL": "http://keycloak:8080",
        "KEYCLOAK_REALM": "ViolentUTF",
        "KEYCLOAK_CLIENT_ID": "violentutf-fastapi",
        "KEYCLOAK_CLIENT_SECRET": "test_client_secret",
        # Override data directories to prevent file system issues
        "APP_DATA_DIR": "/tmp/test_app_data",
        "CONFIG_DIR": "/tmp/test_config",
        # Database (use in-memory for tests)
        "DATABASE_URL": "sqlite:///:memory:",
        # Performance settings for tests
        "MCP_TOOL_TIMEOUT_SECONDS": "30",
        "MCP_CONCURRENT_TOOL_LIMIT": "5",
        "MCP_RESOURCE_CACHE_TTL": "60",
        "MCP_RESOURCE_CACHE_SIZE": "100",
    }

    with patch.dict(os.environ, test_env):
        yield test_env


@pytest.fixture
def mock_settings():
    """Mock settings with test-appropriate values"""
    settings_mock = Mock()
    settings_mock.VIOLENTUTF_API_URL = "http://violentutf-api:8000"
    settings_mock.JWT_SECRET_KEY = "test_secret_key"
    settings_mock.ALGORITHM = "HS256"
    settings_mock.ACCESS_TOKEN_EXPIRE_MINUTES = 30

    with patch("app.core.config.settings", settings_mock):
        yield settings_mock


@pytest.fixture
def disable_external_requests():
    """Disable all external HTTP requests during tests"""

    def mock_request(*args, **kwargs):
        raise Exception("External HTTP requests not allowed in tests. Use proper mocks.")

    with patch("httpx.request", side_effect=mock_request):
        with patch("httpx.get", side_effect=mock_request):
            with patch("httpx.post", side_effect=mock_request):
                with patch("httpx.put", side_effect=mock_request):
                    with patch("httpx.delete", side_effect=mock_request):
                        yield


@pytest.fixture
def clean_registries():
    """Clean tool and resource registries before each test"""
    # Import after environment is set up
    try:
        from app.mcp.resources import resource_registry
        from app.mcp.tools import tool_registry

        # Clear registries
        tool_registry.clear_tools()
        resource_registry.clear_cache()

        yield

        # Clean up after test
        tool_registry.clear_tools()
        resource_registry.clear_cache()
    except ImportError:
        # If imports fail, just yield (test will handle it)
        yield


@pytest.fixture
def mock_mcp_types():
    """Ensure MCP types are available for testing"""
    try:
        from mcp.types import Resource, ServerCapabilities, Tool

        return {"Tool": Tool, "Resource": Resource, "ServerCapabilities": ServerCapabilities}
    except ImportError:
        # Create mock types if MCP library not available
        Tool = Mock
        Tool.__name__ = "Tool"
        Resource = Mock
        Resource.__name__ = "Resource"
        ServerCapabilities = Mock
        ServerCapabilities.__name__ = "ServerCapabilities"

        return {"Tool": Tool, "Resource": Resource, "ServerCapabilities": ServerCapabilities}


@pytest.fixture
def sample_fastapi_routes():
    """Sample FastAPI routes for testing introspection"""
    from unittest.mock import Mock

    from fastapi.routing import APIRoute

    routes = []

    # Create sample routes that match ViolentUTF API structure
    route_definitions = [
        ("/api/v1/generators", ["GET", "POST"], ["generators"]),
        ("/api/v1/generators/{generator_id}", ["GET", "PUT", "DELETE"], ["generators"]),
        ("/api/v1/orchestrators", ["GET", "POST"], ["orchestrators"]),
        ("/api/v1/orchestrators/{orchestrator_id}", ["GET", "PUT", "DELETE"], ["orchestrators"]),
        ("/api/v1/datasets", ["GET", "POST"], ["datasets"]),
        ("/api/v1/config", ["GET"], ["config"]),
        ("/health", ["GET"], ["health"]),  # Should be filtered out
        ("/docs", ["GET"], ["docs"]),  # Should be filtered out
    ]

    for path, methods, tags in route_definitions:
        for method in methods:
            route = Mock(spec=APIRoute)
            route.path = path
            route.methods = {method}
            route.tags = tags
            route.endpoint = Mock()
            route.endpoint.__name__ = (
                f"endpoint_{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
            )
            routes.append(route)

    return routes


@pytest.fixture
def mock_api_responses():
    """Mock API responses for different endpoints"""
    return {
        "generators": {
            "generators": [
                {
                    "id": "test_gen_001",
                    "name": "Test Generator 1",
                    "provider_type": "openai",
                    "model_name": "gpt-4",
                    "status": "active",
                    "created_at": "2024-01-15T10:00:00Z",
                },
                {
                    "id": "test_gen_002",
                    "name": "Test Generator 2",
                    "provider_type": "anthropic",
                    "model_name": "claude-3-sonnet",
                    "status": "active",
                    "created_at": "2024-01-15T11:00:00Z",
                },
            ],
            "total": 2,
        },
        "orchestrators": {
            "orchestrators": [
                {
                    "id": "test_orch_001",
                    "name": "Test Orchestrator 1",
                    "orchestrator_type": "red_teaming",
                    "status": "completed",
                    "created_at": "2024-01-15T09:00:00Z",
                    "completed_at": "2024-01-15T10:30:00Z",
                }
            ],
            "total": 1,
        },
        "datasets": {
            "datasets": [
                {
                    "name": "test_dataset",
                    "category": "harmful_behaviors",
                    "size": 150,
                    "created_at": "2024-01-10T08:00:00Z",
                }
            ],
            "total": 1,
        },
        "config": {
            "version": "1.0.0",
            "environment": "test",
            "features": {"mcp_enabled": True, "tools_enabled": True, "resources_enabled": True},
        },
        "sessions": {
            "sessions": [
                {
                    "id": "test_session_001",
                    "user_id": "test_user",
                    "created_at": "2024-01-15T08:00:00Z",
                    "status": "active",
                }
            ],
            "total": 1,
        },
    }


# Test markers
pytest_markers = [
    "asyncio: marks tests as async",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "slow: marks tests as slow running",
    "external: marks tests that require external services",
]


def pytest_configure(config):
    """Configure pytest with custom markers"""
    for marker in pytest_markers:
        config.addinivalue_line("markers", marker)


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)

        # Mark integration tests based on file name
        if "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)

        # Mark unit tests
        if "test_unit" in item.fspath.basename or "unit" in item.name:
            item.add_marker(pytest.mark.unit)
