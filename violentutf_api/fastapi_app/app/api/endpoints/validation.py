# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""API endpoints for dataset validation operations.

SECURITY: All endpoints require authentication and input validation.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth import get_current_user
from app.core.dataset_validation import ValidationStatus
from app.core.validation import ValidationError
from app.schemas.validation import ValidationError as ValidationErrorSchema
from app.schemas.validation import (
    ValidationHistoryResponse,
    ValidationRequest,
    ValidationResponse,
    ValidationServiceStatus,
    ValidationStatsResponse,
)
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)

router = APIRouter()

# Global validation service instance
validation_service = ValidationService()


@router.post(
    "/validate",
    response_model=ValidationResponse,
    summary="Validate Dataset",
    description="Perform comprehensive validation on a dataset",
    responses={
        200: {"description": "Validation completed successfully"},
        422: {"model": ValidationErrorSchema, "description": "Validation error"},
        500: {"model": ValidationErrorSchema, "description": "Internal server error"},
    },
)
async def validate_dataset(
    request: ValidationRequest, current_user: dict = Depends(get_current_user)
) -> ValidationResponse:
    """Validate a dataset with comprehensive checks.

    Args:
        request: Validation request parameters
        current_user: Current authenticated user

    Returns:
        ValidationResponse with detailed results

    Raises:
        HTTPException: If validation fails or encounters errors
    """
    try:
        logger.info(
            "User %s requested validation for dataset %s with level %s",
            current_user.get("username", "unknown"),
            request.dataset_id,
            request.validation_level,
        )

        # Get user context for dataset access
        user_context = current_user.get("username", "unknown")

        # Perform validation
        result = await validation_service.validate_dataset(request, user_context)

        logger.info("Validation %s completed with status: %s", result.validation_id, result.overall_result)
        return result

    except ValidationError as e:
        logger.error("Validation error for dataset %s: %s", request.dataset_id, e)
        raise
    except Exception as e:
        logger.error("Unexpected error during validation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Validation failed: {str(e)}"
        ) from e


@router.get(
    "/status",
    response_model=ValidationServiceStatus,
    summary="Get Validation Service Status",
    description="Get the current status and statistics of the validation service",
)
async def get_validation_service_status(current_user: dict = Depends(get_current_user)) -> ValidationServiceStatus:
    """Get validation service status and statistics.

    Args:
        current_user: Current authenticated user

    Returns:
        ValidationServiceStatus with service information
    """
    try:
        status_info = await validation_service.get_service_status()

        return ValidationServiceStatus(
            status=status_info["status"],
            available_validators=status_info["available_validators"],
            total_validations=status_info["total_validations"],
            active_validations=status_info["active_validations"],
            service_uptime_seconds=status_info["service_uptime_seconds"],
            memory_usage_mb=status_info["memory_usage_mb"],
            last_validation=status_info["last_validation"],
        )

    except Exception as e:
        logger.error("Error getting validation service status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not retrieve service status: {str(e)}"
        ) from e


