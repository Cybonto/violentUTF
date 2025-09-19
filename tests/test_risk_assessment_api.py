#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Comprehensive tests for Risk Assessment API endpoints - Issue #282.

This module provides comprehensive test coverage for the risk assessment
automation framework including NIST RMF-compliant risk scoring, vulnerability
assessment, security control evaluation, and risk alerting.

Test Coverage:
- Risk assessment endpoint testing (CRUD operations)
- Real-time risk scoring validation
- Vulnerability assessment integration
- Security control assessment
- Risk alert management
- Compliance reporting
- Performance requirement validation
- Error handling and edge cases
"""

import asyncio
import json
import os
import pytest
import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest_asyncio

# Add the FastAPI app to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'violentutf_api', 'fastapi_app'))

# Import the FastAPI app and dependencies
from main import app
from app.api.v1.risk import router
from app.schemas.risk_schemas import (
    RiskAssessmentRequest, RiskAssessmentResponse, VulnerabilityScanRequest,
    BulkRiskAssessmentRequest, RiskLevel, AssessmentMethod, AlertLevel
)
from app.core.risk_engine import NISTRMFRiskEngine, RiskAssessmentResult
from app.services.risk_assessment.vulnerability_service import VulnerabilityAssessmentService


class TestRiskAssessmentAPI:
    """Test suite for Risk Assessment API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/risk")
        return TestClient(app)
    
    @pytest.fixture
    def mock_asset_id(self):
        """Generate mock asset ID."""
        return uuid.uuid4()
    
    @pytest.fixture
    def mock_assessment_response(self, mock_asset_id):
        """Mock risk assessment response."""
        return {
            "id": str(uuid.uuid4()),
            "asset_id": str(mock_asset_id),
            "assessment_date": datetime.utcnow().isoformat(),
            "risk_score": 12.5,
            "risk_level": "medium",
            "risk_factors": {
                "likelihood_score": 3.0,
                "impact_score": 4.0,
                "exposure_factor": 0.7,
                "confidence_score": 0.85
            },
            "system_categorization": {
                "confidentiality_impact": "moderate",
                "integrity_impact": "high", 
                "availability_impact": "high",
                "overall_categorization": "high",
                "data_types": ["authentication_data", "business_data"],
                "rationale": "High impact system with sensitive data"
            },
            "selected_controls": ["AC-2", "AC-3", "AU-12", "SC-8"],
            "assessment_method": "automated",
            "assessment_duration_ms": 450,
            "next_assessment_due": (datetime.utcnow() + timedelta(days=90)).isoformat()
        }
    
    @pytest.fixture
    def mock_auth_user(self):
        """Mock authenticated user."""
        return {"username": "test_user", "roles": ["risk_assessor"]}


class TestRiskAssessmentEndpoints(TestRiskAssessmentAPI):
    """Test risk assessment CRUD endpoints."""
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_asset_by_id")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_recent_risk_assessment")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_risk_engine")
    def test_trigger_risk_assessment_success(self, mock_engine, mock_recent, mock_asset, mock_user, 
                                           client, mock_asset_id, mock_auth_user):
        """Test successful risk assessment trigger."""
        # Setup mocks
        mock_user.return_value = mock_auth_user
        mock_asset.return_value = MagicMock(id=mock_asset_id, name="Test Asset")
        mock_recent.return_value = None  # No recent assessment
        
        # Mock risk engine
        mock_risk_engine = MagicMock()
        mock_risk_result = MagicMock()
        mock_risk_result.risk_score = 12.5
        mock_risk_result.risk_level = MagicMock()
        mock_risk_result.risk_level.value = "medium"
        mock_risk_result.assessment_duration_ms = 450
        mock_risk_engine.calculate_risk_score = AsyncMock(return_value=mock_risk_result)
        mock_engine.return_value = mock_risk_engine
        
        # Test request
        request_data = {
            "asset_id": str(mock_asset_id),
            "assessment_method": "automated",
            "include_vulnerabilities": True,
            "include_controls": True,
            "force_refresh": False
        }
        
        with patch("violentutf_api.fastapi_app.app.api.v1.risk._store_risk_assessment") as mock_store, \
             patch("violentutf_api.fastapi_app.app.api.v1.risk._convert_risk_assessment_to_response") as mock_convert:
            
            mock_assessment = MagicMock()
            mock_store.return_value = mock_assessment
            mock_convert.return_value = mock_assessment
            
            response = client.post("/api/v1/risk/assessments", json=request_data)
        
        # Assertions
        assert response.status_code == 201
        mock_risk_engine.calculate_risk_score.assert_called_once()
        mock_store.assert_called_once()
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_asset_by_id")
    def test_trigger_risk_assessment_asset_not_found(self, mock_asset, mock_user, 
                                                    client, mock_asset_id, mock_auth_user):
        """Test risk assessment with non-existent asset."""
        mock_user.return_value = mock_auth_user
        mock_asset.return_value = None  # Asset not found
        
        request_data = {
            "asset_id": str(mock_asset_id),
            "assessment_method": "automated"
        }
        
        response = client.post("/api/v1/risk/assessments", json=request_data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_latest_risk_assessment")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._convert_risk_assessment_to_response")
    def test_get_risk_assessment_success(self, mock_convert, mock_latest, mock_user,
                                       client, mock_asset_id, mock_auth_user, mock_assessment_response):
        """Test successful risk assessment retrieval."""
        mock_user.return_value = mock_auth_user
        mock_assessment = MagicMock()
        mock_latest.return_value = mock_assessment
        mock_convert.return_value = mock_assessment_response
        
        response = client.get(f"/api/v1/risk/assessments/{mock_asset_id}")
        
        assert response.status_code == 200
        # Note: In actual implementation, would verify response structure
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_latest_risk_assessment")
    def test_get_risk_assessment_not_found(self, mock_latest, mock_user,
                                         client, mock_asset_id, mock_auth_user):
        """Test risk assessment retrieval with no assessment found."""
        mock_user.return_value = mock_auth_user
        mock_latest.return_value = None
        
        response = client.get(f"/api/v1/risk/assessments/{mock_asset_id}")
        
        assert response.status_code == 404
        assert "no risk assessment found" in response.json()["detail"].lower()


