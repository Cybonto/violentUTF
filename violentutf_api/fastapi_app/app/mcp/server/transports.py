# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""MCP Transport Implementations."""

import json
import logging
from typing import Any, AsyncIterator, Dict, Optional

from app.core.auth import get_current_user
from app.mcp.auth import MCPAuthHandler
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from sse_starlette.sse import EventSourceResponse
from starlette.types import Receive, Scope, Send

logger = logging.getLogger(__name__)


async def _parse_sse_request(request: Request, current_user) -> Dict[str, Any]:
    """Parse and validate SSE request body."""
    # Read request body
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")

    # Parse JSON-RPC request
    try:
        rpc_request = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Log request for debugging
    logger.debug(f"MCP SSE request from {current_user.username}: {rpc_request.get('method', 'unknown')}")

    return rpc_request


async def _create_sse_event_generator(server: Server, rpc_request: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
    """Generate SSE events from MCP server requests."""
    try:
        # Process JSON-RPC request
        if "method" not in rpc_request:
            response = _create_error_response(-32600, "Invalid request", rpc_request.get("id"))
        else:
            response = await _process_mcp_method(server, rpc_request)

        # Yield the response as SSE event
        yield {"event": "message", "data": json.dumps(response)}
        yield {"event": "done", "data": ""}

    except Exception as e:
        logger.error(f"Error processing MCP request: {e}")
        error_response = _create_error_response(-32603, str(e), rpc_request.get("id"))
        yield {"event": "error", "data": json.dumps(error_response)}


async def _process_mcp_method(server: Server, rpc_request: Dict[str, Any]) -> Dict[str, Any]:
    """Process MCP method request and return JSON-RPC response."""
    method = rpc_request["method"]
    params = rpc_request.get("params", {})
    request_id = rpc_request.get("id")

    # Dispatch to method handlers
    method_handlers = {
        "initialize": _handle_initialize_method,
        "prompts/list": _handle_prompts_list_method,
        "resources/list": _handle_resources_list_method,
        "tools/list": _handle_tools_list_method,
        "tools/execute": _handle_tools_execute_method,
        "resources/read": _handle_resources_read_method,
        "prompts/get": _handle_prompts_get_method,
    }

    handler = method_handlers.get(method)
    if handler:
        return await handler(server, params, request_id)
    else:
        return _create_error_response(-32601, f"Method not found: {method}", request_id)


def _create_error_response(code: int, message: str, request_id: Any) -> Dict[str, Any]:
    """Create standardized JSON-RPC error response."""
    return {
        "jsonrpc": "2.0",
        "error": {"code": code, "message": message},
        "id": request_id,
    }


def _create_success_response(result: Any, request_id: Any) -> Dict[str, Any]:
    """Create standardized JSON-RPC success response."""
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id,
    }


