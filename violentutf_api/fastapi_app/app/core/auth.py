"""
Authentication and authorization middleware
"""

import logging
from typing import Optional, Tuple

import httpx
from app.core.config import settings
from app.core.security import decode_token
from app.db.database import get_db_session
from app.models.api_key import APIKey
from app.models.auth import User
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError as JWTError

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthMiddleware:
    """
    Authentication middleware that supports both JWT and API keys
    """

    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
        api_key: Optional[str] = Security(api_key_header),
    ) -> User:
        """
        Authenticate request using either JWT or API key
        """
        # Check if request is from APISIX (cryptographically verified)
        if not self._is_from_apisix(request):
            # Log security event for unauthorized direct access attempt
            from app.core.security_logging import log_suspicious_activity

            log_suspicious_activity(
                activity_type="direct_api_access_attempt",
                request=request,
                details="Attempt to bypass APISIX gateway detected",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Direct access not allowed. Use the API gateway."
            )

        # Try JWT authentication first
        if credentials and credentials.credentials:
            return await self._authenticate_jwt(credentials.credentials)

        # Try API key authentication
        if api_key:
            return await self._authenticate_api_key(api_key)

        # No valid authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def _is_from_apisix(self, request: Request) -> bool:
        """
        Verify request is coming from APISIX using practical security measures
        """
        # Check for basic APISIX gateway identification header
        apisix_gateway_header = request.headers.get("X-API-Gateway")
        if apisix_gateway_header != "APISIX":
            logger.warning("Missing or invalid X-API-Gateway header")
            return False

        # Check for APISIX forwarded headers that indicate proper routing
        forwarded_for = request.headers.get("X-Forwarded-For")
        forwarded_host = request.headers.get("X-Forwarded-Host")
        real_ip = request.headers.get("X-Real-IP")

        if not any([forwarded_for, forwarded_host, real_ip]):
            logger.warning("Missing APISIX proxy headers")
            return False

        # Optional: Enhanced HMAC verification if configured
        apisix_signature = request.headers.get("X-APISIX-Signature")
        apisix_timestamp = request.headers.get("X-APISIX-Timestamp")

        if apisix_signature and apisix_timestamp:
            # If HMAC headers are present, verify them
            try:
                # Verify timestamp (5 minute window)
                import time

                current_time = int(time.time())
                request_time = int(apisix_timestamp)

                if abs(current_time - request_time) > 300:
                    logger.warning(f"APISIX timestamp outside valid window: {request_time}")
                    return False

                # Verify HMAC signature
                if not self._verify_apisix_signature(request, apisix_signature, apisix_timestamp):
                    logger.warning("APISIX HMAC signature verification failed")
                    return False

                logger.debug("APISIX HMAC verification successful")
            except Exception as e:
                logger.warning(f"APISIX HMAC verification error: {e}")
                # Continue without HMAC verification for now

        logger.debug("APISIX gateway verification successful")
        return True

    def _verify_apisix_signature(self, request: Request, signature: str, timestamp: str) -> bool:
        """
        Verify HMAC signature from APISIX gateway

        Args:
            request: FastAPI request object
            signature: HMAC signature from APISIX
            timestamp: Request timestamp

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            import base64
            import hashlib
            import hmac

            from app.core.config import settings

            # Get the shared secret
            gateway_secret = settings.APISIX_GATEWAY_SECRET
            if not gateway_secret:
                logger.error("APISIX_GATEWAY_SECRET not configured")
                return False

            # Create signature payload: method + path + timestamp + body_hash
            method = request.method
            path = str(request.url.path)

            # For signature, we'll use: METHOD:PATH:TIMESTAMP
            # In production, you might also include body hash for POST/PUT requests
            signature_payload = f"{method}:{path}:{timestamp}"

            # Calculate expected HMAC signature
            expected_signature = hmac.new(
                gateway_secret.encode("utf-8"), signature_payload.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            # Compare signatures using constant-time comparison
            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"Error verifying APISIX signature: {str(e)}")
            return False

    async def _authenticate_jwt(self, token: str) -> User:
        """
        Authenticate using JWT token
        """
        try:
            # Decode our internal JWT
            payload = decode_token(token)
            if not payload:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

            # Extract user information
            username = payload.get("sub")
            if not username:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

            # Return user object
            return User(username=username, email=payload.get("email"), roles=payload.get("roles", []), is_active=True)

        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate token")

    async def _authenticate_api_key(self, api_key: str) -> User:
        """
        Authenticate using API key
        """
        # Decode API key (which is actually a JWT)
        try:
            payload = decode_token(api_key)
            if not payload:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

            # Check if it's an API key type token
            if payload.get("type") != "api_key":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

            # Get API key from database
            async with get_db_session() as db:
                db_key = await db.get(APIKey, payload.get("key_id"))
                if not db_key or not db_key.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED, detail="API key not found or inactive"
                    )

                # Update last used timestamp
                await db_key.update_last_used()
                await db.commit()

            # Return user object
            return User(
                username=payload.get("sub"),
                email=None,
                roles=["api_user"],
                permissions=payload.get("permissions", []),
                is_active=True,
            )

        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


# Create singleton instance
auth_middleware = AuthMiddleware()


# Dependency for protected routes
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> User:
    """
    Dependency to get current authenticated user
    """
    return await auth_middleware(request, credentials, api_key)


# Dependency for optional authentication
async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
) -> Optional[User]:
    """
    Dependency to get current user if authenticated, None otherwise
    """
    try:
        return await auth_middleware(request, credentials, api_key)
    except HTTPException:
        return None


# Role-based access control
def require_role(role: str):
    """
    Dependency factory for role-based access control
    """

    async def role_checker(current_user: User = Security(get_current_user)):
        if role not in current_user.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{role}' required")
        return current_user

    return role_checker


# Permission-based access control
def require_permission(permission: str):
    """
    Dependency factory for permission-based access control
    """

    async def permission_checker(current_user: User = Security(get_current_user)):
        if permission not in current_user.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission '{permission}' required")
        return current_user

    return permission_checker
