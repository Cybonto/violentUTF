# OpenAPI Integration Enhancement Plan

## Executive Summary

This plan outlines improvements to ViolentUTF's OpenAPI provider integration based on analysis of the GSAi API implementation. The current system successfully creates APISIX routes but needs enhancements for better model discovery, operation mapping, and error handling to fully leverage OpenAPI-compliant AI services.

## Current State Analysis

### GSAi API Structure
The GSAi API provides three main endpoints:
- **Models Endpoint**: `GET /api/v1/models` - Lists available AI models
- **Chat Completions**: `POST /api/v1/chat/completions` - OpenAI-compatible chat interface
- **Embeddings**: `POST /api/v1/embeddings` - Text embedding generation

### Current ViolentUTF Integration
✅ **Working Components**:
- APISIX route creation for OpenAPI endpoints
- Bearer token authentication configuration
- Basic operation ID mapping (`models_api_v1_models_get`, `converse_api_v1_chat_completions_post`, etc.)
- Route discovery in FastAPI backend

❌ **Issues Identified**:
1. **Model Discovery Gap**: No integration with `/api/v1/models` endpoint for dynamic model discovery
2. **Limited Operation Mapping**: Only routes are created, but model selection isn't connected to actual available models
3. **Error Handling**: No specific handling for 403/404/429/503 responses from OpenAPI providers
4. **Authentication Token Management**: Bearer tokens are configured but not validated or refreshed
5. **Model Parameter Mapping**: Temperature, max_tokens etc. not optimized for different model types

## Enhancement Plan

### Phase 1: Dynamic Model Discovery (High Priority)

#### 1.1 Enhanced Model Discovery Function
**File**: `violentutf_api/fastapi_app/app/api/endpoints/generators.py`

```python
async def discover_openapi_models_from_provider(provider_id: str, base_url: str, auth_token: str) -> List[str]:
    """
    Discover available models directly from OpenAPI provider's /models endpoint
    """
    try:
        models_url = f"{base_url.rstrip('/')}/api/v1/models"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(models_url, headers=headers, timeout=10.0)
            
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list):
                return [model["id"] for model in data["data"]]
        
        logger.warning(f"Failed to discover models from {provider_id}: HTTP {response.status_code}")
        return []
        
    except Exception as e:
        logger.error(f"Error discovering models from {provider_id}: {e}")
        return []
```

#### 1.2 Integration with Generator Configuration
Update the `discover_apisix_models` function to query the actual OpenAPI provider when available:

```python
def discover_apisix_models(provider: str) -> List[str]:
    """Enhanced version that queries OpenAPI providers directly"""
    if provider.startswith("openapi-"):
        provider_id = provider.replace("openapi-", "")
        
        # Get provider configuration from environment
        base_url = os.getenv(f"OPENAPI_{provider_id.upper()}_BASE_URL")
        auth_token = os.getenv(f"OPENAPI_{provider_id.upper()}_AUTH_TOKEN")
        
        if base_url and auth_token:
            models = await discover_openapi_models_from_provider(provider_id, base_url, auth_token)
            if models:
                return models
    
    # Fallback to existing APISIX route parsing
    return discover_apisix_models_from_routes(provider)
```

### Phase 2: Smart Operation Mapping (Medium Priority)

#### 2.1 Operation-to-Endpoint Intelligence
**File**: `violentutf_api/fastapi_app/app/utils/openapi_mapper.py` (new)

```python
class OpenAPIOperationMapper:
    """Maps OpenAPI operations to AI service functions"""
    
    OPERATION_PATTERNS = {
        "chat_completion": ["chat", "completion", "converse", "generate"],
        "embedding": ["embedding", "embed"],
        "model_list": ["models", "list"],
    }
    
    def classify_operation(self, operation_id: str, path: str, method: str) -> str:
        """Classify what type of AI operation this endpoint provides"""
        operation_lower = operation_id.lower()
        path_lower = path.lower()
        
        for op_type, patterns in self.OPERATION_PATTERNS.items():
            if any(pattern in operation_lower or pattern in path_lower for pattern in patterns):
                return op_type
        
        return "unknown"
    
    def get_model_parameter_mapping(self, operation_type: str) -> Dict[str, Any]:
        """Get appropriate parameter defaults for different operation types"""
        mappings = {
            "chat_completion": {
                "temperature": {"min": 0.0, "max": 2.0, "default": 0.7},
                "max_tokens": {"min": 1, "max": 4096, "default": 1000},
                "top_p": {"min": 0.0, "max": 1.0, "default": 1.0},
            },
            "embedding": {
                "encoding_format": {"default": "float", "options": ["float"]},
                "dimensions": {"min": 1, "max": 3072, "default": None},
            }
        }
        return mappings.get(operation_type, {})
```

#### 2.2 Enhanced Route Creation with Operation Classification
Update `create_openapi_route` in `setup_macos.sh`:

