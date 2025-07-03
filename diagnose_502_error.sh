#!/bin/bash

echo "=== Diagnosing 502 Bad Gateway Error ==="
echo

# Check if services are running
echo "1. Checking service status..."
docker ps | grep -E "(violentutf_api|apisix)" | grep -v dashboard

echo
echo "2. Checking APISIX routes..."
curl -s -H "X-API-KEY: ${APISIX_ADMIN_KEY}" http://localhost:9180/apisix/admin/routes | jq '.list[] | select(.value.uri | contains("/api/")) | {id: .value.id, uri: .value.uri, upstream: .value.upstream}'

echo
echo "3. Testing direct access to FastAPI..."
docker exec violentutf_api curl -s http://localhost:8000/api/v1/generators/apisix/openapi-providers || echo "Failed to reach FastAPI internally"

echo
echo "4. Checking FastAPI health..."
curl -s http://localhost:9080/api/health || echo "Health check failed"

echo
echo "5. Recent FastAPI logs..."
docker logs violentutf_api --tail 30

echo
echo "6. APISIX error logs..."
docker logs apisix-apisix-1 --tail 20 2>&1 | grep -E "(error|ERROR|502)" || echo "No errors in APISIX logs"