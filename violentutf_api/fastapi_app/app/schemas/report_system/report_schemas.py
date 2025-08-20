# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Enhanced Pydantic schemas for Advanced Dashboard Report Setup
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# Enums for constrained values
class TestingCategory(str, Enum):
    SECURITY = "Security"
    SAFETY = "Safety"
    RELIABILITY = "Reliability"
    ROBUSTNESS = "Robustness"
    COMPLIANCE = "Compliance"


class AttackCategory(str, Enum):
    PROMPT_INJECTION = "Prompt Injection"
    JAILBREAK = "Jailbreak"
    DATA_LEAKAGE = "Data Leakage"
    HALLUCINATION = "Hallucination"
    BIAS = "Bias"
    TOXICITY = "Toxicity"
    HARMFUL_CONTENT = "Harmful Content"
    PRIVACY_VIOLATION = "Privacy Violation"
    MISINFORMATION = "Misinformation"


class SeverityLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class ComplexityLevel(str, Enum):
    BASIC = "Basic"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


class ScannerType(str, Enum):
    PYRIT = "pyrit"
    GARAK = "garak"
    BOTH = "both"


class OutputFormat(str, Enum):
    PDF = "PDF"
    JSON = "JSON"
    MARKDOWN = "Markdown"
    HTML = "HTML"
    CSV = "CSV"
    EXCEL = "Excel"


# Enhanced Template Metadata
class TemplateMetadata(BaseModel):
    """Comprehensive template metadata"""

    testing_category: List[TestingCategory] = Field(default_factory=list)
    attack_categories: List[AttackCategory] = Field(default_factory=list)
    scanner_compatibility: Dict[str, List[str]] = Field(
        default_factory=dict, description="Scanner type to component list mapping"
    )
    severity_focus: List[SeverityLevel] = Field(default_factory=lambda: [SeverityLevel.CRITICAL, SeverityLevel.HIGH])
    compliance_frameworks: List[str] = Field(
        default_factory=list, description="List of compliance frameworks addressed"
    )
    complexity_level: ComplexityLevel = Field(
        default=ComplexityLevel.INTERMEDIATE, description="Template complexity indicator"
    )
    estimated_generation_time: int = Field(
        default=30, ge=1, le=300, description="Estimated report generation time in seconds"
    )
    output_formats: List[OutputFormat] = Field(default_factory=lambda: [OutputFormat.PDF, OutputFormat.JSON])
    ai_requirements: Dict[str, Any] = Field(default_factory=dict, description="AI model requirements for the template")
    usage_count: int = Field(default=0, ge=0)
    last_used: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


# Data Selection Configuration
class DateRange(BaseModel):
    """Date range for filtering"""

    start: datetime
    end: datetime

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v, info):
        if info.data.get("start") and v < info.data["start"]:
            raise ValueError("End date must be after start date")
        return v


class DataSelectionFilter(BaseModel):
    """Filters for scan data selection"""

    date_range: Optional[DateRange] = None
    models: Optional[List[str]] = Field(None, min_items=1)
    score_categories: Optional[List[str]] = Field(None, min_items=1)
    min_severity: Optional[float] = Field(None, ge=0, le=10)
    max_severity: Optional[float] = Field(None, ge=0, le=10)
    datasets: Optional[List[str]] = Field(None, min_items=1)
    scanner_types: Optional[List[ScannerType]] = None

    @model_validator(mode="after")
    def validate_severity_range(self):
        if self.min_severity is not None and self.max_severity is not None and self.min_severity > self.max_severity:
            raise ValueError("min_severity must be less than max_severity")
        return self


class DataSelection(BaseModel):
    """Complete data selection configuration"""

    source: ScannerType = Field(default=ScannerType.BOTH)
    filters: DataSelectionFilter = Field(default_factory=DataSelectionFilter)
    selection_strategy: Literal["latest", "all_matching", "time_window", "custom"] = "latest"
    limit: Optional[int] = Field(None, ge=1, le=1000)


