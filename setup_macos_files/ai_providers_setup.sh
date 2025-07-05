#!/usr/bin/env bash
# ai_providers_setup.sh - AI provider route configuration

# Function to check if ai-proxy plugin is available
check_ai_proxy_plugin() {
    echo "Checking if ai-proxy plugin is available in APISIX..."
    
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
        echo "✅ ai-proxy plugin is available"
        return 0
    else
        echo "❌ ai-proxy plugin is not available"
        echo "   This is needed for AI provider routes"
        echo "   Make sure you're using APISIX version 3.10.0 or later with ai-proxy plugin enabled"
        return 1
    fi
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
    echo "   Using admin key: ${admin_key:0:10}..."
    
    echo "   Creating route for $model at $uri..."
    echo "   Debug - Variables: model='$model', uri='$uri', api_key='${api_key:0:10}...', route_id='$route_id'"
    
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
    
    echo "   Debug - Route config (first 200 chars): ${route_config:0:200}..."
    echo "   Debug - Curl URL: ${apisix_admin_url}/apisix/admin/routes/$route_id"
    echo "   Debug - Admin key: ${admin_key:0:10}..."
    
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PUT "${apisix_admin_url}/apisix/admin/routes/$route_id" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$route_config" 2>/dev/null)
    
    # Extract HTTP status and response body
    local http_status=$(echo "$response" | tail -1 | sed 's/HTTP_STATUS://')
    local response_body=$(echo "$response" | sed '$d')
    
    if [ "$http_status" = "200" ] || [ "$http_status" = "201" ]; then
        echo "   ✅ Created route for $model"
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
    echo "   Using admin key: ${admin_key:0:10}..."
    
    echo "   Creating route for $model at $uri..."
    
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
    
    echo "   Debug - Route config (first 200 chars): ${route_config:0:200}..."
    echo "   Debug - Curl URL: ${apisix_admin_url}/apisix/admin/routes/$route_id"
    echo "   Debug - Admin key: ${admin_key:0:10}..."
    
    response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X PUT "${apisix_admin_url}/apisix/admin/routes/$route_id" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$route_config" 2>/dev/null)
    
    # Extract HTTP status and response body
    local http_status=$(echo "$response" | tail -1 | sed 's/HTTP_STATUS://')
    local response_body=$(echo "$response" | sed '$d')
    
    if [ "$http_status" = "200" ] || [ "$http_status" = "201" ]; then
        echo "   ✅ Created route for $model"
        return 0
    else
        echo "   ❌ Failed to create route for $model (HTTP $http_status)"
        echo "   Response: $response_body"
        return 1
    fi
}

