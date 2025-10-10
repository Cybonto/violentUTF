# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Keycloak authentication helper for tests.
"""

import os
from typing import Any, Dict, Optional

import pytest
import requests
from requests.auth import HTTPBasicAuth


class KeycloakAuthenticator:
    """Helper class for Keycloak authentication in tests."""

    def __init__(self, base_url: str = None):
        """Initialize the Keycloak authenticator."""
        self.base_url = base_url or os.getenv("KEYCLOAK_URL", "http://localhost:8080")
        self.realm = os.getenv("KEYCLOAK_REALM", "violentutf")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "violentutf-api")
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

    def get_token(self, username: str = "testuser", password: str = "testpass") -> Optional[str]:
        """Get an access token from Keycloak."""
        token_url = f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "username": username,
            "password": password,
        }

        if self.client_secret:
            data["client_secret"] = self.client_secret

        try:
            response = requests.post(token_url, data=data, timeout=5)
            if response.status_code == 200:
                return response.json().get("access_token")
        except Exception:
            pass

        return None

    def get_headers(self, token: str = None) -> Dict[str, str]:
        """Get authorization headers."""
        if not token:
            token = self.get_token()

        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def is_keycloak_available(self) -> bool:
        """Check if Keycloak is available."""
        try:
            token = self.get_token()
            return token is not None
        except Exception:
            return False


# Global instance
keycloak_auth = KeycloakAuthenticator()


@pytest.fixture
def auth_headers():
    """Pytest fixture for authentication headers."""
    return keycloak_auth.get_headers()


__all__ = ["KeycloakAuthenticator", "keycloak_auth", "auth_headers"]