#!/usr/bin/env bash
# Test script to run OpenAPI setup directly

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f "ai-tokens.env" ]; then
    echo "Loading AI tokens configuration..."
    source ai-tokens.env
fi

if [ -f "apisix/.env" ]; then
    echo "Loading APISIX configuration..."
    source apisix/.env
fi

echo "OpenAPI_ENABLED: ${OPENAPI_ENABLED:-not set}"
echo "OPENAPI_1_ENABLED: ${OPENAPI_1_ENABLED:-not set}"
echo "OPENAPI_1_BASE_URL: ${OPENAPI_1_BASE_URL:-not set}"

# Source the setup script to get access to functions
source setup_macos.sh

# Run the OpenAPI setup function directly
echo "Calling setup_openapi_routes function..."
setup_openapi_routes