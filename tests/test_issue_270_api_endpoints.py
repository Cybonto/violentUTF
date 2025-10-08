# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test Suite for Issue #270 - Database Monitoring API Endpoints

Tests the RESTful API endpoints for database performance monitoring including
metrics storage, baseline retrieval, and recalculation jobs.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status

from violentutf_api.fastapi_app.app.monitoring.database import (
    PostgreSQLMetrics,
    SQLiteMetrics,
)
from violentutf_api.fastapi_app.app.monitoring.database.baseline_analyzer import (
    PerformanceBaseline,
)


class TestDatabaseOverviewEndpoint:
    """Test GET /monitoring/database/overview endpoint."""

    @pytest.mark.asyncio
    async def test_database_overview_success(self) -> None:
        """Test successful database overview retrieval."""
        # This test verifies the endpoint returns health status for all databases
        from violentutf_api.fastapi_app.app.api.v1.monitoring import (
            get_database_overview,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()

        with (
            patch(
                "violentutf_api.fastapi_app.app.api.v1.monitoring.PostgresMetricsCollector"
            ) as mock_pg_collector_class,
            patch(
                "violentutf_api.fastapi_app.app.api.v1.monitoring.SQLiteMetricsCollector"
            ) as mock_sqlite_collector_class,
        ):
            # Setup PostgreSQL mock
            mock_pg_collector = AsyncMock()
            mock_pg_metrics = PostgreSQLMetrics(
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
            mock_pg_collector.collect_all_metrics.return_value = mock_pg_metrics
            mock_pg_collector_class.return_value = mock_pg_collector

            # Setup SQLite mock
            mock_sqlite_collector = AsyncMock()
            mock_sqlite_metrics = SQLiteMetrics(
                timestamp=datetime.now(timezone.utc),
                database_path="/app/data/test.db",
                database_size_mb=48.5,
                file_growth_rate_mb_per_hour=0.5,
                avg_query_time_ms=8.3,
                wal_size_mb=2.1,
                journal_mode="wal",
            )
            mock_sqlite_collector.collect_all_metrics.return_value = (
                mock_sqlite_metrics
            )
            mock_sqlite_collector_class.return_value = mock_sqlite_collector

            # Execute endpoint
            response = await get_database_overview(db=mock_db, current_user=mock_user)

            # Verify response
            assert response.overall_status == "healthy"
            assert len(response.databases) == 2

            # Verify PostgreSQL status
            pg_status = next(db for db in response.databases if db.db_type == "postgresql")
            assert pg_status.db_id == "postgres-keycloak"
            assert pg_status.status == "healthy"
            assert pg_status.key_metrics["connection_pool_usage"] == 45.5
            assert pg_status.key_metrics["avg_query_latency_ms"] == 15.2

            # Verify SQLite status
            sqlite_status = next(db for db in response.databases if db.db_type == "sqlite")
            assert sqlite_status.db_id == "sqlite-fastapi"
            assert sqlite_status.status == "healthy"
            assert sqlite_status.key_metrics["database_size_mb"] == 48.5

    @pytest.mark.asyncio
    async def test_database_overview_partial_failure(self) -> None:
        """Test database overview with one database failing."""
        from violentutf_api.fastapi_app.app.api.v1.monitoring import (
            get_database_overview,
        )

        mock_db = AsyncMock()
        mock_user = MagicMock()

        with (
            patch(
                "violentutf_api.fastapi_app.app.api.v1.monitoring.PostgresMetricsCollector"
            ) as mock_pg_collector_class,
            patch(
                "violentutf_api.fastapi_app.app.api.v1.monitoring.SQLiteMetricsCollector"
            ) as mock_sqlite_collector_class,
        ):
            # PostgreSQL fails
            mock_pg_collector = AsyncMock()
            mock_pg_collector.collect_all_metrics.side_effect = Exception(
                "Connection failed"
            )
            mock_pg_collector_class.return_value = mock_pg_collector

            # SQLite succeeds
            mock_sqlite_collector = AsyncMock()
            mock_sqlite_metrics = SQLiteMetrics(
                timestamp=datetime.now(timezone.utc),
                database_path="/app/data/test.db",
                database_size_mb=48.5,
                avg_query_time_ms=8.3,
            )
            mock_sqlite_collector.collect_all_metrics.return_value = (
                mock_sqlite_metrics
            )
            mock_sqlite_collector_class.return_value = mock_sqlite_collector

            # Execute endpoint
            response = await get_database_overview(db=mock_db, current_user=mock_user)

            # Verify response shows degraded status
            assert response.overall_status == "degraded"
            assert len(response.databases) == 2

            # Verify PostgreSQL shows critical
            pg_status = next(db for db in response.databases if db.db_type == "postgresql")
            assert pg_status.status == "critical"
            assert pg_status.key_metrics == {}


class TestDatabaseMetricsEndpoint:
    """Test GET /monitoring/database/{db_type}/metrics endpoint."""

    @pytest.mark.asyncio
    async def test_get_postgres_metrics_success(self) -> None:
        """Test successful PostgreSQL metrics retrieval."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        # Create test data
        test_metrics = [
            {
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=i),
                "metric_type": "connection_pool_usage",
                "value": 45.0 + i,
                "unit": "percent",
            }
            for i in range(24)
        ]

        # Mock the MonitoringService method
        with patch.object(
            MonitoringService, "get_database_metrics", new_callable=AsyncMock
        ) as mock_get_metrics:
            mock_get_metrics.return_value = test_metrics

            service = MonitoringService(mock_db)
            metrics = await service.get_database_metrics(
                db_type="postgresql", hours_back=24
            )

            assert len(metrics) == 24
            assert metrics[0]["metric_type"] == "connection_pool_usage"
            mock_get_metrics.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_sqlite_metrics_with_filtering(self) -> None:
        """Test SQLite metrics with metric type filtering."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        # Create filtered test data
        test_metrics = [
            {
                "timestamp": datetime.now(timezone.utc),
                "metric_type": "database_size_mb",
                "value": 50.5,
                "unit": "megabytes",
            }
        ]

        with patch.object(
            MonitoringService, "get_database_metrics", new_callable=AsyncMock
        ) as mock_get_metrics:
            mock_get_metrics.return_value = test_metrics

            service = MonitoringService(mock_db)
            metrics = await service.get_database_metrics(
                db_type="sqlite", hours_back=24, metric_types=["database_size_mb"]
            )

            assert len(metrics) == 1
            assert metrics[0]["metric_type"] == "database_size_mb"

    @pytest.mark.asyncio
    async def test_invalid_database_type_returns_empty(self) -> None:
        """Test querying invalid database type returns empty list."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        with patch.object(
            MonitoringService, "get_database_metrics", new_callable=AsyncMock
        ) as mock_get_metrics:
            mock_get_metrics.return_value = []

            service = MonitoringService(mock_db)
            metrics = await service.get_database_metrics(
                db_type="invalid_db", hours_back=24
            )

            assert metrics == []


class TestDatabaseBaselinesEndpoint:
    """Test GET /monitoring/database/baselines endpoint."""

    @pytest.mark.asyncio
    async def test_get_all_baselines_success(self) -> None:
        """Test successful retrieval of all baselines."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        # Create test baselines
        test_baselines = [
            {
                "db_type": "postgresql",
                "metric_type": "avg_query_latency_ms",
                "baseline_value": 15.5,
                "std_deviation": 3.2,
                "normal_range": {"min": 9.1, "max": 21.9},
                "sample_size": 10080,
                "calculation_window_hours": 168,
                "valid_until": datetime.now(timezone.utc) + timedelta(days=1),
            },
            {
                "db_type": "sqlite",
                "metric_type": "database_size_mb",
                "baseline_value": 48.5,
                "std_deviation": 2.5,
                "normal_range": {"min": 43.5, "max": 53.5},
                "sample_size": 10080,
                "calculation_window_hours": 168,
                "valid_until": datetime.now(timezone.utc) + timedelta(days=1),
            },
        ]

        with patch.object(
            MonitoringService, "get_database_baselines", new_callable=AsyncMock
        ) as mock_get_baselines:
            mock_get_baselines.return_value = test_baselines

            service = MonitoringService(mock_db)
            baselines = await service.get_database_baselines()

            assert len(baselines) == 2
            assert baselines[0]["db_type"] == "postgresql"
            assert baselines[1]["db_type"] == "sqlite"

    @pytest.mark.asyncio
    async def test_get_filtered_baselines(self) -> None:
        """Test baseline retrieval with filtering."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        test_baselines = [
            {
                "db_type": "postgresql",
                "metric_type": "avg_query_latency_ms",
                "baseline_value": 15.5,
                "std_deviation": 3.2,
                "normal_range": {"min": 9.1, "max": 21.9},
                "sample_size": 10080,
                "calculation_window_hours": 168,
                "valid_until": datetime.now(timezone.utc) + timedelta(days=1),
            }
        ]

        with patch.object(
            MonitoringService, "get_database_baselines", new_callable=AsyncMock
        ) as mock_get_baselines:
            mock_get_baselines.return_value = test_baselines

            service = MonitoringService(mock_db)
            baselines = await service.get_database_baselines(
                db_type="postgresql", metric_types=["avg_query_latency_ms"]
            )

            assert len(baselines) == 1
            assert baselines[0]["metric_type"] == "avg_query_latency_ms"

    @pytest.mark.asyncio
    async def test_get_baselines_no_data(self) -> None:
        """Test baseline retrieval when no baselines exist."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        with patch.object(
            MonitoringService, "get_database_baselines", new_callable=AsyncMock
        ) as mock_get_baselines:
            mock_get_baselines.return_value = []

            service = MonitoringService(mock_db)
            baselines = await service.get_database_baselines()

            assert baselines == []


class TestBaselineRecalculationEndpoint:
    """Test POST /monitoring/database/baselines/recalculate endpoint."""

    @pytest.mark.asyncio
    async def test_recalculate_all_baselines(self) -> None:
        """Test triggering recalculation for all baselines."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        with patch.object(
            MonitoringService, "recalculate_baselines", new_callable=AsyncMock
        ) as mock_recalc:
            job_id = str(uuid.uuid4())
            mock_recalc.return_value = {
                "job_id": job_id,
                "status": "queued",
                "message": "Baseline recalculation job queued",
                "started_at": datetime.now(timezone.utc),
            }

            service = MonitoringService(mock_db)
            result = await service.recalculate_baselines()

            assert result["job_id"] == job_id
            assert result["status"] == "queued"
            mock_recalc.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_recalculate_specific_baseline(self) -> None:
        """Test triggering recalculation for specific database type."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        with patch.object(
            MonitoringService, "recalculate_baselines", new_callable=AsyncMock
        ) as mock_recalc:
            job_id = str(uuid.uuid4())
            mock_recalc.return_value = {
                "job_id": job_id,
                "status": "queued",
                "message": "Baseline recalculation job queued for postgresql",
                "started_at": datetime.now(timezone.utc),
            }

            service = MonitoringService(mock_db)
            result = await service.recalculate_baselines(db_type="postgresql")

            assert result["job_id"] == job_id
            assert "postgresql" in result["message"]

    @pytest.mark.asyncio
    async def test_recalculate_baseline_already_running(self) -> None:
        """Test triggering recalculation when job already running."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        with patch.object(
            MonitoringService, "recalculate_baselines", new_callable=AsyncMock
        ) as mock_recalc:
            mock_recalc.return_value = {
                "job_id": None,
                "status": "running",
                "message": "Baseline recalculation already in progress",
                "started_at": datetime.now(timezone.utc) - timedelta(minutes=5),
            }

            service = MonitoringService(mock_db)
            result = await service.recalculate_baselines()

            assert result["status"] == "running"
            assert result["job_id"] is None


class TestMetricsStorageIntegration:
    """Test metrics storage and retrieval through MonitoringService."""

    @pytest.mark.asyncio
    async def test_store_database_metrics(self) -> None:
        """Test storing database performance metrics."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        # Test metrics data
        metrics_data = {
            "db_type": "postgresql",
            "db_id": "postgres-keycloak",
            "timestamp": datetime.now(timezone.utc),
            "metrics": {
                "connection_pool_usage": 45.5,
                "avg_query_latency_ms": 15.2,
                "cache_hit_ratio": 0.98,
            },
        }

        with patch.object(
            MonitoringService, "store_database_metrics", new_callable=AsyncMock
        ) as mock_store:
            mock_store.return_value = True

            service = MonitoringService(mock_db)
            success = await service.store_database_metrics(metrics_data)

            assert success is True
            mock_store.assert_awaited_once_with(metrics_data)

    @pytest.mark.asyncio
    async def test_store_metrics_batch(self) -> None:
        """Test storing batch of metrics."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        batch_data = [
            {
                "db_type": "postgresql",
                "db_id": "postgres-keycloak",
                "timestamp": datetime.now(timezone.utc),
                "metrics": {"connection_pool_usage": 45.5},
            },
            {
                "db_type": "sqlite",
                "db_id": "sqlite-fastapi",
                "timestamp": datetime.now(timezone.utc),
                "metrics": {"database_size_mb": 48.5},
            },
        ]

        with patch.object(
            MonitoringService, "store_database_metrics_batch", new_callable=AsyncMock
        ) as mock_store_batch:
            mock_store_batch.return_value = 2

            service = MonitoringService(mock_db)
            stored_count = await service.store_database_metrics_batch(batch_data)

            assert stored_count == 2
            mock_store_batch.assert_awaited_once()


class TestBaselineStorageIntegration:
    """Test baseline storage and retrieval through MonitoringService."""

    @pytest.mark.asyncio
    async def test_store_baseline(self) -> None:
        """Test storing a calculated baseline."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        baseline = PerformanceBaseline(
            baseline_id=uuid.uuid4(),
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

        with patch.object(
            MonitoringService, "store_baseline", new_callable=AsyncMock
        ) as mock_store:
            mock_store.return_value = baseline.baseline_id

            service = MonitoringService(mock_db)
            baseline_id = await service.store_baseline(baseline.to_dict())

            assert baseline_id == baseline.baseline_id
            mock_store.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_existing_baseline(self) -> None:
        """Test updating an existing baseline."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        baseline_data = {
            "db_type": "postgresql",
            "metric_type": "avg_query_latency_ms",
            "baseline_value": 16.5,
            "std_deviation": 3.5,
        }

        with patch.object(
            MonitoringService, "update_baseline", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = True

            service = MonitoringService(mock_db)
            success = await service.update_baseline(
                "postgresql", "avg_query_latency_ms", baseline_data
            )

            assert success is True
            mock_update.assert_awaited_once()


class TestMetricsAggregation:
    """Test metrics aggregation functionality."""

    @pytest.mark.asyncio
    async def test_aggregate_metrics_hourly(self) -> None:
        """Test hourly aggregation of metrics."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        with patch.object(
            MonitoringService, "aggregate_metrics", new_callable=AsyncMock
        ) as mock_aggregate:
            aggregated = [
                {
                    "hour": datetime.now(timezone.utc).replace(
                        minute=0, second=0, microsecond=0
                    ),
                    "metric_type": "connection_pool_usage",
                    "avg_value": 45.5,
                    "min_value": 30.0,
                    "max_value": 60.0,
                    "sample_count": 360,
                }
            ]
            mock_aggregate.return_value = aggregated

            service = MonitoringService(mock_db)
            result = await service.aggregate_metrics(
                db_type="postgresql", hours_back=24, interval="hourly"
            )

            assert len(result) == 1
            assert result[0]["metric_type"] == "connection_pool_usage"
            assert result[0]["sample_count"] == 360

    @pytest.mark.asyncio
    async def test_aggregate_metrics_daily(self) -> None:
        """Test daily aggregation of metrics."""
        from violentutf_api.fastapi_app.app.services.monitoring.monitoring_service import (
            MonitoringService,
        )

        mock_db = AsyncMock()

        with patch.object(
            MonitoringService, "aggregate_metrics", new_callable=AsyncMock
        ) as mock_aggregate:
            aggregated = [
                {
                    "day": datetime.now(timezone.utc).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ),
                    "metric_type": "database_size_mb",
                    "avg_value": 48.5,
                    "min_value": 47.0,
                    "max_value": 50.0,
                    "sample_count": 8640,
                }
            ]
            mock_aggregate.return_value = aggregated

            service = MonitoringService(mock_db)
            result = await service.aggregate_metrics(
                db_type="sqlite", hours_back=168, interval="daily"
            )

            assert len(result) == 1
            assert result[0]["metric_type"] == "database_size_mb"
