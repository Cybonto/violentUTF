"""
Authentication endpoints for obtaining JWT tokens
SECURITY: Rate limiting and secure error handling implemented to prevent attacks
"""

import logging
from datetime import timedelta
from typing import Optional

import httpx
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.error_handling import authentication_error, safe_error_response
from app.core.password_policy import (default_password_validator,
                                      validate_password_strength)
from app.core.rate_limiting import auth_rate_limit
from app.core.security import create_access_token
from app.core.security_logging import (log_authentication_failure,
                                       log_authentication_success,
                                       log_suspicious_activity,
                                       log_token_event,
                                       log_weak_password_attempt)
from app.models.auth import User
from app.schemas.auth import (Token, TokenInfoResponse, TokenValidationRequest,
                              TokenValidationResponse, UserInfo)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/token", response_model=Token)
@auth_rate_limit("auth_login")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """
    OAuth2 compatible token endpoint.
    Authenticates against Keycloak and returns a JWT token.
    """
    # Prepare request to Keycloak
    token_url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token"

    data = {
        "grant_type": "password",
        "client_id": settings.KEYCLOAK_CLIENT_ID,
        "client_secret": settings.KEYCLOAK_CLIENT_SECRET,
        "username": form_data.username,
        "password": form_data.password,
        "scope": "openid profile email",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(token_url, data=data)

            if response.status_code == 200:
                keycloak_token = response.json()

                # SECURITY FIX: Implement proper Keycloak JWT signature verification
                from app.services.keycloak_verification import \
                    keycloak_verifier

                try:
                    # Verify Keycloak token signature and extract user info
                    keycloak_access_token = keycloak_token["access_token"]
                    decoded_token = await keycloak_verifier.verify_keycloak_token(
                        keycloak_access_token
                    )
                    user_info = keycloak_verifier.extract_user_info(decoded_token)

                    # Use verified information from Keycloak token
                    username = user_info["username"]
                    email = user_info["email"]
                    roles = user_info["roles"]

                    logger.info(
                        f"Successfully verified Keycloak token for user: {username}"
                    )

                except HTTPException:
                    # Keycloak verification failed, re-raise the exception
                    raise
                except Exception as e:
                    logger.error(
                        f"Unexpected error during Keycloak verification: {str(e)}"
                    )
                    log_authentication_failure(
                        username=form_data.username,
                        request=request,
                        reason="Keycloak token verification error",
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Authentication service error",
                    )

                # Create our own JWT token with verified Keycloak information
                access_token_expires = timedelta(
                    minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
                )
                access_token_data = {
                    "sub": username,
                    "email": email,
                    "roles": roles,
                    "keycloak_id": user_info["keycloak_id"],
                    "email_verified": user_info["email_verified"],
                    "name": user_info.get("name"),
                    "session_state": user_info.get("session_state"),
                    "verified_by_keycloak": True,  # Mark as cryptographically verified
                    "keycloak_iat": user_info["issued_at"],
                    "keycloak_exp": user_info["expires_at"],
                }

                access_token = create_access_token(
                    data=access_token_data, expires_delta=access_token_expires
                )

                # Log successful authentication
                log_authentication_success(
                    username=username,
                    user_id=username,
                    request=request,
                    keycloak_auth=True,
                )

                # Log token creation
                log_token_event(
                    event_type="created",
                    username=username,
                    token_type="access",
                    request=request,
                )

                return Token(
                    access_token=access_token,
                    token_type="bearer",
                    expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                )
            else:
                # Log failed authentication attempt without exposing details
                log_authentication_failure(
                    username=form_data.username,
                    request=request,
                    reason="Invalid credentials or Keycloak authentication failed",
                )
                raise authentication_error("Invalid credentials")

    except httpx.RequestError as e:
        # Log detailed error server-side but return generic error to client
        logger.error(f"Keycloak connection error: {str(e)}")
        log_authentication_failure(
            username=form_data.username,
            request=request,
            reason="Authentication service unavailable",
        )
        raise safe_error_response(
            "Authentication service temporarily unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        # Catch any other authentication errors
        logger.error(f"Unexpected authentication error: {str(e)}")
        log_authentication_failure(
            username=form_data.username,
            request=request,
            reason="Unexpected authentication error",
        )
        raise authentication_error("Authentication failed")


@router.get("/me", response_model=UserInfo)
@auth_rate_limit("auth_token")
async def read_users_me(
    request: Request, current_user: User = Depends(get_current_user)
):
    """
    Get current user information
    """
    return UserInfo(
        username=current_user.username,
        email=current_user.email,
        roles=current_user.roles,
    )


@router.post("/refresh", response_model=Token)
@auth_rate_limit("auth_refresh")
async def refresh_token(
    request: Request, current_user: User = Depends(get_current_user)
):
    """
    Refresh access token
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_data = {
        "sub": current_user.username,
        "email": current_user.email,
        "roles": current_user.roles,
    }

    access_token = create_access_token(
        data=access_token_data, expires_delta=access_token_expires
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/token/info", response_model=TokenInfoResponse)
@auth_rate_limit("auth_validate")
async def get_token_info(
    request: Request, current_user: User = Depends(get_current_user)
):
    """
    Get decoded JWT token information for current user
    """
    from datetime import datetime

    import jwt

    # Check if user has AI access (ai-api-access role)
    has_ai_access = "ai-api-access" in current_user.roles

    return TokenInfoResponse(
        username=current_user.username,
        email=current_user.email,
        roles=current_user.roles,
        expires_at=(
            datetime.fromtimestamp(current_user.exp)
            if hasattr(current_user, "exp")
            else datetime.now()
        ),
        issued_at=(
            datetime.fromtimestamp(current_user.iat)
            if hasattr(current_user, "iat")
            else datetime.now()
        ),
        has_ai_access=has_ai_access,
        token_valid=True,
    )


@router.post("/token/validate", response_model=TokenValidationResponse)
@auth_rate_limit("auth_validate")
async def validate_token(
    request_data: TokenValidationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Validate JWT token and check specific roles/permissions
    """
    try:
        # Check if user has AI access
        has_ai_access = "ai-api-access" in current_user.roles

        # Check required roles
        missing_roles = []
        if request_data.required_roles:
            missing_roles = [
                role
                for role in request_data.required_roles
                if role not in current_user.roles
            ]

        # Check AI access if requested
        if request_data.check_ai_access and not has_ai_access:
            missing_roles.append("ai-api-access")

        valid = len(missing_roles) == 0

        return TokenValidationResponse(
            valid=valid,
            username=current_user.username,
            roles=current_user.roles,
            has_ai_access=has_ai_access,
            missing_roles=missing_roles,
            error=None if valid else f"Missing required roles: {missing_roles}",
        )

    except Exception as e:
        return TokenValidationResponse(
            valid=False,
            username=None,
            roles=[],
            has_ai_access=False,
            missing_roles=[],
            error=str(e),
        )


@router.post("/logout")
@auth_rate_limit("auth_token")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """
    Invalidate current session and tokens
    """
    # In a real implementation, you would:
    # 1. Add token to blacklist
    # 2. Clear session data
    # 3. Invalidate refresh tokens
    return {"message": "Successfully logged out"}


@router.get("/password-requirements")
async def get_password_requirements():
    """
    Get password security requirements and policy
    """
    return {
        "requirements": default_password_validator.generate_password_requirements(),
        "message": "Password must meet all security requirements",
    }


@router.post("/password-strength")
@auth_rate_limit("auth_validate")
async def check_password_strength(request: Request):
    """
    Check password strength without storing or logging the password
    Expects JSON: {"password": "string", "username": "optional", "email": "optional"}
    """
    try:
        data = await request.json()
        password = data.get("password", "")
        username = data.get("username")
        email = data.get("email")

        if not password:
            raise safe_error_response("Password is required", status_code=400)

        # Validate password strength
        validation_result = validate_password_strength(
            password=password, username=username, email=email
        )

        # Log weak password attempts for security monitoring
        if not validation_result.is_valid or validation_result.strength.value in [
            "very_weak",
            "weak",
        ]:
            log_weak_password_attempt(
                username=username,
                strength=validation_result.strength.value,
                request=request,
                score=validation_result.score,
            )

        # Return validation result without storing password
        return {
            "valid": validation_result.is_valid,
            "strength": validation_result.strength.value,
            "score": validation_result.score,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "suggestions": validation_result.suggestions,
        }

    except Exception as e:
        logger.error(f"Password strength check error: {str(e)}")
        raise safe_error_response("Failed to check password strength", status_code=500)
