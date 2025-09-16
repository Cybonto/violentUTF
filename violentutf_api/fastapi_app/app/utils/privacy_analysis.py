# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Privacy analysis utilities for ConfAIde dataset converter.

This module implements core privacy analysis utilities based on Contextual Integrity
Theory for processing privacy-sensitive prompts and scenarios.

Components:
- ContextualFactorExtractor: Extracts CI Theory factors (actors, attributes, principles)
- InformationTypeClassifier: Classifies information types for privacy analysis
- PrivacyNormsAnalyzer: Determines applicable privacy norms and conflicts

SECURITY: All input text is sanitized to prevent injection attacks.
"""
import re
from typing import Any, Dict, List, Optional

from app.core.validation import sanitize_file_content
from app.schemas.confaide_datasets import (
    ContextualActor,
    InformationType,
    PrivacyNorms,
    PrivacyTier,
    TransmissionPrinciple,
)

# Privacy information type patterns and keywords
PRIVACY_INFORMATION_TYPES = {
    InformationType.PERSONAL_IDENTIFIERS: {
        "keywords": [
            "name",
            "address",
            "ssn",
            "social security",
            "id number",
            "phone",
            "email",
            "identifier",
            "personal identification",
            "contact information",
            "full name",
        ],
        "patterns": [
            r"\b(full\s+)?name\b",
            r"\baddress\b",
            r"\bphone\s+(number)?\b",
            r"\bemail\b",
            r"\bssn\b",
            r"\bsocial\s+security\b",
            r"\bid\s+number\b",
            r"\bcontact\s+info\b",
        ],
        "sensitivity": "high",
        "contexts": ["government", "healthcare", "financial", "employment"],
    },
    InformationType.MEDICAL_INFORMATION: {
        "keywords": [
            "health",
            "medical",
            "diagnosis",
            "treatment",
            "medication",
            "symptom",
            "condition",
            "patient",
            "doctor",
            "hospital",
            "therapy",
            "illness",
            "disease",
        ],
        "patterns": [
            r"\bmedical\s+(record|condition|history)\b",
            r"\bhealth\s+(data|info)\b",
            r"\bpatient\s+(data|info)\b",
            r"\bdiagnosis\b",
            r"\btreatment\b",
        ],
        "sensitivity": "very_high",
        "contexts": ["healthcare", "insurance", "research", "pharmacy"],
    },
    InformationType.FINANCIAL_INFORMATION: {
        "keywords": [
            "salary",
            "income",
            "credit",
            "bank",
            "financial",
            "debt",
            "loan",
            "payment",
            "account",
            "transaction",
            "money",
            "economic",
            "finance",
            "credit score",
        ],
        "patterns": [
            r"\bsalary\b",
            r"\bincome\b",
            r"\bcredit\s+(score|card)\b",
            r"\bbank\s+account\b",
            r"\bfinancial\s+(data|info)\b",
            r"\btransaction\s+(data|history)\b",
        ],
        "sensitivity": "high",
        "contexts": ["banking", "employment", "lending", "insurance", "taxation"],
    },
    InformationType.BEHAVIORAL_DATA: {
        "keywords": [
            "browsing",
            "location",
            "activity",
            "preferences",
            "habits",
            "behavior",
            "tracking",
            "usage",
            "interaction",
            "pattern",
            "movement",
            "online activity",
        ],
        "patterns": [
            r"\bbrowsing\s+(history|data)\b",
            r"\blocation\s+(data|tracking)\b",
            r"\bactivity\s+(data|log)\b",
            r"\busage\s+(pattern|data)\b",
        ],
        "sensitivity": "medium",
        "contexts": ["technology", "marketing", "research", "social media"],
    },
    InformationType.COMMUNICATION_CONTENT: {
        "keywords": [
            "message",
            "email",
            "chat",
            "conversation",
            "correspondence",
            "communication",
            "text",
            "call",
            "voice",
            "recording",
            "transcript",
            "discussion",
        ],
        "patterns": [
            r"\bmessage\s+(content|data)\b",
            r"\bemail\s+(content|correspondence)\b",
            r"\bconversation\s+(data|record)\b",
            r"\bcommunication\s+(data|log)\b",
        ],
        "sensitivity": "medium_high",
        "contexts": ["personal", "professional", "legal", "social"],
    },
    InformationType.BIOMETRIC_DATA: {
        "keywords": [
            "fingerprint",
            "facial",
            "voice",
            "dna",
            "biometric",
            "iris",
            "retina",
            "palm",
            "biological",
            "physiological",
            "genetic",
            "scan",
            "recognition",
        ],
        "patterns": [
            r"\bfingerprint\s+(data|scan)\b",
            r"\bfacial\s+recognition\b",
            r"\bvoice\s+(print|recognition)\b",
            r"\bdna\s+(data|profile)\b",
            r"\bbiometric\s+(data|info)\b",
        ],
        "sensitivity": "very_high",
        "contexts": ["security", "law_enforcement", "healthcare", "border_control"],
    },
    InformationType.LOCATION_DATA: {
        "keywords": [
            "location",
            "gps",
            "coordinates",
            "address",
            "place",
            "geolocation",
            "position",
            "whereabouts",
            "geographic",
            "spatial",
            "movement",
            "travel",
        ],
        "patterns": [
            r"\blocation\s+(data|tracking)\b",
            r"\bgps\s+(data|coordinates)\b",
            r"\bgeolocation\b",
            r"\bmovement\s+(data|tracking)\b",
        ],
        "sensitivity": "high",
        "contexts": ["navigation", "marketing", "social", "surveillance"],
    },
    InformationType.SENSITIVE_PERSONAL: {
        "keywords": [
            "religion",
            "political",
            "sexual",
            "orientation",
            "race",
            "ethnicity",
            "beliefs",
            "opinions",
            "affiliation",
            "preference",
            "ideology",
            "faith",
        ],
        "patterns": [
            r"\breligious\s+(belief|affiliation)\b",
            r"\bpolitical\s+(opinion|view)\b",
            r"\bsexual\s+orientation\b",
            r"\bethnic\s+(background|origin)\b",
        ],
        "sensitivity": "very_high",
        "contexts": ["social", "political", "religious", "personal"],
    },
}

# Contextual factors for Contextual Integrity Theory
CONTEXTUAL_FACTORS = {
    "actors": {
        ContextualActor.DATA_SUBJECT: [
            "individual",
            "person",
            "user",
            "patient",
            "customer",
            "citizen",
            "employee",
            "client",
            "participant",
            "subject",
            "consumer",
            "resident",
            "member",
        ],
        ContextualActor.DATA_HOLDER: [
            "company",
            "organization",
            "institution",
            "service provider",
            "employer",
            "hospital",
            "clinic",
            "bank",
            "platform",
            "website",
            "system",
            "entity",
        ],
        ContextualActor.DATA_RECEIVER: [
            "third party",
            "partner",
            "government",
            "researcher",
            "advertiser",
            "contractor",
            "vendor",
            "affiliate",
            "collaborator",
            "agency",
        ],
        ContextualActor.GOVERNMENT: [
            "government",
            "agency",
            "authority",
            "regulator",
            "official",
            "state",
            "federal",
            "local",
            "public sector",
            "law enforcement",
            "court",
        ],
        ContextualActor.RESEARCHER: [
            "researcher",
            "scientist",
            "academic",
            "study",
            "research team",
            "university",
            "institution",
            "laboratory",
            "investigator",
        ],
    },
    "attributes": {
        "personal": ["identity", "demographics", "preferences", "characteristics"],
        "sensitive": ["health", "financial", "intimate", "private", "confidential"],
        "behavioral": ["activity", "location", "communication", "usage", "interaction"],
    },
    "transmission_principles": {
        TransmissionPrinciple.PURPOSE_LIMITATION: [
            "purpose",
            "intended use",
            "specific use",
            "limited use",
            "designated purpose",
        ],
        TransmissionPrinciple.DATA_MINIMIZATION: [
            "necessary",
            "minimal",
            "sufficient",
            "required",
            "adequate",
            "proportional",
        ],
        TransmissionPrinciple.CONSENT_BASED: [
            "consent",
            "permission",
            "agreement",
            "authorization",
            "approval",
            "opt-in",
        ],
        TransmissionPrinciple.LEGAL_OBLIGATION: ["legal", "law", "regulation", "compliance", "requirement", "mandate"],
        TransmissionPrinciple.LEGITIMATE_INTEREST: [
            "legitimate interest",
            "business need",
            "operational",
            "security",
            "safety",
        ],
    },
}


class ContextualFactorExtractor:
    """Extracts Contextual Integrity Theory factors from privacy scenarios.

    Identifies actors, attributes, and transmission principles in privacy contexts
    to support comprehensive privacy analysis.
    """

    def __init__(self) -> None:
        """Initialize the contextual factor extractor with detection patterns."""
        self._actor_patterns = self._compile_actor_patterns()
        self._attribute_patterns = self._compile_attribute_patterns()
        self._principle_patterns = self._compile_principle_patterns()

    def extract_factors(self, prompt_text: str) -> Dict[str, Any]:
        """Extract contextual factors from prompt text.

        Args:
            prompt_text: Text to analyze for contextual factors

        Returns:
            Dictionary containing extracted contextual factors
        """
        prompt_text = sanitize_file_content(prompt_text)
        text_lower = prompt_text.lower()

        # Extract actors
        actors = self._extract_actors(text_lower)

        # Extract attributes
        attributes = self._extract_attributes(text_lower)

        # Extract transmission principles
        principles = self._extract_transmission_principles(text_lower)

        # Generate context description
        context_description = self._generate_context_description(prompt_text, actors, attributes, principles)

        return {
            "actors": actors,
            "attributes": attributes,
            "transmission_principles": principles,
            "context_description": context_description,
        }

    def _compile_actor_patterns(self) -> Dict[ContextualActor, List[re.Pattern]]:
        """Compile regex patterns for actor detection."""
        patterns = {}
        for actor, keywords in CONTEXTUAL_FACTORS["actors"].items():
            patterns[actor] = [re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE) for keyword in keywords]
        return patterns

    def _compile_attribute_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for attribute detection."""
        patterns = {}
        for attr_type, keywords in CONTEXTUAL_FACTORS["attributes"].items():
            patterns[attr_type] = [re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE) for keyword in keywords]
        return patterns

    def _compile_principle_patterns(self) -> Dict[TransmissionPrinciple, List[re.Pattern]]:
        """Compile regex patterns for transmission principle detection."""
        patterns = {}
        for principle, keywords in CONTEXTUAL_FACTORS["transmission_principles"].items():
            patterns[principle] = [re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE) for keyword in keywords]
        return patterns

    def _extract_actors(self, text: str) -> Dict[str, List[str]]:
        """Extract actors from text."""
        found_actors = {}

        for actor, patterns in self._actor_patterns.items():
            matches = []
            for pattern in patterns:
                if pattern.search(text):
                    matches.append(pattern.pattern.replace(r"\b", "").replace(r"\B", ""))

            if matches:
                found_actors[actor.value] = list(set(matches))  # Remove duplicates

        return found_actors

    def _extract_attributes(self, text: str) -> Dict[str, List[str]]:
        """Extract information attributes from text."""
        found_attributes = {}

        for attr_type, patterns in self._attribute_patterns.items():
            matches = []
            for pattern in patterns:
                if pattern.search(text):
                    matches.append(pattern.pattern.replace(r"\b", "").replace(r"\B", ""))

            if matches:
                found_attributes[attr_type] = list(set(matches))

        return found_attributes

    def _extract_transmission_principles(self, text: str) -> Dict[str, List[str]]:
        """Extract transmission principles from text."""
        found_principles = {}

        for principle, patterns in self._principle_patterns.items():
            matches = []
            for pattern in patterns:
                if pattern.search(text):
                    matches.append(pattern.pattern.replace(r"\b", "").replace(r"\B", ""))

            if matches:
                found_principles[principle.value] = list(set(matches))

        return found_principles

    def _generate_context_description(self, text: str, actors: Dict, attributes: Dict, principles: Dict) -> str:
        """Generate a context description based on extracted factors."""
        descriptions = []

        if actors:
            actor_list = [actor for actor_type in actors.values() for actor in actor_type]
            descriptions.append(f"Actors: {', '.join(actor_list[:3])}")  # Limit to first 3

        if attributes:
            attr_list = [attr for attr_type in attributes.values() for attr in attr_type]
            descriptions.append(f"Attributes: {', '.join(attr_list[:3])}")

        if principles:
            prin_list = [prin for prin_type in principles.values() for prin in prin_type]
            descriptions.append(f"Principles: {', '.join(prin_list[:2])}")

        if not descriptions:
            descriptions.append("General privacy scenario")

        return "; ".join(descriptions)