```bash
create_openapi_route_enhanced() {
    local provider_id="$1"
    local operation_id="$2"
    local path="$3"
    local method="$4"
    local operation_type="$5"  # New parameter: chat_completion, embedding, etc.
    
    # Create route with operation-specific configuration
    local route_config='{
        "uri": "'"$uri"'",
        "methods": ["'"$method"'"],
        "desc": "'"$provider_name"' '"$operation_type"': '"$operation_id"'",
        "labels": {
            "provider": "'"$provider_id"'",
            "operation_type": "'"$operation_type"'",
            "ai_service": "true"
        },
        "upstream": {
            "type": "roundrobin",
            "nodes": {"'"$hostname:$port"'": 1},
            "scheme": "'"$scheme"'"
        },
        "plugins": {
            "key-auth": {},
            "proxy-rewrite": {
                "regex_uri": ["^/ai/openapi/'"$provider_id"'(.*)", "$1"]
            },
            "response-rewrite": {
                "headers": {
                    "X-Provider-ID": "'"$provider_id"'",
                    "X-Operation-Type": "'"$operation_type"'"
                }
            }
        }
    }'
}
```

### Phase 3: Robust Error Handling (Medium Priority)

#### 3.1 OpenAPI Provider Health Monitoring
**File**: `violentutf_api/fastapi_app/app/utils/openapi_health.py` (new)

```python
class OpenAPIProviderHealth:
    """Monitor health and availability of OpenAPI providers"""
    
    async def check_provider_health(self, provider_id: str) -> Dict[str, Any]:
        """Check if OpenAPI provider is accessible and responsive"""
        base_url = os.getenv(f"OPENAPI_{provider_id.upper()}_BASE_URL")
        auth_token = os.getenv(f"OPENAPI_{provider_id.upper()}_AUTH_TOKEN")
        
        if not base_url or not auth_token:
            return {"status": "misconfigured", "error": "Missing configuration"}
        
        try:
            # Test models endpoint (lightweight check)
            models_url = f"{base_url.rstrip('/')}/api/v1/models"
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(models_url, headers=headers, timeout=5.0)
            
            if response.status_code == 200:
                return {"status": "healthy", "models_count": len(response.json().get("data", []))}
            elif response.status_code == 403:
                return {"status": "auth_error", "error": "Invalid or expired token"}
            elif response.status_code == 404:
                return {"status": "not_found", "error": "Models endpoint not found"}
            elif response.status_code == 429:
                return {"status": "rate_limited", "error": "Too many requests"}
            else:
                return {"status": "error", "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
```

#### 3.2 Enhanced Error Responses in Generator Endpoints
Update generator parameter discovery to handle provider errors gracefully:

```python
async def get_generator_type_params(generator_type: str, current_user=Depends(get_current_user)):
    """Enhanced version with OpenAPI provider health checks"""
    if generator_type == "AI Gateway":
        # ... existing code ...
        
        # Enhanced OpenAPI provider discovery with health checks
        openapi_providers = []
        if settings.OPENAPI_ENABLED:
            try:
                health_checker = OpenAPIProviderHealth()
                raw_providers = get_openapi_providers()
                
                for provider in raw_providers:
                    provider_id = provider.replace("openapi-", "")
                    health = await health_checker.check_provider_health(provider_id)
                    
                    if health["status"] == "healthy":
                        openapi_providers.append(provider)
                        logger.info(f"Provider {provider} is healthy with {health.get('models_count', 0)} models")
                    else:
                        logger.warning(f"Provider {provider} is unhealthy: {health['error']}")
                        
            except Exception as e:
                logger.error(f"Error checking OpenAPI provider health: {e}")
        
        # ... rest of function ...
```

### Phase 4: Advanced Model Configuration (Low Priority)

#### 4.1 Model-Specific Parameter Optimization
Create model-specific parameter templates based on discovered models:

```python
MODEL_PARAMETER_TEMPLATES = {
    # Anthropic Claude models
    "claude_3_5_sonnet": {
        "max_tokens": {"default": 4096, "max": 8192},
        "temperature": {"default": 0.7, "step": 0.1},
        "preferred_for": ["reasoning", "coding", "analysis"]
    },
    "claude_3_haiku": {
        "max_tokens": {"default": 1000, "max": 4096},
        "temperature": {"default": 0.5, "step": 0.1},
        "preferred_for": ["quick_responses", "classification"]
    },
    # Google Gemini models
    "gemini-2.0-flash": {
        "max_tokens": {"default": 2048, "max": 8192},
        "temperature": {"default": 0.8, "step": 0.1},
        "preferred_for": ["multimodal", "creativity"]
    },
    # Embedding models
    "text-embedding-005": {
        "dimensions": {"default": 768, "options": [768, 1536]},
        "input_type": {"default": "search_document", "options": ["search_document", "search_query", "classification"]}
    }
}
```

#### 4.2 Dynamic Parameter Generation
Update generator parameters to be model-aware:

```python
def get_model_specific_parameters(model_id: str, operation_type: str) -> List[Dict]:
    """Generate parameter definitions based on specific model capabilities"""
    base_params = get_base_parameters_for_operation(operation_type)
    
    if model_id in MODEL_PARAMETER_TEMPLATES:
        model_config = MODEL_PARAMETER_TEMPLATES[model_id]
        
        # Override defaults and constraints based on model
        for param in base_params:
            if param["name"] in model_config:
                param.update(model_config[param["name"]])
    
    return base_params
```

