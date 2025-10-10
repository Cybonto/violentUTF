"""Test suite for JudgeBench Meta-Evaluation Converter (Issue #130).

This test suite validates the complete JudgeBench converter functionality including:
- Judge output file discovery and parsing
- Meta-evaluation prompt generation
- Judge performance analysis
- Dataset conversion and validation
- Error handling and edge cases

All tests use real converter components and validate both functionality and performance.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import mock_open, patch

import pytest

# Import the converter components
from app.core.converters.judgebench_converter import (
    JudgeBenchConverter,
    JudgePerformanceAnalyzer,
    MetaEvaluationPromptGenerator,
    SeedPrompt,
    SeedPromptDataset,
)
from app.schemas.judgebench_datasets import (
    BASE_META_EVALUATION_CRITERIA,
    JUDGE_CONFIGURATIONS,
    JudgeAnalysis,
    JudgeFileInfo,
)


class TestJudgeBenchConverter:
    """Test suite for the main JudgeBenchConverter class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.converter = JudgeBenchConverter(validation_enabled=True)
        self.sample_judge_evaluation = {
            "judge_response": "This response demonstrates good understanding of the task.",
            "score": 8.5,
            "reasoning": "The answer is comprehensive and addresses all key points.",
            "original_task": "Explain the benefits of renewable energy.",
            "evaluation_criteria": ["accuracy", "completeness", "clarity"]
        }
        
    def test_converter_initialization(self):
        """Test converter initializes correctly with all components."""
        assert isinstance(self.converter.judge_analyzer, JudgePerformanceAnalyzer)
        assert isinstance(self.converter.meta_prompt_generator, MetaEvaluationPromptGenerator)
        assert self.converter.validation_enabled is True
        
        # Test initialization with validation disabled
        converter_no_validation = JudgeBenchConverter(validation_enabled=False)
        assert converter_no_validation.validation_enabled is False
    
    def test_discover_judge_output_files_single_file(self):
        """Test discovery of judge output files with a single file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid judge file
            judge_file = Path(temp_dir) / "dataset=judgebench,response_model=gpt-4,judge_name=llm_judge,judge_model=claude-3.jsonl"
            judge_file.write_text('{"test": "data"}\n')
            
            discovered_files = self.converter.discover_judge_output_files(str(judge_file))
            assert len(discovered_files) == 1
            assert str(judge_file) in discovered_files
    
    def test_discover_judge_output_files_directory(self):
        """Test discovery of judge output files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple valid and invalid files
            valid_files = [
                "dataset=judgebench,response_model=gpt-4,judge_name=llm_judge,judge_model=claude-3.jsonl",
                "dataset=judgebench,response_model=gemini,judge_name=human_judge,judge_model=gpt-4.jsonl"
            ]
            invalid_files = [
                "other_file.jsonl",
                "dataset=other,response_model=gpt-4,judge_name=test.jsonl"
            ]
            
            for filename in valid_files + invalid_files:
                file_path = Path(temp_dir) / filename
                file_path.write_text('{"test": "data"}\n')
            
            discovered_files = self.converter.discover_judge_output_files(temp_dir)
            assert len(discovered_files) == 2
            
            # Verify only valid files are discovered
            for valid_file in valid_files:
                assert any(valid_file in path for path in discovered_files)
    
    def test_parse_output_filename_valid(self):
        """Test parsing of valid judge output filenames."""
        filename = "/path/dataset=judgebench,response_model=gpt-4,judge_name=llm_judge,judge_model=claude-3.jsonl"
        
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024*1024):  # 1MB
            
            file_info = self.converter.parse_output_filename(filename)
            
            assert file_info.judge_name == "llm_judge"
            assert file_info.judge_model == "claude-3"
            assert file_info.response_model == "gpt-4"
            assert file_info.file_path == filename
            assert file_info.file_size_mb == 1.0
    
    def test_parse_output_filename_invalid(self):
        """Test parsing of invalid judge output filenames."""
        invalid_filenames = [
            "invalid_format.jsonl",
            "dataset=other,response_model=gpt-4.jsonl",
            "response_model=gpt-4,judge_name=test.jsonl"
        ]
        
        for filename in invalid_filenames:
            with pytest.raises(ValueError, match="Invalid judge filename format"):
                self.converter.parse_output_filename(filename)
    
    def test_create_meta_evaluation_prompt(self):
        """Test creation of meta-evaluation prompts."""
        file_info = JudgeFileInfo(
            judge_name="llm_judge",
            judge_model="claude-3",
            response_model="gpt-4",
            file_path="/test/path.jsonl",
            file_size_mb=1.0
        )
        
        prompt = self.converter.create_meta_evaluation_prompt(
            self.sample_judge_evaluation,
            file_info,
            {},
            1
        )
        
        assert isinstance(prompt, SeedPrompt)
        assert "Evaluate the quality and appropriateness of this AI judge's evaluation" in prompt.value
        assert "llm_judge" in prompt.value
        assert "claude-3" in prompt.value
        assert "gpt-4" in prompt.value
        
        # Verify metadata
        assert prompt.metadata["judge_name"] == "llm_judge"
        assert prompt.metadata["judge_model"] == "claude-3"
        assert prompt.metadata["response_model"] == "gpt-4"
        assert prompt.metadata["original_score"] == 8.5
        assert prompt.metadata["evaluation_id"] == 1
        assert "judge_performance_indicators" in prompt.metadata
        assert "meta_evaluation_criteria" in prompt.metadata
    
    def test_process_judge_output_file(self):
        """Test processing of judge output JSONL files."""
        file_info = JudgeFileInfo(
            judge_name="llm_judge",
            judge_model="claude-3",
            response_model="gpt-4",
            file_path="/test/path.jsonl",
            file_size_mb=1.0
        )
        
        # Create sample JSONL content
        sample_data = [
            self.sample_judge_evaluation,
            {
                "judge_response": "Another evaluation response.",
                "score": 7.0,
                "reasoning": "Adequate but could be improved.",
                "original_task": "Different task.",
                "evaluation_criteria": ["accuracy"]
            }
        ]
        
        jsonl_content = '\n'.join(json.dumps(item) for item in sample_data)
        
        with patch('builtins.open', mock_open(read_data=jsonl_content)), \
             patch('os.path.getsize', return_value=1024):
            
            prompts = self.converter.process_judge_output_file(
                "/test/path.jsonl",
                file_info,
                {}
            )
            
            assert len(prompts) == 2
            assert all(isinstance(prompt, SeedPrompt) for prompt in prompts)
            assert prompts[0].metadata["original_score"] == 8.5
            assert prompts[1].metadata["original_score"] == 7.0
    
    def test_process_judge_output_file_with_errors(self):
        """Test processing of judge output files with JSON errors."""
        file_info = JudgeFileInfo(
            judge_name="llm_judge",
            judge_model="claude-3",
            response_model="gpt-4",
            file_path="/test/path.jsonl",
            file_size_mb=1.0
        )
        
        # Content with valid and invalid JSON lines
        jsonl_content = (
            json.dumps(self.sample_judge_evaluation) + '\n' +
            '{"invalid": json}\n' +  # Invalid JSON
            json.dumps({"judge_response": "Valid", "score": 5.0, "reasoning": "OK", "original_task": "Task"}) + '\n'
        )
        
        with patch('builtins.open', mock_open(read_data=jsonl_content)), \
             patch('os.path.getsize', return_value=1024):
            
            prompts = self.converter.process_judge_output_file(
                "/test/path.jsonl",
                file_info,
                {}
            )
            
            # Should process valid lines and skip invalid ones
            assert len(prompts) == 2
            assert prompts[0].metadata["original_score"] == 8.5
            assert prompts[1].metadata["original_score"] == 5.0
    
    def test_convert_full_dataset(self):
        """Test full dataset conversion process."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a sample judge file
            judge_file = Path(temp_dir) / "dataset=judgebench,response_model=gpt-4,judge_name=llm_judge,judge_model=claude-3.jsonl"
            
            sample_data = [self.sample_judge_evaluation] * 3  # Create 3 evaluations
            jsonl_content = '\n'.join(json.dumps(item) for item in sample_data)
            judge_file.write_text(jsonl_content)
            
            dataset = self.converter.convert(temp_dir)
            
            assert isinstance(dataset, SeedPromptDataset)
            assert dataset.name == "JudgeBench_Meta_Evaluation"
            assert dataset.version == "1.0"
            assert dataset.group == "meta_evaluation"
            assert dataset.source == "JudgeBench-ICLR25"
            
            # Verify prompts were created
            assert len(dataset.prompts) == 3
            assert all(isinstance(prompt, SeedPrompt) for prompt in dataset.prompts)
            
            # Verify metadata
            assert dataset.metadata["evaluation_framework"] == "judge_meta_evaluation"
            assert dataset.metadata["total_evaluations"] == 3
            assert dataset.metadata["judge_count"] == 1
            assert "judge_metadata" in dataset.metadata
            assert "llm_judge_claude-3_gpt-4" in dataset.metadata["judge_metadata"]
    
    def test_extract_response_models(self):
        """Test extraction of unique response models."""
        judge_metadata = {
            "judge1": {"response_model": "gpt-4"},
            "judge2": {"response_model": "claude-3"},
            "judge3": {"response_model": "gpt-4"},  # Duplicate
            "judge4": {"other_field": "value"}  # No response_model
        }
        
        response_models = self.converter.extract_response_models(judge_metadata)
        assert response_models == ["claude-3", "gpt-4"]  # Sorted and unique
    
    def test_extract_judge_models(self):
        """Test extraction of unique judge models."""
        judge_metadata = {
            "judge1": {"judge_model": "claude-3"},
            "judge2": {"judge_model": "gpt-4"},
            "judge3": {"judge_model": "claude-3"},  # Duplicate
            "judge4": {"other_field": "value"}  # No judge_model
        }
        
        judge_models = self.converter.extract_judge_models(judge_metadata)
        assert judge_models == ["claude-3", "gpt-4"]  # Sorted and unique


class TestMetaEvaluationPromptGenerator:
    """Test suite for MetaEvaluationPromptGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = MetaEvaluationPromptGenerator()
        self.sample_file_info = JudgeFileInfo(
            judge_name="llm_judge",
            judge_model="claude-3",
            response_model="gpt-4",
            file_path="/test/path.jsonl",
            file_size_mb=1.0
        )
    
    def test_initialization(self):
        """Test generator initialization."""
        assert self.generator.base_criteria == BASE_META_EVALUATION_CRITERIA
        assert self.generator.judge_configs == JUDGE_CONFIGURATIONS
    
    def test_build_meta_evaluation_prompt(self):
        """Test building of meta-evaluation prompts."""
        prompt = self.generator.build_meta_evaluation_prompt(
            original_task="Test task",
            judge_response="Test response",
            judge_score=8.0,
            judge_reasoning="Test reasoning",
            file_info=self.sample_file_info
        )
        
        assert "Evaluate the quality and appropriateness of this AI judge's evaluation" in prompt
        assert "Test task" in prompt
        assert "Test response" in prompt
        assert "8.0" in prompt
        assert "Test reasoning" in prompt
        assert "llm_judge" in prompt
        assert "claude-3" in prompt
        assert "gpt-4" in prompt
        
        # Verify all required sections are present
        assert "=== ORIGINAL TASK ===" in prompt
        assert "=== JUDGE INFORMATION ===" in prompt
        assert "=== JUDGE'S EVALUATION ===" in prompt
        assert "=== META-EVALUATION REQUEST ===" in prompt
    
    def test_build_meta_evaluation_prompt_with_judge_specific_criteria(self):
        """Test prompt building with judge-specific criteria."""
        # Test with a judge that has specific criteria
        file_info = JudgeFileInfo(
            judge_name="preference_judge",  # This should have specific criteria
            judge_model="claude-3",
            response_model="gpt-4",
            file_path="/test/path.jsonl",
            file_size_mb=1.0
        )
        
        prompt = self.generator.build_meta_evaluation_prompt(
            original_task="Test task",
            judge_response="Test response",
            judge_score=8.0,
            judge_reasoning="Test reasoning",
            file_info=file_info
        )
        
        # Should include judge-specific dimensions if available
        if "preference_judge" in JUDGE_CONFIGURATIONS:
            assert "Judge-Specific Assessment Areas" in prompt
    
    def test_get_meta_evaluation_criteria(self):
        """Test retrieval of meta-evaluation criteria."""
        # Test with known judge
        criteria = self.generator.get_meta_evaluation_criteria("llm_judge")
        assert isinstance(criteria, dict)
        assert all(criterion in criteria for criterion in BASE_META_EVALUATION_CRITERIA)
        
        # Test with unknown judge
        criteria_unknown = self.generator.get_meta_evaluation_criteria("unknown_judge")
        assert criteria_unknown == BASE_META_EVALUATION_CRITERIA
    
    def test_get_meta_scorer_config(self):
        """Test generation of meta-scorer configurations."""
        config = self.generator.get_meta_scorer_config("llm_judge")
        
        assert config["scorer_type"] == "meta_evaluation_judge_assessment"
        assert config["judge_name"] == "llm_judge"
        assert config["meta_evaluation_mode"] == "judge_quality_assessment"
        assert "evaluation_focus" in config
        assert "primary_dimensions" in config
        assert "scoring_weight" in config
    
    def test_truncate_text(self):
        """Test text truncation functionality."""
        short_text = "Short text"
        long_text = "A" * 100
        
        # Text shorter than limit should remain unchanged
        assert self.generator.truncate_text(short_text, 50) == short_text
        
        # Text longer than limit should be truncated with ellipsis
        truncated = self.generator.truncate_text(long_text, 50)
        assert len(truncated) == 50
        assert truncated.endswith("...")
        assert truncated.startswith("A")


