#!/bin/bash

# Fix APISIX route for orchestrator executions endpoint
# This script adds a specific route for /api/v1/orchestrators/executions
# to prevent it from being caught by the wildcard route

set -e

# Check if running in container
if [ -f /.dockerenv ]; then
    echo "❌ ERROR: This script should not be run inside a Docker container!"
    echo "Please run this script from your host machine."
    exit 1
fi

# APISIX Admin URL
APISIX_ADMIN_URL="http://localhost:9180"

# Load admin key from .env file
if [ -f .env ]; then
    ADMIN_KEY=$(grep "APISIX_ADMIN_KEY=" .env | cut -d'=' -f2)
fi

if [ -z "$ADMIN_KEY" ]; then
    echo "❌ ERROR: APISIX_ADMIN_KEY not found in .env file"
    echo "Please ensure APISIX_ADMIN_KEY is set in apisix/.env"
    exit 1
fi

echo "🔧 Fixing orchestrator executions route in APISIX..."
echo "📊 This will add a specific route for /api/v1/orchestrators/executions"

# Create specific route for executions endpoint
# Using route ID 2012a to place it before the wildcard orchestrator route (2013)
echo "🛣️  Creating specific route for orchestrator executions..."
curl -H "X-API-KEY: $ADMIN_KEY" -X PUT -d '{
    "uri": "/api/v1/orchestrators/executions",
    "methods": ["GET"],
    "upstream_id": "violentutf-api",
    "priority": 100,
    "plugins": {
        "cors": {
            "allow_origins": "*",
            "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
            "allow_headers": "Content-Type,Authorization,X-Real-IP,X-Forwarded-For,X-Forwarded-Host,X-API-Gateway"
        },
        "proxy-rewrite": {
            "headers": {
                "X-Real-IP": "$remote_addr",
                "X-Forwarded-For": "$proxy_add_x_forwarded_for",
                "X-Forwarded-Host": "$host",
                "X-API-Gateway": "APISIX"
            }
        }
    },
    "desc": "List all orchestrator executions"
}' "$APISIX_ADMIN_URL/apisix/admin/routes/2012a"

echo ""
echo "✅ Route created successfully!"
echo ""
echo "🧪 Test the endpoint with:"
echo "curl -H 'Authorization: Bearer <token>' http://localhost:9080/api/v1/orchestrators/executions"
echo ""
echo "📝 Note: This route has ID 2012a, which comes before the wildcard route 2013,"
echo "   ensuring it takes precedence over the pattern match."