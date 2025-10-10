# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""API Key database model."""
from datetime import datetime
from typing import Self

from sqlalchemy import JSON, Boolean, Column, DateTime, String
from sqlalchemy.sql import func

from app.db.database import Base


class APIKey(Base):
    """API Key model for database storage."""

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True)  # Store hash of the key
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # pylint: disable=not-callable
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    def update_last_used(self: "Self") -> None:
        """Update last used timestamp.

        Note: This should be called within a SQLAlchemy session context.
        The actual timestamp update would be handled by the database.
        """
        # This is a placeholder - actual implementation would use database session
        # Example: session.query(APIKey).filter(APIKey.id == self.id).update({"last_used_at": func.now()})
        return None

    def is_expired(self: "Self") -> bool:
        """Check if key is expired."""
        if not self.expires_at:

            return False
        # Handle SQLAlchemy comparison properly
        return bool(datetime.utcnow() > self.expires_at)

    def to_dict(self: "Self") -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": (self.last_used_at.isoformat() if self.last_used_at else None),
            "is_active": self.is_active,
        }
