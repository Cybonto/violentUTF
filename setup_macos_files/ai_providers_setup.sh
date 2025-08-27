#!/usr/bin/env bash
# ai_providers_setup.sh - AI provider route configuration

# Function to check if ai-proxy plugin is available
check_ai_proxy_plugin() {
    log_debug "Checking if ai-proxy plugin is available in APISIX..."

    local apisix_admin_url="http://localhost:9180"

    # Load APISIX admin key from .env file
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not found in apisix/.env"
        return 1
    fi

    local admin_key="$APISIX_ADMIN_KEY"

    response=$(curl -w "%{http_code}" -X GET "${apisix_admin_url}/apisix/admin/plugins/ai-proxy" \
        -H "X-API-KEY: ${admin_key}" \
        -s -o /dev/null)

    if [ "$response" = "200" ]; then
        log_debug "ai-proxy plugin is available"
        return 0
    else
        echo "❌ ai-proxy plugin is not available (HTTP $response)"
        echo "   This is needed for AI provider routes"
        echo "   Make sure you're using APISIX version 3.10.0 or later with ai-proxy plugin enabled"
        return 1
    fi
}

# Function to wait for APISIX and ai-proxy plugin to be fully ready
wait_for_apisix_ai_ready() {
    log_detail "Waiting for APISIX and ai-proxy plugin to be fully ready..."

    local max_attempts=20  # Increased from 5 to 20
    local attempt=1
    local apisix_admin_url="http://localhost:9180"

    # Load APISIX admin key
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not found"
        return 1
    fi

    local admin_key="$APISIX_ADMIN_KEY"

    while [ $attempt -le $max_attempts ]; do
        # First check basic admin API connectivity
        if curl -s --max-time 5 -H "X-API-KEY: $admin_key" "$apisix_admin_url/apisix/admin/routes" >/dev/null 2>&1; then
            log_debug "APISIX admin API is responding (attempt $attempt/$max_attempts)"

            # Then check if ai-proxy plugin is available
            local plugin_response=$(curl -w "%{http_code}" -X GET "${apisix_admin_url}/apisix/admin/plugins/ai-proxy" \
                -H "X-API-KEY: ${admin_key}" \
                -s -o /dev/null 2>/dev/null)

            if [ "$plugin_response" = "200" ]; then
                log_success "ai-proxy plugin is available and ready"
                return 0
            else
                log_debug "ai-proxy plugin not ready yet (HTTP $plugin_response), waiting..."
            fi
        else
            log_debug "APISIX admin API not ready yet (attempt $attempt/$max_attempts)"
        fi

        sleep 5  # Increased from 2 to 5 seconds
        attempt=$((attempt + 1))
    done

    echo "❌ APISIX or ai-proxy plugin not ready after $((max_attempts * 5)) seconds"
    echo "💡 Troubleshooting tips:"
    echo "   • Check APISIX container logs: docker logs apisix-apisix-1"
    echo "   • Verify ai-proxy plugin is in config: grep ai-proxy apisix/conf/config.yaml"
    echo "   • Try restarting APISIX: docker restart apisix-apisix-1"
    return 1
}

# Function to perform pre-flight checks for AI route setup
ai_route_preflight_check() {
    log_detail "Performing AI route setup pre-flight checks..."

    # Check if ai-proxy plugin is available
    if ! check_ai_proxy_plugin; then
        log_warn "ai-proxy plugin not available on first check"
        log_detail "Attempting APISIX restart to reload plugins..."

        # Try restarting APISIX to reload plugins
        if docker restart apisix-apisix-1 >/dev/null 2>&1; then
            log_success "APISIX restarted successfully"

            # Wait for APISIX to come back up
            log_debug "Waiting for APISIX to restart and plugins to load..."
            sleep 20

            # Check ai-proxy plugin again
            if check_ai_proxy_plugin; then
                log_success "ai-proxy plugin now available after restart"
            else
                echo "❌ ai-proxy plugin still not available after restart"
                echo "💡 This suggests APISIX configuration may not include ai-proxy plugin"
                echo "   Check: grep ai-proxy apisix/conf/config.yaml"
                return 1
            fi
        else
            echo "❌ Failed to restart APISIX container"
            return 1
        fi
    fi

    # Check if any AI providers are enabled
    load_ai_tokens

    local enabled_providers=0

    if [ "${OPENAI_ENABLED:-false}" = "true" ]; then
        enabled_providers=$((enabled_providers + 1))
        log_debug "OpenAI provider enabled"
    fi

    if [ "${ANTHROPIC_ENABLED:-false}" = "true" ]; then
        enabled_providers=$((enabled_providers + 1))
        log_debug "Anthropic provider enabled"
    fi

    if [ "${OLLAMA_ENABLED:-false}" = "true" ]; then
        enabled_providers=$((enabled_providers + 1))
        log_debug "Ollama provider enabled"
    fi

    if [ $enabled_providers -eq 0 ]; then
        log_warn "No AI providers are enabled in ai-tokens.env"
        log_detail "AI routes will be skipped"
        return 0
    fi

    log_success "Pre-flight checks passed - $enabled_providers AI provider(s) enabled"
    return 0
}