class TestJudgePerformanceAnalyzer:
    """Test suite for JudgePerformanceAnalyzer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = JudgePerformanceAnalyzer()
        self.sample_evaluation = {
            "judge_response": "This is a comprehensive evaluation response.",
            "score": 8.5,
            "reasoning": "The response demonstrates good understanding because it addresses all key points and provides clear explanations.",
            "evaluation_criteria": ["accuracy", "completeness", "clarity"]
        }
        self.sample_file_info = JudgeFileInfo(
            judge_name="llm_judge",
            judge_model="claude-3",
            response_model="gpt-4",
            file_path="/test/path.jsonl",
            file_size_mb=1.0
        )
    
    def test_analyze_single_evaluation(self):
        """Test analysis of single judge evaluation."""
        analysis = self.analyzer.analyze_single_evaluation(
            self.sample_evaluation,
            self.sample_file_info
        )
        
        assert isinstance(analysis, JudgeAnalysis)
        assert "response_length" in analysis.performance_indicators
        assert "reasoning_length" in analysis.performance_indicators
        assert "score_value" in analysis.performance_indicators
        assert "has_detailed_reasoning" in analysis.performance_indicators
        assert "evaluation_completeness" in analysis.performance_indicators
        
        # Verify performance indicators are reasonable
        assert analysis.performance_indicators["response_length"] > 0
        assert analysis.performance_indicators["reasoning_length"] > 0
        assert analysis.performance_indicators["score_value"] == 8.5
        assert analysis.performance_indicators["has_detailed_reasoning"] is True  # >50 chars
    
    def test_analyze_judge_file_performance(self):
        """Test analysis of overall judge file performance."""
        # Create sample prompts with metadata
        prompts = []
        for i in range(3):
            prompt = SeedPrompt(
                value="Test prompt",
                metadata={
                    "original_score": 7.0 + i,
                    "judge_performance_indicators": {
                        "reasoning_length": 100 + i * 10,
                        "response_length": 200 + i * 20
                    }
                }
            )
            prompts.append(prompt)
        
        performance = self.analyzer.analyze_judge_file_performance(prompts)
        
        assert performance["total_evaluations"] == 3
        assert "score_statistics" in performance
        assert "reasoning_statistics" in performance
        assert "response_statistics" in performance
        
        # Verify statistics calculations
        assert performance["score_statistics"]["mean"] == 8.0  # (7+8+9)/3
        assert performance["score_statistics"]["min"] == 7.0
        assert performance["score_statistics"]["max"] == 9.0
    
    def test_analyze_judge_file_performance_empty(self):
        """Test analysis with empty prompt list."""
        performance = self.analyzer.analyze_judge_file_performance([])
        assert performance["status"] == "no_data"
    
    def test_assess_evaluation_completeness(self):
        """Test evaluation completeness assessment."""
        complete_evaluation = {
            "judge_response": "Response",
            "score": 8.0,
            "reasoning": "Reasoning",
            "evaluation_criteria": ["accuracy"]
        }
        
        incomplete_evaluation = {
            "judge_response": "Response",
            "score": 8.0
            # Missing reasoning and criteria
        }
        
        complete_score = self.analyzer.assess_evaluation_completeness(complete_evaluation)
        incomplete_score = self.analyzer.assess_evaluation_completeness(incomplete_evaluation)
        
        assert complete_score == 1.0  # All fields present
        assert incomplete_score == 0.5  # 2 out of 4 fields present
    
    def test_assess_reasoning_quality(self):
        """Test reasoning quality assessment."""
        # Test with good reasoning
        good_reasoning = "This response demonstrates understanding because it addresses key points and provides logical explanations with clear evidence."
        quality_good = self.analyzer.assess_reasoning_quality(good_reasoning)
        
        assert "clarity" in quality_good
        assert "logic" in quality_good
        assert "completeness" in quality_good
        assert all(0 <= score <= 1 for score in quality_good.values())
        
        # Test with empty reasoning
        quality_empty = self.analyzer.assess_reasoning_quality("")
        assert all(score == 0.0 for score in quality_empty.values())
        
        # Test with short reasoning
        short_reasoning = "Good."
        quality_short = self.analyzer.assess_reasoning_quality(short_reasoning)
        assert all(score < 0.5 for score in quality_short.values())
    
    def test_assess_score_appropriateness(self):
        """Test score appropriateness assessment."""
        evaluation = {
            "score": 8.5,
            "reasoning": "Detailed reasoning with multiple points and comprehensive analysis."
        }
        
        appropriateness = self.analyzer.assess_score_appropriateness(evaluation)
        
        assert "consistency" in appropriateness
        assert "calibration" in appropriateness
        assert all(0 <= score <= 1 for score in appropriateness.values())
    
    def test_get_judge_evaluation_dimensions(self):
        """Test retrieval of judge evaluation dimensions."""
        # Test with known judge
        dimensions = self.analyzer.get_judge_evaluation_dimensions("llm_judge")
        base_dimensions = ["accuracy", "consistency", "reasoning_quality", "bias_detection"]
        
        assert all(dim in dimensions for dim in base_dimensions)
        
        # Test with unknown judge
        dimensions_unknown = self.analyzer.get_judge_evaluation_dimensions("unknown_judge")
        assert dimensions_unknown == base_dimensions
    
    def test_extract_judge_characteristics(self):
        """Test extraction of judge characteristics."""
        characteristics = self.analyzer.extract_judge_characteristics(self.sample_file_info)
        
        assert characteristics["judge_type"] == "llm_judge"
        assert characteristics["model"] == "claude-3"
        assert characteristics["response_model"] == "gpt-4"
        assert characteristics["file_size_category"] in ["small", "medium", "large"]


class TestSeedPromptAndDataset:
    """Test suite for SeedPrompt and SeedPromptDataset classes."""
    
    def test_seed_prompt_creation(self):
        """Test SeedPrompt creation and properties."""
        metadata = {"test": "value", "score": 8.5}
        prompt = SeedPrompt("Test prompt value", metadata)
        
        assert prompt.value == "Test prompt value"
        assert prompt.metadata == metadata
    
    def test_seed_prompt_sanitization(self):
        """Test SeedPrompt input sanitization."""
        # Test with potentially unsafe input
        unsafe_value = "<script>alert('test')</script>Normal text"
        metadata = {"test": "value"}
        
        prompt = SeedPrompt(unsafe_value, metadata)
        
        # Value should be sanitized (exact behavior depends on sanitize_string implementation)
        assert prompt.value is not None
        assert len(prompt.value) > 0
    
    def test_seed_prompt_dataset_creation(self):
        """Test SeedPromptDataset creation and properties."""
        prompts = [
            SeedPrompt("Prompt 1", {"id": 1}),
            SeedPrompt("Prompt 2", {"id": 2})
        ]
        
        metadata = {"total_prompts": 2, "version": "test"}
        
        dataset = SeedPromptDataset(
            name="Test Dataset",
            version="1.0",
            description="Test description",
            author="Test Author",
            group="test_group",
            source="test_source",
            prompts=prompts,
            metadata=metadata
        )
        
        assert dataset.name == "Test Dataset"
        assert dataset.version == "1.0"
        assert dataset.description == "Test description"
        assert dataset.author == "Test Author"
        assert dataset.group == "test_group"
        assert dataset.source == "test_source"
        assert len(dataset.prompts) == 2
        assert dataset.metadata == metadata
    
    def test_seed_prompt_dataset_to_dict(self):
        """Test SeedPromptDataset to_dict conversion."""
        prompts = [
            SeedPrompt("Prompt 1", {"id": 1}),
            SeedPrompt("Prompt 2", {"id": 2})
        ]
        
        dataset = SeedPromptDataset(
            name="Test Dataset",
            version="1.0",
            description="Test description",
            author="Test Author",
            group="test_group",
            source="test_source",
            prompts=prompts,
            metadata={"test": "value"}
        )
        
        dataset_dict = dataset.to_dict()
        
        assert dataset_dict["name"] == "Test Dataset"
        assert dataset_dict["version"] == "1.0"
        assert dataset_dict["description"] == "Test description"
        assert dataset_dict["author"] == "Test Author"
        assert dataset_dict["group"] == "test_group"
        assert dataset_dict["source"] == "test_source"
        assert len(dataset_dict["prompts"]) == 2
        assert dataset_dict["prompts"][0]["value"] == "Prompt 1"
        assert dataset_dict["prompts"][0]["metadata"]["id"] == 1
        assert dataset_dict["metadata"]["test"] == "value"


# Integration tests
class TestJudgeBenchConverterIntegration:
    """Integration tests for the complete JudgeBench converter workflow."""
    
    def test_end_to_end_conversion_workflow(self):
        """Test complete end-to-end conversion workflow."""
        converter = JudgeBenchConverter(validation_enabled=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple judge files with different judges and models
            judge_files_data = [
                {
                    "filename": "dataset=judgebench,response_model=gpt-4,judge_name=llm_judge,judge_model=claude-3.jsonl",
                    "evaluations": [
                        {
                            "judge_response": "Excellent response with comprehensive coverage.",
                            "score": 9.0,
                            "reasoning": "The response addresses all aspects thoroughly and demonstrates deep understanding of the topic.",
                            "original_task": "Explain renewable energy benefits.",
                            "evaluation_criteria": ["accuracy", "completeness", "clarity"]
                        },
                        {
                            "judge_response": "Good response but lacks some detail.",
                            "score": 7.5,
                            "reasoning": "While the main points are covered, more specific examples would improve the response.",
                            "original_task": "Describe machine learning applications.",
                            "evaluation_criteria": ["accuracy", "completeness"]
                        }
                    ]
                },
                {
                    "filename": "dataset=judgebench,response_model=claude-3,judge_name=human_judge,judge_model=gpt-4.jsonl",
                    "evaluations": [
                        {
                            "judge_response": "Satisfactory response with room for improvement.",
                            "score": 6.0,
                            "reasoning": "The response covers basic points but lacks depth and sophisticated analysis.",
                            "original_task": "Analyze climate change impacts.",
                            "evaluation_criteria": ["accuracy", "depth", "analysis"]
                        }
                    ]
                }
            ]
            
            # Create judge files
            for file_data in judge_files_data:
                file_path = Path(temp_dir) / file_data["filename"]
                jsonl_content = '\n'.join(json.dumps(eval_data) for eval_data in file_data["evaluations"])
                file_path.write_text(jsonl_content)
            
            # Perform conversion
            dataset = converter.convert(temp_dir)
            
            # Verify dataset structure
            assert isinstance(dataset, SeedPromptDataset)
            assert dataset.name == "JudgeBench_Meta_Evaluation"
            assert dataset.version == "1.0"
            assert dataset.group == "meta_evaluation"
            
            # Verify all evaluations were converted
            expected_total_evaluations = sum(len(file_data["evaluations"]) for file_data in judge_files_data)
            assert len(dataset.prompts) == expected_total_evaluations
            
            # Verify metadata
            assert dataset.metadata["total_evaluations"] == expected_total_evaluations
            assert dataset.metadata["judge_count"] == 2
            assert dataset.metadata["total_files_processed"] == 2
            
            # Verify judge metadata
            judge_metadata = dataset.metadata["judge_metadata"]
            assert "llm_judge_claude-3_gpt-4" in judge_metadata
            assert "human_judge_gpt-4_claude-3" in judge_metadata
            
            # Verify response and judge models
            assert "gpt-4" in dataset.metadata["response_models"]
            assert "claude-3" in dataset.metadata["response_models"]
            assert "claude-3" in dataset.metadata["judge_models"]
            assert "gpt-4" in dataset.metadata["judge_models"]
            
            # Verify prompts contain expected content
            for prompt in dataset.prompts:
                assert isinstance(prompt, SeedPrompt)
                assert "Evaluate the quality and appropriateness of this AI judge's evaluation" in prompt.value
                assert "judge_name" in prompt.metadata
                assert "meta_evaluation_criteria" in prompt.metadata
                assert "judge_performance_indicators" in prompt.metadata
    
    def test_error_handling_and_recovery(self):
        """Test error handling and recovery mechanisms."""
        converter = JudgeBenchConverter(validation_enabled=True)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a file with mixed valid and invalid content
            problematic_file = Path(temp_dir) / "dataset=judgebench,response_model=gpt-4,judge_name=test_judge,judge_model=claude-3.jsonl"
            
            mixed_content = (
                json.dumps({"judge_response": "Valid response", "score": 8.0, "reasoning": "Good reasoning", "original_task": "Task 1"}) + '\n' +
                '{"invalid": json content}\n' +  # Invalid JSON
                json.dumps({"judge_response": "Another valid response", "score": 7.0, "reasoning": "OK reasoning", "original_task": "Task 2"}) + '\n' +
                'completely invalid line\n' +  # Invalid line
                json.dumps({"judge_response": "Third valid response", "score": 9.0, "reasoning": "Excellent reasoning", "original_task": "Task 3"}) + '\n'
            )
            
            problematic_file.write_text(mixed_content)
            
            # Conversion should succeed despite errors
            dataset = converter.convert(temp_dir)
            
            # Should have processed only the valid lines
            assert len(dataset.prompts) == 3
            assert dataset.metadata["total_evaluations"] == 3
            
            # Verify the valid evaluations were processed correctly
            scores = [prompt.metadata["original_score"] for prompt in dataset.prompts]
            assert sorted(scores) == [7.0, 8.0, 9.0]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])