# Notification Configuration
class EmailNotification(BaseModel):
    """Email notification settings"""

    enabled: bool = False
    recipients: List[str] = Field(default_factory=list)
    on_success: bool = True
    on_failure: bool = True
    include_report: bool = True

    @field_validator("recipients")
    @classmethod
    def validate_email(cls, v):
        if not v:
            return v
        validated = []
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        for email in v:
            if not re.match(email_pattern, email):
                raise ValueError(f"Invalid email format: {email}")
            validated.append(email.lower())
        return validated


class WebhookNotification(BaseModel):
    """Webhook notification settings"""

    enabled: bool = False
    url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    retry_count: int = Field(default=3, ge=0, le=5)
    timeout: int = Field(default=30, ge=5, le=300)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class NotificationConfig(BaseModel):
    """Complete notification configuration"""

    email: EmailNotification = Field(default_factory=EmailNotification)
    webhook: WebhookNotification = Field(default_factory=WebhookNotification)
    slack: Optional[Dict[str, Any]] = None  # For future expansion


# Block Configuration
class BlockConfiguration(BaseModel):
    """Base block configuration"""

    id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    type: str
    title: str = Field(..., min_length=1, max_length=255)
    configuration: Dict[str, Any] = Field(default_factory=dict)
    order: Optional[int] = None
    enabled: bool = True


# Enhanced Template Schemas
class COBTemplateBase(BaseModel):
    """Base template schema"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    config: Dict[str, Any]
    metadata: TemplateMetadata = Field(default_factory=TemplateMetadata)
    is_active: bool = True


class COBTemplateCreate(COBTemplateBase):
    """Schema for creating a template"""

    version: str = Field("1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    version_notes: Optional[str] = None


class COBTemplateUpdate(BaseModel):
    """Schema for updating a template"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[TemplateMetadata] = None
    is_active: Optional[bool] = None


class COBTemplateResponse(COBTemplateBase):
    """Template response schema"""

    id: str
    version: str
    version_notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: Optional[str]

    class Config:
        orm_mode = True


# Template Version Schema
class TemplateVersionCreate(BaseModel):
    """Create a new template version"""

    version_type: Literal["patch", "minor", "major"]
    change_notes: str = Field(..., min_length=10, max_length=1000)


class TemplateVersionResponse(BaseModel):
    """Template version response"""

    id: str
    template_id: str
    version: str
    change_notes: Optional[str]
    snapshot: Dict[str, Any]
    created_by: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


# Enhanced Schedule Schema
class COBScheduleCreate(BaseModel):
    """Create a new schedule"""

    name: str = Field(..., min_length=1, max_length=255)
    template_id: str
    frequency: Literal["daily", "weekly", "monthly", "custom"]
    frequency_config: Dict[str, Any]
    target_config: Dict[str, Any]  # Model/endpoint configuration
    data_selection: DataSelection = Field(default_factory=DataSelection)
    notification_config: NotificationConfig = Field(default_factory=NotificationConfig)
    timezone: str = Field("UTC", pattern=r"^[A-Za-z]+/[A-Za-z_]+$")
    is_active: bool = True


