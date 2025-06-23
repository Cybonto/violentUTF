# ViolentUTF MCP Configuration Guide

## Overview

This guide covers the configuration options for the ViolentUTF Model Context Protocol (MCP) server, including setup, customization, and deployment considerations.

## Environment Configuration

### Core MCP Settings

Add these settings to your `.env` file:

```bash
# MCP Server Configuration
MCP_SERVER_NAME="ViolentUTF-MCP"
MCP_SERVER_VERSION="1.0.0"

# Feature Toggles
MCP_ENABLE_TOOLS=true
MCP_ENABLE_RESOURCES=true
MCP_ENABLE_PROMPTS=true
MCP_ENABLE_SAMPLING=false

# Transport Configuration
MCP_TRANSPORT_TYPE="sse"
MCP_SSE_ENDPOINT="/mcp/sse"

# Security Settings
MCP_REQUIRE_AUTH=true
MCP_TOKEN_VALIDATION=true

# Performance Settings
MCP_TOOL_TIMEOUT_SECONDS=60
MCP_CONCURRENT_TOOL_LIMIT=10
MCP_RETRY_ATTEMPTS=3

# Resource Management
MCP_RESOURCE_CACHE_TTL=300
MCP_RESOURCE_CACHE_SIZE=1000
MCP_RESOURCE_PREFETCH=true
```

### Authentication Configuration

```bash
# Keycloak Integration
KEYCLOAK_URL="http://keycloak:8080"
KEYCLOAK_REALM="ViolentUTF"
KEYCLOAK_CLIENT_ID="violentutf-fastapi"
KEYCLOAK_CLIENT_SECRET="your-client-secret"

# JWT Configuration
JWT_SECRET_KEY="your-jwt-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
API_KEY_EXPIRE_DAYS=365

# Development Fallback (optional)
KEYCLOAK_USERNAME="dev-user"
KEYCLOAK_PASSWORD="dev-password"
```

### APISIX Gateway Configuration

```bash
# APISIX Settings
APISIX_ADMIN_URL="http://apisix-apisix-1:9180"
APISIX_ADMIN_KEY="your-admin-key"
APISIX_BASE_URL="http://apisix-apisix-1:9080"
APISIX_GATEWAY_SECRET="your-gateway-secret"

# API Gateway Keys
VIOLENTUTF_API_KEY="your-api-key"
AI_GATEWAY_API_KEY="your-ai-gateway-key"
```

## Configuration Files

### MCP Settings (`app/mcp/config.py`)

```python
from pydantic_settings import BaseSettings
from typing import Optional

class MCPSettings(BaseSettings):
    # Server Identity
    MCP_SERVER_NAME: str = "ViolentUTF-MCP"
    MCP_SERVER_VERSION: str = "1.0.0"
    MCP_SERVER_DESCRIPTION: str = "ViolentUTF AI Red-teaming MCP Server"
    
    # Feature Flags
    MCP_ENABLE_TOOLS: bool = True
    MCP_ENABLE_RESOURCES: bool = True
    MCP_ENABLE_PROMPTS: bool = True
    MCP_ENABLE_SAMPLING: bool = False
    
    # Transport Layer
    MCP_TRANSPORT_TYPE: str = "sse"  # Options: sse, websocket
    MCP_SSE_ENDPOINT: str = "/mcp/sse"
    MCP_WEBSOCKET_ENDPOINT: str = "/mcp/ws"
    
    # Security
    MCP_REQUIRE_AUTH: bool = True
    MCP_TOKEN_VALIDATION: bool = True
    MCP_CORS_ENABLED: bool = True
    MCP_CORS_ORIGINS: list = ["http://localhost:3000", "https://claude.ai"]
    
    # Performance
    MCP_TOOL_TIMEOUT_SECONDS: int = 60
    MCP_CONCURRENT_TOOL_LIMIT: int = 10
    MCP_RETRY_ATTEMPTS: int = 3
    MCP_RETRY_BACKOFF_FACTOR: float = 2.0
    
    # Resource Management
    MCP_RESOURCE_CACHE_TTL: int = 300  # 5 minutes
    MCP_RESOURCE_CACHE_SIZE: int = 1000
    MCP_RESOURCE_PREFETCH: bool = True
    MCP_RESOURCE_COMPRESSION: bool = True
    
    # Logging
    MCP_LOG_LEVEL: str = "INFO"
    MCP_LOG_FORMAT: str = "json"
    MCP_ACCESS_LOG_ENABLED: bool = True
    
    # Development
    MCP_DEBUG_MODE: bool = False
    MCP_DEVELOPMENT_MODE: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True
```

