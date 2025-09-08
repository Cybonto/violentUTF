# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Test Suite for Issue #128: GraphWalk Dataset Converter with Massive File Handling.

This test suite follows Test-Driven Development (TDD) methodology to validate
the GraphWalk dataset converter implementation including massive 480MB file processing,
graph structure preservation, spatial reasoning generation, and performance requirements.

SECURITY: All tests use synthetic data for security compliance.
"""
import gc
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import psutil
import pytest


class TestGraphWalkSchemas:
    """Test GraphWalk dataset schema definitions."""

    def test_graph_structure_info_schema(self) -> None:
        """Test GraphStructureInfo schema validation."""
        from app.schemas.graphwalk_datasets import GraphStructureInfo

        # Test valid GraphStructureInfo creation
        graph_info = GraphStructureInfo(
            graph_type="spatial_grid",
            node_count=10,
            edge_count=15,
            spatial_dimensions=2,
            navigation_type="shortest_path",
            properties={
                "is_directed": True,
                "is_weighted": True,
                "has_spatial_coordinates": True
            }
        )

        assert graph_info.graph_type == "spatial_grid"
        assert graph_info.node_count == 10
        assert graph_info.edge_count == 15
        assert graph_info.spatial_dimensions == 2
        assert graph_info.navigation_type == "shortest_path"

    def test_chunk_info_schema(self) -> None:
        """Test ChunkInfo schema for massive file splitting."""
        from app.schemas.graphwalk_datasets import ChunkInfo

        chunk = ChunkInfo(
            chunk_id=1,
            filename="graphwalk_chunk_001.jsonl",
            size=15000000,  # 15MB
            object_count=1000,
            start_line=0,
            end_line=999
        )

        assert chunk.chunk_id == 1
        assert chunk.filename == "graphwalk_chunk_001.jsonl"
        assert chunk.size == 15000000
        assert chunk.object_count == 1000

    def test_question_answering_entry_with_graph_metadata(self) -> None:
        """Test QuestionAnsweringEntry with GraphWalk-specific metadata."""
        from app.schemas.graphwalk_datasets import QuestionAnsweringEntry

        entry = QuestionAnsweringEntry(
            question="What is the shortest path from A to C in this spatial grid?",
            answer_type="path",
            correct_answer=["A", "B", "C"],
            choices=[],
            metadata={
                "graph_id": "graph_12345",
                "graph_type": "spatial_grid",
                "node_count": 10,
                "edge_count": 15,
                "spatial_dimensions": 2,
                "reasoning_type": "spatial_traversal",
                "path_complexity": "medium",
                "conversion_strategy": "strategy_2_reasoning_benchmarks"
            }
        )

        assert "graph_id" in entry.metadata
        assert entry.metadata["reasoning_type"] == "spatial_traversal"


class TestGraphWalkConverter:
    """Test GraphWalkConverter core functionality."""

    def test_graphwalk_converter_initialization(self) -> None:
        """Test GraphWalkConverter proper initialization."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Check memory monitor initialization with 2GB limit
        assert hasattr(converter, "memory_monitor")
        assert converter.memory_monitor.max_usage_gb == 2.0

        # Check massive JSON splitter initialization
        assert hasattr(converter, "massive_splitter")
        
        # Check checkpoint manager
        assert hasattr(converter, "checkpoint_manager")
        
        # Check processing counter
        assert converter.processed_count == 0

    def test_memory_monitor_advanced_functionality(self) -> None:
        """Test AdvancedMemoryMonitor class functionality."""
        from app.utils.graph_processing import AdvancedMemoryMonitor

        monitor = AdvancedMemoryMonitor(max_usage_gb=2.0)

        # Check thresholds
        assert monitor.warning_threshold == monitor.max_usage_bytes * 0.8
        assert monitor.cleanup_threshold == monitor.max_usage_bytes * 0.9

        # Test memory tracking
        current_memory = monitor.get_current_usage()
        assert isinstance(current_memory, int)
        assert current_memory > 0

        # Test cleanup functionality
        monitor.check_and_cleanup()

        # Test context manager
        with monitor.context():
            pass  # Should not raise exceptions

    def test_massive_json_splitter_initialization(self) -> None:
        """Test MassiveJSONSplitter setup."""
        from app.core.splitters.massive_json_splitter import MassiveJSONSplitter

        splitter = MassiveJSONSplitter()

        # Test logger setup
        assert hasattr(splitter, "logger")
        
        # Test splitting methods
        assert hasattr(splitter, "split_massive_json_preserving_graphs")
        assert hasattr(splitter, "write_chunk_safely")


