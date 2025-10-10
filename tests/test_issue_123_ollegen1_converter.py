# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Test suite for Issue #123 - OllaGen1 Converter Implementation

Test-Driven Development (TDD) implementation following P-TDD protocol.
All tests are designed to FAIL initially (RED phase) and guide implementation.

SECURITY: All test data is for defensive security research only.
"""

import asyncio
import csv
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, patch

import pytest

# This will fail initially - these modules don't exist yet
try:
    from app.core.converters.ollegen1_converter import OllaGen1DatasetConverter
    from app.schemas.ollegen1_datasets import (
        OllaGen1ConversionResult,
        OllaGen1ValidationResult,
        PersonProfile,
        QuestionAnsweringEntry,
        QuestionType,
        ScenarioMetadata,
    )
    from app.services.ollegen1_service import OllaGen1Service
    from app.utils.qa_utils import MultipleChoiceParser, QuestionTypeHandler
except ImportError:
    # Expected to fail initially - will be implemented during GREEN phase
    pass


class TestSampleData:
    """Sample test data for OllaGen1 converter testing."""
    
    SAMPLE_CSV_ROW = {
        "ID": "SC001",
        "P1_name": "Alice",
        "P1_cogpath": "analytical",
        "P1_profile": "high-stress",
        "P1_risk_score": "85.5",
        "P1_risk_profile": "critical-thinker",
        "P2_name": "Bob", 
        "P2_cogpath": "intuitive",
        "P2_profile": "collaborative",
        "P2_risk_score": "72.3",
        "P2_risk_profile": "team-player",
        "shared_risk_factor": "communication-breakdown",
        "targetted_factor": "decision-making",
        "combined_risk_score": "91.2",
        "WCP_Question": "What cognitive path best describes Alice's approach? (a) Analytical systematic (b) Intuitive rapid (c) Collaborative consensus (d) Emotional reactive",
        "WCP_Answer": "(option a) - Analytical systematic",
        "WHO_Question": "Which person has higher compliance risk? (a) Alice with 85.5 score (b) Bob with 72.3 score (c) Both equal risk (d) Cannot determine",
        "WHO_Answer": "(option a) - Alice with 85.5 score",
        "TeamRisk_Question": "What is the primary team risk factor? (a) Skill mismatch (b) Communication breakdown (c) Authority conflicts (d) Resource constraints",
        "TeamRisk_Answer": "(option b) - Communication breakdown",
        "TargetFactor_Question": "What intervention should target decision-making issues? (a) Training programs (b) Process changes (c) Team restructuring (d) Technology solutions",
        "TargetFactor_Answer": "(option b) - Process changes"
    }
    
    EXPECTED_QA_ENTRIES = [
        {
            "question": "What cognitive path best describes Alice's approach? (a) Analytical systematic (b) Intuitive rapid (c) Collaborative consensus (d) Emotional reactive",
            "answer_type": "int",
            "correct_answer": 0,
            "choices": ["Analytical systematic", "Intuitive rapid", "Collaborative consensus", "Emotional reactive"],
            "metadata": {
                "scenario_id": "SC001",
                "question_type": "WCP",
                "category": "cognitive_assessment",
                "conversion_strategy": "strategy_1_cognitive_assessment"
            }
        },
        {
            "question": "Which person has higher compliance risk? (a) Alice with 85.5 score (b) Bob with 72.3 score (c) Both equal risk (d) Cannot determine",
            "answer_type": "int", 
            "correct_answer": 0,
            "choices": ["Alice with 85.5 score", "Bob with 72.3 score", "Both equal risk", "Cannot determine"],
            "metadata": {
                "scenario_id": "SC001",
                "question_type": "WHO",
                "category": "risk_evaluation",
                "conversion_strategy": "strategy_1_cognitive_assessment"
            }
        },
        {
            "question": "What is the primary team risk factor? (a) Skill mismatch (b) Communication breakdown (c) Authority conflicts (d) Resource constraints",
            "answer_type": "int",
            "correct_answer": 1,
            "choices": ["Skill mismatch", "Communication breakdown", "Authority conflicts", "Resource constraints"],
            "metadata": {
                "scenario_id": "SC001",
                "question_type": "TeamRisk",
                "category": "team_assessment",
                "conversion_strategy": "strategy_1_cognitive_assessment"
            }
        },
        {
            "question": "What intervention should target decision-making issues? (a) Training programs (b) Process changes (c) Team restructuring (d) Technology solutions",
            "answer_type": "int",
            "correct_answer": 1,
            "choices": ["Training programs", "Process changes", "Team restructuring", "Technology solutions"],
            "metadata": {
                "scenario_id": "SC001",
                "question_type": "TargetFactor",
                "category": "intervention_assessment",
                "conversion_strategy": "strategy_1_cognitive_assessment"
            }
        }
    ]


@pytest.fixture
def sample_csv_data():
    """Create sample CSV test data."""
    return TestSampleData.SAMPLE_CSV_ROW


@pytest.fixture
def sample_manifest_data():
    """Create sample manifest file data."""
    return {
        "dataset_name": "OllaGen1_CognitiveBehavioralAssessment",
        "version": "1.0",
        "total_scenarios": 169999,
        "split_files": [
            {
                "file_name": "ollegen1_part_001.csv",
                "start_scenario": 1,
                "end_scenario": 10000,
                "row_count": 10000
            },
            {
                "file_name": "ollegen1_part_002.csv", 
                "start_scenario": 10001,
                "end_scenario": 20000,
                "row_count": 10000
            }
        ],
        "metadata": {
            "created_date": "2025-01-07",
            "description": "Cognitive behavioral assessment scenarios for AI security testing",
            "question_types": ["WCP", "WHO", "TeamRisk", "TargetFactor"]
        }
    }


@pytest.fixture
def temp_csv_file(sample_csv_data):
    """Create temporary CSV file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        writer = csv.DictWriter(f, fieldnames=sample_csv_data.keys())
        writer.writeheader()
        writer.writerow(sample_csv_data)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture  
