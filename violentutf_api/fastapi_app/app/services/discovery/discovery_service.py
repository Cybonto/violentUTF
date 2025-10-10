# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Main discovery service for FastAPI integration."""

import asyncio
import logging

# Import discovery modules from scripts
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.discovery import CodeReference as DBCodeReference
from ...models.discovery import ContainerInfo as DBContainerInfo
from ...models.discovery import DatabaseFile as DBDatabaseFile
from ...models.discovery import DiscoveredDatabase as DBDiscoveredDatabase
from ...models.discovery import DiscoveryExecution as DBDiscoveryExecution
from ...models.discovery import DiscoveryReport as DBDiscoveryReport
from ...models.discovery import NetworkService as DBNetworkService
from ...models.discovery import SecurityFinding as DBSecurityFinding
from ...schemas.discovery import (
    BulkValidationRequest,
    BulkValidationResponse,
    DiscoveredDatabase,
    DiscoveredDatabaseUpdate,
    DiscoveryConfig,
    DiscoveryExecution,
    DiscoveryExecutionCreate,
    DiscoveryFilter,
    DiscoveryReportCreate,
    DiscoveryStats,
)

sys.path.append("/Users/tamnguyen/Documents/GitHub/violentUTF/scripts/database-automation")

from discovery.exceptions import DiscoveryError  # noqa: E402
from discovery.models import DiscoveryConfig as ScriptDiscoveryConfig  # noqa: E402
from discovery.models import DiscoveryReport  # noqa: E402
from discovery.orchestrator import DiscoveryOrchestrator  # noqa: E402


