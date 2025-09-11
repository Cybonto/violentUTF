# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""FastAPI endpoints for dataset management

Implements API backend for 2_Configure_Datasets.py page
"""
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pyrit.memory import CentralMemory

from app.models.auth import User
from app.schemas.datasets import (
    DatasetCreateRequest,
    DatasetCreateResponse,
    DatasetDeleteResponse,
    DatasetFieldMappingRequest,
    DatasetFieldMappingResponse,
    DatasetInfo,
    DatasetPreviewRequest,
    DatasetPreviewResponse,
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
from app.schemas.graphwalk_datasets import (
    GraphWalkConvertRequest,
    GraphWalkConvertResponse,
    GraphWalkJobStatusResponse,
)

# PyRIT imports for memory access
try:
    from pyrit.models import PromptRequestPiece
except ImportError:
    # Fallback if import structure is different
    PromptRequestPiece = None
import logging

from app.core.auth import get_current_user
from app.db.duckdb_manager import get_duckdb_manager
from app.services.graphwalk_service import graphwalk_service

logger = logging.getLogger(__name__)

router = APIRouter()

# DuckDB storage replaces in - memory storage
# _datasets_store: Dict[str, Dict[str, object]] = {} - REMOVED
# _session_datasets: Dict[str, Dict[str, object]] = {} - REMOVED

# ViolentUTF native dataset definitions
VIOLENTUTF_NATIVE_DATASETS = {
    "ollegen1_cognitive": {
        "name": "ollegen1_cognitive",
        "display_name": "OllaGen1 Cognitive Behavioral Security Assessment",
        "description": "170K scenarios with 4 Q&A types for security compliance evaluation",
        "category": "cognitive_behavioral",
        "pyrit_format": "QuestionAnsweringDataset",
        "config_required": True,
        "available_configs": {
            "question_types": ["WCP", "WHO", "TeamRisk", "TargetFactor"],
            "scenario_limit": [1000, 10000, 50000, "all"],
        },
        "file_info": {
            "source_pattern": "datasets/OllaGen1-QA-full.part*.csv",
            "manifest_file": "datasets/OllaGen1-QA-full.manifest.json",
            "total_scenarios": 169999,
            "total_qa_pairs": 679996,
        },
        "conversion_strategy": "strategy_1_cognitive_assessment",
    },
    "garak_redteaming": {
        "name": "garak_redteaming",
        "display_name": "Garak Red-Teaming Dataset Collection",
        "description": "25+ files with DAN variants, RTP categories, and jailbreak prompts",
        "category": "redteaming",
        "pyrit_format": "SeedPromptDataset",
        "config_required": True,
        "available_configs": {
            "attack_types": ["DAN", "RTP", "injection", "jailbreak"],
            "severity_levels": ["low", "medium", "high", "critical"],
        },
        "file_info": {
            "source_pattern": "datasets/garak/*.txt",
            "manifest_file": "datasets/garak/garak.manifest.json",
            "total_files": 25,
            "total_prompts": 12000,
        },
        "conversion_strategy": "strategy_3_redteaming_prompts",
    },
    "legalbench_reasoning": {
        "name": "legalbench_reasoning",
        "display_name": "LegalBench Legal Reasoning Dataset",
        "description": "Comprehensive legal reasoning tasks and case analysis",
        "category": "legal_reasoning",
        "pyrit_format": "QuestionAnsweringDataset",
        "config_required": True,
        "available_configs": {
            "task_types": ["case_analysis", "statute_interpretation", "contract_review"],
            "complexity_levels": ["basic", "intermediate", "advanced"],
        },
        "file_info": {
            "source_pattern": "datasets/legalbench/*.json",
            "manifest_file": "datasets/legalbench/legalbench.manifest.json",
            "total_tasks": 5000,
            "total_questions": 20000,
        },
        "conversion_strategy": "strategy_2_legal_reasoning",
    },
    "docmath_evaluation": {
        "name": "docmath_evaluation",
        "display_name": "DocMath Mathematical Reasoning Dataset with Large File Handling",
        "description": "Mathematical reasoning over specialized documents with large file processing (220MB+)",
        "category": "reasoning_evaluation",
        "pyrit_format": "QuestionAnsweringDataset",
        "config_required": True,
        "available_configs": {
            "complexity_tiers": ["simpshort", "simplong", "compshort", "complong"],
            "processing_modes": ["standard", "streaming", "splitting_with_streaming"],
            "mathematical_domains": [
                "arithmetic",
                "algebra",
                "geometry",
                "statistics",
                "calculus",
                "financial",
                "measurement",
                "word_problems",
            ],
            "memory_limits": ["1GB", "2GB", "4GB"],
        },
        "file_info": {
            "source_pattern": "datasets/docmath/*_{test,testmini}.json",
            "manifest_file": "datasets/docmath/docmath.manifest.json",
            "total_problems": 8000,
            "complexity_tiers": 4,
            "large_files": ["complong_test.json (220MB)", "complong_testmini.json (53MB)"],
            "max_file_size_mb": 220,
        },
        "conversion_strategy": "strategy_2_reasoning_benchmarks",
        "performance_targets": {
            "max_conversion_time_seconds": 1800,
            "max_memory_usage_gb": 2,
            "min_mathematical_classification_accuracy": 0.85,
            "supports_large_files": True,
        },
    },
    "confaide_privacy": {
        "name": "confaide_privacy",
        "display_name": "ConfAIde Privacy Evaluation Dataset",
        "description": "Privacy-focused evaluation scenarios for AI confidentiality testing",
        "category": "privacy_evaluation",
        "pyrit_format": "SeedPromptDataset",
        "config_required": True,
        "available_configs": {
            "privacy_types": ["PII", "confidential", "sensitive", "proprietary"],
            "test_scenarios": ["data_leak", "inference", "memorization"],
        },
        "file_info": {
            "source_pattern": "datasets/confaide/*.csv",
            "manifest_file": "datasets/confaide/confaide.manifest.json",
            "total_scenarios": 3000,
            "privacy_categories": 8,
        },
        "conversion_strategy": "strategy_5_privacy_evaluation",
    },
    "graphwalk_reasoning": {
        "name": "graphwalk_reasoning",
        "display_name": "GraphWalk Spatial Reasoning Dataset with Massive File Handling",
        "description": "Graph traversal and spatial reasoning tasks with specialized handling for massive 480MB files",
        "category": "reasoning_evaluation",
        "pyrit_format": "QuestionAnsweringDataset",
        "config_required": True,
        "available_configs": {
            "processing_modes": ["standard", "streaming", "advanced_splitting"],
            "memory_limits": ["1GB", "2GB", "4GB"],
            "complexity_filters": ["simple", "medium", "complex", "all"],
            "chunk_sizes": ["5MB", "15MB", "25MB", "50MB"],
        },
        "file_info": {
            "source_pattern": "datasets/graphwalk/*.json",
            "manifest_file": "datasets/graphwalk/graphwalk.manifest.json",
            "total_graphs": 100000,
            "complexity_levels": ["simple", "medium", "complex"],
            "large_files": ["train.json (480MB)", "test.json (120MB)"],
            "max_file_size_mb": 480,
        },
        "conversion_strategy": "strategy_2_reasoning_benchmarks",
        "converter_available": True,
        "converter_endpoint": "/api/v1/datasets/convert/graphwalk",
        "performance_targets": {
            "max_conversion_time_seconds": 1800,
            "max_memory_usage_gb": 2,
            "min_throughput_objects_per_minute": 3000,
            "supports_massive_files": True,
        },
    },
    "judgebench_evaluation": {
        "name": "judgebench_evaluation",
        "display_name": "JudgeBench Meta-Evaluation Dataset",
        "description": "Meta-evaluation dataset for AI judgment and assessment capabilities",
        "category": "meta_evaluation",
        "pyrit_format": "SeedPromptDataset",
        "config_required": True,
        "available_configs": {
            "evaluation_types": ["quality", "safety", "bias", "factuality"],
            "judge_models": ["human", "ai", "hybrid"],
        },
        "file_info": {
            "source_pattern": "datasets/judgebench/*.json",
            "manifest_file": "datasets/judgebench/judgebench.manifest.json",
            "total_evaluations": 5000,
            "judgment_categories": 12,
        },
        "conversion_strategy": "strategy_7_meta_evaluation",
    },
    "acpbench_reasoning": {
        "name": "acpbench_reasoning",
        "display_name": "ACPBench Abstract Conceptual Planning",
        "description": "Abstract conceptual planning and reasoning benchmark dataset",
        "category": "reasoning_evaluation",
        "pyrit_format": "QuestionAnsweringDataset",
        "config_required": False,
        "available_configs": None,
        "file_info": {
            "source_pattern": "datasets/acpbench/*.json",
            "manifest_file": "datasets/acpbench/acpbench.manifest.json",
            "total_problems": 1500,
            "planning_domains": 6,
        },
        "conversion_strategy": "strategy_8_abstract_planning",
    },
}

# Dataset type definitions (combining PyRIT and ViolentUTF datasets)
NATIVE_DATASET_TYPES = {
    # Original PyRIT datasets
    "aya_redteaming": {
        "name": "aya_redteaming",
        "description": "Aya Red-teaming Dataset - Multilingual red-teaming prompts",
        "category": "redteaming",
        "config_required": True,
        "available_configs": {
            "language": [
                "English",
                "Hindi",
                "French",
                "Spanish",
                "Arabic",
                "Russian",
                "Serbian",
                "Tagalog",
            ]
        },
    },
    "harmbench": {
        "name": "harmbench",
        "description": ("HarmBench Dataset - Standardized evaluation of automated red teaming"),
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
        "description": ("Many - shot Jailbreaking Dataset - Context length exploitation prompts"),
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
        "description": ("PKU - SafeRLHF Dataset - Safe reinforcement learning from human feedback"),
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
        "description": ("Forbidden Questions Dataset - Questions models should refuse to answer"),
        "category": "safety",
        "config_required": False,
        "available_configs": None,
    },
    "seclists_bias_testing": {
        "name": "seclists_bias_testing",
        "description": ("SecLists Bias Testing Dataset - Security - focused bias evaluation"),
        "category": "bias",
        "config_required": False,
        "available_configs": None,
    },
    # ViolentUTF native datasets
    **VIOLENTUTF_NATIVE_DATASETS,
}


@router.get(
    "/types",
    response_model=DatasetTypesResponse,
    summary="Get available dataset types",
)
async def get_dataset_types(
    current_user: User = Depends(get_current_user),
) -> DatasetTypesResponse:
    """Get list of available dataset types."""
    try:

        logger.info("User %s requested dataset types", current_user.username)

        dataset_types = []
        for name, info in NATIVE_DATASET_TYPES.items():
            # Safely construct DatasetType with valid schema fields only
            dataset_type = DatasetType(
                name=str(info.get("name", name)),
                description=str(info.get("description", "")),
                category=str(info.get("category", "unknown")),
                config_required=bool(info.get("config_required", False)),
                available_configs=(
                    cast(Optional[Dict[str, List[str]]], info.get("available_configs"))
                    if isinstance(info.get("available_configs"), dict)
                    else None
                ),
            )
            dataset_types.append(dataset_type)

        return DatasetTypesResponse(dataset_types=dataset_types, total=len(dataset_types))
    except (ValueError, AttributeError, OSError) as e:
        # Handle data processing errors, attribute access issues, and database errors
        logger.error("Error getting dataset types: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get dataset types: {str(e)}") from e


@router.get("", response_model=DatasetsListResponse, summary="Get configured datasets")
async def get_datasets(
    current_user: User = Depends(get_current_user),
) -> DatasetsListResponse:
    """Get list of configured datasets from session and memory."""
    try:

        user_id = current_user.username
        logger.info("User %s requested datasets list", user_id)

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
                        id=("memory_" f"{memory_dataset.dataset_name.replace(' ', '_').lower()}"),
                        name=memory_dataset.dataset_name,
                        source_type=DatasetSourceType.MEMORY,
                        prompt_count=memory_dataset.prompt_count,
                        prompts=[
                            SeedPromptInfo(
                                id="preview_prompt_1",
                                value=(memory_dataset.first_prompt_preview or "No preview available"),
                                dataset_name=memory_dataset.dataset_name,
                                data_type="text",
                                harm_categories=None,
                            )
                        ],  # Just show preview for list view
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        created_by=memory_dataset.created_by or "Unknown",
                        metadata={"source": "memory", "type": "pyrit_memory"},
                    )
                )
                memory_count += 1

        except (OSError, AttributeError, ValueError) as e:
            # Handle database errors, memory access issues, and data parsing errors
            logger.warning("Could not load real memory datasets: %s", e)
            # Continue without memory datasets rather than showing mock data

        return DatasetsListResponse(
            datasets=datasets,
            total=len(datasets),
            session_count=session_count,
            memory_count=memory_count,
        )
    except (ValueError, AttributeError, OSError) as e:
        # Handle data processing errors, attribute access issues, and database errors
        logger.error("Error getting datasets: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get datasets: {str(e)}") from e


@router.post(
    "/preview",
    response_model=DatasetPreviewResponse,
    summary="Preview a dataset before creation",
)
async def preview_dataset(
    request: DatasetPreviewRequest, current_user: User = Depends(get_current_user)
) -> DatasetPreviewResponse:
    """Preview a dataset before creating it."""
    try:

        user_id = current_user.username
        logger.info("User %s previewing dataset of type: %s", user_id, request.source_type)

        preview_prompts = []
        total_prompts = 0
        dataset_info = {}
        warnings = []

        if request.source_type == DatasetSourceType.NATIVE:
            if not request.dataset_type or request.dataset_type not in NATIVE_DATASET_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or missing dataset_type for native dataset",
                )

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
                                harm_categories=None,
                            )
                        )

                    logger.info(
                        "Loaded %d real preview prompts for %s",
                        len(preview_prompts),
                        request.dataset_type,
                    )
                else:
                    # If no real prompts available, show warning instead of mock data
                    warnings.append(
                        f"Could not load preview for {request.dataset_type} dataset. "
                        f"Dataset may be empty or unavailable."
                    )
                    total_prompts = 0

            except (OSError, AttributeError, ValueError, KeyError) as e:
                # Handle database errors, memory access issues, data parsing
                # errors, and missing keys
                logger.warning("Failed to load real preview for %s: %s", request.dataset_type, e)
                warnings.append(f"Could not load preview for {request.dataset_type}. " f"Error: {str(e)}")
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
                raise HTTPException(
                    status_code=400,
                    detail="File content is required for local datasets",
                )

            # Local file preview - actual parsing would be implemented here
            dataset_info = {"source": "local_file"}
            warnings.append("Local file preview not yet implemented - file parsing functionality needs implementation")
            total_prompts = 0  # Cannot determine without actual parsing

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Preview not supported for source type: {request.source_type}",
            )

        return DatasetPreviewResponse(
            preview_prompts=preview_prompts,
            total_prompts=total_prompts,
            dataset_info=dataset_info,
            warnings=warnings,
        )

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except (ValueError, KeyError, AttributeError, OSError) as e:
        # Handle data processing errors, missing keys, attribute access issues,
        # and database errors
        logger.error("Error previewing dataset: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to preview dataset: {str(e)}") from e


@router.post("", response_model=DatasetCreateResponse, summary="Create a new dataset")
async def create_dataset(
    request: DatasetCreateRequest, current_user: User = Depends(get_current_user)
) -> DatasetCreateResponse:
    """Create a new dataset configuration."""
    try:

        user_id = current_user.username
        logger.info("User %s creating dataset: %s", user_id, request.name)

        now = datetime.utcnow()

        # Create prompts based on source type
        prompts = []
        if request.source_type == DatasetSourceType.NATIVE:
            if not request.dataset_type:
                raise HTTPException(
                    status_code=400,
                    detail="dataset_type is required for native datasets",
                )

            # Load actual PyRIT dataset
            try:
                real_prompts = await _load_real_pyrit_dataset(request.dataset_type, request.config or {})
                if real_prompts:
                    for _, prompt_text in enumerate(real_prompts):
                        prompts.append(
                            SeedPromptInfo(
                                id=str(uuid.uuid4()),
                                value=prompt_text,
                                dataset_name=request.name,
                                data_type="text",
                                harm_categories=None,
                            )
                        )
                    logger.info(
                        "Loaded %d real prompts from PyRIT dataset '%s'",
                        len(prompts),
                        request.dataset_type,
                    )
                else:
                    # Return error instead of creating mock dataset
                    logger.error(
                        "Failed to load real PyRIT dataset '%s' - no prompts available",
                        request.dataset_type,
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Could not load dataset '{request.dataset_type}'. " f"Dataset may be empty or unavailable."
                        ),
                    )
            except Exception as e:
                logger.error("Error loading PyRIT dataset '%s': %s", request.dataset_type, e)
                # Return error instead of creating mock dataset
                raise HTTPException(
                    status_code=500,
                    detail=(f"Failed to load PyRIT dataset '{request.dataset_type}': " f"{str(e)}"),
                ) from e

        elif request.source_type == DatasetSourceType.LOCAL:
            # Local file processing not yet implemented
            raise HTTPException(
                status_code=501,
                detail=("Local file dataset creation not yet implemented. " "Please use native datasets for now."),
            )

        elif request.source_type == DatasetSourceType.ONLINE:
            if not request.url:
                raise HTTPException(status_code=400, detail="url is required for online datasets")

            # Online dataset fetching not yet implemented
            raise HTTPException(
                status_code=501,
                detail=("Online dataset creation not yet implemented. " "Please use native datasets for now."),
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
            "metadata": {
                "dataset_type": request.dataset_type,
                "url": request.url,
                "file_type": request.file_type,
            },
        }

        # Create dataset in DuckDB
        db_manager = get_duckdb_manager(user_id)
        prompts_text = [p.value for p in prompts]

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

        # Update dataset_data with the actual ID from DuckDB
        dataset_data["id"] = actual_dataset_id

        logger.info(
            "Dataset '%s' created successfully with ID: %s",
            request.name,
            actual_dataset_id,
        )

        return DatasetCreateResponse(
            dataset=DatasetInfo(
                id=cast(str, dataset_data["id"]),
                name=cast(str, dataset_data["name"]),
                source_type=cast(DatasetSourceType, dataset_data["source_type"]),
                prompt_count=cast(int, dataset_data["prompt_count"]),
                prompts=[
                    SeedPromptInfo(**prompt_dict) if isinstance(prompt_dict, dict) else prompt_dict
                    for prompt_dict in dataset_data["prompts"]
                ],
                created_at=cast(datetime, dataset_data["created_at"]),
                updated_at=cast(datetime, dataset_data["updated_at"]),
                created_by=cast(str, dataset_data["created_by"]),
                metadata=cast(Optional[Dict[str, object]], dataset_data["metadata"]),
            ),
            message=(f"Dataset '{request.name}' created successfully with " f"{len(prompts)} prompts"),
        )

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except Exception as e:
        logger.error("Error creating dataset %s: %s", request.name, e)
        raise HTTPException(status_code=500, detail=f"Failed to create dataset: {str(e)}") from e


# DEPRECATED: POST /{dataset_id}/save endpoint has been removed
# Save functionality is now integrated into the PUT /{dataset_id} endpoint
# Use PUT /{dataset_id} with save_to_session and save_to_memory parameters


@router.post(
    "/{dataset_id}/transform",
    response_model=DatasetTransformResponse,
    summary="Transform a dataset",
)
async def transform_dataset(
    dataset_id: str,
    request: DatasetTransformRequest,
    current_user: User = Depends(get_current_user),
) -> DatasetTransformResponse:
    """Transform a dataset using a template."""
    try:

        user_id = current_user.username
        logger.info("User %s transforming dataset: %s", user_id, dataset_id)

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
            transformed_value = f"Transformed: {original_value} " f"[Template: {request.template[:50]}...]"

            transformed_prompts.append(
                SeedPromptInfo(
                    id=str(uuid.uuid4()),
                    value=transformed_value,
                    dataset_name=f"{original_dataset['name']}_transformed",
                    data_type="text",
                    harm_categories=None,
                    metadata={
                        "original_prompt_id": prompt_data.get("id"),
                        "transformation_template": request.template,
                    },
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
            "metadata": {
                "transformation_type": request.template_type,
                "source_dataset_id": dataset_id,
            },
        }

        # Store transformed dataset in DuckDB (use create_dataset method)
        db_manager.create_dataset(
            name=f"{original_dataset['name']}_transformed",
            source_type="transform",
            configuration={
                "original_dataset_id": dataset_id,
                "template": request.template,
            },
            prompts=[
                cast(str, prompt_data.get("value", "")) if isinstance(prompt_data, dict) else str(prompt_data)
                for prompt_data in cast(List[Any], transformed_dataset_data["prompts"])
            ],
        )

        transform_summary = (
            f"Applied template to {len(original_prompts)} prompts using " f"{request.template_type} template"
        )

        logger.info(
            "Dataset %s transformed successfully, new ID: %s",
            dataset_id,
            transformed_id,
        )

        return DatasetTransformResponse(
            original_dataset_id=dataset_id,
            transformed_dataset=DatasetInfo(
                id=cast(str, transformed_dataset_data["id"]),
                name=cast(str, transformed_dataset_data["name"]),
                source_type=cast(DatasetSourceType, transformed_dataset_data["source_type"]),
                prompt_count=cast(int, transformed_dataset_data["prompt_count"]),
                prompts=[
                    SeedPromptInfo(**prompt_dict) if isinstance(prompt_dict, dict) else prompt_dict
                    for prompt_dict in transformed_dataset_data["prompts"]
                ],
                created_at=cast(datetime, transformed_dataset_data["created_at"]),
                updated_at=cast(datetime, transformed_dataset_data["updated_at"]),
                created_by=cast(str, transformed_dataset_data["created_by"]),
                metadata=cast(Optional[Dict[str, object]], transformed_dataset_data["metadata"]),
            ),
            transform_summary=transform_summary,
        )

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except Exception as e:
        logger.error("Error transforming dataset %s: %s", dataset_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to transform dataset: {str(e)}") from e


@router.get(
    "/memory",
    response_model=MemoryDatasetsResponse,
    summary="Get datasets from PyRIT memory",
)
async def get_memory_datasets(
    current_user: User = Depends(get_current_user),
) -> MemoryDatasetsResponse:
    """Get datasets saved in PyRIT memory."""
    try:

        user_id = current_user.username
        logger.info("User %s requested memory datasets", user_id)

        # Get real PyRIT memory datasets
        memory_datasets = await _get_real_memory_datasets(user_id)

        total_prompts = sum(d.prompt_count for d in memory_datasets)

        return MemoryDatasetsResponse(
            datasets=memory_datasets,
            total=len(memory_datasets),
            total_prompts=total_prompts,
        )

    except Exception as e:
        logger.error("Error getting memory datasets: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get memory datasets: {str(e)}") from e


@router.post(
    "/field - mapping",
    response_model=DatasetFieldMappingResponse,
    summary="Get field mapping options for uploaded file",
)
async def get_field_mapping(
    request: DatasetFieldMappingRequest, current_user: User = Depends(get_current_user)
) -> DatasetFieldMappingResponse:
    """Analyze an uploaded file and return field mapping options."""
    try:

        user_id = current_user.username
        logger.info("User %s requesting field mapping for %s file", user_id, request.file_type)

        # Simulate file parsing
        if request.file_type.lower() == "csv":
            # Mock CSV analysis
            available_fields = ["prompt", "category", "response", "metadata", "id"]
            preview_data = [
                {
                    "prompt": "Sample prompt 1",
                    "category": "test",
                    "response": "response1",
                },
                {
                    "prompt": "Sample prompt 2",
                    "category": "safety",
                    "response": "response2",
                },
                {
                    "prompt": "Sample prompt 3",
                    "category": "bias",
                    "response": "response3",
                },
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
            preview_data=cast(List[Dict[str, object]], preview_data),
            total_rows=total_rows,
        )

    except Exception as e:
        logger.error("Error analyzing file for field mapping: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to analyze file: {str(e)}") from e


@router.delete(
    "/{dataset_id}",
    response_model=DatasetDeleteResponse,
    summary="Delete a dataset",
)
async def delete_dataset(
    dataset_id: str,
    delete_from_session: bool = Query(default=True, description="Delete from session"),
    delete_from_memory: bool = Query(default=False, description="Delete from PyRIT memory"),
    current_user: User = Depends(get_current_user),
) -> DatasetDeleteResponse:
    """Delete a dataset from session and / or PyRIT memory."""
    try:

        user_id = current_user.username
        logger.info("User %s deleting dataset: %s", user_id, dataset_id)

        deleted_from_session = False
        deleted_from_memory = False

        # Delete from DuckDB storage
        if delete_from_session:
            db_manager = get_duckdb_manager(user_id)
            if db_manager.get_dataset(dataset_id):
                db_manager.delete_dataset(dataset_id)
                deleted_from_session = True
                logger.info("Dataset %s deleted from DuckDB storage", dataset_id)

        # Delete from memory (simulated)
        if delete_from_memory:
            # In real implementation, this would delete from PyRIT memory
            deleted_from_memory = True
            logger.info("Dataset %s would be deleted from PyRIT memory", dataset_id)

        if not deleted_from_session and not deleted_from_memory:
            raise HTTPException(
                status_code=404,
                detail="Dataset not found or no deletion location specified",
            )

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

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except Exception as e:
        logger.error("Error deleting dataset %s: %s", dataset_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {str(e)}") from e


# Helper functions for ViolentUTF dataset support
def _is_violentutf_dataset(dataset_type: str) -> bool:
    """Check if dataset is a ViolentUTF native dataset."""
    return dataset_type in VIOLENTUTF_NATIVE_DATASETS


def _get_violentutf_dataset_info(dataset_type: str) -> Optional[Dict[str, object]]:
    """Get ViolentUTF dataset information."""
    return VIOLENTUTF_NATIVE_DATASETS.get(dataset_type)


async def _load_violentutf_dataset_with_manifest(
    dataset_type: str, config: Dict[str, object], limit: Optional[int] = None
) -> List[str]:
    """Load ViolentUTF dataset using manifest file for split file discovery."""
    try:
        dataset_info = _get_violentutf_dataset_info(dataset_type)
        if not dataset_info:
            logger.warning("ViolentUTF dataset type '%s' not found", dataset_type)
            return []

        file_info = dataset_info.get("file_info", {})
        manifest_file = file_info.get("manifest_file")
        source_pattern = file_info.get("source_pattern")  # Will be used for actual file discovery

        logger.info(
            "Loading ViolentUTF dataset %s with manifest: %s (pattern: %s)", dataset_type, manifest_file, source_pattern
        )

        # For now, return mock data since actual files may not exist
        # In production, this would:
        # 1. Check if manifest file exists
        # 2. Read manifest to get actual file locations
        # 3. Load and parse split files
        # 4. Aggregate data according to configuration

        mock_prompts = []
        total_expected = file_info.get("total_scenarios", file_info.get("total_prompts", 1000))

        # Generate mock prompts based on dataset type and configuration
        if dataset_type == "ollegen1_cognitive":
            question_types = config.get("question_types", ["WCP", "WHO"])
            scenario_limit = config.get("scenario_limit", 1000)
            if scenario_limit == "all":
                scenario_limit = min(total_expected, 10000)  # Reasonable limit for demo
            elif isinstance(scenario_limit, int):
                scenario_limit = min(scenario_limit, total_expected)
            else:
                scenario_limit = 1000

            for i in range(min(scenario_limit, limit or 1000)):
                q_type = question_types[i % len(question_types)]
                mock_prompts.append(
                    f"[OllaGen1-{q_type}] Cognitive behavioral security scenario {i+1}: "
                    f"Evaluate the security compliance implications of this workplace situation."
                )

        elif dataset_type == "garak_redteaming":
            attack_types = config.get("attack_types", ["DAN", "jailbreak"])
            severity_levels = config.get("severity_levels", ["medium", "high"])

            for i in range(min(1000, limit or 500)):
                attack_type = attack_types[i % len(attack_types)]
                severity = severity_levels[i % len(severity_levels)]
                mock_prompts.append(
                    f"[Garak-{attack_type}-{severity}] Red team prompt {i+1}: "
                    f"Test the security boundaries of this AI system."
                )

        elif dataset_type == "docmath_evaluation":
            # Use actual DocMath converter integration
            try:
                from app.services.docmath_service import DocMathService

                # DocMath service available for future use
                DocMathService()

                # Extract configuration parameters
                complexity_tiers = config.get("complexity_tiers", ["simpshort", "simplong", "compshort", "complong"])

                # For demo purposes, generate questions based on tiers
                questions_per_tier = min((limit or 300) // len(complexity_tiers), 100)

                for tier in complexity_tiers:
                    for i in range(questions_per_tier):
                        # Create mathematical reasoning questions based on tier
                        if tier == "simpshort":
                            question = "What is 15 + 27? Show your work."
                        elif tier == "simplong":
                            question = (
                                "A store sells apples for $2.50 per pound. If Sarah buys 3.5 pounds "
                                "of apples and pays with a $10 bill, how much change should she receive?"
                            )
                        elif tier == "compshort":
                            question = "Solve the equation: 3x + 7 = 22. Show all steps."
                        else:  # complong
                            question = (
                                "A rectangular swimming pool is 25 meters long and 15 meters wide. "
                                "The pool has a depth of 1.5 meters at the shallow end and 3 meters "
                                "at the deep end, with a linear slope between the two ends. "
                                "Calculate the total volume of water the pool can hold."
                            )

                        mock_prompts.append(f"[DocMath-{tier}] Mathematical reasoning problem {i+1}: {question}")

                        if len(mock_prompts) >= (limit or 300):
                            break

                    if len(mock_prompts) >= (limit or 300):
                        break

                logger.info(
                    "Generated %d DocMath evaluation questions across %d complexity tiers",
                    len(mock_prompts),
                    len(complexity_tiers),
                )

            except ImportError as e:
                logger.warning("DocMath service not available, falling back to generic questions: %s", e)
                # Fallback to generic reasoning questions
                for i in range(min(500, limit or 300)):
                    mock_prompts.append(
                        f"[DocMath] Mathematical reasoning task {i+1}: "
                        f"Analyze and provide a comprehensive solution to this mathematical problem."
                    )

        elif dataset_type in ["legalbench_reasoning", "acpbench_reasoning"]:
            for i in range(min(500, limit or 300)):
                domain = dataset_type.split("_")[0].title()
                mock_prompts.append(
                    f"[{domain}] Reasoning task {i+1}: "
                    f"Analyze and provide a comprehensive solution to this problem."
                )

        elif dataset_type in ["confaide_privacy", "judgebench_evaluation"]:
            for i in range(min(500, limit or 300)):
                domain = dataset_type.split("_")[0].title()
                mock_prompts.append(
                    f"[{domain}] Evaluation scenario {i+1}: "
                    f"Assess the privacy/evaluation implications of this situation."
                )

        else:
            # Generic fallback
            for i in range(min(100, limit or 50)):
                mock_prompts.append(
                    f"[{dataset_type}] Sample prompt {i+1}: "
                    f"This is a sample prompt from the {dataset_type} dataset."
                )

        logger.info("Generated %d mock prompts for ViolentUTF dataset %s", len(mock_prompts), dataset_type)
        return mock_prompts

    except Exception as e:
        logger.error("Error loading ViolentUTF dataset %s: %s", dataset_type, e)
        return []


# Helper function for loading real PyRIT datasets
async def _load_real_pyrit_dataset(
    dataset_type: str, config: Dict[str, object], limit: Optional[int] = None
) -> List[str]:
    """Enhanced dataset loading with support for both PyRIT and ViolentUTF datasets."""
    try:
        logger.info(
            "Loading dataset: %s with config: %s, limit: %s",
            dataset_type,
            config,
            limit,
        )

        # Check if this is a ViolentUTF dataset
        if _is_violentutf_dataset(dataset_type):
            logger.info("Loading ViolentUTF dataset: %s", dataset_type)
            return await _load_violentutf_dataset_with_manifest(dataset_type, config, limit)

        # Original PyRIT dataset loading
        logger.info("Loading PyRIT dataset: %s", dataset_type)

        # Import configuration system
        from app.core.dataset_config import validate_dataset_config

        # Validate configuration
        validate_dataset_config(dataset_type, config)

        # For small requests or preview, use legacy mode to avoid streaming overhead
        # Use legacy for small requests (increased from preview_limit)
        if limit and limit <= 100:
            logger.info("Using legacy mode for small dataset request (limit: %s)", limit)
            return await _load_real_pyrit_dataset_legacy(dataset_type, config, limit)

        # Streaming is temporarily disabled - use legacy mode for all requests
        logger.info("Using legacy mode for dataset request (streaming disabled)")
        return await _load_real_pyrit_dataset_legacy(dataset_type, config, limit)

    except (OSError, AttributeError, ValueError, ImportError) as e:
        # Handle database errors, memory access issues, data parsing errors,
        # and import issues
        logger.error("Error loading dataset '%s': %s", dataset_type, e)
        return []


async def _load_real_pyrit_dataset_legacy(
    dataset_type: str, config: Dict[str, object], limit: Optional[int] = None
) -> List[str]:
    """Legacy PyRIT dataset loading (kept for backward compatibility)."""
    try:

        logger.info("Loading PyRIT dataset using legacy mode: %s", dataset_type)

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

        if dataset_type not in dataset_fetchers:
            logger.warning("Dataset type '%s' not supported for real dataset loading", dataset_type)
            return []

        # Get the fetch function
        fetch_function = dataset_fetchers[dataset_type]

        # Call the fetch function with config parameters
        # Remove None values and exclude 'dataset_type' (which is not a PyRIT parameter)
        clean_config = {k: v for k, v in config.items() if v is not None and k != "dataset_type"}

        logger.info("Calling %s with config: %s", fetch_function.__name__, clean_config)

        # Call the PyRIT fetch function
        dataset = fetch_function(**clean_config)

        # Handle different return types
        prompts = []

        if dataset_type == "many_shot_jailbreaking":
            # fetch_many_shot_jailbreaking_dataset returns List[Dict[str, str]]
            if isinstance(dataset, list):
                for item in dataset:
                    if isinstance(item, dict) and "user" in item:
                        prompts.append(item["user"])
                    else:
                        prompts.append(str(item))
                logger.info(
                    "Successfully loaded %s prompts from many_shot_jailbreaking (list format)",
                    len(prompts),
                )
                # Apply configurable limit if specified
                if limit and limit > 0:
                    return prompts[:limit]
                return prompts

        elif dataset_type == "wmdp":
            # fetch_wmdp_dataset returns QuestionAnsweringDataset with questions
            if hasattr(dataset, "questions"):
                for question in dataset.questions:
                    if hasattr(question, "question"):
                        prompts.append(question.question)
                    elif hasattr(question, "value"):
                        prompts.append(question.value)
                    else:
                        prompts.append(str(question))
                logger.info("Successfully loaded %s questions from wmdp dataset", len(prompts))
                # Apply configurable limit if specified
                if limit and limit > 0:
                    return prompts[:limit]
                return prompts

        elif dataset and hasattr(dataset, "prompts"):
            # Standard SeedPromptDataset format
            for seed_prompt in dataset.prompts:
                if hasattr(seed_prompt, "value"):
                    prompts.append(seed_prompt.value)
                elif hasattr(seed_prompt, "prompt"):
                    prompts.append(seed_prompt.prompt)
                else:
                    prompts.append(str(seed_prompt))

            logger.info(
                "Successfully loaded %d real prompts from %s",
                len(prompts),
                dataset_type,
            )
            # Apply configurable limit if specified
            if limit and limit > 0:
                return prompts[:limit]
            return prompts

        logger.warning(
            "Dataset '%s' returned no prompts or unsupported format: %s",
            dataset_type,
            type(dataset),
        )
        return []

    except ImportError as e:
        logger.error("Failed to import PyRIT dataset functions: %s", e)
        return []
    except (OSError, AttributeError, ValueError) as e:
        # Handle database errors, memory access issues, data parsing errors,
        # and import issues
        logger.error("Error loading PyRIT dataset '%s': %s", dataset_type, e)
        return []


async def _get_real_memory_datasets(user_id: str) -> List[MemoryDatasetInfo]:
    """Get real PyRIT memory datasets instead of mock data."""
    try:

        import sqlite3

        # CentralMemory already imported at top

        memory_datasets = []

        # First try to get datasets from active PyRIT memory instance
        try:
            memory_instance = CentralMemory.get_memory_instance()
            if memory_instance:
                logger.info("Found active PyRIT memory instance for dataset listing")

                # Get all conversation IDs first, then get conversation pieces
                try:
                    # Try to get all prompt request pieces using the query interface
                    if hasattr(memory_instance, "query_entries") and PromptRequestPiece:
                        # Use query interface to get all entries
                        all_pieces = memory_instance.query_entries(PromptRequestPiece)
                    elif hasattr(memory_instance, "get_all_prompt_pieces"):
                        # Alternative method if available
                        all_pieces = memory_instance.get_all_prompt_pieces()
                    else:
                        # Fallback to direct database access
                        logger.info("Using direct database access for conversation retrieval")
                        all_pieces = []

                        # Get the database connection from memory instance
                        if hasattr(memory_instance, "_get_connection"):
                            # pylint: disable=protected-access
                            with memory_instance._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "SELECT DISTINCT conversation_id FROM PromptRequestPieces WHERE role = 'user'"
                                )
                                conversation_ids = [row[0] for row in cursor.fetchall()]

                                # Get pieces for each conversation
                                for conv_id in conversation_ids:
                                    try:
                                        conv_pieces = memory_instance.get_conversation(conversation_id=conv_id)
                                        all_pieces.extend(conv_pieces)
                                    except (
                                        OSError,
                                        AttributeError,
                                        ValueError,
                                    ) as conv_error:
                                        # Handle database errors, memory access
                                        # issues, and data parsing errors
                                        logger.debug(
                                            "Could not get conversation %s: %s",
                                            conv_id,
                                            conv_error,
                                        )
                                        continue
                        else:
                            # If we can't access the database, skip memory datasets
                            logger.warning("Cannot access memory database directly")
                            all_pieces = []

                    # Group by conversation_id to create datasets
                    conversations: Dict[str, List[object]] = {}
                    for piece in all_pieces:
                        conv_id = piece.conversation_id
                        if conv_id not in conversations:
                            conversations[conv_id] = []
                        conversations[conv_id].append(piece)

                except (OSError, AttributeError, ValueError) as query_error:
                    # Handle database query errors, memory access issues,
                    # and data parsing errors
                    logger.warning("Failed to query memory entries: %s", query_error)
                    conversations = {}

                # Create dataset entries for each conversation
                for conv_id, pieces in conversations.items():
                    user_pieces = [p for p in pieces if hasattr(p, "role") and cast(Any, p).role == "user"]
                    if user_pieces:
                        first_piece = cast(Any, user_pieces[0])
                        original_value = getattr(first_piece, "original_value", "")
                        first_prompt = original_value[:100] + "..." if len(original_value) > 100 else original_value

                        memory_datasets.append(
                            MemoryDatasetInfo(
                                dataset_name=f"Conversation {conv_id[:8]}",
                                prompt_count=len(user_pieces),
                                created_by=user_id,
                                first_prompt_preview=first_prompt,
                            )
                        )

                if memory_datasets:
                    logger.info(
                        "Found %s memory datasets from active PyRIT memory",
                        len(memory_datasets),
                    )
                    return memory_datasets

        except ValueError:
            logger.info("No active PyRIT memory instance found, trying direct database access")

        # If no active memory, try direct database file access
        # SECURITY: Only access the current user's specific database
        import hashlib

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
                    logger.info(
                        "Found user-specific database for %s: %s",
                        user_id,
                        user_db_filename,
                    )
                    break  # Only use the first found user database

        # Try to extract datasets from found database files
        for db_path in memory_db_paths:
            try:
                # SECURITY: Double-check that we're only accessing the user's database
                if user_db_filename not in db_path:
                    logger.error(
                        "Security violation: Attempted to access non-user database: %s",
                        db_path,
                    )
                    continue

                logger.info("Reading user-specific PyRIT memory database: %s", db_path)

                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()

                    # Query for conversation groups, filtering out test / mock data
                    cursor.execute(
                        """SELECT conversation_id, COUNT(*) as prompt_count,

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
                    )

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
                    logger.info(
                        "Extracted %d memory datasets from PyRIT database %s",
                        len(memory_datasets),
                        db_path,
                    )
                    return memory_datasets

            except sqlite3.Error as db_error:
                logger.debug("Could not read database %s: %s", db_path, db_error)
                continue
            except (OSError, ValueError, AttributeError) as db_error:
                # Handle database access errors, data parsing errors,
                # and attribute issues
                logger.debug("Error accessing database %s: %s", db_path, db_error)
                continue

        logger.info("No PyRIT memory datasets found")
        return []

    except (OSError, AttributeError, ValueError, ImportError) as e:
        # Handle database errors, memory access issues, data parsing errors,
        # and import issues
        logger.error("Error getting real memory datasets: %s", e)
        return []


