# ViolentUTF MCP Server API Reference

## Overview

The ViolentUTF MCP (Model Context Protocol) Server provides programmatic access to AI red-teaming capabilities through the MCP standard. It implements a comprehensive set of tools, prompts, and resources for security testing and vulnerability assessment.

## Server Architecture

The MCP server is integrated into the ViolentUTF FastAPI application and accessible via Server-Sent Events (SSE) transport at `/mcp/sse`.

**Key Components:**
- **Tools**: 23+ specialized tools for generator and orchestrator management
- **Prompts**: 12+ templates for security and capability testing
- **Resources**: Dataset and configuration access with caching
- **Authentication**: Full Keycloak/JWT integration with OAuth 2.0 support

## Authentication

The MCP server requires authentication through the existing ViolentUTF system:

### OAuth 2.0 Flow (Recommended)
```bash
# Get authorization URL
GET /mcp/oauth/authorize

# Exchange code for token
POST /mcp/oauth/token
```

### Bearer Token
```bash
# Use existing JWT token
Authorization: Bearer <your-jwt-token>
```

## Available Tools

### Generator Management

#### `list_generators`
Lists all configured generators with optional filtering.

**Arguments:**
- `provider_type` (optional): Filter by provider (openai, anthropic, etc.)
- `status` (optional): Filter by status (active, inactive)

**Example:**
```json
{"name": "list_generators", "arguments": {"provider_type": "openai"}}
```

#### `create_generator`
Creates a new generator configuration.

**Arguments:**
- `provider_type` (required): Provider type (openai, anthropic, ollama, etc.)
- `model_name` (required): Model identifier
- `parameters` (optional): Model-specific parameters

**Example:**
```json
{
  "name": "create_generator",
  "arguments": {
    "provider_type": "openai",
    "model_name": "gpt-4",
    "parameters": {
      "temperature": 0.7,
      "max_tokens": 1000
    }
  }
}
```

#### `test_generator`
Tests a generator with sample prompts.

**Arguments:**
- `generator_id` (required): Generator to test
- `test_prompts` (optional): Custom test prompts
- `include_metrics` (optional): Include performance metrics

### Orchestrator Management

#### `create_orchestrator`
Creates a new orchestrator configuration.

**Arguments:**
- `orchestrator_type` (required): Type of orchestrator
- `target_generator_id` (required): Target generator
- `dataset_id` (optional): Dataset for testing
- `config` (optional): Additional configuration

#### `start_orchestrator`
Starts orchestrator execution.

**Arguments:**
- `orchestrator_id` (required): Orchestrator to start
- `execution_config` (optional): Execution parameters

#### `get_orchestrator_results`
Retrieves orchestrator execution results.

**Arguments:**
- `orchestrator_id` (required): Orchestrator ID
- `format` (optional): Result format (json, csv, html)

## Available Prompts

### Security Testing Prompts

#### `jailbreak_test`
Generates jailbreak testing prompts.

**Arguments:**
- `scenario` (optional): Jailbreak scenario type
- `target_behavior` (optional): Specific behavior to test
- `complexity_level` (optional): Test complexity (basic, intermediate, advanced)

#### `bias_detection`
Creates prompts for bias and fairness assessment.

**Arguments:**
- `bias_type` (optional): Type of bias to test
- `demographics` (optional): Demographic categories
- `context` (optional): Testing context

#### `prompt_injection`
Generates prompt injection testing scenarios.

**Arguments:**
- `injection_type` (optional): Type of injection attack
- `payload` (optional): Custom injection payload

### General Testing Prompts

#### `capability_test`
Assesses AI capabilities in specific domains.

**Arguments:**
- `domain` (required): Testing domain (reasoning, creativity, knowledge)
- `difficulty` (optional): Test difficulty level
- `metrics` (optional): Success metrics

## Available Resources

### Dataset Resources

Access datasets using URI format: `violentutf://datasets/{dataset_id}`

**Example:**
```json
{"uri": "violentutf://datasets/jailbreak_scenarios"}
```

### Configuration Resources

Access system configurations: `violentutf://config/{config_type}`

**Example:**
```json
{"uri": "violentutf://config/generators"}
```

### Results Resources

Access execution results: `violentutf://results/{orchestrator_id}`

## MCP Protocol Usage

### Initialize Connection
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {},
      "resources": {},
      "prompts": {}
    },
    "clientInfo": {
      "name": "ViolentUTF Client",
      "version": "1.0.0"
    }
  }
}
```

### List Available Tools
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list"
}
```

### Execute Tool
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "create_generator",
    "arguments": {
      "provider_type": "openai",
      "model_name": "gpt-4"
    }
  }
}
```

### Get Prompt
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "prompts/get",
  "params": {
    "name": "jailbreak_test",
    "arguments": {
      "scenario": "dan_attack",
      "complexity_level": "advanced"
    }
  }
}
```

### Read Resource
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "resources/read",
  "params": {
    "uri": "violentutf://datasets/security_prompts"
  }
}
```

## Server Endpoints

### SSE Transport
- **Endpoint**: `/mcp/sse`
- **Method**: GET/POST
- **Protocol**: JSON-RPC over Server-Sent Events

### OAuth Authentication
- **Authorization**: `/mcp/oauth/authorize`
- **Token Exchange**: `/mcp/oauth/token`
- **Callback**: `/mcp/oauth/callback`

## Configuration

### Environment Variables
```bash
# Server Configuration
MCP_SERVER_NAME="ViolentUTF MCP Server"
MCP_TRANSPORT_TYPE="sse"
MCP_SSE_ENDPOINT="/mcp/sse"

# Feature Flags
MCP_ENABLE_TOOLS=true
MCP_ENABLE_RESOURCES=true
MCP_ENABLE_PROMPTS=true

# Security
MCP_REQUIRE_AUTH=true
MCP_ALLOWED_ORIGINS=["http://localhost:*"]

# Performance
MCP_TOOL_TIMEOUT=300
MCP_RESOURCE_CACHE_TTL=3600
```

## Error Handling

The server returns standard JSON-RPC error responses:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "validation_errors": ["provider_type is required"]
    }
  }
}
```

## Best Practices

1. **Initialize First**: Always call `initialize` before other operations
2. **Handle Authentication**: Ensure proper OAuth flow or bearer token
3. **Check Tool Availability**: Use `tools/list` to verify available tools
4. **Validate Arguments**: Check tool schemas before execution
5. **Use Timeouts**: Long-running operations may take several minutes
6. **Cache Resources**: Resource content is cached for 1 hour by default

## Troubleshooting

### Connection Issues
- Verify the MCP server is running at `/mcp/sse`
- Check network connectivity and CORS settings
- Ensure proper SSE client implementation

### Authentication Issues
- Verify JWT token is valid and not expired
- Check OAuth 2.0 flow completion
- Ensure proper authorization headers

### Tool Execution Issues
- Validate tool arguments against schema
- Check tool timeout settings (5 minutes for generators)
- Review error messages for specific validation failures
