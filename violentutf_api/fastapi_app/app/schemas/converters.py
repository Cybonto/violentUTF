"""
Pydantic schemas for converter management API
Supports the 3_Configure_Converters.py page functionality
SECURITY: Enhanced with comprehensive input validation to prevent injection attacks
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from app.core.validation import (
    SecurityLimits,
    ValidationPatterns,
    create_validation_error,
    sanitize_string,
    validate_generator_parameters,
)
from pydantic import BaseModel, Field, validator

# --- Enums ---


class ConverterCategory(str, Enum):
    """Converter categories available in PyRIT"""

    ENCRYPTION = "encryption"
    JAILBREAK = "jailbreak"
    LANGUAGE = "language"
    TRANSFORM = "transform"
    TARGET = "target"
    CUSTOM = "custom"


class ConverterType(str, Enum):
    """Common converter types"""

    ROT13_CONVERTER = "ROT13Converter"
    BASE64_CONVERTER = "Base64Converter"
    CAESAR_CIPHER_CONVERTER = "CaesarCipherConverter"
    MORSE_CODE_CONVERTER = "MorseCodeConverter"
    UNICODE_CONVERTER = "UnicodeConverter"
    TRANSLATION_CONVERTER = "TranslationConverter"
    SEARCH_REPLACE_CONVERTER = "SearchReplaceConverter"
    VARIATION_CONVERTER = "VariationConverter"
    CODE_CHAMELEON_CONVERTER = "CodeChameleonConverter"
    PROMPT_VARIATION_CONVERTER = "PromptVariationConverter"


class ParameterType(str, Enum):
    """Parameter types for converter configuration"""

    STRING = "str"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    LIST = "list"
    TUPLE = "tuple"
    LITERAL = "literal"
    TARGET = "target"
    PROMPT = "prompt"


class ApplicationMode(str, Enum):
    """How to apply converter to dataset"""

    OVERWRITE = "overwrite"
    COPY = "copy"


# --- Base Models ---


class ConverterParameter(BaseModel):
    """Single converter parameter definition"""

    name: str = Field(..., description="Parameter name")
    type_str: str = Field(..., description="Parameter type as string")
    primary_type: str = Field(..., description="Primary type (str, int, bool, etc)")
    required: bool = Field(..., description="Whether parameter is required")
    default: Optional[Any] = Field(None, description="Default value")
    description: Optional[str] = Field(None, description="Parameter description")
    literal_choices: Optional[List[Any]] = Field(
        None, description="Valid choices for literal types"
    )
    skip_in_ui: bool = Field(
        default=False, description="Skip this parameter in UI forms"
    )


class ConverterInfo(BaseModel):
    """Information about a converter class"""

    name: str = Field(..., description="Converter class name")
    category: ConverterCategory = Field(..., description="Converter category")
    description: Optional[str] = Field(None, description="Converter description")
    requires_target: bool = Field(
        default=False, description="Whether converter requires a target"
    )
    parameters: List[ConverterParameter] = Field(
        default=[], description="Converter parameters"
    )


class ConvertedPrompt(BaseModel):
    """A converted prompt result"""

    id: str = Field(..., description="Prompt ID")
    original_value: str = Field(..., description="Original prompt text")
    converted_value: str = Field(..., description="Converted prompt text")
    dataset_name: Optional[str] = Field(None, description="Source dataset name")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata"
    )


# --- Request/Response Models ---


class ConverterTypesResponse(BaseModel):
    """Response for getting converter types"""

    categories: Dict[str, List[str]] = Field(
        ..., description="Converter categories and their classes"
    )
    total: int = Field(..., description="Total number of converter classes")


class ConverterParametersResponse(BaseModel):
    """Response for getting converter parameters"""

    converter_name: str = Field(..., description="Converter class name")
    parameters: List[ConverterParameter] = Field(
        ..., description="Parameter definitions"
    )
    requires_target: bool = Field(
        ..., description="Whether converter requires a target"
    )


class ConverterCreateRequest(BaseModel):
    """Request to create a converter configuration"""

    name: str = Field(
        ...,
        min_length=3,
        max_length=SecurityLimits.MAX_NAME_LENGTH,
        description="Unique converter configuration name",
    )
    converter_type: str = Field(
        ..., min_length=3, max_length=100, description="Converter class name"
    )
    parameters: Dict[str, Any] = Field(default={}, description="Converter parameters")
    generator_id: Optional[str] = Field(
        None, max_length=100, description="Generator ID if converter requires target"
    )

    @validator("name")
    def validate_name_field(cls, v):
        """Validate converter name"""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError(
                "Name must contain only alphanumeric characters, underscores, and hyphens"
            )
        return v

    @validator("converter_type")
    def validate_converter_type_field(cls, v):
        """Validate converter type"""
        v = sanitize_string(v)
        if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
            raise ValueError(
                "Converter type must contain only alphanumeric characters, underscores, and hyphens"
            )
        return v

    @validator("parameters")
    def validate_parameters_field(cls, v):
        """Validate converter parameters"""
        return validate_generator_parameters(v)

    @validator("generator_id")
    def validate_generator_id_field(cls, v):
        """Validate generator ID"""
        if v is not None:
            v = sanitize_string(v)
            if len(v) > 100:
                raise ValueError("Generator ID too long")
        return v


class ConverterCreateResponse(BaseModel):
    """Response for creating a converter"""

    converter: Dict[str, Any] = Field(
        ..., description="Created converter configuration"
    )
    message: str = Field(..., description="Success message")


class ConverterPreviewRequest(BaseModel):
    """Request to preview converter effect"""

    sample_prompts: Optional[List[str]] = Field(
        None, max_items=20, description="Specific prompts to preview (optional)"
    )
    num_samples: int = Field(
        default=1, ge=1, le=20, description="Number of sample prompts to convert"
    )
    dataset_id: Optional[str] = Field(
        None, max_length=100, description="Dataset to sample from"
    )

    @validator("sample_prompts")
    def validate_sample_prompts_field(cls, v):
        """Validate sample prompts"""
        if v is not None:
            validated = []
            for prompt in v:
                if not isinstance(prompt, str):
                    raise ValueError("Sample prompt must be a string")
                prompt = sanitize_string(prompt)
                if len(prompt) > SecurityLimits.MAX_STRING_LENGTH:
                    raise ValueError("Sample prompt too long")
                validated.append(prompt)
            return validated
        return v

    @validator("dataset_id")
    def validate_dataset_id_field(cls, v):
        """Validate dataset ID"""
        if v is not None:
            v = sanitize_string(v)
            if len(v) > 100:
                raise ValueError("Dataset ID too long")
        return v


class ConverterPreviewResponse(BaseModel):
    """Response for converter preview"""

    converter_id: str = Field(..., description="Converter configuration ID")
    preview_results: List[ConvertedPrompt] = Field(
        ..., description="Preview conversion results"
    )
    converter_info: Dict[str, Any] = Field(
        ..., description="Converter configuration info"
    )


class ConverterApplyRequest(BaseModel):
    """Request to apply converter to dataset"""

    dataset_id: str = Field(
        ..., max_length=100, description="Dataset ID to apply converter to"
    )
    mode: ApplicationMode = Field(
        ..., description="Application mode (overwrite or copy)"
    )
    new_dataset_name: Optional[str] = Field(
        None,
        min_length=3,
        max_length=SecurityLimits.MAX_NAME_LENGTH,
        description="Name for copied dataset (required if mode=copy)",
    )
    save_to_memory: bool = Field(
        default=True, description="Save results to PyRIT memory"
    )
    save_to_session: bool = Field(default=True, description="Save results to session")

    @validator("dataset_id")
    def validate_dataset_id_field(cls, v):
        """Validate dataset ID"""
        v = sanitize_string(v)
        if len(v) > 100:
            raise ValueError("Dataset ID too long")
        return v

    @validator("new_dataset_name")
    def validate_new_dataset_name_field(cls, v, values):
        """Validate new dataset name"""
        if v is not None:
            v = sanitize_string(v)
            if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
                raise ValueError(
                    "Dataset name must contain only alphanumeric characters, underscores, and hyphens"
                )

            # Check if required when mode is copy
            if values.get("mode") == ApplicationMode.COPY and not v:
                raise ValueError("New dataset name is required when mode is 'copy'")
        return v


class ConverterApplyResponse(BaseModel):
    """Response for applying converter"""

    success: bool = Field(..., description="Whether application succeeded")
    dataset_id: str = Field(..., description="Resulting dataset ID")
    dataset_name: str = Field(..., description="Resulting dataset name")
    converted_count: int = Field(..., description="Number of prompts converted")
    message: str = Field(..., description="Result message")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional result metadata"
    )


class ConvertersListResponse(BaseModel):
    """Response for listing converter configurations"""

    converters: List[Dict[str, Any]] = Field(..., description="Configured converters")
    total: int = Field(..., description="Total number of converters")


class ConverterDeleteResponse(BaseModel):
    """Response for deleting a converter"""

    success: bool = Field(..., description="Whether deletion succeeded")
    message: str = Field(..., description="Result message")
    deleted_at: datetime = Field(..., description="When converter was deleted")


class ConverterUpdateRequest(BaseModel):
    """Request to update converter configuration"""

    name: Optional[str] = Field(
        None,
        min_length=3,
        max_length=SecurityLimits.MAX_NAME_LENGTH,
        description="New converter name",
    )
    parameters: Optional[Dict[str, Any]] = Field(None, description="Updated parameters")
    generator_id: Optional[str] = Field(
        None, max_length=100, description="Updated generator ID"
    )

    @validator("name")
    def validate_name_field(cls, v):
        """Validate converter name"""
        if v is not None:
            v = sanitize_string(v)
            if not ValidationPatterns.SAFE_IDENTIFIER.match(v):
                raise ValueError(
                    "Name must contain only alphanumeric characters, underscores, and hyphens"
                )
        return v

    @validator("parameters")
    def validate_parameters_field(cls, v):
        """Validate converter parameters"""
        if v is not None:
            return validate_generator_parameters(v)
        return v

    @validator("generator_id")
    def validate_generator_id_field(cls, v):
        """Validate generator ID"""
        if v is not None:
            v = sanitize_string(v)
            if len(v) > 100:
                raise ValueError("Generator ID too long")
        return v


class ConverterError(BaseModel):
    """Error response for converter operations"""

    error_type: str = Field(..., description="Type of error")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When error occurred"
    )


# --- Advanced Models ---


class ConverterApplicationStatus(BaseModel):
    """Status of converter application process"""

    converter_id: str = Field(..., description="Converter ID")
    dataset_id: str = Field(..., description="Dataset ID")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(
        ..., description="Application status"
    )
    progress: float = Field(default=0.0, description="Progress percentage (0.0 to 1.0)")
    started_at: datetime = Field(..., description="When application started")
    completed_at: Optional[datetime] = Field(
        None, description="When application completed"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class ConverterBatchRequest(BaseModel):
    """Request to apply multiple converters"""

    dataset_id: str = Field(
        ..., max_length=100, description="Dataset to apply converters to"
    )
    converter_ids: List[str] = Field(
        ..., max_items=10, description="List of converter IDs to apply"
    )
    mode: ApplicationMode = Field(..., description="Application mode")
    parallel: bool = Field(
        default=False, description="Whether to apply converters in parallel"
    )

    @validator("dataset_id")
    def validate_dataset_id_field(cls, v):
        """Validate dataset ID"""
        v = sanitize_string(v)
        if len(v) > 100:
            raise ValueError("Dataset ID too long")
        return v

    @validator("converter_ids")
    def validate_converter_ids_field(cls, v):
        """Validate converter IDs list"""
        validated = []
        for converter_id in v:
            if not isinstance(converter_id, str):
                raise ValueError("Converter ID must be a string")
            converter_id = sanitize_string(converter_id)
            if len(converter_id) > 100:
                raise ValueError("Converter ID too long")
            validated.append(converter_id)
        return validated


class ConverterBatchResponse(BaseModel):
    """Response for batch converter application"""

    batch_id: str = Field(..., description="Batch operation ID")
    results: List[ConverterApplyResponse] = Field(
        ..., description="Individual application results"
    )
    overall_success: bool = Field(..., description="Whether all applications succeeded")
    total_converted: int = Field(
        ..., description="Total prompts converted across all converters"
    )


class ConverterStats(BaseModel):
    """Statistics about converter usage"""

    total_converters: int = Field(..., description="Total converter configurations")
    total_applications: int = Field(..., description="Total converter applications")
    most_used_converters: List[Dict[str, Any]] = Field(
        ..., description="Most frequently used converters"
    )
    recent_activity: List[Dict[str, Any]] = Field(
        ..., description="Recent converter activity"
    )


class ConverterExportRequest(BaseModel):
    """Request to export converter configuration"""

    converter_ids: List[str] = Field(
        ..., max_items=50, description="Converter IDs to export"
    )
    include_results: bool = Field(
        default=False, description="Include application results"
    )
    format: Literal["json", "yaml", "csv"] = Field(
        default="json", description="Export format"
    )

    @validator("converter_ids")
    def validate_converter_ids_field(cls, v):
        """Validate converter IDs list"""
        validated = []
        for converter_id in v:
            if not isinstance(converter_id, str):
                raise ValueError("Converter ID must be a string")
            converter_id = sanitize_string(converter_id)
            if len(converter_id) > 100:
                raise ValueError("Converter ID too long")
            validated.append(converter_id)
        return validated


class ConverterImportRequest(BaseModel):
    """Request to import converter configuration"""

    config_data: str = Field(
        ...,
        min_length=1,
        max_length=SecurityLimits.MAX_JSON_SIZE,
        description="Configuration data to import",
    )
    format: Literal["json", "yaml"] = Field(default="json", description="Import format")
    overwrite_existing: bool = Field(
        default=False, description="Whether to overwrite existing converters"
    )

    @validator("config_data")
    def validate_config_data_field(cls, v):
        """Validate configuration data"""
        v = sanitize_string(v)
        if len(v.encode("utf-8")) > SecurityLimits.MAX_JSON_SIZE:
            raise ValueError(
                f"Configuration data too large (max {SecurityLimits.MAX_JSON_SIZE} bytes)"
            )
        return v
