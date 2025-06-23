# ViolentUTF MCP Development Guide

## Overview

This guide covers extending and customizing the ViolentUTF Model Context Protocol (MCP) server, including adding new tools, resources, and transport mechanisms.

## Development Environment Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Git
- Virtual environment management tool (venv, conda, etc.)

### Environment Setup

1. **Clone and Setup Repository:**
   ```bash
   git clone https://github.com/your-org/ViolentUTF_nightly.git
   cd ViolentUTF_nightly
   
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r violentutf_api/fastapi_app/requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Development Configuration:**
   ```bash
   # Copy environment template
   cp violentutf/.env.sample violentutf/.env
   
   # Set development-specific variables
   export MCP_DEVELOPMENT_MODE=true
   export MCP_DEBUG_MODE=true
   export MCP_LOG_LEVEL=DEBUG
   export MCP_REQUIRE_AUTH=false  # For local development
   ```

3. **Start Development Services:**
   ```bash
   # Start core services
   docker-compose up -d keycloak apisix-apisix-1
   
   # Run FastAPI with hot reload
   cd violentutf_api/fastapi_app
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### IDE Configuration

**VS Code Settings (`.vscode/settings.json`):**
```json
{
  "python.defaultInterpreterPath": "./.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"],
  "editor.formatOnSave": true,
  "files.associations": {
    "*.py": "python"
  }
}
```

**PyCharm Configuration:**
- Set Python interpreter to `.venv/bin/python`
- Enable Black formatting
- Configure pytest as test runner
- Set up Docker integration

## Architecture Overview

### MCP Server Structure

```
app/mcp/
├── __init__.py              # Main exports
├── config.py                # Configuration management
├── auth.py                  # Authentication bridge
├── oauth_proxy.py           # OAuth 2.0 proxy
├── server/
│   ├── base.py             # Core MCP server
│   └── transports.py       # Transport implementations
├── tools/
│   ├── __init__.py         # Tool registry
│   ├── introspection.py    # Endpoint discovery
│   ├── generator.py        # Tool generation
│   ├── executor.py         # Tool execution
│   ├── generators.py       # Generator management tools
│   └── orchestrators.py    # Orchestrator management tools
├── resources/
│   ├── __init__.py         # Resource registry
│   └── manager.py          # Resource management
└── tests/
    ├── conftest.py         # Test configuration
    ├── test_phase1.py      # Phase 1 tests
    └── test_phase2.py      # Phase 2 tests
```

### Key Components

1. **Tool System**: Manages MCP tool discovery, registration, and execution
2. **Resource System**: Provides structured access to ViolentUTF data
3. **Authentication Bridge**: Integrates with Keycloak and JWT systems
4. **Transport Layer**: Handles client communication (SSE, WebSocket)
5. **Configuration Management**: Environment-based configuration system

## Adding New Tools

### Creating Specialized Tools

Create a new tool module in `app/mcp/tools/`:

