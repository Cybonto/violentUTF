#!/bin/bash

# Script to fix OpenAPI routes in staging with proper methods and route IDs
# Version 2: Ensures methods are included and route IDs have proper suffixes

# Exit on real errors, but handle grep failures properly
set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Fix for Staging OpenAPI Routes v2 ===${NC}"
echo -e "${YELLOW}This version ensures HTTP methods are properly configured${NC}"
echo

# Get APISIX admin key
if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo -n "Enter APISIX Admin Key: "
    read -s APISIX_ADMIN_KEY
    echo
fi

# Get GSAi API key
echo -n "Enter GSAi API Key (Bearer token for GSAi): "
read -s GSAI_API_KEY
echo

APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

echo -e "${YELLOW}Updating OpenAPI routes with methods and regex_uri...${NC}"
echo

# Clean up ALL old OpenAPI routes first
echo -e "${YELLOW}Cleaning up all existing OpenAPI routes...${NC}"
# Use grep || true because not finding routes is OK (they might not exist)
all_openapi_routes=$(curl -s "${APISIX_ADMIN_URL}/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | \
    { grep -o "\"key\":\"/apisix/routes/openapi-gsai-api-1[^\"]*\"" || true; } | \
    cut -d'"' -f4 | cut -d'/' -f4)

if [ -n "$all_openapi_routes" ]; then
    echo "Found existing routes to clean:"
    echo "$all_openapi_routes" | while read -r route_to_delete; do
        if [ -n "$route_to_delete" ]; then
            echo "  Deleting: $route_to_delete"
            curl -s -X DELETE "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_to_delete}" \
                -H "X-API-KEY: ${APISIX_ADMIN_KEY}" &>/dev/null || true
        fi
    done
    echo -e "${GREEN}Old routes cleaned up${NC}"
else
    echo "No existing routes found to clean"
fi
echo

# Generate a random suffix for route IDs (8 chars hex)
generate_suffix() {
    echo $(openssl rand -hex 4)
}

