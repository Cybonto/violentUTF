# Environment B APISIX Authentication Fix

## Problem
The OpenAPI generator is failing with "401 Unauthorized" because APISIX is not properly forwarding authentication to the OpenAPI provider.

## Root Cause
The request flow is:
1. FastAPI sends request to APISIX with Bearer token
2. APISIX should forward to OpenAPI provider with authentication
3. But APISIX is not configured to pass the auth token to the upstream

## Solution

### Check APISIX Route Configuration

1. **List current routes**:
   ```bash
   curl -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        http://localhost:9180/apisix/admin/routes | jq
   ```

2. **Look for the OpenAPI route** (should be something like `/ai/openapi/gsai-api-1/*`)

3. **The route needs to be configured to**:
   - Either pass through the Authorization header from the client
   - Or add the authorization header with the OpenAPI token

### Fix Option 1: Configure APISIX to Add Auth Header

Update the APISIX route to add the authorization header:

```bash
curl -X PUT http://localhost:9180/apisix/admin/routes/openapi-gsai-api-1 \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/ai/openapi/gsai-api-1/*",
    "name": "openapi-gsai-api-1",
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
      },
      "scheme": "https"
    },
    "plugins": {
      "proxy-rewrite": {
        "regex_uri": ["^/ai/openapi/gsai-api-1/(.*)", "/$1"],
        "headers": {
          "set": {
            "Authorization": "Bearer YOUR_ACTUAL_TOKEN_HERE"
          }
        }
      }
    }
  }'
```

### Fix Option 2: Configure APISIX to Pass Through Headers

Ensure APISIX passes through the Authorization header:

```bash
curl -X PUT http://localhost:9180/apisix/admin/routes/openapi-gsai-api-1 \
  -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uri": "/ai/openapi/gsai-api-1/*",
    "name": "openapi-gsai-api-1",
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
      },
      "scheme": "https"
    },
    "plugins": {
      "proxy-rewrite": {
        "regex_uri": ["^/ai/openapi/gsai-api-1/(.*)", "/$1"]
      },
      "request-id": {
        "include_in_response": true
      }
    }
  }'
```

### Fix Option 3: Update Setup Script

The setup script should be creating routes with proper authentication. Check if `setup_linux.sh` or `setup_macos.sh` is properly configuring OpenAPI routes with authentication.

### Verification

After updating the route:

1. **Test the route directly**:
   ```bash
   curl -X POST http://localhost:9080/ai/openapi/gsai-api-1/api/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "claude_3_5_sonnet",
       "messages": [{"role": "user", "content": "test"}]
     }'
   ```

2. **Check APISIX logs**:
   ```bash
   docker logs apisix-apisix-1 --tail 50
   ```

## Temporary Workaround

If you need a quick fix, you can modify the generator_integration_service.py to bypass APISIX for OpenAPI providers:

```python
# In _execute_apisix_generator, around line 57-60
if provider.startswith("openapi-"):
    # For OpenAPI, go direct instead of through APISIX
    provider_id = provider.replace("openapi-", "")
    from app.api.endpoints.generators import get_openapi_provider_config
    provider_config = get_openapi_provider_config(provider_id)
    if provider_config and provider_config.get("base_url"):
        url = f"{provider_config['base_url']}/api/v1/chat/completions"
    else:
        # Fall back to APISIX
        base_url = os.getenv("VIOLENTUTF_API_URL", "http://apisix-apisix-1:9080")
        url = f"{base_url}{endpoint}"
else:
    # Use APISIX for built-in providers
    base_url = os.getenv("VIOLENTUTF_API_URL", "http://apisix-apisix-1:9080")
    url = f"{base_url}{endpoint}"
```

This would bypass APISIX and send requests directly to the OpenAPI provider with the proper authentication.