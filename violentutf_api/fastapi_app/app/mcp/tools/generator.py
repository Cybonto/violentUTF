# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""MCP Tool Generator - Converts FastAPI endpoints to MCP tools"""

import logging
from typing import Any, Dict, List, Optional

from mcp.types import Tool

logger = logging.getLogger(__name__)


class MCPToolGenerator:
    """Generates MCP tools from FastAPI endpoint information"""

    def __init__(self):
        self.generated_tools: Dict[str, Tool] = {}

    def generate_tools_from_endpoints(self, endpoints: List[Dict[str, Any]]) -> List[Tool]:
        """Generate MCP tools from discovered endpoints"""
        tools = []

        for endpoint_info in endpoints:
            try:
                tool = self._create_tool_from_endpoint(endpoint_info)
                if tool:
                    tools.append(tool)
                    self.generated_tools[tool.name] = tool
            except Exception as e:
                logger.error(f"Error generating tool for {endpoint_info.get('name', 'unknown')}: {e}")

        logger.info(f"Generated {len(tools)} MCP tools from endpoints")
        return tools

    def _create_tool_from_endpoint(self, endpoint_info: Dict[str, Any]) -> Optional[Tool]:
        """Create a single MCP tool from endpoint information"""
        try:
            # Build tool description
            description = self._build_tool_description(endpoint_info)

            # Build input schema
            input_schema = self._build_input_schema(endpoint_info)

            # Create MCP Tool
            tool = Tool(name=endpoint_info["name"], description=description, inputSchema=input_schema)

            return tool

        except Exception as e:
            logger.error(f"Error creating tool from endpoint {endpoint_info.get('name')}: {e}")
            return None

    def _build_tool_description(self, endpoint_info: Dict[str, Any]) -> str:
        """Build comprehensive tool description"""
        parts = []

        # Add primary description
        if endpoint_info.get("description"):
            parts.append(endpoint_info["description"].strip())
        elif endpoint_info.get("summary"):
            parts.append(endpoint_info["summary"].strip())
        else:
            parts.append(f"Execute {endpoint_info['method']} request to {endpoint_info['path']}")

        # Add method and path info
        parts.append(f"Method: {endpoint_info['method']} {endpoint_info['path']}")

        # Add parameter info
        if endpoint_info.get("path_parameters"):
            param_names = [p["name"] for p in endpoint_info["path_parameters"]]
            parts.append(f"Path parameters: {', '.join(param_names)}")

        if endpoint_info.get("query_parameters"):
            param_names = [p["name"] for p in endpoint_info["query_parameters"]]
            parts.append(f"Query parameters: {', '.join(param_names)}")

        if endpoint_info.get("request_body"):
            parts.append(f"Request body: {endpoint_info['request_body'].get('model_name', 'JSON object')}")

        # Add tags if available
        if endpoint_info.get("tags"):
            parts.append(f"Tags: {', '.join(endpoint_info['tags'])}")

        return " | ".join(parts)

    def _build_input_schema(self, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build JSON schema for tool input parameters"""
        schema = {"type": "object", "properties": {}, "required": []}

        # Add path parameters
        path_params = endpoint_info.get("path_parameters", [])
        for param in path_params:
            schema["properties"][param["name"]] = {"type": param["type"], "description": param["description"]}
            if param.get("required", True):
                schema["required"].append(param["name"])

        # Add query parameters
        query_params = endpoint_info.get("query_parameters", [])
        for param in query_params:
            schema["properties"][param["name"]] = {"type": param["type"], "description": param["description"]}
            if param.get("default") is not None:
                schema["properties"][param["name"]]["default"] = param["default"]
            if param.get("required", False):
                schema["required"].append(param["name"])

        # Add request body as a single property
        request_body = endpoint_info.get("request_body")
        if request_body:
            if request_body.get("schema"):
                # Use the Pydantic model schema
                body_schema = request_body["schema"]

                # If the schema has properties, add them directly
                if "properties" in body_schema:
                    for prop_name, prop_schema in body_schema["properties"].items():
                        schema["properties"][prop_name] = prop_schema

                    # Add required fields from the model
                    if "required" in body_schema:
                        schema["required"].extend(body_schema["required"])
                else:
                    # Add as a single body parameter
                    schema["properties"]["request_body"] = {
                        "type": "object",
                        "description": f"Request body ({request_body.get('model_name', 'JSON')})",
                        "properties": body_schema.get("properties", {}),
                        "required": body_schema.get("required", []),
                    }
                    schema["required"].append("request_body")
            else:
                # Generic JSON body
                schema["properties"]["request_body"] = {"type": "object", "description": "Request body (JSON object)"}

        # Remove duplicates from required list
        schema["required"] = list(set(schema["required"]))

        return schema

    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Get a generated tool by name"""
        return self.generated_tools.get(name)

    def list_all_tools(self) -> List[Tool]:
        """List all generated tools"""
        return list(self.generated_tools.values())

    def clear_tools(self):
        """Clear all generated tools"""
        self.generated_tools.clear()
        logger.info("Cleared all generated MCP tools")


# Global tool generator instance
tool_generator = MCPToolGenerator()