```python
# app/mcp/tools/datasets.py
"""MCP Dataset Management Tools"""

import logging
from typing import Dict, List, Any, Optional
from mcp.types import Tool
import httpx
from urllib.parse import urljoin

from app.core.config import settings
from app.mcp.auth import MCPAuthHandler

logger = logging.getLogger(__name__)

class DatasetManagementTools:
    """MCP tools for dataset management"""
    
    def __init__(self):
        self.base_url = settings.VIOLENTUTF_API_URL or "http://localhost:8000"
        # Use internal URL for container-to-container communication
        if "localhost:9080" in self.base_url:
            self.base_url = "http://violentutf-api:8000"
        
        self.auth_handler = MCPAuthHandler()
    
    def get_tools(self) -> List[Tool]:
        """Get all dataset management tools"""
        return [
            self._create_list_datasets_tool(),
            self._create_get_dataset_tool(),
            self._create_upload_dataset_tool(),
            self._create_delete_dataset_tool(),
            self._create_validate_dataset_tool()
        ]
    
    def _create_list_datasets_tool(self) -> Tool:
        """Create tool for listing datasets"""
        return Tool(
            name="list_datasets",
            description="List all available datasets with filtering options",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by dataset category",
                        "enum": ["harmful_behaviors", "bias_detection", "privacy", "custom"]
                    },
                    "format": {
                        "type": "string", 
                        "description": "Filter by dataset format",
                        "enum": ["json", "csv", "parquet"]
                    },
                    "min_size": {
                        "type": "integer",
                        "description": "Minimum number of entries",
                        "minimum": 1
                    },
                    "include_samples": {
                        "type": "boolean",
                        "description": "Include sample entries",
                        "default": false
                    }
                },
                "required": []
            }
        )
    
    def _create_get_dataset_tool(self) -> Tool:
        """Create tool for getting dataset details"""
        return Tool(
            name="get_dataset",
            description="Get detailed information about a specific dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_name": {
                        "type": "string",
                        "description": "Name of the dataset to retrieve"
                    },
                    "include_schema": {
                        "type": "boolean",
                        "description": "Include dataset schema information",
                        "default": true
                    },
                    "include_statistics": {
                        "type": "boolean",
                        "description": "Include dataset statistics",
                        "default": true
                    },
                    "sample_size": {
                        "type": "integer",
                        "description": "Number of sample entries to include",
                        "default": 5,
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["dataset_name"]
            }
        )
    
    def _create_upload_dataset_tool(self) -> Tool:
        """Create tool for uploading new datasets"""
        return Tool(
            name="upload_dataset",
            description="Upload a new dataset to the system",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name for the new dataset"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the dataset"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["harmful_behaviors", "bias_detection", "privacy", "custom"],
                        "description": "Dataset category"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "csv", "parquet"],
                        "description": "Dataset format"
                    },
                    "file_content": {
                        "type": "string",
                        "description": "Base64 encoded file content or file path"
                    },
                    "validate_schema": {
                        "type": "boolean",
                        "description": "Validate dataset schema before upload",
                        "default": true
                    }
                },
                "required": ["name", "category", "format", "file_content"]
            }
        )
    
    def _create_delete_dataset_tool(self) -> Tool:
        """Create tool for deleting datasets"""
        return Tool(
            name="delete_dataset",
            description="Delete a dataset from the system",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_name": {
                        "type": "string",
                        "description": "Name of the dataset to delete"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force deletion even if dataset is in use",
                        "default": false
                    },
                    "create_backup": {
                        "type": "boolean",
                        "description": "Create backup before deletion",
                        "default": true
                    }
                },
                "required": ["dataset_name"]
            }
        )
    
    def _create_validate_dataset_tool(self) -> Tool:
        """Create tool for validating dataset format and content"""
        return Tool(
            name="validate_dataset",
            description="Validate dataset format, schema, and content quality",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_name": {
                        "type": "string",
                        "description": "Name of dataset to validate"
                    },
                    "validation_rules": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific validation rules to apply",
                        "default": ["schema", "content", "duplicates", "quality"]
                    },
                    "sample_percentage": {
                        "type": "number",
                        "description": "Percentage of dataset to validate (0.1-1.0)",
                        "minimum": 0.1,
                        "maximum": 1.0,
                        "default": 1.0
                    }
                },
                "required": ["dataset_name"]
            }
        )
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a dataset management tool"""
        logger.info(f"Executing dataset tool: {tool_name}")
        
        try:
            if tool_name == "list_datasets":
                return await self._execute_list_datasets(arguments)
            elif tool_name == "get_dataset":
                return await self._execute_get_dataset(arguments)
            elif tool_name == "upload_dataset":
                return await self._execute_upload_dataset(arguments)
            elif tool_name == "delete_dataset":
                return await self._execute_delete_dataset(arguments)
            elif tool_name == "validate_dataset":
                return await self._execute_validate_dataset(arguments)
            else:
                return {
                    "error": "unknown_tool",
                    "message": f"Unknown dataset tool: {tool_name}"
                }
                
        except Exception as e:
            logger.error(f"Error executing dataset tool {tool_name}: {e}")
            return {
                "error": "execution_failed",
                "message": str(e),
                "tool_name": tool_name
            }
    
    async def _execute_list_datasets(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute list datasets tool"""
        return await self._api_request("GET", "/api/v1/datasets", params=args)
    
    async def _execute_get_dataset(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute get dataset tool"""
        dataset_name = args.pop("dataset_name")
        return await self._api_request("GET", f"/api/v1/datasets/{dataset_name}", params=args)
    
    async def _execute_upload_dataset(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute upload dataset tool"""
        return await self._api_request("POST", "/api/v1/datasets", json=args)
    
    async def _execute_delete_dataset(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute delete dataset tool"""
        dataset_name = args.pop("dataset_name")
        return await self._api_request("DELETE", f"/api/v1/datasets/{dataset_name}", params=args)
    
    async def _execute_validate_dataset(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validate dataset tool"""
        dataset_name = args.pop("dataset_name")
        return await self._api_request("POST", f"/api/v1/datasets/{dataset_name}/validate", json=args)
    
    async def _api_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request"""
        headers = {
            "Content-Type": "application/json",
            "X-API-Gateway": "MCP-Dataset"
        }
        
        # Add authentication headers
        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)
        
        url = urljoin(self.base_url, path)
        timeout = 60.0
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                
                logger.debug(f"Dataset API call: {method} {url} -> {response.status_code}")
                
                if response.status_code >= 400:
                    error_detail = "Unknown error"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", str(error_data))
                    except:
                        error_detail = response.text
                    
                    return {
                        "error": f"api_error_{response.status_code}",
                        "message": error_detail,
                        "status_code": response.status_code
                    }
                
                return response.json()
                
            except httpx.TimeoutException:
                logger.error(f"Timeout on dataset API call: {url}")
                return {
                    "error": "timeout",
                    "message": "Dataset API call timed out"
                }
            except httpx.ConnectError:
                logger.error(f"Connection error on dataset API call: {url}")
                return {
                    "error": "connection_error",
                    "message": "Could not connect to ViolentUTF API"
                }
            except Exception as e:
                logger.error(f"Unexpected error on dataset API call {url}: {e}")
                return {
                    "error": "unexpected_error",
                    "message": str(e)
                }

# Global dataset tools instance
dataset_tools = DatasetManagementTools()
```

