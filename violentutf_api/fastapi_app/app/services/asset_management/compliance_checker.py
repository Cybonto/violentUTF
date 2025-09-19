# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Compliance Gap Checker for Issue #281

This module implements compliance validation engines for GDPR, SOC2, and NIST
frameworks with 95% accuracy targets.
"""

import logging
from typing import Any, Dict, List, Optional

from app.models.asset_inventory import CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.models.gap_analysis import (
    ComplianceFramework,
    ComplianceGap,
    GapSeverity,
    GapType,
    PolicyAssessment,
    PolicyGap,
    PolicyViolation,
)

logger = logging.getLogger(__name__)


class ComplianceGapChecker:
    """Main compliance gap checker orchestrating all frameworks."""

    def __init__(self, compliance_rules: Optional[object]) -> None:
        """Initialize compliance gap checker.

        Args:
            compliance_rules: Compliance rule engine
        """
        self.compliance_rules = compliance_rules
        self.gdpr_checker = GDPRComplianceChecker()
        self.soc2_checker = SOC2ComplianceChecker()
        self.nist_checker = NISTComplianceChecker()

    async def assess_compliance_gaps(self, asset: DatabaseAsset) -> List[ComplianceGap]:
        """Assess compliance gaps across all applicable frameworks.

        Args:
            asset: Asset to assess for compliance

        Returns:
            List of compliance gaps identified
        """
        logger.debug("Assessing compliance gaps for asset %s", asset.id)

        compliance_gaps = []

        try:
            # GDPR compliance assessment
            if self.is_gdpr_applicable(asset):
                gdpr_gaps = await self.gdpr_checker.assess_gaps(asset)
                compliance_gaps.extend(gdpr_gaps)

            # SOC 2 compliance assessment
            if self.is_soc2_applicable(asset):
                soc2_gaps = await self.soc2_checker.assess_gaps(asset)
                compliance_gaps.extend(soc2_gaps)

            # NIST compliance assessment
            if self.is_nist_applicable(asset):
                nist_gaps = await self.nist_checker.assess_gaps(asset)
                compliance_gaps.extend(nist_gaps)

            logger.debug("Found %d compliance gaps for asset %s", len(compliance_gaps), asset.id)

        except Exception as e:
            logger.error("Error assessing compliance for asset %s: %s", asset.id, str(e))

        return compliance_gaps

    def is_gdpr_applicable(self, asset: DatabaseAsset) -> bool:
        """Determine if GDPR applies to this asset.

        Args:
            asset: Asset to check

        Returns:
            True if GDPR compliance assessment is required
        """
        # Check if asset contains personal data
        return (
            asset.security_classification in [SecurityClassification.CONFIDENTIAL, SecurityClassification.RESTRICTED]
            or "personal" in asset.purpose_description.lower()
            if hasattr(asset, "purpose_description") and asset.purpose_description
            else False or "user" in asset.name.lower()
        )

    def is_soc2_applicable(self, asset: DatabaseAsset) -> bool:
        """Determine if SOC2 applies to this asset.

        Args:
            asset: Asset to check

        Returns:
            True if SOC2 compliance assessment is required
        """
        # Production assets generally require SOC2 compliance
        return asset.environment == Environment.PRODUCTION

    def is_nist_applicable(self, asset: DatabaseAsset) -> bool:
        """Determine if NIST framework applies to this asset.

        Args:
            asset: Asset to check

        Returns:
            True if NIST compliance assessment is required
        """
        # Critical and high-value assets require NIST compliance
        return asset.criticality_level in [CriticalityLevel.CRITICAL, CriticalityLevel.HIGH]


class GDPRComplianceChecker:
    """GDPR compliance assessment with 95% accuracy target."""

    async def assess_gaps(self, asset: DatabaseAsset) -> List[ComplianceGap]:
        """Assess GDPR compliance gaps for asset.

        Args:
            asset: Asset to assess

        Returns:
            List of GDPR compliance gaps
        """
        gaps = []

        try:
            # Check data protection impact assessment (DPIA)
            if asset.security_classification == SecurityClassification.RESTRICTED:
                dpia_doc = await self.find_dpia_documentation(asset)
                if not dpia_doc:
                    gaps.append(
                        ComplianceGap(
                            asset_id=asset.id,
                            framework=ComplianceFramework.GDPR,
                            requirement="Article 35 - DPIA",
                            gap_type=GapType.MISSING_COMPLIANCE_DOCUMENTATION,
                            severity=GapSeverity.HIGH,
                            description="High-risk personal data processing requires DPIA",
                            recommendations=[
                                "Conduct Data Protection Impact Assessment",
                                "Document privacy risks and mitigation measures",
                                "Obtain DPO approval if required",
                            ],
                        )
                    )

            # Check data retention policy
            if (
                not hasattr(asset, "compliance_requirements")
                or not asset.compliance_requirements
                or "data_retention_period" not in asset.compliance_requirements
            ):
                gaps.append(
                    ComplianceGap(
                        asset_id=asset.id,
                        framework=ComplianceFramework.GDPR,
                        requirement="Article 5(1)(e) - Storage limitation",
                        gap_type=GapType.MISSING_RETENTION_POLICY,
                        severity=GapSeverity.MEDIUM,
                        description="No documented data retention period",
                        recommendations=[
                            "Define data retention period based on purpose",
                            "Implement automated data deletion",
                            "Document retention justification",
                        ],
                    )
                )

            # Check encryption for personal data
            if not getattr(asset, "encryption_enabled", False):
                gaps.append(
                    ComplianceGap(
                        asset_id=asset.id,
                        framework=ComplianceFramework.GDPR,
                        requirement="Article 32 - Security of processing",
                        gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
                        severity=GapSeverity.HIGH,
                        description="Personal data not encrypted at rest",
                        recommendations=[
                            "Enable database encryption",
                            "Implement encryption key management",
                            "Document encryption procedures",
                        ],
                    )
                )

            # Check data subject rights implementation
            rights_implementation = await self.check_data_subject_rights(asset)
            if not rights_implementation.access_right_implemented:
                gaps.append(
                    ComplianceGap(
                        asset_id=asset.id,
                        framework=ComplianceFramework.GDPR,
                        requirement="Article 15 - Right of access",
                        gap_type=GapType.MISSING_DATA_SUBJECT_RIGHTS,
                        severity=GapSeverity.MEDIUM,
                        description="No mechanism for data subject access requests",
                        recommendations=[
                            "Implement data export functionality",
                            "Create data subject request process",
                            "Document access procedures",
                        ],
                    )
                )

        except Exception as e:
            logger.error("Error in GDPR assessment for asset %s: %s", asset.id, str(e))

        return gaps

    async def find_dpia_documentation(self, asset: DatabaseAsset) -> Dict[str, Any]:
        """Find DPIA documentation for asset.

        Args:
            asset: Asset to check for DPIA

        Returns:
            DPIA documentation object or None
        """
        # Placeholder implementation
        # In practice, this would query a documentation system
        return None

    async def check_data_subject_rights(self, asset: DatabaseAsset) -> List[str]:
        """Check implementation of data subject rights.

        Args:
            asset: Asset to check

        Returns:
            Data subject rights implementation status
        """
        # Placeholder implementation
        from types import SimpleNamespace

        return SimpleNamespace(
            access_right_implemented=False,
            rectification_right_implemented=False,
            erasure_right_implemented=False,
            portability_right_implemented=False,
        )


class SOC2ComplianceChecker:
    """SOC 2 Type II compliance assessment with 95% accuracy target."""

    async def assess_gaps(self, asset: DatabaseAsset) -> List[ComplianceGap]:
        """Assess SOC 2 Type II compliance gaps.

        Args:
            asset: Asset to assess

        Returns:
            List of SOC2 compliance gaps
        """
        gaps = []

        try:
            # Security control CC6.1 - Logical access controls
            if not getattr(asset, "access_restricted", False):
                gaps.append(
                    ComplianceGap(
                        asset_id=asset.id,
                        framework=ComplianceFramework.SOC2,
                        requirement="CC6.1 - Logical Access Controls",
                        gap_type=GapType.INSUFFICIENT_ACCESS_CONTROLS,
                        severity=GapSeverity.HIGH,
                        description="No access restrictions implemented",
                        recommendations=[
                            "Implement role-based access controls",
                            "Configure database authentication",
                            "Document access procedures",
                        ],
                    )
                )

            # Security control CC6.7 - System backup and recovery
            if not getattr(asset, "backup_configured", False):
                gaps.append(
                    ComplianceGap(
                        asset_id=asset.id,
                        framework=ComplianceFramework.SOC2,
                        requirement="CC6.7 - System Backup and Recovery",
                        gap_type=GapType.MISSING_BACKUP_PROCEDURES,
                        severity=GapSeverity.HIGH,
                        description="No backup procedures configured",
                        recommendations=[
                            "Configure automated backups",
                            "Test backup recovery procedures",
                            "Document backup schedules and retention",
                        ],
                    )
                )

            # Monitoring and logging CC7.2
            monitoring_gaps = await self.check_monitoring_controls(asset)
            gaps.extend(monitoring_gaps)

        except Exception as e:
            logger.error("Error in SOC2 assessment for asset %s: %s", asset.id, str(e))

        return gaps

    async def check_monitoring_controls(self, asset: DatabaseAsset) -> List[ComplianceGap]:
        """Check monitoring control implementation.

        Args:
            asset: Asset to check

        Returns:
            List of monitoring-related compliance gaps
        """
        gaps = []

        if not getattr(asset, "monitoring_enabled", False):
            gaps.append(
                ComplianceGap(
                    asset_id=asset.id,
                    framework=ComplianceFramework.SOC2,
                    requirement="CC7.2 - Monitoring Activities",
                    gap_type=GapType.INSUFFICIENT_MONITORING,
                    severity=GapSeverity.MEDIUM,
                    description="No monitoring configured for this asset",
                    recommendations=[
                        "Configure database monitoring",
                        "Implement alerting for critical events",
                        "Document monitoring procedures",
                    ],
                )
            )

        return gaps


class NISTComplianceChecker:
    """NIST Cybersecurity Framework compliance assessment with 95% accuracy target."""

    async def assess_gaps(self, asset: DatabaseAsset) -> List[ComplianceGap]:
        """Assess NIST framework compliance gaps.

        Args:
            asset: Asset to assess

        Returns:
            List of NIST compliance gaps
        """
        gaps = []

        try:
            # PR.DS-1 - Data-at-rest protection
            if not getattr(asset, "encryption_enabled", False):
                gaps.append(
                    ComplianceGap(
                        asset_id=asset.id,
                        framework=ComplianceFramework.NIST,
                        requirement="PR.DS-1 - Data-at-rest protection",
                        gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
                        severity=GapSeverity.MEDIUM,
                        description="Encryption at rest not configured",
                        recommendations=[
                            "Configure data encryption",
                            "Implement key management",
                            "Document encryption procedures",
                        ],
                    )
                )

            # PR.AC-1 - Identity and access management
            if not getattr(asset, "access_controls_implemented", False):
                gaps.append(
                    ComplianceGap(
                        asset_id=asset.id,
                        framework=ComplianceFramework.NIST,
                        requirement="PR.AC-1 - Identity and access management",
                        gap_type=GapType.INSUFFICIENT_ACCESS_CONTROLS,
                        severity=GapSeverity.HIGH,
                        description="Access controls not properly implemented",
                        recommendations=[
                            "Implement identity and access management",
                            "Configure multi-factor authentication",
                            "Regular access reviews",
                        ],
                    )
                )

            # RS.RP-1 - Response planning
            if not getattr(asset, "incident_response_plan", False):
                gaps.append(
                    ComplianceGap(
                        asset_id=asset.id,
                        framework=ComplianceFramework.NIST,
                        requirement="RS.RP-1 - Response planning",
                        gap_type=GapType.MISSING_COMPLIANCE_DOCUMENTATION,
                        severity=GapSeverity.MEDIUM,
                        description="No incident response plan documented",
                        recommendations=[
                            "Create incident response plan",
                            "Define escalation procedures",
                            "Test response procedures",
                        ],
                    )
                )

        except Exception as e:
            logger.error("Error in NIST assessment for asset %s: %s", asset.id, str(e))

        return gaps


class SecurityPolicyChecker:
    """Organizational security policy compliance checker."""

    def __init__(self, policy_engine: Optional[object]) -> None:
        """Initialize security policy checker.

        Args:
            policy_engine: Security policy engine
        """
        self.policy_engine = policy_engine

    async def assess_policy_gaps(self, asset: DatabaseAsset) -> List[PolicyGap]:
        """Assess gaps against organizational security policies.

        Args:
            asset: Asset to assess

        Returns:
            List of policy compliance gaps
        """
        gaps = []

        try:
            applicable_policies = self.policy_engine.get_applicable_policies(asset)

            for policy in applicable_policies:
                policy_assessment = await self.assess_asset_against_policy(asset, policy)
                if not policy_assessment.compliant:
                    gaps.append(
                        PolicyGap(
                            asset_id=asset.id,
                            policy_id=policy.id,
                            policy_name=policy.name,
                            gap_type=GapType.POLICY_VIOLATION,
                            severity=self.calculate_policy_gap_severity(policy, policy_assessment),
                            violations=[
                                {
                                    "rule_id": v.rule_id,
                                    "description": v.rule_description,
                                    "actual": v.actual_value,
                                    "expected": v.expected_value,
                                    "impact": v.impact,
                                }
                                for v in policy_assessment.violations
                            ],
                            description=f"Asset violates policy: {policy.name}",
                            recommendations=policy_assessment.recommendations,
                        )
                    )

        except Exception as e:
            logger.error("Error assessing policy compliance for asset %s: %s", asset.id, str(e))

        return gaps

    async def assess_asset_against_policy(self, asset: DatabaseAsset, policy: Dict[str, Any]) -> PolicyAssessment:
        """Assess specific asset against security policy.

        Args:
            asset: Asset to assess
            policy: Security policy to check against

        Returns:
            Policy assessment result
        """
        violations = []

        try:
            for rule in policy.rules:
                if not await self.evaluate_policy_rule(asset, rule):
                    violations.append(
                        PolicyViolation(
                            rule_id=rule.id,
                            rule_description=rule.description,
                            actual_value=await self.get_asset_value_for_rule(asset, rule),
                            expected_value=rule.expected_value,
                            impact=rule.impact_level,
                        )
                    )

        except Exception as e:
            logger.error("Error evaluating policy %s for asset %s: %s", policy.id, asset.id, str(e))

        return PolicyAssessment(
            compliant=len(violations) == 0,
            violations=violations,
            recommendations=self.generate_policy_recommendations(violations),
        )

    async def evaluate_policy_rule(self, asset: DatabaseAsset, rule: Dict[str, Any]) -> bool:
        """Evaluate a specific policy rule against an asset.

        Args:
            asset: Asset to evaluate
            rule: Policy rule to check

        Returns:
            True if asset complies with the rule
        """
        # Placeholder implementation
        # In practice, this would evaluate specific rule types
        return True

    async def get_asset_value_for_rule(self, asset: DatabaseAsset, rule: Dict[str, Any]) -> str:
        """Get asset value for a specific policy rule.

        Args:
            asset: Asset to get value from
            rule: Policy rule requesting the value

        Returns:
            Asset value for the rule
        """
        # Placeholder implementation
        return None

    def calculate_policy_gap_severity(self, policy: Dict[str, Any], assessment: PolicyAssessment) -> GapSeverity:
        """Calculate severity for policy gaps.

        Args:
            policy: Policy that was violated
            assessment: Policy assessment result

        Returns:
            Calculated severity level
        """
        # High impact violations get high severity
        high_impact_violations = [v for v in assessment.violations if v.impact == "HIGH"]
        if high_impact_violations:
            return GapSeverity.HIGH

        # Medium impact violations get medium severity
        medium_impact_violations = [v for v in assessment.violations if v.impact == "MEDIUM"]
        if medium_impact_violations:
            return GapSeverity.MEDIUM

        # Default to low severity
        return GapSeverity.LOW

    def generate_policy_recommendations(self, violations: List[PolicyViolation]) -> List[str]:
        """Generate recommendations for policy compliance.

        Args:
            violations: List of policy violations

        Returns:
            List of actionable recommendations
        """
        recommendations = []

        for violation in violations:
            if "encryption" in violation.rule_description.lower():
                recommendations.append("Enable database encryption to meet policy requirements")
            elif "access" in violation.rule_description.lower():
                recommendations.append("Implement access controls according to policy")
            elif "backup" in violation.rule_description.lower():
                recommendations.append("Configure backup procedures per policy")
            else:
                recommendations.append(f"Address policy violation: {violation.rule_description}")

        # Remove duplicates while preserving order
        return list(dict.fromkeys(recommendations))
