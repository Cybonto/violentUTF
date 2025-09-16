# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Planning Service Implementation (Issue #125).

Implements domain classification and scenario analysis for ACPBench planning tasks.
Provides intelligent classification of planning domains, complexity assessment,
and key concept extraction for planning reasoning datasets.

SECURITY: All content analysis is for defensive security research only.
"""

import logging
import re
from typing import List, Tuple

from app.core.validation import sanitize_string
from app.schemas.acpbench_datasets import (
    PlanningAnalysisResult,
    PlanningComplexity,
    PlanningDomain,
    PlanningDomainInfo,
    PlanningScenarioContext,
)


class PlanningDomainClassifier:
    """Classifies planning domains based on context and question analysis.

    Uses pattern-based detection and concept extraction to classify planning
    tasks into appropriate domains with confidence scoring.
    """

    def __init__(self) -> None:
        """Initialize the planning domain classifier."""
        self.logger = logging.getLogger(__name__)

        # Domain classification patterns with weighted scoring
        self.domain_patterns = {
            PlanningDomain.LOGISTICS: {
                "keywords": [
                    "truck",
                    "package",
                    "deliver",
                    "warehouse",
                    "location",
                    "cargo",
                    "shipping",
                    "transport",
                    "route",
                    "distribution",
                    "supply",
                    "depot",
                    "vehicle",
                    "pickup",
                    "dropoff",
                    "delivery",
                ],
                "concepts": [
                    "transportation planning",
                    "delivery optimization",
                    "route planning",
                    "supply chain",
                    "vehicle routing",
                    "distribution network",
                ],
                "weight": 1.0,
            },
            PlanningDomain.BLOCKS_WORLD: {
                "keywords": [
                    "block",
                    "stack",
                    "table",
                    "on",
                    "clear",
                    "under",
                    "above",
                    "move",
                    "place",
                    "tower",
                    "grip",
                    "arm",
                    "robot",
                    "manipulator",
                ],
                "concepts": [
                    "block stacking",
                    "spatial reasoning",
                    "object manipulation",
                    "robot planning",
                    "physical constraints",
                    "tower building",
                ],
                "weight": 1.2,  # Higher weight for specific domain
            },
            PlanningDomain.SCHEDULING: {
                "keywords": [
                    "schedule",
                    "time",
                    "resource",
                    "task",
                    "assignment",
                    "deadline",
                    "priority",
                    "conflict",
                    "allocation",
                    "duration",
                    "timeline",
                    "meeting",
                    "appointment",
                    "calendar",
                    "shift",
                ],
                "concepts": [
                    "resource scheduling",
                    "time management",
                    "task assignment",
                    "constraint satisfaction",
                    "temporal planning",
                    "resource allocation",
                ],
                "weight": 1.0,
            },
            PlanningDomain.GENERAL_PLANNING: {
                "keywords": [
                    "goal",
                    "action",
                    "state",
                    "plan",
                    "sequence",
                    "step",
                    "agent",
                    "objective",
                    "strategy",
                    "solution",
                    "problem",
                    "method",
                    "approach",
                    "procedure",
                    "algorithm",
                    "optimization",
                ],
                "concepts": [
                    "goal achievement",
                    "action planning",
                    "problem solving",
                    "strategic planning",
                    "multi-step reasoning",
                    "optimization",
                ],
                "weight": 0.8,  # Lower weight as fallback domain
            },
            PlanningDomain.GRAPH_PLANNING: {
                "keywords": [
                    "graph",
                    "node",
                    "edge",
                    "path",
                    "vertex",
                    "network",
                    "connection",
                    "traversal",
                    "shortest",
                    "distance",
                    "neighbor",
                    "adjacent",
                    "topology",
                    "structure",
                    "connectivity",
                ],
                "concepts": [
                    "graph traversal",
                    "path finding",
                    "network analysis",
                    "connectivity planning",
                    "graph algorithms",
                    "topology optimization",
                ],
                "weight": 1.1,
            },
            PlanningDomain.ROUTE_PLANNING: {
                "keywords": [
                    "route",
                    "path",
                    "navigation",
                    "map",
                    "direction",
                    "waypoint",
                    "destination",
                    "journey",
                    "travel",
                    "distance",
                    "shortest",
                    "optimal",
                    "traffic",
                    "road",
                    "highway",
                ],
                "concepts": [
                    "route optimization",
                    "path planning",
                    "navigation planning",
                    "travel optimization",
                    "geographic planning",
                    "waypoint planning",
                ],
                "weight": 1.0,
            },
            PlanningDomain.RESOURCE_ALLOCATION: {
                "keywords": [
                    "resource",
                    "allocate",
                    "assign",
                    "capacity",
                    "availability",
                    "constraint",
                    "limit",
                    "budget",
                    "cost",
                    "efficient",
                    "optimal",
                    "distribute",
                    "share",
                    "manage",
                    "utilize",
                ],
                "concepts": [
                    "resource management",
                    "allocation optimization",
                    "capacity planning",
                    "constraint satisfaction",
                    "resource distribution",
                    "efficiency optimization",
                ],
                "weight": 1.0,
            },
        }

        # Complexity indicators with scoring weights
        self.complexity_indicators = {
            PlanningComplexity.HIGH: {
                "keywords": [
                    "optimization",
                    "multiple agents",
                    "constraints",
                    "temporal",
                    "complex",
                    "advanced",
                    "sophisticated",
                    "multi-objective",
                    "hierarchical",
                    "coordination",
                    "parallel",
                    "concurrent",
                ],
                "concepts": [
                    "multi-agent coordination",
                    "constraint optimization",
                    "temporal reasoning",
                    "hierarchical planning",
                    "complex dependencies",
                    "parallel execution",
                ],
                "weight": 2.0,
            },
            PlanningComplexity.MEDIUM: {
                "keywords": [
                    "sequence",
                    "planning",
                    "coordination",
                    "logistics",
                    "multiple",
                    "steps",
                    "dependencies",
                    "intermediate",
                    "moderate",
                    "balanced",
                ],
                "concepts": [
                    "sequential planning",
                    "moderate coordination",
                    "multi-step execution",
                    "dependency management",
                    "balanced complexity",
                    "structured approach",
                ],
                "weight": 1.5,
            },
            PlanningComplexity.LOW: {
                "keywords": [
                    "simple",
                    "basic",
                    "single",
                    "direct",
                    "straightforward",
                    "easy",
                    "elementary",
                    "fundamental",
                    "minimal",
                    "clear",
                ],
                "concepts": [
                    "simple execution",
                    "basic planning",
                    "minimal dependencies",
                    "straightforward solution",
                    "elementary reasoning",
                    "direct approach",
                ],
                "weight": 1.0,
            },
        }

    def classify_domain(self, context: str, question: str) -> Tuple[PlanningDomain, float]:
        """Classify the planning domain for given context and question.

        Args:
            context: Planning scenario context
            question: Question text

        Returns:
            Tuple of (PlanningDomain, confidence_score)
        """
        context = sanitize_string(context)
        question = sanitize_string(question)
        combined_text = f"{context} {question}".lower()

        domain_scores = {}

        # Calculate scores for each domain
        for domain, patterns in self.domain_patterns.items():
            score = 0.0

            # Keyword matching with frequency weighting
            for keyword in patterns["keywords"]:
                matches = len(re.findall(r"\b" + re.escape(keyword) + r"\b", combined_text))
                score += matches * patterns["weight"]

            # Concept matching (partial matches allowed)
            for concept in patterns["concepts"]:
                concept_words = concept.lower().split()
                concept_matches = sum(1 for word in concept_words if word in combined_text)
                if concept_matches > 0:
                    concept_score = (concept_matches / len(concept_words)) * patterns["weight"]
                    score += concept_score

            domain_scores[domain] = score

        # Find best matching domain
        if not domain_scores or max(domain_scores.values()) == 0:
            return PlanningDomain.GENERAL_PLANNING, 0.1

        best_domain = max(domain_scores, key=domain_scores.get)
        max_score = domain_scores[best_domain]

        # Calculate confidence (normalize by text length and expected score range)
        text_length = len(combined_text.split())
        confidence = min(1.0, max_score / max(10, text_length * 0.1))
        confidence = max(0.1, confidence)  # Minimum confidence threshold

        return best_domain, confidence

    def assess_complexity(self, context: str, question: str, domain: PlanningDomain) -> PlanningComplexity:
        """Assess the complexity level of a planning task.

        Args:
            context: Planning scenario context
            question: Question text
            domain: Planning domain

        Returns:
            PlanningComplexity level
        """
        context = sanitize_string(context)
        question = sanitize_string(question)
        combined_text = f"{context} {question}".lower()

        complexity_scores = {}

        # Calculate scores for each complexity level
        for complexity, patterns in self.complexity_indicators.items():
            score = 0.0

            # Keyword matching
            for keyword in patterns["keywords"]:
                if keyword in combined_text:
                    score += patterns["weight"]

            # Concept matching
            for concept in patterns["concepts"]:
                concept_words = concept.lower().split()
                concept_matches = sum(1 for word in concept_words if word in combined_text)
                if concept_matches > 0:
                    concept_score = (concept_matches / len(concept_words)) * patterns["weight"]
                    score += concept_score

            complexity_scores[complexity] = score

        # Apply domain-specific complexity adjustments
        if domain == PlanningDomain.BLOCKS_WORLD:
            # Blocks world is generally simpler
            complexity_scores[PlanningComplexity.LOW] *= 1.2
        elif domain == PlanningDomain.GENERAL_PLANNING:
            # General planning tends to be more complex
            complexity_scores[PlanningComplexity.HIGH] *= 1.2
        elif domain == PlanningDomain.LOGISTICS:
            # Logistics has medium baseline complexity
            complexity_scores[PlanningComplexity.MEDIUM] *= 1.1

        # Determine complexity based on scores
        if not complexity_scores or max(complexity_scores.values()) == 0:
            return PlanningComplexity.MEDIUM  # Default

        return max(complexity_scores, key=complexity_scores.get)

    def extract_key_concepts(self, context: str, question: str, domain: PlanningDomain) -> List[str]:
        """Extract key concepts from planning content.

        Args:
            context: Planning scenario context
            question: Question text
            domain: Planning domain

        Returns:
            List of key concepts found
        """
        context = sanitize_string(context)
        question = sanitize_string(question)
        combined_text = f"{context} {question}".lower()

        key_concepts = []

        # Extract domain-specific concepts
        domain_patterns = self.domain_patterns.get(domain, {})

        # Find matching keywords
        for keyword in domain_patterns.get("keywords", []):
            if re.search(r"\b" + re.escape(keyword) + r"\b", combined_text):
                key_concepts.append(keyword)

        # Find matching high-level concepts
        for concept in domain_patterns.get("concepts", []):
            concept_words = concept.lower().split()
            matches = sum(1 for word in concept_words if word in combined_text)
            if matches >= len(concept_words) * 0.5:  # At least 50% of concept words match
                key_concepts.append(concept)

        # Extract numerical and entity concepts using regex patterns
        additional_patterns = {
            "numbers": r"\b\d+\b",
            "time_references": r"\b(?:time|hour|minute|day|week|schedule)\b",
            "agents": r"\b(?:agent|robot|person|truck|vehicle)\b",
            "locations": r"\b(?:location|place|position|site|warehouse|depot)\b",
            "actions": r"\b(?:move|deliver|pick|place|transport|carry)\b",
            "constraints": r"\b(?:constraint|limit|deadline|capacity|maximum|minimum)\b",
        }

        for concept_type, pattern in additional_patterns.items():
            matches = re.findall(pattern, combined_text)
            if matches:
                key_concepts.append(f"{concept_type}: {len(matches)} occurrences")

        # Remove duplicates while preserving order
        seen = set()
        unique_concepts = []
        for concept in key_concepts:
            if concept not in seen:
                seen.add(concept)
                unique_concepts.append(concept)

        return unique_concepts[:10]  # Limit to top 10 concepts

    def get_domain_info(self, domain: PlanningDomain) -> PlanningDomainInfo:
        """Get information about a planning domain.

        Args:
            domain: Planning domain to get info for

        Returns:
            PlanningDomainInfo with domain details
        """
        domain_config = self.domain_patterns.get(domain, {})

        # Determine baseline complexity for domain
        complexity_map = {
            PlanningDomain.BLOCKS_WORLD: PlanningComplexity.LOW,
            PlanningDomain.LOGISTICS: PlanningComplexity.MEDIUM,
            PlanningDomain.SCHEDULING: PlanningComplexity.HIGH,
            PlanningDomain.GENERAL_PLANNING: PlanningComplexity.HIGH,
            PlanningDomain.GRAPH_PLANNING: PlanningComplexity.MEDIUM,
            PlanningDomain.ROUTE_PLANNING: PlanningComplexity.MEDIUM,
            PlanningDomain.RESOURCE_ALLOCATION: PlanningComplexity.HIGH,
        }

        descriptions = {
            PlanningDomain.LOGISTICS: "Transportation and delivery planning with vehicles, packages, and locations",
            PlanningDomain.BLOCKS_WORLD: "Block manipulation and stacking with spatial constraints",
            PlanningDomain.SCHEDULING: "Resource and time scheduling with conflicts and priorities",
            PlanningDomain.GENERAL_PLANNING: "Generic planning scenarios with goals and action sequences",
            PlanningDomain.GRAPH_PLANNING: "Graph-based planning with nodes, edges, and path finding",
            PlanningDomain.ROUTE_PLANNING: "Route optimization and navigation planning",
            PlanningDomain.RESOURCE_ALLOCATION: "Resource management and allocation optimization",
        }

        return PlanningDomainInfo(
            domain=domain,
            description=descriptions.get(domain, "Unknown planning domain"),
            complexity=complexity_map.get(domain, PlanningComplexity.MEDIUM),
            key_concepts=domain_config.get("concepts", []),
            confidence_score=0.9,  # High confidence for known domains
        )


class PlanningScenarioAnalyzer:
    """Analyzes planning scenarios for comprehensive metadata extraction.

    Combines domain classification, complexity assessment, and concept extraction
    to provide comprehensive analysis of planning tasks.
    """

    def __init__(self) -> None:
        """Initialize the planning scenario analyzer."""
        self.domain_classifier = PlanningDomainClassifier()
        self.logger = logging.getLogger(__name__)

    def analyze_scenario(
        self, scenario_id: str, planning_group: str, context: str, question: str
    ) -> PlanningAnalysisResult:
        """Perform comprehensive analysis of a planning scenario.

        Args:
            scenario_id: Unique identifier for the scenario
            planning_group: Planning group/category
            context: Planning scenario context
            question: Question text

        Returns:
            PlanningAnalysisResult with complete analysis
        """
        context = sanitize_string(context)
        question = sanitize_string(question)

        # Classify domain with confidence
        domain, domain_confidence = self.domain_classifier.classify_domain(context, question)

        # Assess complexity
        complexity = self.domain_classifier.assess_complexity(context, question, domain)

        # Extract key concepts
        key_concepts = self.domain_classifier.extract_key_concepts(context, question, domain)

        # Calculate complexity confidence based on indicators found
        complexity_confidence = self._calculate_complexity_confidence(context, question, complexity)

        # Generate analysis metadata
        analysis_metadata = {
            "scenario_id": scenario_id,
            "planning_group": planning_group,
            "context_length": len(context),
            "question_length": len(question),
            "total_concepts_found": len(key_concepts),
            "analysis_method": "pattern_based_classification",
        }

        return PlanningAnalysisResult(
            domain=domain,
            domain_confidence=domain_confidence,
            complexity=complexity,
            complexity_confidence=complexity_confidence,
            key_concepts=key_concepts,
            analysis_metadata=analysis_metadata,
        )

    def create_scenario_context(
        self, scenario_id: str, planning_group: str, context: str, question: str
    ) -> PlanningScenarioContext:
        """Create a comprehensive planning scenario context.

        Args:
            scenario_id: Unique scenario identifier
            planning_group: Planning group/category
            context: Scenario context text
            question: Question text

        Returns:
            PlanningScenarioContext with full scenario information
        """
        # Perform analysis
        analysis = self.analyze_scenario(scenario_id, planning_group, context, question)

        # Create metadata
        metadata = {
            "domain_confidence": analysis.domain_confidence,
            "complexity_confidence": analysis.complexity_confidence,
            "analysis_timestamp": analysis.analysis_timestamp,
            "analysis_metadata": analysis.analysis_metadata,
        }

        return PlanningScenarioContext(
            scenario_id=scenario_id,
            planning_group=planning_group,
            domain=analysis.domain,
            complexity=analysis.complexity,
            context_text=context,
            question_text=question,
            key_concepts=analysis.key_concepts,
            metadata=metadata,
        )

    def _calculate_complexity_confidence(
        self, context: str, question: str, assessed_complexity: PlanningComplexity
    ) -> float:
        """Calculate confidence score for complexity assessment.

        Args:
            context: Planning context
            question: Question text
            assessed_complexity: Assessed complexity level

        Returns:
            Confidence score between 0.0 and 1.0
        """
        combined_text = f"{context} {question}".lower()

        # Get patterns for assessed complexity
        complexity_patterns = self.domain_classifier.complexity_indicators.get(assessed_complexity, {})

        # Count indicator matches
        keyword_matches = sum(1 for keyword in complexity_patterns.get("keywords", []) if keyword in combined_text)

        concept_matches = sum(
            1
            for concept in complexity_patterns.get("concepts", [])
            if any(word in combined_text for word in concept.lower().split())
        )

        total_indicators = len(complexity_patterns.get("keywords", [])) + len(complexity_patterns.get("concepts", []))

        if total_indicators == 0:
            return 0.5  # Neutral confidence

        # Calculate confidence based on match ratio
        total_matches = keyword_matches + concept_matches
        confidence = min(1.0, total_matches / (total_indicators * 0.3))  # 30% match = high confidence

        return max(0.1, confidence)  # Minimum confidence threshold
