#!/bin/bash
# Debug script to diagnose OpenAPI setup issues
# This script checks all the conditions that could prevent OpenAPI routes from being created

echo "🔍 OpenAPI Setup Diagnostic Tool"
echo "================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check a condition and report status
check_condition() {
    local description="$1"
    local condition="$2"
    local value="$3"
    
    echo -n "Checking $description... "
    if [ "$condition" = "true" ] || [ "$condition" = "exists" ]; then
        echo -e "${GREEN}✅ PASS${NC} ($value)"
    elif [ "$condition" = "warning" ]; then
        echo -e "${YELLOW}⚠️  WARNING${NC} ($value)"
    else
        echo -e "${RED}❌ FAIL${NC} ($value)"
    fi
}

echo "📋 Step 1: Basic Environment Check"
echo "-----------------------------------"

# Check if ai-tokens.env exists
if [ -f "ai-tokens.env" ]; then
    check_condition "ai-tokens.env file" "exists" "Found"
else
    check_condition "ai-tokens.env file" "false" "File not found"
    echo ""
    echo -e "${RED}❌ Cannot continue without ai-tokens.env${NC}"
    exit 1
fi

# Load ai-tokens.env
echo ""
echo "📋 Step 2: Loading ai-tokens.env"
echo "--------------------------------"
source ai-tokens.env 2>/dev/null || true

# Check main OPENAPI_ENABLED flag
if [ "$OPENAPI_ENABLED" = "true" ]; then
    check_condition "OPENAPI_ENABLED" "true" "$OPENAPI_ENABLED"
else
    check_condition "OPENAPI_ENABLED" "false" "${OPENAPI_ENABLED:-unset}"
    echo ""
    echo -e "${RED}❌ OPENAPI_ENABLED is not set to 'true' - this will cause setup_openapi_routes() to exit early${NC}"
    echo -e "${YELLOW}💡 Fix: Set OPENAPI_ENABLED=true in ai-tokens.env${NC}"
fi

echo ""
echo "📋 Step 3: Individual Provider Check"
echo "------------------------------------"

# Check individual OpenAPI providers (1-10)
found_providers=0
for i in {1..10}; do
    enabled_var="OPENAPI_${i}_ENABLED"
    id_var="OPENAPI_${i}_ID"
    base_url_var="OPENAPI_${i}_BASE_URL"
    spec_path_var="OPENAPI_${i}_SPEC_PATH"
    
    enabled_val="${!enabled_var}"
    id_val="${!id_var}"
    base_url_val="${!base_url_var}"
    spec_path_val="${!spec_path_var}"
    
    if [ "$enabled_val" = "true" ]; then
        found_providers=$((found_providers + 1))
        echo ""
        echo -e "${BLUE}Provider $i Configuration:${NC}"
        check_condition "  OPENAPI_${i}_ENABLED" "true" "$enabled_val"
        
        if [ -n "$id_val" ]; then
            check_condition "  OPENAPI_${i}_ID" "true" "$id_val"
        else
            check_condition "  OPENAPI_${i}_ID" "false" "unset"
        fi
        
        if [ -n "$base_url_val" ]; then
            check_condition "  OPENAPI_${i}_BASE_URL" "true" "$base_url_val"
        else
            check_condition "  OPENAPI_${i}_BASE_URL" "false" "unset"
        fi
        
        if [ -n "$spec_path_val" ]; then
            check_condition "  OPENAPI_${i}_SPEC_PATH" "true" "$spec_path_val"
        else
            check_condition "  OPENAPI_${i}_SPEC_PATH" "false" "unset"
        fi
        
        # Test connectivity to the OpenAPI spec
        if [ -n "$base_url_val" ] && [ -n "$spec_path_val" ]; then
            full_spec_url="${base_url_val}${spec_path_val}"
            echo -n "  Testing spec URL connectivity... "
            if curl -s --connect-timeout 5 --max-time 10 "$full_spec_url" > /dev/null 2>&1; then
                echo -e "${GREEN}✅ PASS${NC} ($full_spec_url)"
            else
                echo -e "${RED}❌ FAIL${NC} ($full_spec_url - not reachable)"
            fi
        fi
    fi
done

if [ $found_providers -eq 0 ]; then
    echo ""
    echo -e "${RED}❌ No enabled OpenAPI providers found${NC}"
    echo -e "${YELLOW}💡 Fix: Set OPENAPI_X_ENABLED=true for at least one provider (X=1-10)${NC}"
else
    echo ""
    echo -e "${GREEN}✅ Found $found_providers enabled OpenAPI provider(s)${NC}"
fi

echo ""
echo "📋 Step 4: APISIX Connectivity Check"
echo "------------------------------------"

