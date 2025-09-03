# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Unified User Context Manager for ViolentUTF

Standardizes user identification across all operations to prevent data fragmentation
"""

import hashlib
import logging
import os
import re
from typing import Any, Dict, Optional, Type

import streamlit as st

logger = logging.getLogger(__name__)


class UserContextManager:
    """Centralized manager for user context standardization"""

    # Define the standardization rules
    NORMALIZATION_RULES = {
        # Map various user formats to a single canonical format
        "ViolentUTF Web User": "violentutf.web",
        "Tam Nguyen": "tam.nguyen",
        "tam.nguyen@protonmail.com": "tam.nguyen",
        "violentutf.web": "violentutf.web",
    }

    # Default user for fallback
    DEFAULT_USER = "violentutf.web"

    @classmethod
    def normalize_username(cls: Type["UserContextManager"], username: str) -> str:
        """
        Normalize a username to a canonical format

        Args:
            username: Raw username from various sources

        Returns:
            str: Normalized canonical username
        """
        if not username:
            return cls.DEFAULT_USER

        # Trim whitespace
        username = username.strip()

        # Check direct mapping first
        if username in cls.NORMALIZATION_RULES:
            normalized = cls.NORMALIZATION_RULES[username]
            logger.debug("Normalized '%s' -> '%s' (direct mapping)", username, normalized)
            return normalized

        # Email format - extract local part
        if "@" in username:
            local_part = username.split("@")[0]
            # Clean up the local part
            normalized = re.sub(r"[^a-zA-Z0-9._-]", ".", local_part).lower()
            logger.debug("Normalized '%s' -> '%s' (email format)", username, normalized)
            return normalized

        # Names with spaces - convert to dot notation
        if " " in username:
            normalized = username.lower().replace(" ", ".")
            logger.debug("Normalized '%s' -> '%s' (space format)", username, normalized)
            return normalized

        # Already in good format - just lowercase
        normalized = username.lower()
        logger.debug("Normalized '%s' -> '%s' (lowercase)", username, normalized)
        return normalized

    @classmethod
    def get_canonical_username(cls: Type["UserContextManager"]) -> str:
        """
        Get the canonical username for the current session

        Returns:
            str: Canonical username that should be used for all operations
        """
        # Check if we have a cached canonical username
        if "canonical_username" in st.session_state:
            return st.session_state["canonical_username"]

        # Try multiple sources in priority order
        raw_username = None
        source = "unknown"

        # 1. Try Keycloak token (highest priority)
        if "access_token" in st.session_state:
            try:
                import jwt

                payload = jwt.decode(st.session_state["access_token"], options={"verify_signature": False})
                raw_username = payload.get("preferred_username") or payload.get("sub")
                source = "keycloak_token"
            except Exception as e:
                logger.warning("Failed to extract username from Keycloak token: %s", e)

        # 2. Try existing session state
        if not raw_username and "consistent_username" in st.session_state:
            raw_username = st.session_state["consistent_username"]
            source = "session_state"

        # 3. Try environment variable
        if not raw_username:
            raw_username = os.getenv("KEYCLOAK_USERNAME")
            source = "environment"

        # 4. Fallback to default
        if not raw_username:
            raw_username = cls.DEFAULT_USER
            source = "default"

        # Normalize the username
        canonical_username = cls.normalize_username(raw_username)

        # Cache it
        st.session_state["canonical_username"] = canonical_username

        logger.info("Determined canonical username: '%s' from %s (raw: '%s')", canonical_username, source, raw_username)

        return canonical_username

    @classmethod
    def get_user_context_for_token(cls: Type["UserContextManager"]) -> Dict[str, Any]:
        """
        Get standardized user context for JWT token creation

        Returns:
            dict: Standardized user context
        """
        canonical_username = cls.get_canonical_username()

        return {
            "preferred_username": canonical_username,
            "sub": canonical_username,  # Ensure 'sub' matches canonical username
            "email": f"{canonical_username}@violentutf.local",
            "name": f"ViolentUTF User ({canonical_username})",
            "roles": ["ai-api-access"],
        }

    @classmethod
    def verify_token_consistency(cls: Type["UserContextManager"]) -> bool:
        """
        Verify that existing tokens use the canonical username

        Returns:
            bool: True if tokens are consistent, False otherwise
        """
        if "api_token" not in st.session_state:
            return True  # No token to check

        try:
            import jwt

            payload = jwt.decode(st.session_state["api_token"], options={"verify_signature": False})

            token_username = payload.get("sub")
            canonical_username = cls.get_canonical_username()

            if token_username != canonical_username:
                logger.warning(
                    "Token inconsistency detected: token has '%s', canonical is '%s'",
                    token_username,
                    canonical_username,
                )
                return False

            return True

        except Exception as e:
            logger.error("Failed to verify token consistency: %s", e)
            return False

    @classmethod
    def refresh_token_if_needed(cls: Type["UserContextManager"]) -> bool:
        """
        Refresh API token if it doesn't match the canonical username

        Returns:
            bool: True if token was refreshed or is consistent, False on error
        """
        if cls.verify_token_consistency():
            return True  # Already consistent

        logger.info("Token inconsistency detected, refreshing...")

        try:
            # Clear the inconsistent token
            if "api_token" in st.session_state:
                del st.session_state["api_token"]

            # Create new token with canonical username
            from utils.jwt_manager import jwt_manager

            user_context = cls.get_user_context_for_token()
            api_token = jwt_manager.create_token(user_context)

            if api_token:
                st.session_state["api_token"] = api_token
                logger.info("Successfully refreshed token with canonical username")
                return True
            else:
                logger.error("Failed to create new token")
                return False

        except Exception as e:
            logger.error("Failed to refresh token: %s", e)
            return False

    @classmethod
    def get_database_hash_for_user(cls: Type["UserContextManager"], username: Optional[str] = None) -> str:
        """
        Get the database hash for a user (for DuckDB file naming)

        Args:
            username: Username to get hash for (defaults to canonical username)

        Returns:
            str: Database hash for the user
        """
        if username is None:
            username = cls.get_canonical_username()

        # Use the same hashing logic as DuckDB manager
        return hashlib.sha256(username.encode()).hexdigest()

    @classmethod
    def reset_user_context(cls: Type["UserContextManager"]) -> None:
        """Reset cached user context (useful for testing or logout)"""
        keys_to_remove = ["canonical_username", "consistent_username", "api_token"]

        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]

        logger.info("User context cache cleared")


# Convenience functions for backward compatibility
def get_consistent_username() -> str:
    """Get consistent username (backward compatibility)"""
    return UserContextManager.get_canonical_username()


def get_user_context_for_token() -> Dict[str, str]:
    """Get user context for token (backward compatibility)"""
    return UserContextManager.get_user_context_for_token()


def verify_user_consistency() -> bool:
    """Verify user consistency (backward compatibility)"""
    return UserContextManager.verify_token_consistency()
