# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""MCP Server Configuration."""

from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class MCPSettings(BaseSettings):
    """MCP-specific configuration settings."""

    # Server settings.
    MCP_SERVER_NAME: str = Field(default="ViolentUTF MCP Server", env="MCP_SERVER_NAME")
    MCP_SERVER_VERSION: str = Field(default="0.1.0", env="MCP_SERVER_VERSION")
    MCP_SERVER_DESCRIPTION: str = Field(
        default="Model Context Protocol server for ViolentUTF AI red-teaming platform", env="MCP_SERVER_DESCRIPTION"
    )

    # Transport settings
    MCP_TRANSPORT_TYPE: str = Field(default="sse", env="MCP_TRANSPORT_TYPE")  # sse, stdio, asgi
    MCP_SSE_ENDPOINT: str = Field(default="/mcp/sse", env="MCP_SSE_ENDPOINT")

    # Feature flags
    MCP_ENABLE_TOOLS: bool = Field(default=True, env="MCP_ENABLE_TOOLS")
    MCP_ENABLE_RESOURCES: bool = Field(default=True, env="MCP_ENABLE_RESOURCES")
    MCP_ENABLE_PROMPTS: bool = Field(default=True, env="MCP_ENABLE_PROMPTS")
    MCP_ENABLE_SAMPLING: bool = Field(default=True, env="MCP_ENABLE_SAMPLING")

    # Security settings
    MCP_REQUIRE_AUTH: bool = Field(default=True, env="MCP_REQUIRE_AUTH")
    MCP_ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:*", "https://localhost:*"], env="MCP_ALLOWED_ORIGINS"
    )

    # Tool settings
    MCP_TOOL_TIMEOUT: int = Field(default=300, env="MCP_TOOL_TIMEOUT")  # 5 minutes
    MCP_MAX_TOOL_RESULTS: int = Field(default=100, env="MCP_MAX_TOOL_RESULTS")

    # Resource settings
    MCP_RESOURCE_CACHE_TTL: int = Field(default=3600, env="MCP_RESOURCE_CACHE_TTL")  # 1 hour
    MCP_MAX_RESOURCE_SIZE: int = Field(default=10485760, env="MCP_MAX_RESOURCE_SIZE")  # 10MB

    # Prompt settings
    MCP_PROMPT_TEMPLATE_DIR: str = Field(default="./prompts", env="MCP_PROMPT_TEMPLATE_DIR")

    # Sampling settings
    MCP_SAMPLING_MAX_TOKENS: int = Field(default=2000, env="MCP_SAMPLING_MAX_TOKENS")
    MCP_SAMPLING_DEFAULT_TEMPERATURE: float = Field(default=0.7, env="MCP_SAMPLING_DEFAULT_TEMPERATURE")

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}  # Ignore extra fields from .env file


# Create global MCP settings instance
mcp_settings = MCPSettings()
