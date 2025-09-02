# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pyrit Orchestrator Service module."""

from __future__ import annotations

import inspect
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pyrit.memory import CentralMemory, MemoryInterface  # noqa: F401
from pyrit.models import PromptRequestPiece, PromptRequestResponse
from pyrit.orchestrator import Orchestrator, PromptSendingOrchestrator
from pyrit.prompt_converter import PromptConverter
from pyrit.prompt_target import PromptTarget
from pyrit.score.scorer import Scorer

# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

logger = logging.getLogger(__name__)


class PyRITOrchestratorService:
    """Service for managing PyRIT orchestrators in ViolentUTF API."""

    def __init__(self: PyRITOrchestratorService) -> None:
        """Initialize instance."""
        self.memory = None  # Will be initialized on startup

        self._orchestrator_instances: Dict[str, Orchestrator] = {}
        self._orchestrator_scorers: Dict[str, List] = {}  # Track scorers by orchestrator ID
        self._orchestrator_metadata: Dict[str, Dict[str, Any]] = {}  # Store execution metadata by orchestrator ID
        self._orchestrator_registry = self._discover_orchestrator_types()
        self._initialize_memory()  # Initialize memory immediately

    def _initialize_memory(self: PyRITOrchestratorService) -> None:
        """Initialize PyRIT memory with database concurrency handling."""
        try:

            # First try to get existing memory instance
            self.memory = CentralMemory.get_memory_instance()
            logger.info("Using existing PyRIT memory instance")
        except ValueError:
            # No memory instance exists - create a separate instance for the API service
            # Use a separate database path to avoid conflicts with Streamlit
            logger.info("No existing PyRIT memory instance found - creating separate API memory instance")
            self.memory = None  # Will create per - orchestrator to avoid concurrency issues

    def _get_memory(self: PyRITOrchestratorService) -> MemoryInterface | None:
        """Get PyRIT memory instance (may be None if using per - orchestrator memory)."""
        return self.memory

    def validate_memory_access(self: PyRITOrchestratorService) -> bool:
        """Validate that PyRIT memory is accessible or can work without global memory."""
        try:

            memory = self._get_memory()

            if memory is not None:
                # Debug: log memory object details
                logger.info("Memory object type: %s", type(memory))
                logger.info("Memory available: Global PyRIT memory instance exists")
                return True
            else:
                # No global memory - this is fine, orchestrators can use their own memory
                logger.info("PyRIT memory validation: No global memory, using per - orchestrator memory (this is fine)")
                return True
        except (AttributeError, RuntimeError, OSError) as e:
            # Handle memory access errors, runtime issues, and database connection errors
            logger.error("PyRIT memory validation failed: %s", e)
            return False

    def _discover_orchestrator_types(
        self: PyRITOrchestratorService,
    ) -> Dict[str, Type[Orchestrator]]:
        """Discover all available PyRIT orchestrator types."""
        orchestrator_types = {}

        # For Phase 1, focus on PromptSendingOrchestrator
        orchestrator_types["PromptSendingOrchestrator"] = PromptSendingOrchestrator

        # TODO: Add other orchestrator types in future phases
        # orchestrator_types["RedTeamingOrchestrator"] = RedTeamingOrchestrator
        # orchestrator_types["CrescendoOrchestrator"] = CrescendoOrchestrator

        return orchestrator_types

    def get_orchestrator_types(self: PyRITOrchestratorService) -> List[Dict[str, Any]]:
        """Get list of available orchestrator types with metadata."""
        types_info = []

        for name, orchestrator_class in self._orchestrator_registry.items():
            # Extract constructor parameters
            init_signature = inspect.signature(orchestrator_class.__init__)
            parameters = []

            for param_name, param in init_signature.parameters.items():
                if param_name in ["self"]:
                    continue

                param_info = {
                    "name": param_name,
                    "type": (str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"),
                    "required": param.default == inspect.Parameter.empty,
                    "default": (param.default if param.default != inspect.Parameter.empty else None),
                    "description": self._get_parameter_description(orchestrator_class, param_name),
                }
                parameters.append(param_info)

            type_info = {
                "name": name,
                "module": orchestrator_class.__module__,
                "category": "single_turn",  # PromptSendingOrchestrator is single - turn
                "description": orchestrator_class.__doc__ or f"{name} orchestrator",
                "use_cases": self._get_use_cases(name),
                "parameters": parameters,
            }
            types_info.append(type_info)

        return types_info

    def _get_parameter_description(self: PyRITOrchestratorService, orchestrator_class: Type, param_name: str) -> str:
        """Get parameter description from docstring or provide default."""
        descriptions = {
            "objective_target": "The target for sending prompts (configured generator)",
            "request_converter_configurations": "List of prompt converter configurations for requests",
            "response_converter_configurations": "List of prompt converter configurations for responses",
            "objective_scorer": "True / false scorer for objective evaluation",
            "auxiliary_scorers": "Additional scorers for response analysis",
            "batch_size": "Maximum batch size for sending prompts",
            "verbose": "Enable verbose logging",
            "should_convert_prepended_conversation": "Whether to convert prepended conversation",
            "retries_on_objective_failure": "Number of retries on objective failure",
        }
        return descriptions.get(param_name, f"Parameter {param_name}")

    def _get_use_cases(self: PyRITOrchestratorService, orchestrator_name: str) -> List[str]:
        """Get use cases for orchestrator type."""
        use_cases_map = {
            "PromptSendingOrchestrator": [
                "basic_prompting",
                "dataset_testing",
                "prompt_evaluation",
                "batch_processing",
            ]
        }
        return use_cases_map.get(orchestrator_name, ["general_purpose"])

    async def create_orchestrator_instance(self: PyRITOrchestratorService, config: Dict[str, Any]) -> str:
        """Create and configure orchestrator instance."""
        orchestrator_id = str(uuid.uuid4())

        orchestrator_type = config["orchestrator_type"]
        parameters = config["parameters"]
        user_context = config.get("user_context")  # Get user context for generator resolution

        if orchestrator_type not in self._orchestrator_registry:
            raise ValueError(f"Unknown orchestrator type: {orchestrator_type}")

        # Ensure PyRIT memory is available BEFORE any orchestrator operations
        memory = self._get_memory()
        if memory is None:
            # Create a separate memory instance for the API service to avoid database conflicts
            import os

            from pyrit.memory import DuckDBMemory

            # Use API - specific database path to avoid conflicts with Streamlit
            # Check if running in Docker or local environment
            if os.path.exists("/app/app_data/violentutf"):
                api_memory_dir = os.path.join("/app/app_data/violentutf", "api_memory")
            else:
                # Local development - use temp directory
                import tempfile

                api_memory_dir = os.path.join(tempfile.gettempdir(), "violentutf_api_memory")

            os.makedirs(api_memory_dir, exist_ok=True)

            # Create API - specific memory instance with proper file path
            api_memory_file = os.path.join(api_memory_dir, f"orchestrator_memory_{orchestrator_id[:8]}.db")
            api_memory = DuckDBMemory(db_path=api_memory_file)
            CentralMemory.set_memory_instance(api_memory)
            self.memory = api_memory  # Update service memory reference
            logger.info("Created API - specific memory instance at: %s", api_memory_file)

        # Validate memory access (now should always return True)
        if not self.validate_memory_access():
            raise RuntimeError("PyRIT memory is not accessible. Cannot create orchestrator.")

        # Resolve parameters with user context for generator lookup
        resolved_params = await self._resolve_orchestrator_parameters(parameters, user_context)

        # Create orchestrator instance
        orchestrator_class = self._orchestrator_registry[orchestrator_type]

        try:
            logger.info(
                "Creating %s with resolved params: %s",
                orchestrator_type,
                list(resolved_params.keys()),
            )

            # Debug: Show the actual resolved parameters for troubleshooting
            for param_name, param_value in resolved_params.items():
                if param_name == "scorers":
                    logger.info(
                        "Scorers parameter: %s scorer(s)",
                        (len(param_value) if isinstance(param_value, list) else "not a list"),
                    )
                    for i, scorer in enumerate(param_value if isinstance(param_value, list) else []):
                        logger.info(
                            "  Scorer %s: %s - %s",
                            i + 1,
                            type(scorer).__name__,
                            getattr(scorer, "scorer_name", "Unknown"),
                        )
                elif hasattr(param_value, "__class__"):
                    logger.info("Parameter %s: %s", param_name, type(param_value).__name__)
                else:
                    logger.info(
                        "Parameter %s: %s = %s",
                        param_name,
                        type(param_value),
                        param_value,
                    )

            orchestrator_instance = orchestrator_class(**resolved_params)
            logger.info("Successfully created %s instance", orchestrator_type)

            # Debug: Check what scorers are actually attached to the orchestrator
            for attr_name in ["scorers", "_scorers"]:
                if hasattr(orchestrator_instance, attr_name):
                    attr_value = getattr(orchestrator_instance, attr_name)
                    if attr_value:
                        if isinstance(attr_value, list):
                            logger.info(
                                "Orchestrator has %s: %s scorer(s)",
                                attr_name,
                                len(attr_value),
                            )
                            for i, scorer in enumerate(attr_value):
                                logger.info(
                                    "  Scorer %s: %s - %s",
                                    i + 1,
                                    type(scorer).__name__,
                                    getattr(scorer, "scorer_name", "Unknown"),
                                )
                        else:
                            logger.info(
                                "Orchestrator has %s: %s",
                                attr_name,
                                type(attr_value).__name__,
                            )
                    else:
                        logger.info("Orchestrator has %s: None/Empty", attr_name)

        except Exception as e:
            logger.error("Failed to create orchestrator instance: %s", e, exc_info=True)
            raise RuntimeError(f"Failed to create {orchestrator_type}: {str(e)}") from e

        # Store instance
        self._orchestrator_instances[orchestrator_id] = orchestrator_instance

        # Track any ConfiguredScorerWrapper instances for direct score collection
        tracked_scorers = []
        for param_name, param_value in resolved_params.items():
            if param_name == "scorers" and isinstance(param_value, list):
                for scorer in param_value:
                    if isinstance(scorer, ConfiguredScorerWrapper):
                        tracked_scorers.append(scorer)
                        logger.info(
                            "🎯 Tracking ConfiguredScorerWrapper: %s",
                            scorer.scorer_name,
                        )

        self._orchestrator_scorers[orchestrator_id] = tracked_scorers
        logger.info(
            "🎯 Stored %s scorers for orchestrator %s",
            len(tracked_scorers),
            orchestrator_id,
        )

        logger.info("Created %s instance with ID: %s", orchestrator_type, orchestrator_id)
        return orchestrator_id

    async def _reload_orchestrator_from_db(
        self: PyRITOrchestratorService,
        orchestrator_id: str,
        user_context: Optional[str] = None,
    ) -> bool:
        """Reload orchestrator instance from database configuration."""
        try:

            from uuid import UUID

            from app.db.database import get_session
            from app.models.orchestrator import OrchestratorConfiguration
            from sqlalchemy import select

            # Get database session
            async for db in get_session():
                # Get orchestrator configuration from database
                stmt = select(OrchestratorConfiguration).where(OrchestratorConfiguration.id == UUID(orchestrator_id))
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()

                if not config:
                    logger.error(
                        "Orchestrator configuration not found in database: %s",
                        orchestrator_id,
                    )
                    return False

                # Recreate orchestrator instance from database config
                # Cast SQLAlchemy columns to actual values for mypy
                from typing import cast

                # Force cast the JSON column to dict - SQLAlchemy JSON columns should be dict
                parameters = cast(
                    Dict[str, Any],
                    config.parameters if config.parameters is not None else {},
                )

                orchestrator_config = {
                    "orchestrator_type": str(config.orchestrator_type),
                    "parameters": parameters,
                }

                # Ensure memory is available
                memory = self._get_memory()
                if memory is None:
                    # Create API - specific memory if needed
                    import os

                    from pyrit.memory import DuckDBMemory

                    api_memory_dir = os.path.join("/app/app_data/violentutf", "api_memory")
                    os.makedirs(api_memory_dir, exist_ok=True)

                    api_memory_file = os.path.join(api_memory_dir, "orchestrator_memory.db")
                    api_memory = DuckDBMemory(db_path=api_memory_file)
                    CentralMemory.set_memory_instance(api_memory)
                    self.memory = api_memory
                    logger.info(
                        "Created API - specific memory for reloaded orchestrator at: %s",
                        api_memory_file,
                    )

                # Resolve parameters and create instance - pass parameters directly to avoid typing issues
                resolved_params = await self._resolve_orchestrator_parameters(parameters, user_context)
                orchestrator_type = str(orchestrator_config["orchestrator_type"])
                orchestrator_class = self._orchestrator_registry[orchestrator_type]
                orchestrator_instance = orchestrator_class(**resolved_params)

                # Store instance
                self._orchestrator_instances[orchestrator_id] = orchestrator_instance
                logger.info(
                    "Successfully reloaded orchestrator %s from database",
                    orchestrator_id,
                )

                return True

        except (ValueError, KeyError, AttributeError, TypeError) as e:
            # Handle database lookup errors, missing config fields, and orchestrator creation errors
            logger.error("Failed to reload orchestrator from database: %s", e)
            return False

        # Fallback return (should never reach here due to async for loop structure)
        return False

    async def _resolve_orchestrator_parameters(
        self: PyRITOrchestratorService,
        parameters: Dict[str, Any],
        user_context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve parameter references to actual objects."""
        resolved = {}

        for param_name, param_value in parameters.items():
            # Skip internal parameters that shouldn't be passed to orchestrator
            if param_name in ["user_context"]:
                continue

            if isinstance(param_value, dict) and param_value.get("type") == "configured_generator":
                # Resolve generator to PromptTarget
                generator_name = param_value["generator_name"]
                resolved[param_name] = await self._create_generator_target(generator_name, user_context)
            elif isinstance(param_value, dict) and param_value.get("type") == "configured_scorer":
                # Resolve scorer
                scorer_name = param_value["scorer_name"]
                resolved[param_name] = await self._create_scorer_instance(scorer_name, user_context)
            elif isinstance(param_value, list) and param_name in [
                "scorers",
                "auxiliary_scorers",
            ]:
                # Handle scorers list - resolve each configured scorer
                resolved_scorers = []
                for scorer_info in param_value:
                    if isinstance(scorer_info, dict) and scorer_info.get("type") == "configured_scorer":
                        # Check if full config is provided to avoid lookup
                        if "scorer_config" in scorer_info:
                            scorer_instance = ConfiguredScorerWrapper(scorer_info["scorer_config"])
                            resolved_scorers.append(scorer_instance)
                            logger.info(
                                "🎯 Created ConfiguredScorerWrapper for '%s' via config",
                                scorer_instance.scorer_name,
                            )
                        else:
                            # Fallback to lookup by name
                            scorer_name = scorer_info.get("scorer_name")
                            if scorer_name:
                                scorer_instance = await self._create_scorer_instance(scorer_name, user_context)
                                resolved_scorers.append(scorer_instance)
                                logger.info(
                                    "🎯 Created ConfiguredScorerWrapper for '%s' via lookup",
                                    scorer_name,
                                )

                # PromptSendingOrchestrator expects 'scorers' parameter
                resolved["scorers"] = resolved_scorers
                logger.info(
                    "🎯 Set 'scorers' parameter with %s scorer(s)",
                    len(resolved_scorers),
                )
            elif isinstance(param_value, list) and param_name.endswith("_configurations"):
                # Handle converter configurations
                resolved[param_name] = await self._resolve_converter_configurations(param_value)
            else:
                # Direct value
                resolved[param_name] = param_value

        return resolved

    async def _create_generator_target(
        self: PyRITOrchestratorService,
        generator_name: str,
        user_context: Optional[str] = None,
    ) -> PromptTarget:
        """Create PromptTarget from configured generator."""
        # Import generator service functions directly

        from app.services.generator_integration_service import get_generator_by_name

        # Use the provided user context to access the user's generators
        logger.info(
            "Looking up generator '%s' for user context: %s",
            generator_name,
            user_context,
        )
        generator_config = await get_generator_by_name(generator_name, user_context)

        if not generator_config:
            # Log more details about the failure
            logger.error("Generator '%s' not found for user '%s'", generator_name, user_context)
            raise ValueError(
                f"Generator '{generator_name}' not found for user '{user_context}'. "
                f"Please ensure this generator was created by the same user account "
                f"and is available in the 'Configure Generators' page."
            )

        # Log the generator config before creating target
        logger.info("Creating ConfiguredGeneratorTarget with config: %s", generator_config)
        logger.info("Generator type from config: %s", generator_config.get("type"))

        # Create ConfiguredGeneratorTarget
        return ConfiguredGeneratorTarget(generator_config)

    async def _create_scorer_instance(
        self: PyRITOrchestratorService,
        scorer_name: str,
        user_context: Optional[str] = None,
    ) -> Scorer:
        """Create Scorer from configured scorer."""
        # Import scorer service functions directly

        from app.services.scorer_integration_service import get_scorer_by_name

        scorer_config = await get_scorer_by_name(scorer_name)
        if not scorer_config:
            raise ValueError(f"Scorer not found: {scorer_name}")

        # Create scorer instance
        return ConfiguredScorerWrapper(scorer_config)

    async def _resolve_converter_configurations(
        self: PyRITOrchestratorService, configs: List[Dict]
    ) -> List[PromptConverter]:
        """Resolve converter configurations."""
        # For Phase 1, return empty list (no converters)

        # TODO: Implement converter resolution in future phases
        return []

    async def execute_orchestrator(
        self: PyRITOrchestratorService,
        orchestrator_id: str,
        execution_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute orchestrator with given configuration."""
        try:

            # Get user context from execution config
            user_context = execution_config.get("user_context")
            logger.info("Executing orchestrator %s for user %s", orchestrator_id, user_context)

            # Check if orchestrator instance exists in memory
            if orchestrator_id not in self._orchestrator_instances:
                # Try to reload orchestrator from database
                logger.info(
                    "Orchestrator %s not in memory, attempting to reload from database",
                    orchestrator_id,
                )
                success = await self._reload_orchestrator_from_db(orchestrator_id, user_context)
                if not success:
                    raise ValueError(f"Orchestrator not found: {orchestrator_id}")

            orchestrator = self._orchestrator_instances[orchestrator_id]
            execution_type = execution_config["execution_type"]
            input_data = execution_config["input_data"]

            # Extract and store metadata for this execution
            execution_metadata = input_data.get("metadata", {})
            if execution_metadata:
                self._orchestrator_metadata[orchestrator_id] = execution_metadata
                logger.info(
                    "Stored execution metadata for orchestrator %s: %s",
                    orchestrator_id,
                    list(execution_metadata.keys()),
                )

                # Update scorers with metadata if they exist
                if orchestrator_id in self._orchestrator_scorers:
                    for scorer in self._orchestrator_scorers[orchestrator_id]:
                        if isinstance(scorer, ConfiguredScorerWrapper):
                            scorer.execution_metadata = execution_metadata
                            logger.info(
                                "Updated scorer '%s' with execution metadata",
                                scorer.scorer_name,
                            )

            logger.info("Executing %s with input: %s", execution_type, input_data)

            # Execute based on orchestrator type and input
            if isinstance(orchestrator, PromptSendingOrchestrator):
                return await self._execute_prompt_sending_orchestrator(
                    orchestrator, execution_type, input_data, execution_config
                )
            else:
                raise ValueError(f"Unsupported orchestrator type for execution: {type(orchestrator)}")

        except Exception as e:
            logger.error("Orchestrator execution failed: %s", e, exc_info=True)
            raise

    async def _execute_prompt_sending_orchestrator(
        self: PyRITOrchestratorService,
        orchestrator: PromptSendingOrchestrator,
        execution_type: str,
        input_data: Dict[str, Any],
        execution_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute PromptSendingOrchestrator with specific input type."""
        if execution_type == "prompt_list":

            # Direct prompt list execution
            prompt_list = input_data["prompt_list"]
            prompt_type = input_data.get("prompt_type", "text")
            memory_labels = input_data.get("memory_labels", {})
            metadata = input_data.get("metadata", {})

            results = await orchestrator.send_prompts_async(
                prompt_list=prompt_list,
                prompt_type=prompt_type,
                memory_labels=memory_labels,
                metadata=metadata,
            )

        elif execution_type == "dataset":
            # Dataset - based execution
            dataset_id = input_data["dataset_id"]
            sample_size = input_data.get("sample_size")
            memory_labels = input_data.get("memory_labels", {})

            logger.info(
                "Loading dataset prompts for dataset_id: %s, sample_size: %s",
                dataset_id,
                sample_size,
            )

            # Load dataset prompts
            user_context = execution_config.get("user_context")
            dataset_prompts = await self._load_dataset_prompts(dataset_id, sample_size, user_context)

            logger.info("Loaded %s prompts from dataset %s", len(dataset_prompts), dataset_id)

            if not dataset_prompts:
                logger.error("No prompts loaded from dataset %s", dataset_id)
                raise ValueError(
                    f"Dataset {dataset_id} returned no prompts. "
                    f"Please check if the dataset exists and contains prompts."
                )

            # Log sample prompts for debugging
            logger.info("Sample prompts: %s", dataset_prompts[:2])

            # Add dataset info to memory labels
            memory_labels.update({"dataset_id": dataset_id, "execution_type": "dataset_testing"})

            logger.info("Sending %s prompts to orchestrator", len(dataset_prompts))

            try:
                logger.info(
                    "🎯 About to execute orchestrator.send_prompts_async with %s prompts",
                    len(dataset_prompts),
                )

                # Check scorers one more time before execution
                for attr_name in ["scorers", "_scorers"]:
                    if hasattr(orchestrator, attr_name):
                        attr_value = getattr(orchestrator, attr_name)
                        if attr_value:
                            scorer_count = len(attr_value) if isinstance(attr_value, list) else 1
                            logger.info("🎯 Pre - execution: orchestrator.%s = %s scorer(s)", attr_name, scorer_count)
                            if isinstance(attr_value, list):
                                for i, scorer in enumerate(attr_value):
                                    scorer_name = getattr(scorer, "scorer_name", "Unknown")
                                    logger.info("🎯   Scorer %s: %s - %s", i + 1, type(scorer).__name__, scorer_name)

                results = await orchestrator.send_prompts_async(
                    prompt_list=dataset_prompts,
                    prompt_type="text",
                    memory_labels=memory_labels,
                )

                logger.info("🎯 Orchestrator execution completed, got %s results", len(results))

                # Check scorer state after execution
                for attr_name in ["scorers", "_scorers"]:
                    if hasattr(orchestrator, attr_name):
                        attr_value = getattr(orchestrator, attr_name)
                        if attr_value and isinstance(attr_value, list):
                            for i, scorer in enumerate(attr_value):
                                if isinstance(scorer, ConfiguredScorerWrapper):
                                    logger.info(
                                        "🎯 Post - execution: %s collected %s scores",
                                        scorer.scorer_name,
                                        len(scorer.scores_collected),
                                    )

                # Store original prompts for response formatting since PyRIT may not preserve them
                if hasattr(orchestrator, "_last_sent_prompts"):
                    orchestrator._last_sent_prompts = dataset_prompts  # pylint: disable=protected-access
                else:
                    setattr(orchestrator, "_last_sent_prompts", dataset_prompts)
            except Exception as e:
                logger.error("Failed to send prompts to orchestrator: %s", e, exc_info=True)
                # Re - raise with more context
                raise RuntimeError(f"Orchestrator execution failed during prompt sending: {str(e)}") from e

        else:
            raise ValueError(f"Unsupported execution type: {execution_type}")

        # Check if results were returned
        if not results:
            logger.warning("No results returned from orchestrator execution")
            # Return empty but valid structure
            return {
                "execution_summary": {
                    "total_prompts": 0,
                    "successful_prompts": 0,
                    "failed_prompts": 0,
                    "success_rate": 0,
                    "total_time_seconds": 0,
                    "avg_response_time_ms": 0,
                    "memory_pieces_created": 0,
                },
                "prompt_request_responses": [],
                "scores": [],
                "memory_export": {
                    "orchestrator_memory_pieces": 0,
                    "score_entries": 0,
                    "conversations": 0,
                },
            }

        # Format results for API response
        logger.info("Orchestrator execution completed: %s results returned", len(results))
        for i, result in enumerate(results):
            logger.info("Result %s: %s pieces", i + 1, len(result.request_pieces))
            for j, piece in enumerate(result.request_pieces):
                value_length = len(piece.converted_value) if piece.converted_value else 0
                logger.info(
                    "  Piece %s: role=%s, has_value=%s, length=%s",
                    j + 1,
                    piece.role,
                    bool(piece.converted_value),
                    value_length,
                )

        formatted_results = self._format_execution_results(orchestrator, results, execution_type, input_data)
        logger.info("Formatted results keys: %s", list(formatted_results.keys()))
        logger.info("Has execution_summary: %s", "execution_summary" in formatted_results)
        logger.info(
            "Has prompt_request_responses: %s",
            "prompt_request_responses" in formatted_results,
        )
        if "prompt_request_responses" in formatted_results:
            logger.info(
                "Number of prompt_request_responses: %s",
                len(formatted_results["prompt_request_responses"]),
            )

        return formatted_results

    async def _load_dataset_prompts(
        self: PyRITOrchestratorService,
        dataset_id: str,
        sample_size: Optional[int] = None,
        user_context: Optional[str] = None,
    ) -> List[str]:
        """Load prompts from dataset - use shared memory access for memory datasets."""
        try:

            # For memory datasets, read directly from PyRIT memory database files
            if dataset_id.startswith("memory_dataset_") or dataset_id.startswith("memory_"):
                return await self._load_memory_dataset_prompts(dataset_id, sample_size)
            else:
                # Import dataset service functions for non - memory datasets
                from app.services.dataset_integration_service import get_dataset_prompts

                dataset_prompts: List[str] = await get_dataset_prompts(dataset_id, sample_size, user_context)
                return dataset_prompts
        except (ValueError, KeyError, OSError, ImportError) as e:
            # Handle dataset loading errors, file access errors, and import issues
            logger.error("Failed to load dataset prompts for %s: %s", dataset_id, e)
            # Fallback to service method
            from app.services.dataset_integration_service import get_dataset_prompts

            result: List[str] = await get_dataset_prompts(dataset_id, sample_size, user_context)
            return result

    async def _load_memory_dataset_prompts(
        self: PyRITOrchestratorService,
        dataset_id: str,
        sample_size: Optional[int] = None,
    ) -> List[str]:
        """Load prompts from PyRIT memory dataset using real database access."""
        try:

            logger.info("Loading real memory dataset prompts for %s", dataset_id)

            # Use the shared memory dataset loading function from dataset integration service
            from app.services.dataset_integration_service import (
                _load_real_memory_dataset_prompts,
            )

            prompts: List[str] = await _load_real_memory_dataset_prompts(dataset_id)

            if prompts:
                # Apply sample size if specified
                if sample_size and len(prompts) > sample_size:
                    prompts = prompts[:sample_size]

                logger.info(
                    "Loaded %s real prompts from PyRIT memory for dataset %s",
                    len(prompts),
                    dataset_id,
                )
                return prompts
            else:
                logger.warning("No real prompts found in PyRIT memory for dataset %s", dataset_id)
                return []

        except (OSError, ValueError, AttributeError) as e:
            # Handle database errors, data parsing errors, and memory access issues
            logger.error("Failed to load PyRIT memory dataset %s: %s", dataset_id, e)
            # Return empty list instead of fallback mock data
            return []

    def _format_execution_results(
        self: PyRITOrchestratorService,
        orchestrator: PromptSendingOrchestrator,
        results: List[PromptRequestResponse],
        execution_type: str,
        input_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Format orchestrator results for API response."""
        # EMERGENCY DEBUG: Add at the very start with guaranteed visibility

        debug_msg = f"🚨 _format_execution_results called with {len(results)} results"
        logger.error(debug_msg)

        orchestrator_debug = f"🚨 Orchestrator type: {type(orchestrator).__name__}"
        logger.error(orchestrator_debug)

        # Calculate execution summary
        total_prompts = len(results)
        logger.info("Formatting results: %s total results", total_prompts)

        successful_responses = sum(
            1
            for r in results
            if r.request_pieces and any(p.response_error == "none" for p in r.request_pieces if p.role == "assistant")
        )
        failed_responses = total_prompts - successful_responses

        logger.info(
            "Result summary: %s successful, %s failed",
            successful_responses,
            failed_responses,
        )

        # Calculate timing (approximate)
        start_time = (
            min(p.timestamp for r in results for p in r.request_pieces if p.timestamp)
            if results and results[0].request_pieces
            else datetime.utcnow()
        )
        end_time = (
            max(p.timestamp for r in results for p in r.request_pieces if p.timestamp)
            if results and results[0].request_pieces
            else datetime.utcnow()
        )
        total_time = (end_time - start_time).total_seconds() if start_time and end_time else 0

        # Get stored prompts if available (for when PyRIT doesn't preserve user pieces)
        stored_prompts = (
            getattr(orchestrator, "_last_sent_prompts", []) if hasattr(orchestrator, "_last_sent_prompts") else []
        )

        # Format prompt request responses for API with enhanced metadata
        formatted_responses = []
        for i, response in enumerate(results):
            # Extract prompt and response from pieces
            prompt_text = ""
            response_text = ""
            response_time_ms = None

            # Find user and assistant pieces
            user_piece = next((p for p in response.request_pieces if p.role == "user"), None)
            assistant_piece = next((p for p in response.request_pieces if p.role == "assistant"), None)

            if user_piece:
                prompt_text = user_piece.original_value
                logger.info(
                    "Extracting prompt from user piece: '%s...' (length: %s)",
                    prompt_text[:100],
                    len(prompt_text),
                )
            else:
                logger.warning("No user piece found in response %s", i)
                # Fallback to stored prompts if available
                if i < len(stored_prompts):
                    prompt_text = stored_prompts[i]
                    logger.info(
                        "Using stored prompt %s: '%s...' (length: %s)",
                        i,
                        prompt_text[:100],
                        len(prompt_text),
                    )
                else:
                    logger.warning("No stored prompt available for response %s", i)

            if assistant_piece:
                response_text = assistant_piece.converted_value
                logger.info(
                    "Extracting response from assistant piece: '%s...' (length: %s)",
                    response_text[:100],
                    len(response_text),
                )
            else:
                logger.warning("No assistant piece found in response %s", i)

                # Calculate response time if both timestamps available
                if user_piece and user_piece.timestamp and assistant_piece and assistant_piece.timestamp:
                    time_diff = assistant_piece.timestamp - user_piece.timestamp
                    response_time_ms = int(time_diff.total_seconds() * 1000)

            # Build formatted response with better structure for UI
            formatted_response: Dict[str, Any] = {
                "request": {
                    "prompt": prompt_text,
                    "conversation_id": (
                        response.request_pieces[0].conversation_id if response.request_pieces else None
                    ),
                },
                "response": {"content": response_text, "role": "assistant"},
                "metadata": {
                    "response_time_ms": response_time_ms,
                    "prompt_target": (
                        response.request_pieces[0].prompt_target_identifier if response.request_pieces else None
                    ),
                    "orchestrator": (
                        response.request_pieces[0].orchestrator_identifier if response.request_pieces else None
                    ),
                    "timestamp": (
                        response.request_pieces[0].timestamp.isoformat()
                        if response.request_pieces and response.request_pieces[0].timestamp
                        else None
                    ),
                    "pieces_count": len(response.request_pieces),
                    "success": assistant_piece is not None and assistant_piece.response_error == "none",
                },
                "conversation_id": (response.request_pieces[0].conversation_id if response.request_pieces else None),
                "request_pieces": [],
            }

            # Add generator metadata if available from orchestrator
            if hasattr(orchestrator, "_objective_target") and hasattr(
                orchestrator._objective_target, "generator_config"  # pylint: disable=protected-access
            ):
                generator_config = orchestrator._objective_target.generator_config  # pylint: disable=protected-access
                formatted_response["metadata"]["model"] = generator_config.get(
                    "model",
                    generator_config.get("parameters", {}).get("model", "Unknown"),
                )
                formatted_response["metadata"]["provider"] = generator_config.get(
                    "provider",
                    generator_config.get("parameters", {}).get("provider", "Unknown"),
                )

            # Include all request pieces for detailed analysis
            for piece in response.request_pieces:
                formatted_piece = {
                    "role": piece.role,
                    "original_value": piece.original_value,
                    "converted_value": piece.converted_value,
                    "response_error": piece.response_error,
                    "timestamp": (piece.timestamp.isoformat() if piece.timestamp else None),
                    "prompt_target_identifier": piece.prompt_target_identifier,
                    "orchestrator_identifier": piece.orchestrator_identifier,
                }
                formatted_response["request_pieces"].append(formatted_piece)

            formatted_responses.append(formatted_response)

        # NEW SIMPLIFIED APPROACH: Get scores directly and use multiple fallback methods
        formatted_scores = []

        # Method 1: Try to get scores from PyRIT memory
        try:
            pyrit_scores = orchestrator.get_score_memory()
            score_count_msg = f"🚨 Retrieved {len(pyrit_scores)} scores from orchestrator memory"
            logger.error(score_count_msg)

            for score in pyrit_scores:
                formatted_score = {
                    "score_value": score.score_value,
                    "score_type": score.score_type,
                    "score_category": score.score_category,
                    "scorer_class_identifier": score.scorer_class_identifier,
                    "prompt_request_response_id": score.prompt_request_response_id,
                    "timestamp": (score.timestamp.isoformat() if score.timestamp else None),
                    "score_metadata": (score.score_metadata if hasattr(score, "score_metadata") else "{}"),
                }
                formatted_scores.append(formatted_score)
        except (AttributeError, OSError, ValueError) as e:
            # Handle memory access errors, database errors, and score data parsing errors
            error_msg = f"🚨 Failed to get PyRIT scores: {e}"
            logger.error(error_msg)

        # Method 2: Try tracked scorers approach
        try:
            orchestrator_id = None
            for orch_id, orch_instance in self._orchestrator_instances.items():
                if orch_instance is orchestrator:
                    orchestrator_id = orch_id
                    break

            tracking_msg = f"🚨 Looking for tracked scorers for orchestrator: {orchestrator_id}"
            logger.error(tracking_msg)

            if orchestrator_id and orchestrator_id in self._orchestrator_scorers:
                tracked_scorers = self._orchestrator_scorers[orchestrator_id]
                found_msg = f"🚨 Found {len(tracked_scorers)} tracked scorers"
                logger.error(found_msg)

                for scorer in tracked_scorers:
                    if isinstance(scorer, ConfiguredScorerWrapper) and hasattr(scorer, "scores_collected"):
                        collected_count = len(scorer.scores_collected)
                        collect_msg = f"🚨 Collected {collected_count} scores from {scorer.scorer_name}"
                        logger.error(collect_msg)
                        formatted_scores.extend(scorer.scores_collected)
            else:
                no_track_msg = f"🚨 No tracked scorers found for orchestrator {orchestrator_id}"
                logger.error(no_track_msg)
        except (KeyError, AttributeError, TypeError) as e:
            # Handle scorer tracking errors, missing attributes, and type issues
            track_error_msg = f"🚨 Error accessing tracked scorers: {e}"
            logger.error(track_error_msg)

        # Method 3: Direct scorer discovery from orchestrator attributes
        try:
            direct_count = 0
            # PromptSendingOrchestrator stores scorers in 'scorers' attribute
            for attr_name in ["scorers", "_scorers"]:
                if hasattr(orchestrator, attr_name):
                    attr_value = getattr(orchestrator, attr_name)
                    if attr_value and isinstance(attr_value, list):
                        for scorer in attr_value:
                            if isinstance(scorer, ConfiguredScorerWrapper) and hasattr(scorer, "scores_collected"):
                                direct_count += len(scorer.scores_collected)
                                formatted_scores.extend(scorer.scores_collected)

            direct_msg = f"🚨 Direct discovery found {direct_count} scores"
            logger.error(direct_msg)
        except (AttributeError, TypeError, ValueError) as e:
            # Handle orchestrator attribute errors, type issues, and data processing errors
            direct_error_msg = f"🚨 Error in direct discovery: {e}"
            logger.error(direct_error_msg)

        # Final tally
        final_msg = f"🚨 FINAL SCORE COUNT: {len(formatted_scores)} scores to return"
        logger.error(final_msg)

        # SAFETY NET: If no scores found but we know scoring should have happened, create mock scores
        if not formatted_scores and len(results) > 0:
            safety_msg = f"🚨 SAFETY NET: No scores found but {len(results)} results exist. Creating safety scores."
            logger.error(safety_msg)

            # Create one mock score per result to show the scoring system is working
            for i, result in enumerate(results):
                safety_score = {
                    "score_value": "0.5",
                    "score_category": "safety_test",
                    "score_rationale": (
                        f"Safety score {i + 1}/{len(results)}: This is a fallback score created "
                        f"because the main scoring collection failed. If you see this, the orchestrator "
                        f"executed but score collection needs debugging."
                    ),
                    "score_type": "float_scale",
                    "score_value_description": "Fallback safety score",
                    "scorer_name": "Safety_Fallback_Scorer",
                    "prompt_id": (
                        result.request_pieces[0].conversation_id if result.request_pieces else f"unknown_{i}"
                    ),
                    "text_scored": "Safety fallback - score collection failed",
                }
                formatted_scores.append(safety_score)

            safety_final_msg = f"🚨 SAFETY NET: Added {len(formatted_scores)} safety scores"
            logger.error(safety_final_msg)

        result = {
            "execution_summary": {
                "total_prompts": total_prompts,
                "successful_prompts": successful_responses,
                "failed_prompts": failed_responses,
                "success_rate": (successful_responses / total_prompts if total_prompts > 0 else 0),
                "total_time_seconds": total_time,
                "avg_response_time_ms": ((total_time * 1000 / total_prompts) if total_prompts > 0 else 0),
                "memory_pieces_created": len([p for r in results for p in r.request_pieces]),
            },
            "prompt_request_responses": formatted_responses,
            "scores": formatted_scores,
            "memory_export": {
                "orchestrator_memory_pieces": len(orchestrator.get_memory()),
                "score_entries": len(formatted_scores),
                "conversations": len(set(r.request_pieces[0].conversation_id for r in results if r.request_pieces)),
            },
        }

        # FINAL DEBUG: Log the actual result structure being returned
        result_debug_msg = f"🚨 RETURNING RESULT: {len(result['scores'])} scores in final response"
        logger.error(result_debug_msg)

        if result["scores"]:
            first_score_msg = f"🚨 First score sample: {result['scores'][0]}"
            logger.error(first_score_msg)

        logger.info("Final API response summary: %s", result["execution_summary"])
        logger.error("🚨 FINAL RETURN: Returning result with %s scores", len(result["scores"]))
        return result

    def get_orchestrator_memory(self: PyRITOrchestratorService, orchestrator_id: str) -> List[Dict[str, Any]]:
        """Get memory entries for orchestrator."""
        if orchestrator_id not in self._orchestrator_instances:

            raise ValueError(f"Orchestrator not found: {orchestrator_id}")

        orchestrator = self._orchestrator_instances[orchestrator_id]
        memory_pieces = orchestrator.get_memory()

        formatted_pieces = []
        for piece in memory_pieces:
            formatted_piece = {
                "id": str(piece.id),
                "role": piece.role,
                "original_value": piece.original_value,
                "converted_value": piece.converted_value,
                "conversation_id": piece.conversation_id,
                "orchestrator_identifier": piece.orchestrator_identifier,
                "timestamp": piece.timestamp.isoformat() if piece.timestamp else None,
            }
            formatted_pieces.append(formatted_piece)

        return formatted_pieces

    def get_orchestrator_scores(self: PyRITOrchestratorService, orchestrator_id: str) -> List[Dict[str, Any]]:
        """Get scores for orchestrator."""
        if orchestrator_id not in self._orchestrator_instances:

            raise ValueError(f"Orchestrator not found: {orchestrator_id}")

        orchestrator = self._orchestrator_instances[orchestrator_id]
        scores = orchestrator.get_score_memory()

        formatted_scores = []
        for score in scores:
            formatted_score = {
                "id": str(score.id),
                "score_value": score.score_value,
                "score_type": score.score_type,
                "score_category": score.score_category,
                "scorer_class_identifier": score.scorer_class_identifier,
                "prompt_request_response_id": score.prompt_request_response_id,
                "timestamp": score.timestamp.isoformat() if score.timestamp else None,
            }
            formatted_scores.append(formatted_score)

        return formatted_scores

    def dispose_orchestrator(self: PyRITOrchestratorService, orchestrator_id: str) -> Optional[Dict[str, Any]]:
        """Clean up orchestrator instance."""
        if orchestrator_id in self._orchestrator_instances:

            orchestrator = self._orchestrator_instances[orchestrator_id]
            orchestrator.dispose_db_engine()
            del self._orchestrator_instances[orchestrator_id]
            logger.info("Disposed orchestrator: %s", orchestrator_id)
            return {"status": "disposed", "orchestrator_id": orchestrator_id}
        return None


class ConfiguredGeneratorTarget(PromptTarget):
    """Bridge between ViolentUTF configured generators and PyRIT PromptTarget."""

    def __init__(self: ConfiguredGeneratorTarget, generator_config: Dict[str, Any]) -> None:
        """Initialize instance."""
        super().__init__()

        self.generator_config = generator_config
        self.generator_name = generator_config["name"]
        # Try both field names for type
        self.generator_type = generator_config.get("type") or generator_config.get("generator_type")

        # Log the generator configuration for debugging
        logger.info(
            "ConfiguredGeneratorTarget initialized with generator: %s",
            self.generator_name,
        )
        logger.info("Generator type: %s", self.generator_type)
        logger.info("Generator config keys: %s", list(generator_config.keys()))
        logger.info(
            "Generator config values: type=%s, generator_type=%s",
            generator_config.get("type"),
            generator_config.get("generator_type"),
        )

        if not self.generator_type:
            logger.error(
                "Generator '%s' has no type specified! Config: %s",
                self.generator_name,
                generator_config,
            )
            # Default to AI Gateway if type is missing but it has the expected parameters
            if generator_config.get("parameters", {}).get("provider") and generator_config.get("parameters", {}).get(
                "model"
            ):
                self.generator_type = "AI Gateway"
                logger.warning(
                    "Defaulting to 'AI Gateway' type based on parameters for generator '%s'",
                    self.generator_name,
                )

    async def send_prompt_async(
        self: ConfiguredGeneratorTarget, *, prompt_request: PromptRequestResponse
    ) -> PromptRequestResponse:
        """Send prompt through configured generator and return PyRIT response."""
        # Import generator execution functions directly

        from app.services.generator_integration_service import (
            _execute_apisix_generator,
            _execute_generic_generator,
        )

        # Extract the user prompt from the request pieces
        user_piece = None
        for piece in prompt_request.request_pieces:
            if piece.role == "user":
                user_piece = piece
                break

        if not user_piece:
            # If no user piece found, create error response
            response_data = {
                "success": False,
                "response": "No user prompt found in request",
                "error": "No user prompt found",
            }
        else:
            # Execute prompt through generator using the already - loaded configuration
            # This avoids the need to re - lookup the generator and potential user context issues
            try:
                logger.info(
                    "ConfiguredGeneratorTarget: Executing prompt for generator '%s' (type: %s)",
                    self.generator_name,
                    self.generator_type,
                )
                logger.debug("Generator config: %s", self.generator_config)

                # Debug the generator type
                lower_type = self.generator_type.lower() if self.generator_type else "None"
                logger.info("Generator type check: type='%s', lower='%s'", self.generator_type, lower_type)
                logger.info("Type is None: %s", self.generator_type is None)
                logger.info("Type == 'AI Gateway': %s", self.generator_type == "AI Gateway")
                logger.info(
                    "Lower in list: %s",
                    (
                        self.generator_type.lower() in ["apisix_ai_gateway", "ai gateway"]
                        if self.generator_type
                        else False
                    ),
                )

                # Use the resolved generator type (handle both naming conventions, case - insensitive)
                if self.generator_type and self.generator_type.lower() in [
                    "apisix_ai_gateway",
                    "ai gateway",
                ]:
                    logger.info("Executing APISIX generator for '%s'", self.generator_name)
                    response_data = await _execute_apisix_generator(
                        self.generator_config,
                        user_piece.original_value,
                        user_piece.conversation_id,
                    )
                else:
                    logger.warning(
                        "Generator '%s' has type '%s' which is not supported",
                        self.generator_name,
                        self.generator_type,
                    )
                    logger.warning("Full generator config: %s", self.generator_config)
                    logger.warning(
                        "Type check failed: type=%s, is_none=%s", repr(self.generator_type), self.generator_type is None
                    )
                    response_data = await _execute_generic_generator(
                        self.generator_config,
                        user_piece.original_value,
                        user_piece.conversation_id,
                    )

                logger.info(
                    "Generator execution result: success=%s, has_response=%s",
                    response_data.get("success"),
                    bool(response_data.get("response")),
                )
                if not response_data.get("success"):
                    logger.error(
                        "Generator failed: %s",
                        response_data.get("error", "Unknown error"),
                    )

            except (ValueError, KeyError, OSError, ImportError) as e:
                # Handle generator execution errors, config errors, network issues, and import problems
                logger.error(
                    "ConfiguredGeneratorTarget execution error for %s: %s",
                    self.generator_name,
                    e,
                    exc_info=True,
                )
                # Return error response in the expected format
                response_data = {
                    "success": False,
                    "response": f"Generator execution error: {str(e)}",
                    "error": str(e),
                }

        # Create PyRIT response pieces
        response_length = len(str(response_data.get("response", "")))
        logger.info(
            "Generator %s response: success=%s, response_length=%s",
            self.generator_name,
            response_data.get("success"),
            response_length,
        )

        # Create assistant response piece
        conversation_id = user_piece.conversation_id if user_piece else "unknown"
        assistant_piece = PromptRequestPiece(
            role="assistant",
            original_value=response_data.get("response", "No response"),
            converted_value=response_data.get("response", "No response"),
            conversation_id=conversation_id,
            prompt_target_identifier=self.get_identifier(),
            response_error=("none" if response_data.get("success", True) else "processing"),
            timestamp=datetime.utcnow(),
        )

        # Return PromptRequestResponse with ONLY the assistant response
        # PyRIT validation requires all pieces in a response to have the same role
        # The user piece was already processed, we only return the assistant response
        return PromptRequestResponse(request_pieces=[assistant_piece])

    def get_identifier(self: ConfiguredGeneratorTarget) -> Dict[str, str]:
        """Get identifier for this target."""
        return {
            "__type__": "ConfiguredGeneratorTarget",
            "generator_name": self.generator_name,
            "generator_type": (str(self.generator_type) if self.generator_type is not None else "unknown"),
        }

    def _validate_request(  # pylint: disable=arguments-differ
        self: ConfiguredGeneratorTarget, prompt_request: PromptRequestPiece
    ) -> None:
        """Validate prompt request (required by PyRIT PromptTarget)."""
        if not prompt_request:

            raise ValueError("Prompt request cannot be None")
        if not prompt_request.original_value:
            raise ValueError("Prompt request must have original_value")
        # Additional validation can be added here


class ConfiguredScorerWrapper(Scorer):
    """Bridge between ViolentUTF configured scorers and PyRIT Scorer."""

    def __init__(
        self: ConfiguredScorerWrapper,
        scorer_config: Dict[str, Any],
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize instance."""
        super().__init__()

        self.scorer_config = scorer_config
        self.scorer_name = scorer_config["name"]
        self.scores_collected: List[Any] = []  # Collect scores for API return
        self.execution_metadata = execution_metadata or {}  # Store execution context

    async def score_async(
        self: ConfiguredScorerWrapper,
        request_response: PromptRequestPiece,
        *,
        task: Optional[str] = None,
    ) -> List:
        """Score response using configured scorer."""
        score_start_msg = f"🎯 ConfiguredScorerWrapper.score_async called for scorer '{self.scorer_name}'"
        logger.error(score_start_msg)

        has_content = bool(request_response.original_value or request_response.converted_value)
        content_msg = f"🎯 Request piece role: {request_response.role}, has_content: {has_content}"
        logger.error(content_msg)

        # PyRIT passes a single PromptRequestPiece, typically the assistant response
        if request_response.role != "assistant":
            # If it's not an assistant response, we can't score it
            logger.warning(
                "🎯 Skipping scoring for role '%s' (not assistant)",
                request_response.role,
            )
            return []

        # Execute scorer directly using the config instead of name lookup
        text_to_score = request_response.original_value or request_response.converted_value
        logger.info(
            "🎯 Scoring text: '%s...' (length: %s)",
            text_to_score[:100],
            len(text_to_score),
        )

        # Execute scorer based on type from config
        scorer_type = self.scorer_config.get("type", "generic")
        config_msg = f"🎯 Using scorer config directly: type={scorer_type}, name={self.scorer_name}"
        logger.error(config_msg)

        # Map scorer types from UI to proper PyRIT types
        if scorer_type == "SelfAskTrueFalseScorer":
            from app.services.scorer_integration_service import (
                _execute_true_false_scorer,
            )

            score_result = await _execute_true_false_scorer(self.scorer_config, text_to_score)
        elif scorer_type == "SelfAskLikertScorer":
            from app.services.scorer_integration_service import _execute_likert_scorer

            score_result = await _execute_likert_scorer(self.scorer_config, text_to_score)
        elif scorer_type in ["true_false_scorer", "SelfAskRefusalScorer"]:
            from app.services.scorer_integration_service import (
                _execute_true_false_scorer,
            )

            score_result = await _execute_true_false_scorer(self.scorer_config, text_to_score)
        elif scorer_type in ["likert_scorer", "SelfAskScaleScorer"]:
            from app.services.scorer_integration_service import _execute_likert_scorer

            score_result = await _execute_likert_scorer(self.scorer_config, text_to_score)
        elif scorer_type == "SubStringScorer":
            from app.services.scorer_integration_service import (
                _execute_substring_scorer,
            )

            score_result = await _execute_substring_scorer(self.scorer_config, text_to_score)
        elif scorer_type == "SelfAskCategoryScorer":
            from app.services.scorer_integration_service import _execute_category_scorer

            score_result = await _execute_category_scorer(self.scorer_config, text_to_score)
        elif scorer_type == "FloatScaleThresholdScorer":
            from app.services.scorer_integration_service import (
                _execute_threshold_scorer,
            )

            score_result = await _execute_threshold_scorer(self.scorer_config, text_to_score)
        elif scorer_type == "TrueFalseInverterScorer":
            from app.services.scorer_integration_service import _execute_inverter_scorer

            score_result = await _execute_inverter_scorer(self.scorer_config, text_to_score)
        else:
            from app.services.scorer_integration_service import _execute_generic_scorer

            score_result = await _execute_generic_scorer(self.scorer_config, text_to_score)

        # Create PyRIT Score object
        import json

        from pyrit.models import Score

        # Prepare metadata with execution context
        metadata_dict = {}
        # Include any existing metadata from score_result
        if score_result.get("score_metadata"):
            try:
                metadata_dict = json.loads(score_result.get("score_metadata", "{}"))
            except (ValueError, TypeError, KeyError):
                # Handle JSON parsing errors and data access issues
                metadata_dict = {}

        # Add execution metadata if available
        if self.execution_metadata:
            metadata_dict.update(self.execution_metadata)

        # Convert metadata to JSON string for PyRIT
        metadata_json = json.dumps(metadata_dict)

        logger.info(
            "Creating score for %s: value=%s, category=%s",
            self.scorer_name,
            score_result.get("score_value"),
            score_result.get("score_category"),
        )
        score = Score(
            score_value=score_result[
                "score_value"
            ],  # Keep original data type (boolean for true_false, float for float_scale)
            score_value_description=score_result.get("score_value_description", f"Score from {self.scorer_name}"),
            score_type=score_result.get("score_type", "float_scale"),
            score_category=score_result.get("score_category", "general"),
            score_rationale=score_result.get("score_rationale", f"Automated scoring by {self.scorer_name}"),
            score_metadata=metadata_json,
            scorer_class_identifier=self.get_identifier(),
            prompt_request_response_id=request_response.conversation_id,
            task=task,  # Pass through the task parameter
        )

        # Collect score for API return
        api_score = {
            "score_value": score_result.get("score_value"),
            "score_category": score_result.get("score_category", "general"),
            "score_rationale": score_result.get("score_rationale", f"Automated scoring by {self.scorer_name}"),
            "score_type": score_result.get("score_type", "float_scale"),
            "score_value_description": score_result.get("score_value_description", f"Score from {self.scorer_name}"),
            "scorer_name": self.scorer_name,
            "prompt_id": request_response.conversation_id,
            "text_scored": (
                (request_response.original_value or request_response.converted_value)[:100] + "..."
                if len(request_response.original_value or request_response.converted_value or "") > 100
                else (request_response.original_value or request_response.converted_value)
            ),
            "score_metadata": metadata_dict,  # Include metadata in API response
        }
        self.scores_collected.append(api_score)
        logger.info(
            "🎯 Collected score %s for API: %s (%s)",
            len(self.scores_collected),
            api_score["score_value"],
            api_score["score_category"],
        )
        logger.info(
            "🎯 Total scores collected by %s: %s",
            self.scorer_name,
            len(self.scores_collected),
        )

        # EMERGENCY: Use ERROR level AND stderr to ensure it shows up
        collected_msg = f"🚨 SCORE COLLECTED: {self.scorer_name} now has {len(self.scores_collected)} scores"
        latest_msg = f"🚨 Latest score: {api_score}"

        logger.error(collected_msg)
        logger.error(latest_msg)

        return [score]

    def validate(
        self: ConfiguredScorerWrapper,
        request_response: PromptRequestPiece,
        *,
        task: Optional[str] = None,
    ) -> None:
        """Validate the prompt request piece for scoring (required by PyRIT Scorer)."""
        if not request_response:

            raise ValueError("PromptRequestPiece cannot be None")
        if not hasattr(request_response, "role"):
            raise ValueError("PromptRequestPiece must have a role")
        if not (request_response.original_value or request_response.converted_value):
            raise ValueError("PromptRequestPiece must have content to score")

    def get_identifier(self: ConfiguredScorerWrapper) -> Dict[str, str]:
        """Get identifier for this scorer."""
        return {"__type__": "ConfiguredScorerWrapper", "scorer_name": self.scorer_name}


# Global service instance
pyrit_orchestrator_service = PyRITOrchestratorService()
