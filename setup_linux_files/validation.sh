#!/usr/bin/env bash
# validation.sh - Service validation functions

# Function to verify system state
verify_system_state() {
    log_phase "Verifying System State"

    local all_good=true

    # Check Docker
    if docker info >/dev/null 2>&1; then
        log_success "Docker is running"
    else
        log_error "Docker is not running"
        all_good=false
    fi

    # Check shared network
    if docker network ls | grep -q "$SHARED_NETWORK_NAME"; then
        log_success "Shared network exists: $SHARED_NETWORK_NAME"
    else
        log_error "Shared network missing: $SHARED_NETWORK_NAME"
        all_good=false
    fi

    # Check services
    local services=("keycloak" "apisix" "violentutf_api")
    for service in "${services[@]}"; do
        if docker ps | grep -q "$service"; then
            log_success "$service container is running"
        else
            log_error "$service container is not running"
            all_good=false
        fi
    done

    if [ "$all_good" = true ]; then
        log_success "System state verification passed"
        return 0
    else
        log_error "System state verification failed"
        return 1
    fi
}

# Function to validate all services
validate_all_services() {
    log_phase "Validating All Services"

    local validation_passed=true

    # Validate Keycloak
    if validate_keycloak; then
        log_success "Keycloak validation passed"
    else
        log_error "Keycloak validation failed"
        validation_passed=false
    fi

    # Validate APISIX
    if validate_apisix; then
        log_success "APISIX validation passed"
    else
        log_error "APISIX validation failed"
        validation_passed=false
    fi

    # Validate FastAPI
    if validate_fastapi; then
        log_success "FastAPI validation passed"
    else
        log_error "FastAPI validation failed"
        validation_passed=false
    fi

    # Validate AI providers if configured
    if validate_ai_providers; then
        log_success "AI provider validation passed"
    else
        log_warn "AI provider validation failed (this is optional)"
    fi

    if [ "$validation_passed" = true ]; then
        log_success "All service validations passed"
        return 0
    else
        log_error "Some service validations failed"
        return 1
    fi
}

# Function to validate Keycloak
validate_keycloak() {
    log_detail "Validating Keycloak..."

    # Check if Keycloak is accessible
    local keycloak_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/realms/master/.well-known/openid-configuration")
    if [ "$keycloak_status" -ne 200 ]; then
        log_error "Keycloak master realm is not accessible"
        return 1
    fi

    # Check ViolentUTF realm
    local vutf_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration")
    if [ "$vutf_status" -ne 200 ]; then
        log_error "ViolentUTF realm is not accessible"
        return 1
    fi

    return 0
}

# Function to validate APISIX
validate_apisix() {
    log_detail "Validating APISIX..."

    # Check if APISIX gateway is accessible
    local apisix_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:9080/")
    if [ "$apisix_status" -eq 000 ]; then
        log_error "APISIX gateway is not accessible"
        return 1
    fi

    # Check APISIX admin API (internal)
    if [ -n "$APISIX_ADMIN_KEY" ]; then
        local admin_status=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-KEY: $APISIX_ADMIN_KEY" "http://localhost:9180/apisix/admin/routes")
        if [ "$admin_status" -ne 200 ]; then
            log_warn "APISIX admin API not accessible (this is normal if accessed from outside container)"
        fi
    fi

    return 0
}

# Function to validate FastAPI
validate_fastapi() {
    log_detail "Validating FastAPI..."

    # Check if FastAPI is accessible through APISIX
    local api_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:9080/api/v1/health")
    if [ "$api_status" -ne 200 ]; then
        log_error "FastAPI is not accessible through APISIX"
        return 1
    fi

    # Check API docs
    local docs_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:9080/api/docs")
    if [ "$docs_status" -ne 200 ]; then
        log_warn "FastAPI documentation not accessible"
    fi

    return 0
}

# Function to validate AI providers
validate_ai_providers() {
    log_detail "Validating AI providers..."

    # Load AI tokens
    if [ -f "$AI_TOKENS_FILE" ]; then
        source "$AI_TOKENS_FILE"
    fi

    local any_provider_enabled=false

    # Check Ollama
    if [ "${OLLAMA_ENABLED:-false}" = "true" ]; then
        any_provider_enabled=true
        local ollama_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:11434/api/tags")
        if [ "$ollama_status" -eq 200 ]; then
            log_success "Ollama is accessible"
        else
            log_warn "Ollama is enabled but not accessible at localhost:11434"
        fi
    fi

    # Check OpenAI
    if [ "${OPENAI_ENABLED:-false}" = "true" ]; then
        any_provider_enabled=true
        if [ -n "$OPENAI_API_KEY" ] && [ "$OPENAI_API_KEY" != "your_openai_api_key_here" ]; then
            log_success "OpenAI is configured"
        else
            log_warn "OpenAI is enabled but API key not configured"
        fi
    fi

    # Check Anthropic
    if [ "${ANTHROPIC_ENABLED:-false}" = "true" ]; then
        any_provider_enabled=true
        if [ -n "$ANTHROPIC_API_KEY" ] && [ "$ANTHROPIC_API_KEY" != "your_anthropic_api_key_here" ]; then
            log_success "Anthropic is configured"
        else
            log_warn "Anthropic is enabled but API key not configured"
        fi
    fi

    if [ "$any_provider_enabled" = false ]; then
        log_warn "No AI providers are enabled"
        return 1
    fi

    return 0
}

# Function to run comprehensive tests
run_comprehensive_tests() {
    log_phase "Running Comprehensive Tests"

    echo "Testing network connectivity..."
    test_network_connectivity "apisix-apisix-1" "keycloak" "8080"
    test_network_connectivity "violentutf_api-fastapi-1" "apisix-apisix-1" "9080"

    echo ""
    echo "Testing API endpoints..."

    # Test health endpoint
    run_test "Health endpoint" "curl -s http://localhost:9080/api/v1/health | grep -q healthy"

    # Test authentication flow
    if [ -n "$VIOLENTUTF_USER_PASSWORD" ]; then
        run_test "Authentication endpoint" "curl -s http://localhost:9080/auth/realms/ViolentUTF/.well-known/openid-configuration | grep -q authorization_endpoint"
    fi

    echo ""
    log_success "Comprehensive tests completed"
}