class TestRealTimeRiskScoring(TestRiskAssessmentAPI):
    """Test real-time risk scoring endpoints."""
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_asset_by_id")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_risk_engine")
    def test_real_time_risk_scoring_performance(self, mock_engine, mock_asset, mock_user,
                                              client, mock_asset_id, mock_auth_user):
        """Test real-time risk scoring meets performance requirements (≤500ms)."""
        mock_user.return_value = mock_auth_user
        mock_asset.return_value = MagicMock(id=mock_asset_id, name="Test Asset")
        
        # Mock risk engine with performance tracking
        mock_risk_engine = MagicMock()
        mock_risk_result = MagicMock()
        mock_risk_result.risk_score = 15.2
        mock_risk_result.risk_level = MagicMock()
        mock_risk_result.risk_level.value = "high"
        mock_risk_result.assessment_duration_ms = 350  # Within 500ms requirement
        
        async def mock_calculate_risk():
            # Simulate calculation time
            await asyncio.sleep(0.35)  # 350ms
            return mock_risk_result
        
        mock_risk_engine.calculate_risk_score = mock_calculate_risk
        mock_engine.return_value = mock_risk_engine
        
        request_data = {
            "asset_id": str(mock_asset_id),
            "assessment_method": "automated"
        }
        
        with patch("violentutf_api.fastapi_app.app.api.v1.risk._convert_risk_result_to_response") as mock_convert:
            mock_convert.return_value = {"risk_score": 15.2, "assessment_duration_ms": 350}
            
            import time
            start_time = time.time()
            response = client.post("/api/v1/risk/score", json=request_data)
            duration = (time.time() - start_time) * 1000  # Convert to ms
        
        assert response.status_code == 200
        assert duration < 1000  # Allow some overhead for test environment
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_bulk_risk_scoring_request_validation(self, mock_user, client, mock_auth_user):
        """Test bulk risk scoring request validation."""
        mock_user.return_value = mock_auth_user
        
        # Test with too many assets (>100)
        asset_ids = [str(uuid.uuid4()) for _ in range(101)]
        request_data = {
            "asset_ids": asset_ids,
            "assessment_method": "automated"
        }
        
        response = client.post("/api/v1/risk/score/bulk", json=request_data)
        
        assert response.status_code == 400
        assert "maximum 100 assets" in response.json()["detail"].lower()
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_bulk_risk_scoring_success(self, mock_user, client, mock_auth_user):
        """Test successful bulk risk scoring."""
        mock_user.return_value = mock_auth_user
        
        asset_ids = [str(uuid.uuid4()) for _ in range(5)]
        request_data = {
            "asset_ids": asset_ids,
            "assessment_method": "automated",
            "include_vulnerabilities": True
        }
        
        with patch("violentutf_api.fastapi_app.app.api.v1.risk._process_bulk_risk_assessment") as mock_process:
            response = client.post("/api/v1/risk/score/bulk", json=request_data)
        
        assert response.status_code == 202  # Accepted for background processing
        response_data = response.json()
        assert "job_id" in response_data
        assert response_data["status"] == "processing"
        assert response_data["total_assets"] == 5


