# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Debug endpoint for JWT validation testing
Temporarily bypasses APISIX gateway check for troubleshooting
"""

import logging
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.security import decode_token
from fastapi import APIRouter, Header
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()


class JWTDebugResponse(BaseModel):
    """Response model for JWT debug endpoint"""

    jwt_valid: bool
    jwt_secret_preview: str
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    headers_received: Dict[str, str]


@router.post("/api/v1/debug/jwt-validate", response_model=JWTDebugResponse)
async def debug_jwt_validation(
    authorization: Optional[str] = Header(None),
    x_api_gateway: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    x_real_ip: Optional[str] = Header(None),
) -> JWTDebugResponse:
    """
    Debug endpoint to test JWT validation without APISIX gateway check

    This endpoint helps troubleshoot JWT authentication issues by:
    1. Showing what headers were received
    2. Attempting to decode the JWT token
    3. Showing the JWT secret being used (preview only)
    """
    # Collect headers (convert None to empty string)
    headers_received: Dict[str, str] = {
        "authorization": (
            authorization[:50] + "..." if authorization and len(authorization) > 50 else (authorization or "")
        ),
        "x-api-gateway": x_api_gateway or "",
        "x-forwarded-for": x_forwarded_for or "",
        "x-real-ip": x_real_ip or "",
    }

    # Get JWT secret preview
    jwt_secret = settings.JWT_SECRET_KEY or settings.SECRET_KEY
    jwt_secret_preview = f"***{jwt_secret[-8:]}" if jwt_secret else "NOT SET"

    # Try to extract token
    if not authorization:
        return JWTDebugResponse(
            jwt_valid=False,
            jwt_secret_preview=jwt_secret_preview,
            error="No Authorization header provided",
            headers_received=headers_received,
        )

    # Extract bearer token
    token = None
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        return JWTDebugResponse(
            jwt_valid=False,
            jwt_secret_preview=jwt_secret_preview,
            error="Authorization header must start with 'Bearer '",
            headers_received=headers_received,
        )

    # Try to decode token
    try:
        payload = decode_token(token)
        if payload:
            return JWTDebugResponse(
                jwt_valid=True,
                jwt_secret_preview=jwt_secret_preview,
                payload=payload,
                headers_received=headers_received,
            )
        else:
            return JWTDebugResponse(
                jwt_valid=False,
                jwt_secret_preview=jwt_secret_preview,
                error="Token decoded but validation failed",
                headers_received=headers_received,
            )
    except Exception as e:
        logger.error(f"JWT decode error: {str(e)}")
        return JWTDebugResponse(
            jwt_valid=False,
            jwt_secret_preview=jwt_secret_preview,
            error=f"Decode error: {str(e)}",
            headers_received=headers_received,
        )


@router.get("/api/v1/debug/headers")
async def debug_headers(
    authorization: Optional[str] = Header(None),
    x_api_gateway: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    x_forwarded_host: Optional[str] = Header(None),
    x_real_ip: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    Debug endpoint to show all headers received by FastAPI
    This helps verify what APISIX is forwarding
    """
    return {
        "headers_received": {
            "authorization": authorization[:50] + "..." if authorization and len(authorization) > 50 else authorization,
            "x-api-gateway": x_api_gateway,
            "x-forwarded-for": x_forwarded_for,
            "x-forwarded-host": x_forwarded_host,
            "x-real-ip": x_real_ip,
        },
        "apisix_check_would_pass": x_api_gateway == "APISIX",
        "jwt_secret_configured": bool(settings.JWT_SECRET_KEY or settings.SECRET_KEY),
    }
