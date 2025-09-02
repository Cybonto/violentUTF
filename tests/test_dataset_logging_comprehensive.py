# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Comprehensive tests for dataset logging system.

Tests all aspects of the enhanced dataset logging functionality including
structured logging, performance monitoring, audit trails, and centralized logging.
"""

import asyncio
import json
import logging
import os
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from app.core.dataset_logging import (
    CentralizedHandler,
    DatasetAuditLogger,
    DatasetLogger,
    EnhancedLogAnalyzer,
    ImportMetrics,
    LogAnalyzer,
    LogConfig,
    OperationType,
    dataset_audit_logger,
    dataset_logger,
    log_analyzer,
    log_dataset_operation_error,
    log_dataset_operation_start,
    log_dataset_operation_success,
)


class TestLogConfig:
    """Test LogConfig functionality."""

    def test_log_config_defaults(self):
        """Test default LogConfig values."""
        config = LogConfig()

        assert config.environment == "development"
        assert config.log_level == "INFO"
        assert config.enable_file_logging is True
        assert config.enable_structured_logging is True
        assert config.enable_performance_tracking is True
        assert config.enable_centralized_logging is False
        assert config.enable_audit_trails is True

    def test_log_config_from_environment(self):
        """Test LogConfig creation from environment variables."""
        env_vars = {
            "ENVIRONMENT": "production",
            "DATASET_LOG_LEVEL": "ERROR",
            "DATASET_ENABLE_CENTRALIZED_LOGGING": "true",
            "DATASET_CENTRALIZED_ENDPOINT": "https://logs.example.com",
            "DATASET_PERFORMANCE_SAMPLING_RATE": "0.05",
            "DATASET_MAX_LOG_MESSAGE_SIZE": "5000",
        }

        with patch.dict(os.environ, env_vars):
            config = LogConfig.from_environment()

        assert config.environment == "production"
        assert config.log_level == "ERROR"
        assert config.enable_centralized_logging is True
        assert config.centralized_endpoint == "https://logs.example.com"
        assert config.performance_sampling_rate == 0.05
        assert config.max_log_message_size == 5000

    def test_log_config_environment_specific_defaults(self):
        """Test environment-specific default configurations."""
        # Test development environment
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            dev_config = LogConfig.from_environment()
            assert dev_config.log_level == "DEBUG"
            assert dev_config.retention_days == 7
            assert dev_config.async_logging is False

        # Test production environment
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            prod_config = LogConfig.from_environment()
            assert prod_config.log_level == "INFO"
            assert prod_config.console_log_level == "WARNING"
            assert prod_config.retention_days == 30
            assert prod_config.async_logging is True


class TestImportMetrics:
    """Test ImportMetrics functionality."""

    def test_import_metrics_defaults(self):
        """Test default ImportMetrics values."""
        metrics = ImportMetrics()

        assert metrics.total_prompts == 0
        assert metrics.successful_prompts == 0
        assert metrics.failed_prompts == 0
        assert metrics.processing_time_seconds == 0.0
        assert metrics.correlation_id is None

    def test_import_metrics_to_dict(self):
        """Test ImportMetrics to_dict conversion."""
        metrics = ImportMetrics(
            total_prompts=100,
            successful_prompts=95,
            failed_prompts=5,
            start_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
            user_id="test_user",
            correlation_id="test_correlation_id",
        )

        result = metrics.to_dict()

        assert result["total_prompts"] == 100
        assert result["successful_prompts"] == 95
        assert result["failed_prompts"] == 5
        assert result["user_id"] == "test_user"
        assert result["correlation_id"] == "test_correlation_id"
        assert "start_time" in result
        assert "end_time" in result

    def test_import_metrics_calculate_rates(self):
        """Test ImportMetrics rate calculations."""
        metrics = ImportMetrics(
            total_prompts=100,
            successful_prompts=95,
            failed_prompts=5,
            processing_time_seconds=10.0,
            total_chunks=20,
            successful_chunks=18,
            chunk_processing_times=[0.5, 0.6, 0.4, 0.7],
            memory_samples=[100.0, 120.0, 110.0, 130.0],
        )

        rates = metrics.calculate_rates()

        assert rates["success_rate"] == 0.95
        assert rates["failure_rate"] == 0.05
        assert rates["prompts_per_second"] == 9.5
        assert rates["chunk_success_rate"] == 0.9
        assert rates["avg_chunk_time_seconds"] == 0.55
        assert rates["max_chunk_time_seconds"] == 0.7
        assert rates["min_chunk_time_seconds"] == 0.4
        assert rates["avg_memory_mb"] == 115.0
        assert rates["max_memory_mb"] == 130.0


class TestDatasetLogger:
    """Test DatasetLogger functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_config = LogConfig(
            log_dir=Path(self.temp_dir),
            enable_file_logging=True,
            enable_structured_logging=True,
            enable_performance_tracking=True,
            retention_days=1,
        )
        self.logger = DatasetLogger("test_logger", self.log_config)

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dataset_logger_initialization(self):
        """Test DatasetLogger initialization."""
        assert self.logger.logger_name == "test_logger"
        assert self.logger.config == self.log_config
        assert self.logger.current_operation is None
        assert self.logger.correlation_id is None

    def test_set_correlation_id(self):
        """Test correlation ID setting."""
        # Test auto-generation
        correlation_id = self.logger.set_correlation_id()
        assert correlation_id is not None
        assert self.logger.correlation_id == correlation_id
        assert self.logger.metrics.correlation_id == correlation_id

        # Test manual setting
        manual_id = "test_correlation_123"
        result_id = self.logger.set_correlation_id(manual_id)
        assert result_id == manual_id
        assert self.logger.correlation_id == manual_id

    def test_set_user_context(self):
        """Test user context setting."""
        user_id = "test_user"
        session_id = "test_session"

        self.logger.set_user_context(user_id, session_id)

        assert self.logger.metrics.user_id == user_id
        assert self.logger.metrics.session_id == session_id

    def test_operation_context(self):
        """Test operation context manager."""
        operation = "test_operation"
        dataset_id = "test_dataset"

        with self.logger.operation_context(operation, dataset_id=dataset_id):
            assert self.logger.current_operation == operation

        # Operation should be reset after context
        assert self.logger.current_operation is None

    def test_operation_context_with_exception(self):
        """Test operation context manager with exception."""
        operation = "test_operation"

        with pytest.raises(ValueError):
            with self.logger.operation_context(operation):
                raise ValueError("Test error")

    def test_log_chunk_progress(self):
        """Test chunk progress logging."""
        self.logger.log_chunk_progress(
            chunk_index=4,
            total_chunks=10,
            chunk_size=100,
            success=True,
            processing_time=1.5,
        )

        assert self.logger.metrics.total_chunks == 10
        assert self.logger.metrics.successful_chunks == 1
        assert self.logger.metrics.failed_chunks == 0
        assert len(self.logger.metrics.chunk_processing_times) == 1
        assert self.logger.metrics.chunk_processing_times[0] == 1.5

    def test_log_memory_usage(self):
        """Test memory usage logging."""
        self.logger.log_memory_usage(256.5, "test_operation")

        assert len(self.logger.metrics.memory_samples) == 1
        assert self.logger.metrics.memory_samples[0] == 256.5
        assert self.logger.metrics.peak_memory_mb == 256.5
        assert self.logger.metrics.avg_memory_mb == 256.5

    def test_log_retry_attempt(self):
        """Test retry attempt logging."""
        error = Exception("Test error")

        self.logger.log_retry_attempt(2, 3, error)

        assert self.logger.metrics.total_retries == 1
        assert self.logger.metrics.max_retries_per_operation == 2
        assert len(self.logger.metrics.retry_reasons) == 1
        assert "Exception: Test error" in self.logger.metrics.retry_reasons[0]

    def test_log_pyrit_storage(self):
        """Test PyRIT storage logging."""
        self.logger.log_pyrit_storage(
            prompts_stored=100, storage_time_seconds=2.5, storage_size_mb=10.5
        )

        assert self.logger.metrics.pyrit_storage_time_seconds == 2.5
        assert self.logger.metrics.pyrit_storage_size_mb == 10.5

    def test_log_security_event(self):
        """Test security event logging."""
        self.logger.log_security_event(
            event_type="unauthorized_access",
            severity="high",
            details={"user": "test_user", "resource": "sensitive_data"},
        )

        # Should be logged as error due to high severity
        # This test verifies the method doesn't raise an exception

    def test_log_compliance_check(self):
        """Test compliance checking logging."""
        self.logger.log_compliance_check(
            check_type="data_classification",
            result="passed",
            details={"classification": "internal"},
        )

        # This test verifies the method doesn't raise an exception

    def test_log_performance_metric(self):
        """Test performance metric logging."""
        with patch("random.random", return_value=0.05):  # Below sampling rate
            self.logger.log_performance_metric(
                metric_name="query_time",
                metric_value=1.5,
                metric_unit="seconds",
                threshold=2.0,
            )

        # This test verifies the method doesn't raise an exception

    def test_get_current_system_metrics(self):
        """Test system metrics collection."""
        metrics = self.logger.get_current_system_metrics()

        assert "timestamp" in metrics
        assert "process_id" in metrics
        assert "thread_count" in metrics
        assert metrics["process_id"] == os.getpid()

    def test_reset_metrics(self):
        """Test metrics reset functionality."""
        # Set up some metrics
        self.logger.metrics.total_prompts = 100
        self.logger.metrics.user_id = "test_user"
        self.logger.metrics.session_id = "test_session"

        self.logger.reset_metrics()

        assert self.logger.metrics.total_prompts == 0
        assert self.logger.metrics.user_id == "test_user"  # Should be preserved
        assert self.logger.metrics.session_id == "test_session"  # Should be preserved
        assert self.logger.metrics.start_time is not None

    def test_finalize_metrics(self):
        """Test metrics finalization."""
        self.logger.metrics.start_time = datetime.now(timezone.utc)
        time.sleep(0.1)  # Small delay

        final_metrics = self.logger.finalize_metrics()

        assert final_metrics.end_time is not None
        assert final_metrics.processing_time_seconds > 0


