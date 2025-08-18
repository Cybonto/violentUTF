# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Structured logging utilities for dataset import operations

This module provides enhanced logging capabilities with structured data,
metrics tracking, and comprehensive error reporting for dataset operations.
"""

import asyncio
import gzip
import json
import logging
import logging.handlers
import os
import shutil
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Logging level enumeration"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class OperationType(Enum):
    """Dataset operation types for categorization"""

    CONVERSION = "dataset_conversion"
    IMPORT = "dataset_import"
    EXPORT = "dataset_export"
    VALIDATION = "dataset_validation"
    CLEANUP = "dataset_cleanup"
    ANALYSIS = "dataset_analysis"
    BACKUP = "dataset_backup"
    RECOVERY = "dataset_recovery"


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
    memory_samples: List[float] = field(default_factory=list)

    # Streaming metrics
    total_chunks: int = 0
    successful_chunks: int = 0
    failed_chunks: int = 0
    avg_chunk_size: float = 0.0
    chunk_processing_times: List[float] = field(default_factory=list)

    # Retry metrics
    total_retries: int = 0
    max_retries_per_operation: int = 0
    retry_reasons: List[str] = field(default_factory=list)

    # PyRIT memory metrics
    pyrit_storage_size_mb: float = 0.0
    pyrit_storage_time_seconds: float = 0.0

    # Dataset-specific metrics
    dataset_type: str = ""
    dataset_source: str = ""
    dataset_version: str = ""
    conversion_strategy: str = ""

    # User and session info
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None

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

        # Calculate average chunk processing time
        if self.chunk_processing_times:
            rates["avg_chunk_time_seconds"] = sum(self.chunk_processing_times) / len(self.chunk_processing_times)
            rates["max_chunk_time_seconds"] = max(self.chunk_processing_times)
            rates["min_chunk_time_seconds"] = min(self.chunk_processing_times)

        # Calculate memory statistics
        if self.memory_samples:
            rates["avg_memory_mb"] = sum(self.memory_samples) / len(self.memory_samples)
            rates["max_memory_mb"] = max(self.memory_samples)
            rates["min_memory_mb"] = min(self.memory_samples)

        return rates


@dataclass
class LogConfig:
    """Configuration for dataset logging"""

    # Environment
    environment: str = "development"  # development, staging, production

    # Log levels
    log_level: str = "INFO"
    console_log_level: str = "INFO"
    file_log_level: str = "DEBUG"

    # File logging
    enable_file_logging: bool = True
    log_dir: Path = Path("logs/datasets")
    log_file_prefix: str = "dataset_ops"
    max_log_file_size_mb: int = 100
    backup_count: int = 10
    compression: bool = True

    # Log rotation
    rotation_interval: str = "midnight"  # midnight, W0-W6, or time
    retention_days: int = 30

    # Performance
    async_logging: bool = True
    buffer_size: int = 1024

    # Features
    enable_metrics: bool = True
    enable_correlation_id: bool = True
    enable_structured_logging: bool = True
    enable_performance_tracking: bool = True

    @classmethod
    def from_environment(cls) -> "LogConfig":
        """Load configuration from environment variables"""
        env = os.getenv("ENVIRONMENT", "development")

        # Environment-specific defaults
        defaults = {
            "development": {
                "log_level": "DEBUG",
                "console_log_level": "DEBUG",
                "file_log_level": "DEBUG",
                "retention_days": 7,
                "async_logging": False,
            },
            "staging": {
                "log_level": "INFO",
                "console_log_level": "INFO",
                "file_log_level": "DEBUG",
                "retention_days": 14,
                "async_logging": True,
            },
            "production": {
                "log_level": "INFO",
                "console_log_level": "WARNING",
                "file_log_level": "INFO",
                "retention_days": 30,
                "async_logging": True,
            },
        }

        config_defaults = defaults.get(env, defaults["development"])

        return cls(
            environment=env,
            log_level=os.getenv("DATASET_LOG_LEVEL", str(config_defaults["log_level"])),
            console_log_level=os.getenv("DATASET_CONSOLE_LOG_LEVEL", str(config_defaults["console_log_level"])),
            file_log_level=os.getenv("DATASET_FILE_LOG_LEVEL", str(config_defaults["file_log_level"])),
            enable_file_logging=os.getenv("DATASET_ENABLE_FILE_LOGGING", "true").lower() == "true",
            log_dir=Path(os.getenv("DATASET_LOG_DIR", "logs/datasets")),
            log_file_prefix=os.getenv("DATASET_LOG_FILE_PREFIX", "dataset_ops"),
            max_log_file_size_mb=int(os.getenv("DATASET_MAX_LOG_FILE_SIZE_MB", "100")),
            backup_count=int(os.getenv("DATASET_LOG_BACKUP_COUNT", "10")),
            compression=os.getenv("DATASET_LOG_COMPRESSION", "true").lower() == "true",
            rotation_interval=os.getenv("DATASET_LOG_ROTATION_INTERVAL", "midnight"),
            retention_days=int(os.getenv("DATASET_LOG_RETENTION_DAYS", str(config_defaults["retention_days"]))),
            async_logging=os.getenv("DATASET_ASYNC_LOGGING", str(config_defaults["async_logging"])).lower() == "true",
            buffer_size=int(os.getenv("DATASET_LOG_BUFFER_SIZE", "1024")),
            enable_metrics=os.getenv("DATASET_ENABLE_METRICS", "true").lower() == "true",
            enable_correlation_id=os.getenv("DATASET_ENABLE_CORRELATION_ID", "true").lower() == "true",
            enable_structured_logging=os.getenv("DATASET_ENABLE_STRUCTURED_LOGGING", "true").lower() == "true",
            enable_performance_tracking=os.getenv("DATASET_ENABLE_PERFORMANCE_TRACKING", "true").lower() == "true",
        )


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging to files"""

    def format(self, record):
        """Format log record as JSON"""
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields from structured logging
        if hasattr(record, "operation"):
            log_obj["operation"] = record.operation
        if hasattr(record, "dataset_id"):
            log_obj["dataset_id"] = record.dataset_id
        if hasattr(record, "dataset_type"):
            log_obj["dataset_type"] = record.dataset_type
        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id
        if hasattr(record, "correlation_id"):
            log_obj["correlation_id"] = record.correlation_id
        if hasattr(record, "environment"):
            log_obj["environment"] = record.environment

        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "pathname",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "getMessage",
                "operation",
                "dataset_id",
                "dataset_type",
                "user_id",
                "correlation_id",
                "environment",
            ]:
                log_obj[key] = value

        return json.dumps(log_obj, default=str)


