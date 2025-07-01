#!/usr/bin/env bash
# Test the complete request flow to debug 404 issues

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
[ -f "../ai-tokens.env" ] && load_env_file "../ai-tokens.env"

echo -e "${BLUE}=== Testing Request Flow ===${NC}"
echo

# Step 1: Test direct access to upstream
echo -e "${BLUE}Step 1: Test direct access to upstream API${NC}"
if [ -n "${OPENAPI_1_AUTH_TOKEN:-}" ]; then
    echo "Testing: https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models"
    echo "Token: ${OPENAPI_1_AUTH_TOKEN:0:10}..."
    
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models)
    
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Direct access works (HTTP 200)${NC}"
        echo "Models found: $(echo "$body" | jq -r '.data[].id' 2>/dev/null | wc -l | xargs)"
    else
        echo -e "${RED}✗ Direct access failed (HTTP $http_code)${NC}"
        echo "Response: $body" | head -50
    fi
else
    echo -e "${YELLOW}OPENAPI_1_AUTH_TOKEN not found${NC}"
fi
echo

# Step 2: Test APISIX internal connectivity
echo -e "${BLUE}Step 2: Test APISIX connectivity${NC}"
echo "Checking if APISIX can reach the upstream..."

# This would need to be run from inside APISIX container
echo "To test from APISIX container:"
echo "docker exec apisix-apisix-1 curl -I https://api.dev.gsai.mcaas.fcs.gsa.gov"
echo

# Step 3: Test with different headers
echo -e "${BLUE}Step 3: Test APISIX route with different configurations${NC}"

if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
    # Test 1: Basic request
    echo "Test 1: Basic request"
    curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
        -H "apikey: $VIOLENTUTF_API_KEY" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models
    
    # Test 2: With explicit Accept header
    echo
    echo "Test 2: With Accept header"
    curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
        -H "apikey: $VIOLENTUTF_API_KEY" \
        -H "Accept: application/json" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models
    
    # Test 3: With User-Agent
    echo
    echo "Test 3: With User-Agent"
    curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
        -H "apikey: $VIOLENTUTF_API_KEY" \
        -H "User-Agent: ViolentUTF/1.0" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models
fi

# Step 4: Check APISIX error logs
echo
echo -e "${BLUE}Step 4: Check APISIX error logs${NC}"
echo "Recent errors (excluding reportServiceInstance):"
docker logs apisix-apisix-1 2>&1 | grep -v "reportServiceInstance" | grep -i "error" | tail -5

# Step 5: Test a simple APISIX route
echo
echo -e "${BLUE}Step 5: Test APISIX health endpoint${NC}"
health_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:9080/apisix/health)
health_code=$(echo "$health_response" | grep "HTTP_CODE:" | cut -d: -f2)
echo "APISIX health check: HTTP $health_code"

# Step 6: Enable debug logging
echo
echo -e "${BLUE}Step 6: Enable APISIX debug logging${NC}"
echo "To enable debug logging, run:"
echo "docker exec apisix-apisix-1 sed -i 's/error_log_level: \"warn\"/error_log_level: \"info\"/' /usr/local/apisix/conf/config.yaml"
echo "docker restart apisix-apisix-1"
echo
echo "Then check logs with:"
echo "docker logs -f apisix-apisix-1 2>&1 | grep -E 'gsai|openapi|proxy_pass'"

# Analysis
echo
echo -e "${BLUE}=== Analysis ===${NC}"
echo
echo "Common causes of 404 with correct configuration:"
echo "1. APISIX can't reach the upstream (network/firewall issue)"
echo "2. SSL/TLS certificate verification failing"
echo "3. The upstream API is returning 404 and APISIX is passing it through"
echo "4. DNS resolution issues inside Docker"
echo
echo "To test DNS from APISIX container:"
echo "docker exec apisix-apisix-1 nslookup api.dev.gsai.mcaas.fcs.gsa.gov"