# Function to setup OpenAI routes
setup_openai_routes() {
    echo "Setting up OpenAI routes..."
    
    # Wait for APISIX to be ready before creating routes
    echo "Ensuring APISIX is ready for OpenAI route creation..."
    local retries=0
    local max_retries=5
    
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
    
    # Test APISIX readiness
    while [ $retries -lt $max_retries ]; do
        if curl -s --max-time 5 -H "X-API-KEY: $APISIX_ADMIN_KEY" "http://localhost:9180/apisix/admin/routes" >/dev/null 2>&1; then
            echo "✅ APISIX admin API is ready"
            break
        fi
        echo "⏳ Waiting for APISIX admin API (attempt $((retries + 1))/$max_retries)..."
        sleep 2
        retries=$((retries + 1))
    done
    
    if [ $retries -eq $max_retries ]; then
        echo "❌ APISIX admin API is not ready - skipping OpenAI routes"
        return 1
    fi
    
    # Load AI tokens to check if enabled
    load_ai_tokens
    
    if [ "${OPENAI_ENABLED:-false}" != "true" ]; then
        echo "⏭️  OpenAI is disabled, skipping route setup"
        return 0
    fi
    
    if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
        echo "⚠️  OpenAI enabled but API key not configured. Skipping OpenAI setup."
        return 0
    fi
    
    echo "✅ OpenAI is enabled, configuring routes..."
    
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
    echo "Setting up Anthropic routes..."
    
    # Wait for APISIX to be ready before creating routes
    echo "Ensuring APISIX is ready for Anthropic route creation..."
    local retries=0
    local max_retries=5
    
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
    
    # Test APISIX readiness
    while [ $retries -lt $max_retries ]; do
        if curl -s --max-time 5 -H "X-API-KEY: $APISIX_ADMIN_KEY" "http://localhost:9180/apisix/admin/routes" >/dev/null 2>&1; then
            echo "✅ APISIX admin API is ready"
            break
        fi
        echo "⏳ Waiting for APISIX admin API (attempt $((retries + 1))/$max_retries)..."
        sleep 2
        retries=$((retries + 1))
    done
    
    if [ $retries -eq $max_retries ]; then
        echo "❌ APISIX admin API is not ready - skipping Anthropic routes"
        return 1
    fi
    
    # Load AI tokens to check if enabled
    load_ai_tokens
    
    if [ "${ANTHROPIC_ENABLED:-false}" != "true" ]; then
        echo "⏭️  Anthropic is disabled, skipping route setup"
        return 0
    fi
    
    if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
        echo "⚠️  Anthropic enabled but API key not configured. Skipping Anthropic setup."
        return 0
    fi
    
    echo "✅ Anthropic is enabled, configuring routes..."
    
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
    echo "Setting up Ollama routes..."
    
    # Load AI tokens to check if enabled
    load_ai_tokens
    
    if [ "${OLLAMA_ENABLED:-true}" = "true" ]; then
        echo "✅ Ollama is enabled, configuring routes..."
        # Ollama routes would typically proxy to local Ollama instance
        # For now, this is a placeholder as Ollama runs locally
        echo "   ℹ️  Ollama runs locally and doesn't need APISIX routes"
        return 0
    else
        echo "⏭️  Ollama is disabled, skipping route setup"
        return 0
    fi
}

# Function to setup Open WebUI routes
setup_open_webui_routes() {
    echo "Setting up Open WebUI routes..."
    
    # Load AI tokens to check if enabled
    load_ai_tokens
    
    if [ "${OPEN_WEBUI_ENABLED:-false}" = "true" ]; then
        echo "✅ Open WebUI is enabled, configuring routes..."
        # Open WebUI routes would proxy to the Open WebUI instance
        echo "   ℹ️  Open WebUI configuration depends on your deployment"
        return 0
    else
        echo "⏭️  Open WebUI is disabled, skipping route setup"
        return 0
    fi
}

# Function to create APISIX consumer for API key authentication
create_apisix_consumer() {
    echo "Creating APISIX consumer for API key authentication..."
    
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
    echo "   Using admin key: ${admin_key:0:10}..."
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
        echo "✅ Created APISIX consumer with API key"
        return 0
    else
        echo "⚠️  Could not create APISIX consumer (may already exist)"
        return 0
    fi
}

# Function to test AI routes
test_ai_routes() {
    echo "Testing AI provider routes..."
    
    local test_count=0
    local passed_count=0
    
    # Test basic APISIX connectivity
    if curl -s http://localhost:9080/health >/dev/null 2>&1; then
        echo "✅ APISIX gateway is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ APISIX gateway is not accessible"
    fi
    test_count=$((test_count + 1))
    
    # Test API health endpoint
    if curl -s http://localhost:9080/api/v1/health >/dev/null 2>&1; then
        echo "✅ ViolentUTF API health endpoint is accessible"
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
        echo "✅ Found $ai_routes AI provider routes"
        passed_count=$((passed_count + 1))
    else
        echo "⚠️  No AI provider routes found"
    fi
    test_count=$((test_count + 1))
    
    echo "📊 AI route tests: $passed_count/$test_count passed"
    
    if [ $passed_count -eq $test_count ]; then
        return 0
    else
        return 1
    fi
}