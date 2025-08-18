# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
JWT Token Management Utility for ViolentUTF Streamlit Application

This module handles JWT token creation, validation, and refresh logic
between Streamlit frontend and FastAPI backend.
"""

import asyncio
import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt
import requests
import streamlit as st

logger = logging.getLogger(__name__)


class JWTManager:
    """Manages JWT tokens for Streamlit to FastAPI communication"""

    def __init__(self):
        # Load environment variables from .env file
        self._load_environment()
        self.api_base_url = self._get_api_base_url()
        self._cached_secret = None
        self._secret_cache_time = None
        self._secret_cache_duration = 300  # 5 minutes

        # Proactive refresh settings
        self._refresh_enabled = True
        self._refresh_buffer = 600  # 10 minutes before expiry
        self._max_retry_attempts = 3
        self._retry_delay = 5  # seconds

        # Track refresh state
        self._last_refresh_attempt = 0
        self._refresh_in_progress = False
        self._last_error = None

    def _load_environment(self):
        """Load environment variables from .env file if available"""
        try:
            import os
            from pathlib import Path

            from dotenv import load_dotenv

            # Look for .env file in multiple locations
            env_locations = [
                Path(__file__).parent.parent / ".env",  # violentutf/.env
                Path.cwd() / "violentutf" / ".env",  # ./violentutf/.env
                Path.cwd() / ".env",  # ./.env
            ]

            loaded = False
            for env_file in env_locations:
                if env_file.exists():
                    load_dotenv(env_file)
                    logger.info(f"Loaded environment from {env_file}")
                    loaded = True
                    break

            if not loaded:
                logger.warning(f"Environment file not found in any of: {env_locations}")

            # Log what we actually loaded for debugging
            jwt_secret = os.getenv("JWT_SECRET_KEY")
            logger.info(
                f"JWT_SECRET_KEY loaded: {bool(jwt_secret)} (preview: {jwt_secret[:8] + '...' if jwt_secret else 'None'})"
            )

        except ImportError:
            logger.warning("python-dotenv not available, environment variables may not be loaded")
        except Exception as e:
            logger.error(f"Failed to load environment variables: {e}")

    def _get_api_base_url(self) -> str:
        """Get the API base URL from environment or default"""
        raw_url = os.getenv("VIOLENTUTF_API_URL", "http://localhost:9080")
        return raw_url.rstrip("/api").rstrip("/")

    def _get_jwt_secret(self) -> Optional[str]:
        """
        Get JWT secret key using multiple fallback strategies:
        1. Environment variable JWT_SECRET_KEY
        2. Cached secret from previous API call
        3. API call to FastAPI /keys/jwt-public endpoint
        """
        # Strategy 1: Try environment variable first (already loaded by _load_environment)
        secret = os.getenv("JWT_SECRET_KEY")
        if secret:
            logger.info(f"JWT secret obtained from environment variable (preview: {secret[:8]}...)")
            return secret

        # Strategy 2: Try to manually load from .env files if environment loading failed
        from pathlib import Path

        env_locations = [
            Path(__file__).parent.parent / ".env",  # violentutf/.env
            Path.cwd() / "violentutf" / ".env",  # ./violentutf/.env
            Path.cwd() / ".env",  # ./.env
        ]

        for env_file in env_locations:
            if env_file.exists():
                try:
                    with open(env_file, "r") as f:
                        for line in f:
                            if line.strip().startswith("JWT_SECRET_KEY="):
                                file_secret = line.strip().split("=", 1)[1]
                                logger.info(f"JWT secret found in {env_file} (preview: {file_secret[:8]}...)")
                                return file_secret
                except Exception as e:
                    logger.error(f"Failed to read {env_file}: {e}")

        # Strategy 3: Check cached secret
        current_time = time.time()
        if (
            self._cached_secret
            and self._secret_cache_time
            and (current_time - self._secret_cache_time) < self._secret_cache_duration
        ):
            logger.info("JWT secret obtained from cache")
            return self._cached_secret

        # No secret found - provide detailed debugging
        logger.error("JWT_SECRET_KEY not found in any location!")
        logger.error(f"Checked environment variable: {bool(os.getenv('JWT_SECRET_KEY'))}")
        logger.error(f"Checked files: {[str(f) for f in env_locations if f.exists()]}")
        logger.error(f"Current working directory: {Path.cwd()}")
        return None

    def create_token(self, keycloak_token_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a FastAPI-compatible JWT token from Keycloak token data

        Args:
            keycloak_token_data: Decoded Keycloak token payload

        Returns:
            JWT token string or None if failed
        """
        try:
            secret_key = self._get_jwt_secret()
            if not secret_key:
                return None

            # Extract user information from Keycloak token
            # ALWAYS use preferred_username as the unique identifier for consistency
            username = keycloak_token_data.get("preferred_username") or keycloak_token_data.get("sub", "user")
            email = keycloak_token_data.get("email", "user@example.com")

            logger.info(f"Creating JWT token for Keycloak user: {username}")

            # Create FastAPI-compatible token with shorter expiry for security
            current_time = int(time.time())
            payload = {
                "sub": username,
                "username": username,  # Add explicit username field for FastAPI auth
                "email": email,
                "name": keycloak_token_data.get("name", username),
                "roles": keycloak_token_data.get("roles", ["ai-api-access"]),
                "iat": current_time,
                "exp": current_time + 1800,  # 30 minutes expiry (shorter for security)
                "token_type": "access",
            }

            # Create token with HS256 algorithm
            api_token = jwt.encode(payload, secret_key, algorithm="HS256")

            # Store token and expiry time in session state
            st.session_state["api_token"] = api_token
            st.session_state["api_token_exp"] = payload["exp"]
            st.session_state["api_token_created"] = current_time

            logger.info(f"Created JWT token for user: {username}, expires at: {datetime.fromtimestamp(payload['exp'])}")
            return api_token

        except Exception as e:
            logger.error(f"Failed to create JWT token: {e}")
            return None

    def get_valid_token(self) -> Optional[str]:
        """
        Get a valid JWT token, refreshing if necessary

        Returns:
            Valid JWT token or None if unavailable
        """
        try:
            # Check if we have a token in session state
            if "api_token" not in st.session_state:
                logger.debug("No API token in session state")
                return None

            # Validate token signature first
            token = st.session_state["api_token"]
            if not self._validate_token_signature(token):
                logger.warning("JWT token has invalid signature, clearing session and attempting recreation")
                self._clear_token()
                # Try to recreate token immediately
                return self._attempt_token_recreation()

            current_time = int(time.time())
            token_exp = st.session_state.get("api_token_exp", 0)

            # Proactive refresh if token will expire in next 10 minutes
            if current_time >= (token_exp - self._refresh_buffer):
                logger.info("JWT token expiring soon, attempting proactive refresh")
                self._attempt_proactive_refresh()

            # Check if token is expired or will expire very soon (5 minutes buffer)
            if current_time >= (token_exp - 300):
                logger.info("JWT token expired or expiring soon, refresh needed")
                self._clear_token()
                return None

            return st.session_state["api_token"]

        except Exception as e:
            logger.error(f"Error checking token validity: {e}")
            return None

    def is_token_expired(self) -> bool:
        """Check if the current token is expired"""
        if "api_token_exp" not in st.session_state:
            return True

        current_time = int(time.time())
        token_exp = st.session_state.get("api_token_exp", 0)

        return current_time >= token_exp

    def get_token_info(self) -> Dict[str, Any]:
        """Get information about the current token"""
        if "api_token" not in st.session_state:
            return {"status": "no_token"}

        current_time = int(time.time())
        token_exp = st.session_state.get("api_token_exp", 0)
        token_created = st.session_state.get("api_token_created", 0)

        time_remaining = max(0, token_exp - current_time)
        time_elapsed = current_time - token_created

        return {
            "status": "active" if time_remaining > 0 else "expired",
            "expires_at": datetime.fromtimestamp(token_exp).isoformat(),
            "time_remaining_seconds": time_remaining,
            "time_remaining_minutes": time_remaining // 60,
            "time_elapsed_seconds": time_elapsed,
            "created_at": datetime.fromtimestamp(token_created).isoformat(),
        }

    def clear_token(self):
        """Clear the stored token from session state"""
        self._clear_token()
        logger.info("JWT token manually cleared from session state")

    def _validate_token_signature(self, token: str) -> bool:
        """
        Validate JWT token signature using the current secret

        Args:
            token: JWT token to validate

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            secret_key = self._get_jwt_secret()
            if not secret_key:
                logger.error("Cannot validate token - no JWT secret available")
                return False

            # Try to decode the token to validate signature
            jwt.decode(token, secret_key, algorithms=["HS256"])
            return True

        except jwt.InvalidSignatureError:
            logger.error("JWT token signature validation failed - token was created with different secret")
            return False
        except jwt.ExpiredSignatureError:
            # Token is expired but signature is valid
            return True
        except Exception as e:
            logger.error(f"JWT token validation error: {e}")
            return False

    def _attempt_token_recreation(self) -> Optional[str]:
        """
        Attempt to recreate a JWT token using environment credentials

        Returns:
            New JWT token or None if failed
        """
        try:
            import os

            # Get consistent username (always account name, not display name)
            from utils.user_context import get_consistent_username

            username = get_consistent_username()

            # Create mock Keycloak data with account name as identifier
            keycloak_data = {
                "preferred_username": username,
                "name": "ViolentUTF User",  # Generic display name
                "email": f"{username}@violentutf.local",
                "sub": username,
                "roles": ["ai-api-access"],
            }

            # Create new token
            new_token = self.create_token(keycloak_data)
            if new_token:
                logger.info("Successfully recreated JWT token after signature validation failure")
                return new_token
            else:
                logger.error("Failed to recreate JWT token")
                return None

        except Exception as e:
            logger.error(f"Token recreation failed: {e}")
            return None

    def _clear_token(self):
        """Internal method to clear token state"""
        st.session_state.pop("api_token", None)
        st.session_state.pop("api_token_exp", None)
        st.session_state.pop("api_token_created", None)
        self._refresh_in_progress = False

    def _attempt_proactive_refresh(self):
        """Attempt to proactively refresh the token before it expires"""
        current_time = time.time()

        # Avoid too frequent refresh attempts
        if current_time - self._last_refresh_attempt < self._retry_delay:
            return

        # Skip if refresh already in progress
        if self._refresh_in_progress:
            return

        self._last_refresh_attempt = current_time
        self._refresh_in_progress = True

        try:
            # Get current token data to recreate
            old_token_data = self._get_current_token_data()
            if not old_token_data:
                logger.warning("Cannot refresh token - no current token data available")
                return

            # Attempt refresh with retry logic
            new_token = self._refresh_token_with_retry(old_token_data)
            if new_token:
                logger.info("Proactive token refresh successful")
                self._last_error = None
            else:
                logger.warning("Proactive token refresh failed")

        except Exception as e:
            logger.error(f"Error during proactive token refresh: {e}")
            self._last_error = str(e)
        finally:
            self._refresh_in_progress = False

    def _get_current_token_data(self) -> Optional[Dict[str, Any]]:
        """Extract user data from current token for refresh"""
        try:
            current_token = st.session_state.get("api_token")
            if not current_token:
                return None

            # SECURITY FIX: Verify JWT signature properly
            try:
                secret_key = os.getenv("JWT_SECRET_KEY")
                if not secret_key:
                    logger.error("JWT_SECRET_KEY not set - cannot verify token")
                    return None

                # Properly verify the JWT signature
                payload = jwt.decode(current_token, secret_key, algorithms=["HS256"])
                logger.debug("JWT signature verification successful")
            except jwt.ExpiredSignatureError:
                logger.warning("JWT token has expired")
                return None
            except jwt.InvalidTokenError as e:
                logger.error(f"JWT signature verification failed: {e}")
                return None

            # Return user data for token recreation
            return {
                "preferred_username": payload.get("sub", "user"),
                "email": payload.get("email", "user@example.com"),
                "name": payload.get("name", "User"),
                "sub": payload.get("sub", "user"),
                "roles": payload.get("roles", ["ai-api-access"]),
            }
        except Exception as e:
            logger.error(f"Error extracting token data: {e}")
            return None

    def _refresh_token_with_retry(self, token_data: Dict[str, Any]) -> Optional[str]:
        """Refresh token with retry logic"""
        for attempt in range(self._max_retry_attempts):
            try:
                logger.info(f"Token refresh attempt {attempt + 1}/{self._max_retry_attempts}")
                new_token = self.create_token(token_data)
                if new_token:
                    return new_token

            except Exception as e:
                logger.warning(f"Token refresh attempt {attempt + 1} failed: {e}")
                if attempt < self._max_retry_attempts - 1:
                    time.sleep(self._retry_delay)

        return None

    def get_refresh_status(self) -> Dict[str, Any]:
        """Get current refresh status for UI display"""
        current_time = int(time.time())
        token_exp = st.session_state.get("api_token_exp", 0)
        time_remaining = max(0, token_exp - current_time)

        # Determine status
        if not st.session_state.get("api_token"):
            status = "no_token"
        elif self._refresh_in_progress:
            status = "refreshing"
        elif time_remaining <= 300:  # 5 minutes
            status = "expired"
        elif time_remaining <= 600:  # 10 minutes
            status = "expiring_soon"
        else:
            status = "active"

        return {
            "status": status,
            "time_remaining_seconds": time_remaining,
            "time_remaining_minutes": time_remaining // 60,
            "refresh_enabled": self._refresh_enabled,
            "refresh_in_progress": self._refresh_in_progress,
            "last_error": self._last_error,
            "next_refresh_in": (
                max(0, self._refresh_buffer - (token_exp - current_time)) if token_exp > current_time else 0
            ),
        }


# Global instance
jwt_manager = JWTManager()
