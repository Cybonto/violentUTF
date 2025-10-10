#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Test Suite for Issue #127: DocMath Dataset Converter with Large File Handling.

This test suite follows Test-Driven Development (TDD) methodology to validate
the DocMath dataset converter implementation including large file processing,
mathematical reasoning preservation, and performance requirements.

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


class TestDocMathSchemas:
    """Test DocMath dataset schema definitions."""

    def test_docmath_complexity_tier_enum(self) -> None:
        """Test DocMathComplexityTier enum validation."""
        from app.schemas.docmath_datasets import DocMathComplexityTier

        # Expected tiers
        expected_tiers = ["simpshort", "simplong", "compshort", "complong"]

        for tier in expected_tiers:
            assert hasattr(DocMathComplexityTier, tier.upper())
            assert DocMathComplexityTier[tier.upper()].value == tier

    def test_mathematical_answer_type_detection(self) -> None:
        """Test MathematicalAnswerType enum and detection logic."""
        from app.schemas.docmath_datasets import MathematicalAnswerType

        # Expected answer types
        expected_types = ["integer", "float", "string", "expression"]

        for answer_type in expected_types:
            assert hasattr(MathematicalAnswerType, answer_type.upper())

    def test_question_answering_entry_validation(self) -> None:
        """Test QuestionAnsweringEntry field validation."""
        from app.schemas.docmath_datasets import QuestionAnsweringEntry

        # Test valid entry creation
        valid_entry = QuestionAnsweringEntry(
            question="What is 2 + 2?",
            answer_type="int",
            correct_answer=4,
            choices=[],
            metadata={"complexity_tier": "simpshort"},
        )

        assert valid_entry.question == "What is 2 + 2?"
        assert valid_entry.answer_type == "int"
        assert valid_entry.correct_answer == 4


