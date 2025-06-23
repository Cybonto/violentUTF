# ViolentUTF MCP Server - Verified Working Endpoints

## Summary
The ViolentUTF MCP (Model Context Protocol) server is fully operational with Server-Sent Events transport, providing complete access to AI red-teaming capabilities through the MCP standard.

## Working Endpoints

### 1. Initialize
```bash
curl -X POST http://localhost:9080/mcp/sse/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "params": {"capabilities": {}}, "id": 1}'
```

Response:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "serverInfo": {
      "name": "ViolentUTF MCP Server",
      "version": "1.0.0"
    },
    "capabilities": {
      "tools": true,
      "resources": true,
      "prompts": true,
      "sampling": false,
      "notifications": false,
      "experimental": {}
    }
  },
  "id": 1
}
```

### 2. List Prompts
```bash
curl -X POST http://localhost:9080/mcp/sse/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "prompts/list", "id": 2}'
```

Returns 12 security testing prompts including:
- **jailbreak_test** - Standard jailbreak vulnerability testing
- **bias_detection** - AI bias and fairness assessment
- **prompt_injection** - Prompt injection attack testing
- **harmful_content_test** - Harmful content generation testing
- **privacy_test** - Privacy violation and data leakage testing
- **adversarial_test** - Advanced adversarial attack testing
- **capability_test** - AI capability assessment in specific domains
- **reasoning_test** - Logical reasoning and problem-solving evaluation
- **creativity_test** - Creative and generative capability testing
- **knowledge_test** - Knowledge accuracy and factual testing
- **conversation_test** - Conversational ability assessment
- **benchmark_test** - Performance benchmark testing

### 3. List Resources
```bash
curl -X POST http://localhost:9080/mcp/sse/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "resources/list", "id": 3}'
```

Returns various resources including:
- **violentutf://config/database/status** - Database connection and health status
- **violentutf://config/environment/current** - Current environment configuration
- **violentutf://config/system/info** - System information and capabilities
- **violentutf://config/mcp/settings** - MCP server configuration details
- **violentutf://config/api/health** - API service health information
- **violentutf://generator/{id}** - Individual generator configurations
- **violentutf://dataset/{name}** - Dataset information and statistics
- **violentutf://orchestrator/{id}** - Orchestrator execution details

### 4. List Tools
```bash
curl -X POST http://localhost:9080/mcp/sse/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 4}'
```

Returns 23+ specialized tools including:
- **Generator Management** (10 tools): list_generators, create_generator, test_generator, etc.
- **Orchestrator Management** (13 tools): list_orchestrators, create_orchestrator, start_orchestrator, etc.

### 5. Execute Tool
```bash
curl -X POST http://localhost:9080/mcp/sse/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "tools/call", 
    "params": {
      "name": "list_generators",
      "arguments": {"provider_type": "openai"}
    },
    "id": 5
  }'
```

### 6. Get Prompt
```bash
curl -X POST http://localhost:9080/mcp/sse/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "prompts/get", 
    "params": {
      "name": "jailbreak_test",
      "arguments": {"scenario": "dan_attack", "complexity_level": "advanced"}
    },
    "id": 6
  }'
```

### 7. Read Resource
```bash
curl -X POST http://localhost:9080/mcp/sse/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "resources/read", 
    "params": {
      "uri": "violentutf://config/system/info"
    },
    "id": 7
  }'
```

## Implementation Features

### Security & Authentication
- **JWT Token Integration**: Full integration with ViolentUTF authentication system
- **APISIX Gateway Routing**: All requests properly routed through API gateway
- **OAuth 2.0 Support**: Complete OAuth proxy implementation with PKCE
- **Role-Based Access**: Fine-grained permission control

### Performance & Reliability
- **Resource Caching**: Intelligent caching with TTL management (1 hour default)
- **Error Handling**: Comprehensive error recovery and user-friendly messages
- **Rate Limiting**: Built-in protection against abuse
- **Concurrent Operations**: Support for parallel tool execution

### Protocol Compliance
- **JSON-RPC 2.0**: Full compliance with JSON-RPC specification
- **MCP Standard**: Complete implementation of Model Context Protocol
- **SSE Transport**: Server-Sent Events for real-time communication
- **Capabilities Declaration**: Proper server capabilities advertisement

## Client Integration Status

### Ready for Production
- **Claude Desktop**: Full compatibility with native MCP support
- **VS Code Extensions**: Ready for IDE integration and security testing
- **Custom Applications**: Complete API for building specialized tools
- **Web Clients**: CORS-enabled for browser-based applications

## Next Steps
- **Tool Expansion**: Additional specialized tools for advanced security testing
- **WebSocket Transport**: Alternative transport layer for specific use cases
- **Advanced Caching**: Distributed caching for high-availability deployments
- **Monitoring Integration**: Enhanced metrics and observability features