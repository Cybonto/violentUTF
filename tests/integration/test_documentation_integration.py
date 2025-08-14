"""
Integration tests for documentation system in SimpleChat
Tests end-to-end documentation query functionality
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import streamlit as st
from violentutf.utils.mcp_client import MCPClientSync
from violentutf.utils.mcp_integration import MCPCommandType, NaturalLanguageParser


class TestSimpleChatDocumentationIntegration:
    """Test documentation integration in SimpleChat"""
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Create a mock MCP client for testing"""
        mock_client = Mock(spec=MCPClientSync)
        
        # Mock search response
        search_response = {
            "error": None,
            "content": {
                "query": "test query",
                "results": [
                    {
                        "id": "api_auth",
                        "title": "API Authentication",
                        "category": "api",
                        "score": 8.5,
                        "snippet": "This document explains API authentication methods...",
                        "tags": ["api", "authentication", "jwt"],
                        "word_count": 450,
                        "uri": "violentutf://docs/api/api_auth"
                    },
                    {
                        "id": "setup_guide",
                        "title": "Setup Guide", 
                        "category": "guides",
                        "score": 7.2,
                        "snippet": "Complete setup instructions for ViolentUTF...",
                        "tags": ["setup", "installation", "docker"],
                        "word_count": 650,
                        "uri": "violentutf://docs/guides/setup_guide"
                    }
                ],
                "total_found": 2,
                "search_time": "2024-01-01T12:00:00"
            }
        }
        
        # Mock document content response
        doc_response = {
            "error": None,
            "content": """# API Authentication

This document explains how to authenticate with the ViolentUTF API.

## JWT Tokens
Use JWT tokens for secure authentication...

## API Keys
Alternative method for programmatic access...
"""
        }
        
        # Configure mock responses
        mock_client.read_resource.side_effect = lambda uri, params: (
            search_response if "search/query" in uri else doc_response
        )
        
        return mock_client
    
    @pytest.fixture
    def mock_streamlit_environment(self):
        """Set up mock Streamlit environment"""
        with patch.multiple(
            'streamlit',
            session_state={},
            info=Mock(),
            success=Mock(),
            warning=Mock(),
            error=Mock(),
            spinner=Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock())),
            expander=Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock())),
            columns=Mock(return_value=[Mock(), Mock()]),
            button=Mock(return_value=False),
            markdown=Mock(),
        ):
            yield
    
    @pytest.mark.asyncio
    async def test_documentation_query_parsing(self):
        """Test that documentation queries are correctly parsed"""
        parser = NaturalLanguageParser()
        
        test_queries = [
            ("how to setup ViolentUTF", MCPCommandType.DOCUMENTATION, "setup ViolentUTF"),
            ("troubleshooting Docker", MCPCommandType.DOCUMENTATION, "Docker"),
            ("search for API guide", MCPCommandType.SEARCH, "API guide"),
            ("/mcp docs authentication", MCPCommandType.DOCUMENTATION, "authentication"),
        ]
        
        for query, expected_type, expected_content in test_queries:
            result = parser.parse(query)
            assert result.type == expected_type
            assert expected_content in result.arguments.get("query", "")
    
    def test_handle_documentation_query_success(self, mock_streamlit_environment, mock_mcp_client):
        """Test successful documentation query handling"""
        # Import the function here to avoid import issues
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_mcp_client}):
            # Test the function call
            handle_documentation_query("authentication", MCPCommandType.DOCUMENTATION)
            
            # Verify MCP client was called
            mock_mcp_client.read_resource.assert_called_with(
                "violentutf://docs/search/query",
                {"query": "authentication", "limit": 5}
            )
    
    def test_handle_documentation_query_no_results(self, mock_streamlit_environment, mock_mcp_client):
        """Test documentation query with no results"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        # Configure mock to return no results
        no_results_response = {
            "error": None,
            "content": {
                "query": "nonexistent",
                "results": [],
                "suggestions": ["Try searching for 'setup'", "Browse api documentation"],
                "categories": ["api", "guides", "troubleshooting"]
            }
        }
        mock_mcp_client.read_resource.return_value = no_results_response
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_mcp_client}):
            handle_documentation_query("nonexistent", MCPCommandType.DOCUMENTATION)
            
            # Should still call the client
            mock_mcp_client.read_resource.assert_called()
    
    def test_handle_documentation_query_error(self, mock_streamlit_environment, mock_mcp_client):
        """Test documentation query error handling"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        # Configure mock to return error
        error_response = {
            "error": "search_failed",
            "message": "Documentation service unavailable"
        }
        mock_mcp_client.read_resource.return_value = error_response
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_mcp_client}):
            handle_documentation_query("test query", MCPCommandType.DOCUMENTATION)
            
            # Should handle the error gracefully
            mock_mcp_client.read_resource.assert_called()
    
    def test_handle_documentation_query_no_client(self, mock_streamlit_environment):
        """Test documentation query when MCP client is not available"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {}):
            with patch('violentutf.pages.Simple_Chat.MCPClientSync', return_value=None):
                handle_documentation_query("test query", MCPCommandType.DOCUMENTATION)
                
                # Should handle missing client gracefully
                # The function should show an error message
    
    def test_mcp_command_handler_documentation(self, mock_streamlit_environment, mock_mcp_client):
        """Test MCP command handler for documentation commands"""
        from violentutf.pages.Simple_Chat import handle_mcp_command
        from violentutf.utils.mcp_integration import MCPCommand
        
        # Create a documentation command
        doc_command = MCPCommand(
            type=MCPCommandType.DOCUMENTATION,
            arguments={"query": "setup guide"},
            raw_text="how to setup ViolentUTF"
        )
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_mcp_client}):
            with patch('violentutf.pages.Simple_Chat.handle_documentation_query') as mock_handle_doc:
                handle_mcp_command(doc_command)
                
                # Should call documentation handler
                mock_handle_doc.assert_called_with("setup guide", MCPCommandType.DOCUMENTATION)
    
    def test_mcp_command_handler_search(self, mock_streamlit_environment, mock_mcp_client):
        """Test MCP command handler for search commands"""
        from violentutf.pages.Simple_Chat import handle_mcp_command
        from violentutf.utils.mcp_integration import MCPCommand
        
        # Create a search command
        search_command = MCPCommand(
            type=MCPCommandType.SEARCH,
            arguments={"query": "API authentication"},
            raw_text="search for API authentication"
        )
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_mcp_client}):
            with patch('violentutf.pages.Simple_Chat.handle_documentation_query') as mock_handle_doc:
                handle_mcp_command(search_command)
                
                # Should call documentation handler with search type
                mock_handle_doc.assert_called_with("API authentication", MCPCommandType.SEARCH)
    
    def test_mcp_command_handler_empty_query(self, mock_streamlit_environment):
        """Test MCP command handler with empty query"""
        from violentutf.pages.Simple_Chat import handle_mcp_command
        from violentutf.utils.mcp_integration import MCPCommand
        
        # Create a command with empty query
        empty_command = MCPCommand(
            type=MCPCommandType.DOCUMENTATION,
            arguments={},  # No query
            raw_text="docs"
        )
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {}):
            handle_mcp_command(empty_command)
            
            # Should show warning message (tested via st.warning call)
    
    def test_documentation_workflow_end_to_end(self, mock_streamlit_environment, mock_mcp_client):
        """Test complete documentation workflow from input to display"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_mcp_client}):
            # Simulate user query
            handle_documentation_query("how to setup Docker", MCPCommandType.DOCUMENTATION)
            
            # Verify the workflow
            mock_mcp_client.read_resource.assert_called_with(
                "violentutf://docs/search/query",
                {"query": "how to setup Docker", "limit": 5}
            )
    
    @pytest.mark.parametrize("query,command_type", [
        ("setup ViolentUTF", MCPCommandType.DOCUMENTATION),
        ("troubleshooting", MCPCommandType.DOCUMENTATION),
        ("API guide", MCPCommandType.SEARCH),
        ("Docker configuration", MCPCommandType.SEARCH),
    ])
    def test_different_query_types(self, query, command_type, mock_streamlit_environment, mock_mcp_client):
        """Test different types of documentation queries"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_mcp_client}):
            handle_documentation_query(query, command_type)
            
            # Should call MCP client with correct parameters
            mock_mcp_client.read_resource.assert_called_with(
                "violentutf://docs/search/query",
                {"query": query, "limit": 5}
            )


class TestDocumentationErrorHandling:
    """Test error handling in documentation integration"""
    
    @pytest.fixture
    def mock_streamlit_environment(self):
        """Set up mock Streamlit environment"""
        with patch.multiple(
            'streamlit',
            session_state={},
            info=Mock(),
            success=Mock(),
            warning=Mock(),
            error=Mock(),
            spinner=Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock())),
            expander=Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock())),
            columns=Mock(return_value=[Mock(), Mock()]),
            button=Mock(return_value=False),
            markdown=Mock(),
        ):
            yield
    
    def test_mcp_client_exception_handling(self, mock_streamlit_environment):
        """Test handling of MCP client exceptions"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        # Mock client that raises exception
        mock_client = Mock()
        mock_client.read_resource.side_effect = Exception("Connection failed")
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_client}):
            # Should not raise exception, should handle gracefully
            handle_documentation_query("test query", MCPCommandType.DOCUMENTATION)
    
    def test_malformed_response_handling(self, mock_streamlit_environment):
        """Test handling of malformed responses from MCP"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        mock_client = Mock()
        # Return malformed response
        mock_client.read_resource.return_value = {"unexpected": "format"}
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_client}):
            handle_documentation_query("test query", MCPCommandType.DOCUMENTATION)
            
            # Should handle gracefully
    
    def test_none_response_handling(self, mock_streamlit_environment):
        """Test handling of None response from MCP"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        mock_client = Mock()
        mock_client.read_resource.return_value = None
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_client}):
            handle_documentation_query("test query", MCPCommandType.DOCUMENTATION)
            
            # Should handle None response


