"""
Red-teaming endpoints for PyRIT and Garak integration
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services.pyrit_integration import pyrit_service
from app.services.garak_integration import garak_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class RedTeamStatusResponse(BaseModel):
    pyrit_available: bool
    garak_available: bool
    python_version: str
    message: str

class PyRITTargetRequest(BaseModel):
    name: str
    type: str
    parameters: Dict[str, Any]

class PyRITOrchestrationRequest(BaseModel):
    target_id: str
    prompts: List[str]
    conversation_id: Optional[str] = None

class GarakScanRequest(BaseModel):
    target_config: Dict[str, Any]
    probe_module: str = "encoding"
    probe_name: str = "InjectBase64"
    scan_name: Optional[str] = None

class GarakProbesResponse(BaseModel):
    probes: List[Dict[str, Any]]
    total: int

class GarakScanResponse(BaseModel):
    scan_id: str
    status: str
    results: Dict[str, Any]

@router.get("/status", response_model=RedTeamStatusResponse, summary="Get red-teaming tools status")
async def get_redteam_status(current_user = Depends(get_current_user)):
    """Get status of PyRIT and Garak availability"""
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
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error getting red-team status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@router.post("/pyrit/target", summary="Create PyRIT target")
async def create_pyrit_target(
    request: PyRITTargetRequest,
    current_user = Depends(get_current_user)
):
    """Create a PyRIT target for red-teaming"""
    try:
        if not pyrit_service.is_available():
            raise HTTPException(status_code=503, detail="PyRIT is not available")
        
        logger.info(f"User {current_user.username} creating PyRIT target: {request.name}")
        
        # Create target configuration
        target_config = {
            "name": request.name,
            "type": request.type,
            **request.parameters
        }
        
        # Create PyRIT target
        target = await pyrit_service.create_prompt_target(target_config)
        
        # Generate a proper target ID for tracking
        import uuid
        target_id = str(uuid.uuid4())
        
        # Store target configuration for later retrieval (in-memory for now)
        # In production, this would be stored in database
        return {
            "success": True,
            "message": f"PyRIT target '{request.name}' created successfully",
            "target_type": request.type,
            "target_id": target_id
        }
        
    except Exception as e:
        logger.error(f"Error creating PyRIT target: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create target: {str(e)}")

@router.post("/pyrit/orchestrate", summary="Run PyRIT orchestration")
async def run_pyrit_orchestration(
    request: PyRITOrchestrationRequest,
    current_user = Depends(get_current_user)
):
    """Run PyRIT red-teaming orchestration"""
    try:
        if not pyrit_service.is_available():
            raise HTTPException(status_code=503, detail="PyRIT is not available")
        
        logger.info(f"User {current_user.username} running PyRIT orchestration")
        
        # In a real implementation, we'd retrieve the target by ID
        # For now, create a demo target
        target_config = {
            "type": "AI Gateway",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "base_url": "http://localhost:9080"
        }
        
        target = await pyrit_service.create_prompt_target(target_config)
        
        # Run orchestration
        results = await pyrit_service.run_red_team_orchestrator(
            target=target,
            prompts=request.prompts,
            conversation_id=request.conversation_id
        )
        
        return {
            "success": True,
            "conversation_id": request.conversation_id,
            "results": results,
            "total_prompts": len(request.prompts)
        }
        
    except Exception as e:
        logger.error(f"Error running PyRIT orchestration: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestration failed: {str(e)}")

@router.get("/garak/probes", response_model=GarakProbesResponse, summary="List Garak vulnerability probes")
async def list_garak_probes(current_user = Depends(get_current_user)):
    """List all available Garak vulnerability probes"""
    try:
        if not garak_service.is_available():
            raise HTTPException(status_code=503, detail="Garak is not available")
        
        logger.info(f"User {current_user.username} requested Garak probes list")
        
        probes = garak_service.list_available_probes()
        
        return GarakProbesResponse(
            probes=probes,
            total=len(probes)
        )
        
    except Exception as e:
        logger.error(f"Error listing Garak probes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list probes: {str(e)}")

@router.get("/garak/generators", summary="List Garak generators")
async def list_garak_generators(current_user = Depends(get_current_user)):
    """List all available Garak generators"""
    try:
        if not garak_service.is_available():
            raise HTTPException(status_code=503, detail="Garak is not available")
        
        logger.info(f"User {current_user.username} requested Garak generators list")
        
        generators = garak_service.list_available_generators()
        
        return {
            "generators": generators,
            "total": len(generators)
        }
        
    except Exception as e:
        logger.error(f"Error listing Garak generators: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list generators: {str(e)}")

@router.post("/garak/scan", response_model=GarakScanResponse, summary="Run Garak vulnerability scan")
async def run_garak_scan(
    request: GarakScanRequest,
    current_user = Depends(get_current_user)
):
    """Run Garak vulnerability scan against a target"""
    try:
        if not garak_service.is_available():
            raise HTTPException(status_code=503, detail="Garak is not available")
        
        logger.info(f"User {current_user.username} starting Garak scan")
        
        # Prepare probe configuration
        probe_config = {
            "module": request.probe_module,
            "name": request.probe_name
        }
        
        # Run the scan
        scan_result = await garak_service.run_vulnerability_scan(
            target_config=request.target_config,
            probe_config=probe_config
        )
        
        return GarakScanResponse(
            scan_id=scan_result["scan_id"],
            status=scan_result["status"],
            results=scan_result
        )
        
    except Exception as e:
        logger.error(f"Error running Garak scan: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@router.get("/garak/scan/{scan_id}", summary="Get Garak scan results")
async def get_garak_scan_results(
    scan_id: str,
    current_user = Depends(get_current_user)
):
    """Get results for a specific Garak scan"""
    try:
        if not garak_service.is_available():
            raise HTTPException(status_code=503, detail="Garak is not available")
        
        logger.info(f"User {current_user.username} requested scan results for: {scan_id}")
        
        results = garak_service.get_scan_results(scan_id)
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scan results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")