# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""LegalBench Dataset Converter Implementation (Issue #126).

Implements converter to transform LegalBench dataset from TSV format to PyRIT
QuestionAnsweringDataset format, processing 166 legal reasoning task directories
with professional validation metadata preservation and legal domain classification.

This module supports comprehensive conversion of legal reasoning tasks across
8 primary legal categories with performance targets of <10 minutes for complete
dataset processing and >90% legal classification accuracy.

SECURITY: All content is for defensive security research only. Proper sanitization
and validation is applied to all inputs to prevent injection attacks.
"""

import csv
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import psutil

from app.core.validation import sanitize_string
from app.schemas.legalbench_datasets import (
    LegalBenchBatchConversionResult,
    LegalBenchConversionConfig,
    LegalBenchConversionResult,
    LegalCategory,
    ProfessionalValidation,
    QuestionAnsweringDataset,
    QuestionAnsweringEntry,
    QuestionFormat,
    TaskMetadata,
)
from app.utils.legal_categorization import LegalCategorizationEngine


class LegalQuestionFormatAnalyzer:
    """Analyzer for detecting and handling different legal question formats."""

    def __init__(self) -> None:
        """Initialize the question format analyzer."""
        self.logger = logging.getLogger(__name__)

    def analyze_question_format(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Analyze question format and determine answer structure.

        Args:
            row: TSV row data

        Returns:
            Dictionary containing format analysis results
        """
        question_text = row.get("question", "")
        answer_text = row.get("answer", "")

        # Detect multiple choice format
        if self._is_multiple_choice(row):
            choices, correct_index = self._extract_choices(row)
            return {
                "format_type": QuestionFormat.MULTIPLE_CHOICE,
                "answer_type": "int",
                "correct_answer": correct_index,
                "choices": choices,
                "question_text": self._format_multiple_choice_question(question_text, choices),
            }

        # Detect binary (Yes/No) format
        if self._is_binary_question(answer_text):
            return {
                "format_type": QuestionFormat.BINARY,
                "answer_type": "str",
                "correct_answer": sanitize_string(answer_text).strip(),
                "choices": None,
                "question_text": question_text,
            }

        # Detect explanation format
        if self._is_explanation_format(row):
            return {
                "format_type": QuestionFormat.EXPLANATION,
                "answer_type": "str",
                "correct_answer": sanitize_string(answer_text).strip(),
                "choices": None,
                "question_text": self._format_explanation_question(row),
            }

        # Default to short answer format
        return {
            "format_type": QuestionFormat.SHORT_ANSWER,
            "answer_type": "str",
            "correct_answer": sanitize_string(answer_text).strip(),
            "choices": None,
            "question_text": question_text,
        }

    def _is_multiple_choice(self, row: Dict[str, str]) -> bool:
        """Check if question is multiple choice format."""
        # Look for choice columns (A, B, C, D or similar)
        choice_columns = [col for col in row.keys() if col.upper() in ["A", "B", "C", "D", "E", "F"]]
        if len(choice_columns) >= 2:
            return True

        # Look for choices in question text
        question = row.get("question", "")
        if re.search(r"\([A-F]\)|\b[A-F]\.|\b[A-F]\)", question):
            return True

        # Look for "options" or "choices" column
        return any(col.lower() in ["options", "choices", "alternatives"] for col in row.keys())

    def _is_binary_question(self, answer_text: str) -> bool:
        """Check if question expects binary answer."""
        answer = sanitize_string(answer_text).strip().lower()
        binary_answers = {"yes", "no", "true", "false", "correct", "incorrect", "valid", "invalid"}
        return answer in binary_answers

    def _is_explanation_format(self, row: Dict[str, str]) -> bool:
        """Check if question requires explanation format."""
        # Look for explanation-related columns
        explanation_columns = ["explanation", "reasoning", "rationale", "analysis", "justification"]
        return any(col.lower() in explanation_columns for col in row.keys())

    def _extract_choices(self, row: Dict[str, str]) -> Tuple[List[str], int]:
        """Extract multiple choice options and correct answer index."""
        choices = []
        correct_answer = row.get("answer", "").strip()

        # Try to find choice columns
        choice_columns = sorted([col for col in row.keys() if col.upper() in ["A", "B", "C", "D", "E", "F"]])

        if choice_columns:
            for col in choice_columns:
                choice_text = sanitize_string(row.get(col, "")).strip()
                if choice_text:
                    choices.append(choice_text)

            # Find correct answer index
            correct_index = 0
            if correct_answer.upper() in ["A", "B", "C", "D", "E", "F"]:
                correct_index = ord(correct_answer.upper()) - ord("A")
            else:
                # Try to match answer text with choices
                for i, choice in enumerate(choices):
                    if correct_answer.lower() in choice.lower():
                        correct_index = i
                        break

            return choices, min(correct_index, len(choices) - 1)

        # Fallback: extract from question text
        question = row.get("question", "")
        choice_pattern = r"\([A-F]\)\s*([^(]+?)(?=\([A-F]\)|$)"
        matches = re.findall(choice_pattern, question)

        if matches:
            choices = [sanitize_string(match).strip() for match in matches]
            # Try to determine correct answer
            correct_index = 0
            if correct_answer.upper() in ["A", "B", "C", "D", "E", "F"]:
                correct_index = ord(correct_answer.upper()) - ord("A")

            return choices, min(correct_index, len(choices) - 1)

        # Final fallback: create binary choices
        return ["Yes", "No"], 0 if correct_answer.lower() in ["yes", "true", "correct"] else 1

    def _format_multiple_choice_question(self, question_text: str, choices: List[str]) -> str:
        """Format question with multiple choice options."""
        formatted_question = sanitize_string(question_text).strip()

        if not formatted_question.endswith("?"):
            formatted_question += "?"

        formatted_question += "\n\nChoices:"
        for i, choice in enumerate(choices):
            letter = chr(ord("A") + i)
            formatted_question += f"\n({letter}) {choice}"

        return formatted_question

    def _format_explanation_question(self, row: Dict[str, str]) -> str:
        """Format question that requires explanation."""
        question = sanitize_string(row.get("question", "")).strip()

        # Add context from other fields
        context_fields = ["text", "context", "scenario", "case_facts", "regulation_text"]
        context_parts = []

        for field in context_fields:
            if field in row and row[field].strip():
                context_text = sanitize_string(row[field]).strip()
                if len(context_text) > 20:  # Only include substantial context
                    context_parts.append(f"{field.replace('_', ' ').title()}: {context_text}")

        if context_parts:
            formatted_question = "\n\n".join(context_parts) + "\n\nQuestion: " + question
        else:
            formatted_question = question

        if not formatted_question.endswith("?"):
            formatted_question += "?"

        return formatted_question


