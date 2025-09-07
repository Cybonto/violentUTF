# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""OllaGen1 Dataset Converter Implementation (Issue #123).

Implements Strategy 1 converter to transform OllaGen1 cognitive behavioral
assessment data into PyRIT QuestionAnsweringDataset format, converting 1 CSV row
into 4 QuestionAnsweringEntry objects with preserved metadata and scenario relationships.

This module supports comprehensive conversion of 169,999 scenarios to 679,996 Q&A entries
with performance targets of <10 minutes conversion time and >95% accuracy.

SECURITY: All content is for defensive security research only. Proper sanitization
and validation is applied to all inputs to prevent injection attacks.
"""

import asyncio
import csv
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import psutil
from app.core.validation import sanitize_string
from app.schemas.ollegen1_datasets import (
    OllaGen1BatchConversionResult,
    OllaGen1ConversionConfig,
    OllaGen1ConversionResult,
    OllaGen1ManifestInfo,
    PersonProfile,
    QuestionAnsweringEntry,
    ScenarioMetadata,
)
from app.utils.qa_utils import (
    AnswerMapper,
    FormatValidator,
    MetadataValidator,
    MultipleChoiceParser,
    QAValidator,
    QuestionTypeHandler,
)


class OllaGen1DatasetConverter:
    """Main converter class for transforming OllaGen1 datasets to QuestionAnsweringDataset format.

    Orchestrates CSV parsing, question type handling, multiple choice extraction,
    and QuestionAnsweringEntry generation with comprehensive validation.
    """

    def __init__(self, config: Optional[OllaGen1ConversionConfig] = None) -> None:
        """Initialize the OllaGen1 dataset converter.

        Args:
            config: Conversion configuration settings
        """
        self.config = config or OllaGen1ConversionConfig()
        self.choice_parser = MultipleChoiceParser()
        self.answer_mapper = AnswerMapper()
        self.question_handler = QuestionTypeHandler()
        self.qa_validator = QAValidator()
        self.format_validator = FormatValidator()
        self.metadata_validator = MetadataValidator()

        # Performance tracking
        self._conversion_stats = {
            "total_processed": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "total_qa_entries": 0,
            "start_time": None,
            "peak_memory_mb": 0,
        }

    def load_manifest(self, manifest_path: str) -> OllaGen1ManifestInfo:
        """Load and parse manifest file for split file processing.

        Args:
            manifest_path: Path to the manifest file

        Returns:
            Parsed manifest information

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            ValueError: If manifest format is invalid
        """
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                if manifest_path.endswith(".json"):
                    manifest_data = json.load(f)
                else:
                    # Support for YAML manifests if needed
                    try:
                        import yaml

                        manifest_data = yaml.safe_load(f)
                    except ImportError as exc:
                        raise ValueError(
                            "YAML support not available. Install PyYAML for YAML manifest support."
                        ) from exc

            return OllaGen1ManifestInfo(**manifest_data)

        except (json.JSONDecodeError, Exception) as e:
            # Handle both JSON decode errors and YAML errors if yaml is available
            if hasattr(e, "problem"):  # YAML error
                raise ValueError(f"Invalid YAML manifest file format: {e}") from e
            else:
                raise ValueError(f"Invalid manifest file format: {e}") from e

    def parse_csv_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Parse a single CSV row into structured data.

        Args:
            row: CSV row data as dictionary

        Returns:
            Structured data with scenario metadata, person profiles, and question data
        """
        try:
            # Extract person profiles
            person_1 = PersonProfile(
                name=sanitize_string(row.get("P1_name", "")),
                cognitive_path=sanitize_string(row.get("P1_cogpath", "")),
                profile=sanitize_string(row.get("P1_profile", "")),
                risk_score=float(row.get("P1_risk_score", 0)),
                risk_profile=sanitize_string(row.get("P1_risk_profile", "")),
            )

            person_2 = PersonProfile(
                name=sanitize_string(row.get("P2_name", "")),
                cognitive_path=sanitize_string(row.get("P2_cogpath", "")),
                profile=sanitize_string(row.get("P2_profile", "")),
                risk_score=float(row.get("P2_risk_score", 0)),
                risk_profile=sanitize_string(row.get("P2_risk_profile", "")),
            )

            # Extract scenario metadata
            scenario_metadata = ScenarioMetadata(
                scenario_id=sanitize_string(row.get("ID", "")),
                person_1=person_1,
                person_2=person_2,
                shared_risk_factor=sanitize_string(row.get("shared_risk_factor", "")),
                targeted_factor=sanitize_string(row.get("targetted_factor", "")),
                combined_risk_score=float(row.get("combined_risk_score", 0)),
                conversion_timestamp=datetime.now(timezone.utc),
            )

            # Extract question data
            question_data = []
            for q_type in ["WCP", "WHO", "TeamRisk", "TargetFactor"]:
                question_key = f"{q_type}_Question"
                answer_key = f"{q_type}_Answer"

                if question_key in row and answer_key in row:
                    question_data.append(
                        {
                            "type": q_type,
                            "question": sanitize_string(row[question_key]),
                            "answer": sanitize_string(row[answer_key]),
                        }
                    )

            return {
                "scenario_metadata": scenario_metadata,
                "person_profiles": [person_1, person_2],
                "question_data": question_data,
            }

        except Exception as e:
            raise ValueError(f"Error parsing CSV row: {e}") from e

    def get_question_handlers(self) -> Dict[str, QuestionTypeHandler]:
        """Get question type handlers for different question types.

        Returns:
            Dictionary of question type handlers
        """
        return {
            "WCP": self.question_handler,
            "WHO": self.question_handler,
            "TeamRisk": self.question_handler,
            "TargetFactor": self.question_handler,
        }

    def create_qa_entry(
        self, question_text: str, answer_text: str, question_type: str, scenario_metadata: ScenarioMetadata
    ) -> QuestionAnsweringEntry:
        """Create a single QuestionAnsweringEntry from question data.

        Args:
            question_text: Question text with multiple choice options
            answer_text: Answer text to map to choice index
            question_type: Type of question (WCP, WHO, etc.)
            scenario_metadata: Complete scenario metadata

        Returns:
            QuestionAnsweringEntry object

        Raises:
            ValueError: If question processing fails
        """
        # Process question with type-specific handler
        processed = self.question_handler.process_question(question_type, question_text, answer_text)

        if not processed["processing_successful"]:
            raise ValueError(f"Failed to process {question_type} question: extraction or mapping failed")

        # Create metadata for the Q&A entry
        qa_metadata = {
            "scenario_id": scenario_metadata.scenario_id,
            "question_type": question_type,
            "category": processed["category"],
            "person_1": {
                "name": scenario_metadata.person_1.name,
                "cognitive_path": scenario_metadata.person_1.cognitive_path,
                "profile": scenario_metadata.person_1.profile,
                "risk_score": scenario_metadata.person_1.risk_score,
                "risk_profile": scenario_metadata.person_1.risk_profile,
            },
            "person_2": {
                "name": scenario_metadata.person_2.name,
                "cognitive_path": scenario_metadata.person_2.cognitive_path,
                "profile": scenario_metadata.person_2.profile,
                "risk_score": scenario_metadata.person_2.risk_score,
                "risk_profile": scenario_metadata.person_2.risk_profile,
            },
            "shared_risk_factor": scenario_metadata.shared_risk_factor,
            "targeted_factor": scenario_metadata.targeted_factor,
            "combined_risk_score": scenario_metadata.combined_risk_score,
            "conversion_timestamp": scenario_metadata.conversion_timestamp.isoformat(),
            "conversion_strategy": scenario_metadata.conversion_strategy,
            "extraction_confidence": processed["extraction_confidence"],
            "mapping_confidence": processed["mapping_confidence"],
        }

        return QuestionAnsweringEntry(
            question=processed["question_text"],
            answer_type="int",
            correct_answer=processed["correct_answer"],
            choices=processed["choices"],
            metadata=qa_metadata,
        )

    def convert_csv_row_to_qa_entries(self, row: Dict[str, str]) -> List[QuestionAnsweringEntry]:
        """Convert a single CSV row to 4 QuestionAnsweringEntry objects.

        Args:
            row: CSV row data

        Returns:
            List of 4 QuestionAnsweringEntry objects (one for each question type)
        """
        # Parse the CSV row
        parsed_data = self.parse_csv_row(row)
        scenario_metadata = parsed_data["scenario_metadata"]
        question_data = parsed_data["question_data"]

        qa_entries = []

        # Create Q&A entry for each question type
        for question_info in question_data:
            try:
                qa_entry = self.create_qa_entry(
                    question_text=question_info["question"],
                    answer_text=question_info["answer"],
                    question_type=question_info["type"],
                    scenario_metadata=scenario_metadata,
                )
                qa_entries.append(qa_entry)
            except ValueError as e:
                # Log error but continue with other questions
                logging.warning("Failed to create Q&A entry for %s: %s", question_info["type"], e)
                continue

        return qa_entries

    def batch_convert_rows(self, rows: List[Dict[str, str]]) -> List[QuestionAnsweringEntry]:
        """Convert multiple CSV rows in batch.

        Args:
            rows: List of CSV row dictionaries

        Returns:
            List of all generated QuestionAnsweringEntry objects
        """
        all_qa_entries = []

        for row in rows:
            try:
                qa_entries = self.convert_csv_row_to_qa_entries(row)
                all_qa_entries.extend(qa_entries)
                self._conversion_stats["successful_conversions"] += 1
                self._conversion_stats["total_qa_entries"] += len(qa_entries)
            except Exception as e:
                self._conversion_stats["failed_conversions"] += 1
                logging.warning("Failed to convert row %s: %s", row.get("ID", "unknown"), e)
                continue

            self._conversion_stats["total_processed"] += 1

        return all_qa_entries

    async def async_batch_convert(self, rows: List[Dict[str, str]]) -> List[QuestionAnsweringEntry]:
        """Convert multiple CSV rows asynchronously.

        Args:
            rows: List of CSV row dictionaries

        Returns:
            List of all generated QuestionAnsweringEntry objects
        """
        # Split into batches for processing
        batch_size = self.config.batch_size
        batches = [rows[i : i + batch_size] for i in range(0, len(rows), batch_size)]

        # Process batches concurrently
        tasks = []
        for batch in batches:
            task = asyncio.create_task(self._process_batch_async(batch))
            tasks.append(task)

        batch_results = await asyncio.gather(*tasks)

        # Flatten results
        all_qa_entries = []
        for batch_result in batch_results:
            all_qa_entries.extend(batch_result)

        return all_qa_entries

    async def _process_batch_async(self, batch: List[Dict[str, str]]) -> List[QuestionAnsweringEntry]:
        """Process a single batch of rows asynchronously.

        Args:
            batch: Batch of CSV rows to process

        Returns:
            List of QuestionAnsweringEntry objects from the batch
        """
        # Run batch processing in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.batch_convert_rows, batch)

    async def async_batch_convert_with_progress(
        self, rows: List[Dict[str, str]], progress_callback: Optional[callable] = None
    ) -> List[QuestionAnsweringEntry]:
        """Convert with real-time progress tracking.

        Args:
            rows: List of CSV row dictionaries
            progress_callback: Callback function for progress updates

        Returns:
            List of all generated QuestionAnsweringEntry objects
        """
        total_rows = len(rows)
        processed_rows = 0
        all_qa_entries = []

        batch_size = self.config.batch_size
        start_time = time.time()

        for i in range(0, total_rows, batch_size):
            batch = rows[i : i + batch_size]

            # Process batch
            batch_results = await self._process_batch_async(batch)
            all_qa_entries.extend(batch_results)

            # Update progress
            processed_rows += len(batch)
            elapsed_time = time.time() - start_time

            if progress_callback and processed_rows > 0:
                # Calculate ETA
                rate = processed_rows / elapsed_time
                remaining_rows = total_rows - processed_rows
                eta_seconds = remaining_rows / rate if rate > 0 else 0

                progress_callback(processed_rows, total_rows, eta_seconds)

        return all_qa_entries

    def process_split_file(self, file_path: str) -> OllaGen1ConversionResult:
        """Process a single split CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            OllaGen1ConversionResult with processing details
        """
        start_time = time.time()

        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Split file not found: {file_path}")

            # Read CSV file
            rows = []
            with open(file_path, "r", encoding="utf-8", newline="") as csvfile:
                # Detect CSV dialect
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample)

                reader = csv.DictReader(csvfile, dialect=dialect)
                for row in reader:
                    rows.append(row)

            # Convert rows to Q&A entries
            qa_entries = self.batch_convert_rows(rows)

            end_time = time.time()
            conversion_time = end_time - start_time

            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(qa_entries)

            return OllaGen1ConversionResult(
                scenario_id=os.path.basename(file_path),
                success=True,
                qa_entries=qa_entries,
                conversion_time_seconds=conversion_time,
                quality_metrics=quality_metrics,
            )

        except Exception as e:
            end_time = time.time()
            conversion_time = end_time - start_time

            return OllaGen1ConversionResult(
                scenario_id=os.path.basename(file_path),
                success=False,
                qa_entries=[],
                conversion_time_seconds=conversion_time,
                error_message=str(e),
                quality_metrics={},
            )

    def batch_convert_with_recovery(self, rows: List[Dict[str, str]]) -> OllaGen1BatchConversionResult:
        """Batch convert with error recovery and continuation.

        Args:
            rows: List of CSV rows to convert

        Returns:
            OllaGen1BatchConversionResult with detailed results
        """
        start_time = time.time()
        self._conversion_stats["start_time"] = start_time

        # Track memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        successful_conversions = 0
        failed_conversions = 0
        total_qa_entries = 0
        error_reports = []

        for i, row in enumerate(rows):
            try:
                qa_entries = self.convert_csv_row_to_qa_entries(row)
                successful_conversions += 1
                total_qa_entries += len(qa_entries)

                # Track peak memory
                current_memory = process.memory_info().rss / 1024 / 1024
                self._conversion_stats["peak_memory_mb"] = max(
                    self._conversion_stats["peak_memory_mb"], current_memory - initial_memory
                )

            except Exception as e:
                failed_conversions += 1
                error_reports.append({"row_index": i, "scenario_id": row.get("ID", "unknown"), "error": str(e)})

        end_time = time.time()
        total_time = end_time - start_time

        return OllaGen1BatchConversionResult(
            total_scenarios_processed=len(rows),
            successful_conversions=successful_conversions,
            failed_conversions=failed_conversions,
            total_qa_entries_generated=total_qa_entries,
            batch_conversion_time_seconds=total_time,
            average_scenarios_per_second=len(rows) / total_time if total_time > 0 else 0,
            memory_peak_mb=self._conversion_stats["peak_memory_mb"],
            quality_summary={
                "success_rate": successful_conversions / len(rows) if rows else 0,
                "error_count": len(error_reports),
            },
            error_summary={"conversion_errors": [report["error"] for report in error_reports]},
        )

    def get_validator(self) -> QAValidator:
        """Get the Q&A validator instance.

        Returns:
            QAValidator instance for validation
        """
        return self.qa_validator

    def get_accuracy_tester(self) -> "AccuracyTester":
        """Get accuracy tester for evaluation.

        Returns:
            AccuracyTester instance
        """
        return AccuracyTester(self.choice_parser, self.answer_mapper)

    def _calculate_quality_metrics(self, qa_entries: List[QuestionAnsweringEntry]) -> Dict[str, Any]:
        """Calculate quality metrics for converted Q&A entries.

        Args:
            qa_entries: List of QuestionAnsweringEntry objects

        Returns:
            Quality metrics dictionary
        """
        if not qa_entries:
            return {"total_entries": 0, "quality_score": 0.0}

        total_entries = len(qa_entries)
        valid_entries = 0
        format_compliant = 0

        for entry in qa_entries:
            # Validate entry
            validation_result = self.qa_validator.validate_qa_entry(entry.model_dump())
            if validation_result["is_valid"]:
                valid_entries += 1

            # Check format compliance
            compliance_result = self.format_validator.check_pyrit_compliance(entry.model_dump())
            if compliance_result["is_compliant"]:
                format_compliant += 1

        quality_score = (valid_entries + format_compliant) / (2 * total_entries)

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "format_compliant": format_compliant,
            "quality_score": quality_score,
            "validation_rate": valid_entries / total_entries,
            "compliance_rate": format_compliant / total_entries,
        }


