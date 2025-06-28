"""
Unit tests for MCP server (app.mcp.server.base)

This module tests the Model Context Protocol server including:
- Server initialization and setup
- Tool registration and execution
- Resource management
- Prompt handling
- Authentication
- Protocol compliance
"""

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from mcp.types import (CallToolRequest, CreateMessageRequest, GetPromptRequest,
                       Prompt, ReadResourceRequest, Resource,
                       ServerCapabilities, Tool)

# Mock the MCP server module
with patch("mcp.server.Server"):
    from app.mcp.server.base import ViolentUTFMCPServer


class TestViolentUTFMCPServer:
    """Test ViolentUTF MCP Server"""

    @pytest.fixture
    def mock_mcp_settings(self):
        """Mock MCP settings"""
        with patch("app.mcp.config.mcp_settings") as mock_settings:
            mock_settings.MCP_SERVER_NAME = "ViolentUTF MCP"
            mock_settings.MCP_SERVER_VERSION = "1.0.0"
            mock_settings.MCP_ENABLE_TOOLS = True
            mock_settings.MCP_ENABLE_RESOURCES = True
            mock_settings.MCP_ENABLE_PROMPTS = True
            mock_settings.MCP_ENABLE_SAMPLING = True
            yield mock_settings

    @pytest.fixture
    def mcp_server(self, mock_mcp_settings):
        """Create MCP server instance"""
        with patch("mcp.server.Server") as mock_server_class:
            mock_server_instance = Mock()
            mock_server_class.return_value = mock_server_instance

            server = ViolentUTFMCPServer()
            server.server = mock_server_instance
            return server

    @pytest.fixture
    def mock_tool(self):
        """Create mock tool"""
        return Tool(
            name="test_tool",
            description="Test tool for unit tests",
            inputSchema={
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
            },
        )

    @pytest.fixture
    def mock_resource(self):
        """Create mock resource"""
        return Resource(
            uri="test://resource/1",
            name="Test Resource",
            mimeType="text/plain",
            description="Test resource for unit tests",
        )

    @pytest.fixture
    def mock_prompt(self):
        """Create mock prompt"""
        return Prompt(
            name="test_prompt",
            description="Test prompt for unit tests",
            arguments=[
                {"name": "arg1", "description": "First argument", "required": True}
            ],
        )

    # ======================
    # Initialization Tests
    # ======================

    def test_server_initialization(self, mock_mcp_settings):
        """Test server initialization"""
        with patch("mcp.server.Server") as mock_server_class:
            with patch("app.mcp.auth.MCPAuthHandler") as mock_auth_class:
                server = ViolentUTFMCPServer()

                assert server._initialized is False
                mock_server_class.assert_called_once_with("ViolentUTF MCP")
                mock_auth_class.assert_called_once()

    def test_setup_handlers_all_enabled(self, mcp_server):
        """Test handler setup with all features enabled"""
        # Handlers should be assigned
        assert hasattr(mcp_server.server, "list_tools")
        assert hasattr(mcp_server.server, "call_tool")
        assert hasattr(mcp_server.server, "list_resources")
        assert hasattr(mcp_server.server, "read_resource")
        assert hasattr(mcp_server.server, "list_prompts")
        assert hasattr(mcp_server.server, "get_prompt")
        assert hasattr(mcp_server.server, "create_message")

    def test_setup_handlers_tools_disabled(self, mock_mcp_settings):
        """Test handler setup with tools disabled"""
        mock_mcp_settings.MCP_ENABLE_TOOLS = False

        with patch("mcp.server.Server"):
            server = ViolentUTFMCPServer()

            # Tool handlers should not be set
            assert not hasattr(server.server, "list_tools")
            assert not hasattr(server.server, "call_tool")

    @pytest.mark.asyncio
    async def test_initialize_once(self, mcp_server):
        """Test server initializes only once"""
        with patch.object(mcp_server, "_register_tools") as mock_register:
            await mcp_server.initialize()
            assert mcp_server._initialized is True

            # Call initialize again
            await mcp_server.initialize()

            # Should only register once
            mock_register.assert_called_once()

    # ======================
    # Tool Management Tests
    # ======================

    @pytest.mark.asyncio
    async def test_register_tools(self, mcp_server):
        """Test tool registration"""
        mock_tools = {"tool1": Mock(spec=Tool), "tool2": Mock(spec=Tool)}

        with patch("app.mcp.tools.get_all_tools", return_value=mock_tools):
            await mcp_server._register_tools()

            assert hasattr(mcp_server, "tools")
            assert len(mcp_server.tools) == 2
            assert "tool1" in mcp_server.tools

    @pytest.mark.asyncio
    async def test_list_tools(self, mcp_server, mock_tool):
        """Test listing available tools"""
        mcp_server.tools = {"test_tool": mock_tool}

        tools = await mcp_server._list_tools()

        assert len(tools) == 1
        assert tools[0].name == "test_tool"
        assert tools[0].description == "Test tool for unit tests"

    @pytest.mark.asyncio
    async def test_call_tool_success(self, mcp_server):
        """Test successful tool execution"""
        mock_tool_func = AsyncMock(return_value={"result": "success"})
        mcp_server.tools = {"test_tool": mock_tool_func}

        request = CallToolRequest(name="test_tool", arguments={"input": "test input"})

        result = await mcp_server._call_tool(request)

        assert result.content[0].text == '{"result": "success"}'
        mock_tool_func.assert_called_once_with(input="test input")

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self, mcp_server):
        """Test calling non-existent tool"""
        mcp_server.tools = {}

        request = CallToolRequest(name="non_existent_tool", arguments={})

        result = await mcp_server._call_tool(request)

        assert result.isError is True
        assert "Unknown tool" in result.content[0].text

    @pytest.mark.asyncio
    async def test_call_tool_error(self, mcp_server):
        """Test tool execution error handling"""
        mock_tool_func = AsyncMock(side_effect=Exception("Tool error"))
        mcp_server.tools = {"test_tool": mock_tool_func}

        request = CallToolRequest(name="test_tool", arguments={})

        result = await mcp_server._call_tool(request)

        assert result.isError is True
        assert "Tool error" in result.content[0].text

    # ======================
    # Resource Management Tests
    # ======================

    @pytest.mark.asyncio
    async def test_register_resources(self, mcp_server):
        """Test resource registration"""
        mock_resources = {
            "resource1": Mock(spec=Resource),
            "resource2": Mock(spec=Resource),
        }

        with patch("app.mcp.resources.get_all_resources", return_value=mock_resources):
            await mcp_server._register_resources()

            assert hasattr(mcp_server, "resources")
            assert len(mcp_server.resources) == 2

    @pytest.mark.asyncio
    async def test_list_resources(self, mcp_server, mock_resource):
        """Test listing available resources"""
        mcp_server.resources = {"test://resource/1": mock_resource}

        resources = await mcp_server._list_resources()

        assert len(resources) == 1
        assert resources[0].uri == "test://resource/1"
        assert resources[0].name == "Test Resource"

    @pytest.mark.asyncio
    async def test_read_resource_success(self, mcp_server):
        """Test successful resource reading"""
        mock_resource_func = AsyncMock(
            return_value={"contents": [{"text": "Resource content"}]}
        )
        mcp_server.resources = {"test://resource/1": mock_resource_func}

        request = ReadResourceRequest(uri="test://resource/1")

        result = await mcp_server._read_resource(request)

        assert result.contents[0].text == "Resource content"
        mock_resource_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_read_resource_not_found(self, mcp_server):
        """Test reading non-existent resource"""
        mcp_server.resources = {}

        request = ReadResourceRequest(uri="test://non-existent")

        with pytest.raises(Exception) as exc_info:
            await mcp_server._read_resource(request)

        assert "Resource not found" in str(exc_info.value)

    # ======================
    # Prompt Management Tests
    # ======================

    @pytest.mark.asyncio
    async def test_register_prompts(self, mcp_server):
        """Test prompt registration"""
        mock_prompts = {"prompt1": Mock(spec=Prompt), "prompt2": Mock(spec=Prompt)}

        with patch("app.mcp.prompts.get_all_prompts", return_value=mock_prompts):
            await mcp_server._register_prompts()

            assert hasattr(mcp_server, "prompts")
            assert len(mcp_server.prompts) == 2

    @pytest.mark.asyncio
    async def test_list_prompts(self, mcp_server, mock_prompt):
        """Test listing available prompts"""
        mcp_server.prompts = {"test_prompt": mock_prompt}

        prompts = await mcp_server._list_prompts()

        assert len(prompts) == 1
        assert prompts[0].name == "test_prompt"
        assert prompts[0].description == "Test prompt for unit tests"

    @pytest.mark.asyncio
    async def test_get_prompt_success(self, mcp_server):
        """Test successful prompt retrieval"""
        mock_prompt_func = Mock(
            return_value={
                "messages": [{"role": "user", "content": "Test prompt content"}]
            }
        )
        mcp_server.prompts = {"test_prompt": mock_prompt_func}

        request = GetPromptRequest(name="test_prompt", arguments={"arg1": "value1"})

        result = await mcp_server._get_prompt(request)

        assert len(result.messages) == 1
        assert result.messages[0].content.text == "Test prompt content"
        mock_prompt_func.assert_called_once_with(arg1="value1")

    @pytest.mark.asyncio
    async def test_get_prompt_not_found(self, mcp_server):
        """Test getting non-existent prompt"""
        mcp_server.prompts = {}

        request = GetPromptRequest(name="non_existent", arguments={})

        with pytest.raises(Exception) as exc_info:
            await mcp_server._get_prompt(request)

        assert "Prompt not found" in str(exc_info.value)

    # ======================
    # Sampling Tests
    # ======================

    @pytest.mark.asyncio
    async def test_create_message_success(self, mcp_server):
        """Test message creation (sampling)"""
        request = CreateMessageRequest(
            messages=[{"role": "user", "content": {"type": "text", "text": "Hello"}}],
            maxTokens=100,
        )

        with patch("app.mcp.sampling.create_message") as mock_create:
            mock_create.return_value = {
                "role": "assistant",
                "content": {"type": "text", "text": "Hello! How can I help?"},
            }

            result = await mcp_server._create_message(request)

            assert result.content.text == "Hello! How can I help?"
            mock_create.assert_called_once()

    # ======================
    # Transport Integration Tests
    # ======================

    @pytest.mark.asyncio
    async def test_create_sse_transport(self, mcp_server):
        """Test SSE transport creation"""
        read_stream = AsyncMock()
        write_stream = AsyncMock()

        transport = await mcp_server.create_sse_transport(read_stream, write_stream)

        # Check that transport was created (we can't check exact type without importing it)
        assert transport is not None

    @pytest.mark.asyncio
    async def test_run_sse_success(self, mcp_server):
        """Test running SSE transport"""
        read_stream = AsyncMock()
        write_stream = AsyncMock()

        # Mock transport
        mock_transport = AsyncMock()

        with patch.object(
            mcp_server, "create_sse_transport", return_value=mock_transport
        ):
            with patch.object(mcp_server.server, "run") as mock_run:
                mock_run.return_value = None

                await mcp_server.run_sse(read_stream, write_stream)

                mock_run.assert_called_once_with(
                    mock_transport,
                    mcp_server.get_server_capabilities(),
                    raise_exceptions=True,
                )

    def test_get_server_capabilities(self, mcp_server, mock_mcp_settings):
        """Test server capabilities generation"""
        capabilities = mcp_server.get_server_capabilities()

        assert isinstance(capabilities, ServerCapabilities)
        assert capabilities.tools is not None
        assert capabilities.resources is not None
        assert capabilities.prompts is not None
        assert capabilities.sampling is not None

    def test_get_server_capabilities_partial(self, mock_mcp_settings):
        """Test server capabilities with some features disabled"""
        mock_mcp_settings.MCP_ENABLE_TOOLS = False
        mock_mcp_settings.MCP_ENABLE_RESOURCES = False

        with patch("mcp.server.Server"):
            server = ViolentUTFMCPServer()
            capabilities = server.get_server_capabilities()

            assert capabilities.tools is None
            assert capabilities.resources is None
            assert capabilities.prompts is not None
            assert capabilities.sampling is not None


