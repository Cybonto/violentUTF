## Quick Setup and Test Keycloak Integration with ViolentUTF API**

To integrate Keycloak with ViolentUTF API for authentication and authorization, we'll use the OpenID Connect (OIDC) protocol. In this guide, we'll configure ViolentUTF API to validate JWT tokens issued by Keycloak, extract user identity and roles from the tokens, and enforce role-based access control on API endpoints.

Below are the steps to achieve this:

1. **Configure Keycloak**: Set up a realm, client, and user roles in Keycloak.
2. **Set Up ViolentUTF API OAuth2 Authentication**: Use ViolentUTF API dependencies to validate JWT tokens and extract user information.
3. **Implement an Authenticated Endpoint**: Create an authenticated `/api/v1/hello` endpoint that requires valid authentication.

### 1. Configure Keycloak
Before integrating with ViolentUTF API, make sure you have a running Keycloak instance configure it as follows:
- **Install Keycloak**
  - You will need to install [Docker](https://www.docker.com/get-started/) and then run the following command
    ```bash
    docker run -p 8080:8080 -e KC_BOOTSTRAP_ADMIN_USERNAME=admin -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:26.1.4 start-dev 
    ```
  - You will run KeyCloak on localhost port 8080. Your default admin username and password is admin:admin.
- **KeyCloak Admin Login and Change Password**
  - Go to the [Keycloak Admin Console](http://localhost:8080/admin).
  - Log in with the username and password you created earlier.
  - On the top right, click "admin" and then "Manage Account"
  - In the "Personal info" page, click "Account security" on the left panel and chose "Signing in".
  - In "My password" item line, click "Update" and follow the on-screen instructions to change the default admin password.
- **Create a Realm**:
  - Open the [Keycloak Admin Console](http://localhost:8080/admin).
  - Click Keycloak next to master realm, then click Create Realm.
  - Enter `ViolentUTF` in the Realm name field.
  - Click Create.
- **Create a Client**: For example, `violentutf-api`.
  - Open the [Keycloak Admin Console](http://localhost:8080/admin).
  - Click the word master in the top-left corner, then click `ViolentUTF`.
  - Click Clients.
  - Click Create client
  - Fill in the form with the following values:
    - Set the client type to `openid-connect`.
    - Set the Client ID to `violentutf-api`.
    - Client authenticaion to On.
  - Click "Save".
  - Obtain the client credentials (Client ID and Client Secret).
- **Define Roles**: Create roles as needed for your application (e.g., `admin`, `user`).
- **Create Users**: Create users and assign roles to them.
  - Verify that you are still in the `ViolentUTF` realm, which is shown above the word Manage.
  - Click Users in the left-hand menu.
  - Click Create new user.
  - Fill in the form with the following values:
    - Username: `myuser`
    - First name: any first name
    - Last name: any last name
  - Click Create.

### 2. Set Up ViolentUTF API OAuth2 Authentication
- Make sure you are at the ViolentUTF folder (the program's root folder)
- **Update Pip**:
  ```bash
  pip install -U pip
  ```
- **Install Dependencies**:
  ```bash
  pip install -r requirements.txt
  ```
- **Check Authentication Utilities** - `core/security.py`, `core/config.py`, and `core/auth.py` must exist
- **Make sure** to rename `env.sample` to `.env` file with your proper Keycloak settings.
- **Generate a Self-Signed Certificate**:
  ```bash
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout key.pem -out cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=localhost"
  ```
- **Start ViolentUTF API with SSL**:
  ```bash
  uvicorn api:app --reload --host 0.0.0.0 --port 8000 \
    --ssl-keyfile=key.pem --ssl-certfile=cert.pem
  ```
- **Note**:
  - Do Not Commit `.env` to Version Control: Add `.env` to your .gitignore file.
  - Use Environment Variables in Production: Set environment variables directly in your production environment rather than using a `.env` file.
  - Clients (like browsers or API tools) may warn about the self-signed certificate. You'll need to accept or bypass these warnings during development.
  - It's common to run your FastAPI application behind a reverse proxy like Nginx or Traefik, which handles HTTPS termination.
  - In production you hould obtain a Trusted Certificate. Use certificates from a trusted Certificate Authority (CA), such as Let's Encrypt.


### 3. Implement an Authenticated Endpoint
- The `violentutf/api/v1/endpoints/hello.py` must exist
- Attempt to access the endpoint without a token:
  ```bash
  curl http://localhost:8000/api/v1/hello
  ```
- You should receive a `401 Unauthorized` error.
- Obtain an access token from Keycloak (using appropriate OAuth2 flow)
  ```bash
  python get_token.py
  ```
- Copy the `access_token` and include it in the below request:
  ```bash
  curl -H "Authorization: Bearer <access token without quotes here>" http://localhost:8000/api/v1/hello
  ```
- If you correctly configured KeyCloak, the token is valid and the user should be authenticated. You should receive:
  ```json
  {
    "message": "Hello, <username>!"
  }
  ```

### Troubleshooting Notes
You may try to look at the following areas if there are issues.
- Make sure you are in the right realm when creating users, roles, etc.
- Make sure the values in the .env fit the values KeyCloak provides.
- Analyze error messages in CLI windows carefull, especially the one for startig and hosting ViolentUTF API.
- Check network configurations especially when you host this stack on the cloud instead of local machine.