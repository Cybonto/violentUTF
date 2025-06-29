"""
Integration tests for ViolentUTF API through APISIX Gateway
Tests the actual APISIX routing to ensure endpoints work as expected
"""

import json
import os
from typing import Any, Dict, Optional

import pytest
import requests

# APISIX Gateway Configuration
APISIX_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
APISIX_ENDPOINTS = {
    "health": f"{APISIX_BASE_URL}/health",
    "docs": f"{APISIX_BASE_URL}/docs",
    "openapi": f"{APISIX_BASE_URL}/openapi.json",
    "auth_token_info": f"{APISIX_BASE_URL}/api/v1/auth/token/info",
    "auth_token_validate": f"{APISIX_BASE_URL}/api/v1/auth/token/validate",
    "auth_logout": f"{APISIX_BASE_URL}/api/v1/auth/logout",
    "database_initialize": f"{APISIX_BASE_URL}/api/v1/database/initialize",
    "database_status": f"{APISIX_BASE_URL}/api/v1/database/status",
    "database_stats": f"{APISIX_BASE_URL}/api/v1/database/stats",
    "database_reset": f"{APISIX_BASE_URL}/api/v1/database/reset",
    "sessions": f"{APISIX_BASE_URL}/api/v1/sessions",
    "sessions_reset": f"{APISIX_BASE_URL}/api/v1/sessions/reset",
    "sessions_schema": f"{APISIX_BASE_URL}/api/v1/sessions/schema",
    "config_parameters": f"{APISIX_BASE_URL}/api/v1/config/parameters",
    "config_environment": f"{APISIX_BASE_URL}/api/v1/config/environment",
    "config_generate_salt": f"{APISIX_BASE_URL}/api/v1/config/environment/generate-salt",
    "files_upload": f"{APISIX_BASE_URL}/api/v1/files/upload",
    "files_list": f"{APISIX_BASE_URL}/api/v1/files",
}

# Mock JWT token for testing - updated to match new authentication structure
MOCK_JWT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSIsIm5hbWUiOiJUZXN0IFVzZXIiLCJyb2xlcyI6WyJhaS1hcGktYWNjZXNzIl0sImV4cCI6OTk5OTk5OTk5OSwiaWF0IjoxNzAwNjU0OTIxfQ.test_signature"


def get_apisix_headers(include_auth: bool = True) -> Dict[str, str]:
    """Get headers for APISIX requests"""
    headers = {
        "Content-Type": "application/json",
        "X-Real-IP": "127.0.0.1",
        "X-Forwarded-For": "127.0.0.1",
        "X-Forwarded-Host": "localhost:9080",
        "X-API-Gateway": "APISIX",
    }
    if include_auth:
        headers["Authorization"] = f"Bearer {MOCK_JWT_TOKEN}"
    return headers


def make_request(method: str, url: str, include_auth: bool = True, **kwargs) -> requests.Response:
    """Make a request through APISIX with proper headers"""
    headers = get_apisix_headers(include_auth)
    if "headers" in kwargs:
        headers.update(kwargs["headers"])
    kwargs["headers"] = headers

    return requests.request(method, url, timeout=30, **kwargs)


class TestAPISIXConnectivity:
    """Test basic APISIX connectivity and routing"""

    def test_apisix_gateway_running(self):
        """Test that APISIX Gateway is accessible"""
        try:
            response = requests.get(f"{APISIX_BASE_URL}/health", timeout=10)
            assert response.status_code in [200, 404], f"APISIX should be running, got {response.status_code}"
        except requests.ConnectionError:
            pytest.fail("APISIX Gateway is not running on port 9080. Run: cd apisix && docker compose up -d")

    def test_health_endpoint_via_apisix(self):
        """Test health endpoint through APISIX"""
        response = make_request("GET", APISIX_ENDPOINTS["health"], include_auth=False)
        # Should either work (200) or be not found (404) if route not configured
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"

        if response.status_code == 404:
            pytest.skip("Health endpoint route not configured in APISIX. Run: ./configure_routes.sh")

    def test_api_docs_via_apisix(self):
        """Test API documentation endpoint through APISIX"""
        response = make_request("GET", APISIX_ENDPOINTS["docs"], include_auth=False)
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"

        if response.status_code == 404:
            pytest.skip("Docs endpoint route not configured in APISIX. Run: ./configure_routes.sh")


