# IronUTF GSAi Model Discovery Issue

## Problem Description

When using IronUTF's defense module, the GSAi provider shows "No models found for gsai-api-1. Using default." despite the fact that Configure Generator successfully populates GSAi models.

### Error Details

**User Interface**: IronUTF shows warning: "No models found for gsai-api-1. Using default."

**API Logs**:
```
2025-07-16 11:58:28,529 - app.api.endpoints.generators - INFO - User keycloak_user requested models for provider: gsai-api-1
2025-07-16 11:58:28,529 - app.api.endpoints.generators - INFO - Discovering models for provider: gsai-api-1
2025-07-16 11:58:28,532 - app.api.endpoints.generators - WARNING - No models discovered for provider gsai-api-1, using fallback
2025-07-16 11:58:28,532 - app.api.endpoints.generators - WARNING - No models discovered for provider: gsai-api-1
2025-07-16 11:58:28,533 - app.core.error_handling - INFO - Client error 404: Provider not supported or no models available
2025-07-16 11:58:28,533 - app.core.error_handling - ERROR - Error 9ee08244: HTTPException: 404: Provider not supported or no models available
INFO:     172.20.0.4:39088 - "GET /api/v1/generators/apisix/models?provider=gsai-api-1 HTTP/1.1" 404 Not Found
```

## Root Cause Analysis

### 1. Provider ID Mismatch

The core issue is a mismatch in provider naming conventions between different parts of the system:

- **ai-tokens.env Configuration**: `OPENAPI_1_ID=gsai-api-1`
- **APISIX Routes**: Created with URI `/ai/gsai-api-1/chat/completions`
- **API Model Discovery**: Expects provider format `openapi-gsai`
- **Hardcoded Models**: Only work for `provider_id == "gsai"`

### 2. Code Analysis

#### IronUTF Implementation (Working as Designed)
```python
# IronUTF correctly extracts provider ID from route
provider_id = extract_provider_id_from_route(route_uri)  # Returns "gsai-api-1"

# Calls API with the extracted ID
url = f"{api_base}/api/v1/generators/apisix/models?provider={provider_id}"
```

#### API Implementation (generators.py)
```python
async def discover_apisix_models_enhanced(provider: str) -> List[str]:
    if provider.startswith("openapi-"):
        provider_id = provider.replace("openapi-", "")

        # Special handling for GSAi - only matches if provider_id == "gsai"
        if provider_id == "gsai":  # This check fails for "gsai-api-1"
            logger.info("Using hardcoded models for GSAi (models endpoint not working)")
            return [hardcoded_models]
```

The API only recognizes:
- `openapi-gsai` → strips to `gsai` → matches hardcoded list
- But receives `gsai-api-1` → doesn't start with `openapi-` → no match

### 3. Configuration Flow

1. **Setup Phase**:
   - User configures `OPENAPI_1_ID=gsai-api-1` in ai-tokens.env
   - Setup scripts create routes using this ID

2. **Configure Generator**:
   - Uses a different code path that may translate IDs
   - Successfully gets models (needs investigation of exact mechanism)

3. **IronUTF**:
   - Reads route URIs directly: `/ai/gsai-api-1/chat/completions`
   - Extracts `gsai-api-1` and queries API
   - API doesn't recognize this format

## Impact

- IronUTF users cannot see available GSAi models in dropdown
- Must manually know which model names to use
- Inconsistent user experience between Configure Generator and IronUTF

## Temporary Workaround

Users can still test GSAi models by:
1. Knowing the model names (from Configure Generator or documentation)
2. The test will use the model name in the API call payload
3. The GSAi endpoint will accept the model if it's valid

## Potential Solutions

### Option 1: Update API to Handle Multiple ID Formats
- Modify `discover_apisix_models_enhanced` to recognize patterns like `gsai-api-1`
- Check environment configuration for `OPENAPI_X_ID` values
- Return appropriate models based on provider base URL

### Option 2: Standardize Provider IDs
- Update setup scripts to use consistent naming (e.g., always `openapi-gsai`)
- May break existing configurations
- Requires migration path

### Option 3: Add Provider Metadata to Routes
- Include provider type in route metadata
- Would allow proper provider detection regardless of ID format

### Option 4: Create Provider Registry
- Central registry mapping various IDs to provider types
- Would handle `gsai-api-1` → `gsai` → model list

## Recommendation

**Short-term**: Update the API to handle both naming conventions:
```python
# Handle multiple GSAi ID formats
if provider == "gsai-api-1" or provider == "openapi-gsai" or
   (provider.startswith("openapi-") and "gsai" in provider):
    return gsai_models
```