### Integrating New Tools

Update the tool registry to include your new tools:

```python
# app/mcp/tools/__init__.py

from app.mcp.tools.datasets import dataset_tools

class ToolRegistry:
    async def discover_tools(self, app=None):
        """Discover and register tools from multiple sources"""
        # ... existing code ...
        
        # Add dataset tools
        dataset_tools_list = dataset_tools.get_tools()
        for tool in dataset_tools_list:
            self.tools[tool.name] = tool
        logger.info(f"Registered {len(dataset_tools_list)} dataset tools")
        
        # ... rest of discovery code ...
    
    async def call_tool(self, name: str, arguments: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None):
        """Execute tools with intelligent routing"""
        # ... existing routing ...
        
        # Add dataset tool routing
        elif name in [tool.name for tool in dataset_tools.get_tools()]:
            result = await dataset_tools.execute_tool(name, arguments, user_context)
        
        # ... rest of execution code ...
```

## Adding New Resources

### Creating Resource Providers

Create a new resource provider in `app/mcp/resources/`:

```python
# app/mcp/resources/analysis.py
"""MCP Analysis Resource Provider"""

import logging
from typing import Dict, List, Any, Optional
from mcp.types import Resource
import httpx
from urllib.parse import urljoin

from app.core.config import settings
from app.mcp.auth import MCPAuthHandler

logger = logging.getLogger(__name__)

class AnalysisResourceProvider:
    """Provides analysis and reporting resources"""
    
    def __init__(self):
        self.base_url = settings.VIOLENTUTF_API_URL or "http://localhost:8000"
        if "localhost:9080" in self.base_url:
            self.base_url = "http://violentutf-api:8000"
        
        self.auth_handler = MCPAuthHandler()
    
    async def list_resources(self) -> List[Resource]:
        """List all analysis resources"""
        resources = []
        
        try:
            # Get analysis reports
            reports = await self._get_analysis_reports()
            if reports:
                for report in reports:
                    resource = Resource(
                        uri=f"violentutf://analysis/{report['id']}",
                        name=f"Analysis: {report['name']}",
                        description=f"Analysis report - {report['type']} - Created: {report.get('created_at', 'unknown')}",
                        mimeType="application/json"
                    )
                    resources.append(resource)
            
            # Get performance metrics
            metrics = await self._get_performance_metrics()
            if metrics:
                resource = Resource(
                    uri="violentutf://analysis/performance",
                    name="Performance Metrics",
                    description="System performance metrics and statistics",
                    mimeType="application/json"
                )
                resources.append(resource)
            
            # Get security insights
            insights = await self._get_security_insights()
            if insights:
                resource = Resource(
                    uri="violentutf://analysis/security",
                    name="Security Insights",
                    description="Security analysis and vulnerability insights",
                    mimeType="application/json"
                )
                resources.append(resource)
            
            return resources
            
        except Exception as e:
            logger.error(f"Error listing analysis resources: {e}")
            return []
    
    async def read_resource(self, resource_id: str) -> Dict[str, Any]:
        """Read specific analysis resource"""
        try:
            if resource_id == "performance":
                return await self._get_performance_metrics()
            elif resource_id == "security":
                return await self._get_security_insights()
            else:
                # Assume it's an analysis report ID
                return await self._get_analysis_report(resource_id)
            
        except Exception as e:
            logger.error(f"Error reading analysis resource {resource_id}: {e}")
            return {
                "error": "resource_read_failed",
                "message": str(e),
                "resource_id": resource_id
            }
    
    async def _get_analysis_reports(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of analysis reports"""
        response = await self._api_request("GET", "/api/v1/analysis/reports")
        return response.get("reports") if response else None
    
    async def _get_analysis_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get specific analysis report"""
        return await self._api_request("GET", f"/api/v1/analysis/reports/{report_id}")
    
    async def _get_performance_metrics(self) -> Optional[Dict[str, Any]]:
        """Get system performance metrics"""
        return await self._api_request("GET", "/api/v1/analysis/performance")
    
    async def _get_security_insights(self) -> Optional[Dict[str, Any]]:
        """Get security analysis insights"""
        return await self._api_request("GET", "/api/v1/analysis/security")
    
    async def _api_request(self, method: str, path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make authenticated API request"""
        headers = {
            "Content-Type": "application/json",
            "X-API-Gateway": "MCP-Analysis"
        }
        
        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)
        
        url = urljoin(self.base_url, path)
        timeout = 30.0
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    **kwargs
                )
                
                if response.status_code >= 400:
                    logger.warning(f"API error {response.status_code}: {response.text}")
                    return None
                
                return response.json()
                
            except Exception as e:
                logger.error(f"API request failed {url}: {e}")
                return None

# Global analysis resource provider
analysis_resource_provider = AnalysisResourceProvider()
```

