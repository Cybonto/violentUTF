# OpenAPI Integration Guide

## Overview

ViolentUTF now supports automatic integration with any OpenAPI 3.0+ compliant API. This feature allows you to:

- Automatically discover and import API endpoints from OpenAPI specifications
- Create APISIX routes for all discovered endpoints
- Use OpenAPI endpoints through the Streamlit interface just like built-in AI providers
- Test API security with PyRIT orchestrators

## Prerequisites

- ViolentUTF installation completed
- Access to an OpenAPI 3.0+ compliant API
- API credentials (Bearer token, API key, or Basic auth)

## Configuration

### Step 1: Configure OpenAPI Provider

Edit the `ai_tokens.env` file in your ViolentUTF directory and add your OpenAPI provider configuration:

```bash
# Enable OpenAPI providers
OPENAPI_ENABLED=true

# Configure your OpenAPI provider
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=myapi
OPENAPI_1_NAME="My Custom AI API"
OPENAPI_1_BASE_URL=https://api.myservice.com
OPENAPI_1_SPEC_PATH=/openapi.json
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=sk-your-api-token-here
```

### Configuration Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `OPENAPI_ENABLED` | Master switch for OpenAPI providers | `true` |
| `OPENAPI_N_ENABLED` | Enable specific provider (N=1-10) | `true` |
| `OPENAPI_N_ID` | Unique identifier for the provider | `myapi` |
| `OPENAPI_N_NAME` | Display name for the provider | `"My Custom AI API"` |
| `OPENAPI_N_BASE_URL` | Base URL of the API | `https://api.myservice.com` |
| `OPENAPI_N_SPEC_PATH` | Path to OpenAPI specification | `/openapi.json` |
| `OPENAPI_N_AUTH_TYPE` | Authentication type | `bearer`, `api_key`, `basic` |

### Authentication Types

#### Bearer Token
```bash
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=your-bearer-token
```

#### API Key
```bash
OPENAPI_1_AUTH_TYPE=api_key
OPENAPI_1_API_KEY=your-api-key
OPENAPI_1_API_KEY_HEADER=X-API-Key
```

#### Basic Authentication
```bash
OPENAPI_1_AUTH_TYPE=basic
OPENAPI_1_BASIC_USERNAME=username
OPENAPI_1_BASIC_PASSWORD=password
```

### Custom Headers (Optional)

Add custom headers if required by your API:

```bash
OPENAPI_1_CUSTOM_HEADERS="X-Custom-Header:value,X-Another-Header:value2"
```

## Multiple OpenAPI Providers

You can configure up to 10 OpenAPI providers by using `OPENAPI_1` through `OPENAPI_10`:

```bash
# Provider 1
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=provider1
OPENAPI_1_NAME="Provider One"
# ... other settings

# Provider 2
OPENAPI_2_ENABLED=true
OPENAPI_2_ID=provider2
OPENAPI_2_NAME="Provider Two"
# ... other settings
```

## Setup Process

### Step 2: Run Setup Script

After configuring your OpenAPI providers, run the setup script:

```bash
./setup_macos.sh
```

The setup script will:

1. **Fetch OpenAPI Specifications**: Download the OpenAPI spec from each configured provider
2. **Validate Specifications**: Ensure specs are OpenAPI 3.0+ compliant
3. **Parse Endpoints**: Extract all paths and operations
4. **Create APISIX Routes**: Generate routes for each endpoint with proper authentication
5. **Report Results**: Show summary of created routes

### What Happens During Setup

For each OpenAPI provider, the system will:

1. Fetch the OpenAPI specification from `BASE_URL + SPEC_PATH`
2. Validate it's a valid OpenAPI 3.0+ specification
3. Extract all endpoints (paths + operations)
4. Prioritize AI-related endpoints (containing keywords like "chat", "completion", "generate")
5. Create APISIX routes with pattern: `/ai/openapi/{provider-id}/{original-path}`
6. Configure authentication using the ai-proxy plugin

Example route mapping:
- Original: `POST https://api.myservice.com/v1/chat/completions`
- APISIX Route: `POST http://localhost:9080/ai/openapi/myapi/v1/chat/completions`

## Using OpenAPI Endpoints

### Step 3: Access in Streamlit UI

