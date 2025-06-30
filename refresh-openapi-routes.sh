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

# Extract and source the setup functions we need
echo "📥 Extracting setup functions..."

# Create temporary files for the functions
temp_setup_functions="/tmp/setup_functions_$$.sh"
temp_load_tokens="/tmp/load_tokens_$$.sh"

# Extract setup_openapi_routes function
echo "# Extracted setup_openapi_routes function" > "$temp_setup_functions"
grep -A 1000 "setup_openapi_routes()" setup_macos.sh | grep -B 1000 "^}" >> "$temp_setup_functions"

# Extract load_ai_tokens function  
echo "# Extracted load_ai_tokens function" > "$temp_load_tokens"
grep -A 1000 "load_ai_tokens()" setup_macos.sh | grep -B 1000 "^}" >> "$temp_load_tokens"

# Source the functions
source "$temp_load_tokens"
source "$temp_setup_functions"

# Load AI tokens
echo "🔧 Loading AI tokens..."
load_ai_tokens

# Run OpenAPI setup
echo "🔧 Running OpenAPI setup..."
setup_openapi_routes

# Cleanup temp files
rm -f "$temp_setup_functions" "$temp_load_tokens"

# Show final state
echo ""
echo "📋 Final OpenAPI routes:"
list_current_routes

echo ""
echo -e "${GREEN}✅ OpenAPI route refresh complete!${NC}"