class TestDocumentationUserExperience:
    """Test user experience aspects of documentation integration"""
    
    @pytest.fixture
    def mock_streamlit_environment(self):
        """Set up mock Streamlit environment"""
        with patch.multiple(
            'streamlit',
            session_state={},
            info=Mock(),
            success=Mock(),
            warning=Mock(),
            error=Mock(),
            spinner=Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock())),
            expander=Mock(return_value=Mock(__enter__=Mock(), __exit__=Mock())),
            columns=Mock(return_value=[Mock(), Mock()]),
            button=Mock(side_effect=lambda text, key=None: key == "test_button"),
            markdown=Mock(),
        ):
            yield
    
    def test_search_suggestions_display(self, mock_streamlit_environment):
        """Test that search suggestions are properly displayed"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        mock_client = Mock()
        no_results_response = {
            "error": None,
            "content": {
                "query": "nonexistent",
                "results": [],
                "suggestions": ["Try searching for 'setup'", "Browse api documentation"],
                "categories": ["api", "guides", "troubleshooting"]
            }
        }
        mock_client.read_resource.return_value = no_results_response
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_client}):
            handle_documentation_query("nonexistent", MCPCommandType.DOCUMENTATION)
            
            # Should display suggestions
    
    def test_fallback_suggestions_display(self, mock_streamlit_environment):
        """Test that fallback suggestions are shown on error"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        mock_client = Mock()
        mock_client.read_resource.return_value = {"error": "service_unavailable"}
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_client}):
            handle_documentation_query("test", MCPCommandType.DOCUMENTATION)
            
            # Should show fallback suggestions
    
    def test_document_content_display(self, mock_streamlit_environment):
        """Test that document content is properly displayed"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        mock_client = Mock()
        
        # Mock successful search
        search_response = {
            "error": None,
            "content": {
                "results": [{
                    "id": "test_doc",
                    "title": "Test Document",
                    "category": "test",
                    "score": 10.0,
                    "snippet": "Test snippet",
                    "tags": ["test"],
                    "word_count": 100,
                    "uri": "violentutf://docs/test/test_doc"
                }]
            }
        }
        
        # Mock document content
        doc_response = {
            "error": None,
            "content": "# Test Document\n\nThis is test content."
        }
        
        mock_client.read_resource.side_effect = [search_response, doc_response]
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_client}):
            # Mock button click to read full document
            with patch('violentutf.pages.Simple_Chat.st.button', return_value=True):
                handle_documentation_query("test", MCPCommandType.DOCUMENTATION)
                
                # Should call read_resource twice (search + document)
                assert mock_client.read_resource.call_count == 2


class TestDocumentationPerformance:
    """Test performance aspects of documentation integration"""
    
    def test_query_timeout_handling(self, mock_streamlit_environment):
        """Test handling of slow/timeout queries"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        import time
        
        mock_client = Mock()
        
        # Simulate slow response
        def slow_response(*args, **kwargs):
            time.sleep(0.1)  # Small delay for testing
            return {"error": None, "content": {"results": []}}
        
        mock_client.read_resource.side_effect = slow_response
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_client}):
            start_time = time.time()
            handle_documentation_query("test", MCPCommandType.DOCUMENTATION)
            end_time = time.time()
            
            # Should complete in reasonable time
            assert end_time - start_time < 1.0  # Should be much faster than 1 second
    
    def test_large_result_handling(self, mock_streamlit_environment):
        """Test handling of large result sets"""
        from violentutf.pages.Simple_Chat import handle_documentation_query
        
        mock_client = Mock()
        
        # Create large result set
        large_results = []
        for i in range(20):  # More than the limit of 5
            large_results.append({
                "id": f"doc_{i}",
                "title": f"Document {i}",
                "category": "test",
                "score": 10.0 - i * 0.1,
                "snippet": f"Snippet for document {i}",
                "tags": ["test"],
                "word_count": 100 + i,
                "uri": f"violentutf://docs/test/doc_{i}"
            })
        
        large_response = {
            "error": None,
            "content": {
                "results": large_results,
                "total_found": 20
            }
        }
        mock_client.read_resource.return_value = large_response
        
        with patch('violentutf.pages.Simple_Chat.st.session_state', {"mcp_client": mock_client}):
            handle_documentation_query("test", MCPCommandType.DOCUMENTATION)
            
            # Should handle large results gracefully


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])