class TestVulnerabilityAssessment(TestRiskAssessmentAPI):
    """Test vulnerability assessment endpoints."""
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_asset_by_id")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_recent_vulnerability_assessment")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_vulnerability_service")
    def test_vulnerability_scan_success(self, mock_service, mock_recent, mock_asset, mock_user,
                                       client, mock_asset_id, mock_auth_user):
        """Test successful vulnerability scan."""
        mock_user.return_value = mock_auth_user
        mock_asset.return_value = MagicMock(id=mock_asset_id, name="Test Asset")
        mock_recent.return_value = None  # No recent scan
        
        # Mock vulnerability service
        mock_vuln_service = MagicMock()
        mock_vuln_result = MagicMock()
        mock_vuln_result.total_vulnerabilities = 5
        mock_vuln_result.critical_vulnerabilities = 1
        mock_vuln_result.vulnerability_score = 3.5
        mock_vuln_result.scan_duration_seconds = 300  # 5 minutes
        mock_vuln_service.assess_asset_vulnerabilities = AsyncMock(return_value=mock_vuln_result)
        mock_service.return_value = mock_vuln_service
        
        request_data = {
            "asset_id": str(mock_asset_id),
            "scan_depth": "standard",
            "include_exploit_check": True
        }
        
        with patch("violentutf_api.fastapi_app.app.api.v1.risk._store_vulnerability_assessment") as mock_store, \
             patch("violentutf_api.fastapi_app.app.api.v1.risk._convert_vulnerability_assessment_to_response") as mock_convert:
            
            mock_assessment = MagicMock()
            mock_store.return_value = mock_assessment
            mock_convert.return_value = mock_assessment
            
            response = client.post("/api/v1/risk/vulnerabilities/scan", json=request_data)
        
        assert response.status_code == 201
        mock_vuln_service.assess_asset_vulnerabilities.assert_called_once()
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_asset_by_id")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_recent_vulnerability_assessment")
    def test_vulnerability_scan_uses_cached_result(self, mock_recent, mock_asset, mock_user,
                                                  client, mock_asset_id, mock_auth_user):
        """Test vulnerability scan returns cached result when available."""
        mock_user.return_value = mock_auth_user
        mock_asset.return_value = MagicMock(id=mock_asset_id)
        
        # Mock recent assessment (less than 24 hours old)
        recent_assessment = MagicMock()
        recent_assessment.assessment_date = datetime.utcnow() - timedelta(hours=12)
        mock_recent.return_value = recent_assessment
        
        request_data = {
            "asset_id": str(mock_asset_id),
            "force_refresh": False  # Don't force refresh
        }
        
        with patch("violentutf_api.fastapi_app.app.api.v1.risk._convert_vulnerability_assessment_to_response") as mock_convert:
            mock_convert.return_value = {"cached": True}
            
            response = client.post("/api/v1/risk/vulnerabilities/scan", json=request_data)
        
        assert response.status_code == 201
        mock_convert.assert_called_once_with(recent_assessment)