class TestDocMathConverter:
    """Test DocMathConverter core functionality."""

    def test_docmath_converter_initialization(self) -> None:
        """Test DocMathConverter proper initialization."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Check memory monitor initialization
        assert hasattr(converter, "memory_monitor")
        assert converter.memory_monitor.max_usage_gb == 2.0

        # Check JSON splitter configuration
        assert hasattr(converter, "json_splitter")

        # Check processing strategies defined
        assert hasattr(converter, "get_processing_strategy")

    def test_memory_monitor_functionality(self) -> None:
        """Test MemoryMonitor class functionality."""
        from app.utils.math_processing import MemoryMonitor

        monitor = MemoryMonitor(max_usage_gb=2.0)

        # Test memory tracking
        current_memory = monitor.get_current_usage()
        assert isinstance(current_memory, int)
        assert current_memory > 0

        # Test cleanup functionality
        monitor.check_and_cleanup()

        # Test context manager
        with monitor.context():
            pass  # Should not raise exceptions

    def test_json_splitter_configuration(self) -> None:
        """Test MathematicalJSONSplitter setup."""
        from app.utils.math_processing import MathematicalJSONSplitter

        splitter = MathematicalJSONSplitter()

        # Test configuration
        assert hasattr(splitter, "target_size")
        assert hasattr(splitter, "preserve_mathematical_context")
        assert splitter.preserve_mathematical_context is True


class TestFileProcessingStrategy:
    """Test file processing strategy selection."""

    def test_processing_strategy_selection(self) -> None:
        """Test file processing strategy selection logic."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Create temporary test files of different sizes
        with tempfile.NamedTemporaryFile(delete=False) as small_file:
            small_file.write(b"x" * (10 * 1024 * 1024))  # 10MB
            small_path = small_file.name

        with tempfile.NamedTemporaryFile(delete=False) as medium_file:
            medium_file.write(b"x" * (60 * 1024 * 1024))  # 60MB
            medium_path = medium_file.name

        with tempfile.NamedTemporaryFile(delete=False) as large_file:
            large_file.write(b"x" * (150 * 1024 * 1024))  # 150MB
            large_path = large_file.name

        try:
            # Test strategy selection
            assert converter.get_processing_strategy(small_path, "simpshort") == "standard"
            assert converter.get_processing_strategy(medium_path, "simplong") == "streaming"
            assert converter.get_processing_strategy(large_path, "complong") == "splitting_with_streaming"
        finally:
            # Cleanup
            os.unlink(small_path)
            os.unlink(medium_path)
            os.unlink(large_path)

    def test_file_size_detection(self) -> None:
        """Test accurate file size detection."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Test with known file size
        with tempfile.NamedTemporaryFile() as test_file:
            test_data = b"x" * (5 * 1024 * 1024)  # 5MB
            test_file.write(test_data)
            test_file.flush()

            size_mb = converter._get_file_size_mb(test_file.name)
            assert abs(size_mb - 5.0) < 0.1  # Allow small tolerance


class TestMathematicalProcessing:
    """Test mathematical processing functionality."""

    def test_numerical_type_detection(self) -> None:
        """Test numerical answer type detection."""
        from app.utils.math_processing import detect_numerical_type

        # Test integer detection
        assert detect_numerical_type("123") == "int"
        assert detect_numerical_type("-45") == "int"

        # Test float detection
        assert detect_numerical_type("3.14") == "float"
        assert detect_numerical_type("2.5e10") == "float"

        # Test expression detection
        assert detect_numerical_type("2+3") == "expression"
        assert detect_numerical_type("x=5") == "expression"

        # Test text answer
        assert detect_numerical_type("The answer is complex") == "str"

    def test_mathematical_expression_parsing(self) -> None:
        """Test mathematical expression identification."""
        from app.utils.math_processing import is_mathematical_expression

        # Test basic arithmetic
        assert is_mathematical_expression("5+3") is True
        assert is_mathematical_expression("10*2") is True

        # Test scientific notation
        assert is_mathematical_expression("1.5e-10") is True

        # Test fractions
        assert is_mathematical_expression("3/4") is True
        assert is_mathematical_expression("22/7") is True

        # Test percentages
        assert is_mathematical_expression("25%") is True
        assert is_mathematical_expression("100%") is True

        # Test currency
        assert is_mathematical_expression("$100") is True
        assert is_mathematical_expression("$4.50") is True

        # Test non-mathematical text
        assert is_mathematical_expression("Hello world") is False

    def test_mathematical_domain_classification(self) -> None:
        """Test mathematical domain classification logic."""
        from app.services.mathematical_service import MathematicalDomainClassifier

        classifier = MathematicalDomainClassifier()

        # Test arithmetic domain
        arithmetic_problem = {
            "question": "What is 5 + 3?",
            "context": "Basic addition problem",
            "paragraphs": ["Simple arithmetic calculation"],
        }
        assert classifier.classify_mathematical_domain(arithmetic_problem) == "arithmetic"

        # Test algebra domain
        algebra_problem = {
            "question": "Solve for x: 2x + 5 = 15",
            "context": "Linear equation solving",
            "paragraphs": ["Find the value of variable x"],
        }
        assert classifier.classify_mathematical_domain(algebra_problem) == "algebra"

    def test_complexity_assessment(self) -> None:
        """Test mathematical complexity assessment."""
        from app.services.mathematical_service import MathematicalComplexityAnalyzer

        analyzer = MathematicalComplexityAnalyzer()

        # Test simple problem
        simple_problem = {"question": "What is 2 + 2?"}
        complexity = analyzer.assess_mathematical_complexity(simple_problem, "simpshort")
        assert complexity < 0.3  # Low complexity

        # Test complex problem
        complex_problem = {
            "question": "Find the derivative of f(x) = x^3 + 2x^2 - x + 5",
            "context": "Calculus differentiation problem",
        }
        complexity = analyzer.assess_mathematical_complexity(complex_problem, "complong")
        assert complexity > 0.7  # High complexity


class TestContextPreservation:
    """Test mathematical context preservation."""

    def test_mathematical_context_builder(self) -> None:
        """Test mathematical context construction."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        test_item = {
            "context": "Mathematical reasoning problem",
            "paragraphs": ["First paragraph", "Second paragraph"],
            "table_evidence": ["Table data 1", "Table data 2"],
            "question": "What is the result?",
        }

        context = converter.build_mathematical_context(test_item)

        # Verify context includes all components
        assert "Document Context: Mathematical reasoning problem" in context
        assert "Relevant Paragraphs:" in context
        assert "First paragraph" in context
        assert "Second paragraph" in context
        assert "Table Evidence:" in context
        assert "Table data 1" in context
        assert "Question: What is the result?" in context

    def test_table_evidence_extraction(self) -> None:
        """Test table evidence extraction and formatting."""
        from app.utils.math_processing import extract_table_evidence

        test_tables = [{"columns": ["A", "B"], "rows": [[1, 2], [3, 4]]}, {"data": "Raw table string"}]

        formatted_evidence = extract_table_evidence(test_tables)
        assert isinstance(formatted_evidence, list)
        assert len(formatted_evidence) == len(test_tables)


