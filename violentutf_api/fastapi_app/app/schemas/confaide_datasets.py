# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Pydantic schemas for ConfAIde privacy dataset converter functionality.

Supports Issue #129 - ConfAIde Privacy Dataset Converter implementation with
comprehensive privacy analysis based on Contextual Integrity Theory.

SECURITY: Enhanced with comprehensive input validation to prevent injection attacks.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.validation import (
    SecurityLimits,
    sanitize_string,
)
from pydantic import BaseModel, Field, field_validator

# --- Privacy Framework Enums ---


class PrivacyFramework(str, Enum):
    """Privacy analysis frameworks supported."""

    CONTEXTUAL_INTEGRITY = "contextual_integrity_theory"
    PRIVACY_BY_DESIGN = "privacy_by_design"
    GDPR_COMPLIANCE = "gdpr_compliance"
    CCPA_COMPLIANCE = "ccpa_compliance"


class PrivacyTier(int, Enum):
    """Privacy complexity tiers in ConfAIde dataset."""

    BASIC = 1  # Basic privacy sensitivity scenarios
    CONTEXTUAL = 2  # Context-dependent privacy scenarios
    NUANCED = 3  # Complex privacy scenarios
    ADVANCED = 4  # Interactive privacy reasoning


class PrivacySensitivityLevel(str, Enum):
    """Privacy sensitivity classification levels."""

    LOW = "low"
    MEDIUM = "medium"
    MEDIUM_HIGH = "medium_high"
    HIGH = "high"
    VERY_HIGH = "very_high"


class InformationType(str, Enum):
    """Types of information for privacy classification."""

    PERSONAL_IDENTIFIERS = "personal_identifiers"
    MEDICAL_INFORMATION = "medical_information"
    FINANCIAL_INFORMATION = "financial_information"
    BEHAVIORAL_DATA = "behavioral_data"
    COMMUNICATION_CONTENT = "communication_content"
    BIOMETRIC_DATA = "biometric_data"
    LOCATION_DATA = "location_data"
    SENSITIVE_PERSONAL = "sensitive_personal"


class ContextualActor(str, Enum):
    """Actors in Contextual Integrity Theory."""

    DATA_SUBJECT = "data_subject"  # Individual whose data is involved
    DATA_HOLDER = "data_holder"  # Entity that holds/controls data
    DATA_RECEIVER = "data_receiver"  # Entity that receives data
    THIRD_PARTY = "third_party"  # External entities
    GOVERNMENT = "government"  # Government entities
    RESEARCHER = "researcher"  # Research entities


class TransmissionPrinciple(str, Enum):
    """Transmission principles in Contextual Integrity Theory."""

    PURPOSE_LIMITATION = "purpose_limitation"
    DATA_MINIMIZATION = "data_minimization"
    CONSENT_BASED = "consent_based"
    LEGAL_OBLIGATION = "legal_obligation"
    LEGITIMATE_INTEREST = "legitimate_interest"
    VITAL_INTEREST = "vital_interest"


class ExpectedBehavior(str, Enum):
    """Expected AI behavior for privacy scenarios."""

    CLEAR_PRIVACY_RECOGNITION = "clear_privacy_recognition"
    CONTEXT_AWARE_DECISIONS = "context_aware_privacy_decisions"
    SOPHISTICATED_ANALYSIS = "sophisticated_privacy_analysis"
    EXPERT_LEVEL_JUDGMENT = "expert_level_privacy_judgment"
    PRIVACY_RISK_ASSESSMENT = "privacy_risk_assessment"
    CONTEXTUAL_APPROPRIATENESS = "contextual_appropriateness"


# --- Core Data Models ---


class ContextualFactors(BaseModel):
    """Contextual factors from Contextual Integrity Theory."""

    actors: Dict[str, List[str]] = Field(..., description="Actors involved (subjects, holders, receivers)")
    attributes: Dict[str, List[str]] = Field(..., description="Information attributes and characteristics")
    transmission_principles: Dict[str, List[str]] = Field(..., description="Transmission principles and norms")
    context_description: str = Field(..., description="Overall context description")

    @field_validator("context_description")
    @classmethod
    def validate_context_description(cls: type, v: str) -> str:
        """Validate context description."""
        v = sanitize_string(v)
        if len(v) > SecurityLimits.MAX_STRING_LENGTH:
            raise ValueError("Context description too long")
        return v


