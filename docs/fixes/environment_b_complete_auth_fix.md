# Environment B Complete Authentication Fix

## Root Cause Identified

The OpenAPI authentication is failing because the APISIX route configuration in `setup_macos.sh` (lines 1693-1698) is NOT passing authentication headers to the upstream OpenAPI provider.

Current route configuration only has:
- `key-auth`: Validates APISIX API key 
- `proxy-rewrite`: Rewrites the URI path

Missing: Authentication headers for the upstream OpenAPI provider!

## Solution

### Option 1: Fix setup_macos.sh (Recommended)

Modify the `create_openapi_route` function to include authentication headers:

```bash
# In setup_macos.sh, around line 1693, update the plugins section:

"plugins": {
    "key-auth": {},
    "proxy-rewrite": {
        "regex_uri": ["^/ai/openapi/'"$provider_id"'(.*)", "$1"],
        "headers": {
            "set": {
                "Authorization": "Bearer '"$auth_config"'"
            }
        }
    }
}'
```

Or better yet, handle different auth types:

```bash
# Build auth headers based on auth_type
local auth_headers=""
case "$auth_type" in
    "bearer")
        auth_headers='"Authorization": "Bearer '"$auth_config"'"'
        ;;
    "api_key")
        # Parse header name from auth_config or use default
        auth_headers='"X-API-Key": "'"$auth_config"'"'
        ;;
    "basic")
        # Base64 encode username:password
        local basic_auth=$(echo -n "$auth_config" | base64)
        auth_headers='"Authorization": "Basic '"$basic_auth"'"'
        ;;
esac

# Then in the route config:
"plugins": {
    "key-auth": {},
    "proxy-rewrite": {
        "regex_uri": ["^/ai/openapi/'"$provider_id"'(.*)", "$1"],
        "headers": {
            "set": {
                '"$auth_headers"'
            }
        }
    }
}
```

### Option 2: Manual Route Update (Quick Fix)

Update the existing APISIX route to add authentication:

```bash
# Get current route configuration
curl -s -X GET "http://localhost:9180/apisix/admin/routes" \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" | jq '.node.nodes[] | select(.value.uri | contains("/ai/openapi/gsai-api-1"))'

# Update the route with authentication
ROUTE_ID="openapi-gsai-api-1-<hash>"  # Get from above command
AUTH_TOKEN="<your_actual_token>"      # From OPENAPI_1_AUTH_TOKEN

curl -X PATCH "http://localhost:9180/apisix/admin/routes/$ROUTE_ID" \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "plugins": {
        "key-auth": {},
        "proxy-rewrite": {
            "regex_uri": ["^/ai/openapi/gsai-api-1(.*)", "$1"],
            "headers": {
                "set": {
                    "Authorization": "Bearer '"$AUTH_TOKEN"'"
                }
            }
        }
    }
  }'
```

### Option 3: Bypass APISIX (Temporary Workaround)

Modify `generator_integration_service.py` to go direct for OpenAPI providers:

```python
# Around line 57-60 in _execute_apisix_generator
if provider.startswith("openapi-"):
    # For OpenAPI, bypass APISIX and go direct
    provider_id = provider.replace("openapi-", "")
    from app.api.endpoints.generators import get_openapi_provider_config
    provider_config = get_openapi_provider_config(provider_id)
    
    if provider_config and provider_config.get("base_url"):
        # Use direct URL instead of APISIX
        base_url = provider_config['base_url']
        # Get the chat completions endpoint
        url = f"{base_url}/api/v1/chat/completions"
        logger.info(f"Bypassing APISIX for OpenAPI provider, direct URL: {url}")
    else:
        # Fall back to APISIX if config not found
        base_url = os.getenv("VIOLENTUTF_API_URL", "http://apisix-apisix-1:9080")
        url = f"{base_url}{endpoint}"
else:
    # Use APISIX for built-in providers
    base_url = os.getenv("VIOLENTUTF_API_URL", "http://apisix-apisix-1:9080")
    url = f"{base_url}{endpoint}"
```

## Testing After Fix

### Test the APISIX route directly:
```bash
# This should work after the fix
curl -X POST http://localhost:9080/ai/openapi/gsai-api-1/api/v1/chat/completions \
  -H "apikey: $VIOLENTUTF_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude_3_5_sonnet",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Check APISIX logs:
```bash
docker logs apisix-apisix-1 --tail 50
```

Look for:
- Upstream request headers being set
- 401 errors from upstream
- Successful 200 responses

## Long-term Fix

The setup script should be updated to properly handle OpenAPI authentication:

1. Parse auth configuration from environment variables
2. Add appropriate headers to proxy-rewrite plugin
3. Support all auth types (bearer, api_key, basic)
4. Validate routes after creation

This ensures all OpenAPI providers work correctly without manual intervention.