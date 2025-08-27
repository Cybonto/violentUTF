"""
Pytest configuration for API tests
Inherits from main conftest.py and adds API-specific fixtures
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator

# Add parent directory to sys.path to access main conftest and utils
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import pytest
import requests

# Import available fixtures from the main conftest
from conftest import api_headers, authenticated_headers, mock_headers

# Import the keycloak_auth utility
from utils.keycloak_auth import keycloak_auth

# Contract testing imports
from tests.api_tests.test_auth_mock import ContractTestingPatches, create_mock_database_session, create_test_headers


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """API base URL for testing - overrides main conftest to ensure APISIX gateway usage"""
    return os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")


@pytest.fixture(scope="function")
def cleanup_generators(api_headers, api_base_url) -> Generator[Any, None, None]:
    """
    Cleanup generators created during tests
    Tracks created generators and removes them after test completion
    """
    created_generators = []

    def track_generator(generator_id: str) -> str:
        """Track a generator for cleanup"""
        created_generators.append(generator_id)
        return generator_id

    yield track_generator

    # Cleanup after test
    for gen_id in created_generators:
        try:
            response = requests.delete(f"{api_base_url}/api/v1/generators/{gen_id}", headers=api_headers, timeout=10)
            if response.status_code in [200, 204, 404]:
                print(f"✅ Cleaned up generator: {gen_id}")
            else:
                print(f"⚠️ Failed to cleanup generator {gen_id}: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Exception during generator cleanup {gen_id}: {e}")


# Contract testing fixtures
@pytest.fixture(scope="session")
def contract_testing_enabled() -> bool:
    """Check if contract testing is enabled."""
    return os.getenv("CONTRACT_TESTING", "false").lower() == "true"


@pytest.fixture(scope="session")
def test_app(contract_testing_enabled) -> Generator[Any, None, None]:
    """Create FastAPI test app with authentication mocking."""
    if not contract_testing_enabled:
        pytest.skip("Contract testing not enabled")

    try:
        # Setup minimal test environment first
        os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_secret_for_contract_testing_only")
        os.environ.setdefault("TESTING", "true")
        os.environ.setdefault("CONTRACT_TESTING", "true")

        # Try to import the app directly
        from violentutf_api.fastapi_app.app.main import app

        yield app
    except ImportError as e:
        pytest.skip(f"Could not import FastAPI app: {e}")


@pytest.fixture(scope="session")
def test_client(test_app) -> Generator[Any, None, None]:
    """Create test client with authentication mocking."""
    from fastapi.testclient import TestClient

    with TestClient(test_app) as client:
        yield client


@pytest.fixture(scope="session")
def test_headers(contract_testing_enabled) -> Dict[str, str]:
    """Create test headers for API calls."""
    if not contract_testing_enabled:
        pytest.skip("Contract testing not enabled")

    return create_test_headers()


@pytest.fixture(scope="session")
def openapi_schema(test_app) -> Dict[str, Any]:
    """Generate OpenAPI schema from FastAPI app."""
    return test_app.openapi()


@pytest.fixture(scope="function")
def mock_database(contract_testing_enabled) -> Any:
    """Create mock database session for testing."""
    if not contract_testing_enabled:
        pytest.skip("Contract testing not enabled")

    return create_mock_database_session()


def pytest_configure(config) -> None:
    """Configure pytest for API testing"""
    # Add custom markers specific to API tests
    config.addinivalue_line("markers", "api: marks tests as API tests (require API connectivity)")
    config.addinivalue_line("markers", "generator: marks tests as generator-related tests")
    config.addinivalue_line("markers", "requires_cleanup: marks tests that require cleanup of resources")

    # Add markers from main conftest
    config.addinivalue_line("markers", "requires_auth: mark test as requiring authentication")
    config.addinivalue_line("markers", "requires_apisix: mark test as requiring APISIX gateway")
    config.addinivalue_line("markers", "requires_fastapi: mark test as requiring FastAPI service")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "contract: mark test as contract testing")
    config.addinivalue_line("markers", "unit: mark test as unit testing")
    config.addinivalue_line("markers", "allows_mock_auth: mark test as accepting mock authentication")
