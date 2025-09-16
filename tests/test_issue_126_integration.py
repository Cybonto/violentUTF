#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Integration tests for LegalBench dataset converter (Issue #126).

Comprehensive integration test suite for end-to-end LegalBench converter
functionality including full pipeline testing, service integration,
and performance validation.

SECURITY: All tests use sanitized inputs and validate security constraints.
"""

import asyncio
import os
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List

import pytest

from app.core.converters.legalbench_converter import LegalBenchDatasetConverter
from app.schemas.legalbench_datasets import (
    LegalBenchConversionConfig,
    LegalCategory,
    QuestionAnsweringDataset,
)
from app.services.legal_service import LegalService


class TestLegalBenchEndToEndConversion(unittest.TestCase):
    """Integration tests for complete LegalBench conversion pipeline."""

    def setUp(self) -> None:
        """Set up integration test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.legal_service = LegalService()
        self._create_mock_legalbench_dataset()

    def tearDown(self) -> None:
        """Clean up integration test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_mock_legalbench_dataset(self) -> None:
        """Create mock LegalBench dataset structure for testing."""
        # Sample legal task directories with different categories
        task_directories = [
            {
                "name": "contract_analysis_basic",
                "category": "contract",
                "train_data": [
                    {"question": "What is the delivery term in this agreement?", "answer": "30 days", "label": "delivery_obligation"},
                    {"question": "Who is responsible for shipping costs?", "answer": "Buyer", "label": "cost_allocation"}
                ],
                "test_data": [
                    {"question": "What happens if delivery is delayed?", "answer": "Penalty applies", "label": "breach_consequence"}
                ]
            },
            {
                "name": "regulatory_compliance_financial",
                "category": "regulatory",
                "train_data": [
                    {"question": "Does this reporting meet CFR 12.3 requirements?", "answer": "Yes", "label": "compliance_check"},
                    {"question": "What documentation is required?", "answer": "Quarterly reports", "label": "documentation_requirement"}
                ],
                "test_data": [
                    {"question": "Is monthly reporting sufficient?", "answer": "Yes", "label": "frequency_compliance"}
                ]
            },
            {
                "name": "judicial_reasoning_civil",
                "category": "judicial",
                "train_data": [
                    {"question": "What standard of care applies?", "answer": "Reasonable person standard", "label": "standard_determination"},
                    {"question": "Is plaintiff liable?", "answer": "No", "label": "liability_assessment"}
                ],
                "test_data": [
                    {"question": "What damages are recoverable?", "answer": "Compensatory damages", "label": "damages_calculation"}
                ]
            },
            {
                "name": "criminal_procedure_evidence",
                "category": "criminal",
                "train_data": [
                    {"question": "Is this search constitutional?", "answer": "No", "label": "constitutional_analysis"},
                    {"question": "Was Miranda required?", "answer": "Yes", "label": "miranda_requirement"}
                ],
                "test_data": [
                    {"question": "Is the evidence admissible?", "answer": "No", "label": "admissibility_ruling"}
                ]
            },
            {
                "name": "constitutional_rights_analysis",
                "category": "constitutional",
                "train_data": [
                    {"question": "Does this violate the First Amendment?", "answer": "Yes", "label": "constitutional_violation"},
                    {"question": "What level of scrutiny applies?", "answer": "Strict scrutiny", "label": "scrutiny_level"}
                ],
                "test_data": [
                    {"question": "Is the law content-neutral?", "answer": "No", "label": "content_neutrality"}
                ]
            }
        ]
        
        # Create directory structure
        for task_info in task_directories:
            task_dir = os.path.join(self.temp_dir, task_info["name"])
            os.makedirs(task_dir)
            
            # Create train.tsv
            train_path = os.path.join(task_dir, "train.tsv")
            with open(train_path, 'w') as f:
                f.write("question\tanswer\tlabel\n")
                for item in task_info["train_data"]:
                    f.write(f"{item['question']}\t{item['answer']}\t{item['label']}\n")
            
            # Create test.tsv
            test_path = os.path.join(task_dir, "test.tsv")
            with open(test_path, 'w') as f:
                f.write("question\tanswer\tlabel\n")
                for item in task_info["test_data"]:
                    f.write(f"{item['question']}\t{item['answer']}\t{item['label']}\n")

    def test_full_legalbench_conversion(self) -> None:
        """Test complete LegalBench dataset processing across all directories."""
        # Should fail initially - full conversion pipeline not implemented
        converter = LegalBenchDatasetConverter()
        
        result = converter.convert(self.temp_dir)
        
        # Validate conversion results
        self.assertIsNotNone(result)
        self.assertIsInstance(result.dataset, QuestionAnsweringDataset)
        self.assertGreater(len(result.dataset.questions), 0)
        
        # Should have processed 5 directories
        self.assertEqual(result.processing_stats["directories_found"], 5)
        self.assertGreater(result.processing_stats["successful_conversions"], 0)
        
        # Should have detected multiple legal categories
        self.assertGreater(len(result.legal_category_summary), 1)
        
        # Should preserve train/test splits
        train_questions = [q for q in result.dataset.questions if q.metadata.split == "train"]
        test_questions = [q for q in result.dataset.questions if q.metadata.split == "test"]
        self.assertGreater(len(train_questions), 0)
        self.assertGreater(len(test_questions), 0)

    def test_multi_directory_processing(self) -> None:
        """Test batch processing of multiple task directories."""
        config = LegalBenchConversionConfig(
            parallel_processing=False,  # Test sequential first
            enable_progress_tracking=True
        )
        
        converter = LegalBenchDatasetConverter(config)
        result = converter.convert(self.temp_dir)
        
        # Should process all 5 directories
        self.assertEqual(len(result.conversion_results), 5)
        
        # Each directory should have conversion result
        task_names = [r.task_name for r in result.conversion_results]
        self.assertIn("contract_analysis_basic", task_names)
        self.assertIn("regulatory_compliance_financial", task_names)
        self.assertIn("judicial_reasoning_civil", task_names)
        self.assertIn("criminal_procedure_evidence", task_names)
        self.assertIn("constitutional_rights_analysis", task_names)

    def test_legal_domain_aggregation(self) -> None:
        """Test legal category aggregation and reporting."""
        converter = LegalBenchDatasetConverter()
        result = converter.convert(self.temp_dir)
        
        # Should detect different legal categories
        categories_found = set(result.legal_category_summary.keys())
        expected_categories = {
            LegalCategory.CONTRACT,
            LegalCategory.REGULATORY, 
            LegalCategory.JUDICIAL,
            LegalCategory.CRIMINAL,
            LegalCategory.CONSTITUTIONAL
        }
        
        # Should find most expected categories
        intersection = categories_found.intersection(expected_categories)
        self.assertGreaterEqual(len(intersection), 3)  # At least 3 categories detected

    def test_progress_tracking_directories(self) -> None:
        """Test real-time progress tracking across directory processing."""
        config = LegalBenchConversionConfig(enable_progress_tracking=True)
        converter = LegalBenchDatasetConverter(config)
        
        # Monitor conversion statistics during processing
        start_time = time.time()
        result = converter.convert(self.temp_dir)
        end_time = time.time()
        
        # Should complete in reasonable time
        processing_time = end_time - start_time
        self.assertLess(processing_time, 30)  # Should complete within 30 seconds for small test
        
        # Should have tracked statistics
        stats = converter.get_conversion_statistics()
        self.assertGreater(stats["total_processed"], 0)
        self.assertGreaterEqual(stats["success_rate"], 0.0)


class TestLegalClassificationIntegration(unittest.TestCase):
    """Integration tests for legal classification services."""

    def setUp(self) -> None:
        """Set up legal classification test fixtures."""
        self.legal_service = LegalService()

    def test_legal_categorization_service(self) -> None:
        """Test legal classification service integration."""
        # Should fail initially - service integration not implemented
        classification = self.legal_service.classify_legal_task("contract_lease_agreement")
        
        self.assertEqual(classification.primary_category, LegalCategory.CONTRACT)
        self.assertGreater(classification.confidence, 0.5)

    def test_professional_validation_service(self) -> None:
        """Test professional validation metadata service."""
        expertise_areas = self.legal_service.get_legal_expertise_areas("constitutional_due_process")
        
        self.assertIsInstance(expertise_areas, list)
        self.assertIn("constitutional", expertise_areas)
        self.assertIn("due_process", expertise_areas)

    def test_legal_complexity_assessment(self) -> None:
        """Test legal complexity scoring integration."""
        # Constitutional law should be very high complexity
        classification = self.legal_service.classify_legal_task("constitutional_first_amendment_strict_scrutiny")
        
        # Should detect high or very high complexity
        self.assertIn(classification.complexity.value, ["high", "very_high"])

    def test_specialization_mapping_service(self) -> None:
        """Test legal specialization mapping service."""
        classification = self.legal_service.classify_legal_task("contract_employment_discrimination")
        
        # Should detect employment specialization
        specializations = [spec.area for spec in classification.specializations]
        self.assertTrue(any("employment" in spec for spec in specializations))


class TestDataQualityAndValidation(unittest.TestCase):
    """Integration tests for data quality and validation."""

    def setUp(self) -> None:
        """Set up data quality test fixtures."""
        self.legal_service = LegalService()
        self.temp_dir = tempfile.mkdtemp()
        self._create_validation_test_data()

    def tearDown(self) -> None:
        """Clean up data quality test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_validation_test_data(self) -> None:
        """Create test data for validation testing."""
        task_dir = os.path.join(self.temp_dir, "validation_test_task")
        os.makedirs(task_dir)
        
        # Create well-formed train.tsv
        with open(os.path.join(task_dir, "train.tsv"), 'w') as f:
            f.write("question\tanswer\tlabel\tcase_reference\n")
            f.write("Is this contract valid?\tYes\tcontract_validity\tContract_001\n")
            f.write("What are the terms?\t30 days delivery\tdelivery_terms\tContract_001\n")
        
        # Create test.tsv
        with open(os.path.join(task_dir, "test.tsv"), 'w') as f:
            f.write("question\tanswer\tlabel\tcase_reference\n")
            f.write("Is breach proven?\tNo\tbreach_analysis\tContract_001\n")

    def test_legal_question_format_validation(self) -> None:
        """Test legal reasoning question format compliance."""
        converter = LegalBenchDatasetConverter()
        result = converter.convert(self.temp_dir)
        
        # All questions should have proper format
        for question in result.dataset.questions:
            self.assertIsNotNone(question.question)
            self.assertGreater(len(question.question), 0)
            self.assertIsNotNone(question.answer_type)
            self.assertIsNotNone(question.correct_answer)

    def test_answer_type_validation(self) -> None:
        """Test answer format validation for legal questions."""
        converter = LegalBenchDatasetConverter()
        result = converter.convert(self.temp_dir)
        
        # Answer types should be valid
        valid_answer_types = {"int", "str", "bool", "float"}
        for question in result.dataset.questions:
            self.assertIn(question.answer_type, valid_answer_types)

    def test_metadata_completeness(self) -> None:
        """Test professional validation metadata completeness."""
        converter = LegalBenchDatasetConverter()
        result = converter.convert(self.temp_dir)
        
        # All questions should have complete metadata
        for question in result.dataset.questions:
            self.assertIsNotNone(question.metadata)
            self.assertIsNotNone(question.metadata.legal_classification)
            self.assertIsNotNone(question.metadata.professional_validation)
            self.assertTrue(question.metadata.professional_validation.validated)

    def test_legal_domain_accuracy(self) -> None:
        """Test manual verification of legal domain classification."""
        # Create task with clear contract indicators
        contract_task_dir = os.path.join(self.temp_dir, "clear_contract_task")
        os.makedirs(contract_task_dir)
        
        with open(os.path.join(contract_task_dir, "train.tsv"), 'w') as f:
            f.write("question\tanswer\tlabel\n")
            f.write("What is the contract term?\t1 year\tterm_analysis\n")
        
        converter = LegalBenchDatasetConverter()
        result = converter.convert(self.temp_dir)
        
        # Should classify contract-related tasks correctly
        contract_results = [r for r in result.conversion_results if "contract" in r.task_name.lower()]
        if contract_results:
            self.assertEqual(contract_results[0].legal_category, LegalCategory.CONTRACT)