class TSVProcessor:
    """Processor for handling TSV files with legal domain awareness."""

    def __init__(self) -> None:
        """Initialize the TSV processor."""
        self.logger = logging.getLogger(__name__)
        self.format_analyzer = LegalQuestionFormatAnalyzer()

    def process_tsv_file(self, file_path: str, task_name: str, split: str) -> List[Dict[str, Any]]:
        """Process single TSV file and extract structured data.

        Args:
            file_path: Path to TSV file
            task_name: Legal task name
            split: Train or test split

        Returns:
            List of processed row data
        """
        if not os.path.exists(file_path):
            self.logger.warning("TSV file not found: %s", file_path)
            return []

        processed_rows = []

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                # Detect delimiter and field structure
                sample = f.read(1024)
                f.seek(0)

                delimiter = self._detect_delimiter(sample)
                reader = csv.DictReader(f, delimiter=delimiter)

                for row_num, row in enumerate(reader):
                    try:
                        processed_row = self._process_row(row, task_name, split, row_num, file_path)
                        processed_rows.append(processed_row)
                    except Exception as e:
                        self.logger.warning("Failed to process row %d in %s: %s", row_num, file_path, e)
                        continue

        except Exception as e:
            self.logger.error("Failed to read TSV file %s: %s", file_path, e)
            return []

        self.logger.info("Processed %d rows from %s", len(processed_rows), file_path)
        return processed_rows

    def _detect_delimiter(self, sample: str) -> str:
        """Detect delimiter used in TSV/CSV file."""
        tab_count = sample.count("\t")
        comma_count = sample.count(",")
        semicolon_count = sample.count(";")

        # Choose delimiter with highest count
        if tab_count >= comma_count and tab_count >= semicolon_count:
            return "\t"
        elif comma_count >= semicolon_count:
            return ","
        else:
            return ";"

    def _process_row(
        self, row: Dict[str, str], task_name: str, split: str, row_num: int, file_path: str
    ) -> Dict[str, Any]:
        """Process individual TSV row into structured data.

        Args:
            row: Raw CSV row data
            task_name: Legal task name
            split: Train or test split
            row_num: Row number
            file_path: Source file path

        Returns:
            Processed row data with format analysis
        """
        # Analyze question format
        format_info = self.format_analyzer.analyze_question_format(row)

        # Extract legal context
        legal_context = self._extract_legal_context(row)

        return {
            "raw_row": row,
            "task_name": task_name,
            "split": split,
            "row_number": row_num,
            "source_file": file_path,
            "format_info": format_info,
            "legal_context": legal_context,
            "processing_timestamp": datetime.now(timezone.utc),
        }

    def _extract_legal_context(self, row: Dict[str, str]) -> Dict[str, str]:
        """Extract legal context information from row data.

        Args:
            row: Raw CSV row data

        Returns:
            Dictionary of legal context information
        """
        context = {}

        # Standard legal context fields
        context_fields = {
            "case_reference": ["case_reference", "case_id", "case_name"],
            "regulation_reference": ["regulation_reference", "reg_ref", "cfr_reference"],
            "statute_reference": ["statute_reference", "statute", "code_section"],
            "precedent_reference": ["precedent_reference", "precedent", "case_law"],
            "legal_principle": ["legal_principle", "principle", "doctrine"],
            "jurisdiction": ["jurisdiction", "court", "venue"],
            "practice_area": ["practice_area", "area_of_law", "legal_area"],
        }

        for context_key, possible_columns in context_fields.items():
            for col in possible_columns:
                if col in row and row[col].strip():
                    context[context_key] = sanitize_string(row[col]).strip()
                    break

        return context


