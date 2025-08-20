# # Copyright (c) 2024 ViolentUTF Project
# # Licensed under MIT License

"""
Base classes for the enhanced block system
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import markdown
from jinja2 import Environment, Template, meta

logger = logging.getLogger(__name__)


class BlockValidationError(Exception):
    """Block validation error"""

    pass


class BlockRenderError(Exception):
    """Block rendering error"""

    pass


class BlockDefinition:
    """Block definition metadata"""

    def __init__(
        self,
        block_type: str,
        display_name: str,
        description: str,
        category: str,
        configuration_schema: Dict,
        default_config: Dict,
        supported_formats: List[str] = None,
        required_variables: List[str] = None,
    ):
        self.block_type = block_type
        self.display_name = display_name
        self.description = description
        self.category = category
        self.configuration_schema = configuration_schema
        self.default_config = default_config
        self.supported_formats = supported_formats or ["PDF", "JSON", "Markdown"]
        self.required_variables = required_variables or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "block_type": self.block_type,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "configuration_schema": self.configuration_schema,
            "default_config": self.default_config,
            "supported_formats": self.supported_formats,
            "required_variables": self.required_variables,
        }


class BaseReportBlock(ABC):
    """Abstract base class for all report blocks"""

    def __init__(self, block_id: str, title: str, configuration: Dict):
        self.block_id = block_id
        self.title = title
        self.configuration = configuration
        self.rendered_content = {}
        self._jinja_env = Environment()

    @abstractmethod
    def get_definition(self) -> BlockDefinition:
        """Get block definition metadata"""
        pass

    def validate_configuration(self) -> List[str]:
        """Validate block configuration against schema"""
        errors = []

        # Get definition
        definition = self.get_definition()

        # Basic validation - check required fields
        schema = definition.configuration_schema
        if schema and "properties" in schema:
            for prop, prop_schema in schema["properties"].items():
                # Check required properties
                if prop_schema.get("required", False) and prop not in self.configuration:
                    errors.append(f"Required property '{prop}' is missing")

                # Type validation
                if prop in self.configuration:
                    value = self.configuration[prop]
                    expected_type = prop_schema.get("type")

                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(f"Property '{prop}' must be a string")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        errors.append(f"Property '{prop}' must be a number")
                    elif expected_type == "array" and not isinstance(value, list):
                        errors.append(f"Property '{prop}' must be an array")
                    elif expected_type == "object" and not isinstance(value, dict):
                        errors.append(f"Property '{prop}' must be an object")
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        errors.append(f"Property '{prop}' must be a boolean")

        # Custom validation
        custom_errors = self._custom_validation()
        errors.extend(custom_errors)

        return errors

    def _custom_validation(self) -> List[str]:
        """Override for custom validation logic"""
        return []

    @abstractmethod
    def process_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return processed results"""
        pass

    def render(self, format: str, data: Dict[str, Any]) -> Any:
        """Main render method that delegates to format-specific methods"""
        # Validate format
        definition = self.get_definition()
        if format not in definition.supported_formats:
            raise BlockRenderError(f"Format '{format}' not supported by block type '{definition.block_type}'")

        # Process data
        try:
            processed_data = self.process_data(data)
        except Exception as e:
            logger.error(f"Error processing data for block {self.block_id}: {str(e)}")
            raise BlockRenderError(f"Data processing failed: {str(e)}")

        # Render based on format
        try:
            if format in ["HTML", "PDF"]:
                content = self.render_html(processed_data)
            elif format == "Markdown":
                content = self.render_markdown(processed_data)
            elif format == "JSON":
                content = self.render_json(processed_data)
            else:
                raise BlockRenderError(f"Unsupported format: {format}")

            # Store rendered content
            self.rendered_content[format] = content
            return content

        except Exception as e:
            logger.error(f"Error rendering block {self.block_id} as {format}: {str(e)}")
            raise BlockRenderError(f"Rendering failed: {str(e)}")

    @abstractmethod
    def render_html(self, processed_data: Dict[str, Any]) -> str:
        """Render block as HTML"""
        pass

    @abstractmethod
    def render_markdown(self, processed_data: Dict[str, Any]) -> str:
        """Render block as Markdown"""
        pass

    @abstractmethod
    def render_json(self, processed_data: Dict[str, Any]) -> Dict:
        """Render block as JSON"""
        pass

    def get_required_variables(self) -> List[str]:
        """Get list of required variables for this block"""
        definition = self.get_definition()
        required = set(definition.required_variables)

        # Extract variables from templates
        if hasattr(self, "_get_template_variables"):
            template_vars = self._get_template_variables()
            required.update(template_vars)

        return list(required)

    def _get_template_variables(self) -> List[str]:
        """Extract variables from Jinja templates"""
        variables = set()

        # Check configuration for template strings
        for key, value in self.configuration.items():
            if isinstance(value, str) and "{{" in value:
                try:
                    ast = self._jinja_env.parse(value)
                    variables.update(meta.find_undeclared_variables(ast))
                except Exception:
                    pass

        return list(variables)

    def _render_template(self, template_string: str, context: Dict[str, Any]) -> str:
        """Safely render a Jinja template"""
        try:
            template = Template(template_string)
            return template.render(**context)
        except Exception as e:
            logger.warning(f"Template rendering error in block {self.block_id}: {str(e)}")
            return template_string

    def _markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown to HTML"""
        return markdown.markdown(markdown_text, extensions=["tables", "fenced_code", "nl2br", "toc"])

    def _format_number(self, value: float, decimals: int = 1) -> str:
        """Format number for display"""
        if isinstance(value, (int, float)):
            return f"{value:.{decimals}f}"
        return str(value)

    def _get_severity_color(self, score: float) -> str:
        """Get color based on severity score"""
        if score >= 9.0:
            return "#d32f2f"  # Critical - Red
        elif score >= 7.0:
            return "#f57c00"  # High - Orange
        elif score >= 4.0:
            return "#fbc02d"  # Medium - Yellow
        else:
            return "#388e3c"  # Low - Green

    def _get_severity_label(self, score: float) -> str:
        """Get severity label from score"""
        if score >= 9.0:
            return "Critical"
        elif score >= 7.0:
            return "High"
        elif score >= 4.0:
            return "Medium"
        else:
            return "Low"


class BlockRegistry:
    """Registry for managing available block types"""

    def __init__(self):
        self._blocks = {}
        self._categories = set()

    def register(self, block_class: type, force: bool = False):
        """Register a new block type"""
        if not issubclass(block_class, BaseReportBlock):
            raise ValueError(f"Block class must inherit from BaseReportBlock")

        # Create temporary instance to get definition
        try:
            temp_instance = block_class("temp", "temp", {})
            definition = temp_instance.get_definition()
        except Exception as e:
            raise ValueError(f"Failed to get block definition: {str(e)}")

        # Check if already registered
        if definition.block_type in self._blocks and not force:
            raise ValueError(f"Block type '{definition.block_type}' already registered")

        # Register block
        self._blocks[definition.block_type] = {"class": block_class, "definition": definition}

        # Track category
        self._categories.add(definition.category)

        logger.info(f"Registered block type: {definition.block_type}")

    def unregister(self, block_type: str):
        """Unregister a block type"""
        if block_type in self._blocks:
            del self._blocks[block_type]
            logger.info(f"Unregistered block type: {block_type}")

    def get_block_class(self, block_type: str) -> type:
        """Get block class by type"""
        if block_type not in self._blocks:
            raise ValueError(f"Unknown block type: {block_type}")

        return self._blocks[block_type]["class"]

    def get_definition(self, block_type: str) -> BlockDefinition:
        """Get block definition by type"""
        if block_type not in self._blocks:
            raise ValueError(f"Unknown block type: {block_type}")

        return self._blocks[block_type]["definition"]

    def get_all_definitions(self) -> List[BlockDefinition]:
        """Get all registered block definitions"""
        return [b["definition"] for b in self._blocks.values()]

    def get_definitions_by_category(self, category: str) -> List[BlockDefinition]:
        """Get block definitions by category"""
        return [b["definition"] for b in self._blocks.values() if b["definition"].category == category]

    def get_categories(self) -> List[str]:
        """Get all registered categories"""
        return sorted(list(self._categories))

    def create_block(self, block_type: str, block_id: str, title: str, configuration: Dict) -> BaseReportBlock:
        """Create a block instance"""
        block_class = self.get_block_class(block_type)

        # Merge with default config
        definition = self.get_definition(block_type)
        merged_config = {**definition.default_config, **configuration}

        # Create instance
        instance = block_class(block_id, title, merged_config)

        # Validate configuration
        errors = instance.validate_configuration()
        if errors:
            raise BlockValidationError(f"Block configuration errors: {', '.join(errors)}")

        return instance

    def export_registry(self) -> Dict[str, Any]:
        """Export registry as JSON-serializable dict"""
        return {
            "blocks": {
                block_type: {"definition": definition.to_dict()}
                for block_type, block_info in self._blocks.items()
                for definition in [block_info["definition"]]
            },
            "categories": list(self._categories),
        }


# Global registry instance
block_registry = BlockRegistry()


# Utility functions
def validate_block_config(block_type: str, configuration: Dict) -> List[str]:
    """Validate block configuration without creating instance"""
    try:
        definition = block_registry.get_definition(block_type)

        # Create temporary instance for validation
        block_class = block_registry.get_block_class(block_type)
        temp_instance = block_class("temp", "temp", configuration)

        return temp_instance.validate_configuration()
    except Exception as e:
        return [f"Validation error: {str(e)}"]


def get_block_variables(block_type: str, configuration: Dict) -> List[str]:
    """Get required variables for a block configuration"""
    try:
        block_class = block_registry.get_block_class(block_type)
        temp_instance = block_class("temp", "temp", configuration)
        return temp_instance.get_required_variables()
    except Exception:
        return []
