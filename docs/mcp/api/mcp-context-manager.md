# MCP Context Manager API Reference

## Overview

The MCP Context Manager provides intelligent conversation tracking, security pattern detection, and context-aware suggestions for the Simple Chat interface.

## Classes

### ConversationContext

Manages conversation history and context for a session.

```python
class ConversationContext:
    def __init__(self, max_turns: int = 100)
```

#### Methods

##### add_turn(role: str, content: str, metadata: Optional[Dict] = None)
Add a conversation turn to the history.

**Parameters:**
- `role` (str): Speaker role ('user', 'assistant', 'system')
- `content` (str): Message content
- `metadata` (Optional[Dict]): Additional metadata

**Example:**
```python
context = ConversationContext()
context.add_turn("user", "Test for jailbreak", {"timestamp": datetime.now()})
```

##### extract_topics() -> List[str]
Extract topics from conversation history.

**Returns:**
- List[str]: Detected topics

**Example:**
```python
topics = context.extract_topics()
# Returns: ["jailbreak", "security", "testing"]
```

##### add_resource(resource_uri: str)
Track an active resource.

**Parameters:**
- `resource_uri` (str): Resource URI to track

##### add_test_result(test_type: str, result: Dict[str, Any])
Store a test result.

**Parameters:**
- `test_type` (str): Type of test performed
- `result` (Dict): Test result data

##### get_context_summary() -> Dict[str, Any]
Generate a summary of the current context.

**Returns:**
```python
{
    "turn_count": 10,
    "active_resources": 2,
    "test_results": 3,
    "duration": 300.5,  # seconds
    "last_activity": "2024-01-20T10:30:00",
    "topics": ["security", "jailbreak"]
}
```

### ContextAwareMonitor

Monitors conversations for patterns and provides insights.

```python
class ContextAwareMonitor:
    def __init__(self)
```

#### Methods

##### analyze_conversation(session_id: str, user_input: str) -> Dict[str, Any]
Analyze user input and generate insights.

**Parameters:**
- `session_id` (str): Session identifier
- `user_input` (str): User's message

**Returns:**
```python
{
    "topics": ["jailbreak", "security"],
    "suggestions": [
        {
            "text": "Try the jailbreak dataset",
            "command": "/mcp load dataset:jailbreak",
            "reason": "You mentioned testing for jailbreak"
        }
    ],
    "alerts": [
        {
            "level": "warning",
            "concern": "jailbreak",
            "message": "Potential jailbreak attempt detected",
            "patterns": ["ignore", "bypass"]
        }
    ],
    "context_summary": {...}
}
```

##### register_callback(event_type: str, callback: Callable)
Register a callback for specific events.

**Parameters:**
- `event_type` (str): Event type ('alert', 'suggestion', 'topic')
- `callback` (Callable): Function to call

**Example:**
```python
def on_alert(alert_data):
    print(f"Security alert: {alert_data['message']}")

monitor.register_callback("alert", on_alert)
```

##### get_session_stats(session_id: str) -> Dict[str, Any]
Get statistics for a session.

**Returns:**
```python
{
    "summary": {
        "turn_count": 15,
        "active_resources": 3,
        "test_results": 5,
        "duration": 600
    },
    "topics": ["security", "bias", "jailbreak"],
    "alerts_raised": 2
}
```

### ResourceMonitor

Monitors resource changes asynchronously.

```python
class ResourceMonitor:
    def __init__(self, mcp_client)
```

#### Methods

##### async start_monitoring(interval: float = 5.0)
Start monitoring resources.

**Parameters:**
- `interval` (float): Check interval in seconds

##### async stop_monitoring()
Stop resource monitoring.

##### subscribe(resource_uri: str, callback: Callable)
Subscribe to resource changes.

**Parameters:**
- `resource_uri` (str): Resource to monitor
- `callback` (Callable): Async function to call on changes

### IntegratedContextManager

Combines all context management features.

```python
class IntegratedContextManager:
    def __init__(self, mcp_client)
```

#### Methods

##### process_input(session_id: str, user_input: str) -> Dict[str, Any]
Process user input and return comprehensive insights.

**Returns:**
Combined insights from context analysis, including:
- Topics detected
- Suggestions generated
- Security alerts
- Active resources
- Recent test results

##### track_command_execution(session_id: str, command: str, result: Any)
Track MCP command execution in context.

**Parameters:**
- `session_id` (str): Session identifier
- `command` (str): Command executed
- `result` (Any): Command result

##### get_contextual_help(session_id: str) -> List[Dict[str, str]]
Get contextual help items based on conversation.

**Returns:**
```python
[
    {
        "title": "Testing for Jailbreak",
        "content": "Use the jailbreak scorer to detect...",
        "link": "/docs/jailbreak-testing"
    }
]
```

## Security Patterns

The context manager detects these security patterns:

### Jailbreak Patterns
- "ignore previous instructions"
- "bypass", "override", "forget"
- Role-playing attempts
- System prompt manipulation

### Injection Patterns
- "system:", "assistant:"
- Command injection attempts
- Prompt concatenation

### Data Leak Patterns
- "password", "secret", "key"
- Personal information requests
- System information queries

## Usage Examples

### Basic Context Tracking
```python
from utils.mcp_context_manager import IntegratedContextManager

# Initialize
manager = IntegratedContextManager(mcp_client)

# Process input
insights = manager.process_input("session123", "How to test for jailbreak?")

# Check for alerts
if insights['alerts']:
    for alert in insights['alerts']:
        print(f"⚠️ {alert['message']}")

# Use suggestions
for suggestion in insights['suggestions']:
    print(f"💡 {suggestion['text']}")
```

### Real-time Monitoring
```python
monitor = ContextAwareMonitor()

# Register alert handler
def handle_security_alert(alert):
    if alert['concern'] == 'jailbreak':
        log_security_event(alert)

monitor.register_callback("alert", handle_security_alert)

# Analyze conversation
insights = monitor.analyze_conversation("session123", user_input)
```

### Session Analytics
```python
# Get session statistics
stats = manager.monitor.get_session_stats("session123")

print(f"Messages: {stats['summary']['turn_count']}")
print(f"Duration: {stats['summary']['duration']/60:.1f} minutes")
print(f"Topics: {', '.join(stats['topics'])}")
```

## Best Practices

1. **Session Management**: Use unique session IDs for each conversation
2. **Alert Handling**: Always check for security alerts before processing
3. **Resource Tracking**: Track resource usage for better context
4. **Topic Analysis**: Use extracted topics for relevant suggestions
5. **Performance**: Keep max_turns reasonable (default: 100)

## Error Handling

```python
try:
    insights = manager.process_input(session_id, user_input)
except Exception as e:
    logger.error(f"Context analysis failed: {e}")
    # Fallback to basic processing
    insights = {"topics": [], "suggestions": [], "alerts": []}
```