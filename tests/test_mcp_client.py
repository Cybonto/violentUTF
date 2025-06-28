"""
Unit Tests for MCP Client
========================

Tests for MCP client SSE connection, JSON-RPC handling, and authentication.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from violentutf.utils.mcp_client import (
    MCPAuthenticationError,
    MCPClient,
    MCPClientError,
    MCPClientSync,
    MCPConnectionError,
    MCPMethod,
    MCPResponse,
    MCPTimeoutError,
)


class TestMCPResponse:
    """Test MCPResponse dataclass"""

    def test_successful_response(self):
        """Test successful response creation"""
        response = MCPResponse(id=1, result={"data": "test"})
        assert response.id == 1
        assert response.result == {"data": "test"}
        assert response.error is None
        assert not response.is_error

    def test_error_response(self):
        """Test error response creation"""
        response = MCPResponse(id=2, error={"code": -32000, "message": "Test error"})
        assert response.id == 2
        assert response.result is None
        assert response.error == {"code": -32000, "message": "Test error"}
        assert response.is_error
        assert response.error_message == "Test error"


class TestMCPClient:
    """Test async MCP client"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return MCPClient(base_url="http://test.local:9080")

    @pytest.mark.asyncio
    async def test_initialization(self, client):
        """Test client initialization"""
        assert client.base_url == "http://test.local:9080"
        assert client.mcp_endpoint == "http://test.local:9080/mcp/sse/"
        assert not client._initialized
        assert client._server_info == {}

    @pytest.mark.asyncio
    async def test_get_auth_headers(self, client):
        """Test authentication header generation"""
        with patch(
            "violentutf.utils.jwt_manager.jwt_manager.get_valid_token"
        ) as mock_token:
            mock_token.return_value = "test-jwt-token"

            with patch.dict(os.environ, {"APISIX_API_KEY": "test-api-key"}):
                headers = client._get_auth_headers()

                assert headers["Authorization"] == "Bearer test-jwt-token"
                assert headers["Content-Type"] == "application/json"
                assert headers["X-API-Gateway"] == "APISIX"
                assert headers["apikey"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_get_auth_headers_no_token(self, client):
        """Test authentication headers when no token available"""
        with patch(
            "violentutf.utils.jwt_manager.jwt_manager.get_valid_token"
        ) as mock_token:
            mock_token.return_value = None

            headers = client._get_auth_headers()
            assert headers == {}

    @pytest.mark.asyncio
    async def test_send_request_success(self, client):
        """Test successful JSON-RPC request"""
        mock_response_data = {
            "jsonrpc": "2.0",
            "result": {"tools": ["tool1", "tool2"]},
            "id": 1,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = (
                "data: " + json.dumps(mock_response_data) + "\n\nevent: done\n\n"
            )
            mock_response.iter_lines = AsyncMock(
                return_value=["data: " + json.dumps(mock_response_data), "event: done"]
            )

            mock_client.post.return_value.__aenter__.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock auth headers
            with patch.object(
                client,
                "_get_auth_headers",
                return_value={"Authorization": "Bearer test"},
            ):
                response = await client._send_request(MCPMethod.TOOLS_LIST)

                assert response.id == 1
                assert response.result == {"tools": ["tool1", "tool2"]}
                assert not response.is_error

    @pytest.mark.asyncio
    async def test_send_request_auth_failure(self, client):
        """Test request with authentication failure"""
        with patch.object(client, "_get_auth_headers", return_value={}):
            response = await client._send_request(MCPMethod.TOOLS_LIST)

            assert response.is_error
            assert response.error["code"] == -32000
            assert "Authentication failed" in response.error["message"]

    @pytest.mark.asyncio
    async def test_initialize_success(self, client):
        """Test successful initialization"""
        mock_response = MCPResponse(
            id=1,
            result={
                "name": "Test MCP Server",
                "version": "1.0.0",
                "capabilities": {"tools": True},
            },
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            result = await client.initialize()

            assert result is True
            assert client._initialized is True
            assert client._server_info["name"] == "Test MCP Server"

    @pytest.mark.asyncio
    async def test_initialize_failure(self, client):
        """Test initialization failure"""
        mock_response = MCPResponse(
            id=1, error={"code": -32603, "message": "Server error"}
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            result = await client.initialize()

            assert result is False
            assert client._initialized is False

    @pytest.mark.asyncio
    async def test_list_tools(self, client):
        """Test listing tools"""
        client._initialized = True

        mock_response = MCPResponse(
            id=1,
            result={
                "tools": [
                    {"name": "create_generator", "description": "Create a generator"},
                    {"name": "list_datasets", "description": "List datasets"},
                ]
            },
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            tools = await client.list_tools()

            assert len(tools) == 2
            assert tools[0]["name"] == "create_generator"
            assert tools[1]["name"] == "list_datasets"

    @pytest.mark.asyncio
    async def test_execute_tool(self, client):
        """Test tool execution"""
        client._initialized = True

        mock_response = MCPResponse(
            id=1, result={"success": True, "generator_id": "gen-123"}
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            result = await client.execute_tool(
                "create_generator", {"provider": "openai", "model": "gpt-4"}
            )

            assert result["success"] is True
            assert result["generator_id"] == "gen-123"

    @pytest.mark.asyncio
    async def test_list_prompts(self, client):
        """Test listing prompts"""
        client._initialized = True

        mock_response = MCPResponse(
            id=1,
            result={
                "prompts": [
                    {"name": "enhancement", "description": "Enhance prompts"},
                    {"name": "security", "description": "Security analysis"},
                ]
            },
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            prompts = await client.list_prompts()

            assert len(prompts) == 2
            assert prompts[0]["name"] == "enhancement"

    @pytest.mark.asyncio
    async def test_get_prompt(self, client):
        """Test getting a specific prompt"""
        client._initialized = True

        mock_response = MCPResponse(
            id=1,
            result={"messages": [{"role": "user", "content": "Enhanced prompt text"}]},
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            prompt = await client.get_prompt("enhancement", {"original": "test"})

            assert prompt == "Enhanced prompt text"

    @pytest.mark.asyncio
    async def test_list_resources(self, client):
        """Test listing resources"""
        client._initialized = True

        mock_response = MCPResponse(
            id=1,
            result={
                "resources": [
                    {
                        "uri": "violentutf://datasets/jailbreak",
                        "name": "Jailbreak Dataset",
                    },
                    {"uri": "violentutf://generators/gpt4", "name": "GPT-4 Generator"},
                ]
            },
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            resources = await client.list_resources()

            assert len(resources) == 2
            assert resources[0]["uri"] == "violentutf://datasets/jailbreak"

    @pytest.mark.asyncio
    async def test_read_resource(self, client):
        """Test reading a resource"""
        client._initialized = True

        mock_response = MCPResponse(
            id=1, result={"content": {"prompts": ["test1", "test2"]}}
        )

        with patch.object(client, "_send_request", return_value=mock_response):
            resource = await client.read_resource("violentutf://datasets/test")

            assert resource == {"content": {"prompts": ["test1", "test2"]}}

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check"""
        with patch.object(client, "initialize", return_value=True):
            result = await client.health_check()
            assert result is True

        with patch.object(
            client, "initialize", side_effect=Exception("Connection failed")
        ):
            result = await client.health_check()
            assert result is False


class TestMCPClientSync:
    """Test synchronous MCP client wrapper"""

    @pytest.fixture
    def client(self):
        """Create test sync client"""
        return MCPClientSync(base_url="http://test.local:9080")

    def test_initialization(self, client):
        """Test sync client initialization"""
        assert isinstance(client.client, MCPClient)
        assert client.client.base_url == "http://test.local:9080"

    def test_run_async(self, client):
        """Test running async functions in sync context"""

        async def test_coro():
            return "test_result"

        result = client._run_async(test_coro())
        assert result == "test_result"

    def test_initialize(self, client):
        """Test sync initialize"""
        with patch.object(
            client.client, "initialize", return_value=asyncio.coroutine(lambda: True)()
        ):
            result = client.initialize()
            assert result is True

    def test_list_tools(self, client):
        """Test sync list tools"""
        mock_tools = [{"name": "tool1"}, {"name": "tool2"}]
        with patch.object(
            client.client,
            "list_tools",
            return_value=asyncio.coroutine(lambda: mock_tools)(),
        ):
            tools = client.list_tools()
            assert len(tools) == 2
            assert tools[0]["name"] == "tool1"

    def test_execute_tool(self, client):
        """Test sync tool execution"""
        mock_result = {"success": True, "data": "test"}
        with patch.object(
            client.client,
            "execute_tool",
            return_value=asyncio.coroutine(lambda: mock_result)(),
        ):
            result = client.execute_tool("test_tool", {"arg": "value"})
            assert result["success"] is True
            assert result["data"] == "test"

    def test_error_handling(self, client):
        """Test error handling in sync wrapper"""

        async def failing_coro():
            raise MCPConnectionError("Test error")

        with pytest.raises(MCPConnectionError, match="Test error"):
            client._run_async(failing_coro())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