### Docker Compose Configuration

Add MCP configuration to your `docker-compose.yml`:

```yaml
version: '3.8'
services:
  violentutf-api:
    build: 
      context: ./violentutf_api
      dockerfile: Dockerfile
    environment:
      # MCP Configuration
      - MCP_ENABLE_TOOLS=true
      - MCP_ENABLE_RESOURCES=true
      - MCP_TRANSPORT_TYPE=sse
      - MCP_REQUIRE_AUTH=true
      
      # Performance Settings
      - MCP_TOOL_TIMEOUT_SECONDS=60
      - MCP_CONCURRENT_TOOL_LIMIT=10
      - MCP_RESOURCE_CACHE_TTL=300
      
      # Security
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - KEYCLOAK_URL=http://keycloak:8080
      - APISIX_BASE_URL=http://apisix-apisix-1:9080
    networks:
      - vutf-network
    depends_on:
      - keycloak
      - apisix-apisix-1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/mcp/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## APISIX Route Configuration

### MCP Routes Setup

Create `apisix/conf/mcp-routes.sh`:

```bash
#!/bin/bash

# MCP Routes Configuration Script
APISIX_ADMIN_URL=${APISIX_ADMIN_URL:-"http://apisix-apisix-1:9180"}
APISIX_ADMIN_KEY=${APISIX_ADMIN_KEY}

# Health Check Route
curl -X PUT "$APISIX_ADMIN_URL/apisix/admin/routes/mcp-health" \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mcp-health",
    "uri": "/mcp/health",
    "methods": ["GET"],
    "upstream": {
      "nodes": {
        "violentutf-api:8000": 1
      },
      "type": "roundrobin"
    },
    "plugins": {
      "cors": {
        "allow_origins": "*",
        "allow_methods": "GET",
        "allow_headers": "*"
      }
    }
  }'

# SSE Transport Route
curl -X PUT "$APISIX_ADMIN_URL/apisix/admin/routes/mcp-sse" \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mcp-sse",
    "uri": "/mcp/sse/*",
    "methods": ["GET", "POST", "OPTIONS"],
    "upstream": {
      "nodes": {
        "violentutf-api:8000": 1
      },
      "type": "roundrobin"
    },
    "plugins": {
      "cors": {
        "allow_origins": "*",
        "allow_methods": "GET,POST,OPTIONS",
        "allow_headers": "*",
        "allow_credentials": true
      },
      "rate-limit": {
        "count": 100,
        "time_window": 60,
        "rejected_code": 429
      }
    }
  }'

# OAuth Proxy Routes
curl -X PUT "$APISIX_ADMIN_URL/apisix/admin/routes/mcp-oauth" \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mcp-oauth",
    "uri": "/mcp/oauth/*",
    "methods": ["GET", "POST"],
    "upstream": {
      "nodes": {
        "violentutf-api:8000": 1
      },
      "type": "roundrobin"
    },
    "plugins": {
      "cors": {
        "allow_origins": "*",
        "allow_methods": "GET,POST",
        "allow_headers": "*"
      }
    }
  }'

echo "MCP routes configured successfully"
```

### Rate Limiting Configuration

```bash
# Advanced Rate Limiting for MCP Endpoints
curl -X PUT "$APISIX_ADMIN_URL/apisix/admin/routes/mcp-api" \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mcp-api",
    "uri": "/mcp/api/*",
    "methods": ["GET", "POST", "PUT", "DELETE"],
    "upstream": {
      "nodes": {
        "violentutf-api:8000": 1
      }
    },
    "plugins": {
      "rate-limit": {
        "count": 100,
        "time_window": 60,
        "rejected_code": 429,
        "rejected_msg": "Rate limit exceeded for MCP API"
      },
      "limit-conn": {
        "conn": 20,
        "burst": 10,
        "default_conn_delay": 0.1
      }
    }
  }'
