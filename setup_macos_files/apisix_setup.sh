#!/usr/bin/env bash
# apisix_setup.sh - APISIX gateway configuration and route setup

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
    
    # Wait for APISIX to be ready
    if wait_for_apisix_ready; then
        echo "✅ APISIX is ready"
        
        # Register API key consumer (critical for GSAi and other key-auth routes)
        register_api_key_consumer
        
        return 0
    else
        echo "❌ APISIX failed to become ready"
        return 1
    fi
}

# Function to configure APISIX routes
configure_apisix_routes() {
    echo "Configuring APISIX routes..."
    
    # Give APISIX extra time to fully initialize
    echo "Waiting additional time for APISIX to fully initialize..."
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
    if [ -f "apisix/.env" ]; then
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
# Critical for GSAi and other routes using key-auth plugin
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
        echo "   This enables X-API-Key authentication for GSAi and other routes"
        return 0
    else
        echo "❌ Failed to create API key consumer"
        echo "Response: $consumer_response" | jq . 2>/dev/null || echo "$consumer_response"
        return 1
    fi
}