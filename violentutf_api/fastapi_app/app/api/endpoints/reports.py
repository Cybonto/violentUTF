"""
Enhanced API endpoints for Advanced Dashboard Report Setup
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.report_system.report_models import COBBlockDefinition, COBReportVariable, COBScanDataCache
from app.models.user import User

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
    OutputFormat,
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
from app.services.storage_service import get_storage_service
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# Template Management Endpoints


@router.post("/templates", response_model=COBTemplateResponse)
async def create_template(
    template: COBTemplateCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> COBTemplateResponse:
    """Create a new report template"""
    try:
        service = TemplateService(db)
        return service.create_template(template, current_user.id)
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


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
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """List templates with filtering and pagination"""
    try:
        service = TemplateService(db)

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

        templates, total = service.list_templates(
            skip=skip, limit=limit, filters=filters, sort_by=sort_by, sort_order=sort_order
        )

        return {
            "templates": templates,
            "total": total,
            "page": skip // limit + 1,
            "pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/templates/search", response_model=List[COBTemplateResponse])
async def search_templates(
    q: str = Query(..., min_length=2), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[COBTemplateResponse]:
    """Search templates by name, description, or metadata"""
    try:
        service = TemplateService(db)
        return service.search_templates(q)
    except Exception as e:
        logger.error(f"Error searching templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/templates/recommend", response_model=List[TemplateRecommendation])
async def recommend_templates(
    scan_data: Dict[str, Any] = Body(...),
    limit: int = Query(5, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TemplateRecommendation]:
    """Get template recommendations based on scan data"""
    try:
        service = TemplateService(db)
        return service.recommend_templates(scan_data, limit)
    except Exception as e:
        logger.error(f"Error recommending templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/templates/{template_id}", response_model=COBTemplateResponse)
async def get_template(
    template_id: str = Path(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> COBTemplateResponse:
    """Get a specific template"""
    try:
        service = TemplateService(db)
        return service.get_template(template_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Error getting template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/templates/{template_id}", response_model=COBTemplateResponse)
async def update_template(
    template_id: str = Path(...),
    template_update: COBTemplateUpdate = Body(...),
    create_version: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> COBTemplateResponse:
    """Update a template"""
    try:
        service = TemplateService(db)
        return service.update_template(template_id, template_update, current_user.id, create_version)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Error updating template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str = Path(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, str]:
    """Soft delete a template"""
    try:
        service = TemplateService(db)
        service.delete_template(template_id)
        return {"message": "Template deleted successfully"}
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Error deleting template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Template Version Management


@router.post("/templates/{template_id}/versions", response_model=TemplateVersionResponse)
async def create_template_version(
    template_id: str = Path(...),
    version_data: TemplateVersionCreate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TemplateVersionResponse:
    """Create a new version of a template"""
    try:
        service = TemplateService(db)
        return service.create_template_version(template_id, version_data, current_user.id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Error creating template version: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}/versions", response_model=List[TemplateVersionResponse])
async def get_template_versions(
    template_id: str = Path(...),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[TemplateVersionResponse]:
    """Get version history for a template"""
    try:
        service = TemplateService(db)
        return service.get_template_versions(template_id, limit)
    except Exception as e:
        logger.error(f"Error getting template versions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/templates/{template_id}/versions/{version_id}/restore", response_model=COBTemplateResponse)
async def restore_template_version(
    template_id: str = Path(...),
    version_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> COBTemplateResponse:
    """Restore a template to a previous version"""
    try:
        service = TemplateService(db)
        return service.restore_template_version(template_id, version_id, current_user.id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Error restoring template version: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# Template Validation


@router.post("/templates/{template_id}/validate")
async def validate_template(
    template_id: str = Path(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Validate all blocks in a template"""
    try:
        service = TemplateService(db)
        return service.validate_template_blocks(template_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Error validating template: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/templates/{template_id}/variables", response_model=List[str])
async def get_template_variables(
    template_id: str = Path(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[str]:
    """Get all variables required by a template"""
    try:
        service = TemplateService(db)
        return service.get_template_variables(template_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Error getting template variables: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Scan Data Browsing


@router.post("/scan-data/browse", response_model=DataBrowseResponse)
async def browse_scan_data(
    request: DataBrowseRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
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
        logger.error(f"Error browsing scan data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Report Generation


@router.post("/generate", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service=Depends(get_storage_service),
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
        logger.error(f"Error generating report: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/preview", response_model=PreviewResponse)
async def preview_template(
    request: PreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service=Depends(get_storage_service),
) -> PreviewResponse:
    """Generate a preview of template with sample data"""
    try:
        engine = ReportGenerationEngine(db, storage_service)
        return await engine.generate_preview(request, current_user.id)
    except Exception as e:
        logger.error(f"Error generating preview: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/{report_id}", response_model=ReportStatus)
async def get_report_status(
    report_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service=Depends(get_storage_service),
) -> ReportStatus:
    """Get the status of a report generation"""
    try:
        engine = ReportGenerationEngine(db, storage_service)
        return await engine.get_report_status(report_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        logger.error(f"Error getting report status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/download/{report_id}/{format}")
async def download_report(
    report_id: str = Path(...),
    format: str = Path(..., regex="^(pdf|json|markdown|html)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service=Depends(get_storage_service),
):
    """Download a generated report in specified format"""
    try:
        # Check if report exists and user has access
        from app.models.cob_models import COBReport

        report = db.query(COBReport).filter(COBReport.id == report_id).first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if report.status != "completed":
            raise HTTPException(status_code=400, detail=f"Report is not ready. Current status: {report.status}")

        # Check if format was generated
        output_formats = report.config.get("output_formats", [])
        if format.upper() not in [f.upper() for f in output_formats]:
            raise HTTPException(status_code=400, detail=f"Report was not generated in {format} format")

        # Get file from storage
        file_key = f"reports/{report_id}/{report_id}.{format.lower()}"

        if not storage_service.file_exists(file_key):
            raise HTTPException(status_code=404, detail=f"Report file not found in {format} format")

        # Download from storage
        file_path = await storage_service.download_file_async(file_key, f"/tmp/{report_id}.{format}")

        # Return file response
        media_type_map = {
            "pdf": "application/pdf",
            "json": "application/json",
            "markdown": "text/markdown",
            "html": "text/html",
        }

        return FileResponse(
            path=file_path,
            media_type=media_type_map.get(format, "application/octet-stream"),
            filename=f"{report.name}.{format}",
            headers={"Content-Disposition": f'attachment; filename="{report.name}.{format}"'},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/download/{report_id}")
async def get_download_links(
    report_id: str = Path(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service=Depends(get_storage_service),
) -> Dict[str, Any]:
    """Get download links for all available formats of a report"""
    try:
        # Check if report exists
        from app.models.cob_models import COBReport

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
        logger.error(f"Error getting download links: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/generate/batch")
async def generate_batch_reports(
    request: BatchReportRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage_service=Depends(get_storage_service),
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
        logger.error(f"Error generating batch reports: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# Block and Variable Management


@router.get("/blocks", response_model=List[BlockDefinitionResponse])
async def list_block_definitions(
    category: Optional[str] = Query(None),
    is_active: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[BlockDefinitionResponse]:
    """List available block definitions"""
    try:
        query = db.query(COBBlockDefinition).filter(COBBlockDefinition.is_active == is_active)

        if category:
            query = query.filter(COBBlockDefinition.category == category)

        blocks = query.all()

        return [BlockDefinitionResponse.from_orm(block) for block in blocks]
    except Exception as e:
        logger.error(f"Error listing block definitions: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/blocks/registry")
async def get_block_registry(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get the current block registry"""
    try:
        return block_registry.export_registry()
    except Exception as e:
        logger.error(f"Error getting block registry: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/variables", response_model=List[ReportVariableResponse])
async def list_report_variables(
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    is_active: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
        logger.error(f"Error listing report variables: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/variables/categories")
async def get_variable_categories(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> List[str]:
    """Get all variable categories"""
    try:
        categories = db.query(COBReportVariable.category).distinct().all()
        return [cat[0] for cat in categories if cat[0]]
    except Exception as e:
        logger.error(f"Error getting variable categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Template Initialization


@router.post("/templates/initialize")
async def initialize_default_templates(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Initialize default report templates"""
    try:
        service = TemplateService(db)

        initial_templates = get_initial_templates()
        created_count = 0

        for template_data in initial_templates:
            try:
                # Check if template already exists
                existing = service.search_templates(template_data["name"])
                if not existing:
                    template_create = COBTemplateCreate(**template_data)
                    service.create_template(template_create, current_user.id)
                    created_count += 1
            except Exception as e:
                logger.warning(f"Error creating template '{template_data['name']}': {str(e)}")

        return {
            "message": "Template initialization complete",
            "templates_created": created_count,
            "total_templates": len(initial_templates),
        }

    except Exception as e:
        logger.error(f"Error initializing templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Export the router
report_routes = router
