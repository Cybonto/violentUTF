# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""PyRIT Integration Service

Provides PyRIT-based AI red-teaming functionality for ViolentUTF platform
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class PyRITService:
    """Service class for PyRIT integration."""

    def __init__(self: "PyRITService") -> None:
        """Initialize instance."""
        self.memory = None

        self._initialize_pyrit()

    def _initialize_pyrit(self: "PyRITService") -> None:
        """Initialize PyRIT memory and core components."""
        try:

            from pyrit.memory import DuckDBMemory  # noqa: F401  # pylint: disable=unused-import
            from pyrit.models import (  # noqa: F401  # pylint: disable=unused-import
                PromptRequestPiece,
                PromptRequestResponse,
            )

            # Don't initialize DuckDB memory here to avoid conflicts with orchestrator service
            # The orchestrator service handles its own memory management
            logger.info("✅ PyRIT models available (memory handled by orchestrator service)")
            self.memory = None  # Prevent conflicts

        except ImportError as e:
            logger.error("❌ PyRIT not available: %s", e)
            self.memory = None
        except Exception as e:
            logger.error("❌ Failed to initialize PyRIT: %s", e)
            self.memory = None

    def is_available(self: "PyRITService") -> bool:
        """Check if PyRIT is properly initialized."""
        try:

            from pyrit.models import PromptRequestPiece  # noqa: F401  # pylint: disable=unused-import

            return True  # PyRIT is available if we can import its models
        except ImportError:
            return False

    async def create_prompt_target(
        self: "PyRITService", target_config: Dict[str, object]
    ) -> Optional[Dict[str, object]]:
        """Create a PyRIT PromptTarget from configuration

        This replaces the simulated target creation in generators
        """
        if not self.is_available():

            raise RuntimeError("PyRIT is not available")

        try:
            target_type = target_config.get("type", "HTTPTarget")

            if target_type == "AI Gateway":
                return await create_apisix_target(target_config)
            elif target_type == "HTTPTarget":
                return await create_http_target(target_config)
            else:
                raise ValueError(f"Unsupported target type: {target_type}")

        except Exception as e:
            logger.error("Failed to create PyRIT target: %s", e)
            raise


async def create_apisix_target(config: Dict[str, object]) -> object:
    """Create APISIX-based PyRIT target."""
    from pyrit.models import PromptRequestPiece, PromptRequestResponse
    from pyrit.prompt_target import PromptChatTarget

    class APISIXPromptTarget(PromptChatTarget):
        """Customize PyRIT target for APISIX AI Gateway."""

        def __init__(self: "APISIXPromptTarget", provider: str, model: str, base_url: str, **kwargs: object) -> None:

            super().__init__()
            self.provider = provider
            self.model = model
            self.base_url = base_url
            self.endpoint_url = self._get_endpoint_url(provider, model)

        def _get_endpoint_url(self: "APISIXPromptTarget", provider: str, model: str) -> str:
            """Map provider/model to APISIX endpoint."""
            # Import the mapping function from generators.py

            from app.api.endpoints.generators import get_apisix_endpoint_for_model

            endpoint = get_apisix_endpoint_for_model(provider, model)
            if endpoint:
                return f"{self.base_url}{endpoint}"
            else:
                raise ValueError(f"No APISIX route for {provider}/{model}")

        async def send_prompt_async(  # pylint: disable=arguments-differ
            self: "APISIXPromptTarget", prompt_request: PromptRequestPiece
        ) -> PromptRequestResponse:
            """Send prompt through APISIX gateway."""
            try:
                # Prepare request payload
                payload = {
                    "messages": [{"role": "user", "content": prompt_request.original_value}],
                    "temperature": 0.7,
                    "max_tokens": 1000,
                }

                headers = {
                    "Content-Type": "application/json",
                    "X-API-Gateway": "APISIX",
                }

                # Make the API call
                response = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=30)

                if response.status_code == 200:
                    result = response.json()

                    # Extract response based on provider
                    if self.provider == "openai":
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    elif self.provider == "anthropic":
                        content = result.get("content", [{}])[0].get("text", "")
                    else:
                        content = str(result.get("response", result))

                    # Create response piece
                    response_piece = PromptRequestPiece(
                        role="assistant",
                        original_value=content,
                        converted_value=content,
                        prompt_target_identifier={
                            "type": "apisix_gateway",
                            "provider": self.provider,
                            "model": self.model,
                        },
                    )

                    return PromptRequestResponse(request_pieces=[response_piece])

                else:
                    error_msg = f"APISIX call failed: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            except Exception as e:
                logger.error("APISIX target error: %s", e)
                raise

        def is_json_response_supported(self: "APISIXPromptTarget") -> bool:
            return True

    # Create and return the target
    provider = str(config.get("provider", "openai"))
    model = str(config.get("model", "gpt-3.5-turbo"))
    base_url = str(config.get("base_url", "http://localhost:9080"))

    return APISIXPromptTarget(provider, model, base_url)  # pylint: disable=abstract-class-instantiated


async def create_http_target(config: Dict[str, object]) -> None:
    """Create HTTP-based PyRIT target."""
    # This would implement a generic HTTP target
    # For now, return a placeholder
    raise NotImplementedError("HTTP target not yet implemented")


async def run_red_team_orchestrator(
    target: object,
    prompts: List[str],
    conversation_id: Optional[str] = None,
) -> List[Dict[str, object]]:
    """Run PyRIT orchestrator for red-teaming

    This replaces simulated orchestrator functionality
    """
    if not pyrit_service.is_available():

        raise RuntimeError("PyRIT is not available")

    try:
        from pyrit.models import PromptRequestPiece
        from pyrit.orchestrator import PromptSendingOrchestrator

        # Create orchestrator
        orchestrator = PromptSendingOrchestrator(  # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
            prompt_target=target, memory=pyrit_service.memory
        )

        results = []

        for prompt in prompts:
            # Create prompt request piece
            prompt_piece = PromptRequestPiece(
                role="user",
                original_value=prompt,
                converted_value=prompt,
                conversation_id=conversation_id or str(uuid.uuid4()),
            )

            # Send prompt and get response
            response = await orchestrator.send_prompts_async(  # pylint: disable=too-many-function-args,missing-kwoa
                [prompt_piece]
            )

            # Convert to result format
            result = {
                "prompt": prompt,
                "response": (response[0].request_pieces[0].original_value if response else "No response"),
                "timestamp": datetime.utcnow().isoformat(),
                "conversation_id": conversation_id,
            }
            results.append(result)

            logger.info("PyRIT orchestrator processed prompt: %s...", prompt[:50])

        return results

    except Exception as e:
        logger.error("PyRIT orchestrator error: %s", e)
        raise


def get_conversation_history(conversation_id: str) -> List[Dict[str, object]]:
    """Get conversation history from PyRIT memory."""
    if not pyrit_service.is_available():

        return []

    try:
        # Query memory for conversation history
        # This would use PyRIT's memory querying capabilities
        # For now, return empty list
        return []

    except Exception as e:
        logger.error("Failed to get conversation history: %s", e)
        return []


# Global PyRIT service instance
pyrit_service = PyRITService()
