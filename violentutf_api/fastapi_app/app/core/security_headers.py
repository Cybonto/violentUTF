# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Security headers middleware and configuration.

SECURITY: Implements comprehensive security headers to protect against common web vulnerabilities
"""

import logging
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Protects against XSS, clickjacking, MIME sniffing, and other attacks
    """

    def __init__(self: "SecurityHeadersMiddleware", app: Any, environment: str = "production") -> None:
        """Initialize the instance."""
        super().__init__(app)
        self.environment = environment.lower()
        self.headers = self._get_security_headers()

    def _get_security_headers(self: "SecurityHeadersMiddleware") -> Dict[str, str]:
        """Generate security headers based on environment."""
        # Base security headers for all environments.
        headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection in browsers
            "X-XSS-Protection": "1; mode=block",
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Control referrer information
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Prevent browsers from performing DNS prefetching
            "X-DNS-Prefetch-Control": "off",
            # Disable Adobe Flash and PDF handlers
            "X-Permitted-Cross-Domain-Policies": "none",
            # Control download behavior
            "X-Download-Options": "noopen",
            # Prevent content type sniffing for downloads
            "X-Content-Type-Options": "nosniff",
        }

        # Content Security Policy (CSP)
        if self.environment == "production":
            # Strict CSP for production
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Note: unsafe-* may be needed for FastAPI docs
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self' https:",
                "frame-ancestors 'none'",
                "form-action 'self'",
                "base-uri 'self'",
                "object-src 'none'",
                "media-src 'self'",
                "worker-src 'self'",
                "child-src 'self'",
                "manifest-src 'self'",
            ]
            headers["Content-Security-Policy"] = "; ".join(csp_directives)

            # HTTP Strict Transport Security (HSTS) - only in production with HTTPS
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        else:
            # More relaxed CSP for development
            csp_directives = [
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https: http:",
                "font-src 'self' data:",
                "connect-src 'self' https: http: ws: wss:",
                "frame-ancestors 'none'",
                "form-action 'self'",
                "base-uri 'self'",
                "object-src 'none'",
            ]
            headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Permissions Policy (formerly Feature Policy)
        permissions_directives = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
            "usb=()",
            "payment=()",
            "encrypted-media=()",
            "fullscreen=(self)",
            "display-capture=()",
        ]
        headers["Permissions-Policy"] = ", ".join(permissions_directives)

        return headers

    async def dispatch(self: "SecurityHeadersMiddleware", request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Add all security headers
        for header_name, header_value in self.headers.items():
            response.headers[header_name] = header_value

        # Add security-related information to logs (without exposing in response)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Security headers added to {request.method} {request.url.path}")

        return response


def configure_cors_settings(environment: str = "production") -> Dict:
    """
    Configure CORS settings based on environment.

    Args:
        environment: Environment name (production, development, testing)

    Returns:
        Dictionary of CORS configuration settings
    """
    if environment.lower() == "production":
        # Strict CORS for production
        return {
            "allow_origins": [
                "https://localhost:8501",  # Streamlit HTTPS
                "https://127.0.0.1:8501",
                "https://localhost:9080",  # APISIX Gateway HTTPS
                "https://127.0.0.1:9080",
            ],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "Accept",
                "X-API-Key",
                "X-API-Gateway",  # APISIX gateway header
            ],
            "expose_headers": ["X-Rate-Limit-Limit", "X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"],
            "max_age": 3600,  # Cache preflight responses for 1 hour
        }
    else:
        # More permissive CORS for development
        return {
            "allow_origins": [
                "http://localhost:8501",  # Streamlit HTTP
                "https://localhost:8501",  # Streamlit HTTPS
                "http://127.0.0.1:8501",
                "https://127.0.0.1:8501",
                "http://localhost:9080",  # APISIX Gateway HTTP
                "https://localhost:9080",  # APISIX Gateway HTTPS
                "http://127.0.0.1:9080",
                "https://127.0.0.1:9080",
                "http://localhost:3000",  # React development
                "http://127.0.0.1:3000",
            ],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
            "expose_headers": ["X-Rate-Limit-Limit", "X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"],
            "max_age": 86400,  # Cache preflight responses for 24 hours in dev
        }


class APISecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Additional API-specific security headers middleware.

    Adds headers specific to API security concerns
    """

    def __init__(self: "APISecurityHeadersMiddleware", app: Any, api_version: str = "1.0") -> None:
        """Initialize the instance."""
        super().__init__(app)
        self.api_version = api_version

    async def dispatch(self: "APISecurityHeadersMiddleware", request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # API-specific headers
        response.headers["X-API-Version"] = self.api_version
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet, noimageindex"

        # Security headers for API responses
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        # Add CORS headers manually for OPTIONS requests if needed
        if request.method == "OPTIONS":
            response.headers["Access-Control-Max-Age"] = "86400"

        return response


def setup_security_headers(app, environment: str = "production", api_version: str = "1.0") -> None:
    """
    Setup all security headers middleware for the FastAPI application.

    Args:
        app: FastAPI application instance
        environment: Environment name (production, development, testing)
        api_version: API version string
    """
    # Add security headers middleware.
    app.add_middleware(SecurityHeadersMiddleware, environment=environment)

    # Add API-specific security headers
    app.add_middleware(APISecurityHeadersMiddleware, api_version=api_version)

    logger.info(f"Security headers configured for {environment} environment")


def get_csp_nonce() -> str:
    """
    Generate a cryptographically secure nonce for CSP.

    Useful for inline scripts/styles when needed
    """
    import base64
    import secrets

    # Generate 16 bytes of random data and base64 encode
    nonce_bytes = secrets.token_bytes(16)
    nonce = base64.b64encode(nonce_bytes).decode("ascii")

    return nonce


def validate_security_headers(response_headers: Dict[str, str]) -> Dict[str, bool]:
    """
    Validate that required security headers are present.

    Useful for testing and monitoring

    Args:
        response_headers: Dictionary of response headers

    Returns:
        Dictionary indicating which security headers are present
    """
    required_headers = [
        "X-Content-Type-Options",
        "X-XSS-Protection",
        "X-Frame-Options",
        "Referrer-Policy",
        "Content-Security-Policy",
        "Permissions-Policy",
    ]

    validation_results = {}
    for header in required_headers:
        validation_results[header] = header in response_headers

    # Check for HSTS in production-like headers
    validation_results["Strict-Transport-Security"] = "Strict-Transport-Security" in response_headers

    return validation_results


# Security header templates for different response types
SECURITY_HEADER_TEMPLATES = {
    "json_api": {
        "Content-Type": "application/json",
        "Cache-Control": "no-store, no-cache, must-revalidate, private",
        "Pragma": "no-cache",
    },
    "html_page": {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
    },
    "static_asset": {"Cache-Control": "public, max-age=31536000, immutable"},
}


def apply_response_headers(response: Response, template_name: str = "json_api") -> None:
    """
    Apply response-specific headers from templates.

    Args:
        response: FastAPI Response object
        template_name: Name of header template to apply
    """
    if template_name in SECURITY_HEADER_TEMPLATES:
        headers = SECURITY_HEADER_TEMPLATES[template_name]
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
