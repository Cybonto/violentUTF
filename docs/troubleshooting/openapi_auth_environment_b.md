# OpenAPI Authentication Issue in Environment B

## Problem
After pulling updates and re-running setup, environment B still shows:
```
Authentication failed. Please check your OPENAPI-GSAI-API-1 API key configuration.
```

## Root Cause
There are two potential issues:

1. **Incorrect Authentication Handling in FastAPI**: The generator_integration_service.py was trying to add Authorization headers directly, but this is wrong. Authentication should be handled by APISIX via the proxy-rewrite plugin.

2. **Missing Authentication Headers in APISIX Routes**: The APISIX routes may not have the authentication headers configured in the proxy-rewrite plugin.

## Solution

### Step 1: Pull Latest Updates
The generator_integration_service.py has been fixed to not add Authorization headers directly. Instead, it only sends the `apikey` header to APISIX, and APISIX handles upstream authentication.

```bash
git pull
```

### Step 2: Check Current Route Configuration
Use the diagnostic script to check if your OpenAPI routes have authentication configured:

```bash
cd apisix
./check_openapi_routes.sh
```

This will show:
- Which OpenAPI routes exist
- Whether they have authentication headers configured
- What provider configuration is available

### Step 3: Update Existing Routes
If the diagnostic shows routes without authentication headers, update them:

```bash
cd apisix
./update_openapi_auth.sh
```

### Step 4: Verify Configuration
Ensure your `ai-tokens.env` has the correct configuration:

```bash
# For GSAI API 1
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=gsai-api-1
OPENAPI_1_NAME="GSAI API 1"
OPENAPI_1_BASE_URL=https://api.dev.gsai.mcaas.fcs.gsa.gov
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=<your-actual-token-here>
```

### Step 5: Restart Services
After updating routes, restart the FastAPI service to ensure it picks up the changes:

```bash
docker restart violentutf_api
```

### Step 6: Test the Route
Test directly with curl to verify authentication is working:

```bash
# Get your APISIX API key
echo $VIOLENTUTF_API_KEY

# Test the OpenAPI endpoint
curl -v -X POST http://localhost:9080/ai/openapi/gsai-api-1/api/v1/chat/completions \
  -H "apikey: $VIOLENTUTF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "claude_3_5_sonnet", "messages": [{"role": "user", "content": "test"}]}'
```

### Step 7: Check APISIX Logs
If still failing, check APISIX logs to see what's happening:

```bash
docker logs apisix-apisix-1 --tail 100 | grep -E "(gsai-api-1|401|auth)"
```

## Understanding the Fix

### Before (Incorrect)
```
Client → FastAPI (adds Bearer token) → APISIX → OpenAPI Provider
         ❌ Wrong: FastAPI shouldn't handle provider auth
```

### After (Correct)
```
Client → FastAPI (apikey only) → APISIX (adds Bearer token via proxy-rewrite) → OpenAPI Provider
         ✓ Correct: APISIX handles all provider authentication
```

## Common Issues

### "No OpenAPI routes found"
The routes may have been cleared. Re-run the setup script:
```bash
./setup_macos.sh
```

### "Authentication headers missing"
The routes exist but don't have auth headers. Run:
```bash
cd apisix && ./update_openapi_auth.sh
```

### "Invalid token"
Double-check your token in `ai-tokens.env`:
1. Make sure there are no extra spaces or quotes
2. Ensure the token hasn't expired
3. Test the token directly with the API

## Summary

The authentication flow for OpenAPI providers is:
1. Client sends request with `apikey` header to APISIX
2. APISIX validates the gateway API key
3. APISIX adds the provider's authentication header (Bearer token) via proxy-rewrite
4. APISIX forwards the request to the OpenAPI provider
5. OpenAPI provider validates its authentication and responds

The key is that FastAPI should NOT add authentication headers for OpenAPI providers - that's APISIX's job.