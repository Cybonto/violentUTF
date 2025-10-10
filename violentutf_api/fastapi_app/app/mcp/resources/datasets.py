# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Dataset Resources for MCP

========================

This module provides access to ViolentUTF security datasets through the MCP protocol.
Supports comprehensive dataset metadata, content access, and caching.
"""
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Self, cast

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


class DatasetResourceProvider(BaseResourceProvider):
    """Provide comprehensive access to security datasets."""

    def __init__(self: "Self") -> None:
        """Initialize instance."""
        super().__init__("violentutf://datasets/{dataset_id}", "DatasetProvider")

        self.auth_handler = MCPAuthHandler()
        self.base_url = self._get_api_url()

    def _get_api_url(self: "Self") -> str:
        """Get internal API URL for container communication."""
        api_url = getattr(settings, "VIOLENTUTF_API_URL", "http://localhost:8000")

        # Convert external gateway URL to internal service URL
        if "localhost:9080" in api_url or "apisix" in api_url:
            return "http://violentutf-api:8000"
        return api_url

    async def get_resource(self: "Self", uri: str, params: Dict[str, object]) -> Optional[AdvancedResource]:
        """Get specific dataset resource with full content."""
        uri_params = self.extract_params(uri)

        dataset_id = uri_params.get("dataset_id")

        if not dataset_id:
            logger.warning("No dataset_id found in URI: %s", uri)
            return None

        try:
            headers = await self._get_headers(params)

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get dataset metadata
                dataset_response = await client.get(f"{self.base_url}/api/v1/datasets/{dataset_id}", headers=headers)

                if dataset_response.status_code != 200:
                    logger.warning(
                        "Failed to get dataset %s: %s",
                        dataset_id,
                        dataset_response.status_code,
                    )
                    return None

                dataset = dataset_response.json()

                # Get dataset content with pagination support
                content_data = await self._get_dataset_content(client, dataset_id, headers, params)

                # Calculate content metadata
                content_size = len(str(content_data).encode("utf-8"))
                content_hash = hashlib.md5(str(content_data).encode("utf-8"), usedforsecurity=False).hexdigest()

                # Create comprehensive resource
                resource_content = {
                    "metadata": {
                        "id": dataset["id"],
                        "name": dataset["name"],
                        "description": dataset.get("description", ""),
                        "category": dataset.get("category", "unknown"),
                        "format": dataset.get("format", "json"),
                        "size": dataset.get(
                            "size",
                            len(content_data) if isinstance(content_data, list) else 0,
                        ),
                        "created_at": dataset.get("created_at"),
                        "updated_at": dataset.get("updated_at"),
                        "tags": dataset.get("tags", []),
                    },
                    "content": content_data,
                    "statistics": await self._get_dataset_statistics(content_data),
                    "schema": await self._infer_dataset_schema(content_data),
                }

                return AdvancedResource(
                    uri=uri,
                    name=f"Dataset: {dataset['name']}",
                    description=dataset.get("description", f"Security testing dataset: {dataset['name']}"),
                    mimeType="application/json",
                    content=resource_content,
                    metadata=ResourceMetadata(
                        created_at=(
                            datetime.fromisoformat(dataset["created_at"])
                            if dataset.get("created_at")
                            else datetime.now()
                        ),
                        updated_at=datetime.fromisoformat(
                            dataset.get(
                                "updated_at",
                                dataset.get("created_at", datetime.now().isoformat()),
                            )
                        ),
                        version=dataset.get("version", "1.0"),
                        author=dataset.get("author", "ViolentUTF"),
                        tags=dataset.get(
                            "tags",
                            ["dataset", "security", dataset.get("category", "unknown")],
                        ),
                        size=content_size,
                        checksum=content_hash,
                    ),
                )

        except httpx.TimeoutException:
            logger.error("Timeout getting dataset resource: %s", dataset_id)
            return None
        except httpx.ConnectError:
            logger.error("Connection error getting dataset resource: %s", dataset_id)
            return None
        except Exception as e:
            logger.error("Error getting dataset resource %s: %s", dataset_id, e)
            return None

    async def _get_dataset_content(
        self: "Self",
        client: httpx.AsyncClient,
        dataset_id: str,
        headers: Dict[str, str],
        params: Dict[str, object],
    ) -> object:
        """Get dataset content with pagination support."""
        try:

            # Check if content endpoint exists
            content_response = await client.get(
                f"{self.base_url}/api/v1/datasets/{dataset_id}/content",
                headers=headers,
                params={
                    "limit": int(params.get("limit", 1000)),
                    "offset": int(params.get("offset", 0)),
                },
            )

            if content_response.status_code == 200:
                return content_response.json()
            else:
                logger.debug(
                    "Content endpoint not available for dataset %s, returning empty list",
                    dataset_id,
                )
                return []

        except Exception as e:
            logger.debug("Could not fetch content for dataset %s: %s", dataset_id, e)
            return []

    async def _get_dataset_statistics(self: "Self", content: object) -> Dict[str, object]:
        """Generate statistics for dataset content."""
        if not content:

            return {"total_entries": 0}

        stats: Dict[str, object] = {"total_entries": 0}

        if isinstance(content, list):
            stats["total_entries"] = len(content)

            # Analyze content structure
            if content and isinstance(content[0], dict):
                # Get field statistics
                all_fields: set[str] = set()
                for item in content[:100]:  # Sample first 100 items
                    if isinstance(item, dict):
                        all_fields.update(item.keys())

                stats["fields"] = list(all_fields)
                stats["field_count"] = len(all_fields)

                # Sample content analysis
                if "prompt" in all_fields:
                    prompts = [item.get("prompt", "") for item in content[:10] if isinstance(item, dict)]
                    avg_prompt_length = sum(len(str(p)) for p in prompts) // max(len(prompts), 1)
                    stats["average_prompt_length"] = avg_prompt_length

        elif isinstance(content, dict):
            stats["type"] = "object"
            stats["keys"] = list(content.keys())

        return stats

    async def _infer_dataset_schema(self: "Self", content: object) -> Dict[str, object]:
        """Infer schema from dataset content."""
        schema: Dict[str, object] = {"type": "unknown"}

        if isinstance(content, list) and content:
            schema["type"] = "array"
            schema["items"] = {}

            # Analyze first few items to infer schema
            sample_item = content[0]
            if isinstance(sample_item, dict):
                items_schema = cast(Dict[str, object], schema["items"])
                items_schema["type"] = "object"
                items_schema["properties"] = {}

                for key, value in sample_item.items():
                    properties = cast(Dict[str, object], items_schema["properties"])
                    if isinstance(value, str):
                        properties[key] = {"type": "string"}
                    elif isinstance(value, int):
                        properties[key] = {"type": "integer"}
                    elif isinstance(value, float):
                        properties[key] = {"type": "number"}
                    elif isinstance(value, bool):
                        properties[key] = {"type": "boolean"}
                    elif isinstance(value, list):
                        properties[key] = {"type": "array"}
                    elif isinstance(value, dict):
                        properties[key] = {"type": "object"}

        return schema

    async def list_resources(self: "Self", params: Dict[str, object]) -> List[AdvancedResource]:
        """List all available datasets with metadata."""
        resources = []

        try:
            headers = await self._get_headers(params)

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get datasets list
                response = await client.get(
                    f"{self.base_url}/api/v1/datasets",
                    headers=headers,
                    params={
                        "category": str(params.get("category")) if params.get("category") else None,
                        "limit": int(params.get("limit", 100)),
                    },
                )

                if response.status_code == 200:
                    datasets_data = response.json()
                    datasets = (
                        datasets_data.get("datasets", datasets_data)
                        if isinstance(datasets_data, dict)
                        else datasets_data
                    )

                    for dataset in datasets:
                        if isinstance(dataset, dict):
                            # Create lightweight resource for listing
                            resource_content = {
                                "metadata": {
                                    "id": dataset.get("id", dataset.get("name", "unknown")),
                                    "name": dataset.get("name", "Unknown Dataset"),
                                    "description": dataset.get("description", ""),
                                    "category": dataset.get("category", "unknown"),
                                    "format": dataset.get("format", "json"),
                                    "size": dataset.get("size", 0),
                                    "created_at": dataset.get("created_at"),
                                    "updated_at": dataset.get("updated_at"),
                                    "tags": dataset.get("tags", []),
                                },
                                "preview": "Use get_resource to access full content",
                            }

                            dataset_id = dataset.get("id", dataset.get("name", "unknown"))

                            resources.append(
                                AdvancedResource(
                                    uri=f"violentutf://datasets/{dataset_id}",
                                    name=f"Dataset: {dataset.get('name', 'Unknown')}",
                                    description=dataset.get(
                                        "description",
                                        f"Security dataset: {dataset.get('name', 'Unknown')}",
                                    ),
                                    mimeType="application/json",
                                    content=resource_content,
                                    metadata=ResourceMetadata(
                                        created_at=(
                                            datetime.fromisoformat(dataset["created_at"])
                                            if dataset.get("created_at")
                                            else datetime.now()
                                        ),
                                        updated_at=datetime.fromisoformat(
                                            str(
                                                dataset.get(
                                                    "updated_at",
                                                    dataset.get(
                                                        "created_at",
                                                        datetime.now().isoformat(),
                                                    ),
                                                )
                                            )
                                        ),
                                        tags=dataset.get(
                                            "tags",
                                            [
                                                "dataset",
                                                "security",
                                                dataset.get("category", "unknown"),
                                            ],
                                        ),
                                        size=dataset.get("size", 0),
                                    ),
                                )
                            )
                else:
                    logger.warning("Failed to list datasets: %s", response.status_code)

        except Exception as e:
            logger.error("Error listing dataset resources: %s", e)

        logger.info("Listed %s dataset resources", len(resources))
        return resources

    async def _get_headers(self: "Self", params: Dict[str, object]) -> Dict[str, str]:
        """Get API headers with authentication."""
        headers = {"Content-Type": "application/json", "X-API-Gateway": "MCP-Dataset"}

        # Add authentication if available
        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)

        # Override with provided token if available
        if "_auth_token" in params:
            headers["Authorization"] = f"Bearer {params['_auth_token']}"

        return headers


class ResultsResourceProvider(BaseResourceProvider):
    """Provide access to orchestrator execution results."""

    def __init__(self: "Self") -> None:
        """Initialize instance."""
        super().__init__("violentutf://results/{execution_id}", "ResultsProvider")

        self.auth_handler = MCPAuthHandler()
        self.base_url = self._get_api_url()

    def _get_api_url(self: "Self") -> str:
        """Get internal API URL for container communication."""
        api_url = getattr(settings, "VIOLENTUTF_API_URL", "http://localhost:8000")

        if "localhost:9080" in api_url or "apisix" in api_url:
            return "http://violentutf-api:8000"
        return api_url

    async def get_resource(self: "Self", uri: str, params: Dict[str, object]) -> Optional[AdvancedResource]:
        """Get specific execution results."""
        uri_params = self.extract_params(uri)

        execution_id = uri_params.get("execution_id")

        if not execution_id:
            return None

        try:
            headers = await self._get_headers(params)

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get orchestrator results
                response = await client.get(
                    f"{self.base_url}/api/v1/orchestrators/{execution_id}/results",
                    headers=headers,
                )

                if response.status_code == 200:
                    results = response.json()

                    # Get orchestrator metadata
                    orch_response = await client.get(
                        f"{self.base_url}/api/v1/orchestrators/{execution_id}",
                        headers=headers,
                    )

                    orchestrator = orch_response.json() if orch_response.status_code == 200 else {}

                    resource_content = {
                        "execution_id": execution_id,
                        "orchestrator": {
                            "name": orchestrator.get("name", "Unknown"),
                            "type": orchestrator.get("orchestrator_type", "unknown"),
                            "status": orchestrator.get("status", "unknown"),
                        },
                        "results": results,
                        "summary": await self._generate_results_summary(results),
                    }

                    return AdvancedResource(
                        uri=uri,
                        name=f"Results: {orchestrator.get('name', execution_id)}",
                        description=f"Execution results for orchestrator: {orchestrator.get('name', execution_id)}",
                        mimeType="application/json",
                        content=resource_content,
                        metadata=ResourceMetadata(
                            created_at=datetime.fromisoformat(
                                orchestrator.get("created_at", datetime.now().isoformat())
                            ),
                            updated_at=datetime.fromisoformat(
                                orchestrator.get("updated_at", datetime.now().isoformat())
                            ),
                            tags=[
                                "results",
                                "execution",
                                orchestrator.get("orchestrator_type", "unknown"),
                            ],
                        ),
                    )

        except Exception as e:
            logger.error("Error getting results resource %s: %s", execution_id, e)

        return None

    async def _generate_results_summary(self: "Self", results: object) -> Dict[str, object]:
        """Generate summary statistics for results."""
        summary = {"total_results": 0, "status": "unknown"}

        if isinstance(results, dict):
            if "total" in results:
                summary["total_results"] = results["total"]
            if "status" in results:
                summary["status"] = results["status"]
            if "results" in results and isinstance(results["results"], list):
                summary["total_results"] = len(results["results"])
        elif isinstance(results, list):
            summary["total_results"] = len(results)

        return summary

    async def list_resources(self: "Self", params: Dict[str, object]) -> List[AdvancedResource]:
        """List available execution results."""
        resources = []

        try:
            headers = await self._get_headers(params)

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get orchestrators that have results
                response = await client.get(
                    f"{self.base_url}/api/v1/orchestrators",
                    headers=headers,
                    params={"status": "completed"},
                )

                if response.status_code == 200:
                    orchestrators_data = response.json()
                    orchestrators = (
                        orchestrators_data.get("orchestrators", orchestrators_data)
                        if isinstance(orchestrators_data, dict)
                        else orchestrators_data
                    )

                    for orchestrator in orchestrators:
                        if isinstance(orchestrator, dict) and orchestrator.get("status") == "completed":
                            execution_id = orchestrator.get("id", orchestrator.get("name"))

                            resources.append(
                                AdvancedResource(
                                    uri=f"violentutf://results/{execution_id}",
                                    name=f"Results: {orchestrator.get('name', execution_id)}",
                                    description=(
                                        f"Execution results for "
                                        f"{orchestrator.get('orchestrator_type', 'unknown')} orchestrator"
                                    ),
                                    mimeType="application/json",
                                    content={"preview": "Use get_resource to access full results"},
                                    metadata=ResourceMetadata(
                                        created_at=datetime.fromisoformat(
                                            orchestrator.get("created_at", datetime.now().isoformat())
                                        ),
                                        updated_at=datetime.fromisoformat(
                                            orchestrator.get("updated_at", datetime.now().isoformat())
                                        ),
                                        tags=[
                                            "results",
                                            "execution",
                                            orchestrator.get("orchestrator_type", "unknown"),
                                        ],
                                    ),
                                )
                            )

        except Exception as e:
            logger.error("Error listing results resources: %s", e)

        return resources

    async def _get_headers(self: "Self", params: Dict[str, object]) -> Dict[str, str]:
        """Get API headers with authentication."""
        headers = {"Content-Type": "application/json", "X-API-Gateway": "MCP-Results"}

        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)

        if "_auth_token" in params:
            headers["Authorization"] = f"Bearer {params['_auth_token']}"

        return headers


# Register the new resource providers
def register_dataset_providers() -> None:
    """Register all dataset-related resource providers."""
    advanced_resource_registry.register(DatasetResourceProvider())

    advanced_resource_registry.register(ResultsResourceProvider())
    logger.info("Registered dataset and results resource providers")


# Auto-register providers when module is imported
register_dataset_providers()
