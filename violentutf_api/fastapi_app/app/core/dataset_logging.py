# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Structured logging utilities for dataset import operations

This module provides enhanced logging capabilities with structured data,
metrics tracking, and comprehensive error reporting for dataset operations.
"""

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Self, cast

logger = logging.getLogger(__name__)


@dataclass
class ImportMetrics:
    """Metrics collected during dataset import operations."""

    # Basic metrics
    total_prompts: int = 0
    successful_prompts: int = 0
    failed_prompts: int = 0

    # Performance metrics
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    processing_time_seconds: float = 0.0

    # Memory metrics
    peak_memory_mb: float = 0.0
    avg_memory_mb: float = 0.0

    # Streaming metrics
    total_chunks: int = 0
    successful_chunks: int = 0
    failed_chunks: int = 0
    avg_chunk_size: float = 0.0

    # Retry metrics
    total_retries: int = 0
    max_retries_per_operation: int = 0

    # PyRIT memory metrics
    pyrit_storage_size_mb: float = 0.0
    pyrit_storage_time_seconds: float = 0.0

    def to_dict(self: "Self") -> Dict[str, object]:
        """Convert metrics to dictionary."""
        result = asdict(self)
        # Convert datetime objects to ISO strings
        if self.start_time:
            result["start_time"] = self.start_time.isoformat()
        if self.end_time:
            result["end_time"] = self.end_time.isoformat()
        return result

    def calculate_rates(self: "Self") -> Dict[str, float]:
        """Calculate derived rates and percentages."""
        rates = {}

        if self.total_prompts > 0:
            rates["success_rate"] = self.successful_prompts / self.total_prompts
            rates["failure_rate"] = self.failed_prompts / self.total_prompts

        if self.processing_time_seconds > 0:
            rates["prompts_per_second"] = self.successful_prompts / self.processing_time_seconds
            rates["chunks_per_second"] = self.successful_chunks / self.processing_time_seconds

        if self.total_chunks > 0:
            rates["chunk_success_rate"] = self.successful_chunks / self.total_chunks

        return rates


class DatasetLogger:
    """Enhanced logger for dataset operations with structured logging."""

    def __init__(self: "Self", logger_name: str = __name__) -> None:
        """Initialize instance."""
        self.logger = logging.getLogger(logger_name)
        self.current_operation: Optional[str] = None
        self.operation_start_time: Optional[float] = None
        self.metrics = ImportMetrics()

    def _log_structured(
        self: "Self",
        level: int,
        message: str,
        operation: Optional[str] = None,
        dataset_id: Optional[str] = None,
        dataset_type: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: object,
    ) -> None:
        """Log with structured data."""
        structured_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "operation": operation or self.current_operation,
            "dataset_id": dataset_id,
            "dataset_type": dataset_type,
            "user_id": user_id,
            **kwargs,
        }

        # Filter out None values
        structured_data = {k: v for k, v in structured_data.items() if v is not None}

        # Create log message with structured data
        log_message = f"{message} | {json.dumps(structured_data, default=str)}"
        self.logger.log(level, log_message)

    def info(self: "Self", message: str, **kwargs: object) -> None:
        """Log info message with structured data."""
        # Extract expected parameters from kwargs
        self._log_structured(
            logging.INFO,
            message,
            operation=cast(Optional[str], kwargs.get("operation")),
            dataset_id=cast(Optional[str], kwargs.get("dataset_id")),
            dataset_type=cast(Optional[str], kwargs.get("dataset_type")),
            user_id=cast(Optional[str], kwargs.get("user_id")),
            **{k: v for k, v in kwargs.items() if k not in ["operation", "dataset_id", "dataset_type", "user_id"]},
        )

    def warning(self: "Self", message: str, **kwargs: object) -> None:
        """Log warning message with structured data."""
        # Extract expected parameters from kwargs
        self._log_structured(
            logging.WARNING,
            message,
            operation=cast(Optional[str], kwargs.get("operation")),
            dataset_id=cast(Optional[str], kwargs.get("dataset_id")),
            dataset_type=cast(Optional[str], kwargs.get("dataset_type")),
            user_id=cast(Optional[str], kwargs.get("user_id")),
            **{k: v for k, v in kwargs.items() if k not in ["operation", "dataset_id", "dataset_type", "user_id"]},
        )

    def error(self: "Self", message: str, **kwargs: object) -> None:
        """Log error message with structured data."""
        # Extract expected parameters from kwargs
        self._log_structured(
            logging.ERROR,
            message,
            operation=cast(Optional[str], kwargs.get("operation")),
            dataset_id=cast(Optional[str], kwargs.get("dataset_id")),
            dataset_type=cast(Optional[str], kwargs.get("dataset_type")),
            user_id=cast(Optional[str], kwargs.get("user_id")),
            **{k: v for k, v in kwargs.items() if k not in ["operation", "dataset_id", "dataset_type", "user_id"]},
        )

    def debug(self: "Self", message: str, **kwargs: object) -> None:
        """Log debug message with structured data."""
        # Extract expected parameters from kwargs
        self._log_structured(
            logging.DEBUG,
            message,
            operation=cast(Optional[str], kwargs.get("operation")),
            dataset_id=cast(Optional[str], kwargs.get("dataset_id")),
            dataset_type=cast(Optional[str], kwargs.get("dataset_type")),
            user_id=cast(Optional[str], kwargs.get("user_id")),
            **{k: v for k, v in kwargs.items() if k not in ["operation", "dataset_id", "dataset_type", "user_id"]},
        )

    @contextmanager
    def operation_context(
        self: "Self",
        operation: str,
        dataset_id: Optional[str] = None,
        dataset_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Generator["Self", None, None]:
        """Context manager for tracking operations."""
        previous_operation = self.current_operation
        self.current_operation = operation
        self.operation_start_time = time.time()

        self.info(
            f"Starting operation: {operation}",
            operation=operation,
            dataset_id=dataset_id,
            dataset_type=dataset_type,
            user_id=user_id,
        )

        try:
            yield self
        except Exception as e:
            operation_time = time.time() - self.operation_start_time
            self.error(
                f"Operation failed: {operation}",
                operation=operation,
                dataset_id=dataset_id,
                dataset_type=dataset_type,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                operation_time_seconds=operation_time,
            )
            raise
        finally:
            operation_time = time.time() - self.operation_start_time
            self.info(
                f"Completed operation: {operation}",
                operation=operation,
                dataset_id=dataset_id,
                dataset_type=dataset_type,
                user_id=user_id,
                operation_time_seconds=operation_time,
            )
            self.current_operation = previous_operation

    def log_chunk_progress(
        self: "Self",
        chunk_index: int,
        total_chunks: int,
        chunk_size: int,
        success: bool = True,
        **kwargs: object,
    ) -> None:
        """Log chunk processing progress."""
        progress_percent = (chunk_index + 1) / total_chunks * 100

        self.debug(
            f"Chunk {chunk_index + 1}/{total_chunks} ({'success' if success else 'failed'})",
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            chunk_size=chunk_size,
            progress_percent=progress_percent,
            success=success,
            **kwargs,
        )

        # Update metrics
        if success:
            self.metrics.successful_chunks += 1
        else:
            self.metrics.failed_chunks += 1

    def log_memory_usage(self: "Self", memory_mb: float, operation: str = "unknown") -> None:
        """Log current memory usage."""
        self.debug(
            f"Memory usage: {memory_mb:.2f} MB",
            memory_mb=memory_mb,
            operation=operation,
        )

        # Update metrics
        if memory_mb > self.metrics.peak_memory_mb:
            self.metrics.peak_memory_mb = memory_mb

    def log_retry_attempt(
        self: "Self",
        attempt: int,
        max_attempts: int,
        error: Optional[Exception] = None,
        **kwargs: object,
    ) -> None:
        """Log retry attempts."""
        self.warning(
            f"Retry attempt {attempt}/{max_attempts}",
            retry_attempt=attempt,
            max_attempts=max_attempts,
            error=str(error) if error else None,
            error_type=type(error).__name__ if error else None,
            **kwargs,
        )

        # Update metrics
        self.metrics.total_retries += 1
        if attempt > self.metrics.max_retries_per_operation:
            self.metrics.max_retries_per_operation = attempt

    def log_pyrit_storage(
        self: "Self",
        prompts_stored: int,
        storage_time_seconds: float,
        storage_size_mb: float,
        **kwargs: object,
    ) -> None:
        """Log PyRIT memory storage operations."""
        self.info(
            f"Stored {prompts_stored} prompts to PyRIT memory",
            prompts_stored=prompts_stored,
            storage_time_seconds=storage_time_seconds,
            storage_size_mb=storage_size_mb,
            **kwargs,
        )

        # Update metrics
        self.metrics.pyrit_storage_time_seconds += storage_time_seconds
        self.metrics.pyrit_storage_size_mb += storage_size_mb

    def log_import_summary(
        self: "Self", dataset_id: str, dataset_type: str, success: bool = True, **kwargs: object
    ) -> None:
        """Log comprehensive import summary."""
        # Calculate final metrics
        rates = self.metrics.calculate_rates()

        summary_data = {
            "dataset_id": dataset_id,
            "dataset_type": dataset_type,
            "success": success,
            "metrics": self.metrics.to_dict(),
            "rates": rates,
            **kwargs,
        }

        if success:
            self.info(f"Dataset import completed successfully: {dataset_id}", **summary_data)
        else:
            self.error(f"Dataset import failed: {dataset_id}", **summary_data)

    def reset_metrics(self: "Self") -> None:
        """Reset metrics for a new operation."""
        self.metrics = ImportMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)

    def finalize_metrics(self: "Self") -> ImportMetrics:
        """Finalize metrics and return copy."""
        self.metrics.end_time = datetime.now(timezone.utc)

        if self.metrics.start_time and self.metrics.end_time:
            self.metrics.processing_time_seconds = (self.metrics.end_time - self.metrics.start_time).total_seconds()

        return self.metrics


# Global logger instance
dataset_logger = DatasetLogger("violentutf.datasets")


# Convenience functions for common logging patterns
def log_dataset_operation_start(
    operation: str,
    dataset_id: str,
    dataset_type: str,
    user_id: Optional[str] = None,
    **kwargs: object,
) -> None:
    """Log the start of a dataset operation."""
    dataset_logger.info(
        f"Starting {operation}",
        operation=operation,
        dataset_id=dataset_id,
        dataset_type=dataset_type,
        user_id=user_id,
        **kwargs,
    )


def log_dataset_operation_error(operation: str, dataset_id: str, error: Exception, **kwargs: object) -> None:
    """Log a dataset operation error."""
    dataset_logger.error(
        f"Error in {operation}: {str(error)}",
        operation=operation,
        dataset_id=dataset_id,
        error=str(error),
        error_type=type(error).__name__,
        **kwargs,
    )


def log_dataset_operation_success(operation: str, dataset_id: str, **kwargs: object) -> None:
    """Log successful completion of a dataset operation."""
    dataset_logger.info(
        f"Successfully completed {operation} for dataset {dataset_id}",
        operation=operation,
        dataset_id=dataset_id,
        **kwargs,
    )


class CentralizedHandler:
    """Centralized logging handler for coordinating multiple log streams."""

    def __init__(self: "Self") -> None:
        """Initialize centralized handler."""
        self.handlers: Dict[str, DatasetLogger] = {}
        self.global_metrics = ImportMetrics()

    def get_logger(self: "Self", name: str) -> DatasetLogger:
        """Get or create a dataset logger."""
        if name not in self.handlers:
            self.handlers[name] = DatasetLogger(name)
        return self.handlers[name]

    def aggregate_metrics(self: "Self") -> Dict[str, object]:
        """Aggregate metrics from all handlers."""
        aggregated = ImportMetrics()

        for handler in self.handlers.values():
            metrics = handler.metrics
            aggregated.total_prompts += metrics.total_prompts
            aggregated.successful_prompts += metrics.successful_prompts
            aggregated.failed_prompts += metrics.failed_prompts
            aggregated.total_chunks += metrics.total_chunks
            aggregated.successful_chunks += metrics.successful_chunks
            aggregated.failed_chunks += metrics.failed_chunks
            aggregated.total_retries += metrics.total_retries

            if metrics.peak_memory_mb > aggregated.peak_memory_mb:
                aggregated.peak_memory_mb = metrics.peak_memory_mb

            aggregated.processing_time_seconds += metrics.processing_time_seconds
            aggregated.pyrit_storage_size_mb += metrics.pyrit_storage_size_mb
            aggregated.pyrit_storage_time_seconds += metrics.pyrit_storage_time_seconds

        return aggregated.to_dict()

    def reset_all_metrics(self: "Self") -> None:
        """Reset metrics for all handlers."""
        for handler in self.handlers.values():
            handler.reset_metrics()


class LogAnalyzer:
    """Analyzer for log data patterns and performance insights."""

    def __init__(self: "Self", handler: Optional[CentralizedHandler] = None) -> None:
        """Initialize log analyzer."""
        self.handler = handler or CentralizedHandler()
        self.analysis_cache: Dict[str, Dict[str, object]] = {}

    def analyze_performance_trends(self: "Self", operation_type: str) -> Dict[str, object]:
        """Analyze performance trends for specific operation types."""
        metrics = self.handler.aggregate_metrics()

        analysis = {
            "operation_type": operation_type,
            "total_operations": len(self.handler.handlers),
            "performance_summary": {
                "avg_processing_time": 0.0,
                "success_rate": 0.0,
                "error_rate": 0.0,
                "memory_efficiency": 0.0,
            },
            "recommendations": [],
        }

        # Calculate performance indicators
        if isinstance(metrics.get("total_prompts"), (int, float)) and metrics["total_prompts"] > 0:
            analysis["performance_summary"]["success_rate"] = (
                metrics.get("successful_prompts", 0) / metrics["total_prompts"]
            )
            analysis["performance_summary"]["error_rate"] = metrics.get("failed_prompts", 0) / metrics["total_prompts"]

        if isinstance(metrics.get("processing_time_seconds"), (int, float)) and metrics["processing_time_seconds"] > 0:
            analysis["performance_summary"]["avg_processing_time"] = metrics["processing_time_seconds"]

        # Generate recommendations
        if analysis["performance_summary"]["error_rate"] > 0.1:
            analysis["recommendations"].append("High error rate detected - investigate failure causes")

        if analysis["performance_summary"]["avg_processing_time"] > 30:
            analysis["recommendations"].append("Long processing time - consider optimization")

        self.analysis_cache[operation_type] = analysis
        return analysis

    def get_error_patterns(self: "Self") -> Dict[str, object]:
        """Analyze error patterns across all loggers."""
        error_patterns = {"common_errors": [], "error_frequency": {}, "error_trends": {}, "mitigation_suggestions": []}

        # This would analyze actual log entries in a real implementation
        # For now, return basic structure
        return error_patterns

    def generate_performance_report(self: "Self") -> Dict[str, object]:
        """Generate comprehensive performance report."""
        aggregated_metrics = self.handler.aggregate_metrics()

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary_metrics": aggregated_metrics,
            "performance_analysis": {},
            "recommendations": [],
            "health_score": 0.0,
        }

        # Calculate health score based on success rates and performance
        success_rate = 0.0
        if (
            isinstance(aggregated_metrics.get("total_prompts"), (int, float))
            and aggregated_metrics["total_prompts"] > 0
        ):
            success_rate = aggregated_metrics.get("successful_prompts", 0) / aggregated_metrics["total_prompts"]

        report["health_score"] = min(success_rate * 100, 100.0)

        # Add performance analysis for each operation type
        for operation_type in ["import", "conversion", "validation", "storage"]:
            report["performance_analysis"][operation_type] = self.analyze_performance_trends(operation_type)

        return report


class LogConfig:
    """Configuration for logging behavior and settings."""

    def __init__(self: "Self") -> None:
        """Initialize log configuration."""
        self.log_level = "INFO"
        self.enable_structured_logging = True
        self.enable_metrics_collection = True
        self.enable_performance_tracking = True
        self.max_log_file_size_mb = 100
        self.log_retention_days = 30
        self.batch_size = 1000
        self.flush_interval_seconds = 5.0

    def update_from_dict(self: "Self", config: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self: "Self") -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "log_level": self.log_level,
            "enable_structured_logging": self.enable_structured_logging,
            "enable_metrics_collection": self.enable_metrics_collection,
            "enable_performance_tracking": self.enable_performance_tracking,
            "max_log_file_size_mb": self.max_log_file_size_mb,
            "log_retention_days": self.log_retention_days,
            "batch_size": self.batch_size,
            "flush_interval_seconds": self.flush_interval_seconds,
        }


class DatasetAuditLogger:
    """Audit logger for dataset operations with compliance tracking."""

    def __init__(self: "Self", config: Optional[LogConfig] = None) -> None:
        """Initialize audit logger."""
        self.config = config or LogConfig()
        self.base_logger = DatasetLogger("violentutf.datasets.audit")
        self.audit_entries: List[Dict[str, Any]] = []
        self.compliance_violations: List[Dict[str, Any]] = []

    def log_audit_event(
        self: "Self",
        event_type: str,
        dataset_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log audit event for compliance tracking."""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "dataset_id": dataset_id,
            "user_id": user_id,
            "details": details or {},
            "compliance_status": "compliant",
        }

        self.audit_entries.append(audit_entry)

        # Log through structured logger
        self.base_logger.info(
            f"Audit event: {event_type}",
            event_type=event_type,
            dataset_id=dataset_id,
            user_id=user_id,
            audit_entry=audit_entry,
        )

    def log_compliance_violation(
        self: "Self", violation_type: str, dataset_id: str, violation_details: Dict[str, Any], severity: str = "medium"
    ) -> None:
        """Log compliance violation for audit trail."""
        violation = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "violation_type": violation_type,
            "dataset_id": dataset_id,
            "severity": severity,
            "details": violation_details,
            "resolved": False,
        }

        self.compliance_violations.append(violation)

        # Log as warning or error based on severity
        log_level = "error" if severity in ["high", "critical"] else "warning"
        getattr(self.base_logger, log_level)(
            f"Compliance violation: {violation_type}",
            violation_type=violation_type,
            dataset_id=dataset_id,
            severity=severity,
            violation=violation,
        )

    def get_audit_trail(
        self: "Self",
        dataset_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get filtered audit trail."""
        filtered_entries = self.audit_entries

        if dataset_id:
            filtered_entries = [entry for entry in filtered_entries if entry.get("dataset_id") == dataset_id]

        if start_date:
            start_iso = start_date.isoformat()
            filtered_entries = [entry for entry in filtered_entries if entry.get("timestamp", "") >= start_iso]

        if end_date:
            end_iso = end_date.isoformat()
            filtered_entries = [entry for entry in filtered_entries if entry.get("timestamp", "") <= end_iso]

        return filtered_entries

    def generate_compliance_report(self: "Self") -> Dict[str, Any]:
        """Generate compliance report for audit purposes."""
        total_events = len(self.audit_entries)
        total_violations = len(self.compliance_violations)

        violation_by_type = {}
        for violation in self.compliance_violations:
            v_type = violation.get("violation_type", "unknown")
            violation_by_type[v_type] = violation_by_type.get(v_type, 0) + 1

        compliance_score = max(0, 100 - (total_violations * 10))

        return {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_audit_events": total_events,
            "total_violations": total_violations,
            "compliance_score": compliance_score,
            "violation_breakdown": violation_by_type,
            "status": "compliant" if total_violations == 0 else "non_compliant",
        }


# Alias for backward compatibility
class EnhancedLogAnalyzer(LogAnalyzer):
    """Enhanced log analyzer with additional features."""

    def __init__(self: "Self", handler: Optional[CentralizedHandler] = None) -> None:
        """Initialize enhanced log analyzer."""
        super().__init__(handler)
        self.advanced_metrics: Dict[str, Any] = {}

    def enhanced_analysis(self: "Self", dataset_type: str) -> Dict[str, Any]:
        """Perform enhanced analysis with additional metrics."""
        base_analysis = self.analyze_performance_trends(dataset_type)

        # Add enhanced features
        enhanced = {
            **base_analysis,
            "enhanced_features": {
                "trend_analysis": True,
                "predictive_insights": True,
                "anomaly_detection": True,
            },
            "advanced_recommendations": [],
        }

        return enhanced


# Global instances
centralized_handler = CentralizedHandler()
log_analyzer = LogAnalyzer(centralized_handler)
enhanced_log_analyzer = EnhancedLogAnalyzer(centralized_handler)
default_log_config = LogConfig()
audit_logger = DatasetAuditLogger(default_log_config)