class AccuracyTester:
    """Tests accuracy of choice extraction and answer mapping."""

    def __init__(self, choice_parser: MultipleChoiceParser, answer_mapper: AnswerMapper) -> None:
        """Initialize accuracy tester.

        Args:
            choice_parser: Parser for choice extraction
            answer_mapper: Mapper for answer mapping
        """
        self.choice_parser = choice_parser
        self.answer_mapper = answer_mapper

    def test_extraction_accuracy(self, test_questions: List[str]) -> float:
        """Test choice extraction accuracy on test questions.

        Args:
            test_questions: List of questions to test

        Returns:
            Overall extraction accuracy (0.0 to 1.0)
        """
        if not test_questions:
            return 0.0

        successful_extractions = 0

        for question in test_questions:
            extraction_result = self.choice_parser.get_extraction_result(question)
            if extraction_result.extraction_successful:
                successful_extractions += 1

        return successful_extractions / len(test_questions)

    def test_mapping_accuracy(self, test_cases: List[Tuple[str, List[str], int]]) -> float:
        """Test answer mapping accuracy.

        Args:
            test_cases: List of (answer_text, choices, expected_index) tuples

        Returns:
            Overall mapping accuracy (0.0 to 1.0)
        """
        if not test_cases:
            return 0.0

        correct_mappings = 0

        for answer_text, choices, expected_index in test_cases:
            mapped_index = self.answer_mapper.map_answer_to_index(answer_text, choices)
            if mapped_index == expected_index:
                correct_mappings += 1

        return correct_mappings / len(test_cases)
