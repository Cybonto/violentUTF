#!/bin/bash

# Test script to verify regex_uri configuration in APISIX

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Testing regex_uri Configuration ===${NC}"
echo

# Get APISIX admin key
if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo -n "Enter APISIX Admin Key: "
    read -s APISIX_ADMIN_KEY
    echo
fi

APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

# Test route configuration
test_route_id="test-regex-uri-route"
test_uri="/test/regex/*"

echo -e "${YELLOW}Creating test route with regex_uri...${NC}"

# Create a test route with regex_uri
route_config='{
    "id": "'"$test_route_id"'",
    "uri": "'"$test_uri"'",
    "methods": ["GET"],
    "desc": "Test route for regex_uri",
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "httpbin.org:80": 1
        },
        "scheme": "http"
    },
    "plugins": {
        "proxy-rewrite": {
            "regex_uri": ["^/test/regex/(.*)", "/anything/$1"]
        }
    }
}'

echo "Route configuration:"
echo "$route_config" | python3 -m json.tool

echo
echo -e "${YELLOW}Sending to APISIX...${NC}"

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${test_route_id}" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d "${route_config}" 2>/dev/null)

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)
response_body=$(echo "$response" | grep -v "HTTP_CODE:")

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo -e "${GREEN}✅ Test route created successfully${NC}"
    
    echo
    echo -e "${YELLOW}Retrieving route to verify regex_uri...${NC}"
    
    # Get the route back to see what was actually stored
    retrieved_route=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes/${test_route_id}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)
    
    echo "Retrieved route configuration:"
    echo "$retrieved_route" | python3 -m json.tool | grep -A 10 "proxy-rewrite" || echo "proxy-rewrite not found"
    
    if echo "$retrieved_route" | grep -q "regex_uri"; then
        echo -e "${GREEN}✅ regex_uri is present in the route${NC}"
    else
        echo -e "${RED}❌ regex_uri is NOT present in the route${NC}"
        echo
        echo "This indicates APISIX might not support regex_uri in your version"
        echo "or there's an issue with the configuration format."
    fi
    
    # Clean up test route
    echo
    echo -e "${YELLOW}Cleaning up test route...${NC}"
    curl -s -X DELETE "${APISIX_ADMIN_URL}/apisix/admin/routes/${test_route_id}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" > /dev/null 2>&1
    echo -e "${GREEN}✅ Test route deleted${NC}"
else
    echo -e "${RED}❌ Failed to create test route${NC}"
    echo "HTTP Code: $http_code"
    echo "Response: $response_body"
fi

echo
echo -e "${BLUE}=== Alternative: Testing uri with direct rewrite ===${NC}"

# Try alternative configuration format
test_route_id2="test-uri-rewrite-route"

route_config2='{
    "id": "'"$test_route_id2"'",
    "uri": "'"$test_uri"'",
    "methods": ["GET"],
    "desc": "Test route for uri rewrite",
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "httpbin.org:80": 1
        },
        "scheme": "http"
    },
    "plugins": {
        "proxy-rewrite": {
            "uri": "/anything/test"
        }
    }
}'

echo "Alternative configuration (simple uri rewrite):"
echo "$route_config2" | python3 -m json.tool

response2=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${test_route_id2}" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
    -H "Content-Type: application/json" \
    -d "${route_config2}" 2>/dev/null)

http_code2=$(echo "$response2" | grep "HTTP_CODE:" | cut -d':' -f2)

if [ "$http_code2" = "200" ] || [ "$http_code2" = "201" ]; then
    echo -e "${GREEN}✅ Alternative route created successfully${NC}"
    
    # Clean up
    curl -s -X DELETE "${APISIX_ADMIN_URL}/apisix/admin/routes/${test_route_id2}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" > /dev/null 2>&1
else
    echo -e "${RED}❌ Alternative route also failed${NC}"
fi

echo
echo -e "${BLUE}=== Test Complete ===${NC}"
echo
echo "If regex_uri is not working, you may need to:"
echo "1. Check APISIX version supports regex_uri"
echo "2. Use alternative proxy-rewrite configurations"
echo "3. Consider using different plugins for path rewriting"