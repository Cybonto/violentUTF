# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP Authentication Bridge."""
import logging
from typing import Any, Dict, Optional, Self

from fastapi import HTTPException, Request, status

from app.core.security import create_access_token, decode_token
from app.services.keycloak_verification import keycloak_verifier

logger = logging.getLogger(__name__)


class MCPAuthHandler:
    """Handle authentication for MCP operations."""

    def __init__(self: "Self") -> None:
        """Initialize instance."""
        # Use the existing keycloak_verifier instance

        self.keycloak_verifier = keycloak_verifier

    async def authenticate(self: "Self", credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate MCP client."""
        auth_type = credentials.get("type", "bearer")

        if auth_type == "bearer":
            return await self._handle_bearer_auth(credentials)
        elif auth_type == "oauth":
            return await self._handle_oauth_auth(credentials)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unsupported authentication type: {auth_type}",
            )

    async def _handle_bearer_auth(self: "Self", credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bearer token authentication."""
        token = credentials.get("token")

        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")

        # Verify JWT token using existing verification
        try:
            # First try to verify as Keycloak token
            try:
                keycloak_payload = await self.keycloak_verifier.verify_keycloak_token(token)
                user_info = self.keycloak_verifier.extract_user_info(keycloak_payload)
                return {
                    "user_id": user_info["username"],
                    "roles": user_info["roles"],
                    "email": user_info["email"],
                    "keycloak_verified": True,
                }
            except Exception:
                # Fall back to local JWT verification
                payload = decode_token(token)
                if payload:
                    return {
                        "user_id": payload.get("sub"),
                        "roles": payload.get("roles", []),
                        "email": payload.get("email"),
                        "keycloak_verified": False,
                    }
                else:
                    raise HTTPException(  # pylint: disable=raise-missing-from
                        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                    )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("Authentication error: %s", e)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed") from e

    async def _handle_oauth_auth(self: "Self", credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Handle OAuth authentication flow."""
        code = credentials.get("code")

        if not code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth authorization code required",
            )

        try:
            # TODO: Exchange code for token via Keycloak (not yet implemented)
            # token_response = await self.keycloak_verifier.exchange_code(code)
            # access_token = token_response.get("access_token")
            access_token = code  # Temporary: assume code is actually a token

            # Verify the received token
            keycloak_payload = await self.keycloak_verifier.verify_keycloak_token(access_token)
            user_info = self.keycloak_verifier.extract_user_info(keycloak_payload)

            # Create local JWT for API access
            api_token = create_access_token(
                {
                    "sub": user_info["username"],
                    "email": user_info["email"],
                    "roles": user_info["roles"],
                }
            )

            return {
                "user_id": user_info["username"],
                "roles": user_info["roles"],
                "email": user_info["email"],
                "access_token": api_token,
                "keycloak_verified": True,
            }

        except Exception as e:
            logger.error("OAuth authentication error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OAuth authentication failed",
            ) from e

    async def authenticate_request(self: "Self", request: Request) -> Optional[Dict[str, Any]]:
        """Authenticate MCP requests using existing Keycloak verification."""
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        # First try Keycloak verification
        keycloak_payload = await self.keycloak_verifier.verify_keycloak_token(token)
        if keycloak_payload:
            return keycloak_payload

        # Fallback to JWT verification for Streamlit compatibility
        result = decode_token(token)
        return result

    def create_api_token(self: "Self", user_info: Dict[str, Any]) -> str:
        """Create API token for MCP access."""
        return create_access_token(
            {
                "sub": user_info.get("username", user_info.get("user_id")),
                "email": user_info.get("email"),
                "roles": user_info.get("roles", []),
            }
        )

    async def get_auth_headers(self: "Self") -> Dict[str, str]:
        """Get authentication headers for MCP requests."""
        headers = {
            "Content-Type": "application/json",
            "X-API-Gateway": "APISIX",
        }

        # Try to get token from test environment or create a default one
        try:
            # For testing, create a minimal JWT token with basic claims
            test_token = create_access_token(
                {
                    "sub": "mcp_test_user",
                    "email": "mcp_test@violentutf.local",
                    "roles": ["mcp-access"],
                }
            )

            if test_token:
                headers["Authorization"] = f"Bearer {test_token}"

        except Exception as e:
            logger.warning("Could not create auth token for MCP headers: %s", e)
            # Return headers without Authorization if token creation fails

        return headers
