#!/bin/bash

# Fix OpenAPI 404 Issue - Diagnostic and Fix Script
# This script diagnoses and fixes the 404 error when testing OpenAPI generators

set -e

echo "=== OpenAPI 404 Fix Script ==="
echo "This script will diagnose and fix the 404 error for OpenAPI generators"
echo

# Load environment variables
if [ -f ../ai-tokens.env ]; then
    source ../ai-tokens.env
fi

if [ -f .env ]; then
    source .env
fi

# Check if running from apisix directory
if [ ! -f "./configure_routes.sh" ]; then
    echo "❌ Error: Please run this script from the apisix directory"
    echo "   cd apisix && ./fix_openapi_404.sh"
    exit 1
fi

echo "Step 1: Checking APISIX Admin API access from different contexts"
echo "========================================================"

# Test from host (localhost)
echo "Testing from host (localhost:9180)..."
host_response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X GET "http://localhost:9180/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null || echo "FAILED")
host_http_code=$(echo "$host_response" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$host_http_code" = "200" ]; then
    echo "✅ Host access works (localhost:9180)"
    host_route_count=$(echo "$host_response" | grep -o '"id":"openapi-' | wc -l)
    echo "   Found $host_route_count OpenAPI routes from host"
else
    echo "❌ Host access failed (HTTP $host_http_code)"
fi

# Test from container network (apisix-apisix-1)
echo
echo "Testing from container network (apisix-apisix-1:9180)..."
container_response=$(docker exec violentutf_api-fastapi-1 curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X GET "http://apisix-apisix-1:9180/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null || echo "FAILED")
container_http_code=$(echo "$container_response" | grep "HTTP_CODE:" | cut -d: -f2)

if [ "$container_http_code" = "200" ]; then
    echo "✅ Container access works (apisix-apisix-1:9180)"
    container_route_count=$(echo "$container_response" | grep -o '"id":"openapi-' | wc -l)
    echo "   Found $container_route_count OpenAPI routes from container"
else
    echo "❌ Container access failed (HTTP $container_http_code)"
fi

echo
echo "Step 2: Analyzing the Issue"
echo "=========================="

if [ "$host_route_count" -gt 0 ] && [ "$container_route_count" = "0" ]; then
    echo "🔍 ISSUE IDENTIFIED: Routes exist on host but not visible from container"
    echo "   This is likely a network connectivity issue between containers"
elif [ "$host_route_count" = "0" ] && [ "$container_route_count" = "0" ]; then
    echo "🔍 ISSUE IDENTIFIED: No OpenAPI routes exist"
    echo "   Need to run setup to create routes"
else
    echo "🔍 Routes are accessible from both contexts"
fi

echo
echo "Step 3: Checking FastAPI Environment Configuration"
echo "=============================================="

# Check FastAPI .env file
fastapi_env="../violentutf_api/fastapi_app/.env"
if [ -f "$fastapi_env" ]; then
    admin_url=$(grep "APISIX_ADMIN_URL" "$fastapi_env" | cut -d= -f2)
    echo "FastAPI APISIX_ADMIN_URL: $admin_url"
    
    if [[ "$admin_url" == *"localhost"* ]]; then
        echo "❌ FastAPI is configured to use localhost - this won't work in Docker"
        needs_fix=true
    elif [[ "$admin_url" == *"apisix-apisix-1"* ]]; then
        echo "✅ FastAPI is correctly configured for Docker networking"
        needs_fix=false
    else
        echo "⚠️  Unexpected APISIX_ADMIN_URL value"
        needs_fix=true
    fi
else
    echo "❌ FastAPI .env file not found"
    needs_fix=true
fi

echo
echo "Step 4: Testing Route Lookup"
echo "=========================="

# Create a test Python script to verify route lookup
cat > /tmp/test_route_lookup.py << 'EOF'
import os
import sys
import requests

# Add the FastAPI app to path
sys.path.insert(0, '/Users/tamnguyen/Documents/GitHub/ViolentUTF/violentutf_api/fastapi_app')

# Set environment variables
os.environ['APISIX_ADMIN_URL'] = 'http://localhost:9180'
os.environ['APISIX_ADMIN_KEY'] = '2exEp0xPj8qlOBABX3tAQkVz6OANnVRB'

# Import the function
from app.api.endpoints.generators import get_apisix_endpoint_for_model

# Test the lookup
provider = "openapi-gsai-api-1"
model = "claude_3_5_sonnet"

print(f"Testing route lookup for provider={provider}, model={model}")
endpoint = get_apisix_endpoint_for_model(provider, model)

if endpoint:
    print(f"✅ Found endpoint: {endpoint}")
else:
    print(f"❌ No endpoint found")
    
    # Debug: show what routes exist
    try:
        response = requests.get(
            f"{os.environ['APISIX_ADMIN_URL']}/apisix/admin/routes",
            headers={"X-API-KEY": os.environ['APISIX_ADMIN_KEY']},
            timeout=5
        )
        if response.status_code == 200:
            routes = response.json().get('list', [])
            openapi_routes = [
                r['value'] for r in routes 
                if r['value']['id'].startswith('openapi-gsai')
            ]
            print(f"\nFound {len(openapi_routes)} gsai routes:")
            for route in openapi_routes:
                print(f"  ID: {route['id']}")
                print(f"  URI: {route['uri']}")
    except Exception as e:
        print(f"Error checking routes: {e}")
EOF

echo "Running Python route lookup test..."
python3 /tmp/test_route_lookup.py

echo
echo "Step 5: Applying Fixes"
echo "===================="

if [ "$needs_fix" = true ]; then
    echo "Fixing FastAPI environment configuration..."
    
    # Backup original file
    cp "$fastapi_env" "${fastapi_env}.backup"
    
    # Update APISIX_ADMIN_URL to use container name
    if grep -q "APISIX_ADMIN_URL=" "$fastapi_env"; then
        sed -i.tmp 's|APISIX_ADMIN_URL=.*|APISIX_ADMIN_URL=http://apisix-apisix-1:9180|' "$fastapi_env"
    else
        echo "APISIX_ADMIN_URL=http://apisix-apisix-1:9180" >> "$fastapi_env"
    fi
    
    echo "✅ Updated APISIX_ADMIN_URL in FastAPI .env"
    echo "   Old value: $admin_url"
    echo "   New value: http://apisix-apisix-1:9180"
    
    # Restart FastAPI container
    echo "Restarting FastAPI container..."
    docker compose -f ../violentutf_api/docker-compose.yml restart fastapi
    
    echo "✅ FastAPI container restarted"
else
    echo "No fixes needed - configuration is correct"
fi

echo
echo "Step 6: Verification"
echo "=================="

# Wait for services to be ready
sleep 5

# Test the generator through the API
echo "Testing generator through API..."
test_response=$(curl -s -X POST "http://localhost:9080/api/v1/generators/test" \
    -H "Authorization: Bearer ${JWT_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
        "generator_name": "Test1",
        "test_prompt": "Hello"
    }' 2>/dev/null || echo "FAILED")

if [[ "$test_response" == *"success"* ]]; then
    echo "✅ Generator test successful!"
else
    echo "❌ Generator test failed"
    echo "Response: $test_response"
fi

echo
echo "=== Summary ==="
echo "The 404 error occurs when FastAPI tries to look up APISIX routes but uses the wrong URL."
echo "FastAPI running in Docker must use 'apisix-apisix-1:9180' not 'localhost:9180'."
echo
echo "If the test still fails after this fix:"
echo "1. Check that OpenAPI routes exist: ./check_openapi_routes.sh"
echo "2. If no routes exist, run: cd .. && ./setup_macos.sh"
echo "3. Check APISIX logs: docker logs apisix-apisix-1 --tail 50"
echo "4. Check FastAPI logs: docker logs violentutf_api-fastapi-1 --tail 50"

# Cleanup
rm -f /tmp/test_route_lookup.py