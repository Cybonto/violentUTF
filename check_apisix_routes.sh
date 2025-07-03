#!/usr/bin/env bash
# Diagnostic script to check APISIX routes for GSAi

echo "🔍 Checking APISIX routes for AI endpoints..."

# Load APISIX admin key
if [ -f "apisix/.env" ]; then
    source "apisix/.env"
fi

if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY not set"
    exit 1
fi

admin_key="$APISIX_ADMIN_KEY"
apisix_admin_url="http://localhost:9180"

echo "Using admin key: ${admin_key:0:8}...${admin_key: -4}"

# Get all routes
echo ""
echo "📊 Getting all APISIX routes..."
routes_response=$(curl -s -H "X-API-KEY: $admin_key" "$apisix_admin_url/apisix/admin/routes")

if [ $? -ne 0 ]; then
    echo "❌ Failed to connect to APISIX admin API"
    exit 1
fi

# Count total routes
total_routes=$(echo "$routes_response" | jq '.list | length' 2>/dev/null || echo "0")
echo "Total routes found: $total_routes"

# Look for AI routes
echo ""
echo "🤖 Looking for AI routes (containing 'ai-proxy' plugin)..."
ai_routes=$(echo "$routes_response" | jq -r '.list[] | select(.value.plugins["ai-proxy"]) | .value | "ID: " + .id + ", URI: " + .uri + ", Name: " + (.name // "unnamed")' 2>/dev/null)

if [ -n "$ai_routes" ]; then
    echo "✅ Found AI routes:"
    echo "$ai_routes"
else
    echo "❌ No AI routes found with ai-proxy plugin"
fi

# Look for GSAi routes specifically
echo ""
echo "🏛️  Looking for GSAi routes..."
gsai_routes=$(echo "$routes_response" | jq -r '.list[] | select(.value.uri | contains("gsai")) | .value | "ID: " + .id + ", URI: " + .uri + ", Name: " + (.name // "unnamed")' 2>/dev/null)

if [ -n "$gsai_routes" ]; then
    echo "✅ Found GSAi routes:"
    echo "$gsai_routes"
    
    # Check if GSAi routes have ai-proxy plugin
    echo ""
    echo "🔍 Checking GSAi route plugins..."
    gsai_with_plugins=$(echo "$routes_response" | jq -r '.list[] | select(.value.uri | contains("gsai")) | .value | "ID: " + .id + ", Plugins: " + (.plugins | keys | join(", "))' 2>/dev/null)
    echo "$gsai_with_plugins"
else
    echo "❌ No GSAi routes found"
fi

# Look for routes with ID 9001 or 9002 (our GSAi routes)
echo ""
echo "🎯 Looking for routes with ID 9001/9002..."
numbered_routes=$(echo "$routes_response" | jq -r '.list[] | select(.value.id == "9001" or .value.id == "9002") | .value | "ID: " + .id + ", URI: " + .uri + ", Plugins: " + (.plugins | keys | join(", "))' 2>/dev/null)

if [ -n "$numbered_routes" ]; then
    echo "✅ Found numbered routes:"
    echo "$numbered_routes"
else
    echo "❌ No routes with ID 9001/9002 found"
fi

echo ""
echo "🔧 Diagnosis complete. If no AI routes are found, you need to run the setup scripts."