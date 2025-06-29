import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.auth import get_current_user
from app.db.database import get_session
from app.models.orchestrator import OrchestratorConfiguration, OrchestratorExecution
from app.schemas.orchestrator import OrchestratorExecuteResponse  # Keep for backward compatibility in RESTful endpoint
from app.schemas.orchestrator import (  # RESTful schemas
    ExecutionCreate,
    ExecutionListResponse,
    ExecutionResponse,
    OrchestratorConfigCreate,
    OrchestratorConfigResponse,
    OrchestratorMemoryResponse,
    OrchestratorResultsResponse,
    OrchestratorScoresResponse,
    OrchestratorTypeInfo,
)
from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/types", response_model=List[OrchestratorTypeInfo], summary="List orchestrator types")
async def list_orchestrator_types(current_user=Depends(get_current_user)):
    """Get all available PyRIT orchestrator types with metadata"""
    try:
        orchestrator_types = pyrit_orchestrator_service.get_orchestrator_types()
        return orchestrator_types
    except Exception as e:
        logger.error(f"Error listing orchestrator types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list orchestrator types: {str(e)}")


@router.get("/types/{orchestrator_type}", summary="Get orchestrator type details")
async def get_orchestrator_type_details(orchestrator_type: str, current_user=Depends(get_current_user)):
    """Get detailed information about a specific orchestrator type"""
    try:
        orchestrator_types = pyrit_orchestrator_service.get_orchestrator_types()
        type_info = next((t for t in orchestrator_types if t["name"] == orchestrator_type), None)

        if not type_info:
            raise HTTPException(status_code=404, detail=f"Orchestrator type not found: {orchestrator_type}")

        return type_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orchestrator type details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orchestrator type details: {str(e)}")


