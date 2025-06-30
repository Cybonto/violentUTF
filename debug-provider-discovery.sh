#!/usr/bin/env bash
# Debug script to test OpenAPI provider discovery

echo "🔍 Debugging OpenAPI Provider Discovery"
echo "======================================"

# Check FastAPI container environment
echo "1. Checking FastAPI container environment..."
echo "FastAPI .env file:"
echo "OPENAPI_ENABLED=$(grep OPENAPI_ENABLED violentutf_api/fastapi_app/.env)"
echo "APISIX_ADMIN_URL=$(grep APISIX_ADMIN_URL violentutf_api/fastapi_app/.env)"
echo "APISIX_ADMIN_KEY=$(grep APISIX_ADMIN_KEY violentutf_api/fastapi_app/.env)"

echo ""
echo "2. Testing APISIX connectivity from host..."
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
APISIX_ADMIN_KEY="${APISIX_ADMIN_KEY:-ens35VSOYXzPMHLUpUhwV6FcKZEyRxud}"

if curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes" >/dev/null 2>&1; then
    echo "✅ Host can reach APISIX admin API"
    
    # Check for OpenAPI routes
    openapi_routes=$(curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes" | grep -o '"uri":"/ai/openapi/[^"]*"' | wc -l)
    echo "📊 Found $openapi_routes OpenAPI routes in APISIX"
    
    if [ "$openapi_routes" -gt 0 ]; then
        echo "📋 OpenAPI routes:"
        curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes" | grep -o '"uri":"/ai/openapi/[^"]*"' | sed 's/"uri":"//;s/"//' | sed 's/^/  /'
    fi
else
    echo "❌ Host cannot reach APISIX admin API"
fi

echo ""
echo "3. Testing FastAPI container connectivity to APISIX..."
if docker ps --filter "name=violentutf_api" --format "{{.Names}}" | grep -q violentutf_api; then
    echo "✅ FastAPI container is running"
    
    # Test from inside the container
    echo "Testing APISIX connectivity from inside FastAPI container..."
    docker exec violentutf_api curl -s -m 5 http://apisix-apisix-1:9180/apisix/admin/routes \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✅ FastAPI container can reach APISIX"
        
        # Test the provider discovery endpoint directly
        echo ""
        echo "4. Testing provider discovery endpoint..."
        response=$(docker exec violentutf_api curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
            http://apisix-apisix-1:9180/apisix/admin/routes 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            openapi_count=$(echo "$response" | grep -o '"/ai/openapi/' | wc -l)
            echo "📊 FastAPI container sees $openapi_count OpenAPI routes"
            
            if [ "$openapi_count" -gt 0 ]; then
                echo "📋 Providers that should be discovered:"
                echo "$response" | grep -o '"/ai/openapi/[^/]*/' | sed 's|"/ai/openapi/||;s|/"|openapi-|' | sort -u | sed 's/^/  /'
            fi
        else
            echo "❌ FastAPI container API call failed"
        fi
    else
        echo "❌ FastAPI container cannot reach APISIX (network issue)"
    fi
else
    echo "❌ FastAPI container is not running"
fi

echo ""
echo "5. Testing ViolentUTF API endpoints..."
if curl -s -m 5 http://localhost:9080/api/v1/generators/types >/dev/null 2>&1; then
    echo "✅ ViolentUTF API is accessible"
    
    # Test the provider discovery endpoint
    echo "Testing OpenAPI provider discovery endpoint..."
    providers_response=$(curl -s http://localhost:9080/api/v1/generators/apisix/openapi-providers 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "📋 Provider discovery response:"
        echo "$providers_response" | jq . 2>/dev/null || echo "$providers_response"
    else
        echo "❌ Provider discovery endpoint failed"
    fi
else
    echo "❌ ViolentUTF API is not accessible"
fi

echo ""
echo "6. Checking Docker network connectivity..."
echo "Docker networks:"
docker network ls | grep vutf

echo ""
echo "Container network memberships:"
if docker ps --filter "name=violentutf_api" --format "{{.Names}}" | grep -q violentutf_api; then
    echo "FastAPI container networks:"
    docker inspect violentutf_api | jq '.[0].NetworkSettings.Networks | keys[]' 2>/dev/null || echo "  Could not inspect networks"
fi

if docker ps --filter "name=apisix" --format "{{.Names}}" | grep -q apisix; then
    echo "APISIX container networks:"
    docker inspect apisix-apisix-1 | jq '.[0].NetworkSettings.Networks | keys[]' 2>/dev/null || echo "  Could not inspect networks"
fi

echo ""
echo "🎯 Summary:"
echo "- Check if FastAPI container can reach APISIX"
echo "- Verify network connectivity between containers"
echo "- Test the /api/v1/generators/apisix/openapi-providers endpoint"
echo "- Check FastAPI logs: docker logs violentutf_api"