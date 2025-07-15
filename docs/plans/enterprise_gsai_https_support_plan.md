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

## Identified Gaps and Solutions

### 1. URL Parsing Logic
**Gap**: The plan doesn't show how to extract scheme from `OPENAPI_1_BASE_URL` automatically.
**Solution**: Create a URL parsing function that extracts scheme, host, and port from the base URL:
```bash
parse_url() {
    local url="$1"
    # Extract scheme
    if [[ "$url" =~ ^https:// ]]; then
        echo "scheme=https"
    elif [[ "$url" =~ ^http:// ]]; then
        echo "scheme=http"
    else
        echo "scheme=http"  # Default
    fi
    # Extract host and port...
}
```

### 2. Certificate Path Handling
**Gap**: Need to handle multiple certificate locations and formats.
**Solution**: Check common enterprise certificate locations:
```bash
CERT_SEARCH_PATHS=(
    "/etc/ssl/certs/enterprise-ca.crt"
    "/usr/local/share/ca-certificates/"
    "/etc/pki/tls/certs/"
    "$HOME/.ssl/enterprise/"
)
```

### 3. Rollback Strategy
**Gap**: No rollback mechanism if HTTPS setup fails.
**Solution**: Implement configuration backup and restore:
```bash
# Backup current route before modification
backup_route() {
    curl -s "http://localhost:9180/apisix/admin/routes/$1" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" > "/tmp/route_$1_backup.json"
}

# Restore on failure
restore_route() {
    curl -X PUT "http://localhost:9180/apisix/admin/routes/$1" \
        -H "X-API-KEY: $APISIX_ADMIN_KEY" \
        -d @"/tmp/route_$1_backup.json"
}
```

### 4. Health Check Updates
**Gap**: Health checks might still use HTTP even when main route uses HTTPS.
**Solution**: Update health check configuration to match main route scheme.

### 5. Migration Path
**Gap**: No clear migration path for existing deployments.
**Solution**: Create migration script that updates existing routes to support HTTPS.

## Implementation Todo List

### Phase 1: Configuration Updates (Priority: High)
1. **Update ai-tokens.env.template**
   - Add `OPENAPI_1_USE_HTTPS` flag
   - Add `OPENAPI_1_SSL_VERIFY` flag
   - Add `OPENAPI_1_CA_CERT_PATH` for custom CA certificates
   - Add comments explaining enterprise vs local usage

2. **Create URL parsing function**
   - Extract scheme from `OPENAPI_1_BASE_URL` automatically
   - Parse host and port correctly for both HTTP/HTTPS
   - Handle edge cases (no scheme, custom ports)

3. **Update environment validation**
   - Check for conflicting settings (HTTPS URL with USE_HTTPS=false)
   - Validate certificate paths if SSL_VERIFY=true
   - Warn about insecure configurations

### Phase 2: Route Creation Logic (Priority: High)
4. **Modify openapi_setup.sh - create_openapi_route function**
   - Auto-detect scheme from BASE_URL
   - Set upstream scheme based on configuration
   - Add SSL verification parameters
   - Update both ai-proxy and proxy-rewrite plugins

5. **Fix GSAi-specific route handling**
   - Update `fix_gsai_route_after_init` function
   - Ensure scheme matches configuration
   - Handle both HTTP and HTTPS modes

6. **Update health check endpoints**
   - Ensure health checks use correct scheme
   - Add SSL bypass for health checks if needed

### Phase 3: Certificate Management (Priority: Medium)
7. **Create certificate detection script**
   - Check common enterprise CA locations
   - Support multiple certificate formats (PEM, DER)
   - Validate certificate chain

8. **Implement certificate import function**
   - Copy certificates to APISIX container
   - Update APISIX SSL configuration
   - Handle certificate updates/rotation

9. **Add certificate troubleshooting**
   - Verify certificate validity
   - Test SSL handshake
   - Provide clear error messages

### Phase 4: Permission Management (Priority: Medium)
10. **Update Keycloak configuration**
    - Add configurable admin permissions
    - Create separate roles for route viewing vs editing
    - Document security implications

11. **Fix API permission checks**
    - Allow read-only route access for web users
    - Maintain admin-only write access
    - Add proper error messages

### Phase 5: Testing & Validation (Priority: High)
12. **Create test scripts**
    - Test HTTP mode (existing behavior)
    - Test HTTPS with self-signed certificates
    - Test HTTPS with enterprise CA
    - Test SSL verification on/off

13. **Add integration tests**
    - Test Streamlit → APISIX → GSAi flow
    - Verify token passing
    - Check error handling

14. **Create validation script**
    - Check route configuration
    - Verify SSL settings
    - Test actual API calls

### Phase 6: Documentation (Priority: Medium)
15. **Create enterprise deployment guide**
    - Step-by-step HTTPS configuration
    - Certificate management best practices
    - Troubleshooting common issues

16. **Update existing documentation**
    - Add HTTPS options to setup guide
    - Document new environment variables
    - Add security recommendations

17. **Create migration guide**
    - Steps to update existing HTTP deployments
    - Rollback procedures
    - Testing checklist

### Phase 7: Error Handling & Rollback (Priority: Medium)
18. **Implement graceful fallback**
    - Detect HTTPS failures
    - Option to fall back to HTTP
    - Clear error messages

19. **Add rollback mechanism**
    - Save previous route configuration
    - Restore on failure
    - Log all changes

20. **Improve error messages**
    - Clear SSL error descriptions
    - Actionable troubleshooting steps
    - Log correlation IDs

### Execution Timeline
- **Week 1**: Phase 1 & 2 (Configuration and core logic)
- **Week 2**: Phase 3 & 5 (Certificates and testing)
- **Week 3**: Phase 4 & 6 (Permissions and documentation)
- **Week 4**: Phase 7 (Error handling and final testing)

## Success Criteria
1. GSAi works seamlessly in both HTTP (local) and HTTPS (enterprise) modes
2. No manual intervention required for standard deployments
3. Clear error messages guide users through troubleshooting
4. Existing deployments can be migrated without downtime
5. Security best practices are enforced by default