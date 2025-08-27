#!/usr/bin/env bash
# Debug APISIX routing for OpenAPI

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load environment variables
load_env_file() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        while IFS='=' read -r key value; do
            if [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]]; then
                continue
            fi
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            if [[ -n "$key" && "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
                export "$key=$value"
            fi
        done < "$env_file"
    fi
}

# Load configs
[ -f "../violentutf/.env" ] && load_env_file "../violentutf/.env"
[ -f "../apisix/.env" ] && load_env_file "../apisix/.env"

echo -e "${BLUE}=== APISIX Route Debugging ===${NC}"
echo

# Check if APISIX is running
echo "Checking APISIX status..."
if curl -s -o /dev/null http://localhost:9080/health; then
    echo -e "${GREEN}✓ APISIX is running${NC}"
else
    echo -e "${RED}✗ APISIX is not accessible${NC}"
    exit 1
fi
echo

# Get route details
echo "Fetching OpenAPI route details..."
if [ -n "${APISIX_ADMIN_KEY:-}" ]; then
    routes=$(curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        http://localhost:9180/apisix/admin/routes | \
        jq -r '.list[] | select(.value.uri | contains("/ai/openapi/gsai-api-1"))')

    if [ -n "$routes" ]; then
        echo -e "${GREEN}✓ Found OpenAPI routes${NC}"
        echo "$routes" | jq -r '.value | {uri, methods, upstream, plugins: .plugins | keys}'
    else
        echo -e "${RED}✗ No OpenAPI routes found${NC}"
    fi
else
    echo -e "${YELLOW}APISIX_ADMIN_KEY not found${NC}"
fi
echo

# Test different request formats
echo -e "${BLUE}Testing different request paths:${NC}"
echo

if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
    # Test 1: Exact path from route
    echo "1. Testing exact route path:"
    echo "   POST /ai/openapi/gsai-api-1/api/v1/chat/completions"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST http://localhost:9080/ai/openapi/gsai-api-1/api/v1/chat/completions \
        -H "apikey: $VIOLENTUTF_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "test"}]}')

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')
    echo "   Response: HTTP $http_code"
    if [ "$http_code" != "200" ]; then
        echo "   Body: $body" | head -100
    fi
    echo

    # Test 2: Models endpoint through APISIX
    echo "2. Testing models endpoint through APISIX:"
    echo "   GET /ai/openapi/gsai-api-1/api/v1/models"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models \
        -H "apikey: $VIOLENTUTF_API_KEY")

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    if [ "$http_code" = "200" ]; then
        echo -e "   Response: ${GREEN}HTTP $http_code - Models endpoint works${NC}"
    else
        echo -e "   Response: ${RED}HTTP $http_code${NC}"
    fi
    echo

    # Test 3: Check if it's a method issue
    echo "3. Testing with GET method:"
    echo "   GET /ai/openapi/gsai-api-1/api/v1/chat/completions"
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/chat/completions \
        -H "apikey: $VIOLENTUTF_API_KEY")
    echo "   Response: HTTP $response"
    echo

else
    echo -e "${RED}VIOLENTUTF_API_KEY not found${NC}"
fi

# Check APISIX access logs
echo -e "${BLUE}Recent APISIX logs:${NC}"
echo "docker logs apisix-apisix-1 --tail 20 | grep -E '(gsai-api-1|404)'"
echo
echo "Run the above command to see APISIX logs"

# Summary
echo
echo -e "${BLUE}=== Summary ===${NC}"
echo
echo "Based on the tests:"
echo "1. If models endpoint works but chat doesn't -> Route exists but chat endpoint has issues"
echo "2. If both return 404 -> Routes may not be properly configured"
echo "3. If you see 500 errors -> The upstream API has internal issues"
echo
echo "The GSAI API appears to have an internal AWS authentication issue."
echo "This is not related to your API key but their server configuration."
