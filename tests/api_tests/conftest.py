"""
Pytest configuration for API tests
Inherits from main conftest.py and adds API-specific fixtures
"""

import os
import sys
from pathlib import Path

# Add parent directory to sys.path to access main conftest and utils
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

import pytest
import requests

# Import all fixtures from the main conftest
from conftest import *

# Import the keycloak_auth utility
from utils.keycloak_auth import keycloak_auth


@pytest.fixture(scope="session")
def api_base_url():
    """API base URL for testing - overrides main conftest to ensure APISIX gateway usage"""
    return os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")


@pytest.fixture(scope="function")
def cleanup_generators(api_headers, api_base_url):
    """
    Cleanup generators created during tests
    Tracks created generators and removes them after test completion
    """
    created_generators = []

    def track_generator(generator_id: str):
        """Track a generator for cleanup"""
        created_generators.append(generator_id)
        return generator_id

    yield track_generator

    # Cleanup after test
    for gen_id in created_generators:
        try:
            response = requests.delete(
                f"{api_base_url}/api/v1/generators/{gen_id}",
                headers=api_headers,
                timeout=10,
            )
            if response.status_code in [200, 204, 404]:
                print(f"✅ Cleaned up generator: {gen_id}")
            else:
                print(f"⚠️ Failed to cleanup generator {gen_id}: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Exception during generator cleanup {gen_id}: {e}")


def pytest_configure(config):
    """Configure pytest for API testing"""
    # Add custom markers specific to API tests
    config.addinivalue_line(
        "markers", "api: marks tests as API tests (require API connectivity)"
    )
    config.addinivalue_line(
        "markers", "generator: marks tests as generator-related tests"
    )
    config.addinivalue_line(
        "markers", "requires_cleanup: marks tests that require cleanup of resources"
    )
