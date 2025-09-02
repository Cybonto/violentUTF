#!/usr/bin/env bash
# Install Zscaler certificates into APISIX container

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Installing Zscaler Certificates in APISIX ===${NC}"
echo

# Step 1: Check if certificates exist locally
echo -e "${BLUE}Step 1: Checking for local certificates${NC}"

CERT_FILES=()
if [ -f "../zscaler.crt" ]; then
    CERT_FILES+=("../zscaler.crt")
    echo -e "${GREEN}✓ Found zscaler.crt${NC}"
fi

if [ -f "../CA.crt" ]; then
    CERT_FILES+=("../CA.crt")
    echo -e "${GREEN}✓ Found CA.crt${NC}"
fi

if [ -f "../violentutf_api/fastapi_app/zscaler.crt" ]; then
    CERT_FILES+=("../violentutf_api/fastapi_app/zscaler.crt")
    echo -e "${GREEN}✓ Found zscaler.crt in FastAPI directory${NC}"
fi

if [ -f "../violentutf_api/fastapi_app/CA.crt" ]; then
    CERT_FILES+=("../violentutf_api/fastapi_app/CA.crt")
    echo -e "${GREEN}✓ Found CA.crt in FastAPI directory${NC}"
fi

if [ ${#CERT_FILES[@]} -eq 0 ]; then
    echo -e "${RED}✗ No certificate files found${NC}"
    echo
    echo "Please run from the project root:"
    echo "  ./get-zscaler-certs.sh"
    exit 1
fi

echo
echo -e "${BLUE}Step 2: Copying certificates to APISIX container${NC}"

# Copy certificates to APISIX container
for cert in "${CERT_FILES[@]}"; do
    filename=$(basename "$cert")
    echo "Copying $filename to APISIX container..."

    if docker cp "$cert" apisix-apisix-1:/usr/local/share/ca-certificates/; then
        echo -e "${GREEN}✓ Copied $filename${NC}"
    else
        echo -e "${RED}✗ Failed to copy $filename${NC}"
    fi
done

echo
echo -e "${BLUE}Step 3: Updating certificate store in APISIX${NC}"

# Update CA certificates in container
echo "Updating CA certificates..."
if docker exec apisix-apisix-1 update-ca-certificates 2>/dev/null; then
    echo -e "${GREEN}✓ Certificate store updated${NC}"
else
    echo -e "${YELLOW}⚠️  update-ca-certificates not available in APISIX container${NC}"
    echo "Certificates copied but may need manual configuration"
fi

echo
echo -e "${BLUE}Step 4: Testing with wget (APISIX doesn't have curl)${NC}"

# Test connectivity using wget (available in APISIX container)
echo "Testing HTTPS connectivity..."
test_result=$(docker exec apisix-apisix-1 wget -q -O /dev/null -S https://api.dev.gsai.mcaas.fcs.gsa.gov 2>&1 | grep "HTTP/" | tail -1 || echo "FAILED")

if [[ "$test_result" == *"200"* ]] || [[ "$test_result" == *"403"* ]] || [[ "$test_result" == *"401"* ]]; then
    echo -e "${GREEN}✓ HTTPS connectivity working (got HTTP response)${NC}"
    echo "Response: $test_result"
else
    echo -e "${YELLOW}⚠️  HTTPS connectivity test inconclusive${NC}"
    echo "Response: $test_result"
    echo
    echo "Testing with --no-check-certificate..."
    test_insecure=$(docker exec apisix-apisix-1 wget -q -O /dev/null -S --no-check-certificate https://api.dev.gsai.mcaas.fcs.gsa.gov 2>&1 | grep "HTTP/" | tail -1 || echo "FAILED")
    echo "Response without cert check: $test_insecure"
fi

echo
echo -e "${BLUE}Step 5: Restarting APISIX to apply changes${NC}"

docker restart apisix-apisix-1 >/dev/null 2>&1
echo "Waiting for APISIX to restart..."
sleep 5

# Check if APISIX is healthy
if docker ps | grep -q apisix-apisix-1; then
    echo -e "${GREEN}✓ APISIX restarted successfully${NC}"
else
    echo -e "${RED}✗ APISIX failed to restart${NC}"
    echo "Check logs: docker logs apisix-apisix-1"
fi

echo
echo -e "${BLUE}=== Certificate Installation Complete ===${NC}"
echo
echo "Next steps:"
echo "1. Test your OpenAPI routes again"
echo "2. If still getting 404, check APISIX logs:"
echo "   docker logs apisix-apisix-1 2>&1 | tail -50"
echo "3. Verify routes are configured:"
echo "   ./check_openapi_routes.sh"
