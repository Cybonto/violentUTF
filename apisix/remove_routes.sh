#!/bin/bash

# APISIX Route Removal Script for ViolentUTF API
# This script removes all ViolentUTF API routes from APISIX

set -e

APISIX_ADMIN_URL="http://localhost:9180"
# SECURITY: Load admin key from environment - NO hardcoded secrets
ADMIN_KEY="${APISIX_ADMIN_KEY:-}"
if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY environment variable not set"
    exit 1
fi

echo "🗑️  Removing APISIX routes for ViolentUTF API..."

# Function to remove route
remove_route() {
    local route_id=$1
    local desc=$2

    echo "❌ Removing route $route_id: $desc"
    curl -s -H "X-API-KEY: $ADMIN_KEY" -X DELETE "$APISIX_ADMIN_URL/apisix/admin/routes/$route_id" || true
}

# Remove all ViolentUTF routes
remove_route "1001" "Health check endpoint"
remove_route "1002" "FastAPI documentation"
remove_route "1003" "OpenAPI schema"
remove_route "1004" "ReDoc documentation"
remove_route "2001" "Authentication endpoints"
remove_route "2002" "Database management endpoints"
remove_route "2003" "Session management endpoints"
remove_route "2004" "Configuration management endpoints"
remove_route "2005" "File management endpoints"
remove_route "2006" "JWT keys endpoints"
remove_route "2007" "Test endpoints"

echo
echo "🗑️  Removing upstream..."
curl -s -H "X-API-KEY: $ADMIN_KEY" -X DELETE "$APISIX_ADMIN_URL/apisix/admin/upstreams/violentutf-api" || true

echo
echo "✅ All ViolentUTF API routes and upstream removed!"
echo
echo "ℹ️  To reconfigure routes, run: ./configure_routes.sh"
