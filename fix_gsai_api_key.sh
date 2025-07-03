#!/bin/bash

# Fix GSAi API Key Authentication
# This script registers the API key with APISIX's consumer system

set -eo pipefail

echo "=== Fixing GSAi API Key Authentication ==="
echo

# Load environment variables
echo "Loading environment configuration..."
set -a
if [ -f "./apisix/.env" ]; then
    source "./apisix/.env"
fi
if [ -f "./violentutf_api/fastapi_app/.env" ]; then
    source "./violentutf_api/fastapi_app/.env"
fi
set +a

if [ -z "${APISIX_ADMIN_KEY:-}" ]; then
    echo "❌ APISIX_ADMIN_KEY not found"
    exit 1
fi

if [ -z "${VIOLENTUTF_API_KEY:-}" ]; then
    echo "❌ VIOLENTUTF_API_KEY not found"
    # Try to get from container
    VIOLENTUTF_API_KEY=$(docker exec violentutf_api printenv VIOLENTUTF_API_KEY 2>/dev/null || echo "")
    if [ -z "${VIOLENTUTF_API_KEY}" ]; then
        echo "❌ Could not find VIOLENTUTF_API_KEY anywhere"
        exit 1
    fi
fi

echo "✅ API Keys loaded: APISIX=[REDACTED-${#APISIX_ADMIN_KEY}] VIOLENTUTF=[REDACTED-${#VIOLENTUTF_API_KEY}]"

echo
echo "Step 1: Check if consumer exists"
echo "==============================="

# Check if consumer already exists
consumer_check=$(curl -s "http://localhost:9180/apisix/admin/consumers/violentutf_api_user" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null || echo '{"error": "not found"}')

if echo "$consumer_check" | grep -q '"username":"violentutf_api_user"'; then
    echo "✅ Consumer 'violentutf_api_user' already exists"
else
    echo "❌ Consumer 'violentutf_api_user' does not exist - creating..."
    
    echo
    echo "Step 2: Create API key consumer"
    echo "==============================="
    
    # Create consumer with API key
    consumer_config='{
      "username": "violentutf_api_user",
      "plugins": {
        "key-auth": {
          "key": "'"${VIOLENTUTF_API_KEY}"'"
        }
      }
    }'
    
    echo "Creating consumer with API key..."
    consumer_response=$(curl -s -X PUT "http://localhost:9180/apisix/admin/consumers/violentutf_api_user" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d "$consumer_config" 2>/dev/null || echo '{"error": "Failed"}')
    
    if echo "$consumer_response" | grep -q '"username":"violentutf_api_user"'; then
        echo "✅ Created API key consumer successfully"
    else
        echo "❌ Failed to create consumer"
        # Redact sensitive data from response
        redacted_response=$(echo "$consumer_response" | sed -E 's/"key":"[^"]+"/key":"[REDACTED]"/g')
        echo "Response: $redacted_response"
        exit 1
    fi
fi

echo
echo "Step 3: Test GSAi endpoints with registered API key"
echo "=================================================="

echo "Testing models endpoint..."
models_test=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "X-API-Key: ${VIOLENTUTF_API_KEY}" \
    "http://localhost:9080/ai/gsai/models" 2>/dev/null)

models_http_code=$(echo "$models_test" | grep "HTTP_CODE:" | cut -d: -f2)
models_body=$(echo "$models_test" | grep -v "HTTP_CODE:")

echo "Models endpoint HTTP status: $models_http_code"
if [ "$models_http_code" = "200" ]; then
    echo "✅ Models endpoint working!"
    if echo "$models_body" | jq -e '.data[0]' >/dev/null 2>&1; then
        model_count=$(echo "$models_body" | jq '.data | length' 2>/dev/null || echo "0")
        echo "Found $model_count models:"
        echo "$models_body" | jq -r '.data[] | "  - \(.id)"' 2>/dev/null | head -3
    fi
else
    echo "❌ Models endpoint still failing"
    echo "Response: $models_body"
fi

echo
echo "Testing chat completions endpoint..."
chat_test=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "X-API-Key: ${VIOLENTUTF_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"claude_3_5_sonnet","messages":[{"role":"user","content":"Say: GSAi working!"}]}' \
    "http://localhost:9080/ai/gsai/chat/completions" 2>/dev/null)

chat_http_code=$(echo "$chat_test" | grep "HTTP_CODE:" | cut -d: -f2)
chat_body=$(echo "$chat_test" | grep -v "HTTP_CODE:")

echo "Chat completions HTTP status: $chat_http_code"
if [ "$chat_http_code" = "200" ]; then
    echo "✅ Chat completions endpoint working!"
    if echo "$chat_body" | jq -e '.choices[0].message.content' >/dev/null 2>&1; then
        chat_content=$(echo "$chat_body" | jq -r '.choices[0].message.content' 2>/dev/null)
        echo "GSAi responded: \"$chat_content\""
    fi
else
    echo "❌ Chat completions endpoint still failing"
    echo "Response: $chat_body"
fi

echo
echo "=== GSAi API Key Fix Summary ==="
if [ "$models_http_code" = "200" ] && [ "$chat_http_code" = "200" ]; then
    echo "🎉 SUCCESS! GSAi static routes are now working!"
    echo "✅ Models endpoint: http://localhost:9080/ai/gsai/models"
    echo "✅ Chat endpoint: http://localhost:9080/ai/gsai/chat/completions"
    echo "🔑 Authentication: X-API-Key with registered consumer"
    echo
    echo "GSAi now works like OpenAI/Anthropic with simple static authentication!"
else
    echo "❌ GSAi endpoints still not working"
    echo "Check APISIX logs: docker logs apisix-apisix-1 --tail 20"
fi