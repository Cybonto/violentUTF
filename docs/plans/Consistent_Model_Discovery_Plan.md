# Plan: Implementing Consistent Model Discovery Across All UIs (Future Enhancement)

## Executive Summary

**Note**: This is a comprehensive long-term plan. For immediate IronUTF fixes, see `IronUTF_Simple_Fix_Plan.md`.

This plan addresses the inconsistent model discovery behavior between Configure Generator and IronUTF, particularly for GSAi and other OpenAPI providers. The goal is to create a unified, reliable model discovery system that works consistently across all ViolentUTF interfaces.

## Current State Analysis

### Problems Identified

1. **Provider ID Inconsistency**
   - Environment configuration uses: `OPENAPI_1_ID=gsai-api-1`
   - API hardcoded check expects: `provider_id == "gsai"`
   - Route URIs contain: `/ai/gsai-api-1/chat/completions`
   - No unified mapping between these formats

2. **Hardcoded Models Workaround**
   - GSAi models endpoint has persistent issues (403 errors, AWS OIDC problems)
   - Hardcoded list only works for specific provider ID format
   - No fallback mechanism for other OpenAPI providers

3. **Inconsistent UI Behavior**
   - Configure Generator and IronUTF call same API but may have different error handling
   - No clear feedback when model discovery fails
   - Users confused why models appear in one UI but not another

## Proposed Solution Architecture

### 1. Provider Registry Service

Create a centralized provider registry that maintains:
- Provider ID mappings (e.g., `gsai-api-1` → `gsai`)
- Provider capabilities and metadata
- Fallback model lists where needed
- Health status of provider endpoints

### 2. Enhanced Model Discovery API

Improve the `/api/v1/generators/apisix/models` endpoint to:
- Handle multiple provider ID formats
- Implement smart fallbacks
- Cache successful discoveries
- Provide detailed error responses

### 3. Consistent UI Integration

Ensure all UIs:
- Use the same model discovery API
- Handle errors gracefully with clear messages
- Show cached/fallback models when live discovery fails
- Indicate when using fallback data

## Implementation Steps

### Phase 1: Provider Registry (Week 1)

#### 1.1 Create Provider Configuration Schema
```python
class ProviderConfig:
    id: str                    # e.g., "gsai-api-1"
    canonical_name: str        # e.g., "gsai"
    display_name: str          # e.g., "GSAi (Government Services AI)"
    base_url: str
    auth_type: str
    capabilities: List[str]    # e.g., ["chat", "models", "embeddings"]
    fallback_models: Optional[List[str]]
    health_check_endpoint: Optional[str]
```

#### 1.2 Implement Provider Registry
- **Location**: `violentutf_api/fastapi_app/app/core/provider_registry.py`
- **Features**:
  - Load providers from environment configuration
  - Map various ID formats to canonical names
  - Store provider metadata and capabilities
  - Maintain fallback model lists

#### 1.3 Update Environment Configuration
- Add provider metadata to ai-tokens.env:
  ```bash
  OPENAPI_1_CANONICAL_NAME=gsai
  OPENAPI_1_DISPLAY_NAME="GSAi (Government Services AI)"
  OPENAPI_1_CAPABILITIES=chat,models
  OPENAPI_1_FALLBACK_MODELS=claude_3_5_sonnet,claude_3_7_sonnet,llama3211b
  ```

### Phase 2: Enhanced Model Discovery (Week 2)

#### 2.1 Refactor Model Discovery Function
```python
async def discover_models_unified(provider_id: str) -> ModelDiscoveryResult:
    """
    Unified model discovery with intelligent fallbacks
    
    Returns:
        ModelDiscoveryResult with:
        - models: List of available models
        - source: "live" | "cache" | "fallback"
        - timestamp: When models were discovered
        - error: Optional error message
    """
    # 1. Resolve provider ID to canonical form
    provider = registry.get_provider(provider_id)
    
    # 2. Try live discovery
    if provider.supports_model_discovery:
        models = await try_live_discovery(provider)
        if models:
            cache.set(provider.id, models)
            return ModelDiscoveryResult(models, "live")
    
    # 3. Try cache
    cached = cache.get(provider.id)
    if cached and not expired(cached):
        return ModelDiscoveryResult(cached.models, "cache")
    
    # 4. Use fallback
    if provider.fallback_models:
        return ModelDiscoveryResult(provider.fallback_models, "fallback")
    
    # 5. Return empty with error
    return ModelDiscoveryResult([], "error", error="No models available")
```

#### 2.2 Implement Caching Layer
- Cache successful model discoveries with TTL
- Store in Redis or in-memory cache
- Include timestamp and source metadata

#### 2.3 Update API Endpoint
- Modify `/api/v1/generators/apisix/models` to use unified discovery
- Return metadata about discovery source
- Include proper error messages

