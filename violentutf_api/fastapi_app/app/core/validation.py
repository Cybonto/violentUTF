"""
Comprehensive input validation module
SECURITY: Validates and sanitizes all user inputs to prevent injection attacks and data corruption
"""

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import jwt
from fastapi import HTTPException, status
from pydantic import BaseModel, EmailStr, Field, validator

logger = logging.getLogger(__name__)

# Constants to avoid bandit B104 hardcoded binding warnings
WILDCARD_ADDRESS = "0.0.0.0"  # nosec B104


# Security constants for validation
class SecurityLimits:
    """Security limits for input validation"""

    MAX_STRING_LENGTH = 1000
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_LIST_ITEMS = 100
    MAX_NESTED_DEPTH = 5
    MAX_JSON_SIZE = 10000  # bytes

    # Username / identifier limits
    MIN_USERNAME_LENGTH = 3
    MAX_USERNAME_LENGTH = 50
    MIN_NAME_LENGTH = 1
    MAX_NAME_LENGTH = 100

    # API key limits
    MIN_API_KEY_NAME_LENGTH = 3
    MAX_API_KEY_NAME_LENGTH = 100
    MAX_PERMISSIONS = 20


# Validation patterns
class ValidationPatterns:
    """Regex patterns for validation"""
    # fmt: off
    # SECURITY CRITICAL: DO NOT MODIFY THESE PATTERNS
    # These regex patterns are security-critical and must not be modified by automated tools.
    # Any spaces added to character ranges (e.g., [A-Z] becoming [A - Z]) will break validation.

    # Safe username pattern (alphanumeric, dash, underscore)
    USERNAME = re.compile(r"^[a-zA-Z0-9_-]+$")  # noqa: E501

    # Safe name pattern (letters, spaces, basic punctuation)
    SAFE_NAME = re.compile(r"^[a-zA-Z0-9\s\-_.()]+$")

    # Safe identifier for API keys, dataset names, etc.
    SAFE_IDENTIFIER = re.compile(r"^[a-zA-Z0-9_-]+$")

    # Generator name pattern (allows dots for model names like gpt3.5)
    GENERATOR_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")

    # Generator type pattern (allows spaces for types like "AI Gateway")
    GENERATOR_TYPE = re.compile(r"^[a-zA-Z0-9\s_-]+$")

    # Safe file name pattern
    SAFE_FILENAME = re.compile(r"^[a-zA-Z0-9_.-]+$")

    # Safe URL pattern (basic validation)
    SAFE_URL = re.compile(r"^https?://[a-zA-Z0-9.-]+[a-zA-Z0-9/._-]*$")

    # JWT token pattern
    JWT_TOKEN = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")

    # Role pattern (lowercase alphanumeric with dash)
    ROLE_PATTERN = re.compile(r"^[a-z0-9-]+$")  # noqa: E501
    # fmt: on


class SafeString(str):
    """String type that ensures content is sanitized"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("String expected")

        # Check length
        if len(v) > SecurityLimits.MAX_STRING_LENGTH:
            raise ValueError(f"String too long (max {SecurityLimits.MAX_STRING_LENGTH} characters)")

        # Sanitize dangerous characters
        sanitized = sanitize_string(v)
        return cls(sanitized)


class SafeIdentifier(str):
    """Safe identifier for API keys, usernames, etc."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError("String expected")

        v = v.strip()

        # Check length
        if len(v) < SecurityLimits.MIN_USERNAME_LENGTH:
            raise ValueError(f"Identifier too short (min {SecurityLimits.MIN_USERNAME_LENGTH} characters)")
        if len(v) > SecurityLimits.MAX_USERNAME_LENGTH:
            raise ValueError(f"Identifier too long (max {SecurityLimits.MAX_USERNAME_LENGTH} characters)")

        # Check pattern
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Identifier must contain only alphanumeric characters, underscores, and hyphens")

        return cls(v)


def sanitize_string(value: str) -> str:
    """
    Sanitize string input to prevent injection attacks
    """
    if not isinstance(value, str):
        return str(value)

    # Remove null bytes and control characters
    sanitized = "".join(char for char in value if ord(char) >= 32 or char in ["\n", "\r", "\t"])

    # Limit length
    if len(sanitized) > SecurityLimits.MAX_STRING_LENGTH:
        sanitized = sanitized[: SecurityLimits.MAX_STRING_LENGTH]
        logger.warning(f"String truncated to {SecurityLimits.MAX_STRING_LENGTH} characters")

    return sanitized.strip()


