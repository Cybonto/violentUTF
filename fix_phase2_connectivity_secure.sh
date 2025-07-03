#!/bin/bash

# Phase 2 Connectivity Verification Script for Environment B (Secure Version)
# This script verifies APISIX admin API connectivity with enhanced security
# 
# IMPORTANT: This script should be run in Environment B where GSAi is configured
# It will NOT work correctly in Environment A

set -euo pipefail  # Enhanced error handling with undefined variable protection

# Script configuration
readonly SCRIPT_NAME="$(basename "$0")"
readonly LOG_DIR="/tmp/violentutf_logs"
readonly LOG_FILE="${LOG_DIR}/phase2_verify_$(date +%Y%m%d_%H%M%S).log"

# Create log directory
mkdir -p "$LOG_DIR"

# Setup logging
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "=== Phase 2: APISIX Admin API Connectivity Verification (Environment B) ==="
echo "Log file: $LOG_FILE"
echo "Started at: $(date)"
echo

# Colors for output
readonly GREEN='\033[0;32m'
readonly RED='\033[0;31m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" -eq 0 ]; then
        echo -e "${GREEN}✅ $message${NC}"
    else
        echo -e "${RED}❌ $message${NC}"
    fi
}

# Function to validate input
validate_input() {
    local input=$1
    local pattern=$2
    local name=$3
    
    if [[ ! "$input" =~ $pattern ]]; then
        echo -e "${RED}❌ Invalid $name format${NC}"
        return 1
    fi
    return 0
}

# Cleanup function
cleanup() {
    echo
    echo "Script completed at: $(date)"
}
trap cleanup EXIT

# Security check: Validate running environment
if [ ! -f "ai-tokens.env" ]; then
    echo -e "${YELLOW}⚠️  Warning: ai-tokens.env not found${NC}"
    echo "This script requires Environment B configuration with GSAi settings"
fi

# Check required commands
echo "Checking required commands..."
for cmd in docker curl jq; do
    if ! command -v "$cmd" &> /dev/null; then
        print_status 1 "Required command '$cmd' not found"
        echo "Please install $cmd before running this script"
        exit 1
    fi
done
print_status 0 "All required commands found"

# Load environment variables with validation
echo
echo "Loading environment configuration..."

# Function to safely load environment files
load_env_file() {
    local env_file=$1
    if [ -f "$env_file" ]; then
        # Check file permissions
        local perms=$(stat -c "%a" "$env_file" 2>/dev/null || stat -f "%OLp" "$env_file" 2>/dev/null)
        if [ "$perms" != "600" ] && [ "$perms" != "400" ]; then
            echo -e "${YELLOW}⚠️  Warning: $env_file has permissions $perms (should be 600 or 400)${NC}"
        fi
        
        # Source file with validation
        set +e
        source "$env_file"
        local source_result=$?
        set -e
        
        if [ $source_result -eq 0 ]; then
            print_status 0 "Loaded $env_file"
        else
            print_status 1 "Failed to load $env_file"
            return 1
        fi
    else
        return 1
    fi
}

# Load environment files
load_env_file "apisix/.env" || {
    echo "Please ensure you're in the ViolentUTF root directory in Environment B"
    exit 1
}
load_env_file "ai-tokens.env" || echo "ai-tokens.env not loaded (optional)"

# Validate critical environment variables
echo
echo "Validating environment variables..."

# Validate APISIX_ADMIN_KEY
if [ -z "${APISIX_ADMIN_KEY:-}" ]; then
    print_status 1 "APISIX_ADMIN_KEY not found"
    exit 1
else
    # Validate format (alphanumeric, dash, underscore only)
    if validate_input "$APISIX_ADMIN_KEY" '^[a-zA-Z0-9_-]+$' "APISIX_ADMIN_KEY"; then
        print_status 0 "APISIX_ADMIN_KEY validated [${#APISIX_ADMIN_KEY} chars]"
    else
        exit 1
    fi
fi

echo
echo "Step 1: Verify Current Configuration"
echo "===================================="

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^violentutf_api$"; then
    print_status 1 "FastAPI container is not running"
    echo "Please start services with: cd apisix && docker compose up -d"
    exit 1
fi

# Check current APISIX_ADMIN_URL in container
admin_url=$(docker exec violentutf_api printenv APISIX_ADMIN_URL 2>/dev/null || echo "NOT SET")
if [ "$admin_url" = "NOT SET" ] || [ -z "$admin_url" ]; then
    print_status 1 "APISIX_ADMIN_URL is not set in container"
