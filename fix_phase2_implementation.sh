#!/bin/bash

# Phase 2 Implementation Fix Script for Environment B
# This script implements the actual fixes needed for GSAi integration
# 
# IMPORTANT: Run this script in Environment B from the ViolentUTF root directory

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

# Check current directory
if [ ! -f "ai-tokens.env" ] || [ ! -d "apisix" ]; then
    echo -e "${RED}❌ This script must be run from the ViolentUTF root directory${NC}"
    echo "Current directory: $(pwd)"
    echo "Please cd to the ViolentUTF root directory and try again"
    exit 1
fi

# Important: Use the MAIN ai-tokens.env, not the one in apisix/
echo "Checking for environment files..."
if [ -f "./ai-tokens.env" ]; then
    print_status 0 "Found main ai-tokens.env in current directory"
else
    echo -e "${RED}❌ Main ai-tokens.env not found in current directory${NC}"
    exit 1
fi


# Load ALL environment variables properly from the CORRECT locations
echo
echo "Loading environment configuration..."
set -a  # Export all variables

# Load main ai-tokens.env from root directory
if [ -f "./ai-tokens.env" ]; then
    echo "Loading ./ai-tokens.env (main configuration)..."
    source "./ai-tokens.env"
fi

# Load APISIX configuration
if [ -f "./apisix/.env" ]; then
    echo "Loading ./apisix/.env..."
    source "./apisix/.env"
fi

# Load FastAPI configuration
if [ -f "./violentutf_api/fastapi_app/.env" ]; then
    echo "Loading ./violentutf_api/fastapi_app/.env..."
    source "./violentutf_api/fastapi_app/.env"
fi

set +a  # Stop exporting

# Validate GSAi configuration
if [ "${OPENAPI_1_ENABLED:-}" != "true" ] || [ -z "${OPENAPI_1_ID:-}" ]; then
    echo -e "${RED}❌ GSAi configuration not found in ai-tokens.env${NC}"
    echo "Please ensure OPENAPI_1_* variables are set in ./ai-tokens.env"
    echo "Current values:"
    echo "  OPENAPI_1_ENABLED=${OPENAPI_1_ENABLED:-NOT SET}"
    echo "  OPENAPI_1_ID=${OPENAPI_1_ID:-NOT SET}"
    exit 1
fi

# Validate critical variables
if [ -z "${APISIX_ADMIN_KEY:-}" ]; then
    echo -e "${RED}❌ APISIX_ADMIN_KEY not found${NC}"
    echo "Please check ./apisix/.env"
    exit 1
fi

if [ -z "${VIOLENTUTF_API_KEY:-}" ]; then
    echo -e "${YELLOW}⚠️  VIOLENTUTF_API_KEY not found, checking default${NC}"
    # Try to get it from FastAPI .env or use known default
    if [ -z "${VIOLENTUTF_API_KEY:-}" ]; then
        VIOLENTUTF_API_KEY="CHbp3Tmw3COxM6LZwHrSC1skXTWaSiyR"
        echo "Using default VIOLENTUTF_API_KEY"
    fi
fi

print_status 0 "GSAi configuration loaded: $OPENAPI_1_ID"
print_status 0 "Environment variables loaded successfully"

# Debug: Show which ai-tokens.env values we loaded
echo
echo "Loaded GSAi configuration:"
echo "  OPENAPI_ENABLED: ${OPENAPI_ENABLED:-NOT SET}"
echo "  OPENAPI_1_ENABLED: ${OPENAPI_1_ENABLED:-NOT SET}"
echo "  OPENAPI_1_ID: ${OPENAPI_1_ID:-NOT SET}"
echo "  OPENAPI_1_NAME: ${OPENAPI_1_NAME:-NOT SET}"
echo "  OPENAPI_1_BASE_URL: ${OPENAPI_1_BASE_URL:-NOT SET}"
echo "  OPENAPI_1_AUTH_TYPE: ${OPENAPI_1_AUTH_TYPE:-NOT SET}"
echo "  OPENAPI_1_AUTH_TOKEN: [${#OPENAPI_1_AUTH_TOKEN} chars]"

echo
echo "Step 1: Create Docker Compose Override File"
echo "=========================================="

