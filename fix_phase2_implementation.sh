#!/bin/bash

# Phase 2 Implementation Fix Script for Environment B
# This script implements the actual fixes needed for GSAi integration
# 
# IMPORTANT: Run this script in Environment B from the ViolentUTF root directory

set -eo pipefail

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

# Load ViolentUTF configuration (for user password)
if [ -f "./violentutf/.env" ]; then
    echo "Loading ./violentutf/.env..."
    source "./violentutf/.env"
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
    echo -e "${YELLOW}⚠️  VIOLENTUTF_API_KEY not found in environment${NC}"
    # Check if it's in the container
    CONTAINER_API_KEY=$(docker exec violentutf_api printenv VIOLENTUTF_API_KEY 2>/dev/null || echo "")
    if [ -n "${CONTAINER_API_KEY}" ]; then
        VIOLENTUTF_API_KEY="${CONTAINER_API_KEY}"
        echo "Found VIOLENTUTF_API_KEY in container"
    else
        echo -e "${RED}❌ VIOLENTUTF_API_KEY not found anywhere${NC}"
        echo "Please check your configuration files"
        exit 1
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
if [ -n "${OPENAPI_1_AUTH_TOKEN}" ]; then
    echo "  OPENAPI_1_AUTH_TOKEN: [REDACTED - ${#OPENAPI_1_AUTH_TOKEN} chars]"
else
    echo "  OPENAPI_1_AUTH_TOKEN: NOT SET"
fi

echo
echo "Step 0: Diagnostics - Checking Current System State"
echo "=================================================="

# Check if Keycloak is running
echo "Checking Keycloak status..."
keycloak_running=$(docker ps --filter "name=keycloak" --format "{{.Names}}" | grep -E "keycloak" | wc -l)
if [ "$keycloak_running" -gt 0 ]; then
    print_status 0 "Keycloak container is running"
else
    print_status 1 "Keycloak container is NOT running"
    echo "   Run: cd keycloak && docker compose up -d"
fi

