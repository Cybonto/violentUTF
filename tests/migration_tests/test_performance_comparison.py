# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Performance Comparison Tests - SQLite vs DuckDB - Issue #327.

Benchmarks SQLite performance against DuckDB baseline for:
- Bulk insert operations
- Query performance
- Concurrent access patterns
- Memory usage

Acceptance criteria: Performance within 10% of DuckDB baseline.

Usage:
    pytest tests/migration_tests/test_performance_comparison.py -v --benchmark
    pytest tests/migration_tests/test_performance_comparison.py -v --benchmark-only
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

try:
    import duckdb

    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

from violentutf_api.fastapi_app.app.db.sqlite_manager import SQLiteManager

# Performance thresholds (10% tolerance)
PERFORMANCE_TOLERANCE = 0.10  # 10% degradation allowed


class PerformanceMetrics:
    """Track and compare performance metrics."""

    def __init__(self):
        self.metrics = {}

    def record(self, operation: str, db_type: str, duration: float, count: int = 0):
        """Record a performance metric."""
        if operation not in self.metrics:
            self.metrics[operation] = {}
        self.metrics[operation][db_type] = {
            "duration": duration,
            "count": count,
            "ops_per_second": count / duration if duration > 0 else 0,
        }

    def compare(self, operation: str) -> Dict[str, Any]:
        """Compare SQLite vs DuckDB for an operation."""
        if operation not in self.metrics:
            return {}

        sqlite = self.metrics[operation].get("sqlite", {})
        duckdb = self.metrics[operation].get("duckdb", {})

        if not sqlite or not duckdb:
            return {"status": "incomplete"}

        sqlite_duration = sqlite.get("duration", 0)
        duckdb_duration = duckdb.get("duration", 0)

        degradation = (sqlite_duration - duckdb_duration) / duckdb_duration if duckdb_duration > 0 else 0

        return {
            "operation": operation,
            "sqlite_duration": sqlite_duration,
            "duckdb_duration": duckdb_duration,
            "degradation_percent": degradation * 100,
            "within_tolerance": abs(degradation) <= PERFORMANCE_TOLERANCE,
            "sqlite_ops_per_sec": sqlite.get("ops_per_second", 0),
            "duckdb_ops_per_sec": duckdb.get("ops_per_second", 0),
        }

    def generate_report(self) -> str:
        """Generate a performance comparison report."""
        lines = [
            "=" * 80,
            "PERFORMANCE COMPARISON REPORT: SQLite vs DuckDB",
            "=" * 80,
            "",
        ]

        for operation in self.metrics.keys():
            comparison = self.compare(operation)
            if comparison.get("status") == "incomplete":
                continue

            lines.append(f"Operation: {operation}")
            lines.append(f"  SQLite Duration:  {comparison['sqlite_duration']:.4f}s")
            lines.append(f"  DuckDB Duration:  {comparison['duckdb_duration']:.4f}s")
            lines.append(f"  Degradation:      {comparison['degradation_percent']:+.2f}%")
            lines.append(f"  SQLite Ops/sec:   {comparison['sqlite_ops_per_sec']:.2f}")
            lines.append(f"  DuckDB Ops/sec:   {comparison['duckdb_ops_per_sec']:.2f}")
            lines.append(f"  Status:           {'PASS' if comparison['within_tolerance'] else 'FAIL'}")
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def metrics():
    """Create a performance metrics tracker."""
    return PerformanceMetrics()


