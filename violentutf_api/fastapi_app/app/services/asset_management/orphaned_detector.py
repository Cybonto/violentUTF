# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Orphaned Resource Detector for Issue #281

This module implements algorithms to detect orphaned resources, including
assets without proper documentation, ownership, or code references.
"""

import ast
import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.asset_inventory import CriticalityLevel, DatabaseAsset, Environment
from app.models.gap_analysis import (
    CodeReference,
    ConfigurationDrift,
    GapSeverity,
    GapType,
    OrphanedAssetGap,
    UsageMetrics,
)

logger = logging.getLogger(__name__)


class OrphanedResourceDetector:
    """Detector for orphaned and unreferenced database assets."""

    def __init__(
        self,
        asset_service: Optional[object],
        documentation_service: Optional[object],
        monitoring_service: Optional[object],
    ) -> None:
        """Initialize the orphaned resource detector.

        Args:
            asset_service: Service for accessing asset inventory
            documentation_service: Service for accessing documentation
            monitoring_service: Service for accessing usage metrics
        """
        self.asset_service = asset_service
        self.documentation_service = documentation_service
        self.monitoring_service = monitoring_service
        self.unused_threshold_days = 90
        self._cache_enabled = True
        self._cache = {}
        self._cache_timeout = timedelta(minutes=15)

    async def detect_orphaned_assets(self) -> List[OrphanedAssetGap]:
        """Detect all types of orphaned asset gaps.

        Returns:
            List of orphaned asset gaps identified
        """
        logger.info("Starting orphaned asset detection")
        start_time = datetime.now()

        try:
            # Get all assets for analysis
            assets = await self.asset_service.get_all_assets()
            logger.info("Analyzing %d assets for orphaned resources", len(assets))

            all_gaps = []

            # Process assets in batches for performance
            batch_size = 50
            for i in range(0, len(assets), batch_size):
                batch = assets[i : i + batch_size]
                batch_gaps = await self._process_asset_batch(batch)
                all_gaps.extend(batch_gaps)

                # Log progress for large inventories
                if len(assets) > 100:
                    progress = min(100, ((i + batch_size) / len(assets)) * 100)
                    logger.info("Orphaned detection progress: %.1f%%", progress)

            execution_time = (datetime.now() - start_time).total_seconds()
            logger.info("Orphaned asset detection completed in %.2fs, found %d gaps", execution_time, len(all_gaps))

            return all_gaps

        except Exception as e:
            logger.error("Error in orphaned asset detection: %s", str(e))
            raise

    async def _process_asset_batch(self, assets: List[DatabaseAsset]) -> List[OrphanedAssetGap]:
        """Process a batch of assets for orphaned detection.

        Args:
            assets: Batch of assets to analyze

        Returns:
            List of gaps found in this batch
        """
        batch_gaps = []

        # Process assets concurrently within the batch
        tasks = [self._analyze_single_asset(asset) for asset in assets]
        asset_results = await asyncio.gather(*tasks, return_exceptions=True)

        for asset, result in zip(assets, asset_results):
            if isinstance(result, Exception):
                logger.warning("Error analyzing asset %s: %s", asset.id, str(result))
                continue

            if result:
                batch_gaps.extend(result)

        return batch_gaps

    async def _analyze_single_asset(self, asset: DatabaseAsset) -> List[OrphanedAssetGap]:
        """Analyze a single asset for orphaned resource gaps.

        Args:
            asset: Asset to analyze

        Returns:
            List of gaps found for this asset
        """
        gaps = []

        try:
            # Check for missing documentation
            doc_gaps = await self._check_missing_documentation(asset)
            gaps.extend(doc_gaps)

            # Check for unclear ownership
            ownership_gaps = await self._check_unclear_ownership(asset)
            gaps.extend(ownership_gaps)

            # Check for unreferenced assets (code analysis)
            if asset.environment == Environment.PRODUCTION:
                reference_gaps = await self._check_unreferenced_assets(asset)
                gaps.extend(reference_gaps)

            # Check for unused assets (usage pattern analysis)
            usage_gaps = await self._check_unused_assets(asset)
            gaps.extend(usage_gaps)

        except Exception as e:
            logger.warning("Error analyzing asset %s: %s", asset.id, str(e))

        return gaps

    async def _check_missing_documentation(self, asset: DatabaseAsset) -> List[OrphanedAssetGap]:
        """Check for missing documentation gaps.

        Args:
            asset: Asset to check

        Returns:
            List of documentation-related orphaned gaps
        """
        gaps = []

        try:
            # Check if asset has any documentation
            documentation = await self.documentation_service.find_asset_documentation(asset.id)

            if not documentation:
                gap = OrphanedAssetGap(
                    asset_id=asset.id,
                    gap_type=GapType.MISSING_DOCUMENTATION,
                    severity=self.calculate_documentation_gap_severity(asset),
                    description=f"Asset {asset.name} lacks proper documentation",
                    recommendations=self.generate_documentation_recommendations(asset),
                )
                gaps.append(gap)

        except Exception as e:
            logger.warning("Error checking documentation for asset %s: %s", asset.id, str(e))

        return gaps

    async def _check_unclear_ownership(self, asset: DatabaseAsset) -> List[OrphanedAssetGap]:
        """Check for unclear ownership gaps.

        Args:
            asset: Asset to check

        Returns:
            List of ownership-related orphaned gaps
        """
        gaps = []

        # Check if asset has clear ownership
        if not asset.owner_team or not asset.technical_contact:
            gap = OrphanedAssetGap(
                asset_id=asset.id,
                gap_type=GapType.UNCLEAR_OWNERSHIP,
                severity=self.calculate_ownership_gap_severity(asset),
                description=f"Asset {asset.name} lacks clear ownership assignment",
                recommendations=self.generate_ownership_recommendations(asset),
            )
            gaps.append(gap)

        return gaps

    async def _check_unreferenced_assets(self, asset: DatabaseAsset) -> List[OrphanedAssetGap]:
        """Check for unreferenced assets using code analysis.

        Args:
            asset: Asset to check

        Returns:
            List of unreferenced asset gaps
        """
        gaps = []

        try:
            # Find code references to this asset
            code_references = await self.find_code_references(asset)

            if not code_references and asset.environment == Environment.PRODUCTION:
                gap = OrphanedAssetGap(
                    asset_id=asset.id,
                    gap_type=GapType.UNREFERENCED_ASSET,
                    severity=GapSeverity.MEDIUM,
                    description=f"Production asset {asset.name} not referenced in active code",
                    recommendations=[
                        "Verify asset is still needed",
                        "Consider decommissioning if unused",
                        "Update code to remove stale references",
                    ],
                    code_references=[ref.file_path for ref in code_references],
                )
                gaps.append(gap)

        except Exception as e:
            logger.warning("Error checking code references for asset %s: %s", asset.id, str(e))

        return gaps

    async def _check_unused_assets(self, asset: DatabaseAsset) -> List[OrphanedAssetGap]:
        """Check for unused assets based on usage patterns.

        Args:
            asset: Asset to check

        Returns:
            List of unused asset gaps
        """
        gaps = []

        try:
            # Get usage metrics for the asset
            usage_metrics = await self.monitoring_service.get_asset_usage_metrics(
                asset.id, days=self.unused_threshold_days
            )

            if self.is_asset_unused(usage_metrics, asset):
                gap = OrphanedAssetGap(
                    asset_id=asset.id,
                    gap_type=GapType.UNUSED_ASSET,
                    severity=self._calculate_unused_severity(asset, usage_metrics),
                    description=f"Asset {asset.name} shows minimal usage over {self.unused_threshold_days} days",
                    recommendations=self._generate_unused_recommendations(asset, usage_metrics),
                    last_activity_date=usage_metrics.last_activity_date,
                    usage_score=usage_metrics.activity_score,
                )
                gaps.append(gap)

        except Exception as e:
            logger.warning("Error checking usage metrics for asset %s: %s", asset.id, str(e))

        return gaps

    async def find_code_references(self, asset: DatabaseAsset) -> List[CodeReference]:
        """Find references to asset in application code using AST analysis.

        Args:
            asset: Asset to search for references

        Returns:
            List of code references found
        """
        cache_key = f"code_refs_{asset.id}"
        if self._cache_enabled and cache_key in self._cache:
            cached_result, timestamp = self._cache[cache_key]
            if datetime.now() - timestamp < self._cache_timeout:
                return cached_result

        references = []

        try:
            # Search for database name references
            if asset.name:
                name_references = await self._search_code_for_pattern(asset.name)
                references.extend(name_references)

            # Search for connection string patterns
            if asset.connection_string:
                conn_references = await self._search_code_for_connection_pattern(asset.connection_string)
                references.extend(conn_references)

            # Search for file path references (SQLite/DuckDB)
            if asset.file_path:
                path_references = await self._search_code_for_path_pattern(asset.file_path)
                references.extend(path_references)

            # Cache the results
            if self._cache_enabled:
                self._cache[cache_key] = (references, datetime.now())

        except Exception as e:
            logger.warning("Error searching code references for asset %s: %s", asset.id, str(e))

        return references

    async def _search_code_for_pattern(self, pattern: str) -> List[CodeReference]:
        """Search for a pattern in code files.

        Args:
            pattern: Pattern to search for

        Returns:
            List of code references found
        """
        references = []

        # Get project root directory
        project_root = Path.cwd()

        # Search in Python files
        python_files = list(project_root.glob("**/*.py"))

        for file_path in python_files:
            # Skip virtual environments and cache directories
            if any(skip in str(file_path) for skip in [".venv", "__pycache__", ".git", "node_modules"]):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Simple text search
                if pattern.lower() in content.lower():
                    lines = content.split("\n")
                    for line_num, line in enumerate(lines, 1):
                        if pattern.lower() in line.lower():
                            references.append(
                                CodeReference(
                                    file_path=str(file_path),
                                    line_number=line_num,
                                    context=line.strip(),
                                    reference_type="name_reference",
                                )
                            )

                # AST analysis for more sophisticated detection
                ast_references = await self._analyze_ast_for_references(content, pattern, str(file_path))
                references.extend(ast_references)

            except Exception as e:
                logger.debug("Error reading file %s: %s", file_path, str(e))
                continue

        return references

    async def _search_code_for_connection_pattern(self, connection_string: str) -> List[CodeReference]:
        """Search for connection string patterns in code.

        Args:
            connection_string: Connection string to search for

        Returns:
            List of code references found
        """
        references = []

        # Extract components from connection string
        if "://" in connection_string:
            # Parse database URL
            parts = connection_string.split("://")
            if len(parts) > 1:
                protocol = parts[0]
                remainder = parts[1]

                # Search for protocol and host patterns
                if "@" in remainder:
                    host_part = remainder.split("@")[-1].split("/")[0]
                    database_part = remainder.split("/")[-1] if "/" in remainder else ""

                    # Search for these components
                    for component in [protocol, host_part, database_part]:
                        if component:
                            component_refs = await self._search_code_for_pattern(component)
                            references.extend(component_refs)

        return references

    async def _search_code_for_path_pattern(self, file_path: str) -> List[CodeReference]:
        """Search for file path patterns in code.

        Args:
            file_path: File path to search for

        Returns:
            List of code references found
        """
        references = []

        # Search for full path
        full_path_refs = await self._search_code_for_pattern(file_path)
        references.extend(full_path_refs)

        # Search for filename only
        filename = os.path.basename(file_path)
        if filename != file_path:
            filename_refs = await self._search_code_for_pattern(filename)
            references.extend(filename_refs)

        return references

    async def _analyze_ast_for_references(self, code: str, pattern: str, file_path: str) -> List[CodeReference]:
        """Analyze code using AST for more sophisticated pattern matching.

        Args:
            code: Source code to analyze
            pattern: Pattern to search for
            file_path: Path to the file being analyzed

        Returns:
            List of code references found through AST analysis
        """
        references = []

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                # Check function calls that might be database connections
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                        if func_name in ["connect", "create_engine", "open"]:
                            # Check arguments for our pattern
                            for arg in node.args:
                                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                    if pattern.lower() in arg.value.lower():
                                        references.append(
                                            CodeReference(
                                                file_path=file_path,
                                                line_number=getattr(node, "lineno", 0),
                                                context=arg.value,
                                                reference_type="connection_parameter",
                                            )
                                        )

                # Check variable assignments
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                if pattern.lower() in node.value.value.lower():
                                    references.append(
                                        CodeReference(
                                            file_path=file_path,
                                            line_number=getattr(node, "lineno", 0),
                                            context=f"{target.id} = {node.value.value}",
                                            reference_type="variable_assignment",
                                        )
                                    )

        except SyntaxError:
            # Skip files with syntax errors
            logger.debug("Syntax error in file %s, skipping AST analysis", file_path)
        except Exception as e:
            logger.debug("Error in AST analysis for %s: %s", file_path, str(e))

        return references

    async def _search_code_ast_references(
        self, tree: ast.AST, asset: DatabaseAsset, file_path: str
    ) -> List[CodeReference]:
        """Search for references using AST analysis.

        Args:
            tree: AST tree to analyze
            asset: Asset to search for
            file_path: File path being analyzed

        Returns:
            List of code references found
        """
        # This is a mock implementation - in real usage, this would be called
        # from _analyze_ast_for_references and would contain the actual AST logic
        return []

    def is_asset_unused(self, metrics: UsageMetrics, asset: DatabaseAsset) -> bool:
        """Determine if asset is considered unused based on metrics.

        Args:
            metrics: Usage metrics for the asset
            asset: Asset being evaluated

        Returns:
            True if asset is considered unused
        """
        # Handle seasonal patterns
        if hasattr(metrics, "seasonal_pattern") and metrics.seasonal_pattern:
            return False

        # Critical assets require higher evidence threshold
        if asset.criticality_level == CriticalityLevel.CRITICAL:
            return metrics.connection_count == 0 and metrics.days_since_last_activity > 180

        # Regular assets with standard threshold
        return metrics.connection_count < 5 and metrics.days_since_last_activity > self.unused_threshold_days

    def calculate_documentation_gap_severity(self, asset: DatabaseAsset) -> GapSeverity:
        """Calculate severity for documentation gaps.

        Args:
            asset: Asset with documentation gap

        Returns:
            Calculated severity level
        """
        if asset.criticality_level == CriticalityLevel.CRITICAL:
            return GapSeverity.HIGH
        elif asset.environment == Environment.PRODUCTION:
            return GapSeverity.HIGH
        elif asset.criticality_level == CriticalityLevel.HIGH:
            return GapSeverity.MEDIUM
        else:
            return GapSeverity.MEDIUM

    def calculate_ownership_gap_severity(self, asset: DatabaseAsset) -> GapSeverity:
        """Calculate severity for ownership gaps.

        Args:
            asset: Asset with ownership gap

        Returns:
            Calculated severity level
        """
        if asset.environment == Environment.PRODUCTION:
            return GapSeverity.HIGH
        elif asset.criticality_level in [CriticalityLevel.CRITICAL, CriticalityLevel.HIGH]:
            return GapSeverity.HIGH
        else:
            return GapSeverity.MEDIUM

    def _calculate_unused_severity(self, asset: DatabaseAsset, metrics: UsageMetrics) -> GapSeverity:
        """Calculate severity for unused asset gaps.

        Args:
            asset: Asset that appears unused
            metrics: Usage metrics for the asset

        Returns:
            Calculated severity level
        """
        if asset.environment == Environment.PRODUCTION:
            return GapSeverity.HIGH
        elif metrics.days_since_last_activity > 180:
            return GapSeverity.MEDIUM
        else:
            return GapSeverity.LOW

    def generate_documentation_recommendations(self, asset: DatabaseAsset) -> List[str]:
        """Generate recommendations for documentation gaps.

        Args:
            asset: Asset needing documentation

        Returns:
            List of actionable recommendations
        """
        recommendations = [
            "Create comprehensive documentation for this asset",
            "Include technical specifications and connection details",
            "Document business purpose and data classification",
            "Assign documentation ownership to responsible team",
        ]

        if asset.environment == Environment.PRODUCTION:
            recommendations.extend(
                [
                    "Create operational runbooks for production support",
                    "Document backup and recovery procedures",
                    "Include monitoring and alerting configuration",
                ]
            )

        return recommendations

    def generate_ownership_recommendations(self, asset: DatabaseAsset) -> List[str]:
        """Generate recommendations for ownership gaps.

        Args:
            asset: Asset needing ownership assignment

        Returns:
            List of actionable recommendations
        """
        recommendations = [
            "Assign clear ownership to a responsible team",
            "Designate technical contact for operational issues",
            "Document roles and responsibilities for asset management",
        ]

        if asset.environment == Environment.PRODUCTION:
            recommendations.extend(
                [
                    "Establish escalation procedures for critical issues",
                    "Define SLA requirements and response times",
                    "Ensure 24/7 on-call coverage if required",
                ]
            )

        return recommendations

    def _generate_unused_recommendations(self, asset: DatabaseAsset, metrics: UsageMetrics) -> List[str]:
        """Generate recommendations for unused asset gaps.

        Args:
            asset: Asset that appears unused
            metrics: Usage metrics for the asset

        Returns:
            List of actionable recommendations
        """
        recommendations = [
            f"Verify asset is still needed (last activity: {metrics.days_since_last_activity} days ago)",
            "Consult with asset owner before decommissioning",
            "Consider archiving data before removal",
        ]

        if metrics.days_since_last_activity > 180:
            recommendations.extend(
                [
                    "Strong candidate for decommissioning",
                    "Create data backup before removal",
                    "Update documentation to reflect decommissioning",
                ]
            )

        return recommendations

    async def detect_configuration_drift(self, asset_id: str) -> ConfigurationDrift:
        """Detect configuration drift between environments.

        Args:
            asset_id: Asset to check for configuration drift

        Returns:
            Configuration drift analysis
        """
        # This is a placeholder implementation
        # In practice, this would compare configurations across environments
        return ConfigurationDrift(asset_id=asset_id, differences=[], drift_score=0.0)

    async def _load_environment_config(self, environment: str) -> Dict[str, Any]:
        """Load configuration for specific environment.

        Args:
            environment: Environment name

        Returns:
            Configuration dictionary
        """
        # Placeholder implementation
        return {}

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self._cache.clear()
