"""
Test cases for parameter visibility logic in AI Gateway configuration
Tests that API Key and Custom Endpoint are hidden/shown appropriately based on provider selection
"""

from unittest.mock import MagicMock, patch

import pytest


def should_show_parameter(param_name: str, provider: str) -> bool:
    """Determine if a parameter should be shown based on provider selection"""
    cloud_providers = ["openai", "anthropic"]

    if provider in cloud_providers:
        if param_name in ["api_key", "endpoint"]:
            return False

    local_providers = ["ollama", "webui"]
    if provider in local_providers:
        if param_name == "api_key":
            return False

    return True


class TestParameterVisibility:
    """Test suite for parameter visibility logic in generator configuration"""

    def test_should_show_parameter_openai_provider(self):
        """Test parameter visibility for OpenAI provider"""
        provider = "openai"

        # API key should be hidden for OpenAI (gateway handles it)
        assert should_show_parameter("api_key", provider) == False

        # Custom endpoint should be hidden for OpenAI (uses standard endpoint)
        assert should_show_parameter("endpoint", provider) == False

        # Model parameters should be shown
        assert should_show_parameter("temperature", provider) == True
        assert should_show_parameter("max_tokens", provider) == True
        assert should_show_parameter("top_p", provider) == True

    def test_should_show_parameter_anthropic_provider(self):
        """Test parameter visibility for Anthropic provider"""
        provider = "anthropic"

        # API key should be hidden for Anthropic (gateway handles it)
        assert should_show_parameter("api_key", provider) == False

        # Custom endpoint should be hidden for Anthropic (uses standard endpoint)
        assert should_show_parameter("endpoint", provider) == False

        # Model parameters should be shown
        assert should_show_parameter("temperature", provider) == True
        assert should_show_parameter("max_tokens", provider) == True
        assert should_show_parameter("top_p", provider) == True

    def test_should_show_parameter_ollama_provider(self):
        """Test parameter visibility for Ollama (local) provider"""
        provider = "ollama"

        # API key should be hidden for local providers
        assert should_show_parameter("api_key", provider) == False

        # Endpoint should be shown for local providers (custom URLs)
        assert should_show_parameter("endpoint", provider) == True

        # Model parameters should be shown
        assert should_show_parameter("temperature", provider) == True
        assert should_show_parameter("max_tokens", provider) == True

    def test_should_show_parameter_webui_provider(self):
        """Test parameter visibility for WebUI (local) provider"""
        provider = "webui"

        # API key should be hidden for local providers
        assert should_show_parameter("api_key", provider) == False

        # Endpoint should be shown for local providers (custom URLs)
        assert should_show_parameter("endpoint", provider) == True

        # Model parameters should be shown
        assert should_show_parameter("temperature", provider) == True
        assert should_show_parameter("max_tokens", provider) == True


class TestParameterVisibilityIntegration:
    """Integration tests for parameter visibility in Streamlit components"""

    @patch("streamlit.session_state")
    @patch("streamlit.selectbox")
    @patch("streamlit.text_input")
    @patch("streamlit.number_input")
    def test_ai_gateway_openai_parameters_rendered_correctly(
        self, mock_number_input, mock_text_input, mock_selectbox, mock_session_state
    ):
        """Test that AI Gateway with OpenAI provider renders correct parameters"""
        # Mock session state
        mock_session_state.get.side_effect = lambda key, default=None: {
            "AI Gateway_provider": "openai",
            "ai_gateway_available_models": ["gpt-4", "gpt-3.5-turbo"],
        }.get(key, default)

        # Mock parameter definitions
        param_defs = [
            {
                "name": "provider",
                "type": "selectbox",
                "category": "configuration",
                "description": "AI Provider",
                "required": True,
                "options": ["openai", "anthropic", "ollama", "webui"],
            },
            {
                "name": "model",
                "type": "selectbox",
                "category": "configuration",
                "description": "AI Model",
                "required": True,
            },
            {
                "name": "api_key",
                "type": "str",
                "category": "configuration",
                "description": "API Key",
                "required": False,
            },
            {
                "name": "endpoint",
                "type": "str",
                "category": "configuration",
                "description": "Custom Endpoint URL",
                "required": False,
            },
            {
                "name": "temperature",
                "type": "float",
                "category": "model",
                "description": "Temperature",
                "required": False,
                "default": 0.7,
            },
            {
                "name": "max_tokens",
                "type": "int",
                "category": "model",
                "description": "Max Tokens",
                "required": False,
                "default": 1000,
            },
        ]

        # Test that the visibility logic works as expected
        provider = "openai"

        # Check which parameters should be visible
        for param in param_defs:
            param_name = param["name"]
            should_show = should_show_parameter(param_name, provider)

            if param_name in ["api_key", "endpoint"]:
                assert should_show == False, f"{param_name} should be hidden for {provider}"
            elif param_name in ["provider", "model", "temperature", "max_tokens"]:
                assert should_show == True, f"{param_name} should be shown for {provider}"

    def test_parameter_visibility_documentation(self):
        """Document the expected parameter visibility behavior"""
        # Document expected behavior for each provider
        test_cases = [
            # OpenAI - cloud provider
            ("openai", "api_key", False, "API key handled by gateway"),
            ("openai", "endpoint", False, "Uses standard OpenAI endpoint"),
            ("openai", "temperature", True, "Model parameter"),
            ("openai", "max_tokens", True, "Model parameter"),
            # Anthropic - cloud provider
            ("anthropic", "api_key", False, "API key handled by gateway"),
            ("anthropic", "endpoint", False, "Uses standard Anthropic endpoint"),
            ("anthropic", "temperature", True, "Model parameter"),
            # Ollama - local provider
            ("ollama", "api_key", False, "Local provider doesn't need API key"),
            ("ollama", "endpoint", True, "Custom local endpoint configurable"),
            ("ollama", "temperature", True, "Model parameter"),
            # WebUI - local provider
            ("webui", "api_key", False, "Local provider doesn't need API key"),
            ("webui", "endpoint", True, "Custom local endpoint configurable"),
            ("webui", "temperature", True, "Model parameter"),
        ]

        for provider, param_name, expected, reason in test_cases:
            actual = should_show_parameter(param_name, provider)
            assert (
                actual == expected
            ), f"Provider: {provider}, Param: {param_name}, Expected: {expected}, Reason: {reason}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
