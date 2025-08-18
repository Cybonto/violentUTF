# MCP Architecture Overview

## System Architecture

The ViolentUTF MCP integration consists of multiple layers working together to provide intelligent prompt enhancement and security testing capabilities.

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client Applications                   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Claude      │  │  VS Code     │  │  Custom Apps     │  │
│  │ Desktop     │  │  Extensions  │  │  & Scripts       │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │ JSON-RPC over SSE
┌───────────────────────────┴─────────────────────────────────┐
│                      APISIX Gateway                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Rate        │  │ Authentication│  │  CORS & Routing │  │
│  │ Limiting    │  │ & OAuth Proxy │  │  Management     │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                ViolentUTF MCP Server (FastAPI)              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Tool        │  │ Resource     │  │ Prompt           │  │
│  │ Manager     │  │ Manager      │  │ Manager          │  │
│  └─────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                     ┌──────┴──────┐
                     │ ViolentUTF  │
                     │  Backend    │
                     │   APIs      │
                     └─────────────┘
```

## Component Details

### 1. MCP Client Applications

External applications that connect to the ViolentUTF MCP server:

#### Claude Desktop
- **Native Integration**: Built-in MCP support
- **Configuration**: Via mcpServers configuration file
- **Transport**: JSON-RPC over Server-Sent Events

#### VS Code Extensions
- **Developer Tools**: IDE integration for security testing
- **Custom Extensions**: Purpose-built security analysis tools
- **Live Testing**: Real-time vulnerability assessment

#### Custom Applications
- **Python Scripts**: Direct MCP client integration
- **Web Applications**: Browser-based security testing interfaces
- **API Integration**: RESTful access to MCP capabilities

### 2. MCP Integration Layer

This layer provides the business logic for MCP operations:

#### Natural Language Parser
```python
class NaturalLanguageParser:
    """Parse natural language commands for MCP operations"""
```
- Detects MCP commands in user input
- Supports commands: help, test, dataset, enhance, analyze, resources, prompt
- Provides command suggestions and autocomplete

#### Context Analyzer
```python
class ContextAnalyzer:
    """Analyze conversation context for MCP opportunities"""
```
- Identifies enhancement opportunities
- Detects security and bias concerns
- Classifies prompt types (jailbreak, roleplay, question, instruction)

#### Resource Searcher
```python
class ResourceSearcher:
    """Search and filter MCP resources"""
```
- Searches prompts and resources
- Filters by type and category
- Caches results for performance

#### Test Scenario Interpreter
```python
class TestScenarioInterpreter:
    """Interpret and execute test scenarios using MCP"""
```
- Maps test requests to MCP prompts
- Generates default parameters
- Prepares test configurations

### 3. MCP Client Layer

The core communication layer handling MCP protocol:

#### SSE Client
- Implements Server-Sent Events for real-time communication
- Handles connection management and reconnection
- Parses SSE formatted responses

#### JSON-RPC Handler
- Implements JSON-RPC 2.0 protocol
- Manages request/response correlation
- Handles error responses

#### Authentication Integration
- Reuses existing JWT manager
- Automatic token refresh
- APISIX gateway headers

### 4. Infrastructure Layer

#### APISIX Gateway
- Routes `/mcp/*` endpoints
- Handles authentication
- Rate limiting and security

#### MCP Server (FastAPI)
- Implements MCP protocol endpoints
- Manages prompts and resources
- Handles tool execution

## Data Flow

### MCP Protocol Flow

```
1. Client sends JSON-RPC initialize request via SSE
2. Server responds with capabilities and server info
3. Client lists available tools, prompts, and resources
4. Client executes tools with arguments
5. Server returns structured results
6. Client processes and displays results
```

### Tool Execution Flow

```
1. Client calls tool via JSON-RPC (tools/call)
2. Server validates arguments against tool schema
3. Server executes tool with authentication
4. Server makes API calls to ViolentUTF backend
5. Server formats and returns results
6. Client receives structured response
```

### Resource Access Flow

```
1. Client requests resource list (resources/list)
2. Server discovers available resources
3. Client reads specific resource (resources/read)
4. Server retrieves data with caching
5. Server returns formatted resource content
6. Client processes resource data
```

## State Management

### Session State Variables

```python
# MCP Client instances
st.session_state['mcp_client'] = MCPClientSync()
st.session_state['mcp_parser'] = NaturalLanguageParser()
st.session_state['mcp_analyzer'] = ContextAnalyzer()

# Results storage
st.session_state['mcp_enhanced_prompt'] = None
st.session_state['mcp_analysis_results'] = None
st.session_state['mcp_test_variations'] = []

# UI state
st.session_state['show_mcp_results'] = False
st.session_state['mcp_operation_in_progress'] = False
```

### State Persistence
- Results persist during session
- Clear button resets all MCP state
- Compatible with existing prompt variables

## Security Architecture

### Authentication Flow
1. User authenticates via Keycloak
2. JWT token stored in session state
3. MCP client uses jwt_manager for token refresh
4. All requests include Bearer token

### Network Security
- All traffic through APISIX gateway
- HTTPS encryption for external connections
- Internal Docker network for services
- No direct access to backend services

### Error Handling
- Graceful degradation on failures
- User-friendly error messages
- Automatic retry with backoff
- Comprehensive logging

## Performance Considerations

### Caching Strategy
- Resource and prompt lists cached
- Cache invalidation on updates
- Memory-efficient storage

### Async Operations
- Non-blocking UI updates
- Loading states during operations
- Concurrent request handling

### Optimization
- Lazy loading of resources
- Debounced command parsing
- Efficient state updates

## Extensibility

### Adding New Operations
1. Add prompt type to MCP server
2. Update command parser patterns
3. Add UI button/handler
4. Create test coverage

### Integration Points
- Works with existing prompt variables
- Compatible with all LLM providers
- Maintains chat history
- No breaking changes

## Future Architecture (Phases 3-5)

### Phase 3: Command System
- Command execution engine
- History and autocomplete
- Natural language refinement

### Phase 4: Resource Browser
- Sidebar resource explorer
- Real-time monitoring
- Context management

### Phase 5: Visual Builders
- Drag-drop prompt builder
- Test scenario designer
- Collaboration features
