# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
PostgreSQL Metrics Collector for Issue #270

Collects comprehensive performance metrics from PostgreSQL databases including
connection pool status, query performance, database size, cache statistics,
and transaction rates.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import asyncpg


@dataclass
class PostgreSQLMetrics:
    """Container for PostgreSQL performance metrics"""

    timestamp: datetime
    connection_pool: Dict[str, Any]
    query_performance: Dict[str, Any]
    database_size: Dict[str, Any]
    cache: Dict[str, Any]
    transactions: Dict[str, Any]
    replication: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class PostgresMetricsCollector:
    """
    PostgreSQL metrics collector for database performance monitoring.

    Collects metrics from PostgreSQL system catalogs and statistics views
    without impacting database performance.
    """

    def __init__(self, connection_string: str) -> None:
        """
        Initialize PostgreSQL metrics collector.

        Args:
            connection_string: PostgreSQL connection string (postgresql://...)

        Raises:
            ValueError: If connection string is invalid
        """
        self._validate_connection_string(connection_string)
        self.connection_string = connection_string
        self._pool: Optional[asyncpg.Pool] = None

    def _validate_connection_string(self, connection_string: str) -> None:
        """Validate PostgreSQL connection string format"""
        try:
            result = urlparse(connection_string)
            if result.scheme not in ("postgresql", "postgres"):
                raise ValueError(f"Invalid scheme '{result.scheme}', expected 'postgresql' or 'postgres'")
        except Exception as e:
            raise ValueError(f"Invalid connection string: {e}") from e

    async def _get_connection(self) -> asyncpg.Connection:
        """
        Get a connection from the pool.

        Returns:
            asyncpg.Connection: Database connection
        """
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=5,
                command_timeout=10.0,
            )
        return await self._pool.acquire()

    async def _release_connection(self, conn: asyncpg.Connection) -> None:
        """Release connection back to the pool"""
        if self._pool:
            await self._pool.release(conn)

    async def collect_connection_pool_metrics(self) -> Dict[str, Any]:
        """
        Collect connection pool metrics.

        Returns:
            Dict with active, idle, waiting connections and pool usage percentage
        """
        conn = await self._get_connection()
        try:
            # Query pg_stat_activity for connection stats
            query = """
                SELECT
                    count(*) FILTER (WHERE state = 'active') as active,
                    count(*) FILTER (WHERE state = 'idle') as idle,
                    count(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting,
                    count(*) as total
                FROM pg_stat_activity
                WHERE datname = current_database();
            """
            row = await conn.fetchrow(query)

            active = row["active"] or 0
            idle = row["idle"] or 0
            waiting = row["waiting"] or 0
            total = row["total"] or 0

            pool_usage = (active / total * 100) if total > 0 else 0.0

            return {
                "active_connections": active,
                "idle_connections": idle,
                "waiting_connections": waiting,
                "total_connections": total,
                "pool_usage_percent": round(pool_usage, 2),
            }
        finally:
            await self._release_connection(conn)

    async def collect_query_performance_metrics(self) -> Dict[str, Any]:
        """
        Collect query performance metrics.

        Returns:
            Dict with average query time, total queries, slow query count
        """
        conn = await self._get_connection()
        try:
            # Query pg_stat_statements if available, otherwise use pg_stat_database
            query = """
                SELECT
                    COALESCE(AVG(mean_exec_time), 0) as avg_query_time_ms,
                    SUM(calls) as total_queries,
                    COUNT(*) FILTER (WHERE mean_exec_time > 500) as slow_queries_count
                FROM pg_stat_statements
                WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database());
            """

            try:
                row = await conn.fetchrow(query)
                if row and row["avg_query_time_ms"] is not None:
                    return {
                        "avg_query_time_ms": round(float(row["avg_query_time_ms"]), 2),
                        "total_queries": int(row["total_queries"] or 0),
                        "slow_queries_count": int(row["slow_queries_count"] or 0),
                    }
            except asyncpg.UndefinedTableError:
                # pg_stat_statements extension not available, use fallback
                pass

            # Fallback: use pg_stat_database
            fallback_query = """
                SELECT
                    (blks_read + blks_hit) as total_blocks,
                    xact_commit + xact_rollback as total_queries
                FROM pg_stat_database
                WHERE datname = current_database();
            """
            row = await conn.fetchrow(fallback_query)

            return {
                "avg_query_time_ms": 0.0,  # Not available without pg_stat_statements
                "total_queries": int(row["total_queries"] or 0),
                "slow_queries_count": 0,  # Not available without pg_stat_statements
            }
        finally:
            await self._release_connection(conn)

    async def collect_database_size_metrics(self) -> Dict[str, Any]:
        """
        Collect database size metrics.

        Returns:
            Dict with database, table, and index sizes in MB
        """
        conn = await self._get_connection()
        try:
            query = """
                SELECT
                    pg_database_size(current_database()) as database_size,
                    sum(pg_total_relation_size(schemaname||'.'||tablename)) as table_size,
                    sum(pg_indexes_size(schemaname||'.'||tablename)) as index_size
                FROM pg_tables
                WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
            """
            row = await conn.fetchrow(query)

            database_size_mb = (row["database_size"] or 0) / (1024 * 1024)
            table_size_mb = (row["table_size"] or 0) / (1024 * 1024)
            index_size_mb = (row["index_size"] or 0) / (1024 * 1024)

            return {
                "database_size_mb": round(database_size_mb, 2),
                "table_size_mb": round(table_size_mb, 2),
                "index_size_mb": round(index_size_mb, 2),
            }
        finally:
            await self._release_connection(conn)

    async def collect_cache_metrics(self) -> Dict[str, Any]:
        """
        Collect buffer cache metrics.

        Returns:
            Dict with cache hit ratio and buffer statistics
        """
        conn = await self._get_connection()
        try:
            query = """
                SELECT
                    sum(heap_blks_read) as heap_blks_read,
                    sum(heap_blks_hit) as heap_blks_hit
                FROM pg_statio_user_tables;
            """
            row = await conn.fetchrow(query)

            blks_read = row["heap_blks_read"] or 0
            blks_hit = row["heap_blks_hit"] or 0
            total_blks = blks_read + blks_hit

            cache_hit_ratio = (blks_hit / total_blks) if total_blks > 0 else 0.0

            return {
                "cache_hit_ratio": round(cache_hit_ratio, 4),
                "buffer_cache_hits": blks_hit,
                "buffer_cache_reads": blks_read,
            }
        finally:
            await self._release_connection(conn)

    async def collect_transaction_metrics(self) -> Dict[str, Any]:
        """
        Collect transaction statistics.

        Returns:
            Dict with transaction commit/rollback counts and row operation counts
        """
        conn = await self._get_connection()
        try:
            query = """
                SELECT
                    xact_commit,
                    xact_rollback,
                    tup_inserted,
                    tup_updated,
                    tup_deleted
                FROM pg_stat_database
                WHERE datname = current_database();
            """
            row = await conn.fetchrow(query)

            return {
                "transactions_committed": int(row["xact_commit"] or 0),
                "transactions_rolled_back": int(row["xact_rollback"] or 0),
                "rows_inserted": int(row["tup_inserted"] or 0),
                "rows_updated": int(row["tup_updated"] or 0),
                "rows_deleted": int(row["tup_deleted"] or 0),
            }
        finally:
            await self._release_connection(conn)

    async def collect_replication_metrics(self) -> Dict[str, Any]:
        """
        Collect replication status metrics.

        Returns:
            Dict with replication lag and status (empty if not a replica)
        """
        conn = await self._get_connection()
        try:
            # Check if this is a replica
            is_replica_query = "SELECT pg_is_in_recovery();"
            is_replica = await conn.fetchval(is_replica_query)

            if not is_replica:
                return {}  # Primary server, no replication lag

            # Get replication lag
            lag_query = """
                SELECT
                    EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) * 1000 as replication_lag_ms
            """
            lag_row = await conn.fetchrow(lag_query)

            return {
                "replication_lag_ms": round(float(lag_row["replication_lag_ms"] or 0), 2),
                "is_in_recovery": is_replica,
            }
        except Exception:
            # Replication monitoring may not be available
            return {}
        finally:
            await self._release_connection(conn)

    async def collect_all_metrics(self) -> PostgreSQLMetrics:
        """
        Collect all PostgreSQL metrics at once.

        Returns:
            PostgreSQLMetrics: Complete metrics snapshot

        Raises:
            ConnectionError: If unable to connect to database
        """
        try:
            timestamp = datetime.now(timezone.utc)

            connection_pool = await self.collect_connection_pool_metrics()
            query_performance = await self.collect_query_performance_metrics()
            database_size = await self.collect_database_size_metrics()
            cache = await self.collect_cache_metrics()
            transactions = await self.collect_transaction_metrics()
            replication = await self.collect_replication_metrics()

            return PostgreSQLMetrics(
                timestamp=timestamp,
                connection_pool=connection_pool,
                query_performance=query_performance,
                database_size=database_size,
                cache=cache,
                transactions=transactions,
                replication=replication,
            )
        except Exception as e:
            raise ConnectionError(f"Failed to collect PostgreSQL metrics: {e}") from e

    async def close(self) -> None:
        """Close connection pool and cleanup resources"""
        if self._pool:
            await self._pool.close()
            self._pool = None
