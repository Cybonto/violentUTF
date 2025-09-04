#!/usr/bin/env bash
# Test API authentication and routing issues

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️ $1${NC}"; }

# Get inputs - use provided token or prompt
FASTAPI_TOKEN="${FASTAPI_TOKEN:-4mHVvoZralWPYJvo5W5KgWyob4gOEow2}"
if [ -z "$FASTAPI_TOKEN" ]; then
    echo -n "Enter your FastAPI Bearer token: "
    read -s FASTAPI_TOKEN
    echo
fi

FASTAPI_BASE_URL="${FASTAPI_BASE_URL:-http://localhost:9080}"

echo -e "${BLUE}🔐 API Authentication & Routing Test${NC}"
echo "Testing why /api/* routes return 403 Forbidden"
echo

# Test 1: Compare working vs failing endpoints
print_info "1. Comparing working vs failing endpoints..."

echo "Testing /api/v1/health (works):"
health_response=$(curl -s -w "\nSTATUS:%{http_code}" \
    -H "Authorization: Bearer $FASTAPI_TOKEN" \
    "$FASTAPI_BASE_URL/api/v1/health")
health_status=$(echo "$health_response" | grep "STATUS:" | cut -d: -f2)
echo "  Status: $health_status"

echo
echo "Testing /api/v1/generators (fails with 403):"
gen_response=$(curl -s -w "\nSTATUS:%{http_code}" \
    -H "Authorization: Bearer $FASTAPI_TOKEN" \
    "$FASTAPI_BASE_URL/api/v1/generators")
gen_status=$(echo "$gen_response" | grep "STATUS:" | cut -d: -f2)
gen_body=$(echo "$gen_response" | sed '/STATUS:/d')
echo "  Status: $gen_status"
echo "  Response: $gen_body"

# Test 2: Check token validity
print_info "2. Testing token validity..."
token_response=$(curl -s -w "\nSTATUS:%{http_code}" \
    -H "Authorization: Bearer $FASTAPI_TOKEN" \
    "$FASTAPI_BASE_URL/api/v1/auth/token/info" 2>/dev/null || echo "STATUS:000")
token_status=$(echo "$token_response" | grep "STATUS:" | cut -d: -f2)

if [ "$token_status" = "200" ]; then
    print_success "Token is valid"
    token_body=$(echo "$token_response" | sed '/STATUS:/d')
    echo "  Token info: $token_body"
elif [ "$token_status" = "000" ]; then
    print_warning "Token info endpoint doesn't exist"
else
    print_warning "Token validation failed: $token_status"
fi

# Test 3: Test different auth headers
print_info "3. Testing different authentication methods..."

# Test without auth
echo "Testing /api/v1/generators without auth:"
noauth_response=$(curl -s -w "\nSTATUS:%{http_code}" \
    "$FASTAPI_BASE_URL/api/v1/generators" 2>/dev/null)
noauth_status=$(echo "$noauth_response" | grep "STATUS:" | cut -d: -f2)
echo "  Status: $noauth_status (expected 401 if auth required)"

# Test with different header format
echo "Testing with 'Bearer ' prefix (if not already present):"
if [[ "$FASTAPI_TOKEN" != Bearer* ]]; then
    bearer_response=$(curl -s -w "\nSTATUS:%{http_code}" \
        -H "Authorization: Bearer $FASTAPI_TOKEN" \
        "$FASTAPI_BASE_URL/api/v1/generators")
    bearer_status=$(echo "$bearer_response" | grep "STATUS:" | cut -d: -f2)
    echo "  Status: $bearer_status"
else
    echo "  Token already has Bearer prefix"
fi

# Test 4: Check available methods
print_info "4. Testing different HTTP methods..."

echo "Testing GET /api/v1/generators:"
get_status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X GET -H "Authorization: Bearer $FASTAPI_TOKEN" \
    "$FASTAPI_BASE_URL/api/v1/generators")
echo "  GET: $get_status"

echo "Testing POST /api/v1/orchestrators/create:"
post_response=$(curl -s -w "\nSTATUS:%{http_code}" \
    -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $FASTAPI_TOKEN" \
    -d '{}' \
    "$FASTAPI_BASE_URL/api/v1/orchestrators/create")
post_status=$(echo "$post_response" | grep "STATUS:" | cut -d: -f2)
echo "  POST: $post_status"

if [ "$post_status" = "422" ]; then
    print_success "POST works! (422 = validation error for empty payload)"
elif [ "$post_status" = "403" ]; then
    print_error "POST still forbidden"
else
    echo "  Unexpected POST status: $post_status"
fi

# Test 5: Check if it's a CORS issue
print_info "5. Testing CORS headers..."
cors_response=$(curl -s -v -H "Authorization: Bearer $FASTAPI_TOKEN" \
    "$FASTAPI_BASE_URL/api/v1/generators" 2>&1)
    
if echo "$cors_response" | grep -i "access-control" > /dev/null; then
    print_info "CORS headers present in response"
else
    print_warning "No CORS headers found"
fi

if echo "$cors_response" | grep -i "options" > /dev/null; then
    print_info "OPTIONS method may be required"
fi

echo
print_info "🎯 RECOMMENDATIONS:"

if [ "$health_status" = "200" ] && [ "$gen_status" = "403" ]; then
    echo "  • Health works but generators fail → Endpoint-specific authorization issue"
    echo "  • Check if generators endpoint requires special permissions"
    echo "  • Verify token has correct scopes/roles for generator access"
fi

if [ "$post_status" = "422" ]; then
    print_success "  • Orchestrator endpoint IS working! Just needs proper payload"
    echo "  • This solves the 404 conversation error - endpoint exists at /api/v1/orchestrators/create"
fi

if [ "$token_status" != "200" ]; then
    echo "  • Verify token is valid and not expired"
    echo "  • Check token format and authentication method"
fi

echo
echo "Next steps:"
echo "1. Fix token permissions for generator endpoints"
echo "2. Update frontend to use /api/v1/orchestrators/create (not /api/v1/orchestrator/create)"
echo "3. Test actual API calls with proper payloads"