# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Dataset Validation Framework for ViolentUTF.

Comprehensive validation framework to ensure data integrity, format compliance,
and conversion quality across all dataset integration operations.

This module implements:
- Source data validation (file integrity, format compliance)
- Conversion result validation (data preservation, format compliance)
- Performance validation (processing time, memory usage)
- Validation reporting and alerting
- Multiple validation levels (quick, full, deep)
"""

import csv
import io
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status enumeration."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIP = "SKIP"


class ValidationLevel(Enum):
    """Validation level enumeration."""

    QUICK = "quick"  # Basic validation - essential checks only
    FULL = "full"  # Comprehensive validation - all standard checks
    DEEP = "deep"  # Exhaustive validation - includes performance profiling


@dataclass
class ValidationDetail:
    """Detailed validation result for a specific rule."""

    rule_name: str
    status: ValidationStatus
    message: str
    severity: str  # ERROR, WARNING, INFO
    remediation_suggestion: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    validation_type: str
    status: ValidationStatus
    details: List[ValidationDetail]
    metrics: Dict[str, Any]
    timestamp: datetime
    execution_time_ms: float = 0.0
    validator_name: str = ""

    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if not self.validator_name:
            self.validator_name = f"{self.validation_type}_validator"

    def get_summary(self) -> str:
        """Get a summary of the validation result."""
        total_rules = len(self.details)
        passed_rules = len([d for d in self.details if d.status == ValidationStatus.PASS])
        failed_rules = len([d for d in self.details if d.status == ValidationStatus.FAIL])
        warnings = len([d for d in self.details if d.status == ValidationStatus.WARNING])

        return (
            f"{self.validation_type} validation: {self.status.value} "
            f"({passed_rules}/{total_rules} passed, {failed_rules} failed, {warnings} warnings)"
        )


class BaseValidator(ABC):
    """Base class for all validators."""

    def __init__(self, name: str, description: str = "") -> None:
        """Initialize the validator.

        Args:
            name: Validator name
            description: Validator description
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:  # noqa: ANN401
        """Perform validation on the provided data.

        Args:
            data: Data to validate
            context: Optional validation context

        Returns:
            ValidationResult with detailed results
        """
        raise NotImplementedError("Subclasses must implement the validate method")

    def _create_detail(
        self,
        rule_name: str,
        status: ValidationStatus,
        message: str,
        severity: str = "INFO",
        suggestion: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ValidationDetail:
        """Create a validation detail object."""
        return ValidationDetail(
            rule_name=rule_name,
            status=status,
            message=message,
            severity=severity,
            remediation_suggestion=suggestion,
            metadata=metadata or {},
        )

    def _measure_time(self, start_time: float) -> float:
        """Measure elapsed time in milliseconds."""
        return (time.time() - start_time) * 1000


class FileIntegrityValidator(BaseValidator):
    """Validator for file integrity checks."""

    def __init__(self) -> None:
        """Initialize the FileIntegrityValidator."""
        super().__init__(
            name="file_integrity_validator", description="Validates file existence, readability, and basic integrity"
        )

    async def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:  # noqa: ANN401
        """Validate file integrity."""
        start_time = time.time()
        details: List[ValidationDetail] = []

        try:
            file_path = str(data)

            # Check file existence
            if os.path.exists(file_path):
                details.append(self._create_detail("file_exists", ValidationStatus.PASS, f"File exists: {file_path}"))
            else:
                details.append(
                    self._create_detail(
                        "file_exists",
                        ValidationStatus.FAIL,
                        f"File does not exist: {file_path}",
                        "ERROR",
                        "Check file path and ensure file is accessible",
                    )
                )
                # Can't continue with other checks if file doesn't exist
                return ValidationResult(
                    validation_type="file_integrity",
                    status=ValidationStatus.FAIL,
                    details=details,
                    metrics={"file_path": file_path, "file_exists": False},
                    timestamp=datetime.now(),
                    execution_time_ms=self._measure_time(start_time),
                    validator_name=self.name,
                )

            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > 0:
                details.append(
                    self._create_detail("file_size", ValidationStatus.PASS, f"File has valid size: {file_size} bytes")
                )
            else:
                details.append(
                    self._create_detail(
                        "file_size", ValidationStatus.FAIL, "File is empty", "ERROR", "Ensure file contains data"
                    )
                )

            # Check file readability
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    # Try to read first few bytes
                    f.read(1024)
                details.append(self._create_detail("file_readable", ValidationStatus.PASS, "File is readable"))
            except PermissionError:
                details.append(
                    self._create_detail(
                        "file_readable",
                        ValidationStatus.FAIL,
                        "File is not readable due to permissions",
                        "ERROR",
                        "Check file permissions and user access rights",
                    )
                )
            except UnicodeDecodeError:
                details.append(
                    self._create_detail(
                        "file_readable",
                        ValidationStatus.WARNING,
                        "File may contain non-UTF-8 encoding",
                        "WARNING",
                        "Consider converting file to UTF-8 encoding",
                    )
                )

            # Determine overall status
            failed_checks = [d for d in details if d.status == ValidationStatus.FAIL]
            overall_status = ValidationStatus.FAIL if failed_checks else ValidationStatus.PASS

            return ValidationResult(
                validation_type="file_integrity",
                status=overall_status,
                details=details,
                metrics={
                    "file_path": file_path,
                    "file_size": file_size,
                    "file_exists": True,
                    "checks_performed": len(details),
                    "checks_passed": len([d for d in details if d.status == ValidationStatus.PASS]),
                },
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )

        except Exception as e:
            self.logger.error("Error during file integrity validation: %s", e)
            details.append(
                self._create_detail(
                    "validation_error",
                    ValidationStatus.FAIL,
                    f"Validation error: {str(e)}",
                    "ERROR",
                    "Check file path and format",
                )
            )

            return ValidationResult(
                validation_type="file_integrity",
                status=ValidationStatus.FAIL,
                details=details,
                metrics={"error": str(e)},
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )


class FormatComplianceValidator(BaseValidator):
    """Validator for format compliance checks."""

    def __init__(self) -> None:
        """Initialize the FormatComplianceValidator."""
        super().__init__(
            name="format_compliance_validator", description="Validates data format compliance (CSV, JSON, etc.)"
        )

    async def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:  # noqa: ANN401
        """Validate format compliance."""
        start_time = time.time()
        details: List[ValidationDetail] = []

        try:
            format_type = context.get("format", "unknown") if context else "unknown"

            if format_type.lower() == "csv" or (isinstance(data, str) and data.endswith(".csv")):
                return await self._validate_csv_format(data, details, start_time)
            elif format_type.lower() == "json" or (isinstance(data, str) and data.endswith(".json")):
                return await self._validate_json_format(data, details, start_time)
            elif isinstance(data, str):
                # Try to auto-detect format from content
                return await self._validate_auto_detect_format(data, details, start_time)
            else:
                details.append(
                    self._create_detail(
                        "format_detection", ValidationStatus.SKIP, f"Unknown format: {format_type}", "INFO"
                    )
                )

                return ValidationResult(
                    validation_type="format_compliance",
                    status=ValidationStatus.SKIP,
                    details=details,
                    metrics={"format": format_type},
                    timestamp=datetime.now(),
                    execution_time_ms=self._measure_time(start_time),
                    validator_name=self.name,
                )

        except Exception as e:
            self.logger.error("Error during format compliance validation: %s", e)
            details.append(
                self._create_detail("validation_error", ValidationStatus.FAIL, f"Validation error: {str(e)}", "ERROR")
            )

            return ValidationResult(
                validation_type="format_compliance",
                status=ValidationStatus.FAIL,
                details=details,
                metrics={"error": str(e)},
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )

    async def _validate_csv_format(
        self, data: str, details: List[ValidationDetail], start_time: float
    ) -> ValidationResult:
        """Validate CSV format."""
        try:
            if os.path.exists(data):
                with open(data, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = data

            # Parse CSV
            reader = csv.DictReader(io.StringIO(content))
            rows = list(reader)

            # Check if we have headers
            if reader.fieldnames:
                details.append(
                    self._create_detail(
                        "csv_headers", ValidationStatus.PASS, f"CSV has headers: {', '.join(reader.fieldnames)}"
                    )
                )
            else:
                details.append(
                    self._create_detail(
                        "csv_headers",
                        ValidationStatus.FAIL,
                        "CSV has no headers",
                        "ERROR",
                        "Add header row to CSV file",
                    )
                )

            # Check row count
            if rows:
                details.append(self._create_detail("csv_rows", ValidationStatus.PASS, f"CSV has {len(rows)} data rows"))
            else:
                details.append(
                    self._create_detail(
                        "csv_rows",
                        ValidationStatus.WARNING,
                        "CSV has no data rows",
                        "WARNING",
                        "Ensure CSV file contains data",
                    )
                )

            # Check for consistent column count
            if reader.fieldnames:
                expected_cols = len(reader.fieldnames)
                inconsistent_rows = 0
                for row in rows:
                    if len(row) != expected_cols:
                        inconsistent_rows += 1

                if inconsistent_rows == 0:
                    details.append(
                        self._create_detail(
                            "csv_consistency", ValidationStatus.PASS, "All rows have consistent column count"
                        )
                    )
                else:
                    details.append(
                        self._create_detail(
                            "csv_consistency",
                            ValidationStatus.WARNING,
                            f"{inconsistent_rows} rows have inconsistent column count",
                            "WARNING",
                            "Check for missing commas or extra columns",
                        )
                    )

            failed_checks = [d for d in details if d.status == ValidationStatus.FAIL]
            overall_status = ValidationStatus.FAIL if failed_checks else ValidationStatus.PASS

            return ValidationResult(
                validation_type="format_compliance",
                status=overall_status,
                details=details,
                metrics={
                    "format": "csv",
                    "headers": reader.fieldnames,
                    "row_count": len(rows),
                    "column_count": len(reader.fieldnames) if reader.fieldnames else 0,
                },
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )

        except Exception as e:
            details.append(
                self._create_detail(
                    "csv_parse_error",
                    ValidationStatus.FAIL,
                    f"CSV parsing error: {str(e)}",
                    "ERROR",
                    "Check CSV format and encoding",
                )
            )

            return ValidationResult(
                validation_type="format_compliance",
                status=ValidationStatus.FAIL,
                details=details,
                metrics={"format": "csv", "error": str(e)},
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )

    async def _validate_json_format(
        self, data: str, details: List[ValidationDetail], start_time: float
    ) -> ValidationResult:
        """Validate JSON format."""
        try:
            if os.path.exists(data):
                with open(data, "r", encoding="utf-8") as f:
                    content = f.read()
            else:
                content = data

            # Parse JSON
            parsed_json = json.loads(content)

            details.append(self._create_detail("json_parse", ValidationStatus.PASS, "JSON is valid and parseable"))

            # Check JSON structure
            if isinstance(parsed_json, dict):
                details.append(
                    self._create_detail(
                        "json_structure", ValidationStatus.PASS, f"JSON is a dictionary with {len(parsed_json)} keys"
                    )
                )
            elif isinstance(parsed_json, list):
                details.append(
                    self._create_detail(
                        "json_structure", ValidationStatus.PASS, f"JSON is an array with {len(parsed_json)} items"
                    )
                )
            else:
                details.append(
                    self._create_detail(
                        "json_structure", ValidationStatus.WARNING, "JSON is a primitive value", "WARNING"
                    )
                )

            return ValidationResult(
                validation_type="format_compliance",
                status=ValidationStatus.PASS,
                details=details,
                metrics={
                    "format": "json",
                    "type": type(parsed_json).__name__,
                    "size": len(parsed_json) if hasattr(parsed_json, "__len__") else 1,
                },
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )

        except json.JSONDecodeError as e:
            details.append(
                self._create_detail(
                    "json_parse_error",
                    ValidationStatus.FAIL,
                    f"JSON parsing error: {str(e)}",
                    "ERROR",
                    "Check JSON syntax and format",
                )
            )

            return ValidationResult(
                validation_type="format_compliance",
                status=ValidationStatus.FAIL,
                details=details,
                metrics={"format": "json", "error": str(e)},
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )

    async def _validate_auto_detect_format(
        self, data: str, details: List[ValidationDetail], start_time: float
    ) -> ValidationResult:
        """Auto-detect and validate format."""
        # Try JSON first
        try:
            json.loads(data)
            details.append(self._create_detail("format_detection", ValidationStatus.PASS, "Auto-detected JSON format"))
            return await self._validate_json_format(data, details, start_time)
        except json.JSONDecodeError:
            pass

        # Try CSV
        try:
            csv.reader(io.StringIO(data))
            details.append(self._create_detail("format_detection", ValidationStatus.PASS, "Auto-detected CSV format"))
            return await self._validate_csv_format(data, details, start_time)
        except Exception:
            pass

        # Unknown format
        details.append(
            self._create_detail(
                "format_detection",
                ValidationStatus.WARNING,
                "Could not auto-detect format",
                "WARNING",
                "Specify format explicitly",
            )
        )

        return ValidationResult(
            validation_type="format_compliance",
            status=ValidationStatus.WARNING,
            details=details,
            metrics={"format": "unknown"},
            timestamp=datetime.now(),
            execution_time_ms=self._measure_time(start_time),
            validator_name=self.name,
        )


class DataPreservationValidator(BaseValidator):
    """Validator for data preservation during conversion."""

    def __init__(self) -> None:
        """Initialize the DataPreservationValidator."""
        super().__init__(
            name="data_preservation_validator", description="Validates data preservation during conversion processes"
        )

    async def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:  # noqa: ANN401
        """Validate data preservation."""
        start_time = time.time()
        details: List[ValidationDetail] = []

        try:
            if not context or "original_data" not in context:
                details.append(
                    self._create_detail(
                        "context_check",
                        ValidationStatus.FAIL,
                        "Original data not provided in context",
                        "ERROR",
                        "Provide original data for comparison",
                    )
                )

                return ValidationResult(
                    validation_type="data_preservation",
                    status=ValidationStatus.FAIL,
                    details=details,
                    metrics={},
                    timestamp=datetime.now(),
                    execution_time_ms=self._measure_time(start_time),
                    validator_name=self.name,
                )

            original_data = context["original_data"]
            converted_data = data

            # Check record count preservation
            original_count = len(original_data) if hasattr(original_data, "__len__") else 1
            converted_count = len(converted_data) if hasattr(converted_data, "__len__") else 1

            if original_count == converted_count:
                details.append(
                    self._create_detail(
                        "record_count",
                        ValidationStatus.PASS,
                        f"Record count preserved: {original_count} -> {converted_count}",
                    )
                )
            else:
                details.append(
                    self._create_detail(
                        "record_count",
                        ValidationStatus.FAIL,
                        f"Record count mismatch: {original_count} -> {converted_count}",
                        "ERROR",
                        "Check conversion logic for data loss",
                    )
                )

            # Check data type preservation where applicable
            if isinstance(original_data, list) and isinstance(converted_data, list):
                # Sample check on first few items
                sample_size = min(5, len(original_data), len(converted_data))
                content_preserved = 0

                for i in range(sample_size):
                    orig_item = original_data[i]
                    conv_item = converted_data[i]

                    # Basic content comparison - in real implementation this would be more sophisticated
                    if isinstance(orig_item, dict) and isinstance(conv_item, dict):
                        # Check if some original content appears in converted content
                        orig_values = str(orig_item.values()) if orig_item else ""
                        conv_values = str(conv_item.values()) if conv_item else ""

                        if orig_values and any(str(v) in conv_values for v in orig_item.values() if str(v)):
                            content_preserved += 1
                    elif str(orig_item) in str(conv_item):
                        content_preserved += 1

                preservation_rate = content_preserved / sample_size if sample_size > 0 else 0

                if preservation_rate >= 0.8:  # 80% preservation threshold
                    details.append(
                        self._create_detail(
                            "content_preservation",
                            ValidationStatus.PASS,
                            f"Content preservation rate: {preservation_rate:.1%}",
                        )
                    )
                else:
                    details.append(
                        self._create_detail(
                            "content_preservation",
                            ValidationStatus.WARNING,
                            f"Low content preservation rate: {preservation_rate:.1%}",
                            "WARNING",
                            "Review conversion mapping and ensure data is properly transformed",
                        )
                    )

            failed_checks = [d for d in details if d.status == ValidationStatus.FAIL]
            overall_status = ValidationStatus.FAIL if failed_checks else ValidationStatus.PASS

            return ValidationResult(
                validation_type="data_preservation",
                status=overall_status,
                details=details,
                metrics={
                    "original_count": original_count,
                    "converted_count": converted_count,
                    "preservation_ratio": converted_count / original_count if original_count > 0 else 0,
                },
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )

        except Exception as e:
            self.logger.error("Error during data preservation validation: %s", e)
            details.append(
                self._create_detail("validation_error", ValidationStatus.FAIL, f"Validation error: {str(e)}", "ERROR")
            )

            return ValidationResult(
                validation_type="data_preservation",
                status=ValidationStatus.FAIL,
                details=details,
                metrics={"error": str(e)},
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )


class PerformanceValidator(BaseValidator):
    """Validator for performance metrics."""

    def __init__(self) -> None:
        """Initialize the PerformanceValidator."""
        super().__init__(name="performance_validator", description="Validates performance metrics against benchmarks")

    async def validate(self, data: Any, context: Optional[Dict[str, Any]] = None) -> ValidationResult:  # noqa: ANN401
        """Validate performance metrics."""
        start_time = time.time()
        details: List[ValidationDetail] = []

        try:
            metrics = data if isinstance(data, dict) else {}

            # Get benchmarks from context or use defaults
            benchmarks = context.get("benchmarks", {}) if context else {}
            dataset_type = context.get("dataset_type", "default") if context else "default"

            # Default benchmarks by dataset type (from issue requirements)
            default_benchmarks = {
                "OllaGen1": {"max_time_seconds": 600, "max_memory_mb": 2048},
                "Garak": {"max_time_seconds": 60, "max_memory_mb": 1024},
                "DocMath": {"max_time_seconds": 900, "max_memory_mb": 2048},
                "GraphWalk": {"max_time_seconds": 1800, "max_memory_mb": 2048},
                "ConfAIde": {"max_time_seconds": 120, "max_memory_mb": 512},
                "JudgeBench": {"max_time_seconds": 300, "max_memory_mb": 1024},
                "default": {"max_time_seconds": 300, "max_memory_mb": 1024},
            }

            benchmark = benchmarks or default_benchmarks.get(dataset_type, default_benchmarks["default"])

            # Validate processing time
            processing_time = metrics.get("processing_time_seconds", 0)
            max_time = benchmark.get("max_time_seconds", 300)

            if processing_time <= max_time:
                details.append(
                    self._create_detail(
                        "processing_time",
                        ValidationStatus.PASS,
                        f"Processing time within limit: {processing_time:.1f}s <= {max_time}s",
                    )
                )
            else:
                details.append(
                    self._create_detail(
                        "processing_time",
                        ValidationStatus.FAIL,
                        f"Processing time exceeded: {processing_time:.1f}s > {max_time}s",
                        "ERROR",
                        f"Optimize processing or increase time limit for {dataset_type} datasets",
                    )
                )

            # Validate memory usage
            memory_mb = metrics.get("memory_usage_mb", 0)
            max_memory = benchmark.get("max_memory_mb", 1024)

            if memory_mb <= max_memory:
                details.append(
                    self._create_detail(
                        "memory_usage",
                        ValidationStatus.PASS,
                        f"Memory usage within limit: {memory_mb:.1f}MB <= {max_memory}MB",
                    )
                )
            else:
                details.append(
                    self._create_detail(
                        "memory_usage",
                        ValidationStatus.FAIL,
                        f"Memory usage exceeded: {memory_mb:.1f}MB > {max_memory}MB",
                        "ERROR",
                        f"Optimize memory usage or increase limit for {dataset_type} datasets",
                    )
                )

            # Validate validation overhead (should be <5% of conversion time)
            validation_time = metrics.get("validation_time_seconds", 0)
            if processing_time > 0:
                overhead_percent = (validation_time / processing_time) * 100
                if overhead_percent <= 5.0:
                    details.append(
                        self._create_detail(
                            "validation_overhead",
                            ValidationStatus.PASS,
                            f"Validation overhead acceptable: {overhead_percent:.1f}%",
                        )
                    )
                else:
                    details.append(
                        self._create_detail(
                            "validation_overhead",
                            ValidationStatus.WARNING,
                            f"High validation overhead: {overhead_percent:.1f}%",
                            "WARNING",
                            "Consider optimizing validation process or using quick validation level",
                        )
                    )

            # Get current system metrics
            process = psutil.Process()
            current_memory_mb = process.memory_info().rss / 1024 / 1024

            details.append(
                self._create_detail(
                    "current_memory", ValidationStatus.PASS, f"Current memory usage: {current_memory_mb:.1f}MB", "INFO"
                )
            )

            failed_checks = [d for d in details if d.status == ValidationStatus.FAIL]
            overall_status = ValidationStatus.FAIL if failed_checks else ValidationStatus.PASS

            return ValidationResult(
                validation_type="performance",
                status=overall_status,
                details=details,
                metrics={
                    "dataset_type": dataset_type,
                    "processing_time_seconds": processing_time,
                    "memory_usage_mb": memory_mb,
                    "validation_time_seconds": validation_time,
                    "current_memory_mb": current_memory_mb,
                    "benchmarks": benchmark,
                    "validation_overhead_percent": (
                        (validation_time / processing_time) * 100 if processing_time > 0 else 0
                    ),
                },
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )

        except Exception as e:
            self.logger.error("Error during performance validation: %s", e)
            details.append(
                self._create_detail("validation_error", ValidationStatus.FAIL, f"Validation error: {str(e)}", "ERROR")
            )

            return ValidationResult(
                validation_type="performance",
                status=ValidationStatus.FAIL,
                details=details,
                metrics={"error": str(e)},
                timestamp=datetime.now(),
                execution_time_ms=self._measure_time(start_time),
                validator_name=self.name,
            )


class ValidationFramework:
    """Main validation framework that orchestrates all validators."""

    def __init__(self) -> None:
        """Initialize the validation framework."""
        self.logger = logging.getLogger(__name__)
        self.validators = {}
        self._register_default_validators()

    def _register_default_validators(self) -> None:
        """Register default validators."""
        self.validators = {
            "file_integrity": FileIntegrityValidator(),
            "format_compliance": FormatComplianceValidator(),
            "data_preservation": DataPreservationValidator(),
            "performance": PerformanceValidator(),
        }

    def register_validator(self, name: str, validator: BaseValidator) -> None:
        """Register a custom validator."""
        self.validators[name] = validator
        self.logger.info("Registered validator: %s", name)

    async def validate_source_data(
        self, file_path: str, validation_level: ValidationLevel = ValidationLevel.FULL
    ) -> ValidationResult:
        """Pre-conversion validation of source data."""
        self.logger.info("Starting source data validation: %s", file_path)

        validators_to_run = []

        if validation_level in [ValidationLevel.QUICK, ValidationLevel.FULL, ValidationLevel.DEEP]:
            validators_to_run.extend(["file_integrity", "format_compliance"])

        return await self._run_validators(
            validators_to_run, file_path, {"validation_category": "source_data", "file_path": file_path}
        )

    async def validate_conversion_result(
        self,
        original_data: Any,  # noqa: ANN401
        converted_data: Any,  # noqa: ANN401
        validation_level: ValidationLevel = ValidationLevel.FULL,  # noqa: ANN401
    ) -> ValidationResult:
        """Post-conversion validation of conversion results."""
        self.logger.info("Starting conversion result validation")

        validators_to_run = []

        if validation_level in [ValidationLevel.FULL, ValidationLevel.DEEP]:
            validators_to_run.append("data_preservation")

        return await self._run_validators(
            validators_to_run,
            converted_data,
            {"validation_category": "conversion_result", "original_data": original_data},
        )

    async def validate_performance(
        self,
        metrics: Dict[str, Any],
        dataset_type: str = "default",
        validation_level: ValidationLevel = ValidationLevel.FULL,
    ) -> ValidationResult:
        """Validate performance against benchmarks."""
        self.logger.info("Starting performance validation for %s", dataset_type)

        if validation_level in [ValidationLevel.FULL, ValidationLevel.DEEP]:
            return await self._run_validators(
                ["performance"], metrics, {"validation_category": "performance", "dataset_type": dataset_type}
            )
        else:
            # Skip performance validation for quick level
            return ValidationResult(
                validation_type="performance",
                status=ValidationStatus.SKIP,
                details=[
                    ValidationDetail(
                        rule_name="performance_skip",
                        status=ValidationStatus.SKIP,
                        message="Performance validation skipped for quick level",
                        severity="INFO",
                    )
                ],
                metrics={"skipped": True},
                timestamp=datetime.now(),
                validator_name="performance_validator",
            )

    async def _run_validators(
        self, validator_names: List[str], data: Any, context: Dict[str, Any]  # noqa: ANN401
    ) -> ValidationResult:  # noqa: ANN401
        """Run multiple validators and aggregate results."""
        start_time = time.time()
        all_details = []
        all_metrics = {}
        overall_status = ValidationStatus.PASS

        for validator_name in validator_names:
            if validator_name not in self.validators:
                self.logger.warning("Validator not found: %s", validator_name)
                continue

            try:
                validator = self.validators[validator_name]
                result = await validator.validate(data, context)

                all_details.extend(result.details)
                all_metrics.update({f"{validator_name}_{k}": v for k, v in result.metrics.items()})

                # Aggregate status - fail takes precedence
                if result.status == ValidationStatus.FAIL:
                    overall_status = ValidationStatus.FAIL
                elif result.status == ValidationStatus.WARNING and overall_status == ValidationStatus.PASS:
                    overall_status = ValidationStatus.WARNING

            except Exception as e:
                self.logger.error("Error running validator %s: %s", validator_name, e)
                all_details.append(
                    ValidationDetail(
                        rule_name=f"{validator_name}_error",
                        status=ValidationStatus.FAIL,
                        message=f"Validator error: {str(e)}",
                        severity="ERROR",
                    )
                )
                overall_status = ValidationStatus.FAIL

        return ValidationResult(
            validation_type=context.get("validation_category", "unknown"),
            status=overall_status,
            details=all_details,
            metrics=all_metrics,
            timestamp=datetime.now(),
            execution_time_ms=(time.time() - start_time) * 1000,
            validator_name="validation_framework",
        )
