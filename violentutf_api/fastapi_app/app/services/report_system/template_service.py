# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""Template management service for report system"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.cob_models import COBTemplate
from app.models.report_system.report_models import COBTemplateVersion
from app.schemas.report_system.report_schemas import (
    COBTemplateCreate,
    COBTemplateResponse,
    COBTemplateUpdate,
    TemplateRecommendation,
    TemplateVersionResponse,
)

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for managing report templates"""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize TemplateService."""
        self.db = db

    def _template_to_response(self, template: COBTemplate) -> COBTemplateResponse:
        """Convert COBTemplate model to response schema"""
        # Extract metadata from template_config
        metadata = template.template_config.get("metadata", {})
        config = template.template_config.copy()
        config.pop("metadata", None)  # Remove metadata from config

        # Build response data
        response_data = {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
            "config": config,
            "metadata": metadata,  # Return full metadata as-is
            "is_active": template.is_active,
            "version": "1.0.0",  # Default version
            "version_notes": None,  # Optional field
            "created_at": template.created_at,
            "updated_at": template.updated_at,
            "created_by": template.created_by,
        }

        return COBTemplateResponse(**response_data)

    async def create_template(self, template_data: COBTemplateCreate, user_id: str) -> COBTemplateResponse:
        """Create a new template"""
        # Create template model
        # Store extended metadata in template_config
        template_config = (
            template_data.config.copy() if hasattr(template_data, "config") and template_data.config else {}
        )

        # Extract metadata from the template_data
        if hasattr(template_data, "metadata") and template_data.metadata:
            # Convert metadata object to dict
            metadata_dict = template_data.metadata.dict() if hasattr(template_data.metadata, "dict") else {}
            template_config["metadata"] = metadata_dict
        else:
            template_config["metadata"] = {}

        template = COBTemplate(
            name=template_data.name,
            description=template_data.description,
            template_config=template_config,
            export_formats=["markdown", "pdf", "json"],  # Default formats
            tags=(
                template_data.metadata.tags
                if hasattr(template_data, "metadata") and hasattr(template_data.metadata, "tags")
                else []
            ),
            ai_prompts={},  # Empty for now
            created_by=user_id,
        )

        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        # Create initial version
        await self._create_version(template.id, "1.0.0", template.template_config, "Initial version", user_id)

        return self._template_to_response(template)

    async def get_template(self, template_id: str) -> COBTemplateResponse:
        """Get a template by ID"""
        # Convert string ID to UUID
        try:
            template_uuid = uuid.UUID(template_id) if isinstance(template_id, str) else template_id
        except ValueError as exc:
            raise ValueError(f"Invalid template ID format: {template_id}") from exc

        stmt = select(COBTemplate).where(COBTemplate.id == template_uuid)
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        return self._template_to_response(template)

    async def list_templates(
        self,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[COBTemplateResponse], int]:
        """List templates with filtering and pagination"""
        # Base query
        stmt = select(COBTemplate)

        # Apply database-level filters
        if filters and "is_active" in filters:
            stmt = stmt.where(COBTemplate.is_active == filters["is_active"])

        # Apply sorting
        sort_column = getattr(COBTemplate, sort_by, COBTemplate.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Execute query to get all matching templates
        result = await self.db.execute(stmt)
        all_templates = result.scalars().all()

        logger.info("Query returned %s templates from database", len(all_templates))

        # Apply JSON metadata filters in Python
        filtered_templates = []
        for template in all_templates:
            metadata = template.template_config.get("metadata", {})

            # Check filters
            if filters:
                # Testing categories filter
                if "testing_categories" in filters:
                    template_cats = metadata.get("testing_categories", [])
                    if not any(cat in template_cats for cat in filters["testing_categories"]):
                        continue

                # Attack categories filter
                if "attack_categories" in filters:
                    template_attacks = metadata.get("attack_categories", [])
                    if not any(cat in template_attacks for cat in filters["attack_categories"]):
                        continue

                # Scanner type filter
                if "scanner_type" in filters:
                    if metadata.get("scanner_type") != filters["scanner_type"]:
                        continue

                # Complexity level filter
                if "complexity_level" in filters:
                    if metadata.get("complexity_level", "").lower() != filters["complexity_level"].lower():
                        continue

            filtered_templates.append(template)

        # Get total count after filtering
        total = len(filtered_templates)

        # Apply pagination
        paginated_templates = filtered_templates[skip : skip + limit]

        return [self._template_to_response(t) for t in paginated_templates], total

    async def update_template(
        self, template_id: str, template_update: COBTemplateUpdate, user_id: str, create_version: bool = True
    ) -> COBTemplateResponse:
        """Update a template"""
        # Convert string ID to UUID
        try:
            template_uuid = uuid.UUID(template_id) if isinstance(template_id, str) else template_id
        except ValueError as exc:
            raise ValueError(f"Invalid template ID format: {template_id}") from exc

        stmt = select(COBTemplate).where(COBTemplate.id == template_uuid)
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Update fields
        update_data = template_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(template, field, value)

        template.updated_at = datetime.utcnow()

        # Increment version
        if create_version:
            current_version = template.version.split(".")
            current_version[2] = str(int(current_version[2]) + 1)
            template.version = ".".join(current_version)

            # Create version record
            await self._create_version(
                template_id, template.version, template.template_config, "Updated template", user_id
            )

        await self.db.commit()
        await self.db.refresh(template)

        return self._template_to_response(template)

    async def delete_template(self, template_id: str) -> None:
        """Soft delete a template"""
        # Convert string ID to UUID
        try:
            template_uuid = uuid.UUID(template_id) if isinstance(template_id, str) else template_id
        except ValueError as exc:
            raise ValueError(f"Invalid template ID format: {template_id}") from exc

        stmt = select(COBTemplate).where(COBTemplate.id == template_uuid)
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        template.is_active = False
        template.updated_at = datetime.utcnow()

        await self.db.commit()

    async def search_templates(self, query: str) -> List[COBTemplateResponse]:
        """Search templates by name, description, or tags"""
        search_term = f"%{query}%"

        stmt = select(COBTemplate).where(
            or_(
                COBTemplate.name.ilike(search_term),
                COBTemplate.description.ilike(search_term),
                # Note: For JSON fields, might need different approach depending on DB
            )
        )

        result = await self.db.execute(stmt)
        templates = result.scalars().all()

        return [self._template_to_response(t) for t in templates]

    async def recommend_templates(self, scan_data: Dict[str, Any], limit: int = 5) -> List[TemplateRecommendation]:
        """Recommend templates based on scan data characteristics"""
        recommendations = []

        # Get all active templates
        stmt = select(COBTemplate).where(COBTemplate.is_active is True)
        result = await self.db.execute(stmt)
        templates = result.scalars().all()

        for template in templates:
            score = self._calculate_recommendation_score(template, scan_data)
            if score > 0:
                reasons = self._get_recommendation_reasons(template, scan_data)
                recommendations.append(
                    TemplateRecommendation(template=self._template_to_response(template), score=score, reasons=reasons)
                )

        # Sort by score and return top N
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:limit]

    def _calculate_recommendation_score(self, template: COBTemplate, scan_data: Dict[str, Any]) -> float:
        """Calculate recommendation score for a template"""
        score = 0.0

        # Scanner type match
        scanner_types = scan_data.get("scanner_type", [])
        if isinstance(scanner_types, str):
            scanner_types = [scanner_types]

        if template.scanner_type:
            if template.scanner_type == "both" or template.scanner_type in scanner_types:
                score += 0.3

        # Vulnerability match
        vulnerabilities = scan_data.get("vulnerabilities", [])
        if vulnerabilities:
            # Check if template categories match vulnerabilities
            vuln_categories = set(v.get("category", "").lower() for v in vulnerabilities)
            template_categories = set(cat.lower() for cat in template.attack_categories or [])

            overlap = len(vuln_categories & template_categories)
            if overlap > 0:
                score += 0.4 * (overlap / len(vuln_categories))

        # Testing focus match
        if scan_data.get("has_toxicity_data") and "toxicity" in (template.testing_categories or []):
            score += 0.2

        # Complexity match
        total_tests = scan_data.get("total_tests", 0)
        if total_tests > 1000 and template.complexity_level == "advanced":
            score += 0.1
        elif total_tests < 100 and template.complexity_level == "basic":
            score += 0.1

        return min(score, 1.0)

    def _get_recommendation_reasons(self, template: COBTemplate, scan_data: Dict[str, Any]) -> List[str]:
        """Get reasons for recommending a template"""
        reasons = []

        scanner_types = scan_data.get("scanner_type", [])
        if isinstance(scanner_types, str):
            scanner_types = [scanner_types]

        if template.scanner_type and template.scanner_type in scanner_types:
            reasons.append(f"Designed for {template.scanner_type} scanner")

        vulnerabilities = scan_data.get("vulnerabilities", [])
        if vulnerabilities:
            vuln_types = set(v.get("category", "") for v in vulnerabilities)
            matched = vuln_types & set(template.attack_categories or [])
            if matched:
                reasons.append(f"Covers vulnerability types: {', '.join(matched)}")

        if scan_data.get("has_toxicity_data") and "toxicity" in (template.testing_categories or []):
            reasons.append("Includes toxicity analysis sections")

        return reasons

    async def _create_version(
        self,
        template_id: Union[str, uuid.UUID],
        version: str,
        config: Dict[str, Any],
        change_summary: str,
        user_id: str,
    ) -> None:
        """Create a template version record"""
        # Convert string ID to UUID if needed
        template_uuid = uuid.UUID(template_id) if isinstance(template_id, str) else template_id

        version_record = COBTemplateVersion(
            template_id=template_uuid,
            version=version,
            snapshot=config,  # Use snapshot field name instead of config
            change_notes=change_summary,  # Use change_notes field name
            created_by=user_id,
        )

        self.db.add(version_record)
        await self.db.commit()

    async def get_template_versions(self, template_id: str, limit: int = 10) -> List[TemplateVersionResponse]:
        """Get version history for a template"""
        stmt = (
            select(COBTemplateVersion)
            .where(COBTemplateVersion.template_id == template_id)
            .order_by(COBTemplateVersion.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        versions = result.scalars().all()

        return [TemplateVersionResponse.model_validate(v) for v in versions]

    async def create_template_version(self, template_id: str, version_data: Dict[str, Any], user_id: str) -> None:
        """Create a new version of a template - placeholder implementation"""
        raise NotImplementedError("Template versioning functionality not yet implemented")

    async def restore_template_version(self, template_id: str, version_id: str, user_id: str) -> COBTemplateResponse:
        """Restore a template to a previous version"""
        # Get the version
        version_stmt = select(COBTemplateVersion).where(COBTemplateVersion.id == version_id)
        version_result = await self.db.execute(version_stmt)
        version = version_result.scalar_one_or_none()

        if not version:
            raise ValueError(f"Version {version_id} not found")

        # Get the template
        # Convert string ID to UUID
        try:
            template_uuid = uuid.UUID(template_id) if isinstance(template_id, str) else template_id
        except ValueError as exc:
            raise ValueError(f"Invalid template ID format: {template_id}") from exc

        template_stmt = select(COBTemplate).where(COBTemplate.id == template_uuid)
        template_result = await self.db.execute(template_stmt)
        template = template_result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Restore config
        template.template_config = version.snapshot
        template.version = version.version
        template.updated_at = datetime.utcnow()

        # Create new version record
        await self._create_version(
            template_id, template.version, template.template_config, f"Restored to version {version.version}", user_id
        )

        await self.db.commit()
        await self.db.refresh(template)

        return self._template_to_response(template)

    async def validate_template_blocks(self, template_id: str) -> Dict[str, Any]:
        """Validate all blocks in a template"""
        template = await self.get_template(template_id)

        validation_results = {"valid": True, "errors": [], "warnings": [], "block_count": 0}

        blocks = template.template_config.get("blocks", [])
        validation_results["block_count"] = len(blocks)

        for idx, block in enumerate(blocks):
            block_id = block.get("id")
            if not block_id:
                validation_results["errors"].append(f"Block {idx} missing ID")
                validation_results["valid"] = False
                continue

            # Check if block type exists
            from .block_base import block_registry

            block_instance = block_registry.get_block_class(block_id)

            if not block_instance:
                validation_results["errors"].append(f"Block type '{block_id}' not found")
                validation_results["valid"] = False
                continue

            # Validate required variables
            variables = block.get("variables", {})
            missing = block_instance.validate_variables(variables)

            if missing:
                validation_results["warnings"].append(f"Block '{block_id}' missing variables: {', '.join(missing)}")

        return validation_results

    async def get_template_variables(self, template_id: str) -> List[str]:
        """Get all variables required by a template"""
        template = await self.get_template(template_id)

        all_variables = set()
        blocks = template.template_config.get("blocks", [])

        for block in blocks:
            block_id = block.get("id")
            if block_id:
                from .block_base import block_registry

                block_instance = block_registry.get_block_class(block_id)

                if block_instance:
                    all_variables.update(block_instance.required_variables)
                    all_variables.update(block_instance.optional_variables)

        return sorted(list(all_variables))


def get_initial_templates() -> List[Dict[str, Any]]:
    """Get initial system templates"""
    return [
        {
            "name": "Security Assessment Report",
            "description": "Comprehensive security assessment report for AI models",
            "config": {
                "blocks": [
                    {
                        "block_type": "title",
                        "config": {
                            "title": "Security Assessment Report",
                            "subtitle": "AI Model Vulnerability Analysis",
                        },
                    },
                    {"block_type": "executive_summary", "config": {}},
                    {"block_type": "findings_by_severity", "config": {"include_evidence": True}},
                    {"block_type": "recommendations", "config": {"group_by": "severity"}},
                ]
            },
            "metadata": {
                "testing_categories": ["Security", "Robustness"],
                "attack_categories": ["Prompt Injection", "Jailbreak", "Data Leakage"],
                "scanner_type": "both",
                "scanner_compatibility": {"pyrit": ["all"], "garak": ["all"]},
                "severity_focus": ["Critical", "High"],
                "compliance_frameworks": [],
                "complexity_level": "Intermediate",
                "estimated_generation_time": 300,
                "required_data_fields": ["score_value", "score_rationale", "text_scored"],
                "tags": ["security", "vulnerability", "assessment"],
                "is_system": True,
            },
            "is_active": True,
        },
        {
            "name": "Compliance Report",
            "description": "AI model compliance and safety evaluation report",
            "config": {
                "blocks": [
                    {
                        "block_type": "title",
                        "config": {"title": "Compliance Report", "subtitle": "Safety and Regulatory Assessment"},
                    },
                    {"block_type": "executive_summary", "config": {}},
                    {"block_type": "metrics", "config": {"metrics": ["safety_score", "bias_score", "toxicity_score"]}},
                    {"block_type": "compliance_checklist", "config": {}},
                ]
            },
            "metadata": {
                "testing_categories": ["Compliance", "Safety"],
                "attack_categories": ["Bias", "Toxicity", "Harmful Content"],
                "scanner_type": "both",
                "scanner_compatibility": {"pyrit": ["all"], "garak": ["all"]},
                "severity_focus": ["High", "Medium"],
                "compliance_frameworks": ["AI Act", "NIST AI RMF"],
                "complexity_level": "Advanced",
                "estimated_generation_time": 300,
                "required_data_fields": ["score_value", "score_category", "score_rationale"],
                "tags": ["compliance", "safety", "regulatory"],
                "is_system": True,
            },
            "is_active": True,
        },
    ]