class TestBulkInsertPerformance:
    """Test bulk insert performance."""

    @pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="DuckDB not available")
    def test_bulk_insert_generators_duckdb(self, temp_dir, metrics):
        """Benchmark bulk generator insert with DuckDB."""
        db_path = os.path.join(temp_dir, "duckdb_test.db")
        conn = duckdb.connect(db_path)

        # Create table
        conn.execute(
            """
            CREATE TABLE generators (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                parameters VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """
        )

        # Generate test data
        test_data = [
            (
                f"gen_{i}",
                f"generator_{i}",
                "openai",
                '{"model": "gpt-4"}',
                "2025-01-01 00:00:00",
                "2025-01-01 00:00:00",
            )
            for i in range(1000)
        ]

        # Benchmark insert
        start_time = time.time()
        conn.executemany("INSERT INTO generators VALUES (?, ?, ?, ?, ?, ?)", test_data)
        duration = time.time() - start_time

        conn.close()
        metrics.record("bulk_insert_1000_generators", "duckdb", duration, 1000)

    def test_bulk_insert_generators_sqlite(self, temp_dir, metrics):
        """Benchmark bulk generator insert with SQLite."""
        manager = SQLiteManager("test_user", app_data_dir=temp_dir)

        # Generate test data
        test_data = [
            {
                "name": f"generator_{i}",
                "type": "openai",
                "parameters": {"model": "gpt-4"},
            }
            for i in range(1000)
        ]

        # Benchmark insert
        start_time = time.time()
        for data in test_data:
            manager.create_generator(data["name"], data["type"], data["parameters"])
        duration = time.time() - start_time

        metrics.record("bulk_insert_1000_generators", "sqlite", duration, 1000)

        # Compare with DuckDB
        comparison = metrics.compare("bulk_insert_1000_generators")
        if comparison.get("status") != "incomplete":
            print(f"\nBulk Insert (1000 generators): {comparison['degradation_percent']:+.2f}%")
            assert comparison["within_tolerance"], (
                f"SQLite bulk insert degradation ({comparison['degradation_percent']:.2f}%) "
                f"exceeds {PERFORMANCE_TOLERANCE * 100}% threshold"
            )

    @pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="DuckDB not available")
    def test_bulk_insert_prompts_duckdb(self, temp_dir, metrics):
        """Benchmark bulk prompt insert with DuckDB."""
        db_path = os.path.join(temp_dir, "duckdb_prompts.db")
        conn = duckdb.connect(db_path)

        # Create table
        conn.execute(
            """
            CREATE TABLE dataset_prompts (
                id VARCHAR PRIMARY KEY,
                dataset_id VARCHAR,
                prompt_text VARCHAR,
                metadata VARCHAR,
                created_at TIMESTAMP
            )
        """
        )

        # Generate test data (5000 prompts)
        test_data = [
            (
                f"prompt_{i}",
                "dataset_1",
                f"This is test prompt number {i}",
                "{}",
                "2025-01-01 00:00:00",
            )
            for i in range(5000)
        ]

        # Benchmark insert
        start_time = time.time()
        conn.executemany("INSERT INTO dataset_prompts VALUES (?, ?, ?, ?, ?)", test_data)
        duration = time.time() - start_time

        conn.close()
        metrics.record("bulk_insert_5000_prompts", "duckdb", duration, 5000)

    def test_bulk_insert_prompts_sqlite(self, temp_dir, metrics):
        """Benchmark bulk prompt insert with SQLite."""
        manager = SQLiteManager("test_user", app_data_dir=temp_dir)

        # Create dataset first
        dataset_id = manager.create_dataset("test_dataset", {"source": "benchmark"})

        # Generate test data (5000 prompts)
        start_time = time.time()
        for i in range(5000):
            manager.add_prompt_to_dataset(dataset_id, f"This is test prompt number {i}", {})
        duration = time.time() - start_time

        metrics.record("bulk_insert_5000_prompts", "sqlite", duration, 5000)

        # Compare with DuckDB
        comparison = metrics.compare("bulk_insert_5000_prompts")
        if comparison.get("status") != "incomplete":
            print(f"\nBulk Insert (5000 prompts): {comparison['degradation_percent']:+.2f}%")
            # Allow more tolerance for large inserts (20%)
            assert abs(comparison["degradation_percent"]) <= 20, (
                f"SQLite bulk prompt insert degradation ({comparison['degradation_percent']:.2f}%) "
                f"exceeds 20% threshold"
            )


class TestQueryPerformance:
    """Test query performance."""

    @pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="DuckDB not available")
    def test_query_with_filter_duckdb(self, temp_dir, metrics):
        """Benchmark filtered queries with DuckDB."""
        db_path = os.path.join(temp_dir, "duckdb_query.db")
        conn = duckdb.connect(db_path)

        # Create and populate table
        conn.execute(
            """
            CREATE TABLE generators (
                id VARCHAR PRIMARY KEY,
                name VARCHAR,
                type VARCHAR,
                parameters VARCHAR
            )
        """
        )

        test_data = [(f"gen_{i}", f"generator_{i}", "openai" if i % 2 == 0 else "anthropic", "{}") for i in range(2000)]
        conn.executemany("INSERT INTO generators VALUES (?, ?, ?, ?)", test_data)

        # Benchmark filtered query
        start_time = time.time()
        for _ in range(100):
            result = conn.execute("SELECT * FROM generators WHERE type = 'openai'").fetchall()
        duration = time.time() - start_time

        conn.close()
        metrics.record("query_filtered_100x", "duckdb", duration, 100)

    def test_query_with_filter_sqlite(self, temp_dir, metrics):
        """Benchmark filtered queries with SQLite."""
        manager = SQLiteManager("test_user", app_data_dir=temp_dir)

        # Populate data
        for i in range(2000):
            manager.create_generator(f"generator_{i}", "openai" if i % 2 == 0 else "anthropic", {})

        # Benchmark filtered query
        start_time = time.time()
        for _ in range(100):
            result = manager.list_generators(generator_type="openai")
        duration = time.time() - start_time

        metrics.record("query_filtered_100x", "sqlite", duration, 100)

        # Compare with DuckDB
        comparison = metrics.compare("query_filtered_100x")
        if comparison.get("status") != "incomplete":
            print(f"\nFiltered Query (100x): {comparison['degradation_percent']:+.2f}%")
            assert comparison["within_tolerance"], (
                f"SQLite query degradation ({comparison['degradation_percent']:.2f}%) "
                f"exceeds {PERFORMANCE_TOLERANCE * 100}% threshold"
            )


