"""ViolentUTF Model Context Protocol (MCP) Module"""

from app.mcp.server import mcp_server
from app.mcp.config import mcp_settings

__all__ = ["mcp_server", "mcp_settings"]

# Module version
__version__ = "0.1.0"
