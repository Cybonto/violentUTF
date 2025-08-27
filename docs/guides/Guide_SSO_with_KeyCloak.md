# Using Keycloak for Single Sign-On (SSO) Across Multiple Applications

Setting up Keycloak for Single Sign-On (SSO) across multiple services like APISIX, APISIX Dashboard, Prometheus, Grafana, Strapi, and FastAPI requires several integration steps. Let me outline a comprehensive approach for implementing this solution.

## Overview

1. **Keycloak Configuration**: Set up a realm, clients, roles, and users
2. **APISIX Integration**: Use the OpenID Connect plugin
3. **APISIX Dashboard Integration**: Configure authentication
4. **Prometheus Security**: Implement authentication
5. **Grafana SSO**: Configure OAuth/OIDC
6. **Strapi Integration**: Set up OAuth provider
7. **FastAPI Integration**: Implement OAuth2 with OpenID Connect

## Step 1: Keycloak Base Configuration

### Create a Realm
1. Log in to Keycloak admin console
2. Create a new realm (e.g., "platform-sso")
3. Configure realm settings (token lifespans, password policies)

### Create Clients for Each Application
For each application (APISIX, Dashboard, Prometheus, Grafana, Strapi, FastAPI):

1. Go to "Clients" and click "Create"
2. Set up each client:

```
# Example for APISIX
Client ID: apisix
Name: APISIX Gateway
Client Protocol: openid-connect
Access Type: confidential
Valid Redirect URIs: http://localhost:9080/*, https://your-domain.com/*
Web Origins: +

# Example for APISIX Dashboard
Client ID: apisix-dashboard
Name: APISIX Dashboard
...and so on for each application
```

### Create Roles and Users
1. Create roles for access control:
   - `admin`: Full access to all applications
   - `developer`: Access to dev tools
   - `monitor`: Access to monitoring tools
   - Application-specific roles as needed

2. Create test users and assign roles

### Configure Mappers for Each Client
Add mappers to include roles and other attributes in tokens:

1. Go to the client configuration
2. Go to "Mappers" tab
3. Create mappers for roles, groups, etc.

## Step 2: APISIX Integration

