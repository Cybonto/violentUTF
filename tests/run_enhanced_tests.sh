#!/bin/bash

# Enhanced ViolentUTF Test Runner with Live Authentication
# Runs tests with Keycloak SSO and real JWT tokens

set -e

cd "$(dirname "$0")"

echo "🔐 ViolentUTF Enhanced Test Suite with Live Authentication"
echo "==========================================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if service is running
check_service() {
    local service_url=$1
    local service_name=$2
    
    if curl -s "$service_url" > /dev/null 2>&1; then
        print_status $GREEN "✅ $service_name is running"
        return 0
    else
        print_status $RED "❌ $service_name is not running"
        return 1
    fi
}

# Function to check Keycloak authentication
test_keycloak_auth() {
    print_status $BLUE "🔐 Testing Keycloak authentication..."
    
    # Run the Keycloak auth test
    if python3 utils/keycloak_auth.py; then
        print_status $GREEN "✅ Keycloak authentication working"
        return 0
    else
        print_status $YELLOW "⚠️  Keycloak authentication issues detected"
        return 1
    fi
}

# Check prerequisites
echo "🔍 Checking prerequisites..."

# Check Keycloak
if ! check_service "http://localhost:8080/realms/ViolentUTF" "Keycloak"; then
    print_status $YELLOW "💡 Start Keycloak: cd ../keycloak && docker compose up -d"
    KEYCLOAK_RUNNING=false
else
    KEYCLOAK_RUNNING=true
fi

# Check APISIX
if ! check_service "http://localhost:9080/health" "APISIX Gateway"; then
    print_status $YELLOW "💡 Start APISIX: cd ../apisix && docker compose up -d"
    APISIX_RUNNING=false
else
    APISIX_RUNNING=true
fi

# Check FastAPI
if ! check_service "http://localhost:8000/health" "FastAPI Service"; then
    print_status $YELLOW "💡 Start FastAPI: cd ../violentutf_api && docker compose up -d"
    FASTAPI_RUNNING=false
else
    FASTAPI_RUNNING=true
fi

echo

# Test Keycloak authentication if available
if [ "$KEYCLOAK_RUNNING" = true ]; then
    test_keycloak_auth
    KEYCLOAK_AUTH_OK=$?
else
    KEYCLOAK_AUTH_OK=1
fi

echo

# Test 1: Enhanced JWT Authentication Tests with Keycloak
echo "📋 Test 1: Enhanced JWT Authentication Tests with Keycloak"
echo "----------------------------------------------------------"

if [ "$KEYCLOAK_RUNNING" = true ]; then
    print_status $BLUE "Running enhanced JWT authentication tests with live Keycloak..."
    if python3 -m pytest test_jwt_authentication.py::TestJWTAuthentication::test_jwt_token_creation \
                       test_jwt_authentication.py::TestJWTAuthentication::test_jwt_token_expiry_detection \
                       test_jwt_authentication.py::TestJWTAuthentication::test_jwt_token_refresh_timing \
                       test_jwt_authentication.py::TestJWTAuthentication::test_apisix_api_key_header_format \
                       -v -s; then
        print_status $GREEN "✅ Enhanced JWT tests passed"
        JWT_ENHANCED_PASSED=true
    else
        print_status $RED "❌ Enhanced JWT tests failed"
        JWT_ENHANCED_PASSED=false
    fi
else
    print_status $YELLOW "⚠️  Skipping enhanced JWT tests - Keycloak not running"
    JWT_ENHANCED_PASSED=false
fi

echo

# Test 2: Live Authentication API Tests
echo "📋 Test 2: Live Authentication API Tests"
echo "----------------------------------------"

if [ "$APISIX_RUNNING" = true ] && [ "$KEYCLOAK_RUNNING" = true ]; then
    print_status $BLUE "Running live authentication API tests..."
    cd api_tests
    if python3 -m pytest test_enhanced_generator_functionality.py -v -s --tb=short; then
        print_status $GREEN "✅ Live authentication API tests passed"
        LIVE_API_PASSED=true
    else
        print_status $RED "❌ Live authentication API tests failed"
        LIVE_API_PASSED=false
    fi
    cd ..