async def _handle_initialize_method(server: Server, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
    """Handle initialize method request."""
    capabilities = {
        "tools": True,
        "resources": True,
        "prompts": True,
        "sampling": False,
        "notifications": False,
        "experimental": {},
    }
    result = {
        "serverInfo": {"name": server.name, "version": "1.0.0"},
        "capabilities": capabilities,
    }
    return _create_success_response(result, request_id)


async def _handle_prompts_list_method(server: Server, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
    """Handle prompts/list method request."""
    prompts = await server.list_prompts()
    prompt_dicts = [
        {
            "name": p.name,
            "description": p.description,
            "arguments": [
                {"name": arg.name, "description": arg.description, "required": arg.required}
                for arg in (p.arguments or [])
            ],
        }
        for p in prompts
    ]
    return _create_success_response({"prompts": prompt_dicts}, request_id)


async def _handle_resources_list_method(server: Server, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
    """Handle resources/list method request."""
    resources = await server.list_resources()
    resource_dicts = [
        {
            "uri": str(r.uri),
            "name": r.name,
            "description": r.description,
            "mimeType": r.mimeType,
        }
        for r in resources
    ]
    return _create_success_response({"resources": resource_dicts}, request_id)


async def _handle_tools_list_method(server: Server, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
    """Handle tools/list method request."""
    try:
        tools = await server.list_tools()
        tool_dicts = []

        for t in tools:
            try:
                tool_dict = {
                    "name": str(t.name) if hasattr(t, "name") else "unknown",
                    "description": str(t.description) if hasattr(t, "description") else "",
                    "inputSchema": (
                        t.inputSchema if hasattr(t, "inputSchema") and isinstance(t.inputSchema, dict) else {}
                    ),
                }
                # Test JSON serialization
                json.dumps(tool_dict)
                tool_dicts.append(tool_dict)
            except Exception as e:
                logger.warning(f"Skipping tool due to serialization error: {e}")
                continue

        return _create_success_response({"tools": tool_dicts}, request_id)
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return _create_error_response(-32603, f"Error listing tools: {str(e)}", request_id)


async def _handle_tools_execute_method(server: Server, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
    """Handle tools/execute method request."""
    tool_name = params.get("name")
    tool_args = params.get("arguments", {})

    if not tool_name:
        return _create_error_response(-32602, "Invalid params: missing tool name", request_id)

    try:
        result = await server.call_tool(tool_name, tool_args)
        return _create_success_response(result, request_id)
    except Exception as e:
        return _create_error_response(-32603, f"Tool execution error: {str(e)}", request_id)


async def _handle_resources_read_method(server: Server, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
    """Handle resources/read method request."""
    resource_uri = params.get("uri")

    if not resource_uri:
        return _create_error_response(-32602, "Invalid params: missing resource URI", request_id)

    try:
        content = await server.read_resource(resource_uri)
        return _create_success_response(content, request_id)
    except Exception as e:
        return _create_error_response(-32603, f"Resource read error: {str(e)}", request_id)


async def _handle_prompts_get_method(server: Server, params: Dict[str, Any], request_id: Any) -> Dict[str, Any]:
    """Handle prompts/get method request."""
    prompt_name = params.get("name")
    prompt_args = params.get("arguments", {})

    if not prompt_name:
        return _create_error_response(-32602, "Invalid params: missing prompt name", request_id)

    try:
        prompt_result = await server.get_prompt(prompt_name, prompt_args)
        return _create_success_response(prompt_result, request_id)
    except Exception as e:
        return _create_error_response(-32603, f"Prompt get error: {str(e)}", request_id)


def create_sse_transport(server: Server, auth_handler: MCPAuthHandler) -> FastAPI:
    """Create SSE transport for MCP server."""
    app = FastAPI()

    @app.post("/")
    async def handle_sse_request(request: Request, current_user=Depends(get_current_user)) -> Any:
        """Handle SSE requests with authentication."""
        try:
            # Parse and validate request
            rpc_request = await _parse_sse_request(request, current_user)

            # Create and return SSE response
            return EventSourceResponse(_create_sse_event_generator(server, rpc_request))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in SSE handler: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/stream")
    async def handle_sse_stream(request: Request, current_user=Depends(get_current_user)) -> Any:
        """Handle SSE streaming connection."""
        logger.info(f"MCP SSE stream connection from {current_user.username}")

        async def event_stream() -> AsyncIterator[Dict[str, Any]]:
            """Generate SSE event stream."""
            try:
                # Send initial connection event
                yield {
                    "event": "connected",
                    "data": json.dumps({"server": server.name, "capabilities": server.get_capabilities()}),
                }

                # Keep connection alive with periodic pings
                import asyncio

                while True:
                    await asyncio.sleep(30)  # Send ping every 30 seconds
                    yield {"event": "ping", "data": ""}

            except asyncio.CancelledError:
                logger.info(f"SSE stream closed for {current_user.username}")
                raise
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                yield {"event": "error", "data": json.dumps({"error": str(e)})}

        return EventSourceResponse(event_stream())

    return app
