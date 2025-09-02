#!/bin/bash

# ViolentUTF Test Runner
# Runs all tests in the correct order with proper setup

set -e

cd "$(dirname "$0")"

echo "🧪 ViolentUTF Test Suite"
echo "========================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Check prerequisites
echo "🔍 Checking prerequisites..."

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

# Test 1: Unit Tests (Direct FastAPI)
echo "📋 Test 1: Unit Tests (Direct FastAPI)"
echo "--------------------------------------"

if [ "$FASTAPI_RUNNING" = true ]; then
    cd ../violentutf_api/fastapi_app

    if [ -d "venv_api" ]; then
        source venv_api/bin/activate
        export PYTHONPATH=$(pwd)

        print_status $BLUE "Running unit tests..."
        if python -m pytest ../../../tests/test_unit_api_endpoints.py -v; then
            print_status $GREEN "✅ Unit tests passed"
        else
            print_status $RED "❌ Unit tests failed"
        fi
    else
        print_status $YELLOW "⚠️  Virtual environment not found. Creating..."
        python3 -m venv venv_api
        source venv_api/bin/activate
        pip install -r requirements.txt
        pip install pytest duckdb

        export PYTHONPATH=$(pwd)

        print_status $BLUE "Running unit tests..."
        if python -m pytest ../../../tests/test_unit_api_endpoints.py -v; then
            print_status $GREEN "✅ Unit tests passed"
        else
            print_status $RED "❌ Unit tests failed"
        fi
    fi

    cd ../../tests
else
    print_status $YELLOW "⚠️  Skipping unit tests - FastAPI service not running"
fi

echo

# Test 2: Start Page Endpoint Verification
echo "📋 Test 2: Start Page Endpoint Verification"
echo "--------------------------------------------"

if [ "$APISIX_RUNNING" = true ]; then
    print_status $BLUE "Checking Start page endpoints..."
    if python3 test_start_page_endpoints.py; then
        print_status $GREEN "✅ Start page endpoints verified"
        ROUTES_CONFIGURED=true
    else
        print_status $RED "❌ Start page endpoints not routed"
        print_status $YELLOW "💡 Configure routes: cd ../apisix && ./configure_routes.sh"
        ROUTES_CONFIGURED=false
    fi
else
    print_status $YELLOW "⚠️  Skipping endpoint verification - APISIX not running"
    ROUTES_CONFIGURED=false
fi

echo

# Test 3: JWT Authentication Tests
echo "📋 Test 3: JWT Authentication Tests"
echo "-----------------------------------"

print_status $BLUE "Running JWT authentication tests..."
if python3 -m pytest test_jwt_authentication.py -v; then
    print_status $GREEN "✅ JWT authentication tests passed"
    JWT_TESTS_PASSED=true
else
    print_status $RED "❌ JWT authentication tests failed"
    JWT_TESTS_PASSED=false
fi

echo

# Test 4: APISIX Integration Tests
echo "📋 Test 4: APISIX Integration Tests"
echo "-----------------------------------"

if [ "$APISIX_RUNNING" = true ]; then
    print_status $BLUE "Running APISIX integration tests..."
    if python3 -m pytest test_apisix_integration.py -v -s; then
        print_status $GREEN "✅ APISIX integration tests passed"
    else
        if [ "$ROUTES_CONFIGURED" = false ]; then
            print_status $YELLOW "⚠️  Integration tests failed - routes not configured"
        else
            print_status $RED "❌ APISIX integration tests failed"
        fi
    fi
else
    print_status $YELLOW "⚠️  Skipping integration tests - APISIX not running"
fi

echo

# Test 5: API Tests (Generator functionality)
echo "📋 Test 5: API Tests (Generator functionality)"
echo "----------------------------------------------"

if [ "$APISIX_RUNNING" = true ] && [ "$ROUTES_CONFIGURED" = true ]; then
    print_status $BLUE "Running API tests..."
    cd api_tests
    if ./run_api_tests.sh; then
        print_status $GREEN "✅ API tests passed"
    else
        print_status $RED "❌ API tests failed"
    fi
    cd ..
else
    print_status $YELLOW "⚠️  Skipping API tests - APISIX not running or routes not configured"
fi

echo

# Summary
echo "📊 Test Summary"
echo "==============="

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

if [ "$ROUTES_CONFIGURED" = true ]; then
    print_status $GREEN "✅ APISIX Routes: Configured"
else
    print_status $RED "❌ APISIX Routes: Not Configured"
fi

if [ "$JWT_TESTS_PASSED" = true ]; then
    print_status $GREEN "✅ JWT Authentication: Tests Passed"
else
    print_status $RED "❌ JWT Authentication: Tests Failed"
fi

echo

# Next steps
if [ "$APISIX_RUNNING" = false ] || [ "$FASTAPI_RUNNING" = false ] || [ "$ROUTES_CONFIGURED" = false ] || [ "$JWT_TESTS_PASSED" = false ]; then
    echo "🛠️  Next Steps:"

    if [ "$APISIX_RUNNING" = false ]; then
        echo "   1. Start APISIX: cd ../apisix && docker compose up -d"
    fi

    if [ "$ROUTES_CONFIGURED" = false ] && [ "$APISIX_RUNNING" = true ]; then
        echo "   2. Configure routes: cd ../apisix && ./configure_routes.sh"
    fi

    if [ "$FASTAPI_RUNNING" = false ]; then
        echo "   3. Start FastAPI: cd ../violentutf_api && docker compose up -d"
    fi

    if [ "$JWT_TESTS_PASSED" = false ]; then
        echo "   4. Check JWT configuration: verify environment variables in .env files"
    fi

    echo "   5. Re-run tests: ./run_tests.sh"
else
    print_status $GREEN "🎉 All tests passed! System is ready for use."
    echo
    echo "🚀 Start Streamlit app: cd ../violentutf && streamlit run Home.py"
    echo "   Navigate to 0_Start page to test API integration"
fi
