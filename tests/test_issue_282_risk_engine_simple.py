#!/usr/bin/env python3
"""
Simple test for Issue #282 Risk Engine Implementation (TDD Phase)

Testing only the core components that are currently implemented.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta

# Test only what we've implemented so far
try:
    from violentutf_api.fastapi_app.app.core.risk_engine import (
        NISTRMFRiskEngine,
        LikelihoodCalculator,
        ImpactCalculator,
        RiskLevel,
        RiskFactors,
        RiskAssessmentResult,
        SystemCategorization,
        ControlAssessment,
        ImpactLevel,
    )
    from violentutf_api.fastapi_app.app.models.risk_assessment import (
        DatabaseAsset,
        AssetType,
        SecurityClassification,
        CriticalityLevel,
    )

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    IMPORTS_AVAILABLE = False


class TestCoreComponents:
    """Test the core risk engine components"""

    @pytest.fixture
    def mock_postgresql_asset(self):
        """Create a mock PostgreSQL asset for testing"""
        asset = Mock()
        asset.id = uuid4()
        asset.name = "Test PostgreSQL Database"
        asset.asset_type = "postgresql"
        asset.database_version = "14.9"
        asset.location = "us-east-1"
        asset.security_classification = "confidential"
        asset.criticality_level = "high"
        asset.access_restricted = True
        asset.encryption_enabled = True
        asset.technical_contact = "dba@example.com"
        asset.environment = "production"
        return asset

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_risk_level_enum(self):
        """Test RiskLevel enum values"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.VERY_HIGH.value == "very_high"
        assert RiskLevel.CRITICAL.value == "critical"

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_risk_factors_creation(self):
        """Test RiskFactors dataclass creation"""
        factors = RiskFactors(likelihood=4.2, impact=3.8, exposure=0.7, confidence=0.9)

        assert factors.likelihood == 4.2
        assert factors.impact == 3.8
        assert factors.exposure == 0.7
        assert factors.confidence == 0.9

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_likelihood_calculator_initialization(self):
        """Test LikelihoodCalculator can be initialized"""
        calculator = LikelihoodCalculator()
        assert calculator is not None
        assert calculator.vulnerability_service is None
        assert calculator.threat_intelligence is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_impact_calculator_initialization(self):
        """Test ImpactCalculator can be initialized"""
        calculator = ImpactCalculator()
        assert calculator is not None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_impact_calculator_criticality_mapping(self, mock_postgresql_asset):
        """Test criticality level to impact score mapping"""
        calculator = ImpactCalculator()

        test_cases = [("low", 1.0), ("medium", 2.5), ("high", 4.0), ("critical", 5.0)]

        for criticality, expected_impact in test_cases:
            result = calculator.get_criticality_impact(criticality)
            assert result == expected_impact

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_impact_calculator_sensitivity_mapping(self):
        """Test data sensitivity to impact score mapping"""
        calculator = ImpactCalculator()

        test_cases = [("public", 1.0), ("internal", 2.0), ("confidential", 4.0), ("restricted", 5.0)]

        for classification, expected_impact in test_cases:
            result = calculator.get_sensitivity_impact(classification)
            assert result == expected_impact

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    @pytest.mark.asyncio
    async def test_impact_calculator_calculate_impact(self, mock_postgresql_asset):
        """Test complete impact calculation"""
        calculator = ImpactCalculator()

        result = await calculator.calculate_impact(mock_postgresql_asset)

        assert isinstance(result, (int, float))
        assert 1.0 <= result <= 5.0

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_nist_rmf_engine_initialization(self):
        """Test NIST RMF Risk Engine can be initialized"""
        engine = NISTRMFRiskEngine()
        assert engine is not None
        assert engine.likelihood_calculator is not None
        assert engine.impact_calculator is not None
        assert engine.system_categorizer is not None
        assert engine.nist_controls is not None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_risk_engine_calculate_final_risk_score(self):
        """Test final risk score calculation"""
        engine = NISTRMFRiskEngine()

        # Test various risk factor combinations
        test_cases = [
            # (likelihood, impact, exposure, confidence, expected_range)
            (1.0, 1.0, 0.1, 1.0, (1.0, 3.0)),  # Minimum values
            (5.0, 5.0, 1.0, 1.0, (20.0, 25.0)),  # Maximum values
            (3.0, 4.0, 0.7, 0.9, (7.0, 12.0)),  # Typical values
        ]

        for likelihood, impact, exposure, confidence, expected_range in test_cases:
            factors = RiskFactors(likelihood=likelihood, impact=impact, exposure=exposure, confidence=confidence)

            result = engine.calculate_final_risk_score(factors)

            assert isinstance(result, (int, float))
            assert 1.0 <= result <= 25.0
            assert expected_range[0] <= result <= expected_range[1]

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    def test_risk_engine_get_risk_level_mapping(self):
        """Test risk score to risk level mapping"""
        engine = NISTRMFRiskEngine()

        test_cases = [
            (1.0, RiskLevel.LOW),
            (5.0, RiskLevel.LOW),
            (6.0, RiskLevel.MEDIUM),
            (10.0, RiskLevel.MEDIUM),
            (11.0, RiskLevel.HIGH),
            (15.0, RiskLevel.HIGH),
            (16.0, RiskLevel.VERY_HIGH),
            (20.0, RiskLevel.VERY_HIGH),
            (21.0, RiskLevel.CRITICAL),
            (25.0, RiskLevel.CRITICAL),
        ]

        for risk_score, expected_level in test_cases:
            result = engine.get_risk_level(risk_score)
            assert result == expected_level

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    @pytest.mark.asyncio
    async def test_system_categorizer_basic(self, mock_postgresql_asset):
        """Test system categorization"""
        engine = NISTRMFRiskEngine()

        result = await engine.categorize_information_system(mock_postgresql_asset)

        assert isinstance(result, SystemCategorization)
        assert result.confidentiality_impact in [ImpactLevel.LOW, ImpactLevel.MODERATE, ImpactLevel.HIGH]
        assert result.integrity_impact in [ImpactLevel.LOW, ImpactLevel.MODERATE, ImpactLevel.HIGH]
        assert result.availability_impact in [ImpactLevel.LOW, ImpactLevel.MODERATE, ImpactLevel.HIGH]
        assert result.overall_categorization in [ImpactLevel.LOW, ImpactLevel.MODERATE, ImpactLevel.HIGH]
        assert isinstance(result.data_types, list)
        assert isinstance(result.rationale, str)

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Risk engine modules not available")
    @pytest.mark.asyncio
    async def test_risk_assessment_performance(self, mock_postgresql_asset):
        """Test risk assessment performance requirement (≤ 500ms)"""
        engine = NISTRMFRiskEngine()

        start_time = time.time()
        result = await engine.calculate_risk_score(mock_postgresql_asset)
        end_time = time.time()

        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert isinstance(result, RiskAssessmentResult)
        assert result.risk_score >= 1.0 and result.risk_score <= 25.0
        assert result.risk_level in [
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.VERY_HIGH,
            RiskLevel.CRITICAL,
        ]
        assert execution_time <= 500.0  # Performance requirement: ≤ 500ms


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])
