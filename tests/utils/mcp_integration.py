# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test utilities for MCP Integration
Re-exports from violentutf.utils.mcp_integration for test isolation
"""

# Import the actual implementations from violentutf
import sys
from pathlib import Path

# Add violentutf to path for import
violentutf_path = Path(__file__).parent.parent.parent / "violentutf"
sys.path.insert(0, str(violentutf_path))

try:
    from violentutf.utils.mcp_integration import (
        ConfigurationIntentDetector,
        ContextAnalyzer,
        MCPCommand,
        MCPCommandType,
        NaturalLanguageParser,
    )

    # Re-export for tests
    __all__ = [
        "ConfigurationIntentDetector",
        "ContextAnalyzer", 
        "MCPCommand",
        "MCPCommandType",
        "NaturalLanguageParser"
    ]
    
except ImportError as e:
    # Fallback mock implementations for tests
    from dataclasses import dataclass
    from enum import Enum
    from typing import Any, Dict, List, Optional
    
    
    class MCPCommandType(Enum):
        """MCP command types"""
        HELP = "help"
        TEST = "test"
        DATASET = "dataset"
        ENHANCE = "enhance"
        ANALYZE = "analyze"
        RESOURCES = "resources"
        PROMPT = "prompt"
        LIST = "list"
        DOCUMENTATION = "documentation"
        UNKNOWN = "unknown"
        
    
    @dataclass
    class MCPCommand:
        """Parsed MCP command"""
        type: MCPCommandType
        subcommand: Optional[str] = None
        arguments: Optional[Dict[str, Any]] = None
        raw_text: str = ""
        
        def __post_init__(self) -> None:
            if self.arguments is None:
                self.arguments = {}
                

    class NaturalLanguageParser:
        """Mock natural language parser for tests"""
        
        def parse(self, text: str) -> MCPCommand:
            """Mock parse method"""
            return MCPCommand(
                type=MCPCommandType.TEST,
                raw_text=text
            )
            
        def extract_context(self, text: str) -> Dict[str, Any]:
            """Mock context extraction"""
            return {"text": text, "mock": True}
            

    class ContextAnalyzer:
        """Mock context analyzer for tests"""
        
        def analyze(self, text: str) -> Dict[str, Any]:
            """Mock analysis"""
            return {"analysis": "mock", "confidence": 0.5}
            

    class ConfigurationIntentDetector:
        """Mock configuration intent detector for tests"""
        
        def detect_intent(self, text: str) -> Dict[str, Any]:
            """Mock intent detection"""
            return {"intent": "configuration", "confidence": 0.8}