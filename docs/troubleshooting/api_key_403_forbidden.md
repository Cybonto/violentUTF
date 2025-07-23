# API Key 403 Forbidden Troubleshooting Guide

## Problem Description
When using Simple Chat or other AI features, you get:
- "Access forbidden - check API key permissions" error
- HTTP 403 response from APISIX
- API key is shown as present but rejected

## Root Causes

### 1. API Key Not Registered in APISIX
The most common cause is that the API key exists in the environment files but hasn't been registered as a consumer in APISIX.

### 2. API Key Mismatch
Different components may have different API keys:
- Streamlit uses API key from `violentutf/.env`
- FastAPI may have a different key in `violentutf_api/fastapi_app/.env`
- APISIX consumers may be registered with yet another key

### 3. Missing key-auth Plugin
The GSAi routes may be missing the `key-auth` plugin, causing authentication to be bypassed or fail.

## Diagnostic Steps

### 1. Run the Diagnostic Script
```bash
./diagnose_api_key_issue.sh
```

This will:
- Show all registered consumers and their API keys
- Check if your API key exists in any consumer
- Verify GSAi routes have key-auth plugin
- Test authentication with different headers

### 2. Check API Keys Across Services

```bash
# Check Streamlit API key
echo "Streamlit: $(grep '^VIOLENTUTF_API_KEY=' violentutf/.env | cut -d'=' -f2)"

# Check FastAPI API key
echo "FastAPI: $(grep '^VIOLENTUTF_API_KEY=' violentutf_api/fastapi_app/.env | cut -d'=' -f2)"

# Check what key Streamlit is actually using (from logs)
# Look for: "Using generated API key: wdDCpGY4...FVEI"
```

### 3. List All APISIX Consumers
```bash
ADMIN_KEY=$(grep "^APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)
curl -s -H "X-API-KEY: $ADMIN_KEY" http://localhost:9180/apisix/admin/consumers | jq '.list[].value | {username, key: .plugins."key-auth".key}'
```

## Quick Fix Solutions

### Solution 1: Register the Correct API Key
Run the enterprise fix script:
```bash
./fix_enterprise_api_key.sh
```

This will:
- Find the API key from your environment files
- Create/update all three consumers with the correct key
- Test the authentication

### Solution 2: Manual Consumer Creation
If the script doesn't work, manually create the consumer:

```bash
# Get your keys
ADMIN_KEY=$(grep "^APISIX_ADMIN_KEY=" apisix/.env | cut -d'=' -f2)
API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf/.env | cut -d'=' -f2)

# Create consumer
curl -X PUT "http://localhost:9180/apisix/admin/consumers/violentutf-api" \
  -H "X-API-KEY: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"violentutf-api\",
    \"plugins\": {
      \"key-auth\": {
        \"key\": \"$API_KEY\"
      }
    }
  }"
```

### Solution 3: Fix GSAi Routes
If routes are missing key-auth plugin:
```bash
./fix_gsai_ai_proxy.sh
```

## Understanding the Authentication Flow

1. **Streamlit** generates/uses API key from `violentutf/.env`
2. **Streamlit** sends request to APISIX with `apikey: <key>` header
3. **APISIX** checks if the key matches any registered consumer
4. **APISIX** (if authenticated) forwards request to GSAi with Bearer token
5. **GSAi** validates Bearer token and processes request

## Common Issues and Solutions

### "Using generated API key" in Logs
If Streamlit shows "Using generated API key" with a different key than what's in the .env file, it may be generating a new key at runtime. This happens when:
- The .env file is not properly loaded
- The API key environment variable is not set
- There's a mismatch in configuration

**Fix**: Restart Streamlit after ensuring .env files are correct.

### Multiple API Keys in System
If different services have different API keys:
1. Standardize on one key across all services
2. Update all .env files to use the same key
3. Re-register consumers with the standardized key

### Docker Network Issues
If using Docker, ensure services can communicate:
```bash
# Test from Streamlit container
docker exec violentutf-streamlit-1 curl http://apisix-apisix-1:9080/health

# Test from host
curl http://localhost:9080/health
```

## Prevention

1. **Always use setup scripts** to ensure consistent configuration
2. **Don't manually edit API keys** in .env files
3. **Run diagnostic script** after setup to verify configuration
4. **Keep consumers synchronized** with environment files

## Enterprise-Specific Considerations

In enterprise environments:
- API keys may be managed by external systems
- Additional network security may block requests
- Corporate proxies may interfere with Docker networking
- Ensure firewall rules allow internal Docker communication

## Verification Steps

After fixing, verify with:
```bash
# Get the API key
API_KEY=$(grep "^VIOLENTUTF_API_KEY=" violentutf/.env | cut -d'=' -f2)

# Test with lowercase header (recommended)
curl -X POST http://localhost:9080/ai/gsai-api-1/chat/completions \
  -H "apikey: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 50}'
```

Success looks like:
```json
{
  "object": "chat.completion",
  "created": 1721745594,
  "model": "llama3211b",
  "choices": [...]
}
```