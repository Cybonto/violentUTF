# MCP Resource Browser API Reference

## Overview

The MCP Resource Browser provides a comprehensive UI for browsing, searching, and managing MCP resources with preview capabilities and one-click actions.

## Classes

### ResourceBrowser

Main browser component for sidebar resource management.

```python
class ResourceBrowser:
    def __init__(self, mcp_client: MCPClientSync)
```

#### Methods

##### render_browser()
Render the complete resource browser UI in the sidebar.

**UI Components:**
- Search bar
- Category filters
- Refresh button
- Resource list with expandable items

**Example:**
```python
browser = ResourceBrowser(mcp_client)
with st.sidebar:
    browser.render_browser()
```

##### _refresh_resources()
Refresh the resource cache from MCP server.

**Side Effects:**
- Updates `_resource_cache`
- Updates `_last_refresh` timestamp
- Shows success/error message

##### _categorize_resource(resource) -> str
Categorize a resource based on its URI.

**Parameters:**
- `resource`: MCP resource object

**Returns:**
- str: Category name ('datasets', 'prompts', 'results', 'config', 'status', 'other')

##### _matches_search(resource, query: str) -> bool
Check if resource matches search query.

**Search Fields:**
- Resource name
- Resource URI
- Resource description

**Parameters:**
- `resource`: Resource object
- `query` (str): Search query

**Returns:**
- bool: True if matches

### ResourcePreview

Preview panel for displaying resource contents.

```python
class ResourcePreview:
    def __init__(self, mcp_client: MCPClientSync)
```

#### Methods

##### render_preview(resource_uri: str)
Render a preview of the resource.

**Parameters:**
- `resource_uri` (str): URI of resource to preview

**Supported Formats:**
- JSON objects (formatted display)
- Lists (paginated display)
- Text content (text area)
- Automatic JSON detection

**Example:**
```python
preview = ResourcePreview(mcp_client)
preview.render_preview("violentutf://datasets/jailbreak")
```

### ResourceActions

Handle resource-specific actions.

```python
class ResourceActions:
    def __init__(self, mcp_client: MCPClientSync)
```

#### Methods

##### load_dataset(dataset_uri: str) -> Tuple[bool, str]
Load a dataset into the current session.

**Parameters:**
- `dataset_uri` (str): Dataset resource URI

**Returns:**
- Tuple[bool, str]: (success, message)

**Session State Updates:**
```python
st.session_state['loaded_dataset'] = dataset_content
st.session_state['loaded_dataset_name'] = "dataset_name"
st.session_state['loaded_dataset_uri'] = dataset_uri
```

##### use_prompt(prompt_uri: str) -> Tuple[bool, str]
Load and prepare a prompt template for use.

**Parameters:**
- `prompt_uri` (str): Prompt resource URI

**Returns:**
- Tuple[bool, str]: (success, message)

**Session State Updates:**
```python
st.session_state['selected_prompt'] = prompt_content
st.session_state['selected_prompt_name'] = "prompt_name"
```

### IntegratedResourceBrowser

Combines all resource browser components.

```python
class IntegratedResourceBrowser:
    def __init__(self, mcp_client: MCPClientSync)
```

#### Methods

##### render_sidebar()
Render the complete resource browser in sidebar.

##### handle_actions()
Process any pending resource actions from UI interactions.

**Handled Actions:**
- Preview resource
- Load dataset
- Use prompt template

## Resource Categories

### Supported Categories

| Category | Icon | Description | Actions |
|----------|------|-------------|---------|
| datasets | 📁 | Security testing datasets | Load |
| prompts | 📝 | Prompt templates | Use |
| results | 📊 | Test results | Preview |
| config | ⚙️ | Configuration | Preview |
| status | 🔍 | System status | Preview |

### Category Detection

Resources are categorized by URI patterns:
- Contains "dataset" → datasets
- Contains "prompt" → prompts
- Contains "result" → results
- Contains "config" → config
- Contains "status" → status
- Others → other

## UI Components

### Search Bar
```python
search_query = st.sidebar.text_input(
    "Search resources",
    placeholder="Type to search...",
    key="resource_search"
)
```

### Category Filter
```python
selected_categories = st.sidebar.multiselect(
    "Filter by category",
    options=list(categories),
    default=list(categories)
)
```

### Resource Item Display
Each resource shows:
- Icon and name (expandable)
- URI (in caption)
- Description (if available)
- Action buttons (Preview, Load/Use)

## Usage Examples

### Basic Resource Browser
```python
from utils.mcp_resource_browser import IntegratedResourceBrowser

# Initialize
browser = IntegratedResourceBrowser(mcp_client)

# Render in sidebar
with st.sidebar:
    browser.render_sidebar()

# Handle actions in main area
browser.handle_actions()
```

### Custom Resource Actions
```python
from utils.mcp_resource_browser import ResourceActions

actions = ResourceActions(mcp_client)

# Load a dataset
success, message = actions.load_dataset("violentutf://datasets/bias_test")
if success:
    st.success(message)
    # Dataset now in st.session_state['loaded_dataset']
```

### Resource Preview
```python
from utils.mcp_resource_browser import ResourcePreview

preview = ResourcePreview(mcp_client)

# Show preview in main area
if st.button("Preview Dataset"):
    preview.render_preview("violentutf://datasets/security_test")
```

## Session State Integration

The resource browser integrates with Streamlit session state:

### Keys Used
- `preview_resource`: URI of resource to preview
- `load_dataset`: URI of dataset to load
- `use_prompt`: URI of prompt to use
- `loaded_dataset`: Loaded dataset content
- `loaded_dataset_name`: Name of loaded dataset
- `loaded_dataset_uri`: URI of loaded dataset
- `selected_prompt`: Selected prompt content
- `selected_prompt_name`: Name of selected prompt

### Context Manager Integration
When resources are loaded, they're automatically tracked in the context:
```python
# Automatic tracking when loading dataset
context.add_resource(dataset_uri)
```

## Styling

### Custom CSS Classes
The resource browser uses custom styling:
```css
.stExpander {
    background-color: white;
    border: 1px solid #e0e0e0;
    border-radius: 5px;
    margin-bottom: 5px;
}
```

## Error Handling

```python
try:
    browser.render_browser()
except Exception as e:
    logger.error(f"Resource browser error: {e}")
    st.error("Failed to load resource browser")
```

## Performance Considerations

1. **Caching**: Resources are cached until manual refresh
2. **Lazy Loading**: Resources loaded only when needed
3. **Pagination**: Large lists show first 5 items
4. **Search**: Client-side filtering for instant results

## Best Practices

1. **Refresh Periodically**: Use refresh button for latest resources
2. **Search First**: Use search to quickly find resources
3. **Preview Before Load**: Always preview unfamiliar resources
4. **Track Usage**: Loaded resources are tracked in context
5. **Error Recovery**: Handle action failures gracefully
