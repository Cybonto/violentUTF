# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for dependency mapping models."""

import pytest
import uuid
from datetime import datetime, UTC

from violentutf_api.fastapi_app.app.models.dependency import (
    DependencyRelationship,
    ServiceHealth,
    ImpactAnalysisRecord,
    DependencyMatrix,
    DependencyType,
    CriticalityLevel,
    HealthStatus,
    DiscoveryMethod
)


class TestDependencyEnums:
    """Test dependency enumeration classes."""
    
    def test_dependency_type_enum(self):
        """Test DependencyType enumeration values."""
        assert DependencyType.DATABASE.value == "database"
        assert DependencyType.SERVICE.value == "service"
        assert DependencyType.API.value == "api"
        assert DependencyType.AUTHENTICATION.value == "authentication"
        assert DependencyType.CONFIGURATION.value == "configuration"
        assert DependencyType.NETWORK.value == "network"
    
    def test_criticality_level_enum(self):
        """Test CriticalityLevel enumeration values."""
        assert CriticalityLevel.CRITICAL.value == "critical"
        assert CriticalityLevel.HIGH.value == "high"
        assert CriticalityLevel.MEDIUM.value == "medium"
        assert CriticalityLevel.LOW.value == "low"
    
    def test_health_status_enum(self):
        """Test HealthStatus enumeration values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.DOWN.value == "down"
        assert HealthStatus.UNKNOWN.value == "unknown"
    
    def test_discovery_method_enum(self):
        """Test DiscoveryMethod enumeration values."""
        assert DiscoveryMethod.CODE_ANALYSIS.value == "code_analysis"
        assert DiscoveryMethod.RUNTIME_TRACE.value == "runtime_trace"
        assert DiscoveryMethod.CONFIGURATION_SCAN.value == "configuration_scan"
        assert DiscoveryMethod.MANUAL.value == "manual"
        assert DiscoveryMethod.HEALTH_CHECK.value == "health_check"


class TestDependencyRelationshipModel:
    """Test DependencyRelationship model."""
    
    def test_dependency_relationship_creation(self):
        """Test creating a dependency relationship."""
        dep_id = str(uuid.uuid4())
        dependency = DependencyRelationship(
            id=dep_id,
            source_service="violentutf-api",
            target_database="violentutf_api.db",
            dependency_type=DependencyType.DATABASE,
            criticality=CriticalityLevel.CRITICAL,
            discovery_method=DiscoveryMethod.CODE_ANALYSIS
        )
        
        assert dependency.id == dep_id
        assert dependency.source_service == "violentutf-api"
        assert dependency.target_database == "violentutf_api.db"
        assert dependency.dependency_type == DependencyType.DATABASE
        assert dependency.criticality == CriticalityLevel.CRITICAL
        assert dependency.discovery_method == DiscoveryMethod.CODE_ANALYSIS
    
    def test_dependency_relationship_with_service_target(self):
        """Test dependency relationship with service target."""
        dep_id = str(uuid.uuid4())
        dependency = DependencyRelationship(
            id=dep_id,
            source_service="streamlit-app",
            target_service="violentutf-api",
            dependency_type=DependencyType.API,
            criticality=CriticalityLevel.HIGH,
            discovery_method=DiscoveryMethod.RUNTIME_TRACE
        )
        
        assert dependency.source_service == "streamlit-app"
        assert dependency.target_service == "violentutf-api"
        assert dependency.target_database is None
        assert dependency.dependency_type == DependencyType.API
    
    def test_dependency_relationship_with_metadata(self):
        """Test dependency relationship with metadata."""
        dep_id = str(uuid.uuid4())
        metadata = '{"endpoint": "/api/v1/test", "method": "GET"}'
        
        dependency = DependencyRelationship(
            id=dep_id,
            source_service="test-service",
            target_service="api-service",
            dependency_type=DependencyType.API,
            criticality=CriticalityLevel.MEDIUM,
            discovery_method=DiscoveryMethod.CODE_ANALYSIS,
            metadata=metadata
        )
        
        assert dependency.metadata == metadata
    
    def test_dependency_relationship_repr(self):
        """Test string representation of dependency relationship."""
        dep_id = str(uuid.uuid4())
        dependency = DependencyRelationship(
            id=dep_id,
            source_service="service-a",
            target_service="service-b",
            dependency_type=DependencyType.SERVICE,
            criticality=CriticalityLevel.LOW,
            discovery_method=DiscoveryMethod.MANUAL
        )
        
        repr_str = repr(dependency)
        assert "DependencyRelationship" in repr_str
        assert "service-a" in repr_str
        assert "service-b" in repr_str


class TestServiceHealthModel:
    """Test ServiceHealth model."""
    
    def test_service_health_creation(self):
        """Test creating a service health record."""
        health_id = str(uuid.uuid4())
        service_health = ServiceHealth(
            id=health_id,
            service_name="violentutf-api",
            health_status=HealthStatus.HEALTHY
        )
        
        assert service_health.id == health_id
        assert service_health.service_name == "violentutf-api"
        assert service_health.health_status == HealthStatus.HEALTHY
    
    def test_service_health_with_metrics(self):
        """Test service health with performance metrics."""
        health_id = str(uuid.uuid4())
        service_health = ServiceHealth(
            id=health_id,
            service_name="test-service",
            health_status=HealthStatus.HEALTHY,
            response_time_ms=150,
            endpoint_url="http://localhost:8000/health"
        )
        
        assert service_health.response_time_ms == 150
        assert service_health.endpoint_url == "http://localhost:8000/health"
    
    def test_service_health_degraded_with_error(self):
        """Test degraded service health with error message."""
        health_id = str(uuid.uuid4())
        service_health = ServiceHealth(
            id=health_id,
            service_name="failing-service",
            health_status=HealthStatus.DEGRADED,
            error_message="High response time detected",
            response_time_ms=5000
        )
        
        assert service_health.health_status == HealthStatus.DEGRADED
        assert service_health.error_message == "High response time detected"
        assert service_health.response_time_ms == 5000
    
    def test_service_health_repr(self):
        """Test string representation of service health."""
        health_id = str(uuid.uuid4())
        service_health = ServiceHealth(
            id=health_id,
            service_name="test-service",
            health_status=HealthStatus.DOWN
        )
        
        repr_str = repr(service_health)
        assert "ServiceHealth" in repr_str
        assert "test-service" in repr_str
        assert "down" in repr_str


class TestImpactAnalysisRecordModel:
    """Test ImpactAnalysisRecord model."""
    
    def test_impact_analysis_record_creation(self):
        """Test creating an impact analysis record."""
        analysis_id = str(uuid.uuid4())
        analysis = ImpactAnalysisRecord(
            id=analysis_id,
            change_description="Add new table for user preferences",
            proposed_changes='{"table": "user_preferences", "columns": ["id", "user_id", "preferences"]}',
            impact_assessment='{"affected_services": ["api"], "risk_level": "low"}',
            risk_score=3,
            created_by="test-user",
            implemented=False
        )
        
        assert analysis.id == analysis_id
        assert analysis.change_description == "Add new table for user preferences"
        assert analysis.risk_score == 3
        assert analysis.created_by == "test-user"
        assert analysis.implemented is False
    
    def test_impact_analysis_with_implementation(self):
        """Test impact analysis record after implementation."""
        analysis_id = str(uuid.uuid4())
        implementation_date = datetime.now(UTC)
        
        analysis = ImpactAnalysisRecord(
            id=analysis_id,
            change_description="Schema update",
            proposed_changes='{}',
            impact_assessment='{}',
            risk_score=5,
            created_by="admin",
            implemented=True,
            implementation_date=implementation_date,
            implementation_notes="Successfully deployed with no issues"
        )
        
        assert analysis.implemented is True
        assert analysis.implementation_date == implementation_date
        assert analysis.implementation_notes == "Successfully deployed with no issues"
    
    def test_impact_analysis_repr(self):
        """Test string representation of impact analysis."""
        analysis_id = str(uuid.uuid4())
        analysis = ImpactAnalysisRecord(
            id=analysis_id,
            change_description="Test change",
            proposed_changes='{}',
            impact_assessment='{}',
            risk_score=7,
            created_by="tester"
        )
        
        repr_str = repr(analysis)
        assert "ImpactAnalysis" in repr_str
        assert analysis_id in repr_str
        assert "pending" in repr_str
        assert "risk=7" in repr_str


class TestDependencyMatrixModel:
    """Test DependencyMatrix model."""
    
    def test_dependency_matrix_creation(self):
        """Test creating a dependency matrix record."""
        matrix_id = str(uuid.uuid4())
        matrix_data = '{"services": ["api", "web"], "dependencies": []}'
        services_snapshot = '["api", "web", "db"]'
        databases_snapshot = '["main.db", "cache.db"]'
        
        matrix = DependencyMatrix(
            id=matrix_id,
            matrix_version="v1.0.0",
            matrix_data=matrix_data,
            services_snapshot=services_snapshot,
            databases_snapshot=databases_snapshot,
            created_by="system",
            is_current=False
        )
        
        assert matrix.id == matrix_id
        assert matrix.matrix_version == "v1.0.0"
        assert matrix.matrix_data == matrix_data
        assert matrix.services_snapshot == services_snapshot
        assert matrix.databases_snapshot == databases_snapshot
        assert matrix.created_by == "system"
        assert matrix.is_current is False
    
    def test_dependency_matrix_current_version(self):
        """Test current dependency matrix version."""
        matrix_id = str(uuid.uuid4())
        
        matrix = DependencyMatrix(
            id=matrix_id,
            matrix_version="v2.0.0",
            matrix_data='{}',
            services_snapshot='[]',
            databases_snapshot='[]',
            created_by="admin",
            is_current=True
        )
        
        assert matrix.is_current is True
    
    def test_dependency_matrix_repr(self):
        """Test string representation of dependency matrix."""
        matrix_id = str(uuid.uuid4())
        matrix = DependencyMatrix(
            id=matrix_id,
            matrix_version="v1.5.0",
            matrix_data='{}',
            services_snapshot='[]',
            databases_snapshot='[]',
            created_by="test",
            is_current=True
        )
        
        repr_str = repr(matrix)
        assert "DependencyMatrix" in repr_str
        assert "v1.5.0" in repr_str
        assert "(current)" in repr_str


if __name__ == "__main__":
    pytest.main([__file__])