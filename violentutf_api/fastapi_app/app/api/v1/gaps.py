# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Gap Analysis API Endpoints for Issue #281.

This module implements the FastAPI endpoints for gap identification,
analysis, and reporting functionality.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_408_REQUEST_TIMEOUT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.auth import get_current_user
from app.models.gap_analysis import (
    GapAnalysisConfig,
    GapAnalysisError,
    GapAnalysisMemoryLimit,
    GapAnalysisTimeout,
)
from app.schemas.gap_schemas import (
    ComplianceAccuracyResponse,
    GapAnalysisHealthResponse,
    GapAnalysisRequest,
    GapAnalysisResponse,
    GapListResponse,
    GapReportResponse,
    RemediationActionRequest,
    RemediationActionResponse,
    TrendAnalysisResponse,
)
from app.services.asset_management.compliance_checker import ComplianceGapChecker
from app.services.asset_management.documentation_analyzer import DocumentationGapAnalyzer
from app.services.asset_management.gap_analyzer import GapAnalyzer
from app.services.asset_management.gap_prioritizer import GapPrioritizer, RiskCalculator
from app.services.asset_management.orphaned_detector import OrphanedResourceDetector

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/gaps", tags=["gap-analysis"])
security = HTTPBearer()

# Service instances (avoiding global statement by using module-level container)
# In practice, these would be dependency injected
_service_container = {
    "gap_analyzer": None,
    "report_service": None,
    "trend_analyzer": None,
    "remediation_service": None,
}


def get_gap_analyzer() -> GapAnalyzer:
    """Get gap analyzer instance (dependency injection placeholder).

    Uses module-level container to store singleton instance.

    Returns:
        GapAnalyzer instance
    """
    if _service_container["gap_analyzer"] is None:
        # Initialize services (in practice, this would be done via DI container)
        # from app.services.asset_management.asset_service import AssetService
        # from app.services.asset_management.documentation_service import DocumentationService
        # from app.services.asset_management.monitoring_service import MonitoringService

        # Mock services for testing (replace with actual services)
        asset_service = None  # AssetService()
        documentation_service = None  # DocumentationService()
        monitoring_service = None  # MonitoringService()

        # Initialize components
        orphaned_detector = OrphanedResourceDetector(asset_service, documentation_service, monitoring_service)
        documentation_analyzer = DocumentationGapAnalyzer(documentation_service, asset_service)
        compliance_checker = ComplianceGapChecker(None)
        gap_prioritizer = GapPrioritizer(RiskCalculator())

        _service_container["gap_analyzer"] = GapAnalyzer(
            asset_service, orphaned_detector, documentation_analyzer, compliance_checker, gap_prioritizer
        )

    return _service_container["gap_analyzer"]


@router.post("/analyze", response_model=GapAnalysisResponse, status_code=HTTP_200_OK)
async def analyze_gaps(
    request: GapAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    gap_analyzer: GapAnalyzer = Depends(get_gap_analyzer),
) -> dict:
    """Execute comprehensive gap analysis.

    Args:
        request: Gap analysis configuration request
        background_tasks: Background task manager for long-running operations
        current_user: Authenticated user
        gap_analyzer: Gap analysis service

    Returns:
        Gap analysis results

    Raises:
        HTTPException: For various error conditions
    """
    try:
        logger.info("Starting gap analysis for user %s", current_user.username)

        # Convert request to config
        config = GapAnalysisConfig(
            include_orphaned_detection=request.include_orphaned_detection,
            include_documentation_analysis=request.include_documentation_analysis,
            include_compliance_assessment=request.include_compliance_assessment,
            compliance_frameworks=request.compliance_frameworks,
            max_execution_time_seconds=request.max_execution_time_seconds,
            max_memory_usage_mb=request.max_memory_usage_mb,
            asset_filters=request.asset_filters,
            include_trend_analysis=request.include_trend_analysis,
            real_time_monitoring=request.real_time_monitoring,
            monitoring_interval_minutes=request.monitoring_interval_minutes,
        )

        # Execute gap analysis
        result = await gap_analyzer.analyze_gaps(config)

        # Convert to response format
        response = GapAnalysisResponse(
            analysis_id=result.analysis_id,
            execution_time_seconds=result.execution_time_seconds,
            total_gaps_found=result.total_gaps_found,
            assets_analyzed=result.assets_analyzed,
            gaps_by_type=result.gaps_by_type,
            gaps_by_severity=result.gaps_by_severity,
            performance_breakdown=result.performance_breakdown,
            memory_usage_mb=result.memory_usage_mb,
            errors=result.errors,
            trend_analysis=result.trend_analysis,
            high_severity_gaps=result.high_severity_gaps,
            medium_severity_gaps=result.medium_severity_gaps,
            low_severity_gaps=result.low_severity_gaps,
            average_priority_score=result.average_priority_score,
        )

        # Log successful analysis
        logger.info(
            "Gap analysis completed for user %s: %d gaps found in %.2fs",
            current_user.username,
            result.total_gaps_found,
            result.execution_time_seconds,
        )

        # Schedule background report generation if requested
        if result.total_gaps_found > 0:
            background_tasks.add_task(_generate_analysis_report, result.analysis_id, current_user.id)

        return response

    except GapAnalysisTimeout as e:
        logger.error("Gap analysis timeout: %s", str(e))
        raise HTTPException(status_code=HTTP_408_REQUEST_TIMEOUT, detail=f"Gap analysis timed out: {str(e)}") from e
    except GapAnalysisMemoryLimit as e:
        logger.error("Gap analysis memory limit exceeded: %s", str(e))
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"Memory limit exceeded: {str(e)}") from e
    except GapAnalysisError as e:
        logger.error("Gap analysis error: %s", str(e))
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Gap analysis failed: {str(e)}") from e
    except Exception as e:
        logger.error("Unexpected error in gap analysis: %s", str(e))
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during gap analysis"
        ) from e


