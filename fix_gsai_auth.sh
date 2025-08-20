#!/usr/bin/env bash
# Fix GSAi route authentication

echo "🔧 Fixing GSAi Route Authentication"
echo "=================================="

# Get tokens
ADMIN_KEY=$(grep "^APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)
source ai-tokens.env

# Get API key from environment
API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf/.env | cut -d'=' -f2 || echo "")
if [ -z "$API_KEY" ]; then
    echo "❌ ERROR: VIOLENTUTF_API_KEY not found in violentutf/.env"
    exit 1
fi

echo "Using configuration:"
echo "  OPENAPI_1_AUTH_TOKEN: ${OPENAPI_1_AUTH_TOKEN:0:10}..."
echo "  APISIX Admin Key: ${ADMIN_KEY:0:10}..."

# Update the GSAi chat route to accept API key authentication
echo -e "\n📝 Updating GSAi chat route (9001)..."

UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/9001" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"uri\": \"/ai/gsai-api-1/chat/completions\",
    \"name\": \"gsai-api-1-chat-completions\",
    \"methods\": [\"POST\"],
    \"plugins\": {
      \"key-auth\": {},
      \"proxy-rewrite\": {
        \"uri\": \"/api/v1/chat/completions\",
        \"headers\": {
          \"set\": {
            \"Authorization\": \"Bearer $OPENAPI_1_AUTH_TOKEN\",
            \"Host\": \"localhost\"
          }
        }
      },
      \"cors\": {
        \"allow_origins\": \"http://localhost:8501,http://localhost:3000\",
        \"allow_methods\": \"GET,POST,OPTIONS\",
        \"allow_headers\": \"Authorization,Content-Type,X-Requested-With,apikey,X-API-KEY\",
        \"allow_credential\": true,
        \"max_age\": 3600
      }
    },
    \"upstream\": {
      \"type\": \"roundrobin\",
      \"scheme\": \"http\",
      \"nodes\": {
        \"host.docker.internal:8081\": 1
      },
      \"pass_host\": \"rewrite\",
      \"upstream_host\": \"localhost\"
    }
  }")

if echo "$UPDATE_RESPONSE" | grep -q '"id":"9001"'; then
    echo "✅ Route 9001 updated successfully"
else
    echo "❌ Failed to update route 9001"
    echo "Response: $UPDATE_RESPONSE"
fi

# Also update the models route
echo -e "\n📝 Updating GSAi models route (9101)..."

UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/9101" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"uri\": \"/ai/gsai-api-1/models\",
    \"name\": \"gsai-api-1-models\",
    \"methods\": [\"GET\"],
    \"plugins\": {
      \"key-auth\": {},
      \"proxy-rewrite\": {
        \"uri\": \"/api/v1/models\",
        \"headers\": {
          \"set\": {
            \"Authorization\": \"Bearer $OPENAPI_1_AUTH_TOKEN\",
            \"Host\": \"localhost\"
          }
        }
      },
      \"cors\": {
        \"allow_origins\": \"http://localhost:8501,http://localhost:3000\",
        \"allow_methods\": \"GET,POST,OPTIONS\",
        \"allow_headers\": \"Authorization,Content-Type,X-Requested-With,apikey,X-API-KEY\",
        \"allow_credential\": true,
        \"max_age\": 3600
      }
    },
    \"upstream\": {
      \"type\": \"roundrobin\",
      \"scheme\": \"http\",
      \"nodes\": {
        \"host.docker.internal:8081\": 1
      },
      \"pass_host\": \"rewrite\",
      \"upstream_host\": \"localhost\"
    }
  }")

if echo "$UPDATE_RESPONSE" | grep -q '"id":"9101"'; then
    echo "✅ Route 9101 updated successfully"
else
    echo "❌ Failed to update route 9101"
fi

# Test the route
echo -e "\n🧪 Testing GSAi API access..."
TEST_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -X POST \
  http://localhost:9080/ai/gsai-api-1/chat/completions \
  -d '{
    "model": "llama3211b",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }')

HTTP_CODE=$(echo "$TEST_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$TEST_RESPONSE" | sed '/HTTP_CODE:/d')

echo -e "\nTest result:"
echo "HTTP Status: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Authentication working!"
elif [ "$HTTP_CODE" = "401" ]; then
    echo "❌ Still getting authentication error"
    echo "Response: $BODY"
elif [ "$HTTP_CODE" = "403" ]; then
    echo "❌ Still getting forbidden error"
    echo "Response: $BODY"
else
    echo "Response: $BODY"
fi

echo -e "\n✅ GSAi route fix completed!"