### Phase 5: Token Management & Security (High Priority)

#### 5.1 Token Validation and Refresh
**File**: `violentutf_api/fastapi_app/app/utils/openapi_auth.py` (new)

```python
class OpenAPITokenManager:
    """Manage authentication tokens for OpenAPI providers"""
    
    async def validate_token(self, provider_id: str) -> bool:
        """Validate that the current token is still valid"""
        base_url = os.getenv(f"OPENAPI_{provider_id.upper()}_BASE_URL")
        auth_token = os.getenv(f"OPENAPI_{provider_id.upper()}_AUTH_TOKEN")
        
        if not base_url or not auth_token:
            return False
        
        try:
            # Test with lightweight endpoint
            test_url = f"{base_url.rstrip('/')}/api/v1/models"
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(test_url, headers=headers, timeout=5.0)
            
            return response.status_code != 403
            
        except Exception:
            return False
    
    async def get_token_info(self, provider_id: str) -> Dict[str, Any]:
        """Get information about the token (if provider supports it)"""
        # Implementation depends on provider's token info endpoint
        return {"valid": await self.validate_token(provider_id)}
```

#### 5.2 Secure Token Storage
Update setup script to support more secure token management:

```bash
# Enhanced token validation in setup_macos.sh
validate_openapi_token() {
    local provider_id="$1"
    local base_url="$2"
    local auth_token="$3"
    
    echo "Validating OpenAPI token for provider: $provider_id"
    
    local test_response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $auth_token" \
        -H "Accept: application/json" \
        "$base_url/api/v1/models" 2>/dev/null)
    
    local http_code="${test_response: -3}"
    
    case "$http_code" in
        "200")
            echo "✅ Token valid for $provider_id"
            return 0
            ;;
        "403")
            echo "❌ Token invalid or expired for $provider_id"
            return 1
            ;;
        "404")
            echo "⚠️  Models endpoint not found for $provider_id (may not support this endpoint)"
            return 0  # Don't fail setup for this
            ;;
        *)
            echo "⚠️  Could not validate token for $provider_id (HTTP $http_code)"
            return 0  # Don't fail setup for network issues
            ;;
    esac
}
```

## Implementation Timeline

### Week 1: Foundation
- [ ] Implement dynamic model discovery from `/api/v1/models` endpoint
- [ ] Update FastAPI generator configuration to use real model lists
- [ ] Add basic error handling for provider connectivity issues

### Week 2: Intelligence
- [ ] Create OpenAPI operation classification system
- [ ] Implement model-specific parameter templates
- [ ] Add provider health monitoring

### Week 3: Robustness
- [ ] Implement comprehensive error handling (403, 404, 429, 503)
- [ ] Add token validation and management
- [ ] Create provider status monitoring dashboard

### Week 4: Integration & Testing
- [ ] Update setup script with enhanced validation
- [ ] Add integration tests for OpenAPI providers
- [ ] Create user documentation for OpenAPI configuration

## Success Metrics

### Technical Metrics
- [ ] **Model Discovery Accuracy**: 100% of available models from `/api/v1/models` appear in ViolentUTF UI
- [ ] **Error Handling Coverage**: All HTTP error codes (403, 404, 429, 503) handled gracefully
- [ ] **Token Validation**: Automatic detection of invalid/expired tokens
- [ ] **Provider Health**: Real-time status monitoring for all configured providers

### User Experience Metrics
- [ ] **Setup Success Rate**: >95% successful OpenAPI provider configuration
- [ ] **Error Clarity**: Clear, actionable error messages for misconfigurations
- [ ] **Model Selection**: Accurate model lists without manual maintenance
- [ ] **Parameter Optimization**: Model-specific parameter defaults and constraints

## Risk Mitigation

### High Risk: Provider API Changes
- **Mitigation**: Implement fallback mechanisms and version detection
- **Monitoring**: Regular health checks and automated testing

### Medium Risk: Authentication Token Expiry
- **Mitigation**: Token validation before each operation
- **Recovery**: Clear error messages and renewal guidance

### Low Risk: Performance Impact
- **Mitigation**: Async operations and caching for model discovery
- **Monitoring**: Response time tracking and optimization

## Conclusion

This enhancement plan transforms ViolentUTF's OpenAPI integration from basic route creation to intelligent, robust provider management. The phased approach ensures incremental value delivery while maintaining system stability. The focus on the GSAi API as the primary use case ensures real-world validation of all enhancements.

Key benefits of this implementation:
1. **Dynamic Discovery**: Automatic model discovery eliminates manual configuration
2. **Intelligent Mapping**: Operation classification enables optimized parameter defaults
3. **Robust Error Handling**: Graceful handling of all provider error conditions
4. **Security Enhancement**: Token validation and management improve reliability
5. **User Experience**: Clear feedback and automatic configuration reduce setup complexity

The plan prioritizes high-impact, low-risk improvements first, ensuring immediate value while building toward comprehensive OpenAPI provider support.