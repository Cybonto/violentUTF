#!/usr/bin/env bash
# Test different GSAi authentication formats

echo "🧪 Testing GSAi Authentication Formats"
echo "====================================="

# Load environment
source ai-tokens.env
ADMIN_KEY=$(grep "^APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)

echo "GSAi URL: $OPENAPI_1_BASE_URL"
echo "Token: ${OPENAPI_1_AUTH_TOKEN:0:20}..."
echo ""

# Test 1: Standard Bearer format (current)
echo "1. Testing Bearer format:"
curl -s -w "\nHTTP: %{http_code}\n" -k \
    -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -X POST "$OPENAPI_1_BASE_URL/api/v1/chat/completions" \
    -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' | tail -2

# Test 2: Key=value format
echo -e "\n2. Testing key=value format:"
curl -s -w "\nHTTP: %{http_code}\n" -k \
    -H "Authorization: apikey=$OPENAPI_1_AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -X POST "$OPENAPI_1_BASE_URL/api/v1/chat/completions" \
    -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' | tail -2

# Test 3: API-Key header
echo -e "\n3. Testing API-Key header:"
curl -s -w "\nHTTP: %{http_code}\n" -k \
    -H "API-Key: $OPENAPI_1_AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -X POST "$OPENAPI_1_BASE_URL/api/v1/chat/completions" \
    -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' | tail -2

# Test 4: X-API-Key header
echo -e "\n4. Testing X-API-Key header:"
curl -s -w "\nHTTP: %{http_code}\n" -k \
    -H "X-API-Key: $OPENAPI_1_AUTH_TOKEN" \
    -H "Content-Type: application/json" \
    -X POST "$OPENAPI_1_BASE_URL/api/v1/chat/completions" \
    -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}], "max_tokens": 1}' | tail -2

echo -e "\n📝 Summary:"
echo "If any test returns HTTP 200, that's the correct auth format for GSAi"
