# Simple Fix Plan: IronUTF GSAi Model Discovery

**Status: IMPLEMENTED** (2025-07-16) - Option 2 has been implemented in IronUTF

## Problem Summary

IronUTF cannot show GSAi models because the API returns 404 for provider ID `gsai-api-1`, while Simple Chat works because it uses a hardcoded fallback list in `token_manager.py`.

## How Simple Chat Works

Simple Chat has a three-tier approach:
1. **Dynamic Discovery**: Tries to discover routes from APISIX
2. **Fallback List**: Uses hardcoded endpoints in `token_manager.py`
3. **GSAi Models**: Hardcoded in fallback with all models pointing to `/ai/gsai-api-1/chat/completions`

```python
# From token_manager.py
self.fallback_apisix_endpoints = {
    "gsai-api-1": {
        "claude_3_5_sonnet": "/ai/gsai-api-1/chat/completions",
        "claude_3_7_sonnet": "/ai/gsai-api-1/chat/completions",
        "llama3211b": "/ai/gsai-api-1/chat/completions",
        # ... more models
    }
}
```

## Simple Fix for IronUTF

### Option 1: Quick API Fix (Recommended for Immediate Relief)

Update the API to recognize `gsai-api-1` in the hardcoded models check:

**File**: `violentutf_api/fastapi_app/app/api/endpoints/generators.py`
**Function**: `discover_apisix_models_enhanced`

```python
# Change from:
if provider_id == "gsai":

# To:
if provider_id == "gsai" or provider == "gsai-api-1":
```

This minimal change will make the API return the hardcoded GSAi models for IronUTF.

### Option 2: Add Fallback to IronUTF (More Robust)

Add a fallback mechanism to IronUTF similar to Simple Chat:

**File**: `violentutf/pages/IronUTF.py`
**Function**: `fetch_available_models`

```python
def fetch_available_models(provider_id: str) -> List[str]:
    """Fetch available models for a provider from the API."""
    # Hardcoded fallback for known providers
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
        ]
    }
    
    try:
        headers = get_auth_headers()
        api_base = VIOLENTUTF_API_URL
        url = f"{api_base}/api/v1/generators/apisix/models?provider={provider_id}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            logger.info(f"Fetched {len(models)} models for provider {provider_id}")
            return models
        else:
            logger.warning(f"Failed to fetch models for {provider_id}: {response.status_code}")
            # Use fallback if available
            if provider_id in FALLBACK_MODELS:
                logger.info(f"Using fallback models for {provider_id}")
                return FALLBACK_MODELS[provider_id]
            return []
    except Exception as e:
        logger.error(f"Error fetching models for {provider_id}: {e}")
        # Use fallback if available
        if provider_id in FALLBACK_MODELS:
            logger.info(f"Using fallback models for {provider_id} after error")
            return FALLBACK_MODELS[provider_id]
        return []
```

## Implementation Steps

### For Option 1 (API Fix):
1. Update `discover_apisix_models_enhanced` function to recognize `gsai-api-1`
2. Test with IronUTF to confirm models appear
3. No UI changes needed

### For Option 2 (IronUTF Fallback):
1. Add `FALLBACK_MODELS` dictionary to IronUTF
2. Update `fetch_available_models` to use fallback when API fails
3. Add info message when using fallback models
4. Test with GSAi provider

## Testing

1. Open IronUTF
2. Select a GSAi route (e.g., `[GSAI] gsai-api-1 (/ai/gsai-api-1/chat/completions)`)
3. Verify model dropdown shows GSAi models
4. Test configuration with a selected model

## Advantages

**Option 1 (API Fix)**:
- Minimal code change (1 line)
- Consistent with existing hardcoded approach
- Works for all UIs that call the API

**Option 2 (IronUTF Fallback)**:
- More robust (works even if API is down)
- Consistent with Simple Chat approach
- Can be extended for other providers

## Recommendation

**Short-term**: Implement Option 1 (API fix) immediately for quick relief
**Medium-term**: Add Option 2 (fallback) for robustness
**Long-term**: Implement the comprehensive provider registry solution

This approach provides immediate relief while maintaining consistency with how Simple Chat already works successfully.