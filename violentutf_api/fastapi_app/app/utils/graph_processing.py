# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Graph Processing utilities for GraphWalk Dataset Converter (Issue #128).

Implements advanced memory management, checkpoint functionality, and graph processing
utilities for handling massive 480MB files with memory constraints.

SECURITY: All processing includes proper validation for defensive security research.
"""
import gc
import json
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

import psutil
from app.schemas.graphwalk_datasets import MemoryUsageInfo, ProcessingCheckpoint


class AdvancedMemoryMonitor:
    """Advanced memory monitoring system for massive file processing."""

    def __init__(self, max_usage_gb: float = 2.0) -> None:
        """Initialize advanced memory monitor.

        Args:
            max_usage_gb: Maximum allowed memory usage in GB
        """
        self.max_usage_gb = max_usage_gb
        self.max_usage_bytes = max_usage_gb * 1024 * 1024 * 1024
        self.warning_threshold = self.max_usage_bytes * 0.8  # 80%
        self.cleanup_threshold = self.max_usage_bytes * 0.9  # 90%

        self.logger = logging.getLogger(__name__)
        self.peak_usage = 0
        self.cleanup_count = 0

    def get_current_usage(self) -> int:
        """Get current memory usage in bytes."""
        current = psutil.Process().memory_info().rss
        if current > self.peak_usage:
            self.peak_usage = current
        return current

    def get_usage_info(self) -> MemoryUsageInfo:
        """Get detailed memory usage information."""
        current_bytes = self.get_current_usage()
        available_bytes = psutil.virtual_memory().available

        return MemoryUsageInfo(
            current_usage_mb=current_bytes / (1024 * 1024),
            peak_usage_mb=self.peak_usage / (1024 * 1024),
            available_mb=available_bytes / (1024 * 1024),
            usage_percentage=(current_bytes / self.max_usage_bytes) * 100,
            cleanup_triggered=self.cleanup_count > 0,
        )

    def check_and_cleanup(self) -> bool:
        """Check memory usage and perform cleanup if needed.

        Returns:
            True if cleanup was performed, False otherwise
        """
        current_usage = self.get_current_usage()
        usage_gb = current_usage / (1024 * 1024 * 1024)

        if current_usage > self.cleanup_threshold:
            self.logger.warning("Critical memory usage: %.2fGB - forcing cleanup", usage_gb)
            self._force_cleanup()
            self.cleanup_count += 1

            # Check if cleanup was effective
            new_usage = self.get_current_usage()
            new_usage_gb = new_usage / (1024 * 1024 * 1024)

            if new_usage > self.cleanup_threshold:
                raise MemoryError(f"Unable to reduce memory usage below threshold: {new_usage_gb:.2f}GB")

            self.logger.info("Memory cleanup successful: %.2fGB", new_usage_gb)
            return True

        elif current_usage > self.warning_threshold:
            self.logger.warning("High memory usage: %.2fGB - performing mild cleanup", usage_gb)
            gc.collect()
            return True

        return False

    def _force_cleanup(self) -> None:
        """Force aggressive garbage collection."""
        # Multiple rounds of garbage collection
        for i in range(3):
            collected = gc.collect()
            if collected > 0:
                self.logger.debug("GC round %s: collected %s objects", i + 1, collected)

    @contextmanager
    def context(self) -> Generator[None, None, None]:
        """Memory monitoring context manager."""
        start_memory = self.get_current_usage()
        start_time = time.time()

        try:
            yield
        finally:
            end_memory = self.get_current_usage()
            end_time = time.time()

            memory_delta = end_memory - start_memory
            time_delta = end_time - start_time

            if memory_delta > 100 * 1024 * 1024:  # 100MB increase
                self.logger.debug("Memory increased by %.1fMB over %.2fs", memory_delta / 1024 / 1024, time_delta)

            # Always check memory after context
            self.check_and_cleanup()


class ProcessingCheckpointManager:
    """Checkpoint manager for processing recovery."""

    def __init__(self, checkpoint_file: str = "graphwalk_processing_checkpoint.json") -> None:
        """Initialize checkpoint manager.

        Args:
            checkpoint_file: Path to checkpoint file
        """
        self.checkpoint_file = checkpoint_file
        self.logger = logging.getLogger(__name__)

    def save_checkpoint(self, state: Dict[str, Any]) -> None:
        """Save processing checkpoint.

        Args:
            state: Current processing state to save
        """
        try:
            # Add timestamp and memory info
            checkpoint = ProcessingCheckpoint(
                processed_chunks=state.get("processed_chunks", 0),
                total_questions=state.get("total_questions", 0),
                current_chunk=state.get("current_chunk", "unknown"),
                timestamp=time.time(),
                memory_usage_mb=psutil.Process().memory_info().rss / (1024 * 1024),
            )

            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint.model_dump(), f, indent=2)

            self.logger.debug("Checkpoint saved: %s chunks processed", checkpoint.processed_chunks)

        except Exception as e:
            self.logger.error("Failed to save checkpoint: %s", e)

    def load_checkpoint(self) -> Optional[ProcessingCheckpoint]:
        """Load previous checkpoint if available.

        Returns:
            ProcessingCheckpoint if exists, None otherwise
        """
        if not os.path.exists(self.checkpoint_file):
            return None

        try:
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            checkpoint = ProcessingCheckpoint(**data)
            self.logger.info(
                "Checkpoint loaded: %s chunks, %s questions", checkpoint.processed_chunks, checkpoint.total_questions
            )
            return checkpoint

        except Exception as e:
            self.logger.error("Failed to load checkpoint: %s", e)
            return None

    def clear_checkpoint(self) -> None:
        """Clear checkpoint after successful completion."""
        try:
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
                self.logger.info("Checkpoint cleared successfully")
        except Exception as e:
            self.logger.error("Failed to clear checkpoint: %s", e)


def analyze_spatial_dimensions(nodes: list) -> int:
    """Analyze spatial dimensions from node positions.

    Args:
        nodes: List of graph nodes with position information

    Returns:
        Number of spatial dimensions (0-3)
    """
    if not nodes:
        return 0

    max_dimensions = 0
    for node in nodes:
        pos = node.get("pos", [])
        if isinstance(pos, list) and len(pos) > max_dimensions:
            max_dimensions = len(pos)

    return min(max_dimensions, 3)  # Cap at 3D


def has_spatial_coordinates(nodes: list) -> bool:
    """Check if nodes have spatial coordinate information.

    Args:
        nodes: List of graph nodes

    Returns:
        True if nodes have spatial coordinates
    """
    if not nodes:
        return False

    for node in nodes[:5]:  # Check first 5 nodes
        pos = node.get("pos")
        if pos and isinstance(pos, list) and len(pos) >= 2:
            return True

    return False


def is_directed_graph(edges: list) -> bool:
    """Determine if graph is directed based on edges.

    Args:
        edges: List of graph edges

    Returns:
        True if graph appears to be directed
    """
    if not edges:
        return False

    # Check if we have bidirectional edges for the same node pairs
    edge_pairs = set()
    reverse_pairs = set()

    for edge in edges:
        from_node = edge.get("from")
        to_node = edge.get("to")

        if from_node and to_node:
            edge_pairs.add((from_node, to_node))
            reverse_pairs.add((to_node, from_node))

    # If most edges don't have reverse counterparts, likely directed
    common_pairs = edge_pairs.intersection(reverse_pairs)

    if len(edge_pairs) == 0:
        return False

    # If less than 30% of edges are bidirectional, consider directed
    bidirectional_ratio = (len(common_pairs) * 2) / len(edge_pairs)
    return bidirectional_ratio < 0.3


def has_weighted_edges(edges: list) -> bool:
    """Check if graph has weighted edges.

    Args:
        edges: List of graph edges

    Returns:
        True if edges have weight information
    """
    if not edges:
        return False

    for edge in edges[:5]:  # Check first 5 edges
        if "weight" in edge or "cost" in edge or "distance" in edge:
            return True

    return False


def check_connectivity(nodes: list, edges: list) -> bool:
    """Check basic graph connectivity.

    Args:
        nodes: List of graph nodes
        edges: List of graph edges

    Returns:
        True if graph appears connected
    """
    if not nodes or not edges:
        return False

    if len(nodes) <= 1:
        return True

    # Build adjacency representation
    node_ids = {node.get("id") for node in nodes if node.get("id")}
    connected_nodes = set()

    for edge in edges:
        from_node = edge.get("from")
        to_node = edge.get("to")

        if from_node and to_node:
            connected_nodes.add(from_node)
            connected_nodes.add(to_node)

    # Check if most nodes are connected
    if len(node_ids) == 0:
        return False

    connectivity_ratio = len(connected_nodes) / len(node_ids)
    return connectivity_ratio > 0.8  # 80% of nodes connected


def calculate_graph_complexity(nodes: list, edges: list) -> float:
    """Calculate graph complexity score.

    Args:
        nodes: List of graph nodes
        edges: List of graph edges

    Returns:
        Complexity score (0.0 - 1.0)
    """
    if not nodes:
        return 0.0

    node_count = len(nodes)
    edge_count = len(edges)

    # Base complexity from size
    size_complexity = min(1.0, (node_count + edge_count) / 100.0)

    # Edge density complexity
    max_edges = node_count * (node_count - 1)  # Complete graph
    if max_edges > 0:
        density_complexity = edge_count / max_edges
    else:
        density_complexity = 0.0

    # Weighted complexity
    weight_complexity = 0.1 if has_weighted_edges(edges) else 0.0

    # Spatial complexity
    spatial_complexity = analyze_spatial_dimensions(nodes) * 0.1

    # Combined complexity score
    total_complexity = size_complexity * 0.4 + density_complexity * 0.3 + weight_complexity + spatial_complexity

    return min(1.0, total_complexity)


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes.

    Args:
        file_path: Path to file

    Returns:
        File size in MB
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except (OSError, IOError):
        return 0.0


# Export all utilities for convenient importing
__all__ = [
    # Memory management
    "AdvancedMemoryMonitor",
    "ProcessingCheckpointManager",
    # Graph analysis utilities
    "analyze_spatial_dimensions",
    "has_spatial_coordinates",
    "is_directed_graph",
    "has_weighted_edges",
    "check_connectivity",
    "calculate_graph_complexity",
    # File utilities
    "get_file_size_mb",
]
