"""
Test suite for MCP Client implementation
Tests SSE connection, JSON-RPC handling, and all MCP operations
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from httpx import Response

# Import from utils - conftest.py handles path setup
from utils.mcp_client import MCPClient, MCPClientSync, MCPMethod, MCPResponse


class TestMCPResponse:
    """Test MCPResponse dataclass"""

    def test_response_success(self):
        """Test successful response"""
        response = MCPResponse(id=1, result={"data": "test"})
        assert not response.is_error
        assert response.error_message == ""
        assert response.result == {"data": "test"}

    def test_response_error(self):
        """Test error response"""
        response = MCPResponse(id=1, error={"code": -32600, "message": "Invalid request"})
        assert response.is_error
        assert response.error_message == "Invalid request"
        assert response.result is None


class TestMCPClient:
    """Test async MCP Client"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return MCPClient(base_url="http://localhost:9080")

    @pytest.fixture
    def mock_auth_headers(self):
        """Mock authentication headers"""
        return {"Authorization": "Bearer test_token", "Content-Type": "application/json", "X-API-Gateway": "APISIX"}

    @pytest.mark.asyncio
    async def test_initialization(self, client, mock_auth_headers):
        """Test client initialization"""
        # Mock successful initialization response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"name": "ViolentUTF MCP Server", "version": "1.0.0", "capabilities": {}},
        }

        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
                result = await client.initialize()

                assert result is True
                assert client._initialized is True
                assert client._server_info["name"] == "ViolentUTF MCP Server"

    @pytest.mark.asyncio
    async def test_initialization_failure(self, client, mock_auth_headers):
        """Test initialization failure"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
                result = await client.initialize()

                assert result is False
                assert client._initialized is False

    @pytest.mark.asyncio
    async def test_list_prompts(self, client, mock_auth_headers):
        """Test listing prompts"""
        # Mock response with prompts
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "prompts": [
                    {"name": "jailbreak_test", "description": "Test jailbreaking", "arguments": []},
                    {"name": "bias_detection", "description": "Detect bias", "arguments": []},
                ]
            },
        }

        # Mark as initialized
        client._initialized = True

        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
                prompts = await client.list_prompts()

                assert len(prompts) == 2
                assert prompts[0]["name"] == "jailbreak_test"
                assert prompts[1]["name"] == "bias_detection"

    @pytest.mark.asyncio
    async def test_get_prompt(self, client, mock_auth_headers):
        """Test getting a specific prompt"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 3,
            "result": {"messages": [{"role": "user", "content": "Test prompt content"}]},
        }

        client._initialized = True

        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
                prompt = await client.get_prompt("test_prompt", {"arg1": "value1"})

                assert prompt == "Test prompt content"

    @pytest.mark.asyncio
    async def test_list_resources(self, client, mock_auth_headers):
        """Test listing resources"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 4,
            "result": {
                "resources": [
                    {
                        "uri": "violentutf://datasets/harmbench",
                        "name": "HarmBench Dataset",
                        "mimeType": "application/json",
                    }
                ]
            },
        }

        client._initialized = True

        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
                resources = await client.list_resources()

                assert len(resources) == 1
                assert resources[0]["uri"] == "violentutf://datasets/harmbench"

    @pytest.mark.asyncio
    async def test_read_resource(self, client, mock_auth_headers):
        """Test reading a resource"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 5,
            "result": {"contents": [{"mimeType": "text/plain", "text": "Resource content here"}]},
        }

        client._initialized = True

        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
                content = await client.read_resource("violentutf://test")

                assert content == "Resource content here"

    @pytest.mark.asyncio
    async def test_sse_response_parsing(self, client, mock_auth_headers):
        """Test parsing SSE formatted response"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/event-stream"}
        mock_response.text = """data: {"jsonrpc": "2.0", "id": 6, "result": {"test": "sse_data"}}

event: close
data: 

