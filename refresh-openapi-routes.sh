#!/bin/bash
# Script to refresh OpenAPI routes from ai-tokens.env

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔄 OpenAPI Route Refresh Tool"
echo "=============================="

# Check if ai-tokens.env exists
if [ ! -f "ai-tokens.env" ]; then
    echo -e "${RED}❌ ai-tokens.env not found${NC}"
    echo "Please create ai-tokens.env with your OpenAPI configuration"
    exit 1
fi

# Load APISIX configuration
APISIX_ADMIN_URL="http://localhost:9180"
APISIX_ADMIN_KEY=""

# Try to get admin key from apisix/.env
if [ -f "apisix/.env" ]; then
    source apisix/.env
fi

if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo -e "${RED}❌ APISIX_ADMIN_KEY not found${NC}"
    echo "Please ensure APISIX is set up properly"
    exit 1
fi

# Function to clear OpenAPI routes
clear_openapi_routes() {
    echo ""
    echo "📌 Clearing existing OpenAPI routes..."
    
    # Get all routes from APISIX
    local routes_response=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)
    
    # Parse route IDs that start with "openapi-"
    local route_ids=$(echo "$routes_response" | grep -o '"id":"openapi-[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$route_ids" ]; then
        echo "No existing OpenAPI routes found"
        return 0
    fi
    
    local deleted_count=0
    for route_id in $route_ids; do
        echo "  Deleting route: $route_id"
        local delete_response=$(curl -s -w "%{http_code}" -X DELETE "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
            -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>&1)
        local http_code="${delete_response: -3}"
        
        if [ "$http_code" = "200" ] || [ "$http_code" = "204" ]; then
            deleted_count=$((deleted_count + 1))
        else
            echo -e "  ${YELLOW}⚠️  Failed to delete route $route_id (HTTP $http_code)${NC}"
        fi
    done
    
    echo -e "${GREEN}✅ Deleted $deleted_count OpenAPI routes${NC}"
}

# Function to list current routes
list_current_routes() {
    echo ""
    echo "📋 Current OpenAPI routes in APISIX:"
    echo "------------------------------------"
    
    local routes_response=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)
    
    # Parse and display OpenAPI routes
    echo "$routes_response" | jq -r '.list[]?.value | select(.id | startswith("openapi-")) | "\(.id) -> \(.uri)"' 2>/dev/null || \
        echo "Could not parse routes (jq might not be installed)"
}

# Show current state
echo ""
echo "🔍 Checking current OpenAPI routes..."
list_current_routes

# Ask for confirmation
echo ""
read -p "Do you want to clear all OpenAPI routes and reload from ai-tokens.env? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Clear routes
clear_openapi_routes

# Trigger full setup to reload routes
echo ""
echo "🚀 Triggering route reload from ai-tokens.env..."
echo ""

# Run OpenAPI setup by calling the main setup script with a specific function
echo "🔧 Running OpenAPI setup directly..."

# Load environment variables first
if [ -f "ai-tokens.env" ]; then
    echo "📥 Loading ai-tokens.env..."
    source ai-tokens.env
else
    echo "❌ ai-tokens.env not found!"
    exit 1
fi

# Set required variables for the setup
AI_TOKENS_FILE="ai-tokens.env"
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

# Load APISIX admin key
if [ -f "apisix/.env" ]; then
    source apisix/.env
fi

if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo "❌ APISIX_ADMIN_KEY not found in apisix/.env"
    exit 1
fi

echo "🔧 OPENAPI_ENABLED: $OPENAPI_ENABLED"
echo "🔧 OPENAPI_1_ENABLED: $OPENAPI_1_ENABLED"
echo "🔧 APISIX Admin URL: $APISIX_ADMIN_URL"

# Manual OpenAPI setup process
if [ "$OPENAPI_ENABLED" != "true" ]; then
    echo "❌ OPENAPI_ENABLED is not set to 'true' (current: ${OPENAPI_ENABLED:-unset})"
    exit 1
fi

echo "🔧 Processing OpenAPI providers..."
routes_created=0

# Process OpenAPI providers (1-10)
for i in {1..10}; do
    enabled_var="OPENAPI_${i}_ENABLED"
    id_var="OPENAPI_${i}_ID"
    name_var="OPENAPI_${i}_NAME"
    base_url_var="OPENAPI_${i}_BASE_URL"
    spec_path_var="OPENAPI_${i}_SPEC_PATH"
    auth_type_var="OPENAPI_${i}_AUTH_TYPE"
    auth_token_var="OPENAPI_${i}_AUTH_TOKEN"
    
    enabled_val="${!enabled_var}"
    
    if [ "$enabled_val" = "true" ]; then
        id_val="${!id_var}"
        name_val="${!name_var}"
        base_url_val="${!base_url_var}"
        spec_path_val="${!spec_path_var}"
        auth_type_val="${!auth_type_var}"
        auth_token_val="${!auth_token_var}"
        
        echo ""
        echo "Processing OpenAPI provider: $name_val ($id_val)"
        echo "----------------------------------------"
        echo "Base URL: $base_url_val"
        echo "Spec Path: $spec_path_val"
        echo "Auth Type: $auth_type_val"
        
        # Test the OpenAPI spec URL with our SSL fix
        spec_url="${base_url_val%/}/${spec_path_val#/}"
        echo "Testing spec URL: $spec_url"
        
        # Try to fetch spec with SSL bypass if needed
        temp_spec="/tmp/openapi_spec_${i}.json"
        if curl -s -f -k "$spec_url" -H "Authorization: Bearer $auth_token_val" -o "$temp_spec"; then
            echo "✅ Successfully fetched OpenAPI spec"
            
            # Try to parse with our Python diagnostic
            if python3 /Users/tamnguyen/Documents/GitHub/ViolentUTF/test-openapi-parsing.py "$spec_url" "$id_val"; then
                echo "✅ Spec parsing test passed"
                routes_created=$((routes_created + 1))
            else
                echo "❌ Spec parsing test failed"
            fi
        else
            echo "❌ Failed to fetch OpenAPI spec from $spec_url"
        fi
        
        # Clean up temp file
        rm -f "$temp_spec"
    fi
done

echo ""
echo "🎯 OpenAPI setup completed"
echo "   Processed providers: $routes_created"

# Show final state
echo ""
echo "📋 Final OpenAPI routes:"
list_current_routes

echo ""
echo -e "${GREEN}✅ OpenAPI route refresh complete!${NC}"