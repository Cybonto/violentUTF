# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Dataset UI Components and Utilities for ViolentUTF

This module provides utility components for dataset management, performance optimization,
and enhanced user experience in the ViolentUTF Streamlit interface.
"""

import logging
import time
from typing import Any, Dict, List, Optional

import psutil
import streamlit as st

logger = logging.getLogger(__name__)


class LargeDatasetUIOptimization:
    """Performance optimization utilities for large dataset handling in UI"""

    def __init__(self) -> None:
        """Initialize the UI optimization component"""
        self.cache_size_limit = 100_000  # entries
        self.pagination_size = 50
        self.memory_threshold = 500  # MB

        # Initialize session state for optimization
        if "ui_optimization_cache" not in st.session_state:
            st.session_state.ui_optimization_cache = {}
        if "performance_metrics" not in st.session_state:
            st.session_state.performance_metrics = {}

    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def load_dataset_sample(self, dataset_name: str, sample_size: int = 1000) -> List[Dict[str, Any]]:
        """Load representative sample of large dataset for UI operations"""
        logger.info("Loading dataset sample: %s (size: %s)", dataset_name, sample_size)

        # Efficient sampling strategy for large datasets
        if dataset_name == "ollegen1_cognitive":
            return self.sample_large_qa_dataset(dataset_name, sample_size)
        elif dataset_name == "graphwalk_spatial":
            return self.sample_graph_dataset(dataset_name, sample_size)
        else:
            return self.sample_generic_dataset(dataset_name, sample_size)

    def sample_large_qa_dataset(self, dataset_name: str, sample_size: int) -> List[Dict[str, Any]]:
        """Sample from large Q&A dataset efficiently"""
        # Simulate stratified sampling for large cognitive dataset
        categories = ["WCP", "WHO", "TeamRisk", "TargetFactor"]
        difficulties = ["basic", "medium", "high", "expert"]

        samples: List[Dict[str, Any]] = []
        samples_per_category = sample_size // len(categories)

        for category in categories:
            for i in range(samples_per_category):
                samples.append(
                    {
                        "id": len(samples) + 1,
                        "question": f"Sample {category} question {i+1} for cognitive behavioral assessment",
                        "answer": f"Sample answer {i+1} demonstrating {category} reasoning patterns",
                        "category": category,
                        "difficulty": difficulties[i % len(difficulties)],
                        "metadata": {
                            "source": "cognitive_behavioral",
                            "sampled": True,
                            "complexity_score": (i % 10) + 1,
                        },
                    }
                )

        return samples[:sample_size]

    def sample_graph_dataset(self, dataset_name: str, sample_size: int) -> List[Dict[str, Any]]:
        """Sample from graph/spatial dataset efficiently"""
        samples = []

        for i in range(sample_size):
            samples.append(
                {
                    "id": i + 1,
                    "graph_structure": f"Graph {i+1} with {(i % 20) + 5} nodes",
                    "spatial_task": f"Navigation task {i+1}",
                    "complexity": ["simple", "moderate", "complex"][i % 3],
                    "metadata": {"source": "spatial_reasoning", "sampled": True, "node_count": (i % 20) + 5},
                }
            )

        return samples

    def sample_generic_dataset(self, dataset_name: str, sample_size: int) -> List[Dict[str, Any]]:
        """Sample generically from unknown dataset types"""
        return [
            {
                "id": i + 1,
                "content": f"Sample entry {i+1} from {dataset_name}",
                "type": "generic_sample",
                "metadata": {"source": dataset_name, "sampled": True},
            }
            for i in range(sample_size)
        ]

    def render_paginated_preview(self, data: List[Dict[str, Any]], page_size: int = 50) -> List[Dict[str, Any]]:
        """Render paginated preview for large datasets"""
        if not data:
            return []

        total_pages = (len(data) + page_size - 1) // page_size

        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                if st.button("⬅️ Previous", disabled=st.session_state.get("current_page", 1) <= 1):
                    st.session_state.current_page = max(1, st.session_state.get("current_page", 1) - 1)
                    st.rerun()

            with col2:
                page = st.number_input(
                    "Page",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.get("current_page", 1),
                    help=f"Navigate through {total_pages} pages of data",
                    key="pagination_page",
                )
                st.session_state.current_page = page

            with col3:
                if st.button("Next ➡️", disabled=st.session_state.get("current_page", 1) >= total_pages):
                    st.session_state.current_page = min(total_pages, st.session_state.get("current_page", 1) + 1)
                    st.rerun()

            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_data = data[start_idx:end_idx]

            # Show pagination info
            st.caption(f"Showing items {start_idx + 1}-{min(end_idx, len(data))} of {len(data)}")
        else:
            page_data = data

        return page_data

    def optimize_ui_responsiveness(self) -> None:
        """Implement UI responsiveness optimizations"""
        # Check memory usage
        current_memory = self.get_memory_usage()

        if current_memory > self.memory_threshold:
            st.warning(f"⚠️ High memory usage ({current_memory:.1f}MB). Optimizing performance...")
            self.cleanup_cache()

        # Progress indicators for slow operations
        if st.session_state.get("show_loading_indicator", False):
            with st.spinner("Optimizing UI performance..."):
                time.sleep(0.1)  # Minimal delay for UI update
                st.session_state.show_loading_indicator = False

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except Exception:
            return 0.0

    def cleanup_cache(self) -> None:
        """Clean up UI optimization cache"""
        if "ui_optimization_cache" in st.session_state:
            cache_size = len(st.session_state.ui_optimization_cache)
            st.session_state.ui_optimization_cache.clear()
            logger.info("Cleaned up UI cache: %s items removed", cache_size)

    def monitor_performance(self, operation_name: str, execution_time: float) -> None:
        """Monitor and log performance metrics"""
        if "performance_metrics" not in st.session_state:
            st.session_state.performance_metrics = {}

        if operation_name not in st.session_state.performance_metrics:
            st.session_state.performance_metrics[operation_name] = []

        st.session_state.performance_metrics[operation_name].append(execution_time)

        # Keep only last 10 measurements
        if len(st.session_state.performance_metrics[operation_name]) > 10:
            st.session_state.performance_metrics[operation_name] = st.session_state.performance_metrics[operation_name][
                -10:
            ]


class DatasetManagementInterface:
    """Enhanced interface for dataset management and organization"""

    def __init__(self) -> None:
        """Initialize dataset management interface"""
        # Initialize session state for management
        if "favorite_datasets" not in st.session_state:
            st.session_state.favorite_datasets = []
        if "recent_datasets" not in st.session_state:
            st.session_state.recent_datasets = []
        if "dataset_search_history" not in st.session_state:
            st.session_state.dataset_search_history = []

    def render_dataset_management(self) -> None:
        """Render enhanced dataset management interface"""
        st.title("📚 Dataset Management")
        st.markdown("Manage, organize, and discover datasets for your evaluations")

        # Management tabs
        tab1, tab2, tab3, tab4 = st.tabs(["📊 All Datasets", "⭐ Favorites", "🕒 Recent", "🔍 Search"])

        with tab1:
            self.render_all_datasets_view()

        with tab2:
            self.render_favorites_view()

        with tab3:
            self.render_recent_datasets_view()

        with tab4:
            self.render_dataset_search_interface()

    def render_all_datasets_view(self) -> None:
        """Render view of all available datasets"""
        st.subheader("📊 All Available Datasets")

        # Get all datasets (mock data for now)
        all_datasets = self.get_all_datasets()

        # Filter and sort options
        col1, col2, col3 = st.columns(3)

        with col1:
            domain_filter = st.selectbox(
                "Filter by Domain",
                ["All", "Cognitive", "Security", "Legal", "Mathematical", "Spatial", "Privacy", "Meta"],
                key="all_domain_filter",
            )

        with col2:
            size_filter = st.selectbox(
                "Filter by Size",
                ["All", "Small (<1K)", "Medium (1K-10K)", "Large (10K-100K)", "Very Large (>100K)"],
                key="all_size_filter",
            )

        with col3:
            sort_by = st.selectbox("Sort by", ["Name", "Size", "Domain", "Last Updated"], key="all_sort_by")

        # Apply filters
        filtered_datasets = self.apply_filters(all_datasets, domain_filter, size_filter)
        sorted_datasets = self.sort_datasets(filtered_datasets, sort_by)

        # Display datasets
        for dataset in sorted_datasets:
            self.render_dataset_summary_card(dataset)

    def render_favorites_view(self) -> None:
        """Render favorites view"""
        st.subheader("⭐ Favorite Datasets")

        favorites = st.session_state.favorite_datasets

        if not favorites:
            st.info("No favorite datasets yet. Add datasets to favorites from the All Datasets view.")
            return

        st.write(f"You have {len(favorites)} favorite datasets:")

        for dataset_name in favorites:
            dataset_info = self.get_dataset_info(dataset_name)
            if dataset_info:
                self.render_dataset_summary_card(dataset_info, show_favorite=False)

    def render_recent_datasets_view(self) -> None:
        """Render recent datasets view"""
        st.subheader("🕒 Recently Used Datasets")

        recent = st.session_state.recent_datasets

        if not recent:
            st.info("No recently used datasets. Start using datasets to see them here.")
            return

        st.write(f"Your {len(recent)} most recently used datasets:")

        for dataset_name in recent:
            dataset_info = self.get_dataset_info(dataset_name)
            if dataset_info:
                self.render_dataset_summary_card(dataset_info)

    def render_dataset_search_interface(self) -> None:
        """Render advanced dataset search and filtering"""
        st.subheader("🔍 Dataset Search & Discovery")

        # Search controls
        col1, col2 = st.columns([2, 1])

        with col1:
            search_query = st.text_input(
                "Search datasets",
                placeholder="Enter keywords, domain, or dataset name",
                help="Search across dataset names, descriptions, and metadata",
                key="dataset_search_query",
            )

        with col2:
            search_scope = st.selectbox(
                "Search in",
                ["All fields", "Names only", "Descriptions", "Metadata"],
                help="Scope of search operation",
                key="dataset_search_scope",
            )

        # Advanced filters
        with st.expander("🔧 Advanced Filters", expanded=False):
            self.render_advanced_filters()

        # Search results
        if search_query:
            results = self.search_datasets(search_query, search_scope)
            self.render_search_results(results)

            # Add to search history
            if search_query not in st.session_state.dataset_search_history:
                st.session_state.dataset_search_history.append(search_query)
                # Keep only last 10 searches
                if len(st.session_state.dataset_search_history) > 10:
                    st.session_state.dataset_search_history = st.session_state.dataset_search_history[-10:]

        # Show search history
        if st.session_state.dataset_search_history:
            st.markdown("### Recent Searches")
            for i, query in enumerate(reversed(st.session_state.dataset_search_history[-5:])):
                if st.button(f"🔍 {query}", key=f"search_history_{i}"):
                    st.session_state.dataset_search_query = query
                    st.rerun()

    def render_advanced_filters(self) -> None:
        """Render advanced filtering options"""
        col1, col2 = st.columns(2)

        with col1:
            st.slider(
                "Entry Count Range",
                min_value=0,
                max_value=1000000,
                value=(0, 1000000),
                step=1000,
                help="Filter by number of entries",
                key="advanced_entry_range",
            )

            st.multiselect(
                "Dataset Formats",
                ["QuestionAnsweringDataset", "SeedPromptDataset", "ConversationDataset"],
                help="Filter by PyRIT format types",
                key="advanced_formats",
            )

        with col2:
            st.selectbox(
                "Last Updated",
                ["Any time", "Last week", "Last month", "Last 3 months", "Last year"],
                help="Filter by last update time",
                key="advanced_updated",
            )

            st.multiselect(
                "Validation Status",
                ["Validated", "Under Review", "Draft"],
                help="Filter by validation status",
                key="advanced_validation",
            )

    def render_dataset_summary_card(self, dataset: Dict[str, Any], show_favorite: bool = True) -> None:
        """Render a summary card for a dataset"""
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            with col1:
                st.markdown(f"**{dataset['name']}**")
                st.caption(dataset.get("description", "No description available"))

                # Tags
                tags = dataset.get("tags", [])
                if tags:
                    tag_str = " ".join([f"`{tag}`" for tag in tags[:3]])
                    st.markdown(tag_str)

            with col2:
                st.metric("Entries", f"{dataset.get('entries', 0):,}")
                st.caption(f"Domain: {dataset.get('domain', 'Unknown')}")

            with col3:
                st.metric("Size", dataset.get("size", "Unknown"))
                st.caption(f"Format: {dataset.get('format', 'Unknown')}")

            with col4:
                # Action buttons
                if st.button("📊 Select", key=f"select_{dataset['name']}"):
                    self.add_to_recent(dataset["name"])
                    st.success(f"Selected {dataset['name']}")

                if show_favorite:
                    if dataset["name"] in st.session_state.favorite_datasets:
                        if st.button("⭐ Remove", key=f"unfav_{dataset['name']}"):
                            self.remove_from_favorites(dataset["name"])
                            st.rerun()
                    else:
                        if st.button("☆ Add", key=f"fav_{dataset['name']}"):
                            self.add_to_favorites(dataset["name"])
                            st.rerun()

            st.divider()

    def get_all_datasets(self) -> List[Dict[str, Any]]:
        """Get all available datasets (mock data)"""
        return [
            {
                "name": "ollegen1_cognitive",
                "description": "Large-scale cognitive behavioral assessment dataset",
                "entries": 679996,
                "size": "150MB",
                "domain": "Cognitive",
                "format": "QuestionAnsweringDataset",
                "tags": ["cognitive", "behavioral", "large-scale"],
            },
            {
                "name": "garak_redteaming",
                "description": "AI red-teaming prompts for adversarial testing",
                "entries": 1250,
                "size": "2.5MB",
                "domain": "Security",
                "format": "SeedPromptDataset",
                "tags": ["security", "red-teaming", "adversarial"],
            },
            {
                "name": "legalbench_professional",
                "description": "Professional legal reasoning dataset",
                "entries": 45000,
                "size": "25MB",
                "domain": "Legal",
                "format": "QuestionAnsweringDataset",
                "tags": ["legal", "reasoning", "professional"],
            },
        ]

    def get_dataset_info(self, dataset_name: str) -> Optional[Dict[str, Any]]:
        """Get information for a specific dataset"""
        all_datasets = self.get_all_datasets()
        return next((ds for ds in all_datasets if ds["name"] == dataset_name), None)

    def apply_filters(
        self, datasets: List[Dict[str, Any]], domain_filter: str, size_filter: str
    ) -> List[Dict[str, Any]]:
        """Apply filters to dataset list"""
        filtered = datasets

        # Domain filter
        if domain_filter != "All":
            filtered = [ds for ds in filtered if ds.get("domain") == domain_filter]

        # Size filter
        if size_filter != "All":
            size_ranges = {
                "Small (<1K)": (0, 1000),
                "Medium (1K-10K)": (1000, 10000),
                "Large (10K-100K)": (10000, 100000),
                "Very Large (>100K)": (100000, float("inf")),
            }

            if size_filter in size_ranges:
                min_size, max_size = size_ranges[size_filter]
                filtered = [ds for ds in filtered if min_size <= ds.get("entries", 0) < max_size]

        return filtered

    def sort_datasets(self, datasets: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort datasets by specified criteria"""
        if sort_by == "Name":
            return sorted(datasets, key=lambda x: x.get("name", ""))
        elif sort_by == "Size":
            return sorted(datasets, key=lambda x: x.get("entries", 0), reverse=True)
        elif sort_by == "Domain":
            return sorted(datasets, key=lambda x: x.get("domain", ""))
        else:  # Last Updated
            return datasets  # For now, return as-is

    def search_datasets(self, query: str, scope: str) -> List[Dict[str, Any]]:
        """Search datasets based on query and scope"""
        all_datasets = self.get_all_datasets()
        results = []
        query_lower = query.lower()

        for dataset in all_datasets:
            match = False

            if scope == "All fields" or scope == "Names only":
                if query_lower in dataset.get("name", "").lower():
                    match = True

            if scope == "All fields" or scope == "Descriptions":
                if query_lower in dataset.get("description", "").lower():
                    match = True

            if scope == "All fields" or scope == "Metadata":
                tags = dataset.get("tags", [])
                if any(query_lower in tag.lower() for tag in tags):
                    match = True

            if match:
                results.append(dataset)

        return results

    def render_search_results(self, results: List[Dict[str, Any]]) -> None:
        """Render search results"""
        if not results:
            st.info("No datasets found matching your search criteria.")
            return

        st.markdown(f"### Search Results ({len(results)} found)")

        for dataset in results:
            self.render_dataset_summary_card(dataset)

    def add_to_favorites(self, dataset_name: str) -> None:
        """Add dataset to favorites"""
        if dataset_name not in st.session_state.favorite_datasets:
            st.session_state.favorite_datasets.append(dataset_name)
            logger.info("Added %s to favorites", dataset_name)

    def remove_from_favorites(self, dataset_name: str) -> None:
        """Remove dataset from favorites"""
        if dataset_name in st.session_state.favorite_datasets:
            st.session_state.favorite_datasets.remove(dataset_name)
            logger.info("Removed %s from favorites", dataset_name)

    def add_to_recent(self, dataset_name: str) -> None:
        """Add dataset to recent list"""
        if dataset_name in st.session_state.recent_datasets:
            st.session_state.recent_datasets.remove(dataset_name)

        st.session_state.recent_datasets.insert(0, dataset_name)

        # Keep only last 10 recent datasets
        if len(st.session_state.recent_datasets) > 10:
            st.session_state.recent_datasets = st.session_state.recent_datasets[:10]

        logger.info("Added %s to recent datasets", dataset_name)

    def render_batch_operations(self) -> None:
        """Render batch operations interface"""
        st.subheader("🔄 Batch Operations")

        # Multi-select for batch operations
        all_datasets = self.get_all_datasets()
        dataset_names = [ds["name"] for ds in all_datasets]

        selected_datasets = st.multiselect(
            "Select datasets for batch operations",
            dataset_names,
            help="Select multiple datasets for batch operations",
            key="batch_datasets",
        )

        if selected_datasets:
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("⭐ Add All to Favorites"):
                    for dataset in selected_datasets:
                        self.add_to_favorites(dataset)
                    st.success(f"Added {len(selected_datasets)} datasets to favorites")

            with col2:
                if st.button("📊 Batch Preview"):
                    st.info(f"Previewing {len(selected_datasets)} datasets...")
                    # Implement batch preview logic

            with col3:
                if st.button("📋 Export List"):
                    dataset_list = "\n".join(selected_datasets)
                    st.download_button(
                        "Download Dataset List", dataset_list, file_name="selected_datasets.txt", mime="text/plain"
                    )
