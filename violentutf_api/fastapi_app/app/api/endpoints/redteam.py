# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Red-teaming endpoints for PyRIT and Garak integration"""
import logging
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.models.auth import User
from app.services.garak_integration import garak_service
from app.services.pyrit_integration import pyrit_service, run_red_team_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models for request/response
class RedTeamStatusResponse(BaseModel):
    """RedTeamStatusResponse class."""

    pyrit_available: bool

    garak_available: bool
    python_version: str
    message: str


class PyRITTargetRequest(BaseModel):
    """PyRITTargetRequest class."""

    name: str

    type: str
    parameters: Dict[str, Any]


class PyRITOrchestrationRequest(BaseModel):
    """PyRITOrchestrationRequest class."""

    target_id: str

    prompts: List[str]
    conversation_id: Optional[str] = None


class GarakScanRequest(BaseModel):
    """GarakScanRequest class."""

    target_config: Dict[str, Any]

    probe_module: str = "encoding"
    probe_name: str = "InjectBase64"
    scan_name: Optional[str] = None


class GarakProbesResponse(BaseModel):
    """GarakProbesResponse class."""

    probes: List[Dict[str, Any]]

    total: int


class GarakScanResponse(BaseModel):
    """GarakScanResponse class."""

    scan_id: str

    status: str
    results: Dict[str, Any]


@router.get(
    "/status",
    response_model=RedTeamStatusResponse,
    summary="Get red-teaming tools status",
)
async def get_redteam_status(
    current_user: User = Depends(get_current_user),
) -> RedTeamStatusResponse:
    """Get status of PyRIT and Garak availability."""
    try:

        import sys

        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        pyrit_available = pyrit_service.is_available()
        garak_available = garak_service.is_available()

        if pyrit_available and garak_available:
            message = "Both PyRIT and Garak are available and ready for red-teaming operations"
        elif pyrit_available:
            message = "PyRIT is available. Garak is not available."
        elif garak_available:
            message = "Garak is available. PyRIT is not available."
        else:
            message = "Neither PyRIT nor Garak are available. Check installation."

        return RedTeamStatusResponse(
            pyrit_available=pyrit_available,
            garak_available=garak_available,
            python_version=python_version,
            message=message,
        )

    except Exception as e:
        logger.error("Error getting red-team status: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}") from e


@router.post("/pyrit/target", summary="Create PyRIT target")
async def create_pyrit_target(
    request: PyRITTargetRequest, current_user: User = Depends(get_current_user)
) -> Optional[Dict[str, Any]]:
    """Create a PyRIT target for red-teaming."""
    try:

        if not pyrit_service.is_available():
            raise HTTPException(status_code=503, detail="PyRIT is not available")

        logger.info("User %s creating PyRIT target: %s", current_user.username, request.name)

        # Create target configuration
        target_config = {
            "name": request.name,
            "type": request.type,
            **request.parameters,
        }

        # Create PyRIT target
        target = await pyrit_service.create_prompt_target(target_config)

        # Validate target was created successfully
        if not target:
            raise HTTPException(status_code=500, detail="Failed to create PyRIT target")

        # Generate a proper target ID for tracking
        import uuid

        target_id = str(uuid.uuid4())

        # Store target configuration for later retrieval (in-memory for now)
        # In production, this would be stored in database
        return {
            "success": True,
            "message": f"PyRIT target '{request.name}' created successfully",
            "target_type": request.type,
            "target_id": target_id,
        }

    except Exception as e:
        logger.error("Error creating PyRIT target: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to create target: {str(e)}") from e


@router.post("/pyrit/orchestrate", summary="Run PyRIT orchestration")
async def run_pyrit_orchestration(
    request: PyRITOrchestrationRequest, current_user: User = Depends(get_current_user)
) -> Optional[Dict[str, Any]]:
    """Run PyRIT red-teaming orchestration."""
    try:

        if not pyrit_service.is_available():
            raise HTTPException(status_code=503, detail="PyRIT is not available")

        logger.info("User %s running PyRIT orchestration", current_user.username)

        # In a real implementation, we'd retrieve the target by ID
        # For now, create a demo target
        target_config = {
            "type": "AI Gateway",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "base_url": "http://localhost:9080",
        }

        target = await pyrit_service.create_prompt_target(cast(Dict[str, object], target_config))

        # Run orchestration
        results = await run_red_team_orchestrator(
            target=target,
            prompts=request.prompts,
            conversation_id=request.conversation_id,
        )

        return {
            "success": True,
            "conversation_id": request.conversation_id,
            "results": results,
            "total_prompts": len(request.prompts),
        }

    except Exception as e:
        logger.error("Error running PyRIT orchestration: %s", e)
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}") from e


@router.get(
    "/garak/probes",
    response_model=GarakProbesResponse,
    summary="List Garak vulnerability probes",
)
async def list_garak_probes(
    current_user: User = Depends(get_current_user),
) -> GarakProbesResponse:
    """List all available Garak vulnerability probes."""
    try:

        if not garak_service.is_available():
            raise HTTPException(status_code=503, detail="Garak is not available")

        logger.info("User %s requested Garak probes list", current_user.username)

        probes = garak_service.list_available_probes()

        return GarakProbesResponse(probes=probes, total=len(probes))

    except Exception as e:
        logger.error("Error listing Garak probes: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list probes: {str(e)}") from e


@router.get("/garak/generators", summary="List Garak generators")
async def list_garak_generators(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List all available Garak generators."""
    try:

        if not garak_service.is_available():
            raise HTTPException(status_code=503, detail="Garak is not available")

        logger.info("User %s requested Garak generators list", current_user.username)

        generators = garak_service.list_available_generators()

        return {"generators": generators, "total": len(generators)}

    except Exception as e:
        logger.error("Error listing Garak generators: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to list generators: {str(e)}") from e


@router.post(
    "/garak/scan",
    response_model=GarakScanResponse,
    summary="Run Garak vulnerability scan",
)
async def run_garak_scan(
    request: GarakScanRequest, current_user: User = Depends(get_current_user)
) -> GarakScanResponse:
    """Run Garak vulnerability scan against a target."""
    try:

        if not garak_service.is_available():
            raise HTTPException(status_code=503, detail="Garak is not available")

        logger.info("User %s starting Garak scan", current_user.username)

        # Prepare probe configuration
        probe_config = {"module": request.probe_module, "name": request.probe_name}

        # Run the scan
        scan_result = await garak_service.run_vulnerability_scan(
            target_config=request.target_config, probe_config=probe_config
        )

        return GarakScanResponse(
            scan_id=scan_result["scan_id"],
            status=scan_result["status"],
            results=scan_result,
        )

    except Exception as e:
        logger.error("Error running Garak scan: %s", e)
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}") from e


@router.get("/garak/scan/{scan_id}", summary="Get Garak scan results")
async def get_garak_scan_results(scan_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get results for a specific Garak scan."""
    try:

        if not garak_service.is_available():
            raise HTTPException(status_code=503, detail="Garak is not available")

        logger.info("User %s requested scan results for: %s", current_user.username, scan_id)

        results = garak_service.get_scan_results(scan_id)  # pylint: disable=assignment-from-none

        if not results:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting scan results: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}") from e
