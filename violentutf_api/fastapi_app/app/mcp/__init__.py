# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""ViolentUTF Model Context Protocol (MCP) Module"""

from app.mcp.config import mcp_settings
from app.mcp.server import mcp_server

__all__ = ["mcp_server", "mcp_settings"]

# Module version
__version__ = "0.1.0"
