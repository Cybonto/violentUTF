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
            
            # Parse the OpenAPI spec inline
            echo "🔧 Parsing OpenAPI spec..."
            endpoints_count=$(python3 -c "
import json
import sys

try:
    with open('$temp_spec', 'r') as f:
        spec = json.load(f)
    
    paths = spec.get('paths', {})
    endpoint_count = 0
    
    for path, path_item in paths.items():
        if isinstance(path_item, dict) and '\$ref' not in path_item:
            for method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                if method in path_item:
                    endpoint_count += 1
    
    print(endpoint_count)
except Exception as e:
    print(0)
" 2>/dev/null)
            
            if [ "$endpoints_count" -gt 0 ]; then
                echo "✅ Found $endpoints_count endpoints in spec"
                
                # Now try to create actual APISIX routes
                echo "🔧 Creating APISIX routes..."
                
                # Create routes using the actual setup script logic
                created_routes=$(python3 -c "
import json
import requests
import sys

try:
    # Load the spec
    with open('$temp_spec', 'r') as f:
        spec = json.load(f)
    
    paths = spec.get('paths', {})
    routes_created = 0
    
    for path, path_item in paths.items():
        if isinstance(path_item, dict) and '\$ref' not in path_item:
            for method in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                if method in path_item:
                    operation = path_item[method]
                    op_id = operation.get('operationId', f'{method}_{path.replace(\"/\", \"_\").replace(\"{\", \"\").replace(\"}\", \"\")}')
                    
                    # Create APISIX route
                    route_id = f'openapi-$id_val-{op_id.replace(\"_\", \"-\").lower()}'
                    
                    route_config = {
                        'uri': f'/ai/openapi/$id_val{path}',
                        'methods': [method.upper()],
                        'upstream': {
                            'type': 'roundrobin',
                            'nodes': {
                                '$base_url_val'.replace('https://', '').replace('http://', '') + ':443': 1
                            },
                            'scheme': 'https'
                        },
                        'plugins': {
                            'proxy-rewrite': {
                                'regex_uri': [f'^/ai/openapi/$id_val(.*)', '\$1']
                            }
                        }
                    }
                    
                    # Create the route
                    response = requests.put(
                        f'$APISIX_ADMIN_URL/apisix/admin/routes/{route_id}',
                        headers={'X-API-KEY': '$APISIX_ADMIN_KEY', 'Content-Type': 'application/json'},
                        json=route_config,
                        timeout=10
                    )
                    
                    if response.status_code in [200, 201]:
                        routes_created += 1
                        print(f'Created route: {route_id}', file=sys.stderr)
                    else:
                        print(f'Failed to create route {route_id}: {response.status_code}', file=sys.stderr)
    
    print(routes_created)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    print(0)
" 2>&1)
                
                if [ "$created_routes" -gt 0 ]; then
                    echo "✅ Successfully created $created_routes APISIX routes"
                    routes_created=$((routes_created + created_routes))
                else
                    echo "❌ Failed to create APISIX routes"
                fi
            else
                echo "❌ No endpoints found in spec"
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