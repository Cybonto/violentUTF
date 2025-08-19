#!/usr/bin/env bash
# apisix_setup.sh - APISIX gateway setup

# Main APISIX setup function
setup_apisix() {
    log_detail "Setting up APISIX API Gateway..."
    
    local APISIX_DIR="apisix"
    
    cd "$APISIX_DIR" || return 1
    
    # Start APISIX services
    log_detail "Starting APISIX services..."
    $DOCKER_COMPOSE_CMD up -d
    
    # Wait for APISIX to be ready
    log_detail "Waiting for APISIX to be ready..."
    local RETRY_COUNT=0
    local MAX_RETRIES=30
    local SUCCESS=false
    
    until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
        RETRY_COUNT=$((RETRY_COUNT+1))
        
        # Check APISIX gateway port
        if curl -s --max-time 5 http://localhost:9080/ >/dev/null 2>&1; then
            log_success "APISIX gateway is responding"
            SUCCESS=true
            break
        fi
        
        log_debug "APISIX not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES). Waiting 5 seconds..."
        sleep 5
    done
    
    if [ "$SUCCESS" = false ]; then
        echo "❌ APISIX did not become ready in time"
        $DOCKER_COMPOSE_CMD logs
        cd ..
        return 1
    fi
    
    cd ..
    echo "✅ APISIX setup completed"
    return 0
}

# Function to configure APISIX routes
configure_apisix_routes() {
    log_detail "Configuring APISIX routes..."
    
    # Wait a bit for APISIX to fully initialize
    sleep 5
    
    # Configure routes using the route configuration script
    if [ -f "apisix/configure_routes.sh" ]; then
        log_detail "Running route configuration script..."
        cd apisix
        bash configure_routes.sh
        cd ..
    else
        log_warn "Route configuration script not found"
    fi
    
    log_success "APISIX routes configured"
}