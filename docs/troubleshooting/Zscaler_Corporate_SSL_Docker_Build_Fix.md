# Zscaler/Corporate SSL Certificate Docker Build Fix

## Overview

This document provides solutions for Docker build failures in corporate environments that use Zscaler or similar SSL-intercepting proxies/firewalls.

## Problem Description

**Symptoms:**
- Docker build fails with SSL certificate errors like:
  ```
  curl: (60) SSL certificate problem: unable to get local issuer certificate
  ```
- Rust installation fails during Docker build
- pip package installation fails with SSL verification errors
- Build works locally but fails in corporate network environment

**Root Cause:**
Corporate firewalls like Zscaler intercept HTTPS traffic and present their own certificates. Docker containers don't trust these corporate certificates by default, causing SSL verification failures during build processes.

## Solution Implementation

The following solution has been implemented in `violentutf_api/fastapi_app/Dockerfile` to handle corporate SSL certificate issues:

### 1. Environment Variables for SSL Bypass

Added corporate SSL bypass environment variables in both build and runtime stages:

```dockerfile
# Corporate environment SSL certificate handling for Zscaler/corporate proxies
# These help bypass SSL verification issues during build
ENV PYTHONHTTPSVERIFY=0
ENV CURL_CA_BUNDLE=""
ENV REQUESTS_CA_BUNDLE=""
ENV SSL_VERIFY=false
```

### 2. Rust Installation with SSL Fallback

Enhanced Rust installation to try secure connection first, then fallback to insecure if needed:

```dockerfile
# Install Rust with corporate firewall/Zscaler support
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH

# Corporate environment SSL handling for Rust installation
# Try with certificates first, fallback to insecure if needed
RUN set +e && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable; \
    if [ $? -ne 0 ]; then \
        echo "Standard SSL failed, trying with insecure connection (corporate environment)..."; \
        curl --proto '=https' --tlsv1.2 -sSf -k https://sh.rustup.rs | \
        sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable; \
    fi && \
    chmod -R a+w $RUSTUP_HOME $CARGO_HOME
```

### 3. pip Installation with Trusted Hosts

Added trusted host flags for all pip operations:

```dockerfile
# Copy and install requirements with corporate SSL bypass
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org \
        --no-cache-dir -r requirements.txt && \
    pip wheel --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org \
        --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt
```

## Alternative Solutions

### Option 1: Certificate Injection (More Secure)

If you have access to your corporate root certificates, you can inject them into the Docker build:

```dockerfile
# Copy corporate certificates (if available)
COPY corporate-ca.crt /usr/local/share/ca-certificates/
RUN update-ca-certificates
```

### Option 2: Build Args for Dynamic SSL Control

Use build arguments to control SSL verification based on environment:

```dockerfile
ARG CORPORATE_ENV=false
ENV PYTHONHTTPSVERIFY=${CORPORATE_ENV:+0}
```

Then build with:
```bash
docker build --build-arg CORPORATE_ENV=true .
```

## Testing the Fix

After applying these changes, test the Docker build:

```bash
# Build the FastAPI container
cd violentutf_api/fastapi_app
docker build -t violentutf-api .

# If successful, the build should complete without SSL errors
```

## Security Considerations

**Important:** These fixes disable SSL certificate verification, which reduces security. Use these approaches only in corporate environments where:

1. Network traffic is already secured by corporate firewalls
2. You cannot obtain/install corporate root certificates
3. This is the only way to make builds work in the corporate environment

**For production deployments:** Consider working with your IT security team to properly install corporate root certificates instead of disabling SSL verification.

## Related Documentation

- [Custom OpenAPI SSL Integration](./Custom_OpenAPI_SSL_Integration.md) - For APISIX SSL certificate handling
- [Keycloak HTTPS Required Fix](./keycloak_https_required_fix.md) - For Keycloak SSL configuration

## Troubleshooting

If the build still fails after applying these fixes:

1. **Check corporate proxy settings:**
   ```bash
   echo $https_proxy
   echo $http_proxy
   ```

2. **Verify Docker daemon proxy configuration:**
   Check `/etc/systemd/system/docker.service.d/http-proxy.conf` (Linux)
   Or Docker Desktop network settings (Windows/Mac)

3. **Test connectivity outside Docker:**
   ```bash
   curl -I https://sh.rustup.rs
   curl -I https://pypi.org
   ```

4. **Contact IT support:** If none of the above work, your corporate firewall may have additional restrictions that require IT support to resolve.

## Implementation Status

✅ **Applied to:** `violentutf_api/fastapi_app/Dockerfile`
✅ **Tested with:** Zscaler corporate environment
✅ **Fallback strategy:** Secure connection attempted first, insecure as fallback
✅ **Scope:** Both build and runtime stages covered
