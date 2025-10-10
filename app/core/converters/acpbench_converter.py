# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""ACPBench Dataset Converter Implementation (Issue #125).

Implements converter to transform ACPBench planning reasoning datasets from JSON format
to PyRIT QuestionAnsweringDataset format with comprehensive planning domain analysis,
context preservation, and question type handling across boolean, MCQ, and generation tasks.

This module supports Strategy 2 conversion for reasoning benchmarks with performance
targets of <120 seconds execution time and >100 questions/second processing rate.

SECURITY: All content is for defensive security research only. Proper sanitization
and validation is applied to all inputs to prevent injection attacks.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.validation import sanitize_file_content, sanitize_string
from app.schemas.acpbench_datasets import (
    ACPBenchConversionConfig,
    ACPBenchFileInfo,
    ConversionValidationResult,
    PlanningQuestionType,
    QuestionAnsweringDataset,
    QuestionAnsweringEntry,
)
from app.services.planning_service import PlanningDomainClassifier, PlanningScenarioAnalyzer


class QuestionHandlerBase:
    """Base class for question type handlers."""

    def __init__(self, domain_classifier: PlanningDomainClassifier) -> None:
        """Initialize base question handler.

        Args:
            domain_classifier: Planning domain classifier instance
        """
        self.domain_classifier = domain_classifier
        self.logger = logging.getLogger(__name__)

    def create_qa_entry(self, item: Dict[str, Any]) -> QuestionAnsweringEntry:
        """Create QuestionAnsweringEntry from item data.

        Args:
            item: JSON item data

        Returns:
            QuestionAnsweringEntry instance

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement create_qa_entry")

    def _create_full_question(self, context: str, question: str) -> str:
        """Create full question text with context preservation.

        Args:
            context: Planning scenario context
            question: Question text

        Returns:
            Combined question text with context
        """
        context = sanitize_string(context)
        question = sanitize_string(question)
        return f"Context: {context}\n\nQuestion: {question}"

    def _analyze_planning_content(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze planning content for domain and complexity.

        Args:
            item: JSON item data

        Returns:
            Analysis metadata dictionary
        """
        context = item.get("context", "")
        question = item.get("question", "")

        # Classify domain and complexity
        domain, domain_confidence = self.domain_classifier.classify_domain(context, question)
        complexity = self.domain_classifier.assess_complexity(context, question, domain)
        key_concepts = self.domain_classifier.extract_key_concepts(context, question, domain)

        return {
            "planning_domain": domain.value,
            "domain_confidence": domain_confidence,
            "planning_complexity": complexity.value,
            "key_concepts": key_concepts,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }


class BooleanQuestionHandler(QuestionHandlerBase):
    """Handler for boolean question types (bool.json)."""

    def create_qa_entry(self, item: Dict[str, Any]) -> QuestionAnsweringEntry:
        """Create boolean QuestionAnsweringEntry.

        Args:
            item: JSON item data with boolean question structure

        Returns:
            QuestionAnsweringEntry for boolean question
        """
        # Extract required fields
        task_id = sanitize_string(item.get("id", "unknown"))
        planning_group = sanitize_string(item.get("group", "unknown"))
        context = sanitize_string(item.get("context", ""))
        question = sanitize_string(item.get("question", ""))
        correct_answer = item.get("correct", False)

        # Create full question with context
        full_question = self._create_full_question(context, question)

        # Analyze planning content
        planning_analysis = self._analyze_planning_content(item)

        # Create metadata
        metadata = {
            "task_id": task_id,
            "planning_group": planning_group,
            "question_type": "boolean",
            "domain": "planning_reasoning",
            "original_context": context,
            "conversion_strategy": "strategy_2_reasoning_benchmarks",
            "conversion_timestamp": datetime.now(timezone.utc).isoformat(),
            **planning_analysis,
        }

        return QuestionAnsweringEntry(
            question=full_question,
            answer_type="bool",
            correct_answer=bool(correct_answer),
            choices=[],  # No choices for boolean questions
            metadata=metadata,
        )