class PrivacyNorms(BaseModel):
    """Privacy norms analysis for Contextual Integrity."""

    applicable_norms: List[str] = Field(..., description="Applicable privacy norms")
    norm_conflicts: List[str] = Field(default=[], description="Conflicting privacy norms")
    resolution_strategy: Optional[str] = Field(None, description="Strategy for resolving conflicts")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in norm analysis")

    @field_validator("applicable_norms", "norm_conflicts")
    @classmethod
    def validate_norms_list(cls: type, v: List[str]) -> List[str]:
        """Validate privacy norms lists."""
        validated = []
        for norm in v:
            if not isinstance(norm, str):
                raise ValueError("Privacy norm must be a string")
            norm = sanitize_string(norm)
            if len(norm) > 200:
                raise ValueError("Privacy norm description too long")
            validated.append(norm)
        return validated


class PrivacyAnalysis(BaseModel):
    """Complete privacy analysis result based on Contextual Integrity Theory."""

    contextual_factors: ContextualFactors = Field(..., description="Contextual factors analysis")
    information_type: List[InformationType] = Field(..., description="Types of information involved")
    privacy_norms: PrivacyNorms = Field(..., description="Applicable privacy norms")
    complexity_indicators: Dict[str, Any] = Field(..., description="Tier-based complexity indicators")
    tier: PrivacyTier = Field(..., description="Privacy complexity tier")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")

    @field_validator("complexity_indicators")
    @classmethod
    def validate_complexity_indicators(cls: type, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate complexity indicators."""
        if not isinstance(v, dict):
            raise ValueError("Complexity indicators must be a dictionary")
        # Validate keys and values are reasonable
        for key in v.keys():
            if not isinstance(key, str) or len(key) > 100:
                raise ValueError("Invalid complexity indicator key")
        return v


class PrivacySensitivity(BaseModel):
    """Privacy sensitivity classification result."""

    level: PrivacySensitivityLevel = Field(..., description="Privacy sensitivity level")
    categories: List[InformationType] = Field(..., description="Information categories detected")
    expected_behavior: ExpectedBehavior = Field(..., description="Expected AI behavior")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    tier_alignment: bool = Field(..., description="Whether classification aligns with tier expectations")
    reasoning: Optional[str] = Field(None, description="Reasoning for classification")

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls: type, v: Optional[str]) -> Optional[str]:
        """Validate reasoning text."""
        if v is not None:
            v = sanitize_string(v)
            if len(v) > SecurityLimits.MAX_STRING_LENGTH:
                raise ValueError("Reasoning text too long")
        return v


class TierConfiguration(BaseModel):
    """Configuration for a specific privacy tier."""

    tier: PrivacyTier = Field(..., description="Privacy tier number")
    complexity: str = Field(..., description="Complexity level description")
    focus: str = Field(..., description="Primary focus area")
    evaluation_criteria: str = Field(..., description="Evaluation criteria")
    expected_behavior: ExpectedBehavior = Field(..., description="Expected AI behavior")
    description: str = Field(..., description="Tier description")

    @field_validator("complexity", "focus", "evaluation_criteria", "description")
    @classmethod
    def validate_text_fields(cls: type, v: str) -> str:
        """Validate text fields."""
        v = sanitize_string(v)
        if len(v) > SecurityLimits.MAX_STRING_LENGTH:
            raise ValueError("Text field too long")
        return v


class PrivacyScorerConfig(BaseModel):
    """Configuration for privacy-specific scorers."""

    scorer_type: str = Field(..., description="Type of privacy scorer")
    tier: PrivacyTier = Field(..., description="Privacy tier")
    privacy_framework: PrivacyFramework = Field(..., description="Privacy framework used")
    evaluation_mode: str = Field(..., description="Evaluation mode")
    evaluation_dimensions: List[str] = Field(..., description="Dimensions to evaluate")
    scoring_criteria: str = Field(..., description="Scoring criteria")
    complexity_weight: float = Field(..., ge=0.0, le=1.0, description="Complexity weighting factor")

    @field_validator("evaluation_dimensions")
    @classmethod
    def validate_evaluation_dimensions(cls: type, v: List[str]) -> List[str]:
        """Validate evaluation dimensions."""
        if not v:
            raise ValueError("At least one evaluation dimension required")
        validated = []
        for dimension in v:
            if not isinstance(dimension, str):
                raise ValueError("Evaluation dimension must be a string")
            dimension = sanitize_string(dimension)
            if len(dimension) > 200:
                raise ValueError("Evaluation dimension too long")
            validated.append(dimension)
        return validated


# --- Conversion Result Models ---


class ConfAIdePromptMetadata(BaseModel):
    """Metadata for individual ConfAIde prompt."""

    privacy_tier: PrivacyTier = Field(..., description="Privacy complexity tier")
    tier_complexity: str = Field(..., description="Tier complexity level")
    tier_focus: str = Field(..., description="Tier focus area")
    prompt_id: int = Field(..., description="Prompt identifier within tier")
    privacy_sensitivity: PrivacySensitivityLevel = Field(..., description="Privacy sensitivity level")
    privacy_categories: List[InformationType] = Field(..., description="Privacy categories")
    contextual_factors: ContextualFactors = Field(..., description="Contextual factors")
    information_type: List[InformationType] = Field(..., description="Information types")
    privacy_norms: PrivacyNorms = Field(..., description="Privacy norms analysis")
    expected_behavior: ExpectedBehavior = Field(..., description="Expected AI behavior")
    evaluation_criteria: List[str] = Field(..., description="Evaluation criteria")
    privacy_framework: PrivacyFramework = Field(..., description="Privacy framework")
    tier_alignment: bool = Field(..., description="Tier alignment status")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence")
    harm_categories: List[str] = Field(default=[], description="Harm categories")
    privacy_scorer_config: PrivacyScorerConfig = Field(..., description="Privacy scorer configuration")

    @field_validator("evaluation_criteria")
    @classmethod
    def validate_evaluation_criteria(cls: type, v: List[str]) -> List[str]:
        """Validate evaluation criteria."""
        validated = []
        for criterion in v:
            if not isinstance(criterion, str):
                raise ValueError("Evaluation criterion must be a string")
            criterion = sanitize_string(criterion)
            if len(criterion) > 500:
                raise ValueError("Evaluation criterion too long")
            validated.append(criterion)
        return validated


class ConfAIdeDatasetMetadata(BaseModel):
    """Metadata for complete ConfAIde dataset conversion."""

    privacy_framework: PrivacyFramework = Field(..., description="Privacy framework used")
    tier_count: int = Field(..., ge=1, le=4, description="Number of tiers processed")
    total_prompts: int = Field(..., ge=0, description="Total number of prompts")
    tier_metadata: Dict[str, Dict[str, Any]] = Field(..., description="Per-tier metadata")
    evaluation_type: str = Field(..., description="Type of evaluation")
    privacy_categories: List[InformationType] = Field(..., description="Privacy categories covered")
    contextual_factors: List[str] = Field(..., description="Contextual factors types")
    conversion_strategy: str = Field(..., description="Conversion strategy used")
    conversion_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Conversion timestamp")

    @field_validator("tier_metadata")
    @classmethod
    def validate_tier_metadata(cls: type, v: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Validate tier metadata structure."""
        if not isinstance(v, dict):
            raise ValueError("Tier metadata must be a dictionary")

        for tier_key, tier_data in v.items():
            if not tier_key.startswith("tier_"):
                raise ValueError(f"Invalid tier key: {tier_key}")
            if not isinstance(tier_data, dict):
                raise ValueError(f"Tier data must be a dictionary for {tier_key}")

        return v


class ConfAIdeConversionResult(BaseModel):
    """Result of ConfAIde dataset conversion."""

    success: bool = Field(..., description="Whether conversion succeeded")
    dataset_name: str = Field(..., description="Generated dataset name")
    dataset_version: str = Field(..., description="Dataset version")
    dataset_description: str = Field(..., description="Dataset description")
    dataset_author: str = Field(..., description="Dataset author")
    dataset_group: str = Field(..., description="Dataset group")
    dataset_source: str = Field(..., description="Dataset source")
    total_prompts: int = Field(..., ge=0, description="Total prompts converted")
    processed_tiers: int = Field(..., ge=0, le=4, description="Number of tiers processed")
    metadata: ConfAIdeDatasetMetadata = Field(..., description="Dataset metadata")
    conversion_time_seconds: float = Field(..., ge=0.0, description="Conversion processing time")
    error_message: Optional[str] = Field(None, description="Error message if conversion failed")

    @field_validator("dataset_name", "dataset_version", "dataset_description", "dataset_author")
    @classmethod
    def validate_dataset_fields(cls: type, v: str) -> str:
        """Validate dataset text fields."""
        v = sanitize_string(v)
        if len(v) > SecurityLimits.MAX_NAME_LENGTH:
            raise ValueError("Dataset field too long")
        return v


# --- Validation Models ---


class ValidationCheck(BaseModel):
    """Individual validation check result."""

    check_name: str = Field(..., description="Name of validation check")
    passed: bool = Field(..., description="Whether check passed")
    score: float = Field(..., ge=0.0, le=1.0, description="Check score")
    details: Optional[str] = Field(None, description="Additional check details")

    @field_validator("check_name")
    @classmethod
    def validate_check_name(cls: type, v: str) -> str:
        """Validate check name."""
        v = sanitize_string(v)
        if len(v) > 200:
            raise ValueError("Check name too long")
        return v


class ValidationResult(BaseModel):
    """Complete validation result for ConfAIde conversion."""

    overall_status: str = Field(..., description="Overall validation status (PASS/FAIL)")
    individual_checks: List[ValidationCheck] = Field(..., description="Individual validation checks")
    privacy_metrics: Dict[str, Any] = Field(..., description="Privacy-specific validation metrics")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow, description="Validation timestamp")

    @field_validator("overall_status")
    @classmethod
    def validate_status(cls: type, v: str) -> str:
        """Validate overall status."""
        v = sanitize_string(v)
        if v not in ["PASS", "FAIL"]:
            raise ValueError("Status must be PASS or FAIL")
        return v


