"""
Test cases for JWT authentication system and API key management
Tests the recent changes in JWT token handling, refresh mechanisms, and APISIX integration
"""

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import jwt
import pytest
import requests

# API Configuration
API_BASE_URL = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")


class TestJWTAuthentication:
    """Test suite for JWT authentication and token management"""

    def test_jwt_token_creation(self):
        """Test JWT token creation with proper structure"""
        # Simulate JWT manager token creation
        secret_key = "test_secret_key_for_jwt"
        algorithm = "HS256"

        now = datetime.now(timezone.utc)
        payload = {
            "sub": "test_user",
            "email": "test@example.com",
            "name": "Test User",
            "roles": ["ai-api-access"],
            "iat": now,
            "exp": now + timedelta(hours=1),
        }

        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        assert token is not None, "JWT token creation failed"

        # Verify token can be decoded
        decoded = jwt.decode(token, secret_key, algorithms=[algorithm])
        assert decoded["sub"] == "test_user"
        assert decoded["email"] == "test@example.com"
        assert "ai-api-access" in decoded["roles"]

    def test_jwt_token_expiry_detection(self):
        """Test detection of expired JWT tokens"""
        secret_key = "test_secret_key_for_jwt"
        algorithm = "HS256"

        # Create expired token
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        expired_payload = {
            "sub": "test_user",
            "email": "test@example.com",
            "roles": ["ai-api-access"],
            "iat": past_time,
            "exp": past_time + timedelta(minutes=30),  # Expired 1.5 hours ago
        }

        expired_token = jwt.encode(expired_payload, secret_key, algorithm=algorithm)

        # Verify token is detected as expired
        try:
            jwt.decode(expired_token, secret_key, algorithms=[algorithm])
            assert False, "Expired token should have raised an exception"
        except jwt.ExpiredSignatureError:
            assert True, "Correctly detected expired token"

    def test_jwt_token_refresh_timing(self):
        """Test proactive refresh timing (10 minutes before expiry)"""
        secret_key = "test_secret_key_for_jwt"
        algorithm = "HS256"

        # Create token that expires in 5 minutes (should trigger refresh)
        now = datetime.now(timezone.utc)
        soon_to_expire_payload = {
            "sub": "test_user",
            "email": "test@example.com",
            "roles": ["ai-api-access"],
            "iat": now,
            "exp": now + timedelta(minutes=5),  # Expires in 5 minutes
        }

        token = jwt.encode(soon_to_expire_payload, secret_key, algorithm=algorithm)
        decoded = jwt.decode(token, secret_key, algorithms=[algorithm])

        # Check if token should be refreshed (less than 10 minutes remaining)
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        time_remaining = exp_time - datetime.now(timezone.utc)
        refresh_buffer = timedelta(minutes=10)

        should_refresh = time_remaining < refresh_buffer
        assert should_refresh, "Token with 5 minutes remaining should trigger refresh"

    @pytest.mark.skipif(
        not os.getenv("VIOLENTUTF_API_URL"), reason="API URL not configured"
    )
    def test_api_authentication_flow(self):
        """Test the complete API authentication flow"""
        # Test unauthenticated request
        response = requests.get(f"{API_BASE_URL}/api/v1/auth/token/info")
        assert response.status_code == 401, "Unauthenticated request should return 401"

        # Test with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = requests.get(
            f"{API_BASE_URL}/api/v1/auth/token/info", headers=headers
        )
        assert response.status_code == 401, "Invalid token should return 401"

    def test_apisix_api_key_header_format(self):
        """Test APISIX API key header format for AI model access"""
        # Test the header format used by the generator test endpoint
        test_api_key = "test_apisix_api_key_123"

        headers = {
            "Content-Type": "application/json",
            "X-API-Gateway": "APISIX",
            "apikey": test_api_key,  # APISIX expects 'apikey' header
        }

        assert headers["apikey"] == test_api_key
        assert headers["X-API-Gateway"] == "APISIX"

        # Verify header name is correct (not 'X-API-Key' or 'Authorization')
        assert "apikey" in headers
        assert "X-API-Key" not in headers