### Integrating New Resources

Update the resource manager to include your new resource provider:

```python
# app/mcp/resources/manager.py

from app.mcp.resources.analysis import analysis_resource_provider

class ViolentUTFResourceManager:
    async def list_resources(self) -> List[Resource]:
        """List all available resources"""
        resources = []
        
        # ... existing resource providers ...
        
        # Add analysis resources
        analysis_resources = await analysis_resource_provider.list_resources()
        resources.extend(analysis_resources)
        
        logger.info(f"Listed {len(resources)} MCP resources")
        return resources
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a specific resource by URI"""
        # ... existing URI parsing ...
        
        # Add analysis resource handling
        if resource_type == "analysis":
            data = await analysis_resource_provider.read_resource(resource_id)
        # ... existing resource types ...
        
        # ... rest of method ...
```

## Adding New Transports

### Creating Custom Transport

Create a new transport in `app/mcp/server/transports.py`:

```python
# WebSocket transport example
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mcp.types import JSONRPCMessage

logger = logging.getLogger(__name__)

class WebSocketTransport:
    """WebSocket transport for MCP communication"""
    
    def __init__(self, mcp_server, auth_handler):
        self.mcp_server = mcp_server
        self.auth_handler = auth_handler
        self.active_connections: Dict[str, WebSocket] = {}
    
    def create_app(self) -> FastAPI:
        """Create WebSocket transport FastAPI app"""
        app = FastAPI(title="MCP WebSocket Transport")
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.handle_websocket_connection(websocket)
        
        return app
    
    async def handle_websocket_connection(self, websocket: WebSocket):
        """Handle WebSocket connection"""
        connection_id = f"ws_{id(websocket)}"
        
        try:
            await websocket.accept()
            self.active_connections[connection_id] = websocket
            logger.info(f"WebSocket connection established: {connection_id}")
            
            # Authentication handshake
            auth_result = await self.authenticate_connection(websocket)
            if not auth_result:
                await websocket.close(code=4001, reason="Authentication failed")
                return
            
            # Message handling loop
            while True:
                try:
                    # Receive message
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Process MCP message
                    response = await self.process_mcp_message(message, auth_result)
                    
                    # Send response
                    if response:
                        await websocket.send_text(json.dumps(response))
                        
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "error": {"code": -32700, "message": "Parse error"}
                    }))
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
    
    async def authenticate_connection(self, websocket: WebSocket) -> Optional[Dict[str, Any]]:
        """Authenticate WebSocket connection"""
        try:
            # Wait for auth message
            auth_data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=10.0
            )
            
            auth_message = json.loads(auth_data)
            token = auth_message.get("token")
            
            if not token:
                return None
            
            # Validate token
            user_info = await self.auth_handler.validate_token(token)
            if user_info:
                await websocket.send_text(json.dumps({
                    "type": "auth_success",
                    "user": user_info
                }))
                return user_info
            else:
                await websocket.send_text(json.dumps({
                    "type": "auth_failed",
                    "message": "Invalid token"
                }))
                return None
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    async def process_mcp_message(self, message: Dict[str, Any], user_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process MCP JSON-RPC message"""
        try:
            method = message.get("method")
            params = message.get("params", {})
            message_id = message.get("id")
            
            if method == "tools/list":
                result = await self.mcp_server._list_tools()
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": [tool.dict() for tool in result]
                }
            
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                result = await self.mcp_server._call_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": result
                }
            
            elif method == "resources/list":
                result = await self.mcp_server._list_resources()
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": [resource.dict() for resource in result]
                }
            
            elif method == "resources/read":
                uri = params.get("uri")
                result = await self.mcp_server._read_resource(uri)
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "result": result
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": message_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                
        except Exception as e:
            logger.error(f"Message processing error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def broadcast_notification(self, notification: Dict[str, Any]):
        """Broadcast notification to all connected clients"""
        message = json.dumps(notification)
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send notification to {connection_id}: {e}")

def create_websocket_transport(mcp_server, auth_handler) -> FastAPI:
    """Create WebSocket transport"""
    transport = WebSocketTransport(mcp_server, auth_handler)
    return transport.create_app()
```

