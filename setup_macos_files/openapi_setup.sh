#!/usr/bin/env bash
# openapi_setup.sh - OpenAPI/Swagger documentation routes and configuration


# Function to fetch available models from OpenAPI provider
fetch_openapi_provider_models() {
    local base_url="$1"
    local auth_type="$2"
    local auth_token="$3"

    echo "   Fetching available models from $base_url..."

    # Build auth headers
    local auth_header=""
    case "$auth_type" in
        "bearer")
            auth_header="Authorization: Bearer $auth_token"
            ;;
        "api_key")
            auth_header="X-API-Key: $auth_token"
            ;;
        "basic")
            auth_header="Authorization: Basic $auth_token"
            ;;
    esac

    # Fetch models from /api/v1/models endpoint
    local models_json
    if [ -n "$auth_header" ]; then
        models_json=$(curl -s -k --max-time 10 -H "$auth_header" "$base_url/api/v1/models" 2>/dev/null)
    else
        models_json=$(curl -s -k --max-time 10 "$base_url/api/v1/models" 2>/dev/null)
    fi

    # Extract model IDs using jq (if available) or grep/sed fallback
    if command -v jq >/dev/null 2>&1; then
        echo "$models_json" | jq -r '.data[]?.id // empty' 2>/dev/null | head -10
    else
        # Fallback without jq
        echo "$models_json" | grep -o '"id":"[^"]*"' | sed 's/"id":"//' | sed 's/"//' | head -10
    fi
}

# Function to configure OpenAPI documentation routes
configure_openapi_routes() {
    echo "Configuring OpenAPI documentation routes..."

    # Create FastAPI docs routes
    create_fastapi_docs_routes

    # Verify the routes are accessible
    verify_docs_accessibility

    echo "✅ OpenAPI routes configuration completed"
    return 0
}

