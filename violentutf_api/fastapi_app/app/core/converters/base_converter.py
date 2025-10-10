# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Base converter class for dataset transformations.

Provides common interface and functionality for all dataset converters.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseConverter(ABC):
    """Abstract base class for dataset converters."""

    def __init__(self, validation_enabled: bool = True) -> None:
        """Initialize base converter.

        Args:
            validation_enabled: Whether to enable validation
        """
        self.validation_enabled = validation_enabled

    @abstractmethod
    def convert(self, config: Any) -> Dict[str, Any]:  # noqa: ANN401
        """Convert dataset according to configuration.

        Args:
            config: Conversion configuration

        Returns:
            Conversion result dictionary
        """
        raise NotImplementedError

    def validate_input(self, input_path: str) -> bool:
        """Validate input file or path.

        Args:
            input_path: Path to input file or directory

        Returns:
            True if input is valid, False otherwise
        """
        if not input_path:
            return False

        # Basic validation - can be overridden by subclasses
        try:
            from pathlib import Path

            path = Path(input_path)
            return path.exists()
        except Exception:
            return False

    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats.

        Returns:
            List of supported format names
        """
        return ["pyrit", "json"]

    def get_metadata(self) -> Dict[str, Any]:
        """Get converter metadata.

        Returns:
            Metadata dictionary with converter information
        """
        return {
            "name": self.__class__.__name__,
            "description": "Base dataset converter",
            "version": "1.0.0",
            "domain": "general",
        }

    def validate_config(self, config: Any) -> bool:  # noqa: ANN401
        """Validate conversion configuration.

        Args:
            config: Configuration to validate

        Returns:
            True if configuration is valid, False otherwise
        """
        # Basic validation - can be overridden by subclasses
        return config is not None
