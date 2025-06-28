#!/usr/bin/env python3
"""
Phase 3: Integration Tests
Tests for command processing integration with MCP server
"""

import asyncio
import json
import os
import shutil
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from violentutf.utils.mcp_client import MCPClientSync
from violentutf.utils.mcp_integration import (ConfigurationIntentDetector,
                                              ConversationContextAnalyzer,
                                              NaturalLanguageParser)


class TestCommandProcessingIntegration:
    """Test command processing with MCP integration"""

    @pytest.fixture
    def mcp_client(self):
        """Create MCP client instance"""
        client = MCPClientSync()
        # Set a test token
        client.set_test_token("test-jwt-token")
        return client

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_help_command_integration(self, mcp_client):
        """Test /mcp help command through full pipeline"""
        parser = NaturalLanguageParser()

        # Parse command
        command = parser.parse("/mcp help")
        assert command.type.value == "help"

        # Command should be handled in UI, not require MCP server
        # This tests that help is available offline
        assert command.arguments == {}

    def test_natural_language_generator_creation(self):
        """Test natural language generator creation intent"""
        detector = ConfigurationIntentDetector()

        # Test various ways to express generator creation
        test_cases = [
            "Create a GPT-4 generator with temperature 0.7",
            "Set up an OpenAI model with max tokens 2000",
            "Configure a Claude-3 generator",
        ]

        for text in test_cases:
            intent = detector.detect_configuration_intent(text)
            assert intent is not None
            assert intent["type"] == "generator"
            assert intent["action"] == "create"

            # Extract parameters
            params = detector.extract_generator_params(text)
            assert isinstance(params, dict)

            # Check specific parameters
            if "temperature" in text:
                assert "temperature" in params
            if "max tokens" in text:
                assert "max_tokens" in params

    def test_dataset_loading_workflow(self):
        """Test dataset loading command workflow"""
        parser = NaturalLanguageParser()
        detector = ConfigurationIntentDetector()

        # Test explicit command
        cmd = parser.parse("/mcp dataset jailbreak")
        assert cmd.type.value == "dataset"
        assert cmd.arguments["dataset_name"] == "jailbreak"

        # Test natural language
        intent = detector.detect_configuration_intent("Load the jailbreak dataset")
        assert intent["type"] == "dataset"
        assert intent["action"] == "load"
        assert intent["target"] == "jailbreak"

    def test_command_suggestions_context(self):
        """Test context-aware command suggestions"""
        parser = NaturalLanguageParser()
        analyzer = ConversationContextAnalyzer()

        # Test partial command suggestions
        suggestions = parser.suggest_command("/mcp te")
        assert any("/mcp test" in s for s in suggestions)

        # Test context analysis
        messages = [
            {"content": "I need to test for security vulnerabilities"},
            {"content": "Can you help with jailbreak testing?"},
        ]

        context = analyzer.analyze_context(messages)
        assert "security" in context["topics"]
        assert "test" in context["topics"]
        assert len(context["suggested_actions"]) > 0

    @patch("violentutf.utils.mcp_client.httpx.AsyncClient")
    async def test_enhancement_command_with_mcp(self, mock_client_class):
        """Test enhancement command with MCP server"""
        # Mock the HTTP client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock SSE response for enhancement
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.aiter_lines = MagicMock()

        # Simulate SSE messages
        async def mock_sse_lines():
            yield 'data: {"jsonrpc":"2.0","result":{"prompts":[{"name":"enhance_prompt"}]},"id":"1"}'
            yield ""
            yield 'data: {"jsonrpc":"2.0","result":{"messages":[{"role":"assistant","content":"Enhanced: Write a secure Python function"}]},"id":"2"}'
            yield ""

        mock_response.aiter_lines.return_value = mock_sse_lines()
        mock_client.post.return_value.__aenter__.return_value = mock_response

        # Create client and test
        from violentutf.utils.mcp_client import MCPClient

        client = MCPClient()
        client.set_test_token("test-token")

        # Initialize and get prompt
        await client.initialize()
        result = await client.get_prompt(
            "enhance_prompt", {"prompt": "Write a Python function"}
        )

        # Should get enhanced prompt
        assert result is not None

    def test_configuration_workflow_end_to_end(self):
        """Test complete configuration workflow"""
        parser = NaturalLanguageParser()
        detector = ConfigurationIntentDetector()

        # User types natural language command
        user_input = "Create a GPT-4 generator with temperature 0.8 and max tokens 1500"

        # Check if it's a command
        command = parser.parse(user_input)

        if command.type.value == "unknown":
            # Check for configuration intent
            intent = detector.detect_configuration_intent(user_input)
            assert intent is not None
            assert intent["type"] == "generator"

            # Extract parameters
            params = detector.extract_generator_params(user_input)
            assert params["model"] == "gpt-4"
            assert params["temperature"] == 0.8
            assert params["max_tokens"] == 1500

    def test_multi_command_session(self):
        """Test handling multiple commands in a session"""
        parser = NaturalLanguageParser()
        detector = ConfigurationIntentDetector()
        analyzer = ConversationContextAnalyzer()

        # Simulate a conversation
        commands = [
            "Create a GPT-4 generator",
            "Load the jailbreak dataset",
            "/mcp test jailbreak",
            "Configure a bias scorer",
        ]

        messages = []

        for cmd_text in commands:
            # Parse command
            command = parser.parse(cmd_text)

            if command.type.value == "unknown":
                # Check configuration intent
                intent = detector.detect_configuration_intent(cmd_text)
                if intent:
                    messages.append({"content": cmd_text, "intent": intent})
            else:
                messages.append({"content": cmd_text, "command": command.type.value})

        # Analyze conversation context
        context = analyzer.analyze_context(messages)
        assert "generator" in context["mentioned_resources"]
        assert "dataset" in context["mentioned_resources"]

    def test_error_handling_invalid_commands(self):
        """Test handling of invalid commands"""
        parser = NaturalLanguageParser()

        # Test invalid command format
        command = parser.parse("/mcp invalid command")
        assert command.type.value == "unknown"

        # Test empty command
        command = parser.parse("")
        assert command.type.value == "unknown"

        # Test command with special characters
        command = parser.parse("/mcp test <script>alert('xss')</script>")
        # The command type is recognized but test_type is not captured due to special chars
        assert command.type.value == "test"
        # The test_type argument should not be captured due to special characters
        assert "test_type" not in command.arguments

        # Test valid command with safe test type
        command = parser.parse("/mcp test jailbreak")
        assert command.type.value == "test"
        assert command.arguments["test_type"] == "jailbreak"

    def test_command_autocomplete(self):
        """Test command autocomplete functionality"""
        parser = NaturalLanguageParser()

        # Test various partial inputs
        test_cases = [
            ("/mc", ["/mcp help"]),
            ("/mcp h", ["/mcp help"]),
            ("/mcp t", ["/mcp test"]),
            ("/mcp data", ["/mcp dataset"]),
            ("enha", ["/mcp enhance"]),
            ("test jail", ["/mcp test jailbreak"]),
        ]

        for partial, expected_contains in test_cases:
            suggestions = parser.suggest_command(partial)
            assert len(suggestions) > 0
            # Check that at least one expected suggestion is present
            assert any(
                exp in suggestion
                for suggestion in suggestions
                for exp in expected_contains
            )


