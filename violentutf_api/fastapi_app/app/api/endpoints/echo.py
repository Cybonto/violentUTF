"""
Echo endpoint for testing API connectivity
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class EchoRequest(BaseModel):
    """Echo request model"""

    message: str
    metadata: Optional[Dict[str, Any]] = None


class EchoResponse(BaseModel):
    """Echo response model"""

    echo: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str


@router.post("", response_model=EchoResponse)
async def echo(request: EchoRequest):
    """
    Echo endpoint for testing API connectivity.
    Returns the same message that was sent.

    Args:
        request: Echo request with message and optional metadata

    Returns:
        Echo response with the same message and metadata
    """
    from datetime import datetime

    return EchoResponse(echo=request.message, metadata=request.metadata, timestamp=datetime.utcnow().isoformat())


@router.get("/{message}")
async def echo_get(message: str):
    """
    Simple GET echo endpoint for testing.

    Args:
        message: Message to echo back

    Returns:
        Dictionary with echoed message
    """
    from datetime import datetime

    return {"echo": message, "method": "GET", "timestamp": datetime.utcnow().isoformat()}
