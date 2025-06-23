"""
Advanced Base Classes for MCP Resources
======================================

This module provides enhanced base classes for MCP resource providers with
advanced features like caching, metadata, and pattern matching.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

class ResourceMetadata(BaseModel):
    """Enhanced resource metadata"""
    created_at: datetime
    updated_at: datetime
    version: str = "1.0"
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    size: Optional[int] = None
    checksum: Optional[str] = None

class AdvancedResource(BaseModel):
    """Enhanced MCP Resource structure with metadata"""
    uri: str
    name: str
    description: str
    mimeType: str = "application/json"
    content: Any
    metadata: Optional[ResourceMetadata] = None
    
    def __str__(self) -> str:
        return f"Resource(uri={self.uri}, name={self.name})"
    
    def to_mcp_resource(self) -> Dict[str, Any]:
        """Convert to MCP protocol resource format"""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mimeType
        }

class ResourcePattern:
    """Advanced URI pattern matching with parameter extraction"""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        self._regex = self._compile_pattern(pattern)
        self._param_names = self._extract_param_names(pattern)
    
    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Compile pattern into regex"""
        # Convert {param} to named groups
        regex_pattern = pattern
        for param in re.findall(r'\{(\w+)\}', pattern):
            regex_pattern = regex_pattern.replace(f'{{{param}}}', f'(?P<{param}>[^/]+)')
        
        # Escape special characters except our groups
        regex_pattern = regex_pattern.replace('/', r'\/')
        regex_pattern = f'^{regex_pattern}$'
        
        return re.compile(regex_pattern)
    
    def _extract_param_names(self, pattern: str) -> List[str]:
        """Extract parameter names from pattern"""
        return re.findall(r'\{(\w+)\}', pattern)
    
    def matches(self, uri: str) -> bool:
        """Check if URI matches this pattern"""
        return bool(self._regex.match(uri))
    
    def extract_params(self, uri: str) -> Dict[str, str]:
        """Extract parameters from URI"""
        match = self._regex.match(uri)
        if match:
            return match.groupdict()
        return {}

