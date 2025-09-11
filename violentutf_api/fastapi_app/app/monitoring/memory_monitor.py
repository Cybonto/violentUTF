# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Memory Monitor Module

Provides comprehensive memory usage monitoring and cleanup validation
for dataset operations and system resource management.

Key Components:
- MemoryMonitor: Core memory usage tracking and analysis
- MemoryUsageTracker: Real-time memory usage monitoring
- MemoryCleanupValidator: Memory cleanup efficiency validation
- MemoryAlert: Memory usage alerting system

SECURITY: All monitoring data is for defensive security research only.
"""

import gc
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import psutil


class MemoryAlert(Enum):
    """Memory alert severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a specific point in time"""

    timestamp: datetime
    process_memory_mb: float
    system_memory_mb: float
    system_memory_percent: float
    available_memory_mb: float
    swap_memory_mb: float
    swap_memory_percent: float
    gc_count_0: int
    gc_count_1: int
    gc_count_2: int
    operation_context: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)

    @property
    def alert_level(self) -> MemoryAlert:
        """Determine alert level based on memory usage"""
        if self.system_memory_percent >= 95:
            return MemoryAlert.CRITICAL
        elif self.system_memory_percent >= 85:
            return MemoryAlert.HIGH
        elif self.system_memory_percent >= 75:
            return MemoryAlert.MEDIUM
        else:
            return MemoryAlert.LOW


@dataclass
class MemoryCleanupResult:
    """Results from memory cleanup validation"""

    initial_memory_mb: float
    final_memory_mb: float
    memory_freed_mb: float
    cleanup_efficiency_percent: float
    gc_collections_triggered: int
    cleanup_duration_seconds: float
    success: bool
    error_message: Optional[str] = None

    @property
    def is_efficient_cleanup(self) -> bool:
        """Check if cleanup was efficient (>80% of allocations freed)"""
        return self.cleanup_efficiency_percent >= 80.0


class MemoryUsageTracker:
    """Real-time memory usage tracking system"""

    def __init__(self) -> None:
        """Initialize MemoryUsageTracker.

        Sets up the memory tracking system with default configuration:
        - 1-second tracking interval
        - Maximum 1000 memory snapshots
        - Logging capability
        """
        self.snapshots: List[MemorySnapshot] = []
        self.tracking_active = False
        self.tracking_thread: Optional[threading.Thread] = None
        self.tracking_interval = 1.0  # seconds
        self.max_snapshots = 1000
        self.logger = logging.getLogger(__name__)

    def start_tracking(self, interval: float = 1.0) -> None:
        """Start continuous memory tracking"""
        if self.tracking_active:
            return

        self.tracking_interval = interval
        self.tracking_active = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()

    def stop_tracking(self) -> None:
        """Stop continuous memory tracking"""
        self.tracking_active = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=2.0)

    def _tracking_loop(self) -> None:
        """Run the internal tracking loop for continuous memory monitoring."""
        while self.tracking_active:
            try:
                snapshot = self.capture_snapshot("continuous_tracking")
                self.snapshots.append(snapshot)

                # Limit snapshot history
                if len(self.snapshots) > self.max_snapshots:
                    self.snapshots = self.snapshots[-self.max_snapshots // 2 :]

                time.sleep(self.tracking_interval)

            except Exception as e:
                # Log error but continue tracking
                self.logger.error("Memory tracking error: %s", e)
                time.sleep(self.tracking_interval)

    def capture_snapshot(self, context: str = "manual") -> MemorySnapshot:
        """Capture current memory usage snapshot"""
        process = psutil.Process()
        memory_info = process.memory_info()
        system_memory = psutil.virtual_memory()
        swap_memory = psutil.swap_memory()

        # Get garbage collection stats
        gc_stats = gc.get_stats()
        gc_count_0 = gc_stats[0]["collections"] if len(gc_stats) > 0 else 0
        gc_count_1 = gc_stats[1]["collections"] if len(gc_stats) > 1 else 0
        gc_count_2 = gc_stats[2]["collections"] if len(gc_stats) > 2 else 0

        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            process_memory_mb=memory_info.rss / 1024 / 1024,
            system_memory_mb=system_memory.used / 1024 / 1024,
            system_memory_percent=system_memory.percent,
            available_memory_mb=system_memory.available / 1024 / 1024,
            swap_memory_mb=swap_memory.used / 1024 / 1024,
            swap_memory_percent=swap_memory.percent,
            gc_count_0=gc_count_0,
            gc_count_1=gc_count_1,
            gc_count_2=gc_count_2,
            operation_context=context,
        )

        return snapshot

    def get_peak_usage(self) -> Optional[MemorySnapshot]:
        """Get peak memory usage from tracked snapshots"""
        if not self.snapshots:
            return None

        return max(self.snapshots, key=lambda s: s.process_memory_mb)

    def get_usage_trend(self) -> Dict[str, Any]:
        """Analyze memory usage trend from snapshots"""
        if len(self.snapshots) < 2:
            return {"trend": "insufficient_data", "snapshots_count": len(self.snapshots)}

        recent_snapshots = self.snapshots[-10:]  # Last 10 snapshots
        initial_memory = recent_snapshots[0].process_memory_mb
        final_memory = recent_snapshots[-1].process_memory_mb

        memory_change = final_memory - initial_memory
        change_percent = (memory_change / initial_memory) * 100 if initial_memory > 0 else 0

        # Determine trend
        if abs(change_percent) < 5:
            trend = "stable"
        elif change_percent > 0:
            trend = "increasing"
        else:
            trend = "decreasing"

        return {
            "trend": trend,
            "change_mb": memory_change,
            "change_percent": change_percent,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "snapshots_analyzed": len(recent_snapshots),
            "time_window_seconds": (recent_snapshots[-1].timestamp - recent_snapshots[0].timestamp).total_seconds(),
        }


class MemoryCleanupValidator:
    """Memory cleanup efficiency validation system"""

    def __init__(self) -> None:
        """Initialize MemoryCleanupValidator.

        Sets up the cleanup validation system with an empty results list
        for tracking memory cleanup efficiency.
        """
        self.cleanup_results: List[MemoryCleanupResult] = []

    def validate_cleanup_efficiency(
        self, pre_operation_memory: float, post_cleanup_memory: float, operation_context: str = "unknown"
    ) -> MemoryCleanupResult:
        """
        Validate memory cleanup efficiency after operations

        Args:
            pre_operation_memory: Memory usage before operation (MB)
            post_cleanup_memory: Memory usage after cleanup (MB)
            operation_context: Description of the operation

        Returns:
            MemoryCleanupResult: Cleanup validation results
        """
        start_time = time.time()
        # initial_gc_stats available via gc.get_stats() if needed

        success = True
        error_message = None

        try:
            # Force garbage collection
            collected = gc.collect()

            # Get final memory reading after GC
            process = psutil.Process()
            final_memory = process.memory_info().rss / 1024 / 1024

            # Calculate cleanup efficiency
            memory_freed = pre_operation_memory - final_memory
            cleanup_efficiency = (memory_freed / pre_operation_memory) * 100 if pre_operation_memory > 0 else 0

            # Ensure cleanup efficiency is not negative (memory might have increased due to fragmentation)
            cleanup_efficiency = max(0, cleanup_efficiency)

        except Exception as e:
            success = False
            error_message = str(e)
            final_memory = post_cleanup_memory
            memory_freed = 0
            cleanup_efficiency = 0
            collected = 0

        cleanup_duration = time.time() - start_time

        result = MemoryCleanupResult(
            initial_memory_mb=pre_operation_memory,
            final_memory_mb=final_memory,
            memory_freed_mb=memory_freed,
            cleanup_efficiency_percent=cleanup_efficiency,
            gc_collections_triggered=collected,
            cleanup_duration_seconds=cleanup_duration,
            success=success,
            error_message=error_message,
        )

        self.cleanup_results.append(result)
        return result

    def get_cleanup_summary(self) -> Dict[str, Any]:
        """Get summary of cleanup validation results"""
        if not self.cleanup_results:
            return {"total_validations": 0, "summary": "No cleanup validations performed"}

        successful_cleanups = [r for r in self.cleanup_results if r.success]
        efficient_cleanups = [r for r in successful_cleanups if r.is_efficient_cleanup]

        avg_efficiency = (
            sum(r.cleanup_efficiency_percent for r in successful_cleanups) / len(successful_cleanups)
            if successful_cleanups
            else 0
        )
        avg_memory_freed = (
            sum(r.memory_freed_mb for r in successful_cleanups) / len(successful_cleanups) if successful_cleanups else 0
        )

        return {
            "total_validations": len(self.cleanup_results),
            "successful_validations": len(successful_cleanups),
            "efficient_cleanups": len(efficient_cleanups),
            "efficiency_rate": len(efficient_cleanups) / len(self.cleanup_results) if self.cleanup_results else 0,
            "average_cleanup_efficiency_percent": avg_efficiency,
            "average_memory_freed_mb": avg_memory_freed,
            "recent_results": [
                {
                    "initial_memory_mb": r.initial_memory_mb,
                    "final_memory_mb": r.final_memory_mb,
                    "cleanup_efficiency_percent": r.cleanup_efficiency_percent,
                    "is_efficient": r.is_efficient_cleanup,
                }
                for r in self.cleanup_results[-5:]  # Last 5 results
            ],
        }


class MemoryMonitor:
    """
    Comprehensive memory monitoring and management system

    Provides memory usage tracking, cleanup validation, and alert generation
    for dataset operations and system resource management.
    """

    def __init__(self) -> None:
        """Initialize MemoryMonitor.

        Sets up comprehensive memory monitoring with:
        - Memory usage tracker for real-time monitoring
        - Cleanup validator for efficiency validation
        - Alert callback system for memory threshold notifications
        """
        self.usage_tracker = MemoryUsageTracker()
        self.cleanup_validator = MemoryCleanupValidator()
        self.alert_callbacks: List[Callable[[MemorySnapshot], None]] = []
        self.monitoring_active = False
        self.logger = logging.getLogger(__name__)

    def start_monitoring(self, tracking_interval: float = 1.0) -> None:
        """Start comprehensive memory monitoring"""
        self.monitoring_active = True
        self.usage_tracker.start_tracking(tracking_interval)

    def stop_monitoring(self) -> None:
        """Stop comprehensive memory monitoring"""
        self.monitoring_active = False
        self.usage_tracker.stop_tracking()

    def add_alert_callback(self, callback: Callable[[MemorySnapshot], None]) -> None:
        """Add callback for memory alerts"""
        self.alert_callbacks.append(callback)

    def monitor_operation(self, operation_name: str) -> "MemoryOperationMonitor":
        """Context manager for monitoring memory usage during operations"""
        return MemoryOperationMonitor(self, operation_name)

    def validate_memory_usage(
        self, expected_max_memory_mb: float, operation_context: str = "validation"
    ) -> Tuple[bool, MemorySnapshot]:
        """Validate current memory usage against expected limits"""
        snapshot = self.usage_tracker.capture_snapshot(operation_context)

        # Check memory alerts
        for callback in self.alert_callbacks:
            try:
                callback(snapshot)
            except Exception as e:
                self.logger.error("Memory alert callback error: %s", e)

        is_valid = snapshot.process_memory_mb <= expected_max_memory_mb
        return is_valid, snapshot

    def measure_memory_cleanup_efficiency(
        self, pre_operation_memory: float, operation_context: str = "cleanup_test"
    ) -> MemoryCleanupResult:
        """Measure and validate memory cleanup efficiency"""
        return self.cleanup_validator.validate_cleanup_efficiency(
            pre_operation_memory, self.usage_tracker.capture_snapshot().process_memory_mb, operation_context
        )

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive memory monitoring report"""
        current_snapshot = self.usage_tracker.capture_snapshot("report_generation")
        peak_usage = self.usage_tracker.get_peak_usage()
        usage_trend = self.usage_tracker.get_usage_trend()
        cleanup_summary = self.cleanup_validator.get_cleanup_summary()

        return {
            "monitoring_status": {
                "active": self.monitoring_active,
                "tracking_snapshots": len(self.usage_tracker.snapshots),
                "cleanup_validations": len(self.cleanup_validator.cleanup_results),
            },
            "current_memory": {
                "process_memory_mb": current_snapshot.process_memory_mb,
                "system_memory_percent": current_snapshot.system_memory_percent,
                "available_memory_mb": current_snapshot.available_memory_mb,
                "alert_level": current_snapshot.alert_level.value,
            },
            "peak_usage": {
                "peak_memory_mb": peak_usage.process_memory_mb if peak_usage else 0,
                "peak_timestamp": peak_usage.timestamp.isoformat() if peak_usage else None,
            },
            "usage_trend": usage_trend,
            "cleanup_performance": cleanup_summary,
            "system_health": {
                "swap_usage_percent": current_snapshot.swap_memory_percent,
                "gc_collections": {
                    "gen_0": current_snapshot.gc_count_0,
                    "gen_1": current_snapshot.gc_count_1,
                    "gen_2": current_snapshot.gc_count_2,
                },
            },
        }


