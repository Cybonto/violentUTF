# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Continuous Monitoring Service for Issue #270

Background service for automated database performance metrics collection.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ContinuousMonitoringService:
    """
    Continuous monitoring service for automated database metrics collection.

    This service runs in the background and periodically collects metrics
    from configured database sources.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize continuous monitoring service.

        Args:
            config: Configuration dictionary with settings:
                - collection_interval_seconds: Interval between collections
                - enabled_collectors: List of collector types to enable
                - storage_enabled: Whether to store collected metrics
        """
        self.collection_interval = config.get("collection_interval_seconds", 10)
        self.enabled_collectors = config.get("enabled_collectors", [])
        self.storage_enabled = config.get("storage_enabled", True)
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the continuous monitoring service."""
        self.is_running = True

        while self.is_running:
            try:
                await self._collect_metrics()
            except Exception as e:
                logger.error("Error in metric collection cycle: %s", e)

            # Wait for next collection interval
            await asyncio.sleep(self.collection_interval)

    def stop(self) -> None:
        """Stop the continuous monitoring service."""
        self.is_running = False

    async def _collect_metrics(self) -> None:
        """Collect metrics from all enabled collectors."""
        for collector_type in self.enabled_collectors:
            try:
                if collector_type == "postgresql":
                    await self._collect_postgresql_metrics()
                elif collector_type == "sqlite":
                    await self._collect_sqlite_metrics()
            except Exception as e:
                logger.error("Error collecting %s metrics: %s", collector_type, e)

    async def _collect_postgresql_metrics(self) -> None:
        """Collect PostgreSQL metrics."""
        from violentutf_api.fastapi_app.app.monitoring.database import PostgresMetricsCollector

        # Default PostgreSQL connection for Keycloak
        connection_string = "postgresql://keycloak:password@localhost:5432/keycloak"
        collector = PostgresMetricsCollector(connection_string)
        metrics = await collector.collect_all_metrics()

        if self.storage_enabled and metrics:
            await self._store_metrics("postgresql", "postgres-keycloak", metrics)

    async def _collect_sqlite_metrics(self) -> None:
        """Collect SQLite metrics."""
        import os

        from violentutf_api.fastapi_app.app.monitoring.database import SQLiteMetricsCollector

        # Get SQLite database path from environment or use a secure default
        database_path = os.getenv("SQLITE_DB_PATH", "/app/app_data/violentutf_api.db")
        collector = SQLiteMetricsCollector(database_path)
        metrics = await collector.collect_all_metrics()

        if self.storage_enabled and metrics:
            await self._store_metrics("sqlite", "sqlite-fastapi", metrics)

    async def _store_metrics(self, db_type: str, db_id: str, metrics: Any) -> None:  # noqa: ANN401
        """Store collected metrics to database.

        Args:
            db_type: Database type
            db_id: Database identifier
            metrics: Collected metrics object
        """
        # Import here to avoid circular dependencies
        # MonitoringService import removed as it was unused

        # In a real implementation, this would get a proper DB session
        # For now, this is a placeholder that tests can mock
        logger.info("Storing metrics for %s/%s", db_type, db_id)

    async def get_health_status(self) -> Dict[str, Any]:
        """Get service health status.

        Returns:
            Health status dictionary
        """
        return {
            "status": "running" if self.is_running else "stopped",
            "last_collection": datetime.now(timezone.utc),
            "enabled_collectors": self.enabled_collectors,
        }

    def reconfigure(self, config: Dict[str, Any]) -> None:
        """Reconfigure the service without restart.

        Args:
            config: New configuration dictionary
        """
        self.collection_interval = config.get("collection_interval_seconds", self.collection_interval)
        self.enabled_collectors = config.get("enabled_collectors", self.enabled_collectors)
        self.storage_enabled = config.get("storage_enabled", self.storage_enabled)

        logger.info("Monitoring service reconfigured")
