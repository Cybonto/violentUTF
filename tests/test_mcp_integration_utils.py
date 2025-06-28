"""
Unit Tests for MCP Integration Utilities
=======================================

Tests for natural language parsing and command interpretation.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from violentutf.utils.mcp_integration import (
    NaturalLanguageParser,
    MCPCommand,
    MCPCommandType,
    ContextAnalyzer,
    ConfigurationIntentDetector,
)


class TestNaturalLanguageParser:
    """Test natural language command parsing"""

    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return NaturalLanguageParser()

    def test_parse_mcp_help_command(self, parser):
        """Test parsing help commands"""
        test_cases = ["/mcp help", "show mcp commands", "what can mcp do", "mcp usage"]

        for text in test_cases:
            command = parser.parse_command(text)
            assert command.type == MCPCommandType.HELP
            assert command.raw_text == text

    def test_parse_test_commands(self, parser):
        """Test parsing test commands"""
        command = parser.parse_command("/mcp test jailbreak")
        assert command.type == MCPCommandType.TEST
        assert command.arguments["test_type"] == "jailbreak"

        command = parser.parse_command("run security test")
        assert command.type == MCPCommandType.TEST
        assert command.arguments["test_type"] == "security"

        command = parser.parse_command("test for bias")
        assert command.type == MCPCommandType.TEST
        assert command.arguments["test_type"] == "bias"

    def test_parse_dataset_commands(self, parser):
        """Test parsing dataset commands"""
        command = parser.parse_command("/mcp dataset jailbreak-v1")
        assert command.type == MCPCommandType.DATASET
        assert command.arguments["dataset_name"] == "jailbreak-v1"

        command = parser.parse_command("load dataset harmful-behaviors")
        assert command.type == MCPCommandType.DATASET
        assert command.arguments["dataset_name"] == "harmful-behaviors"

    def test_parse_enhance_commands(self, parser):
        """Test parsing enhance commands"""
        test_cases = ["/mcp enhance", "enhance this prompt", "improve this prompt", "make this prompt better"]

        for text in test_cases:
            command = parser.parse_command(text)
            assert command.type == MCPCommandType.ENHANCE

    def test_parse_unknown_command(self, parser):
        """Test parsing unknown commands"""
        command = parser.parse_command("random text")
        assert command.type == MCPCommandType.UNKNOWN

        command = parser.parse_command("/mcp invalid")
        assert command.type == MCPCommandType.UNKNOWN

    def test_extract_parameters(self, parser):
        """Test parameter extraction from natural language"""
        params = parser.extract_parameters("create a generator with temperature 0.8 and max_tokens 1000")
        assert params.get("temperature") == 0.8
        assert params.get("max_tokens") == 1000

        params = parser.extract_parameters("use gpt-4 model with top_p 0.9")
        assert params.get("model") == "gpt-4"
        assert params.get("top_p") == 0.9

    def test_detect_mcp_intent(self, parser):
        """Test MCP intent detection"""
        assert parser.detect_mcp_intent("I want to enhance my prompt") is True
        assert parser.detect_mcp_intent("analyze this for security issues") is True
        assert parser.detect_mcp_intent("load the jailbreak dataset") is True
        assert parser.detect_mcp_intent("hello world") is False

    def test_get_command_suggestions(self, parser):
        """Test command suggestions"""
        suggestions = parser.get_command_suggestions("enh")
        assert any("enhance" in s.lower() for s in suggestions)

        suggestions = parser.get_command_suggestions("test")
        assert any("test" in s.lower() for s in suggestions)

        suggestions = parser.get_command_suggestions("")
        assert len(suggestions) > 0  # Should return some default suggestions


class TestConfigurationIntentDetector:
    """Test configuration intent detection"""

    @pytest.fixture
    def detector(self):
        """Create detector instance"""
        return ConfigurationIntentDetector()

    def test_detect_generator_creation(self, detector):
        """Test detecting generator creation intent"""
        test_cases = [
            ("Create a GPT-4 generator", True),
            ("I want to create an OpenAI generator with GPT-4", True),
            ("Set up a new generator for Claude", True),
            ("Configure a generator with temperature 0.7", True),
            ("Hello world", False),
            ("What is a generator?", False),
        ]

        for text, expected in test_cases:
            intent = detector.detect_configuration_intent(text)
            if expected:
                assert intent is not None
                assert intent["type"] == "generator"
                assert intent["action"] == "create"
            else:
                assert intent is None or intent["type"] != "generator"

    def test_extract_generator_params(self, detector):
        """Test extracting generator parameters"""
        params = detector.extract_generator_params("Create a GPT-4 generator with temperature 0.8")
        assert params.get("model") == "gpt-4"
        assert params.get("temperature") == 0.8

        params = detector.extract_generator_params("OpenAI generator using gpt-3.5-turbo with max_tokens 2000")
        assert params.get("provider") == "openai"
        assert params.get("model") == "gpt-3.5-turbo"
        assert params.get("max_tokens") == 2000

    def test_detect_dataset_operations(self, detector):
        """Test detecting dataset operations"""
        intent = detector.detect_configuration_intent("Load the jailbreak dataset")
        assert intent["type"] == "dataset"
        assert intent["action"] == "load"
        assert intent["target"] == "jailbreak"

        intent = detector.detect_configuration_intent("Create a new dataset from CSV")
        assert intent["type"] == "dataset"
        assert intent["action"] == "create"

    def test_detect_orchestrator_setup(self, detector):
        """Test detecting orchestrator setup"""
        text = "Run a red team test on GPT-4 using jailbreak dataset"
        intent = detector.detect_configuration_intent(text)
        assert intent["type"] == "orchestrator"
        assert intent["action"] == "create"
        assert "gpt-4" in intent.get("details", "").lower()
        assert "jailbreak" in intent.get("details", "").lower()

    def test_detect_scorer_configuration(self, detector):
        """Test detecting scorer configuration"""
        intent = detector.detect_configuration_intent("Configure bias scorer")
        assert intent["type"] == "scorer"
        assert intent["action"] == "configure"
        assert intent["target"] == "bias"

        intent = detector.detect_configuration_intent("Set up security scoring")
        assert intent["type"] == "scorer"
        assert "security" in intent.get("details", "").lower()


class TestContextAnalyzer:
    """Test context analysis functionality"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return ContextAnalyzer()

    def test_analyze_empty_context(self, analyzer):
        """Test analyzing empty context"""
        analysis = analyzer.analyze_context([])
        assert analysis["message_count"] == 0
        assert analysis["topics"] == []
        assert analysis["suggested_actions"] == []

    def test_analyze_security_context(self, analyzer):
        """Test analyzing security-focused context"""
        messages = [
            {"role": "user", "content": "I need to test for jailbreak vulnerabilities"},
            {"role": "assistant", "content": "I can help you test for jailbreak vulnerabilities"},
            {"role": "user", "content": "What datasets should I use?"},
        ]

        analysis = analyzer.analyze_context(messages)
        assert analysis["message_count"] == 3
        assert "jailbreak" in analysis["topics"]
        assert "security" in analysis["topics"] or "test" in analysis["topics"]
        assert len(analysis["suggested_actions"]) > 0

        # Should suggest dataset-related actions
        assert any("dataset" in action.lower() for action in analysis["suggested_actions"])

    def test_detect_incomplete_workflow(self, analyzer):
        """Test detecting incomplete configuration workflow"""
        messages = [
            {"role": "user", "content": "I created a GPT-4 generator"},
            {"role": "assistant", "content": "Generator created successfully"},
        ]

        analysis = analyzer.analyze_context(messages)

        # Should suggest next steps like testing or creating orchestrator
        suggestions = analysis["suggested_actions"]
        assert any("test" in s.lower() or "orchestrator" in s.lower() for s in suggestions)

    def test_resource_tracking(self, analyzer):
        """Test tracking mentioned resources"""
        messages = [
            {"role": "user", "content": "Load the jailbreak dataset"},
            {"role": "assistant", "content": "Loaded jailbreak dataset"},
            {"role": "user", "content": "Also load the bias-test dataset"},
        ]

        analysis = analyzer.analyze_context(messages)
        resources = analysis.get("mentioned_resources", [])

        assert "jailbreak" in str(resources).lower()
        assert "bias-test" in str(resources).lower()


class TestMCPCommand:
    """Test MCPCommand dataclass"""

    def test_command_creation(self):
        """Test creating MCP command"""
        command = MCPCommand(
            type=MCPCommandType.ENHANCE,
            subcommand="aggressive",
            arguments={"level": "high"},
            raw_text="/mcp enhance aggressive",
        )

        assert command.type == MCPCommandType.ENHANCE
        assert command.subcommand == "aggressive"
        assert command.arguments["level"] == "high"
        assert command.raw_text == "/mcp enhance aggressive"

    def test_command_defaults(self):
        """Test command default values"""
        command = MCPCommand(type=MCPCommandType.HELP)

        assert command.type == MCPCommandType.HELP
        assert command.subcommand is None
        assert command.arguments == {}
        assert command.raw_text == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
