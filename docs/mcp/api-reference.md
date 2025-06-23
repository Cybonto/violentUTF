# ViolentUTF MCP API Reference

## Overview

This document provides comprehensive API reference for the ViolentUTF Model Context Protocol (MCP) server, including all tools, resources, and their parameters.

## Tool Reference

### Generator Management Tools

#### `list_generators`
List and filter generator configurations.

**Parameters:**
```json
{
  "provider_type": {
    "type": "string",
    "enum": ["openai", "anthropic", "ollama", "open_webui", "azure_openai"],
    "description": "Filter by provider type",
    "required": false
  },
  "status": {
    "type": "string",
    "enum": ["active", "inactive", "error"],
    "description": "Filter by generator status",
    "required": false
  },
  "include_test_results": {
    "type": "boolean", 
    "description": "Include latest test results",
    "default": false,
    "required": false
  }
}
```

**Response:**
```json
{
  "generators": [
    {
      "id": "gen_001",
      "name": "GPT-4 Production",
      "provider_type": "openai",
      "model_name": "gpt-4",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "last_tested": "2024-01-15T12:00:00Z",
      "test_result": {
        "status": "success",
        "response_time_ms": 1250,
        "token_count": 50
      }
    }
  ],
  "total": 1,
  "filtered": 1
}
```

#### `get_generator`
Retrieve detailed information about a specific generator.

**Parameters:**
```json
{
  "generator_id": {
    "type": "string",
    "description": "Unique identifier of the generator",
    "required": true
  },
  "include_test_history": {
    "type": "boolean",
    "description": "Include test execution history", 
    "default": false,
    "required": false
  }
}
```

**Response:**
```json
{
  "id": "gen_001",
  "name": "GPT-4 Production",
  "provider_type": "openai",
  "model_name": "gpt-4",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 0.9
  },
  "system_prompt": "You are a helpful assistant.",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z",
  "test_history": [
    {
      "timestamp": "2024-01-15T12:00:00Z",
      "status": "success",
      "response_time_ms": 1250,
      "test_prompt": "Hello, how are you?",
      "response": "I'm doing well, thank you!"
    }
  ]
}
```

#### `create_generator`
Create a new generator configuration.

**Parameters:**
```json
{
  "name": {
    "type": "string",
    "description": "Human-readable name for the generator",
    "required": true
  },
  "provider_type": {
    "type": "string",
    "enum": ["openai", "anthropic", "ollama", "open_webui", "azure_openai"],
    "description": "AI provider type",
    "required": true
  },
  "model_name": {
    "type": "string",
    "description": "Model name (e.g., gpt-4, claude-3-sonnet)",
    "required": true
  },
  "parameters": {
    "type": "object",
    "description": "Model parameters",
    "properties": {
      "temperature": {"type": "number", "minimum": 0, "maximum": 2},
      "max_tokens": {"type": "integer", "minimum": 1},
      "top_p": {"type": "number", "minimum": 0, "maximum": 1},
      "frequency_penalty": {"type": "number", "minimum": -2, "maximum": 2},
      "presence_penalty": {"type": "number", "minimum": -2, "maximum": 2}
    },
    "required": false
  },
  "system_prompt": {
    "type": "string",
    "description": "Optional system prompt for the generator",
    "required": false
  },
  "enabled": {
    "type": "boolean",
    "description": "Whether the generator is enabled",
    "default": true,
    "required": false
  },
  "test_after_creation": {
    "type": "boolean",
    "description": "Test the generator after creation",
    "default": true,
    "required": false
  }
}
```

**Response:**
```json
{
  "id": "gen_002",
  "name": "New Generator",
  "provider_type": "openai",
  "model_name": "gpt-4",
  "status": "active",
  "created_at": "2024-01-15T14:30:00Z",
  "test_result": {
    "status": "success",
    "response_time_ms": 1100,
    "message": "Generator created and tested successfully"
  }
}
```

#### `update_generator`
Update an existing generator configuration.

