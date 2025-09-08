# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""FastAPI endpoints for converter management

Implements API backend for 3_Configure_Converters.py page
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.core.auth import get_current_user
from app.db.duckdb_manager import get_duckdb_manager
from app.models.auth import User
from app.schemas.converters import (
    ApplicationMode,
    ConvertedPrompt,
    ConverterApplyRequest,
    ConverterApplyResponse,
    ConverterCreateRequest,
    ConverterCreateResponse,
    ConverterDeleteResponse,
    ConverterParameter,
    ConverterParametersResponse,
    ConverterPreviewRequest,
    ConverterPreviewResponse,
    ConvertersListResponse,
    ConverterTypesResponse,
    ConverterUpdateRequest,
)
from fastapi import APIRouter, Depends, HTTPException

logger = logging.getLogger(__name__)


def _safe_convert_choices(choices: object) -> Optional[List[object]]:
    """Safely convert choices to list of Any."""
    if not choices:

        return None
    if isinstance(choices, (list, tuple)):
        return list(choices)
    return None


router = APIRouter()

# DuckDB storage replaces in-memory storage
# _converters_store: Dict[str, Dict[str, object]] = {} - REMOVED
# _session_converters: Dict[str, Dict[str, object]] = {} - REMOVED

# Converter type definitions (based on PyRIT converters)
CONVERTER_CATEGORIES = {
    "Encryption": [
        "ROT13Converter",
        "Base64Converter",
        "CaesarCipherConverter",
        "MorseCodeConverter",
        "UnicodeConverter",
    ],
    "Jailbreak": ["PromptVariationConverter", "CodeChameleonConverter"],
    "Language": ["TranslationConverter"],
    "Transform": ["SearchReplaceConverter", "VariationConverter"],
    "Target": ["TargetConverter"],
    "Dataset": ["GraphWalkConverter"],
}