class MemoryOperationMonitor:
    """Context manager for monitoring memory usage during specific operations"""

    def __init__(self, memory_monitor: MemoryMonitor, operation_name: str) -> None:
        """Initialize MemoryOperationMonitor.

        Args:
            memory_monitor: MemoryMonitor instance for tracking memory usage
            operation_name: Name of the operation being monitored
        """
        self.memory_monitor = memory_monitor
        self.operation_name = operation_name
        self.start_snapshot: Optional[MemorySnapshot] = None
        self.end_snapshot: Optional[MemorySnapshot] = None

    def __enter__(self) -> "MemoryOperationMonitor":
        """Enter the memory monitoring context."""
        self.start_snapshot = self.memory_monitor.usage_tracker.capture_snapshot(f"{self.operation_name}_start")
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Optional[Any]) -> None:
        """Exit the memory monitoring context and perform cleanup validation."""
        self.end_snapshot = self.memory_monitor.usage_tracker.capture_snapshot(f"{self.operation_name}_end")

        if self.start_snapshot and self.end_snapshot:
            # Validate cleanup if memory was allocated
            if self.end_snapshot.process_memory_mb > self.start_snapshot.process_memory_mb:
                self.memory_monitor.measure_memory_cleanup_efficiency(
                    self.end_snapshot.process_memory_mb, self.operation_name
                )

    def get_memory_delta(self) -> Optional[Dict[str, float]]:
        """Get memory usage delta for this operation"""
        if not (self.start_snapshot and self.end_snapshot):
            return None

        return {
            "memory_delta_mb": self.end_snapshot.process_memory_mb - self.start_snapshot.process_memory_mb,
            "duration_seconds": (self.end_snapshot.timestamp - self.start_snapshot.timestamp).total_seconds(),
            "start_memory_mb": self.start_snapshot.process_memory_mb,
            "end_memory_mb": self.end_snapshot.process_memory_mb,
        }


