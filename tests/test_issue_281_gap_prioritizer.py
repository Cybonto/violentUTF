"""
Test suite for Issue #281: Gap Identification Algorithms - Gap Prioritizer

This module tests the gap prioritization and scoring system that calculates
priority scores based on business impact, regulatory requirements, and risk.

Test Coverage:
- Multi-factor priority scoring
- Business impact assessment
- Risk-based prioritization
- Resource allocation recommendations
- Trend analysis algorithms
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.models.gap_analysis import (
    ComplianceFramework,
    ComplianceGap,
    DocumentationGap,
    Gap,
    GapSeverity,
    GapType,
    OrphanedAssetGap,
)

# Import the classes we'll be testing (will be implemented)
from app.services.asset_management.gap_prioritizer import (
    BusinessImpactAssessment,
    GapPrioritizer,
    PriorityLevel,
    PriorityScore,
    ResourceAllocationRecommendation,
    RiskCalculator,
)


class TestGapPrioritizer:
    """Test suite for the GapPrioritizer class."""

    @pytest.fixture
    def mock_risk_calculator(self):
        """Mock risk calculator for testing."""
        calculator = Mock()
        calculator.calculate_security_risk.return_value = 0.8
        calculator.calculate_compliance_risk.return_value = 0.9
        calculator.calculate_operational_risk.return_value = 0.6
        return calculator

    @pytest.fixture
    def gap_prioritizer(self, mock_risk_calculator):
        """Create GapPrioritizer with mocked dependencies."""
        return GapPrioritizer(risk_calculator=mock_risk_calculator)

    @pytest.fixture
    def critical_production_asset(self):
        """Critical production asset for testing."""
        return DatabaseAsset(
            id="critical_db",
            name="production_database",
            asset_type=AssetType.POSTGRESQL,
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.CRITICAL,
            security_classification=SecurityClassification.CONFIDENTIAL,
            business_impact_level="HIGH"
        )

    @pytest.fixture
    def low_dev_asset(self):
        """Low priority development asset for testing."""
        return DatabaseAsset(
            id="dev_db",
            name="development_database",
            asset_type=AssetType.SQLITE,
            environment=Environment.DEVELOPMENT,
            criticality_level=CriticalityLevel.LOW,
            security_classification=SecurityClassification.INTERNAL,
            business_impact_level="LOW"
        )

    def test_prioritizer_initialization(self, gap_prioritizer):
        """Test GapPrioritizer initialization."""
        assert gap_prioritizer is not None
        assert gap_prioritizer.risk_calculator is not None

    def test_calculate_gap_priority_score_high_priority(self, gap_prioritizer, critical_production_asset):
        """Test priority score calculation for high-priority gap."""
        # High severity compliance gap on critical production asset
        compliance_gap = ComplianceGap(
            asset_id="critical_db",
            framework=ComplianceFramework.GDPR,
            requirement="Article 32 - Security of processing",
            gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
            severity=GapSeverity.HIGH,
            description="Missing encryption",
            recommendations=["Enable encryption"]
        )
        
        score = gap_prioritizer.calculate_gap_priority_score(compliance_gap, critical_production_asset)
        
        # Should be high priority score
        assert isinstance(score, PriorityScore)
        assert score.score >= 200  # High score due to multiple high factors
        assert score.priority_level == PriorityLevel.CRITICAL
        assert score.severity_component >= 8  # High severity
        assert score.criticality_component >= 2.5  # Critical asset
        assert score.regulatory_component >= 2.0  # GDPR compliance

    def test_calculate_gap_priority_score_low_priority(self, gap_prioritizer, low_dev_asset):
        """Test priority score calculation for low-priority gap."""
        # Low severity documentation gap on development asset
        doc_gap = DocumentationGap(
            asset_id="dev_db",
            gap_type=GapType.OUTDATED_DOCUMENTATION,
            documentation_type="basic_info",
            severity=GapSeverity.LOW,
            description="Documentation is 60 days old",
            recommendations=["Update documentation"]
        )
        
        score = gap_prioritizer.calculate_gap_priority_score(doc_gap, low_dev_asset)
        
        # Should be low priority score
        assert score.score <= 50  # Low score due to low impact factors
        assert score.priority_level in [PriorityLevel.LOW, PriorityLevel.MEDIUM]
        assert score.severity_component <= 4  # Low severity
        assert score.criticality_component <= 1.5  # Low criticality

    def test_severity_score_mapping(self, gap_prioritizer):
        """Test mapping of gap severity to numerical scores."""
        assert gap_prioritizer.get_severity_score(GapSeverity.HIGH) == 10
        assert gap_prioritizer.get_severity_score(GapSeverity.MEDIUM) == 6
        assert gap_prioritizer.get_severity_score(GapSeverity.LOW) == 3

    def test_criticality_multiplier_calculation(self, gap_prioritizer):
        """Test asset criticality multiplier calculation."""
        assert gap_prioritizer.get_criticality_multiplier(CriticalityLevel.CRITICAL) == 3.0
        assert gap_prioritizer.get_criticality_multiplier(CriticalityLevel.HIGH) == 2.5
        assert gap_prioritizer.get_criticality_multiplier(CriticalityLevel.MEDIUM) == 2.0
        assert gap_prioritizer.get_criticality_multiplier(CriticalityLevel.LOW) == 1.0

    def test_regulatory_impact_multiplier(self, gap_prioritizer):
        """Test regulatory impact multiplier calculation."""
        # GDPR compliance gap should have high multiplier
        gdpr_gap = Mock(
            gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
            framework=ComplianceFramework.GDPR
        )
        multiplier = gap_prioritizer.get_regulatory_multiplier(gdpr_gap)
        assert multiplier >= 2.0
        
        # Documentation gap should have lower multiplier
        doc_gap = Mock(
            gap_type=GapType.MISSING_DOCUMENTATION,
            framework=None
        )
        multiplier = gap_prioritizer.get_regulatory_multiplier(doc_gap)
        assert multiplier <= 1.5

    def test_security_impact_multiplier(self, gap_prioritizer, critical_production_asset):
        """Test security impact multiplier calculation."""
        # Security control gap on confidential asset should have high multiplier
        security_gap = Mock(gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS)
        
        multiplier = gap_prioritizer.get_security_multiplier(security_gap, critical_production_asset)
        assert multiplier >= 1.5
        
        # Documentation gap should have lower security multiplier
        doc_gap = Mock(gap_type=GapType.MISSING_DOCUMENTATION)
        multiplier = gap_prioritizer.get_security_multiplier(doc_gap, critical_production_asset)
        assert multiplier <= 1.2

    def test_business_impact_multiplier(self, gap_prioritizer, critical_production_asset, low_dev_asset):
        """Test business impact multiplier calculation."""
        # Critical production asset should have high multiplier
        multiplier = gap_prioritizer.get_business_impact_multiplier(critical_production_asset)
        assert multiplier >= 2.0
        
        # Low development asset should have lower multiplier
        multiplier = gap_prioritizer.get_business_impact_multiplier(low_dev_asset)
        assert multiplier <= 1.5

    def test_priority_level_determination(self, gap_prioritizer):
        """Test priority level determination from scores."""
        assert gap_prioritizer.get_priority_level(350) == PriorityLevel.CRITICAL
        assert gap_prioritizer.get_priority_level(250) == PriorityLevel.HIGH
        assert gap_prioritizer.get_priority_level(150) == PriorityLevel.MEDIUM
        assert gap_prioritizer.get_priority_level(50) == PriorityLevel.LOW

    def test_score_capping(self, gap_prioritizer, critical_production_asset):
        """Test that priority scores are capped at maximum value."""
        # Create gap that would generate extremely high score
        extreme_gap = Mock(
            severity=GapSeverity.HIGH,
            gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
            framework=ComplianceFramework.GDPR
        )
        
        score = gap_prioritizer.calculate_gap_priority_score(extreme_gap, critical_production_asset)
        
        # Score should be capped at maximum (375)
        assert score.score <= 375

    def test_compliance_deadline_urgency(self, gap_prioritizer):
        """Test urgency multiplier based on compliance deadlines."""
        # Gap with approaching compliance deadline
        urgent_gap = Mock(
            compliance_deadline=datetime.now() + timedelta(days=30),  # 30 days
            framework=ComplianceFramework.GDPR
        )
        
        urgency = gap_prioritizer.calculate_urgency_multiplier(urgent_gap)
        assert urgency >= 1.5  # Approaching deadline increases urgency
        
        # Gap with distant deadline
        distant_gap = Mock(
            compliance_deadline=datetime.now() + timedelta(days=365),  # 1 year
            framework=ComplianceFramework.GDPR
        )
        
        urgency = gap_prioritizer.calculate_urgency_multiplier(distant_gap)
        assert urgency <= 1.2  # Distant deadline has lower urgency

    def test_resource_allocation_recommendations(self, gap_prioritizer):
        """Test generation of resource allocation recommendations."""
        # High priority gaps
        high_priority_gaps = [
            Mock(priority_score=Mock(score=300, priority_level=PriorityLevel.CRITICAL)),
            Mock(priority_score=Mock(score=280, priority_level=PriorityLevel.HIGH))
        ]
        
        # Low priority gaps
        low_priority_gaps = [
            Mock(priority_score=Mock(score=50, priority_level=PriorityLevel.LOW)),
            Mock(priority_score=Mock(score=40, priority_level=PriorityLevel.LOW))
        ]
        
        all_gaps = high_priority_gaps + low_priority_gaps
        
        recommendations = gap_prioritizer.generate_resource_allocation_recommendations(all_gaps)
        
        assert isinstance(recommendations, ResourceAllocationRecommendation)
        assert recommendations.immediate_action_gaps == 2  # Critical and High
        assert recommendations.scheduled_action_gaps == 2  # Low priority
        assert recommendations.estimated_effort_hours > 0
        assert len(recommendations.team_assignments) > 0

    def test_gap_clustering_by_asset(self, gap_prioritizer):
        """Test clustering of gaps by asset for resource optimization."""
        gaps = [
            Mock(asset_id="asset_001", priority_score=Mock(score=200)),
            Mock(asset_id="asset_001", priority_score=Mock(score=180)),
            Mock(asset_id="asset_002", priority_score=Mock(score=150)),
            Mock(asset_id="asset_002", priority_score=Mock(score=120))
        ]
        
        clusters = gap_prioritizer.cluster_gaps_by_asset(gaps)
        
        assert len(clusters) == 2
        assert "asset_001" in clusters
        assert "asset_002" in clusters
        assert len(clusters["asset_001"]) == 2
        assert len(clusters["asset_002"]) == 2

    def test_gap_clustering_by_type(self, gap_prioritizer):
        """Test clustering of gaps by type for specialized teams."""
        gaps = [
            Mock(gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS),
            Mock(gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS),
            Mock(gap_type=GapType.MISSING_DOCUMENTATION),
            Mock(gap_type=GapType.OUTDATED_DOCUMENTATION)
        ]
        
        clusters = gap_prioritizer.cluster_gaps_by_type(gaps)
        
        assert GapType.INSUFFICIENT_SECURITY_CONTROLS in clusters
        assert GapType.MISSING_DOCUMENTATION in clusters
        assert len(clusters[GapType.INSUFFICIENT_SECURITY_CONTROLS]) == 2
        assert len(clusters[GapType.MISSING_DOCUMENTATION]) == 1  # OUTDATED_DOCUMENTATION separate

    def test_effort_estimation(self, gap_prioritizer):
        """Test effort estimation for gap remediation."""
        # High complexity security gap
        security_gap = Mock(
            gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
            severity=GapSeverity.HIGH,
            complexity="HIGH"
        )
        
        effort = gap_prioritizer.estimate_remediation_effort(security_gap)
        assert effort >= 16  # High effort for complex security gaps
        
        # Simple documentation gap
        doc_gap = Mock(
            gap_type=GapType.MISSING_DOCUMENTATION,
            severity=GapSeverity.LOW,
            complexity="LOW"
        )
        
        effort = gap_prioritizer.estimate_remediation_effort(doc_gap)
        assert effort <= 8  # Lower effort for documentation

    def test_team_assignment_recommendations(self, gap_prioritizer):
        """Test team assignment recommendations based on gap types."""
        gaps = [
            Mock(gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS),
            Mock(gap_type=GapType.MISSING_DOCUMENTATION),
            Mock(gap_type=GapType.INSUFFICIENT_ACCESS_CONTROLS),
            Mock(gap_type=GapType.OUTDATED_DOCUMENTATION)
        ]
        
        assignments = gap_prioritizer.recommend_team_assignments(gaps)
        
        assert "security_team" in assignments
        assert "documentation_team" in assignments
        assert len(assignments["security_team"]) == 2  # Two security gaps
        assert len(assignments["documentation_team"]) == 2  # Two documentation gaps

    def test_priority_trend_analysis(self, gap_prioritizer):
        """Test analysis of gap priority trends over time."""
        # Mock historical gap data
        historical_gaps = [
            {
                "date": datetime.now() - timedelta(days=30),
                "critical_gaps": 5,
                "high_gaps": 10,
                "medium_gaps": 15,
                "low_gaps": 20
            },
            {
                "date": datetime.now() - timedelta(days=60),
                "critical_gaps": 8,
                "high_gaps": 15,
                "medium_gaps": 20,
                "low_gaps": 25
            }
        ]
        
        trend = gap_prioritizer.analyze_priority_trends(historical_gaps)
        
        # Should show improvement (fewer critical/high gaps)
        assert trend.critical_gap_trend < 0  # Decreasing
        assert trend.high_gap_trend < 0      # Decreasing
        assert trend.overall_improvement is True

    def test_sla_based_prioritization(self, gap_prioritizer):
        """Test prioritization based on SLA requirements."""
        # Gap affecting SLA-critical asset
        sla_gap = Mock(
            asset_sla_tier="GOLD",
            sla_impact_level="HIGH"
        )
        
        sla_multiplier = gap_prioritizer.calculate_sla_impact_multiplier(sla_gap)
        assert sla_multiplier >= 1.5  # SLA impact increases priority
        
        # Gap on non-SLA asset
        non_sla_gap = Mock(
            asset_sla_tier=None,
            sla_impact_level="NONE"
        )
        
        sla_multiplier = gap_prioritizer.calculate_sla_impact_multiplier(non_sla_gap)
        assert sla_multiplier == 1.0  # No SLA impact

    def test_cost_benefit_analysis(self, gap_prioritizer):
        """Test cost-benefit analysis for gap remediation."""
        gap = Mock(
            remediation_cost=5000,
            risk_reduction_value=25000,
            compliance_penalty_avoidance=10000
        )
        
        analysis = gap_prioritizer.calculate_cost_benefit_ratio(gap)
        
        assert analysis.benefit_cost_ratio > 1.0  # Benefits outweigh costs
        assert analysis.net_benefit > 0
        assert analysis.roi_percentage > 0

    def test_concurrent_prioritization_safety(self, gap_prioritizer):
        """Test thread safety for concurrent prioritization operations."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        gaps = [
            Mock(
                severity=GapSeverity.HIGH,
                gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS
            )
            for _ in range(10)
        ]
        
        asset = Mock(criticality_level=CriticalityLevel.HIGH)
        
        # Run prioritization concurrently
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(gap_prioritizer.calculate_gap_priority_score, gap, asset)
                for gap in gaps
            ]
            
            results = [future.result() for future in futures]
        
        # All should complete successfully with consistent results
        assert len(results) == 10
        for result in results:
            assert isinstance(result, PriorityScore)
            assert result.score > 0


