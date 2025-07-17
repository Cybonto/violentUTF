"""
COB Reports API endpoints
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from app.core.auth import get_current_user
from app.db.database import get_session
from app.models.cob_models import COBReport, COBSchedule, COBScheduleExecution, COBTemplate
from app.schemas import (
    COBExportRequest,
    COBExportResponse,
    COBReportCreate,
    COBReportListResponse,
    COBReportResponse,
    COBScheduleCreate,
    COBScheduleExecutionListResponse,
    COBScheduleExecutionResponse,
    COBScheduleListResponse,
    COBScheduleResponse,
    COBScheduleUpdate,
    COBSystemStatusResponse,
    COBTemplateCreate,
    COBTemplateListResponse,
    COBTemplateResponse,
    COBTemplateUpdate,
)
from app.services.cob_pdf_service import cob_pdf_generator
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


# Template endpoints
@router.get("/templates", response_model=COBTemplateListResponse, summary="List COB templates")
async def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active_only: bool = Query(True),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List COB report templates with pagination"""
    try:
        query = select(COBTemplate)
        if active_only:
            query = query.where(COBTemplate.is_active == True)  # noqa: E712
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        templates = result.scalars().all()

        # Get total count
        count_query = select(func.count(COBTemplate.id))
        if active_only:
            count_query = count_query.where(COBTemplate.is_active == True)  # noqa: E712
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        template_responses = []
        for template in templates:
            template_dict = template.to_dict()
            template_dict["links"] = {
                "self": f"/api/v1/cob/templates/{template.id}",
                "schedules": f"/api/v1/cob/templates/{template.id}/schedules",
                "reports": f"/api/v1/cob/templates/{template.id}/reports",
            }
            template_responses.append(COBTemplateResponse(**template_dict))

        return COBTemplateListResponse(
            templates=template_responses,
            total=total,
            links={
                "self": f"/api/v1/cob/templates?skip={skip}&limit={limit}",
                "create": "/api/v1/cob/templates",
            },
        )

    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.post("/templates", response_model=COBTemplateResponse, summary="Create COB template")
