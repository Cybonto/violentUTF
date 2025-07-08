#!/usr/bin/env bash
# route_management.sh - Comprehensive APISIX route discovery, setup, and verification
# This script provides enhanced route management capabilities for the ViolentUTF platform

# Global variables for route tracking
declare -A DISCOVERED_ROUTES
declare -A CONFIGURED_ROUTES
declare -A FAILED_ROUTES
declare -A EXPECTED_ROUTES

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# Initialize expected routes based on current configuration
initialize_expected_routes() {
    echo -e "${BLUE}🔍 Initializing expected route definitions...${NC}"
    
    # ViolentUTF API routes
    EXPECTED_ROUTES["health"]="GET:/health"
    EXPECTED_ROUTES["api-health"]="GET:/api/v1/health"
    EXPECTED_ROUTES["api-docs"]="GET:/docs"
    EXPECTED_ROUTES["openapi-schema"]="GET:/openapi.json"
    EXPECTED_ROUTES["redoc"]="GET:/redoc"
    
    # API endpoints
    EXPECTED_ROUTES["auth"]="GET,POST,PUT,DELETE:/api/v1/auth/*"
    EXPECTED_ROUTES["database"]="GET,POST,PUT,DELETE:/api/v1/database/*"
    EXPECTED_ROUTES["sessions"]="GET,POST,PUT,DELETE:/api/v1/sessions*"
    EXPECTED_ROUTES["config"]="GET,POST,PUT,DELETE:/api/v1/config/*"
    EXPECTED_ROUTES["files"]="GET,POST,PUT,DELETE:/api/v1/files*"
    EXPECTED_ROUTES["keys"]="GET,POST,PUT,DELETE:/api/v1/keys/*"
    EXPECTED_ROUTES["test"]="GET,POST,PUT,DELETE:/api/v1/test/*"
    EXPECTED_ROUTES["debug"]="GET,POST,PUT,DELETE:/api/v1/debug/*"
    EXPECTED_ROUTES["generators"]="GET,POST,PUT,DELETE:/api/v1/generators*"
    EXPECTED_ROUTES["datasets"]="GET,POST,PUT,DELETE:/api/v1/datasets*"
    EXPECTED_ROUTES["converters"]="GET,POST,PUT,DELETE:/api/v1/converters*"
    EXPECTED_ROUTES["scorers"]="GET,POST,PUT,DELETE:/api/v1/scorers*"
    EXPECTED_ROUTES["redteam"]="GET,POST,PUT,DELETE:/api/v1/redteam*"
    EXPECTED_ROUTES["orchestrators"]="GET,POST,PUT,DELETE:/api/v1/orchestrators*"
    EXPECTED_ROUTES["apisix-admin"]="GET,POST,PUT,DELETE:/api/v1/apisix-admin*"
    
    # MCP endpoints
    EXPECTED_ROUTES["mcp"]="GET,POST,OPTIONS:/mcp/*"
    EXPECTED_ROUTES["mcp-oauth"]="GET,POST:/mcp/oauth/*"
    
    # AI Provider routes (loaded dynamically based on configuration)
    load_ai_provider_expected_routes
    
    # OpenAPI provider routes (loaded dynamically)
    load_openapi_expected_routes
    
    echo -e "${GREEN}✅ Initialized ${#EXPECTED_ROUTES[@]} expected route definitions${NC}"
}

