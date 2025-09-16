#!/usr/bin/env bash
# apisix_setup.sh - APISIX gateway configuration and route setup

# Function to integrate Custom OpenAPI SSL certificates with APISIX
integrate_custom_openapi_certificates() {
    echo "🔐 Integrating Custom OpenAPI SSL certificates with APISIX..."

    # Look for related containers that might have certificates
    local cert_containers=()

    # Check for ai-gov-api stack
    if docker ps --format "table {{.Names}}" | grep -q "ai-gov-api-caddy"; then
        cert_containers+=("ai-gov-api-caddy-1")
    fi

    # Check for other custom API containers with 'caddy' in the name
    while IFS= read -r container; do
        if [[ "$container" != "ai-gov-api-caddy-1" ]]; then
            cert_containers+=("$container")
        fi
    done < <(docker ps --format "{{.Names}}" | grep -E "(caddy|ssl|cert)" || true)

    if [ ${#cert_containers[@]} -eq 0 ]; then
        echo "   No Custom OpenAPI certificate containers found"
        return 0
    fi

    local cert_container="${cert_containers[0]}"
    echo "   Found certificate container: $cert_container"

    # Extract certificates from the container
    echo "   Extracting SSL certificates from $cert_container..."

    # Common certificate paths for Caddy
    local cert_paths=(
        "/data/caddy/pki/authorities/local/root.crt"
        "/data/caddy/certificates/local/localhost/localhost.crt"
        "/data/caddy/pki/authorities/local/intermediate.crt"
    )

    local extracted_certs=()
    for cert_path in "${cert_paths[@]}"; do
        if docker exec "$cert_container" test -f "$cert_path" 2>/dev/null; then
            local cert_name=$(basename "$cert_path" .crt)
            local temp_cert="/tmp/custom-openapi-${cert_name}.crt"

            if docker cp "${cert_container}:${cert_path}" "$temp_cert" 2>/dev/null; then
                echo "   ✅ Extracted: $cert_path -> $temp_cert"
                extracted_certs+=("$temp_cert")
            else
                echo "   ⚠️  Failed to extract: $cert_path"
            fi
        fi
    done

    if [ ${#extracted_certs[@]} -eq 0 ]; then
        echo "   No certificates found in $cert_container"
        return 0
    fi

    # Wait for APISIX container to be running (but not necessarily ready)
    echo "   Waiting for APISIX container to be available..."
    local retry_count=0
    while ! docker ps --filter "name=apisix-apisix-1" --filter "status=running" --quiet | head -1 && [ $retry_count -lt 30 ]; do
        echo "   Waiting for APISIX container... (attempt $((retry_count + 1))/30)"
        sleep 2
        retry_count=$((retry_count + 1))
    done

    if [ $retry_count -eq 30 ]; then
        echo "   ❌ APISIX container not available for certificate installation"
        # Clean up temp files
        for cert_file in "${extracted_certs[@]}"; do
            rm -f "$cert_file"
        done
        return 1
    fi

    # Copy certificates to APISIX container BEFORE it fully starts
    echo "   Installing certificates in APISIX container..."
    local installed_count=0
    for cert_file in "${extracted_certs[@]}"; do
        local cert_basename=$(basename "$cert_file")

        if docker cp "$cert_file" "apisix-apisix-1:/usr/local/share/ca-certificates/$cert_basename" 2>/dev/null; then
            echo "   ✅ Installed: $cert_basename"
            installed_count=$((installed_count + 1))
        else
            echo "   ⚠️  Failed to install: $cert_basename"
        fi
    done

    if [ $installed_count -gt 0 ]; then
        echo "   Updating APISIX certificate store..."
        if docker exec --user root apisix-apisix-1 update-ca-certificates 2>/dev/null; then
            echo "   ✅ Certificate store updated successfully"
        else
            echo "   ⚠️  Failed to update certificate store (will retry after APISIX starts)"
        fi

        # Clean up temporary certificate files
        for cert_file in "${extracted_certs[@]}"; do
            rm -f "$cert_file"
        done

        return 0
    else
        echo "   ❌ No certificates were successfully installed"
        # Clean up temp files
        for cert_file in "${extracted_certs[@]}"; do
            rm -f "$cert_file"
        done
        return 1
    fi
}

# Function to wait for APISIX to be ready
wait_for_apisix_ready() {
    echo "Waiting for APISIX to be ready..."

    local max_attempts=30
    local attempt=1
    local admin_url="http://localhost:9180"

    # First wait for basic connectivity
    while [ $attempt -le $max_attempts ]; do
        if curl -s --max-time 5 "$admin_url" >/dev/null 2>&1; then
            echo "APISIX admin port is responding (attempt $attempt/$max_attempts)"
            break
        fi
        echo "Waiting for APISIX admin port... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    if [ $attempt -gt $max_attempts ]; then
        echo "❌ APISIX admin port not responding after $max_attempts attempts"
        return 1
    fi

    # Now wait for admin API with key
    echo "Testing APISIX admin API with authentication..."

    # Load admin key
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

    attempt=1
    while [ $attempt -le 15 ]; do
        if curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" "$admin_url/apisix/admin/routes" >/dev/null 2>&1; then
            echo "✅ APISIX admin API is ready and authenticated"
            return 0
        fi
        echo "Waiting for APISIX admin API... (attempt $attempt/15)"
        sleep 3
        attempt=$((attempt + 1))
    done

    echo "❌ APISIX admin API not ready after 45 seconds"
    return 1
}

# Function to register API key consumer
register_api_key_consumer() {
    echo "Registering API key consumer..."

    # Load admin key
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

    local admin_url="http://localhost:9180"
    local api_key="${VIOLENTUTF_API_KEY:-test-api-key}"

    # Create consumer configuration
    local consumer_config='{
        "username": "violentutf-user",
        "plugins": {
            "key-auth": {
                "key": "'$api_key'"
            }
        }
    }'

    local response=$(curl -s -w "%{http_code}" -X PUT "$admin_url/apisix/admin/consumers/violentutf-user" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        -H "Content-Type: application/json" \
        -d "$consumer_config" -o /dev/null)

    if [ "$response" = "200" ] || [ "$response" = "201" ]; then
        echo "✅ API key consumer registered successfully"
        return 0
    else
        echo "⚠️  API key consumer registration returned status: $response (may already exist)"
        return 0
    fi
}

# Function to setup APISIX
setup_apisix() {
    echo "Setting up APISIX gateway..."

    local original_dir=$(pwd)

    if [ ! -d "apisix" ]; then
        echo "❌ APISIX directory not found"
        return 1
    fi

    cd "apisix" || { echo "Failed to cd into apisix directory"; exit 1; }

    # Ensure .env file exists
    if [ ! -f ".env" ]; then
        echo "❌ APISIX .env file missing!"
        cd "$original_dir"
        return 1
    fi

    # Ensure network exists and is available
    echo "Ensuring Docker network is available for APISIX..."
    if ! docker network inspect "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
        echo "Creating shared network for APISIX..."
        docker network create "$SHARED_NETWORK_NAME"
    fi

    # Start APISIX containers
    echo "Starting APISIX containers..."
    if ${DOCKER_COMPOSE_CMD:-docker-compose} up -d; then
        echo "✅ APISIX containers started"
    else
        echo "❌ Failed to start APISIX containers"
        cd "$original_dir"
        return 1
    fi

    cd "$original_dir"

    # Integrate SSL certificates if needed for HTTPS providers
    if [[ "$FORCE_ZSCALER" == "true" ]]; then
        echo "   🔒 Zscaler mode: SSL certificate integration may be needed"
    fi
    # integrate_custom_openapi_certificates  # Uncomment if certificates are needed

    # Wait for APISIX to be ready
    if wait_for_apisix_ready; then
        echo "✅ APISIX is ready"

        # Register API key consumer (critical for key-auth routes)
        register_api_key_consumer

        return 0
    else
        echo "❌ APISIX failed to become ready"
        return 1
    fi
}

# Function to configure APISIX routes
configure_apisix_routes() {
    log_detail "Configuring APISIX routes..."

    # Give APISIX extra time to fully initialize
    log_debug "Waiting additional time for APISIX to fully initialize..."
    sleep 10

    # Ensure APISIX environment is loaded
    if [ -f "apisix/.env" ]; then
        source "apisix/.env"
        echo "Loaded APISIX environment variables"
    else
        echo "❌ APISIX .env file not found at apisix/.env"
        return 1
    fi

    # Verify admin key is available
    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not found in environment"
        echo "Please ensure APISIX_ADMIN_KEY is set in apisix/.env"
        return 1
    fi

    # Export the key so the script can use it
    export APISIX_ADMIN_KEY

    # Use the moved configure routes script
    if [ -f "$SETUP_MODULES_DIR/apisix_configure_routes.sh" ]; then
        echo "Running APISIX route configuration script..."
        cd "$(dirname "$SETUP_MODULES_DIR")" # Go to main directory

        # Copy the .env file to current directory for the script
        cp apisix/.env . 2>/dev/null || true

        bash "$SETUP_MODULES_DIR/apisix_configure_routes.sh"

        # Clean up the temporary .env file
        rm -f .env

        if [ $? -eq 0 ]; then
            echo "✅ APISIX routes configured successfully"
            return 0
        else
            echo "❌ APISIX route configuration failed"
            return 1
        fi
    else
        echo "❌ APISIX route configuration script not found at $SETUP_MODULES_DIR/apisix_configure_routes.sh"
        return 1
    fi
}

# Function to wait for APISIX to be ready
wait_for_apisix_ready() {
    echo "Waiting for APISIX to be ready..."

    local max_retries=30
    local retry_count=0
    local apisix_admin_url="http://localhost:9180"

    # Load APISIX admin key from .env
    if [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo "❌ ERROR: APISIX_ADMIN_KEY not set"
        return 1
    fi
    local admin_key="$APISIX_ADMIN_KEY"

    while [ $retry_count -lt $max_retries ]; do
        if curl -s -H "X-API-KEY: $admin_key" "$apisix_admin_url/apisix/admin/routes" >/dev/null 2>&1; then
            echo "✅ APISIX is ready and responding"
            return 0
        fi

        echo "Waiting for APISIX... (attempt $((retry_count + 1))/$max_retries)"
        sleep 5
        retry_count=$((retry_count + 1))
    done

    echo "❌ APISIX failed to become ready within timeout"
    return 1
}

# Function to verify APISIX configuration
verify_apisix_config() {
    echo "Verifying APISIX configuration..."

    # Load admin key
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

    # Check if APISIX admin API is accessible
    if curl -s -H "X-API-KEY: $admin_key" "$apisix_admin_url/apisix/admin/routes" >/dev/null 2>&1; then
        echo "✅ APISIX admin API is accessible"

        # Count configured routes
        local route_count=$(curl -s -H "X-API-KEY: $admin_key" "$apisix_admin_url/apisix/admin/routes" | jq '.list | length' 2>/dev/null || echo "0")
        echo "📊 Found $route_count configured routes"

        return 0
    else
        echo "❌ APISIX admin API is not accessible"
        return 1
    fi
}

# Function to register API key consumer
# Critical for routes using key-auth plugin
register_api_key_consumer() {
    echo "🔑 Registering API key consumer for APISIX..."

    # Load APISIX admin key
    if [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi

    # Load ViolentUTF API key
    local violentutf_api_key=""
    if [ -f "violentutf_api/fastapi_app/.env" ]; then
        source "violentutf_api/fastapi_app/.env"
        violentutf_api_key="$VIOLENTUTF_API_KEY"
    fi

    # Try to get from container if not found in env files
    if [ -z "$violentutf_api_key" ]; then
        violentutf_api_key=$(docker exec violentutf_api printenv VIOLENTUTF_API_KEY 2>/dev/null || echo "")
    fi

    if [ -z "$APISIX_ADMIN_KEY" ] || [ -z "$violentutf_api_key" ]; then
        echo "⚠️  Cannot register API key consumer - missing keys"
        echo "   APISIX_ADMIN_KEY: ${APISIX_ADMIN_KEY:+SET}"
        echo "   VIOLENTUTF_API_KEY: ${violentutf_api_key:+SET}"
        return 1
    fi

    local admin_key="$APISIX_ADMIN_KEY"
    local apisix_admin_url="http://localhost:9180"
    local consumer_name="violentutf_api_user"

    # Check if consumer already exists
    local consumer_check=$(curl -s "${apisix_admin_url}/apisix/admin/consumers/${consumer_name}" \
        -H "X-API-KEY: ${admin_key}" 2>/dev/null || echo '{"error": "not found"}')

    if echo "$consumer_check" | grep -q "\"username\":\"${consumer_name}\""; then
        echo "✅ API key consumer '${consumer_name}' already exists"
        return 0
    fi

    # Create consumer with API key using jq for proper JSON construction
    local consumer_config=$(jq -n \
      --arg api_key "${violentutf_api_key}" \
      --arg username "${consumer_name}" \
      '{
        "username": $username,
        "plugins": {
          "key-auth": {
            "key": $api_key
          }
        }
      }')

    # Register the consumer
    local consumer_response=$(curl -s -X PUT "${apisix_admin_url}/apisix/admin/consumers/${consumer_name}" \
        -H "X-API-KEY: ${admin_key}" \
        -H "Content-Type: application/json" \
        -d "$consumer_config" 2>/dev/null || echo '{"error": "Failed"}')

    if echo "$consumer_response" | grep -q "\"username\":\"${consumer_name}\""; then
        echo "✅ Created API key consumer '${consumer_name}' successfully"
        echo "   This enables X-API-Key authentication for API routes"
        return 0
    else
        echo "❌ Failed to create API key consumer"
        echo "Response: $consumer_response" | jq . 2>/dev/null || echo "$consumer_response"
        return 1
    fi
}
