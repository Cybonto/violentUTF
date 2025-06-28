"""
APISIX Admin API proxy endpoints with proper authentication and authorization.
This module provides secure access to APISIX admin functions for authorized users.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, List, Optional, Any
import httpx
import os
import logging
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.models.auth import User
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apisix-admin", tags=["apisix-admin"])

# APISIX Admin configuration
APISIX_ADMIN_URL = settings.APISIX_ADMIN_URL
APISIX_ADMIN_KEY = settings.APISIX_ADMIN_KEY


class PluginConfig(BaseModel):
    """Model for plugin configuration"""

    plugin_name: str
    config: Dict[str, Any]


class RouteUpdate(BaseModel):
    """Model for route update request"""

    route_id: str
    plugins: Dict[str, Dict[str, Any]]


class AIPromptGuardConfig(BaseModel):
    """Configuration for ai-prompt-guard plugin"""

    deny_patterns: Optional[List[str]] = Field(default=[], description="Patterns to deny")
    allow_patterns: Optional[List[str]] = Field(default=[], description="Patterns to allow")
    deny_message: Optional[str] = Field(default="Request blocked by policy", description="Message when denied")
    case_insensitive: Optional[bool] = Field(default=True, description="Case insensitive matching")


class AIPromptDecoratorConfig(BaseModel):
    """Configuration for ai-prompt-decorator plugin"""

    prefix: Optional[str] = Field(default="", description="Text to prepend to prompts")
    suffix: Optional[str] = Field(default="", description="Text to append to prompts")
    system: Optional[str] = Field(default="", description="System prompt for chat models")
    template: Optional[str] = Field(default="", description="Template with {prompt} placeholder")


def get_apisix_admin_key():
    """Get APISIX admin key from settings"""
    return APISIX_ADMIN_KEY if APISIX_ADMIN_KEY else None


def check_admin_permission(user: User) -> bool:
    """Check if user has admin permissions for APISIX management"""
    # Check for admin role or specific permission
    if hasattr(user, "roles"):
        return "admin" in user.roles or "apisix-admin" in user.roles

    # For MVP, allow authenticated users with specific username
    allowed_users = ["admin", "violentutf.web", "keycloak_user"]
    return user.username in allowed_users


@router.get("/routes", response_model=Dict[str, Any])
async def get_ai_routes(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get all AI-related routes from APISIX.
    Only returns routes with ai-proxy plugin or /ai/ prefix.
    """
    if not check_admin_permission(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to access APISIX admin functions"
        )

    # Check admin key
    admin_key = get_apisix_admin_key()
    if not admin_key:
        logger.error("APISIX admin key not configured")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="APISIX admin key not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{APISIX_ADMIN_URL}/apisix/admin/routes", headers={"X-API-KEY": admin_key}, timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"Failed to get routes: {response.status_code}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to retrieve routes from APISIX"
                )

            data = response.json()
            all_routes = data.get("list", [])

            # Filter AI routes
            ai_routes = []
            for route in all_routes:
                plugins = route.get("value", {}).get("plugins", {})
                uri = route.get("value", {}).get("uri", "")

                if "ai-proxy" in plugins or "/ai/" in uri:
                    ai_routes.append(route)

            return {"list": ai_routes}

    except httpx.TimeoutException:
        logger.error("Timeout connecting to APISIX admin API")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Timeout connecting to APISIX admin API"
        )
    except Exception as e:
        logger.error(f"Error getting routes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error retrieving routes: {str(e)}"
        )


