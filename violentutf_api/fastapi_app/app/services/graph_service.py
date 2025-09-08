# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Graph Service for GraphWalk Dataset Processing (Issue #128).

Implements graph structure analysis, spatial reasoning processing, and graph
classification for GraphWalk dataset conversion with massive file handling.

SECURITY: All processing includes proper validation for defensive security research.
"""
import logging
from typing import Any, Dict, List

from app.schemas.graphwalk_datasets import GraphStructureInfo, GraphType
from app.utils.graph_processing import (
    analyze_spatial_dimensions,
    calculate_graph_complexity,
    check_connectivity,
    has_spatial_coordinates,
    has_weighted_edges,
    is_directed_graph,
)


class GraphService:
    """Service for graph structure analysis and processing."""

    def __init__(self) -> None:
        """Initialize graph service."""
        self.logger = logging.getLogger(__name__)

    def classify_graph_type(self, nodes: List[Dict], edges: List[Dict]) -> str:
        """Classify graph type based on structure.

        Args:
            nodes: List of graph nodes
            edges: List of graph edges

        Returns:
            Graph type classification string
        """
        if not nodes:
            return GraphType.GENERAL_GRAPH.value

        # Check for spatial characteristics
        if has_spatial_coordinates(nodes):
            spatial_dims = analyze_spatial_dimensions(nodes)
            if spatial_dims >= 2:
                return GraphType.SPATIAL_GRID.value
            else:
                return GraphType.PLANAR_GRAPH.value

        # Check for weighted characteristics
        if has_weighted_edges(edges):
            return GraphType.WEIGHTED_GRAPH.value

        # Check directedness
        if is_directed_graph(edges):
            # Check if it's a DAG (simplified check)
            if self._appears_acyclic(nodes, edges):
                return GraphType.DAG_STRUCTURE.value
            else:
                return GraphType.DIRECTED_GRAPH.value

        # Check if it's a tree
        node_count = len(nodes)
        edge_count = len(edges)

        if edge_count == node_count - 1 and check_connectivity(nodes, edges):
            return GraphType.TREE_STRUCTURE.value

        # Default to general graph
        return GraphType.GENERAL_GRAPH.value

    def determine_navigation_type(self, graph_item: Dict[str, Any]) -> str:
        """Determine navigation type from graph context.

        Args:
            graph_item: Complete graph item with question context

        Returns:
            Navigation type string
        """
        question = graph_item.get("question", "").lower()
        answer = graph_item.get("answer", [])

        # Analyze question content for navigation patterns
        if "shortest" in question and "path" in question:
            return "shortest_path"
        elif "longest" in question and "path" in question:
            return "longest_path"
        elif "optimal" in question or "best" in question:
            return "optimal_path"
        elif "all path" in question or "every path" in question:
            return "all_paths"
        elif "dijkstra" in question:
            return "dijkstra"
        elif "a*" in question or "astar" in question:
            return "a_star"
        elif "breadth" in question or "bfs" in question:
            return "bfs_traversal"
        elif "depth" in question or "dfs" in question:
            return "dfs_traversal"

        # Analyze answer structure
        if isinstance(answer, list) and len(answer) > 2:
            return "shortest_path"  # Most common for path answers

        return "shortest_path"  # Default assumption

    def assess_path_complexity(self, graph_structure: GraphStructureInfo) -> str:
        """Assess path complexity for spatial reasoning.

        Args:
            graph_structure: Graph structure information

        Returns:
            Complexity assessment: "simple", "medium", or "complex"
        """
        # Simple complexity factors
        node_count = graph_structure.node_count
        edge_count = graph_structure.edge_count

        # Base complexity from size
        if node_count <= 5 and edge_count <= 8:
            size_complexity = "simple"
        elif node_count <= 15 and edge_count <= 30:
            size_complexity = "medium"
        else:
            size_complexity = "complex"

        # Graph properties complexity
        properties = graph_structure.properties
        complexity_factors = 0

        if properties.get("is_weighted", False):
            complexity_factors += 1

        if properties.get("is_directed", False):
            complexity_factors += 1

        if graph_structure.spatial_dimensions > 2:
            complexity_factors += 1

        # Combine factors
        if complexity_factors == 0:
            property_complexity = "simple"
        elif complexity_factors <= 2:
            property_complexity = "medium"
        else:
            property_complexity = "complex"

        # Final complexity assessment
        complexities = [size_complexity, property_complexity]

        if "complex" in complexities:
            return "complex"
        elif "medium" in complexities:
            return "medium"
        else:
            return "simple"

    def extract_graph_properties(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        """Extract comprehensive graph properties.

        Args:
            nodes: List of graph nodes
            edges: List of graph edges

        Returns:
            Dictionary of graph properties
        """
        return {
            "is_directed": is_directed_graph(edges),
            "is_weighted": has_weighted_edges(edges),
            "is_connected": check_connectivity(nodes, edges),
            "has_spatial_coordinates": has_spatial_coordinates(nodes),
            "complexity_score": calculate_graph_complexity(nodes, edges),
            "node_degree_stats": self._calculate_degree_statistics(nodes, edges),
            "spatial_bounds": self._calculate_spatial_bounds(nodes),
            "edge_weight_stats": self._calculate_edge_weight_statistics(edges),
        }

    def _appears_acyclic(self, nodes: List[Dict], edges: List[Dict]) -> bool:
        """Check if directed graph appears to be acyclic (DAG).

        Args:
            nodes: List of graph nodes
            edges: List of graph edges

        Returns:
            True if graph appears to be a DAG
        """
        # Simplified DAG detection
        # Build adjacency list
        adj = {}
        node_ids = {node.get("id") for node in nodes if node.get("id")}

        for node_id in node_ids:
            adj[node_id] = []

        for edge in edges:
            from_node = edge.get("from")
            to_node = edge.get("to")

            if from_node and to_node and from_node in adj:
                adj[from_node].append(to_node)

        # Simple cycle detection using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            if node in rec_stack:
                return True  # Back edge found - cycle detected

            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in adj.get(node, []):
                if has_cycle(neighbor):
                    return True

            rec_stack.remove(node)
            return False

        # Check for cycles starting from each node
        for node_id in node_ids:
            if node_id not in visited:
                if has_cycle(node_id):
                    return False  # Cycle found - not acyclic

        return True  # No cycles found - appears to be DAG

    def _calculate_degree_statistics(self, nodes: List[Dict], edges: List[Dict]) -> Dict[str, float]:
        """Calculate node degree statistics.

        Args:
            nodes: List of graph nodes
            edges: List of graph edges

        Returns:
            Dictionary with degree statistics
        """
        node_degrees = {}
        node_ids = {node.get("id") for node in nodes if node.get("id")}

        # Initialize degree counts
        for node_id in node_ids:
            node_degrees[node_id] = 0

        # Count degrees
        for edge in edges:
            from_node = edge.get("from")
            to_node = edge.get("to")

            if from_node in node_degrees:
                node_degrees[from_node] += 1
            if to_node in node_degrees:
                node_degrees[to_node] += 1

        degrees = list(node_degrees.values())

        if not degrees:
            return {"min": 0, "max": 0, "avg": 0, "median": 0}

        degrees.sort()
        n = len(degrees)

        return {"min": min(degrees), "max": max(degrees), "avg": sum(degrees) / n, "median": degrees[n // 2]}

    def _calculate_spatial_bounds(self, nodes: List[Dict]) -> Dict[str, Any]:
        """Calculate spatial bounding box for nodes.

        Args:
            nodes: List of graph nodes with position data

        Returns:
            Dictionary with spatial bounds
        """
        positions = []

        for node in nodes:
            pos = node.get("pos", [])
            if isinstance(pos, list) and len(pos) >= 2:
                positions.append(pos[:2])  # Take x,y coordinates

        if not positions:
            return {"min_x": 0, "max_x": 0, "min_y": 0, "max_y": 0, "width": 0, "height": 0}

        x_coords = [pos[0] for pos in positions]
        y_coords = [pos[1] for pos in positions]

        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)

        return {
            "min_x": min_x,
            "max_x": max_x,
            "min_y": min_y,
            "max_y": max_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
        }

    def _calculate_edge_weight_statistics(self, edges: List[Dict]) -> Dict[str, float]:
        """Calculate edge weight statistics.

        Args:
            edges: List of graph edges

        Returns:
            Dictionary with weight statistics
        """
        weights = []

        for edge in edges:
            weight = edge.get("weight")
            if weight is not None:
                try:
                    weights.append(float(weight))
                except (ValueError, TypeError):
                    continue

        if not weights:
            return {"min": 0, "max": 0, "avg": 0, "total": 0, "count": 0}

        return {
            "min": min(weights),
            "max": max(weights),
            "avg": sum(weights) / len(weights),
            "total": sum(weights),
            "count": len(weights),
        }


# Export for convenient importing
__all__ = [
    "GraphService",
]
