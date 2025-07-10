# Custom OpenAPI SSL Integration Issues and Solutions

## Overview

This document covers challenges and solutions encountered when integrating Custom OpenAPI providers (like local API services) with APISIX AI Gateway, particularly focusing on SSL certificate handling and plugin compatibility.

## ✅ RESOLVED: HTTP Configuration Solution

**Final Resolution (July 2025):** The SSL integration issues were resolved by configuring GSAi to use HTTP instead of HTTPS for container-to-container communication:

- **GSAi Configuration**: Disabled HTTPS, runs on HTTP port 8081 externally, 8080 internally
- **APISIX Routes**: Updated to use `scheme: "http"` and `ai-gov-api-app-1:8080` as upstream
- **Setup Scripts**: Modified to detect GSAi and automatically configure HTTP routing
- **SSL Certificates**: No longer required for GSAi integration

This approach eliminates SSL certificate complexity while maintaining security through the APISIX gateway authentication layer.

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

**Root Cause:**
Custom OpenAPI providers using Caddy or similar reverse proxies generate self-signed certificates that are not trusted by APISIX's default certificate store.

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

## Future Improvements

1. **Automated Certificate Management:** Implement automatic certificate extraction and trust store updates
2. **Health Monitoring:** Add specific health checks for Custom OpenAPI SSL connectivity
3. **Plugin Enhancement:** Contribute improvements to `ai-proxy` plugin for custom SSL scenarios
4. **Documentation:** Expand setup scripts to handle certificate integration automatically

## Related Files

- `setup_macos_files/openapi_setup.sh` - OpenAPI provider route creation
- `violentutf/utils/token_manager.py` - Endpoint discovery and provider detection
- `violentutf/pages/IronUTF.py` - Route detection for security testing
- `violentutf/pages/Simple_Chat.py` - UI integration for Custom OpenAPI providers
- `violentutf/generators/generator_config.py` - Provider configuration options