class MultipleChoiceQuestionHandler(QuestionHandlerBase):
    """Handler for multiple choice question types (mcq.json)."""

    def create_qa_entry(self, item: Dict[str, Any]) -> QuestionAnsweringEntry:
        """Create multiple choice QuestionAnsweringEntry.

        Args:
            item: JSON item data with MCQ structure

        Returns:
            QuestionAnsweringEntry for multiple choice question
        """
        # Extract required fields
        task_id = sanitize_string(item.get("id", "unknown"))
        planning_group = sanitize_string(item.get("group", "unknown"))
        context = sanitize_string(item.get("context", ""))
        question = sanitize_string(item.get("question", ""))
        choices = item.get("choices", [])
        answer_text = sanitize_string(item.get("answer", ""))

        # Sanitize choices
        choices = [sanitize_string(choice) for choice in choices if choice]

        # Create full question with context
        full_question = self._create_full_question(context, question)

        # Find correct answer index
        correct_answer_index = self._find_correct_answer_index(answer_text, choices)

        # Analyze planning content
        planning_analysis = self._analyze_planning_content(item)

        # Create metadata
        metadata = {
            "task_id": task_id,
            "planning_group": planning_group,
            "question_type": "multiple_choice",
            "domain": "planning_reasoning",
            "original_context": context,
            "choice_count": len(choices),
            "conversion_strategy": "strategy_2_reasoning_benchmarks",
            "conversion_timestamp": datetime.now(timezone.utc).isoformat(),
            **planning_analysis,
        }

        return QuestionAnsweringEntry(
            question=full_question,
            answer_type="int",
            correct_answer=correct_answer_index,
            choices=choices,
            metadata=metadata,
        )

    def _find_correct_answer_index(self, answer_text: str, choices: List[str]) -> int:
        """Find the index of the correct answer in the choices list.

        Args:
            answer_text: Answer text from JSON
            choices: List of choice options

        Returns:
            Index of correct answer (0-based), or 0 if not found
        """
        if not answer_text or not choices:
            return 0

        answer_text = answer_text.strip()

        # Method 1: Exact match
        for i, choice in enumerate(choices):
            if answer_text == choice.strip():
                return i

        # Method 2: Match with prefix patterns (A), B), etc.)
        import re

        prefix_match = re.match(r"^([A-D])\)", answer_text, re.IGNORECASE)
        if prefix_match:
            letter = prefix_match.group(1).upper()
            expected_index = ord(letter) - ord("A")
            if 0 <= expected_index < len(choices):
                return expected_index

        # Method 3: Partial content matching
        answer_lower = answer_text.lower()
        for i, choice in enumerate(choices):
            choice_lower = choice.lower().strip()

            # Remove common prefixes from choice
            choice_content = re.sub(r"^[A-D]\)\s*", "", choice_lower)

            # Check if answer content is in choice or vice versa
            if answer_lower in choice_content or choice_content in answer_lower:
                return i

        # Method 4: Extract content after prefix and match
        answer_content = re.sub(r"^[A-D]\)\s*", "", answer_lower)
        if answer_content:
            for i, choice in enumerate(choices):
                choice_content = re.sub(r"^[A-D]\)\s*", "", choice.lower())
                if answer_content in choice_content or choice_content in answer_content:
                    return i

        # Default to first choice if no match found
        self.logger.warning("Could not find correct answer '%s' in choices: %s", answer_text, choices)
        return 0


class GenerationQuestionHandler(QuestionHandlerBase):
    """Handler for generation question types (gen.json)."""

    def create_qa_entry(self, item: Dict[str, Any]) -> QuestionAnsweringEntry:
        """Create generation QuestionAnsweringEntry.

        Args:
            item: JSON item data with generation structure

        Returns:
            QuestionAnsweringEntry for generation question
        """
        # Extract required fields
        task_id = sanitize_string(item.get("id", "unknown"))
        planning_group = sanitize_string(item.get("group", "unknown"))
        context = sanitize_string(item.get("context", ""))
        question = sanitize_string(item.get("question", ""))
        expected_response = sanitize_string(item.get("expected_response", ""))

        # Create full question with context
        full_question = self._create_full_question(context, question)

        # Analyze planning content
        planning_analysis = self._analyze_planning_content(item)

        # Create metadata
        metadata = {
            "task_id": task_id,
            "planning_group": planning_group,
            "question_type": "generation",
            "domain": "planning_reasoning",
            "original_context": context,
            "response_type": "action_sequence",
            "conversion_strategy": "strategy_2_reasoning_benchmarks",
            "conversion_timestamp": datetime.now(timezone.utc).isoformat(),
            **planning_analysis,
        }

        return QuestionAnsweringEntry(
            question=full_question,
            answer_type="str",
            correct_answer=expected_response,
            choices=[],  # No choices for generation tasks
            metadata=metadata,
        )


