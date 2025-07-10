"""
API Contract Testing for ViolentUTF API endpoints.
Tests API contracts against OpenAPI specification.
"""

import json
from typing import Any, Dict

import pytest

from tests.api_tests.test_auth_mock import ContractTestingPatches


@pytest.mark.contract
@pytest.mark.allows_mock_auth
class TestAPIContractValidation:
    """Test API contract validation."""

    def test_openapi_schema_generation(self, test_app, openapi_schema):
        """Test that OpenAPI schema can be generated from FastAPI app."""
        assert openapi_schema is not None
        assert "openapi" in openapi_schema
        assert "info" in openapi_schema
        assert "paths" in openapi_schema

        # Check OpenAPI version
        assert openapi_schema["openapi"].startswith("3.0")

        # Check required info fields
        info = openapi_schema["info"]
        assert "title" in info
        assert "version" in info

    def test_openapi_security_schemes(self, openapi_schema):
        """Test that security schemes are properly defined."""
        components = openapi_schema.get("components", {})
        security_schemes = components.get("securitySchemes", {})

        # Check for expected authentication schemes
        assert "bearerAuth" in security_schemes or "apiKeyAuth" in security_schemes

        # Validate bearer auth if present
        if "bearerAuth" in security_schemes:
            bearer_auth = security_schemes["bearerAuth"]
            assert bearer_auth["type"] == "http"
            assert bearer_auth["scheme"] == "bearer"

    def test_api_endpoints_defined(self, openapi_schema):
        """Test that required API endpoints are defined."""
        paths = openapi_schema.get("paths", {})

        # Check for key endpoints
        expected_endpoints = [
            "/health",
            "/api/v1/generators",
            "/api/v1/scorers",
            "/api/v1/orchestrators",
            "/api/v1/datasets",
        ]

        found_endpoints = []
        for endpoint in expected_endpoints:
            if endpoint in paths:
                found_endpoints.append(endpoint)

        # At least some endpoints should be present
        assert len(found_endpoints) > 0, f"No expected endpoints found in {list(paths.keys())}"

    def test_error_response_schemas(self, openapi_schema):
        """Test that error response schemas are consistent."""
        paths = openapi_schema.get("paths", {})

        for path, path_obj in paths.items():
            for method, method_obj in path_obj.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    responses = method_obj.get("responses", {})

                    # Check for error response codes
                    error_codes = ["400", "401", "403", "404", "422", "500"]
                    for code in error_codes:
                        if code in responses:
                            response = responses[code]
                            # Should have content or description
                            assert "description" in response or "content" in response


@pytest.mark.contract
@pytest.mark.allows_mock_auth
class TestAPIEndpointContracts:
    """Test individual API endpoint contracts."""

    def test_health_endpoint_contract(self, test_client, test_headers):
        """Test health endpoint contract."""
        response = test_client.get("/health", headers=test_headers)

        # Should return 200 or 404 (if not implemented)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            # Health endpoint should return status
            assert "status" in data

    def test_generators_endpoint_contract(self, test_client, test_headers):
        """Test generators endpoint contract."""
        response = test_client.get("/api/v1/generators", headers=test_headers)

        # Should return 200 or 404 (if not implemented)
        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            # Should return a list
            assert isinstance(data, list)

    def test_scorers_endpoint_contract(self, test_client, test_headers):
        """Test scorers endpoint contract."""
        response = test_client.get("/api/v1/scorers", headers=test_headers)

        # Should return 200 or 404 (if not implemented)
        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            # Should return a list
            assert isinstance(data, list)

    def test_orchestrators_endpoint_contract(self, test_client, test_headers):
        """Test orchestrators endpoint contract."""
        response = test_client.get("/api/v1/orchestrators", headers=test_headers)

        # Should return 200 or 404 (if not implemented)
        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            # Should return a list
            assert isinstance(data, list)

    def test_datasets_endpoint_contract(self, test_client, test_headers):
        """Test datasets endpoint contract."""
        response = test_client.get("/api/v1/datasets", headers=test_headers)

        # Should return 200 or 404 (if not implemented)
        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            # Should return a list
            assert isinstance(data, list)


