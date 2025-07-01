# Keycloak 403 Forbidden Fix

## Problem

When accessing ViolentUTF Streamlit pages, you encounter:
```
403 Client Error: Forbidden for url: http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration
```

This happens because Keycloak's default security settings require HTTPS for external requests, but local development uses HTTP.

## Solution Applied

Updated Keycloak's Docker configuration to work properly behind a proxy/in development mode.

### Changes Made

Added these environment variables to `keycloak/docker-compose.yml`:

```yaml
# --- Proxy Configuration ---
KC_PROXY: edge              # Trust edge proxy headers
KC_PROXY_HEADERS: xforwarded
KC_HOSTNAME_STRICT: false   # Allow flexible hostname validation
KC_HOSTNAME_STRICT_HTTPS: false  # Allow HTTP when behind proxy
```

### How to Apply

1. The fix has been applied to `keycloak/docker-compose.yml`
2. Keycloak has been restarted
3. The endpoint is now accessible via HTTP

### Verification

Test that Keycloak is accepting HTTP requests:

```bash
# Should return 200
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration

# Should return the configuration
curl -s http://localhost:8080/realms/ViolentUTF/.well-known/openid-configuration | jq .
```

## Why This Works

The `KC_PROXY=edge` configuration tells Keycloak to:
- Trust proxy headers (X-Forwarded-*)
- Allow HTTP connections when behind a trusted proxy
- Maintain security for production deployments

This is the recommended approach for:
- Local development environments
- Production deployments behind load balancers
- Microservices with API gateways like APISIX

## Security Note

This configuration is secure because:
- It doesn't disable SSL requirements entirely
- It only accepts HTTP when proper proxy headers are present
- Production deployments can still enforce HTTPS at the edge

## Related Issues

If you still see authentication errors after this fix:
1. Check that all services are running: `./check_services.sh`
2. Verify APISIX routes: `cd apisix && ./verify_routes.sh`
3. Ensure tokens are fresh (they expire after 30 minutes)