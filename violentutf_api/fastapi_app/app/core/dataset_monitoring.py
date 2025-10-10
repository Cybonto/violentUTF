# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Monitoring and metrics integration for dataset import operations

This module provides comprehensive monitoring capabilities including
performance metrics, health checks, and integration with monitoring systems.
"""
import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Self, Union, cast

import psutil

from app.core.dataset_config import DatasetImportConfig
from app.core.dataset_logging import ImportMetrics

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System-level metrics for monitoring."""

    # CPU metrics

    cpu_percent: float = 0.0
    cpu_count: int = 0
    load_average: List[float] = field(default_factory=list)

    # Memory metrics
    memory_total_mb: float = 0.0
    memory_used_mb: float = 0.0
    memory_available_mb: float = 0.0
    memory_percent: float = 0.0

    # Disk metrics
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_percent: float = 0.0

    # Network metrics (if available)
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0

    # Process metrics
    process_memory_mb: float = 0.0
    process_cpu_percent: float = 0.0
    open_files: int = 0

    timestamp: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def collect_current(cls: type) -> "SystemMetrics":
        """Collect current system metrics."""
        try:

            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # Load average (Unix-like systems only)
            load_avg = []
            try:
                load_avg = list(psutil.getloadavg())
            except AttributeError:
                load_avg = [0.0, 0.0, 0.0]  # Windows fallback

            # Memory metrics
            memory = psutil.virtual_memory()
            memory_total_mb = memory.total / (1024 * 1024)
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            memory_percent = memory.percent

            # Disk metrics
            disk = psutil.disk_usage("/")
            disk_total_gb = disk.total / (1024 * 1024 * 1024)
            disk_used_gb = disk.used / (1024 * 1024 * 1024)
            disk_free_gb = disk.free / (1024 * 1024 * 1024)
            disk_percent = (disk.used / disk.total) * 100

            # Network metrics
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent
            network_bytes_recv = network.bytes_recv

            # Process metrics
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 * 1024)
            process_cpu_percent = process.cpu_percent()

            # Open files count
            try:
                open_files = len(process.open_files())
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                open_files = 0

            return cast(
                "SystemMetrics",
                cls(
                    cpu_percent=cpu_percent,
                    cpu_count=cpu_count,
                    load_average=load_avg,
                    memory_total_mb=memory_total_mb,
                    memory_used_mb=memory_used_mb,
                    memory_available_mb=memory_available_mb,
                    memory_percent=memory_percent,
                    disk_total_gb=disk_total_gb,
                    disk_used_gb=disk_used_gb,
                    disk_free_gb=disk_free_gb,
                    disk_percent=disk_percent,
                    network_bytes_sent=network_bytes_sent,
                    network_bytes_recv=network_bytes_recv,
                    process_memory_mb=process_memory_mb,
                    process_cpu_percent=process_cpu_percent,
                    open_files=open_files,
                ),
            )

        except Exception as e:
            logger.warning("Failed to collect system metrics: %s", e)
            return cast("SystemMetrics", cls())  # Return empty metrics on failure


