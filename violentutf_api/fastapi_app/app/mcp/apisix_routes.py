"""APISIX Route Configuration for MCP"""
import httpx
from typing import Dict, Any
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class APISIXRouteManager:
    """Manages APISIX routes for MCP endpoints"""
    
    def __init__(self):
        self.admin_url = settings.APISIX_ADMIN_URL
        self.admin_key = settings.APISIX_ADMIN_KEY
        
    async def create_mcp_routes(self) -> Dict[str, Any]:
        """Create all required MCP routes in APISIX"""
        routes = []
        
        # Main MCP route
        main_route = await self._create_route(
            route_id="mcp-main",
            uri="/mcp/*",
            upstream_url=f"http://violentutf-api:8000",
            plugins={
                "cors": {
                    "allow_origins": "*",
                    "allow_methods": "GET,POST,PUT,DELETE,OPTIONS",
                    "allow_headers": "Authorization,Content-Type"
                },
                "jwt-auth": {
                    "key": "user-key",
                    "secret": settings.JWT_SECRET_KEY,
                    "algorithm": "HS256"
                },
                "limit-req": {
                    "rate": 100,
                    "burst": 20,
                    "key": "remote_addr"
                },
                "prometheus": {
                    "prefer_name": True
                }
            }
        )
        routes.append(main_route)
        
        # OAuth callback route (no JWT required)
        oauth_route = await self._create_route(
            route_id="mcp-oauth",
            uri="/mcp/oauth/*",
            upstream_url=f"http://violentutf-api:8000",
            plugins={
                "cors": {
                    "allow_origins": "*"
                },
                "limit-req": {
                    "rate": 10,
                    "burst": 5
                }
            }
        )
        routes.append(oauth_route)
        
        return {"routes": routes, "status": "created"}
        
    async def _create_route(
        self, 
        route_id: str, 
        uri: str, 
        upstream_url: str,
        plugins: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create individual route in APISIX"""
        route_config = {
            "uri": uri,
            "upstream": {
                "type": "roundrobin",
                "nodes": {
                    upstream_url: 1
                }
            },
            "plugins": plugins
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.admin_url}/routes/{route_id}",
                json=route_config,
                headers={"X-API-KEY": self.admin_key}
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to create route {route_id}: {response.text}")
                raise Exception(f"Route creation failed: {response.status_code}")
                
            logger.info(f"Created APISIX route: {route_id}")
            return response.json()
            
    async def delete_mcp_routes(self) -> Dict[str, Any]:
        """Delete MCP routes from APISIX"""
        deleted = []
        
        for route_id in ["mcp-main", "mcp-oauth"]:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.delete(
                        f"{self.admin_url}/routes/{route_id}",
                        headers={"X-API-KEY": self.admin_key}
                    )
                    
                    if response.status_code in [200, 204, 404]:
                        deleted.append(route_id)
                        logger.info(f"Deleted APISIX route: {route_id}")
                    else:
                        logger.error(f"Failed to delete route {route_id}: {response.status_code}")
                        
            except Exception as e:
                logger.error(f"Error deleting route {route_id}: {e}")
                
        return {"deleted": deleted, "status": "complete"}

# Create global route manager
apisix_route_manager = APISIXRouteManager()