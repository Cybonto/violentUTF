# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""DocMath Service Implementation (Issue #127).

Business logic service for DocMath dataset converter operations,
providing high-level APIs for mathematical reasoning classification, conversion management,
validation, and integration with the ViolentUTF platform.

SECURITY: All operations include validation and sanitization to prevent
injection attacks and ensure data integrity.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.converters.docmath_converter import DocMathConverter
from app.core.validation import sanitize_string
from app.schemas.docmath_datasets import (
    DocMathConversionConfig,
    MathematicalDomain,
    QuestionAnsweringDataset,
)
from app.services.mathematical_service import (
    MathematicalComplexityAnalyzer,
    MathematicalDomainClassifier,
)


class DocMathService:
    """Service layer for DocMath dataset conversion and mathematical domain operations.

    Provides high-level APIs for managing DocMath conversions, mathematical classification,
    validation, and integration with PyRIT memory and dataset registry.
    """

    def __init__(self) -> None:
        """Initialize DocMath service."""
        self._active_conversions: Dict[str, Dict[str, Any]] = {}
        self._conversion_history: List[Dict[str, Any]] = []
        self._domain_classifier = MathematicalDomainClassifier()
        self._complexity_analyzer = MathematicalComplexityAnalyzer()

    def get_converter_info(self) -> Dict[str, Any]:
        """Get information about the DocMath converter.

        Returns:
            Converter information and capabilities
        """
        return {
            "name": "DocMath Converter",
            "version": "1.0.0",
            "description": "JSON to QuestionAnsweringDataset converter for DocMath mathematical reasoning "
            + "tasks with large file handling",
            "supported_formats": ["json"],
            "requires_manifest": False,
            "conversion_strategy": "strategy_2_reasoning_benchmarks",
            "mathematical_domains": [domain.value for domain in MathematicalDomain],
            "complexity_tiers": ["simpshort", "simplong", "compshort", "complong"],
            "output_format": "QuestionAnsweringDataset",
            "performance_targets": {
                "max_conversion_time_seconds": 1800,  # 30 minutes for 220MB files
                "max_file_size_mb": 220,
                "max_memory_usage_gb": 2,
                "min_mathematical_classification_accuracy": 0.85,
                "min_context_preservation_accuracy": 1.0,
                "required_large_file_handling": True,
            },
            "capabilities": {
                "large_file_processing": True,
                "file_splitting": True,
                "streaming_processing": True,
                "mathematical_domain_classification": True,
                "complexity_assessment": True,
                "memory_monitoring": True,
                "async_processing": True,
                "progress_tracking": True,
                "error_recovery": True,
                "validation": True,
                "multi_tier_support": True,
            },
        }

    async def initiate_conversion(self, dataset_path: str, config: Optional[DocMathConversionConfig] = None) -> str:
        """Initiate a DocMath dataset conversion.

        Args:
            dataset_path: Path to DocMath dataset directory containing tier files
            config: Optional conversion configuration

        Returns:
            Conversion job ID for status tracking

        Raises:
            FileNotFoundError: If dataset path doesn't exist
            ValueError: If validation fails
        """
        # Validate dataset path
        dataset_path = sanitize_string(dataset_path)
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"Dataset path not found: {dataset_path}")

        if not os.path.isdir(dataset_path):
            raise ValueError(f"Dataset path must be a directory: {dataset_path}")

        # Use default config if not provided
        if config is None:
            config = DocMathConversionConfig()

        # Generate unique conversion ID
        conversion_id = str(uuid.uuid4())

        # Initialize conversion tracking
        conversion_info = {
            "id": conversion_id,
            "dataset_path": dataset_path,
            "config": config,
            "status": "initializing",
            "started_at": datetime.now(timezone.utc),
            "progress": {
                "files_discovered": 0,
                "files_processed": 0,
                "questions_generated": 0,
                "complexity_tiers_found": {},
                "mathematical_domains_found": {},
                "memory_peak_gb": 0.0,
            },
            "error": None,
            "result": None,
        }

        self._active_conversions[conversion_id] = conversion_info

        # Start async conversion
        asyncio.create_task(self._execute_conversion(conversion_id))

        return conversion_id

    async def _execute_conversion(self, conversion_id: str) -> None:
        """Execute DocMath conversion asynchronously.

        Args:
            conversion_id: Unique conversion identifier
        """
        conversion_info = self._active_conversions[conversion_id]

        try:
            conversion_info["status"] = "discovering_files"

            # Initialize converter
            converter = DocMathConverter(conversion_info["config"])

            # Execute conversion
            conversion_info["status"] = "converting"
            result = converter.convert(conversion_info["dataset_path"])

            # Update final status
            conversion_info["status"] = "completed"
            conversion_info["completed_at"] = datetime.now(timezone.utc)
            conversion_info["result"] = result

            # Update progress from result metadata
            if hasattr(result, "metadata") and result.metadata:
                processing_summary = result.metadata.get("processing_summary", {})

                conversion_info["progress"]["files_processed"] = len(processing_summary)
                conversion_info["progress"]["questions_generated"] = result.metadata.get("total_questions", 0)
                conversion_info["progress"]["memory_peak_gb"] = result.metadata.get("memory_peak_gb", 0.0)

                # Count complexity tiers and domains
                for file_info in processing_summary.values():
                    if isinstance(file_info, dict) and "tier" in file_info:
                        tier = file_info["tier"]
                        conversion_info["progress"]["complexity_tiers_found"][tier] = (
                            conversion_info["progress"]["complexity_tiers_found"].get(tier, 0) + 1
                        )

                # Analyze mathematical domains from questions
                domain_counts = {}
                for question in result.questions:
                    if hasattr(question, "metadata") and question.metadata:
                        domain = question.metadata.get("mathematical_domain", "general")
                        domain_counts[domain] = domain_counts.get(domain, 0) + 1

                conversion_info["progress"]["mathematical_domains_found"] = domain_counts

            # Add to history
            self._conversion_history.append(
                {
                    "id": conversion_id,
                    "dataset_path": conversion_info["dataset_path"],
                    "started_at": conversion_info["started_at"],
                    "completed_at": conversion_info["completed_at"],
                    "success": True,
                    "files_processed": conversion_info["progress"]["files_processed"],
                    "questions_generated": conversion_info["progress"]["questions_generated"],
                    "complexity_tiers": list(conversion_info["progress"]["complexity_tiers_found"].keys()),
                    "mathematical_domains": list(conversion_info["progress"]["mathematical_domains_found"].keys()),
                    "memory_peak_gb": conversion_info["progress"]["memory_peak_gb"],
                }
            )

        except Exception as e:
            conversion_info["status"] = "failed"
            conversion_info["error"] = str(e)
            conversion_info["completed_at"] = datetime.now(timezone.utc)

            # Add to history
            self._conversion_history.append(
                {
                    "id": conversion_id,
                    "dataset_path": conversion_info["dataset_path"],
                    "started_at": conversion_info["started_at"],
                    "completed_at": conversion_info["completed_at"],
                    "success": False,
                    "error": str(e),
                }
            )

    def get_conversion_status(self, conversion_id: str) -> Dict[str, Any]:
        """Get status of a conversion job.

        Args:
            conversion_id: Unique conversion identifier

        Returns:
            Conversion status information

        Raises:
            ValueError: If conversion ID not found
        """
        conversion_id = sanitize_string(conversion_id)

        if conversion_id not in self._active_conversions:
            raise ValueError(f"Conversion ID not found: {conversion_id}")

        conversion_info = self._active_conversions[conversion_id].copy()

        # Don't return the full result object in status (too large)
        if "result" in conversion_info and conversion_info["result"]:
            result = conversion_info["result"]
            conversion_info["result_summary"] = {
                "total_questions": len(result.questions),
                "name": result.name,
                "version": result.version,
                "complexity_tiers": result.metadata.get("complexity_tiers", 0),
                "processing_time_seconds": result.metadata.get("processing_time_seconds", 0),
                "mathematical_domains": list(conversion_info["progress"]["mathematical_domains_found"].keys()),
            }
            del conversion_info["result"]

        return conversion_info

    def get_conversion_result(self, conversion_id: str) -> Optional[QuestionAnsweringDataset]:
        """Get full conversion result.

        Args:
            conversion_id: Unique conversion identifier

        Returns:
            Complete conversion result or None if not found/completed
        """
        conversion_id = sanitize_string(conversion_id)

        if conversion_id not in self._active_conversions:
            return None

        conversion_info = self._active_conversions[conversion_id]
        return conversion_info.get("result")

    def list_active_conversions(self) -> List[Dict[str, Any]]:
        """List all active conversion jobs.

        Returns:
            List of active conversion summaries
        """
        summaries = []

        for conversion_id, info in self._active_conversions.items():
            summary = {
                "id": conversion_id,
                "dataset_path": info["dataset_path"],
                "status": info["status"],
                "started_at": info["started_at"],
                "progress": info["progress"].copy(),
            }

            if info["status"] in ["completed", "failed"]:
                summary["completed_at"] = info.get("completed_at")

            if info.get("error"):
                summary["error"] = info["error"]

            summaries.append(summary)

        return summaries

    def get_conversion_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversion history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of historical conversion summaries
        """
        return self._conversion_history[-limit:] if limit > 0 else self._conversion_history

    def cancel_conversion(self, conversion_id: str) -> bool:
        """Cancel an active conversion.

        Args:
            conversion_id: Unique conversion identifier

        Returns:
            True if successfully cancelled, False otherwise
        """
        conversion_id = sanitize_string(conversion_id)

        if conversion_id not in self._active_conversions:
            return False

        conversion_info = self._active_conversions[conversion_id]

        if conversion_info["status"] in ["completed", "failed", "cancelled"]:
            return False

        conversion_info["status"] = "cancelled"
        conversion_info["completed_at"] = datetime.now(timezone.utc)

        return True

    def classify_mathematical_domain(self, item: Dict[str, Any]) -> str:
        """Classify mathematical domain of a DocMath item.

        Args:
            item: DocMath item with question and context

        Returns:
            Mathematical domain classification
        """
        # Sanitize input
        sanitized_item = {}
        for key, value in item.items():
            if isinstance(value, str):
                sanitized_item[sanitize_string(key)] = sanitize_string(value)
            elif isinstance(value, list):
                sanitized_item[sanitize_string(key)] = [sanitize_string(v) if isinstance(v, str) else v for v in value]
            else:
                sanitized_item[sanitize_string(key)] = value

        return self._domain_classifier.classify_mathematical_domain(sanitized_item)

    def assess_mathematical_complexity(self, item: Dict[str, Any], tier: str) -> float:
        """Assess mathematical complexity of a DocMath item.

        Args:
            item: DocMath item with question and context
            tier: Complexity tier (simpshort, simplong, compshort, complong)

        Returns:
            Complexity score between 0.0 and 1.0
        """
        # Sanitize input
        sanitized_item = {}
        for key, value in item.items():
            if isinstance(value, str):
                sanitized_item[sanitize_string(key)] = sanitize_string(value)
            elif isinstance(value, list):
                sanitized_item[sanitize_string(key)] = [sanitize_string(v) if isinstance(v, str) else v for v in value]
            else:
                sanitized_item[sanitize_string(key)] = value

        tier = sanitize_string(tier)
        return self._complexity_analyzer.assess_mathematical_complexity(sanitized_item, tier)

    def get_mathematical_domain_info(self) -> Dict[str, Any]:
        """Get information about supported mathematical domains.

        Returns:
            Mathematical domain information and statistics
        """
        domains = {}

        for domain in MathematicalDomain:
            domain_info = self._domain_classifier.domain_patterns.get(domain, {})
            domains[domain.value] = {
                "description": f"Mathematical problems in {domain.value} domain",
                "complexity": domain_info.get("complexity", "medium"),
                "keywords": domain_info.get("keywords", []),
                "patterns": domain_info.get("patterns", []),
            }

        return {
            "domains": domains,
            "total_domains": len(domains),
            "complexity_levels": ["low", "medium", "high", "variable"],
            "classification_method": "keyword_and_pattern_analysis",
            "complexity_tiers": ["simpshort", "simplong", "compshort", "complong"],
        }

    def validate_dataset(self, dataset: QuestionAnsweringDataset) -> Dict[str, Any]:
        """Validate a DocMath dataset for quality and completeness.

        Args:
            dataset: Dataset to validate

        Returns:
            Comprehensive validation result
        """
        validation_errors = []
        validation_warnings = []

        # Basic dataset validation
        if not dataset.questions:
            validation_errors.append("Dataset contains no questions")

        if not dataset.metadata:
            validation_warnings.append("Dataset metadata is empty")

        # DocMath-specific validation
        mathematical_domains_found = set()
        complexity_tiers_found = set()
        context_preservation_count = 0
        mathematical_classification_count = 0
        total_questions = len(dataset.questions)

        for i, question in enumerate(dataset.questions):
            try:
                # Check mathematical metadata
                if hasattr(question, "metadata") and question.metadata:
                    if "mathematical_domain" in question.metadata:
                        mathematical_domains_found.add(question.metadata["mathematical_domain"])
                        mathematical_classification_count += 1

                    if "complexity_tier" in question.metadata:
                        complexity_tiers_found.add(question.metadata["complexity_tier"])

                    # Check context preservation
                    if any(
                        key in question.metadata for key in ["table_evidence", "paragraph_evidence", "reasoning_steps"]
                    ):
                        context_preservation_count += 1
                else:
                    validation_warnings.append(f"Question {i} missing mathematical metadata")

            except Exception as e:
                validation_warnings.append(f"Question {i} validation error: {e}")

        # Calculate accuracy metrics
        mathematical_classification_accuracy = mathematical_classification_count / max(total_questions, 1)
        context_preservation_accuracy = context_preservation_count / max(total_questions, 1)

        # Determine overall validity
        dataset_valid = (
            len(validation_errors) == 0
            and mathematical_classification_accuracy > 0.8
            and context_preservation_accuracy > 0.9
            and len(mathematical_domains_found) > 0
        )

        return {
            "dataset_valid": dataset_valid,
            "question_count": total_questions,
            "validation_errors": validation_errors,
            "validation_warnings": validation_warnings,
            "mathematical_classification_accuracy": mathematical_classification_accuracy,
            "context_preservation_accuracy": context_preservation_accuracy,
            "mathematical_domains_found": list(mathematical_domains_found),
            "complexity_tiers_found": list(complexity_tiers_found),
            "validation_timestamp": datetime.now(timezone.utc),
        }

    def cleanup_completed_conversions(self, max_age_hours: int = 24) -> int:
        """Clean up completed conversions older than specified age.

        Args:
            max_age_hours: Maximum age in hours for completed conversions

        Returns:
            Number of conversions cleaned up
        """
        cleanup_count = 0
        current_time = datetime.now(timezone.utc)

        # Find conversions to remove
        conversions_to_remove = []

        for conversion_id, info in self._active_conversions.items():
            if info["status"] in ["completed", "failed", "cancelled"]:
                completed_at = info.get("completed_at")
                if completed_at:
                    age_hours = (current_time - completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        conversions_to_remove.append(conversion_id)

        # Remove old conversions
        for conversion_id in conversions_to_remove:
            del self._active_conversions[conversion_id]
            cleanup_count += 1

        return cleanup_count

    def get_service_statistics(self) -> Dict[str, Any]:
        """Get service usage statistics.

        Returns:
            Service statistics and metrics
        """
        active_count = len(self._active_conversions)
        history_count = len(self._conversion_history)

        # Calculate success rate from history
        successful_conversions = sum(1 for h in self._conversion_history if h.get("success", False))
        success_rate = successful_conversions / max(history_count, 1)

        # Aggregate mathematical domains from history
        all_domains = set()
        all_tiers = set()
        total_memory_peak = 0.0

        for h in self._conversion_history:
            if h.get("mathematical_domains"):
                all_domains.update(h["mathematical_domains"])
            if h.get("complexity_tiers"):
                all_tiers.update(h["complexity_tiers"])
            if h.get("memory_peak_gb"):
                total_memory_peak += h["memory_peak_gb"]

        avg_memory_peak = total_memory_peak / max(successful_conversions, 1)

        # Calculate status distribution for active conversions
        status_distribution = {}
        for info in self._active_conversions.values():
            status = info["status"]
            status_distribution[status] = status_distribution.get(status, 0) + 1

        return {
            "active_conversions": active_count,
            "total_conversions_history": history_count,
            "success_rate": success_rate,
            "mathematical_domains_encountered": sorted(list(all_domains)),
            "complexity_tiers_encountered": sorted(list(all_tiers)),
            "average_memory_peak_gb": avg_memory_peak,
            "status_distribution": status_distribution,
            "service_uptime_info": {
                "mathematical_domains_supported": len(MathematicalDomain),
                "complexity_tiers_supported": 4,
                "max_parallel_conversions": 5,  # Lower than legal due to memory requirements
                "cleanup_interval_hours": 24,
                "max_file_size_mb": 220,
                "memory_limit_gb": 2.0,
            },
        }
