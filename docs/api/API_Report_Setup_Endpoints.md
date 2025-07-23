# Report Setup API Endpoints Documentation

## Overview

This document details the API endpoints for the Report Setup feature in ViolentUTF. All endpoints require JWT authentication through the APISIX gateway.

## Base URL

```
http://localhost:9080/api/v1/reports/
```

## Authentication

All endpoints require a valid JWT token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### Template Management

#### List Templates
```http
GET /api/v1/reports/templates
```

Query Parameters:
- `category` (string, optional): Filter by category (executive, technical, compliance, security)
- `type` (string, optional): Filter by type (builtin, custom)
- `search` (string, optional): Search in name and description
- `scanner_type` (string, optional): Filter by scanner compatibility (pyrit, garak, all)
- `has_ai_analysis` (boolean, optional): Filter templates with AI analysis blocks
- `skip` (integer, optional): Pagination offset (default: 0)
- `limit` (integer, optional): Results per page (default: 100)

Response:
```json
{
  "templates": [
    {
      "id": "uuid",
      "name": "Executive Summary Report",
      "description": "High-level overview for executives",
      "category": "executive",
      "type": "builtin",
      "scanner_compatibility": ["pyrit", "garak"],
      "has_ai_analysis": true,
      "blocks": [...],
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 10,
  "skip": 0,
  "limit": 100
}
```

#### Get Template Details
```http
GET /api/v1/reports/templates/{template_id}
```

Response:
```json
{
  "id": "uuid",
  "name": "Executive Summary Report",
  "description": "High-level overview for executives",
  "category": "executive",
  "type": "builtin",
  "blocks": [
    {
      "type": "executive_summary",
      "enabled": true,
      "config": {...}
    }
  ],
  "scanner_compatibility": ["pyrit", "garak"],
  "metadata": {...}
}
```

#### Initialize Default Templates
```http
POST /api/v1/reports/templates/initialize
```

Request Body:
```json
{
  "force": false  // Set to true to reinitialize existing templates
}
```

Response:
```json
{
  "message": "Initialized 4 default templates",
  "templates": ["uuid1", "uuid2", "uuid3", "uuid4"]
}
```

### Block Registry

#### Get Available Block Types
```http
GET /api/v1/reports/blocks/registry
```

Response:
```json
{
  "blocks": {
    "executive_summary": {
      "name": "Executive Summary",
      "description": "High-level overview of findings",
      "schema": {...},
      "default_config": {...}
    },
    "ai_analysis": {
      "name": "AI Analysis",
      "description": "AI-powered security insights",
      "schema": {
        "type": "object",
        "properties": {
          "ai_model": {
            "type": "string",
            "title": "AI Model",
            "x-dynamic-enum": "generators"
          }
        }
      }
    }
  }
}
```

### Data Browsing

#### Browse Scan Data
```http
POST /api/v1/reports/data/browse
```

Request Body:
```json
{
  "filters": {
    "scanner_type": "pyrit",
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-12-31T23:59:59Z"
    },
    "severity_level": ["high", "critical"],
    "model": "gpt-4"
  },
  "pagination": {
    "skip": 0,
    "limit": 50
  }
}
```

Response:
```json
{
  "scans": [
    {
      "id": "scan_123",
      "type": "pyrit",
      "execution_id": "exec_456",
      "model": "gpt-4",
      "timestamp": "2024-01-15T10:30:00Z",
      "summary": {
        "total_prompts": 100,
        "flagged": 15,
        "severity_breakdown": {
          "critical": 2,
          "high": 5,
          "medium": 8
        }
      }
    }
  ],
  "total": 150,
  "skip": 0,
  "limit": 50
}
```

### Report Configuration

#### Save Report Configuration
```http
POST /api/v1/reports/config
```

Request Body:
```json
{
  "template_id": "uuid",
  "selected_scans": ["scan_123", "scan_456"],
  "configuration": {
    "basic": {
      "title": "Q4 Security Assessment",
      "description": "Quarterly security review",
      "period": {
        "start": "2024-10-01",
        "end": "2024-12-31"
      },
      "timezone": "UTC"
    },
    "blocks": {
      "executive_summary": {
        "enabled": true,
        "config": {...}
      },
      "ai_analysis": {
        "enabled": true,
        "config": {
          "ai_model": "gpt-4-security-tuned",
          "analysis_depth": "detailed"
        }
      }
    },
    "output": {
      "formats": ["pdf", "json"],
      "include_raw_data": false
    },
    "notifications": {
      "enabled": true,
      "email": "security@company.com"
    }
  }
}
```