# Create override file with environment variables
cat > apisix/docker-compose.override.yml << EOF
# Auto-generated override file for GSAi integration
# Generated on: $(date)
# This file is automatically loaded by docker-compose

services:
  fastapi:
    environment:
      # AI Provider Configuration
      - OPENAI_ENABLED=${OPENAI_ENABLED:-false}
      - ANTHROPIC_ENABLED=${ANTHROPIC_ENABLED:-false}
      - OLLAMA_ENABLED=${OLLAMA_ENABLED:-false}
      - OPEN_WEBUI_ENABLED=${OPEN_WEBUI_ENABLED:-false}
      - OPENAPI_ENABLED=${OPENAPI_ENABLED:-true}
      # APISIX Admin
      - APISIX_ADMIN_KEY=${APISIX_ADMIN_KEY}
      # OpenAPI Provider 1 (GSAi)
      - OPENAPI_1_ENABLED=${OPENAPI_1_ENABLED}
      - OPENAPI_1_ID=${OPENAPI_1_ID}
      - OPENAPI_1_NAME=${OPENAPI_1_NAME}
      - OPENAPI_1_BASE_URL=${OPENAPI_1_BASE_URL}
      - OPENAPI_1_AUTH_TYPE=${OPENAPI_1_AUTH_TYPE}
      - OPENAPI_1_AUTH_TOKEN=${OPENAPI_1_AUTH_TOKEN}
      - OPENAPI_1_MODELS=${OPENAPI_1_MODELS:-}
      # Additional OpenAPI providers if needed
      - OPENAPI_2_ENABLED=${OPENAPI_2_ENABLED:-false}
      - OPENAPI_3_ENABLED=${OPENAPI_3_ENABLED:-false}
      - OPENAPI_4_ENABLED=${OPENAPI_4_ENABLED:-false}
EOF

print_status 0 "Created docker-compose.override.yml with environment variables"

echo
echo "Step 2: Restart FastAPI Container"
echo "================================="

echo "Stopping FastAPI container..."
cd apisix
docker compose stop fastapi

echo "Starting FastAPI container with new configuration..."
docker compose up -d fastapi
cd ..

# Wait for container to fully start
echo "Waiting for container to start..."
for i in {1..30}; do
    if docker exec violentutf_api curl -s http://localhost:8000/api/health &>/dev/null; then
        echo
        print_status 0 "FastAPI service is ready"
        break
    fi
    echo -n "."
    sleep 2
done
echo

# Check if container is actually running and healthy
container_status=$(docker inspect violentutf_api --format='{{.State.Status}}' 2>/dev/null || echo "not found")
if [ "$container_status" != "running" ]; then
    print_status 1 "FastAPI container is not running (status: $container_status)"
    echo "Container logs:"
    docker logs violentutf_api --tail 50
    exit 1
fi

# Extra wait for service initialization
echo "Waiting for service initialization..."
sleep 5

# Verify environment variables in container
echo "Verifying environment variables in container..."
for var in APISIX_ADMIN_KEY OPENAPI_ENABLED OPENAPI_1_ENABLED OPENAPI_1_ID OPENAPI_1_BASE_URL; do
    value=$(docker exec violentutf_api printenv "$var" 2>/dev/null || echo "NOT SET")
    if [ "$value" != "NOT SET" ] && [ -n "$value" ]; then
        if [[ "$var" == *"KEY"* ]] || [[ "$var" == *"TOKEN"* ]]; then
            print_status 0 "$var is set [${#value} chars]"
        else
            print_status 0 "$var: $value"
        fi
    else
        print_status 1 "$var is NOT SET in container"
    fi
done

echo
echo "Step 3: Fix APISIX Route Authentication"
echo "======================================"

# Extract hostname from BASE_URL
GSAI_HOST=$(echo "${OPENAPI_1_BASE_URL}" | sed -E 's|https?://([^/]+).*|\1|')
echo "GSAi host: $GSAI_HOST"

# Update route 3001 with authentication headers
echo "Updating route 3001 with authentication headers..."

