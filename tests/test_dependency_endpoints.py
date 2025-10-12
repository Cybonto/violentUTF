# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for dependency API endpoints."""

import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Add the FastAPI app directory to Python path for relative imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'violentutf_api', 'fastapi_app'))

from main import app
from app.schemas.dependency import (
    ChangeRequest,
    DependencyDiscoveryConfig,
    DiscoveryMethod
)


class TestDependencyEndpoints:
    """Test cases for dependency API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def sample_change_request(self):
        """Sample change request for testing."""
        return {
            "change_type": "schema_change",
            "change_description": "Add dependency tracking table",
            "affected_components": ["violentutf_api.db"],
            "proposed_changes": {
                "table": "dependency_relationships",
                "columns": ["id", "source_service", "target_database"]
            },
            "requestor": "test-user",
            "urgency": "medium"
        }

    @pytest.fixture
    def sample_discovery_config(self):
        """Sample discovery configuration for testing."""
        return {
            "discovery_methods": ["code_analysis", "runtime_trace"],
            "scan_paths": ["./violentutf", "./violentutf_api"],
            "runtime_trace_duration": 300,
            "health_check_timeout": 30
        }

    def test_get_dependency_matrix(self, client):
        """Test dependency matrix endpoint."""
        response = client.get("/api/v1/dependencies/matrix")
        assert response.status_code == 200

        data = response.json()
        assert "matrix_version" in data
        assert "services" in data
        assert "databases" in data
        assert "dependencies" in data
        assert "service_health" in data
        assert "matrix_metadata" in data

        # Check expected services are included
        assert "streamlit-app" in data["services"]
        assert "violentutf-api" in data["services"]
        assert "keycloak" in data["services"]
        assert "apisix" in data["services"]

        # Check expected databases are included
        assert "violentutf_api.db" in data["databases"]
        assert "keycloak.db" in data["databases"]

    def test_get_dependency_graph(self, client):
        """Test dependency graph endpoint."""
        response = client.get("/api/v1/dependencies/graph")
        assert response.status_code == 200

        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "metadata" in data

        # Check nodes structure
        assert len(data["nodes"]) > 0
        for node in data["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "criticality" in node

        # Check edges structure
        assert len(data["edges"]) > 0
        for edge in data["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "type" in edge

        # Check metadata
        metadata = data["metadata"]
        assert "total_nodes" in metadata
        assert "total_edges" in metadata
        assert metadata["total_nodes"] == len(data["nodes"])
        assert metadata["total_edges"] == len(data["edges"])

    def test_trigger_dependency_discovery_default_config(self, client):
        """Test dependency discovery trigger with default configuration."""
        with patch('violentutf_api.fastapi_app.app.api.endpoints.dependencies.DependencyMappingService') as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            # Mock the discovery result
            mock_result = {
                "discovery_id": "test-discovery-123",
                "discovery_method": "code_analysis",
                "started_at": "2025-01-09T10:00:00Z",
                "completed_at": "2025-01-09T10:05:00Z",
                "status": "completed",
                "discovered_dependencies": 15,
                "new_dependencies": 5,
                "updated_dependencies": 2,
                "errors": [],
                "warnings": [],
                "metadata": {
                    "methods_used": ["code_analysis", "runtime_trace"],
                    "duration_seconds": 300
                }
            }
            mock_instance.discover_all_dependencies.return_value = mock_result

            response = client.post("/api/v1/dependencies/discover")
            assert response.status_code == 200

            data = response.json()
            assert "discovery_id" in data
            assert "status" in data
            assert "discovered_dependencies" in data
            assert data["discovery_id"] == "test-discovery-123"
            assert data["status"] == "completed"

    def test_trigger_dependency_discovery_custom_config(self, client, sample_discovery_config):
        """Test dependency discovery trigger with custom configuration."""
        with patch('violentutf_api.fastapi_app.app.api.endpoints.dependencies.DependencyMappingService') as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            mock_result = {
                "discovery_id": "test-discovery-456",
                "discovery_method": "code_analysis",
                "started_at": "2025-01-09T10:00:00Z",
                "completed_at": "2025-01-09T10:05:00Z",
                "status": "completed",
                "discovered_dependencies": 20,
                "new_dependencies": 8,
                "updated_dependencies": 3,
                "errors": [],
                "warnings": ["Some non-critical warnings"],
                "metadata": {
                    "methods_used": ["code_analysis", "runtime_trace"],
                    "scan_paths": ["./violentutf", "./violentutf_api"],
                    "duration_seconds": 300
                }
            }
            mock_instance.discover_all_dependencies.return_value = mock_result

            response = client.post("/api/v1/dependencies/discover", json=sample_discovery_config)
            assert response.status_code == 200

            data = response.json()
            assert data["discovery_id"] == "test-discovery-456"
            assert data["discovered_dependencies"] == 20
            assert data["new_dependencies"] == 8
            assert len(data["warnings"]) > 0

    def test_analyze_change_impact(self, client, sample_change_request):
        """Test change impact analysis endpoint."""
        with patch('violentutf_api.fastapi_app.app.api.endpoints.dependencies.ImpactAnalysisService') as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            # Mock the impact analysis result
            mock_result = {
                "analysis_id": "test-analysis-789",
                "change_request": sample_change_request,
                "risk_score": 7,
                "affected_services": ["violentutf-api", "streamlit-app"],
                "affected_dependencies": ["dep-001", "dep-002"],
                "impact_severity": "high",
                "estimated_downtime": "10-20 minutes",
                "rollback_complexity": "high",
                "rollback_plan": [
                    {"step": 1, "action": "Stop application services", "estimated_time": "2 minutes"},
                    {"step": 2, "action": "Restore database backup", "estimated_time": "10 minutes"}
                ],
                "deployment_sequence": [
                    {"step": 1, "action": "Create database backup", "estimated_time": "5 minutes"},
                    {"step": 2, "action": "Apply schema changes", "estimated_time": "3 minutes"}
                ],
                "recommendations": [
                    "Schedule during maintenance window",
                    "Test migrations on staging environment first"
                ],
                "warnings": [
                    "Change affects critical dependencies",
                    "Database schema changes may require extended downtime"
                ],
                "created_at": "2025-01-09T10:00:00Z"
            }
            mock_instance.analyze_change_impact.return_value = mock_result

            response = client.post("/api/v1/dependencies/analyze-change", json=sample_change_request)
            assert response.status_code == 200

            data = response.json()
            assert "analysis_id" in data
            assert "risk_score" in data
            assert "affected_services" in data
            assert "rollback_plan" in data
            assert "deployment_sequence" in data
            assert "recommendations" in data

            assert data["analysis_id"] == "test-analysis-789"
            assert data["risk_score"] == 7
            assert "violentutf-api" in data["affected_services"]
            assert len(data["rollback_plan"]) >= 2
            assert len(data["deployment_sequence"]) >= 2
            assert len(data["recommendations"]) > 0

    def test_get_system_health(self, client):
        """Test system health endpoint."""
        response = client.get("/api/v1/dependencies/health")
        assert response.status_code == 200

        data = response.json()
        assert "overall_health" in data
        assert "total_services" in data
        assert "healthy_services" in data
        assert "degraded_services" in data
        assert "down_services" in data
        assert "critical_dependencies_healthy" in data
        assert "total_critical_dependencies" in data
        assert "services_status" in data
        assert "issues" in data

        # Check health status is valid
        assert data["overall_health"] in ["healthy", "degraded", "down", "unknown"]

        # Check counts are non-negative
        assert data["total_services"] >= 0
        assert data["healthy_services"] >= 0
        assert data["degraded_services"] >= 0
        assert data["down_services"] >= 0

        # Check services_status is a list
        assert isinstance(data["services_status"], list)
        assert isinstance(data["issues"], list)

    def test_list_dependencies_no_filters(self, client):
        """Test listing dependencies without filters."""
        response = client.get("/api/v1/dependencies/dependencies")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check dependency structure if any exist
        if len(data) > 0:
            for dependency in data:
                assert "id" in dependency
                assert "dependency_type" in dependency
                assert "criticality" in dependency
                # Should have either source_service or target_service
                assert "source_service" in dependency or "target_service" in dependency

    def test_list_dependencies_with_service_filter(self, client):
        """Test listing dependencies with service name filter."""
        response = client.get("/api/v1/dependencies/dependencies?service_name=violentutf-api")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check that all returned dependencies involve the specified service
        for dependency in data:
            involved_services = [
                dependency.get("source_service"),
                dependency.get("target_service")
            ]
            assert "violentutf-api" in involved_services

    def test_list_dependencies_with_type_filter(self, client):
        """Test listing dependencies with dependency type filter."""
        response = client.get("/api/v1/dependencies/dependencies?dependency_type=database")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check that all returned dependencies are of the specified type
        for dependency in data:
            assert dependency.get("dependency_type") == "database"

    def test_list_dependencies_with_multiple_filters(self, client):
        """Test listing dependencies with multiple filters."""
        response = client.get(
            "/api/v1/dependencies/dependencies?service_name=violentutf-api&dependency_type=database"
        )
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)

        # Check that all returned dependencies match both filters
        for dependency in data:
            assert dependency.get("dependency_type") == "database"
            involved_services = [
                dependency.get("source_service"),
                dependency.get("target_service")
            ]
            assert "violentutf-api" in involved_services

    def test_analyze_change_impact_invalid_request(self, client):
        """Test change impact analysis with invalid request."""
        invalid_request = {
            "change_type": "invalid_type",
            "change_description": "Test change",
            "affected_components": [],
            "proposed_changes": {},
            "requestor": "test-user"
        }

        response = client.post("/api/v1/dependencies/analyze-change", json=invalid_request)
        assert response.status_code == 422  # Validation error

    def test_dependency_discovery_error_handling(self, client):
        """Test dependency discovery error handling."""
        with patch('violentutf_api.fastapi_app.app.api.endpoints.dependencies.DependencyMappingService') as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            # Mock an exception during discovery
            mock_instance.discover_all_dependencies.side_effect = Exception("Discovery failed")

            response = client.post("/api/v1/dependencies/discover")
            assert response.status_code == 500

            data = response.json()
            assert "detail" in data
            assert "Discovery failed" in data["detail"]

    def test_impact_analysis_error_handling(self, client, sample_change_request):
        """Test impact analysis error handling."""
        with patch('violentutf_api.fastapi_app.app.api.endpoints.dependencies.ImpactAnalysisService') as mock_service:
            mock_instance = AsyncMock()
            mock_service.return_value = mock_instance

            # Mock an exception during analysis
            mock_instance.analyze_change_impact.side_effect = Exception("Analysis failed")

            response = client.post("/api/v1/dependencies/analyze-change", json=sample_change_request)
            assert response.status_code == 500

            data = response.json()
            assert "detail" in data
            assert "Analysis failed" in data["detail"]

    def test_api_endpoints_authentication_required(self, client):
        """Test that API endpoints require authentication (if enabled)."""
        # This test would check authentication requirements
        # For now, just verify endpoints are accessible
        # In production, these should require JWT authentication

        endpoints = [
            "/api/v1/dependencies/matrix",
            "/api/v1/dependencies/graph",
            "/api/v1/dependencies/health",
            "/api/v1/dependencies/dependencies"
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should be either 200 (no auth required) or 401/403 (auth required)
            assert response.status_code in [200, 401, 403]

    def test_api_response_content_type(self, client):
        """Test that API endpoints return proper content type."""
        endpoints = [
            "/api/v1/dependencies/matrix",
            "/api/v1/dependencies/graph",
            "/api/v1/dependencies/health",
            "/api/v1/dependencies/dependencies"
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code == 200:
                assert response.headers["content-type"] == "application/json"


if __name__ == "__main__":
    pytest.main([__file__])