**Parameters:**
```json
{
  "generator_id": {
    "type": "string",
    "description": "Unique identifier of the generator to update",
    "required": true
  },
  "name": {
    "type": "string",
    "description": "Updated name for the generator",
    "required": false
  },
  "parameters": {
    "type": "object",
    "description": "Updated model parameters",
    "required": false
  },
  "system_prompt": {
    "type": "string",
    "description": "Updated system prompt",
    "required": false
  },
  "enabled": {
    "type": "boolean",
    "description": "Enable/disable the generator",
    "required": false
  },
  "test_after_update": {
    "type": "boolean",
    "description": "Test the generator after update",
    "default": true,
    "required": false
  }
}
```

#### `delete_generator`
Delete a generator configuration.

**Parameters:**
```json
{
  "generator_id": {
    "type": "string",
    "description": "Unique identifier of the generator to delete",
    "required": true
  },
  "force": {
    "type": "boolean",
    "description": "Force deletion even if generator is in use",
    "default": false,
    "required": false
  }
}
```

#### `test_generator`
Test a generator with a sample prompt.

**Parameters:**
```json
{
  "generator_id": {
    "type": "string",
    "description": "Unique identifier of the generator to test",
    "required": true
  },
  "test_prompt": {
    "type": "string",
    "description": "Test prompt to send to the generator",
    "default": "Hello, please respond with a brief greeting.",
    "required": false
  },
  "timeout_seconds": {
    "type": "integer",
    "description": "Test timeout in seconds",
    "default": 30,
    "minimum": 5,
    "maximum": 120,
    "required": false
  }
}
```

**Response:**
```json
{
  "test_id": "test_001",
  "generator_id": "gen_001",
  "status": "success",
  "test_prompt": "Hello, please respond with a brief greeting.",
  "response": "Hello! I'm doing well and ready to help you today.",
  "response_time_ms": 1150,
  "token_count": 12,
  "timestamp": "2024-01-15T15:30:00Z"
}
```

#### `clone_generator`
Clone an existing generator with modifications.

**Parameters:**
```json
{
  "source_generator_id": {
    "type": "string",
    "description": "ID of the generator to clone",
    "required": true
  },
  "new_name": {
    "type": "string",
    "description": "Name for the cloned generator",
    "required": true
  },
  "parameter_overrides": {
    "type": "object",
    "description": "Parameters to override in the clone",
    "required": false
  },
  "model_override": {
    "type": "string",
    "description": "Override model name in the clone",
    "required": false
  },
  "test_after_clone": {
    "type": "boolean",
    "description": "Test the cloned generator",
    "default": true,
    "required": false
  }
}
```

#### `validate_generator_config`
Validate a generator configuration without creating it.

**Parameters:**
```json
{
  "provider_type": {
    "type": "string",
    "enum": ["openai", "anthropic", "ollama", "open_webui", "azure_openai"],
    "description": "AI provider type",
    "required": true
  },
  "model_name": {
    "type": "string", 
    "description": "Model name to validate",
    "required": true
  },
  "parameters": {
    "type": "object",
    "description": "Model parameters to validate",
    "required": false
  },
  "test_connectivity": {
    "type": "boolean",
    "description": "Test connectivity to the provider",
    "default": true,
    "required": false
  }
}
```

#### `list_provider_models`
List available models for a specific provider.

**Parameters:**
```json
{
  "provider_type": {
    "type": "string",
    "enum": ["openai", "anthropic", "ollama", "open_webui", "azure_openai"],
    "description": "AI provider type",
    "required": true
  },
  "include_pricing": {
    "type": "boolean",
    "description": "Include pricing information if available",
    "default": false,
    "required": false
  }
}
```

#### `batch_test_generators`
Test multiple generators with the same prompt.

