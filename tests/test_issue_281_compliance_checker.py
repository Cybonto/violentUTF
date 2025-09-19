"""
Test suite for Issue #281: Gap Identification Algorithms - Compliance Checker

This module tests the compliance gap assessment engines that validate
against GDPR, SOC2, and NIST frameworks with 95% accuracy targets.

Test Coverage:
- GDPR compliance assessment (95% accuracy target)
- SOC2 compliance validation (95% accuracy target)
- NIST framework alignment (95% accuracy target)
- Policy violation detection
- Compliance scoring and reporting
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.models.gap_analysis import ComplianceGap, GapSeverity, GapType, PolicyGap

# Import the classes we'll be testing (will be implemented)
from app.services.asset_management.compliance_checker import (
    ComplianceFramework,
    ComplianceGapChecker,
    GDPRComplianceChecker,
    NISTComplianceChecker,
    PolicyAssessment,
    PolicyViolation,
    SecurityPolicyChecker,
    SOC2ComplianceChecker,
)


class TestComplianceGapChecker:
    """Test suite for the main ComplianceGapChecker orchestrator."""

    @pytest.fixture
    def mock_gdpr_checker(self):
        """Mock GDPR compliance checker."""
        checker = AsyncMock()
        checker.assess_gaps.return_value = [
            ComplianceGap(
                asset_id="asset_001",
                framework=ComplianceFramework.GDPR,
                requirement="Article 32 - Security of processing",
                gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
                severity=GapSeverity.HIGH,
                description="Missing encryption at rest",
                recommendations=["Enable database encryption"]
            )
        ]
        return checker

    @pytest.fixture
    def mock_soc2_checker(self):
        """Mock SOC2 compliance checker."""
        checker = AsyncMock()
        checker.assess_gaps.return_value = [
            ComplianceGap(
                asset_id="asset_001",
                framework=ComplianceFramework.SOC2,
                requirement="CC6.1 - Logical Access Controls",
                gap_type=GapType.INSUFFICIENT_ACCESS_CONTROLS,
                severity=GapSeverity.HIGH,
                description="No access restrictions implemented",
                recommendations=["Implement role-based access controls"]
            )
        ]
        return checker

    @pytest.fixture
    def mock_nist_checker(self):
        """Mock NIST compliance checker."""
        checker = AsyncMock()
        checker.assess_gaps.return_value = [
            ComplianceGap(
                asset_id="asset_001",
                framework=ComplianceFramework.NIST,
                requirement="PR.DS-1 - Data-at-rest protection",
                gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
                severity=GapSeverity.MEDIUM,
                description="Encryption at rest not configured",
                recommendations=["Configure data encryption"]
            )
        ]
        return checker

    @pytest.fixture
    def compliance_checker(self, mock_gdpr_checker, mock_soc2_checker, mock_nist_checker):
        """Create ComplianceGapChecker with mocked sub-checkers."""
        checker = ComplianceGapChecker(Mock())
        checker.gdpr_checker = mock_gdpr_checker
        checker.soc2_checker = mock_soc2_checker
        checker.nist_checker = mock_nist_checker
        return checker

    @pytest.fixture
    def test_asset(self):
        """Sample asset for testing."""
        return DatabaseAsset(
            id="asset_001",
            name="production_db",
            asset_type=AssetType.POSTGRESQL,
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.CRITICAL,
            security_classification=SecurityClassification.CONFIDENTIAL,
            encryption_enabled=False,
            access_restricted=False,
            backup_configured=False
        )

    async def test_compliance_checker_initialization(self, compliance_checker):
        """Test ComplianceGapChecker initialization."""
        assert compliance_checker is not None
        assert compliance_checker.gdpr_checker is not None
        assert compliance_checker.soc2_checker is not None
        assert compliance_checker.nist_checker is not None

    async def test_assess_all_compliance_gaps(self, compliance_checker, test_asset):
        """Test assessment of all compliance frameworks for an asset."""
        gaps = await compliance_checker.assess_compliance_gaps(test_asset)
        
        # Should assess all applicable frameworks
        assert len(gaps) == 3  # GDPR + SOC2 + NIST
        
        frameworks = {gap.framework for gap in gaps}
        assert ComplianceFramework.GDPR in frameworks
        assert ComplianceFramework.SOC2 in frameworks
        assert ComplianceFramework.NIST in frameworks

    async def test_gdpr_applicability_detection(self, compliance_checker):
        """Test detection of GDPR applicability."""
        # Asset with personal data should trigger GDPR
        personal_data_asset = Mock(
            security_classification=SecurityClassification.CONFIDENTIAL,
            purpose_description="stores user personal information",
            name="user_profiles_db"
        )
        
        assert compliance_checker.is_gdpr_applicable(personal_data_asset) is True
        
        # Asset without personal data should not trigger GDPR
        system_asset = Mock(
            security_classification=SecurityClassification.INTERNAL,
            purpose_description="system configuration data",
            name="config_db"
        )
        
        assert compliance_checker.is_gdpr_applicable(system_asset) is False

    async def test_soc2_applicability_detection(self, compliance_checker):
        """Test detection of SOC2 applicability."""
        # Production asset should trigger SOC2
        prod_asset = Mock(environment=Environment.PRODUCTION)
        assert compliance_checker.is_soc2_applicable(prod_asset) is True
        
        # Development asset may not trigger SOC2
        dev_asset = Mock(environment=Environment.DEVELOPMENT)
        # Implementation may vary - could be True or False based on policy

    async def test_nist_applicability_detection(self, compliance_checker):
        """Test detection of NIST framework applicability."""
        # Critical asset should trigger NIST
        critical_asset = Mock(criticality_level=CriticalityLevel.CRITICAL)
        assert compliance_checker.is_nist_applicable(critical_asset) is True
        
        # Low criticality asset may not trigger NIST
        low_asset = Mock(criticality_level=CriticalityLevel.LOW)
        # Implementation may vary


class TestGDPRComplianceChecker:
    """Test suite for GDPR compliance assessment (95% accuracy target)."""

    @pytest.fixture
    def gdpr_checker(self):
        """Create GDPRComplianceChecker instance."""
        return GDPRComplianceChecker()

    @pytest.fixture
    def personal_data_asset(self):
        """Asset containing personal data."""
        return DatabaseAsset(
            id="personal_db",
            name="user_data",
            security_classification=SecurityClassification.RESTRICTED,
            encryption_enabled=False,
            compliance_requirements={}
        )

    async def test_dpia_requirement_assessment(self, gdpr_checker, personal_data_asset):
        """Test Data Protection Impact Assessment requirement."""
        # Mock missing DPIA documentation
        with patch.object(gdpr_checker, 'find_dpia_documentation') as mock_find:
            mock_find.return_value = None
            
            gaps = await gdpr_checker.assess_gaps(personal_data_asset)
            
            # Should find missing DPIA gap
            dpia_gaps = [gap for gap in gaps if "DPIA" in gap.requirement]
            assert len(dpia_gaps) >= 1
            
            dpia_gap = dpia_gaps[0]
            assert dpia_gap.severity == GapSeverity.HIGH
            assert "article 35" in dpia_gap.requirement.lower()

    async def test_data_retention_policy_assessment(self, gdpr_checker, personal_data_asset):
        """Test data retention policy requirement."""
        # Asset without retention policy
        personal_data_asset.compliance_requirements = {}
        
        gaps = await gdpr_checker.assess_gaps(personal_data_asset)
        
        # Should find missing retention policy gap
        retention_gaps = [gap for gap in gaps if gap.gap_type == GapType.MISSING_RETENTION_POLICY]
        assert len(retention_gaps) >= 1
        
        retention_gap = retention_gaps[0]
        assert retention_gap.severity == GapSeverity.MEDIUM
        assert "storage limitation" in retention_gap.requirement.lower()

    async def test_encryption_requirement_assessment(self, gdpr_checker, personal_data_asset):
        """Test encryption requirement for personal data."""
        # Asset without encryption
        gaps = await gdpr_checker.assess_gaps(personal_data_asset)
        
        # Should find insufficient security controls gap
        encryption_gaps = [gap for gap in gaps if gap.gap_type == GapType.INSUFFICIENT_SECURITY_CONTROLS]
        assert len(encryption_gaps) >= 1
        
        encryption_gap = encryption_gaps[0]
        assert encryption_gap.severity == GapSeverity.HIGH
        assert "article 32" in encryption_gap.requirement.lower()
        assert "encryption" in encryption_gap.description.lower()

    async def test_data_subject_rights_assessment(self, gdpr_checker, personal_data_asset):
        """Test data subject rights implementation."""
        # Mock missing data subject rights implementation
        with patch.object(gdpr_checker, 'check_data_subject_rights') as mock_check:
            mock_check.return_value = Mock(
                access_right_implemented=False,
                rectification_right_implemented=True,
                erasure_right_implemented=False,
                portability_right_implemented=False
            )
            
            gaps = await gdpr_checker.assess_gaps(personal_data_asset)
            
            # Should find missing data subject rights gaps
            rights_gaps = [gap for gap in gaps if gap.gap_type == GapType.MISSING_DATA_SUBJECT_RIGHTS]
            assert len(rights_gaps) >= 1
            
            rights_gap = rights_gaps[0]
            assert rights_gap.severity == GapSeverity.MEDIUM
            assert "article 15" in rights_gap.requirement.lower()

    async def test_gdpr_compliance_accuracy(self, gdpr_checker):
        """Test GDPR compliance detection accuracy (target: 95%)."""
        # Test dataset with known compliance scenarios
        test_scenarios = [
            # Compliant scenario
            {
                "asset": Mock(
                    security_classification=SecurityClassification.CONFIDENTIAL,
                    encryption_enabled=True,
                    compliance_requirements={"data_retention_period": 365},
                    dpia_completed=True,
                    data_subject_rights=True
                ),
                "expected_compliant": True,
                "expected_gaps": 0
            },
            # Non-compliant scenario
            {
                "asset": Mock(
                    security_classification=SecurityClassification.RESTRICTED,
                    encryption_enabled=False,
                    compliance_requirements={},
                    dpia_completed=False,
                    data_subject_rights=False
                ),
                "expected_compliant": False,
                "expected_gaps": 4  # Missing: DPIA, retention, encryption, rights
            }
        ]
        
        correct_assessments = 0
        total_assessments = len(test_scenarios)
        
        for scenario in test_scenarios:
            # Mock supporting methods
            with patch.object(gdpr_checker, 'find_dpia_documentation') as mock_dpia, \
                 patch.object(gdpr_checker, 'check_data_subject_rights') as mock_rights:
                
                mock_dpia.return_value = Mock() if scenario["asset"].dpia_completed else None
                mock_rights.return_value = Mock(
                    access_right_implemented=scenario["asset"].data_subject_rights
                )
                
                gaps = await gdpr_checker.assess_gaps(scenario["asset"])
                
                # Check if assessment is correct
                is_compliant = len(gaps) == 0
                if is_compliant == scenario["expected_compliant"]:
                    correct_assessments += 1
        
        # Calculate accuracy
        accuracy = correct_assessments / total_assessments
        assert accuracy >= 0.95  # 95% accuracy target


class TestSOC2ComplianceChecker:
    """Test suite for SOC2 compliance assessment (95% accuracy target)."""

    @pytest.fixture
    def soc2_checker(self):
        """Create SOC2ComplianceChecker instance."""
        return SOC2ComplianceChecker()

    @pytest.fixture
    def production_asset(self):
        """Production asset for SOC2 testing."""
        return DatabaseAsset(
            id="prod_db",
            name="production_database",
            environment=Environment.PRODUCTION,
            access_restricted=False,
            backup_configured=False,
            monitoring_enabled=False
        )

    async def test_logical_access_controls_assessment(self, soc2_checker, production_asset):
        """Test CC6.1 - Logical Access Controls assessment."""
        gaps = await soc2_checker.assess_gaps(production_asset)
        
        # Should find insufficient access controls gap
        access_gaps = [gap for gap in gaps if gap.gap_type == GapType.INSUFFICIENT_ACCESS_CONTROLS]
        assert len(access_gaps) >= 1
        
        access_gap = access_gaps[0]
        assert access_gap.severity == GapSeverity.HIGH
        assert "cc6.1" in access_gap.requirement.lower()

    async def test_backup_recovery_assessment(self, soc2_checker, production_asset):
        """Test CC6.7 - System Backup and Recovery assessment."""
        gaps = await soc2_checker.assess_gaps(production_asset)
        
        # Should find missing backup procedures gap
        backup_gaps = [gap for gap in gaps if gap.gap_type == GapType.MISSING_BACKUP_PROCEDURES]
        assert len(backup_gaps) >= 1
        
        backup_gap = backup_gaps[0]
        assert backup_gap.severity == GapSeverity.HIGH
        assert "cc6.7" in backup_gap.requirement.lower()

    async def test_monitoring_controls_assessment(self, soc2_checker, production_asset):
        """Test CC7.2 - Monitoring Activities assessment."""
        # Mock monitoring controls check
        with patch.object(soc2_checker, 'check_monitoring_controls') as mock_check:
            mock_check.return_value = [
                ComplianceGap(
                    asset_id=production_asset.id,
                    framework=ComplianceFramework.SOC2,
                    requirement="CC7.2 - Monitoring Activities",
                    gap_type=GapType.INSUFFICIENT_MONITORING,
                    severity=GapSeverity.MEDIUM,
                    description="No monitoring configured",
                    recommendations=["Configure monitoring"]
                )
            ]
            
            gaps = await soc2_checker.assess_gaps(production_asset)
            
            # Should include monitoring gaps
            monitoring_gaps = [gap for gap in gaps if "monitoring" in gap.requirement.lower()]
            assert len(monitoring_gaps) >= 1

    async def test_soc2_compliance_accuracy(self, soc2_checker):
        """Test SOC2 compliance detection accuracy (target: 95%)."""
        test_scenarios = [
            # Compliant scenario
            {
                "asset": Mock(
                    access_restricted=True,
                    backup_configured=True,
                    monitoring_enabled=True,
                    audit_logging=True
                ),
                "expected_compliant": True
            },
            # Non-compliant scenario
            {
                "asset": Mock(
                    access_restricted=False,
                    backup_configured=False,
                    monitoring_enabled=False,
                    audit_logging=False
                ),
                "expected_compliant": False
            }
        ]
        
        correct_assessments = 0
        
        for scenario in test_scenarios:
            with patch.object(soc2_checker, 'check_monitoring_controls') as mock_monitor:
                mock_monitor.return_value = [] if scenario["asset"].monitoring_enabled else [Mock()]
                
                gaps = await soc2_checker.assess_gaps(scenario["asset"])
                
                is_compliant = len(gaps) == 0
                if is_compliant == scenario["expected_compliant"]:
                    correct_assessments += 1
        
        accuracy = correct_assessments / len(test_scenarios)
        assert accuracy >= 0.95


class TestNISTComplianceChecker:
    """Test suite for NIST framework compliance assessment (95% accuracy target)."""

    @pytest.fixture
    def nist_checker(self):
        """Create NISTComplianceChecker instance."""
        return NISTComplianceChecker()

    @pytest.fixture
    def critical_asset(self):
        """Critical asset for NIST testing."""
        return DatabaseAsset(
            id="critical_db",
            name="critical_database",
            criticality_level=CriticalityLevel.CRITICAL,
            encryption_enabled=False,
            access_controls_implemented=False,
            incident_response_plan=False
        )

    async def test_data_protection_assessment(self, nist_checker, critical_asset):
        """Test PR.DS-1 - Data-at-rest protection assessment."""
        gaps = await nist_checker.assess_gaps(critical_asset)
        
        # Should find data protection gaps
        protection_gaps = [gap for gap in gaps if "pr.ds-1" in gap.requirement.lower()]
        assert len(protection_gaps) >= 1
        
        protection_gap = protection_gaps[0]
        assert protection_gap.severity in [GapSeverity.MEDIUM, GapSeverity.HIGH]

    async def test_access_control_assessment(self, nist_checker, critical_asset):
        """Test PR.AC-1 - Access Control assessment."""
        gaps = await nist_checker.assess_gaps(critical_asset)
        
        # Should find access control gaps
        access_gaps = [gap for gap in gaps if "pr.ac" in gap.requirement.lower()]
        assert len(access_gaps) >= 1

    async def test_incident_response_assessment(self, nist_checker, critical_asset):
        """Test RS.RP-1 - Response Planning assessment."""
        gaps = await nist_checker.assess_gaps(critical_asset)
        
        # Should find incident response gaps
        response_gaps = [gap for gap in gaps if "rs.rp" in gap.requirement.lower()]
        assert len(response_gaps) >= 1

    async def test_nist_compliance_accuracy(self, nist_checker):
        """Test NIST compliance detection accuracy (target: 95%)."""
        test_scenarios = [
            # Compliant scenario
            {
                "asset": Mock(
                    encryption_enabled=True,
                    access_controls_implemented=True,
                    incident_response_plan=True,
                    monitoring_configured=True
                ),
                "expected_compliant": True
            },
            # Non-compliant scenario  
            {
                "asset": Mock(
                    encryption_enabled=False,
                    access_controls_implemented=False,
                    incident_response_plan=False,
                    monitoring_configured=False
                ),
                "expected_compliant": False
            }
        ]
        
        correct_assessments = 0
        
        for scenario in test_scenarios:
            gaps = await nist_checker.assess_gaps(scenario["asset"])
            
            is_compliant = len(gaps) == 0
            if is_compliant == scenario["expected_compliant"]:
                correct_assessments += 1
        
        accuracy = correct_assessments / len(test_scenarios)
        assert accuracy >= 0.95


class TestSecurityPolicyChecker:
    """Test suite for organizational security policy compliance."""

    @pytest.fixture
    def policy_engine(self):
        """Mock security policy engine."""
        engine = Mock()
        engine.get_applicable_policies.return_value = [
            Mock(
                id="POL001",
                name="Database Encryption Policy",
                rules=[
                    Mock(
                        id="RULE001",
                        description="All production databases must be encrypted",
                        expected_value=True,
                        impact_level="HIGH"
                    )
                ]
            )
        ]
        return engine

    @pytest.fixture
    def policy_checker(self, policy_engine):
        """Create SecurityPolicyChecker instance."""
        return SecurityPolicyChecker(policy_engine)

    async def test_policy_gap_assessment(self, policy_checker):
        """Test assessment of policy compliance gaps."""
        # Asset violating encryption policy
        asset = Mock(
            id="test_asset",
            encryption_enabled=False,
            environment=Environment.PRODUCTION
        )
        
        # Mock policy evaluation
        with patch.object(policy_checker, 'evaluate_policy_rule') as mock_eval, \
             patch.object(policy_checker, 'get_asset_value_for_rule') as mock_value:
            
            mock_eval.return_value = False  # Policy violated
            mock_value.return_value = False  # Asset not encrypted
            
            gaps = await policy_checker.assess_policy_gaps(asset)
            
            # Should find policy violation
            assert len(gaps) >= 1
            
            policy_gap = gaps[0]
            assert policy_gap.gap_type == GapType.POLICY_VIOLATION
            assert policy_gap.policy_name == "Database Encryption Policy"

    async def test_policy_assessment_with_violations(self, policy_checker):
        """Test policy assessment with specific violations."""
        asset = Mock(encryption_enabled=False)
        policy = Mock(
            id="POL001",
            name="Test Policy",
            rules=[
                Mock(
                    id="RULE001",
                    description="Encryption required",
                    expected_value=True,
                    impact_level="HIGH"
                )
            ]
        )
        
        # Mock rule evaluation to fail
        with patch.object(policy_checker, 'evaluate_policy_rule') as mock_eval, \
             patch.object(policy_checker, 'get_asset_value_for_rule') as mock_value:
            
            mock_eval.return_value = False
            mock_value.return_value = False
            
            assessment = await policy_checker.assess_asset_against_policy(asset, policy)
            
            assert assessment.compliant is False
            assert len(assessment.violations) == 1
            assert assessment.violations[0].rule_id == "RULE001"

    async def test_policy_gap_severity_calculation(self, policy_checker):
        """Test calculation of policy gap severity."""
        policy = Mock(impact_level="HIGH")
        assessment = Mock(
            violations=[
                Mock(impact="HIGH"),
                Mock(impact="MEDIUM")
            ]
        )
        
        severity = policy_checker.calculate_policy_gap_severity(policy, assessment)
        
        # High impact violations should result in high severity
        assert severity == GapSeverity.HIGH

    async def test_policy_recommendation_generation(self, policy_checker):
        """Test generation of policy compliance recommendations."""
        violations = [
            PolicyViolation(
                rule_id="RULE001",
                rule_description="Encryption required",
                actual_value=False,
                expected_value=True,
                impact="HIGH"
            )
        ]
        
        recommendations = policy_checker.generate_policy_recommendations(violations)
        
        assert len(recommendations) > 0
        assert any("encryption" in rec.lower() for rec in recommendations)


class TestComplianceFramework:
    """Test suite for ComplianceFramework enumeration."""

    def test_compliance_framework_values(self):
        """Test ComplianceFramework enumeration values."""
        assert ComplianceFramework.GDPR == "GDPR"
        assert ComplianceFramework.SOC2 == "SOC2"
        assert ComplianceFramework.NIST == "NIST"

    def test_compliance_framework_iteration(self):
        """Test iteration over compliance frameworks."""
        frameworks = list(ComplianceFramework)
        assert len(frameworks) >= 3
        assert ComplianceFramework.GDPR in frameworks


class TestPolicyAssessment:
    """Test suite for PolicyAssessment data class."""

    def test_policy_assessment_creation(self):
        """Test PolicyAssessment creation and properties."""
        violations = [
            PolicyViolation(
                rule_id="RULE001",
                rule_description="Test rule",
                actual_value="actual",
                expected_value="expected",
                impact="HIGH"
            )
        ]
        
        assessment = PolicyAssessment(
            compliant=False,
            violations=violations,
            recommendations=["Fix the violation"]
        )
        
        assert assessment.compliant is False
        assert len(assessment.violations) == 1
        assert len(assessment.recommendations) == 1

    def test_policy_assessment_compliant_scenario(self):
        """Test PolicyAssessment for compliant scenario."""
        assessment = PolicyAssessment(
            compliant=True,
            violations=[],
            recommendations=[]
        )
        
        assert assessment.compliant is True
        assert len(assessment.violations) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])