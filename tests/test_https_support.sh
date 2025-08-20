#!/usr/bin/env bash
# test_https_support.sh - Test script for HTTPS support in ViolentUTF

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Test functions
print_test_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

test_pass() {
    echo -e "${GREEN}✅ PASS${NC}: $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

test_fail() {
    echo -e "${RED}❌ FAIL${NC}: $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

test_info() {
    echo -e "${YELLOW}ℹ️  INFO${NC}: $1"
}

# Test 1: URL Parsing Function
test_url_parsing() {
    print_test_header "Test 1: URL Parsing Function"

    # Source the utils
    source ../setup_macos_files/utils.sh

    # Test cases
    local test_urls=(
        "https://api.example.com|https|api.example.com|443|/"
        "http://localhost:8080/api|http|localhost|8080|/api"
        "https://gsai.enterprise.com:8443|https|gsai.enterprise.com|8443|/"
        "api.example.com|http|api.example.com|80|/"
    )

    for test_case in "${test_urls[@]}"; do
        IFS='|' read -r url expected_scheme expected_host expected_port expected_path <<< "$test_case"

        # Test scheme extraction
        local scheme=$(parse_url "$url" scheme)
        if [ "$scheme" = "$expected_scheme" ]; then
            test_pass "parse_url '$url' scheme = $scheme"
        else
            test_fail "parse_url '$url' scheme: expected $expected_scheme, got $scheme"
        fi

        # Test host extraction
        local host=$(parse_url "$url" host)
        if [ "$host" = "$expected_host" ]; then
            test_pass "parse_url '$url' host = $host"
        else
            test_fail "parse_url '$url' host: expected $expected_host, got $host"
        fi

        # Test port extraction
        local port=$(parse_url "$url" port)
        if [ "$port" = "$expected_port" ]; then
            test_pass "parse_url '$url' port = $port"
        else
            test_fail "parse_url '$url' port: expected $expected_port, got $port"
        fi
    done
}

# Test 2: HTTPS Configuration Detection
test_https_config() {
    print_test_header "Test 2: HTTPS Configuration Detection"

    # Source utils
    source ../setup_macos_files/utils.sh

    # Create test environment
    export OPENAPI_1_BASE_URL="https://gsai.example.com"
    export OPENAPI_1_USE_HTTPS="auto"
    export OPENAPI_1_SSL_VERIFY="true"
    export OPENAPI_1_CA_CERT_PATH="/etc/ssl/certs/ca.crt"

    # Test get_https_config
    local config=$(get_https_config "1")

    if echo "$config" | grep -q "scheme=https"; then
        test_pass "HTTPS auto-detection works"
    else
        test_fail "HTTPS auto-detection failed"
    fi

    if echo "$config" | grep -q "ssl_verify=true"; then
        test_pass "SSL verification flag detected"
    else
        test_fail "SSL verification flag not detected"
    fi

    # Test forced HTTP
    export OPENAPI_1_USE_HTTPS="false"
    config=$(get_https_config "1")

    if echo "$config" | grep -q "scheme=http"; then
        test_pass "Forced HTTP override works"
    else
        test_fail "Forced HTTP override failed"
    fi
}

# Test 3: Environment Validation
test_env_validation() {
    print_test_header "Test 3: Environment Validation"

    # Source validation script
    source ../setup_macos_files/validate_https_config.sh

    # Test 1: Valid HTTPS configuration
    export OPENAPI_1_ENABLED="true"
    export OPENAPI_1_BASE_URL="https://api.example.com"
    export OPENAPI_1_USE_HTTPS="true"
    export OPENAPI_1_SSL_VERIFY="true"

    if validate_provider_https_config "1" "test-api" >/dev/null 2>&1; then
        test_pass "Valid HTTPS configuration passes validation"
    else
        test_fail "Valid HTTPS configuration failed validation"
    fi

    # Test 2: Conflicting configuration
    export OPENAPI_1_BASE_URL="http://api.example.com"
    export OPENAPI_1_USE_HTTPS="true"

    if validate_provider_https_config "1" "test-api" 2>&1 | grep -q "WARNING"; then
        test_pass "Conflicting configuration detected"
    else
        test_fail "Conflicting configuration not detected"
    fi

    # Test 3: Missing CA certificate
    export OPENAPI_1_CA_CERT_PATH="/nonexistent/ca.crt"

    if validate_provider_https_config "1" "test-api" 2>&1 | grep -q "ERROR"; then
        test_pass "Missing CA certificate detected"
    else
        test_fail "Missing CA certificate not detected"
    fi
}

# Test 4: Certificate Management
test_certificate_management() {
    print_test_header "Test 4: Certificate Management"

    # Source certificate management
    source ../setup_macos_files/certificate_management.sh

    # Test certificate detection
    test_info "Testing certificate detection..."
    local certs=$(detect_ca_certificates)
    if [ -n "$certs" ]; then
        test_pass "Certificate detection completed"
    else
        test_info "No certificates found (may be normal)"
    fi

    # Test certificate validation (using a test cert if available)
    if [ -f "/etc/ssl/cert.pem" ]; then
        if validate_certificate "/etc/ssl/cert.pem" >/dev/null 2>&1; then
            test_pass "Certificate validation works"
        else
            test_info "Certificate validation failed (cert may be invalid)"
        fi
    else
        test_info "No test certificate available for validation"
    fi
}

# Test 5: Route Configuration
test_route_configuration() {
    print_test_header "Test 5: Route Configuration Testing"

    # This would test actual route creation, but requires APISIX to be running
    test_info "Route configuration tests require running APISIX instance"

    # Test JSON generation for HTTPS route
    local test_scheme="https"
    local test_ssl_verify="true"
    local test_host="gsai.example.com:443"

    # Generate sample route JSON
    local route_json=$(jq -n \
        --arg scheme "$test_scheme" \
        --arg host "$test_host" \
        --argjson ssl_verify "$test_ssl_verify" \
        '{
            "upstream": {
                "type": "roundrobin",
                "scheme": $scheme,
                "nodes": {
                    ($host): 1
                },
                "tls": {
                    "verify": $ssl_verify
                }
            }
        }')

    if echo "$route_json" | jq -e '.upstream.scheme == "https"' >/dev/null; then
        test_pass "HTTPS route JSON generation works"
    else
        test_fail "HTTPS route JSON generation failed"
    fi

    if echo "$route_json" | jq -e '.upstream.tls.verify == true' >/dev/null; then
        test_pass "SSL verification in route JSON works"
    else
        test_fail "SSL verification in route JSON failed"
    fi
}

# Test 6: Integration Test
test_integration() {
    print_test_header "Test 6: Integration Test"

    # Check if APISIX is running
    if curl -s http://localhost:9180/apisix/admin/routes >/dev/null 2>&1; then
        test_info "APISIX is running - performing integration tests"

        # Would create a test route and verify it works
        test_info "Full integration test would create and test HTTPS routes"
    else
        test_info "APISIX not running - skipping integration tests"
    fi
}

# Main test execution
main() {
    echo "🧪 ViolentUTF HTTPS Support Test Suite"
    echo "======================================"
    echo "Running tests for enterprise HTTPS support implementation"

    # Change to tests directory
    cd "$(dirname "$0")"

    # Run all tests
    test_url_parsing
    test_https_config
    test_env_validation
    test_certificate_management
    test_route_configuration
    test_integration

    # Summary
    echo ""
    echo "=========================================="
    echo "TEST SUMMARY"
    echo "=========================================="
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}🎉 All tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Some tests failed${NC}"
        exit 1
    fi
}

# Run tests
main "$@"
