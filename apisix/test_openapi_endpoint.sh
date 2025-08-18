#!/usr/bin/env bash
# Test OpenAPI endpoints to debug 404 errors

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

# Load configs - check current directory first, then parent
if [ -f "./ai-tokens.env" ]; then
    echo "Loading ai-tokens.env from current directory"
    load_env_file "./ai-tokens.env"
elif [ -f "../ai-tokens.env" ]; then
    echo "Loading ai-tokens.env from parent directory"
    load_env_file "../ai-tokens.env"
else
    echo -e "${YELLOW}Warning: ai-tokens.env not found${NC}"
fi

# Also check for .env files with VIOLENTUTF_API_KEY
if [ -f "./.env" ]; then
    load_env_file "./.env"
fi
if [ -f "./violentutf/.env" ]; then
    echo "Loading violentutf/.env"
    load_env_file "./violentutf/.env"
elif [ -f "../violentutf/.env" ]; then
    echo "Loading ../violentutf/.env"
    load_env_file "../violentutf/.env"
fi
if [ -f "./violentutf_api/fastapi_app/.env" ]; then
    echo "Loading violentutf_api/fastapi_app/.env"
    load_env_file "./violentutf_api/fastapi_app/.env"
elif [ -f "../violentutf_api/fastapi_app/.env" ]; then
    echo "Loading ../violentutf_api/fastapi_app/.env"
    load_env_file "../violentutf_api/fastapi_app/.env"
fi

echo -e "${BLUE}=== OpenAPI Endpoint Testing ===${NC}"
echo

# Test 1: Direct API access
echo -e "${BLUE}Test 1: Direct API Access${NC}"
echo "Testing models endpoint directly..."
echo "URL: https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models"
echo

if [ -n "${OPENAPI_1_AUTH_TOKEN:-}" ]; then
    # Debug: show token length and preview
    token_length=${#OPENAPI_1_AUTH_TOKEN}
    echo "Found auth token (length: $token_length)"
    if [ $token_length -gt 20 ]; then
        echo "Using auth token: ${OPENAPI_1_AUTH_TOKEN:0:10}...${OPENAPI_1_AUTH_TOKEN: -10}"
    else
        echo "Using auth token: [SHORT TOKEN: $OPENAPI_1_AUTH_TOKEN]"
    fi
    echo

    # Test models endpoint
    echo "Models endpoint response:"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models)

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Models endpoint works (HTTP $http_code)${NC}"
        echo "$body" | jq -r '.data[].id' 2>/dev/null | head -5 || echo "$body" | head -100
    else
        echo -e "${RED}✗ Models endpoint failed (HTTP $http_code)${NC}"
        echo "$body" | head -100
    fi
    echo

    # Test chat completions endpoint
    echo "Chat completions endpoint response:"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/chat/completions \
        -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "Say hello"}]}')

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Chat endpoint works (HTTP $http_code)${NC}"
        echo "$body" | jq -r '.choices[0].message.content' 2>/dev/null | head -50 || echo "$body" | head -100
    else
        echo -e "${RED}✗ Chat endpoint failed (HTTP $http_code)${NC}"
        echo "$body" | head -100
    fi
    echo

    # Try alternative endpoints
    echo -e "${BLUE}Testing alternative endpoint paths:${NC}"

    # Test without /api prefix
    echo "Trying /v1/chat/completions (no /api prefix):"
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST https://api.dev.gsai.mcaas.fcs.gsa.gov/v1/chat/completions \
        -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "test"}]}')
    echo "HTTP Status: $response"

    # Test with /chat endpoint
    echo "Trying /api/v1/chat:"
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/chat \
        -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "test"}]}')
    echo "HTTP Status: $response"

else
    echo -e "${RED}No OPENAPI_1_AUTH_TOKEN found in environment${NC}"
fi

echo
echo -e "${BLUE}Test 2: Through APISIX${NC}"

if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
    key_length=${#VIOLENTUTF_API_KEY}
    echo "Found APISIX API key (length: $key_length)"
    if [ $key_length -gt 20 ]; then
        echo "Using APISIX API key: ${VIOLENTUTF_API_KEY:0:10}...${VIOLENTUTF_API_KEY: -10}"
    else
        echo "Using APISIX API key: [SHORT KEY]"
    fi
    echo

    echo "Testing through APISIX gateway:"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST http://localhost:9080/ai/openapi/gsai-api-1/api/v1/chat/completions \
        -H "apikey: $VIOLENTUTF_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "Say hello"}]}')

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')

    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ APISIX route works (HTTP $http_code)${NC}"
        echo "$body" | jq -r '.choices[0].message.content' 2>/dev/null | head -50 || echo "$body" | head -100
    else
        echo -e "${RED}✗ APISIX route failed (HTTP $http_code)${NC}"
        echo "$body" | head -100
    fi
else
    echo -e "${RED}No VIOLENTUTF_API_KEY found in environment${NC}"
fi

echo
echo -e "${BLUE}=== Debugging Tips ===${NC}"
echo
echo "1. If direct access works but APISIX fails:"
echo "   - Check proxy-rewrite configuration"
echo "   - Verify regex_uri pattern is correct"
echo
echo "2. If both fail with 404:"
echo "   - The endpoint path might be wrong"
echo "   - Check OpenAPI spec for correct paths"
echo
echo "3. Check APISIX logs:"
echo "   docker logs apisix-apisix-1 --tail 50 | grep gsai-api-1"
