# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
API Performance Monitoring Module

Provides comprehensive API performance monitoring including response times,
throughput measurement, and concurrent user load testing.

Key Components:
- APIPerformanceMonitor: Core API performance monitoring system
- ResponseTimeTracker: Response time measurement and analysis
- ThroughputMonitor: API throughput and request rate monitoring
- LoadTestRunner: Concurrent user load testing capabilities

SECURITY: All monitoring data is for defensive security research only.
"""

import asyncio
import logging
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import aiohttp
import requests


class ResponseTimeCategory(Enum):
    """Response time performance categories"""

    EXCELLENT = "excellent"  # <100ms
    GOOD = "good"  # 100-300ms
    ACCEPTABLE = "acceptable"  # 300-1000ms
    SLOW = "slow"  # 1000-3000ms
    CRITICAL = "critical"  # >3000ms


@dataclass
class APIResponseMetrics:
    """Individual API response metrics"""

    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    user_agent: Optional[str] = None
    payload_size_bytes: int = 0
    response_size_bytes: int = 0

    @property
    def performance_category(self) -> ResponseTimeCategory:
        """Categorize response time performance"""
        if self.response_time_ms < 100:
            return ResponseTimeCategory.EXCELLENT
        elif self.response_time_ms < 300:
            return ResponseTimeCategory.GOOD
        elif self.response_time_ms < 1000:
            return ResponseTimeCategory.ACCEPTABLE
        elif self.response_time_ms < 3000:
            return ResponseTimeCategory.SLOW
        else:
            return ResponseTimeCategory.CRITICAL


@dataclass
class ThroughputMetrics:
    """API throughput measurement metrics"""

    endpoint: str
    test_duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    error_rate_percent: float
    concurrent_users: int
    timestamp: datetime


@dataclass
class LoadTestConfiguration:
    """Load test configuration parameters"""

    endpoint: str
    method: str = "GET"
    concurrent_users: int = 1
    requests_per_user: int = 10
    test_duration_seconds: int = 60
    ramp_up_seconds: int = 10
    headers: Dict[str, str] = field(default_factory=dict)
    payload: Optional[Dict[str, Any]] = None
    expected_status_codes: List[int] = field(default_factory=lambda: [200])
    max_response_time_ms: int = 3000


class ResponseTimeTracker:
    """Real-time response time tracking system"""

    def __init__(self, max_samples: int = 1000) -> None:
        """Initialize ResponseTimeTracker.

        Args:
            max_samples: Maximum number of response samples to keep in memory.
                        Defaults to 1000.
        """
        self.max_samples = max_samples
        self.response_metrics: List[APIResponseMetrics] = []
        self.endpoint_stats: Dict[str, Dict[str, Any]] = {}

    def record_response(
        self,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        success: bool,
        error_message: Optional[str] = None,
        payload_size: int = 0,
        response_size: int = 0,
    ) -> APIResponseMetrics:
        """Record an API response for tracking"""
        metrics = APIResponseMetrics(
            endpoint=endpoint,
            method=method,
            response_time_ms=response_time_ms,
            status_code=status_code,
            success=success,
            error_message=error_message,
            timestamp=datetime.now(timezone.utc),
            payload_size_bytes=payload_size,
            response_size_bytes=response_size,
        )

        self.response_metrics.append(metrics)

        # Limit stored metrics
        if len(self.response_metrics) > self.max_samples:
            self.response_metrics = self.response_metrics[-self.max_samples // 2 :]

        # Update endpoint statistics
        self._update_endpoint_stats(endpoint, metrics)

        return metrics

    def _update_endpoint_stats(self, endpoint: str, metrics: APIResponseMetrics) -> None:
        """Update rolling statistics for endpoint"""
        if endpoint not in self.endpoint_stats:
            self.endpoint_stats[endpoint] = {
                "response_times": [],
                "success_count": 0,
                "error_count": 0,
                "last_updated": datetime.now(timezone.utc),
            }

        stats = self.endpoint_stats[endpoint]
        stats["response_times"].append(metrics.response_time_ms)

        # Keep only recent response times
        if len(stats["response_times"]) > 100:
            stats["response_times"] = stats["response_times"][-50:]

        if metrics.success:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1

        stats["last_updated"] = datetime.now(timezone.utc)

    def get_endpoint_summary(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get performance summary for specific endpoint"""
        if endpoint not in self.endpoint_stats:
            return None

        stats = self.endpoint_stats[endpoint]
        response_times = stats["response_times"]

        if not response_times:
            return None

        return {
            "endpoint": endpoint,
            "sample_count": len(response_times),
            "avg_response_time_ms": statistics.mean(response_times),
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times),
            "median_response_time_ms": statistics.median(response_times),
            "p95_response_time_ms": self._percentile(response_times, 95),
            "p99_response_time_ms": self._percentile(response_times, 99),
            "success_rate_percent": (stats["success_count"] / (stats["success_count"] + stats["error_count"])) * 100,
            "total_requests": stats["success_count"] + stats["error_count"],
            "last_updated": stats["last_updated"].isoformat(),
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of response times"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def get_performance_distribution(self) -> Dict[str, int]:
        """Get distribution of response time categories"""
        distribution = {category.value: 0 for category in ResponseTimeCategory}

        for metrics in self.response_metrics:
            distribution[metrics.performance_category.value] += 1

        return distribution


