#!/usr/bin/env bash
# Quick test script to test chat completions route creation with fixed config

# Set environment variables
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
APISIX_ADMIN_KEY="${APISIX_ADMIN_KEY:-ens35VSOYXzPMHLUpUhwV6FcKZEyRxud}"

# Test route configuration (mimicking the chat completions route)
provider_id="gsai-api-1"
provider_name="GSAi API Latest"
operation_id="converse_api_v1_chat_completions_post"
hostname="api.dev.gsai.mcaas.fcs.gsa.gov"
port="443"
scheme="https"
uri="/ai/openapi/gsai-api-1/api/v1/chat/completions"

# Generate route ID using the new logic
path_hash=$(echo -n "POST:/api/v1/chat/completions" | shasum -a 256 | cut -c1-8)
safe_operation_id=$(echo "$operation_id" | sed 's/[^a-zA-Z0-9-]/-/g' | tr '[:upper:]' '[:lower:]' | cut -c1-20)
route_id="openapi-${provider_id}-${safe_operation_id}-${path_hash}"

# Check if route ID is too long
if [ ${#route_id} -gt 50 ]; then
    route_id="openapi-${provider_id}-${path_hash}"
fi

echo "Testing chat completions route creation..."
echo "Route ID: $route_id (length: ${#route_id})"

# Create the fixed route configuration (without "id" field)
safe_description=$(echo "${provider_name} ${operation_id}" | sed 's/[\"\\]/\\&/g')

route_config='{
    "uri": "'$uri'",
    "methods": ["POST"],
    "desc": "'$safe_description'",
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "'$hostname':'$port'": 1
        },
        "scheme": "'$scheme'"
    },
    "plugins": {
        "key-auth": {},
        "proxy-rewrite": {
            "regex_uri": ["^/ai/openapi/'$provider_id'(.*)", "$1"]
        }
    }
}'

echo ""
echo "Route configuration:"
echo "$route_config" | jq . 2>/dev/null || echo "$route_config"

echo ""
echo "Creating route..."
response=$(curl -w "%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
  -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d "${route_config}" 2>&1)

http_code="${response: -3}"
response_body="${response%???}"

echo "HTTP Code: $http_code"
echo "Response: $response_body"

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo "✅ Successfully created chat completions route!"
else
    echo "❌ Failed to create route"
    # Try to parse error details
    if command -v jq > /dev/null 2>&1; then
        echo "Error details:"
        echo "$response_body" | jq .
    fi
fi