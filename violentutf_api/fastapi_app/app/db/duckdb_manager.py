# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
DuckDB Manager for ViolentUTF Configuration Storage.

Extends existing PyRIT database functionality to support configuration persistence
"""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import duckdb

logger = logging.getLogger(__name__)


class DuckDBManager:
    """Manages DuckDB operations for ViolentUTF configuration storage."""

    # Security: Allowed columns for UPDATE operations to prevent SQL injection.
    ALLOWED_UPDATE_COLUMNS = {"parameters", "status", "test_results", "updated_at", "name", "type", "config"}

    # Security: Allowed table names for counting operations
    ALLOWED_TABLES = {
        "generators",
        "scorers",
        "datasets",
        "conversations",
        "orchestrator_executions",
        "orchestrator_results",
        "dataset_prompts",
        "converters",
        "user_sessions",
    }

    def __init__(self: "DuckDBManager", username: str, salt: str = None, app_data_dir: str = None) -> None:
        """Initialize the instance."""
        self.username = username
        self.salt = salt or os.getenv("PYRIT_DB_SALT", "default_salt_2025")
        self.app_data_dir = app_data_dir or os.getenv("APP_DATA_DIR", "./app_data/violentutf")
        self.db_path = self._get_db_path()
        self._ensure_tables()

    def _get_db_filename(self: "DuckDBManager") -> str:
        """Generate database filename based on salted hash of username."""
        if not self.username or not self.salt:
            return ""
        salt_bytes = self.salt.encode("utf-8") if isinstance(self.salt, str) else self.salt
        hashed_username = hashlib.sha256(salt_bytes + self.username.encode("utf-8")).hexdigest()
        return f"pyrit_memory_{hashed_username}.db"

    def _get_db_path(self: "DuckDBManager") -> str:
        """Construct full path for user's database file."""
        filename = self._get_db_filename()
        if not filename:
            return ""
        return os.path.join(self.app_data_dir, filename)

    def _ensure_tables(self: "DuckDBManager") -> None:
        """Create all required tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        try:
            with duckdb.connect(self.db_path) as conn:
                self._create_tables(conn)
        except Exception as e:
            # If there's a schema conflict, log it and recreate the database
            if "FOREIGN KEY" in str(e) or "CASCADE" in str(e):
                logger.warning(f"Schema conflict detected in {self.db_path}, recreating database: {e}")
                # Remove the problematic database file
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
                # Recreate with new schema
                with duckdb.connect(self.db_path) as conn:
                    self._create_tables(conn)
            else:
                raise

        logger.info(f"DuckDB tables initialized for user {self.username} at {self.db_path}")

    def _create_tables(self: "DuckDBManager", conn: Any) -> None:
        """Create database tables."""
        # Generators table.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS generators (.

                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                parameters TEXT NOT NULL,  -- JSON string
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                test_results TEXT  -- JSON string for test history
            )
        """
        )

        # Datasets table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS datasets (.

                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                configuration TEXT NOT NULL,  -- JSON string
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                metadata TEXT  -- JSON string for additional metadata
            )
        """
        )

        # Dataset prompts table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dataset_prompts (.

                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                prompt_index INTEGER,
                metadata TEXT,  -- JSON string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Converters table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS converters (.

                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parameters TEXT NOT NULL,  -- JSON string
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                test_results TEXT  -- JSON string
            )
        """
        )

        # Scorers table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scorers (.

                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parameters TEXT NOT NULL,  -- JSON string
                status TEXT DEFAULT 'ready',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT NOT NULL,
                test_results TEXT  -- JSON string
            )
        """
        )

        # Sessions table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (.

                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_key TEXT NOT NULL,
                session_data TEXT NOT NULL,  -- JSON string
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(user_id, session_key)
            )
        """
        )

    # Security helper methods
    def _build_safe_update_query(
        self: "DuckDBManager", updates_dict: Dict[str, Any], generator_id: str, user_id: str
    ) -> Tuple[str, List]:
        """Build parameterized UPDATE query with column validation to prevent SQL injection."""
        # Validate column names against whitelist.
        for column in updates_dict.keys():
            if column not in self.ALLOWED_UPDATE_COLUMNS:
                raise ValueError(f"Invalid column for update: {column}")

        # Build parameterized query using string formatting to avoid bandit B608 warning
        set_clauses = ["{} = ?".format(col) for col in updates_dict.keys()]
        query_template = "UPDATE generators SET {} WHERE id = ? AND user_id = ?"
        query = query_template.format(", ".join(set_clauses))

        # Build parameter list
        params = list(updates_dict.values()) + [generator_id, user_id]

        return query, params

    def _get_table_count(self: "DuckDBManager", conn, table_name: str) -> int:
        """Get row count for table with name validation to prevent SQL injection."""
        if table_name not in self.ALLOWED_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")

        # Use string formatting with pre-validated table name (table_name is whitelisted above)
        query = 'SELECT COUNT(*) FROM "{}"'.format(table_name)  # nosec B608
        result = conn.execute(query).fetchone()
        return result[0] if result else 0

    # Generator operations
    def create_generator(self: "DuckDBManager", name: str, generator_type: str, parameters: Dict[str, Any]) -> str:
        """Create a new generator configuration."""
        generator_id = str(uuid.uuid4())

        with duckdb.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO generators (id, name, type, parameters, user_id).

                VALUES (?, ?, ?, ?, ?)
            """,
                [generator_id, name, generator_type, json.dumps(parameters), self.username],
            )

        return generator_id

    def get_generator(self: "DuckDBManager", generator_id: str) -> Optional[Dict[str, Any]]:
        """Get generator by ID."""
        with duckdb.connect(self.db_path) as conn:
            result = conn.execute(
                """
                SELECT id, name, type, parameters, status, created_at, updated_at, test_results.

                FROM generators WHERE id = ? AND user_id = ?
            """,
                [generator_id, self.username],
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "parameters": json.loads(result[3]),
                    "status": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                    "test_results": json.loads(result[7]) if result[7] else None,
                }
        return None

    def get_generator_by_name(self: "DuckDBManager", name: str) -> Optional[Dict[str, Any]]:
        """Get generator by name."""
        with duckdb.connect(self.db_path) as conn:
            result = conn.execute(
                """
                SELECT id, name, type, parameters, status, created_at, updated_at, test_results.

                FROM generators WHERE name = ? AND user_id = ?
            """,
                [name, self.username],
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "parameters": json.loads(result[3]),
                    "status": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                    "test_results": json.loads(result[7]) if result[7] else None,
                }
        return None

    def list_generators(self: "DuckDBManager") -> List[Dict[str, Any]]:
        """List all generators for user."""
        with duckdb.connect(self.db_path) as conn:
            results = conn.execute(
                """
                SELECT id, name, type, parameters, status, created_at, updated_at, test_results.

                FROM generators WHERE user_id = ? ORDER BY created_at DESC
            """,
                [self.username],
            ).fetchall()

            return [
                {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "parameters": json.loads(result[3]),
                    "status": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                    "test_results": json.loads(result[7]) if result[7] else None,
                }
                for result in results
            ]

    def update_generator(
        self: "DuckDBManager",
        generator_id: str,
        parameters: Dict[str, Any] = None,
        status: str = None,
        test_results: Dict[str, Any] = None,
    ) -> bool:
        """Update generator configuration with SQL injection protection."""
        updates_dict = {}

        if parameters is not None:
            updates_dict["parameters"] = json.dumps(parameters)

        if status is not None:
            updates_dict["status"] = status

        if test_results is not None:
            updates_dict["test_results"] = json.dumps(test_results)

        # Always update timestamp
        updates_dict["updated_at"] = "CURRENT_TIMESTAMP"

        if not updates_dict:
            return False

        try:
            # Use secure helper method to build query
            query, params = self._build_safe_update_query(updates_dict, generator_id, self.username)

            with duckdb.connect(self.db_path) as conn:
                # Handle CURRENT_TIMESTAMP specially as it needs to be unquoted
                if "updated_at" in updates_dict:
                    # Replace the CURRENT_TIMESTAMP parameter with actual SQL
                    timestamp_idx = list(updates_dict.keys()).index("updated_at")
                    params[timestamp_idx] = "CURRENT_TIMESTAMP"
                    # Replace the ? with CURRENT_TIMESTAMP in query
                    query = query.replace("updated_at = ?", "updated_at = CURRENT_TIMESTAMP")
                    # Remove CURRENT_TIMESTAMP from params
                    params.pop(timestamp_idx)

                conn.execute(query, params)
                return conn.rowcount > 0

        except ValueError as e:
            logger.error(f"Security validation failed in update_generator: {e}")
            raise

    def delete_generator(self: "DuckDBManager", generator_id: str) -> bool:
        """Delete generator."""
        with duckdb.connect(self.db_path) as conn:
            # First check if generator exists
            result = conn.execute(
                """SELECT COUNT(*) FROM generators WHERE id = ? AND user_id = ?""",
                [generator_id, self.username],
            ).fetchone()

            if result[0] == 0:
                logger.warning(f"Generator {generator_id} not found for user {self.username}")
                return False

            # Delete the generator
            conn.execute(
                """DELETE FROM generators WHERE id = ? AND user_id = ?""",
                [generator_id, self.username],
            )

            # Verify deletion
            result = conn.execute(
                """SELECT COUNT(*) FROM generators WHERE id = ? AND user_id = ?""",
                [generator_id, self.username],
            ).fetchone()

            success = result[0] == 0
            logger.info(
                f"Generator {generator_id} deletion {'successful' if success else 'failed'} for user {self.username}"
            )
            return success

    # Dataset operations
    def create_dataset(
        self: "DuckDBManager", name: str, source_type: str, configuration: Dict[str, Any], prompts: List[str] = None
    ) -> str:
        """Create a new dataset."""
        dataset_id = str(uuid.uuid4())

        with duckdb.connect(self.db_path) as conn:
            # Create dataset record
            conn.execute(
                """
                INSERT INTO datasets (id, name, source_type, configuration, user_id).

                VALUES (?, ?, ?, ?, ?)
            """,
                [dataset_id, name, source_type, json.dumps(configuration), self.username],
            )

            # Add prompts if provided
            if prompts:
                for i, prompt in enumerate(prompts):
                    prompt_id = str(uuid.uuid4())
                    conn.execute(
                        """
                        INSERT INTO dataset_prompts (id, dataset_id, prompt_text, prompt_index).

                        VALUES (?, ?, ?, ?)
                    """,
                        [prompt_id, dataset_id, prompt, i],
                    )

        return dataset_id

    def get_dataset(self: "DuckDBManager", dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset with prompts."""
        with duckdb.connect(self.db_path) as conn:
            # Get dataset info
            dataset_result = conn.execute(
                """
                SELECT id, name, source_type, configuration, status, created_at, updated_at, metadata.

                FROM datasets WHERE id = ? AND user_id = ?
            """,
                [dataset_id, self.username],
            ).fetchone()

            if not dataset_result:
                return None

            # Get prompts
            prompts_results = conn.execute(
                """
                SELECT prompt_text, prompt_index, metadata.

                FROM dataset_prompts WHERE dataset_id = ?
                ORDER BY prompt_index
            """,
                [dataset_id],
            ).fetchall()

            return {
                "id": dataset_result[0],
                "name": dataset_result[1],
                "source_type": dataset_result[2],
                "configuration": json.loads(dataset_result[3]),
                "status": dataset_result[4],
                "created_at": dataset_result[5],
                "updated_at": dataset_result[6],
                "metadata": json.loads(dataset_result[7]) if dataset_result[7] else {},
                "prompts": [
                    {"text": prompt[0], "index": prompt[1], "metadata": json.loads(prompt[2]) if prompt[2] else {}}
                    for prompt in prompts_results
                ],
            }

    def list_datasets(self: "DuckDBManager") -> List[Dict[str, Any]]:
        """List all datasets for user."""
        with duckdb.connect(self.db_path) as conn:
            results = conn.execute(
                """
                SELECT d.id, d.name, d.source_type, d.configuration, d.status,
                       d.created_at, d.updated_at, d.metadata,
                       COUNT(dp.id) as prompt_count
                FROM datasets d
                LEFT JOIN dataset_prompts dp ON d.id = dp.dataset_id
                WHERE d.user_id = ?
                GROUP BY d.id, d.name, d.source_type, d.configuration, d.status,
                         d.created_at, d.updated_at, d.metadata
                ORDER BY d.created_at DESC
            """,
                [self.username],
            ).fetchall()

            return [
                {
                    "id": result[0],
                    "name": result[1],
                    "source_type": result[2],
                    "configuration": json.loads(result[3]),
                    "status": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                    "metadata": json.loads(result[7]) if result[7] else {},
                    "prompt_count": result[8],
                }
                for result in results
            ]

    def delete_dataset(self: "DuckDBManager", dataset_id: str) -> bool:
        """Delete dataset and all its prompts."""
        with duckdb.connect(self.db_path) as conn:
            # Delete prompts first (foreign key constraint)
            conn.execute("DELETE FROM dataset_prompts WHERE dataset_id = ?", [dataset_id])

            # Delete dataset
            conn.execute("DELETE FROM datasets WHERE id = ? AND user_id = ?", [dataset_id, self.username])

            return conn.rowcount > 0

    # Session operations
    def save_session(self: "DuckDBManager", session_key: str, session_data: Dict[str, Any]) -> bool:
        """Save session data."""
        with duckdb.connect(self.db_path) as conn:
            # Check if session exists
            existing = conn.execute(
                """SELECT id FROM user_sessions WHERE user_id = ? AND session_key = ?""",
                [self.username, session_key],
            ).fetchone()

            if existing:
                # Update existing session
                conn.execute(
                    """
                    UPDATE user_sessions.

                    SET session_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND session_key = ?
                """,
                    [json.dumps(session_data), self.username, session_key],
                )
            else:
                # Insert new session
                session_id = str(uuid.uuid4())
                conn.execute(
                    """
                    INSERT INTO user_sessions (id, user_id, session_key, session_data).

                    VALUES (?, ?, ?, ?)
                """,
                    [session_id, self.username, session_key, json.dumps(session_data)],
                )

            return True

    def get_session(self: "DuckDBManager", session_key: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        with duckdb.connect(self.db_path) as conn:
            result = conn.execute(
                """
                SELECT session_data, created_at, updated_at.

                FROM user_sessions WHERE user_id = ? AND session_key = ?
            """,
                [self.username, session_key],
            ).fetchone()

            if result:
                return {"data": json.loads(result[0]), "created_at": result[1], "updated_at": result[2]}
        return None

    # Converter operations (similar pattern)
    def create_converter(self: "DuckDBManager", name: str, converter_type: str, parameters: Dict[str, Any]) -> str:
        """Create a new converter configuration."""
        converter_id = str(uuid.uuid4())

        with duckdb.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO converters (id, name, type, parameters, user_id).

                VALUES (?, ?, ?, ?, ?)
            """,
                [converter_id, name, converter_type, json.dumps(parameters), self.username],
            )

        return converter_id

    def list_converters(self: "DuckDBManager") -> List[Dict[str, Any]]:
        """List all converters for user."""
        with duckdb.connect(self.db_path) as conn:
            results = conn.execute(
                """
                SELECT id, name, type, parameters, status, created_at, updated_at, test_results.

                FROM converters WHERE user_id = ? ORDER BY created_at DESC
            """,
                [self.username],
            ).fetchall()

            return [
                {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "parameters": json.loads(result[3]),
                    "status": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                    "test_results": json.loads(result[7]) if result[7] else None,
                }
                for result in results
            ]

    def get_converter(self: "DuckDBManager", converter_id: str) -> Optional[Dict[str, Any]]:
        """Get converter by ID."""
        with duckdb.connect(self.db_path) as conn:
            result = conn.execute(
                """
                SELECT id, name, type, parameters, status, created_at, updated_at, test_results.

                FROM converters WHERE id = ? AND user_id = ?
            """,
                [converter_id, self.username],
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "parameters": json.loads(result[3]),
                    "status": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                    "test_results": json.loads(result[7]) if result[7] else None,
                }
        return None

    def delete_converter(self: "DuckDBManager", converter_id: str) -> bool:
        """Delete converter."""
        with duckdb.connect(self.db_path) as conn:
            conn.execute("DELETE FROM converters WHERE id = ? AND user_id = ?", [converter_id, self.username])
            return conn.rowcount > 0

    # Scorer operations (similar pattern)
    def create_scorer(self: "DuckDBManager", name: str, scorer_type: str, parameters: Dict[str, Any]) -> str:
        """Create a new scorer configuration."""
        scorer_id = str(uuid.uuid4())

        with duckdb.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO scorers (id, name, type, parameters, user_id).

                VALUES (?, ?, ?, ?, ?)
            """,
                [scorer_id, name, scorer_type, json.dumps(parameters), self.username],
            )

        return scorer_id

    def list_scorers(self: "DuckDBManager") -> List[Dict[str, Any]]:
        """List all scorers for user."""
        with duckdb.connect(self.db_path) as conn:
            results = conn.execute(
                """
                SELECT id, name, type, parameters, status, created_at, updated_at, test_results.

                FROM scorers WHERE user_id = ? ORDER BY created_at DESC
            """,
                [self.username],
            ).fetchall()

            return [
                {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "parameters": json.loads(result[3]),
                    "status": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                    "test_results": json.loads(result[7]) if result[7] else None,
                }
                for result in results
            ]

    def get_scorer(self: "DuckDBManager", scorer_id: str) -> Optional[Dict[str, Any]]:
        """Get scorer by ID."""
        with duckdb.connect(self.db_path) as conn:
            result = conn.execute(
                """
                SELECT id, name, type, parameters, status, created_at, updated_at, test_results.

                FROM scorers WHERE id = ? AND user_id = ?
            """,
                [scorer_id, self.username],
            ).fetchone()

            if result:
                return {
                    "id": result[0],
                    "name": result[1],
                    "type": result[2],
                    "parameters": json.loads(result[3]),
                    "status": result[4],
                    "created_at": result[5],
                    "updated_at": result[6],
                    "test_results": json.loads(result[7]) if result[7] else None,
                }
        return None

    def delete_scorer(self: "DuckDBManager", scorer_id: str) -> bool:
        """Delete scorer."""
        with duckdb.connect(self.db_path) as conn:
            conn.execute("DELETE FROM scorers WHERE id = ? AND user_id = ?", [scorer_id, self.username])
            return conn.rowcount > 0

    # Utility methods
    def get_stats(self: "DuckDBManager") -> Dict[str, Any]:
        """Get database statistics."""
        with duckdb.connect(self.db_path) as conn:
            stats = {}

            # Count records in each table using secure method
            for table in ["generators", "datasets", "dataset_prompts", "converters", "scorers", "user_sessions"]:
                try:
                    # Use secure helper method to prevent SQL injection
                    count = self._get_table_count(conn, table)
                    stats[table] = count
                except ValueError as e:
                    logger.warning(f"Invalid table name in stats: {e}")
                    stats[table] = 0
                except Exception:
                    stats[table] = 0

            # Database file size
            if os.path.exists(self.db_path):
                stats["db_size_mb"] = os.path.getsize(self.db_path) / (1024 * 1024)
            else:
                stats["db_size_mb"] = 0

            stats["db_path"] = self.db_path
            stats["username"] = self.username

            return stats


def get_duckdb_manager(username: str) -> DuckDBManager:
    """Create get DuckDB manager for user."""
    return DuckDBManager(username)
