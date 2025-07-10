"""
User Context Management for ViolentUTF
Ensures consistent user identification across all pages
"""

import logging

from utils.user_context_manager import UserContextManager

logger = logging.getLogger(__name__)


def get_consistent_username() -> str:
    """
    Get a consistent username for the current session.

    This function ensures that the same username is used across all pages,
    preventing issues with user-specific data storage in DuckDB.

    Uses the new UserContextManager for standardized user identification.

    Returns:
        str: Canonical username for the current session
    """
    return UserContextManager.get_canonical_username()


def get_user_context_for_token() -> dict:
    """
    Get consistent user context for JWT token creation.

    This ensures all pages create tokens with the same user information,
    preventing data isolation issues between pages.

    Returns:
        dict: User context with canonical username and other attributes
    """
    return UserContextManager.get_user_context_for_token()


def verify_user_consistency() -> bool:
    """
    Verify that the current token matches the expected username.

    This can be used to detect and warn about inconsistent user contexts.

    Returns:
        bool: True if user context is consistent, False otherwise
    """
    return UserContextManager.verify_token_consistency()
