# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""FastAPI Endpoint Introspection for MCP Tool Discovery."""
import inspect
import logging
import re
from typing import Any, Dict, List, Optional, Self, Type, Union

from fastapi import FastAPI
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


class ViolentUTFToolFilter:
    """Customize tool filter for ViolentUTF API endpoints."""

    # Endpoints to include in MCP exposure

    INCLUDE_PATTERNS = [
        r"^/api/v1/orchestrators",
        r"^/api/v1/generators",
        r"^/api/v1/datasets",
        r"^/api/v1/converters",
        r"^/api/v1/scorers",
        r"^/api/v1/redteam",
        r"^/api/v1/config",
        r"^/api/v1/sessions",
        r"^/api/v1/files",
        r"^/api/v1/database",
    ]

    # Endpoints to exclude from MCP exposure
    EXCLUDE_PATTERNS = [
        r"/admin",
        r"/debug",
        r"/internal",
        r"/health",
        r"/docs",
        r"/openapi",
        r"/auth/token",  # Exclude sensitive auth endpoints
        r"/keys/generate",  # Exclude key generation
    ]

    # HTTP methods to include
    INCLUDE_METHODS = ["GET", "POST", "PUT", "DELETE"]

    @classmethod
    def should_include_endpoint(cls: Type["ViolentUTFToolFilter"], path: str, method: str) -> bool:
        """Check if endpoint should be included in MCP tools."""
        # Check method inclusion
        if method.upper() not in cls.INCLUDE_METHODS:
            return False

        # Check exclusion patterns first
        for pattern in cls.EXCLUDE_PATTERNS:
            if re.search(pattern, path):
                return False

        # Check inclusion patterns
        for pattern in cls.INCLUDE_PATTERNS:
            if re.search(pattern, path):
                return True

        return False