class WorkflowMemoryMonitor:
    """
    Workflow-specific memory monitoring for end-to-end test validation.

    This class provides specialized memory monitoring capabilities for workflow
    execution, including memory limit enforcement and usage validation.
    """

    def __init__(self) -> None:
        """Initialize workflow memory monitor."""
        self.memory_monitor = MemoryMonitor()
        self.workflow_limits = {
            "garak_collection": {"max_memory_mb": 500, "warning_threshold": 0.8},
            "ollegen1_full": {"max_memory_mb": 2048, "warning_threshold": 0.8},
            "acpbench_all": {"max_memory_mb": 500, "warning_threshold": 0.8},
            "legalbench_166_dirs": {"max_memory_mb": 1024, "warning_threshold": 0.8},
            "docmath_220mb": {"max_memory_mb": 2048, "warning_threshold": 0.8},
            "graphwalk_480mb": {"max_memory_mb": 2048, "warning_threshold": 0.8},
            "confaide_4_tiers": {"max_memory_mb": 500, "warning_threshold": 0.8},
            "judgebench_all": {"max_memory_mb": 1024, "warning_threshold": 0.8},
            "meta_evaluation": {"max_memory_mb": 1024, "warning_threshold": 0.8},
        }
        self.active_workflows: Dict[str, MemorySnapshot] = {}

    def get_memory_limits(self) -> Dict[str, Dict[str, float]]:
        """Get memory limits for all workflow types."""
        return self.workflow_limits.copy()

    def get_current_workflow_memory(self) -> Dict[str, Any]:
        """Get current memory usage for workflow validation."""
        current_snapshot = self.memory_monitor.usage_tracker.capture_snapshot("workflow_current")

        return {
            "process_memory_mb": current_snapshot.process_memory_mb,
            "system_memory_percent": current_snapshot.system_memory_percent,
            "available_memory_mb": current_snapshot.available_memory_mb,
            "timestamp": current_snapshot.timestamp.isoformat(),
            "memory_limits": self.workflow_limits,
        }

    def start_workflow_monitoring(self, workflow_name: str, workflow_type: str) -> str:
        """Start monitoring memory for a specific workflow."""
        snapshot = self.memory_monitor.usage_tracker.capture_snapshot(f"workflow_{workflow_name}_start")
        self.active_workflows[workflow_name] = snapshot

        # Check if we have limits for this workflow type
        if workflow_type not in self.workflow_limits:
            workflow_type = "default"
            self.workflow_limits["default"] = {"max_memory_mb": 1024, "warning_threshold": 0.8}

        return workflow_name

    def check_workflow_memory_compliance(self, workflow_name: str, workflow_type: str) -> Dict[str, Any]:
        """Check if workflow is within memory compliance limits."""
        current_snapshot = self.memory_monitor.usage_tracker.capture_snapshot(f"workflow_{workflow_name}_check")

        limits = self.workflow_limits.get(
            workflow_type, self.workflow_limits.get("default", {"max_memory_mb": 1024, "warning_threshold": 0.8})
        )

        compliance_result = {
            "workflow_name": workflow_name,
            "workflow_type": workflow_type,
            "current_memory_mb": current_snapshot.process_memory_mb,
            "memory_limit_mb": limits["max_memory_mb"],
            "warning_threshold_mb": limits["max_memory_mb"] * limits["warning_threshold"],
            "is_compliant": current_snapshot.process_memory_mb <= limits["max_memory_mb"],
            "is_warning": current_snapshot.process_memory_mb >= (limits["max_memory_mb"] * limits["warning_threshold"]),
            "memory_usage_percent": (current_snapshot.process_memory_mb / limits["max_memory_mb"]) * 100,
            "timestamp": current_snapshot.timestamp.isoformat(),
        }

        # Add memory delta if we have a starting snapshot
        if workflow_name in self.active_workflows:
            start_snapshot = self.active_workflows[workflow_name]
            compliance_result["memory_delta_mb"] = current_snapshot.process_memory_mb - start_snapshot.process_memory_mb
            compliance_result["duration_seconds"] = (
                current_snapshot.timestamp - start_snapshot.timestamp
            ).total_seconds()

        return compliance_result

    def stop_workflow_monitoring(self, workflow_name: str) -> Dict[str, Any]:
        """Stop monitoring and get final memory report for workflow."""
        end_snapshot = self.memory_monitor.usage_tracker.capture_snapshot(f"workflow_{workflow_name}_end")

        if workflow_name not in self.active_workflows:
            return {"error": f"Workflow {workflow_name} was not being monitored"}

        start_snapshot = self.active_workflows[workflow_name]
        del self.active_workflows[workflow_name]

        return {
            "workflow_name": workflow_name,
            "start_memory_mb": start_snapshot.process_memory_mb,
            "end_memory_mb": end_snapshot.process_memory_mb,
            "memory_delta_mb": end_snapshot.process_memory_mb - start_snapshot.process_memory_mb,
            "duration_seconds": (end_snapshot.timestamp - start_snapshot.timestamp).total_seconds(),
            "peak_memory_mb": max(start_snapshot.process_memory_mb, end_snapshot.process_memory_mb),
            "start_timestamp": start_snapshot.timestamp.isoformat(),
            "end_timestamp": end_snapshot.timestamp.isoformat(),
        }

    def validate_memory_cleanup_after_workflow(
        self, workflow_name: str, expected_cleanup_percent: float = 90.0
    ) -> Dict[str, Any]:
        """Validate that memory was properly cleaned up after workflow completion."""
        # Force garbage collection
        gc.collect()
        time.sleep(0.1)  # Brief pause for cleanup

        cleanup_snapshot = self.memory_monitor.usage_tracker.capture_snapshot(f"workflow_{workflow_name}_cleanup")

        # Use memory monitor's cleanup validation
        cleanup_result = self.memory_monitor.measure_memory_cleanup_efficiency(
            cleanup_snapshot.process_memory_mb, workflow_name
        )

        return {
            "workflow_name": workflow_name,
            "cleanup_validation": cleanup_result,
            "expected_cleanup_percent": expected_cleanup_percent,
            "cleanup_successful": cleanup_result["cleanup_efficiency_percent"] >= expected_cleanup_percent,
            "current_memory_mb": cleanup_snapshot.process_memory_mb,
            "timestamp": cleanup_snapshot.timestamp.isoformat(),
        }
