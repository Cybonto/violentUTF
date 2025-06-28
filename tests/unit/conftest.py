"""
Base configuration and fixtures for unit tests.
This file provides shared fixtures and configuration for all unit tests.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import the db mock
sys.path.insert(0, str(Path(__file__).parent.parent))

# Comment out deleted imports - tests will use mock modules defined below
# The tests now have properly fixed expectations

import asyncio
import json
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from freezegun import freeze_time

# Load test environment variables BEFORE importing any app modules
test_env_file = Path(__file__).parent.parent / ".env.test"
if test_env_file.exists():
    from dotenv import load_dotenv

    load_dotenv(test_env_file, override=True)

# Create test directories
test_dirs = [
    Path("/tmp/violentutf_test/app_data/violentutf/datasets"),
    Path("/tmp/violentutf_test/app_data/violentutf/parameters"),
    Path("/tmp/violentutf_test/app_data/violentutf/api_memory"),
    Path("/tmp/violentutf_test/config"),
]
for test_dir in test_dirs:
    test_dir.mkdir(parents=True, exist_ok=True)

# Add the FastAPI app directory to Python path
fastapi_app_path = os.path.join(
    os.path.dirname(__file__), "../../violentutf_api/fastapi_app"
)
violentutf_path = os.path.join(os.path.dirname(__file__), "../../violentutf")

# Ensure paths exist and add them
if os.path.exists(fastapi_app_path):
    sys.path.insert(0, fastapi_app_path)
if os.path.exists(violentutf_path):
    sys.path.insert(0, violentutf_path)


# ====================
# Event Loop Configuration
# ====================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ====================
# Environment and Configuration
# ====================


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "JWT_SECRET_KEY": "test-secret-key-for-unit-tests",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRATION_MINUTES": "30",
        "VIOLENTUTF_API_KEY": "test-api-key-12345",
        "KEYCLOAK_URL": "http://mock-keycloak:8080",
        "KEYCLOAK_REALM": "violentutf",
        "KEYCLOAK_CLIENT_ID": "violentutf-client",
        "KEYCLOAK_CLIENT_SECRET": "test-client-secret",
        "APISIX_ADMIN_KEY": "test-admin-key",
        "APISIX_GATEWAY_URL": "http://localhost:9080",
        "DATABASE_URL": "duckdb:///:memory:",
        "REDIS_URL": "redis://localhost:6379/0",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test",
    }

    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def test_config():
    """Test configuration object."""
    return {
        "app_name": "ViolentUTF Test",
        "version": "1.0.0-test",
        "debug": True,
        "testing": True,
        "rate_limit": {"enabled": False, "requests_per_minute": 60},
        "security": {
            "cors_origins": ["http://localhost:3000"],
            "allowed_hosts": ["localhost", "127.0.0.1"],
        },
    }


# ====================
# File System and I/O
# ====================


@pytest.fixture
def isolated_filesystem():
    """Provide isolated filesystem for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        old_cwd = os.getcwd()
        os.chdir(tmpdir)

        # Create common directories
        os.makedirs("app_data/violentutf/datasets", exist_ok=True)
        os.makedirs("app_data/violentutf/parameters", exist_ok=True)
        os.makedirs("app_data/violentutf/api_memory", exist_ok=True)
        os.makedirs("logs", exist_ok=True)

        yield tmpdir
        os.chdir(old_cwd)


# ====================
# Database Fixtures
# ====================


@pytest.fixture
def mock_db_session():
    """Mock database session for SQLAlchemy-style operations."""
    session = Mock()
    session.query = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.flush = Mock()
    session.close = Mock()
    session.execute = Mock()

    # Make query chainable
    query_mock = Mock()
    query_mock.filter = Mock(return_value=query_mock)
    query_mock.filter_by = Mock(return_value=query_mock)
    query_mock.first = Mock(return_value=None)
    query_mock.all = Mock(return_value=[])
    query_mock.count = Mock(return_value=0)
    query_mock.limit = Mock(return_value=query_mock)
    query_mock.offset = Mock(return_value=query_mock)

    session.query.return_value = query_mock

    return session


@pytest.fixture
def mock_duckdb_manager():
    """Mock DuckDB manager for testing."""
    manager = Mock()
    manager.execute = AsyncMock(return_value=[])
    manager.fetch_one = AsyncMock(return_value=None)
    manager.fetch_all = AsyncMock(return_value=[])
    manager.create_table = AsyncMock()
    manager.close = AsyncMock()

    # Add connection context manager
    async def async_context():
        yield manager

    manager.__aenter__ = AsyncMock(return_value=manager)
    manager.__aexit__ = AsyncMock(return_value=None)

    return manager


