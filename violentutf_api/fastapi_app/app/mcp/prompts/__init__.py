# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
MCP Prompts Module

=================

This module provides MCP prompt functionality for ViolentUTF with
security testing templates and dynamic prompt generation.
"""

import logging
from typing import Any, Dict, List

# Import prompt providers to auto-register them
from app.mcp.prompts import security, testing
from app.mcp.prompts.base import prompt_registry

logger = logging.getLogger(__name__)


class PromptsManager:
    """Manages MCP prompts for ViolentUTF."""

    def __init__(self) -> None:
        """Initialize the instance."""
        self.registry = prompt_registry
        self._initialized = False

    async def initialize(self):
        """Initialize prompts manager."""
        if self._initialized:
            return

        logger.info("Initializing MCP prompts manager...")
        self._initialized = True
        logger.info(f"Prompts manager initialized with {len(self.registry._prompts)} prompts")

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """List all available prompts."""
        if not self._initialized:
            await self.initialize()

        prompts = self.registry.list_prompts()
        return [prompt.dict() for prompt in prompts]

    async def get_prompt(self, name: str, args: Dict[str, Any] = None) -> str:
        """Get and render a prompt by name."""
        if not self._initialized:
            await self.initialize()

        prompt = self.registry.get(name)
        if not prompt:
            raise ValueError(f"Prompt not found: {name}")

        return await prompt.render(args or {})

    def get_prompt_info(self, name: str) -> Dict[str, Any]:
        """Get prompt definition and metadata."""
        prompt = self.registry.get(name)
        if not prompt:
            return {"error": f"Prompt not found: {name}"}

        definition = prompt.get_definition()
        return definition.dict()


# Global prompts manager
prompts_manager = PromptsManager()

__all__ = ["prompts_manager", "prompt_registry"]
