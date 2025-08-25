# Phase 1 OpenAPI Integration Guide

## Overview

Phase 1 of the OpenAPI integration enhancement brings dynamic model discovery to ViolentUTF. Instead of relying solely on static route parsing, the system now queries actual OpenAPI providers' `/api/v1/models` endpoints to discover available AI models in real-time.

## Key Features Implemented

### 1. Dynamic Model Discovery
- **Function**: `discover_openapi_models_from_provider()`
- **Purpose**: Queries OpenAPI providers' `/api/v1/models` endpoint
- **Benefits**: 
  - Real-time model availability
  - No manual configuration needed
  - Automatic updates when providers add/remove models

### 2. Enhanced Provider Configuration
- **Function**: `get_openapi_provider_config()`
- **Purpose**: Centralized provider configuration mapping
- **Supports**:
  - Numbered format: `OPENAPI_1_*`, `OPENAPI_2_*`, etc.
  - Direct format: `OPENAPI_GSAI_API_1_*`

### 3. Intelligent Discovery with Fallback
- **Function**: `discover_apisix_models_enhanced()`
- **Purpose**: Attempts dynamic discovery, falls back to route parsing
- **Benefits**: Robust operation even if provider APIs are temporarily unavailable

### 4. New API Endpoints

#### `/api/v1/generators/apisix/openapi-models`
- **Method**: GET
- **Purpose**: Get models for all configured OpenAPI providers
- **Response**: `{"openapi-provider-1": ["model1", "model2"], ...}`

#### `/api/v1/generators/apisix/openapi-debug`
- **Method**: GET  
- **Purpose**: Debug OpenAPI provider configurations
- **Response**: Comprehensive debugging information

## Implementation Details

### Enhanced Model Discovery Flow

```python
async def discover_apisix_models_enhanced(provider: str) -> List[str]:
    if provider.startswith("openapi-"):
        # 1. Get provider configuration from environment
        config = get_openapi_provider_config(provider_id)
        
        if config["base_url"] and config["auth_token"]:
            # 2. Try dynamic discovery from /api/v1/models
            models = await discover_openapi_models_from_provider(...)
            
            if models:
                return models  # Success!
        
    # 3. Fallback to existing route-based discovery
    return discover_apisix_models(provider)
```

### Error Handling

The implementation includes comprehensive error handling for:

- **403 Forbidden**: Invalid or expired authentication tokens
- **404 Not Found**: Provider doesn't support `/api/v1/models` endpoint
- **429 Rate Limited**: Provider is throttling requests
- **Network Errors**: Timeouts, connection failures
- **Parse Errors**: Unexpected response formats

### Configuration Support

The system supports flexible OpenAPI provider configuration:

```bash
# Numbered format (recommended)
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=gsai-api-1
OPENAPI_1_NAME="GSAi API Latest"
OPENAPI_1_BASE_URL=https://api.dev.gsai.mcaas.fcs.gsa.gov
OPENAPI_1_AUTH_TOKEN=your_bearer_token

# Direct format (alternative)
OPENAPI_GSAI_API_1_BASE_URL=https://api.dev.gsai.mcaas.fcs.gsa.gov
OPENAPI_GSAI_API_1_AUTH_TOKEN=your_bearer_token
```

## Testing and Validation

### Debug Endpoint Usage

Test your OpenAPI configuration:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:9080/api/v1/generators/apisix/openapi-debug
```

Expected response includes:
- `openapi_enabled`: Boolean status
- `discovered_providers`: List of found providers
- `provider_configs`: Configuration for each provider
- `environment_check`: Environment variable status
- `routes_check`: APISIX route status

### Model Discovery Testing

Test model discovery for all providers:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:9080/api/v1/generators/apisix/openapi-models
```

Test model discovery for specific provider:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     "http://localhost:9080/api/v1/generators/apisix/models?provider=openapi-gsai-api-1"
```

### Expected GSAi API Response

With proper configuration, the GSAi API should return:

```json
{
  "openapi-gsai-api-1": [
    "claude_3_5_sonnet",
    "claude_3_7_sonnet", 
    "claude_3_haiku",
    "llama3211b",
    "cohere_english_v3",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro-preview-05-06",
    "text-embedding-005"
  ]
}
```

## Integration with ViolentUTF UI

### Streamlit Configuration

The Streamlit interface now includes the new endpoint:

```python
API_ENDPOINTS = {
    # ... existing endpoints ...
    "openapi_models": f"{API_BASE_URL}/api/v1/generators/apisix/openapi-models",
}
```

### Model Selection Flow

1. **Provider Selection**: User selects "openapi-gsai-api-1" as provider
2. **Dynamic Model Loading**: Frontend calls `/apisix/models?provider=openapi-gsai-api-1`
3. **Real-time Discovery**: Backend queries GSAi `/api/v1/models` endpoint
4. **Model Population**: Dropdown populated with actual available models

## Troubleshooting

### Common Issues

#### 1. No Models Discovered
**Symptoms**: Empty model lists for OpenAPI providers
**Causes**:
- Invalid authentication token
- Incorrect base URL
- Provider API temporarily unavailable
- Network connectivity issues

**Solutions**:
1. Check debug endpoint: `/apisix/openapi-debug`
2. Verify `OPENAPI_1_AUTH_TOKEN` is valid
3. Test provider API directly with curl
4. Check FastAPI logs for error details

#### 2. Authentication Errors
**Symptoms**: 403 Forbidden responses
**Causes**:
- Expired bearer token
- Incorrect token format
- Missing Authorization header

**Solutions**:
1. Verify token validity with provider
2. Ensure `OPENAPI_1_AUTH_TOKEN` includes the full token
3. Check token isn't expired

#### 3. Provider Not Found
**Symptoms**: No OpenAPI providers in generator configuration
**Causes**:
- `OPENAPI_ENABLED=false`
- Missing provider configuration
- APISIX routes not created

**Solutions**:
1. Verify `OPENAPI_ENABLED=true` in ai-tokens.env
2. Run setup script to create routes
3. Check APISIX admin API for OpenAPI routes

### Debugging Commands

Check environment variables:
```bash
docker exec violentutf_api printenv | grep OPENAPI
```

Check FastAPI logs:
```bash
docker logs violentutf_api --tail 50 | grep -i openapi
```

Test provider directly:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models
```

## Performance Considerations

### Caching Strategy
- Model discovery results are not cached in Phase 1
- Each request triggers a new API call to the provider
- Future phases will implement intelligent caching

### Timeout Settings
- API calls timeout after 10 seconds
- Network errors trigger fallback to route parsing
- Provides graceful degradation

### Async Implementation
- All model discovery is async
- Non-blocking for other API operations
- Concurrent discovery for multiple providers

## Next Steps

Phase 1 provides the foundation for advanced OpenAPI integration. Future phases will add:

1. **Phase 2**: Smart operation mapping and model-specific parameters
2. **Phase 3**: Comprehensive error handling and provider health monitoring
3. **Phase 4**: Advanced caching and performance optimization
4. **Phase 5**: Token management and automatic refresh

## Conclusion

Phase 1 successfully implements dynamic model discovery for OpenAPI providers, eliminating the need for manual model configuration and providing real-time model availability. The implementation is robust, with proper error handling and fallback mechanisms to ensure system reliability.

The GSAi API integration serves as a reference implementation, demonstrating how ViolentUTF can seamlessly integrate with any OpenAI-compatible API provider.