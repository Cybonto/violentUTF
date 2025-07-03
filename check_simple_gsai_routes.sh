#!/bin/bash

# Simple GSAi Routes Check Script
# This script focuses on testing the static GSAi routes created by ./create_simple_gsai_route.sh

set -eo pipefail

echo "=== Simple Static GSAi Routes Check ==="
echo "Testing routes created by ./create_simple_gsai_route.sh"
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
    exit 1
fi

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

# Load FastAPI configuration (where VIOLENTUTF_API_KEY is stored)
if [ -f "./violentutf_api/fastapi_app/.env" ]; then
    echo "Loading ./violentutf_api/fastapi_app/.env..."
    source "./violentutf_api/fastapi_app/.env"
fi

set +a  # Stop exporting

echo
echo "Environment files status:"
[ -f "./ai-tokens.env" ] && echo "✅ ./ai-tokens.env exists" || echo "❌ ./ai-tokens.env missing"
[ -f "./apisix/.env" ] && echo "✅ ./apisix/.env exists" || echo "❌ ./apisix/.env missing"
[ -f "./violentutf_api/fastapi_app/.env" ] && echo "✅ ./violentutf_api/fastapi_app/.env exists" || echo "❌ ./violentutf_api/fastapi_app/.env missing"

echo
echo "Validating configuration..."
if [ -z "${APISIX_ADMIN_KEY:-}" ]; then
    echo "❌ APISIX_ADMIN_KEY not found in environment files"
    echo "Try: export APISIX_ADMIN_KEY=\$(grep APISIX_ADMIN_KEY ./apisix/.env | cut -d'=' -f2 | tr -d '\"')"
    exit 1
fi

if [ -z "${VIOLENTUTF_API_KEY:-}" ]; then
    echo "❌ VIOLENTUTF_API_KEY not found in environment files"
    echo "Checking container for API key..."
    CONTAINER_API_KEY=$(docker exec violentutf_api printenv VIOLENTUTF_API_KEY 2>/dev/null || echo "")
    if [ -n "${CONTAINER_API_KEY}" ]; then
        VIOLENTUTF_API_KEY="${CONTAINER_API_KEY}"
        echo "✅ Found VIOLENTUTF_API_KEY in container: [REDACTED - ${#VIOLENTUTF_API_KEY} chars]"
    else
        echo "❌ VIOLENTUTF_API_KEY not found anywhere"
        echo "Please check your configuration files"
        exit 1
    fi
else
    echo "✅ VIOLENTUTF_API_KEY found: [REDACTED - ${#VIOLENTUTF_API_KEY} chars]"
fi

echo "✅ APISIX_ADMIN_KEY found: [REDACTED - ${#APISIX_ADMIN_KEY} chars]"

echo
echo "Step 1: Check Simple Static Routes Exist"
echo "========================================"

# Check if simple static routes exist (routes 9001 and 9002)
echo "Checking for simple static GSAi routes (9001, 9002)..."
simple_routes_response=$(curl -s "http://localhost:9180/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null || echo '{"error": "Failed"}')

simple_route_9001_exists=false
simple_route_9002_exists=false

if echo "$simple_routes_response" | grep -q '"list"'; then
    if echo "$simple_routes_response" | jq -e '.list[] | select(.key == "/apisix/routes/9001")' >/dev/null 2>&1; then
        simple_route_9001_exists=true
        route_9001_name=$(echo "$simple_routes_response" | jq -r '.list[] | select(.key == "/apisix/routes/9001") | .value.name')
        route_9001_uri=$(echo "$simple_routes_response" | jq -r '.list[] | select(.key == "/apisix/routes/9001") | .value.uri')
        print_status 0 "Route 9001 exists: $route_9001_name ($route_9001_uri)"
    else
        print_status 1 "Route 9001 (gsai-static-chat-completions) missing"
    fi
    
    if echo "$simple_routes_response" | jq -e '.list[] | select(.key == "/apisix/routes/9002")' >/dev/null 2>&1; then
        simple_route_9002_exists=true
        route_9002_name=$(echo "$simple_routes_response" | jq -r '.list[] | select(.key == "/apisix/routes/9002") | .value.name')
        route_9002_uri=$(echo "$simple_routes_response" | jq -r '.list[] | select(.key == "/apisix/routes/9002") | .value.uri')
        print_status 0 "Route 9002 exists: $route_9002_name ($route_9002_uri)"
    else
        print_status 1 "Route 9002 (gsai-static-models) missing"
    fi
else
    print_status 1 "Failed to retrieve routes from APISIX"
    echo "Response: $simple_routes_response"
    exit 1
fi

if [ "$simple_route_9001_exists" = false ] || [ "$simple_route_9002_exists" = false ]; then
    echo
    echo "❌ Simple static routes not found!"
    echo "Run: ./create_simple_gsai_route.sh to create them"
    exit 1
fi

echo
echo "Step 2: Debug Route Configuration"
echo "================================="

echo "Checking route 9002 (models) configuration..."
route_9002_config=$(echo "$simple_routes_response" | jq '.list[] | select(.key == "/apisix/routes/9002") | .value')
echo "Route 9002 plugins:"
echo "$route_9002_config" | jq '.plugins // {}'

echo
echo "Checking route 9001 (chat) configuration..."
route_9001_config=$(echo "$simple_routes_response" | jq '.list[] | select(.key == "/apisix/routes/9001") | .value')
echo "Route 9001 plugins:"
echo "$route_9001_config" | jq '.plugins // {}'

echo
echo "Step 3: Test API Key Authentication"
echo "==================================="

echo "Testing APISIX key-auth plugin..."
echo "Using API key: [REDACTED - ${#VIOLENTUTF_API_KEY} chars]"

# Test a known working endpoint first
echo "Testing API key against health endpoint..."
health_test=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "X-API-Key: ${VIOLENTUTF_API_KEY}" \
    "http://localhost:9080/api/v1/health" 2>/dev/null || echo "000")