class TestMCPServerAuthentication:
    """Test MCP server authentication"""

    @pytest.fixture
    def mcp_server_with_auth(self, mock_mcp_settings):
        """Create MCP server with auth enabled"""
        with patch("mcp.server.Server"):
            with patch("app.mcp.auth.MCPAuthHandler") as mock_auth_class:
                mock_auth = Mock()
                mock_auth_class.return_value = mock_auth

                server = ViolentUTFMCPServer()
                server.auth_handler = mock_auth
                return server

    @pytest.mark.asyncio
    async def test_authenticated_tool_call(self, mcp_server_with_auth):
        """Test tool call with authentication"""
        mock_tool_func = AsyncMock(return_value={"result": "success"})
        mcp_server_with_auth.tools = {"secure_tool": mock_tool_func}

        # Mock authentication
        mcp_server_with_auth.auth_handler.verify_request = AsyncMock(return_value=True)

        request = CallToolRequest(name="secure_tool", arguments={"input": "test"})

        # Add auth context
        with patch("app.mcp.server.base.current_auth_context", {"user": "test-user"}):
            result = await mcp_server_with_auth._call_tool(request)

            assert result.content[0].text == '{"result": "success"}'
            mcp_server_with_auth.auth_handler.verify_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_unauthenticated_tool_call(self, mcp_server_with_auth):
        """Test tool call without authentication"""
        mcp_server_with_auth.tools = {"secure_tool": AsyncMock()}

        # Mock authentication failure
        mcp_server_with_auth.auth_handler.verify_request = AsyncMock(return_value=False)

        request = CallToolRequest(name="secure_tool", arguments={})

        result = await mcp_server_with_auth._call_tool(request)

        assert result.isError is True
        assert "Unauthorized" in result.content[0].text


