# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP (Model Context Protocol) client implementation.

MCP (Model Context Protocol) Client for ViolentUTF
Implements SSE client for real-time MCP server communication
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Coroutine, Dict, List, Optional, Self, Union, cast
from urllib.parse import urljoin

import httpx

# Import existing authentication utilities
from .jwt_manager import jwt_manager
from .logging import get_logger

# Set up logger for this module
logger = get_logger(__name__)


# Exception classes
class MCPClientError(Exception):
    """Base exception for MCP client errors."""


class MCPConnectionError(MCPClientError):
    """Connection-related errors."""


class MCPAuthenticationError(MCPClientError):
    """Authentication failures."""


class MCPTimeoutError(MCPClientError):
    """Request timeout errors."""


class MCPMethod(Enum):
    """MCP JSON-RPC methods."""

    INITIALIZE = "initialize"

    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    TOOLS_LIST = "tools/list"
    TOOLS_EXECUTE = "tools/execute"
    COMPLETION = "completion"


@dataclass
class MCPResponse:
    """Structured MCP response."""

    id: int

    result: Optional[Dict[str, object]] = None
    error: Optional[Dict[str, object]] = None

    @property
    def is_error(self: "Self") -> bool:
        """Check if response contains an error."""
        return self.error is not None

    @property
    def error_message(self: "Self") -> str:
        """Get error message from response."""
        if self.error:
            return str(self.error.get("message", "Unknown error"))
        return ""


