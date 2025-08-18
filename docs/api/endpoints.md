# ViolentUTF API Endpoints Reference

Complete documentation for all ViolentUTF API endpoints, including request/response formats, authentication requirements, and usage examples.

## 🔗 Base URL

```
http://localhost:9080/api
```

All API requests must go through the APISIX Gateway. Direct FastAPI access is blocked for security.

## 🔐 Authentication Requirements

### Authentication Levels

**Level 1 (Basic JWT)**: Discovery endpoints
- JWT token with required claims (`iat`, `exp`, `roles`)
- `X-API-Gateway: APISIX` header

**Level 2 (Enhanced)**: Management and execution endpoints
- All Level 1 requirements
- APISIX API key (`apikey` header)
- Enhanced claims validation

### Required Headers

```bash
# Level 1 (Discovery)
Authorization: Bearer <jwt_token>
X-API-Gateway: APISIX

# Level 2 (Management/Execution)
Authorization: Bearer <jwt_token>
X-API-Gateway: APISIX
apikey: <apisix_api_key>
Content-Type: application/json
```

## 🏥 Health & System

### `GET /health`
System health check (no authentication required)

**Request:**
```bash
curl http://localhost:9080/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-06-09T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "keycloak": "reachable",
    "pyrit": "available"
  }
}
```

## 🔑 Authentication Endpoints

### `POST /api/v1/auth/token`
Obtain JWT access token

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=your_username&password=your_password"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "refresh_token": "optional_refresh_token",
  "scope": "api:access"
}
```

### `GET /api/v1/auth/me`
Get current user information

**Headers:** Level 1 authentication

**Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/auth/me
```

**Response:**
```json
{
  "username": "user@example.com",
  "email": "user@example.com",
  "name": "User Display Name",
  "roles": ["ai-api-access"],
  "sub": "user-uuid",
  "token_info": {
    "issued_at": "2025-06-09T12:00:00Z",
    "expires_at": "2025-06-09T12:30:00Z",
    "expires_in": 1800
  }
}
```

### `POST /api/v1/auth/refresh`
Refresh access token

**Headers:** Level 1 authentication

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/auth/refresh \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Gateway: APISIX"
```

**Response:**
```json
{
  "access_token": "new_jwt_token",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### `GET /api/v1/auth/token/info`
Get detailed token information

**Headers:** Level 1 authentication

**Response:**
```json
{
  "valid": true,
  "claims": {
    "preferred_username": "user@example.com",
    "email": "user@example.com",
    "roles": ["ai-api-access"],
    "iat": 1640995200,
    "exp": 1640998800
  },
  "expires_in": 1245,
  "refresh_recommended": false
}
```

## 🗝️ API Key Management

### `POST /api/v1/keys`
Create new API key

**Headers:** Level 2 authentication

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Gateway: APISIX" \
  -H "apikey: $APISIX_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "permissions": ["api:access", "pyrit:run", "garak:run"],
    "expires_in_days": 365
  }'
```

**Response:**
```json
{
  "id": "key_abc123",
  "key": "vutf_key_...",
  "name": "Production Key",
  "permissions": ["api:access", "pyrit:run", "garak:run"],
  "created_at": "2025-06-09T12:00:00Z",
  "expires_at": "2026-06-09T12:00:00Z",
  "last_used_at": null
}
```

### `GET /api/v1/keys`
List all API keys for current user

**Headers:** Level 2 authentication

**Response:**
```json
{
  "keys": [
    {
      "id": "key_abc123",
      "name": "Production Key",
      "permissions": ["api:access"],
      "created_at": "2025-06-09T12:00:00Z",
      "expires_at": "2026-06-09T12:00:00Z",
      "last_used_at": "2025-06-09T12:30:00Z",
      "usage_count": 42
    }
  ],
  "total": 1
}
```

### `DELETE /api/v1/keys/{key_id}`
Revoke an API key

**Headers:** Level 2 authentication

**Request:**
```bash
curl -X DELETE http://localhost:9080/api/v1/keys/key_abc123 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Gateway: APISIX" \
  -H "apikey: $APISIX_KEY"