# WARNING: These converter parameter definitions are MOCK DATA and do not accurately
# represent PyRIT's actual converter implementations. They contain:
# - Incorrect converter names (CaesarCipherConverter vs CaesarConverter)
# - Non-existent parameters (append_description for ROT13/Base64)
# - Wrong default values and required/optional status
# - Missing actual PyRIT parameters
# TODO: Replace with real PyRIT converter parameter definitions
CONVERTER_PARAMETERS = {
    "ROT13Converter": [
        # ROT13Converter in PyRIT takes no specific parameters beyond *args, **kwargs: object
        # It's a simple converter that rotates characters by 13 positions
    ],
    "Base64Converter": [
        # Base64Converter in PyRIT takes no specific parameters beyond *args, **kwargs: object
        # It encodes the prompt using base64 encoding
    ],
    "CaesarCipherConverter": [
        {
            "name": "caesar_offset",
            "type_str": "int",
            "primary_type": "int",
            "required": False,
            "default": 3,
            "description": "Caesar cipher offset (shift amount)",
            "literal_choices": None,
            "skip_in_ui": False,
        },
        {
            "name": "append_description",
            "type_str": "bool",
            "primary_type": "bool",
            "required": False,
            "default": True,
            "description": "Whether to append explanation of Caesar cipher",
            "literal_choices": None,
            "skip_in_ui": False,
        },
    ],
    "MorseCodeConverter": [
        {
            "name": "append_description",
            "type_str": "bool",
            "primary_type": "bool",
            "required": False,
            "default": True,
            "description": "Whether to append explanation of Morse code",
            "literal_choices": None,
            "skip_in_ui": False,
        }
    ],
    "UnicodeConverter": [
        {
            "name": "start_value",
            "type_str": "int",
            "primary_type": "int",
            "required": False,
            "default": 0x1D400,
            "description": "Starting Unicode value for conversion",
            "literal_choices": None,
            "skip_in_ui": False,
        }
    ],
    "TranslationConverter": [
        {
            "name": "language",
            "type_str": "str",
            "primary_type": "str",
            "required": True,
            "default": "French",
            "description": "Target language for translation",
            "literal_choices": [
                "French",
                "Spanish",
                "German",
                "Italian",
                "Portuguese",
                "Russian",
                "Chinese",
                "Japanese",
            ],
            "skip_in_ui": False,
        },
        {
            "name": "converter_target",
            "type_str": "PromptChatTarget",
            "primary_type": "target",
            "required": True,
            "default": None,
            "description": "Target for translation requests",
            "literal_choices": None,
            "skip_in_ui": True,
        },
    ],
    "SearchReplaceConverter": [
        {
            "name": "old_value",
            "type_str": "str",
            "primary_type": "str",
            "required": True,
            "default": "",
            "description": "Text to search for",
            "literal_choices": None,
            "skip_in_ui": False,
        },
        {
            "name": "new_value",
            "type_str": "str",
            "primary_type": "str",
            "required": True,
            "default": "",
            "description": "Replacement text",
            "literal_choices": None,
            "skip_in_ui": False,
        },
    ],
    "VariationConverter": [
        {
            "name": "variations",
            "type_str": "list[str]",
            "primary_type": "list",
            "required": True,
            "default": [],
            "description": "List of variation templates",
            "literal_choices": None,
            "skip_in_ui": False,
        }
    ],
    "CodeChameleonConverter": [
        {
            "name": "encrypt_type",
            "type_str": "str",
            "primary_type": "str",
            "required": False,
            "default": "custom",
            "description": "Type of code chameleon encryption",
            "literal_choices": [
                "custom",
                "reverse",
                "binary_tree",
                "odd_even",
                "length",
            ],
            "skip_in_ui": False,
        }
    ],
    "PromptVariationConverter": [
        {
            "name": "converter_target",
            "type_str": "PromptChatTarget",
            "primary_type": "target",
            "required": True,
            "default": None,
            "description": "Target for generating variations",
            "literal_choices": None,
            "skip_in_ui": True,
        }
    ],
    "GraphWalkConverter": [
        {
            "name": "file_path",
            "type_str": "str",
            "primary_type": "str",
            "required": True,
            "default": "",
            "description": "Path to GraphWalk dataset file",
            "literal_choices": None,
            "skip_in_ui": False,
        },
        {
            "name": "max_memory_usage_gb",
            "type_str": "float",
            "primary_type": "float",
            "required": False,
            "default": 2.0,
            "description": "Maximum memory usage in GB for processing",
            "literal_choices": None,
            "skip_in_ui": False,
        },
        {
            "name": "chunk_size_mb",
            "type_str": "int",
            "primary_type": "int",
            "required": False,
            "default": 15,
            "description": "Chunk size in MB for massive file splitting",
            "literal_choices": [5, 15, 25, 50],
            "skip_in_ui": False,
        },
        {
            "name": "performance_mode",
            "type_str": "str",
            "primary_type": "str",
            "required": False,
            "default": "balanced",
            "description": "Performance optimization mode",
            "literal_choices": ["speed", "balanced", "memory_optimized"],
            "skip_in_ui": False,
        },
        {
            "name": "async_conversion",
            "type_str": "bool",
            "primary_type": "bool",
            "required": False,
            "default": True,
            "description": "Run conversion asynchronously for large files",
            "literal_choices": None,
            "skip_in_ui": False,
        },
    ],
}


@router.get(
    "/types",
    response_model=ConverterTypesResponse,
    summary="Get available converter types",
)
async def get_converter_types(
    current_user: User = Depends(get_current_user),
) -> ConverterTypesResponse:
    """Get list of available converter categories and classes."""
    try:

        logger.info("User %s requested converter types", current_user.username)

        total_converters = sum(len(converters) for converters in CONVERTER_CATEGORIES.values())

        return ConverterTypesResponse(categories=CONVERTER_CATEGORIES, total=total_converters)
    except Exception as e:
        logger.error("Error getting converter types: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get converter types: {str(e)}") from e


