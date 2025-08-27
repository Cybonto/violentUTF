#!/bin/bash

# Run API tests for ViolentUTF Generator functionality
# This script runs the pytest tests for "Save and Test Generator" functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Running ViolentUTF API Tests for Generator Functionality${NC}"
echo "=================================================================="

# Check if services are running
echo -e "${YELLOW}🔍 Checking API service availability...${NC}"

API_URL="${VIOLENTUTF_API_URL:-http://localhost:9080}"
echo "Using API URL: $API_URL"

# Test API connectivity
if curl -sf "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ API service is reachable${NC}"
else
    echo -e "${RED}❌ API service not reachable at $API_URL${NC}"
    echo "Please ensure the APISIX and FastAPI services are running:"
    echo "cd ../apisix && docker compose up -d"
    exit 1
fi

# Install requirements if needed
if ! python3 -c "import pytest" &> /dev/null; then
    echo -e "${YELLOW}📦 Installing pytest...${NC}"
    pip3 install pytest requests
fi

# Set up environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../../"
export VIOLENTUTF_API_URL="$API_URL"

echo -e "${YELLOW}🚀 Running API tests...${NC}"
echo ""

# Run the tests
if python3 -m pytest test_save_and_test_generator.py -v --tb=short; then
    echo ""
    echo -e "${GREEN}✅ All API tests passed!${NC}"
    echo -e "${GREEN}🎉 Save and Test Generator functionality is working correctly${NC}"
else
    echo ""
    echo -e "${RED}❌ Some API tests failed${NC}"
    echo -e "${YELLOW}💡 Check the test output above for details${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}📊 Test Summary:${NC}"
echo "- Generator creation and validation: ✅"
echo "- Provider-specific parameter handling: ✅"
echo "- Model selection and testing: ✅"
echo "- Error handling and edge cases: ✅"
echo ""
echo -e "${GREEN}🔧 To run specific test categories:${NC}"
echo "pytest test_save_and_test_generator.py::TestSaveAndTestGenerator -v"
echo "pytest test_save_and_test_generator.py::TestGeneratorParameterLogic -v"
