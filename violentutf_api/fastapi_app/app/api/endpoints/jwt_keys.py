"""
JWT API Key management endpoints
SECURITY: Rate limiting applied to prevent API key enumeration attacks
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from datetime import datetime
import secrets
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.security import create_api_key_token
from app.core.rate_limiting import auth_rate_limit
from app.schemas.auth import UserInfo, APIKey, APIKeyCreate, APIKeyList
from app.schemas.auth import APIKeyResponse
from app.models.auth import User
from app.models.api_key import APIKey as APIKeyModel
from app.db.database import get_session

router = APIRouter()


@router.post("/create", response_model=APIKeyResponse)
@auth_rate_limit("auth_token")
async def create_api_key(
    key_request: APIKeyCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Create a new API key for the authenticated user
    """
    # Check if user has ai-api-access role
    if "ai-api-access" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have ai-api-access role"
        )
    
    # Generate a unique key ID
    key_id = secrets.token_urlsafe(16)
    
    # Generate API key with key_id embedded
    key_data = create_api_key_token(
        user_id=current_user.username,
        key_name=key_request.name,
        permissions=key_request.permissions,
        key_id=key_id  # Add key_id to token payload
    )
    
    # Hash the token for storage
    key_hash = hashlib.sha256(key_data["token"].encode()).hexdigest()
    
    # Store key metadata in database
    api_key = APIKeyModel(
        id=key_id,
        user_id=current_user.username,
        name=key_data["key_name"],
        key_hash=key_hash,
        permissions=key_data["permissions"],
        expires_at=datetime.fromisoformat(key_data["expires_at"])
    )
    
    db.add(api_key)
    await db.commit()
    
    return APIKeyResponse(
        key_id=key_id,
        api_key=key_data["token"],
        name=key_data["key_name"],
        created_at=key_data["created_at"],
        expires_at=key_data["expires_at"],
        permissions=key_data["permissions"]
    )


@router.get("/list", response_model=APIKeyList)
@auth_rate_limit("auth_token")
async def list_api_keys(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    List all API keys for the authenticated user
    """
    # Query database for user's API keys
    result = await db.execute(
        select(APIKeyModel).where(
            APIKeyModel.user_id == current_user.username,
            APIKeyModel.is_active == True
        )
    )
    db_keys = result.scalars().all()
    
    keys = []
    for db_key in db_keys:
        keys.append(APIKey(
            id=db_key.id,
            name=db_key.name,
            created_at=db_key.created_at.isoformat(),
            expires_at=db_key.expires_at.isoformat() if db_key.expires_at else None,
            last_used=db_key.last_used_at.isoformat() if db_key.last_used_at else None,
            permissions=db_key.permissions,
            active=db_key.is_active
        ))
    
    return APIKeyList(keys=keys)


@router.delete("/{key_id}")
@auth_rate_limit("auth_token")
async def revoke_api_key(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session)
):
    """
    Revoke an API key
    """
    # Find the API key
    result = await db.execute(
        select(APIKeyModel).where(
            APIKeyModel.id == key_id,
            APIKeyModel.user_id == current_user.username
        )
    )
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Mark as inactive
    api_key.is_active = False
    await db.commit()
    
    return {"message": "API key revoked successfully", "key_id": key_id}


@router.get("/current", response_model=APIKeyResponse)
@auth_rate_limit("auth_token")
async def get_current_token(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's JWT token (from their session)
    This is useful for displaying the token in the UI
    """
    # Create a session-based API key that expires with the current session
    from datetime import timedelta
    
    key_data = create_api_key_token(
        user_id=current_user.username,
        key_name="Session Token",
        permissions=["api:access", "ai:access"] if "ai-api-access" in current_user.roles else ["api:access"]
    )
    
    # Return the current session token info
    return APIKeyResponse(
        key_id="session",
        api_key=key_data["token"],
        name="Session Token",
        created_at=datetime.utcnow().isoformat(),
        expires_at=key_data["expires_at"],
        permissions=key_data["permissions"]
    )