# ====================
# HTTP and Network
# ====================


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for external API calls."""
    client = AsyncMock()

    # Default response
    response = Mock()
    response.status_code = 200
    response.json = Mock(return_value={"status": "success"})
    response.text = "OK"
    response.headers = {}
    response.raise_for_status = Mock()

    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.put = AsyncMock(return_value=response)
    client.delete = AsyncMock(return_value=response)
    client.patch = AsyncMock(return_value=response)

    return client


@pytest.fixture
def security_headers():
    """Standard security headers for testing."""
    return {
        "X-Request-ID": f"test-{uuid.uuid4()}",
        "X-Forwarded-For": "127.0.0.1",
        "X-Real-IP": "127.0.0.1",
        "User-Agent": "pytest/test-agent",
        "Authorization": "Bearer test-token",
    }


# ====================
# Authentication and JWT
# ====================


@pytest.fixture
def fixed_datetime():
    """Fixed datetime for deterministic tests."""
    with freeze_time("2024-01-01 00:00:00"):
        yield datetime(2024, 1, 1, 0, 0, 0)


@pytest.fixture
def mock_jwt_payload(fixed_datetime):
    """Standard JWT payload for testing."""
    return {
        "sub": "test-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "preferred_username": "testuser",
        "roles": ["user"],
        "exp": int((fixed_datetime + timedelta(hours=1)).timestamp()),
        "iat": int(fixed_datetime.timestamp()),
        "iss": "http://localhost:8080/auth/realms/violentutf",
        "aud": "violentutf-client",
    }


@pytest.fixture
def mock_admin_jwt_payload(mock_jwt_payload):
    """Admin JWT payload for testing."""
    admin_payload = mock_jwt_payload.copy()
    admin_payload.update(
        {
            "sub": "admin-user-456",
            "email": "admin@example.com",
            "name": "Admin User",
            "preferred_username": "admin",
            "roles": ["user", "admin"],
        }
    )
    return admin_payload


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token string."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItMTIzIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwibmFtZSI6IlRlc3QgVXNlciIsImV4cCI6MTcwNDA3MDgwMCwiaWF0IjoxNzA0MDY3MjAwfQ.test-signature"


@pytest.fixture
def mock_keycloak_response():
    """Mock Keycloak token response."""
    return {
        "access_token": "mock-access-token",
        "refresh_token": "mock-refresh-token",
        "expires_in": 3600,
        "refresh_expires_in": 7200,
        "token_type": "Bearer",
        "id_token": "mock-id-token",
        "not_before_policy": 0,
        "session_state": "mock-session-state",
        "scope": "openid email profile",
    }


# ====================
# API Response Fixtures
# ====================


@pytest.fixture
def success_response():
    """Standard success API response."""

    def _response(data: Any = None, message: str = "Success"):
        return {"status": "success", "message": message, "data": data}

    return _response


@pytest.fixture
def error_response():
    """Standard error API response."""

    def _response(message: str = "Error", code: str = "ERROR", status_code: int = 400):
        return {
            "status": "error",
            "message": message,
            "code": code,
            "status_code": status_code,
        }

    return _response


# ====================
# Model and Data Fixtures
# ====================


@pytest.fixture
def sample_generator():
    """Sample generator data for testing."""
    return {
        "id": "gen-" + str(uuid.uuid4()),
        "name": "test-generator",
        "model": "gpt-4",
        "provider": "openai",
        "parameters": {"temperature": 0.7, "max_tokens": 1000, "top_p": 0.9},
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "is_active": True,
    }


@pytest.fixture
def sample_dataset():
    """Sample dataset data for testing."""
    return {
        "id": "dataset-" + str(uuid.uuid4()),
        "name": "test-dataset",
        "description": "Test dataset for unit tests",
        "type": "jailbreak",
        "prompts": [
            {"id": 1, "prompt": "Test prompt 1", "category": "test"},
            {"id": 2, "prompt": "Test prompt 2", "category": "test"},
        ],
        "created_at": datetime.utcnow().isoformat(),
        "size": 2,
    }


@pytest.fixture
def sample_orchestrator_config():
    """Sample orchestrator configuration."""
    return {
        "id": "orch-" + str(uuid.uuid4()),
        "name": "test-orchestrator",
        "type": "red_teaming",
        "target": {"type": "http_target", "url": "http://test-target/api/chat"},
        "generators": ["gen-123"],
        "converters": ["ascii_art", "base64"],
        "scorers": ["self_ask", "substring"],
        "max_iterations": 5,
        "batch_size": 10,
    }


@pytest.fixture
def sample_scorer_config():
    """Sample scorer configuration."""
    return {
        "id": "scorer-" + str(uuid.uuid4()),
        "name": "test-scorer",
        "type": "substring",
        "parameters": {"substring": "test", "case_sensitive": False},
        "threshold": 0.8,
    }


# ====================
# Mock Services
# ====================


@pytest.fixture
def mock_pyrit_orchestrator():
    """Mock PyRIT orchestrator."""
    orchestrator = Mock()
    orchestrator.id = "orch-123"
    orchestrator.run_async = AsyncMock(
        return_value={
            "results": [{"prompt": "test", "response": "response", "score": 0.9}],
            "status": "completed",
        }
    )
    orchestrator.get_memory = Mock(return_value=[])
    orchestrator.dispose_db_engine = Mock()

    return orchestrator


@pytest.fixture
def mock_garak_scanner():
    """Mock Garak scanner."""
    scanner = Mock()
    scanner.scan = AsyncMock(
        return_value={"vulnerabilities": [], "score": 1.0, "status": "safe"}
    )
    return scanner


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server."""
    server = Mock()
    server.tools = {}
    server.resources = {}
    server.prompts = {}
    server.register_tool = Mock()
    server.register_resource = Mock()
    server.handle_request = AsyncMock(return_value={"result": "success"})

    return server


# ====================
# FastAPI Test Client
# ====================


@pytest.fixture
def mock_request():
    """Mock FastAPI request object."""
    request = Mock()
    request.headers = {}
    request.query_params = {}
    request.path_params = {}
    request.cookies = {}
    request.url = Mock()
    request.url.path = "/test"
    request.method = "GET"
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.state = Mock()

    return request


# ====================
# Utility Functions
# ====================


@pytest.fixture
def create_temp_file():
    """Create temporary file for testing."""

    def _create(content: str = "", suffix: str = ".txt") -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name

    return _create


@pytest.fixture
def async_return():
    """Helper to create async return values."""

    def _return(value):
        future = asyncio.Future()
        future.set_result(value)
        return future

    return _return


# ====================
# Cleanup
# ====================


@pytest.fixture(autouse=True)
def cleanup():
    """Automatic cleanup after each test."""
    yield
    # Clean up any temporary files or resources
    import gc

    gc.collect()