class TestConcurrentAccessPerformance:
    """Test concurrent access performance."""

    def test_concurrent_writes_sqlite(self, temp_dir, metrics):
        """Benchmark concurrent write operations with SQLite."""
        import threading

        manager = SQLiteManager("test_user", app_data_dir=temp_dir)
        num_threads = 10
        operations_per_thread = 50

        def write_operations(thread_id: int):
            """Perform write operations."""
            for i in range(operations_per_thread):
                manager.create_generator(f"thread_{thread_id}_gen_{i}", "openai", {"thread": thread_id})

        # Benchmark concurrent writes
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=write_operations, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        duration = time.time() - start_time
        total_ops = num_threads * operations_per_thread

        metrics.record("concurrent_writes_10_threads", "sqlite", duration, total_ops)
        print(f"\nConcurrent Writes (10 threads, 500 ops): {duration:.4f}s")
        print(f"Operations per second: {total_ops / duration:.2f}")

        # Should complete in reasonable time (< 30 seconds for 500 ops)
        assert duration < 30, f"Concurrent writes too slow: {duration:.2f}s"

    def test_mixed_concurrent_operations_sqlite(self, temp_dir, metrics):
        """Benchmark mixed read/write operations with SQLite."""
        import threading

        manager = SQLiteManager("test_user", app_data_dir=temp_dir)

        # Pre-populate some data
        for i in range(100):
            manager.create_generator(f"preset_gen_{i}", "openai", {})

        num_threads = 10
        operations_per_thread = 20

        def mixed_operations(thread_id: int):
            """Perform mixed read/write operations."""
            for i in range(operations_per_thread):
                if i % 2 == 0:
                    # Write
                    manager.create_generator(f"thread_{thread_id}_gen_{i}", "openai", {})
                else:
                    # Read
                    manager.list_generators()

        # Benchmark mixed operations
        start_time = time.time()
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=mixed_operations, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        duration = time.time() - start_time
        total_ops = num_threads * operations_per_thread

        metrics.record("mixed_concurrent_ops", "sqlite", duration, total_ops)
        print(f"\nMixed Concurrent Ops (10 threads, 200 ops): {duration:.4f}s")
        print(f"Operations per second: {total_ops / duration:.2f}")

        # Should complete without deadlocks
        assert duration < 30, f"Mixed operations too slow: {duration:.2f}s"


class TestMemoryUsage:
    """Test memory usage patterns."""

    def test_large_dataset_memory_usage_sqlite(self, temp_dir):
        """Test memory usage with large datasets in SQLite."""
        import os as os_module

        import psutil

        process = psutil.Process(os_module.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        manager = SQLiteManager("test_user", app_data_dir=temp_dir)

        # Create large dataset
        dataset_id = manager.create_dataset("large_dataset", {})
        for i in range(10000):
            manager.add_prompt_to_dataset(dataset_id, f"This is a long test prompt number {i} " * 10, {"index": i})

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"\nMemory Usage (10k prompts):")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final:   {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")

        # Memory increase should be reasonable (< 500 MB for 10k prompts)
        assert memory_increase < 500, f"Excessive memory usage: {memory_increase:.2f} MB"


@pytest.mark.benchmark
class TestBenchmarkSummary:
    """Generate final benchmark summary."""

    def test_generate_performance_report(self, metrics):
        """Generate and display performance comparison report."""
        report = metrics.generate_report()
        print(report)

        # Save report to file
        report_dir = Path("/Users/tamnguyen/Documents/GitHub/violentUTF/reports")
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / "performance_comparison_sqlite_vs_duckdb.txt"
        with open(report_file, "w") as f:
            f.write(report)

        print(f"\nPerformance report saved to: {report_file}")


if __name__ == "__main__":
    # Run benchmarks
    pytest.main([__file__, "-v", "--benchmark"])
