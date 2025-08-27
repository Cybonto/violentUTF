"""
MCP (Model Context Protocol) Client for ViolentUTF
Implements SSE client for real-time MCP server communication
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx
from httpx_sse import ServerSentEvent, connect_sse

# Import existing authentication utilities
from .jwt_manager import jwt_manager
from .logging import get_logger

# Set up logger for this module
logger = get_logger(__name__)


# Exception classes
class MCPClientError(Exception):
    """Base exception for MCP client errors"""

    pass


class MCPConnectionError(MCPClientError):
    """Connection-related errors"""

    pass


class MCPAuthenticationError(MCPClientError):
    """Authentication failures"""

    pass


class MCPTimeoutError(MCPClientError):
    """Request timeout errors"""

    pass


class MCPMethod(Enum):
    """MCP JSON-RPC methods"""

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
    """Structured MCP response"""

    id: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    @property
    def is_error(self) -> bool:
        return self.error is not None

    @property
    def error_message(self) -> str:
        if self.error:
            return self.error.get("message", "Unknown error")  # type: ignore[no-any-return]
        return ""


class MCPClient:
    """MCP Client for Server-Sent Events communication"""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        """
        Initialize MCP Client

        Args:
            base_url: Base URL for MCP server (defaults to APISIX gateway)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
        self.mcp_endpoint = urljoin(self.base_url or "", "/mcp/sse/")
        self.timeout = timeout
        self._request_id = 0
        self._initialized = False
        self._server_info: Dict[str, Any] = {}
        self.logger = logger
        self._test_token: Optional[str] = None  # For testing without streamlit

    def set_test_token(self, token: str) -> None:
        """Set a test token for non-streamlit environments"""
        self._test_token = token

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers with automatic token refresh"""
        try:
            # Use test token if available (for testing without streamlit)
            if self._test_token:
                token = self._test_token
            else:
                # Use jwt_manager for automatic token refresh
                token = jwt_manager.get_valid_token()

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
            self.logger.error(f"Failed to get auth headers: {e}")
            return {}

    def _get_next_id(self) -> int:
        """Get next request ID for JSON-RPC"""
        self._request_id += 1
        return self._request_id

    async def _send_request(self, method: MCPMethod, params: Optional[Dict[str, Any]] = None) -> MCPResponse:
        """
        Send JSON-RPC request to MCP server

        Args:
            method: MCP method to call
            params: Optional parameters for the method

        Returns:
            MCPResponse object with result or error
        """
        request_id = self._get_next_id()
        request = {"jsonrpc": "2.0", "method": method.value, "id": request_id}

        if params:
            request["params"] = params

        headers = self._get_auth_headers()
        if not headers:
            return MCPResponse(id=request_id, error={"code": -32000, "message": "Authentication failed"})

        try:
            # Ensure request is JSON serializable
            try:
                json.dumps(request)  # Test serialization
            except (TypeError, ValueError) as e:
                self.logger.error(f"Request not JSON serializable: {e}")
                return MCPResponse(id=request_id, error={"code": -32600, "message": f"Invalid request: {e}"})

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # For SSE, we need to handle the streaming response
                response = await client.post(self.mcp_endpoint, headers=headers, json=request)

                if response.status_code != 200:
                    return MCPResponse(
                        id=request_id,
                        error={"code": -32603, "message": f"HTTP {response.status_code}: {response.text}"},
                    )

                # Parse response - could be JSON or SSE format
                content_type = response.headers.get("content-type", "")

                if "application/json" in content_type:
                    # Direct JSON response
                    data = response.json()
                    return MCPResponse(
                        id=data.get("id", request_id), result=data.get("result"), error=data.get("error")
                    )
                elif "text/event-stream" in content_type:
                    # SSE response - parse the event stream
                    text = response.text
                    for line in text.split("\n"):
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                return MCPResponse(
                                    id=data.get("id", request_id), result=data.get("result"), error=data.get("error")
                                )
                            except json.JSONDecodeError:
                                continue

                # Fallback - try to parse as JSON
                try:
                    data = response.json()
                    return MCPResponse(
                        id=data.get("id", request_id), result=data.get("result"), error=data.get("error")
                    )
                except Exception:
                    return MCPResponse(
                        id=request_id,
                        error={"code": -32700, "message": f"Invalid response format: {response.text[:200]}"},
                    )

        except httpx.TimeoutException:
            return MCPResponse(id=request_id, error={"code": -32001, "message": "Request timeout"})
        except Exception as e:
            self.logger.error(f"MCP request failed: {e}")
            return MCPResponse(id=request_id, error={"code": -32603, "message": str(e)})

    async def initialize(self, capabilities: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize connection to MCP server

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
            self.logger.info(f"MCP server initialized: {self._server_info.get('name', 'Unknown')}")
            return True
        else:
            self.logger.error(f"MCP initialization failed: {response.error_message}")
            return False

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List all available prompts from MCP server

        Returns:
            List of prompt definitions
        """
        if not self._initialized:
            await self.initialize()

        response = await self._send_request(MCPMethod.PROMPTS_LIST)

        if not response.is_error and response.result:
            return response.result.get("prompts", [])
        else:
            self.logger.error(f"Failed to list prompts: {response.error_message}")
            return []

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get a specific prompt with arguments

        Args:
            name: Name of the prompt
            arguments: Arguments to pass to the prompt

        Returns:
            Rendered prompt text or None if error
        """
        if not self._initialized:
            await self.initialize()

        params = {"name": name}
        if arguments:
            params["arguments"] = arguments

        response = await self._send_request(MCPMethod.PROMPTS_GET, params)

        if not response.is_error and response.result:
            # Extract the rendered prompt from messages
            messages = response.result.get("messages", [])
            if messages and isinstance(messages, list):
                # Concatenate all message contents
                return "\n".join(msg.get("content", "") for msg in messages)
            return response.result.get("prompt", "")
        else:
            self.logger.error(f"Failed to get prompt '{name}': {response.error_message}")
            return None

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        List all available resources from MCP server

        Returns:
            List of resource definitions
        """
        if not self._initialized:
            await self.initialize()

        response = await self._send_request(MCPMethod.RESOURCES_LIST)

        if not response.is_error and response.result:
            return response.result.get("resources", [])
        else:
            self.logger.error(f"Failed to list resources: {response.error_message}")
            return []

    async def read_resource(self, uri: str) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Read a specific resource by URI

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
                    return contents[0].get("text", "")
                # Otherwise return the full contents
                return contents
            return response.result
        else:
            self.logger.error(f"Failed to read resource '{uri}': {response.error_message}")
            return None

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools from MCP server

        Returns:
            List of tool definitions
        """
        if not self._initialized:
            await self.initialize()

        response = await self._send_request(MCPMethod.TOOLS_LIST)

        if not response.is_error and response.result:
            tools = response.result.get("tools", [])
            self.logger.debug(f"Received {len(tools)} tools from server")
            return tools
        else:
            error_msg = response.error_message if response.is_error else "No result returned"
            self.logger.error(f"Failed to list tools: {error_msg}")
            if response.error:
                self.logger.error(f"Error details: {response.error}")
            return []

    async def execute_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Execute a tool with arguments

        Args:
            name: Name of the tool
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result or None if error
        """
        if not self._initialized:
            await self.initialize()

        params = {"name": name}
        if arguments:
            params["arguments"] = arguments

        response = await self._send_request(MCPMethod.TOOLS_EXECUTE, params)

        if not response.is_error and response.result:
            return response.result
        else:
            self.logger.error(f"Failed to execute tool '{name}': {response.error_message}")
            return None

    async def health_check(self) -> bool:
        """
        Check if MCP server is healthy and accessible

        Returns:
            True if server is healthy
        """
        try:
            # Try to initialize or re-initialize
            self._initialized = False  # Force re-initialization
            return await self.initialize()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def close(self) -> None:
        """Close any open connections"""
        # Currently using httpx with context managers, so no persistent connections
        self._initialized = False
        self._server_info = {}


