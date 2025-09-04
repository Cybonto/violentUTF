#!/usr/bin/env bash
# Fixed production endpoint testing script
# Handles production-specific API gateway routing and JSON structures

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️ $1${NC}"
}

# Get required inputs
get_user_inputs() {
    echo -e "${BLUE}Fixed Production API Endpoint Testing${NC}"
    echo "This script handles production-specific routing and JSON structures."
    echo
    
    # Get FastAPI token
    if [ -z "$FASTAPI_TOKEN" ]; then
        echo -n "Enter your FastAPI Bearer token: "
        read -s FASTAPI_TOKEN
        echo
    fi
    
    # Get APISIX admin key  
    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo -n "Enter APISIX admin key: "
        read -s APISIX_ADMIN_KEY
        echo
    fi
    
    # Set default endpoints
    FASTAPI_BASE_URL="${FASTAPI_BASE_URL:-http://localhost:9080}"
    APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
    
    echo
    print_info "Using FastAPI base URL: $FASTAPI_BASE_URL"
    print_info "Using APISIX admin URL: $APISIX_ADMIN_URL"
    echo
}

# Test APISIX routes with flexible JSON parsing
test_apisix_routes_fixed() {
    print_header "TEST: APISIX Routes Analysis (Fixed JSON Parsing)"
    
    local url="$APISIX_ADMIN_URL/apisix/admin/routes"
    print_info "Testing: $url"
    
    echo "Calling APISIX admin API..."
    local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        "$url")
    
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    echo "HTTP Status: $http_status"
    
    if [ "$http_status" = "200" ]; then
        print_success "APISIX admin API accessible"
        
        # Debug: Show actual JSON structure
        print_info "Raw JSON structure (first 500 chars):"
        echo "$body" | head -c 500
        echo -e "\n..."
        
        # Try multiple JSON parsing approaches
        echo -e "\n🔍 Attempting to parse routes..."
        
        # Try approach 1: .list.list (original)
        local routes1=$(echo "$body" | jq -r '.list.list[]?.uri // empty' 2>/dev/null || echo "")
        if [ -n "$routes1" ]; then
            print_info "Found routes using .list.list structure:"
            echo "$routes1" | head -10
        else
            print_warning "Failed to parse with .list.list structure"
        fi
        
        # Try approach 2: Direct array
        local routes2=$(echo "$body" | jq -r '.[]?.uri // empty' 2>/dev/null || echo "")
        if [ -n "$routes2" ]; then
            print_info "Found routes using direct array structure:"
            echo "$routes2" | head -10
        else
            print_warning "Failed to parse with direct array structure"
        fi
        
        # Try approach 3: .list only
        local routes3=$(echo "$body" | jq -r '.list[]?.uri // empty' 2>/dev/null || echo "")
        if [ -n "$routes3" ]; then
            print_info "Found routes using .list structure:"
            echo "$routes3" | head -10
        else
            print_warning "Failed to parse with .list structure"
        fi
        
        # Try approach 4: Look for any uri fields anywhere
        local all_uris=$(echo "$body" | jq -r '.. | .uri? // empty' 2>/dev/null | grep -v "^$" || echo "")
        if [ -n "$all_uris" ]; then
            print_success "Found URI fields in JSON:"
            echo "$all_uris" | head -10
            
            # Look for OpenAPI routes
            local openapi_routes=$(echo "$all_uris" | grep -i openapi || echo "")
            if [ -n "$openapi_routes" ]; then
                print_success "🎯 Found OpenAPI routes:"
                echo "$openapi_routes"
            else
                print_warning "No OpenAPI routes found in URIs"
            fi
        else
            print_error "Could not find any URI fields in the JSON response"
        fi
        
        # Show available keys in the JSON
        print_info "Available top-level JSON keys:"
        echo "$body" | jq -r 'keys[]' 2>/dev/null | head -10 || echo "Could not parse JSON keys"
        
    else
        print_error "APISIX admin API call failed with status $http_status"
        echo "Response body:"
        echo "$body"
    fi
}