# Function to create OpenAPI provider routes (improved for local APIs)
create_openapi_provider_routes() {
    local provider_id="$1"
    local provider_name="$2"
    local base_url="$3"
    local auth_type="$4"
    local auth_token="$5"
    local provider_num="$6"

    echo "🔧 Creating OpenAPI routes for: $provider_name"
    log_debug "Base URL: $base_url"
    log_debug "Auth Type: $auth_type"

    # Fetch available models from the provider
    local available_models
    available_models=$(fetch_openapi_provider_models "$base_url" "$auth_type" "$auth_token")

    if [ -n "$available_models" ]; then
        log_debug "Available models: $(echo "$available_models" | tr '\n' ' ')"
        # Store the first model as default for route creation
        local default_model=$(echo "$available_models" | head -1)
        if [ -n "$default_model" ]; then
            log_debug "Using default model: $default_model"
        fi
    else
        echo "   ⚠️  Could not fetch models, will create generic routes"
        local default_model=""
    fi

    # Load APISIX configuration
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not set"
        return 1
    fi
    local admin_key="$APISIX_ADMIN_KEY"
    local apisix_admin_url="http://localhost:9180"

    # Parse base URL to extract host and port
    local scheme=$(echo "$base_url" | grep -o '^https\?')
    local host_port=$(echo "$base_url" | sed -E 's|^https?://||' | sed -E 's|/.*||')
    local default_port="443"
    if [ "$scheme" = "http" ]; then
        default_port="80"
    fi

    # Add default port if not specified
    if [[ "$host_port" != *":"* ]]; then
        host_port="${host_port}:${default_port}"
    fi

    # For Docker containers, convert localhost to custom OpenAPI container name or bridge IP
    # This allows APISIX running in Docker to access services on the host machine or other Docker stacks
    if [[ "$host_port" == "localhost:"* ]]; then
        # Check if this is a GSAi provider and containers are on the same network
        if [[ "$provider_id" == *"gsai"* ]] && docker network inspect vutf-network 2>/dev/null | grep -q "ai-gov-api-app-1"; then
            # Use GSAi app container name for direct network access (HTTP on port 8080)
            host_port="ai-gov-api-app-1:8080"
            echo "   🔄 Converting localhost to ai-gov-api-app-1:8080 for direct Docker network access"
        elif docker network inspect vutf-network 2>/dev/null | grep -q "apisix-apisix-1"; then
            # Check for other custom API containers on vutf-network
            local custom_container=$(docker network inspect vutf-network 2>/dev/null | jq -r '.[] | .Containers | to_entries[] | select(.value.Name | contains("app") or contains("api")) | .value.Name' | head -1)
            if [ -n "$custom_container" ] && [ "$custom_container" != "null" ]; then
                local custom_port=$(echo "$host_port" | cut -d':' -f2)
                # For GSAi, always use port 8080 internally
                if [[ "$custom_container" == *"ai-gov-api"* ]]; then
                    host_port="${custom_container}:8080"
                else
                    host_port="${custom_container}:${custom_port}"
                fi
                echo "   🔄 Converting localhost to ${host_port} for direct Docker network access"
            else
                # Get Docker bridge gateway IP - fallback for other services
                local bridge_ip=$(docker network inspect vutf-network 2>/dev/null | jq -r '.[0].IPAM.Config[0].Gateway' 2>/dev/null || echo "172.18.0.1")
                host_port=$(echo "$host_port" | sed "s/^localhost:/${bridge_ip}:/")
                echo "   🔄 Converting localhost to ${bridge_ip} for Docker-to-host access"
            fi
        else
            # Get Docker bridge gateway IP - fallback for other services
            local bridge_ip=$(docker network inspect vutf-network 2>/dev/null | jq -r '.[0].IPAM.Config[0].Gateway' 2>/dev/null || echo "172.18.0.1")
            host_port=$(echo "$host_port" | sed "s/^localhost:/${bridge_ip}:/")
            echo "   🔄 Converting localhost to ${bridge_ip} for Docker-to-host access"
        fi
    fi

    # Calculate unique route IDs
    local chat_route_id=$((9000 + provider_num))
    local models_route_id=$((9100 + provider_num))


    # Clean up any existing routes for this provider
    for route_id in $chat_route_id $models_route_id; do
        curl -s -X DELETE "${apisix_admin_url}/apisix/admin/routes/${route_id}" \
            -H "X-API-KEY: ${admin_key}" >/dev/null 2>&1
    done

    # Build authentication headers based on type
    local auth_headers="{}"
    case "$auth_type" in
        "bearer")
            auth_headers=$(jq -n --arg token "$auth_token" '{
                "Authorization": ("Bearer " + $token)
            }')
            ;;
        "api_key")
            auth_headers=$(jq -n --arg token "$auth_token" '{
                "X-API-Key": $token
            }')
            ;;
        "basic")
            auth_headers=$(jq -n --arg token "$auth_token" '{
                "Authorization": ("Basic " + $token)
            }')
            ;;
        *)
            echo "⚠️  Unknown auth type: $auth_type, using bearer as fallback"
            auth_headers=$(jq -n --arg token "$auth_token" '{
                "Authorization": ("Bearer " + $token)
            }')
            ;;
    esac

    # Determine SSL configuration - GSAi uses HTTP, others may use HTTPS
    local ssl_verify="false"
    if [[ "$scheme" == "https" ]] && [[ "$base_url" == "https://localhost"* ]] && [[ "$provider_id" != *"gsai"* ]]; then
        # For local HTTPS providers (excluding GSAi), enable SSL verification
        ssl_verify="true"
    elif [[ "$provider_id" == *"gsai"* ]]; then
        # GSAi uses HTTP, ensure scheme is set correctly
        scheme="http"
        ssl_verify="false"
    fi

    # Create chat completions route - use ai-proxy for GSAi, proxy-rewrite for others
    if [[ "$provider_id" == *"gsai"* ]]; then
        # Use ai-proxy plugin for GSAi following OpenAI/Anthropic pattern
        local auth_token="$auth_token"

        local chat_route_json=$(jq -n \
          --arg route_id "$chat_route_id" \
          --arg provider_id "$provider_id" \
          --arg scheme "$scheme" \
          --arg host_port "$host_port" \
          --arg auth_token "$auth_token" \
          '{
            "id": $route_id,
            "uri": ("/ai/" + $provider_id + "/chat/completions"),
            "name": ($provider_id + "-chat-completions"),
            "methods": ["POST"],
            "plugins": {
              "ai-proxy": {
                "provider": "openai-compatible",
                "auth": {
                  "header": {
                    "Authorization": ("Bearer " + $auth_token)
                  }
                },
                "override": {
                  "endpoint": ($scheme + "://" + $host_port + "/api/v1/chat/completions")
                },
                "timeout": 30000,
                "keepalive": true,
                "keepalive_pool": 30,
                "ssl_verify": false
              },
              "cors": {
                "allow_origins": "http://localhost:8501,http://localhost:3000",
                "allow_methods": "GET,POST,OPTIONS",
                "allow_headers": "Authorization,Content-Type,X-Requested-With,apikey",
                "allow_credential": true,
                "max_age": 3600
              }
            }
          }')
    elif [[ "$ssl_verify" == "true" ]]; then
        # Use proxy-rewrite for other providers with SSL
        local chat_route_json=$(jq -n \
          --arg route_id "$chat_route_id" \
          --arg provider_id "$provider_id" \
          --arg scheme "$scheme" \
          --arg host_port "$host_port" \
          --argjson auth_headers "$auth_headers" \
          '{
            "id": $route_id,
            "uri": ("/ai/" + $provider_id + "/chat/completions"),
            "name": ($provider_id + "-chat-completions"),
            "methods": ["POST"],
            "upstream": {
              "type": "roundrobin",
              "scheme": $scheme,
              "nodes": {
                ($host_port): 1
              },
              "pass_host": "rewrite",
              "upstream_host": "localhost",
              "tls": {
                "verify": true
              }
            },
            "plugins": {
              "proxy-rewrite": {
                "uri": "/api/v1/chat/completions",
                "headers": {
                  "set": ($auth_headers + {"Host": "localhost"})
                },
                "use_real_request_uri_unsafe": false
              },
              "cors": {
                "allow_origins": "http://localhost:8501,http://localhost:3000",
                "allow_methods": "GET,POST,OPTIONS",
                "allow_headers": "Authorization,Content-Type,X-Requested-With,apikey",
                "allow_credential": true,
                "max_age": 3600
              }
            }
          }')
    else
        # Use proxy-rewrite for other providers without SSL
        local chat_route_json=$(jq -n \
          --arg route_id "$chat_route_id" \
          --arg provider_id "$provider_id" \
          --arg scheme "$scheme" \
          --arg host_port "$host_port" \
          --argjson auth_headers "$auth_headers" \
          '{
            "id": $route_id,
            "uri": ("/ai/" + $provider_id + "/chat/completions"),
            "name": ($provider_id + "-chat-completions"),
            "methods": ["POST"],
            "upstream": {
              "type": "roundrobin",
              "scheme": $scheme,
              "nodes": {
                ($host_port): 1
              },
              "pass_host": "rewrite",
              "upstream_host": "localhost"
            },
            "plugins": {
              "proxy-rewrite": {
                "uri": "/api/v1/chat/completions",
                "headers": {
                  "set": ($auth_headers + {"Host": "localhost"})
                },
                "use_real_request_uri_unsafe": false
              },
              "cors": {
                "allow_origins": "http://localhost:8501,http://localhost:3000",
                "allow_methods": "GET,POST,OPTIONS",
                "allow_headers": "Authorization,Content-Type,X-Requested-With,apikey",
                "allow_credential": true,
                "max_age": 3600
              }
            }
          }')
    fi

    # Create chat completions route
    local chat_response=$(curl -s -X PUT "${apisix_admin_url}/apisix/admin/routes/${chat_route_id}" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$chat_route_json" 2>/dev/null || echo '{"error": "Failed"}')

    if ! echo "$chat_response" | grep -q "\"id\":\"$chat_route_id\""; then
        echo "❌ Failed to create chat completions route for $provider_name"
        echo "   Debug - Route ID: $chat_route_id"
        echo "   Debug - Response: $(echo "$chat_response" | head -c 200)..."
        echo "   Debug - Host Port: $host_port"
        return 1
    fi

    # Create models route - use proxy-rewrite for all providers (ai-proxy has issues with GET)
    if [[ "$provider_id" == *"gsai"* ]]; then
        # GSAi models route with proxy-rewrite (hardcoded auth works better for GET)
        local models_route_json=$(jq -n \
          --arg route_id "$models_route_id" \
          --arg provider_id "$provider_id" \
          --arg scheme "$scheme" \
          --arg host_port "$host_port" \
          --arg auth_token "$auth_token" \
          '{
            "id": $route_id,
            "uri": ("/ai/" + $provider_id + "/models"),
            "name": ($provider_id + "-models"),
            "methods": ["GET"],
            "upstream": {
              "type": "roundrobin",
              "scheme": $scheme,
              "nodes": {
                ($host_port): 1
              },
              "pass_host": "rewrite",
              "upstream_host": "localhost",
              "timeout": {
                "connect": 60,
                "send": 60,
                "read": 60
              }
            },
            "plugins": {
              "proxy-rewrite": {
                "uri": "/api/v1/models",
                "headers": {
                  "set": {
                    "Host": "localhost",
                    "Authorization": ("Bearer " + $auth_token)
                  }
                },
                "use_real_request_uri_unsafe": false
              },
              "cors": {
                "allow_origins": "http://localhost:8501,http://localhost:3000",
                "allow_methods": "GET,POST,OPTIONS",
                "allow_headers": "Authorization,Content-Type,X-Requested-With,apikey",
                "allow_credential": true,
                "max_age": 3600
              }
            }
          }')
    elif [[ "$ssl_verify" == "true" ]]; then
        local models_route_json=$(jq -n \
          --arg route_id "$models_route_id" \
          --arg provider_id "$provider_id" \
          --arg scheme "$scheme" \
          --arg host_port "$host_port" \
          --argjson auth_headers "$auth_headers" \
          '{
            "id": $route_id,
            "uri": ("/ai/" + $provider_id + "/models"),
            "name": ($provider_id + "-models"),
            "methods": ["GET"],
            "upstream": {
              "type": "roundrobin",
              "scheme": $scheme,
              "nodes": {
                ($host_port): 1
              },
              "pass_host": "rewrite",
              "upstream_host": "localhost",
              "timeout": {
                "connect": 60,
                "send": 60,
                "read": 60
              },
              "tls": {
                "verify": true
              }
            },
            "plugins": {
              "proxy-rewrite": {
                "uri": "/api/v1/models",
                "headers": {
                  "set": ($auth_headers + {"Host": "localhost"})
                },
                "use_real_request_uri_unsafe": false
              },
              "cors": {
                "allow_origins": "http://localhost:8501,http://localhost:3000",
                "allow_methods": "GET,POST,OPTIONS",
                "allow_headers": "Authorization,Content-Type,X-Requested-With,apikey",
                "allow_credential": true,
                "max_age": 3600
              }
            }
          }')
    else
        local models_route_json=$(jq -n \
          --arg route_id "$models_route_id" \
          --arg provider_id "$provider_id" \
          --arg scheme "$scheme" \
          --arg host_port "$host_port" \
          --argjson auth_headers "$auth_headers" \
          '{
            "id": $route_id,
            "uri": ("/ai/" + $provider_id + "/models"),
            "name": ($provider_id + "-models"),
            "methods": ["GET"],
            "upstream": {
              "type": "roundrobin",
              "scheme": $scheme,
              "nodes": {
                ($host_port): 1
              },
              "pass_host": "rewrite",
              "upstream_host": "localhost",
              "timeout": {
                "connect": 60,
                "send": 60,
                "read": 60
              }
            },
            "plugins": {
              "proxy-rewrite": {
                "uri": "/api/v1/models",
                "headers": {
                  "set": ($auth_headers + {"Host": "localhost"})
                },
                "use_real_request_uri_unsafe": false
              },
              "cors": {
                "allow_origins": "http://localhost:8501,http://localhost:3000",
                "allow_methods": "GET,POST,OPTIONS",
                "allow_headers": "Authorization,Content-Type,X-Requested-With,apikey",
                "allow_credential": true,
                "max_age": 3600
              }
            }
          }')
    fi

    # Create models route
    local models_response=$(curl -s -X PUT "${apisix_admin_url}/apisix/admin/routes/${models_route_id}" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$models_route_json" 2>/dev/null || echo '{"error": "Failed"}')

    if ! echo "$models_response" | grep -q "\"id\":\"$models_route_id\""; then
        echo "⚠️  Warning: Failed to create models route for $provider_name (non-critical)"
        echo "Chat completions will still work"
    fi

    echo "✅ OpenAPI routes created successfully for $provider_name"
    log_debug "Chat: http://localhost:9080/ai/$provider_id/chat/completions"
    log_debug "Models: http://localhost:9080/ai/$provider_id/models"
    log_debug "Target: $base_url"

    return 0
}

# Function to setup OpenAPI provider routes (including GSAi)
setup_openapi_routes() {
    echo "Setting up OpenAPI provider routes..."

    # Wait for APISIX to be ready before creating routes
    echo "Ensuring APISIX is ready for OpenAPI route creation..."
    local retries=0
    local max_retries=10

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

    # Test APISIX readiness with a simple API call
    while [ $retries -lt $max_retries ]; do
        if curl -s --max-time 5 -H "X-API-KEY: $APISIX_ADMIN_KEY" "http://localhost:9180/apisix/admin/routes" >/dev/null 2>&1; then
            echo "✅ APISIX admin API is ready for route creation"
            break
        fi
        echo "⏳ Waiting for APISIX admin API (attempt $((retries + 1))/$max_retries)..."
        sleep 3
        retries=$((retries + 1))
    done

    if [ $retries -eq $max_retries ]; then
        echo "❌ APISIX admin API is not ready - cannot setup OpenAPI routes"
        return 1
    fi

    # Create local tmp directory if it doesn't exist
    mkdir -p "./tmp"
    local log_file="./tmp/violentutf_openapi_setup.log"
    echo "$(date): Starting OpenAPI setup" > "$log_file"

    # Load AI tokens to get OpenAPI configuration
    if [ -f "./ai-tokens.env" ]; then
        echo "Loading OpenAPI configuration from ai-tokens.env..."
        source "./ai-tokens.env"
    else
        echo "⚠️  ai-tokens.env not found - OpenAPI providers may not be configured"
    fi

    echo "Setting up OpenAPI provider routes..."
    echo "$(date): OPENAPI_ENABLED = '${OPENAPI_ENABLED:-<not set>}'" >> "$log_file"

    # Check if any OpenAPI providers are enabled
    local openapi_enabled=false

    # Check for OPENAPI_ENABLED (legacy)
    if [ "$OPENAPI_ENABLED" = "true" ]; then
        openapi_enabled=true
    fi

    # Check for specific OpenAPI providers (OPENAPI_1, OPENAPI_2, etc.)
    for i in {1..5}; do
        local enabled_var="OPENAPI_${i}_ENABLED"
        if [ "${!enabled_var}" = "true" ]; then
            openapi_enabled=true
            break
        fi
    done

    if [ "$openapi_enabled" != "true" ]; then
        echo "OpenAPI providers disabled. Skipping setup."
        echo "$(date): Skipping - No OpenAPI providers enabled" >> "$log_file"
        return 0
    fi

    # Always use localhost for host-based script execution
    local apisix_admin_url="http://localhost:9180"

    # Load APISIX admin key
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi
    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not set"
        return 1
    fi
    local admin_key="$APISIX_ADMIN_KEY"

    # Check APISIX readiness
    echo "$(date): Checking APISIX readiness..." >> "$log_file"
    if ! curl -s -H "X-API-KEY: $admin_key" "http://localhost:9180/apisix/admin/routes" > /dev/null 2>&1; then
        echo "❌ APISIX admin API is not ready - cannot setup OpenAPI routes"
        echo "$(date): APISIX readiness check failed" >> "$log_file"
        return 1
    fi
    echo "$(date): APISIX is ready" >> "$log_file"


    # Process each OpenAPI provider (up to 10)
    local setup_count=0
    local error_count=0

    for i in {1..10}; do
        local enabled_var="OPENAPI_${i}_ENABLED"
        local id_var="OPENAPI_${i}_ID"
        local name_var="OPENAPI_${i}_NAME"
        local base_url_var="OPENAPI_${i}_BASE_URL"
        local spec_path_var="OPENAPI_${i}_SPEC_PATH"
        local auth_type_var="OPENAPI_${i}_AUTH_TYPE"
        local auth_token_var="OPENAPI_${i}_AUTH_TOKEN"

        # Check if this provider is enabled
        if [ "${!enabled_var}" != "true" ]; then
            continue
        fi

        local provider_id="${!id_var}"
        local provider_name="${!name_var}"
        local base_url="${!base_url_var}"
        local spec_path="${!spec_path_var}"
        local auth_type="${!auth_type_var}"
        local auth_token="${!auth_token_var}"

        if [ -z "$provider_id" ] || [ -z "$base_url" ]; then
            echo "⚠️  Skipping OpenAPI provider $i - missing required configuration"
            continue
        fi

        echo "Setting up OpenAPI provider: $provider_name ($provider_id)"
        echo "$(date): Processing provider $i: $provider_id" >> "$log_file"

        # Optional: Verify provider health before creating routes
        if verify_openapi_provider_health "$provider_id" "$provider_name" "$base_url" "$auth_type" "$auth_token"; then
            echo "$(date): Provider $provider_id health check passed" >> "$log_file"
        else
            echo "$(date): Provider $provider_id health check failed (proceeding anyway)" >> "$log_file"
            echo "⚠️  Warning: Provider $provider_name may not be accessible, but creating routes anyway"
        fi

        # Create routes for OpenAPI provider (works with any OpenAPI-compliant API)
        if create_openapi_provider_routes "$provider_id" "$provider_name" "$base_url" "$auth_type" "$auth_token" "$i"; then
            setup_count=$((setup_count + 1))
            echo "✅ Created routes for OpenAPI provider: $provider_name"
        else
            error_count=$((error_count + 1))
            echo "❌ Failed to create routes for OpenAPI provider: $provider_name"
        fi
    done

    echo "$(date): Setup complete. Success: $setup_count, Errors: $error_count" >> "$log_file"

    if [ $setup_count -gt 0 ]; then
        echo "✅ Successfully set up $setup_count OpenAPI provider route(s)"

        # Create a generic OpenAPI discovery route
        create_openapi_discovery_route

        return 0
    elif [ $error_count -gt 0 ]; then
        echo "❌ Failed to set up any OpenAPI provider routes"
        return 1
    else
        echo "ℹ️  No OpenAPI providers configured"
        return 0
    fi
}

# Function to create OpenAPI discovery route
create_openapi_discovery_route() {
    echo "Creating OpenAPI discovery route..."

    local route_id="3099"  # Special ID for discovery route

    cat > /tmp/openapi-discovery-route.json <<EOF
{
    "id": "$route_id",
    "uri": "/api/openapi/discover",
    "name": "openapi-discovery",
    "methods": ["GET", "POST"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "violentutf_api:8000": 1
        }
    },
    "plugins": {
        "proxy-rewrite": {
            "uri": "/api/openapi/discover"
        },
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,POST,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With",
            "allow_credential": true,
            "max_age": 3600
        }
    },
    "priority": 100
}
EOF

    local response=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d @/tmp/openapi-discovery-route.json \
        "http://localhost:9180/apisix/admin/routes/${route_id}")

    rm -f /tmp/openapi-discovery-route.json

    if [ "$response" = "200" ] || [ "$response" = "201" ]; then
        echo "✅ Created OpenAPI discovery route"
        return 0
    else
        echo "❌ Failed to create discovery route. HTTP status: $response"
        return 1
    fi
}