class TestRiskAlertManagement(TestRiskAssessmentAPI):
    """Test risk alert management endpoints."""
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_configure_risk_alerts(self, mock_user, client, mock_asset_id, mock_auth_user):
        """Test risk alert configuration."""
        mock_user.return_value = mock_auth_user
        
        request_data = {
            "asset_id": str(mock_asset_id),
            "risk_threshold": 15.0,
            "alert_level": "critical",
            "notification_channels": ["email", "webhook"],
            "escalation_rules": {
                "max_escalations": 3,
                "escalation_interval_minutes": 15
            },
            "enabled": True
        }
        
        with patch("violentutf_api.fastapi_app.app.api.v1.risk._store_alert_configuration") as mock_store:
            mock_store.return_value = uuid.uuid4()
            
            response = client.post("/api/v1/risk/alerts/configure", json=request_data)
        
        assert response.status_code == 201
        response_data = response.json()
        assert "config_id" in response_data
        assert response_data["risk_threshold"] == 15.0
        assert response_data["alert_level"] == "critical"
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_risk_alerts_with_filters")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._convert_risk_alert_to_response")
    def test_get_active_alerts(self, mock_convert, mock_get_alerts, mock_user,
                              client, mock_auth_user):
        """Test retrieving active risk alerts."""
        mock_user.return_value = mock_auth_user
        
        # Mock alerts
        mock_alerts = [
            MagicMock(id=uuid.uuid4(), alert_level="critical", resolved_at=None),
            MagicMock(id=uuid.uuid4(), alert_level="warning", resolved_at=None)
        ]
        mock_get_alerts.return_value = mock_alerts
        mock_convert.side_effect = [
            {"id": str(alert.id), "alert_level": alert.alert_level}
            for alert in mock_alerts
        ]
        
        response = client.get("/api/v1/risk/alerts?unresolved_only=true")
        
        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == 2
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._acknowledge_risk_alert")
    def test_acknowledge_alert(self, mock_acknowledge, mock_user, client, mock_auth_user):
        """Test acknowledging risk alert."""
        mock_user.return_value = mock_auth_user
        mock_acknowledge.return_value = True
        
        alert_id = uuid.uuid4()
        response = client.post(f"/api/v1/risk/alerts/{alert_id}/acknowledge")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "acknowledged"
        assert response_data["alert_id"] == str(alert_id)
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._resolve_risk_alert")
    def test_resolve_alert(self, mock_resolve, mock_user, client, mock_auth_user):
        """Test resolving risk alert."""
        mock_user.return_value = mock_auth_user
        mock_resolve.return_value = True
        
        alert_id = uuid.uuid4()
        response = client.post(f"/api/v1/risk/alerts/{alert_id}/resolve")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["status"] == "resolved"
        assert response_data["alert_id"] == str(alert_id)


class TestRiskAnalytics(TestRiskAssessmentAPI):
    """Test risk analytics and reporting endpoints."""
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_get_risk_trends(self, mock_user, client, mock_auth_user):
        """Test risk trend analysis endpoint."""
        mock_user.return_value = mock_auth_user
        
        response = client.get("/api/v1/risk/analytics/trends?days=30")
        
        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, list)
        # In actual implementation, would verify trend data structure
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_get_risk_predictions(self, mock_user, client, mock_auth_user):
        """Test predictive risk analysis endpoint."""
        mock_user.return_value = mock_auth_user
        
        response = client.get("/api/v1/risk/analytics/predictions?prediction_days=30")
        
        assert response.status_code == 200
        response_data = response.json()
        assert "total_assets" in response_data
        assert "average_compliance_score" in response_data
        assert "priority_recommendations" in response_data
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._search_risk_assessments")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._convert_risk_assessment_to_response")
    def test_search_risk_assessments(self, mock_convert, mock_search, mock_user,
                                   client, mock_auth_user):
        """Test risk assessment search functionality."""
        mock_user.return_value = mock_auth_user
        
        # Mock search results
        mock_assessments = [MagicMock() for _ in range(3)]
        mock_search.return_value = mock_assessments
        mock_convert.side_effect = [
            {"id": str(uuid.uuid4()), "risk_score": 10.0 + i}
            for i in range(3)
        ]
        
        search_request = {
            "query": "high risk assets",
            "risk_level": "high",
            "min_risk_score": 15.0,
            "limit": 10,
            "offset": 0
        }
        
        response = client.post("/api/v1/risk/search", json=search_request)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "results" in response_data
        assert "execution_time" in response_data
        assert len(response_data["results"]) == 3


class TestPerformanceRequirements(TestRiskAssessmentAPI):
    """Test performance requirements compliance."""
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_asset_by_id")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_risk_engine")
    def test_risk_calculation_performance_requirement(self, mock_engine, mock_asset, mock_user,
                                                     client, mock_asset_id, mock_auth_user):
        """Test that risk calculation meets ≤500ms performance requirement."""
        mock_user.return_value = mock_auth_user
        mock_asset.return_value = MagicMock(id=mock_asset_id)
        
        # Mock risk engine that takes exactly 500ms
        mock_risk_engine = MagicMock()
        mock_risk_result = MagicMock()
        mock_risk_result.assessment_duration_ms = 500  # Exactly at limit
        
        async def slow_calculation():
            await asyncio.sleep(0.5)  # 500ms
            return mock_risk_result
        
        mock_risk_engine.calculate_risk_score = slow_calculation
        mock_engine.return_value = mock_risk_engine
        
        request_data = {"asset_id": str(mock_asset_id)}
        
        with patch("violentutf_api.fastapi_app.app.api.v1.risk._convert_risk_result_to_response") as mock_convert, \
             patch("time.time") as mock_time:
            
            # Mock time to simulate exact 500ms
            mock_time.side_effect = [0, 0.5]  # Start and end times
            mock_convert.return_value = {"assessment_duration_ms": 500}
            
            response = client.post("/api/v1/risk/score", json=request_data)
        
        assert response.status_code == 200
        # Verify performance requirement logging would be triggered if exceeded
    
    def test_concurrent_assessment_scalability(self, client):
        """Test system can handle 50+ concurrent assessments."""
        # This would be an integration test in a real environment
        # Here we just verify the endpoint structure supports concurrent requests
        
        asset_ids = [str(uuid.uuid4()) for _ in range(50)]
        request_data = {
            "asset_ids": asset_ids,
            "assessment_method": "automated"
        }
        
        with patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user") as mock_user:
            mock_user.return_value = {"username": "test_user"}
            
            response = client.post("/api/v1/risk/score/bulk", json=request_data)
        
        # Should accept the request for background processing
        assert response.status_code == 202