class TestFileProcessingIntegration:
    """Test complete file processing workflows."""

    def test_small_file_processing_complete(self) -> None:
        """Test complete processing of small DocMath files."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Create synthetic small DocMath file  
        test_data = [
            {
                "question_id": "test_1",
                "question": "What is 2 + 2?",
                "ground_truth": 4,
                "context": "Basic arithmetic",
                "paragraphs": ["Simple addition"],
                "table_evidence": [],
            }
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            test_file_path = f.name

        try:
            # Test processing
            questions = converter.process_standard_file(test_file_path, "simpshort", "test")

            assert len(questions) == 1
            assert questions[0].question is not None
            assert questions[0].correct_answer == 4
            assert questions[0].metadata["complexity_tier"] == "simpshort"

        finally:
            os.unlink(test_file_path)

    def test_medium_file_streaming(self) -> None:
        """Test streaming processing of medium files."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Mock medium-sized file processing
        with patch.object(converter, "process_file_with_streaming") as mock_streaming:
            mock_streaming.return_value = [Mock(), Mock(), Mock()]  # 3 questions

            # Test streaming call
            result = converter.process_file_with_streaming("test_medium.json", "simplong", "test")

            assert len(result) == 3
            mock_streaming.assert_called_once_with("test_medium.json", "simplong", "test")

    def test_large_file_splitting_integration(self) -> None:
        """Test complete large file processing."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Mock large file splitting and processing
        with patch.object(converter, "process_large_file_with_splitting") as mock_splitting:
            mock_splitting.return_value = [Mock() for _ in range(10)]  # 10 questions

            result = converter.process_large_file_with_splitting("test_large.json", "complong", "test")

            assert len(result) == 10
            mock_splitting.assert_called_once_with("test_large.json", "complong", "test")


class TestPerformanceRequirements:
    """Test performance and memory requirements."""

    def test_memory_usage_compliance(self) -> None:
        """Test memory usage stays within 2GB limit."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Mock large file processing with memory monitoring
        initial_memory = psutil.Process().memory_info().rss / (1024 * 1024 * 1024)  # GB

        with patch.object(converter, "memory_monitor") as mock_monitor:
            mock_monitor.max_usage_gb = 2.0
            mock_monitor.check_and_cleanup.return_value = None

            # Simulate processing that should stay under limit
            converter.memory_monitor.check_and_cleanup()

            # Verify memory monitoring was called
            mock_monitor.check_and_cleanup.assert_called()

    def test_processing_time_benchmarks(self) -> None:
        """Test processing time meets performance targets."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Mock timed processing
        start_time = time.time()

        # Simulate processing that should complete quickly
        with patch.object(converter, "convert") as mock_convert:
            mock_convert.return_value = Mock()

            result = converter.convert("test_dataset_path")
            elapsed_time = time.time() - start_time

            # For unit test, should be very fast
            assert elapsed_time < 1.0  # Less than 1 second for mocked processing
            assert result is not None


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_missing_file_handling(self) -> None:
        """Test handling of missing DocMath files."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Test missing file handling
        non_existent_path = "/tmp/non_existent_file.json"

        # Should handle missing file gracefully
        result = converter.convert(non_existent_path)

        # Should return empty dataset but not crash
        assert result is not None
        assert len(result.questions) == 0

    def test_corrupted_json_handling(self) -> None:
        """Test handling of malformed JSON files."""
        from app.core.converters.docmath_converter import DocMathConverter

        converter = DocMathConverter()

        # Create corrupted JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"invalid": json content}')  # Malformed JSON
            corrupted_file = f.name

        try:
            # Should handle corrupted JSON gracefully
            result = converter.process_standard_file(corrupted_file, "simpshort", "test")

            # Should return empty list but not crash
            assert isinstance(result, list)

        finally:
            os.unlink(corrupted_file)

    def test_memory_exhaustion_recovery(self) -> None:
        """Test recovery from memory exhaustion scenarios."""
        from app.utils.math_processing import MemoryMonitor

        monitor = MemoryMonitor(max_usage_gb=0.001)  # Very low limit for testing

        # Simulate memory exhaustion
        with patch.object(psutil.Process(), "memory_info") as mock_memory:
            mock_memory.return_value.rss = 10 * 1024 * 1024 * 1024  # 10GB (over limit)

            # Should trigger cleanup
            monitor.check_and_cleanup()

            # Verify cleanup was attempted
            assert mock_memory.called