# Function to create FastAPI docs routes
create_fastapi_docs_routes() {
    echo "Creating FastAPI documentation routes..."

    # Load APISIX configuration
    if [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not set"
        return 1
    fi
    local admin_key="$APISIX_ADMIN_KEY"
    local apisix_admin_url="http://localhost:9180"

    # Create /api/docs route
    cat > /tmp/fastapi-docs-route.json <<EOF
{
    "uri": "/api/docs",
    "name": "violentutf-docs",
    "methods": ["GET"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "violentutf_api:8000": 1
        }
    },
    "plugins": {
        "proxy-rewrite": {
            "uri": "/docs"
        },
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With",
            "max_age": 3600,
            "allow_credential": true
        }
    }
}
EOF

    # Create docs route
    local response=$(curl -s -w "\n%{http_code}" -X PUT "${apisix_admin_url}/apisix/admin/routes/violentutf-docs" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d @/tmp/fastapi-docs-route.json)

    local status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        echo "✅ FastAPI docs route created successfully."
    else
        echo "⚠️  Warning: Failed to create FastAPI docs route. Status: $status_code"
    fi

    # Create /api/redoc route
    cat > /tmp/fastapi-redoc-route.json <<EOF
{
    "uri": "/api/redoc",
    "name": "violentutf-redoc",
    "methods": ["GET"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "violentutf_api:8000": 1
        }
    },
    "plugins": {
        "proxy-rewrite": {
            "uri": "/redoc"
        },
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With",
            "max_age": 3600,
            "allow_credential": true
        }
    }
}
EOF

    # Create redoc route
    local response=$(curl -s -w "\n%{http_code}" -X PUT "${apisix_admin_url}/apisix/admin/routes/violentutf-redoc" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d @/tmp/fastapi-redoc-route.json)

    local status_code=$(echo "$response" | tail -n1)
    if [ "$status_code" = "200" ] || [ "$status_code" = "201" ]; then
        echo "✅ FastAPI redoc route created successfully."
    else
        echo "⚠️  Warning: Failed to create FastAPI redoc route. Status: $status_code"
    fi

    # Clean up temp files
    rm -f /tmp/fastapi-docs-route.json /tmp/fastapi-redoc-route.json

    echo "FastAPI documentation routes configured."
}

