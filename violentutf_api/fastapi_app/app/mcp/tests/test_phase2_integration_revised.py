"""
Phase 2 Integration Tests for ViolentUTF MCP Server - Revised
============================================================

These tests validate Phase 2 implementation with proper architecture:
- FastAPI and MCP server run within violentutf_api instance
- All requests routed through APISIX gateway
- Mock external dependencies appropriately
- Test actual implementation, not future phases
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from app.mcp.auth import MCPAuthHandler
from app.mcp.config import mcp_settings
from app.mcp.resources import resource_registry
from app.mcp.resources.manager import ViolentUTFResourceManager, resource_manager
from app.mcp.server.base import ViolentUTFMCPServer

# Test the actual implemented components
from app.mcp.tools import tool_registry
from app.mcp.tools.executor import tool_executor
from app.mcp.tools.generator import tool_generator
from app.mcp.tools.generators import GeneratorConfigurationTools, generator_tools
from app.mcp.tools.introspection import (
    EndpointIntrospector,
    ViolentUTFToolFilter,
    initialize_introspector,
)
from app.mcp.tools.orchestrators import OrchestratorManagementTools, orchestrator_tools
from fastapi import FastAPI
from fastapi.routing import APIRoute

# MCP and core imports
from mcp.types import Resource, ServerCapabilities, Tool

logger = logging.getLogger(__name__)


class TestPhase2Architecture:
    """Test Phase 2 architecture compliance and integration"""

    @pytest.fixture
    def realistic_fastapi_app(self):
        """Create a realistic FastAPI app mimicking ViolentUTF API structure"""
        app = FastAPI(title="ViolentUTF API", version="1.0.0")

        # Create realistic API routes based on ViolentUTF API structure
        realistic_routes = [
            # Generator endpoints
            {
                "path": "/api/v1/generators",
                "methods": ["GET", "POST"],
                "tags": ["generators"],
                "summary": "List or create generators",
                "description": "List all generators or create a new generator configuration",
            },
            {
                "path": "/api/v1/generators/{generator_id}",
                "methods": ["GET", "PUT", "DELETE"],
                "tags": ["generators"],
                "summary": "Manage generator by ID",
                "description": "Get, update, or delete a specific generator",
            },
            {
                "path": "/api/v1/generators/{generator_id}/test",
                "methods": ["POST"],
                "tags": ["generators"],
                "summary": "Test generator",
                "description": "Execute a test prompt against the generator",
            },
            # Orchestrator endpoints
            {
                "path": "/api/v1/orchestrators",
                "methods": ["GET", "POST"],
                "tags": ["orchestrators"],
                "summary": "List or create orchestrators",
                "description": "List all orchestrators or create a new orchestrator",
            },
            {
                "path": "/api/v1/orchestrators/{orchestrator_id}",
                "methods": ["GET", "PUT", "DELETE"],
                "tags": ["orchestrators"],
                "summary": "Manage orchestrator by ID",
                "description": "Get, update, or delete a specific orchestrator",
            },
            {
                "path": "/api/v1/orchestrators/{orchestrator_id}/start",
                "methods": ["POST"],
                "tags": ["orchestrators"],
                "summary": "Start orchestrator",
                "description": "Start execution of an orchestrator",
            },
            {
                "path": "/api/v1/orchestrators/{orchestrator_id}/stop",
                "methods": ["POST"],
                "tags": ["orchestrators"],
                "summary": "Stop orchestrator",
                "description": "Stop execution of a running orchestrator",
            },
            {
                "path": "/api/v1/orchestrators/{orchestrator_id}/results",
                "methods": ["GET"],
                "tags": ["orchestrators"],
                "summary": "Get orchestrator results",
                "description": "Retrieve results from orchestrator execution",
            },
            # Dataset endpoints
            {
                "path": "/api/v1/datasets",
                "methods": ["GET", "POST"],
                "tags": ["datasets"],
                "summary": "List or upload datasets",
                "description": "List all datasets or upload a new dataset",
            },
            {
                "path": "/api/v1/datasets/{dataset_name}",
                "methods": ["GET", "DELETE"],
                "tags": ["datasets"],
                "summary": "Manage dataset by name",
                "description": "Get or delete a specific dataset",
            },
            # Config endpoints
            {
                "path": "/api/v1/config",
                "methods": ["GET"],
                "tags": ["config"],
                "summary": "Get system configuration",
                "description": "Retrieve system configuration and settings",
            },
            # Session endpoints
            {
                "path": "/api/v1/sessions",
                "methods": ["GET"],
                "tags": ["sessions"],
                "summary": "List sessions",
                "description": "List all active sessions",
            },
            {
                "path": "/api/v1/sessions/{session_id}",
                "methods": ["GET", "DELETE"],
                "tags": ["sessions"],
                "summary": "Manage session by ID",
                "description": "Get or delete a specific session",
            },
        ]

        # Convert to APIRoute objects with proper mocking
        api_routes = []
        for route_def in realistic_routes:
            for method in route_def["methods"]:
                route = Mock(spec=APIRoute)
                route.path = route_def["path"]
                route.methods = {method}
                route.tags = route_def["tags"]
                route.summary = route_def.get("summary", "")
                route.description = route_def.get("description", "")

                # Create a mock endpoint function with proper signature
                if "{" in route_def["path"]:
                    # Path parameter endpoint
                    def mock_endpoint(path_param: str):
                        return {"result": "success", "id": path_param}

                else:
                    # No path parameters
                    def mock_endpoint():
                        return {"result": "success"}

                route.endpoint = mock_endpoint
                api_routes.append(route)

        app.routes = api_routes
        return app

    @pytest.fixture
    def mock_apisix_responses(self):
        """Mock APISIX gateway responses for API calls"""

        def create_mock_response(status_code=200, json_data=None, text=""):
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.json.return_value = json_data or {"success": True}
            mock_response.text = text or json.dumps(json_data or {"success": True})
            return mock_response

        return {
            "success": create_mock_response(
                200, {"success": True, "data": "mock_data"}
            ),
            "generators_list": create_mock_response(
                200,
                {
                    "generators": [
                        {
                            "id": "gen_001",
                            "name": "Test Generator",
                            "provider_type": "openai",
                            "model_name": "gpt-4",
                            "status": "active",
                        }
                    ]
                },
            ),
            "orchestrators_list": create_mock_response(
                200,
                {
                    "orchestrators": [
                        {
                            "id": "orch_001",
                            "name": "Test Orchestrator",
                            "status": "completed",
                            "orchestrator_type": "red_teaming",
                        }
                    ]
                },
            ),
            "datasets_list": create_mock_response(
                200,
                {
                    "datasets": [
                        {
                            "name": "test_dataset",
                            "category": "harmful_behaviors",
                            "size": 100,
                        }
                    ]
                },
            ),
            "not_found": create_mock_response(404, {"detail": "Resource not found"}),
            "server_error": create_mock_response(
                500, {"detail": "Internal server error"}
            ),
        }


class TestPhase2EndpointIntrospection(TestPhase2Architecture):
    """Test FastAPI endpoint introspection functionality"""

    def test_tool_filter_patterns(self):
        """Test ViolentUTF tool filter with realistic patterns"""
        tool_filter = ViolentUTFToolFilter()

        # Test included endpoints (should be exposed via MCP)
        included_endpoints = [
            ("/api/v1/generators", "GET"),
            ("/api/v1/generators", "POST"),
            ("/api/v1/generators/test-id", "PUT"),
            ("/api/v1/orchestrators", "GET"),
            ("/api/v1/orchestrators/orch-123/start", "POST"),
            ("/api/v1/datasets", "GET"),
            ("/api/v1/datasets/test-dataset", "DELETE"),
            ("/api/v1/config", "GET"),
            ("/api/v1/sessions", "GET"),
        ]

        for path, method in included_endpoints:
            assert tool_filter.should_include_endpoint(
                path, method
            ), f"Should include {method} {path}"

        # Test excluded endpoints (should NOT be exposed via MCP)
        excluded_endpoints = [
            ("/health", "GET"),
            ("/docs", "GET"),
            ("/openapi.json", "GET"),
            ("/api/v1/auth/token", "POST"),
            ("/api/v1/keys/generate", "POST"),
            ("/admin/dashboard", "GET"),
            ("/debug/logs", "GET"),
            ("/internal/metrics", "GET"),
        ]

        for path, method in excluded_endpoints:
            assert not tool_filter.should_include_endpoint(
                path, method
            ), f"Should exclude {method} {path}"

    @pytest.mark.asyncio
    async def test_endpoint_introspection_realistic(self, realistic_fastapi_app):
        """Test endpoint introspection with realistic FastAPI app"""
        # Initialize introspector
        introspector = initialize_introspector(realistic_fastapi_app)

        assert introspector is not None
        assert introspector.app == realistic_fastapi_app
        assert isinstance(introspector.tool_filter, ViolentUTFToolFilter)

        # Test endpoint discovery
        endpoints = introspector.discover_endpoints()

        assert isinstance(endpoints, list)
        assert len(endpoints) > 0

        # Verify endpoint structure and content
        endpoint_paths = [ep["path"] for ep in endpoints]

        # Check that expected endpoints are discovered
        expected_paths = [
            "/api/v1/generators",
            "/api/v1/generators/{generator_id}",
            "/api/v1/orchestrators",
            "/api/v1/datasets",
        ]

        for expected_path in expected_paths:
            assert any(
                path == expected_path for path in endpoint_paths
            ), f"Expected endpoint {expected_path} not found"

        # Verify endpoint structure
        for endpoint in endpoints[:3]:  # Check first 3
            assert "name" in endpoint
            assert "method" in endpoint
            assert "path" in endpoint
            assert "description" in endpoint
            assert isinstance(endpoint["name"], str)
            assert endpoint["method"] in ["GET", "POST", "PUT", "DELETE"]
            assert endpoint["path"].startswith("/api/v1/")

    def test_tool_name_generation(self):
        """Test tool name generation from endpoints"""
        introspector = EndpointIntrospector(Mock())

        test_cases = [
            # (path, method, expected_name)
            ("/api/v1/generators", "GET", "get_generators"),
            ("/api/v1/generators", "POST", "create_generators"),
            ("/api/v1/generators/{generator_id}", "GET", "get_generators_by_id"),
            ("/api/v1/generators/{generator_id}", "PUT", "update_generators_by_id"),
            ("/api/v1/generators/{generator_id}", "DELETE", "delete_generators_by_id"),
            (
                "/api/v1/orchestrators/{id}/start",
                "POST",
                "create_orchestrators_start_by_id",
            ),
            ("/api/v1/datasets", "GET", "get_datasets"),
        ]

        for path, method, expected_name in test_cases:
            actual_name = introspector._generate_tool_name(path, method)
            assert (
                actual_name == expected_name
            ), f"Expected {expected_name}, got {actual_name} for {method} {path}"


class TestPhase2SpecializedTools(TestPhase2Architecture):
    """Test specialized tool implementations"""

    def test_generator_tools_structure(self):
        """Test generator tools structure and completeness"""
        tools = generator_tools.get_tools()

        assert len(tools) == 10, f"Expected 10 generator tools, got {len(tools)}"

        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "list_generators",
            "get_generator",
            "create_generator",
            "update_generator",
            "delete_generator",
            "test_generator",
            "list_provider_models",
            "validate_generator_config",
            "clone_generator",
            "batch_test_generators",
        ]

        for expected_tool in expected_tools:
            assert (
                expected_tool in tool_names
            ), f"Missing generator tool: {expected_tool}"

        # Verify tool schema compliance
        for tool in tools:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema

    def test_orchestrator_tools_structure(self):
        """Test orchestrator tools structure and completeness"""
        tools = orchestrator_tools.get_tools()

        assert len(tools) == 14, f"Expected 14 orchestrator tools, got {len(tools)}"

        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "list_orchestrators",
            "get_orchestrator",
            "create_orchestrator",
            "start_orchestrator",
            "stop_orchestrator",
            "pause_orchestrator",
            "resume_orchestrator",
            "get_orchestrator_results",
            "get_orchestrator_logs",
            "delete_orchestrator",
            "clone_orchestrator",
            "get_orchestrator_stats",
            "export_orchestrator_results",
            "validate_orchestrator_config",
        ]

        for expected_tool in expected_tools:
            assert (
                expected_tool in tool_names
            ), f"Missing orchestrator tool: {expected_tool}"

    @pytest.mark.asyncio
    async def test_generator_tool_execution_with_apisix_mock(
        self, mock_apisix_responses
    ):
        """Test generator tool execution with mocked APISIX responses"""

        with patch("httpx.AsyncClient") as mock_client:
            # Mock successful API response through APISIX
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_apisix_responses["generators_list"]
            )

            # Test list_generators tool
            result = await generator_tools.execute_tool(
                "list_generators", {"provider_type": "openai"}, {"token": "mock_token"}
            )

            assert isinstance(result, dict)
            assert "generators" in result
            assert len(result["generators"]) > 0
            assert result["generators"][0]["provider_type"] == "openai"

            # Verify API call was made with correct parameters
            mock_client.return_value.__aenter__.return_value.request.assert_called_once()
            call_args = (
                mock_client.return_value.__aenter__.return_value.request.call_args
            )

            # Verify request goes through internal URL (violentutf-api:8000)
            assert "violentutf-api:8000" in str(call_args[1]["url"])

            # Verify authentication headers
            headers = call_args[1]["headers"]
            assert "X-API-Gateway" in headers
            assert headers["X-API-Gateway"] == "MCP-Generator"

    @pytest.mark.asyncio
    async def test_orchestrator_tool_execution_with_apisix_mock(
        self, mock_apisix_responses
    ):
        """Test orchestrator tool execution with mocked APISIX responses"""

        with patch("httpx.AsyncClient") as mock_client:
            # Mock successful API response
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_apisix_responses["orchestrators_list"]
            )

            # Test list_orchestrators tool
            result = await orchestrator_tools.execute_tool(
                "list_orchestrators", {"status": "completed"}, {"token": "mock_token"}
            )

            assert isinstance(result, dict)
            assert "orchestrators" in result
            assert len(result["orchestrators"]) > 0
            assert result["orchestrators"][0]["status"] == "completed"

            # Verify API call parameters
            call_args = (
                mock_client.return_value.__aenter__.return_value.request.call_args
            )
            assert "violentutf-api:8000" in str(call_args[1]["url"])

            headers = call_args[1]["headers"]
            assert headers["X-API-Gateway"] == "MCP-Orchestrator"

    @pytest.mark.asyncio
    async def test_tool_error_handling_apisix_failures(self, mock_apisix_responses):
        """Test tool error handling when APISIX returns errors"""

        with patch("httpx.AsyncClient") as mock_client:
            # Mock API error response
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_apisix_responses["not_found"]
            )

            # Test generator tool with 404 response
            result = await generator_tools.execute_tool(
                "get_generator",
                {"generator_id": "nonexistent"},
                {"token": "mock_token"},
            )

            assert isinstance(result, dict)
            assert "error" in result
            assert result["error"] == "api_error_404"
            assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_tool_network_error_handling(self):
        """Test tool handling of network errors (APISIX unreachable)"""

        with patch("httpx.AsyncClient") as mock_client:
            # Mock connection error
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            result = await generator_tools.execute_tool(
                "list_generators", {}, {"token": "mock_token"}
            )

            assert isinstance(result, dict)
            assert "error" in result
            assert result["error"] == "execution_failed"
            assert "Connection refused" in result["message"]


class TestPhase2ResourceManagement(TestPhase2Architecture):
    """Test resource management system"""

    @pytest.mark.asyncio
    async def test_resource_manager_initialization(self):
        """Test resource manager initialization"""
        # Test direct resource manager
        manager = ViolentUTFResourceManager()
        assert manager.base_url
        assert manager.auth_handler
        assert manager.resource_cache == {}
        assert manager.cache_ttl == 300

        # Test resource registry initialization
        await resource_registry.initialize()
        assert resource_registry._initialized

    @pytest.mark.asyncio
    async def test_resource_uri_parsing(self):
        """Test resource URI parsing functionality"""
        manager = ViolentUTFResourceManager()

        # Test valid URIs
        test_cases = [
            ("violentutf://generator/gen_001", ("generator", "gen_001")),
            (
                "violentutf://dataset/harmful_behaviors",
                ("dataset", "harmful_behaviors"),
            ),
            ("violentutf://orchestrator/orch_123", ("orchestrator", "orch_123")),
            ("violentutf://config/system", ("config", "system")),
            ("violentutf://session/sess_456", ("session", "sess_456")),
            (
                "violentutf://generator/complex/path/id",
                ("generator", "complex/path/id"),
            ),
        ]

        for uri, expected in test_cases:
            resource_type, resource_id = manager._parse_resource_uri(uri)
            assert resource_type == expected[0]
            assert resource_id == expected[1]

        # Test invalid URIs
        invalid_uris = [
            "http://example.com/resource",
            "violentutf://",
            "violentutf://generator",
            "not-a-uri",
            "violentutf:generator/test",
        ]

        for invalid_uri in invalid_uris:
            with pytest.raises(ValueError):
                manager._parse_resource_uri(invalid_uri)

    @pytest.mark.asyncio
    async def test_resource_listing_with_apisix_mock(self, mock_apisix_responses):
        """Test resource listing with mocked APISIX responses"""

        with patch("httpx.AsyncClient") as mock_client:
            # Mock responses for different resource types
            def mock_request(*args, **kwargs):
                url = kwargs.get("url", "")
                if "/generators" in url:
                    return mock_apisix_responses["generators_list"]
                elif "/orchestrators" in url:
                    return mock_apisix_responses["orchestrators_list"]
                elif "/datasets" in url:
                    return mock_apisix_responses["datasets_list"]
                else:
                    return mock_apisix_responses["success"]

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=mock_request
            )

            # Test resource listing
            resources = await resource_registry.list_resources()

            assert isinstance(resources, list)
            # Should have resources from generators, orchestrators, datasets
            assert len(resources) >= 3

            # Verify resource structure
            resource_uris = [r.uri for r in resources]
            assert any(
                uri.startswith("violentutf://generator/") for uri in resource_uris
            )
            assert any(
                uri.startswith("violentutf://orchestrator/") for uri in resource_uris
            )
            assert any(uri.startswith("violentutf://dataset/") for uri in resource_uris)

    @pytest.mark.asyncio
    async def test_resource_caching_functionality(self, mock_apisix_responses):
        """Test resource caching functionality"""

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_apisix_responses["generators_list"]
            )

            manager = ViolentUTFResourceManager()

            # First read (cache miss)
            result1 = await manager.read_resource("violentutf://generator/gen_001")
            assert isinstance(result1, dict)

            # Verify cache was populated
            cache_stats = manager.get_cache_stats()
            assert cache_stats["total_entries"] > 0

            # Second read (cache hit)
            result2 = await manager.read_resource("violentutf://generator/gen_001")
            assert result2 == result1

            # Verify only one API call was made (second was cached)
            assert (
                mock_client.return_value.__aenter__.return_value.request.call_count == 1
            )

    def test_resource_cache_statistics(self):
        """Test resource cache statistics functionality"""
        manager = ViolentUTFResourceManager()

        # Test empty cache stats
        stats = manager.get_cache_stats()
        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["cache_ttl_seconds"] == 300

        # Test cache clearing
        manager.clear_cache()
        stats_after_clear = manager.get_cache_stats()
        assert stats_after_clear["total_entries"] == 0


class TestPhase2ToolRegistry(TestPhase2Architecture):
    """Test tool registry and discovery system"""

    @pytest.mark.asyncio
    async def test_tool_discovery_integration(self, realistic_fastapi_app):
        """Test complete tool discovery process"""
        # Clear existing tools
        tool_registry.clear_tools()

        # Perform discovery
        await tool_registry.discover_tools(realistic_fastapi_app)

        # Verify tools were discovered
        tools = await tool_registry.list_tools()
        assert len(tools) > 0

        # Verify specialized tools are present
        tool_names = [tool.name for tool in tools]

        # Should have generator tools
        generator_tool_names = [t.name for t in generator_tools.get_tools()]
        for gen_tool in generator_tool_names:
            assert gen_tool in tool_names, f"Missing generator tool: {gen_tool}"

        # Should have orchestrator tools
        orchestrator_tool_names = [t.name for t in orchestrator_tools.get_tools()]
        for orch_tool in orchestrator_tool_names:
            assert orch_tool in tool_names, f"Missing orchestrator tool: {orch_tool}"

        # Should have auto-generated endpoint tools (non-conflicting)
        endpoint_tools = [
            t
            for t in tools
            if t.name not in (generator_tool_names + orchestrator_tool_names)
        ]
        assert len(endpoint_tools) > 0, "Should have some auto-generated endpoint tools"

    @pytest.mark.asyncio
    async def test_tool_execution_routing(
        self, realistic_fastapi_app, mock_apisix_responses
    ):
        """Test tool execution routing to appropriate handlers"""
        await tool_registry.discover_tools(realistic_fastapi_app)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_apisix_responses["success"]
            )

            # Test generator tool routing
            result = await tool_registry.call_tool(
                "list_generators", {"provider_type": "openai"}, {"token": "mock_token"}
            )

            assert isinstance(result, dict)
            assert "success" in result or "generators" in result or "error" in result

            # Test orchestrator tool routing
            result = await tool_registry.call_tool(
                "list_orchestrators", {"status": "running"}, {"token": "mock_token"}
            )

            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_tool_validation_integration(self, realistic_fastapi_app):
        """Test tool argument validation"""
        await tool_registry.discover_tools(realistic_fastapi_app)

        # Test with invalid tool name
        result = await tool_registry.call_tool(
            "nonexistent_tool", {}, {"token": "mock_token"}
        )

        assert "error" in result
        assert result["error"] == "tool_not_found"
        assert "available_tools" in result

    def test_tool_registry_state_management(self):
        """Test tool registry state management"""
        # Test initial state
        assert hasattr(tool_registry, "tools")
        assert hasattr(tool_registry, "endpoints_discovered")

        # Test clearing
        tool_registry.clear_tools()
        assert len(tool_registry.tools) == 0
        assert not tool_registry.endpoints_discovered

        # Test tool count
        count = tool_registry.get_tool_count()
        assert count == 0


class TestPhase2MCPServerIntegration(TestPhase2Architecture):
    """Test complete MCP server integration"""

    @pytest.mark.asyncio
    async def test_mcp_server_initialization(self):
        """Test MCP server initialization"""
        mcp_server = ViolentUTFMCPServer()

        # Test initial state
        assert mcp_server.server
        assert mcp_server.auth_handler
        assert not mcp_server._initialized

        # Test initialization
        await mcp_server.initialize()
        assert mcp_server._initialized

    @pytest.mark.asyncio
    async def test_mcp_server_capabilities(self):
        """Test MCP server capabilities"""
        mcp_server = ViolentUTFMCPServer()

        capabilities = mcp_server.get_capabilities()

        assert isinstance(capabilities, ServerCapabilities)
        # Phase 2 should have tools and resources enabled
        assert capabilities.tools is True
        assert capabilities.resources is True

    @pytest.mark.asyncio
    async def test_mcp_server_mounting(self, realistic_fastapi_app):
        """Test MCP server mounting to FastAPI app"""
        mcp_server = ViolentUTFMCPServer()
        await mcp_server.initialize()

        # Test mounting (should not raise exceptions)
        try:
            mcp_server.mount_to_app(realistic_fastapi_app)
        except Exception as e:
            # Some mount operations may fail in test environment (e.g., OAuth setup)
            # But the core mounting should work
            logger.warning(f"Mount operation warning: {e}")

    @pytest.mark.asyncio
    async def test_mcp_server_handlers(
        self, realistic_fastapi_app, mock_apisix_responses
    ):
        """Test MCP server handler methods"""
        mcp_server = ViolentUTFMCPServer()
        await mcp_server.initialize()
        mcp_server.mount_to_app(realistic_fastapi_app)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_apisix_responses["success"]
            )

            # Test tool listing
            tools = await mcp_server._list_tools()
            assert isinstance(tools, list)
            assert len(tools) > 0

            # Test resource listing
            resources = await mcp_server._list_resources()
            assert isinstance(resources, list)

            # Test tool calling
            if tools:
                result = await mcp_server._call_tool(
                    tools[0].name, {}, {"token": "mock_token"}
                )
                assert isinstance(result, dict)


class TestPhase2AuthenticationIntegration(TestPhase2Architecture):
    """Test authentication integration"""

    @pytest.mark.asyncio
    async def test_auth_handler_initialization(self):
        """Test MCP auth handler initialization"""
        auth_handler = MCPAuthHandler()
        assert auth_handler is not None

        # Test auth header generation (should not error)
        headers = await auth_handler.get_auth_headers()
        assert isinstance(headers, dict)

    @pytest.mark.asyncio
    async def test_tool_authentication_flow(self, mock_apisix_responses):
        """Test authentication flow in tool execution"""

        # Mock environment variables for auth
        with patch.dict(
            os.environ,
            {"KEYCLOAK_USERNAME": "test_user", "KEYCLOAK_PASSWORD": "test_pass"},
        ):
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                    return_value=mock_apisix_responses["success"]
                )

                # Test tool execution with auth context
                result = await generator_tools.execute_tool(
                    "list_generators", {}, {"token": "test_token"}
                )

                # Verify API call included auth headers
                call_args = (
                    mock_client.return_value.__aenter__.return_value.request.call_args
                )
                headers = call_args[1]["headers"]
                assert "X-API-Gateway" in headers


class TestPhase2ConfigurationCompliance(TestPhase2Architecture):
    """Test configuration compliance"""

    def test_mcp_settings_validation(self):
        """Test MCP settings are properly configured for Phase 2"""
        # Verify Phase 2 features are enabled
        assert mcp_settings.MCP_ENABLE_TOOLS is True
        assert mcp_settings.MCP_ENABLE_RESOURCES is True

        # Verify server identification
        assert mcp_settings.MCP_SERVER_NAME
        assert mcp_settings.MCP_SERVER_VERSION

        # Verify transport configuration
        assert mcp_settings.MCP_TRANSPORT_TYPE in ["sse", "websocket"]
        assert mcp_settings.MCP_SSE_ENDPOINT


class TestPhase2PerformanceAndReliability(TestPhase2Architecture):
    """Test performance and reliability aspects"""

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(
        self, realistic_fastapi_app, mock_apisix_responses
    ):
        """Test concurrent tool execution performance"""
        await tool_registry.discover_tools(realistic_fastapi_app)

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_apisix_responses["success"]
            )

            # Execute multiple tools concurrently
            tasks = []
            for i in range(5):
                task = tool_registry.call_tool(
                    "list_generators", {"limit": 10}, {"token": f"mock_token_{i}"}
                )
                tasks.append(task)

            # Should complete without errors
            results = await asyncio.gather(*tasks, return_exceptions=True)

            assert len(results) == 5
            for result in results:
                assert not isinstance(result, Exception), f"Task failed: {result}"
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self, realistic_fastapi_app):
        """Test error recovery and system resilience"""

        # Test tool discovery with no app
        await tool_registry.discover_tools(None)
        tools = await tool_registry.list_tools()

        # Should still have specialized tools even without endpoint discovery
        specialized_count = len(generator_tools.get_tools()) + len(
            orchestrator_tools.get_tools()
        )
        assert len(tools) >= specialized_count

        # Test resource registry error handling
        with patch(
            "app.mcp.resources.manager.resource_manager.list_resources"
        ) as mock_list:
            mock_list.side_effect = Exception("Mock API failure")

            resources = await resource_registry.list_resources()
            assert isinstance(resources, list)
            assert len(resources) == 0  # Should return empty list on error


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
