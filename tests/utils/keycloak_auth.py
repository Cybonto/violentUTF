"""
Compatibility module for keycloak authentication.
This module re-exports from keycloak_auth_helper to maintain backward compatibility.
"""

from tests.utils.keycloak_auth_helper import *

# Re-export the main objects for backward compatibility
from tests.utils.keycloak_auth_helper import KeycloakAuthenticator, keycloak_auth

__all__ = ["KeycloakAuthenticator", "keycloak_auth"]
