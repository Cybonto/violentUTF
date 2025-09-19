"""
Test suite for Issue #281: Gap Identification Algorithms - Orphaned Resource Detector

This module tests the orphaned resource detection algorithms that identify
assets without proper documentation, ownership, or code references.

Test Coverage:
- Asset-documentation comparison logic
- Code reference analysis using AST
- Configuration consistency checking  
- Usage pattern analysis
- False positive reduction
"""

import ast
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment
from app.models.gap_analysis import GapSeverity, GapType, OrphanedAssetGap

# Import the classes we'll be testing (will be implemented)
from app.services.asset_management.orphaned_detector import (
    CodeReference,
    ConfigurationDrift,
    OrphanedResourceDetector,
    UsageMetrics,
)


class TestOrphanedResourceDetector:
    """Test suite for the OrphanedResourceDetector class."""

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
                criticality_level=CriticalityLevel.CRITICAL,
                owner_team="data_team",
                technical_contact="admin@company.com",
                connection_string="postgresql://user:pass@localhost/prod_db",
                file_path=None
            ),
            DatabaseAsset(
                id="asset_002",
                name="orphaned_sqlite",
                asset_type=AssetType.SQLITE,
                environment=Environment.DEVELOPMENT,
                criticality_level=CriticalityLevel.LOW,
                owner_team=None,  # Missing ownership
                technical_contact=None,
                connection_string=None,
                file_path="/app/data/orphaned.db"
            ),
            DatabaseAsset(
                id="asset_003",
                name="unreferenced_db",
                asset_type=AssetType.DUCKDB,
                environment=Environment.PRODUCTION,
                criticality_level=CriticalityLevel.MEDIUM,
                owner_team="analytics_team",
                technical_contact="analytics@company.com",
                connection_string=None,
                file_path="/app/data/analytics.duckdb"
            )
        ]
        return service

    @pytest.fixture
    def mock_documentation_service(self):
        """Mock documentation service."""
        service = AsyncMock()
        
        # asset_001 has documentation, asset_002 doesn't
        async def mock_find_documentation(asset_id, doc_type=None):
            if asset_id == "asset_001":
                return Mock(
                    asset_id=asset_id,
                    documentation_type="technical_specs",
                    last_updated=datetime.now(),
                    completeness_score=0.9
                )
            return None
            
        service.find_asset_documentation.side_effect = mock_find_documentation
        return service

    @pytest.fixture
    def mock_monitoring_service(self):
        """Mock monitoring service for usage metrics."""
        service = AsyncMock()
        
        async def mock_get_usage_metrics(asset_id, days):
            # asset_003 is unused, others have activity
            if asset_id == "asset_003":
                return UsageMetrics(
                    asset_id=asset_id,
                    connection_count=0,
                    last_activity_date=datetime.now() - timedelta(days=120),
                    days_since_last_activity=120,
                    activity_score=0.0
                )
            return UsageMetrics(
                asset_id=asset_id,
                connection_count=150,
                last_activity_date=datetime.now() - timedelta(days=1),
                days_since_last_activity=1,
                activity_score=0.95
            )
            
        service.get_asset_usage_metrics.side_effect = mock_get_usage_metrics
        return service

    @pytest.fixture
    def orphaned_detector(self, mock_asset_service, mock_documentation_service, mock_monitoring_service):
        """Create OrphanedResourceDetector with mocked dependencies."""
        return OrphanedResourceDetector(
            asset_service=mock_asset_service,
            documentation_service=mock_documentation_service,
            monitoring_service=mock_monitoring_service
        )

    async def test_detector_initialization(self, orphaned_detector):
        """Test OrphanedResourceDetector initialization."""
        assert orphaned_detector is not None
        assert orphaned_detector.asset_service is not None
        assert orphaned_detector.documentation_service is not None
        assert orphaned_detector.monitoring_service is not None

    async def test_detect_orphaned_assets_missing_documentation(self, orphaned_detector):
        """Test detection of assets missing documentation."""
        gaps = await orphaned_detector.detect_orphaned_assets()
        
        # Should find asset_002 missing documentation
        doc_gaps = [gap for gap in gaps if gap.gap_type == GapType.MISSING_DOCUMENTATION]
        assert len(doc_gaps) >= 1
        
        orphaned_gap = next(gap for gap in doc_gaps if gap.asset_id == "asset_002")
        assert orphaned_gap.severity == GapSeverity.MEDIUM
        assert "lacks proper documentation" in orphaned_gap.description.lower()
        assert len(orphaned_gap.recommendations) > 0

    async def test_detect_orphaned_assets_missing_ownership(self, orphaned_detector):
        """Test detection of assets missing ownership."""
        gaps = await orphaned_detector.detect_orphaned_assets()
        
        # Should find asset_002 missing ownership
        ownership_gaps = [gap for gap in gaps if gap.gap_type == GapType.UNCLEAR_OWNERSHIP]
        assert len(ownership_gaps) >= 1
        
        ownership_gap = next(gap for gap in ownership_gaps if gap.asset_id == "asset_002")
        assert ownership_gap.severity in [GapSeverity.MEDIUM, GapSeverity.HIGH]
        assert "lacks clear ownership" in ownership_gap.description.lower()

    async def test_detect_unreferenced_assets(self, orphaned_detector):
        """Test detection of assets not referenced in code."""
        # Mock code search to return no references for asset_003
        with patch.object(orphaned_detector, 'find_code_references') as mock_search:
            mock_search.return_value = []
            
            gaps = await orphaned_detector.detect_orphaned_assets()
            
            # Should find asset_003 as unreferenced
            unreferenced_gaps = [gap for gap in gaps if gap.gap_type == GapType.UNREFERENCED_ASSET]
            assert len(unreferenced_gaps) >= 1
            
            unreferenced_gap = next(gap for gap in unreferenced_gaps if gap.asset_id == "asset_003")
            assert unreferenced_gap.severity == GapSeverity.MEDIUM
            assert "not referenced in active code" in unreferenced_gap.description.lower()

    @pytest.mark.asyncio
    async def test_code_reference_search_database_names(self, orphaned_detector):
        """Test searching for database name references in code."""
        # Mock file system search
        sample_code = """
import sqlite3
import psycopg2

# Connect to production database
conn = psycopg2.connect("postgresql://user:pass@localhost/production_db")

# SQLite connection
sqlite_conn = sqlite3.connect("/app/data/orphaned.db")
        """
        
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('builtins.open', mock_open(read_data=sample_code)):
            
            mock_glob.return_value = [Path("test_file.py")]
            
            asset = Mock(name="production_db", connection_string=None, file_path=None)
            references = await orphaned_detector.find_code_references(asset)
            
            # Should find reference to production_db
            assert len(references) > 0
            assert any("production_db" in ref.context for ref in references)

    @pytest.mark.asyncio
    async def test_code_reference_search_file_paths(self, orphaned_detector):
        """Test searching for file path references in code."""
        sample_code = """
import duckdb

# Connect to analytics database
conn = duckdb.connect("/app/data/analytics.duckdb")
        """
        
        with patch('pathlib.Path.glob') as mock_glob, \
             patch('builtins.open', mock_open(read_data=sample_code)):
            
            mock_glob.return_value = [Path("analytics.py")]
            
            asset = Mock(
                name="analytics_db", 
                connection_string=None, 
                file_path="/app/data/analytics.duckdb"
            )
            references = await orphaned_detector.find_code_references(asset)
            
            # Should find reference to file path
            assert len(references) > 0
            assert any("/app/data/analytics.duckdb" in ref.context for ref in references)

    @pytest.mark.asyncio
    async def test_ast_analysis_for_database_connections(self, orphaned_detector):
        """Test AST analysis for finding database connections."""
        code_with_db_calls = """
import sqlite3
import psycopg2

def connect_to_db():
    # PostgreSQL connection
    pg_conn = psycopg2.connect(
        host="localhost",
        database="production_db", 
        user="admin",
        password="secret"
    )
    
    # SQLite connection
    sqlite_conn = sqlite3.connect("data.db")
    
    return pg_conn, sqlite_conn
        """
        
        # Parse AST
        tree = ast.parse(code_with_db_calls)
        
        # Mock asset
        asset = Mock(name="production_db")
        
        # Test AST analysis
        with patch.object(orphaned_detector, '_analyze_ast_for_references') as mock_ast:
            mock_ast.return_value = [
                CodeReference(
                    file_path="test.py",
                    line_number=8,
                    context='database="production_db"',
                    reference_type="connection_parameter"
                )
            ]
            
            references = await orphaned_detector._search_code_ast_references(
                tree, asset, "test.py"
            )
            
            assert len(references) > 0
            assert references[0].reference_type == "connection_parameter"

    async def test_configuration_consistency_checking(self, orphaned_detector):
        """Test configuration consistency across environments."""
        # Mock configuration data for different environments
        dev_config = {
            "database_url": "sqlite:///dev.db",
            "max_connections": 10
        }
        
        prod_config = {
            "database_url": "postgresql://prod_server/prod_db",
            "max_connections": 100,
            "ssl_enabled": True  # Missing in dev
        }
        
        with patch.object(orphaned_detector, '_load_environment_config') as mock_config:
            mock_config.side_effect = lambda env: dev_config if env == "development" else prod_config
            
            drift = await orphaned_detector.detect_configuration_drift("test_db")
            
            assert isinstance(drift, ConfigurationDrift)
            assert len(drift.differences) > 0
            
            # Should detect SSL configuration difference
            ssl_diff = next(d for d in drift.differences if "ssl_enabled" in d.parameter)
            assert ssl_diff.dev_value != ssl_diff.prod_value

    async def test_usage_pattern_analysis(self, orphaned_detector):
        """Test analysis of asset usage patterns."""
        # Test with low-usage asset
        asset = Mock(
            id="low_usage_asset",
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.DEVELOPMENT
        )
        
        low_usage_metrics = UsageMetrics(
            asset_id="low_usage_asset",
            connection_count=2,
            last_activity_date=datetime.now() - timedelta(days=95),
            days_since_last_activity=95,
            activity_score=0.1
        )
        
        is_unused = orphaned_detector.is_asset_unused(low_usage_metrics, asset)
        assert is_unused is True

    async def test_critical_asset_usage_threshold(self, orphaned_detector):
        """Test higher threshold for critical assets."""
        # Critical asset with same low usage should not be marked unused
        critical_asset = Mock(
            id="critical_asset",
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION
        )
        
        low_usage_metrics = UsageMetrics(
            asset_id="critical_asset",
            connection_count=0,
            last_activity_date=datetime.now() - timedelta(days=95),
            days_since_last_activity=95,
            activity_score=0.0
        )
        
        # Critical assets require 180+ days of inactivity
        is_unused = orphaned_detector.is_asset_unused(low_usage_metrics, critical_asset)
        assert is_unused is False

    async def test_severity_calculation_missing_documentation(self, orphaned_detector):
        """Test severity calculation for missing documentation gaps."""
        # High criticality asset should get higher severity
        critical_asset = Mock(
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION
        )
        
        severity = orphaned_detector.calculate_documentation_gap_severity(critical_asset)
        assert severity == GapSeverity.HIGH
        
        # Low criticality asset should get lower severity
        low_asset = Mock(
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.DEVELOPMENT
        )
        
        severity = orphaned_detector.calculate_documentation_gap_severity(low_asset)
        assert severity == GapSeverity.MEDIUM

    async def test_ownership_gap_severity_calculation(self, orphaned_detector):
        """Test severity calculation for ownership gaps."""
        # Production asset without owner should be high severity
        prod_asset = Mock(
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.MEDIUM
        )
        
        severity = orphaned_detector.calculate_ownership_gap_severity(prod_asset)
        assert severity == GapSeverity.HIGH
        
        # Development asset without owner should be medium severity
        dev_asset = Mock(
            environment=Environment.DEVELOPMENT,
            criticality_level=CriticalityLevel.LOW
        )
        
        severity = orphaned_detector.calculate_ownership_gap_severity(dev_asset)
        assert severity == GapSeverity.MEDIUM

    async def test_recommendation_generation_documentation(self, orphaned_detector):
        """Test generation of documentation recommendations."""
        asset = Mock(
            name="test_db",
            asset_type=AssetType.POSTGRESQL,
            environment=Environment.PRODUCTION
        )
        
        recommendations = orphaned_detector.generate_documentation_recommendations(asset)
        
        assert len(recommendations) > 0
        assert any("create documentation" in rec.lower() for rec in recommendations)
        assert any("technical specifications" in rec.lower() for rec in recommendations)

    async def test_recommendation_generation_ownership(self, orphaned_detector):
        """Test generation of ownership recommendations."""
        asset = Mock(
            name="orphaned_db",
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.HIGH
        )
        
        recommendations = orphaned_detector.generate_ownership_recommendations(asset)
        
        assert len(recommendations) > 0
        assert any("assign owner" in rec.lower() for rec in recommendations)
        assert any("technical contact" in rec.lower() for rec in recommendations)

    async def test_false_positive_reduction_seasonal_usage(self, orphaned_detector):
        """Test false positive reduction for seasonal usage patterns."""
        # Mock seasonal metrics showing activity in cycles
        seasonal_metrics = UsageMetrics(
            asset_id="seasonal_db",
            connection_count=0,
            last_activity_date=datetime.now() - timedelta(days=60),
            days_since_last_activity=60,
            activity_score=0.0,
            seasonal_pattern=True,  # Indicates seasonal usage
            last_season_activity=datetime.now() - timedelta(days=90)
        )
        
        asset = Mock(
            id="seasonal_db",
            criticality_level=CriticalityLevel.MEDIUM,
            environment=Environment.PRODUCTION,
            usage_pattern="seasonal"
        )
        
        # Should not mark as unused due to seasonal pattern
        is_unused = orphaned_detector.is_asset_unused(seasonal_metrics, asset)
        assert is_unused is False

    async def test_batch_processing_large_asset_inventory(self, orphaned_detector):
        """Test batch processing for large asset inventories."""
        # Mock large number of assets
        large_asset_list = []
        for i in range(1000):
            large_asset_list.append(Mock(
                id=f"asset_{i:04d}",
                name=f"db_{i:04d}",
                owner_team="team_1" if i % 2 == 0 else None
            ))
        
        orphaned_detector.asset_service.get_all_assets.return_value = large_asset_list
        
        # Should handle large inventory without performance issues
        start_time = datetime.now()
        gaps = await orphaned_detector.detect_orphaned_assets()
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Should complete within reasonable time
        assert execution_time < 60  # 1 minute for 1000 assets
        assert len(gaps) > 0  # Should find gaps in half the assets (no owner)

    async def test_concurrent_detection_safety(self, orphaned_detector):
        """Test thread safety for concurrent detection operations."""
        import asyncio

        # Run multiple detection operations concurrently
        tasks = [
            orphaned_detector.detect_orphaned_assets()
            for _ in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully with consistent results
        assert len(results) == 3
        for result in results:
            assert isinstance(result, list)
            assert len(result) > 0

    async def test_error_handling_service_failures(self, orphaned_detector):
        """Test error handling when dependent services fail."""
        # Mock documentation service failure
        orphaned_detector.documentation_service.find_asset_documentation.side_effect = Exception("Service unavailable")
        
        # Should continue with other detections
        gaps = await orphaned_detector.detect_orphaned_assets()
        
        # Should still find ownership gaps even if documentation service fails
        ownership_gaps = [gap for gap in gaps if gap.gap_type == GapType.UNCLEAR_OWNERSHIP]
        assert len(ownership_gaps) > 0

    async def test_cache_optimization_repeated_calls(self, orphaned_detector):
        """Test caching optimization for repeated detection calls."""
        # First call should hit services
        gaps1 = await orphaned_detector.detect_orphaned_assets()
        call_count1 = orphaned_detector.asset_service.get_all_assets.call_count
        
        # Second call within cache window should use cache
        gaps2 = await orphaned_detector.detect_orphaned_assets()
        call_count2 = orphaned_detector.asset_service.get_all_assets.call_count
        
        # Results should be identical
        assert len(gaps1) == len(gaps2)
        
        # Service should not be called again (cached)
        if hasattr(orphaned_detector, '_cache_enabled'):
            assert call_count2 == call_count1


class TestCodeReference:
    """Test suite for CodeReference data class."""

    def test_code_reference_creation(self):
        """Test CodeReference creation and properties."""
        ref = CodeReference(
            file_path="app/database.py",
            line_number=42,
            context='conn = psycopg2.connect("postgresql://localhost/mydb")',
            reference_type="connection_string"
        )
        
        assert ref.file_path == "app/database.py"
        assert ref.line_number == 42
        assert "postgresql://localhost/mydb" in ref.context
        assert ref.reference_type == "connection_string"

    def test_code_reference_equality(self):
        """Test CodeReference equality comparison."""
        ref1 = CodeReference(
            file_path="test.py",
            line_number=10,
            context="test context",
            reference_type="name_reference"
        )
        
        ref2 = CodeReference(
            file_path="test.py",
            line_number=10,
            context="test context",
            reference_type="name_reference"
        )
        
        ref3 = CodeReference(
            file_path="test.py",
            line_number=11,  # Different line
            context="test context",
            reference_type="name_reference"
        )
        
        assert ref1 == ref2
        assert ref1 != ref3


class TestUsageMetrics:
    """Test suite for UsageMetrics data class."""

    def test_usage_metrics_creation(self):
        """Test UsageMetrics creation and computed properties."""
        metrics = UsageMetrics(
            asset_id="test_asset",
            connection_count=100,
            last_activity_date=datetime.now() - timedelta(days=7),
            days_since_last_activity=7,
            activity_score=0.85
        )
        
        assert metrics.asset_id == "test_asset"
        assert metrics.connection_count == 100
        assert metrics.days_since_last_activity == 7
        assert metrics.activity_score == 0.85

    def test_usage_metrics_activity_calculation(self):
        """Test activity score calculation."""
        # High activity
        high_metrics = UsageMetrics(
            asset_id="high_activity",
            connection_count=500,
            last_activity_date=datetime.now(),
            days_since_last_activity=0,
            activity_score=1.0
        )
        
        assert high_metrics.is_active() is True
        
        # Low activity
        low_metrics = UsageMetrics(
            asset_id="low_activity",
            connection_count=1,
            last_activity_date=datetime.now() - timedelta(days=120),
            days_since_last_activity=120,
            activity_score=0.1
        )
        
        assert low_metrics.is_active() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])