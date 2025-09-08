# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""GraphWalk Dataset Converter Implementation (Issue #128).

Implements comprehensive GraphWalk dataset converter with massive 480MB file handling,
graph structure preservation, spatial reasoning generation, and advanced memory management.

SECURITY: All processing includes proper validation for defensive security research.
"""
import json
import logging
import os
import time
from typing import Any, Dict, List

from app.core.splitters.massive_json_splitter import MassiveJSONSplitter
from app.schemas.graphwalk_datasets import (
    ChunkInfo,
    FileAnalysisInfo,
    GraphAnswerInfo,
    GraphStructureInfo,
    GraphWalkConversionConfig,
    ProcessingStats,
    QuestionAnsweringDataset,
    QuestionAnsweringEntry,
)
from app.services.graph_service import GraphService
from app.utils.graph_processing import (
    AdvancedMemoryMonitor,
    ProcessingCheckpointManager,
    analyze_spatial_dimensions,
    get_file_size_mb,
)


class GraphWalkConverter:
    """GraphWalk dataset converter with massive 480MB file handling support.

    Implements advanced converter to transform GraphWalk spatial reasoning
    datasets into PyRIT QuestionAnsweringDataset format with specialized handling
    for very large files (480MB+) using streaming and advanced file splitting.
    """

    def __init__(self, config: GraphWalkConversionConfig = None) -> None:
        """Initialize GraphWalk converter.

        Args:
            config: Optional conversion configuration
        """
        self.config = config or GraphWalkConversionConfig()

        # Initialize core components
        self.memory_monitor = AdvancedMemoryMonitor(max_usage_gb=self.config.max_memory_usage_gb)
        self.massive_splitter = MassiveJSONSplitter()
        self.checkpoint_manager = ProcessingCheckpointManager()

        # Initialize processing services
        self.graph_service = GraphService()

        # Processing counters
        self.processed_count = 0

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def convert(self, file_path: str) -> QuestionAnsweringDataset:
        """Convert GraphWalk dataset with massive file handling.

        Args:
            file_path: Path to GraphWalk dataset file

        Returns:
            QuestionAnsweringDataset with converted spatial reasoning tasks
        """
        start_time = time.time()

        if not os.path.exists(file_path):
            # Return empty dataset for missing path
            return QuestionAnsweringDataset(
                name="GraphWalk_Spatial_Reasoning",
                version="1.0",
                description="Graph traversal and spatial reasoning tasks (empty - path not found)",
                author="GraphWalk Research",
                group="graph_reasoning",
                source="GraphWalk-OpenAI",
                questions=[],
                metadata={
                    "error": f"Dataset path not found: {file_path}",
                    "conversion_strategy": "strategy_2_reasoning_benchmarks",
                },
            )

        # Analyze file to determine processing strategy
        file_info = self.analyze_massive_file(file_path)

        self.logger.info("Processing %.1fMB GraphWalk file: %s", file_info.size_mb, file_path)
        self.logger.info("Processing strategy: %s", file_info.processing_strategy)

        # Route to appropriate processing strategy
        if file_info.size_mb > 400:  # 480MB train.json and similar massive files
            result = self.convert_with_advanced_splitting(file_path)
        else:
            result = self.convert_with_streaming(file_path)

        processing_time = time.time() - start_time
        self.logger.info("GraphWalk conversion completed in %.2f seconds", processing_time)

        # Update metadata with processing info
        result.metadata.update(
            {
                "processing_time_seconds": processing_time,
                "file_size_mb": file_info.size_mb,
                "processing_strategy": file_info.processing_strategy,
                "memory_peak_mb": self.memory_monitor.peak_usage / (1024 * 1024),
            }
        )

        return result

    def analyze_massive_file(self, file_path: str) -> FileAnalysisInfo:
        """Analyze file to determine processing requirements.

        Args:
            file_path: Path to file to analyze

        Returns:
            FileAnalysisInfo with analysis results
        """
        size_mb = get_file_size_mb(file_path)

        # Estimate object count based on file size (rough approximation)
        if size_mb > 400:
            estimated_objects = "100K+"
            structure = "JSONL with massive graph objects"
            requires_splitting = True
            strategy = "convert_with_advanced_splitting"
        elif size_mb > 50:
            estimated_objects = "10K-50K"
            structure = "JSONL with graph objects"
            requires_splitting = False
            strategy = "convert_with_streaming"
        else:
            estimated_objects = "<10K"
            structure = "JSONL with graph objects"
            requires_splitting = False
            strategy = "convert_with_streaming"

        return FileAnalysisInfo(
            size_mb=size_mb,
            estimated_objects=estimated_objects,
            structure=structure,
            requires_advanced_splitting=requires_splitting,
            processing_strategy=strategy,
        )

    def determine_processing_strategy(self, file_path: str) -> str:
        """Determine processing strategy based on file characteristics.

        Args:
            file_path: Path to file

        Returns:
            Processing strategy string
        """
        file_info = self.analyze_massive_file(file_path)
        return file_info.processing_strategy

    def convert_with_advanced_splitting(self, file_path: str) -> QuestionAnsweringDataset:
        """Convert massive file using advanced splitting strategy.

        Args:
            file_path: Path to massive file

        Returns:
            QuestionAnsweringDataset with converted questions
        """
        self.logger.info("Initiating advanced splitting for massive file")

        # Split massive file into manageable chunks
        split_result = self.massive_splitter.split_massive_json_preserving_graphs(
            file_path,
            target_size=self.config.chunk_size_mb * 1024 * 1024,  # Convert MB to bytes
            preserve_graph_integrity=True,
            enable_checkpointing=True,
        )

        all_questions = []
        processing_stats = ProcessingStats(
            total_chunks=len(split_result.chunks),
            processed_chunks=0,
            failed_chunks=0,
            total_objects=0,
            processing_time_seconds=0.0,
            memory_peak_mb=0.0,
            objects_per_minute=0.0,
        )

        start_time = time.time()

        # Process each chunk with comprehensive monitoring
        for chunk_info in split_result.chunks:
            try:
                self.logger.info("Processing chunk %s/%s", chunk_info.chunk_id, len(split_result.chunks))

                with self.memory_monitor.context():
                    chunk_questions = self.process_graph_chunk_with_recovery(chunk_info)
                    all_questions.extend(chunk_questions)

                    processing_stats.processed_chunks += 1
                    processing_stats.total_objects += len(chunk_questions)

                    # Create checkpoint
                    self.checkpoint_manager.save_checkpoint(
                        {
                            "processed_chunks": processing_stats.processed_chunks,
                            "total_questions": len(all_questions),
                            "current_chunk": f"chunk_{chunk_info.chunk_id:03d}",
                        }
                    )

                    # Progress reporting
                    progress = (processing_stats.processed_chunks / processing_stats.total_chunks) * 100
                    self.logger.info("Progress: %.1f%% - %s questions processed", progress, len(all_questions))

            except Exception as e:
                self.logger.error("Failed to process chunk %s: %s", chunk_info.chunk_id, e)
                processing_stats.failed_chunks += 1
                continue

        # Calculate final processing statistics
        processing_stats.processing_time_seconds = time.time() - start_time
        processing_stats.memory_peak_mb = self.memory_monitor.peak_usage / (1024 * 1024)

        if processing_stats.processing_time_seconds > 0:
            processing_stats.objects_per_minute = (
                processing_stats.total_objects / processing_stats.processing_time_seconds * 60
            )

        # Cleanup chunk files
        self.massive_splitter.cleanup_chunks(split_result.chunks)

        # Clear checkpoint after successful completion
        self.checkpoint_manager.clear_checkpoint()

        return self.create_graphwalk_dataset(all_questions, split_result.metadata, processing_stats)

    def convert_with_streaming(self, file_path: str) -> QuestionAnsweringDataset:
        """Convert file using streaming processing for smaller files.

        Args:
            file_path: Path to file

        Returns:
            QuestionAnsweringDataset with converted questions
        """
        self.logger.info("Processing file with streaming strategy")

        questions = []
        error_count = 0
        start_time = time.time()

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        graph_item = json.loads(line)
                        qa_entry = self.create_graph_reasoning_question(graph_item, "streaming")
                        questions.append(qa_entry)
                        self.processed_count += 1

                        # Memory check every 1000 items for streaming
                        if line_num % 1000 == 0:
                            self.memory_monitor.check_and_cleanup()

                    except json.JSONDecodeError as e:
                        error_count += 1
                        self.logger.warning("JSON decode error at line %s: %s", line_num + 1, e)
                        continue

                    except Exception as e:
                        error_count += 1
                        self.logger.warning("Error processing item at line %s: %s", line_num + 1, e)
                        continue

        except Exception as e:
            self.logger.error("Critical error during streaming processing: %s", e)
            raise

        processing_time = time.time() - start_time

        # Create processing stats
        processing_stats = ProcessingStats(
            total_chunks=1,
            processed_chunks=1,
            failed_chunks=0,
            total_objects=len(questions),
            processing_time_seconds=processing_time,
            memory_peak_mb=self.memory_monitor.peak_usage / (1024 * 1024),
            objects_per_minute=(len(questions) / processing_time * 60) if processing_time > 0 else 0,
        )

        metadata = {"processing_strategy": "streaming", "error_count": error_count}

        return self.create_graphwalk_dataset(questions, metadata, processing_stats)

    def process_graph_chunk_with_recovery(self, chunk_info: ChunkInfo) -> List[QuestionAnsweringEntry]:
        """Process graph chunk with error recovery.

        Args:
            chunk_info: Information about chunk to process

        Returns:
            List of processed QuestionAnsweringEntry objects
        """
        questions = []
        error_count = 0
        max_errors = 100  # Allow some errors in massive file processing

        try:
            with open(chunk_info.filename, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        graph_item = json.loads(line)
                        qa_entry = self.create_graph_reasoning_question(graph_item, f"chunk_{chunk_info.chunk_id}")
                        questions.append(qa_entry)
                        self.processed_count += 1

                        # Memory check every 500 items
                        if line_num % 500 == 0:
                            self.memory_monitor.check_and_cleanup()

                    except json.JSONDecodeError as e:
                        error_count += 1
                        if error_count > max_errors:
                            raise RuntimeError(f"Too many JSON errors in chunk {chunk_info.chunk_id}") from e
                        self.logger.warning("JSON decode error at line %s: %s", line_num, e)
                        continue

                    except Exception as e:
                        error_count += 1
                        if error_count > max_errors:
                            raise RuntimeError(f"Too many processing errors in chunk {chunk_info.chunk_id}") from e
                        self.logger.warning("Error processing graph item at line %s: %s", line_num, e)
                        continue

        except Exception as e:
            self.logger.error("Critical error processing chunk %s: %s", chunk_info.filename, e)
            raise

        self.logger.info(
            "Processed %s questions from chunk %s (errors: %s)", len(questions), chunk_info.chunk_id, error_count
        )
        return questions

    def create_graph_reasoning_question(self, graph_item: Dict[str, Any], chunk_id: str) -> QuestionAnsweringEntry:
        """Create graph reasoning QuestionAnsweringEntry from GraphWalk item.

        Args:
            graph_item: GraphWalk graph item
            chunk_id: Chunk identifier for tracking

        Returns:
            QuestionAnsweringEntry with spatial reasoning question
        """
        # Extract and analyze graph structure
        graph_structure = self.extract_graph_structure(graph_item)

        # Build spatial reasoning question with graph context
        question_text = self.build_graph_question_with_context(graph_item, graph_structure)

        # Process graph traversal answer
        answer_info = self.process_graph_traversal_answer(graph_item)

        return QuestionAnsweringEntry(
            question=question_text,
            answer_type=answer_info.answer_type,
            correct_answer=answer_info.correct_answer,
            choices=answer_info.choices,
            metadata={
                "graph_id": graph_item.get("id", f"chunk_{chunk_id}_unknown"),
                "graph_type": graph_structure.graph_type,
                "node_count": graph_structure.node_count,
                "edge_count": graph_structure.edge_count,
                "spatial_dimensions": graph_structure.spatial_dimensions,
                "reasoning_type": "spatial_traversal",
                "chunk_id": chunk_id,
                "graph_properties": graph_structure.properties,
                "path_complexity": self.graph_service.assess_path_complexity(graph_structure),
                "navigation_type": graph_structure.navigation_type,
                "conversion_strategy": "strategy_2_reasoning_benchmarks",
            },
        )

    def extract_graph_structure(self, graph_item: Dict[str, Any]) -> GraphStructureInfo:
        """Extract and analyze graph structure from GraphWalk item.

        Args:
            graph_item: GraphWalk graph item

        Returns:
            GraphStructureInfo with analyzed structure
        """
        graph_data = graph_item.get("graph", {})
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        # Analyze spatial properties and graph type
        spatial_dimensions = analyze_spatial_dimensions(nodes)
        graph_type = self.graph_service.classify_graph_type(nodes, edges)
        navigation_type = self.graph_service.determine_navigation_type(graph_item)

        # Extract comprehensive graph properties
        properties = self.graph_service.extract_graph_properties(nodes, edges)

        return GraphStructureInfo(
            graph_type=graph_type,
            node_count=len(nodes),
            edge_count=len(edges),
            spatial_dimensions=spatial_dimensions,
            navigation_type=navigation_type,
            properties=properties,
        )

    def build_graph_question_with_context(self, graph_item: Dict[str, Any], graph_structure: GraphStructureInfo) -> str:
        """Build comprehensive graph reasoning question with context.

        Args:
            graph_item: GraphWalk graph item
            graph_structure: Analyzed graph structure

        Returns:
            Comprehensive question text with graph context
        """
        context_parts = []

        # Add graph description
        context_parts.append(
            f"Graph Structure: {graph_structure.node_count} nodes, " f"{graph_structure.edge_count} edges"
        )

        # Add spatial context if available
        if graph_structure.spatial_dimensions > 0:
            context_parts.append(f"Spatial Context: {graph_structure.spatial_dimensions}D navigation")

        # Add graph properties
        if graph_structure.properties.get("is_weighted"):
            context_parts.append("Graph Type: Weighted graph with edge costs")

        # Add navigation context
        spatial_context = graph_item.get("spatial_context", "")
        if spatial_context:
            context_parts.append(f"Navigation Context: {spatial_context}")

        # Add the reasoning question
        question = graph_item.get("question", "")
        if question:
            context_parts.append(f"Question: {question}")

        return "\n\n".join(context_parts)

    def process_graph_traversal_answer(self, graph_item: Dict[str, Any]) -> GraphAnswerInfo:
        """Process graph traversal answer information.

        Args:
            graph_item: GraphWalk graph item

        Returns:
            GraphAnswerInfo with processed answer
        """
        answer = graph_item.get("answer", [])
        reasoning = graph_item.get("reasoning", "")

        # Determine answer type based on structure
        if isinstance(answer, list):
            if all(isinstance(x, str) for x in answer):
                answer_type = "path"
            else:
                answer_type = "sequence"
        elif isinstance(answer, (int, float)):
            answer_type = "numeric"
        else:
            answer_type = "text"

        return GraphAnswerInfo(
            answer_type=answer_type,
            correct_answer=answer,
            choices=[],  # GraphWalk typically doesn't provide multiple choices
            reasoning=reasoning,
        )

    def create_graphwalk_dataset(
        self, questions: List[QuestionAnsweringEntry], metadata: Dict[str, Any], processing_stats: ProcessingStats
    ) -> QuestionAnsweringDataset:
        """Create final GraphWalk QuestionAnsweringDataset.

        Args:
            questions: List of processed questions
            metadata: Processing metadata
            processing_stats: Processing statistics

        Returns:
            Complete QuestionAnsweringDataset
        """
        return QuestionAnsweringDataset(
            name="GraphWalk_Spatial_Reasoning",
            version="1.0",
            description=(
                "Graph traversal and spatial reasoning tasks converted from GraphWalk dataset. "
                f"Contains {len(questions)} spatial reasoning questions with graph structure analysis."
            ),
            author="GraphWalk Research / ViolentUTF Converter",
            group="graph_reasoning",
            source="GraphWalk-OpenAI",
            questions=questions,
            metadata={
                "total_questions": len(questions),
                "conversion_strategy": "strategy_2_reasoning_benchmarks",
                "split_metadata": metadata,
                "processing_stats": (
                    processing_stats.model_dump() if hasattr(processing_stats, "model_dump") else processing_stats
                ),
                "converter_version": "1.0.0",
                "graph_types_processed": list(set(q.metadata.get("graph_type", "unknown") for q in questions)),
                "spatial_dimensions_range": self._get_spatial_dimensions_range(questions),
                "complexity_distribution": self._get_complexity_distribution(questions),
            },
        )

    def _get_spatial_dimensions_range(self, questions: List[QuestionAnsweringEntry]) -> Dict[str, int]:
        """Get range of spatial dimensions in processed questions.

        Args:
            questions: List of processed questions

        Returns:
            Dictionary with min/max spatial dimensions
        """
        dimensions = [q.metadata.get("spatial_dimensions", 0) for q in questions if "spatial_dimensions" in q.metadata]

        if not dimensions:
            return {"min": 0, "max": 0}

        return {"min": min(dimensions), "max": max(dimensions)}

    def _get_complexity_distribution(self, questions: List[QuestionAnsweringEntry]) -> Dict[str, int]:
        """Get complexity distribution of processed questions.

        Args:
            questions: List of processed questions

        Returns:
            Dictionary with complexity counts
        """
        complexity_counts = {"simple": 0, "medium": 0, "complex": 0}

        for question in questions:
            complexity = question.metadata.get("path_complexity", "unknown")
            if complexity in complexity_counts:
                complexity_counts[complexity] += 1

        return complexity_counts


# Export for convenient importing
__all__ = [
    "GraphWalkConverter",
]
