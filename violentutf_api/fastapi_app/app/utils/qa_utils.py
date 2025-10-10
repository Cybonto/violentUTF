# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Question-Answering utilities for OllaGen1 converter (Issue #123).

Provides multiple choice parsing, answer mapping, and validation utilities
for converting OllaGen1 cognitive assessment data to PyRIT format.

SECURITY: All input processing includes sanitization to prevent injection attacks.
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.core.validation import sanitize_string
from app.schemas.ollegen1_datasets import (
    AnswerMappingResult,
    AssessmentCategory,
    MultipleChoiceExtractionResult,
    QuestionType,
)


class MultipleChoiceParser:
    """Parser for extracting multiple choice options from question text.

    Handles various formats and provides fallback parsing for malformed patterns.
    """

    def __init__(self) -> None:
        """Initialize parser with regex patterns."""
        # Primary pattern: (a) text (b) text (c) text (d) text
        self.primary_pattern = re.compile(r"\(([a-d])\)\s*([^(]+?)(?=\([a-d]\)|$)", re.IGNORECASE)

        # Alternative patterns for different formats
        self.alt_patterns = [
            re.compile(r"([a-d])\)\s*([^a-d)]+?)(?=[a-d]\)|$)", re.IGNORECASE),  # a) text b) text
            re.compile(r"([a-d])\.?\s*([^a-d.]+?)(?=[a-d]\.|\n|$)", re.IGNORECASE),  # a. text b. text
            re.compile(r"Option\s*([a-d]):\s*([^O]+?)(?=Option\s*[a-d]:|$)", re.IGNORECASE),  # Option A: text
        ]

        # Pattern for malformed detection
        self.malformed_patterns = [
            re.compile(r"\([a-d][^)]*$"),  # Incomplete closing
            re.compile(r"^[^(]*[a-d]\)"),  # Missing opening
            re.compile(r"\([a-d]\)\s*$"),  # Empty choice
        ]

    def extract_choices(self, question_text: str) -> List[str]:
        """Extract multiple choice options from question text.

        Args:
            question_text: Question with embedded multiple choice options

        Returns:
            List of choice option texts
        """
        if not question_text:
            return []

        question_text = sanitize_string(question_text)

        # Try primary pattern first
        matches = self.primary_pattern.findall(question_text)
        if len(matches) >= 2:
            return [match[1].strip() for match in matches]

        # Try alternative patterns
        for pattern in self.alt_patterns:
            matches = pattern.findall(question_text)
            if len(matches) >= 2:
                return [match[1].strip() for match in matches]

        # No valid pattern found
        return []

    def extract_choices_with_fallback(self, question_text: str) -> List[str]:
        """Extract choices with comprehensive fallback handling.

        Args:
            question_text: Question text to parse

        Returns:
            List of extracted choices (may be partial)
        """
        question_text = sanitize_string(question_text)

        # Try standard extraction first
        choices = self.extract_choices(question_text)
        if len(choices) >= 2:
            return choices

        # Fallback: Look for any parenthetical content
        fallback_pattern = re.compile(r"\([^)]+\)", re.IGNORECASE)
        parentheticals = fallback_pattern.findall(question_text)

        if len(parentheticals) >= 2:
            # Filter out obvious non-choices (like option indicators)
            filtered_choices = []
            for paren in parentheticals:
                # Remove parentheses and check if it looks like a choice
                content = paren[1:-1].strip()
                if len(content) > 2 and not re.match(r"^option\s*[a-d]$", content, re.IGNORECASE):
                    filtered_choices.append(content)

            if len(filtered_choices) >= 2:
                return filtered_choices[:4]  # Limit to 4 choices

        return []

    def validate_choices(self, choices: List[str]) -> bool:
        """Validate extracted choices for completeness and quality.

        Args:
            choices: List of choice options to validate

        Returns:
            True if choices are valid, False otherwise
        """
        if not choices or len(choices) < 2 or len(choices) > 4:
            return False

        # Check each choice
        for choice in choices:
            if not choice or len(choice.strip()) < 2:
                return False
            if len(choice) > 200:  # Too long
                return False

        # Check for reasonable variation (not all identical)
        unique_choices = set(choice.lower().strip() for choice in choices)
        if len(unique_choices) < len(choices) * 0.8:  # Allow some similarity
            return False

        return True

    def get_extraction_result(self, question_text: str) -> MultipleChoiceExtractionResult:
        """Get detailed extraction result with diagnostics.

        Args:
            question_text: Question text to analyze

        Returns:
            MultipleChoiceExtractionResult with full diagnostics
        """
        question_text = sanitize_string(question_text)

        # Try extraction methods in order
        choices = self.extract_choices(question_text)
        method = "primary_pattern"
        confidence = 0.9

        if not choices:
            choices = self.extract_choices_with_fallback(question_text)
            method = "fallback_pattern"
            confidence = 0.6

        # Detect malformed patterns
        malformed = []
        for pattern in self.malformed_patterns:
            if pattern.search(question_text):
                malformed.append(pattern.pattern)

        # Validate extraction
        is_valid = self.validate_choices(choices)
        if not is_valid and choices:
            confidence *= 0.5  # Reduce confidence for invalid choices

        return MultipleChoiceExtractionResult(
            choices=choices,
            extraction_successful=is_valid,
            extraction_method=method,
            confidence_score=confidence,
            malformed_patterns=malformed,
        )