```

## Client Configuration

### Claude Desktop Configuration

Add to Claude Desktop's configuration:

```json
{
  "mcpServers": {
    "violentutf": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sse"],
      "env": {
        "MCP_SERVER_URL": "http://localhost:9080/mcp/sse",
        "MCP_AUTH_TYPE": "oauth",
        "MCP_CLIENT_ID": "claude-desktop",
        "MCP_REDIRECT_URI": "http://localhost:3000/auth/callback"
      }
    }
  }
}
```

### Web Client Configuration

For web-based MCP clients:

```javascript
// MCP Client Configuration
const mcpConfig = {
  serverUrl: 'http://localhost:9080/mcp/sse',
  authType: 'oauth',
  clientId: 'web-client',
  redirectUri: 'http://localhost:3000/auth/callback',
  scopes: ['read:generators', 'write:generators', 'read:orchestrators', 'write:orchestrators'],
  transport: 'sse',
  timeout: 30000,
  retries: 3
};

// Initialize MCP Client
const mcpClient = new MCPClient(mcpConfig);
```

### Python Client Configuration

```python
import os
from mcp_client import MCPClient

# MCP Client Configuration
mcp_config = {
    'server_url': os.getenv('MCP_SERVER_URL', 'http://localhost:9080/mcp/sse'),
    'auth_type': 'oauth',
    'client_id': 'python-client',
    'client_secret': os.getenv('MCP_CLIENT_SECRET'),
    'timeout': 30,
    'retries': 3,
    'backoff_factor': 2.0
}

# Initialize client
client = MCPClient(**mcp_config)
```

## Security Configuration

### Authentication Settings

```bash
# Strong Authentication
MCP_REQUIRE_AUTH=true
MCP_TOKEN_VALIDATION=true
JWT_SECRET_KEY="your-strong-secret-key"  # Use 256-bit key
ALGORITHM="HS256"

# Token Expiration
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
API_KEY_EXPIRE_DAYS=365

# OAuth Security
OAUTH_STATE_TTL_SECONDS=600
OAUTH_CODE_TTL_SECONDS=300
OAUTH_PKCE_REQUIRED=true
```

### Network Security

```bash
# HTTPS Configuration (Production)
MCP_USE_HTTPS=true
MCP_SSL_CERT_PATH="/etc/ssl/certs/mcp.crt"
MCP_SSL_KEY_PATH="/etc/ssl/private/mcp.key"

# CORS Settings
MCP_CORS_ENABLED=true
MCP_CORS_ORIGINS="https://claude.ai,https://your-app.com"
MCP_CORS_ALLOW_CREDENTIALS=true

# Security Headers
MCP_SECURITY_HEADERS_ENABLED=true
MCP_HSTS_ENABLED=true
MCP_CSP_ENABLED=true
```

### Access Control

```bash
# Role-Based Access Control
MCP_RBAC_ENABLED=true
MCP_DEFAULT_USER_ROLE="user"
MCP_ADMIN_ROLE="admin"

# Resource Access Control
MCP_RESOURCE_ACCESS_CONTROL=true
MCP_GENERATOR_READ_ROLES="user,admin"
MCP_GENERATOR_WRITE_ROLES="admin"
MCP_ORCHESTRATOR_READ_ROLES="user,admin"
MCP_ORCHESTRATOR_WRITE_ROLES="admin"
```

## Performance Tuning

### Tool Execution Performance

```bash
# Tool Performance
MCP_TOOL_TIMEOUT_SECONDS=60
MCP_CONCURRENT_TOOL_LIMIT=10
MCP_TOOL_QUEUE_SIZE=100
MCP_TOOL_WORKER_THREADS=4

# Generator Tool Specific
MCP_GENERATOR_TEST_TIMEOUT=30
MCP_GENERATOR_BATCH_SIZE=10
MCP_GENERATOR_PARALLEL_TESTS=true

