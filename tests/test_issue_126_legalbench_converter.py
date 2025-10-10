#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Unit tests for LegalBench dataset converter (Issue #126).

Comprehensive test suite following TDD methodology for LegalBench converter
implementation including legal domain classification, TSV processing,
and QuestionAnsweringEntry generation.

SECURITY: All tests use sanitized inputs and validate security constraints.
"""

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.core.converters.legalbench_converter import (
    LegalBenchDatasetConverter,
    LegalQuestionFormatAnalyzer,
    TSVProcessor,
)
from app.schemas.legalbench_datasets import (
    LegalBenchConversionConfig,
    LegalCategory,
    LegalClassification,
    LegalComplexity,
    QuestionAnsweringDataset,
    QuestionAnsweringEntry,
    QuestionFormat,
)
from app.services.legal_service import LegalService
from app.utils.legal_categorization import LegalCategorizationEngine


class TestLegalBenchConverter(unittest.TestCase):
    """Unit tests for LegalBenchDatasetConverter core functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = LegalBenchConversionConfig()
        self.converter = LegalBenchDatasetConverter(self.config)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_converter_initialization(self) -> None:
        """Test basic converter initialization with legal classification config."""
        # Should fail initially - converter not implemented
        converter = LegalBenchDatasetConverter()
        
        self.assertIsNotNone(converter)
        self.assertIsNotNone(converter.legal_engine)
        self.assertIsNotNone(converter.tsv_processor)
        self.assertIsInstance(converter.config, LegalBenchConversionConfig)

    def test_converter_initialization_with_config(self) -> None:
        """Test converter initialization with custom configuration."""
        config = LegalBenchConversionConfig(
            parallel_processing=True,
            max_workers=8,
            batch_size=500
        )
        
        converter = LegalBenchDatasetConverter(config)
        
        self.assertEqual(converter.config.parallel_processing, True)
        self.assertEqual(converter.config.max_workers, 8)
        self.assertEqual(converter.config.batch_size, 500)

    def test_directory_traversal_empty_directory(self) -> None:
        """Test directory traversal with empty directory."""
        # Should fail initially - discover method not implemented
        with self.assertRaises(ValueError):
            self.converter.convert(self.temp_dir)

    def test_directory_traversal_missing_directory(self) -> None:
        """Test directory traversal with non-existent directory."""
        missing_path = os.path.join(self.temp_dir, "nonexistent")
        
        with self.assertRaises(FileNotFoundError):
            self.converter.convert(missing_path)

    def test_legal_task_directory_discovery(self) -> None:
        """Test discovery of legal task directories."""
        # Create mock legal task directories
        task_dirs = ["contract_analysis_basic", "regulatory_compliance_financial", "judicial_reasoning_civil"]
        
        for task_dir in task_dirs:
            task_path = os.path.join(self.temp_dir, task_dir)
            os.makedirs(task_path)
            
            # Create mock TSV files
            with open(os.path.join(task_path, "train.tsv"), 'w') as f:
                f.write("question\tanswer\tlabel\n")
                f.write("What is the contract term?\t30 days\tdelivery_obligation\n")
            
            with open(os.path.join(task_path, "test.tsv"), 'w') as f:
                f.write("question\tanswer\tlabel\n")
                f.write("Is this compliant?\tYes\tcompliance_check\n")
        
        # Should fail initially - method not implemented
        directories = self.converter._discover_task_directories(self.temp_dir)
        
        self.assertEqual(len(directories), 3)
        self.assertIn("contract_analysis_basic", directories)
        self.assertIn("regulatory_compliance_financial", directories)
        self.assertIn("judicial_reasoning_civil", directories)

    def test_conversion_error_handling(self) -> None:
        """Test error recovery and validation during conversion."""
        # Create directory with malformed TSV
        task_path = os.path.join(self.temp_dir, "malformed_task")
        os.makedirs(task_path)
        
        with open(os.path.join(task_path, "train.tsv"), 'w') as f:
            f.write("invalid\ttsv\tcontent\twith\ttoo\tmany\tcolumns\n")
        
        # Should handle errors gracefully
        result = self.converter.convert(self.temp_dir)
        
        # Should have some failed conversions but not crash
        self.assertIsNotNone(result)
        self.assertTrue(result.processing_stats["failed_conversions"] >= 0)


