"""
Pytest configuration and fixtures for ViolentUTF tests
Provides authentication, environment setup, and common test utilities
Enhanced for contract testing with authentication mocking
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional

import pytest
import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from tests.utils.keycloak_auth import keycloak_auth


# Load environment variables from project root
def load_environment():
    """Load environment variables from .env files"""
    project_root = Path(__file__).parent.parent
    env_files = [
        project_root / "violentutf" / ".env",
        project_root / "violentutf_api" / "fastapi_app" / ".env",
        project_root / "keycloak" / ".env",
    ]

    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            os.environ.setdefault(key, value)
            except Exception as e:
                print(f"Warning: Could not load {env_file}: {e}")


# Setup contract testing environment if enabled
def setup_contract_testing_environment():
    """Setup environment for contract testing."""
    if os.getenv("CONTRACT_TESTING", "false").lower() == "true":
        test_env_vars = {
            "TESTING": "true",
            "CONTRACT_TESTING": "true",
            "JWT_SECRET_KEY": "test_jwt_secret_for_contract_testing_only",
            "SECRET_KEY": "test_jwt_secret_for_contract_testing_only",
            "VIOLENTUTF_API_KEY": "test_api_key_for_contract_testing",
            "APISIX_API_KEY": "test_api_key_for_contract_testing",
            "AI_GATEWAY_API_KEY": "test_api_key_for_contract_testing",
            "KEYCLOAK_URL": "http://localhost:8080",
            "KEYCLOAK_REALM": "ViolentUTF-Test",
            "KEYCLOAK_USERNAME": "violentutf.test",
            "KEYCLOAK_PASSWORD": "test_password",
            "KEYCLOAK_APISIX_CLIENT_ID": "apisix-test",
            "KEYCLOAK_APISIX_CLIENT_SECRET": "test_secret",
            "VIOLENTUTF_API_URL": "http://localhost:8000",
            "DUCKDB_PATH": ":memory:",
            "PYRIT_DB_PATH": ":memory:",
        }

        for key, value in test_env_vars.items():
            os.environ.setdefault(key, value)

        print("🧪 Contract testing environment configured")


# Load environment and setup contract testing
load_environment()
setup_contract_testing_environment()


@pytest.fixture(scope="session")
def api_base_url():
    """API base URL for testing"""
    return os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")


@pytest.fixture(scope="session")
def keycloak_available():
    """Check if Keycloak is available for authentication"""
    return keycloak_auth.is_keycloak_available()


@pytest.fixture(scope="session")
def authenticated_headers(keycloak_available):
    """Get authenticated headers for API requests"""
    if not keycloak_available:
        pytest.skip("Keycloak not available for authentication")

    headers = keycloak_auth.get_auth_headers()
    if not headers or "Authorization" not in headers:
        pytest.skip("Could not obtain authentication headers")

    return headers


@pytest.fixture(scope="session")
def mock_headers():
    """Get mock headers for testing without authentication"""
    jwt_secret = os.getenv("JWT_SECRET_KEY", "test_secret")

    # Create a simple mock JWT for testing
    from datetime import datetime, timedelta, timezone

    import jwt

    payload = {
        "sub": "test_user",
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["ai-api-access"],
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    mock_token = jwt.encode(payload, jwt_secret, algorithm="HS256")

    headers = {
        "Authorization": f"Bearer {mock_token}",
        "Content-Type": "application/json",
        "X-Real-IP": "127.0.0.1",
        "X-Forwarded-For": "127.0.0.1",
        "X-Forwarded-Host": "localhost:9080",
        "X-API-Gateway": "APISIX",
    }

    # Add APISIX API key if available
    apisix_api_key = os.getenv("VIOLENTUTF_API_KEY")
    if apisix_api_key:
        headers["apikey"] = apisix_api_key

    return headers


@pytest.fixture(scope="function")
def api_headers(keycloak_available, authenticated_headers, mock_headers):
    """
    Get API headers - try authenticated first, fall back to mock
    This fixture allows tests to work both with and without Keycloak
    """
    if keycloak_available:
        try:
            return authenticated_headers
        except Exception:
            pass

    # Fall back to mock headers
    return mock_headers


@pytest.fixture(scope="session")
def apisix_running():
    """Check if APISIX is running"""
    try:
        api_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
        response = requests.get(f"{api_url.replace('/api', '')}/health", timeout=5)
        return response.status_code in [200, 404]  # 404 is OK, means APISIX is running
    except Exception:
        return False


@pytest.fixture(scope="session")
def fastapi_running():
    """Check if FastAPI is running"""
    try:
        # Try direct FastAPI access (for unit tests)
        response = requests.get("http://localhost:8000/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def setup_test_environment(apisix_running, fastapi_running):
    """Setup and validate test environment"""
    environment_status = {
        "apisix_running": apisix_running,
        "fastapi_running": fastapi_running,
        "keycloak_available": keycloak_auth.is_keycloak_available(),
        "api_base_url": os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080"),
        "jwt_secret_configured": bool(os.getenv("JWT_SECRET_KEY")),
        "apisix_api_key_configured": bool(os.getenv("VIOLENTUTF_API_KEY")),
    }

    return environment_status


@pytest.fixture(scope="function")
def cleanup_generators(api_headers, api_base_url):
    """Cleanup generators created during tests"""
    created_generators = []

    def track_generator(generator_id: str):
        created_generators.append(generator_id)
        return generator_id

    yield track_generator

    # Cleanup after test
    for gen_id in created_generators:
        try:
            requests.delete(f"{api_base_url}/api/v1/generators/{gen_id}", headers=api_headers, timeout=10)
        except Exception:
            pass  # Ignore cleanup failures


@pytest.fixture(scope="session", autouse=True)
def print_test_environment(setup_test_environment):
    """Print test environment status at start of session"""
    env = setup_test_environment

    print("\n" + "=" * 60)
    print("🧪 ViolentUTF Test Environment Status")
    print("=" * 60)
    print(f"🔌 APISIX Gateway:        {'✅ Running' if env['apisix_running'] else '❌ Not Running'}")
    print(f"⚡ FastAPI Service:       {'✅ Running' if env['fastapi_running'] else '❌ Not Running'}")
    print(f"🔐 Keycloak Available:    {'✅ Yes' if env['keycloak_available'] else '❌ No'}")
    print(f"🔑 JWT Secret:            {'✅ Configured' if env['jwt_secret_configured'] else '❌ Missing'}")
    print(f"🗝️  APISIX API Key:        {'✅ Configured' if env['apisix_api_key_configured'] else '❌ Missing'}")
    print(f"🌐 API Base URL:          {env['api_base_url']}")
    print("=" * 60)

    if env["keycloak_available"]:
        print("🔐 Testing Keycloak Authentication...")
        if keycloak_auth.test_authentication_flow():
            print("✅ Keycloak authentication flow working")
        else:
            print("⚠️  Keycloak authentication issues detected")
        print("=" * 60)


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line("markers", "requires_auth: mark test as requiring authentication")
    config.addinivalue_line("markers", "requires_apisix: mark test as requiring APISIX gateway")
    config.addinivalue_line("markers", "requires_fastapi: mark test as requiring FastAPI service")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "contract: mark test as contract testing")
    config.addinivalue_line("markers", "unit: mark test as unit testing")
    config.addinivalue_line("markers", "allows_mock_auth: mark test as accepting mock authentication")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle service requirements"""
    apisix_running = True
    fastapi_running = True
    keycloak_available = True

    try:
        apisix_running = requests.get("http://localhost:9080/health", timeout=2).status_code in [200, 404]
    except Exception:
        apisix_running = False

    try:
        fastapi_running = requests.get("http://localhost:8000/health", timeout=2).status_code == 200
    except Exception:
        fastapi_running = False

    try:
        keycloak_available = keycloak_auth.is_keycloak_available()
    except Exception:
        keycloak_available = False

    for item in items:
        # Skip tests requiring APISIX if not running
        if item.get_closest_marker("requires_apisix") and not apisix_running:
            item.add_marker(pytest.mark.skip(reason="APISIX gateway not running"))

        # Skip tests requiring FastAPI if not running
        if item.get_closest_marker("requires_fastapi") and not fastapi_running:
            item.add_marker(pytest.mark.skip(reason="FastAPI service not running"))

        # Skip tests requiring auth if Keycloak not available (unless mock auth is OK)
        if item.get_closest_marker("requires_auth") and not keycloak_available:
            # Check if test accepts mock auth
            if not item.get_closest_marker("allows_mock_auth"):
                item.add_marker(pytest.mark.skip(reason="Authentication not available"))


