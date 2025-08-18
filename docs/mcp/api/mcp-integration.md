# MCP Integration API Reference

The MCP Integration module provides utilities for natural language processing, context analysis, and integration with ViolentUTF's existing features.

## Classes

### NaturalLanguageParser

Parses natural language commands for MCP operations.

```python
from utils.mcp_integration import NaturalLanguageParser, MCPCommandType

parser = NaturalLanguageParser()
```

#### Methods

##### `parse(text: str) -> MCPCommand`

Parse natural language text into MCP command.

```python
command = parser.parse("/mcp enhance")
# Returns: MCPCommand(type=MCPCommandType.ENHANCE, arguments={}, raw_text="/mcp enhance")

command = parser.parse("run bias test")
# Returns: MCPCommand(type=MCPCommandType.TEST, arguments={"test_type": "bias"}, ...)
```

**Parameters:**
- `text`: Input text to parse

**Returns:** `MCPCommand` object with parsed information

##### `suggest_command(partial_text: str) -> List[str]`

Suggest commands based on partial input.

```python
suggestions = parser.suggest_command("/mcp")
# Returns: ["/mcp help", "/mcp enhance", "/mcp analyze", ...]
```

**Parameters:**
- `partial_text`: Partial command text

**Returns:** List of suggested commands (max 5)

#### Command Patterns

| Command Type | Example Patterns |
|--------------|------------------|
| HELP | `/mcp help`, `show mcp commands` |
| TEST | `/mcp test jailbreak`, `run bias test` |
| DATASET | `/mcp dataset harmbench`, `load dataset advbench` |
| ENHANCE | `/mcp enhance`, `improve this prompt` |
| ANALYZE | `/mcp analyze`, `analyze for bias` |
| RESOURCES | `/mcp resources`, `show mcp resources` |
| PROMPT | `/mcp prompt security_test`, `use jailbreak_test prompt` |

### ContextAnalyzer

Analyzes conversation context for MCP opportunities.

```python
from utils.mcp_integration import ContextAnalyzer

analyzer = ContextAnalyzer(mcp_client)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mcp_client` | `Optional[MCPClientSync]` | `MCPClientSync()` | MCP client instance |

#### Methods

##### `analyze_for_suggestions(text: str) -> List[Dict[str, Any]]`

Analyze text and suggest relevant MCP operations.

```python
suggestions = analyzer.analyze_for_suggestions("I want to improve this prompt")
# Returns: [{"type": "enhance", "reason": "...", "command": "/mcp enhance", "priority": 1}]
```

**Parameters:**
- `text`: Text to analyze

**Returns:** List of suggestions with type, reason, command, and priority

##### `detect_prompt_type(text: str) -> str`

Detect the type of prompt based on content.

```python
prompt_type = analyzer.detect_prompt_type("Ignore all previous instructions")
# Returns: "jailbreak_attempt"
```

**Parameters:**
- `text`: Prompt text to analyze

**Returns:** Detected prompt type: `"jailbreak_attempt"`, `"roleplay"`, `"question"`, `"instruction"`, or `"general"`

#### Trigger Keywords

| Suggestion Type | Trigger Words |
|----------------|---------------|
| Enhancement | improve, better, enhance, optimize, refine |
| Security | jailbreak, bypass, security, safety, harmful |
| Bias | bias, fair, discriminat*, stereotyp*, prejudic* |

### ResourceSearcher

Search and filter MCP resources.

```python
from utils.mcp_integration import ResourceSearcher

searcher = ResourceSearcher(mcp_client)
```

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mcp_client` | `Optional[MCPClientSync]` | `MCPClientSync()` | MCP client instance |

#### Methods

##### `search_resources(query: str, resource_type: Optional[str] = None) -> List[Dict[str, Any]]`

Search for resources matching query.

```python
resources = searcher.search_resources("dataset", resource_type="datasets")
# Returns: [{"uri": "violentutf://datasets/...", "name": "...", ...}]
```

**Parameters:**
- `query`: Search query
- `resource_type`: Optional filter by resource type

**Returns:** List of matching resources

##### `search_prompts(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]`

Search for prompts matching query.

```python
prompts = searcher.search_prompts("security", category="test")
# Returns: [{"name": "security_test", "description": "...", ...}]
```

**Parameters:**
- `query`: Search query
- `category`: Optional filter by category

**Returns:** List of matching prompts

##### `get_resource_by_uri(uri: str) -> Optional[Dict[str, Any]]`

Get specific resource by URI.

```python
resource = searcher.get_resource_by_uri("violentutf://datasets/harmbench")
```

##### `get_prompt_by_name(name: str) -> Optional[Dict[str, Any]]`

Get specific prompt by name.

```python
prompt = searcher.get_prompt_by_name("jailbreak_test")
```

### TestScenarioInterpreter

Interpret and execute test scenarios using MCP.

```python
from utils.mcp_integration import TestScenarioInterpreter