# Function to verify OpenAPI provider endpoint health
verify_openapi_provider_health() {
    local provider_id="$1"
    local provider_name="$2"
    local base_url="$3"
    local auth_type="$4"
    local auth_token="$5"

    echo "🔍 Verifying health of OpenAPI provider: $provider_name"

    # Build auth headers for curl
    local auth_header=""
    case "$auth_type" in
        "bearer")
            auth_header="Authorization: Bearer $auth_token"
            ;;
        "api_key")
            auth_header="X-API-Key: $auth_token"
            ;;
        "basic")
            auth_header="Authorization: Basic $auth_token"
            ;;
    esac

    local test_count=0
    local passed_count=0

    # Test models endpoint
    echo "   Testing models endpoint: $base_url/api/v1/models"
    if [ -n "$auth_header" ]; then
        if curl -s -k --max-time 10 -H "$auth_header" "$base_url/api/v1/models" >/dev/null 2>&1; then
            echo "   ✅ Models endpoint is accessible"
            passed_count=$((passed_count + 1))
        else
            echo "   ❌ Models endpoint is not accessible"
        fi
    else
        if curl -s -k --max-time 10 "$base_url/api/v1/models" >/dev/null 2>&1; then
            echo "   ✅ Models endpoint is accessible"
            passed_count=$((passed_count + 1))
        else
            echo "   ❌ Models endpoint is not accessible"
        fi
    fi
    test_count=$((test_count + 1))

    # Test docs endpoint (optional)
    echo "   Testing docs endpoint: $base_url/docs"
    if [ -n "$auth_header" ]; then
        if curl -s -k --max-time 10 -H "$auth_header" "$base_url/docs" >/dev/null 2>&1; then
            echo "   ✅ Docs endpoint is accessible"
            passed_count=$((passed_count + 1))
        else
            echo "   ⚠️  Docs endpoint is not accessible (optional)"
        fi
    else
        if curl -s -k --max-time 10 "$base_url/docs" >/dev/null 2>&1; then
            echo "   ✅ Docs endpoint is accessible"
            passed_count=$((passed_count + 1))
        else
            echo "   ⚠️  Docs endpoint is not accessible (optional)"
        fi
    fi
    test_count=$((test_count + 1))

    echo "   📊 Health check: $passed_count/$test_count endpoints accessible"

    # Return success if at least models endpoint works
    if [ $passed_count -gt 0 ]; then
        return 0
    else
        echo "   ❌ Provider $provider_name appears to be unavailable"
        return 1
    fi
}

# Function to verify documentation accessibility
verify_docs_accessibility() {
    echo "Verifying documentation accessibility..."

    local test_count=0
    local passed_count=0

    # Test docs endpoint
    if curl -s http://localhost:9080/api/docs >/dev/null 2>&1; then
        echo "✅ FastAPI docs endpoint is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ FastAPI docs endpoint is not accessible"
    fi
    test_count=$((test_count + 1))

    # Test redoc endpoint
    if curl -s http://localhost:9080/api/redoc >/dev/null 2>&1; then
        echo "✅ FastAPI redoc endpoint is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ FastAPI redoc endpoint is not accessible"
    fi
    test_count=$((test_count + 1))

    # Test OpenAPI JSON endpoint
    if curl -s http://localhost:9080/api/openapi.json >/dev/null 2>&1; then
        echo "✅ OpenAPI JSON endpoint is accessible"
        passed_count=$((passed_count + 1))
    else
        echo "❌ OpenAPI JSON endpoint is not accessible"
    fi
    test_count=$((test_count + 1))

    echo "📊 Documentation accessibility: $passed_count/$test_count endpoints accessible"

    if [ $passed_count -eq $test_count ]; then
        return 0
    else
        return 1
    fi
}
