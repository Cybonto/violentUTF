# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Keycloak Authentication Test Utility

This module provides test utilities for Keycloak authentication testing
in the ViolentUTF end-to-end testing framework.

SECURITY: All test data is for defensive security research only.
"""

import json
import time
from typing import Dict, Optional
from unittest.mock import MagicMock

import requests


class KeycloakTestAuth:
    """
    Test utility for Keycloak authentication in end-to-end tests.
    
    This is a mock implementation that simulates Keycloak authentication
    for testing purposes. In the RED phase, this will provide basic
    functionality to support test execution.
    """
    
    def __init__(self, keycloak_url: str = "http://localhost:8080"):
        self.keycloak_url = keycloak_url
        self.realm = "violentutf"
        self.client_id = "violentutf-client"
        self.mock_users = {
            "test_security_researcher": {
                "role": "security_analyst",
                "permissions": ["garak", "security_datasets"],
                "password": "test_password"
            },
            "test_compliance_officer": {
                "role": "compliance_manager", 
                "permissions": ["ollegen1", "compliance_datasets"],
                "password": "test_password"
            },
            "test_ai_researcher": {
                "role": "researcher",
                "permissions": ["all_datasets"],
                "password": "test_password"
            }
        }
        
    def authenticate_user(self, username: str, password: str) -> Dict[str, str]:
        """
        Mock user authentication for testing.
        
        In the RED phase, this returns a mock JWT token.
        In the GREEN phase, this should integrate with actual Keycloak.
        """
        if username in self.mock_users and self.mock_users[username]["password"] == password:
            # Generate mock JWT token
            mock_token = {
                "access_token": f"mock_jwt_token_{username}_{int(time.time())}",
                "refresh_token": f"mock_refresh_token_{username}_{int(time.time())}",
                "token_type": "Bearer",
                "expires_in": 3600,
                "user_role": self.mock_users[username]["role"],
                "permissions": self.mock_users[username]["permissions"]
            }
            return mock_token
        else:
            raise AuthenticationError(f"Authentication failed for user: {username}")
    
    def validate_token(self, token: str) -> bool:
        """
        Mock token validation for testing.
        
        In the RED phase, this provides basic validation.
        In the GREEN phase, this should validate against Keycloak.
        """
        # Simple mock validation - check if token starts with mock prefix
        return token.startswith("mock_jwt_token_")
    
    def get_user_permissions(self, token: str) -> list:
        """
        Mock user permission retrieval for testing.
        
        Extracts permissions from mock token for testing purposes.
        """
        # Extract username from mock token
        if token.startswith("mock_jwt_token_"):
            parts = token.split("_")
            if len(parts) >= 3:
                username = parts[3]  # Extract username part
                if username in self.mock_users:
                    return self.mock_users[username]["permissions"]
        
        return []


class AuthenticationError(Exception):
    """Exception raised for authentication failures."""
    pass