# --- Request/Response Models for API ---


class ConfAIdeConversionRequest(BaseModel):
    """Request to convert ConfAIde privacy dataset."""

    dataset_path: str = Field(..., description="Path to ConfAIde dataset directory")
    include_validation: bool = Field(default=True, description="Include validation in conversion")
    privacy_framework: PrivacyFramework = Field(
        default=PrivacyFramework.CONTEXTUAL_INTEGRITY, description="Privacy framework to use"
    )
    tier_filter: Optional[List[PrivacyTier]] = Field(None, description="Filter to specific tiers (default: all tiers)")

    @field_validator("dataset_path")
    @classmethod
    def validate_dataset_path(cls: type, v: str) -> str:
        """Validate dataset path."""
        v = sanitize_string(v)
        if len(v) > SecurityLimits.MAX_PATH_LENGTH:
            raise ValueError("Dataset path too long")
        return v


class ConfAIdeConversionResponse(BaseModel):
    """Response for ConfAIde dataset conversion."""

    success: bool = Field(..., description="Whether conversion succeeded")
    result: Optional[ConfAIdeConversionResult] = Field(None, description="Conversion result")
    validation: Optional[ValidationResult] = Field(None, description="Validation result")
    message: str = Field(..., description="Response message")

    @field_validator("message")
    @classmethod
    def validate_message(cls: type, v: str) -> str:
        """Validate response message."""
        v = sanitize_string(v)
        if len(v) > SecurityLimits.MAX_STRING_LENGTH:
            raise ValueError("Message too long")
        return v
