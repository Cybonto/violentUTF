#!/usr/bin/env bash
# Script to refresh FastAPI container to pick up new OpenAPI providers

echo "🔄 Refreshing FastAPI Container for OpenAPI Providers"
echo "====================================================="

echo "1. Checking current FastAPI container status..."
if docker ps --filter "name=violentutf_api" --format "{{.Names}}" | grep -q violentutf_api; then
    echo "✅ FastAPI container is running"
    
    echo ""
    echo "2. Restarting FastAPI container to refresh environment..."
    docker restart violentutf_api
    
    echo ""
    echo "3. Waiting for container to be ready..."
    sleep 5
    
    # Wait for the container to be healthy
    max_attempts=12
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -s -m 3 http://localhost:9080/health >/dev/null 2>&1; then
            echo "✅ FastAPI container is ready"
            break
        else
            echo "  Waiting... (attempt $attempt/$max_attempts)"
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo "⚠️  FastAPI container may not be fully ready yet"
    fi
    
    echo ""
    echo "4. Testing OpenAPI provider discovery..."
    
    # Test the discovery endpoint
    echo "Testing /api/v1/generators/apisix/openapi-providers..."
    response=$(curl -s http://localhost:9080/api/v1/generators/apisix/openapi-providers 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        echo "✅ Provider discovery endpoint is working"
        echo "📋 Discovered providers:"
        echo "$response" | jq . 2>/dev/null || echo "$response"
        
        # Count providers
        provider_count=$(echo "$response" | jq '. | length' 2>/dev/null || echo "unknown")
        echo "📊 Total providers found: $provider_count"
        
        if [ "$provider_count" -gt 0 ] || echo "$response" | grep -q "openapi-gsai-api-1"; then
            echo "🎉 SUCCESS: OpenAPI providers are now discoverable!"
        else
            echo "⚠️  No OpenAPI providers found yet"
        fi
    else
        echo "❌ Provider discovery endpoint failed"
        echo "Response: $response"
    fi
    
    echo ""
    echo "5. Testing generator type parameters..."
    
    # Test the generator types endpoint
    echo "Testing /api/v1/generators/types/AI Gateway/params..."
    params_response=$(curl -s "http://localhost:9080/api/v1/generators/types/AI%20Gateway/params" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$params_response" ]; then
        echo "✅ Generator parameters endpoint is working"
        
        # Check if OpenAPI providers are in the options
        if echo "$params_response" | grep -q "openapi-gsai-api-1"; then
            echo "🎉 SUCCESS: GSAi API provider is available in generator configuration!"
        else
            echo "⚠️  GSAi API provider not found in generator options"
            echo "Available providers:"
            echo "$params_response" | jq '.parameters[] | select(.name=="provider") | .options' 2>/dev/null || echo "Could not parse providers"
        fi
    else
        echo "❌ Generator parameters endpoint failed"
    fi
    
    echo ""
    echo "6. Final status check..."
    echo "FastAPI container logs (last 10 lines):"
    docker logs violentutf_api --tail 10
    
else
    echo "❌ FastAPI container is not running"
    echo "Try starting it with: docker-compose up -d"
fi

echo ""
echo "🎯 Next steps:"
echo "1. Open the ViolentUTF Streamlit interface"
echo "2. Go to Configure Generators page" 
echo "3. Select 'AI Gateway' as generator type"
echo "4. Check if 'openapi-gsai-api-1' appears in the provider dropdown"
echo "5. If not, check the container logs: docker logs violentutf_api"