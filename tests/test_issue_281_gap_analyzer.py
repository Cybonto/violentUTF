"""
Test suite for Issue #281: Gap Identification Algorithms - Core Gap Analyzer

This module tests the central gap analysis orchestrator that coordinates
all gap detection algorithms and aggregates results.

Test Coverage:
- Gap analysis initialization and configuration
- Multi-algorithm execution coordination
- Result aggregation and deduplication
- Error handling and recovery
- Performance profiling and optimization
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.models.asset_inventory import AssetType, DatabaseAsset, Environment
from app.models.gap_analysis import (
    ComplianceGap,
    DocumentationGap,
    Gap,
    GapSeverity,
    GapType,
    OrphanedAssetGap,
    PriorityLevel,
)

# Import the classes we'll be testing (will be implemented)
from app.services.asset_management.gap_analyzer import (
    GapAnalysisConfig,
    GapAnalysisError,
    GapAnalysisResult,
    GapAnalyzer,
)


class TestGapAnalyzer:
    """Test suite for the central GapAnalyzer orchestrator."""

    @pytest.fixture
    def mock_asset_service(self):
        """Mock asset service for testing."""
        service = AsyncMock()
        service.get_all_assets.return_value = [
            DatabaseAsset(
                id="asset_001",
                name="production_db",
                asset_type=AssetType.POSTGRESQL,
                environment=Environment.PRODUCTION,
                criticality_level="critical",
                owner_team="data_team",
                technical_contact="admin@company.com"
            ),
            DatabaseAsset(
                id="asset_002", 
                name="orphaned_db",
                asset_type=AssetType.SQLITE,
                environment=Environment.DEVELOPMENT,
                criticality_level="low",
                owner_team=None,  # Orphaned
                technical_contact=None
            )
        ]
        return service

    @pytest.fixture
    def mock_orphaned_detector(self):
        """Mock orphaned resource detector."""
        detector = AsyncMock()
        detector.detect_orphaned_assets.return_value = [
            OrphanedAssetGap(
                asset_id="asset_002",
                gap_type=GapType.MISSING_DOCUMENTATION,
                severity=GapSeverity.MEDIUM,
                description="Asset lacks proper documentation",
                recommendations=["Create documentation", "Assign owner"]
            )
        ]
        return detector

    @pytest.fixture
    def mock_documentation_analyzer(self):
        """Mock documentation analyzer."""
        analyzer = AsyncMock()
        analyzer.analyze_documentation_gaps.return_value = [
            DocumentationGap(
                asset_id="asset_001",
                gap_type=GapType.OUTDATED_DOCUMENTATION,
                documentation_type="technical_specs",
                severity=GapSeverity.LOW,
                description="Documentation is 120 days old",
                recommendations=["Update documentation"]
            )
        ]
        return analyzer

    @pytest.fixture
    def mock_compliance_checker(self):
        """Mock compliance checker."""
        checker = AsyncMock()
        checker.assess_compliance_gaps.return_value = [
            ComplianceGap(
                asset_id="asset_001",
                framework="GDPR",
                requirement="Article 32 - Security of processing",
                gap_type=GapType.INSUFFICIENT_SECURITY_CONTROLS,
                severity=GapSeverity.HIGH,
                description="Missing encryption at rest",
                recommendations=["Enable database encryption"]
            )
        ]
        return checker

    @pytest.fixture
    def mock_gap_prioritizer(self):
        """Mock gap prioritizer."""
        prioritizer = Mock()
        prioritizer.calculate_gap_priority_score.return_value = Mock(
            score=75.5,
            priority_level=PriorityLevel.HIGH
        )
        return prioritizer

    @pytest.fixture
    def gap_analyzer(self, mock_asset_service, mock_orphaned_detector, 
                    mock_documentation_analyzer, mock_compliance_checker, 
                    mock_gap_prioritizer):
        """Create GapAnalyzer instance with mocked dependencies."""
        return GapAnalyzer(
            asset_service=mock_asset_service,
            orphaned_detector=mock_orphaned_detector,
            documentation_analyzer=mock_documentation_analyzer,
            compliance_checker=mock_compliance_checker,
            gap_prioritizer=mock_gap_prioritizer
        )

    @pytest.fixture
    def analysis_config(self):
        """Default gap analysis configuration."""
        return GapAnalysisConfig(
            include_orphaned_detection=True,
            include_documentation_analysis=True,
            include_compliance_assessment=True,
            compliance_frameworks=["GDPR", "SOC2", "NIST"],
            max_execution_time_seconds=180,
            max_memory_usage_mb=256
        )

    async def test_gap_analyzer_initialization(self, gap_analyzer):
        """Test GapAnalyzer initialization with all dependencies."""
        assert gap_analyzer is not None
        assert gap_analyzer.asset_service is not None
        assert gap_analyzer.orphaned_detector is not None
        assert gap_analyzer.documentation_analyzer is not None
        assert gap_analyzer.compliance_checker is not None
        assert gap_analyzer.gap_prioritizer is not None

    async def test_full_gap_analysis_execution(self, gap_analyzer, analysis_config):
        """Test complete gap analysis execution flow."""
        # Execute gap analysis
        result = await gap_analyzer.analyze_gaps(analysis_config)
        
        # Verify result structure
        assert isinstance(result, GapAnalysisResult)
        assert result.analysis_id is not None
        assert result.execution_time_seconds > 0
        assert result.total_gaps_found >= 0
        assert isinstance(result.gaps_by_type, dict)
        assert isinstance(result.gaps_by_severity, dict)
        
        # Verify all detectors were called
        gap_analyzer.orphaned_detector.detect_orphaned_assets.assert_called_once()
        gap_analyzer.documentation_analyzer.analyze_documentation_gaps.assert_called()
        gap_analyzer.compliance_checker.assess_compliance_gaps.assert_called()

    async def test_gap_result_aggregation(self, gap_analyzer, analysis_config):
        """Test proper aggregation of gaps from multiple detectors."""
        result = await gap_analyzer.analyze_gaps(analysis_config)
        
        # Should have gaps from all three detectors
        assert result.total_gaps_found == 3  # 1 orphaned + 1 documentation + 1 compliance
        
        # Verify gap categorization
        assert GapType.MISSING_DOCUMENTATION in result.gaps_by_type
        assert GapType.OUTDATED_DOCUMENTATION in result.gaps_by_type
        assert GapType.INSUFFICIENT_SECURITY_CONTROLS in result.gaps_by_type
        
        # Verify severity distribution
        assert GapSeverity.HIGH in result.gaps_by_severity
        assert GapSeverity.MEDIUM in result.gaps_by_severity
        assert GapSeverity.LOW in result.gaps_by_severity

    async def test_gap_deduplication(self, gap_analyzer, analysis_config):
        """Test deduplication of identical gaps from different detectors."""
        # Configure detectors to return duplicate gaps
        duplicate_gap = OrphanedAssetGap(
            asset_id="asset_001",
            gap_type=GapType.MISSING_DOCUMENTATION,
            severity=GapSeverity.MEDIUM,
            description="Duplicate gap",
            recommendations=["Fix duplicate"]
        )
        
        gap_analyzer.orphaned_detector.detect_orphaned_assets.return_value = [duplicate_gap]
        gap_analyzer.documentation_analyzer.analyze_documentation_gaps.return_value = [duplicate_gap]
        
        result = await gap_analyzer.analyze_gaps(analysis_config)
        
        # Should deduplicate identical gaps
        assert result.total_gaps_found == 2  # 1 unique gap + 1 compliance gap

    async def test_performance_monitoring(self, gap_analyzer, analysis_config):
        """Test performance monitoring during gap analysis."""
        result = await gap_analyzer.analyze_gaps(analysis_config)
        
        # Verify performance metrics are captured
        assert result.execution_time_seconds < 180  # Must meet requirement
        assert result.memory_usage_mb < 256  # Must meet requirement
        assert result.assets_analyzed > 0
        
        # Verify performance breakdown
        assert hasattr(result, 'performance_breakdown')
        assert 'orphaned_detection_time' in result.performance_breakdown
        assert 'documentation_analysis_time' in result.performance_breakdown
        assert 'compliance_assessment_time' in result.performance_breakdown

    async def test_selective_analysis_configuration(self, gap_analyzer):
        """Test selective enabling/disabling of analysis components."""
        # Test with only orphaned detection enabled
        config = GapAnalysisConfig(
            include_orphaned_detection=True,
            include_documentation_analysis=False,
            include_compliance_assessment=False
        )
        
        result = await gap_analyzer.analyze_gaps(config)
        
        # Verify only orphaned detection was executed
        gap_analyzer.orphaned_detector.detect_orphaned_assets.assert_called_once()
        gap_analyzer.documentation_analyzer.analyze_documentation_gaps.assert_not_called()
        gap_analyzer.compliance_checker.assess_compliance_gaps.assert_not_called()
        
        # Should only have orphaned gaps
        assert all(gap.gap_type in [GapType.MISSING_DOCUMENTATION, GapType.UNCLEAR_OWNERSHIP, 
                                  GapType.UNREFERENCED_ASSET] for gap in result.all_gaps)

    async def test_error_handling_detector_failure(self, gap_analyzer, analysis_config):
        """Test error handling when individual detectors fail."""
        # Configure orphaned detector to raise exception
        gap_analyzer.orphaned_detector.detect_orphaned_assets.side_effect = Exception("Detector failed")
        
        # Analysis should continue with other detectors
        result = await gap_analyzer.analyze_gaps(analysis_config)
        
        # Should still have gaps from other detectors
        assert result.total_gaps_found == 2  # Documentation + compliance gaps
        
        # Should log the error
        assert len(result.errors) == 1
        assert "Detector failed" in result.errors[0]

    async def test_timeout_handling(self, gap_analyzer):
        """Test timeout handling for long-running analysis."""
        # Configure very short timeout
        config = GapAnalysisConfig(
            max_execution_time_seconds=0.001  # 1ms timeout
        )
        
        # Configure detector with long delay
        async def slow_detection(*args):
            await asyncio.sleep(1)  # 1 second delay
            return []
        
        gap_analyzer.orphaned_detector.detect_orphaned_assets = slow_detection
        
        # Should raise timeout error
        with pytest.raises(GapAnalysisError) as exc_info:
            await gap_analyzer.analyze_gaps(config)
        
        assert "timeout" in str(exc_info.value).lower()

    async def test_memory_limit_monitoring(self, gap_analyzer, analysis_config):
        """Test memory usage monitoring during analysis."""
        # Configure strict memory limit
        analysis_config.max_memory_usage_mb = 1  # 1MB limit
        
        # Mock memory monitoring to simulate high usage
        with patch('psutil.Process') as mock_process:
            mock_process.return_value.memory_info.return_value.rss = 2 * 1024 * 1024  # 2MB
            
            # Should detect memory limit exceeded
            with pytest.raises(GapAnalysisError) as exc_info:
                await gap_analyzer.analyze_gaps(analysis_config)
            
            assert "memory limit exceeded" in str(exc_info.value).lower()

    async def test_gap_prioritization_integration(self, gap_analyzer, analysis_config):
        """Test integration with gap prioritization system."""
        result = await gap_analyzer.analyze_gaps(analysis_config)
        
        # Verify all gaps were prioritized
        for gap in result.all_gaps:
            assert hasattr(gap, 'priority_score')
            assert gap.priority_score is not None
            
        # Verify prioritizer was called for each gap
        assert gap_analyzer.gap_prioritizer.calculate_gap_priority_score.call_count == 3

    async def test_concurrent_analysis_safety(self, gap_analyzer, analysis_config):
        """Test thread safety for concurrent gap analysis."""
        # Run multiple analyses concurrently
        tasks = [
            gap_analyzer.analyze_gaps(analysis_config)
            for _ in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All analyses should complete successfully
        assert len(results) == 3
        for result in results:
            assert isinstance(result, GapAnalysisResult)
            assert result.total_gaps_found > 0

    async def test_result_caching(self, gap_analyzer, analysis_config):
        """Test result caching for identical analysis configurations."""
        # First analysis
        result1 = await gap_analyzer.analyze_gaps(analysis_config)
        
        # Second identical analysis (should use cache)
        result2 = await gap_analyzer.analyze_gaps(analysis_config)
        
        # Results should be identical
        assert result1.analysis_id != result2.analysis_id  # Different execution IDs
        assert result1.total_gaps_found == result2.total_gaps_found
        assert len(result1.all_gaps) == len(result2.all_gaps)

    def test_gap_analysis_config_validation(self):
        """Test validation of gap analysis configuration."""
        # Test invalid timeout
        with pytest.raises(ValueError):
            GapAnalysisConfig(max_execution_time_seconds=-1)
        
        # Test invalid memory limit  
        with pytest.raises(ValueError):
            GapAnalysisConfig(max_memory_usage_mb=0)
        
        # Test invalid compliance framework
        with pytest.raises(ValueError):
            GapAnalysisConfig(compliance_frameworks=["INVALID_FRAMEWORK"])

    async def test_asset_filtering(self, gap_analyzer):
        """Test filtering assets for analysis based on criteria."""
        # Configure analysis with specific asset filters
        config = GapAnalysisConfig(
            asset_filters={
                "environment": ["production"],
                "criticality": ["critical", "high"]
            }
        )
        
        result = await gap_analyzer.analyze_gaps(config)
        
        # Should only analyze filtered assets
        assert result.assets_analyzed == 1  # Only production_db matches filters

    async def test_trend_analysis_integration(self, gap_analyzer, analysis_config):
        """Test integration with gap trend analysis."""
        # Mock historical gap data
        with patch.object(gap_analyzer, '_load_historical_gaps') as mock_load:
            mock_load.return_value = []  # No historical gaps
            
            result = await gap_analyzer.analyze_gaps(analysis_config)
            
            # Should include trend analysis
            assert hasattr(result, 'trend_analysis')
            assert result.trend_analysis is not None


class TestGapAnalysisConfig:
    """Test suite for GapAnalysisConfig class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = GapAnalysisConfig()
        
        assert config.include_orphaned_detection is True
        assert config.include_documentation_analysis is True
        assert config.include_compliance_assessment is True
        assert config.max_execution_time_seconds == 180
        assert config.max_memory_usage_mb == 256
        assert "GDPR" in config.compliance_frameworks
        assert "SOC2" in config.compliance_frameworks

    def test_custom_configuration(self):
        """Test custom configuration creation."""
        config = GapAnalysisConfig(
            include_orphaned_detection=False,
            max_execution_time_seconds=300,
            compliance_frameworks=["GDPR"]
        )
        
        assert config.include_orphaned_detection is False
        assert config.max_execution_time_seconds == 300
        assert config.compliance_frameworks == ["GDPR"]

    def test_configuration_serialization(self):
        """Test configuration serialization/deserialization."""
        config = GapAnalysisConfig(
            include_orphaned_detection=True,
            compliance_frameworks=["GDPR", "SOC2"]
        )
        
        # Should be JSON serializable
        config_dict = config.dict()
        assert isinstance(config_dict, dict)
        assert config_dict['include_orphaned_detection'] is True
        assert set(config_dict['compliance_frameworks']) == {"GDPR", "SOC2"}


