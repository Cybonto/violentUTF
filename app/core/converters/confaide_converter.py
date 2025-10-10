# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""ConfAIde Privacy Dataset Converter Implementation.

Implements specialized converter to transform ConfAIde-ICLR24 privacy evaluation dataset
into PyRIT SeedPromptDataset format with tier-based processing (4 tiers) and comprehensive
Contextual Integrity Theory metadata.

This module supports Issue #129 - ConfAIde Privacy Dataset Converter implementation following
Test-Driven Development methodology with comprehensive privacy validation.

Components:
- ConfAIdeConverter: Main converter class
- TierProcessor: Tier-based file processing (tier_1.txt through tier_4.txt)
- PrivacyAnalyzer: Contextual Integrity Theory analysis orchestrator

SECURITY: All content is for defensive security research only. Proper sanitization
and validation is applied to all inputs to prevent injection attacks.
"""
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.validation import sanitize_file_content
from app.schemas.confaide_datasets import (
    PrivacyFramework,
    PrivacyTier,
    ValidationCheck,
    ValidationResult,
)
from app.services.privacy_service import PrivacyService

logger = logging.getLogger(__name__)


# Simple data classes for PyRIT compatibility
class SeedPrompt:
    """Simple SeedPrompt class for PyRIT compatibility."""

    def __init__(self, value: str, data_type: str = "text", metadata: Optional[Dict[str, Any]] = None) -> None:
        """Initialize SeedPrompt instance.

        Args:
            value: The prompt text value
            data_type: Type of prompt data (default: "text")
            metadata: Associated metadata dictionary
        """
        self.value = value
        self.data_type = data_type
        self.metadata = metadata or {}


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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize SeedPromptDataset instance.

        Args:
            name: Dataset name
            version: Dataset version
            description: Dataset description
            author: Dataset author
            group: Dataset group
            source: Dataset source
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
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "group": self.group,
            "source": self.source,
            "prompts": [{"value": p.value, "data_type": p.data_type, "metadata": p.metadata} for p in self.prompts],
            "metadata": self.metadata,
        }


class TierProcessor:
    """Processes privacy tier files for ConfAIde dataset conversion.

    Handles discovery and processing of tier_1.txt through tier_4.txt files
    with progressive complexity analysis and validation.
    """

    def __init__(self) -> None:
        """Initialize the tier processor."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def discover_tier_files(self, dataset_path: str) -> Dict[int, str]:
        """Discover tier files in dataset directory.

        Args:
            dataset_path: Path to ConfAIde dataset directory

        Returns:
            Dictionary mapping tier numbers to file paths
        """
        discovered_files = {}
        dataset_dir = Path(dataset_path)

        for tier in range(1, 5):  # Tiers 1-4
            tier_file = dataset_dir / f"tier_{tier}.txt"
            if tier_file.exists():
                discovered_files[tier] = str(tier_file)
                self.logger.info("Discovered tier file: %s", tier_file)
            else:
                self.logger.warning("Tier file not found: %s", tier_file)

        return discovered_files

    def process_tier_file(self, tier_file_path: str, tier: int) -> List[SeedPrompt]:
        """Process single tier file and extract prompts.

        Args:
            tier_file_path: Path to tier file
            tier: Tier number (1-4)

        Returns:
            List of SeedPrompt objects with privacy metadata
        """
        try:
            with open(tier_file_path, "r", encoding="utf-8") as f:
                content = f.read()

            content = sanitize_file_content(content)

            # Extract individual prompts from file content
            prompts = self._extract_prompts_from_content(content, tier)

            self.logger.info("Processed %s prompts from tier %s", len(prompts), tier)
            return prompts

        except Exception as e:
            self.logger.error("Error processing tier file %s: %s", tier_file_path, e)
            return []

    def validate_tier_progression(self, tier_configs: Dict[int, Dict[str, Any]]) -> bool:
        """Validate that tier complexity progression is appropriate.

        Args:
            tier_configs: Configuration for each tier

        Returns:
            True if tier progression is valid
        """
        expected_progression = ["basic", "contextual", "nuanced", "advanced"]

        for tier_num in range(1, 5):
            if tier_num not in tier_configs:
                self.logger.warning("Missing configuration for tier %s", tier_num)
                return False

            expected_complexity = expected_progression[tier_num - 1]
            actual_complexity = tier_configs[tier_num].get("complexity")

            if actual_complexity != expected_complexity:
                self.logger.error(
                    "Tier %s complexity mismatch: expected %s, got %s",
                    tier_num,
                    expected_complexity,
                    actual_complexity,
                )
                return False

        return True

    def _extract_prompts_from_content(self, content: str, tier: int) -> List[SeedPrompt]:
        """Extract individual prompts from tier file content.

        Args:
            content: File content
            tier: Tier number

        Returns:
            List of SeedPrompt objects
        """
        # Split content into individual prompts
        # ConfAIde files typically have one prompt per line or paragraph
        lines = content.strip().split("\n")
        prompts = []

        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith("#"):  # Skip empty lines and comments
                prompt = SeedPrompt(
                    value=line, data_type="text", metadata={"privacy_tier": tier, "prompt_id": i, "source_line": i + 1}
                )
                prompts.append(prompt)

        return prompts