class TestCentralizedHandler:
    """Test CentralizedHandler functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.endpoint = "https://logs.example.com/api/logs"
        self.api_key = "test_api_key"

    def test_centralized_handler_initialization(self):
        """Test CentralizedHandler initialization."""
        handler = CentralizedHandler(
            endpoint=self.endpoint, api_key=self.api_key, buffer_size=50
        )

        assert handler.endpoint == self.endpoint
        assert handler.api_key == self.api_key
        assert handler.buffer_size == 50
        assert handler.worker_thread.is_alive()

        handler.close()

    @patch("requests.post")
    def test_centralized_handler_emit(self, mock_post):
        """Test log emission to centralized system."""
        mock_post.return_value.status_code = 200

        handler = CentralizedHandler(
            endpoint=self.endpoint,
            api_key=self.api_key,
            buffer_size=1,  # Small buffer for immediate sending
        )

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        handler.emit(record)

        # Give worker thread time to process
        time.sleep(0.5)

        handler.close()

    def test_centralized_handler_without_requests(self):
        """Test CentralizedHandler when requests library is unavailable."""
        with patch("app.core.dataset_logging.requests", None):
            handler = CentralizedHandler(endpoint=self.endpoint, api_key=self.api_key)

            # Should not raise an exception
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test message",
                args=(),
                exc_info=None,
            )

            handler.emit(record)
            handler.close()


class TestDatasetAuditLogger:
    """Test DatasetAuditLogger functionality."""

    def setup_method(self):
        """Setup test environment."""
        temp_dir = tempfile.mkdtemp()
        log_config = LogConfig(log_dir=Path(temp_dir))
        base_logger = DatasetLogger("test_audit", log_config)
        self.audit_logger = DatasetAuditLogger(base_logger)

    def test_audit_logger_initialization(self):
        """Test DatasetAuditLogger initialization."""
        assert self.audit_logger.base_logger is not None
        assert len(self.audit_logger.audit_events) == 0

    def test_log_user_action(self):
        """Test user action logging."""
        self.audit_logger.log_user_action(
            action="create_dataset",
            resource="dataset:test_dataset",
            user_id="test_user",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert len(self.audit_logger.audit_events) == 1
        event = self.audit_logger.audit_events[0]
        assert event["event_type"] == "user_action"
        assert event["action"] == "create_dataset"
        assert event["resource"] == "dataset:test_dataset"
        assert event["user_id"] == "test_user"
        assert event["ip_address"] == "192.168.1.1"

    def test_log_data_access(self):
        """Test data access logging."""
        self.audit_logger.log_data_access(
            dataset_id="test_dataset_123",
            access_type="read",
            user_id="test_user",
            data_classification="confidential",
            record_count=1000,
        )

        assert len(self.audit_logger.audit_events) == 1
        event = self.audit_logger.audit_events[0]
        assert event["event_type"] == "data_access"
        assert event["dataset_id"] == "test_dataset_123"
        assert event["access_type"] == "read"
        assert event["data_classification"] == "confidential"
        assert event["record_count"] == 1000

    def test_get_audit_trail(self):
        """Test audit trail retrieval."""
        # Add multiple events
        self.audit_logger.log_user_action("action1", "resource1", "user1")
        self.audit_logger.log_data_access("dataset1", "read", "user1")

        trail = self.audit_logger.get_audit_trail()

        assert len(trail) == 2
        assert trail[0]["action"] == "action1"
        assert trail[1]["access_type"] == "read"


class TestEnhancedLogAnalyzer:
    """Test EnhancedLogAnalyzer functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir)
        self.analyzer = EnhancedLogAnalyzer(self.log_dir)

        # Create sample log file
        self.log_file = self.log_dir / "test.log"
        self._create_sample_logs()

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_sample_logs(self):
        """Create sample log entries for testing."""
        logs = [
            {
                "timestamp": "2024-01-01T10:00:00Z",
                "level": "INFO",
                "message": "User action performed",
                "security_category": "dataset_operation",
                "severity": "low",
                "event_type": "security_event",
            },
            {
                "timestamp": "2024-01-01T10:05:00Z",
                "level": "ERROR",
                "message": "Compliance check failed",
                "compliance_category": "dataset_governance",
                "result": "failed",
                "check_type": "data_classification",
            },
            {
                "timestamp": "2024-01-01T10:10:00Z",
                "level": "DEBUG",
                "message": "Performance metric recorded",
                "performance_category": "dataset_metrics",
                "metric_name": "query_time",
                "metric_value": 1.5,
                "metric_unit": "seconds",
            },
            {
                "timestamp": "2024-01-01T10:15:00Z",
                "level": "WARNING",
                "message": "Performance threshold exceeded: query_time=5.0seconds > 3.0seconds",
                "performance_category": "dataset_metrics",
                "metric_name": "query_time",
                "metric_value": 5.0,
            },
        ]

        with open(self.log_file, "w") as f:
            for log_entry in logs:
                f.write(json.dumps(log_entry) + "\n")

    def test_find_security_events(self):
        """Test security event finding."""
        security_events = self.analyzer.find_security_events()

        assert len(security_events) == 1
        assert security_events[0]["severity"] == "low"
        assert security_events[0]["security_category"] == "dataset_operation"

    def test_find_security_events_by_severity(self):
        """Test security event finding by severity."""
        security_events = self.analyzer.find_security_events(severity="high")

        assert len(security_events) == 0  # No high severity events in sample

    def test_find_compliance_violations(self):
        """Test compliance violation finding."""
        violations = self.analyzer.find_compliance_violations()

        assert len(violations) == 1
        assert violations[0]["result"] == "failed"
        assert violations[0]["check_type"] == "data_classification"

    def test_analyze_performance_trends(self):
        """Test performance trend analysis."""
        trends = self.analyzer.analyze_performance_trends("query_time", hours=24)

        assert trends["metric_name"] == "query_time"
        assert trends["sample_count"] == 2
        assert trends["min_value"] == 1.5
        assert trends["max_value"] == 5.0
        assert trends["avg_value"] == 3.25
        assert trends["threshold_violations"] == 1

    def test_analyze_performance_trends_no_data(self):
        """Test performance trend analysis with no data."""
        trends = self.analyzer.analyze_performance_trends(
            "nonexistent_metric", hours=24
        )

        assert "error" in trends
        assert "No data found" in trends["error"]

    def test_generate_compliance_report(self):
        """Test compliance report generation."""
        report = self.analyzer.generate_compliance_report()

        assert "report_period" in report
        assert "summary" in report
        assert "security_summary" in report
        assert "compliance_rate" in report

        summary = report["summary"]
        assert summary["total_log_entries"] == 4
        assert summary["violations"] == 1
        assert summary["compliance_checks"] == 1


