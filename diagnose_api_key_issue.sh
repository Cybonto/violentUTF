#!/usr/bin/env bash
# Diagnostic script for API key authentication issues

echo "🔍 API Key Authentication Diagnostic"
echo "===================================="

# Get the APISIX admin key
ADMIN_KEY=$(grep "^APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)
if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY not found in apisix/.env"
    exit 1
fi

# Get the ViolentUTF API key
API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf/.env | cut -d'=' -f2)
if [ -z "$API_KEY" ]; then
    echo "❌ ERROR: VIOLENTUTF_API_KEY not found in violentutf/.env"
    exit 1
fi

echo "Found API Key: ${API_KEY:0:12}...${API_KEY: -4}"
echo ""

# Check all consumers
echo "📋 Checking APISIX Consumers:"
echo "----------------------------"
CONSUMERS=$(curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/consumers)
echo "$CONSUMERS" | jq -r '.list[].value | "\(.username): \(.plugins."key-auth".key[:12])...\(.plugins."key-auth".key[-4:])"'

# Check if our API key exists in any consumer
echo ""
echo "🔑 Searching for API key in consumers:"
echo "-------------------------------------"
FOUND_CONSUMER=$(echo "$CONSUMERS" | jq -r --arg key "$API_KEY" '.list[].value | select(.plugins."key-auth".key == $key) | .username')
if [ -n "$FOUND_CONSUMER" ]; then
    echo "✅ API key found in consumer: $FOUND_CONSUMER"
else
    echo "❌ API key NOT found in any consumer!"
    echo ""
    echo "Creating missing consumers..."
    
    # Create the three standard consumers
    for consumer in "violentutf-api" "violentutf-user" "violentutf_api_user"; do
        echo -n "Creating consumer $consumer... "
        RESPONSE=$(curl -s -w "%{http_code}" -X PUT "http://localhost:9180/apisix/admin/consumers/$consumer" \
            -H "X-API-KEY: $ADMIN_KEY" \
            -H "Content-Type: application/json" \
            -d "{
                \"username\": \"$consumer\",
                \"plugins\": {
                    \"key-auth\": {
                        \"key\": \"$API_KEY\"
                    }
                }
            }" -o /dev/null)
        
        if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "201" ]; then
            echo "✅ Success"
        else
            echo "❌ Failed (HTTP $RESPONSE)"
        fi
    done
fi

# Check GSAi routes
echo ""
echo "🛣️  Checking GSAi Routes:"
echo "----------------------"
ROUTES=$(curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/routes)
GSAI_ROUTES=$(echo "$ROUTES" | jq -r '.list[].value | select(.uri | contains("gsai")) | "\(.id): \(.uri) - Plugins: \(.plugins | keys | join(", "))"')
if [ -n "$GSAI_ROUTES" ]; then
    echo "$GSAI_ROUTES"
else
    echo "❌ No GSAi routes found!"
fi

# Test authentication
echo ""
echo "🧪 Testing Authentication:"
echo "------------------------"

# Test with lowercase apikey header
echo -n "Test 1 - lowercase 'apikey' header: "
TEST1=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "apikey: $API_KEY" \
    -H "Content-Type: application/json" \
    -X POST \
    http://localhost:9080/ai/gsai-api-1/chat/completions \
    -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' 2>&1)
HTTP_CODE=$(echo "$TEST1" | grep "HTTP_CODE:" | cut -d: -f2)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Success (HTTP 200)"
else
    echo "❌ Failed (HTTP $HTTP_CODE)"
    BODY=$(echo "$TEST1" | sed '/HTTP_CODE:/d')
    echo "   Response: $BODY"
fi

# Test with uppercase X-API-KEY header
echo -n "Test 2 - uppercase 'X-API-KEY' header: "
TEST2=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "X-API-KEY: $API_KEY" \
    -H "Content-Type: application/json" \
    -X POST \
    http://localhost:9080/ai/gsai-api-1/chat/completions \
    -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' 2>&1)
HTTP_CODE=$(echo "$TEST2" | grep "HTTP_CODE:" | cut -d: -f2)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Success (HTTP 200)"
else
    echo "❌ Failed (HTTP $HTTP_CODE)"
fi

# Check route details
echo ""
echo "📝 GSAi Route Details:"
echo "--------------------"
ROUTE_9001=$(curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/routes/9001)
if echo "$ROUTE_9001" | jq -e '.value' > /dev/null 2>&1; then
    echo "Route 9001 plugins:"
    echo "$ROUTE_9001" | jq -r '.value.plugins | keys[] | "  - \(.)"'
    
    # Check if key-auth is configured
    if echo "$ROUTE_9001" | jq -e '.value.plugins."key-auth"' > /dev/null 2>&1; then
        echo "  ✅ key-auth plugin is configured"
    else
        echo "  ❌ key-auth plugin is MISSING!"
    fi
else
    echo "❌ Route 9001 not found"
fi

echo ""
echo "💡 Recommendations:"
echo "-----------------"
if [ "$HTTP_CODE" != "200" ]; then
    echo "1. Run ./fix_gsai_ai_proxy.sh to fix GSAi routes"
    echo "2. Ensure OPENAPI_1_AUTH_TOKEN in ai-tokens.env is valid"
    echo "3. Check if the API key matches between Streamlit and APISIX"
    echo "4. Verify Docker network connectivity"
fi