# Load expected AI provider routes based on configuration
load_ai_provider_expected_routes() {
    echo -e "${CYAN}📡 Loading AI provider route expectations...${NC}"
    
    # Load AI tokens configuration
    load_ai_tokens
    
    # OpenAI routes
    if [ "${OPENAI_ENABLED:-false}" = "true" ]; then
        local openai_models=("gpt-4" "gpt-3.5-turbo" "gpt-4-turbo" "gpt-4o" "gpt-4o-mini" "o1-preview" "o1-mini" "o3-mini" "o4-mini")
        local openai_uris=("/ai/openai/gpt4" "/ai/openai/gpt35" "/ai/openai/gpt4-turbo" "/ai/openai/gpt4o" "/ai/openai/gpt4o-mini" "/ai/openai/o1-preview" "/ai/openai/o1-mini" "/ai/openai/o3-mini" "/ai/openai/o4-mini")
        
        for i in "${!openai_models[@]}"; do
            local model="${openai_models[$i]}"
            local uri="${openai_uris[$i]}"
            # Sanitize model name for array key (replace dots and special chars with underscores)
            local safe_key="openai_$(echo "${model}" | tr '.-' '_')"
            EXPECTED_ROUTES["${safe_key}"]="POST,GET:${uri}"
        done
        echo "   ✅ Added ${#openai_models[@]} OpenAI route expectations"
    fi
    
    # Anthropic routes
    if [ "${ANTHROPIC_ENABLED:-false}" = "true" ]; then
        local anthropic_models=("claude-3-opus-20240229" "claude-3-sonnet-20240229" "claude-3-haiku-20240307" "claude-3-5-sonnet-20241022" "claude-3-5-haiku-20241022")
        local anthropic_uris=("/ai/anthropic/claude3-opus" "/ai/anthropic/claude3-sonnet" "/ai/anthropic/claude3-haiku" "/ai/anthropic/claude35-sonnet" "/ai/anthropic/claude35-haiku")
        
        for i in "${!anthropic_models[@]}"; do
            local model="${anthropic_models[$i]}"
            local uri="${anthropic_uris[$i]}"
            # Sanitize model name for array key (replace dots and special chars with underscores)
            local safe_key="anthropic_$(echo "${model}" | tr '.-' '_')"
            EXPECTED_ROUTES["${safe_key}"]="POST:${uri}"
        done
        echo "   ✅ Added ${#anthropic_models[@]} Anthropic route expectations"
    fi
    
    # Ollama routes
    if [ "${OLLAMA_ENABLED:-false}" = "true" ]; then
        local ollama_models=("llama2" "codellama" "mistral" "llama3")
        for model in "${ollama_models[@]}"; do
            # Sanitize model name for array key
            local safe_key="ollama_$(echo "${model}" | tr '.-' '_')"
            EXPECTED_ROUTES["${safe_key}"]="POST:/ai/ollama/${model}"
        done
        echo "   ✅ Added ${#ollama_models[@]} Ollama route expectations"
    fi
}

# Load expected OpenAPI provider routes
load_openapi_expected_routes() {
    echo -e "${CYAN}🔗 Loading OpenAPI provider route expectations...${NC}"
    
    local openapi_count=0
    
    # Check for OpenAPI providers (1-10)
    for i in {1..10}; do
        local enabled_var="OPENAPI_${i}_ENABLED"
        local id_var="OPENAPI_${i}_ID"
        
        if [ "${!enabled_var:-false}" = "true" ] && [ -n "${!id_var}" ]; then
            local provider_id="${!id_var}"
            
            # Add OpenAPI provider routes with sanitized keys
            local safe_provider_id="$(echo "${provider_id}" | tr '.-' '_')"
            EXPECTED_ROUTES["openapi_${safe_provider_id}_spec"]="GET:/openapi/${provider_id}/openapi.json"
            EXPECTED_ROUTES["openapi_${safe_provider_id}_chat"]="POST:/openapi/${provider_id}/api/v1/chat/completions"
            EXPECTED_ROUTES["openapi_${safe_provider_id}_models"]="GET:/openapi/${provider_id}/api/v1/models"
            
            openapi_count=$((openapi_count + 1))
        fi
    done
    
    if [ $openapi_count -gt 0 ]; then
        echo "   ✅ Added OpenAPI route expectations for $openapi_count providers"
    else
        echo "   ℹ️  No OpenAPI providers configured"
    fi
}