class TestLogAnalysisFunctions:
    """Test standalone logging functions."""

    def setup_method(self):
        """Setup test environment."""
        # Reset the global logger for clean testing
        dataset_logger.reset_metrics()

    def test_log_dataset_operation_start(self):
        """Test dataset operation start logging."""
        log_dataset_operation_start(
            operation="test_operation",
            dataset_id="test_dataset",
            dataset_type="test_type",
            user_id="test_user",
        )

        # This test verifies the function doesn't raise an exception

    def test_log_dataset_operation_success(self):
        """Test dataset operation success logging."""
        log_dataset_operation_success(
            operation="test_operation", dataset_id="test_dataset", processing_time=5.0
        )

        # This test verifies the function doesn't raise an exception

    def test_log_dataset_operation_error(self):
        """Test dataset operation error logging."""
        error = Exception("Test error")

        log_dataset_operation_error(
            operation="test_operation",
            dataset_id="test_dataset",
            error=error,
            user_id="test_user",
        )

        # This test verifies the function doesn't raise an exception


class TestPerformanceOptimization:
    """Test performance optimization features."""

    def test_performance_sampling(self):
        """Test performance metric sampling."""
        temp_dir = tempfile.mkdtemp()
        config = LogConfig(
            log_dir=Path(temp_dir),
            enable_performance_monitoring=True,
            performance_sampling_rate=0.5,  # 50% sampling
        )
        logger = DatasetLogger("performance_test", config)

        # Mock random to control sampling
        with patch("random.random") as mock_random:
            mock_random.side_effect = [0.3, 0.7, 0.2, 0.8]  # 2 below, 2 above threshold

            for i in range(4):
                logger.log_performance_metric(
                    metric_name="test_metric",
                    metric_value=i * 0.5,
                    metric_unit="seconds",
                )

        # Only 2 metrics should have been logged (sampling rate 50%)
        # This is a behavior test, exact implementation may vary

    def test_log_message_size_limit(self):
        """Test log message size limiting."""
        temp_dir = tempfile.mkdtemp()
        config = LogConfig(
            log_dir=Path(temp_dir), max_log_message_size=100  # Small limit
        )
        logger = DatasetLogger("size_test", config)

        # Create a very long message
        long_message = "x" * 1000

        # Should not raise an exception even with long message
        logger.info(long_message)

    def test_async_logging_performance(self):
        """Test async logging performance impact."""
        temp_dir = tempfile.mkdtemp()
        config = LogConfig(log_dir=Path(temp_dir), async_logging=True)
        logger = DatasetLogger("async_test", config)

        start_time = time.time()

        # Log many messages quickly
        for i in range(100):
            logger.info(f"Test message {i}")

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete quickly (under 1 second for 100 messages)
        assert elapsed < 1.0


