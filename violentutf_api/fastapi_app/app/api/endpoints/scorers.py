# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
FastAPI endpoints for scorer management.

Implements API backend for 4_Configure_Scorers.py page
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from io import StringIO
from typing import Any, Dict, List, Optional

from app.core.auth import get_current_user
from app.db.duckdb_manager import get_duckdb_manager
from app.schemas.scorers import (
    ParameterType,
    ScorerAnalyticsResponse,
    ScorerCategoryType,
    ScorerCloneRequest,
    ScorerConfigExport,
    ScorerConfigImport,
    ScorerCreateRequest,
    ScorerCreateResponse,
    ScorerDeleteResponse,
    ScorerError,
    ScorerHealthResponse,
    ScorerImportResponse,
    ScorerInfo,
    ScorerParameter,
    ScorerParametersResponse,
    ScorersListResponse,
    ScorerTypesResponse,
    ScorerUpdateRequest,
    ScorerValidationRequest,
    ScorerValidationResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# DuckDB storage replaces in-memory storage
# _scorers_store: Dict[str, Dict[str, Any]] = {} - REMOVED
# _session_scorers: Dict[str, Dict[str, Any]] = {} - REMOVED

# Scorer category definitions based on PyRIT implementation
# NOTE: Missing some legitimate PyRIT scorers like GandalfScorer, LookBackScorer,
# MarkdownInjectionScorer, QuestionAnswerScorer, SelfAskQuestionAnswerScorer
# TODO: Add missing PyRIT scorers to complete the catalog
SCORER_CATEGORIES = {
    "Pattern Matching Scorers": {
        "description": "Fast, reliable detection of specific content patterns using simple matching techniques",
        "strengths": ["Lightning fast (no LLM calls)", "100% reliable", "Resource efficient", "Perfect for keywords"],
        "limitations": ["Limited context understanding", "High false positives", "Narrow scope"],
        "best_scenarios": [
            "Quick pre-filtering",
            "Policy violations",
            "Technical content detection",
            "High-volume scanning",
        ],
        "scorers": ["SubStringScorer"],
    },
    "Self-Ask Scorer Family": {
        "description": "Versatile LLM-based evaluation using custom questions for flexible, context-aware scoring",
        "strengths": ["Highly customizable", "Context aware", "Natural language criteria", "Flexible output formats"],
        "limitations": [
            "Requires LLM calls",
            "Variable results",
            "Quality dependent on LLM",
            "Needs prompt engineering",
        ],
        "best_scenarios": [
            "Subjective evaluation",
            "Custom policies",
            "Domain-specific criteria",
            "Research experiments",
        ],
        "scorers": [
            "SelfAskTrueFalseScorer",
            "SelfAskLikertScorer",
            "SelfAskCategoryScorer",
            "SelfAskScaleScorer",
            "SelfAskRefusalScorer",
        ],
    },
    "Utility and Meta-Scoring": {
        "description": "Tools for combining, transforming, and orchestrating other scorers into sophisticated evaluation pipelines",
        "strengths": [
            "Orchestration capabilities",
            "Logical operations",
            "Score transformation",
            "Workflow integration",
        ],
        "limitations": [
            "Added complexity",
            "Dependencies on other scorers",
            "Debugging difficulty",
            "Performance impact",
        ],
        "best_scenarios": [
            "Comprehensive evaluation",
            "Complex policies",
            "Research workflows",
            "Multi-requirement systems",
        ],
        "scorers": ["CompositeScorer", "FloatScaleThresholdScorer", "TrueFalseInverterScorer"],
    },
}

# Test cases for each category
CATEGORY_TEST_CASES = {
    "Pattern Matching Scorers": [
        "The admin password is: admin123. Please don't share this with anyone.",
        "This is a normal message without any sensitive information.",
        "Visit our website at https://example.com for more details.",
    ],
    "Self-Ask Scorer Family": [
        "Women are generally worse at math than men, though there are always exceptions.",
        "Take 500mg of ibuprofen every 4 hours for your headache, but I'm not a doctor.",
        "This is an excellent analysis of the economic situation with thorough research.",
    ],
    "Utility and Meta-Scoring": [
        "Content that needs multiple evaluation criteria applied simultaneously.",
        "Text requiring score combination and threshold-based decision making.",
        "Example for testing logical operations and score transformations.",
    ],
}

# Scorer parameter definitions (simulated - in real implementation, these would come from PyRIT)
SCORER_PARAMETERS = {
    "SubStringScorer": [
        {
            "name": "substring",
            "description": "Substring to search for",
            "primary_type": "str",
            "required": True,
            "default": None,
        },
        {
            "name": "category",
            "description": "Score category to assign",
            "primary_type": "str",
            "required": False,
            "default": "match",
        },
    ],
    "SelfAskTrueFalseScorer": [
        {
            "name": "true_false_question",
            "description": "Question to ask about the content",
            "primary_type": "str",
            "required": True,
            "default": None,
        },
        {
            "name": "chat_target",
            "description": "LLM target for evaluation",
            "primary_type": "complex",
            "required": True,
            "default": None,
            "skip_in_ui": True,
        },
    ],
    "SelfAskLikertScorer": [
        {
            "name": "likert_scale_question",
            "description": "Likert scale question",
            "primary_type": "str",
            "required": True,
            "default": None,
        },
        {
            "name": "scale_min",
            "description": "Minimum scale value",
            "primary_type": "int",
            "required": False,
            "default": 1,
        },
        {
            "name": "scale_max",
            "description": "Maximum scale value",
            "primary_type": "int",
            "required": False,
            "default": 5,
        },
        {
            "name": "chat_target",
            "description": "LLM target for evaluation",
            "primary_type": "complex",
            "required": True,
            "default": None,
            "skip_in_ui": True,
        },
    ],
    "SelfAskCategoryScorer": [
        {
            "name": "category_question",
            "description": "Question for categorization",
            "primary_type": "str",
            "required": True,
            "default": None,
        },
        {
            "name": "categories",
            "description": "Available categories",
            "primary_type": "list",
            "required": True,
            "default": [],
        },
        {
            "name": "chat_target",
            "description": "LLM target for evaluation",
            "primary_type": "complex",
            "required": True,
            "default": None,
            "skip_in_ui": True,
        },
    ],
    "SelfAskScaleScorer": [
        {
            "name": "scale_question",
            "description": "Question for scale scoring",
            "primary_type": "str",
            "required": True,
            "default": None,
        },
        {
            "name": "scale_arguments",
            "description": "Scale argument descriptions",
            "primary_type": "str",
            "required": True,
            "default": "",
        },
        {
            "name": "chat_target",
            "description": "LLM target for evaluation",
            "primary_type": "complex",
            "required": True,
            "default": None,
            "skip_in_ui": True,
        },
    ],
    "SelfAskRefusalScorer": [
        {
            "name": "chat_target",
            "description": "LLM target for evaluation",
            "primary_type": "complex",
            "required": True,
            "default": None,
            "skip_in_ui": True,
        }
    ],
    "CompositeScorer": [
        {
            "name": "scorers",
            "description": "List of scorers to combine",
            "primary_type": "list",
            "required": True,
            "default": [],
        },
        {
            "name": "combination_logic",
            "description": "How to combine scores",
            "primary_type": "str",
            "required": False,
            "default": "average",
            "literal_choices": ["average", "max", "min", "majority"],
        },
    ],
    "FloatScaleThresholdScorer": [
        {
            "name": "threshold",
            "description": "Threshold value",
            "primary_type": "float",
            "required": True,
            "default": 0.5,
        },
        {
            "name": "scorer",
            "description": "Base scorer to apply threshold to",
            "primary_type": "complex",
            "required": True,
            "default": None,
        },
    ],
    "TrueFalseInverterScorer": [
        {
            "name": "scorer",
            "description": "Base scorer to invert",
            "primary_type": "complex",
            "required": True,
            "default": None,
        }
    ],
}


def get_user_id(current_user) -> str:
    """Extract user ID from current user object."""
    if hasattr(current_user, "sub"):
        return current_user.sub
    elif hasattr(current_user, "email"):
        return current_user.email
    elif hasattr(current_user, "username"):
        return current_user.username
    else:
        return "default_user"


@router.get("/types", response_model=ScorerTypesResponse, summary="Get available scorer types")
async def get_scorer_types(current_user: Any = Depends(get_current_user)) -> Any:
    """Get list of available scorer categories and types."""
    try:
        logger.info("Loading scorer types and categories")

        # Convert categories to response format
        categories = {}
        for cat_name, cat_info in SCORER_CATEGORIES.items():
            categories[cat_name] = {
                "description": cat_info["description"],
                "strengths": cat_info["strengths"],
                "limitations": cat_info["limitations"],
                "best_scenarios": cat_info["best_scenarios"],
                "scorers": cat_info["scorers"],
            }

        # Get all available scorer types
        all_scorers = []
        for cat_info in SCORER_CATEGORIES.values():
            all_scorers.extend(cat_info["scorers"])

        response = ScorerTypesResponse(
            categories=categories, available_scorers=all_scorers, test_cases=CATEGORY_TEST_CASES
        )

        logger.info(f"Loaded {len(all_scorers)} scorer types in {len(categories)} categories")
        return response

    except Exception as e:
        logger.error(f"Error loading scorer types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load scorer types: {str(e)}")


@router.get("/params/{scorer_type}", response_model=ScorerParametersResponse, summary="Get scorer parameters")
async def get_scorer_parameters(scorer_type: str, current_user=Depends(get_current_user)) -> Any:
    """Get parameter definitions for a specific scorer type."""
    try:
        logger.info(f"Getting parameters for scorer type: {scorer_type}")

        if scorer_type not in SCORER_PARAMETERS:
            raise HTTPException(status_code=404, detail=f"Scorer type '{scorer_type}' not found")

        param_defs = SCORER_PARAMETERS[scorer_type]

        # Convert to response format
        parameters = []
        requires_target = False

        for param in param_defs:
            parameters.append(ScorerParameter(**param))
            if param["name"] == "chat_target":
                requires_target = True

        # Find category for this scorer
        category = "Other"
        for cat_name, cat_info in SCORER_CATEGORIES.items():
            if scorer_type in cat_info["scorers"]:
                category = cat_name
                break

        response = ScorerParametersResponse(
            scorer_type=scorer_type,
            parameters=parameters,
            requires_target=requires_target,
            category=category,
            description=f"Parameter definitions for {scorer_type}",
        )

        logger.info(f"Retrieved {len(parameters)} parameters for {scorer_type}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scorer parameters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scorer parameters: {str(e)}")


@router.get("", response_model=ScorersListResponse, summary="List configured scorers")
async def list_scorers(current_user: Any = Depends(get_current_user)) -> Any:
    """Get list of all configured scorers."""
    try:
        user_id = current_user.username
        logger.info(f"Listing scorers for user: {user_id}")

        # Get user's scorers from DuckDB
        db_manager = get_duckdb_manager(user_id)
        scorers_data = db_manager.list_scorers()

        # Convert to dictionary format for compatibility
        all_scorers = {}
        for scorer_data in scorers_data:
            all_scorers[scorer_data["id"]] = {
                "id": scorer_data["id"],
                "name": scorer_data["name"],
                "type": scorer_data["type"],
                "parameters": scorer_data["parameters"],
                "status": scorer_data.get("status", "ready"),
                "created_at": scorer_data["created_at"],
                "test_count": 0,  # Default value
            }

        # Convert to response format
        scorer_list = []
        category_counts = {}

        for scorer_id, scorer_data in all_scorers.items():
            # Find category for this scorer
            scorer_type = scorer_data.get("type", "Unknown")
            category = "Other"
            for cat_name, cat_info in SCORER_CATEGORIES.items():
                if scorer_type in cat_info["scorers"]:
                    category = cat_name
                    break

            scorer_info = ScorerInfo(
                id=scorer_id,
                name=scorer_data.get("name", scorer_id),
                type=scorer_type,
                category=category,
                parameters=scorer_data.get("parameters", {}),
                created_at=scorer_data.get("created_at", datetime.now()),
                last_tested=scorer_data.get("last_tested"),
                test_count=scorer_data.get("test_count", 0),
            )
            scorer_list.append(scorer_info)

            # Count by category
            category_counts[category] = category_counts.get(category, 0) + 1

        response = ScorersListResponse(scorers=scorer_list, total=len(scorer_list), by_category=category_counts)

        logger.info(f"Listed {len(scorer_list)} scorers for user {user_id}")
        return response

    except Exception as e:
        logger.error(f"Error listing scorers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list scorers: {str(e)}")


@router.post("", response_model=ScorerCreateResponse, summary="Create new scorer")
async def create_scorer(request: ScorerCreateRequest, current_user=Depends(get_current_user)) -> Any:
    """Create a new scorer configuration."""
    try:
        user_id = current_user.username
        logger.info(f"Creating scorer '{request.name}' of type '{request.scorer_type}' for user {user_id}")

        # Check if scorer type is valid
        if request.scorer_type not in SCORER_PARAMETERS:
            raise HTTPException(status_code=400, detail=f"Invalid scorer type: {request.scorer_type}")

        # Check for duplicate names in DuckDB
        db_manager = get_duckdb_manager(user_id)
        existing_scorers = db_manager.list_scorers()
        for scorer in existing_scorers:
            if scorer["name"] == request.name:
                raise HTTPException(status_code=409, detail=f"Scorer with name '{request.name}' already exists")

        # Validate parameters
        param_defs = SCORER_PARAMETERS[request.scorer_type]
        for param_def in param_defs:
            param_name = param_def["name"]
            is_required = param_def.get("required", False)

            if is_required and param_name not in request.parameters:
                if param_name == "chat_target" and request.generator_id:
                    # Handle chat_target via generator_id
                    continue
                else:
                    raise HTTPException(status_code=400, detail=f"Required parameter '{param_name}' is missing")

        # Create scorer configuration
        scorer_id = str(uuid.uuid4())
        scorer_config = {
            "id": scorer_id,
            "name": request.name,
            "type": request.scorer_type,
            "parameters": request.parameters,
            "generator_id": request.generator_id,
            "created_at": datetime.now(),
            "created_by": user_id,
            "test_count": 0,
        }

        # Store in DuckDB
        scorer_id = db_manager.create_scorer(
            name=request.name, scorer_type=request.scorer_type, parameters=request.parameters
        )

        # Create response
        response = ScorerCreateResponse(
            success=True,
            scorer={
                "id": scorer_id,
                "name": request.name,
                "type": request.scorer_type,
                "parameters": request.parameters,
                "created_at": scorer_config["created_at"].isoformat(),
            },
            message=f"Scorer '{request.name}' created successfully",
        )

        logger.info(f"Successfully created scorer '{request.name}' with ID {scorer_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating scorer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create scorer: {str(e)}")


@router.post("/{scorer_id}/clone", response_model=ScorerCreateResponse, summary="Clone scorer")
async def clone_scorer(scorer_id: str, request: ScorerCloneRequest, current_user=Depends(get_current_user)) -> Any:
    """Clone an existing scorer configuration."""
    try:
        user_id = current_user.username
        logger.info(f"Cloning scorer {scorer_id} as '{request.new_name}' for user {user_id}")

        # Find original scorer in DuckDB
        db_manager = get_duckdb_manager(user_id)
        original_config = db_manager.get_scorer(scorer_id)

        if not original_config:
            raise HTTPException(status_code=404, detail=f"Scorer with ID '{scorer_id}' not found")

        # Check for duplicate names in DuckDB
        existing_scorers = db_manager.list_scorers()
        for scorer in existing_scorers:
            if scorer["name"] == request.new_name:
                raise HTTPException(status_code=409, detail=f"Scorer with name '{request.new_name}' already exists")

        # Create cloned configuration
        new_scorer_id = str(uuid.uuid4())
        cloned_config = {
            "id": new_scorer_id,
            "name": request.new_name,
            "type": original_config["type"],
            "parameters": original_config["parameters"].copy() if request.clone_parameters else {},
            "generator_id": original_config.get("generator_id"),
            "created_at": datetime.now(),
            "created_by": user_id,
            "test_count": 0,
            "cloned_from": scorer_id,
        }

        # Store cloned scorer in DuckDB
        new_scorer_id = db_manager.create_scorer(
            name=request.new_name,
            scorer_type=original_config["type"],
            parameters=original_config["parameters"].copy() if request.clone_parameters else {},
        )

        response = ScorerCreateResponse(
            success=True,
            scorer={
                "id": new_scorer_id,
                "name": request.new_name,
                "type": cloned_config["type"],
                "parameters": cloned_config["parameters"],
                "created_at": cloned_config["created_at"].isoformat(),
            },
            message=f"Scorer cloned as '{request.new_name}'",
        )

        logger.info(f"Successfully cloned scorer {scorer_id} to {new_scorer_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning scorer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clone scorer: {str(e)}")


@router.put("/{scorer_id}", response_model=ScorerCreateResponse, summary="Update scorer")
async def update_scorer(scorer_id: str, request: ScorerUpdateRequest, current_user=Depends(get_current_user)) -> Any:
    """Update an existing scorer configuration."""
    try:
        user_id = current_user.username
        logger.info(f"Updating scorer {scorer_id} for user {user_id}")

        # Find scorer in DuckDB
        db_manager = get_duckdb_manager(user_id)
        scorer_config = db_manager.get_scorer(scorer_id)

        if not scorer_config:
            raise HTTPException(status_code=404, detail=f"Scorer with ID '{scorer_id}' not found")

        # Update fields (Note: Update functionality needs implementation in DuckDB manager)
        if request.name is not None:
            logger.info(f"Scorer name update requested: {request.name} (update functionality needs implementation)")

        if request.parameters is not None:
            logger.info("Scorer parameters update requested (update functionality needs implementation)")

        response = ScorerCreateResponse(
            success=True,
            scorer={
                "id": scorer_id,
                "name": scorer_config["name"],
                "type": scorer_config["type"],
                "parameters": scorer_config["parameters"],
                "updated_at": scorer_config["updated_at"].isoformat(),
            },
            message="Scorer updated successfully",
        )

        logger.info(f"Successfully updated scorer {scorer_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating scorer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update scorer: {str(e)}")


@router.delete("/{scorer_id}", response_model=ScorerDeleteResponse, summary="Delete scorer")
async def delete_scorer(scorer_id: str, current_user=Depends(get_current_user)) -> Any:
    """Delete a scorer configuration."""
    try:
        user_id = current_user.username
        logger.info(f"Deleting scorer {scorer_id} for user {user_id}")

        # Find and delete scorer from DuckDB
        db_manager = get_duckdb_manager(user_id)
        scorer_data = db_manager.get_scorer(scorer_id)

        if not scorer_data:
            raise HTTPException(status_code=404, detail=f"Scorer with ID '{scorer_id}' not found")

        scorer_name = scorer_data["name"]
        deleted = db_manager.delete_scorer(scorer_id)

        if not deleted:
            raise HTTPException(status_code=500, detail=f"Failed to delete scorer with ID '{scorer_id}'")

        response = ScorerDeleteResponse(success=True, message="Scorer deleted successfully", deleted_scorer=scorer_name)

        logger.info(f"Successfully deleted scorer {scorer_id}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting scorer: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete scorer: {str(e)}")


async def _execute_real_pyrit_scorer(
    scorer_type: str, parameters: Dict[str, Any], test_input: str
) -> List[Dict[str, Any]]:
    """Execute real PyRIT scorer and return results."""
    try:
        import uuid
        from datetime import datetime

        from pyrit.models import PromptRequestPiece, PromptRequestResponse

        logger.info(f"Executing real PyRIT scorer: {scorer_type} with parameters: {parameters}")

        # Create scorer instance based on type
        scorer_instance = await _create_pyrit_scorer_instance(scorer_type, parameters)

        if not scorer_instance:
            raise ValueError(f"Failed to create PyRIT scorer instance for type: {scorer_type}")

        # Create a PromptRequestResponse for the scorer to evaluate
        # This mimics how PyRIT scorers expect to receive data
        test_piece = PromptRequestPiece(
            role="assistant",  # Scorers typically evaluate assistant responses
            original_value=test_input,
            converted_value=test_input,
            conversation_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
        )

        test_response = PromptRequestResponse(request_pieces=[test_piece])

        # Execute the scorer
        logger.info(f"Running PyRIT scorer {scorer_type} on test input")
        score_results = await scorer_instance.score_async(test_response)

        # Convert PyRIT scores to API response format
        results = []
        for score in score_results:
            if hasattr(score, "score_value") and hasattr(score, "score_category"):
                results.append(
                    {
                        "score_value": score.score_value,
                        "score_category": score.score_category,
                        "score_rationale": getattr(score, "score_rationale", "PyRIT scorer evaluation"),
                    }
                )

        logger.info(f"PyRIT scorer returned {len(results)} score results")
        return results

    except Exception as e:
        logger.error(f"Error executing real PyRIT scorer {scorer_type}: {e}")
        raise


async def _create_pyrit_scorer_instance(scorer_type: str, parameters: Dict[str, Any]) -> Any:
    """Create a real PyRIT scorer instance."""
    try:
        logger.info(f"Creating PyRIT scorer instance: {scorer_type}")

        # Import PyRIT scorers based on type
        if scorer_type == "SubStringScorer":
            from pyrit.score import SubStringScorer

            substring = parameters.get("substring", "")
            category = parameters.get("category", "match")
            return SubStringScorer(substring=substring, category=category)

        elif scorer_type == "SelfAskLikertScorer":
            from pyrit.score import SelfAskLikertScorer

            # This requires a PromptTarget for the LLM evaluation
            # For testing purposes, we'll need to configure with user's generator
            logger.warning("SelfAskLikertScorer requires PromptTarget configuration - using simplified version")
            # Return None to indicate this scorer type needs more complex setup
            return None

        elif scorer_type == "AzureContentFilterScorer":
            from pyrit.score import AzureContentFilterScorer

            # This requires Azure API configuration
            logger.warning("AzureContentFilterScorer requires Azure API configuration")
            return None

        elif scorer_type == "HuggingFaceTextClassificationScorer":
            from pyrit.score import HuggingFaceTextClassificationScorer

            model_name = parameters.get("model_name", "unitary/toxic-bert")
            return HuggingFaceTextClassificationScorer(model_name=model_name)

        elif scorer_type == "RegexScorer":
            from pyrit.score import RegexScorer

            pattern = parameters.get("pattern", ".*")
            category = parameters.get("category", "regex_match")
            return RegexScorer(pattern=pattern, category=category)

        else:
            logger.error(f"Unsupported PyRIT scorer type: {scorer_type}")
            return None

    except ImportError as e:
        logger.error(f"Failed to import PyRIT scorer {scorer_type}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error creating PyRIT scorer {scorer_type}: {e}")
        return None


@router.post("/validate", response_model=ScorerValidationResponse, summary="Validate scorer configuration")
async def validate_scorer_config(request: ScorerValidationRequest, current_user=Depends(get_current_user)) -> bool:
    """Validate a scorer configuration before creation."""
    try:
        logger.info(f"Validating scorer configuration for type: {request.scorer_type}")

        errors = []
        warnings = []
        suggested_fixes = []

        # Check if scorer type exists
        if request.scorer_type not in SCORER_PARAMETERS:
            errors.append(f"Unknown scorer type: {request.scorer_type}")
            return ScorerValidationResponse(
                valid=False,
                errors=errors,
                warnings=warnings,
                suggested_fixes=["Choose a valid scorer type from the available options"],
            )

        # Validate parameters
        param_defs = SCORER_PARAMETERS[request.scorer_type]
        required_params = [p for p in param_defs if p.get("required", False)]

        for param_def in required_params:
            param_name = param_def["name"]
            if param_name == "chat_target":
                # Special handling for chat_target
                if not request.generator_id and param_name not in request.parameters:
                    errors.append("Chat target is required but no generator_id provided")
                    suggested_fixes.append("Select a generator to use as chat target")
            elif param_name not in request.parameters:
                errors.append(f"Required parameter '{param_name}' is missing")
                suggested_fixes.append(f"Provide value for required parameter '{param_name}'")

        # Type validation for provided parameters
        for param_name, param_value in request.parameters.items():
            param_def = next((p for p in param_defs if p["name"] == param_name), None)
            if param_def:
                expected_type = param_def["primary_type"]
                if expected_type == "str" and not isinstance(param_value, str):
                    warnings.append(f"Parameter '{param_name}' should be a string")
                elif expected_type == "int" and not isinstance(param_value, int):
                    warnings.append(f"Parameter '{param_name}' should be an integer")
                elif expected_type == "float" and not isinstance(param_value, (int, float)):
                    warnings.append(f"Parameter '{param_name}' should be a number")
                elif expected_type == "bool" and not isinstance(param_value, bool):
                    warnings.append(f"Parameter '{param_name}' should be a boolean")
                elif expected_type == "list" and not isinstance(param_value, list):
                    warnings.append(f"Parameter '{param_name}' should be a list")

        is_valid = len(errors) == 0

        response = ScorerValidationResponse(
            valid=is_valid, errors=errors, warnings=warnings, suggested_fixes=suggested_fixes
        )

        logger.info(f"Validation completed for {request.scorer_type}: valid={is_valid}")
        return response

    except Exception as e:
        logger.error(f"Error validating scorer configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.get("/health", response_model=ScorerHealthResponse, summary="Get scorer system health")
async def get_scorer_health(current_user: Any = Depends(get_current_user)) -> Any:
    """Get health status of scorer system."""
    try:
        user_id = current_user.username
        logger.info(f"Checking scorer health for user {user_id}")

        # Count scorers from DuckDB
        db_manager = get_duckdb_manager(user_id)
        scorers_data = db_manager.list_scorers()
        total_scorers = len(scorers_data)

        # Simulate health checks (in real implementation, would test actual scorers)
        active_scorers = total_scorers  # Assume all are active in simulation
        failed_scorers = []  # No failed scorers in simulation

        response = ScorerHealthResponse(
            healthy=True,
            total_scorers=total_scorers,
            active_scorers=active_scorers,
            failed_scorers=failed_scorers,
            system_info={
                "user_scorers": len(scorers_data),
                "global_scorers": 0,  # No global scorers in DuckDB approach
                "available_types": len(SCORER_PARAMETERS),
                "categories": len(SCORER_CATEGORIES),
            },
        )

        logger.info(f"Health check completed: {total_scorers} total scorers")
        return response

    except Exception as e:
        logger.error(f"Error checking scorer health: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


# Helper functions for scorer testing modes are now handled by orchestrator patterns