async def create_template(
    template_data: COBTemplateCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new COB report template"""
    try:
        # Check if template name already exists
        existing_query = select(COBTemplate).where(COBTemplate.name == template_data.name)
        existing_result = await db.execute(existing_query)
        if existing_result.scalar():
            raise HTTPException(status_code=400, detail=f"Template with name '{template_data.name}' already exists")

        template = COBTemplate(
            name=template_data.name,
            description=template_data.description,
            template_config=template_data.template_config,
            ai_prompts=template_data.ai_prompts,
            export_formats=template_data.export_formats or ["markdown", "pdf", "json"],
            tags=template_data.tags,
            created_by=current_user.username,
        )

        db.add(template)
        await db.commit()
        await db.refresh(template)

        template_dict = template.to_dict()
        template_dict["links"] = {
            "self": f"/api/v1/cob/templates/{template.id}",
            "update": f"/api/v1/cob/templates/{template.id}",
            "delete": f"/api/v1/cob/templates/{template.id}",
            "schedules": f"/api/v1/cob/templates/{template.id}/schedules",
        }

        logger.info(f"Template created: {template.id} by {current_user.username}")
        return COBTemplateResponse(**template_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create template: {str(e)}")


@router.get("/templates/{template_id}", response_model=COBTemplateResponse, summary="Get COB template")
async def get_template(
    template_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get a specific COB template by ID"""
    try:
        query = select(COBTemplate).where(COBTemplate.id == template_id)
        result = await db.execute(query)
        template = result.scalar()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

        template_dict = template.to_dict()
        template_dict["links"] = {
            "self": f"/api/v1/cob/templates/{template.id}",
            "update": f"/api/v1/cob/templates/{template.id}",
            "delete": f"/api/v1/cob/templates/{template.id}",
            "schedules": f"/api/v1/cob/templates/{template.id}/schedules",
            "reports": f"/api/v1/cob/templates/{template.id}/reports",
        }

        return COBTemplateResponse(**template_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get template: {str(e)}")


@router.put("/templates/{template_id}", response_model=COBTemplateResponse, summary="Update COB template")
async def update_template(
    template_id: UUID,
    template_update: COBTemplateUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update a COB template"""
    try:
        query = select(COBTemplate).where(COBTemplate.id == template_id)
        result = await db.execute(query)
        template = result.scalar()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

        # Update only provided fields
        update_data = template_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)

        template.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(template)

        template_dict = template.to_dict()
        template_dict["links"] = {
            "self": f"/api/v1/cob/templates/{template.id}",
            "schedules": f"/api/v1/cob/templates/{template.id}/schedules",
            "reports": f"/api/v1/cob/templates/{template.id}/reports",
        }

        logger.info(f"Template updated: {template.id} by {current_user.username}")
        return COBTemplateResponse(**template_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update template: {str(e)}")


@router.delete("/templates/{template_id}", summary="Delete COB template")
async def delete_template(
    template_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Delete a COB template (soft delete by setting is_active=False)"""
    try:
        query = select(COBTemplate).where(COBTemplate.id == template_id)
        result = await db.execute(query)
        template = result.scalar()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")

        # Soft delete
        template.is_active = False
        template.updated_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(f"Template deleted: {template.id} by {current_user.username}")
        return {"message": "Template deleted successfully", "template_id": str(template_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete template: {str(e)}")


# Schedule endpoints
@router.get("/schedules", response_model=COBScheduleListResponse, summary="List COB schedules")
async def list_schedules(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active_only: bool = Query(True),
    template_id: Optional[UUID] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List COB report schedules with pagination"""
    try:
        query = select(COBSchedule)
        if active_only:
            query = query.where(COBSchedule.is_active == True)  # noqa: E712
        if template_id:
            query = query.where(COBSchedule.template_id == template_id)
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        schedules = result.scalars().all()

        # Get total count
        count_query = select(func.count(COBSchedule.id))
        if active_only:
            count_query = count_query.where(COBSchedule.is_active == True)  # noqa: E712
        if template_id:
            count_query = count_query.where(COBSchedule.template_id == template_id)
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        schedule_responses = []
        for schedule in schedules:
            schedule_dict = schedule.to_dict()
            schedule_dict["links"] = {
                "self": f"/api/v1/cob/schedules/{schedule.id}",
                "template": f"/api/v1/cob/templates/{schedule.template_id}",
                "executions": f"/api/v1/cob/schedules/{schedule.id}/executions",
            }
            schedule_responses.append(COBScheduleResponse(**schedule_dict))

        return COBScheduleListResponse(
            schedules=schedule_responses,
            total=total,
            links={"self": f"/api/v1/cob/schedules?skip={skip}&limit={limit}", "create": "/api/v1/cob/schedules"},
        )

    except Exception as e:
        logger.error(f"Error listing schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}")


@router.post("/schedules", response_model=COBScheduleResponse, summary="Create COB schedule")
async def create_schedule(
    schedule_data: COBScheduleCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new COB report schedule"""
    try:
        # Verify template exists
        template_query = select(COBTemplate).where(
            COBTemplate.id == schedule_data.template_id, COBTemplate.is_active == True  # noqa: E712
        )
        template_result = await db.execute(template_query)
        if not template_result.scalar():
            raise HTTPException(status_code=400, detail=f"Template not found: {schedule_data.template_id}")

        schedule = COBSchedule(
            template_id=schedule_data.template_id,
            name=schedule_data.name,
            description=schedule_data.description,
            frequency=schedule_data.frequency,
            schedule_time=schedule_data.schedule_time,
            timezone=schedule_data.timezone or "UTC",
            days_of_week=schedule_data.days_of_week,
            day_of_month=schedule_data.day_of_month,
            ai_model_config=schedule_data.ai_model_config,
            export_config=schedule_data.export_config,
            created_by=current_user.username,
        )

        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)

        schedule_dict = schedule.to_dict()
        schedule_dict["links"] = {
            "self": f"/api/v1/cob/schedules/{schedule.id}",
            "update": f"/api/v1/cob/schedules/{schedule.id}",
            "delete": f"/api/v1/cob/schedules/{schedule.id}",
            "template": f"/api/v1/cob/templates/{schedule.template_id}",
        }

        logger.info(f"Schedule created: {schedule.id} by {current_user.username}")
        return COBScheduleResponse(**schedule_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


# Internal endpoint for cron job
@router.post("/internal/check-schedules", summary="Check scheduled reports (Internal)")
async def check_scheduled_reports(
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Internal endpoint called by system cron to check for due schedules

    Note: This endpoint requires authentication. For cron jobs, use a service account
    or API key with appropriate permissions.
    """
    try:
        now = datetime.now(timezone.utc)

        # Get schedules that are due
        query = select(COBSchedule).where(
            COBSchedule.is_active == True,  # noqa: E712
            COBSchedule.next_run_at <= now,
        )
        result = await db.execute(query)
        due_schedules = result.scalars().all()

        processed = 0
        for schedule in due_schedules:
            # Add background task for each due schedule
            background_tasks.add_task(execute_scheduled_report, schedule.id, db)
            processed += 1

        logger.info(f"Processed {processed} due schedules")
        return {"processed": processed, "timestamp": now.isoformat()}

    except Exception as e:
        logger.error(f"Error checking schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check schedules: {str(e)}")


async def execute_scheduled_report(schedule_id: UUID, db: AsyncSession):
    """Execute a scheduled report (background task)"""
    try:
        # Get schedule details
        query = select(COBSchedule).where(COBSchedule.id == schedule_id)
        result = await db.execute(query)
        schedule = result.scalar()

        if not schedule:
            logger.error(f"Schedule not found for execution: {schedule_id}")
            return

        # Create execution record
        execution = COBScheduleExecution(
            schedule_id=schedule_id,
            execution_status="started",
            execution_log={
                "message": "Schedule execution started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.add(execution)
        await db.commit()

        # TODO: Implement actual report generation logic here
        # For now, just mark as completed
        execution.execution_status = "completed"
        execution.completed_at = datetime.now(timezone.utc)
        execution.execution_log = {
            "message": "Schedule execution completed (placeholder)",
            "steps": ["Started", "Placeholder execution", "Completed"],
        }

        # Update schedule next run time (simplified logic)
        schedule.last_run_at = datetime.now(timezone.utc)
        # TODO: Calculate proper next_run_at based on schedule frequency

        await db.commit()
        logger.info(f"Scheduled report executed: {schedule_id}")

    except Exception as e:
        logger.error(f"Error executing scheduled report {schedule_id}: {e}")
        # Update execution status to failed
        try:
            execution.execution_status = "failed"
            execution.error_details = {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}
            await db.commit()
        except Exception as commit_error:
            logger.error(f"Failed to update execution status: {commit_error}")


@router.get("/system/status", response_model=COBSystemStatusResponse, summary="Get COB system status")
async def get_system_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get overall COB system status"""
    try:
        # Count active templates
        templates_result = await db.execute(
            select(func.count(COBTemplate.id)).where(COBTemplate.is_active == True)  # noqa: E712
        )
        active_templates = templates_result.scalar()

        # Count active schedules
        schedules_result = await db.execute(
            select(func.count(COBSchedule.id)).where(COBSchedule.is_active == True)  # noqa: E712
        )
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
            .where(COBSchedule.is_active == True, COBSchedule.next_run_at.isnot(None))  # noqa: E712
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
            active_templates=active_templates,
            active_schedules=active_schedules,
            pending_executions=pending_executions,
            last_execution_time=last_execution,
            next_scheduled_execution=next_execution,
            system_health=health,
        )

    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")


# PDF Export endpoints
@router.get("/reports/{report_id}/export/pdf", summary="Export COB report as PDF")
async def export_report_pdf(
    report_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Export a COB report as PDF file"""
    try:
        # Get report with template
        report_query = select(COBReport).where(COBReport.id == report_id)
        report_result = await db.execute(report_query)
        report = report_result.scalar()

        if not report:
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")

        # Get template configuration
        template_query = select(COBTemplate).where(COBTemplate.id == report.template_id)
        template_result = await db.execute(template_query)
        template = template_result.scalar()

        if not template:
            raise HTTPException(status_code=404, detail=f"Template not found for report: {report_id}")

        # Generate PDF
        report_data = report.to_dict()
        template_config = template.template_config

        pdf_bytes = await cob_pdf_generator.generate_pdf(report_data, template_config)

        # Return PDF as response
        filename = f"{report.report_name.replace(' ', '_')}_{report_id}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}", "Content-Length": str(len(pdf_bytes))},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting report {report_id} to PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")


@router.post("/reports/{report_id}/export", response_model=COBExportResponse, summary="Request report export")
async def request_report_export(
    report_id: UUID,
    export_request: COBExportRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Request export of a COB report in specified format (async processing)"""
    try:
        # Verify report exists
        report_query = select(COBReport).where(COBReport.id == report_id)
        report_result = await db.execute(report_query)
        report = report_result.scalar()

        if not report:
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")

        # Validate export format
        supported_formats = ["pdf", "markdown", "json"]
        if export_request.export_format not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported export format: {export_request.export_format}. Supported: {supported_formats}",
            )

        # Generate export ID
        export_id = (
            f"export_{report_id}_{export_request.export_format}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        )

        # Add background task for export processing
        background_tasks.add_task(
            process_report_export,
            export_id,
            report_id,
            export_request.export_format,
            export_request.export_options or {},
            current_user.username,
            db,
        )

        # Return export response
        return COBExportResponse(
            export_id=export_id,
            report_id=report_id,
            export_format=export_request.export_format,
            export_status="pending",
            created_at=datetime.now(timezone.utc),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting export for report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to request export: {str(e)}")


@router.get("/exports/{export_id}", response_model=COBExportResponse, summary="Get export status")
async def get_export_status(
    export_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get status of an export request"""
    try:
        # In a production system, this would query an exports table
        # For now, return a basic response
        # TODO: Implement actual export tracking in database

        return COBExportResponse(
            export_id=export_id,
            report_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
            export_format="pdf",
            export_status="completed",
            file_path=f"/tmp/exports/{export_id}.pdf",
            download_url=f"/api/v1/cob/exports/{export_id}/download",
            created_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Error getting export status {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get export status: {str(e)}")


async def process_report_export(
    export_id: str, report_id: UUID, export_format: str, export_options: Dict[str, any], username: str, db: AsyncSession
):
    """Background task to process report export"""
    try:
        logger.info(f"Processing export {export_id} for report {report_id} in format {export_format}")

        # Get report and template
        report_query = select(COBReport).where(COBReport.id == report_id)
        report_result = await db.execute(report_query)
        report = report_result.scalar()

        if not report:
            logger.error(f"Report not found during export: {report_id}")
            return

        template_query = select(COBTemplate).where(COBTemplate.id == report.template_id)
        template_result = await db.execute(template_query)
        template = template_result.scalar()

        if not template:
            logger.error(f"Template not found during export: {report.template_id}")
            return

        # Process export based on format
        if export_format == "pdf":
            report_data = report.to_dict()
            template_config = template.template_config

            pdf_bytes = await cob_pdf_generator.generate_pdf(report_data, template_config)

            # Save to file system (in production, use proper file storage)
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(pdf_bytes)
                file_path = tmp_file.name

            logger.info(f"PDF export completed: {export_id} -> {file_path}")

        elif export_format == "json":
            # Export as JSON
            import json
            import tempfile

            export_data = {
                "report": report.to_dict(),
                "template": template.to_dict(),
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "exported_by": username,
            }

            with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as tmp_file:
                json.dump(export_data, tmp_file, indent=2, default=str)
                file_path = tmp_file.name

            logger.info(f"JSON export completed: {export_id} -> {file_path}")

        elif export_format == "markdown":
            # Export as Markdown
            import tempfile

            # Generate markdown content (reuse from PDF generator)
            from app.services.cob_pdf_service import COBPDFGenerator

            pdf_gen = COBPDFGenerator()
            markdown_content = pdf_gen._generate_markdown_content(report.to_dict(), template.template_config)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".md", mode="w") as tmp_file:
                tmp_file.write(markdown_content)
                file_path = tmp_file.name

            logger.info(f"Markdown export completed: {export_id} -> {file_path}")

        # TODO: Update export status in database
        # In production, save export metadata to database

    except Exception as e:
        logger.error(f"Export processing failed for {export_id}: {e}")
        # TODO: Update export status to failed in database