class StructuredFormatter(logging.Formatter):
    """Structured formatter for console output"""

    def format(self, record):
        """Format log record with structured data"""
        # Build structured suffix
        structured_parts = []

        if hasattr(record, "correlation_id") and record.correlation_id:
            structured_parts.append(f"correlation_id={record.correlation_id}")
        if hasattr(record, "operation") and record.operation:
            structured_parts.append(f"operation={record.operation}")
        if hasattr(record, "dataset_id") and record.dataset_id:
            structured_parts.append(f"dataset_id={record.dataset_id}")
        if hasattr(record, "user_id") and record.user_id:
            structured_parts.append(f"user_id={record.user_id}")

        # Format base message
        base_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        if structured_parts:
            base_format += f" [{', '.join(structured_parts)}]"

        self._style._fmt = base_format
        return super().format(record)


class DatasetLogger:
    """Enhanced logger for dataset operations with structured logging"""

    def __init__(self, logger_name: str = __name__, config: Optional[LogConfig] = None):
        self.logger_name = logger_name
        self.logger = logging.getLogger(logger_name)
        self.config = config or LogConfig.from_environment()
        self.current_operation: Optional[str] = None
        self.operation_start_time: Optional[float] = None
        self.metrics = ImportMetrics()
        self.correlation_id: Optional[str] = None
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Setup logging handlers based on configuration"""
        # Set base logger level
        self.logger.setLevel(getattr(logging, self.config.log_level))
        self.logger.handlers = []  # Clear existing handlers

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.config.console_log_level))

        if self.config.enable_structured_logging:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(console_handler)

        # File handler with rotation
        if self.config.enable_file_logging:
            self._setup_file_handler()

    def _setup_file_handler(self) -> None:
        """Setup file handler with rotation and compression"""
        # Create log directory
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file path
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = self.config.log_dir / f"{self.config.log_file_prefix}_{timestamp}.log"

        # Rotating file handler
        file_handler: Union[logging.handlers.TimedRotatingFileHandler, logging.handlers.RotatingFileHandler]
        if self.config.rotation_interval == "midnight":
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file,
                when="midnight",
                interval=1,
                backupCount=self.config.backup_count,
                encoding="utf-8",
            )
        else:
            # Size-based rotation
            max_bytes = self.config.max_log_file_size_mb * 1024 * 1024
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=self.config.backup_count,
                encoding="utf-8",
            )

        file_handler.setLevel(getattr(logging, self.config.file_log_level))

        # Set formatter
        if self.config.enable_structured_logging:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

        # Add compression if enabled
        if self.config.compression:
            file_handler.rotator = self._compress_log

        self.logger.addHandler(file_handler)

        # Clean up old logs
        self._cleanup_old_logs()

    def _compress_log(self, source: str, dest: str) -> None:
        """Compress rotated log files"""
        with open(source, "rb") as f_in:
            with gzip.open(f"{dest}.gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(source)

    def _cleanup_old_logs(self) -> None:
        """Remove logs older than retention period"""
        if self.config.retention_days <= 0:
            return

        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)

        # Look for any log files that match the pattern
        patterns = [
            f"{self.config.log_file_prefix}*.log",
            f"{self.config.log_file_prefix}*.log.gz",
            f"*{self.config.log_file_prefix}*.log",
            f"*{self.config.log_file_prefix}*.log.gz",
        ]

        for pattern in patterns:
            for log_file in self.config.log_dir.glob(pattern):
                try:
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        log_file.unlink()
                        logger.debug(f"Removed old log file: {log_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove old log file {log_file}: {e}")

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
            "log_message": message,  # Changed from "message" to avoid conflict
            "operation": operation or self.current_operation,
            "dataset_id": dataset_id,
            "dataset_type": dataset_type,
            "user_id": user_id or self.metrics.user_id,
            "session_id": self.metrics.session_id,
            "correlation_id": self.correlation_id or self.metrics.correlation_id,
            "environment": self.config.environment,
            **kwargs,
        }

        # Add performance metrics if enabled
        if self.config.enable_performance_tracking and self.operation_start_time:
            structured_data["operation_elapsed_seconds"] = time.time() - self.operation_start_time

        # Filter out None values
        structured_data = {k: v for k, v in structured_data.items() if v is not None}

        # Log based on configuration
        if self.config.enable_structured_logging:
            # Add structured data as extra fields (excluding protected keys)
            # Remove any fields that conflict with LogRecord attributes
            protected_keys = {
                "message",
                "asctime",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "pathname",
                "process",
                "processName",
                "thread",
                "threadName",
            }
            safe_data = {k: v for k, v in structured_data.items() if k not in protected_keys}
            self.logger.log(level, message, extra=safe_data)
        else:
            # Create log message with structured data inline
            log_message = f"{message} | {json.dumps(structured_data, default=str)}"
            self.logger.log(level, log_message)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with structured data"""
        # Early exit if info logging is disabled to avoid overhead
        if not self.logger.isEnabledFor(logging.INFO):
            return
        self._log_structured(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with structured data"""
        # Early exit if warning logging is disabled to avoid overhead
        if not self.logger.isEnabledFor(logging.WARNING):
            return
        self._log_structured(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with structured data"""
        # Early exit if error logging is disabled to avoid overhead
        if not self.logger.isEnabledFor(logging.ERROR):
            return
        self._log_structured(logging.ERROR, message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with structured data"""
        # Early exit if debug logging is disabled to avoid overhead
        if not self.logger.isEnabledFor(logging.DEBUG):
            return
        self._log_structured(logging.DEBUG, message, **kwargs)

    def set_correlation_id(self, correlation_id: Optional[str] = None) -> str:
        """Set or generate correlation ID for tracking related operations"""
        if correlation_id:
            self.correlation_id = correlation_id
        else:
            self.correlation_id = str(uuid.uuid4())
        self.metrics.correlation_id = self.correlation_id
        return self.correlation_id

    def set_user_context(self, user_id: str, session_id: Optional[str] = None) -> None:
        """Set user context for all subsequent logs"""
        self.metrics.user_id = user_id
        self.metrics.session_id = session_id or str(uuid.uuid4())

    @contextmanager
    def operation_context(
        self,
        operation: str,
        dataset_id: Optional[str] = None,
        dataset_type: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        """Context manager for tracking operations"""

        previous_operation = self.current_operation
        previous_correlation_id = self.correlation_id

        self.current_operation = operation
        self.operation_start_time = time.time()

        # Set correlation ID if provided or generate new one
        if correlation_id or not self.correlation_id:
            self.set_correlation_id(correlation_id)

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
            if correlation_id:  # Only reset if we changed it
                self.correlation_id = previous_correlation_id

    def log_chunk_progress(
        self,
        chunk_index: int,
        total_chunks: int,
        chunk_size: int,
        success: bool = True,
        processing_time: Optional[float] = None,
        **kwargs,
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
            processing_time_seconds=processing_time,
            **kwargs,
        )

        # Update metrics
        self.metrics.total_chunks = max(self.metrics.total_chunks, total_chunks)
        if success:
            self.metrics.successful_chunks += 1
        else:
            self.metrics.failed_chunks += 1

        if processing_time:
            self.metrics.chunk_processing_times.append(processing_time)

        # Update average chunk size
        if self.metrics.successful_chunks > 0:
            self.metrics.avg_chunk_size = (
                self.metrics.avg_chunk_size * (self.metrics.successful_chunks - 1) + chunk_size
            ) / self.metrics.successful_chunks

    def log_memory_usage(self, memory_mb: float, operation: str = "unknown") -> None:
        """Log current memory usage"""

        self.debug(f"Memory usage: {memory_mb:.2f} MB", memory_mb=memory_mb, operation=operation)

        # Update metrics
        self.metrics.memory_samples.append(memory_mb)
        if memory_mb > self.metrics.peak_memory_mb:
            self.metrics.peak_memory_mb = memory_mb

        # Calculate running average
        if self.metrics.memory_samples:
            self.metrics.avg_memory_mb = sum(self.metrics.memory_samples) / len(self.metrics.memory_samples)

    def log_retry_attempt(self, attempt: int, max_attempts: int, error: Optional[Exception] = None, **kwargs) -> None:
        """Log retry attempts"""

        error_msg = str(error) if error else "Unknown error"
        self.warning(
            f"Retry attempt {attempt}/{max_attempts}: {error_msg}",
            retry_attempt=attempt,
            max_attempts=max_attempts,
            error=error_msg,
            error_type=type(error).__name__ if error else None,
            **kwargs,
        )

        # Update metrics
        self.metrics.total_retries += 1
        if attempt > self.metrics.max_retries_per_operation:
            self.metrics.max_retries_per_operation = attempt
        if error:
            self.metrics.retry_reasons.append(f"{type(error).__name__}: {str(error)[:100]}")

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

    def log_conversion_details(
        self,
        dataset_type: str,
        conversion_strategy: str,
        input_format: str,
        output_format: str,
        **kwargs,
    ) -> None:
        """Log dataset conversion details"""
        self.info(
            f"Dataset conversion: {dataset_type} using {conversion_strategy}",
            dataset_type=dataset_type,
            conversion_strategy=conversion_strategy,
            input_format=input_format,
            output_format=output_format,
            **kwargs,
        )

        # Update metrics
        self.metrics.dataset_type = dataset_type
        self.metrics.conversion_strategy = conversion_strategy

    def reset_metrics(self) -> None:
        """Reset metrics for a new operation"""
        # Preserve user context
        user_id = self.metrics.user_id
        session_id = self.metrics.session_id

        self.metrics = ImportMetrics()
        self.metrics.start_time = datetime.now(timezone.utc)

        # Restore user context
        self.metrics.user_id = user_id
        self.metrics.session_id = session_id

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


# Log analysis utilities
class LogAnalyzer:
    """Utilities for analyzing dataset operation logs"""

    def __init__(self, log_dir: Path = Path("logs/datasets")):
        self.log_dir = log_dir

    def read_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        operation: Optional[str] = None,
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read and filter log entries"""
        logs = []

        # Find log files in the directory
        log_files = list(self.log_dir.glob("*.log")) + list(self.log_dir.glob("*.log.gz"))

        for log_file in log_files:
            if log_file.suffix == ".gz":
                with gzip.open(log_file, "rt") as f:
                    lines = f.readlines()
            else:
                with open(log_file, "r") as f:
                    lines = f.readlines()

            for line in lines:
                try:
                    # Try to parse as JSON
                    log_entry = json.loads(line)

                    # Apply filters
                    if start_time and datetime.fromisoformat(log_entry["timestamp"]) < start_time:
                        continue
                    if end_time and datetime.fromisoformat(log_entry["timestamp"]) > end_time:
                        continue
                    if operation and log_entry.get("operation") != operation:
                        continue
                    if dataset_id and log_entry.get("dataset_id") != dataset_id:
                        continue
                    if user_id and log_entry.get("user_id") != user_id:
                        continue
                    if correlation_id and log_entry.get("correlation_id") != correlation_id:
                        continue

                    logs.append(log_entry)
                except json.JSONDecodeError:
                    # Skip non-JSON lines
                    continue

        return logs

    def analyze_performance(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze performance metrics from logs"""
        if not logs:
            return {}

        performance_metrics = {
            "total_operations": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "avg_processing_time": 0,
            "max_processing_time": 0,
            "min_processing_time": float("inf"),
            "total_prompts_processed": 0,
            "avg_prompts_per_second": 0,
            "memory_usage": {
                "peak": 0,
                "average": 0,
            },
            "retry_statistics": {
                "total_retries": 0,
                "operations_with_retries": 0,
            },
        }

        processing_times = []
        memory_samples = []
        prompts_processed = []

        for log in logs:
            if log.get("message", "").startswith("Completed operation"):
                performance_metrics["total_operations"] += 1

                if "operation_time_seconds" in log:
                    time_seconds = log["operation_time_seconds"]
                    processing_times.append(time_seconds)
                    performance_metrics["max_processing_time"] = max(
                        performance_metrics["max_processing_time"], time_seconds
                    )
                    performance_metrics["min_processing_time"] = min(
                        performance_metrics["min_processing_time"], time_seconds
                    )

            if log.get("level") == "ERROR":
                performance_metrics["failed_operations"] += 1

            if "memory_mb" in log:
                memory_samples.append(log["memory_mb"])

            if "prompts_stored" in log:
                prompts_processed.append(log["prompts_stored"])

            if "retry_attempt" in log:
                performance_metrics["retry_statistics"]["total_retries"] += 1

        # Calculate averages
        if processing_times:
            performance_metrics["avg_processing_time"] = sum(processing_times) / len(processing_times)

        if memory_samples:
            performance_metrics["memory_usage"]["average"] = sum(memory_samples) / len(memory_samples)
            performance_metrics["memory_usage"]["peak"] = max(memory_samples)

        if prompts_processed:
            performance_metrics["total_prompts_processed"] = sum(prompts_processed)
            if processing_times:
                total_time = sum(processing_times)
                performance_metrics["avg_prompts_per_second"] = (
                    sum(prompts_processed) / total_time if total_time > 0 else 0
                )

        performance_metrics["successful_operations"] = (
            performance_metrics["total_operations"] - performance_metrics["failed_operations"]
        )

        return performance_metrics

    def find_errors(self, logs: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Find all error entries in logs"""
        if logs is None:
            logs = self.read_logs()

        return [log for log in logs if log.get("level") in ["ERROR", "CRITICAL"]]

    def get_operation_trace(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get complete trace of an operation by correlation ID"""
        logs = self.read_logs(correlation_id=correlation_id)
        return sorted(logs, key=lambda x: x.get("timestamp", ""))

    def generate_summary_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive summary report"""
        logs = self.read_logs(start_time=start_time, end_time=end_time)

        performance = self.analyze_performance(logs)
        errors = self.find_errors(logs)

        # Group operations by type
        operations_by_type: Dict[str, int] = {}
        for log in logs:
            if op := log.get("operation"):
                operations_by_type[op] = operations_by_type.get(op, 0) + 1

        # Group by dataset type
        datasets_processed: Dict[str, int] = {}
        for log in logs:
            if dt := log.get("dataset_type"):
                datasets_processed[dt] = datasets_processed.get(dt, 0) + 1

        return {
            "summary": {
                "total_log_entries": len(logs),
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None,
                },
            },
            "performance": performance,
            "errors": {
                "total_errors": len(errors),
                "error_rate": len(errors) / len(logs) if logs else 0,
                "recent_errors": errors[-10:],  # Last 10 errors
            },
            "operations": operations_by_type,
            "datasets": datasets_processed,
        }


# Initialize global log analyzer
log_analyzer = LogAnalyzer()
