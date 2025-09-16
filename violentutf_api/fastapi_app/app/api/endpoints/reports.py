# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Enhanced API endpoints for Advanced Dashboard Report Setup"""

import logging
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.database import get_session
from app.models.auth import User
from app.models.cob_models import COBReport, COBSchedule, COBScheduleExecution, COBTemplate
from app.models.report_system.report_models import COBBlockDefinition, COBReportVariable, COBScanDataCache

# Import schedule and export related schemas from COB system
from app.schemas import (
    COBScheduleCreate,
    COBScheduleListResponse,
    COBScheduleResponse,
    COBSystemStatusResponse,
)

# Import extended schemas and services
from app.schemas.report_system.report_schemas import (
    AttackCategory,
    BatchReportRequest,
    BlockDefinitionResponse,
    COBTemplateCreate,
    COBTemplateResponse,
    COBTemplateUpdate,
    DataBrowseRequest,
    DataBrowseResponse,
    PreviewRequest,
    PreviewResponse,
    ReportGenerationRequest,
    ReportGenerationResponse,
    ReportStatus,
    ReportVariableResponse,
    ScannerType,
    ScanResultSummary,
    TemplateRecommendation,
    TemplateVersionCreate,
    TemplateVersionResponse,
    TestingCategory,
)
from app.services.report_system.block_base import block_registry
from app.services.report_system.report_engine import ReportGenerationEngine
from app.services.report_system.template_service import TemplateService, get_initial_templates
from app.services.storage_service import StorageService, get_storage_service

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["reports"])


# Template Management Endpoints


@router.post("/templates", response_model=COBTemplateResponse)
async def create_template(
    template: COBTemplateCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)
) -> COBTemplateResponse:
    """Create a new report template"""
    try:
        service = TemplateService(db)
        return await service.create_template(template, current_user.id)
    except Exception as e:
        logger.error("Error creating template: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/templates", response_model=Dict[str, Any])
