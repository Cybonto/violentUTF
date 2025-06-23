#!/bin/bash

# Test script for ViolentUTF services

echo "==================================="
echo "ViolentUTF Services Test Suite"
echo "==================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local name=$1
    local url=$2
    local expected_status=$3
    
    echo -n "Testing $name: "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}PASS${NC} (HTTP $response)"
    else
        echo -e "${RED}FAIL${NC} (Expected $expected_status, got $response)"
    fi
}

# Test APISIX Admin API
test_endpoint "APISIX Admin API" "http://localhost:9180/apisix/admin/routes" "401"

# Test APISIX Gateway
test_endpoint "APISIX Gateway" "http://localhost:9080/" "404"

# Test Keycloak
test_endpoint "Keycloak" "http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration" "200"

# Test FastAPI through APISIX
test_endpoint "FastAPI Health (via APISIX)" "http://localhost:9080/api/v1/health" "200"

# Test FastAPI Echo endpoint
test_endpoint "FastAPI Echo (via APISIX)" "http://localhost:9080/api/v1/test/echo/test" "200"

# Test FastAPI Auth endpoint with invalid key
test_endpoint "FastAPI Auth (via APISIX)" "http://localhost:9080/api/v1/auth/me" "401"

# Test FastAPI Documentation endpoints
test_endpoint "FastAPI Docs (via APISIX)" "http://localhost:9080/api/docs" "200"

test_endpoint "FastAPI ReDoc (via APISIX)" "http://localhost:9080/api/redoc" "200"

# Test that direct FastAPI access is blocked
echo -n "Testing FastAPI Direct Access Block: "
if ! curl -s --connect-timeout 2 http://localhost:8000 &>/dev/null; then
    echo -e "${GREEN}PASS${NC} (Correctly blocked)"
else
    echo -e "${RED}FAIL${NC} (Should not be accessible)"
fi

echo ""
echo "==================================="
echo "Test Summary Complete"
echo "==================================="