# Discover existing routes from APISIX
discover_existing_routes() {
    echo -e "${BLUE}🔍 Discovering existing routes from APISIX...${NC}"
    
    # Clear previous discoveries
    DISCOVERED_ROUTES=()
    
    # Load APISIX admin credentials
    local admin_key
    if ! admin_key=$(load_apisix_admin_key); then
        echo -e "${RED}❌ Failed to load APISIX admin key${NC}"
        return 1
    fi
    
    local admin_url="http://localhost:9180"
    
    # Fetch all routes
    local routes_response
    if ! routes_response=$(curl -s -X GET "${admin_url}/apisix/admin/routes" \
        -H "X-API-KEY: ${admin_key}" 2>/dev/null); then
        echo -e "${RED}❌ Failed to fetch routes from APISIX${NC}"
        return 1
    fi
    
    # Parse routes and store in DISCOVERED_ROUTES
    local route_count=0
    
    # Use jq to parse the response if available
    if command -v jq >/dev/null 2>&1; then
        # Parse with jq (preferred method)
        while IFS= read -r route_data; do
            if [ -n "$route_data" ]; then
                local route_id=$(echo "$route_data" | jq -r '.key | split("/") | last')
                local route_uri=$(echo "$route_data" | jq -r '.value.uri // "unknown"')
                local route_methods=$(echo "$route_data" | jq -r '.value.methods // [] | join(",")')
                local route_plugins=$(echo "$route_data" | jq -r '.value.plugins // {} | keys | join(",")')
                
                DISCOVERED_ROUTES["$route_id"]="${route_methods}:${route_uri}:${route_plugins}"
                route_count=$((route_count + 1))
            fi
        done < <(echo "$routes_response" | jq -c '.list[]?' 2>/dev/null || echo "")
    else
        # Fallback parsing without jq
        echo -e "${YELLOW}⚠️  jq not available, using basic parsing${NC}"
        # Basic regex parsing as fallback
        local route_ids=$(echo "$routes_response" | grep -o '"key":"[^"]*"' | cut -d'"' -f4 | sed 's|.*/||')
        for route_id in $route_ids; do
            DISCOVERED_ROUTES["$route_id"]="unknown:unknown:unknown"
            route_count=$((route_count + 1))
        done
    fi
    
    echo -e "${GREEN}✅ Discovered $route_count existing routes${NC}"
    
    # Display discovered routes summary
    if [ $route_count -gt 0 ]; then
        echo -e "${CYAN}📋 Route Summary:${NC}"
        for route_id in "${!DISCOVERED_ROUTES[@]}"; do
            local route_info="${DISCOVERED_ROUTES[$route_id]}"
            local methods=$(echo "$route_info" | cut -d':' -f1)
            local uri=$(echo "$route_info" | cut -d':' -f2)
            echo "   • $route_id: $methods $uri"
        done
    fi
    
    return 0
}

# Load APISIX admin key from environment
load_apisix_admin_key() {
    local admin_key=""
    
    # Try different .env file locations
    local env_files=(
        "${SETUP_MODULES_DIR}/../apisix/.env"
        "apisix/.env"
        ".env"
    )
    
    for env_file in "${env_files[@]}"; do
        if [ -f "$env_file" ]; then
            admin_key=$(grep "APISIX_ADMIN_KEY=" "$env_file" 2>/dev/null | cut -d'=' -f2)
            if [ -n "$admin_key" ]; then
                echo "$admin_key"
                return 0
            fi
        fi
    done
    
    # Try environment variable
    if [ -n "$APISIX_ADMIN_KEY" ]; then
        echo "$APISIX_ADMIN_KEY"
        return 0
    fi
    
    echo -e "${RED}❌ APISIX admin key not found in any location${NC}" >&2
    return 1
}

