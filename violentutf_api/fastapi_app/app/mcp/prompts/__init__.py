# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""MCP Prompts Module

=================

This module provides MCP prompt functionality for ViolentUTF with
security testing templates and dynamic prompt generation.
"""
import logging
from typing import Any, Dict, List, Optional, Self

# Import prompt providers to auto-register them
from app.mcp.prompts import security, testing  # noqa: F401
from app.mcp.prompts.base import prompt_registry

logger = logging.getLogger(__name__)


class PromptsManager:
    """Manage MCP prompts for ViolentUTF."""

    def __init__(self: "Self") -> None:

        self.registry = prompt_registry
        self._initialized = False

    async def initialize(self: "Self") -> None:
        """Initialize prompts manager."""
        if self._initialized:

            return

        logger.info("Initializing MCP prompts manager...")
        self._initialized = True
        logger.info(
            "Prompts manager initialized with %s prompts",
            len(self.registry._prompts),  # pylint: disable=protected-access
        )

    async def list_prompts(self: "Self") -> List[Dict[str, Any]]:
        """List all available prompts."""
        if not self._initialized:

            await self.initialize()

        prompts = self.registry.list_prompts()
        return [prompt.dict() for prompt in prompts]

    async def get_prompt(self: "Self", name: str, args: Optional[Dict[str, Any]] = None) -> str:
        """Get and render a prompt by name."""
        if not self._initialized:

            await self.initialize()

        prompt = self.registry.get(name)
        if not prompt:
            raise ValueError(f"Prompt not found: {name}")

        result = await prompt.render(args or {})
        return str(result)

    def get_prompt_info(self: "Self", name: str) -> Dict[str, Any]:
        prompt = self.registry.get(name)

        if not prompt:
            return {"error": f"Prompt not found: {name}"}

        definition = prompt.get_definition()
        result = definition.dict()
        return dict(result)


# Global prompts manager
prompts_manager = PromptsManager()

__all__ = ["prompts_manager", "prompt_registry"]