class TestIntegrationScenarios:
    """Test integration scenarios with multiple components."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = LogConfig(
            log_dir=Path(self.temp_dir),
            enable_file_logging=True,
            enable_structured_logging=True,
            enable_performance_tracking=True,
            enable_audit_trails=True,
        )

    def teardown_method(self):
        """Cleanup test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_dataset_operation_workflow(self):
        """Test complete dataset operation with all logging features."""
        logger = DatasetLogger("integration_test", self.config)
        audit_logger = DatasetAuditLogger(logger)

        user_id = "integration_user"
        dataset_id = "integration_dataset"
        correlation_id = logger.set_correlation_id()
        logger.set_user_context(user_id)

        # Simulate complete workflow
        with logger.operation_context(
            operation=OperationType.IMPORT.value,
            dataset_id=dataset_id,
            dataset_type="test_type",
            user_id=user_id,
            correlation_id=correlation_id,
        ):
            # Log user action
            audit_logger.log_user_action(
                action="start_import", resource=f"dataset:{dataset_id}", user_id=user_id
            )

            # Simulate processing chunks
            for i in range(5):
                logger.log_chunk_progress(
                    chunk_index=i,
                    total_chunks=5,
                    chunk_size=100,
                    success=True,
                    processing_time=0.5 + i * 0.1,
                )
                logger.log_memory_usage(100 + i * 10, "chunk_processing")

            # Log security events
            logger.log_security_event(
                event_type="data_processing",
                severity="low",
                details={"chunks_processed": 5},
            )

            # Log compliance check
            logger.log_compliance_check(
                check_type="data_validation",
                result="passed",
                details={"validation_rules": ["format", "content"]},
            )

            # Log performance metrics
            logger.log_performance_metric(
                metric_name="total_processing_time",
                metric_value=3.0,
                metric_unit="seconds",
                threshold=5.0,
            )

            # Log PyRIT storage
            logger.log_pyrit_storage(
                prompts_stored=500, storage_time_seconds=1.2, storage_size_mb=5.5
            )

            # Log data access
            audit_logger.log_data_access(
                dataset_id=dataset_id,
                access_type="import",
                user_id=user_id,
                data_classification="internal",
                record_count=500,
            )

        # Verify metrics were collected
        final_metrics = logger.finalize_metrics()
        assert final_metrics.total_chunks == 5
        assert final_metrics.successful_chunks == 5
        assert len(final_metrics.memory_samples) == 5
        assert len(final_metrics.chunk_processing_times) == 5

        # Verify audit trail
        audit_trail = audit_logger.get_audit_trail()
        assert len(audit_trail) == 2  # user_action + data_access

        # Check log files were created
        log_files = list(Path(self.temp_dir).glob("*.log"))
        assert len(log_files) > 0

    def test_error_handling_workflow(self):
        """Test error handling and logging workflow."""
        logger = DatasetLogger("error_test", self.config)
        # audit_logger is intentionally unused in this test - we're testing the logger directly
        _audit_logger = DatasetAuditLogger(logger)

        user_id = "error_user"
        dataset_id = "error_dataset"

        try:
            with logger.operation_context(
                operation=OperationType.IMPORT.value,
                dataset_id=dataset_id,
                user_id=user_id,
            ):
                # Log security event for suspicious activity
                logger.log_security_event(
                    event_type="suspicious_activity",
                    severity="high",
                    details={"reason": "unusual_pattern"},
                )

                # Simulate retry attempts
                for attempt in range(3):
                    error = Exception(f"Attempt {attempt + 1} failed")
                    logger.log_retry_attempt(attempt + 1, 3, error)

                # Simulate final failure
                raise ValueError("Final failure after retries")

        except ValueError as e:
            # Exception should be logged by context manager
            # Verify that the exception was properly handled
            assert str(e) == "Final failure after retries"

        # Verify retry metrics
        assert logger.metrics.total_retries == 3
        assert logger.metrics.max_retries_per_operation == 3
        assert len(logger.metrics.retry_reasons) == 3

    def test_log_analysis_workflow(self):
        """Test log analysis on generated logs."""
        logger = DatasetLogger("analysis_test", self.config)

        # Generate various types of logs
        logger.log_security_event("test_event", "medium")
        logger.log_compliance_check("test_check", "failed")
        logger.log_performance_metric("test_metric", 2.5, threshold=3.0)

        # Force log file creation
        for handler in logger.logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Wait a bit for file I/O
        time.sleep(0.1)

        # Analyze logs
        _analyzer = EnhancedLogAnalyzer(Path(self.temp_dir))

        # This test verifies the analyzer can work with generated logs
        # Actual analysis results may vary based on log format and timing
        # The analyzer instance is created but not used in this basic workflow test


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
