#!/bin/bash
# verify_rate_limiting.sh
# Quick verification script to test rate limiting implementation

echo "🔒 ViolentUTF API Rate Limiting Verification"
echo "=" * 50

API_BASE="http://localhost:9080/api/v1"
LOGIN_ENDPOINT="$API_BASE/auth/token"

echo "📍 Testing rate limiting on login endpoint..."
echo "   Endpoint: $LOGIN_ENDPOINT"
echo "   Expected limit: 5 requests/minute"
echo

# Test rapid login attempts (should trigger rate limiting)
echo "🚀 Sending rapid login requests..."
for i in {1..8}; do
    echo -n "Request $i: "
    
    response=$(curl -s -w "%{http_code}" -o /dev/null \
        -X POST "$LOGIN_ENDPOINT" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=test&password=test")
    
    case $response in
        200|201)
            echo "✅ Success ($response)"
            ;;
        401|403)
            echo "🔐 Auth Error ($response) - Expected"
            ;;
        429)
            echo "🛑 Rate Limited ($response) - Rate limiting working!"
            rate_limited=true
            ;;
        *)
            echo "❓ Other ($response)"
            ;;
    esac
    
    # Small delay between requests
    sleep 0.2
done

echo
if [ "$rate_limited" = true ]; then
    echo "✅ SUCCESS: Rate limiting is working correctly!"
    echo "   🛡️  Authentication endpoints are protected from brute force attacks"
else
    echo "❌ WARNING: Rate limiting may not be working"
    echo "   Please check if the violentutf_api container has been rebuilt with slowapi dependency"
fi

echo
echo "📋 Next steps to complete deployment:"
echo "   1. Rebuild violentutf_api container: cd apisix && docker compose up -d --build"
echo "   2. Verify rate limiting: ./verify_rate_limiting.sh"
echo "   3. Run comprehensive tests: cd violentutf_api && python test_rate_limiting.py"
echo
echo "📖 Documentation: violentutf_api/RATE_LIMITING_SECURITY.md"