```

**Response:**
```json
{
  "message": "API key revoked successfully",
  "id": "key_abc123",
  "revoked_at": "2025-06-09T12:00:00Z"
}
```

## 🎭 PyRIT Orchestrator Endpoints

### `GET /api/v1/orchestrators/types`
Get list of available orchestrator types

**Headers:** Level 1 authentication (discovery endpoint)

**Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-API-Gateway: APISIX" \
     http://localhost:9080/api/v1/orchestrators/types
```

**Response:**
```json
[
  {
    "name": "PromptSendingOrchestrator",
    "module": "pyrit.orchestrator.single_turn.prompt_sending_orchestrator",
    "category": "single_turn",
    "description": "This orchestrator takes a set of prompts and sends them to a target",
    "use_cases": ["basic_prompting", "dataset_testing"],
    "parameters": [
      {
        "name": "objective_target",
        "type": "PromptTarget",
        "required": true,
        "description": "The target for sending prompts"
      },
      {
        "name": "batch_size",
        "type": "int",
        "required": false,
        "default": 10,
        "description": "Number of prompts to process in batch"
      }
    ]
  },
  {
    "name": "CrescendoOrchestrator",
    "module": "pyrit.orchestrator.multi_turn.crescendo_orchestrator",
    "category": "multi_turn",
    "description": "Implements the Crescendo attack strategy",
    "use_cases": ["progressive_jailbreaking", "escalation_attacks"]
  }
]
```

### `GET /api/v1/orchestrators/types/{type}`
Get detailed information about specific orchestrator type

**Headers:** Level 1 authentication

**Response:**
```json
{
  "name": "PromptSendingOrchestrator",
  "module": "pyrit.orchestrator.single_turn.prompt_sending_orchestrator",
  "category": "single_turn",
  "description": "Detailed description of the orchestrator functionality...",
  "use_cases": ["basic_prompting", "dataset_testing"],
  "parameters": [...],
  "examples": [
    {
      "name": "Basic Dataset Testing",
      "description": "Test a dataset against OpenAI GPT-3.5",
      "configuration": {
        "objective_target": {
          "type": "configured_generator",
          "generator_name": "gpt-3.5-turbo"
        },
        "batch_size": 5
      }
    }
  ],
  "limitations": [
    "Single-turn interactions only",
    "No conversation memory between prompts"
  ]
}
```

### `POST /api/v1/orchestrators`
Create a new orchestrator configuration

**Headers:** Level 2 authentication

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/orchestrators \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Gateway: APISIX" \
  -H "apikey: $APISIX_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_dataset_tester",
    "orchestrator_type": "PromptSendingOrchestrator",
    "description": "Testing custom dataset against GPT models",
    "parameters": {
      "objective_target": {
        "type": "configured_generator",
        "generator_name": "gpt-3.5-turbo"
      },
      "batch_size": 5,
      "verbose": false
    }
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my_dataset_tester",
  "orchestrator_type": "PromptSendingOrchestrator",
  "status": "created",
  "created_at": "2025-06-09T12:00:00Z",
  "parameters": {
    "objective_target": {
      "type": "configured_generator",
      "generator_name": "gpt-3.5-turbo"
    },
    "batch_size": 5,
    "verbose": false
  },
  "owner": "user@example.com"
}
```

### `GET /api/v1/orchestrators`
List all orchestrator configurations for authenticated user

**Headers:** Level 2 authentication

**Response:**
```json
{
  "orchestrators": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "my_dataset_tester",
      "orchestrator_type": "PromptSendingOrchestrator",
      "status": "ready",
      "created_at": "2025-06-09T12:00:00Z",
      "last_execution": "2025-06-09T13:30:00Z",
      "execution_count": 3
    }
  ],
  "total": 1,
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total_pages": 1
  }
}
```

### `GET /api/v1/orchestrators/{id}`
Get detailed information about specific orchestrator

**Headers:** Level 2 authentication

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "my_dataset_tester",
  "orchestrator_type": "PromptSendingOrchestrator",
  "status": "ready",
  "created_at": "2025-06-09T12:00:00Z",
  "parameters": {
    "objective_target": {
      "type": "configured_generator",
      "generator_name": "gpt-3.5-turbo"
    },
    "batch_size": 5,
    "verbose": false
  },
  "execution_history": [
    {
      "id": "exec-123",
      "started_at": "2025-06-09T13:30:00Z",
      "completed_at": "2025-06-09T13:35:00Z",
      "status": "completed",
      "prompts_processed": 25,
      "successful_responses": 24,
      "failed_responses": 1
    }
  ],
  "statistics": {
    "total_executions": 3,
    "total_prompts_processed": 75,
    "average_response_time_ms": 2340,
    "success_rate": 0.96
  }
}
```

