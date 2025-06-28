"""ViolentUTF MCP Server Base Implementation"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import ServerCapabilities, Tool, Resource, Prompt, CreateMessageRequest

from app.core.config import settings
from app.mcp.config import mcp_settings
from app.mcp.auth import MCPAuthHandler

logger = logging.getLogger(__name__)


class ViolentUTFMCPServer:
    """MCP Server that integrates with the existing ViolentUTF FastAPI instance"""

    def __init__(self):
        self.server = Server(mcp_settings.MCP_SERVER_NAME)
        self.auth_handler = MCPAuthHandler()
        self._setup_handlers()
        self._initialized = False

    def _setup_handlers(self):
        """Set up MCP server handlers"""
        # Tool handlers
        if mcp_settings.MCP_ENABLE_TOOLS:
            self.server.list_tools = self._list_tools
            self.server.call_tool = self._call_tool

        # Resource handlers
        if mcp_settings.MCP_ENABLE_RESOURCES:
            self.server.list_resources = self._list_resources
            self.server.read_resource = self._read_resource

        # Prompt handlers
        if mcp_settings.MCP_ENABLE_PROMPTS:
            self.server.list_prompts = self._list_prompts
            self.server.get_prompt = self._get_prompt

        # Sampling handlers
        if mcp_settings.MCP_ENABLE_SAMPLING:
            self.server.create_message = self._create_message

    async def initialize(self):
        """Initialize the MCP server"""
        if self._initialized:
            return

        logger.info(f"Initializing {mcp_settings.MCP_SERVER_NAME} v{mcp_settings.MCP_SERVER_VERSION}")

        # Import tool and resource modules here to avoid circular imports
        if mcp_settings.MCP_ENABLE_TOOLS:
            from app.mcp.tools import tool_registry

            # Note: Tool discovery will be done when FastAPI app is provided
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

    def mount_to_app(self, app: FastAPI) -> None:
        """Mount MCP server to existing ViolentUTF FastAPI app"""
        logger.info("Mounting MCP server to FastAPI app")

        # Initialize tool discovery with FastAPI app
        if mcp_settings.MCP_ENABLE_TOOLS:
            try:
                from app.mcp.tools.introspection import initialize_introspector

                initialize_introspector(app)
                logger.info("Initialized FastAPI endpoint introspector")
            except Exception as e:
                logger.error(f"Failed to initialize introspector: {e}")

        # Mount transport endpoints based on configuration
        if mcp_settings.MCP_TRANSPORT_TYPE == "sse":
            # SSE transport for web clients
            from app.mcp.server.transports import create_sse_transport

            sse_app = create_sse_transport(self.server, self.auth_handler)
            app.mount(mcp_settings.MCP_SSE_ENDPOINT, sse_app)
            logger.info(f"Mounted SSE transport at {mcp_settings.MCP_SSE_ENDPOINT}")

        # Mount OAuth proxy
        try:
            from app.mcp.oauth_proxy import mcp_oauth_proxy

            app.include_router(mcp_oauth_proxy.router)
            logger.info("Mounted MCP OAuth proxy")
        except Exception as e:
            logger.error(f"Failed to mount OAuth proxy: {e}")

        # Add startup event to initialize server and discover tools
        @app.on_event("startup")
        async def startup_mcp():
            await self.initialize()

            # Discover tools from FastAPI endpoints
            if mcp_settings.MCP_ENABLE_TOOLS:
                try:
                    from app.mcp.tools import tool_registry

                    await tool_registry.discover_tools(app)
                    logger.info(f"Discovered {tool_registry.get_tool_count()} MCP tools")
                except Exception as e:
                    logger.error(f"Failed to discover tools: {e}")

    def get_capabilities(self) -> ServerCapabilities:
        """Get server capabilities"""
        capabilities = {}

        if mcp_settings.MCP_ENABLE_TOOLS:
            capabilities["tools"] = True

        if mcp_settings.MCP_ENABLE_RESOURCES:
            capabilities["resources"] = True
            capabilities["resource_subscriptions"] = True

        if mcp_settings.MCP_ENABLE_PROMPTS:
            capabilities["prompts"] = True

        if mcp_settings.MCP_ENABLE_SAMPLING:
            capabilities["sampling"] = True

        return ServerCapabilities(**capabilities)

    # Tool handlers
    async def _list_tools(self) -> List[Tool]:
        """List available tools"""
        from app.mcp.tools import tool_registry

        return await tool_registry.list_tools()

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool"""
        from app.mcp.tools import tool_registry

        return await tool_registry.call_tool(name, arguments)

    # Resource handlers
    async def _list_resources(self) -> List[Resource]:
        """List available resources"""
        from app.mcp.resources import resource_registry

        return await resource_registry.list_resources()

    async def _read_resource(self, uri: str) -> Any:
        """Read a resource"""
        from app.mcp.resources import resource_registry

        return await resource_registry.read_resource(uri)

    # Prompt handlers
    async def _list_prompts(self) -> List[Prompt]:
        """List available prompts"""
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

            logger.debug(f"Listed {len(prompts)} prompts")
            return prompts

        except Exception as e:
            logger.error(f"Error listing prompts: {e}")
            return []

    async def _get_prompt(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Get and render a prompt"""
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
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting prompt {name}: {e}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

    # Sampling handlers
    async def _create_message(self, request: CreateMessageRequest) -> Any:
        """Create a message using sampling"""
        # Implementation will be added in Phase 3
        raise HTTPException(status_code=501, detail="Sampling not yet implemented")


# Create global MCP server instance
mcp_server = ViolentUTFMCPServer()
