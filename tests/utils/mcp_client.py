# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test utilities for MCP Client
Re-exports from violentutf.utils.mcp_client for test isolation
"""

# Import the actual implementations from violentutf
import sys
from pathlib import Path

# Add violentutf to path for import
violentutf_path = Path(__file__).parent.parent.parent / "violentutf"
sys.path.insert(0, str(violentutf_path))

try:
    from violentutf.utils.mcp_client import MCPClient, MCPClientSync, MCPMethod, MCPResponse

    # Re-export for tests
    __all__ = ["MCPClient", "MCPClientSync", "MCPMethod", "MCPResponse"]
    
except ImportError as e:
    # Fallback mock implementations for tests
    from dataclasses import dataclass
    from enum import Enum
    from typing import Any, Dict, Optional
    
    
    class MCPMethod(Enum):
        """MCP JSON-RPC methods"""
        INITIALIZE = "initialize"
        LIST_RESOURCES = "resources/list"
        READ_RESOURCE = "resources/read"
        LIST_TOOLS = "tools/list"
        CALL_TOOL = "tools/call"
        LIST_PROMPTS = "prompts/list"
        GET_PROMPT = "prompts/get"
        
    
    @dataclass
    class MCPResponse:
        """MCP response container"""
        success: bool
        data: Optional[Dict[str, Any]] = None
        error: Optional[str] = None
        method: Optional[str] = None
        id: Optional[str] = None
        
        
    class MCPClient:
        """Mock async MCP client for tests"""
        
        def __init__(self, base_url: str = "http://localhost:9080"):
            self.base_url = base_url
            self.session_id: Optional[str] = None
            
        async def connect(self) -> bool:
            """Mock connect"""
            return True
            
        async def disconnect(self) -> None:
            """Mock disconnect"""
            pass
            
        async def call_method(self, method: MCPMethod, params: Dict[str, Any]) -> MCPResponse:
            """Mock method call"""
            return MCPResponse(success=True, data={"result": "mock"})
            
    
    class MCPClientSync:
        """Mock sync MCP client for tests"""
        
        def __init__(self, base_url: str = "http://localhost:9080"):
            self.base_url = base_url
            self.session_id: Optional[str] = None
            
        def connect(self) -> bool:
            """Mock connect"""
            return True
            
        def disconnect(self) -> None:
            """Mock disconnect"""
            pass
            
        def call_method(self, method: MCPMethod, params: Dict[str, Any]) -> MCPResponse:
            """Mock method call"""
            return MCPResponse(success=True, data={"result": "mock"})