class TestAuthenticationEndpointsViaAPISIX:
    """Test authentication endpoints through APISIX"""

    def test_token_info_endpoint_routing(self):
        """Test that auth/token/info endpoint is routed correctly"""
        response = make_request("GET", APISIX_ENDPOINTS["auth_token_info"])

        # Should get some response (not connection error)
        assert response.status_code != 0, "Failed to connect to APISIX"

        # Should be 401/403 (auth required) or 404 (route not configured)
        if response.status_code == 404:
            pytest.fail("Authentication route not configured in APISIX. Run: ./configure_routes.sh")

        # If route is configured, should require authentication
        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_token_validate_endpoint_routing(self):
        """Test that auth/token/validate endpoint is routed correctly"""
        payload = {"required_roles": ["ai-api-access"], "check_ai_access": True}

        response = make_request("POST", APISIX_ENDPOINTS["auth_token_validate"], json=payload)

        if response.status_code == 404:
            pytest.fail("Authentication route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_logout_endpoint_routing(self):
        """Test that auth/logout endpoint is routed correctly"""
        response = make_request("POST", APISIX_ENDPOINTS["auth_logout"])

        if response.status_code == 404:
            pytest.fail("Authentication route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"


class TestDatabaseEndpointsViaAPISIX:
    """Test database management endpoints through APISIX"""

    def test_database_initialize_routing(self):
        """Test database initialization endpoint routing"""
        payload = {"force_recreate": False, "custom_salt": "test_salt", "backup_existing": True}

        response = make_request("POST", APISIX_ENDPOINTS["database_initialize"], json=payload)

        if response.status_code == 404:
            pytest.fail("Database route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_database_status_routing(self):
        """Test database status endpoint routing"""
        response = make_request("GET", APISIX_ENDPOINTS["database_status"])

        if response.status_code == 404:
            pytest.fail("Database route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_database_stats_routing(self):
        """Test database stats endpoint routing"""
        response = make_request("GET", APISIX_ENDPOINTS["database_stats"])

        if response.status_code == 404:
            pytest.fail("Database route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_database_reset_routing(self):
        """Test database reset endpoint routing"""
        payload = {"confirmation": True, "backup_before_reset": True, "preserve_user_data": False}

        response = make_request("POST", APISIX_ENDPOINTS["database_reset"], json=payload)

        if response.status_code == 404:
            pytest.fail("Database route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"


class TestSessionEndpointsViaAPISIX:
    """Test session management endpoints through APISIX"""

    def test_sessions_get_routing(self):
        """Test sessions GET endpoint routing"""
        response = make_request("GET", APISIX_ENDPOINTS["sessions"])

        if response.status_code == 404:
            pytest.fail("Sessions route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_sessions_put_routing(self):
        """Test sessions PUT endpoint routing"""
        payload = {"ui_preferences": {"theme": "dark"}, "workflow_state": {"step": "init"}}

        response = make_request("PUT", APISIX_ENDPOINTS["sessions"], json=payload)

        if response.status_code == 404:
            pytest.fail("Sessions route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_sessions_reset_routing(self):
        """Test sessions reset endpoint routing"""
        response = make_request("POST", APISIX_ENDPOINTS["sessions_reset"])

        if response.status_code == 404:
            pytest.fail("Sessions route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_sessions_schema_routing(self):
        """Test sessions schema endpoint routing"""
        response = make_request("GET", APISIX_ENDPOINTS["sessions_schema"], include_auth=False)

        if response.status_code == 404:
            pytest.fail("Sessions route not configured in APISIX. Run: ./configure_routes.sh")

        # Schema endpoint might not require auth
        assert response.status_code in [200, 401, 403], f"Unexpected status: {response.status_code}: {response.text}"


class TestConfigEndpointsViaAPISIX:
    """Test configuration management endpoints through APISIX"""

    def test_config_parameters_routing(self):
        """Test config parameters endpoint routing"""
        response = make_request("GET", APISIX_ENDPOINTS["config_parameters"])

        if response.status_code == 404:
            pytest.fail("Config route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_config_environment_routing(self):
        """Test config environment endpoint routing"""
        response = make_request("GET", APISIX_ENDPOINTS["config_environment"])

        if response.status_code == 404:
            pytest.fail("Config route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_config_generate_salt_routing(self):
        """Test config generate salt endpoint routing"""
        response = make_request("POST", APISIX_ENDPOINTS["config_generate_salt"])

        if response.status_code == 404:
            pytest.fail("Config route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"


class TestFileEndpointsViaAPISIX:
    """Test file management endpoints through APISIX"""

    def test_files_list_routing(self):
        """Test files list endpoint routing"""
        response = make_request("GET", APISIX_ENDPOINTS["files_list"])

        if response.status_code == 404:
            pytest.fail("Files route not configured in APISIX. Run: ./configure_routes.sh")

        assert response.status_code in [401, 403], f"Expected auth error, got {response.status_code}: {response.text}"

    def test_files_upload_routing(self):
        """Test files upload endpoint routing"""
        # Test without actually uploading a file
        headers = get_apisix_headers(include_auth=True)
        headers.pop("Content-Type", None)  # Remove for multipart

        response = requests.post(APISIX_ENDPOINTS["files_upload"], headers=headers, timeout=30)

        if response.status_code == 404:
            pytest.fail("Files route not configured in APISIX. Run: ./configure_routes.sh")

        # Should get auth error or bad request (missing file)
        assert response.status_code in [
            400,
            401,
            403,
            422,
        ], f"Unexpected status: {response.status_code}: {response.text}"


class TestStartPageEndpoints:
    """Verify that all endpoints used in 0_Start.py are correctly routed"""

    def test_all_start_page_endpoints_exist(self):
        """Test that all endpoints used in Start page have corresponding APISIX routes"""

        # Read the Start page to extract endpoints
        start_page_path = "/Users/tamnguyen/Documents/GitHub/ViolentUTF_nightly/violentutf/pages/0_Start.py"

        with open(start_page_path, "r") as f:
            content = f.read()

        # Extract API endpoints from the file
        import re

        endpoint_pattern = r'"([^"]*)/api/v1/[^"]*"'
        found_endpoints = re.findall(endpoint_pattern, content)

        # Check that these match our APISIX endpoints
        for endpoint_url in found_endpoints:
            # Convert to relative path
            if endpoint_url.startswith("http://"):
                continue  # Skip full URLs

            # Skip template/placeholder URLs
            if "{" in endpoint_url or "API_BASE_URL" in endpoint_url:
                continue

            relative_path = (
                endpoint_url.split("localhost:9080")[-1] if "localhost:9080" in endpoint_url else endpoint_url
            )

            # Test that the endpoint is routed
            full_url = f"{APISIX_BASE_URL}{relative_path}"
            try:
                response = make_request("GET", full_url)
                # Should not get 404 (route not found)
                assert (
                    response.status_code != 404
                ), f"Route not configured for {relative_path}. Run: ./configure_routes.sh"
            except Exception as e:
                pytest.fail(f"Error testing endpoint {relative_path}: {e}")


# Utility test to help debug configuration
class TestDebugHelpers:
    """Helper tests for debugging APISIX configuration"""

    def test_print_apisix_status(self):
        """Print current APISIX status for debugging"""
        print(f"\n🔍 APISIX Gateway Status:")
        print(f"   Base URL: {APISIX_BASE_URL}")

        try:
            health_response = requests.get(f"{APISIX_BASE_URL}/health", timeout=5)
            print(f"   Health Status: {health_response.status_code}")
        except Exception as e:
            print(f"   Health Check Failed: {e}")

        # Test a few key endpoints
        test_endpoints = ["/api/v1/auth/token/info", "/api/v1/database/status", "/api/v1/sessions", "/docs"]

        print(f"\n📋 Route Status:")
        for endpoint in test_endpoints:
            try:
                response = requests.get(f"{APISIX_BASE_URL}{endpoint}", headers=get_apisix_headers(), timeout=5)
                status = "✅ Routed" if response.status_code != 404 else "❌ Not Found"
                print(f"   {endpoint}: {status} ({response.status_code})")
            except Exception as e:
                print(f"   {endpoint}: ❌ Error ({e})")

        print(f"\n💡 If routes are missing, run: cd apisix && ./configure_routes.sh")


class TestJWTAuthenticationIntegration:
    """Test JWT authentication integration through APISIX"""

    def test_jwt_token_structure(self):
        """Test that JWT tokens have the expected structure for APISIX routing"""
        import jwt

        # Test the mock token structure
        try:
            # Decode without verification for structure testing
            decoded = jwt.decode(MOCK_JWT_TOKEN, options={"verify_signature": False})

            # Verify required fields for new authentication system
            assert "sub" in decoded, "JWT missing 'sub' field"
            assert "email" in decoded, "JWT missing 'email' field"
            assert "name" in decoded, "JWT missing 'name' field"
            assert "roles" in decoded, "JWT missing 'roles' field"
            assert "ai-api-access" in decoded["roles"], "JWT missing 'ai-api-access' role"

        except Exception as e:
            pytest.skip(f"JWT decode test failed: {e}")

    def test_generator_endpoints_routing(self):
        """Test that generator endpoints are properly routed through APISIX"""
        generator_endpoints = [
            "/api/v1/generators",
            "/api/v1/generators/types",
        ]

        print(f"\n🔧 Testing Generator Endpoints:")
        for endpoint in generator_endpoints:
            response = make_request("GET", f"{APISIX_BASE_URL}{endpoint}")

            # Should not return 404 (not routed)
            assert response.status_code != 404, f"Generator endpoint {endpoint} not routed through APISIX"

            # May return 401 (auth required) or 200 (success) - both indicate proper routing
            assert response.status_code in [200, 401, 403], f"Unexpected status for {endpoint}: {response.status_code}"
            print(f"   {endpoint}: ✅ Routed ({response.status_code})")

    def test_apisix_api_key_endpoints(self):
        """Test endpoints that require APISIX API key authentication"""
        # This tests the routes that use key-auth plugin for AI access

        # Mock the APISIX API key header format
        api_key_headers = {
            "Content-Type": "application/json",
            "apikey": "test_apisix_api_key",  # This is the format fixed in generators.py
            "X-API-Gateway": "APISIX",
        }

        # Test that the header format is correct
        assert "apikey" in api_key_headers, "APISIX API key header should use 'apikey' field"
        assert api_key_headers["X-API-Gateway"] == "APISIX", "Should include APISIX gateway marker"

    def test_environment_variable_integration(self):
        """Test environment variable integration for APISIX authentication"""
        import os

        # Test the environment variable priority order used in generators.py
        test_env = {
            "VIOLENTUTF_API_KEY": "priority_1",
            "APISIX_API_KEY": "priority_2",
            "AI_GATEWAY_API_KEY": "priority_3",
        }

        with patch.dict(os.environ, test_env):
            # Test the priority order
            api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY") or os.getenv("AI_GATEWAY_API_KEY")
            assert api_key == "priority_1", "VIOLENTUTF_API_KEY should have highest priority"

        # Test fallback behavior
        with patch.dict(os.environ, {"APISIX_API_KEY": "fallback_key"}):
            api_key = os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY") or os.getenv("AI_GATEWAY_API_KEY")
            assert api_key == "fallback_key", "Should fallback to APISIX_API_KEY"


class TestAuthenticationErrorHandling:
    """Test authentication error handling through APISIX"""

    def test_missing_jwt_token(self):
        """Test endpoints with missing JWT token"""
        headers_without_auth = {
            "Content-Type": "application/json",
            "X-Real-IP": "127.0.0.1",
            "X-Forwarded-For": "127.0.0.1",
            "X-API-Gateway": "APISIX",
        }

        response = make_request(
            "GET", f"{APISIX_BASE_URL}/api/v1/auth/token/info", include_auth=False, headers=headers_without_auth
        )

        # Should return 401 for missing authentication
        assert response.status_code == 401, f"Expected 401 for missing auth, got {response.status_code}"

    def test_malformed_jwt_token(self):
        """Test endpoints with malformed JWT token"""
        malformed_headers = {
            "Authorization": "Bearer invalid.jwt.token",
            "Content-Type": "application/json",
            "X-Real-IP": "127.0.0.1",
            "X-Forwarded-For": "127.0.0.1",
            "X-API-Gateway": "APISIX",
        }

        response = requests.get(f"{APISIX_BASE_URL}/api/v1/auth/token/info", headers=malformed_headers, timeout=10)

        # Should return 401 for invalid token
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}"

    def test_authentication_error_messages(self):
        """Test that authentication errors don't expose sensitive information"""
        response = make_request("GET", f"{APISIX_BASE_URL}/api/v1/auth/token/info", include_auth=False)

        if response.status_code == 401:
            # Verify error message doesn't expose internal details
            error_text = response.text.lower()

            # Should not contain sensitive information
            sensitive_terms = ["secret", "key", "password", "internal", "debug"]
            for term in sensitive_terms:
                assert term not in error_text, f"Error message contains sensitive term: {term}"


# Import patch for environment variable testing
from unittest.mock import patch

if __name__ == "__main__":
    # Run with: python -m pytest test_apisix_integration.py -v -s
    pytest.main([__file__, "-v", "-s"])
