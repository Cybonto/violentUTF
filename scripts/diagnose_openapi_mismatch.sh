#!/bin/bash
# Diagnose and fix OpenAPI provider ID mismatch issue

echo "========================================="
echo "OpenAPI Provider ID Mismatch Diagnostic"
echo "========================================="
echo ""

# Check ai-tokens.env
echo "1. Checking ai-tokens.env configuration:"
echo "-----------------------------------------"
if [ -f "ai-tokens.env" ]; then
    echo "✅ ai-tokens.env found"

    # Extract OpenAPI configuration
    OPENAPI_1_ID=$(grep "^OPENAPI_1_ID=" ai-tokens.env | cut -d'=' -f2)
    OPENAPI_1_ENABLED=$(grep "^OPENAPI_1_ENABLED=" ai-tokens.env | cut -d'=' -f2)
    OPENAPI_1_BASE_URL=$(grep "^OPENAPI_1_BASE_URL=" ai-tokens.env | cut -d'=' -f2)

    echo "  OPENAPI_1_ENABLED: $OPENAPI_1_ENABLED"
    echo "  OPENAPI_1_ID: $OPENAPI_1_ID"
    echo "  OPENAPI_1_BASE_URL: $OPENAPI_1_BASE_URL"

    if [ "$OPENAPI_1_ID" = "custom-api-1" ]; then
        echo ""
        echo "⚠️  WARNING: OPENAPI_1_ID is set to 'custom-api-1' (default from sample)"
        echo "   This may cause routing issues if APISIX routes expect 'gsai-api-1'"
    fi
else
    echo "❌ ai-tokens.env not found"
fi

echo ""
echo "2. Checking APISIX routes:"
echo "---------------------------"
# Check if running in Docker or locally
if docker ps &>/dev/null && docker ps | grep -q apisix; then
    echo "Using Docker environment..."
    APISIX_ADMIN_URL="http://localhost:9180"
else
    echo "Using local environment..."
    APISIX_ADMIN_URL="http://localhost:9180"
fi

# Ask for APISIX admin key if not provided
if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo -n "Enter APISIX admin key (or press Enter for default): "
    read -r input_key
    if [ -z "$input_key" ]; then
        APISIX_ADMIN_KEY="Ds1fynPj1Zqv9hrucePsCZ35wEF4Its4"
        echo "Using default admin key"
    else
        APISIX_ADMIN_KEY="$input_key"
        echo "Using provided admin key"
    fi
else
    echo "Using admin key from environment variable"
fi

# Query APISIX routes
echo "Querying APISIX routes..."
ROUTES=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

if [ $? -eq 0 ]; then
    # Parse JSON properly to find OpenAPI routes
    # Using python for reliable JSON parsing
    OPENAPI_ROUTES=$(echo "$ROUTES" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    routes = []
    for item in data.get('list', []):
        uri = item.get('value', {}).get('uri', '')
        if '/ai/openapi/' in uri:
            routes.append(uri)
    for route in sorted(set(routes)):
        print(route)
except:
    pass
" 2>/dev/null)

    if [ -n "$OPENAPI_ROUTES" ]; then
        echo "Found OpenAPI routes:"
        echo "$OPENAPI_ROUTES" | while read -r route; do
            # Extract provider ID from route
            provider_id=$(echo "$route" | sed 's|/ai/openapi/\([^/]*\)/.*|\1|')
            echo "  - Provider ID: $provider_id (Route: $route)"
        done
    else
        echo "❌ No OpenAPI routes found in APISIX"
    fi

    # Check for GSAi-specific routes
    GSAI_ROUTES=$(echo "$ROUTES" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for item in data.get('list', []):
        uri = item.get('value', {}).get('uri', '')
        if '/ai/gsai' in uri:
            print(uri)
except:
    pass
" 2>/dev/null | sort -u)

    if [ -n "$GSAI_ROUTES" ]; then
        echo ""
        echo "Found GSAi-specific routes:"
        echo "$GSAI_ROUTES"
    fi
else
    echo "❌ Failed to query APISIX routes (is APISIX running?)"
fi

echo ""
echo "3. Checking FastAPI environment:"
echo "---------------------------------"
if [ -f "violentutf_api/fastapi_app/.env" ]; then
    echo "✅ FastAPI .env found"

    # Check if OpenAPI config is present
    FASTAPI_OPENAPI=$(grep "^OPENAPI_1_ID=" violentutf_api/fastapi_app/.env)
    if [ -n "$FASTAPI_OPENAPI" ]; then
        echo "  FastAPI has OpenAPI configuration:"
        echo "  $FASTAPI_OPENAPI"
    else
        echo "⚠️  FastAPI .env missing OPENAPI_1_ID configuration"
    fi
else
    echo "❌ FastAPI .env not found"
fi

echo ""
echo "========================================="
echo "Diagnosis Summary:"
echo "========================================="

# Determine the issue
if [ "$OPENAPI_1_ID" = "custom-api-1" ]; then
    echo "❌ PROBLEM IDENTIFIED: ID Mismatch"
    echo ""
    echo "Your ai-tokens.env has OPENAPI_1_ID=custom-api-1"
    echo "This doesn't match the expected 'gsai-api-1' for GSAi integration."
    echo ""
    echo "SOLUTION:"
    echo "1. Edit ai-tokens.env and change:"
    echo "   OPENAPI_1_ID=custom-api-1"
    echo "   to:"
    echo "   OPENAPI_1_ID=gsai-api-1"
    echo ""
    echo "2. Re-run the setup script to recreate routes:"
    echo "   ./setup_macos.sh"
    echo ""
    echo "3. OR run this command to auto-fix (make backup first):"
    echo "   cp ai-tokens.env ai-tokens.env.backup"
    echo "   sed -i '' 's/OPENAPI_1_ID=custom-api-1/OPENAPI_1_ID=gsai-api-1/' ai-tokens.env"
elif [ -z "$OPENAPI_1_ID" ]; then
    echo "⚠️  No OPENAPI_1_ID found in ai-tokens.env"
    echo "Please configure your OpenAPI provider in ai-tokens.env"
else
    echo "✅ OPENAPI_1_ID is set to: $OPENAPI_1_ID"
    echo "If you're still having issues, ensure APISIX routes match this ID"
fi

echo ""
echo "========================================="
echo "Quick Fix Option:"
echo "========================================="
echo "Run this command to fix the ID mismatch:"
echo ""
echo "sed -i.backup 's/OPENAPI_1_ID=custom-api-1/OPENAPI_1_ID=gsai-api-1/' ai-tokens.env && ./setup_macos.sh"
echo ""