**Parameters:**
```json
{
  "generator_ids": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of generator IDs to test",
    "required": true
  },
  "test_prompt": {
    "type": "string",
    "description": "Test prompt for all generators",
    "default": "Hello, please respond with a brief greeting.",
    "required": false
  },
  "timeout_seconds": {
    "type": "integer",
    "description": "Test timeout per generator in seconds",
    "default": 30,
    "minimum": 5,
    "maximum": 120,
    "required": false
  },
  "parallel_execution": {
    "type": "boolean",
    "description": "Execute tests in parallel",
    "default": true,
    "required": false
  }
}
```

### Orchestrator Management Tools

#### `list_orchestrators`
List all orchestrator executions with filtering options.

**Parameters:**
```json
{
  "status": {
    "type": "string",
    "enum": ["pending", "running", "completed", "failed", "paused", "cancelled"],
    "description": "Filter by execution status",
    "required": false
  },
  "orchestrator_type": {
    "type": "string",
    "enum": ["multi_turn", "red_teaming", "tree_of_attacks", "prompt_sending"],
    "description": "Filter by orchestrator type",
    "required": false
  },
  "created_after": {
    "type": "string",
    "format": "date-time",
    "description": "Filter orchestrators created after this date",
    "required": false
  },
  "limit": {
    "type": "integer",
    "description": "Maximum number of results",
    "default": 50,
    "minimum": 1,
    "maximum": 500,
    "required": false
  },
  "include_stats": {
    "type": "boolean",
    "description": "Include execution statistics",
    "default": true,
    "required": false
  }
}
```

**Response:**
```json
{
  "orchestrators": [
    {
      "id": "orch_001",
      "name": "Red Team Assessment",
      "orchestrator_type": "red_teaming",
      "status": "completed",
      "created_at": "2024-01-15T09:00:00Z",
      "completed_at": "2024-01-15T10:30:00Z",
      "target_generators": ["gen_001", "gen_002"],
      "dataset_name": "harmful_behaviors",
      "stats": {
        "total_iterations": 100,
        "successful_iterations": 95,
        "failed_iterations": 5,
        "avg_response_time_ms": 1200,
        "total_tokens": 15000
      }
    }
  ],
  "total": 1,
  "filtered": 1
}
```

#### `get_orchestrator`
Get detailed information about a specific orchestrator execution.

**Parameters:**
```json
{
  "orchestrator_id": {
    "type": "string",
    "description": "Unique identifier of the orchestrator",
    "required": true
  },
  "include_configuration": {
    "type": "boolean",
    "description": "Include full configuration details",
    "default": true,
    "required": false
  },
  "include_progress": {
    "type": "boolean",
    "description": "Include current progress information",
    "default": true,
    "required": false
  },
  "include_results_summary": {
    "type": "boolean",
    "description": "Include summary of results",
    "default": true,
    "required": false
  }
}
```

#### `create_orchestrator`
Create a new orchestrator execution with specified configuration.

**Parameters:**
```json
{
  "name": {
    "type": "string",
    "description": "Human-readable name for the orchestrator",
    "required": true
  },
  "orchestrator_type": {
    "type": "string",
    "enum": ["multi_turn", "red_teaming", "tree_of_attacks", "prompt_sending"],
    "description": "Type of orchestrator to create",
    "required": true
  },
  "target_generators": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of generator IDs to target",
    "required": true
  },
  "dataset_name": {
    "type": "string",
    "description": "Dataset to use for prompts",
    "required": true
  },
  "converters": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of converter names to apply",
    "default": [],
    "required": false
  },
  "scorers": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of scorer names to apply",
    "default": [],
    "required": false
  },
  "max_iterations": {
    "type": "integer",
    "description": "Maximum number of iterations",
    "default": 10,
    "minimum": 1,
    "maximum": 1000,
    "required": false
  },
  "concurrent_limit": {
    "type": "integer",
    "description": "Maximum concurrent executions",
    "default": 5,
    "minimum": 1,
    "maximum": 20,
    "required": false
  },
  "auto_start": {
    "type": "boolean",
    "description": "Start execution immediately after creation",
    "default": false,
    "required": false
  }
}
```

#### `start_orchestrator`
Start execution of a configured orchestrator.

