#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Test suite for ACPBench Dataset Converter (Issue #125).

Tests the complete ACPBench converter implementation including JSON processing,
question type handlers, planning domain classification, and PyRIT format compliance.

SECURITY: All test data is for defensive security research only.
"""

import json
import os

# Add the violentutf_api directory to the path for testing
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List

violentutf_api_path = Path(__file__).parent.parent / "violentutf_api" / "fastapi_app"
sys.path.insert(0, str(violentutf_api_path))

try:
    from app.core.converters.acpbench_converter import (
        ACPBenchConverter,
        BooleanQuestionHandler,
        GenerationQuestionHandler,
        MultipleChoiceQuestionHandler,
    )
    from app.schemas.acpbench_datasets import (
        ACPBenchConversionConfig,
        PlanningComplexity,
        PlanningDomain,
        PlanningQuestionType,
    )
    from app.services.planning_service import PlanningDomainClassifier, PlanningScenarioAnalyzer
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Python path: {sys.path}")
    raise


class TestACPBenchConverter(unittest.TestCase):
    """Test cases for the main ACPBench converter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.converter = ACPBenchConverter()
        self.test_data_dir = Path(__file__).parent / "test_data" / "acpbench"
        
        # Ensure test data directory exists
        if not self.test_data_dir.exists():
            self.skipTest(f"Test data directory not found: {self.test_data_dir}")

    def test_converter_initialization(self):
        """Test ACPBench converter initializes correctly."""
        self.assertIsInstance(self.converter, ACPBenchConverter)
        self.assertIsNotNone(self.converter.config)
        self.assertIsNotNone(self.converter.domain_classifier)
        self.assertIsNotNone(self.converter.boolean_handler)
        self.assertIsNotNone(self.converter.mcq_handler) 
        self.assertIsNotNone(self.converter.gen_handler)

    def test_convert_with_sample_data(self):
        """Test complete conversion with sample ACPBench data."""
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")

        try:
            dataset = self.converter.convert(str(self.test_data_dir), "Test_ACPBench")
            
            # Basic structure validation
            self.assertIsNotNone(dataset)
            self.assertEqual(dataset.name, "Test_ACPBench")
            self.assertEqual(dataset.version, "1.0")
            self.assertGreater(len(dataset.questions), 0)
            
            # Check question types are present
            question_types = [q.metadata.get("question_type") for q in dataset.questions]
            self.assertIn("boolean", question_types)
            self.assertIn("multiple_choice", question_types)
            self.assertIn("generation", question_types)
            
            # Validate PyRIT format compliance
            for question in dataset.questions:
                self.assertIsNotNone(question.question)
                self.assertIsNotNone(question.answer_type)
                self.assertIsNotNone(question.correct_answer)
                self.assertIsInstance(question.choices, list)
                self.assertIsInstance(question.metadata, dict)
                
                # Check required metadata fields
                required_fields = ["task_id", "planning_group", "question_type", 
                                 "domain", "planning_domain", "conversion_strategy"]
                for field in required_fields:
                    self.assertIn(field, question.metadata, 
                                f"Missing required metadata field: {field}")

            print(f"Successfully converted {len(dataset.questions)} questions")
            
        except Exception as e:
            self.fail(f"Conversion failed with error: {str(e)}")

    def test_convert_nonexistent_directory(self):
        """Test converter handles non-existent directory gracefully."""
        with self.assertRaises(FileNotFoundError):
            self.converter.convert("/nonexistent/directory")

    def test_convert_empty_directory(self):
        """Test converter handles directory with no JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                self.converter.convert(temp_dir)


class TestPlanningDomainClassifier(unittest.TestCase):
    """Test cases for the planning domain classifier."""

    def setUp(self):
        """Set up test fixtures."""
        self.classifier = PlanningDomainClassifier()

    def test_classifier_initialization(self):
        """Test planning domain classifier initializes correctly."""
        self.assertIsInstance(self.classifier, PlanningDomainClassifier)
        self.assertIsNotNone(self.classifier.domain_patterns)
        
        # Check all expected domains are configured
        expected_domains = [
            PlanningDomain.LOGISTICS, 
            PlanningDomain.BLOCKS_WORLD,
            PlanningDomain.SCHEDULING, 
            PlanningDomain.GENERAL_PLANNING
        ]
        for domain in expected_domains:
            self.assertIn(domain, self.classifier.domain_patterns)

    def test_classify_logistics_domain(self):
        """Test classification of logistics domain content."""
        context = "A truck needs to deliver packages from warehouse to locations"
        question = "What is the optimal delivery route?"
        
        domain, confidence = self.classifier.classify_domain(context, question)
        
        self.assertEqual(domain, PlanningDomain.LOGISTICS)
        self.assertGreater(confidence, 0.1)

    def test_classify_blocks_world_domain(self):
        """Test classification of blocks world domain content."""
        context = "There are 3 blocks: A, B, and C. Block A is on the table, B is on A"
        question = "Can block C be placed on top of block B?"
        
        domain, confidence = self.classifier.classify_domain(context, question)
        
        self.assertEqual(domain, PlanningDomain.BLOCKS_WORLD)
        self.assertGreater(confidence, 0.1)

    def test_assess_complexity_levels(self):
        """Test complexity assessment for different scenarios."""
        # Simple scenario
        simple_context = "Move block A to position B"
        simple_question = "Is this possible?"
        complexity = self.classifier.assess_complexity(simple_context, simple_question, PlanningDomain.BLOCKS_WORLD)
        
        # Complex scenario  
        complex_context = "Multi-agent coordination with optimization constraints and temporal dependencies"
        complex_question = "Find optimal solution considering all constraints?"
        complex_complexity = self.classifier.assess_complexity(complex_context, complex_question, PlanningDomain.GENERAL_PLANNING)
        
        # Complexity should be valid enum values
        self.assertIsInstance(complexity, PlanningComplexity)
        self.assertIsInstance(complex_complexity, PlanningComplexity)

    def test_extract_key_concepts(self):
        """Test key concept extraction from planning content."""
        context = "Logistics scenario with trucks delivering packages to locations"
        question = "What is the optimal route?"
        
        concepts = self.classifier.extract_key_concepts(context, question, PlanningDomain.LOGISTICS)
        
        self.assertIsInstance(concepts, list)
        self.assertGreater(len(concepts), 0)
        
        # Should contain relevant logistics concepts
        concept_text = " ".join(concepts).lower()
        logistics_terms = ["truck", "deliver", "package", "location", "route"]
        found_terms = sum(1 for term in logistics_terms if term in concept_text)
        self.assertGreater(found_terms, 0, "Should extract relevant logistics concepts")


class TestQuestionHandlers(unittest.TestCase):
    """Test cases for question type handlers."""

    def setUp(self):
        """Set up test fixtures."""
        self.domain_classifier = PlanningDomainClassifier()
        self.boolean_handler = BooleanQuestionHandler(self.domain_classifier)
        self.mcq_handler = MultipleChoiceQuestionHandler(self.domain_classifier)
        self.gen_handler = GenerationQuestionHandler(self.domain_classifier)

    def test_boolean_handler(self):
        """Test boolean question handler."""
        item = {
            "id": "test_bool_1",
            "group": "logistics",
            "context": "A truck can carry 2 packages at once",
            "question": "Can it deliver 3 packages in one trip?",
            "correct": False
        }
        
        qa_entry = self.boolean_handler.create_qa_entry(item)
        
        self.assertEqual(qa_entry.answer_type, "bool")
        self.assertEqual(qa_entry.correct_answer, False)
        self.assertEqual(qa_entry.choices, [])
        self.assertIn("Context:", qa_entry.question)
        self.assertIn("Question:", qa_entry.question)
        
        # Check metadata
        self.assertEqual(qa_entry.metadata["task_id"], "test_bool_1")
        self.assertEqual(qa_entry.metadata["planning_group"], "logistics")
        self.assertEqual(qa_entry.metadata["question_type"], "boolean")

    def test_multiple_choice_handler(self):
        """Test multiple choice question handler."""
        item = {
            "id": "test_mcq_1",
            "group": "blocks_world",
            "context": "Blocks A, B, C with A on table, B on A",
            "question": "What's the first step to put C on B?",
            "choices": ["A) Move C directly", "B) Move B to table first", "C) Impossible"],
            "answer": "B) Move B to table first"
        }
        
        qa_entry = self.mcq_handler.create_qa_entry(item)
        
        self.assertEqual(qa_entry.answer_type, "int")
        self.assertIsInstance(qa_entry.correct_answer, int)
        self.assertEqual(len(qa_entry.choices), 3)
        self.assertIn("Context:", qa_entry.question)
        
        # Check metadata
        self.assertEqual(qa_entry.metadata["task_id"], "test_mcq_1")
        self.assertEqual(qa_entry.metadata["question_type"], "multiple_choice")
        self.assertEqual(qa_entry.metadata["choice_count"], 3)

    def test_generation_handler(self):
        """Test generation question handler."""
        item = {
            "id": "test_gen_1",
            "group": "general_planning",
            "context": "Agent needs to collect objects from different locations",
            "question": "Generate the action sequence",
            "expected_response": "Step 1: Move to object1. Step 2: Pick object1. Step 3: Return to base."
        }
        
        qa_entry = self.gen_handler.create_qa_entry(item)
        
        self.assertEqual(qa_entry.answer_type, "str")
        self.assertIsInstance(qa_entry.correct_answer, str)
        self.assertEqual(qa_entry.choices, [])
        self.assertIn("Step 1:", qa_entry.correct_answer)
        
        # Check metadata
        self.assertEqual(qa_entry.metadata["task_id"], "test_gen_1")
        self.assertEqual(qa_entry.metadata["question_type"], "generation")
        self.assertEqual(qa_entry.metadata["response_type"], "action_sequence")

    def test_mcq_answer_index_mapping(self):
        """Test multiple choice answer index mapping."""
        # Test exact match
        choices = ["Option A", "Option B", "Option C"]
        index = self.mcq_handler._find_correct_answer_index("Option B", choices)
        self.assertEqual(index, 1)
        
        # Test prefix match (A), B), etc.)
        choices = ["A) First option", "B) Second option", "C) Third option"]  
        index = self.mcq_handler._find_correct_answer_index("B) Second option", choices)
        self.assertEqual(index, 1)
        
        # Test partial match
        choices = ["Move block A first", "Move block B first", "Move block C first"]
        index = self.mcq_handler._find_correct_answer_index("Move block B", choices)
        self.assertEqual(index, 1)


class TestSchemaValidation(unittest.TestCase):
    """Test cases for schema validation and data structures."""

    def test_planning_domain_enum(self):
        """Test PlanningDomain enum values."""
        domains = [
            PlanningDomain.LOGISTICS,
            PlanningDomain.BLOCKS_WORLD, 
            PlanningDomain.SCHEDULING,
            PlanningDomain.GENERAL_PLANNING
        ]
        
        for domain in domains:
            self.assertIsInstance(domain.value, str)
            self.assertTrue(len(domain.value) > 0)

    def test_planning_complexity_enum(self):
        """Test PlanningComplexity enum values."""
        complexities = [
            PlanningComplexity.LOW,
            PlanningComplexity.MEDIUM,
            PlanningComplexity.HIGH
        ]
        
        for complexity in complexities:
            self.assertIsInstance(complexity.value, str)
            self.assertIn(complexity.value, ["low", "medium", "high"])

    def test_planning_question_type_enum(self):
        """Test PlanningQuestionType enum values."""
        question_types = [
            PlanningQuestionType.BOOLEAN,
            PlanningQuestionType.MULTIPLE_CHOICE,
            PlanningQuestionType.GENERATION
        ]
        
        for q_type in question_types:
            self.assertIsInstance(q_type.value, str)
            self.assertIn(q_type.value, ["boolean", "multiple_choice", "generation"])


if __name__ == "__main__":
    # Set up logging for test runs
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the tests
    unittest.main(verbosity=2)