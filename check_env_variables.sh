#!/bin/bash

# Environment Variable Check Script
# This script helps diagnose environment variable configuration issues

echo "=== Environment Variable Configuration Check ==="
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to check file
check_file() {
    local file=$1
    local desc=$2
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} Found $desc: $file"
        return 0
    else
        echo -e "${RED}✗${NC} Missing $desc: $file"
        return 1
    fi
}

# Function to check variable
check_var() {
    local var_name=$1
    local var_value="${!var_name:-}"
    if [ -n "$var_value" ]; then
        if [[ "$var_name" == *"TOKEN"* ]] || [[ "$var_name" == *"KEY"* ]] || [[ "$var_name" == *"SECRET"* ]]; then
            echo -e "  ${GREEN}✓${NC} $var_name: [SET - ${#var_value} chars]"
        else
            echo -e "  ${GREEN}✓${NC} $var_name: $var_value"
        fi
        return 0
    else
        echo -e "  ${RED}✗${NC} $var_name: NOT SET"
        return 1
    fi
}

echo "Step 1: Check Environment Files"
echo "=============================="

check_file "ai-tokens.env" "AI tokens configuration"
check_file "apisix/.env" "APISIX configuration"
check_file "violentutf_api/fastapi_app/.env" "FastAPI configuration"

echo
echo "Step 2: Load and Check Variables"
echo "==============================="

# Load variables
echo "Loading environment variables..."
set -a
[ -f "ai-tokens.env" ] && source ai-tokens.env
[ -f "apisix/.env" ] && source apisix/.env
[ -f "violentutf_api/fastapi_app/.env" ] && source violentutf_api/fastapi_app/.env
set +a

echo
echo "Critical Variables:"
check_var "APISIX_ADMIN_KEY"
check_var "VIOLENTUTF_API_KEY"
check_var "OPENAPI_ENABLED"

echo
echo "GSAi Configuration (OPENAPI_1_*):"
check_var "OPENAPI_1_ENABLED"
check_var "OPENAPI_1_ID"
check_var "OPENAPI_1_NAME"
check_var "OPENAPI_1_BASE_URL"
check_var "OPENAPI_1_AUTH_TYPE"
check_var "OPENAPI_1_AUTH_TOKEN"
check_var "OPENAPI_1_MODELS"

echo
echo "Step 3: Check Docker Environment"
echo "==============================="

if docker ps | grep -q violentutf_api; then
    echo -e "${GREEN}✓${NC} FastAPI container is running"
    
    echo
    echo "Variables in FastAPI container:"
    for var in OPENAPI_ENABLED OPENAPI_1_ENABLED OPENAPI_1_ID APISIX_ADMIN_KEY; do
        value=$(docker exec violentutf_api printenv "$var" 2>/dev/null || echo "NOT SET")
        if [ "$value" != "NOT SET" ]; then
            if [[ "$var" == *"KEY"* ]] || [[ "$var" == *"TOKEN"* ]]; then
                echo -e "  ${GREEN}✓${NC} $var: [SET - ${#value} chars]"
            else
                echo -e "  ${GREEN}✓${NC} $var: $value"
            fi
        else
            echo -e "  ${RED}✗${NC} $var: NOT SET in container"
        fi
    done
else
    echo -e "${RED}✗${NC} FastAPI container is not running"
fi

echo
echo "Step 4: Check Docker Compose Files"
echo "================================="

check_file "apisix/docker-compose.yml" "Main compose file"
check_file "apisix/docker-compose.override.yml" "Override file"

if [ -f "apisix/docker-compose.override.yml" ]; then
    echo
    echo "Override file contains:"
    grep -E "OPENAPI_1_|APISIX_ADMIN_KEY" apisix/docker-compose.override.yml | head -10
fi

echo
echo "Step 5: Recommendations"
echo "======================"

if [ ! -f "apisix/docker-compose.override.yml" ]; then
    echo -e "${YELLOW}!${NC} No docker-compose.override.yml found"
    echo "  Run fix_phase2_implementation_v2.sh to create it"
elif ! docker exec violentutf_api printenv OPENAPI_1_ID &>/dev/null; then
    echo -e "${YELLOW}!${NC} Environment variables not in container"
    echo "  Restart containers: cd apisix && docker compose down && docker compose up -d"
fi

echo
echo "To manually test variable loading:"
echo "  docker exec violentutf_api env | grep -E 'OPENAPI|APISIX_ADMIN'"