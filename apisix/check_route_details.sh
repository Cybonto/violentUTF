#!/usr/bin/env bash
# Check detailed APISIX route configuration

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
[ -f "../apisix/.env" ] && load_env_file "../apisix/.env"

echo -e "${BLUE}=== Detailed APISIX Route Configuration ===${NC}"
echo

APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

# Get the models route specifically
echo "Fetching detailed configuration for models route..."
models_route=$(curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
    "${APISIX_ADMIN_URL}/apisix/admin/routes" | \
    jq -r '.list[] | select(.value.uri == "/ai/openapi/gsai-api-1/api/v1/models")')

if [ -n "$models_route" ]; then
    echo -e "${GREEN}Found models route${NC}"
    echo
    echo "Full route configuration:"
    echo "$models_route" | jq '.'
    echo

    # Extract key details
    echo -e "${BLUE}Key configuration details:${NC}"
    echo

    # Route ID
    route_id=$(echo "$models_route" | jq -r '.key | split("/") | last')
    echo "Route ID: $route_id"
    echo

    # Proxy-rewrite plugin config
    echo "Proxy-rewrite plugin configuration:"
    proxy_rewrite=$(echo "$models_route" | jq -r '.value.plugins."proxy-rewrite"')
    echo "$proxy_rewrite" | jq '.'
    echo

    # Check regex_uri
    regex_uri=$(echo "$proxy_rewrite" | jq -r '.regex_uri[]?' 2>/dev/null)
    if [ -n "$regex_uri" ]; then
        echo "Regex URI pattern: $regex_uri"
        echo
    fi

    # Check headers
    echo "Headers configuration:"
    headers=$(echo "$proxy_rewrite" | jq -r '.headers')
    if [ "$headers" != "null" ]; then
        echo "$headers" | jq '.'
    else
        echo "No headers configured"
    fi
    echo

    # Test the regex pattern
    echo -e "${BLUE}Testing URI rewrite:${NC}"
    test_uri="/ai/openapi/gsai-api-1/api/v1/models"
    echo "Original URI: $test_uri"

    # Apply regex if exists
    if [ -n "$regex_uri" ]; then
        pattern=$(echo "$proxy_rewrite" | jq -r '.regex_uri[0]')
        replacement=$(echo "$proxy_rewrite" | jq -r '.regex_uri[1]')
        echo "Pattern: $pattern"
        echo "Replacement: $replacement"

        # Test with sed (approximation)
        rewritten=$(echo "$test_uri" | sed -E "s|$pattern|$replacement|")
        echo "Rewritten URI: $rewritten"
    fi
else
    echo -e "${RED}Models route not found!${NC}"
fi

echo
echo -e "${BLUE}Testing route with curl verbose:${NC}"
echo

# Test with verbose output
if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
    echo "Testing models endpoint with verbose output..."
    curl -v -H "apikey: $VIOLENTUTF_API_KEY" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models 2>&1 | \
        grep -E "(< HTTP|< |> |Host:|Connected to)"
fi

echo
echo -e "${BLUE}Checking APISIX access logs:${NC}"
echo "docker logs apisix-apisix-1 2>&1 | grep -v 'reportServiceInstance' | tail -20"
echo

echo -e "${BLUE}=== Potential Issues ===${NC}"
echo
echo "1. If regex_uri is wrong, the path won't be rewritten correctly"
echo "2. If upstream uses different paths than expected"
echo "3. If SSL/TLS handshake is failing"
echo "4. If the host header is causing issues"
