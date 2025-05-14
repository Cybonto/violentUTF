from keycloak import KeycloakOpenID
import os
from dotenv import load_dotenv

# Load environment variables from .env file (BEST PRACTICE!)
load_dotenv()

# --- Keycloak Configuration (from environment variables) ---
KEYCLOAK_URL = os.environ.get("KEYCLOAK_URL")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM")
CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID")
CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET")  # For confidential clients ONLY
USERNAME = os.environ.get("KEYCLOAK_USERNAME")
PASSWORD = os.environ.get("KEYCLOAK_PASSWORD")

# --- Validate Environment Variables ---
if not all([KEYCLOAK_URL, KEYCLOAK_REALM, CLIENT_ID, USERNAME, PASSWORD]):
    raise ValueError("Missing required environment variables.  Check your .env file.")

# --- Initialize Keycloak Client ---
keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_URL,
    client_id=CLIENT_ID,
    realm_name=KEYCLOAK_REALM,
    client_secret_key=CLIENT_SECRET,  # Only needed for confidential clients
    verify=True,  # Verify SSL certificates (VERY IMPORTANT in production)
)


def get_token_with_resource_owner_grant():
    """Gets a token using the Resource Owner Password Credentials Grant.
       This is ONLY suitable for trusted clients and for testing/development.
       AVOID THIS IN PRODUCTION if possible.
    """
    try:
        token = keycloak_openid.token(username=USERNAME, password=PASSWORD)
        return token
    except Exception as e:
        print(f"Error during token retrieval: {e}")
        return None

def get_token_with_client_credentials():
    """Gets a token using Client Credentials flow.
        This is suitable for machine-to-machine communication.
        Client MUST be confidential.
    """
    if not CLIENT_SECRET:
        raise ValueError("CLIENT_SECRET is required for client credentials flow.")

    try:
        token = keycloak_openid.get_token() #no need for user and password
        return token
    except Exception as e:
        print(f"Error getting client credentials token: {e}")
        return None

def refresh_token(refresh_token_str):
    """Refreshes an existing token using the refresh token."""
    try:
        new_token = keycloak_openid.refresh_token(refresh_token_str)
        return new_token
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None


def get_user_info(access_token):
    """Gets user information using the access token."""
    try:
        userinfo = keycloak_openid.userinfo(access_token)
        return userinfo
    except Exception as e:
        print(f"Error getting user info: {e}")
        return None

def main():
    """Main function to demonstrate token retrieval and user info."""

    # Choose your grant type (uncomment the one you want to use):

    # --- Resource Owner Password Credentials Grant (FOR TESTING ONLY) ---
    token_response = get_token_with_resource_owner_grant()

    # --- Client Credentials Grant (FOR MACHINE-TO-MACHINE) ---
    # token_response = get_token_with_client_credentials()

    if token_response:
        print("Token Response:")
        print(token_response)

        access_token = token_response.get("access_token")
        if access_token:
             # --- Get User Info (Optional) ---
            user_info = get_user_info(access_token)
            if user_info:
                print("\nUser Info:")
                print(user_info)

        refresh_token_str = token_response.get("refresh_token")
        if refresh_token_str:
            # --- Refresh token (Optional) ---
            #Wait till access_token expire
            # new_token_response = refresh_token(refresh_token_str)
            # if new_token_response:
            #     print("\nRefreshed Token Response:")
            #     print(new_token_response)
            pass

if __name__ == "__main__":
    main()