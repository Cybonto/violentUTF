# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Legal categorization utility for LegalBench dataset converter (Issue #126).

Provides comprehensive legal domain classification, specialization mapping,
and complexity assessment for legal reasoning tasks across 8 primary categories.

SECURITY: All inputs are sanitized and validated to prevent injection attacks.
"""

import logging
from typing import Dict, List, Optional, Tuple

from app.core.validation import sanitize_string
from app.schemas.legalbench_datasets import (
    LegalCategory,
    LegalClassification,
    LegalComplexity,
    LegalSpecialization,
)


class LegalCategorizationEngine:
    """Advanced legal domain categorization engine for LegalBench tasks.

    Implements multi-factor classification using keyword analysis, content analysis,
    and domain expertise patterns to accurately categorize legal reasoning tasks.
    """

    def __init__(self) -> None:
        """Initialize the legal categorization engine."""
        self.logger = logging.getLogger(__name__)
        self._init_classification_patterns()
        self._init_complexity_indicators()
        self._init_specialization_mappings()

    def _init_classification_patterns(self) -> None:
        """Initialize legal category classification patterns."""
        self.legal_categories = {
            LegalCategory.CONTRACT: {
                "keywords": [
                    "cuad",
                    "contract",
                    "agreement",
                    "lease",
                    "nda",
                    "license",
                    "terms",
                    "breach",
                    "obligation",
                    "consideration",
                    "warranty",
                    "indemnif",
                    "assign",
                    "sublicense",
                    "termination",
                    "renewal",
                ],
                "description": "Contract analysis and interpretation",
                "complexity": LegalComplexity.MEDIUM,
                "specializations": [
                    "commercial",
                    "employment",
                    "real_estate",
                    "intellectual_property",
                    "construction",
                    "service",
                    "license",
                    "joint_venture",
                ],
            },
            LegalCategory.REGULATORY: {
                "keywords": [
                    "regulatory",
                    "compliance",
                    "cfr",
                    "regulation",
                    "policy",
                    "administrative",
                    "agency",
                    "enforcement",
                    "violation",
                    "permit",
                    "license",
                    "standards",
                    "guidelines",
                    "rules",
                ],
                "description": "Regulatory compliance and interpretation",
                "complexity": LegalComplexity.HIGH,
                "specializations": [
                    "financial",
                    "healthcare",
                    "environmental",
                    "securities",
                    "telecommunications",
                    "energy",
                    "transportation",
                    "data_privacy",
                ],
            },
            LegalCategory.JUDICIAL: {
                "keywords": [
                    "judicial",
                    "court",
                    "decision",
                    "opinion",
                    "ruling",
                    "judgment",
                    "appeal",
                    "precedent",
                    "case_law",
                    "holding",
                    "dicta",
                    "reasoning",
                    "rationale",
                    "analysis",
                    "interpretation",
                ],
                "description": "Judicial reasoning and case analysis",
                "complexity": LegalComplexity.HIGH,
                "specializations": [
                    "civil",
                    "criminal",
                    "appellate",
                    "constitutional",
                    "administrative",
                    "family",
                    "probate",
                    "bankruptcy",
                ],
            },
            LegalCategory.CIVIL: {
                "keywords": [
                    "civil",
                    "tort",
                    "liability",
                    "damages",
                    "negligence",
                    "personal_injury",
                    "property",
                    "defamation",
                    "privacy",
                    "nuisance",
                    "trespass",
                    "conversion",
                    "fraud",
                    "misrepresentation",
                ],
                "description": "Civil law and tort analysis",
                "complexity": LegalComplexity.MEDIUM,
                "specializations": [
                    "personal_injury",
                    "property",
                    "family",
                    "employment",
                    "medical_malpractice",
                    "products_liability",
                    "professional_liability",
                ],
            },
            LegalCategory.CRIMINAL: {
                "keywords": [
                    "criminal",
                    "penal",
                    "prosecution",
                    "defense",
                    "evidence",
                    "sentencing",
                    "plea",
                    "conviction",
                    "acquittal",
                    "charges",
                    "indictment",
                    "arrest",
                    "search",
                    "seizure",
                    "miranda",
                ],
                "description": "Criminal law and procedure",
                "complexity": LegalComplexity.HIGH,
                "specializations": [
                    "violent_crimes",
                    "white_collar",
                    "procedure",
                    "sentencing",
                    "constitutional_criminal",
                    "federal_crimes",
                    "juvenile",
                ],
            },
            LegalCategory.CONSTITUTIONAL: {
                "keywords": [
                    "constitutional",
                    "rights",
                    "amendment",
                    "due_process",
                    "equal_protection",
                    "first_amendment",
                    "fourth_amendment",
                    "commerce_clause",
                    "supremacy",
                    "federalism",
                    "separation_powers",
                ],
                "description": "Constitutional law and rights analysis",
                "complexity": LegalComplexity.VERY_HIGH,
                "specializations": [
                    "bill_of_rights",
                    "federalism",
                    "separation_of_powers",
                    "due_process",
                    "equal_protection",
                    "first_amendment",
                    "criminal_procedure",
                ],
            },
            LegalCategory.CORPORATE: {
                "keywords": [
                    "corporate",
                    "business",
                    "entity",
                    "governance",
                    "securities",
                    "merger",
                    "acquisition",
                    "board",
                    "shareholder",
                    "fiduciary",
                    "proxy",
                    "disclosure",
                    "insider_trading",
                    "sec",
                    "stock",
                ],
                "description": "Corporate law and business entity analysis",
                "complexity": LegalComplexity.MEDIUM,
                "specializations": [
                    "governance",
                    "mergers",
                    "securities",
                    "compliance",
                    "fiduciary_duty",
                    "shareholder_rights",
                    "public_companies",
                ],
            },
            LegalCategory.INTELLECTUAL_PROPERTY: {
                "keywords": [
                    "ip",
                    "patent",
                    "trademark",
                    "copyright",
                    "trade_secret",
                    "infringement",
                    "fair_use",
                    "licensing",
                    "royalty",
                    "prior_art",
                    "novelty",
                    "obviousness",
                    "dilution",
                    "dmca",
                ],
                "description": "Intellectual property law and analysis",
                "complexity": LegalComplexity.HIGH,
                "specializations": [
                    "patents",
                    "trademarks",
                    "copyrights",
                    "trade_secrets",
                    "licensing",
                    "technology_transfer",
                    "entertainment",
                ],
            },
        }

    def _init_complexity_indicators(self) -> None:
        """Initialize complexity assessment indicators."""
        self.complexity_indicators = {
            LegalComplexity.BASIC: {
                "keywords": ["basic", "simple", "elementary", "introductory"],
                "characteristics": ["single_issue", "clear_rule", "straightforward"],
            },
            LegalComplexity.MEDIUM: {
                "keywords": ["standard", "typical", "common", "intermediate"],
                "characteristics": ["multiple_factors", "balancing_test", "fact_intensive"],
            },
            LegalComplexity.HIGH: {
                "keywords": ["complex", "advanced", "sophisticated", "multi_factor"],
                "characteristics": ["constitutional_issues", "conflicting_precedents", "policy_considerations"],
            },
            LegalComplexity.VERY_HIGH: {
                "keywords": ["constitutional", "supreme_court", "landmark", "precedent_setting"],
                "characteristics": ["constitutional_interpretation", "circuit_split", "first_impression"],
            },
        }

    def _init_specialization_mappings(self) -> None:
        """Initialize legal specialization mappings."""
        self.specialization_keywords = {
            # Contract specializations
            "commercial": ["commercial", "business", "sale", "ucc", "goods"],
            "employment": ["employment", "labor", "workplace", "discrimination", "wage"],
            "real_estate": ["real_estate", "property", "land", "lease", "mortgage"],
            "construction": ["construction", "building", "contractor", "architect", "delay"],
            # Regulatory specializations
            "financial": ["banking", "finance", "investment", "securities", "credit"],
            "healthcare": ["health", "medical", "hipaa", "patient", "drug"],
            "environmental": ["environment", "epa", "pollution", "clean", "waste"],
            "data_privacy": ["privacy", "data", "gdpr", "ccpa", "personal_information"],
            # Civil specializations
            "personal_injury": ["injury", "accident", "negligence", "malpractice", "damages"],
            "medical_malpractice": ["medical", "doctor", "hospital", "malpractice", "standard_care"],
            "products_liability": ["product", "defective", "manufacturing", "design", "warning"],
            # Criminal specializations
            "white_collar": ["fraud", "embezzlement", "securities", "tax", "insider"],
            "violent_crimes": ["assault", "murder", "robbery", "violence", "weapon"],
            "procedure": ["search", "seizure", "miranda", "confession", "warrant"],
            # Constitutional specializations
            "first_amendment": ["speech", "religion", "press", "assembly", "petition"],
            "fourth_amendment": ["search", "seizure", "privacy", "warrant", "probable_cause"],
            "due_process": ["due_process", "procedural", "substantive", "fairness", "notice"],
            # Corporate specializations
            "governance": ["board", "director", "officer", "governance", "fiduciary"],
            "mergers": ["merger", "acquisition", "takeover", "proxy", "tender"],
            "securities": ["securities", "stock", "bond", "disclosure", "sec"],
            # IP specializations
            "patents": ["patent", "invention", "prior_art", "novelty", "obviousness"],
            "trademarks": ["trademark", "brand", "confusion", "dilution", "genericness"],
            "copyrights": ["copyright", "authorship", "fair_use", "derivative", "dmca"],
        }

    def classify_legal_task(self, task_name: str, task_content: Optional[Dict] = None) -> LegalClassification:
        """Classify legal task into appropriate category with specializations.

        Args:
            task_name: Legal task directory name
            task_content: Optional task content for enhanced classification

        Returns:
            Complete legal classification result
        """
        task_name = sanitize_string(task_name).lower()

        # Primary category detection
        primary_category, primary_confidence = self._detect_primary_category(task_name, task_content)

        # Specialization detection
        specializations = self._detect_specializations(task_name, task_content, primary_category)

        # Complexity assessment
        complexity = self._assess_complexity(task_name, task_content, primary_category)

        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(
            primary_confidence, specializations, task_content is not None
        )

        return LegalClassification(
            primary_category=primary_category,
            specializations=specializations,
            complexity=complexity,
            confidence=overall_confidence,
            classification_method="keyword_and_content_analysis",
        )

    def _detect_primary_category(
        self, task_name: str, task_content: Optional[Dict] = None
    ) -> Tuple[LegalCategory, float]:
        """Detect primary legal category with confidence score.

        Args:
            task_name: Sanitized task name in lowercase
            task_content: Optional task content for analysis

        Returns:
            Tuple of (primary_category, confidence_score)
        """
        category_scores = {}

        # Keyword-based scoring
        for category, info in self.legal_categories.items():
            score = 0.0
            matched_keywords = 0

            for keyword in info["keywords"]:
                if keyword.lower() in task_name:
                    score += 0.2
                    matched_keywords += 1

                    # Boost score for exact matches
                    if task_name.startswith(keyword.lower()):
                        score += 0.1

            # Normalize by keyword coverage
            if len(info["keywords"]) > 0:
                coverage = matched_keywords / len(info["keywords"])
                score *= 1.0 + coverage

            category_scores[category] = score

        # Content-based refinement if available
        if task_content:
            self._refine_scores_with_content(category_scores, task_content)

        # Select category with highest score
        if category_scores:
            best_category = max(category_scores.keys(), key=lambda k: category_scores[k])
            confidence = min(category_scores[best_category], 1.0)

            # Require minimum confidence threshold
            if confidence < 0.1:
                return LegalCategory.GENERAL, 0.5

            return best_category, confidence

        return LegalCategory.GENERAL, 0.5

    def _refine_scores_with_content(self, category_scores: Dict[LegalCategory, float], task_content: Dict) -> None:
        """Refine category scores using task content analysis.

        Args:
            category_scores: Current category scores (modified in-place)
            task_content: Task content for analysis
        """
        content_text = ""

        # Extract text content from various fields
        for _, value in task_content.items():
            if isinstance(value, str):
                content_text += " " + value.lower()

        if not content_text:
            return

        content_text = sanitize_string(content_text)

        # Boost scores based on content keywords
        for category, info in self.legal_categories.items():
            content_boost = 0.0

            for keyword in info["keywords"]:
                keyword_count = content_text.count(keyword.lower())
                if keyword_count > 0:
                    content_boost += min(keyword_count * 0.05, 0.2)

            category_scores[category] = category_scores.get(category, 0.0) + content_boost

    def _detect_specializations(
        self, task_name: str, task_content: Optional[Dict], primary_category: LegalCategory
    ) -> List[LegalSpecialization]:
        """Detect legal specializations within the primary category.

        Args:
            task_name: Sanitized task name in lowercase
            task_content: Optional task content for analysis
            primary_category: Primary legal category

        Returns:
            List of detected specializations
        """
        specializations = []
        category_info = self.legal_categories.get(primary_category, {})
        available_specs = category_info.get("specializations", [])

        for spec in available_specs:
            confidence, keywords_matched = self._calculate_specialization_confidence(spec, task_name, task_content)

            if confidence > 0.2:  # Minimum threshold for specialization
                specializations.append(
                    LegalSpecialization(area=spec, confidence=confidence, keywords_matched=keywords_matched)
                )

        # Sort by confidence and return top 3
        specializations.sort(key=lambda x: x.confidence, reverse=True)
        return specializations[:3]

    def _calculate_specialization_confidence(
        self, specialization: str, task_name: str, task_content: Optional[Dict]
    ) -> Tuple[float, List[str]]:
        """Calculate confidence score for a specific specialization.

        Args:
            specialization: Specialization area to evaluate
            task_name: Sanitized task name in lowercase
            task_content: Optional task content for analysis

        Returns:
            Tuple of (confidence_score, keywords_matched)
        """
        spec_keywords = self.specialization_keywords.get(specialization, [])
        if not spec_keywords:
            return 0.0, []

        matched_keywords = []
        confidence = 0.0

        # Check task name
        for keyword in spec_keywords:
            if keyword.lower() in task_name:
                confidence += 0.3
                matched_keywords.append(keyword)

        # Check content if available
        if task_content:
            content_text = ""
            for _, value in task_content.items():
                if isinstance(value, str):
                    content_text += " " + value.lower()

            content_text = sanitize_string(content_text)

            for keyword in spec_keywords:
                keyword_count = content_text.count(keyword.lower())
                if keyword_count > 0:
                    confidence += min(keyword_count * 0.1, 0.3)
                    if keyword not in matched_keywords:
                        matched_keywords.append(keyword)

        return min(confidence, 1.0), matched_keywords

    def _assess_complexity(
        self, task_name: str, task_content: Optional[Dict], primary_category: LegalCategory
    ) -> LegalComplexity:
        """Assess legal complexity of the task.

        Args:
            task_name: Sanitized task name in lowercase
            task_content: Optional task content for analysis
            primary_category: Primary legal category

        Returns:
            Legal complexity assessment
        """
        # Default complexity based on category
        default_complexity = self.legal_categories.get(primary_category, {}).get("complexity", LegalComplexity.MEDIUM)

        complexity_scores = {
            LegalComplexity.BASIC: 0.0,
            LegalComplexity.MEDIUM: 0.5,  # Default baseline
            LegalComplexity.HIGH: 0.0,
            LegalComplexity.VERY_HIGH: 0.0,
        }

        # Keyword-based complexity assessment
        for complexity, info in self.complexity_indicators.items():
            for keyword in info["keywords"]:
                if keyword.lower() in task_name:
                    complexity_scores[complexity] += 0.3

            for characteristic in info["characteristics"]:
                if characteristic.lower().replace("_", " ") in task_name:
                    complexity_scores[complexity] += 0.2

        # Content-based complexity refinement
        if task_content:
            self._refine_complexity_with_content(complexity_scores, task_content)

        # Select complexity with highest score, fallback to default
        max_score = max(complexity_scores.values())
        if max_score > 0.6:
            return max(complexity_scores.keys(), key=lambda k: complexity_scores[k])

        return default_complexity

    def _refine_complexity_with_content(
        self, complexity_scores: Dict[LegalComplexity, float], task_content: Dict
    ) -> None:
        """Refine complexity scores using content analysis.

        Args:
            complexity_scores: Current complexity scores (modified in-place)
            task_content: Task content for analysis
        """
        content_text = ""
        for _, value in task_content.items():
            if isinstance(value, str):
                content_text += " " + value.lower()

        if not content_text:
            return

        content_text = sanitize_string(content_text)

        # High complexity indicators
        high_complexity_terms = [
            "constitutional",
            "supreme court",
            "circuit split",
            "precedent",
            "balancing test",
            "strict scrutiny",
            "intermediate scrutiny",
            "compelling interest",
            "least restrictive means",
            "statutory interpretation",
        ]

        for term in high_complexity_terms:
            if term in content_text:
                complexity_scores[LegalComplexity.HIGH] += 0.2
                complexity_scores[LegalComplexity.VERY_HIGH] += 0.1

        # Very high complexity indicators
        very_high_complexity_terms = [
            "first impression",
            "landmark",
            "overrule",
            "constitutional interpretation",
            "fundamental right",
            "suspect classification",
            "commerce clause",
        ]

        for term in very_high_complexity_terms:
            if term in content_text:
                complexity_scores[LegalComplexity.VERY_HIGH] += 0.3

    def _calculate_overall_confidence(
        self, primary_confidence: float, specializations: List[LegalSpecialization], has_content: bool
    ) -> float:
        """Calculate overall classification confidence.

        Args:
            primary_confidence: Primary category confidence
            specializations: Detected specializations
            has_content: Whether task content was available for analysis

        Returns:
            Overall confidence score
        """
        # Base confidence from primary category
        confidence = primary_confidence

        # Boost from specializations
        if specializations:
            spec_boost = sum(spec.confidence for spec in specializations) / len(specializations)
            confidence += spec_boost * 0.2

        # Boost from content availability
        if has_content:
            confidence += 0.1

        return min(confidence, 1.0)

    def get_legal_expertise_areas(self, task_name: str) -> List[str]:
        """Get relevant legal expertise areas for professional validation.

        Args:
            task_name: Legal task name

        Returns:
            List of relevant expertise areas
        """
        task_name = sanitize_string(task_name).lower()
        classification = self.classify_legal_task(task_name)

        expertise_areas = [classification.primary_category.value]

        # Add specialization areas
        for spec in classification.specializations:
            expertise_areas.append(spec.area)

        # Add general areas based on complexity
        if classification.complexity == LegalComplexity.VERY_HIGH:
            expertise_areas.extend(["constitutional_law", "appellate_practice"])
        elif classification.complexity == LegalComplexity.HIGH:
            expertise_areas.extend(["advanced_legal_analysis", "complex_litigation"])

        return list(set(expertise_areas))  # Remove duplicates

    def validate_legal_classification(self, classification: LegalClassification) -> List[str]:
        """Validate legal classification result.

        Args:
            classification: Legal classification to validate

        Returns:
            List of validation warnings (empty if valid)
        """
        warnings = []

        # Check confidence thresholds
        if classification.confidence < 0.3:
            warnings.append("Low classification confidence - may need manual review")

        # Check specialization consistency
        category_info = self.legal_categories.get(classification.primary_category, {})
        available_specs = set(category_info.get("specializations", []))

        for spec in classification.specializations:
            if spec.area not in available_specs:
                warnings.append(f"Specialization '{spec.area}' not typical for {classification.primary_category.value}")

        # Check complexity consistency
        expected_complexity = category_info.get("complexity", LegalComplexity.MEDIUM)
        if classification.complexity != expected_complexity:
            complexity_diff = abs(
                list(LegalComplexity).index(classification.complexity)
                - list(LegalComplexity).index(expected_complexity)
            )
            if complexity_diff > 1:
                warnings.append("Complexity assessment may be inconsistent with category")

        return warnings
