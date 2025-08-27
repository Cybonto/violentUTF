# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Configuration management schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class UpdateConfigRequest(BaseModel):
    """Request to update configuration parameters"""

    parameters: Dict[str, Any]
    merge_strategy: Optional[Literal["replace", "merge", "overlay"]] = "merge"


class ConfigParametersResponse(BaseModel):
    """Configuration parameters response"""

    parameters: Dict[str, Any]
    loaded_from: str = Field(description="File path or source")
    last_updated: datetime
    app_data_dir: str
    validation_status: str


class ConfigLoadResponse(BaseModel):
    """Response from loading configuration file"""

    parameters: Dict[str, Any]
    loaded_from: str
    validation_results: List[str]
    success: bool
    message: str


class ParameterFile(BaseModel):
    """Information about a parameter file"""

    filename: str
    path: str
    size_bytes: int
    modified: datetime
    type: Literal["system", "user"]


class ParameterFilesListResponse(BaseModel):
    """List of available parameter files"""

    files: List[ParameterFile]
    total_count: int


# Environment Configuration Schemas


class UpdateEnvironmentConfigRequest(BaseModel):
    """Request to update environment configuration"""

    environment_variables: Dict[str, str]
    validate_before_update: Optional[bool] = True


class EnvironmentConfigResponse(BaseModel):
    """Environment configuration response"""

    environment_variables: Dict[str, Optional[str]] = Field(description="Sensitive values masked")
    validation_results: Dict[str, bool]
    missing_required: List[str]
    configuration_complete: bool


class EnvironmentValidationResponse(BaseModel):
    """Environment configuration validation response"""

    is_valid: bool
    validation_results: Dict[str, bool]
    missing_variables: List[str]
    recommendations: List[str]
    overall_score: int = Field(ge=0, le=100, description="Validation score out of 100")


class EnvironmentSchemaResponse(BaseModel):
    """Environment variable schema definition"""

    env_schema: Dict[str, Any] = Field(alias="schema")
    version: str
    last_updated: datetime


class SaltGenerationResponse(BaseModel):
    """Response from salt generation"""

    salt: str
    length: int
    entropy_bits: float
    generation_method: str
    usage_instructions: str
