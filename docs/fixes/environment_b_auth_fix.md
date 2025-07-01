# Environment B OpenAPI Authentication Fix

## Problem
The OpenAPI generator is failing with "401 Unauthorized" because the authentication token is not being found or passed correctly.

## Root Cause
The provider ID `openapi-gsai-api-1` is being processed incorrectly:
1. The code strips `openapi-` prefix → `gsai-api-1`
2. It then looks for environment variables that don't exist
3. No auth token is found, resulting in 401 error

## Solution

### Option 1: Set Environment Variables in Numbered Format (Recommended)

In environment B's `ai-tokens.env`, ensure you have:

```bash
# Enable OpenAPI
OPENAPI_ENABLED=true

# Configure GSAI API as provider 1
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=gsai-api-1
OPENAPI_1_NAME="GSAI API Provider"
OPENAPI_1_BASE_URL=https://api.dev.gsai.mcaas.fcs.gsa.gov
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=your_actual_gsai_auth_token_here
```

### Option 2: Set Environment Variables in Direct Format

Alternatively, set these environment variables:

```bash
OPENAPI_GSAI_API_1_BASE_URL=https://api.dev.gsai.mcaas.fcs.gsa.gov
OPENAPI_GSAI_API_1_AUTH_TOKEN=your_actual_gsai_auth_token_here
OPENAPI_GSAI_API_1_AUTH_TYPE=bearer
OPENAPI_GSAI_API_1_NAME="GSAI API Provider"
```

### Option 3: Fix the Code to Handle Provider IDs Better

Create a patch file to improve the provider ID handling:

```python
# In generators.py, update get_openapi_provider_config function
def get_openapi_provider_config(provider_id: str) -> Dict[str, Optional[str]]:
    """
    Get configuration for an OpenAPI provider from settings
    """
    # Handle both with and without 'openapi-' prefix
    if provider_id.startswith('openapi-'):
        provider_id = provider_id.replace('openapi-', '')
    
    # Continue with existing logic...
```

## Verification Steps

1. **Check current environment variables**:
   ```bash
   env | grep OPENAPI | grep -E "(ID|TOKEN|URL)" | sort
   ```

2. **Verify the provider configuration**:
   ```bash
   curl -H "Authorization: Bearer $JWT_TOKEN" \
        http://localhost:9080/api/v1/generators/apisix/openapi-providers
   ```

3. **Test the generator**:
   After setting the environment variables, restart the services and test again.

## Important Notes

- The auth token must be the actual API key/token for the GSAI API service
- SSL verification is disabled for this provider (as shown in logs)
- The token is passed as a Bearer token in the Authorization header
- Make sure to restart the FastAPI service after changing environment variables:
  ```bash
  docker-compose restart violentutf-api
  ```