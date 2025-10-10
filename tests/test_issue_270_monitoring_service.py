# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test Suite for Issue #270 - Continuous Monitoring Service

Tests the continuous monitoring service that performs automated data collection
and background processing for database performance monitoring.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestContinuousMonitoringService:
    """Test the continuous monitoring service."""

    @pytest.mark.asyncio
    async def test_service_initialization(self) -> None:
        """Test service initializes with correct configuration."""
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        config = {
            "collection_interval_seconds": 10,
            "enabled_collectors": ["postgresql", "sqlite"],
            "storage_enabled": True,
        }

        service = ContinuousMonitoringService(config)

        assert service.collection_interval == 10
        assert "postgresql" in service.enabled_collectors
        assert service.storage_enabled is True

    @pytest.mark.asyncio
    async def test_service_starts_collection(self) -> None:
        """Test service starts metric collection on startup."""
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        config = {"collection_interval_seconds": 1, "enabled_collectors": ["postgresql"]}

        with (
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.monitoring_service.PostgresMetricsCollector"
            ) as mock_collector,
        ):
            mock_instance = AsyncMock()
            mock_collector.return_value = mock_instance

            service = ContinuousMonitoringService(config)

            # Start service in background
            task = asyncio.create_task(service.start())

            # Let it run one cycle
            await asyncio.sleep(1.5)

            # Stop service
            service.stop()
            await task

            # Verify collector was used
            assert mock_collector.called

    @pytest.mark.asyncio
    async def test_service_collects_metrics_periodically(self) -> None:
        """Test service collects metrics at configured intervals."""
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        collection_count = 0

        async def mock_collect() -> None:
            nonlocal collection_count
            collection_count += 1

        config = {"collection_interval_seconds": 0.5, "enabled_collectors": ["sqlite"]}

        with patch(
            "violentutf_api.fastapi_app.app.monitoring.database.monitoring_service.ContinuousMonitoringService._collect_metrics",
            new=mock_collect,
        ):
            service = ContinuousMonitoringService(config)

            task = asyncio.create_task(service.start())
            await asyncio.sleep(1.6)
            service.stop()
            await task

            # Should have collected 3 times (at 0, 0.5, 1.0, 1.5)
            assert collection_count >= 3

    @pytest.mark.asyncio
    async def test_service_handles_collection_errors(self) -> None:
        """Test service continues after collection errors."""
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        config = {"collection_interval_seconds": 0.5, "enabled_collectors": ["postgresql"]}

        with (
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.monitoring_service.PostgresMetricsCollector"
            ) as mock_collector,
        ):
            mock_instance = AsyncMock()
            # First call fails, second succeeds
            mock_instance.collect_all_metrics.side_effect = [
                Exception("Connection error"),
                MagicMock(),
            ]
            mock_collector.return_value = mock_instance

            service = ContinuousMonitoringService(config)

            task = asyncio.create_task(service.start())
            await asyncio.sleep(1.2)
            service.stop()
            await task

            # Should have attempted collection twice
            assert mock_instance.collect_all_metrics.call_count >= 2

    @pytest.mark.asyncio
    async def test_service_stores_collected_metrics(self) -> None:
        """Test service stores metrics after collection."""
        from violentutf_api.fastapi_app.app.monitoring.database import (
            PostgreSQLMetrics,
        )
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        config = {
            "collection_interval_seconds": 0.5,
            "enabled_collectors": ["postgresql"],
            "storage_enabled": True,
        }

        mock_metrics = PostgreSQLMetrics(
            timestamp=datetime.now(timezone.utc),
            connection_pool_usage=45.5,
            active_connections=10,
            idle_connections=12,
            waiting_connections=0,
            avg_query_latency_ms=15.2,
            slow_query_count=0,
            database_size_mb=1024.5,
            cache_hit_ratio=0.98,
            transaction_rate=125.5,
            replication_lag_seconds=0.0,
        )

        with (
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.monitoring_service.PostgresMetricsCollector"
            ) as mock_collector,
            patch(
                "violentutf_api.fastapi_app.app.services.monitoring.monitoring_service.MonitoringService"
            ) as mock_service_class,
        ):
            mock_collector_instance = AsyncMock()
            mock_collector_instance.collect_all_metrics.return_value = mock_metrics
            mock_collector.return_value = mock_collector_instance

            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            service = ContinuousMonitoringService(config)

            task = asyncio.create_task(service.start())
            await asyncio.sleep(0.7)
            service.stop()
            await task

            # Verify storage was called
            assert mock_service.store_database_metrics.called

    @pytest.mark.asyncio
    async def test_service_graceful_shutdown(self) -> None:
        """Test service shuts down gracefully."""
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        config = {"collection_interval_seconds": 1, "enabled_collectors": ["sqlite"]}

        service = ContinuousMonitoringService(config)

        task = asyncio.create_task(service.start())
        await asyncio.sleep(0.5)

        # Stop service
        service.stop()
        await asyncio.wait_for(task, timeout=2.0)

        # Verify service stopped
        assert service.is_running is False

    @pytest.mark.asyncio
    async def test_service_multiple_collectors(self) -> None:
        """Test service manages multiple collectors."""
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        config = {
            "collection_interval_seconds": 0.5,
            "enabled_collectors": ["postgresql", "sqlite"],
        }

        with (
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.monitoring_service.PostgresMetricsCollector"
            ) as mock_pg,
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.monitoring_service.SQLiteMetricsCollector"
            ) as mock_sqlite,
        ):
            mock_pg_instance = AsyncMock()
            mock_sqlite_instance = AsyncMock()
            mock_pg.return_value = mock_pg_instance
            mock_sqlite.return_value = mock_sqlite_instance

            service = ContinuousMonitoringService(config)

            task = asyncio.create_task(service.start())
            await asyncio.sleep(0.7)
            service.stop()
            await task

            # Both collectors should be used
            assert mock_pg.called
            assert mock_sqlite.called

    @pytest.mark.asyncio
    async def test_service_health_check(self) -> None:
        """Test service health check reports status."""
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        config = {"collection_interval_seconds": 10, "enabled_collectors": ["postgresql"]}

        service = ContinuousMonitoringService(config)

        health = await service.get_health_status()

        assert "status" in health
        assert "last_collection" in health
        assert "enabled_collectors" in health

    @pytest.mark.asyncio
    async def test_service_reconfigure(self) -> None:
        """Test service can be reconfigured without restart."""
        from violentutf_api.fastapi_app.app.monitoring.database.monitoring_service import (
            ContinuousMonitoringService,
        )

        config = {"collection_interval_seconds": 10, "enabled_collectors": ["postgresql"]}

        service = ContinuousMonitoringService(config)
        assert service.collection_interval == 10

        # Reconfigure
        new_config = {"collection_interval_seconds": 5, "enabled_collectors": ["sqlite"]}
        service.reconfigure(new_config)

        assert service.collection_interval == 5
        assert "sqlite" in service.enabled_collectors


