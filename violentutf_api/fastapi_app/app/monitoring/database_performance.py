# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Database Performance Monitoring Module

Provides comprehensive database performance monitoring including query performance,
connection pooling efficiency, transaction monitoring, and database scalability testing.

Key Components:
- DatabasePerformanceMonitor: Core database performance monitoring
- QueryPerformanceTracker: Individual query performance analysis
- ConnectionPoolMonitor: Database connection pool efficiency monitoring
- TransactionMonitor: Transaction performance and rollback tracking

SECURITY: All monitoring data is for defensive security research only.
"""

import logging
import sqlite3
import statistics
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import psutil


class QueryType(Enum):
    """Database query type classifications"""

    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    DROP = "drop"
    INDEX = "index"
    TRANSACTION = "transaction"


class PerformanceTier(Enum):
    """Database performance tier classifications"""

    EXCELLENT = "excellent"  # <10ms query, <100 concurrent
    GOOD = "good"  # <100ms query, <500 concurrent
    ACCEPTABLE = "acceptable"  # <1000ms query, <1000 concurrent
    POOR = "poor"  # <5000ms query, <2000 concurrent
    CRITICAL = "critical"  # >5000ms query, >2000 concurrent


@dataclass
class QueryPerformanceMetrics:
    """Individual database query performance metrics"""

    query_id: str
    query_type: QueryType
    query_text: str
    execution_time_ms: float
    rows_affected: int
    rows_returned: int
    connection_time_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    connection_pool_size: int = 0
    transaction_id: Optional[str] = None

    @property
    def performance_tier(self) -> PerformanceTier:
        """Determine query performance tier"""
        if self.execution_time_ms < 10:
            return PerformanceTier.EXCELLENT
        elif self.execution_time_ms < 100:
            return PerformanceTier.GOOD
        elif self.execution_time_ms < 1000:
            return PerformanceTier.ACCEPTABLE
        elif self.execution_time_ms < 5000:
            return PerformanceTier.POOR
        else:
            return PerformanceTier.CRITICAL


@dataclass
class DatabaseLoadMetrics:
    """Database load testing metrics"""

    test_id: str
    concurrent_connections: int
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_query_time_ms: float
    max_query_time_ms: float
    min_query_time_ms: float
    queries_per_second: float
    connection_errors: int
    deadlocks: int
    timeouts: int
    memory_usage_peak_mb: float
    cpu_usage_peak_percent: float
    test_duration_seconds: float
    timestamp: datetime


class QueryPerformanceTracker:
    """Track individual query performance and analysis"""

    def __init__(self, max_queries: int = 1000) -> None:
        """Initialize QueryPerformanceTracker.

        Args:
            max_queries: Maximum number of query metrics to keep in memory.
                        Defaults to 1000.
        """
        self.max_queries = max_queries
        self.query_metrics: List[QueryPerformanceMetrics] = []
        self.query_stats: Dict[QueryType, Dict[str, Any]] = {}

    def record_query_performance(
        self,
        query_text: str,
        execution_time_ms: float,
        rows_affected: int = 0,
        rows_returned: int = 0,
        connection_time_ms: float = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ) -> QueryPerformanceMetrics:
        """Record performance metrics for a database query"""
        # Determine query type
        query_type = self._determine_query_type(query_text)

        # Get system metrics
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024
        cpu_usage = process.cpu_percent(interval=0.1)

        metrics = QueryPerformanceMetrics(
            query_id=f"query_{int(time.time() * 1000)}",
            query_type=query_type,
            query_text=query_text[:200],  # Truncate long queries
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            rows_returned=rows_returned,
            connection_time_ms=connection_time_ms,
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            success=success,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc),
            transaction_id=transaction_id,
        )

        self.query_metrics.append(metrics)

        # Maintain size limit
        if len(self.query_metrics) > self.max_queries:
            self.query_metrics = self.query_metrics[-self.max_queries // 2 :]

        # Update query type statistics
        self._update_query_stats(query_type, metrics)

        return metrics

    def _determine_query_type(self, query_text: str) -> QueryType:
        """Determine query type from SQL text"""
        query_lower = query_text.lower().strip()

        if query_lower.startswith("select"):
            return QueryType.SELECT
        elif query_lower.startswith("insert"):
            return QueryType.INSERT
        elif query_lower.startswith("update"):
            return QueryType.UPDATE
        elif query_lower.startswith("delete"):
            return QueryType.DELETE
        elif query_lower.startswith("create"):
            return QueryType.CREATE
        elif query_lower.startswith("drop"):
            return QueryType.DROP
        elif "index" in query_lower:
            return QueryType.INDEX
        elif any(word in query_lower for word in ["begin", "commit", "rollback"]):
            return QueryType.TRANSACTION
        else:
            return QueryType.SELECT  # Default

    def _update_query_stats(self, query_type: QueryType, metrics: QueryPerformanceMetrics) -> None:
        """Update rolling statistics for query type"""
        if query_type not in self.query_stats:
            self.query_stats[query_type] = {
                "execution_times": [],
                "success_count": 0,
                "error_count": 0,
                "total_rows_affected": 0,
                "total_rows_returned": 0,
            }

        stats = self.query_stats[query_type]
        stats["execution_times"].append(metrics.execution_time_ms)

        # Keep only recent execution times
        if len(stats["execution_times"]) > 100:
            stats["execution_times"] = stats["execution_times"][-50:]

        if metrics.success:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1

        stats["total_rows_affected"] += metrics.rows_affected
        stats["total_rows_returned"] += metrics.rows_returned

    def get_query_type_summary(self, query_type: QueryType) -> Optional[Dict[str, Any]]:
        """Get performance summary for specific query type"""
        if query_type not in self.query_stats:
            return None

        stats = self.query_stats[query_type]
        execution_times = stats["execution_times"]

        if not execution_times:
            return None

        total_queries = stats["success_count"] + stats["error_count"]

        return {
            "query_type": query_type.value,
            "total_queries": total_queries,
            "success_rate": (stats["success_count"] / total_queries) * 100,
            "avg_execution_time_ms": statistics.mean(execution_times),
            "min_execution_time_ms": min(execution_times),
            "max_execution_time_ms": max(execution_times),
            "median_execution_time_ms": statistics.median(execution_times),
            "p95_execution_time_ms": self._percentile(execution_times, 95),
            "total_rows_affected": stats["total_rows_affected"],
            "total_rows_returned": stats["total_rows_returned"],
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of execution times"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class ConnectionPoolMonitor:
    """Monitor database connection pool efficiency and performance"""

    def __init__(self) -> None:
        """Initialize ConnectionPoolMonitor.

        Sets up monitoring for database connection pool efficiency,
        including connection events and pool status history.
        """
        self.connection_metrics: List[Dict[str, Any]] = []
        self.pool_status_history: List[Dict[str, Any]] = []

    def record_connection_event(
        self,
        event_type: str,  # acquire, release, timeout, error
        connection_time_ms: float,
        pool_size: int,
        active_connections: int,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Record connection pool event"""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "connection_time_ms": connection_time_ms,
            "pool_size": pool_size,
            "active_connections": active_connections,
            "success": success,
            "error_message": error_message,
            "pool_utilization_percent": (active_connections / pool_size) * 100 if pool_size > 0 else 0,
        }

        self.connection_metrics.append(event)

        # Maintain size limit
        if len(self.connection_metrics) > 1000:
            self.connection_metrics = self.connection_metrics[-500:]

    def get_pool_efficiency_summary(self) -> Dict[str, Any]:
        """Get connection pool efficiency summary"""
        if not self.connection_metrics:
            return {"message": "No connection metrics available"}

        # Calculate efficiency metrics
        acquire_events = [e for e in self.connection_metrics if e["event_type"] == "acquire"]
        timeout_events = [e for e in self.connection_metrics if e["event_type"] == "timeout"]
        error_events = [e for e in self.connection_metrics if e["event_type"] == "error"]

        if acquire_events:
            avg_acquisition_time = statistics.mean([e["connection_time_ms"] for e in acquire_events])
            max_acquisition_time = max([e["connection_time_ms"] for e in acquire_events])
            avg_utilization = statistics.mean([e["pool_utilization_percent"] for e in acquire_events])
        else:
            avg_acquisition_time = max_acquisition_time = avg_utilization = 0

        return {
            "total_connection_events": len(self.connection_metrics),
            "successful_acquisitions": len(acquire_events),
            "timeout_events": len(timeout_events),
            "error_events": len(error_events),
            "success_rate_percent": (len(acquire_events) / len(self.connection_metrics)) * 100,
            "avg_acquisition_time_ms": avg_acquisition_time,
            "max_acquisition_time_ms": max_acquisition_time,
            "avg_pool_utilization_percent": avg_utilization,
            "efficiency_score": max(0, 100 - (len(timeout_events) + len(error_events)) * 10),  # Simple scoring
        }


