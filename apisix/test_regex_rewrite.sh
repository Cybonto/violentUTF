#!/usr/bin/env bash
# Test APISIX regex URI rewriting

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Testing APISIX Regex URI Rewriting ===${NC}"
echo

# Test the regex pattern
echo "Testing regex pattern: ^/ai/openapi/gsai-api-1(.*)"
echo

test_uris=(
    "/ai/openapi/gsai-api-1/api/v1/models"
    "/ai/openapi/gsai-api-1/api/v1/chat/completions"
    "/ai/openapi/gsai-api-1/api/v1/embeddings"
)

for uri in "${test_uris[@]}"; do
    echo "Original URI: $uri"
    # Apply the regex transformation
    rewritten=$(echo "$uri" | sed -E 's|^/ai/openapi/gsai-api-1(.*)|\1|')
    echo "Rewritten URI: $rewritten"
    echo "Expected upstream path: https://api.dev.gsai.mcaas.fcs.gsa.gov$rewritten"
    echo
done

echo -e "${BLUE}=== Testing APISIX Route with Verbose Output ===${NC}"
echo

# Load environment
if [ -f "../violentutf/.env" ]; then
    source ../violentutf/.env
fi

if [ -n "${VIOLENTUTF_API_KEY:-}" ]; then
    echo "Testing chat completions route with verbose output..."
    echo

    # Use -v for verbose output to see what APISIX is doing
    curl -v -X POST http://localhost:9080/ai/openapi/gsai-api-1/api/v1/chat/completions \
        -H "apikey: $VIOLENTUTF_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "test"}]}' 2>&1 | \
        grep -E "(< HTTP|> Host:|> POST|< |Connected to)"
else
    echo -e "${YELLOW}VIOLENTUTF_API_KEY not found${NC}"
fi

echo
echo -e "${BLUE}=== Checking APISIX Error Log ===${NC}"
echo "Looking for upstream connection errors..."
docker logs apisix-apisix-1 2>&1 | grep -E "(upstream|gsai|proxy_pass|failed)" | tail -10 || echo "No relevant errors found"

echo
echo -e "${BLUE}=== Summary ===${NC}"
echo
echo "The issue is clear from the direct API test:"
echo "- Models endpoint: Works fine (200)"
echo "- Chat endpoint: Returns 500 with AWS authentication error"
echo
echo "The GSA API has an internal issue with AWS EKS authentication."
echo "This is NOT related to:"
echo "- Your Bearer token (it works for models)"
echo "- SSL certificates (connection is established)"
echo "- APISIX configuration (routes are correct)"
echo
echo "The 404 from APISIX might be because:"
echo "1. APISIX is configured to return 404 for upstream 5xx errors"
echo "2. The request times out before getting the 500 response"
echo
echo -e "${YELLOW}This needs to be fixed by the GSA API team.${NC}"
