# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP server base classes and core server functionality.

ViolentUTF MCP Server Base Implementation.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, cast

from app.mcp.auth import MCPAuthHandler
from app.mcp.config import mcp_settings
from fastapi import FastAPI, HTTPException
from mcp.server import Server
from mcp.types import CreateMessageRequest, Prompt, Resource, ServerCapabilities, Tool

# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

logger = logging.getLogger(__name__)


class ViolentUTFMCPServer:
    """MCP Server that integrates with the existing ViolentUTF FastAPI instance."""

    def __init__(self: ViolentUTFMCPServer) -> None:
        """Initialize instance."""
        self.server = Server(mcp_settings.MCP_SERVER_NAME)

        self.auth_handler = MCPAuthHandler()
        self._setup_handlers()
        self._initialized = False

    def _setup_handlers(self: ViolentUTFMCPServer) -> None:
        """Set up MCP server handlers."""
        # Store handler references for dynamic dispatch using Any type to avoid signature conflicts
        self._handlers: Dict[str, Callable[..., Any]] = {}

        # Tool handlers
        if mcp_settings.MCP_ENABLE_TOOLS:
            self._handlers["list_tools"] = self._list_tools
            self._handlers["call_tool"] = self._call_tool

        # Resource handlers
        if mcp_settings.MCP_ENABLE_RESOURCES:
            self._handlers["list_resources"] = self._list_resources
            self._handlers["read_resource"] = self._read_resource

        # Prompt handlers
        if mcp_settings.MCP_ENABLE_PROMPTS:
            self._handlers["list_prompts"] = self._list_prompts
            self._handlers["get_prompt"] = self._get_prompt

        # Sampling handlers
        if mcp_settings.MCP_ENABLE_SAMPLING:
            # Note: create_message handler would be set up here if supported by MCP server
            pass

    async def initialize(self: ViolentUTFMCPServer) -> None:
        """Initialize the MCP server."""
        if self._initialized:

            return

        logger.info(
            "Initializing %s v%s",
            mcp_settings.MCP_SERVER_NAME,
            mcp_settings.MCP_SERVER_VERSION,
        )

        # Import tool and resource modules here to avoid circular imports
        if mcp_settings.MCP_ENABLE_TOOLS:
            # Tool registry import removed - tool discovery done when FastAPI app is provided
            logger.info("Tool registry ready for discovery")

        if mcp_settings.MCP_ENABLE_RESOURCES:
            from app.mcp.resources import resource_registry

            await resource_registry.initialize()

        if mcp_settings.MCP_ENABLE_PROMPTS:
            from app.mcp.prompts import prompts_manager

            await prompts_manager.initialize()
            logger.info("Prompts manager initialized")

        self._initialized = True
        logger.info("MCP server initialized successfully")

    def mount_to_app(self: ViolentUTFMCPServer, app: FastAPI) -> None:
        """Mount MCP server to existing ViolentUTF FastAPI app."""
        logger.info("Mounting MCP server to FastAPI app")

        # Initialize tool discovery with FastAPI app
        if mcp_settings.MCP_ENABLE_TOOLS:
            try:
                from app.mcp.tools.introspection import initialize_introspector

                initialize_introspector(app)
                logger.info("Initialized FastAPI endpoint introspector")
            except Exception as e:
                logger.error("Failed to initialize introspector: %s", e)

        # Mount transport endpoints based on configuration
        if mcp_settings.MCP_TRANSPORT_TYPE == "sse":
            # SSE transport for web clients
            from app.mcp.server.transports import create_sse_transport

            sse_app = create_sse_transport(self.server, self.auth_handler)
            app.mount(mcp_settings.MCP_SSE_ENDPOINT, sse_app)
            logger.info("Mounted SSE transport at %s", mcp_settings.MCP_SSE_ENDPOINT)

        # Mount OAuth proxy
        try:
            from app.mcp.oauth_proxy import mcp_oauth_proxy

            app.include_router(mcp_oauth_proxy.router)
            logger.info("Mounted MCP OAuth proxy")
        except Exception as e:
            logger.error("Failed to mount OAuth proxy: %s", e)

        # Add startup event to initialize server and discover tools
        @app.on_event("startup")
        async def startup_mcp() -> None:
            await self.initialize()

            # Discover tools from FastAPI endpoints
            if mcp_settings.MCP_ENABLE_TOOLS:
                try:
                    from app.mcp.tools import tool_registry

                    await tool_registry.discover_tools(app)
                    logger.info("Discovered %s MCP tools", tool_registry.get_tool_count())
                except Exception as e:
                    logger.error("Failed to discover tools: %s", e)

    def get_capabilities(self: ViolentUTFMCPServer) -> ServerCapabilities:
        """Get server capabilities."""
        from mcp.types import PromptsCapability, ResourcesCapability, ToolsCapability

        # Create ServerCapabilities with proper capability objects
        return ServerCapabilities(
            tools=ToolsCapability() if mcp_settings.MCP_ENABLE_TOOLS else None,
            resources=(ResourcesCapability() if mcp_settings.MCP_ENABLE_RESOURCES else None),
            prompts=PromptsCapability() if mcp_settings.MCP_ENABLE_PROMPTS else None,
            logging=None,  # Default disabled
        )

    # Tool handlers
    async def _list_tools(self: ViolentUTFMCPServer) -> List[Tool]:
        """List available tools."""
        from app.mcp.tools import tool_registry

        return cast(List[Any], await tool_registry.list_tools())

    async def _call_tool(self: ViolentUTFMCPServer, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool."""
        from app.mcp.tools import tool_registry

        return await tool_registry.call_tool(name, arguments)

    # Resource handlers
    async def _list_resources(self: ViolentUTFMCPServer) -> List[Resource]:
        """List available resources."""
        from app.mcp.resources import resource_registry

        return cast(List[Any], await resource_registry.list_resources())

    async def _read_resource(self: ViolentUTFMCPServer, uri: str) -> Optional[Dict[str, Any]]:
        """Read a resource."""
        from app.mcp.resources import resource_registry

        return await resource_registry.read_resource(uri)

    # Prompt handlers
    async def _list_prompts(self: ViolentUTFMCPServer) -> List[Prompt]:
        """List available prompts."""
        try:

            from app.mcp.prompts import prompts_manager

            prompt_definitions = await prompts_manager.list_prompts()

            # Convert to MCP Prompt objects
            prompts = []
            for prompt_def in prompt_definitions:
                prompt = Prompt(
                    name=prompt_def["name"],
                    description=prompt_def["description"],
                    arguments=prompt_def.get("arguments", []),
                )
                prompts.append(prompt)

            logger.debug("Listed %s prompts", len(prompts))
            return prompts

        except Exception as e:
            logger.error("Error listing prompts: %s", e)
            return []

    async def _get_prompt(self: ViolentUTFMCPServer, name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get and render a prompt."""
        try:

            from app.mcp.prompts import prompts_manager

            # Get prompt definition for metadata
            prompt_info = prompts_manager.get_prompt_info(name)
            if "error" in prompt_info:
                raise HTTPException(status_code=404, detail=prompt_info["error"])

            # Render the prompt with provided arguments
            rendered_prompt = await prompts_manager.get_prompt(name, arguments)

            return {
                "messages": [{"role": "user", "content": rendered_prompt}],
                "prompt_info": prompt_info,
                "rendered_at": f"{__import__('datetime').datetime.now().isoformat()}",
                "arguments_used": arguments,
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.error("Error getting prompt %s: %s", name, e)
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") from e

    # Sampling handlers
    async def _create_message(self: ViolentUTFMCPServer, request: CreateMessageRequest) -> Dict[str, Any]:
        """Create a message using sampling."""
        # Implementation will be added in Phase 3

        raise HTTPException(status_code=501, detail="Sampling not yet implemented")


# Create global MCP server instance
mcp_server = ViolentUTFMCPServer()