class TransactionMonitor:
    """Monitor database transaction performance and rollback patterns"""

    def __init__(self) -> None:
        """Initialize TransactionMonitor.

        Sets up transaction performance monitoring including active transaction
        tracking and completed transaction history.
        """
        self.transaction_metrics: Dict[str, Dict[str, Any]] = {}
        self.completed_transactions: List[Dict[str, Any]] = []

    def start_transaction(self, transaction_id: str) -> str:
        """Start monitoring a database transaction"""
        self.transaction_metrics[transaction_id] = {
            "transaction_id": transaction_id,
            "start_time": datetime.now(timezone.utc),
            "queries": [],
            "status": "active",
        }
        return transaction_id

    def record_transaction_query(self, transaction_id: str, query_metrics: QueryPerformanceMetrics) -> None:
        """Record a query within a transaction"""
        if transaction_id in self.transaction_metrics:
            self.transaction_metrics[transaction_id]["queries"].append(
                {
                    "query_id": query_metrics.query_id,
                    "query_type": query_metrics.query_type.value,
                    "execution_time_ms": query_metrics.execution_time_ms,
                    "rows_affected": query_metrics.rows_affected,
                    "success": query_metrics.success,
                }
            )

    def complete_transaction(
        self, transaction_id: str, committed: bool = True, error_message: Optional[str] = None
    ) -> None:
        """Complete transaction monitoring"""
        if transaction_id not in self.transaction_metrics:
            return

        transaction = self.transaction_metrics[transaction_id]
        transaction["end_time"] = datetime.now(timezone.utc)
        transaction["duration_seconds"] = (transaction["end_time"] - transaction["start_time"]).total_seconds()
        transaction["committed"] = committed
        transaction["error_message"] = error_message
        transaction["status"] = "committed" if committed else "rolled_back"

        # Calculate transaction metrics
        queries = transaction["queries"]
        if queries:
            transaction["total_queries"] = len(queries)
            transaction["successful_queries"] = sum(1 for q in queries if q["success"])
            transaction["total_execution_time_ms"] = sum(q["execution_time_ms"] for q in queries)
            transaction["total_rows_affected"] = sum(q["rows_affected"] for q in queries)

        self.completed_transactions.append(transaction.copy())
        del self.transaction_metrics[transaction_id]

        # Maintain size limit
        if len(self.completed_transactions) > 500:
            self.completed_transactions = self.completed_transactions[-250:]

    def get_transaction_summary(self) -> Dict[str, Any]:
        """Get transaction performance summary"""
        if not self.completed_transactions:
            return {"message": "No completed transactions"}

        committed_txns = [t for t in self.completed_transactions if t.get("committed", False)]
        rolled_back_txns = [t for t in self.completed_transactions if not t.get("committed", True)]

        if committed_txns:
            avg_duration = statistics.mean([t["duration_seconds"] for t in committed_txns])
            avg_queries_per_txn = statistics.mean([t.get("total_queries", 0) for t in committed_txns])
        else:
            avg_duration = avg_queries_per_txn = 0

        return {
            "total_transactions": len(self.completed_transactions),
            "committed_transactions": len(committed_txns),
            "rolled_back_transactions": len(rolled_back_txns),
            "commit_rate_percent": (len(committed_txns) / len(self.completed_transactions)) * 100,
            "avg_transaction_duration_seconds": avg_duration,
            "avg_queries_per_transaction": avg_queries_per_txn,
            "active_transactions": len(self.transaction_metrics),
        }


