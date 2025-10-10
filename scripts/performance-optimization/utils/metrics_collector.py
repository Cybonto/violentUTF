# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Metrics collection utilities for performance optimization."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from .db_connections import DatabaseConnection


class MetricsCollector:
    """Collect performance metrics from databases."""

    def __init__(self: MetricsCollector) -> None:
        """Initialize metrics collector."""
        self.metrics: Dict[str, Any] = {}

    def collect_database_stats(self: MetricsCollector, db_path: str, db_type: str) -> Dict[str, Any]:
        """Collect basic database statistics.

        Args:
            db_path: Path to database file
            db_type: Type of database

        Returns:
            Dictionary of database statistics
        """
        stats = {
            "db_path": db_path,
            "db_type": db_type,
            "timestamp": time.time(),
        }

        # File size
        if os.path.exists(db_path):
            stats["file_size_bytes"] = os.path.getsize(db_path)
            stats["file_size_mb"] = stats["file_size_bytes"] / (1024 * 1024)

        # Database-specific stats
        with DatabaseConnection(db_path, db_type) as conn:
            stats["tables"] = self.get_table_list(conn)
            stats["row_counts"] = self._get_row_counts(conn, stats["tables"])

        return stats

    def get_table_list(self: MetricsCollector, conn: DatabaseConnection) -> List[str]:
        """Get list of tables in database.

        Args:
            conn: Database connection

        Returns:
            List of table names
        """
        if conn.db_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table'"
        # DuckDB support removed - PyRIT migrated to SQLite in v0.10.0rc0 (issue #269)
        else:
            return []

        results = conn.fetchall(query)
        return [row[0] for row in results]

    def _get_row_counts(self: MetricsCollector, conn: DatabaseConnection, tables: List[str]) -> Dict[str, int]:
        """Get row counts for each table.

        Args:
            conn: Database connection
            tables: List of table names

        Returns:
            Dictionary mapping table names to row counts
        """
        row_counts = {}

        for table in tables:
            try:
                # Use parameterized query to prevent SQL injection
                query = f'SELECT COUNT(*) FROM "{table}"'  # nosec B608
                result = conn.fetchone(query)
                row_counts[table] = result[0] if result else 0
            except Exception:
                row_counts[table] = 0

        return row_counts

    def measure_query_time(
        self: MetricsCollector,
        conn: DatabaseConnection,
        query: str,
        params: Optional[tuple] = None,
        iterations: int = 1,
    ) -> Dict[str, float]:
        """Measure query execution time.

        Args:
            conn: Database connection
            query: SQL query to measure
            params: Query parameters
            iterations: Number of times to run query

        Returns:
            Dictionary with timing metrics
        """
        times = []

        for _ in range(iterations):
            start_time = time.perf_counter()
            conn.execute(query, params)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)  # Convert to milliseconds

        return {
            "avg_time_ms": sum(times) / len(times),
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "total_time_ms": sum(times),
            "iterations": iterations,
        }

    def collect_index_stats(self: MetricsCollector, db_path: str, db_type: str) -> Dict[str, Any]:
        """Collect index statistics.

        Args:
            db_path: Path to database file
            db_type: Type of database

        Returns:
            Dictionary of index statistics
        """
        stats = {"indexes": []}

        with DatabaseConnection(db_path, db_type) as conn:
            if db_type == "sqlite":
                query = "SELECT name, tbl_name FROM sqlite_master WHERE type='index'"
                results = conn.fetchall(query)

                for row in results:
                    stats["indexes"].append({"name": row[0], "table": row[1]})

        return stats

    def collect_cache_stats(self: MetricsCollector, db_path: str, db_type: str) -> Dict[str, Any]:
        """Collect cache statistics.

        Args:
            db_path: Path to database file
            db_type: Type of database

        Returns:
            Dictionary of cache statistics
        """
        stats = {}

        with DatabaseConnection(db_path, db_type) as conn:
            if db_type == "sqlite":
                # Get cache size
                result = conn.fetchone("PRAGMA cache_size")
                if result:
                    stats["cache_size"] = result[0]

                # Get page count
                result = conn.fetchone("PRAGMA page_count")
                if result:
                    stats["page_count"] = result[0]

                # Get page size
                result = conn.fetchone("PRAGMA page_size")
                if result:
                    stats["page_size"] = result[0]

        return stats