@router.post("", response_model=OrchestratorConfigResponse, summary="Create orchestrator configuration")
async def create_orchestrator_configuration(
    request: OrchestratorConfigCreate, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """Create and save PyRIT orchestrator configuration"""
    return await _create_orchestrator_configuration_impl(request, db, current_user)


@router.post("/create", response_model=OrchestratorConfigResponse, summary="Create orchestrator configuration (alias)")
async def create_orchestrator_configuration_alias(
    request: OrchestratorConfigCreate, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """Create and save PyRIT orchestrator configuration (alias endpoint)"""
    return await _create_orchestrator_configuration_impl(request, db, current_user)


async def _create_orchestrator_configuration_impl(request: OrchestratorConfigCreate, db: AsyncSession, current_user):
    """Create and save PyRIT orchestrator configuration"""
    try:
        # Check if name already exists
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.name == request.name)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail=f"Orchestrator with name '{request.name}' already exists")

        # Create orchestrator instance with user context for generator resolution
        orchestrator_id = await pyrit_orchestrator_service.create_orchestrator_instance(
            {
                "orchestrator_type": request.orchestrator_type,
                "parameters": request.parameters,
                "user_context": current_user.username,  # Pass user context for generator lookup
            }
        )

        # Save to database
        config = OrchestratorConfiguration(
            id=UUID(orchestrator_id),
            name=request.name,
            orchestrator_type=request.orchestrator_type,
            description=request.description,
            parameters=request.parameters,
            tags=request.tags,
            status="configured",
            created_by=current_user.username,
            instance_active=True,
        )

        db.add(config)
        await db.commit()
        await db.refresh(config)

        logger.info(f"User {current_user.username} created orchestrator: {request.name}")

        return OrchestratorConfigResponse(
            orchestrator_id=config.id,
            name=config.name,
            orchestrator_type=config.orchestrator_type,
            status=config.status,
            created_at=config.created_at,
            parameters_validated=True,
            pyrit_identifier=config.pyrit_identifier,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating orchestrator configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create orchestrator: {str(e)}")


@router.get("", summary="List orchestrator configurations")
async def list_orchestrator_configurations(
    orchestrator_type: Optional[str] = Query(None, description="Filter by orchestrator type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """List all configured orchestrators with optional filtering"""
    try:
        stmt = select(OrchestratorConfiguration)

        if orchestrator_type:
            stmt = stmt.where(OrchestratorConfiguration.orchestrator_type == orchestrator_type)

        if status:
            stmt = stmt.where(OrchestratorConfiguration.status == status)

        result = await db.execute(stmt)
        configurations = result.scalars().all()

        return [
            {
                "orchestrator_id": config.id,
                "name": config.name,
                "orchestrator_type": config.orchestrator_type,
                "description": config.description,
                "status": config.status,
                "tags": config.tags,
                "created_at": config.created_at,
                "instance_active": config.instance_active,
            }
            for config in configurations
        ]

    except Exception as e:
        logger.error(f"Error listing orchestrator configurations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list orchestrators: {str(e)}")


@router.get("/{orchestrator_id}", summary="Get orchestrator configuration")
async def get_orchestrator_configuration(
    orchestrator_id: UUID, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """Get specific orchestrator configuration"""
    try:
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator not found: {orchestrator_id}")

        return {
            "orchestrator_id": config.id,
            "name": config.name,
            "orchestrator_type": config.orchestrator_type,
            "description": config.description,
            "parameters": config.parameters,
            "status": config.status,
            "tags": config.tags,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
            "instance_active": config.instance_active,
            "pyrit_identifier": config.pyrit_identifier,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orchestrator configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orchestrator: {str(e)}")


# DEPRECATED: This endpoint has been replaced by POST /{orchestrator_id}/executions
# The non-RESTful verb-based URI violates REST principles
# Use POST /{orchestrator_id}/executions instead for creating new executions


@router.get(
    "/executions/{execution_id}/results", response_model=OrchestratorResultsResponse, summary="Get execution results"
)
async def get_execution_results(
    execution_id: UUID, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """Get results from orchestrator execution"""
    try:
        stmt = select(OrchestratorExecution).where(OrchestratorExecution.id == execution_id)
        result = await db.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

        # Get orchestrator configuration
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == execution.orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator configuration not found")

        if execution.status != "completed":
            raise HTTPException(status_code=400, detail=f"Execution not completed. Status: {execution.status}")

        return OrchestratorResultsResponse(
            execution_id=execution.id,
            status=execution.status,
            orchestrator_name=config.name,
            orchestrator_type=config.orchestrator_type,
            execution_summary=execution.execution_summary or {},
            prompt_request_responses=execution.results.get("prompt_request_responses", []),
            scores=execution.results.get("scores", []),
            memory_export=execution.results.get("memory_export", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution results: {str(e)}")


@router.get("/{orchestrator_id}/memory", response_model=OrchestratorMemoryResponse, summary="Get orchestrator memory")
async def get_orchestrator_memory(
    orchestrator_id: UUID, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """Get PyRIT memory entries for orchestrator"""
    try:
        # Verify orchestrator exists
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator not found: {orchestrator_id}")

        # Get memory from PyRIT service
        memory_pieces = pyrit_orchestrator_service.get_orchestrator_memory(str(orchestrator_id))

        return OrchestratorMemoryResponse(
            orchestrator_id=orchestrator_id,
            memory_pieces=memory_pieces,
            total_pieces=len(memory_pieces),
            conversations=len(set(p["conversation_id"] for p in memory_pieces if p.get("conversation_id"))),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orchestrator memory: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orchestrator memory: {str(e)}")


@router.get("/{orchestrator_id}/scores", response_model=OrchestratorScoresResponse, summary="Get orchestrator scores")
async def get_orchestrator_scores(
    orchestrator_id: UUID, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """Get PyRIT scores for orchestrator"""
    try:
        # Verify orchestrator exists
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator not found: {orchestrator_id}")

        # Get scores from PyRIT service
        scores = pyrit_orchestrator_service.get_orchestrator_scores(str(orchestrator_id))

        return OrchestratorScoresResponse(orchestrator_id=orchestrator_id, scores=scores, total_scores=len(scores))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orchestrator scores: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orchestrator scores: {str(e)}")


# RESTful Execution Endpoints (Phase 1 Implementation)
@router.post("/{orchestrator_id}/executions", summary="Create orchestrator execution (RESTful)")
async def create_orchestrator_execution(
    orchestrator_id: UUID,
    request: ExecutionCreate,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Create a new orchestrator execution (RESTful endpoint)"""
    try:
        # Get orchestrator configuration
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator not found: {orchestrator_id}")

        # Create execution record
        execution = OrchestratorExecution(
            orchestrator_id=orchestrator_id,
            execution_name=request.execution_name,
            execution_type=request.execution_type,
            input_data=request.input_data,
            status="running",
            created_by=current_user.username,
        )

        db.add(execution)
        await db.commit()
        await db.refresh(execution)

        # Execute orchestrator synchronously
        try:
            execution_config = {
                "execution_type": request.execution_type,
                "input_data": request.input_data,
                "user_context": current_user.username,  # Add user context for generator access
            }

            results = await pyrit_orchestrator_service.execute_orchestrator(str(orchestrator_id), execution_config)

            # Update execution with results
            execution.status = "completed"
            execution.results = results
            execution.execution_summary = results.get("execution_summary", {})
            execution.completed_at = datetime.utcnow()

            await db.commit()

            logger.info(f"User {current_user.username} executed orchestrator {config.name}")
            logger.info(f"Execution results keys: {list(results.keys()) if results else 'None'}")
            logger.info(f"Has execution_summary: {'execution_summary' in results if results else False}")
            logger.info(f"Has prompt_request_responses: {'prompt_request_responses' in results if results else False}")

        except Exception as exec_error:
            # Update execution with error
            execution.status = "failed"
            execution.results = {"error": str(exec_error)}
            execution.completed_at = datetime.utcnow()
            await db.commit()
            raise

        # Calculate expected operations (EXACTLY like original)
        expected_ops = (
            len(request.input_data.get("prompt_list", []))
            if request.execution_type == "prompt_list"
            else request.input_data.get("sample_size", 1) if request.execution_type == "dataset" else 1
        )

        # For completed executions, return the full results directly (EXACTLY like original)
        # This provides better UX for synchronous operations like dataset testing
        if execution.status == "completed" and execution.results:
            # Log what we're about to return
            logger.info(f"Returning completed execution with results. Keys: {list(execution.results.keys())}")

            # Return the actual execution results for immediate use
            response_data = {
                "execution_id": execution.id,
                "status": execution.status,
                "orchestrator_id": orchestrator_id,
                "orchestrator_type": config.orchestrator_type,
                "execution_name": execution.execution_name,
                "started_at": execution.started_at,
                "completed_at": execution.completed_at,
                "expected_operations": expected_ops,
                "progress": {"completed": expected_ops, "total": expected_ops, "current_operation": "Completed"},
            }

            # Spread the execution results if they exist
            if execution.results:
                response_data.update(execution.results)

            logger.info(f"Final response keys: {list(response_data.keys())}")
            return response_data
        else:
            # For async/long-running executions, return tracking info
            return OrchestratorExecuteResponse(
                execution_id=execution.id,
                status=execution.status,
                orchestrator_id=orchestrator_id,
                orchestrator_type=config.orchestrator_type,
                execution_name=execution.execution_name,
                started_at=execution.started_at,
                expected_operations=expected_ops,
                progress={
                    "completed": expected_ops if execution.status == "completed" else 0,
                    "total": expected_ops,
                    "current_operation": "Completed" if execution.status == "completed" else "Processing...",
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating orchestrator execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create execution: {str(e)}")


@router.get("/executions", summary="List all orchestrator executions")
async def list_all_orchestrator_executions(
    db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """List all executions across all orchestrators"""
    try:
        # Get all executions with their orchestrator info
        stmt = select(OrchestratorExecution).order_by(OrchestratorExecution.started_at.desc())
        result = await db.execute(stmt)
        executions = result.scalars().all()

        # Get orchestrator configurations for names
        stmt = select(OrchestratorConfiguration)
        result = await db.execute(stmt)
        orchestrators = {str(o.id): o for o in result.scalars().all()}

        execution_list = []
        for execution in executions:
            orchestrator = orchestrators.get(str(execution.orchestrator_id))

            # Check if execution has scorer results
            has_scorer_results = False
            if execution.results and isinstance(execution.results, dict):
                scores = execution.results.get("scores", [])
                has_scorer_results = len(scores) > 0

            execution_data = {
                "id": str(execution.id),
                "orchestrator_id": str(execution.orchestrator_id),
                "name": orchestrator.name if orchestrator else "Unknown",
                "orchestrator_type": orchestrator.orchestrator_type if orchestrator else "Unknown",
                "execution_type": execution.execution_type,
                "execution_name": execution.execution_name,
                "status": execution.status,
                "created_at": execution.started_at.isoformat() if execution.started_at else None,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "has_scorer_results": has_scorer_results,
                "created_by": execution.created_by,
            }
            execution_list.append(execution_data)

        return {"executions": execution_list, "total": len(execution_list)}

    except Exception as e:
        logger.error(f"Error listing all orchestrator executions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")


@router.get(
    "/{orchestrator_id}/executions",
    response_model=ExecutionListResponse,
    summary="List orchestrator executions (RESTful)",
)
async def list_orchestrator_executions(
    orchestrator_id: UUID, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """List all executions for an orchestrator (RESTful endpoint)"""
    try:
        # Verify orchestrator exists
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator not found: {orchestrator_id}")

        # Get executions
        stmt = (
            select(OrchestratorExecution)
            .where(OrchestratorExecution.orchestrator_id == orchestrator_id)
            .order_by(OrchestratorExecution.started_at.desc())
        )

        result = await db.execute(stmt)
        executions = result.scalars().all()

        # Build response with HATEOAS links
        base_url = f"/api/v1/orchestrators/{orchestrator_id}"
        execution_responses = []

        for execution in executions:
            links = {
                "self": f"{base_url}/executions/{execution.id}",
                "orchestrator": f"/api/v1/orchestrators/{orchestrator_id}",
                "results": f"{base_url}/executions/{execution.id}/results",
            }

            execution_responses.append(
                ExecutionResponse(
                    id=execution.id,
                    orchestrator_id=orchestrator_id,
                    execution_type=execution.execution_type,
                    execution_name=execution.execution_name,
                    status=execution.status,
                    created_at=execution.started_at,
                    started_at=execution.started_at,
                    completed_at=execution.completed_at,
                    input_data=execution.input_data,
                    results=execution.results,
                    execution_summary=execution.execution_summary,
                    created_by=execution.created_by,
                    links=links,
                )
            )

        list_links = {
            "self": f"{base_url}/executions",
            "orchestrator": f"/api/v1/orchestrators/{orchestrator_id}",
            "create": f"{base_url}/executions",
        }

        return ExecutionListResponse(executions=execution_responses, total=len(execution_responses), _links=list_links)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing orchestrator executions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")


@router.get(
    "/{orchestrator_id}/executions/{execution_id}",
    response_model=ExecutionResponse,
    summary="Get orchestrator execution (RESTful)",
)
async def get_orchestrator_execution(
    orchestrator_id: UUID,
    execution_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Get a specific orchestrator execution (RESTful endpoint)"""
    try:
        # Verify orchestrator exists
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator not found: {orchestrator_id}")

        # Get execution
        stmt = select(OrchestratorExecution).where(
            OrchestratorExecution.id == execution_id, OrchestratorExecution.orchestrator_id == orchestrator_id
        )
        result = await db.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

        # Create HATEOAS links
        base_url = f"/api/v1/orchestrators/{orchestrator_id}"
        links = {
            "self": f"{base_url}/executions/{execution.id}",
            "orchestrator": f"/api/v1/orchestrators/{orchestrator_id}",
            "results": f"{base_url}/executions/{execution.id}/results",
            "list": f"{base_url}/executions",
        }

        return ExecutionResponse(
            id=execution.id,
            orchestrator_id=orchestrator_id,
            execution_type=execution.execution_type,
            execution_name=execution.execution_name,
            status=execution.status,
            created_at=execution.started_at,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            input_data=execution.input_data,
            results=execution.results,
            execution_summary=execution.execution_summary,
            created_by=execution.created_by,
            links=links,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting orchestrator execution: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution: {str(e)}")


@router.get(
    "/{orchestrator_id}/executions/{execution_id}/results",
    response_model=OrchestratorResultsResponse,
    summary="Get execution results (RESTful)",
)
async def get_execution_results_restful(
    orchestrator_id: UUID,
    execution_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Get results from orchestrator execution (RESTful endpoint - mirrors original exactly)"""
    try:
        # Get execution (exactly like original - no orchestrator_id validation)
        stmt = select(OrchestratorExecution).where(OrchestratorExecution.id == execution_id)
        result = await db.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

        # Get orchestrator configuration (exactly like original)
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == execution.orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator configuration not found")

        # Same status check as original (400 not 409)
        if execution.status != "completed":
            raise HTTPException(status_code=400, detail=f"Execution not completed. Status: {execution.status}")

        # Return exactly the same format as original
        return OrchestratorResultsResponse(
            execution_id=execution.id,
            status=execution.status,
            orchestrator_name=config.name,
            orchestrator_type=config.orchestrator_type,
            execution_summary=execution.execution_summary or {},
            prompt_request_responses=execution.results.get("prompt_request_responses", []),
            scores=execution.results.get("scores", []),
            memory_export=execution.results.get("memory_export", {}),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution results: {str(e)}")


@router.delete("/{orchestrator_id}", summary="Delete orchestrator configuration")
async def delete_orchestrator_configuration(
    orchestrator_id: UUID, db: AsyncSession = Depends(get_session), current_user=Depends(get_current_user)
):
    """Delete orchestrator configuration and clean up instance"""
    try:
        stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == orchestrator_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"Orchestrator not found: {orchestrator_id}")

        # Clean up PyRIT instance
        pyrit_orchestrator_service.dispose_orchestrator(str(orchestrator_id))

        # Delete from database
        await db.delete(config)
        await db.commit()

        logger.info(f"User {current_user.username} deleted orchestrator: {config.name}")

        return {"message": f"Orchestrator '{config.name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting orchestrator: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete orchestrator: {str(e)}")
