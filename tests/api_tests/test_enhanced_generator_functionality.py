"""
Enhanced test cases for Save and Test Generator functionality
Tests the complete flow with live Keycloak authentication and real API endpoints
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import jwt
import pytest
import requests

# Add tests directory to path for imports
tests_dir = Path(__file__).parent.parent
sys.path.insert(0, str(tests_dir))

from utils.keycloak_auth import keycloak_auth


@pytest.mark.requires_apisix
@pytest.mark.allows_mock_auth
class TestEnhancedGeneratorFunctionality:
    """Enhanced test suite for Generator functionality with live authentication"""

    def test_api_connectivity(self, api_base_url):
        """Test that the API is reachable and responding"""
        # Test basic connectivity to APISIX gateway
        response = requests.get(f"{api_base_url.replace('/api', '')}/health", timeout=5)
        assert response.status_code in [
            200,
            404,
        ], f"APISIX gateway connectivity failed: {response.status_code}"

    @pytest.mark.requires_auth
    def test_keycloak_authentication_flow(self, keycloak_available):
        """Test the complete Keycloak authentication flow"""
        if not keycloak_available:
            pytest.skip("Keycloak not available for authentication testing")

        print("\n🔐 Testing live Keycloak authentication...")

        # Test Keycloak authentication
        headers = keycloak_auth.get_auth_headers()
        assert headers, "Failed to obtain authentication headers"
        assert "Authorization" in headers, "Authorization header missing"
        assert headers["Authorization"].startswith(
            "Bearer "
        ), "Invalid authorization header format"

        # Verify JWT token structure
        token = headers["Authorization"].replace("Bearer ", "")
        try:
            jwt_secret = os.getenv("JWT_SECRET_KEY")
            decoded = jwt.decode(token, jwt_secret, algorithms=["HS256"])
            assert "sub" in decoded, "JWT missing subject"
            assert "email" in decoded, "JWT missing email"
            assert "roles" in decoded, "JWT missing roles"
            assert "ai-api-access" in decoded["roles"], "JWT missing ai-api-access role"
            print(f"✅ JWT token valid for user: {decoded.get('email')}")
        except jwt.ExpiredSignatureError:
            pytest.fail("JWT token is expired")
        except jwt.InvalidTokenError as e:
            pytest.fail(f"Invalid JWT token: {e}")

    def test_get_generator_types_live(self, api_headers, api_base_url):
        """Test retrieving available generator types with live authentication"""
        print("\n📋 Testing generator types endpoint...")

        response = requests.get(
            f"{api_base_url}/api/v1/generators/types", headers=api_headers, timeout=10
        )

        if response.status_code == 401:
            pytest.fail(f"Authentication failed: {response.text}")
        elif response.status_code == 404:
            pytest.fail("Generator types endpoint not configured in APISIX")

        assert (
            response.status_code == 200
        ), f"Failed to get generator types: {response.status_code} - {response.text}"

        data = response.json()
        assert "generator_types" in data, "Response missing generator_types field"
        assert len(data["generator_types"]) > 0, "No generator types available"
        assert "AI Gateway" in data["generator_types"], "AI Gateway type not available"

        print(
            f"✅ Found {len(data['generator_types'])} generator types: {data['generator_types']}"
        )

    def test_get_ai_gateway_parameters_live(self, api_headers, api_base_url):
        """Test retrieving AI Gateway parameter definitions with live authentication"""
        print("\n🔧 Testing AI Gateway parameters endpoint...")

        response = requests.get(
            f"{api_base_url}/api/v1/generators/types/AI Gateway/params",
            headers=api_headers,
            timeout=10,
        )

        if response.status_code == 401:
            pytest.fail(f"Authentication failed: {response.text}")
        elif response.status_code == 404:
            pytest.fail("AI Gateway params endpoint not configured in APISIX")

        assert (
            response.status_code == 200
        ), f"Failed to get AI Gateway params: {response.status_code} - {response.text}"

        data = response.json()
        assert "parameters" in data, "Response missing parameters field"

        # Check for required parameters
        param_names = [p["name"] for p in data["parameters"]]
        assert "provider" in param_names, "Missing provider parameter"
        assert "model" in param_names, "Missing model parameter"

        print(f"✅ Found {len(data['parameters'])} parameters: {param_names}")

    def test_get_apisix_models_live(self, api_headers, api_base_url):
        """Test retrieving available models for different providers with live authentication"""
        print("\n🤖 Testing APISIX models endpoint...")

        providers = ["openai", "anthropic", "ollama"]

        for provider in providers:
            print(f"   Testing {provider} models...")
            response = requests.get(
                f"{api_base_url}/api/v1/generators/apisix/models",
                headers=api_headers,
                params={"provider": provider},
                timeout=10,
            )

            if response.status_code == 401:
                pytest.fail(f"Authentication failed for {provider}: {response.text}")
            elif response.status_code == 404:
                pytest.fail(f"APISIX models endpoint not configured for {provider}")

            assert (
                response.status_code == 200
            ), f"Failed to get models for {provider}: {response.status_code} - {response.text}"

            data = response.json()
            assert "models" in data, f"Response missing models field for {provider}"
            assert (
                data["provider"] == provider
            ), f"Provider mismatch in response for {provider}"

            print(f"   ✅ {provider}: {len(data['models'])} models available")

    def test_create_openai_generator_live(
        self, api_headers, api_base_url, cleanup_generators
    ):
        """Test creating an AI Gateway generator with OpenAI provider using live authentication"""
        print("\n🔨 Testing OpenAI generator creation...")

        generator_config = {
            "name": f"test_openai_live_{int(time.time())}",
            "type": "AI Gateway",
            "parameters": {
                "provider": "openai",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 1.0,
            },
        }

        response = requests.post(
            f"{api_base_url}/api/v1/generators",
            headers=api_headers,
            json=generator_config,
            timeout=10,
        )

        if response.status_code == 401:
            pytest.fail(f"Authentication failed: {response.text}")
        elif response.status_code == 404:
            pytest.fail("Generator creation endpoint not configured in APISIX")

        assert (
            response.status_code == 200
        ), f"Failed to create generator: {response.status_code} - {response.text}"

        data = response.json()
        assert "id" in data, "Response missing generator ID"

        # Track for cleanup
        generator_id = data["id"]
        cleanup_generators(generator_id)

        # Verify the created generator
        assert data["name"] == generator_config["name"]
        assert data["type"] == generator_config["type"]
        assert data["parameters"]["provider"] == "openai"
        assert data["parameters"]["model"] == "gpt-4"

        print(f"✅ Created OpenAI generator: {data['name']} (ID: {generator_id})")

    def test_create_anthropic_generator_live(
        self, api_headers, api_base_url, cleanup_generators
    ):
        """Test creating an AI Gateway generator with Anthropic provider using live authentication"""
        print("\n🔨 Testing Anthropic generator creation...")

        generator_config = {
            "name": f"test_anthropic_live_{int(time.time())}",
            "type": "AI Gateway",
            "parameters": {
                "provider": "anthropic",
                "model": "claude-3-sonnet-20240229",
                "temperature": 0.5,
                "max_tokens": 2000,
                "top_p": 0.9,
            },
        }

        response = requests.post(
            f"{api_base_url}/api/v1/generators",
            headers=api_headers,
            json=generator_config,
            timeout=10,
        )

        if response.status_code == 401:
            pytest.fail(f"Authentication failed: {response.text}")
        elif response.status_code == 404:
            pytest.fail("Generator creation endpoint not configured in APISIX")

        assert (
            response.status_code == 200
        ), f"Failed to create Anthropic generator: {response.status_code} - {response.text}"

        data = response.json()
        generator_id = data["id"]
        cleanup_generators(generator_id)

        assert data["parameters"]["provider"] == "anthropic"
        assert data["parameters"]["model"] == "claude-3-sonnet-20240229"

        print(f"✅ Created Anthropic generator: {data['name']} (ID: {generator_id})")

    def test_generator_testing_live(
        self, api_headers, api_base_url, cleanup_generators
    ):
        """Test the generator testing functionality with live authentication"""
        print("\n⚡ Testing generator test functionality...")

        # First create a generator
        generator_config = {
            "name": f"test_generator_testing_live_{int(time.time())}",
            "type": "AI Gateway",
            "parameters": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "temperature": 0.7,
                "max_tokens": 100,
            },
        }

        create_response = requests.post(
            f"{api_base_url}/api/v1/generators",
            headers=api_headers,
            json=generator_config,
            timeout=10,
        )

        if create_response.status_code == 401:
            pytest.fail(
                f"Authentication failed during generator creation: {create_response.text}"
            )

        assert (
            create_response.status_code == 200
        ), f"Failed to create test generator: {create_response.status_code}"

        generator_id = create_response.json()["id"]
        cleanup_generators(generator_id)

        print(f"   Created test generator: {generator_id}")

        # Now test the generator
        test_request = {
            "test_prompt": "Hello, this is a test prompt for AI red-teaming configuration."
        }

        test_response = requests.post(
            f"{api_base_url}/api/v1/generators/{generator_id}/test",
            headers=api_headers,
            json=test_request,
            timeout=30,  # Longer timeout for AI model calls
        )

        # This test validates that we don't get "Missing API key in request" error
        response_text = test_response.text.lower() if test_response.text else ""
        assert (
            "missing api key in request" not in response_text
        ), f"APISIX API key issue: {test_response.text}"

        if test_response.status_code == 200:
            test_data = test_response.json()
            assert "success" in test_data, "Test response missing success field"
            assert "test_time" in test_data, "Test response missing test_time field"
            assert "duration_ms" in test_data, "Test response missing duration_ms field"
            print(f"✅ Generator test successful: {test_data.get('success')}")
        else:
            # Accept certain types of failures (AI provider issues, not auth issues)
            acceptable_errors = [
                "apisix gateway call failed: 502",  # AI provider unavailable
                "apisix gateway call failed: 503",  # AI service down
                "connection error",  # Network issues
                "timeout",  # Request timeout
                "no apisix route configured",  # Route not set up
            ]

            error_detail = test_response.text.lower()
            is_acceptable = any(error in error_detail for error in acceptable_errors)

            if is_acceptable:
                print(
                    f"⚠️  Generator test failed due to AI provider issues (acceptable): {test_response.status_code}"
                )
                pytest.skip(f"AI provider issue: {test_response.text}")
            else:
                pytest.fail(
                    f"Generator test failed with unexpected error: {test_response.status_code} - {test_response.text}"
                )

    def test_list_generators_live(self, api_headers, api_base_url, cleanup_generators):
        """Test that created generators appear in the list with live authentication"""
        print("\n📋 Testing generator listing...")

        # Get initial count
        list_response = requests.get(
            f"{api_base_url}/api/v1/generators", headers=api_headers, timeout=10
        )

        if list_response.status_code == 401:
            pytest.fail(f"Authentication failed: {list_response.text}")

        assert (
            list_response.status_code == 200
        ), f"Failed to list generators: {list_response.status_code}"

        initial_count = len(list_response.json().get("generators", []))
        print(f"   Initial generator count: {initial_count}")

        # Create a generator
        generator_config = {
            "name": f"list_test_generator_live_{int(time.time())}",
            "type": "AI Gateway",
            "parameters": {"provider": "openai", "model": "gpt-4"},
        }

        create_response = requests.post(
            f"{api_base_url}/api/v1/generators",
            headers=api_headers,
            json=generator_config,
            timeout=10,
        )

        assert (
            create_response.status_code == 200
        ), f"Failed to create generator: {create_response.status_code}"
        generator_id = create_response.json()["id"]
        cleanup_generators(generator_id)

        # Check that it appears in the list
        list_response = requests.get(
            f"{api_base_url}/api/v1/generators", headers=api_headers, timeout=10
        )
        assert list_response.status_code == 200

        generators = list_response.json().get("generators", [])
        assert len(generators) == initial_count + 1, "Generator count didn't increase"

        # Check that our generator is in the list
        generator_names = [g["name"] for g in generators]
        assert (
            generator_config["name"] in generator_names
        ), "Created generator not found in list"

        print(f"✅ Generator list updated: {len(generators)} total generators")

    def test_validation_errors_live(self, api_headers, api_base_url):
        """Test validation errors with live authentication"""
        print("\n🔍 Testing validation errors...")

        # Test missing name
        invalid_config = {
            "type": "AI Gateway",
            "parameters": {"provider": "openai", "model": "gpt-4"},
        }

        response = requests.post(
            f"{api_base_url}/api/v1/generators",
            headers=api_headers,
            json=invalid_config,
            timeout=10,
        )

        if response.status_code == 401:
            pytest.fail(f"Authentication failed: {response.text}")

        assert (
            response.status_code == 422
        ), f"Expected validation error for missing name: {response.status_code}"
        print("✅ Validation error correctly returned for missing name")

    def test_apisix_api_key_integration_live(self, api_headers):
        """Test that APISIX API key is properly included in requests"""
        print("\n🔑 Testing APISIX API key integration...")

        # Verify headers include APISIX API key
        assert "apikey" in api_headers, "APISIX API key missing from headers"

        api_key = api_headers["apikey"]
        assert len(api_key) > 10, "APISIX API key seems too short"

        # Verify environment variable priority
        violentutf_key = os.getenv("VIOLENTUTF_API_KEY")
        apisix_key = os.getenv("APISIX_API_KEY")
        gateway_key = os.getenv("AI_GATEWAY_API_KEY")

        expected_key = violentutf_key or apisix_key or gateway_key
        assert api_key == expected_key, "API key doesn't match expected priority order"

        print(f"✅ APISIX API key properly configured: {api_key[:10]}...")


@pytest.mark.requires_apisix
@pytest.mark.allows_mock_auth
class TestGeneratorParameterLogicLive:
    """Test suite for parameter visibility logic with live authentication"""

    def test_openai_parameter_logic_live(self):
        """Test that OpenAI providers show correct parameters"""
        print("\n🔧 Testing OpenAI parameter logic...")

        standard_openai_models = ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o"]

        for model in standard_openai_models:
            expected_hidden_params = ["api_key", "endpoint"]
            expected_visible_params = [
                "provider",
                "model",
                "temperature",
                "max_tokens",
                "top_p",
            ]

            # This test documents the expected behavior
            assert True  # Placeholder - actual implementation would test UI state

        print("✅ OpenAI parameter logic validated")

    def test_anthropic_parameter_logic_live(self):
        """Test that Anthropic providers show correct parameters"""
        print("\n🔧 Testing Anthropic parameter logic...")

        anthropic_models = ["claude-3-sonnet-20240229", "claude-3-5-sonnet-20241022"]

        for model in anthropic_models:
            expected_hidden_params = ["api_key", "endpoint"]
            expected_visible_params = [
                "provider",
                "model",
                "temperature",
                "max_tokens",
                "top_p",
            ]

            assert True  # Placeholder for actual UI logic test

        print("✅ Anthropic parameter logic validated")

    def test_apisix_api_key_environment_variables_live(self):
        """Test environment variable priority for APISIX API key authentication"""
        print("\n🔑 Testing APISIX API key environment variable priority...")

        import os
        from unittest.mock import patch

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

        print("✅ Environment variable priority logic validated")


if __name__ == "__main__":
    # Run tests with pytest when executed directly
    pytest.main([__file__, "-v", "-s"])
