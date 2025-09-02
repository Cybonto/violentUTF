# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP Tools Module."""
import logging
from typing import Any, Dict, List, Optional, Self, cast

from app.mcp.tools.executor import tool_executor
from app.mcp.tools.generator import tool_generator
from app.mcp.tools.generators import generator_tools
from app.mcp.tools.introspection import get_introspector, initialize_introspector
from app.mcp.tools.orchestrators import orchestrator_tools
from fastapi import FastAPI
from mcp.types import Tool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for MCP tools with FastAPI endpoint introspection."""

    def __init__(self: "Self") -> None:
        """Initialize instance."""
        self.tools: Dict[str, Tool] = {}

        self.endpoints_discovered = False

    async def discover_tools(self: "Self", app: Optional["FastAPI"] = None) -> None:
        """Discover and register available tools from FastAPI endpoints and specialized tools."""
        logger.info("Discovering MCP tools from FastAPI endpoints and specialized tools...")

        try:
            # Clear existing tools
            self.tools.clear()

            # Add specialized generator tools
            generator_tools_list = generator_tools.get_tools()
            for tool in generator_tools_list:
                self.tools[tool.name] = tool
            logger.info("Registered %s specialized generator tools", len(generator_tools_list))

            # Add specialized orchestrator tools
            orchestrator_tools_list = orchestrator_tools.get_tools()
            for tool in orchestrator_tools_list:
                self.tools[tool.name] = tool
            logger.info(
                "Registered %s specialized orchestrator tools",
                len(orchestrator_tools_list),
            )

            # Initialize introspector if app provided for generic endpoint discovery
            if app and get_introspector() is None:
                initialize_introspector(app)

            introspector = get_introspector()
            if introspector:
                # Discover endpoints
                endpoints = introspector.discover_endpoints()
                logger.info("Found %s discoverable endpoints", len(endpoints))

                # Generate MCP tools from endpoints (excluding those already covered by specialized tools)
                endpoint_tools = tool_generator.generate_tools_from_endpoints(endpoints)

                # Add endpoint tools that don't conflict with specialized tools
                for tool in endpoint_tools:
                    if tool.name not in self.tools:
                        self.tools[tool.name] = tool

                logger.info("Added %s endpoint-based tools", len(endpoint_tools))
            else:
                logger.warning("No introspector available, skipping endpoint discovery")

            self.endpoints_discovered = True
            logger.info("Successfully registered %s total MCP tools", len(self.tools))

            # Log tool categories
            specialized_tools = len(generator_tools_list) + len(orchestrator_tools_list)
            endpoint_tools_count = len(self.tools) - specialized_tools
            logger.info(
                "Tool breakdown: %s specialized, %s endpoint-based",
                specialized_tools,
                endpoint_tools_count,
            )

        except (ImportError, AttributeError, ValueError, KeyError) as e:
            logger.error("Error discovering tools: %s", e)
            # Don't raise, allow MCP server to continue with available tools

    async def list_tools(self: "Self") -> List[Tool]:
        """List all available tools."""
        if not self.endpoints_discovered:

            # Attempt discovery if not done yet
            await self.discover_tools()

        tools_list = list(self.tools.values())
        logger.debug("Listing %s available tools", len(tools_list))
        return tools_list

    async def call_tool(
        self: "Self",
        name: str,
        arguments: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a tool by name."""
        logger.info("Executing tool: %s with arguments: %s", name, list(arguments.keys()))

        if name not in self.tools:
            # Try to rediscover tools in case of new endpoints
            await self.discover_tools()

            if name not in self.tools:
                logger.error("Tool '%s' not found in registry", name)
                return {
                    "error": "tool_not_found",
                    "message": f"Tool '{name}' is not available",
                    "available_tools": list(self.tools.keys())[:10],  # Show first 10
                }

        # Validate arguments
        validation_result = await tool_executor.validate_tool_arguments(name, arguments)
        if not validation_result["valid"]:
            logger.warning("Invalid arguments for tool %s: %s", name, validation_result["errors"])
            return {
                "error": "invalid_arguments",
                "message": "Tool arguments validation failed",
                "validation_errors": validation_result["errors"],
                "tool_schema": (self.tools[name].inputSchema if name in self.tools else None),
            }

        # Execute the tool
        try:
            # Check if it's a specialized tool
            if name in [tool.name for tool in generator_tools.get_tools()]:
                result = await generator_tools.execute_tool(name, arguments, user_context)
            elif name in [tool.name for tool in orchestrator_tools.get_tools()]:
                result = await orchestrator_tools.execute_tool(name, arguments, user_context)
            else:
                # Use generic executor for endpoint-based tools
                result = await tool_executor.execute_tool(name, arguments, user_context)

            logger.info("Tool %s executed successfully", name)
            return result
        except (ImportError, AttributeError, ValueError, KeyError, TypeError) as e:
            logger.error("Error executing tool %s: %s", name, e)
            return {"error": "execution_failed", "message": str(e), "tool_name": name}

    def get_tool(self: "Self", name: str) -> Optional[Tool]:
        """Get a specific tool by name."""
        return self.tools.get(name)

    def get_tool_count(self: "Self") -> int:
        """Get the number of registered tools."""
        return len(self.tools)

    def clear_tools(self: "Self") -> None:
        """Clear all registered tools."""
        self.tools.clear()

        self.endpoints_discovered = False
        tool_generator.clear_tools()
        logger.info("Cleared all registered tools")


# Create global tool registry
tool_registry = ToolRegistry()

__all__ = ["tool_registry", "ToolRegistry"]
