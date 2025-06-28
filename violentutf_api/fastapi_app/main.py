"""
ViolentUTF API - FastAPI application for programmatic access to LLM red-teaming tools
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.api.routes import api_router
from app.core.logging import setup_logging
from app.db.database import init_db
from app.core.rate_limiting import limiter, custom_rate_limit_handler
from app.core.error_handling import setup_error_handlers
from app.core.security_headers import setup_security_headers, configure_cors_settings
from slowapi.errors import RateLimitExceeded

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting ViolentUTF API...")
    logger.info(f"API Title: {settings.PROJECT_NAME}")
    logger.info(f"API Version: {settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")

    # Initialize PyRIT orchestrator service
    logger.info("Initializing PyRIT orchestrator service...")
    try:
        from app.services.pyrit_orchestrator_service import pyrit_orchestrator_service

        logger.info("PyRIT orchestrator service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize PyRIT orchestrator service: {e}")
        # Don't fail the startup, just log the error

    # Initialize MCP server
    logger.info("Initializing MCP server...")
    try:
        from app.mcp import mcp_server

        await mcp_server.initialize()
        logger.info("MCP server initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
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
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

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
    logger.error(f"Failed to mount MCP server: {e}")


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


if __name__ == "__main__":
    import uvicorn

    # Secure network binding - only bind to all interfaces if explicitly allowed
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    
    # Warn if attempting to bind to all interfaces without explicit permission
    if host == "0.0.0.0" and os.getenv("ALLOW_PUBLIC_BINDING") != "true":
        logger = logging.getLogger(__name__)
        logger.warning("Attempting to bind to all interfaces without explicit permission. Defaulting to localhost.")
        host = "127.0.0.1"
    
    uvicorn.run("main:app", host=host, port=port, reload=settings.DEBUG, log_level="info")
