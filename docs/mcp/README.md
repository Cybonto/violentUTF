# ViolentUTF Model Context Protocol (MCP) Server

## Overview

The ViolentUTF MCP Server provides a standardized interface for LLM clients to interact with the ViolentUTF AI red-teaming platform. Built on the [Model Context Protocol](https://modelcontextprotocol.io/), it enables seamless integration between AI models and ViolentUTF's security testing capabilities.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LLM Client    │────│   MCP Server    │────│  ViolentUTF API │
│  (Claude, etc)  │    │   (Phase 1-2)   │    │   (FastAPI)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                        ┌─────────────┐
                        │   APISIX    │
                        │  Gateway    │
                        └─────────────┘
                              │
                        ┌─────────────┐
                        │  Keycloak   │
                        │    SSO      │
                        └─────────────┘
```

## Features

### 🔧 Tool Interface
- **23+ Specialized Tools**: High-level operations for generators and orchestrators
- **Generator Management**: Create, test, update, and manage AI model configurations
- **Orchestrator Control**: Execute and monitor security testing campaigns
- **Parameter Validation**: Comprehensive input validation and error handling

### 📊 Resource Interface
- **Generator Resources**: Access to AI model configurations and test results
- **Dataset Resources**: Browse and access red-teaming datasets
- **Orchestrator Resources**: Monitor execution status and retrieve results
- **Configuration Resources**: System settings and component configurations
- **Session Resources**: Active session data and history

### 🧠 Intelligent Analysis
- **Security Testing Prompts**: 12+ specialized prompts for vulnerability assessment
- **Context-Aware Responses**: Dynamic prompt generation with argument injection
- **Real-time Evaluation**: Integration with PyRIT scorers for automated analysis

### 💬 Multiple Access Methods
- **JSON-RPC Protocol**: Standard MCP communication over Server-Sent Events
- **RESTful Interface**: Direct API access through APISIX gateway
- **OAuth 2.0 Integration**: Secure authentication with PKCE support

### 🔐 Security & Authentication
- **JWT Integration**: Seamless token management and refresh
- **APISIX Gateway**: All requests routed through secure API gateway
- **Keycloak SSO**: Enterprise-grade authentication and authorization
- **Role-Based Access**: Fine-grained permission control

### 🚀 Performance & Reliability
- **Resource Caching**: Intelligent caching with TTL management
- **Error Recovery**: Graceful degradation and comprehensive error handling
- **Container Integration**: Docker-aware networking and service discovery
- **Concurrent Operations**: Support for parallel tool execution

## Quick Start

### Prerequisites

- Docker and Docker Compose
- ViolentUTF platform deployed and running
- MCP-compatible LLM client

### Installation

1. **Deploy ViolentUTF with MCP Support**:
   ```bash
   cd ViolentUTF_nightly
   ./setup_macos.sh  # or setup_linux.sh
   ```

2. **Verify MCP Server**:
   ```bash
   curl http://localhost:9080/mcp/health
   ```

3. **Configure LLM Client**:
   ```json
   {
     "mcpServers": {
       "violentutf": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-sse"],
         "env": {
           "MCP_SERVER_URL": "http://localhost:9080/mcp/sse"
         }
       }
     }
   }
   ```

## Documentation Structure

### Core Documentation
- **[Architecture Overview](./architecture.md)**: System design and components
- **[Configuration Guide](./configuration.md)**: Setup and configuration options
- **[Development Guide](./development.md)**: Extending and customizing the MCP server
- **[Troubleshooting Guide](./troubleshooting.md)**: Common issues and solutions

### Implementation Reference
- **[Anthropic MCP Reference](./anthropic_mcp.md)**: Official MCP protocol specification
- **[API Reference](./api-reference.md)**: Complete API documentation
- **[Working Endpoints](./mcp_endpoints_working.md)**: Verified functional endpoints

### API Reference
- **[MCP Client API](./api/mcp-client.md)**: Core MCP client documentation
- **[MCP Integration API](./api/mcp-integration.md)**: Natural language and command handling
- **[Context Manager API](./api/mcp-context-manager.md)**: Context-aware features
- **[Resource Browser API](./api/mcp-resource-browser.md)**: Resource management
- **[Scorer Integration API](./api/mcp-scorer-integration.md)**: Security scoring

### Development
- **[Configuration Guide](./configuration.md)**: Setup and configuration options
- **[Troubleshooting Guide](./troubleshooting.md)**: Common issues and solutions
- **[Development Guide](./development.md)**: Extending and customizing the MCP server

## Usage Examples

### List Available Generators
```javascript
// Using MCP client
const result = await mcpClient.callTool('list_generators', {
  provider_type: 'openai',
  include_test_results: true
});
```

### Create and Test a Generator
```javascript
// Create generator
const generator = await mcpClient.callTool('create_generator', {
  name: 'GPT-4 Test Generator',
  provider_type: 'openai',
  model_name: 'gpt-4',
  parameters: {
    temperature: 0.7,
    max_tokens: 1000
  },
  test_after_creation: true
});

// Get test results
const testResult = await mcpClient.callTool('get_generator', {
  generator_id: generator.id,
  include_test_history: true
});
```

### Access Generator Configuration Resource
```javascript
// Read generator resource
const generatorConfig = await mcpClient.readResource(
  'violentutf://generator/gpt4-test-001'
);
```

### Create and Execute Orchestrator
```javascript
// Create orchestrator
const orchestrator = await mcpClient.callTool('create_orchestrator', {
  name: 'Red Team Assessment',
  orchestrator_type: 'red_teaming',
  target_generators: ['gpt4-test-001'],
  dataset_name: 'harmful_behaviors',
  max_iterations: 50,
  auto_start: true
});

// Monitor progress
const status = await mcpClient.callTool('get_orchestrator', {
  orchestrator_id: orchestrator.id,
  include_progress: true
});
```

## Security Considerations

### Authentication Flow
1. **Client Authentication**: LLM client connects to MCP server
2. **Token Management**: MCP server manages JWT tokens with Keycloak
3. **API Gateway**: All ViolentUTF API calls routed through APISIX
4. **Authorization**: Role-based access control enforced at gateway level

### Network Security
- **Internal Communication**: Container-to-container networking
- **TLS/SSL**: HTTPS encryption for external connections
- **API Keys**: Secure API key management for AI providers
- **Rate Limiting**: Protection against abuse and resource exhaustion

## Monitoring and Logging

### Health Checks
- **MCP Server Health**: `GET /mcp/health`
- **Component Status**: Tool and resource availability monitoring
- **API Connectivity**: Backend service health verification

### Logging
- **Structured Logs**: JSON-formatted logs with correlation IDs
- **Performance Metrics**: Tool execution times and success rates
- **Error Tracking**: Comprehensive error logging and alerting
- **Audit Trail**: Security-relevant actions and access patterns

## Contributing

See [Development Guide](./development.md) for information on:
- Setting up development environment
- Adding new tools and resources
- Testing and validation
- Code style and conventions

## License

This project is part of the ViolentUTF platform. See the main repository for license information.

## Support

- **Documentation**: Comprehensive guides and API reference
- **GitHub Issues**: Bug reports and feature requests
- **Community**: Discussions and community support

---

*For detailed implementation information, see the phase-specific documentation linked above.*