# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Base Classes for MCP Prompts

============================

This module provides the foundation for MCP prompt system with
template rendering, argument validation, and context management.
"""
import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Self

from jinja2 import BaseLoader, Environment, Template, TemplateError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PromptArgument(BaseModel):
    """Define prompt argument with validation."""

    name: str

    description: str
    type: str = "string"  # string, integer, boolean, array, object
    required: bool = False
    default: Optional[object] = None
    enum: Optional[List[object]] = None

    def validate_value(self: "Self", value: object) -> bool:
        """Validate value against this argument definition."""
        if self.required and value is None:
            return False

        if value is None and self.default is not None:
            return True

        if self.enum and hasattr(self.enum, "__contains__"):
            if value not in self.enum:  # pylint: disable=unsupported-membership-test
                return False

        # Basic type checking
        if self.type == "string" and not isinstance(value, str):
            return False
        elif self.type == "integer" and not isinstance(value, int):
            return False
        elif self.type == "boolean" and not isinstance(value, bool):
            return False
        elif self.type == "array" and not isinstance(value, list):
            return False
        elif self.type == "object" and not isinstance(value, dict):
            return False

        return True


class PromptDefinition(BaseModel):
    """Complete prompt definition for MCP protocol."""

    name: str

    description: str
    arguments: List[PromptArgument] = Field(default_factory=list)


class BasePrompt(ABC):
    """Provide Base class for all MCP prompts with template rendering."""

    def __init__(
        self: "Self",
        name: str,
        description: str,
        template: str,
        category: str = "general",
    ) -> None:
        """Initialize instance."""
        self.name = name

        self.description = description
        self.template_string = template
        self.category = category
        self.arguments: List[PromptArgument] = []
        self.template: Optional[Template] = None

        # Create Jinja2 environment with security features
        self.jinja_env = Environment(loader=BaseLoader(), autoescape=True, trim_blocks=True, lstrip_blocks=True)

        try:
            self.template = self.jinja_env.from_string(template)
        except TemplateError as e:
            logger.error("Template error in prompt %s: %s", name, e)
            self.template = None

    @abstractmethod
    async def get_context(self: "Self", params: Dict[str, object]) -> Dict[str, object]:
        """Get additional context for the prompt."""
        raise NotImplementedError

    def add_argument(self: "Self", argument: PromptArgument) -> None:
        """Add argument to prompt definition."""
        self.arguments.append(argument)

    def get_definition(self: "Self") -> PromptDefinition:
        """Get complete prompt definition for MCP."""
        return PromptDefinition(name=self.name, description=self.description, arguments=self.arguments)

    def validate_arguments(self: "Self", params: Dict[str, object]) -> tuple[bool, List[str]]:
        """Validate provided arguments against prompt definition."""
        errors = []

        # Check required arguments
        for arg in self.arguments:
            if arg.required and arg.name not in params:
                errors.append(f"Required argument '{arg.name}' is missing")
            elif arg.name in params and not arg.validate_value(params[arg.name]):
                errors.append(f"Invalid value for argument '{arg.name}': expected {arg.type}")

        return len(errors) == 0, errors

    async def render(self: "Self", params: Dict[str, object]) -> str:
        """Render the prompt with given parameters."""
        if not self.template:
            raise ValueError(f"Template not available for prompt: {self.name}")

        # Validate arguments
        is_valid, errors = self.validate_arguments(params)
        if not is_valid:
            raise ValueError(f"Argument validation failed: {', '.join(errors)}")

        # Get additional context
        try:
            context = await self.get_context(params)
        except Exception as e:
            logger.warning("Error getting context for prompt %s: %s", self.name, e)
            context = {}

        # Merge with provided parameters
        full_context = {**params, **context}

        # Apply defaults for missing arguments
        for arg in self.arguments:
            if arg.name not in full_context and arg.default is not None:
                full_context[arg.name] = arg.default

        # Render template
        try:
            rendered = self.template.render(**full_context)
            logger.debug("Successfully rendered prompt: %s", self.name)
            return rendered
        except Exception as e:
            logger.error("Prompt rendering error for %s: %s", self.name, e)
            raise ValueError(f"Failed to render prompt: {e}") from e


class StaticPrompt(BasePrompt):
    """A prompt that doesn't require additional context."""

    async def get_context(self: "Self", params: Dict[str, object]) -> Dict[str, object]:
        """Return empty context for static prompts."""
        return {}


class DynamicPrompt(BasePrompt):
    """A prompt that fetches dynamic context from external sources."""

    def __init__(
        self: "Self",
        name: str,
        description: str,
        template: str,
        context_provider: Optional[Callable] = None,
        category: str = "dynamic",
    ) -> None:
        """Initialize instance."""
        super().__init__(name, description, template, category)
        self.context_provider = context_provider

    async def get_context(self: "Self", params: Dict[str, object]) -> Dict[str, object]:
        """Get dynamic context from provider."""
        if self.context_provider:
            try:
                result = await self.context_provider(params)
                return result
            except Exception as e:
                logger.error("Error getting dynamic context for %s: %s", self.name, e)
                return {"error": str(e)}
        return {}


class PromptRegistry:
    """Registry for all available prompts with categorization."""

    def __init__(self: "Self") -> None:
        """Initialize instance."""
        self._prompts: Dict[str, BasePrompt] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self: "Self", prompt: BasePrompt) -> None:
        """Register prompt."""
        logger.info("Registering prompt: %s (category: %s)", prompt.name, prompt.category)
        self._prompts[prompt.name] = prompt

        # Add to category
        if prompt.category not in self._categories:
            self._categories[prompt.category] = []
        self._categories[prompt.category].append(prompt.name)

    def get(self: "Self", name: str) -> Optional[BasePrompt]:
        """Get prompt by name."""
        return self._prompts.get(name)

    def list_prompts(self: "Self") -> List[PromptDefinition]:
        """List all available prompts."""
        return [prompt.get_definition() for prompt in self._prompts.values()]

    def list_by_category(self: "Self", category: str) -> List[PromptDefinition]:
        """List prompts by category."""
        prompt_names = self._categories.get(category, [])

        return [self._prompts[name].get_definition() for name in prompt_names if name in self._prompts]

    def get_categories(self: "Self") -> List[str]:
        """Get all available categories."""
        return list(self._categories.keys())

    def get_stats(self: "Self") -> Dict[str, object]:
        """Get registry statistics."""
        return {
            "total_prompts": len(self._prompts),
            "categories": {cat: len(prompts) for cat, prompts in self._categories.items()},
            "category_count": len(self._categories),
        }


# Global prompt registry
prompt_registry = PromptRegistry()
