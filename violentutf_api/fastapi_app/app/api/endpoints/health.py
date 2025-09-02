# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Health module."""

from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.security_logging import security_metrics
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check basic health endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check - verifies all dependencies are available"""
    checks = {
        "api": True,
        "config": bool(settings.SECRET_KEY),
        "keycloak_configured": bool(settings.KEYCLOAK_CLIENT_SECRET),
    }

    all_ready = all(checks.values())

    return {
        "ready": all_ready,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/security-headers")
async def test_security_headers() -> dict[str, str]:
    """Test endpoint to verify security headers are properly applied"""
    # This endpoint will automatically get security headers applied by middleware

    # We can validate them here for testing purposes

    return {
        "status": "security headers applied",
        "environment": settings.ENVIRONMENT,
        "endpoint": "/api/v1/health/security-headers",
        "timestamp": datetime.utcnow().isoformat(),
        "note": "Check response headers to verify security headers are present",
    }


@router.get("/security-metrics")
async def get_security_metrics() -> dict[str, Any]:
    """Get current security metrics for monitoring

    Note: In production, this should require admin authentication
    """
    return {
        "metrics": security_metrics.get_metrics(),
        "last_reset": security_metrics.last_reset,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
    }