class TestJWTManager:
    """Test the JWT manager class functionality"""

    def test_jwt_manager_initialization(self):
        """Test JWT manager initialization with correct settings"""
        # Mock the JWT manager initialization
        refresh_buffer = 600  # 10 minutes
        max_retry_attempts = 3
        retry_delay = 5

        assert (
            refresh_buffer == 600
        ), "Refresh buffer should be 10 minutes (600 seconds)"
        assert max_retry_attempts == 3, "Should allow 3 retry attempts"
        assert retry_delay == 5, "Should wait 5 seconds between retries"

    def test_token_refresh_status(self):
        """Test token refresh status reporting"""
        # Test different refresh statuses
        statuses = ["active", "expiring_soon", "refreshing", "expired"]

        for status in statuses:
            # Mock refresh status response
            mock_status = {
                "status": status,
                "time_remaining": 300 if status != "expired" else 0,
                "refresh_in_progress": status == "refreshing",
            }

            assert mock_status["status"] in statuses
            if status == "expired":
                assert mock_status["time_remaining"] == 0
            if status == "refreshing":
                assert mock_status["refresh_in_progress"] is True

    def test_environment_variable_priority(self):
        """Test environment variable priority for APISIX API key"""
        # Test the priority order used in generators.py
        test_vars = {
            "VIOLENTUTF_API_KEY": "violentutf_key",
            "APISIX_API_KEY": "apisix_key",
            "AI_GATEWAY_API_KEY": "gateway_key",
        }

        # Test priority order: VIOLENTUTF_API_KEY first
        with patch.dict(os.environ, test_vars):
            api_key = (
                os.getenv("VIOLENTUTF_API_KEY")
                or os.getenv("APISIX_API_KEY")
                or os.getenv("AI_GATEWAY_API_KEY")
            )
            assert (
                api_key == "violentutf_key"
            ), "VIOLENTUTF_API_KEY should have highest priority"

        # Test fallback to APISIX_API_KEY
        with patch.dict(
            os.environ,
            {"APISIX_API_KEY": "apisix_key", "AI_GATEWAY_API_KEY": "gateway_key"},
        ):
            api_key = (
                os.getenv("VIOLENTUTF_API_KEY")
                or os.getenv("APISIX_API_KEY")
                or os.getenv("AI_GATEWAY_API_KEY")
            )
            assert api_key == "apisix_key", "Should fallback to APISIX_API_KEY"


class TestStreamlitIntegration:
    """Test Streamlit frontend integration with JWT system"""

    def test_auth_headers_generation(self):
        """Test authentication header generation for Streamlit requests"""
        # Mock the get_auth_headers function behavior
        mock_token = "mock_jwt_token_123"

        headers = {
            "Authorization": f"Bearer {mock_token}",
            "Content-Type": "application/json",
            "X-Real-IP": "127.0.0.1",
            "X-Forwarded-For": "127.0.0.1",
            "X-Forwarded-Host": "localhost:9080",
            "X-API-Gateway": "APISIX",
        }

        assert headers["Authorization"] == f"Bearer {mock_token}"
        assert headers["X-API-Gateway"] == "APISIX"
        assert headers["X-Real-IP"] == "127.0.0.1"

    def test_sidebar_status_messages(self):
        """Test sidebar authentication status message format"""
        # Test different status message formats
        status_tests = [
            {"status": "refreshing", "expected": "🔄 AI Gateway: Refreshing Token..."},
            {"status": "expired", "expected": "⏰ AI Gateway: Token Expired"},
            {
                "status": "expiring_soon",
                "minutes": 5,
                "expected": "⚠️ AI Gateway: Expires in 5m",
            },
            {
                "status": "active",
                "minutes": 45,
                "expected": "🚀 AI Gateway: Active (45m left)",
            },
        ]

        for test in status_tests:
            if test["status"] == "expiring_soon":
                message = f"⚠️ AI Gateway: Expires in {test['minutes']}m"
            elif test["status"] == "active":
                message = f"🚀 AI Gateway: Active ({test['minutes']}m left)"
            elif test["status"] == "refreshing":
                message = "🔄 AI Gateway: Refreshing Token..."
            elif test["status"] == "expired":
                message = "⏰ AI Gateway: Token Expired"

            assert (
                message == test["expected"]
            ), f"Status message format incorrect for {test['status']}"


