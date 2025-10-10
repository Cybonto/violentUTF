#!/usr/bin/env bash
# Diagnostic script for API key authentication issues

echo "🔍 GSAi Authentication Diagnostic"
echo "================================="

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
echo "🧪 Testing GSAi Routes:"
echo "----------------------"

# Test without API key (since key-auth should be removed)
echo -n "Test 1 - No API key header: "
TEST1=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "Content-Type: application/json" \
    -X POST \
    http://localhost:9080/ai/gsai-api-1/chat/completions \
    -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' 2>&1)
HTTP_CODE=$(echo "$TEST1" | grep "HTTP_CODE:" | cut -d: -f2)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Success (HTTP 200)"
elif [ "$HTTP_CODE" = "403" ]; then
    echo "❌ Failed (HTTP 403 - GSAi API rejected request)"
    BODY=$(echo "$TEST1" | sed '/HTTP_CODE:/d')
    echo "   Response: $BODY"
elif [ "$HTTP_CODE" = "500" ]; then
    echo "❌ Failed (HTTP 500 - SSL or connection issue)"
    BODY=$(echo "$TEST1" | sed '/HTTP_CODE:/d')
    echo "   Response: $BODY"
else
    echo "❌ Failed (HTTP $HTTP_CODE)"
    BODY=$(echo "$TEST1" | sed '/HTTP_CODE:/d')
    echo "   Response: $BODY"
fi

# Test direct to GSAi (bypass APISIX)
echo ""
echo -n "Test 2 - Direct to GSAi API: "
source ai-tokens.env
if [ -n "$OPENAPI_1_BASE_URL" ] && [ -n "$OPENAPI_1_AUTH_TOKEN" ]; then
    TEST2=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST \
        "$OPENAPI_1_BASE_URL/api/v1/chat/completions" \
        -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' 2>&1)
    HTTP_CODE=$(echo "$TEST2" | grep "HTTP_CODE:" | cut -d: -f2)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Direct access works"
    else
        echo "❌ Direct access failed (HTTP $HTTP_CODE)"
        echo "   This suggests the issue is with GSAi API, not APISIX"
    fi
else
    echo "⚠️  Cannot test - OPENAPI_1 not configured"
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
echo "🔐 SSL/TLS Configuration:"
echo "-----------------------"
source ai-tokens.env
echo "OPENAPI_1_SSL_VERIFY: ${OPENAPI_1_SSL_VERIFY:-not set (defaults to true)}"
echo "OPENAPI_1_BASE_URL: $OPENAPI_1_BASE_URL"
if [[ "$OPENAPI_1_BASE_URL" =~ ^https:// ]]; then
    echo "⚠️  Using HTTPS - ensure SSL_VERIFY is set correctly for self-signed certs"
fi

echo ""
echo "💡 Recommendations:"
echo "-----------------"
if [ "$HTTP_CODE" = "403" ]; then
    echo "1. GSAi is rejecting the request. Check:"
    echo "   - Is your Bearer token valid?"
    echo "   - Do you have access to the 'llama3211b' model?"
    echo "   - Try a different model like 'claude_3_haiku'"
elif [ "$HTTP_CODE" = "500" ]; then
    echo "1. Server error. Check:"
    echo "   - SSL certificate issues (set OPENAPI_1_SSL_VERIFY=false for self-signed)"
    echo "   - Run ./fix_gsai_ai_proxy.sh to update routes"
    echo "   - Check APISIX logs: docker logs apisix-apisix-1 --tail 20"
elif [ "$HTTP_CODE" != "200" ]; then
    echo "1. Run ./fix_gsai_ai_proxy.sh to fix GSAi routes"
    echo "2. Ensure OPENAPI_1_AUTH_TOKEN in ai-tokens.env is valid"
    echo "3. Check Docker network connectivity"
fi
