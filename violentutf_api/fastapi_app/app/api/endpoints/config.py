# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Configuration management endpoints
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from app.core.auth import get_current_user
from app.models.auth import User
from app.schemas.config import (
    ConfigLoadResponse,
    ConfigParametersResponse,
    EnvironmentConfigResponse,
    EnvironmentSchemaResponse,
    EnvironmentValidationResponse,
    ParameterFile,
    ParameterFilesListResponse,
    SaltGenerationResponse,
    UpdateConfigRequest,
    UpdateEnvironmentConfigRequest,
)
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

router = APIRouter()

DEFAULT_PARAMETERS_FILE = "parameters/default_parameters.yaml"


def get_config_file_path() -> str:
    """Get path to main configuration file"""
    config_dir = os.getenv("CONFIG_DIR", "./app_data/config")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "global_parameters.yaml")


def load_default_parameters() -> Dict[str, Any]:
    """Load default parameters from file"""
    try:
        # First try to load from configured path
        if os.path.exists(DEFAULT_PARAMETERS_FILE):
            with open(DEFAULT_PARAMETERS_FILE, "r") as f:
                return yaml.safe_load(f) or {}
    except Exception:
        pass

    # Return minimal default configuration
    return {"APP_DATA_DIR": os.getenv("APP_DATA_DIR", "./app_data/violentutf"), "version": "1.0", "initialized": True}


def save_parameters(params: Dict[str, Any]) -> None:
    """Save parameters to configuration file"""
    config_file = get_config_file_path()
    try:
        with open(config_file, "w") as f:
            yaml.dump(params, f, default_flow_style=False, indent=2)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error saving configuration: {str(e)}"
        )


@router.get("/parameters", response_model=ConfigParametersResponse)
async def get_config_parameters(current_user: User = Depends(get_current_user)):
    """
    Get current global configuration parameters
    """
    try:
        config_file = get_config_file_path()

        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                parameters = yaml.safe_load(f) or {}
            loaded_from = config_file
        else:
            parameters = load_default_parameters()
            loaded_from = "default"

        return ConfigParametersResponse(
            parameters=parameters,
            loaded_from=loaded_from,
            last_updated=(
                datetime.fromtimestamp(os.path.getmtime(config_file)) if os.path.exists(config_file) else datetime.now()
            ),
            app_data_dir=parameters.get("APP_DATA_DIR", "./app_data/violentutf"),
            validation_status="valid",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error loading configuration: {str(e)}"
        )


@router.put("/parameters", response_model=ConfigParametersResponse)
async def update_config_parameters(request: UpdateConfigRequest, current_user: User = Depends(get_current_user)):
    """
    Update global configuration parameters
    """
    try:
        config_file = get_config_file_path()

        # Load existing parameters
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                existing_params = yaml.safe_load(f) or {}
        else:
            existing_params = load_default_parameters()

        # Apply update strategy
        if request.merge_strategy == "replace":
            parameters = request.parameters
        elif request.merge_strategy == "overlay":
            parameters = {**existing_params, **request.parameters}
        else:  # merge (default)
            parameters = existing_params.copy()
            parameters.update(request.parameters)

        # Save updated parameters
        save_parameters(parameters)

        return ConfigParametersResponse(
            parameters=parameters,
            loaded_from=config_file,
            last_updated=datetime.now(),
            app_data_dir=parameters.get("APP_DATA_DIR", "./app_data/violentutf"),
            validation_status="valid",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating configuration: {str(e)}"
        )


