# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Dataset API Client for ViolentUTF

This module provides the DatasetAPIClient class for integrating the enhanced
NativeDatasetSelector component with the FastAPI backend to restore access
to all 18 datasets (10 PyRIT + 8 ViolentUTF).

Resolves Issue #239: Dataset Access Regression
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
import streamlit as st

logger = logging.getLogger(__name__)


@dataclass
class DatasetType:
    """Dataset type definition from API"""

    name: str
    description: str
    category: str
    config_required: bool
    available_configs: Optional[Dict[str, List[str]]] = None


@dataclass
class CategoryInfo:
    """Category information for UI organization"""

    name: str
    datasets: List[str]
    description: str
    icon: str


class DatasetAPIClient:
    """
    API client for dataset type retrieval and management

    Integrates with ViolentUTF FastAPI backend to load all available datasets
    and organize them into categories for the enhanced UI.
    """

    def __init__(self, base_url: str = "http://localhost:9080/api", auth_token: Optional[str] = None) -> None:
        """
        Initialize the dataset API client

        Args:
            base_url: Base URL for the API (default: localhost:9080/api)
            auth_token: JWT authentication token (optional, will try to get from session)
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or self._get_auth_token()
        self.session = requests.Session()
        self._setup_session()

        # Cache for dataset types (valid for 5 minutes)
        self._dataset_cache: Optional[List[DatasetType]] = None
        self._cache_timestamp: float = 0
        self._cache_duration = 300  # 5 minutes

    def _get_auth_token(self) -> Optional[str]:
        """Get authentication token from Streamlit session state"""
        try:
            # Try to get JWT token from session state
            if hasattr(st, "session_state") and "jwt_token" in st.session_state:
                return st.session_state.jwt_token
            elif hasattr(st, "session_state") and "api_token" in st.session_state:
                return st.session_state.api_token
        except Exception as e:
            logger.debug("Could not get auth token from session state: %s", e)
        return None

    def _setup_session(self) -> None:
        """Set up requests session with headers and timeouts"""
        if self.auth_token:
            self.session.headers.update(
                {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            )

        # Set reasonable timeouts (Note: timeout is set per request, not on session)
        # self.session.timeout = (5, 30)  # (connect, read) timeouts

    async def get_dataset_types(self) -> List[DatasetType]:
        """
        Get all available dataset types from API

        Returns:
            List of DatasetType objects

        Raises:
            APIError: If API request fails
        """
        # Check cache first
        if self._is_cache_valid() and self._dataset_cache is not None:
            logger.debug("Returning cached dataset types")
            return self._dataset_cache

        try:
            logger.info("Fetching dataset types from API: %s/v1/datasets/types", self.base_url)

            response = self.session.get(f"{self.base_url}/v1/datasets/types", timeout=(5, 30))
            response.raise_for_status()

            data = response.json()

            # Parse dataset types
            dataset_types = []
            for dataset_data in data.get("dataset_types", []):
                dataset_type = DatasetType(
                    name=dataset_data["name"],
                    description=dataset_data["description"],
                    category=dataset_data["category"],
                    config_required=dataset_data["config_required"],
                    available_configs=dataset_data.get("available_configs"),
                )
                dataset_types.append(dataset_type)

            # Cache the results
            self._dataset_cache = dataset_types
            self._cache_timestamp = time.time()

            logger.info("Successfully loaded %d dataset types from API", len(dataset_types))
            return dataset_types

        except requests.exceptions.RequestException as e:
            logger.error("API request failed: %s", e)
            raise APIError(f"Failed to fetch dataset types: {str(e)}") from e
        except Exception as e:
            logger.error("Unexpected error fetching dataset types: %s", e)
            raise APIError(f"Unexpected error: {str(e)}") from e

    async def get_dataset_categories(self) -> Dict[str, CategoryInfo]:
        """
        Get organized dataset categories for UI

        Returns:
            Dictionary mapping category keys to CategoryInfo objects
        """
        dataset_types = await self.get_dataset_types()

        # Category mappings for UI organization
        category_mappings = {
            "redteaming": {
                "name": "AI Red-Teaming & Security",
                "description": "Red-teaming, adversarial testing, and security assessment datasets",
                "icon": "🔴",
                "categories": ["redteaming", "safety", "adversarial", "jailbreaking", "dangerous"],
            },
            "cognitive_behavioral": {
                "name": "Cognitive & Behavioral Assessment",
                "description": "Cognitive behavioral security assessment datasets",
                "icon": "🧠",
                "categories": ["cognitive_behavioral"],
            },
            "legal_reasoning": {
                "name": "Legal & Regulatory Reasoning",
                "description": "Professional-validated legal reasoning datasets",
                "icon": "⚖️",
                "categories": ["legal_reasoning"],
            },
            "mathematical_reasoning": {
                "name": "Mathematical & Document Reasoning",
                "description": "Mathematical and planning reasoning datasets",
                "icon": "🔢",
                "categories": ["reasoning_evaluation", "mathematical"],
            },
            "spatial_reasoning": {
                "name": "Spatial & Graph Reasoning",
                "description": "Spatial navigation and graph reasoning datasets",
                "icon": "🗺️",
                "categories": ["spatial", "graph"],
            },
            "privacy_evaluation": {
                "name": "Privacy & Contextual Integrity",
                "description": "Privacy evaluation with Contextual Integrity Theory",
                "icon": "🔒",
                "categories": ["privacy_evaluation", "privacy"],
            },
            "meta_evaluation": {
                "name": "Meta-Evaluation & Judge Assessment",
                "description": "Meta-evaluation and judge-the-judge assessment",
                "icon": "👨‍⚖️",
                "categories": ["meta_evaluation", "evaluation"],
            },
            "bias_evaluation": {
                "name": "Bias & Fairness Testing",
                "description": "Bias detection and fairness evaluation datasets",
                "icon": "⚖️",
                "categories": ["bias"],
            },
        }

        # Initialize categories
        categories: Dict[str, CategoryInfo] = {}
        for category_key, mapping in category_mappings.items():
            categories[category_key] = CategoryInfo(
                name=str(mapping["name"]),
                datasets=[],
                description=str(mapping["description"]),
                icon=str(mapping["icon"]),
            )

        # Organize datasets into categories
        for dataset_type in dataset_types:
            # Find appropriate category
            assigned = False
            for category_key, mapping in category_mappings.items():
                if dataset_type.category in mapping["categories"]:
                    categories[category_key].datasets.append(dataset_type.name)
                    assigned = True
                    break

            # If no category found, add to appropriate default based on dataset name
            if not assigned:
                if any(term in dataset_type.name.lower() for term in ["cognitive", "behavioral"]):
                    categories["cognitive_behavioral"].datasets.append(dataset_type.name)
                elif any(term in dataset_type.name.lower() for term in ["legal", "bench"]):
                    categories["legal_reasoning"].datasets.append(dataset_type.name)
                elif any(term in dataset_type.name.lower() for term in ["math", "reasoning", "planning"]):
                    categories["mathematical_reasoning"].datasets.append(dataset_type.name)
                elif any(term in dataset_type.name.lower() for term in ["graph", "spatial"]):
                    categories["spatial_reasoning"].datasets.append(dataset_type.name)
                elif any(term in dataset_type.name.lower() for term in ["privacy", "confaide"]):
                    categories["privacy_evaluation"].datasets.append(dataset_type.name)
                elif any(term in dataset_type.name.lower() for term in ["judge", "meta", "evaluation"]):
                    categories["meta_evaluation"].datasets.append(dataset_type.name)
                elif any(term in dataset_type.name.lower() for term in ["bias", "stereotype"]):
                    categories["bias_evaluation"].datasets.append(dataset_type.name)
                else:
                    # Default to red-teaming category
                    categories["redteaming"].datasets.append(dataset_type.name)

        # Remove empty categories
        categories = {k: v for k, v in categories.items() if v.datasets}

        logger.info("Organized %d datasets into %d categories", len(dataset_types), len(categories))
        return categories

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._dataset_cache is None:
            return False

        return (time.time() - self._cache_timestamp) < self._cache_duration

    def invalidate_cache(self) -> None:
        """Invalidate the dataset cache"""
        self._dataset_cache = None
        self._cache_timestamp = 0.0
        logger.debug("Dataset cache invalidated")

    def _handle_api_error(self, error: Exception) -> None:
        """Handle API errors with appropriate logging and user feedback"""
        logger.error("API error: %s", error)

        # Could add user notification here
        if hasattr(st, "error"):
            st.error(f"API Error: {str(error)}")


class APIError(Exception):
    """Custom exception for API-related errors"""


# Dataset name mappings for backward compatibility
DATASET_NAME_MAPPINGS = {
    "legalbench_reasoning": "legalbench_professional",
    "docmath_evaluation": "docmath_mathematical",
    "graphwalk_reasoning": "graphwalk_spatial",
    "acpbench_reasoning": "acpbench_planning",
}


def map_dataset_name(original_name: str) -> str:
    """
    Map dataset names for backward compatibility

    Args:
        original_name: Original dataset name

    Returns:
        Mapped dataset name (or original if no mapping exists)
    """
    return DATASET_NAME_MAPPINGS.get(original_name, original_name)


def reverse_map_dataset_name(mapped_name: str) -> str:
    """
    Reverse map dataset names for backward compatibility

    Args:
        mapped_name: Mapped dataset name

    Returns:
        Original dataset name (or mapped if no reverse mapping exists)
    """
    reverse_mappings = {v: k for k, v in DATASET_NAME_MAPPINGS.items()}
    return reverse_mappings.get(mapped_name, mapped_name)
