# Securing Your Docker Stack with Apache APISIX and Keycloak

This guide outlines the steps to secure services within your Dockerized application stack using Apache APISIX as an API gateway and an external Keycloak instance as the identity and access management provider.

## Table of Contents

1.  [Prerequisites](#prerequisites)
2.  [Keycloak Configuration (External Instance)](#keycloak-configuration-external-instance)
    * [A. Create/Verify Realm](#a-createverify-realm)
    * [B. Create OIDC Clients for Services/APISIX](#b-create-oidc-clients-for-servicesapisix)
    * [C. (Optional) User and Role Management](#c-optional-user-and-role-management)
3.  [APISIX General Configuration Strategy](#apisix-general-configuration-strategy)
    * [A. Enable `openid-connect` Plugin](#a-enable-openid-connect-plugin)
    * [B. Define Upstreams](#b-define-upstreams)
    * [C. Create and Secure Routes](#c-create-and-secure-routes)
4.  [Securing Specific Services (Examples)](#securing-specific-services-examples)
    * [A. Securing Strapi API](#a-securing-strapi-api)
    * [B. Securing APISIX Dashboard](#b-securing-apisix-dashboard)
    * [C. Securing Grafana UI](#c-securing-grafana-ui)
    * [D. Securing APISIX Admin API (Recommended)](#d-securing-apisix-admin-api-recommended)
5.  [Key `openid-connect` Plugin Parameters](#key-openid-connect-plugin-parameters)
6.  [General Security Best Practices](#general-security-best-practices)
7.  [Troubleshooting Tips](#troubleshooting-tips)

## 1. Prerequisites

* **Running APISIX Stack:** Your Docker Compose stack (with APISIX, ETCD, Strapi, Grafana, etc.) is up and running.
* **Running External Keycloak Stack:** Your separate Keycloak Docker stack (with its own Postgres) is operational and accessible from the APISIX stack.
* **Network Connectivity:** Ensure containers in the APISIX stack can resolve and reach the Keycloak instance's URL (e.g., `http://host.docker.internal:8080`, a shared Docker network, or a publicly resolvable FQDN).
* **Admin Access:**
    * APISIX Admin API (default: `http://localhost:9180` if exposed, or via an internal route).
    * Keycloak Admin Console (e.g., `http://localhost:8080` if Keycloak is on port 8080 of the host).
* **`.env` File:** Your main `docker-compose.yml`'s `.env` file is configured with:
    * `KEYCLOAK_EXTERNAL_URL`: The full base URL of your external Keycloak (e.g., `http://keycloak.example.com` or `http://host.docker.internal:8080`).
    * `KEYCLOAK_EXTERNAL_REALM_NAME`: The name of your Keycloak realm (e.g., `ViolentUTF`).
* **Tools:** `curl` and `jq` installed on the machine where you'll run APISIX Admin API commands.

## 2. Keycloak Configuration (External Instance)

These steps are performed in your *external* Keycloak Admin Console.

### A. Create/Verify Realm

Ensure you have a realm created for your applications. For this guide, we'll assume the realm name is defined by `KEYCLOAK_EXTERNAL_REALM_NAME` (e.g., `ViolentUTF`).

### B. Create OIDC Clients for Services/APISIX

For each service/UI you want to protect via APISIX, and potentially for APISIX itself (if securing its Admin API or Dashboard via a specific client), you need to create an OIDC client in Keycloak.

**General Client Creation Steps:**

1.  Navigate to your Realm -> `Clients` -> `Create client`.
2.  **Client ID:** A unique identifier (e.g., `apisix-gateway-client`, `strapi-client`, `dashboard-client`).
3.  **Name:** A descriptive name.
4.  **Client authentication:** `On`.
5.  **Authentication flow:**
    * Enable `Standard flow` (for user-facing applications like dashboards).
    * Enable `Direct access grants` (if any service needs to exchange user credentials for a token, though less common when APISIX handles OIDC).
    * Enable `Service accounts` if a service (or APISIX itself for certain operations) needs to authenticate as a client using client credentials.
6.  Click `Next`.
7.  **Capability config:**
    * **Client authentication:** `On`.
    * **Authorization:** (Usually leave off unless using fine-grained UMA policies directly in Keycloak).
    * **Authentication flow:** Check `Standard flow`. `Direct access grants` can be enabled if needed.
8.  Click `Save`.
9.  **Client Details Configuration (after saving):**
    * **Access Type (Old UI) / Client authentication (New UI):**
        * For APISIX `openid-connect` plugin when it needs to authenticate itself (e.g., to use the token introspection endpoint or refresh tokens): `Confidential` (or `Client ID and secret` in new UI). Note the generated **secret** from the `Credentials` tab.
        * For protecting UIs where APISIX handles the login flow: `Public` might be suitable if PKCE is used, or `Confidential` if APISIX is to use a secret. Typically, APISIX acts as a confidential client.
        * For APIs protected by APISIX where APISIX only validates bearer tokens: The Keycloak client might be `bearer-only` if it represents the resource server, but the `openid-connect` plugin in APISIX will act as a (typically confidential) client to Keycloak.
    * **Valid Redirect URIs:**
        * Crucial for `Standard flow`. Add the URI(s) where Keycloak will redirect after successful authentication. This will be an APISIX endpoint. Example: `http://<your-apisix-public-host>:<port>/dashboard/callback/*`, `http://<your-apisix-public-host>:<port>/strapi/callback/*`.
        * Use `+` for wildcard if subpaths are dynamic, but be as specific as possible.
    * **Web Origins:** Add URLs from which requests to Keycloak are allowed (e.g., `http://<your-apisix-public-host>:<port>`). Use `+` to allow all origins from that base URL for development, or be specific in production.
    * **(Optional) Service Account Roles:** If using client credentials grant for a service, assign necessary roles to its service account under the `Service Account Roles` tab.
    * **Credentials Tab:** Note the `Client secret` if you chose `Confidential` access type.

**Specific Clients to Consider:**

* **A general APISIX client:** (e.g., `apisix-oidc-client`) This client would be configured in the `openid-connect` plugin on various routes. It would be `Confidential`.
* **Clients per application (optional but good practice):** (e.g., `strapi-app-client`, `grafana-app-client`). This allows for more granular control.

### C. (Optional) User and Role Management

* Create users who will access your services.
* Define realm roles (e.g., `admin`, `editor`, `viewer`) or client-specific roles.
* Assign roles to users or groups. The `openid-connect` plugin in APISIX can be configured to pass role information in headers to upstream services.

## 3. APISIX General Configuration Strategy

These steps are performed by interacting with the APISIX Admin API (default `http://localhost:9180` or via a protected route).

### A. Enable `openid-connect` Plugin

Ensure the `openid-connect` plugin is listed in your `apisix_conf/config-apisix.yaml` under the `plugins` section. This makes it available for use in routes and services. (This is already done in the provided `apisix_config_yaml_v2`).

### B. Define Upstreams

For each backend service in your `docker-compose.yml`, define an upstream in APISIX. An upstream points to the internal Docker network address of the service.

**Example: Creating an upstream for Strapi:**
(Strapi runs on `http://strapi:1337` within the Docker network)

```bash
ADMIN_API_KEY="edd1c9f034335f136f87ad84b625c8f1" # Your APISIX Admin Key
APISIX_ADMIN_URL="http://localhost:9180" # Or your APISIX Admin API endpoint

curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/upstreams/strapi-upstream" \
-H "X-API-KEY: ${ADMIN_API_KEY}" \
-H "Content-Type: application/json" -d '{
    "name": "Strapi Service Upstream",
    "type": "roundrobin",
    "nodes": {
        "strapi:1337": 1
    },
    "desc": "Upstream for the Strapi CMS service"
}'
```
Repeat for other services like `apisix-dashboard:9000`, `grafana:3000`, etc.

### C. Create and Secure Routes

For each service, create a route that defines the public-facing path and applies the `openid-connect` plugin.

## 4. Securing Specific Services (Examples)

Replace placeholders like `<YOUR_APISIX_HOST_PORT>`, `${KEYCLOAK_EXTERNAL_URL}`, `${KEYCLOAK_EXTERNAL_REALM_NAME}`, `<YOUR_CLIENT_ID>`, and `<YOUR_CLIENT_SECRET>` with your actual values.

### A. Securing Strapi API

Assuming Strapi is an API and expects a bearer token.

1.  **Keycloak Client:** Create a client in Keycloak for Strapi (e.g., `strapi-api-client`, confidential, note its secret). `Valid Redirect URIs` might not be strictly needed if APISIX handles the entire OIDC flow and Strapi only validates tokens.
2.  **APISIX Route for Strapi:**

    ```bash
    curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/strapi-api-route" \
    -H "X-API-KEY: ${ADMIN_API_KEY}" \
    -H "Content-Type: application/json" -d '{
        "name": "Secure Strapi API Route",
        "uri": "/api/strapi/*",  # Public path for Strapi API
        "upstream_id": "strapi-upstream", # Matches the upstream created earlier
        "plugins": {
            "openid-connect": {
                "client_id": "<YOUR_STRAPI_CLIENT_ID_IN_KEYCLOAK>",
                "client_secret": "<YOUR_STRAPI_CLIENT_SECRET_IN_KEYCLOAK>",
                "discovery": "${KEYCLOAK_EXTERNAL_URL}/realms/${KEYCLOAK_EXTERNAL_REALM_NAME}/.well-known/openid-configuration",
                "bearer_only": true,
                "realm": "${KEYCLOAK_EXTERNAL_REALM_NAME}",
                "token_endpoint_auth_method": "client_secret_post",
                "set_userinfo_header": true, // Optional: pass userinfo to Strapi
                "userinfo_header_name": "X-Userinfo",
                "set_access_token_header": true, // Optional: pass access token
                "access_token_header_name": "X-Access-Token"
            },
            "proxy-rewrite": { // Ensure correct path rewriting to the Strapi service
                "regex_uri": ["^/api/strapi/(.*)", "/$1"]
            }
        },
        "desc": "Route to Strapi API secured by Keycloak"
    }'
    ```
    * Users will need to obtain a token from Keycloak (e.g., via a separate frontend app or password grant) and include it in the `Authorization: Bearer <token>` header when calling `/api/strapi/*`.
    * Strapi itself might need its "Users & Permissions" plugin configured with the "oidc" or "oauth2" provider to understand the user context from the token if it does its own fine-grained checks.

### B. Securing APISIX Dashboard

The APISIX Dashboard requires a login flow.

1.  **Keycloak Client:** Create a client (e.g., `apisix-dashboard-client`, confidential).
    * **Valid Redirect URIs:** `http://<YOUR_APISIX_HOST_PORT>/dashboard-callback/*` (or a more specific path).
    * **Web Origins:** `http://<YOUR_APISIX_HOST_PORT>`
2.  **APISIX Route for Dashboard:**
    (Dashboard runs on `http://apisix-dashboard:9000` internally)

    ```bash
    # Define upstream for apisix-dashboard first if not already done
    curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/upstreams/apisix-dashboard-upstream" \
    -H "X-API-KEY: ${ADMIN_API_KEY}" \
    -H "Content-Type: application/json" -d '{
        "name": "APISIX Dashboard Upstream",
        "type": "roundrobin",
        "nodes": { "apisix-dashboard:9000": 1 }
    }'

    # Secure the route to the dashboard
    curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/apisix-dashboard-route" \
    -H "X-API-KEY: ${ADMIN_API_KEY}" \
    -H "Content-Type: application/json" -d '{
        "name": "Secure APISIX Dashboard Route",
        "uri": "/dashboard/*", # Public path for the dashboard
        "upstream_id": "apisix-dashboard-upstream",
        "plugins": {
            "openid-connect": {
                "client_id": "<YOUR_DASHBOARD_CLIENT_ID_IN_KEYCLOAK>",
                "client_secret": "<YOUR_DASHBOARD_CLIENT_SECRET_IN_KEYCLOAK>",
                "discovery": "${KEYCLOAK_EXTERNAL_URL}/realms/${KEYCLOAK_EXTERNAL_REALM_NAME}/.well-known/openid-configuration",
                "bearer_only": false,
                "redirect_uri": "http://<YOUR_APISIX_HOST_PORT>/dashboard/callback", // Must match Keycloak client config
                "scope": "openid profile email roles", // Request roles scope
                "session": {
                    "secret": "$(openssl rand -hex 16)", // Generate a random secret
                    "cookie_name": "apisix_dashboard_session",
                    "cookie_samesite": "Lax"
                },
                "logout_path": "/dashboard/logout",
                "post_logout_redirect_uri": "http://<YOUR_APISIX_HOST_PORT>/dashboard/loggedout.html" // A static page or back to login
            },
            "proxy-rewrite": {
                "regex_uri": ["^/dashboard/(.*)", "/$1"]
            }
        },
        "desc": "Route to APISIX Dashboard secured by Keycloak"
    }'
    ```
    * Ensure the `redirect_uri` and `post_logout_redirect_uri` are registered in the Keycloak client.
    * The APISIX Dashboard's internal authentication (from `dashboard-conf.yaml`) might still be active. After Keycloak authentication, APISIX could potentially pass user identity, but the dashboard itself isn't designed for direct OIDC user provisioning. Users might still need to log into the dashboard with its local credentials after Keycloak auth, or you'd need a more advanced setup (custom plugin, or if dashboard supports OIDC directly). For now, this protects access to the dashboard page.

### C. Securing Grafana UI

Similar to the APISIX Dashboard, assuming you want APISIX to handle the OIDC flow.

1.  **Keycloak Client:** Create a client (e.g., `grafana-ui-client`, confidential).
    * **Valid Redirect URIs:** `http://<YOUR_APISIX_HOST_PORT>/grafana-callback/*`
    * **Web Origins:** `http://<YOUR_APISIX_HOST_PORT>`
2.  **APISIX Route for Grafana:**
    (Grafana runs on `http://grafana:3000` internally)

    ```bash
    # Define upstream for grafana first
    curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/upstreams/grafana-upstream" \
    -H "X-API-KEY: ${ADMIN_API_KEY}" \
    -H "Content-Type: application/json" -d '{
        "name": "Grafana UI Upstream",
        "type": "roundrobin",
        "nodes": { "grafana:3000": 1 }
    }'

    # Secure the route to Grafana
    curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/grafana-route" \
    -H "X-API-KEY: ${ADMIN_API_KEY}" \
    -H "Content-Type: application/json" -d '{
        "name": "Secure Grafana UI Route",
        "uri": "/grafana/*",
        "upstream_id": "grafana-upstream",
        "plugins": {
            "openid-connect": {
                "client_id": "<YOUR_GRAFANA_CLIENT_ID_IN_KEYCLOAK>",
                "client_secret": "<YOUR_GRAFANA_CLIENT_SECRET_IN_KEYCLOAK>",
                "discovery": "${KEYCLOAK_EXTERNAL_URL}/realms/${KEYCLOAK_EXTERNAL_REALM_NAME}/.well-known/openid-configuration",
                "bearer_only": false,
                "redirect_uri": "http://<YOUR_APISIX_HOST_PORT>/grafana/callback", // Example callback path
                "scope": "openid profile email roles",
                "session": {
                    "secret": "$(openssl rand -hex 16)",
                    "cookie_name": "grafana_session"
                },
                "logout_path": "/grafana/logout"
                // Optional: Set headers to pass user info to Grafana if it can use them for auth proxy mode
                // "set_userinfo_header": true,
                // "userinfo_header_name": "X-WEBAUTH-USER" // Common header for Grafana auth proxy
            },
            "proxy-rewrite": {
                "regex_uri": ["^/grafana/(.*)", "/$1"],
                "headers": { // Grafana needs the Host header to be correct for subpaths
                    "Host": "grafana:3000"
                }
            }
        },
        "desc": "Route to Grafana UI secured by Keycloak"
    }'
    ```
    * Grafana can also be configured to use Generic OAuth directly (see `GF_AUTH_GENERIC_OAUTH_*` env vars in `docker-compose.yml`). If using that, APISIX might just do SSL termination or basic routing. The example above shows APISIX handling the OIDC flow.

### D. Securing APISIX Admin API (Recommended)

Do not expose port `9180` directly to the internet.

1.  **Keycloak Client:** Create a client (e.g., `apisix-admin-client`, confidential).
2.  **APISIX Route for Admin API:**

    ```bash
    # Define upstream for APISIX Admin API (points to itself)
    # Note: APISIX Admin API listens on 127.0.0.1:9180 by default inside the container for security.
    # To proxy to it via another APISIX route, you might need to adjust admin_listen in config-apisix.yaml
    # to 0.0.0.0:9180 or use a more advanced internal routing technique.
    # For this example, let's assume admin API is accessible on apisix:9180 (requires config change).
    # If config.yaml has `admin_listen.ip: 0.0.0.0`, this upstream is fine.
    curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/upstreams/apisix-admin-api-upstream" \
    -H "X-API-KEY: ${ADMIN_API_KEY}" \
    -H "Content-Type: application/json" -d '{
        "name": "APISIX Admin API Internal Upstream",
        "type": "roundrobin",
        "nodes": { "apisix:9180": 1 }
    }'

    curl -X PUT "${APISIX_ADMIN_URL}/apisix/admin/routes/apisix-admin-route" \
    -H "X-API-KEY: ${ADMIN_API_KEY}" \
    -H "Content-Type: application/json" -d '{
        "name": "Secure APISIX Admin API Route",
        "uri": "/secure-admin/*", # Choose a public path
        "upstream_id": "apisix-admin-api-upstream",
        "plugins": {
            "openid-connect": {
                "client_id": "<YOUR_APISIX_ADMIN_CLIENT_ID>",
                "client_secret": "<YOUR_APISIX_ADMIN_CLIENT_SECRET>",
                "discovery": "${KEYCLOAK_EXTERNAL_URL}/realms/${KEYCLOAK_EXTERNAL_REALM_NAME}/.well-known/openid-configuration",
                "bearer_only": true, // Expect a token from an admin user/script
                "realm": "${KEYCLOAK_EXTERNAL_REALM_NAME}",
                "token_endpoint_auth_method": "client_secret_post"
            },
            "proxy-rewrite": {
                "regex_uri": ["^/secure-admin/(.*)", "/apisix/admin/$1"] // Rewrite to actual admin path
            }
        },
        "desc": "Route to APISIX Admin API secured by Keycloak"
    }'
    ```
    * Admin users/scripts would obtain a token from Keycloak and use it to call `/secure-admin/*`.
    * The original `admin_key` is still needed for this initial setup of the secure route.

## 5. Key `openid-connect` Plugin Parameters

* `discovery`: (String) URL of the OIDC provider's discovery document. (e.g., `http://keycloak-host/realms/myrealm/.well-known/openid-configuration`)
* `client_id`: (String) Client ID registered with the OIDC provider.
* `client_secret`: (String) Client Secret for confidential clients.
* `realm`: (String) Keycloak realm (often not needed if using `discovery`, but good for clarity).
* `bearer_only`: (Boolean) If `true`, APISIX expects a bearer token and validates it. If `false`, APISIX initiates the OIDC login flow (redirects to Keycloak). Default `false`.
* `redirect_uri`: (String) URI where the OIDC provider redirects after authentication (required if `bearer_only` is `false`). Must be registered in Keycloak.
* `scope`: (String) Space-separated list of scopes to request (e.g., `openid profile email roles`).
* `token_endpoint_auth_method`: (String) How APISIX authenticates to the token endpoint (e.g., `client_secret_post`, `client_secret_basic`).
* `introspection_endpoint`: (String) URL of the token introspection endpoint. Can be used instead of or alongside local JWT validation.
* `public_key`: (String) The public key (PEM format) of the OIDC provider for local JWT signature validation.
* `session.*`: Configuration for session management if `bearer_only` is `false`. Includes `secret`, `cookie_name`, etc.
* `set_access_token_header`, `set_id_token_header`, `set_userinfo_header`: (Boolean) Whether to pass token/user info to the upstream service in headers.
* `*_header_name`: Names for the headers mentioned above.

Refer to the [APISIX openid-connect plugin documentation](https://apisix.apache.org/docs/apisix/plugins/openid-connect/) for all parameters.

## 6. General Security Best Practices

* **HTTPS Everywhere:** Configure SSL termination on APISIX for all external traffic. Use SSL for communication between APISIX and backend services where possible.
* **Strong Secrets:** Use strong, unique secrets for Keycloak clients, APISIX admin key, database passwords, etc. Manage them securely (e.g., using environment variables from a protected `.env` file or a secrets manager).
* **Change Defaults:**
    * Change the default APISIX `admin_key`.
    * Change the default APISIX Dashboard `admin/admin` credentials (or better, protect it via APISIX/Keycloak).
* **Principle of Least Privilege:**
    * Grant only necessary permissions/roles to Keycloak clients and users.
    * Restrict access to APISIX Admin API.
* **Regular Updates:** Keep APISIX, Keycloak, and all other services updated to their latest stable versions.
* **Network Segmentation:** Use Docker networks to isolate services. Only expose necessary ports.
* **Input Validation:** Use APISIX plugins like `request-validation` for incoming requests.
* **Rate Limiting & WAF:** Implement rate limiting (`limit-count`, `limit-req`) and consider WAF capabilities if needed.
* **Logging and Monitoring:** Configure comprehensive logging (APISIX, Keycloak, services) and monitor metrics (Prometheus, Grafana).

## 7. Troubleshooting Tips

* **Check APISIX Logs:** `docker logs apisix_gateway` (or your APISIX container name). Look for errors related to the `openid-connect` plugin.
* **Check Keycloak Logs:** `docker logs keycloak_auth_server` (or your Keycloak container name). Look for login errors, client issues, etc.
* **Verify Discovery URL:** Ensure the `discovery` URL in the `openid-connect` plugin config is correct and accessible from within the APISIX container (`docker exec -it apisix_gateway curl <discovery_url>`).
* **Client Configuration Mismatch:** Double-check `client_id`, `client_secret`, `redirect_uri` between APISIX plugin config and Keycloak client settings.
* **Token Issues:** Use tools like [jwt.io](https://jwt.io) to decode JWT tokens and verify their signature, issuer, audience, and expiration.
* **Network Connectivity:** Ensure APISIX can reach Keycloak's token, userinfo, and jwks_uri endpoints.
* **CORS Issues:** If your frontend application interacts with APISIX-protected APIs, ensure CORS is correctly configured on APISIX (using the `cors` plugin).
