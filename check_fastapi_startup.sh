#!/bin/bash

echo "=== FastAPI Startup Diagnostic ==="
echo

# Check container status
echo "1. Container Status:"
docker ps -a | grep violentutf_api

echo
echo "2. Container Health Check:"
docker inspect violentutf_api --format='{{json .State}}' | jq .

echo
echo "3. Recent Container Logs:"
docker logs violentutf_api --tail 50 2>&1

echo
echo "4. Check if port 8000 is listening inside container:"
docker exec violentutf_api sh -c 'netstat -tlnp 2>/dev/null | grep 8000 || ss -tlnp | grep 8000 || echo "No netstat/ss available"'

echo
echo "5. Try to access FastAPI directly inside container:"
docker exec violentutf_api curl -v http://localhost:8000/health 2>&1 || echo "Curl failed"

echo
echo "6. Check running processes:"
docker exec violentutf_api ps aux | grep -E "(python|uvicorn)" || echo "No python/uvicorn processes found"

echo
echo "7. Environment variables related to OpenAPI:"
docker exec violentutf_api env | grep -E "(OPENAPI|APISIX_ADMIN)" | sort