def validate_email(email: str) -> str:
    """
    Validate email address format
    """
    if not email:
        raise ValueError("Email is required")

    email = email.strip().lower()

    # Basic format check
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email format")

    if len(email) > 254:  # RFC 5321 limit
        raise ValueError("Email address too long")

    return email


def validate_username(username: str) -> str:
    """
    Validate username format and length
    """
    if not username:
        raise ValueError("Username is required")

    username = username.strip()

    if len(username) < SecurityLimits.MIN_USERNAME_LENGTH:
        raise ValueError(f"Username too short (min {SecurityLimits.MIN_USERNAME_LENGTH} characters)")

    if len(username) > SecurityLimits.MAX_USERNAME_LENGTH:
        raise ValueError(f"Username too long (max {SecurityLimits.MAX_USERNAME_LENGTH} characters)")

    if not ValidationPatterns.USERNAME.match(username):
        raise ValueError("Username must contain only alphanumeric characters, underscores, and hyphens")

    return username


def validate_role_list(roles: List[str]) -> List[str]:
    """
    Validate list of roles
    """
    if not roles:
        return []

    if len(roles) > SecurityLimits.MAX_PERMISSIONS:
        raise ValueError(f"Too many roles (max {SecurityLimits.MAX_PERMISSIONS})")

    validated_roles = []
    for role in roles:
        if not isinstance(role, str):
            raise ValueError("Role must be a string")

        role = role.strip().lower()

        if not role:
            continue

        if len(role) > 50:
            raise ValueError("Role name too long (max 50 characters)")

        if not ValidationPatterns.ROLE_PATTERN.match(role):
            raise ValueError(
                f"Invalid role format: {role}. Must contain only lowercase alphanumeric characters and hyphens"
            )

        if role not in validated_roles:
            validated_roles.append(role)

    return validated_roles


def validate_jwt_token(token: str) -> Dict[str, Any]:
    """
    Validate JWT token structure and basic format
    """
    if not token:
        raise ValueError("Token is required")

    token = token.strip()

    # Remove 'Bearer ' prefix if present
    if token.startswith("Bearer "):
        token = token[7:]

    # Check basic JWT format
    if not ValidationPatterns.JWT_TOKEN.match(token):
        raise ValueError("Invalid JWT token format")

    # Check token length (reasonable bounds)
    if len(token) > 2048:
        raise ValueError("Token too long")

    if len(token) < 50:
        raise ValueError("Token too short")

    try:
        # Decode header to check algorithm
        header = jwt.get_unverified_header(token)

        # Validate algorithm
        allowed_algorithms = ["HS256", "RS256", "ES256"]
        if header.get("alg") not in allowed_algorithms:
            raise ValueError(f"Unsupported JWT algorithm: {header.get('alg')}")

        # Get unverified payload for basic validation
        payload = jwt.decode(token, options={"verify_signature": False})

        # Validate required claims
        required_claims = ["sub", "iat", "exp"]
        for claim in required_claims:
            if claim not in payload:
                raise ValueError(f"Missing required JWT claim: {claim}")

        # Validate expiration
        if payload.get("exp"):
            exp_time = datetime.fromtimestamp(payload["exp"])
            if exp_time < datetime.now():
                raise ValueError("JWT token has expired")

        return payload

    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid JWT token: {str(e)}")


def validate_url(url: str) -> str:
    """
    Validate URL format and security
    """
    if not url:
        raise ValueError("URL is required")

    url = url.strip()

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError("Invalid URL format")

    # Check scheme
    if parsed.scheme not in ["http", "https"]:
        raise ValueError("URL must use http or https scheme")

    # Check host
    if not parsed.netloc:
        raise ValueError("URL must have a valid host")

    # Enhanced security checks for URL validation
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid URL: no hostname")

    # Enhanced dangerous hosts list
    dangerous_hosts = [
        "localhost",
        "127.",
        "::1",
        "10.",  # Private network
        "192.168.",  # Private network
        "172.",  # Private network (172.16 - 31.x.x)
        "169.254.",  # Link - local
        "metadata.google.internal",
        "metadata",
        "metadata.aws",
        "metadata.azure.com",
    ]

    # Special handling for wildcard address - always block
    # nosec B104 - This is security validation, not binding to all interfaces
    if host == WILDCARD_ADDRESS:
        raise ValueError("Access to 0.0.0.0 is not allowed")

    for dangerous in dangerous_hosts:
        if host.startswith(dangerous):
            raise ValueError(f"Access to internal / localhost URLs not allowed: {host}")

    # Additional check for private IP ranges
    import ipaddress

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"Access to private / internal IP addresses not allowed: {host}")
    except ipaddress.AddressValueError:
        # Not an IP address, hostname validation above should catch issues
        pass

    # Additional check for private IP ranges
    import ipaddress

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            raise ValueError(f"Access to private/internal IP addresses not allowed: {host}")
    except ipaddress.AddressValueError:
        # Not an IP address, hostname validation above should catch issues
        pass

    if len(url) > 2048:
        raise ValueError("URL too long")

    return url


