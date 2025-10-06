"""
Test suite for smoke tests - validates that smoke tests themselves work correctly.

This is meta-testing following TDD principles:
Write tests for smoke tests → Implement smoke tests → Refactor

Issue: #328 - Phase 4.3.7: Production Deployment and Cleanup
"""

import importlib
import sys
from pathlib import Path

import pytest

# Add project root to Python path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))


class TestSmokeTestsStructure:
    """Test that smoke test modules have proper structure."""

    def test_smoke_tests_package_exists(self):
        """Test that smoke_tests package can be imported."""
        try:
            import tests.smoke_tests  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Could not import smoke_tests package: {e}")

    def test_smoke_tests_init_has_config(self):
        """Test that __init__.py has required configuration."""
        import tests.smoke_tests as smoke_tests

        assert hasattr(smoke_tests, "DEFAULT_API_BASE_URL")
        assert hasattr(smoke_tests, "DEFAULT_STREAMLIT_URL")
        assert hasattr(smoke_tests, "DEFAULT_DB_PATH")

    def test_api_health_module_exists(self):
        """Test that test_api_health module exists."""
        try:
            import tests.smoke_tests.test_api_health  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Could not import test_api_health module: {e}")

    def test_database_connectivity_module_exists(self):
        """Test that test_database_connectivity module exists."""
        try:
            import tests.smoke_tests.test_database_connectivity  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(
                f"Could not import test_database_connectivity module: {e}"
            )


class TestAPIHealthSmokeTests:
    """Test that API health smoke tests have proper structure."""

    def test_api_health_has_test_class(self):
        """Test that test_api_health has TestAPIHealth class."""
        try:
            from tests.smoke_tests.test_api_health import TestAPIHealth

            assert TestAPIHealth is not None
        except ImportError as e:
            pytest.fail(f"Could not import TestAPIHealth class: {e}")

    def test_api_health_has_health_endpoint_test(self):
        """Test that TestAPIHealth has test_health_endpoint method."""
        from tests.smoke_tests.test_api_health import TestAPIHealth

        assert hasattr(TestAPIHealth, "test_health_endpoint")
        assert callable(getattr(TestAPIHealth, "test_health_endpoint"))

    def test_api_health_has_response_times_test(self):
        """Test that TestAPIHealth has test_api_response_times method."""
        from tests.smoke_tests.test_api_health import TestAPIHealth

        assert hasattr(TestAPIHealth, "test_api_response_times")
        assert callable(getattr(TestAPIHealth, "test_api_response_times"))

    def test_api_health_has_endpoints_accessible_test(self):
        """Test that TestAPIHealth has test_all_endpoints_accessible."""
        from tests.smoke_tests.test_api_health import TestAPIHealth

        assert hasattr(TestAPIHealth, "test_all_endpoints_accessible")
        assert callable(
            getattr(TestAPIHealth, "test_all_endpoints_accessible")
        )


class TestDatabaseConnectivitySmokeTests:
    """Test that database connectivity smoke tests have proper structure."""

    def test_db_connectivity_has_test_class(self):
        """Test that test_database_connectivity has TestDatabaseConnectivity."""
        try:
            from tests.smoke_tests.test_database_connectivity import (
                TestDatabaseConnectivity,
            )

            assert TestDatabaseConnectivity is not None
        except ImportError as e:
            pytest.fail(f"Could not import TestDatabaseConnectivity class: {e}")

    def test_db_connectivity_has_files_exist_test(self):
        """Test that TestDatabaseConnectivity has test_database_files_exist."""
        from tests.smoke_tests.test_database_connectivity import (
            TestDatabaseConnectivity,
        )

        assert hasattr(TestDatabaseConnectivity, "test_database_files_exist")
        assert callable(
            getattr(TestDatabaseConnectivity, "test_database_files_exist")
        )

    def test_db_connectivity_has_accessible_test(self):
        """Test that TestDatabaseConnectivity has test_database_accessible."""
        from tests.smoke_tests.test_database_connectivity import (
            TestDatabaseConnectivity,
        )

        assert hasattr(TestDatabaseConnectivity, "test_database_accessible")
        assert callable(
            getattr(TestDatabaseConnectivity, "test_database_accessible")
        )

    def test_db_connectivity_has_schema_test(self):
        """Test that TestDatabaseConnectivity has test_database_schema."""
        from tests.smoke_tests.test_database_connectivity import (
            TestDatabaseConnectivity,
        )

        assert hasattr(TestDatabaseConnectivity, "test_database_schema")
        assert callable(getattr(TestDatabaseConnectivity, "test_database_schema"))


class TestSmokeTestsExecution:
    """Test that smoke tests can actually execute."""

    def test_smoke_tests_can_be_collected(self):
        """Test that pytest can collect smoke tests."""
        smoke_tests_dir = REPO_ROOT / "tests" / "smoke_tests"
        assert smoke_tests_dir.exists()

        # Check that test files exist
        test_files = list(smoke_tests_dir.glob("test_*.py"))
        assert len(test_files) >= 2, "Should have at least 2 test files"

    def test_api_health_tests_are_valid_pytest(self):
        """Test that API health tests follow pytest conventions."""
        from tests.smoke_tests.test_api_health import TestAPIHealth

        test_class = TestAPIHealth
        test_methods = [
            method
            for method in dir(test_class)
            if method.startswith("test_") and callable(getattr(test_class, method))
        ]

        assert len(test_methods) >= 3, (
            "Should have at least 3 test methods"
        )

    def test_db_connectivity_tests_are_valid_pytest(self):
        """Test that DB connectivity tests follow pytest conventions."""
        from tests.smoke_tests.test_database_connectivity import (
            TestDatabaseConnectivity,
        )

        test_class = TestDatabaseConnectivity
        test_methods = [
            method
            for method in dir(test_class)
            if method.startswith("test_") and callable(getattr(test_class, method))
        ]

        assert len(test_methods) >= 3, (
            "Should have at least 3 test methods"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