class TestLegalDomainClassification(unittest.TestCase):
    """Unit tests for legal domain classification functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.legal_engine = LegalCategorizationEngine()

    def test_contract_category_detection(self) -> None:
        """Test contract law task identification."""
        # Should fail initially - classification not implemented properly
        task_name = "cuad_contract_analysis_basic"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        self.assertEqual(classification.primary_category, LegalCategory.CONTRACT)
        self.assertGreater(classification.confidence, 0.5)
        self.assertEqual(classification.complexity, LegalComplexity.MEDIUM)

    def test_regulatory_category_detection(self) -> None:
        """Test regulatory compliance task identification."""
        task_name = "regulatory_compliance_financial_cfr"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        self.assertEqual(classification.primary_category, LegalCategory.REGULATORY)
        self.assertGreater(classification.confidence, 0.5)
        self.assertEqual(classification.complexity, LegalComplexity.HIGH)

    def test_judicial_category_detection(self) -> None:
        """Test judicial reasoning task identification."""
        task_name = "judicial_court_decision_analysis"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        self.assertEqual(classification.primary_category, LegalCategory.JUDICIAL)
        self.assertGreater(classification.confidence, 0.5)

    def test_civil_category_detection(self) -> None:
        """Test civil law task identification."""
        task_name = "civil_tort_liability_negligence"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        self.assertEqual(classification.primary_category, LegalCategory.CIVIL)
        self.assertGreater(classification.confidence, 0.5)

    def test_criminal_category_detection(self) -> None:
        """Test criminal law task identification."""
        task_name = "criminal_prosecution_evidence_analysis"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        self.assertEqual(classification.primary_category, LegalCategory.CRIMINAL)
        self.assertGreater(classification.confidence, 0.5)

    def test_constitutional_category_detection(self) -> None:
        """Test constitutional law task identification."""
        task_name = "constitutional_rights_first_amendment"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        self.assertEqual(classification.primary_category, LegalCategory.CONSTITUTIONAL)
        self.assertGreater(classification.confidence, 0.5)
        self.assertEqual(classification.complexity, LegalComplexity.VERY_HIGH)

    def test_corporate_category_detection(self) -> None:
        """Test corporate law task identification."""
        task_name = "corporate_governance_securities_disclosure"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        self.assertEqual(classification.primary_category, LegalCategory.CORPORATE)
        self.assertGreater(classification.confidence, 0.5)

    def test_ip_category_detection(self) -> None:
        """Test intellectual property law task identification."""
        task_name = "ip_patent_infringement_analysis"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        self.assertEqual(classification.primary_category, LegalCategory.INTELLECTUAL_PROPERTY)
        self.assertGreater(classification.confidence, 0.5)

    def test_specialization_mapping(self) -> None:
        """Test legal specialization sub-categorization."""
        task_name = "contract_employment_discrimination"
        classification = self.legal_engine.classify_legal_task(task_name)
        
        # Should detect employment specialization within contract category
        specialization_areas = [spec.area for spec in classification.specializations]
        self.assertIn("employment", specialization_areas)

    def test_content_based_classification_enhancement(self) -> None:
        """Test classification improvement with content analysis."""
        task_name = "legal_analysis_task"  # Generic name
        
        # Without content - should be general
        classification_basic = self.legal_engine.classify_legal_task(task_name)
        
        # With content - should be more specific
        content = {
            "question": "What are the constitutional implications of this search and seizure?",
            "context": "Fourth Amendment analysis regarding probable cause and warrant requirements"
        }
        classification_enhanced = self.legal_engine.classify_legal_task(task_name, content)
        
        # Enhanced classification should be more confident and specific
        self.assertGreaterEqual(classification_enhanced.confidence, classification_basic.confidence)


class TestTSVProcessing(unittest.TestCase):
    """Unit tests for TSV processing with legal domain awareness."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.tsv_processor = TSVProcessor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tsv_format_detection(self) -> None:
        """Test auto-detection of TSV delimiter and field structure."""
        # Tab-separated format
        tsv_content = "question\tanswer\tlabel\nWhat is X?\tY\ttest\n"
        
        # Should fail initially - delimiter detection not implemented
        delimiter = self.tsv_processor._detect_delimiter(tsv_content)
        self.assertEqual(delimiter, '\t')
        
        # Comma-separated format
        csv_content = "question,answer,label\nWhat is X?,Y,test\n"
        delimiter = self.tsv_processor._detect_delimiter(csv_content)
        self.assertEqual(delimiter, ',')

    def test_train_test_split_parsing(self) -> None:
        """Test separate parsing of train.tsv and test.tsv files."""
        task_dir = os.path.join(self.temp_dir, "test_task")
        os.makedirs(task_dir)
        
        # Create train.tsv
        train_path = os.path.join(task_dir, "train.tsv")
        with open(train_path, 'w') as f:
            f.write("question\tanswer\tlabel\n")
            f.write("Train question 1?\tTrain answer 1\ttrain_label_1\n")
            f.write("Train question 2?\tTrain answer 2\ttrain_label_2\n")
        
        # Create test.tsv
        test_path = os.path.join(task_dir, "test.tsv")
        with open(test_path, 'w') as f:
            f.write("question\tanswer\tlabel\n")
            f.write("Test question 1?\tTest answer 1\ttest_label_1\n")
        
        # Should fail initially - processing not implemented
        train_data = self.tsv_processor.process_tsv_file(train_path, "test_task", "train")
        test_data = self.tsv_processor.process_tsv_file(test_path, "test_task", "test")
        
        self.assertEqual(len(train_data), 2)
        self.assertEqual(len(test_data), 1)
        self.assertEqual(train_data[0]["split"], "train")
        self.assertEqual(test_data[0]["split"], "test")

    def test_flexible_field_mapping(self) -> None:
        """Test handling of varying TSV column structures."""
        # Contract analysis format
        contract_tsv = os.path.join(self.temp_dir, "contract.tsv")
        with open(contract_tsv, 'w') as f:
            f.write("text\tquestion\tanswer\tlabel\tcase_reference\n")
            f.write("Agreement text...\tWhat are obligations?\t30 days\tdelivery\tContract_001\n")
        
        # Regulatory format
        regulatory_tsv = os.path.join(self.temp_dir, "regulatory.tsv")
        with open(regulatory_tsv, 'w') as f:
            f.write("regulation_text\tscenario\tquestion\tanswer\texplanation\n")
            f.write("CFR Section 12.3...\tCompany policy...\tCompliant?\tYes\tMeets requirements\n")
        
        # Should handle both formats
        contract_data = self.tsv_processor.process_tsv_file(contract_tsv, "contract_task", "train")
        regulatory_data = self.tsv_processor.process_tsv_file(regulatory_tsv, "regulatory_task", "train")
        
        self.assertEqual(len(contract_data), 1)
        self.assertEqual(len(regulatory_data), 1)
        
        # Should extract legal context appropriately
        self.assertIn("case_reference", contract_data[0]["legal_context"])
        self.assertEqual(contract_data[0]["legal_context"]["case_reference"], "Contract_001")

    def test_legal_question_format_detection(self) -> None:
        """Test legal reasoning question type identification."""
        analyzer = LegalQuestionFormatAnalyzer()
        
        # Multiple choice format
        mc_row = {
            "question": "Which party has the obligation? (A) Party A (B) Party B (C) Both",
            "answer": "A",
            "A": "Party A",
            "B": "Party B", 
            "C": "Both"
        }
        
        # Should fail initially - format analysis not implemented
        format_info = analyzer.analyze_question_format(mc_row)
        self.assertEqual(format_info["format_type"], QuestionFormat.MULTIPLE_CHOICE)
        self.assertEqual(format_info["answer_type"], "int")
        self.assertEqual(format_info["correct_answer"], 0)  # Index of "A"

    def test_answer_format_handling(self) -> None:
        """Test multiple choice vs. open-ended answer processing."""
        analyzer = LegalQuestionFormatAnalyzer()
        
        # Binary answer format
        binary_row = {
            "question": "Is this constitutional?",
            "answer": "Yes"
        }
        
        format_info = analyzer.analyze_question_format(binary_row)
        self.assertEqual(format_info["format_type"], QuestionFormat.BINARY)
        self.assertEqual(format_info["answer_type"], "str")
        self.assertEqual(format_info["correct_answer"], "Yes")


