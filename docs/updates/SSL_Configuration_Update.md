# SSL Configuration Update for OpenAPI Providers

## Summary
Updated the ViolentUTF setup to properly handle SSL certificate verification for OpenAPI providers, particularly for enterprise environments with self-signed certificates.

## Changes Made

### 1. GSAi Route Configuration Fix
**Critical**: GSAi routes must NOT use the `key-auth` plugin as it interferes with the Authorization header:
- GSAi routes use only `ai-proxy` and `cors` plugins
- Other OpenAPI providers can use `key-auth` + `proxy-rewrite` + `cors`
- This prevents the "Invalid key=value pair" error from GSAi

### 2. Environment Configuration Template
Updated `setup_macos_files/env_management.sh` to include SSL configuration options for all OpenAPI providers:

```bash
# SSL/TLS Configuration (for HTTPS endpoints)
OPENAPI_1_USE_HTTPS=auto        # auto (detect from URL), true, or false
OPENAPI_1_SSL_VERIFY=true       # true or false (set to false for self-signed certs)
OPENAPI_1_CA_CERT_PATH=""       # Path to custom CA certificate (optional)
```

### 2. Fix Scripts
Updated `fix_gsai_ai_proxy.sh` to:
- Set `ssl_verify: false` for self-signed certificates
- Properly extract host/port from BASE_URL
- Show warning when using HTTPS with self-signed certificates
- Use the extracted host/port in upstream configuration

### 3. Documentation
Updated `docs/troubleshooting/Custom_OpenAPI_SSL_Integration.md` with:
- Specific error messages for self-signed certificate issues
- Quick fix using the updated script
- Enterprise environment troubleshooting section
- Combined issues (SSL + Authentication) guidance

## Configuration Options

### For Development/Testing (Self-Signed Certificates)
```bash
# In ai-tokens.env
OPENAPI_1_SSL_VERIFY=false
```

### For Production (Enterprise CA)
```bash
# In ai-tokens.env
OPENAPI_1_SSL_VERIFY=true
OPENAPI_1_CA_CERT_PATH=/path/to/enterprise-ca.crt
```

## How It Works

1. The `get_https_config()` function in `utils.sh` reads SSL configuration from environment
2. Default SSL verification is `true` for security
3. When `ssl_verify=false`, the ai-proxy plugin skips certificate verification
4. The setup properly configures both chat and models routes with SSL settings

## Enterprise Environment Fix Process

When encountering SSL certificate errors in enterprise environments:

1. Run the comprehensive fix:
   ```bash
   ./fix_enterprise_api_key.sh
   ```

2. If SSL errors persist, run:
   ```bash
   ./fix_gsai_ai_proxy.sh
   ```

This will disable SSL verification and update routes appropriately.

## Future Improvements

1. **Linux Setup**: Add OpenAPI support to Linux setup scripts
2. **Certificate Management**: Automated CA certificate import for enterprises
3. **Validation**: Pre-setup SSL connectivity testing
4. **Windows Support**: Add SSL configuration to Windows setup

## Related Files

- `setup_macos_files/env_management.sh` - Environment template with SSL options
- `setup_macos_files/openapi_setup.sh` - Route creation with SSL support
- `setup_macos_files/utils.sh` - SSL configuration detection
- `fix_gsai_ai_proxy.sh` - Fix script for SSL issues
- `docs/troubleshooting/Custom_OpenAPI_SSL_Integration.md` - Comprehensive SSL troubleshooting