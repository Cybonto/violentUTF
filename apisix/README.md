# APISIX Gateway for ViolentUTF

APISIX API Gateway provides secure routing, authentication, and AI model proxy capabilities for the ViolentUTF platform.

## Quick Start

```bash
# Start APISIX services
docker-compose up -d

# Configure routes
./configure_routes.sh

# Verify setup
./verify_routes.sh
```

## Key Features

- **AI Model Proxy**: Route requests to OpenAI, Anthropic, Ollama, and Open WebUI
- **Authentication**: Keycloak SSO integration with JWT validation
- **Rate Limiting**: Configurable limits for API protection
- **Security**: TLS termination and security headers

## Configuration Files

- `docker-compose.yml` - Service definitions
- `conf/config.yaml` - APISIX configuration
- `configure_routes.sh` - Route setup automation
- `apisix-gateway-auth.lua` - Custom authentication plugin

## Documentation

For detailed setup, configuration, and troubleshooting information, see:

**📚 [Complete Documentation](../docs/API6_setup.md)**

## Environment Setup

Copy `env.sample` to `.env` and configure your API keys and endpoints before starting services.