"""MCP Transport Implementations"""

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


def create_sse_transport(server: Server, auth_handler: MCPAuthHandler) -> FastAPI:
    """Create SSE transport for MCP server"""
    app = FastAPI()

    # Note: SSE transport implementation handled by FastAPI endpoints below

    @app.post("/")
    async def handle_sse_request(request: Request, current_user=Depends(get_current_user)):
        """Handle SSE requests with authentication"""
        try:
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

            # Create SSE response generator
            async def event_generator() -> AsyncIterator[Dict[str, Any]]:
                """Generate SSE events from MCP server"""
                try:
                    # Process JSON-RPC request directly through the server
                    if "method" in rpc_request:
                        method = rpc_request["method"]
                        params = rpc_request.get("params", {})
                        request_id = rpc_request.get("id")

                        # Handle different MCP methods
                        if method == "initialize":
                            # Get server capabilities
                            capabilities = {
                                "tools": True,
                                "resources": True,
                                "prompts": True,
                                "sampling": False,
                                "notifications": False,
                                "experimental": {},
                            }
                            response = {
                                "jsonrpc": "2.0",
                                "result": {
                                    "serverInfo": {"name": server.name, "version": "1.0.0"},
                                    "capabilities": capabilities,
                                },
                                "id": request_id,
                            }
                        elif method == "prompts/list":
                            prompts = await server.list_prompts()
                            # Convert Prompt objects to dicts
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
                            response = {"jsonrpc": "2.0", "result": {"prompts": prompt_dicts}, "id": request_id}
                        elif method == "resources/list":
                            resources = await server.list_resources()
                            # Convert Resource objects to dicts
                            resource_dicts = [
                                {
                                    "uri": str(r.uri),  # Convert AnyUrl to string
                                    "name": r.name,
                                    "description": r.description,
                                    "mimeType": r.mimeType,
                                }
                                for r in resources
                            ]
                            response = {"jsonrpc": "2.0", "result": {"resources": resource_dicts}, "id": request_id}
                        elif method == "tools/list":
                            try:
                                tools = await server.list_tools()
                                # Convert Tool objects to dicts, handling potential issues
                                tool_dicts = []
                                for t in tools:
                                    try:
                                        tool_dict = {
                                            "name": str(t.name) if hasattr(t, "name") else "unknown",
                                            "description": str(t.description) if hasattr(t, "description") else "",
                                            "inputSchema": (
                                                t.inputSchema
                                                if hasattr(t, "inputSchema") and isinstance(t.inputSchema, dict)
                                                else {}
                                            ),
                                        }
                                        # Ensure the dict is JSON serializable
                                        json.dumps(tool_dict)  # Test serialization
                                        tool_dicts.append(tool_dict)
                                    except Exception as e:
                                        logger.warning(f"Skipping tool due to serialization error: {e}")
                                        continue

                                response = {"jsonrpc": "2.0", "result": {"tools": tool_dicts}, "id": request_id}
                            except Exception as e:
                                logger.error(f"Error listing tools: {e}")
                                response = {
                                    "jsonrpc": "2.0",
                                    "error": {"code": -32603, "message": f"Error listing tools: {str(e)}"},
                                    "id": request_id,
                                }
                        elif method == "tools/execute":
                            # Execute a tool
                            tool_name = params.get("name")
                            tool_args = params.get("arguments", {})

                            if not tool_name:
                                response = {
                                    "jsonrpc": "2.0",
                                    "error": {"code": -32602, "message": "Invalid params: missing tool name"},
                                    "id": request_id,
                                }
                            else:
                                try:
                                    result = await server.call_tool(tool_name, tool_args)
                                    response = {"jsonrpc": "2.0", "result": result, "id": request_id}
                                except Exception as e:
                                    response = {
                                        "jsonrpc": "2.0",
                                        "error": {"code": -32603, "message": f"Tool execution error: {str(e)}"},
                                        "id": request_id,
                                    }
                        elif method == "resources/read":
                            # Read a resource
                            resource_uri = params.get("uri")

                            if not resource_uri:
                                response = {
                                    "jsonrpc": "2.0",
                                    "error": {"code": -32602, "message": "Invalid params: missing resource URI"},
                                    "id": request_id,
                                }
                            else:
                                try:
                                    # Pass all parameters except uri as params
                                    resource_params = {k: v for k, v in params.items() if k != "uri"}
                                    content = await server.read_resource(resource_uri, resource_params)
                                    response = {"jsonrpc": "2.0", "result": content, "id": request_id}
                                except Exception as e:
                                    response = {
                                        "jsonrpc": "2.0",
                                        "error": {"code": -32603, "message": f"Resource read error: {str(e)}"},
                                        "id": request_id,
                                    }
                        elif method == "prompts/get":
                            # Get a prompt
                            prompt_name = params.get("name")
                            prompt_args = params.get("arguments", {})

                            if not prompt_name:
                                response = {
                                    "jsonrpc": "2.0",
                                    "error": {"code": -32602, "message": "Invalid params: missing prompt name"},
                                    "id": request_id,
                                }
                            else:
                                try:
                                    prompt_result = await server.get_prompt(prompt_name, prompt_args)
                                    response = {"jsonrpc": "2.0", "result": prompt_result, "id": request_id}
                                except Exception as e:
                                    response = {
                                        "jsonrpc": "2.0",
                                        "error": {"code": -32603, "message": f"Prompt get error: {str(e)}"},
                                        "id": request_id,
                                    }
                        else:
                            response = {
                                "jsonrpc": "2.0",
                                "error": {"code": -32601, "message": f"Method not found: {method}"},
                                "id": request_id,
                            }
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "error": {"code": -32600, "message": "Invalid request"},
                            "id": rpc_request.get("id"),
                        }

                    # Yield the response as SSE event
                    yield {"event": "message", "data": json.dumps(response)}

                    # Send completion event
                    yield {"event": "done", "data": ""}

                except Exception as e:
                    logger.error(f"Error processing MCP request: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": str(e)},
                        "id": rpc_request.get("id"),
                    }
                    yield {"event": "error", "data": json.dumps(error_response)}

            # Return SSE response
            return EventSourceResponse(event_generator())

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in SSE handler: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    @app.get("/stream")
    async def handle_sse_stream(request: Request, current_user=Depends(get_current_user)):
        """Handle SSE streaming connection"""
        logger.info(f"MCP SSE stream connection from {current_user.username}")

        async def event_stream() -> AsyncIterator[Dict[str, Any]]:
            """Generate SSE event stream"""
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
