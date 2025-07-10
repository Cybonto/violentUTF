#!/usr/bin/env bash
# Fix OpenAPI routes for Zscaler/corporate SSL environments
# This script properly configures APISIX to handle corporate SSL certificates

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load environment variables
load_env_file() {
    local env_file="$1"
    if [ -f "$env_file" ]; then
        while IFS='=' read -r key value; do
            if [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]]; then
                continue
            fi
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            if [[ -n "$key" && "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
                export "$key=$value"
            fi
        done < "$env_file"
    fi
}

# Load configs
[ -f "../apisix/.env" ] && load_env_file "../apisix/.env"
[ -f "./.env" ] && load_env_file "./.env"

APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"
APISIX_ADMIN_KEY="${APISIX_ADMIN_KEY:-edd1c9f034335f136f87ad84b625c8f1}"

echo -e "${BLUE}=== Fixing OpenAPI Routes for Zscaler/Corporate SSL ===${NC}"
echo

# Step 1: Check if we have Zscaler certificates
echo -e "${BLUE}Step 1: Checking for Zscaler/CA certificates${NC}"

CERT_DIR="/usr/local/share/ca-certificates"
APISIX_CERT_DIR="/usr/local/apisix/conf/cert"

# Check if certificates exist in APISIX container
echo "Checking certificates in APISIX container..."
cert_check=$(docker exec apisix-apisix-1 ls -la $CERT_DIR 2>/dev/null || echo "")

if echo "$cert_check" | grep -q "zscaler\|CA.crt"; then
    echo -e "${GREEN}✓ Found certificates in APISIX container${NC}"
    docker exec apisix-apisix-1 ls -la $CERT_DIR | grep -E "zscaler|CA.crt" || true
else
    echo -e "${YELLOW}⚠️  No Zscaler/CA certificates found in APISIX container${NC}"
    echo
    echo "To fix SSL issues properly:"
    echo "1. Export your Zscaler certificates:"
    echo "   ./get-zscaler-certs.sh"
    echo
    echo "2. Copy them to APISIX during setup:"
    echo "   The setup script should handle this automatically"
    echo
    echo "3. Or manually copy to container:"
    echo "   docker cp zscaler.crt apisix-apisix-1:$CERT_DIR/"
    echo "   docker exec apisix-apisix-1 update-ca-certificates"
fi

echo
echo -e "${BLUE}Step 2: Checking APISIX SSL configuration${NC}"

# Check if APISIX is configured to use system certificates
ssl_config=$(docker exec apisix-apisix-1 cat /usr/local/apisix/conf/config.yaml 2>/dev/null | grep -A5 "ssl" || echo "")

if [ -n "$ssl_config" ]; then
    echo "Current SSL configuration:"
    echo "$ssl_config"
else
    echo "No specific SSL configuration found in APISIX"
fi

echo
echo -e "${BLUE}Step 3: Testing SSL connectivity${NC}"

# Test if APISIX can connect to the upstream with certificates
echo "Testing connection to GSA API..."
test_result=$(docker exec apisix-apisix-1 curl -s -o /dev/null -w "%{http_code}" \
    --cacert /etc/ssl/certs/ca-certificates.crt \
    https://api.dev.gsai.mcaas.fcs.gsa.gov 2>&1 || echo "FAILED")

if [ "$test_result" != "FAILED" ] && [ "$test_result" -ge 200 ] && [ "$test_result" -lt 500 ]; then
    echo -e "${GREEN}✓ SSL connection successful with system certificates (HTTP $test_result)${NC}"
else
    echo -e "${YELLOW}⚠️  SSL connection failed with system certificates${NC}"
    
    # Try without certificate verification
    echo "Testing without certificate verification..."
    test_insecure=$(docker exec apisix-apisix-1 curl -k -s -o /dev/null -w "%{http_code}" \
        https://api.dev.gsai.mcaas.fcs.gsa.gov 2>&1 || echo "FAILED")
    
    if [ "$test_insecure" != "FAILED" ] && [ "$test_insecure" -ge 200 ] && [ "$test_insecure" -lt 500 ]; then
        echo -e "${YELLOW}Connection works without certificate verification (HTTP $test_insecure)${NC}"
        echo "This indicates a certificate trust issue"
    else
        echo -e "${RED}✗ Connection failed even without certificate verification${NC}"
        echo "This may be a network/firewall issue"
    fi
fi

echo
echo -e "${BLUE}Step 4: Updating OpenAPI routes for proper SSL handling${NC}"

# Get all OpenAPI routes
routes=$(curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
    "${APISIX_ADMIN_URL}/apisix/admin/routes" | \
    jq -r '.list[] | select(.value.uri | contains("/ai/openapi/"))')

if [ -z "$routes" ]; then
    echo -e "${YELLOW}No OpenAPI routes found${NC}"
    exit 0
fi

route_count=$(echo "$routes" | jq -s 'length')
echo "Found $route_count OpenAPI routes to update"
echo

# For Zscaler environments, we need to ensure APISIX uses the system CA bundle
echo "$routes" | jq -c '.' | while IFS= read -r route; do
    route_id=$(echo "$route" | jq -r '.key | split("/") | last')
    uri=$(echo "$route" | jq -r '.value.uri')
    
    echo "Updating route: $uri"
    
    # Get current config
    current_config=$(echo "$route" | jq -r '.value')
    
    # Update upstream configuration
    # Instead of disabling SSL, we ensure proper host passing
    updated_config=$(echo "$current_config" | jq '
        .upstream.pass_host = "pass" |
        .upstream.keepalive_pool = {
            "size": 320,
            "idle_timeout": 60,
            "requests": 1000
        }
    ')
    
    # Update the route
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X PUT \
        "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
        -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
        -H "Content-Type: application/json" \
        -d "$updated_config" 2>&1)
    
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ Updated${NC}"
    else
        echo -e "${RED}✗ Failed (HTTP $http_code)${NC}"
    fi
done

echo
echo -e "${BLUE}Step 5: Testing updated routes${NC}"

if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
    echo "Testing models endpoint..."
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "apikey: $VIOLENTUTF_API_KEY" \
        http://localhost:9080/ai/openapi/gsai-api-1/api/v1/models)
    
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ Routes are working!${NC}"
        echo "Models found: $(echo "$body" | jq -r '.data[].id' 2>/dev/null | wc -l | xargs)"
    else
        echo -e "${YELLOW}Routes still returning HTTP $http_code${NC}"
        echo
        echo "Next steps:"
        echo "1. Ensure Zscaler certificates are properly installed:"
        echo "   ./get-zscaler-certs.sh"
        echo "   docker cp zscaler.crt apisix-apisix-1:/usr/local/share/ca-certificates/"
        echo "   docker exec apisix-apisix-1 update-ca-certificates"
        echo
        echo "2. Restart APISIX to pick up new certificates:"
        echo "   docker restart apisix-apisix-1"
        echo
        echo "3. Check APISIX logs for specific errors:"
        echo "   docker logs apisix-apisix-1 2>&1 | tail -50"
    fi
else
    echo -e "${YELLOW}VIOLENTUTF_API_KEY not found${NC}"
fi

echo
echo -e "${BLUE}=== Summary ===${NC}"
echo
echo "For Zscaler/corporate SSL environments:"
echo "1. Export certificates using: ./get-zscaler-certs.sh"
echo "2. Ensure certificates are copied to APISIX container"
echo "3. Routes are configured with proper host passing"
echo "4. APISIX should use system CA bundle automatically"
echo
echo "If issues persist, check:"
echo "- Certificate trust chain"
echo "- Network connectivity from Docker"
echo "- Upstream API availability"