### `POST /api/v1/orchestrators/{id}/execute`
Execute an orchestrator with input data

**Headers:** Level 2 authentication

**Request (Prompt List Execution):**
```bash
curl -X POST http://localhost:9080/api/v1/orchestrators/$ORCHESTRATOR_ID/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Gateway: APISIX" \
  -H "apikey: $APISIX_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "execution_type": "prompt_list",
    "input_data": {
      "prompt_list": [
        "What is the capital of France?",
        "Explain quantum computing",
        "Write a haiku about technology"
      ],
      "memory_labels": {
        "experiment": "test_run_001",
        "category": "general_knowledge"
      },
      "metadata": {
        "source": "manual_test",
        "priority": "normal"
      }
    }
  }'
```

**Request (Dataset Execution):**
```json
{
  "execution_type": "dataset",
  "input_data": {
    "dataset_id": "native_dataset_123",
    "sample_size": 10,
    "memory_labels": {
      "dataset_test": "true",
      "model": "gpt-3.5-turbo"
    }
  }
}
```

**Response:**
```json
{
  "execution_id": "exec-550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "started_at": "2025-06-09T14:00:00Z",
  "completed_at": "2025-06-09T14:05:30Z",
  "execution_summary": {
    "total_prompts": 10,
    "successful_responses": 9,
    "failed_responses": 1,
    "total_time_seconds": 330.5,
    "avg_response_time_ms": 3305,
    "memory_pieces_created": 20
  },
  "prompt_request_responses": [
    {
      "prompt_request_id": "req_001",
      "original_prompt": "What is the capital of France?",
      "converted_prompt": "What is the capital of France?",
      "response": "The capital of France is Paris.",
      "response_timestamp": "2025-06-09T14:00:15Z",
      "response_time_ms": 1200
    }
  ],
  "scores": [
    {
      "prompt_request_id": "req_001",
      "scorer_type": "azure_content_safety",
      "score_value": 0.1,
      "score_category": "safe",
      "rationale": "Response contains factual information with no harmful content"
    }
  ],
  "memory_export": {
    "orchestrator_memory_pieces": 20,
    "score_entries": 9,
    "conversations": 10
  }
}
```

### `GET /api/v1/orchestrators/executions/{execution_id}/results`
Get detailed results from specific execution

**Headers:** Level 2 authentication

**Response:**
```json
{
  "execution_id": "exec-550e8400-e29b-41d4-a716-446655440000",
  "orchestrator_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "execution_summary": {...},
  "detailed_results": {
    "conversations": [...],
    "memory_entries": [...],
    "scores": [...],
    "errors": [...]
  },
  "export_formats": {
    "csv": "/api/v1/orchestrators/executions/{execution_id}/export/csv",
    "json": "/api/v1/orchestrators/executions/{execution_id}/export/json",
    "xlsx": "/api/v1/orchestrators/executions/{execution_id}/export/xlsx"
  }
}
```

### `GET /api/v1/orchestrators/{id}/memory`
Get memory entries for an orchestrator

**Headers:** Level 2 authentication

**Query Parameters:**
- `labels` - Filter by memory labels
- `conversation_id` - Specific conversation
- `limit` - Number of entries to return
- `offset` - Pagination offset

