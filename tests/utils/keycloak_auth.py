# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Compatibility module for keycloak authentication.
This module re-exports from keycloak_auth_helper to maintain backward compatibility.
"""

from tests.utils.keycloak_auth_helper import KeycloakAuthenticator, keycloak_auth

__all__ = ["KeycloakAuthenticator", "keycloak_auth"]
