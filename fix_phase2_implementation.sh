#!/bin/bash

# Phase 2 Implementation Fix Script for Environment B
# This script implements the actual fixes needed for GSAi integration
# 
# IMPORTANT: Run this script in Environment B after pulling code from Environment A

set -euo pipefail

echo "=== Phase 2 Implementation Fixes for GSAi Integration ==="
echo "This script will fix the issues preventing GSAi integration"
echo

# Colors for output
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" -eq 0 ]; then
        echo -e "${GREEN}✅ $message${NC}"
    else
        echo -e "${RED}❌ $message${NC}"
    fi
}

# Check if we're in the right environment
if [ ! -f "ai-tokens.env" ]; then
    echo -e "${RED}❌ ai-tokens.env not found${NC}"
    echo "This script must be run in Environment B with GSAi configuration"
    exit 1
fi

# Load environment variables
echo "Loading environment configuration..."
source ai-tokens.env
source apisix/.env

# Validate GSAi configuration
if [ "$OPENAPI_1_ENABLED" != "true" ] || [ -z "$OPENAPI_1_ID" ]; then
    echo -e "${RED}❌ GSAi configuration not found in ai-tokens.env${NC}"
    exit 1
fi

print_status 0 "GSAi configuration loaded: $OPENAPI_1_ID"

echo
echo "Step 1: Fix Docker Compose Environment Variables"
echo "=============================================="

# Check if docker-compose.yml needs updating
if ! grep -q "APISIX_ADMIN_KEY" apisix/docker-compose.yml; then
    echo "Adding missing environment variables to docker-compose.yml..."
    
    # Create backup
    cp apisix/docker-compose.yml apisix/docker-compose.yml.backup
    
    # Add environment variables to FastAPI service
    cat > /tmp/docker-compose-patch.yml << 'EOF'
      # AI Provider Configuration (from ai-tokens.env)
      - OPENAI_ENABLED=${OPENAI_ENABLED:-false}
      - ANTHROPIC_ENABLED=${ANTHROPIC_ENABLED:-false}
      - OLLAMA_ENABLED=${OLLAMA_ENABLED:-false}
      - OPEN_WEBUI_ENABLED=${OPEN_WEBUI_ENABLED:-false}
      - OPENAPI_ENABLED=${OPENAPI_ENABLED:-true}
      # APISIX Admin
      - APISIX_ADMIN_KEY=${APISIX_ADMIN_KEY}
      # OpenAPI Provider 1 (GSAi)
      - OPENAPI_1_ENABLED=${OPENAPI_1_ENABLED:-false}
      - OPENAPI_1_ID=${OPENAPI_1_ID}
      - OPENAPI_1_NAME=${OPENAPI_1_NAME}
      - OPENAPI_1_BASE_URL=${OPENAPI_1_BASE_URL}
      - OPENAPI_1_AUTH_TYPE=${OPENAPI_1_AUTH_TYPE}
      - OPENAPI_1_AUTH_TOKEN=${OPENAPI_1_AUTH_TOKEN}
      - OPENAPI_1_MODELS=${OPENAPI_1_MODELS}
EOF
    
    # Find the line after APISIX_ADMIN_URL and insert the new variables
    awk '/APISIX_ADMIN_URL=http:\/\/apisix:9180/ {print; while(getline line<"/tmp/docker-compose-patch.yml") print line; next} 1' \
        apisix/docker-compose.yml > apisix/docker-compose.yml.new
    
    mv apisix/docker-compose.yml.new apisix/docker-compose.yml
    rm /tmp/docker-compose-patch.yml
    
    print_status 0 "Updated docker-compose.yml with environment variables"
else
    print_status 0 "docker-compose.yml already has environment variables"
fi

echo
echo "Step 2: Restart FastAPI Container with New Environment"
echo "===================================================="

echo "Restarting FastAPI container..."
cd apisix && docker compose up -d fastapi && cd ..
sleep 5

# Verify environment variables
echo "Verifying environment variables in container..."
for var in APISIX_ADMIN_KEY OPENAPI_1_ID OPENAPI_1_BASE_URL; do
    value=$(docker exec violentutf_api printenv "$var" 2>/dev/null || echo "NOT SET")
    if [ "$value" != "NOT SET" ] && [ -n "$value" ]; then
        if [[ "$var" == *"KEY"* ]] || [[ "$var" == *"TOKEN"* ]]; then
            print_status 0 "$var is set [${#value} chars]"
        else
            print_status 0 "$var: $value"
        fi
    else
        print_status 1 "$var is NOT SET"
    fi
done

echo
echo "Step 3: Fix APISIX Route Authentication Headers"
echo "=============================================="

# Fix route 3001 to include authentication headers
echo "Updating route 3001 with authentication headers..."

route_config=$(cat <<EOF
{
  "uri": "/openapi/gsai-api-1/*",
  "name": "openapi-gsai-api-1",
  "upstream": {
    "type": "roundrobin",
    "scheme": "https",
    "nodes": {
      "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
    }
  },
  "plugins": {
    "cors": {
      "allow_origins": "*",
      "allow_methods": "*",
      "allow_headers": "*",
      "expose_headers": "*",
      "max_age": 3600,
      "allow_credentials": true
    },
    "proxy-rewrite": {
      "regex_uri": ["^/openapi/gsai-api-1/(.*)", "/\$1"],
      "headers": {
        "set": {
          "Authorization": "Bearer ${OPENAPI_1_AUTH_TOKEN}"
        }
      }
    }
  }
}
EOF
)