### Transport Configuration

Update the MCP server to support your new transport:

```python
# app/mcp/server/base.py

def mount_to_app(self, app: FastAPI) -> None:
    """Mount MCP server to existing ViolentUTF FastAPI app"""
    # ... existing SSE transport ...
    
    # Add WebSocket transport
    if mcp_settings.MCP_TRANSPORT_TYPE == "websocket":
        from app.mcp.server.transports import create_websocket_transport
        ws_app = create_websocket_transport(self.server, self.auth_handler)
        app.mount(mcp_settings.MCP_WEBSOCKET_ENDPOINT, ws_app)
        logger.info(f"Mounted WebSocket transport at {mcp_settings.MCP_WEBSOCKET_ENDPOINT}")
```

## Testing Framework

### Unit Testing

Create unit tests for your components:

```python
# tests/test_dataset_tools.py
import pytest
from unittest.mock import Mock, patch, AsyncMock

from app.mcp.tools.datasets import DatasetManagementTools

class TestDatasetTools:
    """Unit tests for dataset management tools"""
    
    @pytest.fixture
    def dataset_tools(self):
        """Create DatasetManagementTools instance"""
        return DatasetManagementTools()
    
    def test_get_tools(self, dataset_tools):
        """Test tool creation"""
        tools = dataset_tools.get_tools()
        
        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]
        assert "list_datasets" in tool_names
        assert "get_dataset" in tool_names
        assert "upload_dataset" in tool_names
        assert "delete_dataset" in tool_names
        assert "validate_dataset" in tool_names
    
    def test_tool_schemas(self, dataset_tools):
        """Test tool input schemas"""
        tools = dataset_tools.get_tools()
        
        for tool in tools:
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema
    
    @pytest.mark.asyncio
    async def test_list_datasets_execution(self, dataset_tools):
        """Test list datasets tool execution"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "datasets": [
                    {"name": "test_dataset", "category": "custom", "size": 100}
                ]
            }
            
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )
            
            # Execute tool
            result = await dataset_tools.execute_tool(
                "list_datasets",
                {"category": "custom"},
                {"token": "test_token"}
            )
            
            assert "datasets" in result
            assert len(result["datasets"]) == 1
            assert result["datasets"][0]["name"] == "test_dataset"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, dataset_tools):
        """Test error handling in tool execution"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock error response
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"detail": "Dataset not found"}
            
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )
            
            # Execute tool
            result = await dataset_tools.execute_tool(
                "get_dataset",
                {"dataset_name": "nonexistent"},
                {"token": "test_token"}
            )
            
            assert "error" in result
            assert result["error"] == "api_error_404"
            assert "Dataset not found" in result["message"]
    
    @pytest.mark.asyncio
    async def test_unknown_tool(self, dataset_tools):
        """Test unknown tool handling"""
        result = await dataset_tools.execute_tool(
            "unknown_tool",
            {},
            None
        )
        
        assert result["error"] == "unknown_tool"
        assert "unknown_tool" in result["message"]
```

