#!/usr/bin/env bash
# violentutf_api_setup.sh - FastAPI service configuration and startup

# Function to setup ViolentUTF API
setup_violentutf_api() {
    echo "Setting up ViolentUTF API service..."
    
    # The ViolentUTF API is now integrated with APISIX
    # This function primarily ensures environment configuration is correct
    
    # Configure FastAPI environment
    configure_fastapi_env
    
    # Update AI provider flags
    update_fastapi_env
    
    # Initialize documentation system
    initialize_documentation_system
    
    echo "✅ ViolentUTF API configuration completed"
    echo "📝 Note: API service is started with APISIX container stack"
    
    return 0
}

# Function to configure FastAPI environment
configure_fastapi_env() {
    echo "Configuring FastAPI environment..."
    
    local fastapi_env_file="violentutf_api/fastapi_app/.env"
    
    if [ ! -f "$fastapi_env_file" ]; then
        echo "❌ FastAPI .env file not found: $fastapi_env_file"
        return 1
    fi
    
    # Ensure required environment variables are set
    local required_vars=("JWT_SECRET_KEY" "VIOLENTUTF_API_KEY" "PYRIT_DB_SALT")
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$fastapi_env_file"; then
            echo "⚠️  Missing required variable: $var"
            echo "${var}=$(generate_random_string 32)" >> "$fastapi_env_file"
            echo "   Added $var to FastAPI environment"
        fi
    done
    
    # Ensure APP_DATA_DIR is set for Phase 1 database improvements
    if ! grep -q "^APP_DATA_DIR=" "$fastapi_env_file"; then
        echo "APP_DATA_DIR=/app/app_data/violentutf" >> "$fastapi_env_file"
        echo "   Added APP_DATA_DIR for consistent database paths"
    fi
    
    echo "✅ FastAPI environment configuration verified"
    return 0
}

# Function to verify API health
verify_api_health() {
    echo "Verifying API health..."
    
    local max_retries=10
    local retry_count=0
    
    # Wait for API to be accessible through APISIX
    while [ $retry_count -lt $max_retries ]; do
        if curl -s http://localhost:9080/api/v1/health >/dev/null 2>&1; then
            echo "✅ ViolentUTF API is healthy and accessible"
            
            # Get API health details
            local health_response=$(curl -s http://localhost:9080/api/v1/health 2>/dev/null || echo "{}")
            local api_status=$(echo "$health_response" | jq -r '.status' 2>/dev/null || echo "unknown")
            
            echo "📊 API Status: $api_status"
            return 0
        fi
        
        echo "Waiting for API health... (attempt $((retry_count + 1))/$max_retries)"
        sleep 5
        retry_count=$((retry_count + 1))
    done
    
    echo "❌ API health check failed - service may not be accessible"
    return 1
}

# Function to initialize MCP documentation system
initialize_documentation_system() {
    log_detail "Initializing MCP documentation system..."
    
    local docs_dir="./docs"
    local api_dir="violentutf_api/fastapi_app"
    
    # Check if documentation directory exists
    if [ ! -d "$docs_dir" ]; then
        log_warn "Documentation directory not found: $docs_dir"
        return 1
    fi
    
    # Count documentation files
    local doc_count=$(find "$docs_dir" -name "*.md" | wc -l)
    log_debug "Found $doc_count documentation files in $docs_dir"
    
    # Verify documentation provider exists
    if [ ! -f "$api_dir/app/mcp/resources/documentation.py" ]; then
        log_warn "Documentation provider not found: $api_dir/app/mcp/resources/documentation.py"
        return 1
    fi
    
    # Add documentation provider flag to FastAPI environment
    local fastapi_env_file="$api_dir/.env"
    if [ -f "$fastapi_env_file" ]; then
        if ! grep -q "^MCP_ENABLE_DOCUMENTATION=" "$fastapi_env_file"; then
            echo "MCP_ENABLE_DOCUMENTATION=true" >> "$fastapi_env_file"
            log_debug "Added MCP_ENABLE_DOCUMENTATION=true to FastAPI environment"
        fi
        
        # Set documentation directory path
        if ! grep -q "^DOCUMENTATION_ROOT_PATH=" "$fastapi_env_file"; then
            echo "DOCUMENTATION_ROOT_PATH=./docs" >> "$fastapi_env_file"
            log_debug "Added DOCUMENTATION_ROOT_PATH=./docs to FastAPI environment"
        fi
    else
        log_warn "FastAPI environment file not found: $fastapi_env_file"
        return 1
    fi
    
    log_success "MCP documentation system initialized successfully"
    log_info "📚 Documentation: $doc_count MD files will be accessible via SimpleChat"
    return 0
}