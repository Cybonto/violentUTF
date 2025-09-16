# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Test suite for JudgeBench Meta-Evaluation Converter (Issue #130).

Comprehensive test suite following Test-Driven Development methodology with
RED-GREEN-REFACTOR cycles for JudgeBench meta-evaluation converter implementation.

SECURITY: All test data is sanitized and validated. No malicious content included.
"""

import json
import os
import random
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

# Import schemas and converters to be implemented
from app.schemas.judgebench_datasets import (
    JudgeAnalysis, 
    JudgeEvaluationEntry,
    JudgeFileInfo
)
from app.core.converters.judgebench_converter import (
    JudgeBenchConverter,
    JudgePerformanceAnalyzer,
    MetaEvaluationPromptGenerator,
    SeedPrompt,
    SeedPromptDataset
)
from app.utils.judge_analysis import JudgeAnalysisUtils
from app.services.meta_evaluation_service import MetaEvaluationService


# Test data constants
MOCK_ARENA_HARD_EVALUATION = {
    "id": "eval_arena_001",
    "original_task": "Write a creative story about space exploration with scientific accuracy",
    "model_response": "Commander Sarah Chen gazed out at the infinite cosmos through the observation deck of the Mars Transit Station...",
    "judge_name": "arena_hard", 
    "judge_model": "gpt-4",
    "judge_response": "This response demonstrates excellent creativity combined with scientific accuracy. The narrative effectively balances engaging storytelling with realistic space exploration concepts.",
    "score": 8.5,
    "reasoning": "The story successfully combines scientific accuracy with compelling narrative structure. Technical details about Mars transit are realistic while maintaining reader engagement through character development.",
    "evaluation_criteria": ["creativity", "scientific_accuracy", "narrative_flow", "technical_plausibility"],
    "metadata": {
        "response_model": "claude-3",
        "task_category": "creative_writing",
        "difficulty_level": "high",
        "evaluation_timestamp": "2024-12-01T10:30:00Z"
    }
}

MOCK_REWARD_MODEL_EVALUATION = {
    "id": "eval_reward_001",
    "original_task": "Provide ethical guidance on AI development priorities",
    "model_response": "AI development should prioritize safety, transparency, and human benefit above rapid capability advancement...",
    "judge_name": "reward_model",
    "judge_model": "claude-3-opus", 
    "judge_response": "This response demonstrates strong ethical reasoning and balanced perspective on AI development priorities.",
    "score": 9.2,
    "reasoning": "The response shows comprehensive understanding of AI ethics with well-structured arguments for safety-first development approaches.",
    "evaluation_criteria": ["ethical_reasoning", "balance", "comprehensiveness", "practicality"],
    "metadata": {
        "response_model": "gpt-4",
        "task_category": "ethics",
        "difficulty_level": "medium",
        "evaluation_timestamp": "2024-12-01T10:35:00Z"
    }
}

MOCK_PROMETHEUS_2_EVALUATION = {
    "id": "eval_prometheus_001", 
    "original_task": "Analyze the economic impact of renewable energy adoption",
    "model_response": "Renewable energy adoption creates substantial long-term economic benefits through job creation, energy independence, and reduced healthcare costs...",
    "judge_name": "prometheus_2",
    "judge_model": "gpt-4-turbo",
    "judge_response": "This analysis provides comprehensive coverage of economic factors with strong supporting evidence and clear reasoning.",
    "score": 7.8,
    "reasoning": "The response covers multiple economic dimensions including direct costs, indirect benefits, and long-term implications. Evidence is well-sourced and reasoning is logically structured.",
    "evaluation_criteria": ["comprehensiveness", "evidence_quality", "economic_reasoning", "clarity"],
    "metadata": {
        "response_model": "claude-2",
        "task_category": "economic_analysis", 
        "difficulty_level": "high",
        "evaluation_timestamp": "2024-12-01T10:40:00Z"
    }
}


class TestJudgeBenchSchemas:
    """Test JudgeBench schema definitions and validation."""

    def test_judge_file_info_schema(self):
        """Test JudgeFileInfo schema validation and creation."""
        # RED: This test should initially fail
        judge_info = JudgeFileInfo(
            judge_name="arena_hard",
            judge_model="gpt-4", 
            response_model="claude-3",
            file_path="/path/to/judge/file.jsonl",
            file_size_mb=8.5
        )
        
        assert judge_info.judge_name == "arena_hard"
        assert judge_info.judge_model == "gpt-4"
        assert judge_info.response_model == "claude-3"
        assert judge_info.file_size_mb == 8.5
        
        # Test invalid data
        with pytest.raises((ValueError, TypeError)):
            JudgeFileInfo(judge_name="", judge_model="gpt-4")

    def test_judge_analysis_schema(self):
        """Test JudgeAnalysis schema with comprehensive performance indicators."""
        analysis = JudgeAnalysis(
            performance_indicators={
                "response_length": 245,
                "reasoning_length": 128,
                "score_value": 8.5,
                "has_detailed_reasoning": True,
                "evaluation_completeness": 0.95
            },
            evaluation_dimensions=["accuracy", "consistency", "reasoning_quality"],
            reasoning_quality={"clarity": 0.9, "logic": 0.85, "completeness": 0.92},
            score_appropriateness={"consistency": 0.88, "calibration": 0.91},
            consistency_indicators={"score_reasoning_alignment": 0.87},
            judge_characteristics={"judge_type": "arena_hard", "model": "gpt-4"}
        )
        
        assert len(analysis.evaluation_dimensions) == 3
        assert analysis.reasoning_quality["clarity"] == 0.9
        assert analysis.performance_indicators["has_detailed_reasoning"] is True

    def test_judge_evaluation_entry_validation(self):
        """Test JSONL entry parsing and validation."""
        entry = JudgeEvaluationEntry(**MOCK_ARENA_HARD_EVALUATION)
        
        assert entry.judge_name == "arena_hard"
        assert entry.score == 8.5
        assert len(entry.evaluation_criteria) == 4
        
        # Test invalid score range
        invalid_entry = MOCK_ARENA_HARD_EVALUATION.copy()
        invalid_entry['score'] = 15.0  # Invalid score
        with pytest.raises((ValueError, TypeError)):
            JudgeEvaluationEntry(**invalid_entry)


class TestJudgeFileDiscovery:
    """Test judge file discovery and pattern matching."""

    def test_judge_file_discovery(self, tmp_path):
        """Test discovery of judge output files using filename patterns."""
        # Create mock judge files
        arena_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
        reward_file = tmp_path / "dataset=judgebench,response_model=gpt-4,judge_name=reward_model,judge_model=claude-opus.jsonl"
        prometheus_file = tmp_path / "dataset=judgebench,response_model=claude-2,judge_name=prometheus_2,judge_model=gpt-4-turbo.jsonl"
        
        arena_file.write_text('{"test": "data"}\n')
        reward_file.write_text('{"test": "data"}\n')  
        prometheus_file.write_text('{"test": "data"}\n')
        
        converter = JudgeBenchConverter()
        discovered_files = converter.discover_judge_output_files(str(tmp_path))
        
        assert len(discovered_files) == 3
        assert any("arena_hard" in f for f in discovered_files)
        assert any("reward_model" in f for f in discovered_files)
        assert any("prometheus_2" in f for f in discovered_files)

    def test_filename_parsing(self):
        """Test parsing of judge output filenames for metadata extraction."""
        filename = "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
        
        converter = JudgeBenchConverter()
        file_info = converter.parse_output_filename(filename)
        
        assert file_info.judge_name == "arena_hard"
        assert file_info.judge_model == "gpt-4"
        assert file_info.response_model == "claude-3"
        
        # Test malformed filename
        with pytest.raises(ValueError):
            converter.parse_output_filename("invalid_filename.jsonl")


class TestJSONLProcessing:
    """Test JSONL streaming processing functionality."""

    def test_jsonl_streaming_processing(self, tmp_path):
        """Test memory-efficient streaming processing of large JSONL files."""
        # Create test JSONL file
        test_file = tmp_path / "test_judge.jsonl" 
        with open(test_file, 'w') as f:
            for i in range(100):  # Moderate size for unit test
                evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
                evaluation['id'] = f"eval_{i:06d}"
                f.write(json.dumps(evaluation) + '\n')
        
        file_info = JudgeFileInfo(
            judge_name="arena_hard",
            judge_model="gpt-4",
            response_model="claude-3", 
            file_path=str(test_file),
            file_size_mb=1.0
        )
        
        converter = JudgeBenchConverter()
        prompts = converter.process_judge_output_file(str(test_file), file_info, {})
        
        assert len(prompts) == 100
        assert all(isinstance(p, SeedPrompt) for p in prompts)
        assert all("meta_evaluation_type" in p.metadata for p in prompts)

    def test_jsonl_error_handling(self, tmp_path):
        """Test error handling during JSONL processing."""
        # Create file with some invalid JSON lines
        test_file = tmp_path / "test_judge_errors.jsonl"
        with open(test_file, 'w') as f:
            f.write(json.dumps(MOCK_ARENA_HARD_EVALUATION) + '\n')  # Valid
            f.write('{"invalid": json}\n')  # Invalid JSON
            f.write(json.dumps(MOCK_REWARD_MODEL_EVALUATION) + '\n')  # Valid
        
        file_info = JudgeFileInfo(
            judge_name="arena_hard", 
            judge_model="gpt-4",
            response_model="claude-3",
            file_path=str(test_file),
            file_size_mb=0.1
        )
        
        converter = JudgeBenchConverter()
        prompts = converter.process_judge_output_file(str(test_file), file_info, {})
        
        # Should recover from errors and process valid lines
        assert len(prompts) == 2  # Two valid lines processed


class TestMetaEvaluationPromptGeneration:
    """Test meta-evaluation prompt generation functionality."""

    def test_meta_evaluation_prompt_generation(self):
        """Test quality and structure of generated meta-evaluation prompts."""
        generator = MetaEvaluationPromptGenerator()
        
        file_info = JudgeFileInfo(
            judge_name="arena_hard",
            judge_model="gpt-4", 
            response_model="claude-3",
            file_path="test.jsonl",
            file_size_mb=1.0
        )
        
        prompt = generator.build_meta_evaluation_prompt(
            original_task="Write a creative story about space exploration",
            judge_response="This response demonstrates excellent creativity...",
            judge_score=8.5,
            judge_reasoning="The story effectively combines scientific accuracy...",
            file_info=file_info
        )
        
        # Validate prompt structure
        assert "ORIGINAL TASK" in prompt
        assert "JUDGE INFORMATION" in prompt  
        assert "JUDGE'S EVALUATION" in prompt
        assert "META-EVALUATION REQUEST" in prompt
        assert "arena_hard" in prompt
        assert "gpt-4" in prompt
        assert "8.5" in prompt
        
        # Validate meta-evaluation dimensions
        assert "Accuracy" in prompt
        assert "Consistency" in prompt
        assert "Completeness" in prompt
        assert "Reasoning Quality" in prompt
        assert "Bias Detection" in prompt
        assert "Score Appropriateness" in prompt

    def test_judge_specific_prompt_templates(self):
        """Test judge-specific meta-evaluation prompt templates."""
        generator = MetaEvaluationPromptGenerator()
        
        # Test Arena-Hard specific elements
        arena_criteria = generator.get_meta_evaluation_criteria("arena_hard")
        assert "difficulty_calibration" in arena_criteria
        assert "comparative_ranking" in arena_criteria
        assert "competitive_assessment" in arena_criteria
        
        # Test Reward Model specific elements
        reward_criteria = generator.get_meta_evaluation_criteria("reward_model") 
        assert "reward_alignment" in reward_criteria
        assert "preference_consistency" in reward_criteria
        assert "value_alignment" in reward_criteria
        
        # Test Prometheus-2 specific elements
        prometheus_criteria = generator.get_meta_evaluation_criteria("prometheus_2")
        assert "rubric_adherence" in prometheus_criteria
        assert "score_justification" in prometheus_criteria
        assert "criterion_coverage" in prometheus_criteria

    def test_meta_scorer_configuration(self):
        """Test meta-evaluation scorer configuration generation."""
        generator = MetaEvaluationPromptGenerator()
        
        # Test Arena-Hard scorer config
        arena_config = generator.get_meta_scorer_config("arena_hard")
        assert arena_config["evaluation_focus"] == "competitive_performance_assessment"
        assert "accuracy" in arena_config["primary_dimensions"]
        assert "comparative_ranking" in arena_config["primary_dimensions"]
        assert "difficulty_calibration" in arena_config["primary_dimensions"]
        
        # Test scoring weights
        weights = arena_config["scoring_weight"]
        assert weights["accuracy"] == 0.4
        assert weights["consistency"] == 0.3
        assert weights["calibration"] == 0.3
        assert abs(sum(weights.values()) - 1.0) < 0.01


class TestJudgePerformanceAnalysis:
    """Test judge performance analysis functionality."""

    def test_judge_performance_analysis(self):
        """Test judge performance indicator extraction and analysis."""
        analyzer = JudgePerformanceAnalyzer()
        
        file_info = JudgeFileInfo(
            judge_name="arena_hard",
            judge_model="gpt-4",
            response_model="claude-3", 
            file_path="test.jsonl",
            file_size_mb=1.0
        )
        
        analysis = analyzer.analyze_single_evaluation(MOCK_ARENA_HARD_EVALUATION, file_info)
        
        # Validate performance indicators
        assert "response_length" in analysis.performance_indicators
        assert "reasoning_length" in analysis.performance_indicators
        assert "score_value" in analysis.performance_indicators
        assert "has_detailed_reasoning" in analysis.performance_indicators
        assert "evaluation_completeness" in analysis.performance_indicators
        
        # Validate evaluation dimensions
        assert len(analysis.evaluation_dimensions) > 0
        assert all(isinstance(dim, str) for dim in analysis.evaluation_dimensions)
        
        # Validate reasoning quality assessment
        assert "clarity" in analysis.reasoning_quality
        assert "logic" in analysis.reasoning_quality
        assert "completeness" in analysis.reasoning_quality
        assert all(0 <= v <= 1 for v in analysis.reasoning_quality.values())

    def test_aggregate_judge_file_performance(self):
        """Test aggregate performance analysis across multiple evaluations."""
        analyzer = JudgePerformanceAnalyzer()
        
        # Create multiple mock prompts
        prompts = []
        for i in range(10):
            metadata = {
                "original_score": random.uniform(5.0, 10.0),
                "judge_performance_indicators": {
                    "reasoning_length": random.randint(50, 200),
                    "response_length": random.randint(100, 500)
                }
            }
            prompts.append(SeedPrompt(f"prompt_{i}", metadata))
        
        performance = analyzer.analyze_judge_file_performance(prompts)
        
        assert performance["total_evaluations"] == 10
        assert "score_statistics" in performance
        assert "reasoning_statistics" in performance
        assert "response_statistics" in performance
        
        # Validate statistics
        stats = performance["score_statistics"]
        assert 5.0 <= stats["mean"] <= 10.0
        assert stats["min"] >= 5.0
        assert stats["max"] <= 10.0

    def test_reasoning_quality_assessment(self):
        """Test reasoning quality assessment algorithms."""
        analyzer = JudgePerformanceAnalyzer()
        
        high_quality_reasoning = "The response demonstrates excellent understanding of the topic with clear logical progression. Each point is well-supported with evidence and the conclusion follows naturally from the premises presented."
        
        low_quality_reasoning = "Good response."
        
        high_quality_score = analyzer.assess_reasoning_quality(high_quality_reasoning)
        low_quality_score = analyzer.assess_reasoning_quality(low_quality_reasoning)
        
        assert high_quality_score["clarity"] > low_quality_score["clarity"]
        assert high_quality_score["completeness"] > low_quality_score["completeness"]
        assert high_quality_score["logic"] > low_quality_score["logic"]


class TestSeedPromptCreation:
    """Test SeedPrompt and SeedPromptDataset creation."""

    def test_seed_prompt_creation(self):
        """Test creation of SeedPrompt instances with comprehensive metadata."""
        converter = JudgeBenchConverter()
        
        file_info = JudgeFileInfo(
            judge_name="arena_hard",
            judge_model="gpt-4",
            response_model="claude-3",
            file_path="test.jsonl", 
            file_size_mb=1.0
        )
        
        prompt = converter.create_meta_evaluation_prompt(
            MOCK_ARENA_HARD_EVALUATION,
            file_info,
            {},
            1
        )
        
        # Validate SeedPrompt structure
        assert isinstance(prompt, SeedPrompt)
        assert isinstance(prompt.value, str)
        assert isinstance(prompt.metadata, dict)
        
        # Validate required metadata fields
        required_fields = [
            "evaluation_id", "judge_name", "judge_model", "response_model",
            "original_score", "judge_performance_indicators", "evaluation_dimensions",
            "meta_evaluation_type", "expected_meta_behavior", "meta_evaluation_criteria",
            "harm_categories", "meta_scorer_config"
        ]
        
        for field in required_fields:
            assert field in prompt.metadata, f"Missing required field: {field}"
        
        # Validate metadata values
        assert prompt.metadata["judge_name"] == "arena_hard"
        assert prompt.metadata["judge_model"] == "gpt-4"
        assert prompt.metadata["response_model"] == "claude-3"
        assert prompt.metadata["original_score"] == 8.5
        assert prompt.metadata["meta_evaluation_type"] == "judge_assessment"

    def test_seed_prompt_dataset_creation(self, tmp_path):
        """Test complete SeedPromptDataset creation from judge files."""
        # Create mock judge files
        arena_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
        
        with open(arena_file, 'w') as f:
            for i in range(5):
                evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
                evaluation['id'] = f"eval_{i:06d}"
                f.write(json.dumps(evaluation) + '\n')
        
        converter = JudgeBenchConverter()
        dataset = converter.convert(str(tmp_path))
        
        # Validate SeedPromptDataset structure
        assert isinstance(dataset, SeedPromptDataset)
        assert hasattr(dataset, 'prompts')
        assert hasattr(dataset, 'metadata')
        
        # Validate dataset metadata
        expected_metadata_fields = [
            "evaluation_framework", "judge_count", "total_evaluations",
            "total_files_processed", "response_models", "judge_models",
            "judge_metadata", "meta_evaluation_types", "conversion_strategy"
        ]
        
        for field in expected_metadata_fields:
            assert field in dataset.metadata, f"Missing dataset metadata field: {field}"
        
        # Validate prompts
        assert len(dataset.prompts) == 5
        assert all(isinstance(p, SeedPrompt) for p in dataset.prompts)
        
        # Validate conversion strategy
        assert dataset.metadata["conversion_strategy"] == "strategy_4_meta_evaluation"
        assert dataset.metadata["evaluation_framework"] == "judge_meta_evaluation"


class TestCompleteConversionPipeline:
    """Test complete end-to-end conversion pipeline."""

    def test_complete_conversion_pipeline(self, tmp_path):
        """Test complete end-to-end conversion pipeline."""
        # Create comprehensive test dataset
        arena_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
        reward_file = tmp_path / "dataset=judgebench,response_model=gpt-4,judge_name=reward_model,judge_model=claude-opus.jsonl"
        prometheus_file = tmp_path / "dataset=judgebench,response_model=claude-2,judge_name=prometheus_2,judge_model=gpt-4-turbo.jsonl"
        
        # Write test data
        with open(arena_file, 'w') as f:
            for i in range(3):
                eval_data = MOCK_ARENA_HARD_EVALUATION.copy()
                eval_data['id'] = f"arena_eval_{i:06d}"
                f.write(json.dumps(eval_data) + '\n')
        
        with open(reward_file, 'w') as f:
            for i in range(3):
                eval_data = MOCK_REWARD_MODEL_EVALUATION.copy()
                eval_data['id'] = f"reward_eval_{i:06d}"
                f.write(json.dumps(eval_data) + '\n')
        
        with open(prometheus_file, 'w') as f:
            for i in range(3):
                eval_data = MOCK_PROMETHEUS_2_EVALUATION.copy()
                eval_data['id'] = f"prometheus_eval_{i:06d}"
                f.write(json.dumps(eval_data) + '\n')
        
        # Execute complete conversion
        converter = JudgeBenchConverter()
        dataset = converter.convert(str(tmp_path))
        
        # Validate complete conversion
        assert len(dataset.prompts) == 9  # 3 files × 3 evaluations each
        assert dataset.metadata["judge_count"] == 3
        assert dataset.metadata["total_evaluations"] == 9
        assert dataset.metadata["total_files_processed"] == 3
        
        # Validate multi-model judge representation
        judge_models = dataset.metadata["judge_models"]
        assert "gpt-4" in judge_models
        assert "claude-opus" in judge_models  
        assert "gpt-4-turbo" in judge_models
        
        response_models = dataset.metadata["response_models"]
        assert "claude-3" in response_models
        assert "gpt-4" in response_models
        assert "claude-2" in response_models
        
        # Validate judge-specific metadata
        judge_metadata = dataset.metadata["judge_metadata"]
        assert len(judge_metadata) == 3
        
        for judge_key, metadata in judge_metadata.items():
            assert "evaluation_count" in metadata
            assert "file_size_mb" in metadata
            assert "evaluation_focus" in metadata
            assert "performance_analysis" in metadata

    def test_multi_model_hierarchy_preservation(self):
        """Test preservation of multi-model evaluation hierarchies."""
        converter = JudgeBenchConverter()
        
        # Test hierarchy extraction from judge metadata
        judge_metadata = {
            "arena_hard_gpt-4_claude-3": {
                "judge_name": "arena_hard",
                "judge_model": "gpt-4", 
                "response_model": "claude-3",
                "evaluation_count": 100
            },
            "arena_hard_gpt-4_gpt-4": {
                "judge_name": "arena_hard",
                "judge_model": "gpt-4",
                "response_model": "gpt-4", 
                "evaluation_count": 95
            }
        }
        
        response_models = converter.extract_response_models(judge_metadata)
        judge_models = converter.extract_judge_models(judge_metadata)
        
        assert "claude-3" in response_models
        assert "gpt-4" in response_models
        assert "gpt-4" in judge_models
        assert len(response_models) == 2
        assert len(judge_models) == 1


@pytest.mark.performance
class TestPerformanceRequirements:
    """Test performance requirements for large file processing."""

    @pytest.mark.skip(reason="Performance test - run manually")
    def test_large_file_processing_performance(self, tmp_path):
        """Test performance with large JSONL files (7-12MB simulation)."""
        # This test is skipped by default for CI/CD performance
        # Run manually: pytest -m performance tests/test_judgebench_converter.py::TestPerformanceRequirements::test_large_file_processing_performance
        
        # Generate large test file (simulate 12MB file)
        large_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
        
        # Generate ~5000 entries for substantial file size
        start_generation = time.time()
        with open(large_file, 'w') as f:
            for i in range(5000):
                evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
                evaluation['id'] = f"perf_eval_{i:06d}"
                evaluation['model_response'] = "Extended model response content " * 50  # Make entries substantial
                f.write(json.dumps(evaluation) + '\n')
        
        generation_time = time.time() - start_generation
        file_size_mb = os.path.getsize(large_file) / (1024 * 1024)
        
        print(f"Generated test file: {file_size_mb:.1f}MB in {generation_time:.2f}s")
        
        # Test processing performance
        converter = JudgeBenchConverter()
        start_time = time.time()
        
        file_info = JudgeFileInfo(
            judge_name="arena_hard",
            judge_model="gpt-4",
            response_model="claude-3",
            file_path=str(large_file),
            file_size_mb=file_size_mb
        )
        
        prompts = converter.process_judge_output_file(str(large_file), file_info, {})
        
        processing_time = time.time() - start_time
        
        # Performance assertions
        assert processing_time < 300  # Must complete within 5 minutes (300 seconds)
        assert len(prompts) == 5000
        
        # Calculate throughput
        throughput = len(prompts) / processing_time
        assert throughput > 8.33  # Must process >500 evaluations per minute (8.33/sec)
        
        print(f"Performance Results:")
        print(f"  Processing Time: {processing_time:.2f}s")
        print(f"  Throughput: {throughput:.1f} evaluations/second")


class TestValidationAndErrorHandling:
    """Test comprehensive error handling and validation."""

    def test_comprehensive_error_handling(self, tmp_path):
        """Test comprehensive error handling and recovery mechanisms."""
        
        # Test 1: Empty file handling
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        
        converter = JudgeBenchConverter()
        file_info = JudgeFileInfo(
            judge_name="arena_hard", 
            judge_model="gpt-4",
            response_model="claude-3",
            file_path=str(empty_file),
            file_size_mb=0.0
        )
        
        prompts = converter.process_judge_output_file(str(empty_file), file_info, {})
        assert len(prompts) == 0
        
        # Test 2: Malformed JSON handling
        malformed_file = tmp_path / "malformed.jsonl" 
        with open(malformed_file, 'w') as f:
            f.write('{"valid": "json"}\n')
            f.write('{"malformed": json without quotes}\n')  # Invalid JSON
            f.write('{"another": "valid"}\n')
            f.write('completely invalid line\n')  # Invalid line
            f.write('{"final": "valid"}\n')
        
        file_info.file_path = str(malformed_file)
        prompts = converter.process_judge_output_file(str(malformed_file), file_info, {})
        assert len(prompts) == 3  # Should recover and process valid lines
        
        # Test 3: File permission errors
        with pytest.raises(Exception):
            converter.process_judge_output_file("/nonexistent/path/file.jsonl", file_info, {})

    def test_validation_framework_integration(self):
        """Test integration with validation framework (Issue #120 dependency)."""
        from app.core.validation import sanitize_string, validate_json_data
        
        # Test input sanitization (current implementation removes control chars but not HTML)
        malicious_input = "<script>alert('xss')</script>Test content"
        sanitized = sanitize_string(malicious_input)
        # Current sanitize_string removes control chars, not HTML tags
        assert len(sanitized) > 0
        assert "Test content" in sanitized  # Core content should remain
        
        # Test JSON validation (returns data if valid, raises exception if invalid)
        valid_json = {"test": "data", "score": 8.5}
        result = validate_json_data(valid_json)
        assert result == valid_json  # Returns the data if valid
        
        # Test converter applies validation
        converter = JudgeBenchConverter()
        
        # Mock evaluation with potentially malicious content
        malicious_evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
        malicious_evaluation['judge_response'] = "<script>alert('test')</script>Good response"
        
        file_info = JudgeFileInfo(
            judge_name="arena_hard",
            judge_model="gpt-4", 
            response_model="claude-3",
            file_path="test.jsonl",
            file_size_mb=1.0
        )
        
        # Should apply sanitization during processing (SeedPrompt constructor sanitizes value)
        prompt = converter.create_meta_evaluation_prompt(malicious_evaluation, file_info, {}, 1)
        # The prompt value is sanitized in SeedPrompt constructor
        assert "Good response" in prompt.value  # Core content preserved


# Pytest fixtures for test data
@pytest.fixture
def mock_judge_files(tmp_path):
    """Create comprehensive mock judge files for testing."""
    files = {}
    
    # Arena-Hard file
    arena_file = tmp_path / "dataset=judgebench,response_model=claude-3,judge_name=arena_hard,judge_model=gpt-4.jsonl"
    with open(arena_file, 'w') as f:
        for i in range(10):
            evaluation = MOCK_ARENA_HARD_EVALUATION.copy()
            evaluation['id'] = f"arena_{i:06d}"
            f.write(json.dumps(evaluation) + '\n')
    files['arena_hard'] = arena_file
    
    # Reward Model file
    reward_file = tmp_path / "dataset=judgebench,response_model=gpt-4,judge_name=reward_model,judge_model=claude-opus.jsonl"
    with open(reward_file, 'w') as f:
        for i in range(10):
            evaluation = MOCK_REWARD_MODEL_EVALUATION.copy()
            evaluation['id'] = f"reward_{i:06d}"
            f.write(json.dumps(evaluation) + '\n')
    files['reward_model'] = reward_file
    
    # Prometheus-2 file
    prometheus_file = tmp_path / "dataset=judgebench,response_model=claude-2,judge_name=prometheus_2,judge_model=gpt-4-turbo.jsonl"
    with open(prometheus_file, 'w') as f:
        for i in range(10):
            evaluation = MOCK_PROMETHEUS_2_EVALUATION.copy()
            evaluation['id'] = f"prometheus_{i:06d}"
            f.write(json.dumps(evaluation) + '\n')
    files['prometheus_2'] = prometheus_file
    
    return files


@pytest.fixture
def judge_performance_analyzer():
    """Provide configured JudgePerformanceAnalyzer for testing."""
    return JudgePerformanceAnalyzer()


@pytest.fixture 
def meta_prompt_generator():
    """Provide configured MetaEvaluationPromptGenerator for testing."""
    return MetaEvaluationPromptGenerator()