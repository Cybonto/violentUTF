# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Mathematical Processing Service for DocMath Dataset Converter (Issue #127).

Provides mathematical domain classification, complexity analysis, and specialized
processing for mathematical reasoning tasks.

SECURITY: All processing includes proper validation for defensive security research.
"""
import re
from typing import Any, Dict, Tuple

from app.schemas.docmath_datasets import MathematicalDomain


class MathematicalDomainClassifier:
    """Classifier for mathematical domains based on content analysis."""

    def __init__(self) -> None:
        """Initialize the domain classifier with pattern definitions."""
        self.domain_patterns = {
            MathematicalDomain.ARITHMETIC: {
                "keywords": [
                    "addition",
                    "subtraction",
                    "multiplication",
                    "division",
                    "calculate",
                    "add",
                    "subtract",
                    "multiply",
                    "divide",
                    "sum",
                    "difference",
                    "product",
                    "quotient",
                ],
                "patterns": [r"\d+\s*[+\-*/]\s*\d+", r"what is \d+", r"calculate \d+"],
                "complexity": "low",
            },
            MathematicalDomain.ALGEBRA: {
                "keywords": [
                    "equation",
                    "solve",
                    "variable",
                    "polynomial",
                    "linear",
                    "quadratic",
                    "x",
                    "y",
                    "unknown",
                    "coefficient",
                    "expression",
                ],
                "patterns": [r"solve for [a-zA-Z]", r"[a-zA-Z]\s*=\s*\d+", r"\d*[a-zA-Z]\s*[+\-]"],
                "complexity": "medium",
            },
            MathematicalDomain.GEOMETRY: {
                "keywords": [
                    "area",
                    "perimeter",
                    "volume",
                    "triangle",
                    "circle",
                    "rectangle",
                    "square",
                    "angle",
                    "radius",
                    "diameter",
                    "circumference",
                    "polygon",
                    "surface",
                ],
                "patterns": [r"area of", r"perimeter of", r"volume of", r"\d+\s*degrees?"],
                "complexity": "medium",
            },
            MathematicalDomain.STATISTICS: {
                "keywords": [
                    "mean",
                    "median",
                    "mode",
                    "average",
                    "probability",
                    "standard deviation",
                    "variance",
                    "distribution",
                    "sample",
                    "population",
                    "correlation",
                ],
                "patterns": [r"average of", r"mean of", r"probability that", r"standard deviation"],
                "complexity": "medium",
            },
            MathematicalDomain.CALCULUS: {
                "keywords": [
                    "derivative",
                    "integral",
                    "limit",
                    "rate of change",
                    "optimization",
                    "differentiate",
                    "integrate",
                    "continuous",
                    "discontinuous",
                    "asymptote",
                ],
                "patterns": [r"derivative of", r"integrate", r"limit as", r"rate of change"],
                "complexity": "high",
            },
            MathematicalDomain.FINANCIAL: {
                "keywords": [
                    "interest",
                    "loan",
                    "investment",
                    "profit",
                    "loss",
                    "percentage",
                    "rate",
                    "compound",
                    "simple",
                    "principal",
                    "bank",
                    "mortgage",
                    "APR",
                ],
                "patterns": [r"\$\d+", r"\d+%", r"interest rate", r"compound interest"],
                "complexity": "medium",
            },
            MathematicalDomain.MEASUREMENT: {
                "keywords": [
                    "units",
                    "conversion",
                    "metric",
                    "imperial",
                    "distance",
                    "weight",
                    "length",
                    "meters",
                    "feet",
                    "inches",
                    "kilograms",
                    "pounds",
                    "liters",
                    "gallons",
                ],
                "patterns": [r"\d+\s*(?:m|ft|in|kg|lb|L|gal)", r"convert \d+", r"from .* to .*"],
                "complexity": "low",
            },
            MathematicalDomain.WORD_PROBLEMS: {
                "keywords": [
                    "story",
                    "scenario",
                    "real-world",
                    "application",
                    "practical",
                    "problem",
                    "situation",
                    "context",
                    "example",
                    "case",
                    "if",
                    "when",
                    "how many",
                ],
                "patterns": [r"if .* then", r"how many", r"a person has", r"in a situation"],
                "complexity": "variable",
            },
        }

    def classify_mathematical_domain(self, item: Dict[str, Any]) -> str:
        """Classify mathematical domain based on content analysis.

        Args:
            item: Dictionary containing question, context, and paragraphs

        Returns:
            String indicating the detected mathematical domain
        """
        # Combine all text content for analysis
        text_content = self._extract_text_content(item).lower()

        domain_scores = {}

        # Score each domain based on keyword matches and pattern matches
        for domain, info in self.domain_patterns.items():
            score = 0

            # Keyword scoring
            for keyword in info["keywords"]:
                if keyword in text_content:
                    score += 1

            # Pattern scoring (weighted higher)
            for pattern in info["patterns"]:
                if re.search(pattern, text_content, re.IGNORECASE):
                    score += 2

            domain_scores[domain] = score

        # Return domain with highest score
        if domain_scores:
            best_domain = max(domain_scores.items(), key=lambda x: x[1])
            if best_domain[1] > 0:  # Only return if we found matches
                return best_domain[0].value

        return MathematicalDomain.GENERAL.value

    def _extract_text_content(self, item: Dict[str, Any]) -> str:
        """Extract all text content from a DocMath item."""
        content_parts = []

        # Add question
        if "question" in item:
            content_parts.append(str(item["question"]))

        # Add context
        if "context" in item:
            content_parts.append(str(item["context"]))

        # Add paragraphs
        if "paragraphs" in item and isinstance(item["paragraphs"], list):
            content_parts.extend(str(p) for p in item["paragraphs"])

        # Add table evidence (text content only)
        if "table_evidence" in item and isinstance(item["table_evidence"], list):
            for evidence in item["table_evidence"]:
                if isinstance(evidence, str):
                    content_parts.append(evidence)

        return " ".join(content_parts)


class MathematicalComplexityAnalyzer:
    """Analyzer for mathematical complexity assessment."""

    def __init__(self) -> None:
        """Initialize the complexity analyzer."""
        self.complexity_indicators = {
            "high": [
                "derivative",
                "integral",
                "limit",
                "matrix",
                "eigenvalue",
                "vector space",
                "differential equation",
                "partial derivative",
                "infinite series",
                "topology",
                "proof",
                "theorem",
                "lemma",
                "corollary",
                "optimization",
                "calculus",
            ],
            "medium": [
                "quadratic",
                "polynomial",
                "logarithm",
                "exponential",
                "trigonometric",
                "sine",
                "cosine",
                "tangent",
                "equation system",
                "inequality",
                "function",
                "graph",
                "coordinate",
                "vertex",
                "parabola",
            ],
            "low": [
                "addition",
                "subtraction",
                "multiplication",
                "division",
                "basic",
                "simple",
                "elementary",
                "count",
                "sum",
                "difference",
                "product",
            ],
        }

        self.complexity_patterns = {
            "high": [
                r"∫.*dx",  # Integration symbols
                r"d/dx",  # Derivative notation
                r"lim.*→",  # Limit notation
                r"∂.*∂",  # Partial derivatives
                r"∇",  # Gradient/nabla
                r"∑.*=",  # Summation
                r"∏.*=",  # Product notation
            ],
            "medium": [
                r"[a-zA-Z]\^[2-9]",  # Powers higher than 1
                r"log\s*\(",  # Logarithms
                r"sin\s*\(",  # Trig functions
                r"cos\s*\(",
                r"tan\s*\(",
                r"√",  # Square root
                r"\d+[a-zA-Z]\s*[+\-]\s*\d+",  # Linear expressions
            ],
            "low": [
                r"^\d+\s*[+\-*/]\s*\d+$",  # Simple arithmetic
                r"what is \d+",  # Basic questions
                r"\d+\s*\+\s*\d+",  # Simple addition
                r"\d+\s*\-\s*\d+",  # Simple subtraction
            ],
        }

    def assess_mathematical_complexity(self, item: Dict[str, Any], tier: str) -> float:
        """Assess mathematical complexity of an item.

        Args:
            item: Dictionary containing mathematical content
            tier: Complexity tier (simpshort, simplong, compshort, complong)

        Returns:
            Float between 0.0 and 1.0 indicating complexity level
        """
        # Extract text content
        text_content = self._extract_text_for_analysis(item).lower()

        # Base complexity from tier
        tier_base_complexity = {"simpshort": 0.1, "simplong": 0.3, "compshort": 0.6, "complong": 0.8}

        base_score = tier_base_complexity.get(tier, 0.5)

        # Analyze content complexity
        content_score = self._analyze_content_complexity(text_content)

        # Combine scores with weighting
        final_score = (base_score * 0.6) + (content_score * 0.4)

        # Ensure score is in valid range
        return max(0.0, min(1.0, final_score))

    def _extract_text_for_analysis(self, item: Dict[str, Any]) -> str:
        """Extract text content for complexity analysis."""
        content_parts = []

        if "question" in item:
            content_parts.append(str(item["question"]))
        if "context" in item:
            content_parts.append(str(item["context"]))
        if "python_solution" in item:
            content_parts.append(str(item["python_solution"]))

        return " ".join(content_parts)

    def _analyze_content_complexity(self, text: str) -> float:
        """Analyze text content for complexity indicators."""
        scores = {"high": 0, "medium": 0, "low": 0}

        # Keyword analysis
        for level, keywords in self.complexity_indicators.items():
            for keyword in keywords:
                if keyword in text:
                    scores[level] += 1

        # Pattern analysis (weighted higher)
        for level, patterns in self.complexity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    scores[level] += 2

        # Calculate weighted score
        total_indicators = sum(scores.values())
        if total_indicators == 0:
            return 0.5  # Default medium complexity

        weighted_score = (scores["high"] * 1.0 + scores["medium"] * 0.5 + scores["low"] * 0.1) / total_indicators

        return weighted_score


class MathematicalAnswerProcessor:
    """Processor for mathematical answer validation and conversion."""

    def __init__(self) -> None:
        """Initialize the answer processor."""
        self.numerical_patterns = {
            "integer": r"^-?\d+$",
            "float": r"^-?\d*\.\d+$",
            "scientific": r"^-?\d+\.?\d*e[+\-]?\d+$",
            "fraction": r"^-?\d+/\d+$",
            "percentage": r"^-?\d+\.?\d*%$",
            "currency": r"^\$-?\d+\.?\d*$",
        }

    def process_mathematical_answer(self, item: Dict[str, Any]) -> Tuple[str, Any]:
        """Process mathematical answer to determine type and value.

        Args:
            item: Dictionary containing answer data

        Returns:
            Tuple of (answer_type, processed_answer)
        """
        # Get the answer value
        ground_truth = item.get("ground_truth", item.get("answer", ""))

        if isinstance(ground_truth, (int, bool)):
            return "int", int(ground_truth)
        elif isinstance(ground_truth, float):
            return "float", float(ground_truth)
        elif isinstance(ground_truth, str):
            return self._process_string_answer(ground_truth)
        else:
            return "str", str(ground_truth)

    def _process_string_answer(self, answer_str: str) -> Tuple[str, Any]:
        """Process string answer to detect type and convert."""
        answer_str = str(answer_str).strip()

        # Try to detect and convert numerical types
        for answer_type, pattern in self.numerical_patterns.items():
            if re.match(pattern, answer_str):
                return self._convert_by_type(answer_str, answer_type)

        # Try basic numerical conversion
        try:
            # Try integer first
            if "." not in answer_str and "e" not in answer_str.lower():
                return "int", int(answer_str)
            else:
                return "float", float(answer_str)
        except ValueError:
            pass

        # Return as string if no conversion possible
        return "str", answer_str

    def _convert_by_type(self, answer_str: str, detected_type: str) -> Tuple[str, Any]:
        """Convert answer string based on detected type."""
        try:
            if detected_type == "integer":
                return "int", int(answer_str)
            elif detected_type == "float":
                return "float", float(answer_str)
            elif detected_type == "scientific":
                return "float", float(answer_str)
            elif detected_type == "fraction":
                # Convert fraction to float
                parts = answer_str.split("/")
                return "float", float(parts[0]) / float(parts[1])
            elif detected_type == "percentage":
                # Convert percentage to float
                num_str = answer_str.rstrip("%")
                return "float", float(num_str) / 100.0
            elif detected_type == "currency":
                # Convert currency to float
                num_str = answer_str.lstrip("$")
                return "float", float(num_str)
            else:
                return "str", answer_str
        except (ValueError, ZeroDivisionError, IndexError):
            return "str", answer_str


class MathematicalContextBuilder:
    """Builder for comprehensive mathematical context."""

    def build_mathematical_context(self, item: Dict[str, Any]) -> str:
        """Build comprehensive mathematical context from DocMath item.

        Args:
            item: Dictionary containing DocMath data

        Returns:
            String with formatted mathematical context
        """
        context_parts = []

        # Add document context
        if item.get("context"):
            context_parts.append(f"Document Context: {item['context']}")

        # Add paragraphs for mathematical reasoning
        if item.get("paragraphs"):
            context_parts.append("Relevant Paragraphs:")
            for i, para in enumerate(item["paragraphs"], 1):
                context_parts.append(f"Paragraph {i}: {para}")

        # Add table evidence if present
        if item.get("table_evidence"):
            context_parts.append("Table Evidence:")
            for i, table in enumerate(item["table_evidence"], 1):
                context_parts.append(f"Table {i}: {table}")

        # Add reasoning steps if available
        if item.get("reasoning_steps"):
            context_parts.append("Reasoning Steps:")
            for i, step in enumerate(item["reasoning_steps"], 1):
                context_parts.append(f"Step {i}: {step}")

        # Add Python solution if available
        if item.get("python_solution"):
            context_parts.append(f"Solution Code: {item['python_solution']}")

        # Add the mathematical question
        if item.get("question"):
            context_parts.append(f"Question: {item['question']}")

        return "\n\n".join(context_parts)