else
    print_status 0 "APISIX_ADMIN_URL: $admin_url"
fi

echo
echo "Step 2: Test Connectivity with Authentication"
echo "==========================================="

# Create temporary file for API key (more secure than command line)
temp_key_file=$(mktemp)
chmod 600 "$temp_key_file"
echo "$APISIX_ADMIN_KEY" > "$temp_key_file"

# Test connectivity using file-based auth
echo "Testing connectivity to APISIX admin API..."
test_result=$(docker exec -i violentutf_api sh -c 'curl -s --max-time 5 -o /dev/null -w "%{http_code}" -H "X-API-KEY: $(cat)" http://apisix:9180/apisix/admin/routes' < "$temp_key_file" 2>/dev/null || echo "000")

# Clean up temp file
rm -f "$temp_key_file"

if [ "$test_result" = "200" ]; then
    print_status 0 "Successfully connected to APISIX admin API"
elif [ "$test_result" = "401" ]; then
    print_status 1 "Authentication failed (HTTP 401)"
    echo "   The API key may be incorrect or expired"
else
    print_status 1 "Failed to connect (HTTP $test_result)"
    echo "   Check if APISIX is running and accessible"
fi

echo
echo "Step 3: Verify Route Discovery"
echo "=============================="

if [ "$test_result" = "200" ]; then
    # Create temp file for API key again
    temp_key_file=$(mktemp)
    chmod 600 "$temp_key_file"
    echo "$APISIX_ADMIN_KEY" > "$temp_key_file"
    
    # Get route count
    routes_response=$(docker exec -i violentutf_api sh -c 'curl -s --max-time 5 -H "X-API-KEY: $(cat)" http://apisix:9180/apisix/admin/routes' < "$temp_key_file" 2>/dev/null || echo "{}")
    routes_count=$(echo "$routes_response" | jq '.list | length' 2>/dev/null || echo "0")
    
    rm -f "$temp_key_file"
    
    if [ "$routes_count" -gt 0 ]; then
        print_status 0 "Route discovery working - found $routes_count routes"
        
        # Check for OpenAPI routes
        openapi_count=$(echo "$routes_response" | jq '[.list[]?.value | select(.uri | contains("/openapi/"))] | length' 2>/dev/null || echo "0")
        if [ "$openapi_count" -gt 0 ]; then
            print_status 0 "Found $openapi_count OpenAPI routes"
        else
            echo "   No OpenAPI routes found (expected in Environment A)"
        fi
    else
        print_status 1 "Route discovery failed or no routes found"
    fi
else
    echo "Skipping route discovery due to connectivity issues"
fi

echo
echo "Step 4: Security Recommendations"
echo "==============================="

# Check file permissions
echo "Checking configuration file permissions..."
for file in "ai-tokens.env" "apisix/.env" "violentutf_api/fastapi_app/.env"; do
    if [ -f "$file" ]; then
        perms=$(stat -c "%a" "$file" 2>/dev/null || stat -f "%OLp" "$file" 2>/dev/null)
        if [ "$perms" = "600" ] || [ "$perms" = "400" ]; then
            print_status 0 "$file has secure permissions ($perms)"
        else
            print_status 1 "$file has insecure permissions ($perms)"
            echo "   Fix with: chmod 600 $file"
        fi
    fi
done

echo
echo "=== Phase 2 Verification Summary ==="

if [ "$test_result" = "200" ]; then
    print_status 0 "APISIX admin API connectivity is working correctly"
    echo "   - FastAPI can discover routes through APISIX"
    echo "   - Authentication is properly configured"
    echo "   - Ready for GSAi integration testing"
else
    print_status 1 "Issues detected with APISIX admin API connectivity"
    echo
    echo "Troubleshooting steps:"
    echo "1. Check container status: docker ps | grep -E '(apisix|violentutf_api)'"
    echo "2. Review APISIX logs: docker logs apisix-apisix-1 --tail 50"
    echo "3. Verify network connectivity: docker network inspect vutf-network"
    echo "4. Check API key configuration in apisix/.env"
fi

echo
echo "Security Notes:"
echo "- Always use secure file permissions (600) for configuration files"
echo "- Never expose API keys in command lines or logs"
echo "- Regularly rotate API keys and tokens"
echo "- Monitor logs for unauthorized access attempts"