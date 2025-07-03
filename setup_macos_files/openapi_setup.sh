#!/usr/bin/env bash
# openapi_setup.sh - OpenAPI/Swagger documentation routes and configuration

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

# Function to setup OpenAPI provider routes
setup_openapi_routes() {
    # Create local tmp directory if it doesn't exist
    mkdir -p "./tmp"
    local log_file="./tmp/violentutf_openapi_setup.log"
    echo "$(date): Starting OpenAPI setup" > "$log_file"
    
    echo "Setting up OpenAPI provider routes..."
    echo "$(date): OPENAPI_ENABLED = '${OPENAPI_ENABLED:-<not set>}'" >> "$log_file"
    
    if [ "$OPENAPI_ENABLED" != "true" ]; then
        echo "OpenAPI providers disabled. Skipping setup."
        echo "$(date): Skipping - OPENAPI_ENABLED != 'true'" >> "$log_file"
        return 0
    fi
    
    # Ensure APISIX admin URL is set
    if [ -z "$APISIX_ADMIN_URL" ]; then
        APISIX_ADMIN_URL="http://localhost:9180"
        echo "⚠️  APISIX_ADMIN_URL not set, using default: $APISIX_ADMIN_URL"
    fi
    
    # Load APISIX admin key
    if [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi
    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not set"
        return 1
    fi
    local admin_key="$APISIX_ADMIN_KEY"
    
    # Check APISIX readiness
    echo "$(date): Checking APISIX readiness..." >> "$log_file"
    if ! curl -s -H "X-API-KEY: $admin_key" "$APISIX_ADMIN_URL/apisix/admin/routes" > /dev/null 2>&1; then
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
        
        # Create route for this OpenAPI provider
        if create_openapi_provider_route "$provider_id" "$base_url" "$auth_type" "$auth_token" "$i"; then
            setup_count=$((setup_count + 1))
            echo "✅ Created route for OpenAPI provider: $provider_id"
        else
            error_count=$((error_count + 1))
            echo "❌ Failed to create route for OpenAPI provider: $provider_id"
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

# Function to create route for individual OpenAPI provider
create_openapi_provider_route() {
    local provider_id="$1"
    local base_url="$2"
    local auth_type="$3"
    local auth_token="$4"
    local provider_num="$5"
    
    # Calculate unique route ID (3000 + provider number)
    local route_id=$((3000 + provider_num))
    
    # Parse base URL to get host and port
    local host_port=$(echo "$base_url" | sed -E 's|https?://||' | sed -E 's|/.*||')
    
    # Build authentication plugin configuration
    local auth_plugin=""
    case "$auth_type" in
        "bearer")
            auth_plugin='"proxy-rewrite": {
                "headers": {
                    "set": {
                        "Authorization": "Bearer '"$auth_token"'"
                    }
                }
            },'
            ;;
        "api_key")
            auth_plugin='"proxy-rewrite": {
                "headers": {
                    "set": {
                        "X-API-Key": "'"$auth_token"'"
                    }
                }
            },'
            ;;
        "basic")
            # For basic auth, token should be base64(username:password)
            auth_plugin='"proxy-rewrite": {
                "headers": {
                    "set": {
                        "Authorization": "Basic '"$auth_token"'"
                    }
                }
            },'
            ;;
    esac
    
    # Create the route configuration
    cat > "/tmp/openapi-route-${provider_id}.json" <<EOF
{
    "id": "$route_id",
    "uri": "/openapi/${provider_id}/*",
    "name": "openapi-${provider_id}",
    "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "${host_port}": 1
        },
        "scheme": "https",
        "pass_host": "pass",
        "timeout": {
            "connect": 60,
            "send": 60,
            "read": 60
        }
    },
    "plugins": {
        $auth_plugin
        "proxy-rewrite": {
            "regex_uri": ["^/openapi/${provider_id}/(.*)", "/\$1"]
        },
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,POST,PUT,DELETE,PATCH,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With,X-API-Key",
            "allow_credential": true,
            "max_age": 3600
        }
    },
    "priority": 100
}
EOF
    
    # Create the route
    local response=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d @"/tmp/openapi-route-${provider_id}.json" \
        "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}")
    
    rm -f "/tmp/openapi-route-${provider_id}.json"
    
    if [ "$response" = "200" ] || [ "$response" = "201" ]; then
        return 0
    else
        echo "Failed to create route. HTTP status: $response"
        return 1
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
        "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}")
    
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