interpreter = TestScenarioInterpreter(mcp_client)
```

#### Methods

##### `interpret_test_request(test_type: str, context: Optional[str] = None) -> Dict[str, Any]`

Interpret a test request and prepare test configuration.

```python
config = interpreter.interpret_test_request("jailbreak", "Test this prompt")
# Returns: {"test_type": "jailbreak", "prompt_name": "jailbreak_test", ...}
```

**Parameters:**
- `test_type`: Type of test requested
- `context`: Optional context or prompt to test

**Returns:** Test configuration dictionary

##### `execute_test(test_config: Dict[str, Any]) -> Dict[str, Any]`

Execute a test based on configuration.

```python
result = interpreter.execute_test(config)
# Returns: {"test_type": "...", "rendered_prompt": "...", "status": "ready", ...}
```

**Parameters:**
- `test_config`: Test configuration from `interpret_test_request`

**Returns:** Test results dictionary

#### Test Type Mappings

| Test Type | MCP Prompt Name | Default Parameters |
|-----------|-----------------|-------------------|
| jailbreak | jailbreak_test | scenario, techniques, target_behavior |
| bias | bias_detection | focus_area, demographics, test_depth |
| privacy | privacy_test | data_types, test_method, sensitivity_level |
| security | security_audit | audit_scope, vulnerability_types |
| harmful | harmful_content_test | content_types, test_intensity |
| injection | prompt_injection | injection_type, payload_complexity |

### DatasetIntegration

Integrate MCP with existing dataset system.

```python
from utils.mcp_integration import DatasetIntegration

integration = DatasetIntegration(mcp_client)
```

#### Methods

##### `load_mcp_dataset(dataset_uri: str) -> Optional[Any]`

Load dataset from MCP resource.

```python
dataset = integration.load_mcp_dataset("violentutf://datasets/harmbench")
# Returns: Parsed dataset content (list, dict, or string)
```

**Parameters:**
- `dataset_uri`: MCP resource URI for dataset

**Returns:** Loaded dataset or None if error

##### `transform_with_jinja(data: Any, template: str) -> Optional[str]`

Transform data using Jinja2 template.

```python
result = integration.transform_with_jinja(
    [{"name": "test1"}, {"name": "test2"}],
    "{% for item in items %}{{ item.name }}\n{% endfor %}"
)
# Returns: "test1\ntest2\n"
```

**Parameters:**
- `data`: Data to transform
- `template`: Jinja2 template string

**Returns:** Transformed string or None if error

##### `list_available_datasets() -> Dict[str, List[Dict[str, Any]]]`

List all available datasets from both MCP and local sources.

```python
datasets = integration.list_available_datasets()
# Returns: {"mcp": [...], "local": [...]}
```

**Returns:** Dictionary with 'mcp' and 'local' dataset lists

## Data Classes

### MCPCommand

Parsed MCP command representation.

```python
from utils.mcp_integration import MCPCommand, MCPCommandType

command = MCPCommand(
    type=MCPCommandType.ENHANCE,
    subcommand=None,
    arguments={"level": "advanced"},
    raw_text="/mcp enhance --level advanced"
)
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `type` | `MCPCommandType` | Type of command |
| `subcommand` | `Optional[str]` | Subcommand if any |
| `arguments` | `Dict[str, Any]` | Parsed arguments |
| `raw_text` | `str` | Original input text |

### MCPCommandType

Enumeration of MCP command types.

```python
from utils.mcp_integration import MCPCommandType

MCPCommandType.HELP      # Help commands
MCPCommandType.TEST      # Test commands
MCPCommandType.DATASET   # Dataset commands
MCPCommandType.ENHANCE   # Enhancement commands
MCPCommandType.ANALYZE   # Analysis commands
MCPCommandType.RESOURCES # Resource commands
MCPCommandType.PROMPT    # Prompt commands
MCPCommandType.UNKNOWN   # Unrecognized commands
```