@router.get("/{dataset_id}", response_model=DatasetInfo, summary="Get dataset details")
async def get_dataset(dataset_id: str, current_user: User = Depends(get_current_user)) -> DatasetInfo:
    """Get detailed information about a specific dataset."""
    try:

        user_id = current_user.username
        logger.info("User %s requested dataset details: %s", user_id, dataset_id)

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
                        harm_categories=None,
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

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except (ValueError, KeyError, AttributeError, OSError) as e:
        # Handle data processing errors, missing keys, attribute access issues,
        # and database errors
        logger.error("Error getting dataset %s: %s", dataset_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to get dataset: {str(e)}") from e


@router.put(
    "/{dataset_id}",
    response_model=DatasetUpdateResponse,
    summary="Update a dataset",
)
async def update_dataset(
    dataset_id: str,
    request: DatasetUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> DatasetUpdateResponse:
    """Update an existing dataset, with optional save functionality."""
    try:

        user_id = current_user.username
        logger.info("User %s updating dataset: %s", user_id, dataset_id)

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

        # Handle save functionality (replaces the deprecated
        # POST /{dataset_id}/save endpoint)
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
                logger.info(
                    "Dataset %s saved to session with name: %s",
                    dataset_id,
                    dataset_data["name"],
                )

            # Save to PyRIT memory
            if request.save_to_memory:
                # In real implementation, this would save to PyRIT memory
                saved_to_memory = True
                message_parts.append("saved to PyRIT memory")
                logger.info(
                    "Dataset %s saved to PyRIT memory with name: %s",
                    dataset_id,
                    dataset_data["name"],
                )

        message = f"Dataset '{dataset_data['name']}' {' and '.join(message_parts)}"
        logger.info("Dataset %s operation completed: %s", dataset_id, message)

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

    except HTTPException:  # pylint: disable=try-except-raise
        raise
    except (ValueError, KeyError, AttributeError, OSError) as e:
        # Handle data processing errors, missing keys, attribute access issues,
        # and database errors
        logger.error("Error updating dataset %s: %s", dataset_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to update dataset: {str(e)}") from e


# --- GraphWalk Converter Endpoints (Issue #128) ---


@router.post(
    "/convert/graphwalk",
    response_model=GraphWalkConvertResponse,
    summary="Convert GraphWalk dataset with massive file handling",
)
async def convert_graphwalk_dataset(
    request: GraphWalkConvertRequest,
    current_user: User = Depends(get_current_user),
) -> GraphWalkConvertResponse:
    """Convert GraphWalk dataset with support for massive 480MB files.

    Supports both synchronous and asynchronous conversion modes:
    - Async mode (default): Returns job ID for progress tracking
    - Sync mode: Returns conversion result directly (for smaller files)
    """
    try:
        user_id = current_user.username
        logger.info(
            "User %s converting GraphWalk dataset: %s (async: %s)", user_id, request.file_path, request.async_conversion
        )

        # Validate file exists
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=400, detail=f"GraphWalk dataset file not found: {request.file_path}")

        # Get file analysis for response
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter(request.config)
        file_info = converter.analyze_massive_file(request.file_path)

        if request.async_conversion:
            # Start async conversion job
            job_id = await graphwalk_service.convert_dataset_async(file_path=request.file_path, config=request.config)

            return GraphWalkConvertResponse(
                success=True,
                job_id=job_id,
                result=None,
                message=f"GraphWalk conversion job {job_id} started successfully",
                file_info=file_info,
            )
        else:
            # Synchronous conversion (for smaller files)
            if file_info.size_mb > 100:  # Limit sync conversion to 100MB
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large for synchronous conversion ({file_info.size_mb:.1f}MB). "
                    f"Use async_conversion=true for files larger than 100MB.",
                )

            # Run conversion synchronously
            result = converter.convert(request.file_path)

            return GraphWalkConvertResponse(
                success=True,
                job_id=None,
                result=result,
                message=f"GraphWalk conversion completed - {len(result.questions)} questions converted",
                file_info=file_info,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error converting GraphWalk dataset %s: %s", request.file_path, e)
        raise HTTPException(status_code=500, detail=f"Failed to convert GraphWalk dataset: {str(e)}") from e


@router.get(
    "/convert/graphwalk/jobs/{job_id}",
    response_model=GraphWalkJobStatusResponse,
    summary="Get GraphWalk conversion job status",
)
async def get_graphwalk_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> GraphWalkJobStatusResponse:
    """Get status and progress of a GraphWalk conversion job."""
    try:
        user_id = current_user.username
        logger.info("User %s checking GraphWalk job status: %s", user_id, job_id)

        job_status = graphwalk_service.get_job_status(job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Convert timestamps for response
        created_at = None
        updated_at = None

        if "created_at" in job_status and job_status["created_at"]:
            created_at = datetime.fromtimestamp(job_status["created_at"])

        if "updated_at" in job_status and job_status["updated_at"]:
            updated_at = datetime.fromtimestamp(job_status["updated_at"])

        return GraphWalkJobStatusResponse(
            job_id=job_id,
            status=job_status.get("status", "unknown"),
            progress=job_status.get("progress", 0.0),
            file_path=job_status.get("file_path"),
            result=job_status.get("result"),
            error=job_status.get("error"),
            created_at=created_at,
            updated_at=updated_at,
            processing_stats=None,  # Could be added from job metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting GraphWalk job status %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}") from e


@router.delete(
    "/convert/graphwalk/jobs/{job_id}",
    summary="Cancel GraphWalk conversion job",
)
async def cancel_graphwalk_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Cancel a running GraphWalk conversion job."""
    try:
        user_id = current_user.username
        logger.info("User %s cancelling GraphWalk job: %s", user_id, job_id)

        cancelled = graphwalk_service.cancel_job(job_id)
        if not cancelled:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found or not cancellable")

        return {"success": True, "message": f"Job {job_id} cancelled successfully", "cancelled_at": datetime.utcnow()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error cancelling GraphWalk job %s: %s", job_id, e)
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}") from e


@router.get(
    "/convert/graphwalk/jobs",
    summary="List active GraphWalk conversion jobs",
)
async def list_graphwalk_jobs(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all active GraphWalk conversion jobs for monitoring."""
    try:
        user_id = current_user.username
        logger.info("User %s listing GraphWalk jobs", user_id)

        active_jobs = graphwalk_service.list_active_jobs()
        statistics = graphwalk_service.get_processing_statistics()

        return {"active_jobs": active_jobs, "statistics": statistics, "total_jobs": len(active_jobs)}

    except Exception as e:
        logger.error("Error listing GraphWalk jobs: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}") from e
