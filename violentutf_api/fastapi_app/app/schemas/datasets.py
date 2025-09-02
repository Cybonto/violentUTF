# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for dataset management API endpoints.

SECURITY: Enhanced with comprehensive input validation to prevent injection attacks.
"""
# pylint: disable=no-self-argument  # Pydantic validators use cls, not self
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Type

from app.core.validation import (
    SecurityLimits,
    ValidationPatterns,
    sanitize_string,
    validate_json_data,
    validate_url,
)
from pydantic import BaseModel, Field, field_validator


class DatasetSourceType(str, Enum):
    """Dataset source types."""

    NATIVE = "native"

    LOCAL = "local"
    ONLINE = "online"
    MEMORY = "memory"
    COMBINATION = "combination"
    TRANSFORM = "transform"
    CONVERTER = "converter"  # Added for datasets created by converters


class DatasetType(BaseModel):
    """Dataset type information."""

    name: str = Field(..., description="Dataset type name")

    description: str = Field(..., description="Description of the dataset")
    category: str = Field(..., description="Category of the dataset")
    config_required: bool = Field(default=False, description="Whether configuration is required")
    available_configs: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Available configuration options"
    )


class SeedPromptInfo(BaseModel):
    """Seed prompt information."""

    id: Optional[str] = Field(default=None, description="Prompt unique identifier")

    value: str = Field(
        ...,
        min_length=1,
        max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH,
        description="Prompt text content",
    )
    data_type: str = Field(default="text", max_length=50, description="Data type of the prompt")
    name: Optional[str] = Field(
        default=None,
        max_length=SecurityLimits.MAX_NAME_LENGTH,
        description="Prompt name",
    )
    dataset_name: Optional[str] = Field(
        default=None,
        max_length=SecurityLimits.MAX_NAME_LENGTH,
        description="Dataset this prompt belongs to",
    )
    harm_categories: Optional[List[str]] = Field(default=None, description="Harm categories", max_length=20)
    description: Optional[str] = Field(
        default=None,
        max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH,
        description="Prompt description",
    )
    metadata: Optional[Dict[str, object]] = Field(default=None, description="Additional metadata")

    @field_validator("value")
    @classmethod
    def validate_value_field(cls: Type["SeedPromptInfo"], v: str) -> str:
        """Validate prompt value."""
        return sanitize_string(v)

    @field_validator("name")
    @classmethod
    def validate_name_field(cls: Type["SeedPromptInfo"], v: Optional[str]) -> Optional[str]:
        """Validate prompt name."""
        if v is not None:

            v = sanitize_string(v)
            if not ValidationPatterns.SAFE_NAME.match(v):
                raise ValueError("Name contains invalid characters")
        return v

    @field_validator("harm_categories")
    @classmethod
    def validate_harm_categories_field(cls: Type["SeedPromptInfo"], v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate harm categories."""
        if v is not None:

            validated = []
            for category in v:
                if not isinstance(category, str):
                    raise ValueError("Harm category must be a string")
                category = sanitize_string(category).lower()
                if category and len(category) <= 100:
                    validated.append(category)
            return validated
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_field(
        cls: Type["SeedPromptInfo"], v: Optional[Dict[str, object]]
    ) -> Optional[Dict[str, object]]:
        """Validate metadata."""
        if v is not None:
            return validate_json_data(v, max_depth=3)
        return v


