# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
ViolentUTF API - FastAPI application for programmatic access to LLM red-teaming tools
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Callable, cast

from app.api.routes import api_router
from app.core.config import settings
from app.core.error_handling import setup_error_handlers
from app.core.logging import setup_logging
from app.core.rate_limiting import custom_rate_limit_handler, limiter
from app.core.security_headers import configure_cors_settings, setup_security_headers
from app.db.database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Constants to avoid bandit B104 hardcoded binding warnings
WILDCARD_ADDRESS = "0.0.0.0"  # nosec B104


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting ViolentUTF API...")
    logger.info("API Title: %s", settings.PROJECT_NAME)
    logger.info("API Version: %s", settings.VERSION)
    logger.info("Environment: %s", settings.ENVIRONMENT)

    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Initialize PyRIT orchestrator service
    logger.info("Initializing PyRIT orchestrator service...")
    try:
        from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service  # noqa: F401

        logger.info("PyRIT orchestrator service initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize PyRIT orchestrator service: %s", e)
        # Don't fail the startup, just log the error

    # Initialize MCP server
    logger.info("Initializing MCP server...")
    try:
        from app.mcp import mcp_server

        await mcp_server.initialize()
        logger.info("MCP server initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize MCP server: %s", e)
        # Don't fail the startup, just log the error

    yield

    # Shutdown tasks can be added here
    logger.info("Shutting down ViolentUTF API...")


# Create FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure secure CORS settings
cors_settings = configure_cors_settings(environment=settings.ENVIRONMENT)
app.add_middleware(CORSMiddleware, **cors_settings)

# Setup comprehensive security headers
setup_security_headers(app, environment=settings.ENVIRONMENT, api_version=settings.VERSION)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Callable, custom_rate_limit_handler))

# Setup secure error handlers
setup_error_handlers(app, development_mode=settings.DEBUG)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount MCP server
try:
    from app.mcp import mcp_server

    mcp_server.mount_to_app(app)
    logger.info("MCP server mounted successfully")
except Exception as e:
    logger.error("Failed to mount MCP server: %s", e)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to ViolentUTF API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
        "mcp": "/mcp/sse",
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}


def get_secure_binding_config():
    """Get secure network binding configuration with enhanced security checks"""
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))

    logger = logging.getLogger(__name__)

    # Security check for public binding
    # nosec B104 - This is security validation, not binding to all interfaces
    if host == WILDCARD_ADDRESS:
        if os.getenv("ALLOW_PUBLIC_BINDING", "false").lower() != "true":
            logger.warning(
                "Attempted to bind to all interfaces (0.0.0.0) without explicit permission. "
                "Set ALLOW_PUBLIC_BINDING=true to enable. Falling back to localhost."
            )
            host = "127.0.0.1"
        else:
            logger.warning("Binding to all interfaces (0.0.0.0) - ensure firewall rules are properly configured")

    return host, port


if __name__ == "__main__":
    import uvicorn

    # Get secure network binding configuration
    host, port = get_secure_binding_config()

    uvicorn.run("main:app", host=host, port=port, reload=settings.DEBUG, log_level="info")