class TestMCPServerTools:
    """Test specific MCP server tools"""

    @pytest.mark.asyncio
    async def test_generator_tool(self, mcp_server):
        """Test generator management tool"""
        from app.mcp.tools.generators import create_generator_tool

        tool_func = create_generator_tool()

        # Test listing generators
        result = await tool_func(action="list")
        assert isinstance(result, dict)
        assert "generators" in result

        # Test creating generator
        result = await tool_func(
            action="create", name="test-gen", provider="openai", model="gpt-4"
        )
        assert "id" in result

        # Test invalid action
        result = await tool_func(action="invalid")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_orchestrator_tool(self, mcp_server):
        """Test orchestrator management tool"""
        from app.mcp.tools.orchestrators import create_orchestrator_tool

        tool_func = create_orchestrator_tool()

        # Test listing orchestrator types
        result = await tool_func(action="list_types")
        assert isinstance(result, dict)
        assert "types" in result

        # Test creating orchestrator
        with patch("app.services.pyrit_orchestrator_service.PyRITOrchestratorService"):
            result = await tool_func(
                action="create",
                config={"type": "PromptSendingOrchestrator"},
                target={"type": "http_endpoint", "url": "http://test"},
            )
            assert "orchestrator_id" in result or "error" in result


class TestMCPServerResources:
    """Test MCP server resources"""

    @pytest.mark.asyncio
    async def test_dataset_resource(self, mcp_server):
        """Test dataset resource provider"""
        from app.mcp.resources.datasets import create_dataset_resource

        resource_func = create_dataset_resource("test-dataset")

        with patch("app.mcp.resources.datasets.load_dataset") as mock_load:
            mock_load.return_value = {
                "name": "test-dataset",
                "prompts": ["prompt1", "prompt2"],
            }

            result = await resource_func()

            assert "contents" in result
            assert len(result["contents"]) > 0
            assert "test-dataset" in result["contents"][0]["text"]

    @pytest.mark.asyncio
    async def test_configuration_resource(self, mcp_server):
        """Test configuration resource provider"""
        from app.mcp.resources.configuration import create_config_resource

        resource_func = create_config_resource("generators")

        with patch("app.mcp.resources.configuration.load_config") as mock_load:
            mock_load.return_value = {
                "generators": {"openai": {"models": ["gpt-4", "gpt-3.5-turbo"]}}
            }

            result = await resource_func()

            assert "contents" in result
            assert "generators" in result["contents"][0]["text"]