@router.get("/routes/{route_id}", response_model=Dict[str, Any])
async def get_route(route_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get specific route configuration from APISIX."""
    if not check_admin_permission(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to access APISIX admin functions"
        )

    admin_key = get_apisix_admin_key()
    if not admin_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="APISIX admin key not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{APISIX_ADMIN_URL}/apisix/admin/routes/{route_id}", headers={"X-API-KEY": admin_key}, timeout=10.0
            )

            if response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Route {route_id} not found")

            return response.json()

    except Exception as e:
        logger.error(f"Error getting route {route_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error retrieving route: {str(e)}"
        )


@router.put("/routes/{route_id}/plugins", response_model=Dict[str, Any])
async def update_route_plugins(
    route_id: str, route_config: Dict[str, Any], current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Update plugins configuration for a specific route.
    This endpoint allows updating the entire route configuration including plugins.
    """
    if not check_admin_permission(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions to modify APISIX configurations"
        )

    admin_key = get_apisix_admin_key()
    if not admin_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="APISIX admin key not configured")

    try:
        # Validate that we're only updating AI routes
        if "plugins" in route_config:
            plugins = route_config["plugins"]
            uri = route_config.get("uri", "")

            # Ensure this is an AI route
            if "ai-proxy" not in plugins and "/ai/" not in uri:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Can only update AI-related routes through this endpoint",
                )

        # Update the route
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{APISIX_ADMIN_URL}/apisix/admin/routes/{route_id}",
                headers={"X-API-KEY": admin_key, "Content-Type": "application/json"},
                json=route_config,
                timeout=10.0,
            )

            if response.status_code not in [200, 201]:
                logger.error(f"Failed to update route: {response.status_code} - {response.text}")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to update route in APISIX")

            logger.info(f"Successfully updated route {route_id} by user {current_user.username}")
            return response.json()

    except httpx.TimeoutException:
        logger.error("Timeout updating route in APISIX")
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Timeout updating route in APISIX")
    except Exception as e:
        logger.error(f"Error updating route {route_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating route: {str(e)}")


@router.post("/routes/{route_id}/plugins/ai-prompt-guard", response_model=Dict[str, Any])
async def configure_prompt_guard(
    route_id: str, config: AIPromptGuardConfig, current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Configure ai-prompt-guard plugin for a specific route.
    This is a convenience endpoint for updating just the prompt guard plugin.
    """
    if not check_admin_permission(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Get current route configuration
    route_data = await get_route(route_id, current_user)
    route_config = route_data.get("node", {}).get("value", {})

    if not route_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Route {route_id} not found")

    # Update plugins
    if "plugins" not in route_config:
        route_config["plugins"] = {}

    # Add or update ai-prompt-guard plugin
    route_config["plugins"]["ai-prompt-guard"] = config.dict(exclude_unset=True)

    # Update the route
    return await update_route_plugins(route_id, route_config, current_user)


@router.post("/routes/{route_id}/plugins/ai-prompt-decorator", response_model=Dict[str, Any])
async def configure_prompt_decorator(
    route_id: str, config: AIPromptDecoratorConfig, current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Configure ai-prompt-decorator plugin for a specific route.
    This is a convenience endpoint for updating just the prompt decorator plugin.
    """
    if not check_admin_permission(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Get current route configuration
    route_data = await get_route(route_id, current_user)
    route_config = route_data.get("node", {}).get("value", {})

    if not route_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Route {route_id} not found")

    # Update plugins
    if "plugins" not in route_config:
        route_config["plugins"] = {}

    # Add or update ai-prompt-decorator plugin
    route_config["plugins"]["ai-prompt-decorator"] = config.dict(exclude_unset=True)

    # Update the route
    return await update_route_plugins(route_id, route_config, current_user)


@router.delete("/routes/{route_id}/plugins/{plugin_name}")
async def remove_plugin(
    route_id: str, plugin_name: str, current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Remove a specific plugin from a route."""
    if not check_admin_permission(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    # Validate plugin name
    allowed_plugins = ["ai-prompt-guard", "ai-prompt-decorator"]
    if plugin_name not in allowed_plugins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plugin {plugin_name} cannot be removed through this endpoint",
        )

    # Get current route configuration
    route_data = await get_route(route_id, current_user)
    route_config = route_data.get("node", {}).get("value", {})

    if not route_config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Route {route_id} not found")

    # Remove plugin
    if "plugins" in route_config and plugin_name in route_config["plugins"]:
        del route_config["plugins"][plugin_name]

        # Update the route
        return await update_route_plugins(route_id, route_config, current_user)
    else:
        return {"message": f"Plugin {plugin_name} not found on route {route_id}"}
