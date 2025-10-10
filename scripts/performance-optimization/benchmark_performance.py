# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Performance benchmarking tool for database optimization validation."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from typing import Any, Dict, List

from utils.db_connections import DatabaseConnection
from utils.metrics_collector import MetricsCollector
from utils.report_generator import ReportGenerator


class PerformanceBenchmark:
    """Benchmark database performance."""

    def __init__(self: PerformanceBenchmark) -> None:
        """Initialize performance benchmark."""
        self.metrics_collector = MetricsCollector()
        self.report_generator = ReportGenerator()

    def run_benchmark(self: PerformanceBenchmark, db_path: str, db_type: str, queries: List[str]) -> Dict[str, Any]:
        """Run performance benchmark.

        Args:
            db_path: Path to database
            db_type: Type of database
            queries: List of queries to benchmark

        Returns:
            Benchmark results
        """
        results: Dict[str, Any] = {"queries": [], "metrics": {}}

        with DatabaseConnection(db_path, db_type) as conn:
            for query in queries:
                timing = self.metrics_collector.measure_query_time(conn, query, iterations=10)
                results["queries"].append({"query": query, "timing": timing})

            # Calculate overall metrics
            avg_times = [q["timing"]["avg_time_ms"] for q in results["queries"]]
            results["metrics"] = {
                "avg_query_time": statistics.mean(avg_times) if avg_times else 0,
                "total_queries": len(queries),
            }

        return results

    def measure_throughput(
        self: PerformanceBenchmark, db_path: str, db_type: str, query: str, duration: int = 10
    ) -> Dict[str, Any]:
        """Measure query throughput.

        Args:
            db_path: Path to database
            db_type: Type of database
            query: Query to benchmark
            duration: Duration in seconds

        Returns:
            Throughput metrics
        """
        start_time = time.time()
        operations = 0

        with DatabaseConnection(db_path, db_type) as conn:
            while time.time() - start_time < duration:
                conn.execute(query, (1,))
                operations += 1

        elapsed = time.time() - start_time
        ops_per_second = operations / elapsed

        return {"operations_per_second": ops_per_second, "total_operations": operations, "duration": elapsed}

    def measure_latency(
        self: PerformanceBenchmark, db_path: str, db_type: str, query: str, iterations: int = 100
    ) -> Dict[str, Any]:
        """Measure query latency.

        Args:
            db_path: Path to database
            db_type: Type of database
            query: Query to benchmark
            iterations: Number of iterations

        Returns:
            Latency metrics
        """
        latencies = []

        with DatabaseConnection(db_path, db_type) as conn:
            for _ in range(iterations):
                start = time.perf_counter()
                conn.execute(query)
                end = time.perf_counter()
                latencies.append((end - start) * 1000)  # Convert to ms

        return {
            "avg_latency": statistics.mean(latencies),
            "min_latency": min(latencies),
            "max_latency": max(latencies),
            "p95_latency": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99_latency": sorted(latencies)[int(len(latencies) * 0.99)],
        }

    def run_concurrent_benchmark(
        self: PerformanceBenchmark,
        db_path: str,
        db_type: str,
        query: str,
        concurrent_users: int = 10,
        duration: int = 10,
    ) -> Dict[str, Any]:
        """Run concurrent query benchmark.

        Args:
            db_path: Path to database
            db_type: Type of database
            query: Query to benchmark
            concurrent_users: Number of concurrent users
            duration: Duration in seconds

        Returns:
            Concurrent benchmark results
        """
        # Simplified implementation - single-threaded for now
        start_time = time.time()
        operations = 0

        with DatabaseConnection(db_path, db_type) as conn:
            while time.time() - start_time < duration:
                for _ in range(concurrent_users):
                    conn.execute(query, (1,))
                    operations += 1

        elapsed = time.time() - start_time

        return {
            "concurrent_users": concurrent_users,
            "total_operations": operations,
            "operations_per_second": operations / elapsed,
            "duration": elapsed,
        }

    def run_load_test(
        self: PerformanceBenchmark,
        db_path: str,
        db_type: str,
        queries: List[str],
        ramp_up_users: int = 10,
        duration: int = 60,
    ) -> Dict[str, Any]:
        """Run load test.

        Args:
            db_path: Path to database
            db_type: Type of database
            queries: List of queries to test
            ramp_up_users: Maximum concurrent users
            duration: Duration in seconds

        Returns:
            Load test results
        """
        results = {
            "load_test_results": [],
            "max_concurrent_users": ramp_up_users,
        }

        # Simplified implementation
        for users in range(1, ramp_up_users + 1, 2):
            test_result = self.run_concurrent_benchmark(db_path, db_type, queries[0], users, duration // 10)
            results["load_test_results"].append(test_result)

        return results

    def run_stress_test(
        self: PerformanceBenchmark,
        db_path: str,
        db_type: str,
        queries: List[str],
        max_users: int = 100,
        duration: int = 60,
    ) -> Dict[str, Any]:
        """Run stress test.

        Args:
            db_path: Path to database
            db_type: Type of database
            queries: List of queries to test
            max_users: Maximum users to test
            duration: Duration in seconds

        Returns:
            Stress test results
        """
        # Simplified implementation
        throughput_results = []

        for users in range(10, max_users + 1, 10):
            result = self.run_concurrent_benchmark(db_path, db_type, queries[0], users, duration // 10)
            throughput_results.append({"users": users, "ops_per_second": result["operations_per_second"]})

        # Find breaking point (where throughput starts declining)
        max_throughput = max([r["ops_per_second"] for r in throughput_results])
        breaking_point = next(
            (r["users"] for r in throughput_results if r["ops_per_second"] < max_throughput * 0.9), max_users
        )

        return {"breaking_point": breaking_point, "max_throughput": max_throughput, "results": throughput_results}

    def compare_results(
        self: PerformanceBenchmark, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare benchmark results.

        Args:
            baseline: Baseline metrics
            current: Current metrics

        Returns:
            Comparison results
        """
        comparison = {"improvement": {}}

        # Compare each metric
        for key in baseline:
            if key in current and isinstance(baseline[key], (int, float)):
                baseline_val = baseline[key]
                current_val = current[key]

                if baseline_val != 0:
                    # For latency, lower is better (negative improvement is good)
                    # For throughput, higher is better (positive improvement is good)
                    improvement = ((current_val - baseline_val) / baseline_val) * 100
                    comparison["improvement"][key] = improvement

        return comparison

    def detect_regression(
        self: PerformanceBenchmark,
        baseline: Dict[str, Any],
        current: Dict[str, Any],
        threshold: float = 0.1,
    ) -> Dict[str, Any]:
        """Detect performance regression.

        Args:
            baseline: Baseline metrics
            current: Current metrics
            threshold: Regression threshold (10% by default)

        Returns:
            Regression detection results
        """
        regressions = []

        for key in baseline:
            if key in current and isinstance(baseline[key], (int, float)):
                baseline_val = baseline[key]
                current_val = current[key]

                if baseline_val != 0:
                    change = (current_val - baseline_val) / baseline_val

                    # For ops_per_second, negative change is regression
                    # For latency, positive change is regression
                    if "latency" in key.lower() or "time" in key.lower():
                        if change > threshold:
                            regressions.append({"metric": key, "change_percent": change * 100, "type": "latency"})
                    else:
                        if change < -threshold:
                            regressions.append({"metric": key, "change_percent": change * 100, "type": "throughput"})

        return {"has_regression": len(regressions) > 0, "regressions": regressions}

    def calculate_performance_score(self: PerformanceBenchmark, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score.

        Args:
            metrics: Performance metrics

        Returns:
            Performance score (0-100)
        """
        score = 100.0

        # Penalize for high latency
        if "avg_latency" in metrics:
            latency = metrics["avg_latency"]
            if latency > 100:
                score -= min(50, (latency - 100) / 10)

        # Penalize for low throughput
        if "operations_per_second" in metrics:
            ops = metrics["operations_per_second"]
            if ops < 100:
                score -= min(30, (100 - ops) / 5)

        # Penalize for errors
        if "error_rate" in metrics:
            error_rate = metrics["error_rate"]
            score -= error_rate * 100

        return max(0, score)

    def save_baseline(self: PerformanceBenchmark, metrics: Dict[str, Any], output_path: str) -> None:
        """Save baseline metrics.

        Args:
            metrics: Baseline metrics
            output_path: Path to save baseline
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

    def load_baseline(self: PerformanceBenchmark, baseline_path: str) -> Dict[str, Any]:
        """Load baseline metrics.

        Args:
            baseline_path: Path to baseline file

        Returns:
            Baseline metrics
        """
        with open(baseline_path, encoding="utf-8") as f:
            return json.load(f)

    def generate_report(self: PerformanceBenchmark, results: Dict[str, Any], output_path: str) -> None:
        """Generate benchmark report.

        Args:
            results: Benchmark results
            output_path: Path to save report
        """
        self.report_generator.generate_json_report(results, output_path)


def calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Calculate percentiles.

    Args:
        values: List of values

    Returns:
        Percentile metrics
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


def calculate_std_dev(values: List[float]) -> float:
    """Calculate standard deviation.

    Args:
        values: List of values

    Returns:
        Standard deviation
    """
    return statistics.stdev(values) if len(values) > 1 else 0


def calculate_cv(values: List[float]) -> float:
    """Calculate coefficient of variation.

    Args:
        values: List of values

    Returns:
        Coefficient of variation
    """
    if not values:
        return 0

    mean = statistics.mean(values)
    if mean == 0:
        return 0

    std_dev = calculate_std_dev(values)
    return (std_dev / mean) * 100


def main() -> None:
    """Benchmark database performance."""
    parser = argparse.ArgumentParser(description="Benchmark database performance")
    parser.add_argument("--db-path", required=True, help="Path to database")
    parser.add_argument("--db-type", default="sqlite", help="Database type")
    parser.add_argument("--compare-baseline", help="Path to baseline for comparison")
    parser.add_argument("--output", default="benchmark_report.json", help="Output report path")

    args = parser.parse_args()

    benchmark = PerformanceBenchmark()

    print(f"Running benchmarks on: {args.db_path}")

    # Example queries
    queries = ["SELECT * FROM users LIMIT 10", "SELECT COUNT(*) FROM users"]

    results = benchmark.run_benchmark(args.db_path, args.db_type, queries)

    print("\nBenchmark complete:")
    print(f"  Total queries: {results['metrics']['total_queries']}")
    print(f"  Average query time: {results['metrics']['avg_query_time']:.2f} ms")

    # Compare with baseline if provided
    if args.compare_baseline and os.path.exists(args.compare_baseline):
        baseline = benchmark.load_baseline(args.compare_baseline)
        comparison = benchmark.compare_results(baseline, results["metrics"])

        print("\nComparison with baseline:")
        for metric, improvement in comparison["improvement"].items():
            print(f"  {metric}: {improvement:+.2f}%")

    # Generate report
    benchmark.generate_report(results, args.output)
    print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