### Integration Testing

Create integration tests:

```python
# tests/test_mcp_integration.py
import pytest
import asyncio
from fastapi.testclient import TestClient

from app.main import app
from app.mcp.server import mcp_server

class TestMCPIntegration:
    """Integration tests for MCP server"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    async def mcp_initialized(self):
        """Initialize MCP server for testing"""
        await mcp_server.initialize()
        yield mcp_server
    
    def test_health_endpoint(self, client):
        """Test MCP health endpoint"""
        response = client.get("/mcp/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_tool_discovery(self, mcp_initialized):
        """Test tool discovery process"""
        # Mount to a test app
        from fastapi import FastAPI
        test_app = FastAPI()
        mcp_initialized.mount_to_app(test_app)
        
        # Test tool listing
        tools = await mcp_initialized._list_tools()
        assert len(tools) > 0
        
        # Verify specialized tools are present
        tool_names = [tool.name for tool in tools]
        assert "list_generators" in tool_names
        assert "list_orchestrators" in tool_names
    
    @pytest.mark.asyncio
    async def test_resource_access(self, mcp_initialized):
        """Test resource access"""
        # Test resource listing
        resources = await mcp_initialized._list_resources()
        assert isinstance(resources, list)
        
        # Resources might be empty in test environment
        # Just verify the call succeeds
    
    def test_oauth_endpoints(self, client):
        """Test OAuth proxy endpoints"""
        # Test authorization endpoint
        response = client.get("/mcp/oauth/authorize", params={
            "client_id": "test_client",
            "redirect_uri": "http://localhost:3000/callback",
            "state": "test_state"
        })
        
        # Should redirect to Keycloak (or return error in test env)
        assert response.status_code in [302, 500]  # 500 expected in test without Keycloak
```

### Performance Testing

Create performance tests:

```python
# tests/test_performance.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from app.mcp.tools import tool_registry
from app.mcp.resources import resource_registry

class TestPerformance:
    """Performance tests for MCP components"""
    
    @pytest.mark.asyncio
    async def test_tool_discovery_performance(self):
        """Test tool discovery performance"""
        start_time = time.time()
        
        await tool_registry.discover_tools()
        tools = await tool_registry.list_tools()
        
        discovery_time = time.time() - start_time
        
        # Should complete within 2 seconds
        assert discovery_time < 2.0
        assert len(tools) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test concurrent tool execution"""
        # Initialize tools
        await tool_registry.discover_tools()
        
        async def execute_tool():
            return await tool_registry.call_tool(
                "list_generators",
                {},
                {"token": "test_token"}
            )
        
        # Execute 10 concurrent tool calls
        start_time = time.time()
        tasks = [execute_tool() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Should complete within 5 seconds
        assert execution_time < 5.0
        
        # Most calls should succeed (some may fail due to no API in test)
        successful_calls = sum(1 for result in results if not isinstance(result, Exception))
        assert successful_calls >= 0  # At least some should work
    
    @pytest.mark.asyncio
    async def test_resource_cache_performance(self):
        """Test resource caching performance"""
        await resource_registry.initialize()
        
        # First access (cache miss)
        start_time = time.time()
        resources1 = await resource_registry.list_resources()
        first_access_time = time.time() - start_time
        
        # Second access (cache hit)
        start_time = time.time()
        resources2 = await resource_registry.list_resources()
        second_access_time = time.time() - start_time
        
        # Second access should be faster (or at least not slower)
        assert second_access_time <= first_access_time * 1.1  # Allow 10% variance
```

## Debugging and Profiling

### Debug Configuration

Enable debug mode for development:

```python
# app/mcp/config.py
class MCPSettings(BaseSettings):
    MCP_DEBUG_MODE: bool = False
    MCP_LOG_LEVEL: str = "INFO"
    MCP_DEVELOPMENT_MODE: bool = False
    
    # Development overrides
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if self.MCP_DEVELOPMENT_MODE:
            self.MCP_DEBUG_MODE = True
            self.MCP_LOG_LEVEL = "DEBUG"
            self.MCP_REQUIRE_AUTH = False
```

