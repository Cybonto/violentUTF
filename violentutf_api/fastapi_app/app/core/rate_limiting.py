# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Rate limiting implementation for authentication endpoints

SECURITY: Implements rate limiting to prevent brute force attacks
"""

import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


# Rate limiter configuration
def get_client_ip(request: Request) -> str:
    """
    Get client IP for rate limiting.

    SECURITY: Uses proper forwarded headers from APISIX gateway
    """
    # Check for forwarded IP from APISIX gateway
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP (original client) from X-Forwarded-For chain
        client_ip = forwarded_for.split(",")[0].strip()
        return client_ip

    # Fallback to direct connection IP
    return get_remote_address(request)


# Create limiter instance
limiter = Limiter(key_func=get_client_ip)

# Rate limiting configurations for different endpoint types
RATE_LIMITS = {
    # Authentication endpoints (stricter limits)
    "auth_login": "5/minute",  # Login attempts: 5 per minute
    "auth_token": "10/minute",  # Token requests: 10 per minute
    "auth_refresh": "20/minute",  # Token refresh: 20 per minute
    "auth_validate": "30/minute",  # Token validation: 30 per minute
    # General API endpoints (more permissive)
    "api_general": "100/minute",  # General API calls: 100 per minute
    "api_data": "50/minute",  # Data operations: 50 per minute
}


def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom rate limit exceeded handler with security logging.
    """
    client_ip = get_client_ip(request)
    endpoint = request.url.path

    # Log security event
    from app.core.security_logging import log_rate_limit_exceeded

    log_rate_limit_exceeded(request=request, limit_type=endpoint, limit_details=str(exc.detail))

    # Log the rate limit violation for security monitoring
    logger.warning(
        f"Rate limit exceeded for IP {client_ip} on endpoint {endpoint}. "
        f"Limit: {exc.detail}, User-Agent: {request.headers.get('User-Agent', 'Unknown')}"
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": 60,  # Suggest retry after 60 seconds
        },
        headers={"Retry-After": "60"},
    )


def get_rate_limit(endpoint_type: str) -> str:
    """
    Get rate limit configuration for endpoint type.
    """
    return RATE_LIMITS.get(endpoint_type, RATE_LIMITS["api_general"])


# Rate limiting decorators for different endpoint types
def auth_rate_limit(endpoint_type: str = "auth_login"):
    """
    Rate limiting decorator for authentication endpoints.
    """
    rate_limit = get_rate_limit(endpoint_type)
    return limiter.limit(rate_limit)


def api_rate_limit(endpoint_type: str = "api_general"):
    """
    Rate limiting decorator for general API endpoints.
    """
    rate_limit = get_rate_limit(endpoint_type)
    return limiter.limit(rate_limit)
