# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Unit Tests for Issue #270: SQLite Metrics Collector

Tests the SQLite metrics collection functionality including file size,
query performance, lock contention, and WAL mode statistics.
"""

import pytest
import pytest_asyncio
import aiosqlite
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from violentutf_api.fastapi_app.app.monitoring.database.sqlite_metrics import (
    SQLiteMetricsCollector,
    SQLiteMetrics,
)


class TestSQLiteMetricsCollector:
    """Test suite for SQLiteMetricsCollector"""

    @pytest_asyncio.fixture
    async def test_database(self):
        """Create a temporary SQLite database for testing"""
        temp_fd, temp_path = tempfile.mkstemp(suffix=".db")
        os.close(temp_fd)

        # Initialize with some data
        async with aiosqlite.connect(temp_path) as db:
            await db.execute(
                """
                CREATE TABLE test_table (
                    id INTEGER PRIMARY KEY,
                    data TEXT
                )
                """
            )
            await db.executemany(
                "INSERT INTO test_table (data) VALUES (?)",
                [("test_data",) for _ in range(100)],
            )
            await db.commit()

        yield temp_path

        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        wal_path = f"{temp_path}-wal"
        if os.path.exists(wal_path):
            os.unlink(wal_path)
        shm_path = f"{temp_path}-shm"
        if os.path.exists(shm_path):
            os.unlink(shm_path)

    @pytest.fixture
    def collector(self, test_database):
        """Create a SQLiteMetricsCollector instance for testing"""
        return SQLiteMetricsCollector(test_database)

    @pytest.mark.asyncio
    async def test_collect_file_size_metrics(self, collector, test_database):
        """Test collection of database file size metrics"""
        metrics = await collector.collect_file_size_metrics()

        assert isinstance(metrics, dict)
        assert "database_file_size_mb" in metrics
        assert "wal_file_size_mb" in metrics
        assert "shm_file_size_mb" in metrics
        assert "total_size_mb" in metrics
        assert metrics["database_file_size_mb"] > 0
        assert metrics["total_size_mb"] >= metrics["database_file_size_mb"]

    @pytest.mark.asyncio
    async def test_file_growth_rate_calculation(self, collector):
        """Test file growth rate calculation over time"""
        # Collect initial metrics
        metrics1 = await collector.collect_file_size_metrics()
        initial_size = metrics1["database_file_size_mb"]

        # Add more data
        async with aiosqlite.connect(collector.database_path) as db:
            await db.executemany(
                "INSERT INTO test_table (data) VALUES (?)",
                [("more_data",) for _ in range(1000)],
            )
            await db.commit()

        # Collect metrics again
        metrics2 = await collector.collect_file_size_metrics()
        final_size = metrics2["database_file_size_mb"]

        assert final_size > initial_size
        growth = final_size - initial_size
        assert growth > 0

    @pytest.mark.asyncio
    async def test_collect_query_performance_metrics(self, collector):
        """Test collection of query execution time metrics"""
        metrics = await collector.collect_query_performance_metrics()

        assert isinstance(metrics, dict)
        assert "avg_query_time_ms" in metrics
        assert "total_queries_executed" in metrics
        assert "slow_queries_count" in metrics
        assert metrics["avg_query_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_collect_lock_contention_metrics(self, collector):
        """Test lock contention detection"""
        metrics = await collector.collect_lock_contention_metrics()

        assert isinstance(metrics, dict)
        assert "lock_timeout_count" in metrics
        assert "concurrent_connections" in metrics
        assert "busy_timeout_ms" in metrics
        assert metrics["lock_timeout_count"] >= 0
        assert metrics["concurrent_connections"] >= 0

    @pytest.mark.asyncio
    async def test_wal_mode_detection(self, collector):
        """Test WAL mode detection"""
        # Enable WAL mode
        async with aiosqlite.connect(collector.database_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.commit()

        metrics = await collector.collect_wal_metrics()

        assert isinstance(metrics, dict)
        assert "journal_mode" in metrics
        assert metrics["journal_mode"] in ["wal", "delete", "truncate", "persist"]

    @pytest.mark.asyncio
    async def test_wal_file_size_monitoring(self, collector):
        """Test WAL file size tracking"""
        # Enable WAL mode and create some transactions
        async with aiosqlite.connect(collector.database_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.executemany(
                "INSERT INTO test_table (data) VALUES (?)",
                [("wal_data",) for _ in range(500)],
            )
            await db.commit()

        metrics = await collector.collect_wal_metrics()

        assert "wal_file_size_mb" in metrics
        assert "wal_checkpoint_count" in metrics
        assert metrics["wal_file_size_mb"] >= 0

    @pytest.mark.asyncio
    async def test_checkpoint_frequency_monitoring(self, collector):
        """Test checkpoint operation monitoring"""
        # Enable WAL mode
        async with aiosqlite.connect(collector.database_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.commit()

            # Trigger checkpoint
            await db.execute("PRAGMA wal_checkpoint(FULL)")
            await db.commit()

        metrics = await collector.collect_wal_metrics()

        assert "wal_checkpoint_count" in metrics
        assert "last_checkpoint_time" in metrics

    @pytest.mark.asyncio
    async def test_concurrent_access_patterns(self, collector):
        """Test concurrent connection tracking"""
        metrics = await collector.collect_lock_contention_metrics()

        assert "concurrent_connections" in metrics
        assert metrics["concurrent_connections"] >= 1  # At least our connection

    @pytest.mark.asyncio
    async def test_backup_operation_status(self, collector):
        """Test backup operation monitoring"""
        metrics = await collector.collect_backup_metrics()

        assert isinstance(metrics, dict)
        assert "last_backup_time" in metrics
        assert "backup_size_mb" in metrics

    @pytest.mark.asyncio
    async def test_io_latency_measurement(self, collector):
        """Test I/O latency measurement"""
        metrics = await collector.collect_io_metrics()

        assert isinstance(metrics, dict)
        assert "avg_read_latency_ms" in metrics
        assert "avg_write_latency_ms" in metrics
        assert metrics["avg_read_latency_ms"] >= 0
        assert metrics["avg_write_latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_collect_all_metrics(self, collector):
        """Test collection of all SQLite metrics at once"""
        metrics = await collector.collect_all_metrics()

        assert isinstance(metrics, SQLiteMetrics)
        assert metrics.timestamp is not None
        assert isinstance(metrics.timestamp, datetime)
        assert metrics.timestamp.tzinfo is not None  # Timezone aware
        assert hasattr(metrics, "file_size")
        assert hasattr(metrics, "query_performance")
        assert hasattr(metrics, "lock_contention")
        assert hasattr(metrics, "wal_metrics")

    @pytest.mark.asyncio
    async def test_missing_database_file_handling(self):
        """Test graceful handling of missing database file"""
        collector = SQLiteMetricsCollector("/nonexistent/database.db")

        with pytest.raises(FileNotFoundError):
            await collector.collect_file_size_metrics()

    @pytest.mark.asyncio
    async def test_metric_timestamp_accuracy(self, collector):
        """Test that metric timestamps are accurate and timezone-aware"""
        before = datetime.now(timezone.utc)
        metrics = await collector.collect_all_metrics()
        after = datetime.now(timezone.utc)

        assert before <= metrics.timestamp <= after
        assert metrics.timestamp.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_collection_performance(self, collector):
        """Test that collection completes within 1 second"""
        import time

        start = time.time()
        await collector.collect_all_metrics()
        duration = time.time() - start

        assert duration < 1.0, f"Collection took {duration:.2f}s, expected < 1s"

    @pytest.mark.asyncio
    async def test_no_database_lock_during_collection(self, collector):
        """Test that metrics collection doesn't lock the database"""
        # Start metrics collection
        import asyncio

        async def collect_metrics():
            return await collector.collect_all_metrics()

        async def write_data():
            async with aiosqlite.connect(collector.database_path) as db:
                await db.execute(
                    "INSERT INTO test_table (data) VALUES (?)", ("concurrent_data",)
                )
                await db.commit()
            return True

        # Run both operations concurrently
        results = await asyncio.gather(collect_metrics(), write_data())

        assert results[0] is not None  # Metrics collected
        assert results[1] is True  # Write succeeded

    @pytest.mark.asyncio
    async def test_metric_value_validation(self, collector):
        """Test that metric values are within expected ranges"""
        metrics = await collector.collect_file_size_metrics()

        # File sizes should be non-negative
        assert metrics["database_file_size_mb"] >= 0
        assert metrics["wal_file_size_mb"] >= 0
        assert metrics["shm_file_size_mb"] >= 0
        assert metrics["total_size_mb"] >= 0

    @pytest.mark.asyncio
    async def test_wal_mode_status(self, collector):
        """Test WAL mode status detection"""
        # Test with WAL mode enabled
        async with aiosqlite.connect(collector.database_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.commit()

        metrics = await collector.collect_wal_metrics()
        assert metrics["journal_mode"] == "wal"

    @pytest.mark.asyncio
    async def test_wal_size_thresholds(self, collector):
        """Test WAL size threshold checking"""
        # Enable WAL and add data
        async with aiosqlite.connect(collector.database_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.executemany(
                "INSERT INTO test_table (data) VALUES (?)",
                [("threshold_test",) for _ in range(5000)],
            )
            await db.commit()

        metrics = await collector.collect_wal_metrics()

        # Check if WAL size is being tracked
        assert "wal_file_size_mb" in metrics
        assert "wal_size_warning_threshold" in metrics

    @pytest.mark.asyncio
    async def test_database_integrity_check(self, collector):
        """Test database integrity validation"""
        metrics = await collector.collect_integrity_metrics()

        assert isinstance(metrics, dict)
        assert "integrity_check_passed" in metrics
        assert "page_count" in metrics
        assert "page_size_bytes" in metrics

    @pytest.mark.asyncio
    async def test_cache_statistics(self, collector):
        """Test cache statistics collection"""
        metrics = await collector.collect_cache_metrics()

        assert isinstance(metrics, dict)
        assert "cache_size_kb" in metrics
        assert "cache_hit_ratio" in metrics

    def test_database_path_validation(self):
        """Test database path validation"""
        # Valid path
        collector = SQLiteMetricsCollector("/tmp/test.db")
        assert collector.database_path == "/tmp/test.db"

        # Empty path should raise error
        with pytest.raises(ValueError):
            SQLiteMetricsCollector("")

    @pytest.mark.asyncio
    async def test_concurrent_metric_collection(self, collector):
        """Test concurrent metric collection doesn't cause issues"""
        import asyncio

        # Collect metrics concurrently
        tasks = [collector.collect_all_metrics() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for metrics in results:
            assert isinstance(metrics, SQLiteMetrics)

    @pytest.mark.asyncio
    async def test_query_performance_tracking(self, collector):
        """Test query performance measurement"""
        # Execute some queries
        async with aiosqlite.connect(collector.database_path) as db:
            for _ in range(10):
                await db.execute("SELECT * FROM test_table LIMIT 10")

        metrics = await collector.collect_query_performance_metrics()

        assert metrics["total_queries_executed"] > 0
        assert metrics["avg_query_time_ms"] >= 0


class TestSQLiteMetrics:
    """Test suite for SQLiteMetrics data class"""

    def test_metrics_creation(self):
        """Test SQLiteMetrics can be created with required fields"""
        metrics = SQLiteMetrics(
            timestamp=datetime.now(timezone.utc),
            file_size={"database_file_size_mb": 50.0},
            query_performance={"avg_query_time_ms": 5.2},
            lock_contention={"lock_timeout_count": 0},
            wal_metrics={"journal_mode": "wal"},
            io_metrics={"avg_read_latency_ms": 1.5},
            cache_metrics={"cache_hit_ratio": 0.95},
        )

        assert metrics.timestamp is not None
        assert isinstance(metrics.file_size, dict)
        assert isinstance(metrics.query_performance, dict)
        assert isinstance(metrics.lock_contention, dict)
        assert isinstance(metrics.wal_metrics, dict)

    def test_metrics_to_dict(self):
        """Test SQLiteMetrics can be serialized to dict"""
        metrics = SQLiteMetrics(
            timestamp=datetime.now(timezone.utc),
            file_size={"database_file_size_mb": 50.0},
            query_performance={"avg_query_time_ms": 5.2},
            lock_contention={"lock_timeout_count": 0},
            wal_metrics={"journal_mode": "wal"},
            io_metrics={"avg_read_latency_ms": 1.5},
            cache_metrics={"cache_hit_ratio": 0.95},
        )

        data = metrics.to_dict()
        assert isinstance(data, dict)
        assert "timestamp" in data
        assert "file_size" in data
        assert "query_performance" in data
        assert "lock_contention" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
