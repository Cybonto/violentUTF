#!/usr/bin/env bash
# violentutf_api_setup.sh - ViolentUTF API (FastAPI) setup

# Main ViolentUTF API setup function
setup_violentutf_api() {
    log_detail "Setting up ViolentUTF API (FastAPI)..."
    
    local API_DIR="violentutf_api"
    
    cd "$API_DIR" || return 1
    
    # Build and start the API service
    log_detail "Building and starting ViolentUTF API service..."
    $DOCKER_COMPOSE_CMD up -d --build
    
    # Wait for API to be ready
    log_detail "Waiting for ViolentUTF API to be ready..."
    local RETRY_COUNT=0
    local MAX_RETRIES=60
    local SUCCESS=false
    
    until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
        RETRY_COUNT=$((RETRY_COUNT+1))
        
        # Check API health through APISIX
        if curl -s --max-time 5 http://localhost:9080/api/v1/health 2>/dev/null | grep -q "healthy"; then
            log_success "ViolentUTF API is healthy and responding"
            SUCCESS=true
            break
        fi
        
        log_debug "API not ready yet (attempt $RETRY_COUNT/$MAX_RETRIES). Waiting 5 seconds..."
        sleep 5
    done
    
    if [ "$SUCCESS" = false ]; then
        echo "❌ ViolentUTF API did not become ready in time"
        $DOCKER_COMPOSE_CMD logs
        cd ..
        return 1
    fi
    
    cd ..
    echo "✅ ViolentUTF API setup completed"
    return 0
}