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

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "violentutf_api", "fastapi_app"))

from app.core.auth import get_current_user
from app.models.auth import User
from main import app

client = TestClient(app)

# Mock JWT token for authentication
MOCK_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsInJvbGVzIjpbImFpLWFwaS1hY2Nlc3MiXSwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjE3MDA2NTQ5MjF9.example_signature"


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests"""
    return {
        "Authorization": f"Bearer {MOCK_TOKEN}",
        "X-Real-IP": "127.0.0.1",  # Mock APISIX header
        "X-Forwarded-For": "127.0.0.1",
    }


@pytest.fixture
def mock_user():
    """Mock user object"""
    return User(username="testuser", email="test@example.com", roles=["ai-api-access"], is_active=True)


class TestAuthenticationEndpoints:
    """Test authentication endpoints"""

    def test_get_token_info(self, auth_headers, mock_user):
        """Test GET /auth/token/info endpoint"""
        # Override dependency
        app.dependency_overrides[get_current_user] = lambda: mock_user

        response = client.get("/api/v1/auth/token/info", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "ai-api-access" in data["roles"]
        assert data["has_ai_access"] is True
        assert data["token_valid"] is True

        # Clean up
        app.dependency_overrides.clear()

    @patch("app.core.auth.get_current_user")
    def test_validate_token(self, mock_get_user, auth_headers, mock_user):
        """Test POST /auth/token/validate endpoint"""
        mock_get_user.return_value = mock_user

        # Test valid token with AI access
        payload = {"required_roles": ["ai-api-access"], "check_ai_access": True}

        response = client.post("/api/v1/auth/token/validate", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is True
        assert data["has_ai_access"] is True
        assert data["missing_roles"] == []

    @patch("app.core.auth.get_current_user")
    def test_validate_token_missing_role(self, mock_get_user, auth_headers):
        """Test token validation with missing role"""
        mock_user_no_access = type("MockUser", (), {"username": "testuser", "email": "test@example.com", "roles": []})()
        mock_get_user.return_value = mock_user_no_access

        payload = {"required_roles": ["admin"], "check_ai_access": True}

        response = client.post("/api/v1/auth/token/validate", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["valid"] is False
        assert "admin" in data["missing_roles"]
        assert "ai-api-access" in data["missing_roles"]

    @patch("app.core.auth.get_current_user")
    def test_logout(self, mock_get_user, auth_headers, mock_user):
        """Test POST /auth/logout endpoint"""
        mock_get_user.return_value = mock_user

        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "message" in response.json()


class TestDatabaseEndpoints:
    """Test database management endpoints"""

    @patch("app.core.auth.get_current_user")
    @patch("os.makedirs")
    @patch("duckdb.connect")
    @patch("os.path.exists")
    def test_initialize_database(self, mock_exists, mock_duckdb, mock_makedirs, mock_get_user, auth_headers, mock_user):
        """Test POST /database/initialize endpoint"""
        mock_get_user.return_value = mock_user
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

    @patch("app.core.auth.get_current_user")
    @patch("os.path.exists")
    @patch("os.stat")
    @patch("duckdb.connect")
    def test_get_database_status(self, mock_duckdb, mock_stat, mock_exists, mock_get_user, auth_headers, mock_user):
        """Test GET /database/status endpoint"""
        mock_get_user.return_value = mock_user
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

    @patch("app.core.auth.get_current_user")
    @patch("os.path.exists")
    @patch("os.stat")
    @patch("duckdb.connect")
    def test_get_database_stats(self, mock_duckdb, mock_stat, mock_exists, mock_get_user, auth_headers, mock_user):
        """Test GET /database/stats endpoint"""
        mock_get_user.return_value = mock_user
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

    @patch("app.core.auth.get_current_user")
    @patch("os.path.exists")
    def test_reset_database(self, mock_exists, mock_get_user, auth_headers, mock_user):
        """Test POST /database/reset endpoint"""
        mock_get_user.return_value = mock_user
        mock_exists.return_value = True

        payload = {"confirmation": True, "backup_before_reset": True, "preserve_user_data": False}

        response = client.post("/api/v1/database/reset", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert data["task_status"] == "running"

    def test_reset_database_no_confirmation(self, auth_headers):
        """Test database reset without confirmation"""
        payload = {"confirmation": False}

        response = client.post("/api/v1/database/reset", headers=auth_headers, json=payload)
        assert response.status_code == 400


class TestSessionEndpoints:
    """Test session management endpoints"""

    @patch("app.core.auth.get_current_user")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"session_id": "test_session", "user_id": "testuser", "ui_preferences": {}, "workflow_state": {}, "temporary_data": {}, "cache_data": {}, "last_updated": "2024-01-01T00:00:00"}',
    )
    @patch("os.path.exists")
    def test_get_session_state(self, mock_exists, mock_file, mock_get_user, auth_headers, mock_user):
        """Test GET /sessions endpoint"""
        mock_get_user.return_value = mock_user
        mock_exists.return_value = True

        response = client.get("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["user_id"] == "testuser"
        assert "session_id" in data
        assert "ui_preferences" in data
        assert "workflow_state" in data

    @patch("app.core.auth.get_current_user")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_update_session_state(self, mock_makedirs, mock_exists, mock_file, mock_get_user, auth_headers, mock_user):
        """Test PUT /sessions endpoint"""
        mock_get_user.return_value = mock_user
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

    @patch("app.core.auth.get_current_user")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_reset_session_state(self, mock_makedirs, mock_file, mock_get_user, auth_headers, mock_user):
        """Test POST /sessions/reset endpoint"""
        mock_get_user.return_value = mock_user

        response = client.post("/api/v1/sessions/reset", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["user_id"] == "testuser"
        assert data["ui_preferences"] == {}
        assert data["workflow_state"] == {}
        assert data["temporary_data"] == {}

    def test_get_session_schema(self):
        """Test GET /sessions/schema endpoint"""
        response = client.get("/api/v1/sessions/schema")
        assert response.status_code == 200

        data = response.json()
        assert "schema" in data
        assert "version" in data
        assert data["version"] == "1.0"


class TestConfigEndpoints:
    """Test configuration management endpoints"""

    @patch("app.core.auth.get_current_user")
    @patch("builtins.open", new_callable=mock_open, read_data='APP_DATA_DIR: ./app_data/violentutf\nversion: "1.0"')
    @patch("os.path.exists")
    @patch("os.path.getmtime")
    def test_get_config_parameters(self, mock_getmtime, mock_exists, mock_file, mock_get_user, auth_headers, mock_user):
        """Test GET /config/parameters endpoint"""
        mock_get_user.return_value = mock_user
        mock_exists.return_value = True
        mock_getmtime.return_value = 1700654921

        response = client.get("/api/v1/config/parameters", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "parameters" in data
        assert "APP_DATA_DIR" in data["parameters"]
        assert data["validation_status"] == "valid"

    @patch("app.core.auth.get_current_user")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_update_config_parameters(
        self, mock_makedirs, mock_exists, mock_file, mock_get_user, auth_headers, mock_user
    ):
        """Test PUT /config/parameters endpoint"""
        mock_get_user.return_value = mock_user
        mock_exists.return_value = False

        payload = {"parameters": {"APP_DATA_DIR": "./new_data_dir", "new_setting": "value"}, "merge_strategy": "merge"}

        response = client.put("/api/v1/config/parameters", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["parameters"]["APP_DATA_DIR"] == "./new_data_dir"
        assert data["parameters"]["new_setting"] == "value"

    @patch("app.core.auth.get_current_user")
    def test_load_config_from_yaml(self, mock_get_user, auth_headers, mock_user):
        """Test POST /config/parameters/load endpoint"""
        mock_get_user.return_value = mock_user

        # Create test YAML content
        yaml_content = """
