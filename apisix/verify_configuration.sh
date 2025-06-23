#!/bin/bash

# APISIX Configuration Verification Script
# This script verifies that APISIX and ViolentUTF API configurations are properly set up

set -e

APISIX_ADMIN_URL="http://localhost:9180"
# SECURITY: Load admin key from environment - NO hardcoded secrets
ADMIN_KEY="${APISIX_ADMIN_KEY:-}"
if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY environment variable not set"
    exit 1
fi
APISIX_GATEWAY_URL="http://localhost:9080"

echo "🔍 Verifying APISIX Configuration..."

# Check if APISIX is running
echo "📡 Checking APISIX Admin API..."
if curl -s -f -H "X-API-KEY: $ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes" > /dev/null; then
    echo "✅ APISIX Admin API is accessible"
else
    echo "❌ APISIX Admin API is not accessible"
    echo "   Please ensure APISIX is running with: cd apisix && docker compose up -d"
    exit 1
fi

# Check if upstream exists
echo "📡 Checking ViolentUTF API upstream..."
upstream_response=$(curl -s -H "X-API-KEY: $ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/upstreams/violentutf-api")
if echo "$upstream_response" | grep -q '"violentutf_api:8000"'; then
    echo "✅ ViolentUTF API upstream is configured"
else
    echo "❌ ViolentUTF API upstream is not configured"
    echo "   Please run: ./configure_routes.sh"
    exit 1
fi

# Check critical routes
echo "🛣️  Checking critical routes..."

# Define expected routes (using simple arrays for bash compatibility)
route_ids=("1001" "2001" "2008" "2009" "2010" "2011")
route_paths=("/health" "/api/v1/auth/*" "/api/v1/generators*" "/api/v1/datasets*" "/api/v1/converters*" "/api/v1/scorers*")

missing_routes=0
for i in "${!route_ids[@]}"; do
    route_id="${route_ids[$i]}"
    route_path="${route_paths[$i]}"
    route_response=$(curl -s -H "X-API-KEY: $ADMIN_KEY" "$APISIX_ADMIN_URL/apisix/admin/routes/$route_id")
    
    # Escape special characters in route_path for grep
    escaped_path=$(echo "$route_path" | sed 's/\*/\\*/g')
    if echo "$route_response" | grep -q "\"uri\":\"$escaped_path\""; then
        echo "✅ Route $route_id ($route_path) is configured"
    else
        echo "❌ Route $route_id ($route_path) is missing"
        missing_routes=$((missing_routes + 1))
    fi
done

if [ $missing_routes -gt 0 ]; then
    echo "❌ $missing_routes route(s) are missing. Please run: ./configure_routes.sh"
    exit 1
fi

# Test actual connectivity
echo "🧪 Testing API connectivity..."

# Test health endpoint
if curl -s -f "$APISIX_GATEWAY_URL/health" > /dev/null; then
    echo "✅ Health endpoint is accessible through APISIX"
else
    echo "❌ Health endpoint is not accessible through APISIX"
    echo "   Please ensure ViolentUTF API container is running"
    exit 1
fi

# Test documentation endpoint
if curl -s -f "$APISIX_GATEWAY_URL/docs" > /dev/null; then
    echo "✅ API documentation is accessible through APISIX"
else
    echo "❌ API documentation is not accessible through APISIX"
fi

echo
echo "🎯 Configuration Summary:"
echo "   - APISIX Admin URL: $APISIX_ADMIN_URL"
echo "   - APISIX Gateway URL: $APISIX_GATEWAY_URL"
echo "   - ViolentUTF API: http://violentutf_api:8000 (internal)"
echo "   - API Documentation: $APISIX_GATEWAY_URL/docs"
echo "   - API Health: $APISIX_GATEWAY_URL/health"
echo
echo "✅ All critical configurations are verified!"
echo
echo "📚 Available API Categories:"
echo "   - Authentication: $APISIX_GATEWAY_URL/api/v1/auth/*"
echo "   - Database: $APISIX_GATEWAY_URL/api/v1/database/*"
echo "   - Sessions: $APISIX_GATEWAY_URL/api/v1/sessions*"
echo "   - Configuration: $APISIX_GATEWAY_URL/api/v1/config/*"
echo "   - Files: $APISIX_GATEWAY_URL/api/v1/files*"
echo "   - Generators: $APISIX_GATEWAY_URL/api/v1/generators*"
echo "   - Datasets: $APISIX_GATEWAY_URL/api/v1/datasets*"
echo "   - Converters: $APISIX_GATEWAY_URL/api/v1/converters*"
echo "   - Scorers: $APISIX_GATEWAY_URL/api/v1/scorers*"
echo
echo "🔧 Troubleshooting:"
echo "   - If routes are missing: ./configure_routes.sh"
echo "   - If API is not responding: cd ../violentutf_api && docker compose up -d"
echo "   - If APISIX is not running: docker compose up -d"