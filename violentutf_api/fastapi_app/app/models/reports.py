# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Database models for report templates and generation"""

import uuid
from datetime import datetime
from typing import Optional

from app.db.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID


class ReportTemplate(Base):
    """Report template model"""

    __tablename__ = "report_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # executive, technical, compliance, etc.
    template_type = Column(String(20), nullable=False, default="custom")  # builtin or custom

    # JSON fields for flexible structure
    sections = Column(JSON, nullable=False)  # List of template sections
    requirements = Column(JSON, nullable=False, default={})  # Template requirements
    settings = Column(JSON, nullable=False, default={})  # Default settings
    tags = Column(JSON, nullable=False, default=[])  # Search tags

    # Metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=True)  # Username for custom templates

    def __repr__(self):
        return f"<ReportTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"


class GeneratedReport(Base):
    """Generated report model"""

    __tablename__ = "generated_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), nullable=False)

    # Report metadata
    title = Column(String(255), nullable=False)
    subtitle = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="pending")  # pending, generating, completed, failed
    output_format = Column(String(20), nullable=False, default="html")  # html, pdf, docx, markdown

    # Generation details
    execution_ids = Column(JSON, nullable=False)  # List of execution IDs included
    settings = Column(JSON, nullable=False)  # Settings used for generation
    file_path = Column(Text, nullable=True)  # Path to generated file
    file_size = Column(String(50), nullable=True)  # File size
    error_message = Column(Text, nullable=True)  # Error if generation failed

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_by = Column(String(255), nullable=False)  # Username who generated

    def __repr__(self):
        return f"<GeneratedReport(id={self.id}, status='{self.status}', format='{self.output_format}')>"
