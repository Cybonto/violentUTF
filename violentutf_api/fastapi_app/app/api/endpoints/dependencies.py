# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Dependency mapping and impact analysis API endpoints."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.dependency import (
    ChangeRequest,
    DependencyDiscoveryConfig,
    DependencyGraph,
    DependencyMatrix,
    DiscoveryResult,
    ImpactAnalysisResult,
    SystemHealthStatus,
)
from app.services.dependency_mapping import DependencyMappingService
from app.services.impact_analysis import ImpactAnalysisService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/matrix", response_model=DependencyMatrix)
async def get_dependency_matrix(session: AsyncSession = Depends(get_session)) -> DependencyMatrix:
    """Get complete dependency matrix for the system."""
    try:
        # This would implement actual matrix retrieval from database
        # For now, return a sample matrix
        return DependencyMatrix(
            matrix_version="v1.0.0",
            services=["streamlit-app", "violentutf-api", "keycloak", "apisix"],
            databases=["violentutf_api.db", "keycloak.db", "pyrit_memory.db"],
            dependencies=[],
            service_health=[],
            matrix_metadata={
                "generated_method": "automated_discovery",
                "total_dependencies": 0,
                "critical_dependencies": 0,
            },
        )
    except Exception as e:
        logger.error("Failed to get dependency matrix: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve dependency matrix"
        ) from e


@router.get("/graph", response_model=DependencyGraph)
async def get_dependency_graph(session: AsyncSession = Depends(get_session)) -> DependencyGraph:
    """Get dependency graph for visualization."""
    try:
        # Sample dependency graph
        nodes = [
            {"id": "streamlit-app", "type": "service", "criticality": "high"},
            {"id": "violentutf-api", "type": "service", "criticality": "critical"},
            {"id": "keycloak", "type": "service", "criticality": "critical"},
            {"id": "apisix", "type": "service", "criticality": "high"},
            {"id": "violentutf_api.db", "type": "database", "criticality": "critical"},
            {"id": "keycloak.db", "type": "database", "criticality": "critical"},
        ]

        edges = [
            {"source": "streamlit-app", "target": "violentutf-api", "type": "api"},
            {"source": "streamlit-app", "target": "keycloak", "type": "authentication"},
            {"source": "violentutf-api", "target": "violentutf_api.db", "type": "database"},
            {"source": "keycloak", "target": "keycloak.db", "type": "database"},
            {"source": "apisix", "target": "violentutf-api", "type": "proxy"},
            {"source": "apisix", "target": "keycloak", "type": "proxy"},
        ]

        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            metadata={"total_nodes": len(nodes), "total_edges": len(edges), "graph_type": "directed"},
        )
    except Exception as e:
        logger.error("Failed to get dependency graph: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve dependency graph"
        ) from e


@router.post("/discover", response_model=DiscoveryResult)
async def trigger_dependency_discovery(
    config: DependencyDiscoveryConfig = None, session: AsyncSession = Depends(get_session)
) -> DiscoveryResult:
    """Trigger dependency discovery process."""
    try:
        mapping_service = DependencyMappingService()

        if config is None:
            config = DependencyDiscoveryConfig()

        result = await mapping_service.discover_all_dependencies(config)

        logger.info("Discovery %s completed with status: %s", result.discovery_id, result.status)

        return result
    except Exception as e:
        logger.error("Dependency discovery failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Dependency discovery failed: " + str(e)
        ) from e


@router.post("/analyze-change", response_model=ImpactAnalysisResult)
async def analyze_change_impact(
    change_request: ChangeRequest, session: AsyncSession = Depends(get_session)
) -> ImpactAnalysisResult:
    """Analyze impact of proposed changes."""
    try:
        analysis_service = ImpactAnalysisService()

        result = await analysis_service.analyze_change_impact(change_request)

        logger.info("Impact analysis %s completed with risk score: %d", result.analysis_id, result.risk_score)

        return result
    except Exception as e:
        logger.error("Impact analysis failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Impact analysis failed: " + str(e)
        ) from e


@router.get("/health", response_model=SystemHealthStatus)
async def get_system_health(session: AsyncSession = Depends(get_session)) -> SystemHealthStatus:
    """Get overall system dependency health status."""
    try:
        # This would implement actual health status retrieval
        # For now, return a sample health status
        from violentutf_api.fastapi_app.app.models.dependency import HealthStatus

        return SystemHealthStatus(
            overall_health=HealthStatus.HEALTHY,
            total_services=4,
            healthy_services=4,
            degraded_services=0,
            down_services=0,
            critical_dependencies_healthy=6,
            total_critical_dependencies=6,
            services_status=[],
            issues=[],
        )
    except Exception as e:
        logger.error("Failed to get system health: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve system health status"
        ) from e


@router.get("/dependencies", response_model=List[dict])
async def list_dependencies(
    service_name: str = None, dependency_type: str = None, session: AsyncSession = Depends(get_session)
) -> List[dict]:
    """List dependencies with optional filtering."""
    try:
        # This would implement actual dependency listing from database
        # For now, return sample dependencies
        sample_dependencies = [
            {
                "id": "dep-001",
                "source_service": "streamlit-app",
                "target_service": "violentutf-api",
                "dependency_type": "api",
                "criticality": "critical",
            },
            {
                "id": "dep-002",
                "source_service": "violentutf-api",
                "target_database": "violentutf_api.db",
                "dependency_type": "database",
                "criticality": "critical",
            },
        ]

        # Apply filters if provided
        if service_name:
            sample_dependencies = [
                dep
                for dep in sample_dependencies
                if dep.get("source_service") == service_name or dep.get("target_service") == service_name
            ]

        if dependency_type:
            sample_dependencies = [dep for dep in sample_dependencies if dep.get("dependency_type") == dependency_type]

        return sample_dependencies
    except Exception as e:
        logger.error("Failed to list dependencies: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list dependencies"
        ) from e