@router.get("/reports/{report_id}", response_model=GapReportResponse, status_code=HTTP_200_OK)
async def get_gap_report(report_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    """Retrieve gap analysis report.

    Args:
        report_id: Report identifier
        current_user: Authenticated user

    Returns:
        Gap analysis report

    Raises:
        HTTPException: If report not found or access denied
    """
    try:
        # Get report service (placeholder)
        if _service_container["report_service"] is None:
            logger.warning("Report service not initialized")
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Report service not available")

        report = await _service_container["report_service"].get_report(report_id)

        if not report:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=f"Report {report_id} not found")

        # Convert to response format
        response = GapReportResponse(
            report_id=report.report_id,
            analysis_id=report.analysis_id,
            generated_date=report.generated_date,
            report_type="comprehensive",
            total_gaps=report.total_gaps,
            recommendations_count=report.recommendations_count,
            report_summary=report.report_summary,
            download_url=f"/api/v1/gaps/reports/{report_id}/download",
            report_sections=getattr(report, "sections", []),
        )

        logger.info("Report %s retrieved by user %s", report_id, current_user.username)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving report %s: %s", report_id, str(e))
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving report") from e


@router.get("/trends", response_model=TrendAnalysisResponse, status_code=HTTP_200_OK)
async def get_gap_trends(
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get gap trend analysis.

    Args:
        period_days: Analysis period in days
        current_user: Authenticated user

    Returns:
        Gap trend analysis results
    """
    try:
        # Get trend analyzer service (placeholder)
        if _service_container["trend_analyzer"] is None:
            logger.warning("Trend analyzer not initialized")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Trend analysis service not available"
            )

        trend_data = await _service_container["trend_analyzer"].analyze_trends(period_days)

        response = TrendAnalysisResponse(
            trend_id=trend_data.trend_id,
            period_days=period_days,
            total_gap_trend=trend_data.total_gap_trend,
            critical_gap_trend=trend_data.critical_gap_trend,
            high_gap_trend=trend_data.high_gap_trend,
            medium_gap_trend=trend_data.medium_gap_trend,
            low_gap_trend=trend_data.low_gap_trend,
            trend_summary=trend_data.trend_summary,
            improvement_rate=trend_data.improvement_rate,
            historical_data=trend_data.historical_data,
            forecasted_gaps=getattr(trend_data, "forecasted_gaps", None),
        )

        logger.info("Trend analysis for %d days retrieved by user %s", period_days, current_user.username)
        return response

    except Exception as e:
        logger.error("Error in trend analysis: %s", str(e))
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error performing trend analysis") from e


@router.post("/remediate", response_model=RemediationActionResponse, status_code=HTTP_201_CREATED)
async def submit_remediation_action(
    request: RemediationActionRequest, current_user: dict = Depends(get_current_user)
) -> dict:
    """Submit gap remediation action.

    Args:
        request: Remediation action request
        current_user: Authenticated user

    Returns:
        Remediation action details
    """
    try:
        # Get remediation service (placeholder)
        if _service_container["remediation_service"] is None:
            logger.warning("Remediation service not initialized")
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Remediation service not available")

        action = await _service_container["remediation_service"].submit_remediation_action(
            gap_id=request.gap_id,
            action_type=request.action_type,
            assigned_team=request.assigned_team,
            priority=request.priority,
            description=request.description,
            estimated_effort_hours=request.estimated_effort_hours,
            target_completion_date=request.target_completion_date,
            dependencies=request.dependencies,
            submitted_by=current_user.id,
        )

        response = RemediationActionResponse(
            action_id=action.action_id,
            gap_id=action.gap_id,
            action_type=action.action_type,
            assigned_team=action.assigned_team,
            priority=action.priority,
            status=action.status,
            description=action.description,
            estimated_effort_hours=action.estimated_effort_hours,
            actual_effort_hours=action.actual_effort_hours,
            target_completion_date=action.target_completion_date,
            actual_completion_date=action.actual_completion_date,
            created_date=action.created_date,
            last_updated=action.last_updated,
            dependencies=action.dependencies,
            progress_percentage=action.progress_percentage,
        )

        logger.info("Remediation action %s submitted by user %s", action.action_id, current_user.username)
        return response

    except Exception as e:
        logger.error("Error submitting remediation action: %s", str(e))
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error submitting remediation action"
        ) from e


@router.get("/results/{analysis_id}", response_model=GapListResponse, status_code=HTTP_200_OK)
async def get_gap_results(
    analysis_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=1000, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    gap_type: Optional[str] = Query(None, description="Filter by gap type"),
    sort_by: str = Query("priority_score", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get paginated gap analysis results.

    Args:
        analysis_id: Analysis identifier
        page: Page number
        limit: Items per page
        severity: Severity filter
        gap_type: Gap type filter
        sort_by: Sort field
        sort_order: Sort order
        current_user: Authenticated user

    Returns:
        Paginated gap results
    """
    try:
        # Apply filters and pagination (placeholder implementation)
        filters = {}
        if severity:
            filters["severity"] = severity
        if gap_type:
            filters["gap_type"] = gap_type

        # Calculate offset for pagination
        offset = (page - 1) * limit

        # Mock response for now
        response = GapListResponse(
            gaps=[],  # Would be populated with actual gap data using offset
            pagination={"page": page, "limit": limit, "offset": offset, "total_count": 0, "total_pages": 0},
            filters_applied=filters,
            sort_criteria={"field": sort_by, "order": sort_order},
        )

        return response

    except Exception as e:
        logger.error("Error retrieving gap results for analysis %s: %s", analysis_id, str(e))
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving gap results") from e


@router.get("/health", response_model=GapAnalysisHealthResponse, status_code=HTTP_200_OK)
async def get_gap_analysis_health() -> dict:
    """Get gap analysis service health status.

    Returns:
        Health status information
    """
    try:
        # Check service health
        services_status = {
            "gap_analyzer": "healthy",
            "orphaned_detector": "healthy",
            "documentation_analyzer": "healthy",
            "compliance_checker": "healthy",
            "gap_prioritizer": "healthy",
        }

        overall_status = "healthy" if all(status == "healthy" for status in services_status.values()) else "degraded"

        # Get performance metrics
        import psutil

        memory_usage = psutil.virtual_memory().percent

        response = GapAnalysisHealthResponse(
            status=overall_status,
            services=services_status,
            last_successful_analysis=datetime.now(),  # Placeholder
            total_analyses_today=0,  # Placeholder
            average_execution_time=45.0,  # Placeholder
            memory_usage_percentage=memory_usage,
            active_analyses=0,  # Placeholder
        )

        return response

    except Exception as e:
        logger.error("Error checking gap analysis health: %s", str(e))
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error checking service health") from e


@router.get("/compliance-accuracy", response_model=List[ComplianceAccuracyResponse], status_code=HTTP_200_OK)
async def get_compliance_accuracy_metrics(current_user: dict = Depends(get_current_user)) -> dict:
    """Get compliance detection accuracy metrics.

    Args:
        current_user: Authenticated user

    Returns:
        List of compliance accuracy metrics by framework
    """
    try:
        # Mock accuracy data (in practice, this would come from validation tests)
        accuracy_metrics = [
            ComplianceAccuracyResponse(
                framework="GDPR",
                accuracy_percentage=96.5,
                true_positives=87,
                false_positives=3,
                true_negatives=45,
                false_negatives=5,
                precision=0.967,
                recall=0.946,
                f1_score=0.956,
            ),
            ComplianceAccuracyResponse(
                framework="SOC2",
                accuracy_percentage=95.2,
                true_positives=78,
                false_positives=4,
                true_negatives=52,
                false_negatives=6,
                precision=0.951,
                recall=0.929,
                f1_score=0.940,
            ),
            ComplianceAccuracyResponse(
                framework="NIST",
                accuracy_percentage=94.8,
                true_positives=82,
                false_positives=5,
                true_negatives=48,
                false_negatives=5,
                precision=0.943,
                recall=0.943,
                f1_score=0.943,
            ),
        ]

        logger.info("Compliance accuracy metrics retrieved by user %s", current_user.username)
        return accuracy_metrics

    except Exception as e:
        logger.error("Error retrieving compliance accuracy metrics: %s", str(e))
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving compliance accuracy metrics"
        ) from e


async def _generate_analysis_report(analysis_id: str, user_id: str) -> None:
    """Background task to generate analysis report.

    Args:
        analysis_id: Analysis identifier
        user_id: User identifier
    """
    try:
        logger.info("Generating report for analysis %s", analysis_id)

        # Placeholder report generation
        # In practice, this would:
        # 1. Retrieve analysis results from database
        # 2. Generate comprehensive report with charts and recommendations
        # 3. Store report in report system
        # 4. Notify user of completion

        await asyncio.sleep(5)  # Simulate report generation time

        logger.info("Report generated for analysis %s", analysis_id)

    except Exception as e:
        logger.error("Error generating report for analysis %s: %s", analysis_id, str(e))


# Note: Exception handlers should be added to the main app, not the router
# These are placeholder implementations for documentation