class AnswerMapper:
    """Maps answer text to multiple choice indices.

    Handles various answer formats and provides confidence scoring.
    """

    def __init__(self) -> None:
        """Initialize answer mapper with patterns."""
        # Pattern for "(option x) - content" format
        self.option_pattern = re.compile(r"\(option\s*([a-d])\)\s*[-:]?\s*(.*)", re.IGNORECASE)

        # Pattern for simple "(x) content" format
        self.simple_pattern = re.compile(r"\(([a-d])\)\s*(.*)", re.IGNORECASE)

        # Pattern for letter-only answers
        self.letter_pattern = re.compile(r"^([a-d])$", re.IGNORECASE)

    def map_answer_to_index(self, answer_text: str, choices: List[str]) -> int:
        """Map answer text to choice index.

        Args:
            answer_text: Answer text from CSV
            choices: List of available choices

        Returns:
            Index of matching choice (0-3), or -1 if no match
        """
        if not answer_text or not choices:
            return -1

        answer_text = sanitize_string(answer_text)

        # Method 1: Try option pattern matching
        match = self.option_pattern.match(answer_text)
        if match:
            letter = match.group(1).lower()
            return ord(letter) - ord("a")

        # Method 2: Try simple pattern matching
        match = self.simple_pattern.match(answer_text)
        if match:
            letter = match.group(1).lower()
            return ord(letter) - ord("a")

        # Method 3: Try letter-only matching
        match = self.letter_pattern.match(answer_text.strip())
        if match:
            letter = match.group(1).lower()
            return ord(letter) - ord("a")

        # Method 4: Content matching
        return self._match_content_to_choices(answer_text, choices)

    def _match_content_to_choices(self, answer_text: str, choices: List[str]) -> int:
        """Match answer content against choice text.

        Args:
            answer_text: Answer text to match
            choices: List of choice options

        Returns:
            Index of best matching choice, or -1 if no good match
        """
        answer_lower = answer_text.lower().strip()

        # Extract meaningful content from answer (remove common prefixes)
        content_patterns = [
            r"\(option\s*[a-d]\)\s*[-:]?\s*(.*)",
            r"\([a-d]\)\s*(.*)",
            r"^[a-d]\.?\s*(.*)",
            r"^\s*(.*?)\s*$",
        ]

        extracted_content = answer_lower
        for pattern in content_patterns:
            match = re.match(pattern, answer_lower, re.IGNORECASE)
            if match and match.group(1).strip():
                extracted_content = match.group(1).strip()
                break

        # Find best matching choice
        best_match_idx = -1
        best_score = 0.0

        for i, choice in enumerate(choices):
            choice_lower = choice.lower().strip()

            # Exact match
            if extracted_content == choice_lower:
                return i

            # Substring matching
            if extracted_content in choice_lower or choice_lower in extracted_content:
                score = min(len(extracted_content), len(choice_lower)) / max(len(extracted_content), len(choice_lower))
                if score > best_score and score > 0.5:
                    best_score = score
                    best_match_idx = i

        return best_match_idx

    def get_mapping_result(self, answer_text: str, choices: List[str]) -> AnswerMappingResult:
        """Get detailed mapping result with diagnostics.

        Args:
            answer_text: Answer text to map
            choices: Available choice options

        Returns:
            AnswerMappingResult with mapping details and confidence
        """
        answer_text = sanitize_string(answer_text)

        # Try mapping
        mapped_idx = self.map_answer_to_index(answer_text, choices)

        # Determine method and confidence
        method = "unknown"
        confidence = 0.0

        if mapped_idx >= 0:
            # Check which method worked
            if self.option_pattern.match(answer_text):
                method = "option_pattern"
                confidence = 0.95
            elif self.simple_pattern.match(answer_text):
                method = "simple_pattern"
                confidence = 0.9
            elif self.letter_pattern.match(answer_text.strip()):
                method = "letter_only"
                confidence = 0.85
            else:
                method = "content_matching"
                confidence = 0.7

        return AnswerMappingResult(
            mapped_index=max(0, mapped_idx),
            mapping_successful=mapped_idx >= 0,
            mapping_method=method,
            confidence_score=confidence,
            original_answer_text=answer_text,
        )