class CacheEntry:
    """Represents a cached resource with TTL"""
    
    def __init__(self, resource: AdvancedResource, ttl_seconds: int = 300):
        self.resource = resource
        self.ttl_seconds = ttl_seconds
        self.created_at = datetime.now()
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid"""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed < self.ttl_seconds
    
    def time_remaining(self) -> float:
        """Get seconds remaining before expiry"""
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return max(0, self.ttl_seconds - elapsed)

class BaseResourceProvider(ABC):
    """Enhanced base class for resource providers"""
    
    def __init__(self, uri_pattern: str, provider_name: str = None):
        self.pattern = ResourcePattern(uri_pattern)
        self.provider_name = provider_name or self.__class__.__name__
        self._cache: Dict[str, AdvancedResource] = {}
        self._cache_ttl = 300  # 5 minutes default
        self._cache_timestamps: Dict[str, datetime] = {}
        
    @abstractmethod
    async def get_resource(self, uri: str, params: Dict[str, Any]) -> Optional[AdvancedResource]:
        """Get a specific resource by URI"""
        pass
        
    @abstractmethod
    async def list_resources(self, params: Dict[str, Any]) -> List[AdvancedResource]:
        """List available resources"""
        pass
        
    def matches_uri(self, uri: str) -> bool:
        """Check if URI matches this provider's pattern"""
        return self.pattern.matches(uri)
    
    def extract_params(self, uri: str) -> Dict[str, str]:
        """Extract parameters from URI"""
        return self.pattern.extract_params(uri)
    
    def _is_cache_valid(self, uri: str) -> bool:
        """Check if cached resource is still valid"""
        if uri not in self._cache or uri not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[uri]
        elapsed = (datetime.now() - cache_time).total_seconds()
        return elapsed < self._cache_ttl
    
    def _cache_resource(self, uri: str, resource: AdvancedResource) -> None:
        """Cache a resource"""
        self._cache[uri] = resource
        self._cache_timestamps[uri] = datetime.now()
    
    def _get_cached_resource(self, uri: str) -> Optional[AdvancedResource]:
        """Get resource from cache if valid"""
        if self._is_cache_valid(uri):
            logger.debug(f"Cache hit for resource: {uri}")
            return self._cache[uri]
        return None
    
    def clear_cache(self) -> None:
        """Clear resource cache"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.info(f"Cleared cache for {self.provider_name}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = datetime.now()
        valid_entries = sum(
            1 for uri, timestamp in self._cache_timestamps.items()
            if (now - timestamp).total_seconds() < self._cache_ttl
        )
        
        return {
            "provider": self.provider_name,
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "cache_ttl_seconds": self._cache_ttl
        }

class AdvancedResourceRegistry:
    """Enhanced registry for resource providers with advanced features"""
    
    def __init__(self):
        self._providers: List[BaseResourceProvider] = []
        self._provider_map: Dict[str, BaseResourceProvider] = {}
        self._initialized = False
        
    def register(self, provider: BaseResourceProvider) -> None:
        """Register a resource provider"""
        logger.info(f"Registering resource provider: {provider.provider_name} for pattern: {provider.pattern.pattern}")
        self._providers.append(provider)
        self._provider_map[provider.provider_name] = provider
        
    async def initialize(self) -> None:
        """Initialize the registry"""
        if self._initialized:
            return
            
        logger.info(f"Initializing resource registry with {len(self._providers)} providers")
        self._initialized = True
        
    async def get_resource(self, uri: str, params: Dict[str, Any] = None) -> Optional[AdvancedResource]:
        """Get resource from appropriate provider"""
        if not self._initialized:
            await self.initialize()
            
        params = params or {}
        
        for provider in self._providers:
            if provider.matches_uri(uri):
                try:
                    # Check cache first
                    cached = provider._get_cached_resource(uri)
                    if cached:
                        return cached
                    
                    # Get from provider
                    resource = await provider.get_resource(uri, params)
                    
                    # Cache the result
                    if resource:
                        provider._cache_resource(uri, resource)
                    
                    return resource
                except Exception as e:
                    logger.error(f"Error getting resource {uri} from {provider.provider_name}: {e}")
                    continue
                    
        logger.warning(f"No provider found for URI: {uri}")
        return None
        
    async def list_resources(self, provider_filter: Optional[str] = None, pattern: Optional[str] = None) -> List[AdvancedResource]:
        """List all available resources with optional filtering"""
        if not self._initialized:
            await self.initialize()
            
        all_resources = []
        
        providers_to_check = self._providers
        if provider_filter:
            provider = self._provider_map.get(provider_filter)
            providers_to_check = [provider] if provider else []
        
        for provider in providers_to_check:
            try:
                resources = await provider.list_resources({})
                
                # Apply pattern filter if provided
                if pattern:
                    resources = [r for r in resources if pattern.lower() in r.name.lower() or pattern.lower() in r.description.lower()]
                
                all_resources.extend(resources)
                
            except Exception as e:
                logger.error(f"Error listing resources from {provider.provider_name}: {e}")
                continue
                
        logger.info(f"Listed {len(all_resources)} resources from {len(providers_to_check)} providers")
        return all_resources
    
    def get_provider_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all providers"""
        stats = []
        for provider in self._providers:
            provider_stats = provider.get_cache_stats()
            provider_stats["pattern"] = provider.pattern.pattern
            stats.append(provider_stats)
        return stats
    
    def clear_all_caches(self) -> None:
        """Clear caches for all providers"""
        for provider in self._providers:
            provider.clear_cache()
        logger.info("Cleared all provider caches")
    
    def get_providers(self) -> List[str]:
        """Get list of registered provider names"""
        return [provider.provider_name for provider in self._providers]
    
    def to_mcp_resources(self, resources: List[AdvancedResource]) -> List[Dict[str, Any]]:
        """Convert advanced resources to MCP protocol format"""
        return [resource.to_mcp_resource() for resource in resources]

# Global advanced resource registry instance
advanced_resource_registry = AdvancedResourceRegistry()