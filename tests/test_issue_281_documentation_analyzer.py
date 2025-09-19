"""
Test suite for Issue #281: Gap Identification Algorithms - Documentation Analyzer

This module tests the documentation gap analysis algorithms that detect
missing, outdated, or inconsistent documentation.

Test Coverage:
- Required documentation validation
- Template compliance checking
- Content freshness assessment
- Schema documentation analysis
- Quality scoring algorithms
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models.asset_inventory import AssetType, CriticalityLevel, DatabaseAsset, Environment, SecurityClassification
from app.models.gap_analysis import DocumentationGap, GapSeverity, GapType, SchemaDocumentationGap

# Import the classes we'll be testing (will be implemented)
from app.services.asset_management.documentation_analyzer import (
    DocumentationGapAnalyzer,
    DocumentationType,
    QualityIssue,
    SchemaDocumentationAnalyzer,
)


class TestDocumentationGapAnalyzer:
    """Test suite for the DocumentationGapAnalyzer class."""

    @pytest.fixture
    def mock_documentation_service(self):
        """Mock documentation service for testing."""
        service = AsyncMock()
        
        # Mock documentation lookup
        async def mock_find_documentation(asset_id, doc_type):
            # asset_001 has complete recent documentation
            if asset_id == "asset_001" and doc_type == DocumentationType.BASIC_INFO:
                return Mock(
                    asset_id=asset_id,
                    documentation_type=doc_type,
                    last_updated=datetime.now() - timedelta(days=30),
                    completeness_score=0.95,
                    content="Complete documentation"
                )
            # asset_002 has outdated documentation
            elif asset_id == "asset_002" and doc_type == DocumentationType.TECHNICAL_SPECS:
                return Mock(
                    asset_id=asset_id,
                    documentation_type=doc_type,
                    last_updated=datetime.now() - timedelta(days=120),  # Outdated
                    completeness_score=0.60,  # Incomplete
                    content="Partial outdated documentation"
                )
            # asset_003 has no documentation
            return None
            
        service.find_documentation.side_effect = mock_find_documentation
        return service

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
                security_classification=SecurityClassification.CONFIDENTIAL
            ),
            DatabaseAsset(
                id="asset_002",
                name="staging_db",
                asset_type=AssetType.POSTGRESQL,
                environment=Environment.STAGING,
                criticality_level=CriticalityLevel.MEDIUM,
                security_classification=SecurityClassification.INTERNAL
            ),
            DatabaseAsset(
                id="asset_003",
                name="dev_db",
                asset_type=AssetType.SQLITE,
                environment=Environment.DEVELOPMENT,
                criticality_level=CriticalityLevel.LOW,
                security_classification=SecurityClassification.PUBLIC
            )
        ]
        return service

    @pytest.fixture
    def documentation_analyzer(self, mock_documentation_service, mock_asset_service):
        """Create DocumentationGapAnalyzer with mocked dependencies."""
        return DocumentationGapAnalyzer(
            documentation_service=mock_documentation_service,
            asset_service=mock_asset_service
        )

    async def test_analyzer_initialization(self, documentation_analyzer):
        """Test DocumentationGapAnalyzer initialization."""
        assert documentation_analyzer is not None
        assert documentation_analyzer.documentation_service is not None
        assert hasattr(documentation_analyzer, 'required_docs')

    async def test_analyze_missing_documentation_gaps(self, documentation_analyzer):
        """Test detection of missing documentation gaps."""
        gaps = await documentation_analyzer.analyze_documentation_gaps()
        
        # Should find missing documentation for asset_003
        missing_gaps = [gap for gap in gaps if gap.gap_type == GapType.MISSING_DOCUMENTATION]
        assert len(missing_gaps) > 0
        
        # Verify gap details
        missing_gap = next(gap for gap in missing_gaps if gap.asset_id == "asset_003")
        assert missing_gap.severity in [GapSeverity.MEDIUM, GapSeverity.HIGH]
        assert "missing" in missing_gap.description.lower()
        assert len(missing_gap.recommendations) > 0

    async def test_analyze_outdated_documentation_gaps(self, documentation_analyzer):
        """Test detection of outdated documentation gaps."""
        gaps = await documentation_analyzer.analyze_documentation_gaps()
        
        # Should find outdated documentation for asset_002
        outdated_gaps = [gap for gap in gaps if gap.gap_type == GapType.OUTDATED_DOCUMENTATION]
        assert len(outdated_gaps) > 0
        
        outdated_gap = next(gap for gap in outdated_gaps if gap.asset_id == "asset_002")
        assert outdated_gap.severity == GapSeverity.MEDIUM
        assert "days old" in outdated_gap.description

    async def test_required_documentation_by_classification(self, documentation_analyzer):
        """Test required documentation based on security classification."""
        # Confidential asset (asset_001) should require more documentation
        confidential_asset = Mock(
            security_classification=SecurityClassification.CONFIDENTIAL,
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.CRITICAL
        )
        
        required_docs = documentation_analyzer.get_required_documentation(confidential_asset)
        
        # Should include security-specific documentation
        assert DocumentationType.BASIC_INFO in required_docs
        assert DocumentationType.TECHNICAL_SPECS in required_docs
        assert DocumentationType.SECURITY_PROCEDURES in required_docs
        assert DocumentationType.ACCESS_CONTROLS in required_docs
        assert DocumentationType.DATA_CLASSIFICATION in required_docs

    async def test_required_documentation_by_environment(self, documentation_analyzer):
        """Test required documentation based on environment."""
        # Production asset should require operational documentation
        prod_asset = Mock(
            security_classification=SecurityClassification.INTERNAL,
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.MEDIUM
        )
        
        required_docs = documentation_analyzer.get_required_documentation(prod_asset)
        
        # Should include operational documentation
        assert DocumentationType.BACKUP_PROCEDURES in required_docs
        assert DocumentationType.DISASTER_RECOVERY in required_docs
        assert DocumentationType.MONITORING_SETUP in required_docs

    async def test_required_documentation_by_criticality(self, documentation_analyzer):
        """Test required documentation based on criticality level."""
        # Critical asset should require comprehensive documentation
        critical_asset = Mock(
            security_classification=SecurityClassification.INTERNAL,
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.CRITICAL
        )
        
        required_docs = documentation_analyzer.get_required_documentation(critical_asset)
        
        # Should include critical asset documentation
        assert DocumentationType.RUNBOOKS in required_docs
        assert DocumentationType.ESCALATION_PROCEDURES in required_docs
        assert DocumentationType.CAPACITY_PLANNING in required_docs

    async def test_documentation_quality_assessment(self, documentation_analyzer):
        """Test assessment of documentation quality."""
        # Mock document with quality issues
        document = Mock(
            asset_id="test_asset",
            last_updated=datetime.now() - timedelta(days=120),  # Old
            completeness_score=0.60,  # Incomplete
            content="Partial documentation content"
        )
        
        asset = Mock(
            criticality_level=CriticalityLevel.HIGH,
            environment=Environment.PRODUCTION
        )
        
        issues = await documentation_analyzer.assess_documentation_quality(document, asset)
        
        # Should find age and completeness issues
        assert len(issues) >= 2
        
        age_issue = next(issue for issue in issues if "days ago" in issue.description)
        assert age_issue.severity == GapSeverity.MEDIUM
        
        completeness_issue = next(issue for issue in issues if "complete" in issue.description.lower())
        assert completeness_issue.severity == GapSeverity.HIGH

    async def test_completeness_score_calculation(self, documentation_analyzer):
        """Test documentation completeness score calculation."""
        # Mock document with missing sections
        document = Mock(
            content="""
            # Database Documentation
            
            ## Basic Information
            Name: test_db
            
            ## Technical Specifications
            [Missing content]
            
            ## Security Procedures
            [Missing content]
            """,
            template_sections=["basic_info", "technical_specs", "security_procedures", "backup_procedures"]
        )
        
        asset = Mock(environment=Environment.PRODUCTION)
        
        score = await documentation_analyzer.calculate_completeness_score(document, asset)
        
        # Should have partial completeness (1 of 4 sections complete)
        assert 0.2 <= score <= 0.3

    async def test_technical_accuracy_validation(self, documentation_analyzer):
        """Test validation of technical accuracy in documentation."""
        # Mock document with technical inaccuracies
        document = Mock(
            content="Database connection: postgresql://localhost:5432/wrong_db_name",
            asset_id="asset_001"
        )
        
        asset = Mock(
            name="production_db",  # Different from documented name
            connection_string="postgresql://localhost:5432/production_db"
        )
        
        issues = await documentation_analyzer.validate_technical_accuracy(document, asset)
        
        # Should find name mismatch
        assert len(issues) > 0
        name_issue = next(issue for issue in issues if "name" in issue.description.lower())
        assert name_issue.severity == GapSeverity.MEDIUM

    async def test_documentation_template_compliance(self, documentation_analyzer):
        """Test compliance with documentation templates."""
        # Mock template requirements
        template = {
            "required_sections": ["overview", "connection_info", "schema", "procedures"],
            "required_fields": ["owner", "purpose", "last_reviewed"]
        }
        
        # Document missing required sections
        document = Mock(
            content="""
            # Overview
            This is a database.
            
            # Connection Info
            Host: localhost
            """,
            sections=["overview", "connection_info"]  # Missing schema and procedures
        )
        
        compliance_issues = await documentation_analyzer.check_template_compliance(document, template)
        
        # Should find missing sections
        assert len(compliance_issues) >= 2  # Missing schema and procedures sections

    async def test_documentation_gap_severity_calculation(self, documentation_analyzer):
        """Test severity calculation for documentation gaps."""
        # Critical production asset missing documentation should be high severity
        critical_asset = Mock(
            criticality_level=CriticalityLevel.CRITICAL,
            environment=Environment.PRODUCTION
        )
        
        severity = documentation_analyzer.calculate_missing_doc_severity(
            critical_asset, DocumentationType.SECURITY_PROCEDURES
        )
        assert severity == GapSeverity.HIGH
        
        # Low priority development asset missing documentation should be lower severity
        dev_asset = Mock(
            criticality_level=CriticalityLevel.LOW,
            environment=Environment.DEVELOPMENT
        )
        
        severity = documentation_analyzer.calculate_missing_doc_severity(
            dev_asset, DocumentationType.BASIC_INFO
        )
        assert severity == GapSeverity.MEDIUM

    async def test_documentation_creation_recommendations(self, documentation_analyzer):
        """Test generation of documentation creation recommendations."""
        asset = Mock(
            name="test_db",
            asset_type=AssetType.POSTGRESQL,
            environment=Environment.PRODUCTION,
            criticality_level=CriticalityLevel.HIGH
        )
        
        recommendations = documentation_analyzer.generate_doc_creation_recommendations(
            asset, DocumentationType.TECHNICAL_SPECS
        )
        
        assert len(recommendations) > 0
        assert any("create" in rec.lower() for rec in recommendations)
        assert any("technical" in rec.lower() for rec in recommendations)

    async def test_batch_documentation_analysis(self, documentation_analyzer):
        """Test batch analysis of multiple assets."""
        # Should analyze all assets in the mock service
        gaps = await documentation_analyzer.analyze_documentation_gaps()
        
        # Should find gaps for multiple assets
        asset_ids_with_gaps = set(gap.asset_id for gap in gaps)
        assert len(asset_ids_with_gaps) >= 2  # At least asset_002 and asset_003

    async def test_documentation_trend_analysis(self, documentation_analyzer):
        """Test trend analysis of documentation quality over time."""
        # Mock historical documentation data
        historical_data = [
            Mock(
                date=datetime.now() - timedelta(days=30),
                total_assets=10,
                documented_assets=7,
                average_quality_score=0.75
            ),
            Mock(
                date=datetime.now() - timedelta(days=60),
                total_assets=10,
                documented_assets=6,
                average_quality_score=0.70
            )
        ]
        
        with patch.object(documentation_analyzer, '_load_historical_documentation_data') as mock_load:
            mock_load.return_value = historical_data
            
            trend = await documentation_analyzer.analyze_documentation_trends()
            
            # Should show improvement trend
            assert trend.coverage_trend > 0  # Coverage improved
            assert trend.quality_trend > 0   # Quality improved

    async def test_error_handling_service_failures(self, documentation_analyzer):
        """Test error handling when documentation service fails."""
        # Mock service failure
        documentation_analyzer.documentation_service.find_documentation.side_effect = Exception("Service error")
        
        # Should handle error gracefully and continue analysis
        gaps = await documentation_analyzer.analyze_documentation_gaps()
        
        # May have empty results but should not crash
        assert isinstance(gaps, list)

    async def test_concurrent_analysis_safety(self, documentation_analyzer):
        """Test thread safety for concurrent documentation analysis."""
        import asyncio

        # Run multiple analyses concurrently
        tasks = [
            documentation_analyzer.analyze_documentation_gaps()
            for _ in range(3)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 3
        for result in results:
            assert isinstance(result, list)


class TestSchemaDocumentationAnalyzer:
    """Test suite for database schema documentation analysis."""

    @pytest.fixture
    def schema_analyzer(self):
        """Create SchemaDocumentationAnalyzer instance."""
        return SchemaDocumentationAnalyzer()

    @pytest.fixture
    def mock_actual_schema(self):
        """Mock actual database schema."""
        return Mock(
            tables={
                "users": Mock(
                    name="users",
                    columns={
                        "id": Mock(name="id", type="INTEGER", nullable=False),
                        "email": Mock(name="email", type="VARCHAR", nullable=False),
                        "created_at": Mock(name="created_at", type="TIMESTAMP", nullable=True)
                    }
                ),
                "orders": Mock(
                    name="orders",
                    columns={
                        "id": Mock(name="id", type="INTEGER", nullable=False),
                        "user_id": Mock(name="user_id", type="INTEGER", nullable=False),
                        "total": Mock(name="total", type="DECIMAL", nullable=False)
                    }
                ),
                "undocumented_table": Mock(
                    name="undocumented_table",
                    columns={
                        "data": Mock(name="data", type="TEXT", nullable=True)
                    }
                )
            }
        )

    @pytest.fixture
    def mock_documented_schema(self):
        """Mock documented schema."""
        return Mock(
            tables={
                "users": Mock(
                    name="users",
                    columns={
                        "id": "Primary key for users",
                        "email": "User email address"
                        # missing created_at documentation
                    },
                    description="User accounts table"
                ),
                "orders": Mock(
                    name="orders",
                    columns={
                        "id": "Order ID",
                        "user_id": "Reference to users table",
                        "total": "Order total amount"
                    },
                    description="Customer orders"
                )
                # missing undocumented_table
            }
        )

    async def test_schema_documentation_gap_detection(self, schema_analyzer):
        """Test detection of schema documentation gaps."""
        asset = Mock(
            id="test_db",
            asset_type=AssetType.POSTGRESQL
        )
        
        # Mock schema data
        with patch.object(schema_analyzer, 'get_database_schema') as mock_get_schema, \
             patch.object(schema_analyzer.documentation_service, 'get_schema_documentation') as mock_get_docs:
            
            mock_get_schema.return_value = self.mock_actual_schema
            mock_get_docs.return_value = self.mock_documented_schema
            
            gaps = await schema_analyzer.analyze_schema_documentation_gaps(asset)
            
            # Should find undocumented table
            table_gaps = [gap for gap in gaps if gap.gap_type == GapType.UNDOCUMENTED_TABLE]
            assert len(table_gaps) >= 1
            
            undocumented_gap = next(gap for gap in table_gaps if gap.table_name == "undocumented_table")
            assert undocumented_gap.asset_id == "test_db"

    async def test_column_documentation_gaps(self, schema_analyzer):
        """Test detection of undocumented columns."""
        asset = Mock(id="test_db", asset_type=AssetType.POSTGRESQL)
        
        with patch.object(schema_analyzer, 'get_database_schema') as mock_get_schema, \
             patch.object(schema_analyzer.documentation_service, 'get_schema_documentation') as mock_get_docs:
            
            mock_get_schema.return_value = self.mock_actual_schema
            mock_get_docs.return_value = self.mock_documented_schema
            
            gaps = await schema_analyzer.analyze_schema_documentation_gaps(asset)
            
            # Should find undocumented created_at column
            column_gaps = [gap for gap in gaps if gap.gap_type == GapType.UNDOCUMENTED_COLUMN]
            assert len(column_gaps) >= 1
            
            created_at_gap = next(
                gap for gap in column_gaps 
                if gap.table_name == "users" and gap.column_name == "created_at"
            )
            assert created_at_gap.severity == GapSeverity.LOW

    async def test_non_relational_database_skip(self, schema_analyzer):
        """Test skipping schema analysis for non-relational databases."""
        duckdb_asset = Mock(
            id="analytics_db",
            asset_type=AssetType.DUCKDB  # Non-relational for schema docs
        )
        
        gaps = await schema_analyzer.analyze_schema_documentation_gaps(duckdb_asset)
        
        # Should return empty list for non-relational databases
        assert gaps == []

    async def test_table_documentation_severity(self, schema_analyzer):
        """Test severity calculation for table documentation gaps."""
        # Important table should get higher severity
        important_table = Mock(
            name="users",
            row_count=100000,  # Large table
            has_pii=True       # Contains PII
        )
        
        severity = schema_analyzer.calculate_table_documentation_severity(important_table)
        assert severity == GapSeverity.MEDIUM
        
        # Small utility table should get lower severity
        utility_table = Mock(
            name="config",
            row_count=10,
            has_pii=False
        )
        
        severity = schema_analyzer.calculate_table_documentation_severity(utility_table)
        assert severity == GapSeverity.LOW


class TestDocumentationType:
    """Test suite for DocumentationType enumeration."""

    def test_documentation_type_values(self):
        """Test DocumentationType enumeration values."""
        assert DocumentationType.BASIC_INFO == "basic_info"
        assert DocumentationType.TECHNICAL_SPECS == "technical_specs"
        assert DocumentationType.SECURITY_PROCEDURES == "security_procedures"
        assert DocumentationType.BACKUP_PROCEDURES == "backup_procedures"

    def test_documentation_type_iteration(self):
        """Test iteration over documentation types."""
        doc_types = list(DocumentationType)
        assert len(doc_types) >= 8  # At least 8 types defined
        assert DocumentationType.BASIC_INFO in doc_types


class TestQualityIssue:
    """Test suite for QualityIssue data class."""

    def test_quality_issue_creation(self):
        """Test QualityIssue creation and properties."""
        issue = QualityIssue(
            severity=GapSeverity.HIGH,
            description="Documentation is incomplete",
            recommendations=["Complete missing sections", "Review accuracy"]
        )
        
        assert issue.severity == GapSeverity.HIGH
        assert "incomplete" in issue.description
        assert len(issue.recommendations) == 2

    def test_quality_issue_equality(self):
        """Test QualityIssue equality comparison."""
        issue1 = QualityIssue(
            severity=GapSeverity.MEDIUM,
            description="Test issue",
            recommendations=["Fix it"]
        )
        
        issue2 = QualityIssue(
            severity=GapSeverity.MEDIUM,
            description="Test issue",
            recommendations=["Fix it"]
        )
        
        issue3 = QualityIssue(
            severity=GapSeverity.HIGH,  # Different severity
            description="Test issue",
            recommendations=["Fix it"]
        )
        
        assert issue1 == issue2
        assert issue1 != issue3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])