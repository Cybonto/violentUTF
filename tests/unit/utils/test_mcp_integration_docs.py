# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Unit tests for MCP integration documentation features
Tests the enhanced natural language parser with documentation queries
"""

import pytest

from violentutf.utils.mcp_integration import MCPCommand, MCPCommandType, NaturalLanguageParser


class TestDocumentationCommandParsing:
    """Test documentation command parsing in NaturalLanguageParser"""

    @pytest.fixture
    def parser(self):
        """Create a NaturalLanguageParser instance"""
        return NaturalLanguageParser()

    def test_explicit_documentation_commands(self, parser):
        """Test explicit /mcp docs commands"""
        test_cases = [
            ("/mcp docs setup", MCPCommandType.DOCUMENTATION, {"query": "setup"}),
            ("/mcp doc authentication", MCPCommandType.DOCUMENTATION, {"query": "authentication"}),
            ("/mcp documentation API guide", MCPCommandType.DOCUMENTATION, {"query": "API guide"}),
        ]

        for text, expected_type, expected_args in test_cases:
            result = parser.parse(text)
            assert result.type == expected_type
            assert result.arguments["query"] == expected_args["query"]
            assert result.raw_text == text

    def test_natural_language_documentation_queries(self, parser):
        """Test natural language patterns for documentation"""
        test_cases = [
            ("how do i setup ViolentUTF", MCPCommandType.DOCUMENTATION, "setup ViolentUTF"),
            ("how to configure authentication", MCPCommandType.DOCUMENTATION, "configure authentication"),
            ("what is MCP", MCPCommandType.DOCUMENTATION, "MCP"),
            ("guide for Docker setup", MCPCommandType.DOCUMENTATION, "Docker setup"),
            ("help me with API integration", MCPCommandType.DOCUMENTATION, "API integration"),
            ("troubleshooting Docker issues", MCPCommandType.DOCUMENTATION, "Docker issues"),
            ("setup keycloak", MCPCommandType.DOCUMENTATION, "keycloak"),
            ("configure APISIX", MCPCommandType.DOCUMENTATION, "APISIX"),
            ("install ViolentUTF", MCPCommandType.DOCUMENTATION, "ViolentUTF"),
        ]

        for text, expected_type, expected_query in test_cases:
            result = parser.parse(text)
            assert result.type == expected_type, f"Failed for: {text}"
            assert result.arguments["query"] == expected_query
            assert result.raw_text == text

    def test_search_commands(self, parser):
        """Test search command parsing"""
        test_cases = [
            ("/mcp search authentication", MCPCommandType.SEARCH, {"query": "authentication"}),
            ("search for Docker setup", MCPCommandType.SEARCH, {"query": "Docker setup"}),
            ("find information about API", MCPCommandType.SEARCH, {"query": "information about API"}),
            ("look up troubleshooting guide", MCPCommandType.SEARCH, {"query": "troubleshooting guide"}),
        ]

        for text, expected_type, expected_args in test_cases:
            result = parser.parse(text)
            assert result.type == expected_type
            assert result.arguments["query"] == expected_args["query"]
            assert result.raw_text == text

    def test_documentation_patterns_with_variations(self, parser):
        """Test various documentation query patterns"""
        # "show docs" patterns
        show_patterns = [
            "show me the docs for setup",
            "show docs about API",
            "show documentation for troubleshooting",
        ]

        for pattern in show_patterns:
            result = parser.parse(pattern)
            assert result.type == MCPCommandType.DOCUMENTATION
            assert "query" in result.arguments
            assert len(result.arguments["query"]) > 0

        # "docs for" patterns
        docs_patterns = [
            "docs for authentication",
            "docs about Docker",
            "find docs for setup guide",
        ]

        for pattern in docs_patterns:
            result = parser.parse(pattern)
            assert result.type == MCPCommandType.DOCUMENTATION
            assert "query" in result.arguments

    def test_case_insensitive_parsing(self, parser):
        """Test that parsing is case insensitive"""
        test_cases = [
            "HOW TO SETUP VIOLENTUTF",
            "How To Setup ViolentUTF",
            "how to setup violentutf",
            "GUIDE FOR DOCKER SETUP",
            "Guide For Docker Setup",
        ]

        for text in test_cases:
            result = parser.parse(text)
            assert result.type == MCPCommandType.DOCUMENTATION
            assert "query" in result.arguments
            assert len(result.arguments["query"]) > 0

    def test_complex_queries(self, parser):
        """Test parsing of complex documentation queries"""
        complex_queries = [
            "how do I setup ViolentUTF with Docker and Keycloak",
            "troubleshooting authentication issues with JWT tokens",
            "guide for setting up APISIX with SSL certificates",
            "what is the difference between PyRIT and Garak",
        ]

        for query in complex_queries:
            result = parser.parse(query)
            assert result.type == MCPCommandType.DOCUMENTATION
            assert (
                result.arguments["query"] == query.split(None, 2)[-1]
                if query.startswith(("how do I", "what is"))
                else query.split(None, 1)[-1]
            )

    def test_ambiguous_patterns(self, parser):
        """Test handling of potentially ambiguous patterns"""
        # These could match multiple patterns but should resolve consistently
        ambiguous_cases = [
            ("help with setup", MCPCommandType.DOCUMENTATION),
            ("find setup guide", MCPCommandType.SEARCH),
            ("search docs for API", MCPCommandType.SEARCH),
        ]

        for text, expected_type in ambiguous_cases:
            result = parser.parse(text)
            assert result.type == expected_type
            assert "query" in result.arguments

    def test_non_documentation_queries_unchanged(self, parser):
        """Test that non-documentation queries still work"""
        # These should not be parsed as documentation commands
        non_doc_queries = [
            "/mcp help",
            "/mcp test jailbreak",
            "/mcp enhance",
            "create a new generator",
            "random conversation text",
        ]

        for text in non_doc_queries:
            result = parser.parse(text)
            assert result.type != MCPCommandType.DOCUMENTATION
            assert result.type != MCPCommandType.SEARCH

    def test_empty_queries(self, parser):
        """Test handling of empty or minimal queries"""
        empty_cases = [
            "how to",
            "what is",
            "guide for",
            "help with",
            "docs",
            "search",
        ]

        for text in empty_cases:
            result = parser.parse(text)
            # Should either be UNKNOWN or have a minimal query
            if result.type in (MCPCommandType.DOCUMENTATION, MCPCommandType.SEARCH):
                # If parsed as documentation/search, should have some query content
                assert "query" in result.arguments

    def test_special_characters_in_queries(self, parser):
        """Test handling of special characters"""
        special_cases = [
            "how to setup API v2.0",
            "troubleshooting 404 errors",
            "guide for OAuth 2.0 configuration",
            "setup with environment variables like $PORT",
        ]

        for text in special_cases:
            result = parser.parse(text)
            if result.type == MCPCommandType.DOCUMENTATION:
                assert "query" in result.arguments
                assert len(result.arguments["query"]) > 0


class TestEnhancedCommandSuggestions:
    """Test enhanced command suggestions with documentation support"""

    @pytest.fixture
    def parser(self):
        """Create a NaturalLanguageParser instance"""
        return NaturalLanguageParser()

    def test_documentation_suggestions(self, parser):
        """Test suggestions for documentation-related partial text"""
        test_cases = [
            ("how", ["how to setup ViolentUTF"]),
            ("what", ["guide for MCP"]),
            ("guide", ["/mcp docs setup"]),
            ("troubl", ["troubleshooting Docker"]),
            ("help", ["/mcp docs troubleshooting"]),
            ("setup", ["/mcp docs setup", "how to setup ViolentUTF"]),
            ("install", ["/mcp docs setup", "how to setup ViolentUTF"]),
            ("search", ["/mcp search authentication"]),
            ("find", ["/mcp search authentication"]),
        ]

        for partial, expected_patterns in test_cases:
            suggestions = parser.suggest_command(partial)

            # Check that at least one expected pattern is in suggestions
            found_match = False
            for expected in expected_patterns:
                if any(expected in suggestion for suggestion in suggestions):
                    found_match = True
                    break

            assert found_match, f"No expected patterns {expected_patterns} found in suggestions: {suggestions}"

    def test_suggestions_include_documentation_commands(self, parser):
        """Test that suggestions include new documentation commands"""
        # Test partial MCP command
        suggestions = parser.suggest_command("/mcp")

        # Should include documentation commands
        doc_commands = ["/mcp docs setup", "/mcp docs API", "/mcp search authentication"]
        suggestion_text = " ".join(suggestions)

        assert any(doc_cmd in suggestion_text for doc_cmd in doc_commands)

    def test_suggestions_natural_language_patterns(self, parser):
        """Test suggestions for natural language patterns"""
        suggestions = parser.suggest_command("how")

        # Should include natural language documentation patterns
        natural_patterns = ["how to setup ViolentUTF", "guide for MCP", "troubleshooting Docker"]
        suggestion_text = " ".join(suggestions)

        assert any(pattern in suggestion_text for pattern in natural_patterns)

    def test_suggestions_limit(self, parser):
        """Test that suggestions are properly limited"""
        suggestions = parser.suggest_command("e")  # Very broad query

        assert len(suggestions) <= 5  # Should respect the limit
        assert isinstance(suggestions, list)

    def test_suggestions_relevance(self, parser):
        """Test that suggestions are relevant to input"""
        test_cases = [
            ("setup", ["setup", "ViolentUTF"]),
            ("docker", ["Docker", "troubleshoot"]),
            ("api", ["API", "auth"]),
            ("auth", ["authentication", "JWT"]),
        ]

        for partial, relevant_keywords in test_cases:
            suggestions = parser.suggest_command(partial)

            # At least one suggestion should contain a relevant keyword
            suggestion_text = " ".join(suggestions).lower()
            assert any(keyword.lower() in suggestion_text for keyword in relevant_keywords)


class TestMCPCommandStructure:
    """Test MCPCommand structure with documentation types"""

    def test_documentation_command_creation(self):
        """Test creating documentation MCPCommand"""
        cmd = MCPCommand(
            type=MCPCommandType.DOCUMENTATION, arguments={"query": "setup guide"}, raw_text="how to setup ViolentUTF"
        )

        assert cmd.type == MCPCommandType.DOCUMENTATION
        assert cmd.arguments["query"] == "setup guide"
        assert cmd.raw_text == "how to setup ViolentUTF"
        assert cmd.subcommand is None

    def test_search_command_creation(self):
        """Test creating search MCPCommand"""
        cmd = MCPCommand(
            type=MCPCommandType.SEARCH,
            arguments={"query": "API authentication"},
            raw_text="search for API authentication",
        )

        assert cmd.type == MCPCommandType.SEARCH
        assert cmd.arguments["query"] == "API authentication"
        assert cmd.raw_text == "search for API authentication"

    def test_command_with_empty_arguments(self):
        """Test command creation with empty arguments"""
        cmd = MCPCommand(type=MCPCommandType.DOCUMENTATION, raw_text="docs")

        assert cmd.type == MCPCommandType.DOCUMENTATION
        assert cmd.arguments == {}  # Should be empty dict, not None
        assert cmd.raw_text == "docs"

    def test_command_type_enum_values(self):
        """Test that new command types are properly defined"""
        assert MCPCommandType.DOCUMENTATION.value == "documentation"
        assert MCPCommandType.SEARCH.value == "search"

        # Ensure they're part of the enum
        all_types = list(MCPCommandType)
        assert MCPCommandType.DOCUMENTATION in all_types
        assert MCPCommandType.SEARCH in all_types


class TestErrorHandling:
    """Test error handling in documentation parsing"""

    @pytest.fixture
    def parser(self):
        """Create a NaturalLanguageParser instance"""
        return NaturalLanguageParser()

    def test_malformed_input_handling(self, parser):
        """Test handling of malformed input"""
        malformed_inputs = [
            "",  # Empty string
            "   ",  # Whitespace only
            "\n\t\r",  # Various whitespace
            None,  # This would cause an error, but we test string inputs
        ]

        # Test empty and whitespace strings
        for text in malformed_inputs[:-1]:  # Exclude None
            result = parser.parse(text)
            assert result.type == MCPCommandType.UNKNOWN
            assert result.raw_text == text

    def test_very_long_input(self, parser):
        """Test handling of very long input strings"""
        long_input = "how to setup " + "ViolentUTF " * 1000  # Very long query

        result = parser.parse(long_input)
        assert result.type == MCPCommandType.DOCUMENTATION
        assert "query" in result.arguments
        assert result.raw_text == long_input

    def test_unicode_input(self, parser):
        """Test handling of unicode characters"""
        unicode_inputs = [
            "how to setup ViolentUTF with 特殊字符",
            "guide für Docker Setup",
            "troubleshooting émojis 🐳",
        ]

        for text in unicode_inputs:
            result = parser.parse(text)
            # Should parse normally, unicode shouldn't break parsing
            assert isinstance(result, MCPCommand)
            assert result.raw_text == text

    def test_regex_edge_cases(self, parser):
        """Test regex pattern edge cases"""
        edge_cases = [
            "how to (setup) ViolentUTF",  # Parentheses
            "what is ViolentUTF?",  # Question mark
            "setup ViolentUTF v2.0+",  # Plus sign
            "guide for API [v1]",  # Brackets
            "troubleshoot *.log files",  # Asterisk
        ]

        for text in edge_cases:
            result = parser.parse(text)
            # Should not crash and should produce reasonable results
            assert isinstance(result, MCPCommand)
            assert result.raw_text == text


class TestPatternPriority:
    """Test pattern matching priority and conflicts"""

    @pytest.fixture
    def parser(self):
        """Create a NaturalLanguageParser instance"""
        return NaturalLanguageParser()

    def test_overlapping_patterns(self, parser):
        """Test handling of overlapping patterns"""
        # "help" could match both DOCUMENTATION and HELP patterns
        result = parser.parse("help with setup")

        # Should prefer DOCUMENTATION since it's more specific
        assert result.type == MCPCommandType.DOCUMENTATION
        assert "query" in result.arguments

    def test_explicit_vs_natural_patterns(self, parser):
        """Test that explicit commands take priority"""
        # Both could match different patterns
        explicit_cases = [
            ("/mcp search setup", MCPCommandType.SEARCH),
            ("/mcp docs API", MCPCommandType.DOCUMENTATION),
            ("/mcp help", MCPCommandType.HELP),
        ]

        for text, expected_type in explicit_cases:
            result = parser.parse(text)
            assert result.type == expected_type

    def test_pattern_matching_order(self, parser):
        """Test that pattern matching follows expected order"""
        # The parser should check patterns in a consistent order
        # This is important for reproducible behavior

        result1 = parser.parse("search for setup guide")
        result2 = parser.parse("search for setup guide")

        # Should get consistent results
        assert result1.type == result2.type
        assert result1.arguments == result2.arguments


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
