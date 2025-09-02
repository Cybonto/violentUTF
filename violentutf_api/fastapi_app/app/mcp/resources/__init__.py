# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP Resources Module - Enhanced

==============================

This module provides access to ViolentUTF resources through the MCP protocol
with enhanced features including advanced resource providers, caching, and metadata.
"""
import logging
from typing import Any, Dict, List, Optional, Self, cast

# Import resource providers to auto-register them
from app.mcp.resources import configuration, datasets  # noqa: F401
from app.mcp.resources.base import advanced_resource_registry
from app.mcp.resources.manager import resource_manager
from mcp.types import Resource

logger = logging.getLogger(__name__)


class ResourceRegistry:
    """Registry for MCP resources with ViolentUTF integration."""

    def __init__(self: "Self") -> None:

        self.manager = resource_manager
        self._initialized = False

    async def initialize(self: "Self") -> None:
        """Initialize resource registry."""
        if self._initialized:

            return

        logger.info("Initializing MCP resource registry...")

        # Clear any existing cache
        self.manager.clear_cache()

        # Test resource manager connectivity
        try:
            resources = await self.manager.list_resources()
            logger.info(
                "Successfully initialized resource registry with %s resources",
                len(resources),
            )
        except Exception as e:
            logger.warning("Resource manager initialization test failed: %s", e)
            logger.info("Resource registry initialized (resources may be unavailable)")

        self._initialized = True
        logger.info("MCP resource registry initialized")

    async def list_resources(self: "Self") -> List[Resource]:
        """List all available resources."""
        if not self._initialized:

            await self.initialize()

        try:
            resources = await self.manager.list_resources()
            logger.debug("Listed %s resources", len(resources))
            return cast(List[Any], resources)
        except Exception as e:
            logger.error("Error listing resources: %s", e)
            return []

    async def read_resource(self: "Self", uri: str) -> Optional[Dict[str, Any]]:
        """Read a resource by URI."""
        if not self._initialized:

            await self.initialize()

        try:
            return await self.manager.read_resource(uri)
        except Exception as e:
            logger.error("Error reading resource %s: %s", uri, e)
            return {"error": "resource_read_failed", "message": str(e), "uri": uri}

    def get_cache_stats(self: "Self") -> Dict[str, Any]:
        """Get comprehensive resource cache statistics."""
        return self.manager.get_cache_stats()

    def clear_cache(self: "Self") -> None:
        """Clear resource cache."""
        self.manager.clear_cache()

    def get_providers(self: "Self") -> List[str]:
        """Get list of registered resource providers."""
        return advanced_resource_registry.get_providers()

    async def get_resource_summary(self: "Self") -> Dict[str, Any]:
        """Get summary of all available resources."""
        return await self.manager.get_resource_summary()


# Create global resource registry
resource_registry = ResourceRegistry()

__all__ = ["resource_registry", "resource_manager", "advanced_resource_registry"]