APISIX has an [OpenID Connect plugin](https://apisix.apache.org/docs/apisix/plugins/openid-connect/) that makes integration straightforward:

1. Configure the plugin in your route or global rules:

```yaml
# In a route configuration
{
  "uri": "/secure/*",
  "plugins": {
    "openid-connect": {
      "client_id": "apisix",
      "client_secret": "your-client-secret",
      "discovery": "http://keycloak:8080/realms/platform-sso/.well-known/openid-configuration",
      "redirect_uri": "https://your-apisix-gateway/callback",
      "scope": "openid profile email",
      "bearer_only": false,
      "realm": "platform-sso",
      "logout_path": "/logout",
      "post_logout_redirect_uri": "https://your-apisix-gateway/"
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "your-backend:8000": 1
    }
  }
}
```

2. For global protection, add it to the global rules.

## Step 3: APISIX Dashboard SSO Integration

The APISIX Dashboard doesn't natively support OIDC, but you can:

1. Configure APISIX to proxy the Dashboard
2. Add the openid-connect plugin to this route
3. Update your dashboard configuration:

```yaml
# In your dashboard config.yaml
conf:
  listen:
    host: 0.0.0.0
    port: 9000
  # Other configs...

# Use the APISIX proxy with OIDC for authentication instead of default authentication
```

## Step 4: Prometheus Security with Keycloak

Prometheus doesn't support OAuth2/OIDC directly. The recommended approach is:

1. Use APISIX as a proxy in front of Prometheus
2. Secure the APISIX route with the openid-connect plugin
3. Configure Prometheus to only accept connections from APISIX

```yaml
# APISIX route for Prometheus
{
  "uri": "/prometheus/*",
  "plugins": {
    "openid-connect": {
      "client_id": "prometheus",
      "client_secret": "your-prometheus-client-secret",
      "discovery": "http://keycloak:8080/realms/platform-sso/.well-known/openid-configuration",
      "scope": "openid profile",
      "bearer_only": false,
      "realm": "platform-sso"
    },
    "proxy-rewrite": {
      "regex_uri": ["/prometheus/(.*)", "/$1"]
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "prometheus:9090": 1
    }
  }
}
```

## Step 5: Grafana SSO with Keycloak

Grafana has built-in support for OAuth/OIDC:

1. Update Grafana configuration in `grafana.ini` or environment variables:

```ini
[auth.generic_oauth]
enabled = true
name = Keycloak
allow_sign_up = true
client_id = grafana
client_secret = your-grafana-client-secret
scopes = openid email profile
auth_url = http://keycloak:8080/realms/platform-sso/protocol/openid-connect/auth
token_url = http://keycloak:8080/realms/platform-sso/protocol/openid-connect/token
api_url = http://keycloak:8080/realms/platform-sso/protocol/openid-connect/userinfo
role_attribute_path = contains(roles[*], 'admin') && 'Admin' || contains(roles[*], 'monitor') && 'Editor' || 'Viewer'
```

2. Restart Grafana

## Step 6: Strapi Integration with Keycloak

For Strapi, you'll need to install and configure a provider:

1. Install the required packages:
```bash
npm install @strapi/plugin-users-permissions
```

2. Configure the OAuth provider in Strapi admin panel:
   - Go to Settings > Users & Permissions Plugin > Providers
   - Configure a new provider for Keycloak

3. Add configuration to `config/plugins.js`:

```javascript
module.exports = ({ env }) => ({
  'users-permissions': {
    config: {
      providers: {
        keycloak: {
          enabled: true,
          icon: 'key',
          key: 'strapi',
          secret: env('KEYCLOAK_CLIENT_SECRET'),
          callback: '/auth/keycloak/callback',
          scope: ['openid', 'email', 'profile'],
          authorizationURL: 'http://keycloak:8080/realms/platform-sso/protocol/openid-connect/auth',
          tokenURL: 'http://keycloak:8080/realms/platform-sso/protocol/openid-connect/token',
          userInfoURL: 'http://keycloak:8080/realms/platform-sso/protocol/openid-connect/userinfo',
          userURL: 'http://keycloak:8080/realms/platform-sso/protocol/openid-connect/userinfo',
        },
      },
    },
  },
});
```

## Step 7: FastAPI Integration with Keycloak

For FastAPI, you can use libraries like `fastapi-auth-middleware` or implement OAuth2 with OpenID Connect:

1. Install required packages:
```bash
pip install fastapi python-jose httpx
```

2. Implement OpenID Connect in your FastAPI app:

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt, JWTError
import httpx

app = FastAPI()

# OIDC configuration
KEYCLOAK_URL = "http://keycloak:8080/realms/platform-sso"
OIDC_DISCOVERY_URL = f"{KEYCLOAK_URL}/.well-known/openid-configuration"
CLIENT_ID = "fastapi"
CLIENT_SECRET = "your-fastapi-client-secret"

# Get OIDC configuration
async def get_oidc_config():
    async with httpx.AsyncClient() as client:
        response = await client.get(OIDC_DISCOVERY_URL)
        return response.json()

# OAuth2 scheme
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_URL}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_URL}/protocol/openid-connect/token",
    scopes={"openid": "OpenID Connect", "profile": "Profile", "email": "Email"}
)

# Verify JWT token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        # Get JWKS
        config = await get_oidc_config()
        jwks_uri = config["jwks_uri"]

        async with httpx.AsyncClient() as client:
            jwks_response = await client.get(jwks_uri)
            jwks = jwks_response.json()

        # Decode token
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=CLIENT_ID
        )

        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Protected route example
