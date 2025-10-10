# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Unit Tests for Issue #270: PostgreSQL Metrics Collector

Tests the PostgreSQL metrics collection functionality including connection pool
metrics, query performance, database size, and cache statistics.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the class we'll implement
from violentutf_api.fastapi_app.app.monitoring.database.postgres_metrics import (
    PostgresMetricsCollector,
    PostgreSQLMetrics,
)


class TestPostgresMetricsCollector:
    """Test suite for PostgresMetricsCollector"""

    @pytest.fixture
    def collector(self):
        """Create a PostgresMetricsCollector instance for testing"""
        connection_string = "postgresql://keycloak:test@localhost:5432/keycloak"
        return PostgresMetricsCollector(connection_string)

    @pytest.fixture
    def mock_postgres_connection(self):
        """Mock PostgreSQL database connection"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.execute.return_value = mock_cursor
        return mock_conn, mock_cursor

    @pytest.mark.asyncio
    async def test_collect_connection_pool_metrics(self, collector):
        """Test collection of connection pool metrics"""
        mock_conn = AsyncMock()

        # Mock connection pool stats query result with proper fetchrow
        mock_row = {
            'total': 100,
            'active': 45,
            'idle': 50,
            'waiting': 5
        }
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        with patch.object(collector, '_get_connection', return_value=mock_conn):
            with patch.object(collector, '_release_connection', return_value=None):
                metrics = await collector.collect_connection_pool_metrics()

        assert isinstance(metrics, dict)
        assert 'active_connections' in metrics
        assert 'idle_connections' in metrics
        assert 'waiting_connections' in metrics
        assert 'total_connections' in metrics
        assert 'pool_usage_percent' in metrics

        assert metrics['active_connections'] == 45
        assert metrics['idle_connections'] == 50
        assert metrics['waiting_connections'] == 5
        assert metrics['total_connections'] == 100
        assert metrics['pool_usage_percent'] == 45.0  # 45/100

    @pytest.mark.asyncio
    async def test_collect_query_performance_metrics(self, collector, mock_postgres_connection):
        """Test collection of query performance metrics"""
        mock_conn, mock_cursor = mock_postgres_connection

        # Mock query performance stats
        mock_cursor.fetchall.return_value = [
            {'query': 'SELECT * FROM users', 'avg_time': 15.5, 'calls': 1000},
            {'query': 'INSERT INTO sessions', 'avg_time': 8.2, 'calls': 500},
        ]

        with patch.object(collector, '_get_connection', return_value=mock_conn):
            metrics = await collector.collect_query_performance_metrics()

        assert isinstance(metrics, dict)
        assert 'avg_query_time_ms' in metrics
        assert 'total_queries' in metrics
        assert 'slow_queries_count' in metrics
        assert metrics['avg_query_time_ms'] > 0

    @pytest.mark.asyncio
    async def test_collect_database_size_metrics(self, collector):
        """Test collection of database size metrics"""
        mock_conn = AsyncMock()

        # Mock database size query result
        mock_row = {
            'database_size': 52428800,  # 50MB in bytes
            'table_size': 41943040,     # 40MB
            'index_size': 10485760      # 10MB
        }
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        with patch.object(collector, '_get_connection', return_value=mock_conn):
            with patch.object(collector, '_release_connection', return_value=None):
                metrics = await collector.collect_database_size_metrics()

        assert isinstance(metrics, dict)
        assert 'database_size_mb' in metrics
        assert 'table_size_mb' in metrics
        assert 'index_size_mb' in metrics
        assert metrics['database_size_mb'] == pytest.approx(50.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_collect_cache_hit_ratio(self, collector):
        """Test collection of cache hit ratio metrics"""
        mock_conn = AsyncMock()

        # Mock cache stats - 98% hit ratio
        mock_row = {
            'heap_blks_read': 1000,
            'heap_blks_hit': 49000
        }
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        with patch.object(collector, '_get_connection', return_value=mock_conn):
            with patch.object(collector, '_release_connection', return_value=None):
                metrics = await collector.collect_cache_metrics()

        assert isinstance(metrics, dict)
        assert 'cache_hit_ratio' in metrics
        assert 'buffer_cache_hits' in metrics
        assert 'buffer_cache_reads' in metrics
        assert 0.0 <= metrics['cache_hit_ratio'] <= 1.0
        assert metrics['cache_hit_ratio'] == pytest.approx(0.98, rel=0.01)

    @pytest.mark.asyncio
    async def test_collect_transaction_rate_metrics(self, collector, mock_postgres_connection):
        """Test collection of transaction rate metrics"""
        mock_conn, mock_cursor = mock_postgres_connection

        # Mock transaction stats
        mock_cursor.fetchone.return_value = {
            'xact_commit': 10000,
            'xact_rollback': 100,
            'tup_inserted': 5000,
            'tup_updated': 3000,
            'tup_deleted': 500
        }

        with patch.object(collector, '_get_connection', return_value=mock_conn):
            metrics = await collector.collect_transaction_metrics()

        assert isinstance(metrics, dict)
        assert 'transactions_committed' in metrics
        assert 'transactions_rolled_back' in metrics
        assert 'rows_inserted' in metrics
        assert 'rows_updated' in metrics
        assert 'rows_deleted' in metrics

    @pytest.mark.asyncio
    async def test_collect_replication_status(self, collector):
        """Test collection of replication status metrics"""
        mock_conn = AsyncMock()

        # Mock replication stats
        mock_row = {
            'replication_lag_bytes': 1024,
            'is_in_recovery': False
        }
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        with patch.object(collector, '_get_connection', return_value=mock_conn):
            with patch.object(collector, '_release_connection', return_value=None):
                metrics = await collector.collect_replication_metrics()

        assert isinstance(metrics, dict)
        assert 'replication_lag_bytes' in metrics or metrics == {}  # May be empty if no replication

    @pytest.mark.asyncio
    async def test_collect_all_metrics(self, collector):
        """Test collection of all metrics at once"""
        with patch.object(collector, 'collect_connection_pool_metrics', return_value={'pool': 'data'}), \
             patch.object(collector, 'collect_query_performance_metrics', return_value={'query': 'data'}), \
             patch.object(collector, 'collect_database_size_metrics', return_value={'size': 'data'}), \
             patch.object(collector, 'collect_cache_metrics', return_value={'cache': 'data'}), \
             patch.object(collector, 'collect_transaction_metrics', return_value={'txn': 'data'}), \
             patch.object(collector, 'collect_replication_metrics', return_value={}):

            metrics = await collector.collect_all_metrics()

        assert isinstance(metrics, PostgreSQLMetrics)
        assert metrics.timestamp is not None
        assert isinstance(metrics.timestamp, datetime)
        assert metrics.timestamp.tzinfo is not None  # Timezone aware
        assert hasattr(metrics, 'connection_pool')
        assert hasattr(metrics, 'query_performance')
        assert hasattr(metrics, 'database_size')
        assert hasattr(metrics, 'cache')

    @pytest.mark.asyncio
    async def test_connection_failure_handling(self, collector):
        """Test graceful handling of connection failures"""
        with patch.object(collector, '_get_connection', side_effect=ConnectionError("Database unavailable")):
            with pytest.raises(ConnectionError):
                await collector.collect_all_metrics()

    @pytest.mark.asyncio
    async def test_metric_timestamp_accuracy(self, collector):
        """Test that metric timestamps are accurate and timezone-aware"""
        with patch.object(collector, 'collect_connection_pool_metrics', return_value={}), \
             patch.object(collector, 'collect_query_performance_metrics', return_value={}), \
             patch.object(collector, 'collect_database_size_metrics', return_value={}), \
             patch.object(collector, 'collect_cache_metrics', return_value={}), \
             patch.object(collector, 'collect_transaction_metrics', return_value={}), \
             patch.object(collector, 'collect_replication_metrics', return_value={}):

            before = datetime.now(timezone.utc)
            metrics = await collector.collect_all_metrics()
            after = datetime.now(timezone.utc)

        assert before <= metrics.timestamp <= after
        assert metrics.timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_connection_pool_acquisition(self, collector):
        """Test connection pool can acquire connections"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)

        async def mock_create_pool(*args, **kwargs):
            return mock_pool

        with patch('asyncpg.create_pool', side_effect=mock_create_pool):
            conn = await collector._get_connection()
            assert conn is not None
            assert conn == mock_conn

    @pytest.mark.asyncio
    async def test_connection_release(self, collector):
        """Test proper connection release after metric collection"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()

        collector._pool = mock_pool

        conn = await collector._get_connection()
        await collector._release_connection(conn)

        mock_pool.release.assert_called_once_with(mock_conn)

    @pytest.mark.asyncio
    async def test_collection_performance(self, collector):
        """Test that collection completes within 2 seconds"""
        import time

        with patch.object(collector, 'collect_connection_pool_metrics', return_value={}), \
             patch.object(collector, 'collect_query_performance_metrics', return_value={}), \
             patch.object(collector, 'collect_database_size_metrics', return_value={}), \
             patch.object(collector, 'collect_cache_metrics', return_value={}), \
             patch.object(collector, 'collect_transaction_metrics', return_value={}), \
             patch.object(collector, 'collect_replication_metrics', return_value={}):

            start = time.time()
            await collector.collect_all_metrics()
            duration = time.time() - start

        assert duration < 2.0, f"Collection took {duration:.2f}s, expected < 2s"

    def test_connection_string_validation(self):
        """Test connection string validation"""
        # Valid connection string
        collector = PostgresMetricsCollector("postgresql://user:pass@localhost:5432/db")
        assert collector.connection_string is not None

        # Invalid connection string should raise error
        with pytest.raises(ValueError):
            PostgresMetricsCollector("invalid://connection/string")

    @pytest.mark.asyncio
    async def test_metric_value_validation(self, collector):
        """Test that metric values are within expected ranges"""
        mock_conn = AsyncMock()

        # Test connection pool metrics are non-negative
        mock_row = {
            'total': 100,
            'active': 45,
            'idle': 50,
            'waiting': 5
        }
        mock_conn.fetchrow = AsyncMock(return_value=mock_row)

        with patch.object(collector, '_get_connection', return_value=mock_conn):
            with patch.object(collector, '_release_connection', return_value=None):
                metrics = await collector.collect_connection_pool_metrics()

        assert metrics['active_connections'] >= 0
        assert metrics['idle_connections'] >= 0
        assert metrics['waiting_connections'] >= 0
        assert metrics['total_connections'] >= 0
        assert 0 <= metrics['pool_usage_percent'] <= 100

    @pytest.mark.asyncio
    async def test_no_connection_leak(self, collector):
        """Test that connections are properly closed and not leaked"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        mock_pool.release = AsyncMock()

        collector._pool = mock_pool

        # Collect metrics multiple times
        for _ in range(10):
            conn = await collector._get_connection()
            await collector._release_connection(conn)

        # Verify all connections were released
        assert mock_pool.acquire.call_count == 10
        assert mock_pool.release.call_count == 10