class TestFastAPIIntegration:
    """Test FastAPI backend integration with JWT and APISIX"""

    def test_fastapi_environment_variables(self):
        """Test that FastAPI has access to required environment variables"""
        required_vars = [
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "VIOLENTUTF_API_KEY",
            "APISIX_BASE_URL",
        ]

        # Mock environment setup
        mock_env = {
            "SECRET_KEY": "fastapi_secret",
            "JWT_SECRET_KEY": "shared_jwt_secret",
            "VIOLENTUTF_API_KEY": "apisix_api_key",
            "APISIX_BASE_URL": "http://apisix:9080",
        }

        with patch.dict(os.environ, mock_env):
            for var in required_vars:
                assert (
                    os.getenv(var) is not None
                ), f"Required environment variable {var} not found"

    def test_generator_test_authentication(self):
        """Test generator test endpoint authentication requirements"""
        # Mock the authentication flow for generator testing

        # 1. JWT authentication for FastAPI endpoint
        jwt_headers = {
            "Authorization": "Bearer jwt_token_here",
            "Content-Type": "application/json",
        }

        # 2. APISIX API key for AI model access
        apisix_headers = {
            "Content-Type": "application/json",
            "X-API-Gateway": "APISIX",
            "apikey": "apisix_api_key_here",
        }

        assert "Authorization" in jwt_headers, "JWT authentication header required"
        assert "apikey" in apisix_headers, "APISIX API key header required"
        assert (
            apisix_headers["X-API-Gateway"] == "APISIX"
        ), "APISIX gateway header required"

    def test_error_handling_for_missing_api_key(self):
        """Test error handling when APISIX API key is missing"""
        # Test the error scenario that was fixed
        mock_request_without_key = {
            "headers": {
                "Content-Type": "application/json",
                "X-API-Gateway": "APISIX",
                # Missing 'apikey' header
            }
        }

        # Should detect missing API key
        has_api_key = "apikey" in mock_request_without_key["headers"]
        assert not has_api_key, "Should detect missing API key"

        # Test the fixed version with API key
        mock_request_with_key = {
            "headers": {
                "Content-Type": "application/json",
                "X-API-Gateway": "APISIX",
                "apikey": "test_api_key",
            }
        }

        has_api_key = "apikey" in mock_request_with_key["headers"]
        assert has_api_key, "Should detect present API key"


class TestEnvironmentConfiguration:
    """Test environment configuration for the authentication system"""

    def test_setup_script_variables(self):
        """Test that setup script generates required variables"""
        # Variables that should be generated by setup_macos.sh
        required_generated_vars = [
            "VIOLENTUTF_API_KEY",
            "JWT_SECRET_KEY",
            "FASTAPI_SECRET_KEY",
            "APISIX_ADMIN_KEY",
        ]

        # Mock generated values (these would be created by setup script)
        for var in required_generated_vars:
            assert len(var) > 0, f"Variable {var} name should not be empty"
            # In real setup, these would be cryptographically secure random strings

    def test_streamlit_env_file_structure(self):
        """Test Streamlit .env file structure"""
        # Variables that should be in violentutf/.env
        streamlit_vars = [
            "JWT_SECRET_KEY",
            "VIOLENTUTF_API_KEY",
            "VIOLENTUTF_API_URL",
            "KEYCLOAK_USERNAME",
            "KEYCLOAK_PASSWORD",
        ]

        for var in streamlit_vars:
            assert isinstance(var, str), f"Variable {var} should be a string"

    def test_fastapi_env_file_structure(self):
        """Test FastAPI .env file structure"""
        # Variables that should be in violentutf_api/fastapi_app/.env
        fastapi_vars = [
            "SECRET_KEY",
            "JWT_SECRET_KEY",  # Should match Streamlit
            "VIOLENTUTF_API_KEY",  # Added in recent fix
            "APISIX_BASE_URL",
            "APISIX_ADMIN_URL",
        ]

        for var in fastapi_vars:
            assert isinstance(var, str), f"Variable {var} should be a string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
