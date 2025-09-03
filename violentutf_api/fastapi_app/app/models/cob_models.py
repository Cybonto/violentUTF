# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""COB Report database models"""

import uuid

from app.db.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class COBTemplate(Base):
    """COB Report template model for database storage"""

    __tablename__ = "cob_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    template_config = Column(JSON, nullable=False)  # Template structure and blocks
    ai_prompts = Column(JSON)  # AI analysis prompts configuration
    export_formats = Column(JSON, default=lambda: ["markdown", "pdf", "json"])  # Supported export formats
    tags = Column(JSON)  # Template tags for organization
    is_active = Column(Boolean, default=True)
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    # Note: COBTemplateVersion is defined in app.models.report_system.report_models
    versions = relationship(
        "app.models.report_system.report_models.COBTemplateVersion",
        back_populates="template",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "template_config": self.template_config,
            "ai_prompts": self.ai_prompts,
            "export_formats": self.export_formats,
            "tags": self.tags,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class COBSchedule(Base):
    """COB Report schedule model for database storage"""

    __tablename__ = "cob_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    frequency = Column(String(20), nullable=False)  # 'daily', 'weekly', 'monthly'
    schedule_time = Column(String(8), nullable=False)  # 'HH:MM:SS' format
    timezone = Column(String(50), default="UTC")
    days_of_week = Column(JSON)  # For weekly schedules: [1,2,3,4,5] for Mon-Fri
    day_of_month = Column(String(2))  # For monthly schedules: '01', '15', 'last'
    ai_model_config = Column(JSON)  # AI model configuration for analysis blocks
    export_config = Column(JSON)  # Export format and destination configuration
    is_active = Column(Boolean, default=True)
    next_run_at = Column(DateTime(timezone=True))
    last_run_at = Column(DateTime(timezone=True))
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "template_id": str(self.template_id),
            "name": self.name,
            "description": self.description,
            "frequency": self.frequency,
            "schedule_time": self.schedule_time,
            "timezone": self.timezone,
            "days_of_week": self.days_of_week,
            "day_of_month": self.day_of_month,
            "ai_model_config": self.ai_model_config,
            "export_config": self.export_config,
            "is_active": self.is_active,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class COBReport(Base):
    """COB Report instance model for database storage"""

    __tablename__ = "cob_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), nullable=False)
    schedule_id = Column(UUID(as_uuid=True))  # NULL for manual reports
    report_name = Column(String(255), nullable=False)
    report_period_start = Column(DateTime(timezone=True))
    report_period_end = Column(DateTime(timezone=True))
    generation_status = Column(String(50), default="generating")  # 'generating', 'completed', 'failed'
    content_blocks = Column(JSON)  # Generated content for each block
    ai_analysis_results = Column(JSON)  # Results from AI analysis blocks
    export_results = Column(JSON)  # Export status and file paths
    generation_metadata = Column(JSON)  # Metadata about generation process
    generated_by = Column(String(255))
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "template_id": str(self.template_id),
            "schedule_id": str(self.schedule_id) if self.schedule_id else None,
            "report_name": self.report_name,
            "report_period_start": self.report_period_start.isoformat() if self.report_period_start else None,
            "report_period_end": self.report_period_end.isoformat() if self.report_period_end else None,
            "generation_status": self.generation_status,
            "content_blocks": self.content_blocks,
            "ai_analysis_results": self.ai_analysis_results,
            "export_results": self.export_results,
            "generation_metadata": self.generation_metadata,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class COBScheduleExecution(Base):
    """COB Schedule execution tracking model"""

    __tablename__ = "cob_schedule_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id = Column(UUID(as_uuid=True), nullable=False)
    report_id = Column(UUID(as_uuid=True))  # NULL if execution failed before report creation
    execution_status = Column(String(50), default="started")  # 'started', 'completed', 'failed'
    execution_log = Column(JSON)  # Detailed execution log
    error_details = Column(JSON)  # Error information if failed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    execution_duration_seconds = Column(String(10))  # Duration as string to avoid precision issues

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "schedule_id": str(self.schedule_id),
            "report_id": str(self.report_id) if self.report_id else None,
            "execution_status": self.execution_status,
            "execution_log": self.execution_log,
            "error_details": self.error_details,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "execution_duration_seconds": self.execution_duration_seconds,
        }
