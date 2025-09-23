# Issue #264 Test Specification: Database Dependency Mapping and Impact Analysis System

## Test Overview

This document defines comprehensive tests for the database dependency mapping and impact analysis system. Tests follow Test-Driven Development (TDD) principles with complete coverage of all functionality.

## Test Categories

### 1. Unit Tests

#### 1.1 Dependency Discovery Service Tests
- **test_discover_code_dependencies**: Validate static code analysis
- **test_discover_runtime_dependencies**: Test runtime tracing
- **test_map_service_dependencies**: Verify service mapping
- **test_update_dependency_matrix**: Test matrix updates

#### 1.2 Impact Analysis Engine Tests
- **test_analyze_change_impact**: Validate impact analysis
- **test_generate_rollback_plan**: Test rollback planning
- **test_calculate_risk_score**: Verify risk scoring
- **test_create_deployment_sequence**: Test deployment ordering

#### 1.3 Dependency Models Tests
- **test_dependency_relationship_model**: Model validation
- **test_service_health_model**: Health tracking model
- **test_impact_analysis_model**: Analysis model validation

### 2. Integration Tests

#### 2.1 Database Integration Tests
- **test_dependency_matrix_storage**: Database storage
- **test_cross_database_dependencies**: Multi-DB mapping
- **test_service_health_tracking**: Health monitoring

#### 2.2 API Integration Tests
- **test_dependency_endpoints**: All API endpoints
- **test_dependency_graph_generation**: Graph creation
- **test_impact_analysis_workflow**: End-to-end analysis

### 3. Performance Tests

#### 3.1 Discovery Performance Tests
- **test_large_codebase_discovery**: Scale testing
- **test_concurrent_discovery**: Parallel processing
- **test_memory_usage**: Resource consumption

#### 3.2 Analysis Performance Tests
- **test_complex_graph_analysis**: Large graph handling
- **test_real_time_monitoring**: Live monitoring performance

## Test Implementation

### Unit Test Files

#### tests/test_dependency_mapping_service.py
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from violentutf_api.fastapi_app.app.services.dependency_mapping import DependencyMappingService
from violentutf_api.fastapi_app.app.models.dependency import DatabaseDependency, ServiceDependency

class TestDependencyMappingService:
    @pytest.fixture
    def dependency_service(self):
        return DependencyMappingService()
    
    def test_discover_code_dependencies(self, dependency_service):
        """Test static code analysis for dependencies"""
        # Should discover SQLAlchemy imports, DuckDB connections, etc.
        pass
    
    def test_discover_runtime_dependencies(self, dependency_service):
        """Test runtime dependency tracing"""
        # Should monitor active database connections
        pass
    
    def test_map_service_dependencies(self, dependency_service):
        """Test service-to-service dependency mapping"""
        # Should map Streamlit->FastAPI, APISIX->Services, etc.
        pass
    
    def test_update_dependency_matrix(self, dependency_service):
        """Test dependency matrix updates"""
        # Should properly update matrix with new dependencies
        pass
```

#### tests/test_impact_analysis_service.py
```python
import pytest
from violentutf_api.fastapi_app.app.services.impact_analysis import ImpactAnalysisService
from violentutf_api.fastapi_app.app.schemas.dependency import ChangeRequest, ImpactAnalysis

class TestImpactAnalysisService:
    @pytest.fixture
    def analysis_service(self):
        return ImpactAnalysisService()
    
    def test_analyze_change_impact(self, analysis_service):
        """Test change impact analysis"""
        change_request = ChangeRequest(
            change_type="schema_change",
            affected_components=["violentutf_api.db"],
            description="Add new table for dependency tracking"
        )
        # Should return comprehensive impact analysis
        pass
    
    def test_generate_rollback_plan(self, analysis_service):
        """Test rollback plan generation"""
        # Should create step-by-step rollback procedures
        pass
    
    def test_calculate_risk_score(self, analysis_service):
        """Test risk score calculation"""
        # Should return risk score 1-10 based on impact severity
        pass
    
    def test_create_deployment_sequence(self, analysis_service):
        """Test deployment sequence optimization"""
        # Should order changes to minimize dependencies issues
        pass
