# GSAi API Model Access Issue

## Problem Description

When attempting to use the `claude_3_7_sonnet` model through the GSAi API, the system returns a 403 Forbidden error with the message:
```
AccessDeniedException: You don't have access to the model with the specified model ID.
```

## Root Causes

1. **API Token Permissions**: The GSAi API token (`<REDACTED>`) doesn't have access permissions for the `claude_3_7_sonnet` model, even though the model is listed in the API's available models.

2. **Provider Name Inconsistency**: The system had an inconsistency where:
   - The OpenAPI provider was configured with ID `gsai-api-1` in `ai-tokens.env`
   - The token manager had hardcoded fallback endpoints under the key `"gsai"`
   - This created confusion about which provider name to use

## Solutions Applied

### 1. Fixed Provider Name Consistency
- Updated all references to use `gsai-api-1` consistently throughout the codebase
- Removed the confusing `"gsai"` key from fallback endpoints in `token_manager.py`
- Updated `generator_config.py` to use `gsai-api-1` as the provider option

### 2. Cleaned Up Token Manager
- Removed duplicate handling for both "gsai" and "gsai-api-1"
- Now uses only the correct provider ID `gsai-api-1` that matches the configuration
- Updated display names to clearly identify GSAi models

## Remaining Issue

The API token permission issue requires action from the GSAi API administrator:
- The token `<REDACTED>` needs to be granted access to the `claude_3_7_sonnet` model
- Alternatively, a new token with appropriate permissions should be generated

## Testing

1. **Verify the fix works with accessible models**:
   ```bash
   # Test with llama model (which works)
   curl -X POST "http://localhost:9080/ai/gsai-api-1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "llama3211b",
       "messages": [{"role": "user", "content": "Hello"}],
       "max_tokens": 10
     }'
   ```

2. **Confirm Claude model still needs permission**:
   ```bash
   # This will still fail until token permissions are updated
   curl -X POST "http://localhost:9080/ai/gsai-api-1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "claude_3_7_sonnet",
       "messages": [{"role": "user", "content": "Hello"}],
       "max_tokens": 10
     }'
   ```

## Recommendations

1. Contact the GSAi API administrator to grant access to Claude models for the token
2. Consider using different tokens for different model families if access control is intentional
3. Update the `ai-tokens.env` file with appropriate tokens once permissions are resolved