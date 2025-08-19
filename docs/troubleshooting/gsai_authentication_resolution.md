# GSAi Authentication Resolution

## Summary
The GSAi API authentication issue has been successfully resolved. The fix involved updating the APISIX routes to use the `ai-proxy` plugin with proper Bearer token authentication from `OPENAPI_1_AUTH_TOKEN` in `ai-tokens.env`.

## Changes Made

### 1. Route Configuration Updates
- **Route 9001** (chat/completions): Now uses `ai-proxy` plugin with Bearer token authentication
- **Route 9101** (models): Uses `proxy-rewrite` plugin (ai-proxy doesn't work well with GET requests)

### 2. Security Improvements
Updated the fix scripts to remove hardcoded API keys:
- `fix_gsai_ai_proxy.sh`: Now reads `VIOLENTUTF_API_KEY` from `violentutf/.env`
- `fix_gsai_auth.sh`: Now reads `VIOLENTUTF_API_KEY` from `violentutf/.env`

Previously hardcoded key `7t3wlLo4qaGPjcpSq7w5ze0nlBkDBeO3` has been replaced with environment variable.

### 3. Setup Script Status
- **macOS Setup (`setup_macos_new.sh`)**: Already has proper GSAi route configuration with ai-proxy
- **Linux Setup (`setup_linux.sh`)**: Does not yet have OpenAPI support (no openapi_setup.sh module)

## Technical Details

### Working Configuration
The GSAi routes now use this configuration pattern:

```json
{
  "plugins": {
    "key-auth": {},
    "ai-proxy": {
      "provider": "openai-compatible",
      "auth": {
        "header": {
          "Authorization": "Bearer $OPENAPI_1_AUTH_TOKEN"
        }
      },
      "model": {
        "passthrough": true
      },
      "override": {
        "endpoint": "$OPENAPI_1_BASE_URL/api/v1/chat/completions"
      }
    }
  }
}
```

### Authentication Flow
1. Client sends request with `apikey` header to APISIX
2. APISIX validates the API key using `key-auth` plugin
3. APISIX forwards request to GSAi API with Bearer token from `OPENAPI_1_AUTH_TOKEN`
4. GSAi API processes the request and returns response

### Consumer Configuration
The setup creates two consumers for backward compatibility:
- `violentutf-api`: Primary consumer
- `violentutf-user`: Legacy consumer

Both use the same API key from `VIOLENTUTF_API_KEY` environment variable.

## Testing
Test the GSAi API with:
```bash
# Load the API key
API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf/.env | cut -d'=' -f2)

# Test chat completions
curl -X POST http://localhost:9080/ai/gsai-api-1/chat/completions \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3211b",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

## Next Steps
1. Add OpenAPI support to Linux setup script
2. Consider consolidating consumer names to just use `violentutf-api`
3. Document the ai-proxy vs proxy-rewrite plugin usage patterns

## References
- Commit 5e7d24ebd4677668dfb0c372ae759d54e6d78705 has the working route configuration
- `ai-tokens.env` contains the Bearer token configuration
- `violentutf/.env` contains the APISIX API key