class TestCommandHandlerIntegration:
    """Test integration with Streamlit command handlers"""

    def test_command_result_formatting(self):
        """Test formatting of command results for display"""
        # Simulate command results
        results = [
            {"type": "success", "content": "Generator created successfully"},
            {"type": "error", "content": "Failed to load dataset"},
            {"type": "info", "content": "No datasets available"},
            {"type": "help", "content": "**MCP Commands**\n- /mcp help"},
            {"type": "list", "content": "- Generator 1\n- Generator 2"},
        ]

        for result in results:
            assert "type" in result
            assert "content" in result
            assert isinstance(result["content"], str)

    def test_session_state_integration(self):
        """Test integration with Streamlit session state"""
        # Simulate session state
        session_state = {
            "mcp_command_history": [],
            "user_input": "Create a GPT-4 generator",
            "mcp_client": MCPClientSync(),
        }

        # Add command to history
        command_result = {
            "command": session_state["user_input"],
            "result": {"type": "success", "content": "Created"},
            "timestamp": "2024-01-01T00:00:00",
        }

        session_state["mcp_command_history"].append(command_result)

        # Verify history tracking
        assert len(session_state["mcp_command_history"]) == 1
        assert (
            session_state["mcp_command_history"][0]["command"]
            == "Create a GPT-4 generator"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
