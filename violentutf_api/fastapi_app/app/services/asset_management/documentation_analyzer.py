# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Documentation Gap Analyzer for Issue #281

This module implements algorithms to detect missing, outdated, or
inconsistent documentation across database assets.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.models.gap_analysis import (
    DocumentationGap,
    DocumentationType,
    GapSeverity,
    GapType,
    QualityIssue,
    SchemaDocumentationGap,
)

logger = logging.getLogger(__name__)


class DocumentationGapAnalyzer:
    """Analyzer for documentation gaps across database assets."""

    def __init__(self, documentation_service: Optional[object], asset_service: Optional[object] = None) -> None:
        """Initialize the documentation gap analyzer.

        Args:
            documentation_service: Service for accessing documentation
            asset_service: Service for accessing asset inventory
        """
        self.documentation_service = documentation_service
        self.asset_service = asset_service
        self.required_docs = self._load_documentation_requirements()

    def _load_documentation_requirements(self) -> Dict[str, Any]:
        """Load documentation requirements configuration.

        Returns:
            Dictionary of documentation requirements by asset type/classification
        """
        return {
            "templates": {
                "basic_info": {
                    "required_sections": ["overview", "purpose", "owner"],
                    "required_fields": ["name", "description", "owner_team", "technical_contact"],
                },
                "technical_specs": {
                    "required_sections": ["architecture", "connection_info", "schema"],
                    "required_fields": ["connection_details", "schema_documentation", "dependencies"],
                },
                "security_procedures": {
                    "required_sections": ["access_controls", "data_classification", "compliance"],
                    "required_fields": ["access_matrix", "data_sensitivity", "compliance_frameworks"],
                },
            },
            "freshness_thresholds": {"critical_assets": 60, "production_assets": 90, "general_assets": 120},  # days
        }

    async def analyze_documentation_gaps(self) -> List[DocumentationGap]:
        """Analyze documentation gaps across all assets.

        Returns:
            List of documentation gaps identified
        """
        logger.info("Starting documentation gap analysis")
        start_time = datetime.now()

        try:
            # Get all assets for analysis
            if self.asset_service:
                assets = await self.asset_service.get_all_assets()
            else:
                # Fallback if asset service not available
                logger.warning("Asset service not available, using mock data")
                assets = []

            logger.info("Analyzing documentation for %d assets", len(assets))

            all_gaps = []

            # Process assets concurrently for performance
            semaphore = asyncio.Semaphore(10)  # Limit concurrent processing
            tasks = [self._analyze_asset_documentation(asset, semaphore) for asset in assets]
            asset_results = await asyncio.gather(*tasks, return_exceptions=True)

            for asset, result in zip(assets, asset_results):
                if isinstance(result, Exception):
                    logger.warning("Error analyzing documentation for asset %s: %s", asset.id, str(result))
                    continue

                if result:
                    all_gaps.extend(result)

            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info("Documentation gap analysis completed in %.2fs, found %d gaps", execution_time, len(all_gaps))

            return all_gaps

        except Exception as e:
            logger.error("Error in documentation gap analysis: %s", str(e))
            raise

    async def _analyze_asset_documentation(
        self, asset: DatabaseAsset, semaphore: asyncio.Semaphore
    ) -> List[DocumentationGap]:
        """Analyze documentation for a single asset.

        Args:
            asset: Asset to analyze
            semaphore: Concurrency limiter

        Returns:
            List of documentation gaps for this asset
        """
        async with semaphore:
            gaps = []

            try:
                # Get required documentation types for this asset
                required_docs = self.get_required_documentation(asset)

                for doc_type in required_docs:
                    # Check if documentation exists
                    existing_doc = await self.documentation_service.find_documentation(asset.id, doc_type)

                    if not existing_doc:
                        # Missing documentation gap
                        gap = DocumentationGap(
                            asset_id=asset.id,
                            gap_type=GapType.MISSING_DOCUMENTATION,
                            documentation_type=doc_type,
                            severity=self.calculate_missing_doc_severity(asset, doc_type),
                            description=f"Missing {doc_type.value} documentation for {asset.name}",
                            recommendations=self.generate_doc_creation_recommendations(asset, doc_type),
                        )
                        gaps.append(gap)
                    else:
                        # Check documentation quality and freshness
                        quality_issues = await self.assess_documentation_quality(existing_doc, asset)
                        for issue in quality_issues:
                            gap = DocumentationGap(
                                asset_id=asset.id,
                                gap_type=GapType.OUTDATED_DOCUMENTATION,
                                documentation_type=doc_type,
                                severity=issue.severity,
                                description=issue.description,
                                recommendations=issue.recommendations,
                                last_updated=existing_doc.last_updated,
                                completeness_score=getattr(existing_doc, "completeness_score", None),
                                quality_issues=[issue.description],
                            )
                            gaps.append(gap)

            except Exception as e:
                logger.warning("Error analyzing documentation for asset %s: %s", asset.id, str(e))

            return gaps

    def get_required_documentation(self, asset: DatabaseAsset) -> List[DocumentationType]:
        """Get required documentation types based on asset characteristics.

        Args:
            asset: Asset to determine requirements for

        Returns:
            List of required documentation types
        """
        required = [DocumentationType.BASIC_INFO, DocumentationType.TECHNICAL_SPECS]

        # High-security assets require additional documentation
        if asset.security_classification in [SecurityClassification.CONFIDENTIAL, SecurityClassification.RESTRICTED]:
            required.extend(
                [
                    DocumentationType.SECURITY_PROCEDURES,
                    DocumentationType.ACCESS_CONTROLS,
                    DocumentationType.DATA_CLASSIFICATION,
                ]
            )

        # Production assets require operational documentation
        if asset.environment == Environment.PRODUCTION:
            required.extend(
                [
                    DocumentationType.BACKUP_PROCEDURES,
                    DocumentationType.DISASTER_RECOVERY,
                    DocumentationType.MONITORING_SETUP,
                ]
            )

        # Critical assets require comprehensive documentation
        if asset.criticality_level == CriticalityLevel.CRITICAL:
            required.extend(
                [
                    DocumentationType.RUNBOOKS,
                    DocumentationType.ESCALATION_PROCEDURES,
                    DocumentationType.CAPACITY_PLANNING,
                ]
            )

        return required

    async def assess_documentation_quality(self, document: Dict[str, Any], asset: DatabaseAsset) -> List[QualityIssue]:
        """Assess quality and freshness of existing documentation.

        Args:
            document: Documentation object to assess
            asset: Asset the documentation relates to

        Returns:
            List of quality issues identified
        """
        issues = []

        try:
            # Check documentation age
            if hasattr(document, "last_updated") and document.last_updated:
                days_since_update = (datetime.now() - document.last_updated).days
                threshold = self._get_freshness_threshold(asset)

                if days_since_update > threshold:
                    issues.append(
                        QualityIssue(
                            severity=GapSeverity.MEDIUM,
                            description=f"Documentation last updated {days_since_update} days ago",
                            recommendations=[
                                "Review and update documentation",
                                "Establish regular review schedule",
                                "Verify information accuracy",
                            ],
                        )
                    )

            # Check content completeness
            if hasattr(document, "completeness_score"):
                completeness_score = document.completeness_score
            else:
                completeness_score = await self.calculate_completeness_score(document, asset)

            if completeness_score < 0.7:  # Less than 70% complete
                issues.append(
                    QualityIssue(
                        severity=GapSeverity.HIGH,
                        description=f"Documentation is {completeness_score*100:.0f}% complete",
                        recommendations=[
                            "Complete missing sections",
                            "Use documentation template",
                            "Review with subject matter experts",
                        ],
                    )
                )

            # Check technical accuracy
            accuracy_issues = await self.validate_technical_accuracy(document, asset)
            issues.extend(accuracy_issues)

            # Check template compliance
            template_issues = await self._check_template_compliance(document, asset)
            issues.extend(template_issues)

        except Exception as e:
            logger.warning("Error assessing documentation quality: %s", str(e))

        return issues

    async def calculate_completeness_score(self, document: Dict[str, Any], asset: DatabaseAsset) -> float:
        """Calculate documentation completeness score.

        Args:
            document: Documentation to assess
            asset: Asset the documentation relates to

        Returns:
            Completeness score between 0.0 and 1.0
        """
        if not hasattr(document, "content"):
            return 0.0

        content = document.content or ""

        # Get expected sections for this document type
        doc_type = getattr(document, "documentation_type", None)
        if not doc_type:
            return 0.5  # Default score if type unknown

        doc_type_name = doc_type.value if hasattr(doc_type, "value") else str(doc_type)

        # Get template requirements
        template = self.required_docs.get("templates", {}).get(doc_type_name, {})
        required_sections = template.get("required_sections", [])
        required_fields = template.get("required_fields", [])

        if not required_sections and not required_fields:
            return 0.8  # Default good score if no specific requirements

        # Count present sections
        sections_present = 0
        for section in required_sections:
            if section.lower() in content.lower():
                sections_present += 1

        # Count present fields
        fields_present = 0
        for field in required_fields:
            if field.lower() in content.lower():
                fields_present += 1

        # Calculate weighted score
        total_requirements = len(required_sections) + len(required_fields)
        total_present = sections_present + fields_present

        return total_present / total_requirements if total_requirements > 0 else 0.0

    async def validate_technical_accuracy(self, document: Dict[str, Any], asset: DatabaseAsset) -> List[QualityIssue]:
        """Validate technical accuracy of documentation.

        Args:
            document: Documentation to validate
            asset: Asset the documentation relates to

        Returns:
            List of technical accuracy issues
        """
        issues = []

        try:
            content = getattr(document, "content", "") or ""

            # Check if documented asset name matches actual name
            if asset.name and asset.name.lower() not in content.lower():
                issues.append(
                    QualityIssue(
                        severity=GapSeverity.MEDIUM,
                        description="Documented asset name doesn't match actual asset name",
                        recommendations=[
                            "Update documentation with correct asset name",
                            "Verify all references are consistent",
                        ],
                    )
                )

            # Check connection string consistency (if available)
            if asset.connection_string:
                # Extract key components from connection string
                if "://" in asset.connection_string:
                    protocol = asset.connection_string.split("://")[0]
                    if protocol not in content.lower():
                        issues.append(
                            QualityIssue(
                                severity=GapSeverity.LOW,
                                description=f"Documentation doesn't mention database type ({protocol})",
                                recommendations=[
                                    "Include database type in technical specifications",
                                    "Document connection details accurately",
                                ],
                            )
                        )

            # Check environment consistency
            if asset.environment:
                env_name = asset.environment.value if hasattr(asset.environment, "value") else str(asset.environment)
                if env_name.lower() not in content.lower():
                    issues.append(
                        QualityIssue(
                            severity=GapSeverity.LOW,
                            description=f"Documentation doesn't specify environment ({env_name})",
                            recommendations=[
                                "Document the environment this asset belongs to",
                                "Include environment-specific procedures",
                            ],
                        )
                    )

        except Exception as e:
            logger.warning("Error validating technical accuracy: %s", str(e))

        return issues

    async def _check_template_compliance(self, document: Dict[str, Any], asset: DatabaseAsset) -> List[QualityIssue]:
        """Check compliance with documentation templates.

        Args:
            document: Documentation to check
            asset: Asset the documentation relates to

        Returns:
            List of template compliance issues
        """
        issues = []

        try:
            doc_type = getattr(document, "documentation_type", None)
            if not doc_type:
                return issues

            doc_type_name = doc_type.value if hasattr(doc_type, "value") else str(doc_type)
            template = self.required_docs.get("templates", {}).get(doc_type_name, {})

            if template:
                compliance_issues = await self.check_template_compliance(document, template)
                for compliance_issue in compliance_issues:
                    issues.append(
                        QualityIssue(
                            severity=GapSeverity.MEDIUM,
                            description=f"Template compliance issue: {compliance_issue}",
                            recommendations=[
                                "Use the standard documentation template",
                                "Include all required sections",
                                "Follow documentation guidelines",
                            ],
                        )
                    )

        except Exception as e:
            logger.warning("Error checking template compliance: %s", str(e))

        return issues

    async def check_template_compliance(self, document: Dict[str, Any], template: Dict[str, Any]) -> List[str]:
        """Check if document complies with template requirements.

        Args:
            document: Documentation to check
            template: Template requirements

        Returns:
            List of compliance issues
        """
        issues = []
        content = getattr(document, "content", "") or ""

        # Check required sections
        required_sections = template.get("required_sections", [])
        for section in required_sections:
            if section.lower() not in content.lower():
                issues.append(f"Missing required section: {section}")

        # Check required fields
        required_fields = template.get("required_fields", [])
        for field in required_fields:
            if field.lower() not in content.lower():
                issues.append(f"Missing required field: {field}")

        return issues

    def calculate_missing_doc_severity(self, asset: DatabaseAsset, doc_type: DocumentationType) -> GapSeverity:
        """Calculate severity for missing documentation.

        Args:
            asset: Asset missing documentation
            doc_type: Type of missing documentation

        Returns:
            Calculated severity level
        """
        # Critical assets missing any documentation = HIGH
        if asset.criticality_level == CriticalityLevel.CRITICAL:
            return GapSeverity.HIGH

        # Production assets missing operational docs = HIGH
        if asset.environment == Environment.PRODUCTION and doc_type in [
            DocumentationType.BACKUP_PROCEDURES,
            DocumentationType.DISASTER_RECOVERY,
            DocumentationType.RUNBOOKS,
        ]:
            return GapSeverity.HIGH

        # Security-sensitive assets missing security docs = HIGH
        if asset.security_classification in [
            SecurityClassification.CONFIDENTIAL,
            SecurityClassification.RESTRICTED,
        ] and doc_type in [DocumentationType.SECURITY_PROCEDURES, DocumentationType.ACCESS_CONTROLS]:
            return GapSeverity.HIGH

        # Basic documentation for production assets = MEDIUM
        if asset.environment == Environment.PRODUCTION and doc_type in [
            DocumentationType.BASIC_INFO,
            DocumentationType.TECHNICAL_SPECS,
        ]:
            return GapSeverity.MEDIUM

        # Everything else = MEDIUM (documentation is important)
        return GapSeverity.MEDIUM

    def generate_doc_creation_recommendations(self, asset: DatabaseAsset, doc_type: DocumentationType) -> List[str]:
        """Generate recommendations for creating missing documentation.

        Args:
            asset: Asset needing documentation
            doc_type: Type of documentation to create

        Returns:
            List of actionable recommendations
        """
        recommendations = [
            f"Create {doc_type.value} documentation for {asset.name}",
            "Use the standard documentation template",
            "Collaborate with asset owner and technical team",
        ]

        # Type-specific recommendations
        if doc_type == DocumentationType.TECHNICAL_SPECS:
            recommendations.extend(
                [
                    "Include database schema and table descriptions",
                    "Document connection details and access patterns",
                    "List dependencies and integrations",
                ]
            )
        elif doc_type == DocumentationType.SECURITY_PROCEDURES:
            recommendations.extend(
                [
                    "Document data classification and sensitivity",
                    "Include access control matrix",
                    "Specify compliance requirements",
                ]
            )
        elif doc_type == DocumentationType.BACKUP_PROCEDURES:
            recommendations.extend(
                [
                    "Document backup schedule and retention policies",
                    "Include recovery procedures and testing",
                    "Specify backup validation processes",
                ]
            )

        return recommendations

    def _get_freshness_threshold(self, asset: DatabaseAsset) -> int:
        """Get documentation freshness threshold for asset.

        Args:
            asset: Asset to get threshold for

        Returns:
            Freshness threshold in days
        """
        thresholds = self.required_docs.get("freshness_thresholds", {})

        if asset.criticality_level == CriticalityLevel.CRITICAL:
            return thresholds.get("critical_assets", 60)
        elif asset.environment == Environment.PRODUCTION:
            return thresholds.get("production_assets", 90)
        else:
            return thresholds.get("general_assets", 120)

    async def analyze_documentation_trends(self) -> Dict[str, Any]:
        """Analyze documentation trends over time.

        Returns:
            Dictionary containing trend analysis results
        """
        try:
            # Load historical documentation data
            historical_data = await self._load_historical_documentation_data()

            if len(historical_data) < 2:
                return {"coverage_trend": 0.0, "quality_trend": 0.0, "insufficient_data": True}

            # Calculate trends
            latest = historical_data[0]
            previous = historical_data[1]

            coverage_trend = (latest.documented_assets / latest.total_assets) - (
                previous.documented_assets / previous.total_assets
            )

            quality_trend = latest.average_quality_score - previous.average_quality_score

            return {
                "coverage_trend": coverage_trend,
                "quality_trend": quality_trend,
                "overall_improvement": coverage_trend > 0 and quality_trend > 0,
                "historical_data": [
                    {
                        "date": data.date.isoformat(),
                        "coverage": data.documented_assets / data.total_assets,
                        "quality": data.average_quality_score,
                    }
                    for data in historical_data
                ],
            }

        except Exception as e:
            logger.warning("Error analyzing documentation trends: %s", str(e))
            return {"error": str(e)}

    async def _load_historical_documentation_data(self) -> List[Any]:
        """Load historical documentation data for trend analysis.

        Returns:
            List of historical data points
        """
        # Placeholder implementation
        # In practice, this would load from a documentation metrics database
        return []


