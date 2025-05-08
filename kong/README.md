# Kong Gateway with Docker Compose

This project provides a robust and customizable setup for deploying Kong Gateway using Docker Compose. It supports running Kong in DB-less mode or with a PostgreSQL database, includes security best practices by default, and allows for easy configuration adjustments.

## Table of Contents

1.  [What is Kong?](https://www.google.com/search?q=%23what-is-kong)
2.  [Prerequisites](https://www.google.com/search?q=%23prerequisites)
3.  [Key Features](https://www.google.com/search?q=%23key-features)
4.  [Directory Structure](https://www.google.com/search?q=%23directory-structure)
5.  [Getting Started](https://www.google.com/search?q=%23getting-started)
      * [1. Create Database Password File](https://www.google.com/search?q=%231-create-database-password-file)
      * [2. Define Administrator Credentials](https://www.google.com/search?q=%232-define-administrator-credentials)
      * [3. Running Kong in DB-less Mode (Default)](https://www.google.com/search?q=%233-running-kong-in-db-less-mode-default)
      * [4. Running Kong with a PostgreSQL Database](https://www.google.com/search?q=%234-running-kong-with-a-postgresql-database)
      * [5. Stopping the Setup](https://www.google.com/search?q=%235-stopping-the-setup)
6.  [Accessing Kong](https://www.google.com/search?q=%23accessing-kong)
      * [Kong Proxy](https://www.google.com/search?q=%23kong-proxy)
      * [Kong Admin API](https://www.google.com/search?q=%23kong-admin-api)
      * [Kong Manager (GUI)](https://www.google.com/search?q=%23kong-manager-gui)
7.  [Customizing Your Setup](https://www.google.com/search?q=%23customizing-your-setup)
      * [Kong and PostgreSQL Versions](https://www.google.com/search?q=%23kong-and-postgresql-versions)
      * [Network Ports](https://www.google.com/search?q=%23network-ports)
      * [Kong Environment Variables](https://www.google.com/search?q=%23kong-environment-variables)
      * [Declarative Configuration (`config/kong.yaml`)](https://www.google.com/search?q=%23declarative-configuration-configkongyaml)
      * [Database Settings](https://www.google.com/search?q=%23database-settings)
      * [Exposing Admin Interfaces (Advanced)](https://www.google.com/search?q=%23exposing-admin-interfaces-advanced)
8.  [Managing the Deployment](https://www.google.com/search?q=%23managing-the-deployment)
9.  [Important Security Considerations](https://www.google.com/search?q=%23important-security-considerations)
10. [Troubleshooting](https://www.google.com/search?q=%23troubleshooting)
11. [Original Kong Docker Information](https://www.google.com/search?q=%23original-kong-docker-information)

## What is Kong?

Kong, or Kong API Gateway, is a cloud-native, platform-agnostic, scalable API Gateway distinguished for its high performance and extensibility via plugins.

  * Kong's Official documentation: [docs.konghq.com](https://docs.konghq.com/)
  * Official Kong Docker distribution: [Docker Hub](https://hub.docker.com/_/kong)

## Prerequisites

  * **Docker Engine:** Version 20.10.0 or newer is recommended (as the `docker-compose.yml` uses Compose specification v3.9).
  * **Docker Compose:** Ensure Docker Compose is installed and compatible with your Docker Engine.

## Key Features

  * **Flexible Kong Version:** Defaults to a stable Kong version (e.g., `kong:3.6.1.4`) but is easily customizable using the `KONG_DOCKER_TAG` environment variable.
  * **Modern PostgreSQL:** Utilizes `postgres:16` for the DB-backed mode, offering current features and security.
  * **Secure by Default:**
      * **Restricted Admin Interfaces:** Kong Admin API and Kong Manager GUI ports are mapped only to `127.0.0.1` (localhost) on the host machine, preventing direct external network exposure.
      * **RBAC Enabled:** Role-Based Access Control is enabled by default (`KONG_ENFORCE_RBAC=on`) for enhanced security.
      * **Kong Manager Authentication:** Kong Manager is protected by Basic Authentication by default (`KONG_ADMIN_GUI_AUTH=basic-auth`), requiring credentials from a defined Kong User.
  * **Declarative Configuration:** Leverages `config/kong.yaml` for defining Kong services, routes, plugins, consumers, users, credentials, and RBAC assignments, promoting GitOps practices.
  * **Secrets Management:** Uses Docker secrets for securely managing the PostgreSQL password.
  * **Container Optimizations:** The Kong container runs with a read-only root filesystem and uses `tmpfs` for ephemeral data like the Nginx prefix and temporary files, enhancing security and performance.
  * **Profile-based Deployment:** Easily switch between DB-less mode (default) and DB-backed mode using Docker Compose profiles.

## Directory Structure

```
kong/
├── docker-compose.yml      # Main Docker Compose file
├── config/
│   └── kong.yaml           # Declarative configuration for Kong (including users)
├── POSTGRES_PASSWORD       # Stores the PostgreSQL password (you need to create this)
└── README.md               # This file
```

## Getting Started

### 1\. Create Database Password File

(Only required if you plan to use DB-backed mode)
Before starting, create a file to store the PostgreSQL password. This file is used by Docker Secrets.

Create a file named `POSTGRES_PASSWORD` in the `kong/` directory:

```bash
echo "YourStrongDbPassword123!" > POSTGRES_PASSWORD
```

**Important:** Replace `"YourStrongDbPassword123!"` with a strong, unique password for the database.

### 2\. Define Administrator Credentials

Open the `kong/config/kong.yaml` file. You need to set secure passwords for the pre-defined administrative users:

  * **For Kong Manager GUI Login (`kong_manager_admin`):**
    Locate the `basicauth_credentials` section for `kong_manager_admin` and change the placeholder password:

    ```yaml
    basicauth_credentials:
      - consumer: null
        username: kong_manager_admin
        password: YourSecurePasswordForKongManager! # <<< CHANGE THIS to a strong password
    ```

  * **For Proxied Admin API Access (`admin-proxy-user`):**
    If you plan to use the proxied Admin API service, also change the password for `admin-proxy-user`:

    ```yaml
    basicauth_credentials:
      # ... (credential for kong_manager_admin)
      - consumer: admin-proxy-user
        username: admin-proxy-user
        password: AnotherSecurePasswordForProxyUser! # <<< CHANGE THIS if used
    ```

**Save the `config/kong.yaml` file after setting these passwords.**

### 3\. Running Kong in DB-less Mode (Default)

In DB-less mode, Kong runs without a database, and its configuration (including users and credentials defined above) is managed through `config/kong.yaml`.

```bash
docker compose up -d
```

This command starts a single Kong container.

### 4\. Running Kong with a PostgreSQL Database

To run Kong with PostgreSQL as its backing database:

```bash
KONG_DATABASE=postgres docker compose --profile database up -d
```

This command will:

  * Start the PostgreSQL (`db`) container.
  * Start the Kong migration containers to set up or update the database schema. Kong will load entities (like users and credentials from `config/kong.yaml`) into the database.
  * Start the Kong (`kong`) container, configured to use the PostgreSQL database.

### 5\. Stopping the Setup

To stop and remove the containers:

```bash
docker compose down
```

To remove the PostgreSQL data volume as well (use with caution):

```bash
docker compose down -v
```

## Accessing Kong

### Kong Proxy

  * **HTTP:** `http://localhost:8000`
  * **HTTPS:** `https://localhost:8443`
    *Note: SSL termination is handled by Kong based on its configuration. You'll need to configure SSL certificates in Kong for HTTPS to work properly.*

### Kong Admin API

The Admin API is restricted to `localhost` on the Docker host for security.

  * **HTTP:** `http://localhost:8001`
  * **HTTPS:** `http://localhost:8444`
    *If you've configured the `kong-admin-api-service` in `config/kong.yaml` with the `basic-auth` plugin, accessing `http://localhost:8000/admin-api` would require the `admin-proxy-user` credentials.*

### Kong Manager (GUI)

Kong Manager is restricted to `localhost` on the Docker host and protected by Basic Authentication by default.

  * **URL:** `http://localhost:8002`
  * **Username:** `kong_manager_admin`
  * **Password:** The password you set for `kong_manager_admin` in the `kong/config/kong.yaml` file (where it said `YourSecurePasswordForKongManager!`).

The `kong_manager_admin` user is declaratively configured with the `super-admin` RBAC role, granting full administrative access to Kong Manager.

## Customizing Your Setup

### Kong and PostgreSQL Versions

  * **Kong Version:** Set the `KONG_DOCKER_TAG` environment variable (e.g., `export KONG_DOCKER_TAG="kong:3.5"`). Default is specified in `docker-compose.yml`.
  * **PostgreSQL Version:** Modify the `image` tag for the `db` service in `docker-compose.yml`.

### Network Ports

Adjust port mappings in the `kong` service definition in `docker-compose.yml`:

  * **Proxy Ports:** Host IP is customizable via `${KONG_INBOUND_PROXY_LISTEN:-0.0.0.0}`. Host port can be changed (e.g., `8080:8000`).
  * **Admin/Manager Ports:** Mapped to `127.0.0.1` on host. Host port number can be changed (e.g., `127.0.0.1:8003:8002`).

### Kong Environment Variables

Key `KONG_*` variables in `docker-compose.yml` for the `kong` service:

  * `KONG_LOG_LEVEL` (default: `info`).
  * `KONG_ADMIN_GUI_AUTH` (default: `basic-auth`).
  * **`KONG_ADMIN_GUI_SESSION_CONF`:** Contains session settings. **CRITICAL: You MUST change the default `secret` value (e.g., `CHANGEME_KONG_ADMIN_GUI_SESSION_SECRET`) in this JSON string to a strong, unique key.** If exposing Manager via HTTPS, set `cookie_secure: true`.

### Declarative Configuration (`config/kong.yaml`)

This file (`kong/config/kong.yaml`) is central to your Kong setup. It's used to define:

  * Services, Routes, Plugins
  * Consumers
  * **Users (like `kong_manager_admin`) and their Basic Auth credentials**
  * **RBAC role assignments (e.g., assigning `super-admin` to `kong_manager_admin`)**

Refer to the [Kong Declarative Configuration documentation](https://docs.konghq.com/gateway/latest/production/deployment-topologies/db-less-and-declarative-config/) for syntax.

### Database Settings

For DB-backed mode, configure via `KONG_PG_*` environment variables or use the defaults. The password is set in the `POSTGRES_PASSWORD` file.

### Exposing Admin Interfaces (Advanced)

To expose Admin API or Kong Manager beyond `localhost`:

1.  Modify `docker-compose.yml`: Change `127.0.0.1` to `0.0.0.0` or a specific IP in the `ports` mapping for admin interfaces.
2.  **Security Implications:** This is risky. Ensure strong authentication, HTTPS, and consider firewalls.

## Managing the Deployment

  * **View Logs:** `docker compose logs -f kong` (or `db`).
  * **View Services:** `docker compose ps`.
  * **Access Kong Shell:** `docker compose exec kong /bin/sh`.

## Important Security Considerations

  * **Change ALL Placeholder Passwords:**
      * In `config/kong.yaml`: for `kong_manager_admin` and `admin-proxy-user`.
      * In `POSTGRES_PASSWORD` file for the database.
      * The `secret` within `KONG_ADMIN_GUI_SESSION_CONF` in `docker-compose.yml`.
  * **Admin Interface Exposure:** Keep restricted to `localhost` unless explicitly needed and fully secured.
  * **Regular Updates:** Update Kong and PostgreSQL versions.
  * **Review Kong Security Documentation.**

## Troubleshooting

  * **Port Conflicts:** Check host port usage.
  * **DB Connection/Migration Issues:** Check `db` and `kong-migrations*` logs.
  * **Declarative Config Errors:** Check `kong` logs for parsing errors of `config/kong.yaml`.
  * **Login Issues:** Double-check passwords in `config/kong.yaml` are correctly set and Kong has restarted to apply them. Ensure the `kong_manager_admin` user is correctly defined and assigned the `super-admin` role in `config/kong.yaml`.

## Original Kong Docker Information

This setup is based on common practices. For official Kong Docker information:

  * [Kong on Docker Hub](https://hub.docker.com/_/kong)
  * [Kong Docker GitHub](https://github.com/Kong/docker-kong)

-----