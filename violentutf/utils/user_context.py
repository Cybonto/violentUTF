# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
User Context Management for ViolentUTF.

Ensures consistent user identification across all pages
"""

import logging
import os
from typing import Any

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
    # Check if we have a cached username in session state.
    if "consistent_username" in st.session_state:
        return st.session_state["consistent_username"]

    # Try to get username from Keycloak token if available
    if "access_token" in st.session_state:
        try:
            import jwt

            # Decode without verification to check the username
            payload = jwt.decode(st.session_state["access_token"], options={"verify_signature": False})

            # Always use preferred_username (account name) as the unique identifier
            preferred_username = payload.get("preferred_username")
            if preferred_username:
                # Cache it in session state
                st.session_state["consistent_username"] = preferred_username
                logger.info(f"Using Keycloak preferred_username: {preferred_username}")
                return preferred_username

        except Exception as e:
            logger.warning(f"Failed to decode Keycloak token: {e}")

    # Fallback to environment variable
    env_username = os.getenv("KEYCLOAK_USERNAME", "violentutf.web")

    # Cache it in session state
    st.session_state["consistent_username"] = env_username

    logger.info(f"Using consistent username from environment: {env_username}")
    return env_username


def get_user_context_for_token() -> dict:
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


def verify_user_consistency() -> Any:
    """
    Verify that the current token matches the expected username.

    This can be used to detect and warn about inconsistent user contexts.
    """
    if "api_token" in st.session_state:
        try:
            import jwt

            # Decode without verification to check the username
            payload = jwt.decode(st.session_state["api_token"], options={"verify_signature": False})

            token_username = payload.get("sub")
            expected_username = get_consistent_username()

            if token_username != expected_username:
                logger.warning(
                    f"User context mismatch: token has '{token_username}', " f"expected '{expected_username}'"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Failed to verify user consistency: {e}")
            return False

    return True