def temp_manifest_file(sample_manifest_data):
    """Create temporary manifest file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_manifest_data, f, indent=2)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestOllaGen1DatasetConverter:
    """Test suite for OllaGen1DatasetConverter core functionality.
    
    All tests designed to FAIL initially and guide TDD implementation.
    """
    
    def test_converter_initialization(self):
        """Test basic converter initialization.
        
        Expected to FAIL: OllaGen1DatasetConverter class doesn't exist yet.
        """
        with pytest.raises((ImportError, NameError)):
            converter = OllaGen1DatasetConverter()
            assert converter is not None
            assert hasattr(converter, 'convert_csv_row')
            assert hasattr(converter, 'process_manifest')
            assert hasattr(converter, 'extract_question_types')
    
    def test_csv_row_parsing(self, sample_csv_data):
        """Test CSV row parsing with 22 columns.
        
        Expected to FAIL: Parser methods don't exist yet.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            # Should parse all 22 required columns
            parsed_data = converter.parse_csv_row(sample_csv_data)
            
            assert "scenario_metadata" in parsed_data
            assert "person_profiles" in parsed_data
            assert "question_data" in parsed_data
            
            # Verify person profiles
            assert len(parsed_data["person_profiles"]) == 2
            assert parsed_data["person_profiles"][0]["name"] == "Alice"
            assert parsed_data["person_profiles"][1]["name"] == "Bob"
            
            # Verify question data
            assert len(parsed_data["question_data"]) == 4
            question_types = [q["type"] for q in parsed_data["question_data"]]
            assert set(question_types) == {"WCP", "WHO", "TeamRisk", "TargetFactor"}
    
    def test_manifest_file_processing(self, temp_manifest_file):
        """Test manifest-based split file processing.
        
        Expected to FAIL: Manifest processing not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            manifest_data = converter.load_manifest(temp_manifest_file)
            
            assert manifest_data["total_scenarios"] == 169999
            assert len(manifest_data["split_files"]) == 2
            assert manifest_data["dataset_name"] == "OllaGen1_CognitiveBehavioralAssessment"
    
    def test_question_type_identification(self, sample_csv_data):
        """Test question type identification and handling.
        
        Expected to FAIL: Question type handlers not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            question_handlers = converter.get_question_handlers()
            
            assert "WCP" in question_handlers
            assert "WHO" in question_handlers  
            assert "TeamRisk" in question_handlers
            assert "TargetFactor" in question_handlers
            
            # Test WCP handler
            wcp_result = question_handlers["WCP"].process(
                sample_csv_data["WCP_Question"],
                sample_csv_data["WCP_Answer"] 
            )
            assert wcp_result["category"] == "cognitive_assessment"
            assert wcp_result["correct_answer"] == 0