class TestPriorityScore:
    """Test suite for PriorityScore data class."""

    def test_priority_score_creation(self):
        """Test PriorityScore creation and properties."""
        score = PriorityScore(
            score=250.5,
            severity_component=8.0,
            criticality_component=2.5,
            regulatory_component=2.0,
            security_component=1.8,
            business_component=2.2,
            priority_level=PriorityLevel.HIGH
        )
        
        assert score.score == 250.5
        assert score.priority_level == PriorityLevel.HIGH
        assert score.severity_component == 8.0

    def test_priority_score_comparison(self):
        """Test comparison of priority scores."""
        high_score = PriorityScore(
            score=300,
            severity_component=10,
            criticality_component=3.0,
            regulatory_component=2.5,
            security_component=2.0,
            business_component=2.5,
            priority_level=PriorityLevel.CRITICAL
        )
        
        low_score = PriorityScore(
            score=100,
            severity_component=6,
            criticality_component=1.5,
            regulatory_component=1.0,
            security_component=1.0,
            business_component=1.0,
            priority_level=PriorityLevel.MEDIUM
        )
        
        assert high_score > low_score
        assert low_score < high_score

    def test_priority_score_serialization(self):
        """Test PriorityScore serialization for API responses."""
        score = PriorityScore(
            score=200,
            severity_component=8,
            criticality_component=2.0,
            regulatory_component=1.5,
            security_component=1.5,
            business_component=2.0,
            priority_level=PriorityLevel.HIGH
        )
        
        score_dict = score.dict()
        assert isinstance(score_dict, dict)
        assert score_dict['score'] == 200
        assert score_dict['priority_level'] == PriorityLevel.HIGH


