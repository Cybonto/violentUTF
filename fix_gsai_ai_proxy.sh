#!/usr/bin/env bash
# Fix GSAi route to use ai-proxy with correct authentication

echo "🔧 Fixing GSAi Route with AI-Proxy"
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
echo "  OPENAPI_1_BASE_URL: $OPENAPI_1_BASE_URL"
echo "  APISIX Admin Key: ${ADMIN_KEY:0:10}..."

# Warn about SSL if using HTTPS
if [[ "$OPENAPI_1_BASE_URL" =~ ^https:// ]]; then
    echo "  ⚠️  Using HTTPS - SSL verification will be disabled for self-signed certificates"
fi

# First, let's check if we need HTTPS
SCHEME="http"
if [[ "$OPENAPI_1_BASE_URL" =~ ^https:// ]]; then
    SCHEME="https"
fi

# Extract host and port from the base URL
HOST_PORT=$(echo "$OPENAPI_1_BASE_URL" | sed -E 's|https?://||' | sed 's|/.*||')
echo "  Upstream: $SCHEME://$HOST_PORT"

# Update the GSAi chat route to use ai-proxy properly
echo -e "\n📝 Updating GSAi chat route (9001) with ai-proxy..."

UPDATE_RESPONSE=$(curl -s -X PUT "http://localhost:9180/apisix/admin/routes/9001" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"uri\": \"/ai/gsai-api-1/chat/completions\",
    \"name\": \"gsai-api-1-chat-completions\",
    \"methods\": [\"POST\"],
    \"plugins\": {
      \"key-auth\": {},
      \"ai-proxy\": {
        \"provider\": \"openai-compatible\",
        \"auth\": {
          \"header\": {
            \"Authorization\": \"Bearer $OPENAPI_1_AUTH_TOKEN\"
          }
        },
        \"model\": {
          \"passthrough\": true
        },
        \"override\": {
          \"endpoint\": \"$OPENAPI_1_BASE_URL/api/v1/chat/completions\"
        },
        \"timeout\": 30000,
        \"keepalive\": true,
        \"keepalive_timeout\": 60000,
        \"keepalive_pool\": 30,
        \"ssl_verify\": false
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
      \"scheme\": \"$SCHEME\",
      \"nodes\": {
        \"$HOST_PORT\": 1
      }
    }
  }")

if echo "$UPDATE_RESPONSE" | grep -q '"id":"9001"'; then
    echo "✅ Route 9001 updated successfully with ai-proxy"
else
    echo "❌ Failed to update route 9001"
    echo "Response: $UPDATE_RESPONSE"
fi

# Models route should use proxy-rewrite (ai-proxy doesn't work well with GET)
echo -e "\n📝 Updating GSAi models route (9101) with proxy-rewrite..."

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
            \"Authorization\": \"Bearer $OPENAPI_1_AUTH_TOKEN\"
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
      \"scheme\": \"$SCHEME\",
      \"nodes\": {
        \"$HOST_PORT\": 1
      }
    }
  }")

if echo "$UPDATE_RESPONSE" | grep -q '"id":"9101"'; then
    echo "✅ Route 9101 updated successfully with proxy-rewrite"
else
    echo "❌ Failed to update route 9101"
fi

# Make sure we have the correct consumer
echo -e "\n🔑 Checking consumer configuration..."
CONSUMER_CHECK=$(curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/consumers | jq -r --arg key "$API_KEY" '.list[].value | select(.plugins."key-auth".key == $key) | .username')

if [ -n "$CONSUMER_CHECK" ]; then
    echo "✅ Found consumer: $CONSUMER_CHECK"
else
    echo "❌ No consumer found with the API key"
    echo "Creating consumer..."
    
    curl -s -X PUT "http://localhost:9180/apisix/admin/consumers/violentutf-api" \
      -H "X-API-KEY: $ADMIN_KEY" \
      -H "Content-Type: application/json" \
      -d "{
        \"username\": \"violentutf-api\",
        \"plugins\": {
          \"key-auth\": {
            \"key\": \"$API_KEY\"
          }
        }
      }" > /dev/null
      
    echo "✅ Created consumer violentutf-api"
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
    echo "Response preview: $(echo "$BODY" | head -c 200)..."
elif [ "$HTTP_CODE" = "401" ]; then
    echo "⚠️  Authentication error - check consumer setup"
    echo "Response: $BODY"
elif [ "$HTTP_CODE" = "403" ]; then
    echo "⚠️  Forbidden - may be model access issue"
    echo "Response: $BODY"
else
    echo "Response: $BODY"
fi

echo -e "\n✅ GSAi route fix completed!"