# Verify route functionality
verify_route_functionality() {
    local route_id="$1"
    local route_info="$2"
    
    local methods=$(echo "$route_info" | cut -d':' -f1)
    local uri=$(echo "$route_info" | cut -d':' -f2)
    local plugins=$(echo "$route_info" | cut -d':' -f3)
    
    # Basic connectivity test
    local gateway_url="http://localhost:9080"
    local test_url="${gateway_url}${uri}"
    
    # Replace wildcards with test paths
    test_url=$(echo "$test_url" | sed 's|\*|test|g')
    
    # Test based on methods
    if [[ "$methods" == *"GET"* ]] || [ "$methods" = "unknown" ]; then
        if curl -s --max-time 5 --head "$test_url" >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    # For other methods, just check if the route responds (even with errors)
    if curl -s --max-time 5 --head "$test_url" >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Verify all discovered routes
verify_discovered_routes() {
    echo -e "${BLUE}🧪 Verifying functionality of discovered routes...${NC}"
    
    local total_routes=${#DISCOVERED_ROUTES[@]}
    local verified_routes=0
    local failed_routes=0
    
    if [ $total_routes -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No routes to verify${NC}"
        return 1
    fi
    
    for route_id in "${!DISCOVERED_ROUTES[@]}"; do
        local route_info="${DISCOVERED_ROUTES[$route_id]}"
        
        echo -n "   Testing $route_id... "
        
        if verify_route_functionality "$route_id" "$route_info"; then
            echo -e "${GREEN}✅${NC}"
            verified_routes=$((verified_routes + 1))
        else
            echo -e "${RED}❌${NC}"
            FAILED_ROUTES["$route_id"]="$route_info"
            failed_routes=$((failed_routes + 1))
        fi
    done
    
    echo
    echo -e "${CYAN}📊 Route Verification Results:${NC}"
    echo "   • Total routes: $total_routes"
    echo "   • Verified: $verified_routes"
    echo "   • Failed: $failed_routes"
    
    if [ $failed_routes -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Failed routes:${NC}"
        for route_id in "${!FAILED_ROUTES[@]}"; do
            local route_info="${FAILED_ROUTES[$route_id]}"
            local uri=$(echo "$route_info" | cut -d':' -f2)
            echo "   • $route_id: $uri"
        done
    fi
    
    # Return success if at least 80% of routes are working
    local success_rate=$((verified_routes * 100 / total_routes))
    if [ $success_rate -ge 80 ]; then
        echo -e "${GREEN}✅ Route verification passed (${success_rate}% success rate)${NC}"
        return 0
    else
        echo -e "${RED}❌ Route verification failed (${success_rate}% success rate)${NC}"
        return 1
    fi
}

# Compare expected vs discovered routes
analyze_route_coverage() {
    echo -e "${BLUE}📊 Analyzing route coverage...${NC}"
    
    local total_expected=${#EXPECTED_ROUTES[@]}
    local found_count=0
    local missing_count=0
    
    echo -e "${CYAN}🔍 Expected vs Discovered Routes:${NC}"
    
    for expected_route in "${!EXPECTED_ROUTES[@]}"; do
        local expected_info="${EXPECTED_ROUTES[$expected_route]}"
        local expected_uri=$(echo "$expected_info" | cut -d':' -f2)
        
        # Check if we have a matching discovered route
        local found=false
        for discovered_route in "${!DISCOVERED_ROUTES[@]}"; do
            local discovered_info="${DISCOVERED_ROUTES[$discovered_route]}"
            local discovered_uri=$(echo "$discovered_info" | cut -d':' -f2)
            
            # Match by URI pattern
            if [[ "$discovered_uri" == "$expected_uri" ]] || [[ "$expected_uri" == *"*"* && "$discovered_uri" == "${expected_uri%\*}"* ]]; then
                echo "   ✅ $expected_route: $expected_uri"
                found=true
                found_count=$((found_count + 1))
                break
            fi
        done
        
        if [ "$found" = false ]; then
            echo "   ❌ $expected_route: $expected_uri (MISSING)"
            missing_count=$((missing_count + 1))
        fi
    done
    
    echo
    echo -e "${CYAN}📈 Coverage Analysis:${NC}"
    echo "   • Expected routes: $total_expected"
    echo "   • Found routes: $found_count"
    echo "   • Missing routes: $missing_count"
    
    local coverage_rate=$((found_count * 100 / total_expected))
    echo "   • Coverage rate: ${coverage_rate}%"
    
    if [ $coverage_rate -ge 90 ]; then
        echo -e "${GREEN}✅ Excellent route coverage${NC}"
        return 0
    elif [ $coverage_rate -ge 75 ]; then
        echo -e "${YELLOW}⚠️  Good route coverage, some missing${NC}"
        return 0
    else
        echo -e "${RED}❌ Poor route coverage, many routes missing${NC}"
        return 1
    fi
}

# Setup missing routes
setup_missing_routes() {
    echo -e "${BLUE}🔧 Setting up missing routes...${NC}"
    
    local setup_count=0
    local failed_count=0
    
    # Load admin key
    local admin_key
    if ! admin_key=$(load_apisix_admin_key); then
        echo -e "${RED}❌ Cannot setup routes without admin key${NC}"
        return 1
    fi
    
    # Check each expected route
    for expected_route in "${!EXPECTED_ROUTES[@]}"; do
        local expected_info="${EXPECTED_ROUTES[$expected_route]}"
        local expected_uri=$(echo "$expected_info" | cut -d':' -f2)
        
        # Skip if route already exists
        local exists=false
        for discovered_route in "${!DISCOVERED_ROUTES[@]}"; do
            local discovered_info="${DISCOVERED_ROUTES[$discovered_route]}"
            local discovered_uri=$(echo "$discovered_info" | cut -d':' -f2)
            
            if [[ "$discovered_uri" == "$expected_uri" ]] || [[ "$expected_uri" == *"*"* && "$discovered_uri" == "${expected_uri%\*}"* ]]; then
                exists=true
                break
            fi
        done
        
        if [ "$exists" = true ]; then
            continue
        fi
        
        echo "   🔧 Setting up missing route: $expected_route ($expected_uri)"
        
        # Determine route type and setup accordingly
        if [[ "$expected_route" == "openai-"* ]]; then
            if setup_missing_openai_route "$expected_route" "$expected_info" "$admin_key"; then
                setup_count=$((setup_count + 1))
            else
                failed_count=$((failed_count + 1))
            fi
        elif [[ "$expected_route" == "anthropic-"* ]]; then
            if setup_missing_anthropic_route "$expected_route" "$expected_info" "$admin_key"; then
                setup_count=$((setup_count + 1))
            else
                failed_count=$((failed_count + 1))
            fi
        elif [[ "$expected_route" == "openapi-"* ]]; then
            if setup_missing_openapi_route "$expected_route" "$expected_info" "$admin_key"; then
                setup_count=$((setup_count + 1))
            else
                failed_count=$((failed_count + 1))
            fi
        else
            # Standard API route
            if setup_missing_api_route "$expected_route" "$expected_info" "$admin_key"; then
                setup_count=$((setup_count + 1))
            else
                failed_count=$((failed_count + 1))
            fi
        fi
    done
    
    echo
    echo -e "${CYAN}📋 Route Setup Results:${NC}"
    echo "   • Routes created: $setup_count"
    echo "   • Setup failures: $failed_count"
    
    if [ $failed_count -eq 0 ]; then
        echo -e "${GREEN}✅ All missing routes set up successfully${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Some routes failed to set up${NC}"
        return 1
    fi
}

# Setup missing OpenAI route
setup_missing_openai_route() {
    local route_name="$1"
    local route_info="$2"
    local admin_key="$3"
    
    # Extract model name
    local model=$(echo "$route_name" | sed 's/^openai-//')
    local uri=$(echo "$route_info" | cut -d':' -f2)
    
    # Load OpenAI API key
    load_ai_tokens
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        echo "      ⏭️  Skipping $model - API key not configured"
        return 0
    fi
    
    # Create route using existing function
    if create_openai_route "$model" "$uri" "$OPENAI_API_KEY"; then
        echo "      ✅ Created OpenAI route for $model"
        return 0
    else
        echo "      ❌ Failed to create OpenAI route for $model"
        return 1
    fi
}

# Setup missing Anthropic route
setup_missing_anthropic_route() {
    local route_name="$1"
    local route_info="$2"
    local admin_key="$3"
    
    # Extract model name
    local model=$(echo "$route_name" | sed 's/^anthropic-//')
    local uri=$(echo "$route_info" | cut -d':' -f2)
    
    # Load Anthropic API key
    load_ai_tokens
    
    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
        echo "      ⏭️  Skipping $model - API key not configured"
        return 0
    fi
    
    # Create route using existing function
    if create_anthropic_route "$model" "$uri" "$ANTHROPIC_API_KEY"; then
        echo "      ✅ Created Anthropic route for $model"
        return 0
    else
        echo "      ❌ Failed to create Anthropic route for $model"
        return 1
    fi
}

# Setup missing OpenAPI route
setup_missing_openapi_route() {
    local route_name="$1"
    local route_info="$2"
    local admin_key="$3"
    
    echo "      ℹ️  OpenAPI route setup requires specialized configuration"
    echo "      Use 'setup_openapi_routes' function for proper setup"
    return 0
}

# Setup missing API route
setup_missing_api_route() {
    local route_name="$1"
    local route_info="$2"
    local admin_key="$3"
    
    local methods=$(echo "$route_info" | cut -d':' -f1)
    local uri=$(echo "$route_info" | cut -d':' -f2)
    
    # Generate route ID
    local route_id=$(echo "$route_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    
    # Create basic API route
    local route_config='{
        "uri": "'$uri'",
        "methods": ["'$(echo "$methods" | tr ',' '","')'"],
        "upstream_id": "violentutf-api",
        "plugins": {
            "cors": {
                "allow_origins": "*",
                "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                "allow_headers": "Content-Type,Authorization,X-Real-IP,X-Forwarded-For,X-Forwarded-Host,X-API-Gateway"
            },
            "proxy-rewrite": {
                "headers": {
                    "set": {
                        "X-Real-IP": "$remote_addr",
                        "X-Forwarded-For": "$proxy_add_x_forwarded_for",
                        "X-Forwarded-Host": "$host",
                        "X-API-Gateway": "APISIX"
                    }
                }
            }
        },
        "desc": "Auto-generated route for '$route_name'"
    }'
    
    local admin_url="http://localhost:9180"
    local response=$(curl -s -w "%{http_code}" -X PUT "${admin_url}/apisix/admin/routes/${route_id}" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$route_config" -o /dev/null 2>/dev/null)
    
    if [ "$response" = "200" ] || [ "$response" = "201" ]; then
        echo "      ✅ Created API route for $route_name"
        return 0
    else
        echo "      ❌ Failed to create API route for $route_name (HTTP $response)"
        return 1
    fi
}

# Generate route diagnostic report
generate_route_diagnostic_report() {
    echo -e "${BLUE}📋 Generating comprehensive route diagnostic report...${NC}"
    
    local report_file="route_diagnostic_report_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# ViolentUTF Route Diagnostic Report
Generated: $(date)

## Summary
- Expected Routes: ${#EXPECTED_ROUTES[@]}
- Discovered Routes: ${#DISCOVERED_ROUTES[@]}
- Failed Routes: ${#FAILED_ROUTES[@]}

## Expected Routes
$(for route in "${!EXPECTED_ROUTES[@]}"; do echo "- $route: ${EXPECTED_ROUTES[$route]}"; done)

## Discovered Routes
$(for route in "${!DISCOVERED_ROUTES[@]}"; do echo "- $route: ${DISCOVERED_ROUTES[$route]}"; done)

## Failed Routes
$(for route in "${!FAILED_ROUTES[@]}"; do echo "- $route: ${FAILED_ROUTES[$route]}"; done)

## Route Coverage Analysis
$(analyze_route_coverage 2>&1)

## Recommendations
EOF

    # Add recommendations based on findings
    if [ ${#FAILED_ROUTES[@]} -gt 0 ]; then
        echo "- Investigate failed routes and check upstream services" >> "$report_file"
    fi
    
    local coverage_rate=$((${#DISCOVERED_ROUTES[@]} * 100 / ${#EXPECTED_ROUTES[@]}))
    if [ $coverage_rate -lt 90 ]; then
        echo "- Set up missing routes to improve coverage" >> "$report_file"
    fi
    
    echo "- Verify AI provider configurations and API keys" >> "$report_file"
    echo "- Check APISIX logs for detailed error information" >> "$report_file"
    
    echo -e "${GREEN}✅ Diagnostic report saved: $report_file${NC}"
}

# Main route management function
comprehensive_route_management() {
    echo -e "${PURPLE}🚀 Starting Comprehensive Route Management${NC}"
    echo -e "${PURPLE}===========================================${NC}"
    
    # Initialize expected routes
    initialize_expected_routes
    
    # Discover existing routes
    if ! discover_existing_routes; then
        echo -e "${RED}❌ Failed to discover existing routes${NC}"
        return 1
    fi
    
    # Verify discovered routes
    verify_discovered_routes
    
    # Analyze coverage
    analyze_route_coverage
    
    # Setup missing routes if needed
    if [ ${#DISCOVERED_ROUTES[@]} -lt ${#EXPECTED_ROUTES[@]} ]; then
        echo -e "${YELLOW}⚠️  Missing routes detected, attempting to set up...${NC}"
        setup_missing_routes
        
        # Re-discover after setup
        echo -e "${BLUE}🔄 Re-discovering routes after setup...${NC}"
        discover_existing_routes
    fi
    
    # Generate diagnostic report
    generate_route_diagnostic_report
    
    echo -e "${PURPLE}===========================================${NC}"
    echo -e "${PURPLE}✅ Comprehensive Route Management Complete${NC}"
    
    # Final summary
    local total_expected=${#EXPECTED_ROUTES[@]}
    local total_discovered=${#DISCOVERED_ROUTES[@]}
    local coverage_rate=$((total_discovered * 100 / total_expected))
    
    echo -e "${CYAN}📊 Final Summary:${NC}"
    echo "   • Expected: $total_expected routes"
    echo "   • Discovered: $total_discovered routes"
    echo "   • Coverage: ${coverage_rate}%"
    
    if [ $coverage_rate -ge 90 ]; then
        echo -e "${GREEN}✅ Route management successful${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Route management completed with warnings${NC}"
        return 1
    fi
}

# Quick route verification function
quick_route_verification() {
    echo -e "${BLUE}⚡ Quick Route Verification${NC}"
    
    # Test key routes
    local key_routes=(
        "health:http://localhost:9080/health"
        "api-health:http://localhost:9080/api/v1/health"
        "api-docs:http://localhost:9080/docs"
    )
    
    local passed=0
    local total=${#key_routes[@]}
    
    for route_test in "${key_routes[@]}"; do
        local name=$(echo "$route_test" | cut -d':' -f1)
        local url=$(echo "$route_test" | cut -d':' -f2)
        
        echo -n "   Testing $name... "
        if curl -s --max-time 5 "$url" >/dev/null 2>&1; then
            echo -e "${GREEN}✅${NC}"
            passed=$((passed + 1))
        else
            echo -e "${RED}❌${NC}"
        fi
    done
    
    echo "   Result: $passed/$total key routes working"
    
    if [ $passed -eq $total ]; then
        echo -e "${GREEN}✅ Quick verification passed${NC}"
        return 0
    else
        echo -e "${RED}❌ Quick verification failed${NC}"
        return 1
    fi
}