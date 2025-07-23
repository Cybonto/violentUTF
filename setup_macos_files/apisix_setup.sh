#!/usr/bin/env bash
# apisix_setup.sh - APISIX gateway configuration and route setup

# Function to integrate Custom OpenAPI SSL certificates with APISIX
# Note: This function is deprecated since GSAi now uses HTTP instead of HTTPS
integrate_custom_openapi_certificates() {
    echo "🔐 Integrating Custom OpenAPI SSL certificates with APISIX..."
    echo "   ⚠️  Note: GSAi now uses HTTP, certificate integration may not be needed"
    
    # Look for related containers that might have certificates
    local cert_containers=()
    
    # Check for ai-gov-api stack (GSAi)
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

# Enhanced function to wait for APISIX with actual response verification
wait_for_apisix_ready_enhanced() {
    log_detail "Waiting for APISIX to be ready with enhanced verification..."
    
    local max_attempts=30
    local attempt=1
    local admin_url="http://localhost:9180"
    local gateway_url="http://localhost:9080"
    
    # First wait for container to be running
    log_debug "Checking APISIX container status..."
    attempt=1
    while [ $attempt -le 10 ]; do
        if docker ps | grep -q "apisix-apisix-1"; then
            log_debug "APISIX container is running"
            break
        fi
        log_debug "Waiting for APISIX container... (attempt $attempt/10)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt 10 ]; then
        log_error "APISIX container not running after 20 seconds"
        return 1
    fi
    
    # Wait for admin port with actual response check
    log_detail "Testing APISIX admin port connectivity..."
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        # Test with a real HTTP response check
        local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$admin_url" 2>/dev/null || echo "000")
        if [ "$response" != "000" ]; then
            log_success "APISIX admin port is responding (HTTP $response)"
            break
        fi
        log_debug "Waiting for APISIX admin port... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        log_error "APISIX admin port not responding after $max_attempts attempts"
        return 1
    fi
    
    # Load admin key
    local apisix_env_file="${SETUP_MODULES_DIR}/../apisix/.env"
    if [ -f "$apisix_env_file" ]; then
        source "$apisix_env_file"
    elif [ -f "apisix/.env" ]; then
        source "apisix/.env"
    fi
    
    if [ -z "$APISIX_ADMIN_KEY" ]; then
        log_error "APISIX_ADMIN_KEY not found in apisix/.env"
        return 1
    fi
    
    # Test admin API with actual route listing
    log_detail "Testing APISIX admin API with authentication..."
    attempt=1
    while [ $attempt -le 15 ]; do
        local api_response=$(curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" "$admin_url/apisix/admin/routes" 2>/dev/null || echo '{"error":"failed"}')
        
        # Check if we got a valid JSON response
        if echo "$api_response" | jq -e '.list' >/dev/null 2>&1 || echo "$api_response" | jq -e '.total' >/dev/null 2>&1; then
            log_success "APISIX admin API is ready and returning valid responses"
            
            # Final check: test gateway port
            local gateway_response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$gateway_url" 2>/dev/null || echo "000")
            if [ "$gateway_response" != "000" ]; then
                log_success "APISIX gateway port is also responding (HTTP $gateway_response)"
                return 0
            else
                log_warn "APISIX gateway port not yet responding, but admin API is ready"
                return 0  # Admin API ready is sufficient
            fi
        fi
        
        log_debug "Waiting for APISIX admin API... (attempt $attempt/15)"
        sleep 3
        attempt=$((attempt + 1))
    done
    
    log_error "APISIX admin API not returning valid responses after 45 seconds"
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
    
    # Create consumer configuration for violentutf-api (used by the application)
    local consumer_config='{
        "username": "violentutf-api",
        "plugins": {
            "key-auth": {
                "key": "'$api_key'"
            }
        }
    }'
    
    local response=$(curl -s -w "%{http_code}" -X PUT "$admin_url/apisix/admin/consumers/violentutf-api" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        -H "Content-Type: application/json" \
        -d "$consumer_config" -o /dev/null)
    
    if [ "$response" = "200" ] || [ "$response" = "201" ]; then
        echo "✅ API key consumer 'violentutf-api' registered successfully"
    else
        echo "⚠️  API key consumer registration returned status: $response (may already exist)"
    fi
    
    # Also create violentutf-user for backward compatibility
    consumer_config='{
        "username": "violentutf-user",
        "plugins": {
            "key-auth": {
                "key": "'$api_key'"
            }
        }
    }'
    
    response=$(curl -s -w "%{http_code}" -X PUT "$admin_url/apisix/admin/consumers/violentutf-user" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        -H "Content-Type: application/json" \
        -d "$consumer_config" -o /dev/null)
    
    if [ "$response" = "200" ] || [ "$response" = "201" ]; then
        echo "✅ API key consumer 'violentutf-user' registered successfully"
        return 0
    else
        echo "⚠️  API key consumer registration returned status: $response (may already exist)"
        return 0
    fi
}