async def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: Optional[bool] = Query(None),
    testing_category: Optional[TestingCategory] = Query(None),
    attack_category: Optional[AttackCategory] = Query(None),
    scanner_type: Optional[ScannerType] = Query(None),
    complexity_level: Optional[str] = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|updated_at|name|usage_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """List templates with filtering and pagination"""
    try:
        service = TemplateService(db)

        logger.info(
            "List templates called with params: skip=%s, limit=%s, is_active=%s, "
            "testing_category=%s, attack_category=%s, scanner_type=%s, complexity_level=%s",
            skip,
            limit,
            is_active,
            testing_category,
            attack_category,
            scanner_type,
            complexity_level,
        )

        # Build filters
        filters = {}
        if is_active is not None:
            filters["is_active"] = is_active
        if testing_category:
            filters["testing_categories"] = [testing_category.value]
        if attack_category:
            filters["attack_categories"] = [attack_category.value]
        if scanner_type:
            filters["scanner_type"] = scanner_type.value
        if complexity_level:
            filters["complexity_level"] = complexity_level

        templates, total = await service.list_templates(
            skip=skip, limit=limit, filters=filters, sort_by=sort_by, sort_order=sort_order
        )

        logger.info("Found %d templates, returning %d templates", total, len(templates))

        return {
            "templates": templates,
            "total": total,
            "page": skip // limit + 1,
            "pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        logger.error("Error listing templates: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/templates/search", response_model=List[COBTemplateResponse])
async def search_templates(
    q: str = Query(..., min_length=2),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> List[COBTemplateResponse]:
    """Search templates by name, description, or metadata"""
    try:
        service = TemplateService(db)
        return await service.search_templates(q)
    except Exception as e:
        logger.error("Error searching templates: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/templates/recommend", response_model=List[TemplateRecommendation])
async def recommend_templates(
    scan_data: Dict[str, Any] = Body(...),
    limit: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> List[TemplateRecommendation]:
    """Get template recommendations based on scan data"""
    try:
        service = TemplateService(db)
        return await service.recommend_templates(scan_data, limit)
    except Exception as e:
        logger.error("Error recommending templates: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/templates/{template_id}", response_model=COBTemplateResponse)
async def get_template(
    template_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> COBTemplateResponse:
    """Get a specific template"""
    try:
        service = TemplateService(db)
        return await service.get_template(template_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        logger.error("Error getting template: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.put("/templates/{template_id}", response_model=COBTemplateResponse)
async def update_template(
    template_id: str = Path(...),
    template_update: COBTemplateUpdate = Body(...),
    create_version: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> COBTemplateResponse:
    """Update a template"""
    try:
        service = TemplateService(db)
        return await service.update_template(template_id, template_update, current_user.id, create_version)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        logger.error("Error updating template: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, str]:
    """Soft delete a template"""
    try:
        service = TemplateService(db)
        await service.delete_template(template_id)
        return {"message": "Template deleted successfully"}
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        logger.error("Error deleting template: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


# Template Version Management


@router.post("/templates/{template_id}/versions", response_model=TemplateVersionResponse)
async def create_template_version(
    template_id: str = Path(...),
    version_data: TemplateVersionCreate = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> TemplateVersionResponse:
    """Create a new version of a template"""
    try:
        service = TemplateService(db)
        return await service.create_template_version(template_id, version_data, current_user.id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        logger.error("Error creating template version: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/templates/{template_id}/versions", response_model=List[TemplateVersionResponse])
async def get_template_versions(
    template_id: str = Path(...),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> List[TemplateVersionResponse]:
    """Get version history for a template"""
    try:
        service = TemplateService(db)
        return await service.get_template_versions(template_id, limit)
    except Exception as e:
        logger.error("Error getting template versions: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/templates/{template_id}/versions/{version_id}/restore", response_model=COBTemplateResponse)
async def restore_template_version(
    template_id: str = Path(...),
    version_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> COBTemplateResponse:
    """Restore a template to a previous version"""
    try:
        service = TemplateService(db)
        return await service.restore_template_version(template_id, version_id, current_user.id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        logger.error("Error restoring template version: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


# Template Validation


@router.post("/templates/{template_id}/validate")
async def validate_template(
    template_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """Validate all blocks in a template"""
    try:
        service = TemplateService(db)
        return await service.validate_template_blocks(template_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        logger.error("Error validating template: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/templates/{template_id}/variables", response_model=List[str])
async def get_template_variables(
    template_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> List[str]:
    """Get all variables required by a template"""
    try:
        service = TemplateService(db)
        return await service.get_template_variables(template_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        logger.error("Error getting template variables: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


# Scan Data Browsing


@router.post("/scan-data/browse", response_model=DataBrowseResponse)
async def browse_scan_data(
    request: DataBrowseRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)
) -> DataBrowseResponse:
    """Browse available scan data with filtering"""
    try:
        # First get from cache
        cache_query = db.query(COBScanDataCache)

        # Apply filters to cache
        if request.scanner_type:
            cache_query = cache_query.filter(COBScanDataCache.scanner_type == request.scanner_type.value)

        if request.date_range:
            cache_query = cache_query.filter(
                COBScanDataCache.scan_date >= request.date_range.start,
                COBScanDataCache.scan_date <= request.date_range.end,
            )

        if request.model_filter:
            cache_query = cache_query.filter(COBScanDataCache.target_model.in_(request.model_filter))

        # Get cached results
        cached_data = cache_query.all()
        cached_ids = {scan.execution_id for scan in cached_data}

        # Also query OrchestratorExecution for uncached results
        from app.models.orchestrator import OrchestratorExecution

        exec_query = db.query(OrchestratorExecution).filter(OrchestratorExecution.status == "completed")

        if request.date_range:
            exec_query = exec_query.filter(
                OrchestratorExecution.started_at >= request.date_range.start,
                OrchestratorExecution.started_at <= request.date_range.end,
            )

        executions = exec_query.all()

        # Process results
        results = []

        # Add cached results
        for scan in cached_data:
            summary = ScanResultSummary(
                execution_id=scan.execution_id,
                scanner_type=scan.scanner_type,
                target_model=scan.target_model,
                scan_date=scan.scan_date,
                total_tests=scan.score_data.get("total_tests", 0),
                score_summary=scan.score_data.get("score_summary", {}),
                key_findings=scan.score_data.get("key_findings", []),
                severity_distribution=scan.score_data.get("severity_distribution", {}),
                dataset_info=scan.metadata.get("dataset_info"),
            )
            results.append(summary)

        # Add uncached execution results
        for execution in executions:
            if str(execution.id) not in cached_ids:
                # Process execution results
                results_data = execution.results or {}
                scores = results_data.get("scores", [])
                metadata = results_data.get("execution_summary", {}).get("metadata", {})

                # Skip if doesn't match filters
                if request.scanner_type:
                    orchestrator_type = metadata.get("orchestrator_type", "").lower()
                    if request.scanner_type.value not in orchestrator_type:
                        continue

                if request.model_filter:
                    target_model = metadata.get("target_model", "Unknown")
                    if target_model not in request.model_filter:
                        continue

                # Create summary
                summary = ScanResultSummary(
                    execution_id=str(execution.id),
                    scanner_type="pyrit" if "pyrit" in metadata.get("orchestrator_type", "").lower() else "garak",
                    target_model=metadata.get("target_model", "Unknown"),
                    scan_date=execution.started_at,
                    total_tests=len(scores),
                    score_summary={},  # Would need processing
                    key_findings=[],
                    severity_distribution={},
                    dataset_info=metadata.get("dataset_name"),
                )
                results.append(summary)

        # Sort results
        if request.sort_by == "date":
            results.sort(key=lambda x: x.scan_date, reverse=(request.sort_order == "desc"))
        elif request.sort_by == "model":
            results.sort(key=lambda x: x.target_model, reverse=(request.sort_order == "desc"))
        elif request.sort_by == "scanner":
            results.sort(key=lambda x: x.scanner_type, reverse=(request.sort_order == "desc"))

        # Apply pagination
        total_count = len(results)
        start = request.offset
        end = request.offset + request.limit
        paginated_results = results[start:end]

        return DataBrowseResponse(
            results=paginated_results,
            total_count=total_count,
            has_more=(request.offset + request.limit) < total_count,
            filters_applied=request.dict(exclude_unset=True),
        )

    except Exception as e:
        logger.error("Error browsing scan data: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


# Report Generation


@router.post("/generate", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    storage_service: StorageService = Depends(get_storage_service),
) -> ReportGenerationResponse:
    """Generate a report from template and scan data"""
    try:
        engine = ReportGenerationEngine(db, storage_service)
        response = await engine.generate_report(request, current_user.id)

        # Start background processing if not preview
        if not request.preview_mode:
            background_tasks.add_task(engine.start_processing_queue)

        return response
    except Exception as e:
        logger.error("Error generating report: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/preview", response_model=PreviewResponse)
async def preview_template(
    request: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    storage_service: StorageService = Depends(get_storage_service),
) -> PreviewResponse:
    """Generate a preview of template with sample data"""
    try:
        engine = ReportGenerationEngine(db, storage_service)
        return await engine.generate_preview(request, current_user.id)
    except Exception as e:
        logger.error("Error generating preview: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/status/{report_id}", response_model=ReportStatus)
async def get_report_status(
    report_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    storage_service: StorageService = Depends(get_storage_service),
) -> ReportStatus:
    """Get the status of a report generation"""
    try:
        engine = ReportGenerationEngine(db, storage_service)
        return await engine.get_report_status(report_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        logger.error("Error getting report status: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/download/{report_id}/{format}")
async def download_report(
    report_id: str = Path(...),
    file_format: str = Path(..., regex="^(pdf|json|markdown|html)$", alias="format"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    storage_service: StorageService = Depends(get_storage_service),
) -> FileResponse:
    """Download a generated report in specified format"""
    try:
        # Check if report exists and user has access

        report = db.query(COBReport).filter(COBReport.id == report_id).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if report.status != "completed":
            raise HTTPException(status_code=400, detail=f"Report is not ready. Current status: {report.status}")

        # Check if format was generated
        output_formats = report.config.get("output_formats", [])
        if file_format.upper() not in [f.upper() for f in output_formats]:
            raise HTTPException(status_code=400, detail=f"Report was not generated in {file_format} format")

        # Get file from storage
        file_key = f"reports/{report_id}/{report_id}.{file_format.lower()}"

        if not storage_service.file_exists(file_key):
            raise HTTPException(status_code=404, detail=f"Report file not found in {file_format} format")

        # Download from storage
        temp_dir = tempfile.gettempdir()
        file_path = await storage_service.download_file_async(file_key, f"{temp_dir}/{report_id}.{file_format}")

        # Return file response
        media_type_map = {
            "pdf": "application/pdf",
            "json": "application/json",
            "markdown": "text/markdown",
            "html": "text/html",
        }

        return FileResponse(
            path=file_path,
            media_type=media_type_map.get(file_format, "application/octet-stream"),
            filename=f"{report.name}.{file_format}",
            headers={"Content-Disposition": f'attachment; filename="{report.name}.{file_format}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error downloading report: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/download/{report_id}")
async def get_download_links(
    report_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    storage_service: StorageService = Depends(get_storage_service),
) -> Dict[str, Any]:
    """Get download links for all available formats of a report"""
    try:
        # Check if report exists

        report = db.query(COBReport).filter(COBReport.id == report_id).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if report.status != "completed":
            raise HTTPException(status_code=400, detail=f"Report is not ready. Current status: {report.status}")

        # Get available formats
        output_formats = report.config.get("output_formats", [])
        download_links = {}

        for format_type in output_formats:
            file_key = f"reports/{report_id}/{report_id}.{format_type.lower()}"
            if storage_service.file_exists(file_key):
                download_links[format_type.lower()] = {
                    "url": f"/api/v1/reports/download/{report_id}/{format_type.lower()}",
                    "size": storage_service.get_file_size(file_key),
                    "available": True,
                }
            else:
                download_links[format_type.lower()] = {"url": None, "size": 0, "available": False}

        return {
            "report_id": report_id,
            "report_name": report.name,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "formats": download_links,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting download links: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/generate/batch")
async def generate_batch_reports(
    request: BatchReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    storage_service: StorageService = Depends(get_storage_service),
) -> Dict[str, Any]:
    """Generate multiple reports in batch"""
    try:
        engine = ReportGenerationEngine(db, storage_service)

        batch_id = str(uuid.uuid4())
        report_ids = []

        # Create individual report tasks
        for scan_group in request.scan_data_groups:
            report_request = ReportGenerationRequest(
                template_id=request.template_id,
                scan_data_ids=scan_group,
                output_formats=request.output_formats,
                report_name=f"{request.batch_name or 'Batch'} - Group {len(report_ids) + 1}",
            )

            response = await engine.generate_report(report_request, current_user.id)
            report_ids.append(response.report_id)

        # Start background processing
        background_tasks.add_task(engine.start_processing_queue)

        return {
            "batch_id": batch_id,
            "report_ids": report_ids,
            "total_reports": len(report_ids),
            "status": "processing",
        }

    except Exception as e:
        logger.error("Error generating batch reports: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


# Block and Variable Management


@router.get("/blocks", response_model=List[BlockDefinitionResponse])
async def list_block_definitions(
    category: Optional[str] = Query(None),
    is_active: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> List[BlockDefinitionResponse]:
    """List available block definitions"""
    try:
        query = db.query(COBBlockDefinition).filter(COBBlockDefinition.is_active == is_active)

        if category:
            query = query.filter(COBBlockDefinition.category == category)

        blocks = query.all()

        return [BlockDefinitionResponse.from_orm(block) for block in blocks]
    except Exception as e:
        logger.error("Error listing block definitions: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/blocks/registry")
async def get_block_registry(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get the current block registry"""
    try:
        return block_registry.export_registry()
    except Exception as e:
        logger.error("Error getting block registry: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/variables", response_model=List[ReportVariableResponse])
async def list_report_variables(
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    is_active: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> List[ReportVariableResponse]:
    """List available report variables"""
    try:
        query = db.query(COBReportVariable).filter(COBReportVariable.is_active == is_active)

        if category:
            query = query.filter(COBReportVariable.category == category)

        if source:
            query = query.filter(COBReportVariable.source == source)

        variables = query.all()

        return [ReportVariableResponse.from_orm(var) for var in variables]
    except Exception as e:
        logger.error("Error listing report variables: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/variables/categories")
async def get_variable_categories(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)
) -> List[str]:
    """Get all variable categories"""
    try:
        categories = db.query(COBReportVariable.category).distinct().all()
        return [cat[0] for cat in categories if cat[0]]
    except Exception as e:
        logger.error("Error getting variable categories: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


# Template Initialization


@router.post("/templates/initialize")
async def initialize_default_templates(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """Initialize default report templates"""
    try:
        service = TemplateService(db)

        initial_templates = get_initial_templates()
        created_count = 0
        errors = []

        logger.info("Initializing %d default templates", len(initial_templates))

        for template_data in initial_templates:
            try:
                # Check if template already exists
                existing = await service.search_templates(template_data["name"])
                if not existing:
                    logger.info("Creating template: %s", template_data["name"])
                    template_create = COBTemplateCreate(**template_data)
                    await service.create_template(template_create, current_user.username)
                    created_count += 1
                    logger.info("Successfully created template: %s", template_data["name"])
                else:
                    logger.info("Template already exists: %s", template_data["name"])
            except Exception as e:
                error_msg = f"Error creating template '{template_data["name"]}': {str(e)}"
                logger.error(error_msg, exc_info=True)
                errors.append(error_msg)

        # Commit all changes
        await db.commit()
        logger.info("Database commit complete. Created %d templates", created_count)

        return {
            "message": "Template initialization complete",
            "templates_created": created_count,
            "total_templates": len(initial_templates),
            "errors": errors if errors else None,
        }

    except Exception as e:
        logger.error("Error initializing templates: %s", str(e))
        raise HTTPException(status_code=500, detail="Internal server error") from e


# Schedule Management Endpoints (migrated from COB system)


@router.get("/schedules", response_model=COBScheduleListResponse, summary="List report schedules")
async def list_schedules(
    skip: int = Query(0, ge=1),
    limit: int = Query(50, ge=1, le=100),
    active_only: bool = Query(True),
    template_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> COBScheduleListResponse:
    """List report schedules with pagination"""
    try:
        query = select(COBSchedule)
        if active_only:
            query = query.where(COBSchedule.is_active is True)
        if template_id:
            query = query.where(COBSchedule.template_id == uuid.UUID(template_id))
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        schedules = result.scalars().all()

        # Get total count
        count_query = select(func.count(COBSchedule.id))
        if active_only:
            count_query = count_query.where(COBSchedule.is_active is True)
        if template_id:
            count_query = count_query.where(COBSchedule.template_id == uuid.UUID(template_id))
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        schedule_responses = []
        for schedule in schedules:
            schedule_dict = schedule.to_dict()
            schedule_dict["links"] = {
                "self": f"/api/v1/reports/schedules/{schedule.id}",
                "template": f"/api/v1/reports/templates/{schedule.template_id}",
                "executions": f"/api/v1/reports/schedules/{schedule.id}/executions",
            }
            schedule_responses.append(COBScheduleResponse(**schedule_dict))

        return COBScheduleListResponse(
            schedules=schedule_responses,
            total=total,
            links={
                "self": f"/api/v1/reports/schedules?skip={skip}&limit={limit}",
                "create": "/api/v1/reports/schedules",
            },
        )

    except Exception as e:
        logger.error("Error listing schedules: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}") from e


@router.post("/schedules", response_model=COBScheduleResponse, summary="Create report schedule")
async def create_schedule(
    schedule_data: COBScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> COBScheduleResponse:
    """Create a new report schedule"""
    try:
        # Verify template exists
        template_query = select(COBTemplate).where(COBTemplate.id == schedule_data.template_id)
        template_result = await db.execute(template_query)
        template = template_result.scalar()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {schedule_data.template_id}")

        # Create schedule
        schedule = COBSchedule(
            template_id=schedule_data.template_id,
            name=schedule_data.name,
            description=schedule_data.description,
            frequency=schedule_data.frequency,
            schedule_config=schedule_data.schedule_config,
            notification_config=schedule_data.notification_config,
            is_active=schedule_data.is_active,
            created_by=current_user.username,
        )

        # Set next run time based on frequency

        now = datetime.now(timezone.utc)
        if schedule.frequency == "daily":
            schedule.next_run_at = now + timedelta(days=1)
        elif schedule.frequency == "weekly":
            schedule.next_run_at = now + timedelta(weeks=1)
        elif schedule.frequency == "monthly":
            schedule.next_run_at = now + timedelta(days=30)

        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)

        schedule_dict = schedule.to_dict()
        schedule_dict["links"] = {
            "self": f"/api/v1/reports/schedules/{schedule.id}",
            "update": f"/api/v1/reports/schedules/{schedule.id}",
            "delete": f"/api/v1/reports/schedules/{schedule.id}",
            "template": f"/api/v1/reports/templates/{schedule.template_id}",
        }

        logger.info("Schedule created: %s by %s", schedule.id, current_user.username)
        return COBScheduleResponse(**schedule_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating schedule: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}") from e


@router.post("/internal/check-schedules", summary="Check scheduled reports (Internal)")
async def check_scheduled_reports(db: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    """Check and execute scheduled reports"""
    try:
        # Get all active schedules that are due
        now = datetime.now(timezone.utc)
        query = select(COBSchedule).where(COBSchedule.is_active is True, COBSchedule.next_run_at <= now)
        result = await db.execute(query)
        due_schedules = result.scalars().all()

        executed = []
        for schedule in due_schedules:
            try:
                # Execute the schedule
                await _execute_scheduled_report(schedule.id, db)
                executed.append(str(schedule.id))
            except Exception as e:
                logger.error("Failed to execute schedule %s: %s", schedule.id, e)

        return {
            "checked_at": now.isoformat(),
            "schedules_found": len(due_schedules),
            "schedules_executed": len(executed),
            "executed_ids": executed,
        }

    except Exception as e:
        logger.error("Error checking schedules: %s", e)
        return {"error": str(e), "checked_at": datetime.now(timezone.utc).isoformat()}


async def _execute_scheduled_report(schedule_id: uuid.UUID, db: AsyncSession) -> None:
    """Execute a scheduled report generation"""
    try:
        # Get the schedule
        query = select(COBSchedule).where(COBSchedule.id == schedule_id)
        result = await db.execute(query)
        schedule = result.scalar()

        if not schedule:
            raise ValueError(f"Schedule not found: {schedule_id}")

        # Create execution record
        execution = COBScheduleExecution(
            schedule_id=schedule.id,
            execution_status="started",
            started_at=datetime.now(timezone.utc),
        )
        db.add(execution)
        await db.commit()

        # Generate report (simplified version)
        try:
            # Get the template
            template_query = select(COBTemplate).where(COBTemplate.id == schedule.template_id)
            template_result = await db.execute(template_query)
            template = template_result.scalar()

            if not template:
                raise ValueError(f"Template not found: {schedule.template_id}")

            # Create report name
            report_name = f"{schedule.name} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"

            # Create report record
            new_report = COBReport(
                template_id=schedule.template_id,
                schedule_id=schedule.id,
                report_name=report_name,
                report_period_start=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0),
                report_period_end=datetime.now(timezone.utc),
                generation_status="completed",
                content_blocks={},
                ai_analysis_results={},
                export_results={},
                generation_metadata={
                    "generated_by_schedule": True,
                    "schedule_name": schedule.name,
                },
                generated_by="system_scheduler",
            )

            db.add(new_report)
            await db.commit()
            await db.refresh(new_report)

            # Update execution
            execution.execution_status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            execution.report_id = new_report.id
            execution.execution_log = {"message": "Schedule execution completed"}

            # Update schedule next run time
            schedule.last_run_at = datetime.now(timezone.utc)
            if schedule.frequency == "daily":
                schedule.next_run_at = schedule.last_run_at + timedelta(days=1)
            elif schedule.frequency == "weekly":
                schedule.next_run_at = schedule.last_run_at + timedelta(weeks=1)
            elif schedule.frequency == "monthly":
                schedule.next_run_at = schedule.last_run_at + timedelta(days=30)

            await db.commit()
            logger.info("Scheduled report executed: %s", schedule_id)

        except Exception as e:
            execution.execution_status = "failed"
            execution.error_details = {"error": str(e)}
            await db.commit()
            raise

    except Exception as e:
        logger.error("Error executing scheduled report %s: %s", schedule_id, e)
        raise


# System Status Endpoint


@router.get("/system/status", response_model=COBSystemStatusResponse, summary="Get report system status")
async def get_system_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> COBSystemStatusResponse:
    """Get overall report system status"""
    try:
        # Count active templates
        templates_result = await db.execute(select(func.count(COBTemplate.id)).where(COBTemplate.is_active is True))
        active_templates = templates_result.scalar()

        # Count active schedules
        schedules_result = await db.execute(select(func.count(COBSchedule.id)).where(COBSchedule.is_active is True))
        active_schedules = schedules_result.scalar()

        # Count pending executions
        pending_result = await db.execute(
            select(func.count(COBScheduleExecution.id)).where(COBScheduleExecution.execution_status == "started")
        )
        pending_executions = pending_result.scalar()

        # Get last execution time
        last_execution_result = await db.execute(
            select(COBScheduleExecution.completed_at)
            .where(COBScheduleExecution.execution_status == "completed")
            .order_by(COBScheduleExecution.completed_at.desc())
            .limit(1)
        )
        last_execution = last_execution_result.scalar()

        # Get next scheduled execution
        next_execution_result = await db.execute(
            select(COBSchedule.next_run_at)
            .where(COBSchedule.is_active is True, COBSchedule.next_run_at.isnot(None))
            .order_by(COBSchedule.next_run_at.asc())
            .limit(1)
        )
        next_execution = next_execution_result.scalar()

        # Determine system health
        health = "healthy"
        if pending_executions > 10:
            health = "degraded"
        elif pending_executions > 50:
            health = "unhealthy"

        return COBSystemStatusResponse(
            status=health,
            active_templates=active_templates,
            active_schedules=active_schedules,
            pending_executions=pending_executions,
            last_execution_time=last_execution.isoformat() if last_execution else None,
            next_scheduled_execution=next_execution.isoformat() if next_execution else None,
            system_info={
                "version": "2.0.0",
                "report_engine": "COB Report System",
                "features": ["templates", "scheduling", "ai_analysis", "multi_format_export"],
            },
        )

    except Exception as e:
        logger.error("Error getting system status: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}") from e


# Export the router
report_routes = router