```

#### tests/test_dependency_models.py
```python
import pytest
from violentutf_api.fastapi_app.app.models.dependency import (
    DatabaseDependency, ServiceDependency, DependencyType, CriticalityLevel
)

class TestDependencyModels:
    def test_database_dependency_model(self):
        """Test DatabaseDependency model validation"""
        dependency = DatabaseDependency(
            source_service="violentutf-api",
            target_database="violentutf_api.db",
            dependency_type=DependencyType.DATABASE,
            criticality=CriticalityLevel.CRITICAL
        )
        assert dependency.source_service == "violentutf-api"
        assert dependency.criticality == CriticalityLevel.CRITICAL
    
    def test_service_dependency_model(self):
        """Test ServiceDependency model validation"""
        service_dep = ServiceDependency(
            service_name="streamlit-app",
            dependent_services=["violentutf-api"],
            database_connections=["violentutf_api.db"]
        )
        assert "violentutf-api" in service_dep.dependent_services
    
    def test_dependency_type_enum(self):
        """Test DependencyType enumeration"""
        assert DependencyType.DATABASE == "database"
        assert DependencyType.SERVICE == "service"
        assert DependencyType.API == "api"
```

### Integration Test Files

#### tests/api_tests/test_dependency_endpoints.py
```python
import pytest
from fastapi.testclient import TestClient
from violentutf_api.fastapi_app.main import app

class TestDependencyEndpoints:
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_get_dependency_matrix(self, client):
        """Test dependency matrix endpoint"""
        response = client.get("/api/v1/dependencies/matrix")
        assert response.status_code == 200
        assert "dependencies" in response.json()
    
    def test_get_dependency_graph(self, client):
        """Test dependency graph endpoint"""
        response = client.get("/api/v1/dependencies/graph")
        assert response.status_code == 200
        assert "nodes" in response.json()
        assert "edges" in response.json()
    
    def test_trigger_dependency_discovery(self, client):
        """Test dependency discovery trigger"""
        response = client.post("/api/v1/dependencies/discover")
        assert response.status_code == 200
        assert "discovery_id" in response.json()
    
    def test_analyze_change_impact(self, client):
        """Test change impact analysis endpoint"""
        change_request = {
            "change_type": "schema_change",
            "affected_components": ["violentutf_api.db"],
            "description": "Add dependency tracking table"
        }
        response = client.post("/api/v1/dependencies/analyze-change", json=change_request)
        assert response.status_code == 200
        assert "impact_score" in response.json()
    
    def test_get_system_health(self, client):
        """Test system health endpoint"""
        response = client.get("/api/v1/dependencies/health")
        assert response.status_code == 200
        assert "overall_health" in response.json()
```

#### tests/test_dependency_database_integration.py
```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from violentutf_api.fastapi_app.app.db.database import get_db_session
from violentutf_api.fastapi_app.app.models.dependency import DependencyRelationship

class TestDependencyDatabaseIntegration:
    @pytest.mark.asyncio
    async def test_store_dependency_relationship(self):
        """Test storing dependency relationships in database"""
        async with get_db_session() as session:
            dependency = DependencyRelationship(
                source_service="streamlit-app",
                target_database="violentutf_api.db",
                dependency_type="database",
                criticality="critical"
            )
            session.add(dependency)
            await session.commit()
            
            # Verify storage
            stored = await session.get(DependencyRelationship, dependency.id)
            assert stored is not None
            assert stored.source_service == "streamlit-app"
    
    @pytest.mark.asyncio
    async def test_query_dependencies_by_service(self):
        """Test querying dependencies for specific service"""
        # Should return all dependencies for a given service
        pass
    
    @pytest.mark.asyncio
    async def test_update_dependency_health_status(self):
        """Test updating service health status"""
        # Should update health status and timestamps
        pass
