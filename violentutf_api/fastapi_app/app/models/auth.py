# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Authentication models."""

from typing import List, Optional, Self

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """Provide User model for authentication."""

    model_config = ConfigDict(extra="forbid")  # Prevent extra fields from JWT

    username: str
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True

    @property
    def is_authenticated(self: "Self") -> bool:
        """Check if authenticated."""
        return True

    def has_role(self: "Self", role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_permission(self: "Self", permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def has_any_role(self: "Self", roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def has_all_roles(self: "Self", roles: List[str]) -> bool:
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in roles)

    def __str__(self: "Self") -> str:
        """Return string representation of user - ALWAYS use username."""
        return self.username

    def __repr__(self: "Self") -> str:
        """Return developer-friendly representation."""
        return f"User(username='{self.username}', roles={self.roles})"