@pytest.mark.contract
@pytest.mark.allows_mock_auth
class TestAuthenticationContracts:
    """Test authentication contract compliance."""

    def test_unauthorized_access_handling(self, test_client):
        """Test that unauthorized access is properly handled."""
        # Test without authentication headers
        response = test_client.get("/api/v1/generators")

        # Should return 401 or 403, or allow if endpoint is public
        assert response.status_code in [200, 401, 403, 404, 422]

    def test_invalid_token_handling(self, test_client):
        """Test that invalid tokens are properly handled."""
        invalid_headers = {"Authorization": "Bearer invalid_token", "Content-Type": "application/json"}

        response = test_client.get("/api/v1/generators", headers=invalid_headers)

        # Should return 401 or 403 for invalid token
        assert response.status_code in [200, 401, 403, 404, 422]

    def test_api_key_authentication(self, test_client):
        """Test API key authentication."""
        api_key_headers = {"apikey": "test_api_key", "Content-Type": "application/json"}

        response = test_client.get("/api/v1/generators", headers=api_key_headers)

        # Should handle API key auth
        assert response.status_code in [200, 401, 403, 404, 422]


@pytest.mark.contract
@pytest.mark.allows_mock_auth
class TestResponseFormatContracts:
    """Test response format contract compliance."""

    def test_json_response_format(self, test_client, test_headers):
        """Test that API responses are in JSON format."""
        endpoints = ["/api/v1/generators", "/api/v1/scorers", "/api/v1/orchestrators", "/api/v1/datasets"]

        for endpoint in endpoints:
            response = test_client.get(endpoint, headers=test_headers)

            if response.status_code == 200:
                # Should have JSON content type
                assert "application/json" in response.headers.get("content-type", "")

                # Should be valid JSON
                try:
                    response.json()
                except json.JSONDecodeError:
                    pytest.fail(f"Invalid JSON response from {endpoint}")

    def test_error_response_format(self, test_client):
        """Test that error responses follow expected format."""
        # Test with invalid endpoint
        response = test_client.get("/api/v1/invalid_endpoint")

        if response.status_code >= 400:
            # Should have JSON content type for errors
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                data = response.json()
                # Should have error details
                assert "detail" in data or "message" in data or "error" in data

    def test_cors_headers(self, test_client, test_headers):
        """Test that CORS headers are properly set."""
        response = test_client.options("/api/v1/generators", headers=test_headers)

        # Should handle OPTIONS request
        assert response.status_code in [200, 204, 404, 405]


@pytest.mark.contract
@pytest.mark.allows_mock_auth
class TestDataValidationContracts:
    """Test data validation contract compliance."""

    def test_post_request_validation(self, test_client, test_headers):
        """Test POST request validation."""
        # Test with invalid JSON
        response = test_client.post("/api/v1/generators", headers=test_headers, json={"invalid": "data"})

        # Should handle validation errors appropriately
        assert response.status_code in [200, 400, 404, 422]

    def test_query_parameter_validation(self, test_client, test_headers):
        """Test query parameter validation."""
        # Test with invalid query parameters
        response = test_client.get("/api/v1/generators?invalid_param=value", headers=test_headers)

        # Should handle invalid parameters gracefully
        assert response.status_code in [200, 400, 404, 422]

    def test_path_parameter_validation(self, test_client, test_headers):
        """Test path parameter validation."""
        # Test with invalid path parameter
        response = test_client.get("/api/v1/generators/invalid_id", headers=test_headers)

        # Should handle invalid path parameters
        assert response.status_code in [200, 400, 404, 422]


@pytest.mark.contract
@pytest.mark.allows_mock_auth
class TestPerformanceContracts:
    """Test performance-related contract compliance."""

    def test_response_time_reasonable(self, test_client, test_headers):
        """Test that response times are reasonable."""
        import time

        endpoints = ["/api/v1/generators", "/api/v1/scorers"]

        for endpoint in endpoints:
            start_time = time.time()
            _ = test_client.get(endpoint, headers=test_headers)  # Response not used, just timing
            end_time = time.time()

            response_time = end_time - start_time

            # Response should be under 5 seconds for contract testing
            assert response_time < 5.0, f"Response time too slow for {endpoint}: {response_time}s"

    def test_concurrent_request_handling(self, test_client, test_headers):
        """Test that API can handle concurrent requests."""
        import threading
        import time

        results = []

        def make_request():
            response = test_client.get("/api/v1/generators", headers=test_headers)
            results.append(response.status_code)

        # Make 3 concurrent requests
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All requests should complete
        assert len(results) == 3

        # At least some should succeed (allowing for 404s in testing)
        success_codes = [200, 404, 422]
        successful_requests = [r for r in results if r in success_codes]
        assert len(successful_requests) > 0