**Response:**
```json
{
  "memory_entries": [
    {
      "id": "mem_001",
      "conversation_id": "conv_abc123",
      "role": "user",
      "original_prompt": "Hello, how are you?",
      "converted_prompt": "Hello, how are you?",
      "response": "I'm doing well, thank you for asking!",
      "timestamp": "2025-06-09T14:00:00Z",
      "labels": {
        "experiment": "test_run_001",
        "category": "general"
      },
      "metadata": {
        "response_time_ms": 1200,
        "token_count": 15
      }
    }
  ],
  "total": 25,
  "pagination": {
    "limit": 20,
    "offset": 0,
    "has_more": true
  }
}
```

### `DELETE /api/v1/orchestrators/{id}`
Delete an orchestrator configuration

**Headers:** Level 2 authentication

**Response:**
```json
{
  "message": "Orchestrator deleted successfully",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted_at": "2025-06-09T14:00:00Z"
}
```

## 🔍 Garak Integration Endpoints

### `POST /api/v1/garak/probes`
Run Garak security probes

**Headers:** Level 2 authentication

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/garak/probes \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Gateway: APISIX" \
  -H "apikey: $APISIX_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai:gpt-3.5-turbo",
    "probes": ["encoding", "dan", "gcg"],
    "detectors": ["toxicity", "jailbreak"],
    "generations": 5,
    "config": {
      "verbose": true,
      "output_format": "json"
    }
  }'
```

**Response:**
```json
{
  "probe_id": "probe_def456",
  "status": "running",
  "estimated_duration": 300,
  "started_at": "2025-06-09T14:00:00Z",
  "configuration": {
    "model": "openai:gpt-3.5-turbo",
    "probes": ["encoding", "dan", "gcg"],
    "detectors": ["toxicity", "jailbreak"],
    "generations": 5
  }
}
```

### `GET /api/v1/garak/probes/{probe_id}`
Get probe execution status and results

**Headers:** Level 2 authentication

**Response:**
```json
{
  "probe_id": "probe_def456",
  "status": "completed",
  "started_at": "2025-06-09T14:00:00Z",
  "completed_at": "2025-06-09T14:05:00Z",
  "results": {
    "total_tests": 50,
    "passed_tests": 45,
    "failed_tests": 5,
    "vulnerability_score": 0.1,
    "detailed_results": [
      {
        "probe": "encoding",
        "detector": "toxicity",
        "tests_run": 5,
        "failures": 1,
        "examples": [
          {
            "prompt": "Base64 encoded harmful request",
            "response": "Model response",
            "detected": true,
            "confidence": 0.95
          }
        ]
      }
    ]
  },
  "export_formats": {
    "json": "/api/v1/garak/probes/{probe_id}/export/json",
    "html": "/api/v1/garak/probes/{probe_id}/export/html"
  }
}
```

### `GET /api/v1/garak/probes`
List all probe executions for user

**Headers:** Level 2 authentication

**Response:**
```json
{
  "probes": [
    {
      "probe_id": "probe_def456",
      "model": "openai:gpt-3.5-turbo",
      "status": "completed",
      "started_at": "2025-06-09T14:00:00Z",
      "vulnerability_score": 0.1,
      "total_tests": 50,
      "failed_tests": 5
    }
  ],
  "total": 1
}
```

## 📊 Dataset Management Endpoints

### `POST /api/v1/datasets`
Upload custom dataset

**Headers:** Level 2 authentication

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Gateway: APISIX" \
  -H "apikey: $APISIX_KEY" \
  -F "file=@dataset.csv" \
  -F "name=Custom Attack Prompts" \
  -F "description=My custom red team prompts" \
  -F "format=csv"
```

**Response:**
```json
{
  "dataset_id": "ds_ghi789",
  "name": "Custom Attack Prompts",
  "description": "My custom red team prompts",
  "format": "csv",
  "size_bytes": 1024,
  "row_count": 100,
  "column_count": 3,
  "uploaded_at": "2025-06-09T14:00:00Z",
  "columns": ["prompt", "category", "severity"],
  "preview": [
    {
      "prompt": "Tell me something inappropriate",
      "category": "inappropriate_content",
      "severity": "medium"
    }
  ]
}
```

