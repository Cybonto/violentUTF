#!/usr/bin/env bash
# Quick endpoint test for production debugging
# Simplified version for fast testing

# Usage: ./quick_endpoint_test.sh <fastapi_token> <apisix_admin_key>

FASTAPI_TOKEN="${1:-$FASTAPI_TOKEN}"
APISIX_ADMIN_KEY="${2:-$APISIX_ADMIN_KEY}"
FASTAPI_BASE_URL="${FASTAPI_BASE_URL:-http://localhost:9080}"
APISIX_ADMIN_URL="${APISIX_ADMIN_URL:-http://localhost:9180}"

if [ -z "$FASTAPI_TOKEN" ] || [ -z "$APISIX_ADMIN_KEY" ]; then
    echo "Usage: $0 <fastapi_token> <apisix_admin_key>"
    echo "Or set FASTAPI_TOKEN and APISIX_ADMIN_KEY environment variables"
    exit 1
fi

echo "🧪 Quick Production Endpoint Test"
echo "=================================="

# Test 1: Model options fix
echo -e "\n1️⃣ Testing model options fix..."
response=$(curl -s "$FASTAPI_BASE_URL/api/v1/generators/types/AI%20Gateway/params" \
    -H "Authorization: Bearer $FASTAPI_TOKEN")

if [ $? -eq 0 ]; then
    model_count=$(echo "$response" | jq -r '.parameters[] | select(.name=="model") | .options | length' 2>/dev/null || echo "0")
    if [ "$model_count" != "null" ] && [ "$model_count" -gt 0 ]; then
        echo "✅ Model options populated: $model_count models found"
    else
        echo "❌ Model options still empty"
    fi
else
    echo "❌ Failed to call AI Gateway params API"
fi

# Test 2: Find OpenAPI routes (fixed JSON parsing)
echo -e "\n2️⃣ Finding OpenAPI routes..."
routes=$(curl -s "$APISIX_ADMIN_URL/apisix/admin/routes" \
    -H "X-API-KEY: $APISIX_ADMIN_KEY" | \
    jq -r '.. | .uri? // empty' 2>/dev/null | grep -i openapi || echo "")

if [ -n "$routes" ]; then
    echo "✅ Found OpenAPI routes:"
    echo "$routes" | sed 's/^/  /'
    
    # Test first route
    first_route=$(echo "$routes" | head -1)
    echo -e "\n3️⃣ Testing route: $first_route"
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$FASTAPI_BASE_URL$first_route" \
        -H "Authorization: Bearer $FASTAPI_TOKEN")
    
    if [ "$status" = "200" ]; then
        echo "✅ Route accessible (200)"
    elif [ "$status" = "404" ]; then
        echo "❌ Route returns 404 (this is the problem!)"
    else
        echo "⚠️ Route returns $status"
    fi
else
    echo "❌ No OpenAPI routes found in APISIX"
fi

# Test 3: Quick orchestrator test
echo -e "\n4️⃣ Testing orchestrator creation..."
orch_response=$(curl -s -w "\nSTATUS:%{http_code}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $FASTAPI_TOKEN" \
    -d '{
        "name": "quick_test_'$(date +%s)'",
        "orchestrator_type": "PromptSendingOrchestrator",
        "description": "Quick production test",
        "parameters": {
            "objective_target": {
                "type": "configured_generator", 
                "generator_name": "test1"
            }
        }
    }' \
    "$FASTAPI_BASE_URL/api/v1/orchestrators/create")

status=$(echo "$orch_response" | grep "STATUS:" | cut -d: -f2)
if [ "$status" = "200" ] || [ "$status" = "201" ]; then
    echo "✅ Orchestrator creation works"
else
    echo "❌ Orchestrator creation failed ($status)"
fi

echo -e "\n🏁 Quick test complete!"
echo "Run ./scripts/test_production_endpoints.sh for detailed analysis"