# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP Server Configuration"""

from typing import List

from pydantic_settings import BaseSettings


class MCPSettings(BaseSettings):
    """MCP-specific configuration settings"""

    # Server settings
    MCP_SERVER_NAME: str = "ViolentUTF MCP Server"
    MCP_SERVER_VERSION: str = "0.1.0"
    MCP_SERVER_DESCRIPTION: str = "Model Context Protocol server for ViolentUTF AI red-teaming platform"

    # Transport settings
    MCP_TRANSPORT_TYPE: str = "sse"  # sse, stdio, asgi
    MCP_SSE_ENDPOINT: str = "/mcp/sse"

    # Feature flags
    MCP_ENABLE_TOOLS: bool = True
    MCP_ENABLE_RESOURCES: bool = True
    MCP_ENABLE_PROMPTS: bool = True
    MCP_ENABLE_SAMPLING: bool = True

    # Security settings
    MCP_REQUIRE_AUTH: bool = True
    MCP_ALLOWED_ORIGINS: List[str] = ["http://localhost:*", "https://localhost:*"]

    # Tool settings
    MCP_TOOL_TIMEOUT: int = 300  # 5 minutes
    MCP_MAX_TOOL_RESULTS: int = 100

    # Resource settings
    MCP_RESOURCE_CACHE_TTL: int = 3600  # 1 hour
    MCP_MAX_RESOURCE_SIZE: int = 10485760  # 10MB

    # Prompt settings
    MCP_PROMPT_TEMPLATE_DIR: str = "./prompts"

    # Sampling settings
    MCP_SAMPLING_MAX_TOKENS: int = 2000
    MCP_SAMPLING_DEFAULT_TEMPERATURE: float = 0.7

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}  # Ignore extra fields from .env file


# Create global MCP settings instance
mcp_settings = MCPSettings()