class TestBaselineCalculationJob:
    """Test baseline calculation job processor."""

    @pytest.mark.asyncio
    async def test_job_initialization(self) -> None:
        """Test baseline calculation job initializes correctly."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
        )

        job = BaselineCalculationJob(
            job_id="test-job-123", db_type="postgresql", metric_types=["avg_query_latency_ms"]
        )

        assert job.job_id == "test-job-123"
        assert job.db_type == "postgresql"
        assert job.status == "queued"

    @pytest.mark.asyncio
    async def test_job_execution(self) -> None:
        """Test baseline calculation job executes successfully."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
        )

        mock_db = AsyncMock()

        with (
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.baseline_job.BaselineAnalyzer"
            ) as mock_analyzer,
            patch("violentutf_api.fastapi_app.app.services.monitoring.monitoring_service.MonitoringService") as mock_service,
        ):
            mock_analyzer_instance = MagicMock()
            mock_analyzer.return_value = mock_analyzer_instance

            job = BaselineCalculationJob(
                job_id="test-job", db_type="postgresql", metric_types=None
            )

            result = await job.execute(mock_db)

            assert result["status"] == "completed"
            assert result["job_id"] == "test-job"
            assert mock_analyzer.called

    @pytest.mark.asyncio
    async def test_job_calculates_all_metrics(self) -> None:
        """Test job calculates baselines for all metric types."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_analyzer import (
            PerformanceBaseline,
        )
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
        )

        mock_db = AsyncMock()

        test_baseline = PerformanceBaseline(
            baseline_id="baseline-123",
            db_type="postgresql",
            metric_type="avg_query_latency_ms",
            baseline_value=15.5,
            std_deviation=3.2,
            min_value=9.1,
            max_value=21.9,
            sample_size=10080,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=1),
        )

        with (
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.baseline_job.BaselineAnalyzer"
            ) as mock_analyzer,
            patch("violentutf_api.fastapi_app.app.services.monitoring.monitoring_service.MonitoringService") as mock_service,
        ):
            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.calculate_baseline.return_value = test_baseline
            mock_analyzer.return_value = mock_analyzer_instance

            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance

            job = BaselineCalculationJob(job_id="test-job", db_type="postgresql")

            result = await job.execute(mock_db)

            assert result["status"] == "completed"
            assert result["baselines_calculated"] > 0

    @pytest.mark.asyncio
    async def test_job_handles_insufficient_data(self) -> None:
        """Test job handles case with insufficient data."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
        )

        mock_db = AsyncMock()

        with (
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.baseline_job.BaselineAnalyzer"
            ) as mock_analyzer,
        ):
            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.calculate_baseline.return_value = None
            mock_analyzer.return_value = mock_analyzer_instance

            job = BaselineCalculationJob(job_id="test-job", db_type="sqlite")

            result = await job.execute(mock_db)

            assert result["status"] == "completed"
            assert result["baselines_calculated"] == 0
            assert "insufficient data" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_job_error_handling(self) -> None:
        """Test job handles errors gracefully."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
        )

        mock_db = AsyncMock()

        with patch(
            "violentutf_api.fastapi_app.app.monitoring.database.baseline_job.BaselineAnalyzer"
        ) as mock_analyzer:
            mock_analyzer.side_effect = Exception("Database connection failed")

            job = BaselineCalculationJob(job_id="test-job", db_type="postgresql")

            result = await job.execute(mock_db)

            assert result["status"] == "failed"
            assert "error" in result

    @pytest.mark.asyncio
    async def test_job_status_updates(self) -> None:
        """Test job updates status during execution."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
        )

        mock_db = AsyncMock()

        job = BaselineCalculationJob(job_id="test-job", db_type="postgresql")

        assert job.status == "queued"

        with (
            patch("violentutf_api.fastapi_app.app.monitoring.database.baseline_job.BaselineAnalyzer"),
            patch("violentutf_api.fastapi_app.app.services.monitoring.monitoring_service.MonitoringService"),
        ):
            task = asyncio.create_task(job.execute(mock_db))

            # Check running status
            await asyncio.sleep(0.1)
            assert job.status == "running"

            # Wait for completion
            await task

            assert job.status in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_job_stores_results(self) -> None:
        """Test job stores calculated baselines."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_analyzer import (
            PerformanceBaseline,
        )
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
        )

        mock_db = AsyncMock()

        test_baseline = PerformanceBaseline(
            baseline_id="baseline-123",
            db_type="postgresql",
            metric_type="avg_query_latency_ms",
            baseline_value=15.5,
            std_deviation=3.2,
            min_value=9.1,
            max_value=21.9,
            sample_size=10080,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=1),
        )

        with (
            patch(
                "violentutf_api.fastapi_app.app.monitoring.database.baseline_job.BaselineAnalyzer"
            ) as mock_analyzer,
            patch("violentutf_api.fastapi_app.app.services.monitoring.monitoring_service.MonitoringService") as mock_service,
        ):
            mock_analyzer_instance = MagicMock()
            mock_analyzer_instance.calculate_baseline.return_value = test_baseline
            mock_analyzer.return_value = mock_analyzer_instance

            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance

            job = BaselineCalculationJob(job_id="test-job", db_type="postgresql")

            await job.execute(mock_db)

            # Verify baseline was stored
            assert mock_service_instance.store_baseline.called


class TestJobQueue:
    """Test baseline calculation job queue."""

    @pytest.mark.asyncio
    async def test_queue_initialization(self) -> None:
        """Test job queue initializes correctly."""
        from app.monitoring.database.baseline_job import BaselineJobQueue

        queue = BaselineJobQueue()

        assert queue.size() == 0
        assert queue.is_empty()

    @pytest.mark.asyncio
    async def test_enqueue_job(self) -> None:
        """Test enqueueing a job."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
            BaselineJobQueue,
        )

        queue = BaselineJobQueue()
        job = BaselineCalculationJob(job_id="test-job", db_type="postgresql")

        job_id = await queue.enqueue(job)

        assert job_id == "test-job"
        assert queue.size() == 1
        assert not queue.is_empty()

    @pytest.mark.asyncio
    async def test_prevent_duplicate_jobs(self) -> None:
        """Test queue prevents duplicate jobs."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
            BaselineJobQueue,
        )

        queue = BaselineJobQueue()

        job1 = BaselineCalculationJob(job_id="job-1", db_type="postgresql")
        job2 = BaselineCalculationJob(job_id="job-1", db_type="postgresql")

        await queue.enqueue(job1)

        # Second enqueue should fail or return existing
        result = await queue.enqueue(job2)

        assert queue.size() == 1

    @pytest.mark.asyncio
    async def test_process_queue(self) -> None:
        """Test queue processes jobs in order."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
            BaselineJobQueue,
        )

        queue = BaselineJobQueue()
        mock_db = AsyncMock()

        job1 = BaselineCalculationJob(job_id="job-1", db_type="postgresql")
        job2 = BaselineCalculationJob(job_id="job-2", db_type="sqlite")

        await queue.enqueue(job1)
        await queue.enqueue(job2)

        with (
            patch("violentutf_api.fastapi_app.app.monitoring.database.baseline_job.BaselineAnalyzer"),
            patch("violentutf_api.fastapi_app.app.services.monitoring.monitoring_service.MonitoringService"),
        ):
            await queue.process_next(mock_db)

            assert queue.size() == 1

            await queue.process_next(mock_db)

            assert queue.is_empty()

    @pytest.mark.asyncio
    async def test_get_job_status(self) -> None:
        """Test retrieving job status."""
        from violentutf_api.fastapi_app.app.monitoring.database.baseline_job import (
            BaselineCalculationJob,
            BaselineJobQueue,
        )

        queue = BaselineJobQueue()
        job = BaselineCalculationJob(job_id="test-job", db_type="postgresql")

        await queue.enqueue(job)

        status = await queue.get_job_status("test-job")

        assert status is not None
        assert status["job_id"] == "test-job"
        assert status["status"] == "queued"
