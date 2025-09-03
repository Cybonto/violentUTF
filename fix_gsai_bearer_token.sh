#!/usr/bin/env bash
# Fix GSAi Bearer token format issue

echo "🔧 Fixing GSAi Bearer Token Format"
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
echo "  OPENAPI_1_AUTH_TOKEN: ${OPENAPI_1_AUTH_TOKEN:0:20}..."
echo "  OPENAPI_1_BASE_URL: $OPENAPI_1_BASE_URL"
echo "  APISIX Admin Key: ${ADMIN_KEY:0:10}..."
echo ""

# Check if the auth token might be in the wrong format
if [[ "$OPENAPI_1_AUTH_TOKEN" == *"="* ]]; then
    echo "✅ Auth token appears to contain key=value format"
else
    echo "⚠️  WARNING: Auth token may not be in the expected format"
    echo "   GSAi expects: key=value format in Authorization header"
    echo "   Current token: ${OPENAPI_1_AUTH_TOKEN:0:20}..."
fi

# Update the GSAi chat route to use the correct Authorization format
echo -e "\n📝 Updating GSAi chat route (9001) with corrected auth format..."

# First, let's check if we need HTTPS
SCHEME="http"
if [[ "$OPENAPI_1_BASE_URL" =~ ^https:// ]]; then
    SCHEME="https"
fi

# Extract host and port from base URL
HOST_PORT=$(echo "$OPENAPI_1_BASE_URL" | sed -E 's|https?://||' | sed 's|/.*||')

# Update route with correct Authorization header format
UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/9001" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"uri\": \"/ai/gsai-api-1/chat/completions\",
    \"name\": \"gsai-api-1-chat-completions\",
    \"methods\": [\"POST\"],
    \"upstream\": {
      \"type\": \"roundrobin\",
      \"scheme\": \"$SCHEME\",
      \"nodes\": {
        \"$HOST_PORT\": 1
      }
    },
    \"plugins\": {
      \"key-auth\": {},
      \"proxy-rewrite\": {
        \"uri\": \"/api/v1/chat/completions\",
        \"headers\": {
          \"set\": {
            \"Authorization\": \"$OPENAPI_1_AUTH_TOKEN\"
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
    \"upstream\": {
      \"type\": \"roundrobin\",
      \"scheme\": \"$SCHEME\",
      \"nodes\": {
        \"$HOST_PORT\": 1
      }
    },
    \"plugins\": {
      \"key-auth\": {},
      \"proxy-rewrite\": {
        \"uri\": \"/api/v1/models\",
        \"headers\": {
          \"set\": {
            \"Authorization\": \"$OPENAPI_1_AUTH_TOKEN\"
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
    }
  }")

if echo "$UPDATE_RESPONSE" | grep -q '"id":"9101"'; then
    echo "✅ Route 9101 updated successfully"
else
    echo "❌ Failed to update route 9101"
fi

# Test the route with direct Authorization header
echo -e "\n🧪 Testing GSAi API directly..."
echo "Testing with direct curl to GSAi endpoint:"
TEST_DIRECT=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: $OPENAPI_1_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST \
  "$OPENAPI_1_BASE_URL/api/v1/chat/completions" \
  -d '{
    "model": "llama3211b",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }')

HTTP_CODE=$(echo "$TEST_DIRECT" | grep "HTTP_CODE:" | cut -d: -f2)
echo "Direct test result: HTTP $HTTP_CODE"
if [ "$HTTP_CODE" != "200" ]; then
    BODY=$(echo "$TEST_DIRECT" | sed '/HTTP_CODE:/d')
    echo "Response: $BODY"
fi

# Test through APISIX
echo -e "\n🧪 Testing through APISIX gateway..."
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
echo "APISIX test result: HTTP $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Authentication working!"
elif [ "$HTTP_CODE" = "403" ] || [ "$HTTP_CODE" = "401" ]; then
    echo "❌ Authentication still failing"
    BODY=$(echo "$TEST_RESPONSE" | sed '/HTTP_CODE:/d')
    echo "Response: $BODY"
    echo ""
    echo "💡 The error suggests GSAi expects a different Authorization format."
    echo "   Current format: Bearer token or similar"
    echo "   Expected format: key=value format"
    echo ""
    echo "   Please check your OPENAPI_1_AUTH_TOKEN in ai-tokens.env"
    echo "   It should be in the format that GSAi expects, e.g.:"
    echo "   - 'api-key=your_actual_key'"
    echo "   - 'token=your_actual_token'"
    echo "   - Or whatever format GSAi documentation specifies"
fi

echo -e "\n✅ Route update completed!"
