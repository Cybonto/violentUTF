# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""ViolentUTF Model Context Protocol (MCP) Module."""

from app.mcp.config import mcp_settings
from app.mcp.server import mcp_server

__all__ = ["mcp_server", "mcp_settings"]

# Module version
__version__ = "0.1.0"
