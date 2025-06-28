# Planning: OpenAPI Routes Integration for ViolentUTF

## Executive Summary

This document outlines a comprehensive plan to integrate OpenAPI-compliant endpoints into ViolentUTF's existing architecture. The goal is to enable users to specify any OpenAPI-compliant API base URL, provide authentication credentials, and have the system automatically discover and configure APISIX routes for all available endpoints, making them accessible through the Streamlit interface for AI security testing.

## Current Architecture Analysis

### Existing AI Provider Integration
The current system follows a well-defined pattern for integrating AI providers:

1. **Configuration Management**: 
   - AI provider settings stored in `ai_tokens.env`
   - Providers can be enabled/disabled with boolean flags
   - API keys and endpoints are configurable per provider

2. **Route Creation Process**:
   - Shell script functions (`create_openai_route`, `create_anthropic_route`) generate APISIX route configurations
   - Routes use the `ai-proxy` plugin for authentication and request transformation
   - Each model gets a unique URI pattern: `/ai/{provider}/{model-alias}`

3. **Dynamic Discovery**:
   - FastAPI backend discovers available models from APISIX admin API
   - Streamlit UI dynamically populates dropdown menus with discovered models
   - Fallback to hardcoded model lists if discovery fails

## Proposed Solution Architecture

### Core Design Principles
1. **Minimal Code Changes**: Leverage existing patterns and infrastructure
2. **Dynamic Discovery**: Automatically extract all endpoints from OpenAPI specifications
3. **Seamless Integration**: OpenAPI endpoints should work like existing AI providers
4. **Flexible Authentication**: Support various authentication schemes defined in OpenAPI specs

### High-Level Implementation Plan

#### Phase 1: Configuration Extension

**Objective**: Extend the configuration system to support OpenAPI providers

**Tasks**:
1. Modify `ai_tokens.env` template to include OpenAPI provider section
2. Support multiple OpenAPI endpoints with unique identifiers
3. Store configuration parameters:
   - Provider ID (unique identifier)
   - Display name
   - Base URL
   - OpenAPI spec path (e.g., `/openapi.json`)
   - Authentication type and credentials
   - Custom headers (optional)

**Example Configuration**:
```bash
# OpenAPI Provider Configuration
OPENAPI_ENABLED=true

# OpenAPI Provider 1
OPENAPI_1_ID=custom-llm
OPENAPI_1_NAME="Custom LLM Service"
OPENAPI_1_BASE_URL=https://api.custom-llm.com
OPENAPI_1_SPEC_PATH=/openapi.json
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=sk-xxxxxx

# OpenAPI Provider 2  
OPENAPI_2_ID=internal-ai
OPENAPI_2_NAME="Internal AI API"
OPENAPI_2_BASE_URL=https://internal.company.com/ai/v1
OPENAPI_2_SPEC_PATH=/swagger.json
OPENAPI_2_AUTH_TYPE=api_key
OPENAPI_2_API_KEY=xxxxxx
OPENAPI_2_API_KEY_HEADER=X-API-Key
```

#### Phase 2: OpenAPI Discovery Module

**Objective**: Create functions to fetch and parse OpenAPI specifications

**Tasks**:
1. Add `fetch_openapi_spec()` function to retrieve specifications
   - Handle authentication for spec retrieval
   - Support both JSON and YAML formats
   - Cache specifications locally for performance

2. Add `parse_openapi_spec()` function to extract endpoints
   - Extract all paths and operations
   - Identify chat/completion endpoints (priority for LLM testing)
   - Extract security requirements per operation
   - Parse request/response schemas

3. Create `validate_openapi_spec()` function
   - Ensure OpenAPI 3.0+ compatibility
   - Validate required fields
   - Check for supported authentication schemes

#### Phase 3: Dynamic Route Generation

**Objective**: Automatically create APISIX routes from OpenAPI specifications

**Tasks**:
1. Create `setup_openapi_routes()` function in setup script
   - Iterate through configured OpenAPI providers
   - Fetch and parse each specification
   - Generate APISIX routes for discovered endpoints

2. Implement `create_openapi_route()` function
   - Generate route configuration using ai-proxy plugin
   - Map OpenAPI paths to APISIX URI patterns
   - Configure authentication based on security schemes
   - Set endpoint override to actual API URL

3. Route naming convention:
   - Pattern: `/ai/openapi/{provider-id}/{original-path}`
   - Example: `/chat/completions` → `/ai/openapi/custom-llm/chat/completions`

