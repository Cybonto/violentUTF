#!/bin/bash

# Simple GSAi Route Creation Script
# This treats GSAi like a traditional AI provider with static authentication

set -eo pipefail

echo "=== Creating Simple GSAi Route (Static Authentication) ==="
echo "This approach treats GSAi like OpenAI/Anthropic with static token"
echo

# Load environment variables from all relevant files
echo "Loading environment configuration..."
set -a  # Export all variables

# Load main ai-tokens.env
if [ -f "./ai-tokens.env" ]; then
    echo "Loading ./ai-tokens.env..."
    source "./ai-tokens.env"
fi

# Load APISIX configuration (where APISIX_ADMIN_KEY is stored)
if [ -f "./apisix/.env" ]; then
    echo "Loading ./apisix/.env..."
    source "./apisix/.env"
fi

# Load FastAPI configuration
if [ -f "./violentutf_api/fastapi_app/.env" ]; then
    echo "Loading ./violentutf_api/fastapi_app/.env..."
    source "./violentutf_api/fastapi_app/.env"
fi

# Load ViolentUTF configuration
if [ -f "./violentutf/.env" ]; then
    echo "Loading ./violentutf/.env..."
    source "./violentutf/.env"
fi

set +a  # Stop exporting

# Debug: Show which files exist
echo
echo "Environment files status:"
[ -f "./ai-tokens.env" ] && echo "✅ ./ai-tokens.env exists" || echo "❌ ./ai-tokens.env missing"
[ -f "./apisix/.env" ] && echo "✅ ./apisix/.env exists" || echo "❌ ./apisix/.env missing"
[ -f "./violentutf_api/fastapi_app/.env" ] && echo "✅ ./violentutf_api/fastapi_app/.env exists" || echo "❌ ./violentutf_api/fastapi_app/.env missing"
[ -f "./violentutf/.env" ] && echo "✅ ./violentutf/.env exists" || echo "❌ ./violentutf/.env missing"

# Validate GSAi configuration
echo
echo "Validating configuration..."
if [ -z "${OPENAPI_1_AUTH_TOKEN:-}" ]; then
    echo "❌ OPENAPI_1_AUTH_TOKEN not found in environment files"
    echo "Please check that OPENAPI_1_AUTH_TOKEN is set in ./ai-tokens.env"
    exit 1
fi

if [ -z "${APISIX_ADMIN_KEY:-}" ]; then
    echo "❌ APISIX_ADMIN_KEY not found in environment files"
    echo "Please check that APISIX_ADMIN_KEY is set in ./apisix/.env"
    echo "You can also try: export APISIX_ADMIN_KEY=\$(grep APISIX_ADMIN_KEY ./apisix/.env | cut -d'=' -f2)"
    exit 1
fi

echo "✅ Configuration loaded:"
echo "  GSAi Token: [REDACTED - ${#OPENAPI_1_AUTH_TOKEN} chars]"
echo "  APISIX Key: [REDACTED - ${#APISIX_ADMIN_KEY} chars]"
echo

# Create static GSAi route using ai-proxy plugin (like OpenAI/Anthropic)
echo "Creating static GSAi route with ai-proxy plugin..."

static_gsai_route='{
  "id": "9001",
  "uri": "/ai/gsai/chat/completions",
  "name": "gsai-static-chat-completions",
  "methods": ["POST"],
  "upstream": {
    "type": "roundrobin",
    "scheme": "https",
    "nodes": {
      "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
    },
    "tls": {
      "verify": false
    }
  },
  "plugins": {
    "key-auth": {
      "header": "X-API-Key"
    },
    "ai-proxy": {
      "provider": "openai-compatible",
      "auth": {
        "header": {
          "Authorization": "Bearer '"${OPENAPI_1_AUTH_TOKEN}"'"
        }
      },
      "override": {
        "endpoint": "https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/chat/completions"
      },
      "options": {
        "model": "claude_3_5_sonnet"
      },
      "ssl_verify": false
    },
    "cors": {
      "allow_origins": "*",
      "allow_methods": "*",
      "allow_headers": "*",
      "expose_headers": "*",
      "max_age": 3600,
      "allow_credentials": true
    }
  }
}'

# Create the route
echo "Sending route configuration to APISIX..."
response=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/9001" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d "$static_gsai_route" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$response" | grep -q '"id":"9001"'; then
    echo "✅ Created static GSAi route (ID: 9001)"
    echo "✅ Endpoint: http://localhost:9080/ai/gsai/chat/completions"
else
    echo "❌ Failed to create GSAi route"
    # Redact any sensitive data from response
    redacted_response=$(echo "$response" | sed -E 's/"Authorization": "Bearer [^"]+"/Authorization": "Bearer [REDACTED]"/g')
    echo "Response: $redacted_response" | jq . 2>/dev/null || echo "$redacted_response"
    exit 1
fi

# Create static GSAi models route
echo
echo "Creating static GSAi models route..."

echo "Debug: OPENAPI_1_AUTH_TOKEN length: ${#OPENAPI_1_AUTH_TOKEN}"

static_gsai_models_route='{
  "id": "9002", 
  "uri": "/ai/gsai/models",
  "name": "gsai-static-models",
  "methods": ["GET"],
  "upstream": {
    "type": "roundrobin",
    "scheme": "https",
    "nodes": {
      "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
    },
    "pass_host": "pass",
    "upstream_host": "api.dev.gsai.mcaas.fcs.gsa.gov"
  },
  "plugins": {
    "key-auth": {
      "header": "X-API-Key"
    },
    "proxy-rewrite": {
      "uri": "/api/v1/models",
      "method": "GET",
      "headers": {
        "set": {
          "Authorization": "Bearer '"${OPENAPI_1_AUTH_TOKEN}"'",
          "Content-Length": "0"
        },
        "remove": ["Content-Type"]
      }
    },
    "cors": {
      "allow_origins": "*",
      "allow_methods": "*", 
      "allow_headers": "*",
      "expose_headers": "*",
      "max_age": 3600,
      "allow_credentials": true
    }
  }
}'

echo "Debug: JSON payload for route 9002:"
echo "$static_gsai_models_route" | jq . 2>/dev/null || echo "Invalid JSON: $static_gsai_models_route"

response=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/9002" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d "$static_gsai_models_route" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$response" | grep -q '"id":"9002"'; then
    echo "✅ Created static GSAi models route (ID: 9002)"
    echo "✅ Endpoint: http://localhost:9080/ai/gsai/models"
else
    echo "❌ Failed to create GSAi models route"
    # Redact any sensitive data from response
    redacted_response=$(echo "$response" | sed -E 's/"Authorization": "Bearer [^"]+"/Authorization": "Bearer [REDACTED]"/g')
    echo "Response: $redacted_response" | jq . 2>/dev/null || echo "$redacted_response"
fi

echo
echo "=== Static GSAi Routes Created ==="
echo
echo "✅ GSAi is now configured like OpenAI/Anthropic with static authentication!"
echo "✅ No JWT/Keycloak dependency for API calls"
echo "✅ Uses simple API key authentication via APISIX gateway"
echo
echo "Test your routes:"
echo "1. Chat completions: curl -H 'X-API-Key: YOUR_VIOLENTUTF_API_KEY' http://localhost:9080/ai/gsai/chat/completions"
echo "2. Models: curl -H 'X-API-Key: YOUR_VIOLENTUTF_API_KEY' http://localhost:9080/ai/gsai/models"
echo
echo "Now GSAi works just like OpenAI/Anthropic - no complex authentication needed!"