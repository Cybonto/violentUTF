"""
Security utilities for JWT token generation and validation
SECURITY: Enhanced with comprehensive validation to prevent token injection attacks
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
from app.core.config import settings
from app.core.password_policy import PasswordStrength, validate_password_strength
from app.core.validation import SecurityLimits, sanitize_string, validate_jwt_token
from fastapi import HTTPException, status
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token settings
ALGORITHM = settings.ALGORITHM
# Use JWT_SECRET_KEY for compatibility with Streamlit JWT manager
SECRET_KEY = settings.JWT_SECRET_KEY or settings.SECRET_KEY


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload data to encode
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any] | None:
    """
    Decode and validate a JWT token with comprehensive security checks

    Args:
        token: JWT token to decode

    Returns:
        Decoded payload or None if invalid
    """
    if not token:
        logger.warning("Empty token provided for validation")
        return None

    try:
        # First, validate token format and basic structure
        validate_jwt_token(token)

        # Decode with signature verification
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Additional payload validation
        if not payload.get("sub"):
            logger.warning("JWT token missing required 'sub' claim")
            return None

        # Validate subject (username/user_id)
        subject = sanitize_string(payload["sub"])
        if len(subject) > SecurityLimits.MAX_USERNAME_LENGTH:
            logger.warning(f"JWT subject too long: {len(subject)} characters")
            return None

        payload["sub"] = subject

        # Validate roles if present
        if "roles" in payload:
            if isinstance(payload["roles"], list):
                # Sanitize roles
                safe_roles = []
                for role in payload["roles"]:
                    if isinstance(role, str):
                        safe_role = sanitize_string(role).lower()
                        if safe_role and len(safe_role) <= 50:
                            safe_roles.append(safe_role)
                payload["roles"] = safe_roles
            else:
                logger.warning("JWT roles claim is not a list")
                payload["roles"] = []

        # Validate email if present
        if "email" in payload and payload["email"]:
            try:
                email = sanitize_string(payload["email"]).lower()
                if "@" not in email or len(email) > 254:
                    logger.warning("Invalid email in JWT payload")
                    payload["email"] = None
                else:
                    payload["email"] = email
            except Exception:
                payload["email"] = None

        logger.debug(f"Successfully validated JWT token for user: {payload.get('sub')}")
        return dict(payload)

    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidSignatureError:
        logger.warning("JWT token has invalid signature")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None
    except ValueError as e:
        logger.warning(f"JWT validation failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during JWT validation: {str(e)}")
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password with input validation

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    if not plain_password or not hashed_password:
        logger.warning("Empty password or hash provided for verification")
        return False

    # Validate password length to prevent DoS attacks
    if len(plain_password) > 1000:
        logger.warning("Password too long for verification")
        return False

    try:
        return bool(pwd_context.verify(plain_password, hashed_password))
    except Exception as e:
        logger.error(f"Password verification error: {str(e)}")
        return False


def get_password_hash(password: str, username: Optional[str] = None, email: Optional[str] = None) -> str:
    """
    Hash a password using bcrypt with comprehensive security validation

    Args:
        password: Plain text password
        username: Username for personal info validation
        email: Email for personal info validation

    Returns:
        Hashed password

    Raises:
        ValueError: If password doesn't meet security requirements
    """
    if not password:
        raise ValueError("Password is required")

    # Comprehensive password strength validation
    validation_result = validate_password_strength(password=password, username=username, email=email)

    if not validation_result.is_valid:
        error_msg = "Password does not meet security requirements: " + "; ".join(validation_result.errors)
        logger.warning(f"Password validation failed: {len(validation_result.errors)} errors")
        raise ValueError(error_msg)

    # Warn about weak passwords but allow them if they pass basic validation
    if validation_result.strength in [PasswordStrength.WEAK, PasswordStrength.MODERATE]:
        logger.warning(
            f"Weak password detected (strength: {validation_result.strength.value}, score: {validation_result.score})"
        )
        if validation_result.warnings:
            logger.info(f"Password warnings: {'; '.join(validation_result.warnings)}")

    try:
        hashed = pwd_context.hash(password)
        logger.info(
            f"Password hashed successfully (strength: {validation_result.strength.value}, score: {validation_result.score})"
        )
        return str(hashed)
    except Exception as e:
        logger.error(f"Password hashing error: {str(e)}")
        raise ValueError("Failed to hash password")


def create_api_key_token(user_id: str, key_name: str, permissions: Optional[list] = None, key_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an API key token with extended expiration and input validation

    Args:
        user_id: User identifier
        key_name: Name/description of the API key
        permissions: List of permissions/scopes
        key_id: Unique identifier for the key

    Returns:
        Dictionary with token and metadata

    Raises:
        ValueError: If input validation fails
    """
    # Validate inputs
    if not user_id:
        raise ValueError("User ID is required")

    if not key_name:
        raise ValueError("Key name is required")

    # Sanitize and validate user_id
    user_id = sanitize_string(user_id)
    if len(user_id) > SecurityLimits.MAX_USERNAME_LENGTH:
        raise ValueError("User ID too long")

    # Sanitize and validate key_name
    key_name = sanitize_string(key_name)
    if len(key_name) < 3 or len(key_name) > SecurityLimits.MAX_API_KEY_NAME_LENGTH:
        raise ValueError(f"Key name must be 3-{SecurityLimits.MAX_API_KEY_NAME_LENGTH} characters")

    # Validate permissions
    if permissions:
        if not isinstance(permissions, list):
            raise ValueError("Permissions must be a list")

        if len(permissions) > SecurityLimits.MAX_PERMISSIONS:
            raise ValueError(f"Too many permissions (max {SecurityLimits.MAX_PERMISSIONS})")

        safe_permissions = []
        for perm in permissions:
            if not isinstance(perm, str):
                raise ValueError("Permission must be a string")

            perm = sanitize_string(perm).lower()
            if not perm:
                continue

            if len(perm) > 50:
                raise ValueError("Permission name too long")

            # Validate permission format
            import re

            if not re.match(r"^[a-z0-9:_-]+$", perm):
                raise ValueError(f"Invalid permission format: {perm}")

            safe_permissions.append(perm)

        permissions = safe_permissions
    else:
        permissions = ["api:access"]

    # Validate key_id if provided
    if key_id:
        key_id = sanitize_string(key_id)
        if len(key_id) > 64:
            raise ValueError("Key ID too long")

    # API keys have longer expiration (1 year by default)
    expires_delta = timedelta(days=365)

    data = {"sub": user_id, "key_name": key_name, "key_id": key_id, "type": "api_key", "permissions": permissions}

    try:
        token = create_access_token(data, expires_delta)

        return {
            "token": token,
            "key_name": key_name,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + expires_delta).isoformat(),
            "permissions": permissions,
        }
    except Exception as e:
        logger.error(f"Failed to create API key token: {str(e)}")
        raise ValueError("Failed to create API key token")