"""

        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
                response = await client._send_request(MCPMethod.PROMPTS_LIST)

                assert not response.is_error
                assert response.result == {"test": "sse_data"}

    @pytest.mark.asyncio
    async def test_auth_header_generation(self, client):
        """Test authentication header generation"""
        with patch("utils.jwt_manager.jwt_manager.get_valid_token", return_value="test_token"):
            with patch.dict(os.environ, {"VIOLENTUTF_API_KEY": "test_api_key"}):
                headers = client._get_auth_headers()

                assert headers["Authorization"] == "Bearer test_token"
                assert headers["X-API-Gateway"] == "APISIX"
                assert headers["apikey"] == "test_api_key"

    @pytest.mark.asyncio
    async def test_request_timeout(self, client, mock_auth_headers):
        """Test request timeout handling"""
        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("Timeout")):
                response = await client._send_request(MCPMethod.PROMPTS_LIST)

                assert response.is_error
                assert response.error["code"] == -32001
                assert "timeout" in response.error["message"].lower()

    @pytest.mark.asyncio
    async def test_health_check(self, client, mock_auth_headers):
        """Test health check functionality"""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"name": "ViolentUTF MCP Server", "version": "1.0.0"},
        }

        with patch.object(client, "_get_auth_headers", return_value=mock_auth_headers):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
                result = await client.health_check()

                assert result is True


class TestMCPClientSync:
    """Test synchronous MCP Client wrapper"""

    @pytest.fixture
    def client(self):
        """Create test sync client"""
        return MCPClientSync(base_url="http://localhost:9080")

    def test_sync_initialization(self, client):
        """Test synchronous initialization"""
        with patch.object(client.client, "initialize", new_callable=AsyncMock, return_value=True):
            result = client.initialize()
            assert result is True

    def test_sync_list_prompts(self, client):
        """Test synchronous prompt listing"""
        mock_prompts = [{"name": "test1", "description": "Test 1"}, {"name": "test2", "description": "Test 2"}]

        with patch.object(client.client, "list_prompts", new_callable=AsyncMock, return_value=mock_prompts):
            prompts = client.list_prompts()
            assert len(prompts) == 2
            assert prompts[0]["name"] == "test1"

    def test_sync_get_prompt(self, client):
        """Test synchronous prompt retrieval"""
        mock_prompt = "This is a test prompt"

        with patch.object(client.client, "get_prompt", new_callable=AsyncMock, return_value=mock_prompt):
            prompt = client.get_prompt("test", {"arg": "value"})
            assert prompt == "This is a test prompt"

    def test_sync_error_handling(self, client):
        """Test synchronous error handling"""
        with patch.object(client.client, "list_prompts", new_callable=AsyncMock, side_effect=Exception("Test error")):
            with pytest.raises(Exception) as exc_info:
                client.list_prompts()
            assert "Test error" in str(exc_info.value)


class TestIntegration:
    """Integration tests with mock MCP server"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow from initialization to prompt retrieval"""
        client = MCPClient(base_url="http://localhost:9080")

        # Mock all responses
        responses = [
            # Initialize response
            {"jsonrpc": "2.0", "id": 1, "result": {"name": "ViolentUTF MCP Server", "version": "1.0.0"}},
            # List prompts response
            {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "prompts": [
                        {
                            "name": "security_test",
                            "description": "Security testing prompt",
                            "arguments": [{"name": "target", "type": "string", "required": True}],
                        }
                    ]
                },
            },
            # Get prompt response
            {
                "jsonrpc": "2.0",
                "id": 3,
                "result": {"messages": [{"role": "user", "content": "Testing security for: example.com"}]},
            },
        ]

        response_iter = iter(responses)

        def mock_response(*args, **kwargs):
            resp_data = next(response_iter)
            mock_resp = Mock(spec=Response)
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "application/json"}
            mock_resp.json.return_value = resp_data
            return mock_resp

        with patch("utils.jwt_manager.jwt_manager.get_valid_token", return_value="test_token"):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_response):
                # Initialize
                init_result = await client.initialize()
                assert init_result is True

                # List prompts
                prompts = await client.list_prompts()
                assert len(prompts) == 1
                assert prompts[0]["name"] == "security_test"

                # Get specific prompt
                prompt_text = await client.get_prompt("security_test", {"target": "example.com"})
                assert prompt_text == "Testing security for: example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
