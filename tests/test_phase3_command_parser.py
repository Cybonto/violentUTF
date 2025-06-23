#!/usr/bin/env python3
"""
Phase 3: Command Parser Tests
Tests for natural language command parsing and MCP command recognition
"""

import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from violentutf.utils.mcp_integration import (
    NaturalLanguageParser,
    ConfigurationIntentDetector,
    MCPCommandType,
    MCPCommand
)


class TestNaturalLanguageParser(unittest.TestCase):
    """Test natural language command parsing"""
    
    def setUp(self):
        self.parser = NaturalLanguageParser()
    
    def test_explicit_help_command(self):
        """Test parsing /mcp help command"""
        command = self.parser.parse("/mcp help")
        self.assertEqual(command.type, MCPCommandType.HELP)
        self.assertEqual(command.arguments, {})
    
    def test_explicit_test_commands(self):
        """Test parsing /mcp test commands with parameters"""
        test_cases = [
            ("/mcp test jailbreak", "jailbreak"),
            ("/mcp test bias", "bias"),
            ("/mcp test privacy", "privacy")
        ]
        
        for cmd_text, expected_type in test_cases:
            with self.subTest(command=cmd_text):
                command = self.parser.parse(cmd_text)
                self.assertEqual(command.type, MCPCommandType.TEST)
                self.assertEqual(command.arguments.get('test_type'), expected_type)
    
    def test_dataset_commands(self):
        """Test parsing dataset commands"""
        test_cases = [
            "/mcp dataset harmbench",
            "load dataset jailbreak-prompts",
            "use harmful-content dataset"
        ]
        
        for cmd_text in test_cases:
            with self.subTest(command=cmd_text):
                command = self.parser.parse(cmd_text)
                self.assertEqual(command.type, MCPCommandType.DATASET)
                self.assertIn('dataset_name', command.arguments)
    
    def test_enhance_commands(self):
        """Test parsing enhance commands"""
        test_cases = [
            "/mcp enhance",
            "enhance this prompt",
            "improve this prompt",
            "make this prompt better"
        ]
        
        for cmd_text in test_cases:
            with self.subTest(command=cmd_text):
                command = self.parser.parse(cmd_text)
                self.assertEqual(command.type, MCPCommandType.ENHANCE)
    
    def test_analyze_commands(self):
        """Test parsing analyze commands"""
        test_cases = [
            "/mcp analyze",
            "analyze this prompt",
            "analyze for security",
            "find bias issues"
        ]
        
        for cmd_text in test_cases:
            with self.subTest(command=cmd_text):
                command = self.parser.parse(cmd_text)
                self.assertEqual(command.type, MCPCommandType.ANALYZE)
    
    def test_unknown_command(self):
        """Test parsing unknown commands"""
        command = self.parser.parse("this is just regular text")
        self.assertEqual(command.type, MCPCommandType.UNKNOWN)
    
    def test_case_insensitive_parsing(self):
        """Test that commands are parsed case-insensitively"""
        test_cases = [
            "/MCP HELP",
            "/Mcp Help",
            "/mcp HELP"
        ]
        
        for cmd_text in test_cases:
            with self.subTest(command=cmd_text):
                command = self.parser.parse(cmd_text)
                self.assertEqual(command.type, MCPCommandType.HELP)
    
    def test_command_suggestions(self):
        """Test command suggestion functionality"""
        suggestions = self.parser.suggest_command("/mcp")
        self.assertIsInstance(suggestions, list)
        self.assertTrue(len(suggestions) > 0)
        self.assertIn("/mcp help", suggestions)
    
    def test_parameter_extraction(self):
        """Test extracting parameters from natural language"""
        test_cases = [
            ("temperature 0.7", {"temperature": 0.7}),
            ("temp=0.5", {"temperature": 0.5}),
            ("max tokens 1000", {"max_tokens": 1000}),
            ("creative mode", {"temperature": 0.9}),
            ("focused response", {"temperature": 0.3})
        ]
        
        for text, expected_params in test_cases:
            with self.subTest(text=text):
                params = self.parser.extract_parameters(text)
                for key, value in expected_params.items():
                    self.assertIn(key, params)
                    self.assertEqual(params[key], value)


