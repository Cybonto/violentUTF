# Guide: Implementing Model-Specific Routes for GSAi

## Overview

This guide provides options for enhancing the current GSAi endpoint structure to enable fine-grained control through model-specific routes. Currently, GSAi uses a single endpoint `/ai/gsai-api-1/chat/completions` where models are passed as parameters in the request body. This enhancement will create separate routes for each model, allowing for model-specific ai-proxy configurations.

## Current State

### Existing GSAi Route
- **Endpoint**: `/ai/gsai-api-1/chat/completions`
- **Model Selection**: Passed in request body as `"model": "claude_3_5_sonnet"`
- **Plugin Configuration**: Applied uniformly to all models
- **Example Request**:
  ```json
  POST /ai/gsai-api-1/chat/completions
  {
    "model": "claude_3_5_sonnet",
    "messages": [{"role": "user", "content": "Hello"}]
  }
  ```

## Objective

Transform the single endpoint into multiple model-specific endpoints while maintaining backward compatibility. This enables:
- Different rate limits per model (e.g., higher for cheap models, lower for expensive ones)
- Model-specific prompt filtering (stricter for more capable models)
- Custom token limits based on model capabilities
- Granular access control and monitoring
- Different caching strategies per model

## Implementation Options

### Option 1: Automatic Route Generation (Recommended for Quick Implementation)

Generate individual routes for each GSAi model during setup, creating endpoints like:
- `/ai/gsai-api-1/chat/completions/claude_3_5_sonnet`
- `/ai/gsai-api-1/chat/completions/claude_3_7_sonnet`
- `/ai/gsai-api-1/chat/completions/llama3211b`

**Implementation Example**:
```bash
#!/bin/bash
# Add to setup script after main GSAi route creation

GSAI_MODELS=(
    "claude_3_5_sonnet"
    "claude_3_7_sonnet"
    "claude_3_haiku"
    "llama3211b"
    "cohere_english_v3"
    "gemini-2.0-flash"
    "gemini-2.0-flash-lite"
    "gemini-2.5-pro-preview-05-06"
)

# Function to create model-specific route
create_gsai_model_route() {
    local model=$1
    local model_index=$2
    local route_id=$((9100 + model_index))
    
    curl -X PUT "http://localhost:9180/apisix/admin/routes/$route_id" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        -d '{
            "uri": "/ai/gsai-api-1/chat/completions/'$model'",
            "name": "GSAi '$model' Completions",
            "methods": ["POST"],
            "plugins": {
                "proxy-rewrite": {
                    "uri": "/api/v1/chat/completions",
                    "method": "POST"
                },
                "ai-proxy": {
                    "provider": "openai-compatible",
                    "override": {
                        "endpoint": "'$OPENAPI_1_BASE_URL'",
                        "model": "'$model'"
                    }
                },
                "ai-prompt-guard": {
                    "allow_patterns": [".*"],
                    "deny_patterns": []
                }
            },
            "upstream": {
                "type": "roundrobin",
                "scheme": "https",
                "nodes": {
                    "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
                }
            }
        }'
}

# Create routes for all models
for i in "${!GSAI_MODELS[@]}"; do
    create_gsai_model_route "${GSAI_MODELS[$i]}" "$i"
done
```

**Advantages**:
- Simple to implement in existing setup scripts
- Full control over each model's configuration
- Easy to understand and debug
- Maintains backward compatibility

**Disadvantages**:
- Creates many routes (8+ additional)
- More routes to manage in APISIX

### Option 2: Model Family Grouping

Group models by capability or provider for balanced granularity:
- `/ai/gsai-api-1/chat/completions/claude/*` → All Claude models
- `/ai/gsai-api-1/chat/completions/google/*` → All Gemini models
- `/ai/gsai-api-1/chat/completions/opensource/*` → LLaMA, Cohere, etc.

**Model Groupings**:
```yaml
claude_models:
  - claude_3_5_sonnet
  - claude_3_7_sonnet  
  - claude_3_haiku

google_models:
  - gemini-2.0-flash
  - gemini-2.0-flash-lite
  - gemini-2.5-pro-preview-05-06

opensource_models:
  - llama3211b
  - cohere_english_v3
```

**Advantages**:
- Fewer routes to manage
- Logical grouping by capabilities
- Easier to apply family-wide policies

**Disadvantages**:
- Less granular control
- Need routing logic for model selection

### Option 3: Configuration-Driven Routes (Best for Long-term)

Define routes and their configurations in a YAML file:

```yaml
# gsai-routes-config.yaml
gsai_model_routes:
  - model: claude_3_5_sonnet
    route_id: 9101
    rate_limit:
      requests_per_minute: 100
      tokens_per_minute: 100000
    prompt_guard:
      level: strict
      custom_deny_patterns:
        - "jailbreak"
        - "ignore previous"
    max_tokens: 4096
    
  - model: llama3211b
    route_id: 9102
    rate_limit:
      requests_per_minute: 200
      tokens_per_minute: 50000
    prompt_guard:
      level: moderate
    max_tokens: 2048
    
  - model: gemini-2.0-flash
    route_id: 9103
    rate_limit:
      requests_per_minute: 500
      tokens_per_minute: 200000
    prompt_guard:
      level: minimal
    max_tokens: 8192
```

