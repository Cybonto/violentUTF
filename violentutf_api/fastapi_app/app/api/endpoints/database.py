# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Database management endpoints for PyRIT Memory (DuckDB) operations."""

import hashlib
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

import duckdb
from app.core.auth import get_current_user
from app.models.auth import User
from app.schemas.database import (
    DatabaseInitResponse,
    DatabaseStatsResponse,
    DatabaseStatusResponse,
    InitializeDatabaseRequest,
    ResetDatabaseRequest,
    TableStats,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

logger = logging.getLogger(__name__)
router = APIRouter()


def get_db_filename(username: str, salt: str) -> str:
    """Generate database filename based on salted hash of username."""
    if not username or not salt:
        return ""
    salt_bytes = salt.encode("utf-8") if isinstance(salt, str) else salt
    hashed_username = hashlib.sha256(salt_bytes + username.encode("utf-8")).hexdigest()
    return f"pyrit_memory_{hashed_username}.db"


def get_db_path(username: str, salt: str, app_data_dir: str) -> str:
    """Construct full path for user's database file."""
    if not app_data_dir:
        return ""
    filename = get_db_filename(username, salt)
    if not filename:
        return ""
    return os.path.join(app_data_dir, filename)


# Security: Allowed table names for counting operations to prevent SQL injection
ALLOWED_PYRIT_TABLES = {
    "prompt_pieces",
    "conversations",
    "scores",
    "datasets",
    "generators",
    "scorers",
    "orchestrator_executions",
    "orchestrator_results",
}


def get_secure_table_count(conn, table_name: str) -> int:
    """Get row count for table with name validation to prevent SQL injection."""
    if table_name not in ALLOWED_PYRIT_TABLES:
        raise ValueError(f"Invalid table name: {table_name}")

    # Use string formatting with pre-validated table name (table_name is whitelisted above)
    query = 'SELECT COUNT(*) FROM "{}"'.format(table_name)  # nosec B608
    result = conn.execute(query).fetchone()
    return result[0] if result else 0


@router.post("/initialize", response_model=DatabaseInitResponse)
async def initialize_database(
    request: InitializeDatabaseRequest, current_user: User = Depends(get_current_user)
) -> Any:
    """Initialize user-specific PyRIT DuckDB database using salted hash-based path generation."""
    try:
        # Get configuration
        salt = request.custom_salt or os.getenv("PYRIT_DB_SALT", "default_salt_2025")
        app_data_dir = os.getenv("APP_DATA_DIR", "./app_data/violentutf")

        # Generate database path
        db_path = get_db_path(current_user.username, salt, app_data_dir)
        if not db_path:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not generate database path"
            )

        db_filename = os.path.basename(db_path)

        # Create directory if needed
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)

        # Check if database already exists
        if os.path.exists(db_path) and not request.force_recreate:
            return DatabaseInitResponse(
                database_path=db_path,
                database_filename=db_filename,
                initialization_status="already_exists",
                path_generation_method="SHA256 salted hash",
                salt_hash_preview=hashlib.sha256(salt.encode()).hexdigest()[:8],
                schema_version="1.0",
            )

        # Backup existing database if requested
        if os.path.exists(db_path) and request.backup_existing:
            backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(db_path, backup_path)

        # Initialize database
        with duckdb.connect(db_path) as conn:
            # Create basic PyRIT schema
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prompt_pieces (

                    id INTEGER PRIMARY KEY,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (

                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scores (

                    id INTEGER PRIMARY KEY,
                    prompt_piece_id INTEGER,
                    scorer_name TEXT,
                    score_value REAL,
                    score_metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prompt_piece_id) REFERENCES prompt_pieces(id)
                )
            """
            )

        return DatabaseInitResponse(
            database_path=db_path,
            database_filename=db_filename,
            initialization_status="success",
            path_generation_method="SHA256 salted hash",
            salt_hash_preview=hashlib.sha256(salt.encode()).hexdigest()[:8],
            schema_version="1.0",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database initialization failed: {str(e)}"
        )


@router.get("/status", response_model=DatabaseStatusResponse)
async def get_database_status(current_user: User = Depends(get_current_user)) -> Any:
    """Check database initialization status and health."""
    try:
        salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
        app_data_dir = os.getenv("APP_DATA_DIR", "./app_data/violentutf")
        db_path = get_db_path(current_user.username, salt, app_data_dir)

        if not os.path.exists(db_path):
            return DatabaseStatusResponse(
                is_initialized=False,
                database_path=db_path,
                connection_healthy=False,
                schema_version="N/A",
                last_accessed=None,
                file_size_mb=None,
            )

        # Test connection
        try:
            with duckdb.connect(db_path) as conn:
                conn.execute("SELECT 1").fetchone()
                connection_healthy = True
        except Exception:
            connection_healthy = False

        # Get file stats
        stat = os.stat(db_path)
        file_size_mb = stat.st_size / (1024 * 1024)
        last_accessed = datetime.fromtimestamp(stat.st_atime)

        return DatabaseStatusResponse(
            is_initialized=True,
            database_path=db_path,
            connection_healthy=connection_healthy,
            schema_version="1.0",
            last_accessed=last_accessed,
            file_size_mb=round(file_size_mb, 2),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error checking database status: {str(e)}"
        )


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats(current_user: User = Depends(get_current_user)) -> Any:
    """Get comprehensive database statistics and table information."""
    try:
        salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
        app_data_dir = os.getenv("APP_DATA_DIR", "./app_data/violentutf")
        db_path = get_db_path(current_user.username, salt, app_data_dir)

        if not os.path.exists(db_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Database not found. Please initialize first."
            )

        tables = []
        total_records = 0

        with duckdb.connect(db_path) as conn:
            # Get table information
            table_names = ["prompt_pieces", "conversations", "scores"]

            for table_name in table_names:
                try:
                    # Use secure helper method to prevent SQL injection
                    count = get_secure_table_count(conn, table_name)
                    total_records += count

                    tables.append(TableStats(table_name=table_name, row_count=count))
                except ValueError as e:
                    # Invalid table name
                    logger.warning(f"Invalid table name in database stats: {e}")
                    tables.append(TableStats(table_name=table_name, row_count=0))
                except Exception:
                    # Table might not exist
                    tables.append(TableStats(table_name=table_name, row_count=0))

        # Get file size
        stat = os.stat(db_path)
        file_size_mb = stat.st_size / (1024 * 1024)

        return DatabaseStatsResponse(
            tables=tables,
            total_records=total_records,
            database_size_mb=round(file_size_mb, 2),
            last_backup=None,  # TODO: Implement backup tracking
            health_status="healthy" if total_records >= 0 else "error",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting database stats: {str(e)}"
        )


async def reset_database_task(db_path: str, preserve_user_data: bool = False) -> None:
    """Background task to reset database."""
    try:
        with duckdb.connect(db_path) as conn:
            if not preserve_user_data:
                # Drop all tables
                conn.execute("DROP TABLE IF EXISTS scores")
                conn.execute("DROP TABLE IF EXISTS prompt_pieces")
                conn.execute("DROP TABLE IF EXISTS conversations")
            else:
                # Just clear data but keep structure
                conn.execute("DELETE FROM scores")
                conn.execute("DELETE FROM prompt_pieces")
                conn.execute("DELETE FROM conversations")

            # Recreate schema
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS prompt_pieces (

                    id INTEGER PRIMARY KEY,
                    conversation_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (

                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scores (

                    id INTEGER PRIMARY KEY,
                    prompt_piece_id INTEGER,
                    scorer_name TEXT,
                    score_value REAL,
                    score_metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (prompt_piece_id) REFERENCES prompt_pieces(id)
                )
            """
            )
    except Exception as e:
        logger.error(f"Error in reset_database_task: {e}")


