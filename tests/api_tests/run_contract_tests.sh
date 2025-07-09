#!/bin/bash

# Run API contract tests for ViolentUTF
# This script sets up the environment and runs contract testing

set -e

echo "🧪 ViolentUTF API Contract Testing"
echo "=================================="

# Set contract testing environment
export TESTING="true"
export CONTRACT_TESTING="true"
export JWT_SECRET_KEY="test_jwt_secret_for_contract_testing_only"
export SECRET_KEY="test_jwt_secret_for_contract_testing_only"
export VIOLENTUTF_API_KEY="test_api_key_for_contract_testing"
export APISIX_API_KEY="test_api_key_for_contract_testing"
export AI_GATEWAY_API_KEY="test_api_key_for_contract_testing"
export KEYCLOAK_URL="http://localhost:8080"
export KEYCLOAK_REALM="ViolentUTF-Test"
export KEYCLOAK_USERNAME="violentutf.test"
export KEYCLOAK_PASSWORD="test_password"
export KEYCLOAK_APISIX_CLIENT_ID="apisix-test"
export KEYCLOAK_APISIX_CLIENT_SECRET="test_secret"
export VIOLENTUTF_API_URL="http://localhost:8000"
export DUCKDB_PATH=":memory:"
export PYRIT_DB_PATH=":memory:"

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "📁 Project root: ${PROJECT_ROOT}"
echo "🔧 Test environment configured"

# Change to project root
cd "${PROJECT_ROOT}"

# Check if Python virtual environment exists
if [ -d "venv" ]; then
    echo "🐍 Activating Python virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "🐍 Activating Python virtual environment..."
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found, using system Python"
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-mock httpx jsonschema openapi-spec-validator PyJWT fastapi uvicorn

if [ -f "tests/requirements.txt" ]; then
    pip install -q -r tests/requirements.txt
fi

# Generate OpenAPI schema
echo "🔄 Generating OpenAPI schema..."
python tests/api_tests/generate_openapi_schema.py --output generated_openapi.json

# Validate OpenAPI schema
echo "✅ Validating OpenAPI schema..."
python tests/api_tests/validate_openapi_schemas.py

# Run contract tests
echo "🧪 Running API contract tests..."
python -m pytest tests/api_tests/test_contract_validation.py -v --tb=short --junit-xml=contract-test-results.xml -m "contract"

# Run additional API tests if available
if [ -f "tests/api_tests/test_auth_mock.py" ]; then
    echo "🔐 Running authentication mock tests..."
    python -m pytest tests/api_tests/test_auth_mock.py -v --tb=short -m "contract" || true
fi

# Check for other contract tests
echo "🔍 Running other contract tests..."
python -m pytest tests/api_tests/ -v --tb=short -m "contract and allows_mock_auth" || true

echo ""
echo "✅ Contract testing completed!"
echo "📄 Results saved to: contract-test-results.xml"
echo "📋 OpenAPI schema: generated_openapi.json"

# Summary
if [ -f "contract-test-results.xml" ]; then
    echo ""
    echo "📊 Test Results Summary:"
    echo "======================"
    
    # Extract test results from XML (simple grep)
    TESTS=$(grep -o 'tests="[0-9]*"' contract-test-results.xml | cut -d'"' -f2 || echo "0")
    FAILURES=$(grep -o 'failures="[0-9]*"' contract-test-results.xml | cut -d'"' -f2 || echo "0")
    ERRORS=$(grep -o 'errors="[0-9]*"' contract-test-results.xml | cut -d'"' -f2 || echo "0")
    
    echo "Total tests: ${TESTS}"
    echo "Failures: ${FAILURES}"
    echo "Errors: ${ERRORS}"
    
    if [ "${FAILURES}" -eq "0" ] && [ "${ERRORS}" -eq "0" ]; then
        echo "🎉 All tests passed!"
        exit 0
    else
        echo "❌ Some tests failed"
        exit 1
    fi
else
    echo "⚠️  No test results file found"
    exit 1
fi