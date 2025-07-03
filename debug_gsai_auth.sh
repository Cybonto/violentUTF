#!/usr/bin/env bash
# Debug GSAi authentication issues

echo "🔍 Debugging GSAi Authentication..."

# Load environment variables
if [ -f "apisix/.env" ]; then
    source "apisix/.env"
    echo "✅ Loaded APISIX admin key: ${APISIX_ADMIN_KEY:0:8}...${APISIX_ADMIN_KEY: -4}"
fi

if [ -f "violentutf_api/fastapi_app/.env" ]; then
    source "violentutf_api/fastapi_app/.env"
    echo "✅ Loaded ViolentUTF API key: ${VIOLENTUTF_API_KEY:0:8}...${VIOLENTUTF_API_KEY: -4}"
fi

admin_key="$APISIX_ADMIN_KEY"
api_key="$VIOLENTUTF_API_KEY"
apisix_admin_url="http://localhost:9180"

# Check if consumer exists
echo ""
echo "🔑 Checking if API key consumer exists..."
consumer_response=$(curl -s "$apisix_admin_url/apisix/admin/consumers/violentutf_api_user" \
    -H "X-API-KEY: $admin_key")

if echo "$consumer_response" | grep -q "violentutf_api_user"; then
    echo "✅ Consumer exists"
    # Extract the consumer's API key
    consumer_key=$(echo "$consumer_response" | jq -r '.value.plugins["key-auth"].key' 2>/dev/null)
    echo "   Consumer API key: ${consumer_key:0:8}...${consumer_key: -4}"
    
    # Compare with our API key
    if [ "$consumer_key" = "$api_key" ]; then
        echo "✅ API keys match!"
    else
        echo "❌ API key mismatch!"
        echo "   Our key:      ${api_key:0:8}...${api_key: -4}"
        echo "   Consumer key: ${consumer_key:0:8}...${consumer_key: -4}"
    fi
else
    echo "❌ Consumer does not exist"
    echo "Response: $consumer_response"
fi

# Test authentication directly
echo ""
echo "🧪 Testing direct GSAi authentication..."
echo "Using API key: ${api_key:0:8}...${api_key: -4}"

test_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "X-API-Key: $api_key" \
    -H "Content-Type: application/json" \
    -X POST \
    -d '{"model":"claude_3_5_sonnet","messages":[{"role":"user","content":"test"}],"max_tokens":10}' \
    "http://localhost:9080/ai/gsai/chat/completions")

http_code=$(echo "$test_response" | grep "HTTP_CODE:" | cut -d: -f2)
response_body=$(echo "$test_response" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $http_code"
echo "Response: $response_body"

if [ "$http_code" = "200" ]; then
    echo "✅ Authentication working!"
elif [ "$http_code" = "401" ]; then
    echo "❌ Authentication failed - API key not accepted"
elif [ "$http_code" = "404" ]; then
    echo "❌ Route not found"
else
    echo "❌ Unexpected error (HTTP $http_code)"
fi

echo ""
echo "🔧 Debug complete."