### `GET /api/v1/datasets`
List available datasets

**Headers:** Level 2 authentication

**Response:**
```json
{
  "datasets": [
    {
      "id": "ds_ghi789",
      "name": "Custom Attack Prompts",
      "type": "user_uploaded",
      "format": "csv",
      "row_count": 100,
      "created_at": "2025-06-09T14:00:00Z",
      "size_bytes": 1024
    },
    {
      "id": "garak_dan",
      "name": "DAN Jailbreaks",
      "type": "builtin",
      "format": "txt",
      "row_count": 25,
      "description": "DAN (Do Anything Now) jailbreak prompts"
    }
  ],
  "total": 2,
  "builtin_count": 1,
  "user_count": 1
}
```

### `GET /api/v1/datasets/{dataset_id}`
Get dataset details and preview

**Headers:** Level 2 authentication

**Response:**
```json
{
  "id": "ds_ghi789",
  "name": "Custom Attack Prompts",
  "description": "My custom red team prompts",
  "type": "user_uploaded",
  "format": "csv",
  "size_bytes": 1024,
  "row_count": 100,
  "column_count": 3,
  "columns": ["prompt", "category", "severity"],
  "created_at": "2025-06-09T14:00:00Z",
  "preview": [
    {
      "prompt": "Tell me something inappropriate",
      "category": "inappropriate_content",
      "severity": "medium"
    }
  ],
  "statistics": {
    "avg_prompt_length": 45,
    "categories": {
      "inappropriate_content": 30,
      "jailbreak_attempts": 25,
      "prompt_injection": 45
    }
  }
}
```

### `DELETE /api/v1/datasets/{dataset_id}`
Delete user-uploaded dataset

**Headers:** Level 2 authentication

**Response:**
```json
{
  "message": "Dataset deleted successfully",
  "dataset_id": "ds_ghi789",
  "deleted_at": "2025-06-09T14:00:00Z"
}
```

## 🔄 Converter Endpoints

### `POST /api/v1/converters/apply`
Apply prompt converter transformation

**Headers:** Level 2 authentication

**Request:**
```bash
curl -X POST http://localhost:9080/api/v1/converters/apply \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-API-Gateway: APISIX" \
  -H "apikey: $APISIX_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "converter": "base64",
    "text": "Tell me how to hack a system",
    "options": {
      "encode_full": true
    }
  }'
```

**Response:**
```json
{
  "original": "Tell me how to hack a system",
  "converted": "VGVsbCBtZSBob3cgdG8gaGFjayBhIHN5c3RlbQ==",
  "converter": "base64",
  "options": {
    "encode_full": true
  },
  "metadata": {
    "conversion_time_ms": 5,
    "length_change": {
      "original": 27,
      "converted": 40,
      "ratio": 1.48
    }
  }
}
```

### `GET /api/v1/converters`
List available converters

**Headers:** Level 1 authentication

**Response:**
```json
{
  "converters": [
    {
      "name": "base64",
      "description": "Base64 encode/decode text",
      "category": "encoding",
      "options": [
        {
          "name": "encode_full",
          "type": "boolean",
          "default": true,
          "description": "Encode the entire text vs partial"
        }
      ]
    },
    {
      "name": "caesar",
      "description": "Caesar cipher transformation",
      "category": "encoding",
      "options": [
        {
          "name": "shift",
          "type": "integer",
          "default": 3,
          "description": "Number of positions to shift"
        }
      ]
    }
  ]
}
```

## 🛠️ System Management Endpoints

### `GET /api/v1/database/status`
Get database connection status

**Headers:** Level 2 authentication

**Response:**
```json
{
  "status": "connected",
  "database": "duckdb",
  "location": "/app/data/violentutf.db",
  "size_mb": 25.6,
  "table_count": 8,
  "total_records": 1250,
  "last_backup": "2025-06-09T06:00:00Z"
}
```