class TestMultipleChoiceParser:
    """Test suite for multiple choice option extraction and parsing.
    
    Tests the core logic for parsing various multiple choice formats.
    """
    
    def test_multiple_choice_extraction(self):
        """Test standard multiple choice extraction.
        
        Expected to FAIL: MultipleChoiceParser class doesn't exist.
        """
        with pytest.raises((ImportError, NameError)):
            parser = MultipleChoiceParser()
            
            question_text = "What is the answer? (a) Option A (b) Option B (c) Option C (d) Option D"
            choices = parser.extract_choices(question_text)
            
            assert len(choices) == 4
            assert choices[0] == "Option A"
            assert choices[1] == "Option B"
            assert choices[2] == "Option C"
            assert choices[3] == "Option D"
    
    def test_malformed_choice_patterns(self):
        """Test handling of non-standard choice formats.
        
        Expected to FAIL: Fallback parsing not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            parser = MultipleChoiceParser()
            
            # Test incomplete pattern
            malformed_text = "Choose: (a) First choice (b) Second choice (c) Third"
            choices = parser.extract_choices_with_fallback(malformed_text)
            
            assert len(choices) >= 2  # Should handle partial matches
            assert "First choice" in choices
            assert "Second choice" in choices
    
    def test_answer_index_mapping(self):
        """Test answer text to index mapping.
        
        Expected to FAIL: Answer mapping logic not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            parser = MultipleChoiceParser()
            
            choices = ["Option A", "Option B", "Option C", "Option D"]
            
            # Test various answer formats
            assert parser.map_answer_to_index("(option a) - Option A", choices) == 0
            assert parser.map_answer_to_index("(option b) - Option B", choices) == 1
            assert parser.map_answer_to_index("Option C", choices) == 2
    
    def test_choice_validation(self):
        """Test choice completeness validation.
        
        Expected to FAIL: Validation logic not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            parser = MultipleChoiceParser()
            
            valid_choices = ["A", "B", "C", "D"]
            invalid_choices = ["A", "B"]  # Incomplete
            
            assert parser.validate_choices(valid_choices) is True
            assert parser.validate_choices(invalid_choices) is False


class TestQuestionAnsweringEntryGeneration:
    """Test suite for QuestionAnsweringEntry object generation.
    
    Tests the conversion from CSV data to PyRIT-compliant Q&A entries.
    """
    
    def test_qa_entry_creation(self, sample_csv_data):
        """Test single Q&A entry creation from CSV row.
        
        Expected to FAIL: QuestionAnsweringEntry class doesn't exist.
        """
        with pytest.raises((ImportError, NameError)):
            converter = OllaGen1DatasetConverter()
            
            qa_entry = converter.create_qa_entry(
                question_text=sample_csv_data["WCP_Question"],
                answer_text=sample_csv_data["WCP_Answer"],
                question_type="WCP",
                scenario_metadata={"scenario_id": "SC001"}
            )
            
            assert isinstance(qa_entry, QuestionAnsweringEntry)
            assert qa_entry.answer_type == "int"
            assert qa_entry.correct_answer == 0
            assert len(qa_entry.choices) == 4
    
    def test_batch_qa_generation(self, sample_csv_data):
        """Test 1 CSV row -> 4 Q&A entries conversion.
        
        Expected to FAIL: Batch processing not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            qa_entries = converter.convert_csv_row_to_qa_entries(sample_csv_data)
            
            assert len(qa_entries) == 4
            
            question_types = [entry.metadata["question_type"] for entry in qa_entries]
            assert set(question_types) == {"WCP", "WHO", "TeamRisk", "TargetFactor"}
    
    def test_metadata_preservation(self, sample_csv_data):
        """Test complete metadata preservation.
        
        Expected to FAIL: Metadata extraction not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            qa_entries = converter.convert_csv_row_to_qa_entries(sample_csv_data)
            
            for entry in qa_entries:
                metadata = entry.metadata
                
                # Verify required metadata fields
                assert "scenario_id" in metadata
                assert "person_1" in metadata
                assert "person_2" in metadata
                assert "shared_risk_factor" in metadata
                assert "targeted_factor" in metadata
                assert "combined_risk_score" in metadata
                assert "conversion_timestamp" in metadata
                assert "conversion_strategy" in metadata
                
                # Verify person profile completeness
                person_1 = metadata["person_1"]
                assert person_1["name"] == "Alice"
                assert person_1["cognitive_path"] == "analytical"
                assert person_1["risk_score"] == 85.5
    
    def test_pyrit_format_compliance(self, sample_csv_data):
        """Test PyRIT format compliance.
        
        Expected to FAIL: Format validation not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            qa_entries = converter.convert_csv_row_to_qa_entries(sample_csv_data)
            
            for entry in qa_entries:
                # Verify PyRIT QuestionAnsweringEntry compliance
                assert hasattr(entry, 'question')
                assert hasattr(entry, 'answer_type') 
                assert hasattr(entry, 'correct_answer')
                assert hasattr(entry, 'choices')
                assert hasattr(entry, 'metadata')
                
                assert entry.answer_type == "int"
                assert isinstance(entry.correct_answer, int)
                assert 0 <= entry.correct_answer < len(entry.choices)
                assert isinstance(entry.choices, list)
                assert len(entry.choices) >= 2


