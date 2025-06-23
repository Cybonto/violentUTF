#!/bin/bash

# APISIX Route Verification Script
# This script verifies that ViolentUTF API routes are properly configured

set -e

# SECURITY: Load environment variables from .env file
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    set -a  # Automatically export all variables
    source .env
    set +a  # Stop auto-exporting
else
    echo "Warning: .env file not found, using system environment variables"
fi

APISIX_ADMIN_URL="http://localhost:9180"
# SECURITY: Load admin key from environment - NO hardcoded secrets
ADMIN_KEY="${APISIX_ADMIN_KEY:-}"
if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY environment variable not set"
    echo "Please ensure APISIX_ADMIN_KEY is set in .env file or environment"
    exit 1
fi
GATEWAY_URL="http://localhost:9080"

echo "🔍 Verifying APISIX routes for ViolentUTF API..."
echo

# Function to check if APISIX is running
check_apisix() {
    echo "🔧 Checking APISIX status..."
    if curl -s "$GATEWAY_URL/health" > /dev/null 2>&1; then
        echo "✅ APISIX Gateway is running on port 9080"
    else
        echo "❌ APISIX Gateway is not accessible on port 9080"
        return 1
    fi
    echo
}

# Function to list all routes
list_routes() {
    echo "📋 Listing configured routes..."
    curl -s -H "X-API-KEY: $ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes" | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'list' in data:
    for route in data['list']:
        route_id = route.get('key', 'Unknown').split('/')[-1]
        value = route.get('value', {})
        uri = value.get('uri', 'N/A')
        methods = value.get('methods', [])
        desc = value.get('desc', 'No description')
        print(f'  Route {route_id}: {uri} [{\", \".join(methods)}] - {desc}')
else:
    print('  No routes found or error in response')
"
    echo
}

# Function to test health endpoint
test_health() {
    echo "🏥 Testing health endpoint..."
    if response=$(curl -s "$GATEWAY_URL/health" 2>/dev/null); then
        echo "✅ Health endpoint accessible: $response"
    else
        echo "❌ Health endpoint not accessible"
    fi
    echo
}

# Function to test API docs endpoint
test_docs() {
    echo "📚 Testing API documentation endpoint..."
    if curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/docs" | grep -q "200"; then
        echo "✅ API docs accessible at: $GATEWAY_URL/docs"
    else
        echo "❌ API docs not accessible"
    fi
    echo
}

# Function to check upstream status
check_upstream() {
    echo "📡 Checking upstream configuration..."
    curl -s -H "X-API-KEY: $ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/upstreams/violentutf-api" | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'value' in data:
    upstream = data['value']
    nodes = upstream.get('nodes', {})
    scheme = upstream.get('scheme', 'unknown')
    print(f'  ✅ Upstream configured: {scheme}://{list(nodes.keys())[0] if nodes else \"none\"}')
else:
    print('  ❌ Upstream not found')
"
    echo
}

# Function to test API endpoint (requires token)
test_api_endpoint() {
    echo "🔐 Testing protected API endpoint..."
    echo "   (This will fail without valid JWT token - expected behavior)"
    
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/auth/token/info" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "✅ Protected endpoint working (returns $response_code as expected without token)"
            ;;
        "404")
            echo "❌ Endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "❌ Gateway error - FastAPI service may not be running"
            ;;
        "000")
            echo "❌ Connection failed - APISIX may not be running"
            ;;
        *)
            echo "⚠️  Unexpected response code: $response_code"
            ;;
    esac
    echo
}

# Function to test generator endpoints specifically
test_generator_endpoints() {
    echo "⚙️ Testing generator endpoints..."
    echo "   (These will fail without valid JWT token - expected behavior)"
    
    # Test generator types endpoint
    echo "   Testing /api/v1/generators/types..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/generators/types" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Generator types endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Generator types endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Generator types endpoint response: $response_code"
            ;;
    esac
    
    # Test generators list endpoint
    echo "   Testing /api/v1/generators..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/generators" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Generators list endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Generators list endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Generators list endpoint response: $response_code"
            ;;
    esac
    echo
}