class PerformanceMonitor:
    """Monitor performance of dataset operations."""

    def __init__(self: "Self", config: DatasetImportConfig) -> None:
        """Initialize instance."""
        self.config = config

        self.metrics_history: deque = deque(maxlen=1000)  # Store last 1000 metrics
        self.operation_timings: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.active_operations: Dict[str, datetime] = {}
        self.system_metrics_history: deque = deque(maxlen=100)

        # Start background monitoring if enabled
        if config.enable_statistics_tracking:
            self._monitoring_task: Optional[asyncio.Task[Any]] = None
            self._start_background_monitoring()

    def _start_background_monitoring(self: "Self") -> None:
        """Start background system monitoring."""

        async def monitor_loop() -> None:
            while True:
                try:
                    system_metrics = SystemMetrics.collect_current()
                    self.system_metrics_history.append(system_metrics)

                    # Check for resource alerts
                    await self._check_resource_alerts(system_metrics)

                    # Clean up old data
                    self._cleanup_old_data()

                except Exception as e:
                    logger.warning("Background monitoring error: %s", e)

                await asyncio.sleep(30)  # Monitor every 30 seconds

        # Start the monitoring task
        try:
            loop = asyncio.get_event_loop()
            self._monitoring_task = loop.create_task(monitor_loop())
        except RuntimeError:
            # No event loop running
            logger.debug("No event loop for background monitoring")

    async def _check_resource_alerts(self: "Self", metrics: SystemMetrics) -> None:
        """Check for resource usage alerts."""
        alerts = []

        # Memory alerts
        if metrics.memory_percent > 90:
            alerts.append(f"High memory usage: {metrics.memory_percent:.1f}%")

        # CPU alerts
        if metrics.cpu_percent > 95:
            alerts.append(f"High CPU usage: {metrics.cpu_percent:.1f}%")

        # Disk alerts
        if metrics.disk_percent > 90:
            alerts.append(f"Low disk space: {metrics.disk_percent:.1f}% used")

        # Process memory alerts
        if metrics.process_memory_mb > self.config.max_memory_mb:
            alerts.append(
                f"Process memory limit exceeded: {metrics.process_memory_mb:.1f}MB "
                f"(limit: {self.config.max_memory_mb}MB)"
            )

        # Log alerts
        for alert in alerts:
            logger.warning("Resource alert: %s", alert)

    def _cleanup_old_data(self: "Self") -> None:
        """Clean up old monitoring data."""
        # Note: cutoff_time would be used if we stored timestamps with timings

        # cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Clean up operation timings older than 24 hours
        for operation, timings in self.operation_timings.items():
            # This is simplified - in practice you'd store timestamps with timings
            if len(timings) > 1000:  # Keep only last 1000 entries
                self.operation_timings[operation] = timings[-1000:]

    def start_operation(self: "Self", operation_id: str, operation_type: str) -> None:
        """Start tracking an operation."""
        self.active_operations[operation_id] = datetime.utcnow()

        logger.debug("Started tracking operation: %s (type: %s)", operation_id, operation_type)

    def end_operation(
        self: "Self",
        operation_id: str,
        operation_type: str,
        success: bool = True,
        metrics: Optional[ImportMetrics] = None,
    ) -> float:
        """End tracking an operation and return duration."""
        start_time = self.active_operations.pop(operation_id, None)

        if not start_time:
            logger.warning("No start time found for operation: %s", operation_id)
            return 0.0

        duration = (datetime.utcnow() - start_time).total_seconds()

        # Record timing
        self.operation_timings[operation_type].append(duration)

        # Record metrics if provided
        if metrics:
            self.metrics_history.append(
                {
                    "operation_id": operation_id,
                    "operation_type": operation_type,
                    "duration": duration,
                    "success": success,
                    "metrics": metrics.to_dict(),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        # Update error counts
        if not success:
            self.error_counts[operation_type] += 1

        logger.debug(
            "Completed operation: %s (type: %s, duration: %.2fs, success: %s)",
            operation_id,
            operation_type,
            duration,
            success,
        )

        return duration

    def record_error(self: "Self", operation_type: str, error: Exception) -> None:
        """Record an error occurrence."""
        self.error_counts[f"{operation_type}_error"] += 1

        self.error_counts[f"{type(error).__name__}"] += 1

        logger.debug(
            "Recorded error for %s: %s - %s",
            operation_type,
            type(error).__name__,
            str(error),
        )

    def get_performance_summary(self: "Self", operation_type: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary for operations."""
        if operation_type:

            timings = self.operation_timings.get(operation_type, [])
        else:
            # All timings combined
            timings = []
            for op_timings in self.operation_timings.values():
                timings.extend(op_timings)

        if not timings:
            return {
                "operation_type": operation_type,
                "total_operations": 0,
                "avg_duration_seconds": 0.0,
                "min_duration_seconds": 0.0,
                "max_duration_seconds": 0.0,
                "error_count": 0,
            }

        return {
            "operation_type": operation_type,
            "total_operations": len(timings),
            "avg_duration_seconds": sum(timings) / len(timings),
            "min_duration_seconds": min(timings),
            "max_duration_seconds": max(timings),
            "error_count": (
                self.error_counts.get(f"{operation_type}_error", 0)
                if operation_type
                else sum(self.error_counts.values())
            ),
        }

    def get_system_health(self: "Self") -> Dict[str, Any]:
        """Get current system health status."""
        if not self.system_metrics_history:

            current_metrics = SystemMetrics.collect_current()
        else:
            current_metrics = self.system_metrics_history[-1]

        # Calculate health score (0-100)
        health_score = 100.0

        # Deduct for high resource usage
        if current_metrics.memory_percent > 80:
            health_score -= (current_metrics.memory_percent - 80) * 2

        if current_metrics.cpu_percent > 80:
            health_score -= (current_metrics.cpu_percent - 80) * 1.5

        if current_metrics.disk_percent > 85:
            health_score -= (current_metrics.disk_percent - 85) * 3

        # Deduct for recent errors
        recent_errors = sum(self.error_counts.values())
        if recent_errors > 0:
            health_score -= min(recent_errors * 5, 30)  # Max 30 point deduction for errors

        health_score = max(0, health_score)

        # Determine health status
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 75:
            status = "good"
        elif health_score >= 60:
            status = "fair"
        elif health_score >= 40:
            status = "poor"
        else:
            status = "critical"

        return {
            "health_score": health_score,
            "status": status,
            "system_metrics": {
                "cpu_percent": current_metrics.cpu_percent,
                "memory_percent": current_metrics.memory_percent,
                "disk_percent": current_metrics.disk_percent,
                "process_memory_mb": current_metrics.process_memory_mb,
            },
            "active_operations": len(self.active_operations),
            "total_errors": sum(self.error_counts.values()),
            "timestamp": current_metrics.timestamp.isoformat(),
        }

    def get_detailed_metrics(self: "Self") -> Dict[str, Any]:
        """Get detailed metrics for debugging and analysis."""
        return {
            "performance_summary": {
                op_type: self.get_performance_summary(op_type) for op_type in self.operation_timings.keys()
            },
            "error_breakdown": dict(self.error_counts),
            "system_health": self.get_system_health(),
            "recent_metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "memory_percent": m.memory_percent,
                    "cpu_percent": m.cpu_percent,
                    "process_memory_mb": m.process_memory_mb,
                }
                for m in list(self.system_metrics_history)[-10:]  # Last 10 metrics
            ],
            "active_operations": [
                {
                    "operation_id": op_id,
                    "started_at": start_time.isoformat(),
                    "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
                }
                for op_id, start_time in self.active_operations.items()
            ],
        }

    def export_metrics(self: "Self", export_format: str = "json") -> Union[str, Dict[str, Any]]:
        """Export metrics in specified format."""
        metrics_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "metrics_count": len(self.metrics_history),
            "operation_types": list(self.operation_timings.keys()),
            "detailed_metrics": self.get_detailed_metrics(),
            "recent_operations": list(self.metrics_history)[-50:],  # Last 50 operations
        }

        if export_format.lower() == "json":
            import json

            return json.dumps(metrics_data, indent=2, default=str)
        else:
            return metrics_data

    def reset_metrics(self: "Self") -> None:
        """Reset all metrics (useful for testing)."""
        self.metrics_history.clear()

        self.operation_timings.clear()
        self.error_counts.clear()
        self.active_operations.clear()
        self.system_metrics_history.clear()

        logger.info("All monitoring metrics have been reset")

    def __del__(self: "Self") -> None:
        """Cleanup monitoring task."""
        if hasattr(self, "_monitoring_task") and self._monitoring_task:

            self._monitoring_task.cancel()


# Global monitoring instance
_global_monitor: Optional[PerformanceMonitor] = None


def get_global_monitor(
    config: Optional[DatasetImportConfig] = None,
) -> PerformanceMonitor:
    """Get or create global performance monitor."""
    global _global_monitor  # pylint: disable=global-statement

    if _global_monitor is None:
        if config is None:
            from app.core.dataset_config import get_global_config

            config = get_global_config()

        _global_monitor = PerformanceMonitor(config)

    return _global_monitor


def reset_global_monitor() -> None:
    """Reset global performance monitor (useful for testing)."""
    global _global_monitor  # pylint: disable=global-statement

    if _global_monitor:
        _global_monitor.reset_metrics()
    _global_monitor = None


# Convenience functions for common monitoring patterns
def start_monitoring_operation(operation_id: str, operation_type: str) -> None:
    """Start monitoring an operation."""
    monitor = get_global_monitor()

    monitor.start_operation(operation_id, operation_type)


def end_monitoring_operation(
    operation_id: str,
    operation_type: str,
    success: bool = True,
    metrics: Optional[ImportMetrics] = None,
) -> float:
    """End monitoring an operation."""
    monitor = get_global_monitor()

    return monitor.end_operation(operation_id, operation_type, success, metrics)


def record_monitoring_error(operation_type: str, error: Exception) -> None:
    """Record an error in monitoring."""
    monitor = get_global_monitor()

    monitor.record_error(operation_type, error)


def get_system_health_status() -> Dict[str, Any]:
    """Get current system health status."""
    monitor = get_global_monitor()

    return monitor.get_system_health()