class MCPClient:
    """MCP Client for Server-Sent Events communication."""

    def __init__(self: "Self", base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        """Initialize MCP Client

        Args:
            base_url: Base URL for MCP server (defaults to APISIX gateway)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")

        self.mcp_endpoint = urljoin(self.base_url or "", "/mcp/sse/")
        self.timeout = timeout
        self._request_id = 0
        self._initialized = False
        self._server_info: Dict[str, object] = {}
        self.logger = logger
        self._test_token: Optional[str] = None  # For testing without streamlit

    def set_test_token(self: "Self", token: str) -> None:
        """Set a test token for non-streamlit environments."""
        self._test_token = token

    def _get_auth_headers(self: "Self") -> Dict[str, str]:
        """Get authentication headers with automatic token refresh."""
        try:

            # Use test token if available (for testing without streamlit)
            if self._test_token:
                token = self._test_token
            else:
                # Use jwt_manager for automatic token refresh
                token = jwt_manager.get_valid_token() or ""

            if not token:
                self.logger.warning("No valid JWT token available")
                return {}

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-API-Gateway": "APISIX",
            }

            # Add APISIX API key if available
            apisix_api_key = (
                os.getenv("VIOLENTUTF_API_KEY") or os.getenv("APISIX_API_KEY") or os.getenv("AI_GATEWAY_API_KEY")
            )
            if apisix_api_key:
                headers["apikey"] = apisix_api_key

            return headers
        except Exception as e:
            self.logger.error("Failed to get auth headers: %s", e)
            return {}

    def _get_next_id(self: "Self") -> int:
        """Get next request ID for JSON-RPC."""
        self._request_id += 1

        return self._request_id

    async def _send_request(self: "Self", method: MCPMethod, params: Optional[Dict[str, object]] = None) -> MCPResponse:
        """Send JSON-RPC request to MCP server

        Args:
            method: MCP method to call
            params: Optional parameters for the method

        Returns:
            MCPResponse object with result or error
        """
        request_id = self._get_next_id()

        request: Dict[str, object] = {
            "jsonrpc": "2.0",
            "method": method.value,
            "id": request_id,
        }

        if params:
            request["params"] = params

        headers = self._get_auth_headers()
        if not headers:
            return MCPResponse(
                id=request_id,
                error={"code": -32000, "message": "Authentication failed"},
            )

        try:
            # Ensure request is JSON serializable
            try:
                json.dumps(request)  # Test serialization
            except (TypeError, ValueError) as e:
                self.logger.error("Request not JSON serializable: %s", e)
                return MCPResponse(
                    id=request_id,
                    error={"code": -32600, "message": f"Invalid request: {e}"},
                )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # For SSE, we need to handle the streaming response
                response = await client.post(self.mcp_endpoint, headers=headers, json=request)

                if response.status_code != 200:
                    return MCPResponse(
                        id=request_id,
                        error={
                            "code": -32603,
                            "message": f"HTTP {response.status_code}: {response.text}",
                        },
                    )

                # Parse response - could be JSON or SSE format
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    # Direct JSON response
                    data = response.json()
                    return MCPResponse(
                        id=cast(Dict[str, Any], data).get("id", request_id),
                        result=cast(Dict[str, Any], data).get("result"),
                        error=cast(Dict[str, Any], data).get("error"),
                    )
                elif "text/event-stream" in content_type:
                    # SSE response - parse the event stream
                    text = response.text
                    for line in text.split("\n"):
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                return MCPResponse(
                                    id=cast(Dict[str, Any], data).get("id", request_id),
                                    result=cast(Dict[str, Any], data).get("result"),
                                    error=cast(Dict[str, Any], data).get("error"),
                                )
                            except json.JSONDecodeError:  # nosec B112 - acceptable exception handling

                                continue
                # Fallback - try to parse as JSON
                try:
                    data = response.json()
                    return MCPResponse(
                        id=cast(Dict[str, Any], data).get("id", request_id),
                        result=cast(Dict[str, Any], data).get("result"),
                        error=cast(Dict[str, Any], data).get("error"),
                    )
                except Exception:
                    return MCPResponse(
                        id=request_id,
                        error={
                            "code": -32700,
                            "message": f"Invalid response format: {response.text[:200]}",
                        },
                    )

        except httpx.TimeoutException:
            return MCPResponse(id=request_id, error={"code": -32001, "message": "Request timeout"})
        except Exception as e:
            self.logger.error("MCP request failed: %s", e)
            return MCPResponse(id=request_id, error={"code": -32603, "message": str(e)})

    async def initialize(self: "Self", capabilities: Optional[Dict[str, object]] = None) -> bool:
        """Initialize connection to MCP server

        Args:
            capabilities: Client capabilities to send to server

        Returns:
            True if initialization successful
        """
        if self._initialized:

            return True

        response = await self._send_request(MCPMethod.INITIALIZE, {"capabilities": capabilities or {}})

        if not response.is_error and response.result:
            self._server_info = response.result
            self._initialized = True
            self.logger.info("MCP server initialized: %s", self._server_info.get("name", "Unknown"))
            return True
        else:
            self.logger.error("MCP initialization failed: %s", response.error_message)
            return False

    async def list_prompts(self: "Self") -> List[Dict[str, object]]:
        """List all available prompts from MCP server

        Returns:
            List of prompt definitions
        """
        if not self._initialized:

            await self.initialize()

        response = await self._send_request(MCPMethod.PROMPTS_LIST)

        if not response.is_error and response.result:
            prompts_data = cast(List[Dict[str, object]], response.result.get("prompts", []))
            return list(prompts_data)
        else:
            self.logger.error("Failed to list prompts: %s", response.error_message)
            return []

    async def get_prompt(self: "Self", name: str, arguments: Optional[Dict[str, object]] = None) -> Optional[str]:
        """Get a specific prompt with arguments

        Args:
            name: Name of the prompt
            arguments: Arguments to pass to the prompt

        Returns:
            Rendered prompt text or None if error
        """
        if not self._initialized:

            await self.initialize()

        params: Dict[str, object] = {"name": name}
        if arguments:
            params["arguments"] = arguments

        response = await self._send_request(MCPMethod.PROMPTS_GET, params)

        if not response.is_error and response.result:
            # Extract the rendered prompt from messages
            messages = response.result.get("messages", [])
            if messages and isinstance(messages, list):
                # Concatenate all message contents
                return "\n".join(msg.get("content", "") for msg in messages)
            return str(response.result.get("prompt", ""))
        else:
            self.logger.error("Failed to get prompt '%s': %s", name, response.error_message)
            return None

    async def list_resources(self: "Self") -> List[Dict[str, object]]:
        """List all available resources from MCP server

        Returns:
            List of resource definitions
        """
        if not self._initialized:

            await self.initialize()

        response = await self._send_request(MCPMethod.RESOURCES_LIST)

        if not response.is_error and response.result:
            resources_data = cast(List[Dict[str, object]], response.result.get("resources", []))
            return list(resources_data)
        else:
            self.logger.error("Failed to list resources: %s", response.error_message)
            return []

    async def read_resource(self: "Self", uri: str) -> Optional[Union[str, Dict[str, object]]]:
        """Read a specific resource by URI

        Args:
            uri: Resource URI to read

        Returns:
            Resource content (string or dict) or None if error
        """
        if not self._initialized:

            await self.initialize()

        response = await self._send_request(MCPMethod.RESOURCES_READ, {"uri": uri})

        if not response.is_error and response.result:
            contents = response.result.get("contents", [])
            if contents and isinstance(contents, list):
                # If single text content, return as string
                if len(contents) == 1 and contents[0].get("mimeType") == "text/plain":
                    return str(contents[0].get("text", ""))
                # Otherwise return the first content as dict if single dict, or first content
                if len(contents) == 1 and isinstance(contents[0], dict):
                    return dict(contents[0])
                else:
                    # Return first content as string if it has text, otherwise None
                    return str(contents[0].get("text", "")) if contents else None
            return response.result
        else:
            self.logger.error("Failed to read resource '%s': %s", uri, response.error_message)
            return None

    async def list_tools(self: "Self") -> List[Dict[str, object]]:
        """List all available tools from MCP server

        Returns:
            List of tool definitions
        """
        if not self._initialized:

            await self.initialize()

        response = await self._send_request(MCPMethod.TOOLS_LIST)

        if not response.is_error and response.result:
            tools = cast(List[Dict[str, object]], response.result.get("tools", []))
            self.logger.debug("Received %s tools from server", len(tools))
            return list(tools)
        else:
            error_msg = response.error_message if response.is_error else "No result returned"
            self.logger.error("Failed to list tools: %s", error_msg)
            if response.error:
                self.logger.error("Error details: %s", response.error)
            return []

    async def execute_tool(self: "Self", name: str, arguments: Optional[Dict[str, object]] = None) -> Optional[object]:
        """Execute a tool with arguments

        Args:
            name: Name of the tool
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result or None if error
        """
        if not self._initialized:

            await self.initialize()

        params: Dict[str, object] = {"name": name}
        if arguments:
            params["arguments"] = arguments

        response = await self._send_request(MCPMethod.TOOLS_EXECUTE, params)

        if not response.is_error and response.result:
            return response.result
        else:
            self.logger.error("Failed to execute tool '%s': %s", name, response.error_message)
            return None

    async def health_check(self: "Self") -> bool:
        """Check if MCP server is healthy and accessible

        Returns:
            True if server is healthy
        """
        try:

            # Try to initialize or re-initialize
            self._initialized = False  # Force re-initialization
            return await self.initialize()
        except Exception as e:
            self.logger.error("Health check failed: %s", e)
            return False

    def close(self: "Self") -> None:
        """Close any open connections."""
        # Currently using httpx with context managers, so no persistent connections

        self._initialized = False
        self._server_info = {}


# Synchronous wrapper for easier use in Streamlit
class MCPClientSync:
    """Synchronous wrapper for MCPClient for use in Streamlit."""

    def __init__(self: MCPClientSync, base_url: Optional[str] = None, timeout: float = 30.0) -> None:
        """Initialize instance."""
        self.client = MCPClient(base_url, timeout)

        self._loop = None

    def set_test_token(self: MCPClientSync, token: str) -> None:
        """Set a test token for non-streamlit environments."""
        self.client.set_test_token(token)

    def _get_loop(self: MCPClientSync) -> asyncio.AbstractEventLoop:
        """Get or create event loop."""
        try:

            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _run_async(self: MCPClientSync, coro: Coroutine[Any, Any, Any]) -> Any:  # noqa: ANN401
        """Run async coroutine in sync context."""
        loop = self._get_loop()

        return loop.run_until_complete(coro)

    def initialize(self: MCPClientSync, capabilities: Optional[Dict[str, object]] = None) -> bool:
        """Initialize connection to MCP server."""
        return bool(self._run_async(self.client.initialize(capabilities)))

    def list_prompts(self: MCPClientSync) -> List[Dict[str, object]]:
        """List all available prompts."""
        result = self._run_async(self.client.list_prompts())
        return cast(List[Dict[str, object]], result)

    def get_prompt(self: MCPClientSync, name: str, arguments: Optional[Dict[str, object]] = None) -> Optional[str]:
        """Get a specific prompt with arguments."""
        result = self._run_async(self.client.get_prompt(name, arguments))

        return str(result) if result is not None else None

    def list_resources(self: MCPClientSync) -> List[Dict[str, object]]:
        """List all available resources."""
        result = self._run_async(self.client.list_resources())
        return cast(List[Dict[str, object]], result)

    def read_resource(self: MCPClientSync, uri: str) -> Optional[Union[str, Dict[str, object]]]:
        """Read a specific resource."""
        result = self._run_async(self.client.read_resource(uri))

        # Cast result to match return type annotation
        if isinstance(result, str):
            return str(result)
        elif isinstance(result, dict):
            return dict(result)
        else:
            return None  # Return None for non-string/dict types as per Optional return type

    def list_tools(self: MCPClientSync) -> List[Dict[str, object]]:
        """List all available tools."""
        result = self._run_async(self.client.list_tools())
        return cast(List[Dict[str, object]], result)

    def execute_tool(self: MCPClientSync, name: str, arguments: Optional[Dict[str, object]] = None) -> Optional[object]:
        """Execute a tool."""
        result = self._run_async(self.client.execute_tool(name, arguments))
        return cast(Optional[object], result)

    def health_check(self: MCPClientSync) -> bool:
        """Check server health."""
        return bool(self._run_async(self.client.health_check()))

    def close(self: MCPClientSync) -> None:
        """Close client."""
        self.client.close()
