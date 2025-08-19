# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Pydantic schemas for generator management API endpoints.

SECURITY: Enhanced with comprehensive input validation to prevent injection attacks
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.core.validation import (
    SecurityLimits,
    ValidationPatterns,
    create_validation_error,
    sanitize_string,
    validate_generator_parameters,
)
from pydantic import BaseModel, Field, validator


class GeneratorType(BaseModel):
    """Generator type information."""

    name: str = Field(..., description="Generator type name")
    description: str = Field(..., description="Description of the generator type")
    category: str = Field(..., description="Category of the generator")


class GeneratorParameter(BaseModel):
    """Parameter definition for a generator type."""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (str, int, float, bool, dict, list, selectbox)")
    description: str = Field(..., description="Parameter description")
    required: bool = Field(default=False, description="Whether the parameter is required")
    default: Any = Field(default=None, description="Default value for the parameter")
    options: Optional[List[str]] = Field(default=None, description="Available options for selectbox type")
    category: Optional[str] = Field(default=None, description="Parameter category for grouping")
    step: Optional[float] = Field(default=None, description="Step size for numeric parameters")


class GeneratorCreateRequest(BaseModel):
    """Request model for creating a new generator."""

    name: str = Field(..., min_length=3, max_length=100, description="Unique generator name")
    type: str = Field(..., min_length=3, max_length=50, description="Generator type")
    parameters: Dict[str, Any] = Field(..., description="Generator configuration parameters")

    @validator("name")
    def validate_name_field(cls: type["GeneratorCreateRequest"], v: Any) -> bool:
        """Validate generator name."""
        v = sanitize_string(v)
        if not ValidationPatterns.GENERATOR_NAME.match(v):
            raise ValueError("Name must contain only alphanumeric characters, dots, underscores, and hyphens")
        return v

    @validator("type")
    def validate_type_field(cls: type["GeneratorCreateRequest"], v: Any) -> bool:
        """Validate generator type."""
        v = sanitize_string(v)
        if not ValidationPatterns.GENERATOR_TYPE.match(v):
            raise ValueError("Type must contain only alphanumeric characters, spaces, underscores, and hyphens")
        return v

    @validator("parameters")
    def validate_parameters_field(cls: type["GeneratorCreateRequest"], v: Any) -> bool:
        """Validate generator parameters."""
        return validate_generator_parameters(v)


class GeneratorUpdateRequest(BaseModel):
    """Request model for updating a generator."""

    name: Optional[str] = Field(default=None, description="New generator name")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Updated parameters")

    @validator("name")
    def validate_name_field(cls: type["GeneratorUpdateRequest"], v: Any) -> bool:
        """Validate generator name if provided."""
        if v is not None:
            v = sanitize_string(v)
            if not ValidationPatterns.GENERATOR_NAME.match(v):
                raise ValueError("Name must contain only alphanumeric characters, dots, underscores, and hyphens")
        return v


class GeneratorInfo(BaseModel):
    """Generator information response."""

    id: str = Field(..., description="Generator unique identifier")
    name: str = Field(..., description="Generator name")
    type: str = Field(..., description="Generator type")
    status: str = Field(..., description="Generator status (ready, failed, testing)")
    parameters: Dict[str, Any] = Field(..., description="Generator configuration parameters")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_test_result: Optional[str] = Field(default=None, description="Last test result")
    last_test_time: Optional[datetime] = Field(default=None, description="Last test timestamp")


class GeneratorTypesResponse(BaseModel):
    """Response model for generator types list."""

    generator_types: List[str] = Field(..., description="List of available generator types")
    total: int = Field(..., description="Total number of generator types")


class GeneratorParametersResponse(BaseModel):
    """Response model for generator type parameters."""

    generator_type: str = Field(..., description="Generator type name")
    parameters: List[GeneratorParameter] = Field(..., description="Parameter definitions")


class GeneratorsListResponse(BaseModel):
    """Response model for generators list."""

    generators: List[GeneratorInfo] = Field(..., description="List of configured generators")
    total: int = Field(..., description="Total number of generators")


class APIXModelsResponse(BaseModel):
    """Response model for APISIX AI Gateway models."""

    provider: str = Field(..., description="AI provider name")
    models: List[str] = Field(..., description="Available models for the provider")
    total: int = Field(..., description="Total number of models")


class GeneratorDeleteResponse(BaseModel):
    """Response model for generator deletion."""

    success: bool = Field(..., description="Whether the deletion was successful")
    message: str = Field(..., description="Deletion result message")
    deleted_at: datetime = Field(..., description="Deletion timestamp")


# Error response models
class GeneratorError(BaseModel):
    """Error response for generator operations."""

    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(default=None, description="Additional error details")
    generator_name: Optional[str] = Field(default=None, description="Generator name if applicable")
    error_code: Optional[str] = Field(default=None, description="Error code for programmatic handling")


class ValidationError(BaseModel):
    """Validation error response."""

    error: str = Field(..., description="Validation error message")
    field: str = Field(..., description="Field that failed validation")