class DiscoveryService:
    """Service for managing database discovery operations."""

    def __init__(self) -> None:
        """Initialize the discovery service."""
        self.logger = logging.getLogger(__name__)

    async def execute_discovery(self, db: AsyncSession, config: Optional[DiscoveryConfig] = None) -> DiscoveryExecution:
        """
        Execute database discovery process asynchronously.

        Args:
            db: Database session
            config: Discovery configuration

        Returns:
            Discovery execution record
        """
        # Create execution record
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        execution_data = DiscoveryExecutionCreate(
            execution_id=execution_id, status="running", config_snapshot=config.model_dump() if config else {}
        )

        db_execution = DBDiscoveryExecution(**execution_data.model_dump())
        db.add(db_execution)
        await db.commit()
        await db.refresh(db_execution)

        try:
            # Convert Pydantic config to script config
            script_config = self._convert_config(config)

            # Run discovery in background
            discovery_result = await self._run_discovery_async(script_config)

            # Store discoveries in database
            stored_discoveries = await self._store_discoveries(db, discovery_result.databases)

            # Create and store report
            report = await self._create_report(db, discovery_result, stored_discoveries)

            # Update execution record
            db_execution.status = "completed"
            db_execution.discoveries_found = len(stored_discoveries)
            db_execution.execution_time_seconds = discovery_result.execution_time_seconds
            db_execution.completed_at = datetime.utcnow()
            db_execution.report_id = report.report_id

            await db.commit()
            await db.refresh(db_execution)

            self.logger.info("Discovery execution %s completed successfully", execution_id)

            return DiscoveryExecution.model_validate(db_execution)

        except Exception as e:
            self.logger.error("Discovery execution %s failed: %s", execution_id, e)

            # Update execution with error
            db_execution.status = "failed"
            db_execution.errors_encountered = [str(e)]
            db_execution.completed_at = datetime.utcnow()

            await db.commit()

            raise DiscoveryError(f"Discovery execution failed: {e}") from e

    def _convert_config(self, config: Optional[DiscoveryConfig]) -> ScriptDiscoveryConfig:
        """Convert Pydantic config to script config."""
        if not config:
            return ScriptDiscoveryConfig()

        return ScriptDiscoveryConfig(
            enable_container_discovery=config.enable_container_discovery,
            enable_network_discovery=config.enable_network_discovery,
            enable_filesystem_discovery=config.enable_filesystem_discovery,
            enable_code_discovery=config.enable_code_discovery,
            enable_security_scanning=config.enable_security_scanning,
            scan_compose_files=config.scan_compose_files,
            compose_file_patterns=config.compose_file_patterns,
            network_ranges=config.network_ranges,
            database_ports=config.database_ports,
            network_timeout_seconds=config.network_timeout_seconds,
            max_concurrent_scans=config.max_concurrent_scans,
            scan_paths=config.scan_paths,
            file_extensions=config.file_extensions,
            max_file_size_mb=config.max_file_size_mb,
            code_extensions=config.code_extensions,
            exclude_patterns=config.exclude_patterns,
            secrets_baseline_file=config.secrets_baseline_file,
            bandit_config_file=config.bandit_config_file,
            exclude_security_paths=config.exclude_security_paths,
            max_execution_time_seconds=config.max_execution_time_seconds,
            max_memory_usage_mb=config.max_memory_usage_mb,
            enable_parallel_processing=config.enable_parallel_processing,
            max_workers=config.max_workers,
            output_format=config.output_format,
            include_raw_data=config.include_raw_data,
            include_security_details=config.include_security_details,
            validation_enabled=config.validation_enabled,
        )

    async def _run_discovery_async(self, config: ScriptDiscoveryConfig) -> DiscoveryReport:
        """Run discovery process asynchronously."""
        loop = asyncio.get_event_loop()

        def run_discovery() -> DiscoveryReport:
            orchestrator = DiscoveryOrchestrator(config)
            return orchestrator.execute_full_discovery()

        # Run in thread pool to avoid blocking the event loop
        return await loop.run_in_executor(None, run_discovery)

    async def _store_discoveries(self, db: AsyncSession, discoveries: List) -> List[DBDiscoveredDatabase]:
        """Store discovery results in database."""
        stored_discoveries = []

        for discovery in discoveries:
            try:
                # Convert script model to database model
                db_discovery = DBDiscoveredDatabase(
                    database_id=discovery.database_id,
                    name=discovery.name,
                    description=discovery.description,
                    database_type=discovery.database_type.value,
                    host=discovery.host,
                    port=discovery.port,
                    file_path=discovery.file_path,
                    connection_string=discovery.connection_string,
                    discovery_method=discovery.discovery_method.value,
                    confidence_level=discovery.confidence_level.value,
                    confidence_score=discovery.confidence_score,
                    discovered_at=discovery.discovered_at,
                    version=discovery.version,
                    size_mb=discovery.size_mb,
                    is_active=discovery.is_active,
                    is_accessible=discovery.is_accessible,
                    is_validated=discovery.is_validated,
                    validation_errors=discovery.validation_errors,
                    tags=discovery.tags,
                    custom_properties=discovery.custom_properties,
                )

                db.add(db_discovery)
                await db.flush()  # Get ID without committing

                # Store related data
                if discovery.container_info:
                    container_info = DBContainerInfo(
                        database_id=discovery.database_id,
                        container_id=discovery.container_info.container_id,
                        name=discovery.container_info.name,
                        image=discovery.container_info.image,
                        status=discovery.container_info.status,
                        ports=discovery.container_info.ports,
                        environment=discovery.container_info.environment,
                        volumes=discovery.container_info.volumes,
                        networks=discovery.container_info.networks,
                        is_database=discovery.container_info.is_database,
                        database_type=(
                            discovery.container_info.database_type.value
                            if discovery.container_info.database_type
                            else None
                        ),
                    )
                    db.add(container_info)

                if discovery.network_service:
                    network_service = DBNetworkService(
                        database_id=discovery.database_id,
                        host=discovery.network_service.host,
                        port=discovery.network_service.port,
                        protocol=discovery.network_service.protocol,
                        service_name=discovery.network_service.service_name,
                        banner=discovery.network_service.banner,
                        response_time_ms=discovery.network_service.response_time_ms,
                        is_database=discovery.network_service.is_database,
                        database_type=(
                            discovery.network_service.database_type.value
                            if discovery.network_service.database_type
                            else None
                        ),
                    )
                    db.add(network_service)

                # Store database files
                for db_file in discovery.database_files:
                    database_file = DBDatabaseFile(
                        database_id=discovery.database_id,
                        file_path=db_file.file_path,
                        file_size=db_file.file_size,
                        last_modified=db_file.last_modified,
                        file_type=db_file.file_type,
                        database_type=db_file.database_type.value,
                        is_accessible=db_file.is_accessible,
                        schema_info=db_file.schema_info,
                        connection_string=db_file.connection_string,
                    )
                    db.add(database_file)

                # Store code references
                for code_ref in discovery.code_references:
                    code_reference = DBCodeReference(
                        database_id=discovery.database_id,
                        file_path=code_ref.file_path,
                        line_number=code_ref.line_number,
                        code_snippet=code_ref.code_snippet,
                        reference_type=code_ref.reference_type,
                        database_type=code_ref.database_type.value if code_ref.database_type else None,
                        connection_string=code_ref.connection_string,
                        is_credential=code_ref.is_credential,
                    )
                    db.add(code_reference)

                # Store security findings
                for security_finding in discovery.security_findings:
                    finding = DBSecurityFinding(
                        database_id=discovery.database_id,
                        file_path=security_finding.file_path,
                        line_number=security_finding.line_number,
                        finding_type=security_finding.finding_type,
                        severity=security_finding.severity,
                        description=security_finding.description,
                        recommendation=security_finding.recommendation,
                        is_false_positive=security_finding.is_false_positive,
                    )
                    db.add(finding)

                stored_discoveries.append(db_discovery)

            except Exception as e:
                self.logger.error("Error storing discovery %s: %s", discovery.database_id, e)
                continue

        await db.commit()

        # Refresh all stored discoveries
        for discovery in stored_discoveries:
            await db.refresh(discovery)

        return stored_discoveries

    async def _create_report(
        self, db: AsyncSession, discovery_result: DiscoveryReport, stored_discoveries: List[DBDiscoveredDatabase]
    ) -> DBDiscoveryReport:
        """Create and store discovery report."""
        report_data = DiscoveryReportCreate(
            report_id=discovery_result.report_id,
            execution_time_seconds=discovery_result.execution_time_seconds,
            total_discoveries=discovery_result.total_discoveries,
            type_counts={k.value: v for k, v in discovery_result.type_counts.items()},
            method_counts={k.value: v for k, v in discovery_result.method_counts.items()},
            confidence_distribution={k.value: v for k, v in discovery_result.confidence_distribution.items()},
            scan_targets=discovery_result.scan_targets,
            processing_stats=discovery_result.processing_stats,
            security_findings_count=discovery_result.security_findings_count,
            credential_exposures=discovery_result.credential_exposures,
            high_severity_findings=discovery_result.high_severity_findings,
            validated_discoveries=discovery_result.validated_discoveries,
            validation_errors=discovery_result.validation_errors,
            discovery_scope=discovery_result.discovery_scope,
            excluded_paths=discovery_result.excluded_paths,
            configuration=discovery_result.configuration,
            report_data=discovery_result.to_dict(),
        )

        db_report = DBDiscoveryReport(**report_data.model_dump())
        db.add(db_report)
        await db.commit()
        await db.refresh(db_report)

        return db_report

    async def get_discoveries(
        self, db: AsyncSession, filters: Optional[DiscoveryFilter] = None, limit: int = 50, offset: int = 0
    ) -> List[DiscoveredDatabase]:
        """Get discovered databases with optional filtering."""
        query = select(DBDiscoveredDatabase)

        if filters:
            conditions = []

            if filters.database_type:
                conditions.append(DBDiscoveredDatabase.database_type == filters.database_type.value)

            if filters.discovery_method:
                conditions.append(DBDiscoveredDatabase.discovery_method == filters.discovery_method.value)

            if filters.confidence_level:
                conditions.append(DBDiscoveredDatabase.confidence_level == filters.confidence_level.value)

            if filters.is_active is not None:
                conditions.append(DBDiscoveredDatabase.is_active == filters.is_active)

            if filters.is_validated is not None:
                conditions.append(DBDiscoveredDatabase.is_validated == filters.is_validated)

            if filters.host:
                conditions.append(DBDiscoveredDatabase.host == filters.host)

            if filters.min_confidence_score:
                conditions.append(DBDiscoveredDatabase.confidence_score >= filters.min_confidence_score)

            if filters.discovered_after:
                conditions.append(DBDiscoveredDatabase.discovered_at >= filters.discovered_after)

            if filters.discovered_before:
                conditions.append(DBDiscoveredDatabase.discovered_at <= filters.discovered_before)

            if filters.tags:
                # Check if any of the specified tags are present
                tag_conditions = []
                for tag in filters.tags:
                    tag_conditions.append(func.json_contains(DBDiscoveredDatabase.tags, f'"{tag}"'))
                conditions.append(or_(*tag_conditions))

            if conditions:
                query = query.where(and_(*conditions))

        query = query.offset(offset).limit(limit).order_by(DBDiscoveredDatabase.discovered_at.desc())

        result = await db.execute(query)
        db_discoveries = result.scalars().all()

        return [DiscoveredDatabase.model_validate(discovery) for discovery in db_discoveries]

    async def get_discovery_by_id(self, db: AsyncSession, database_id: str) -> Optional[DiscoveredDatabase]:
        """Get a specific discovered database by ID."""
        query = select(DBDiscoveredDatabase).where(DBDiscoveredDatabase.database_id == database_id)
        result = await db.execute(query)
        db_discovery = result.scalar_one_or_none()

        if db_discovery:
            return DiscoveredDatabase.model_validate(db_discovery)
        return None

    async def update_discovery(
        self, db: AsyncSession, database_id: str, update_data: DiscoveredDatabaseUpdate
    ) -> Optional[DiscoveredDatabase]:
        """Update a discovered database."""
        query = select(DBDiscoveredDatabase).where(DBDiscoveredDatabase.database_id == database_id)
        result = await db.execute(query)
        db_discovery = result.scalar_one_or_none()

        if not db_discovery:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(db_discovery, field, value)

        await db.commit()
        await db.refresh(db_discovery)

        return DiscoveredDatabase.model_validate(db_discovery)

    async def delete_discovery(self, db: AsyncSession, database_id: str) -> bool:
        """Delete a discovered database."""
        query = select(DBDiscoveredDatabase).where(DBDiscoveredDatabase.database_id == database_id)
        result = await db.execute(query)
        db_discovery = result.scalar_one_or_none()

        if not db_discovery:
            return False

        await db.delete(db_discovery)
        await db.commit()

        return True

    async def get_discovery_stats(self, db: AsyncSession) -> DiscoveryStats:
        """Get discovery statistics."""
        # Get total counts
        total_query = select(func.count(DBDiscoveredDatabase.id))
        total_result = await db.execute(total_query)
        total_databases = total_result.scalar()

        # Get active count
        active_query = select(func.count(DBDiscoveredDatabase.id)).where(DBDiscoveredDatabase.is_active.is_(True))
        active_result = await db.execute(active_query)
        active_databases = active_result.scalar()

        # Get type distribution
        type_query = select(DBDiscoveredDatabase.database_type, func.count(DBDiscoveredDatabase.id)).group_by(
            DBDiscoveredDatabase.database_type
        )
        type_result = await db.execute(type_query)
        database_types = {row[0]: row[1] for row in type_result}

        # Get method distribution
        method_query = select(DBDiscoveredDatabase.discovery_method, func.count(DBDiscoveredDatabase.id)).group_by(
            DBDiscoveredDatabase.discovery_method
        )
        method_result = await db.execute(method_query)
        discovery_methods = {row[0]: row[1] for row in method_result}

        # Get confidence distribution
        confidence_query = select(DBDiscoveredDatabase.confidence_level, func.count(DBDiscoveredDatabase.id)).group_by(
            DBDiscoveredDatabase.confidence_level
        )
        confidence_result = await db.execute(confidence_query)
        confidence_levels = {row[0]: row[1] for row in confidence_result}

        # Get security findings count
        security_query = select(func.count(DBSecurityFinding.id))
        security_result = await db.execute(security_query)
        security_findings = security_result.scalar()

        # Get last discovery time
        last_discovery_query = select(func.max(DBDiscoveredDatabase.discovered_at))
        last_discovery_result = await db.execute(last_discovery_query)
        last_discovery_at = last_discovery_result.scalar()

        return DiscoveryStats(
            total_databases=total_databases,
            active_databases=active_databases,
            database_types=database_types,
            discovery_methods=discovery_methods,
            confidence_levels=confidence_levels,
            security_findings=security_findings,
            last_discovery_at=last_discovery_at,
        )

    async def validate_discoveries(self, db: AsyncSession, request: BulkValidationRequest) -> BulkValidationResponse:
        """Validate multiple discoveries."""
        validation_results = {}
        errors = {}
        processed_count = 0
        success_count = 0
        error_count = 0

        for database_id in request.database_ids:
            try:
                # Get discovery
                discovery = await self.get_discovery_by_id(db, database_id)
                if not discovery:
                    errors[database_id] = "Discovery not found"
                    error_count += 1
                    continue

                # Skip if already validated and not forcing revalidation
                if discovery.is_validated and not request.force_revalidation:
                    validation_results[database_id] = True
                    success_count += 1
                    processed_count += 1
                    continue

                # Perform validation
                is_valid = await self._validate_single_discovery(discovery)

                # Update discovery with validation result
                update_data = DiscoveredDatabaseUpdate(
                    is_validated=is_valid, validation_errors=[] if is_valid else ["Validation failed"]
                )

                await self.update_discovery(db, database_id, update_data)

                validation_results[database_id] = is_valid
                if is_valid:
                    success_count += 1
                else:
                    error_count += 1

                processed_count += 1

            except Exception as e:
                errors[database_id] = str(e)
                error_count += 1

        return BulkValidationResponse(
            validation_results=validation_results,
            errors=errors,
            processed_count=processed_count,
            success_count=success_count,
            error_count=error_count,
        )

    async def _validate_single_discovery(self, discovery: DiscoveredDatabase) -> bool:
        """Validate a single discovery."""
        try:
            # Basic validation checks
            if not discovery.database_type or discovery.database_type == "unknown":
                return False

            # File-based validation
            if discovery.file_path:
                file_path = Path(discovery.file_path)
                if not file_path.exists():
                    return False

            # Network-based validation
            if discovery.host and discovery.port:
                # Could implement actual connectivity test here
                pass

            return True

        except Exception as e:
            self.logger.error("Validation error for %s: %s", discovery.database_id, e)
            return False