class ACPBenchConverter:
    """Main converter class for transforming ACPBench datasets to QuestionAnsweringDataset format.

    Orchestrates JSON parsing, question type handling, planning domain analysis,
    and PyRIT format conversion with comprehensive validation and performance tracking.
    """

    def __init__(self, config: Optional[ACPBenchConversionConfig] = None) -> None:
        """Initialize the ACPBench dataset converter.

        Args:
            config: Conversion configuration settings
        """
        self.config = config or ACPBenchConversionConfig()
        self.domain_classifier = PlanningDomainClassifier()
        self.scenario_analyzer = PlanningScenarioAnalyzer()

        # Initialize question handlers
        self.boolean_handler = BooleanQuestionHandler(self.domain_classifier)
        self.mcq_handler = MultipleChoiceQuestionHandler(self.domain_classifier)
        self.gen_handler = GenerationQuestionHandler(self.domain_classifier)

        # Question type mapping
        self.question_type_handlers = {
            "bool.json": (PlanningQuestionType.BOOLEAN, self.boolean_handler),
            "mcq.json": (PlanningQuestionType.MULTIPLE_CHOICE, self.mcq_handler),
            "gen.json": (PlanningQuestionType.GENERATION, self.gen_handler),
        }

        self.logger = logging.getLogger(__name__)

        # Performance tracking
        self._performance_metrics = {
            "start_time": None,
            "end_time": None,
            "total_questions_processed": 0,
            "files_processed": 0,
            "average_processing_rate": 0.0,
        }

    def convert(self, dataset_path: str, dataset_name: str = "ACPBench_Planning_Reasoning") -> QuestionAnsweringDataset:
        """Convert ACPBench dataset to QuestionAnsweringDataset format.

        Args:
            dataset_path: Path to ACPBench dataset directory
            dataset_name: Name for the converted dataset

        Returns:
            QuestionAnsweringDataset with converted questions

        Raises:
            FileNotFoundError: If dataset directory doesn't exist
            ValueError: If no valid JSON files found
        """
        if not os.path.exists(dataset_path):
            raise FileNotFoundError("Dataset directory not found: %s" % dataset_path)

        start_time = time.time()
        self._performance_metrics["start_time"] = start_time

        all_questions = []
        file_info_list = []
        processing_summary = {}

        # Process each question type file
        for filename, (question_type, handler) in self.question_type_handlers.items():
            file_path = os.path.join(dataset_path, filename)

            if os.path.exists(file_path):
                self.logger.info("Processing %s...", filename)

                file_start_time = time.time()
                questions = self._process_json_file(file_path, handler)
                file_end_time = time.time()

                all_questions.extend(questions)

                # Collect planning groups from this file
                planning_groups = list(set(q.metadata.get("planning_group", "unknown") for q in questions))

                # Create file info
                file_info = ACPBenchFileInfo(
                    file_type=question_type,
                    file_path=file_path,
                    question_count=len(questions),
                    planning_domains=planning_groups,
                    processing_time_seconds=file_end_time - file_start_time,
                    file_size_bytes=os.path.getsize(file_path),
                )
                file_info_list.append(file_info)

                processing_summary[filename] = {
                    "question_count": len(questions),
                    "planning_groups": planning_groups,
                    "processing_time": file_end_time - file_start_time,
                }

                self.logger.info("Processed %d questions from %s", len(questions), filename)

        if not all_questions:
            raise ValueError("No questions were successfully converted from the dataset")

        # Calculate performance metrics
        end_time = time.time()
        total_time = end_time - start_time

        self._performance_metrics.update(
            {
                "end_time": end_time,
                "total_questions_processed": len(all_questions),
                "files_processed": len(file_info_list),
                "average_processing_rate": len(all_questions) / max(total_time, 0.1),
                "total_processing_time": total_time,
            }
        )

        # Create dataset metadata
        dataset_metadata = {
            "total_questions": len(all_questions),
            "question_types": ["boolean", "multiple_choice", "generation"],
            "planning_domains": len(set(q.metadata.get("planning_domain", "unknown") for q in all_questions)),
            "file_summary": processing_summary,
            "conversion_strategy": "strategy_2_reasoning_benchmarks",
            "performance_metrics": self._performance_metrics,
            "conversion_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Create and return the dataset
        dataset = QuestionAnsweringDataset(
            name=dataset_name,
            version="1.0",
            description="Automated planning and logical reasoning tasks across multiple domains from ACPBench-IBM",
            author="ACPBench-IBM",
            group="planning_reasoning",
            source="ACPBench-IBM",
            questions=all_questions,
            metadata=dataset_metadata,
        )

        self.logger.info(
            "Successfully converted %d questions in %.2f seconds (%.1f questions/second)",
            len(all_questions),
            total_time,
            self._performance_metrics["average_processing_rate"],
        )

        return dataset

    def _process_json_file(self, file_path: str, handler: QuestionHandlerBase) -> List[QuestionAnsweringEntry]:
        """Process a single JSON file using the appropriate handler.

        Args:
            file_path: Path to JSON file
            handler: Question handler for this file type

        Returns:
            List of QuestionAnsweringEntry objects
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                content = sanitize_file_content(content)
                data = json.loads(content)

            questions = []

            # Handle both list and single object formats
            items = data if isinstance(data, list) else [data]

            for item in items:
                try:
                    qa_entry = handler.create_qa_entry(item)
                    questions.append(qa_entry)
                except Exception as e:
                    self.logger.warning("Failed to convert item %s: %s", item.get("id", "unknown"), str(e))
                    continue

            return questions

        except Exception as e:
            self.logger.error("Failed to process file %s: %s", file_path, str(e))
            return []

    def validate_conversion(
        self, dataset: QuestionAnsweringDataset, original_file_count: int = 0
    ) -> ConversionValidationResult:
        """Validate conversion quality and compliance.

        Args:
            dataset: Converted dataset to validate
            original_file_count: Number of original files processed

        Returns:
            ConversionValidationResult with validation details
        """
        validation_errors = []
        validation_warnings = []

        # Check dataset structure
        if not dataset.questions:
            validation_errors.append("Dataset contains no questions")

        if not dataset.metadata:
            validation_errors.append("Dataset missing metadata")

        # Validate question entries
        for i, question in enumerate(dataset.questions):
            try:
                # Check required fields
                if not question.question or not question.question.strip():
                    validation_errors.append(f"Question {i} has empty question text")

                if question.answer_type not in ["bool", "int", "str"]:
                    validation_errors.append(f"Question {i} has invalid answer type: {question.answer_type}")

                # Check metadata completeness
                required_metadata = [
                    "task_id",
                    "planning_group",
                    "question_type",
                    "domain",
                    "planning_domain",
                    "conversion_strategy",
                ]

                for field in required_metadata:
                    if field not in question.metadata:
                        validation_errors.append(f"Question {i} missing required metadata: {field}")

                # Type-specific validation
                if question.answer_type == "bool" and not isinstance(question.correct_answer, bool):
                    validation_errors.append(f"Question {i} boolean answer type mismatch")
                elif question.answer_type == "int" and not isinstance(question.correct_answer, int):
                    validation_errors.append(f"Question {i} integer answer type mismatch")
                elif question.answer_type == "str" and not isinstance(question.correct_answer, str):
                    validation_errors.append(f"Question {i} string answer type mismatch")

                # Choice validation for MCQ
                if question.answer_type == "int":
                    if not question.choices:
                        validation_warnings.append(f"Question {i} MCQ has no choices")
                    elif question.correct_answer >= len(question.choices):
                        validation_errors.append(f"Question {i} answer index out of range")

            except Exception as e:
                validation_errors.append(f"Question {i} validation error: {str(e)}")

        # Calculate quality metrics
        total_questions = len(dataset.questions)

        # Context preservation rate (check if questions contain "Context:")
        context_preserved = sum(1 for q in dataset.questions if "Context:" in q.question)
        context_preservation_rate = context_preserved / total_questions if total_questions > 0 else 0.0

        # Metadata completeness
        required_metadata_count = 6  # Number of required metadata fields
        metadata_complete_questions = sum(1 for q in dataset.questions if len(q.metadata) >= required_metadata_count)
        metadata_completeness = metadata_complete_questions / total_questions if total_questions > 0 else 0.0

        # Overall quality score
        error_penalty = min(1.0, len(validation_errors) / 10.0)  # Max 10 errors = 0 quality
        warning_penalty = min(0.5, len(validation_warnings) / 20.0)  # Max 20 warnings = -0.5 quality

        quality_score = max(0.0, 1.0 - error_penalty - warning_penalty)
        quality_score = (quality_score + context_preservation_rate + metadata_completeness) / 3.0

        return ConversionValidationResult(
            is_valid=len(validation_errors) == 0,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
            quality_score=quality_score,
            metadata_completeness=metadata_completeness,
            context_preservation_rate=context_preservation_rate,
        )

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics.

        Returns:
            Dictionary with performance metrics
        """
        return self._performance_metrics.copy()

    def get_supported_file_types(self) -> List[str]:
        """Get list of supported file types.

        Returns:
            List of supported JSON file names
        """
        return list(self.question_type_handlers.keys())