class PrivacyAnalyzer:
    """Orchestrates Contextual Integrity Theory analysis for privacy scenarios.

    Provides high-level interface for privacy analysis combining multiple
    analysis components and services.
    """

    def __init__(self) -> None:
        """Initialize the privacy analyzer with service dependencies."""
        self.privacy_service = PrivacyService()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def analyze_privacy_context(self, prompt_text: str, tier: int) -> Dict[str, Any]:
        """Analyze privacy context using Contextual Integrity Theory.

        Args:
            prompt_text: Text to analyze
            tier: Privacy tier number

        Returns:
            Dictionary containing privacy analysis results
        """
        try:
            privacy_tier = PrivacyTier(tier)
            analysis = self.privacy_service.analyze_privacy_context(prompt_text, privacy_tier)

            return {
                "contextual_factors": {
                    "actors": analysis.contextual_factors.actors,
                    "attributes": analysis.contextual_factors.attributes,
                    "transmission_principles": analysis.contextual_factors.transmission_principles,
                },
                "information_type": [info_type.value for info_type in analysis.information_type],
                "privacy_norms": {
                    "applicable_norms": analysis.privacy_norms.applicable_norms,
                    "norm_conflicts": analysis.privacy_norms.norm_conflicts,
                    "confidence_score": analysis.privacy_norms.confidence_score,
                },
                "complexity_indicators": analysis.complexity_indicators,
                "tier": tier,
            }

        except Exception as e:
            self.logger.error("Error in privacy context analysis: %s", e)
            return self._create_default_analysis(tier)

    def classify_privacy_sensitivity(self, prompt_text: str, tier: int, label: Optional[str] = None) -> Dict[str, Any]:
        """Classify privacy sensitivity level for prompt.

        Args:
            prompt_text: Text to analyze
            tier: Privacy tier number
            label: Optional label for validation

        Returns:
            Dictionary containing sensitivity classification results
        """
        try:
            privacy_tier = PrivacyTier(tier)
            sensitivity = self.privacy_service.classify_privacy_sensitivity(prompt_text, privacy_tier, label)

            return {
                "level": sensitivity.level.value,
                "categories": [category.value for category in sensitivity.categories],
                "expected_behavior": sensitivity.expected_behavior.value,
                "confidence": sensitivity.confidence,
                "tier_alignment": sensitivity.tier_alignment,
            }

        except Exception as e:
            self.logger.error("Error in privacy sensitivity classification: %s", e)
            return self._create_default_sensitivity(tier)

    def _create_default_analysis(self, tier: int) -> Dict[str, Any]:
        """Create default analysis on error."""
        return {
            "contextual_factors": {"actors": {}, "attributes": {}, "transmission_principles": {}},
            "information_type": ["personal_identifiers"],
            "privacy_norms": {
                "applicable_norms": ["Purpose Limitation"],
                "norm_conflicts": [],
                "confidence_score": 0.1,
            },
            "complexity_indicators": {"error": True},
            "tier": tier,
        }

    def _create_default_sensitivity(self, tier: int) -> Dict[str, Any]:
        """Create default sensitivity classification on error."""
        return {
            "level": "medium",
            "categories": ["personal_identifiers"],
            "expected_behavior": "clear_privacy_recognition",
            "confidence": 0.1,
            "tier_alignment": True,
        }