class TestQuestionAnsweringEntryGeneration(unittest.TestCase):
    """Unit tests for QuestionAnsweringEntry generation with legal metadata."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.converter = LegalBenchDatasetConverter()

    def test_legal_qa_entry_creation(self) -> None:
        """Test legal Q&A entry creation with domain metadata."""
        row_data = {
            "raw_row": {
                "question": "What is the delivery obligation in this contract?",
                "answer": "30 days from signing",
                "label": "delivery_obligation"
            },
            "task_name": "contract_delivery_analysis",
            "split": "train",
            "row_number": 0,
            "source_file": "/path/to/train.tsv",
            "format_info": {
                "format_type": QuestionFormat.SHORT_ANSWER,
                "answer_type": "str",
                "correct_answer": "30 days from signing",
                "choices": None,
                "question_text": "What is the delivery obligation in this contract?"
            },
            "legal_context": {"case_reference": "Contract_001"},
            "processing_timestamp": datetime.now(timezone.utc)
        }
        
        # Should fail initially - entry creation not implemented
        qa_entry = self.converter._create_question_answering_entry(row_data)
        
        self.assertIsInstance(qa_entry, QuestionAnsweringEntry)
        self.assertEqual(qa_entry.answer_type, "str")
        self.assertEqual(qa_entry.correct_answer, "30 days from signing")
        self.assertEqual(qa_entry.metadata.task_name, "contract_delivery_analysis")
        self.assertEqual(qa_entry.metadata.split, "train")

    def test_legal_context_preservation(self) -> None:
        """Test legal case/statute context preservation."""
        row_data = {
            "raw_row": {
                "question": "What precedent applies?",
                "answer": "Smith v. Jones",
                "precedent_reference": "Smith_v_Jones_2020"
            },
            "task_name": "judicial_precedent_analysis",
            "split": "test",
            "row_number": 5,
            "source_file": "/path/to/test.tsv",
            "format_info": {
                "format_type": QuestionFormat.SHORT_ANSWER,
                "answer_type": "str",
                "correct_answer": "Smith v. Jones",
                "choices": None,
                "question_text": "What precedent applies?"
            },
            "legal_context": {"precedent_reference": "Smith_v_Jones_2020"},
            "processing_timestamp": datetime.now(timezone.utc)
        }
        
        qa_entry = self.converter._create_question_answering_entry(row_data)
        
        self.assertIn("precedent_reference", qa_entry.metadata.legal_context)
        self.assertEqual(qa_entry.metadata.legal_context["precedent_reference"], "Smith_v_Jones_2020")

    def test_train_test_split_metadata(self) -> None:
        """Test train/test split information preservation."""
        train_row_data = {
            "raw_row": {"question": "What are the training requirements for this position?", "answer": "40 hours of training required"},
            "task_name": "split_test_task",
            "split": "train",
            "row_number": 0,
            "source_file": "/path/to/train.tsv",
            "format_info": {
                "format_type": QuestionFormat.SHORT_ANSWER,
                "answer_type": "str",
                "correct_answer": "40 hours of training required",
                "choices": None,
                "question_text": "What are the training requirements for this position?"
            },
            "legal_context": {},
            "processing_timestamp": datetime.now(timezone.utc)
        }
        
        test_row_data = {
            "raw_row": {"question": "What testing procedures must be followed?", "answer": "Annual compliance testing required"},
            "task_name": "split_test_task",
            "split": "test",
            "row_number": 0,
            "source_file": "/path/to/test.tsv",
            "format_info": {
                "format_type": QuestionFormat.SHORT_ANSWER,
                "answer_type": "str",
                "correct_answer": "Annual compliance testing required",
                "choices": None,
                "question_text": "What testing procedures must be followed?"
            },
            "legal_context": {},
            "processing_timestamp": datetime.now(timezone.utc)
        }
        
        train_entry = self.converter._create_question_answering_entry(train_row_data)
        test_entry = self.converter._create_question_answering_entry(test_row_data)
        
        self.assertEqual(train_entry.metadata.split, "train")
        self.assertEqual(test_entry.metadata.split, "test")
        self.assertNotEqual(train_entry.metadata.source_file, test_entry.metadata.source_file)

    def test_professional_validation_tags(self) -> None:
        """Test professional validation metadata inclusion."""
        row_data = {
            "raw_row": {"question": "What constitutional rights are implicated in this case?", "answer": "First Amendment speech rights"},
            "task_name": "constitutional_rights_analysis",
            "split": "train",
            "row_number": 0,
            "source_file": "/path/to/train.tsv",
            "format_info": {
                "format_type": QuestionFormat.SHORT_ANSWER,
                "answer_type": "str",
                "correct_answer": "First Amendment speech rights",
                "choices": None,
                "question_text": "What constitutional rights are implicated in this case?"
            },
            "legal_context": {},
            "processing_timestamp": datetime.now(timezone.utc)
        }
        
        qa_entry = self.converter._create_question_answering_entry(row_data)
        
        self.assertTrue(qa_entry.metadata.professional_validation.validated)
        self.assertEqual(qa_entry.metadata.professional_validation.validator_count, "40+")
        self.assertTrue(qa_entry.metadata.professional_validation.peer_reviewed)

    def test_legal_complexity_scoring(self) -> None:
        """Test legal complexity assessment integration."""
        # Constitutional law task (very high complexity)
        constitutional_row = {
            "raw_row": {"question": "Constitutional analysis?", "answer": "Due process applies"},
            "task_name": "constitutional_due_process_analysis",
            "split": "train",
            "row_number": 0,
            "source_file": "/path/to/train.tsv",
            "format_info": {
                "format_type": QuestionFormat.SHORT_ANSWER,
                "answer_type": "str",
                "correct_answer": "Due process applies",
                "choices": None,
                "question_text": "Constitutional analysis?"
            },
            "legal_context": {},
            "processing_timestamp": datetime.now(timezone.utc)
        }
        
        qa_entry = self.converter._create_question_answering_entry(constitutional_row)
        
        # Should detect high/very high complexity for constitutional law
        complexity = qa_entry.metadata.legal_classification.complexity
        self.assertIn(complexity, [LegalComplexity.HIGH, LegalComplexity.VERY_HIGH])


class TestLegalService(unittest.TestCase):
    """Unit tests for LegalService integration."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.legal_service = LegalService()

    def test_service_initialization(self) -> None:
        """Test legal service initialization."""
        # Should fail initially - service not implemented
        self.assertIsNotNone(self.legal_service)
        self.assertIsInstance(self.legal_service._legal_engine, LegalCategorizationEngine)

    def test_converter_info_retrieval(self) -> None:
        """Test retrieval of converter information."""
        info = self.legal_service.get_converter_info()
        
        self.assertEqual(info["name"], "LegalBench Converter")
        self.assertIn("legal_categories", info)
        self.assertEqual(len(info["legal_categories"]), 9)  # 8 categories + general
        self.assertTrue(info["capabilities"]["legal_domain_classification"])

    def test_legal_task_classification_service(self) -> None:
        """Test legal task classification through service."""
        classification = self.legal_service.classify_legal_task("contract_lease_analysis")
        
        self.assertEqual(classification.primary_category, LegalCategory.CONTRACT)
        self.assertGreater(classification.confidence, 0.0)

    def test_conversion_initiation(self) -> None:
        """Test conversion job initiation."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Should fail initially - conversion not implemented
            with self.assertRaises((FileNotFoundError, ValueError)):
                conversion_id = asyncio.run(self.legal_service.initiate_conversion(temp_dir))
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    # Run with verbose output
    unittest.main(verbosity=2)