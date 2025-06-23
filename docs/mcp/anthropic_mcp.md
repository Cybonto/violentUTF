# Anthropic Model Context Protocol (MCP) Reference

## Overview

The Model Context Protocol (MCP) is an open standard that enables secure connections between AI hosts (applications with LLMs) and external data sources and tools. It provides a universal way for LLMs to access contextual information through a standard client-server architecture.

---

## Architecture

### Core Components

**Hosts**
- LLM applications that initiate connections
- Contain multiple MCP clients
- Examples: Claude Desktop, IDEs, custom applications

**Clients**
- Maintain 1:1 connections with servers
- Reside inside host applications
- Handle protocol communication and message routing

**Servers**
- Provide context, tools, and prompts to clients
- Expose capabilities through MCP primitives
- Can be local processes or remote services

### Communication Model

**Protocol Layer**
- Handles message framing and communication
- Supports request/response and notification patterns
- Key methods:
  - `setRequestHandler()` - Handle incoming requests
  - `setNotificationHandler()` - Handle notifications
  - `request()` - Send requests with responses
  - `notification()` - Send one-way messages

**Connection Lifecycle**
1. **Initialization**: Exchange protocol versions and capabilities
2. **Handshake**: Send `initialize` request/response, then `initialized` notification
3. **Message Exchange**: Request-response interactions and notifications
4. **Termination**: Clean shutdown via `close()` or transport disconnection

---

## Transport Layer

### Transport Types

**1. Standard Input/Output (stdio)**
- Communication through stdin/stdout streams
- Ideal for local integrations and command-line tools
- Simple process communication model
- Example: Local Python/Node.js scripts

**2. Streamable HTTP**
- Uses HTTP POST for client-to-server communication
- Optional Server-Sent Events (SSE) for server-to-client streams
- Supports multiple concurrent clients
- Resumable connections and web-based integrations

### Technical Details
- **Wire Format**: JSON-RPC 2.0
- **Message Types**: Requests, Responses, Notifications
- **Custom Transports**: Flexible interfaces for custom implementations
- **Security**: Built-in error handling and security considerations

---

## MCP Primitives

### Resources

**Purpose**: Expose structured data that can be included in LLM context

**Key Characteristics**:
- Identified by unique URIs (e.g., `file://`, `http://`, custom schemes)
- Support both text (UTF-8) and binary (base64) content
- Application-controlled - clients decide how to use them
- Real-time updates via subscriptions

**Resource Types**:
- **Text Resources**: Source code, logs, configuration files, documentation
- **Binary Resources**: Images, PDFs, audio/video files, executables

**Implementation**:
```typescript
{
  uri: string;           // Unique identifier
  name: string;          // Human-readable name
  description?: string;  // Optional description
  mimeType?: string;     // Content type
}
```

**Discovery Methods**:
1. **Direct Lists**: Server exposes static resource catalog
2. **URI Templates**: Dynamic content generation patterns

**Best Practices**:
- Use clear, descriptive names and descriptions
- Set appropriate MIME types for content
- Implement access controls and validation
- Support subscription updates for dynamic content

### Tools

**Purpose**: Expose executable functions that LLMs can call to perform actions

**Key Characteristics**:
- Model-controlled with human approval
- Identified by unique names within server scope
- Defined with input schemas and descriptions
- Support dynamic discovery and invocation

**Tool Categories**:
- **System Operations**: File system access, shell commands
- **API Integrations**: External service interactions
- **Data Processing**: Calculations, transformations
- **Workflow Actions**: Multi-step processes

**Implementation**:
```typescript
{
  name: string;              // Unique identifier
  description?: string;      // Human-readable description
  inputSchema: {             // JSON Schema for parameters
    type: "object";
    properties: { ... };
    required?: string[];
  }
}
```

**Endpoints**:
- `tools/list` - Discover available tools
- `tools/call` - Execute tool with parameters

**Best Practices**:
- Provide clear, unambiguous descriptions
- Implement robust input validation
- Include proper error handling and status codes
- Consider security implications and rate limiting
- Use annotations to describe tool behavior

### Prompts

**Purpose**: Provide reusable, structured templates for LLM interactions

**Key Characteristics**:
- User-controlled - explicitly selected and triggered
- Support dynamic arguments and context injection
- Enable standardized interaction patterns
- Facilitate multi-step workflows

**Prompt Components**:
```typescript
{
  name: string;              // Unique identifier
  description?: string;      // Human-readable description
  arguments?: [              // Optional configurable parameters
    {
      name: string;
      description?: string;
      required?: boolean;
    }
  ]
}
```

**Use Cases**:
- **Code Generation**: Template-based code creation
- **Analysis Workflows**: Structured evaluation processes
- **Documentation**: Standardized reporting formats
- **Debugging**: Systematic troubleshooting approaches

**Implementation Features**:
- **Dynamic Arguments**: Runtime parameter injection
- **Resource Context**: Integration with resource data
- **Chained Interactions**: Multi-step workflow support
- **Template Engine**: Flexible content generation

### Sampling

**Purpose**: Enable servers to request LLM completions through clients

**Key Characteristics**:
- Server-initiated LLM text generation
- Human-in-the-loop design maintains user control
- Supports both text and image content
- Configurable model preferences and parameters

