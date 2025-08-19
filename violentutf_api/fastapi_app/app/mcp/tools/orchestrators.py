# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""MCP Orchestrator Management Tools."""

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from app.core.config import settings
from app.mcp.auth import MCPAuthHandler
from mcp.types import Tool

logger = logging.getLogger(__name__)


class OrchestratorManagementTools:
    """MCP tools for orchestrator management and execution."""

    def __init__(self) -> None:
        """ "Initialize the instance."""
        self.base_url = settings.VIOLENTUTF_API_URL or "http://localhost:8000"
        # Use internal URL for direct API access from within container
        if self.base_url and "localhost:9080" in self.base_url:
            self.base_url = "http://violentutf-api:8000"

        self.auth_handler = MCPAuthHandler()

    def get_tools(self: "OrchestratorManagementTools") -> List[Tool]:
        """Get all orchestrator management tools."""
        return [
            self._create_list_orchestrators_tool(),
            self._create_get_orchestrator_tool(),
            self._create_create_orchestrator_tool(),
            self._create_start_orchestrator_tool(),
            self._create_stop_orchestrator_tool(),
            self._create_pause_orchestrator_tool(),
            self._create_resume_orchestrator_tool(),
            self._create_get_orchestrator_results_tool(),
            self._create_get_orchestrator_logs_tool(),
            self._create_delete_orchestrator_tool(),
            self._create_clone_orchestrator_tool(),
            self._create_get_orchestrator_stats_tool(),
            self._create_export_orchestrator_results_tool(),
            self._create_validate_orchestrator_config_tool(),
        ]

    def _create_list_orchestrators_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for listing orchestrators."""
        return Tool(
            name="list_orchestrators",
            description="List all orchestrator executions with filtering options",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by execution status",
                        "enum": ["pending", "running", "completed", "failed", "paused", "cancelled"],
                    },
                    "orchestrator_type": {
                        "type": "string",
                        "description": "Filter by orchestrator type",
                        "enum": ["multi_turn", "red_teaming", "tree_of_attacks", "prompt_sending"],
                    },
                    "created_after": {
                        "type": "string",
                        "format": "date-time",
                        "description": "Filter orchestrators created after this date",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 500,
                    },
                    "include_stats": {
                        "type": "boolean",
                        "description": "Include execution statistics",
                        "default": True,
                    },
                },
                "required": [],
            },
        )

    def _create_get_orchestrator_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for getting orchestrator details."""
        return Tool(
            name="get_orchestrator",
            description="Get detailed information about a specific orchestrator execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {"type": "string", "description": "Unique identifier of the orchestrator"},
                    "include_configuration": {
                        "type": "boolean",
                        "description": "Include full configuration details",
                        "default": True,
                    },
                    "include_progress": {
                        "type": "boolean",
                        "description": "Include current progress information",
                        "default": True,
                    },
                    "include_results_summary": {
                        "type": "boolean",
                        "description": "Include summary of results",
                        "default": True,
                    },
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_create_orchestrator_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for creating new orchestrators."""
        return Tool(
            name="create_orchestrator",
            description="Create a new orchestrator execution with specified configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Human-readable name for the orchestrator"},
                    "orchestrator_type": {
                        "type": "string",
                        "description": "Type of orchestrator to create",
                        "enum": ["multi_turn", "red_teaming", "tree_of_attacks", "prompt_sending"],
                    },
                    "target_generators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of generator IDs to target",
                    },
                    "dataset_name": {"type": "string", "description": "Dataset to use for prompts"},
                    "converters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of converter names to apply",
                        "default": [],
                    },
                    "scorers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of scorer names to apply",
                        "default": [],
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Maximum number of iterations",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "concurrent_limit": {
                        "type": "integer",
                        "description": "Maximum concurrent executions",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                    "memory_labels": {"type": "object", "description": "Memory labels for result tracking"},
                    "auto_start": {
                        "type": "boolean",
                        "description": "Start execution immediately after creation",
                        "default": False,
                    },
                },
                "required": ["name", "orchestrator_type", "target_generators", "dataset_name"],
            },
        )

    def _create_start_orchestrator_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for starting orchestrators."""
        return Tool(
            name="start_orchestrator",
            description="Start execution of a configured orchestrator",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {
                        "type": "string",
                        "description": "Unique identifier of the orchestrator to start",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Execution priority",
                        "enum": ["low", "normal", "high"],
                        "default": "normal",
                    },
                    "notifications": {
                        "type": "boolean",
                        "description": "Enable completion notifications",
                        "default": True,
                    },
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_stop_orchestrator_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for stopping orchestrators."""
        return Tool(
            name="stop_orchestrator",
            description="Stop a running orchestrator execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {
                        "type": "string",
                        "description": "Unique identifier of the orchestrator to stop",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force stop without graceful shutdown",
                        "default": False,
                    },
                    "save_partial_results": {
                        "type": "boolean",
                        "description": "Save partial results before stopping",
                        "default": True,
                    },
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_pause_orchestrator_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for pausing orchestrators."""
        return Tool(
            name="pause_orchestrator",
            description="Pause a running orchestrator execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {
                        "type": "string",
                        "description": "Unique identifier of the orchestrator to pause",
                    },
                    "save_state": {"type": "boolean", "description": "Save current execution state", "default": True},
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_resume_orchestrator_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for resuming orchestrators."""
        return Tool(
            name="resume_orchestrator",
            description="Resume a paused orchestrator execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {
                        "type": "string",
                        "description": "Unique identifier of the orchestrator to resume",
                    },
                    "priority": {
                        "type": "string",
                        "description": "Execution priority for resumed execution",
                        "enum": ["low", "normal", "high"],
                        "default": "normal",
                    },
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_get_orchestrator_results_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for getting orchestrator results."""
        return Tool(
            name="get_orchestrator_results",
            description="Get execution results from an orchestrator",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {"type": "string", "description": "Unique identifier of the orchestrator"},
                    "result_format": {
                        "type": "string",
                        "description": "Format for results",
                        "enum": ["summary", "detailed", "raw", "scored_only"],
                        "default": "summary",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "include_scores": {"type": "boolean", "description": "Include scoring results", "default": True},
                    "filter_by_score": {
                        "type": "object",
                        "description": "Filter results by score thresholds",
                        "properties": {
                            "min_score": {"type": "number"},
                            "max_score": {"type": "number"},
                            "scorer_name": {"type": "string"},
                        },
                    },
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_get_orchestrator_logs_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for getting orchestrator logs."""
        return Tool(
            name="get_orchestrator_logs",
            description="Get execution logs from an orchestrator",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {"type": "string", "description": "Unique identifier of the orchestrator"},
                    "log_level": {
                        "type": "string",
                        "description": "Minimum log level to include",
                        "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        "default": "INFO",
                    },
                    "tail_lines": {
                        "type": "integer",
                        "description": "Number of recent log lines to return",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "include_timestamps": {
                        "type": "boolean",
                        "description": "Include timestamps in log output",
                        "default": True,
                    },
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_delete_orchestrator_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for deleting orchestrators."""
        return Tool(
            name="delete_orchestrator",
            description="Delete an orchestrator and its results",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {
                        "type": "string",
                        "description": "Unique identifier of the orchestrator to delete",
                    },
                    "force": {"type": "boolean", "description": "Force deletion even if running", "default": False},
                    "keep_results": {
                        "type": "boolean",
                        "description": "Keep execution results after deletion",
                        "default": False,
                    },
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_clone_orchestrator_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for cloning orchestrators."""
        return Tool(
            name="clone_orchestrator",
            description="Clone an existing orchestrator configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_orchestrator_id": {"type": "string", "description": "ID of the orchestrator to clone"},
                    "new_name": {"type": "string", "description": "Name for the cloned orchestrator"},
                    "configuration_overrides": {
                        "type": "object",
                        "description": "Configuration parameters to override",
                    },
                    "copy_results": {
                        "type": "boolean",
                        "description": "Copy existing results to the clone",
                        "default": False,
                    },
                },
                "required": ["source_orchestrator_id", "new_name"],
            },
        )

    def _create_get_orchestrator_stats_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for getting orchestrator statistics."""
        return Tool(
            name="get_orchestrator_stats",
            description="Get execution statistics and metrics for an orchestrator",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {"type": "string", "description": "Unique identifier of the orchestrator"},
                    "include_performance_metrics": {
                        "type": "boolean",
                        "description": "Include performance and timing metrics",
                        "default": True,
                    },
                    "include_score_distribution": {
                        "type": "boolean",
                        "description": "Include score distribution analysis",
                        "default": True,
                    },
                    "include_error_analysis": {
                        "type": "boolean",
                        "description": "Include error and failure analysis",
                        "default": True,
                    },
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_export_orchestrator_results_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for exporting orchestrator results."""
        return Tool(
            name="export_orchestrator_results",
            description="Export orchestrator results in various formats",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_id": {"type": "string", "description": "Unique identifier of the orchestrator"},
                    "export_format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["json", "csv", "xlsx", "html", "pdf"],
                        "default": "json",
                    },
                    "include_scores": {
                        "type": "boolean",
                        "description": "Include scoring results in export",
                        "default": True,
                    },
                    "include_metadata": {
                        "type": "boolean",
                        "description": "Include metadata and configuration",
                        "default": True,
                    },
                    "compress": {"type": "boolean", "description": "Compress export file", "default": False},
                },
                "required": ["orchestrator_id"],
            },
        )

    def _create_validate_orchestrator_config_tool(self: "OrchestratorManagementTools") -> Tool:
        """Create tool for validating orchestrator configuration."""
        return Tool(
            name="validate_orchestrator_config",
            description="Validate an orchestrator configuration without creating it",
            inputSchema={
                "type": "object",
                "properties": {
                    "orchestrator_type": {
                        "type": "string",
                        "description": "Type of orchestrator to validate",
                        "enum": ["multi_turn", "red_teaming", "tree_of_attacks", "prompt_sending"],
                    },
                    "target_generators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of generator IDs to validate",
                    },
                    "dataset_name": {"type": "string", "description": "Dataset name to validate"},
                    "converters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of converter names to validate",
                    },
                    "scorers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of scorer names to validate",
                    },
                    "check_compatibility": {
                        "type": "boolean",
                        "description": "Check component compatibility",
                        "default": True,
                    },
                    "estimate_resources": {
                        "type": "boolean",
                        "description": "Estimate resource requirements",
                        "default": True,
                    },
                },
                "required": ["orchestrator_type", "target_generators", "dataset_name"],
            },
        )

    async def execute_tool(
        self: "OrchestratorManagementTools",
        tool_name: str,
        arguments: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute an orchestrator management tool."""
        logger.info(f"Executing orchestrator tool: {tool_name}")

        try:
            # Route to appropriate execution method
            execution_method = getattr(self, f"_execute_{tool_name}", None)
            if execution_method:
                return await execution_method(arguments)
            else:
                return {"error": "unknown_tool", "message": f"Unknown orchestrator tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Error executing orchestrator tool {tool_name}: {e}")
            return {"error": "execution_failed", "message": str(e), "tool_name": tool_name}

    # Individual execution methods for each tool
    async def _execute_list_orchestrators(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._api_request("GET", "/api/v1/orchestrators", params=args)

    async def _execute_get_orchestrator(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("GET", f"/api/v1/orchestrators/{orch_id}", params=args)

    async def _execute_create_orchestrator(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        return await self._api_request("POST", "/api/v1/orchestrators", json=args)

    async def _execute_start_orchestrator(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("POST", f"/api/v1/orchestrators/{orch_id}/start", json=args)

    async def _execute_stop_orchestrator(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("POST", f"/api/v1/orchestrators/{orch_id}/stop", json=args)

    async def _execute_pause_orchestrator(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("POST", f"/api/v1/orchestrators/{orch_id}/pause", json=args)

    async def _execute_resume_orchestrator(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("POST", f"/api/v1/orchestrators/{orch_id}/resume", json=args)

    async def _execute_get_orchestrator_results(
        self: "OrchestratorManagementTools", args: Dict[str, Any]
    ) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("GET", f"/api/v1/orchestrators/{orch_id}/results", params=args)

    async def _execute_get_orchestrator_logs(
        self: "OrchestratorManagementTools", args: Dict[str, Any]
    ) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("GET", f"/api/v1/orchestrators/{orch_id}/logs", params=args)

    async def _execute_delete_orchestrator(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("DELETE", f"/api/v1/orchestrators/{orch_id}", params=args)

    async def _execute_clone_orchestrator(self: "OrchestratorManagementTools", args: Dict[str, Any]) -> Dict[str, Any]:
        source_id = args.pop("source_orchestrator_id")
        return await self._api_request("POST", f"/api/v1/orchestrators/{source_id}/clone", json=args)

    async def _execute_get_orchestrator_stats(
        self: "OrchestratorManagementTools", args: Dict[str, Any]
    ) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("GET", f"/api/v1/orchestrators/{orch_id}/stats", params=args)

    async def _execute_export_orchestrator_results(
        self: "OrchestratorManagementTools", args: Dict[str, Any]
    ) -> Dict[str, Any]:
        orch_id = args.pop("orchestrator_id")
        return await self._api_request("POST", f"/api/v1/orchestrators/{orch_id}/export", json=args)

    async def _execute_validate_orchestrator_config(
        self: "OrchestratorManagementTools", args: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self._api_request("POST", "/api/v1/orchestrators/validate", json=args)

    async def _api_request(self: "OrchestratorManagementTools", method: str, path: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated API request."""
        headers = {"Content-Type": "application/json", "X-API-Gateway": "MCP-Orchestrator"}

        # Add authentication headers if available
        auth_headers = await self.auth_handler.get_auth_headers()
        headers.update(auth_headers)

        url = urljoin(self.base_url, path)
        timeout = 120.0  # Longer timeout for orchestrator operations

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(method=method, url=url, headers=headers, **kwargs)
                logger.debug(f"Orchestrator API call: {method} {url} -> {response.status_code}")

                if response.status_code >= 400:
                    error_detail = "Unknown error"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", str(error_data))
                    except Exception:
                        error_detail = response.text

                    return {
                        "error": f"api_error_{response.status_code}",
                        "message": error_detail,
                        "status_code": response.status_code,
                    }

                return response.json()

            except httpx.TimeoutException:
                logger.error(f"Timeout on orchestrator API call: {url}")
                return {"error": "timeout", "message": "Orchestrator API call timed out"}
            except httpx.ConnectError:
                logger.error(f"Connection error on orchestrator API call: {url}")
                return {"error": "connection_error", "message": "Could not connect to ViolentUTF API"}
            except Exception as e:
                logger.error(f"Unexpected error on orchestrator API call {url}: {e}")
                return {"error": "unexpected_error", "message": str(e)}


# Global orchestrator tools instance
orchestrator_tools = OrchestratorManagementTools()