# Orchestrator Tool Specific
MCP_ORCHESTRATOR_STATUS_POLL_INTERVAL=5
MCP_ORCHESTRATOR_RESULT_BATCH_SIZE=100
MCP_ORCHESTRATOR_LOG_TAIL_LINES=1000
```

### Resource Management Performance

```bash
# Resource Caching
MCP_RESOURCE_CACHE_TTL=300
MCP_RESOURCE_CACHE_SIZE=1000
MCP_RESOURCE_CACHE_MEMORY_LIMIT="512MB"
MCP_RESOURCE_PREFETCH=true
MCP_RESOURCE_BACKGROUND_REFRESH=true

# Cache Eviction
MCP_CACHE_EVICTION_POLICY="lru"
MCP_CACHE_CLEANUP_INTERVAL=60
MCP_CACHE_MAX_AGE=3600

# Compression
MCP_RESOURCE_COMPRESSION=true
MCP_COMPRESSION_LEVEL=6
MCP_COMPRESSION_MIN_SIZE=1024
```

### Database Performance

```bash
# Connection Pooling
MCP_DB_POOL_SIZE=20
MCP_DB_MAX_OVERFLOW=30
MCP_DB_POOL_TIMEOUT=30
MCP_DB_POOL_RECYCLE=3600

# Query Optimization
MCP_DB_ECHO=false
MCP_DB_QUERY_TIMEOUT=30
MCP_DB_BATCH_SIZE=100
```

## Monitoring and Logging

### Logging Configuration

```bash
# Log Levels
MCP_LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
MCP_ACCESS_LOG_ENABLED=true
MCP_ERROR_LOG_ENABLED=true
MCP_PERFORMANCE_LOG_ENABLED=true

# Log Format
MCP_LOG_FORMAT="json"  # json, text
MCP_LOG_TIMESTAMP_FORMAT="iso"
MCP_LOG_INCLUDE_TRACE_ID=true

# Log Destinations
MCP_LOG_FILE_ENABLED=true
MCP_LOG_FILE_PATH="/var/log/violentutf/mcp.log"
MCP_LOG_ROTATION_SIZE="100MB"
MCP_LOG_ROTATION_COUNT=10

# Structured Logging
MCP_LOG_STRUCTURED=true
MCP_LOG_CORRELATION_ID=true
MCP_LOG_USER_CONTEXT=true
```

### Metrics Configuration

```bash
# Metrics Collection
MCP_METRICS_ENABLED=true
MCP_METRICS_PORT=9090
MCP_METRICS_PATH="/metrics"

# Prometheus Integration
MCP_PROMETHEUS_ENABLED=true
MCP_PROMETHEUS_NAMESPACE="violentutf_mcp"
MCP_PROMETHEUS_SUBSYSTEM="server"

# Custom Metrics
MCP_TOOL_EXECUTION_METRICS=true
MCP_RESOURCE_ACCESS_METRICS=true
MCP_AUTHENTICATION_METRICS=true
MCP_PERFORMANCE_METRICS=true
```

### Health Checks

```bash
# Health Check Configuration
MCP_HEALTH_CHECK_ENABLED=true
MCP_HEALTH_CHECK_PATH="/mcp/health"
MCP_HEALTH_CHECK_INTERVAL=30

# Component Health Checks
MCP_CHECK_DATABASE_HEALTH=true
MCP_CHECK_KEYCLOAK_HEALTH=true
MCP_CHECK_APISIX_HEALTH=true
MCP_CHECK_TOOL_REGISTRY_HEALTH=true
MCP_CHECK_RESOURCE_MANAGER_HEALTH=true

# Health Check Timeouts
MCP_HEALTH_CHECK_TIMEOUT=10
MCP_HEALTH_CHECK_RETRIES=3
```

## Environment-Specific Configurations

### Development Environment

```bash
# Development Settings
MCP_DEVELOPMENT_MODE=true
MCP_DEBUG_MODE=true
MCP_LOG_LEVEL="DEBUG"

# Relaxed Security (Development Only)
MCP_REQUIRE_AUTH=false
MCP_TOKEN_VALIDATION=false
MCP_CORS_ORIGINS="*"

# Performance (Development)
MCP_RESOURCE_CACHE_TTL=60
MCP_TOOL_TIMEOUT_SECONDS=30
MCP_CONCURRENT_TOOL_LIMIT=5