# Contract testing fixtures
@pytest.fixture(scope="session")
def contract_testing_enabled():
    """Check if contract testing is enabled."""
    return os.getenv("CONTRACT_TESTING", "false").lower() == "true"


@pytest.fixture(scope="session")
def test_app(contract_testing_enabled):
    """Create FastAPI test app with authentication mocking."""
    if not contract_testing_enabled:
        pytest.skip("Contract testing not enabled")

    try:
        # Import after environment setup
        from tests.api_tests.test_auth_mock import ContractTestingPatches

        with ContractTestingPatches():
            from violentutf_api.fastapi_app.app.main import app

            yield app
    except ImportError as e:
        pytest.skip(f"Could not import FastAPI app: {e}")


@pytest.fixture(scope="session")
def test_client(test_app):
    """Create test client with authentication mocking."""
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="session")
def test_headers(contract_testing_enabled):
    """Create test headers for API calls."""
    if not contract_testing_enabled:
        pytest.skip("Contract testing not enabled")

    try:
        from tests.api_tests.test_auth_mock import create_test_headers

        return create_test_headers()
    except ImportError:
        pytest.skip("Could not import test auth utilities")


@pytest.fixture(scope="session")
def auth_patches(contract_testing_enabled):
    """Apply authentication patches for contract testing."""
    if not contract_testing_enabled:
        pytest.skip("Contract testing not enabled")

    try:
        from tests.api_tests.test_auth_mock import ContractTestingPatches

        with ContractTestingPatches() as patches:
            yield patches
    except ImportError:
        pytest.skip("Could not import authentication patches")


@pytest.fixture(scope="session")
def openapi_schema(test_app):
    """Generate OpenAPI schema from FastAPI app."""
    return test_app.openapi()


@pytest.fixture(scope="session")
def contract_base_url():
    """Base URL for contract testing."""
    return "http://testserver"


@pytest.fixture(scope="function")
def mock_database(contract_testing_enabled):
    """Create mock database session for testing."""
    if not contract_testing_enabled:
        pytest.skip("Contract testing not enabled")

    try:
        from tests.api_tests.test_auth_mock import create_mock_database_session

        return create_mock_database_session()
    except ImportError:
        pytest.skip("Could not import mock database utilities")


# Cleanup after contract tests
@pytest.fixture(scope="session", autouse=True)
def cleanup_contract_tests():
    """Cleanup after contract tests complete."""
    yield

    # Cleanup test artifacts if contract testing was enabled
    if os.getenv("CONTRACT_TESTING", "false").lower() == "true":
        test_files = ["generated_openapi.json", "contract-test-results.xml", "test_output.log"]

        for file in test_files:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except Exception:
                    pass  # Ignore cleanup failures
