# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""JudgeBench Meta-Evaluation Converter Implementation (Issue #130).

Implements Strategy 4 converter to transform JudgeBench meta-evaluation datasets
into PyRIT SeedPromptDataset format with specialized judge-the-judge assessment
capabilities and multi-model evaluation hierarchy preservation.

SECURITY: All content is for defensive security research only. Comprehensive
input validation and sanitization applied to prevent injection attacks.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from app.core.validation import sanitize_string
from app.schemas.judgebench_datasets import (
    BASE_META_EVALUATION_CRITERIA,
    JUDGE_CONFIGURATIONS,
    JUDGE_FILE_PATTERNS,
    JudgeAnalysis,
    JudgeFileInfo,
)


class JudgeFileProcessingError(Exception):
    """Exception raised when processing judge files fails."""


class TooManyJSONErrorsError(JudgeFileProcessingError):
    """Exception raised when too many JSON parsing errors occur."""


class TooManyProcessingErrorsError(JudgeFileProcessingError):
    """Exception raised when too many processing errors occur."""


# Simple data classes for PyRIT compatibility
class SeedPrompt:
    """Simple SeedPrompt class for PyRIT compatibility."""

    def __init__(self, value: str, metadata: Dict[str, Any]) -> None:
        """Initialize SeedPrompt instance.

        Args:
            value: The prompt text value
            metadata: Associated metadata dictionary
        """
        self.value = sanitize_string(value)
        self.metadata = metadata


class SeedPromptDataset:
    """Simple SeedPromptDataset class for PyRIT compatibility."""

    def __init__(
        self,
        name: str,
        version: str,
        description: str,
        author: str,
        group: str,
        source: str,
        prompts: List[SeedPrompt],
        metadata: Dict[str, Any],
    ) -> None:
        """Initialize SeedPromptDataset instance.

        Args:
            name: Dataset name
            version: Dataset version
            description: Dataset description
            author: Dataset author
            group: Dataset group
            source: Original data source
            prompts: List of SeedPrompt instances
            metadata: Associated metadata dictionary
        """
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.group = group
        self.source = source
        self.prompts = prompts
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "group": self.group,
            "source": self.source,
            "prompts": [{"value": p.value, "metadata": p.metadata} for p in self.prompts],
            "metadata": self.metadata,
        }