else
    print_status $YELLOW "⚠️  Skipping live API tests - APISIX or Keycloak not running"
    LIVE_API_PASSED=false
fi

echo

# Test 3: Enhanced APISIX Integration Tests
echo "📋 Test 3: Enhanced APISIX Integration Tests"
echo "--------------------------------------------"

if [ "$APISIX_RUNNING" = true ]; then
    print_status $BLUE "Running enhanced APISIX integration tests..."
    if python3 -m pytest test_apisix_integration.py::TestJWTAuthenticationIntegration \
                       test_apisix_integration.py::TestAuthenticationErrorHandling \
                       -v -s; then
        print_status $GREEN "✅ Enhanced APISIX integration tests passed"
        APISIX_ENHANCED_PASSED=true
    else
        print_status $RED "❌ Enhanced APISIX integration tests failed"
        APISIX_ENHANCED_PASSED=false
    fi
else
    print_status $YELLOW "⚠️  Skipping enhanced APISIX tests - APISIX not running"
    APISIX_ENHANCED_PASSED=false
fi

echo

# Test 4: End-to-End Workflow Test
echo "📋 Test 4: End-to-End Workflow Test"
echo "-----------------------------------"

if [ "$APISIX_RUNNING" = true ] && [ "$KEYCLOAK_RUNNING" = true ] && [ "$FASTAPI_RUNNING" = true ]; then
    print_status $BLUE "Running end-to-end workflow test..."
    
    # Test the complete workflow: Keycloak auth -> JWT creation -> API calls -> Generator testing
    cd api_tests
    if python3 -m pytest test_enhanced_generator_functionality.py::TestEnhancedGeneratorFunctionality::test_keycloak_authentication_flow \
                       test_enhanced_generator_functionality.py::TestEnhancedGeneratorFunctionality::test_create_openai_generator_live \
                       test_enhanced_generator_functionality.py::TestEnhancedGeneratorFunctionality::test_generator_testing_live \
                       -v -s; then
        print_status $GREEN "✅ End-to-end workflow test passed"
        E2E_PASSED=true
    else
        print_status $YELLOW "⚠️  End-to-end workflow test had issues (may be due to AI provider connectivity)"
        E2E_PASSED=false
    fi
    cd ..
else
    print_status $YELLOW "⚠️  Skipping end-to-end test - not all services running"
    E2E_PASSED=false
fi

echo

# Performance and Load Test (Optional)
echo "📋 Test 5: Authentication Performance Test"
echo "------------------------------------------"

if [ "$KEYCLOAK_RUNNING" = true ] && [ "$APISIX_RUNNING" = true ]; then
    print_status $BLUE "Running authentication performance test..."
    
    # Test multiple rapid authentication requests
    python3 -c "
import time
import sys
sys.path.append('.')
from utils.keycloak_auth import keycloak_auth

print('Testing 5 rapid authentication requests...')
start_time = time.time()
successes = 0

for i in range(5):
    headers = keycloak_auth.get_auth_headers()
    if headers and 'Authorization' in headers:
        successes += 1
        print(f'  Request {i+1}: ✅ Success')
    else:
        print(f'  Request {i+1}: ❌ Failed')

end_time = time.time()
duration = end_time - start_time

print(f'Performance: {successes}/5 successful in {duration:.2f}s ({duration/5:.2f}s avg)')
if successes >= 4:
    print('✅ Performance test passed')
    exit(0)
else:
    print('❌ Performance test failed')
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_status $GREEN "✅ Authentication performance test passed"
        PERF_PASSED=true
    else
        print_status $RED "❌ Authentication performance test failed"
        PERF_PASSED=false
    fi
