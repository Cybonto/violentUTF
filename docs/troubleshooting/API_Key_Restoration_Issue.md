# API Key Restoration Issue

## Problem
After running setup with credential preservation, you may encounter:
```
Access forbidden - check API key permissions
```

This indicates that API keys were not properly restored to the FastAPI service.

## Root Cause
The setup script was not properly restoring API keys from preserved .env files to the FastAPI environment. Specifically:

1. The `VIOLENTUTF_API_KEY` was being generated but not properly propagated
2. AI provider API keys from `ai-tokens.env` were not being copied to FastAPI's .env
3. The `update_fastapi_env` function was not being called during setup

## Solution

### Immediate Fix
If you encounter this issue, manually update the FastAPI .env file:

```bash
# 1. Check your preserved API key
grep "VIOLENTUTF_API_KEY" violentutf/.env

# 2. Copy it to FastAPI
echo "VIOLENTUTF_API_KEY=<your-key-here>" >> violentutf_api/fastapi_app/.env

# 3. If using AI providers, also copy those keys
grep "OPENAI_API_KEY" ai-tokens.env >> violentutf_api/fastapi_app/.env
grep "ANTHROPIC_API_KEY" ai-tokens.env >> violentutf_api/fastapi_app/.env

# 4. Restart the FastAPI container
docker restart violentutf_api-fastapi-1
```

### Permanent Fix
Update to the latest setup scripts which include:

1. Enhanced credential restoration logic in `utils.sh`
2. Proper API key propagation in `env_management.sh`
3. Call to `update_fastapi_env` in the main setup flow

## Prevention

### Before Running Setup
1. Verify your credentials are properly backed up:
```bash
ls -la */.env
cat violentutf_api/fastapi_app/.env | grep API_KEY
```

2. Create a manual backup:
```bash
./setup_macos_new.sh --backup production
```

### After Running Setup
1. Verify API keys were restored:
```bash
# Check all API keys
grep "API_KEY" violentutf_api/fastapi_app/.env
grep "ENABLED=true" violentutf_api/fastapi_app/.env
```

2. Test API access:
```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
     http://localhost:9080/api/v1/health
```

## Technical Details

The setup process should:
1. Load existing .env files during `generate_all_secrets()`
2. Preserve API keys when found
3. Generate new ones only if missing
4. Propagate all keys to FastAPI via `update_fastapi_env()`
5. Include AI provider keys from `ai-tokens.env`

## Related Issues
- Credential preservation not working as expected
- AI provider tokens not being loaded
- Mismatch between services' API keys

## Verification Steps

After fix, verify:
```bash
# 1. API key is present
docker exec violentutf_api-fastapi-1 env | grep VIOLENTUTF_API_KEY

# 2. AI providers are configured
docker exec violentutf_api-fastapi-1 env | grep "_ENABLED"

# 3. Service is accessible
curl http://localhost:9080/api/v1/health
```