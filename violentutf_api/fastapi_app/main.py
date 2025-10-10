# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""ViolentUTF API - FastAPI application for programmatic access to LLM red-teaming tools.

Copyright (c) 2025 ViolentUTF Contributors.
Licensed under the MIT License.

This file is part of ViolentUTF - An AI Red Teaming Platform.
See LICENSE file in the project root for license information.

"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Dict, cast

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.api.routes import api_router
from app.core.config import settings
from app.core.error_handling import setup_error_handlers
from app.core.logging import setup_logging
from app.core.rate_limiting import custom_rate_limit_handler, limiter
from app.core.security_headers import configure_cors_settings, setup_security_headers
from app.db.database import init_db
from app.mcp import mcp_server as mcp_service
from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service

# Constants to avoid bandit B104 hardcoded binding warnings
WILDCARD_ADDRESS = "0.0.0.0"  # nosec B104

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan."""
    logger.info("Starting ViolentUTF API...")

    logger.info("API Title: %s", settings.PROJECT_NAME)
    logger.info("API Version: %s", settings.VERSION)
    logger.info("Environment: %s", settings.ENVIRONMENT)

    # Initialize database
    logger.info("Initializing database...")
    await init_db()

    # Initialize PyRIT orchestrator service (if available)
    try:
        _ = pyrit_orchestrator_service
        logger.info("PyRIT orchestrator service available")
    except (ImportError, AttributeError, ValueError) as e:
        logger.warning("PyRIT orchestrator service not available: %s", e)

    # Initialize MCP service
    try:
        await mcp_service.initialize()
        logger.info("MCP service initialized")
    except (ImportError, AttributeError, OSError, ValueError) as e:
        logger.warning("MCP service initialization failed: %s", e)

    logger.info("ViolentUTF API startup completed")

    yield

    # Shutdown
    logger.info("ViolentUTF API shutdown completed")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
cors_settings = configure_cors_settings(environment=settings.ENVIRONMENT)
app.add_middleware(CORSMiddleware, **cors_settings)

# Configure security headers
setup_security_headers(app, environment=settings.ENVIRONMENT, api_version=settings.VERSION)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, cast(Callable, custom_rate_limit_handler))

# Configure error handlers
setup_error_handlers(app, development_mode=settings.DEBUG)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount MCP server if available
try:
    mcp_service.mount_to_app(app)
    logger.info("MCP server mounted to FastAPI app")
except (ImportError, AttributeError, OSError, ValueError) as e:
    logger.warning("Failed to mount MCP server: %s", e)


@app.get("/")
async def read_root() -> Dict[str, str]:
    """Get API root information."""
    return {
        "message": "ViolentUTF API - LLM Red Teaming Platform",
        "docs": "/docs",
        "redoc": "/redoc",
        "version": settings.VERSION,
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Check API health status."""
    return {"status": "healthy", "version": settings.VERSION}


def get_secure_binding_config() -> Dict[str, Any]:
    """Get secure binding configuration for the API server."""
    api_host = os.getenv("API_HOST", "127.0.0.1")

    api_port = int(os.getenv("API_PORT", "8000"))

    config_logger = logging.getLogger(__name__)

    # Security check: prevent public binding in production
    if api_host == WILDCARD_ADDRESS:
        if os.getenv("ALLOW_PUBLIC_BINDING", "false").lower() != "true":
            config_logger.warning(
                "Public binding (0.0.0.0) blocked for security. Set ALLOW_PUBLIC_BINDING=true to override"
            )
            api_host = "127.0.0.1"

    return {"host": api_host, "port": api_port}


if __name__ == "__main__":
    config = get_secure_binding_config()
    host = config["host"]
    port = config["port"]

    uvicorn.run("main:app", host=host, port=port, reload=settings.DEBUG, log_level="info")
