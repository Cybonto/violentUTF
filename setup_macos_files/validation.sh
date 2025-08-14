#!/usr/bin/env bash
# validation.sh - System validation and health checks

# Function to verify system state
verify_system_state() {
    echo "Verifying system state..."
    
    local total_checks=0
    local passed_checks=0
    
    # Check Docker network
    if docker network inspect "$SHARED_NETWORK_NAME" >/dev/null 2>&1; then
        echo "✅ Shared Docker network exists"
        passed_checks=$((passed_checks + 1))
    else
        echo "❌ Shared Docker network missing"
    fi
    total_checks=$((total_checks + 1))
    
    # Check Keycloak
    if curl -s -k http://localhost:8080/realms/master >/dev/null 2>&1; then
        echo "✅ Keycloak is accessible"
        passed_checks=$((passed_checks + 1))
    else
        echo "❌ Keycloak is not accessible"
    fi
    total_checks=$((total_checks + 1))
    
    # Check APISIX
    if curl -s http://localhost:9080/health >/dev/null 2>&1; then
        echo "✅ APISIX gateway is accessible"
        passed_checks=$((passed_checks + 1))
    else
        echo "❌ APISIX gateway is not accessible"
    fi
    total_checks=$((total_checks + 1))
    
    # Check ViolentUTF API
    if curl -s http://localhost:9080/api/v1/health >/dev/null 2>&1; then
        echo "✅ ViolentUTF API is accessible"
        passed_checks=$((passed_checks + 1))
    else
        echo "❌ ViolentUTF API is not accessible"
    fi
    total_checks=$((total_checks + 1))
    
    # Check MCP Documentation System
    if validate_documentation_system; then
        echo "✅ MCP documentation system is accessible"
        passed_checks=$((passed_checks + 1))
    else
        echo "❌ MCP documentation system is not accessible"
    fi
    total_checks=$((total_checks + 1))
    
    echo "📊 System verification: $passed_checks/$total_checks checks passed"
    
    if [ $passed_checks -eq $total_checks ]; then
        echo "✅ System state verification completed - ready for use!"
        return 0
    else
        echo "⚠️  System state verification found issues - may need manual intervention"
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    echo "Running integration tests..."
    
    # This would run the actual test suite
    echo "📝 Integration tests placeholder"
    echo "   In full implementation, this would run:"
    echo "   - API endpoint tests"
    echo "   - Authentication flow tests" 
    echo "   - AI provider route tests"
    echo "   - Database connectivity tests"
    
    return 0
}

# Function to validate all services
validate_all_services() {
    echo "Validating all services..."
    
    local services=("keycloak:8080" "apisix:9080" "api:9080/api/v1/health")
    local all_valid=true
    
    for service in "${services[@]}"; do
        local service_name=$(echo "$service" | cut -d':' -f1)
        local endpoint="http://localhost:${service#*:}"
        
        if curl -s "$endpoint" >/dev/null 2>&1; then
            echo "✅ $service_name service is valid"
        else
            echo "❌ $service_name service validation failed"
            all_valid=false
        fi
    done
    
    if [ "$all_valid" = true ]; then
        echo "✅ All services validated successfully"
        return 0
    else
        echo "❌ Some services failed validation"
        return 1
    fi
}

# Function to check service connectivity
check_service_connectivity() {
    echo "Checking service connectivity..."
    
    # Test basic connectivity between services
    echo "📋 Connectivity test results:"
    
    # Keycloak to host
    if curl -s -k http://localhost:8080/realms/master >/dev/null 2>&1; then
        echo "  ✅ Host -> Keycloak: OK"
    else
        echo "  ❌ Host -> Keycloak: FAILED"
    fi
    
    # APISIX to host
    if curl -s http://localhost:9080/health >/dev/null 2>&1; then
        echo "  ✅ Host -> APISIX: OK"
    else
        echo "  ❌ Host -> APISIX: FAILED"
    fi
    
    # API through APISIX
    if curl -s http://localhost:9080/api/v1/health >/dev/null 2>&1; then
        echo "  ✅ Host -> API (via APISIX): OK"
    else
        echo "  ❌ Host -> API (via APISIX): FAILED"
    fi
    
    echo "✅ Service connectivity check completed"
    return 0
}

# Function to validate MCP documentation system
validate_documentation_system() {
    log_detail "Validating MCP documentation system..."
    
    local docs_dir="./docs"
    local checks_passed=0
    local total_checks=3
    
    # Check 1: Verify docs directory exists and has content
    if [ -d "$docs_dir" ] && [ "$(find "$docs_dir" -name "*.md" | wc -l)" -gt 0 ]; then
        log_debug "✅ Documentation directory exists with MD files"
        checks_passed=$((checks_passed + 1))
    else
        log_debug "❌ Documentation directory missing or empty"
    fi
    
    # Check 2: Test MCP resources endpoint
    if curl -s -H "Content-Type: application/json" \
            -H "X-API-Gateway: MCP-Test" \
            -d '{"jsonrpc":"2.0","method":"resources/list","id":1}' \
            http://localhost:9080/mcp/sse/ >/dev/null 2>&1; then
        log_debug "✅ MCP resources endpoint is responding"
        checks_passed=$((checks_passed + 1))
    else
        log_debug "❌ MCP resources endpoint not responding"
    fi
    
    # Check 3: Verify documentation provider is initialized
    if [ -f "violentutf_api/fastapi_app/app/mcp/resources/documentation.py" ]; then
        log_debug "✅ Documentation provider file exists"
        checks_passed=$((checks_passed + 1))
    else
        log_debug "❌ Documentation provider file missing"
    fi
    
    if [ $checks_passed -eq $total_checks ]; then
        log_debug "📚 Documentation system validation: $checks_passed/$total_checks passed"
        return 0
    else
        log_warn "📚 Documentation system validation: $checks_passed/$total_checks passed"
        return 1
    fi
}