# Function to update a route with methods, regex_uri, and proper ID
update_route() {
    local route_base="$1"
    local uri="$2"
    local method="$3"
    local description="$4"

    # Generate route ID with suffix
    local suffix=$(generate_suffix)
    local route_id="${route_base}-${suffix}"

    echo -e "${BLUE}Updating: $description${NC}"
    echo "  Route ID: $route_id"
    echo "  URI: $uri"
    echo "  Method: $method"

    # Auto-detect the correct upstream configuration
    echo "  Detecting correct upstream configuration..."

    local api_port=""
    local api_host=""

    # First, check what ports the FastAPI container is actually listening on
    echo "    Checking FastAPI container ports..."

    # Get the actual listening port from the container
    if docker ps --format "{{.Names}}" | grep -q "violentutf_api"; then
        # Check what port uvicorn is actually listening on inside the container
        local listening_port=$(docker exec violentutf_api sh -c "netstat -tln 2>/dev/null | grep LISTEN | grep -E ':(8000|8081)' | head -1" 2>/dev/null | grep -o ':[0-9]\+' | grep -o '[0-9]\+' | head -1)

        if [ -z "$listening_port" ]; then
            # Try with ss if netstat not available
            listening_port=$(docker exec violentutf_api sh -c "ss -tln 2>/dev/null | grep LISTEN | grep -E ':(8000|8081)' | head -1" 2>/dev/null | grep -o ':[0-9]\+' | grep -o '[0-9]\+' | head -1)
        fi

        if [ -z "$listening_port" ]; then
            # Last resort - check logs
            listening_port=$(docker logs violentutf_api 2>&1 | grep "Uvicorn running" | tail -1 | grep -o ':[0-9]\+' | grep -o '[0-9]\+')
        fi

        if [ -n "$listening_port" ]; then
            api_port="$listening_port"
            api_host="violentutf_api"
            echo "    FastAPI is listening on port ${api_port}"

            # Test connectivity from APISIX container to FastAPI
            echo "    Testing connectivity from APISIX to ${api_host}:${api_port}..."
            local test_result=$(docker exec apisix-apisix sh -c "nc -zv ${api_host} ${api_port} 2>&1" 2>/dev/null || echo "failed")

            if echo "$test_result" | grep -q "succeeded\|open"; then
                echo -e "    ${GREEN}✓ Connectivity verified${NC}"
            else
                echo -e "    ${YELLOW}⚠ Could not verify connectivity, but will proceed${NC}"

                # Try alternative ports if main port fails
                for alt_port in 8000 8001 8080 8081; do
                    if [ "$alt_port" != "$api_port" ]; then
                        echo "    Trying alternative port ${alt_port}..."
                        test_result=$(docker exec apisix-apisix sh -c "nc -zv ${api_host} ${alt_port} 2>&1" 2>/dev/null || echo "failed")
                        if echo "$test_result" | grep -q "succeeded\|open"; then
                            api_port="$alt_port"
                            echo -e "    ${GREEN}✓ Found working port: ${alt_port}${NC}"
                            break
                        fi
                    fi
                done
            fi
        else
            echo -e "    ${YELLOW}⚠ Could not detect listening port, using default 8000${NC}"
            api_port="8000"
            api_host="violentutf_api"
        fi
    else
        # Container not running, check existing working routes
        echo "    FastAPI container not found, checking existing routes for reference..."
        local existing_upstream=$(curl -s "${APISIX_ADMIN_URL}/apisix/admin/routes" \
            -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null | \
            python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data.get('list', []):
    route = item.get('value', {})
    nodes = route.get('upstream', {}).get('nodes', {})
    for node in nodes:
        if 'violentutf' in node.lower() or ':800' in node:
            print(node)
            break
" 2>/dev/null | head -1)

        if [ -n "$existing_upstream" ]; then
            api_host=$(echo "$existing_upstream" | cut -d':' -f1)
            api_port=$(echo "$existing_upstream" | cut -d':' -f2)
            echo "    Using upstream from existing routes: ${api_host}:${api_port}"
        else
            # Default fallback
            api_host="violentutf_api"
            api_port="8000"
            echo -e "    ${YELLOW}⚠ Using default: ${api_host}:${api_port}${NC}"
        fi
    fi

    echo "  Final upstream configuration: ${api_host}:${api_port}"

    # Create the complete route configuration
    local route_config='{
        "uri": "'"$uri"'",
        "methods": ["'"$method"'"],
        "desc": "'"$description"'",
        "status": 1,
        "upstream": {
            "type": "roundrobin",
            "nodes": {
                "'"${api_host}:${api_port}"'": 1
            },
            "scheme": "http",
            "pass_host": "pass"
        },
        "plugins": {
            "key-auth": {},
            "proxy-rewrite": {
                "regex_uri": ["^/ai/openapi/gsai-api-1/(.*)", "/$1"],
                "headers": {
                    "set": {
                        "Authorization": "Bearer '"$GSAI_API_KEY"'"
                    }
                }
            }
        }
    }'

    # First, find and delete ALL existing routes with this base pattern
    echo "  Removing old routes with pattern: ${route_base}*"

    # Get list of all routes and delete matching ones
    # Use grep || true because not finding routes is OK
    existing_routes=$(curl -s "${APISIX_ADMIN_URL}/apisix/admin/routes" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" | \
        { grep -o "\"key\":\"/apisix/routes/${route_base}[^\"]*\"" || true; } | \
        cut -d'"' -f4 | cut -d'/' -f4)

    if [ -n "$existing_routes" ]; then
        echo "$existing_routes" | while read -r old_route_id; do
            if [ -n "$old_route_id" ]; then
                echo "    Deleting: $old_route_id"
                curl -s -X DELETE "${APISIX_ADMIN_URL}/apisix/admin/routes/${old_route_id}" \
                    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" &>/dev/null || true
            fi
        done
    fi

    # Also specifically try common malformed patterns
    curl -s -X DELETE "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_base}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" &>/dev/null || true
    curl -s -X DELETE "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_base}-" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" &>/dev/null || true

    # Create the new route with proper suffix
    echo "  Creating new route with suffix..."
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d "${route_config}" 2>/dev/null)

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "  ${GREEN}✅ Successfully created route${NC}"

        # Verify the update
        echo "  Verifying configuration..."
        updated_route=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
            -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

        # Check if we got a valid response
        if [ -z "$updated_route" ]; then
            echo -e "  ${YELLOW}⚠ Warning: Could not verify route - APISIX might be slow to update${NC}"
        else
            # Check for methods - grep returns 1 if not found, which is expected behavior
            if echo "$updated_route" | grep -q '"methods"'; then
                methods=$(echo "$updated_route" | grep -o '"methods":\[[^]]*\]' || echo "not found")
                echo -e "  ${GREEN}✅ Methods confirmed: $methods${NC}"
            else
                echo -e "  ${RED}❌ Warning: methods not found in route configuration${NC}"
                echo -e "  ${YELLOW}  Response received: ${updated_route:0:100}...${NC}"
            fi

            # Check for regex_uri - grep returns 1 if not found, which is expected behavior
            if echo "$updated_route" | grep -q "regex_uri"; then
                echo -e "  ${GREEN}✅ regex_uri confirmed in route${NC}"
            else
                echo -e "  ${RED}❌ Warning: regex_uri not found in route configuration${NC}"
                echo -e "  ${YELLOW}  This means path rewriting won't work${NC}"
            fi
        fi
    else
        echo -e "  ${RED}❌ Failed to update (HTTP $http_code)${NC}"
        echo "Response: $(echo "$response" | grep -v "HTTP_CODE:")"
    fi
    echo
}