APP_DATA_DIR: ./test_data
version: "2.0"
test_param: test_value
"""

        files = {"file": ("test_config.yaml", yaml_content, "application/x-yaml")}

        with patch("builtins.open", mock_open()):
            response = client.post("/api/v1/config/parameters/load", headers=auth_headers, files=files)
            assert response.status_code == 200

            data = response.json()
            assert data["success"] is True
            assert "test_param" in data["parameters"]

    def test_load_invalid_yaml(self, auth_headers):
        """Test loading invalid YAML file"""
        invalid_yaml = "invalid: yaml: content: ["

        files = {"file": ("invalid.yaml", invalid_yaml, "application/x-yaml")}

        response = client.post("/api/v1/config/parameters/load", headers=auth_headers, files=files)
        assert response.status_code == 400

    @patch("app.core.auth.get_current_user")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_list_parameter_files(self, mock_glob, mock_exists, mock_get_user, auth_headers, mock_user):
        """Test GET /config/parameters/files endpoint"""
        mock_get_user.return_value = mock_user
        mock_exists.return_value = True

        # Mock file paths
        mock_files = [
            type(
                "MockPath",
                (),
                {
                    "name": "default_parameters.yaml",
                    "stat": lambda: type("MockStat", (), {"st_size": 1024, "st_mtime": 1700654921})(),
                },
            )()
        ]
        mock_glob.return_value = mock_files

        response = client.get("/api/v1/config/parameters/files", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "files" in data
        assert data["total_count"] >= 0


class TestEnvironmentConfigEndpoints:
    """Test environment configuration endpoints"""

    @patch("app.core.auth.get_current_user")
    @patch.dict(
        os.environ,
        {
            "PYRIT_DB_SALT": "test_salt_12345678",
            "VIOLENTUTF_API_KEY": "test_api_key_12345678",
            "APP_DATA_DIR": "./app_data",
        },
    )
    def test_get_environment_config(self, mock_get_user, auth_headers, mock_user):
        """Test GET /config/environment endpoint"""
        mock_get_user.return_value = mock_user

        response = client.get("/api/v1/config/environment", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "environment_variables" in data
        assert "PYRIT_DB_SALT" in data["environment_variables"]
        # Check that sensitive values are masked
        assert data["environment_variables"]["PYRIT_DB_SALT"] == "test_sal..."

    @patch("app.core.auth.get_current_user")
    def test_update_environment_config(self, mock_get_user, auth_headers, mock_user):
        """Test PUT /config/environment endpoint"""
        mock_get_user.return_value = mock_user

        payload = {
            "environment_variables": {"PYRIT_DB_SALT": "new_salt_value_123456", "APP_DATA_DIR": "./new_app_data"},
            "validate_before_update": True,
        }

        response = client.put("/api/v1/config/environment", headers=auth_headers, json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["configuration_complete"] is True

    @patch("app.core.auth.get_current_user")
    def test_validate_environment_config(self, mock_get_user, auth_headers, mock_user):
        """Test POST /config/environment/validate endpoint"""
        mock_get_user.return_value = mock_user

        with patch.dict(os.environ, {"PYRIT_DB_SALT": "short"}):
            response = client.post("/api/v1/config/environment/validate", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert "validation_results" in data
            assert "recommendations" in data

    def test_get_environment_schema(self):
        """Test GET /config/environment/schema endpoint"""
        response = client.get("/api/v1/config/environment/schema")
        assert response.status_code == 200

        data = response.json()
        assert "schema" in data
        assert "PYRIT_DB_SALT" in data["schema"]
        assert data["schema"]["PYRIT_DB_SALT"]["required"] is True

    @patch("app.core.auth.get_current_user")
    def test_generate_salt(self, mock_get_user, auth_headers, mock_user):
        """Test POST /config/environment/generate-salt endpoint"""
        mock_get_user.return_value = mock_user

        response = client.post("/api/v1/config/environment/generate-salt", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "salt" in data
        assert data["length"] == 32
        assert len(data["salt"]) == 32


class TestFileEndpoints:
    """Test file management endpoints"""

    @patch("app.core.auth.get_current_user")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_upload_file(self, mock_makedirs, mock_file, mock_get_user, auth_headers, mock_user):
        """Test POST /files/upload endpoint"""
        mock_get_user.return_value = mock_user

        file_content = "test file content"
        files = {"file": ("test.txt", file_content, "text/plain")}

        response = client.post("/api/v1/files/upload", headers=auth_headers, files=files)
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "test.txt"
        assert "file_id" in data

    @patch("app.core.auth.get_current_user")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"file_id": "test-id", "original_filename": "test.txt", "content_type": "text/plain", "size_bytes": 100, "uploaded_at": "2024-01-01T00:00:00", "uploaded_by": "testuser"}',
    )
    @patch("os.path.exists")
    def test_get_file_metadata(self, mock_exists, mock_file, mock_get_user, auth_headers, mock_user):
        """Test GET /files/{file_id} endpoint"""
        mock_get_user.return_value = mock_user
        mock_exists.return_value = True

        response = client.get("/api/v1/files/test-id", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["file_info"]["file_id"] == "test-id"
        assert data["file_info"]["filename"] == "test.txt"
        assert data["available"] is True

    def test_get_file_not_found(self, auth_headers):
        """Test GET /files/{file_id} with non-existent file"""
        response = client.get("/api/v1/files/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    @patch("app.core.auth.get_current_user")
    @patch("pathlib.Path.glob")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"file_id": "test-id", "original_filename": "test.txt", "content_type": "text/plain", "size_bytes": 100, "uploaded_at": "2024-01-01T00:00:00", "uploaded_by": "testuser"}',
    )
    @patch("os.makedirs")
    def test_list_files(self, mock_makedirs, mock_file, mock_glob, mock_get_user, auth_headers, mock_user):
        """Test GET /files endpoint"""
        mock_get_user.return_value = mock_user

        # Mock metadata files
        mock_glob.return_value = [type("MockPath", (), {"name": "test-id.metadata.json"})()]

        response = client.get("/api/v1/files", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "files" in data
        assert "total_count" in data

    @patch("app.core.auth.get_current_user")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data='{"file_id": "test-id", "original_filename": "test.txt", "content_type": "text/plain", "size_bytes": 100, "uploaded_at": "2024-01-01T00:00:00", "uploaded_by": "testuser"}',
    )
    @patch("os.path.exists")
    @patch("os.remove")
    def test_delete_file(self, mock_remove, mock_exists, mock_file, mock_get_user, auth_headers, mock_user):
        """Test DELETE /files/{file_id} endpoint"""
        mock_get_user.return_value = mock_user
        mock_exists.return_value = True

        response = client.delete("/api/v1/files/test-id", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "message" in data


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
