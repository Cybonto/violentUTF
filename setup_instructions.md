# Setup Instructions

Here's how to set up and run your Dockerized ViolentUTF stack with "Lean" and "Full" profiles:

**1. Directory Structure:**

```
your_project_root/
├── docker-compose.yml      # The main Docker Compose file (updated with profiles)
├── keycloak_import/
│   └── realm-export.json
├── violentutf/
│   ├── Dockerfile
│   ├── .dockerignore
│   └── ... (ViolentUTF app files)
├── apisix_conf/            # NEW
│   └── config.yaml
├── prometheus_conf/        # NEW
│   └── prometheus.yml
└── otel_conf/              # NEW
    └── otel-collector-config.yaml
```

**2. Populate New Configuration Files:**

* **`your_project_root/apisix_conf/config.yaml`**: Save the APISIX `config.yaml` content provided above into this file.
    * **Important for APISIX-Keycloak Integration**:
        * You will need to create an OIDC client for APISIX within your Keycloak `violentutf-realm`.
        * Go to your Keycloak admin console (`http://localhost:8080`), select the `violentutf-realm`.
        * Go to `Clients` > `Create client`.
        * Set `Client type` to `OpenID Connect`.
        * Set a `Client ID` (e.g., `apisix-gateway-client`).
        * Click `Next`.
        * Enable `Client authentication`.
        * Set `Authentication flow` to standard.
        * Under `Access settings`, set `Valid redirect URIs` to `http://localhost:9080/*` (or your APISIX public URL if different, followed by `/*` for flexibility during testing). For production, be more specific, e.g., `http://your-apisix-domain/callback*`.
        * Save the client.
        * Go to the `Credentials` tab of the newly created client and copy the `Client secret`.
        * You will use this `Client ID` and `Client secret` when configuring the `openid-connect` plugin on specific APISIX routes or services via the APISIX Admin API (`http://localhost:9180`). The `apisix_conf/config.yaml` enables the plugin, but the actual route protection is configured dynamically.
* **`your_project_root/prometheus_conf/prometheus.yml`**: Save the Prometheus `prometheus.yml` content.
* **`your_project_root/otel_conf/otel-collector-config.yaml`**: Save the OpenTelemetry Collector `otel-collector-config.yaml` content.

**3. Configure Environment Variables:**

* Open `docker-compose.yml`.
* **ViolentUTF**: Update `OPENAI_API_KEY` if needed. The `OTEL_EXPORTER_OTLP_ENDPOINT` is set to send traces to `otel-collector`.
* **APISIX**: The `apisix_conf/config.yaml` has a default admin key. **CHANGE THIS** if you plan to expose the admin API. OpenTelemetry settings for APISIX are primarily in its `config.yaml` under `plugin_attr.opentelemetry`.

**4. Build and Run the Stack:**

Navigate to `your_project_root` directory in your terminal.

* **To run the "Lean" profile (Keycloak + ViolentUTF):**
    ```bash
    docker-compose --profile lean up --build -d
    ```
* **To run the "Full" profile (all services):**
    ```bash
    docker-compose --profile full up --build -d
    ```
    (If a service does not have a profile explicitly assigned in `docker-compose.yml`, it will be included if no profiles are specified on the command line, or if its implicitly part of a selected profile through dependencies. Here, `lean` and `full` are explicit.)
* To run all services defined (which will be the "full" stack as services without a profile are always started, and "full" profile services will also start):
    ```bash
    docker-compose up --build -d
    ```

The first time, Docker will download new images and build/rebuild existing ones.

**5. Accessing the Services (Full Profile):**

* **Keycloak:** `http://localhost:8080/` (Admin: `admin/admin`)
* **ViolentUTF:** `http://localhost:8501/`
* **APISIX Gateway:**
    * Proxy: `http://localhost:9080/`
    * Admin API: `http://localhost:9180/` (Use the admin key from `apisix_conf/config.yaml`)
* **ETCD:** Primarily used by APISIX internally. (Port `2379`)
* **Prometheus:** `http://localhost:9090/` (Targets: `http://localhost:9090/targets`)
* **Grafana:** `http://localhost:3000/` (Login: `admin/admin`). You'll need to add Prometheus as a data source (`http://prometheus:9090`).
* **OpenTelemetry Collector:** Receives data on ports `4317` (gRPC) and `4318` (HTTP).
* **Jaeger UI (for Traces):** `http://localhost:16686/`

**6. Using APISIX with Keycloak:**

1.  After the stack is up, access the APISIX Admin API (e.g., using Postman or cURL) or the APISIX Dashboard (if you deploy one separately) to configure routes.
2.  When creating a route that you want to protect with Keycloak:
    * Add the `openid-connect` plugin to the route.
    * Configure it with:
        * `discovery`: `http://keycloak:8080/realms/violentutf-realm/.well-known/openid-configuration`
        * `client_id`: The client ID you created in Keycloak for APISIX.
        * `client_secret`: The client secret from Keycloak.
        * `bearer_only`: `false` (APISIX will handle redirect to Keycloak login page).
        * `redirect_uri`: e.g., `http://localhost:9080/your-service/callback` (This path needs to be registered in Keycloak's valid redirect URIs for the APISIX client).
        * Other parameters as needed (scope, session settings, etc. - refer to APISIX `openid-connect` plugin documentation).

**7. Stopping the Stack:**

* To stop all services:
    ```bash
    docker-compose down
    ```
* To stop services for a specific profile (e.g., lean):
    ```bash
    docker-compose --profile lean down
    ```
* To stop and remove volumes (Warning: deletes data):
    ```bash
    docker-compose down -v
    ```

This provides a comprehensive setup for both lean and full deployments of your ViolentUTF stack!