class TestMCPServerPrompts:
    """Test MCP server prompts"""

    def test_security_testing_prompt(self, mcp_server):
        """Test security testing prompt"""
        from app.mcp.prompts.security import security_testing_prompt

        result = security_testing_prompt(
            target="http://test-api", test_type="injection"
        )

        assert "messages" in result
        assert len(result["messages"]) > 0
        assert "injection" in result["messages"][0]["content"]["text"].lower()

    def test_red_teaming_prompt(self, mcp_server):
        """Test red teaming prompt"""
        from app.mcp.prompts.testing import red_teaming_prompt

        result = red_teaming_prompt(
            objective="Test jailbreak resistance",
            constraints=["No harmful content", "Stay ethical"],
        )

        assert "messages" in result
        assert any(
            "jailbreak" in msg["content"]["text"].lower() for msg in result["messages"]
        )


class TestMCPServerEdgeCases:
    """Test edge cases and error scenarios"""

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mcp_server):
        """Test handling concurrent tool calls"""
        call_count = 0

        async def mock_tool(**kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)
            return {"call": call_count}

        mcp_server.tools = {"concurrent_tool": mock_tool}

        # Make concurrent requests
        requests = [
            CallToolRequest(name="concurrent_tool", arguments={}) for _ in range(5)
        ]

        results = await asyncio.gather(
            *[mcp_server._call_tool(req) for req in requests]
        )

        assert len(results) == 5
        assert call_count == 5

        # Check all results are unique
        result_values = [json.loads(r.content[0].text)["call"] for r in results]
        assert len(set(result_values)) == 5

    @pytest.mark.asyncio
    async def test_large_resource_handling(self, mcp_server):
        """Test handling of large resources"""
        large_content = "x" * (1024 * 1024)  # 1MB of data

        async def large_resource():
            return {"contents": [{"text": large_content}]}

        mcp_server.resources = {"test://large": large_resource}

        request = ReadResourceRequest(uri="test://large")
        result = await mcp_server._read_resource(request)

        assert len(result.contents[0].text) == len(large_content)

    @pytest.mark.asyncio
    async def test_malformed_tool_arguments(self, mcp_server):
        """Test handling of malformed tool arguments"""
        mcp_server.tools = {"strict_tool": AsyncMock()}

        # Missing required arguments
        request = CallToolRequest(
            name="strict_tool", arguments={}  # Missing required args
        )

        result = await mcp_server._call_tool(request)

        # Should handle gracefully
        assert result.isError is True or result.content is not None

    @pytest.mark.asyncio
    async def test_transport_connection_loss(self, mcp_server):
        """Test handling of transport connection loss"""
        read_stream = AsyncMock()
        write_stream = AsyncMock()

        # Simulate connection loss
        read_stream.readline.side_effect = ConnectionError("Connection lost")

        with pytest.raises(ConnectionError):
            await mcp_server.run_sse(read_stream, write_stream)
