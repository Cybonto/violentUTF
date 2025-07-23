# Custom OpenAPI SSL Integration Issues and Solutions

## Overview

This document covers challenges and solutions encountered when integrating Custom OpenAPI providers (like local API services and enterprise AI gateways) with APISIX AI Gateway, particularly focusing on SSL certificate handling and plugin compatibility.

## Current Solution: Configurable HTTPS Support

**As of July 2025:** ViolentUTF now includes comprehensive HTTPS support with automatic scheme detection, SSL verification control, and custom CA certificate management. This allows seamless integration with enterprise AI gateways that use HTTPS with valid SSL certificates.

### Configuration

```bash
# In ai-tokens.env
OPENAPI_1_BASE_URL=https://gsai.enterprise.com
OPENAPI_1_USE_HTTPS=auto              # auto, true, or false
OPENAPI_1_SSL_VERIFY=true             # Verify SSL certificates
OPENAPI_1_CA_CERT_PATH=/path/to/enterprise-ca.crt  # Optional custom CA
```

### Key Features

1. **Automatic HTTPS Detection**: The `auto` setting detects scheme from BASE_URL
2. **SSL Verification Control**: Enable/disable certificate verification
3. **Custom CA Support**: Import enterprise CA certificates for trusted connections
4. **Backward Compatibility**: Existing HTTP deployments continue to work

