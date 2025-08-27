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
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ImportMetrics:
    """Metrics collected during dataset import operations"""

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

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        result = asdict(self)
        # Convert datetime objects to ISO strings
        if self.start_time:
            result["start_time"] = self.start_time.isoformat()
        if self.end_time:
            result["end_time"] = self.end_time.isoformat()
        return result

    def calculate_rates(self) -> Dict[str, float]:
        """Calculate derived rates and percentages"""
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
    """Enhanced logger for dataset operations with structured logging"""

    def __init__(self, logger_name: str = __name__):
        self.logger = logging.getLogger(logger_name)
        self.current_operation: Optional[str] = None
        self.operation_start_time: Optional[float] = None
        self.metrics = ImportMetrics()

    def _log_structured(
        self,
        level: int,
        message: str,
        operation: Optional[str] = None,
        dataset_id: Optional[str] = None,
        dataset_type: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log with structured data"""

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

    def info(self, message: str, **kwargs) -> None:
        """Log info message with structured data"""
        self._log_structured(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with structured data"""
        self._log_structured(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with structured data"""
        self._log_structured(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured data"""
        self._log_structured(logging.DEBUG, message, **kwargs)

    @contextmanager
    def operation_context(
        self,
        operation: str,
        dataset_id: Optional[str] = None,
        dataset_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Context manager for tracking operations"""

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
        self, chunk_index: int, total_chunks: int, chunk_size: int, success: bool = True, **kwargs
    ) -> None:
        """Log chunk processing progress"""

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

    def log_memory_usage(self, memory_mb: float, operation: str = "unknown") -> None:
        """Log current memory usage"""

        self.debug(f"Memory usage: {memory_mb:.2f} MB", memory_mb=memory_mb, operation=operation)

        # Update metrics
        if memory_mb > self.metrics.peak_memory_mb:
            self.metrics.peak_memory_mb = memory_mb

    def log_retry_attempt(self, attempt: int, max_attempts: int, error: Optional[Exception] = None, **kwargs) -> None:
        """Log retry attempts"""

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
        self, prompts_stored: int, storage_time_seconds: float, storage_size_mb: float, **kwargs
    ) -> None:
        """Log PyRIT memory storage operations"""

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

    def log_import_summary(self, dataset_id: str, dataset_type: str, success: bool = True, **kwargs) -> None:
        """Log comprehensive import summary"""

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

    def reset_metrics(self) -> None:
        """Reset metrics for a new operation"""
        self.metrics = ImportMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)

    def finalize_metrics(self) -> ImportMetrics:
        """Finalize metrics and return copy"""
        self.metrics.end_time = datetime.now(timezone.utc)

        if self.metrics.start_time and self.metrics.end_time:
            self.metrics.processing_time_seconds = (self.metrics.end_time - self.metrics.start_time).total_seconds()

        return self.metrics


# Global logger instance
dataset_logger = DatasetLogger("violentutf.datasets")


# Convenience functions for common logging patterns
def log_dataset_operation_start(
    operation: str, dataset_id: str, dataset_type: str, user_id: Optional[str] = None, **kwargs
) -> None:
    """Log the start of a dataset operation"""
    dataset_logger.info(
        f"Starting {operation}",
        operation=operation,
        dataset_id=dataset_id,
        dataset_type=dataset_type,
        user_id=user_id,
        **kwargs,
    )


def log_dataset_operation_error(operation: str, dataset_id: str, error: Exception, **kwargs) -> None:
    """Log a dataset operation error"""
    dataset_logger.error(
        f"Error in {operation}: {str(error)}",
        operation=operation,
        dataset_id=dataset_id,
        error=str(error),
        error_type=type(error).__name__,
        **kwargs,
    )


def log_dataset_operation_success(operation: str, dataset_id: str, **kwargs) -> None:
    """Log successful completion of a dataset operation"""
    dataset_logger.info(f"Successfully completed {operation}", operation=operation, dataset_id=dataset_id, **kwargs)