@router.post("/reset")
async def reset_database(
    request: ResetDatabaseRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)
) -> Any:
    """
    Reset database tables (drops and recreates schema). Requires confirmation.
    """
    if not request.confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Database reset requires explicit confirmation"
        )

    try:
        salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
        app_data_dir = os.getenv("APP_DATA_DIR", "./app_data/violentutf")
        db_path = get_db_path(current_user.username, salt, app_data_dir)

        if not os.path.exists(db_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database not found. Nothing to reset.")

        # Create backup if requested
        if request.backup_before_reset:
            backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil

            shutil.copy2(db_path, backup_path)

        # Schedule reset task
        background_tasks.add_task(reset_database_task, db_path, request.preserve_user_data)

        return {"message": "Database reset initiated", "task_status": "running"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error resetting database: {str(e)}"
        )


@router.post("/backup")
async def backup_database(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)) -> Any:
    """Create database backup."""
    try:
        salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
        app_data_dir = os.getenv("APP_DATA_DIR", "./app_data/violentutf")
        db_path = get_db_path(current_user.username, salt, app_data_dir)

        if not os.path.exists(db_path):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Database not found. Nothing to backup.")

        # Create backup
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        def backup_task() -> None:
            import shutil

            shutil.copy2(db_path, backup_path)

        background_tasks.add_task(backup_task)

        return {"message": "Database backup initiated", "backup_path": backup_path, "task_status": "running"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error creating backup: {str(e)}"
        )
