#!/usr/bin/env bash
# Create APISIX consumer for ViolentUTF

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
[ -f "../violentutf_api/fastapi_app/.env" ] && load_env_file "../violentutf_api/fastapi_app/.env"

echo -e "${BLUE}=== Creating APISIX Consumer ===${NC}"
echo

# Check required variables
if [ -z "${APISIX_ADMIN_KEY:-}" ]; then
    echo -e "${RED}Error: APISIX_ADMIN_KEY not found${NC}"
    exit 1
fi

if [ -z "${VIOLENTUTF_API_KEY:-}" ]; then
    echo -e "${RED}Error: VIOLENTUTF_API_KEY not found${NC}"
    exit 1
fi

APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

echo "APISIX Admin URL: $APISIX_ADMIN_URL"
echo "API Key to configure: ${VIOLENTUTF_API_KEY:0:10}..."
echo

# Check if consumer already exists
echo "Checking if consumer 'violentutf' exists..."
existing_consumer=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/consumers/violentutf" \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

if echo "$existing_consumer" | grep -q '"username":"violentutf"'; then
    echo -e "${YELLOW}Consumer 'violentutf' already exists, will update it${NC}"
else
    echo "Consumer does not exist, will create it"
fi

# Create/update consumer
consumer_config='{
    "username": "violentutf",
    "plugins": {
        "key-auth": {
            "key": "'$VIOLENTUTF_API_KEY'"
        }
    }
}'

echo
echo "Creating/updating consumer..."
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/consumers/violentutf" \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d "${consumer_config}")

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE:/d')

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo -e "${GREEN}✅ Successfully created/updated consumer 'violentutf'${NC}"
    echo "API Key configured: ${VIOLENTUTF_API_KEY:0:10}..."
else
    echo -e "${RED}❌ Failed to create consumer${NC}"
    echo "HTTP Code: $http_code"
    echo "Response: $body" | jq '.' 2>/dev/null || echo "$body"
    exit 1
fi

echo
echo -e "${BLUE}Testing the configuration:${NC}"
echo

# Test with API key
echo "Testing with API key..."
test_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "apikey: $VIOLENTUTF_API_KEY" \
    http://localhost:9080/apisix/health)

test_code=$(echo "$test_response" | grep "HTTP_CODE:" | cut -d: -f2)
test_body=$(echo "$test_response" | sed '/HTTP_CODE:/d')

if [ "$test_code" = "200" ]; then
    echo -e "${GREEN}✓ API key authentication working${NC}"
else
    echo -e "${YELLOW}Health check returned: $test_code${NC}"
fi

# Test OpenAPI route
echo
echo "Testing OpenAPI route..."
openapi_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "apikey: $VIOLENTUTF_API_KEY" \
    http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models)

openapi_code=$(echo "$openapi_response" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$openapi_code" = "200" ]; then
    echo -e "${GREEN}✓ OpenAPI route is working!${NC}"
elif [ "$openapi_code" = "404" ]; then
    echo -e "${YELLOW}Route returned 404 - may need to check route configuration${NC}"
elif [ "$openapi_code" = "401" ]; then
    echo -e "${RED}Still getting 401 - authentication issue persists${NC}"
else
    echo "OpenAPI route returned: $openapi_code"
fi

echo
echo -e "${GREEN}Consumer configuration complete!${NC}"
echo
echo "You can now use the API with:"
echo "  Header: apikey: $VIOLENTUTF_API_KEY"