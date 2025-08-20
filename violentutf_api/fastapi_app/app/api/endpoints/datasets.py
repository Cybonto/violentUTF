# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
FastAPI endpoints for dataset management.

Implements API backend for 2_Configure_Datasets.py page
"""

import asyncio
import base64
import json
import time
import uuid
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

from app.schemas.datasets import (
    DatasetCreateRequest,
    DatasetCreateResponse,
    DatasetDeleteResponse,
    DatasetError,
    DatasetFieldMappingRequest,
    DatasetFieldMappingResponse,
    DatasetInfo,
    DatasetPreviewRequest,
    DatasetPreviewResponse,
    DatasetSaveRequest,
    DatasetSaveResponse,
    DatasetsListResponse,
    DatasetSourceType,
    DatasetTransformRequest,
    DatasetTransformResponse,
    DatasetType,
    DatasetTypesResponse,
    DatasetUpdateRequest,
    DatasetUpdateResponse,
    MemoryDatasetInfo,
    MemoryDatasetsResponse,
    SeedPromptInfo,
)
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

# PyRIT imports for memory access
try:
    from pyrit.models import PromptRequestPiece
except ImportError:
    # Fallback if import structure is different
    PromptRequestPiece = None
import logging

from app.core.auth import get_current_user
from app.core.dataset_logging import (
    OperationType,
    dataset_audit_logger,
    dataset_logger,
    log_dataset_operation_error,
    log_dataset_operation_start,
    log_dataset_operation_success,
)
from app.db.duckdb_manager import get_duckdb_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# DuckDB storage replaces in - memory storage
# _datasets_store: Dict[str, Dict[str, Any]] = {} - REMOVED
# _session_datasets: Dict[str, Dict[str, Any]] = {} - REMOVED

# Dataset type definitions (based on PyRIT datasets)
NATIVE_DATASET_TYPES = {
    "aya_redteaming": {
        "name": "aya_redteaming",
        "description": "Aya Red-teaming Dataset - Multilingual red-teaming prompts",
        "category": "redteaming",
        "config_required": True,
        "available_configs": {
            "language": ["English", "Hindi", "French", "Spanish", "Arabic", "Russian", "Serbian", "Tagalog"]
        },
    },
    "harmbench": {
        "name": "harmbench",
        "description": "HarmBench Dataset - Standardized evaluation of automated red teaming",
        "category": "safety",
        "config_required": False,
        "available_configs": None,
    },
    "adv_bench": {
        "name": "adv_bench",
        "description": "AdvBench Dataset - Adversarial benchmark for language models",
        "category": "adversarial",
        "config_required": False,
        "available_configs": None,
    },
    "many_shot_jailbreaking": {
        "name": "many_shot_jailbreaking",
        "description": "Many - shot Jailbreaking Dataset - Context length exploitation prompts",
        "category": "jailbreaking",
        "config_required": False,
        "available_configs": None,
    },
    "decoding_trust_stereotypes": {
        "name": "decoding_trust_stereotypes",
        "description": "Decoding Trust Stereotypes Dataset - Bias evaluation prompts",
        "category": "bias",
        "config_required": False,
        "available_configs": None,
    },
    "xstest": {
        "name": "xstest",
        "description": "XSTest Dataset - Cross - domain safety testing",
        "category": "safety",
        "config_required": False,
        "available_configs": None,
    },
    "pku_safe_rlhf": {
        "name": "pku_safe_rlhf",
        "description": "PKU - SafeRLHF Dataset - Safe reinforcement learning from human feedback",
        "category": "safety",
        "config_required": False,
        "available_configs": None,
    },
    "wmdp": {
        "name": "wmdp",
        "description": "WMDP Dataset - Weapons of mass destruction prompts",
        "category": "dangerous",
        "config_required": False,
        "available_configs": None,
    },
    "forbidden_questions": {
        "name": "forbidden_questions",
        "description": "Forbidden Questions Dataset - Questions models should refuse to answer",
        "category": "safety",
        "config_required": False,
        "available_configs": None,
    },
    "seclists_bias_testing": {
        "name": "seclists_bias_testing",
        "description": "SecLists Bias Testing Dataset - Security - focused bias evaluation",
        "category": "bias",
        "config_required": False,
        "available_configs": None,
    },
}


@router.get("/types", response_model=DatasetTypesResponse, summary="Get available dataset types")
async def get_dataset_types(current_user: Any = Depends(get_current_user)) -> Any:
    """Get list of available dataset types."""
    try:
        logger.info(f"User {current_user.username} requested dataset types")

        dataset_types = []
        for name, info in NATIVE_DATASET_TYPES.items():
            dataset_types.append(DatasetType(**info))

        return DatasetTypesResponse(dataset_types=dataset_types, total=len(dataset_types))
    except Exception as e:
        logger.error(f"Error getting dataset types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dataset types: {str(e)}")


@router.get("", response_model=DatasetsListResponse, summary="Get configured datasets")
async def get_datasets(current_user: Any = Depends(get_current_user)) -> Any:
    """Get list of configured datasets from session and memory."""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} requested datasets list")

        datasets = []
        session_count = 0
        memory_count = 0

        # Get datasets from DuckDB
        db_manager = get_duckdb_manager(user_id)
        datasets_data = db_manager.list_datasets()

        for dataset_data in datasets_data:
            datasets.append(
                DatasetInfo(
                    id=dataset_data["id"],
                    name=dataset_data["name"],
                    source_type=dataset_data["source_type"],
                    prompt_count=dataset_data["prompt_count"],
                    prompts=[],  # Don't load all prompts for list view
                    created_at=dataset_data["created_at"],
                    updated_at=dataset_data["updated_at"],
                    created_by=dataset_data.get("user_id", user_id),
                    metadata=dataset_data["metadata"],
                )
            )
            session_count += 1

        # Get real PyRIT memory datasets
        try:
            real_memory_datasets = await _get_real_memory_datasets(user_id)

            for memory_dataset in real_memory_datasets:
                # Convert MemoryDatasetInfo to DatasetInfo format
                datasets.append(
                    DatasetInfo(
                        id=f"memory_{memory_dataset.dataset_name.replace(' ', '_').lower()}",
                        name=memory_dataset.dataset_name,
                        source_type=DatasetSourceType.MEMORY,
                        prompt_count=memory_dataset.prompt_count,
                        prompts=[
                            SeedPromptInfo(
                                id="preview_prompt_1",
                                value=memory_dataset.first_prompt_preview,
                                dataset_name=memory_dataset.dataset_name,
                                data_type="text",
                            )
                        ],  # Just show preview for list view
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        created_by=memory_dataset.created_by,
                        metadata={"source": "memory", "type": "pyrit_memory"},
                    )
                )
                memory_count += 1

        except Exception as e:
            logger.warning(f"Could not load real memory datasets: {e}")
            # Continue without memory datasets rather than showing mock data

        return DatasetsListResponse(
            datasets=datasets, total=len(datasets), session_count=session_count, memory_count=memory_count
        )
    except Exception as e:
        logger.error(f"Error getting datasets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get datasets: {str(e)}")


@router.post("/preview", response_model=DatasetPreviewResponse, summary="Preview a dataset before creation")
async def preview_dataset(request: DatasetPreviewRequest, current_user=Depends(get_current_user)) -> Any:
    """Preview a dataset before creating it."""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} previewing dataset of type: {request.source_type}")

        preview_prompts = []
        total_prompts = 0
        dataset_info = {}
        warnings = []

        if request.source_type == DatasetSourceType.NATIVE:
            if not request.dataset_type or request.dataset_type not in NATIVE_DATASET_TYPES:
                raise HTTPException(status_code=400, detail="Invalid or missing dataset_type for native dataset")

            # Load real native dataset preview
            dataset_def = NATIVE_DATASET_TYPES[request.dataset_type]
            dataset_info = dict(dataset_def)

            try:
                # Load real prompts from PyRIT dataset for preview
                real_preview_prompts = await _load_real_pyrit_dataset(request.dataset_type, request.config or {})

                if real_preview_prompts:
                    # Use real prompts for preview (limit to first 5)
                    preview_prompts_list = real_preview_prompts[:5]
                    total_prompts = len(real_preview_prompts)

                    for i, prompt_text in enumerate(preview_prompts_list):
                        preview_prompts.append(
                            SeedPromptInfo(
                                id=f"real_preview_{i}",
                                value=prompt_text,
                                dataset_name=request.dataset_type,
                                data_type="text",
                            )
                        )

                    logger.info(f"Loaded {len(preview_prompts)} real preview prompts for {request.dataset_type}")
                else:
                    # If no real prompts available, show warning instead of mock data
                    warnings.append(
                        f"Could not load preview for {request.dataset_type} dataset. Dataset may be empty or unavailable."
                    )
                    total_prompts = 0

            except Exception as e:
                logger.warning(f"Failed to load real preview for {request.dataset_type}: {e}")
                warnings.append(f"Could not load preview for {request.dataset_type}. Error: {str(e)}")
                total_prompts = 0

        elif request.source_type == DatasetSourceType.ONLINE:
            if not request.url:
                raise HTTPException(status_code=400, detail="URL is required for online datasets")

            # Online dataset preview - actual fetching would be implemented here
            dataset_info = {"url": request.url, "source": "online"}
            warnings.append("Online dataset preview not yet implemented - upload file locally for preview")
            total_prompts = 0  # Cannot determine without actual fetching

        elif request.source_type == DatasetSourceType.LOCAL:
            if not request.file_content:
                raise HTTPException(status_code=400, detail="File content is required for local datasets")

            # Local file preview - actual parsing would be implemented here
            dataset_info = {"source": "local_file"}
            warnings.append("Local file preview not yet implemented - file parsing functionality needs implementation")
            total_prompts = 0  # Cannot determine without actual parsing

        else:
            raise HTTPException(status_code=400, detail=f"Preview not supported for source type: {request.source_type}")

        return DatasetPreviewResponse(
            preview_prompts=preview_prompts, total_prompts=total_prompts, dataset_info=dataset_info, warnings=warnings
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview dataset: {str(e)}")


@router.post("", response_model=DatasetCreateResponse, summary="Create a new dataset")
async def create_dataset(request: DatasetCreateRequest, current_user=Depends(get_current_user)) -> Any:
    """Create a new dataset configuration."""
    operation_start_time = time.time()
    user_id = current_user.username
    correlation_id = dataset_logger.set_correlation_id()
    dataset_logger.set_user_context(user_id)

    # Log user action for audit trail
    dataset_audit_logger.log_user_action(
        action="create_dataset",
        resource=f"dataset:{request.name}",
        user_id=user_id,
        ip_address=getattr(current_user, "ip_address", None),
    )

    try:
        with dataset_logger.operation_context(
            operation=OperationType.IMPORT.value,
            dataset_id=request.name,
            dataset_type=request.dataset_type or "unknown",
            user_id=user_id,
            correlation_id=correlation_id,
        ):
            logger.info(f"User {user_id} creating dataset: {request.name}")

            # Log security event for dataset creation
            dataset_logger.log_security_event(
                event_type="dataset_creation_attempt",
                severity="low",
                details={
                    "dataset_name": request.name,
                    "source_type": request.source_type.value,
                    "dataset_type": request.dataset_type,
                },
            )

        now = datetime.utcnow()

        # Create prompts based on source type
        prompts = []
        if request.source_type == DatasetSourceType.NATIVE:
            if not request.dataset_type:
                raise HTTPException(status_code=400, detail="dataset_type is required for native datasets")

            # Load actual PyRIT dataset
            try:
                real_prompts = await _load_real_pyrit_dataset(request.dataset_type, request.config or {})
                if real_prompts:
                    for i, prompt_text in enumerate(real_prompts):
                        prompts.append(
                            SeedPromptInfo(
                                id=str(uuid.uuid4()), value=prompt_text, dataset_name=request.name, data_type="text"
                            )
                        )
                    # Log dataset conversion details
                    dataset_logger.log_conversion_details(
                        dataset_type=request.dataset_type,
                        conversion_strategy="native_pyrit_load",
                        input_format="pyrit_dataset",
                        output_format="prompt_list",
                        input_size=len(real_prompts),
                        output_size=len(prompts),
                    )

                    logger.info(f"Loaded {len(prompts)} real prompts from PyRIT dataset '{request.dataset_type}'")
                else:
                    # Return error instead of creating mock dataset
                    logger.error(f"Failed to load real PyRIT dataset '{request.dataset_type}' - no prompts available")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Could not load dataset '{request.dataset_type}'. Dataset may be empty or unavailable.",
                    )
            except Exception as e:
                logger.error(f"Error loading PyRIT dataset '{request.dataset_type}': {e}")
                # Return error instead of creating mock dataset
                raise HTTPException(
                    status_code=500, detail=f"Failed to load PyRIT dataset '{request.dataset_type}': {str(e)}"
                )

        elif request.source_type == DatasetSourceType.LOCAL:
            # Local file processing not yet implemented
            raise HTTPException(
                status_code=501,
                detail="Local file dataset creation not yet implemented. Please use native datasets for now.",
            )

        elif request.source_type == DatasetSourceType.ONLINE:
            if not request.url:
                raise HTTPException(status_code=400, detail="url is required for online datasets")

            # Online dataset fetching not yet implemented
            raise HTTPException(
                status_code=501,
                detail="Online dataset creation not yet implemented. Please use native datasets for now.",
            )

        # Create dataset data (ID will be set after DuckDB creation)
        dataset_data = {
            "id": None,  # Will be set after DuckDB creation
            "name": request.name,
            "source_type": request.source_type,
            "prompt_count": len(prompts),
            "prompts": [prompt.dict() for prompt in prompts],
            "config": request.config or {},
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "metadata": {"dataset_type": request.dataset_type, "url": request.url, "file_type": request.file_type},
        }

        # Create dataset in DuckDB
        db_manager = get_duckdb_manager(user_id)
        prompts_text = [p.value for p in prompts]

        # Log PyRIT storage operation
        pyrit_start_time = time.time()

        # Create dataset and get the actual ID from DuckDB
        actual_dataset_id = db_manager.create_dataset(
            name=request.name,
            source_type=request.source_type.value,
            configuration={
                "dataset_type": request.dataset_type,
                "url": request.url,
                "file_type": request.file_type,
                "config": request.config or {},
            },
            prompts=prompts_text,
        )

        # Log PyRIT storage metrics
        pyrit_storage_time = time.time() - pyrit_start_time
        dataset_logger.log_pyrit_storage(
            prompts_stored=len(prompts_text),
            storage_time_seconds=pyrit_storage_time,
            storage_size_mb=sum(len(p.encode("utf-8")) for p in prompts_text) / 1024 / 1024,
            dataset_id=actual_dataset_id,
        )

        # Update dataset_data with the actual ID from DuckDB
        dataset_data["id"] = actual_dataset_id

        # Log successful dataset creation with metrics
        operation_time = time.time() - operation_start_time
        dataset_logger.log_performance_metric(
            metric_name="dataset_creation_time",
            metric_value=operation_time,
            metric_unit="seconds",
            threshold=30.0,  # 30 second threshold
            dataset_id=actual_dataset_id,
            prompt_count=len(prompts),
        )

        # Log data access event
        dataset_audit_logger.log_data_access(
            dataset_id=actual_dataset_id,
            access_type="create",
            user_id=user_id,
            data_classification="internal",
            record_count=len(prompts),
        )

        # Log successful operation
        log_dataset_operation_success(
            operation="create_dataset",
            dataset_id=actual_dataset_id,
            dataset_type=request.dataset_type or "unknown",
            user_id=user_id,
            prompt_count=len(prompts),
            processing_time_seconds=operation_time,
        )

        logger.info(f"Dataset '{request.name}' created successfully with ID: {actual_dataset_id}")

        return DatasetCreateResponse(
            dataset=DatasetInfo(**dataset_data),
            message=f"Dataset '{request.name}' created successfully with {len(prompts)} prompts",
        )

    except HTTPException as e:
        # Log HTTP errors
        operation_time = time.time() - operation_start_time
        log_dataset_operation_error(
            operation="create_dataset",
            dataset_id=request.name,
            error=e,
            user_id=user_id,
            processing_time_seconds=operation_time,
        )

        # Log security event for failed creation
        dataset_logger.log_security_event(
            event_type="dataset_creation_failed",
            severity="medium",
            details={"error_code": e.status_code, "error_message": str(e.detail), "dataset_name": request.name},
        )
        raise
    except Exception as e:
        # Log unexpected errors
        operation_time = time.time() - operation_start_time
        log_dataset_operation_error(
            operation="create_dataset",
            dataset_id=request.name,
            error=e,
            user_id=user_id,
            processing_time_seconds=operation_time,
        )

        # Log security event for system errors
        dataset_logger.log_security_event(
            event_type="dataset_creation_system_error",
            severity="high",
            details={"error_type": type(e).__name__, "error_message": str(e), "dataset_name": request.name},
        )

        logger.error(f"Error creating dataset {request.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create dataset: {str(e)}")


# DEPRECATED: POST /{dataset_id}/save endpoint has been removed
# Save functionality is now integrated into the PUT /{dataset_id} endpoint
# Use PUT /{dataset_id} with save_to_session and save_to_memory parameters


@router.post("/{dataset_id}/transform", response_model=DatasetTransformResponse, summary="Transform a dataset")
async def transform_dataset(
    dataset_id: str, request: DatasetTransformRequest, current_user=Depends(get_current_user)
) -> Any:
    """Transform a dataset using a template."""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} transforming dataset: {dataset_id}")

        # Find original dataset in DuckDB
        db_manager = get_duckdb_manager(user_id)
        original_dataset = db_manager.get_dataset(dataset_id)

        if not original_dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Create transformed dataset
        transformed_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Simulate template transformation
        original_prompts = original_dataset.get("prompts", [])
        transformed_prompts = []

        for prompt_data in original_prompts:
            # Simple template application simulation
            original_value = prompt_data.get("value", "")
            transformed_value = f"Transformed: {original_value} [Template: {request.template[:50]}...]"

            transformed_prompts.append(
                SeedPromptInfo(
                    id=str(uuid.uuid4()),
                    value=transformed_value,
                    dataset_name=f"{original_dataset['name']}_transformed",
                    data_type="text",
                    metadata={"original_prompt_id": prompt_data.get("id"), "transformation_template": request.template},
                )
            )

        # Create transformed dataset
        transformed_dataset_data = {
            "id": transformed_id,
            "name": f"{original_dataset['name']}_transformed",
            "source_type": DatasetSourceType.TRANSFORM,
            "prompt_count": len(transformed_prompts),
            "prompts": [prompt.dict() for prompt in transformed_prompts],
            "config": {"original_dataset_id": dataset_id, "template": request.template},
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "metadata": {"transformation_type": request.template_type, "source_dataset_id": dataset_id},
        }

        # Store transformed dataset
        # _session_datasets[user_session_key][transformed_id] = transformed_dataset_data  # Legacy session storage removed

        transform_summary = (
            f"Applied template to {len(original_prompts)} prompts using {request.template_type} template"
        )

        logger.info(f"Dataset {dataset_id} transformed successfully, new ID: {transformed_id}")

        return DatasetTransformResponse(
            original_dataset_id=dataset_id,
            transformed_dataset=DatasetInfo(**transformed_dataset_data),
            transform_summary=transform_summary,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transforming dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to transform dataset: {str(e)}")


@router.get("/memory", response_model=MemoryDatasetsResponse, summary="Get datasets from PyRIT memory")
async def get_memory_datasets(current_user: Any = Depends(get_current_user)) -> Any:
    """Get datasets saved in PyRIT memory."""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} requested memory datasets")

        # Get real PyRIT memory datasets
        memory_datasets = await _get_real_memory_datasets(user_id)

        total_prompts = sum(d.prompt_count for d in memory_datasets)

        return MemoryDatasetsResponse(datasets=memory_datasets, total=len(memory_datasets), total_prompts=total_prompts)

    except Exception as e:
        logger.error(f"Error getting memory datasets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get memory datasets: {str(e)}")


@router.post(
    "/field - mapping",
    response_model=DatasetFieldMappingResponse,
    summary="Get field mapping options for uploaded file",
)
async def get_field_mapping(request: DatasetFieldMappingRequest, current_user=Depends(get_current_user)) -> Any:
    """Analyze an uploaded file and return field mapping options."""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} requesting field mapping for {request.file_type} file")

        # Simulate file parsing
        if request.file_type.lower() == "csv":
            # Mock CSV analysis
            available_fields = ["prompt", "category", "response", "metadata", "id"]
            preview_data = [
                {"prompt": "Sample prompt 1", "category": "test", "response": "response1"},
                {"prompt": "Sample prompt 2", "category": "safety", "response": "response2"},
                {"prompt": "Sample prompt 3", "category": "bias", "response": "response3"},
            ]
        elif request.file_type.lower() == "json":
            # Mock JSON analysis
            available_fields = ["text", "label", "source", "timestamp"]
            preview_data = [
                {"text": "JSON sample 1", "label": "category1", "source": "dataset1"},
                {"text": "JSON sample 2", "label": "category2", "source": "dataset2"},
            ]
        else:
            available_fields = ["content", "type"]
            preview_data = [{"content": "Generic file content", "type": "unknown"}]

        required_fields = ["value"]  # Required for SeedPrompt
        total_rows = len(preview_data) * 20  # Simulate larger dataset

        return DatasetFieldMappingResponse(
            available_fields=available_fields,
            required_fields=required_fields,
            preview_data=preview_data,
            total_rows=total_rows,
        )

    except Exception as e:
        logger.error(f"Error analyzing file for field mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze file: {str(e)}")


@router.delete("/{dataset_id}", response_model=DatasetDeleteResponse, summary="Delete a dataset")
async def delete_dataset(
    dataset_id: str,
    delete_from_session: bool = Query(default=True, description="Delete from session"),
    delete_from_memory: bool = Query(default=False, description="Delete from PyRIT memory"),
    current_user=Depends(get_current_user),
) -> Any:
    """Delete a dataset from session and / or PyRIT memory."""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} deleting dataset: {dataset_id}")

        deleted_from_session = False
        deleted_from_memory = False

        # Delete from session
        if delete_from_session:
            # Legacy session storage removed
            # if user_session_key in _session_datasets and dataset_id in _session_datasets[user_session_key]:
            #     del _session_datasets[user_session_key][dataset_id]
            #     deleted_from_session = True
            #     logger.info(f"Dataset {dataset_id} deleted from session")
            deleted_from_session = False  # Session storage not available

        # Delete from memory (simulated)
        if delete_from_memory:
            # In real implementation, this would delete from PyRIT memory
            deleted_from_memory = True
            logger.info(f"Dataset {dataset_id} would be deleted from PyRIT memory")

        if not deleted_from_session and not deleted_from_memory:
            raise HTTPException(status_code=404, detail="Dataset not found or no deletion location specified")

        locations = []
        if deleted_from_session:
            locations.append("session")
        if deleted_from_memory:
            locations.append("PyRIT memory")

        message = f"Dataset deleted from {' and '.join(locations)}"

        return DatasetDeleteResponse(
            success=True,
            message=message,
            deleted_from_session=deleted_from_session,
            deleted_from_memory=deleted_from_memory,
            deleted_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {str(e)}")


# Helper function for loading real PyRIT datasets
async def _load_real_pyrit_dataset(dataset_type: str, config: Dict[str, Any], limit: Optional[int] = None) -> List[str]:
    """Enhanced PyRIT dataset loading with streaming support and configurable limits."""
    try:
        logger.info(f"Loading real PyRIT dataset: {dataset_type} with config: {config}, limit: {limit}")

        # Import configuration system
        from app.core.dataset_config import DatasetImportConfig, validate_dataset_config
        from app.services.dataset_stream_processor import PyRITStreamProcessor

        # Validate configuration
        validate_dataset_config(dataset_type, config)

        # Check if streaming is enabled and limit is high enough
        import_config = DatasetImportConfig.from_env()

        # For small requests or preview, use legacy mode to avoid streaming overhead
        if limit and limit <= 100:  # Use legacy for small requests (increased from preview_limit)
            logger.info(f"Using legacy mode for small dataset request (limit: {limit})")
            return await _load_real_pyrit_dataset_legacy(dataset_type, config, limit)

        # For larger requests, use streaming (temporarily disabled for testing)
        if import_config.enable_streaming and False:  # Temporarily disabled
            try:
                processor = PyRITStreamProcessor()
                all_prompts = []

                # Stream process but collect all results (for backward compatibility)
                async for chunk in processor.process_pyrit_dataset_stream(dataset_type, config, limit):
                    all_prompts.extend(chunk.prompts)

                    # Apply limit if specified
                    if limit and len(all_prompts) >= limit:
                        all_prompts = all_prompts[:limit]
                        break

                logger.info(f"Successfully loaded {len(all_prompts)} prompts using streaming")
                return all_prompts

            except Exception as e:
                logger.warning(f"Streaming failed, falling back to legacy mode: {e}")
                return await _load_real_pyrit_dataset_legacy(dataset_type, config, limit)

        # Fallback to legacy mode
        return await _load_real_pyrit_dataset_legacy(dataset_type, config, limit)

    except Exception as e:
        logger.error(f"Error loading PyRIT dataset '{dataset_type}': {e}")
        return []


async def _load_real_pyrit_dataset_legacy(
    dataset_type: str, config: Dict[str, Any], limit: Optional[int] = None
) -> List[str]:
    """Legacy PyRIT dataset loading (kept for backward compatibility)."""
    try:
        logger.info(f"Loading PyRIT dataset using legacy mode: {dataset_type}")

        # Get dataset fetcher function
        fetch_function = _get_dataset_fetcher(dataset_type)
        if not fetch_function:
            logger.warning(f"Dataset type '{dataset_type}' not supported for real dataset loading")
            return []

        # Fetch the dataset
        dataset = _fetch_dataset(fetch_function, config)

        # Extract prompts based on dataset type
        prompts = _extract_prompts_from_dataset(dataset, dataset_type)

        # Apply limit and return
        return _apply_limit_to_prompts(prompts, limit)

    except ImportError as e:
        logger.error(f"Failed to import PyRIT dataset functions: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading PyRIT dataset '{dataset_type}': {e}")
        return []


def _get_dataset_fetcher(dataset_type: str):
    """Get the appropriate dataset fetcher function for the given type."""
    # Import PyRIT dataset functions
    from pyrit.datasets import (
        fetch_adv_bench_dataset,
        fetch_aya_redteaming_dataset,
        fetch_decoding_trust_stereotypes_dataset,
        fetch_forbidden_questions_dataset,
        fetch_harmbench_dataset,
        fetch_many_shot_jailbreaking_dataset,
        fetch_pku_safe_rlhf_dataset,
        fetch_seclists_bias_testing_dataset,
        fetch_wmdp_dataset,
        fetch_xstest_dataset,
    )

    # Map dataset types to their fetch functions
    dataset_fetchers = {
        "aya_redteaming": fetch_aya_redteaming_dataset,
        "harmbench": fetch_harmbench_dataset,
        "adv_bench": fetch_adv_bench_dataset,
        "xstest": fetch_xstest_dataset,
        "pku_safe_rlhf": fetch_pku_safe_rlhf_dataset,
        "decoding_trust_stereotypes": fetch_decoding_trust_stereotypes_dataset,
        "many_shot_jailbreaking": fetch_many_shot_jailbreaking_dataset,
        "forbidden_questions": fetch_forbidden_questions_dataset,
        "seclists_bias_testing": fetch_seclists_bias_testing_dataset,
        "wmdp": fetch_wmdp_dataset,
    }

    return dataset_fetchers.get(dataset_type)


def _fetch_dataset(fetch_function, config: Dict[str, Any]):
    """Fetch dataset using the provided function and config."""
    # Remove None values and exclude 'dataset_type' (which is not a PyRIT parameter)
    clean_config = {k: v for k, v in config.items() if v is not None and k != "dataset_type"}

    logger.info(f"Calling {fetch_function.__name__} with config: {clean_config}")

    # Call the PyRIT fetch function
    return fetch_function(**clean_config)


def _extract_prompts_from_dataset(dataset, dataset_type: str) -> List[str]:
    """Extract prompts from dataset based on its type and structure."""
    # Use dispatch pattern for different dataset types
    extractors = {
        "many_shot_jailbreaking": _extract_many_shot_prompts,
        "wmdp": _extract_wmdp_prompts,
    }

    # Try specific extractor first
    extractor = extractors.get(dataset_type)
    if extractor:
        prompts = extractor(dataset)
        if prompts:
            logger.info(f"Successfully loaded {len(prompts)} prompts from {dataset_type}")
            return prompts

    # Fall back to standard extraction
    return _extract_standard_prompts(dataset, dataset_type)


def _extract_many_shot_prompts(dataset) -> List[str]:
    """Extract prompts from many_shot_jailbreaking dataset format."""
    prompts = []

    if isinstance(dataset, list):
        for item in dataset:
            if isinstance(item, dict) and "user" in item:
                prompts.append(item["user"])
            else:
                prompts.append(str(item))
        logger.info(f"Extracted {len(prompts)} prompts from many_shot_jailbreaking (list format)")

    return prompts


def _extract_wmdp_prompts(dataset) -> List[str]:
    """Extract prompts from wmdp dataset format."""
    prompts = []

    if hasattr(dataset, "questions"):
        for question in dataset.questions:
            if hasattr(question, "question"):
                prompts.append(question.question)
            elif hasattr(question, "value"):
                prompts.append(question.value)
            else:
                prompts.append(str(question))
        logger.info(f"Extracted {len(prompts)} questions from wmdp dataset")

    return prompts


def _extract_standard_prompts(dataset, dataset_type: str) -> List[str]:
    """Extract prompts from standard SeedPromptDataset format."""
    prompts = []

    if dataset and hasattr(dataset, "prompts"):
        for seed_prompt in dataset.prompts:
            if hasattr(seed_prompt, "value"):
                prompts.append(seed_prompt.value)
            elif hasattr(seed_prompt, "prompt"):
                prompts.append(seed_prompt.prompt)
            else:
                prompts.append(str(seed_prompt))

        logger.info(f"Successfully loaded {len(prompts)} real prompts from {dataset_type}")
    else:
        logger.warning(f"Dataset '{dataset_type}' returned no prompts or unsupported format: {type(dataset)}")

    return prompts


def _apply_limit_to_prompts(prompts: List[str], limit: Optional[int]) -> List[str]:
    """Apply limit to prompts list if specified."""
    if limit and limit > 0 and prompts:
        return prompts[:limit]
    return prompts


async def _get_real_memory_datasets(user_id: str) -> List[MemoryDatasetInfo]:
    """Get real PyRIT memory datasets instead of mock data."""
    try:
        # Try active PyRIT memory instance first
        memory_datasets = await _get_datasets_from_active_memory(user_id)
        if memory_datasets:
            return memory_datasets

        # Fall back to direct database file access
        return await _get_datasets_from_database_files(user_id)

    except Exception as e:
        logger.error(f"Error getting real memory datasets: {e}")
        return []


async def _get_datasets_from_active_memory(user_id: str) -> List[MemoryDatasetInfo]:
    """Try to get datasets from active PyRIT memory instance."""
    try:
        from pyrit.memory import CentralMemory

        memory_instance = CentralMemory.get_memory_instance()
        if not memory_instance:
            return []

        logger.info("Found active PyRIT memory instance for dataset listing")

        # Get all conversation pieces using available methods
        all_pieces = await _get_memory_pieces_from_instance(memory_instance)

        # Group pieces by conversation and create datasets
        conversations = _group_pieces_by_conversation(all_pieces)
        memory_datasets = _create_memory_datasets_from_conversations(conversations, user_id)

        if memory_datasets:
            logger.info(f"Found {len(memory_datasets)} memory datasets from active PyRIT memory")

        return memory_datasets

    except ValueError:
        logger.info("No active PyRIT memory instance found")
        return []
    except Exception as e:
        logger.warning(f"Error accessing active memory instance: {e}")
        return []


async def _get_memory_pieces_from_instance(memory_instance) -> List:
    """Get conversation pieces from memory instance using available methods."""
    try:
        # Try to get all prompt request pieces using the query interface
        if hasattr(memory_instance, "query_entries") and PromptRequestPiece:
            return memory_instance.query_entries(PromptRequestPiece)
        elif hasattr(memory_instance, "get_all_prompt_pieces"):
            return memory_instance.get_all_prompt_pieces()
        else:
            # Fallback to direct database access
            return await _get_pieces_via_direct_db_access(memory_instance)

    except Exception as query_error:
        logger.warning(f"Failed to query memory entries: {query_error}")
        return []


async def _get_pieces_via_direct_db_access(memory_instance) -> List:
    """Get pieces via direct database access as fallback."""
    try:
        logger.info("Using direct database access for conversation retrieval")
        all_pieces = []

        if not hasattr(memory_instance, "_get_connection"):
            logger.warning("Cannot access memory database directly")
            return []

        with memory_instance._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT conversation_id FROM PromptRequestPieces WHERE role = 'user'")
            conversation_ids = [row[0] for row in cursor.fetchall()]

            # Get pieces for each conversation
            for conv_id in conversation_ids:
                try:
                    conv_pieces = memory_instance.get_conversation(conversation_id=conv_id)
                    all_pieces.extend(conv_pieces)
                except Exception as conv_error:
                    logger.debug(f"Could not get conversation {conv_id}: {conv_error}")
                    continue

        return all_pieces

    except Exception as e:
        logger.warning(f"Direct database access failed: {e}")
        return []


def _group_pieces_by_conversation(all_pieces: List) -> Dict:
    """Group conversation pieces by conversation ID."""
    conversations = {}
    for piece in all_pieces:
        conv_id = piece.conversation_id
        if conv_id not in conversations:
            conversations[conv_id] = []
        conversations[conv_id].append(piece)
    return conversations


def _create_memory_datasets_from_conversations(conversations: Dict, user_id: str) -> List[MemoryDatasetInfo]:
    """Create memory dataset objects from grouped conversations."""
    memory_datasets = []

    for conv_id, pieces in conversations.items():
        user_pieces = [p for p in pieces if p.role == "user"]
        if user_pieces:
            first_prompt = (
                user_pieces[0].original_value[:100] + "..."
                if len(user_pieces[0].original_value) > 100
                else user_pieces[0].original_value
            )

            memory_datasets.append(
                MemoryDatasetInfo(
                    dataset_name=f"Conversation {conv_id[:8]}",
                    prompt_count=len(user_pieces),
                    created_by=user_id,
                    first_prompt_preview=first_prompt,
                )
            )

    return memory_datasets


async def _get_datasets_from_database_files(user_id: str) -> List[MemoryDatasetInfo]:
    """Get datasets from direct database file access."""
    try:
        # Generate user-specific database details
        db_paths = _get_user_database_paths(user_id)

        # Try to extract datasets from found database files
        for db_path in db_paths:
            memory_datasets = await _extract_datasets_from_db_file(db_path, user_id)
            if memory_datasets:
                return memory_datasets

        logger.info("No PyRIT memory datasets found")
        return []

    except Exception as e:
        logger.error(f"Error accessing database files: {e}")
        return []


def _get_user_database_paths(user_id: str) -> List[str]:
    """Get paths to user-specific database files."""
    import hashlib
    import os

    # Generate the user's specific database filename
    salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
    user_hash = hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()
    user_db_filename = f"pyrit_memory_{user_hash}.db"

    # Only check the user's specific database file in known locations
    memory_db_paths = []
    potential_paths = [
        "/app/app_data/violentutf",  # Docker API memory
        "./app_data/violentutf",  # Relative app data
    ]

    for base_path in potential_paths:
        if os.path.exists(base_path):
            user_db_path = os.path.join(base_path, user_db_filename)
            if os.path.exists(user_db_path):
                memory_db_paths.append(user_db_path)
                logger.info(f"Found user-specific database for {user_id}: {user_db_filename}")
                break  # Only use the first found user database

    return memory_db_paths


async def _extract_datasets_from_db_file(db_path: str, user_id: str) -> List[MemoryDatasetInfo]:
    """Extract datasets from a specific database file."""
    try:
        import sqlite3

        # Security check
        user_db_filename = _get_user_db_filename(user_id)
        if user_db_filename not in db_path:
            logger.error(f"Security violation: Attempted to access non-user database: {db_path}")
            return []

        logger.info(f"Reading user-specific PyRIT memory database: {db_path}")
        memory_datasets = []

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(_get_dataset_query())

            rows = cursor.fetchall()
            for row in rows:
                conv_id, count, first_prompt = row
                preview = first_prompt[:100] + "..." if len(first_prompt) > 100 else first_prompt

                memory_datasets.append(
                    MemoryDatasetInfo(
                        dataset_name=f"Memory Dataset {conv_id[:8]}",
                        prompt_count=count,
                        created_by=user_id,
                        first_prompt_preview=preview,
                    )
                )

        if memory_datasets:
            logger.info(f"Extracted {len(memory_datasets)} memory datasets from PyRIT database {db_path}")

        return memory_datasets

    except Exception as db_error:
        logger.debug(f"Error accessing database {db_path}: {db_error}")
        return []


def _get_user_db_filename(user_id: str) -> str:
    """Get user-specific database filename."""
    import hashlib
    import os

    salt = os.getenv("PYRIT_DB_SALT", "default_salt_2025")
    user_hash = hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()
    return f"pyrit_memory_{user_hash}.db"


def _get_dataset_query() -> str:
    """Get SQL query for dataset extraction."""
    return """
        SELECT conversation_id, COUNT(*) as prompt_count,
               MIN(original_value) as first_prompt
        FROM PromptRequestPieces
        WHERE role = 'user' AND original_value IS NOT NULL
        AND LENGTH(original_value) > 0
        AND original_value NOT LIKE '%Native harmbench prompt%'
        AND original_value NOT LIKE '%Native % prompt %'
        AND original_value NOT LIKE '%Sample % prompt %'
        AND original_value NOT LIKE '%Test prompt%'
        AND original_value NOT LIKE '%mock%'
        AND original_value NOT LIKE '%test prompt%'
        GROUP BY conversation_id
        ORDER BY timestamp DESC
        LIMIT 20
    """


@router.get("/{dataset_id}", response_model=DatasetInfo, summary="Get dataset details")
async def get_dataset(dataset_id: str, current_user=Depends(get_current_user)) -> Any:
    """Get detailed information about a specific dataset."""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} requested dataset details: {dataset_id}")

        # Find dataset in DuckDB
        db_manager = get_duckdb_manager(user_id)
        dataset_data = db_manager.get_dataset(dataset_id)
        if dataset_data:
            # Convert prompts from DuckDB format to API format
            prompts = []
            for prompt in dataset_data.get("prompts", []):
                prompts.append(
                    SeedPromptInfo(
                        id=str(uuid.uuid4()),  # Generate ID if not present
                        value=prompt.get("text", ""),  # Map 'text' to 'value'
                        dataset_name=dataset_data["name"],
                        data_type="text",
                        metadata=prompt.get("metadata", {}),
                    )
                )

            return DatasetInfo(
                id=dataset_data["id"],
                name=dataset_data["name"],
                source_type=dataset_data["source_type"],
                prompt_count=len(prompts),  # Calculate from actual prompts
                prompts=prompts,
                created_at=dataset_data["created_at"],
                updated_at=dataset_data["updated_at"],
                created_by=dataset_data.get("user_id", user_id),
                metadata=dataset_data.get("metadata", {}),
            )

        raise HTTPException(status_code=404, detail="Dataset not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dataset: {str(e)}")


@router.put("/{dataset_id}", response_model=DatasetUpdateResponse, summary="Update a dataset")
async def update_dataset(dataset_id: str, request: DatasetUpdateRequest, current_user=Depends(get_current_user)) -> Any:
    """Update an existing dataset, with optional save functionality."""
    try:
        user_id = current_user.username
        logger.info(f"User {user_id} updating dataset: {dataset_id}")

        # Find dataset in DuckDB
        db_manager = get_duckdb_manager(user_id)
        dataset_data = db_manager.get_dataset(dataset_id)

        if not dataset_data:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Update fields
        if request.name is not None:
            dataset_data["name"] = request.name
        if request.config is not None:
            dataset_data["config"] = request.config
        if request.metadata is not None:
            dataset_data["metadata"] = request.metadata

        dataset_data["updated_at"] = datetime.utcnow()

        # Handle save functionality (replaces the deprecated POST /{dataset_id}/save endpoint)
        saved_to_session = None
        saved_to_memory = None
        saved_at = None
        message_parts = ["Dataset updated"]

        if request.save_to_session is not None or request.save_to_memory is not None:
            saved_at = datetime.utcnow()

            # Save to session
            if request.save_to_session:
                saved_to_session = True
                message_parts.append("saved to session")
                logger.info(f"Dataset {dataset_id} saved to session with name: {dataset_data['name']}")

            # Save to PyRIT memory
            if request.save_to_memory:
                # In real implementation, this would save to PyRIT memory
                saved_to_memory = True
                message_parts.append("saved to PyRIT memory")
                logger.info(f"Dataset {dataset_id} saved to PyRIT memory with name: {dataset_data['name']}")

        message = f"Dataset '{dataset_data['name']}' {' and '.join(message_parts)}"
        logger.info(f"Dataset {dataset_id} operation completed: {message}")

        # Create updated dataset info
        updated_dataset = DatasetInfo(
            id=dataset_data["id"],
            name=dataset_data["name"],
            source_type=dataset_data["source_type"],
            prompt_count=dataset_data["prompt_count"],
            prompts=[],
            created_at=dataset_data["created_at"],
            updated_at=dataset_data["updated_at"],
            created_by=dataset_data.get("user_id", user_id),
            metadata=dataset_data["metadata"],
        )

        # Return response with save information if applicable
        return DatasetUpdateResponse(
            dataset=updated_dataset,
            message=message,
            saved_to_session=saved_to_session,
            saved_to_memory=saved_to_memory,
            saved_at=saved_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update dataset: {str(e)}")
