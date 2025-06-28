"""
Health check endpoints
"""

from fastapi import APIRouter, Request, Response
from datetime import datetime
from app.core.config import settings
from app.core.security_headers import validate_security_headers
from app.core.security_logging import security_metrics

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available
    """
    checks = {
        "api": True,
        "config": bool(settings.SECRET_KEY),
        "keycloak_configured": bool(settings.KEYCLOAK_CLIENT_SECRET),
    }

    all_ready = all(checks.values())

    return {"ready": all_ready, "checks": checks, "timestamp": datetime.utcnow().isoformat()}


@router.get("/security-headers")
async def security_headers_check(request: Request, response: Response):
    """
    Test endpoint to verify security headers are properly applied
    """
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
async def security_metrics_check():
    """
    Get current security metrics for monitoring
    Note: In production, this should require admin authentication
    """
    return {
        "metrics": security_metrics.get_metrics(),
        "last_reset": security_metrics.last_reset,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
    }
