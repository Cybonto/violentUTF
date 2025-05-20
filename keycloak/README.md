Below is a step-by-step guide to set up a Keycloak instance for Violent UTF login. This guide covers installing prerequisites, running Keycloak via Docker, importing your realm configuration, and updating your application settings.

---
## 1. Prerequisites

- Install Docker and Docker Compose on your machine.
  - For Docker Desktop (Windows, macOS) or the Docker Engine on Linux.
- Clone or download the Violent UTF codebase.
- Ensure you have a working Python virtual environment set up with the required dependencies (as listed in requirements.txt).

---
## 2. Prepare Environment Variables

- Create a file named `.env` in your project root (or use the provided sample) with the following content. (Make sure to keep this file secure and add it to your .gitignore if you’re using version control.)

  Example `.env`:
  ```dotenv
  POSTGRES_PASSWORD=YourVeryStrongPassword123!
  ```

---
## 3. Launch Keycloak and PostgreSQL Using Docker Compose

- Navigate to the “keycloak” folder that contains the docker-compose.yml file.
- In a terminal, run:
  ```bash
  docker-compose up -d
  ```

- What this does:
  - “postgres” service is started with PostgreSQL (version 15) using the password defined in your .env file.
  - “keycloak” service is started from the quay.io/keycloak/keycloak image (version 26.1.4). It uses the production settings and reads critical values from environment variables.
  - Keycloak is configured to use the PostgreSQL database. It also starts with essential health, metrics, and HTTP settings.
- Wait a few minutes until Docker reports the services as healthy. (The “postgres” service healthcheck uses pg_isready to confirm database availability.)

---
## 4. Access Keycloak Admin Console

- Open your browser and navigate to:
  `http://localhost:8080`
- Log in with the default Keycloak administrator credentials:
  - Username: `admin`
  - Password: `admin`
- (For better security, you may later change these credentials as needed.)

---
## 5. Import Your Realm Configuration

- Once logged in, create or switch to a realm for Violent UTF. (If your team already exported your realm settings into a file such as `realm-export.json`, you can import it.)
  - In the Admin Console, click the “Master” dropdown at the top-left and select “Add realm.”
  - Choose the “Import realm” option and select your `realm-export.json` file.
- Verify that your realm now appears in the Keycloak list and that all roles, clients, and mappings are configured as expected.

---
## 6. Configure a Client for Violent UTF

- Inside your imported (or newly created) realm, create a new Client for your Streamlit application:
  - In the Admin Console, go to “Clients” and click “Create.”
  - Set the Client ID (for example, “streamlit-app”).
  - Select “openid-connect” as the protocol.
  - Set “Access Type” to Confidential (this will allow your app to securely store the client secret).
- After saving, navigate to the “Credentials” tab of the client and copy the “Secret” value.
- Configure the following settings under “Settings”:
  - Valid Redirect URIs: Add the redirect URI used by your Streamlit app (for example, `http://localhost:8501/oauth2callback` or `https://localhost:8501/oauth2callback` if using HTTPS).
  - Web Origins: Add the application URL (e.g., `http://localhost:8501`).
- Save the client settings.

---
## 7. Update Your Application’s Keycloak Settings

- Open the file `.streamlit/secrets.toml` in your project.
- Ensure it contains the required configuration for authentication. For example:

  ```toml
  [auth]
  redirect_uri = "http://localhost:8501/oauth2callback"
  cookie_secret = "A_STRONG_RANDOM_SECRET"  # change this to a strong random value

  [auth.keycloak]
  client_id = "streamlit-app"
  client_secret = "YOUR_KEYCLOAK_CLIENT_SECRET"  # paste the secret copied from Keycloak here
  server_metadata_url = "http://localhost:8080/realms/YourRealmName/.well-known/openid-configuration"
  ```

- Replace `YourRealmName` with the name of your imported (or created) realm.
- Ensure that the `redirect_uri` and other URLs match your development setup and that the `cookie_secret` is secure.

---
## 8. Testing Your Setup

- Run your Streamlit app (e.g., “Home.py” or your main entry point).
- When you open the application in your browser (usually running on port 8501), you should be redirected to the Keycloak login page.
- Log in with a user from your Keycloak realm.
- After successful authentication, you should be redirected back to your application’s Welcome page with a greeting that uses your name.
- If everything works, your Keycloak instance is properly configured for Violent UTF.

---
## 9. Troubleshooting and Tips

- If you encounter connection errors in your Streamlit app:
  - Verify that Docker services are running with `docker-compose ps` and the health status is OK.
  - Check that the correct environment variables (POSTGRES_PASSWORD, KC_HOSTNAME, etc.) are set.
- Make sure that your `.env` and `secrets.toml` files are updated with the correct values.
- Review logs in the `logs/` or `app_logs/` directories if your application reports errors.
- Consult the Keycloak documentation for additional guidance on configuring realms and clients.

---
## 10. Security Considerations

- Never hard-code production passwords or secrets in your source code.
- Use strong, unique passwords for Keycloak and PostgreSQL in any production environment.
- Keep access to your `.env` and `secrets.toml` files restricted.
- When you move to a production environment, consider using HTTPS and additional security measures.
