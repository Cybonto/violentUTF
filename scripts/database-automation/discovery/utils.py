# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Common utilities for database discovery system."""

import hashlib
import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .exceptions import DiscoveryError, ValidationError
from .models import ConfidenceLevel, DatabaseType


def setup_logging(name: str = "discovery", level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """Set up structured logging for discovery operations."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def generate_database_id(database_type: DatabaseType, identifier: str) -> str:
    """Generate unique database ID from type and identifier."""
    combined = f"{database_type.value}:{identifier}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def calculate_confidence_score(
    detection_methods: List[str], validation_results: Dict[str, bool], consistency_score: float = 1.0
) -> Tuple[float, ConfidenceLevel]:
    """
    Calculate confidence score and level for discovery result.

    Args:
        detection_methods: List of methods that detected the database
        validation_results: Results of validation checks
        consistency_score: Score for cross-method consistency (0.0-1.0)

    Returns:
        Tuple of (confidence_score, confidence_level)
    """
    # Base score from number of detection methods
    method_score = min(len(detection_methods) * 0.25, 1.0)

    # Validation score
    if validation_results:
        validation_score = sum(validation_results.values()) / len(validation_results)
    else:
        validation_score = 0.5  # Neutral when no validation available

    # Combine scores
    confidence_score = method_score * 0.4 + validation_score * 0.4 + consistency_score * 0.2
    confidence_score = max(0.0, min(1.0, confidence_score))

    # Determine confidence level
    if confidence_score >= 0.9:
        confidence_level = ConfidenceLevel.HIGH
    elif confidence_score >= 0.7:
        confidence_level = ConfidenceLevel.MEDIUM
    elif confidence_score >= 0.5:
        confidence_level = ConfidenceLevel.LOW
    else:
        confidence_level = ConfidenceLevel.VERY_LOW

    return confidence_score, confidence_level


def validate_file_path(file_path: str) -> bool:
    """Validate if file path exists and is accessible."""
    try:
        path = Path(file_path)
        return path.exists() and path.is_file() and os.access(path, os.R_OK)
    except (OSError, PermissionError):
        return False


def detect_database_type_from_extension(file_path: str) -> DatabaseType:
    """Detect database type from file extension."""
    path = Path(file_path)
    extension = path.suffix.lower()

    if extension in [".db", ".sqlite", ".sqlite3"]:
        return DatabaseType.SQLITE
    elif extension == ".duckdb":
        return DatabaseType.DUCKDB
    else:
        return DatabaseType.UNKNOWN


def detect_database_type_from_content(file_path: str) -> DatabaseType:
    """Detect database type by examining file content."""
    try:
        path = Path(file_path)

        # Check file size (empty files are not databases)
        if path.stat().st_size == 0:
            return DatabaseType.UNKNOWN

        # Read first few bytes to check magic numbers
        with open(path, "rb") as f:
            header = f.read(16)

        # SQLite magic number
        if header.startswith(b"SQLite format 3\x00"):
            return DatabaseType.SQLITE

        # DuckDB magic number (simplified check)
        if b"DUCK" in header or b"duckdb" in header.lower():
            return DatabaseType.DUCKDB

        return DatabaseType.UNKNOWN

    except (OSError, IOError, PermissionError):
        return DatabaseType.UNKNOWN


def validate_sqlite_database(file_path: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate SQLite database and extract basic schema information.

    Returns:
        Tuple of (is_valid, schema_info)
    """
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()

        # Get table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        # Get database size
        cursor.execute("PRAGMA page_count;")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]
        size_bytes = page_count * page_size

        schema_info = {
            "tables": tables,
            "table_count": len(tables),
            "size_bytes": size_bytes,
            "is_empty": len(tables) == 0,
        }

        conn.close()
        return True, schema_info

    except sqlite3.Error:
        return False, None
    except Exception:
        return False, None


def parse_connection_string(connection_string: str) -> Optional[Dict[str, str]]:
    """Parse database connection string to extract components."""
    try:
        # PostgreSQL format: postgresql://user:password@host:port/database
        if connection_string.startswith("postgresql://"):
            parts = connection_string[13:].split("@")
            if len(parts) == 2:
                user_pass, host_db = parts
                user_info = user_pass.split(":")
                host_info = host_db.split("/")

                return {
                    "type": "postgresql",
                    "user": user_info[0] if user_info else None,
                    "password": user_info[1] if len(user_info) > 1 else None,
                    "host": host_info[0].split(":")[0] if host_info else None,
                    "port": host_info[0].split(":")[1] if ":" in host_info[0] else "5432",
                    "database": host_info[1] if len(host_info) > 1 else None,
                }

        # SQLite format: sqlite:///path/to/database.db
        elif connection_string.startswith("sqlite:///"):
            return {"type": "sqlite", "path": connection_string[10:]}

        return None

    except Exception:
        return None


def sanitize_for_logging(value: str) -> str:
    """Sanitize sensitive values for logging (remove passwords, etc.)."""
    # Replace common password patterns
    sanitized = value

    # Database connection strings
    if "://" in sanitized and "@" in sanitized:
        parts = sanitized.split("@")
        if len(parts) == 2:
            protocol_user = parts[0]
            if ":" in protocol_user:
                protocol, user = protocol_user.rsplit(":", 1)  # noqa: F841  # pylint: disable=unused-variable
                sanitized = f"{protocol}:***@{parts[1]}"

    # Environment variables with password/key/secret
    sensitive_patterns = ["password", "pass", "secret", "key", "token"]
    for pattern in sensitive_patterns:
        if pattern.lower() in value.lower():
            return "***REDACTED***"

    return sanitized


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """Load YAML configuration file with error handling."""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError as e:
        raise ValidationError(f"Configuration file not found: {config_path}") from e
    except yaml.YAMLError as e:
        raise ValidationError(f"Invalid YAML in configuration file: {e}") from e
    except Exception as e:
        raise DiscoveryError(f"Error loading configuration: {e}") from e


def measure_execution_time(func):  # noqa: ANN001 ANN201
    """Measure function execution time."""

    def wrapper(*args, **kwargs):  # noqa: ANN002 ANN003 ANN201
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            if hasattr(result, "__dict__"):
                result.execution_time = execution_time
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger = logging.getLogger("discovery")
            logger.error("Function %s failed after %.2fs: %s", func.__name__, execution_time, e)
            raise

    return wrapper


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def is_likely_test_file(file_path: str) -> bool:
    """Check if file is likely a test file that should be excluded."""
    path = Path(file_path)
    path_str = str(path).lower()

    test_indicators = [
        "/test/",
        "/tests/",
        "_test.",
        "test_",
        ".test.",
        "/mock/",
        "/fixtures/",
        "/samples/",
        "/examples/",
    ]

    return any(indicator in path_str for indicator in test_indicators)


def normalize_host(host: str) -> str:
    """Normalize host name for consistent comparison."""
    host = host.lower().strip()
    if host in ["localhost", "127.0.0.1", "0.0.0.0"]:
        return "localhost"
    return host


def create_report_directory(base_path: str = "reports") -> Path:
    """Create timestamped directory for discovery reports."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = Path(base_path) / f"discovery_{timestamp}"
    report_dir.mkdir(parents=True, exist_ok=True)
    return report_dir