1. Navigate to **Configure Generators** in the Streamlit interface
2. Select **AI Gateway** as the Generator Technology
3. Your OpenAPI provider will appear in the **AI Provider** dropdown as `openapi-{provider-id}`
4. Select your provider to see available operations in the **AI Model** dropdown
5. Configure and save the generator

### Step 4: Test with PyRIT

Once configured, you can test your OpenAPI endpoints using PyRIT orchestrators:

1. Create a new orchestrator in the **Run PyRIT Orchestrators** page
2. Select your OpenAPI generator as the target
3. Run security tests just like with built-in providers

## Troubleshooting

### OpenAPI Spec Not Found

If the setup script can't fetch your OpenAPI spec:
- Verify the URL is correct: `BASE_URL + SPEC_PATH`
- Check if authentication is required to access the spec
- Try accessing the spec URL directly in a browser

### Authentication Failures

If routes are created but API calls fail:
- Verify your authentication credentials are correct
- Check if the API requires additional headers
- Review APISIX logs: `docker logs violentutf-apisix-1`

### No Endpoints Discovered

If no endpoints are found in your OpenAPI spec:
- Ensure the spec is OpenAPI 3.0+ (not Swagger 2.0)
- Check if the spec has valid paths defined
- Verify the spec is valid JSON or YAML

### Routes Not Appearing in UI

If your OpenAPI provider doesn't appear in Streamlit:
- Restart the FastAPI service: `docker restart violentutf_api`
- Check FastAPI logs: `docker logs violentutf_api`
- Verify routes were created: `curl -H "X-API-KEY: your-key" http://localhost:9180/apisix/admin/routes`

## Advanced Configuration

### Filtering Endpoints

To import only specific endpoints, you can modify the parsing logic in `setup_macos.sh`:

```bash
# Only import endpoints with specific tags
if [[ " ${endpoint['tags']} " =~ " ai " ]]; then
    # Create route
fi
```

### Custom Route Patterns

Modify the URI pattern in `create_openapi_route()`:

```bash
local uri="/ai/openapi/${provider_id}${endpoint_path}"
# Change to:
local uri="/custom/prefix/${provider_id}${endpoint_path}"
```

### Request/Response Transformation

Add transformation plugins to the route configuration:

```json
"plugins": {
    "key-auth": {},
    "ai-proxy": { ... },
    "request-transformer": {
        "headers": {
            "add": {"X-Custom": "value"}
        }
    }
}
```

## Example: Integrating a Custom LLM API

Here's a complete example of integrating a custom LLM API:

1. **Configure in ai_tokens.env**:
```bash
OPENAPI_ENABLED=true
OPENAPI_1_ENABLED=true
OPENAPI_1_ID=customllm
OPENAPI_1_NAME="Custom LLM Service"
OPENAPI_1_BASE_URL=https://llm.company.internal
OPENAPI_1_SPEC_PATH=/api/v1/openapi.json
OPENAPI_1_AUTH_TYPE=bearer
OPENAPI_1_AUTH_TOKEN=eyJhbGciOiJIUzI1NiIs...
```

2. **Run setup**:
```bash
./setup_macos.sh
```

3. **Output**:
```
Processing OpenAPI provider: Custom LLM Service (customllm)
----------------------------------------
Fetching OpenAPI spec from https://llm.company.internal/api/v1/openapi.json...
✅ Successfully fetched OpenAPI spec
✅ Valid JSON format
✅ OpenAPI version: 3.0.2
✅ Found 5 endpoints
Creating APISIX routes for discovered endpoints...
✅ Created route: /ai/openapi/customllm/v1/chat/completions
✅ Created route: /ai/openapi/customllm/v1/embeddings
✅ Created route: /ai/openapi/customllm/v1/models
...
```

4. **Use in Streamlit**:
- Provider: `openapi-customllm`
- Models: `createChatCompletion`, `createEmbedding`, etc.

## Security Considerations

- **Credentials**: Store API tokens securely in `ai_tokens.env` (excluded from git)
- **HTTPS**: Always use HTTPS for production APIs
- **Network**: Ensure your ViolentUTF instance can reach the API endpoints
- **Rate Limits**: Be aware of API rate limits when running security tests

## Limitations

- Only OpenAPI 3.0+ specifications are supported (not Swagger 2.0)
- Maximum 10 OpenAPI providers can be configured
- Path parameters in URLs are converted to wildcards for APISIX routing
- OAuth2 flows are not automatically handled (use Bearer tokens instead)