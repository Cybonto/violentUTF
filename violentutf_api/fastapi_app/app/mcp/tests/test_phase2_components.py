# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Phase 2 Component Tests for ViolentUTF MCP Server."""

import asyncio
import logging
import os
import sys
import tempfile
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

# Mock environment variables to prevent path creation errors
with patch.dict(
    os.environ,
    {
        "APP_DATA_DIR": tempfile.mkdtemp(prefix="test_app_data_"),
        "CONFIG_DIR": tempfile.mkdtemp(prefix="test_config_"),
        "JWT_SECRET_KEY": "test_secret_key",
    },
):
    try:
        from app.mcp.config import mcp_settings
        from app.mcp.tools.generators import GeneratorConfigurationTools
        from app.mcp.tools.introspection import EndpointIntrospector, ViolentUTFToolFilter
        from app.mcp.tools.orchestrators import OrchestratorManagementTools
        from mcp.types import Resource, Tool
    except ImportError as e:
        # If imports fail, we'll skip the tests
        pytest.skip(f"Required modules not available: {e}")

logger = logging.getLogger(__name__)


class TestPhase2Components:
    """Unit tests for Phase 2 MCP components."""

    def test_generator_tools_creation(self) -> None:
        """Test generator tools creation and structure."""
        generator_tools = GeneratorConfigurationTools()
        tools = generator_tools.get_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Check for required generator tools
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "list_generators",
            "get_generator",
            "create_generator",
            "update_generator",
            "delete_generator",
            "test_generator",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing generator tool: {expected_tool}"

        # Validate tool structure
        for tool in tools:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert isinstance(tool.inputSchema, dict)
            assert tool.inputSchema.get("type") == "object"
            assert "properties" in tool.inputSchema

    def test_orchestrator_tools_creation(self) -> None:
        """Test orchestrator tools creation and structure."""
        orchestrator_tools = OrchestratorManagementTools()
        tools = orchestrator_tools.get_tools()

        assert isinstance(tools, list)
        assert len(tools) > 0

        # Check for required orchestrator tools
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "list_orchestrators",
            "get_orchestrator",
            "create_orchestrator",
            "start_orchestrator",
            "stop_orchestrator",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names, f"Missing orchestrator tool: {expected_tool}"

        # Validate tool structure
        for tool in tools:
            assert isinstance(tool, Tool)
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert isinstance(tool.inputSchema, dict)
            assert tool.inputSchema.get("type") == "object"
            assert "properties" in tool.inputSchema

    def test_tool_filter_functionality(self) -> None:
        """Test ViolentUTF tool filter functionality."""
        tool_filter = ViolentUTFToolFilter()

        # Test included endpoints
        included_endpoints = [
            "/api/v1/generators",
            "/api/v1/orchestrators",
            "/api/v1/datasets",
            "/api/v1/converters",
            "/api/v1/scorers",
        ]

        for endpoint in included_endpoints:
            assert tool_filter.should_include_endpoint(endpoint, "GET"), f"Should include {endpoint}"

        # Test excluded endpoints
        excluded_endpoints = ["/admin", "/debug", "/health", "/docs", "/auth/token"]

        for endpoint in excluded_endpoints:
            assert not tool_filter.should_include_endpoint(endpoint, "GET"), f"Should exclude {endpoint}"

    def test_endpoint_introspector_initialization(self) -> None:
        """Test endpoint introspector initialization."""
        from fastapi import FastAPI

        app = FastAPI()
        introspector = EndpointIntrospector(app)

        assert introspector.app == app
        assert introspector.tool_filter is not None
        assert isinstance(introspector.tool_filter, ViolentUTFToolFilter)

    def test_mcp_configuration(self) -> None:
        """Test MCP configuration settings."""
        # Test configuration values
        assert mcp_settings.MCP_SERVER_NAME
        assert mcp_settings.MCP_SERVER_VERSION
        assert isinstance(mcp_settings.MCP_ENABLE_TOOLS, bool)
        assert isinstance(mcp_settings.MCP_ENABLE_RESOURCES, bool)

        # For Phase 2, these should be enabled
        assert mcp_settings.MCP_ENABLE_TOOLS is True
        assert mcp_settings.MCP_ENABLE_RESOURCES is True

    def test_generator_tool_schemas(self) -> None:
        """Test generator tool input schemas."""
        generator_tools = GeneratorConfigurationTools()
        tools = generator_tools.get_tools()

        # Test specific tool schemas
        create_generator_tool = next((t for t in tools if t.name == "create_generator"), None)
        assert create_generator_tool is not None

        schema = create_generator_tool.inputSchema
        required_fields = schema.get("required", [])

        # Should require name, provider_type, model_name
        assert "name" in required_fields
        assert "provider_type" in required_fields
        assert "model_name" in required_fields

        # Check properties
        properties = schema.get("properties", {})
        assert "name" in properties
        assert "provider_type" in properties
        assert "model_name" in properties
        assert "parameters" in properties

    def test_orchestrator_tool_schemas(self) -> None:
        """Test orchestrator tool input schemas."""
        orchestrator_tools = OrchestratorManagementTools()
        tools = orchestrator_tools.get_tools()

        # Test create orchestrator tool schema
        create_orch_tool = next((t for t in tools if t.name == "create_orchestrator"), None)
        assert create_orch_tool is not None

        schema = create_orch_tool.inputSchema
        required_fields = schema.get("required", [])

        # Should require name, orchestrator_type, target_generators, dataset_name
        assert "name" in required_fields
        assert "orchestrator_type" in required_fields
        assert "target_generators" in required_fields
        assert "dataset_name" in required_fields

        # Check properties
        properties = schema.get("properties", {})
        assert "name" in properties
        assert "orchestrator_type" in properties
        assert "target_generators" in properties
        assert "dataset_name" in properties

    @pytest.mark.asyncio
    async def test_generator_tool_execution_mock(self) -> None:
        """Test generator tool execution with mocked HTTP calls."""
        generator_tools = GeneratorConfigurationTools()

        # Mock HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "generators": [
                    {"id": "test-gen-1", "name": "Test Generator", "provider_type": "openai", "model_name": "gpt-4"}
                ]
            }

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)

            # Test list generators execution
            result = await generator_tools.execute_tool(
                "list_generators", {"provider_type": "openai"}, {"token": "mock_token"}
            )

            assert isinstance(result, dict)
            assert "generators" in result
            assert len(result["generators"]) > 0

    @pytest.mark.asyncio
    async def test_orchestrator_tool_execution_mock(self) -> None:
        """Test orchestrator tool execution with mocked HTTP calls."""
        orchestrator_tools = OrchestratorManagementTools()

        # Mock HTTP client
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "orchestrators": [
                    {
                        "id": "test-orch-1",
                        "name": "Test Orchestrator",
                        "status": "completed",
                        "orchestrator_type": "red_teaming",
                    }
                ]
            }

            mock_client.return_value.__aenter__.return_value.request = AsyncMock(return_value=mock_response)

            # Test list orchestrators execution
            result = await orchestrator_tools.execute_tool(
                "list_orchestrators", {"status": "completed"}, {"token": "mock_token"}
            )

            assert isinstance(result, dict)
            assert "orchestrators" in result
            assert len(result["orchestrators"]) > 0

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        """Test error handling in tool execution."""
        generator_tools = GeneratorConfigurationTools()

        # Test unknown tool
        result = await generator_tools.execute_tool("unknown_tool", {}, None)

        assert "error" in result
        assert result["error"] == "unknown_tool"

        # Test execution with connection error
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=Exception("Connection failed")
            )

            result = await generator_tools.execute_tool("list_generators", {}, {"token": "mock_token"})

            assert "error" in result
            assert result["error"] == "execution_failed"

    def test_tool_naming_conventions(self) -> None:
        """Test that tool names follow proper conventions."""
        generator_tools = GeneratorConfigurationTools()
        orchestrator_tools = OrchestratorManagementTools()

        all_tools = []
        all_tools.extend(generator_tools.get_tools())
        all_tools.extend(orchestrator_tools.get_tools())

        for tool in all_tools:
            # Tool names should be snake_case
            assert tool.name.islower(), f"Tool name should be lowercase: {tool.name}"
            assert " " not in tool.name, f"Tool name should not contain spaces: {tool.name}"

            # Should contain underscores for multi-word names
            if len(tool.name.split("_")) > 1:
                assert "_" in tool.name, f"Multi-word tool name should use underscores: {tool.name}"

    def test_tool_description_quality(self) -> None:
        """Test that tool descriptions are meaningful."""
        generator_tools = GeneratorConfigurationTools()
        orchestrator_tools = OrchestratorManagementTools()

        all_tools = []
        all_tools.extend(generator_tools.get_tools())
        all_tools.extend(orchestrator_tools.get_tools())

        for tool in all_tools:
            # Description should be non-empty and meaningful
            assert len(tool.description) > 10, f"Tool description too short: {tool.name}"
            assert tool.description.strip(), f"Tool description is empty: {tool.name}"

            # Should start with capital letter
            assert tool.description[0].isupper(), f"Tool description should start with capital: {tool.name}"

    def test_schema_validation_completeness(self) -> None:
        """Test that schemas have proper validation rules."""
        generator_tools = GeneratorConfigurationTools()
        tools = generator_tools.get_tools()

        for tool in tools:
            schema = tool.inputSchema
            properties = schema.get("properties", {})

            # Check that enum properties have valid values
            for prop_name, prop_schema in properties.items():
                if "enum" in prop_schema:
                    enum_values = prop_schema["enum"]
                    assert len(enum_values) > 0, f"Empty enum for {tool.name}.{prop_name}"
                    assert all(
                        isinstance(v, str) for v in enum_values
                    ), f"Non-string enum values in {tool.name}.{prop_name}"

                # Check that numeric properties have proper constraints
                if prop_schema.get("type") in ["integer", "number"]:
                    if "minimum" in prop_schema:
                        assert isinstance(prop_schema["minimum"], (int, float))
                    if "maximum" in prop_schema:
                        assert isinstance(prop_schema["maximum"], (int, float))


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
