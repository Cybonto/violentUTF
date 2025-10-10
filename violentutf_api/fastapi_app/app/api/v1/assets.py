# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Asset Management API Endpoints for Issue #280.

This module provides REST API endpoints for asset management operations,
including CRUD operations, bulk import, and search functionality.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.database import get_session
from app.schemas.asset_schemas import (
    AssetCreate,
    AssetResponse,
    AssetSearchRequest,
    AssetSearchResponse,
    AssetUpdate,
    BulkImportRequest,
    BulkImportResponse,
    BulkUpdateRequest,
    ImportJobStatus,
    ValidationBatchRequest,
    ValidationBatchResponse,
)
from app.services.asset_management.asset_service import AssetNotFoundError, AssetService, DuplicateAssetError
from app.services.asset_management.audit_service import AuditService
from app.services.asset_management.validation_service import ValidationService

router = APIRouter(tags=["assets"])


def get_asset_service(db: AsyncSession = Depends(get_session)) -> AssetService:
    """Get asset service instance with dependencies."""
    audit_service = AuditService(db)
    return AssetService(db, audit_service)


def get_validation_service() -> ValidationService:
    """Get validation service instance."""
    return ValidationService()


@router.get("/", response_model=List[AssetResponse])
async def list_assets(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    security_classification: Optional[str] = Query(None, description="Filter by security classification"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    search: Optional[str] = Query(None, description="Search term for name/description"),
    service: AssetService = Depends(get_asset_service),
    current_user: dict = Depends(get_current_user),
) -> List[AssetResponse]:
    """List database assets with filtering and pagination.

    Args:
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        asset_type: Optional filter by asset type
        security_classification: Optional filter by security classification
        environment: Optional filter by environment
        search: Optional search term for name/description
        service: Asset service dependency
        current_user: Current authenticated user

    Returns:
        List of asset responses
    """
    try:
        filters = {
            "asset_type": asset_type,
            "security_classification": security_classification,
            "environment": environment,
            "search": search,
        }
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}

        assets = await service.list_assets(skip=skip, limit=limit, filters=filters)
        return assets
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to list assets: {str(e)}"
        ) from e


@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    service: AssetService = Depends(get_asset_service),
    current_user: dict = Depends(get_current_user),
) -> AssetResponse:
    """Create a new database asset.

    Args:
        asset_data: Asset creation data
        service: Asset service dependency
        current_user: Current authenticated user

    Returns:
        Created asset response

    Raises:
        HTTPException: If asset creation fails or duplicate exists
    """
    try:
        created_asset = await service.create_asset(asset_data, created_by=current_user.get("username", "unknown"))
        return created_asset
    except DuplicateAssetError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create asset: {str(e)}"
        ) from e


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: uuid.UUID,
    service: AssetService = Depends(get_asset_service),
    current_user: dict = Depends(get_current_user),
) -> AssetResponse:
    """Get specific database asset by ID.

    Args:
        asset_id: Asset UUID
        service: Asset service dependency
        current_user: Current authenticated user

    Returns:
        Asset response

    Raises:
        HTTPException: If asset not found
    """
    try:
        asset = await service.get_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
        return asset
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve asset: {str(e)}"
        ) from e


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(
    asset_id: uuid.UUID,
    asset_data: AssetUpdate,
    service: AssetService = Depends(get_asset_service),
    current_user: dict = Depends(get_current_user),
) -> AssetResponse:
    """Update existing database asset.

    Args:
        asset_id: Asset UUID
        asset_data: Asset update data
        service: Asset service dependency
        current_user: Current authenticated user

    Returns:
        Updated asset response

    Raises:
        HTTPException: If asset not found or update fails
    """
    try:
        updated_asset = await service.update_asset(
            asset_id, asset_data, updated_by=current_user.get("username", "unknown")
        )
        return updated_asset
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found") from exc
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update asset: {str(e)}"
        ) from e


@router.patch("/{asset_id}", response_model=AssetResponse)
async def patch_asset(
    asset_id: uuid.UUID,
    asset_data: AssetUpdate,
    service: AssetService = Depends(get_asset_service),
    current_user: dict = Depends(get_current_user),
) -> AssetResponse:
    """Update existing database asset partially.

    Args:
        asset_id: Asset UUID
        asset_data: Partial asset update data
        service: Asset service dependency
        current_user: Current authenticated user

    Returns:
        Updated asset response

    Raises:
        HTTPException: If asset not found or update fails
    """
    # PATCH and PUT have same implementation for this use case
    return await update_asset(asset_id, asset_data, service, current_user)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: uuid.UUID,
    service: AssetService = Depends(get_asset_service),
    current_user: dict = Depends(get_current_user),
) -> None:
    """Soft delete database asset.

    Args:
        asset_id: Asset UUID
        service: Asset service dependency
        current_user: Current authenticated user

    Raises:
        HTTPException: If asset not found or deletion fails
    """
    try:
        deleted = await service.delete_asset(asset_id, deleted_by=current_user.get("username", "unknown"))
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete asset: {str(e)}"
        ) from e


