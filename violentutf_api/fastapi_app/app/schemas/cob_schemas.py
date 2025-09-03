# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""COB Report Pydantic schemas for API validation"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.validation import SecurityLimits
from pydantic import BaseModel, Field


# Template Schemas
class COBTemplateCreate(BaseModel):
    """Schema for creating COB template"""

    name: str = Field(
        ..., min_length=3, max_length=SecurityLimits.MAX_NAME_LENGTH, description="Unique name for the template"
    )
    description: Optional[str] = Field(
        None, max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH, description="Description of the template"
    )
    template_config: Dict[str, Any] = Field(..., description="Template structure and blocks configuration")
    ai_prompts: Optional[Dict[str, Any]] = Field(None, description="AI analysis prompts configuration")
    export_formats: Optional[List[str]] = Field(
        default=["markdown", "pdf", "json"], description="Supported export formats"
    )
    tags: Optional[List[str]] = Field(None, description="Tags for template organization")


class COBTemplateUpdate(BaseModel):
    """Schema for updating COB template"""

    name: Optional[str] = Field(
        None, min_length=3, max_length=SecurityLimits.MAX_NAME_LENGTH, description="Unique name for the template"
    )
    description: Optional[str] = Field(
        None, max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH, description="Description of the template"
    )
    template_config: Optional[Dict[str, Any]] = Field(None, description="Template structure and blocks configuration")
    ai_prompts: Optional[Dict[str, Any]] = Field(None, description="AI analysis prompts configuration")
    export_formats: Optional[List[str]] = Field(None, description="Supported export formats")
    tags: Optional[List[str]] = Field(None, description="Tags for template organization")
    is_active: Optional[bool] = Field(None, description="Whether template is active")


class COBTemplateResponse(BaseModel):
    """Schema for COB template response"""

    id: UUID
    name: str
    description: Optional[str]
    template_config: Dict[str, Any]
    ai_prompts: Optional[Dict[str, Any]]
    export_formats: List[str]
    tags: Optional[List[str]]
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: datetime
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


# Schedule Schemas
class COBScheduleCreate(BaseModel):
    """Schema for creating COB schedule"""

    template_id: UUID = Field(..., description="Template to use for scheduled reports")
    name: str = Field(..., min_length=3, max_length=SecurityLimits.MAX_NAME_LENGTH, description="Name for the schedule")
    description: Optional[str] = Field(
        None, max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH, description="Description of the schedule"
    )
    frequency: str = Field(..., description="Schedule frequency: daily, weekly, monthly")
    schedule_time: str = Field(..., description="Time to run in HH:MM:SS format")
    timezone: Optional[str] = Field(default="UTC", description="Timezone for schedule")
    days_of_week: Optional[List[int]] = Field(None, description="Days of week for weekly schedules (1=Monday)")
    day_of_month: Optional[str] = Field(None, description="Day of month for monthly schedules")
    ai_model_config: Optional[Dict[str, Any]] = Field(None, description="AI model configuration")
    export_config: Optional[Dict[str, Any]] = Field(None, description="Export configuration")


class COBScheduleUpdate(BaseModel):
    """Schema for updating COB schedule"""

    template_id: Optional[UUID] = Field(None, description="Template to use for scheduled reports")
    name: Optional[str] = Field(
        None, min_length=3, max_length=SecurityLimits.MAX_NAME_LENGTH, description="Name for the schedule"
    )
    description: Optional[str] = Field(
        None, max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH, description="Description of the schedule"
    )
    frequency: Optional[str] = Field(None, description="Schedule frequency: daily, weekly, monthly")
    schedule_time: Optional[str] = Field(None, description="Time to run in HH:MM:SS format")
    timezone: Optional[str] = Field(None, description="Timezone for schedule")
    days_of_week: Optional[List[int]] = Field(None, description="Days of week for weekly schedules")
    day_of_month: Optional[str] = Field(None, description="Day of month for monthly schedules")
    ai_model_config: Optional[Dict[str, Any]] = Field(None, description="AI model configuration")
    export_config: Optional[Dict[str, Any]] = Field(None, description="Export configuration")
    is_active: Optional[bool] = Field(None, description="Whether schedule is active")


