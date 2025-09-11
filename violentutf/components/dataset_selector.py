# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Native Dataset Selector Component for ViolentUTF

This module provides the NativeDatasetSelector class for managing the selection
and organization of native datasets across different evaluation domains.
"""

import logging
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger(__name__)


class NativeDatasetSelector:
    """Enhanced dataset selector supporting native dataset integration with categories"""

    def __init__(self) -> None:
        """Initialize the native dataset selector with predefined categories"""
        self.dataset_categories = {
            "cognitive_behavioral": {
                "name": "Cognitive & Behavioral Assessment",
                "datasets": ["ollegen1_cognitive"],
                "description": "Cognitive behavioral security assessment datasets",
                "icon": "🧠",
            },
            "redteaming": {
                "name": "AI Red-Teaming & Security",
                "datasets": ["garak_redteaming"],
                "description": "Red-teaming and adversarial prompt datasets",
                "icon": "🔴",
            },
            "legal_reasoning": {
                "name": "Legal & Regulatory Reasoning",
                "datasets": ["legalbench_professional"],
                "description": "Professional-validated legal reasoning datasets",
                "icon": "⚖️",
            },
            "mathematical_reasoning": {
                "name": "Mathematical & Document Reasoning",
                "datasets": ["docmath_mathematical", "acpbench_planning"],
                "description": "Mathematical and planning reasoning datasets",
                "icon": "🔢",
            },
            "spatial_reasoning": {
                "name": "Spatial & Graph Reasoning",
                "datasets": ["graphwalk_spatial"],
                "description": "Spatial navigation and graph reasoning datasets",
                "icon": "🗺️",
            },
            "privacy_evaluation": {
                "name": "Privacy & Contextual Integrity",
                "datasets": ["confaide_privacy"],
                "description": "Privacy evaluation with Contextual Integrity Theory",
                "icon": "🔒",
            },
            "meta_evaluation": {
                "name": "Meta-Evaluation & Judge Assessment",
                "datasets": ["judgebench_meta"],
                "description": "Meta-evaluation and judge-the-judge assessment",
                "icon": "👨‍⚖️",
            },
        }

        # Initialize session state for dataset selection
        if "selected_dataset_category" not in st.session_state:
            st.session_state.selected_dataset_category = None
        if "selected_native_dataset" not in st.session_state:
            st.session_state.selected_native_dataset = None

    def render_dataset_selection_interface(self) -> None:
        """Render the enhanced dataset selection interface with categories"""
        st.title("🗂️ Configure Native Datasets")
        st.markdown("Select and configure datasets for your AI security evaluation")

        # Dataset category tabs
        category_names = [cat["name"] for cat in self.dataset_categories.values()]
        category_tabs = st.tabs(category_names)

        for idx, (category_key, category_info) in enumerate(self.dataset_categories.items()):
            with category_tabs[idx]:
                self.render_category_interface(category_key, category_info)

    def render_category_interface(self, category_key: str, category_info: Dict[str, Any]) -> None:
        """Render interface for specific dataset category"""
        st.markdown(f"## {category_info['icon']} {category_info['name']}")
        st.markdown(category_info["description"])

        # Dataset selection within category
        for dataset_name in category_info["datasets"]:
            with st.expander(f"📊 {dataset_name}", expanded=False):
                self.render_dataset_card(dataset_name, category_key)

    def render_dataset_card(self, dataset_name: str, category_key: str) -> None:
        """Render individual dataset card with selection and preview"""
        # Get dataset metadata
        metadata = self.get_dataset_metadata(dataset_name)

        # Dataset information display
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"**Dataset:** {dataset_name}")
            st.markdown(f"**Domain:** {metadata.get('domain', 'Unknown')}")
            st.markdown(f"**Entries:** {metadata.get('total_entries', 'Unknown'):,}")
            st.markdown(f"**Format:** {metadata.get('pyrit_format', 'Unknown')}")

        with col2:
            st.metric("Size", metadata.get("file_size", "Unknown"))
            st.metric("Status", metadata.get("status", "Available"))

        # Selection and action buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button(f"Select {dataset_name}", key=f"select_{dataset_name}"):
                st.session_state.selected_native_dataset = dataset_name
                st.session_state.selected_dataset_category = category_key
                st.success(f"✅ Selected {dataset_name}")
                st.rerun()

        with col2:
            if st.button("Preview", key=f"preview_{dataset_name}"):
                self._show_dataset_preview(dataset_name, metadata)

        with col3:
            if st.button("Configure", key=f"config_{dataset_name}"):
                self._show_configuration_options(dataset_name, category_key)

    def get_dataset_metadata(self, dataset_name: str) -> Dict[str, Any]:
        """Get metadata for a specific dataset"""
        # Default metadata - in real implementation, this would fetch from API
        default_metadata = {
            "total_entries": 1000,
            "file_size": "10MB",
            "pyrit_format": "QuestionAnsweringDataset",
            "domain": "general",
            "status": "Available",
        }

        # Enhanced metadata for specific datasets
        enhanced_metadata = {
            "ollegen1_cognitive": {
                "total_entries": 679996,
                "file_size": "150MB",
                "pyrit_format": "QuestionAnsweringDataset",
                "domain": "cognitive_behavioral",
                "status": "Available",
                "categories": ["WCP", "WHO", "TeamRisk", "TargetFactor"],
                "difficulty_levels": ["basic", "medium", "high", "expert"],
            },
            "garak_redteaming": {
                "total_entries": 1250,
                "file_size": "2.5MB",
                "pyrit_format": "SeedPromptDataset",
                "domain": "redteaming",
                "status": "Available",
                "attack_types": ["jailbreak", "prompt_injection", "data_extraction"],
                "severity_levels": ["low", "medium", "high", "critical"],
            },
            "legalbench_professional": {
                "total_entries": 45000,
                "file_size": "25MB",
                "pyrit_format": "QuestionAnsweringDataset",
                "domain": "legal_reasoning",
                "status": "Available",
                "legal_domains": ["contract", "constitutional", "criminal", "tort"],
                "complexity_levels": ["basic", "intermediate", "advanced"],
            },
        }

        return enhanced_metadata.get(dataset_name, default_metadata)

    def _show_dataset_preview(self, dataset_name: str, metadata: Dict[str, Any]) -> None:
        """Show dataset preview in a modal or expander"""
        with st.expander(f"📋 Preview: {dataset_name}", expanded=True):
            st.markdown("### Dataset Preview")

            # Show metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Entries", f"{metadata.get('total_entries', 0):,}")
            with col2:
                st.metric("Format", metadata.get("pyrit_format", "Unknown"))
            with col3:
                st.metric("Domain", metadata.get("domain", "Unknown"))

            # Sample data preview
            st.markdown("### Sample Data")
            if dataset_name == "ollegen1_cognitive":
                sample_data = [
                    {
                        "question": "In a cybersecurity incident, what factors should be prioritized?",
                        "answer": "Risk assessment should prioritize asset criticality and business impact.",
                        "category": "WCP",
                        "difficulty": "medium",
                    },
                    {
                        "question": "How should team communication be structured during a security crisis?",
                        "answer": "Clear communication protocols with defined roles are essential.",
                        "category": "WHO",
                        "difficulty": "high",
                    },
                ]
            else:
                sample_data = [
                    {"prompt": f"Sample prompt from {dataset_name}", "category": "general"},
                    {"prompt": f"Another sample from {dataset_name}", "category": "general"},
                ]

            for i, item in enumerate(sample_data):
                st.markdown(f"**Sample {i+1}:**")
                st.json(item)

    def _show_configuration_options(self, dataset_name: str, category_key: str) -> None:
        """Show configuration options for the dataset"""
        with st.expander(f"⚙️ Configure: {dataset_name}", expanded=True):
            st.markdown("### Dataset Configuration")

            # Category-specific configuration options
            if category_key == "cognitive_behavioral":
                question_types = st.multiselect(
                    "Question Types",
                    ["WCP", "WHO", "TeamRisk", "TargetFactor"],
                    default=["WCP", "WHO"],
                    help="Select which question types to include",
                    key=f"config_qt_{dataset_name}",
                )

                scenario_limit = st.selectbox(
                    "Scenario Limit",
                    [1000, 10000, 50000, "All scenarios"],
                    index=1,
                    help="Number of scenarios to include",
                    key=f"config_sl_{dataset_name}",
                )

                config = {"question_types": question_types, "scenario_limit": scenario_limit}

            elif category_key == "redteaming":
                attack_types = st.multiselect(
                    "Attack Types",
                    ["jailbreak", "prompt_injection", "data_extraction", "bias_amplification"],
                    default=["jailbreak", "prompt_injection"],
                    help="Select attack types to include",
                    key=f"config_at_{dataset_name}",
                )

                severity_filter = st.selectbox(
                    "Minimum Severity",
                    ["low", "medium", "high", "critical"],
                    index=1,
                    help="Filter by minimum severity level",
                    key=f"config_sf_{dataset_name}",
                )

                config = {"attack_types": attack_types, "severity_filter": severity_filter}

            else:
                # Generic configuration
                sample_size = st.slider(
                    "Sample Size",
                    min_value=100,
                    max_value=10000,
                    value=1000,
                    step=100,
                    help="Number of samples to include",
                    key=f"config_ss_{dataset_name}",
                )

                config = {"sample_size": sample_size}

            # Save configuration button
            if st.button("Save Configuration", key=f"save_config_{dataset_name}"):
                # Store configuration in session state
                if "dataset_configurations" not in st.session_state:
                    st.session_state.dataset_configurations = {}

                st.session_state.dataset_configurations[dataset_name] = config
                st.success(f"✅ Configuration saved for {dataset_name}")
                logger.info("Dataset configuration saved: %s -> %s", dataset_name, config)

    def get_selected_dataset(self) -> Optional[str]:
        """Get currently selected dataset"""
        return st.session_state.get("selected_native_dataset")

    def get_selected_category(self) -> Optional[str]:
        """Get currently selected dataset category"""
        return st.session_state.get("selected_dataset_category")

    def get_dataset_configuration(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific dataset"""
        configurations = st.session_state.get("dataset_configurations", {})
        return configurations.get(dataset_name)

    def reset_selection(self) -> None:
        """Reset dataset selection"""
        st.session_state.selected_native_dataset = None
        st.session_state.selected_dataset_category = None
        if "dataset_configurations" in st.session_state:
            del st.session_state.dataset_configurations
