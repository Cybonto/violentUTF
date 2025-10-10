# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
NIST RMF-Compliant Risk Assessment Engine

This module implements a comprehensive risk assessment engine based on the NIST Risk Management Framework (RMF).
The engine follows the 6-step NIST RMF process and calculates risk scores on a 1-25 scale with high accuracy
and performance requirements.

Key Components:
- NISTRMFRiskEngine: Main orchestrator for complete risk assessments
- LikelihoodCalculator: Threat likelihood assessment (1-5 scale)
- ImpactCalculator: Business impact assessment (1-5 scale)
- SystemCategorizer: NIST RMF Step 1 information system categorization
- SecurityControlSelector: NIST RMF Step 2 security control selection

Performance Requirements:
- Risk calculation: ≤ 500ms per asset
- Accuracy: ≥ 95% for risk level classification
- Scale: Support 50+ concurrent assessments
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from app.models.risk_assessment import DatabaseAsset

# Configure logging
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level categories based on NIST RMF scoring (1-25 scale)"""

    LOW = "low"  # 1-5
    MEDIUM = "medium"  # 6-10
    HIGH = "high"  # 11-15
    VERY_HIGH = "very_high"  # 16-20
    CRITICAL = "critical"  # 21-25


class ImpactLevel(Enum):
    """NIST RMF impact levels for system categorization"""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ControlFamily(Enum):
    """NIST SP 800-53 security control families"""

    ACCESS_CONTROL = "AC"
    AWARENESS_TRAINING = "AT"
    AUDIT_ACCOUNTABILITY = "AU"
    SECURITY_ASSESSMENT = "CA"
    CONFIGURATION_MANAGEMENT = "CM"
    CONTINGENCY_PLANNING = "CP"
    IDENTIFICATION_AUTHENTICATION = "IA"
    INCIDENT_RESPONSE = "IR"
    MAINTENANCE = "MA"
    MEDIA_PROTECTION = "MP"
    PHYSICAL_ENVIRONMENTAL = "PE"
    PLANNING = "PL"
    PERSONNEL_SECURITY = "PS"
    RISK_ASSESSMENT = "RA"
    SYSTEM_SERVICES_ACQUISITION = "SA"
    SYSTEM_COMMUNICATIONS_PROTECTION = "SC"
    SYSTEM_INFORMATION_INTEGRITY = "SI"


@dataclass
class RiskFactors:
    """Risk assessment factors for NIST RMF calculation"""

    likelihood: float  # 1-5 scale: Threat likelihood
    impact: float  # 1-5 scale: Business impact
    exposure: float  # 0.1-1.0 scale: Exposure factor based on controls
    confidence: float  # 0.0-1.0 scale: Confidence in assessment


@dataclass
class SystemCategorization:
    """NIST RMF Step 1: System categorization results"""

    confidentiality_impact: ImpactLevel
    integrity_impact: ImpactLevel
    availability_impact: ImpactLevel
    overall_categorization: ImpactLevel
    data_types: List[str]
    rationale: str


@dataclass
class SecurityControl:
    """NIST SP 800-53 security control definition"""

    id: str  # Control identifier (e.g., AC-2)
    name: str  # Control name
    family: ControlFamily  # Control family
    priority: str  # P1, P2, P3
    baseline: str  # Low, Moderate, High
    description: str  # Control description
    implementation_guidance: str


@dataclass
class ControlResult:
    """Individual security control assessment result"""

    control_id: str
    control_name: str
    implementation_status: str  # IMPLEMENTED, PARTIALLY_IMPLEMENTED, NOT_IMPLEMENTED
    effectiveness_score: float  # 0.0-1.0 scale
    evidence: List[str]
    gaps: List[str]
    recommendations: List[str]


@dataclass
class ControlAssessment:
    """NIST RMF Step 4: Security control assessment results"""

    asset_id: str
    assessment_date: datetime
    control_results: List[ControlResult]
    overall_effectiveness: float  # 0.0-1.0 scale
    total_controls_assessed: int
    implemented_controls: int
    gaps_identified: int


@dataclass
class MonitoringPlan:
    """NIST RMF Step 6: Continuous monitoring plan"""

    continuous_monitoring_frequency: str
    control_assessment_frequency: str
    vulnerability_scanning_frequency: str
    automated_monitoring_tools: List[str]
    manual_review_procedures: List[str]


@dataclass
class RiskAssessmentResult:
    """Complete NIST RMF risk assessment result"""

    asset_id: str
    risk_score: float  # 1-25 scale
    risk_level: RiskLevel
    risk_factors: RiskFactors
    categorization: SystemCategorization
    control_assessment: ControlAssessment
    monitoring_plan: MonitoringPlan
    assessment_timestamp: datetime
    next_assessment_due: datetime
    assessment_duration_ms: Optional[int] = None


class LikelihoodCalculator:
    """
    Calculates threat likelihood component of risk assessment (1-5 scale)

    Considers:
    - Vulnerability exposure and exploitability
    - Threat intelligence and attack patterns
    - Attack surface analysis
    - Security control effectiveness
    """

    def __init__(self, vulnerability_service: Any = None, threat_intelligence: Any = None) -> None:  # noqa: ANN401
        """Initialize likelihood calculator with optional services."""
        self.vulnerability_service = vulnerability_service
        self.threat_intelligence = threat_intelligence

    async def calculate_likelihood(self, asset: DatabaseAsset, control_assessment: ControlAssessment) -> float:
        """
        Calculate threat likelihood score (1-5 scale)

        Args:
            asset: Database asset to assess
            control_assessment: Security control assessment results

        Returns:
            Likelihood score between 1.0 and 5.0
        """
        try:
            # Get vulnerability data
            vulnerability_score = await self._calculate_vulnerability_score(asset)

            # Get threat intelligence
            threat_score = await self._calculate_threat_score(asset)

            # Assess attack surface
            exposure_score = await self._calculate_exposure_score(asset)

            # Calculate base likelihood
            base_likelihood = (vulnerability_score + threat_score + exposure_score) / 3.0

            # Apply control effectiveness reduction
            control_reduction = self._calculate_control_reduction(control_assessment)
            adjusted_likelihood = base_likelihood * control_reduction

            # Ensure result is within valid range
            return max(1.0, min(5.0, round(adjusted_likelihood, 1)))

        except Exception as e:
            logger.error("Error calculating likelihood for asset %s: %s", asset.id, e)
            return 3.0  # Default to medium likelihood on error

    async def _calculate_vulnerability_score(self, asset: DatabaseAsset) -> float:
        """Calculate vulnerability-based likelihood component"""
        if not self.vulnerability_service:
            return 2.5  # Default moderate score if no vulnerability service

        try:
            # Get vulnerabilities for the asset
            vulnerabilities = await self.vulnerability_service.get_asset_vulnerabilities(asset)

            if not vulnerabilities:
                return 1.5  # Low likelihood if no vulnerabilities

            # Weight vulnerabilities by severity and exploitability
            weighted_score = 0.0
            total_weight = 0.0

            for vuln in vulnerabilities:
                # Base weight from CVSS score (normalized to 0-1)
                base_weight = vuln.cvss_score / 10.0

                # Increase weight for exploitable vulnerabilities
                if getattr(vuln, "exploit_available", False):
                    base_weight *= 1.5

                # Increase weight for recent vulnerabilities
                if hasattr(vuln, "published_date"):
                    days_since_published = (datetime.utcnow() - vuln.published_date).days
                    if days_since_published <= 30:  # Recent vulnerabilities
                        base_weight *= 1.3
                    elif days_since_published <= 90:
                        base_weight *= 1.1

                weighted_score += (vuln.cvss_score / 10.0) * 5.0 * base_weight
                total_weight += base_weight

            if total_weight == 0:
                return 1.5

            # Normalize to 1-5 scale
            avg_score = weighted_score / total_weight
            return max(1.0, min(5.0, avg_score))

        except Exception as e:
            logger.error("Error calculating vulnerability score: %s", e)
            return 2.5

    async def _calculate_threat_score(self, asset: DatabaseAsset) -> float:
        """Calculate threat intelligence-based likelihood component"""
        if not self.threat_intelligence:
            return 2.5  # Default moderate score if no threat intelligence

        try:
            # Get threat landscape for asset type and industry
            threat_data = await self.threat_intelligence.get_threat_landscape(asset)

            # Calculate weighted threat score
            db_threat_score = self._score_database_threats(threat_data.get("database_threats", []))
            industry_threat_score = self._score_industry_threats(threat_data.get("industry_threats", []))
            geo_threat_score = self._score_geographic_threats(threat_data.get("geographic_threats", []))

            # Weight the different threat categories
            weighted_score = (
                db_threat_score * 0.5  # Database-specific threats most important
                + industry_threat_score * 0.3  # Industry threats significant
                + geo_threat_score * 0.2  # Geographic threats least weight
            )

            return max(1.0, min(5.0, weighted_score))

        except Exception as e:
            logger.error("Error calculating threat score: %s", e)
            return 2.5

    async def _calculate_exposure_score(self, asset: DatabaseAsset) -> float:
        """Calculate attack surface exposure score"""
        try:
            await self._assess_attack_surface(asset)

            exposure_factors = []

            # Network exposure
            if asset.location and "public" in asset.location.lower():
                exposure_factors.append(4.5)  # High exposure for public-facing
            elif asset.location and "dmz" in asset.location.lower():
                exposure_factors.append(3.5)  # Medium-high for DMZ
            else:
                exposure_factors.append(2.0)  # Lower for internal

            # Access controls
            if asset.access_restricted:
                exposure_factors.append(2.0)  # Lower exposure with access controls
            else:
                exposure_factors.append(4.0)  # Higher exposure without controls

            # Encryption status
            if asset.encryption_enabled:
                exposure_factors.append(1.5)  # Lower exposure with encryption
            else:
                exposure_factors.append(3.5)  # Higher exposure without encryption

            # Asset criticality (higher criticality = higher attack likelihood)
            criticality_map = {"low": 1.5, "medium": 2.5, "high": 3.5, "critical": 4.5}
            exposure_factors.append(criticality_map.get(asset.criticality_level, 2.5))

            # Calculate average exposure
            avg_exposure = sum(exposure_factors) / len(exposure_factors)
            return max(1.0, min(5.0, avg_exposure))

        except Exception as e:
            logger.error("Error calculating exposure score: %s", e)
            return 3.0

    async def _assess_attack_surface(self, asset: DatabaseAsset) -> Dict[str, Any]:
        """Assess attack surface characteristics"""
        surface = {
            "network_exposure": "internal",
            "authentication_methods": ["password"],
            "encryption_enabled": asset.encryption_enabled,
            "access_restricted": asset.access_restricted,
        }

        # Determine network exposure based on location
        if asset.location:
            if any(term in asset.location.lower() for term in ["public", "internet", "external"]):
                surface["network_exposure"] = "public"
            elif "dmz" in asset.location.lower():
                surface["network_exposure"] = "dmz"

        return surface

    def _calculate_control_reduction(self, control_assessment: ControlAssessment) -> float:
        """Calculate likelihood reduction based on control effectiveness"""
        if not control_assessment or control_assessment.overall_effectiveness == 0:
            return 1.0  # No reduction if no controls

        # Maximum 80% reduction from highly effective controls
        max_reduction = 0.8
        reduction_factor = 1.0 - (control_assessment.overall_effectiveness * max_reduction)

        return max(0.2, reduction_factor)  # Minimum 20% of original likelihood

    def _score_database_threats(self, db_threats: List[Dict]) -> float:
        """Score database-specific threats"""
        if not db_threats:
            return 2.0

        total_score = sum(threat.get("likelihood", 3.0) for threat in db_threats)
        return min(5.0, total_score / len(db_threats))

    def _score_industry_threats(self, industry_threats: List[Dict]) -> float:
        """Score industry-specific threats"""
        if not industry_threats:
            return 2.0

        total_score = sum(threat.get("likelihood", 3.0) for threat in industry_threats)
        return min(5.0, total_score / len(industry_threats))

    def _score_geographic_threats(self, geo_threats: List[Dict]) -> float:
        """Score geographic/regional threats"""
        if not geo_threats:
            return 2.0

        total_score = sum(threat.get("likelihood", 3.0) for threat in geo_threats)
        return min(5.0, total_score / len(geo_threats))


class ImpactCalculator:
    """
    Calculates business impact component of risk assessment (1-5 scale)

    Considers:
    - Asset criticality and business value
    - Data sensitivity and classification
    - Operational disruption potential
    - Compliance and regulatory impact
    - Financial impact assessment
    """

    def __init__(self) -> None:
        """Initialize impact calculator."""
        # No specific initialization required
        pass  # pylint: disable=unnecessary-pass

    async def calculate_impact(self, asset: DatabaseAsset) -> float:
        """
        Calculate business impact score (1-5 scale)

        Args:
            asset: Database asset to assess

        Returns:
            Impact score between 1.0 and 5.0
        """
        try:
            # Calculate individual impact components
            criticality_impact = self.get_criticality_impact(asset.criticality_level)
            sensitivity_impact = self.get_sensitivity_impact(asset.security_classification)
            operational_impact = await self.calculate_operational_impact(asset)
            compliance_impact = await self.calculate_compliance_impact(asset)
            financial_impact = await self.calculate_financial_impact(asset)

            # Weight and combine impacts
            weighted_impact = (
                criticality_impact * 0.30  # Asset criticality most important
                + sensitivity_impact * 0.25  # Data sensitivity very important
                + operational_impact * 0.20  # Operational disruption significant
                + compliance_impact * 0.15  # Compliance impact important
                + financial_impact * 0.10  # Financial impact baseline
            )

            return max(1.0, min(5.0, round(weighted_impact, 1)))

        except Exception as e:
            logger.error("Error calculating impact for asset %s: %s", asset.id, e)
            return 3.0  # Default to medium impact on error

    def get_criticality_impact(self, criticality: str) -> float:
        """Map asset criticality to impact score"""
        criticality_map = {"low": 1.0, "medium": 2.5, "high": 4.0, "critical": 5.0}
        return criticality_map.get(criticality.lower(), 2.5)

    def get_sensitivity_impact(self, classification: str) -> float:
        """Map data sensitivity to impact score"""
        sensitivity_map = {"public": 1.0, "internal": 2.0, "confidential": 4.0, "restricted": 5.0}
        return sensitivity_map.get(classification.lower(), 2.0)

    async def calculate_operational_impact(self, asset: DatabaseAsset) -> float:
        """Calculate operational disruption impact"""
        try:
            impact_factors = []

            # Environment-based impact
            env_impact = {"prod": 5.0, "production": 5.0, "staging": 3.0, "test": 2.0, "dev": 1.5, "development": 1.5}

            if asset.environment:
                impact_factors.append(env_impact.get(asset.environment.lower(), 3.0))
            else:
                impact_factors.append(3.0)  # Default moderate impact

            # Business hours impact (assume higher impact if business-critical)
            if asset.criticality_level in ["high", "critical"]:
                impact_factors.append(4.5)  # High operational dependency
            else:
                impact_factors.append(2.5)  # Lower operational dependency

            # User impact estimation
            if asset.technical_contact and "@" in asset.technical_contact:
                # Has technical contact = likely important system
                impact_factors.append(3.5)
            else:
                impact_factors.append(2.0)

            return sum(impact_factors) / len(impact_factors)

        except Exception as e:
            logger.error("Error calculating operational impact: %s", e)
            return 3.0

    async def calculate_compliance_impact(self, asset: DatabaseAsset) -> float:
        """Calculate regulatory compliance impact"""
        try:
            impact_factors = []

            # Data classification compliance impact
            classification_compliance = {
                "public": 1.0,  # Minimal compliance impact
                "internal": 2.5,  # Moderate compliance requirements
                "confidential": 4.0,  # High compliance requirements
                "restricted": 5.0,  # Maximum compliance requirements
            }

            impact_factors.append(classification_compliance.get(asset.security_classification.lower(), 2.5))

            # Geographic compliance (assume GDPR for EU, other regulations for other regions)
            if asset.location:
                if any(region in asset.location.lower() for region in ["eu", "europe", "gdpr"]):
                    impact_factors.append(4.5)  # High GDPR compliance impact
                elif any(region in asset.location.lower() for region in ["us", "america"]):
                    impact_factors.append(3.5)  # Moderate US regulation impact
                else:
                    impact_factors.append(3.0)  # Default compliance impact
            else:
                impact_factors.append(3.0)

            # Industry-specific compliance (cybersecurity sector has high requirements)
            impact_factors.append(4.0)  # High compliance requirements for cybersecurity

            return sum(impact_factors) / len(impact_factors)

        except Exception as e:
            logger.error("Error calculating compliance impact: %s", e)
            return 3.0

    async def calculate_financial_impact(self, asset: DatabaseAsset) -> float:
        """Calculate financial loss impact"""
        try:
            impact_factors = []

            # Asset value estimation based on type and criticality
            asset_value_map = {
                ("postgresql", "critical"): 5.0,
                ("postgresql", "high"): 4.0,
                ("postgresql", "medium"): 3.0,
                ("sqlite", "critical"): 4.0,
                ("sqlite", "high"): 3.0,
                ("sqlite", "medium"): 2.0,
                ("duckdb", "critical"): 4.5,
                ("duckdb", "high"): 3.5,
                ("duckdb", "medium"): 2.5,
            }

            asset_key = (asset.asset_type.lower(), asset.criticality_level.lower())
            impact_factors.append(asset_value_map.get(asset_key, 3.0))

            # Data sensitivity financial impact
            sensitivity_financial = {"public": 1.0, "internal": 2.5, "confidential": 4.0, "restricted": 5.0}
            impact_factors.append(sensitivity_financial.get(asset.security_classification.lower(), 2.5))

            # Business disruption cost
            if asset.environment and asset.environment.lower() in ["prod", "production"]:
                impact_factors.append(4.5)  # High business disruption cost
            else:
                impact_factors.append(2.0)  # Lower disruption cost for non-prod

            return sum(impact_factors) / len(impact_factors)

        except Exception as e:
            logger.error("Error calculating financial impact: %s", e)
            return 3.0


class SystemCategorizer:
    """
    NIST RMF Step 1: Information System Categorization

    Categorizes information systems based on the impact levels for
    confidentiality, integrity, and availability according to NIST SP 800-60.
    """

    def __init__(self) -> None:
        """Initialize impact calculator."""
        # No specific initialization required
        pass  # pylint: disable=unnecessary-pass

    async def categorize_information_system(self, asset: DatabaseAsset) -> SystemCategorization:
        """
        Perform NIST RMF Step 1: System categorization

        Args:
            asset: Database asset to categorize

        Returns:
            SystemCategorization with impact levels and rationale
        """
        try:
            # Analyze data types and sensitivity
            data_sensitivity = self._analyze_data_sensitivity(asset)

            # Determine impact levels for CIA triad
            confidentiality_impact = self._assess_confidentiality_impact(asset, data_sensitivity)
            integrity_impact = self._assess_integrity_impact(asset, data_sensitivity)
            availability_impact = self._assess_availability_impact(asset, data_sensitivity)

            # Determine overall system categorization (highest impact level)
            overall_categorization = max(
                confidentiality_impact,
                integrity_impact,
                availability_impact,
                key=lambda x: ["low", "moderate", "high"].index(x.value),
            )

            # Generate rationale
            rationale = self._generate_categorization_rationale(
                asset, data_sensitivity, confidentiality_impact, integrity_impact, availability_impact
            )

            return SystemCategorization(
                confidentiality_impact=confidentiality_impact,
                integrity_impact=integrity_impact,
                availability_impact=availability_impact,
                overall_categorization=overall_categorization,
                data_types=data_sensitivity["data_types"],
                rationale=rationale,
            )

        except Exception as e:
            logger.error("Error categorizing system for asset %s: %s", asset.id, e)
            # Return default moderate categorization on error
            return SystemCategorization(
                confidentiality_impact=ImpactLevel.MODERATE,
                integrity_impact=ImpactLevel.MODERATE,
                availability_impact=ImpactLevel.MODERATE,
                overall_categorization=ImpactLevel.MODERATE,
                data_types=["unknown"],
                rationale="Error during categorization - default to moderate impact",
            )

    def _analyze_data_sensitivity(self, asset: DatabaseAsset) -> Dict[str, Any]:
        """Analyze data types and sensitivity based on asset metadata"""
        data_types = []
        sensitivity_indicators = []

        # Infer data types from asset name and metadata
        asset_name_lower = asset.name.lower()

        if any(term in asset_name_lower for term in ["user", "auth", "login", "account"]):
            data_types.append("authentication_data")
            sensitivity_indicators.append("high")

        if any(term in asset_name_lower for term in ["financial", "payment", "billing", "transaction"]):
            data_types.append("financial_data")
            sensitivity_indicators.append("high")

        if any(term in asset_name_lower for term in ["personal", "pii", "customer", "employee"]):
            data_types.append("personal_data")
            sensitivity_indicators.append("high")

        if any(term in asset_name_lower for term in ["analytics", "reporting", "dashboard"]):
            data_types.append("analytics_data")
            sensitivity_indicators.append("medium")

        if any(term in asset_name_lower for term in ["log", "audit", "monitoring"]):
            data_types.append("audit_data")
            sensitivity_indicators.append("medium")

        if any(term in asset_name_lower for term in ["config", "setting", "parameter"]):
            data_types.append("configuration_data")
            sensitivity_indicators.append("medium")

        if not data_types:
            data_types.append("general_business_data")
            sensitivity_indicators.append("medium")

        return {
            "data_types": data_types,
            "sensitivity_indicators": sensitivity_indicators,
            "classification": asset.security_classification,
        }

    def _assess_confidentiality_impact(self, asset: DatabaseAsset, data_sensitivity: Dict) -> ImpactLevel:
        """Assess confidentiality impact level"""
        # Base impact from security classification
        classification_impact = {
            "public": ImpactLevel.LOW,
            "internal": ImpactLevel.MODERATE,
            "confidential": ImpactLevel.HIGH,
            "restricted": ImpactLevel.HIGH,
        }

        base_impact = classification_impact.get(asset.security_classification.lower(), ImpactLevel.MODERATE)

        # Adjust based on data types
        high_sensitivity_data = ["authentication_data", "financial_data", "personal_data"]
        if any(dt in data_sensitivity["data_types"] for dt in high_sensitivity_data):
            if base_impact == ImpactLevel.LOW:
                return ImpactLevel.MODERATE
            elif base_impact == ImpactLevel.MODERATE:
                return ImpactLevel.HIGH

        return base_impact

    def _assess_integrity_impact(self, asset: DatabaseAsset, data_sensitivity: Dict) -> ImpactLevel:
        """Assess integrity impact level"""
        # Start with criticality-based impact
        criticality_impact = {
            "low": ImpactLevel.LOW,
            "medium": ImpactLevel.MODERATE,
            "high": ImpactLevel.HIGH,
            "critical": ImpactLevel.HIGH,
        }

        base_impact = criticality_impact.get(asset.criticality_level.lower(), ImpactLevel.MODERATE)

        # Critical data types require high integrity
        critical_integrity_data = ["financial_data", "authentication_data", "audit_data"]
        if any(dt in data_sensitivity["data_types"] for dt in critical_integrity_data):
            return ImpactLevel.HIGH

        return base_impact

    def _assess_availability_impact(self, asset: DatabaseAsset, data_sensitivity: Dict) -> ImpactLevel:
        """Assess availability impact level"""
        # Environment-based availability requirements
        env_impact = {
            "prod": ImpactLevel.HIGH,
            "production": ImpactLevel.HIGH,
            "staging": ImpactLevel.MODERATE,
            "test": ImpactLevel.LOW,
            "dev": ImpactLevel.LOW,
            "development": ImpactLevel.LOW,
        }

        if asset.environment:
            env_based = env_impact.get(asset.environment.lower(), ImpactLevel.MODERATE)
        else:
            env_based = ImpactLevel.MODERATE

        # Criticality-based availability
        criticality_impact = {
            "low": ImpactLevel.LOW,
            "medium": ImpactLevel.MODERATE,
            "high": ImpactLevel.HIGH,
            "critical": ImpactLevel.HIGH,
        }

        criticality_based = criticality_impact.get(asset.criticality_level.lower(), ImpactLevel.MODERATE)

        # Return the higher of the two assessments
        impact_levels = [ImpactLevel.LOW, ImpactLevel.MODERATE, ImpactLevel.HIGH]
        env_index = impact_levels.index(env_based)
        crit_index = impact_levels.index(criticality_based)

        return impact_levels[max(env_index, crit_index)]

    def _generate_categorization_rationale(
        self,
        asset: DatabaseAsset,
        data_sensitivity: Dict,
        conf_impact: ImpactLevel,
        int_impact: ImpactLevel,
        avail_impact: ImpactLevel,
    ) -> str:
        """Generate human-readable rationale for categorization decision"""
        rationale_parts = []

        # Asset description
        rationale_parts.append(f"Asset '{asset.name}' is a {asset.asset_type} database")

        if asset.environment:
            rationale_parts.append(f"in the {asset.environment} environment")

        # Data sensitivity rationale
        if data_sensitivity["data_types"]:
            data_desc = ", ".join(data_sensitivity["data_types"])
            rationale_parts.append(f"containing {data_desc}")

        # Classification rationale
        rationale_parts.append(f"classified as {asset.security_classification}")

        # Impact rationale
        rationale_parts.append(
            f"Confidentiality impact: {conf_impact.value} " f"(based on data classification and sensitivity)"
        )

        rationale_parts.append(f"Integrity impact: {int_impact.value} " f"(based on criticality level and data types)")

        rationale_parts.append(
            f"Availability impact: {avail_impact.value} " f"(based on environment and business criticality)"
        )

        return ". ".join(rationale_parts) + "."


class NISTRMFRiskEngine:
    """
    Main NIST RMF Risk Assessment Engine

    Orchestrates the complete 6-step NIST RMF process and calculates
    comprehensive risk scores on a 1-25 scale with high performance
    and accuracy requirements.
    """

    def __init__(  # noqa: ANN401
        self,
        vulnerability_service: Any = None,  # noqa: ANN401
        threat_intelligence: Any = None,  # noqa: ANN401
        control_assessor: Any = None,  # noqa: ANN401
    ) -> None:
        """Initialize NIST RMF Risk Engine with optional services."""
        self.vulnerability_service = vulnerability_service
        self.threat_intelligence = threat_intelligence
        self.control_assessor = control_assessor

        # Initialize component calculators
        self.likelihood_calculator = LikelihoodCalculator(vulnerability_service, threat_intelligence)
        self.impact_calculator = ImpactCalculator()
        self.system_categorizer = SystemCategorizer()

        # Load NIST control catalog (placeholder for now)
        self.nist_controls = self._load_nist_control_catalog()

        logger.info("NIST RMF Risk Engine initialized")

    async def calculate_risk_score(self, asset: DatabaseAsset) -> RiskAssessmentResult:
        """
        Calculate comprehensive NIST RMF-compliant risk score

        Implements the complete 6-step NIST RMF process:
        1. Categorize information system
        2. Select security controls
        3. Implement security controls (assess existing implementation)
        4. Assess security controls
        5. Authorize information system (calculate risk)
        6. Monitor security controls

        Args:
            asset: Database asset to assess

        Returns:
            Complete risk assessment result with 1-25 scale risk score
        """
        start_time = time.time()

        try:
            logger.info("Starting NIST RMF risk assessment for asset %s", asset.id)

            # Step 1: Categorize information system
            categorization = await self.categorize_information_system(asset)

            # Step 2: Select security controls
            required_controls = await self.select_security_controls(asset, categorization)

            # Step 3: Implement security controls (assessment of existing implementation)
            control_implementation = await self.assess_control_implementation(asset, required_controls)

            # Step 4: Assess security controls
            control_assessment = await self.assess_control_effectiveness(asset, control_implementation)

            # Step 5: Authorize information system (risk calculation)
            risk_factors = await self.calculate_risk_factors(asset, control_assessment)

            # Calculate final risk score
            risk_score = self.calculate_final_risk_score(risk_factors)

            # Step 6: Monitor security controls (continuous monitoring setup)
            monitoring_plan = await self.create_monitoring_plan(asset, required_controls)

            # Calculate assessment duration
            end_time = time.time()
            duration_ms = int((end_time - start_time) * 1000)

            # Performance requirement check
            if duration_ms > 500:
                logger.warning("Risk assessment took %sms, exceeding 500ms target", duration_ms)

            result = RiskAssessmentResult(
                asset_id=str(asset.id),
                risk_score=risk_score,
                risk_level=self.get_risk_level(risk_score),
                risk_factors=risk_factors,
                categorization=categorization,
                control_assessment=control_assessment,
                monitoring_plan=monitoring_plan,
                assessment_timestamp=datetime.utcnow(),
                next_assessment_due=self.calculate_next_assessment_date(risk_score),
                assessment_duration_ms=duration_ms,
            )

            logger.info(
                "Risk assessment completed for asset %s: score=%s, level=%s, duration=%sms",
                asset.id,
                risk_score,
                result.risk_level.value,
                duration_ms,
            )

            return result

        except Exception as e:
            logger.error("Error in risk assessment for asset %s: %s", asset.id, e)
            raise

    async def categorize_information_system(self, asset: DatabaseAsset) -> SystemCategorization:
        """NIST RMF Step 1: Categorize information system"""
        return await self.system_categorizer.categorize_information_system(asset)

    async def select_security_controls(
        self, asset: DatabaseAsset, categorization: SystemCategorization
    ) -> List[SecurityControl]:
        """NIST RMF Step 2: Select security controls based on categorization"""
        try:
            # Select controls based on system categorization level
            baseline_controls = self._get_baseline_controls(categorization.overall_categorization)

            # Add asset-specific controls
            asset_specific_controls = self._get_asset_specific_controls(asset)

            # Combine and deduplicate
            all_controls = baseline_controls + asset_specific_controls
            unique_controls = {ctrl.id: ctrl for ctrl in all_controls}.values()

            return list(unique_controls)

        except Exception as e:
            logger.error("Error selecting security controls: %s", e)
            return []

    async def assess_control_implementation(
        self, asset: DatabaseAsset, required_controls: List[SecurityControl]
    ) -> Dict[str, Any]:
        """NIST RMF Step 3: Assess control implementation (existing state)"""
        try:
            if self.control_assessor:
                return await self.control_assessor.assess_control_implementation(asset, required_controls)
            else:
                # Default implementation assessment
                return {
                    "implemented_controls": [ctrl.id for ctrl in required_controls[:2]],  # Assume some implemented
                    "partially_implemented_controls": [ctrl.id for ctrl in required_controls[2:4]],
                    "not_implemented_controls": [ctrl.id for ctrl in required_controls[4:]],
                    "implementation_gaps": ["Missing automated monitoring", "Insufficient access controls"],
                }

        except Exception as e:
            logger.error("Error assessing control implementation: %s", e)
            return {
                "implemented_controls": [],
                "partially_implemented_controls": [],
                "not_implemented_controls": [],
                "implementation_gaps": [],
            }

    async def assess_control_effectiveness(
        self, asset: DatabaseAsset, control_implementation: Dict[str, Any]
    ) -> ControlAssessment:
        """NIST RMF Step 4: Assess security controls"""
        try:
            if self.control_assessor:
                return await self.control_assessor.assess_control_effectiveness(asset, control_implementation)
            else:
                # Default control assessment
                implemented = len(control_implementation.get("implemented_controls", []))
                partial = len(control_implementation.get("partially_implemented_controls", []))
                not_implemented = len(control_implementation.get("not_implemented_controls", []))
                total = implemented + partial + not_implemented

                if total == 0:
                    effectiveness = 0.5  # Default moderate effectiveness
                else:
                    # Calculate effectiveness: full credit for implemented, half credit for partial
                    effectiveness = (implemented + 0.5 * partial) / total

                return ControlAssessment(
                    asset_id=str(asset.id),
                    assessment_date=datetime.utcnow(),
                    control_results=[],  # Simplified for this implementation
                    overall_effectiveness=effectiveness,
                    total_controls_assessed=total,
                    implemented_controls=implemented,
                    gaps_identified=len(control_implementation.get("implementation_gaps", [])),
                )

        except Exception as e:
            logger.error("Error assessing control effectiveness: %s", e)
            return ControlAssessment(
                asset_id=str(asset.id),
                assessment_date=datetime.utcnow(),
                control_results=[],
                overall_effectiveness=0.5,
                total_controls_assessed=0,
                implemented_controls=0,
                gaps_identified=0,
            )

    async def calculate_risk_factors(self, asset: DatabaseAsset, control_assessment: ControlAssessment) -> RiskFactors:
        """NIST RMF Step 5: Calculate risk factors for authorization decision"""
        try:
            # Calculate likelihood based on threats and vulnerabilities
            likelihood = await self.likelihood_calculator.calculate_likelihood(asset, control_assessment)

            # Calculate impact based on business criticality and data sensitivity
            impact = await self.impact_calculator.calculate_impact(asset)

            # Calculate exposure factor based on control effectiveness
            exposure = self._calculate_exposure_factor(control_assessment)

            # Calculate confidence based on data quality and assessment coverage
            confidence = self._calculate_confidence(asset, control_assessment)

            return RiskFactors(likelihood=likelihood, impact=impact, exposure=exposure, confidence=confidence)

        except Exception as e:
            logger.error("Error calculating risk factors: %s", e)
            return RiskFactors(likelihood=3.0, impact=3.0, exposure=0.7, confidence=0.5)

    async def create_monitoring_plan(
        self, asset: DatabaseAsset, required_controls: List[SecurityControl]
    ) -> MonitoringPlan:
        """NIST RMF Step 6: Create continuous monitoring plan"""
        try:
            # Determine monitoring frequency based on risk level and criticality
            if asset.criticality_level in ["critical", "high"]:
                continuous_freq = "daily"
                control_freq = "monthly"
                vuln_freq = "weekly"
            elif asset.criticality_level == "medium":
                continuous_freq = "weekly"
                control_freq = "quarterly"
                vuln_freq = "monthly"
            else:
                continuous_freq = "monthly"
                control_freq = "semi-annually"
                vuln_freq = "quarterly"

            return MonitoringPlan(
                continuous_monitoring_frequency=continuous_freq,
                control_assessment_frequency=control_freq,
                vulnerability_scanning_frequency=vuln_freq,
                automated_monitoring_tools=["SIEM", "vulnerability_scanner", "log_analyzer"],
                manual_review_procedures=["quarterly_audit", "annual_assessment", "incident_review"],
            )

        except Exception as e:
            logger.error("Error creating monitoring plan: %s", e)
            return MonitoringPlan(
                continuous_monitoring_frequency="monthly",
                control_assessment_frequency="quarterly",
                vulnerability_scanning_frequency="monthly",
                automated_monitoring_tools=["basic_monitoring"],
                manual_review_procedures=["annual_review"],
            )

    def calculate_final_risk_score(self, factors: RiskFactors) -> float:
        """Calculate final risk score on 1-25 scale using NIST RMF methodology"""
        try:
            # Base calculation: Likelihood × Impact × Exposure
            base_score = factors.likelihood * factors.impact * factors.exposure

            # Apply confidence adjustment (reduce score if low confidence)
            confidence_adjustment = 0.8 + (0.2 * factors.confidence)
            adjusted_score = base_score * confidence_adjustment

            # Ensure score is within 1-25 range
            final_score = max(1.0, min(25.0, adjusted_score))

            # Round to 1 decimal place for consistency
            return round(final_score, 1)

        except Exception as e:
            logger.error("Error calculating final risk score: %s", e)
            return 12.5  # Default to medium risk

    def get_risk_level(self, risk_score: float) -> RiskLevel:
        """Map numeric risk score to categorical risk level"""
        if risk_score <= 5.0:
            return RiskLevel.LOW
        elif risk_score <= 10.0:
            return RiskLevel.MEDIUM
        elif risk_score <= 15.0:
            return RiskLevel.HIGH
        elif risk_score <= 20.0:
            return RiskLevel.VERY_HIGH
        else:
            return RiskLevel.CRITICAL

    def calculate_next_assessment_date(self, risk_score: float) -> datetime:
        """Calculate next assessment due date based on risk score"""
        # Higher risk = more frequent assessments
        if risk_score >= 20.0:  # Critical/Very High
            days_until_next = 30  # Monthly for critical
        elif risk_score >= 15.0:  # High
            days_until_next = 60  # Bi-monthly for high
        elif risk_score >= 10.0:  # Medium
            days_until_next = 90  # Quarterly for medium
        else:  # Low
            days_until_next = 180  # Semi-annually for low

        return datetime.utcnow() + timedelta(days=days_until_next)

    def _calculate_exposure_factor(self, control_assessment: ControlAssessment) -> float:
        """Calculate exposure factor based on control effectiveness"""
        if not control_assessment:
            return 1.0  # Maximum exposure if no controls assessed

        # Exposure decreases with control effectiveness
        # Range: 0.1 (minimum exposure with perfect controls) to 1.0 (maximum exposure with no controls)
        exposure = 1.0 - (control_assessment.overall_effectiveness * 0.9)
        return max(0.1, min(1.0, exposure))

    def _calculate_confidence(self, asset: DatabaseAsset, control_assessment: ControlAssessment) -> float:
        """Calculate confidence in risk assessment based on data quality"""
        confidence_factors = []

        # Asset data completeness
        asset_completeness = 0.0
        if asset.name:
            asset_completeness += 0.1
        if asset.asset_type:
            asset_completeness += 0.2
        if asset.database_version:
            asset_completeness += 0.2
        if asset.security_classification:
            asset_completeness += 0.2
        if asset.criticality_level:
            asset_completeness += 0.2
        if asset.technical_contact:
            asset_completeness += 0.1

        confidence_factors.append(asset_completeness)

        # Control assessment coverage
        if control_assessment and control_assessment.total_controls_assessed > 0:
            control_confidence = min(1.0, control_assessment.total_controls_assessed / 10.0)
        else:
            control_confidence = 0.3  # Low confidence without control assessment

        confidence_factors.append(control_confidence)

        # Vulnerability data availability (placeholder)
        vuln_confidence = 0.8  # Assume good vulnerability data availability
        confidence_factors.append(vuln_confidence)

        # Overall confidence is the average of all factors
        return sum(confidence_factors) / len(confidence_factors)

    def _load_nist_control_catalog(self) -> Dict[str, SecurityControl]:
        """Load NIST SP 800-53 control catalog (placeholder implementation)"""
        # This would load the full NIST SP 800-53 control catalog
        # For now, return a subset of key controls
        controls = {}

        # Access Control (AC) family
        controls["AC-2"] = SecurityControl(
            id="AC-2",
            name="Account Management",
            family=ControlFamily.ACCESS_CONTROL,
            priority="P1",
            baseline="Low",
            description="Manage system accounts, group memberships, privileges, workflow, "
            "notifications, deactivations, and authorizations.",
            implementation_guidance="Implement automated account management procedures.",
        )

        controls["AC-3"] = SecurityControl(
            id="AC-3",
            name="Access Enforcement",
            family=ControlFamily.ACCESS_CONTROL,
            priority="P1",
            baseline="Low",
            description="Enforce approved authorizations for logical access to information and system resources.",
            implementation_guidance="Implement role-based access control mechanisms.",
        )

        # Audit and Accountability (AU) family
        controls["AU-12"] = SecurityControl(
            id="AU-12",
            name="Audit Generation",
            family=ControlFamily.AUDIT_ACCOUNTABILITY,
            priority="P1",
            baseline="Low",
            description="Provide audit record generation capability for the auditable events.",
            implementation_guidance="Configure comprehensive audit logging for database activities.",
        )

        # System and Communications Protection (SC) family
        controls["SC-8"] = SecurityControl(
            id="SC-8",
            name="Transmission Confidentiality and Integrity",
            family=ControlFamily.SYSTEM_COMMUNICATIONS_PROTECTION,
            priority="P1",
            baseline="Moderate",
            description="Protect the confidentiality and integrity of transmitted information.",
            implementation_guidance="Implement encryption for data in transit.",
        )

        return controls

    def _get_baseline_controls(self, categorization_level: ImpactLevel) -> List[SecurityControl]:
        """Get baseline controls for system categorization level"""
        baseline_map = {
            ImpactLevel.LOW: ["AC-2", "AC-3", "AU-12"],
            ImpactLevel.MODERATE: ["AC-2", "AC-3", "AU-12", "SC-8"],
            ImpactLevel.HIGH: ["AC-2", "AC-3", "AU-12", "SC-8"],  # Would include more controls
        }

        control_ids = baseline_map.get(categorization_level, ["AC-2", "AC-3"])
        return [self.nist_controls[ctrl_id] for ctrl_id in control_ids if ctrl_id in self.nist_controls]

    def _get_asset_specific_controls(self, asset: DatabaseAsset) -> List[SecurityControl]:
        """Get additional controls specific to asset characteristics"""
        additional_controls = []

        # Add database-specific controls
        if asset.asset_type.lower() == "postgresql":
            # PostgreSQL-specific controls would be added here
            pass
        elif asset.asset_type.lower() == "sqlite":
            # SQLite-specific controls would be added here
            pass

        # Add environment-specific controls
        if asset.environment and asset.environment.lower() in ["prod", "production"]:
            # Production environment requires additional controls
            pass

        return additional_controls
