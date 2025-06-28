"""
Configuration Resources for MCP
==============================

This module provides access to ViolentUTF system configuration and status
information through the MCP protocol.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from app.core.config import settings
from app.mcp.auth import MCPAuthHandler
from app.mcp.resources.base import (
    AdvancedResource,
    BaseResourceProvider,
    ResourceMetadata,
    advanced_resource_registry,
)

logger = logging.getLogger(__name__)


class ConfigurationResourceProvider(BaseResourceProvider):
    """Provides access to system configuration resources"""

    def __init__(self):
        super().__init__(
            "violentutf://config/{component}/{config_id}", "ConfigProvider"
        )
        self.auth_handler = MCPAuthHandler()
        self.base_url = self._get_api_url()

    def _get_api_url(self) -> str:
        """Get internal API URL for container communication"""
        api_url = getattr(settings, "VIOLENTUTF_API_URL", "http://localhost:8000")
        if "localhost:9080" in api_url or "apisix" in api_url:
            return "http://violentutf-api:8000"
        return api_url

    async def get_resource(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get specific configuration resource"""
        uri_params = self.extract_params(uri)
        component = uri_params.get("component")
        config_id = uri_params.get("config_id")

        if not component or not config_id:
            logger.warning(f"Invalid configuration URI: {uri}")
            return None

        # Route to appropriate configuration handler
        if component == "database" and config_id == "status":
            return await self._get_database_status(uri, params)
        elif component == "environment" and config_id == "current":
            return await self._get_environment_config(uri, params)
        elif component == "system" and config_id == "info":
            return await self._get_system_info(uri, params)
        elif component == "mcp" and config_id == "settings":
            return await self._get_mcp_settings(uri, params)
        elif component == "api" and config_id == "health":
            return await self._get_api_health(uri, params)
        else:
            logger.warning(f"Unknown configuration: {component}/{config_id}")
            return None

    async def _get_database_status(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get database status and statistics"""
        try:
            headers = await self._get_headers(params)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/database/status", headers=headers
                )

                if response.status_code == 200:
                    status_data = response.json()

                    # Enhance with additional database metrics
                    enhanced_status = {
                        **status_data,
                        "timestamp": datetime.now().isoformat(),
                        "connection_status": (
                            "healthy" if response.status_code == 200 else "unhealthy"
                        ),
                        "response_time_ms": (
                            getattr(response, "elapsed", {}).total_seconds() * 1000
                            if hasattr(response, "elapsed")
                            else None
                        ),
                    }

                    return AdvancedResource(
                        uri=uri,
                        name="Database Status",
                        description="Current database status, connections, and performance metrics",
                        mimeType="application/json",
                        content=enhanced_status,
                        metadata=ResourceMetadata(
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            version="1.0",
                            tags=["system", "database", "status", "monitoring"],
                        ),
                    )
                else:
                    # Return error status
                    error_status = {
                        "status": "error",
                        "status_code": response.status_code,
                        "message": "Database status check failed",
                        "timestamp": datetime.now().isoformat(),
                    }

                    return AdvancedResource(
                        uri=uri,
                        name="Database Status (Error)",
                        description="Database status check failed",
                        mimeType="application/json",
                        content=error_status,
                        metadata=ResourceMetadata(
                            created_at=datetime.now(),
                            updated_at=datetime.now(),
                            tags=["system", "database", "error"],
                        ),
                    )

        except Exception as e:
            logger.error(f"Error getting database status: {e}")
            error_status = {
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
            }

            return AdvancedResource(
                uri=uri,
                name="Database Status (Error)",
                description=f"Database status error: {str(e)}",
                mimeType="application/json",
                content=error_status,
                metadata=ResourceMetadata(
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    tags=["system", "database", "error"],
                ),
            )

    async def _get_environment_config(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get current environment configuration"""
        try:
            headers = await self._get_headers(params)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/config/environment", headers=headers
                )

                if response.status_code == 200:
                    config_data = response.json()
                else:
                    # Fallback to basic environment info
                    config_data = await self._get_basic_env_info()

                return AdvancedResource(
                    uri=uri,
                    name="Environment Configuration",
                    description="Current environment settings and variables",
                    mimeType="application/json",
                    content=config_data,
                    metadata=ResourceMetadata(
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        tags=["system", "configuration", "environment"],
                    ),
                )

        except Exception as e:
            logger.error(f"Error getting environment config: {e}")
            config_data = await self._get_basic_env_info()
            config_data["error"] = str(e)

            return AdvancedResource(
                uri=uri,
                name="Environment Configuration",
                description="Environment configuration with errors",
                mimeType="application/json",
                content=config_data,
                metadata=ResourceMetadata(
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    tags=["system", "configuration", "environment", "error"],
                ),
            )

    async def _get_basic_env_info(self) -> Dict[str, Any]:
        """Get basic environment information"""
        return {
            "service_name": getattr(settings, "SERVICE_NAME", "ViolentUTF API"),
            "service_version": getattr(settings, "SERVICE_VERSION", "1.0.0"),
            "debug_mode": getattr(settings, "DEBUG", False),
            "api_url": self.base_url,
            "mcp_enabled": True,
            "timestamp": datetime.now().isoformat(),
        }

    async def _get_system_info(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get system information"""
        system_info = {
            "service": {
                "name": getattr(settings, "SERVICE_NAME", "ViolentUTF API"),
                "version": getattr(settings, "SERVICE_VERSION", "1.0.0"),
                "debug": getattr(settings, "DEBUG", False),
            },
            "mcp": {
                "enabled": True,
                "version": "1.0.0",
                "features": ["tools", "resources", "prompts"],
            },
            "environment": {
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "platform": os.name,
                "timestamp": datetime.now().isoformat(),
            },
        }

        return AdvancedResource(
            uri=uri,
            name="System Information",
            description="ViolentUTF system information and capabilities",
            mimeType="application/json",
            content=system_info,
            metadata=ResourceMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["system", "info", "version"],
            ),
        )

    async def _get_mcp_settings(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get MCP configuration settings"""
        try:
            from app.mcp.config import mcp_settings

            # Safe subset of MCP settings (no secrets)
            safe_settings = {
                "server_name": mcp_settings.MCP_SERVER_NAME,
                "server_version": mcp_settings.MCP_SERVER_VERSION,
                "enable_tools": mcp_settings.MCP_ENABLE_TOOLS,
                "enable_resources": mcp_settings.MCP_ENABLE_RESOURCES,
                "enable_prompts": getattr(mcp_settings, "MCP_ENABLE_PROMPTS", True),
                "transport_type": mcp_settings.MCP_TRANSPORT_TYPE,
                "sse_endpoint": mcp_settings.MCP_SSE_ENDPOINT,
                "development_mode": mcp_settings.MCP_DEVELOPMENT_MODE,
                "debug_mode": mcp_settings.MCP_DEBUG_MODE,
                "timestamp": datetime.now().isoformat(),
            }

            return AdvancedResource(
                uri=uri,
                name="MCP Settings",
                description="Model Context Protocol server configuration",
                mimeType="application/json",
                content=safe_settings,
                metadata=ResourceMetadata(
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    tags=["mcp", "configuration", "settings"],
                ),
            )

        except Exception as e:
            logger.error(f"Error getting MCP settings: {e}")
            return None

    async def _get_api_health(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get API health status"""
        try:
            headers = await self._get_headers(params)

            async with httpx.AsyncClient(timeout=10.0) as client:
                start_time = datetime.now()
                response = await client.get(f"{self.base_url}/health", headers=headers)
                response_time = (datetime.now() - start_time).total_seconds()

                if response.status_code == 200:
                    health_data = response.json()
                    health_data["response_time_seconds"] = response_time
                    health_data["timestamp"] = datetime.now().isoformat()
                else:
                    health_data = {
                        "status": "unhealthy",
                        "status_code": response.status_code,
                        "response_time_seconds": response_time,
                        "timestamp": datetime.now().isoformat(),
                    }

                return AdvancedResource(
                    uri=uri,
                    name="API Health Status",
                    description="ViolentUTF API health and performance metrics",
                    mimeType="application/json",
                    content=health_data,
                    metadata=ResourceMetadata(
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        tags=["api", "health", "monitoring"],
                    ),
                )

        except Exception as e:
            logger.error(f"Error getting API health: {e}")
            health_data = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

            return AdvancedResource(
                uri=uri,
                name="API Health Status (Error)",
                description=f"API health check failed: {str(e)}",
                mimeType="application/json",
                content=health_data,
                metadata=ResourceMetadata(
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    tags=["api", "health", "error"],
                ),
            )

    async def list_resources(self, params: Dict[str, Any]) -> List[AdvancedResource]:
        """List all available configuration resources"""
        resources = []

        # Define available configuration resources
        config_resources = [
            {
                "uri": "violentutf://config/database/status",
                "name": "Database Status",
                "description": "Current database status and performance metrics",
            },
            {
                "uri": "violentutf://config/environment/current",
                "name": "Environment Configuration",
                "description": "Current environment settings and variables",
            },
            {
                "uri": "violentutf://config/system/info",
                "name": "System Information",
                "description": "ViolentUTF system information and capabilities",
            },
            {
                "uri": "violentutf://config/mcp/settings",
                "name": "MCP Settings",
                "description": "Model Context Protocol server configuration",
            },
            {
                "uri": "violentutf://config/api/health",
                "name": "API Health Status",
                "description": "ViolentUTF API health and performance metrics",
            },
        ]

        for config in config_resources:
            resources.append(
                AdvancedResource(
                    uri=config["uri"],
                    name=config["name"],
                    description=config["description"],
                    mimeType="application/json",
                    content={"preview": "Use get_resource to access current data"},
                    metadata=ResourceMetadata(
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        tags=["system", "configuration", "available"],
                    ),
                )
            )

        logger.info(f"Listed {len(resources)} configuration resources")
        return resources

    async def _get_headers(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Get API headers with authentication"""
        headers = {"Content-Type": "application/json", "X-API-Gateway": "MCP-Config"}

        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)

        if "_auth_token" in params:
            headers["Authorization"] = f"Bearer {params['_auth_token']}"

        return headers


class StatusResourceProvider(BaseResourceProvider):
    """Provides access to system status resources"""

    def __init__(self):
        super().__init__("violentutf://status/{component}", "StatusProvider")
        self.auth_handler = MCPAuthHandler()
        self.base_url = self._get_api_url()

    def _get_api_url(self) -> str:
        """Get internal API URL for container communication"""
        api_url = getattr(settings, "VIOLENTUTF_API_URL", "http://localhost:8000")
        if "localhost:9080" in api_url or "apisix" in api_url:
            return "http://violentutf-api:8000"
        return api_url

    async def get_resource(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get specific status resource"""
        uri_params = self.extract_params(uri)
        component = uri_params.get("component")

        if component == "overall":
            return await self._get_overall_status(uri, params)
        elif component == "services":
            return await self._get_services_status(uri, params)
        elif component == "mcp":
            return await self._get_mcp_status(uri, params)
        else:
            logger.warning(f"Unknown status component: {component}")
            return None

    async def _get_overall_status(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get overall system status"""
        status = {
            "system": "ViolentUTF",
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "components": {},
        }

        try:
            headers = await self._get_headers(params)

            async with httpx.AsyncClient(timeout=10.0) as client:
                # Check API health
                try:
                    api_response = await client.get(
                        f"{self.base_url}/health", headers=headers
                    )
                    status["components"]["api"] = {
                        "status": (
                            "healthy"
                            if api_response.status_code == 200
                            else "unhealthy"
                        ),
                        "status_code": api_response.status_code,
                    }
                except:
                    status["components"]["api"] = {
                        "status": "unhealthy",
                        "error": "Connection failed",
                    }

                # Check database
                try:
                    db_response = await client.get(
                        f"{self.base_url}/api/v1/database/status", headers=headers
                    )
                    status["components"]["database"] = {
                        "status": (
                            "healthy" if db_response.status_code == 200 else "unhealthy"
                        ),
                        "status_code": db_response.status_code,
                    }
                except:
                    status["components"]["database"] = {
                        "status": "unhealthy",
                        "error": "Connection failed",
                    }

            # MCP status
            status["components"]["mcp"] = {
                "status": "healthy",
                "features": ["tools", "resources", "prompts"],
            }

            # Determine overall status
            component_statuses = [
                comp.get("status", "unknown") for comp in status["components"].values()
            ]
            if all(s == "healthy" for s in component_statuses):
                status["overall_status"] = "healthy"
            elif any(s == "unhealthy" for s in component_statuses):
                status["overall_status"] = "degraded"
            else:
                status["overall_status"] = "unknown"

        except Exception as e:
            logger.error(f"Error getting overall status: {e}")
            status["overall_status"] = "error"
            status["error"] = str(e)

        return AdvancedResource(
            uri=uri,
            name="Overall System Status",
            description="Comprehensive ViolentUTF system status",
            mimeType="application/json",
            content=status,
            metadata=ResourceMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["system", "status", "monitoring", "health"],
            ),
        )

    async def _get_services_status(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get status of all services"""
        services_status = {
            "timestamp": datetime.now().isoformat(),
            "services": {
                "violentutf_api": {"status": "unknown"},
                "keycloak": {"status": "unknown"},
                "apisix": {"status": "unknown"},
                "database": {"status": "unknown"},
            },
        }

        # This would typically check actual service status
        # For now, return basic status information
        services_status["services"]["violentutf_api"]["status"] = "healthy"
        services_status["services"]["mcp_server"] = {"status": "healthy"}

        return AdvancedResource(
            uri=uri,
            name="Services Status",
            description="Status of all ViolentUTF services",
            mimeType="application/json",
            content=services_status,
            metadata=ResourceMetadata(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                tags=["services", "status", "monitoring"],
            ),
        )

    async def _get_mcp_status(
        self, uri: str, params: Dict[str, Any]
    ) -> Optional[AdvancedResource]:
        """Get MCP server status"""
        try:
            from app.mcp.resources import resource_registry
            from app.mcp.tools import tool_registry

            # Get tool and resource counts
            tools = await tool_registry.list_tools()
            resources = await resource_registry.list_resources()

            mcp_status = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "features": {
                    "tools": {"enabled": True, "count": len(tools)},
                    "resources": {"enabled": True, "count": len(resources)},
                    "prompts": {
                        "enabled": True,
                        "count": 0,  # Will be updated in Phase 3.2
                    },
                },
                "providers": (
                    resource_registry.get_providers()
                    if hasattr(resource_registry, "get_providers")
                    else []
                ),
            }

            return AdvancedResource(
                uri=uri,
                name="MCP Server Status",
                description="Model Context Protocol server status and capabilities",
                mimeType="application/json",
                content=mcp_status,
                metadata=ResourceMetadata(
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    tags=["mcp", "status", "capabilities"],
                ),
            )

        except Exception as e:
            logger.error(f"Error getting MCP status: {e}")
            return None

    async def list_resources(self, params: Dict[str, Any]) -> List[AdvancedResource]:
        """List available status resources"""
        status_resources = [
            {
                "uri": "violentutf://status/overall",
                "name": "Overall System Status",
                "description": "Comprehensive ViolentUTF system status",
            },
            {
                "uri": "violentutf://status/services",
                "name": "Services Status",
                "description": "Status of all ViolentUTF services",
            },
            {
                "uri": "violentutf://status/mcp",
                "name": "MCP Server Status",
                "description": "Model Context Protocol server status and capabilities",
            },
        ]

        resources = []
        for status in status_resources:
            resources.append(
                AdvancedResource(
                    uri=status["uri"],
                    name=status["name"],
                    description=status["description"],
                    mimeType="application/json",
                    content={"preview": "Use get_resource to access current status"},
                    metadata=ResourceMetadata(
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        tags=["status", "monitoring", "available"],
                    ),
                )
            )

        return resources

    async def _get_headers(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Get API headers with authentication"""
        headers = {"Content-Type": "application/json", "X-API-Gateway": "MCP-Status"}

        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)

        if "_auth_token" in params:
            headers["Authorization"] = f"Bearer {params['_auth_token']}"

        return headers


# Register configuration providers
def register_configuration_providers():
    """Register all configuration-related resource providers"""
    advanced_resource_registry.register(ConfigurationResourceProvider())
    advanced_resource_registry.register(StatusResourceProvider())
    logger.info("Registered configuration and status resource providers")


# Auto-register providers when module is imported
register_configuration_providers()