# Check APISIX configuration
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
APISIX_ADMIN_KEY="${APISIX_ADMIN_KEY:-}"

if [ -f "apisix/.env" ]; then
    check_condition "apisix/.env file" "exists" "Found"
    source apisix/.env 2>/dev/null || true
else
    check_condition "apisix/.env file" "false" "Not found"
fi

check_condition "APISIX_ADMIN_URL" "true" "$APISIX_ADMIN_URL"

if [ -n "$APISIX_ADMIN_KEY" ]; then
    check_condition "APISIX_ADMIN_KEY" "true" "Set (${#APISIX_ADMIN_KEY} chars)"
else
    check_condition "APISIX_ADMIN_KEY" "false" "Not set"
fi

# Test APISIX connectivity
echo -n "Testing APISIX admin API connectivity... "
if curl -s --connect-timeout 5 --max-time 10 "${APISIX_ADMIN_URL}/apisix/admin/routes" \
    -H "X-API-KEY: ${APISIX_ADMIN_KEY}" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PASS${NC}"
else
    echo -e "${RED}❌ FAIL${NC} (APISIX admin API not reachable)"
fi

echo ""
echo "📋 Step 5: Current OpenAPI Routes"
echo "---------------------------------"

# Check existing routes
if [ -n "$APISIX_ADMIN_KEY" ]; then
    routes_response=$(curl -s "${APISIX_ADMIN_URL}/apisix/admin/routes" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        openapi_routes=$(echo "$routes_response" | grep -o '"id":"openapi-[^"]*"' | wc -l)
        if [ "$openapi_routes" -gt 0 ]; then
            echo -e "${GREEN}✅ Found $openapi_routes existing OpenAPI route(s)${NC}"
            echo "Current OpenAPI routes:"
            echo "$routes_response" | grep -o '"id":"openapi-[^"]*"' | sed 's/"id":"//;s/"//' | sed 's/^/  - /'
        else
            echo -e "${YELLOW}⚠️  No existing OpenAPI routes found${NC}"
        fi
    else
        echo -e "${RED}❌ Could not query APISIX routes${NC}"
    fi
else
    echo -e "${RED}❌ Cannot check routes without APISIX_ADMIN_KEY${NC}"
fi

echo ""
echo "📋 Step 6: FastAPI Settings Check"
echo "---------------------------------"

# Check if FastAPI service is running and what it reports
if curl -s --connect-timeout 5 --max-time 10 "http://localhost:8000/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ FastAPI service is reachable${NC}"
    
    # Try to get the settings from the FastAPI service if we can
    # This would require authentication, so we'll skip this for now
    echo -e "${YELLOW}⚠️  FastAPI settings check requires authentication - skipping${NC}"
else
    echo -e "${RED}❌ FastAPI service not reachable${NC}"
fi

echo ""
echo "📋 Summary and Recommendations"
echo "=============================="

if [ "$OPENAPI_ENABLED" != "true" ]; then
    echo -e "${RED}🚨 CRITICAL: OPENAPI_ENABLED is not set to 'true'${NC}"
    echo "   This is the most likely cause of the issue."
    echo "   The setup_openapi_routes() function exits early if this is not exactly 'true'."
    echo ""
    echo -e "${YELLOW}💡 RECOMMENDED FIX:${NC}"
    echo "   1. Edit ai-tokens.env"
    echo "   2. Change OPENAPI_ENABLED=false to OPENAPI_ENABLED=true"
    echo "   3. Re-run setup: ./setup_macos.sh"
    echo ""
elif [ $found_providers -eq 0 ]; then
    echo -e "${RED}🚨 CRITICAL: No enabled OpenAPI providers found${NC}"
    echo "   Even with OPENAPI_ENABLED=true, no individual providers are enabled."
    echo ""
    echo -e "${YELLOW}💡 RECOMMENDED FIX:${NC}"
    echo "   1. Edit ai-tokens.env"
    echo "   2. Set OPENAPI_X_ENABLED=true for at least one provider (X=1-10)"
    echo "   3. Configure the required fields for that provider"
    echo "   4. Re-run setup: ./setup_macos.sh"
    echo ""
else
    echo -e "${GREEN}✅ Configuration looks correct${NC}"
    echo "   OpenAPI is enabled and providers are configured."
    echo ""
    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo -e "${YELLOW}💡 POSSIBLE ISSUE: APISIX_ADMIN_KEY not found${NC}"
        echo "   This could prevent route creation."
        echo "   Try running the full setup to regenerate APISIX configuration."
    fi
fi

echo ""
echo "To run the OpenAPI setup manually:"
echo "  ./refresh-openapi-routes.sh"
echo ""
echo "To run full setup:"
echo "  ./setup_macos.sh"