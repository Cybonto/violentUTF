# HTTPS/SSL Quick Troubleshooting Guide

## Common Errors and Quick Fixes

### 1. "failed to connect to LLM server: 19: self-signed certificate in certificate chain"

**Symptom**: APISIX logs show this error when trying to connect to your AI gateway.

**Quick Fix** (for testing):
```bash
# Edit ai-tokens.env
OPENAPI_1_SSL_VERIFY=false

# Update routes
cd setup_macos_files && ./openapi_setup.sh
```

**Proper Fix** (for production):
```bash
# Get enterprise CA certificate from IT department or extract it
openssl s_client -connect your-gateway:443 -showcerts < /dev/null | \
  sed -n '/BEGIN/,/END/p' > cert-chain.pem

# Configure and import
echo "OPENAPI_1_SSL_VERIFY=true" >> ai-tokens.env
echo "OPENAPI_1_CA_CERT_PATH=/path/to/ca.crt" >> ai-tokens.env
cd setup_macos_files
./certificate_management.sh import /path/to/ca.crt
./openapi_setup.sh
```

### 2. "The plain HTTP request was sent to HTTPS port"

**Symptom**: Your AI gateway expects HTTPS but receives HTTP.

**Fix**:
```bash
# Edit ai-tokens.env
OPENAPI_1_BASE_URL=https://your-gateway.com  # Ensure https://
OPENAPI_1_USE_HTTPS=true

# Update routes
cd setup_macos_files && ./openapi_setup.sh
```

### 3. "SSL certificate problem: unable to get local issuer certificate"

**Symptom**: Certificate verification fails due to missing CA certificate.

**Fix**:
```bash
# Set CA certificate path in ai-tokens.env
OPENAPI_1_CA_CERT_PATH=/path/to/enterprise-ca.crt

# Import to APISIX
cd setup_macos_files
./certificate_management.sh import /path/to/enterprise-ca.crt
```

### 4. "x509: certificate signed by unknown authority"

**Symptom**: Similar to #3, but from different components.

**Fix**: Same as #3 - import your enterprise CA certificate.

## Quick Diagnostic Commands

### Check Current Route Configuration
```bash
# Load APISIX admin key
source apisix/.env

# Check GSAi route SSL settings
curl -s -H "X-API-KEY: $APISIX_ADMIN_KEY" \
  http://localhost:9180/apisix/admin/routes/9001 | \
  jq '.value.plugins."ai-proxy".model.options'
```

### Test SSL Connection Directly
```bash
# Test with system certificates
curl -v https://your-gateway.com/health

# Test with custom CA
curl -v --cacert /path/to/ca.crt https://your-gateway.com/health
```

### View APISIX Logs for SSL Errors
```bash
docker logs apisix-apisix-1 --tail 50 | grep -E "SSL|certificate|self-signed"
```

## Decision Tree

1. **Is your AI gateway using HTTPS?**
   - No → Ensure `OPENAPI_1_BASE_URL` uses `http://`
   - Yes → Continue to #2

2. **Is it using a self-signed or enterprise CA certificate?**
   - No (public CA) → Should work by default
   - Yes → Continue to #3

3. **Do you have the CA certificate file?**
   - No → Get it from IT or extract it (see commands above)
   - Yes → Continue to #4

4. **Is this for production or testing?**
   - Testing → Set `SSL_VERIFY=false` (quick fix)
   - Production → Import CA cert and set `SSL_VERIFY=true`

## Prevention

To avoid SSL issues:

1. **During Setup**: Always configure HTTPS settings in `ai-tokens.env` before running setup
2. **Validate First**: Run `./validate_https_config.sh` before setup
3. **Test Connection**: Use `./certificate_management.sh test` to verify SSL before full setup
4. **Document CA Source**: Keep notes on where your CA certificates came from for future updates

## Need More Help?

- **Detailed Guide**: [OpenAPI Integration Guide](../guides/openapi-integration.md#enterprise-https-support)
- **SSL Troubleshooting**: [Custom OpenAPI SSL Integration](Custom_OpenAPI_SSL_Integration.md)
- **Certificate Management**: Run `./certificate_management.sh` without arguments for help