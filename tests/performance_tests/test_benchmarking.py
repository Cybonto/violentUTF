# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for performance benchmarking functionality."""

from __future__ import annotations

import os
import sys
import tempfile
from typing import Any, Dict

import pytest
import sqlite3

# Add scripts directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts/performance-optimization"))


@pytest.fixture
def temp_benchmark_dir() -> Any:
    """Create temporary directory for benchmark results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_db(temp_benchmark_dir: str) -> str:
    """Create sample database for benchmarking."""
    db_path = os.path.join(temp_benchmark_dir, "benchmark.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE test_data (
            id INTEGER PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    for i in range(1000):
        cursor.execute("INSERT INTO test_data (data) VALUES (?)", (f"data_{i}",))

    conn.commit()
    conn.close()
    return db_path


class TestPerformanceBenchmark:
    """Test performance benchmarking functionality."""

    def test_benchmark_initialization(self) -> None:
        """Test benchmark tool can be initialized."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()
        assert benchmark is not None
        assert hasattr(benchmark, "run_benchmark")
        assert hasattr(benchmark, "compare_results")
        assert hasattr(benchmark, "generate_report")

    def test_run_query_benchmark(self, sample_db: str) -> None:
        """Test running query benchmarks."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        queries = [
            "SELECT * FROM test_data WHERE id = 1",
            "SELECT COUNT(*) FROM test_data",
            "SELECT * FROM test_data ORDER BY created_at DESC LIMIT 10",
        ]

        results = benchmark.run_benchmark(sample_db, "sqlite", queries)

        assert results is not None
        assert "queries" in results
        assert "metrics" in results
        assert len(results["queries"]) == len(queries)

    def test_measure_throughput(self, sample_db: str) -> None:
        """Test throughput measurement."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        query = "SELECT * FROM test_data WHERE id = ?"
        throughput = benchmark.measure_throughput(
            sample_db, "sqlite", query, duration=5
        )

        assert throughput is not None
        assert "operations_per_second" in throughput
        assert throughput["operations_per_second"] > 0

    def test_measure_latency(self, sample_db: str) -> None:
        """Test latency measurement."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        query = "SELECT * FROM test_data WHERE id = 1"
        latency = benchmark.measure_latency(sample_db, "sqlite", query, iterations=100)

        assert latency is not None
        assert "avg_latency" in latency
        assert "min_latency" in latency
        assert "max_latency" in latency
        assert "p95_latency" in latency
        assert "p99_latency" in latency

    def test_concurrent_benchmark(self, sample_db: str) -> None:
        """Test concurrent query benchmarking."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        query = "SELECT * FROM test_data WHERE id = ?"
        results = benchmark.run_concurrent_benchmark(
            sample_db, "sqlite", query, concurrent_users=10, duration=5
        )

        assert results is not None
        assert "concurrent_users" in results
        assert "total_operations" in results
        assert "operations_per_second" in results

    def test_load_test(self, sample_db: str) -> None:
        """Test load testing."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        queries = ["SELECT * FROM test_data WHERE id = ?"]

        results = benchmark.run_load_test(
            sample_db, "sqlite", queries, ramp_up_users=10, duration=10
        )

        assert results is not None
        assert "load_test_results" in results
        assert "max_concurrent_users" in results

    def test_stress_test(self, sample_db: str) -> None:
        """Test stress testing."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        queries = ["SELECT * FROM test_data WHERE id = ?"]

        results = benchmark.run_stress_test(
            sample_db, "sqlite", queries, max_users=50, duration=10
        )

        assert results is not None
        assert "breaking_point" in results
        assert "max_throughput" in results

    def test_compare_benchmark_results(self) -> None:
        """Test benchmark result comparison."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        baseline = {
            "operations_per_second": 500,
            "avg_latency": 100,
            "p95_latency": 200,
        }

        current = {
            "operations_per_second": 750,
            "avg_latency": 66,
            "p95_latency": 150,
        }

        comparison = benchmark.compare_results(baseline, current)

        assert comparison is not None
        assert "improvement" in comparison
        assert comparison["improvement"]["operations_per_second"] > 0
        assert comparison["improvement"]["avg_latency"] < 0  # Lower is better

    def test_generate_benchmark_report(
        self, sample_db: str, temp_benchmark_dir: str
    ) -> None:
        """Test benchmark report generation."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        queries = ["SELECT * FROM test_data WHERE id = 1"]
        results = benchmark.run_benchmark(sample_db, "sqlite", queries)

        report_path = os.path.join(temp_benchmark_dir, "benchmark_report.json")
        benchmark.generate_report(results, report_path)

        assert os.path.exists(report_path)

    def test_save_baseline_metrics(self, temp_benchmark_dir: str) -> None:
        """Test saving baseline metrics."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        metrics = {
            "operations_per_second": 500,
            "avg_latency": 100,
            "database": "sqlite",
        }

        baseline_path = os.path.join(temp_benchmark_dir, "baseline.json")
        benchmark.save_baseline(metrics, baseline_path)

        assert os.path.exists(baseline_path)

    def test_load_baseline_metrics(self, temp_benchmark_dir: str) -> None:
        """Test loading baseline metrics."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        metrics = {
            "operations_per_second": 500,
            "avg_latency": 100,
            "database": "sqlite",
        }

        baseline_path = os.path.join(temp_benchmark_dir, "baseline.json")
        benchmark.save_baseline(metrics, baseline_path)

        loaded = benchmark.load_baseline(baseline_path)

        assert loaded is not None
        assert loaded["operations_per_second"] == metrics["operations_per_second"]

    def test_regression_detection(self) -> None:
        """Test performance regression detection."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        baseline = {"operations_per_second": 500, "avg_latency": 100}

        current = {"operations_per_second": 400, "avg_latency": 150}

        regression = benchmark.detect_regression(baseline, current, threshold=0.1)

        assert regression is not None
        assert regression["has_regression"] is True
        assert len(regression["regressions"]) > 0

    def test_calculate_performance_score(self) -> None:
        """Test performance score calculation."""
        from benchmark_performance import PerformanceBenchmark

        benchmark = PerformanceBenchmark()

        metrics = {
            "operations_per_second": 750,
            "avg_latency": 50,
            "p95_latency": 100,
            "error_rate": 0.01,
        }

        score = benchmark.calculate_performance_score(metrics)

        assert score is not None
        assert 0 <= score <= 100


class TestBenchmarkMetrics:
    """Test benchmark metric utilities."""

    def test_calculate_percentiles(self) -> None:
        """Test percentile calculation."""
        from benchmark_performance import calculate_percentiles

        values = list(range(1, 101))
        percentiles = calculate_percentiles(values)

        assert percentiles is not None
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

    def test_calculate_standard_deviation(self) -> None:
        """Test standard deviation calculation."""
        from benchmark_performance import calculate_std_dev

        values = [10, 20, 30, 40, 50]
        std_dev = calculate_std_dev(values)

        assert std_dev is not None
        assert std_dev > 0

    def test_calculate_coefficient_of_variation(self) -> None:
        """Test coefficient of variation calculation."""
        from benchmark_performance import calculate_cv

        values = [10, 20, 30, 40, 50]
        cv = calculate_cv(values)

        assert cv is not None
        assert cv > 0
