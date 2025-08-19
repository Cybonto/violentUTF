# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Authentication models."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class User(BaseModel):
    """User model for authentication."""

    model_config = ConfigDict(extra="forbid")  # Prevent extra fields from JWT
    username: str
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    is_active: bool = True

    @property
    def is_authenticated(self: "User") -> bool:
        return True

    def has_role(self: "User", role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_permission(self: "User", permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def has_any_role(self: "User", roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def has_all_roles(self: "User", roles: List[str]) -> bool:
        """Check if user has all of the specified roles."""
        return all(role in self.roles for role in roles)

    def __str__(self: "User") -> str:
        """Return string representation of user - ALWAYS use username."""
        return self.username

    def __repr__(self: "User") -> str:
        """Developer-friendly representation."""
        return f"User(username='{self.username}', roles={self.roles})"