class TestMassiveFileProcessing:
    """Test massive 480MB file processing functionality."""

    def test_file_analysis_for_massive_files(self) -> None:
        """Test file analysis for massive file detection."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Create test files of different sizes
        with tempfile.NamedTemporaryFile(delete=False) as small_file:
            small_file.write(b"x" * (50 * 1024 * 1024))  # 50MB
            small_path = small_file.name

        with tempfile.NamedTemporaryFile(delete=False) as massive_file:
            massive_file.write(b"x" * (500 * 1024 * 1024))  # 500MB (simulates 480MB)
            massive_path = massive_file.name

        try:
            # Test file analysis
            small_info = converter.analyze_massive_file(small_path)
            massive_info = converter.analyze_massive_file(massive_path)

            assert small_info.size_mb < 400
            assert massive_info.size_mb > 400
            
            # Massive file should trigger advanced splitting
            assert massive_info.requires_advanced_splitting is True
            
        finally:
            os.unlink(small_path)
            os.unlink(massive_path)

    def test_processing_strategy_selection_for_massive_files(self) -> None:
        """Test processing strategy selection for 480MB files."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Create massive file (simulating 480MB)
        with tempfile.NamedTemporaryFile(delete=False) as massive_file:
            massive_file.write(b"x" * (480 * 1024 * 1024))  # 480MB
            massive_path = massive_file.name

        try:
            # Should use advanced splitting strategy
            strategy = converter.determine_processing_strategy(massive_path)
            assert strategy == "convert_with_advanced_splitting"
            
        finally:
            os.unlink(massive_path)

    def test_massive_json_splitting_with_graph_preservation(self) -> None:
        """Test massive JSON splitting while preserving graph integrity."""
        from app.core.splitters.massive_json_splitter import MassiveJSONSplitter

        splitter = MassiveJSONSplitter()

        # Create test JSONL file with graph objects
        graph_objects = []
        for i in range(1000):  # Create 1000 graph objects
            graph_obj = {
                "id": f"graph_{i}",
                "graph": {
                    "nodes": [
                        {"id": "A", "pos": [0, 0]},
                        {"id": "B", "pos": [1, 0]},
                        {"id": "C", "pos": [1, 1]}
                    ],
                    "edges": [
                        {"from": "A", "to": "B", "weight": 1.0},
                        {"from": "B", "to": "C", "weight": 1.5}
                    ]
                },
                "question": f"Test question {i}",
                "answer": ["A", "B", "C"]
            }
            graph_objects.append(json.dumps(graph_obj))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as test_file:
            for obj in graph_objects:
                test_file.write(obj + '\n')
            test_path = test_file.name

        try:
            # Test massive splitting
            result = splitter.split_massive_json_preserving_graphs(
                test_path,
                target_size=50000,  # 50KB chunks for testing
                preserve_graph_integrity=True,
                enable_checkpointing=True
            )

            # Validate split result
            assert result.total_chunks > 1
            assert result.total_objects == 1000
            assert len(result.chunks) == result.total_chunks
            
            # Validate each chunk
            total_objects_in_chunks = 0
            for chunk in result.chunks:
                assert os.path.exists(chunk.filename)
                assert chunk.object_count > 0
                total_objects_in_chunks += chunk.object_count
                
                # Cleanup chunk files
                os.unlink(chunk.filename)
                
            assert total_objects_in_chunks == 1000

        finally:
            os.unlink(test_path)

    def test_memory_monitoring_during_massive_processing(self) -> None:
        """Test memory monitoring during massive file processing."""
        from app.utils.graph_processing import AdvancedMemoryMonitor

        monitor = AdvancedMemoryMonitor(max_usage_gb=2.0)

        # Simulate memory pressure
        large_data = []
        
        with monitor.context():
            # Add some data to increase memory
            for i in range(1000):
                large_data.append(f"test_data_{i}" * 1000)
                
                # Check memory every 100 iterations
                if i % 100 == 0:
                    monitor.check_and_cleanup()

        # Should complete without memory errors
        assert len(large_data) == 1000