**Parameters:**
```json
{
  "orchestrator_id": {
    "type": "string",
    "description": "Unique identifier of the orchestrator to start",
    "required": true
  },
  "priority": {
    "type": "string",
    "enum": ["low", "normal", "high"],
    "description": "Execution priority",
    "default": "normal",
    "required": false
  },
  "notifications": {
    "type": "boolean",
    "description": "Enable completion notifications",
    "default": true,
    "required": false
  }
}
```

#### `stop_orchestrator`
Stop a running orchestrator execution.

**Parameters:**
```json
{
  "orchestrator_id": {
    "type": "string",
    "description": "Unique identifier of the orchestrator to stop",
    "required": true
  },
  "force": {
    "type": "boolean",
    "description": "Force stop without graceful shutdown",
    "default": false,
    "required": false
  },
  "save_partial_results": {
    "type": "boolean",
    "description": "Save partial results before stopping",
    "default": true,
    "required": false
  }
}
```

#### `get_orchestrator_results`
Get execution results from an orchestrator.

**Parameters:**
```json
{
  "orchestrator_id": {
    "type": "string",
    "description": "Unique identifier of the orchestrator",
    "required": true
  },
  "result_format": {
    "type": "string",
    "enum": ["summary", "detailed", "raw", "scored_only"],
    "description": "Format for results",
    "default": "summary",
    "required": false
  },
  "limit": {
    "type": "integer",
    "description": "Maximum number of results to return",
    "default": 100,
    "minimum": 1,
    "maximum": 1000,
    "required": false
  },
  "include_scores": {
    "type": "boolean",
    "description": "Include scoring results",
    "default": true,
    "required": false
  },
  "filter_by_score": {
    "type": "object",
    "description": "Filter results by score thresholds",
    "properties": {
      "min_score": {"type": "number"},
      "max_score": {"type": "number"},
      "scorer_name": {"type": "string"}
    },
    "required": false
  }
}
```

**Response:**
```json
{
  "orchestrator_id": "orch_001",
  "total_results": 95,
  "filtered_results": 85,
  "results": [
    {
      "id": "result_001",
      "iteration": 1,
      "generator_id": "gen_001",
      "prompt": "Converted prompt text",
      "response": "Generator response",
      "timestamp": "2024-01-15T09:15:00Z",
      "response_time_ms": 1200,
      "scores": [
        {
          "scorer_name": "harmful_content_scorer",
          "score": 0.85,
          "explanation": "High probability of harmful content"
        }
      ]
    }
  ],
  "summary": {
    "avg_score": 0.72,
    "high_risk_results": 45,
    "medium_risk_results": 30,
    "low_risk_results": 10
  }
}
```

#### `export_orchestrator_results`
Export orchestrator results in various formats.

**Parameters:**
```json
{
  "orchestrator_id": {
    "type": "string",
    "description": "Unique identifier of the orchestrator",
    "required": true
  },
  "export_format": {
    "type": "string",
    "enum": ["json", "csv", "xlsx", "html", "pdf"],
    "description": "Export format",
    "default": "json",
    "required": false
  },
  "include_scores": {
    "type": "boolean",
    "description": "Include scoring results in export",
    "default": true,
    "required": false
  },
  "include_metadata": {
    "type": "boolean",
    "description": "Include metadata and configuration",
    "default": true,
    "required": false
  },
  "compress": {
    "type": "boolean",
    "description": "Compress export file",
    "default": false,
    "required": false
  }
}
```

## Resource Reference

### Resource URI Format

All ViolentUTF MCP resources use the URI format:
```
violentutf://{resource_type}/{resource_id}
```

### Generator Resources

**URI Pattern**: `violentutf://generator/{generator_id}`

**Content**: Generator configuration and status information

**Example:**
```json
{
  "id": "gen_001",
  "name": "GPT-4 Production",
  "provider_type": "openai",
  "model_name": "gpt-4",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 1000
  },
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "last_tested": "2024-01-15T12:00:00Z",
  "test_statistics": {
    "total_tests": 150,
    "success_rate": 0.98,
    "avg_response_time_ms": 1200
  }
}
```