**Long-term**: Implement a proper provider registry that:
1. Reads OpenAPI configuration from environment
2. Maps provider IDs to their capabilities
3. Provides consistent model discovery across all UIs

## Related Issues

- GSAi models endpoint returns 403 for some models (see gsai_api_model_access_issue.md)
- Provider naming inconsistency throughout the codebase
- No dynamic model discovery for GSAi (using hardcoded list)

## Additional Investigation

### Configure Generator Behavior

Investigating Configure Generator reveals it also calls the same API endpoint with `gsai-api-1`:

```python
# Configure Generator also uses gsai-api-1
provider_param["options"] = ["openai", "anthropic", "ollama", "webui", "gsai-api-1"]
selected_provider = st.selectbox(...)  # User selects "gsai-api-1"
models = get_apisix_models_from_api(selected_provider)  # Calls API with "gsai-api-1"
```

However, Configure Generator may have fallback behavior or cached models that allow it to work despite the API returning 404. This needs further investigation to understand why it appears to work there.

### Key Differences

1. **Configure Generator**:
   - Has display name mapping: `"openapi-gsai": "GSAi (Government Services AI)"`
   - But actually uses `gsai-api-1` in API calls
   - May have fallback mechanisms or cached data

2. **IronUTF**:
   - Directly extracts provider ID from route URI
   - No fallback mechanism
   - Shows error when API returns 404

## Testing Notes

To reproduce:
1. Configure `OPENAPI_1_ID=gsai-api-1` in ai-tokens.env
2. Run setup to create routes
3. Open IronUTF and select GSAi route
4. Observe "No models found" warning
5. Check API logs for 404 error

To verify fix:
1. API should return models for `gsai-api-1` provider ID
2. IronUTF should show model dropdown with GSAi models
3. Selected model should work in test configuration

## Why Models Were Hardcoded

Investigation reveals the hardcoded GSAi models exist because:

1. **GSAi API Issues**: The GSAi `/api/v1/models` endpoint has persistent problems:
   - Returns 403 Forbidden for models even when they're listed
   - AWS IAM/OIDC configuration causes 500 Internal Server errors
   - Authentication works but permissions are inconsistent

2. **Pragmatic Workaround**: Rather than wait for GSAi to fix their API, developers hardcoded known working models:
   ```python
   # Special handling for GSAi - use hardcoded models since models endpoint has issues
   if provider_id == "gsai":
       logger.info("Using hardcoded models for GSAi (models endpoint not working)")
       return [hardcoded_list]
   ```

3. **Limited Scope**: The workaround only works for `provider_id == "gsai"`, not `gsai-api-1`

## Immediate Fix

~~For immediate relief, update the API to recognize `gsai-api-1`:~~

**Update (2025-07-16)**: Implemented Option 2 from the Simple Fix Plan - Added fallback mechanism directly to IronUTF:

```python
# In IronUTF.py, added to fetch_available_models function
FALLBACK_MODELS = {
    "gsai-api-1": [
        "claude_3_5_sonnet",
        "claude_3_7_sonnet",
        "claude_3_haiku",
        "llama3211b",
        "cohere_english_v3",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.5-pro-preview-05-06",
    ],
    "openai": [...],
    "anthropic": [...]
}

# Use fallback when API fails
if response.status_code != 200 or not models:
    if provider_id in FALLBACK_MODELS:
        logger.info(f"Using fallback models for {provider_id}")
        return FALLBACK_MODELS[provider_id]
```

This approach:
- Provides immediate relief without requiring API changes
- Maintains consistency with Simple Chat's approach
- Works even when the API is unavailable
- Logs when fallback is used for debugging

**Additional Fix**: Also updated `test_plugin_configuration` to properly handle GSAi routes by:
- Adding `route_uri` parameter to use the actual route URI
- Special handling for GSAi provider to use the correct endpoint
- This fixes the "404 Route Not Found" error when testing GSAi configurations

## Long-term Solution

A comprehensive plan has been created at: `docs/plans/Consistent_Model_Discovery_Plan.md`

Key components:
1. **Provider Registry**: Central mapping of provider IDs to capabilities
2. **Smart Discovery**: Try live → cache → fallback model lists
3. **Consistent UI**: Shared components across all interfaces
4. **Clear Feedback**: Show users when using fallback data

This will ensure consistent model discovery across Configure Generator, IronUTF, and any future UIs.