@router.post("/parameters/load", response_model=ConfigLoadResponse)
async def load_config_from_file(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """
    Load configuration from uploaded YAML file
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith((".yaml", ".yml")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a YAML file (.yaml or .yml)"
            )

        # Read and parse file
        content = await file.read()
        try:
            parameters = yaml.safe_load(content.decode("utf-8"))
        except yaml.YAMLError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid YAML format: {str(e)}")

        if not isinstance(parameters, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="YAML file must contain a dictionary (key-value pairs)"
            )

        # Save loaded parameters
        save_parameters(parameters)

        # Validate loaded parameters
        validation_results = []
        if "APP_DATA_DIR" not in parameters:
            validation_results.append("Warning: APP_DATA_DIR not specified")

        return ConfigLoadResponse(
            parameters=parameters,
            loaded_from=file.filename or "Unknown file",
            validation_results=validation_results,
            success=True,
            message=f"Successfully loaded {len(parameters)} parameters from {file.filename}",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error loading configuration file: {str(e)}"
        )


@router.get("/parameters/files", response_model=ParameterFilesListResponse)
async def list_parameter_files(current_user: User = Depends(get_current_user)):
    """
    List available parameter files in the system
    """
    try:
        parameter_files = []

        # Check default parameters directory
        param_dir = Path("parameters")
        if param_dir.exists():
            for file_path in param_dir.glob("*.yaml"):
                stat = file_path.stat()
                parameter_files.append(
                    ParameterFile(
                        filename=file_path.name,
                        path=str(file_path),
                        size_bytes=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        type="system",
                    )
                )

            for file_path in param_dir.glob("*.yml"):
                stat = file_path.stat()
                parameter_files.append(
                    ParameterFile(
                        filename=file_path.name,
                        path=str(file_path),
                        size_bytes=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        type="system",
                    )
                )

        # Check user config directory
        config_dir = Path(os.getenv("CONFIG_DIR", "./app_data/config"))
        if config_dir.exists():
            for file_path in config_dir.glob("*.yaml"):
                stat = file_path.stat()
                parameter_files.append(
                    ParameterFile(
                        filename=file_path.name,
                        path=str(file_path),
                        size_bytes=stat.st_size,
                        modified=datetime.fromtimestamp(stat.st_mtime),
                        type="user",
                    )
                )

        return ParameterFilesListResponse(files=parameter_files, total_count=len(parameter_files))

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error listing parameter files: {str(e)}"
        )


# Environment Configuration Endpoints


@router.get("/environment", response_model=EnvironmentConfigResponse)
async def get_environment_config(current_user: User = Depends(get_current_user)):
    """
    Get current environment configuration including database salt, API keys, and system paths
    """
    try:
        # Get environment variables (mask sensitive ones)
        env_vars: Dict[str, Optional[str]] = {}
        required_vars = [
            "PYRIT_DB_SALT",
            "VIOLENTUTF_API_KEY",
            "APP_DATA_DIR",
            "KEYCLOAK_URL",
            "KEYCLOAK_REALM",
            "KEYCLOAK_CLIENT_ID",
            "OPENAI_CHAT_KEY",
        ]

        validation_results = {}
        missing_required = []

        for var in required_vars:
            value = os.getenv(var)
            if value:
                # Mask sensitive values
                if "KEY" in var or "SECRET" in var or "SALT" in var:
                    env_vars[var] = f"{value[:8]}..." if len(value) > 8 else "***"
                else:
                    env_vars[var] = value
                validation_results[var] = True
            else:
                env_vars[var] = None
                validation_results[var] = False
                missing_required.append(var)

        return EnvironmentConfigResponse(
            environment_variables=env_vars,
            validation_results=validation_results,
            missing_required=missing_required,
            configuration_complete=len(missing_required) == 0,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting environment configuration: {str(e)}",
        )


@router.put("/environment", response_model=EnvironmentConfigResponse)
async def update_environment_config(
    request: UpdateEnvironmentConfigRequest, current_user: User = Depends(get_current_user)
):
    """
    Update environment configuration variables
    """
    try:
        # In a real implementation, you would update environment variables
        # For now, we'll simulate the update

        if request.validate_before_update:
            # Validate provided values
            validation_errors = []
            for key, value in request.environment_variables.items():
                if key == "PYRIT_DB_SALT" and len(value) < 8:
                    validation_errors.append("PYRIT_DB_SALT must be at least 8 characters")
                if key == "APP_DATA_DIR" and not os.path.exists(os.path.dirname(value)):
                    validation_errors.append(f"Parent directory for APP_DATA_DIR does not exist: {value}")

            if validation_errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Validation errors: {validation_errors}"
                )

        # Simulate update (in production, this would actually update environment)
        updated_vars: Dict[str, Optional[str]] = {}
        for key, value in request.environment_variables.items():
            # Mask sensitive values in response
            if "KEY" in key or "SECRET" in key or "SALT" in key:
                updated_vars[key] = f"{value[:8]}..." if len(value) > 8 else "***"
            else:
                updated_vars[key] = value

        return EnvironmentConfigResponse(
            environment_variables=updated_vars,
            validation_results={k: True for k in request.environment_variables.keys()},
            missing_required=[],
            configuration_complete=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating environment configuration: {str(e)}",
        )


@router.post("/environment/validate", response_model=EnvironmentValidationResponse)
async def validate_environment_config(current_user: User = Depends(get_current_user)):
    """
    Validate current environment configuration for completeness and correctness
    """
    try:
        required_vars = [
            "PYRIT_DB_SALT",
            "VIOLENTUTF_API_KEY",
            "APP_DATA_DIR",
            "KEYCLOAK_URL",
            "KEYCLOAK_REALM",
            "KEYCLOAK_CLIENT_ID",
        ]

        validation_results = {}
        recommendations = []
        missing_vars = []

        for var in required_vars:
            value = os.getenv(var)
            if value:
                validation_results[var] = True

                # Additional validation
                if var == "PYRIT_DB_SALT" and len(value) < 16:
                    recommendations.append(f"{var} should be at least 16 characters for better security")
                elif var == "APP_DATA_DIR" and not os.path.exists(value):
                    recommendations.append(f"{var} directory does not exist: {value}")
                elif var == "KEYCLOAK_URL" and not value.startswith(("http://", "https://")):
                    recommendations.append(f"{var} should start with http:// or https://")

            else:
                validation_results[var] = False
                missing_vars.append(var)

        is_valid = len(missing_vars) == 0

        return EnvironmentValidationResponse(
            is_valid=is_valid,
            validation_results=validation_results,
            missing_variables=missing_vars,
            recommendations=recommendations,
            overall_score=int((sum(validation_results.values()) / len(validation_results)) * 100),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating environment configuration: {str(e)}",
        )


@router.get("/environment/schema", response_model=EnvironmentSchemaResponse)
async def get_environment_schema():
    """
    Get the schema of required environment variables and their purposes
    """
    schema = {
        "PYRIT_DB_SALT": {
            "type": "string",
            "required": True,
            "description": "Salt for generating user-specific database file names",
            "minimum_length": 16,
            "security_level": "high",
        },
        "VIOLENTUTF_API_KEY": {
            "type": "string",
            "required": True,
            "description": "API key for ViolentUTF service authentication",
            "format": "api_key",
            "security_level": "high",
        },
        "APP_DATA_DIR": {
            "type": "string",
            "required": True,
            "description": "Base directory for application data storage",
            "format": "directory_path",
            "default": "./app_data/violentutf",
        },
        "KEYCLOAK_URL": {
            "type": "string",
            "required": True,
            "description": "Base URL for Keycloak authentication server",
            "format": "url",
            "example": "http://localhost:8080",
        },
        "KEYCLOAK_REALM": {
            "type": "string",
            "required": True,
            "description": "Keycloak realm name",
            "default": "ViolentUTF",
        },
        "KEYCLOAK_CLIENT_ID": {
            "type": "string",
            "required": True,
            "description": "Keycloak client identifier",
            "default": "violentutf",
        },
        "OPENAI_CHAT_KEY": {
            "type": "string",
            "required": False,
            "description": "OpenAI API key for AI model access",
            "format": "api_key",
            "security_level": "high",
        },
    }

    return EnvironmentSchemaResponse(schema=schema, version="1.0", last_updated=datetime.now())


@router.post("/environment/generate-salt", response_model=SaltGenerationResponse)
async def generate_database_salt(current_user: User = Depends(get_current_user)):
    """
    Generate a new cryptographically secure database salt for PyRIT operations
    """
    try:
        import secrets
        import string

        # Generate cryptographically secure salt
        alphabet = string.ascii_letters + string.digits
        salt = "".join(secrets.choice(alphabet) for _ in range(32))

        return SaltGenerationResponse(
            salt=salt,
            length=len(salt),
            entropy_bits=len(alphabet) ** len(salt),
            generation_method="cryptographically_secure_random",
            usage_instructions="Set this value as PYRIT_DB_SALT environment variable",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generating salt: {str(e)}"
        )
