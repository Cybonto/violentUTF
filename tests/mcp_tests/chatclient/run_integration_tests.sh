#!/bin/bash

# Run MCP Integration tests for Phase 1, Task 2

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Running MCP Integration Tests - Phase 1, Task 2"
echo "========================================="

# Change to the script directory
cd "$(dirname "$0")" || exit

# Ensure we're in the right venv
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Using virtual environment: $VIRTUAL_ENV"
else
    echo "WARNING: No virtual environment active"
fi

# Run the tests
echo -e "\n${GREEN}Running test_mcp_integration.py...${NC}"
python -m pytest test_mcp_integration.py -v --tb=short -p no:warnings --confcutdir=.

# Check the exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All MCP Integration tests passed!${NC}"
    echo -e "${GREEN}Phase 1, Task 2 completed successfully.${NC}"
else
    echo -e "\n${RED}✗ Some tests failed!${NC}"
    echo -e "${RED}Please fix the issues before proceeding to the next task.${NC}"
    exit 1
fi

echo -e "\n========================================="
echo "Test Summary:"
echo "- Natural language command parser ✓"
echo "- Context analysis functions ✓"
echo "- Resource search and filtering ✓"
echo "- Test scenario interpreter ✓"
echo "- Dataset integration ✓"
echo "========================================="

# Run all Phase 1 tests together
echo -e "\n${YELLOW}Running all Phase 1 tests...${NC}"
python -m pytest test_mcp_client.py test_mcp_integration.py -v --tb=short -p no:warnings --confcutdir=.

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All Phase 1 tests passed!${NC}"
    echo -e "${GREEN}Phase 1 (Foundation & MCP Client Implementation) completed successfully!${NC}"
else
    echo -e "\n${RED}✗ Some Phase 1 tests failed!${NC}"
    exit 1
fi
