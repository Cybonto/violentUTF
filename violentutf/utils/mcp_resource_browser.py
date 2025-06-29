"""
MCP Resource Browser for Phase 4 Implementation
==============================================

This module provides a sidebar resource browser for MCP resources
with search, filtering, and preview capabilities.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from .mcp_client import MCPClientSync

logger = logging.getLogger(__name__)


class ResourceBrowser:
    """Sidebar resource browser for MCP resources"""

    def __init__(self, mcp_client: MCPClientSync):
        self.mcp_client = mcp_client
        self._resource_cache = {}
        self._last_refresh = None
        self._categories = {
            "datasets": {"icon": "📁", "description": "Security testing datasets"},
            "prompts": {"icon": "📝", "description": "Prompt templates"},
            "results": {"icon": "📊", "description": "Test results"},
            "config": {"icon": "⚙️", "description": "Configuration"},
            "status": {"icon": "🔍", "description": "System status"},
        }

    def render_browser(self):
        """Render the resource browser in sidebar"""
        st.sidebar.markdown("---")
        st.sidebar.header("🗂️ Resource Browser")

        # Search bar
        search_query = st.sidebar.text_input("Search resources", placeholder="Type to search...", key="resource_search")

        # Category filter
        selected_categories = st.sidebar.multiselect(
            "Filter by category",
            options=list(self._categories.keys()),
            default=list(self._categories.keys()),
            format_func=lambda x: f"{self._categories[x]['icon']} {x.title()}",
        )

        # Refresh button
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            if self._last_refresh:
                st.caption(f"Updated: {self._last_refresh.strftime('%H:%M:%S')}")
        with col2:
            if st.button("🔄", help="Refresh resources"):
                self._refresh_resources()

        # Display resources
        self._display_resources(search_query, selected_categories)

    def _refresh_resources(self):
        """Refresh resource list from MCP server"""
        try:
            with st.spinner("Refreshing resources..."):
                resources = self.mcp_client.list_resources()

                # Categorize resources
                self._resource_cache = {
                    "datasets": [],
                    "prompts": [],
                    "results": [],
                    "config": [],
                    "status": [],
                    "other": [],
                }

                for resource in resources:
                    category = self._categorize_resource(resource)
                    self._resource_cache[category].append(resource)

                self._last_refresh = datetime.now()
                st.success("Resources refreshed!")

        except Exception as e:
            logger.error(f"Failed to refresh resources: {e}")
            st.error("Failed to refresh resources")

    def _categorize_resource(self, resource) -> str:
        """Categorize a resource based on URI"""
        uri = resource.uri.lower()

        if "dataset" in uri:
            return "datasets"
        elif "prompt" in uri:
            return "prompts"
        elif "result" in uri:
            return "results"
        elif "config" in uri:
            return "config"
        elif "status" in uri:
            return "status"
        else:
            return "other"

    def _display_resources(self, search_query: str, categories: List[str]):
        """Display filtered resources"""
        # Initialize if needed
        if not self._resource_cache and not self._last_refresh:
            self._refresh_resources()

        # Filter resources
        filtered_resources = []
        for category in categories:
            if category in self._resource_cache:
                for resource in self._resource_cache[category]:
                    if self._matches_search(resource, search_query):
                        filtered_resources.append((category, resource))

        # Display count
        st.sidebar.caption(f"Found {len(filtered_resources)} resources")

        # Group by category
        displayed_categories = set()
        for category, resource in filtered_resources:
            if category not in displayed_categories:
                displayed_categories.add(category)
                st.sidebar.subheader(f"{self._categories.get(category, {}).get('icon', '📄')} {category.title()}")

            self._display_resource_item(resource, category)

    def _matches_search(self, resource, query: str) -> bool:
        """Check if resource matches search query"""
        if not query:
            return True

        query_lower = query.lower()

        # Check name and URI
        if hasattr(resource, "name") and query_lower in resource.name.lower():
            return True
        if hasattr(resource, "uri") and query_lower in resource.uri.lower():
            return True
        if hasattr(resource, "description") and query_lower in resource.description.lower():
            return True

        return False

    def _display_resource_item(self, resource, category: str):
        """Display a single resource item"""
        with st.sidebar.expander(f"📄 {resource.name}", expanded=False):
            # Resource details
            st.caption(f"**URI:** `{resource.uri}`")

            if hasattr(resource, "description"):
                st.write(resource.description)

            # Action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👁️ Preview", key=f"preview_{resource.uri}"):
                    st.session_state["preview_resource"] = resource.uri

            with col2:
                if category == "datasets":
                    if st.button("📥 Load", key=f"load_{resource.uri}"):
                        st.session_state["load_dataset"] = resource.uri
                elif category == "prompts":
                    if st.button("✨ Use", key=f"use_{resource.uri}"):
                        st.session_state["use_prompt"] = resource.uri


class ResourcePreview:
    """Preview panel for MCP resources"""

    def __init__(self, mcp_client: MCPClientSync):
        self.mcp_client = mcp_client

    def render_preview(self, resource_uri: str):
        """Render resource preview"""
        try:
            # Fetch resource content
            content = self.mcp_client.read_resource(resource_uri)

            # Display based on content type
            if isinstance(content, dict):
                self._preview_dict(content, resource_uri)
            elif isinstance(content, list):
                self._preview_list(content, resource_uri)
            elif isinstance(content, str):
                self._preview_text(content, resource_uri)
            else:
                st.info(f"Resource type: {type(content).__name__}")
                st.write(content)

        except Exception as e:
            logger.error(f"Failed to preview resource {resource_uri}: {e}")
            st.error("Failed to load resource preview")

    def _preview_dict(self, content: Dict[str, Any], uri: str):
        """Preview dictionary content"""
        st.subheader(f"📋 Resource: {uri.split('/')[-1]}")

        # Check for specific content types
        if "metadata" in content:
            with st.expander("Metadata", expanded=True):
                st.json(content["metadata"])

        if "content" in content:
            with st.expander("Content", expanded=True):
                if isinstance(content["content"], list):
                    st.write(f"Items: {len(content['content'])}")
                    # Show first few items
                    for i, item in enumerate(content["content"][:3]):
                        st.write(f"**Item {i+1}:**")
                        st.json(item)
                    if len(content["content"]) > 3:
                        st.caption(f"...and {len(content['content']) - 3} more items")
                else:
                    st.json(content["content"])

        # Show raw JSON
        with st.expander("Raw Data", expanded=False):
            st.json(content)

    def _preview_list(self, content: List[Any], uri: str):
        """Preview list content"""
        st.subheader(f"📋 Resource: {uri.split('/')[-1]}")
        st.write(f"**Total items:** {len(content)}")

        # Display first few items
        for i, item in enumerate(content[:5]):
            with st.expander(f"Item {i+1}", expanded=i == 0):
                if isinstance(item, dict):
                    st.json(item)
                else:
                    st.write(item)

        if len(content) > 5:
            st.caption(f"...and {len(content) - 5} more items")

    def _preview_text(self, content: str, uri: str):
        """Preview text content"""
        st.subheader(f"📋 Resource: {uri.split('/')[-1]}")

        # Check if it's JSON string
        try:
            json_content = json.loads(content)
            st.json(json_content)
        except Exception:
            # Display as text
            st.text_area("Content", value=content, height=300)


class ResourceActions:
    """Handle resource actions like loading datasets"""

    def __init__(self, mcp_client: MCPClientSync):
        self.mcp_client = mcp_client

    def load_dataset(self, dataset_uri: str) -> Tuple[bool, str]:
        """Load a dataset into session"""
        try:
            # Read dataset content
            dataset = self.mcp_client.read_resource(dataset_uri)

            if dataset:
                # Store in session state
                dataset_name = dataset_uri.split("/")[-1]
                st.session_state["loaded_dataset"] = dataset
                st.session_state["loaded_dataset_name"] = dataset_name
                st.session_state["loaded_dataset_uri"] = dataset_uri

                # Track in context
                if "context_manager" in st.session_state:
                    session_id = st.session_state.get("session_id", "default")
                    context = st.session_state["context_manager"].monitor.get_or_create_context(session_id)
                    context.add_resource(dataset_uri)

                return True, f"Dataset '{dataset_name}' loaded successfully"
            else:
                return False, "Failed to load dataset"

        except Exception as e:
            logger.error(f"Failed to load dataset {dataset_uri}: {e}")
            return False, f"Error loading dataset: {str(e)}"

    def use_prompt(self, prompt_uri: str) -> Tuple[bool, str]:
        """Use a prompt template"""
        try:
            # Extract prompt name from URI
            prompt_name = prompt_uri.split("/")[-1]

            # Get prompt with minimal args
            prompt_content = self.mcp_client.get_prompt(prompt_name, {})

            if prompt_content:
                # Store for use
                st.session_state["selected_prompt"] = prompt_content
                st.session_state["selected_prompt_name"] = prompt_name

                return True, f"Prompt '{prompt_name}' ready to use"
            else:
                return False, "Failed to load prompt"

        except Exception as e:
            logger.error(f"Failed to use prompt {prompt_uri}: {e}")
            return False, f"Error loading prompt: {str(e)}"


class IntegratedResourceBrowser:
    """Integrates all resource browser components"""

    def __init__(self, mcp_client: MCPClientSync):
        self.browser = ResourceBrowser(mcp_client)
        self.preview = ResourcePreview(mcp_client)
        self.actions = ResourceActions(mcp_client)

    def render_sidebar(self):
        """Render complete resource browser in sidebar"""
        self.browser.render_browser()

    def handle_actions(self):
        """Handle any pending resource actions"""
        # Handle preview
        if st.session_state.get("preview_resource"):
            resource_uri = st.session_state["preview_resource"]
            with st.container():
                self.preview.render_preview(resource_uri)
            st.session_state["preview_resource"] = None

        # Handle dataset loading
        if st.session_state.get("load_dataset"):
            dataset_uri = st.session_state["load_dataset"]
            success, message = self.actions.load_dataset(dataset_uri)
            if success:
                st.success(message)
            else:
                st.error(message)
            st.session_state["load_dataset"] = None

        # Handle prompt usage
        if st.session_state.get("use_prompt"):
            prompt_uri = st.session_state["use_prompt"]
            success, message = self.actions.use_prompt(prompt_uri)
            if success:
                st.success(message)
            else:
                st.error(message)
            st.session_state["use_prompt"] = None
