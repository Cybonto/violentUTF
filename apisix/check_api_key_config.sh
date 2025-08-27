#!/usr/bin/env bash
# Check APISIX API key configuration

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
[ -f "../violentutf/.env" ] && load_env_file "../violentutf/.env"

echo -e "${BLUE}=== APISIX API Key Configuration Check ===${NC}"
echo

# Check APISIX admin key
if [ -n "${APISIX_ADMIN_KEY:-}" ]; then
    echo "APISIX Admin Key found (for admin API): ${APISIX_ADMIN_KEY:0:10}..."
else
    echo -e "${RED}APISIX_ADMIN_KEY not found${NC}"
fi

# Check ViolentUTF API key
if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
    echo "ViolentUTF API Key found (for gateway): ${VIOLENTUTF_API_KEY:0:10}..."
else
    echo -e "${RED}VIOLENTUTF_API_KEY not found${NC}"
fi
echo

# Get consumers from APISIX
echo -e "${BLUE}Checking APISIX consumers:${NC}"
if [ -n "${APISIX_ADMIN_KEY:-}" ]; then
    consumers=$(curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        http://localhost:9180/apisix/admin/consumers)

    if echo "$consumers" | jq -e '.list' > /dev/null 2>&1; then
        echo "Consumers found:"
        echo "$consumers" | jq -r '.list[] | {username: .value.username, plugins: .value.plugins | keys}'

        # Check for violentutf consumer
        violentutf_consumer=$(echo "$consumers" | jq -r '.list[] | select(.value.username == "violentutf")')
        if [ -n "$violentutf_consumer" ]; then
            echo
            echo -e "${GREEN}✓ Found 'violentutf' consumer${NC}"

            # Get the configured key
            configured_key=$(echo "$violentutf_consumer" | jq -r '.value.plugins."key-auth".key' 2>/dev/null || echo "")
            if [ -n "$configured_key" ]; then
                echo "Configured key in APISIX: ${configured_key:0:10}..."

                # Compare with environment key
                if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
                    if [ "$configured_key" = "$VIOLENTUTF_API_KEY" ]; then
                        echo -e "${GREEN}✓ Keys match!${NC}"
                    else
                        echo -e "${RED}✗ Keys DO NOT match!${NC}"
                        echo "  Environment: ${VIOLENTUTF_API_KEY:0:10}..."
                        echo "  APISIX:      ${configured_key:0:10}..."
                    fi
                fi
            else
                echo -e "${RED}No key-auth plugin configured for violentutf consumer${NC}"
            fi
        else
            echo -e "${RED}✗ No 'violentutf' consumer found${NC}"
        fi
    else
        echo -e "${YELLOW}No consumers found or unable to fetch${NC}"
    fi
else
    echo -e "${RED}Cannot check consumers - APISIX_ADMIN_KEY not set${NC}"
fi

echo
echo -e "${BLUE}Testing key-auth:${NC}"

# Test with the API key
if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
    echo "Testing with VIOLENTUTF_API_KEY..."
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "apikey: $VIOLENTUTF_API_KEY" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models)

    if [ "$response" = "404" ]; then
        echo -e "${YELLOW}Got 404 - key-auth passed but route not found${NC}"
    elif [ "$response" = "401" ]; then
        echo -e "${RED}Got 401 - key-auth rejected the API key${NC}"
    else
        echo "Response: HTTP $response"
    fi

    # Test without API key
    echo
    echo "Testing without API key..."
    response=$(curl -s -o /dev/null -w "%{http_code}" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models)
    echo "Response without key: HTTP $response (should be 401)"
fi

echo
echo -e "${BLUE}=== Recommendations ===${NC}"
echo
echo "If keys don't match or consumer is missing:"
echo "1. Re-run setup script: ./setup_macos.sh"
echo "2. Or manually create consumer:"
echo
echo "curl -X PUT http://localhost:9180/apisix/admin/consumers/violentutf \\"
echo "  -H \"X-API-KEY: \$APISIX_ADMIN_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{"
echo "    \"username\": \"violentutf\","
echo "    \"plugins\": {"
echo "      \"key-auth\": {"
echo "        \"key\": \"'\$VIOLENTUTF_API_KEY'\""
echo "      }"
echo "    }"
echo "  }'"