@router.get(
    "/params/{converter_type}",
    response_model=ConverterParametersResponse,
    summary="Get converter parameters",
)
async def get_converter_parameters(
    converter_type: str, current_user: User = Depends(get_current_user)
) -> ConverterParametersResponse:
    """Get parameter definitions for a specific converter type."""
    try:

        logger.info(
            "User %s requested parameters for converter: %s",
            current_user.username,
            converter_type,
        )

        if converter_type not in CONVERTER_PARAMETERS:
            raise HTTPException(status_code=404, detail=f"Converter type '{converter_type}' not found")

        param_definitions = CONVERTER_PARAMETERS[converter_type]
        parameters = []
        for param in param_definitions:
            # Safely construct ConverterParameter with all required fields
            param_type = str(param.get("type", "str"))
            converter_param = ConverterParameter(
                name=str(param.get("name", "")),
                description=str(param.get("description", "")),
                type_str=param_type,
                primary_type=param_type,  # Use same value for both type fields
                required=bool(param.get("required", False)),
                default=param.get("default_value"),
                literal_choices=_safe_convert_choices(param.get("literal_choices")),  # Add missing field
            )
            parameters.append(converter_param)

        # Check if converter requires a target
        requires_target = any(
            param.get("skip_in_ui", False) and "target" in str(param.get("type_str", "")) for param in param_definitions
        )

        return ConverterParametersResponse(
            converter_name=converter_type,
            parameters=parameters,
            requires_target=requires_target,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting parameters for %s: %s", converter_type, e)
        raise HTTPException(status_code=500, detail=f"Failed to get converter parameters: {str(e)}") from e


@router.get("", response_model=ConvertersListResponse, summary="Get configured converters")
async def get_converters(
    current_user: User = Depends(get_current_user),
) -> ConvertersListResponse:
    """Get list of configured converters from session."""
    try:

        user_id = current_user.username
        logger.info("User %s requested converters list", user_id)

        converters = []

        # Get converters from DuckDB
        db_manager = get_duckdb_manager(user_id)
        converters_data = db_manager.list_converters()

        for converter_data in converters_data:
            converters.append(
                {
                    "id": converter_data["id"],
                    "name": converter_data["name"],
                    "converter_type": converter_data["type"],
                    "parameters": converter_data["parameters"],
                    "created_at": converter_data["created_at"],
                    "updated_at": converter_data["updated_at"],
                    "status": converter_data.get("status", "ready"),
                }
            )

        return ConvertersListResponse(converters=converters, total=len(converters))
    except Exception as e:
        logger.error("Error getting converters: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get converters: {str(e)}") from e


@router.post("", response_model=ConverterCreateResponse, summary="Create a new converter")
async def create_converter(
    request: ConverterCreateRequest, current_user: User = Depends(get_current_user)
) -> ConverterCreateResponse:
    """Create a new converter configuration."""
    try:

        user_id = current_user.username
        logger.info("User %s creating converter: %s", user_id, request.name)

        # Generate converter ID
        converter_id = str(uuid.uuid4())

        # Validate converter type
        all_converter_types = []
        for category_converters in CONVERTER_CATEGORIES.values():
            all_converter_types.extend(category_converters)

        if request.converter_type not in all_converter_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid converter type: {request.converter_type}",
            )

        # Validate parameters against converter definition
        if request.converter_type in CONVERTER_PARAMETERS:
            param_definitions = CONVERTER_PARAMETERS[request.converter_type]
            required_params = [p["name"] for p in param_definitions if p["required"] and not p.get("skip_in_ui", False)]

            for required_param in required_params:
                if required_param not in request.parameters:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Required parameter '{required_param}' missing",
                    )

        # Store converter in DuckDB
        db_manager = get_duckdb_manager(user_id)
        converter_id = db_manager.create_converter(
            name=request.name,
            converter_type=request.converter_type,
            parameters=request.parameters,
        )

        logger.info(
            "Converter '%s' created successfully with ID: %s",
            request.name,
            converter_id,
        )

        # Get the created converter data
        created_converter = db_manager.get_converter(converter_id)
        if not created_converter:
            raise HTTPException(status_code=500, detail="Failed to retrieve created converter")

        return ConverterCreateResponse(
            converter={
                "id": converter_id,
                "name": request.name,
                "converter_type": request.converter_type,
                "parameters": request.parameters,
                "created_at": created_converter["created_at"],
                "updated_at": created_converter["updated_at"],
                "status": "ready",
            },
            message=f"Converter '{request.name}' created successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating converter %s: %s", request.name, e)
        raise HTTPException(status_code=500, detail=f"Failed to create converter: {str(e)}") from e


