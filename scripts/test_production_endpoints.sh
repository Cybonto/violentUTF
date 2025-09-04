#!/usr/bin/env bash
# Interactive script to test API endpoints through APISIX in production
# This script helps debug the 404 errors and empty model options issues

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
    echo -e "${BLUE}Production API Endpoint Testing${NC}"
    echo "This script will test the FastAPI endpoints through APISIX to debug the production issues."
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

# Test 1: Check AI Gateway parameters (should have populated model options)
test_ai_gateway_parameters() {
    print_header "TEST 1: AI Gateway Parameters (Model Options Fix)"
    
    local url="$FASTAPI_BASE_URL/api/v1/generators/types/AI%20Gateway/params"
    print_info "Testing: $url"
    
    echo "Calling API..."
    local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
        -H "Authorization: Bearer $FASTAPI_TOKEN" \
        "$url")
    
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    echo "HTTP Status: $http_status"
    
    if [ "$http_status" = "200" ]; then
        print_success "API call successful"
        
        # Check if model parameter has options
        local model_options=$(echo "$body" | jq -r '.parameters[] | select(.name=="model") | .options | length')
        if [ "$model_options" != "null" ] && [ "$model_options" -gt 0 ]; then
            print_success "Model parameter has $model_options options (fix working!)"
            echo "Model options preview:"
            echo "$body" | jq -r '.parameters[] | select(.name=="model") | .options[0:3][]' | head -3
        else
            print_error "Model parameter still has empty options"
            echo "Model parameter details:"
            echo "$body" | jq '.parameters[] | select(.name=="model")'
        fi
        
        # Check provider options  
        local provider_options=$(echo "$body" | jq -r '.parameters[] | select(.name=="provider") | .options | length')
        if [ "$provider_options" != "null" ] && [ "$provider_options" -gt 0 ]; then
            print_success "Provider parameter has $provider_options options"
            echo "Provider options:"
            echo "$body" | jq -r '.parameters[] | select(.name=="provider") | .options[]'
        else
            print_warning "Provider parameter has no options"
        fi
    else
        print_error "API call failed with status $http_status"
        echo "Response body:"
        echo "$body"
    fi
}

# Test 2: List APISIX routes (find OpenAPI routes)
test_apisix_routes() {
    print_header "TEST 2: APISIX Routes (Find OpenAPI Endpoints)"
    
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
        
        # Count total routes
        local total_routes=$(echo "$body" | jq -r '.list.list | length')
        print_info "Total routes: $total_routes"
        
        # Find OpenAPI routes
        local openapi_routes=$(echo "$body" | jq -r '.list.list[] | select(.uri | contains("openapi")) | .uri')
        if [ -n "$openapi_routes" ]; then
            print_success "Found OpenAPI routes:"
            echo "$openapi_routes" | while read -r route; do
                echo "  - $route"
            done
            
            # Test first OpenAPI route
            local first_route=$(echo "$openapi_routes" | head -1)
            if [ -n "$first_route" ]; then
                echo
                print_info "Testing first OpenAPI route: $first_route"
                test_openapi_endpoint "$first_route"
            fi
        else
            print_error "No OpenAPI routes found"
            print_info "Available route URIs:"
            echo "$body" | jq -r '.list.list[].uri' | head -10
        fi
    else
        print_error "APISIX admin API call failed with status $http_status"
        echo "Response body:"
        echo "$body"
    fi
}

# Test 3: Test OpenAPI endpoint directly
test_openapi_endpoint() {
    local endpoint_path="$1"
    print_header "TEST 3: OpenAPI Endpoint Direct Test"
    
    local url="$FASTAPI_BASE_URL$endpoint_path"
    print_info "Testing: $url"
    
    # Try different HTTP methods
    for method in GET POST; do
        echo
        print_info "Trying $method request..."
        
        local curl_args=("-s" "-w" "\nHTTP_STATUS:%{http_code}" "-X" "$method")
        curl_args+=("-H" "Authorization: Bearer $FASTAPI_TOKEN")
        
        if [ "$method" = "POST" ]; then
            curl_args+=("-H" "Content-Type: application/json")
            # Try with a simple chat completion request
            if [[ "$endpoint_path" == *"chat/completions"* ]]; then
                curl_args+=("-d" '{"model":"claude_3_5_sonnet","messages":[{"role":"user","content":"Hello"}],"max_tokens":100}')
            fi
        fi
        
        local response=$(curl "${curl_args[@]}" "$url")
        local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
        local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
        
        echo "  HTTP Status: $http_status"
        
        if [ "$http_status" = "200" ]; then
            print_success "$method request successful"
            echo "  Response preview:"
            echo "$body" | head -3
        elif [ "$http_status" = "404" ]; then
            print_error "$method request failed - 404 Not Found (this is the problem!)"
        elif [ "$http_status" = "401" ]; then
            print_warning "$method request failed - 401 Unauthorized (check token)"
        else
            print_warning "$method request failed with status $http_status"
            echo "  Response: $body" | head -2
        fi
    done
}

