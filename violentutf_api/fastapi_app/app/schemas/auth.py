# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Authentication and authorization schemas.

SECURITY: Enhanced with comprehensive input validation to prevent injection attacks
"""
# pylint: disable=no-self-argument  # Pydantic validators use cls, not self
import re
from datetime import datetime
from typing import List, Optional, Type

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.password_policy import validate_password_strength
from app.core.validation import (
    ValidationPatterns,
    sanitize_string,
    validate_role_list,
    validate_username,
)


class Token(BaseModel):
    """OAuth2 token response."""

    access_token: str = Field(..., min_length=50, max_length=2048, description="JWT access token")

    token_type: str = Field(default="bearer", pattern="^bearer$", description="Token type")
    expires_in: int = Field(..., gt=0, le=86400, description="Token expiration time in seconds")

    @field_validator("access_token")
    @classmethod
    def validate_access_token(cls: Type["Token"], v: str) -> str:
        """Validate JWT token format."""
        if not ValidationPatterns.JWT_TOKEN.match(v):

            raise ValueError("Invalid JWT token format")
        return str(v)


class TokenData(BaseModel):
    """Token payload data."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)

    email: Optional[EmailStr] = None
    roles: List[str] = Field(default_factory=list, description="User roles", max_length=20)

    @field_validator("username")
    @classmethod
    def validate_username_field(cls: Type["TokenData"], v: Optional[str]) -> Optional[str]:
        """Validate username format."""
        if v is not None:

            return str(validate_username(v))
        return v

    @field_validator("roles")
    @classmethod
    def validate_roles_field(cls: Type["TokenData"], v: List[str]) -> List[str]:
        """Validate roles list."""
        return validate_role_list(v)


class UserInfo(BaseModel):
    """User information."""

    username: str = Field(..., min_length=3, max_length=50)

    email: Optional[EmailStr] = None
    roles: List[str] = Field(default_factory=list, description="User roles", max_length=20)

    @field_validator("username")
    @classmethod
    def validate_username_field(cls: Type["UserInfo"], v: str) -> str:
        """Validate username format."""
        return validate_username(v)

    @field_validator("roles")
    @classmethod
    def validate_roles_field(cls: Type["UserInfo"], v: List[str]) -> List[str]:
        """Validate roles list."""
        return validate_role_list(v)


class APIKeyCreate(BaseModel):
    """Request to create a new API key."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Name/description for the API key",
    )

    permissions: List[str] = Field(
        default=["api:access"],
        description="List of permissions for this key",
        max_length=20,
    )

    @field_validator("name")
    @classmethod
    def validate_name_field(cls: Type["APIKeyCreate"], v: str) -> str:
        """Validate API key name."""
        v_str = sanitize_string(v)
        if not ValidationPatterns.SAFE_NAME.match(v_str):
            raise ValueError("Name contains invalid characters")
        return v_str

    @field_validator("permissions")
    @classmethod
    def validate_permissions_field(cls: Type["APIKeyCreate"], v: List[str]) -> List[str]:
        """Validate permissions list."""
        validated = []

        for perm in v:
            perm = sanitize_string(perm).lower()
            if not re.match(r"^[a-z0-9:_-]+$", perm):
                raise ValueError(f"Invalid permission format: {perm}")
            if len(perm) > 50:
                raise ValueError("Permission name too long")
            validated.append(perm)
        return validated


class APIKey(BaseModel):
    """API key information."""

    id: str

    name: str
    created_at: str
    expires_at: str
    last_used: Optional[str] = None
    permissions: List[str] = []
    active: bool = True


class APIKeyResponse(BaseModel):
    """Response when creating a new API key."""

    key_id: str

    api_key: str = Field(description="The actual JWT token to use")
    name: str
    created_at: str
    expires_at: str
    permissions: List[str]


class APIKeyList(BaseModel):
    """List of API keys."""

    keys: List[APIKey]


class TokenInfoResponse(BaseModel):
    """JWT token information response."""

    username: str

    email: Optional[str] = None
    roles: List[str] = []
    expires_at: datetime
    issued_at: datetime
    has_ai_access: bool
    token_valid: bool


class TokenValidationRequest(BaseModel):
    """Token validation request."""

    required_roles: Optional[List[str]] = Field(
        default_factory=list, description="Required roles for validation", max_length=20
    )
    check_ai_access: Optional[bool] = Field(default=True)

    @field_validator("required_roles")
    @classmethod
    def validate_required_roles_field(cls: Type["TokenValidationRequest"], v: List[str]) -> List[str]:
        """Validate required roles list."""
        if v:
            return validate_role_list(v)
        return []


class TokenValidationResponse(BaseModel):
    """Token validation response."""

    valid: bool

    username: Optional[str] = None
    roles: List[str] = []
    has_ai_access: bool
    missing_roles: List[str] = []
    error: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request."""

    username: str = Field(..., min_length=3, max_length=50)

    password: str = Field(..., min_length=8, max_length=128)
    remember_me: Optional[bool] = Field(default=False)

    @field_validator("username")
    @classmethod
    def validate_username_field(cls: Type["LoginRequest"], v: str) -> str:
        """Validate username format."""
        return validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password_field(cls: type, v: str, info) -> str:  # noqa: ANN001
        """Validate password strength and security requirements."""
        values = info.data if info else {}
        username = values.get("username")

        # Comprehensive password strength validation
        validation_result = validate_password_strength(password=v, username=username)

        if not validation_result.is_valid:
            # Combine all errors into a single message
            error_msg = "; ".join(validation_result.errors)
            raise ValueError(error_msg)

        return str(v)


class AuthResponse(BaseModel):
    """Enhanced authentication response."""

    access_token: str

    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    user_profile: UserInfo
    session_id: str
