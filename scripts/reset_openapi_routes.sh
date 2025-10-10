#!/bin/bash

# Script to delete and recreate OpenAPI routes with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== OpenAPI Route Reset Script ===${NC}"
echo "This will delete existing OpenAPI routes and recreate them with proper URI rewriting"
echo

# Get APISIX admin key
if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo -n "Enter APISIX Admin Key: "
    read -s APISIX_ADMIN_KEY
    echo
fi

# Set APISIX URL
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

echo -e "${YELLOW}Step 1: Deleting existing OpenAPI routes...${NC}"

# List of OpenAPI route IDs to delete
route_ids=(
    "openapi-gsai-api-1-completions-"
    "openapi-gsai-api-1-embeddings-"
    "openapi-gsai-api-1-models-"
)

for route_id in "${route_ids[@]}"; do
    echo -n "  Deleting route $route_id: "
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X DELETE "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)

    if [ "$http_code" = "200" ] || [ "$http_code" = "404" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ (HTTP $http_code)${NC}"
    fi
done

echo
echo -e "${YELLOW}Step 2: Running setup to recreate routes...${NC}"
echo "The setup script will now create fresh routes with proper regex_uri configuration"
echo

# Run the setup script to recreate routes
cd "$(dirname "$0")/.."
./setup_macos.sh

echo
echo -e "${GREEN}=== Reset Complete ===${NC}"
echo "Run './scripts/stack_check.sh' and choose option 7 to verify the routes are properly configured"
