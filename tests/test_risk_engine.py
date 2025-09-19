#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Comprehensive tests for NIST RMF Risk Engine - Issue #282.

This module provides comprehensive test coverage for the NIST RMF-compliant
risk assessment engine including all 6 steps of the RMF process, risk scoring
calculations, and performance requirements validation.

Test Coverage:
- NIST RMF 6-step process implementation
- Risk score calculation (1-25 scale)
- Risk factor calculations (likelihood, impact, exposure)
- System categorization (CIA impact levels)
- Security control selection and assessment
- Performance requirements (≤500ms per assessment)
- Edge cases and error handling
"""

import asyncio
import os
import pytest
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# Add the FastAPI app to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'violentutf_api', 'fastapi_app'))

from app.core.risk_engine import (
    NISTRMFRiskEngine, LikelihoodCalculator, ImpactCalculator, SystemCategorizer,
    RiskLevel, ImpactLevel, RiskFactors, SystemCategorization, SecurityControl,
    ControlAssessment, RiskAssessmentResult
)
from app.models.risk_assessment import (
    DatabaseAsset, AssetType, SecurityClassification, CriticalityLevel
)


class TestNISTRMFRiskEngine:
    """Test suite for NIST RMF Risk Engine."""
    
    @pytest.fixture
    def mock_database_asset(self):
        """Create mock database asset for testing."""
        return DatabaseAsset(
            id="test-asset-uuid",
            name="Test PostgreSQL Database",
            asset_type=AssetType.POSTGRESQL,
            security_classification=SecurityClassification.CONFIDENTIAL,
            criticality_level=CriticalityLevel.HIGH,
            access_restricted=True,
            encryption_enabled=True,
            technical_contact="admin@example.com",
            environment="production",
            database_version="15.4",
            location="datacenter-1"
        )
    
    @pytest.fixture
    def risk_engine(self):
        """Create risk engine instance with mocked dependencies."""
        vulnerability_service = MagicMock()
        threat_intelligence = MagicMock()
        control_assessor = MagicMock()
        
        return NISTRMFRiskEngine(
            vulnerability_service=vulnerability_service,
            threat_intelligence=threat_intelligence,
            control_assessor=control_assessor
        )
    
    @pytest.fixture
    def mock_control_assessment(self):
        """Create mock control assessment."""
        return ControlAssessment(
            asset_id="test-asset-uuid",
            assessment_date=datetime.utcnow(),
            control_results=[],
            overall_effectiveness=0.75,
            total_controls_assessed=10,
            implemented_controls=7,
            gaps_identified=3
        )


class TestRiskScoreCalculation(TestNISTRMFRiskEngine):
    """Test risk score calculation functionality."""
    
    @pytest.mark.asyncio
    async def test_calculate_risk_score_complete_process(self, risk_engine, mock_database_asset):
        """Test complete NIST RMF risk assessment process."""
        # Mock the 6-step process
        with patch.object(risk_engine, 'categorize_information_system') as mock_categorize, \
             patch.object(risk_engine, 'select_security_controls') as mock_select, \
             patch.object(risk_engine, 'assess_control_implementation') as mock_implement, \
             patch.object(risk_engine, 'assess_control_effectiveness') as mock_assess, \
             patch.object(risk_engine, 'calculate_risk_factors') as mock_factors, \
             patch.object(risk_engine, 'create_monitoring_plan') as mock_monitor:
            
            # Setup mock returns
            mock_categorize.return_value = SystemCategorization(
                confidentiality_impact=ImpactLevel.HIGH,
                integrity_impact=ImpactLevel.HIGH,
                availability_impact=ImpactLevel.MODERATE,
                overall_categorization=ImpactLevel.HIGH,
                data_types=["authentication_data", "business_data"],
                rationale="High impact system with sensitive authentication data"
            )
            
            mock_select.return_value = [
                SecurityControl(
                    id="AC-2", name="Account Management", family=None,
                    priority="P1", baseline="Low", description="Account management",
                    implementation_guidance="Implement automated account management"
                )
            ]
            
            mock_implement.return_value = {
                'implemented_controls': ['AC-2'],
                'partially_implemented_controls': [],
                'not_implemented_controls': []
            }
            
            mock_assess.return_value = ControlAssessment(
                asset_id="test-asset-uuid",
                assessment_date=datetime.utcnow(),
                control_results=[],
                overall_effectiveness=0.80,
                total_controls_assessed=5,
                implemented_controls=4,
                gaps_identified=1
            )
            
            mock_factors.return_value = RiskFactors(
                likelihood=3.5,
                impact=4.0,
                exposure=0.6,
                confidence=0.85
            )
            
            mock_monitor.return_value = MagicMock()
            
            # Execute risk assessment
            result = await risk_engine.calculate_risk_score(mock_database_asset)
            
            # Verify all steps were called
            mock_categorize.assert_called_once()
            mock_select.assert_called_once()
            mock_implement.assert_called_once()
            mock_assess.assert_called_once()
            mock_factors.assert_called_once()
            mock_monitor.assert_called_once()
            
            # Verify result structure
            assert isinstance(result, RiskAssessmentResult)
            assert result.asset_id == "test-asset-uuid"
            assert 1.0 <= result.risk_score <= 25.0
            assert result.risk_level in RiskLevel
            assert result.assessment_timestamp is not None
    
    def test_calculate_final_risk_score_formula(self, risk_engine):
        """Test risk score calculation formula: Likelihood × Impact × Exposure × Confidence."""
        # Test case 1: High risk scenario
        high_risk_factors = RiskFactors(
            likelihood=4.5,  # High likelihood
            impact=4.8,      # High impact
            exposure=0.9,    # High exposure
            confidence=0.95  # High confidence
        )
        
        score = risk_engine.calculate_final_risk_score(high_risk_factors)
        expected = 4.5 * 4.8 * 0.9 * (0.8 + 0.2 * 0.95)  # ~18.4
        
        assert 18.0 <= score <= 19.0  # Allow small rounding differences
        assert score <= 25.0  # Within maximum range
        
        # Test case 2: Low risk scenario
        low_risk_factors = RiskFactors(
            likelihood=1.5,  # Low likelihood
            impact=2.0,      # Low impact
            exposure=0.3,    # Low exposure
            confidence=0.7   # Moderate confidence
        )
        
        score = risk_engine.calculate_final_risk_score(low_risk_factors)
        expected = 1.5 * 2.0 * 0.3 * (0.8 + 0.2 * 0.7)  # ~0.85
        
        assert score >= 1.0  # Minimum risk score
        assert score <= 5.0  # Should be in low range
        
        # Test case 3: Maximum risk scenario
        max_risk_factors = RiskFactors(
            likelihood=5.0,
            impact=5.0,
            exposure=1.0,
            confidence=1.0
        )
        
        score = risk_engine.calculate_final_risk_score(max_risk_factors)
        assert score == 25.0  # Should hit maximum
    
    def test_get_risk_level_mapping(self, risk_engine):
        """Test risk level mapping from numeric scores."""
        assert risk_engine.get_risk_level(3.0) == RiskLevel.LOW
        assert risk_engine.get_risk_level(7.5) == RiskLevel.MEDIUM
        assert risk_engine.get_risk_level(12.0) == RiskLevel.HIGH
        assert risk_engine.get_risk_level(18.0) == RiskLevel.VERY_HIGH
        assert risk_engine.get_risk_level(24.0) == RiskLevel.CRITICAL
        
        # Test boundary conditions
        assert risk_engine.get_risk_level(5.0) == RiskLevel.LOW
        assert risk_engine.get_risk_level(5.1) == RiskLevel.MEDIUM
        assert risk_engine.get_risk_level(10.0) == RiskLevel.MEDIUM
        assert risk_engine.get_risk_level(10.1) == RiskLevel.HIGH
    
    def test_calculate_next_assessment_date(self, risk_engine):
        """Test next assessment date calculation based on risk score."""
        # Critical risk - monthly assessment
        critical_date = risk_engine.calculate_next_assessment_date(22.0)
        expected_critical = datetime.utcnow() + timedelta(days=30)
        assert abs((critical_date - expected_critical).days) <= 1
        
        # High risk - bi-monthly assessment
        high_date = risk_engine.calculate_next_assessment_date(17.0)
        expected_high = datetime.utcnow() + timedelta(days=60)
        assert abs((high_date - expected_high).days) <= 1
        
        # Medium risk - quarterly assessment
        medium_date = risk_engine.calculate_next_assessment_date(8.0)
        expected_medium = datetime.utcnow() + timedelta(days=90)
        assert abs((medium_date - expected_medium).days) <= 1
        
        # Low risk - semi-annual assessment
        low_date = risk_engine.calculate_next_assessment_date(3.0)
        expected_low = datetime.utcnow() + timedelta(days=180)
        assert abs((low_date - expected_low).days) <= 1


class TestPerformanceRequirements(TestNISTRMFRiskEngine):
    """Test performance requirements compliance."""
    
    @pytest.mark.asyncio
    async def test_risk_assessment_performance_requirement(self, risk_engine, mock_database_asset):
        """Test that risk assessment completes within 500ms requirement."""
        # Mock all dependencies to return quickly
        with patch.object(risk_engine, 'categorize_information_system') as mock_categorize, \
             patch.object(risk_engine, 'select_security_controls') as mock_select, \
             patch.object(risk_engine, 'assess_control_implementation') as mock_implement, \
             patch.object(risk_engine, 'assess_control_effectiveness') as mock_assess, \
             patch.object(risk_engine, 'calculate_risk_factors') as mock_factors, \
             patch.object(risk_engine, 'create_monitoring_plan') as mock_monitor:
            
            # Setup fast-returning mocks
            mock_categorize.return_value = SystemCategorization(
                confidentiality_impact=ImpactLevel.MODERATE,
                integrity_impact=ImpactLevel.MODERATE,
                availability_impact=ImpactLevel.MODERATE,
                overall_categorization=ImpactLevel.MODERATE,
                data_types=["test_data"],
                rationale="Test categorization"
            )
            mock_select.return_value = []
            mock_implement.return_value = {}
            mock_assess.return_value = ControlAssessment(
                asset_id="test", assessment_date=datetime.utcnow(),
                control_results=[], overall_effectiveness=0.5,
                total_controls_assessed=0, implemented_controls=0, gaps_identified=0
            )
            mock_factors.return_value = RiskFactors(
                likelihood=3.0, impact=3.0, exposure=0.5, confidence=0.8
            )
            mock_monitor.return_value = MagicMock()
            
            # Measure execution time
            start_time = time.time()
            result = await risk_engine.calculate_risk_score(mock_database_asset)
            duration_ms = (time.time() - start_time) * 1000
            
            # Verify performance requirement
            assert duration_ms <= 500, f"Risk assessment took {duration_ms}ms, exceeding 500ms requirement"
            assert result.assessment_duration_ms is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_assessment_capability(self, risk_engine):
        """Test that engine can handle concurrent assessments."""
        # Create multiple mock assets
        assets = [
            DatabaseAsset(
                id=f"asset-{i}",
                name=f"Test Asset {i}",
                asset_type=AssetType.POSTGRESQL,
                security_classification=SecurityClassification.INTERNAL,
                criticality_level=CriticalityLevel.MEDIUM,
                environment="test"
            )
            for i in range(10)
        ]
        
        # Mock all dependencies for fast execution
        with patch.object(risk_engine, 'categorize_information_system'), \
             patch.object(risk_engine, 'select_security_controls'), \
             patch.object(risk_engine, 'assess_control_implementation'), \
             patch.object(risk_engine, 'assess_control_effectiveness'), \
             patch.object(risk_engine, 'calculate_risk_factors'), \
             patch.object(risk_engine, 'create_monitoring_plan'):
            
            # Setup mock returns
            risk_engine.categorize_information_system.return_value = SystemCategorization(
                confidentiality_impact=ImpactLevel.MODERATE,
                integrity_impact=ImpactLevel.MODERATE,
                availability_impact=ImpactLevel.MODERATE,
                overall_categorization=ImpactLevel.MODERATE,
                data_types=[], rationale="Test"
            )
            risk_engine.select_security_controls.return_value = []
            risk_engine.assess_control_implementation.return_value = {}
            risk_engine.assess_control_effectiveness.return_value = ControlAssessment(
                asset_id="test", assessment_date=datetime.utcnow(),
                control_results=[], overall_effectiveness=0.5,
                total_controls_assessed=0, implemented_controls=0, gaps_identified=0
            )
            risk_engine.calculate_risk_factors.return_value = RiskFactors(
                likelihood=3.0, impact=3.0, exposure=0.5, confidence=0.8
            )
            risk_engine.create_monitoring_plan.return_value = MagicMock()
            
            # Execute concurrent assessments
            start_time = time.time()
            tasks = [risk_engine.calculate_risk_score(asset) for asset in assets]
            results = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time
            
            # Verify all assessments completed
            assert len(results) == 10
            assert all(isinstance(result, RiskAssessmentResult) for result in results)
            
            # Verify concurrent execution was efficient
            # Should be much faster than 10 * 500ms if truly concurrent
            assert total_duration < 2.0, f"Concurrent assessments took {total_duration}s, too slow"


class TestLikelihoodCalculator(TestNISTRMFRiskEngine):
    """Test likelihood calculation component."""
    
    @pytest.fixture
    def likelihood_calculator(self):
        """Create likelihood calculator with mocked services."""
        vulnerability_service = MagicMock()
        threat_intelligence = MagicMock()
        return LikelihoodCalculator(vulnerability_service, threat_intelligence)
    
    @pytest.mark.asyncio
    async def test_calculate_likelihood_components(self, likelihood_calculator, mock_database_asset, mock_control_assessment):
        """Test likelihood calculation with all components."""
        # Mock vulnerability score calculation
        with patch.object(likelihood_calculator, '_calculate_vulnerability_score') as mock_vuln, \
             patch.object(likelihood_calculator, '_calculate_threat_score') as mock_threat, \
             patch.object(likelihood_calculator, '_calculate_exposure_score') as mock_exposure:
            
            mock_vuln.return_value = 3.5  # High vulnerability score
            mock_threat.return_value = 3.0  # Moderate threat score
            mock_exposure.return_value = 2.5  # Low exposure score
            
            likelihood = await likelihood_calculator.calculate_likelihood(mock_database_asset, mock_control_assessment)
            
            # Should average the three components and apply control reduction
            # Base: (3.5 + 3.0 + 2.5) / 3 = 3.0
            # With 75% control effectiveness: 3.0 * (1 - 0.75 * 0.8) = 3.0 * 0.4 = 1.2
            # But minimum is 1.0, so should be adjusted
            assert 1.0 <= likelihood <= 5.0
            assert likelihood < 3.0  # Should be reduced by controls
    
    @pytest.mark.asyncio
    async def test_vulnerability_score_calculation(self, likelihood_calculator, mock_database_asset):
        """Test vulnerability score calculation."""
        # Mock vulnerability service
        mock_vulnerabilities = [
            MagicMock(cvss_score=9.8, exploit_available=True, published_date=datetime.utcnow() - timedelta(days=10)),
            MagicMock(cvss_score=7.5, exploit_available=False, published_date=datetime.utcnow() - timedelta(days=60)),
            MagicMock(cvss_score=5.0, exploit_available=False, published_date=datetime.utcnow() - timedelta(days=200))
        ]
        
        likelihood_calculator.vulnerability_service.get_asset_vulnerabilities = AsyncMock(return_value=mock_vulnerabilities)
        
        score = await likelihood_calculator._calculate_vulnerability_score(mock_database_asset)
        
        # Should be weighted higher due to critical vulnerability with exploit
        assert 3.0 <= score <= 5.0
    
    @pytest.mark.asyncio
    async def test_threat_score_calculation(self, likelihood_calculator, mock_database_asset):
        """Test threat intelligence score calculation."""
        # Mock threat intelligence data
        mock_threat_data = {
            'database_threats': [
                {'likelihood': 4.0, 'type': 'sql_injection'},
                {'likelihood': 3.5, 'type': 'privilege_escalation'}
            ],
            'industry_threats': [
                {'likelihood': 3.0, 'type': 'ransomware'},
                {'likelihood': 2.5, 'type': 'data_breach'}
            ],
            'geographic_threats': [
                {'likelihood': 2.0, 'type': 'state_sponsored'}
            ]
        }
        
        likelihood_calculator.threat_intelligence.get_threat_landscape = AsyncMock(return_value=mock_threat_data)
        
        score = await likelihood_calculator._calculate_threat_score(mock_database_asset)
        
        # Should weight database threats highest
        assert 2.0 <= score <= 5.0
    
    @pytest.mark.asyncio
    async def test_exposure_score_factors(self, likelihood_calculator, mock_database_asset):
        """Test attack surface exposure scoring."""
        score = await likelihood_calculator._calculate_exposure_score(mock_database_asset)
        
        # Should consider multiple exposure factors
        assert 1.0 <= score <= 5.0
        
        # Test with high exposure asset
        high_exposure_asset = mock_database_asset
        high_exposure_asset.location = "public cloud"
        high_exposure_asset.access_restricted = False
        high_exposure_asset.encryption_enabled = False
        high_exposure_asset.criticality_level = CriticalityLevel.CRITICAL
        
        high_score = await likelihood_calculator._calculate_exposure_score(high_exposure_asset)
        assert high_score > score  # Should be higher than original


class TestImpactCalculator(TestNISTRMFRiskEngine):
    """Test impact calculation component."""
    
    @pytest.fixture
    def impact_calculator(self):
        """Create impact calculator."""
        return ImpactCalculator()
    
    @pytest.mark.asyncio
    async def test_calculate_impact_components(self, impact_calculator, mock_database_asset):
        """Test impact calculation with all components."""
        impact = await impact_calculator.calculate_impact(mock_database_asset)
        
        # Should be weighted combination of all impact factors
        assert 1.0 <= impact <= 5.0
        
        # High criticality and confidential classification should result in higher impact
        assert impact >= 3.0  # Should be on higher side
    
    def test_criticality_impact_mapping(self, impact_calculator):
        """Test asset criticality to impact score mapping."""
        assert impact_calculator.get_criticality_impact('low') == 1.0
        assert impact_calculator.get_criticality_impact('medium') == 2.5
        assert impact_calculator.get_criticality_impact('high') == 4.0
        assert impact_calculator.get_criticality_impact('critical') == 5.0
        assert impact_calculator.get_criticality_impact('unknown') == 2.5  # Default
    
    def test_sensitivity_impact_mapping(self, impact_calculator):
        """Test data sensitivity to impact score mapping."""
        assert impact_calculator.get_sensitivity_impact('public') == 1.0
        assert impact_calculator.get_sensitivity_impact('internal') == 2.0
        assert impact_calculator.get_sensitivity_impact('confidential') == 4.0
        assert impact_calculator.get_sensitivity_impact('restricted') == 5.0
    
    @pytest.mark.asyncio
    async def test_operational_impact_calculation(self, impact_calculator, mock_database_asset):
        """Test operational disruption impact calculation."""
        impact = await impact_calculator.calculate_operational_impact(mock_database_asset)
        
        # Production environment should have high operational impact
        assert 3.0 <= impact <= 5.0
        
        # Test with development environment
        dev_asset = mock_database_asset
        dev_asset.environment = "development"
        dev_asset.criticality_level = CriticalityLevel.LOW
        
        dev_impact = await impact_calculator.calculate_operational_impact(dev_asset)
        assert dev_impact < impact  # Should be lower than production
    
    @pytest.mark.asyncio
    async def test_compliance_impact_calculation(self, impact_calculator, mock_database_asset):
        """Test regulatory compliance impact calculation."""
        impact = await impact_calculator.calculate_compliance_impact(mock_database_asset)
        
        # Confidential classification should have high compliance impact
        assert 3.0 <= impact <= 5.0
        
        # Test with public classification
        public_asset = mock_database_asset
        public_asset.security_classification = SecurityClassification.PUBLIC
        
        public_impact = await impact_calculator.calculate_compliance_impact(public_asset)
        assert public_impact < impact  # Should be lower than confidential


class TestSystemCategorizer(TestNISTRMFRiskEngine):
    """Test NIST RMF Step 1 - System Categorization."""
    
    @pytest.fixture
    def system_categorizer(self):
        """Create system categorizer."""
        return SystemCategorizer()
    
    @pytest.mark.asyncio
    async def test_categorize_information_system(self, system_categorizer, mock_database_asset):
        """Test complete system categorization process."""
        categorization = await system_categorizer.categorize_information_system(mock_database_asset)
        
        assert isinstance(categorization, SystemCategorization)
        assert categorization.confidentiality_impact in ImpactLevel
        assert categorization.integrity_impact in ImpactLevel
        assert categorization.availability_impact in ImpactLevel
        assert categorization.overall_categorization in ImpactLevel
        assert isinstance(categorization.data_types, list)
        assert len(categorization.rationale) > 0
    
    def test_data_sensitivity_analysis(self, system_categorizer):
        """Test data sensitivity analysis based on asset metadata."""
        # Test authentication database
        auth_asset = MagicMock()
        auth_asset.name = "User Authentication Database"
        
        data_sensitivity = system_categorizer._analyze_data_sensitivity(auth_asset)
        
        assert 'authentication_data' in data_sensitivity['data_types']
        assert 'high' in data_sensitivity['sensitivity_indicators']
        
        # Test analytics database
        analytics_asset = MagicMock()
        analytics_asset.name = "Analytics Reporting Database"
        
        data_sensitivity = system_categorizer._analyze_data_sensitivity(analytics_asset)
        
        assert 'analytics_data' in data_sensitivity['data_types']
        assert 'medium' in data_sensitivity['sensitivity_indicators']
    
    def test_confidentiality_impact_assessment(self, system_categorizer, mock_database_asset):
        """Test confidentiality impact level assessment."""
        data_sensitivity = {
            'data_types': ['authentication_data', 'personal_data'],
            'sensitivity_indicators': ['high'],
            'classification': 'confidential'
        }
        
        impact = system_categorizer._assess_confidentiality_impact(mock_database_asset, data_sensitivity)
        
        # Confidential classification with sensitive data should be HIGH
        assert impact == ImpactLevel.HIGH
    
    def test_integrity_impact_assessment(self, system_categorizer, mock_database_asset):
        """Test integrity impact level assessment."""
        data_sensitivity = {
            'data_types': ['financial_data', 'authentication_data'],
            'sensitivity_indicators': ['high']
        }
        
        impact = system_categorizer._assess_integrity_impact(mock_database_asset, data_sensitivity)
        
        # Critical data types should result in HIGH integrity impact
        assert impact == ImpactLevel.HIGH
    
    def test_availability_impact_assessment(self, system_categorizer, mock_database_asset):
        """Test availability impact level assessment."""
        data_sensitivity = {'data_types': ['business_data']}
        
        impact = system_categorizer._assess_availability_impact(mock_database_asset, data_sensitivity)
        
        # Production environment with high criticality should be HIGH
        assert impact == ImpactLevel.HIGH


class TestErrorHandling(TestNISTRMFRiskEngine):
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_risk_assessment_with_service_failures(self, risk_engine, mock_database_asset):
        """Test risk assessment continues when external services fail."""
        # Mock vulnerability service failure
        risk_engine.vulnerability_service = None
        
        # Should still complete assessment with default values
        result = await risk_engine.calculate_risk_score(mock_database_asset)
        
        assert isinstance(result, RiskAssessmentResult)
        assert 1.0 <= result.risk_score <= 25.0
    
    @pytest.mark.asyncio
    async def test_invalid_asset_data_handling(self, risk_engine):
        """Test handling of invalid asset data."""
        # Create asset with missing required fields
        invalid_asset = DatabaseAsset(
            id="invalid-asset",
            name="",  # Empty name
            asset_type=None,  # Missing type
            security_classification=None,
            criticality_level=None
        )
        
        # Should handle gracefully and use defaults
        result = await risk_engine.calculate_risk_score(invalid_asset)
        
        assert isinstance(result, RiskAssessmentResult)
        assert result.risk_score >= 1.0
    
    def test_confidence_calculation_edge_cases(self, risk_engine):
        """Test confidence calculation with incomplete data."""
        # Asset with minimal data
        minimal_asset = DatabaseAsset(
            id="minimal",
            name="Minimal Asset",
            asset_type=AssetType.SQLITE,
            security_classification=SecurityClassification.INTERNAL,
            criticality_level=CriticalityLevel.LOW
        )
        
        minimal_control_assessment = ControlAssessment(
            asset_id="minimal",
            assessment_date=datetime.utcnow(),
            control_results=[],
            overall_effectiveness=0.0,
            total_controls_assessed=0,
            implemented_controls=0,
            gaps_identified=0
        )
        
        confidence = risk_engine._calculate_confidence(minimal_asset, minimal_control_assessment)
        
        # Should still provide reasonable confidence estimate
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.8  # Should be lower due to minimal data


# Test fixtures for async testing
@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Performance test markers
pytestmark = [
    pytest.mark.risk_engine,
    pytest.mark.nist_rmf,
    pytest.mark.performance,
    pytest.mark.issue_282
]


if __name__ == "__main__":
    # Run tests with coverage reporting
    pytest.main([
        __file__,
        "-v", 
        "--cov=violentutf_api.fastapi_app.app.core.risk_engine",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-min=92"  # 92% minimum coverage requirement
    ])