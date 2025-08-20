# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Schemas for report generation and templates"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateSection(BaseModel):
    """A section within a report template"""

    id: str = Field(..., description="Section identifier")
    title: str = Field(..., description="Section title")
    description: Optional[str] = Field(None, description="Section description")
    required: bool = Field(True, description="Whether this section is required")
    order: int = Field(..., description="Display order")
    components: List[str] = Field(default_factory=list, description="Components in this section")


class TemplateRequirements(BaseModel):
    """Requirements for using a template"""

    min_executions: int = Field(1, description="Minimum number of executions needed")
    max_executions: Optional[int] = Field(None, description="Maximum number of executions supported")
    needs_severity_data: bool = Field(False, description="Requires severity distribution data")
    needs_prompt_response: bool = Field(False, description="Requires prompt/response data")
    needs_full_evidence: bool = Field(False, description="Requires full evidence data")
    required_score_types: List[str] = Field(default_factory=list, description="Required score types")
    required_orchestrators: List[str] = Field(default_factory=list, description="Required orchestrator types")


class TemplateSettings(BaseModel):
    """Configurable settings for a template"""

    include_executive_summary: bool = Field(True, description="Include executive summary")
    include_technical_details: bool = Field(True, description="Include technical details")
    include_evidence: bool = Field(True, description="Include evidence/examples")
    evidence_limit: int = Field(10, description="Maximum evidence items per finding")
    group_by: str = Field("severity", description="Group findings by: severity, category, generator")
    include_recommendations: bool = Field(True, description="Include recommendations")
    include_appendix: bool = Field(False, description="Include appendix")
    custom_branding: Optional[Dict[str, Any]] = Field(None, description="Custom branding options")


class ReportTemplateBase(BaseModel):
    """Base fields for report templates"""

    name: str = Field(..., description="Template name", min_length=1, max_length=100)
    description: str = Field(..., description="Template description", max_length=500)
    category: str = Field(
        ...,
        description="Template category",
        pattern="^(executive|technical|compliance|vulnerability|redteam|custom)$",
    )
    template_type: str = Field("custom", description="Template type", pattern="^(builtin|custom)$")
    tags: List[str] = Field(default_factory=list, description="Template tags for search")
    is_active: bool = Field(True, description="Whether template is active")


class ReportTemplateCreate(ReportTemplateBase):
    """Schema for creating a report template"""

    sections: List[TemplateSection] = Field(..., description="Template sections")
    requirements: TemplateRequirements = Field(
        default_factory=TemplateRequirements, description="Template requirements"
    )
    settings: TemplateSettings = Field(default_factory=TemplateSettings, description="Default settings")


class ReportTemplateUpdate(BaseModel):
    """Schema for updating a report template"""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, pattern="^(executive|technical|compliance|vulnerability|redteam|custom)$")
    tags: Optional[List[str]] = None
    sections: Optional[List[TemplateSection]] = None
    requirements: Optional[TemplateRequirements] = None
    settings: Optional[TemplateSettings] = None
    is_active: Optional[bool] = None


class ReportTemplate(ReportTemplateBase):
    """Complete report template"""

    id: UUID = Field(..., description="Template ID")
    sections: List[TemplateSection] = Field(..., description="Template sections")
    requirements: TemplateRequirements = Field(..., description="Template requirements")
    settings: TemplateSettings = Field(..., description="Default settings")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: Optional[str] = Field(None, description="Username who created the template")

    class Config:
        orm_mode = True


class TemplateSummary(BaseModel):
    """Summary view of a template for listing"""

    id: UUID = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category")
    template_type: str = Field(..., description="Template type")
    tags: List[str] = Field(default_factory=list, description="Template tags")
    is_active: bool = Field(..., description="Whether template is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    section_count: int = Field(..., description="Number of sections")
    is_compatible: Optional[bool] = Field(None, description="Compatible with selected data")
    compatibility_notes: Optional[List[str]] = Field(None, description="Compatibility issues if any")


class TemplateListRequest(BaseModel):
    """Request for listing templates"""

    category: Optional[str] = Field(None, description="Filter by category")
    search: Optional[str] = Field(None, description="Search in name and description")
    template_type: Optional[str] = Field(None, description="Filter by template type")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    include_inactive: bool = Field(False, description="Include inactive templates")
    check_compatibility: bool = Field(False, description="Check compatibility with execution IDs")
    execution_ids: Optional[List[UUID]] = Field(None, description="Execution IDs to check compatibility")
    sort_by: str = Field("name", description="Sort field", pattern="^(name|category|created_at|updated_at)$")
    sort_order: str = Field("asc", description="Sort order", pattern="^(asc|desc)$")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class TemplateListResponse(BaseModel):
    """Response for template listing"""

    templates: List[TemplateSummary] = Field(..., description="List of templates")
    total_count: int = Field(..., description="Total number of templates")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")


class TemplatePreviewRequest(BaseModel):
    """Request for template preview"""

    template_id: UUID = Field(..., description="Template ID to preview")
    execution_ids: List[UUID] = Field(..., description="Selected execution IDs")
    settings_override: Optional[TemplateSettings] = Field(None, description="Override default settings")


class TemplatePreviewResponse(BaseModel):
    """Response for template preview"""

    template_name: str = Field(..., description="Template name")
    estimated_sections: int = Field(..., description="Estimated number of sections")
    estimated_pages: int = Field(..., description="Estimated page count")
    outline: List[Dict[str, Any]] = Field(..., description="Report outline")
    data_coverage: Dict[str, bool] = Field(..., description="Data availability for each section")
    warnings: List[str] = Field(default_factory=list, description="Any warnings or limitations")


class ReportGenerationRequest(BaseModel):
    """Request to generate a report"""

    template_id: UUID = Field(..., description="Template ID to use")
    execution_ids: List[UUID] = Field(..., description="Execution IDs to include")
    settings: TemplateSettings = Field(..., description="Report settings")
    output_format: str = Field("html", description="Output format", pattern="^(html|pdf|docx|markdown)$")
    report_title: Optional[str] = Field(None, description="Custom report title")
    report_subtitle: Optional[str] = Field(None, description="Custom report subtitle")


class ReportGenerationResponse(BaseModel):
    """Response for report generation"""

    report_id: UUID = Field(..., description="Generated report ID")
    status: str = Field(..., description="Generation status")
    message: str = Field(..., description="Status message")
    estimated_time: Optional[int] = Field(None, description="Estimated completion time in seconds")
    download_url: Optional[str] = Field(None, description="URL to download completed report")