class ConfAIdeConverter:
    """Main converter class for transforming ConfAIde datasets to SeedPromptDataset format.

    Orchestrates tier-based file processing, privacy analysis, and dataset conversion
    with comprehensive validation and quality checks based on Contextual Integrity Theory.
    """

    def __init__(self, validation_enabled: bool = True) -> None:
        """Initialize the ConfAIde dataset converter.

        Args:
            validation_enabled: Whether to enable conversion validation
        """
        self.tier_processor = TierProcessor()
        self.privacy_analyzer = PrivacyAnalyzer()
        self.privacy_service = PrivacyService()
        self.validation_enabled = validation_enabled
        self.supported_framework = PrivacyFramework.CONTEXTUAL_INTEGRITY
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def convert(self, dataset_path: str) -> SeedPromptDataset:
        """Convert ConfAIde privacy dataset to SeedPromptDataset format.

        Args:
            dataset_path: Path to ConfAIde dataset directory

        Returns:
            SeedPromptDataset with privacy metadata
        """
        start_time = time.time()

        try:
            all_prompts = []
            tier_metadata = {}
            processing_summary = {"total_prompts": 0, "processed_tiers": 0}

            # Discover tier files
            tier_files = self.tier_processor.discover_tier_files(dataset_path)
            self.logger.info("Discovered %s tier files", len(tier_files))

            # Process each privacy tier sequentially
            for tier in range(1, 5):  # Tiers 1-4
                if tier not in tier_files:
                    self.logger.warning("Tier %s file not found, skipping", tier)
                    continue

                self.logger.info("Processing privacy tier %s", tier)

                try:
                    tier_prompts = self._process_privacy_tier(tier_files[tier], tier)
                    all_prompts.extend(tier_prompts)

                    # Generate tier metadata
                    tier_metadata[f"tier_{tier}"] = self._generate_tier_metadata(tier, len(tier_prompts))

                    processing_summary["total_prompts"] += len(tier_prompts)
                    processing_summary["processed_tiers"] += 1

                except Exception as e:
                    self.logger.error("Failed to process tier %s: %s", tier, e)
                    continue

            # Create dataset metadata
            dataset_metadata = self._create_dataset_metadata(processing_summary, tier_metadata)

            # Create and return SeedPromptDataset
            dataset = SeedPromptDataset(
                name="ConfAIde_Privacy_Evaluation",
                version="1.0",
                description="Privacy evaluation based on Contextual Integrity Theory across 4 complexity tiers",
                author="Mireshghallah et al. (ICLR 2024)",
                group="privacy_evaluation",
                source="ConfAIde-ICLR24",
                prompts=all_prompts,
                metadata=dataset_metadata,
            )

            processing_time = time.time() - start_time
            self.logger.info("Conversion completed in %.2f seconds", processing_time)

            return dataset

        except Exception as e:
            self.logger.error("Error during ConfAIde conversion: %s", e)
            raise

    def validate_privacy_conversion(self, dataset: SeedPromptDataset) -> ValidationResult:
        """Validate ConfAIde privacy conversion quality.

        Args:
            dataset: Converted dataset to validate

        Returns:
            ValidationResult with validation metrics
        """
        if not self.validation_enabled:
            return ValidationResult(overall_status="PASS", individual_checks=[], privacy_metrics={}, quality_score=1.0)

        validation_checks = []

        # Check tier progression
        tier_check = self._validate_tier_progression(dataset)
        validation_checks.append(tier_check)

        # Check Contextual Integrity Theory compliance
        ci_check = self._validate_contextual_integrity_compliance(dataset)
        validation_checks.append(ci_check)

        # Check privacy metadata completeness
        metadata_check = self._validate_privacy_metadata(dataset)
        validation_checks.append(metadata_check)

        # Check privacy scoring configuration
        scoring_check = self._validate_privacy_scoring_config(dataset)
        validation_checks.append(scoring_check)

        # Calculate overall status and quality score
        passed_checks = sum(1 for check in validation_checks if check.passed)
        overall_status = "PASS" if passed_checks == len(validation_checks) else "FAIL"
        quality_score = passed_checks / len(validation_checks) if validation_checks else 0.0

        return ValidationResult(
            overall_status=overall_status,
            individual_checks=validation_checks,
            privacy_metrics={
                "tier_coverage": self._analyze_tier_distribution(dataset),
                "ci_compliance_score": ci_check.score,
                "metadata_completeness": metadata_check.score,
                "scoring_config_quality": scoring_check.score,
            },
            quality_score=quality_score,
        )

    def _process_privacy_tier(self, tier_file_path: str, tier: int) -> List[SeedPrompt]:
        """Process single privacy tier file.

        Args:
            tier_file_path: Path to tier file
            tier: Tier number

        Returns:
            List of SeedPrompt objects with privacy metadata
        """
        # Get base prompts from tier processor
        base_prompts = self.tier_processor.process_tier_file(tier_file_path, tier)

        # Enhance each prompt with comprehensive privacy metadata
        enhanced_prompts = []
        for prompt in base_prompts:
            enhanced_prompt = self._create_privacy_prompt(prompt, tier)
            enhanced_prompts.append(enhanced_prompt)

        return enhanced_prompts

    def _create_privacy_prompt(self, base_prompt: SeedPrompt, tier: int) -> SeedPrompt:
        """Create privacy-focused SeedPrompt with comprehensive metadata.

        Args:
            base_prompt: Base prompt from tier processing
            tier: Privacy tier number

        Returns:
            Enhanced SeedPrompt with privacy metadata
        """
        # Analyze privacy context using Contextual Integrity Theory
        privacy_analysis = self.privacy_analyzer.analyze_privacy_context(base_prompt.value, tier)

        # Classify privacy sensitivity
        sensitivity = self.privacy_analyzer.classify_privacy_sensitivity(base_prompt.value, tier)

        # Get evaluation criteria for this tier
        evaluation_criteria = self.privacy_service.get_tier_evaluation_criteria(PrivacyTier(tier))

        # Get privacy scorer configuration
        scorer_config = self.privacy_service.get_privacy_scorer_config(PrivacyTier(tier))

        # Get tier configuration
        from app.services.privacy_service import PRIVACY_TIER_CONFIG

        tier_config = PRIVACY_TIER_CONFIG[PrivacyTier(tier)]

        # Create comprehensive metadata
        metadata = {
            **base_prompt.metadata,  # Preserve existing metadata
            "privacy_tier": tier,
            "tier_complexity": tier_config["complexity"],
            "tier_focus": tier_config["focus"],
            "privacy_sensitivity": sensitivity["level"],
            "privacy_categories": sensitivity["categories"],
            "contextual_factors": privacy_analysis["contextual_factors"],
            "information_type": privacy_analysis["information_type"],
            "privacy_norms": privacy_analysis["privacy_norms"],
            "expected_behavior": sensitivity["expected_behavior"],
            "evaluation_criteria": evaluation_criteria,
            "privacy_framework": self.supported_framework.value,
            "tier_alignment": sensitivity["tier_alignment"],
            "confidence": sensitivity["confidence"],
            "harm_categories": ["privacy_violation", "information_disclosure", "contextual_integrity_breach"],
            "privacy_scorer_config": {
                "scorer_type": scorer_config.scorer_type,
                "tier": scorer_config.tier.value,
                "privacy_framework": scorer_config.privacy_framework.value,
                "evaluation_mode": scorer_config.evaluation_mode,
                "evaluation_dimensions": scorer_config.evaluation_dimensions,
                "scoring_criteria": scorer_config.scoring_criteria,
                "complexity_weight": scorer_config.complexity_weight,
            },
            "conversion_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return SeedPrompt(value=base_prompt.value, data_type=base_prompt.data_type, metadata=metadata)

    def _generate_tier_metadata(self, tier: int, prompt_count: int) -> Dict[str, Any]:
        """Generate metadata for a specific tier.

        Args:
            tier: Tier number
            prompt_count: Number of prompts in tier

        Returns:
            Tier metadata dictionary
        """
        from app.services.privacy_service import PRIVACY_TIER_CONFIG

        tier_config = PRIVACY_TIER_CONFIG[PrivacyTier(tier)]

        return {
            "prompt_count": prompt_count,
            "complexity_level": tier_config["complexity"],
            "privacy_focus": tier_config["focus"],
            "evaluation_criteria": tier_config["evaluation_criteria"],
            "expected_behavior": tier_config["expected_behavior"].value,
            "description": tier_config["description"],
        }

    def _create_dataset_metadata(
        self, processing_summary: Dict[str, Any], tier_metadata: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create complete dataset metadata.

        Args:
            processing_summary: Summary of processing results
            tier_metadata: Metadata for each tier

        Returns:
            Complete dataset metadata dictionary
        """
        return {
            "privacy_framework": "contextual_integrity_theory",
            "tier_count": processing_summary["processed_tiers"],
            "total_prompts": processing_summary["total_prompts"],
            "tier_metadata": tier_metadata,
            "evaluation_type": "privacy_sensitivity",
            "privacy_categories": [
                "personal_identifiers",
                "medical_information",
                "financial_information",
                "behavioral_data",
                "communication_content",
                "biometric_data",
            ],
            "contextual_factors": ["actors", "attributes", "transmission_principles"],
            "conversion_strategy": "strategy_4_privacy_evaluation",
            "conversion_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _validate_tier_progression(self, dataset: SeedPromptDataset) -> ValidationCheck:
        """Validate tier progression in dataset."""
        try:
            tiers_present = set()
            for prompt in dataset.prompts:
                tier = prompt.metadata.get("privacy_tier")
                if tier:
                    tiers_present.add(tier)

            expected_tiers = {1, 2, 3, 4}
            has_all_tiers = tiers_present == expected_tiers

            return ValidationCheck(
                check_name="Tier Progression",
                passed=has_all_tiers,
                score=1.0 if has_all_tiers else len(tiers_present) / 4,
                details=f"Present tiers: {sorted(tiers_present)}, Expected: {sorted(expected_tiers)}",
            )
        except Exception as e:
            return ValidationCheck(check_name="Tier Progression", passed=False, score=0.0, details=f"Error: {e}")

    def _validate_contextual_integrity_compliance(self, dataset: SeedPromptDataset) -> ValidationCheck:
        """Validate Contextual Integrity Theory compliance."""
        try:
            compliant_prompts = 0
            total_prompts = len(dataset.prompts)

            for prompt in dataset.prompts:
                metadata = prompt.metadata
                contextual_factors = metadata.get("contextual_factors", {})

                # Check for CI Theory components
                has_actors = bool(contextual_factors.get("actors"))
                has_attributes = bool(contextual_factors.get("attributes"))
                has_principles = bool(contextual_factors.get("transmission_principles"))

                if has_actors or has_attributes or has_principles:
                    compliant_prompts += 1

            compliance_rate = compliant_prompts / total_prompts if total_prompts > 0 else 0.0

            return ValidationCheck(
                check_name="Contextual Integrity Compliance",
                passed=compliance_rate >= 0.8,
                score=compliance_rate,
                details=f"{compliant_prompts}/{total_prompts} prompts have CI factors",
            )
        except Exception as e:
            return ValidationCheck(
                check_name="Contextual Integrity Compliance", passed=False, score=0.0, details=f"Error: {e}"
            )

    def _validate_privacy_metadata(self, dataset: SeedPromptDataset) -> ValidationCheck:
        """Validate privacy metadata completeness."""
        try:
            required_fields = [
                "privacy_tier",
                "privacy_sensitivity",
                "privacy_categories",
                "contextual_factors",
                "information_type",
                "expected_behavior",
                "privacy_framework",
                "privacy_scorer_config",
            ]

            complete_prompts = 0
            total_prompts = len(dataset.prompts)

            for prompt in dataset.prompts:
                metadata = prompt.metadata
                has_all_fields = all(field in metadata for field in required_fields)
                if has_all_fields:
                    complete_prompts += 1

            completeness_rate = complete_prompts / total_prompts if total_prompts > 0 else 0.0

            return ValidationCheck(
                check_name="Privacy Metadata Completeness",
                passed=completeness_rate >= 0.95,
                score=completeness_rate,
                details=f"{complete_prompts}/{total_prompts} prompts have complete metadata",
            )
        except Exception as e:
            return ValidationCheck(
                check_name="Privacy Metadata Completeness", passed=False, score=0.0, details=f"Error: {e}"
            )

    def _validate_privacy_scoring_config(self, dataset: SeedPromptDataset) -> ValidationCheck:
        """Validate privacy scoring configuration."""
        try:
            valid_configs = 0
            total_prompts = len(dataset.prompts)

            for prompt in dataset.prompts:
                scorer_config = prompt.metadata.get("privacy_scorer_config", {})

                # Check required fields
                required_fields = ["scorer_type", "evaluation_dimensions", "scoring_criteria"]
                has_required_fields = all(field in scorer_config for field in required_fields)

                if has_required_fields:
                    valid_configs += 1

            validity_rate = valid_configs / total_prompts if total_prompts > 0 else 0.0

            return ValidationCheck(
                check_name="Privacy Scoring Configuration",
                passed=validity_rate >= 0.9,
                score=validity_rate,
                details=f"{valid_configs}/{total_prompts} prompts have valid scorer config",
            )
        except Exception as e:
            return ValidationCheck(
                check_name="Privacy Scoring Configuration", passed=False, score=0.0, details=f"Error: {e}"
            )

    def _analyze_tier_distribution(self, dataset: SeedPromptDataset) -> Dict[str, int]:
        """Analyze distribution of prompts across tiers."""
        tier_counts = {"1": 0, "2": 0, "3": 0, "4": 0}

        for prompt in dataset.prompts:
            tier = prompt.metadata.get("privacy_tier")
            tier_str = str(tier) if tier is not None else ""
            if tier_str in tier_counts:
                tier_counts[tier_str] += 1

        return tier_counts
