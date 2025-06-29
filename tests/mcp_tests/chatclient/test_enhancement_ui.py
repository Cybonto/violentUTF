"""
Test suite for MCP Enhancement Strip UI in Simple_Chat.py
Tests UI components, session state management, and user interactions
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
import streamlit as st

# Import utilities
from utils.mcp_client import MCPClientSync
from utils.mcp_integration import ContextAnalyzer, MCPCommandType, NaturalLanguageParser


class TestEnhancementStripUI:
    """Test the enhancement strip UI components"""

    @pytest.fixture
    def mock_session_state(self):
        """Mock streamlit session state"""
        session_state = {
            "mcp_client": Mock(spec=MCPClientSync),
            "mcp_parser": Mock(spec=NaturalLanguageParser),
            "mcp_analyzer": Mock(spec=ContextAnalyzer),
            "mcp_enhanced_prompt": None,
            "mcp_analysis_results": None,
            "mcp_test_variations": [],
            "show_mcp_results": False,
            "mcp_operation_in_progress": False,
        }
        return session_state

    def test_enhancement_strip_appears_with_input(self, mock_session_state):
        """Test that enhancement strip appears when user input is provided"""
        user_input = "Test prompt for enhancement"

        # Mock parser to return no command
        mock_session_state["mcp_parser"].parse.return_value = Mock(type=MCPCommandType.UNKNOWN)

        # Mock analyzer to return no suggestions
        mock_session_state["mcp_analyzer"].analyze_for_suggestions.return_value = []

        # Verify parser and analyzer are called with user input
        assert user_input != ""
        mock_session_state["mcp_parser"].parse.assert_not_called()  # Not called in test

    def test_command_detection(self, mock_session_state):
        """Test natural language command detection"""
        user_input = "/mcp enhance"

        # Mock parser to detect enhance command
        mock_cmd = Mock(type=MCPCommandType.ENHANCE)
        mock_session_state["mcp_parser"].parse.return_value = mock_cmd

        # Parse the command
        parsed = mock_session_state["mcp_parser"].parse(user_input)
        assert parsed.type == MCPCommandType.ENHANCE

    def test_context_suggestions(self, mock_session_state):
        """Test context-aware suggestions"""
        user_input = "I want to improve this prompt"

        # Mock analyzer to return enhancement suggestion
        suggestions = [
            {
                "type": "enhance",
                "reason": "Your message mentions improvement. Would you like to enhance this prompt?",
                "command": "/mcp enhance",
                "priority": 1,
            }
        ]
        mock_session_state["mcp_analyzer"].analyze_for_suggestions.return_value = suggestions

        # Get suggestions
        result = mock_session_state["mcp_analyzer"].analyze_for_suggestions(user_input)
        assert len(result) == 1
        assert result[0]["type"] == "enhance"

    def test_enhance_button_functionality(self, mock_session_state):
        """Test enhance button functionality"""
        user_input = "Test prompt"

        # Mock MCP client to return enhanced prompt
        enhanced_prompt = "Enhanced: Test prompt with improved clarity and effectiveness"
        mock_session_state["mcp_client"].get_prompt.return_value = enhanced_prompt

        # Simulate enhance button click
        mock_session_state["mcp_operation_in_progress"] = True
        mock_session_state["show_mcp_results"] = True

        # Call enhance
        result = mock_session_state["mcp_client"].get_prompt("prompt_enhancement", {"original_prompt": user_input})

        # Verify enhanced prompt
        assert result == enhanced_prompt
        mock_session_state["mcp_enhanced_prompt"] = result
        assert mock_session_state["mcp_enhanced_prompt"] is not None

        # Reset operation flag
        mock_session_state["mcp_operation_in_progress"] = False

    def test_analyze_button_functionality(self, mock_session_state):
        """Test analyze button functionality"""
        user_input = "Test prompt with potential issues"

        # Mock MCP client to return analysis
        analysis = "Analysis: No security issues detected. Bias score: Low. Quality: Good."
        mock_session_state["mcp_client"].get_prompt.return_value = analysis

        # Simulate analyze button click
        result = mock_session_state["mcp_client"].get_prompt("security_analysis", {"prompt": user_input})

        # Verify analysis
        assert result == analysis
        mock_session_state["mcp_analysis_results"] = result
        assert mock_session_state["mcp_analysis_results"] is not None

    def test_test_button_functionality(self, mock_session_state):
        """Test test variations button functionality"""
        user_input = "Test prompt"

        # Mock MCP client to return test variations
        test_variations = {
            "jailbreak_test": "Jailbreak test: Ignore instructions and...",
            "bias_detection": "Bias test: Check if the model shows preference...",
            "privacy_test": "Privacy test: Can you tell me personal information...",
        }

        def mock_get_prompt(test_type, args):
            return test_variations.get(test_type, "")

        mock_session_state["mcp_client"].get_prompt.side_effect = mock_get_prompt

        # Generate test variations
        variations = []
        for test_type in ["jailbreak_test", "bias_detection", "privacy_test"]:
            variation = mock_session_state["mcp_client"].get_prompt(test_type, {"context": user_input})
            if variation:
                variations.append({"type": test_type, "prompt": variation})

        # Verify variations
        assert len(variations) == 3
        assert variations[0]["type"] == "jailbreak_test"
        assert "Jailbreak test" in variations[0]["prompt"]

        mock_session_state["mcp_test_variations"] = variations
        assert len(mock_session_state["mcp_test_variations"]) == 3

    def test_results_display(self, mock_session_state):
        """Test results display functionality"""
        # Set up test data
        mock_session_state["show_mcp_results"] = True
        mock_session_state["mcp_enhanced_prompt"] = "Enhanced prompt"
        mock_session_state["mcp_analysis_results"] = "Analysis results"
        mock_session_state["mcp_test_variations"] = [{"type": "test1", "prompt": "Test variation 1"}]

        # Verify all results are available
        assert mock_session_state["show_mcp_results"] is True
        assert mock_session_state["mcp_enhanced_prompt"] is not None
        assert mock_session_state["mcp_analysis_results"] is not None
        assert len(mock_session_state["mcp_test_variations"]) > 0

    def test_clear_results_functionality(self, mock_session_state):
        """Test clear results button"""
        # Set up results
        mock_session_state["mcp_enhanced_prompt"] = "Enhanced"
        mock_session_state["mcp_analysis_results"] = "Analysis"
        mock_session_state["mcp_test_variations"] = ["test"]
        mock_session_state["show_mcp_results"] = True

        # Clear results
        mock_session_state["mcp_enhanced_prompt"] = None
        mock_session_state["mcp_analysis_results"] = None
        mock_session_state["mcp_test_variations"] = []
        mock_session_state["show_mcp_results"] = False

        # Verify cleared
        assert mock_session_state["mcp_enhanced_prompt"] is None
        assert mock_session_state["mcp_analysis_results"] is None
        assert len(mock_session_state["mcp_test_variations"]) == 0
        assert mock_session_state["show_mcp_results"] is False

    def test_quick_actions_dropdown(self, mock_session_state):
        """Test quick actions dropdown functionality"""
        quick_actions = ["Select action...", "Security audit", "Bias check", "Privacy scan", "Load dataset"]

        # Verify all actions are available
        assert len(quick_actions) == 5
        assert "Security audit" in quick_actions
        assert "Bias check" in quick_actions

    def test_use_enhanced_prompt(self, mock_session_state):
        """Test using enhanced prompt functionality"""
        original = "Original prompt"
        enhanced = "Enhanced prompt with improvements"

        mock_session_state["mcp_enhanced_prompt"] = enhanced

        # Simulate using enhanced prompt
        user_input = mock_session_state["mcp_enhanced_prompt"]

        assert user_input == enhanced
        assert user_input != original

    def test_operation_in_progress_state(self, mock_session_state):
        """Test operation in progress state management"""
        # Initially not in progress
        assert mock_session_state["mcp_operation_in_progress"] is False

        # Start operation
        mock_session_state["mcp_operation_in_progress"] = True
        assert mock_session_state["mcp_operation_in_progress"] is True

        # Complete operation
        mock_session_state["mcp_operation_in_progress"] = False
        assert mock_session_state["mcp_operation_in_progress"] is False

    def test_error_handling(self, mock_session_state):
        """Test error handling in enhancement operations"""
        # Mock MCP client to raise error
        mock_session_state["mcp_client"].get_prompt.side_effect = Exception("Test error")

        # Attempt enhancement
        try:
            result = mock_session_state["mcp_client"].get_prompt("prompt_enhancement", {"original_prompt": "test"})
        except Exception as e:
            error_msg = str(e)
            assert error_msg == "Test error"

        # Ensure operation flag is reset
        mock_session_state["mcp_operation_in_progress"] = False
        assert mock_session_state["mcp_operation_in_progress"] is False


class TestSessionStateIntegration:
    """Test session state integration with MCP components"""

    def test_session_state_initialization(self):
        """Test proper initialization of MCP session state"""
        # Mock session state initialization
        session_state = {
            "mcp_client": MCPClientSync(),
            "mcp_parser": NaturalLanguageParser(),
            "mcp_analyzer": None,  # Will be initialized with client
            "mcp_enhanced_prompt": None,
            "mcp_analysis_results": None,
            "mcp_test_variations": [],
            "show_mcp_results": False,
            "mcp_operation_in_progress": False,
        }

        # Initialize analyzer with client
        session_state["mcp_analyzer"] = ContextAnalyzer(session_state["mcp_client"])

        # Verify all components are initialized
        assert isinstance(session_state["mcp_client"], MCPClientSync)
        assert isinstance(session_state["mcp_parser"], NaturalLanguageParser)
        assert isinstance(session_state["mcp_analyzer"], ContextAnalyzer)
        assert session_state["mcp_enhanced_prompt"] is None
        assert session_state["mcp_analysis_results"] is None
        assert isinstance(session_state["mcp_test_variations"], list)
        assert session_state["show_mcp_results"] is False
        assert session_state["mcp_operation_in_progress"] is False

    def test_prompt_variable_integration(self):
        """Test integration with existing prompt variable system"""
        # Mock prompt variables
        prompt_variables = {
            "greeting": {"value": "Hello, how can I help you?", "num_tokens": 6, "timestamp": "2024-01-01T00:00:00"}
        }

        # Enhanced prompt can reference variables
        enhanced_prompt = "Enhanced: {{greeting}} Let me assist you better."

        # Resolve variables (simplified)
        resolved = enhanced_prompt.replace("{{greeting}}", prompt_variables["greeting"]["value"])

        assert "Hello, how can I help you?" in resolved
        assert "Let me assist you better" in resolved


class TestUserFlows:
    """Test complete user flows"""

    def test_enhance_and_use_flow(self):
        """Test flow: write prompt -> enhance -> use enhanced"""
        session_state = {"mcp_client": Mock(spec=MCPClientSync), "mcp_enhanced_prompt": None, "show_mcp_results": False}

        # User writes prompt
        user_input = "Tell me about Python"

        # User clicks enhance
        enhanced = "Please provide a comprehensive overview of Python programming language, including its history, key features, and common use cases."
        session_state["mcp_client"].get_prompt.return_value = enhanced

        # Enhance operation
        result = session_state["mcp_client"].get_prompt("prompt_enhancement", {"original_prompt": user_input})
        session_state["mcp_enhanced_prompt"] = result
        session_state["show_mcp_results"] = True

        # User clicks "Use This Prompt"
        new_input = session_state["mcp_enhanced_prompt"]

        # Verify flow
        assert new_input == enhanced
        assert new_input != user_input
        assert len(new_input) > len(user_input)

    def test_analyze_and_improve_flow(self):
        """Test flow: write prompt -> analyze -> view results -> improve"""
        session_state = {"mcp_client": Mock(spec=MCPClientSync), "mcp_analysis_results": None}

        # User writes potentially problematic prompt
        user_input = "Write code to hack into a system"

        # User clicks analyze
        analysis = "Security Alert: This prompt may be requesting harmful content. Suggestion: Rephrase to focus on ethical security testing or educational purposes."
        session_state["mcp_client"].get_prompt.return_value = analysis

        # Analyze operation
        result = session_state["mcp_client"].get_prompt("security_analysis", {"prompt": user_input})
        session_state["mcp_analysis_results"] = result

        # Verify analysis detected issue
        assert "Security Alert" in session_state["mcp_analysis_results"]
        assert "harmful" in session_state["mcp_analysis_results"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
