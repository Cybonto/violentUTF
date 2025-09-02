# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Secure error handling module to prevent information disclosure

SECURITY: Sanitizes error messages and prevents internal system information leakage

"""
import logging
import re
import traceback
import uuid
from typing import Any, Dict, Optional, Self

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Sensitive patterns that should never be exposed in error messages
SENSITIVE_PATTERNS = [
    r"password[^a-zA-Z]",
    r"secret[^a-zA-Z]",
    r"token[^a-zA-Z]",
    r"key[^a-zA-Z]",
    r"auth[^a-zA-Z]",
    r"api[_-]?key",
    r"bearer\s+[a-zA-Z0-9._-]+",
    r"postgresql://[^/]+/[^?]+",
    r"mysql://[^/]+/[^?]+",
    r"mongodb://[^/]+/[^?]+",
    r"/Users/[^/]+",
    r"/home/[^/]+",
    r"C:\\Users\\[^\\]+",
    r'file:///[^"\']+',
    r"jwt\.decode",
    r"SECRET_KEY",
    r"APISIX_ADMIN_KEY",
    r"127\.0\.0\.1",
    r"localhost",
    r"0\.0\.0\.0",
    r"192\.168\.\d+\.\d+",
    r"10\.\d+\.\d+\.\d+",
    r"172\.\d+\.\d+\.\d+",
]


class SecurityError(HTTPException):
    """Security-related error that requires special handling."""

    def __init__(self: "Self", detail: str, status_code: int = status.HTTP_403_FORBIDDEN) -> None:
        """Initialize instance."""
        super().__init__(status_code=status_code, detail=detail)


class RateLimitError(HTTPException):
    """Rate limit exceeded error."""

    def __init__(self: "Self", detail: str = "Rate limit exceeded") -> None:
        """Initialize instance."""
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class ValidationSecurityError(HTTPException):
    """Validation error with security implications."""

    def __init__(self: "Self", detail: str) -> None:
        """Initialize instance."""
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


def sanitize_error_message(message: str) -> str:
    """Sanitize error message to remove sensitive information

    Args:
        message: Original error message

    Returns:
        Sanitized error message safe for client exposure

    """
    if not message:

        return "An error occurred"

    # Convert to string and limit length
    message = str(message)[:1000]

    # Remove sensitive patterns
    sanitized = message
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

    # Remove file paths
    sanitized = re.sub(r"/[a-zA-Z0-9/_.-]+\.py", "[FILE]", sanitized)
    sanitized = re.sub(r"C:\\[a-zA-Z0-9\\._-]+\.py", "[FILE]", sanitized)

    # Remove line numbers and specific code references
    sanitized = re.sub(r"line \d+", "line [NUM]", sanitized)
    sanitized = re.sub(r"at 0x[a-fA-F0-9]+", "at [ADDR]", sanitized)

    # Remove stack trace information
    sanitized = re.sub(r'File "[^"]+", line \d+, in [^\n]+', "[STACK_TRACE]", sanitized)

    # If message becomes too generic after sanitization, provide a safer default
    if sanitized in ["[REDACTED]", "", "[FILE]", "[STACK_TRACE]"]:
        return "Invalid request parameters"

    return sanitized


def create_error_response(
    error: Exception,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail: Optional[str] = None,
    include_error_id: bool = True,
) -> Dict[str, Any]:
    """Create secure error response with sanitized information

    Args:
        error: Original exception
        status_code: HTTP status code
        detail: Custom error detail (will be sanitized)
        include_error_id: Whether to include error tracking ID

    Returns:
        Sanitized error response dictionary

    """
    # Generate error ID for tracking
    error_id = str(uuid.uuid4())[:8] if include_error_id else None

    # Log the full error for debugging (server-side only)
    logger.error(
        "Error %s: %s: %s",
        error_id,
        type(error).__name__,
        str(error),
        exc_info=True if logger.isEnabledFor(logging.DEBUG) else False,
    )

    # Determine sanitized error message
    if detail:
        message = sanitize_error_message(detail)
    else:
        message = sanitize_error_message(str(error))

    # Create response based on error type and status code
    response = {"error": True, "message": message, "status_code": status_code}

    # Add error ID for tracking (but not sensitive info)
    if error_id:
        response["error_id"] = error_id

    # Add error type for client handling (but sanitized)
    error_type = type(error).__name__
    safe_error_types = [
        "ValidationError",
        "ValueError",
        "KeyError",
        "TypeError",
        "HTTPException",
        "SecurityError",
        "RateLimitError",
    ]

    if error_type in safe_error_types:
        response["error_type"] = error_type
    else:
        response["error_type"] = "ServerError"

    return response


def handle_validation_error(error: ValidationError) -> Dict[str, Any]:
    """Handle Pydantic validation errors securely

    Args:
        error: Pydantic ValidationError

    Returns:
        Sanitized validation error response

    """
    # Extract validation errors but sanitize them

    errors = []
    for err in error.errors():
        field = err.get("loc", ["unknown"])[-1]  # Get last part of field path
        message = sanitize_error_message(err.get("msg", "Invalid value"))

        # Don't expose internal field paths
        if isinstance(field, str) and len(field) <= 100:
            safe_field = re.sub(r"[^a-zA-Z0-9_.-]", "", field)
        else:
            safe_field = "field"

        errors.append({"field": safe_field, "message": message})

    return {
        "error": True,
        "message": "Validation failed",
        "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "validation_errors": errors[:10],  # Limit number of errors
        "error_type": "ValidationError",
    }


async def security_error_handler(request: Request, exc: SecurityError) -> JSONResponse:
    """Handle security-related errors."""
    client_host = request.client.host if request.client else "unknown"

    logger.warning("Security error from %s: %s", client_host, exc.detail)

    response = create_error_response(
        exc,
        status_code=exc.status_code,
        detail="Access denied",  # Generic message for security
    )

    return JSONResponse(status_code=exc.status_code, content=response)


async def rate_limit_error_handler(request: Request, exc: RateLimitError) -> JSONResponse:
    """Handle rate limit errors."""
    client_host = request.client.host if request.client else "unknown"

    logger.warning("Rate limit exceeded from %s", client_host)

    response = create_error_response(
        exc,
        status_code=exc.status_code,
        detail="Rate limit exceeded. Please try again later.",
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response,
        headers={"Retry-After": "60"},  # Suggest retry after 1 minute
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    from app.core.security_logging import log_validation_failure

    # Log validation failure for security monitoring
    log_validation_failure(
        request=request,
        field=("multiple" if len(exc.errors()) > 1 else str(exc.errors()[0].get("loc", ["unknown"])[-1])),
        error=f"{len(exc.errors())} validation errors",
    )

    client_host = request.client.host if request.client else "unknown"
    logger.info("Validation error from %s: %s errors", client_host, len(exc.errors()))

    response = handle_validation_error(exc)

    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=response)


async def http_exception_handler(  # pylint: disable=unused-argument
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    # Log but don't expose details for server errors

    if exc.status_code >= 500:
        logger.error("Server error %s: %s", exc.status_code, exc.detail)
        detail = "Internal server error"
    else:
        logger.info("Client error %s: %s", exc.status_code, exc.detail)
        detail = exc.detail

    response = create_error_response(exc, status_code=exc.status_code, detail=detail)

    return JSONResponse(status_code=exc.status_code, content=response)


async def general_exception_handler(  # pylint: disable=unused-argument
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unexpected exceptions."""
    # Generate error ID for tracking
    error_id = str(uuid.uuid4())[:8]

    # Log full error details server-side
    logger.error(
        "Unhandled exception %s: %s: %s",
        error_id,
        type(exc).__name__,
        str(exc),
        exc_info=True,
    )

    # Return generic error to client
    response = {
        "error": True,
        "message": "An unexpected error occurred",
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "error_id": error_id,
        "error_type": "ServerError",
    }

    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response)