# Local URLs
KEYCLOAK_URL="http://localhost:8080"
APISIX_BASE_URL="http://localhost:9080"
VIOLENTUTF_API_URL="http://localhost:8000"
```

### Testing Environment

```bash
# Testing Configuration
MCP_TESTING_MODE=true
MCP_LOG_LEVEL="WARNING"
MCP_MOCK_EXTERNAL_SERVICES=true

# Test-Specific Settings
MCP_TEST_TOKEN_EXPIRY=3600
MCP_TEST_CACHE_DISABLED=true
MCP_TEST_RATE_LIMIT_DISABLED=true

# Test Database
DATABASE_URL="sqlite:///./test_mcp.db"
MCP_DB_ECHO=true
```

### Production Environment

```bash
# Production Settings
MCP_PRODUCTION_MODE=true
MCP_DEBUG_MODE=false
MCP_LOG_LEVEL="INFO"

# Security (Production)
MCP_REQUIRE_AUTH=true
MCP_TOKEN_VALIDATION=true
MCP_USE_HTTPS=true
MCP_SECURITY_HEADERS_ENABLED=true

# Performance (Production)
MCP_RESOURCE_CACHE_TTL=300
MCP_TOOL_TIMEOUT_SECONDS=60
MCP_CONCURRENT_TOOL_LIMIT=20
MCP_RESOURCE_CACHE_SIZE=5000

# High Availability
MCP_HEALTH_CHECK_ENABLED=true
MCP_METRICS_ENABLED=true
MCP_DISTRIBUTED_CACHE=true
```

## Troubleshooting Configuration

### Common Configuration Issues

**Issue: MCP server fails to start**
```bash
# Check configuration validity
python -c "from app.mcp.config import mcp_settings; print(mcp_settings.dict())"

# Verify environment variables
env | grep MCP_
```

**Issue: Authentication failures**
```bash
# Test Keycloak connectivity
curl -I $KEYCLOAK_URL/auth/realms/$KEYCLOAK_REALM

# Verify JWT secret
echo $JWT_SECRET_KEY | wc -c  # Should be 32+ characters
```

**Issue: APISIX route problems**
```bash
# Check APISIX routes
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     $APISIX_ADMIN_URL/apisix/admin/routes

# Test MCP endpoints
curl http://localhost:9080/mcp/health
```

### Configuration Validation

Create `scripts/validate-config.py`:

```python
#!/usr/bin/env python3
"""MCP Configuration Validator"""

import os
import sys
from typing import List

def validate_mcp_config() -> List[str]:
    """Validate MCP configuration and return list of issues"""
    issues = []
    
    # Required settings
    required_vars = [
        'JWT_SECRET_KEY',
        'KEYCLOAK_URL',
        'APISIX_BASE_URL'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f"Missing required environment variable: {var}")
    
    # JWT secret strength
    jwt_secret = os.getenv('JWT_SECRET_KEY', '')
    if len(jwt_secret) < 32:
        issues.append("JWT_SECRET_KEY should be at least 32 characters long")
    
    # URL format validation
    urls = {
        'KEYCLOAK_URL': os.getenv('KEYCLOAK_URL'),
        'APISIX_BASE_URL': os.getenv('APISIX_BASE_URL')
    }
    
    for name, url in urls.items():
        if url and not url.startswith(('http://', 'https://')):
            issues.append(f"{name} should start with http:// or https://")
    
    return issues

if __name__ == "__main__":
    issues = validate_mcp_config()
    if issues:
        print("Configuration Issues Found:")
        for issue in issues:
            print(f"  ❌ {issue}")
        sys.exit(1)
    else:
        print("✅ MCP configuration is valid")
```

### Performance Monitoring

Create monitoring configuration in `monitoring/mcp-monitoring.yml`:

```yaml
# Prometheus scrape configuration
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'violentutf-mcp'
    static_configs:
      - targets: ['violentutf-api:9090']
    metrics_path: '/metrics'
    scrape_interval: 30s
    
rule_files:
  - "mcp-alerts.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

---

*For API usage details, see [API Reference](./api-reference.md).*  
*For troubleshooting help, see [Troubleshooting Guide](./troubleshooting.md).*