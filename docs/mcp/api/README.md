# MCP API Reference Documentation

Comprehensive API documentation for ViolentUTF's Model Context Protocol (MCP) integration, covering client libraries, integration utilities, and specialized components.

## 📚 API Documentation Index

### 🔌 **Core Client APIs**
- **[MCP Client](mcp-client.md)** - Primary MCP client classes (async/sync) for server communication
- **[MCP Integration](mcp-integration.md)** - Natural language parsing and command processing utilities

### 🧠 **Context & Intelligence**
- **[MCP Context Manager](mcp-context-manager.md)** - Conversation tracking and context-aware suggestions
- **[MCP Resource Browser](mcp-resource-browser.md)** - UI components for resource management and browsing

### 🔍 **Security & Evaluation**
- **[MCP Scorer Integration](mcp-scorer-integration.md)** - Real-time vulnerability assessment using PyRIT scorers

## 🚀 Quick Start

### Basic MCP Client Usage
```python
from utils.mcp_client import MCPClientSync

# Initialize client
client = MCPClientSync()
client.initialize()

# List available tools
tools = client.list_tools()

# Execute tool
result = client.execute_tool("create_generator", {
    "provider_type": "openai",
    "model_name": "gpt-4"
})
```

### Natural Language Processing
```python
from utils.mcp_integration import NaturalLanguageParser

parser = NaturalLanguageParser()
command = parser.parse("run bias test on gpt-4")
# Returns parsed MCPCommand with test configuration
```

### Resource Management
```python
from utils.mcp_resource_browser import ResourceBrowser

browser = ResourceBrowser(mcp_client)
browser.render_browser()  # Displays interactive resource UI
```

## 🏗️ API Architecture

### Client Layer
```
┌─────────────────┐
│   MCPClient     │ ← Async MCP communication
│   MCPClientSync │ ← Sync wrapper for Streamlit
└─────────────────┘
```

### Integration Layer
```
┌─────────────────┐
│ NaturalLanguage │ ← Command parsing & NLP
│ ContextManager  │ ← Conversation tracking
│ ResourceBrowser │ ← UI resource management
└─────────────────┘
```

### Security Layer
```
┌─────────────────┐
│ ScorerIntegration│ ← PyRIT scorer analysis
│ SecurityAnalysis │ ← Real-time vulnerability assessment
└─────────────────┘
```

## 📖 API Categories

### 🔌 **Client APIs**
| Component | Purpose | Use Case |
|-----------|---------|----------|
| **MCPClient** | Async MCP communication | Server applications, async contexts |
| **MCPClientSync** | Sync MCP wrapper | Streamlit apps, simple scripts |

### 🛠️ **Integration APIs**
| Component | Purpose | Use Case |
|-----------|---------|----------|
| **NaturalLanguageParser** | Command parsing | Natural language interfaces |
| **ConversationContext** | Context tracking | Chat applications |
| **ResourceBrowser** | Resource UI | Interactive resource management |

### 🔍 **Security APIs**
| Component | Purpose | Use Case |
|-----------|---------|----------|
| **ScorerIntegration** | Vulnerability scoring | Real-time security analysis |
| **SecurityAnalysis** | Threat detection | Automated security assessment |

## 🎯 Common Use Cases

### Interactive Chat Application
```python
# Setup components
client = MCPClientSync()
parser = NaturalLanguageParser()
context = ConversationContext()

# Process user input
command = parser.parse(user_input)
result = client.execute_tool(command.type, command.arguments)
context.add_turn("user", user_input)
context.add_turn("assistant", result)
```

### Security Assessment Workflow
```python
# Setup security analysis
client = MCPClientSync()
scorer = ScorerIntegration(client)

# Analyze content
results = scorer.score_content(content, ["bias", "toxicity", "jailbreak"])
security_report = scorer.generate_report(results)
```

### Resource Management Interface
```python
# Setup resource browser
client = MCPClientSync()
browser = ResourceBrowser(client)

# Display interactive browser
with st.sidebar:
    browser.render_browser()
    selected_resource = browser.get_selected()
```

## 🔧 Configuration

### Environment Variables
```bash
# MCP Client Configuration
VIOLENTUTF_API_URL=http://localhost:9080
MCP_TIMEOUT=30
MCP_MAX_RETRIES=3

# Integration Features
MCP_ENABLE_NLP=true
MCP_ENABLE_CONTEXT=true
MCP_ENABLE_SCORING=true

# Security Configuration
MCP_SCORER_TIMEOUT=60
MCP_SECURITY_LEVEL=standard
```

### Client Configuration
```python
# Custom client configuration
client = MCPClientSync(
    base_url="http://localhost:9080",
    timeout=30.0,
    max_retries=3,
    enable_caching=True
)
```

## 🎭 Usage Patterns

### Async Pattern (Server Applications)
```python
import asyncio
from utils.mcp_client import MCPClient

async def main():
    client = MCPClient()
    await client.initialize()

    tools = await client.list_tools()
    result = await client.execute_tool("test_generator", {"generator_id": "gpt-4"})

asyncio.run(main())
```

### Sync Pattern (Streamlit Applications)
```python
import streamlit as st
from utils.mcp_client import MCPClientSync

@st.cache_resource
def get_mcp_client():
    client = MCPClientSync()
    client.initialize()
    return client

client = get_mcp_client()
tools = client.list_tools()
```

### Error Handling Pattern
```python
from utils.mcp_client import MCPClientError, MCPConnectionError

try:
    result = client.execute_tool("create_generator", params)
except MCPConnectionError:
    st.error("MCP server connection failed")
except MCPClientError as e:
    st.error(f"MCP operation failed: {e}")
```

## 🔍 API Reference Quick Links

### Core Methods
- **`initialize()`** - Initialize MCP connection ([mcp-client.md](mcp-client.md#initialize))
- **`list_tools()`** - List available tools ([mcp-client.md](mcp-client.md#list-tools))
- **`execute_tool()`** - Execute MCP tool ([mcp-client.md](mcp-client.md#execute-tool))
- **`list_resources()`** - List MCP resources ([mcp-client.md](mcp-client.md#list-resources))

### Integration Methods
- **`parse()`** - Parse natural language ([mcp-integration.md](mcp-integration.md#parse))
- **`add_turn()`** - Add conversation turn ([mcp-context-manager.md](mcp-context-manager.md#add-turn))
- **`render_browser()`** - Display resource browser ([mcp-resource-browser.md](mcp-resource-browser.md#render-browser))

### Security Methods
- **`score_content()`** - Score content for security ([mcp-scorer-integration.md](mcp-scorer-integration.md#score-content))
- **`generate_report()`** - Generate security report ([mcp-scorer-integration.md](mcp-scorer-integration.md#generate-report))

## 🔗 Related Documentation

- **[../README.md](../README.md)** - MCP overview and architecture
- **[../configuration.md](../configuration.md)** - MCP server configuration
- **[../development.md](../development.md)** - MCP development guide
- **[../../api/README.md](../../api/README.md)** - Core API documentation

---

**📡 Protocol Notice**: These APIs implement the Model Context Protocol (MCP) specification for standardized AI tool communication.
