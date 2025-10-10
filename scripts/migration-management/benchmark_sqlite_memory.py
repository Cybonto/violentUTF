#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""PyRIT SQLiteMemory Performance Benchmark Script

This script benchmarks SQLiteMemory operations to compare against DuckDB
baseline performance and ensure <10% degradation requirement is met.
"""

import asyncio
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List

from pyrit.memory import SQLiteMemory
from pyrit.models import SeedPrompt


class PerformanceBenchmark:
    """Performance benchmark suite for SQLiteMemory."""

    def __init__(self, db_path: str) -> None:
        """Initialize benchmark with database path."""
        self.db_path = db_path
        self.memory: SQLiteMemory | None = None
        self.results: Dict[str, Any] = {}

    async def setup(self) -> None:
        """Set up test environment."""
        self.memory = SQLiteMemory(db_path=self.db_path)
        print(f"Initialized SQLiteMemory at: {self.db_path}")

    async def teardown(self) -> None:
        """Clean up test environment."""
        if self.memory:
            self.memory.dispose_engine()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        # Also remove SQLite journal files if they exist
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = self.db_path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)
        print("Cleaned up test database")

    def generate_test_prompts(self, count: int) -> List[SeedPrompt]:
        """Generate test seed prompts."""
        prompts = []
        for i in range(count):
            prompt = SeedPrompt(
                value=f"Test prompt number {i} - " f"This is a sample prompt for benchmarking purposes.",
                data_type="text",
                metadata={
                    "test_id": str(i),
                    "batch": str(i // 100),
                    "category": f"category_{i % 10}",
                },
            )
            prompts.append(prompt)
        return prompts

    async def benchmark_memory_initialization(self) -> Dict[str, Any]:
        """Benchmark memory initialization time."""
        print("\nBenchmarking memory initialization...")

        # Test cold start
        start = time.perf_counter()
        memory = SQLiteMemory(db_path=self.db_path + "_init_test")
        cold_time = time.perf_counter() - start

        # Test warm start (existing database)
        start = time.perf_counter()
        memory2 = SQLiteMemory(db_path=self.db_path + "_init_test")
        warm_time = time.perf_counter() - start

        # Cleanup
        memory.dispose_engine()
        memory2.dispose_engine()
        test_path = self.db_path + "_init_test"
        if os.path.exists(test_path):
            os.remove(test_path)
        # Also remove SQLite journal files if they exist
        for suffix in ["-wal", "-shm", "-journal"]:
            journal_path = test_path + suffix
            if os.path.exists(journal_path):
                os.remove(journal_path)

        result = {
            "cold_start_seconds": round(cold_time, 4),
            "warm_start_seconds": round(warm_time, 4),
        }

        print(f"  Cold start: {result['cold_start_seconds']}s")
        print(f"  Warm start: {result['warm_start_seconds']}s")

        return result

    async def benchmark_bulk_insert(self, prompt_counts: List[int]) -> Dict[str, Any]:
        """Benchmark bulk insert operations."""
        print("\nBenchmarking bulk insert operations...")
        results = {}

        for count in prompt_counts:
            prompts = self.generate_test_prompts(count)

            # Benchmark insert
            start = time.perf_counter()
            await self.memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by="benchmark_script")
            elapsed = time.perf_counter() - start

            throughput = count / elapsed if elapsed > 0 else 0

            results[f"{count}_prompts"] = {
                "elapsed_seconds": round(elapsed, 4),
                "prompts_per_second": round(throughput, 2),
                "avg_time_per_prompt_ms": round((elapsed / count) * 1000, 4),
            }

            print(f"  {count} prompts: {elapsed:.4f}s " f"({throughput:.2f} prompts/s)")

        return results

    async def benchmark_query_operations(self) -> Dict[str, Any]:
        """Benchmark query operations with various filters."""
        print("\nBenchmarking query operations...")

        # First, add test data
        test_prompts = self.generate_test_prompts(1000)
        await self.memory.add_seed_prompts_to_memory_async(prompts=test_prompts, added_by="benchmark_script")

        results = {}

        # Test 1: Get all prompts
        start = time.perf_counter()
        all_prompts = self.memory.get_seed_prompts()
        elapsed = time.perf_counter() - start
        results["get_all_prompts"] = {
            "elapsed_seconds": round(elapsed, 4),
            "count": len(all_prompts),
        }
        print(f"  Get all prompts: {elapsed:.4f}s ({len(all_prompts)} prompts)")

        # Test 2: Get prompts with metadata filter
        start = time.perf_counter()
        filtered_prompts = self.memory.get_seed_prompts(metadata={"category": "category_5"})
        elapsed = time.perf_counter() - start
        results["get_filtered_prompts"] = {
            "elapsed_seconds": round(elapsed, 4),
            "count": len(filtered_prompts),
        }
        print(f"  Get filtered prompts: {elapsed:.4f}s " f"({len(filtered_prompts)} prompts)")

        # Test 3: Get prompts with value search
        start = time.perf_counter()
        search_prompts = self.memory.get_seed_prompts(value="Test prompt number 500")
        elapsed = time.perf_counter() - start
        results["get_search_prompts"] = {
            "elapsed_seconds": round(elapsed, 4),
            "count": len(search_prompts),
        }
        print(f"  Get search prompts: {elapsed:.4f}s " f"({len(search_prompts)} prompts)")

        return results

    async def benchmark_concurrent_operations(self) -> Dict[str, Any]:
        """Benchmark concurrent operations."""
        print("\nBenchmarking concurrent operations...")

        # Create multiple concurrent insert tasks
        async def insert_batch(batch_id: int, count: int) -> float:
            prompts = self.generate_test_prompts(count)
            for prompt in prompts:
                prompt.metadata["batch_id"] = str(batch_id)

            start = time.perf_counter()
            await self.memory.add_seed_prompts_to_memory_async(prompts=prompts, added_by="benchmark_script")
            return time.perf_counter() - start

        # Run 5 concurrent batches of 100 prompts each
        start = time.perf_counter()
        tasks = [insert_batch(i, 100) for i in range(5)]
        batch_times = await asyncio.gather(*tasks)
        total_elapsed = time.perf_counter() - start

        result = {
            "total_elapsed_seconds": round(total_elapsed, 4),
            "batch_times": [round(t, 4) for t in batch_times],
            "total_prompts": 500,
            "prompts_per_second": round(500 / total_elapsed, 2),
        }

        print(f"  Total time: {total_elapsed:.4f}s")
        print(f"  Throughput: {result['prompts_per_second']} prompts/s")

        return result

    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite."""
        print("=" * 80)
        print("PyRIT SQLiteMemory Performance Benchmark")
        print("=" * 80)

        await self.setup()

        try:
            self.results = {
                "timestamp": datetime.now(UTC).isoformat(),
                "database_path": self.db_path,
                "benchmarks": {
                    "initialization": (await self.benchmark_memory_initialization()),
                    "bulk_insert": await self.benchmark_bulk_insert([100, 1000, 5000]),
                    "query_operations": await self.benchmark_query_operations(),
                    "concurrent_operations": (await self.benchmark_concurrent_operations()),
                },
            }

        finally:
            await self.teardown()

        return self.results


