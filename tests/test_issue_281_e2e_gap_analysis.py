"""
Test suite for Issue #281: Gap Identification Algorithms - End-to-End Integration Tests

This module tests the complete gap analysis workflow from asset discovery
through gap detection, prioritization, and reporting.

Test Coverage:
- Full asset inventory gap analysis
- Cross-service integration validation
- Performance under load conditions
- Memory usage optimization
- Real-time monitoring integration
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import psutil
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
from app.services.asset_management.compliance_checker import ComplianceGapChecker
from app.services.asset_management.documentation_analyzer import DocumentationGapAnalyzer

# Import the classes being tested
from app.services.asset_management.gap_analyzer import GapAnalysisConfig, GapAnalysisResult, GapAnalyzer
from app.services.asset_management.gap_prioritizer import GapPrioritizer
from app.services.asset_management.orphaned_detector import OrphanedResourceDetector


class TestEndToEndGapAnalysis:
    """End-to-end integration tests for gap analysis workflow."""

    @pytest.fixture
    def comprehensive_asset_inventory(self):
        """Comprehensive asset inventory for testing."""
        return [
            # Critical production database - should trigger all compliance checks
            DatabaseAsset(
                id="prod_001",
                name="user_profiles_db",
                asset_type=AssetType.POSTGRESQL,
                environment=Environment.PRODUCTION,
                criticality_level=CriticalityLevel.CRITICAL,
                security_classification=SecurityClassification.CONFIDENTIAL,
                owner_team="data_team",
                technical_contact="data-admin@company.com",
                encryption_enabled=False,  # Compliance violation
                access_restricted=True,
                backup_configured=True,
                purpose_description="stores user personal information"
            ),
            
            # Orphaned development database - missing ownership
            DatabaseAsset(
                id="dev_002",
                name="orphaned_test_db",
                asset_type=AssetType.SQLITE,
                environment=Environment.DEVELOPMENT,
                criticality_level=CriticalityLevel.LOW,
                security_classification=SecurityClassification.INTERNAL,
                owner_team=None,  # Orphaned
                technical_contact=None,  # Orphaned
                encryption_enabled=False,
                access_restricted=False,
                backup_configured=False,
                file_path="/tmp/test.db"
            ),
            
            # Staging database with documentation issues
            DatabaseAsset(
                id="stage_003",
                name="staging_analytics",
                asset_type=AssetType.DUCKDB,
                environment=Environment.STAGING,
                criticality_level=CriticalityLevel.MEDIUM,
                security_classification=SecurityClassification.INTERNAL,
                owner_team="analytics_team",
                technical_contact="analytics@company.com",
                encryption_enabled=True,
                access_restricted=True,
                backup_configured=False,  # Missing backup
                file_path="/app/analytics/staging.duckdb"
            ),
            
            # Production database with missing compliance controls
            DatabaseAsset(
                id="prod_004",
                name="financial_transactions",
                asset_type=AssetType.POSTGRESQL,
                environment=Environment.PRODUCTION,
                criticality_level=CriticalityLevel.CRITICAL,
                security_classification=SecurityClassification.RESTRICTED,
                owner_team="finance_team",
                technical_contact="finance-admin@company.com",
                encryption_enabled=False,  # Major compliance issue
                access_restricted=False,   # Major compliance issue
                backup_configured=True,
                purpose_description="financial transaction records"
            ),
            
            # Development database that's actually unused
            DatabaseAsset(
                id="dev_005",
                name="unused_experiment",
                asset_type=AssetType.SQLITE,
                environment=Environment.DEVELOPMENT,
                criticality_level=CriticalityLevel.LOW,
                security_classification=SecurityClassification.PUBLIC,
                owner_team="research_team",
                technical_contact="research@company.com",
                encryption_enabled=False,
                access_restricted=False,
                backup_configured=False,
                file_path="/experiments/unused.db",
                last_accessed=datetime.now() - timedelta(days=120)  # Unused
            )
        ]

    @pytest.fixture
    def mock_documentation_data(self):
        """Mock documentation data simulating real documentation system."""
        return {
            "prod_001": {
                "basic_info": {
                    "last_updated": datetime.now() - timedelta(days=45),
                    "completeness_score": 0.85,
                    "content": "User profiles database documentation"
                },
                "technical_specs": {
                    "last_updated": datetime.now() - timedelta(days=30),
                    "completeness_score": 0.90,
                    "content": "Technical specifications for user_profiles_db"
                }
                # Missing security_procedures for confidential data
            },
            "stage_003": {
                "basic_info": {
                    "last_updated": datetime.now() - timedelta(days=150),  # Outdated
                    "completeness_score": 0.40,  # Incomplete
                    "content": "Basic analytics database info"
                }
                # Missing technical_specs and other required docs
            }
            # dev_002 and others have no documentation (orphaned/missing)
        }

    @pytest.fixture
    def mock_usage_metrics_data(self):
        """Mock usage metrics data."""
        return {
            "prod_001": {
                "connection_count": 1500,
                "last_activity_date": datetime.now() - timedelta(hours=2),
                "days_since_last_activity": 0,
                "activity_score": 0.98
            },
            "dev_002": {
                "connection_count": 5,
                "last_activity_date": datetime.now() - timedelta(days=30),
                "days_since_last_activity": 30,
                "activity_score": 0.15
            },
            "stage_003": {
                "connection_count": 50,
                "last_activity_date": datetime.now() - timedelta(days=3),
                "days_since_last_activity": 3,
                "activity_score": 0.65
            },
            "prod_004": {
                "connection_count": 800,
                "last_activity_date": datetime.now() - timedelta(hours=6),
                "days_since_last_activity": 0,
                "activity_score": 0.92
            },
            "dev_005": {
                "connection_count": 0,
                "last_activity_date": datetime.now() - timedelta(days=120),
                "days_since_last_activity": 120,
                "activity_score": 0.0
            }
        }

    @pytest.fixture
    def integration_test_services(self, comprehensive_asset_inventory, 
                                 mock_documentation_data, mock_usage_metrics_data):
        """Setup integrated services with realistic mock data."""
        
        # Asset service
        asset_service = AsyncMock()
        asset_service.get_all_assets.return_value = comprehensive_asset_inventory
        
        # Documentation service
        documentation_service = AsyncMock()
        
        async def mock_find_documentation(asset_id, doc_type):
            if asset_id in mock_documentation_data and doc_type.value in mock_documentation_data[asset_id]:
                doc_data = mock_documentation_data[asset_id][doc_type.value]
                return Mock(
                    asset_id=asset_id,
                    documentation_type=doc_type,
                    last_updated=doc_data["last_updated"],
                    completeness_score=doc_data["completeness_score"],
                    content=doc_data["content"]
                )
            return None
        
        documentation_service.find_documentation.side_effect = mock_find_documentation
        
        # Monitoring service
        monitoring_service = AsyncMock()
        
        async def mock_get_usage_metrics(asset_id, days):
            if asset_id in mock_usage_metrics_data:
                metrics_data = mock_usage_metrics_data[asset_id]
                return Mock(
                    asset_id=asset_id,
                    connection_count=metrics_data["connection_count"],
                    last_activity_date=metrics_data["last_activity_date"],
                    days_since_last_activity=metrics_data["days_since_last_activity"],
                    activity_score=metrics_data["activity_score"]
                )
            return Mock(
                asset_id=asset_id,
                connection_count=0,
                last_activity_date=datetime.now() - timedelta(days=365),
                days_since_last_activity=365,
                activity_score=0.0
            )
        
        monitoring_service.get_asset_usage_metrics.side_effect = mock_get_usage_metrics
        
        return {
            "asset_service": asset_service,
            "documentation_service": documentation_service,
            "monitoring_service": monitoring_service
        }

    @pytest.fixture
    def e2e_gap_analyzer(self, integration_test_services):
        """Create fully integrated GapAnalyzer for E2E testing."""
        services = integration_test_services
        
        # Create integrated components
        orphaned_detector = OrphanedResourceDetector(
            asset_service=services["asset_service"],
            documentation_service=services["documentation_service"],
            monitoring_service=services["monitoring_service"]
        )
        
        documentation_analyzer = DocumentationGapAnalyzer(
            documentation_service=services["documentation_service"],
            asset_service=services["asset_service"]
        )
        
        compliance_checker = ComplianceGapChecker(Mock())
        gap_prioritizer = GapPrioritizer(Mock())
        
        return GapAnalyzer(
            asset_service=services["asset_service"],
            orphaned_detector=orphaned_detector,
            documentation_analyzer=documentation_analyzer,
            compliance_checker=compliance_checker,
            gap_prioritizer=gap_prioritizer
        )

    async def test_complete_gap_analysis_workflow(self, e2e_gap_analyzer):
        """Test complete end-to-end gap analysis workflow."""
        # Configure comprehensive analysis
        config = GapAnalysisConfig(
            include_orphaned_detection=True,
            include_documentation_analysis=True,
            include_compliance_assessment=True,
            compliance_frameworks=["GDPR", "SOC2", "NIST"],
            max_execution_time_seconds=180,
            max_memory_usage_mb=256
        )
        
        # Execute full analysis
        start_time = time.time()
        result = await e2e_gap_analyzer.analyze_gaps(config)
        execution_time = time.time() - start_time
        
        # Verify execution meets performance requirements
        assert execution_time < 180  # Must complete within time limit
        assert isinstance(result, GapAnalysisResult)
        assert result.execution_time_seconds > 0
        
        # Verify comprehensive gap detection
        assert result.total_gaps_found >= 10  # Should find multiple types of gaps
        assert result.assets_analyzed == 5     # All test assets analyzed
        
        # Verify gap type distribution
        assert GapType.MISSING_DOCUMENTATION in result.gaps_by_type
        assert GapType.INSUFFICIENT_SECURITY_CONTROLS in result.gaps_by_type
        assert GapType.UNCLEAR_OWNERSHIP in result.gaps_by_type
        
        # Verify severity distribution
        assert GapSeverity.HIGH in result.gaps_by_severity
        assert GapSeverity.MEDIUM in result.gaps_by_severity
        assert GapSeverity.LOW in result.gaps_by_severity

    async def test_performance_under_load(self, e2e_gap_analyzer):
        """Test performance with large asset inventory."""
        # Create large asset inventory
        large_inventory = []
        for i in range(100):
            large_inventory.append(
                DatabaseAsset(
                    id=f"asset_{i:03d}",
                    name=f"database_{i:03d}",
                    asset_type=AssetType.POSTGRESQL if i % 2 == 0 else AssetType.SQLITE,
                    environment=Environment.PRODUCTION if i % 3 == 0 else Environment.DEVELOPMENT,
                    criticality_level=CriticalityLevel.HIGH if i % 4 == 0 else CriticalityLevel.MEDIUM,
                    security_classification=SecurityClassification.CONFIDENTIAL if i % 5 == 0 else SecurityClassification.INTERNAL,
                    owner_team="team_1" if i % 6 != 0 else None,  # Some orphaned
                    technical_contact=f"admin_{i}@company.com" if i % 6 != 0 else None,
                    encryption_enabled=i % 7 != 0,  # Some without encryption
                    access_restricted=i % 8 != 0,   # Some without access controls
                    backup_configured=i % 9 != 0    # Some without backups
                )
            )
        
        # Update asset service to return large inventory
        e2e_gap_analyzer.asset_service.get_all_assets.return_value = large_inventory
        
        config = GapAnalysisConfig(max_execution_time_seconds=180, max_memory_usage_mb=256)
        
        # Monitor memory usage during execution
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.time()
        result = await e2e_gap_analyzer.analyze_gaps(config)
        execution_time = time.time() - start_time
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_used = peak_memory - initial_memory
        
        # Verify performance requirements
        assert execution_time < 180    # Time limit
        assert memory_used < 256       # Memory limit
        assert result.assets_analyzed == 100
        assert result.total_gaps_found > 0

    async def test_cross_service_integration_validation(self, e2e_gap_analyzer):
        """Test integration between different gap detection services."""
        config = GapAnalysisConfig()
        result = await e2e_gap_analyzer.analyze_gaps(config)
        
        # Verify each service contributed gaps
        orphaned_gaps = [gap for gap in result.all_gaps if isinstance(gap, OrphanedAssetGap)]
        doc_gaps = [gap for gap in result.all_gaps if isinstance(gap, DocumentationGap)]
        compliance_gaps = [gap for gap in result.all_gaps if isinstance(gap, ComplianceGap)]
        
        assert len(orphaned_gaps) > 0      # Orphaned detector found gaps
        assert len(doc_gaps) > 0           # Documentation analyzer found gaps
        assert len(compliance_gaps) > 0    # Compliance checker found gaps
        
        # Verify no duplicate gaps (deduplication working)
        gap_signatures = set()
        for gap in result.all_gaps:
            signature = (gap.asset_id, gap.gap_type, gap.description)
            assert signature not in gap_signatures  # No duplicates
            gap_signatures.add(signature)

    async def test_gap_prioritization_integration(self, e2e_gap_analyzer):
        """Test integration with gap prioritization system."""
        config = GapAnalysisConfig()
        result = await e2e_gap_analyzer.analyze_gaps(config)
        
        # Verify all gaps have priority scores
        for gap in result.all_gaps:
            assert hasattr(gap, 'priority_score')
            assert gap.priority_score is not None
            assert gap.priority_score.score > 0
        
        # Verify priority distribution makes sense
        critical_gaps = [gap for gap in result.all_gaps 
                        if gap.priority_score.priority_level == "CRITICAL"]
        high_gaps = [gap for gap in result.all_gaps 
                    if gap.priority_score.priority_level == "HIGH"]
        
        # Critical production assets should have high priority gaps
        prod_gaps = [gap for gap in result.all_gaps 
                    if gap.asset_id in ["prod_001", "prod_004"]]
        assert len(prod_gaps) > 0
        
        # At least some production gaps should be high priority
        high_priority_prod_gaps = [gap for gap in prod_gaps 
                                  if gap.priority_score.priority_level in ["CRITICAL", "HIGH"]]
        assert len(high_priority_prod_gaps) > 0

    async def test_real_time_monitoring_integration(self, e2e_gap_analyzer):
        """Test integration with real-time monitoring systems."""
        # Simulate real-time gap detection triggers
        config = GapAnalysisConfig(
            real_time_monitoring=True,
            monitoring_interval_minutes=5
        )
        
        # First analysis
        result1 = await e2e_gap_analyzer.analyze_gaps(config)
        initial_gap_count = result1.total_gaps_found
        
        # Simulate asset change that would trigger new gaps
        new_asset = DatabaseAsset(
            id="new_001",
            name="newly_discovered_db",
            asset_type=AssetType.POSTGRESQL,
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.HIGH,
            security_classification=SecurityClassification.CONFIDENTIAL,
            owner_team=None,  # Orphaned
            technical_contact=None,
            encryption_enabled=False,  # Compliance violation
            access_restricted=False
        )
        
        # Update asset inventory
        current_assets = await e2e_gap_analyzer.asset_service.get_all_assets()
        e2e_gap_analyzer.asset_service.get_all_assets.return_value = current_assets + [new_asset]
        
        # Second analysis should detect new gaps
        result2 = await e2e_gap_analyzer.analyze_gaps(config)
        
        # Should have more gaps due to new problematic asset
        assert result2.total_gaps_found > initial_gap_count
        
        # Should detect gaps for the new asset
        new_asset_gaps = [gap for gap in result2.all_gaps if gap.asset_id == "new_001"]
        assert len(new_asset_gaps) >= 2  # At least orphaned and compliance gaps

    async def test_error_handling_and_recovery(self, e2e_gap_analyzer):
        """Test error handling and graceful degradation."""
        # Simulate partial service failures
        config = GapAnalysisConfig()
        
        # Make documentation service fail
        e2e_gap_analyzer.documentation_analyzer.documentation_service.find_documentation.side_effect = Exception("Service unavailable")
        
        # Analysis should continue with other detectors
        result = await e2e_gap_analyzer.analyze_gaps(config)
        
        # Should still have gaps from other services
        assert result.total_gaps_found > 0
        
        # Should record the error
        assert len(result.errors) > 0
        assert any("service unavailable" in error.lower() for error in result.errors)
        
        # Should still have orphaned and compliance gaps
        orphaned_gaps = [gap for gap in result.all_gaps if isinstance(gap, OrphanedAssetGap)]
        compliance_gaps = [gap for gap in result.all_gaps if isinstance(gap, ComplianceGap)]
        assert len(orphaned_gaps) > 0
        assert len(compliance_gaps) > 0

    async def test_concurrent_analysis_execution(self, e2e_gap_analyzer):
        """Test concurrent execution of multiple gap analyses."""
        config = GapAnalysisConfig()
        
        # Run multiple analyses concurrently
        tasks = [
            e2e_gap_analyzer.analyze_gaps(config)
            for _ in range(3)
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # All should complete successfully
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, GapAnalysisResult)
            assert result.total_gaps_found > 0
        
        # Concurrent execution should not significantly increase total time
        assert execution_time < 300  # Should not be 3x single execution time

    async def test_gap_trend_analysis_integration(self, e2e_gap_analyzer):
        """Test integration with gap trend analysis."""
        # Mock historical gap data
        with patch.object(e2e_gap_analyzer, '_load_historical_gaps') as mock_load:
            mock_load.return_value = [
                Mock(
                    date=datetime.now() - timedelta(days=30),
                    total_gaps=25,
                    critical_gaps=3,
                    high_gaps=8
                ),
                Mock(
                    date=datetime.now() - timedelta(days=60),
                    total_gaps=30,
                    critical_gaps=5,
                    high_gaps=12
                )
            ]
            
            config = GapAnalysisConfig(include_trend_analysis=True)
            result = await e2e_gap_analyzer.analyze_gaps(config)
            
            # Should include trend analysis
            assert hasattr(result, 'trend_analysis')
            assert result.trend_analysis is not None
            
            # Should show improvement trend (fewer gaps over time)
            assert result.trend_analysis.overall_trend == "IMPROVING"

    async def test_compliance_accuracy_integration(self, e2e_gap_analyzer):
        """Test end-to-end compliance detection accuracy."""
        config = GapAnalysisConfig(
            compliance_frameworks=["GDPR", "SOC2", "NIST"]
        )
        
        result = await e2e_gap_analyzer.analyze_gaps(config)
        
        # Verify compliance gaps are detected for assets with known violations
        compliance_gaps = [gap for gap in result.all_gaps if isinstance(gap, ComplianceGap)]
        
        # Should find GDPR violations for personal data assets
        gdpr_gaps = [gap for gap in compliance_gaps if gap.framework == ComplianceFramework.GDPR]
        personal_data_assets = ["prod_001", "prod_004"]  # Both have personal data indicators
        gdpr_asset_violations = [gap for gap in gdpr_gaps if gap.asset_id in personal_data_assets]
        assert len(gdpr_asset_violations) > 0
        
        # Should find SOC2 violations for production assets with missing controls
        soc2_gaps = [gap for gap in compliance_gaps if gap.framework == ComplianceFramework.SOC2]
        production_assets = ["prod_001", "prod_004"]
        soc2_asset_violations = [gap for gap in soc2_gaps if gap.asset_id in production_assets]
        assert len(soc2_asset_violations) > 0

    async def test_memory_optimization_and_cleanup(self, e2e_gap_analyzer):
        """Test memory optimization and cleanup during analysis."""
        config = GapAnalysisConfig()
        
        # Monitor memory throughout the process
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute analysis
        result = await e2e_gap_analyzer.analyze_gaps(config)
        
        # Force garbage collection to ensure cleanup
        import gc
        gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable
        assert memory_growth < 100  # Less than 100MB growth
        
        # Should not have memory leaks (reasonable cleanup)
        assert memory_growth < 256  # Within configured limit

    async def test_result_serialization_and_persistence(self, e2e_gap_analyzer):
        """Test serialization and persistence of analysis results."""
        config = GapAnalysisConfig()
        result = await e2e_gap_analyzer.analyze_gaps(config)
        
        # Test result serialization
        result_dict = result.dict()
        assert isinstance(result_dict, dict)
        assert 'analysis_id' in result_dict
        assert 'total_gaps_found' in result_dict
        assert 'gaps_by_type' in result_dict
        
        # Test gap serialization
        for gap in result.all_gaps:
            gap_dict = gap.dict()
            assert isinstance(gap_dict, dict)
            assert 'asset_id' in gap_dict
            assert 'gap_type' in gap_dict
            assert 'severity' in gap_dict
        
        # Verify serialization preserves all critical data
        assert result_dict['total_gaps_found'] == result.total_gaps_found
        assert result_dict['assets_analyzed'] == result.assets_analyzed


class TestPerformanceBenchmarks:
    """Performance benchmark tests for gap analysis system."""

    @pytest.mark.benchmark
    async def test_gap_analysis_performance_benchmark(self, e2e_gap_analyzer):
        """Benchmark gap analysis performance for different scenarios."""
        scenarios = [
            {"assets": 10, "name": "small_inventory"},
            {"assets": 50, "name": "medium_inventory"},
            {"assets": 100, "name": "large_inventory"}
        ]
        
        results = {}
        
        for scenario in scenarios:
            # Create test inventory
            inventory = [
                DatabaseAsset(
                    id=f"perf_asset_{i:03d}",
                    name=f"perf_db_{i:03d}",
                    asset_type=AssetType.POSTGRESQL,
                    environment=Environment.PRODUCTION,
                    criticality_level=CriticalityLevel.MEDIUM,
                    security_classification=SecurityClassification.INTERNAL,
                    owner_team="test_team",
                    technical_contact="test@company.com"
                )
                for i in range(scenario["assets"])
            ]
            
            e2e_gap_analyzer.asset_service.get_all_assets.return_value = inventory
            
            # Benchmark execution
            config = GapAnalysisConfig()
            start_time = time.time()
            result = await e2e_gap_analyzer.analyze_gaps(config)
            execution_time = time.time() - start_time
            
            results[scenario["name"]] = {
                "execution_time": execution_time,
                "assets_analyzed": result.assets_analyzed,
                "gaps_found": result.total_gaps_found,
                "throughput": result.assets_analyzed / execution_time
            }
        
        # Verify performance scaling
        small_throughput = results["small_inventory"]["throughput"]
        large_throughput = results["large_inventory"]["throughput"]
        
        # Throughput should not degrade significantly with scale
        throughput_ratio = large_throughput / small_throughput
        assert throughput_ratio > 0.5  # Less than 50% degradation acceptable


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])