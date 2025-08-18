# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""MCP Authentication Bridge."""
import logging
from typing import Any, Dict, Optional

import jwt
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, decode_token
from app.services.keycloak_verification import keycloak_verifier
from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


class MCPAuthHandler:
    """Handles authentication for MCP operations."""

    def __init__(self) -> None:
        """Initialize the instance."""
        # Use the existing keycloak_verifier instance
        self.keycloak_verifier = keycloak_verifier

    async def authenticate(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate MCP client."""
        auth_type = credentials.get("type", "bearer")

        if auth_type == "bearer":
            return await self._handle_bearer_auth(credentials)
        elif auth_type == "oauth":
            return await self._handle_oauth_auth(credentials)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unsupported authentication type: {auth_type}"
            )

    async def _handle_bearer_auth(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
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
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed")

    async def _handle_oauth_auth(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Handle OAuth authentication flow."""
        code = credentials.get("code")
        if not code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OAuth authorization code required")

        try:
            # Exchange code for token via Keycloak
            token_response = await self.keycloak_verifier.exchange_code(code)
            access_token = token_response.get("access_token")

            # Verify the received token
            keycloak_payload = await self.keycloak_verifier.verify_keycloak_token(access_token)
            user_info = self.keycloak_verifier.extract_user_info(keycloak_payload)

            # Create local JWT for API access
            api_token = create_access_token(
                {"sub": user_info["username"], "email": user_info["email"], "roles": user_info["roles"]}
            )

            return {
                "user_id": user_info["username"],
                "roles": user_info["roles"],
                "email": user_info["email"],
                "access_token": api_token,
                "keycloak_verified": True,
            }

        except Exception as e:
            logger.error(f"OAuth authentication error: {e}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OAuth authentication failed")

    async def authenticate_request(self, request: Request) -> Optional[Dict[str, Any]]:
        """Authenticate MCP requests using existing Keycloak verification."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        # First try Keycloak verification
        keycloak_payload = await self.keycloak_verifier.verify_token(token)
        if keycloak_payload:
            return keycloak_payload

        # Fallback to JWT verification for Streamlit compatibility
        return decode_token(token)

    def create_api_token(self, user_info: Dict[str, Any]) -> str:
        """Create API token for MCP access."""
        return create_access_token(
            {
                "sub": user_info.get("username", user_info.get("user_id")),
                "email": user_info.get("email"),
                "roles": user_info.get("roles", []),
            }
        )
