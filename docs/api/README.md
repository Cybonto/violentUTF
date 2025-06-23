# API Documentation Hub

Technical documentation for the ViolentUTF API ecosystem, covering RESTful APIs, MCP server integration, and developer tooling.

## 🚀 Quick Start

```bash
# Setup and start API services
./setup_macos.sh

# Get authentication token
curl -X POST http://localhost:9080/api/v1/auth/token \
  -d "username=user&password=pass"

# Access API with token
curl -H "Authorization: Bearer TOKEN" \
     http://localhost:9080/api/v1/auth/me
```

## 📋 Documentation Index

### Core API Documentation
- **[🔐 Authentication](authentication.md)** - JWT, Keycloak SSO, API keys, and troubleshooting
- **[🛠️ Endpoints](endpoints.md)** - Complete API endpoint reference with examples
- **[🌐 APISIX Gateway](gateway.md)** - Gateway configuration and routing setup

### Integration & Development
- **[🔧 Framework Integration](frameworks.md)** - PyRIT and Garak integration patterns
- **[🧪 Testing Guide](testing.md)** - Unit, integration, and authentication testing
- **[🚀 Deployment](deployment.md)** - Docker setup and operational guidance

### Specialized APIs
- **[📡 MCP Server](mcp-client.md)** - Model Context Protocol server for tool access
- **[🔍 Audit API](audit_api.md)** - Security auditing and compliance features

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client Apps   │────▶│    APISIX    │────▶│  FastAPI    │
│  (CLI, Web)     │     │   Gateway    │     │   Service   │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │                      │
                               ▼                      ▼
                        ┌──────────────┐     ┌─────────────┐
                        │   Keycloak   │     │   PyRIT/    │
                        │     (SSO)     │     │   Garak     │
                        └──────────────┘     └─────────────┘
```

## 🔑 Base Configuration

### API Base URL
```
http://localhost:9080/api
```

### Core Endpoints
| Endpoint | Purpose | Documentation |
|----------|---------|---------------|
| `/health` | Service health check | [endpoints.md](endpoints.md#health) |
| `/api/v1/auth/*` | Authentication | [authentication.md](authentication.md) |
| `/api/v1/orchestrators/*` | PyRIT orchestrators | [endpoints.md](endpoints.md#pyrit) |
| `/api/v1/garak/*` | Garak security probes | [endpoints.md](endpoints.md#garak) |
| `/mcp/sse` | MCP server protocol | [mcp-client.md](mcp-client.md) |

## 🔧 Authentication Methods

### JWT Bearer Token (Primary)
```bash
# Get token
TOKEN=$(curl -X POST http://localhost:9080/api/v1/auth/token \
  -d "username=user&password=pass" | jq -r .access_token)

# Use token
curl -H "Authorization: Bearer $TOKEN" <endpoint>
```

### API Key (Automation)
```bash
# Create API key
python3 violentutf_api/jwt_cli.py keys create --name "automation"

# Use API key
curl -H "X-API-Key: YOUR_KEY" <endpoint>
```

## 📊 Rate Limiting & Security

- **Rate Limit**: 100 req/s (burst: 50), 1000 req/hour per IP
- **Authentication**: Required for all endpoints except `/health`
- **CORS**: Configured for localhost development
- **Headers**: APISIX gateway adds security headers

## 🛠️ Development Tools

### CLI Interface
```bash
# Authentication
python3 violentutf_api/jwt_cli.py login

# Operations
python3 violentutf_api/jwt_cli.py orchestrators list
python3 violentutf_api/jwt_cli.py datasets upload data.csv
```

### Interactive Documentation
- **Swagger UI**: http://localhost:9080/docs
- **ReDoc**: http://localhost:9080/redoc
- **OpenAPI Schema**: http://localhost:9080/openapi.json

## 🚨 Error Handling

Standard error format:
```json
{
  "detail": "Error description",
  "status_code": 400,
  "error_code": "INVALID_REQUEST"
}
```

Common status codes: `400` (Bad Request), `401` (Unauthorized), `403` (Forbidden), `404` (Not Found), `429` (Rate Limited), `500` (Server Error)

## 📖 Related Resources

- **[ViolentUTF Main Documentation](../../README.md)** - Platform overview and setup
- **[PyRIT Framework](https://github.com/Azure/PyRIT)** - Microsoft's risk identification toolkit
- **[Garak Documentation](https://garak.ai/)** - LLM vulnerability scanner
- **[APISIX Gateway](https://apisix.apache.org/)** - API gateway documentation

---

**⚠️ Security Notice**: This API provides access to security testing tools. Use only in authorized testing environments.