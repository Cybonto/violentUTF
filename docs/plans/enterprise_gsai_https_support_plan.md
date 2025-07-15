# Enterprise GSAi HTTPS Support Plan

## Problem Summary

In enterprise environments, GSAi runs with HTTPS and valid SSL certificates, but the current ViolentUTF setup assumes GSAi uses HTTP. This causes:
1. APISIX sends HTTP requests to HTTPS ports, resulting in "400 Bad Request - The plain HTTP request was sent to HTTPS port"
2. AI Gateway requests fail in the Streamlit app
3. Service discovery errors in APISIX logs

## Current State Analysis

### Local Environment (Working)
- GSAi runs on HTTP (port 8080)
- APISIX routes configured with `scheme: http`
- No SSL verification needed
- Direct container-to-container communication

### Enterprise Environment (Failing)
- GSAi runs on HTTPS with valid certificates
- APISIX routes still using `scheme: http`
- SSL certificates not configured in routes
- HTTP/HTTPS mismatch causes connection failures

## Proposed Solution

### 1. Environment-Aware Configuration

Add environment detection to `ai-tokens.env`:
```bash
# GSAi Configuration
OPENAPI_1_ENABLED=true
OPENAPI_1_NAME="GSAi API"
OPENAPI_1_BASE_URL="https://gsai.enterprise.com"  # Use HTTPS for enterprise
OPENAPI_1_AUTH_TOKEN="your-api-key"
OPENAPI_1_USE_HTTPS=true  # New flag for HTTPS
OPENAPI_1_SSL_VERIFY=true  # New flag for SSL verification
```

### 2. Update Route Creation Logic

Modify `openapi_setup.sh` to handle HTTPS properly:

```bash
# Determine scheme based on configuration
if [[ "${OPENAPI_1_USE_HTTPS:-false}" == "true" ]]; then
    scheme="https"
    ssl_verify="${OPENAPI_1_SSL_VERIFY:-true}"
else
    scheme="http"
    ssl_verify="false"
fi

# Update upstream configuration for HTTPS
if [[ "$scheme" == "https" ]]; then
    upstream_config='{
        "type": "roundrobin",
        "nodes": {
            "'"$host_port"'": 1
        },
        "scheme": "https",
        "pass_host": "node",
        "ssl_verify": '"$ssl_verify"'
    }'
fi
```

### 3. Fix AI-Proxy Plugin Configuration

The ai-proxy plugin needs proper HTTPS upstream configuration:

```json
{
    "ai-proxy": {
        "auth": {
            "header": {
                "Authorization": "Bearer <token>"
            }
        },
        "model": {
            "provider": "openai",
            "name": "gsai-model"
        },
        "upstream": {
            "scheme": "https",  // Must match actual GSAi scheme
            "host": "gsai.enterprise.com",
            "port": 443,
            "path": "/api/v1/chat/completions"
        },
        "ssl_verify": true
    }
}
```

### 4. Add SSL Certificate Management

For enterprise environments with custom CA certificates:

```bash
# In setup script, detect and import enterprise CA certs
if [ -f "/etc/ssl/certs/enterprise-ca.crt" ]; then
    # Copy CA cert to APISIX container
    docker cp /etc/ssl/certs/enterprise-ca.crt apisix-apisix-1:/usr/local/openresty/nginx/conf/ssl/
    
    # Update APISIX config to trust the CA
    docker exec apisix-apisix-1 sh -c 'echo "lua_ssl_trusted_certificate /usr/local/openresty/nginx/conf/ssl/enterprise-ca.crt;" >> /usr/local/apisix/conf/config-default.yaml'
fi
```

### 5. Update Permissions

The `violentutf.web` user needs proper permissions. Add to Keycloak setup:

```bash
# Grant APISIX admin access to web user for route inspection
# This should be configurable based on security requirements
if [[ "${GRANT_WEB_USER_ADMIN:-false}" == "true" ]]; then
    # Add admin role to web user
    echo "Granting admin permissions to web user..."
fi
```

## Implementation Steps

1. **Update Configuration Templates**
   - Add HTTPS flags to `ai-tokens.env.template`
   - Update route creation scripts to check these flags

2. **Modify Route Creation**
   - Update `openapi_setup.sh` to handle HTTPS schemes
   - Fix ai-proxy plugin upstream configuration
   - Add SSL verification options

3. **Add Certificate Management**
   - Detect enterprise CA certificates
   - Import them into APISIX container
   - Configure APISIX to trust custom CAs

4. **Test Both Environments**
   - Local: HTTP without SSL (current behavior)
   - Enterprise: HTTPS with SSL verification

5. **Documentation Updates**
   - Add enterprise deployment guide
   - Document HTTPS configuration options
   - Add troubleshooting for SSL issues

## Backward Compatibility

- Default behavior remains HTTP for local development
- HTTPS only activated when explicitly configured
- No breaking changes to existing deployments

## Security Considerations

1. **SSL Verification**: Default to `true` for production
2. **Certificate Storage**: Store CA certs securely
3. **Token Management**: Use environment-specific tokens
4. **Permission Model**: Configure based on enterprise requirements

## Testing Plan

1. Test HTTP mode (local development)
2. Test HTTPS with self-signed certs
3. Test HTTPS with enterprise CA
4. Test SSL verification on/off
5. Verify error handling for certificate issues