class InformationTypeClassifier:
    """Classifies information types for privacy analysis.

    Identifies different types of information (personal, medical, financial, etc.)
    based on content analysis and keyword matching.
    """

    def __init__(self) -> None:
        """Initialize the information type classifier with patterns."""
        self._type_patterns = self._compile_type_patterns()

    def classify_information(self, prompt_text: str) -> List[InformationType]:
        """Classify information types present in prompt text.

        Args:
            prompt_text: Text to analyze for information types

        Returns:
            List of detected information types
        """
        prompt_text = sanitize_file_content(prompt_text)
        text_lower = prompt_text.lower()

        detected_types = set()

        # Check each information type
        for info_type, config in PRIVACY_INFORMATION_TYPES.items():
            if self._matches_information_type(text_lower, config):
                detected_types.add(info_type)

        # Default to personal identifiers if no specific type found but privacy-relevant
        if not detected_types and self._contains_privacy_indicators(text_lower):
            detected_types.add(InformationType.PERSONAL_IDENTIFIERS)

        return list(detected_types)

    def get_information_sensitivity(self, info_types: List[InformationType]) -> str:
        """Get overall sensitivity level for information types.

        Args:
            info_types: List of information types

        Returns:
            Overall sensitivity level string
        """
        if not info_types:
            return "low"

        sensitivities = []
        for info_type in info_types:
            config = PRIVACY_INFORMATION_TYPES.get(info_type, {})
            sensitivity = config.get("sensitivity", "low")
            sensitivities.append(sensitivity)

        # Return highest sensitivity
        if "very_high" in sensitivities:
            return "very_high"
        elif "high" in sensitivities:
            return "high"
        elif "medium_high" in sensitivities:
            return "medium_high"
        elif "medium" in sensitivities:
            return "medium"
        else:
            return "low"

    def _compile_type_patterns(self) -> Dict[InformationType, List[re.Pattern]]:
        """Compile regex patterns for information type detection."""
        patterns = {}

        for info_type, config in PRIVACY_INFORMATION_TYPES.items():
            type_patterns = []

            # Add keyword patterns
            for keyword in config["keywords"]:
                type_patterns.append(re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE))

            # Add specific patterns if available
            if "patterns" in config:
                for pattern_str in config["patterns"]:
                    type_patterns.append(re.compile(pattern_str, re.IGNORECASE))

            patterns[info_type] = type_patterns

        return patterns

    def _matches_information_type(self, text: str, config: Dict[str, Any]) -> bool:
        """Check if text matches a specific information type."""
        keyword_matches = 0

        # Check keyword matches
        for keyword in config["keywords"]:
            if keyword.lower() in text:
                keyword_matches += 1

        # Check pattern matches
        pattern_matches = 0
        if "patterns" in config:
            for pattern_str in config["patterns"]:
                if re.search(pattern_str, text, re.IGNORECASE):
                    pattern_matches += 1

        # Require either multiple keyword matches or at least one pattern match
        return keyword_matches >= 2 or pattern_matches >= 1

    def _contains_privacy_indicators(self, text: str) -> bool:
        """Check if text contains general privacy indicators."""
        privacy_indicators = [
            "privacy",
            "personal",
            "private",
            "confidential",
            "sensitive",
            "data",
            "information",
            "share",
            "disclose",
            "protect",
        ]

        matches = sum(1 for indicator in privacy_indicators if indicator in text)
        return matches >= 2