class TestGapAnalysisResult:
    """Test suite for GapAnalysisResult class."""

    def test_result_creation(self):
        """Test gap analysis result creation."""
        gaps = [
            OrphanedAssetGap(
                asset_id="asset_001",
                gap_type=GapType.MISSING_DOCUMENTATION,
                severity=GapSeverity.HIGH,
                description="Test gap",
                recommendations=["Fix it"]
            )
        ]
        
        result = GapAnalysisResult(
            analysis_id="test_analysis_001",
            execution_time_seconds=45.5,
            gaps=gaps,
            assets_analyzed=5
        )
        
        assert result.analysis_id == "test_analysis_001"
        assert result.execution_time_seconds == 45.5
        assert result.total_gaps_found == 1
        assert result.assets_analyzed == 5

    def test_gap_categorization(self):
        """Test automatic gap categorization in results."""
        gaps = [
            OrphanedAssetGap(
                asset_id="asset_001",
                gap_type=GapType.MISSING_DOCUMENTATION,
                severity=GapSeverity.HIGH,
                description="Test gap 1",
                recommendations=[]
            ),
            DocumentationGap(
                asset_id="asset_002",
                gap_type=GapType.OUTDATED_DOCUMENTATION,
                severity=GapSeverity.MEDIUM,
                description="Test gap 2",
                recommendations=[]
            )
        ]
        
        result = GapAnalysisResult(
            analysis_id="test",
            execution_time_seconds=30,
            gaps=gaps,
            assets_analyzed=2
        )
        
        # Test categorization by type
        assert result.gaps_by_type[GapType.MISSING_DOCUMENTATION] == 1
        assert result.gaps_by_type[GapType.OUTDATED_DOCUMENTATION] == 1
        
        # Test categorization by severity
        assert result.gaps_by_severity[GapSeverity.HIGH] == 1
        assert result.gaps_by_severity[GapSeverity.MEDIUM] == 1

    def test_result_summary_statistics(self):
        """Test calculation of summary statistics."""
        gaps = [
            Mock(severity=GapSeverity.HIGH, priority_score=Mock(score=90)),
            Mock(severity=GapSeverity.MEDIUM, priority_score=Mock(score=60)),
            Mock(severity=GapSeverity.LOW, priority_score=Mock(score=30))
        ]
        
        result = GapAnalysisResult(
            analysis_id="test",
            execution_time_seconds=60,
            gaps=gaps,
            assets_analyzed=10
        )
        
        # Test summary statistics
        assert result.total_gaps_found == 3
        assert result.high_severity_gaps == 1
        assert result.medium_severity_gaps == 1
        assert result.low_severity_gaps == 1
        assert result.average_priority_score == 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])