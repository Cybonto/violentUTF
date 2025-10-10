# GSAi Setup Improvements Guide

## Overview
This guide documents the improvements made to the GSAi API setup in ViolentUTF to ensure proper authentication and eliminate hardcoded credentials.

## Key Improvements

### 1. Authentication Configuration
All GSAi routes now properly require API key authentication:
- Added `key-auth` plugin to all OpenAPI routes (chat/completions and models endpoints)
- Routes use the dynamically generated `VIOLENTUTF_API_KEY` from environment
- No hardcoded API keys in setup scripts

### 2. Route Configuration Updates

#### Chat Completions Route (POST /ai/gsai-api-1/chat/completions)
- Uses `ai-proxy` plugin for OpenAI-compatible interface
- Includes proper Bearer token authentication from `OPENAPI_1_AUTH_TOKEN`
- Added `model.passthrough: true` for model selection flexibility
- Includes upstream configuration for proper routing

#### Models Route (GET /ai/gsai-api-1/models)
- Uses `proxy-rewrite` plugin (ai-proxy doesn't work well with GET requests)
- Properly forwards Bearer token authentication
- Includes timeout configuration for longer-running requests

### 3. Consumer Management
The setup now creates three consumers for compatibility:
- `violentutf-api` - Primary consumer (recommended)
- `violentutf-user` - Legacy consumer for backward compatibility
- `violentutf_api_user` - Additional consumer for specific integrations

All consumers use the same dynamically generated API key from `VIOLENTUTF_API_KEY`.

### 4. Security Improvements
- Removed hardcoded API key `7t3wlLo4qaGPjcpSq7w5ze0nlBkDBeO3` from fix scripts
- All API keys are now read from environment files
- Fix scripts (`fix_gsai_ai_proxy.sh` and `fix_gsai_auth.sh`) updated to use environment variables

## Configuration in ai-tokens.env

Ensure your `ai-tokens.env` has the correct GSAi configuration:

```bash
# GSAi API Configuration
OPENAPI_ENABLED=true
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=gsai-api-1
OPENAPI_1_NAME="GSAi API Latest"
OPENAPI_1_BASE_URL=http://host.docker.internal:8081  # Or your GSAi endpoint
OPENAPI_1_SPEC_PATH=/openapi.json
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=your_gsai_bearer_token_here
```

## Testing the Configuration

After setup, test GSAi access:

```bash
# Get the API key
API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf/.env | cut -d'=' -f2)

# Test chat completions
curl -X POST http://localhost:9080/ai/gsai-api-1/chat/completions \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3211b",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "max_tokens": 100
  }'

# Test models listing
curl -H "apikey: $API_KEY" \
  http://localhost:9080/ai/gsai-api-1/models
```

## Troubleshooting

### "Missing API key in request" Error
- Ensure you're using the lowercase `apikey` header (not `X-API-KEY`)
- Verify the API key matches what's in `violentutf/.env`

### "403 Forbidden" Error
- Check that `OPENAPI_1_AUTH_TOKEN` in `ai-tokens.env` is valid
- Verify the token has access to the requested model
- Contact GSAi administrator if token needs additional permissions

### "Bad Gateway" Error
- Verify GSAi endpoint is accessible: `curl $OPENAPI_1_BASE_URL/api/v1/models`
- Check Docker network connectivity if using `host.docker.internal`
- Ensure APISIX can reach the GSAi service

## Next Steps

1. **Linux Setup**: The Linux setup script needs to be updated to include OpenAPI support
2. **Consumer Consolidation**: Consider standardizing on just `violentutf-api` consumer
3. **Documentation**: Update API documentation to reflect the authentication requirements

## Related Files

- `/setup_macos_files/openapi_setup.sh` - Main OpenAPI route configuration
- `/setup_macos_files/apisix_setup.sh` - Consumer creation logic
- `/docs/troubleshooting/gsai_authentication_resolution.md` - Detailed troubleshooting guide
- `/fix_gsai_ai_proxy.sh` - Utility script for fixing GSAi routes (updated to use env vars)
