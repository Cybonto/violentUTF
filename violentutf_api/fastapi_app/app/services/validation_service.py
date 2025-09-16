# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Validation Service for dataset validation operations.

This service provides high-level validation operations for datasets,
including orchestration of multiple validators, result aggregation,
and integration with the conversion pipeline.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.dataset_validation import (
    ValidationFramework,
    ValidationLevel,
    ValidationResult,
    ValidationStatus,
)
from app.schemas.validation import (
    PerformanceMetrics,
    ValidationDetailSchema,
    ValidationRequest,
    ValidationResponse,
    ValidationResultSchema,
    ValidationStatusEnum,
)
from app.services.dataset_integration_service import get_dataset_prompts

logger = logging.getLogger(__name__)


def _convert_status_to_enum(status: ValidationStatus) -> ValidationStatusEnum:
    """Convert internal ValidationStatus to API ValidationStatusEnum."""
    return ValidationStatusEnum(status.value)


class ValidationService:
    """Service for performing dataset validations."""

    def __init__(self) -> None:
        """Initialize the validation service."""
        self.framework = ValidationFramework()
        self.active_validations: Dict[str, Dict[str, Any]] = {}
        self.validation_history: List[Dict[str, Any]] = []
        self.service_start_time = time.time()
        self.total_validations = 0

        logger.info("ValidationService initialized")

    async def validate_dataset(
        self, request: ValidationRequest, user_context: Optional[str] = None
    ) -> ValidationResponse:
        """Perform comprehensive dataset validation.

        Args:
            request: Validation request parameters
            user_context: User context for dataset access

        Returns:
            ValidationResponse with complete results
        """
        validation_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info("Starting dataset validation %s for dataset %s", validation_id, request.dataset_id)

        # Track active validation
        self.active_validations[validation_id] = {
            "dataset_id": request.dataset_id,
            "status": "running",
            "start_time": start_time,
            "level": request.validation_level,
        }

        try:
            # Convert enum to internal enum
            validation_level = ValidationLevel(request.validation_level.value)

            results = []
            errors = []
            warnings = []
            performance_metrics = None

            # Determine what validations to run based on request
            if any(vtype.value == "source_data" for vtype in request.validation_types):
                # Source data validation
                try:
                    file_path = request.file_path or await self._get_dataset_file_path(request.dataset_id, user_context)
                    if file_path:
                        source_result = await self.framework.validate_source_data(file_path, validation_level)
                        results.append(source_result)

                        # Collect warnings and errors
                        for detail in source_result.details:
                            if detail.status == ValidationStatus.WARNING:
                                warnings.append(detail.message)
                            elif detail.status == ValidationStatus.FAIL:
                                errors.append(detail.message)
                    else:
                        errors.append("Could not determine file path for source data validation")

                except Exception as e:
                    error_msg = f"Source data validation failed: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            if any(vtype.value == "conversion_result" for vtype in request.validation_types):
                # Conversion result validation
                try:
                    original_data, converted_data = await self._get_conversion_data(request.dataset_id, user_context)
                    if original_data and converted_data:
                        conversion_result = await self.framework.validate_conversion_result(
                            original_data, converted_data, validation_level
                        )
                        results.append(conversion_result)

                        # Collect warnings and errors
                        for detail in conversion_result.details:
                            if detail.status == ValidationStatus.WARNING:
                                warnings.append(detail.message)
                            elif detail.status == ValidationStatus.FAIL:
                                errors.append(detail.message)
                    else:
                        warnings.append("Could not obtain conversion data for validation")

                except Exception as e:
                    error_msg = f"Conversion result validation failed: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            if any(vtype.value == "performance" for vtype in request.validation_types):
                # Performance validation
                try:
                    perf_metrics = await self._collect_performance_metrics(
                        request.dataset_id, validation_id, user_context
                    )

                    if perf_metrics:
                        performance_result = await self.framework.validate_performance(
                            perf_metrics, request.dataset_type, validation_level
                        )
                        results.append(performance_result)

                        # Store performance metrics for response
                        performance_metrics = PerformanceMetrics(
                            processing_time_seconds=perf_metrics.get("processing_time_seconds", 0),
                            memory_usage_mb=perf_metrics.get("memory_usage_mb", 0),
                            validation_time_seconds=perf_metrics.get("validation_time_seconds", 0),
                            throughput_items_per_second=perf_metrics.get("throughput_items_per_second"),
                            cpu_usage_percent=perf_metrics.get("cpu_usage_percent"),
                        )

                        # Collect warnings and errors
                        for detail in performance_result.details:
                            if detail.status == ValidationStatus.WARNING:
                                warnings.append(detail.message)
                            elif detail.status == ValidationStatus.FAIL:
                                errors.append(detail.message)
                    else:
                        warnings.append("Could not collect performance metrics")

                except Exception as e:
                    error_msg = f"Performance validation failed: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Determine overall result
            overall_result = self._determine_overall_result(results)

            # Calculate total execution time
            total_execution_time = (time.time() - start_time) * 1000

            # Generate summary
            summary = self._generate_validation_summary(results, errors, warnings)

            # Create response
            response = ValidationResponse(
                validation_id=validation_id,
                dataset_id=request.dataset_id,
                status="completed",
                overall_result=_convert_status_to_enum(overall_result),
                validation_level=request.validation_level,
                results=[self.convert_result_to_schema(result) for result in results],
                summary=summary,
                total_execution_time_ms=total_execution_time,
                timestamp=datetime.now(),
                performance_metrics=performance_metrics,
                errors=errors,
                warnings=warnings,
                statistics={
                    "total_validators_run": len(results),
                    "validation_types_requested": len(request.validation_types),
                    "validation_overhead_ms": total_execution_time,
                },
            )

            # Update tracking
            self.active_validations.pop(validation_id, None)
            self.total_validations += 1

            # Add to history
            self.validation_history.append(
                {
                    "validation_id": validation_id,
                    "dataset_id": request.dataset_id,
                    "validation_level": request.validation_level,
                    "overall_result": overall_result,
                    "timestamp": datetime.now(),
                    "execution_time_ms": total_execution_time,
                    "validation_types": [vtype.value for vtype in request.validation_types],
                    "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                }
            )

            # Keep history size manageable
            if len(self.validation_history) > 1000:
                self.validation_history = self.validation_history[-500:]

            logger.info("Completed dataset validation %s with result: %s", validation_id, overall_result)
            return response

        except Exception as e:
            logger.error("Dataset validation %s failed: %s", validation_id, e)

            # Clean up tracking
            self.active_validations.pop(validation_id, None)

            # Return error response
            return ValidationResponse(
                validation_id=validation_id,
                dataset_id=request.dataset_id,
                status="failed",
                overall_result=_convert_status_to_enum(ValidationStatus.FAIL),
                validation_level=request.validation_level,
                results=[],
                summary=f"Validation failed: {str(e)}",
                total_execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.now(),
                errors=[str(e)],
            )

    async def validate_source_data_only(
        self, file_path: str, validation_level: ValidationLevel = ValidationLevel.FULL
    ) -> ValidationResult:
        """Validate source data file only.

        Args:
            file_path: Path to the source data file
            validation_level: Level of validation to perform

        Returns:
            ValidationResult for source data
        """
        logger.info("Validating source data: %s", file_path)
        return await self.framework.validate_source_data(file_path, validation_level)

    async def validate_conversion_result_only(
        self,
        original_data: Any,  # noqa: ANN401
        converted_data: Any,  # noqa: ANN401
        validation_level: ValidationLevel = ValidationLevel.FULL,  # noqa: ANN401
    ) -> ValidationResult:
        """Validate conversion result only.

        Args:
            original_data: Original dataset data
            converted_data: Converted dataset data
            validation_level: Level of validation to perform

        Returns:
            ValidationResult for conversion
        """
        logger.info("Validating conversion result")
        return await self.framework.validate_conversion_result(original_data, converted_data, validation_level)

    async def get_service_status(self) -> Dict[str, Any]:
        """Get validation service status.

        Returns:
            Dictionary with service status information
        """
        uptime = time.time() - self.service_start_time

        return {
            "status": "running",
            "available_validators": list(self.framework.validators.keys()),
            "total_validations": self.total_validations,
            "active_validations": len(self.active_validations),
            "service_uptime_seconds": uptime,
            "memory_usage_mb": self._get_current_memory_usage(),
            "last_validation": (
                max(self.validation_history, key=lambda x: x["timestamp"])["timestamp"]
                if self.validation_history
                else None
            ),
        }

    async def get_validation_history(
        self, dataset_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get validation history.

        Args:
            dataset_id: Optional dataset ID filter
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            Tuple of (history entries, total count)
        """
        history = self.validation_history

        if dataset_id:
            history = [h for h in history if h.get("dataset_id") == dataset_id]

        total = len(history)

        # Sort by timestamp descending
        history = sorted(history, key=lambda x: x["timestamp"], reverse=True)

        # Apply pagination
        paginated_history = history[offset : offset + limit]

        return paginated_history, total

    async def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dictionary with validation statistics
        """
        if not self.validation_history:
            return {
                "total_validations": 0,
                "successful_validations": 0,
                "failed_validations": 0,
                "warnings": 0,
                "average_execution_time_ms": 0.0,
                "peak_memory_usage_mb": 0.0,
                "validation_types": {},
                "dataset_types": {},
                "status_distribution": {},
                "last_updated": datetime.now(),
            }

        successful = len([h for h in self.validation_history if h["overall_result"] == ValidationStatus.PASS])
        failed = len([h for h in self.validation_history if h["overall_result"] == ValidationStatus.FAIL])
        warnings = len([h for h in self.validation_history if h["overall_result"] == ValidationStatus.WARNING])

        avg_time = sum(h["execution_time_ms"] for h in self.validation_history) / len(self.validation_history)

        # Count validation types
        validation_types: Dict[str, int] = {}
        for history_entry in self.validation_history:
            for vtype in history_entry.get("validation_types", []):
                validation_types[vtype] = validation_types.get(vtype, 0) + 1

        return {
            "total_validations": self.total_validations,
            "successful_validations": successful,
            "failed_validations": failed,
            "warnings": warnings,
            "average_execution_time_ms": avg_time,
            "peak_memory_usage_mb": self._get_current_memory_usage(),  # Simplified
            "validation_types": validation_types,
            "dataset_types": {},  # Would be populated from actual data
            "status_distribution": {"PASS": successful, "FAIL": failed, "WARNING": warnings, "SKIP": 0},
            "last_updated": datetime.now(),
        }

    def _determine_overall_result(self, results: List[ValidationResult]) -> ValidationStatus:
        """Determine overall validation result from individual results."""
        if not results:
            return ValidationStatus.SKIP

        # If any failed, overall is fail
        if any(r.status == ValidationStatus.FAIL for r in results):
            return ValidationStatus.FAIL

        # If any warnings, overall is warning
        if any(r.status == ValidationStatus.WARNING for r in results):
            return ValidationStatus.WARNING

        # If all skipped, overall is skip
        if all(r.status == ValidationStatus.SKIP for r in results):
            return ValidationStatus.SKIP

        # Otherwise, pass
        return ValidationStatus.PASS

    def _generate_validation_summary(
        self, results: List[ValidationResult], errors: List[str], warnings: List[str]
    ) -> str:
        """Generate a human-readable validation summary."""
        if not results:
            return "No validation results"

        total_validators = len(results)
        passed_validators = len([r for r in results if r.status == ValidationStatus.PASS])
        failed_validators = len([r for r in results if r.status == ValidationStatus.FAIL])
        warning_validators = len([r for r in results if r.status == ValidationStatus.WARNING])

        summary_parts = [f"Validation completed: {passed_validators}/{total_validators} validators passed"]

        if failed_validators > 0:
            summary_parts.append(f"{failed_validators} failed")

        if warning_validators > 0:
            summary_parts.append(f"{warning_validators} with warnings")

        if errors:
            summary_parts.append(f"{len(errors)} errors encountered")

        if warnings:
            summary_parts.append(f"{len(warnings)} warnings")

        return "; ".join(summary_parts)

    def convert_result_to_schema(self, result: ValidationResult) -> ValidationResultSchema:
        """Convert ValidationResult to ValidationResultSchema."""
        return ValidationResultSchema(
            validation_type=result.validation_type,
            status=_convert_status_to_enum(result.status),
            details=[
                ValidationDetailSchema(
                    rule_name=detail.rule_name,
                    status=_convert_status_to_enum(detail.status),
                    message=detail.message,
                    severity=detail.severity,
                    remediation_suggestion=detail.remediation_suggestion,
                    execution_time_ms=detail.execution_time_ms,
                    metadata=detail.metadata,
                )
                for detail in result.details
            ],
            metrics=result.metrics,
            timestamp=result.timestamp,
            execution_time_ms=result.execution_time_ms,
            validator_name=result.validator_name,
        )

    async def _get_dataset_file_path(self, dataset_id: str, user_context: Optional[str] = None) -> Optional[str]:
        """Get file path for a dataset."""
        try:
            # In a real implementation, this would query the dataset service
            # For now, return a placeholder that indicates the dataset path
            return f"/app/app_data/datasets/{dataset_id}"
        except Exception as e:
            logger.error("Error getting dataset file path: %s", e)
            return None

    async def _get_conversion_data(
        self, dataset_id: str, user_context: Optional[str] = None
    ) -> Tuple[Optional[Any], Optional[Any]]:
        """Get original and converted data for comparison."""
        try:
            # This would integrate with the actual dataset service
            # For now, get prompts as converted data
            converted_prompts = await get_dataset_prompts(dataset_id, user_context=user_context)

            # Original data would come from the source file
            # For now, simulate original data
            original_data = [{"id": i, "content": f"Original content {i}"} for i in range(len(converted_prompts))]

            return original_data, converted_prompts
        except Exception as e:
            logger.error("Error getting conversion data: %s", e)
            return None, None

    async def _collect_performance_metrics(
        self, dataset_id: str, validation_id: str, user_context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Collect performance metrics for validation."""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent()

            # Simulate processing time based on dataset size
            # In real implementation, this would come from actual conversion metrics
            processing_time = 30.0  # Simulated
            validation_time = 2.0  # Simulated

            return {
                "processing_time_seconds": processing_time,
                "memory_usage_mb": memory_mb,
                "validation_time_seconds": validation_time,
                "cpu_usage_percent": cpu_percent,
                "throughput_items_per_second": 100.0,  # Simulated
            }
        except Exception as e:
            logger.error("Error collecting performance metrics: %s", e)
            return None

    def _get_current_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0