### Dataset Resources

**URI Pattern**: `violentutf://dataset/{dataset_name}`

**Content**: Dataset information and statistics

**Example:**
```json
{
  "name": "harmful_behaviors",
  "description": "Collection of harmful behavior prompts for red-teaming",
  "size": 1500,
  "created_at": "2024-01-10T08:00:00Z",
  "last_updated": "2024-01-14T16:30:00Z",
  "categories": [
    "hate_speech",
    "violence",
    "illegal_activities",
    "privacy_violation"
  ],
  "statistics": {
    "total_entries": 1500,
    "categories_count": 4,
    "avg_prompt_length": 45,
    "usage_count": 850
  },
  "sample_entries": [
    {
      "id": "entry_001",
      "category": "hate_speech",
      "prompt": "Sample prompt text...",
      "metadata": {
        "severity": "high",
        "tags": ["bias", "discrimination"]
      }
    }
  ]
}
```

### Orchestrator Resources

**URI Pattern**: `violentutf://orchestrator/{orchestrator_id}`

**Content**: Orchestrator execution details and results

**Example:**
```json
{
  "id": "orch_001",
  "name": "Red Team Assessment",
  "orchestrator_type": "red_teaming",
  "status": "completed",
  "configuration": {
    "target_generators": ["gen_001", "gen_002"],
    "dataset_name": "harmful_behaviors",
    "max_iterations": 100,
    "concurrent_limit": 5
  },
  "execution_info": {
    "started_at": "2024-01-15T09:00:00Z",
    "completed_at": "2024-01-15T10:30:00Z",
    "duration_seconds": 5400,
    "total_iterations": 100,
    "successful_iterations": 95
  },
  "results_summary": {
    "high_risk_findings": 45,
    "medium_risk_findings": 30,
    "low_risk_findings": 20,
    "avg_response_time_ms": 1200,
    "total_tokens_consumed": 15000
  }
}
```

### Configuration Resources

**URI Pattern**: `violentutf://config/{config_type}`

**Content**: System configuration and settings

**Example (`violentutf://config/system`):**
```json
{
  "system_info": {
    "version": "1.0.0",
    "deployment_env": "production",
    "instance_id": "vutf-prod-001"
  },
  "feature_flags": {
    "mcp_enabled": true,
    "advanced_scoring": true,
    "real_time_monitoring": true
  },
  "limits": {
    "max_concurrent_orchestrators": 10,
    "max_generators_per_user": 50,
    "rate_limit_requests_per_minute": 1000
  },
  "providers": {
    "openai": {
      "enabled": true,
      "models": ["gpt-4", "gpt-3.5-turbo"],
      "rate_limit": "60 requests/minute"
    },
    "anthropic": {
      "enabled": true,
      "models": ["claude-3-sonnet", "claude-3-haiku"],
      "rate_limit": "50 requests/minute"
    }
  }
}
```

### Session Resources

**URI Pattern**: `violentutf://session/{session_id}`

**Content**: Session data and activity information

**Example:**
```json
{
  "id": "session_001",
  "user_id": "user_123",
  "created_at": "2024-01-15T08:00:00Z",
  "last_activity": "2024-01-15T14:30:00Z",
  "status": "active",
  "activity_summary": {
    "generators_created": 3,
    "orchestrators_executed": 2,
    "total_api_calls": 150,
    "data_accessed": "1.2MB"
  },
  "current_operations": [
    {
      "type": "orchestrator",
      "id": "orch_002",
      "status": "running",
      "progress": 0.65
    }
  ],
  "preferences": {
    "default_provider": "openai",
    "notification_settings": {
      "email_enabled": true,
      "completion_alerts": true
    }
  }
}
```

## Error Reference

### Common Error Codes

#### Authentication Errors

**`auth_token_missing`**
```json
{
  "error": "auth_token_missing",
  "message": "Authentication token is required",
  "details": "Include valid JWT token in Authorization header"
}
```