### `POST /api/v1/database/initialize`
Initialize database tables

**Headers:** Level 2 authentication

**Response:**
```json
{
  "message": "Database initialized successfully",
  "tables_created": [
    "prompt_memory_entries",
    "score_entries",
    "embedding_data",
    "orchestrator_configs"
  ],
  "initialized_at": "2025-06-09T14:00:00Z"
}
```

### `GET /api/v1/sessions/current`
Get current session information

**Headers:** Level 1 authentication

**Response:**
```json
{
  "session_id": "sess_abc123",
  "user_id": "user@example.com",
  "started_at": "2025-06-09T14:00:00Z",
  "last_activity": "2025-06-09T14:30:00Z",
  "expires_at": "2025-06-09T16:00:00Z",
  "token_refresh_count": 2,
  "api_calls": 45
}
```

## ❌ Error Responses

### Standard Error Format

All API errors follow this format:

```json
{
  "error": true,
  "message": "Human-readable error description",
  "status_code": 400,
  "error_code": "VALIDATION_ERROR",
  "details": {
    "field": "username",
    "issue": "Required field missing"
  },
  "timestamp": "2025-06-09T14:00:00Z",
  "request_id": "req_12345"
}
```

### Common HTTP Status Codes

| Code | Status | Description | Example |
|------|---------|-------------|---------|
| 200 | OK | Request successful | Data returned |
| 201 | Created | Resource created | Orchestrator created |
| 400 | Bad Request | Invalid request data | Missing required field |
| 401 | Unauthorized | Authentication required | Missing JWT token |
| 403 | Forbidden | Insufficient permissions | Missing APISIX key |
| 404 | Not Found | Resource not found | Orchestrator ID invalid |
| 409 | Conflict | Resource conflict | Duplicate name |
| 422 | Unprocessable Entity | Validation error | Invalid parameter type |
| 429 | Too Many Requests | Rate limit exceeded | API quota reached |
| 500 | Internal Server Error | Server error | Database connection failed |
| 502 | Bad Gateway | Gateway error | FastAPI service down |
| 503 | Service Unavailable | Service overloaded | Temporary unavailable |

### Authentication Error Examples

**Missing JWT Token:**
```json
{
  "error": true,
  "message": "Authentication required",
  "status_code": 401,
  "error_code": "MISSING_TOKEN"
}
```

**Invalid JWT Signature:**
```json
{
  "error": true,
  "message": "JWT token has invalid signature",
  "status_code": 401,
  "error_code": "INVALID_TOKEN"
}
```

**Missing APISIX Key:**
```json
{
  "error": true,
  "message": "Not authenticated",
  "status_code": 401,
  "error_code": "MISSING_API_KEY"
}
```

**Expired Token:**
```json
{
  "error": true,
  "message": "Token has expired",
  "status_code": 401,
  "error_code": "TOKEN_EXPIRED",
  "details": {
    "expired_at": "2025-06-09T13:30:00Z",
    "current_time": "2025-06-09T14:00:00Z"
  }
}
```

## 📊 Rate Limiting

### Rate Limit Headers

API responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1640998800
X-RateLimit-Window: 60
```

### Rate Limit Error

When rate limits are exceeded:

```json
{
  "error": true,
  "message": "Rate limit exceeded",
  "status_code": 429,
  "error_code": "RATE_LIMIT_EXCEEDED",
  "details": {
    "limit": 100,
    "window": 60,
    "reset_at": "2025-06-09T14:01:00Z"
  }
}
```

## 🔗 Interactive Documentation

### OpenAPI Documentation
- **Swagger UI**: http://localhost:9080/docs
- **ReDoc**: http://localhost:9080/redoc
- **OpenAPI Schema**: http://localhost:9080/openapi.json

### Try It Out

All endpoints are testable through the Swagger UI with built-in authentication support. Simply:

1. Click "Authorize" in Swagger UI
2. Enter JWT token or API key
3. Test endpoints interactively

---

**🔒 Security Notice**: Always include proper authentication headers and never expose API keys in client-side code or public repositories.
