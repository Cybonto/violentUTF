from typing import Any

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Comprehensive tests for 0_Welcome.py backend API endpoints

"""

import json
import os

# Import the FastAPI app
import sys
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "../violentutf_api/fastapi_app"))

from app.core.auth import get_current_user
from app.models.auth import User
from main import app

client = TestClient(app)


@pytest.fixture
def mock_user() -> Any:
    """Mock user object."""
    return User(username="testuser", email="test@example.com", roles=["ai-api-access"], is_active=True)


@pytest.fixture
def auth_headers() -> Any:
    """Authentication headers for API requests."""
    return {
        "Authorization": "Bearer test_token",
        "X-Real-IP": "127.0.0.1",  # Mock APISIX header
        "X-Forwarded-For": "127.0.0.1",
    }


@pytest.fixture(autouse=True)
def setup_auth_override(mock_user) -> None:
    """Setup authentication override for all tests."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.clear()


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_get_token_info(self: "TestAuthenticationEndpoints", auth_headers: Any) -> None:
        """Test GET /auth/token/info endpoint."""
        response = client.get("/api/v1/auth/token/info", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "ai-api-access" in data["roles"]
        assert data["has_ai_access"] is True
        assert data["token_valid"] is True

    def test_validate_token(self: "TestAuthenticationEndpoints", auth_headers: Any) -> None:
        """Test POST /auth/token/validate endpoint."""
        # Test valid token with AI access.
        payload = {"required_roles": ["ai-api-access"], "check_ai_access": True}

        response = client.post("/api/v1/auth/token/validate", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is True
        assert data["has_ai_access"] is True
        assert data["missing_roles"] == []

    def test_validate_token_missing_role(self: "TestAuthenticationEndpoints", auth_headers: Any) -> None:
        """Test token validation with missing role."""
        payload = {"required_roles": ["admin"], "check_ai_access": True}

        response = client.post("/api/v1/auth/token/validate", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is False
        assert "admin" in data["missing_roles"]

    def test_logout(self: "TestAuthenticationEndpoints", auth_headers: Any) -> None:
        """Test POST /auth/logout endpoint."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "message" in response.json()


class TestDatabaseEndpoints:
    """Test database management endpoints."""

    @patch("os.makedirs")
    @patch("duckdb.connect")
    @patch("os.path.exists")
    def test_initialize_database(
        self: "TestDatabaseEndpoints", mock_exists, mock_duckdb, mock_makedirs, auth_headers: Any
    ) -> None:
        """Test POST /database/initialize endpoint."""
        mock_exists.return_value = False

        # Mock DuckDB connection
        mock_conn = mock_duckdb.return_value.__enter__.return_value
        mock_conn.execute.return_value = None

        payload = {"force_recreate": False, "custom_salt": "test_salt_123", "backup_existing": True}

        response = client.post("/api/v1/database/initialize", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["initialization_status"] == "success"
        assert "database_path" in data
        assert data["path_generation_method"] == "SHA256 salted hash"
        assert data["schema_version"] == "1.0"

    @patch("os.path.exists")
    @patch("os.stat")
    @patch("duckdb.connect")
    def test_get_database_status(
        self: "TestDatabaseEndpoints", mock_duckdb, mock_stat, mock_exists, auth_headers: Any
    ) -> None:
        """Test GET /database/status endpoint."""
        mock_exists.return_value = True

        # Mock file stats
        mock_stat.return_value.st_size = 1024 * 1024  # 1MB
        mock_stat.return_value.st_atime = 1700654921

        # Mock successful DB connection
        mock_conn = mock_duckdb.return_value.__enter__.return_value
        mock_conn.execute.return_value.fetchone.return_value = [1]

        response = client.get("/api/v1/database/status", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["is_initialized"] is True
        assert data["connection_healthy"] is True
        assert data["file_size_mb"] == 1.0

    @patch("os.path.exists")
    @patch("os.stat")
    @patch("duckdb.connect")
    def test_get_database_stats(
        self: "TestDatabaseEndpoints", mock_duckdb, mock_stat, mock_exists, auth_headers: Any
    ) -> None:
        """Test GET /database/stats endpoint."""
        mock_exists.return_value = True

        # Mock file stats
        mock_stat.return_value.st_size = 2 * 1024 * 1024  # 2MB

        # Mock DB queries
        mock_conn = mock_duckdb.return_value.__enter__.return_value
        mock_conn.execute.return_value.fetchone.side_effect = [[10], [5], [3]]

        response = client.get("/api/v1/database/stats", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["total_records"] == 18  # 10 + 5 + 3
        assert data["database_size_mb"] == 2.0
        assert len(data["tables"]) == 3

    @patch("os.path.exists")
    @patch("shutil.copy2")
    @patch("os.getenv")
    def test_reset_database(
        self: "TestDatabaseEndpoints", mock_getenv, mock_shutil, mock_exists, auth_headers: Any
    ) -> None:
        """Test POST /database/reset endpoint."""
        mock_exists.return_value = True
        mock_getenv.side_effect = lambda key, default: {
            "PYRIT_DB_SALT": "test_salt",
            "APP_DATA_DIR": "./app_data/violentutf",
        }.get(key, default)

        payload = {"confirmation": True, "backup_before_reset": True, "preserve_user_data": False}

        response = client.post("/api/v1/database/reset", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert data["task_status"] == "running"

    def test_reset_database_no_confirmation(self: "TestDatabaseEndpoints", auth_headers: Any) -> None:
        """Test database reset without confirmation."""
        payload = {"confirmation": False}

        response = client.post("/api/v1/database/reset", headers=auth_headers, json=payload)
        assert response.status_code == 400


class TestSessionEndpoints:
    """Test session management endpoints."""

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"session_id": "test_session", "user_id": "testuser", "ui_preferences": {}, "workflow_state": {}, "temporary_data": {}, "cache_data": {}, "last_updated": "2024-01-01T00:00:00"}',
    )
    @patch("os.path.exists")
    def test_get_session_state(self: "TestSessionEndpoints", mock_exists, mock_file, auth_headers: Any) -> None:
        """Test GET /sessions endpoint."""
        mock_exists.return_value = True

        response = client.get("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["user_id"] == "testuser"
        assert "session_id" in data
        assert "ui_preferences" in data
        assert "workflow_state" in data

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_update_session_state(
        self: "TestSessionEndpoints", mock_makedirs, mock_exists, mock_file, auth_headers: Any
    ) -> None:
        """Test PUT /sessions endpoint."""
        mock_exists.return_value = True

        # Mock existing session data
        existing_data = {
            "session_id": "test_session",
            "user_id": "testuser",
            "ui_preferences": {"theme": "dark"},
            "workflow_state": {},
            "temporary_data": {},
            "cache_data": {},
            "last_updated": "2024-01-01T00:00:00",
        }
        mock_file.return_value.read.return_value = json.dumps(existing_data)

        payload = {
            "ui_preferences": {"theme": "light", "sidebar_collapsed": True},
            "workflow_state": {"current_step": "database_init"},
        }

        response = client.put("/api/v1/sessions", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["ui_preferences"]["theme"] == "light"
        assert data["ui_preferences"]["sidebar_collapsed"] is True
        assert data["workflow_state"]["current_step"] == "database_init"

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_reset_session_state(self: "TestSessionEndpoints", mock_makedirs, mock_file, auth_headers: Any) -> None:
        """Test POST /sessions/reset endpoint."""
        response = client.post("/api/v1/sessions/reset", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["user_id"] == "testuser"
        assert data["ui_preferences"] == {}
        assert data["workflow_state"] == {}
        assert data["temporary_data"] == {}

    def test_get_session_schema(self: "TestSessionEndpoints") -> None:
        """Test GET /sessions/schema endpoint."""
        response = client.get("/api/v1/sessions/schema")
        assert response.status_code == 200

        data = response.json()
        assert "schema" in data
        assert "version" in data
        assert data["version"] == "1.0"


class TestConfigEndpoints:
    """Test configuration management endpoints."""

    @patch("builtins.open", new_callable=mock_open, read_data='APP_DATA_DIR: ./app_data/violentutf\nversion: "1.0"')
    @patch("os.path.exists")
    @patch("os.path.getmtime")
    def test_get_config_parameters(
        self: "TestConfigEndpoints", mock_getmtime, mock_exists, mock_file, auth_headers: Any
    ) -> None:
        """Test GET /config/parameters endpoint."""
        mock_exists.return_value = True
        mock_getmtime.return_value = 1700654921

        response = client.get("/api/v1/config/parameters", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "parameters" in data
        assert "APP_DATA_DIR" in data["parameters"]
        assert data["validation_status"] == "valid"


class TestEnvironmentConfigEndpoints:
    """Test environment configuration endpoints."""

    @patch.dict(
        os.environ,
        {
            "PYRIT_DB_SALT": "test_salt_12345678",
            "VIOLENTUTF_API_KEY": "test_api_key_12345678",
            "APP_DATA_DIR": "./app_data",
        },
    )
    def test_get_environment_config(self: "TestEnvironmentConfigEndpoints", auth_headers: Any) -> None:
        """Test GET /config/environment endpoint."""
        response = client.get("/api/v1/config/environment", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "environment_variables" in data
        assert "PYRIT_DB_SALT" in data["environment_variables"]
        # Check that sensitive values are masked
        assert data["environment_variables"]["PYRIT_DB_SALT"] == "test_sal..."

    def test_generate_salt(self: "TestEnvironmentConfigEndpoints", auth_headers: Any) -> None:
        """Test POST /config/environment/generate-salt endpoint."""
        response = client.post("/api/v1/config/environment/generate-salt", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "salt" in data
        assert data["length"] == 32
        assert len(data["salt"]) == 32


class TestFileEndpoints:
    """Test file management endpoints."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_upload_file(self: "TestFileEndpoints", mock_makedirs, mock_file, auth_headers: Any) -> None:
        """Test POST /files/upload endpoint."""
        file_content = "test file content"
        files = {"file": ("test.txt", file_content, "text/plain")}

        response = client.post("/api/v1/files/upload", headers=auth_headers, files=files)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "test.txt"
        assert "file_id" in data


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