@router.post("/search", response_model=AssetSearchResponse)
async def search_assets(
    search_request: AssetSearchRequest,
    service: AssetService = Depends(get_asset_service),
    current_user: dict = Depends(get_current_user),
) -> AssetSearchResponse:
    """Search assets by query with advanced filtering.

    Args:
        search_request: Search request with query and filters
        service: Asset service dependency
        current_user: Current authenticated user

    Returns:
        Search response with results and metadata
    """
    try:
        import time

        start_time = time.time()

        # Perform search
        assets = await service.search_assets(
            search_term=search_request.query, limit=search_request.limit, offset=search_request.offset
        )

        execution_time = time.time() - start_time

        return AssetSearchResponse(
            results=assets, total_matches=len(assets), query=search_request.query, execution_time=execution_time
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Search failed: {str(e)}") from e


# Bulk operations endpoints
@router.post("/bulk-import", response_model=BulkImportResponse, status_code=status.HTTP_202_ACCEPTED)
async def bulk_import_assets(
    import_data: BulkImportRequest,
    background_tasks: BackgroundTasks,
    service: AssetService = Depends(get_asset_service),
    validation_service: ValidationService = Depends(get_validation_service),
    current_user: dict = Depends(get_current_user),
) -> BulkImportResponse:
    """Import multiple assets from discovery results.

    Args:
        import_data: Bulk import request data
        background_tasks: FastAPI background tasks
        service: Asset service dependency
        validation_service: Validation service dependency
        current_user: Current authenticated user

    Returns:
        Bulk import response with job ID
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Add background task for processing
        background_tasks.add_task(
            _process_bulk_import,
            job_id=job_id,
            import_data=import_data,
            service=service,
            validation_service=validation_service,
            created_by=current_user.get("username", "unknown"),
        )

        return BulkImportResponse(
            job_id=job_id,
            status="processing",
            assets_count=len(import_data.assets),
            estimated_duration=len(import_data.assets) * 2,  # Rough estimate: 2 seconds per asset
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start bulk import: {str(e)}"
        ) from e


@router.get("/import-status/{job_id}", response_model=ImportJobStatus)
async def get_import_status(job_id: str, current_user: dict = Depends(get_current_user)) -> ImportJobStatus:
    """Check bulk import job status.

    Args:
        job_id: Import job ID
        current_user: Current authenticated user

    Returns:
        Import job status
    """
    # This would typically fetch from a job tracking system (Redis, database, etc.)
    # For now, return a mock response
    return ImportJobStatus(
        job_id=job_id,
        status="completed",
        progress=1.0,
        assets_processed=0,
        assets_created=0,
        assets_updated=0,
        assets_failed=0,
        errors=[],
        started_at=datetime.now(),
        completed_at=datetime.now(),
    )


@router.post("/validate-batch", response_model=ValidationBatchResponse)
async def validate_batch(
    validation_request: ValidationBatchRequest,
    validation_service: ValidationService = Depends(get_validation_service),
    current_user: dict = Depends(get_current_user),
) -> ValidationBatchResponse:
    """Validate asset data before import.

    Args:
        validation_request: Batch validation request
        validation_service: Validation service dependency
        current_user: Current authenticated user

    Returns:
        Validation batch response
    """
    try:
        # Convert bulk import assets to asset create objects
        assets_to_validate = []
        for bulk_asset in validation_request.assets:
            asset_create = AssetCreate(
                name=bulk_asset.name,
                asset_type=bulk_asset.asset_type,
                unique_identifier=bulk_asset.unique_identifier,
                location=bulk_asset.location,
                security_classification=bulk_asset.security_classification,
                criticality_level=bulk_asset.criticality_level,
                environment=bulk_asset.environment,
                discovery_method=bulk_asset.discovery_method,
                confidence_score=bulk_asset.confidence_score,
                connection_string=bulk_asset.connection_string,
                technical_contact=bulk_asset.technical_contact,
                backup_configured=bulk_asset.backup_configured,
                compliance_requirements=bulk_asset.compliance_requirements,
            )
            assets_to_validate.append(asset_create)

        # Validate batch
        validation_results = await validation_service.validate_batch(assets_to_validate)

        return ValidationBatchResponse(
            valid_count=validation_results["valid_count"],
            invalid_count=validation_results["invalid_count"],
            validation_errors=validation_results["validation_errors"],
            validation_warnings=validation_results["validation_warnings"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Batch validation failed: {str(e)}"
        ) from e


@router.post("/bulk-update", status_code=status.HTTP_202_ACCEPTED)
async def bulk_update_assets(
    update_request: BulkUpdateRequest,
    background_tasks: BackgroundTasks,
    service: AssetService = Depends(get_asset_service),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update multiple assets in bulk.

    Args:
        update_request: Bulk update request
        background_tasks: FastAPI background tasks
        service: Asset service dependency
        current_user: Current authenticated user

    Returns:
        Bulk update response
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())

        # Add background task for processing
        background_tasks.add_task(
            _process_bulk_update,
            job_id=job_id,
            update_request=update_request,
            service=service,
            updated_by=current_user.get("username", "unknown"),
        )

        return {"job_id": job_id, "status": "processing", "updates_count": len(update_request.updates)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to start bulk update: {str(e)}"
        ) from e


# Background task functions
async def _process_bulk_import(
    job_id: str,
    import_data: BulkImportRequest,
    service: AssetService,
    validation_service: ValidationService,
    created_by: str,
) -> None:
    """Process bulk import in background.

    Args:
        job_id: Import job ID
        import_data: Import data
        service: Asset service
        validation_service: Validation service
        created_by: User creating assets
    """
    # This would be implemented to process the bulk import
    # and update job status in a tracking system
    # TODO: Implement background bulk import processing


async def _process_bulk_update(
    job_id: str, update_request: BulkUpdateRequest, service: AssetService, updated_by: str
) -> None:
    """Process bulk update in background.

    Args:
        job_id: Update job ID
        update_request: Update request data
        service: Asset service
        updated_by: User updating assets
    """
    # This would be implemented to process the bulk update
    # and update job status in a tracking system
    # TODO: Implement background bulk update processing
