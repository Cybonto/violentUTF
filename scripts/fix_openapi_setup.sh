#!/bin/bash

# Enhanced OpenAPI Setup Script with proper timing and environment detection
# This script ensures OpenAPI routes are properly configured in both dev and staging

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}OpenAPI Route Setup and Configuration Fix${NC}"
echo -e "${BLUE}===========================================${NC}"
echo ""

# Function to detect environment
detect_environment() {
    echo -e "${YELLOW}Detecting environment...${NC}"

    if docker ps 2>/dev/null | grep -q "ai-gov-api"; then
        echo -e "${GREEN}✅ Development environment detected (ai-gov-api present)${NC}"
        echo "dev"
    elif docker ps 2>/dev/null | grep -q "apisix"; then
        echo -e "${GREEN}✅ Staging/Production environment detected (no ai-gov-api, APISIX present)${NC}"
        echo "staging"
    else
        echo -e "${RED}❌ No recognizable environment detected${NC}"
        echo "unknown"
    fi
}

# Function to load configuration
load_configuration() {
    local env_type="$1"

    echo -e "${YELLOW}Loading configuration...${NC}"

    # Load ai-tokens.env for OpenAPI configuration
    if [ -f "$PROJECT_ROOT/ai-tokens.env" ]; then
        source "$PROJECT_ROOT/ai-tokens.env"
        echo "✅ Loaded ai-tokens.env"
    else
        echo -e "${RED}❌ ai-tokens.env not found${NC}"
        exit 1
    fi

    # Load APISIX configuration
    if [ -f "$PROJECT_ROOT/apisix/.env" ]; then
        source "$PROJECT_ROOT/apisix/.env"
        echo "✅ Loaded apisix/.env"
    else
        echo -e "${RED}❌ apisix/.env not found${NC}"
        exit 1
    fi

    # Set APISIX URLs based on environment
    if [ "$env_type" = "staging" ]; then
        APISIX_BASE_URL="http://localhost:9080"
        APISIX_ADMIN_URL="http://localhost:9180"
    else
        APISIX_BASE_URL="${APISIX_BASE_URL:-http://localhost:9080}"
        APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
    fi

    echo "   APISIX Base URL: $APISIX_BASE_URL"
    echo "   APISIX Admin URL: $APISIX_ADMIN_URL"
}

# Function to ensure APISIX is ready
ensure_apisix_ready() {
    echo -e "${YELLOW}Checking APISIX readiness...${NC}"

    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "${APISIX_ADMIN_URL}/apisix/admin/routes" \
           -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null | grep -q "200"; then
            echo -e "${GREEN}✅ APISIX Admin API is ready!${NC}"
            return 0
        fi

        attempt=$((attempt + 1))
        echo "   Waiting for APISIX... ($attempt/$max_attempts)"
        sleep 2
    done

    echo -e "${RED}❌ APISIX Admin API did not become ready${NC}"
    return 1
}

# Function to check and restart APISIX if needed
restart_apisix_if_needed() {
    echo -e "${YELLOW}Checking if APISIX needs restart for new configuration...${NC}"

    # Check if config files were recently updated
    local config_age=$(find "$PROJECT_ROOT/apisix/conf/config.yaml" -mmin -5 2>/dev/null | wc -l)

    if [ "$config_age" -gt 0 ]; then
        echo "Config files were recently updated. Restarting APISIX..."

        # Find and restart APISIX container
        local apisix_container=$(docker ps --format "{{.Names}}" | grep -E "apisix(-apisix)?(-1)?$" | head -1)

        if [ -n "$apisix_container" ]; then
            docker restart "$apisix_container" >/dev/null 2>&1
            echo "✅ APISIX restarted: $apisix_container"
            echo "Waiting for APISIX to be ready after restart..."
            sleep 15
            ensure_apisix_ready
        else
            echo -e "${YELLOW}⚠️ Could not find APISIX container to restart${NC}"
        fi
    else
        echo "✅ Config files are not recent, no restart needed"
    fi
}