# Test API endpoints through gateway paths
test_gateway_endpoints() {
    print_header "TEST: API Gateway Endpoint Access"
    
    print_info "Production blocks direct API access. Testing gateway paths..."
    
    # Common gateway path patterns
    local gateway_paths=(
        "/api/v1/generators/types/AI%20Gateway/params"
        "/apisix/api/v1/generators/types/AI%20Gateway/params" 
        "/gateway/api/v1/generators/types/AI%20Gateway/params"
        "/api/gateway/v1/generators/types/AI%20Gateway/params"
    )
    
    for path in "${gateway_paths[@]}"; do
        echo
        print_info "Testing gateway path: $path"
        
        local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
            -H "Authorization: Bearer $FASTAPI_TOKEN" \
            "$FASTAPI_BASE_URL$path")
        
        local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
        local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
        
        echo "Status: $http_status"
        
        if [ "$http_status" = "200" ]; then
            print_success "✨ Gateway path works!"
            
            # Check model options fix
            local model_count=$(echo "$body" | jq -r '.parameters[] | select(.name=="model") | .options | length' 2>/dev/null || echo "0")
            if [ "$model_count" != "null" ] && [ "$model_count" -gt 0 ]; then
                print_success "🎯 Model options fix working: $model_count models found!"
            else
                print_warning "Model options still empty"
            fi
            break
            
        elif [ "$http_status" = "403" ]; then
            print_warning "403 Forbidden - gateway path not correct"
        elif [ "$http_status" = "404" ]; then
            print_warning "404 Not Found - endpoint doesn't exist at this path"
        else
            print_warning "Unexpected status: $http_status"
        fi
    done
}

# Test orchestrator endpoints
test_orchestrator_endpoints() {
    print_header "TEST: Orchestrator Endpoint Discovery"
    
    print_info "The 404 error suggests orchestrator endpoints might be at different paths..."
    
    # Common orchestrator path patterns
    local orchestrator_paths=(
        "/api/v1/orchestrator/create"
        "/api/v1/orchestrators/create"
        "/api/v1/redteam/orchestrator/create"
        "/apisix/api/v1/orchestrator/create"
    )
    
    for path in "${orchestrator_paths[@]}"; do
        echo
        print_info "Testing orchestrator path: $path"
        
        local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $FASTAPI_TOKEN" \
            -X POST \
            -d '{"test": "probe"}' \
            "$FASTAPI_BASE_URL$path")
        
        local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
        
        echo "Status: $http_status"
        
        if [ "$http_status" = "200" ] || [ "$http_status" = "201" ]; then
            print_success "✨ Found working orchestrator endpoint!"
            break
        elif [ "$http_status" = "422" ]; then
            print_success "✨ Endpoint exists (422 = validation error, which is expected for test payload)"
            break
        elif [ "$http_status" = "403" ]; then
            print_warning "403 Forbidden - endpoint exists but access denied"
        elif [ "$http_status" = "404" ]; then
            print_warning "404 Not Found - endpoint doesn't exist at this path"
        else
            print_warning "Status: $http_status"
        fi
    done
}

# Check what endpoints actually exist
discover_available_endpoints() {
    print_header "TEST: Endpoint Discovery"
    
    print_info "Probing for available API endpoints..."
    
    # Common endpoint patterns to test
    local endpoints=(
        "/api/v1/health"
        "/api/v1/generators"
        "/api/v1/orchestrators" 
        "/api/v1/redteam"
        "/health"
        "/docs"
        "/openapi.json"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
            -H "Authorization: Bearer $FASTAPI_TOKEN" \
            "$FASTAPI_BASE_URL$endpoint")
        
        local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
        
        if [ "$http_status" = "200" ]; then
            print_success "$endpoint → $http_status (Available)"
        elif [ "$http_status" = "403" ]; then
            print_warning "$endpoint → $http_status (Forbidden - needs gateway routing)"
        elif [ "$http_status" = "404" ]; then
            echo "  $endpoint → $http_status (Not Found)"
        else
            print_info "$endpoint → $http_status"
        fi
    done
}

# Main execution
main() {
    print_header "ViolentUTF Production Endpoint Analysis (Fixed)"
    echo "This script handles production-specific API gateway routing and JSON structures."
    echo
    
    # Check dependencies
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed"
        exit 1
    fi
    
    # Get user inputs
    get_user_inputs
    
    # Run tests
    discover_available_endpoints
    test_apisix_routes_fixed
    test_gateway_endpoints
    test_orchestrator_endpoints
    
    print_header "ANALYSIS COMPLETE"
    print_info "Key findings:"
    echo "  🔒 Production requires API gateway routing (no direct FastAPI access)"
    echo "  🗺️  APISIX route JSON structure differs from expected format"
    echo "  🚫 Orchestrator endpoints may be missing or at different paths"
    echo "  🎯 This explains both the empty model options and 404 conversation errors"
}

# Run the script
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi