#!/usr/bin/env bash
# Fix script for Enterprise environment API key issue

echo "🔧 Enterprise API Key Fix"
echo "========================"

# Get the APISIX admin key
ADMIN_KEY=$(grep "^APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)
if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY not found in apisix/.env"
    exit 1
fi

# Get the API key from violentutf/.env
VIOLENTUTF_API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf/.env | cut -d'=' -f2)
echo "Found ViolentUTF API key: ${VIOLENTUTF_API_KEY:0:12}...${VIOLENTUTF_API_KEY: -4}"

# Also check FastAPI .env in case they differ
FASTAPI_API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf_api/fastapi_app/.env | cut -d'=' -f2 || echo "")
if [ -n "$FASTAPI_API_KEY" ] && [ "$FASTAPI_API_KEY" != "$VIOLENTUTF_API_KEY" ]; then
    echo "⚠️  WARNING: FastAPI has different API key: ${FASTAPI_API_KEY:0:12}...${FASTAPI_API_KEY: -4}"
    echo "Using FastAPI key for consumer creation..."
    API_KEY="$FASTAPI_API_KEY"
else
    API_KEY="$VIOLENTUTF_API_KEY"
fi

# Create/update all three consumers with the correct API key
echo ""
echo "📝 Creating/updating APISIX consumers..."

for consumer in "violentutf-api" "violentutf-user" "violentutf_api_user"; do
    echo -n "  $consumer: "
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
        echo "✅ Updated"
    else
        echo "❌ Failed (HTTP $RESPONSE)"
    fi
done

# Verify GSAi routes have key-auth
echo ""
echo "🔍 Checking GSAi routes..."
ROUTE_9001=$(curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/routes/9001)
if echo "$ROUTE_9001" | jq -e '.value.plugins."key-auth"' > /dev/null 2>&1; then
    echo "✅ Route 9001 has key-auth plugin"
else
    echo "❌ Route 9001 missing key-auth plugin"
    echo "   Run ./fix_gsai_ai_proxy.sh to fix routes"
fi

# Test the API key
echo ""
echo "🧪 Testing API access..."
TEST_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "apikey: $API_KEY" \
    -H "Content-Type: application/json" \
    -X POST \
    http://localhost:9080/ai/gsai-api-1/chat/completions \
    -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}')

HTTP_CODE=$(echo "$TEST_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
echo "Test result: HTTP $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ API key authentication is working!"
elif [ "$HTTP_CODE" = "403" ]; then
    echo "❌ Still getting 403 Forbidden"
    echo "   This may indicate:"
    echo "   1. The route needs key-auth plugin (run ./fix_gsai_ai_proxy.sh)"
    echo "   2. GSAi Bearer token is invalid (check OPENAPI_1_AUTH_TOKEN in ai-tokens.env)"
    echo "   3. Model access is restricted for your GSAi token"
else
    echo "❌ Unexpected response"
    BODY=$(echo "$TEST_RESPONSE" | sed '/HTTP_CODE:/d')
    echo "   Response: $BODY"
fi

echo ""
echo "🔍 Checking APISIX admin permissions..."
APISIX_ADMIN_FILE="violentutf_api/fastapi_app/app/api/endpoints/apisix_admin.py"
if [ -f "$APISIX_ADMIN_FILE" ]; then
    if grep -q '"violentutf.web"' "$APISIX_ADMIN_FILE"; then
        echo "✅ User 'violentutf.web' is already in allowed users list"
    else
        echo "❌ User 'violentutf.web' is NOT in allowed users list"
        echo "   This will cause '403 Forbidden' errors in Simple Chat"
        echo ""
        echo "   To fix, add 'violentutf.web' to the allowed_users list in:"
        echo "   $APISIX_ADMIN_FILE"
        echo ""
        echo "   Change:"
        echo '   allowed_users = ["admin", "keycloak_user"]'
        echo "   To:"
        echo '   allowed_users = ["admin", "violentutf.web", "keycloak_user"]'
        echo ""
        echo "   Then restart FastAPI: docker restart violentutf_api"
    fi
else
    echo "⚠️  Cannot check permissions - file not found: $APISIX_ADMIN_FILE"
fi

echo ""
echo "💡 Next Steps:"
echo "1. If still failing, check that Streamlit is using the correct API key"
echo "2. Verify OPENAPI_1_AUTH_TOKEN in ai-tokens.env is valid"
echo "3. Run ./fix_gsai_ai_proxy.sh if routes need updating"
echo "4. Check Docker logs: docker logs apisix-apisix-1 --tail 50"
echo "5. If getting 403 on APISIX admin, fix the allowed_users list as shown above"