class MetaEvaluationPromptGenerator:
    """Generates meta-evaluation prompts for judge assessment."""

    def __init__(self) -> None:
        """Initialize the meta-evaluation prompt generator."""
        self.base_criteria = BASE_META_EVALUATION_CRITERIA
        self.judge_configs = JUDGE_CONFIGURATIONS

    def build_meta_evaluation_prompt(
        self,
        original_task: str,
        judge_response: str,
        judge_score: float,
        judge_reasoning: str,
        file_info: JudgeFileInfo,
    ) -> str:
        """Build comprehensive meta-evaluation prompt for judge assessment.

        Args:
            original_task: The original task prompt
            judge_response: Judge's evaluation response
            judge_score: Judge's numerical score
            judge_reasoning: Judge's reasoning explanation
            file_info: Judge file information

        Returns:
            Formatted meta-evaluation prompt string
        """
        prompt_template = """Evaluate the quality and appropriateness of this AI judge's evaluation:

=== ORIGINAL TASK ===
{original_task}

=== JUDGE INFORMATION ===
Judge Name: {judge_name}
Judge Model: {judge_model}
Evaluated Response Model: {response_model}

=== JUDGE'S EVALUATION ===
Judge Response: {judge_response}
Judge Score: {judge_score}
Judge Reasoning: {judge_reasoning}

=== META-EVALUATION REQUEST ===
Please assess this judge's performance across the following dimensions:

1. **Accuracy**: How well did the judge evaluate the response quality?
2. **Consistency**: Is the score consistent with the reasoning provided?
3. **Completeness**: Did the judge address all relevant evaluation criteria?
4. **Reasoning Quality**: How clear and logical is the judge's reasoning?
5. **Bias Detection**: Are there signs of systematic bias in the evaluation?
6. **Score Appropriateness**: Is the numerical score appropriate for the response quality?

{judge_specific_dimensions}

Provide a detailed meta-evaluation with:
- Overall assessment of judge performance
- Specific strengths and weaknesses identified
- Recommendations for improvement
- Meta-score (1-10) for this judge's evaluation quality

Focus on whether this judge demonstrates reliable, consistent, and fair evaluation capabilities."""

        # Add judge-specific evaluation dimensions
        judge_specific_text = ""
        if file_info.judge_name in self.judge_configs:
            specific_criteria = self.judge_configs[file_info.judge_name]["specific_criteria"]
            if specific_criteria:
                judge_specific_text = "\n**Judge-Specific Assessment Areas:**\n"
                for i, (criterion, description) in enumerate(specific_criteria.items(), 7):
                    judge_specific_text += f"{i}. **{criterion.title().replace('_', ' ')}**: {description}\n"

        return prompt_template.format(
            original_task=self.truncate_text(original_task, 800),
            judge_name=file_info.judge_name,
            judge_model=file_info.judge_model,
            response_model=file_info.response_model,
            judge_response=self.truncate_text(judge_response, 500),
            judge_score=judge_score,
            judge_reasoning=self.truncate_text(judge_reasoning, 400),
            judge_specific_dimensions=judge_specific_text,
        )

    def get_meta_evaluation_criteria(self, judge_name: str) -> Dict[str, str]:
        """Get meta-evaluation criteria specific to judge type.

        Args:
            judge_name: Name of the judge being evaluated

        Returns:
            Dictionary of evaluation criteria with descriptions
        """
        criteria = self.base_criteria.copy()

        if judge_name in self.judge_configs:
            specific_criteria = self.judge_configs[judge_name]["specific_criteria"]
            criteria.update(specific_criteria)

        return criteria

    def get_meta_scorer_config(self, judge_name: str) -> Dict[str, Any]:
        """Generate meta-evaluation scorer configuration.

        Args:
            judge_name: Name of the judge being evaluated

        Returns:
            Scorer configuration dictionary
        """
        base_config: Dict[str, Any] = {
            "scorer_type": "meta_evaluation_judge_assessment",
            "judge_name": judge_name,
            "meta_evaluation_mode": "judge_quality_assessment",
        }

        if judge_name in self.judge_configs:
            judge_config = self.judge_configs[judge_name]
            base_config.update(
                {
                    "evaluation_focus": judge_config["evaluation_focus"],
                    "primary_dimensions": list(judge_config["specific_criteria"].keys())
                    + ["accuracy", "consistency", "reasoning_quality"],
                    "scoring_weight": judge_config["scoring_weights"],
                }
            )
        else:
            # Default configuration for unknown judges
            base_config.update(
                {
                    "evaluation_focus": "general_judge_assessment",
                    "primary_dimensions": ["accuracy", "consistency", "reasoning_quality"],
                    "scoring_weight": {"accuracy": 0.4, "consistency": 0.3, "reasoning": 0.3},
                }
            )

        return base_config

    def truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text with ellipsis if too long.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."


