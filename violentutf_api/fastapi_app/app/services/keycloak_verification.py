# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Keycloak JWT Token Verification Service
SECURITY: Implements proper JWT signature verification using Keycloak public keys
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
import jwt
from app.core.config import settings
from app.core.security_logging import log_authentication_failure, log_security_error
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException, status
from jwt import PyJWKClient

logger = logging.getLogger(__name__)


class KeycloakJWTVerifier:
    """
    Keycloak JWT token verification with proper signature validation.
    """

    def __init__(self) -> None:
        self.keycloak_url = settings.KEYCLOAK_URL
        self.realm = settings.KEYCLOAK_REALM
        self.client_id = settings.KEYCLOAK_CLIENT_ID

        # Keycloak well-known configuration URL
        self.well_known_url = f"{self.keycloak_url}/realms/{self.realm}/.well-known/openid_configuration"
        self.jwks_uri = None
        self.jwks_client = None
        self.issuer = f"{self.keycloak_url}/realms/{self.realm}"

        # Cache for configuration
        self._config_cache = {}
        self._config_cache_time = 0
        self._cache_ttl = 3600  # 1 hour cache

    async def _get_keycloak_config(self) -> Dict[str, Any]:
        """
        Get Keycloak OpenID Connect configuration.

        Returns:
            Dictionary containing Keycloak configuration
        """
        current_time = time.time().

        # Check cache
        if self._config_cache and current_time - self._config_cache_time < self._cache_ttl:
            return self._config_cache

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.well_known_url)
                response.raise_for_status()

                config = response.json()
                self._config_cache = config
                self._config_cache_time = current_time

                # Store JWKS URI for key retrieval
                self.jwks_uri = config.get("jwks_uri")

                logger.info(f"Retrieved Keycloak configuration for realm: {self.realm}")
                return config

        except Exception as e:
            logger.error(f"Failed to retrieve Keycloak configuration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service configuration unavailable",
            )

    async def _get_jwks_client(self) -> PyJWKClient:
        """
        Get or create JWKS client for key retrieval.

        Returns:
            PyJWKClient instance
        """
        if not self.jwks_client or not self.jwks_uri:
            # Ensure we have the JWKS URI
            await self._get_keycloak_config()

            if not self.jwks_uri:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="JWKS URI not available from Keycloak"
                )

            # Create JWKS client with caching
            self.jwks_client = PyJWKClient(
                uri=self.jwks_uri,
                cache_keys=True,
                max_cached_keys=10,
                cache_jwks_for=3600,  # Cache for 1 hour
                jwks_request_timeout=10,
            )

        return self.jwks_client

    async def verify_keycloak_token(self, token: str) -> Dict[str, Any]:
        """
        Verify Keycloak JWT token with proper signature validation.

        Args:
            token: Keycloak JWT token to verify

        Returns:
            Decoded and verified token payload

        Raises:
            HTTPException: If token verification fails
        """
        try:
            # Get JWKS client
            jwks_client = await self._get_jwks_client()

            # Get the signing key from Keycloak JWKS
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
            except jwt.PyJWKClientError as e:
                logger.warning(f"Failed to get signing key from Keycloak: {str(e)}")
                log_authentication_failure(reason="Invalid JWT signing key", keycloak_error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: unable to verify signature"
                )

            # Verify token signature and claims
            try:
                decoded_token = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256", "ES256", "HS256"],  # Common Keycloak algorithms
                    audience=self.client_id,  # Verify audience matches our client
                    issuer=self.issuer,  # Verify issuer matches our realm
                    options={
                        "verify_signature": True,  # CRITICAL: Always verify signature
                        "verify_exp": True,  # Verify expiration
                        "verify_iat": True,  # Verify issued at
                        "verify_aud": True,  # Verify audience
                        "verify_iss": True,  # Verify issuer
                        "require_exp": True,  # Require expiration claim
                        "require_iat": True,  # Require issued at claim
                    },
                )

                # Additional security validations
                self._validate_token_claims(decoded_token)

                logger.debug(
                    f"Successfully verified Keycloak token for user: {decoded_token.get('preferred_username')}"
                )
                return decoded_token

            except jwt.ExpiredSignatureError:
                logger.warning("Keycloak token has expired")
                log_authentication_failure(reason="Token expired")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")

            except jwt.InvalidAudienceError:
                logger.warning("Keycloak token has invalid audience")
                log_authentication_failure(reason="Invalid token audience")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token audience mismatch")

            except jwt.InvalidIssuerError:
                logger.warning("Keycloak token has invalid issuer")
                log_authentication_failure(reason="Invalid token issuer")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token issuer mismatch")

            except jwt.InvalidSignatureError:
                logger.warning("Keycloak token has invalid signature")
                log_authentication_failure(reason="Invalid token signature")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token signature verification failed"
                )

            except jwt.InvalidTokenError as e:
                logger.warning(f"Keycloak token validation failed: {str(e)}")
                log_authentication_failure(reason=f"Token validation failed: {str(e)}")
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token validation failed")

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {str(e)}")
            log_security_error(error_type="keycloak_verification_error", error_message=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token verification service error"
            )

    def _validate_token_claims(self, decoded_token: Dict[str, Any]) -> None:
        """
        Perform additional validation on token claims.

        Args:
            decoded_token: Decoded JWT payload

        Raises:
            HTTPException: If validation fails
        """
        # Validate token type
        token_type = decoded_token.get("typ")
        if token_type and token_type.lower() != "bearer":
            logger.warning(f"Invalid token type: {token_type}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

        # Validate required claims
        required_claims = ["sub", "preferred_username", "email", "realm_access"]
        for claim in required_claims:
            if claim not in decoded_token:
                logger.warning(f"Missing required claim: {claim}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token missing required claim: {claim}"
                )

        # Validate subject is not empty
        subject = decoded_token.get("sub")
        if not subject or not isinstance(subject, str) or len(subject.strip()) == 0:
            logger.warning("Invalid or empty subject claim")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

        # Validate username
        username = decoded_token.get("preferred_username")
        if not username or not isinstance(username, str) or len(username.strip()) == 0:
            logger.warning("Invalid or empty username claim")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token username")

        # Validate email format (basic check)
        email = decoded_token.get("email")
        if email and not isinstance(email, str):
            logger.warning("Invalid email claim type")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token email")

        # Validate realm access structure
        realm_access = decoded_token.get("realm_access", {})
        if not isinstance(realm_access, dict):
            logger.warning("Invalid realm_access claim structure")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token realm access")

    def extract_user_info(self, decoded_token: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract user information from verified Keycloak token.

        Args:
            decoded_token: Verified Keycloak JWT payload

        Returns:
            Dictionary containing user information
        """
        # Extract realm roles
        realm_access = decoded_token.get("realm_access", {})
        realm_roles = realm_access.get("roles", [])

        # Extract resource access roles
        resource_access = decoded_token.get("resource_access", {})
        client_access = resource_access.get(self.client_id, {})
        client_roles = client_access.get("roles", [])

        # Combine roles and filter for ViolentUTF specific roles
        all_roles = list(set(realm_roles + client_roles))

        # Map Keycloak roles to ViolentUTF roles
        violentutf_roles = self._map_keycloak_roles(all_roles)

        return {
            "sub": decoded_token.get("sub"),
            "username": decoded_token.get("preferred_username"),
            "email": decoded_token.get("email"),
            "email_verified": decoded_token.get("email_verified", False),
            "name": decoded_token.get("name"),
            "given_name": decoded_token.get("given_name"),
            "family_name": decoded_token.get("family_name"),
            "roles": violentutf_roles,
            "realm_roles": realm_roles,
            "client_roles": client_roles,
            "keycloak_id": decoded_token.get("sub"),
            "issued_at": decoded_token.get("iat"),
            "expires_at": decoded_token.get("exp"),
            "session_state": decoded_token.get("session_state"),
        }

    def _map_keycloak_roles(self, keycloak_roles: List[str]) -> List[str]:
        """
        Map Keycloak roles to ViolentUTF application roles.

        Args:
            keycloak_roles: List of Keycloak roles

        Returns:
            List of mapped ViolentUTF roles
        """
        role_mapping = {
            # Keycloak admin roles
            "realm-admin": "admin",
            "admin": "admin",
            "violentutf-admin": "admin",
            # AI access roles
            "ai-user": "ai-api-access",
            "ai-access": "ai-api-access",
            "violentutf-ai-access": "ai-api-access",
            # Default user roles
            "user": "user",
            "violentutf-user": "user",
            # Research roles
            "researcher": "researcher",
            "violentutf-researcher": "researcher",
            # Analyst roles
            "analyst": "analyst",
            "violentutf-analyst": "analyst",
        }

        mapped_roles = []

        for role in keycloak_roles:
            # Direct mapping
            if role in role_mapping:
                mapped_roles.append(role_mapping[role])
            # Keep roles that start with violentutf-
            elif role.startswith("violentutf-"):
                mapped_roles.append(role)

        # Ensure every authenticated user has basic access
        if not mapped_roles:
            mapped_roles = ["user"]

        # Ensure AI access users have the necessary role
        if any(role in mapped_roles for role in ["admin", "researcher", "analyst"]):
            if "ai-api-access" not in mapped_roles:
                mapped_roles.append("ai-api-access")

        return list(set(mapped_roles))  # Remove duplicates


# Global instance
keycloak_verifier = KeycloakJWTVerifier()