class QuestionTypeHandler:
    """Handles different question types and their specific processing."""

    def __init__(self) -> None:
        """Initialize question type handler."""
        self.question_type_configs = {
            QuestionType.WCP: {
                "name": "Which Cognitive Path",
                "category": AssessmentCategory.COGNITIVE_ASSESSMENT,
                "description": "Evaluate understanding of cognitive behavioral patterns",
            },
            QuestionType.WHO: {
                "name": "Compliance Comparison",
                "category": AssessmentCategory.RISK_EVALUATION,
                "description": "Test compliance framework understanding",
            },
            QuestionType.TEAM_RISK: {
                "name": "Team Dynamics",
                "category": AssessmentCategory.TEAM_ASSESSMENT,
                "description": "Assess team-based security risk factors",
            },
            QuestionType.TARGET_FACTOR: {
                "name": "Intervention",
                "category": AssessmentCategory.INTERVENTION_ASSESSMENT,
                "description": "Evaluate remediation and mitigation approaches",
            },
        }

    def get_question_config(self, question_type: str) -> Dict[str, Any]:
        """Get configuration for a question type.

        Args:
            question_type: Question type identifier

        Returns:
            Configuration dictionary for the question type
        """
        try:
            q_type = QuestionType(question_type)
            return self.question_type_configs.get(q_type, {})
        except ValueError:
            return {}

    def process_question(self, question_type: str, question_text: str, answer_text: str) -> Dict[str, Any]:
        """Process a question of specific type.

        Args:
            question_type: Type of question (WCP, WHO, etc.)
            question_text: Question text with choices
            answer_text: Answer text to map

        Returns:
            Processed question data with metadata
        """
        question_text = sanitize_string(question_text)
        answer_text = sanitize_string(answer_text)

        # Get question type configuration
        config = self.get_question_config(question_type)

        # Extract choices
        parser = MultipleChoiceParser()
        extraction_result = parser.get_extraction_result(question_text)

        # Map answer
        mapper = AnswerMapper()
        mapping_result = mapper.get_mapping_result(answer_text, extraction_result.choices)

        return {
            "question_type": question_type,
            "category": config.get("category", "unknown"),
            "name": config.get("name", question_type),
            "description": config.get("description", ""),
            "question_text": question_text,
            "choices": extraction_result.choices,
            "correct_answer": mapping_result.mapped_index if mapping_result.mapping_successful else -1,
            "extraction_confidence": extraction_result.confidence_score,
            "mapping_confidence": mapping_result.confidence_score,
            "processing_successful": extraction_result.extraction_successful and mapping_result.mapping_successful,
        }