# Function to create startup wrapper for APISIX
create_apisix_startup_wrapper() {
    log_detail "Creating APISIX startup wrapper..."
    
    cat > startup-wrapper.sh << 'EOF'
#!/bin/sh
# APISIX startup wrapper to handle socket cleanup
# This ensures cleanup happens even when container is restarted

echo "🧹 Cleaning up stale socket files..."
rm -f /usr/local/apisix/logs/worker_events.sock 2>/dev/null || true
rm -f /usr/local/apisix/logs/nginx.pid 2>/dev/null || true

echo "🚀 Starting APISIX..."
exec apisix start
EOF
    
    chmod +x startup-wrapper.sh
    log_success "Created startup-wrapper.sh with executable permissions"
}

# Function to create docker-compose override for APISIX
create_apisix_compose_override() {
    log_detail "Creating docker-compose.override.yml for APISIX..."
    
    # Load APISIX admin key if available
    local admin_key="edd1c9f034335f136f87ad84b625c8f1"
    if [ -f ".env" ]; then
        source .env
        admin_key="${APISIX_ADMIN_KEY:-$admin_key}"
    fi
    
    cat > docker-compose.override.yml << EOF
version: '3.8'

services:
  apisix:
    # Use a wrapper script to ensure cleanup always happens
    volumes:
      - ./startup-wrapper.sh:/startup-wrapper.sh:ro
    entrypoint: ["/bin/sh", "/startup-wrapper.sh"]
    
    # Add health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9180/apisix/admin/routes", "-H", "X-API-KEY: \${APISIX_ADMIN_KEY:-$admin_key}"]
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 30s
    
    # Add init flag to handle PID 1 issues
    init: true
    
    # Ensure clean shutdown
    stop_grace_period: 30s
    
    # Additional environment variables for better behavior
    environment:
      - APISIX_STAND_ALONE=false
      - APISIX_ENABLE_HEARTBEAT=true
EOF
    
    log_success "Created docker-compose.override.yml with health checks"
}