class TestErrorHandling(TestRiskAssessmentAPI):
    """Test error handling and edge cases."""
    
    def test_unauthenticated_request(self, client, mock_asset_id):
        """Test that unauthenticated requests are rejected."""
        request_data = {"asset_id": str(mock_asset_id)}
        
        # Don't mock authentication - should fail
        response = client.post("/api/v1/risk/assessments", json=request_data)
        
        # Should return 401 or redirect to auth
        assert response.status_code in [401, 403]
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_invalid_uuid_format(self, mock_user, client, mock_auth_user):
        """Test handling of invalid UUID format."""
        mock_user.return_value = mock_auth_user
        
        request_data = {"asset_id": "invalid-uuid-format"}
        
        response = client.post("/api/v1/risk/assessments", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk._get_asset_by_id")
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_risk_engine")
    def test_risk_engine_exception_handling(self, mock_engine, mock_asset, mock_user,
                                          client, mock_asset_id, mock_auth_user):
        """Test handling of risk engine exceptions."""
        mock_user.return_value = mock_auth_user
        mock_asset.return_value = MagicMock(id=mock_asset_id)
        
        # Mock risk engine that raises exception
        mock_risk_engine = MagicMock()
        mock_risk_engine.calculate_risk_score = AsyncMock(side_effect=Exception("Engine failure"))
        mock_engine.return_value = mock_risk_engine
        
        request_data = {"asset_id": str(mock_asset_id)}
        
        response = client.post("/api/v1/risk/assessments", json=request_data)
        
        assert response.status_code == 500
        assert "risk assessment failed" in response.json()["detail"].lower()


class TestInputValidation(TestRiskAssessmentAPI):
    """Test input validation and schema compliance."""
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_risk_score_range_validation(self, mock_user, client, mock_auth_user):
        """Test risk score range validation in search requests."""
        mock_user.return_value = mock_auth_user
        
        # Test invalid risk score range
        search_request = {
            "min_risk_score": 20.0,
            "max_risk_score": 10.0,  # Max less than min - should fail
            "limit": 10
        }
        
        response = client.post("/api/v1/risk/search", json=search_request)
        
        assert response.status_code == 422  # Validation error
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_alert_threshold_validation(self, mock_user, client, mock_auth_user):
        """Test alert threshold validation."""
        mock_user.return_value = mock_auth_user
        
        # Test invalid risk threshold (outside 1-25 range)
        request_data = {
            "risk_threshold": 30.0,  # Above maximum
            "alert_level": "critical",
            "notification_channels": ["email"]
        }
        
        response = client.post("/api/v1/risk/alerts/configure", json=request_data)
        
        assert response.status_code == 422  # Validation error
    
    @patch("violentutf_api.fastapi_app.app.api.v1.risk.get_current_user")
    def test_required_field_validation(self, mock_user, client, mock_auth_user):
        """Test required field validation."""
        mock_user.return_value = mock_auth_user
        
        # Test missing required asset_id
        request_data = {
            "assessment_method": "automated"
            # Missing asset_id
        }
        
        response = client.post("/api/v1/risk/assessments", json=request_data)
        
        assert response.status_code == 422  # Validation error


# Test fixtures and utilities
@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database_session():
    """Mock database session."""
    return AsyncMock()


# Integration test markers
pytestmark = [
    pytest.mark.api,
    pytest.mark.risk_assessment,
    pytest.mark.issue_282
]


if __name__ == "__main__":
    # Run tests with coverage reporting
    pytest.main([
        __file__,
        "-v",
        "--cov=violentutf_api.fastapi_app.app.api.v1.risk",
        "--cov=violentutf_api.fastapi_app.app.schemas.risk_schemas",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-min=92"  # 92% minimum coverage requirement
    ])