# Update the route
response=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/3001" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d "$route_config" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$response" | grep -q '"id":"3001"'; then
    print_status 0 "Updated route 3001 with authentication headers"
else
    print_status 1 "Failed to update route 3001"
    echo "Response: $response"
fi

echo
echo "Step 4: Create Chat Completions Route"
echo "===================================="

# Create specific chat completions route
chat_route_config=$(cat <<EOF
{
  "uri": "/openapi/gsai-api-1/v1/chat/completions",
  "name": "openapi-gsai-api-1-chat",
  "methods": ["POST"],
  "upstream": {
    "type": "roundrobin",
    "scheme": "https",
    "nodes": {
      "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
    }
  },
  "plugins": {
    "cors": {
      "allow_origins": "*",
      "allow_methods": "*",
      "allow_headers": "*",
      "expose_headers": "*",
      "max_age": 3600,
      "allow_credentials": true
    },
    "proxy-rewrite": {
      "uri": "/api/v1/chat/completions",
      "headers": {
        "set": {
          "Authorization": "Bearer ${OPENAPI_1_AUTH_TOKEN}"
        }
      }
    }
  }
}
EOF
)

# Create the route
response=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/3002" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d "$chat_route_config" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$response" | grep -q '"id":"3002"'; then
    print_status 0 "Created chat completions route (ID: 3002)"
else
    print_status 1 "Failed to create chat completions route"
    echo "Response: $response"
fi

echo
echo "Step 5: Test Provider Discovery"
echo "==============================="

# Wait for container to fully restart
sleep 3

# Test if FastAPI can now discover providers
echo "Testing provider discovery through FastAPI..."
providers_response=$(curl -s "http://localhost:9080/api/v1/generators/apisix/openapi-providers" \
    -H "apikey: ${VIOLENTUTF_API_KEY}" 2>/dev/null || echo '[]')

provider_count=$(echo "$providers_response" | jq '. | length' 2>/dev/null || echo "0")

if [ "$provider_count" -gt 0 ]; then
    print_status 0 "Provider discovery working - found $provider_count provider(s)"
    echo "$providers_response" | jq -r '.[]' 2>/dev/null | head -5
else
    print_status 1 "Provider discovery still not working"
    
    # Additional debugging
    echo
    echo "Debugging information:"
    echo "1. Check if APISIX admin is accessible from FastAPI:"
    docker exec violentutf_api sh -c "curl -s -H 'X-API-KEY: $APISIX_ADMIN_KEY' http://apisix:9180/apisix/admin/routes" | jq '.list | length' 2>/dev/null || echo "Failed"
    
    echo "2. Check FastAPI logs:"
    docker logs violentutf_api --tail 20 2>&1 | grep -E "(OPENAPI|ERROR|WARNING)" || true
fi

echo
echo "Step 6: Test Model Discovery"
echo "==========================="

# Test model discovery for GSAi
echo "Testing model discovery for openapi-gsai-api-1..."
models_response=$(curl -s "http://localhost:9080/api/v1/generators/apisix/models?provider=openapi-gsai-api-1" \
    -H "apikey: ${VIOLENTUTF_API_KEY}" 2>/dev/null)

if echo "$models_response" | jq -e '.[0]' >/dev/null 2>&1; then
    model_count=$(echo "$models_response" | jq '. | length')
    print_status 0 "Model discovery working - found $model_count models"
else
    print_status 1 "Model discovery failed"
    echo "Response: $models_response"
fi

echo
echo "Step 7: Test Chat Completions"
echo "============================"

# Test the chat completions endpoint
echo "Testing chat completions endpoint..."
test_payload='{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 10}'

chat_response=$(curl -s -X POST "http://localhost:9080/openapi/gsai-api-1/v1/chat/completions" \
    -H "apikey: ${VIOLENTUTF_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "$test_payload" 2>/dev/null)

if echo "$chat_response" | jq -e '.choices' >/dev/null 2>&1; then
    print_status 0 "Chat completions endpoint working!"
    echo "Response: $(echo "$chat_response" | jq -r '.choices[0].message.content' 2>/dev/null | head -1)"
else
    print_status 1 "Chat completions endpoint not working"
    echo "Response: $chat_response"
fi

echo
echo "=== Phase 2 Implementation Summary ==="

echo
echo "Actions taken:"
echo "1. Added environment variables to docker-compose.yml"
echo "2. Restarted FastAPI with proper configuration"
echo "3. Updated APISIX routes with authentication headers"
echo "4. Created chat completions route"
echo
echo "Next steps:"
echo "1. If provider discovery is still failing, check FastAPI logs"
echo "2. Verify in the web UI that GSAi appears in the provider dropdown"
echo "3. Try creating a generator with GSAi provider"
echo "4. Run test_gsai_integration.sh again to verify all fixes"