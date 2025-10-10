# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Gap Analyzer for Issue #281

This module implements the central gap analysis orchestrator that coordinates
all gap detection algorithms and aggregates results.
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import psutil

from app.models.gap_analysis import (
    Gap,
    GapAnalysisConfig,
    GapAnalysisError,
    GapAnalysisMemoryLimit,
    GapAnalysisResult,
    GapAnalysisTimeout,
)
from app.services.asset_management.compliance_checker import ComplianceGapChecker
from app.services.asset_management.documentation_analyzer import DocumentationGapAnalyzer
from app.services.asset_management.gap_prioritizer import GapPrioritizer
from app.services.asset_management.orphaned_detector import OrphanedResourceDetector

logger = logging.getLogger(__name__)


class GapAnalyzer:
    """Central gap analysis orchestrator coordinating all detection algorithms."""

    def __init__(
        self,
        asset_service: Optional[object],
        orphaned_detector: OrphanedResourceDetector,
        documentation_analyzer: DocumentationGapAnalyzer,
        compliance_checker: ComplianceGapChecker,
        gap_prioritizer: GapPrioritizer,
    ) -> None:
        """Initialize gap analyzer with all component services.

        Args:
            asset_service: Service for accessing asset inventory
            orphaned_detector: Orphaned resource detection service
            documentation_analyzer: Documentation gap analysis service
            compliance_checker: Compliance gap assessment service
            gap_prioritizer: Gap prioritization service
        """
        self.asset_service = asset_service
        self.orphaned_detector = orphaned_detector
        self.documentation_analyzer = documentation_analyzer
        self.compliance_checker = compliance_checker
        self.gap_prioritizer = gap_prioritizer

        # Performance monitoring
        self._performance_tracker = {}
        self._cache = {}
        self._cache_timeout = timedelta(minutes=30)

    async def analyze_gaps(self, config: GapAnalysisConfig) -> GapAnalysisResult:
        """Execute comprehensive gap analysis workflow.

        Args:
            config: Gap analysis configuration

        Returns:
            Complete gap analysis results
        """
        analysis_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info("Starting gap analysis %s", analysis_id)

        try:
            # Validate configuration
            self._validate_config(config)

            # Initialize performance tracking
            self._performance_tracker[analysis_id] = {
                "start_time": start_time,
                "memory_start": self._get_memory_usage(),
            }

            # Get assets to analyze
            assets = await self._get_filtered_assets(config)
            logger.info("Analyzing %d assets", len(assets))

            # Initialize result tracking
            all_gaps = []
            errors = []
            performance_breakdown = {}

            # Execute detection algorithms based on configuration
            if config.include_orphaned_detection:
                orphaned_gaps, orphaned_time = await self._run_with_timing(
                    self.orphaned_detector.detect_orphaned_assets
                )
                all_gaps.extend(orphaned_gaps)
                performance_breakdown["orphaned_detection_time"] = orphaned_time
                logger.info("Orphaned detection found %d gaps in %.2fs", len(orphaned_gaps), orphaned_time)

            if config.include_documentation_analysis:
                doc_gaps, doc_time = await self._run_with_timing(self.documentation_analyzer.analyze_documentation_gaps)
                all_gaps.extend(doc_gaps)
                performance_breakdown["documentation_analysis_time"] = doc_time
                logger.info("Documentation analysis found %d gaps in %.2fs", len(doc_gaps), doc_time)

            if config.include_compliance_assessment:
                compliance_gaps, compliance_time = await self._run_compliance_assessment(assets, config)
                all_gaps.extend(compliance_gaps)
                performance_breakdown["compliance_assessment_time"] = compliance_time
                logger.info("Compliance assessment found %d gaps in %.2fs", len(compliance_gaps), compliance_time)

            # Deduplicate gaps
            unique_gaps = self._deduplicate_gaps(all_gaps)
            logger.info("After deduplication: %d unique gaps", len(unique_gaps))

            # Calculate priority scores for all gaps
            await self._calculate_priority_scores(unique_gaps, assets)

            # Check performance limits
            execution_time = time.time() - start_time
            memory_usage = self._get_memory_usage()

            self._check_performance_limits(config, execution_time, memory_usage)

            # Include trend analysis if requested
            trend_analysis = None
            if config.include_trend_analysis:
                trend_analysis = await self._analyze_trends()

            # Build result
            result = GapAnalysisResult(
                analysis_id=analysis_id,
                execution_time_seconds=execution_time,
                total_gaps_found=len(unique_gaps),
                assets_analyzed=len(assets),
                gaps=unique_gaps,
                gaps_by_type=self._categorize_gaps_by_type(unique_gaps),
                gaps_by_severity=self._categorize_gaps_by_severity(unique_gaps),
                performance_breakdown=performance_breakdown,
                memory_usage_mb=memory_usage,
                errors=errors,
                trend_analysis=trend_analysis,
            )

            logger.info(
                "Gap analysis %s completed successfully in %.2fs, found %d gaps",
                analysis_id,
                execution_time,
                len(unique_gaps),
            )

            return result

        except GapAnalysisTimeout:
            logger.error("Gap analysis %s timed out", analysis_id)
            raise
        except GapAnalysisMemoryLimit:
            logger.error("Gap analysis %s exceeded memory limit", analysis_id)
            raise
        except Exception as e:
            logger.error("Gap analysis %s failed: %s", analysis_id, str(e))
            raise GapAnalysisError(f"Gap analysis failed: {str(e)}") from e
        finally:
            # Cleanup tracking data
            if analysis_id in self._performance_tracker:
                del self._performance_tracker[analysis_id]

    def _validate_config(self, config: GapAnalysisConfig) -> None:
        """Validate gap analysis configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValueError: If configuration is invalid
        """
        if config.max_execution_time_seconds <= 0:
            raise ValueError("max_execution_time_seconds must be positive")

        if config.max_memory_usage_mb <= 0:
            raise ValueError("max_memory_usage_mb must be positive")

        valid_frameworks = ["GDPR", "SOC2", "NIST", "HIPAA", "PCI_DSS"]
        for framework in config.compliance_frameworks:
            if framework not in valid_frameworks:
                raise ValueError(f"Invalid compliance framework: {framework}")

    async def _get_filtered_assets(self, config: GapAnalysisConfig) -> List[object]:
        """Get assets filtered according to configuration.

        Args:
            config: Gap analysis configuration

        Returns:
            List of filtered assets
        """
        all_assets = await self.asset_service.get_all_assets()

        if not config.asset_filters:
            return all_assets

        filtered_assets = []
        for asset in all_assets:
            include_asset = True

            for filter_key, filter_values in config.asset_filters.items():
                asset_value = getattr(asset, filter_key, None)

                if asset_value is None:
                    include_asset = False
                    break

                # Handle enum values
                if hasattr(asset_value, "value"):
                    asset_value = asset_value.value

                if str(asset_value).lower() not in [v.lower() for v in filter_values]:
                    include_asset = False
                    break

            if include_asset:
                filtered_assets.append(asset)

        return filtered_assets

    async def _run_with_timing(
        self, func: Callable[..., object], *args: object, **kwargs: object
    ) -> tuple[object, float]:
        """Run a function and measure execution time.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Tuple of (result, execution_time)
        """
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            return result, execution_time
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error("Function %s failed after %.2fs: %s", func.__name__, execution_time, str(e))
            raise

    async def _run_compliance_assessment(self, assets: List[object], config: GapAnalysisConfig) -> List[Gap]:
        """Run compliance assessment across all assets.

        Args:
            assets: List of assets to assess
            config: Gap analysis configuration

        Returns:
            Tuple of (compliance_gaps, execution_time)
        """
        start_time = time.time()
        all_compliance_gaps = []

        # Process assets in batches for performance
        batch_size = 10
        for i in range(0, len(assets), batch_size):
            batch = assets[i : i + batch_size]
            batch_tasks = [self.compliance_checker.assess_compliance_gaps(asset) for asset in batch]

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for asset, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.warning("Compliance assessment failed for asset %s: %s", asset.id, str(result))
                    continue

                all_compliance_gaps.extend(result)

        execution_time = time.time() - start_time
        return all_compliance_gaps, execution_time

    def _deduplicate_gaps(self, gaps: List[Gap]) -> List[Gap]:
        """Remove duplicate gaps from the list.

        Args:
            gaps: List of gaps potentially containing duplicates

        Returns:
            List of unique gaps
        """
        seen_signatures = set()
        unique_gaps = []

        for gap in gaps:
            # Create signature based on key attributes
            signature = (
                gap.asset_id,
                gap.gap_type,
                gap.severity,
                gap.description[:100],  # First 100 chars of description
            )

            if signature not in seen_signatures:
                seen_signatures.add(signature)
                unique_gaps.append(gap)
            else:
                logger.debug("Duplicate gap detected and removed: %s", signature)

        return unique_gaps

    async def _calculate_priority_scores(self, gaps: List[Gap], assets: List[object]) -> None:
        """Calculate priority scores for all gaps.

        Args:
            gaps: List of gaps to prioritize
            assets: List of assets for context
        """
        # Create asset lookup for performance
        asset_lookup = {asset.id: asset for asset in assets}

        for gap in gaps:
            asset = asset_lookup.get(gap.asset_id)
            if asset:
                try:
                    priority_score = self.gap_prioritizer.calculate_gap_priority_score(gap, asset)
                    gap.priority_score = priority_score
                except Exception as e:
                    logger.warning("Failed to calculate priority for gap %s: %s", gap.gap_id, str(e))
                    # Set default priority on error
                    from app.models.gap_analysis import PriorityLevel, PriorityScore

                    gap.priority_score = PriorityScore(
                        score=100,
                        severity_component=5,
                        criticality_component=1.5,
                        regulatory_component=1.0,
                        security_component=1.0,
                        business_component=1.5,
                        priority_level=PriorityLevel.MEDIUM,
                    )

    def _categorize_gaps_by_type(self, gaps: List[Gap]) -> Dict[str, int]:
        """Categorize gaps by type.

        Args:
            gaps: List of gaps to categorize

        Returns:
            Dictionary mapping gap types to counts
        """
        type_counts = defaultdict(int)
        for gap in gaps:
            gap_type = gap.gap_type.value if hasattr(gap.gap_type, "value") else str(gap.gap_type)
            type_counts[gap_type] += 1
        return dict(type_counts)

    def _categorize_gaps_by_severity(self, gaps: List[Gap]) -> Dict[str, int]:
        """Categorize gaps by severity.

        Args:
            gaps: List of gaps to categorize

        Returns:
            Dictionary mapping severities to counts
        """
        severity_counts = defaultdict(int)
        for gap in gaps:
            severity = gap.severity.value if hasattr(gap.severity, "value") else str(gap.severity)
            severity_counts[severity] += 1
        return dict(severity_counts)

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB.

        Returns:
            Current memory usage in megabytes
        """
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0

    def _check_performance_limits(self, config: GapAnalysisConfig, execution_time: float, memory_usage: float) -> None:
        """Check if performance limits are exceeded.

        Args:
            config: Gap analysis configuration
            execution_time: Current execution time in seconds
            memory_usage: Current memory usage in MB

        Raises:
            GapAnalysisTimeout: If execution time limit exceeded
            GapAnalysisMemoryLimit: If memory limit exceeded
        """
        if execution_time > config.max_execution_time_seconds:
            raise GapAnalysisTimeout(
                f"Execution time {execution_time:.2f}s exceeded limit {config.max_execution_time_seconds}s"
            )

        if memory_usage > config.max_memory_usage_mb:
            raise GapAnalysisMemoryLimit(
                f"Memory usage {memory_usage:.2f}MB exceeded limit {config.max_memory_usage_mb}MB"
            )

    async def _analyze_trends(self) -> Optional[Dict[str, Any]]:
        """Analyze gap trends over time.

        Returns:
            Trend analysis results or None if not available
        """
        try:
            historical_gaps = await self._load_historical_gaps()
            if len(historical_gaps) < 2:
                return None

            # Basic trend calculation
            latest = historical_gaps[0]
            previous = historical_gaps[1]

            total_trend = (latest.get("total_gaps", 0) - previous.get("total_gaps", 0)) / max(
                previous.get("total_gaps", 1), 1
            )

            return {
                "total_gap_trend": total_trend,
                "analysis_period_days": 30,
                "trend_direction": "improving" if total_trend < 0 else "degrading",
            }

        except Exception as e:
            logger.warning("Trend analysis failed: %s", str(e))
            return None

    async def _load_historical_gaps(self) -> List[Dict[str, Any]]:
        """Load historical gap data for trend analysis.

        Returns:
            List of historical gap data points
        """
        # Placeholder implementation
        # In practice, this would load from a gap analysis history database
        return [
            {"date": datetime.now() - timedelta(days=30), "total_gaps": 20},
            {"date": datetime.now() - timedelta(days=60), "total_gaps": 25},
        ]

    def clear_cache(self) -> None:
        """Clear the internal cache."""
        self._cache.clear()

    async def get_analysis_status(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get status of running analysis.

        Args:
            analysis_id: Analysis identifier

        Returns:
            Analysis status information or None if not found
        """
        if analysis_id not in self._performance_tracker:
            return None

        tracker = self._performance_tracker[analysis_id]
        current_time = time.time()
        elapsed_time = current_time - tracker["start_time"]

        return {
            "analysis_id": analysis_id,
            "status": "running",
            "elapsed_time_seconds": elapsed_time,
            "memory_usage_mb": self._get_memory_usage(),
        }