class DatabasePerformanceMonitor:
    """
    Comprehensive database performance monitoring system

    Monitors query performance, connection efficiency, transaction patterns,
    and provides database load testing capabilities.
    """

    def __init__(self, db_path: str = ":memory:", session_id: str = None) -> None:
        """Initialize DatabasePerformanceMonitor.

        Args:
            db_path: Path to database file. Defaults to in-memory database.
            session_id: Unique identifier for monitoring session.
                       Defaults to timestamp-based ID.
        """
        self.db_path = db_path
        self.session_id = session_id or f"db_perf_{int(time.time())}"
        self.query_tracker = QueryPerformanceTracker()
        self.connection_monitor = ConnectionPoolMonitor()
        self.transaction_monitor = TransactionMonitor()
        self.load_test_results: List[DatabaseLoadMetrics] = []
        self.logger = logging.getLogger(__name__)

    def measure_database_performance_under_load(
        self, concurrent_connections: int, queries_per_connection: int, test_duration_seconds: int = 60
    ) -> DatabaseLoadMetrics:
        """
        Test database performance under concurrent load

        Args:
            concurrent_connections: Number of concurrent database connections
            queries_per_connection: Number of queries per connection
            test_duration_seconds: Maximum test duration

        Returns:
            DatabaseLoadMetrics: Load test performance results
        """
        test_id = f"db_load_test_{int(time.time())}"
        start_time = datetime.now(timezone.utc)

        # Initialize metrics tracking
        total_queries = 0
        successful_queries = 0
        failed_queries = 0
        query_times = []
        connection_errors = 0
        deadlocks = 0
        timeouts = 0

        peak_memory_mb = 0
        peak_cpu_percent = 0

        # Create test database schema if needed
        self._setup_test_database()

        try:
            # Use threading to simulate concurrent connections
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def connection_worker(connection_id: int) -> Dict[str, Any]:
                """Worker function for each database connection"""
                worker_results = {
                    "connection_id": connection_id,
                    "queries_executed": 0,
                    "queries_successful": 0,
                    "queries_failed": 0,
                    "query_times": [],
                    "errors": [],
                    "deadlocks": 0,
                    "timeouts": 0,
                    "connection_errors": 0,
                }

                try:
                    # Create database connection
                    conn = sqlite3.connect(self.db_path, timeout=10)
                    conn.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency

                    end_time = time.time() + test_duration_seconds

                    for query_num in range(queries_per_connection):
                        if time.time() >= end_time:
                            break

                        # Generate test query
                        query = self._generate_test_query(query_num)

                        try:
                            query_start = time.time()
                            cursor = conn.execute(query)
                            rows = cursor.fetchall()
                            conn.commit()
                            query_time = (time.time() - query_start) * 1000

                            worker_results["query_times"].append(query_time)
                            worker_results["queries_successful"] += 1

                            # Record in query tracker
                            self.query_tracker.record_query_performance(
                                query_text=query, execution_time_ms=query_time, rows_returned=len(rows), success=True
                            )

                        except sqlite3.OperationalError as e:
                            if "database is locked" in str(e):
                                worker_results["deadlocks"] += 1
                            elif "timeout" in str(e):
                                worker_results["timeouts"] += 1
                            worker_results["errors"].append(str(e))
                            worker_results["queries_failed"] += 1

                        except Exception as e:
                            worker_results["errors"].append(str(e))
                            worker_results["queries_failed"] += 1

                        worker_results["queries_executed"] += 1

                        # Small delay to prevent overwhelming
                        time.sleep(0.01)

                    conn.close()

                except Exception as e:
                    worker_results["connection_errors"] += 1
                    worker_results["errors"].append(f"Connection error: {str(e)}")

                return worker_results

            # Execute concurrent connections
            with ThreadPoolExecutor(max_workers=concurrent_connections) as executor:
                # Monitor system resources during test
                def monitor_resources() -> None:
                    nonlocal peak_memory_mb, peak_cpu_percent
                    process = psutil.Process()

                    while time.time() < time.time() + test_duration_seconds:
                        memory_mb = process.memory_info().rss / 1024 / 1024
                        cpu_percent = process.cpu_percent(interval=1)

                        peak_memory_mb = max(peak_memory_mb, memory_mb)
                        peak_cpu_percent = max(peak_cpu_percent, cpu_percent)

                        time.sleep(1)

                # Start resource monitoring
                monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
                monitor_thread.start()

                # Submit connection workers
                futures = [executor.submit(connection_worker, conn_id) for conn_id in range(concurrent_connections)]

                # Collect results
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        total_queries += result["queries_executed"]
                        successful_queries += result["queries_successful"]
                        failed_queries += result["queries_failed"]
                        query_times.extend(result["query_times"])
                        deadlocks += result.get("deadlocks", 0)
                        timeouts += result.get("timeouts", 0)
                        connection_errors += result.get("connection_errors", 0)

                    except Exception:
                        connection_errors += 1

        except Exception:
            # Handle critical errors
            failed_queries += concurrent_connections * queries_per_connection

        end_time = datetime.now(timezone.utc)
        actual_duration = (end_time - start_time).total_seconds()

        # Calculate performance metrics
        if query_times:
            avg_query_time = statistics.mean(query_times)
            max_query_time = max(query_times)
            min_query_time = min(query_times)
        else:
            avg_query_time = max_query_time = min_query_time = 0

        queries_per_second = total_queries / actual_duration if actual_duration > 0 else 0

        load_metrics = DatabaseLoadMetrics(
            test_id=test_id,
            concurrent_connections=concurrent_connections,
            total_queries=total_queries,
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            avg_query_time_ms=avg_query_time,
            max_query_time_ms=max_query_time,
            min_query_time_ms=min_query_time,
            queries_per_second=queries_per_second,
            connection_errors=connection_errors,
            deadlocks=deadlocks,
            timeouts=timeouts,
            memory_usage_peak_mb=peak_memory_mb,
            cpu_usage_peak_percent=peak_cpu_percent,
            test_duration_seconds=actual_duration,
            timestamp=start_time,
        )

        self.load_test_results.append(load_metrics)
        return load_metrics

    def _setup_test_database(self) -> None:
        """Set up test database schema for performance testing."""
        try:
            conn = sqlite3.connect(self.db_path)

            # Create test tables if they don't exist
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_data (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    value INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS test_metrics (
                    id INTEGER PRIMARY KEY,
                    metric_name TEXT,
                    metric_value REAL,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_data_name ON test_data(name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_test_metrics_name ON test_metrics(metric_name)")

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error("Database setup error: %s", e)

    def _generate_test_query(self, query_num: int) -> str:
        """Generate test queries for load testing"""
        import random

        query_types = [
            # SELECT queries
            "SELECT * FROM test_data WHERE id = {}".format(  # nosec B608 # Test query generation with controlled input
                random.randint(1, 1000)  # nosec B311 # Test data generation, not crypto
            ),
            "SELECT COUNT(*) FROM test_data",
            "SELECT name, value FROM test_data WHERE value > {}".format(  # nosec B608 # Test query - safe
                random.randint(1, 100)  # nosec B311 # Test data generation, not crypto
            ),
            # INSERT queries
            "INSERT INTO test_data (name, value) VALUES ('test_{}', {})".format(  # nosec B608 # Test query - safe
                query_num, random.randint(1, 1000)  # nosec B311 # Test data generation, not crypto
            ),
            "INSERT INTO test_metrics (metric_name, metric_value) VALUES ('test_metric_{}', {})".format(  # nosec B608
                query_num, random.random() * 100  # nosec B311 # Test data generation, not crypto
            ),
            # UPDATE queries
            "UPDATE test_data SET value = {} WHERE id = {}".format(  # nosec B608 # Test query with controlled input
                random.randint(1, 1000), random.randint(1, 100)  # nosec B311 B311 # Test data generation, not crypto
            ),
            # DELETE queries (occasional)
            (
                "DELETE FROM test_data WHERE id = {}".format(  # nosec B608 # Test query generation
                    random.randint(1, 50)  # nosec B311 # Test data generation, not crypto
                )
                if query_num % 10 == 0
                else "SELECT 1"
            ),
        ]

        return random.choice(query_types)  # nosec B311 # Test query selection, not crypto

    def get_comprehensive_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive database performance summary"""
        summary = {
            "query_performance": {},
            "connection_pool_efficiency": self.connection_monitor.get_pool_efficiency_summary(),
            "transaction_performance": self.transaction_monitor.get_transaction_summary(),
            "load_test_results": [],
        }

        # Add query type summaries
        for query_type in QueryType:
            type_summary = self.query_tracker.get_query_type_summary(query_type)
            if type_summary:
                summary["query_performance"][query_type.value] = type_summary

        # Add load test summaries
        for load_test in self.load_test_results[-5:]:  # Last 5 tests
            summary["load_test_results"].append(
                {
                    "test_id": load_test.test_id,
                    "concurrent_connections": load_test.concurrent_connections,
                    "queries_per_second": load_test.queries_per_second,
                    "success_rate_percent": (load_test.successful_queries / load_test.total_queries) * 100,
                    "avg_query_time_ms": load_test.avg_query_time_ms,
                }
            )

        return summary