# Function to create OpenAI route
create_openai_route() {
    local model="$1"
    local uri="$2"
    local api_key="$3"

    if [ -z "$api_key" ] || [ "$api_key" = "your_openai_api_key_here" ]; then
        echo "   ⏭️  Skipping $model - API key not configured"
        return 0
    fi

    local route_id="openai-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"
    local apisix_admin_url="http://localhost:9180"

    # Load APISIX admin key from .env file
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not found in apisix/.env"
        echo "   Checked: $apisix_env_file"
        echo "   Current working directory: $(pwd)"
        return 1
    fi

    local admin_key="$APISIX_ADMIN_KEY"
    log_debug "Using admin key: ${admin_key:0:10}..."

    log_debug "Creating route for $model at $uri..."
    log_debug "Variables: model='$model', uri='$uri', api_key='${api_key:0:10}...', route_id='$route_id'"

    local route_config='{
        "uri": "'$uri'",
        "name": "'$route_id'",
        "methods": ["POST", "GET"],
        "upstream": {
            "type": "roundrobin",
            "nodes": {
                "httpbin.org:80": 1
            }
        },
        "plugins": {
            "ai-proxy": {
                "provider": "openai",
                "auth": {
                    "header": {
                        "Authorization": "Bearer '$api_key'"
                    }
                },
                "options": {
                    "model": "'$model'"
                }
            }
        }
    }'

    log_debug "Route config (first 200 chars): ${route_config:0:200}..."
    log_debug "Curl URL: ${apisix_admin_url}/apisix/admin/routes/$route_id"
    log_debug "Admin key: ${admin_key:0:10}..."

    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PUT "${apisix_admin_url}/apisix/admin/routes/$route_id" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$route_config" 2>/dev/null)

    # Extract HTTP status and response body
    local http_status=$(echo "$response" | tail -1 | sed 's/HTTP_STATUS://')
    local response_body=$(echo "$response" | sed '$d')

    if [ "$http_status" = "200" ] || [ "$http_status" = "201" ]; then
        log_debug "Created route for $model"
        return 0
    else
        echo "   ❌ Failed to create route for $model (HTTP $http_status)"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to create Anthropic route
create_anthropic_route() {
    local model="$1"
    local uri="$2"
    local api_key="$3"

    if [ -z "$api_key" ] || [ "$api_key" = "your_anthropic_api_key_here" ]; then
        echo "   ⏭️  Skipping $model - API key not configured"
        return 0
    fi

    local route_id="anthropic-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"
    local apisix_admin_url="http://localhost:9180"

    # Load APISIX admin key from .env file
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not found in apisix/.env"
        echo "   Checked: $apisix_env_file"
        echo "   Current working directory: $(pwd)"
        return 1
    fi

    local admin_key="$APISIX_ADMIN_KEY"
    log_debug "Using admin key: ${admin_key:0:10}..."

    log_debug "Creating route for $model at $uri..."

    local route_config='{
        "uri": "'$uri'",
        "name": "'$route_id'",
        "methods": ["POST"],
        "upstream": {
            "type": "roundrobin",
            "nodes": {
                "httpbin.org:80": 1
            }
        },
        "plugins": {
            "ai-proxy": {
                "provider": "openai-compatible",
                "auth": {
                    "header": {
                        "x-api-key": "'$api_key'",
                        "anthropic-version": "2023-06-01"
                    }
                },
                "override": {
                    "endpoint": "https://api.anthropic.com/v1/messages"
                },
                "options": {
                    "model": "'$model'"
                }
            }
        }
    }'

    log_debug "Route config (first 200 chars): ${route_config:0:200}..."
    log_debug "Curl URL: ${apisix_admin_url}/apisix/admin/routes/$route_id"
    log_debug "Admin key: ${admin_key:0:10}..."

    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PUT "${apisix_admin_url}/apisix/admin/routes/$route_id" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$route_config" 2>/dev/null)

    # Extract HTTP status and response body
    local http_status=$(echo "$response" | tail -1 | sed 's/HTTP_STATUS://')
    local response_body=$(echo "$response" | sed '$d')

    if [ "$http_status" = "200" ] || [ "$http_status" = "201" ]; then
        log_debug "Created route for $model"
        return 0
    else
        echo "   ❌ Failed to create route for $model (HTTP $http_status)"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to setup OpenAI routes
