# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Garak Dataset Service for API integration.

Provides service-layer functionality for Garak dataset conversion with
file validation, metadata management, and integration with the broader
ViolentUTF system.

SECURITY: All operations include comprehensive validation and sanitization
to prevent injection attacks and ensure data integrity.
"""
import os
from pathlib import Path
from typing import Any, Dict

from app.core.converters.garak_converter import GarakDatasetConverter
from app.core.validation import sanitize_string
from app.schemas.garak_datasets import (
    GarakConversionResult,
    SingleFileConversionResult,
)


class GarakDatasetService:
    """Service class for Garak dataset operations.

    Provides high-level interface for file validation, conversion,
    and metadata management of Garak datasets.
    """

    def __init__(self) -> None:
        """Initialize the Garak dataset service."""
        self.converter = GarakDatasetConverter()
        self.supported_file_types = [".txt", ".text"]
        self.max_file_size_mb = 10

    async def validate_file_for_conversion(self, file_path: str) -> bool:
        """Validate if a file is suitable for Garak conversion.

        Args:
            file_path: Path to the file to validate

        Returns:
            True if file is valid for conversion, False otherwise
        """
        try:
            # Sanitize path
            file_path = sanitize_string(file_path)

            # Check if file exists
            if not os.path.exists(file_path):
                return False

            # Check if it's a file (not directory)
            if not os.path.isfile(file_path):
                return False

            # Check file extension
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_file_types:
                return False

            # Check file size
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return False

            # Try to read file content to ensure it's readable
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(1000)  # Read first 1000 chars for validation
                if not content.strip():
                    return False

            return True

        except Exception:
            return False

    async def convert_garak_file(self, file_path: str) -> GarakConversionResult:
        """Convert a single Garak file through the service layer.

        Args:
            file_path: Path to the Garak file to convert

        Returns:
            GarakConversionResult with service-level metadata
        """
        # Validate file first
        is_valid = await self.validate_file_for_conversion(file_path)
        if not is_valid:
            return GarakConversionResult(
                success=False,
                dataset=None,
                file_results=[],
                total_prompts_converted=0,
                conversion_time_seconds=0.0,
                metadata={"error": "File validation failed", "file_path": file_path},
                errors=["File validation failed - file may not exist, be too large, or have invalid format"],
            )

        # Convert file using the converter
        conversion_result = await self.converter.convert_file(file_path)

        # Prepare service-level result
        if conversion_result.success:
            total_prompts = len(conversion_result.dataset["prompts"]) if conversion_result.dataset else 0

            service_metadata = {
                "conversion_strategy": "single_file",
                "file_analysis": {
                    "file_type": conversion_result.file_analysis.file_type.value,
                    "content_type": conversion_result.file_analysis.content_type,
                    "prompt_count": conversion_result.file_analysis.prompt_count,
                    "has_template_variables": conversion_result.file_analysis.has_template_variables,
                    "confidence_score": conversion_result.file_analysis.confidence_score,
                },
                "quality_metrics": {
                    "conversion_time_seconds": conversion_result.conversion_time_seconds,
                    "prompts_generated": total_prompts,
                    "attack_classifications": len(conversion_result.attack_classifications),
                },
            }

            return GarakConversionResult(
                success=True,
                dataset=conversion_result.dataset,
                file_results=[self._convert_to_dict(conversion_result)],
                total_prompts_converted=total_prompts,
                conversion_time_seconds=conversion_result.conversion_time_seconds,
                metadata=service_metadata,
                validation_result=None,  # Would be populated in full implementation
                errors=[],
                warnings=[],
            )
        else:
            return GarakConversionResult(
                success=False,
                dataset=None,
                file_results=[self._convert_to_dict(conversion_result)],
                total_prompts_converted=0,
                conversion_time_seconds=conversion_result.conversion_time_seconds,
                metadata={"conversion_strategy": "single_file", "error": conversion_result.error_message},
                errors=[conversion_result.error_message or "Unknown conversion error"],
            )

    def _convert_to_dict(self, result: SingleFileConversionResult) -> Dict[str, Any]:
        """Convert SingleFileConversionResult to dictionary for JSON serialization."""
        return {
            "file_path": result.file_path,
            "success": result.success,
            "dataset": result.dataset,
            "file_analysis": {
                "file_type": result.file_analysis.file_type.value,
                "content_type": result.file_analysis.content_type,
                "prompt_count": result.file_analysis.prompt_count,
                "has_template_variables": result.file_analysis.has_template_variables,
                "template_variables": result.file_analysis.template_variables,
                "detected_patterns": result.file_analysis.detected_patterns,
                "confidence_score": result.file_analysis.confidence_score,
                "analysis_metadata": result.file_analysis.analysis_metadata,
            },
            "template_info": (
                {
                    "variables": result.template_info.variables,
                    "variable_count": result.template_info.variable_count,
                    "extraction_success": result.template_info.extraction_success,
                    "has_nested_variables": result.template_info.has_nested_variables,
                    "malformed_patterns": result.template_info.malformed_patterns,
                    "variable_metadata": result.template_info.variable_metadata,
                }
                if result.template_info
                else None
            ),
            "attack_classifications": [
                {
                    "attack_type": attack.attack_type.value,
                    "harm_categories": [cat.value for cat in attack.harm_categories],
                    "confidence_score": attack.confidence_score,
                    "severity_level": attack.severity_level,
                    "detection_patterns": attack.detection_patterns,
                    "classification_metadata": attack.classification_metadata,
                }
                for attack in result.attack_classifications
            ],
            "conversion_time_seconds": result.conversion_time_seconds,
            "error_message": result.error_message,
        }