# Function to check and handle stuck APISIX processes
check_and_cleanup_stuck_apisix() {
    log_detail "Checking for stuck APISIX processes..."
    
    # Check if APISIX container exists but is not responding
    if docker ps -a | grep -q "apisix-apisix-1"; then
        # Check if container is running
        if docker ps | grep -q "apisix-apisix-1"; then
            # Test if APISIX is actually responding
            if ! curl -s --max-time 5 http://localhost:9180 >/dev/null 2>&1; then
                log_warn "APISIX container is running but not responding"
                log_detail "Attempting to restart APISIX container..."
                
                # Stop the container forcefully
                docker stop -t 10 apisix-apisix-1 2>/dev/null || true
                docker rm -f apisix-apisix-1 2>/dev/null || true
                
                # Also check for other APISIX-related containers
                docker ps -a | grep "apisix" | awk '{print $1}' | xargs -r docker rm -f 2>/dev/null || true
                
                log_success "Cleaned up stuck APISIX containers"
                return 0
            fi
        else
            # Container exists but is not running - remove it
            log_detail "Removing stopped APISIX container..."
            docker rm -f apisix-apisix-1 2>/dev/null || true
        fi
    fi
    
    return 0
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
    
    # Debug: Show current directory and list config files
    echo "Current directory: $(pwd)"
    echo "Checking for required configuration files..."
    ls -la conf/ 2>/dev/null || echo "conf/ directory not found"
    
    # Critical: Check if config.yaml or dashboard.yaml were mistakenly created as directories
    if [ -d "conf/config.yaml" ]; then
        echo "❌ ERROR: config.yaml exists as a directory instead of a file!"
        echo "Removing incorrect directory structure..."
        rm -rf "conf/config.yaml"
    fi
    
    if [ -d "conf/dashboard.yaml" ]; then
        echo "❌ ERROR: dashboard.yaml exists as a directory instead of a file!"
        echo "Removing incorrect directory structure..."
        rm -rf "conf/dashboard.yaml"
    fi
    
    if [ -d "conf/prometheus.yml" ]; then
        echo "❌ ERROR: prometheus.yml exists as a directory instead of a file!"
        echo "Removing incorrect directory structure..."
        rm -rf "conf/prometheus.yml"
    fi
    
    # Ensure .env file exists
    if [ ! -f ".env" ]; then
        echo "❌ APISIX .env file missing!"
        cd "$original_dir"
        return 1
    fi
    
    # Ensure config.yaml exists before starting Docker
    if [ ! -f "conf/config.yaml" ]; then
        echo "⚠️  APISIX config.yaml missing!"
        echo "This file should have been created during environment setup."
        echo "Checking for template file..."
        
        if [ -f "conf/config.yaml.template" ]; then
            echo "Found template, attempting to create config.yaml..."
            
            # Source necessary functions if not already available
            if ! command -v prepare_config_from_template &> /dev/null; then
                local setup_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
                if [ -f "$setup_dir/utils.sh" ]; then
                    source "$setup_dir/utils.sh"
                fi
            fi
            
            # Try to create config.yaml from template
            if command -v prepare_config_from_template &> /dev/null; then
                prepare_config_from_template "conf/config.yaml.template"
                
                # Replace placeholders with values from .env if available
                if [ -f ".env" ]; then
                    source .env
                    
                    # Generate missing values if needed
                    [ -z "$APISIX_ADMIN_KEY" ] && APISIX_ADMIN_KEY=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
                    [ -z "$APISIX_KEYRING_VALUE_1" ] && APISIX_KEYRING_VALUE_1=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
                    [ -z "$APISIX_KEYRING_VALUE_2" ] && APISIX_KEYRING_VALUE_2=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
                    
                    # Replace placeholders
                    sed -i.bak "s/APISIX_ADMIN_KEY_PLACEHOLDER/$APISIX_ADMIN_KEY/g" conf/config.yaml
                    sed -i.bak "s/APISIX_KEYRING_VALUE_1_PLACEHOLDER/$APISIX_KEYRING_VALUE_1/g" conf/config.yaml
                    sed -i.bak "s/APISIX_KEYRING_VALUE_2_PLACEHOLDER/$APISIX_KEYRING_VALUE_2/g" conf/config.yaml
                    rm -f conf/config.yaml.bak
                    
                    echo "✅ Successfully created config.yaml from template"
                else
                    echo "⚠️  Warning: .env file not found, using template as-is"
                    cp conf/config.yaml.template conf/config.yaml
                fi
            else
                # Fallback: simple copy
                echo "Using simple copy method..."
                cp conf/config.yaml.template conf/config.yaml
                echo "⚠️  Warning: config.yaml created but placeholders not replaced"
            fi
            
            # Verify the file was created
            if [ ! -f "conf/config.yaml" ]; then
                echo "❌ Failed to create config.yaml"
                cd "$original_dir"
                return 1
            fi
        else
            echo "❌ Template file conf/config.yaml.template is also missing!"
            echo "Cannot proceed without configuration files."
            cd "$original_dir"
            return 1
        fi
    fi
    
    # Verify other required config files
    if [ ! -f "conf/dashboard.yaml" ]; then
        echo "⚠️  Warning: dashboard.yaml missing"
        
        if [ -f "conf/dashboard.yaml.template" ]; then
            echo "Creating dashboard.yaml from template..."
            cp conf/dashboard.yaml.template conf/dashboard.yaml
            
            # Generate missing values if needed
            [ -z "$APISIX_DASHBOARD_SECRET" ] && APISIX_DASHBOARD_SECRET=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
            [ -z "$APISIX_DASHBOARD_PASSWORD" ] && APISIX_DASHBOARD_PASSWORD=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16)
            
            # Replace placeholders
            sed -i.bak "s/APISIX_DASHBOARD_SECRET_PLACEHOLDER/$APISIX_DASHBOARD_SECRET/g" conf/dashboard.yaml
            sed -i.bak "s/APISIX_DASHBOARD_PASSWORD_PLACEHOLDER/$APISIX_DASHBOARD_PASSWORD/g" conf/dashboard.yaml
            rm -f conf/dashboard.yaml.bak
            
            echo "✅ Created dashboard.yaml"
        fi
    fi
    
    # Create startup wrapper and override files
    create_apisix_startup_wrapper
    create_apisix_compose_override
    
    # Check and cleanup any stuck APISIX processes
    check_and_cleanup_stuck_apisix
    
    # Ensure network exists and is available
    echo "Ensuring Docker network is available for APISIX..."
    if ! docker network inspect "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
        echo "Creating shared network for APISIX..."
        docker network create "$SHARED_NETWORK_NAME"
    fi
    
    # Build images first with timeout handling
    echo "Building APISIX service images..."
    
    # Set build timeout environment variables
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    export BUILDKIT_PROGRESS=plain
    
    # Create pip config for FastAPI build to handle timeouts
    if [ -f "../violentutf_api/fastapi_app/Dockerfile" ]; then
        echo "Configuring pip for better timeout handling..."
        cat > ../violentutf_api/fastapi_app/pip.conf << 'EOF'