class TestPostgreSQLMetrics:
    """Test suite for PostgreSQLMetrics data class"""

    def test_metrics_creation(self):
        """Test PostgreSQLMetrics can be created with required fields"""
        metrics = PostgreSQLMetrics(
            timestamp=datetime.now(timezone.utc),
            connection_pool={'active': 45},
            query_performance={'avg_time': 15.5},
            database_size={'size_mb': 50.0},
            cache={'hit_ratio': 0.98},
            transactions={'committed': 1000},
            replication={}
        )

        assert metrics.timestamp is not None
        assert isinstance(metrics.connection_pool, dict)
        assert isinstance(metrics.query_performance, dict)
        assert isinstance(metrics.database_size, dict)
        assert isinstance(metrics.cache, dict)

    def test_metrics_to_dict(self):
        """Test PostgreSQLMetrics can be serialized to dict"""
        metrics = PostgreSQLMetrics(
            timestamp=datetime.now(timezone.utc),
            connection_pool={'active': 45},
            query_performance={'avg_time': 15.5},
            database_size={'size_mb': 50.0},
            cache={'hit_ratio': 0.98},
            transactions={'committed': 1000},
            replication={}
        )

        data = metrics.to_dict()
        assert isinstance(data, dict)
        assert 'timestamp' in data
        assert 'connection_pool' in data
        assert 'query_performance' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
