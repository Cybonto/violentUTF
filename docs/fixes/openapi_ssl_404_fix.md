# OpenAPI Zscaler/Corporate SSL Fix

## Problem Description

OpenAPI routes through APISIX were returning 404 errors even when:
- Consumer "violentutf" existed with correct API key
- Routes were configured with proper authentication headers
- Key-auth was passing (401 without key, 404 with key)
- Direct API calls worked with Bearer token

## Root Cause

Government and corporate APIs often use SSL/TLS certificates that:
1. Are issued by internal Certificate Authorities (CAs)
2. Use Zscaler or other corporate proxy certificates
3. Are not in the default certificate trust store

APISIX was failing to establish SSL connections to the upstream API due to certificate trust issues, resulting in 404 responses.

## Solution

ViolentUTF includes a built-in mechanism to handle Zscaler and corporate SSL certificates properly.

### For New Deployments

The setup script automatically detects SSL certificate issues and prompts for certificate installation:

```bash
# Run setup - it will detect SSL issues
./setup_macos.sh

# If prompted, export certificates
./get-zscaler-certs.sh

# Re-run setup
./setup_macos.sh
```

### For Existing Environments

Use the Zscaler-aware fix script:

```bash
cd apisix
./fix_openapi_zscaler.sh
```

This script:
- Checks for Zscaler/CA certificates in APISIX container
- Configures proper host header forwarding
- Tests connectivity with system certificates
- Provides specific guidance for certificate installation

## How It Works

### Certificate Installation

1. **Export Certificates** (macOS):
   ```bash
   ./get-zscaler-certs.sh
   ```
   This exports Zscaler certificates from the macOS Keychain to:
   - `zscaler.crt`
   - `CA.crt`

2. **Dockerfile Integration**:
   The FastAPI Dockerfile automatically copies and installs certificates:
   ```dockerfile
   # Copy certificates if they exist
   COPY zscaler.cr[t] CA.cr[t] /usr/local/share/ca-certificates/
   RUN update-ca-certificates || true
   
   # Set environment to use system certificates
   ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
   ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
   ```

3. **APISIX Configuration**:
   Routes are configured with proper host forwarding:
   ```json
   "upstream": {
       "pass_host": "pass",
       "keepalive_pool": {
           "size": 320,
           "idle_timeout": 60,
           "requests": 1000
       }
   }
   ```

## Troubleshooting

If routes still return 404 after applying the fix:

### 1. Check Network Connectivity

Test from inside APISIX container:

```bash
# DNS resolution
docker exec apisix-apisix-1 nslookup api.dev.gsai.mcaas.fcs.gsa.gov

# HTTPS connectivity
docker exec apisix-apisix-1 curl -k -I https://api.dev.gsai.mcaas.fcs.gsa.gov
```

### 2. Enable Debug Logging

```bash
# Enable info level logging
docker exec apisix-apisix-1 sed -i 's/error_log_level: "warn"/error_log_level: "info"/' /usr/local/apisix/conf/config.yaml
docker restart apisix-apisix-1

# Watch logs
docker logs -f apisix-apisix-1 2>&1 | grep -E 'gsai|openapi|proxy_pass'
```

### 3. Verify Token Validity

Test directly with your Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.dev.gsai.mcaas.fcs.gsa.gov/api/v1/models
```

### 4. Common Issues

- **Firewall blocking**: Check if APISIX container can reach external HTTPS
- **Token expiration**: Ensure Bearer tokens are valid and not expired
- **API changes**: Verify the upstream API endpoints haven't changed
- **Docker networking**: Ensure Docker can resolve external DNS

## Manual Certificate Installation

If automatic certificate export doesn't work:

### macOS
```bash
# Open Keychain Access and export Zscaler certificate
# Then copy to project
cp ~/Downloads/zscaler.crt violentutf_api/fastapi_app/
```

### Windows
```bash
# Export from Certificate Manager (certmgr.msc)
# Copy to project directory
cp C:/path/to/zscaler.crt violentutf_api/fastapi_app/
```

### Linux
```bash
# Copy from system certificate store
cp /usr/local/share/ca-certificates/zscaler.crt violentutf_api/fastapi_app/
```

## APISIX Container Certificate Setup

To manually install certificates in APISIX:

```bash
# Copy certificate to container
docker cp zscaler.crt apisix-apisix-1:/usr/local/share/ca-certificates/

# Update certificate store
docker exec apisix-apisix-1 update-ca-certificates

# Restart APISIX
docker restart apisix-apisix-1
```

## Security Considerations

This approach maintains security by:
1. Using proper CA certificates instead of disabling verification
2. Keeping SSL/TLS encryption intact
3. Only trusting explicitly added certificates
4. Following corporate security policies

## Related Files

- `/get-zscaler-certs.sh` - Export certificates from macOS Keychain
- `/fix-zscaler-build.sh` - Fix Docker build issues with Zscaler
- `/apisix/fix_openapi_zscaler.sh` - Fix OpenAPI routes for Zscaler
- `/setup_macos.sh` - Handles certificate detection and setup
- `/docs/guides/zscaler-setup.md` - Detailed Zscaler setup guide