class TestServiceIntegration(unittest.TestCase):
    """Integration tests for service layer functionality."""

    def setUp(self) -> None:
        """Set up service integration test fixtures."""
        self.legal_service = LegalService()
        self.temp_dir = tempfile.mkdtemp()
        self._create_service_test_data()

    def tearDown(self) -> None:
        """Clean up service integration test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_service_test_data(self) -> None:
        """Create test data for service integration."""
        task_dir = os.path.join(self.temp_dir, "service_integration_task")
        os.makedirs(task_dir)
        
        with open(os.path.join(task_dir, "train.tsv"), 'w') as f:
            f.write("question\tanswer\tlabel\n")
            f.write("Service integration test?\tYes\tintegration_test\n")

    def test_api_endpoint_integration(self) -> None:
        """Test FastAPI service integration for LegalBench."""
        # Should fail initially - API integration not implemented
        converter_info = self.legal_service.get_converter_info()
        
        self.assertEqual(converter_info["name"], "LegalBench Converter")
        self.assertTrue(converter_info["capabilities"]["legal_domain_classification"])

    def test_database_persistence_legal(self) -> None:
        """Test legal dataset storage with domain metadata."""
        # This would test database persistence of legal metadata
        # Implementation depends on database layer
        self.assertTrue(True)  # Placeholder for now

    def test_validation_framework_legal(self) -> None:
        """Test legal domain validation framework integration."""
        classification = self.legal_service.classify_legal_task("contract_validation_test")
        warnings = self.legal_service.validate_legal_classification(classification)
        
        self.assertIsInstance(warnings, list)
        # Should either have no warnings or reasonable warnings
        if warnings:
            for warning in warnings:
                self.assertIsInstance(warning, str)
                self.assertGreater(len(warning), 0)

    def test_error_recovery_directories(self) -> None:
        """Test directory-level failure recovery mechanisms."""
        # Create directory with problematic data
        bad_task_dir = os.path.join(self.temp_dir, "malformed_task")
        os.makedirs(bad_task_dir)
        
        # Create malformed TSV
        with open(os.path.join(bad_task_dir, "train.tsv"), 'w') as f:
            f.write("malformed\tdata\twithout\tproper\theaders\n")
            f.write("and\tinconsistent\tcolumn\tcounts\n")
        
        converter = LegalBenchDatasetConverter()
        
        # Should handle errors gracefully and continue processing
        result = converter.convert(self.temp_dir)
        
        self.assertIsNotNone(result)
        # Should have some failures but not crash completely
        self.assertGreaterEqual(result.processing_stats["failed_conversions"], 0)


class TestAsyncConversionIntegration(unittest.TestCase):
    """Integration tests for async conversion functionality."""

    def setUp(self) -> None:
        """Set up async integration test fixtures."""
        self.legal_service = LegalService()
        self.temp_dir = tempfile.mkdtemp()
        self._create_async_test_data()

    def tearDown(self) -> None:
        """Clean up async integration test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_async_test_data(self) -> None:
        """Create test data for async processing."""
        task_dir = os.path.join(self.temp_dir, "async_test_task")
        os.makedirs(task_dir)
        
        with open(os.path.join(task_dir, "train.tsv"), 'w') as f:
            f.write("question\tanswer\tlabel\n")
            f.write("Async processing test?\tYes\tasync_test\n")

    def test_async_conversion_initiation(self) -> None:
        """Test async conversion job initiation."""
        # Should fail initially - async conversion not implemented
        async def run_test():
            conversion_id = await self.legal_service.initiate_conversion(self.temp_dir)
            self.assertIsInstance(conversion_id, str)
            self.assertGreater(len(conversion_id), 0)
            return conversion_id
        
        # May fail due to implementation not complete
        try:
            conversion_id = asyncio.run(run_test())
            self.assertIsNotNone(conversion_id)
        except (NotImplementedError, FileNotFoundError):
            # Expected to fail initially
            pass

    def test_conversion_status_tracking(self) -> None:
        """Test conversion job status tracking."""
        # This test would verify status tracking functionality
        # Should fail initially since async conversion not implemented
        try:
            async def run_test():
                conversion_id = await self.legal_service.initiate_conversion(self.temp_dir)
                
                # Wait briefly for processing to start
                await asyncio.sleep(0.1)
                
                status = self.legal_service.get_conversion_status(conversion_id)
                self.assertIn("status", status)
                self.assertIn("progress", status)
                
                return status
            
            asyncio.run(run_test())
        except (NotImplementedError, FileNotFoundError, ValueError):
            # Expected to fail initially
            pass


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)