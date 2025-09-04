#!/bin/bash

# Script to manually fix OpenAPI routes in staging with proper regex_uri

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Manual Fix for Staging OpenAPI Routes ===${NC}"
echo

# Get APISIX admin key
if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo -n "Enter APISIX Admin Key: "
    read -s APISIX_ADMIN_KEY
    echo
fi

# Get GSAi API key
echo -n "Enter GSAi API Key (from ai-tokens.env OPENAPI_1_API_KEY): "
read -s GSAI_API_KEY
echo

APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

echo -e "${YELLOW}Updating OpenAPI routes with regex_uri...${NC}"
echo

# Function to update a route with regex_uri
update_route() {
    local route_id="$1"
    local uri="$2"
    local method="$3"
    local description="$4"

    echo -e "${BLUE}Updating: $description${NC}"
    echo "  Route ID: $route_id"
    echo "  URI: $uri"

    # Create the complete route configuration with regex_uri
    local route_config='{
        "id": "'"$route_id"'",
        "uri": "'"$uri"'",
        "methods": ["'"$method"'"],
        "desc": "'"$description"'",
        "upstream": {
            "type": "roundrobin",
            "nodes": {
                "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
            },
            "scheme": "https"
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

    # Update the route
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d "${route_config}" 2>/dev/null)

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "  ${GREEN}✅ Successfully updated${NC}"

        # Verify the update
        updated_route=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
            -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

        if echo "$updated_route" | grep -q "regex_uri"; then
            echo -e "  ${GREEN}✅ regex_uri confirmed in route${NC}"
        else
            echo -e "  ${RED}❌ Warning: regex_uri not found after update${NC}"
        fi
    else
        echo -e "  ${RED}❌ Failed to update (HTTP $http_code)${NC}"
    fi
    echo
}

# Update the three main OpenAPI routes
update_route "openapi-gsai-api-1-completions-" \
    "/ai/openapi/gsai-api-1/api/v1/chat/completions" \
    "POST" \
    "GSAi Chat Completions"

update_route "openapi-gsai-api-1-embeddings-" \
    "/ai/openapi/gsai-api-1/api/v1/embeddings" \
    "POST" \
    "GSAi Embeddings"

update_route "openapi-gsai-api-1-models-" \
    "/ai/openapi/gsai-api-1/api/v1/models" \
    "GET" \
    "GSAi Models"

echo -e "${GREEN}=== Update Complete ===${NC}"
echo
echo "Next steps:"
echo "1. Run: ./scripts/stack_check.sh"
echo "2. Choose option 7 to verify regex_uri is now present"
echo "3. Choose option 5 to test the OpenAPI endpoints"
echo
echo "The routes should now properly rewrite:"
echo "  /ai/openapi/gsai-api-1/api/v1/chat/completions → /api/v1/chat/completions"
echo "  /ai/openapi/gsai-api-1/api/v1/embeddings → /api/v1/embeddings"
echo "  /ai/openapi/gsai-api-1/api/v1/models → /api/v1/models"