class TestConfigurationIntentDetector(unittest.TestCase):
    """Test configuration intent detection"""
    
    def setUp(self):
        self.detector = ConfigurationIntentDetector()
    
    def test_generator_intent_detection(self):
        """Test detecting generator configuration intents"""
        test_cases = [
            ("Create a GPT-4 generator", "create"),
            ("Set up a new Claude model", "create"),
            ("Configure OpenAI generator", "create")
        ]
        
        for text, expected_action in test_cases:
            with self.subTest(text=text):
                intent = self.detector.detect_configuration_intent(text)
                self.assertIsNotNone(intent)
                self.assertEqual(intent['type'], 'generator')
                self.assertEqual(intent['action'], expected_action)
    
    def test_dataset_intent_detection(self):
        """Test detecting dataset configuration intents"""
        test_cases = [
            ("Load the jailbreak dataset", "load", "jailbreak"),
            ("Load harmful content data", "load", "harmful-content"),
            ("Create a new dataset", "create", "custom")
        ]
        
        for text, expected_action, expected_target in test_cases:
            with self.subTest(text=text):
                intent = self.detector.detect_configuration_intent(text)
                self.assertIsNotNone(intent)
                self.assertEqual(intent['type'], 'dataset')
                self.assertEqual(intent['action'], expected_action)
                self.assertEqual(intent['target'], expected_target)
    
    def test_orchestrator_intent_detection(self):
        """Test detecting orchestrator configuration intents"""
        test_cases = [
            "Set up a red team test",
            "Create a new orchestrator",
            "Run security testing pipeline"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                intent = self.detector.detect_configuration_intent(text)
                self.assertIsNotNone(intent)
                self.assertEqual(intent['type'], 'orchestrator')
                self.assertEqual(intent['action'], 'create')
    
    def test_scorer_intent_detection(self):
        """Test detecting scorer configuration intents"""
        test_cases = [
            ("Configure a bias scorer", "bias"),
            ("Set up security evaluation", "security"),
            ("Create harmful content scorer", "harmful")
        ]
        
        for text, expected_target in test_cases:
            with self.subTest(text=text):
                intent = self.detector.detect_configuration_intent(text)
                self.assertIsNotNone(intent)
                self.assertEqual(intent['type'], 'scorer')
                self.assertEqual(intent['action'], 'configure')
                self.assertEqual(intent['target'], expected_target)
    
    def test_no_intent_detection(self):
        """Test that regular text doesn't trigger intent detection"""
        test_cases = [
            "Hello, how are you?",
            "What's the weather like?",
            "Tell me a joke"
        ]
        
        for text in test_cases:
            with self.subTest(text=text):
                intent = self.detector.detect_configuration_intent(text)
                self.assertIsNone(intent)
    
    def test_extract_generator_params(self):
        """Test extracting generator parameters from natural language"""
        test_cases = [
            ("Create a GPT-4 generator with temperature 0.7", {
                "model": "gpt-4",
                "temperature": 0.7
            }),
            ("Set up OpenAI GPT-3.5 model", {
                "model": "gpt-3.5-turbo",
                "provider": "openai"
            }),
            ("Configure Anthropic Claude with temp 0.5", {
                "model": "claude-3",
                "provider": "anthropic",
                "temperature": 0.5
            })
        ]
        
        for text, expected_params in test_cases:
            with self.subTest(text=text):
                params = self.detector.extract_generator_params(text)
                for key, value in expected_params.items():
                    self.assertIn(key, params)
                    self.assertEqual(params[key], value)


class TestMCPCommandStructure(unittest.TestCase):
    """Test MCPCommand data structure"""
    
    def test_command_creation(self):
        """Test creating MCPCommand objects"""
        command = MCPCommand(
            type=MCPCommandType.HELP,
            subcommand="test",
            arguments={"param": "value"},
            raw_text="/mcp help test"
        )
        
        self.assertEqual(command.type, MCPCommandType.HELP)
        self.assertEqual(command.subcommand, "test")
        self.assertEqual(command.arguments, {"param": "value"})
        self.assertEqual(command.raw_text, "/mcp help test")
    
    def test_command_default_arguments(self):
        """Test that arguments default to empty dict"""
        command = MCPCommand(type=MCPCommandType.TEST)
        self.assertEqual(command.arguments, {})


if __name__ == '__main__':
    unittest.main()