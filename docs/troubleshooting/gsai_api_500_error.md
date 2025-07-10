# GSAI API 500 Internal Server Error

## Issue
The GSAI API returns a 500 error for chat completions with the message:
```
InvalidIdentityToken: No OpenIDConnect provider found in your account for https://oidc.eks.us-east-1.amazonaws.com/id/A44B5A838D746E276B7356BE3E4D8051
```

## What This Means
1. **Your authentication is working correctly** - The API accepts your token (models endpoint works)
2. **The GSAI API has an internal configuration issue** - They're trying to use AWS IAM roles internally
3. **This is not something you can fix** - It's a server-side issue with GSAI

## Current Status
- ✅ Authentication token is valid
- ✅ Models endpoint works: `/api/v1/models`
- ❌ Chat endpoint fails: `/api/v1/chat/completions` (500 error)
- ❌ APISIX routing returns 404 (likely because the route expects POST but gets an error)

## Workarounds

### Option 1: Use a Different Model
If the issue is specific to certain models, try others from the list:
- claude_3_haiku
- llama3211b
- gemini-2.0-flash

### Option 2: Contact GSAI Support
Report the error message to GSAI team:
- Endpoint: `https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/chat/completions`
- Error: `InvalidIdentityToken` with AWS OIDC reference
- Note that `/api/v1/models` works fine

### Option 3: Try Alternative Endpoints
Some APIs have multiple endpoints:
```bash
# Try without /api prefix
curl -X POST https://api.dev.gsai.mcaas.fcs.gsa.gov/v1/chat/completions \
  -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "test"}]}'

# Try /completions instead of /chat/completions
curl -X POST https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/completions \
  -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model": "claude_3_5_sonnet", "prompt": "test"}'
```

## Fix the APISIX 404

While waiting for GSAI to fix their API, you can still fix the APISIX routing issue:

1. **Run the debug script**:
   ```bash
   cd apisix
   ./debug_apisix_route.sh
   ```

2. **Check if routes exist**:
   ```bash
   curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        http://localhost:9180/apisix/admin/routes | \
        jq '.list[].value.uri' | grep openapi
   ```

3. **If no routes, re-run setup**:
   ```bash
   ./setup_macos.sh
   ```

## Summary
The authentication is now working correctly. The 500 error is an internal GSAI API issue related to their AWS infrastructure. You'll need to wait for them to fix it or use an alternative OpenAPI provider.