For detailed HTTPS configuration, see the [OpenAPI Integration Guide](../guides/openapi-integration.md#enterprise-https-support).

## Alternative Solution: HTTP Configuration for Container-to-Container Communication

**Alternative Resolution:** For local development or container-to-container communication, you can configure providers to use HTTP instead of HTTPS:

- **Provider Configuration**: Run on HTTP port internally
- **APISIX Routes**: Use `scheme: "http"` for internal communication
- **Setup Scripts**: Automatically configure based on USE_HTTPS setting
- **SSL Certificates**: Not required for internal HTTP communication

This approach eliminates SSL certificate complexity for internal communication while maintaining security through the APISIX gateway authentication layer. However, for enterprise environments, the HTTPS configuration with proper certificates is recommended.

## Issue Summary

When integrating Custom OpenAPI providers that use self-signed SSL certificates (e.g., Caddy with automatic HTTPS), several integration challenges arise:

1. **SSL Certificate Verification Failures**: APISIX cannot verify self-signed certificates
2. **Plugin Compatibility**: `ai-proxy` plugin has limitations with custom SSL configurations
3. **Docker Network Connectivity**: Container-to-container HTTPS communication issues
4. **Route Configuration**: Proper upstream and host header configuration required

## Problem Details

### SSL Certificate Verification Issues

**Error Symptoms:**
- HTTP 500 Internal Server Error from APISIX
- APISIX logs showing SSL certificate parsing failures:
  ```
  [lua] ssl.lua:211: in function 'create_obj_fun'
  [lua] ssl.lua:217: in function 'fetch_cert' 
  SSL certificate verification failed
  ```
- ai-proxy plugin errors:
  ```
  [lua] openai-base.lua:198: phase_func(): failed to connect to LLM server: 19: self-signed certificate in certificate chain
  ```

**Root Cause:**
- Custom OpenAPI providers using Caddy or similar reverse proxies generate self-signed certificates that are not trusted by APISIX's default certificate store
- Enterprise AI gateways use internal CA certificates that APISIX doesn't trust by default
- The ai-proxy plugin performs SSL verification but cannot handle custom CA certificates without proper configuration

### AI-Proxy Plugin Limitations

**Issue:**
The `ai-proxy` plugin expects standard SSL configurations and may not handle custom certificate scenarios properly.

**Workaround:**
Use `proxy-rewrite` plugin instead, which provides more flexibility for custom SSL setups.

## Solutions Implemented

### 1. Certificate Trust Store Integration

**Approach:** Add Custom OpenAPI certificates to APISIX's trust store

**Steps:**
1. Extract certificates from Custom OpenAPI container:
   ```bash
   # Extract root CA certificate
   docker cp custom-api-caddy-1:/data/caddy/pki/authorities/local/root.crt /tmp/custom-root-ca.crt
   
   # Extract localhost certificate
   docker cp custom-api-caddy-1:/data/caddy/certificates/local/localhost/localhost.crt /tmp/custom-localhost.crt
   ```

2. Copy certificates to APISIX container:
   ```bash
   docker cp /tmp/custom-root-ca.crt apisix-apisix-1:/usr/local/share/ca-certificates/custom-root-ca.crt
   docker cp /tmp/custom-localhost.crt apisix-apisix-1:/usr/local/share/ca-certificates/custom-localhost.crt
   ```

3. Update certificate store:
   ```bash
   docker exec --user root apisix-apisix-1 update-ca-certificates
   ```

4. Restart APISIX to reload certificates:
   ```bash
   docker restart apisix-apisix-1
   ```

### 2. Proxy-Rewrite Configuration

**Route Configuration:**
```json
{
    "id": "9001",
    "uri": "/ai/custom-api-1/chat/completions",
    "name": "custom-api-1-chat-completions",
    "methods": ["POST"],
    "upstream": {
        "type": "roundrobin",
        "nodes": {
            "custom-api-caddy-1:443": 1
        },
        "scheme": "https",
        "pass_host": "rewrite",
        "upstream_host": "localhost",
        "tls": {
            "verify": true
        }
    },
    "plugins": {
        "cors": {
            "allow_origins": "http://localhost:8501,http://localhost:3000",
            "allow_methods": "GET,POST,OPTIONS",
            "allow_headers": "Authorization,Content-Type,X-Requested-With,apikey",
            "allow_credential": true,
            "max_age": 3600
        },
        "proxy-rewrite": {
            "uri": "/api/v1/chat/completions",
            "headers": {
                "set": {
                    "Host": "localhost",
                    "Authorization": "Bearer custom_api_token"
                }
            },
            "use_real_request_uri_unsafe": false
        }
    }
}
```

**Key Configuration Points:**
- `"pass_host": "rewrite"` with `"upstream_host": "localhost"` ensures proper Host header
- `"tls": {"verify": true}` enables SSL verification with trusted certificates
- `proxy-rewrite` plugin handles authentication and path rewriting
- CORS configuration allows Streamlit frontend access

### 3. Docker Network Configuration

**Requirement:** Both APISIX and Custom OpenAPI containers must be on the same Docker network.

**Implementation:**
```bash
# Ensure Custom OpenAPI stack uses vutf-network
# Rebuild Custom OpenAPI stack with network configuration
```

### 4. Detection Logic Updates

**TokenManager Updates:**
- Added detection for both `ai-proxy` and `proxy-rewrite` plugins
- Provider mapping from `custom-api-1` to `custom` provider type
- Fallback endpoints configuration for Custom OpenAPI models

**UI Component Updates:**
- IronUTF: Updated `detect_provider_type()` to recognize Custom OpenAPI routes
- Simple Chat: Provider selection and model display for Custom OpenAPI
- Configure Generator: Added Custom OpenAPI as provider option

## Testing and Validation

### Route Testing
```bash
# Test Custom OpenAPI route directly
curl -X POST \
  -H "apikey: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello, test message"}]}' \
  "http://localhost:9080/ai/custom-api-1/chat/completions"
```

### Certificate Verification
```bash
# Check certificate trust store in APISIX
docker exec apisix-apisix-1 ls -la /usr/local/share/ca-certificates/
docker exec apisix-apisix-1 openssl x509 -in /usr/local/share/ca-certificates/custom-root-ca.crt -text -noout
```

## Best Practices

1. **Certificate Management:**
   - Always use proper certificate trust store integration
   - Avoid `"verify": false` in production environments
   - Document certificate renewal procedures

2. **Plugin Selection:**
   - Use `proxy-rewrite` for custom SSL configurations
   - Reserve `ai-proxy` for standard cloud provider integrations
   - Test plugin compatibility before deployment

3. **Network Configuration:**
   - Ensure all containers are on appropriate Docker networks
   - Use container names for internal communication
   - Implement proper service discovery

4. **Monitoring:**
   - Monitor APISIX logs for SSL-related errors
   - Implement health checks for Custom OpenAPI endpoints
   - Set up alerting for certificate expiration

## Known Limitations

1. **Certificate Renewal:** Manual process required when Custom OpenAPI certificates rotate
2. **Container Restarts:** APISIX restart required after certificate updates
3. **Plugin Compatibility:** Not all APISIX plugins support custom SSL configurations
4. **Performance:** Additional SSL handshake overhead for container-to-container communication

## Common SSL/TLS Errors and Solutions

### Error: "failed to connect to LLM server: 19: self-signed certificate in certificate chain"

This is the most common error when integrating with enterprise AI gateways or development environments using self-signed certificates.

**Error in APISIX logs:**
```
[warn] [lua] openai-base.lua:198: phase_func(): failed to connect to LLM server: 19: self-signed certificate in certificate chain
[warn] [lua] plugin.lua:1207: common_phase(): ai-proxy exits with http status code 500
```

#### Quick Solution (Development/Testing)

**Method 1: Using the fix script**
```bash
# Run the GSAi fix script which disables SSL verification
./fix_gsai_ai_proxy.sh

# This will:
# - Set ssl_verify to false in the ai-proxy plugin
# - Update both chat and models routes
# - Test the connection
```

**Method 2: Manual configuration**
```bash
# 1. Disable SSL verification in ai-tokens.env
OPENAPI_1_SSL_VERIFY=false

# 2. Update routes
cd setup_macos_files
./openapi_setup.sh

# 3. Verify the change
source ../apisix/.env
curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" http://localhost:9180/apisix/admin/routes/9001 | \
  jq '.value.plugins."ai-proxy".ssl_verify'
# Should show: false
```

#### Proper Solution (Production)

```bash
# 1. Get the certificate chain from your server
openssl s_client -connect your-ai-gateway.com:443 -showcerts < /dev/null 2>/dev/null | \
  sed -n '/BEGIN CERTIFICATE/,/END CERTIFICATE/p' > cert-chain.pem

# 2. Extract individual certificates
csplit -f cert- -b %02d.pem cert-chain.pem '/-----BEGIN CERTIFICATE-----/' '{*}'

# 3. Find the root CA (check each cert)
for cert in cert-*.pem; do
  echo "=== $cert ==="
  openssl x509 -in $cert -noout -subject -issuer
done

# 4. Configure in ai-tokens.env
OPENAPI_1_SSL_VERIFY=true
OPENAPI_1_CA_CERT_PATH=/path/to/root-ca.pem

# 5. Import and update
cd setup_macos_files
./certificate_management.sh import /path/to/root-ca.pem
./openapi_setup.sh
```

## Enterprise HTTPS Configuration

### Overview

For enterprise deployments where AI gateways use HTTPS with valid SSL certificates, ViolentUTF provides comprehensive support through configurable HTTPS settings.

### Implementation Details

1. **URL Parsing**: Automatic scheme detection from provider URLs
2. **Dynamic Route Creation**: Routes created with proper HTTPS upstream configuration
3. **Certificate Management**: Support for custom CA certificates
4. **Validation**: Pre-setup validation to catch configuration issues early

### Configuration Process

1. **Set HTTPS Configuration in ai-tokens.env**:
   ```bash
   OPENAPI_1_USE_HTTPS=auto
   OPENAPI_1_SSL_VERIFY=true
   OPENAPI_1_CA_CERT_PATH=/path/to/ca.crt
   ```

2. **Validate Configuration**:
   ```bash
   ./setup_macos_files/validate_https_config.sh
   ```

3. **Import CA Certificate** (if needed):
   ```bash
   ./setup_macos_files/certificate_management.sh import /path/to/ca.crt
   ```

4. **Run Setup**:
   ```bash
   ./setup_macos_new.sh
   ```

### Testing

Use the enterprise test script:
```bash
cd tests
./test_enterprise_gsai.sh
```

## Troubleshooting Enterprise Environments

### Combined Issues: SSL + Authentication

In enterprise environments, you may encounter multiple issues simultaneously:

1. **SSL Certificate Error (500)**: Self-signed certificate rejection
2. **API Key Authentication (403)**: Missing key-auth plugin or incorrect consumer
3. **APISIX Admin Permission (403)**: User not in allowed list

**Complete Fix Process:**
```bash
# 1. Run comprehensive enterprise fix
./fix_enterprise_api_key.sh

# This checks:
# - API key consumers
# - GSAi route configuration  
# - APISIX admin permissions

# 2. If SSL error persists, run GSAi fix
./fix_gsai_ai_proxy.sh

# This will:
# - Disable SSL verification for self-signed certs
# - Update upstream configuration
# - Test the connection
```

### Diagnostic Commands

```bash
# Check current route configuration
curl -s -H "X-API-KEY: $(grep '^APISIX_ADMIN_KEY=' apisix/.env | cut -d'=' -f2)" \
  http://localhost:9180/apisix/admin/routes/9001 | jq '.value.plugins'

# Check APISIX logs for SSL errors
docker logs apisix-apisix-1 --tail 50 | grep -i "ssl\|certificate"

# Test direct connection to GSAi
source ai-tokens.env
curl -k -X POST "$OPENAPI_1_BASE_URL/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENAPI_1_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3211b", "messages": [{"role": "user", "content": "test"}]}'
```

## Future Improvements

1. **Automated Certificate Renewal:** Handle certificate rotation automatically
2. **Health Monitoring:** Enhanced SSL connectivity monitoring
3. **Plugin Enhancement:** Continue improving HTTPS support in plugins
4. **Multi-Environment Support:** Better support for dev/staging/prod configurations

## Related Files

- `setup_macos_files/openapi_setup.sh` - OpenAPI provider route creation
- `violentutf/utils/token_manager.py` - Endpoint discovery and provider detection
- `violentutf/pages/IronUTF.py` - Route detection for security testing
- `violentutf/pages/Simple_Chat.py` - UI integration for Custom OpenAPI providers
- `violentutf/generators/generator_config.py` - Provider configuration options