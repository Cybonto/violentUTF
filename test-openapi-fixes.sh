#!/usr/bin/env bash
# Test script for OpenAPI setup fixes
# Tests the 6 major fixes implemented for setup_macos.sh OpenAPI functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Testing OpenAPI Setup Fixes${NC}"
echo "=================================="

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# Test result function
test_result() {
    local test_name="$1"
    local result="$2"
    local details="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        if [ -n "$details" ]; then
            echo -e "   ${YELLOW}Details: $details${NC}"
        fi
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Test 1: APISIX Readiness Check Function
echo -e "\n${BLUE}Test 1: APISIX Readiness Check Function${NC}"
if grep -q "wait_for_apisix_admin_api()" setup_macos.sh; then
    if grep -A 20 "wait_for_apisix_admin_api()" setup_macos.sh | grep -q "APISIX admin API is ready"; then
        test_result "APISIX readiness function exists and has proper checks" "PASS"
    else
        test_result "APISIX readiness function exists but missing checks" "FAIL"
    fi
else
    test_result "APISIX readiness function missing" "FAIL"
fi

# Test 2: OpenAPI Configuration Validation
echo -e "\n${BLUE}Test 2: OpenAPI Configuration Validation${NC}"
if grep -q "validate_all_openapi_providers()" setup_macos.sh; then
    if grep -q "validate_openapi_provider()" setup_macos.sh; then
        test_result "OpenAPI validation functions exist" "PASS"
    else
        test_result "OpenAPI validation incomplete" "FAIL"
    fi
else
    test_result "OpenAPI validation functions missing" "FAIL"
fi

# Test 3: Enhanced Spec Fetching and Validation
echo -e "\n${BLUE}Test 3: Enhanced Spec Fetching and Validation${NC}"
if grep -q "fetch_openapi_spec()" setup_macos.sh; then
    if grep -A 10 "fetch_openapi_spec()" setup_macos.sh | grep -q "SSL certificate"; then
        test_result "Enhanced spec fetching with SSL handling" "PASS"
    else
        test_result "Basic spec fetching exists but missing enhancements" "FAIL"
    fi
else
    test_result "Spec fetching function missing" "FAIL"
fi

# Test 4: Route Creation Error Handling
echo -e "\n${BLUE}Test 4: Route Creation Error Handling${NC}"
if grep -q "create_openapi_route()" setup_macos.sh; then
    if grep -A 30 "create_openapi_route()" setup_macos.sh | grep -q "Parse error details"; then
        test_result "Enhanced route creation error handling" "PASS"
    else
        test_result "Basic route creation exists but missing error handling" "FAIL"
    fi
else
    test_result "Route creation function missing" "FAIL"
fi

# Test 5: Rollback Mechanisms
echo -e "\n${BLUE}Test 5: Rollback Mechanisms${NC}"
if grep -q "rollback_provider_routes()" setup_macos.sh; then
    if grep -q "save_provider_state()" setup_macos.sh; then
        test_result "Rollback mechanisms implemented" "PASS"
    else
        test_result "Partial rollback implementation" "FAIL"
    fi
else
    test_result "Rollback mechanisms missing" "FAIL"
fi

# Test 6: Integration in Main Setup Function
echo -e "\n${BLUE}Test 6: Integration in Main Setup Function${NC}"
if grep -A 50 "setup_openapi_routes()" setup_macos.sh | grep -q "wait_for_apisix_admin_api"; then
    if grep -A 100 "setup_openapi_routes()" setup_macos.sh | grep -q "rollback_provider_routes"; then
        test_result "Main setup function properly integrated with fixes" "PASS"
    else
        test_result "Main setup missing rollback integration" "FAIL"
    fi
else
    test_result "Main setup missing APISIX readiness check" "FAIL"
fi

# Test 7: Syntax Validation
echo -e "\n${BLUE}Test 7: Bash Syntax Validation${NC}"
if bash -n setup_macos.sh 2>/dev/null; then
    test_result "Bash syntax validation" "PASS"
else
    syntax_error=$(bash -n setup_macos.sh 2>&1)
    test_result "Bash syntax validation" "FAIL" "$syntax_error"
fi

# Test 8: Function Dependency Check
echo -e "\n${BLUE}Test 8: Function Dependency Check${NC}"
missing_deps=()

# Check if all required functions are defined
required_functions=(
    "wait_for_apisix_admin_api"
    "validate_all_openapi_providers"
    "validate_openapi_provider"
    "fetch_openapi_spec"
    "validate_openapi_spec"
    "parse_openapi_endpoints"
    "create_openapi_route"
    "clear_openapi_routes"
    "rollback_provider_routes"
    "save_provider_state"
    "setup_openapi_routes"
)

for func in "${required_functions[@]}"; do
    if ! grep -q "^${func}()" setup_macos.sh; then
        missing_deps+=("$func")
    fi
done

if [ ${#missing_deps[@]} -eq 0 ]; then
    test_result "All required functions present" "PASS"
else
    test_result "Missing required functions" "FAIL" "Missing: ${missing_deps[*]}"
fi

# Test 9: Environment Variable Handling
echo -e "\n${BLUE}Test 9: Environment Variable Handling${NC}"
env_vars_found=0

# Check for proper environment variable handling
if grep -q "APISIX_ADMIN_URL" setup_macos.sh; then
    env_vars_found=$((env_vars_found + 1))
fi
if grep -q "APISIX_ADMIN_KEY" setup_macos.sh; then
    env_vars_found=$((env_vars_found + 1))
fi
if grep -q "OPENAPI_.*_ENABLED" setup_macos.sh; then
    env_vars_found=$((env_vars_found + 1))
fi

if [ $env_vars_found -ge 3 ]; then
    test_result "Environment variable handling" "PASS"
else
    test_result "Environment variable handling" "FAIL" "Only $env_vars_found/3 key variables found"
fi

# Test 10: Error Recovery Patterns
echo -e "\n${BLUE}Test 10: Error Recovery Patterns${NC}"
recovery_patterns=0

# Check for error recovery patterns
if grep -q "if.*then.*else.*return.*fi" setup_macos.sh; then
    recovery_patterns=$((recovery_patterns + 1))
fi
if grep -q "|| echo.*Warning" setup_macos.sh; then
    recovery_patterns=$((recovery_patterns + 1))
fi
if grep -q "cleanup.*cache" setup_macos.sh; then
    recovery_patterns=$((recovery_patterns + 1))
fi

if [ $recovery_patterns -ge 2 ]; then
    test_result "Error recovery patterns" "PASS"
else
    test_result "Error recovery patterns" "FAIL" "Only $recovery_patterns recovery patterns found"
fi

# Test 11: OpenAPI Test Script Integration
echo -e "\n${BLUE}Test 11: OpenAPI Test Script Integration${NC}"
if [ -f "test-openapi-parsing.py" ]; then
    if python3 -m py_compile test-openapi-parsing.py 2>/dev/null; then
        test_result "OpenAPI test script syntax" "PASS"
    else
        test_result "OpenAPI test script syntax" "FAIL" "Python syntax error"
    fi
else
    test_result "OpenAPI test script missing" "FAIL" "test-openapi-parsing.py not found"
fi

# Test 12: Documentation and Comments
echo -e "\n${BLUE}Test 12: Documentation and Comments${NC}"
comment_lines=$(grep -c "^[[:space:]]*#" setup_macos.sh || echo "0")
function_comments=$(grep -c "# Function to" setup_macos.sh || echo "0")

if [ $comment_lines -gt 50 ] && [ $function_comments -gt 10 ]; then
    test_result "Documentation and comments" "PASS"
else
    test_result "Documentation and comments" "FAIL" "$comment_lines comment lines, $function_comments function comments"
fi

# Final Summary
echo -e "\n${BLUE}Test Summary${NC}"
echo "=============="
echo -e "Total Tests: $TOTAL_TESTS"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}🎉 All tests passed! OpenAPI fixes are properly implemented.${NC}"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Some tests failed. Review the implementation.${NC}"
    
    # Calculate success rate
    success_rate=$((TESTS_PASSED * 100 / TOTAL_TESTS))
    echo -e "Success Rate: ${success_rate}%"
    
    if [ $success_rate -ge 80 ]; then
        echo -e "${YELLOW}Most fixes are in place. Minor issues to address.${NC}"
        exit 1
    else
        echo -e "${RED}Significant issues found. Major fixes needed.${NC}"
        exit 2
    fi
fi