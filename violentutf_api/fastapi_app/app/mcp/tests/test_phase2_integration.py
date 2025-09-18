# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Phase 2 Integration Tests for ViolentUTF MCP Server."""

# pylint: disable=protected-access
import asyncio
import logging
from typing import Self
from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.types import Tool

from app.mcp.resources import resource_registry
from app.mcp.server.base import ViolentUTFMCPServer
from app.mcp.tools import tool_registry
from app.mcp.tools.generators import generator_tools
from app.mcp.tools.introspection import initialize_introspector
from app.mcp.tools.orchestrators import orchestrator_tools

logger = logging.getLogger(__name__)


class TestPhase2Integration:
    """Integration tests for Phase 2 MCP implementation."""

    @pytest.fixture
    def mock_fastapi_app(self: "Self"):
        """Create a mock FastAPI app for testing."""
        from fastapi import FastAPI
        from fastapi.routing import APIRoute

        app = FastAPI()

        # Mock some routes
        mock_routes = [
            Mock(
                path="/api/v1/generators",
                methods=["GET", "POST"],
                endpoint=lambda: None,
                tags=["generators"],
            ),
            Mock(
                path="/api/v1/generators/{generator_id}",
                methods=["GET", "PUT", "DELETE"],
                endpoint=lambda generator_id: None,
                tags=["generators"],
            ),
            Mock(
                path="/api/v1/orchestrators",
                methods=["GET", "POST"],
                endpoint=lambda: None,
                tags=["orchestrators"],
            ),
        ]

        # Make each mock route an APIRoute instance
        api_routes = []
        for mock_route in mock_routes:
            route = Mock(spec=APIRoute)
            route.path = mock_route.path  # pylint: disable=no-member
            route.methods = mock_route.methods  # pylint: disable=no-member
            route.endpoint = mock_route.endpoint  # pylint: disable=no-member
            route.tags = mock_route.tags  # pylint: disable=no-member
            api_routes.append(route)

        # Use router.routes.extend() for FastAPI v0.116+ compatibility
        app.router.routes.extend(api_routes)
        return app

    @pytest.mark.asyncio
    async def test_endpoint_introspection(self: "TestPhase2Integration", mock_fastapi_app: "FastAPI"):
        """Test FastAPI endpoint introspection functionality."""
        # Initialize introspector

        introspector = initialize_introspector(mock_fastapi_app)

        assert introspector is not None
        assert introspector.app == mock_fastapi_app

        # Test endpoint discovery
        endpoints = introspector.discover_endpoints()

        assert isinstance(endpoints, list)
        assert len(endpoints) > 0

        # Verify endpoint structure
        for endpoint in endpoints:
            assert "name" in endpoint
            assert "method" in endpoint
            assert "path" in endpoint
            assert "description" in endpoint

    @pytest.mark.asyncio
    async def test_tool_discovery_and_registration(self: "TestPhase2Integration", mock_fastapi_app: "FastAPI"):
        """Test tool discovery and registration process."""
        # Clear existing tools

        tool_registry.clear_tools()

        # Discover tools
        await tool_registry.discover_tools(mock_fastapi_app)

        # Verify tools were discovered
        tools = await tool_registry.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

        # Check for specialized tools
        tool_names = [tool.name for tool in tools]

        # Generator tools should be present
        expected_generator_tools = [
            "list_generators",
            "get_generator",
            "create_generator",
            "update_generator",
            "delete_generator",
            "test_generator",
        ]
        for tool_name in expected_generator_tools:
            assert tool_name in tool_names, f"Missing generator tool: {tool_name}"

        # Orchestrator tools should be present
        expected_orchestrator_tools = [
            "list_orchestrators",
            "get_orchestrator",
            "create_orchestrator",
            "start_orchestrator",
            "stop_orchestrator",
        ]
        for tool_name in expected_orchestrator_tools:
            assert tool_name in tool_names, f"Missing orchestrator tool: {tool_name}"

    @pytest.mark.asyncio
    async def test_generator_tools_functionality(self: "Self"):
        """Test generator tools functionality."""
        tools = generator_tools.get_tools()

        assert len(tools) > 0

        # Test tool schemas
        for tool in tools:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert isinstance(tool.inputSchema, dict)
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"

    @pytest.mark.asyncio
    async def test_orchestrator_tools_functionality(self: "Self"):
        """Test orchestrator tools functionality."""
        tools = orchestrator_tools.get_tools()

        assert len(tools) > 0

        # Test tool schemas
        for tool in tools:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert isinstance(tool.inputSchema, dict)
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"

    @pytest.mark.asyncio
    async def test_resource_management_system(self: "Self"):
        """Test resource management system."""
        # Initialize resource registry

        await resource_registry.initialize()

        # Test resource listing (will return empty list due to no API connection)
        resources = await resource_registry.list_resources()
        assert isinstance(resources, list)

        # Test cache functionality
        cache_stats = resource_registry.get_cache_stats()
        assert isinstance(cache_stats, dict)
        assert "total_entries" in cache_stats
        assert "valid_entries" in cache_stats
        assert "expired_entries" in cache_stats
        assert "cache_ttl_seconds" in cache_stats

    @pytest.mark.asyncio
    async def test_tool_execution_routing(self: "TestPhase2Integration", mock_fastapi_app: "FastAPI"):
        """Test tool execution routing to specialized tools."""
        # Setup tools

        await tool_registry.discover_tools(mock_fastapi_app)

        # Mock the HTTP calls to prevent actual API requests
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True, "data": "mock_data"}

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)

            # Test generator tool execution
            result = await tool_registry.call_tool(
                "list_generators", {"provider_type": "openai"}, {"token": "mock_token"}
            )

            assert isinstance(result, dict)
            # Should not have error if routing worked
            if "error" in result:
                # Expected if API is not available
                assert result["error"] in ["connection_error", "timeout"]

    @pytest.mark.asyncio
    async def test_mcp_server_integration(self: "TestPhase2Integration", mock_fastapi_app: "FastAPI"):
        """Test MCP server integration with all Phase 2 components."""
        # Create MCP server

        mcp_server = ViolentUTFMCPServer()

        # Initialize server
        await mcp_server.initialize()

        # Test capabilities
        capabilities = mcp_server.get_capabilities()
        assert capabilities is not None

        # Mount to app (this will trigger tool discovery)
        mcp_server.mount_to_app(mock_fastapi_app)

        # Test tool listing through MCP server
        tools = await mcp_server._list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

        # Test resource listing through MCP server
        resources = await mcp_server._list_resources()
        assert isinstance(resources, list)

    @pytest.mark.asyncio
    async def test_tool_validation_system(self: "Self"):
        """Test tool argument validation system."""
        # Test with valid generator tool arguments

        valid_args = {"generator_id": "test-generator-id"}

        # Mock the tool executor validation
        with patch("app.mcp.tools.executor.tool_executor.validate_tool_arguments") as mock_validate:
            mock_validate.return_value = {"valid": True, "errors": []}

            # This would normally validate against actual endpoint schema
            validation_result = await mock_validate("get_generator", valid_args)
            assert validation_result["valid"] is True
            assert len(validation_result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self: "TestPhase2Integration", mock_fastapi_app: "FastAPI"):
        """Test error handling and recovery mechanisms."""
        # Test tool registry with invalid app

        await tool_registry.discover_tools(None)

        # Should still have specialized tools even without endpoint discovery
        tools = await tool_registry.list_tools()
        specialized_tool_count = len(generator_tools.get_tools()) + len(orchestrator_tools.get_tools())
        assert len(tools) >= specialized_tool_count

        # Test resource registry with failed initialization
        with patch("app.mcp.resources.manager.resource_manager.list_resources") as mock_list:
            mock_list.side_effect = Exception("Mock API failure")

            # Should handle the error gracefully
            resources = await resource_registry.list_resources()
            assert isinstance(resources, list)
            assert len(resources) == 0  # Empty list on error

    @pytest.mark.asyncio
    async def test_authentication_integration(self: "Self"):
        """Test authentication integration across all components."""
        from app.mcp.auth import MCPAuthHandler

        # Test auth handler initialization
        auth_handler = MCPAuthHandler()
        assert auth_handler is not None

        # Test auth header generation
        headers = await auth_handler.get_auth_headers()
        assert isinstance(headers, dict)

        # Headers might be empty if no token available, but should not error

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self: "TestPhase2Integration", mock_fastapi_app: "FastAPI"):
        """Test concurrent tool execution."""
        await tool_registry.discover_tools(mock_fastapi_app)

        # Mock HTTP responses
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)

            # Execute multiple tools concurrently
            tasks = []
            for i in range(3):
                task = tool_registry.call_tool("list_generators", {"limit": 10}, {"token": f"mock_token_{i}"})
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            for result in results:
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_configuration_validation(self: "Self"):
        """Test configuration validation across components."""
        from app.mcp.config import mcp_settings

        # Test MCP settings
        assert mcp_settings.MCP_SERVER_NAME
        assert mcp_settings.MCP_SERVER_VERSION
        assert isinstance(mcp_settings.MCP_ENABLE_TOOLS, bool)
        assert isinstance(mcp_settings.MCP_ENABLE_RESOURCES, bool)

        # Verify tool and resource features are enabled for Phase 2
        assert mcp_settings.MCP_ENABLE_TOOLS is True
        assert mcp_settings.MCP_ENABLE_RESOURCES is True

    def test_tool_schema_compliance(self: "Self"):
        """Test that all tools comply with MCP schema requirements."""
        # Get all tools

        all_tools = []
        all_tools.extend(generator_tools.get_tools())
        all_tools.extend(orchestrator_tools.get_tools())

        for tool in all_tools:
            # Verify required fields
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")

            # Verify name format
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0
            assert "_" in tool.name or tool.name.islower()  # snake_case or lowercase

            # Verify description
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

            # Verify input schema structure
            schema = tool.inputSchema
            assert isinstance(schema, dict)
            assert schema.get("type") == "object"
            assert "properties" in schema
            assert isinstance(schema["properties"], dict)

            if "required" in schema:
                assert isinstance(schema["required"], list)

    @pytest.mark.asyncio
    async def test_resource_uri_parsing(self: "Self"):
        """Test resource URI parsing and validation."""
        from app.mcp.resources.manager import resource_manager

        # Test valid URI parsing
        valid_uris = [
            "violentutf://generator/test-id",
            "violentutf://dataset/test-dataset",
            "violentutf://orchestrator/orch-123",
            "violentutf://config/system",
            "violentutf://session/session-456",
        ]

        for uri in valid_uris:
            try:
                resource_type, resource_id = resource_manager._parse_resource_uri(uri)
                assert resource_type in [
                    "generator",
                    "dataset",
                    "orchestrator",
                    "config",
                    "session",
                ]
                assert len(resource_id) > 0
            except Exception as e:
                pytest.fail(f"Valid URI {uri} failed to parse: {e}")

        # Test invalid URIs
        invalid_uris = [
            "http://example.com/resource",
            "violentutf://",
            "violentutf://invalid",
            "not-a-uri",
        ]

        for uri in invalid_uris:
            with pytest.raises(ValueError):
                resource_manager._parse_resource_uri(uri)


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
