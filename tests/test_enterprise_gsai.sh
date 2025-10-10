#!/usr/bin/env bash
# test_enterprise_gsai.sh - Manual test script for enterprise GSAi HTTPS setup

echo "🔒 Enterprise GSAi HTTPS Test Script"
echo "===================================="
echo ""
echo "This script helps verify GSAi HTTPS configuration in enterprise environments"
echo ""

# Configuration
GSAI_URL="${GSAI_URL:-https://gsai.enterprise.com}"
GSAI_TOKEN="${GSAI_TOKEN:-your-api-token}"
CA_CERT_PATH="${CA_CERT_PATH:-}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test functions
test_direct_connection() {
    echo "1️⃣  Testing direct HTTPS connection to GSAi..."
    echo "   URL: $GSAI_URL"

    local curl_opts="-s -I --max-time 10"

    if [ -n "$CA_CERT_PATH" ] && [ -f "$CA_CERT_PATH" ]; then
        echo "   Using CA certificate: $CA_CERT_PATH"
        curl_opts="$curl_opts --cacert $CA_CERT_PATH"
    else
        echo "   Using system CA certificates"
    fi

    if curl $curl_opts "$GSAI_URL/health" >/dev/null 2>&1; then
        echo -e "   ${GREEN}✅ Direct HTTPS connection successful${NC}"
        return 0
    else
        echo -e "   ${RED}❌ Direct HTTPS connection failed${NC}"
        echo "   Error details:"
        curl -v $curl_opts "$GSAI_URL/health" 2>&1 | grep -i "ssl\|certificate" | head -5
        return 1
    fi
}

test_api_endpoint() {
    echo ""
    echo "2️⃣  Testing GSAi API endpoint..."

    local curl_opts="-s --max-time 10"

    if [ -n "$CA_CERT_PATH" ] && [ -f "$CA_CERT_PATH" ]; then
        curl_opts="$curl_opts --cacert $CA_CERT_PATH"
    fi

    # Test models endpoint
    local response=$(curl $curl_opts -H "Authorization: Bearer $GSAI_TOKEN" "$GSAI_URL/api/v1/models" 2>/dev/null)

    if echo "$response" | grep -q "model"; then
        echo -e "   ${GREEN}✅ API endpoint accessible${NC}"
        echo "   Models found: $(echo "$response" | grep -o '"id"' | wc -l)"
        return 0
    else
        echo -e "   ${RED}❌ API endpoint not accessible${NC}"
        return 1
    fi
}

test_apisix_route() {
    echo ""
    echo "3️⃣  Testing APISIX route to GSAi..."

    # Check if APISIX is running
    if ! curl -s http://localhost:9080/health >/dev/null 2>&1; then
        echo -e "   ${YELLOW}⚠️  APISIX not running - skipping route test${NC}"
        return 0
    fi

    # Test the AI route
    local test_payload='{
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello"}],
        "max_tokens": 10
    }'

    local response=$(curl -s --max-time 10 \
        -X POST http://localhost:9080/ai/gsai-api-1/chat/completions \
        -H "Content-Type: application/json" \
        -d "$test_payload" 2>/dev/null)

    if echo "$response" | grep -q "choices\|error"; then
        if echo "$response" | grep -q "choices"; then
            echo -e "   ${GREEN}✅ APISIX route working correctly${NC}"
        else
            echo -e "   ${YELLOW}⚠️  APISIX route accessible but returned error${NC}"
            echo "   Response: $(echo "$response" | head -c 200)"
        fi
        return 0
    else
        echo -e "   ${RED}❌ APISIX route not working${NC}"
        return 1
    fi
}

