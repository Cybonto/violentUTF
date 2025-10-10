# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Gap Prioritizer for Issue #281

This module implements gap prioritization and scoring algorithms based on
business impact, regulatory requirements, and risk assessment.
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.asset_inventory import CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.models.gap_analysis import (
    ComplianceFramework,
    Gap,
    GapSeverity,
    GapType,
    PriorityLevel,
    PriorityScore,
    ResourceAllocationRecommendation,
)

logger = logging.getLogger(__name__)


class GapPrioritizer:
    """Gap prioritization and scoring system."""

    def __init__(self, risk_calculator: Optional[object]) -> None:
        """Initialize gap prioritizer.

        Args:
            risk_calculator: Risk calculation service
        """
        self.risk_calculator = risk_calculator

    def calculate_gap_priority_score(self, gap: Gap, asset: DatabaseAsset) -> PriorityScore:
        """Calculate comprehensive priority score for gap remediation.

        Args:
            gap: Gap to prioritize
            asset: Asset the gap relates to

        Returns:
            Calculated priority score
        """
        try:
            # Base severity score (1-10)
            severity_score = self.get_severity_score(gap.severity)

            # Asset criticality multiplier (1.0-3.0)
            criticality_multiplier = self.get_criticality_multiplier(asset.criticality_level)

            # Regulatory impact multiplier (1.0-2.5)
            regulatory_multiplier = self.get_regulatory_multiplier(gap)

            # Security impact multiplier (1.0-2.0)
            security_multiplier = self.get_security_multiplier(gap, asset)

            # Business impact multiplier (1.0-2.5)
            business_multiplier = self.get_business_impact_multiplier(asset)

            # Urgency multiplier based on deadlines
            urgency_multiplier = self.calculate_urgency_multiplier(gap)

            # Calculate final priority score (max 375)
            priority_score = (
                severity_score
                * criticality_multiplier
                * regulatory_multiplier
                * security_multiplier
                * business_multiplier
                * urgency_multiplier
            )

            # Cap at maximum
            capped_score = min(priority_score, 375)

            return PriorityScore(
                score=capped_score,
                severity_component=severity_score,
                criticality_component=criticality_multiplier,
                regulatory_component=regulatory_multiplier,
                security_component=security_multiplier,
                business_component=business_multiplier,
                priority_level=self.get_priority_level(capped_score),
            )

        except Exception as e:
            logger.error("Error calculating priority score for gap %s: %s", gap.gap_id, str(e))
            # Return default medium priority on error
            return PriorityScore(
                score=100,
                severity_component=5,
                criticality_component=1.5,
                regulatory_component=1.0,
                security_component=1.0,
                business_component=1.5,
                priority_level=PriorityLevel.MEDIUM,
            )

    def get_severity_score(self, severity: GapSeverity) -> float:
        """Map gap severity to numerical score.

        Args:
            severity: Gap severity level

        Returns:
            Numerical severity score (1-10)
        """
        severity_mapping = {GapSeverity.CRITICAL: 10, GapSeverity.HIGH: 8, GapSeverity.MEDIUM: 6, GapSeverity.LOW: 3}
        return severity_mapping.get(severity, 5)

    def get_criticality_multiplier(self, criticality: CriticalityLevel) -> float:
        """Calculate asset criticality multiplier.

        Args:
            criticality: Asset criticality level

        Returns:
            Criticality multiplier (1.0-3.0)
        """
        criticality_mapping = {
            CriticalityLevel.CRITICAL: 3.0,
            CriticalityLevel.HIGH: 2.5,
            CriticalityLevel.MEDIUM: 2.0,
            CriticalityLevel.LOW: 1.0,
        }
        return criticality_mapping.get(criticality, 1.5)

    def get_regulatory_multiplier(self, gap: Gap) -> float:
        """Calculate regulatory impact multiplier.

        Args:
            gap: Gap to assess

        Returns:
            Regulatory impact multiplier (1.0-2.5)
        """
        # Compliance gaps have higher regulatory impact
        if hasattr(gap, "framework"):
            framework_impact = {
                ComplianceFramework.GDPR: 2.5,
                ComplianceFramework.SOC2: 2.0,
                ComplianceFramework.NIST: 2.0,
                ComplianceFramework.HIPAA: 2.5,
                ComplianceFramework.PCI_DSS: 2.3,
            }
            return framework_impact.get(gap.framework, 2.0)

        # Gap types with regulatory implications
        regulatory_gap_types = {
            GapType.INSUFFICIENT_SECURITY_CONTROLS: 2.0,
            GapType.MISSING_DATA_SUBJECT_RIGHTS: 2.2,
            GapType.MISSING_RETENTION_POLICY: 1.8,
            GapType.INSUFFICIENT_ACCESS_CONTROLS: 1.9,
            GapType.MISSING_BACKUP_PROCEDURES: 1.6,
        }

        return regulatory_gap_types.get(gap.gap_type, 1.0)

    def get_security_multiplier(self, gap: Gap, asset: DatabaseAsset) -> float:
        """Calculate security impact multiplier.

        Args:
            gap: Gap to assess
            asset: Asset the gap relates to

        Returns:
            Security impact multiplier (1.0-2.0)
        """
        # Security-related gap types
        security_gap_types = {
            GapType.INSUFFICIENT_SECURITY_CONTROLS: 2.0,
            GapType.INSUFFICIENT_ACCESS_CONTROLS: 1.9,
            GapType.MISSING_BACKUP_PROCEDURES: 1.5,
            GapType.POLICY_VIOLATION: 1.6,
        }

        gap_multiplier = security_gap_types.get(gap.gap_type, 1.0)

        # Asset security classification impact
        classification_impact = {
            SecurityClassification.RESTRICTED: 1.8,
            SecurityClassification.CONFIDENTIAL: 1.6,
            SecurityClassification.INTERNAL: 1.3,
            SecurityClassification.PUBLIC: 1.0,
        }

        classification_multiplier = classification_impact.get(asset.security_classification, 1.0)

        return min(gap_multiplier * classification_multiplier, 2.0)

    def get_business_impact_multiplier(self, asset: DatabaseAsset) -> float:
        """Calculate business impact multiplier.

        Args:
            asset: Asset to assess business impact for

        Returns:
            Business impact multiplier (1.0-2.5)
        """
        # Environment impact
        environment_impact = {Environment.PRODUCTION: 2.5, Environment.STAGING: 1.5, Environment.DEVELOPMENT: 1.0}

        env_multiplier = environment_impact.get(asset.environment, 1.0)

        # Criticality impact
        criticality_impact = {
            CriticalityLevel.CRITICAL: 1.3,
            CriticalityLevel.HIGH: 1.2,
            CriticalityLevel.MEDIUM: 1.1,
            CriticalityLevel.LOW: 1.0,
        }

        crit_multiplier = criticality_impact.get(asset.criticality_level, 1.0)

        # Business impact level (if available)
        business_impact_level = getattr(asset, "business_impact_level", "MEDIUM")
        impact_multiplier = {"HIGH": 1.2, "MEDIUM": 1.0, "LOW": 0.8}.get(business_impact_level, 1.0)

        return min(env_multiplier * crit_multiplier * impact_multiplier, 2.5)

    def calculate_urgency_multiplier(self, gap: Gap) -> float:
        """Calculate urgency multiplier based on deadlines.

        Args:
            gap: Gap to assess urgency for

        Returns:
            Urgency multiplier (0.8-2.0)
        """
        # Check for compliance deadlines
        if hasattr(gap, "compliance_deadline") and gap.compliance_deadline:
            days_to_deadline = (gap.compliance_deadline - datetime.now()).days

            if days_to_deadline <= 30:  # 30 days or less
                return 2.0
            elif days_to_deadline <= 90:  # 3 months or less
                return 1.5
            elif days_to_deadline <= 180:  # 6 months or less
                return 1.2
            else:
                return 1.0

        # Default urgency for different gap types
        urgent_gap_types = {
            GapType.INSUFFICIENT_SECURITY_CONTROLS: 1.3,
            GapType.INSUFFICIENT_ACCESS_CONTROLS: 1.3,
            GapType.MISSING_DATA_SUBJECT_RIGHTS: 1.2,
            GapType.POLICY_VIOLATION: 1.2,
        }

        return urgent_gap_types.get(gap.gap_type, 1.0)

    def get_priority_level(self, score: float) -> PriorityLevel:
        """Determine priority level from numerical score.

        Args:
            score: Numerical priority score

        Returns:
            Priority level enumeration
        """
        if score >= 300:
            return PriorityLevel.CRITICAL
        elif score >= 200:
            return PriorityLevel.HIGH
        elif score >= 100:
            return PriorityLevel.MEDIUM
        else:
            return PriorityLevel.LOW

    def generate_resource_allocation_recommendations(self, gaps: List[Gap]) -> ResourceAllocationRecommendation:
        """Generate resource allocation recommendations for gap remediation.

        Args:
            gaps: List of gaps to allocate resources for

        Returns:
            Resource allocation recommendations
        """
        # Count gaps by priority level
        critical_gaps = len(
            [g for g in gaps if g.priority_score and g.priority_score.priority_level == PriorityLevel.CRITICAL]
        )
        high_gaps = len([g for g in gaps if g.priority_score and g.priority_score.priority_level == PriorityLevel.HIGH])
        immediate_action_gaps = critical_gaps + high_gaps

        medium_gaps = len(
            [g for g in gaps if g.priority_score and g.priority_score.priority_level == PriorityLevel.MEDIUM]
        )
        low_gaps = len([g for g in gaps if g.priority_score and g.priority_score.priority_level == PriorityLevel.LOW])
        scheduled_action_gaps = medium_gaps + low_gaps

        # Calculate total effort
        total_effort = sum(self.estimate_remediation_effort(gap) for gap in gaps)

        # Generate team assignments
        team_assignments = self.recommend_team_assignments(gaps)

        # Calculate timeline
        timeline_weeks = self._calculate_recommended_timeline(gaps, total_effort)

        # Estimate budget (placeholder calculation)
        budget_estimate = total_effort * 150  # $150 per hour estimate

        return ResourceAllocationRecommendation(
            immediate_action_gaps=immediate_action_gaps,
            scheduled_action_gaps=scheduled_action_gaps,
            estimated_effort_hours=total_effort,
            team_assignments=team_assignments,
            recommended_timeline_weeks=timeline_weeks,
            budget_estimate=budget_estimate,
        )

    def estimate_remediation_effort(self, gap: Gap) -> int:
        """Estimate effort required for gap remediation.

        Args:
            gap: Gap to estimate effort for

        Returns:
            Estimated effort in hours
        """
        # Base effort by gap type
        effort_mapping = {
            GapType.MISSING_DOCUMENTATION: 8,
            GapType.OUTDATED_DOCUMENTATION: 4,
            GapType.UNCLEAR_OWNERSHIP: 2,
            GapType.UNREFERENCED_ASSET: 6,
            GapType.UNUSED_ASSET: 4,
            GapType.INSUFFICIENT_SECURITY_CONTROLS: 24,
            GapType.INSUFFICIENT_ACCESS_CONTROLS: 16,
            GapType.MISSING_BACKUP_PROCEDURES: 12,
            GapType.MISSING_RETENTION_POLICY: 6,
            GapType.MISSING_DATA_SUBJECT_RIGHTS: 20,
            GapType.INSUFFICIENT_MONITORING: 8,
            GapType.POLICY_VIOLATION: 10,
            GapType.UNDOCUMENTED_TABLE: 3,
            GapType.UNDOCUMENTED_COLUMN: 1,
            GapType.MISSING_COMPLIANCE_DOCUMENTATION: 12,
        }

        base_effort = effort_mapping.get(gap.gap_type, 8)

        # Adjust for severity
        severity_multiplier = {
            GapSeverity.CRITICAL: 1.5,
            GapSeverity.HIGH: 1.3,
            GapSeverity.MEDIUM: 1.0,
            GapSeverity.LOW: 0.8,
        }

        multiplier = severity_multiplier.get(gap.severity, 1.0)

        return int(base_effort * multiplier)

    def recommend_team_assignments(self, gaps: List[Gap]) -> Dict[str, int]:
        """Recommend team assignments for gap remediation.

        Args:
            gaps: List of gaps to assign teams for

        Returns:
            Dictionary mapping team names to gap counts
        """
        team_assignments = defaultdict(int)

        for gap in gaps:
            if gap.gap_type in [
                GapType.INSUFFICIENT_SECURITY_CONTROLS,
                GapType.INSUFFICIENT_ACCESS_CONTROLS,
                GapType.POLICY_VIOLATION,
            ]:
                team_assignments["security_team"] += 1

            elif gap.gap_type in [
                GapType.MISSING_DOCUMENTATION,
                GapType.OUTDATED_DOCUMENTATION,
                GapType.UNDOCUMENTED_TABLE,
                GapType.UNDOCUMENTED_COLUMN,
            ]:
                team_assignments["documentation_team"] += 1

            elif gap.gap_type in [GapType.MISSING_BACKUP_PROCEDURES, GapType.INSUFFICIENT_MONITORING]:
                team_assignments["operations_team"] += 1

            elif gap.gap_type in [
                GapType.MISSING_DATA_SUBJECT_RIGHTS,
                GapType.MISSING_RETENTION_POLICY,
                GapType.MISSING_COMPLIANCE_DOCUMENTATION,
            ]:
                team_assignments["compliance_team"] += 1

            elif gap.gap_type in [GapType.UNCLEAR_OWNERSHIP, GapType.UNREFERENCED_ASSET, GapType.UNUSED_ASSET]:
                team_assignments["asset_management_team"] += 1

            else:
                team_assignments["general_team"] += 1

        return dict(team_assignments)

    def _calculate_recommended_timeline(self, gaps: List[Gap], total_effort: int) -> int:
        """Calculate recommended timeline for gap remediation.

        Args:
            gaps: List of gaps
            total_effort: Total estimated effort hours

        Returns:
            Recommended timeline in weeks
        """
        # Assume 40 hours per week per team member
        # Assume we can assign teams in parallel
        team_assignments = self.recommend_team_assignments(gaps)
        max_team_count = len(team_assignments)

        # Parallel execution reduces timeline
        parallel_factor = min(max_team_count, 4)  # Max 4 teams in parallel

        # Calculate timeline with parallel execution
        timeline_hours = total_effort / parallel_factor
        timeline_weeks = max(1, int(timeline_hours / 40))  # At least 1 week

        # Add buffer for critical gaps
        critical_gaps = [
            g for g in gaps if g.priority_score and g.priority_score.priority_level == PriorityLevel.CRITICAL
        ]
        if critical_gaps:
            timeline_weeks = max(timeline_weeks, 2)  # At least 2 weeks for critical gaps

        return timeline_weeks

    def cluster_gaps_by_asset(self, gaps: List[Gap]) -> Dict[str, List[Gap]]:
        """Cluster gaps by asset for resource optimization.

        Args:
            gaps: List of gaps to cluster

        Returns:
            Dictionary mapping asset IDs to gap lists
        """
        clusters = defaultdict(list)
        for gap in gaps:
            clusters[gap.asset_id].append(gap)
        return dict(clusters)

    def cluster_gaps_by_type(self, gaps: List[Gap]) -> Dict[GapType, List[Gap]]:
        """Cluster gaps by type for specialized teams.

        Args:
            gaps: List of gaps to cluster

        Returns:
            Dictionary mapping gap types to gap lists
        """
        clusters = defaultdict(list)
        for gap in gaps:
            clusters[gap.gap_type].append(gap)
        return dict(clusters)

    def analyze_priority_trends(self, historical_gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze gap priority trends over time.

        Args:
            historical_gaps: Historical gap data

        Returns:
            Trend analysis results
        """
        if len(historical_gaps) < 2:
            return {
                "insufficient_data": True,
                "critical_gap_trend": 0.0,
                "high_gap_trend": 0.0,
                "overall_improvement": False,
            }

        latest = historical_gaps[0]
        previous = historical_gaps[1]

        critical_trend = latest["critical_gaps"] - previous["critical_gaps"]
        high_trend = latest["high_gaps"] - previous["high_gaps"]

        return {
            "critical_gap_trend": critical_trend / previous["critical_gaps"] if previous["critical_gaps"] > 0 else 0,
            "high_gap_trend": high_trend / previous["high_gaps"] if previous["high_gaps"] > 0 else 0,
            "overall_improvement": critical_trend <= 0 and high_trend <= 0,
        }

    def calculate_sla_impact_multiplier(self, gap: Gap) -> float:
        """Calculate SLA impact multiplier.

        Args:
            gap: Gap to assess SLA impact for

        Returns:
            SLA impact multiplier (1.0-2.0)
        """
        # Check if gap affects SLA-critical assets
        if hasattr(gap, "asset_sla_tier"):
            sla_tiers = {"GOLD": 2.0, "SILVER": 1.5, "BRONZE": 1.2}
            return sla_tiers.get(gap.asset_sla_tier, 1.0)

        return 1.0

    def calculate_cost_benefit_ratio(self, gap: Gap) -> Dict[str, float]:
        """Calculate cost-benefit analysis for gap remediation.

        Args:
            gap: Gap to analyze

        Returns:
            Cost-benefit analysis results
        """
        # Estimate remediation cost
        effort_hours = self.estimate_remediation_effort(gap)
        remediation_cost = effort_hours * 150  # $150 per hour

        # Estimate risk reduction value (placeholder calculation)
        risk_value = 10000  # Base risk value
        severity_multiplier = {
            GapSeverity.CRITICAL: 5.0,
            GapSeverity.HIGH: 3.0,
            GapSeverity.MEDIUM: 2.0,
            GapSeverity.LOW: 1.0,
        }

        risk_reduction_value = risk_value * severity_multiplier.get(gap.severity, 1.0)

        # Calculate penalties avoided (for compliance gaps)
        penalty_avoidance = 0
        if hasattr(gap, "framework"):
            penalty_values = {
                ComplianceFramework.GDPR: 50000,
                ComplianceFramework.SOC2: 25000,
                ComplianceFramework.NIST: 20000,
            }
            penalty_avoidance = penalty_values.get(gap.framework, 0)

        total_benefit = risk_reduction_value + penalty_avoidance
        benefit_cost_ratio = total_benefit / remediation_cost if remediation_cost > 0 else 0
        net_benefit = total_benefit - remediation_cost
        roi_percentage = (net_benefit / remediation_cost * 100) if remediation_cost > 0 else 0

        return {
            "remediation_cost": remediation_cost,
            "risk_reduction_value": risk_reduction_value,
            "compliance_penalty_avoidance": penalty_avoidance,
            "total_benefit": total_benefit,
            "benefit_cost_ratio": benefit_cost_ratio,
            "net_benefit": net_benefit,
            "roi_percentage": roi_percentage,
        }


class RiskCalculator:
    """Risk calculation service for gap prioritization."""

    def calculate_security_risk(self, gap: Gap, asset: DatabaseAsset) -> float:
        """Calculate security risk score.

        Args:
            gap: Gap to assess
            asset: Asset the gap relates to

        Returns:
            Security risk score (0.0-1.0)
        """
        # Placeholder implementation
        return 0.5

    def calculate_compliance_risk(self, gap: Gap) -> float:
        """Calculate compliance risk score.

        Args:
            gap: Gap to assess

        Returns:
            Compliance risk score (0.0-1.0)
        """
        # Placeholder implementation
        return 0.6

    def calculate_operational_risk(self, gap: Gap, asset: DatabaseAsset) -> float:
        """Calculate operational risk score.

        Args:
            gap: Gap to assess
            asset: Asset the gap relates to

        Returns:
            Operational risk score (0.0-1.0)
        """
        # Placeholder implementation
        return 0.4
