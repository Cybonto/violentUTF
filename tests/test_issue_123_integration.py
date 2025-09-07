# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Integration tests for Issue #123 - OllaGen1 Converter Implementation

Tests the complete end-to-end conversion pipeline from CSV data to
PyRIT-compliant QuestionAnsweringDataset format.

SECURITY: All test data is for defensive security research only.
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Dict, List

import pytest

from app.core.converters.ollegen1_converter import OllaGen1DatasetConverter
from app.schemas.ollegen1_datasets import (
    OllaGen1ConversionConfig,
    OllaGen1ConversionRequest,
    PersonProfile,
    QuestionType,
    ScenarioMetadata,
)
from app.services.ollegen1_service import OllaGen1Service
from app.utils.qa_utils import MultipleChoiceParser, QAValidator


class TestOllaGen1Integration:
    """Integration tests for complete OllaGen1 conversion pipeline."""
    
    @pytest.fixture
    def sample_csv_rows(self):
        """Create sample CSV data for testing."""
        return [
            {
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
            },
            {
                "ID": "SC002",
                "P1_name": "Charlie",
                "P1_cogpath": "emotional",
                "P1_profile": "low-stress",
                "P1_risk_score": "45.2",
                "P1_risk_profile": "adaptable",
                "P2_name": "Diana",
                "P2_cogpath": "logical",
                "P2_profile": "independent", 
                "P2_risk_score": "88.7",
                "P2_risk_profile": "perfectionist",
                "shared_risk_factor": "resource-conflicts",
                "targetted_factor": "communication",
                "combined_risk_score": "76.9",
                "WCP_Question": "What describes Charlie's cognitive approach? (a) Emotional intuitive (b) Logical systematic (c) Adaptable flexible (d) Independent decisive",
                "WCP_Answer": "(option a) - Emotional intuitive",
                "WHO_Question": "Who shows higher compliance risk patterns? (a) Charlie at 45.2 (b) Diana at 88.7 (c) Equal risk levels (d) Insufficient data",
                "WHO_Answer": "(option b) - Diana at 88.7",
                "TeamRisk_Question": "What team risk needs immediate attention? (a) Resource conflicts (b) Skill gaps (c) Communication issues (d) Leadership problems", 
                "TeamRisk_Answer": "(option a) - Resource conflicts",
                "TargetFactor_Question": "Which intervention targets communication effectively? (a) Policy updates (b) Training sessions (c) System improvements (d) Workflow changes",
                "TargetFactor_Answer": "(option b) - Training sessions"
            }
        ]
    
    @pytest.fixture
    def temp_manifest(self):
        """Create temporary manifest file."""
        manifest_data = {
            "dataset_name": "OllaGen1_TestDataset",
            "version": "1.0",
            "total_scenarios": 2,
            "expected_qa_entries": 8,
            "split_files": [
                {
                    "file_name": "test_data.csv",
                    "start_scenario": 1,
                    "end_scenario": 2,
                    "row_count": 2
                }
            ],
            "schema": {
                "required_columns": [
                    "ID", "P1_name", "P1_cogpath", "P1_profile", "P1_risk_score", "P1_risk_profile",
                    "P2_name", "P2_cogpath", "P2_profile", "P2_risk_score", "P2_risk_profile",
                    "shared_risk_factor", "targetted_factor", "combined_risk_score",
                    "WCP_Question", "WCP_Answer", "WHO_Question", "WHO_Answer",
                    "TeamRisk_Question", "TeamRisk_Answer", "TargetFactor_Question", "TargetFactor_Answer"
                ],
                "column_count": 22
            },
            "question_types": {
                "WCP": {"category": "cognitive_assessment"},
                "WHO": {"category": "risk_evaluation"},
                "TeamRisk": {"category": "team_assessment"},
                "TargetFactor": {"category": "intervention_assessment"}
            },
            "metadata": {
                "created_date": "2025-01-07T00:00:00Z",
                "description": "Test dataset for OllaGen1 converter integration testing"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(manifest_data, f, indent=2)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    def test_complete_conversion_pipeline(self, sample_csv_rows, temp_manifest):
        """Test complete conversion pipeline from CSV to QuestionAnswering entries."""
        # Initialize converter
        config = OllaGen1ConversionConfig(
            batch_size=100,
            enable_validation=True,
            enable_progress_tracking=True
        )
        
        converter = OllaGen1DatasetConverter(config)
        
        # Test manifest loading
        manifest_info = converter.load_manifest(temp_manifest)
        assert manifest_info.dataset_name == "OllaGen1_TestDataset"
        assert manifest_info.total_scenarios == 2
        assert manifest_info.expected_qa_entries == 8
        
        # Test CSV row conversion
        all_qa_entries = []
        for row in sample_csv_rows:
            qa_entries = converter.convert_csv_row_to_qa_entries(row)
            all_qa_entries.extend(qa_entries)
        
        # Verify conversion results
        assert len(all_qa_entries) == 8  # 2 rows × 4 questions each
        
        # Group by scenario
        scenario_groups = {}
        for entry in all_qa_entries:
            scenario_id = entry.metadata["scenario_id"]
            if scenario_id not in scenario_groups:
                scenario_groups[scenario_id] = []
            scenario_groups[scenario_id].append(entry)
        
        assert len(scenario_groups) == 2  # SC001 and SC002
        
        # Verify each scenario has 4 questions
        for scenario_id, entries in scenario_groups.items():
            assert len(entries) == 4
            
            # Check question types
            question_types = {entry.metadata["question_type"] for entry in entries}
            assert question_types == {"WCP", "WHO", "TeamRisk", "TargetFactor"}
            
            # Verify PyRIT format compliance
            for entry in entries:
                assert entry.answer_type == "int"
                assert isinstance(entry.correct_answer, int)
                assert 0 <= entry.correct_answer < len(entry.choices)
                assert isinstance(entry.choices, list)
                assert len(entry.choices) >= 2
    
    def test_question_type_specific_processing(self, sample_csv_rows):
        """Test that each question type is processed correctly with proper categories."""
        converter = OllaGen1DatasetConverter()
        
        # Convert first row
        qa_entries = converter.convert_csv_row_to_qa_entries(sample_csv_rows[0])
        
        # Create lookup by question type
        entries_by_type = {entry.metadata["question_type"]: entry for entry in qa_entries}
        
        # Test WCP question
        wcp_entry = entries_by_type["WCP"]
        assert wcp_entry.metadata["category"] == "cognitive_assessment"
        assert "cognitive path" in wcp_entry.question.lower()
        assert wcp_entry.correct_answer == 0  # Should map to option (a)
        assert "Analytical systematic" in wcp_entry.choices
        
        # Test WHO question  
        who_entry = entries_by_type["WHO"]
        assert who_entry.metadata["category"] == "risk_evaluation"
        assert "compliance risk" in who_entry.question.lower()
        assert wcp_entry.correct_answer == 0  # Should map to option (a)
        assert "Alice with 85.5 score" in who_entry.choices
        
        # Test TeamRisk question
        team_entry = entries_by_type["TeamRisk"]
        assert team_entry.metadata["category"] == "team_assessment"
        assert "team risk" in team_entry.question.lower()
        assert team_entry.correct_answer == 1  # Should map to option (b)
        assert "Communication breakdown" in team_entry.choices
        
        # Test TargetFactor question
        target_entry = entries_by_type["TargetFactor"]
        assert target_entry.metadata["category"] == "intervention_assessment"
        assert "intervention" in target_entry.question.lower()
        assert target_entry.correct_answer == 1  # Should map to option (b) 
        assert "Process changes" in target_entry.choices
    
    def test_metadata_preservation_completeness(self, sample_csv_rows):
        """Test that all metadata is preserved correctly in converted entries."""
        converter = OllaGen1DatasetConverter()
        
        qa_entries = converter.convert_csv_row_to_qa_entries(sample_csv_rows[0])
        
        for entry in qa_entries:
            metadata = entry.metadata
            
            # Verify required metadata fields
            required_fields = [
                "scenario_id", "question_type", "category",
                "person_1", "person_2", "shared_risk_factor",
                "targeted_factor", "combined_risk_score",
                "conversion_timestamp", "conversion_strategy"
            ]
            
            for field in required_fields:
                assert field in metadata, f"Missing metadata field: {field}"
            
            # Verify person profiles
            person_1 = metadata["person_1"]
            assert person_1["name"] == "Alice"
            assert person_1["cognitive_path"] == "analytical"
            assert person_1["risk_score"] == 85.5
            
            person_2 = metadata["person_2"]
            assert person_2["name"] == "Bob"
            assert person_2["cognitive_path"] == "intuitive" 
            assert person_2["risk_score"] == 72.3
            
            # Verify scenario data
            assert metadata["scenario_id"] == "SC001"
            assert metadata["shared_risk_factor"] == "communication-breakdown"
            assert metadata["targeted_factor"] == "decision-making"
            assert metadata["combined_risk_score"] == 91.2
            assert metadata["conversion_strategy"] == "strategy_1_cognitive_assessment"
    
    @pytest.mark.asyncio
    async def test_async_batch_processing(self, sample_csv_rows):
        """Test asynchronous batch processing capabilities."""
        converter = OllaGen1DatasetConverter()
        
        # Duplicate sample data to test batch processing
        extended_rows = sample_csv_rows * 10  # 20 rows total
        
        start_time = asyncio.get_event_loop().time()
        qa_entries = await converter.async_batch_convert(extended_rows)
        end_time = asyncio.get_event_loop().time()
        
        # Verify results
        assert len(qa_entries) == 80  # 20 rows × 4 questions each
        
        # Verify processing time is reasonable
        processing_time = end_time - start_time
        assert processing_time < 10  # Should complete in under 10 seconds
        
        # Verify throughput
        throughput = len(extended_rows) / processing_time
        assert throughput > 2  # Should process at least 2 scenarios per second
    
    @pytest.mark.asyncio
    async def test_progress_tracking(self, sample_csv_rows):
        """Test real-time progress tracking during conversion."""
        converter = OllaGen1DatasetConverter()
        
        # Track progress updates
        progress_updates = []
        
        def progress_callback(current, total, eta):
            progress_updates.append({
                "current": current,
                "total": total,
                "eta": eta,
                "progress": current / total if total > 0 else 0
            })
        
        # Run with progress tracking
        extended_rows = sample_csv_rows * 5  # 10 rows
        await converter.async_batch_convert_with_progress(
            extended_rows,
            progress_callback=progress_callback
        )
        
        # Verify progress updates
        assert len(progress_updates) > 0
        
        # Check that progress increases
        progress_values = [update["progress"] for update in progress_updates]
        assert progress_values[-1] == 1.0  # Should reach 100%
        
        # Verify progress is monotonically increasing
        for i in range(1, len(progress_values)):
            assert progress_values[i] >= progress_values[i-1]
    
    def test_validation_framework_integration(self, sample_csv_rows):
        """Test integration with validation framework."""
        converter = OllaGen1DatasetConverter()
        validator = converter.get_validator()
        
        # Convert sample data
        qa_entries = converter.convert_csv_row_to_qa_entries(sample_csv_rows[0])
        
        # Validate each entry
        for entry in qa_entries:
            validation_result = validator.validate_qa_entry(entry.model_dump())
            
            assert validation_result["is_valid"], f"Validation failed: {validation_result.get('errors', [])}"
            assert len(validation_result.get("errors", [])) == 0
            
            # Check warnings (should be minimal)
            warnings = validation_result.get("warnings", [])
            assert len(warnings) <= 1  # Allow minimal warnings
        
        # Test metadata completeness
        for entry in qa_entries:
            metadata_validation = validator.validate_metadata_completeness(entry.metadata)
            assert metadata_validation["completeness_score"] >= 0.95
            assert metadata_validation["is_complete"]
    
    def test_error_recovery_mechanisms(self, sample_csv_rows):
        """Test error recovery and graceful failure handling."""
        converter = OllaGen1DatasetConverter()
        
        # Create problematic data
        bad_rows = sample_csv_rows.copy()
        bad_rows.append({
            "ID": "SC999",
            "P1_name": "",  # Missing required data
            "P1_risk_score": "invalid",  # Invalid numeric data
            # Missing other required fields
        })
        
        # Test batch conversion with recovery
        result = converter.batch_convert_with_recovery(bad_rows)
        
        # Should continue processing despite errors
        assert result.successful_conversions >= 2  # At least the good rows
        assert result.failed_conversions >= 1   # The bad row
        assert result.total_scenarios_processed == len(bad_rows)
        
        # Should have some valid Q&A entries
        assert result.total_qa_entries_generated >= 8  # From the 2 good rows
    
    def test_performance_benchmarks(self, sample_csv_rows):
        """Test performance meets specified benchmarks."""
        converter = OllaGen1DatasetConverter()
        
        # Create larger dataset for performance testing
        large_dataset = sample_csv_rows * 100  # 200 rows
        
        start_time = datetime.now()
        result = converter.batch_convert_with_recovery(large_dataset)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Verify performance benchmarks
        assert result.average_scenarios_per_second > 10  # Should process > 10 scenarios/sec
        assert result.memory_peak_mb < 100  # Should use < 100MB for test data
        assert processing_time < 30  # Should complete in under 30 seconds
        
        # Verify quality metrics
        assert result.quality_summary["success_rate"] > 0.99  # >99% success rate


class TestOllaGen1ServiceIntegration:
    """Integration tests for OllaGen1Service layer."""
    
    @pytest.fixture
    def service(self):
        """Create OllaGen1Service instance."""
        return OllaGen1Service()
    
    def test_temp_conversion_request(self, service):
        """Create temporary conversion request and test service integration."""
        # Create temp manifest inline
        manifest_data = {
            "dataset_name": "OllaGen1_TestDataset",
            "version": "1.0", 
            "total_scenarios": 2,
            "expected_qa_entries": 8,
            "split_files": [
                {"file_name": "test_data.csv", "start_scenario": 1, "end_scenario": 2, "row_count": 2}
            ],
            "schema": {"required_columns": [], "column_count": 22},
            "question_types": {},
            "metadata": {"created_date": "2025-01-07T00:00:00Z"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(manifest_data, f, indent=2)
            temp_manifest_path = f.name
        
        try:
            request = OllaGen1ConversionRequest(
                manifest_file_path=temp_manifest_path,
                output_dataset_name="test_converted_dataset",
                conversion_config=OllaGen1ConversionConfig(
                    batch_size=100,
                    enable_validation=True,
                    enable_progress_tracking=True
                ),
                save_to_memory=True,
                overwrite_existing=True
            )
            
            # Just verify request creation works
            assert request.output_dataset_name == "test_converted_dataset"
            assert request.save_to_memory is True
            
        finally:
            if os.path.exists(temp_manifest_path):
                os.unlink(temp_manifest_path)
    
    def test_service_converter_info(self, service):
        """Test service provides correct converter information."""
        info = service.get_converter_info()
        
        assert info["name"] == "OllaGen1 Converter"
        assert info["version"] == "1.0.0"
        assert "Strategy 1" in info["description"]
        assert "csv" in info["supported_formats"]
        assert info["requires_manifest"] is True
        assert len(info["question_types"]) == 4
        assert "WCP" in info["question_types"]
        
        # Check performance targets
        targets = info["performance_targets"]
        assert targets["max_conversion_time_seconds"] == 600
        assert targets["min_throughput_scenarios_per_second"] == 300
        assert targets["max_memory_usage_gb"] == 2
        assert targets["min_choice_extraction_accuracy"] == 0.95
    
    def test_service_status_tracking(self, service):
        """Test service status tracking capabilities."""
        # Test empty state
        active_conversions = service.list_active_conversions()
        assert isinstance(active_conversions, list)
        assert len(active_conversions) == 0
        
        history = service.get_conversion_history()
        assert isinstance(history, list)
        
        # Test invalid conversion ID
        with pytest.raises(ValueError):
            asyncio.run(service.get_conversion_status("invalid-id"))
    
    def test_service_performance_metrics(self, service):
        """Test service performance metrics tracking."""
        metrics = service.get_performance_metrics()
        
        # Should return valid metrics structure
        assert "total_conversions" in metrics
        assert "successful_conversions" in metrics
        assert "failed_conversions" in metrics
        assert "success_rate" in metrics
        assert "conversion_metrics" in metrics
        
        # Values should be non-negative
        assert metrics["total_conversions"] >= 0
        assert metrics["successful_conversions"] >= 0
        assert metrics["failed_conversions"] >= 0
        assert 0.0 <= metrics["success_rate"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--disable-warnings"])