# Synchronous wrapper for easier use in Streamlit
class MCPClientSync:
    """Synchronous wrapper for MCPClient for use in Streamlit"""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        self.client = MCPClient(base_url, timeout)
        self._loop = None

    def set_test_token(self, token: str) -> None:
        """Set a test token for non-streamlit environments"""
        self.client.set_test_token(token)

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _run_async(self, coro) -> Any:
        """Run async coroutine in sync context"""
        loop = self._get_loop()
        return loop.run_until_complete(coro)

    def initialize(self, capabilities: Optional[Dict[str, Any]] = None) -> bool:
        """Initialize connection to MCP server"""
        return self._run_async(self.client.initialize(capabilities))

    def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available prompts"""
        return self._run_async(self.client.list_prompts())

    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get a specific prompt with arguments"""
        return self._run_async(self.client.get_prompt(name, arguments))

    def list_resources(self) -> List[Dict[str, Any]]:
        """List all available resources"""
        return self._run_async(self.client.list_resources())

    def read_resource(self, uri: str) -> Optional[Union[str, Dict[str, Any]]]:
        """Read a specific resource"""
        return self._run_async(self.client.read_resource(uri))

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        return self._run_async(self.client.list_tools())

    def execute_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """Execute a tool"""
        return self._run_async(self.client.execute_tool(name, arguments))

    def health_check(self) -> bool:
        """Check server health"""
        return self._run_async(self.client.health_check())

    def close(self) -> None:
        """Close client"""
        self.client.close()