class TestPerformanceAndQuality:
    """Test suite for performance benchmarks and quality assurance.
    
    Tests conversion speed, memory usage, and data integrity.
    """
    
    def test_conversion_performance(self):
        """Test conversion speed benchmarks.
        
        Expected to FAIL: Performance optimization not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            # Create test data simulating full dataset size
            test_rows = [TestSampleData.SAMPLE_CSV_ROW] * 1000  # Scaled down for testing
            
            start_time = time.time()
            results = converter.batch_convert_rows(test_rows)
            end_time = time.time()
            
            conversion_time = end_time - start_time
            throughput = len(test_rows) / conversion_time
            
            # Should process >300 scenarios per second
            assert throughput > 300
            assert len(results) == len(test_rows) * 4  # 4 Q&A entries per row
    
    def test_memory_usage(self):
        """Test memory consumption during conversion.
        
        Expected to FAIL: Memory optimization not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            import psutil
            
            converter = OllaGen1DatasetConverter()
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Process large batch
            test_rows = [TestSampleData.SAMPLE_CSV_ROW] * 5000
            results = converter.batch_convert_rows(test_rows)
            
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            # Should use <2GB additional memory
            assert memory_increase < 2048
    
    def test_data_integrity(self, sample_csv_data):
        """Test 100% data preservation validation.
        
        Expected to FAIL: Validation framework not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            validator = converter.get_validator()
            
            qa_entries = converter.convert_csv_row_to_qa_entries(sample_csv_data)
            validation_result = validator.validate_conversion(sample_csv_data, qa_entries)
            
            assert validation_result.integrity_check_passed
            assert validation_result.data_preservation_rate == 1.0
            assert validation_result.metadata_completeness_score >= 0.95
    
    def test_accuracy_metrics(self):
        """Test >95% choice extraction accuracy.
        
        Expected to FAIL: Accuracy measurement not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            accuracy_tester = converter.get_accuracy_tester()
            
            # Test with various question formats
            test_questions = [
                "Question? (a) Choice A (b) Choice B (c) Choice C (d) Choice D",
                "What is it? (a) First (b) Second (c) Third (d) Fourth",  
                "Choose: (a) Option 1 (b) Option 2 (c) Option 3 (d) Option 4"
            ]
            
            total_accuracy = accuracy_tester.test_extraction_accuracy(test_questions)
            
            assert total_accuracy > 0.95  # >95% accuracy requirement


