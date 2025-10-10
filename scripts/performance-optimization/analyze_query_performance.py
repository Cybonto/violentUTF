# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Query performance analysis tool for database optimization."""

from __future__ import annotations

import argparse
import os
import statistics
import time
from typing import Any, Dict, List, Optional

from utils.db_connections import DatabaseConnection
from utils.metrics_collector import MetricsCollector
from utils.report_generator import ReportGenerator


class QueryPerformanceAnalyzer:
    """Analyze query performance across database systems."""

    def __init__(self: QueryPerformanceAnalyzer) -> None:
        """Initialize query performance analyzer."""
        self.metrics_collector = MetricsCollector()
        self.report_generator = ReportGenerator()

    def analyze_sqlite(
        self: QueryPerformanceAnalyzer,
        db_path: str,
        concurrent: bool = False,
        track_memory: bool = False,
    ) -> Dict[str, Any]:
        """Analyze SQLite database query performance.

        Args:
            db_path: Path to SQLite database
            concurrent: Whether to analyze concurrent queries
            track_memory: Whether to track memory usage

        Returns:
            Dictionary containing analysis results
        """
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")

        results: Dict[str, Any] = {"queries": [], "metrics": {}}

        with DatabaseConnection(db_path, "sqlite") as conn:
            # Collect baseline stats
            stats = self.metrics_collector.collect_database_stats(db_path, "sqlite")
            results["baseline_stats"] = stats

            # Analyze common query patterns
            queries = self._get_common_queries(conn, "sqlite")
            results["queries"] = queries

            # Calculate metrics
            if queries:
                query_times = [q["time"] for q in queries if "time" in q]
                results["metrics"] = {
                    "total_queries": len(queries),
                    "avg_execution_time": (statistics.mean(query_times) if query_times else 0),
                    "slow_queries": [q for q in queries if q.get("time", 0) > 100],
                }

        return results

    # DuckDB analysis removed - PyRIT migrated to SQLite in v0.10.0rc0 (issue #269)

    def analyze_postgres(self: QueryPerformanceAnalyzer, connection_string: str) -> Dict[str, Any]:
        """Analyze PostgreSQL database query performance.

        Args:
            connection_string: PostgreSQL connection string

        Returns:
            Dictionary containing analysis results
        """
        # Placeholder for PostgreSQL analysis
        return {
            "queries": [],
            "metrics": {"total_queries": 0, "avg_execution_time": 0, "slow_queries": []},
        }

    def _get_common_queries(
        self: QueryPerformanceAnalyzer, conn: DatabaseConnection, db_type: str
    ) -> List[Dict[str, Any]]:
        """Get common queries for analysis.

        Args:
            conn: Database connection
            db_type: Type of database

        Returns:
            List of queries with performance metrics
        """
        queries = []

        # Get table list
        tables = self.metrics_collector.get_table_list(conn)

        # Test simple SELECT queries for each table
        for table in tables:
            query = f'SELECT * FROM "{table}" LIMIT 10'  # nosec B608
            try:
                timing = self.metrics_collector.measure_query_time(conn, query)
                queries.append(
                    {
                        "query": query,
                        "table": table,
                        "time": timing["avg_time_ms"],
                        "type": "select",
                    }
                )
            except Exception:
                pass

        return queries

    def get_execution_plan(self: QueryPerformanceAnalyzer, db_path: str, query: str, db_type: str) -> Optional[str]:
        """Get execution plan for a query.

        Args:
            db_path: Path to database
            query: SQL query
            db_type: Type of database

        Returns:
            Execution plan string
        """
        with DatabaseConnection(db_path, db_type) as conn:
            if db_type == "sqlite":
                explain_query = f"EXPLAIN QUERY PLAN {query}"
                results = conn.fetchall(explain_query)
                return "\n".join([str(row) for row in results])
            # DuckDB support removed - PyRIT migrated to SQLite in v0.10.0rc0 (issue #269)

        return None

    def collect_baseline_metrics(self: QueryPerformanceAnalyzer, db_path: str, db_type: str) -> Dict[str, Any]:
        """Collect baseline performance metrics.

        Args:
            db_path: Path to database
            db_type: Type of database

        Returns:
            Baseline metrics dictionary
        """
        stats = self.metrics_collector.collect_database_stats(db_path, db_type)
        stats["timestamp"] = time.time()
        stats["database_size"] = stats.get("file_size_mb", 0)
        stats["table_count"] = len(stats.get("tables", []))

        return stats

    def compare_metrics(
        self: QueryPerformanceAnalyzer, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare baseline and current performance metrics.

        Args:
            baseline: Baseline metrics
            current: Current metrics

        Returns:
            Comparison results
        """
        comparison = {}

        # Compare average execution time
        if "avg_execution_time" in baseline and "avg_execution_time" in current:
            baseline_time = baseline["avg_execution_time"]
            current_time = current["avg_execution_time"]

            if baseline_time > 0:
                improvement = ((baseline_time - current_time) / baseline_time) * 100
                comparison["improvement_percentage"] = improvement

        # Compare slow query counts
        if "slow_queries" in baseline and "slow_queries" in current:
            baseline_slow = len(baseline["slow_queries"])
            current_slow = len(current["slow_queries"])
            comparison["slow_query_reduction"] = baseline_slow - current_slow

        return comparison

    def generate_report(self: QueryPerformanceAnalyzer, results: Dict[str, Any], output_path: str) -> None:
        """Generate performance analysis report.

        Args:
            results: Analysis results
            output_path: Path to save report
        """
        self.report_generator.generate_json_report(results, output_path)


def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Calculate percentiles for a list of values.

    Args:
        values: List of numeric values

    Returns:
        Dictionary with p50, p95, p99 percentiles
    """
    if not values:
        return {"p50": 0, "p95": 0, "p99": 0}

    sorted_values = sorted(values)
    n = len(sorted_values)

    return {
        "p50": sorted_values[int(n * 0.50)],
        "p95": sorted_values[int(n * 0.95)] if n > 1 else sorted_values[0],
        "p99": sorted_values[int(n * 0.99)] if n > 2 else sorted_values[0],
    }


def calculate_query_statistics(queries: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate statistics for query execution times.

    Args:
        queries: List of query results

    Returns:
        Dictionary with min, max, avg times
    """
    times = [q.get("time", 0) for q in queries]

    if not times:
        return {"avg_time": 0, "min_time": 0, "max_time": 0}

    return {
        "avg_time": statistics.mean(times),
        "min_time": min(times),
        "max_time": max(times),
    }


def main() -> None:
    """Analyze database query performance."""
    parser = argparse.ArgumentParser(description="Analyze database query performance")
    parser.add_argument("--all-databases", action="store_true", help="Analyze all databases")
    parser.add_argument("--db-path", help="Path to specific database")
    parser.add_argument("--db-type", default="sqlite", help="Database type")
    parser.add_argument("--output", default="performance_report.json", help="Output report path")

    args = parser.parse_args()

    analyzer = QueryPerformanceAnalyzer()

    if args.all_databases:
        # Analyze all databases in app_data
        app_data_dir = os.path.join(os.getcwd(), "app_data")

        print("Analyzing all databases...")

        # Find SQLite databases
        for root, _, files in os.walk(app_data_dir):
            for file in files:
                if file.endswith(".db"):
                    db_path = os.path.join(root, file)
                    print(f"\nAnalyzing: {db_path}")

                    try:
                        results = analyzer.analyze_sqlite(db_path)
                        output_name = f"report_{os.path.basename(db_path)}.json"
                        output_path = os.path.join("reports", output_name)
                        analyzer.generate_report(results, output_path)
                        print(f"Report saved to: {output_path}")
                    except Exception as e:
                        print(f"Error analyzing {db_path}: {e}")

    elif args.db_path:
        # Analyze specific database
        print(f"Analyzing database: {args.db_path}")

        if args.db_type == "sqlite":
            results = analyzer.analyze_sqlite(args.db_path)
        elif args.db_type == "postgres":
            # PostgreSQL analysis not yet implemented
            print("PostgreSQL analysis not yet implemented")
            return
        else:
            print(f"Unsupported database type: {args.db_type}")
            print("Supported types: sqlite")
            return

        analyzer.generate_report(results, args.output)
        print(f"Report saved to: {args.output}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