@router.post(
    "/{converter_id}/preview",
    response_model=ConverterPreviewResponse,
    summary="Preview converter effect",
)
async def preview_converter(
    converter_id: str,
    request: ConverterPreviewRequest,
    current_user: User = Depends(get_current_user),
) -> object:
    """Preview the effect of a converter on sample prompts."""
    try:

        user_id = current_user.username
        logger.info("User %s previewing converter: %s", user_id, converter_id)

        # Find converter in DuckDB
        db_manager = get_duckdb_manager(user_id)
        converter_data = db_manager.get_converter(converter_id)

        if not converter_data:
            raise HTTPException(status_code=404, detail="Converter not found")

        # Get sample prompts
        sample_prompts = []
        if request.sample_prompts:
            sample_prompts = request.sample_prompts[: request.num_samples]
        elif request.dataset_id:
            # Load real prompts from dataset for converter preview
            try:
                from app.services.dataset_integration_service import get_dataset_prompts

                real_prompts = await get_dataset_prompts(
                    dataset_id=request.dataset_id,
                    sample_size=request.num_samples,
                    user_context=user_id,
                )

                if real_prompts:
                    sample_prompts = real_prompts[: request.num_samples]
                    logger.info(
                        "Loaded %s real prompts from dataset %s",
                        len(sample_prompts),
                        request.dataset_id,
                    )
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"No prompts found in dataset {request.dataset_id}. "
                        f"Please check if the dataset exists and contains prompts.",
                    )
            except Exception as e:
                logger.error("Failed to load prompts from dataset %s: %s", request.dataset_id, e)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to load prompts from dataset: {str(e)}",
                ) from e
        else:
            # No dataset specified - return error instead of using dangerous mock prompts
            raise HTTPException(
                status_code=400,
                detail="Either sample_prompts or dataset_id is required for converter preview.",
            )

        # Simulate converter application
        converter_type = converter_data["type"]
        parameters = converter_data["parameters"]

        preview_results = []
        for _, prompt in enumerate(sample_prompts):
            converted_prompt = simulate_converter_application(converter_type, prompt, parameters)

            preview_results.append(
                ConvertedPrompt(
                    id=str(uuid.uuid4()),
                    original_value=prompt,
                    converted_value=converted_prompt,
                    dataset_name=request.dataset_id,
                    metadata={
                        "converter_type": converter_type,
                        "parameters": parameters,
                    },
                )
            )

        return ConverterPreviewResponse(
            converter_id=converter_id,
            preview_results=preview_results,
            converter_info=converter_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error previewing converter %s: %s", converter_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to preview converter: {str(e)}") from e