@router.get(
    "/history",
    response_model=ValidationHistoryResponse,
    summary="Get Validation History",
    description="Get validation history with optional filtering and pagination",
)
async def get_validation_history(
    dataset_id: Optional[str] = Query(None, description="Filter by dataset ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=1000, description="Page size"),
    current_user: dict = Depends(get_current_user),
) -> ValidationHistoryResponse:
    """Get validation history with optional filtering.

    Args:
        dataset_id: Optional dataset ID filter
        page: Page number for pagination
        page_size: Number of items per page
        current_user: Current authenticated user

    Returns:
        ValidationHistoryResponse with paginated history
    """
    try:
        offset = (page - 1) * page_size

        history_entries, total = await validation_service.get_validation_history(
            dataset_id=dataset_id, limit=page_size, offset=offset
        )

        # Convert to response format
        from app.schemas.validation import ValidationHistoryEntry

        entries = [
            ValidationHistoryEntry(
                validation_id=entry["validation_id"],
                dataset_id=entry["dataset_id"],
                validation_level=entry["validation_level"],
                overall_result=entry["overall_result"],
                timestamp=entry["timestamp"],
                execution_time_ms=entry["execution_time_ms"],
                validation_types=entry["validation_types"],
                summary=entry["summary"],
            )
            for entry in history_entries
        ]

        return ValidationHistoryResponse(
            validations=entries, total=total, page=page, page_size=page_size, has_next=offset + page_size < total
        )

    except Exception as e:
        logger.error("Error getting validation history: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not retrieve validation history: {str(e)}"
        ) from e


@router.get(
    "/statistics",
    response_model=ValidationStatsResponse,
    summary="Get Validation Statistics",
    description="Get comprehensive validation statistics and metrics",
)
async def get_validation_statistics(current_user: dict = Depends(get_current_user)) -> ValidationStatsResponse:
    """Get validation statistics and metrics.

    Args:
        current_user: Current authenticated user

    Returns:
        ValidationStatsResponse with comprehensive statistics
    """
    try:
        stats = await validation_service.get_validation_statistics()

        return ValidationStatsResponse(
            total_validations=stats["total_validations"],
            successful_validations=stats["successful_validations"],
            failed_validations=stats["failed_validations"],
            warnings=stats["warnings"],
            average_execution_time_ms=stats["average_execution_time_ms"],
            peak_memory_usage_mb=stats["peak_memory_usage_mb"],
            validation_types=stats["validation_types"],
            dataset_types=stats["dataset_types"],
            status_distribution=stats["status_distribution"],
            last_updated=stats["last_updated"],
        )

    except Exception as e:
        logger.error("Error getting validation statistics: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve validation statistics: {str(e)}",
        ) from e


@router.post(
    "/validate/source",
    response_model=ValidationResponse,
    summary="Validate Source Data Only",
    description="Perform validation on source data file only",
    responses={
        200: {"description": "Source validation completed"},
        422: {"model": ValidationErrorSchema, "description": "Validation error"},
        500: {"model": ValidationErrorSchema, "description": "Internal server error"},
    },
)
async def validate_source_data_only(
    file_path: str = Query(..., description="Path to source data file"),
    validation_level: str = Query("full", description="Validation level (quick/full/deep)"),
    current_user: dict = Depends(get_current_user),
) -> ValidationResponse:
    """Validate source data file only.

    Args:
        file_path: Path to the source data file
        validation_level: Level of validation to perform
        current_user: Current authenticated user

    Returns:
        ValidationResponse with source validation results
    """
    try:
        from app.core.dataset_validation import ValidationLevel

        # Convert string to enum
        level_mapping = {"quick": ValidationLevel.QUICK, "full": ValidationLevel.FULL, "deep": ValidationLevel.DEEP}

        if validation_level not in level_mapping:
            raise ValidationError(f"Invalid validation level: {validation_level}")

        level = level_mapping[validation_level]

        # Validate input path (security check)
        if not file_path or ".." in file_path:
            raise ValidationError("Invalid file path")

        logger.info("User %s requested source validation for: %s", current_user.get("username", "unknown"), file_path)

        # Perform source validation only
        result = await validation_service.validate_source_data_only(file_path, level)

        # Convert to response format (simplified for source-only validation)
        from app.schemas.validation import ValidationLevelEnum, ValidationStatusEnum

        def convert_status(validation_status: ValidationStatus) -> ValidationStatusEnum:
            return ValidationStatusEnum(validation_status.value)

        response = ValidationResponse(
            validation_id=f"source_{result.validator_name}_{int(result.timestamp.timestamp())}",
            dataset_id="source_file",
            status="completed",
            overall_result=convert_status(result.status),
            validation_level=ValidationLevelEnum(validation_level),
            results=[validation_service.convert_result_to_schema(result)],
            summary=result.get_summary(),
            total_execution_time_ms=result.execution_time_ms,
            timestamp=result.timestamp,
        )

        return response

    except ValidationError as e:
        logger.error("Source validation error for %s: %s", file_path, e)
        raise
    except Exception as e:
        logger.error("Unexpected error during source validation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Source validation failed: {str(e)}"
        ) from e


@router.get(
    "/validators",
    response_model=List[str],
    summary="Get Available Validators",
    description="Get list of available validators in the system",
)
async def get_available_validators(current_user: dict = Depends(get_current_user)) -> List[str]:
    """Get list of available validators.

    Args:
        current_user: Current authenticated user

    Returns:
        List of available validator names
    """
    try:
        status_info = await validation_service.get_service_status()
        return status_info["available_validators"]

    except Exception as e:
        logger.error("Error getting available validators: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not retrieve validators: {str(e)}"
        ) from e


# Health check endpoint
@router.get(
    "/health",
    summary="Validation Service Health Check",
    description="Check if the validation service is healthy and responsive",
)
async def health_check() -> dict:
    """Health check for validation service.

    Returns:
        Dictionary with health status
    """
    try:
        # Basic health checks
        status_info = await validation_service.get_service_status()

        return {
            "status": "healthy",
            "service_status": status_info["status"],
            "available_validators": len(status_info["available_validators"]),
            "uptime_seconds": status_info["service_uptime_seconds"],
        }

    except Exception as e:
        logger.error("Health check failed: %s", e)
        return {"status": "unhealthy", "error": str(e)}