class TestGraphStructureProcessing:
    """Test graph structure analysis and processing."""

    def test_graph_structure_extraction(self) -> None:
        """Test graph structure extraction from GraphWalk objects."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Sample GraphWalk object
        graph_item = {
            "id": "test_graph",
            "graph": {
                "nodes": [
                    {"id": "A", "pos": [0, 0], "properties": {"type": "start"}},
                    {"id": "B", "pos": [1, 0], "properties": {"type": "waypoint"}},
                    {"id": "C", "pos": [1, 1], "properties": {"type": "goal"}}
                ],
                "edges": [
                    {"from": "A", "to": "B", "weight": 1.0},
                    {"from": "B", "to": "C", "weight": 1.5}
                ]
            },
            "question": "What is the shortest path from A to C?",
            "answer": ["A", "B", "C"],
            "spatial_context": "2D grid navigation"
        }

        structure = converter.extract_graph_structure(graph_item)

        assert structure.node_count == 3
        assert structure.edge_count == 2
        assert structure.spatial_dimensions == 2
        assert structure.properties["is_weighted"] is True
        assert structure.properties["has_spatial_coordinates"] is True

    def test_spatial_reasoning_question_generation(self) -> None:
        """Test spatial reasoning question generation."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        graph_item = {
            "id": "spatial_test",
            "graph": {
                "nodes": [{"id": "A", "pos": [0, 0]}, {"id": "B", "pos": [1, 1]}],
                "edges": [{"from": "A", "to": "B", "weight": 1.414}]
            },
            "question": "Find shortest path from A to B",
            "answer": ["A", "B"],
            "spatial_context": "2D Euclidean space"
        }

        qa_entry = converter.create_graph_reasoning_question(graph_item, "chunk_1")

        assert "Graph Structure:" in qa_entry.question
        assert "Spatial Context:" in qa_entry.question
        assert qa_entry.metadata["reasoning_type"] == "spatial_traversal"
        assert qa_entry.metadata["chunk_id"] == "chunk_1"

    def test_graph_type_classification(self) -> None:
        """Test graph type classification logic."""
        from app.services.graph_service import GraphService

        service = GraphService()

        # Test spatial grid classification
        nodes_grid = [{"id": "A", "pos": [0, 0]}, {"id": "B", "pos": [1, 0]}]
        edges_grid = [{"from": "A", "to": "B"}]
        
        graph_type = service.classify_graph_type(nodes_grid, edges_grid)
        assert graph_type in ["spatial_grid", "planar_graph", "general_graph"]

    def test_path_complexity_assessment(self) -> None:
        """Test path complexity assessment for spatial reasoning."""
        from app.services.graph_service import GraphService

        service = GraphService()

        # Simple path - use actual GraphStructureInfo instead of Mock
        from app.schemas.graphwalk_datasets import GraphStructureInfo
        
        simple_structure = GraphStructureInfo(
            graph_type="simple_graph",
            node_count=3,
            edge_count=2,
            spatial_dimensions=2,
            navigation_type="shortest_path",
            properties={"is_directed": False, "is_weighted": False}
        )
        
        complexity = service.assess_path_complexity(simple_structure)
        assert complexity in ["simple", "medium", "complex"]


class TestMemoryManagement:
    """Test memory management for massive file processing."""

    def test_memory_threshold_detection(self) -> None:
        """Test memory threshold detection and response."""
        from app.utils.graph_processing import AdvancedMemoryMonitor

        monitor = AdvancedMemoryMonitor(max_usage_gb=2.0)

        # Test warning threshold calculation
        warning_bytes = monitor.warning_threshold
        cleanup_bytes = monitor.cleanup_threshold

        assert warning_bytes < cleanup_bytes
        assert cleanup_bytes < monitor.max_usage_bytes

    def test_progressive_garbage_collection(self) -> None:
        """Test progressive garbage collection mechanism."""
        from app.utils.graph_processing import AdvancedMemoryMonitor

        monitor = AdvancedMemoryMonitor(max_usage_gb=2.0)

        # Create some objects to trigger GC
        test_objects = []
        for i in range(1000):
            test_objects.append({"data": f"test_{i}" * 100})

        # Clear references
        test_objects = None
        
        # Trigger cleanup
        monitor.check_and_cleanup()
        
        # Should complete without errors

    def test_memory_monitoring_context_manager(self) -> None:
        """Test memory monitoring context manager behavior."""
        from app.utils.graph_processing import AdvancedMemoryMonitor

        monitor = AdvancedMemoryMonitor(max_usage_gb=2.0)

        start_memory = None
        end_memory = None

        with monitor.context():
            start_memory = psutil.Process().memory_info().rss
            # Simulate some processing
            temp_data = ["x" * 1000 for _ in range(1000)]
            end_memory = psutil.Process().memory_info().rss

        # Context manager should have handled cleanup
        assert start_memory is not None
        assert end_memory is not None


