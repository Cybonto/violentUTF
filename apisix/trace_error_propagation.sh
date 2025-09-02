#!/usr/bin/env bash
# Trace how internal AWS errors propagate through the API

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Tracing Error Propagation ===${NC}"
echo

# Load environment
if [ -f "../ai-tokens.env" ]; then
    source ../ai-tokens.env
fi

echo -e "${BLUE}How the AWS error reaches you:${NC}"
echo
echo "1. Your request: POST /api/v1/chat/completions"
echo "   ↓"
echo "2. GSA API receives request with valid Bearer token"
echo "   ↓"
echo "3. GSA API tries to call AWS service (likely Bedrock)"
echo "   ↓"
echo "4. Their code tries to get AWS credentials via IRSA"
echo "   ↓"
echo "5. AWS IAM rejects: 'No OpenIDConnect provider found'"
echo "   ↓"
echo "6. GSA API returns HTTP 500 with the error details"
echo

echo -e "${BLUE}Let's see the full error response:${NC}"
echo

if [ -n "${OPENAPI_1_AUTH_TOKEN:-}" ]; then
    echo "Making direct request to see full error..."
    response=$(curl -s -X POST https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/chat/completions \
        -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "test"}]}' \
        --insecure 2>&1)

    echo "Full error response:"
    echo "$response" | jq . 2>/dev/null || echo "$response"
    echo

    echo -e "${BLUE}What this tells us:${NC}"
    echo
    echo "The GSA API is poorly designed because it:"
    echo "1. Exposes internal AWS configuration errors to external users"
    echo "2. Returns implementation details in error messages"
    echo "3. Doesn't handle AWS credential failures gracefully"
    echo
    echo "A well-designed API would:"
    echo "- Return a generic 'Service temporarily unavailable' message"
    echo "- Log the AWS error internally"
    echo "- Not expose internal infrastructure details"
else
    echo "No OPENAPI_1_AUTH_TOKEN found"
fi

echo
echo -e "${BLUE}The error propagation path:${NC}"
echo
cat << 'EOF'
┌─────────────────┐
│   Your Client   │
└────────┬────────┘
         │ POST /api/v1/chat/completions
         ↓
┌─────────────────┐
│   GSA API       │
│  (Public API)   │
└────────┬────────┘
         │ Internal call
         ↓
┌─────────────────┐
│  AWS Service    │ ← Tries to assume IAM role
│  (Bedrock?)     │
└────────┬────────┘
         │ Get credentials via IRSA
         ↓
┌─────────────────┐
│   AWS STS       │
│ (Security Token │ ← Checks OIDC provider
│    Service)     │
└────────┬────────┘
         │
         ✗ InvalidIdentityToken error
         │
         ↓ Error bubbles up
┌─────────────────┐
│   GSA API       │ ← Should handle gracefully
│                 │   but doesn't
└────────┬────────┘
         │ HTTP 500 + raw error
         ↓
┌─────────────────┐
│   Your Client   │ ← Receives internal error details
└─────────────────┘
EOF

echo
echo -e "${YELLOW}Security implications:${NC}"
echo "- Exposes internal cluster ID: A44B5A838D746E276B7356BE3E4D8051"
echo "- Reveals they're using AWS EKS in us-east-1"
echo "- Shows their internal authentication architecture"
echo "- Indicates poor error handling practices"
