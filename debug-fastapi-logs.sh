#!/usr/bin/env bash
# Debug FastAPI container and check logs for OpenAPI provider issues

echo "🔍 FastAPI Container Debug & Log Analysis"
echo "=========================================="

echo "1. Restarting FastAPI container to apply logging changes..."
docker restart violentutf_api

echo ""
echo "2. Waiting for container to be ready..."
sleep 5

# Check if container is running
if ! docker ps --filter "name=violentutf_api" --format "{{.Names}}" | grep -q violentutf_api; then
    echo "❌ FastAPI container is not running"
    exit 1
fi

echo "✅ FastAPI container is running"

echo ""
echo "3. Testing API endpoints to trigger logging..."

echo "Testing generator types endpoint..."
curl -s "http://localhost:9080/api/v1/generators/types" >/dev/null

echo "Testing AI Gateway parameters endpoint (this should trigger the OpenAPI discovery)..."
curl -s "http://localhost:9080/api/v1/generators/types/AI%20Gateway/params" >/dev/null

echo "Testing OpenAPI providers endpoint directly..."
curl -s "http://localhost:9080/api/v1/generators/apisix/openapi-providers" >/dev/null

echo ""
echo "4. Checking FastAPI container environment variables..."
echo "Environment variables in container:"
docker exec violentutf_api printenv | grep -E "OPENAPI|APISIX" | sort

echo ""
echo "5. Analyzing FastAPI logs for OpenAPI-related entries..."
echo "Recent logs (last 50 lines):"
echo "============================================"
docker logs violentutf_api --tail 50

echo ""
echo "============================================"
echo "6. Filtering for OpenAPI-specific log entries..."
echo "OpenAPI-related logs:"
docker logs violentutf_api 2>&1 | grep -i "openapi\|provider.*discover\|OPENAPI_ENABLED" | tail -20

echo ""
echo "7. Checking for errors in logs..."
echo "Error logs:"
docker logs violentutf_api 2>&1 | grep -i "error\|exception\|traceback" | tail -10

echo ""
echo "8. Testing the specific generator parameters endpoint with curl..."
echo "Direct curl test of AI Gateway parameters:"
response=$(curl -s "http://localhost:9080/api/v1/generators/types/AI%20Gateway/params")
echo "Response:"
echo "$response" | jq . 2>/dev/null || echo "$response"

echo ""
echo "9. Checking if provider options are populated..."
if echo "$response" | grep -q '"options"'; then
    echo "✅ Provider options found in response"
    provider_count=$(echo "$response" | jq '.parameters[] | select(.name=="provider") | .options | length' 2>/dev/null)
    echo "Provider count: $provider_count"
    
    if [ "$provider_count" -gt 0 ]; then
        echo "Provider options:"
        echo "$response" | jq '.parameters[] | select(.name=="provider") | .options' 2>/dev/null
    else
        echo "❌ Provider options array is empty"
    fi
else
    echo "❌ No provider options found in response"
fi

echo ""
echo "🎯 Summary:"
echo "- Check the environment variables to ensure OPENAPI_ENABLED=true"
echo "- Look for any errors in the logs"
echo "- Verify the OpenAPI discovery is being called and working"
echo "- Check if the provider options are being populated correctly"