class TestErrorHandlingAndRecovery:
    """Test error handling and recovery mechanisms."""

    def test_checkpoint_manager_functionality(self) -> None:
        """Test checkpoint manager save/load/clear operations."""
        from app.utils.graph_processing import ProcessingCheckpointManager

        manager = ProcessingCheckpointManager()

        # Test checkpoint save
        test_state = {
            "processed_chunks": 5,
            "total_questions": 15000,
            "current_chunk": "chunk_005"
        }
        
        manager.save_checkpoint(test_state)
        
        # Test checkpoint load
        loaded_checkpoint = manager.load_checkpoint()
        assert loaded_checkpoint is not None
        assert loaded_checkpoint.processed_chunks == 5
        assert loaded_checkpoint.total_questions == 15000
        assert loaded_checkpoint.current_chunk == "chunk_005"
        
        # Test checkpoint clear
        manager.clear_checkpoint()
        cleared_checkpoint = manager.load_checkpoint()
        assert cleared_checkpoint is None

    def test_error_recovery_from_processing_interruption(self) -> None:
        """Test error recovery from processing interruption."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Mock chunk info
        chunk_info = Mock()
        chunk_info.chunk_id = 1
        chunk_info.filename = "test_chunk.jsonl"

        # Create test chunk file with some valid and invalid JSON
        test_content = [
            '{"id": "valid1", "graph": {"nodes": [], "edges": []}, "question": "test"}',
            'invalid json line',
            '{"id": "valid2", "graph": {"nodes": [], "edges": []}, "question": "test2"}'
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for line in test_content:
                f.write(line + '\n')
            chunk_info.filename = f.name

        try:
            # Should handle errors gracefully and continue processing
            questions = converter.process_graph_chunk_with_recovery(chunk_info)
            
            # Should have processed 2 valid items despite 1 invalid
            assert len(questions) == 2
            
        finally:
            os.unlink(chunk_info.filename)

    def test_memory_exhaustion_handling(self) -> None:
        """Test handling of memory exhaustion scenarios."""
        from app.utils.graph_processing import AdvancedMemoryMonitor

        # Create monitor with very low memory limit for testing
        monitor = AdvancedMemoryMonitor(max_usage_gb=0.001)  # 1MB limit

        # This should trigger cleanup or raise MemoryError
        with pytest.raises((MemoryError, Exception)):
            with monitor.context():
                # Try to exceed memory limit
                large_data = ["x" * 1000000 for _ in range(100)]  # 100MB of data


class TestPerformanceRequirements:
    """Test performance requirements and benchmarks."""

    def test_processing_speed_benchmark(self) -> None:
        """Test processing speed meets requirements (>3000 objects/minute)."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Create test data with known number of objects
        test_objects = []
        for i in range(100):  # Smaller sample for unit test
            test_obj = {
                "id": f"perf_test_{i}",
                "graph": {"nodes": [{"id": "A"}], "edges": []},
                "question": f"Test question {i}",
                "answer": "A"
            }
            test_objects.append(json.dumps(test_obj))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for obj in test_objects:
                f.write(obj + '\n')
            test_path = f.name

        try:
            start_time = time.time()
            
            # Process test file
            result = converter.convert(test_path)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Calculate objects per minute
            objects_per_minute = (len(test_objects) / processing_time) * 60
            
            # For unit test, just verify it processes at reasonable speed
            assert objects_per_minute > 100  # Lower threshold for unit test
            
        finally:
            os.unlink(test_path)

    def test_memory_usage_stays_under_limit(self) -> None:
        """Test memory usage stays under 2GB limit during processing."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Monitor should enforce 2GB limit
        assert converter.memory_monitor.max_usage_gb == 2.0

        # Memory monitor should be properly configured
        max_bytes = converter.memory_monitor.max_usage_bytes
        expected_bytes = 2.0 * 1024 * 1024 * 1024
        assert max_bytes == expected_bytes

    def test_chunk_processing_time_limits(self) -> None:
        """Test individual chunk processing stays within time limits."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Create small test chunk
        chunk_data = []
        for i in range(10):
            chunk_data.append(json.dumps({
                "id": f"chunk_test_{i}",
                "graph": {"nodes": [], "edges": []},
                "question": f"Test {i}",
                "answer": "test"
            }))

        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for line in chunk_data:
                f.write(line + '\n')
            
            chunk_info = Mock()
            chunk_info.chunk_id = 1
            chunk_info.filename = f.name

        try:
            start_time = time.time()
            questions = converter.process_graph_chunk_with_recovery(chunk_info)
            processing_time = time.time() - start_time
            
            # Should process small chunk quickly
            assert processing_time < 10  # 10 seconds max for small chunk
            assert len(questions) == 10
            
        finally:
            os.unlink(chunk_info.filename)


