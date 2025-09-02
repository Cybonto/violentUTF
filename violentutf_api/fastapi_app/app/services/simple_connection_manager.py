# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Simple Connection Manager for Database Access
Provides basic connection pooling to prevent database lock conflicts
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SimpleConnectionManager:
    """
    Simple connection manager that prevents concurrent database access issues

    This is a basic implementation for Phase 1 that provides:
    - Single connection per database file
    - Async locks to prevent concurrent access
    - Proper cleanup on errors
    """

    def __init__(self):
        self._connections: Dict[str, Any] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock(self, db_path: str) -> asyncio.Lock:
        """Get or create a lock for a specific database path"""
        async with self._global_lock:
            if db_path not in self._locks:
                self._locks[db_path] = asyncio.Lock()
            return self._locks[db_path]

    @asynccontextmanager
    async def get_connection(self, db_path: str):
        """
        Get a database connection with proper locking

        Args:
            db_path: Full path to the database file

        Yields:
            DuckDBMemory: Database connection instance
        """
        # Get the lock for this database path
        lock = await self._get_lock(db_path)

        async with lock:
            try:
                # Check if we already have a connection
                if db_path not in self._connections:
                    from pyrit.memory import DuckDBMemory

                    self._connections[db_path] = DuckDBMemory(db_path=db_path)
                    logger.debug(f"Created new database connection for {db_path}")

                yield self._connections[db_path]

            except Exception as e:
                logger.error(f"Database connection error for {db_path}: {e}")
                # Remove the failed connection so it can be recreated
                if db_path in self._connections:
                    del self._connections[db_path]
                raise

    def get_connection_sync(self, db_path: str):
        """
        Get a database connection synchronously (for legacy code)

        Args:
            db_path: Full path to the database file

        Returns:
            DuckDBMemory: Database connection instance
        """
        try:
            if db_path not in self._connections:
                from pyrit.memory import DuckDBMemory

                self._connections[db_path] = DuckDBMemory(db_path=db_path)
                logger.debug(f"Created new sync database connection for {db_path}")

            return self._connections[db_path]
        except Exception as e:
            logger.error(f"Sync database connection error for {db_path}: {e}")
            # Remove the failed connection so it can be recreated
            if db_path in self._connections:
                del self._connections[db_path]
            raise

    def close_connection(self, db_path: str):
        """
        Close a specific database connection

        Args:
            db_path: Full path to the database file
        """
        if db_path in self._connections:
            try:
                connection = self._connections[db_path]
                if hasattr(connection, "dispose_engine"):
                    connection.dispose_engine()
                logger.debug(f"Closed database connection for {db_path}")
            except Exception as e:
                logger.error(f"Error closing connection for {db_path}: {e}")
            finally:
                del self._connections[db_path]

    def close_all_connections(self):
        """Close all database connections"""
        for db_path in list(self._connections.keys()):
            self.close_connection(db_path)

        # Clear locks as well
        self._locks.clear()
        logger.info("All database connections closed")

    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about current connections

        Returns:
            dict: Connection statistics
        """
        return {
            "total_connections": len(self._connections),
            "active_locks": len(self._locks),
            "connection_paths": list(self._connections.keys()),
        }

    def __del__(self):
        """Cleanup on object destruction"""
        try:
            self.close_all_connections()
        except Exception:
            pass  # Ignore errors during cleanup


# Global instance for use across the application
simple_connection_manager = SimpleConnectionManager()


def get_simple_connection_manager() -> SimpleConnectionManager:
    """Get the global connection manager instance"""
    return simple_connection_manager
