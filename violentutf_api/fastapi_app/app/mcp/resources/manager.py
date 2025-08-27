# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
MCP Resource Manager - Enhanced Provides access to ViolentUTF resources
======================================================================

This module manages ViolentUTF resources for MCP access with enhanced
features including advanced resource providers, caching, and metadata.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from urllib.parse import urljoin

import httpx
from app.core.config import settings
from app.mcp.auth import MCPAuthHandler
from app.mcp.resources.base import advanced_resource_registry
from mcp.types import Resource
from pydantic import AnyUrl

logger = logging.getLogger(__name__)


class ViolentUTFResourceManager:
    """Manages ViolentUTF resources for MCP access"""

    def __init__(self):
        self.base_url = settings.VIOLENTUTF_API_URL or "http://localhost:8000"
        # Use internal URL for direct API access from within container
        if "localhost:9080" in self.base_url:
            self.base_url = "http://violentutf-api:8000"

        self.auth_handler = MCPAuthHandler()
        self.resource_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes

    async def list_resources(self) -> List[Resource]:
        """List all available resources using advanced resource registry"""
        try:
            # Initialize advanced resource registry
            await advanced_resource_registry.initialize()

            # Get advanced resources
            advanced_resources = await advanced_resource_registry.list_resources()

            # Convert to MCP resource format
            mcp_resources = []
            for adv_resource in advanced_resources:
                mcp_resource = Resource(
                    uri=AnyUrl(adv_resource.uri),
                    name=adv_resource.name,
                    description=adv_resource.description,
                    mimeType=adv_resource.mimeType,
                )
                mcp_resources.append(mcp_resource)

            # Also include legacy resources for backward compatibility
            legacy_resources = await self._list_legacy_resources()
            mcp_resources.extend(legacy_resources)

            logger.info(
                f"Listed {len(mcp_resources)} MCP resources ({len(advanced_resources)} advanced, "
                f"{len(legacy_resources)} legacy)"
            )
            return mcp_resources

        except (AttributeError, TypeError, KeyError) as e:
            # Handle errors from resource registry initialization or resource conversion
            logger.error("Error listing resources: %s", e)
            return []

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a specific resource by URI using advanced resource registry"""
        logger.info("Reading resource: %s", uri)

        try:
            # Initialize advanced resource registry
            await advanced_resource_registry.initialize()

            # Try to get resource from advanced registry first
            advanced_resource = await advanced_resource_registry.get_resource(uri)

            if advanced_resource:
                # Return advanced resource content
                logger.debug("Returning advanced resource: %s", uri)
                return {
                    "uri": advanced_resource.uri,
                    "name": advanced_resource.name,
                    "description": advanced_resource.description,
                    "mimeType": advanced_resource.mimeType,
                    "content": advanced_resource.content,
                    "metadata": advanced_resource.metadata.dict() if advanced_resource.metadata else None,
                }

            # Fallback to legacy resource handling
            logger.debug("Falling back to legacy resource handling for: %s", uri)
            return await self._read_legacy_resource(uri)

        except (AttributeError, TypeError, ValueError) as e:
            # Handle errors from advanced registry operations or resource parsing
            logger.error("Error reading resource %s: %s", uri, e)
            return {"error": "resource_read_failed", "message": str(e), "uri": uri}

    async def _read_legacy_resource(self, uri: str) -> Dict[str, Any]:
        """Read resource using legacy method for backward compatibility"""
        try:
            # Check cache first
            if uri in self.resource_cache:
                cached_data = self.resource_cache[uri]
                if datetime.now().timestamp() - cached_data["timestamp"] < self.cache_ttl:
                    logger.debug("Returning cached legacy resource: %s", uri)
                    return cast(Dict[str, Any], cached_data["data"])

            # Parse URI to determine resource type
            resource_type, resource_id = self._parse_resource_uri(uri)

            # Fetch resource data
            if resource_type == "generator":
                data = await self._read_generator_resource(resource_id)
            elif resource_type == "dataset":
                data = await self._read_dataset_resource(resource_id)
            elif resource_type == "orchestrator":
                data = await self._read_orchestrator_resource(resource_id)
            elif resource_type == "config":
                data = await self._read_config_resource(resource_id)
            elif resource_type == "session":
                data = await self._read_session_resource(resource_id)
            else:
                raise ValueError(f"Unknown resource type: {resource_type}")

            # Ensure data is not None before caching and returning
            if data is None:
                data = {"error": "resource_not_found", "resource_type": resource_type, "resource_id": resource_id}

            # Cache the result
            self.resource_cache[uri] = {"data": data, "timestamp": datetime.now().timestamp()}

            return data

        except (ValueError, KeyError, AttributeError) as e:
            # Handle URI parsing errors, resource type errors, and data access errors
            logger.error("Error reading legacy resource %s: %s", uri, e)
            return {"error": "legacy_resource_read_failed", "message": str(e), "uri": uri}

    def _parse_resource_uri(self, uri: str) -> tuple[str, str]:
        """Parse resource URI to extract type and ID"""
        # URI format: violentutf://resource_type/resource_id
        if not uri.startswith("violentutf://"):
            raise ValueError(f"Invalid resource URI format: {uri}")

        path = uri.replace("violentutf://", "")
        parts = path.split("/")

        if len(parts) < 2:
            raise ValueError(f"Invalid resource URI path: {uri}")

        return parts[0], "/".join(parts[1:])

    async def _list_legacy_resources(self) -> List[Resource]:
        """List legacy resources for backward compatibility"""
        legacy_resources = []

        try:
            # Generator resources
            generator_resources = await self._list_generator_resources()
            legacy_resources.extend(generator_resources)

            # Session resources (not covered by advanced providers yet)
            session_resources = await self._list_session_resources()
            legacy_resources.extend(session_resources)

        except (AttributeError, TypeError, ValueError) as e:
            # Handle errors from resource fetching and processing
            logger.error("Error listing legacy resources: %s", e)

        return legacy_resources

    async def _list_generator_resources(self) -> List[Resource]:
        """List generator configuration resources"""
        try:
            # Fetch generator configurations
            generators = await self._api_request("GET", "/api/v1/generators")

            resources = []
            if generators and "generators" in generators:
                for gen in generators["generators"]:
                    resource = Resource(
                        uri=AnyUrl(f"violentutf://generator/{gen['id']}"),
                        name=f"Generator: {gen['name']}",
                        description=f"Generator configuration for {gen['provider_type']} - {gen['model_name']}",
                        mimeType="application/json",
                    )
                    resources.append(resource)

            return resources

        except (KeyError, AttributeError, TypeError) as e:
            # Handle API response parsing errors and resource creation errors
            logger.error("Error listing generator resources: %s", e)
            return []

    async def _list_dataset_resources(self) -> List[Resource]:
        """List dataset resources"""
        try:
            # Fetch available datasets
            datasets = await self._api_request("GET", "/api/v1/datasets")

            resources = []
            if datasets and "datasets" in datasets:
                for dataset in datasets["datasets"]:
                    resource = Resource(
                        uri=AnyUrl(f"violentutf://dataset/{dataset['name']}"),
                        name=f"Dataset: {dataset['name']}",
                        description=f"Dataset with {dataset.get('size', 'unknown')} entries",
                        mimeType="application/json",
                    )
                    resources.append(resource)

            return resources

        except (KeyError, AttributeError, TypeError) as e:
            # Handle API response parsing errors and resource creation errors
            logger.error("Error listing dataset resources: %s", e)
            return []

    async def _list_orchestrator_resources(self) -> List[Resource]:
        """List orchestrator execution resources"""
        try:
            # Fetch orchestrator executions
            orchestrators = await self._api_request("GET", "/api/v1/orchestrators")

            resources = []
            if orchestrators and "orchestrators" in orchestrators:
                for orch in orchestrators["orchestrators"]:
                    resource = Resource(
                        uri=AnyUrl(f"violentutf://orchestrator/{orch['id']}"),
                        name=f"Orchestrator: {orch['name']}",
                        description=f"Orchestrator execution results - Status: {orch.get('status', 'unknown')}",
                        mimeType="application/json",
                    )
                    resources.append(resource)

            return resources

        except (KeyError, AttributeError, TypeError) as e:
            # Handle API response parsing errors and resource creation errors
            logger.error("Error listing orchestrator resources: %s", e)
            return []

    async def _list_config_resources(self) -> List[Resource]:
        """List configuration resources"""
        try:
            # Fetch system configuration
            config = await self._api_request("GET", "/api/v1/config")

            resources = []
            if config:
                resource = Resource(
                    uri=AnyUrl("violentutf://config/system"),
                    name="System Configuration",
                    description="ViolentUTF system configuration and settings",
                    mimeType="application/json",
                )
                resources.append(resource)

            return resources

        except (KeyError, AttributeError, TypeError) as e:
            # Handle API response parsing errors and resource creation errors
            logger.error("Error listing config resources: %s", e)
            return []

    async def _list_session_resources(self) -> List[Resource]:
        """List session resources"""
        try:
            # Fetch active sessions
            sessions = await self._api_request("GET", "/api/v1/sessions")

            resources = []
            if sessions and "sessions" in sessions:
                for session in sessions["sessions"]:
                    resource = Resource(
                        uri=AnyUrl(f"violentutf://session/{session['id']}"),
                        name=f"Session: {session['name']}",
                        description=f"Session data - Created: {session.get('created_at', 'unknown')}",
                        mimeType="application/json",
                    )
                    resources.append(resource)

            return resources

        except (KeyError, AttributeError, TypeError) as e:
            # Handle API response parsing errors and resource creation errors
            logger.error("Error listing session resources: %s", e)
            return []

    async def _read_generator_resource(self, generator_id: str) -> Optional[Dict[str, Any]]:
        """Read generator configuration details"""
        return await self._api_request("GET", f"/api/v1/generators/{generator_id}")

    async def _read_dataset_resource(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Read dataset details"""
        return await self._api_request("GET", f"/api/v1/datasets/{dataset_name}")

    async def _read_orchestrator_resource(self, orchestrator_id: str) -> Optional[Dict[str, Any]]:
        """Read orchestrator execution details"""
        return await self._api_request("GET", f"/api/v1/orchestrators/{orchestrator_id}")

    async def _read_config_resource(self, config_type: str) -> Dict[str, Any]:
        """Read configuration details"""
        if config_type == "system":
            result = await self._api_request("GET", "/api/v1/config")
        else:
            result = await self._api_request("GET", f"/api/v1/config/{config_type}")

        return result or {"error": "config_not_found", "config_type": config_type}

    async def _read_session_resource(self, session_id: str) -> Dict[str, Any]:
        """Read session details"""
        result = await self._api_request("GET", f"/api/v1/sessions/{session_id}")
        return result or {"error": "session_not_found", "session_id": session_id}

    async def _api_request(self, method: str, path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make authenticated API request"""
        headers = {"Content-Type": "application/json", "X-API-Gateway": "MCP-Resource"}

        # Add authentication headers if available
        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)

        url = urljoin(self.base_url, path)
        timeout = 30.0

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(method=method, url=url, headers=headers, **kwargs)

                logger.debug("MCP Resource API call: %s %s -> %s", method, url, response.status_code)

                if response.status_code >= 400:
                    logger.warning("API error %s: %s", response.status_code, response.text)
                    return None

                result = response.json()
                return cast(Optional[Dict[str, Any]], result)

            except httpx.TimeoutException:
                logger.error("Timeout on API call: %s", url)
                return None
            except httpx.ConnectError:
                logger.error("Connection error on API call: %s", url)
                return None
            except (ValueError, OSError) as e:
                # Handle JSON parsing errors and other network/system errors
                logger.error("Unexpected error on API call %s: %s", url, e)
                return None

    def clear_cache(self):
        """Clear resource cache"""
        self.resource_cache.clear()
        # Also clear advanced registry caches
        advanced_resource_registry.clear_all_caches()
        logger.info("Resource cache cleared (legacy and advanced)")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        current_time = datetime.now().timestamp()
        valid_entries = 0
        expired_entries = 0

        for uri, cached_data in self.resource_cache.items():
            if current_time - cached_data["timestamp"] < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1

        legacy_stats = {
            "total_entries": len(self.resource_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_seconds": self.cache_ttl,
        }

        # Get advanced provider stats
        advanced_stats = advanced_resource_registry.get_provider_stats()

        return {
            "legacy_cache": legacy_stats,
            "advanced_providers": advanced_stats,
            "total_providers": len(advanced_stats),
            "providers_list": advanced_resource_registry.get_providers(),
        }

    def get_providers_info(self) -> Dict[str, Any]:
        """Get information about registered resource providers"""
        try:
            providers = advanced_resource_registry.get_providers()
            provider_stats = advanced_resource_registry.get_provider_stats()

            return {"total_providers": len(providers), "providers": providers, "provider_details": provider_stats}
        except (AttributeError, TypeError) as e:
            # Handle errors from advanced resource registry operations
            logger.error("Error getting providers info: %s", e)
            return {"error": str(e)}

    async def get_resource_summary(self) -> Dict[str, Any]:
        """Get summary of all available resources"""
        try:
            await advanced_resource_registry.initialize()

            # Get all resources
            all_resources = await advanced_resource_registry.list_resources()

            # Categorize resources
            categories: Dict[str, List[Dict[str, str]]] = {}
            for resource in all_resources:
                category = resource.uri.split("://")[1].split("/")[0] if "://" in resource.uri else "unknown"
                if category not in categories:
                    categories[category] = []
                categories[category].append(
                    {"uri": resource.uri, "name": resource.name, "description": resource.description}
                )

            summary = {
                "total_resources": len(all_resources),
                "categories": {cat: len(resources) for cat, resources in categories.items()},
                "category_details": categories,
                "providers": self.get_providers_info(),
            }

            return summary

        except (AttributeError, TypeError, KeyError) as e:
            # Handle errors from resource registry operations and data processing
            logger.error("Error getting resource summary: %s", e)
            return {"error": str(e)}


# Global resource manager instance
resource_manager = ViolentUTFResourceManager()