class DatasetInfo(BaseModel):
    """Dataset information."""

    id: str = Field(..., description="Dataset unique identifier")

    name: str = Field(..., description="Dataset name")
    source_type: DatasetSourceType = Field(..., description="Dataset source type")
    prompt_count: int = Field(..., description="Number of prompts in dataset")
    prompts: List[SeedPromptInfo] = Field(..., description="Dataset prompts")
    config: Optional[Dict[str, object]] = Field(default=None, description="Dataset configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    created_by: str = Field(..., description="User who created the dataset")
    metadata: Optional[Dict[str, object]] = Field(default=None, description="Additional metadata")


class DatasetCreateRequest(BaseModel):
    """Request model for creating a dataset."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=SecurityLimits.MAX_NAME_LENGTH,
        description="Dataset name",
    )

    source_type: DatasetSourceType = Field(..., description="Dataset source type")
    config: Optional[Dict[str, object]] = Field(default=None, description="Dataset configuration")

    # For native datasets
    dataset_type: Optional[str] = Field(default=None, max_length=100, description="Native dataset type name")

    # For local/online datasets
    file_content: Optional[str] = Field(default=None, description="File content (base64 encoded)")
    file_type: Optional[str] = Field(default=None, max_length=20, description="File type (csv, json, etc.)")
    url: Optional[str] = Field(default=None, max_length=2048, description="URL for online datasets")
    field_mappings: Optional[Dict[str, str]] = Field(default=None, description="Field mappings for custom datasets")

    # For combination datasets
    dataset_ids: Optional[List[str]] = Field(default=None, description="Dataset IDs to combine", max_length=20)

    # For transformation datasets
    source_dataset_id: Optional[str] = Field(
        default=None, max_length=100, description="Source dataset ID for transformation"
    )
    template: Optional[str] = Field(
        default=None,
        max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH,
        description="Transformation template",
    )

    @field_validator("name")
    @classmethod
    def validate_name_field(cls: Type["DatasetCreateRequest"], v: Optional[str]) -> Optional[str]:
        """Validate dataset name."""
        if v is None:

            return v
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_NAME.match(v):
            raise ValueError(
                "Name must contain only alphanumeric characters, spaces, underscores, hyphens, dots, and parentheses"
            )
        return v

    @field_validator("dataset_type")
    @classmethod
    def validate_dataset_type_field(cls: Type["DatasetCreateRequest"], v: Optional[str]) -> Optional[str]:
        """Validate dataset type."""
        if v is not None:

            v = sanitize_string(v)
            if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
                raise ValueError("Dataset type must contain only alphanumeric characters, underscores, and hyphens")
        return v

    @field_validator("url")
    @classmethod
    def validate_url_field(cls: Type["DatasetCreateRequest"], v: Optional[str]) -> Optional[str]:
        """Validate URL."""
        if v is not None:

            return str(validate_url(v))
        return v

    @field_validator("file_type")
    @classmethod
    def validate_file_type_field(cls: Type["DatasetCreateRequest"], v: Optional[str]) -> Optional[str]:
        """Validate file type."""
        if v is not None:

            v = sanitize_string(v).lower()
            allowed_types = ["csv", "json", "txt", "yaml", "yml", "tsv"]
            if v not in allowed_types:
                raise ValueError(f"File type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator("config")
    @classmethod
    def validate_config_field(
        cls: Type["DatasetCreateRequest"], v: Optional[Dict[str, object]]
    ) -> Optional[Dict[str, object]]:
        """Validate configuration."""
        if v is not None:

            return validate_json_data(v, max_depth=3)
        return v

    @field_validator("field_mappings")
    @classmethod
    def validate_field_mappings_field(
        cls: Type["DatasetCreateRequest"], v: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """Validate field mappings."""
        if v is not None:

            if len(v) > 50:
                raise ValueError("Too many field mappings")
            validated = {}
            for key, value in v.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError("Field mapping keys and values must be strings")
                key = sanitize_string(key)
                value = sanitize_string(value)
                if len(key) > 100 or len(value) > 100:
                    raise ValueError("Field mapping keys/values too long")
                validated[key] = value
            return validated
        return v

    @field_validator("dataset_ids")
    @classmethod
    def validate_dataset_ids_field(cls: Type["DatasetCreateRequest"], v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate dataset IDs list."""
        if v is not None:

            validated = []
            for dataset_id in v:
                if not isinstance(dataset_id, str):
                    raise ValueError("Dataset ID must be a string")
                dataset_id = sanitize_string(dataset_id)
                if len(dataset_id) > 100:
                    raise ValueError("Dataset ID too long")
                validated.append(dataset_id)
            return validated
        return v

    @field_validator("template")
    @classmethod
    def validate_template_field(cls: Type["DatasetCreateRequest"], v: Optional[str]) -> Optional[str]:
        """Validate transformation template."""
        if v is not None:

            return str(sanitize_string(v))
        return v

    @field_validator("dataset_type")
    @classmethod
    def validate_native_dataset(cls: Type["DatasetCreateRequest"], v: object, values: Dict[str, object]) -> str:
        """Validate native dataset."""
        if values.get("source_type") == DatasetSourceType.NATIVE and not v:

            raise ValueError("dataset_type is required for native datasets")
        return str(v)

    @field_validator("url")
    @classmethod
    def validate_online_dataset(cls: Type["DatasetCreateRequest"], v: object, values: Dict[str, object]) -> str:
        """Validate online dataset."""
        if values.get("source_type") == DatasetSourceType.ONLINE and not v:

            raise ValueError("url is required for online datasets")
        return str(v)


class DatasetUpdateRequest(BaseModel):
    """Request model for updating a dataset."""

    name: Optional[str] = Field(default=None, description="New dataset name")

    config: Optional[Dict[str, object]] = Field(default=None, description="Updated configuration")
    metadata: Optional[Dict[str, object]] = Field(default=None, description="Updated metadata")

    # Save functionality (replaces the deprecated POST /{dataset_id}/save endpoint)
    save_to_session: Optional[bool] = Field(default=None, description="Save to current session")
    save_to_memory: Optional[bool] = Field(default=None, description="Save to PyRIT memory")
    overwrite: Optional[bool] = Field(default=False, description="Whether to overwrite if exists")

    @field_validator("name")
    @classmethod
    def validate_name_field(cls: Type["DatasetUpdateRequest"], v: Optional[str]) -> Optional[str]:
        """Validate dataset name."""
        if v is not None:

            v = sanitize_string(v)
            if not ValidationPatterns.SAFE_NAME.match(v):
                raise ValueError(
                    "Name must contain only alphanumeric characters, spaces, underscores, "
                    "hyphens, dots, and parentheses"
                )
        return v


class DatasetTransformRequest(BaseModel):
    """Request model for transforming a dataset."""

    template: str = Field(
        ...,
        min_length=1,
        max_length=SecurityLimits.MAX_DESCRIPTION_LENGTH,
        description="Transformation template",
    )
    template_type: str = Field(
        default="custom",
        max_length=50,
        description="Type of template (custom, existing)",
    )
    template_variables: Optional[Dict[str, object]] = Field(default=None, description="Template variables")

    @field_validator("template")
    @classmethod
    def validate_template_field(cls: Type["DatasetTransformRequest"], v: Optional[str]) -> Optional[str]:
        """Validate transformation template."""
        if v is None:

            return v
        return sanitize_string(v)

    @field_validator("template_type")
    @classmethod
    def validate_template_type_field(cls: Type["DatasetTransformRequest"], v: str) -> str:
        """Validate template type."""
        v = sanitize_string(v).lower()

        allowed_types = ["custom", "existing", "predefined"]
        if v not in allowed_types:
            raise ValueError(f"Template type must be one of: {', '.join(allowed_types)}")
        return v

    @field_validator("template_variables")
    @classmethod
    def validate_template_variables_field(
        cls: Type["DatasetTransformRequest"], v: Optional[Dict[str, object]]
    ) -> Optional[Dict[str, object]]:
        """Validate template variables."""
        if v is not None:

            return validate_json_data(v, max_depth=2)
        return v


class DatasetTestRequest(BaseModel):
    """Request model for testing a dataset."""

    generator_id: str = Field(..., description="Generator ID to test with")

    num_samples: int = Field(default=3, ge=1, le=10, description="Number of samples to test")
    save_results: bool = Field(default=True, description="Whether to save test results to memory")


class DatasetSaveRequest(BaseModel):
    """Request model for saving a dataset."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=SecurityLimits.MAX_NAME_LENGTH,
        description="Name to save the dataset under",
    )
    save_to_session: bool = Field(default=True, description="Save to current session")
    save_to_memory: bool = Field(default=True, description="Save to PyRIT memory")
    overwrite: bool = Field(default=False, description="Whether to overwrite if exists")

    @field_validator("name")
    @classmethod
    def validate_name_field(cls: Type["DatasetSaveRequest"], v: Optional[str]) -> Optional[str]:
        """Validate dataset save name."""
        if v is None:

            return v
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError("Name must contain only alphanumeric characters, underscores, and hyphens")
        return v


class DatasetTestResult(BaseModel):
    """Dataset test result."""

    prompt_id: str = Field(..., description="Prompt ID that was tested")

    prompt_value: str = Field(..., description="Prompt text")
    response: Optional[str] = Field(default=None, description="Generator response")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    response_time_ms: int = Field(..., description="Response time in milliseconds")
    success: bool = Field(..., description="Whether the test was successful")


class DatasetTestResponse(BaseModel):
    """Response model for dataset testing."""

    dataset_id: str = Field(..., description="Dataset ID that was tested")

    generator_id: str = Field(..., description="Generator ID used for testing")
    num_samples: int = Field(..., description="Number of samples tested")
    results: List[DatasetTestResult] = Field(..., description="Test results")
    success_rate: float = Field(..., description="Success rate (0.0 to 1.0)")
    total_time_ms: int = Field(..., description="Total test time in milliseconds")
    test_time: datetime = Field(..., description="Test execution timestamp")


class DatasetTypesResponse(BaseModel):
    """Response model for dataset types list."""

    dataset_types: List[DatasetType] = Field(..., description="Available dataset types")

    total: int = Field(..., description="Total number of dataset types")


class DatasetsListResponse(BaseModel):
    """Response model for datasets list."""

    datasets: List[DatasetInfo] = Field(..., description="List of datasets")

    total: int = Field(..., description="Total number of datasets")
    session_count: int = Field(..., description="Number of session datasets")
    memory_count: int = Field(..., description="Number of memory datasets")


class DatasetCreateResponse(BaseModel):
    """Response model for dataset creation."""

    dataset: DatasetInfo = Field(..., description="Created dataset information")

    message: str = Field(..., description="Success message")


class DatasetUpdateResponse(BaseModel):
    """Response model for dataset update/save operations."""

    dataset: DatasetInfo = Field(..., description="Updated dataset information")

    message: str = Field(..., description="Update result message")

    # Save operation results (when save parameters are included in PUT request)
    saved_to_session: Optional[bool] = Field(default=None, description="Whether saved to session")
    saved_to_memory: Optional[bool] = Field(default=None, description="Whether saved to PyRIT memory")
    saved_at: Optional[datetime] = Field(default=None, description="Save timestamp")


class DatasetSaveResponse(BaseModel):
    """Response model for dataset saving (DEPRECATED: Use DatasetUpdateResponse with PUT /{dataset_id})."""

    dataset_id: str = Field(..., description="Dataset ID")

    saved_to_session: bool = Field(..., description="Whether saved to session")
    saved_to_memory: bool = Field(..., description="Whether saved to PyRIT memory")
    message: str = Field(..., description="Save result message")
    saved_at: datetime = Field(..., description="Save timestamp")


class DatasetTransformResponse(BaseModel):
    """Response model for dataset transformation."""

    original_dataset_id: str = Field(..., description="Original dataset ID")

    transformed_dataset: DatasetInfo = Field(..., description="Transformed dataset")
    transform_summary: str = Field(..., description="Summary of transformation applied")


class MemoryDatasetInfo(BaseModel):
    """Information about datasets saved in PyRIT memory."""

    dataset_name: str = Field(..., description="Dataset name")

    prompt_count: int = Field(..., description="Number of prompts")
    created_by: Optional[str] = Field(default=None, description="Creator information")
    first_prompt_preview: Optional[str] = Field(default=None, description="Preview of first prompt")


class MemoryDatasetsResponse(BaseModel):
    """Response model for PyRIT memory datasets."""

    datasets: List[MemoryDatasetInfo] = Field(..., description="Datasets in PyRIT memory")

    total: int = Field(..., description="Total number of memory datasets")
    total_prompts: int = Field(..., description="Total prompts across all datasets")


class DatasetFieldMappingRequest(BaseModel):
    """Request model for dataset field mapping."""

    file_content: str = Field(..., description="File content (base64 encoded)")

    file_type: str = Field(..., description="File type (csv, json, etc.)")


class DatasetFieldMappingResponse(BaseModel):
    """Response model for dataset field mapping."""

    available_fields: List[str] = Field(..., description="Available fields in the dataset")

    required_fields: List[str] = Field(..., description="Required fields for SeedPrompt")
    preview_data: List[Dict[str, object]] = Field(..., description="Preview of the data")
    total_rows: int = Field(..., description="Total number of rows")


class DatasetDeleteResponse(BaseModel):
    """Response model for dataset deletion."""

    success: bool = Field(..., description="Whether deletion was successful")

    message: str = Field(..., description="Deletion result message")
    deleted_from_session: bool = Field(..., description="Whether deleted from session")
    deleted_from_memory: bool = Field(..., description="Whether deleted from memory")
    deleted_at: datetime = Field(..., description="Deletion timestamp")


# Error response models


class DatasetError(BaseModel):
    """Error response for dataset operations."""

    error: str = Field(..., description="Error message")

    details: Optional[str] = Field(default=None, description="Additional error details")
    dataset_name: Optional[str] = Field(default=None, description="Dataset name if applicable")
    error_code: Optional[str] = Field(default=None, description="Error code for programmatic handling")
    suggestions: Optional[List[str]] = Field(default=None, description="Suggested fixes or alternatives")


class DatasetValidationError(BaseModel):
    """Validation error response."""

    error: str = Field(..., description="Validation error message")

    field: str = Field(..., description="Field that failed validation")
    value: object = Field(..., description="Invalid value provided")
    expected: Optional[str] = Field(default=None, description="Expected value format")


# Helper models for complex operations


class DatasetPreviewRequest(BaseModel):
    """Request model for previewing a dataset before creation."""

    source_type: DatasetSourceType = Field(..., description="Dataset source type")

    config: Optional[Dict[str, object]] = Field(default=None, description="Dataset configuration")
    dataset_type: Optional[str] = Field(default=None, description="Native dataset type")
    url: Optional[str] = Field(default=None, description="URL for online datasets")
    file_content: Optional[str] = Field(default=None, description="File content for local datasets")


class DatasetPreviewResponse(BaseModel):
    """Response model for dataset preview."""

    preview_prompts: List[SeedPromptInfo] = Field(..., description="Preview of dataset prompts")

    total_prompts: int = Field(..., description="Total number of prompts available")
    dataset_info: Dict[str, object] = Field(..., description="Additional dataset information")
    warnings: Optional[List[str]] = Field(default=None, description="Any warnings about the dataset")
