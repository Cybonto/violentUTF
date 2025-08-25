#!/bin/bash

# Diagnostic script for OpenAPI 404 issue
# This script checks the actual problem without trying to fix anything

set -e

echo "=== OpenAPI 404 Diagnostic Script ==="
echo "This script will help diagnose why OpenAPI generators return 404"
echo

# Load environment variables
if [ -f ../ai-tokens.env ]; then
    source ../ai-tokens.env
fi

if [ -f .env ]; then
    source .env
fi

echo "Step 1: Verify OpenAPI Routes Exist"
echo "==================================="

# Check routes from host
echo "Checking routes via localhost..."
routes_response=$(curl -s -X GET "http://localhost:9180/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

if [ $? -eq 0 ]; then
    gsai_routes=$(echo "$routes_response" | jq -r '.list[]?.value | select(.id | startswith("openapi-gsai")) | {id: .id, uri: .uri}' 2>/dev/null)
    if [ -n "$gsai_routes" ]; then
        echo "✅ Found GSAI routes:"
        echo "$gsai_routes" | jq .
    else
        echo "❌ No GSAI routes found"
    fi
else
    echo "❌ Failed to query routes"
fi

echo
echo "Step 2: Test Network Connectivity from FastAPI Container"
echo "======================================================"

# Test if FastAPI container can reach APISIX admin
echo "Testing connectivity from FastAPI container..."
container_test=$(docker exec violentutf_api sh -c 'curl -s -w "HTTP_CODE:%{http_code}" http://apisix-apisix-1:9180/apisix/admin/health' 2>/dev/null || echo "FAILED")

if [[ "$container_test" == *"HTTP_CODE:200"* ]]; then
    echo "✅ FastAPI container can reach APISIX admin API"
else
    echo "❌ FastAPI container cannot reach APISIX admin API"
    echo "   This is the root cause of the 404 error"
fi

echo
echo "Step 3: Check FastAPI Environment Variables"
echo "========================================"

# Check if FastAPI has the right environment variables
echo "Checking FastAPI environment..."
fastapi_env=$(docker exec violentutf_api sh -c 'echo "APISIX_ADMIN_URL=$APISIX_ADMIN_URL"' 2>/dev/null || echo "FAILED")
echo "FastAPI env: $fastapi_env"

if [[ "$fastapi_env" == *"apisix-apisix-1"* ]]; then
    echo "✅ FastAPI has correct APISIX_ADMIN_URL"
elif [[ "$fastapi_env" == *"APISIX_ADMIN_URL="* ]]; then
    echo "❌ APISIX_ADMIN_URL is not set in FastAPI container"
    echo "   The code will use the default value"
else
    echo "❌ Could not check FastAPI environment"
fi

echo
echo "Step 4: Test Route Query from Inside FastAPI Container"
echo "=================================================="

# Create a test script that runs inside the container
cat > /tmp/test_route_query.sh << 'EOF'
#!/bin/sh
# Test querying APISIX routes from inside FastAPI container

APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://apisix-apisix-1:9180}"
APISIX_ADMIN_KEY="${APISIX_ADMIN_KEY:-2exEp0xPj8qlOBABX3tAQkVz6OANnVRB}"

echo "Using APISIX_ADMIN_URL: $APISIX_ADMIN_URL"
echo "Testing route query..."

response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$APISIX_ADMIN_URL/apisix/admin/routes" \
    -H "X-API-KEY: $APISIX_ADMIN_KEY" 2>&1)

http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
body=$(echo "$response" | grep -v "HTTP_CODE:")

if [ "$http_code" = "200" ]; then
    echo "✅ Successfully queried routes (HTTP 200)"
    # Count OpenAPI routes
    openapi_count=$(echo "$body" | grep -o '"id":"openapi-' | wc -l)
    echo "   Found $openapi_count OpenAPI routes"
    
    # Look for GSAI routes specifically
    gsai_count=$(echo "$body" | grep -o '"id":"openapi-gsai-api-1-' | wc -l)
    echo "   Found $gsai_count GSAI routes"
    
    if [ "$gsai_count" -gt 0 ]; then
        echo "   GSAI route IDs:"
        echo "$body" | grep -o '"id":"openapi-gsai-api-1-[^"]*"' | cut -d'"' -f4
    fi
else
    echo "❌ Failed to query routes (HTTP $http_code)"
    echo "   Error: $body"
fi
EOF

# Copy and run the test script in the container
docker cp /tmp/test_route_query.sh violentutf_api:/tmp/
docker exec violentutf_api sh /tmp/test_route_query.sh

echo
echo "Step 5: Check Docker Network Configuration"
echo "========================================"

# Check if containers are on the same network
echo "Checking Docker networks..."
apisix_networks=$(docker inspect apisix-apisix-1 -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || echo "FAILED")
fastapi_networks=$(docker inspect violentutf_api -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || echo "FAILED")

echo "APISIX networks: $apisix_networks"
echo "FastAPI networks: $fastapi_networks"

# Check if they share a network
if [ "$apisix_networks" != "FAILED" ] && [ "$fastapi_networks" != "FAILED" ]; then
    shared_network=""
    for net in $apisix_networks; do
        if [[ " $fastapi_networks " =~ " $net " ]]; then
            shared_network=$net
            break
        fi
    done
    
    if [ -n "$shared_network" ]; then
        echo "✅ Containers share network: $shared_network"
    else
        echo "❌ Containers are not on the same network!"
        echo "   This would cause connection failures"
    fi
fi

echo
echo "Step 6: Test API Gateway Request"
echo "=============================="

# Test making a request through the API gateway
echo "Testing generator endpoint through API..."
test_url="http://localhost:9080/api/v1/generators/apisix/openapi-providers"

if [ -n "$VIOLENTUTF_API_KEY" ]; then
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "$test_url" \
        -H "apikey: $VIOLENTUTF_API_KEY" 2>&1)
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    
    if [ "$http_code" = "200" ]; then
        echo "✅ API gateway is working"
    else
        echo "❌ API gateway returned HTTP $http_code"
    fi
else
    echo "⚠️  No VIOLENTUTF_API_KEY found - skipping API test"
fi

echo
echo "=== Diagnostic Summary ==="
echo
echo "Based on the tests above:"
echo "1. Check if GSAI routes exist (Step 1)"
echo "2. Check if FastAPI can reach APISIX admin (Step 2)"
echo "3. Check if environment variables are set (Step 3)"
echo "4. Check if route queries work from inside container (Step 4)"
echo "5. Check if containers are on the same network (Step 5)"
echo
echo "The most common causes of 404 errors are:"
echo "- FastAPI container cannot reach APISIX admin API"
echo "- Environment variables not set in FastAPI container"
echo "- Containers not on the same Docker network"
echo "- Routes don't exist (need to run setup)"

# Cleanup
rm -f /tmp/test_route_query.sh