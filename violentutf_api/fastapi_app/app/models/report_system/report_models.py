# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Extended database models for advanced report features"""

import uuid
from typing import Any, Dict

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base

# Note: COBTemplate extensions (metadata, version fields) should be added directly to COBTemplate model if needed


class COBTemplateVersion(Base):
    """Template version history"""

    __tablename__ = "cob_template_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id = Column(UUID(as_uuid=True), ForeignKey("cob_templates.id"), nullable=False)
    version = Column(String(20), nullable=False)
    change_notes = Column(Text)
    snapshot = Column(JSON, nullable=False)  # Complete template state at this version
    created_by = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    template = relationship("COBTemplate", back_populates="versions")


# Note: COBSchedule extensions (data_selection, notification_config) should be added
# directly to COBSchedule model if needed


class COBScanDataCache(Base):
    """Cache for scan data used in reports"""

    __tablename__ = "cob_scan_data_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(String, unique=True, index=True)
    scanner_type = Column(String(50), index=True)  # pyrit, garak
    target_model = Column(String(255))
    scan_date = Column(DateTime)
    score_data = Column(JSON)  # Aggregated scores and metrics
    raw_results = Column(JSON)  # Full scan results (optional)
    scan_metadata = Column(JSON)  # Additional context (renamed from metadata)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, index=True)  # For cache cleanup

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "scanner_type": self.scanner_type,
            "target_model": self.target_model,
            "scan_date": self.scan_date.isoformat() if self.scan_date else None,
            "score_data": self.score_data,
            "metadata": self.scan_metadata,  # Keep API compatibility
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class COBReportVariable(Base):
    """Registry of available report variables"""

    __tablename__ = "cob_report_variables"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category = Column(String(100), index=True)  # scan_results, model_info, metrics, etc.
    variable_name = Column(String(255), unique=True)
    description = Column(Text)
    data_type = Column(String(50))  # string, number, array, object
    source = Column(String(50))  # pyrit, garak, system, custom
    example_value = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "category": self.category,
            "variable_name": self.variable_name,
            "description": self.description,
            "data_type": self.data_type,
            "source": self.source,
            "example_value": self.example_value,
            "is_active": self.is_active,
        }


class COBBlockDefinition(Base):
    """Block type definitions"""

    __tablename__ = "cob_block_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    block_type = Column(String(100), unique=True)
    display_name = Column(String(255))
    description = Column(Text)
    category = Column(String(100), index=True)  # analysis, metrics, visualization, custom
    configuration_schema = Column(JSON)  # JSON schema for block config
    default_config = Column(JSON)
    supported_formats = Column(JSON, default=["PDF", "JSON", "Markdown"])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "block_type": self.block_type,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "configuration_schema": self.configuration_schema,
            "default_config": self.default_config,
            "supported_formats": self.supported_formats,
            "is_active": self.is_active,
        }


# Note: COBReport extensions (progress, generation_metadata, error_message) should be added
# directly to COBReport model if needed
