# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
MCP Resources Module - Enhanced.

==============================

This module provides access to ViolentUTF resources through the MCP protocol
with enhanced features including advanced resource providers, caching, and metadata.
"""

import logging
from typing import Any, Dict, List

# Import resource providers to auto-register them
from app.mcp.resources import configuration, datasets
from app.mcp.resources.base import advanced_resource_registry
from app.mcp.resources.manager import resource_manager
from mcp.types import Resource

logger = logging.getLogger(__name__)


class ResourceRegistry:
    """Registry for MCP resources with ViolentUTF integration."""

    def __init__(self) -> None:
        """Initialize the instance."""
        self.manager = resource_manager
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize resource registry."""
        if self._initialized:
            return

        logger.info("Initializing MCP resource registry...")

        # Clear any existing cache
        self.manager.clear_cache()

        # Test resource manager connectivity
        try:
            resources = await self.manager.list_resources()
            logger.info(f"Successfully initialized resource registry with {len(resources)} resources")
        except Exception as e:
            logger.warning(f"Resource manager initialization test failed: {e}")
            logger.info("Resource registry initialized (resources may be unavailable)")

        self._initialized = True
        logger.info("MCP resource registry initialized")

    async def list_resources(self) -> List[Resource]:
        """List all available resources."""
        if not self._initialized:
            await self.initialize()

        try:
            resources = await self.manager.list_resources()
            logger.debug(f"Listed {len(resources)} resources")
            return resources
        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            return []

    async def read_resource(self, uri: str) -> Any:
        """Read a resource by URI."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self.manager.read_resource(uri)
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            return {"error": "resource_read_failed", "message": str(e), "uri": uri}

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive resource cache statistics."""
        return self.manager.get_cache_stats()

    def clear_cache(self) -> None:
        """Clear resource cache."""
        self.manager.clear_cache()

    def get_providers(self) -> List[str]:
        """Get list of registered resource providers."""
        return advanced_resource_registry.get_providers()

    async def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary of all available resources."""
        return await self.manager.get_resource_summary()


# Create global resource registry
resource_registry = ResourceRegistry()

__all__ = ["resource_registry", "resource_manager", "advanced_resource_registry"]
