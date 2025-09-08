# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Legal Service Implementation (Issue #126).

Business logic service for LegalBench dataset converter operations,
providing high-level APIs for legal domain classification, conversion management,
validation, and integration with the ViolentUTF platform.

SECURITY: All operations include validation and sanitization to prevent
injection attacks and ensure data integrity.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.converters.legalbench_converter import LegalBenchDatasetConverter
from app.core.validation import sanitize_string
from app.schemas.legalbench_datasets import (
    LegalBenchBatchConversionResult,
    LegalBenchConversionConfig,
    LegalBenchValidationResult,
    LegalCategory,
    LegalClassification,
    QuestionAnsweringDataset,
)
from app.utils.legal_categorization import LegalCategorizationEngine


class LegalService:
    """Service layer for LegalBench dataset conversion and legal domain operations.

    Provides high-level APIs for managing LegalBench conversions, legal classification,
    validation, and integration with PyRIT memory and dataset registry.
    """

    def __init__(self) -> None:
        """Initialize Legal service."""
        self._active_conversions: Dict[str, Dict[str, Any]] = {}
        self._conversion_history: List[Dict[str, Any]] = []
        self._legal_engine = LegalCategorizationEngine()

    def get_converter_info(self) -> Dict[str, Any]:
        """Get information about the LegalBench converter.

        Returns:
            Converter information and capabilities
        """
        return {
            "name": "LegalBench Converter",
            "version": "1.0.0",
            "description": "TSV to QuestionAnsweringDataset converter for LegalBench legal reasoning tasks",
            "supported_formats": ["tsv", "csv"],
            "requires_manifest": False,
            "conversion_strategy": "legal_reasoning_multi_directory",
            "legal_categories": [cat.value for cat in LegalCategory],
            "output_format": "QuestionAnsweringDataset",
            "performance_targets": {
                "max_conversion_time_seconds": 600,
                "max_directory_count": 200,
                "max_memory_usage_gb": 1,
                "min_legal_classification_accuracy": 0.9,
                "min_split_preservation_accuracy": 1.0,
                "required_professional_validation_coverage": 1.0,
            },
            "capabilities": {
                "batch_processing": True,
                "parallel_directory_processing": True,
                "legal_domain_classification": True,
                "professional_validation_metadata": True,
                "train_test_split_preservation": True,
                "async_processing": True,
                "progress_tracking": True,
                "error_recovery": True,
                "validation": True,
                "multi_directory_traversal": True,
            },
        }

    async def initiate_conversion(self, dataset_root: str, config: Optional[LegalBenchConversionConfig] = None) -> str:
        """Initiate a LegalBench dataset conversion.

        Args:
            dataset_root: Root directory containing legal task directories
            config: Optional conversion configuration

        Returns:
            Conversion job ID for status tracking

        Raises:
            FileNotFoundError: If dataset root doesn't exist
            ValueError: If validation fails
        """
        # Validate dataset root
        dataset_root = sanitize_string(dataset_root)
        if not os.path.exists(dataset_root):
            raise FileNotFoundError(f"Dataset root directory not found: {dataset_root}")

        if not os.path.isdir(dataset_root):
            raise ValueError(f"Dataset root must be a directory: {dataset_root}")

        # Use default config if not provided
        if config is None:
            config = LegalBenchConversionConfig()

        # Generate unique conversion ID
        conversion_id = str(uuid.uuid4())

        # Initialize conversion tracking
        conversion_info = {
            "id": conversion_id,
            "dataset_root": dataset_root,
            "config": config,
            "status": "initializing",
            "started_at": datetime.now(timezone.utc),
            "progress": {
                "directories_discovered": 0,
                "directories_processed": 0,
                "questions_generated": 0,
                "legal_categories_found": {},
            },
            "error": None,
            "result": None,
        }

        self._active_conversions[conversion_id] = conversion_info

        # Start async conversion
        asyncio.create_task(self._execute_conversion(conversion_id))

        return conversion_id

    async def _execute_conversion(self, conversion_id: str) -> None:
        """Execute LegalBench conversion asynchronously.

        Args:
            conversion_id: Unique conversion identifier
        """
        conversion_info = self._active_conversions[conversion_id]

        try:
            conversion_info["status"] = "discovering_directories"

            # Initialize converter
            converter = LegalBenchDatasetConverter(conversion_info["config"])

            # Execute conversion
            conversion_info["status"] = "converting"
            result = converter.convert(conversion_info["dataset_root"])

            # Update final status
            conversion_info["status"] = "completed"
            conversion_info["completed_at"] = datetime.now(timezone.utc)
            conversion_info["result"] = result

            # Update progress
            conversion_info["progress"]["directories_processed"] = result.processing_stats.get(
                "successful_conversions", 0
            )
            conversion_info["progress"]["questions_generated"] = result.processing_stats.get("total_qa_entries", 0)
            conversion_info["progress"]["legal_categories_found"] = result.legal_category_summary

            # Add to history
            self._conversion_history.append(
                {
                    "id": conversion_id,
                    "dataset_root": conversion_info["dataset_root"],
                    "started_at": conversion_info["started_at"],
                    "completed_at": conversion_info["completed_at"],
                    "success": True,
                    "directories_processed": result.processing_stats.get("successful_conversions", 0),
                    "questions_generated": result.processing_stats.get("total_qa_entries", 0),
                    "legal_categories": list(result.legal_category_summary.keys()),
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
                    "dataset_root": conversion_info["dataset_root"],
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
                "total_questions": len(result.dataset.questions),
                "success_rate": result.success_rate,
                "total_processing_time_ms": result.total_processing_time_ms,
                "legal_categories": list(result.legal_category_summary.keys()),
            }
            del conversion_info["result"]

        return conversion_info

    def get_conversion_result(self, conversion_id: str) -> Optional[LegalBenchBatchConversionResult]:
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
                "dataset_root": info["dataset_root"],
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

    def classify_legal_task(self, task_name: str, task_content: Optional[Dict] = None) -> LegalClassification:
        """Classify a legal task into appropriate domain category.

        Args:
            task_name: Legal task name
            task_content: Optional task content for enhanced classification

        Returns:
            Complete legal classification result
        """
        task_name = sanitize_string(task_name)

        if task_content:
            # Sanitize task content
            sanitized_content = {}
            for key, value in task_content.items():
                if isinstance(value, str):
                    sanitized_content[sanitize_string(key)] = sanitize_string(value)
                else:
                    sanitized_content[sanitize_string(key)] = value
            task_content = sanitized_content

        return self._legal_engine.classify_legal_task(task_name, task_content)

    def get_legal_expertise_areas(self, task_name: str) -> List[str]:
        """Get relevant legal expertise areas for a task.

        Args:
            task_name: Legal task name

        Returns:
            List of relevant expertise areas for professional validation
        """
        task_name = sanitize_string(task_name)
        return self._legal_engine.get_legal_expertise_areas(task_name)

    def validate_legal_classification(self, classification: LegalClassification) -> List[str]:
        """Validate a legal classification result.

        Args:
            classification: Legal classification to validate

        Returns:
            List of validation warnings (empty if valid)
        """
        return self._legal_engine.validate_legal_classification(classification)

    def get_legal_category_info(self) -> Dict[str, Any]:
        """Get information about supported legal categories.

        Returns:
            Legal category information and statistics
        """
        categories = {}

        for category in LegalCategory:
            category_info = self._legal_engine.legal_categories.get(category, {})
            categories[category.value] = {
                "description": category_info.get("description", ""),
                "complexity": (
                    category_info.get("complexity", "medium").value
                    if hasattr(category_info.get("complexity", "medium"), "value")
                    else category_info.get("complexity", "medium")
                ),
                "specializations": category_info.get("specializations", []),
                "keyword_count": len(category_info.get("keywords", [])),
            }

        return {
            "categories": categories,
            "total_categories": len(categories),
            "complexity_levels": ["basic", "medium", "high", "very_high"],
            "classification_method": "keyword_and_content_analysis",
        }

    async def validate_dataset(self, dataset: QuestionAnsweringDataset) -> LegalBenchValidationResult:
        """Validate a legal dataset for quality and completeness.

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

        # Legal-specific validation
        legal_categories_found = set()
        professional_validation_count = 0
        split_preservation_count = 0
        total_questions = len(dataset.questions)

        for i, question in enumerate(dataset.questions):
            try:
                # Check legal metadata
                if hasattr(question, "metadata") and question.metadata:
                    if hasattr(question.metadata, "legal_classification"):
                        legal_categories_found.add(question.metadata.legal_classification.primary_category)

                    if (
                        hasattr(question.metadata, "professional_validation")
                        and question.metadata.professional_validation.validated
                    ):
                        professional_validation_count += 1

                    if hasattr(question.metadata, "split") and question.metadata.split in ["train", "test"]:
                        split_preservation_count += 1
                else:
                    validation_warnings.append(f"Question {i} missing legal metadata")

            except Exception as e:
                validation_warnings.append(f"Question {i} validation error: {e}")

        # Calculate accuracy metrics
        legal_classification_accuracy = len(legal_categories_found) / max(len(LegalCategory), 1)
        professional_validation_coverage = professional_validation_count / max(total_questions, 1)
        split_preservation_accuracy = split_preservation_count / max(total_questions, 1)

        # Determine overall validity
        dataset_valid = (
            len(validation_errors) == 0
            and legal_classification_accuracy > 0.7
            and professional_validation_coverage > 0.9
            and split_preservation_accuracy > 0.9
        )

        return LegalBenchValidationResult(
            dataset_valid=dataset_valid,
            question_count=total_questions,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            legal_classification_accuracy=legal_classification_accuracy,
            professional_validation_coverage=professional_validation_coverage,
            split_preservation_accuracy=split_preservation_accuracy,
            validation_timestamp=datetime.now(timezone.utc),
        )

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

        # Aggregate legal categories from history
        all_categories = set()
        for h in self._conversion_history:
            if h.get("legal_categories"):
                all_categories.update(h["legal_categories"])

        # Calculate status distribution for active conversions
        status_distribution = {}
        for info in self._active_conversions.values():
            status = info["status"]
            status_distribution[status] = status_distribution.get(status, 0) + 1

        return {
            "active_conversions": active_count,
            "total_conversions_history": history_count,
            "success_rate": success_rate,
            "legal_categories_encountered": sorted(list(all_categories)),
            "status_distribution": status_distribution,
            "service_uptime_info": {
                "legal_categories_supported": len(LegalCategory),
                "max_parallel_conversions": 10,  # Could be configurable
                "cleanup_interval_hours": 24,
            },
        }