**Route Configuration Template**:
```json
{
  "id": "openapi-{provider-id}-{operation-id}",
  "uri": "/ai/openapi/{provider-id}{original-path}",
  "methods": ["POST"],
  "plugins": {
    "key-auth": {},
    "ai-proxy": {
      "provider": "openai-compatible",
      "auth": {
        "header": {
          "Authorization": "Bearer {token}"
        }
      },
      "override": {
        "endpoint": "{base-url}{original-path}"
      }
    }
  }
}
```

#### Phase 4: FastAPI Backend Enhancement

**Objective**: Extend backend to support OpenAPI providers

**Tasks**:
1. Update `discover_apisix_models()` to recognize OpenAPI routes
   - Parse route patterns containing `/ai/openapi/`
   - Extract provider ID and operation info
   - Map to human-readable model names

2. Extend generator configuration
   - Add "OpenAPI" as a generator type
   - Store OpenAPI-specific metadata
   - Support operation-specific parameters

3. Implement request transformation
   - Use OpenAPI schemas for request validation
   - Transform requests to match API expectations
   - Handle parameter mapping (query, header, body)

#### Phase 5: Streamlit UI Integration

**Objective**: Provide user-friendly interface for OpenAPI endpoints

**Tasks**:
1. Enhance provider discovery
   - Display OpenAPI providers alongside existing ones
   - Group operations by tags or paths
   - Show operation descriptions from OpenAPI spec

2. Dynamic parameter handling
   - Generate input forms based on OpenAPI schemas
   - Support required/optional parameters
   - Validate inputs according to schema constraints

3. Testing interface
   - Allow testing individual endpoints
   - Display request/response details
   - Show schema validation results

#### Phase 6: Advanced Features (Future Enhancement)

**Objective**: Provide enterprise-grade OpenAPI management

**Tasks**:
1. Batch import capabilities
   - Import multiple OpenAPI specs simultaneously
   - Handle spec versioning and updates
   - Manage naming conflicts

2. Route management UI
   - View all imported routes
   - Enable/disable specific operations
   - Update credentials without reimport
   - Delete provider configurations

3. Monitoring and analytics
   - Track usage per OpenAPI operation
   - Monitor success/failure rates
   - Generate compatibility reports

## Implementation Approach

### Step-by-Step Process

1. **Configuration Setup**
   - User adds OpenAPI provider details to `ai_tokens.env`
   - Includes base URL, auth credentials, and spec location

2. **Automatic Discovery**
   - Setup script fetches OpenAPI specification
   - Parses all available endpoints
   - Identifies AI-compatible operations (chat, completion, etc.)

3. **Route Creation**
   - Script generates APISIX routes for each operation
   - Configures authentication using ai-proxy plugin
   - Maps OpenAPI paths to APISIX URIs

4. **UI Integration**
   - FastAPI discovers new routes via APISIX admin API
   - Streamlit displays operations in dropdown menus
   - Users interact with endpoints like any other AI provider

### Technical Considerations

1. **Authentication Mapping**
   ```
   OpenAPI Security Scheme → APISIX Plugin Configuration
   - Bearer Token → auth.header.Authorization
   - API Key → auth.header[custom-header]
   - Basic Auth → auth.header.Authorization (base64)
   ```

2. **Path Parameter Handling**
   - OpenAPI: `/models/{model_id}/generate`
   - APISIX: `/ai/openapi/provider/models/*/generate`
   - Use wildcard matching for path parameters

3. **Error Handling**
   - Validate spec accessibility before processing
   - Handle malformed specifications gracefully
   - Provide clear error messages for auth failures
   - Log all route creation attempts

## Success Metrics

1. **Functionality**
   - Successfully import any OpenAPI 3.0+ specification
   - Create working routes for all discovered endpoints
   - Handle authentication transparently
   - Enable interaction through existing UI

2. **Performance**
   - Spec parsing completes within 30 seconds
   - Route creation scales to 100+ endpoints
   - No noticeable UI slowdown with many providers

3. **Usability**
   - Zero code changes required for new providers
   - Clear documentation for configuration
   - Intuitive error messages
   - Seamless integration with existing workflows

## Risk Mitigation

1. **Large Specifications**
   - Implement selective import (by tags/paths)
   - Add progress indicators during import
   - Cache parsed specifications

2. **Complex Authentication**
   - Start with common schemes (Bearer, API Key)
   - Document unsupported auth types
   - Provide manual override options

3. **Incompatible APIs**
   - Validate chat/completion compatibility
   - Provide compatibility warnings
   - Allow custom endpoint mapping

## Conclusion

This plan provides a comprehensive approach to integrating OpenAPI-compliant endpoints into ViolentUTF. By leveraging the existing architecture and patterns, we can add this powerful capability with minimal disruption while maintaining the system's security testing focus. The phased approach allows for incremental implementation and testing, ensuring a robust and reliable solution.