check_route_config() {
    echo ""
    echo "4️⃣  Checking APISIX route configuration..."

    # Load APISIX admin key
    if [ -f "../apisix/.env" ]; then
        source ../apisix/.env
    fi

    if [ -z "$APISIX_ADMIN_KEY" ]; then
        echo -e "   ${YELLOW}⚠️  APISIX admin key not found${NC}"
        return 0
    fi

    # Get route 9001 (GSAi route)
    local route=$(curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        http://localhost:9180/apisix/admin/routes/9001 2>/dev/null)

    if echo "$route" | grep -q '"id":"9001"'; then
        echo -e "   ${GREEN}✅ GSAi route found${NC}"

        # Check scheme
        local scheme=$(echo "$route" | grep -o '"scheme":"[^"]*"' | cut -d'"' -f4)
        echo "   Scheme: $scheme"

        # Check SSL verification
        if echo "$route" | grep -q '"tls"'; then
            local ssl_verify=$(echo "$route" | grep -o '"verify":[^,}]*' | cut -d':' -f2)
            echo "   SSL Verify: $ssl_verify"
        fi

        # Check upstream
        local upstream=$(echo "$route" | grep -o '"nodes":{[^}]*}' | head -1)
        echo "   Upstream: $upstream"
    else
        echo -e "   ${YELLOW}⚠️  GSAi route not found${NC}"
    fi
}

verify_certificates() {
    echo ""
    echo "5️⃣  Verifying certificates..."

    # Check system CA certificates
    local ca_locations=(
        "/etc/ssl/certs/ca-certificates.crt"
        "/etc/pki/tls/certs/ca-bundle.crt"
        "/etc/ssl/cert.pem"
    )

    for ca_path in "${ca_locations[@]}"; do
        if [ -f "$ca_path" ]; then
            echo -e "   ${GREEN}✅ Found system CA bundle: $ca_path${NC}"
            break
        fi
    done

    # Check custom CA if provided
    if [ -n "$CA_CERT_PATH" ]; then
        if [ -f "$CA_CERT_PATH" ]; then
            echo -e "   ${GREEN}✅ Custom CA certificate exists: $CA_CERT_PATH${NC}"

            # Verify it's valid
            if openssl x509 -in "$CA_CERT_PATH" -noout 2>/dev/null; then
                echo -e "   ${GREEN}✅ Certificate format is valid${NC}"

                # Show certificate info
                local subject=$(openssl x509 -in "$CA_CERT_PATH" -noout -subject | sed 's/subject=//')
                echo "   Subject: $subject"
            else
                echo -e "   ${RED}❌ Invalid certificate format${NC}"
            fi
        else
            echo -e "   ${RED}❌ Custom CA certificate not found: $CA_CERT_PATH${NC}"
        fi
    fi
}

show_troubleshooting() {
    echo ""
    echo "🔧 Troubleshooting Guide"
    echo "======================="
    echo ""
    echo "If tests are failing:"
    echo ""
    echo "1. SSL Certificate Issues:"
    echo "   - Verify CA certificate path is correct"
    echo "   - Check if certificate is in PEM format"
    echo "   - Ensure certificate is not expired"
    echo "   export CA_CERT_PATH=/path/to/enterprise-ca.crt"
    echo ""
    echo "2. Route Configuration Issues:"
    echo "   - Check ai-tokens.env has correct settings:"
    echo "     OPENAPI_1_BASE_URL=$GSAI_URL"
    echo "     OPENAPI_1_USE_HTTPS=true"
    echo "     OPENAPI_1_SSL_VERIFY=true"
    echo "     OPENAPI_1_CA_CERT_PATH=$CA_CERT_PATH"
    echo ""
    echo "3. Fix route manually:"
    echo "   cd ../setup_macos_files"
    echo "   ./certificate_management.sh import $CA_CERT_PATH"
    echo "   # Then update the route..."
    echo ""
}

# Main execution
main() {
    # Check environment
    if [ "$GSAI_URL" = "https://gsai.enterprise.com" ]; then
        echo -e "${YELLOW}⚠️  Using default URL. Set your actual GSAi URL:${NC}"
        echo "   export GSAI_URL=https://your-gsai-instance.com"
        echo ""
    fi

    if [ "$GSAI_TOKEN" = "your-api-token" ]; then
        echo -e "${YELLOW}⚠️  Using default token. Set your actual API token:${NC}"
        echo "   export GSAI_TOKEN=your-actual-token"
        echo ""
    fi

    # Run tests
    test_direct_connection
    test_api_endpoint
    test_apisix_route
    check_route_config
    verify_certificates

    # Show troubleshooting if any test failed
    if [ $? -ne 0 ]; then
        show_troubleshooting
    fi

    echo ""
    echo "✨ Test complete!"
}

# Run main
main "$@"
