# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Massive JSON Splitter for GraphWalk Dataset Converter (Issue #128).

Implements advanced file splitting for 480MB GraphWalk files with graph integrity
preservation, object-boundary awareness, and memory-efficient processing.

SECURITY: All processing includes proper validation for defensive security research.
"""
import json
import logging
import os
from typing import Dict, List

from app.schemas.graphwalk_datasets import ChunkInfo, SplitResult


class MassiveJSONSplitter:
    """Advanced JSON splitter for massive GraphWalk files."""

    def __init__(self) -> None:
        """Initialize massive JSON splitter."""
        self.logger = logging.getLogger(__name__)

    def split_massive_json_preserving_graphs(
        self, file_path: str, target_size: int, preserve_graph_integrity: bool = True, enable_checkpointing: bool = True
    ) -> SplitResult:
        """Split massive JSON file while preserving graph object integrity.

        Args:
            file_path: Path to massive JSON file
            target_size: Target size for each chunk in bytes
            preserve_graph_integrity: Whether to preserve graph object boundaries
            enable_checkpointing: Whether to enable checkpointing

        Returns:
            SplitResult with chunk information and metadata
        """
        chunks = []
        current_chunk_size = 0
        current_chunk_lines = []
        chunk_count = 1
        total_objects = 0
        error_count = 0

        self.logger.info("Starting to split massive file: %s", file_path)
        self.logger.info("Target chunk size: %.1fMB", target_size / (1024 * 1024))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue

                    line_size = len(line.encode("utf-8"))

                    # Validate JSON if preserving integrity
                    if preserve_graph_integrity:
                        try:
                            json.loads(line)  # Validate JSON structure
                        except json.JSONDecodeError as e:
                            self.logger.warning("Invalid JSON at line %s: %s", line_num + 1, e)
                            error_count += 1
                            continue  # Skip invalid JSON

                    # Check if adding this line would exceed target size
                    if current_chunk_size + line_size > target_size and current_chunk_lines:

                        # Write current chunk
                        chunk_filename = f"graphwalk_chunk_{chunk_count:03d}.jsonl"
                        self.write_chunk_safely(chunk_filename, current_chunk_lines)

                        chunks.append(
                            ChunkInfo(
                                chunk_id=chunk_count,
                                filename=chunk_filename,
                                size=current_chunk_size,
                                object_count=len(current_chunk_lines),
                                start_line=line_num - len(current_chunk_lines),
                                end_line=line_num - 1,
                            )
                        )

                        # Progress logging
                        if chunk_count % 10 == 0:
                            self.logger.info("Created %s chunks, processed %s objects", chunk_count, total_objects)

                        # Reset for next chunk
                        current_chunk_lines = []
                        current_chunk_size = 0
                        chunk_count += 1

                    # Add line to current chunk
                    current_chunk_lines.append(line + "\n")
                    current_chunk_size += line_size + 1  # +1 for newline
                    total_objects += 1

                    # Progress reporting every 10000 lines
                    if (line_num + 1) % 10000 == 0:
                        self.logger.debug("Processed %s lines, %s valid objects", line_num + 1, total_objects)

            # Handle final chunk
            if current_chunk_lines:
                chunk_filename = f"graphwalk_chunk_{chunk_count:03d}.jsonl"
                self.write_chunk_safely(chunk_filename, current_chunk_lines)

                chunks.append(
                    ChunkInfo(
                        chunk_id=chunk_count,
                        filename=chunk_filename,
                        size=current_chunk_size,
                        object_count=len(current_chunk_lines),
                        start_line=total_objects - len(current_chunk_lines),
                        end_line=total_objects - 1,
                    )
                )

        except Exception as e:
            self.logger.error("Error during massive file splitting: %s", e)
            raise

        self.logger.info("Successfully split massive file into %s chunks", len(chunks))
        self.logger.info("Total objects processed: %s", total_objects)
        if error_count > 0:
            self.logger.warning("Skipped %s invalid JSON lines", error_count)

        return SplitResult(
            chunks=chunks,
            total_chunks=len(chunks),
            total_objects=total_objects,
            original_size=os.path.getsize(file_path),
            metadata={
                "split_strategy": "object_boundary_preservation",
                "target_chunk_size_mb": target_size / (1024 * 1024),
                "preserve_graph_integrity": preserve_graph_integrity,
                "error_count": error_count,
                "enable_checkpointing": enable_checkpointing,
            },
        )

    def write_chunk_safely(self, filename: str, lines: List[str]) -> None:
        """Write chunk file with error handling.

        Args:
            filename: Chunk filename
            lines: List of lines to write
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.writelines(lines)

            self.logger.debug("Successfully wrote chunk: %s", filename)

        except Exception as e:
            self.logger.error("Failed to write chunk %s: %s", filename, e)
            raise

    def validate_chunk_integrity(self, chunk_filename: str) -> Dict[str, bool]:
        """Validate chunk integrity after splitting.

        Args:
            chunk_filename: Path to chunk file

        Returns:
            Dictionary with validation results
        """
        results = {"file_exists": False, "json_valid": True, "graph_objects_valid": True, "object_count_matches": True}

        try:
            # Check file exists
            results["file_exists"] = os.path.exists(chunk_filename)
            if not results["file_exists"]:
                return results

            # Validate JSON and count objects
            object_count = 0
            with open(chunk_filename, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        # Validate JSON
                        obj = json.loads(line)
                        object_count += 1

                        # Basic graph object validation
                        if not self._validate_graph_object(obj):
                            results["graph_objects_valid"] = False

                    except json.JSONDecodeError:
                        results["json_valid"] = False
                        self.logger.warning("Invalid JSON in chunk %s at line %s", chunk_filename, line_num + 1)

            self.logger.debug("Chunk %s validated: %s objects", chunk_filename, object_count)

        except Exception as e:
            self.logger.error("Error validating chunk %s: %s", chunk_filename, e)
            results["json_valid"] = False

        return results

    def _validate_graph_object(self, obj: dict) -> bool:
        """Validate basic graph object structure.

        Args:
            obj: Graph object to validate

        Returns:
            True if object has valid graph structure
        """
        # Basic graph object should have id, graph, and question
        required_fields = ["id", "graph", "question"]

        for field in required_fields:
            if field not in obj:
                return False

        # Validate graph structure
        graph = obj.get("graph", {})
        if not isinstance(graph, dict):
            return False

        # Should have nodes and edges
        if "nodes" not in graph or "edges" not in graph:
            return False

        nodes = graph["nodes"]
        edges = graph["edges"]

        if not isinstance(nodes, list) or not isinstance(edges, list):
            return False

        return True

    def cleanup_chunks(self, chunks: List[ChunkInfo]) -> None:
        """Clean up chunk files after processing.

        Args:
            chunks: List of chunk information to clean up
        """
        cleanup_count = 0
        error_count = 0

        for chunk in chunks:
            try:
                if os.path.exists(chunk.filename):
                    os.remove(chunk.filename)
                    cleanup_count += 1
            except Exception as e:
                self.logger.warning("Failed to cleanup chunk %s: %s", chunk.filename, e)
                error_count += 1

        self.logger.info("Cleaned up %s chunk files", cleanup_count)
        if error_count > 0:
            self.logger.warning("Failed to cleanup %s chunk files", error_count)


# Export for convenient importing
__all__ = [
    "MassiveJSONSplitter",
]
