#!/usr/bin/env bash
# Debug script for OpenAPI setup issues
# This script helps diagnose why OpenAPI routes aren't being created

echo "🔍 OpenAPI Setup Debug Script"
echo "============================="

# Check if ai-tokens.env exists and has OpenAPI configuration
echo "1. Checking ai-tokens.env file..."
if [ -f "ai-tokens.env" ]; then
    echo "✅ ai-tokens.env found"
    
    # Check OpenAPI settings
    echo "📋 OpenAPI Configuration:"
    grep "OPENAPI" ai-tokens.env || echo "❌ No OPENAPI variables found"
    
    # Load the variables to test
    set -a
    source ai-tokens.env
    set +a
    
    echo ""
    echo "📋 Loaded OpenAPI Variables:"
    echo "  OPENAPI_ENABLED: ${OPENAPI_ENABLED:-'(not set)'}"
    echo "  OPENAPI_1_ENABLED: ${OPENAPI_1_ENABLED:-'(not set)'}"
    echo "  OPENAPI_1_ID: ${OPENAPI_1_ID:-'(not set)'}"
    echo "  OPENAPI_1_NAME: ${OPENAPI_1_NAME:-'(not set)'}"
    echo "  OPENAPI_1_BASE_URL: ${OPENAPI_1_BASE_URL:-'(not set)'}"
    echo "  OPENAPI_1_SPEC_PATH: ${OPENAPI_1_SPEC_PATH:-'(not set)'}"
    echo "  OPENAPI_1_AUTH_TYPE: ${OPENAPI_1_AUTH_TYPE:-'(not set)'}"
    echo "  OPENAPI_1_AUTH_TOKEN: ${OPENAPI_1_AUTH_TOKEN:+***TOKEN_SET***}"
else
    echo "❌ ai-tokens.env not found"
    exit 1
fi