### Phase 3: UI Consistency (Week 3)

#### 3.1 Create Shared Model Discovery Hook
```python
# utils/model_discovery.py
def use_model_discovery(provider_id: str) -> ModelDiscoveryState:
    """React-style hook for model discovery in Streamlit"""
    
    @st.cache_data(ttl=300)  # 5 minute cache
    def fetch_models(provider_id):
        response = api_request("GET", f"/api/v1/generators/apisix/models?provider={provider_id}")
        return response
    
    result = fetch_models(provider_id)
    
    return ModelDiscoveryState(
        models=result.get("models", []),
        loading=False,
        error=result.get("error"),
        source=result.get("source", "unknown"),
        show_fallback_notice=result.get("source") == "fallback"
    )
```

#### 3.2 Update Configure Generator
- Replace direct API call with shared hook
- Show discovery source indicator
- Handle errors consistently

#### 3.3 Update IronUTF
- Use same shared hook
- Show same UI indicators
- Ensure consistent behavior

#### 3.4 Create UI Components
```python
def render_model_selector(provider_id: str, key: str):
    """Reusable model selector component"""
    discovery = use_model_discovery(provider_id)
    
    if discovery.loading:
        st.spinner("Discovering models...")
    
    if discovery.error and not discovery.models:
        st.error(f"Failed to discover models: {discovery.error}")
    
    if discovery.show_fallback_notice:
        st.info("ℹ️ Using cached model list. Live discovery temporarily unavailable.")
    
    selected = st.selectbox(
        "Select Model",
        options=discovery.models or ["No models available"],
        disabled=not discovery.models,
        key=key,
        help=f"Models from {discovery.source} source"
    )
    
    return selected
```

### Phase 4: Migration and Testing (Week 4)

#### 4.1 Migration Script
- Update existing configurations to new format
- Map old provider IDs to canonical names
- Preserve backward compatibility

#### 4.2 Comprehensive Testing
- Unit tests for provider registry
- Integration tests for model discovery
- End-to-end tests for both UIs
- Load testing for cache behavior

#### 4.3 Documentation Updates
- Update setup guides with new configuration
- Document provider registry system
- Create troubleshooting guide for model discovery

## Configuration Examples

### Example 1: GSAi with Fallback
```bash
# ai-tokens.env
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=gsai-api-1
OPENAPI_1_CANONICAL_NAME=gsai
OPENAPI_1_NAME="GSAi API Latest"
OPENAPI_1_BASE_URL=https://localhost
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=<token>
OPENAPI_1_CAPABILITIES=chat,models
OPENAPI_1_FALLBACK_MODELS=claude_3_5_sonnet,claude_3_7_sonnet,llama3211b,cohere_english_v3,gemini-2.0-flash
OPENAPI_1_MODEL_DISCOVERY_ENABLED=true
OPENAPI_1_MODEL_DISCOVERY_TIMEOUT=5000
```

### Example 2: Custom OpenAPI Provider
```bash
OPENAPI_2_ENABLED=true
OPENAPI_2_ID=custom-llm-api
OPENAPI_2_CANONICAL_NAME=custom
OPENAPI_2_NAME="Internal LLM Service"
OPENAPI_2_BASE_URL=https://llm.internal.company.com
OPENAPI_2_AUTH_TYPE=api_key
OPENAPI_2_AUTH_TOKEN=<api_key>
OPENAPI_2_CAPABILITIES=chat
OPENAPI_2_MODEL_DISCOVERY_ENABLED=false
OPENAPI_2_FALLBACK_MODELS=company-model-v1,company-model-v2
```

## Success Metrics

1. **Consistency**: Same models appear in all UIs for same provider
2. **Reliability**: 99% success rate for model discovery (live or fallback)
3. **Performance**: Model lists load within 2 seconds
4. **User Experience**: Clear indication of discovery source and any issues
5. **Maintainability**: Easy to add new providers without code changes

## Risk Mitigation

1. **Backward Compatibility**: Maintain support for old provider ID formats
2. **Graceful Degradation**: Always show something useful, even if live discovery fails
3. **Performance**: Implement caching to avoid repeated API calls
4. **Security**: Validate provider configurations to prevent injection attacks
5. **Monitoring**: Log all discovery attempts and failures for debugging

## Timeline

- **Week 1**: Provider Registry implementation
- **Week 2**: Enhanced Model Discovery API
- **Week 3**: UI updates and consistency
- **Week 4**: Testing, migration, and documentation
- **Week 5**: Deployment and monitoring

## Next Steps

1. Review and approve this plan
2. Create detailed technical specifications
3. Set up development branch
4. Begin Phase 1 implementation
5. Schedule weekly progress reviews