@app.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"message": "This is a protected route", "user": user}
```

## Step 8: Create a Unified Authentication Entry Point

For a seamless experience, use APISIX to create a unified entry point:

1. Configure APISIX routes for all services
2. Apply consistent authentication using the openid-connect plugin
3. Configure proper redirects

```yaml
# Example routes in APISIX
routes:
  - uri: /dashboard/*
    upstream: apisix-dashboard:9000
    plugins:
      openid-connect: { ... }
  - uri: /prometheus/*
    upstream: prometheus:9090
    plugins:
      openid-connect: { ... }
  - uri: /grafana/*
    upstream: grafana:3000
    plugins:
      openid-connect: { ... }
  - uri: /strapi/*
    upstream: strapi:1337
    plugins:
      openid-connect: { ... }
  - uri: /api/*
    upstream: fastapi:8000
    plugins:
      openid-connect: { ... }
```

## Practical Implementation Recommendations

1. **Start Small**: Begin with one application and gradually add others
2. **Use Docker Compose** for local development to ensure proper network connectivity
3. **Implement a Consistent UI**: Consider a dashboard that links to all applications
4. **Role-Based Menu**: Show only applications the user has access to

## Security Considerations

1. **Use TLS**: Ensure all communications are encrypted
2. **Token Validation**: Always validate tokens properly
3. **Role-Based Access Control**: Use Keycloak roles effectively
4. **Short-Lived Tokens**: Configure appropriate token lifetimes
5. **Regular Audits**: Review access logs and user permissions regularly

## Script Example: Setting Up the Whole Stack

Here's a script snippet you could add to your setup_macos.sh to configure Keycloak for all these services:

```bash
# Create clients for all services
echo "Creating clients for all services in Keycloak..."

# Function to create a client in Keycloak
create_client() {
    local client_id="$1"
    local client_name="$2"
    local redirect_uris="$3"

    # Check if client already exists
    make_api_call "GET" "/realms/${TARGET_REALM_NAME}/clients?clientId=${client_id}"
    if [ "$API_CALL_STATUS" -eq 200 ] && [ "$(echo "$API_CALL_RESPONSE" | jq 'length')" -gt 0 ]; then
        echo "Client '$client_id' already exists. Skipping creation."
        return 0
    fi

    # Create client configuration
    local client_data='{
        "clientId": "'$client_id'",
        "name": "'$client_name'",
        "enabled": true,
        "protocol": "openid-connect",
        "publicClient": false,
        "redirectUris": '$redirect_uris',
        "webOrigins": ["+"],
        "standardFlowEnabled": true,
        "implicitFlowEnabled": false,
        "directAccessGrantsEnabled": true,
        "serviceAccountsEnabled": true
    }'

    # Create the client
    make_api_call "POST" "/realms/${TARGET_REALM_NAME}/clients" "$client_data"
    if [ "$API_CALL_STATUS" -eq 201 ]; then
        echo "Client '$client_id' created successfully."

        # Get the client UUID
        make_api_call "GET" "/realms/${TARGET_REALM_NAME}/clients?clientId=${client_id}"
        local client_uuid=$(echo "$API_CALL_RESPONSE" | jq -r '.[0].id')

        # Generate client secret
        make_api_call "POST" "/realms/${TARGET_REALM_NAME}/clients/${client_uuid}/client-secret"
        local client_secret=$(echo "$API_CALL_RESPONSE" | jq -r '.value')

        # Store secret for reporting
        SENSITIVE_VALUES+=("$client_name Client Secret: $client_secret")

        # Return the client secret
        echo "$client_secret"
    else
        echo "Failed to create client '$client_id'. Status: $API_CALL_STATUS"
        return 1
    fi
}

# Create clients for each service
APISIX_CLIENT_SECRET=$(create_client "apisix" "APISIX Gateway" '["http://localhost:9080/*"]')
DASHBOARD_CLIENT_SECRET=$(create_client "apisix-dashboard" "APISIX Dashboard" '["http://localhost:9001/*"]')
PROMETHEUS_CLIENT_SECRET=$(create_client "prometheus" "Prometheus" '["http://localhost:9090/*"]')
GRAFANA_CLIENT_SECRET=$(create_client "grafana" "Grafana" '["http://localhost:3000/*"]')
STRAPI_CLIENT_SECRET=$(create_client "strapi" "Strapi CMS" '["http://localhost:1337/*"]')
FASTAPI_CLIENT_SECRET=$(create_client "fastapi" "FastAPI Application" '["http://localhost:8000/*"]')

# Create roles
echo "Creating roles in Keycloak..."
create_realm_role() {
    local role_name="$1"
    local role_description="$2"

    # Check if role exists
    make_api_call "GET" "/realms/${TARGET_REALM_NAME}/roles/${role_name}"
    if [ "$API_CALL_STATUS" -eq 200 ]; then
        echo "Role '$role_name' already exists. Skipping creation."
        return 0
    elif [ "$API_CALL_STATUS" -ne 404 ]; then
        echo "Error checking for role '$role_name'. Status: $API_CALL_STATUS"
        return 1
    fi

    # Create role
    local role_data='{
        "name": "'$role_name'",
        "description": "'$role_description'"
    }'

    make_api_call "POST" "/realms/${TARGET_REALM_NAME}/roles" "$role_data"
    if [ "$API_CALL_STATUS" -eq 201 ]; then
        echo "Role '$role_name' created successfully."
        return 0
    else
        echo "Failed to create role '$role_name'. Status: $API_CALL_STATUS"
        return 1
    fi
}

# Create basic roles
create_realm_role "admin" "Administrator with full access"
create_realm_role "developer" "Developer with access to development tools"
create_realm_role "monitor" "User with access to monitoring tools"

# Assign roles to test user
if [ -n "$USER_EXISTS_ID" ]; then
    echo "Assigning roles to user '$KEYCLOAK_APP_USERNAME'..."

    # Get role representation
    make_api_call "GET" "/realms/${TARGET_REALM_NAME}/roles/admin"
    local admin_role_representation="$API_CALL_RESPONSE"

    # Assign role to user
    make_api_call "POST" "/realms/${TARGET_REALM_NAME}/users/${USER_EXISTS_ID}/role-mappings/realm" "[$admin_role_representation]"
    if [ "$API_CALL_STATUS" -eq 204 ]; then
        echo "Role 'admin' assigned to user '$KEYCLOAK_APP_USERNAME'."
    else
        echo "Failed to assign role to user. Status: $API_CALL_STATUS"
    fi
fi

# Configure APISIX routes for SSO
echo "Configuring APISIX routes for SSO..."

# Create APISIX routes configuration
configure_apisix_route() {
    local route_id="$1"
    local uri_pattern="$2"
    local upstream_target="$3"
    local client_id="$4"
    local client_secret="$5"

    local route_config='{
        "uri": "'$uri_pattern'",
        "plugins": {
            "openid-connect": {
                "client_id": "'$client_id'",
                "client_secret": "'$client_secret'",
                "discovery": "http://keycloak:8080/realms/'${TARGET_REALM_NAME}'/.well-known/openid-configuration",
                "scope": "openid profile email",
                "bearer_only": false,
                "realm": "'${TARGET_REALM_NAME}'",
                "redirect_uri": "http://localhost:9080'$uri_pattern'",
                "logout_path": "/logout"
            }
        },
        "upstream": {
            "type": "roundrobin",
            "nodes": {
                "'$upstream_target'": 1
            }
        }
    }'

    # Create the route in APISIX
    curl -i -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/${route_id}" \
      -H "X-API-KEY: ${APISIX_ADMIN_KEY}" \
      -H "Content-Type: application/json" \
      -d "${route_config}"

    if [ $? -eq 0 ]; then
        echo "Successfully configured APISIX route for $route_id"
    else
        echo "Warning: Failed to configure APISIX route for $route_id"
    fi
}

# Configure routes for each service
configure_apisix_route "dashboard-sso" "/dashboard/*" "apisix-dashboard:9000" "apisix-dashboard" "$DASHBOARD_CLIENT_SECRET"
configure_apisix_route "prometheus-sso" "/prometheus/*" "prometheus:9090" "prometheus" "$PROMETHEUS_CLIENT_SECRET"
configure_apisix_route "grafana-sso" "/grafana/*" "grafana:3000" "grafana" "$GRAFANA_CLIENT_SECRET"
configure_apisix_route "strapi-sso" "/strapi/*" "strapi:1337" "strapi" "$STRAPI_CLIENT_SECRET"
configure_apisix_route "fastapi-sso" "/api/*" "fastapi:8000" "fastapi" "$FASTAPI_CLIENT_SECRET"
```