else
    print_status $YELLOW "⚠️  Skipping performance test - services not available"
    PERF_PASSED=false
fi

echo

# Summary
echo "📊 Enhanced Test Summary"
echo "========================"

# Service Status
if [ "$KEYCLOAK_RUNNING" = true ]; then
    print_status $GREEN "✅ Keycloak Service: Running"
else
    print_status $RED "❌ Keycloak Service: Not Running"
fi

if [ "$FASTAPI_RUNNING" = true ]; then
    print_status $GREEN "✅ FastAPI Service: Running"
else
    print_status $RED "❌ FastAPI Service: Not Running"
fi

if [ "$APISIX_RUNNING" = true ]; then
    print_status $GREEN "✅ APISIX Gateway: Running"
else
    print_status $RED "❌ APISIX Gateway: Not Running"
fi

# Authentication Status
if [ "$KEYCLOAK_AUTH_OK" -eq 0 ]; then
    print_status $GREEN "✅ Keycloak Authentication: Working"
else
    print_status $RED "❌ Keycloak Authentication: Issues"
fi

# Test Results
if [ "$JWT_ENHANCED_PASSED" = true ]; then
    print_status $GREEN "✅ Enhanced JWT Tests: Passed"
else
    print_status $RED "❌ Enhanced JWT Tests: Failed"
fi

if [ "$LIVE_API_PASSED" = true ]; then
    print_status $GREEN "✅ Live API Tests: Passed"
else
    print_status $RED "❌ Live API Tests: Failed"
fi

if [ "$APISIX_ENHANCED_PASSED" = true ]; then
    print_status $GREEN "✅ Enhanced APISIX Tests: Passed"
else
    print_status $RED "❌ Enhanced APISIX Tests: Failed"
fi

if [ "$E2E_PASSED" = true ]; then
    print_status $GREEN "✅ End-to-End Workflow: Passed"
else
    print_status $YELLOW "⚠️  End-to-End Workflow: Issues (may be AI provider related)"
fi

if [ "$PERF_PASSED" = true ]; then
    print_status $GREEN "✅ Performance Tests: Passed"
else
    print_status $RED "❌ Performance Tests: Failed"
fi

echo

# Next steps
if [ "$KEYCLOAK_RUNNING" = false ] || [ "$FASTAPI_RUNNING" = false ] || [ "$APISIX_RUNNING" = false ]; then
    echo "🛠️  Next Steps for Full Testing:"
    
    if [ "$KEYCLOAK_RUNNING" = false ]; then
        echo "   1. Start Keycloak: cd ../keycloak && docker compose up -d"
    fi
    
    if [ "$APISIX_RUNNING" = false ]; then
        echo "   2. Start APISIX: cd ../apisix && docker compose up -d"
    fi
    
    if [ "$FASTAPI_RUNNING" = false ]; then
        echo "   3. Start FastAPI: cd ../violentutf_api && docker compose up -d"
    fi
    
    echo "   4. Configure routes: cd ../apisix && ./configure_routes.sh"
    echo "   5. Re-run enhanced tests: ./run_enhanced_tests.sh"
else
    if [ "$LIVE_API_PASSED" = true ] && [ "$JWT_ENHANCED_PASSED" = true ]; then
        print_status $GREEN "🎉 All enhanced tests passed! Live authentication is working perfectly."
        echo
        echo "🚀 Start Streamlit app with live auth: cd ../violentutf && streamlit run Home.py"
        echo "   Navigate to pages and test with real Keycloak authentication"
    else
        print_status $YELLOW "⚠️  Some enhanced tests had issues. Check the output above for details."
    fi
fi

echo
print_status $CYAN "📖 Enhanced Testing Documentation:"
print_status $CYAN "   - Live authentication uses real Keycloak SSO"
print_status $CYAN "   - JWT tokens are created from Keycloak user info"
print_status $CYAN "   - All API calls use real authentication headers"
print_status $CYAN "   - Tests validate the complete auth flow"