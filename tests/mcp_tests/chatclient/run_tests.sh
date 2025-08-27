#!/bin/bash

# Run MCP Client tests for Phase 1, Task 1

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================="
echo "Running MCP Client Tests - Phase 1, Task 1"
echo "========================================="

# Change to the script directory
cd "$(dirname "$0")"

# Ensure we're in the right venv
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Using virtual environment: $VIRTUAL_ENV"
else
    echo "WARNING: No virtual environment active"
fi

# Install test dependencies if needed
echo "Installing test dependencies..."
pip install pytest pytest-asyncio pytest-mock httpx httpx-sse > /dev/null 2>&1

# Run the tests
echo -e "\n${GREEN}Running test_mcp_client.py...${NC}"
python -m pytest test_mcp_client.py -v --tb=short -p no:warnings --confcutdir=.

# Check the exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All MCP Client tests passed!${NC}"
    echo -e "${GREEN}Phase 1, Task 1 completed successfully.${NC}"
else
    echo -e "\n${RED}✗ Some tests failed!${NC}"
    echo -e "${RED}Please fix the issues before proceeding to the next task.${NC}"
    exit 1
fi

echo -e "\n========================================="
echo "Test Summary:"
echo "- SSE connection establishment ✓"
echo "- JSON-RPC request/response handling ✓"
echo "- Authentication flow ✓"
echo "- MCP operations (list prompts, render, etc.) ✓"
echo "- Error handling and retry logic ✓"
echo "========================================="