# Test 4: Test generator resolution
test_generator_resolution() {
    print_header "TEST 4: Generator Resolution (Orchestrator Issue)"
    
    # Get list of generators first
    local generators_url="$FASTAPI_BASE_URL/api/v1/generators"
    print_info "Getting generators list: $generators_url"
    
    local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
        -H "Authorization: Bearer $FASTAPI_TOKEN" \
        "$generators_url")
    
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    if [ "$http_status" = "200" ]; then
        print_success "Generators list retrieved"
        
        # Find a generator to test
        local generator_names=$(echo "$body" | jq -r 'keys[]' | head -3)
        
        if [ -n "$generator_names" ]; then
            print_info "Available generators:"
            echo "$generator_names" | while read -r name; do
                echo "  - $name"
            done
            
            # Test first generator
            local first_gen=$(echo "$generator_names" | head -1)
            print_info "Testing generator resolution for: $first_gen"
            
            # Try to get generator endpoint
            local endpoint_url="$FASTAPI_BASE_URL/api/v1/generators/$first_gen/endpoint"
            print_info "Testing endpoint resolution: $endpoint_url"
            
            local endpoint_response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
                -H "Authorization: Bearer $FASTAPI_TOKEN" \
                "$endpoint_url")
            
            local endpoint_status=$(echo "$endpoint_response" | grep "HTTP_STATUS:" | cut -d: -f2)
            local endpoint_body=$(echo "$endpoint_response" | sed '/HTTP_STATUS:/d')
            
            echo "Endpoint resolution status: $endpoint_status"
            if [ "$endpoint_status" = "200" ]; then
                print_success "Generator endpoint resolved successfully"
                echo "Endpoint details:"
                echo "$endpoint_body" | jq '.'
            else
                print_error "Generator endpoint resolution failed"
                echo "Error response: $endpoint_body"
            fi
        else
            print_warning "No generators found to test"
        fi
    else
        print_error "Failed to get generators list: $http_status"
        echo "Response: $body"
    fi
}

# Test 5: Test orchestrator creation
test_orchestrator_creation() {
    print_header "TEST 5: Orchestrator Creation (Direct Issue Test)"
    
    local url="$FASTAPI_BASE_URL/api/v1/orchestrator/create"
    print_info "Testing: $url"
    
    # Create a simple test orchestrator
    local payload='{
        "name": "endpoint_test_debug",
        "orchestrator_type": "PromptSendingOrchestrator",
        "description": "Debug test for endpoint resolution",
        "parameters": {
            "objective_target": {
                "type": "configured_generator",
                "generator_name": "test1"
            },
            "user_context": "production_test"
        }
    }'
    
    print_info "Creating test orchestrator..."
    echo "Payload:"
    echo "$payload" | jq '.'
    
    local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $FASTAPI_TOKEN" \
        -d "$payload" \
        "$url")
    
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    echo "HTTP Status: $http_status"
    
    if [ "$http_status" = "200" ] || [ "$http_status" = "201" ]; then
        print_success "Orchestrator created successfully"
        local orchestrator_id=$(echo "$body" | jq -r '.id // .orchestrator_id // empty')
        if [ -n "$orchestrator_id" ]; then
            print_info "Orchestrator ID: $orchestrator_id"
            
            # Try to send a message to test the 404 issue
            print_info "Testing message send (this might trigger the 404 error)..."
            test_orchestrator_message "$orchestrator_id"
        fi
    else
        print_error "Orchestrator creation failed with status $http_status"
        echo "Response: $body"
    fi
}

# Test orchestrator message sending
test_orchestrator_message() {
    local orchestrator_id="$1"
    
    local send_url="$FASTAPI_BASE_URL/api/v1/orchestrator/$orchestrator_id/send"
    print_info "Testing message send: $send_url"
    
    local message_payload='{"prompt": "Hello, this is a test message to debug the 404 error."}'
    
    local response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $FASTAPI_TOKEN" \
        -d "$message_payload" \
        "$send_url")
    
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    echo "Message send status: $http_status"
    
    if [ "$http_status" = "200" ]; then
        print_success "Message sent successfully - 404 error is fixed!"
        echo "Response preview:"
        echo "$body" | head -3
    elif [ "$http_status" = "404" ]; then
        print_error "404 error reproduced! This confirms the issue."
        echo "Error response: $body"
    else
        print_warning "Unexpected status: $http_status"
        echo "Response: $body"
    fi
}

# Main execution
main() {
    print_header "ViolentUTF Production Endpoint Testing"
    echo "This script tests the production API endpoints to debug:"
    echo "1. Empty model options issue (should be fixed)"
    echo "2. 404 error in test conversations"
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
    test_ai_gateway_parameters
    test_apisix_routes
    test_generator_resolution
    test_orchestrator_creation
    
    print_header "TESTING COMPLETE"
    print_info "Review the results above to identify the issues:"
    echo "  - Empty model options → Should be fixed if Test 1 shows populated options"
    echo "  - 404 error → Check if OpenAPI routes exist in Test 2 and work in Test 3"
    echo "  - Generator resolution → Test 4 shows if generators can be resolved to endpoints"
    echo "  - Orchestrator 404 → Test 5 reproduces the exact issue from the UI"
}

# Run the script
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi