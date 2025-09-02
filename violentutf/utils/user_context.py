# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""User Context module.

Copyright (c) 2025 ViolentUTF Contributors.
Licensed under the MIT License.

This file is part of ViolentUTF - An AI Red Teaming Platform.
See LICENSE file in the project root for license information.
"""

import logging
import os
from typing import Any, Dict

import jwt
import streamlit as st

logger = logging.getLogger(__name__)


def get_consistent_username() -> str:
    """
    Get a consistent username for the current session.

    This function ensures that the same username is used across all pages,
    preventing issues with user-specific data storage in DuckDB.

    ALWAYS uses the Keycloak account name (preferred_username) as the unique identifier,
    not the display name which may not be unique.

    Priority order:
    1. Keycloak preferred_username from SSO token
    2. Environment variable KEYCLOAK_USERNAME
    3. Default fallback

    Returns:
        str: Consistent username for the current session (always the account name)
    """
    # Check if we have a cached username in session state
    if "consistent_username" in st.session_state:
        return str(st.session_state["consistent_username"])

    # Try to get username from Keycloak token if available
    if "access_token" in st.session_state:
        try:

            # Decode without verification to check the username
            payload = jwt.decode(st.session_state["access_token"], options={"verify_signature": False})

            # Always use preferred_username (account name) as the unique identifier
            preferred_username = payload.get("preferred_username")
            if preferred_username:
                # Cache it in session state
                st.session_state["consistent_username"] = preferred_username
                logger.info("Using Keycloak preferred_username: %s", preferred_username)
                return str(preferred_username)

        except (OSError, ValueError, KeyError, TypeError) as e:
            logger.warning("Failed to decode Keycloak token: %s", e)

    # Fallback to environment variable
    env_username = os.getenv("KEYCLOAK_USERNAME", "violentutf.web")

    # Cache it in session state
    st.session_state["consistent_username"] = env_username

    logger.info("Using consistent username from environment: %s", env_username)
    return env_username


def get_user_context() -> Dict[str, Any]:
    """
    Get consistent user context for JWT token creation.

    This ensures all pages create tokens with the same user information,
    preventing data isolation issues between pages.

    Returns:
        dict: User context with consistent username and other attributes
    """
    username = get_consistent_username()

    return {
        "preferred_username": username,
        "sub": username,  # Ensure 'sub' matches username
        "email": f"{username}@violentutf.local",
        "name": "ViolentUTF User",
        "roles": ["ai-api-access"],
    }


def verify_user_consistency() -> bool:
    """
    Verify that the current token matches the expected username.

    This can be used to detect and warn about inconsistent user contexts.

    Returns:
        bool: True if user context is consistent, False otherwise.
    """
    if "api_token" in st.session_state:
        try:

            # Decode without verification to check the username
            payload = jwt.decode(st.session_state["api_token"], options={"verify_signature": False})

            token_username = payload.get("sub")
            expected_username = get_consistent_username()

            if token_username != expected_username:
                logger.warning(
                    "User context mismatch: token has '%s', expected '%s'",
                    token_username,
                    expected_username,
                )
                return False

            return True

        except (OSError, ValueError, KeyError, TypeError) as e:
            logger.error("Failed to verify user consistency: %s", e)
            return False

    return True
