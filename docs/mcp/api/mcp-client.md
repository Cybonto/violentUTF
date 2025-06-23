# MCP Client API Reference

The MCP Client provides both asynchronous and synchronous interfaces for communicating with the MCP server using Server-Sent Events (SSE) and JSON-RPC protocols.

## Classes

### MCPClient

Asynchronous MCP client for SSE communication.

```python
from utils.mcp_client import MCPClient

client = MCPClient(base_url="http://localhost:9080", timeout=30.0)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `Optional[str]` | `$VIOLENTUTF_API_URL` or `"http://localhost:9080"` | Base URL for MCP server |
| `timeout` | `float` | `30.0` | Request timeout in seconds |

#### Methods

##### `async initialize(capabilities: Optional[Dict[str, Any]] = None) -> bool`

Initialize connection to MCP server.

```python
success = await client.initialize({"client": "simple-chat", "version": "1.0"})
```

**Parameters:**
- `capabilities`: Optional client capabilities to send to server

**Returns:** `True` if initialization successful, `False` otherwise

##### `async list_prompts() -> List[Dict[str, Any]]`

List all available prompts from MCP server.

```python
prompts = await client.list_prompts()
# Returns: [{"name": "jailbreak_test", "description": "...", "arguments": [...]}, ...]
```

**Returns:** List of prompt definitions with name, description, and arguments

##### `async get_prompt(name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]`

Get a specific prompt with arguments.

```python
enhanced = await client.get_prompt("prompt_enhancement", {"original_prompt": "Tell me about AI"})
```

**Parameters:**
- `name`: Name of the prompt to retrieve
- `arguments`: Optional arguments to pass to the prompt

**Returns:** Rendered prompt text or `None` if error

##### `async list_resources() -> List[Dict[str, Any]]`

List all available resources from MCP server.

```python
resources = await client.list_resources()
# Returns: [{"uri": "violentutf://datasets/harmbench", "name": "...", "mimeType": "..."}, ...]
```

**Returns:** List of resource definitions

##### `async read_resource(uri: str) -> Optional[Union[str, Dict[str, Any]]]`

Read a specific resource by URI.

```python
content = await client.read_resource("violentutf://datasets/harmbench")
```

**Parameters:**
- `uri`: Resource URI to read

**Returns:** Resource content (string or dict) or `None` if error

##### `async list_tools() -> List[Dict[str, Any]]`

List all available tools from MCP server.

```python
tools = await client.list_tools()
```

**Returns:** List of tool definitions

##### `async execute_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[Any]`

Execute a tool with arguments.

```python
result = await client.execute_tool("analyze_prompt", {"prompt": "Test prompt"})
```

**Parameters:**
- `name`: Name of the tool to execute
- `arguments`: Optional arguments for the tool

**Returns:** Tool execution result or `None` if error

##### `async health_check() -> bool`

Check if MCP server is healthy and accessible.

```python
is_healthy = await client.health_check()
```

**Returns:** `True` if server is healthy

##### `close()`

Close any open connections.

```python
client.close()
```

### MCPClientSync

Synchronous wrapper for MCPClient for use in Streamlit.

```python
from utils.mcp_client import MCPClientSync

