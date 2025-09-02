<<<<<<<< HEAD:tests/utils/keycloak_auth.py
# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License
========
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.
>>>>>>>> dev_nightly:tests/utils/keycloak_auth_helper.py

"""
Compatibility module for keycloak authentication.

This module re-exports from keycloak_auth_helper to maintain backward compatibility.
"""

from tests.utils.keycloak_auth_helper import KeycloakAuthenticator, keycloak_auth

__all__ = ["KeycloakAuthenticator", "keycloak_auth"]