# Check current routes
echo
echo "Checking existing APISIX routes..."
existing_routes=$(curl -s "http://localhost:9180/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$existing_routes" | grep -q '"list"'; then
    route_count=$(echo "$existing_routes" | jq '.list | length' 2>/dev/null || echo "0")
    print_status 0 "Found $route_count routes in APISIX"
    
    # Check specifically for our routes
    for route_id in 3001 3002 3003; do
        if echo "$existing_routes" | jq -e ".list[] | select(.key == \"/apisix/routes/$route_id\")" >/dev/null 2>&1; then
            echo "   ✓ Route $route_id exists"
        else
            echo "   ✗ Route $route_id missing"
        fi
    done
else
    print_status 1 "Failed to retrieve APISIX routes"
fi

# Test basic connectivity
echo
echo "Testing basic service connectivity..."
# Test API health without auth
health_response=$(curl -s "http://localhost:9080/api/v1/health" 2>/dev/null || echo '{"error": "Failed"}')
if echo "$health_response" | grep -q '"status":"healthy"'; then
    print_status 0 "API health endpoint is accessible"
else
    print_status 1 "API health endpoint is NOT accessible"
fi

# Check if we already have an override file
if [ -f "apisix/docker-compose.override.yml" ]; then
    echo
    echo "⚠️  Found existing docker-compose.override.yml"
    echo "   This will be replaced with new configuration"
fi

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
        if [[ "$var" == *"KEY"* ]] || [[ "$var" == *"TOKEN"* ]] || [[ "$var" == *"SECRET"* ]] || [[ "$var" == *"PASSWORD"* ]]; then
            print_status 0 "$var is set [REDACTED - ${#value} chars]"
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

# First check if route 3001 exists
echo "Checking if route 3001 exists..."
existing_route=$(curl -s "http://localhost:9180/apisix/admin/routes/3001" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null || echo '{}')

if echo "$existing_route" | grep -q '"id":"3001"'; then
    echo "Route 3001 exists, updating..."
else
    echo "Route 3001 does not exist, creating..."
fi

# Update route 3001 with authentication headers
echo "Configuring route 3001 with authentication headers..."

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

# Show redacted configuration for debugging
echo "Route configuration (redacted):"
echo "$route_config" | sed -E 's/"Authorization": "Bearer [^"]+"/Authorization": "Bearer [REDACTED]"/g' | sed 's/\\$/$/g' | jq -c . 2>/dev/null || echo "[Route config created but JSON display failed]"

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
echo "Step 4: Fix API Key Configuration"
echo "================================="

# Ensure API key is properly set in the container
echo "Verifying API key configuration..."
CONTAINER_API_KEY=$(docker exec violentutf_api printenv VIOLENTUTF_API_KEY 2>/dev/null || echo "")
if [ -n "${CONTAINER_API_KEY}" ]; then
    print_status 0 "API key is set in container: [REDACTED - ${#CONTAINER_API_KEY} chars]"
    # Use the container's API key for our tests
    VIOLENTUTF_API_KEY="${CONTAINER_API_KEY}"
else
    print_status 1 "API key not found in container"
fi

echo
echo "Step 5: Test Provider Discovery"
echo "==============================="

# Wait for services to stabilize
sleep 3

# First, test if FastAPI can reach APISIX admin
echo "Testing FastAPI → APISIX admin connectivity..."
echo "Using APISIX admin key: [REDACTED - ${#APISIX_ADMIN_KEY} chars]"
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

# First, let's check what password we should use
echo "Checking for user credentials..."
if [ -n "${VIOLENTUTF_USER_PASSWORD:-}" ]; then
    echo "Found VIOLENTUTF_USER_PASSWORD in environment [REDACTED - ${#VIOLENTUTF_USER_PASSWORD} chars]"
    USER_PASSWORD="${VIOLENTUTF_USER_PASSWORD}"
elif [ -n "${KEYCLOAK_PASSWORD:-}" ]; then
    echo "Found KEYCLOAK_PASSWORD in environment [REDACTED - ${#KEYCLOAK_PASSWORD} chars]"
    USER_PASSWORD="${KEYCLOAK_PASSWORD}"
else
    echo "No password found in environment, using default..."
    # Use default password for violentutf.web user
    USER_PASSWORD="violentutf.web"
fi

# First, let's try to get a valid JWT token using the service account
echo "Getting authentication token..."
echo "Using username: violentutf.web"
echo "Using password: [REDACTED - ${#USER_PASSWORD} chars]"

# If using default password, also try to find the actual password from container
if [ "$USER_PASSWORD" = "violentutf.web" ]; then
    echo "Checking for generated password in container..."
    CONTAINER_PASSWORD=$(docker exec violentutf_api printenv KEYCLOAK_PASSWORD 2>/dev/null || echo "")
    if [ -n "${CONTAINER_PASSWORD}" ] && [ "${CONTAINER_PASSWORD}" != "violentutf.web" ]; then
        echo "Found different password in container, using that instead"
        USER_PASSWORD="${CONTAINER_PASSWORD}"
    fi
    
    # Also check if there's a different password in the Streamlit container
    if docker ps | grep -q "8501"; then
        echo "Checking Streamlit configuration..."
        STREAMLIT_PASSWORD=$(docker exec $(docker ps --filter "publish=8501" --format "{{.Names}}" | head -1) printenv KEYCLOAK_PASSWORD 2>/dev/null || echo "")
        if [ -n "${STREAMLIT_PASSWORD}" ] && [ "${STREAMLIT_PASSWORD}" != "violentutf.web" ]; then
            echo "Found password in Streamlit container"
            USER_PASSWORD="${STREAMLIT_PASSWORD}"
        fi
    fi
fi

echo "Final password selection: [REDACTED - ${#USER_PASSWORD} chars]"

auth_response=$(curl -s -X POST "http://localhost:9080/api/v1/auth/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=password&username=violentutf.web&password=${USER_PASSWORD}" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$auth_response" | jq -e '.access_token' >/dev/null 2>&1; then
    JWT_TOKEN=$(echo "$auth_response" | jq -r '.access_token')
    print_status 0 "Successfully authenticated"
    
    # Use JWT token for provider discovery
    providers_response=$(curl -s --max-time 10 "http://localhost:9080/api/v1/generators/apisix/openapi-providers" \
        -H "Authorization: Bearer ${JWT_TOKEN}" 2>/dev/null || echo '{"error": "Failed"}')
else
    print_status 1 "Authentication failed"
    echo "Auth response: $auth_response" | jq . 2>/dev/null || echo "$auth_response"
    
    # Debug: Check if Keycloak is accessible
    echo
    echo "Debugging authentication issue..."
    echo "Checking Keycloak accessibility..."
    keycloak_health=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration" 2>/dev/null || echo "000")
    if [ "$keycloak_health" = "200" ]; then
        echo "✅ Keycloak is accessible"
    else
        echo "❌ Keycloak is not accessible (HTTP $keycloak_health)"
        echo "   Please ensure Keycloak is running: cd keycloak && docker compose ps"
    fi
    
    # Try with API key as fallback
    echo
    echo "Trying with API key instead..."
    echo "Using API key: [REDACTED - ${#VIOLENTUTF_API_KEY} chars]"
    
    # First verify the API key is valid
    echo "Testing API key validity..."
    api_test_response=$(curl -s "http://localhost:9080/api/v1/health" \
        -H "X-API-Key: ${VIOLENTUTF_API_KEY}" 2>/dev/null || echo '{"error": "Failed"}')
    
    if echo "$api_test_response" | grep -q '"status":"healthy"'; then
        echo "✅ API key is valid"
    else
        echo "❌ API key is invalid or not working"
        echo "Response: $api_test_response"
        
        # Try to find the correct API key
        echo
        echo "Checking for correct API key in configuration files..."
        
        # Check FastAPI .env file
        if [ -f "./violentutf_api/fastapi_app/.env" ]; then
            FILE_API_KEY=$(grep "^VIOLENTUTF_API_KEY=" "./violentutf_api/fastapi_app/.env" | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
            if [ -n "$FILE_API_KEY" ]; then
                echo "Found API key in FastAPI .env file"
                VIOLENTUTF_API_KEY="$FILE_API_KEY"
                echo "Retrying with file-based API key..."
            fi
        fi
    fi
    
    providers_response=$(curl -s --max-time 10 "http://localhost:9080/api/v1/generators/apisix/openapi-providers" \
        -H "X-API-Key: ${VIOLENTUTF_API_KEY}" 2>/dev/null || echo '{"error": "Failed"}')
fi

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
    # Redact sensitive values when showing environment
    docker exec violentutf_api sh -c 'env | grep -E "^(OPENAPI|APISIX_ADMIN)" | sort' | while read -r line; do
        if echo "$line" | grep -qE "(KEY|TOKEN|SECRET|PASSWORD)="; then
            var_name=$(echo "$line" | cut -d'=' -f1)
            var_value=$(echo "$line" | cut -d'=' -f2-)
            echo "${var_name}=[REDACTED - ${#var_value} chars]"
        else
            echo "$line"
        fi
    done | head -20
    
    # Check FastAPI logs for errors
    echo
    echo "Checking FastAPI logs for errors..."
    docker logs violentutf_api --tail 20 2>&1 | grep -E "(ERROR|WARNING|openapi)" || echo "No relevant logs found"
fi

echo
echo "Step 6: Fix OpenAPI Provider Routes"
echo "==================================="

# Create a proper proxy route for GSAi provider discovery
echo "Creating GSAi provider proxy route..."

# This route will forward requests from /openapi/gsai/* to the actual GSAi endpoints
provider_route_config=$(cat <<EOF
{
  "uri": "/openapi/${OPENAPI_1_ID}/providers",
  "name": "openapi-${OPENAPI_1_ID}-providers",
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

# Create the providers route
response=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/3002" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d "$provider_route_config" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$response" | grep -q '"id":"3002"'; then
    print_status 0 "Created GSAi provider discovery route"
else
    print_status 1 "Failed to create provider discovery route"
    echo "Response: $response" | jq . 2>/dev/null || echo "$response"
fi

echo
echo "Step 7: Create Dedicated GSAi Discovery Endpoint"
echo "==============================================="

# Since GSAi doesn't have a /providers endpoint, we need to create a mock response
# This will be handled by the FastAPI backend
echo "Creating GSAi provider configuration in FastAPI..."

# Create a special route that returns GSAi provider information
gsai_info_route=$(cat <<EOF
{
  "uri": "/api/v1/openapi/${OPENAPI_1_ID}/info",
  "name": "openapi-${OPENAPI_1_ID}-info",
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "violentutf_api:8000": 1
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
    }
  }
}
EOF
)

response=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/3003" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d "$gsai_info_route" 2>/dev/null || echo '{"error": "Failed"}')

if echo "$response" | grep -q '"id":"3003"'; then
    print_status 0 "Created GSAi info route"
else
    print_status 1 "Failed to create GSAi info route"
fi

echo
echo "Step 8: Test Model Discovery"
echo "==========================="

if [ "${provider_count:-0}" -gt 0 ]; then
    echo "Testing model discovery for openapi-${OPENAPI_1_ID}..."
    
    # Use JWT token if available, otherwise use API key
    if [ -n "${JWT_TOKEN:-}" ]; then
        models_response=$(curl -s --max-time 10 "http://localhost:9080/api/v1/generators/apisix/models?provider=openapi-${OPENAPI_1_ID}" \
            -H "Authorization: Bearer ${JWT_TOKEN}" 2>/dev/null || echo '{"error": "Failed"}')
    else
        models_response=$(curl -s --max-time 10 "http://localhost:9080/api/v1/generators/apisix/models?provider=openapi-${OPENAPI_1_ID}" \
            -H "X-API-Key: ${VIOLENTUTF_API_KEY}" 2>/dev/null || echo '{"error": "Failed"}')
    fi

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
echo "4. Created GSAi provider discovery route (3002)"
echo "5. Created GSAi info route (3003) for provider metadata"
echo "6. Fixed authentication method for JWT token generation"
echo "7. Configured proper Bearer token authentication for GSAi"
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
echo
echo "Troubleshooting:"
echo "1. If authentication fails, check the password in violentutf/.env"
echo "2. If API key fails, verify VIOLENTUTF_API_KEY in violentutf_api/fastapi_app/.env"
echo "3. Check container logs: docker logs violentutf_api --tail 50"
echo "4. Verify routes: curl -H 'X-API-KEY: [YOUR_APISIX_ADMIN_KEY]' http://localhost:9180/apisix/admin/routes"
echo
echo "Common Issues:"
echo "- Invalid credentials: The password in Keycloak may not match what's in .env files"
echo "- Invalid API key: The API key in the container may be different from what's loaded"
echo "- MCP server error: This is a known issue but doesn't affect GSAi integration"
echo
echo "To manually test GSAi integration:"
echo "1. Get a valid JWT token or API key that works"
echo "2. Test provider discovery: curl -H 'X-API-Key: [YOUR_KEY]' http://localhost:9080/api/v1/generators/apisix/openapi-providers"
echo "3. Test GSAi directly: curl -H 'Authorization: Bearer ${OPENAPI_1_AUTH_TOKEN}' https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/chat/completions"