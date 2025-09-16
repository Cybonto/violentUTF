# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP Generator Configuration Tools."""
import logging
from typing import Any, Dict, List, Optional, Self
from urllib.parse import urljoin

import httpx
from mcp.types import Tool

from app.core.config import settings
from app.mcp.auth import MCPAuthHandler

logger = logging.getLogger(__name__)


class GeneratorConfigurationTools:
    """MCP tools for generator configuration and management."""

    def __init__(self: "Self") -> None:
        """Initialize instance."""
        self.base_url = settings.VIOLENTUTF_API_URL or "http://localhost:8000"

        # Use internal URL for direct API access from within container
        if self.base_url and "localhost:9080" in self.base_url:
            self.base_url = "http://violentutf-api:8000"

        self.auth_handler = MCPAuthHandler()

    def get_tools(self: "Self") -> List[Tool]:
        """Get all generator configuration tools."""
        return [
            self._create_list_generators_tool(),
            self._create_get_generator_tool(),
            self._create_create_generator_tool(),
            self._create_update_generator_tool(),
            self._create_delete_generator_tool(),
            self._create_test_generator_tool(),
            self._create_list_provider_models_tool(),
            self._create_validate_generator_config_tool(),
            self._create_clone_generator_tool(),
            self._create_batch_test_generators_tool(),
        ]

    def _create_list_generators_tool(self: "Self") -> Tool:
        """Create tool for listing generators."""
        return Tool(
            name="list_generators",
            description="List all configured generators with filtering options",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider_type": {
                        "type": "string",
                        "description": "Filter by provider type (openai, anthropic, ollama, etc.)",
                        "enum": [
                            "openai",
                            "anthropic",
                            "ollama",
                            "open_webui",
                            "azure_openai",
                        ],
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by generator status",
                        "enum": ["active", "inactive", "error"],
                    },
                    "include_test_results": {
                        "type": "boolean",
                        "description": "Include latest test results",
                        "default": False,
                    },
                },
                "required": [],
            },
        )

    def _create_get_generator_tool(self: "Self") -> Tool:
        """Create tool for getting generator details."""
        return Tool(
            name="get_generator",
            description="Get detailed configuration and status of a specific generator",
            inputSchema={
                "type": "object",
                "properties": {
                    "generator_id": {
                        "type": "string",
                        "description": "Unique identifier of the generator",
                    },
                    "include_test_history": {
                        "type": "boolean",
                        "description": "Include test execution history",
                        "default": False,
                    },
                },
                "required": ["generator_id"],
            },
        )

    def _create_create_generator_tool(self: "Self") -> Tool:
        """Create tool for creating new generators."""
        return Tool(
            name="create_generator",
            description="Create a new generator configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Human-readable name for the generator",
                    },
                    "provider_type": {
                        "type": "string",
                        "description": "AI provider type",
                        "enum": [
                            "openai",
                            "anthropic",
                            "ollama",
                            "open_webui",
                            "azure_openai",
                        ],
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Model name (e.g., gpt-4, claude-3-sonnet)",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Model parameters (temperature, max_tokens, etc.)",
                        "properties": {
                            "temperature": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 2,
                            },
                            "max_tokens": {"type": "integer", "minimum": 1},
                            "top_p": {"type": "number", "minimum": 0, "maximum": 1},
                            "frequency_penalty": {
                                "type": "number",
                                "minimum": -2,
                                "maximum": 2,
                            },
                            "presence_penalty": {
                                "type": "number",
                                "minimum": -2,
                                "maximum": 2,
                            },
                        },
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Optional system prompt for the generator",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether the generator is enabled",
                        "default": True,
                    },
                    "test_after_creation": {
                        "type": "boolean",
                        "description": "Test the generator after creation",
                        "default": True,
                    },
                },
                "required": ["name", "provider_type", "model_name"],
            },
        )

    def _create_update_generator_tool(self: "Self") -> Tool:
        """Create tool for updating generators."""
        return Tool(
            name="update_generator",
            description="Update an existing generator configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "generator_id": {
                        "type": "string",
                        "description": "Unique identifier of the generator to update",
                    },
                    "name": {
                        "type": "string",
                        "description": "Updated name for the generator",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Updated model parameters",
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Updated system prompt",
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable/disable the generator",
                    },
                    "test_after_update": {
                        "type": "boolean",
                        "description": "Test the generator after update",
                        "default": True,
                    },
                },
                "required": ["generator_id"],
            },
        )

    def _create_delete_generator_tool(self: "Self") -> Tool:
        """Create tool for deleting generators."""
        return Tool(
            name="delete_generator",
            description="Delete a generator configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "generator_id": {
                        "type": "string",
                        "description": "Unique identifier of the generator to delete",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force deletion even if generator is in use",
                        "default": False,
                    },
                },
                "required": ["generator_id"],
            },
        )

    def _create_test_generator_tool(self: "Self") -> Tool:
        """Create tool for testing generators."""
        return Tool(
            name="test_generator",
            description="Test a generator with a sample prompt",
            inputSchema={
                "type": "object",
                "properties": {
                    "generator_id": {
                        "type": "string",
                        "description": "Unique identifier of the generator to test",
                    },
                    "test_prompt": {
                        "type": "string",
                        "description": "Test prompt to send to the generator",
                        "default": "Hello, please respond with a brief greeting.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Test timeout in seconds",
                        "default": 30,
                        "minimum": 5,
                        "maximum": 120,
                    },
                },
                "required": ["generator_id"],
            },
        )

    def _create_list_provider_models_tool(self: "Self") -> Tool:
        """Create tool for listing available models."""
        return Tool(
            name="list_provider_models",
            description="List available models for a specific provider",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider_type": {
                        "type": "string",
                        "description": "AI provider type",
                        "enum": [
                            "openai",
                            "anthropic",
                            "ollama",
                            "open_webui",
                            "azure_openai",
                        ],
                    },
                    "include_pricing": {
                        "type": "boolean",
                        "description": "Include pricing information if available",
                        "default": False,
                    },
                },
                "required": ["provider_type"],
            },
        )

    def _create_validate_generator_config_tool(self: "Self") -> Tool:
        """Create tool for validating generator configuration."""
        return Tool(
            name="validate_generator_config",
            description="Validate a generator configuration without creating it",
            inputSchema={
                "type": "object",
                "properties": {
                    "provider_type": {
                        "type": "string",
                        "description": "AI provider type",
                        "enum": [
                            "openai",
                            "anthropic",
                            "ollama",
                            "open_webui",
                            "azure_openai",
                        ],
                    },
                    "model_name": {
                        "type": "string",
                        "description": "Model name to validate",
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Model parameters to validate",
                    },
                    "test_connectivity": {
                        "type": "boolean",
                        "description": "Test connectivity to the provider",
                        "default": True,
                    },
                },
                "required": ["provider_type", "model_name"],
            },
        )

    def _create_clone_generator_tool(self: "Self") -> Tool:
        """Create tool for cloning generators."""
        return Tool(
            name="clone_generator",
            description="Clone an existing generator with modifications",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_generator_id": {
                        "type": "string",
                        "description": "ID of the generator to clone",
                    },
                    "new_name": {
                        "type": "string",
                        "description": "Name for the cloned generator",
                    },
                    "parameter_overrides": {
                        "type": "object",
                        "description": "Parameters to override in the clone",
                    },
                    "model_override": {
                        "type": "string",
                        "description": "Override model name in the clone",
                    },
                    "test_after_clone": {
                        "type": "boolean",
                        "description": "Test the cloned generator",
                        "default": True,
                    },
                },
                "required": ["source_generator_id", "new_name"],
            },
        )

    def _create_batch_test_generators_tool(self: "Self") -> Tool:
        """Create tool for batch testing generators."""
        return Tool(
            name="batch_test_generators",
            description="Test multiple generators with the same prompt",
            inputSchema={
                "type": "object",
                "properties": {
                    "generator_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of generator IDs to test",
                    },
                    "test_prompt": {
                        "type": "string",
                        "description": "Test prompt for all generators",
                        "default": "Hello, please respond with a brief greeting.",
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Test timeout per generator in seconds",
                        "default": 30,
                        "minimum": 5,
                        "maximum": 120,
                    },
                    "parallel_execution": {
                        "type": "boolean",
                        "description": "Execute tests in parallel",
                        "default": True,
                    },
                },
                "required": ["generator_ids"],
            },
        )

    async def execute_tool(
        self: "Self",
        tool_name: str,
        arguments: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a generator configuration tool."""
        logger.info("Executing generator tool: %s", tool_name)

        try:
            if tool_name == "list_generators":
                return await self._execute_list_generators(arguments)
            elif tool_name == "get_generator":
                return await self._execute_get_generator(arguments)
            elif tool_name == "create_generator":
                return await self._execute_create_generator(arguments)
            elif tool_name == "update_generator":
                return await self._execute_update_generator(arguments)
            elif tool_name == "delete_generator":
                return await self._execute_delete_generator(arguments)
            elif tool_name == "test_generator":
                return await self._execute_test_generator(arguments)
            elif tool_name == "list_provider_models":
                return await self._execute_list_provider_models(arguments)
            elif tool_name == "validate_generator_config":
                return await self._execute_validate_generator_config(arguments)
            elif tool_name == "clone_generator":
                return await self._execute_clone_generator(arguments)
            elif tool_name == "batch_test_generators":
                return await self._execute_batch_test_generators(arguments)
            else:
                return {
                    "error": "unknown_tool",
                    "message": f"Unknown generator tool: {tool_name}",
                }

        except (AttributeError, KeyError, ValueError, TypeError) as e:
            logger.error("Error executing generator tool %s: %s", tool_name, e)
            return {
                "error": "execution_failed",
                "message": str(e),
                "tool_name": tool_name,
            }

    async def _execute_list_generators(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute list generators tool."""
        params = {}

        if "provider_type" in args:
            params["provider_type"] = args["provider_type"]
        if "status" in args:
            params["status"] = args["status"]
        if "include_test_results" in args:
            params["include_test_results"] = args["include_test_results"]

        return await self._api_request("GET", "/api/v1/generators", params=params)

    async def _execute_get_generator(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get generator tool."""
        generator_id = args["generator_id"]

        params = {}
        if "include_test_history" in args:
            params["include_test_history"] = args["include_test_history"]

        return await self._api_request("GET", f"/api/v1/generators/{generator_id}", params=params)

    async def _execute_create_generator(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create generator tool."""
        return await self._api_request("POST", "/api/v1/generators", json=args)

    async def _execute_update_generator(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute update generator tool."""
        generator_id = args.pop("generator_id")

        return await self._api_request("PUT", f"/api/v1/generators/{generator_id}", json=args)

    async def _execute_delete_generator(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute delete generator tool."""
        generator_id = args["generator_id"]

        params = {}
        if "force" in args:
            params["force"] = args["force"]

        return await self._api_request("DELETE", f"/api/v1/generators/{generator_id}", params=params)

    async def _execute_test_generator(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute test generator tool."""
        generator_id = args["generator_id"]

        test_data = {
            "test_prompt": args.get("test_prompt", "Hello, please respond with a brief greeting."),
            "timeout_seconds": args.get("timeout_seconds", 30),
        }

        return await self._api_request("POST", f"/api/v1/generators/{generator_id}/test", json=test_data)

    async def _execute_list_provider_models(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute list provider models tool."""
        provider_type = args["provider_type"]

        params = {}
        if "include_pricing" in args:
            params["include_pricing"] = args["include_pricing"]

        return await self._api_request("GET", f"/api/v1/generators/providers/{provider_type}/models", params=params)

    async def _execute_validate_generator_config(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validate generator config tool."""
        return await self._api_request("POST", "/api/v1/generators/validate", json=args)

    async def _execute_clone_generator(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute clone generator tool."""
        source_id = args["source_generator_id"]

        clone_data = {
            "new_name": args["new_name"],
            "parameter_overrides": args.get("parameter_overrides", {}),
            "model_override": args.get("model_override"),
            "test_after_clone": args.get("test_after_clone", True),
        }

        return await self._api_request("POST", f"/api/v1/generators/{source_id}/clone", json=clone_data)

    async def _execute_batch_test_generators(self: "Self", args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute batch test generators tool."""
        return await self._api_request("POST", "/api/v1/generators/batch-test", json=args)

    async def _api_request(self: "Self", method: str, path: str, **kwargs: object) -> Dict[str, Any]:
        """Make authenticated API request."""
        headers = {"Content-Type": "application/json", "X-API-Gateway": "MCP-Generator"}

        # Add authentication headers if available
        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)

        url = urljoin(self.base_url, path)
        timeout = 60.0  # Longer timeout for generator operations

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(method=method, url=url, headers=headers, **kwargs)

                logger.debug("Generator API call: %s %s -> %s", method, url, response.status_code)

                if response.status_code >= 400:
                    error_detail = "Unknown error"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", str(error_data))
                    except (ValueError, KeyError, TypeError):
                        error_detail = response.text

                    return {
                        "error": f"api_error_{response.status_code}",
                        "message": error_detail,
                        "status_code": response.status_code,
                    }

                return response.json()

            except httpx.TimeoutException:
                logger.error("Timeout on generator API call: %s", url)
                return {"error": "timeout", "message": "Generator API call timed out"}
            except httpx.ConnectError:
                logger.error("Connection error on generator API call: %s", url)
                return {
                    "error": "connection_error",
                    "message": "Could not connect to ViolentUTF API",
                }
            except (ValueError, TypeError, OSError) as e:
                logger.error("Unexpected error on generator API call %s: %s", url, e)
                return {"error": "unexpected_error", "message": str(e)}


# Global generator tools instance
generator_tools = GeneratorConfigurationTools()