# Function to test dataset endpoints specifically
test_dataset_endpoints() {
    echo "📊 Testing dataset endpoints..."
    echo "   (These will fail without valid JWT token - expected behavior)"
    
    # Test dataset types endpoint
    echo "   Testing /api/v1/datasets/types..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/datasets/types" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Dataset types endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Dataset types endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Dataset types endpoint response: $response_code"
            ;;
    esac
    
    # Test datasets list endpoint
    echo "   Testing /api/v1/datasets..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/datasets" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Datasets list endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Datasets list endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Datasets list endpoint response: $response_code"
            ;;
    esac
    
    # Test memory datasets endpoint
    echo "   Testing /api/v1/datasets/memory..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/datasets/memory" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Memory datasets endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Memory datasets endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Memory datasets endpoint response: $response_code"
            ;;
    esac
    echo
}

# Function to test converter endpoints specifically
test_converter_endpoints() {
    echo "🔄 Testing converter endpoints..."
    echo "   (These will fail without valid JWT token - expected behavior)"
    
    # Test converter types endpoint
    echo "   Testing /api/v1/converters/types..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/converters/types" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Converter types endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Converter types endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Converter types endpoint response: $response_code"
            ;;
    esac
    
    # Test converters list endpoint
    echo "   Testing /api/v1/converters..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/converters" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Converters list endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Converters list endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Converters list endpoint response: $response_code"
            ;;
    esac
    
    # Test converter parameters endpoint
    echo "   Testing /api/v1/converters/params/ROT13Converter..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/converters/params/ROT13Converter" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Converter params endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Converter params endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Converter params endpoint response: $response_code"
            ;;
    esac
    echo
}

# Function to test scorer endpoints specifically
test_scorer_endpoints() {
    echo "🎯 Testing scorer endpoints..."
    echo "   (These will fail without valid JWT token - expected behavior)"
    
    # Test scorer types endpoint
    echo "   Testing /api/v1/scorers/types..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/scorers/types" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Scorer types endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Scorer types endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Scorer types endpoint response: $response_code"
            ;;
    esac
    
    # Test scorers list endpoint
    echo "   Testing /api/v1/scorers..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/scorers" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Scorers list endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Scorers list endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Scorers list endpoint response: $response_code"
            ;;
    esac
    
    # Test scorer parameters endpoint
    echo "   Testing /api/v1/scorers/params/SubStringScorer..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/scorers/params/SubStringScorer" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Scorer params endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Scorer params endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Scorer params endpoint response: $response_code"
            ;;
    esac
    
    # Test scorer health endpoint
    echo "   Testing /api/v1/scorers/health..."
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$GATEWAY_URL/api/v1/scorers/health" 2>/dev/null || echo "000")
    
    case $response_code in
        "401"|"403")
            echo "   ✅ Scorer health endpoint routed (returns $response_code as expected)"
            ;;
        "404")
            echo "   ❌ Scorer health endpoint not found - check route configuration"
            ;;
        "502"|"503")
            echo "   ❌ Gateway error - FastAPI service may not be running"
            ;;
        *)
            echo "   ⚠️  Scorer health endpoint response: $response_code"
            ;;
    esac
    echo
}

# Main verification flow
echo "Starting APISIX route verification..."
echo "=================================="
echo

check_apisix || exit 1
check_upstream
list_routes
test_health
test_docs
test_api_endpoint
test_generator_endpoints
test_dataset_endpoints
test_converter_endpoints
test_scorer_endpoints

echo "✅ Route verification completed!"
echo
echo "🛠️  Next steps:"
echo "   1. Ensure FastAPI service is running: cd ../violentutf_api && docker compose up -d"
echo "   2. Test with valid JWT token from ViolentUTF Streamlit app"
echo "   3. Check APISIX Dashboard: http://localhost:9001"
echo "   4. View logs: docker compose logs apisix"