# Function to check ai-proxy plugin with retries
check_ai_proxy_plugin() {
    echo -e "${YELLOW}Checking ai-proxy plugin availability...${NC}"

    local max_attempts=3
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        local response=$(curl -s -w "\n%{http_code}" -X GET "${APISIX_ADMIN_URL}/apisix/admin/plugins/list" \
            -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

        local http_code=$(echo "$response" | tail -n 1)
        local body=$(echo "$response" | head -n -1)

        if [ "$http_code" = "200" ] && echo "$body" | grep -q "ai-proxy"; then
            echo -e "${GREEN}✅ ai-proxy plugin is available${NC}"
            return 0
        fi

        attempt=$((attempt + 1))
        if [ $attempt -lt $max_attempts ]; then
            echo "   Plugin not found, retrying... ($attempt/$max_attempts)"
            sleep 5
        fi
    done

    echo -e "${YELLOW}⚠️ ai-proxy plugin not available - routes will use proxy-rewrite instead${NC}"
    return 1
}

# Function to create OpenAPI route
create_openapi_route() {
    local provider_id="$1"
    local path="$2"
    local method="$3"
    local operation_id="$4"
    local upstream_url="$5"
    local auth_token="$6"

    # Generate route ID
    local method_lower=$(echo "$method" | tr '[:upper:]' '[:lower:]')
    local path_slug=$(echo "$path" | sed 's#/#-#g' | sed 's#^-##' | sed 's#[{}]##g')
    local route_id="openapi-${provider_id}-${path_slug}-${method_lower}"

    # Create URI pattern
    local uri_pattern="/ai/openapi/${provider_id}${path}"
    uri_pattern=$(echo "$uri_pattern" | sed 's#{[^}]*}#*#g')

    echo "Creating route: $method $uri_pattern -> $upstream_url$path"

    # Build route configuration
    local route_config="{
        \"id\": \"$route_id\",
        \"uri\": \"$uri_pattern\",
        \"methods\": [\"$method\"],
        \"plugins\": {
            \"proxy-rewrite\": {
                \"uri\": \"$path\",
                \"headers\": {
                    \"add\": {
                        \"Authorization\": \"Bearer $auth_token\"
                    }
                }
            }
        },
        \"upstream\": {
            \"type\": \"roundrobin\",
            \"nodes\": {
                \"$upstream_url\": 1
            }
        }
    }"

    # Create the route
    local response=$(curl -s -w "\n%{http_code}" -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/$route_id" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d "$route_config" 2>/dev/null)

    local http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✅ Route created successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to create route (HTTP $http_code)${NC}"
        return 1
    fi
}