class COBScheduleUpdate(BaseModel):
    """Update a schedule"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    frequency: Optional[Literal["daily", "weekly", "monthly", "custom"]]
    frequency_config: Optional[Dict[str, Any]]
    target_config: Optional[Dict[str, Any]]
    data_selection: Optional[DataSelection]
    notification_config: Optional[NotificationConfig]
    timezone: Optional[str] = Field(None, pattern=r"^[A-Za-z]+/[A-Za-z_]+$")
    is_active: Optional[bool]


# Scan Data Schemas
class ScanDataCache(BaseModel):
    """Scan data cache entry"""

    execution_id: str
    scanner_type: ScannerType
    target_model: str
    scan_date: datetime
    score_data: Dict[str, Any]
    raw_results: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        orm_mode = True


class ScanResultSummary(BaseModel):
    """Summary of a scan result"""

    execution_id: str
    scanner_type: str
    target_model: str
    scan_date: datetime
    total_tests: int = Field(ge=0)
    score_summary: Dict[str, float]
    key_findings: List[str] = Field(default_factory=list)
    severity_distribution: Dict[str, int]
    dataset_info: Optional[Dict[str, Any]] = None


# Report Variable Schema
class ReportVariableResponse(BaseModel):
    """Report variable information"""

    category: str
    variable_name: str
    description: str
    data_type: Literal["string", "number", "array", "object", "boolean"]
    source: str
    example_value: str
    is_active: bool = True

    class Config:
        orm_mode = True


# Block Definition Schema
class BlockDefinitionResponse(BaseModel):
    """Block definition information"""

    block_type: str
    display_name: str
    description: str
    category: Literal["summary", "analysis", "visualization", "metrics", "content", "custom"]
    configuration_schema: Dict[str, Any]
    default_config: Dict[str, Any]
    supported_formats: List[str]
    is_active: bool = True

    class Config:
        orm_mode = True


# Template Recommendation Schema
class TemplateRecommendation(BaseModel):
    """Template recommendation based on scan data"""

    template_id: str
    template_name: str
    description: Optional[str]
    match_score: float = Field(ge=0, le=1)
    match_reasons: List[str]
    metadata: TemplateMetadata
    compatibility_details: Dict[str, Any] = Field(default_factory=dict)


# Data Browse Request/Response
class DataBrowseRequest(BaseModel):
    """Request for browsing scan data"""

    scanner_type: Optional[ScannerType] = None
    date_range: Optional[DateRange] = None
    model_filter: Optional[List[str]] = None
    score_category_filter: Optional[List[str]] = None
    severity_filter: Optional[List[SeverityLevel]] = None
    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)
    sort_by: Literal["date", "severity", "model", "scanner"] = "date"
    sort_order: Literal["asc", "desc"] = "desc"


class DataBrowseResponse(BaseModel):
    """Response for data browse request"""

    results: List[ScanResultSummary]
    total_count: int
    has_more: bool
    filters_applied: Dict[str, Any]
    aggregations: Optional[Dict[str, Any]] = None


# Report Generation Request/Response
class ReportGenerationRequest(BaseModel):
    """Request to generate a report"""

    template_id: str
    scan_data_ids: List[str] = Field(..., min_items=1)
    output_formats: List[OutputFormat] = Field(default_factory=lambda: [OutputFormat.PDF, OutputFormat.JSON])
    configuration_overrides: Optional[Dict[str, Any]] = None
    preview_mode: bool = False
    report_name: Optional[str] = Field(None, max_length=255)
    priority: Literal["low", "normal", "high"] = "normal"


class ReportGenerationResponse(BaseModel):
    """Response for report generation request"""

    report_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    estimated_time: int  # seconds
    preview_mode: bool
    queue_position: Optional[int] = None
    created_at: datetime


# Real-time Preview Request/Response
class PreviewRequest(BaseModel):
    """Request for template preview"""

    template_config: Dict[str, Any]
    sample_data: Dict[str, Any]
    block_id: Optional[str] = None  # Preview specific block only
    output_format: OutputFormat = OutputFormat.HTML


class PreviewResponse(BaseModel):
    """Preview generation response"""

    html_content: Optional[str] = None
    markdown_content: Optional[str] = None
    estimated_pages: int = Field(ge=1)
    warnings: List[str] = Field(default_factory=list)
    processing_time: float  # seconds


# Report Status
class ReportStatus(BaseModel):
    """Report generation status"""

    report_id: str
    status: Literal["pending", "processing", "completed", "failed", "cancelled"]
    progress: int = Field(ge=0, le=100)
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    outputs: Optional[Dict[str, Dict[str, Any]]] = None
    completed_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# Batch Operations
class BatchReportRequest(BaseModel):
    """Request for batch report generation"""

    template_id: str
    scan_data_groups: List[List[str]]  # List of scan ID groups
    output_formats: List[OutputFormat]
    batch_name: Optional[str] = None
    parallel_execution: bool = True
    max_parallel: int = Field(5, ge=1, le=20)