route_config=$(cat <<EOF
{
  "uri": "/openapi/${OPENAPI_1_ID}/*",
  "name": "openapi-${OPENAPI_1_ID}",
  "upstream": {
    "type": "roundrobin",
    "scheme": "https",
    "nodes": {
      "${GSAI_HOST}:443": 1
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
      "regex_uri": ["^/openapi/${OPENAPI_1_ID}/(.*)", "/\$1"],
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
    print_status 0 "Updated route 3001 with authentication"
else
    print_status 1 "Failed to update route 3001"
    echo "Response: $response" | jq . 2>/dev/null || echo "$response"
fi

echo
echo "Step 4: Test Provider Discovery"
echo "==============================="

# Wait for services to stabilize
sleep 3

# First, test if FastAPI can reach APISIX admin
echo "Testing FastAPI → APISIX admin connectivity..."
admin_test=$(docker exec violentutf_api sh -c "curl -s --max-time 5 -o /dev/null -w '%{http_code}' -H 'X-API-KEY: ${APISIX_ADMIN_KEY}' http://apisix:9180/apisix/admin/routes" 2>/dev/null || echo "000")

if [ "$admin_test" = "200" ]; then
    print_status 0 "FastAPI can reach APISIX admin API"
else
    print_status 1 "FastAPI cannot reach APISIX admin (HTTP $admin_test)"
fi

# Test provider discovery
echo
echo "Testing provider discovery..."
provider_count=0
providers_response=$(curl -s --max-time 10 "http://localhost:9080/api/v1/generators/apisix/openapi-providers" \
    -H "X-API-Key: ${VIOLENTUTF_API_KEY}" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$providers_response" | jq -e '.[0]' >/dev/null 2>&1; then
    provider_count=$(echo "$providers_response" | jq '. | length' 2>/dev/null || echo "0")
    print_status 0 "Provider discovery working - found $provider_count provider(s)"
    echo "Providers:"
    echo "$providers_response" | jq -r '.[] | "  - \(.id): \(.name)"' 2>/dev/null || echo "  Failed to parse"
else
    print_status 1 "Provider discovery not working"
    echo "Response: $providers_response" | head -100
    
    # Additional debugging
    echo
    echo "Debugging: Checking container environment..."
    docker exec violentutf_api sh -c 'env | grep -E "^(OPENAPI|APISIX_ADMIN)" | sort' | head -20
    
    # Check FastAPI logs for errors
    echo
    echo "Checking FastAPI logs for errors..."
    docker logs violentutf_api --tail 20 2>&1 | grep -E "(ERROR|WARNING|openapi)" || echo "No relevant logs found"
fi

echo
echo "Step 5: Test Model Discovery"
echo "==========================="

if [ "${provider_count:-0}" -gt 0 ]; then
    echo "Testing model discovery for openapi-${OPENAPI_1_ID}..."
    models_response=$(curl -s --max-time 10 "http://localhost:9080/api/v1/generators/apisix/models?provider=openapi-${OPENAPI_1_ID}" \
        -H "X-API-Key: ${VIOLENTUTF_API_KEY}" 2>/dev/null || echo '{"error": "Failed"}')

    if echo "$models_response" | jq -e '.[0]' >/dev/null 2>&1; then
        model_count=$(echo "$models_response" | jq '. | length' 2>/dev/null || echo "0")
        print_status 0 "Model discovery working - found $model_count models"
        echo "Sample models:"
        echo "$models_response" | jq -r '.[:3][]' 2>/dev/null | head -5
    else
        print_status 1 "Model discovery failed"
        echo "Response: $models_response" | head -100
    fi
else
    echo "Skipping model discovery test (no providers found)"
fi

echo
echo "=== Phase 2 Implementation Summary ==="
echo
echo "Actions completed:"
echo "1. Created docker-compose.override.yml with GSAi environment variables"
echo "2. Restarted FastAPI container with new configuration"
echo "3. Updated APISIX route 3001 with authentication headers"
echo
echo
echo "Next steps:"
echo "1. Check the Streamlit UI at http://localhost:8501"
echo "2. GSAi should now appear in the AI provider dropdown"
echo "3. Try creating a generator with provider 'openapi-${OPENAPI_1_ID}'"
echo "4. Check logs if issues persist: docker logs violentutf_api --tail 50"
echo
echo "To verify the fix worked:"
echo "  ./test_gsai_integration.sh"
echo
echo "To remove the override file and revert:"
echo "  rm apisix/docker-compose.override.yml"
echo "  cd apisix && docker compose restart fastapi"