class EndpointIntrospector:
    """Introspects FastAPI application for available endpoints."""

    def __init__(self: "Self", app: FastAPI) -> None:
        """Initialize instance."""
        self.app = app

        self.tool_filter = ViolentUTFToolFilter()

    def discover_endpoints(self: "Self") -> List[Dict[str, Any]]:
        """Discover all available endpoints from FastAPI app."""
        endpoints = []

        for route in self.app.routes:
            if isinstance(route, APIRoute):
                for method in route.methods:
                    # Skip OPTIONS method
                    if method == "OPTIONS":
                        continue

                    path = route.path

                    # Check if endpoint should be included
                    if not self.tool_filter.should_include_endpoint(path, method):
                        continue

                    endpoint_info = self._extract_endpoint_info(route, method)
                    if endpoint_info:
                        endpoints.append(endpoint_info)

        logger.info("Discovered %s MCP-compatible endpoints", len(endpoints))
        return endpoints

    def _extract_endpoint_info(self: "Self", route: APIRoute, method: str) -> Optional[Dict[str, Any]]:
        """Extract detailed information about an endpoint."""
        try:

            endpoint_func = route.endpoint

            # Get function signature and documentation
            signature = inspect.signature(endpoint_func)
            doc = inspect.getdoc(endpoint_func) or "No description available"

            # Extract path parameters
            path_params = self._extract_path_parameters(route.path, signature)

            # Extract query parameters
            query_params = self._extract_query_parameters(signature)

            # Extract request body schema
            request_body = self._extract_request_body_schema(signature)

            # Generate tool name
            tool_name = self._generate_tool_name(route.path, method)

            return {
                "name": tool_name,
                "method": method,
                "path": route.path,
                "description": doc,
                "path_parameters": path_params,
                "query_parameters": query_params,
                "request_body": request_body,
                "tags": getattr(route, "tags", []),
                "summary": getattr(route, "summary", ""),
                "operation_id": getattr(route, "operation_id", ""),
                "response_model": self._extract_response_model(route),
            }

        except (AttributeError, ValueError, TypeError, KeyError) as e:
            logger.error("Error extracting endpoint info for %s %s: %s", route.path, method, e)
            return None

    def _generate_tool_name(self: "Self", path: str, method: str) -> str:
        """Generate a descriptive tool name from path and method."""
        # Convert path to tool name

        # /api/v1/orchestrators/{id} -> orchestrator_by_id
        # /api/v1/generators -> generators

        # Remove /api/v1 prefix
        clean_path = path.replace("/api/v1/", "")

        # Split path into segments
        segments = [seg for seg in clean_path.split("/") if seg and not seg.startswith("{")]

        # Handle path parameters
        if "{" in path:
            if method.upper() == "GET":
                segments.append("by_id")
            elif method.upper() in ["PUT", "DELETE"]:
                segments.append("by_id")

        # Add method prefix for non-GET methods
        method_prefixes = {
            "POST": "create",
            "PUT": "update",
            "DELETE": "delete",
            "GET": "get",
        }

        tool_name = "_".join(segments)

        # Add method prefix if not GET or if it's a collection endpoint
        if method.upper() != "GET" or not tool_name.endswith("by_id"):
            prefix = method_prefixes.get(method.upper(), method.lower())
            if not tool_name.startswith(prefix):
                tool_name = f"{prefix}_{tool_name}"

        return tool_name

    def _extract_path_parameters(self: "Self", path: str, signature: inspect.Signature) -> List[Dict[str, Any]]:
        """Extract path parameters from route path and function signature."""
        path_params = []

        # Find path parameters like {id}, {orchestrator_id}
        param_matches = re.findall(r"{([^}]+)}", path)

        for param_name in param_matches:
            param_info = {
                "name": param_name,
                "type": "string",  # Default type
                "required": True,
                "description": f"Path parameter: {param_name}",
            }

            # Try to get type from function signature
            if param_name in signature.parameters:
                param = signature.parameters[param_name]
                if param.annotation != inspect.Parameter.empty:
                    param_info["type"] = self._python_type_to_json_type(param.annotation)

            path_params.append(param_info)

        return path_params

    def _extract_query_parameters(self: "Self", signature: inspect.Signature) -> List[Dict[str, Any]]:
        """Extract query parameters from function signature."""
        query_params = []

        for param_name, param in signature.parameters.items():
            # Skip common FastAPI dependencies
            if param_name in ["current_user", "db", "request", "response"]:
                continue

            # Check if it's a Query parameter
            if hasattr(param.default, "__class__") and "Query" in str(param.default.__class__):
                param_info = {
                    "name": param_name,
                    "type": self._python_type_to_json_type(param.annotation),
                    "required": param.default is inspect.Parameter.empty,
                    "description": getattr(param.default, "description", f"Query parameter: {param_name}"),
                }

                # Add default value if available
                if hasattr(param.default, "default") and param.default.default is not None:
                    param_info["default"] = param.default.default

                query_params.append(param_info)

        return query_params

    def _extract_request_body_schema(self: "Self", signature: inspect.Signature) -> Optional[Dict[str, Any]]:
        """Extract request body schema from Pydantic models."""
        for _, param in signature.parameters.items():

            if param.annotation != inspect.Parameter.empty:
                # Check if it's a Pydantic model
                if hasattr(param.annotation, "__bases__") and any(
                    "BaseModel" in str(base) for base in param.annotation.__bases__
                ):
                    try:
                        # Get Pydantic model schema
                        schema = param.annotation.model_json_schema()
                        return {
                            "type": "object",
                            "schema": schema,
                            "model_name": param.annotation.__name__,
                        }
                    except (AttributeError, ValueError, TypeError) as e:
                        logger.warning("Could not extract schema for %s: %s", param.annotation, e)

        return None

    def _extract_response_model(self: "Self", route: APIRoute) -> Optional[str]:
        """Extract response model information."""
        if hasattr(route, "response_model") and route.response_model:

            return str(route.response_model.__name__)
        return None

    def _python_type_to_json_type(self: "Self", python_type: type) -> str:
        """Convert Python type annotation to JSON schema type."""
        type_mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        # Handle Optional types
        if hasattr(python_type, "__origin__"):
            if python_type.__origin__ is Union:
                # Handle Optional[Type] which is Union[Type, NoneType]
                args = getattr(python_type, "__args__", ())
                if len(args) == 2 and type(None) in args:
                    non_none_type = next(arg for arg in args if arg is not type(None))
                    return self._python_type_to_json_type(non_none_type)
            elif python_type.__origin__ in (list, List):
                return "array"
            elif python_type.__origin__ in (dict, Dict):
                return "object"

        return type_mapping.get(python_type, "string")


# Global introspector instance
endpoint_introspector: Optional[EndpointIntrospector] = None


def initialize_introspector(app: FastAPI) -> EndpointIntrospector:
    """Initialize the endpoint introspector with FastAPI app."""
    global endpoint_introspector  # pylint: disable=global-statement

    endpoint_introspector = EndpointIntrospector(app)
    logger.info("FastAPI endpoint introspector initialized")
    return endpoint_introspector


def get_introspector() -> Optional[EndpointIntrospector]:
    """Get the global endpoint introspector instance."""
    return endpoint_introspector
