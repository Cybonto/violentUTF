# Keycloak HTTPS Required (403) Error Fix

## Problem
When accessing Streamlit pages, you encounter:
```
403 Client Error: Forbidden for url: http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration
{"error": "invalid_request", "error_description": "HTTPS required"}
```

## Root Cause
Keycloak's `sslRequired` is set to "external" (secure default), which requires HTTPS for all external requests. However, local development uses HTTP.

## Solution: Configure Keycloak Proxy Mode

Instead of disabling SSL requirements (insecure), configure Keycloak to work behind a proxy. This maintains security while allowing local HTTP access.

### Step 1: Update Docker Configuration

Add these environment variables to `keycloak/docker-compose.yml`:

```yaml
environment:
  # ... existing config ...

  # --- Proxy Configuration ---
  KC_PROXY: edge              # Trust edge proxy headers
  KC_HOSTNAME_STRICT: false   # Allow flexible hostname validation
  KC_HOSTNAME_STRICT_HTTPS: false  # Allow HTTP when behind proxy
```

### Step 2: Restart Keycloak

```bash
cd keycloak
docker-compose down
docker-compose up -d
```

### Step 3: Verify Configuration

```bash
# Test OpenID endpoint (should return 200)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration

# Verify sslRequired is still "external" (secure)
docker exec keycloak-keycloak-1 /opt/keycloak/bin/kcadm.sh get realms/ViolentUTF -F sslRequired
```

## How It Works

The `KC_PROXY=edge` configuration tells Keycloak to:
1. Trust X-Forwarded-* headers from reverse proxies
2. Allow HTTP connections when behind a trusted proxy
3. Maintain security by still requiring HTTPS for direct external access

This is the recommended approach for:
- Local development environments
- Production deployments behind load balancers/reverse proxies
- Microservices architectures with API gateways (like APISIX)

## Alternative Solutions

1. **Use HTTPS Locally**: Set up self-signed certificates
2. **Route Through APISIX**: Configure all traffic through the API gateway
3. **Development Only**: Set `sslRequired: none` (NOT recommended for production)

## Security Note

This configuration maintains security by:
- Keeping `sslRequired: external` in the realm configuration
- Only accepting HTTP when proper proxy headers indicate SSL termination
- Working correctly with APISIX gateway and other reverse proxies
