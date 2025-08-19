# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Authentication mock layer for API contract testing.

Provides simplified authentication bypass for testing purposes.
"""

import json
import logging
import os
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional
from unittest.mock import Mock, patch

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPBearer

logger = logging.getLogger(__name__)

# Test JWT secret - only for testing
TEST_JWT_SECRET = "test_jwt_secret_for_contract_testing_only"
TEST_API_KEY = "test_api_key_for_contract_testing"


class MockTokenManager:
    """Mock token manager for contract testing."""

    def __init__(self: "MockTokenManager") -> None:
        """Initialize mock token manager."""
        self.test_user_payload = {
            "sub": "test_user",
            "username": "violentutf.test",
            "email": "test@violentutf.local",
            "roles": ["ai-api-access", "admin"],
            "exp": int(time.time()) + 3600,  # 1 hour from now
            "iat": int(time.time()),
            "iss": "ViolentUTF-Test",
        }

    def generate_test_token(self: "MockTokenManager", user_payload: Optional[Dict[str, Any]] = None) -> str:
        """Generate a test JWT token."""
        payload = user_payload or self.test_user_payload
        return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    def extract_user_token(self: "MockTokenManager") -> Optional[str]:
        """Mock token extraction."""
        return self.generate_test_token()

    def has_ai_access(self: "MockTokenManager", token: str) -> bool:
        """Mock AI access check."""
        return True

    def get_user_roles(self: "MockTokenManager", token: str) -> List[str]:
        """Mock user roles."""
        return ["ai-api-access", "admin"]


class MockAuthenticationMiddleware:
    """Mock authentication middleware for contract testing."""

    def __init__(self: "MockAuthenticationMiddleware", app: object) -> None:
        """Initialize mock authentication middleware."""
        self.app = app
        self.token_manager = MockTokenManager()

    async def __call__(self: "MockAuthenticationMiddleware", scope: Dict[str, Any], receive: Callable[[], Awaitable[Dict[str, Any]]], send: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Mock authentication middleware."""
        # Add test authentication headers
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))

            # Add mock APISIX gateway header
            headers[b"x-api-gateway"] = b"APISIX"

            # Add test authorization header if not present
            if b"authorization" not in headers:
                test_token = self.token_manager.generate_test_token()
                headers[b"authorization"] = f"Bearer {test_token}".encode()

            # Update scope with mock headers
            scope["headers"] = [(k, v) for k, v in headers.items()]

        await self.app(scope, receive, send)


def setup_test_environment() -> None:
    """Set up test environment variables for contract testing."""
    test_env_vars = {
        "JWT_SECRET_KEY": TEST_JWT_SECRET,
        "SECRET_KEY": TEST_JWT_SECRET,
        "VIOLENTUTF_API_KEY": TEST_API_KEY,
        "APISIX_API_KEY": TEST_API_KEY,
        "AI_GATEWAY_API_KEY": TEST_API_KEY,
        "KEYCLOAK_URL": "http://localhost:8080",
        "KEYCLOAK_REALM": "ViolentUTF-Test",
        "KEYCLOAK_USERNAME": "violentutf.test",
        "KEYCLOAK_PASSWORD": "test_password",
        "KEYCLOAK_APISIX_CLIENT_ID": "apisix-test",
        "KEYCLOAK_APISIX_CLIENT_SECRET": "test_secret",
        "VIOLENTUTF_API_URL": "http://localhost:8000",
        "TESTING": "true",
        "CONTRACT_TESTING": "true",
    }

    for key, value in test_env_vars.items():
        if key not in os.environ:
            os.environ[key] = value


def mock_jwt_decode(token: str, secret: str = None, algorithms: list = None) -> Dict[str, Any]:
    """Mock JWT decode function."""
    # Return mock payload for any token during testing
    return {
        "sub": "test_user",
        "username": "violentutf.test",
        "email": "test@violentutf.local",
        "roles": ["ai-api-access", "admin"],
        "exp": int(time.time()) + 3600,
        "iat": int(time.time()),
        "iss": "ViolentUTF-Test",
    }


def mock_requests_post(*args: Any, **kwargs: Any) -> Mock:
    """Mock requests.post for authentication calls."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": MockTokenManager().generate_test_token(),
        "token_type": "bearer",
        "expires_in": 3600,
        "refresh_token": "test_refresh_token",
    }
    return mock_response


def mock_apisix_endpoints():
    """Mock APISIX endpoints for testing."""
    return {
        "openai": {"gpt-4": "/ai/openai/gpt4", "gpt-3.5-turbo": "/ai/openai/gpt35"},
        "anthropic": {
            "claude-3-sonnet-20240229": "/ai/anthropic/claude3-sonnet",
            "claude-3-5-sonnet-20241022": "/ai/anthropic/claude35-sonnet",
        },
        "ollama": {"llama2": "/ai/ollama/llama2"},
    }


class ContractTestingPatches:
    """Context manager for applying all contract testing patches."""

    def __init__(self):
        self.patches = []

    def __enter__(self):
        """Apply all contract testing patches."""
        setup_test_environment()

        # Patch JWT decode
        jwt_patch = patch("jwt.decode", side_effect=mock_jwt_decode)
        self.patches.append(jwt_patch)
        jwt_patch.start()

        # Patch requests.post for authentication
        requests_patch = patch("requests.post", side_effect=mock_requests_post)
        self.patches.append(requests_patch)
        requests_patch.start()

        # Patch token manager
        token_manager_patch = patch("violentutf.utils.token_manager.token_manager", MockTokenManager())
        self.patches.append(token_manager_patch)
        token_manager_patch.start()

        # Patch APISIX endpoints
        endpoints_patch = patch(
            "violentutf.utils.token_manager.TokenManager.get_apisix_endpoints", return_value=mock_apisix_endpoints()
        )
        self.patches.append(endpoints_patch)
        endpoints_patch.start()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop all patches."""
        for patch_obj in self.patches:
            patch_obj.stop()


def create_test_client_with_auth():
    """Create a test client with authentication mocking."""
    from fastapi.testclient import TestClient

    # Import the FastAPI app
    try:
        from violentutf_api.fastapi_app.app.main import app
    except ImportError:
        logger.error("Could not import FastAPI app for testing")
        return None

    # Apply authentication middleware
    app.middleware("http")(MockAuthenticationMiddleware)

    return TestClient(app)


# Pytest fixtures for contract testing
def pytest_configure(config):
    """Configure pytest for contract testing."""
    setup_test_environment()


def pytest_fixture_setup():
    """Setup fixtures for contract testing."""
    return ContractTestingPatches()


# Test helper functions
def create_test_headers() -> Dict[str, str]:
    """Create test headers for API calls."""
    token_manager = MockTokenManager()
    test_token = token_manager.generate_test_token()

    return {
        "Authorization": f"Bearer {test_token}",
        "X-API-Gateway": "APISIX",
        "Content-Type": "application/json",
        "apikey": TEST_API_KEY,
    }


def validate_response_schema(response_data: Dict[str, Any], expected_schema: Dict[str, Any]) -> bool:
    """Validate response data against expected schema."""
    try:
        import jsonschema

        jsonschema.validate(response_data, expected_schema)
        return True
    except jsonschema.ValidationError as e:
        logger.error(f"Response schema validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Schema validation error: {e}")
        return False


def create_mock_database_session():
    """Create a mock database session for testing."""
    from unittest.mock import Mock

    mock_db = Mock()
    mock_db.query.return_value = Mock()
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.rollback.return_value = None
    mock_db.close.return_value = None

    return mock_db
