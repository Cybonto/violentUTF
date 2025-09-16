# Keycloak HTTPS Required Error Fix

## Problem
When accessing Keycloak or during setup, you encounter:
```
403 Client Error: Forbidden for url: http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration
{"error": "invalid_request", "error_description": "HTTPS required"}
```

OR during setup:
```
Error: Could not obtain Keycloak admin access token.
Response: {"error":"invalid_request","error_description":"HTTPS required"}
```

## Root Cause
Keycloak's `sslRequired` is set to "external" (secure default) for both the **ViolentUTF realm** and the **master realm**, which requires HTTPS for all external requests. However, local development uses HTTP.

The master realm SSL requirement affects admin token acquisition during setup.

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
# Test master realm accessibility (should return 200)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/realms/master

# Test admin token acquisition
curl -s -X POST "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin&grant_type=password&client_id=admin-cli"

# Test ViolentUTF realm (after realm import)
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration
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

## If Proxy Configuration Doesn't Work

### Automatic Master Realm SSL Fix

The setup script now includes an automatic fix for master realm SSL requirements. If the HTTPS error persists, the script will:

1. **Automatically disable SSL** for the master realm in development
2. **Retry token acquisition** after the fix
3. **Continue with setup** if successful

### Manual Restart Solution

If the automatic fix doesn't work, **restart the setup script**:

```bash
# Stop current setup
./setup_macos.sh --cleanup

# Restart setup (proxy config will be active from start)
./setup_macos.sh
```

### Manual Realm SSL Fix

If needed, you can manually fix the SSL requirement for both realms:

```bash
# Connect to Keycloak container
docker exec -it keycloak-keycloak-1 bash

# Configure kcadm credentials
/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin --client admin-cli

# Disable SSL requirement for master realm (development only)
/opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=NONE

# Disable SSL requirement for ViolentUTF realm (development only)
/opt/keycloak/bin/kcadm.sh update realms/ViolentUTF -s sslRequired=NONE

# Verify the changes
/opt/keycloak/bin/kcadm.sh get realms/master -F sslRequired
/opt/keycloak/bin/kcadm.sh get realms/ViolentUTF -F sslRequired
```

The setup script now includes comprehensive error handling and automatic fixes for HTTPS requirement issues.

## Security Note

This configuration maintains security by:
- Keeping `sslRequired: external` in the realm configuration
- Only accepting HTTP when proper proxy headers indicate SSL termination
- Working correctly with APISIX gateway and other reverse proxies