class COBScheduleResponse(BaseModel):
    """Schema for COB schedule response"""

    id: UUID
    template_id: UUID
    name: str
    description: Optional[str]
    frequency: str
    schedule_time: str
    timezone: str
    days_of_week: Optional[List[int]]
    day_of_month: Optional[str]
    ai_model_config: Optional[Dict[str, Any]]
    export_config: Optional[Dict[str, Any]]
    is_active: bool
    next_run_at: Optional[datetime]
    last_run_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


# Report Schemas
class COBReportCreate(BaseModel):
    """Schema for creating COB report (manual generation)"""

    template_id: UUID = Field(..., description="Template to use for report generation")
    report_name: str = Field(
        ..., min_length=3, max_length=SecurityLimits.MAX_NAME_LENGTH, description="Name for the generated report"
    )
    report_period_start: Optional[datetime] = Field(None, description="Start of reporting period")
    report_period_end: Optional[datetime] = Field(None, description="End of reporting period")
    export_formats: Optional[List[str]] = Field(default=["markdown"], description="Export formats to generate")
    ai_model_config: Optional[Dict[str, Any]] = Field(None, description="Override AI model configuration")


class COBReportResponse(BaseModel):
    """Schema for COB report response"""

    id: UUID
    template_id: UUID
    schedule_id: Optional[UUID]
    report_name: str
    report_period_start: Optional[datetime]
    report_period_end: Optional[datetime]
    generation_status: str
    content_blocks: Optional[Dict[str, Any]]
    ai_analysis_results: Optional[Dict[str, Any]]
    export_results: Optional[Dict[str, Any]]
    generation_metadata: Optional[Dict[str, Any]]
    generated_by: str
    generated_at: datetime
    completed_at: Optional[datetime]
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


# Schedule Execution Schemas
class COBScheduleExecutionResponse(BaseModel):
    """Schema for COB schedule execution response"""

    id: UUID
    schedule_id: UUID
    report_id: Optional[UUID]
    execution_status: str
    execution_log: Optional[Dict[str, Any]]
    error_details: Optional[Dict[str, Any]]
    started_at: datetime
    completed_at: Optional[datetime]
    execution_duration_seconds: Optional[str]
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


# List Response Schemas
class COBTemplateListResponse(BaseModel):
    """Schema for listing COB templates"""

    templates: List[COBTemplateResponse]
    total: int
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


class COBScheduleListResponse(BaseModel):
    """Schema for listing COB schedules"""

    schedules: List[COBScheduleResponse]
    total: int
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


class COBReportListResponse(BaseModel):
    """Schema for listing COB reports"""

    reports: List[COBReportResponse]
    total: int
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


class COBScheduleExecutionListResponse(BaseModel):
    """Schema for listing COB schedule executions"""

    executions: List[COBScheduleExecutionResponse]
    total: int
    links: Dict[str, str] = Field(default_factory=dict, description="HATEOAS navigation links")


# Status and Health Check Schemas
class COBSystemStatusResponse(BaseModel):
    """Schema for COB system status"""

    active_templates: int
    active_schedules: int
    pending_executions: int
    last_execution_time: Optional[datetime]
    next_scheduled_execution: Optional[datetime]
    system_health: str = Field(..., description="overall, healthy, degraded, unhealthy")


# Export Related Schemas
class COBExportRequest(BaseModel):
    """Schema for manual report export request"""

    report_id: UUID = Field(..., description="Report ID to export")
    export_format: str = Field(..., description="Export format: markdown, pdf, json")
    export_options: Optional[Dict[str, Any]] = Field(None, description="Export-specific options")


class COBExportResponse(BaseModel):
    """Schema for export response"""

    export_id: str
    report_id: UUID
    export_format: str
    export_status: str = Field(..., description="pending, completed, failed")
    file_path: Optional[str] = Field(None, description="Path to exported file")
    download_url: Optional[str] = Field(None, description="URL to download exported file")
    error_message: Optional[str] = Field(None, description="Error message if export failed")
    created_at: datetime
