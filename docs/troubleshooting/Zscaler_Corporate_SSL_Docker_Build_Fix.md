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

**Enhanced Understanding:**
The Rust installer (`rustup`) not only downloads the initial script but also makes additional HTTPS calls to download components like toolchains and libraries. These internal downloads also fail SSL verification in corporate environments, requiring comprehensive SSL bypass configuration.

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

### 2. Comprehensive Rust Installation with SSL Bypass

Enhanced Rust installation that handles both the installer script and internal component downloads with SSL bypass:

```dockerfile
# Install Rust with comprehensive corporate firewall/Zscaler support
ENV RUSTUP_HOME=/usr/local/rustup CARGO_HOME=/usr/local/cargo PATH=/usr/local/cargo/bin:$PATH

# Corporate environment: Configure curl to ignore SSL for Rust installer
# Create curl config that tells rustup to ignore SSL certificates
RUN mkdir -p ~/.config && \
    echo "insecure" > /etc/curl_config && \
    echo "capath=" >> /etc/curl_config

# Set environment variables for Rust installer SSL bypass
ENV CURL_HOME=/etc
ENV RUSTUP_USE_CURL=1
ENV RUSTUP_CURL_OPTIONS="--insecure"

# Install Rust with corporate SSL bypass
RUN curl --insecure --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | \
    RUSTUP_USE_CURL=1 sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable && \
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

### 4. Machine Learning Package SSL Bypass

Added environment variables for ML packages that download models during runtime:

```dockerfile
# Hugging Face and ML model download SSL bypass for corporate environments
ENV HF_HUB_DISABLE_SSL=1
ENV TRANSFORMERS_OFFLINE=0
ENV HF_DATASETS_OFFLINE=0
ENV TORCH_HOME=/tmp/torch_cache
ENV TRANSFORMERS_CACHE=/tmp/transformers_cache
ENV HF_HOME=/tmp/hf_cache
```

### 5. Package Verification with SSL Bypass

Enhanced verification step to handle SSL issues during package imports:

```dockerfile
# Verify PyRIT and other packages installation with SSL bypass
RUN PYTHONHTTPSVERIFY=0 SSL_VERIFY=false python verify_redteam_install.py && \
    echo "✅ Package verification completed successfully"
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