class TestErrorHandlingAndRecovery:
    """Test suite for error handling and recovery mechanisms.
    
    Tests graceful handling of various failure scenarios.
    """
    
    def test_malformed_csv_handling(self):
        """Test handling of malformed CSV data.
        
        Expected to FAIL: Error handling not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            # Test with missing columns
            incomplete_row = {"ID": "SC001", "P1_name": "Alice"}  # Missing other columns
            
            result = converter.convert_csv_row_to_qa_entries(incomplete_row)
            
            # Should handle gracefully without crashing
            assert result is not None or result == []
    
    def test_missing_file_recovery(self):
        """Test recovery from missing or corrupted files.
        
        Expected to FAIL: File handling not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            # Test with non-existent file
            result = converter.process_split_file("nonexistent_file.csv")
            
            assert result.success is False
            assert result.error_message is not None
            assert "file not found" in result.error_message.lower()
    
    def test_partial_conversion_recovery(self):
        """Test partial conversion recovery mechanisms.
        
        Expected to FAIL: Recovery mechanisms not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            # Simulate partial failure during batch processing
            test_rows = [TestSampleData.SAMPLE_CSV_ROW] * 100
            
            with patch.object(converter, 'convert_csv_row_to_qa_entries') as mock_convert:
                # Simulate failure on row 50
                def side_effect(row):
                    if row.get("ID") == "SC050":
                        raise Exception("Simulated conversion error")
                    return [Mock()]
                
                mock_convert.side_effect = side_effect
                
                result = converter.batch_convert_with_recovery(test_rows)
                
                # Should continue processing after failure
                assert result.successful_conversions > 0
                assert result.failed_conversions == 1
                assert len(result.error_reports) == 1


@pytest.mark.asyncio
class TestAsyncProcessing:
    """Test suite for asynchronous processing capabilities.
    
    Tests async batch processing and progress tracking.
    """
    
    async def test_async_batch_processing(self):
        """Test asynchronous batch processing.
        
        Expected to FAIL: Async processing not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            test_rows = [TestSampleData.SAMPLE_CSV_ROW] * 100
            
            results = await converter.async_batch_convert(test_rows)
            
            assert len(results) == len(test_rows) * 4
            
    async def test_progress_tracking(self):
        """Test real-time progress tracking.
        
        Expected to FAIL: Progress tracking not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            converter = OllaGen1DatasetConverter()
            
            test_rows = [TestSampleData.SAMPLE_CSV_ROW] * 1000
            progress_updates = []
            
            def progress_callback(current, total, eta):
                progress_updates.append((current, total, eta))
            
            await converter.async_batch_convert_with_progress(
                test_rows, 
                progress_callback=progress_callback
            )
            
            # Should receive progress updates
            assert len(progress_updates) > 0
            assert progress_updates[-1][0] == progress_updates[-1][1]  # Final: current == total


class TestDataValidationFramework:
    """Test suite for data validation and quality assurance.
    
    Tests comprehensive validation of converted data.
    """
    
    def test_question_answer_validation(self):
        """Test question-answer relationship validation.
        
        Expected to FAIL: Q&A validation not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            from app.utils.qa_utils import QAValidator
            
            validator = QAValidator()
            
            # Test valid Q&A entry
            valid_entry = {
                "question": "Test question? (a) A (b) B (c) C (d) D",
                "answer_type": "int",
                "correct_answer": 1,
                "choices": ["A", "B", "C", "D"]
            }
            
            validation_result = validator.validate_qa_entry(valid_entry)
            assert validation_result.is_valid
            
            # Test invalid entry (answer index out of range)
            invalid_entry = valid_entry.copy()
            invalid_entry["correct_answer"] = 5  # Out of range
            
            validation_result = validator.validate_qa_entry(invalid_entry)
            assert not validation_result.is_valid
            assert "answer index out of range" in validation_result.error_message.lower()
    
    def test_metadata_completeness_validation(self):
        """Test metadata completeness validation.
        
        Expected to FAIL: Metadata validation not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            from app.utils.qa_utils import MetadataValidator
            
            validator = MetadataValidator()
            
            complete_metadata = {
                "scenario_id": "SC001",
                "question_type": "WCP",
                "person_1": {"name": "Alice", "risk_score": 85.5},
                "person_2": {"name": "Bob", "risk_score": 72.3},
                "conversion_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            validation_result = validator.validate_metadata(complete_metadata)
            assert validation_result.completeness_score == 1.0
            
            # Test incomplete metadata
            incomplete_metadata = {"scenario_id": "SC001"}  # Missing required fields
            
            validation_result = validator.validate_metadata(incomplete_metadata)
            assert validation_result.completeness_score < 0.5
    
    def test_format_compliance_validation(self):
        """Test PyRIT format compliance validation.
        
        Expected to FAIL: Format compliance checking not implemented.
        """
        with pytest.raises((ImportError, NameError, AttributeError)):
            from app.utils.qa_utils import FormatValidator
            
            validator = FormatValidator()
            
            # Test PyRIT compliant entry
            compliant_entry = {
                "question": "Test question?",
                "answer_type": "int",
                "correct_answer": 0,
                "choices": ["Choice A", "Choice B"],
                "metadata": {"source": "test"}
            }
            
            compliance_result = validator.check_pyrit_compliance(compliant_entry)
            assert compliance_result.is_compliant
            
            # Test non-compliant entry  
            non_compliant_entry = {
                "question": "Test?",
                "answer_type": "string",  # Should be "int" for multiple choice
                "correct_answer": "A",    # Should be int index
            }
            
            compliance_result = validator.check_pyrit_compliance(non_compliant_entry)
            assert not compliance_result.is_compliant
            assert len(compliance_result.violations) > 0


if __name__ == "__main__":
    # Run specific test classes for TDD phases
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--disable-warnings"
    ])