Response:
```json
{
  "config_id": "config_789",
  "message": "Configuration saved successfully"
}
```

### Generator Integration

#### Get Available Generators (for AI models)
```http
GET /api/v1/generators
```

Response:
```json
{
  "generators": [
    {
      "id": "gen_123",
      "name": "gpt-4-security-tuned",
      "type": "openai",
      "description": "Fine-tuned GPT-4 for security analysis",
      "configuration": {...}
    },
    {
      "id": "gen_456",
      "name": "claude-3-security",
      "type": "anthropic",
      "description": "Claude 3 configured for security assessments"
    }
  ]
}
```

### Orchestrator Results (for AI Analysis)

#### Get Execution Details
```http
GET /api/v1/orchestrators/results/{execution_id}
```

Response:
```json
{
  "execution_id": "exec_123",
  "orchestrator": "RedTeamingOrchestrator",
  "status": "completed",
  "results": {
    "total_prompts": 100,
    "flagged_prompts": 15,
    "scores": [
      {
        "prompt": "...",
        "score": 0.85,
        "category": "jailbreak",
        "severity": "high"
      }
    ],
    "summary": {
      "average_score": 0.45,
      "max_score": 0.95,
      "categories": {
        "jailbreak": 5,
        "toxicity": 3,
        "bias": 7
      }
    }
  }
}
```

## Error Responses

All endpoints follow a consistent error response format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "type": "validation_error",
  "errors": [
    {
      "field": "template_id",
      "message": "Invalid UUID format"
    }
  ]
}
```

Common HTTP status codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request (validation error)
- `401`: Unauthorized (invalid/missing JWT)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

API endpoints are rate-limited through APISIX:
- Default: 100 requests per minute per user
- Burst: 200 requests allowed
- Headers returned:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Time when limit resets

## Webhook Events

For configured webhooks, the following events are sent:

### Report Generation Started
```json
{
  "event": "report.generation.started",
  "timestamp": "2024-01-01T10:00:00Z",
  "data": {
    "job_id": "job_123",
    "template_id": "template_456",
    "user": "user@company.com"
  }
}
```

### Report Generation Completed
```json
{
  "event": "report.generation.completed",
  "timestamp": "2024-01-01T10:30:00Z",
  "data": {
    "job_id": "job_123",
    "report_id": "report_789",
    "formats": ["pdf", "json"],
    "duration_seconds": 1800
  }
}
```

### Report Generation Failed
```json
{
  "event": "report.generation.failed",
  "timestamp": "2024-01-01T10:15:00Z",
  "data": {
    "job_id": "job_123",
    "error": "AI service timeout",
    "error_code": "AI_TIMEOUT"
  }
}
```

## Migration Notes

### From COB Endpoints

If you were using the legacy `/api/v1/cob/` endpoints:

| Old Endpoint | New Endpoint |
|-------------|--------------|
| `GET /api/v1/cob/templates` | `GET /api/v1/reports/templates` |
| `POST /api/v1/cob/reports` | `POST /api/v1/reports/generate` |
| `GET /api/v1/cob/schedules` | Use configuration in Report Setup |

### Key Changes:
1. All endpoints now under `/api/v1/reports/`
2. Enhanced filtering and search capabilities
3. Real-time data integration (no mock data)
4. Dynamic AI model selection from generators
5. Improved error handling and validation

## SDK Examples

### Python
```python
import requests

# Setup headers
headers = {
    "Authorization": f"Bearer {jwt_token}",
    "Content-Type": "application/json"
}

# List templates
response = requests.get(
    "http://localhost:9080/api/v1/reports/templates",
    headers=headers,
    params={"category": "executive", "has_ai_analysis": True}
)
templates = response.json()

# Get generators for AI models
response = requests.get(
    "http://localhost:9080/api/v1/generators",
    headers=headers
)
generators = response.json()
```

### JavaScript
```javascript
// List templates with AI analysis
const response = await fetch(
  'http://localhost:9080/api/v1/reports/templates?has_ai_analysis=true',
  {
    headers: {
      'Authorization': `Bearer ${jwtToken}`,
      'Content-Type': 'application/json'
    }
  }
);
const templates = await response.json();

// Save configuration
const config = {
  template_id: selectedTemplate,
  configuration: {
    // ... configuration details
  }
};

await fetch('http://localhost:9080/api/v1/reports/config', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(config)
});
```