# Update the three main OpenAPI routes with proper IDs
update_route "openapi-gsai-api-1-completions" \
    "/ai/openapi/gsai-api-1/api/v1/chat/completions" \
    "POST" \
    "GSAi Chat Completions"

update_route "openapi-gsai-api-1-embeddings" \
    "/ai/openapi/gsai-api-1/api/v1/embeddings" \
    "POST" \
    "GSAi Embeddings"

update_route "openapi-gsai-api-1-models" \
    "/ai/openapi/gsai-api-1/api/v1/models" \
    "GET" \
    "GSAi Models"

echo -e "${GREEN}=== Update Complete ===${NC}"
echo
echo "Verifying all routes..."

# List all OpenAPI routes to confirm
all_routes=$(curl -s "${APISIX_ADMIN_URL}/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

echo "Current OpenAPI routes:"
echo "$all_routes" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    routes = data.get('list', [])
    openapi_routes = [r for r in routes if 'openapi-gsai-api-1' in r.get('key', '')]
    for route in openapi_routes:
        key = route.get('key', '').split('/')[-1]
        value = route.get('value', {})
        methods = value.get('methods', [])
        uri = value.get('uri', '')
        print(f'  - {key}')
        print(f'    URI: {uri}')
        print(f'    Methods: {methods}')
except Exception as e:
    print(f'Error parsing: {e}')
" 2>/dev/null || echo "  Could not parse routes"

echo
echo "Next steps:"
echo "1. Run: ./scripts/stack_check.sh"
echo "2. Choose option 7 to verify routes are properly configured"
echo "3. Choose option 5 to test the OpenAPI endpoints"
echo
echo "The routes should now:"
echo "  - Have proper route IDs with suffixes (like in dev)"
echo "  - Include HTTP methods (GET for models, POST for completions/embeddings)"
echo "  - Rewrite paths correctly with regex_uri"
echo "  - Include Authorization header with your API key"