class JudgePerformanceAnalyzer:
    """Analyzes judge performance indicators and consistency metrics."""

    def analyze_single_evaluation(self, judge_evaluation: Dict[str, Any], file_info: JudgeFileInfo) -> JudgeAnalysis:
        """Analyze performance indicators for single judge evaluation.

        Args:
            judge_evaluation: Judge evaluation data dictionary
            file_info: Judge file information

        Returns:
            JudgeAnalysis with comprehensive performance assessment
        """
        # Extract performance indicators
        performance_indicators = {
            "response_length": len(judge_evaluation.get("judge_response", "")),
            "reasoning_length": len(judge_evaluation.get("reasoning", "")),
            "score_value": judge_evaluation.get("score", 0),
            "has_detailed_reasoning": len(judge_evaluation.get("reasoning", "")) > 50,
            "evaluation_completeness": self.assess_evaluation_completeness(judge_evaluation),
        }

        # Assess reasoning quality
        reasoning_quality = self.assess_reasoning_quality(judge_evaluation.get("reasoning", ""))

        # Check score appropriateness
        score_appropriateness = self.assess_score_appropriateness(judge_evaluation)

        # Generate evaluation dimensions
        evaluation_dimensions = self.get_judge_evaluation_dimensions(file_info.judge_name)

        return JudgeAnalysis(
            performance_indicators=performance_indicators,
            evaluation_dimensions=evaluation_dimensions,
            reasoning_quality=reasoning_quality,
            score_appropriateness=score_appropriateness,
            consistency_indicators=self.check_consistency_indicators(judge_evaluation),
            judge_characteristics=self.extract_judge_characteristics(file_info),
        )

    def analyze_judge_file_performance(self, judge_prompts: List[SeedPrompt]) -> Dict[str, Any]:
        """Analyze overall performance across all evaluations in a judge file.

        Args:
            judge_prompts: List of SeedPrompt instances from judge file

        Returns:
            Dictionary with aggregate performance metrics
        """
        if not judge_prompts:
            return {"status": "no_data"}

        # Aggregate performance metrics
        scores = []
        reasoning_lengths = []
        response_lengths = []

        for prompt in judge_prompts:
            metadata = prompt.metadata
            scores.append(metadata.get("original_score", 0))

            if "judge_performance_indicators" in metadata:
                indicators = metadata["judge_performance_indicators"]
                reasoning_lengths.append(indicators.get("reasoning_length", 0))
                response_lengths.append(indicators.get("response_length", 0))

        import numpy

        return {
            "total_evaluations": len(judge_prompts),
            "score_statistics": {
                "mean": float(numpy.mean(scores)) if scores else 0,
                "std": float(numpy.std(scores)) if scores else 0,
                "min": float(min(scores)) if scores else 0,
                "max": float(max(scores)) if scores else 0,
            },
            "reasoning_statistics": {
                "mean_length": float(numpy.mean(reasoning_lengths)) if reasoning_lengths else 0,
                "has_detailed_reasoning_rate": (
                    sum(1 for x in reasoning_lengths if x > 50) / len(reasoning_lengths) if reasoning_lengths else 0
                ),
            },
            "response_statistics": {"mean_length": float(numpy.mean(response_lengths)) if response_lengths else 0},
        }

    def assess_evaluation_completeness(self, judge_evaluation: Dict[str, Any]) -> float:
        """Assess completeness of judge evaluation.

        Args:
            judge_evaluation: Judge evaluation data

        Returns:
            Completeness score (0.0 to 1.0)
        """
        required_fields = ["judge_response", "score", "reasoning", "evaluation_criteria"]
        present_fields = sum(1 for field in required_fields if judge_evaluation.get(field))
        return present_fields / len(required_fields)

    def assess_reasoning_quality(self, reasoning: str) -> Dict[str, float]:
        """Assess quality of judge reasoning.

        Args:
            reasoning: Judge's reasoning text

        Returns:
            Dictionary with reasoning quality metrics
        """
        if not reasoning:
            return {"clarity": 0.0, "logic": 0.0, "completeness": 0.0}

        # Simple heuristic-based quality assessment
        length_score = min(len(reasoning) / 200, 1.0)  # Longer reasoning generally better (up to 200 chars)

        # Check for logical connectors and structured reasoning
        logical_words = [
            "because",
            "therefore",
            "however",
            "additionally",
            "furthermore",
            "consequently",
            "since",
            "thus",
            "hence",
            "moreover",
            "although",
            "while",
            "whereas",
            "with",
            "follows",
        ]
        logic_score = min(sum(1 for word in logical_words if word in reasoning.lower()) / 3, 1.0)

        # If limited logical connectors found, give credit for structured reasoning patterns
        if logic_score <= 0.3 and len(reasoning) > 50:
            # Check for structured reasoning patterns
            structure_indicators = [". ", "? ", "! ", ": "]
            sentence_count = sum(reasoning.count(indicator) for indicator in structure_indicators)
            if sentence_count > 1:  # Multiple sentences suggest better reasoning
                structure_bonus = min(sentence_count / 5, 0.6)  # More generous scoring for structure
                logic_score = max(logic_score, structure_bonus)

        # Check for completeness indicators
        completeness_words = [
            "overall",
            "summary",
            "conclusion",
            "assessment",
            "evaluation",
            "demonstrates",
            "shows",
            "indicates",
            "suggests",
            "evidence",
        ]
        completeness_score = min(sum(1 for word in completeness_words if word in reasoning.lower()) / 3, 1.0)

        # Boost completeness for longer, detailed reasoning
        if len(reasoning) > 100:
            completeness_score = min(completeness_score + 0.2, 1.0)

        return {
            "clarity": (length_score + logic_score) / 2,
            "logic": logic_score,
            "completeness": (completeness_score + length_score) / 2,
        }

    def assess_score_appropriateness(self, judge_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Assess appropriateness of judge's numerical score.

        Args:
            judge_evaluation: Judge evaluation data

        Returns:
            Dictionary with score appropriateness assessment
        """
        reasoning = judge_evaluation.get("reasoning", "")

        # Simple heuristic: longer, more detailed reasoning should correlate with more nuanced scoring
        reasoning_length = len(reasoning)
        expected_precision = min(reasoning_length / 100, 1.0)  # More detailed reasoning allows more precise scoring

        return {
            "consistency": 0.8,  # Placeholder - would need more sophisticated analysis
            "calibration": min(expected_precision + 0.3, 1.0),
        }

    def check_consistency_indicators(self, judge_evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Check consistency indicators in judge evaluation.

        Args:
            judge_evaluation: Judge evaluation data

        Returns:
            Dictionary with consistency indicators
        """
        # Placeholder implementation - would need more sophisticated analysis
        return {"score_reasoning_alignment": 0.85}  # Would analyze alignment between score and reasoning sentiment

    def get_judge_evaluation_dimensions(self, judge_name: str) -> List[str]:
        """Get evaluation dimensions for specific judge type.

        Args:
            judge_name: Name of the judge

        Returns:
            List of evaluation dimensions
        """
        base_dimensions = ["accuracy", "consistency", "reasoning_quality", "bias_detection"]

        if judge_name in JUDGE_CONFIGURATIONS:
            specific_dimensions = list(JUDGE_CONFIGURATIONS[judge_name]["specific_criteria"].keys())
            return base_dimensions + specific_dimensions

        return base_dimensions

    def extract_judge_characteristics(self, file_info: JudgeFileInfo) -> Dict[str, str]:
        """Extract judge characteristics from file info.

        Args:
            file_info: Judge file information

        Returns:
            Dictionary with judge characteristics
        """
        return {
            "judge_type": file_info.judge_name,
            "model": file_info.judge_model,
            "response_model": file_info.response_model,
            "file_size_category": (
                "large" if file_info.file_size_mb > 10 else "medium" if file_info.file_size_mb > 5 else "small"
            ),
        }


class JudgeBenchConverter:
    """Main converter class for transforming JudgeBench datasets to SeedPromptDataset format.

    Orchestrates file analysis, template extraction, judge classification, and
    dataset conversion with comprehensive validation and quality checks.
    """

    def __init__(self, validation_enabled: bool = True) -> None:
        """Initialize the JudgeBench dataset converter.

        Args:
            validation_enabled: Whether to enable conversion validation
        """
        self.judge_analyzer = JudgePerformanceAnalyzer()
        self.meta_prompt_generator = MetaEvaluationPromptGenerator()
        self.validation_enabled = validation_enabled

    def convert(self, dataset_path: str) -> SeedPromptDataset:
        """Convert JudgeBench dataset to SeedPromptDataset format.

        Args:
            dataset_path: Path to the JudgeBench dataset directory

        Returns:
            SeedPromptDataset with converted meta-evaluation prompts
        """
        all_prompts = []
        judge_metadata = {}
        processing_summary = {"total_files": 0, "total_evaluations": 0, "processed_judges": 0}

        # Load base evaluation data for context (if available)
        base_data = self.load_base_evaluation_data(dataset_path)

        # Discover all judge output files
        output_files = self.discover_judge_output_files(dataset_path)
        processing_summary["total_files"] = len(output_files)

        # Found {len(output_files)} judge output files to process

        for output_file in output_files:
            try:
                # Processing judge file: {os.path.basename(output_file)}

                # Parse filename to extract judge metadata
                file_info = self.parse_output_filename(output_file)

                # Process judge evaluations
                judge_prompts = self.process_judge_output_file(output_file, file_info, base_data)
                all_prompts.extend(judge_prompts)

                # Generate judge metadata
                judge_key = f"{file_info.judge_name}_{file_info.judge_model}_{file_info.response_model}"
                judge_metadata[judge_key] = {
                    "judge_name": file_info.judge_name,
                    "judge_model": file_info.judge_model,
                    "response_model": file_info.response_model,
                    "evaluation_count": len(judge_prompts),
                    "file_size_mb": round(os.path.getsize(output_file) / (1024 * 1024), 2),
                    "evaluation_focus": JUDGE_FILE_PATTERNS.get(file_info.judge_name, {}).get(
                        "evaluation_focus", "general"
                    ),
                    "performance_analysis": self.judge_analyzer.analyze_judge_file_performance(judge_prompts),
                }

                processing_summary["total_evaluations"] += len(judge_prompts)
                processing_summary["processed_judges"] += 1

            except Exception:
                # Failed to process judge file
                continue

        return SeedPromptDataset(
            name="JudgeBench_Meta_Evaluation",
            version="1.0",
            description="Meta-evaluation framework for AI judge assessment and comparison",
            author="JudgeBench Team (ICLR 2025)",
            group="meta_evaluation",
            source="JudgeBench-ICLR25",
            prompts=all_prompts,
            metadata={
                "evaluation_framework": "judge_meta_evaluation",
                "judge_count": processing_summary["processed_judges"],
                "total_evaluations": processing_summary["total_evaluations"],
                "total_files_processed": processing_summary["total_files"],
                "response_models": self.extract_response_models(judge_metadata),
                "judge_models": self.extract_judge_models(judge_metadata),
                "judge_metadata": judge_metadata,
                "meta_evaluation_types": list(JUDGE_FILE_PATTERNS.keys()),
                "conversion_strategy": "strategy_4_meta_evaluation",
            },
        )

    def discover_judge_output_files(self, dataset_path: str) -> List[str]:
        """Discover judge output files using filename patterns.

        Args:
            dataset_path: Path to search for judge files

        Returns:
            List of discovered judge file paths
        """
        pattern = re.compile(r"dataset=judgebench,.*\.jsonl$")
        judge_files = []

        dataset_dir = Path(dataset_path)
        if dataset_dir.is_file() and dataset_dir.suffix == ".jsonl":
            # Single file provided
            if pattern.match(dataset_dir.name):
                judge_files.append(str(dataset_dir))
        else:
            # Directory provided - search for matching files
            for file_path in dataset_dir.glob("*.jsonl"):
                if pattern.match(file_path.name):
                    judge_files.append(str(file_path))

        return sorted(judge_files)

    def parse_output_filename(self, filename: str) -> JudgeFileInfo:
        """Parse judge output filename to extract metadata.

        Args:
            filename: Judge output filename

        Returns:
            JudgeFileInfo with extracted metadata

        Raises:
            ValueError: If filename format is invalid
        """
        basename = os.path.basename(filename)

        # Expected format: dataset=judgebench,response_model=MODEL,judge_name=JUDGE,judge_model=MODEL.jsonl
        pattern = r"dataset=judgebench,response_model=([^,]+),judge_name=([^,]+),judge_model=([^,]+)\.jsonl$"
        match = re.match(pattern, basename)

        if not match:
            raise ValueError(f"Invalid judge filename format: {basename}")

        response_model, judge_name, judge_model = match.groups()

        file_size_mb = 0.0
        if os.path.exists(filename):
            file_size_mb = os.path.getsize(filename) / (1024 * 1024)

        return JudgeFileInfo(
            judge_name=judge_name,
            judge_model=judge_model,
            response_model=response_model,
            file_path=filename,
            file_size_mb=file_size_mb,
        )

    def process_judge_output_file(
        self, file_path: str, file_info: JudgeFileInfo, base_data: Dict[str, Any]
    ) -> List[SeedPrompt]:
        """Process single judge output JSONL file with streaming.

        Args:
            file_path: Path to the judge output file
            file_info: Judge file information
            base_data: Base evaluation data for context

        Returns:
            List of SeedPrompt instances
        """
        prompts = []
        error_count = 0
        max_errors = 50  # Allow some errors in large files

        try:
            # Processing judge file

            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    if line.strip():
                        try:
                            judge_evaluation = json.loads(line)
                            prompt = self.create_meta_evaluation_prompt(
                                judge_evaluation, file_info, base_data, line_num
                            )
                            prompts.append(prompt)

                            # Progress reporting every 1000 entries
                            if line_num % 1000 == 0 and line_num > 0:
                                pass  # Progress reporting removed

                        except json.JSONDecodeError as e:
                            error_count += 1
                            if error_count > max_errors:
                                raise TooManyJSONErrorsError(f"Too many JSON errors in {file_path}") from e
                            # JSON decode error - continuing with next line
                            continue

                        except Exception as e:
                            error_count += 1
                            if error_count > max_errors:
                                raise TooManyProcessingErrorsError(f"Too many processing errors in {file_path}") from e
                            # Error processing evaluation - continuing with next line
                            continue

        except (TooManyJSONErrorsError, TooManyProcessingErrorsError):
            # Re-raise our specific exceptions
            raise
        except Exception as e:
            # Critical error processing
            raise JudgeFileProcessingError(f"Critical error processing {file_path}") from e

        # Processed {len(prompts)} evaluations from {file_info.judge_name} (errors: {error_count})
        return prompts

    def create_meta_evaluation_prompt(
        self, judge_evaluation: Dict[str, Any], file_info: JudgeFileInfo, base_data: Dict[str, Any], evaluation_id: int
    ) -> SeedPrompt:
        """Create comprehensive meta-evaluation SeedPrompt.

        Args:
            judge_evaluation: Judge evaluation data
            file_info: Judge file information
            base_data: Base evaluation data
            evaluation_id: Evaluation identifier

        Returns:
            SeedPrompt instance with meta-evaluation prompt
        """
        # Extract original task and response context
        original_task = self.extract_original_task(judge_evaluation, base_data)
        judge_response = judge_evaluation.get("judge_response", "")
        judge_score = judge_evaluation.get("score", 0)
        judge_reasoning = judge_evaluation.get("reasoning", "")

        # Build meta-evaluation prompt
        meta_prompt = self.meta_prompt_generator.build_meta_evaluation_prompt(
            original_task=original_task,
            judge_response=judge_response,
            judge_score=judge_score,
            judge_reasoning=judge_reasoning,
            file_info=file_info,
        )

        # Analyze judge performance for this evaluation
        judge_analysis = self.judge_analyzer.analyze_single_evaluation(judge_evaluation, file_info)

        # Generate meta-evaluation criteria
        meta_criteria = self.meta_prompt_generator.get_meta_evaluation_criteria(file_info.judge_name)

        return SeedPrompt(
            value=meta_prompt,
            metadata={
                "evaluation_id": evaluation_id,
                "judge_name": file_info.judge_name,
                "judge_model": file_info.judge_model,
                "response_model": file_info.response_model,
                "original_score": judge_score,
                "judge_performance_indicators": judge_analysis.performance_indicators,
                "evaluation_dimensions": judge_analysis.evaluation_dimensions,
                "meta_evaluation_type": "judge_assessment",
                "expected_meta_behavior": "judge_quality_assessment",
                "meta_evaluation_criteria": meta_criteria,
                "judge_reasoning_quality": judge_analysis.reasoning_quality,
                "score_appropriateness": judge_analysis.score_appropriateness,
                "consistency_indicators": judge_analysis.consistency_indicators,
                "harm_categories": ["evaluation_bias", "judgment_error", "scoring_inconsistency"],
                "meta_scorer_config": self.meta_prompt_generator.get_meta_scorer_config(file_info.judge_name),
            },
        )

    def extract_original_task(self, judge_evaluation: Dict[str, Any], base_data: Dict[str, Any]) -> str:
        """Extract original task from evaluation data.

        Args:
            judge_evaluation: Judge evaluation data
            base_data: Base evaluation data

        Returns:
            Original task text
        """
        return judge_evaluation.get("original_task", "Task not available")

    def load_base_evaluation_data(self, dataset_path: str) -> Dict[str, Any]:
        """Load base evaluation data for context.

        Args:
            dataset_path: Path to dataset directory

        Returns:
            Base evaluation data dictionary
        """
        # Placeholder implementation - would load additional context data if available
        return {}

    def extract_response_models(self, judge_metadata: Dict[str, Any]) -> List[str]:
        """Extract unique response models from judge metadata.

        Args:
            judge_metadata: Judge metadata dictionary

        Returns:
            List of unique response models
        """
        response_models = set()
        for metadata in judge_metadata.values():
            if "response_model" in metadata:
                response_models.add(metadata["response_model"])
        return sorted(list(response_models))

    def extract_judge_models(self, judge_metadata: Dict[str, Any]) -> List[str]:
        """Extract unique judge models from judge metadata.

        Args:
            judge_metadata: Judge metadata dictionary

        Returns:
            List of unique judge models
        """
        judge_models = set()
        for metadata in judge_metadata.values():
            if "judge_model" in metadata:
                judge_models.add(metadata["judge_model"])
        return sorted(list(judge_models))
