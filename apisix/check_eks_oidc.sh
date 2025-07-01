#!/usr/bin/env bash
# Check if the EKS OIDC endpoint is resolvable and accessible

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Checking EKS OIDC Provider Resolution ===${NC}"
echo

OIDC_URL="https://oidc.eks.us-east-1.amazonaws.com/id/A44B5A838D746E276B7356BE3E4D8051"

# Step 1: DNS resolution
echo -e "${BLUE}Step 1: DNS Resolution${NC}"
echo "Resolving: oidc.eks.us-east-1.amazonaws.com"
nslookup oidc.eks.us-east-1.amazonaws.com 2>&1 || echo "DNS lookup failed"
echo

# Step 2: Test from your machine
echo -e "${BLUE}Step 2: Testing OIDC endpoint accessibility${NC}"
echo "Testing: $OIDC_URL/.well-known/openid-configuration"
response=$(curl -s -o /dev/null -w "%{http_code}" "$OIDC_URL/.well-known/openid-configuration" 2>&1 || echo "FAILED")
echo "HTTP response code: $response"

if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ OIDC endpoint is accessible${NC}"
    echo "Getting OIDC configuration..."
    curl -s "$OIDC_URL/.well-known/openid-configuration" | jq . 2>/dev/null | head -20
else
    echo -e "${YELLOW}⚠️  OIDC endpoint returned: $response${NC}"
fi
echo

# Step 3: Test from APISIX container
echo -e "${BLUE}Step 3: Testing from APISIX container${NC}"
echo "Checking if APISIX can resolve the OIDC domain..."
docker exec apisix-apisix-1 nslookup oidc.eks.us-east-1.amazonaws.com 2>&1 || echo "DNS lookup failed in container"
echo

# Step 4: Trace the actual error
echo -e "${BLUE}Step 4: Understanding the error${NC}"
echo
echo "The error 'InvalidIdentityToken: No OpenIDConnect provider found' means:"
echo "1. The GSA API is running on AWS EKS"
echo "2. It's trying to assume an IAM role using IRSA (IAM Roles for Service Accounts)"
echo "3. The OIDC provider is not configured correctly in their AWS account"
echo
echo "This is an internal GSA API configuration issue where:"
echo "- Their EKS cluster has OIDC provider: $OIDC_URL"
echo "- But this provider is not registered in their AWS IAM"
echo "- Or the service account doesn't have the correct annotations"
echo
echo -e "${YELLOW}This CANNOT be fixed from your side. The GSA team needs to:${NC}"
echo "1. Register the OIDC provider in AWS IAM:"
echo "   aws iam create-open-id-connect-provider --url $OIDC_URL"
echo "2. Or fix their service account annotations"
echo "3. Or fix their pod's IAM role assumption"