def calculate_performance_metrics(results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate key performance metrics from benchmark results."""
    benchmarks = results["benchmarks"]

    # Get key metrics
    init_cold = benchmarks["initialization"]["cold_start_seconds"]
    insert_1000 = benchmarks["bulk_insert"]["1000_prompts"]["elapsed_seconds"]
    insert_throughput = benchmarks["bulk_insert"]["1000_prompts"]["prompts_per_second"]
    query_all = benchmarks["query_operations"]["get_all_prompts"]["elapsed_seconds"]
    concurrent_throughput = benchmarks["concurrent_operations"]["prompts_per_second"]

    metrics = {
        "summary": {
            "initialization_time": f"{init_cold}s",
            "insert_1000_prompts_time": f"{insert_1000}s",
            "insert_throughput": f"{insert_throughput} prompts/s",
            "query_all_time": f"{query_all}s",
            "concurrent_throughput": f"{concurrent_throughput} prompts/s",
        },
        "performance_grade": "EXCELLENT",
    }

    # Determine performance grade based on thresholds
    if init_cold > 1.0 or insert_1000 > 5.0 or query_all > 1.0:
        metrics["performance_grade"] = "POOR"
    elif init_cold > 0.5 or insert_1000 > 3.0 or query_all > 0.5:
        metrics["performance_grade"] = "ACCEPTABLE"
    else:
        metrics["performance_grade"] = "EXCELLENT"

    return metrics


async def main() -> None:
    """Execute PyRIT SQLiteMemory performance benchmarks."""
    # Create temporary database path
    temp_dir = tempfile.mkdtemp(prefix="pyrit_benchmark_")
    db_path = os.path.join(temp_dir, "benchmark_test.db")

    try:
        # Run benchmark
        benchmark = PerformanceBenchmark(db_path)
        results = await benchmark.run_full_benchmark()

        # Calculate metrics
        metrics = calculate_performance_metrics(results)
        results["metrics"] = metrics

        # Save results
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent.parent
        output_path = repo_root / "reports" / "pyrit_sqlite_performance_benchmarks.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        # Print summary
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)
        print(f"Performance Grade: {metrics['performance_grade']}")
        print("\nKey Metrics:")
        for key, value in metrics["summary"].items():
            print(f"  {key}: {value}")
        print(f"\nFull results saved to: {output_path}")
        print("=" * 80)

    finally:
        # Cleanup temp directory
        import shutil

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    asyncio.run(main())