def validate_json_data(data: Union[str, Dict, List], max_depth: int = SecurityLimits.MAX_NESTED_DEPTH) -> Any:
    """
    Validate JSON data structure and prevent deeply nested objects
    """
    if isinstance(data, str):
        if len(data.encode("utf-8")) > SecurityLimits.MAX_JSON_SIZE:
            raise ValueError(f"JSON data too large (max {SecurityLimits.MAX_JSON_SIZE} bytes)")

        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

    def check_depth(obj, current_depth=0):
        if current_depth > max_depth:
            raise ValueError(f"JSON structure too deeply nested (max depth {max_depth})")

        if isinstance(obj, dict):
            if len(obj) > SecurityLimits.MAX_LIST_ITEMS:
                raise ValueError(f"Too many dictionary items (max {SecurityLimits.MAX_LIST_ITEMS})")

            for key, value in obj.items():
                if not isinstance(key, str):
                    raise ValueError("Dictionary keys must be strings")
                if len(str(key)) > 100:
                    raise ValueError("Dictionary key too long")
                check_depth(value, current_depth + 1)

        elif isinstance(obj, list):
            if len(obj) > SecurityLimits.MAX_LIST_ITEMS:
                raise ValueError(f"Too many list items (max {SecurityLimits.MAX_LIST_ITEMS})")

            for item in obj:
                check_depth(item, current_depth + 1)

        elif isinstance(obj, str):
            if len(obj) > SecurityLimits.MAX_STRING_LENGTH:
                raise ValueError(f"String too long in JSON (max {SecurityLimits.MAX_STRING_LENGTH} characters)")

    check_depth(data)
    return data


def validate_file_upload(filename: str, content_type: str, file_size: int) -> str:
    """
    Validate file upload parameters
    """
    if not filename:
        raise ValueError("Filename is required")

    filename = filename.strip()

    # Validate filename
    if not ValidationPatterns.SAFE_FILENAME.match(filename):
        raise ValueError(
            "Invalid filename format. Only alphanumeric characters, dots, underscores, and hyphens allowed"
        )

    if len(filename) > 255:
        raise ValueError("Filename too long")

    # Check file extension
    allowed_extensions = [".csv", ".txt", ".json", ".yaml", ".yml", ".tsv"]
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise ValueError(f"File type not allowed. Supported: {', '.join(allowed_extensions)}")

    # Validate content type
    allowed_content_types = [
        "text/csv",
        "text/plain",
        "application/json",
        "application/x-yaml",
        "text/yaml",
        "text/tab-separated-values",
    ]

    if content_type not in allowed_content_types:
        logger.warning(f"Unexpected content type: {content_type}")

    # Check file size (10MB limit)
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        raise ValueError(f"File too large (max {max_size // (1024 * 1024)}MB)")

    return filename


class ValidationError(HTTPException):
    """Custom validation error with proper HTTP status"""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Validation error: {detail}")


def create_validation_error(detail: str) -> ValidationError:
    """Create a validation error with security logging"""
    logger.warning(f"Validation error: {detail}")
    return ValidationError(detail)


# Enhanced validators for common patterns
def validate_generator_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate generator parameters dictionary
    """
    if not isinstance(parameters, dict):
        raise ValueError("Parameters must be a dictionary")

    validated = {}

    for key, value in parameters.items():
        # Validate key
        if not isinstance(key, str):
            raise ValueError("Parameter keys must be strings")

        key = key.strip()
        if len(key) > 100:
            raise ValueError("Parameter key too long")

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
            raise ValueError(f"Invalid parameter key format: {key}")

        # Validate value based on type
        if isinstance(value, str):
            value = sanitize_string(value)
            if len(value) > SecurityLimits.MAX_STRING_LENGTH:
                raise ValueError(f"Parameter value too long for key: {key}")
        elif isinstance(value, (int, float, bool)):
            pass  # These are safe
        elif isinstance(value, list):
            if len(value) > SecurityLimits.MAX_LIST_ITEMS:
                raise ValueError(f"Too many items in parameter list: {key}")
            value = [sanitize_string(str(item)) if isinstance(item, str) else item for item in value]
        elif isinstance(value, dict):
            value = validate_json_data(value, max_depth=2)  # Limited depth for parameters
        else:
            raise ValueError(f"Unsupported parameter type for key: {key}")

        validated[key] = value

    return validated