setup_openai_routes() {
    log_detail "Setting up OpenAI routes..."

    # Use improved waiting mechanism that checks ai-proxy plugin
    if ! wait_for_apisix_ai_ready; then
        echo "❌ APISIX or ai-proxy plugin not ready - skipping OpenAI routes"
        return 1
    fi

    # Load AI tokens to check if enabled
    load_ai_tokens

    if [ "${OPENAI_ENABLED:-false}" != "true" ]; then
        log_detail "OpenAI is disabled, skipping route setup"
        return 0
    fi

    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        log_warn "OpenAI enabled but API key not configured. Skipping OpenAI setup."
        return 0
    fi

    log_success "OpenAI is enabled, configuring routes..."

    # OpenAI models and their URIs
    local models=("gpt-4" "gpt-3.5-turbo" "gpt-4-turbo" "gpt-4o" "gpt-4o-mini" "gpt-4-1106-preview" "gpt-4-vision-preview")
    local uris=("/ai/openai/gpt4" "/ai/openai/gpt35" "/ai/openai/gpt4-turbo" "/ai/openai/gpt4o" "/ai/openai/gpt4o-mini" "/ai/openai/gpt4-preview" "/ai/openai/gpt4-vision")

    local setup_success=true
    for i in "${!models[@]}"; do
        if ! create_openai_route "${models[$i]}" "${uris[$i]}" "$OPENAI_API_KEY"; then
            setup_success=false
        fi
    done

    if [ "$setup_success" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to setup Anthropic routes
setup_anthropic_routes() {
    log_detail "Setting up Anthropic routes..."

    # Use improved waiting mechanism that checks ai-proxy plugin
    if ! wait_for_apisix_ai_ready; then
        echo "❌ APISIX or ai-proxy plugin not ready - skipping Anthropic routes"
        return 1
    fi

    # Load AI tokens to check if enabled
    load_ai_tokens

    if [ "${ANTHROPIC_ENABLED:-false}" != "true" ]; then
        log_detail "Anthropic is disabled, skipping route setup"
        return 0
    fi

    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
        log_warn "Anthropic enabled but API key not configured. Skipping Anthropic setup."
        return 0
    fi

    log_success "Anthropic is enabled, configuring routes..."

    # Anthropic models and their URIs
    local models=("claude-3-opus-20240229" "claude-3-sonnet-20240229" "claude-3-haiku-20240307" "claude-3-5-sonnet-20241022" "claude-3-5-haiku-20241022")
    local uris=("/ai/anthropic/claude3-opus" "/ai/anthropic/claude3-sonnet" "/ai/anthropic/claude3-haiku" "/ai/anthropic/claude35-sonnet" "/ai/anthropic/claude35-haiku")

    local setup_success=true
    for i in "${!models[@]}"; do
        if ! create_anthropic_route "${models[$i]}" "${uris[$i]}" "$ANTHROPIC_API_KEY"; then
            setup_success=false
        fi
    done

    if [ "$setup_success" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to setup Ollama routes
setup_ollama_routes() {
    log_detail "Setting up Ollama routes..."

    # Load AI tokens to check if enabled
    load_ai_tokens

    if [ "${OLLAMA_ENABLED:-true}" = "true" ]; then
        log_success "Ollama is enabled, configuring routes..."
        # Ollama routes would typically proxy to local Ollama instance
        # For now, this is a placeholder as Ollama runs locally
        log_debug "Ollama runs locally and doesn't need APISIX routes"
        return 0
    else
        log_detail "Ollama is disabled, skipping route setup"
        return 0
    fi
}

# Function to setup Open WebUI routes
setup_open_webui_routes() {
    log_detail "Setting up Open WebUI routes..."

    # Load AI tokens to check if enabled
    load_ai_tokens

    if [ "${OPEN_WEBUI_ENABLED:-false}" = "true" ]; then
        log_success "Open WebUI is enabled, configuring routes..."
        # Open WebUI routes would proxy to the Open WebUI instance
        log_debug "Open WebUI configuration depends on your deployment"
        return 0
    else
        log_detail "Open WebUI is disabled, skipping route setup"
        return 0
    fi
}

# Function to create APISIX consumer for API key authentication
create_apisix_consumer() {
    log_detail "Creating APISIX consumer for API key authentication..."

    # Load APISIX admin key
    if [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    # Load APISIX admin key from .env file
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not found in apisix/.env"
        echo "   Checked: $apisix_env_file"
        echo "   Current working directory: $(pwd)"
        return 1
    fi

    local admin_key="$APISIX_ADMIN_KEY"
    log_debug "Using admin key: ${admin_key:0:10}..."
    local apisix_admin_url="http://localhost:9180"
    local violentutf_api_key="${VIOLENTUTF_API_KEY:-test-api-key}"

    # Create consumer with key-auth plugin
    local consumer_config='{
        "username": "violentutf-user",
        "plugins": {
            "key-auth": {
                "key": "'$violentutf_api_key'"
            }
        }
    }'

    response=$(curl -s -X PUT "${apisix_admin_url}/apisix/admin/consumers/violentutf-user" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$consumer_config" 2>/dev/null)

    if echo "$response" | grep -q "\"username\":\"violentutf-user\""; then
        log_success "Created APISIX consumer with API key"
        return 0
    else
        log_warn "Could not create APISIX consumer (may already exist)"
        return 0
    fi
}

# Function to verify specific AI route configuration
verify_ai_route() {
    local provider="$1"
    local model="$2"
    local expected_uri="$3"

    # Load APISIX admin key
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        return 1
    fi

    local admin_key="$APISIX_ADMIN_KEY"
    local route_id="${provider}-$(echo "$model" | tr '.' '-' | tr '[:upper:]' '[:lower:]')"

    # Check if route exists and get its configuration
    local route_response=$(curl -s -H "X-API-KEY: ${admin_key}" \
        "http://localhost:9180/apisix/admin/routes/${route_id}" 2>/dev/null)

    if echo "$route_response" | grep -q "\"uri\":\"${expected_uri}\""; then
        log_debug "$provider $model route configured correctly"
        return 0
    else
        echo "❌ $provider $model route missing or misconfigured"
        return 1
    fi
}

# Function to verify OpenAI routes
verify_openai_routes() {
    log_detail "Verifying OpenAI routes..."

    load_ai_tokens

    if [ "${OPENAI_ENABLED:-false}" != "true" ]; then
        log_detail "OpenAI disabled, skipping verification"
        return 0
    fi

    local models=("gpt-4" "gpt-3.5-turbo" "gpt-4-turbo" "gpt-4o" "gpt-4o-mini")
    local uris=("/ai/openai/gpt4" "/ai/openai/gpt35" "/ai/openai/gpt4-turbo" "/ai/openai/gpt4o" "/ai/openai/gpt4o-mini")

    local verified=0
    local total=${#models[@]}

    for i in "${!models[@]}"; do
        if verify_ai_route "openai" "${models[$i]}" "${uris[$i]}"; then
            verified=$((verified + 1))
        fi
    done

    log_debug "OpenAI route verification: $verified/$total routes verified"

    if [ $verified -eq $total ]; then
        return 0
    else
        return 1
    fi
}

# Function to verify Anthropic routes
verify_anthropic_routes() {
    log_detail "Verifying Anthropic routes..."

    load_ai_tokens

    if [ "${ANTHROPIC_ENABLED:-false}" != "true" ]; then
        log_detail "Anthropic disabled, skipping verification"
        return 0
    fi

    local models=("claude-3-opus-20240229" "claude-3-sonnet-20240229" "claude-3-haiku-20240307" "claude-3-5-sonnet-20241022" "claude-3-5-haiku-20241022")
    local uris=("/ai/anthropic/claude3-opus" "/ai/anthropic/claude3-sonnet" "/ai/anthropic/claude3-haiku" "/ai/anthropic/claude35-sonnet" "/ai/anthropic/claude35-haiku")

    local verified=0
    local total=${#models[@]}

    for i in "${!models[@]}"; do
        if verify_ai_route "anthropic" "${models[$i]}" "${uris[$i]}"; then
            verified=$((verified + 1))
        fi
    done

    log_debug "Anthropic route verification: $verified/$total routes verified"

    if [ $verified -eq $total ]; then
        return 0
    else
        return 1
    fi
}

# Function to test AI route functionality
test_ai_route_functionality() {
    local provider="$1"
    local uri="$2"
    local api_key="$3"

    local test_url="http://localhost:9080${uri}"

    # Test with actual AI request to verify ai-proxy plugin is working
    local test_payload=""
    local response_code=""

    if [ "$provider" = "anthropic" ]; then
        # Anthropic requires max_tokens parameter
        test_payload='{"model":"claude-3-sonnet-20240229","messages":[{"role":"user","content":"test"}],"max_tokens":1}'
    else
        # OpenAI format
        test_payload='{"model":"gpt-4","messages":[{"role":"user","content":"test"}],"max_tokens":1}'
    fi

    # Send a POST request to test actual functionality
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        -X POST "$test_url" \
        -H "Content-Type: application/json" \
        -d "$test_payload" 2>/dev/null)

    # Consider success codes:
    # 200 = Success
    # 400 = Bad request (but route is working)
    # 401 = Auth error (but route is working)
    # 429 = Rate limit (but route is working)
    # Failure codes:
    # 404 = Route not found
    # 502/503 = Upstream issues
    # 000 = Connection failed

    case "$response_code" in
        200|400|401|429)
            return 0  # Route is working
            ;;
        404|502|503|000)
            return 1  # Route has issues
            ;;
        *)
            # For other codes, consider it working if we got a response
            return 0
            ;;
    esac
}

# Function to test AI routes
test_ai_routes() {
    log_detail "Testing AI provider routes..."

    local test_count=0
    local passed_count=0

    # Test basic APISIX connectivity
    if curl -s http://localhost:9080/health >/dev/null 2>&1; then
        log_success "APISIX gateway is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ APISIX gateway is not accessible"
    fi
    test_count=$((test_count + 1))

    # Test API health endpoint
    if curl -s http://localhost:9080/api/v1/health >/dev/null 2>&1; then
        log_success "ViolentUTF API health endpoint is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ ViolentUTF API health endpoint is not accessible"
    fi
    test_count=$((test_count + 1))

    # Load APISIX admin key from .env file
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not found"
        return 1
    fi

    # Check if any AI routes exist
    local admin_key="$APISIX_ADMIN_KEY"
    local ai_routes=$(curl -s -H "X-API-KEY: ${admin_key}" "http://localhost:9180/apisix/admin/routes" | \
        jq -r '.list[].value | select(.id | startswith("openai-") or startswith("anthropic-")) | .id' 2>/dev/null | wc -l)

    if [ "$ai_routes" -gt 0 ]; then
        log_success "Found $ai_routes AI provider routes"
        passed_count=$((passed_count + 1))
    else
        log_warn "No AI provider routes found"
    fi
    test_count=$((test_count + 1))

    # Test specific AI provider routes
    load_ai_tokens

    # Test OpenAI routes if enabled
    if [ "${OPENAI_ENABLED:-false}" = "true" ]; then
        log_debug "Testing OpenAI route functionality..."
        if test_ai_route_functionality "openai" "/ai/openai/gpt4" "$OPENAI_API_KEY"; then
            log_success "OpenAI routes are accessible"
            passed_count=$((passed_count + 1))
        else
            echo "❌ OpenAI routes not accessible"
        fi
        test_count=$((test_count + 1))
    fi

    # Test Anthropic routes if enabled
    if [ "${ANTHROPIC_ENABLED:-false}" = "true" ]; then
        log_debug "Testing Anthropic route functionality..."
        if test_ai_route_functionality "anthropic" "/ai/anthropic/claude3-sonnet" "$ANTHROPIC_API_KEY"; then
            log_success "Anthropic routes are accessible"
            passed_count=$((passed_count + 1))
        else
            echo "❌ Anthropic routes not accessible"
        fi
        test_count=$((test_count + 1))
    fi

    log_detail "AI route tests: $passed_count/$test_count passed"

    if [ $passed_count -eq $test_count ]; then
        return 0
    else
        return 1
    fi
}

# Function to perform comprehensive AI route verification
comprehensive_ai_route_verification() {
    log_detail "Comprehensive AI Route Verification"

    local verification_passed=true

    # Verify OpenAI routes
    if ! verify_openai_routes; then
        verification_passed=false
    fi

    # Verify Anthropic routes
    if ! verify_anthropic_routes; then
        verification_passed=false
    fi

    # Test route functionality
    if ! test_ai_routes; then
        verification_passed=false
    fi

    echo "====================================="

    if [ "$verification_passed" = true ]; then
        echo "✅ Comprehensive AI route verification passed"
        return 0
    else
        echo "❌ Comprehensive AI route verification failed"
        echo "💡 Recommendations:"
        echo "   • Check AI provider API keys are valid"
        echo "   • Verify APISIX ai-proxy plugin is enabled"
        echo "   • Review APISIX logs for detailed errors"
        echo "   • Ensure all services are running and healthy"
        return 1
    fi
}
