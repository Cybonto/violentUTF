# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for query performance analysis functionality."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import duckdb
import pytest
import sqlite3

# Add scripts directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts/performance-optimization"))

# Test fixtures and setup


@pytest.fixture
def temp_db_dir() -> Any:
    """Create temporary directory for test databases."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_sqlite_db(temp_db_dir: str) -> str:
    """Create sample SQLite database for testing."""
    db_path = os.path.join(temp_db_dir, "test.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create sample tables
    cursor.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )

    # Insert sample data
    for i in range(100):
        cursor.execute(
            "INSERT INTO users (username, email) VALUES (?, ?)",
            (f"user_{i}", f"user_{i}@example.com"),
        )

    for i in range(500):
        cursor.execute(
            "INSERT INTO sessions (user_id, token) VALUES (?, ?)",
            (i % 100 + 1, f"token_{i}"),
        )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def sample_duckdb_db(temp_db_dir: str) -> str:
    """Create sample DuckDB database for testing."""
    db_path = os.path.join(temp_db_dir, "test.duckdb")
    conn = duckdb.connect(db_path)

    # Create sample tables
    conn.execute(
        """
        CREATE TABLE generators (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            parameters TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    conn.execute(
        """
        CREATE TABLE datasets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            configuration TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    # Insert sample data
    for i in range(50):
        conn.execute(
            "INSERT INTO generators VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (f"gen_{i}", f"Generator {i}", "openai", "{}"),
        )

    for i in range(100):
        conn.execute(
            "INSERT INTO datasets VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (f"ds_{i}", f"Dataset {i}", "custom", "{}"),
        )

    conn.close()
    return db_path


# Test classes


class TestQueryPerformanceAnalyzer:
    """Test query performance analysis functionality."""

    def test_analyzer_initialization(self) -> None:
        """Test analyzer can be initialized with database connections."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        assert analyzer is not None
        assert hasattr(analyzer, "analyze_sqlite")
        assert hasattr(analyzer, "analyze_duckdb")
        assert hasattr(analyzer, "analyze_postgres")

    def test_analyze_sqlite_queries(self, sample_sqlite_db: str) -> None:
        """Test SQLite query analysis returns performance metrics."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        results = analyzer.analyze_sqlite(sample_sqlite_db)

        assert results is not None
        assert "queries" in results
        assert "metrics" in results
        assert len(results["queries"]) > 0

        # Check metrics structure
        metrics = results["metrics"]
        assert "total_queries" in metrics
        assert "avg_execution_time" in metrics
        assert "slow_queries" in metrics

    def test_analyze_duckdb_queries(self, sample_duckdb_db: str) -> None:
        """Test DuckDB query analysis returns performance metrics."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        results = analyzer.analyze_duckdb(sample_duckdb_db)

        assert results is not None
        assert "queries" in results
        assert "metrics" in results
        assert len(results["queries"]) > 0

    def test_identify_slow_queries(self, sample_sqlite_db: str) -> None:
        """Test identification of slow queries."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        results = analyzer.analyze_sqlite(sample_sqlite_db)

        slow_queries = results["metrics"]["slow_queries"]
        assert isinstance(slow_queries, list)

    def test_execution_plan_analysis(self, sample_sqlite_db: str) -> None:
        """Test execution plan generation for queries."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        query = "SELECT * FROM users WHERE username = 'user_1'"
        plan = analyzer.get_execution_plan(sample_sqlite_db, query, "sqlite")

        assert plan is not None
        assert isinstance(plan, (str, dict))

    def test_generate_performance_report(
        self, sample_sqlite_db: str, temp_db_dir: str
    ) -> None:
        """Test performance report generation."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        results = analyzer.analyze_sqlite(sample_sqlite_db)

        report_path = os.path.join(temp_db_dir, "performance_report.json")
        analyzer.generate_report(results, report_path)

        assert os.path.exists(report_path)

    def test_baseline_metrics_collection(self, sample_sqlite_db: str) -> None:
        """Test baseline metrics collection."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        baseline = analyzer.collect_baseline_metrics(sample_sqlite_db, "sqlite")

        assert baseline is not None
        assert "timestamp" in baseline
        assert "database_size" in baseline
        assert "table_count" in baseline
        assert "row_counts" in baseline

    def test_compare_performance_metrics(self) -> None:
        """Test comparison of before/after performance metrics."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()

        baseline = {
            "avg_execution_time": 100.0,
            "total_queries": 50,
            "slow_queries": [{"query": "test", "time": 500}],
        }

        current = {
            "avg_execution_time": 75.0,
            "total_queries": 50,
            "slow_queries": [{"query": "test", "time": 350}],
        }

        comparison = analyzer.compare_metrics(baseline, current)

        assert comparison is not None
        assert "improvement_percentage" in comparison
        assert comparison["improvement_percentage"] > 0

    def test_handle_missing_database(self) -> None:
        """Test handling of missing database file."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()

        with pytest.raises((FileNotFoundError, ValueError)):
            analyzer.analyze_sqlite("/nonexistent/path/to/db.db")

    def test_handle_invalid_query(self, sample_sqlite_db: str) -> None:
        """Test handling of invalid SQL queries."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()

        with pytest.raises((sqlite3.Error, ValueError)):
            analyzer.get_execution_plan(
                sample_sqlite_db, "INVALID SQL SYNTAX", "sqlite"
            )

    def test_concurrent_query_analysis(self, sample_sqlite_db: str) -> None:
        """Test concurrent query analysis."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        results = analyzer.analyze_sqlite(sample_sqlite_db, concurrent=True)

        assert results is not None
        assert "queries" in results

    def test_memory_usage_tracking(self, sample_sqlite_db: str) -> None:
        """Test memory usage tracking during analysis."""
        from analyze_query_performance import QueryPerformanceAnalyzer

        analyzer = QueryPerformanceAnalyzer()
        results = analyzer.analyze_sqlite(sample_sqlite_db, track_memory=True)

        assert results is not None
        if "memory_usage" in results:
            assert isinstance(results["memory_usage"], (int, float))


class TestQueryMetrics:
    """Test query metrics calculation."""

    def test_calculate_percentiles(self) -> None:
        """Test percentile calculation for query times."""
        from analyze_query_performance import calculate_percentiles

        query_times = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        percentiles = calculate_percentiles(query_times)

        assert percentiles is not None
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles
        assert percentiles["p50"] <= percentiles["p95"]
        assert percentiles["p95"] <= percentiles["p99"]

    def test_calculate_query_statistics(self) -> None:
        """Test query statistics calculation."""
        from analyze_query_performance import calculate_query_statistics

        queries = [
            {"time": 10, "query": "SELECT * FROM users"},
            {"time": 20, "query": "SELECT * FROM users"},
            {"time": 30, "query": "SELECT * FROM sessions"},
        ]

        stats = calculate_query_statistics(queries)

        assert stats is not None
        assert "avg_time" in stats
        assert "min_time" in stats
        assert "max_time" in stats
        assert stats["min_time"] <= stats["avg_time"] <= stats["max_time"]