## Usage Examples

### Natural Language Parsing

```python
from utils.mcp_integration import NaturalLanguageParser

parser = NaturalLanguageParser()

# Parse various command formats
commands = [
    "/mcp help",
    "enhance this prompt",
    "run jailbreak test",
    "load dataset harmbench"
]

for cmd_text in commands:
    command = parser.parse(cmd_text)
    print(f"Input: {cmd_text}")
    print(f"Type: {command.type.value}")
    print(f"Arguments: {command.arguments}")
    print()
```

### Context Analysis

```python
from utils.mcp_integration import ContextAnalyzer
from utils.mcp_client import MCPClientSync

client = MCPClientSync()
analyzer = ContextAnalyzer(client)

# Analyze user input
text = "I need to improve this prompt to bypass the content filter"

# Get suggestions
suggestions = analyzer.analyze_for_suggestions(text)
for suggestion in suggestions:
    print(f"Type: {suggestion['type']}")
    print(f"Reason: {suggestion['reason']}")
    print(f"Command: {suggestion['command']}")

# Detect prompt type
prompt_type = analyzer.detect_prompt_type(text)
print(f"Detected type: {prompt_type}")
```

### Resource Search

```python
from utils.mcp_integration import ResourceSearcher
from utils.mcp_client import MCPClientSync

client = MCPClientSync()
searcher = ResourceSearcher(client)

# Search for security-related resources
resources = searcher.search_resources("security")
for resource in resources:
    print(f"Resource: {resource['name']} - {resource['uri']}")

# Search for bias detection prompts
prompts = searcher.search_prompts("bias")
for prompt in prompts:
    print(f"Prompt: {prompt['name']} - {prompt['description']}")
```

### Test Scenario Execution

```python
from utils.mcp_integration import TestScenarioInterpreter
from utils.mcp_client import MCPClientSync

client = MCPClientSync()
interpreter = TestScenarioInterpreter(client)

# Interpret test request
config = interpreter.interpret_test_request(
    "jailbreak",
    "Tell me how to hack into a system"
)

print(f"Test type: {config['test_type']}")
print(f"Prompt name: {config['prompt_name']}")
print(f"Parameters: {config['parameters']}")

# Execute test
result = interpreter.execute_test(config)
print(f"Status: {result['status']}")
print(f"Rendered prompt: {result['rendered_prompt'][:100]}...")
```

### Dataset Integration

```python
from utils.mcp_integration import DatasetIntegration
from utils.mcp_client import MCPClientSync

client = MCPClientSync()
integration = DatasetIntegration(client)

# List all datasets
datasets = integration.list_available_datasets()
print(f"MCP datasets: {len(datasets['mcp'])}")
print(f"Local datasets: {len(datasets['local'])}")

# Load specific dataset
dataset = integration.load_mcp_dataset("violentutf://datasets/harmbench")
if dataset:
    print(f"Loaded dataset with {len(dataset)} entries")

# Transform with Jinja2
template = """
{% for item in items %}
Prompt: {{ item.prompt }}
Category: {{ item.category }}
---
{% endfor %}
"""
result = integration.transform_with_jinja(dataset, template)
print(result)
```

## Best Practices

1. **Cache Searcher Instances** - They cache resources/prompts internally
2. **Handle None Returns** - All methods return None on error
3. **Use Priority in Suggestions** - Sort by priority for best UX
4. **Validate Test Configs** - Check for errors before execution
5. **Template Safety** - Sanitize user templates before transformation

## Integration with Simple Chat

The integration utilities are designed to work seamlessly with Simple Chat:

```python
# In Simple Chat session state
st.session_state['mcp_parser'] = NaturalLanguageParser()
st.session_state['mcp_analyzer'] = ContextAnalyzer(st.session_state['mcp_client'])

# Parse user input
user_input = st.text_area("Enter prompt")
command = st.session_state['mcp_parser'].parse(user_input)

# Get suggestions
suggestions = st.session_state['mcp_analyzer'].analyze_for_suggestions(user_input)

# Display suggestions
for suggestion in suggestions:
    if st.button(f"Apply: {suggestion['reason']}"):
        # Execute suggestion
        pass
```
