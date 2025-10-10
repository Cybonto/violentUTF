# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""DocMath Dataset Converter Implementation (Issue #127).

Implements comprehensive DocMath dataset converter with large file handling,
mathematical reasoning preservation, and performance optimization for files
up to 220MB with streaming processing and memory management.

SECURITY: All processing includes proper validation for defensive security research.
"""
import json
import os
import time
from typing import Any, Dict, List, Optional

from app.core.validation import sanitize_file_content
from app.schemas.docmath_datasets import (
    DocMathConversionConfig,
    QuestionAnsweringDataset,
    QuestionAnsweringEntry,
)
from app.services.mathematical_service import (
    MathematicalAnswerProcessor,
    MathematicalComplexityAnalyzer,
    MathematicalContextBuilder,
    MathematicalDomainClassifier,
)
from app.utils.math_processing import (
    MathematicalJSONSplitter,
    MemoryMonitor,
    detect_numerical_type,
    get_file_size_mb,
)


class DocMathConverter:
    """DocMath dataset converter with large file handling support.

    Implements Strategy 2 converter to transform DocMath mathematical reasoning
    datasets into PyRIT QuestionAnsweringDataset format with specialized handling
    for very large files (220MB+) using streaming and file splitting.
    """

    def __init__(self, config: Optional[DocMathConversionConfig] = None) -> None:
        """Initialize DocMath converter.

        Args:
            config: Optional conversion configuration
        """
        self.config = config or DocMathConversionConfig()

        # Initialize core components
        self.memory_monitor = MemoryMonitor(max_usage_gb=self.config.max_memory_usage_gb)
        self.json_splitter = MathematicalJSONSplitter(
            target_size_mb=self.config.chunk_size_mb,
            preserve_mathematical_context=self.config.enable_context_preservation,
        )

        # Initialize processing services
        self.domain_classifier = MathematicalDomainClassifier()
        self.complexity_analyzer = MathematicalComplexityAnalyzer()
        self.answer_processor = MathematicalAnswerProcessor()
        self.context_builder = MathematicalContextBuilder()

    def convert(self, dataset_path: str) -> QuestionAnsweringDataset:
        """Convert DocMath dataset with large file handling.

        Args:
            dataset_path: Path to DocMath dataset directory

        Returns:
            QuestionAnsweringDataset with converted mathematical reasoning tasks
        """
        start_time = time.time()
        all_questions = []
        processing_summary = {}

        if not os.path.exists(dataset_path):
            # Return empty dataset for missing path
            return QuestionAnsweringDataset(
                name="DocMath_Mathematical_Reasoning",
                version="1.0",
                description="Mathematical reasoning over specialized documents (empty - path not found)",
                author="Yale NLP",
                group="mathematical_reasoning",
                source="DocMath-Yale",
                questions=[],
                metadata={
                    "error": f"Dataset path not found: {dataset_path}",
                    "conversion_strategy": "strategy_2_reasoning_benchmarks",
                },
            )

        # Process each complexity tier
        for tier in ["simpshort", "simplong", "compshort", "complong"]:
            for split in ["test", "testmini"]:
                file_name = f"{tier}_{split}.json"
                file_path = os.path.join(dataset_path, file_name)

                if os.path.exists(file_path):
                    try:
                        # Determine processing strategy
                        strategy = self.get_processing_strategy(file_path, tier)

                        if strategy == "splitting_with_streaming":
                            questions = self.process_large_file_with_splitting(file_path, tier, split)
                        elif strategy == "streaming":
                            questions = self.process_file_with_streaming(file_path, tier, split)
                        else:
                            questions = self.process_standard_file(file_path, tier, split)

                        all_questions.extend(questions)
                        processing_summary[file_name] = {
                            "question_count": len(questions),
                            "processing_strategy": strategy,
                            "tier": tier,
                            "split": split,
                            "file_size_mb": get_file_size_mb(file_path),
                        }

                    except Exception as e:
                        processing_summary[file_name] = {"error": str(e), "tier": tier, "split": split}

        processing_time = time.time() - start_time

        return QuestionAnsweringDataset(
            name="DocMath_Mathematical_Reasoning",
            version="1.0",
            description="Mathematical reasoning over specialized documents with complexity tiers",
            author="Yale NLP",
            group="mathematical_reasoning",
            source="DocMath-Yale",
            questions=all_questions,
            metadata={
                "complexity_tiers": 4,
                "document_types": ["specialized", "long_form"],
                "reasoning_type": "numerical",
                "processing_summary": processing_summary,
                "total_questions": len(all_questions),
                "processing_time_seconds": processing_time,
                "conversion_strategy": "strategy_2_reasoning_benchmarks",
                "memory_peak_gb": self.memory_monitor.get_current_usage_gb(),
            },
        )

    def get_processing_strategy(self, file_path: str, tier: str) -> str:
        """Determine optimal processing strategy based on file size and tier.

        Args:
            file_path: Path to file to process
            tier: Complexity tier

        Returns:
            Processing strategy string
        """
        if not os.path.exists(file_path):
            return "standard"

        size_mb = get_file_size_mb(file_path)

        if size_mb > 100:  # 220MB complong_test.json
            return "splitting_with_streaming"
        elif size_mb > 50:  # 53MB complong_testmini.json
            return "streaming"
        else:
            return "standard"

    def _get_file_size_mb(self, file_path: str) -> float:
        """Get file size in MB.

        Args:
            file_path: Path to file

        Returns:
            File size in MB
        """
        return get_file_size_mb(file_path)

    def process_standard_file(self, file_path: str, tier: str, split: str) -> List[QuestionAnsweringEntry]:
        """Process standard-sized DocMath file.

        Args:
            file_path: Path to JSON file
            tier: Complexity tier
            split: Dataset split

        Returns:
            List of QuestionAnsweringEntry objects
        """
        questions = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = sanitize_file_content(f.read())
                data = json.loads(content)

            # Handle different data structures
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "questions" in data:
                items = data["questions"]
            else:
                items = [data]

            # Process each item
            for item in items:
                if isinstance(item, dict):
                    qa_entry = self.create_mathematical_question(item, tier, split)
                    questions.append(qa_entry)

        except (json.JSONDecodeError, IOError) as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error("Error processing file %s: %s", file_path, e)

        return questions

    def process_file_with_streaming(self, file_path: str, tier: str, split: str) -> List[QuestionAnsweringEntry]:
        """Process medium-sized file with streaming.

        Args:
            file_path: Path to JSON file
            tier: Complexity tier
            split: Dataset split

        Returns:
            List of QuestionAnsweringEntry objects
        """
        questions = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Load full JSON (streaming within memory limits)
                content = sanitize_file_content(f.read())
                data = json.loads(content)

                # Process in batches to manage memory
                items = data if isinstance(data, list) else [data]

                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        qa_entry = self.create_mathematical_question(item, tier, split)
                        questions.append(qa_entry)

                        # Periodic memory check
                        if i % self.config.batch_size == 0:
                            self.memory_monitor.check_and_cleanup()

        except (json.JSONDecodeError, IOError) as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error("Error processing file %s: %s", file_path, e)

        return questions

    def process_large_file_with_splitting(self, file_path: str, tier: str, split: str) -> List[QuestionAnsweringEntry]:
        """Process large file with splitting strategy.

        Args:
            file_path: Path to JSON file
            tier: Complexity tier
            split: Dataset split

        Returns:
            List of QuestionAnsweringEntry objects
        """
        all_questions = []

        try:
            # Split large JSON file into manageable chunks
            split_result = self.json_splitter.split_json_preserving_objects(
                file_path,
                target_size=self.config.chunk_size_mb * 1024 * 1024,  # Convert to bytes
                preserve_mathematical_context=self.config.enable_context_preservation,
            )

            # Process each chunk with memory monitoring
            for chunk_info in split_result.chunks:
                with self.memory_monitor.context():
                    chunk_questions = self.process_json_chunk(chunk_info.filename, tier, split)
                    all_questions.extend(chunk_questions)

            # Clean up split files
            split_result.cleanup_chunks()

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error("Error processing large file %s: %s", file_path, e)

        return all_questions

    def process_json_chunk(self, chunk_path: str, tier: str, split: str) -> List[QuestionAnsweringEntry]:
        """Process a JSON chunk file.

        Args:
            chunk_path: Path to chunk file
            tier: Complexity tier
            split: Dataset split

        Returns:
            List of QuestionAnsweringEntry objects
        """
        return self.process_standard_file(chunk_path, tier, split)

    def create_mathematical_question(self, item: Dict[str, Any], tier: str, split: str) -> QuestionAnsweringEntry:
        """Create mathematical reasoning QuestionAnsweringEntry.

        Args:
            item: Dictionary containing DocMath item data
            tier: Complexity tier
            split: Dataset split

        Returns:
            QuestionAnsweringEntry with mathematical reasoning context
        """
        # Build comprehensive question with mathematical context
        full_question = self.build_mathematical_context(item)

        # Process mathematical answer
        answer_type, correct_answer = self.answer_processor.process_mathematical_answer(item)

        # Extract mathematical domain and complexity
        math_domain = self.domain_classifier.classify_mathematical_domain(item)
        complexity_score = self.complexity_analyzer.assess_mathematical_complexity(item, tier)

        # Detect numerical type for additional validation
        numerical_type = detect_numerical_type(correct_answer)

        return QuestionAnsweringEntry(
            question=full_question,
            answer_type=answer_type,
            correct_answer=correct_answer,
            choices=[],  # Mathematical reasoning typically doesn't use multiple choice
            metadata={
                "question_id": item.get("question_id", ""),
                "complexity_tier": tier,
                "split": split,
                "document_type": "mathematical",
                "table_evidence": item.get("table_evidence", []),
                "paragraph_evidence": item.get("paragraphs", []),
                "python_solution": item.get("python_solution", ""),
                "mathematical_domain": math_domain,
                "complexity_score": complexity_score,
                "numerical_type": numerical_type,
                "reasoning_steps": item.get("reasoning_steps", []),
                "original_context": item.get("context", ""),
            },
        )

    def build_mathematical_context(self, item: Dict[str, Any]) -> str:
        """Build comprehensive mathematical context.

        Args:
            item: Dictionary containing DocMath item data

        Returns:
            String with formatted mathematical context
        """
        return self.context_builder.build_mathematical_context(item)
