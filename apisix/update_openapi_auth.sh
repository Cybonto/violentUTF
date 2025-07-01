#!/usr/bin/env bash
# Update existing APISIX OpenAPI routes with authentication headers
# This script adds authentication headers to existing OpenAPI routes that may have been created without them

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

# Load AI tokens for authentication details
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

echo -e "${BLUE}=== ViolentUTF OpenAPI Route Authentication Update ===${NC}"
echo

# Function to update a route with authentication headers
update_route_auth() {
    local route_id="$1"
    local provider_id="$2"
    local existing_config="$3"
    
    # Extract provider configuration
    local provider_num=""
    for i in {1..10}; do
        local env_id=$(eval echo "\${OPENAPI_${i}_ID:-}")
        if [ "$env_id" = "$provider_id" ]; then
            provider_num=$i
            break
        fi
    done
    
    if [ -z "$provider_num" ]; then
        echo -e "${YELLOW}Warning: No configuration found for provider $provider_id${NC}"
        return 1
    fi
    
    # Get authentication details
    local auth_type=$(eval echo "\${OPENAPI_${provider_num}_AUTH_TYPE:-}")
    local auth_token=$(eval echo "\${OPENAPI_${provider_num}_AUTH_TOKEN:-}")
    local api_key=$(eval echo "\${OPENAPI_${provider_num}_API_KEY:-}")
    local api_key_header=$(eval echo "\${OPENAPI_${provider_num}_API_KEY_HEADER:-X-API-Key}")
    local basic_username=$(eval echo "\${OPENAPI_${provider_num}_BASIC_USERNAME:-}")
    local basic_password=$(eval echo "\${OPENAPI_${provider_num}_BASIC_PASSWORD:-}")
    
    # Build authentication headers based on auth_type
    local auth_headers=""
    case "$auth_type" in
        "bearer")
            if [ -n "$auth_token" ]; then
                auth_headers="\"Authorization\": \"Bearer $auth_token\""
            fi
            ;;
        "api_key")
            if [ -n "$api_key" ]; then
                auth_headers="\"$api_key_header\": \"$api_key\""
            fi
            ;;
        "basic")
            if [ -n "$basic_username" ] && [ -n "$basic_password" ]; then
                local basic_auth=$(echo -n "$basic_username:$basic_password" | base64)
                auth_headers="\"Authorization\": \"Basic $basic_auth\""
            fi
            ;;
        *)
            echo -e "${YELLOW}Unknown auth type: $auth_type for provider $provider_id${NC}"
            return 1
            ;;
    esac
    
    if [ -z "$auth_headers" ]; then
        echo -e "${YELLOW}No authentication configured for provider $provider_id${NC}"
        return 1
    fi
    
    # Extract current route configuration
    local current_plugins=$(echo "$existing_config" | jq -r '.value.plugins // {}')
    local current_proxy_rewrite=$(echo "$current_plugins" | jq -r '."proxy-rewrite" // {}')
    
    # Update proxy-rewrite plugin with authentication headers
    local updated_proxy_rewrite=$(echo "$current_proxy_rewrite" | jq --argjson headers "{$auth_headers}" '.headers.set = ($headers + (.headers.set // {}))')
    local updated_plugins=$(echo "$current_plugins" | jq --argjson pr "$updated_proxy_rewrite" '."proxy-rewrite" = $pr')
    
    # Update the route
    local update_response=$(curl -s -X PATCH "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d "{\"plugins\": $updated_plugins}")
    
    if echo "$update_response" | jq -e '.value' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Updated route $route_id with authentication headers${NC}"
        return 0
    else
        echo -e "${RED}✗ Failed to update route $route_id${NC}"
        echo "$update_response" | jq '.'
        return 1
    fi
}

# Get all routes
echo "Fetching existing APISIX routes..."
routes_response=$(curl -s -X GET "${APISIX_ADMIN_URL}/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}")

if ! echo "$routes_response" | jq -e '.list' > /dev/null 2>&1; then
    echo -e "${RED}Failed to fetch routes from APISIX${NC}"
    echo "$routes_response"
    exit 1
fi

# Find OpenAPI routes and store as JSON array
openapi_routes=$(echo "$routes_response" | jq -r '[.list[] | select(.value.uri | contains("/ai/openapi/"))]')

# Check if any routes found
route_count=$(echo "$openapi_routes" | jq 'length')

if [ "$route_count" -eq 0 ]; then
    echo -e "${YELLOW}No OpenAPI routes found${NC}"
    exit 0
fi

echo -e "${BLUE}Found $route_count OpenAPI route(s) to check${NC}"
echo

# Process each OpenAPI route
updated_count=0
skipped_count=0
failed_count=0

echo "$openapi_routes" | jq -c '.[]' | while IFS= read -r route; do
    route_id=$(echo "$route" | jq -r '.key | split("/") | last')
    route_uri=$(echo "$route" | jq -r '.value.uri')
    
    # Extract provider ID from URI
    provider_id=$(echo "$route_uri" | sed -n 's|.*/ai/openapi/\([^/]*\)/.*|\1|p')
    
    if [ -z "$provider_id" ]; then
        echo -e "${YELLOW}Could not extract provider ID from URI: $route_uri${NC}"
        ((skipped_count++))
        continue
    fi
    
    echo -e "${BLUE}Checking route: $route_id (Provider: $provider_id)${NC}"
    
    # Check if route already has authentication headers
    existing_auth=$(echo "$route" | jq -r '.value.plugins."proxy-rewrite".headers.set.Authorization // empty')
    existing_api_key=$(echo "$route" | jq -r '.value.plugins."proxy-rewrite".headers.set | to_entries[] | select(.key | contains("Key") or contains("key")) | .value // empty' | head -1)
    
    if [ -n "$existing_auth" ] || [ -n "$existing_api_key" ]; then
        echo -e "${GREEN}✓ Route already has authentication headers${NC}"
        ((skipped_count++))
        continue
    fi
    
    # Update the route
    if update_route_auth "$route_id" "$provider_id" "$route"; then
        ((updated_count++))
    else
        ((failed_count++))
    fi
    
    echo
done

# Summary
echo -e "${BLUE}=== Update Summary ===${NC}"
echo -e "Total routes checked: ${route_count}"
echo -e "${GREEN}Updated: ${updated_count}${NC}"
echo -e "${YELLOW}Skipped (already configured): ${skipped_count}${NC}"
echo -e "${RED}Failed: ${failed_count}${NC}"

# Test updated routes
if [ $updated_count -gt 0 ]; then
    echo
    echo -e "${BLUE}=== Testing Updated Routes ===${NC}"
    echo "You can test the updated routes with:"
    echo
    echo "curl -X POST http://localhost:9080/ai/openapi/{provider-id}/api/v1/chat/completions \\"
    echo "  -H \"apikey: \$VIOLENTUTF_API_KEY\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{\"model\": \"your-model\", \"messages\": [{\"role\": \"user\", \"content\": \"test\"}]}'"
fi

echo
echo -e "${GREEN}Update complete!${NC}"