@router.post(
    "/{converter_id}/apply",
    response_model=ConverterApplyResponse,
    summary="Apply converter to dataset",
)
async def apply_converter(
    converter_id: str,
    request: ConverterApplyRequest,
    current_user: User = Depends(get_current_user),
) -> ConverterApplyResponse:
    """Apply a converter to an entire dataset."""
    try:

        user_id = current_user.username
        logger.info(
            "User %s applying converter %s to dataset %s",
            user_id,
            converter_id,
            request.dataset_id,
        )

        # Get DuckDB manager
        db_manager = get_duckdb_manager(user_id)

        # Find converter in DuckDB
        converter_data = db_manager.get_converter(converter_id)
        if not converter_data:
            raise HTTPException(status_code=404, detail="Converter not found")

        # Validate request based on mode
        if request.mode == ApplicationMode.COPY and not request.new_dataset_name:
            raise HTTPException(
                status_code=400,
                detail="new_dataset_name is required when mode is 'copy'",
            )

        # Get the source dataset
        source_dataset = db_manager.get_dataset(request.dataset_id)
        if not source_dataset:
            raise HTTPException(status_code=404, detail=f"Dataset {request.dataset_id} not found")

        # Get dataset prompts from the dataset data
        # The DuckDB manager returns prompts with 'text' field
        dataset_prompts = [p.get("text", "") for p in source_dataset.get("prompts", [])]
        if not dataset_prompts:
            raise HTTPException(status_code=400, detail=f"Dataset {request.dataset_id} has no prompts")

        # Prepare converter info
        converter_type = converter_data["type"]
        parameters = converter_data["parameters"]

        # Apply converter to all prompts
        converted_prompts = []
        for prompt in dataset_prompts:
            # Apply converter using the simulate function (or real PyRIT converter when integrated)
            converted_prompt = simulate_converter_application(converter_type, prompt, parameters)
            converted_prompts.append(converted_prompt)

        # Handle based on mode
        if request.mode == ApplicationMode.COPY:
            # Validate new dataset name is provided for COPY mode
            if not request.new_dataset_name:
                raise HTTPException(status_code=400, detail="New dataset name is required for COPY mode")

            # Create a new dataset with converted prompts
            new_dataset_id = db_manager.create_dataset(
                name=request.new_dataset_name,
                source_type="converter",  # Mark as created by converter
                configuration={
                    "original_dataset_id": request.dataset_id,
                    "original_dataset_name": source_dataset.get("name", "Unknown"),
                    "converter_id": converter_id,
                    "converter_type": converter_type,
                    "conversion_timestamp": datetime.utcnow().isoformat(),
                },
                prompts=converted_prompts,
            )

            result_dataset_name = request.new_dataset_name  # Already validated to be non-None above
            assert result_dataset_name is not None  # nosec B101 - mypy type narrowing, already validated above
            result_dataset_id = new_dataset_id

            logger.info(
                "Created new dataset '%s' (ID: %s) with %d converted prompts",
                result_dataset_name,
                result_dataset_id,
                len(converted_prompts),
            )

        else:  # OVERWRITE mode
            # For overwrite mode, we need to delete the old dataset and create a new one with the same name
            # since DuckDB manager doesn't have update methods for prompts
            dataset_name = source_dataset.get("name", "Unknown")

            # Delete the old dataset
            db_manager.delete_dataset(request.dataset_id)

            # Create new dataset with converted prompts but same name
            new_dataset_id = db_manager.create_dataset(
                name=dataset_name,
                source_type=source_dataset.get("source_type", "converter"),
                configuration={
                    **source_dataset.get("configuration", {}),
                    "last_converter_id": converter_id,
                    "last_converter_type": converter_type,
                    "last_conversion_timestamp": datetime.utcnow().isoformat(),
                },
                prompts=converted_prompts,
            )

            result_dataset_name = dataset_name
            result_dataset_id = new_dataset_id

            logger.info(
                "Overwrote dataset '%s' (new ID: %s) with %d converted prompts",
                result_dataset_name,
                result_dataset_id,
                len(converted_prompts),
            )

        # Save to PyRIT memory if requested
        if request.save_to_memory:
            # TODO: Integrate with PyRIT memory when available
            logger.info(
                "Would save %s converted prompts to PyRIT memory",
                len(converted_prompts),
            )

        return ConverterApplyResponse(
            success=True,
            dataset_id=result_dataset_id,
            dataset_name=result_dataset_name,
            converted_count=len(converted_prompts),
            message=f"Converter applied successfully. {len(converted_prompts)} prompts converted.",
            metadata={
                "converter_type": converter_type,
                "original_dataset_id": request.dataset_id,
                "mode": request.mode.value,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error applying converter %s: %s", converter_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to apply converter: {str(e)}") from e


@router.delete(
    "/{converter_id}",
    response_model=ConverterDeleteResponse,
    summary="Delete a converter",
)
async def delete_converter(
    converter_id: str, current_user: User = Depends(get_current_user)
) -> ConverterDeleteResponse:
    """Delete a converter configuration."""
    try:

        user_id = current_user.username
        logger.info("User %s deleting converter: %s", user_id, converter_id)

        # Find and delete converter from DuckDB
        db_manager = get_duckdb_manager(user_id)
        deleted = db_manager.delete_converter(converter_id)

        if deleted:
            logger.info("Converter %s deleted successfully", converter_id)
            return ConverterDeleteResponse(
                success=True,
                message="Converter deleted successfully",
                deleted_at=datetime.utcnow(),
            )
        else:
            raise HTTPException(status_code=404, detail="Converter not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting converter %s: %s", converter_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete converter: {str(e)}") from e


@router.put("/{converter_id}", response_model=Dict[str, object], summary="Update a converter")
async def update_converter(
    converter_id: str,
    request: ConverterUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, object]:
    """Update an existing converter configuration."""
    try:

        user_id = current_user.username
        logger.info("User %s updating converter: %s", user_id, converter_id)

        # Find converter in DuckDB
        db_manager = get_duckdb_manager(user_id)
        converter_data = db_manager.get_converter(converter_id)

        if not converter_data:
            raise HTTPException(status_code=404, detail="Converter not found")

        # Update fields
        if request.name is not None:
            converter_data["name"] = request.name
        if request.parameters is not None:
            converter_data["parameters"] = request.parameters
        if request.generator_id is not None:
            converter_data["generator_id"] = request.generator_id

        converter_data["updated_at"] = datetime.utcnow()

        logger.info("Converter %s updated successfully", converter_id)

        # Return current converter data (updates not implemented yet)
        return {
            "id": converter_data["id"],
            "name": converter_data["name"],
            "converter_type": converter_data["type"],
            "parameters": converter_data["parameters"],
            "created_at": converter_data["created_at"],
            "updated_at": converter_data["updated_at"],
            "status": converter_data.get("status", "ready"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating converter %s: %s", converter_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to update converter: {str(e)}") from e


@router.get("/{converter_id}", response_model=Dict[str, object], summary="Get converter details")
async def get_converter(converter_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, object]:
    """Get detailed information about a specific converter."""
    try:

        user_id = current_user.username
        logger.info("User %s requested converter details: %s", user_id, converter_id)

        # Find converter in DuckDB
        db_manager = get_duckdb_manager(user_id)
        converter_data = db_manager.get_converter(converter_id)
        if converter_data:
            return {
                "id": converter_data["id"],
                "name": converter_data["name"],
                "converter_type": converter_data["type"],
                "parameters": converter_data["parameters"],
                "created_at": converter_data["created_at"],
                "updated_at": converter_data["updated_at"],
                "status": converter_data.get("status", "ready"),
            }

        raise HTTPException(status_code=404, detail="Converter not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting converter %s: %s", converter_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to get converter: {str(e)}") from e


# --- Helper Functions ---


def simulate_converter_application(converter_type: str, prompt: str, parameters: Dict[str, object]) -> str:
    """Simulate applying a converter to a prompt."""
    try:

        if converter_type == "ROT13Converter":
            # Simple ROT13 simulation
            converted = "".join(
                (
                    chr((ord(c) - ord("a") + 13) % 26 + ord("a"))
                    if "a" <= c <= "z"
                    else (chr((ord(c) - ord("A") + 13) % 26 + ord("A")) if "A" <= c <= "Z" else c)
                )
                for c in prompt
            )
            if parameters.get("append_description", True):
                converted += (
                    "\n\n[This message has been encoded using ROT13 cipher. "
                    "Please decode and respond using the same cipher.]"
                )
            return converted

        elif converter_type == "Base64Converter":
            # Simple Base64-like simulation
            import base64

            encoded = base64.b64encode(prompt.encode()).decode()
            if parameters.get("append_description", True):
                encoded += (
                    "\n\n[This message has been encoded using Base64. "
                    "Please decode and respond using the same encoding.]"
                )
            return encoded

        elif converter_type == "CaesarCipherConverter":
            caesar_offset = parameters.get("caesar_offset")
            offset = int(caesar_offset) if caesar_offset is not None else 3
            converted = "".join(
                (
                    chr((ord(c) - ord("a") + offset) % 26 + ord("a"))
                    if "a" <= c <= "z"
                    else (chr((ord(c) - ord("A") + offset) % 26 + ord("A")) if "A" <= c <= "Z" else c)
                )
                for c in prompt
            )
            if parameters.get("append_description", True):
                converted += (
                    f"\n\n[This message has been encoded using Caesar cipher with offset {offset}. "
                    f"Please decode and respond using the same cipher.]"
                )
            return converted

        elif converter_type == "MorseCodeConverter":
            # Simple Morse code simulation (partial)
            morse_map = {
                "A": ".-",
                "B": "-...",
                "C": "-.-.",
                "D": "-..",
                "E": ".",
                "F": "..-.",
                "G": "--.",
                "H": "....",
                " ": "/",
            }
            converted = " ".join(morse_map.get(c.upper(), c) for c in prompt)
            if parameters.get("append_description", True):
                converted += (
                    "\n\n[This message has been encoded in Morse code. Please decode and respond using the same code.]"
                )
            return converted

        elif converter_type == "SearchReplaceConverter":
            old_value = str(parameters.get("old_value", ""))
            new_value = str(parameters.get("new_value", ""))
            return prompt.replace(old_value, new_value)

        elif converter_type == "TranslationConverter":
            language = parameters.get("language", "French")
            return f"[Translated to {language}] {prompt} [Translation placeholder]"

        elif converter_type == "CodeChameleonConverter":
            encrypt_type = str(parameters.get("encrypt_type", "custom"))
            if encrypt_type == "reverse":
                return prompt[::-1] + "\n\n[This message has been reversed. Please decode and respond.]"
            elif encrypt_type == "odd_even":
                odd = prompt[1::2]
                even = prompt[::2]
                return f"{odd}|{even}\n\n[This message has been split odd/even. Please decode and respond.]"
            else:
                return f"[{encrypt_type.upper()}] {prompt} [Code Chameleon encrypted]"

        else:
            # Default simulation
            return f"[{converter_type} CONVERTED] {prompt}"

    except Exception as e:
        logger.warning("Error in converter simulation: %s", e)
        return f"[{converter_type} CONVERSION ERROR] {prompt}"