class LegalBenchDatasetConverter:
    """Main converter class for transforming LegalBench datasets to QuestionAnsweringDataset format.

    Orchestrates directory traversal, TSV processing, legal classification, and
    QuestionAnsweringEntry generation with comprehensive validation and professional metadata.
    """

    def __init__(self, config: Optional[LegalBenchConversionConfig] = None) -> None:
        """Initialize the LegalBench dataset converter.

        Args:
            config: Conversion configuration settings
        """
        self.config = config or LegalBenchConversionConfig()
        self.legal_engine = LegalCategorizationEngine()
        self.tsv_processor = TSVProcessor()
        self.logger = logging.getLogger(__name__)

        # Performance tracking with explicit types
        self._conversion_stats: Dict[str, Union[int, float, Dict[str, int], None]] = {
            "total_processed": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "total_qa_entries": 0,
            "start_time": None,
            "peak_memory_mb": 0.0,
            "directories_found": 0,
            "legal_categories": {},
        }

    def convert(self, dataset_root: str) -> LegalBenchBatchConversionResult:
        """Convert complete LegalBench dataset across all directories.

        Args:
            dataset_root: Root directory containing 166 legal task directories

        Returns:
            Complete batch conversion result
        """
        self.logger.info("Starting LegalBench conversion from: %s", dataset_root)
        self._conversion_stats["start_time"] = time.time()

        # Discover task directories
        task_directories = self._discover_task_directories(dataset_root)
        self._conversion_stats["directories_found"] = len(task_directories)

        if not task_directories:
            raise ValueError(f"No legal task directories found in: {dataset_root}")

        self.logger.info("Found %d legal task directories to process", len(task_directories))

        # Process directories (parallel or sequential based on config)
        conversion_results = self._process_task_directories(dataset_root, task_directories)

        # Aggregate all questions from successful conversions
        all_questions: List[QuestionAnsweringEntry] = []
        legal_category_summary: Dict[LegalCategory, int] = {}

        for result in conversion_results:
            if result.success:
                self._update_category_summary(legal_category_summary, result.legal_category)

                # Re-process the successful task to get actual questions
                task_dir_name = result.task_name
                task_path = os.path.join(dataset_root, task_dir_name)

                try:
                    # Process train and test splits for this task
                    train_questions = self._process_task_split(task_path, task_dir_name, "train")
                    test_questions = self._process_task_split(task_path, task_dir_name, "test")

                    all_questions.extend(train_questions)
                    all_questions.extend(test_questions)

                    self.logger.debug(
                        "Added %d train + %d test questions from %s",
                        len(train_questions),
                        len(test_questions),
                        task_dir_name,
                    )

                except Exception as e:
                    self.logger.warning("Failed to re-process questions for %s: %s", task_dir_name, e)
                    continue

        # Create dataset
        dataset = self._create_dataset(all_questions, conversion_results)

        # Calculate final statistics
        start_time = self._conversion_stats["start_time"]
        if start_time is not None and isinstance(start_time, (int, float)):
            total_time = int((time.time() - start_time) * 1000)
        else:
            total_time = 0

        successful_conversions = self._conversion_stats["successful_conversions"]
        total_processed = self._conversion_stats["total_processed"]

        if isinstance(successful_conversions, int) and isinstance(total_processed, int):
            success_rate = successful_conversions / max(total_processed, 1)
        else:
            success_rate = 0.0

        return LegalBenchBatchConversionResult(
            dataset=dataset,
            conversion_results=conversion_results,
            processing_stats=self._conversion_stats.copy(),
            legal_category_summary=legal_category_summary,
            total_processing_time_ms=total_time,
            success_rate=success_rate,
        )

    def _discover_task_directories(self, dataset_root: str) -> List[str]:
        """Discover all legal task directories in the dataset root.

        Args:
            dataset_root: Root directory path

        Returns:
            List of task directory names
        """
        if not os.path.exists(dataset_root):
            raise FileNotFoundError(f"Dataset root directory not found: {dataset_root}")

        task_directories = []

        try:
            for item in os.listdir(dataset_root):
                item_path = os.path.join(dataset_root, item)
                if os.path.isdir(item_path):
                    # Check if directory contains TSV files
                    if self._has_legal_task_files(item_path):
                        task_directories.append(item)

        except Exception as e:
            self.logger.error("Failed to discover task directories: %s", e)
            return []

        return sorted(task_directories)

    def _has_legal_task_files(self, directory_path: str) -> bool:
        """Check if directory contains legal task files (train.tsv, test.tsv, etc.).

        Args:
            directory_path: Directory to check

        Returns:
            True if directory contains legal task files
        """
        required_files = ["train.tsv", "test.tsv"]
        optional_files = ["train.csv", "test.csv", "data.tsv", "data.csv"]

        existing_files = []
        try:
            existing_files = os.listdir(directory_path)
        except Exception:
            return False

        # Check for required files
        has_required = any(file in existing_files for file in required_files)

        # Check for optional files if no required files
        has_optional = any(file in existing_files for file in optional_files)

        return has_required or has_optional

    def _process_task_directories(
        self, dataset_root: str, task_directories: List[str]
    ) -> List[LegalBenchConversionResult]:
        """Process all task directories to generate conversion results.

        Args:
            dataset_root: Root directory path
            task_directories: List of task directory names

        Returns:
            List of conversion results
        """
        conversion_results = []

        if self.config.parallel_processing and len(task_directories) > 2:
            conversion_results = self._process_directories_parallel(dataset_root, task_directories)
        else:
            conversion_results = self._process_directories_sequential(dataset_root, task_directories)

        return conversion_results

    def _process_directories_sequential(
        self, dataset_root: str, task_directories: List[str]
    ) -> List[LegalBenchConversionResult]:
        """Process task directories sequentially.

        Args:
            dataset_root: Root directory path
            task_directories: List of task directory names

        Returns:
            List of conversion results
        """
        conversion_results: List[LegalBenchConversionResult] = []

        for task_dir in task_directories:
            if self.config.enable_progress_tracking and len(conversion_results) % 10 == 0:
                self.logger.info(
                    "Processing directory %d/%d: %s", len(conversion_results) + 1, len(task_directories), task_dir
                )

            try:
                result = self._process_single_task_directory(dataset_root, task_dir)
                conversion_results.append(result)

                if result.success:
                    successful_conversions = self._conversion_stats["successful_conversions"]
                    if isinstance(successful_conversions, int):
                        self._conversion_stats["successful_conversions"] = successful_conversions + 1
                    else:
                        self._conversion_stats["successful_conversions"] = 1
                else:
                    failed_conversions = self._conversion_stats["failed_conversions"]
                    if isinstance(failed_conversions, int):
                        self._conversion_stats["failed_conversions"] = failed_conversions + 1
                    else:
                        self._conversion_stats["failed_conversions"] = 1

            except Exception as e:
                self.logger.error("Failed to process directory %s: %s", task_dir, e)
                conversion_results.append(
                    LegalBenchConversionResult(
                        task_name=task_dir,
                        success=False,
                        questions_generated=0,
                        legal_category=LegalCategory.GENERAL,
                        specializations=[],
                        processing_time_ms=0,
                        error_message=str(e),
                    )
                )
                failed_conversions = self._conversion_stats["failed_conversions"]
                if isinstance(failed_conversions, int):
                    self._conversion_stats["failed_conversions"] = failed_conversions + 1
                else:
                    self._conversion_stats["failed_conversions"] = 1

            total_processed = self._conversion_stats["total_processed"]
            if isinstance(total_processed, int):
                self._conversion_stats["total_processed"] = total_processed + 1
            else:
                self._conversion_stats["total_processed"] = 1

            # Update peak memory usage
            current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            peak_memory = self._conversion_stats["peak_memory_mb"]
            if isinstance(peak_memory, (int, float)):
                self._conversion_stats["peak_memory_mb"] = max(peak_memory, current_memory)
            else:
                self._conversion_stats["peak_memory_mb"] = current_memory

        return conversion_results

    def _process_directories_parallel(
        self, dataset_root: str, task_directories: List[str]
    ) -> List[LegalBenchConversionResult]:
        """Process task directories in parallel.

        Args:
            dataset_root: Root directory path
            task_directories: List of task directory names

        Returns:
            List of conversion results
        """
        conversion_results = []

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._process_single_task_directory, dataset_root, task_dir): task_dir
                for task_dir in task_directories
            }

            # Collect results as they complete
            for future in as_completed(future_to_task):
                task_dir = future_to_task[future]

                try:
                    result = future.result()
                    conversion_results.append(result)

                    if result.success:
                        successful_conversions = self._conversion_stats["successful_conversions"]
                        if isinstance(successful_conversions, int):
                            self._conversion_stats["successful_conversions"] = successful_conversions + 1
                        else:
                            self._conversion_stats["successful_conversions"] = 1
                    else:
                        failed_conversions = self._conversion_stats["failed_conversions"]
                        if isinstance(failed_conversions, int):
                            self._conversion_stats["failed_conversions"] = failed_conversions + 1
                        else:
                            self._conversion_stats["failed_conversions"] = 1

                except Exception as e:
                    self.logger.error("Failed to process directory %s: %s", task_dir, e)
                    conversion_results.append(
                        LegalBenchConversionResult(
                            task_name=task_dir,
                            success=False,
                            questions_generated=0,
                            legal_category=LegalCategory.GENERAL,
                            specializations=[],
                            processing_time_ms=0,
                            error_message=str(e),
                        )
                    )
                    failed_conversions = self._conversion_stats["failed_conversions"]
                    if isinstance(failed_conversions, int):
                        self._conversion_stats["failed_conversions"] = failed_conversions + 1
                    else:
                        self._conversion_stats["failed_conversions"] = 1

                total_processed = self._conversion_stats["total_processed"]
                if isinstance(total_processed, int):
                    self._conversion_stats["total_processed"] = total_processed + 1
                else:
                    self._conversion_stats["total_processed"] = 1

                total_processed = self._conversion_stats["total_processed"]
                if (
                    self.config.enable_progress_tracking
                    and isinstance(total_processed, int)
                    and total_processed % 20 == 0
                ):
                    self.logger.info(
                        "Processed %d/%d directories", self._conversion_stats["total_processed"], len(task_directories)
                    )

        return conversion_results

    def _process_single_task_directory(self, dataset_root: str, task_dir: str) -> LegalBenchConversionResult:
        """Process single legal task directory.

        Args:
            dataset_root: Root directory path
            task_dir: Task directory name

        Returns:
            Conversion result for this task
        """
        start_time = time.time()
        task_path = os.path.join(dataset_root, task_dir)

        try:
            # Classify legal domain
            legal_classification = self.legal_engine.classify_legal_task(task_dir)

            # Process train and test files
            train_questions = self._process_task_split(task_path, task_dir, "train")
            test_questions = self._process_task_split(task_path, task_dir, "test")

            total_questions = len(train_questions) + len(test_questions)
            processing_time = int((time.time() - start_time) * 1000)

            # Update statistics
            total_qa_entries = self._conversion_stats["total_qa_entries"]
            if isinstance(total_qa_entries, int):
                self._conversion_stats["total_qa_entries"] = total_qa_entries + total_questions
            else:
                self._conversion_stats["total_qa_entries"] = total_questions
            self._update_category_stats(legal_classification.primary_category)

            return LegalBenchConversionResult(
                task_name=task_dir,
                success=True,
                questions_generated=total_questions,
                legal_category=legal_classification.primary_category,
                specializations=[spec.area for spec in legal_classification.specializations],
                processing_time_ms=processing_time,
                warnings=self.legal_engine.validate_legal_classification(legal_classification),
            )

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            self.logger.error("Failed to process task directory %s: %s", task_dir, e)

            return LegalBenchConversionResult(
                task_name=task_dir,
                success=False,
                questions_generated=0,
                legal_category=LegalCategory.GENERAL,
                specializations=[],
                processing_time_ms=processing_time,
                error_message=str(e),
            )

    def _process_task_split(self, task_path: str, task_name: str, split: str) -> List[QuestionAnsweringEntry]:
        """Process train or test split for a task.

        Args:
            task_path: Path to task directory
            task_name: Task directory name
            split: "train" or "test"

        Returns:
            List of QuestionAnsweringEntry objects
        """
        file_path = os.path.join(task_path, f"{split}.tsv")

        # Try CSV if TSV doesn't exist
        if not os.path.exists(file_path):
            file_path = os.path.join(task_path, f"{split}.csv")

        if not os.path.exists(file_path):
            self.logger.warning("No %s file found for task %s", split, task_name)
            return []

        # Process TSV file
        processed_rows = self.tsv_processor.process_tsv_file(file_path, task_name, split)

        # Convert to QuestionAnsweringEntry objects
        questions = []
        for row_data in processed_rows:
            try:
                qa_entry = self._create_question_answering_entry(row_data)
                questions.append(qa_entry)
            except Exception as e:
                self.logger.warning("Failed to create Q&A entry for %s/%s: %s", task_name, split, e)
                continue

        return questions

    def _create_question_answering_entry(self, row_data: Dict[str, Any]) -> QuestionAnsweringEntry:
        """Create QuestionAnsweringEntry from processed row data.

        Args:
            row_data: Processed row data from TSV

        Returns:
            QuestionAnsweringEntry object
        """
        format_info = row_data["format_info"]
        task_name = row_data["task_name"]

        # Classify legal domain for this task
        legal_classification = self.legal_engine.classify_legal_task(task_name, row_data["raw_row"])

        # Create professional validation metadata
        professional_validation = ProfessionalValidation(
            expertise_areas=self.legal_engine.get_legal_expertise_areas(task_name)
        )

        # Create task metadata
        task_metadata = TaskMetadata(
            task_name=task_name,
            task_id=f"{task_name}_{row_data['split']}_{row_data['row_number']}",
            legal_classification=legal_classification,
            split=row_data["split"],
            row_number=row_data["row_number"],
            professional_validation=professional_validation,
            question_format=format_info["format_type"],
            legal_context=row_data["legal_context"],
            source_file=row_data["source_file"],
            processing_timestamp=row_data["processing_timestamp"],
        )

        return QuestionAnsweringEntry(
            question=format_info["question_text"],
            answer_type=format_info["answer_type"],
            correct_answer=format_info["correct_answer"],
            choices=format_info["choices"],
            metadata=task_metadata,
        )

    def _create_dataset(
        self, all_questions: List[QuestionAnsweringEntry], conversion_results: List[LegalBenchConversionResult]
    ) -> QuestionAnsweringDataset:
        """Create complete QuestionAnsweringDataset from all questions.

        Args:
            all_questions: All converted Q&A entries
            conversion_results: Individual task conversion results

        Returns:
            Complete dataset
        """
        # Calculate summary statistics
        successful_tasks = [r for r in conversion_results if r.success]
        failed_tasks = [r for r in conversion_results if not r.success]

        # Aggregate legal categories
        category_counts: Dict[str, int] = {}
        for result in successful_tasks:
            category = result.legal_category.value
            category_counts[category] = category_counts.get(category, 0) + 1

        dataset_metadata = {
            "total_tasks": len(conversion_results),
            "successful_tasks": len(successful_tasks),
            "failed_tasks": len(failed_tasks),
            "professional_validation": True,
            "validator_count": "40+",
            "task_summary": {
                result.task_name: {
                    "success": result.success,
                    "questions_generated": result.questions_generated,
                    "legal_category": result.legal_category.value,
                    "specializations": result.specializations,
                    "processing_time_ms": result.processing_time_ms,
                }
                for result in conversion_results
            },
            "legal_categories": list(category_counts.keys()),
            "category_distribution": category_counts,
            "conversion_strategy": "legal_reasoning_multi_directory",
            "processing_stats": self._conversion_stats.copy(),
            "failed_task_names": [r.task_name for r in failed_tasks],
            "warnings": [warning for result in conversion_results for warning in result.warnings],
        }

        return QuestionAnsweringDataset(
            name="LegalBench_Professional_Legal_Reasoning",
            version="1.0",
            description="Professional-validated legal reasoning dataset across 162+ tasks covering 8 legal domains",
            author="Stanford University + Legal Professionals",
            group="legal_reasoning",
            source="LegalBench-Stanford",
            questions=all_questions,
            metadata=dataset_metadata,
        )

    def _update_category_summary(self, summary: Dict[LegalCategory, int], category: LegalCategory) -> None:
        """Update legal category summary statistics."""
        summary[category] = summary.get(category, 0) + 1

    def _update_category_stats(self, category: LegalCategory) -> None:
        """Update internal category statistics."""
        cat_name = category.value
        legal_categories = self._conversion_stats["legal_categories"]
        if isinstance(legal_categories, dict):
            legal_categories[cat_name] = legal_categories.get(cat_name, 0) + 1

    def get_conversion_statistics(self) -> Dict[str, Any]:
        """Get current conversion statistics.

        Returns:
            Dictionary of conversion statistics
        """
        stats = self._conversion_stats.copy()

        start_time = stats["start_time"]
        if start_time is not None and isinstance(start_time, (int, float)):
            stats["elapsed_time_seconds"] = time.time() - start_time

        total_processed = stats["total_processed"]
        if isinstance(total_processed, int) and total_processed > 0:
            successful_conversions = stats["successful_conversions"]
            total_qa_entries = stats["total_qa_entries"]

            if isinstance(successful_conversions, int):
                stats["success_rate"] = successful_conversions / total_processed

                if isinstance(total_qa_entries, int) and successful_conversions > 0:
                    stats["questions_per_task_avg"] = total_qa_entries / successful_conversions
                else:
                    stats["questions_per_task_avg"] = 0

        return stats
