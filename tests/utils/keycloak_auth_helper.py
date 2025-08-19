# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Keycloak authentication utility for tests.

Handles OAuth2 authentication with Keycloak to obtain JWT tokens for testing
"""

import os
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin

import jwt
import requests


class KeycloakAuthenticator:
    """Handles Keycloak OAuth2 authentication for testing."""

    def __init__(self: "KeycloakAuthenticator") -> None:
        # Load environment variables from project .env files
        self._load_environment()

        # Load Keycloak configuration from environment
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080/")
        self.realm = os.getenv("KEYCLOAK_REALM", "ViolentUTF")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "violentutf")
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET")
        self.username = os.getenv("KEYCLOAK_USERNAME", "violentutf.web")
        self.password = os.getenv("KEYCLOAK_PASSWORD")

        # Build Keycloak URLs
        self.realm_url = urljoin(self.keycloak_url, f"realms/{self.realm}/")
        self.token_url = urljoin(self.realm_url, "protocol/openid-connect/token")
        self.userinfo_url = urljoin(self.realm_url, "protocol/openid-connect/userinfo")

        # Cache for tokens
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = 0

    def _load_environment(self: "KeycloakAuthenticator") -> None:
        """Load environment variables from project .env files"""
        from pathlib import Path

        # Get project root directory
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent

        # List of .env files to load
        env_files = [
            project_root / "violentutf" / ".env",
            project_root / "violentutf_api" / "fastapi_app" / ".env",
            project_root / "keycloak" / ".env",
        ]

        for env_file in env_files:
            if env_file.exists():
                try:
                    with open(env_file, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                # Only set if not already in environment
                                if key not in os.environ:
                                    os.environ[key] = value
                except Exception as e:
                    print(f"Warning: Could not load {env_file}: {e}")

    def is_keycloak_available(self: "KeycloakAuthenticator") -> bool:
        """Check if Keycloak is running and accessible."""
        try:
            response = requests.get(self.realm_url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def authenticate(self: "KeycloakAuthenticator") -> Optional[str]:
        """
        Authenticate with Keycloak using OAuth2 Resource Owner Password Credentials Grant.
        Returns the access token if successful, None otherwise
        """
        if not self.client_secret or not self.password:
            print("❌ Keycloak credentials not configured")
            return None

        if not self.is_keycloak_available():
            print("❌ Keycloak service not available")
            return None

        # Check if we have a valid cached token
        if self._access_token and time.time() < self._token_expires_at - 30:  # 30s buffer
            return self._access_token

        try:
            # OAuth2 Resource Owner Password Credentials Grant
            data = {
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": self.username,
                "password": self.password,
                "scope": "openid profile email",
            }

            response = requests.post(self.token_url, data=data, timeout=10)

            if response.status_code != 200:
                print(f"❌ Keycloak authentication failed: {response.status_code} - {response.text}")
                return None

            token_data = response.json()
            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")

            # Calculate expiry time
            expires_in = token_data.get("expires_in", 300)  # Default 5 minutes
            self._token_expires_at = time.time() + expires_in

            print(f"✅ Keycloak authentication successful, token expires in {expires_in}s")
            return self._access_token

        except Exception as e:
            print(f"❌ Keycloak authentication error: {e}")
            return None

    def refresh_access_token(self: "KeycloakAuthenticator") -> Optional[str]:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            return self.authenticate()

        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self._refresh_token,
            }

            response = requests.post(self.token_url, data=data, timeout=10)

            if response.status_code != 200:
                print(f"❌ Token refresh failed: {response.status_code}")
                return self.authenticate()  # Fall back to full authentication

            token_data = response.json()
            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")

            expires_in = token_data.get("expires_in", 300)
            self._token_expires_at = time.time() + expires_in

            print(f"✅ Token refreshed successfully, expires in {expires_in}s")
            return self._access_token

        except Exception as e:
            print(f"❌ Token refresh error: {e}")
            return self.authenticate()

    def get_user_info(self: "KeycloakAuthenticator", access_token: str) -> Optional[Dict]:
        """Get user information using the access token."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(self.userinfo_url, headers=headers, timeout=10)

            if response.status_code != 200:
                print(f"❌ Failed to get user info: {response.status_code}")
                return None

            return response.json()

        except Exception as e:
            print(f"❌ Error getting user info: {e}")
            return None

    def create_violentutf_jwt(self: "KeycloakAuthenticator", keycloak_token: str) -> Optional[str]:
        """
        Create a ViolentUTF-compatible JWT token using Keycloak user info.
        This mimics the token creation process in the ViolentUTF application
        """
        try:
            # Get user info from Keycloak
            user_info = self.get_user_info(keycloak_token)
            if not user_info:
                return None

            # Load ViolentUTF JWT secret
            jwt_secret = os.getenv("JWT_SECRET_KEY")
            if not jwt_secret:
                print("❌ JWT_SECRET_KEY not configured")
                return None

            # Create ViolentUTF JWT payload
            now = datetime.now(timezone.utc)
            payload = {
                "sub": user_info.get("preferred_username", "test_user"),
                "email": user_info.get("email", "test@example.com"),
                "name": user_info.get("name", "Test User"),
                "roles": ["ai-api-access"],  # Grant AI API access
                "iat": now,
                "exp": now.timestamp() + 3600,  # 1 hour expiry
                "keycloak_token": True,  # Mark as Keycloak-derived
            }

            # Create JWT token
            violentutf_token = jwt.encode(payload, jwt_secret, algorithm="HS256")

            print(f"✅ ViolentUTF JWT created for user: {payload['email']}")
            return violentutf_token

        except Exception as e:
            print(f"❌ Error creating ViolentUTF JWT: {e}")
            return None

    def get_auth_headers(self: "KeycloakAuthenticator") -> Dict[str, str]:
        """Get authentication headers for API requests."""
        # First get Keycloak token.
        keycloak_token = self.authenticate()
        if not keycloak_token:
            return {}

        # Create ViolentUTF JWT
        violentutf_jwt = self.create_violentutf_jwt(keycloak_token)
        if not violentutf_jwt:
            return {}

        # Return headers with ViolentUTF JWT and APISIX API key
        headers = {
            "Authorization": f"Bearer {violentutf_jwt}",
            "Content-Type": "application/json",
            "X-Real-IP": "127.0.0.1",
            "X-Forwarded-For": "127.0.0.1",
            "X-Forwarded-Host": "localhost:9080",
            "X-API-Gateway": "APISIX",
        }

        # Add APISIX API key if available
        apisix_api_key = os.getenv("VIOLENTUTF_API_KEY")
        if apisix_api_key:
            headers["apikey"] = apisix_api_key

        return headers

    def test_authentication_flow(self: "KeycloakAuthenticator") -> bool:
        """Test the complete authentication flow."""
        print("\n🔐 Testing Keycloak Authentication Flow")
        print("=" * 50)

        # Step 1: Check Keycloak availability
        print("1. Checking Keycloak availability...")
        if not self.is_keycloak_available():
            print("   ❌ Keycloak not available")
            return False
        print("   ✅ Keycloak is running")

        # Step 2: Authenticate with Keycloak
        print("2. Authenticating with Keycloak...")
        keycloak_token = self.authenticate()
        if not keycloak_token:
            print("   ❌ Keycloak authentication failed")
            return False
        print("   ✅ Keycloak authentication successful")

        # Step 3: Get user info
        print("3. Getting user information...")
        user_info = self.get_user_info(keycloak_token)
        if not user_info:
            print("   ❌ Failed to get user info")
            return False
        print(f"   ✅ User: {user_info.get('email', 'unknown')}")

        # Step 4: Create ViolentUTF JWT
        print("4. Creating ViolentUTF JWT...")
        violentutf_jwt = self.create_violentutf_jwt(keycloak_token)
        if not violentutf_jwt:
            print("   ❌ Failed to create ViolentUTF JWT")
            return False
        print("   ✅ ViolentUTF JWT created")

        # Step 5: Test token validation
        print("5. Validating JWT token...")
        try:
            jwt_secret = os.getenv("JWT_SECRET_KEY")
            decoded = jwt.decode(violentutf_jwt, jwt_secret, algorithms=["HS256"])
            print(f"   ✅ JWT valid, user: {decoded.get('email')}")
        except Exception as e:
            print(f"   ❌ JWT validation failed: {e}")
            return False

        print("\n🎉 Authentication flow test completed successfully!")
        return True


# Global authenticator instance
keycloak_auth = KeycloakAuthenticator()


if __name__ == "__main__":
    # Test the authentication flow when run directly
    keycloak_auth.test_authentication_flow()