**Route Generator Script**:
```python
#!/usr/bin/env python3
import yaml
import requests
import os

def generate_gsai_routes(config_file):
    with open(config_file) as f:
        config = yaml.safe_load(f)
    
    apisix_admin_key = os.getenv('APISIX_ADMIN_KEY')
    apisix_admin_url = "http://localhost:9180/apisix/admin/routes"
    
    for route in config['gsai_model_routes']:
        route_config = {
            "uri": f"/ai/gsai-api-1/chat/completions/{route['model']}",
            "name": f"GSAi {route['model']} Completions",
            "methods": ["POST"],
            "plugins": build_plugins_config(route),
            "upstream": {
                "type": "roundrobin",
                "scheme": "https",
                "nodes": {
                    "api.dev.gsai.mcaas.fcs.gsa.gov:443": 1
                }
            }
        }
        
        response = requests.put(
            f"{apisix_admin_url}/{route['route_id']}",
            json=route_config,
            headers={"X-API-KEY": apisix_admin_key}
        )
        print(f"Created route for {route['model']}: {response.status_code}")

def build_plugins_config(route):
    """Build plugins configuration based on route settings"""
    plugins = {
        "proxy-rewrite": {
            "uri": "/api/v1/chat/completions",
            "method": "POST"
        },
        "ai-proxy": {
            "provider": "openai-compatible",
            "override": {
                "endpoint": os.getenv('OPENAPI_1_BASE_URL'),
                "model": route['model']
            }
        }
    }
    
    # Add rate limiting if specified
    if 'rate_limit' in route:
        plugins['limit-req'] = {
            "rate": route['rate_limit']['requests_per_minute'],
            "burst": route['rate_limit']['requests_per_minute'] // 2,
            "key": "remote_addr"
        }
    
    # Add prompt guard with custom settings
    if 'prompt_guard' in route:
        guard_config = route['prompt_guard']
        if guard_config['level'] == 'strict':
            plugins['ai-prompt-guard'] = {
                "deny_patterns": [
                    "jailbreak", "ignore previous", "disregard instructions"
                ] + guard_config.get('custom_deny_patterns', [])
            }
        elif guard_config['level'] == 'moderate':
            plugins['ai-prompt-guard'] = {
                "deny_patterns": guard_config.get('custom_deny_patterns', [])
            }
    
    return plugins

if __name__ == "__main__":
    generate_gsai_routes("gsai-routes-config.yaml")
```

**Advantages**:
- Declarative configuration
- Easy to version control and review changes
- Model-specific settings in one place
- Supports complex plugin configurations

**Disadvantages**:
- Requires additional tooling
- More complex initial setup

## Model-Specific Configuration Examples

### High-Cost Model (Claude 3.5 Sonnet)
```json
{
    "plugins": {
        "limit-req": {
            "rate": 60,
            "burst": 10,
            "key": "consumer_name"
        },
        "ai-prompt-guard": {
            "deny_patterns": ["jailbreak", "ignore previous instructions"],
            "max_length": 2000
        },
        "ai-proxy": {
            "provider": "openai-compatible",
            "override": {
                "model": "claude_3_5_sonnet",
                "max_tokens": 4096
            }
        }
    }
}
```

### High-Volume Model (Gemini Flash)
```json
{
    "plugins": {
        "limit-req": {
            "rate": 300,
            "burst": 50,
            "key": "remote_addr"
        },
        "ai-prompt-guard": {
            "deny_patterns": [],
            "max_length": 5000
        },
        "proxy-cache": {
            "cache_ttl": 300,
            "cache_key": ["$uri", "$arg_messages"]
        }
    }
}
```

## Migration Strategy

1. **Keep existing endpoint**: `/ai/gsai-api-1/chat/completions` remains functional
2. **Add new endpoints**: Create model-specific routes alongside
3. **Gradual migration**: Update UIs to use new endpoints over time
4. **Deprecation notice**: Eventually phase out general endpoint

## UI Updates Required

### IronUTF
- Detect model-specific routes in route listing
- Use specific endpoint when available
- Fall back to general endpoint for compatibility

### Configure Generator
- Show model-specific routes when available
- Allow configuration of model-specific settings

## Benefits of Model-Specific Routes

1. **Performance Optimization**
   - Cache cheap model responses longer
   - Higher rate limits for efficient models
   - Lower timeouts for fast models

2. **Security & Compliance**
   - Stricter prompt filtering for powerful models
   - Model-specific access controls
   - Audit logging per model

3. **Cost Management**
   - Different rate limits based on model cost
   - Usage tracking per model
   - Budget alerts per model

4. **Operational Excellence**
   - Model-specific error handling
   - Targeted monitoring and alerts
   - A/B testing between models

## Next Steps

1. **Choose implementation option** based on your needs:
   - Option 1 for quick implementation
   - Option 3 for long-term maintainability

2. **Test with 2-3 models** before full rollout

3. **Update documentation** for the new endpoints

4. **Monitor usage patterns** to optimize configurations

5. **Gradually migrate UIs** to use model-specific endpoints