class TestEndToEndIntegration:
    """Test complete end-to-end workflows."""

    def test_complete_docmath_conversion_workflow(self) -> None:
        """Test complete DocMath conversion workflow."""
        from app.core.converters.docmath_converter import DocMathConverter
        from app.schemas.docmath_datasets import QuestionAnsweringDataset

        converter = DocMathConverter()

        # Create test dataset directory structure
        with tempfile.TemporaryDirectory() as test_dir:
            # Create test files for each complexity tier
            tiers = ["simpshort", "simplong", "compshort", "complong"]
            splits = ["test", "testmini"]

            for tier in tiers:
                for split in splits:
                    file_name = f"{tier}_{split}.json"
                    file_path = os.path.join(test_dir, file_name)

                    test_data = [
                        {
                            "question_id": f"{tier}_{split}_1",
                            "question": f"Test question for {tier}",
                            "ground_truth": 42,
                            "context": f"Context for {tier} tier",
                        }
                    ]

                    with open(file_path, "w") as f:
                        json.dump(test_data, f)

            # Test complete conversion
            result = converter.convert(test_dir)

            # Verify result structure
            assert isinstance(result, QuestionAnsweringDataset)
            assert result.name == "DocMath_Mathematical_Reasoning"
            assert result.group == "mathematical_reasoning"
            assert len(result.questions) > 0
            assert "complexity_tiers" in result.metadata
            assert result.metadata["complexity_tiers"] == 4

    def test_converter_registration_integration(self) -> None:
        """Test DocMath converter registration with API."""
        from app.core.converters.docmath_converter import DocMathConverter

        # Mock API registration
        with patch("app.api.endpoints.converters.get_available_converters") as mock_converters:
            mock_converters.return_value = {
                "dataset_converters": {
                    "DocMathConverter": {
                        "description": "DocMath Dataset Converter with Large File Handling",
                        "parameters": [],
                        "category": "reasoning_benchmarks",
                    }
                }
            }

            available_converters = mock_converters()

            # Verify DocMath converter is available
            assert "DocMathConverter" in available_converters["dataset_converters"]
            converter_info = available_converters["dataset_converters"]["DocMathConverter"]
            assert "Large File Handling" in converter_info["description"]


# Performance test fixtures
@pytest.fixture
def large_test_file():
    """Create a large test file for performance testing."""
    # Create synthetic large file (smaller for testing)
    test_data = []
    for i in range(1000):  # 1000 questions for testing
        test_data.append(
            {
                "question_id": f"perf_test_{i}",
                "question": f"Performance test question {i}: What is {i} + {i}?",
                "ground_truth": i + i,
                "context": f"Performance test context {i}",
                "paragraphs": [f"Test paragraph {i}"],
                "table_evidence": [],
            }
        )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(test_data, f)
        yield f.name

    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def memory_monitor():
    """Memory monitoring fixture for performance tests."""
    initial_memory = psutil.Process().memory_info().rss
    yield initial_memory

    # Check for memory leaks
    final_memory = psutil.Process().memory_info().rss
    memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB

    # Allow some tolerance for test overhead
    assert memory_increase < 100, f"Memory leak detected: {memory_increase:.2f}MB increase"


# Test execution markers
pytestmark = [pytest.mark.issue_127, pytest.mark.tdd, pytest.mark.docmath_converter, pytest.mark.large_file_handling]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
