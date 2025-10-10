# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Database connection utilities for performance optimization."""

from __future__ import annotations

import os
import sqlite3
from typing import Optional

# duckdb removed - PyRIT migrated to SQLite in v0.10.0rc0 (see issue #269)


class DatabaseConnection:
    """Manage database connections for performance tools."""

    def __init__(self: DatabaseConnection, db_path: str, db_type: str = "sqlite") -> None:
        """Initialize database connection.

        Args:
            db_path: Path to database file
            db_type: Type of database (sqlite, postgres)
        """
        self.db_path = db_path
        self.db_type = db_type.lower()
        self.connection: Optional[sqlite3.Connection] = None

    def connect(self: DatabaseConnection) -> sqlite3.Connection:
        """Establish database connection.

        Returns:
            Database connection object

        Raises:
            FileNotFoundError: If database file doesn't exist
            ValueError: If database type is unsupported
        """
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        if self.db_type == "sqlite":
            self.connection = sqlite3.connect(self.db_path)
        elif self.db_type == "postgres":
            # PostgreSQL support would require psycopg2/asyncpg
            # Currently focused on SQLite per PyRIT migration (issue #269)
            raise ValueError("PostgreSQL support not implemented yet")
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

        return self.connection

    def disconnect(self: DatabaseConnection) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute(self: DatabaseConnection, query: str, params: Optional[tuple] = None) -> sqlite3.Cursor:
        """Execute a query.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Query result
        """
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()  # type: ignore[union-attr]
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        return cursor

    def fetchall(self: DatabaseConnection, query: str, params: Optional[tuple] = None) -> list:
        """Execute query and fetch all results.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            List of result rows
        """
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def fetchone(self: DatabaseConnection, query: str, params: Optional[tuple] = None) -> Optional[tuple]:
        """Execute query and fetch one result.

        Args:
            query: SQL query to execute
            params: Query parameters

        Returns:
            Single result row or None
        """
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def __enter__(self: DatabaseConnection) -> DatabaseConnection:
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(
        self: DatabaseConnection, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Optional[type]
    ) -> None:
        """Context manager exit."""
        self.disconnect()


def get_connection(db_path: str, db_type: str = "sqlite") -> DatabaseConnection:
    """Get database connection.

    Args:
        db_path: Path to database file
        db_type: Type of database

    Returns:
        DatabaseConnection instance
    """
    return DatabaseConnection(db_path, db_type)
