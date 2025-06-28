"""MCP Tool Executor - Executes MCP tools by calling FastAPI endpoints"""

import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
import httpx
from urllib.parse import urljoin

from app.core.config import settings
from app.mcp.tools.introspection import get_introspector

logger = logging.getLogger(__name__)


class MCPToolExecutor:
    """Executes MCP tools by making authenticated API calls"""

    def __init__(self):
        self.base_url = settings.VIOLENTUTF_API_URL or "http://localhost:8000"
        # Use internal URL for direct API access from within container
        if "localhost:9080" in self.base_url:
            self.base_url = "http://violentutf-api:8000"

    async def execute_tool(
        self, tool_name: str, arguments: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a tool with given arguments"""
        try:
            # Get endpoint information for the tool
            endpoint_info = await self._get_endpoint_info(tool_name)
            if not endpoint_info:
                return {"error": "tool_not_found", "message": f"Tool '{tool_name}' not found"}

            # Build the API request
            request_info = self._build_api_request(endpoint_info, arguments)

            # Execute the API call
            result = await self._execute_api_call(request_info, user_context)

            return {
                "success": True,
                "tool_name": tool_name,
                "result": result,
                "endpoint": f"{endpoint_info['method']} {endpoint_info['path']}",
            }

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": "execution_failed", "message": str(e), "tool_name": tool_name}

    async def _get_endpoint_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get endpoint information for a tool name"""
        introspector = get_introspector()
        if not introspector:
            logger.error("Endpoint introspector not initialized")
            return None

        # Discover endpoints and find matching tool
        endpoints = introspector.discover_endpoints()

        for endpoint in endpoints:
            if endpoint["name"] == tool_name:
                return endpoint

        logger.warning(f"No endpoint found for tool: {tool_name}")
        return None

    def _build_api_request(self, endpoint_info: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Build API request from endpoint info and arguments"""
        method = endpoint_info["method"]
        path = endpoint_info["path"]

        # Separate different types of parameters
        path_params = {}
        query_params = {}
        request_body = None

        # Extract path parameters
        for param_info in endpoint_info.get("path_parameters", []):
            param_name = param_info["name"]
            if param_name in arguments:
                path_params[param_name] = arguments[param_name]

        # Extract query parameters
        for param_info in endpoint_info.get("query_parameters", []):
            param_name = param_info["name"]
            if param_name in arguments:
                query_params[param_name] = arguments[param_name]

        # Build request body
        if endpoint_info.get("request_body"):
            body_schema = endpoint_info["request_body"]

            if "request_body" in arguments:
                # Direct body parameter
                request_body = arguments["request_body"]
            else:
                # Build body from individual properties
                if body_schema.get("schema", {}).get("properties"):
                    request_body = {}
                    for prop_name in body_schema["schema"]["properties"].keys():
                        if prop_name in arguments:
                            request_body[prop_name] = arguments[prop_name]

                    # Only include body if it has content
                    if not request_body:
                        request_body = None

        # Substitute path parameters in URL
        url_path = path
        for param_name, param_value in path_params.items():
            url_path = url_path.replace(f"{{{param_name}}}", str(param_value))

        return {
            "method": method,
            "url": urljoin(self.base_url, url_path),
            "params": query_params if query_params else None,
            "json": request_body if request_body else None,
        }

    async def _execute_api_call(
        self, request_info: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute the actual API call"""
        headers = {"Content-Type": "application/json", "X-API-Gateway": "MCP"}  # Identify requests from MCP

        # Add authentication if user context provided
        if user_context and "token" in user_context:
            headers["Authorization"] = f"Bearer {user_context['token']}"

        timeout = 30.0  # 30 second timeout for API calls

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=request_info["method"],
                    url=request_info["url"],
                    headers=headers,
                    params=request_info.get("params"),
                    json=request_info.get("json"),
                )

                # Log the request for debugging
                logger.info(f"MCP API call: {request_info['method']} {request_info['url']} -> {response.status_code}")

                # Handle response
                if response.status_code >= 400:
                    error_detail = "Unknown error"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", str(error_data))
                    except Exception:
                        error_detail = response.text

                    return {
                        "error": f"api_error_{response.status_code}",
                        "message": error_detail,
                        "status_code": response.status_code,
                    }

                # Return successful response
                try:
                    return response.json()
                except Exception:
                    return {"message": "Success", "raw_response": response.text}

            except httpx.TimeoutException:
                logger.error(f"Timeout executing API call: {request_info['url']}")
                return {"error": "timeout", "message": "API call timed out after 30 seconds"}
            except httpx.ConnectError:
                logger.error(f"Connection error executing API call: {request_info['url']}")
                return {"error": "connection_error", "message": "Could not connect to ViolentUTF API"}
            except Exception as e:
                logger.error(f"Unexpected error executing API call: {e}")
                return {"error": "unexpected_error", "message": str(e)}

    async def validate_tool_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool arguments against endpoint schema"""
        endpoint_info = await self._get_endpoint_info(tool_name)
        if not endpoint_info:
            return {"valid": False, "errors": [f"Tool '{tool_name}' not found"]}

        errors = []

        # Check required path parameters
        for param_info in endpoint_info.get("path_parameters", []):
            if param_info.get("required", True) and param_info["name"] not in arguments:
                errors.append(f"Missing required path parameter: {param_info['name']}")

        # Check required query parameters
        for param_info in endpoint_info.get("query_parameters", []):
            if param_info.get("required", False) and param_info["name"] not in arguments:
                errors.append(f"Missing required query parameter: {param_info['name']}")

        # Check request body requirements
        request_body = endpoint_info.get("request_body")
        if request_body:
            schema = request_body.get("schema", {})
            required_fields = schema.get("required", [])

            # Check if we have a direct body parameter
            if "request_body" in arguments:
                body = arguments["request_body"]
                if isinstance(body, dict):
                    for field in required_fields:
                        if field not in body:
                            errors.append(f"Missing required body field: {field}")
            else:
                # Check individual properties
                for field in required_fields:
                    if field not in arguments:
                        errors.append(f"Missing required field: {field}")

        return {"valid": len(errors) == 0, "errors": errors}


# Global tool executor instance
tool_executor = MCPToolExecutor()