[global]
timeout = 600
retries = 10
index-url = https://pypi.org/simple
trusted-host = pypi.org pypi.python.org files.pythonhosted.org
EOF
    fi
    
    # Try to build with extended timeout
    echo "Building containers (this may take several minutes for first build)..."
    if ${DOCKER_COMPOSE_CMD:-docker-compose} build; then
        echo "✅ Container images built successfully"
    else
        echo "⚠️  Build failed, trying alternative approach..."
        
        # Alternative: Start without FastAPI first
        echo "Starting APISIX core services only..."
        if ${DOCKER_COMPOSE_CMD:-docker-compose} up -d apisix etcd prometheus grafana dashboard; then
            echo "✅ APISIX core services started"
            
            # Try to build FastAPI separately with more control
            echo "Building FastAPI service separately..."
            if ${DOCKER_COMPOSE_CMD:-docker-compose} build fastapi; then
                echo "✅ FastAPI built successfully"
                ${DOCKER_COMPOSE_CMD:-docker-compose} up -d fastapi
            else
                echo "⚠️  FastAPI build failed - will continue without it"
                echo "You can manually build it later with:"
                echo "  cd apisix && docker-compose build fastapi"
            fi
        else
            echo "❌ Failed to start APISIX core containers"
            cd "$original_dir"
            return 1
        fi
    fi
    
    # Start all containers
    echo "Starting APISIX containers..."
    if ${DOCKER_COMPOSE_CMD:-docker-compose} up -d; then
        echo "✅ APISIX containers started"
    else
        echo "❌ Failed to start APISIX containers"
        cd "$original_dir"
        return 1
    fi
    
    cd "$original_dir"
    
    # Note: Certificate integration disabled since GSAi now uses HTTP
    # integrate_custom_openapi_certificates
    
    # Wait for APISIX to be ready with enhanced verification
    if wait_for_apisix_ready_enhanced; then
        echo "✅ APISIX is ready and verified responsive"
        
        # Register API key consumer (critical for GSAi and other key-auth routes)
        register_api_key_consumer
        
        return 0
    else
        echo "❌ APISIX failed to become ready"
        
        # Try one recovery attempt
        log_warn "Attempting APISIX recovery..."
        docker restart apisix-apisix-1 2>/dev/null || true
        sleep 10
        
        if wait_for_apisix_ready_enhanced; then
            log_success "APISIX recovered after restart"
            register_api_key_consumer
            return 0
        else
            log_error "APISIX recovery failed"
            return 1
        fi
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