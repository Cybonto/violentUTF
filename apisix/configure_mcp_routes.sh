#!/bin/bash
# Configure APISIX routes for MCP endpoints

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Load environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
fi

# Default values
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
APISIX_ADMIN_KEY="${APISIX_ADMIN_KEY:-your-admin-key}"
VIOLENTUTF_API_URL="${VIOLENTUTF_API_URL:-http://violentutf-api:8000}"
JWT_SECRET_KEY="${JWT_SECRET_KEY:-your-jwt-secret-key}"

echo "Configuring MCP routes in APISIX..."
echo "Admin URL: $APISIX_ADMIN_URL"

# Function to create a route
create_route() {
    local route_id=$1
    local uri=$2
    local plugins=$3
    
    echo "Creating route: $route_id"
    
    response=$(curl -s -w "\n%{http_code}" -X PUT \
        "$APISIX_ADMIN_URL/apisix/admin/routes/$route_id" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"uri\": \"$uri\",
            \"upstream\": {
                \"type\": \"roundrobin\",
                \"nodes\": {
                    \"$VIOLENTUTF_API_URL\": 1
                }
            },
            \"plugins\": $plugins
        }")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 201 ]; then
        echo "✓ Route $route_id created successfully"
    else
        echo "✗ Failed to create route $route_id (HTTP $http_code)"
        echo "Response: $body"
        return 1
    fi
}

# Main MCP route with authentication
create_route "mcp-main" "/mcp/*" '{
    "cors": {
        "allow_origins": "*",
        "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
        "allow_headers": "Authorization,Content-Type,X-API-Gateway"
    },
    "jwt-auth": {
        "key": "user-key",
        "secret": "'$JWT_SECRET_KEY'",
        "algorithm": "HS256"
    },
    "limit-req": {
        "rate": 100,
        "burst": 20,
        "key": "remote_addr"
    },
    "prometheus": {
        "prefer_name": true
    }
}'

# OAuth callback route (no JWT required)
create_route "mcp-oauth" "/mcp/oauth/*" '{
    "cors": {
        "allow_origins": "*",
        "allow_methods": "GET,POST",
        "allow_headers": "Content-Type"
    },
    "limit-req": {
        "rate": 10,
        "burst": 5,
        "key": "remote_addr"
    }
}'

echo ""
echo "MCP route configuration complete!"
echo ""
echo "Routes created:"
echo "  - /mcp/*       : Main MCP endpoint (JWT required)"
echo "  - /mcp/oauth/* : OAuth callback endpoint (public)"
echo ""
echo "Test with:"
echo "  curl -H 'Authorization: Bearer <token>' http://localhost:9080/mcp/sse"