**Workflow**:
1. **Server Request**: Send sampling request with content and parameters
2. **Client Review**: User/client reviews and potentially modifies request
3. **LLM Generation**: Client generates completion from preferred model
4. **Result Review**: Client reviews completion before returning
5. **Server Response**: Server receives final completion

**Configuration Options**:
```typescript
{
  prompt: string | Content[];    // Text or multimodal content
  systemPrompt?: string;         // System instruction
  includeContext?: string;       // Additional context method
  temperature?: number;          // Randomness control
  maxTokens?: number;           // Length limit
  stopSequences?: string[];     // Completion terminators
  modelPreferences?: {          // Preferred models
    hints?: ModelHint[];
    costPriority?: number;
    speedPriority?: number;
    intelligencePriority?: number;
  }
}
```

**Use Cases**:
- **Agentic Workflows**: AI-driven decision making
- **Content Generation**: Dynamic text/code creation
- **Analysis Enhancement**: AI-assisted data interpretation
- **Interactive Processes**: Conversational tool interactions

---

## Roots

**Purpose**: Define resource boundaries and workspace organization for servers

**Key Characteristics**:
- URI-based resource boundary definitions
- Inform servers about relevant resource locations
- Enable working with multiple resource sets
- Provide workspace organization guidance

**Root Types**:
- **Filesystem Paths**: Local directory access (e.g., `file:///project/`)
- **HTTP URLs**: Remote API endpoints (e.g., `https://api.example.com/`)
- **Custom Schemes**: Application-specific resource locations

**Configuration Example**:
```json
{
  "roots": [
    {
      "uri": "file:///home/user/projects/frontend",
      "name": "Frontend Repository"
    },
    {
      "uri": "https://api.example.com/v1",
      "name": "API Endpoint"
    }
  ]
}
```

**Best Practices**:
- Respect provided root boundaries
- Prioritize operations within root scope
- Use clear, descriptive root names
- Monitor root accessibility and handle changes gracefully
- Suggest only necessary resources within roots

**Security Considerations**:
- Roots provide natural access control boundaries
- Prevent unauthorized file system or network access
- Scope server operations to defined resource locations
- Enable fine-grained permission management

---

## Examples and Implementation Patterns

### Reference Server Implementations

**1. Filesystem Server**
- **Purpose**: Secure file operations with configurable access controls
- **Features**: File reading, writing, directory listing, search
- **Security**: Path validation, access control, safe operations

**2. Fetch Server**
- **Purpose**: Web content fetching and conversion for LLM usage
- **Features**: URL fetching, content transformation, caching
- **Optimization**: Content extraction, format conversion

**3. Memory Server**
- **Purpose**: Knowledge graph-based persistent memory system
- **Features**: Structured data storage, relationship tracking, querying
- **Use Cases**: Long-term context, knowledge management

**4. Sequential Thinking Server**
- **Purpose**: Dynamic problem-solving through thought sequences
- **Features**: Step-by-step reasoning, workflow management
- **Applications**: Complex analysis, multi-step processes

### Integration Patterns

**Package Manager Installation**:
```bash
# TypeScript/Node.js
npm install @example/mcp-server

# Python
pip install example-mcp-server
```

**Client Configuration**:
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"]
    },
    "fetch": {
      "command": "python",
      "args": ["-m", "mcp_server_fetch"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

### Development Best Practices

**Server Design**:
- Implement comprehensive input validation
- Use clear, descriptive naming conventions
- Provide detailed error messages and status codes
- Support graceful degradation and error recovery
- Include proper logging and monitoring

**Security Considerations**:
- Validate all inputs and parameters
- Implement access controls and rate limiting
- Use secure transport mechanisms (TLS)
- Audit and log security-relevant operations
- Follow principle of least privilege

**Performance Optimization**:
- Implement efficient caching strategies
- Support pagination for large datasets
- Use async operations for I/O operations
- Optimize resource usage and memory management
- Monitor and profile server performance

---

## Security Framework

### Common Threat Vectors

**Input Validation**:
- Parameter injection attacks
- Path traversal vulnerabilities
- Command injection risks
- Data validation failures

**Access Control**:
- Unauthorized resource access
- Privilege escalation attempts
- Authentication bypass
- Session management issues

**Data Protection**:
- Information disclosure
- Credential exposure
- Data integrity violations
- Privacy violations

### Mitigation Strategies

**Secure Development**:
- Implement comprehensive input sanitization
- Use parameterized queries and commands
- Apply principle of least privilege
- Conduct regular security audits

**Runtime Protection**:
- Monitor for suspicious activities
- Implement rate limiting and quotas
- Use secure communication channels
- Maintain audit logs for security events

**Operational Security**:
- Keep dependencies updated
- Use secure deployment practices
- Implement backup and recovery procedures
- Conduct penetration testing

---

## Future Considerations

### Protocol Evolution
- Monitor MCP specification updates
- Plan for backward compatibility
- Implement feature flags for experimental capabilities
- Design extensible architecture patterns

### Ecosystem Growth
- Participate in community development
- Contribute to best practices documentation
- Share reusable server implementations
- Collaborate on security standards

### Technology Integration
- Support emerging transport mechanisms
- Adapt to new LLM capabilities
- Integrate with cloud-native architectures
- Enable multi-modal content support