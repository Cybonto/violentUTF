# 0. The Home Page

## Authentication Flows

### User Accesses the Streamlit App:
- The user navigates to the Streamlit application URL.
- If the user is not authenticated, the app displays a login button.

### User Initiates Login:
- The user clicks the "Log in" button, triggering `st.login("keycloak")`.
- Streamlit redirects the user to the Keycloak authentication endpoint.

### Keycloak Authentication:
- The user is presented with the Keycloak login page.
- Keycloak authenticates the user.

### Keycloak Redirects Back to Streamlit:
- Upon successful authentication, Keycloak redirects the user back to the Streamlit app using the `redirect_uri` specified.
- The redirection includes an authorization code as a query parameter.

### Streamlit Exchanges Authorization Code for Tokens:
- The Streamlit app receives the authorization code.
- These tokens are JSON Web Tokens (JWTs) containing user identity information.

### Token Validation:
- The app validates the ID token's signature and claims (issuer, audience, expiration).
- Extracts user information (e.g., username, roles) from the token.

### User Session Established:
- A user session is created within the Streamlit app.
- `st.experimental_user` is populated with the user's details.

### User Interacts with the App:
- The user gains access to the app's features.
- Authorization logic can be applied based on user roles.

### User Logout:
- When the user clicks "Log out," `st.logout()` is called.
- The app redirects the user to Keycloak's logout endpoint to invalidate the session server-side.

## Configurations

### Keycloak Setup:
- Create a New Client.

### Streamlit Configuration:
- Update `.streamlit/secrets.toml`.