# Development mode error handler (more verbose for debugging)
async def development_exception_handler(  # pylint: disable=unused-argument
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle exceptions in development mode with more details."""
    error_id = str(uuid.uuid4())[:8]

    # Log full error
    logger.error(
        "Development exception %s: %s: %s",
        error_id,
        type(exc).__name__,
        str(exc),
        exc_info=True,
    )

    # In development, provide more details but still sanitize
    response = {
        "error": True,
        "message": sanitize_error_message(str(exc)),
        "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "error_id": error_id,
        "error_type": type(exc).__name__,
        "development_mode": True,
    }

    # Add sanitized traceback in development
    if hasattr(exc, "__traceback__"):
        tb_lines = traceback.format_tb(exc.__traceback__)
        sanitized_tb = []
        for line in tb_lines[-3:]:  # Only last 3 frames
            sanitized_line = sanitize_error_message(line.strip())
            sanitized_tb.append(sanitized_line)
        response["traceback"] = sanitized_tb

    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response)


def setup_error_handlers(app: "FastAPI", development_mode: bool = False) -> None:
    """Set up error handlers for the FastAPI application

    Args:
        app: FastAPI application instance
        development_mode: Whether to use development error handlers

    """
    # Security errors

    app.add_exception_handler(SecurityError, security_error_handler)

    # Rate limit errors
    app.add_exception_handler(RateLimitError, rate_limit_error_handler)

    # Validation errors
    app.add_exception_handler(ValidationError, validation_error_handler)

    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)

    # General exceptions
    if development_mode:
        app.add_exception_handler(Exception, development_exception_handler)
    else:
        app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Error handlers configured (development_mode=%s)", development_mode)


# Utility functions for endpoint error handling
def safe_error_response(message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> HTTPException:
    """Create safe error response for endpoints."""
    sanitized_message = sanitize_error_message(message)

    return HTTPException(status_code=status_code, detail=sanitized_message)


def authentication_error(message: str = "Authentication failed") -> SecurityError:
    """Create authentication error."""
    return SecurityError(detail=message, status_code=status.HTTP_401_UNAUTHORIZED)


def authorization_error(message: str = "Access denied") -> SecurityError:
    """Create authorization error."""
    return SecurityError(detail=message, status_code=status.HTTP_403_FORBIDDEN)


def validation_error(message: str) -> ValidationSecurityError:
    """Create validation error."""
    sanitized_message = sanitize_error_message(message)

    return ValidationSecurityError(detail=sanitized_message)
