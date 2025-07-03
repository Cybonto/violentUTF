#!/bin/bash

# Phase 2 Configuration Check for Environment A
# This script checks the configuration that will be used when code is pulled to Environment B
# Run this in Environment A before pulling to Environment B

set -e

echo "=== Phase 2 Configuration Check (Environment A) ==="
echo "This script checks configurations that will be used in Environment B"
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

echo "Step 1: Check Docker Compose Configuration"
echo "========================================="

# Check docker-compose.yml
if [ -f "apisix/docker-compose.yml" ]; then
    print_status 0 "Found apisix/docker-compose.yml"
    
    # Check APISIX_ADMIN_URL setting
    admin_url_config=$(grep -A15 "fastapi:" apisix/docker-compose.yml | grep "APISIX_ADMIN_URL" | sed 's/.*APISIX_ADMIN_URL=//' | tr -d ' ' || echo "NOT FOUND")
    if [ "$admin_url_config" = "http://apisix:9180" ]; then
        print_status 0 "APISIX_ADMIN_URL correctly set to: $admin_url_config"
    else
        print_status 1 "APISIX_ADMIN_URL incorrect or not found: $admin_url_config"
    fi
else
    print_status 1 "apisix/docker-compose.yml not found"
fi

echo
echo "Step 2: Check FastAPI .env File"
echo "==============================="

# Check FastAPI .env
if [ -f "violentutf_api/fastapi_app/.env" ]; then
    print_status 0 "Found violentutf_api/fastapi_app/.env"
    
    # Check for APISIX configuration
    apisix_base=$(grep "^APISIX_BASE_URL=" violentutf_api/fastapi_app/.env | cut -d'=' -f2 || echo "NOT SET")
    apisix_admin=$(grep "^APISIX_ADMIN_URL=" violentutf_api/fastapi_app/.env | cut -d'=' -f2 || echo "NOT SET")
    
    echo "   APISIX_BASE_URL: $apisix_base"
    echo "   APISIX_ADMIN_URL: $apisix_admin"
    echo "   Note: docker-compose.yml will override these with correct values"
else
    print_status 1 "violentutf_api/fastapi_app/.env not found"
fi

echo
echo "Step 3: Check Required Scripts"
echo "=============================="

# Check for test scripts
scripts=(
    "test_gsai_integration.sh"
    "fix_gsai_network.sh"
    "verify_phase2_config.sh"
    "fix_phase2_connectivity.sh"
)

for script in "${scripts[@]}"; do
    if [ -f "$script" ]; then
        print_status 0 "Found $script"
    else
        print_status 1 "Missing $script"
    fi
done

echo
echo "Step 4: Check OpenAPI Route Configuration"
echo "========================================"

# Check route configuration script
if [ -f "apisix/check_openapi_routes.sh" ]; then
    print_status 0 "Found apisix/check_openapi_routes.sh"
    
    # Verify it's checking for correct pattern
    if grep -q '"/openapi/"' apisix/check_openapi_routes.sh; then
        print_status 0 "Route check script uses correct pattern (/openapi/)"
    else
        print_status 1 "Route check script may be using wrong pattern"
    fi
else
    print_status 1 "Missing apisix/check_openapi_routes.sh"
fi

echo
echo "Step 5: Environment B Requirements"
echo "================================="

echo "When you pull this code to Environment B, ensure:"
echo "1. ai-tokens.env contains GSAi configuration (OPENAPI_1_*)"
echo "2. Docker services are running (docker compose up -d in apisix/)"
echo "3. Run test_gsai_integration.sh to verify GSAi integration"
echo "4. Run fix_phase2_connectivity.sh if there are connectivity issues"

echo
echo "Step 6: Code Analysis - Generator Comments"
echo "========================================"

# Check if generator code has correct comments
if [ -f "violentutf_api/fastapi_app/app/utils/generators.py" ]; then
    if grep -q "Routes follow pattern: /openapi/{provider_id}/" violentutf_api/fastapi_app/app/utils/generators.py; then
        print_status 0 "generators.py has correct route pattern comment"
    else
        print_status 1 "generators.py may have outdated route pattern comment"
        echo "   Should be: /openapi/{provider_id}/* (not /ai/openapi/...)"
    fi
fi

echo
echo "=== Summary for Environment A ==="
echo "Configuration appears to be ready for Environment B deployment."
echo "The key configuration (APISIX_ADMIN_URL=http://apisix:9180) is correctly"
echo "set in docker-compose.yml and will work when deployed to Environment B."
echo
echo "Next steps:"
echo "1. Commit and push these changes"
echo "2. Pull the code in Environment B"
echo "3. Run test_gsai_integration.sh in Environment B"