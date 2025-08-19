# GSAi Key-Auth Plugin Conflict Issue

## Problem Summary
GSAi authentication was failing with the error:
```
"Invalid key=value pair (missing equal-sign) in Authorization header (hashed with SHA-256)"
```

This was NOT because GSAi needs a special token format, but because the `key-auth` plugin was interfering with the Authorization header.

## Root Cause
In commit 5e7d24e (when GSAi was working), routes were configured WITHOUT the `key-auth` plugin. Later updates added `key-auth` to all routes for API key authentication, but this breaks GSAi because:

1. Client sends request with `apikey` header for APISIX authentication
2. `key-auth` plugin validates the API key
3. **Problem**: `key-auth` plugin modifies/consumes the Authorization header
4. `ai-proxy` plugin tries to add `Authorization: Bearer <token>` for GSAi
5. GSAi receives a corrupted Authorization header

## Solution
GSAi routes must be configured WITHOUT the `key-auth` plugin:

```json
// ❌ WRONG - Causes header conflict
{
  "plugins": {
    "key-auth": {},
    "ai-proxy": {
      "auth": {
        "header": {
          "Authorization": "Bearer <token>"
        }
      }
    }
  }
}

// ✅ CORRECT - No key-auth for GSAi
{
  "plugins": {
    "ai-proxy": {
      "auth": {
        "header": {
          "Authorization": "Bearer <token>"
        }
      }
    }
  }
}
```

## Fix Applied
1. Updated `fix_gsai_ai_proxy.sh` to remove `key-auth` plugin from GSAi routes
2. Updated `setup_macos_files/openapi_setup.sh` to not add `key-auth` for GSAi routes
3. Token format in `ai-tokens.env` remains standard (no key=value needed):
   ```bash
   OPENAPI_1_AUTH_TOKEN=test_user_WGE_PBSQ4wxJdgOY  # This is correct
   ```

## Security Note
Removing `key-auth` from GSAi routes means these routes are publicly accessible through APISIX. This is acceptable because:
- GSAi itself requires Bearer token authentication
- The ai-proxy plugin adds the authentication header
- GSAi validates the token on their end

For production environments, consider:
- IP whitelisting for GSAi routes
- Rate limiting
- Additional APISIX plugins for security

## Testing
After running the fix:
```bash
./fix_gsai_ai_proxy.sh
```

Test with:
```bash
# This should now work
curl -X POST http://localhost:9080/ai/gsai-api-1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "Hello"}]}'
```

Note: No `apikey` header needed since key-auth is removed for GSAi routes.