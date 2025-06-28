"""OAuth Proxy for MCP Client Compatibility"""

import httpx
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
import logging
import secrets
import time
import base64
import hashlib
from urllib.parse import urlencode

from app.core.config import settings
from app.services.keycloak_verification import keycloak_verifier
from app.core.security import create_access_token
from app.core.error_handling import safe_error_response

logger = logging.getLogger(__name__)


class MCPOAuthProxy:
    """Provides OAuth proxy endpoints for MCP client compatibility"""

    def __init__(self):
        self.keycloak_verifier = keycloak_verifier
        self.router = APIRouter(prefix="/mcp/oauth")
        self.pkce_verifiers: Dict[str, str] = {}  # Store PKCE verifiers
        self._setup_routes()

    def _setup_routes(self):
        """Configure OAuth proxy routes"""
        self.router.get("/.well-known/oauth-authorization-server")(self.get_oauth_metadata)
        self.router.get("/authorize")(self.proxy_authorize)
        self.router.post("/token")(self.proxy_token_exchange)
        self.router.get("/callback")(self.handle_callback)

    async def get_oauth_metadata(self) -> JSONResponse:
        """Provide OAuth metadata for MCP clients"""
        base_url = settings.EXTERNAL_URL or "http://localhost:9080"

        metadata = {
            "issuer": f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}",
            "authorization_endpoint": f"{base_url}/mcp/oauth/authorize",
            "token_endpoint": f"{base_url}/mcp/oauth/token",
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "response_types_supported": ["code"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": ["openid", "profile", "email", "violentutf-api"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "claims_supported": ["sub", "email", "email_verified", "name", "preferred_username", "roles"],
        }

        return JSONResponse(content=metadata)

    async def proxy_authorize(
        self,
        client_id: str = Query(...),
        redirect_uri: str = Query(...),
        response_type: str = Query(...),
        scope: str = Query(...),
        state: Optional[str] = Query(None),
        code_challenge: Optional[str] = Query(None),
        code_challenge_method: Optional[str] = Query(None),
    ) -> RedirectResponse:
        """Proxy authorization request to Keycloak"""

        # Build Keycloak authorization URL
        keycloak_auth_url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/auth"

        # Store PKCE verifier if provided
        if code_challenge:
            # Generate a unique key for this auth request
            auth_key = f"{client_id}:{state or secrets.token_urlsafe(16)}"
            self.pkce_verifiers[auth_key] = code_challenge

            # Clean up old verifiers (older than 10 minutes)
            current_time = time.time()
            self.pkce_verifiers = {
                k: v
                for k, v in self.pkce_verifiers.items()
                if not hasattr(v, "_timestamp") or current_time - v._timestamp < 600
            }

        # Prepare Keycloak parameters
        params = {
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "redirect_uri": f"{settings.EXTERNAL_URL or 'http://localhost:9080'}/mcp/oauth/callback",
            "response_type": response_type,
            "scope": scope,
            "state": state,
        }

        # Add PKCE parameters if present
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = code_challenge_method or "S256"

        # Redirect to Keycloak
        redirect_url = f"{keycloak_auth_url}?{urlencode(params)}"
        return RedirectResponse(url=redirect_url)

    async def handle_callback(
        self,
        code: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        error: Optional[str] = Query(None),
        error_description: Optional[str] = Query(None),
    ) -> JSONResponse:
        """Handle OAuth callback from Keycloak"""

        if error:
            return JSONResponse(
                status_code=400,
                content={"error": error, "error_description": error_description or "Authorization failed"},
            )

        if not code:
            return JSONResponse(
                status_code=400, content={"error": "invalid_request", "error_description": "Authorization code missing"}
            )

        # Return the authorization code to the client
        # In a real implementation, this would redirect back to the MCP client
        return JSONResponse(
            content={
                "code": code,
                "state": state,
                "message": "Authorization successful. Use this code to exchange for tokens.",
            }
        )

    async def proxy_token_exchange(self, request: Request) -> JSONResponse:
        """Exchange authorization code for tokens"""

        # Parse form data
        form_data = await request.form()
        grant_type = form_data.get("grant_type")

        if grant_type == "authorization_code":
            return await self._handle_authorization_code_exchange(form_data)
        elif grant_type == "refresh_token":
            return await self._handle_refresh_token_exchange(form_data)
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "unsupported_grant_type",
                    "error_description": f"Grant type '{grant_type}' not supported",
                },
            )

    async def _handle_authorization_code_exchange(self, form_data) -> JSONResponse:
        """Handle authorization code exchange"""

        code = form_data.get("code")
        redirect_uri = form_data.get("redirect_uri")
        code_verifier = form_data.get("code_verifier")

        if not code:
            return JSONResponse(
                status_code=400, content={"error": "invalid_request", "error_description": "Code required"}
            )

        try:
            # Exchange code with Keycloak
            keycloak_token_url = (
                f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
            )

            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri
                or f"{settings.EXTERNAL_URL or 'http://localhost:9080'}/mcp/oauth/callback",
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
            }

            # Add PKCE verifier if present
            if code_verifier:
                token_data["code_verifier"] = code_verifier

            async with httpx.AsyncClient() as client:
                response = await client.post(keycloak_token_url, data=token_data)

                if response.status_code != 200:
                    logger.error(f"Keycloak token exchange failed: {response.text}")
                    return JSONResponse(status_code=response.status_code, content=response.json())

                token_response = response.json()

            # Verify the received token
            access_token = token_response.get("access_token")
            keycloak_payload = await self.keycloak_verifier.verify_token(access_token)

            if not keycloak_payload:
                return JSONResponse(
                    status_code=401,
                    content={"error": "invalid_token", "error_description": "Token verification failed"},
                )

            # Create local JWT for API access
            user_info = self.keycloak_verifier.extract_user_info(keycloak_payload)
            api_token = create_access_token(
                {"sub": user_info["username"], "email": user_info["email"], "roles": user_info["roles"]}
            )

            # Return tokens
            return JSONResponse(
                content={
                    "access_token": api_token,
                    "token_type": "Bearer",
                    "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    "refresh_token": token_response.get("refresh_token"),
                    "scope": token_response.get("scope", ""),
                }
            )

        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return JSONResponse(
                status_code=500, content={"error": "server_error", "error_description": "Token exchange failed"}
            )

    async def _handle_refresh_token_exchange(self, form_data) -> JSONResponse:
        """Handle refresh token exchange"""

        refresh_token = form_data.get("refresh_token")

        if not refresh_token:
            return JSONResponse(
                status_code=400, content={"error": "invalid_request", "error_description": "Refresh token required"}
            )

        try:
            # Exchange refresh token with Keycloak
            keycloak_token_url = (
                f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"
            )

            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.KEYCLOAK_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(keycloak_token_url, data=token_data)

                if response.status_code != 200:
                    logger.error(f"Keycloak refresh failed: {response.text}")
                    return JSONResponse(status_code=response.status_code, content=response.json())

                token_response = response.json()

            # Verify the new token
            access_token = token_response.get("access_token")
            keycloak_payload = await self.keycloak_verifier.verify_token(access_token)

            if not keycloak_payload:
                return JSONResponse(
                    status_code=401,
                    content={"error": "invalid_token", "error_description": "Token verification failed"},
                )

            # Create new local JWT
            user_info = self.keycloak_verifier.extract_user_info(keycloak_payload)
            api_token = create_access_token(
                {"sub": user_info["username"], "email": user_info["email"], "roles": user_info["roles"]}
            )

            # Return new tokens
            return JSONResponse(
                content={
                    "access_token": api_token,
                    "token_type": "Bearer",
                    "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                    "refresh_token": token_response.get("refresh_token"),
                    "scope": token_response.get("scope", ""),
                }
            )

        except Exception as e:
            logger.error(f"Refresh token error: {e}")
            return JSONResponse(
                status_code=500, content={"error": "server_error", "error_description": "Token refresh failed"}
            )


# Create global OAuth proxy instance
mcp_oauth_proxy = MCPOAuthProxy()