class QAValidator:
    """Validates QuestionAnswering entries for quality and compliance."""

    def __init__(self) -> None:
        """Initialize validator."""
        self.required_metadata_fields = [
            "scenario_id",
            "question_type",
            "category",
            "conversion_strategy",
            "conversion_timestamp",
        ]

    def validate_qa_entry(self, qa_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single Q&A entry.

        Args:
            qa_entry: QuestionAnswering entry to validate

        Returns:
            Validation result with details
        """
        errors = []
        warnings = []

        # Check required fields
        required_fields = ["question", "answer_type", "correct_answer", "choices", "metadata"]
        for field in required_fields:
            if field not in qa_entry:
                errors.append(f"Missing required field: {field}")

        if errors:
            return {"is_valid": False, "errors": errors, "warnings": warnings}

        # Validate answer_type
        if qa_entry.get("answer_type") != "int":
            errors.append("Answer type must be 'int' for multiple choice questions")

        # Validate choices
        choices = qa_entry.get("choices", [])
        if not isinstance(choices, list) or len(choices) < 2 or len(choices) > 4:
            errors.append("Must have 2-4 choice options")

        # Validate correct_answer
        correct_answer = qa_entry.get("correct_answer", -1)
        if not isinstance(correct_answer, int) or correct_answer < 0 or correct_answer >= len(choices):
            errors.append(f"Correct answer index {correct_answer} is out of range for {len(choices)} choices")

        # Validate metadata
        metadata = qa_entry.get("metadata", {})
        for field in self.required_metadata_fields:
            if field not in metadata:
                errors.append(f"Missing required metadata field: {field}")

        # Quality checks (warnings)
        if len(qa_entry.get("question", "")) < 20:
            warnings.append("Question text is very short")

        if any(len(choice) < 3 for choice in choices):
            warnings.append("Some choices are very short")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "error_message": "; ".join(errors) if errors else None,
        }

    def validate_metadata_completeness(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata completeness.

        Args:
            metadata: Metadata dictionary to validate

        Returns:
            Completeness validation result
        """
        total_fields = len(self.required_metadata_fields)
        present_fields = sum(1 for field in self.required_metadata_fields if field in metadata)

        completeness_score = present_fields / total_fields if total_fields > 0 else 0.0

        missing_fields = [field for field in self.required_metadata_fields if field not in metadata]

        return {
            "completeness_score": completeness_score,
            "present_fields": present_fields,
            "total_fields": total_fields,
            "missing_fields": missing_fields,
            "is_complete": completeness_score >= 0.95,
        }


class FormatValidator:
    """Validates PyRIT format compliance."""

    def check_pyrit_compliance(self, qa_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Check PyRIT QuestionAnsweringEntry format compliance.

        Args:
            qa_entry: Entry to check for compliance

        Returns:
            Compliance validation result
        """
        violations = []

        # Check PyRIT-specific requirements
        if qa_entry.get("answer_type") != "int":
            violations.append("Answer type must be 'int' for PyRIT multiple choice format")

        correct_answer = qa_entry.get("correct_answer")
        if not isinstance(correct_answer, int):
            violations.append("Correct answer must be integer index for PyRIT format")

        choices = qa_entry.get("choices", [])
        if not isinstance(choices, list):
            violations.append("Choices must be list for PyRIT format")

        metadata = qa_entry.get("metadata")
        if not isinstance(metadata, dict):
            violations.append("Metadata must be dictionary for PyRIT format")

        question = qa_entry.get("question")
        if not isinstance(question, str) or len(question.strip()) == 0:
            violations.append("Question must be non-empty string for PyRIT format")

        return {
            "is_compliant": len(violations) == 0,
            "violations": violations,
            "compliance_score": 1.0 - (len(violations) / 5.0),  # Max 5 checks
        }


class MetadataValidator:
    """Validates metadata structure and completeness."""

    def validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate metadata structure and content.

        Args:
            metadata: Metadata to validate

        Returns:
            Validation result
        """
        required_fields = ["scenario_id", "question_type", "category", "conversion_strategy", "conversion_timestamp"]

        optional_fields = ["person_1", "person_2", "shared_risk_factor", "targeted_factor", "combined_risk_score"]

        total_possible = len(required_fields) + len(optional_fields)
        present_count = 0
        missing_required = []

        # Check required fields
        for field in required_fields:
            if field in metadata and metadata[field] is not None:
                present_count += 1
            else:
                missing_required.append(field)

        # Check optional fields
        for field in optional_fields:
            if field in metadata and metadata[field] is not None:
                present_count += 1

        completeness_score = present_count / total_possible

        return {
            "completeness_score": completeness_score,
            "missing_required": missing_required,
            "is_valid": len(missing_required) == 0,
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
        }