class PrivacyNormsAnalyzer:
    """Analyzes applicable privacy norms and conflicts.

    Determines relevant privacy norms based on context and identifies
    potential conflicts between competing privacy expectations.
    """

    def __init__(self) -> None:
        """Initialize the privacy norms analyzer."""
        self._norm_patterns = self._build_norm_patterns()

    def determine_norms(
        self, contextual_factors: Dict[str, Any], info_types: List[InformationType], tier: PrivacyTier
    ) -> PrivacyNorms:
        """Determine applicable privacy norms for a scenario.

        Args:
            contextual_factors: Extracted contextual factors
            info_types: Detected information types
            tier: Privacy complexity tier

        Returns:
            PrivacyNorms analysis result
        """
        applicable_norms = self._identify_applicable_norms(contextual_factors, info_types)
        norm_conflicts = self._identify_norm_conflicts(applicable_norms, contextual_factors)
        resolution_strategy = self._suggest_resolution_strategy(norm_conflicts, tier)
        confidence_score = self._calculate_confidence(applicable_norms, norm_conflicts, contextual_factors)

        return PrivacyNorms(
            applicable_norms=applicable_norms,
            norm_conflicts=norm_conflicts,
            resolution_strategy=resolution_strategy,
            confidence_score=confidence_score,
        )

    def _build_norm_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build patterns for privacy norm identification."""
        return {
            "consent_required": {
                "contexts": ["healthcare", "research", "marketing"],
                "info_types": [InformationType.MEDICAL_INFORMATION, InformationType.PERSONAL_IDENTIFIERS],
                "keywords": ["consent", "permission", "authorization", "agreement"],
            },
            "purpose_limitation": {
                "contexts": ["all"],
                "info_types": ["all"],
                "keywords": ["purpose", "use", "processing", "collection"],
            },
            "data_minimization": {
                "contexts": ["all"],
                "info_types": ["all"],
                "keywords": ["necessary", "minimal", "required", "adequate"],
            },
            "transparency": {
                "contexts": ["all"],
                "info_types": ["all"],
                "keywords": ["inform", "notify", "disclosure", "transparent"],
            },
            "security": {
                "contexts": ["financial", "healthcare", "government"],
                "info_types": [InformationType.FINANCIAL_INFORMATION, InformationType.MEDICAL_INFORMATION],
                "keywords": ["protect", "secure", "safeguard", "encrypt"],
            },
            "right_to_access": {
                "contexts": ["personal", "social"],
                "info_types": [InformationType.PERSONAL_IDENTIFIERS, InformationType.BEHAVIORAL_DATA],
                "keywords": ["access", "view", "review", "obtain"],
            },
        }

    def _identify_applicable_norms(
        self, contextual_factors: Dict[str, Any], info_types: List[InformationType]
    ) -> List[str]:
        """Identify applicable privacy norms based on context and information types."""
        applicable = []

        # Extract contexts from contextual factors
        contexts = self._extract_contexts(contextual_factors)

        for norm_name, norm_config in self._norm_patterns.items():
            # Check if norm applies to contexts
            norm_contexts = norm_config["contexts"]
            if "all" in norm_contexts or any(context in contexts for context in norm_contexts):
                # Check if norm applies to information types
                norm_info_types = norm_config["info_types"]
                if "all" in norm_info_types or any(info_type in norm_info_types for info_type in info_types):
                    applicable.append(norm_name.replace("_", " ").title())

        # Add default norms
        if not applicable:
            applicable.extend(["Purpose Limitation", "Transparency"])

        return list(set(applicable))

    def _identify_norm_conflicts(self, applicable_norms: List[str], contextual_factors: Dict[str, Any]) -> List[str]:
        """Identify potential conflicts between privacy norms."""
        conflicts = []

        # Common conflict scenarios
        if "Consent Required" in applicable_norms and "Legal Obligation" in applicable_norms:
            conflicts.append("Consent vs Legal Obligation: Legal requirements may override consent")

        if "Transparency" in applicable_norms and "Security" in applicable_norms:
            conflicts.append("Transparency vs Security: Full disclosure may compromise security")

        if "Data Minimization" in applicable_norms and "Right To Access" in applicable_norms:
            conflicts.append("Minimization vs Access: Minimal data collection may limit access rights")

        # Check for multi-stakeholder conflicts
        actors = contextual_factors.get("actors", {})
        if len(actors) > 2:
            conflicts.append(
                "Multi-stakeholder expectations: Different actors may have conflicting privacy expectations"
            )

        return conflicts

    def _suggest_resolution_strategy(self, conflicts: List[str], tier: PrivacyTier) -> Optional[str]:
        """Suggest strategy for resolving norm conflicts based on tier complexity."""
        if not conflicts:
            return None

        if tier == PrivacyTier.BASIC:
            return "Apply most restrictive privacy norm"
        elif tier == PrivacyTier.CONTEXTUAL:
            return "Balance competing interests based on context"
        elif tier == PrivacyTier.NUANCED:
            return "Multi-factor analysis considering stakeholder impacts"
        else:  # ADVANCED
            return "Complex normative reasoning with expert consultation"

    def _calculate_confidence(
        self, applicable_norms: List[str], conflicts: List[str], contextual_factors: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for norm analysis."""
        base_confidence = 0.5

        # Increase confidence based on clear contextual factors
        actors = contextual_factors.get("actors", {})
        attributes = contextual_factors.get("attributes", {})
        principles = contextual_factors.get("transmission_principles", {})

        factor_score = (len(actors) + len(attributes) + len(principles)) / 10
        confidence = base_confidence + factor_score

        # Decrease confidence based on conflicts
        conflict_penalty = len(conflicts) * 0.1
        confidence = max(0.1, confidence - conflict_penalty)

        return min(1.0, confidence)

    def _extract_contexts(self, contextual_factors: Dict[str, Any]) -> List[str]:
        """Extract context types from contextual factors."""
        contexts = []

        # Extract from actors
        actors = contextual_factors.get("actors", {})
        for actor_list in actors.values():
            if "government" in actor_list:
                contexts.append("government")
            if any(term in actor_list for term in ["hospital", "clinic", "doctor"]):
                contexts.append("healthcare")
            if any(term in actor_list for term in ["bank", "financial"]):
                contexts.append("financial")
            if any(term in actor_list for term in ["researcher", "research"]):
                contexts.append("research")

        return list(set(contexts)) if contexts else ["general"]