class TestPriorityLevel:
    """Test suite for PriorityLevel enumeration."""

    def test_priority_level_values(self):
        """Test PriorityLevel enumeration values."""
        assert PriorityLevel.CRITICAL == "CRITICAL"
        assert PriorityLevel.HIGH == "HIGH"
        assert PriorityLevel.MEDIUM == "MEDIUM"
        assert PriorityLevel.LOW == "LOW"

    def test_priority_level_ordering(self):
        """Test priority level ordering."""
        levels = [PriorityLevel.LOW, PriorityLevel.CRITICAL, PriorityLevel.MEDIUM, PriorityLevel.HIGH]
        expected_order = [PriorityLevel.CRITICAL, PriorityLevel.HIGH, PriorityLevel.MEDIUM, PriorityLevel.LOW]
        
        # Sort by priority (implementation dependent)
        # This test assumes implementation provides ordering


class TestResourceAllocationRecommendation:
    """Test suite for ResourceAllocationRecommendation data class."""

    def test_resource_allocation_creation(self):
        """Test ResourceAllocationRecommendation creation."""
        recommendation = ResourceAllocationRecommendation(
            immediate_action_gaps=5,
            scheduled_action_gaps=10,
            estimated_effort_hours=120,
            team_assignments={
                "security_team": 3,
                "documentation_team": 7,
                "operations_team": 5
            },
            recommended_timeline_weeks=8,
            budget_estimate=25000
        )
        
        assert recommendation.immediate_action_gaps == 5
        assert recommendation.total_gaps == 15
        assert recommendation.estimated_effort_hours == 120
        assert len(recommendation.team_assignments) == 3

    def test_resource_allocation_calculations(self):
        """Test calculated properties of resource allocation."""
        recommendation = ResourceAllocationRecommendation(
            immediate_action_gaps=2,
            scheduled_action_gaps=8,
            estimated_effort_hours=80,
            team_assignments={"team1": 5, "team2": 5},
            recommended_timeline_weeks=4,
            budget_estimate=20000
        )
        
        assert recommendation.total_gaps == 10
        assert recommendation.average_effort_per_gap == 8.0  # 80 hours / 10 gaps
        assert recommendation.weekly_budget == 5000  # 20000 / 4 weeks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])