### Logging Setup

Configure detailed logging:

```python
# app/mcp/logging.py
import logging
import sys
from typing import Dict, Any

def setup_mcp_logging(config: Dict[str, Any]):
    """Setup MCP-specific logging"""
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Setup file handler if configured
    if config.get("log_file"):
        file_handler = logging.FileHandler(config["log_file"])
        file_handler.setFormatter(formatter)
    
    # Configure MCP loggers
    mcp_loggers = [
        'app.mcp',
        'app.mcp.server',
        'app.mcp.tools',
        'app.mcp.resources',
        'app.mcp.auth'
    ]
    
    for logger_name in mcp_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(config.get("log_level", "INFO"))
        logger.addHandler(console_handler)
        
        if config.get("log_file"):
            logger.addHandler(file_handler)
```

### Performance Profiling

Create profiling utilities:

```python
# app/mcp/profiling.py
import functools
import time
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def profile_execution(func_name: str = None):
    """Decorator to profile function execution time"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            name = func_name or f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"Profile: {name} completed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Profile: {name} failed after {execution_time:.3f}s - {e}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            name = func_name or f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"Profile: {name} completed in {execution_time:.3f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Profile: {name} failed after {execution_time:.3f}s - {e}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# Usage example:
@profile_execution("tool_execution")
async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # Tool execution logic
    pass
```

## Deployment and Distribution

### Building Custom MCP Server

Create a standalone distribution:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="violentutf-mcp-server",
    version="1.0.0",
    description="ViolentUTF Model Context Protocol Server",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn>=0.20.0",
        "model-context-protocol>=0.1.0",
        "httpx>=0.24.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "python-jose[cryptography]>=3.3.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0"
        ]
    },
    entry_points={
        "console_scripts": [
            "violentutf-mcp=app.mcp.cli:main"
        ]
    }
)
```

### Docker Development

Create development Dockerfile:

```dockerfile
# Dockerfile.dev
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

# Copy source code
COPY app/ ./app/
COPY tests/ ./tests/

# Development configuration
ENV MCP_DEVELOPMENT_MODE=true
ENV MCP_DEBUG_MODE=true
ENV PYTHONPATH=/app

# Hot reload command
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
```

### Development Docker Compose

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  violentutf-api-dev:
    build:
      context: ./violentutf_api/fastapi_app
      dockerfile: Dockerfile.dev
    volumes:
      - ./violentutf_api/fastapi_app:/app
      - ./logs:/app/logs
    environment:
      - MCP_DEVELOPMENT_MODE=true
      - MCP_DEBUG_MODE=true
      - MCP_LOG_LEVEL=DEBUG
      - MCP_REQUIRE_AUTH=false
    ports:
      - "8000:8000"
    networks:
      - vutf-network
    depends_on:
      - keycloak
      - apisix-apisix-1

networks:
  vutf-network:
    external: true
```

## Best Practices

### Code Organization

1. **Separation of Concerns**: Keep tools, resources, and transports in separate modules
2. **Interface Consistency**: Follow MCP protocol specifications exactly
3. **Error Handling**: Provide meaningful error messages and proper HTTP status codes
4. **Async Patterns**: Use async/await consistently for all I/O operations
5. **Type Hints**: Use comprehensive type hints for better IDE support and validation

### Security Considerations

1. **Input Validation**: Validate all tool parameters and resource URIs
2. **Authentication**: Always require authentication in production
3. **Authorization**: Implement role-based access control for sensitive operations
4. **Rate Limiting**: Protect against abuse with proper rate limiting
5. **Logging**: Log security-relevant events for audit purposes

### Performance Optimization

1. **Caching**: Implement intelligent caching for frequently accessed data
2. **Connection Pooling**: Use connection pooling for external API calls
3. **Async Processing**: Leverage asyncio for concurrent operations
4. **Resource Management**: Implement proper resource cleanup and limits
5. **Monitoring**: Add comprehensive monitoring and alerting

### Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **Performance Tests**: Verify performance under load
4. **Security Tests**: Test authentication and authorization
5. **End-to-End Tests**: Test complete user workflows

---

*For configuration options, see [Configuration Guide](./configuration.md).*  
*For troubleshooting help, see [Troubleshooting Guide](./troubleshooting.md).*  
*For API usage, see [API Reference](./api-reference.md).*