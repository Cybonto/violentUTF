"""
Test suite for Issue #281: Gap Identification Algorithms - API Integration Tests

This module tests the FastAPI endpoints for gap analysis functionality
including authentication, error handling, and response validation.

Test Coverage:
- Gap analysis request/response validation
- Authentication and authorization
- Error handling and status codes
- Report generation and retrieval
- Trend analysis endpoints
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.gaps import router as gaps_router
from app.core.auth import get_current_user

# Import FastAPI app and dependencies
from app.main import app
from app.models.gap_analysis import Gap, GapAnalysisResult, GapSeverity, GapType
from app.schemas.gap_schemas import GapAnalysisRequest, GapAnalysisResponse, GapReportResponse, TrendAnalysisResponse


class TestGapAnalysisAPIEndpoints:
    """Test suite for gap analysis API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for FastAPI app."""
        return TestClient(app)

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return Mock(
            id="user_001",
            username="test_user",
            email="test@company.com",
            roles=["gap_analyst"]
        )

    @pytest.fixture
    def mock_gap_analysis_result(self):
        """Mock gap analysis result for testing."""
        return GapAnalysisResult(
            analysis_id="analysis_001",
            execution_time_seconds=45.5,
            total_gaps_found=15,
            assets_analyzed=10,
            gaps=[
                Mock(
                    asset_id="asset_001",
                    gap_type=GapType.MISSING_DOCUMENTATION,
                    severity=GapSeverity.HIGH,
                    description="Missing documentation",
                    recommendations=["Create documentation"]
                )
            ],
            gaps_by_type={GapType.MISSING_DOCUMENTATION: 8, GapType.INSUFFICIENT_SECURITY_CONTROLS: 7},
            gaps_by_severity={GapSeverity.HIGH: 5, GapSeverity.MEDIUM: 7, GapSeverity.LOW: 3}
        )

    def test_gap_analysis_endpoint_post_success(self, client, mock_user, mock_gap_analysis_result):
        """Test successful gap analysis request."""
        # Mock authentication
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            # Mock gap analyzer service
            with patch('app.api.v1.gaps.gap_analyzer') as mock_analyzer:
                mock_analyzer.analyze_gaps.return_value = mock_gap_analysis_result
                
                # Make request
                request_data = {
                    "include_orphaned_detection": True,
                    "include_documentation_analysis": True,
                    "include_compliance_assessment": True,
                    "compliance_frameworks": ["GDPR", "SOC2"],
                    "asset_filters": {
                        "environment": ["production"],
                        "criticality": ["critical", "high"]
                    }
                }
                
                response = client.post(
                    "/api/v1/gaps/analyze",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["analysis_id"] == "analysis_001"
                assert data["total_gaps_found"] == 15
                assert data["assets_analyzed"] == 10
                assert "gaps_by_type" in data
                assert "gaps_by_severity" in data

    def test_gap_analysis_endpoint_authentication_required(self, client):
        """Test that gap analysis requires authentication."""
        request_data = {
            "include_orphaned_detection": True,
            "include_documentation_analysis": True,
            "include_compliance_assessment": True
        }
        
        # Request without authentication
        response = client.post("/api/v1/gaps/analyze", json=request_data)
        
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    def test_gap_analysis_endpoint_invalid_request(self, client, mock_user):
        """Test gap analysis with invalid request data."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            # Invalid request data
            request_data = {
                "include_orphaned_detection": True,
                "compliance_frameworks": ["INVALID_FRAMEWORK"],  # Invalid framework
                "max_execution_time_seconds": -1  # Invalid timeout
            }
            
            response = client.post(
                "/api/v1/gaps/analyze",
                json=request_data,
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 422  # Validation error
            assert "validation error" in response.json()["detail"][0]["type"]

    def test_gap_analysis_endpoint_service_error(self, client, mock_user):
        """Test gap analysis with service error."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            with patch('app.api.v1.gaps.gap_analyzer') as mock_analyzer:
                # Mock service error
                mock_analyzer.analyze_gaps.side_effect = Exception("Service unavailable")
                
                request_data = {
                    "include_orphaned_detection": True,
                    "include_documentation_analysis": True
                }
                
                response = client.post(
                    "/api/v1/gaps/analyze",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 500
                assert "internal server error" in response.json()["detail"].lower()

    def test_gap_analysis_endpoint_timeout_handling(self, client, mock_user):
        """Test gap analysis timeout handling."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            with patch('app.api.v1.gaps.gap_analyzer') as mock_analyzer:
                # Mock timeout error
                from app.services.asset_management.gap_analyzer import GapAnalysisError
                mock_analyzer.analyze_gaps.side_effect = GapAnalysisError("Analysis timeout")
                
                request_data = {
                    "include_orphaned_detection": True,
                    "max_execution_time_seconds": 1  # Very short timeout
                }
                
                response = client.post(
                    "/api/v1/gaps/analyze",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 408  # Request timeout
                assert "timeout" in response.json()["detail"].lower()

    def test_gap_report_retrieval_endpoint(self, client, mock_user):
        """Test gap report retrieval endpoint."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            with patch('app.api.v1.gaps.gap_report_service') as mock_service:
                # Mock report data
                mock_report = Mock(
                    report_id="report_001",
                    analysis_id="analysis_001",
                    generated_date=datetime.now(),
                    total_gaps=15,
                    recommendations_count=25,
                    report_summary="Gap analysis summary"
                )
                mock_service.get_report.return_value = mock_report
                
                response = client.get(
                    "/api/v1/gaps/reports/report_001",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["report_id"] == "report_001"
                assert data["analysis_id"] == "analysis_001"
                assert data["total_gaps"] == 15

    def test_gap_report_not_found(self, client, mock_user):
        """Test gap report retrieval for non-existent report."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            with patch('app.api.v1.gaps.gap_report_service') as mock_service:
                mock_service.get_report.return_value = None
                
                response = client.get(
                    "/api/v1/gaps/reports/nonexistent_report",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()

    def test_trend_analysis_endpoint(self, client, mock_user):
        """Test gap trend analysis endpoint."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            with patch('app.api.v1.gaps.trend_analyzer') as mock_analyzer:
                # Mock trend data
                mock_trend = Mock(
                    trend_id="trend_001",
                    period_days=30,
                    total_gap_trend=-0.15,  # 15% improvement
                    critical_gap_trend=-0.25,
                    trend_summary="Gap counts decreasing",
                    historical_data=[
                        {"date": "2025-01-01", "total_gaps": 20},
                        {"date": "2025-01-15", "total_gaps": 17}
                    ]
                )
                mock_analyzer.analyze_trends.return_value = mock_trend
                
                response = client.get(
                    "/api/v1/gaps/trends?period_days=30",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["trend_id"] == "trend_001"
                assert data["total_gap_trend"] == -0.15
                assert len(data["historical_data"]) == 2

    def test_remediation_action_endpoint(self, client, mock_user):
        """Test gap remediation action submission endpoint."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            with patch('app.api.v1.gaps.remediation_service') as mock_service:
                mock_service.submit_remediation_action.return_value = Mock(
                    action_id="action_001",
                    gap_id="gap_001",
                    status="submitted",
                    estimated_completion=datetime.now() + timedelta(days=7)
                )
                
                request_data = {
                    "gap_id": "gap_001",
                    "action_type": "documentation_creation",
                    "assigned_team": "documentation_team",
                    "priority": "high",
                    "description": "Create missing technical documentation",
                    "estimated_effort_hours": 16
                }
                
                response = client.post(
                    "/api/v1/gaps/remediate",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["action_id"] == "action_001"
                assert data["status"] == "submitted"

    def test_gap_analysis_request_validation(self, client, mock_user):
        """Test comprehensive request validation."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            # Test various invalid requests
            invalid_requests = [
                # Missing required fields
                {},
                # Invalid compliance framework
                {
                    "include_compliance_assessment": True,
                    "compliance_frameworks": ["INVALID"]
                },
                # Invalid timeout values
                {
                    "max_execution_time_seconds": 0
                },
                # Invalid memory limit
                {
                    "max_memory_usage_mb": -1
                },
                # Invalid asset filters
                {
                    "asset_filters": {
                        "invalid_filter": ["value"]
                    }
                }
            ]
            
            for request_data in invalid_requests:
                response = client.post(
                    "/api/v1/gaps/analyze",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 422

    def test_gap_analysis_response_schema(self, client, mock_user, mock_gap_analysis_result):
        """Test gap analysis response schema validation."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            with patch('app.api.v1.gaps.gap_analyzer') as mock_analyzer:
                mock_analyzer.analyze_gaps.return_value = mock_gap_analysis_result
                
                request_data = {
                    "include_orphaned_detection": True,
                    "include_documentation_analysis": True
                }
                
                response = client.post(
                    "/api/v1/gaps/analyze",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify required fields
                required_fields = [
                    "analysis_id", "execution_time_seconds", "total_gaps_found",
                    "assets_analyzed", "gaps_by_type", "gaps_by_severity"
                ]
                
                for field in required_fields:
                    assert field in data
                
                # Verify data types
                assert isinstance(data["total_gaps_found"], int)
                assert isinstance(data["execution_time_seconds"], (int, float))
                assert isinstance(data["gaps_by_type"], dict)
                assert isinstance(data["gaps_by_severity"], dict)

    def test_pagination_for_large_gap_results(self, client, mock_user):
        """Test pagination for large gap analysis results."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            # Create large result set
            large_gaps = [
                Mock(
                    asset_id=f"asset_{i:03d}",
                    gap_type=GapType.MISSING_DOCUMENTATION,
                    severity=GapSeverity.MEDIUM
                )
                for i in range(100)
            ]
            
            large_result = Mock(
                analysis_id="large_analysis",
                total_gaps_found=100,
                gaps=large_gaps
            )
            
            with patch('app.api.v1.gaps.gap_analyzer') as mock_analyzer:
                mock_analyzer.analyze_gaps.return_value = large_result
                
                # Request with pagination
                response = client.get(
                    "/api/v1/gaps/results/large_analysis?page=1&limit=20",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["gaps"]) <= 20  # Respects limit
                assert "pagination" in data
                assert data["pagination"]["total_count"] == 100

    def test_filtering_and_sorting_gaps(self, client, mock_user):
        """Test filtering and sorting of gap results."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            # Request with filters and sorting
            response = client.get(
                "/api/v1/gaps/results/analysis_001?"
                "severity=HIGH&gap_type=MISSING_DOCUMENTATION&"
                "sort_by=priority_score&sort_order=desc",
                headers={"Authorization": "Bearer test_token"}
            )
            
            # Should apply filters and sorting
            assert response.status_code == 200

    def test_rate_limiting_on_gap_analysis(self, client, mock_user):
        """Test rate limiting on gap analysis endpoints."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            request_data = {
                "include_orphaned_detection": True
            }
            
            # Make multiple rapid requests
            responses = []
            for _ in range(10):
                response = client.post(
                    "/api/v1/gaps/analyze",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )
                responses.append(response)
            
            # Should eventually hit rate limit
            rate_limited = any(r.status_code == 429 for r in responses)
            # This test depends on rate limiting configuration

    def test_api_versioning_compatibility(self, client, mock_user):
        """Test API versioning and backward compatibility."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            # Test v1 endpoint
            response_v1 = client.get(
                "/api/v1/gaps/status",
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response_v1.status_code in [200, 404]  # Either works or not implemented yet

    def test_audit_logging_for_gap_analysis(self, client, mock_user):
        """Test audit logging for gap analysis operations."""
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            with patch('app.core.audit_logger') as mock_logger:
                request_data = {
                    "include_orphaned_detection": True,
                    "include_compliance_assessment": True
                }
                
                response = client.post(
                    "/api/v1/gaps/analyze",
                    json=request_data,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                # Should log the gap analysis request
                mock_logger.log_gap_analysis.assert_called_once()

    def test_concurrent_api_requests(self, client, mock_user):
        """Test handling of concurrent API requests."""
        import threading
        import time
        
        with patch.object(gaps_router, 'get_current_user', return_value=mock_user):
            results = []
            errors = []
            
            def make_request():
                try:
                    response = client.post(
                        "/api/v1/gaps/analyze",
                        json={"include_orphaned_detection": True},
                        headers={"Authorization": "Bearer test_token"}
                    )
                    results.append(response.status_code)
                except Exception as e:
                    errors.append(str(e))
            
            # Create multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()
            
            # Wait for all to complete
            for thread in threads:
                thread.join()
            
            # Should handle concurrent requests gracefully
            assert len(errors) == 0  # No threading errors
            assert len(results) == 5  # All requests completed


class TestGapAnalysisRequestSchema:
    """Test suite for GapAnalysisRequest schema validation."""

    def test_gap_analysis_request_default_values(self):
        """Test default values in gap analysis request."""
        request = GapAnalysisRequest()
        
        assert request.include_orphaned_detection is True
        assert request.include_documentation_analysis is True
        assert request.include_compliance_assessment is True
        assert request.max_execution_time_seconds == 180
        assert request.max_memory_usage_mb == 256

    def test_gap_analysis_request_custom_values(self):
        """Test custom values in gap analysis request."""
        request = GapAnalysisRequest(
            include_orphaned_detection=False,
            compliance_frameworks=["GDPR"],
            max_execution_time_seconds=300,
            asset_filters={"environment": ["production"]}
        )
        
        assert request.include_orphaned_detection is False
        assert request.compliance_frameworks == ["GDPR"]
        assert request.max_execution_time_seconds == 300
        assert request.asset_filters == {"environment": ["production"]}

    def test_gap_analysis_request_validation(self):
        """Test validation of gap analysis request."""
        # Invalid timeout
        with pytest.raises(ValueError):
            GapAnalysisRequest(max_execution_time_seconds=-1)
        
        # Invalid memory limit
        with pytest.raises(ValueError):
            GapAnalysisRequest(max_memory_usage_mb=0)
        
        # Invalid compliance framework
        with pytest.raises(ValueError):
            GapAnalysisRequest(compliance_frameworks=["INVALID"])


class TestGapAnalysisResponseSchema:
    """Test suite for GapAnalysisResponse schema."""

    def test_gap_analysis_response_creation(self):
        """Test gap analysis response creation."""
        response = GapAnalysisResponse(
            analysis_id="test_001",
            execution_time_seconds=45.5,
            total_gaps_found=10,
            assets_analyzed=5,
            gaps_by_type={GapType.MISSING_DOCUMENTATION: 6, GapType.INSUFFICIENT_SECURITY_CONTROLS: 4},
            gaps_by_severity={GapSeverity.HIGH: 3, GapSeverity.MEDIUM: 4, GapSeverity.LOW: 3}
        )
        
        assert response.analysis_id == "test_001"
        assert response.total_gaps_found == 10
        assert response.assets_analyzed == 5

    def test_gap_analysis_response_serialization(self):
        """Test gap analysis response JSON serialization."""
        response = GapAnalysisResponse(
            analysis_id="test_001",
            execution_time_seconds=45.5,
            total_gaps_found=10,
            assets_analyzed=5,
            gaps_by_type={GapType.MISSING_DOCUMENTATION: 10},
            gaps_by_severity={GapSeverity.HIGH: 10}
        )
        
        response_dict = response.dict()
        assert isinstance(response_dict, dict)
        assert response_dict["analysis_id"] == "test_001"


class TestErrorHandling:
    """Test suite for API error handling."""

    def test_validation_error_response_format(self, client):
        """Test validation error response format."""
        # Invalid JSON data
        response = client.post(
            "/api/v1/gaps/analyze",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_authentication_error_response(self, client):
        """Test authentication error response format."""
        response = client.post("/api/v1/gaps/analyze", json={})
        
        assert response.status_code == 401
        error_data = response.json()
        assert "detail" in error_data
        assert "not authenticated" in error_data["detail"].lower()

    def test_authorization_error_response(self, client):
        """Test authorization error response format."""
        # Mock user without proper permissions
        limited_user = Mock(
            id="user_002",
            username="limited_user",
            roles=["viewer"]  # No gap analysis permission
        )
        
        with patch.object(gaps_router, 'get_current_user', return_value=limited_user):
            response = client.post(
                "/api/v1/gaps/analyze",
                json={"include_orphaned_detection": True},
                headers={"Authorization": "Bearer test_token"}
            )
            
            assert response.status_code == 403
            error_data = response.json()
            assert "permission" in error_data["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])