# Function to setup OpenAPI routes
setup_openapi_routes() {
    local env_type="$1"

    echo -e "${YELLOW}Setting up OpenAPI routes for $env_type environment...${NC}"

    if [ "$OPENAPI_ENABLED" != "true" ] || [ "$OPENAPI_1_ENABLED" != "true" ]; then
        echo "OpenAPI providers disabled in configuration"
        return 0
    fi

    # Determine upstream based on environment
    local upstream_host
    local upstream_port
    local upstream_scheme

    if [ "$env_type" = "dev" ]; then
        # In dev, use ai-gov-api
        upstream_host="ai-gov-api"
        upstream_port="8081"
        upstream_scheme="http"
        echo "Using ai-gov-api at $upstream_host:$upstream_port"
    else
        # In staging/production, use GSAi directly
        upstream_host="api.dev.gsai.mcaas.fcs.gsa.gov"
        upstream_port="443"
        upstream_scheme="https"
        echo "Using GSAi API at $upstream_host"
    fi

    local upstream_url="${upstream_host}:${upstream_port}"

    # Fetch and parse OpenAPI spec
    echo -e "${YELLOW}Fetching OpenAPI specification...${NC}"

    local spec_url="${upstream_scheme}://${upstream_url}${OPENAPI_1_SPEC_PATH}"
    local auth_header="Authorization: Bearer ${OPENAPI_1_AUTH_TOKEN}"

    # Test connectivity first
    echo "Testing connectivity to $spec_url..."
    local test_response=$(curl -s -o /dev/null -w "%{http_code}" -H "$auth_header" "$spec_url" 2>/dev/null)
    echo "Connectivity test result: HTTP $test_response"

    if [ "$test_response" != "200" ]; then
        echo -e "${RED}❌ Cannot fetch OpenAPI spec from $spec_url${NC}"
        echo "Please verify:"
        echo "  1. The endpoint is accessible"
        echo "  2. The auth token is valid"
        echo "  3. The spec path is correct"
        return 1
    fi

    # Fetch the spec
    local spec_file="/tmp/openapi_spec_$$.json"
    if curl -s -H "$auth_header" "$spec_url" -o "$spec_file"; then
        echo -e "${GREEN}✅ OpenAPI spec fetched successfully${NC}"
    else
        echo -e "${RED}❌ Failed to fetch OpenAPI spec${NC}"
        return 1
    fi

    # Create routes for key endpoints
    echo -e "${YELLOW}Creating OpenAPI routes...${NC}"

    local routes_created=0
    local routes_failed=0

    # Models endpoint (GET)
    if create_openapi_route "gsai-api-1" "/v1/models" "GET" "list-models" "$upstream_url" "$OPENAPI_1_AUTH_TOKEN"; then
        ((routes_created++))
    else
        ((routes_failed++))
    fi

    # Chat completions endpoint (POST)
    if create_openapi_route "gsai-api-1" "/v1/chat/completions" "POST" "create-chat-completion" "$upstream_url" "$OPENAPI_1_AUTH_TOKEN"; then
        ((routes_created++))
    else
        ((routes_failed++))
    fi

    # Completions endpoint (POST)
    if create_openapi_route "gsai-api-1" "/v1/completions" "POST" "create-completion" "$upstream_url" "$OPENAPI_1_AUTH_TOKEN"; then
        ((routes_created++))
    else
        ((routes_failed++))
    fi

    # Embeddings endpoint (POST)
    if create_openapi_route "gsai-api-1" "/v1/embeddings" "POST" "create-embedding" "$upstream_url" "$OPENAPI_1_AUTH_TOKEN"; then
        ((routes_created++))
    else
        ((routes_failed++))
    fi

    # Clean up
    rm -f "$spec_file"

    echo ""
    echo -e "${BLUE}OpenAPI Route Setup Summary:${NC}"
    echo "  Routes created: $routes_created"
    echo "  Routes failed: $routes_failed"

    if [ $routes_created -gt 0 ]; then
        echo -e "${GREEN}✅ OpenAPI routes configured successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to create any OpenAPI routes${NC}"
        return 1
    fi
}

# Function to verify routes
verify_routes() {
    echo -e "${YELLOW}Verifying OpenAPI routes...${NC}"

    local response=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)

    local openapi_routes=$(echo "$response" | grep -o '"id":"openapi-[^"]*"' | wc -l)

    if [ "$openapi_routes" -gt 0 ]; then
        echo -e "${GREEN}✅ Found $openapi_routes OpenAPI routes${NC}"
        echo "$response" | grep -o '"id":"openapi-[^"]*"' | sed 's/"id":"/ - /' | sed 's/"//'
        return 0
    else
        echo -e "${YELLOW}⚠️ No OpenAPI routes found${NC}"
        return 1
    fi
}

# Main execution
main() {
    # Detect environment
    ENV_TYPE=$(detect_environment)

    if [ "$ENV_TYPE" = "unknown" ]; then
        echo -e "${RED}Cannot proceed without a valid environment${NC}"
        exit 1
    fi

    # Load configuration
    load_configuration "$ENV_TYPE"

    # Ensure APISIX is ready
    if ! ensure_apisix_ready; then
        echo -e "${RED}Cannot proceed - APISIX is not ready${NC}"
        exit 1
    fi

    # Check if APISIX needs restart
    restart_apisix_if_needed

    # Check ai-proxy plugin (optional)
    check_ai_proxy_plugin

    # Setup OpenAPI routes
    if setup_openapi_routes "$ENV_TYPE"; then
        echo ""
        # Give APISIX time to sync
        echo "Waiting for route synchronization..."
        sleep 5

        # Verify routes
        verify_routes

        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}OpenAPI setup completed successfully!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo "Test the routes with:"
        echo "  curl -H 'apikey: $VIOLENTUTF_API_KEY' $APISIX_BASE_URL/ai/openapi/gsai-api-1/v1/models"
    else
        echo ""
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}OpenAPI setup failed!${NC}"
        echo -e "${RED}========================================${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
