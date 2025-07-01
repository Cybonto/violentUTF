# OpenAPI Authentication Implementation Complete

## Summary

Successfully implemented authentication header forwarding for OpenAPI providers in ViolentUTF. The fix ensures that APISIX properly forwards authentication credentials (Bearer tokens, API keys, Basic auth) to upstream OpenAPI providers.

## Changes Made

### 1. Updated setup_macos.sh
- Modified `create_openapi_route` function (lines 1682-1732)
- Added authentication header configuration based on auth_type
- Supports Bearer, API Key, and Basic authentication
- Headers are added via the proxy-rewrite plugin

### 2. Created Update Script
- New file: `apisix/update_openapi_auth.sh`
- Updates existing APISIX routes with missing authentication headers
- Reads configuration from ai-tokens.env
- Reports which routes were updated

### 3. Updated Documentation
- **OpenAPI Integration Guide** (`docs/guides/openapi-integration.md`):
  - Added authentication details section
  - Explained how headers are forwarded
  - Added troubleshooting steps for auth failures
  - Included update script usage

- **Authentication Guide** (`docs/api/authentication.md`):
  - Added OpenAPI provider authentication section
  - Included troubleshooting for 401 errors
  - Added debugging commands for OpenAPI auth

## How It Works

1. **Configuration**: Users specify auth details in `ai-tokens.env`:
   ```bash
   OPENAPI_1_AUTH_TYPE=bearer
   OPENAPI_1_AUTH_TOKEN=sk-your-token
   ```

2. **Route Creation**: Setup script creates APISIX routes with authentication:
   ```json
   {
     "plugins": {
       "key-auth": {},
       "proxy-rewrite": {
         "regex_uri": ["^/ai/openapi/provider(.*)", "$1"],
         "headers": {
           "set": {
             "Authorization": "Bearer sk-your-token"
           }
         }
       }
     }
   }
   ```

3. **Request Flow**:
   - Client → APISIX with `apikey` header
   - APISIX validates gateway key
   - APISIX adds provider auth header
   - APISIX → OpenAPI provider with proper authentication

## Testing

To test the implementation:

```bash
# 1. Update existing routes (if any)
cd apisix && ./update_openapi_auth.sh

# 2. Test an OpenAPI endpoint
curl -X POST http://localhost:9080/ai/openapi/provider-id/api/v1/chat/completions \
  -H "apikey: $VIOLENTUTF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "model-name", "messages": [{"role": "user", "content": "test"}]}'

# 3. Check route configuration
curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
     http://localhost:9180/apisix/admin/routes | \
     jq '.list[] | select(.value.uri | contains("/ai/openapi/"))'
```

## Notes

- Setup script automatically configures auth headers during route creation
- Existing routes can be updated using the update script
- All auth types (Bearer, API Key, Basic) are supported
- No changes needed to FastAPI or Streamlit code

## Related Files

- `/Users/tamnguyen/Documents/GitHub/ViolentUTF/setup_macos.sh`
- `/Users/tamnguyen/Documents/GitHub/ViolentUTF/apisix/update_openapi_auth.sh`
- `/Users/tamnguyen/Documents/GitHub/ViolentUTF/docs/guides/openapi-integration.md`
- `/Users/tamnguyen/Documents/GitHub/ViolentUTF/docs/api/authentication.md`