```

### Performance Test Files

#### tests/test_dependency_performance.py
```python
import pytest
import time
from unittest.mock import Mock
from violentutf_api.fastapi_app.app.services.dependency_mapping import DependencyMappingService

class TestDependencyPerformance:
    def test_large_codebase_discovery_performance(self):
        """Test performance with large codebase"""
        service = DependencyMappingService()
        start_time = time.time()
        
        # Mock large codebase analysis
        with Mock() as mock_analyzer:
            mock_analyzer.analyze_directory.return_value = ["file"] * 1000
            result = service.discover_code_dependencies()
        
        execution_time = time.time() - start_time
        assert execution_time < 30  # Should complete within 30 seconds
    
    def test_concurrent_discovery_performance(self):
        """Test concurrent dependency discovery"""
        # Should handle multiple parallel discovery requests
        pass
    
    def test_memory_usage_during_discovery(self):
        """Test memory consumption during discovery"""
        # Should not exceed reasonable memory limits
        pass
    
    def test_graph_analysis_performance(self):
        """Test performance of complex graph analysis"""
        # Should handle large dependency graphs efficiently
        pass
```

## Test Data Fixtures

### Mock Database Configurations
```python
# tests/conftest.py additions for dependency testing

@pytest.fixture
def mock_database_connections():
    return {
        "violentutf_api": "sqlite+aiosqlite:///./app_data/violentutf_api.db",
        "keycloak": "postgresql://keycloak:password@localhost:5432/keycloak",
        "pyrit_memory": "duckdb:///./app_data/violentutf/pyrit_memory_*.db"
    }

@pytest.fixture
def mock_service_registry():
    return {
        "streamlit-app": {"port": 8501, "health_endpoint": "/health"},
        "fastapi-app": {"port": 8000, "health_endpoint": "/health"},
        "keycloak": {"port": 8080, "health_endpoint": "/health"},
        "apisix": {"port": 9080, "health_endpoint": "/apisix/status"}
    }

@pytest.fixture
def sample_dependency_graph():
    return {
        "nodes": [
            {"id": "streamlit-app", "type": "service"},
            {"id": "fastapi-app", "type": "service"},
            {"id": "violentutf_api.db", "type": "database"},
            {"id": "keycloak", "type": "service"},
            {"id": "keycloak.db", "type": "database"}
        ],
        "edges": [
            {"source": "streamlit-app", "target": "fastapi-app", "type": "api"},
            {"source": "fastapi-app", "target": "violentutf_api.db", "type": "database"},
            {"source": "streamlit-app", "target": "keycloak", "type": "authentication"},
            {"source": "keycloak", "target": "keycloak.db", "type": "database"}
        ]
    }
```

## Test Execution Strategy

### Phase 1: Unit Tests (Red Phase)
1. Create all unit test files with failing tests
2. Run tests to confirm RED state
3. Implement minimal code to pass tests (GREEN)
4. Refactor and optimize (REFACTOR)

### Phase 2: Integration Tests
1. Database integration tests
2. API endpoint tests with authentication
3. Cross-service dependency validation

### Phase 3: Performance Tests
1. Load testing with large datasets
2. Concurrent access testing
3. Memory and CPU usage validation

### Phase 4: End-to-End Testing
1. Full dependency discovery workflow
2. Complete impact analysis scenario
3. Real-world change impact validation

## Test Coverage Requirements

### Minimum Coverage Targets
- Unit Tests: 95% code coverage
- Integration Tests: 85% endpoint coverage
- Performance Tests: All critical paths
- E2E Tests: All major user workflows

### Coverage Validation
```bash
# Run with coverage reporting
pytest --cov=violentutf_api.fastapi_app.app.services.dependency_mapping --cov-report=html
pytest --cov=violentutf_api.fastapi_app.app.services.impact_analysis --cov-report=html
```

## Continuous Integration

### Test Automation
- All tests run on every commit
- Performance regression detection
- Coverage threshold enforcement
- Integration test environment validation

### Test Environment Requirements
- Docker containers for all services
- Test database isolation
- Mock external dependencies
- Automated test data setup/teardown