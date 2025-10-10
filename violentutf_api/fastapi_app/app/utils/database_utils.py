# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Database utility functions for consistent database path management

Fixes the database switching issue by ensuring all services use the same user-specific paths
"""

import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def get_user_memory_path(user_id: str, salt: Optional[str] = None) -> str:
    """
    Get consistent database path for a user across all services

    This function ensures that all parts of the application use the same database file
    for a given user, preventing the database switching issue.

    Args:
        user_id: The user identifier (canonical username)
        salt: Optional salt for hashing (defaults to environment variable)

    Returns:
        str: Full path to the user's database file

    Example:
        >>> get_user_memory_path("violentutf.web")
        '/app/app_data/violentutf/pyrit_memory_a1b2c3d4e5f6g7h8.db'
    """
    if not user_id:
        logger.warning("Empty user_id provided to get_user_memory_path, using default")
        user_id = "violentutf.web"

    # Use consistent salt from environment
    if salt is None:
        salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")

    # Generate consistent hash (same logic as existing systems)
    combined = f"{salt}{user_id}"
    user_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    # Use consistent memory directory
    memory_dir = os.getenv("APP_DATA_DIR", "/app/app_data/violentutf")
    os.makedirs(memory_dir, exist_ok=True)

    # Create consistent filename
    db_filename = f"pyrit_memory_{user_hash}.db"
    db_path = os.path.join(memory_dir, db_filename)

    logger.debug("Generated database path for user '%s': %s", user_id, db_path)
    return db_path


def get_memory_directory() -> str:
    """
    Get the memory directory path where database files are stored

    Returns:
        str: Path to the memory directory
    """
    memory_dir = os.getenv("APP_DATA_DIR", "/app/app_data/violentutf")
    os.makedirs(memory_dir, exist_ok=True)
    return memory_dir


def validate_user_database_path(user_id: str, db_path: str) -> bool:
    """
    Validate that a database path is correct for a given user

    Args:
        user_id: The user identifier
        db_path: The database path to validate

    Returns:
        bool: True if the path is correct for the user
    """
    expected_path = get_user_memory_path(user_id)
    return db_path == expected_path


def list_user_database_files(memory_dir: Optional[str] = None) -> list:
    """
    List all PyRIT memory database files in the memory directory

    Args:
        memory_dir: Optional memory directory (defaults to configured directory)

    Returns:
        list: List of database file paths
    """
    if memory_dir is None:
        memory_dir = get_memory_directory()

    try:
        files = []
        for filename in os.listdir(memory_dir):
            if filename.startswith("pyrit_memory_") and filename.endswith(".db"):
                files.append(os.path.join(memory_dir, filename))
        return files
    except OSError as e:
        logger.error("Error listing database files in %s: %s", memory_dir, e)
        return []


def cleanup_orphaned_orchestrator_databases(memory_dir: Optional[str] = None) -> int:
    """
    Clean up orphaned orchestrator database files (from the old buggy system)

    These are database files created with the pattern orchestrator_memory_*.db
    that should no longer be used after the fix.

    Args:
        memory_dir: Optional memory directory (defaults to configured directory)

    Returns:
        int: Number of files cleaned up
    """
    if memory_dir is None:
        memory_dir = get_memory_directory()

    cleaned_count = 0
    try:
        for filename in os.listdir(memory_dir):
            if filename.startswith("orchestrator_memory_") and filename.endswith(".db"):
                file_path = os.path.join(memory_dir, filename)
                try:
                    os.remove(file_path)
                    cleaned_count += 1
                    logger.info("Cleaned up orphaned orchestrator database: %s", filename)
                except OSError as e:
                    logger.error("Failed to remove %s: %s", filename, e)
    except OSError as e:
        logger.error("Error accessing memory directory %s: %s", memory_dir, e)

    return cleaned_count
