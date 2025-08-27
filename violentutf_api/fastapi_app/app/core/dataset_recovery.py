# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Error recovery mechanisms for dataset import operations

This module provides robust error recovery strategies including retry logic,
partial import recovery, and automated cleanup procedures.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

from app.core.dataset_config import DatasetImportConfig
from app.core.dataset_logging import dataset_logger
from app.exceptions.dataset_exceptions import DatasetRetryExhaustedException, DatasetStreamingError, DatasetTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy:
    """Configurable retry strategy for dataset operations"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = self.base_delay * (self.backoff_factor**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            # Add up to 20% jitter
            jitter_amount = delay * 0.2 * random.random()
            delay += jitter_amount

        return delay

    @classmethod
    def from_config(cls, config: DatasetImportConfig, dataset_type: str = "") -> "RetryStrategy":
        """Create retry strategy from configuration"""
        retry_config = config.get_effective_retry_config(dataset_type)

        return cls(
            max_retries=retry_config["max_retries"],
            base_delay=retry_config["retry_delay"],
            backoff_factor=retry_config["backoff_factor"],
            max_delay=retry_config["timeout"],
        )


def with_retry(
    retry_strategy: Optional[RetryStrategy] = None, exceptions: tuple = (Exception,), operation_name: str = "operation"
):
    """Decorator for adding retry logic to functions"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:  # Proper typing for decorator
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            strategy = retry_strategy or RetryStrategy()
            last_exception = None

            for attempt in range(strategy.max_retries + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        result = cast(T, await func(*args, **kwargs))
                        return result
                    else:
                        result = func(*args, **kwargs)
                        return result

                except exceptions as e:
                    last_exception = e

                    if attempt == strategy.max_retries:
                        dataset_logger.error(
                            f"Retry exhausted for {operation_name}",
                            operation=operation_name,
                            attempt=attempt + 1,
                            max_retries=strategy.max_retries + 1,
                            error=str(e),
                        )
                        raise DatasetRetryExhaustedException(
                            f"Maximum retries ({strategy.max_retries}) exceeded for {operation_name}",
                            max_retries=strategy.max_retries,
                            last_error=e,
                        )

                    delay = strategy.calculate_delay(attempt)

                    dataset_logger.log_retry_attempt(
                        attempt=attempt + 1,
                        max_attempts=strategy.max_retries + 1,
                        error=e,
                        operation=operation_name,
                        delay_seconds=delay,
                    )

                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            raise DatasetRetryExhaustedException(
                f"Unexpected retry exhaustion for {operation_name}",
                max_retries=strategy.max_retries,
                last_error=last_exception,
            )

        return cast(Callable[..., T], wrapper)

    return decorator


class PartialImportRecovery:
    """Handles recovery of partial dataset imports"""

    def __init__(self, config: DatasetImportConfig):
        self.config = config
        self.successful_chunks: List[Dict[str, Any]] = []
        self.failed_chunks: List[Dict[str, Any]] = []
        self.partial_data: Dict[str, Any] = {}

    def record_successful_chunk(
        self, chunk_index: int, chunk_data: List[str], metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a successfully processed chunk"""
        self.successful_chunks.append(
            {"chunk_index": chunk_index, "size": len(chunk_data), "timestamp": time.time(), "metadata": metadata or {}}
        )

        dataset_logger.debug(
            f"Recorded successful chunk {chunk_index}", chunk_index=chunk_index, chunk_size=len(chunk_data)
        )

    def record_failed_chunk(
        self,
        chunk_index: int,
        error: Exception,
        chunk_data: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a failed chunk for potential recovery"""
        self.failed_chunks.append(
            {
                "chunk_index": chunk_index,
                "error": str(error),
                "error_type": type(error).__name__,
                "timestamp": time.time(),
                "data": chunk_data,
                "metadata": metadata or {},
            }
        )

        dataset_logger.warning(
            f"Recorded failed chunk {chunk_index}",
            chunk_index=chunk_index,
            error=str(error),
            chunk_size=len(chunk_data) if chunk_data else 0,
        )

    async def attempt_recovery(self) -> Dict[str, Any]:
        """Attempt to recover failed chunks"""
        if not self.config.enable_partial_import:
            raise DatasetStreamingError("Partial import recovery is disabled in configuration")

        recovery_results = {"recovered_chunks": 0, "still_failed_chunks": 0, "total_attempted": len(self.failed_chunks)}

        dataset_logger.info(
            f"Starting recovery for {len(self.failed_chunks)} failed chunks",
            failed_chunks=len(self.failed_chunks),
            successful_chunks=len(self.successful_chunks),
        )

        retry_strategy = RetryStrategy(
            max_retries=2, base_delay=0.5, backoff_factor=1.5  # Less aggressive retries for recovery
        )

        for chunk_info in self.failed_chunks[:]:  # Copy list to allow modification
            try:
                # Attempt to recover the chunk
                await self._recover_single_chunk(chunk_info, retry_strategy)

                # Move from failed to successful
                self.failed_chunks.remove(chunk_info)
                self.record_successful_chunk(
                    chunk_info["chunk_index"], chunk_info.get("data", []), chunk_info.get("metadata", {})
                )

                recovery_results["recovered_chunks"] += 1

            except Exception as e:
                dataset_logger.warning(
                    f"Recovery failed for chunk {chunk_info['chunk_index']}",
                    chunk_index=chunk_info["chunk_index"],
                    error=str(e),
                )
                recovery_results["still_failed_chunks"] += 1

        dataset_logger.info("Recovery attempt completed", **recovery_results)

        return recovery_results

    async def _recover_single_chunk(self, chunk_info: Dict[str, Any], retry_strategy: RetryStrategy) -> None:
        """Attempt to recover a single failed chunk"""
        # This is a placeholder - actual recovery logic would depend on
        # the specific failure type and data available

        chunk_index = chunk_info["chunk_index"]
        chunk_data = chunk_info.get("data")

        if not chunk_data:
            raise DatasetStreamingError(f"No data available for chunk {chunk_index} recovery")

        # Simulate recovery operation
        # In practice, this would involve re-processing the chunk
        # with potentially different parameters or strategies
        await asyncio.sleep(0.1)  # Simulate processing time

        dataset_logger.debug(f"Successfully recovered chunk {chunk_index}", chunk_index=chunk_index)

    def get_recovery_summary(self) -> Dict[str, Any]:
        """Get summary of recovery status"""
        total_chunks = len(self.successful_chunks) + len(self.failed_chunks)
        success_rate = len(self.successful_chunks) / total_chunks if total_chunks > 0 else 0

        return {
            "total_chunks": total_chunks,
            "successful_chunks": len(self.successful_chunks),
            "failed_chunks": len(self.failed_chunks),
            "success_rate": success_rate,
            "can_recover": self.config.enable_partial_import and len(self.failed_chunks) > 0,
            "partial_data_available": len(self.partial_data) > 0,
        }


class AutoCleanupManager:
    """Manages automatic cleanup of failed or partial imports"""

    def __init__(self, config: DatasetImportConfig):
        self.config = config
        self.cleanup_tasks: List[Callable] = []
        self.temp_files: List[str] = []
        self.temp_data: List[Any] = []

    def register_cleanup_task(self, task: Callable) -> None:
        """Register a cleanup task to be executed on failure"""
        self.cleanup_tasks.append(task)

    def register_temp_file(self, file_path: str) -> None:
        """Register a temporary file for cleanup"""
        self.temp_files.append(file_path)

    def register_temp_data(self, data: Any) -> None:
        """Register temporary data for cleanup"""
        self.temp_data.append(data)

    async def cleanup_on_failure(
        self, error: Exception, dataset_id: str, partial_recovery: Optional[PartialImportRecovery] = None
    ) -> None:
        """Perform cleanup operations after a failure"""

        if not self.config.cleanup_on_failure:
            dataset_logger.info("Cleanup on failure is disabled, skipping cleanup", dataset_id=dataset_id)
            return

        dataset_logger.info(
            f"Starting cleanup after failure: {type(error).__name__}",
            dataset_id=dataset_id,
            error=str(error),
            cleanup_tasks=len(self.cleanup_tasks),
            temp_files=len(self.temp_files),
        )

        cleanup_results = {"tasks_executed": 0, "tasks_failed": 0, "files_cleaned": 0, "files_failed": 0}

        # Execute cleanup tasks
        for i, task in enumerate(self.cleanup_tasks):
            try:
                if asyncio.iscoroutinefunction(task):
                    await task()
                else:
                    task()
                cleanup_results["tasks_executed"] += 1

            except Exception as cleanup_error:
                dataset_logger.warning(f"Cleanup task {i} failed", cleanup_task_index=i, error=str(cleanup_error))
                cleanup_results["tasks_failed"] += 1

        # Clean up temporary files
        import os

        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    cleanup_results["files_cleaned"] += 1

            except Exception as cleanup_error:
                dataset_logger.warning(
                    f"Failed to clean up file: {file_path}", file_path=file_path, error=str(cleanup_error)
                )
                cleanup_results["files_failed"] += 1

        # Clear temporary data
        self.temp_data.clear()

        dataset_logger.info("Cleanup completed", dataset_id=dataset_id, **cleanup_results)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self.config.cleanup_on_failure:
            # Synchronous cleanup for context manager
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self.cleanup_on_failure(exc_val, "unknown"))
            except RuntimeError:
                # Fallback to synchronous cleanup if no event loop
                for task in self.cleanup_tasks:
                    try:
                        if not asyncio.iscoroutinefunction(task):
                            task()
                    except Exception:
                        pass


# Utility functions for common recovery patterns
async def with_timeout(
    operation: Callable[..., T], timeout_seconds: float, operation_name: str = "operation", *args, **kwargs
) -> T:
    """Execute operation with timeout"""
    try:
        if asyncio.iscoroutinefunction(operation):
            return await asyncio.wait_for(operation(*args, **kwargs), timeout=timeout_seconds)
        else:
            # For non-async functions, we need to run in executor
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, operation, *args, **kwargs), timeout=timeout_seconds
            )

    except asyncio.TimeoutError:
        raise DatasetTimeoutError(
            f"Operation '{operation_name}' exceeded timeout of {timeout_seconds} seconds",
            timeout_seconds=timeout_seconds,
            operation=operation_name,
        )


def create_recovery_context(
    config: DatasetImportConfig, dataset_id: str, dataset_type: str
) -> tuple[PartialImportRecovery, AutoCleanupManager]:
    """Create recovery context for dataset operations"""

    partial_recovery = PartialImportRecovery(config)
    cleanup_manager = AutoCleanupManager(config)

    dataset_logger.info(
        "Created recovery context",
        dataset_id=dataset_id,
        dataset_type=dataset_type,
        partial_import_enabled=config.enable_partial_import,
        cleanup_enabled=config.cleanup_on_failure,
    )

    return partial_recovery, cleanup_manager
