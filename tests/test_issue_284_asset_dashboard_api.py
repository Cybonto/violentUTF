#!/usr/bin/env python3
"""
Test suite for Issue #284: Database Asset Management Dashboard API endpoints
Tests comprehensive asset management, risk assessment, and compliance APIs
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock
import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

# Import application components
from violentutf_api.fastapi_app.main import app
from violentutf_api.fastapi_app.app.models.asset import AssetModel, AssetType, AssetEnvironment
from violentutf_api.fastapi_app.app.models.risk_assessment import RiskAssessmentModel, RiskLevel
from violentutf_api.fastapi_app.app.models.compliance import ComplianceFramework, ComplianceStatusModel
from violentutf_api.fastapi_app.app.schemas.asset import AssetCreate, AssetUpdate, AssetResponse
from violentutf_api.fastapi_app.app.schemas.risk_assessment import RiskAssessmentCreate, RiskAssessmentResponse
from violentutf_api.fastapi_app.app.schemas.compliance import ComplianceStatusCreate, ComplianceStatusResponse
from violentutf_api.fastapi_app.app.services.asset_management_service import AssetManagementService
from violentutf_api.fastapi_app.app.services.risk_assessment_service import RiskAssessmentService
from violentutf_api.fastapi_app.app.services.compliance_monitoring_service import ComplianceMonitoringService
from violentutf_api.fastapi_app.app.core.auth import get_current_user
from violentutf_api.fastapi_app.app.db.database import get_db


class TestAssetManagementAPI:
    """Test suite for Asset Management API endpoints"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(app)
        self.test_user = {
            "id": "test-user-123",
            "username": "test_admin",
            "roles": ["admin", "asset_manager"]
        }
        
        # Mock authentication
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        
        # Sample test data
        self.sample_asset_data = {
            "name": "test-postgresql-db",
            "asset_type": "POSTGRESQL",
            "environment": "PRODUCTION",
            "security_classification": "CONFIDENTIAL",
            "criticality_level": "HIGH",
            "owner_team": "data-engineering",
            "technical_contact": "admin@example.com",
            "description": "Main production PostgreSQL database",
            "metadata": {
                "location": "us-east-1",
                "version": "14.5",
                "backup_enabled": True
            }
        }
        
        self.sample_risk_data = {
            "asset_id": "asset-123",
            "risk_score": 15.5,
            "risk_level": "HIGH",
            "vulnerability_count": 3,
            "threat_level": "MEDIUM",
            "impact_score": 8.5,
            "likelihood_score": 7.0,
            "risk_factors": [
                "outdated_components",
                "exposed_endpoints",
                "insufficient_monitoring"
            ]
        }
        
        self.sample_compliance_data = {
            "asset_id": "asset-123",
            "framework": "SOC2",
            "overall_score": 85.5,
            "compliant": True,
            "gaps": [
                {
                    "control_id": "CC6.1",
                    "description": "Logical access controls",
                    "status": "NON_COMPLIANT",
                    "severity": "MEDIUM"
                }
            ]
        }
    
    def teardown_method(self):
        """Cleanup test environment"""
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_create_asset_success(self):
        """Test successful asset creation"""
        with patch('violentutf_api.fastapi_app.app.services.asset_management_service.AssetManagementService.create_asset') as mock_create:
            mock_asset = AssetModel(id="asset-123", **self.sample_asset_data)
            mock_create.return_value = mock_asset
            
            response = self.client.post("/api/v1/assets/", json=self.sample_asset_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == self.sample_asset_data["name"]
            assert data["asset_type"] == self.sample_asset_data["asset_type"]
            assert data["environment"] == self.sample_asset_data["environment"]
            mock_create.assert_called_once()
    
    def test_create_asset_validation_error(self):
        """Test asset creation with invalid data"""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "asset_type": "INVALID_TYPE",
            "environment": "INVALID_ENV"
        }
        
        response = self.client.post("/api/v1/assets/", json=invalid_data)
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_assets_with_filters(self):
        """Test retrieving assets with filtering parameters"""
        mock_assets = [
            AssetModel(id="asset-1", name="db1", asset_type=AssetType.POSTGRESQL, environment=AssetEnvironment.PRODUCTION),
            AssetModel(id="asset-2", name="db2", asset_type=AssetType.SQLITE, environment=AssetEnvironment.DEVELOPMENT)
        ]
        
        with patch('violentutf_api.fastapi_app.app.services.asset_management_service.AssetManagementService.get_assets') as mock_get:
            mock_get.return_value = mock_assets
            
            # Test with filters
            response = self.client.get("/api/v1/assets/?asset_types=POSTGRESQL&environments=PRODUCTION")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            mock_get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_asset_by_id_success(self):
        """Test retrieving a specific asset by ID"""
        mock_asset = AssetModel(id="asset-123", **self.sample_asset_data)
        
        with patch('violentutf_api.fastapi_app.app.services.asset_management_service.AssetManagementService.get_asset') as mock_get:
            mock_get.return_value = mock_asset
            
            response = self.client.get("/api/v1/assets/asset-123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "asset-123"
            assert data["name"] == self.sample_asset_data["name"]
    
    def test_get_asset_by_id_not_found(self):
        """Test retrieving non-existent asset"""
        with patch('violentutf_api.fastapi_app.app.services.asset_management_service.AssetManagementService.get_asset') as mock_get:
            mock_get.return_value = None
            
            response = self.client.get("/api/v1/assets/non-existent-id")
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_asset_success(self):
        """Test successful asset update"""
        update_data = {
            "name": "updated-db-name",
            "criticality_level": "CRITICAL",
            "metadata": {"updated": True}
        }
        
        mock_asset = AssetModel(id="asset-123", **{**self.sample_asset_data, **update_data})
        
        with patch('violentutf_api.fastapi_app.app.services.asset_management_service.AssetManagementService.update_asset') as mock_update:
            mock_update.return_value = mock_asset
            
            response = self.client.put("/api/v1/assets/asset-123", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == update_data["name"]
            assert data["criticality_level"] == update_data["criticality_level"]
    
    @pytest.mark.asyncio
    async def test_delete_asset_success(self):
        """Test successful asset deletion"""
        with patch('violentutf_api.fastapi_app.app.services.asset_management_service.AssetManagementService.delete_asset') as mock_delete:
            mock_delete.return_value = True
            
            response = self.client.delete("/api/v1/assets/asset-123")
            assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_get_asset_relationships(self):
        """Test retrieving asset relationships"""
        mock_relationships = [
            {
                "source_asset_id": "asset-123",
                "target_asset_id": "asset-456",
                "relationship_type": "DEPENDS_ON",
                "relationship_strength": 0.8
            }
        ]
        
        with patch('violentutf_api.fastapi_app.app.services.asset_management_service.AssetManagementService.get_asset_relationships') as mock_get_rel:
            mock_get_rel.return_value = mock_relationships
            
            response = self.client.get("/api/v1/assets/asset-123/relationships")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["relationship_type"] == "DEPENDS_ON"


class TestRiskAssessmentAPI:
    """Test suite for Risk Assessment API endpoints"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(app)
        self.test_user = {
            "id": "test-user-123",
            "username": "test_admin", 
            "roles": ["admin", "risk_analyst"]
        }
        
        app.dependency_overrides[get_current_user] = lambda: self.test_user
    
    def teardown_method(self):
        """Cleanup test environment"""
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_create_risk_assessment(self):
        """Test creating a new risk assessment"""
        risk_data = {
            "asset_id": "asset-123",
            "risk_score": 15.5,
            "risk_level": "HIGH",
            "vulnerability_count": 3,
            "threat_level": "MEDIUM",
            "impact_score": 8.5,
            "likelihood_score": 7.0,
            "risk_factors": ["outdated_components", "exposed_endpoints"]
        }
        
        mock_assessment = RiskAssessmentModel(id="risk-123", **risk_data)
        
        with patch('violentutf_api.fastapi_app.app.services.risk_assessment_service.RiskAssessmentService.create_assessment') as mock_create:
            mock_create.return_value = mock_assessment
            
            response = self.client.post("/api/v1/risk-assessments/", json=risk_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["risk_score"] == 15.5
            assert data["risk_level"] == "HIGH"
    
    @pytest.mark.asyncio
    async def test_get_latest_risk_assessment(self):
        """Test retrieving latest risk assessment for an asset"""
        mock_assessment = RiskAssessmentModel(
            id="risk-123",
            asset_id="asset-123",
            risk_score=15.5,
            risk_level=RiskLevel.HIGH,
            vulnerability_count=3
        )
        
        with patch('violentutf_api.fastapi_app.app.services.risk_assessment_service.RiskAssessmentService.get_latest_assessment') as mock_get:
            mock_get.return_value = mock_assessment
            
            response = self.client.get("/api/v1/assets/asset-123/risk-assessment/latest")
            
            assert response.status_code == 200
            data = response.json()
            assert data["risk_score"] == 15.5
            assert data["asset_id"] == "asset-123"
    
    @pytest.mark.asyncio
    async def test_get_risk_trend_data(self):
        """Test retrieving risk trend data for time series analysis"""
        mock_trend_data = [
            {
                "date": "2024-01-01",
                "risk_score": 12.0,
                "vulnerability_count": 2
            },
            {
                "date": "2024-01-02",
                "risk_score": 15.5,
                "vulnerability_count": 3
            }
        ]
        
        with patch('violentutf_api.fastapi_app.app.services.risk_assessment_service.RiskAssessmentService.get_risk_trends') as mock_trends:
            mock_trends.return_value = mock_trend_data
            
            response = self.client.get("/api/v1/assets/asset-123/risk-trends?days=30")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[1]["risk_score"] == 15.5
    
    @pytest.mark.asyncio
    async def test_get_risk_predictions(self):
        """Test retrieving risk predictions and forecasts"""
        mock_predictions = {
            "asset_id": "asset-123",
            "current_risk": 15.5,
            "predicted_risk_30_days": 18.2,
            "confidence": 0.85,
            "risk_factors_trending": ["increasing_vulnerabilities", "network_exposure"],
            "recommended_actions": [
                "Update security patches",
                "Implement network segmentation"
            ]
        }
        
        with patch('violentutf_api.fastapi_app.app.services.risk_assessment_service.RiskAssessmentService.get_risk_predictions') as mock_predict:
            mock_predict.return_value = mock_predictions
            
            response = self.client.get("/api/v1/assets/asset-123/risk-predictions")
            
            assert response.status_code == 200
            data = response.json()
            assert data["predicted_risk_30_days"] == 18.2
            assert data["confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_bulk_risk_assessment(self):
        """Test bulk risk assessment for multiple assets"""
        asset_ids = ["asset-123", "asset-456", "asset-789"]
        
        mock_assessments = [
            {"asset_id": aid, "risk_score": 15.0 + i, "risk_level": "MEDIUM"} 
            for i, aid in enumerate(asset_ids)
        ]
        
        with patch('violentutf_api.fastapi_app.app.services.risk_assessment_service.RiskAssessmentService.bulk_assess_risks') as mock_bulk:
            mock_bulk.return_value = mock_assessments
            
            response = self.client.post("/api/v1/risk-assessments/bulk", json={"asset_ids": asset_ids})
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert all("risk_score" in item for item in data)


class TestComplianceMonitoringAPI:
    """Test suite for Compliance Monitoring API endpoints"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(app)
        self.test_user = {
            "id": "test-user-123",
            "username": "test_admin",
            "roles": ["admin", "compliance_officer"]
        }
        
        app.dependency_overrides[get_current_user] = lambda: self.test_user
    
    def teardown_method(self):
        """Cleanup test environment"""
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_compliance_status(self):
        """Test retrieving compliance status for an asset"""
        mock_compliance = ComplianceStatusModel(
            id="comp-123",
            asset_id="asset-123",
            framework=ComplianceFramework.SOC2,
            overall_score=85.5,
            compliant=True
        )
        
        with patch('violentutf_api.fastapi_app.app.services.compliance_monitoring_service.ComplianceMonitoringService.get_compliance_status') as mock_get:
            mock_get.return_value = mock_compliance
            
            response = self.client.get("/api/v1/assets/asset-123/compliance/SOC2")
            
            assert response.status_code == 200
            data = response.json()
            assert data["overall_score"] == 85.5
            assert data["compliant"] is True
    
    @pytest.mark.asyncio
    async def test_run_compliance_assessment(self):
        """Test running a new compliance assessment"""
        assessment_request = {
            "asset_id": "asset-123",
            "framework": "GDPR",
            "include_recommendations": True
        }
        
        mock_result = {
            "assessment_id": "assessment-123",
            "asset_id": "asset-123",
            "framework": "GDPR",
            "overall_score": 78.5,
            "compliant": False,
            "gaps": [
                {
                    "control_id": "Article 32",
                    "description": "Security of processing",
                    "status": "NON_COMPLIANT",
                    "severity": "HIGH"
                }
            ]
        }
        
        with patch('violentutf_api.fastapi_app.app.services.compliance_monitoring_service.ComplianceMonitoringService.run_assessment') as mock_assess:
            mock_assess.return_value = mock_result
            
            response = self.client.post("/api/v1/compliance-assessments/", json=assessment_request)
            
            assert response.status_code == 201
            data = response.json()
            assert data["overall_score"] == 78.5
            assert len(data["gaps"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_compliance_gaps(self):
        """Test retrieving compliance gaps and remediation recommendations"""
        mock_gaps = [
            {
                "asset_id": "asset-123",
                "framework": "SOC2",
                "control_id": "CC6.1",
                "description": "Logical access controls",
                "severity": "HIGH",
                "remediation_steps": [
                    "Implement multi-factor authentication",
                    "Review user access permissions",
                    "Enable audit logging"
                ],
                "estimated_effort": "2-4 weeks"
            }
        ]
        
        with patch('violentutf_api.fastapi_app.app.services.compliance_monitoring_service.ComplianceMonitoringService.get_compliance_gaps') as mock_gaps_func:
            mock_gaps_func.return_value = mock_gaps
            
            response = self.client.get("/api/v1/assets/asset-123/compliance-gaps")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["severity"] == "HIGH"
            assert len(data[0]["remediation_steps"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_compliance_dashboard_data(self):
        """Test retrieving dashboard-specific compliance data"""
        mock_dashboard_data = {
            "overall_compliance_score": 82.3,
            "frameworks": {
                "SOC2": {"score": 85.5, "compliant": True, "gaps": 2},
                "GDPR": {"score": 78.1, "compliant": False, "gaps": 5},
                "NIST": {"score": 83.7, "compliant": True, "gaps": 1}
            },
            "trending": {
                "direction": "improving",
                "change_percentage": 5.2,
                "period": "30_days"
            },
            "high_priority_gaps": 3,
            "total_assets_assessed": 15
        }
        
        with patch('violentutf_api.fastapi_app.app.services.compliance_monitoring_service.ComplianceMonitoringService.get_dashboard_data') as mock_dashboard:
            mock_dashboard.return_value = mock_dashboard_data
            
            response = self.client.get("/api/v1/compliance/dashboard")
            
            assert response.status_code == 200
            data = response.json()
            assert data["overall_compliance_score"] == 82.3
            assert len(data["frameworks"]) == 3
            assert data["high_priority_gaps"] == 3


class TestDashboardMetricsAPI:
    """Test suite for Dashboard Metrics and KPI API endpoints"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(app)
        self.test_user = {
            "id": "test-user-123",
            "username": "test_admin",
            "roles": ["admin", "dashboard_viewer"]
        }
        
        app.dependency_overrides[get_current_user] = lambda: self.test_user
    
    def teardown_method(self):
        """Cleanup test environment"""
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_get_asset_inventory_metrics(self):
        """Test retrieving asset inventory dashboard metrics"""
        mock_metrics = {
            "total_assets": 125,
            "assets_by_type": {
                "POSTGRESQL": 45,
                "SQLITE": 30,
                "DUCKDB": 25,
                "FILE_STORAGE": 25
            },
            "assets_by_environment": {
                "PRODUCTION": 50,
                "STAGING": 35,
                "DEVELOPMENT": 40
            },
            "critical_assets": 15,
            "high_risk_assets": 8,
            "compliance_score": 84.2,
            "monitoring_coverage": 92.0
        }
        
        with patch('violentutf_api.fastapi_app.app.services.dashboard_metrics_service.DashboardMetricsService.get_asset_inventory_metrics') as mock_metrics_func:
            mock_metrics_func.return_value = mock_metrics
            
            response = self.client.get("/api/v1/dashboard/asset-inventory-metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_assets"] == 125
            assert data["critical_assets"] == 15
            assert data["compliance_score"] == 84.2
    
    @pytest.mark.asyncio
    async def test_get_risk_dashboard_metrics(self):
        """Test retrieving risk dashboard metrics"""
        mock_risk_metrics = {
            "average_risk_score": 12.5,
            "risk_distribution": {
                "LOW": 85,
                "MEDIUM": 25,
                "HIGH": 12,
                "CRITICAL": 3
            },
            "risk_velocity": 0.05,  # Risk increase per day
            "predicted_30_day_change": 1.2,
            "high_priority_vulnerabilities": 15,
            "assets_requiring_attention": [
                {"asset_id": "asset-123", "asset_name": "prod-db-1", "risk_score": 22.5},
                {"asset_id": "asset-456", "asset_name": "api-server", "risk_score": 19.8}
            ]
        }
        
        with patch('violentutf_api.fastapi_app.app.services.dashboard_metrics_service.DashboardMetricsService.get_risk_dashboard_metrics') as mock_risk_metrics_func:
            mock_risk_metrics_func.return_value = mock_risk_metrics
            
            response = self.client.get("/api/v1/dashboard/risk-metrics")
            
            assert response.status_code == 200
            data = response.json()
            assert data["average_risk_score"] == 12.5
            assert data["risk_velocity"] == 0.05
            assert len(data["assets_requiring_attention"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_executive_report_data(self):
        """Test retrieving executive report data and KPIs"""
        mock_executive_data = {
            "summary": {
                "total_assets": 125,
                "security_posture_score": 78.5,
                "compliance_percentage": 84.2,
                "critical_findings": 5
            },
            "trends": {
                "security_improvement": 5.2,  # percentage
                "new_assets_30_days": 8,
                "resolved_vulnerabilities": 23,
                "compliance_improvement": 2.1
            },
            "recommendations": [
                {
                    "priority": "HIGH",
                    "title": "Upgrade legacy database systems",
                    "impact": "Reduce security risk by 15%",
                    "effort": "4-6 weeks"
                }
            ],
            "cost_impact": {
                "security_investment": 150000,
                "potential_savings": 2500000,
                "roi_percentage": 1667
            }
        }
        
        with patch('violentutf_api.fastapi_app.app.services.dashboard_metrics_service.DashboardMetricsService.get_executive_report_data') as mock_exec_data:
            mock_exec_data.return_value = mock_executive_data
            
            response = self.client.get("/api/v1/dashboard/executive-report")
            
            assert response.status_code == 200
            data = response.json()
            assert data["summary"]["total_assets"] == 125
            assert data["trends"]["security_improvement"] == 5.2
            assert len(data["recommendations"]) == 1


class TestDashboardPerformance:
    """Test suite for Dashboard Performance Requirements"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(app)
        self.test_user = {
            "id": "test-user-123",
            "username": "test_admin",
            "roles": ["admin"]
        }
        
        app.dependency_overrides[get_current_user] = lambda: self.test_user
    
    def teardown_method(self):
        """Cleanup test environment"""
        app.dependency_overrides.clear()
    
    @pytest.mark.asyncio
    async def test_dashboard_response_time_requirements(self):
        """Test that dashboard endpoints meet performance requirements"""
        import time
        
        # Mock fast service responses
        with patch('violentutf_api.fastapi_app.app.services.dashboard_metrics_service.DashboardMetricsService.get_asset_inventory_metrics') as mock_metrics:
            mock_metrics.return_value = {"total_assets": 100}
            
            start_time = time.time()
            response = self.client.get("/api/v1/dashboard/asset-inventory-metrics")
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200
            # Dashboard refresh should be < 5 seconds (requirement)
            assert response_time < 5.0
    
    @pytest.mark.asyncio 
    async def test_bulk_operations_performance(self):
        """Test performance of bulk operations"""
        import time
        
        # Test bulk risk assessment performance
        asset_ids = [f"asset-{i}" for i in range(50)]  # Test with 50 assets
        
        with patch('violentutf_api.fastapi_app.app.services.risk_assessment_service.RiskAssessmentService.bulk_assess_risks') as mock_bulk:
            mock_bulk.return_value = [{"asset_id": aid, "risk_score": 10.0} for aid in asset_ids]
            
            start_time = time.time()
            response = self.client.post("/api/v1/risk-assessments/bulk", json={"asset_ids": asset_ids})
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200
            # Bulk operations should complete reasonably quickly
            assert response_time < 10.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])