if [ "$health_test" = "200" ]; then
    print_status 0 "API key works with health endpoint"
else
    print_status 1 "API key fails with health endpoint (HTTP $health_test)"
    echo "This suggests the API key itself is invalid"
fi

echo
echo "Step 4: Test Simple GSAi Models Endpoint"
echo "========================================"

echo "Testing: http://localhost:9080/ai/gsai/models"
echo "Headers: X-API-Key: [REDACTED]"

simple_models_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "X-API-Key: ${VIOLENTUTF_API_KEY}" \
    "http://localhost:9080/ai/gsai/models" 2>/dev/null)

# Extract HTTP code and body
models_http_code=$(echo "$simple_models_response" | grep "HTTP_CODE:" | cut -d: -f2)
models_body=$(echo "$simple_models_response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $models_http_code"
echo "Response body:"
echo "$models_body" | jq . 2>/dev/null || echo "$models_body"

if [ "$models_http_code" = "200" ]; then
    if echo "$models_body" | jq -e '.data[0]' >/dev/null 2>&1; then
        model_count=$(echo "$models_body" | jq '.data | length' 2>/dev/null || echo "0")
        print_status 0 "Models endpoint working - found $model_count models"
        echo "Available models:"
        echo "$models_body" | jq -r '.data[] | "  - \(.id)"' 2>/dev/null | head -5
    else
        print_status 1 "Models endpoint returned 200 but unexpected format"
    fi
else
    print_status 1 "Models endpoint failed (HTTP $models_http_code)"
fi

echo
echo "Step 5: Test Simple GSAi Chat Completions Endpoint"
echo "================================================="

echo "Testing: http://localhost:9080/ai/gsai/chat/completions"
echo "Headers: X-API-Key: [REDACTED], Content-Type: application/json"

simple_chat_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "X-API-Key: ${VIOLENTUTF_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"gpt-4","messages":[{"role":"user","content":"Hello, respond with just: GSAi working!"}]}' \
    "http://localhost:9080/ai/gsai/chat/completions" 2>/dev/null)

# Extract HTTP code and body
chat_http_code=$(echo "$simple_chat_response" | grep "HTTP_CODE:" | cut -d: -f2)
chat_body=$(echo "$simple_chat_response" | grep -v "HTTP_CODE:")

echo "HTTP Status: $chat_http_code"
echo "Response body:"
echo "$chat_body" | jq . 2>/dev/null || echo "$chat_body"

if [ "$chat_http_code" = "200" ]; then
    if echo "$chat_body" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
        chat_content=$(echo "$chat_body" | jq -r '.choices[0].message.content' 2>/dev/null)
        print_status 0 "Chat completions endpoint working"
        echo "GSAi Response: \"$chat_content\""
    else
        print_status 1 "Chat endpoint returned 200 but unexpected format"
    fi
else
    print_status 1 "Chat completions endpoint failed (HTTP $chat_http_code)"
fi

echo
echo "Step 6: Troubleshooting Analysis"
echo "==============================="

if [ "$models_http_code" != "200" ] || [ "$chat_http_code" != "200" ]; then
    echo "🔍 TROUBLESHOOTING STEPS:"
    echo
    echo "1. Check if routes have key-auth plugin enabled:"
    echo "   Route 9001 plugins: $(echo "$route_9001_config" | jq -c '.plugins // {}')"
    echo "   Route 9002 plugins: $(echo "$route_9002_config" | jq -c '.plugins // {}')"
    echo
    echo "2. Verify API key format:"
    echo "   Length: ${#VIOLENTUTF_API_KEY} characters"
    echo "   Source: Environment files"
    echo
    echo "3. Test direct GSAi (bypass APISIX):"
    if [ -n "${OPENAPI_1_AUTH_TOKEN:-}" ]; then
        echo "   curl -H 'Authorization: Bearer ${OPENAPI_1_AUTH_TOKEN}' https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models"
    else
        echo "   OPENAPI_1_AUTH_TOKEN not available for direct test"
    fi
    echo
    echo "4. Check APISIX logs:"
    echo "   docker logs apisix-apisix-1 --tail 20"
    echo
    echo "5. Recreate routes:"
    echo "   ./create_simple_gsai_route.sh"
else
    echo "🎉 SUCCESS! Simple static GSAi routes are working!"
    echo "✅ Models endpoint: http://localhost:9080/ai/gsai/models"
    echo "✅ Chat endpoint: http://localhost:9080/ai/gsai/chat/completions"
    echo "🔧 Authentication: X-API-Key (like OpenAI/Anthropic)"
fi

echo
echo "=== Simple GSAi Routes Check Complete ==="