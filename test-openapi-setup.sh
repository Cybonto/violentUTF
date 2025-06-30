#!/bin/bash
# Test script to check why setup_macos.sh doesn't create OpenAPI routes

echo "🔍 Testing OpenAPI setup within setup_macos.sh context"
echo "===================================================="

# Simulate the exact environment that setup_macos.sh creates
AI_TOKENS_FILE="ai-tokens.env"

# Create ai-tokens template (like setup_macos.sh does)
echo "📥 Loading AI tokens template..."
if [ -f "$AI_TOKENS_FILE" ]; then
    source "$AI_TOKENS_FILE"
    echo "✅ Loaded $AI_TOKENS_FILE"
else
    echo "❌ $AI_TOKENS_FILE not found"
    exit 1
fi

# Load APISIX config (like setup_macos.sh does)
if [ -f "apisix/.env" ]; then
    source apisix/.env
    echo "✅ Loaded apisix/.env"
else
    echo "❌ apisix/.env not found"
fi

echo ""
echo "🔧 Environment variables:"
echo "   OPENAPI_ENABLED: '$OPENAPI_ENABLED'"
echo "   OPENAPI_1_ENABLED: '$OPENAPI_1_ENABLED'"
echo "   OPENAPI_1_ID: '$OPENAPI_1_ID'"
echo "   APISIX_ADMIN_URL: '$APISIX_ADMIN_URL'"
echo "   APISIX_ADMIN_KEY: '${APISIX_ADMIN_KEY:0:8}...'"

echo ""
echo "🔧 Testing setup_openapi_routes() function conditions..."

# Test the main condition that could cause early exit
if [ "$OPENAPI_ENABLED" != "true" ]; then
    echo "❌ OPENAPI_ENABLED is not 'true' - this would cause setup_openapi_routes() to exit early"
    echo "   Current value: '$OPENAPI_ENABLED'"
    echo "   Expected: 'true'"
else
    echo "✅ OPENAPI_ENABLED check passed"
fi

# Test provider configuration
for i in {1..10}; do
    enabled_var="OPENAPI_${i}_ENABLED"
    enabled="${!enabled_var}"
    
    if [ "$enabled" = "true" ]; then
        echo "✅ Found enabled OpenAPI provider: OPENAPI_${i}_ENABLED"
        
        # Check required fields
        id_var="OPENAPI_${i}_ID"
        base_url_var="OPENAPI_${i}_BASE_URL"
        spec_path_var="OPENAPI_${i}_SPEC_PATH"
        
        provider_id="${!id_var}"
        base_url="${!base_url_var}"
        spec_path="${!spec_path_var}"
        
        if [ -z "$provider_id" ] || [ -z "$base_url" ] || [ -z "$spec_path" ]; then
            echo "❌ Provider $i missing required fields:"
            echo "   ID: '$provider_id'"
            echo "   BASE_URL: '$base_url'"
            echo "   SPEC_PATH: '$spec_path'"
        else
            echo "   ✅ Provider $i has all required fields"
        fi
    fi
done

echo ""
echo "🔧 Testing APISIX connectivity..."
if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo "❌ APISIX_ADMIN_KEY not set"
else
    # Test APISIX admin API
    if curl -s --connect-timeout 5 "${APISIX_ADMIN_URL:-http://localhost:9180}/apisix/admin/routes" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" > /dev/null 2>&1; then
        echo "✅ APISIX admin API accessible"
    else
        echo "❌ APISIX admin API not accessible"
    fi
fi

echo ""
echo "🔧 Testing hash function availability..."
if command -v shasum > /dev/null 2>&1; then
    test_hash=$(echo -n "test" | shasum -a 256 | cut -c1-8)
    echo "✅ shasum available, test hash: $test_hash"
elif command -v md5sum > /dev/null 2>&1; then
    test_hash=$(echo -n "test" | md5sum | cut -c1-8)
    echo "✅ md5sum available, test hash: $test_hash"
else
    test_hash=$(echo -n "test" | wc -c | xargs printf "%08x")
    echo "⚠️  Using fallback hash method, test hash: $test_hash"
fi

echo ""
echo "📋 Summary:"
echo "============"

if [ "$OPENAPI_ENABLED" = "true" ]; then
    echo "✅ OpenAPI is enabled"
    
    found_providers=0
    for i in {1..10}; do
        enabled_var="OPENAPI_${i}_ENABLED"
        if [ "${!enabled_var}" = "true" ]; then
            found_providers=$((found_providers + 1))
        fi
    done
    
    if [ $found_providers -gt 0 ]; then
        echo "✅ Found $found_providers enabled provider(s)"
        echo "✅ setup_openapi_routes() should create routes"
        echo ""
        echo "💡 If routes are still not created, the issue is likely in:"
        echo "   1. The fetch_openapi_spec function (SSL/auth issues)"
        echo "   2. The parse_openapi_endpoints function (Python script issues)"  
        echo "   3. The create_openapi_route function (APISIX API issues)"
        echo ""
        echo "   Run with verbose logging:"
        echo "   bash -x ./setup_macos.sh 2>&1 | grep -A 50 -B 5 'OpenAPI'"
    else
        echo "❌ No enabled providers found"
    fi
else
    echo "❌ OpenAPI is disabled - routes will not be created"
fi