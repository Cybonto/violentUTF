#!/bin/bash

# GSAi Integration Test Script
# This script verifies that GSAi API integration is working correctly
# Run this in Environment B where GSAi is configured

set -e

echo "=== GSAi Integration Test Script ==="
echo "This script will verify GSAi API integration in ViolentUTF"
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f ai-tokens.env ]; then
    source ai-tokens.env
fi

if [ -f apisix/.env ]; then
    source apisix/.env
fi

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

echo "Step 1: Verify GSAi Configuration"
echo "================================="

# Check if OpenAPI is enabled
if [ "$OPENAPI_ENABLED" = "true" ]; then
    print_status 0 "OpenAPI is enabled"
else
    print_status 1 "OpenAPI is NOT enabled"
    echo "Please set OPENAPI_ENABLED=true in ai-tokens.env"
    exit 1
fi

# Check required commands
for cmd in curl jq docker; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}❌ Required command '$cmd' not found${NC}"
        echo "Please install $cmd before running this script"
        exit 1
    fi
done

# Check GSAi configuration
if [ "$OPENAPI_1_ENABLED" = "true" ] && [ -n "$OPENAPI_1_ID" ]; then
    print_status 0 "GSAi provider configured: ID=$OPENAPI_1_ID"
    echo "   Name: $OPENAPI_1_NAME"
    echo "   Base URL: $OPENAPI_1_BASE_URL"
    echo "   Auth Type: $OPENAPI_1_AUTH_TYPE"
    # Security: Never display token values
    if [ -n "$OPENAPI_1_AUTH_TOKEN" ]; then
        echo "   Auth Token: [CONFIGURED - ${#OPENAPI_1_AUTH_TOKEN} chars]"
    else
        echo "   Auth Token: [NOT SET]"
    fi
else
    print_status 1 "GSAi provider NOT configured"
    echo "Please configure OPENAPI_1_* variables in ai-tokens.env"
    exit 1
fi

echo
echo "Step 2: Check APISIX Routes"
echo "==========================="

# Check if GSAi routes exist
echo "Checking for GSAi routes in APISIX..."
# Security: Properly escape provider ID to prevent injection
escaped_provider_id=$(printf '%s' "$OPENAPI_1_ID" | sed 's/[[\.*^$()+?{|]/\\&/g')
gsai_routes=$(curl -s --max-time 10 -X GET "http://localhost:9180/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null | \
    jq --arg provider "$escaped_provider_id" -r '.list[]?.value | select(.uri | contains("/openapi/\($provider)")) | {id: .id, uri: .uri, name: .name}' 2>/dev/null)

if [ -n "$gsai_routes" ]; then
    print_status 0 "Found GSAi routes in APISIX:"
    echo "$gsai_routes" | jq .
else
    print_status 1 "No GSAi routes found in APISIX"
    echo "You may need to run the setup script to create routes"
fi

echo
echo "Step 3: Test Model Discovery"
echo "============================"

# Test model discovery through FastAPI
echo "Testing model discovery for openapi-${OPENAPI_1_ID}..."
model_response=$(curl -s --max-time 10 -X GET "http://localhost:9080/api/v1/generators/apisix/models?provider=openapi-${OPENAPI_1_ID}" \
    -H "apikey: ${VIOLENTUTF_API_KEY:-test-key}" 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$model_response" ]; then
    model_count=$(echo "$model_response" | jq '. | length' 2>/dev/null || echo "0")
    if [ "$model_count" -gt 0 ]; then
        print_status 0 "Model discovery successful - found $model_count models:"
        echo "$model_response" | jq -r '.[]' 2>/dev/null | head -10
    else
        print_status 1 "Model discovery returned empty list"
        echo "This may indicate authentication issues or network problems"
    fi
else
    print_status 1 "Model discovery request failed"
fi

echo
echo "Step 4: Test Direct GSAi API Access"
echo "==================================="

# Test direct access to GSAi models endpoint
echo "Testing direct access to GSAi /api/v1/models endpoint..."
direct_response=$(curl -s --max-time 10 -k -X GET "${OPENAPI_1_BASE_URL}/api/v1/models" \
    -H "Authorization: Bearer ${OPENAPI_1_AUTH_TOKEN}" \
    -H "Accept: application/json" 2>/dev/null)

if [ $? -eq 0 ]; then
    if echo "$direct_response" | jq -e '.data' >/dev/null 2>&1; then
        model_count=$(echo "$direct_response" | jq '.data | length')
        print_status 0 "Direct API access successful - found $model_count models"
        echo "Sample models:"
        echo "$direct_response" | jq -r '.data[:3][] | "  - \(.id) (by \(.owned_by))"' 2>/dev/null
    else
        print_status 1 "Direct API returned unexpected response"
        echo "Response: $direct_response"
    fi
else
    print_status 1 "Direct API access failed"
    echo "Check network connectivity and authentication token"
fi

echo
echo "Step 5: Test FastAPI Container Network"
echo "====================================="

# Test if FastAPI can reach APISIX admin
echo "Testing FastAPI → APISIX admin connectivity..."
container_test=$(docker exec violentutf_api sh -c 'curl -s -w "HTTP_CODE:%{http_code}" http://apisix-apisix-1:9180/apisix/admin/health' 2>/dev/null || echo "FAILED")

if [[ "$container_test" == *"HTTP_CODE:200"* ]]; then
    print_status 0 "FastAPI can reach APISIX admin API"
else
    print_status 1 "FastAPI cannot reach APISIX admin API"
    echo "This is critical for endpoint discovery"
fi

# Check APISIX_ADMIN_URL in FastAPI
echo "Checking APISIX_ADMIN_URL in FastAPI container..."
admin_url=$(docker exec violentutf_api sh -c 'echo $APISIX_ADMIN_URL' 2>/dev/null || echo "NOT SET")
if [ "$admin_url" = "http://apisix-apisix-1:9180" ]; then
    print_status 0 "APISIX_ADMIN_URL correctly set: $admin_url"
else
    print_status 1 "APISIX_ADMIN_URL incorrect or not set: $admin_url"
fi

echo
echo "Step 6: Test Chat Completion Endpoint"
echo "===================================="

# Find the chat completions route
echo "Looking for GSAi chat completions route..."
chat_route=$(curl -s --max-time 10 -X GET "http://localhost:9180/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null | \
    jq --arg provider "$escaped_provider_id" -r '.list[]?.value | select(.uri | contains("/openapi/\($provider)") and contains("/chat/completions")) | .uri' | head -1)

if [ -n "$chat_route" ]; then
    print_status 0 "Found chat completions route: $chat_route"
    
    # Try a test request
    echo "Sending test request..."
    test_payload='{
        "model": "claude_3_5_sonnet",
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 10
    }'
    
    test_response=$(curl -s --max-time 30 -X POST "http://localhost:9080${chat_route}" \
        -H "apikey: ${VIOLENTUTF_API_KEY:-test-key}" \
        -H "Content-Type: application/json" \
        -d "$test_payload" 2>/dev/null)
    
    if echo "$test_response" | jq -e '.choices' >/dev/null 2>&1; then
        print_status 0 "Chat completion test successful!"
        echo "Response: $(echo "$test_response" | jq -r '.choices[0].message.content' 2>/dev/null)"
    else
        print_status 1 "Chat completion test failed"
        echo "Response: $test_response"
    fi
else
    print_status 1 "No chat completions route found for GSAi"
fi

echo
echo "=== Summary ==="
echo "If all tests passed, GSAi integration is working correctly."
echo "If any tests failed, check the error messages above for guidance."