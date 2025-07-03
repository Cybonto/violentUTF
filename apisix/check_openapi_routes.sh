#!/usr/bin/env bash
# Check OpenAPI routes in APISIX and their authentication configuration

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables
load_env_file() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        # Read env file line by line, skip comments and empty lines
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            if [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]]; then
                continue
            fi
            # Remove leading/trailing whitespace
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            # Export if valid
            if [[ -n "$key" && "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
                export "$key=$value"
            fi
        done < "$env_file"
    fi
}

# Load APISIX environment
if [ -f "apisix/.env" ]; then
    load_env_file "apisix/.env"
elif [ -f ".env" ]; then
    load_env_file ".env"
fi

# Load AI tokens for provider details
if [ -f "ai-tokens.env" ]; then
    load_env_file "ai-tokens.env"
elif [ -f "../ai-tokens.env" ]; then
    load_env_file "../ai-tokens.env"
fi

# APISIX configuration
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
APISIX_ADMIN_KEY="${APISIX_ADMIN_KEY}"

if [ -z "$APISIX_ADMIN_KEY" ]; then
    echo -e "${RED}Error: APISIX_ADMIN_KEY not found in environment${NC}"
    echo "Please ensure APISIX is properly configured with an admin key"
    exit 1
fi

echo -e "${BLUE}=== APISIX OpenAPI Route Diagnostic ===${NC}"
echo

# Get all routes
echo "Fetching APISIX routes..."
routes_response=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}")

if ! echo "$routes_response" | jq -e '.list' > /dev/null 2>&1; then
    echo -e "${RED}Failed to fetch routes from APISIX${NC}"
    echo "$routes_response"
    exit 1
fi

# Find OpenAPI routes and store as JSON array
openapi_routes=$(echo "$routes_response" | jq -r '[.list[] | select(.value.uri | contains("/openapi/"))]')

# Check if any routes found
route_count=$(echo "$openapi_routes" | jq 'length')

if [ "$route_count" -eq 0 ]; then
    echo -e "${YELLOW}No OpenAPI routes found in APISIX${NC}"
    exit 0
fi

echo -e "${BLUE}Found $route_count OpenAPI route(s)${NC}"
echo

# Process each OpenAPI route
echo "$openapi_routes" | jq -c '.[]' | while IFS= read -r route; do
    route_id=$(echo "$route" | jq -r '.key | split("/") | last')
    route_uri=$(echo "$route" | jq -r '.value.uri')
    
    # Extract provider ID from URI
    provider_id=$(echo "$route_uri" | sed -n 's|.*/openapi/\([^/]*\)/.*|\1|p')
    
    echo -e "${BLUE}Route: $route_id${NC}"
    echo "  URI: $route_uri"
    echo "  Provider: $provider_id"
    
    # Check upstream configuration
    upstream=$(echo "$route" | jq -r '.value.upstream')
    echo "  Upstream: $(echo "$upstream" | jq -r '.nodes | keys[0]')"
    
    # Check plugins
    plugins=$(echo "$route" | jq -r '.value.plugins')
    echo "  Plugins: $(echo "$plugins" | jq -r 'keys | join(", ")')"
    
    # Check proxy-rewrite configuration
    proxy_rewrite=$(echo "$plugins" | jq -r '."proxy-rewrite" // empty')
    if [ -n "$proxy_rewrite" ]; then
        echo "  Proxy-rewrite configured: ✓"
        
        # Check for authentication headers
        auth_headers=$(echo "$proxy_rewrite" | jq -r '.headers.set // empty')
        if [ -n "$auth_headers" ]; then
            echo "  Authentication headers:"
            echo "$auth_headers" | jq -r 'to_entries[] | "    - " + .key + ": " + (.value | tostring | if length > 20 then .[0:10] + "..." + .[-10:] else . end)'
            
            # Check specific auth headers
            has_auth_header=$(echo "$auth_headers" | jq -r 'has("Authorization")')
            has_api_key=$(echo "$auth_headers" | jq -r 'to_entries[] | select(.key | test("[Kk]ey"; "i")) | .key' | head -1)
            
            if [ "$has_auth_header" = "true" ] || [ -n "$has_api_key" ]; then
                echo -e "  ${GREEN}✓ Authentication configured${NC}"
            else
                echo -e "  ${YELLOW}⚠ No authentication headers found${NC}"
            fi
        else
            echo -e "  ${RED}✗ No headers configured in proxy-rewrite${NC}"
        fi
    else
        echo -e "  ${RED}✗ No proxy-rewrite plugin configured${NC}"
    fi
    
    # Check provider configuration
    echo "  Provider configuration:"
    for i in {1..10}; do
        env_id=$(eval echo "\${OPENAPI_${i}_ID:-}")
        if [ "$env_id" = "$provider_id" ]; then
            auth_type=$(eval echo "\${OPENAPI_${i}_AUTH_TYPE:-}")
            echo "    - Config: OPENAPI_${i}_*"
            echo "    - Auth type: ${auth_type:-not set}"
            
            # Check if auth credentials exist
            case "$auth_type" in
                "bearer")
                    auth_token=$(eval echo "\${OPENAPI_${i}_AUTH_TOKEN:-}")
                    if [ -n "$auth_token" ]; then
                        echo -e "    - Auth token: ${GREEN}configured${NC} (${#auth_token} chars)"
                    else
                        echo -e "    - Auth token: ${RED}missing${NC}"
                    fi
                    ;;
                "api_key")
                    api_key=$(eval echo "\${OPENAPI_${i}_API_KEY:-}")
                    if [ -n "$api_key" ]; then
                        echo -e "    - API key: ${GREEN}configured${NC} (${#api_key} chars)"
                    else
                        echo -e "    - API key: ${RED}missing${NC}"
                    fi
                    ;;
                "basic")
                    username=$(eval echo "\${OPENAPI_${i}_BASIC_USERNAME:-}")
                    password=$(eval echo "\${OPENAPI_${i}_BASIC_PASSWORD:-}")
                    if [ -n "$username" ] && [ -n "$password" ]; then
                        echo -e "    - Basic auth: ${GREEN}configured${NC}"
                    else
                        echo -e "    - Basic auth: ${RED}missing${NC}"
                    fi
                    ;;
            esac
            break
        fi
    done
    
    echo
done

# Summary
echo -e "${BLUE}=== Recommendations ===${NC}"
echo

# Check if any routes need updating
needs_update=$(echo "$openapi_routes" | jq '[.[] | select(.value.plugins."proxy-rewrite".headers.set | not)] | length')

if [ "$needs_update" -gt 0 ]; then
    echo -e "${YELLOW}Found $needs_update route(s) without authentication headers${NC}"
    echo "Run the following command to update them:"
    echo
    echo "  cd apisix && ./update_openapi_auth.sh"
    echo
else
    echo -e "${GREEN}All OpenAPI routes have authentication configured${NC}"
fi

# Test command
echo -e "${BLUE}=== Test Commands ===${NC}"
echo
echo "Test an OpenAPI route with:"
echo
echo "curl -v -X POST http://localhost:9080/openapi/{provider-id}/api/v1/chat/completions \\"
echo "  -H \"apikey: \$VIOLENTUTF_API_KEY\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"model\": \"your-model\", \"messages\": [{\"role\": \"user\", \"content\": \"test\"}]}'"
echo
echo "Check APISIX logs for details:"
echo "docker logs apisix-apisix-1 --tail 50"