echo ""
echo "2. Testing OpenAPI spec accessibility..."
if [ -n "$OPENAPI_1_BASE_URL" ] && [ -n "$OPENAPI_1_SPEC_PATH" ]; then
    spec_url="${OPENAPI_1_BASE_URL}${OPENAPI_1_SPEC_PATH}"
    echo "  Testing: $spec_url"
    
    # Test basic connectivity
    if curl -s -I -m 10 "$spec_url" >/dev/null 2>&1; then
        echo "✅ Basic connectivity to spec URL successful"
        
        # Test with authentication if bearer token is set
        if [ "$OPENAPI_1_AUTH_TYPE" = "bearer" ] && [ -n "$OPENAPI_1_AUTH_TOKEN" ]; then
            echo "  Testing with bearer authentication..."
            response=$(curl -s -m 10 -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" "$spec_url")
            if echo "$response" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
                echo "✅ Authenticated spec fetch successful"
                
                # Count endpoints
                endpoint_count=$(echo "$response" | python3 -c "
import sys, json
try:
    spec = json.load(sys.stdin)
    paths = spec.get('paths', {})
    count = 0
    for path, path_item in paths.items():
        if isinstance(path_item, dict) and '\$ref' not in path_item:
            for method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                if method in path_item:
                    count += 1
    print(count)
except:
    print(0)
")
                echo "  📊 Found $endpoint_count endpoints in spec"
            else
                echo "❌ Authenticated spec fetch failed or returned invalid JSON"
            fi
        else
            echo "  ⚠️  No authentication configured, testing without auth"
        fi
    else
        echo "❌ Cannot reach spec URL: $spec_url"
    fi
else
    echo "❌ OpenAPI base URL or spec path not configured"
fi

echo ""
echo "3. Checking APISIX connectivity..."
# Set defaults if not set
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
APISIX_ADMIN_KEY="${APISIX_ADMIN_KEY:-ens35VSOYXzPMHLUpUhwV6FcKZEyRxud}"

echo "  Testing: $APISIX_ADMIN_URL"
if curl -s -m 5 -H "X-API-KEY: $APISIX_ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes" >/dev/null 2>&1; then
    echo "✅ APISIX admin API accessible"
    
    # Check existing OpenAPI routes
    existing_routes=$(curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes" | grep -o '"id":"openapi-[^"]*"' | wc -l)
    echo "  📊 Found $existing_routes existing OpenAPI routes"
    
    if [ "$existing_routes" -gt 0 ]; then
        echo "  📋 Existing OpenAPI routes:"
        curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes" | grep -o '"id":"openapi-[^"]*"' | cut -d'"' -f4 | sed 's/^/    /'
    fi
else
    echo "❌ Cannot reach APISIX admin API"
fi

echo ""
echo "4. Checking required functions in setup_macos.sh..."
required_functions=(
    "wait_for_apisix_admin_api"
    "validate_all_openapi_providers"
    "validate_openapi_provider"
    "fetch_openapi_spec"
    "validate_openapi_spec"
    "parse_openapi_endpoints"
    "create_openapi_route"
    "clear_openapi_routes"
    "rollback_provider_routes"
    "save_provider_state"
    "setup_openapi_routes"
    "load_ai_tokens"
)

missing_functions=()
for func in "${required_functions[@]}"; do
    if grep -q "^${func}()" setup_macos.sh; then
        echo "✅ $func"
    else
        echo "❌ $func (missing)"
        missing_functions+=("$func")
    fi
done

if [ ${#missing_functions[@]} -gt 0 ]; then
    echo ""
    echo "⚠️  Missing functions: ${missing_functions[*]}"
    echo "   This will cause OpenAPI setup to fail"
fi

echo ""
echo "5. Testing the test-openapi-parsing.py script..."
if [ -f "test-openapi-parsing.py" ] && [ -n "$OPENAPI_1_BASE_URL" ] && [ -n "$OPENAPI_1_SPEC_PATH" ]; then
    spec_url="${OPENAPI_1_BASE_URL}${OPENAPI_1_SPEC_PATH}"
    echo "  Running: python3 test-openapi-parsing.py '$spec_url' '${OPENAPI_1_ID}'"
    
    if python3 test-openapi-parsing.py "$spec_url" "${OPENAPI_1_ID}" 2>/dev/null; then
        echo "✅ OpenAPI parsing test successful"
    else
        echo "❌ OpenAPI parsing test failed"
        echo "  Detailed output:"
        python3 test-openapi-parsing.py "$spec_url" "${OPENAPI_1_ID}" 2>&1 | sed 's/^/    /'
    fi
else
    echo "❌ Cannot run parsing test (missing script or configuration)"
fi

echo ""
echo "6. Syntax check of setup_macos.sh..."
if bash -n setup_macos.sh 2>/dev/null; then
    echo "✅ setup_macos.sh syntax is valid"
else
    echo "❌ setup_macos.sh has syntax errors:"
    bash -n setup_macos.sh 2>&1 | sed 's/^/    /'
fi

echo ""
echo "🎯 Summary and Recommendations:"
echo "================================"

if [ "$OPENAPI_ENABLED" = "true" ] && [ "$OPENAPI_1_ENABLED" = "true" ]; then
    echo "✅ OpenAPI is properly enabled in configuration"
else
    echo "❌ OpenAPI is not enabled - check OPENAPI_ENABLED and OPENAPI_1_ENABLED"
fi

if [ -n "$OPENAPI_1_BASE_URL" ] && [ -n "$OPENAPI_1_SPEC_PATH" ]; then
    echo "✅ OpenAPI provider configuration looks complete"
else
    echo "❌ OpenAPI provider configuration is incomplete"
fi

echo ""
echo "To debug further:"
echo "1. Ensure APISIX and all services are running: ./check_services.sh"
echo "2. Try running just the OpenAPI setup manually:"
echo "   source ai-tokens.env && bash -c 'source setup_macos.sh; setup_openapi_routes'"
echo "3. Check APISIX logs: docker logs apisix-apisix-1"
echo "4. Check setup script logs during execution"

echo ""
echo "Debug script completed."