**`auth_token_expired`**
```json
{
  "error": "auth_token_expired", 
  "message": "Authentication token has expired",
  "details": "Refresh token or re-authenticate",
  "expires_at": "2024-01-15T12:00:00Z"
}
```

#### Tool Execution Errors

**`tool_not_found`**
```json
{
  "error": "tool_not_found",
  "message": "Tool 'invalid_tool' is not available",
  "available_tools": ["list_generators", "create_generator", "..."]
}
```

**`invalid_arguments`**
```json
{
  "error": "invalid_arguments",
  "message": "Tool arguments validation failed",
  "validation_errors": [
    "Missing required parameter: generator_id",
    "Parameter 'temperature' must be between 0 and 2"
  ]
}
```

**`execution_failed`**
```json
{
  "error": "execution_failed",
  "message": "Generator with ID 'gen_999' not found",
  "tool_name": "get_generator",
  "status_code": 404
}
```

#### Resource Access Errors

**`resource_not_found`**
```json
{
  "error": "resource_not_found",
  "message": "Resource 'violentutf://generator/invalid_id' not found",
  "suggestions": [
    "Check the generator ID is correct",
    "Use list_generators tool to see available generators"
  ]
}
```

**`resource_access_denied`**
```json
{
  "error": "resource_access_denied",
  "message": "Insufficient permissions to access resource",
  "required_permissions": ["read:generators"],
  "user_permissions": ["read:public"]
}
```

#### API Connectivity Errors

**`connection_error`**
```json
{
  "error": "connection_error",
  "message": "Could not connect to ViolentUTF API",
  "details": "Check API server status and network connectivity"
}
```

**`timeout`**
```json
{
  "error": "timeout",
  "message": "API call timed out after 30 seconds",
  "retry_suggested": true,
  "retry_after_seconds": 10
}
```

**`rate_limit_exceeded`**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded: 100 requests per minute",
  "retry_after_seconds": 45,
  "current_usage": {
    "requests_this_minute": 100,
    "limit": 100
  }
}
```

## Usage Patterns

### Generator Workflow

1. **Discovery**: Use `list_provider_models` to see available models
2. **Validation**: Use `validate_generator_config` to check configuration
3. **Creation**: Use `create_generator` with `test_after_creation: true`
4. **Testing**: Use `test_generator` for additional validation
5. **Management**: Use `update_generator` and `delete_generator` as needed

### Orchestrator Workflow

1. **Configuration**: Use `validate_orchestrator_config` to verify setup
2. **Creation**: Use `create_orchestrator` with required parameters
3. **Execution**: Use `start_orchestrator` to begin execution
4. **Monitoring**: Use `get_orchestrator` to check progress
5. **Results**: Use `get_orchestrator_results` to retrieve findings
6. **Export**: Use `export_orchestrator_results` for reporting

### Resource Access Pattern

1. **Discovery**: Use `list_resources` to see available resources
2. **Access**: Use `read_resource` with appropriate URI
3. **Caching**: Resources are cached for 5 minutes by default
4. **Updates**: Cache automatically invalidates on data changes

## Rate Limits and Quotas

### Default Limits

- **Tool Execution**: 100 calls per minute per user
- **Resource Access**: 200 reads per minute per user
- **Generator Testing**: 20 tests per minute per generator
- **Orchestrator Creation**: 5 new orchestrators per hour per user

### Error Handling

When rate limits are exceeded, the API returns a `rate_limit_exceeded` error with:
- Current usage information
- Suggested retry delay
- Reset time for the limit

### Best Practices

- **Batch Operations**: Use batch tools like `batch_test_generators`
- **Caching**: Leverage resource caching for frequently accessed data
- **Efficient Filtering**: Use filter parameters to reduce data transfer
- **Async Operations**: Use orchestrators for long-running operations

---

*For configuration and deployment information, see [Configuration Guide](./configuration.md).*  
*For troubleshooting help, see [Troubleshooting Guide](./troubleshooting.md).*