class SchemaDocumentationAnalyzer:
    """Analyzer for database schema documentation gaps."""

    def __init__(self, documentation_service: Optional[object] = None) -> None:
        """Initialize schema documentation analyzer.

        Args:
            documentation_service: Service for accessing documentation
        """
        self.documentation_service = documentation_service

    async def analyze_schema_documentation_gaps(self, asset: DatabaseAsset) -> List[SchemaDocumentationGap]:
        """Analyze gaps in database schema documentation.

        Args:
            asset: Database asset to analyze

        Returns:
            List of schema documentation gaps
        """
        if asset.asset_type not in [AssetType.POSTGRESQL, AssetType.SQLITE]:
            return []  # Only analyze relational databases

        schema_gaps = []

        try:
            # Get actual schema from database
            actual_schema = await self.get_database_schema(asset)

            # Get documented schema
            documented_schema = await self.documentation_service.get_schema_documentation(asset.id)

            # Compare and identify gaps
            for table in actual_schema.tables.values():
                if table.name not in documented_schema.tables:
                    schema_gaps.append(
                        SchemaDocumentationGap(
                            asset_id=asset.id,
                            gap_type=GapType.UNDOCUMENTED_TABLE,
                            table_name=table.name,
                            severity=self.calculate_table_documentation_severity(table),
                            description=f"Table {table.name} lacks documentation",
                            recommendations=[
                                "Create table documentation",
                                "Document business purpose and relationships",
                                "Include column descriptions",
                            ],
                            schema_element_type="table",
                        )
                    )
                else:
                    # Check column documentation completeness
                    documented_table = documented_schema.tables[table.name]
                    for column in table.columns.values():
                        if column.name not in documented_table.columns:
                            schema_gaps.append(
                                SchemaDocumentationGap(
                                    asset_id=asset.id,
                                    gap_type=GapType.UNDOCUMENTED_COLUMN,
                                    table_name=table.name,
                                    column_name=column.name,
                                    severity=GapSeverity.LOW,
                                    description=f"Column {table.name}.{column.name} lacks documentation",
                                    recommendations=["Document column purpose and constraints"],
                                    schema_element_type="column",
                                )
                            )

        except Exception as e:
            logger.warning("Error analyzing schema documentation for asset %s: %s", asset.id, str(e))

        return schema_gaps

    async def get_database_schema(self, asset: DatabaseAsset) -> Dict[str, List[str]]:
        """Get database schema information.

        Args:
            asset: Database asset to introspect

        Returns:
            Schema information object
        """
        # Placeholder implementation
        # In practice, this would connect to the database and introspect the schema
        from types import SimpleNamespace

        return SimpleNamespace(
            tables={
                "example_table": SimpleNamespace(
                    name="example_table",
                    columns={
                        "id": SimpleNamespace(name="id", type="INTEGER"),
                        "name": SimpleNamespace(name="name", type="VARCHAR"),
                    },
                )
            }
        )

    def calculate_table_documentation_severity(self, table: str) -> GapSeverity:
        """Calculate severity for table documentation gaps.

        Args:
            table: Table object with metadata

        Returns:
            Calculated severity level
        """
        # Check if table appears to contain important data
        if hasattr(table, "row_count") and table.row_count > 10000:
            return GapSeverity.MEDIUM

        # Check if table contains PII indicators
        if hasattr(table, "has_pii") and table.has_pii:
            return GapSeverity.MEDIUM

        # Default to low severity for schema documentation
        return GapSeverity.LOW