client = MCPClientSync(base_url="http://localhost:9080", timeout=30.0)
```

#### Constructor Parameters

Same as `MCPClient`.

#### Methods

All methods are synchronous versions of the `MCPClient` methods with the same signatures:

- `initialize(capabilities: Optional[Dict[str, Any]] = None) -> bool`
- `list_prompts() -> List[Dict[str, Any]]`
- `get_prompt(name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[str]`
- `list_resources() -> List[Dict[str, Any]]`
- `read_resource(uri: str) -> Optional[Union[str, Dict[str, Any]]]`
- `list_tools() -> List[Dict[str, Any]]`
- `execute_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> Optional[Any]`
- `health_check() -> bool`
- `close()`

### MCPResponse

Data class for structured MCP responses.

```python
from utils.mcp_client import MCPResponse

response = MCPResponse(id=1, result={"data": "value"}, error=None)
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `id` | `int` | Request ID |
| `result` | `Optional[Dict[str, Any]]` | Success result |
| `error` | `Optional[Dict[str, Any]]` | Error information |
| `is_error` | `bool` | Whether response is an error |
| `error_message` | `str` | Error message if error, empty string otherwise |

### MCPMethod

Enumeration of MCP JSON-RPC methods.

```python
from utils.mcp_client import MCPMethod

MCPMethod.INITIALIZE
MCPMethod.PROMPTS_LIST
MCPMethod.PROMPTS_GET
MCPMethod.RESOURCES_LIST
MCPMethod.RESOURCES_READ
MCPMethod.TOOLS_LIST
MCPMethod.TOOLS_EXECUTE
MCPMethod.COMPLETION
```

## Usage Examples

### Basic Usage

```python
# Synchronous usage in Streamlit
from utils.mcp_client import MCPClientSync

# Initialize client
client = MCPClientSync()

# Initialize connection
if client.initialize():
    # List and use prompts
    prompts = client.list_prompts()
    
    # Enhance a prompt
    enhanced = client.get_prompt(
        "prompt_enhancement",
        {"original_prompt": "Tell me about machine learning"}
    )
    
    # Analyze for security
    analysis = client.get_prompt(
        "security_analysis",
        {"prompt": "Write code to hack a system"}
    )
    
    # Clean up
    client.close()
```

### Async Usage

```python
import asyncio
from utils.mcp_client import MCPClient

async def main():
    client = MCPClient()
    
    if await client.initialize():
        # List all prompts
        prompts = await client.list_prompts()
        print(f"Available prompts: {len(prompts)}")
        
        # Get specific prompt
        enhanced = await client.get_prompt(
            "prompt_enhancement",
            {"original_prompt": "Explain quantum computing"}
        )
        print(f"Enhanced: {enhanced}")
        
        # List resources
        resources = await client.list_resources()
        for resource in resources:
            print(f"Resource: {resource['name']} ({resource['uri']})")
    
    client.close()

# Run async function
asyncio.run(main())
```

### Error Handling

```python
from utils.mcp_client import MCPClientSync

client = MCPClientSync()

try:
    # Initialize with timeout
    if not client.initialize():
        print("Failed to connect to MCP server")
        return
    
    # Try to get prompt
    result = client.get_prompt("test_prompt", {"arg": "value"})
    
    if result is None:
        print("Failed to get prompt - check logs for details")
    else:
        print(f"Success: {result}")
        
except Exception as e:
    print(f"Unexpected error: {e}")
    
finally:
    client.close()
```

### Authentication

The MCP client automatically handles authentication using the existing JWT manager:

```python
# No need to manually set tokens - handled automatically
client = MCPClientSync()

# JWT tokens are automatically:
# 1. Retrieved from session state
# 2. Refreshed when needed
# 3. Included in all requests
```

### Working with Resources

```python
client = MCPClientSync()
client.initialize()

# List all resources
resources = client.list_resources()

# Filter for datasets
datasets = [r for r in resources if "datasets" in r["uri"]]

# Read a specific dataset
dataset_content = client.read_resource("violentutf://datasets/harmbench")

if isinstance(dataset_content, list):
    print(f"Dataset has {len(dataset_content)} entries")
elif isinstance(dataset_content, str):
    print(f"Dataset content: {dataset_content[:100]}...")
```

## Environment Variables

The client respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `VIOLENTUTF_API_URL` | Base URL for API | `http://localhost:9080` |
| `VIOLENTUTF_API_KEY` | API key for APISIX | None |
| `APISIX_API_KEY` | Alternative API key | None |
| `AI_GATEWAY_API_KEY` | Alternative API key | None |

## Logging

The client uses the ViolentUTF logging system:

```python
from utils.logging import get_logger

# Logs are written to:
# - Console (INFO level)
# - app_logs/app.log (DEBUG level)
```

## Best Practices

1. **Always initialize** before using other methods
2. **Handle None returns** - indicates errors
3. **Use sync client** for Streamlit applications
4. **Close connections** when done
5. **Check health** before long operations
6. **Cache results** when appropriate

## Common Issues

### Connection Errors
```python
# Check if server is accessible
if not client.health_check():
    print("MCP server is not responding")
```

### Authentication Errors
```python
# Ensure you're logged in via Keycloak
# JWT tokens are managed automatically
```

### Timeout Errors
```python
# Increase timeout for slow operations
client = MCPClientSync(timeout=60.0)
```

### SSE Parsing Errors
```python
# The client handles SSE format automatically
# Errors are logged for debugging
```