class ThroughputMonitor:
    """API throughput and load monitoring system"""

    def __init__(self) -> None:
        """Initialize ThroughputMonitor.

        Sets up the throughput monitoring system with an empty test results list.
        """
        self.throughput_tests: List[ThroughputMetrics] = []

    async def measure_throughput(
        self,
        endpoint: str,
        concurrent_users: int,
        test_duration_seconds: int,
        requests_per_second_target: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ThroughputMetrics:
        """Measure API throughput under concurrent load"""
        start_time = time.time()
        request_metrics: List[APIResponseMetrics] = []

        headers = headers or {}

        async def make_request(session: aiohttp.ClientSession, user_id: int) -> APIResponseMetrics:
            """Make individual API request"""
            request_start = time.time()

            try:
                async with session.get(endpoint, headers=headers, timeout=30) as response:
                    response_text = await response.text()
                    request_time = (time.time() - request_start) * 1000

                    return APIResponseMetrics(
                        endpoint=endpoint,
                        method="GET",
                        response_time_ms=request_time,
                        status_code=response.status,
                        success=200 <= response.status < 400,
                        error_message=None if 200 <= response.status < 400 else f"HTTP {response.status}",
                        timestamp=datetime.now(timezone.utc),
                        user_agent=f"LoadTest-User-{user_id}",
                        response_size_bytes=len(response_text.encode("utf-8")),
                    )

            except Exception as e:
                request_time = (time.time() - request_start) * 1000
                return APIResponseMetrics(
                    endpoint=endpoint,
                    method="GET",
                    response_time_ms=request_time,
                    status_code=0,
                    success=False,
                    error_message=str(e),
                    timestamp=datetime.now(timezone.utc),
                    user_agent=f"LoadTest-User-{user_id}",
                )

        async def user_simulation(user_id: int) -> List[APIResponseMetrics]:
            """Simulate single user making requests"""
            user_metrics = []

            async with aiohttp.ClientSession() as session:
                end_time = start_time + test_duration_seconds

                while time.time() < end_time:
                    try:
                        metrics = await make_request(session, user_id)
                        user_metrics.append(metrics)

                        # Add small delay to prevent overwhelming
                        await asyncio.sleep(0.1)

                    except Exception:
                        break

            return user_metrics

        # Run concurrent user simulations
        tasks = []
        for user_id in range(concurrent_users):
            task = asyncio.create_task(user_simulation(user_id))
            tasks.append(task)

        # Gather all user results
        user_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        for user_metrics in user_results:
            if isinstance(user_metrics, list):
                request_metrics.extend(user_metrics)

        # Calculate metrics
        actual_duration = time.time() - start_time
        total_requests = len(request_metrics)
        successful_requests = sum(1 for m in request_metrics if m.success)
        failed_requests = total_requests - successful_requests

        if total_requests > 0:
            response_times = [m.response_time_ms for m in request_metrics]
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = self._percentile(response_times, 95)
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0

        throughput_metrics = ThroughputMetrics(
            endpoint=endpoint,
            test_duration_seconds=actual_duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=total_requests / actual_duration if actual_duration > 0 else 0,
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p95_response_time_ms=p95_response_time,
            error_rate_percent=(failed_requests / total_requests) * 100 if total_requests > 0 else 0,
            concurrent_users=concurrent_users,
            timestamp=datetime.now(timezone.utc),
        )

        self.throughput_tests.append(throughput_metrics)
        return throughput_metrics

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of response times"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class LoadTestRunner:
    """Advanced load testing capabilities"""

    def __init__(self) -> None:
        """Initialize LoadTestRunner.

        Sets up the load testing framework with result storage and logging.
        """
        self.test_results: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)

    def run_load_test(
        self, config: LoadTestConfiguration, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """Run comprehensive load test with configuration"""
        test_id = f"load_test_{int(time.time())}"
        start_time = time.time()

        results = {
            "test_id": test_id,
            "config": config,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "metrics": [],
            "summary": {},
        }

        try:
            # Execute load test using ThreadPoolExecutor for better control
            with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
                futures = []

                for user_id in range(config.concurrent_users):
                    future = executor.submit(self._user_load_test, config, user_id)
                    futures.append(future)

                # Collect results
                user_metrics = []
                for future in as_completed(futures):
                    try:
                        metrics = future.result(timeout=config.test_duration_seconds + 30)
                        user_metrics.extend(metrics)
                    except Exception as e:
                        self.logger.error("User load test failed: %s", e)

                # Calculate summary statistics
                results["metrics"] = user_metrics
                results["summary"] = self._calculate_load_test_summary(user_metrics, start_time)
                results["status"] = "completed"

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)

        results["end_time"] = datetime.now(timezone.utc).isoformat()
        results["duration_seconds"] = time.time() - start_time

        self.test_results[test_id] = results
        return results

    def _user_load_test(self, config: LoadTestConfiguration, user_id: int) -> List[Dict[str, Any]]:
        """Execute load test for single user"""
        user_metrics = []

        # Ramp-up delay
        ramp_up_delay = (config.ramp_up_seconds / config.concurrent_users) * user_id
        time.sleep(ramp_up_delay)

        end_time = time.time() + config.test_duration_seconds
        request_count = 0

        while time.time() < end_time and request_count < config.requests_per_user:
            request_start = time.time()

            try:
                if config.method.upper() == "POST":
                    response = requests.post(config.endpoint, json=config.payload, headers=config.headers, timeout=30)
                elif config.method.upper() == "PUT":
                    response = requests.put(config.endpoint, json=config.payload, headers=config.headers, timeout=30)
                else:
                    response = requests.get(config.endpoint, headers=config.headers, timeout=30)

                request_time = (time.time() - request_start) * 1000
                success = response.status_code in config.expected_status_codes

                metrics = {
                    "user_id": user_id,
                    "request_id": request_count,
                    "response_time_ms": request_time,
                    "status_code": response.status_code,
                    "success": success,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "response_size_bytes": len(response.content),
                }

                user_metrics.append(metrics)

            except Exception as e:
                request_time = (time.time() - request_start) * 1000

                metrics = {
                    "user_id": user_id,
                    "request_id": request_count,
                    "response_time_ms": request_time,
                    "status_code": 0,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                user_metrics.append(metrics)

            request_count += 1

            # Small delay between requests
            time.sleep(0.01)

        return user_metrics

    def _calculate_load_test_summary(self, metrics: List[Dict[str, Any]], start_time: float) -> Dict[str, Any]:
        """Calculate load test summary statistics"""
        if not metrics:
            return {"error": "No metrics collected"}

        total_requests = len(metrics)
        successful_requests = sum(1 for m in metrics if m.get("success", False))
        failed_requests = total_requests - successful_requests

        response_times = [m["response_time_ms"] for m in metrics if "response_time_ms" in m]

        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = self._percentile(response_times, 95)
            p99_response_time = self._percentile(response_times, 99)
        else:
            avg_response_time = min_response_time = max_response_time = 0
            median_response_time = p95_response_time = p99_response_time = 0

        duration = time.time() - start_time

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate_percent": (successful_requests / total_requests) * 100,
            "error_rate_percent": (failed_requests / total_requests) * 100,
            "requests_per_second": total_requests / duration if duration > 0 else 0,
            "avg_response_time_ms": avg_response_time,
            "min_response_time_ms": min_response_time,
            "max_response_time_ms": max_response_time,
            "median_response_time_ms": median_response_time,
            "p95_response_time_ms": p95_response_time,
            "p99_response_time_ms": p99_response_time,
            "test_duration_seconds": duration,
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of response times"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class APIPerformanceMonitor:
    """
    Comprehensive API performance monitoring system

    Combines response time tracking, throughput monitoring, and load testing
    to provide complete API performance validation.
    """

    def __init__(self, session_id: Optional[str] = None, base_url: str = "http://localhost:9080") -> None:
        """Initialize APIPerformanceMonitor.

        Args:
            session_id: Unique identifier for monitoring session.
                       Defaults to timestamp-based ID.
            base_url: Base URL for API endpoints. Defaults to 'http://localhost:9080'.
        """
        self.session_id = session_id or f"api_monitor_{int(time.time())}"
        self.base_url = base_url

        self.response_tracker = ResponseTimeTracker()
        self.throughput_monitor = ThroughputMonitor()
        self.load_test_runner = LoadTestRunner()

    def measure_api_response_times(
        self,
        endpoints: List[str],
        concurrent_users: int = 1,
        requests_per_endpoint: int = 10,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Measure response times for multiple API endpoints"""
        results = {
            "session_id": self.session_id,
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
            "concurrent_users": concurrent_users,
            "requests_per_endpoint": requests_per_endpoint,
            "endpoint_results": {},
            "summary": {},
        }

        total_requests = 0
        total_response_time = 0
        successful_requests = 0

        for endpoint in endpoints:
            endpoint_metrics = []
            full_url = f"{self.base_url}{endpoint}"

            # Use ThreadPoolExecutor for concurrent requests
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = []

                for _ in range(requests_per_endpoint):
                    future = executor.submit(self._measure_single_request, full_url, headers)
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        metrics = future.result(timeout=30)
                        endpoint_metrics.append(metrics)
                        self.response_tracker.record_response(
                            endpoint=endpoint,
                            method="GET",
                            response_time_ms=metrics["response_time_ms"],
                            status_code=metrics["status_code"],
                            success=metrics["success"],
                            error_message=metrics.get("error_message"),
                        )
                    except Exception as e:
                        endpoint_metrics.append(
                            {"success": False, "error_message": str(e), "response_time_ms": 30000}  # Timeout
                        )

            # Calculate endpoint statistics
            response_times = [m["response_time_ms"] for m in endpoint_metrics]
            endpoint_successful = sum(1 for m in endpoint_metrics if m["success"])

            endpoint_summary = {
                "endpoint": endpoint,
                "total_requests": len(endpoint_metrics),
                "successful_requests": endpoint_successful,
                "success_rate_percent": (endpoint_successful / len(endpoint_metrics)) * 100,
                "avg_response_time_ms": statistics.mean(response_times) if response_times else 0,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "p95_response_time_ms": self._percentile(response_times, 95) if response_times else 0,
            }

            results["endpoint_results"][endpoint] = endpoint_summary

            # Accumulate totals
            total_requests += len(endpoint_metrics)
            total_response_time += sum(response_times) if response_times else 0
            successful_requests += endpoint_successful

        # Calculate overall summary
        results["summary"] = {
            "total_endpoints": len(endpoints),
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "overall_success_rate_percent": (successful_requests / total_requests) * 100 if total_requests > 0 else 0,
            "avg_response_time_ms": total_response_time / total_requests if total_requests > 0 else 0,
        }

        return results

    def _measure_single_request(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Measure single API request"""
        start_time = time.time()

        try:
            response = requests.get(url, headers=headers or {}, timeout=30)
            response_time = (time.time() - start_time) * 1000

            return {
                "response_time_ms": response_time,
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 400,
                "response_size_bytes": len(response.content),
            }

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            return {"response_time_ms": response_time, "status_code": 0, "success": False, "error_message": str(e)}

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of response times"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    async def run_throughput_test(
        self, endpoint: str, concurrent_users: int = 5, test_duration_seconds: int = 30
    ) -> ThroughputMetrics:
        """Run throughput test on specific endpoint"""
        full_url = f"{self.base_url}{endpoint}"
        return await self.throughput_monitor.measure_throughput(full_url, concurrent_users, test_duration_seconds)

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance monitoring summary"""
        return {
            "session_id": self.session_id,
            "response_tracking": {
                "total_requests": len(self.response_tracker.response_metrics),
                "performance_distribution": self.response_tracker.get_performance_distribution(),
                "endpoint_summaries": {
                    endpoint: self.response_tracker.get_endpoint_summary(endpoint)
                    for endpoint in self.response_tracker.endpoint_stats.keys()
                },
            },
            "throughput_tests": len(self.throughput_monitor.throughput_tests),
            "load_tests": len(self.load_test_runner.test_results),
        }