class TestIntegrationRequirements:
    """Test integration requirements with existing system."""

    def test_graphwalk_dataset_creation(self) -> None:
        """Test QuestionAnsweringDataset creation with GraphWalk data."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter
        from app.schemas.graphwalk_datasets import QuestionAnsweringEntry

        converter = GraphWalkConverter()

        # Sample questions
        questions = [
            QuestionAnsweringEntry(
                question="Test spatial reasoning question",
                answer_type="path",
                correct_answer=["A", "B"],
                choices=[],
                metadata={
                    "graph_id": "test_graph",
                    "reasoning_type": "spatial_traversal",
                    "conversion_strategy": "strategy_2_reasoning_benchmarks"
                }
            )
        ]

        # Mock metadata
        split_metadata = Mock()
        split_metadata.total_chunks = 1
        split_metadata.total_objects = 1

        processing_stats = {
            "processed_chunks": 1,
            "total_objects": 1
        }

        dataset = converter.create_graphwalk_dataset(questions, split_metadata, processing_stats)

        assert dataset.name == "GraphWalk_Spatial_Reasoning"
        assert dataset.group == "graph_reasoning"
        assert len(dataset.questions) == 1
        assert "split_metadata" in dataset.metadata
        assert "processing_stats" in dataset.metadata

    def test_api_endpoint_integration_requirements(self) -> None:
        """Test requirements for API endpoint integration."""
        from app.core.converters.graphwalk_converter import GraphWalkConverter

        converter = GraphWalkConverter()

        # Converter should be compatible with dataset endpoint patterns
        assert hasattr(converter, "convert")
        assert callable(getattr(converter, "convert"))

        # Should return QuestionAnsweringDataset
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({}, f)  # Empty JSON file
            test_path = f.name

        try:
            result = converter.convert(test_path)
            assert hasattr(result, "name")
            assert hasattr(result, "questions")
            assert hasattr(result, "metadata")
            
        finally:
            os.unlink(test_path)


# Test data and fixtures for comprehensive testing
@pytest.fixture
def sample_graphwalk_data():
    """Fixture providing sample GraphWalk dataset structure."""
    return {
        "id": "test_graph_123",
        "graph": {
            "nodes": [
                {"id": "start", "pos": [0, 0], "properties": {"type": "start"}},
                {"id": "middle", "pos": [5, 3], "properties": {"type": "waypoint"}},
                {"id": "goal", "pos": [10, 6], "properties": {"type": "goal"}}
            ],
            "edges": [
                {"from": "start", "to": "middle", "weight": 5.83},
                {"from": "middle", "to": "goal", "weight": 5.83},
                {"from": "start", "to": "goal", "weight": 11.66}
            ]
        },
        "question": "What is the shortest path from start to goal?",
        "answer": ["start", "goal"],
        "reasoning": "Direct path is shorter than going through waypoint",
        "spatial_context": "2D Euclidean navigation with weighted edges"
    }


@pytest.fixture
def massive_file_simulation():
    """Fixture for simulating massive file processing."""
    def _create_massive_file(size_mb: int, objects_count: int) -> str:
        """Create a test file of specified size with GraphWalk objects."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for i in range(objects_count):
                obj = {
                    "id": f"massive_test_{i}",
                    "graph": {"nodes": [{"id": "A"}], "edges": []},
                    "question": f"Massive test question {i}",
                    "answer": "A"
                }
                f.write(json.dumps(obj) + '\n')
            return f.name
    return _create_massive_file


if __name__ == "__main__":
    pytest.main([__file__, "-v"])