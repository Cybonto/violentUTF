"""
User Context Manager for FastAPI
Provides standardized user identification to match Streamlit's UserContextManager
"""

import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class FastAPIUserContextManager:
    """
    FastAPI-specific user context manager that mirrors Streamlit's normalization rules
    """

    # Same normalization rules as Streamlit
    NORMALIZATION_RULES = {
        "ViolentUTF Web User": "violentutf.web",
        "Tam Nguyen": "tam.nguyen",
        "tam.nguyen@protonmail.com": "tam.nguyen",
        "violentutf.web": "violentutf.web",
    }

    DEFAULT_USER = "violentutf.web"

    @classmethod
    def normalize_username(cls, username: str) -> str:
        """
        Normalize a username to a canonical format (mirrors Streamlit logic)

        Args:
            username: Raw username from JWT token

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
            logger.debug(f"Normalized '{username}' -> '{normalized}' (direct mapping)")
            return normalized

        # Email format - extract local part
        if "@" in username:
            local_part = username.split("@")[0]
            # Clean up the local part
            normalized = re.sub(r"[^a-zA-Z0-9._-]", ".", local_part).lower()
            logger.debug(f"Normalized '{username}' -> '{normalized}' (email format)")
            return normalized

        # Names with spaces - convert to dot notation
        if " " in username:
            normalized = username.lower().replace(" ", ".")
            logger.debug(f"Normalized '{username}' -> '{normalized}' (space format)")
            return normalized

        # Already in good format - just lowercase
        normalized = username.lower()
        logger.debug(f"Normalized '{username}' -> '{normalized}' (lowercase)")
        return normalized

    @classmethod
    def extract_canonical_username(cls, jwt_payload: Dict) -> str:
        """
        Extract and normalize username from JWT payload

        Args:
            jwt_payload: Decoded JWT payload

        Returns:
            str: Canonical username
        """
        # Extract raw username from JWT
        raw_username = jwt_payload.get("sub") or jwt_payload.get("preferred_username")

        if not raw_username:
            logger.warning("No username found in JWT payload, using default")
            return cls.DEFAULT_USER

        # Log deprecation warnings for old fields
        if "name" in jwt_payload and jwt_payload["name"] != raw_username:
            logger.warning(
                f"JWT contains deprecated 'name' field: {jwt_payload.get('name')}, " f"using sub: {raw_username}"
            )

        # Normalize the username
        canonical_username = cls.normalize_username(raw_username)

        if canonical_username != raw_username:
            logger.info(f"Normalized username: '{raw_username}' -> '{canonical_username}'")

        return canonical_username

    @classmethod
    def create_user_context(cls, jwt_payload: Dict) -> Dict:
        """
        Create standardized user context from JWT payload

        Args:
            jwt_payload: Decoded JWT payload

        Returns:
            dict: Standardized user context
        """
        canonical_username = cls.extract_canonical_username(jwt_payload)

        return {
            "canonical_username": canonical_username,
            "raw_username": jwt_payload.get("sub"),
            "email": jwt_payload.get("email", f"{canonical_username}@violentutf.local"),
            "roles": jwt_payload.get("roles", ["ai-api-access"]),
            "name": f"ViolentUTF User ({canonical_username})",
        }
