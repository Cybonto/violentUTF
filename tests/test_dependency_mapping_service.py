# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for dependency mapping service."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from violentutf_api.fastapi_app.app.services.dependency_mapping import DependencyMappingService
from violentutf_api.fastapi_app.app.models.dependency import (
    DependencyType,
    CriticalityLevel,
    HealthStatus,
    DiscoveryMethod
)
from violentutf_api.fastapi_app.app.schemas.dependency import DependencyDiscoveryConfig


class TestDependencyMappingService:
    """Test cases for DependencyMappingService."""
    
    @pytest.fixture
    def dependency_service(self):
        """Create dependency mapping service instance."""
        return DependencyMappingService()
    
    @pytest.fixture
    def sample_python_code(self):
        """Sample Python code with dependencies."""
        return '''
import sqlalchemy
from duckdb import connect
import requests
import streamlit as st

# Database connections
engine = sqlalchemy.create_engine("sqlite:///violentutf_api.db")
duck_conn = connect("./app_data/violentutf/memory.duckdb")

# API calls
response = requests.get("http://localhost:8000/api/v1/health")
keycloak_url = "http://localhost:8080/auth"

def get_data():
    return engine.execute("SELECT * FROM users")
'''
    
    @pytest.fixture
    def temp_python_file(self, sample_python_code):
        """Create temporary Python file with sample code."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(sample_python_code)
            f.flush()
            yield Path(f.name)
            Path(f.name).unlink()
    
    def test_service_initialization(self, dependency_service):
        """Test dependency mapping service initialization."""
        assert dependency_service is not None
        assert hasattr(dependency_service, 'service_registry')
        assert 'streamlit-app' in dependency_service.service_registry
        assert 'violentutf-api' in dependency_service.service_registry
        assert 'keycloak' in dependency_service.service_registry
        assert 'apisix' in dependency_service.service_registry
    
    def test_service_registry_configuration(self, dependency_service):
        """Test service registry has correct configuration."""
        streamlit_config = dependency_service.service_registry['streamlit-app']
        assert streamlit_config['port'] == 8501
        assert streamlit_config['health_endpoint'] == '/health'
        
        api_config = dependency_service.service_registry['violentutf-api']
        assert api_config['port'] == 8000
        assert api_config['health_endpoint'] == '/health'
    
    @pytest.mark.asyncio
    async def test_discover_all_dependencies_default_config(self, dependency_service):
        """Test discovering all dependencies with default configuration."""
        with patch.object(dependency_service, 'discover_code_dependencies', return_value=[]):
            with patch.object(dependency_service, 'discover_runtime_dependencies', return_value=[]):
                with patch.object(dependency_service, 'discover_configuration_dependencies', return_value=[]):
                    with patch.object(dependency_service, 'discover_service_health', return_value=None):
                        
                        result = await dependency_service.discover_all_dependencies()
                        
                        assert result.discovery_id is not None
                        assert result.status in ['completed', 'completed_with_errors']
                        assert result.started_at is not None
                        assert result.completed_at is not None
                        assert isinstance(result.discovered_dependencies, int)
    
    @pytest.mark.asyncio
    async def test_discover_all_dependencies_custom_config(self, dependency_service):
        """Test discovering dependencies with custom configuration."""
        config = DependencyDiscoveryConfig(
            discovery_methods=[DiscoveryMethod.CODE_ANALYSIS],
            scan_paths=['/test/path'],
            runtime_trace_duration=60
        )
        
        with patch.object(dependency_service, 'discover_code_dependencies', return_value=[{'test': 'dep'}]):
            result = await dependency_service.discover_all_dependencies(config)
            
            assert result.status in ['completed', 'completed_with_errors']
            assert 'code_analysis' in result.metadata['methods_used']
            assert result.metadata['scan_paths'] == ['/test/path']
    
    @pytest.mark.asyncio
    async def test_discover_code_dependencies_nonexistent_path(self, dependency_service):
        """Test code dependency discovery with non-existent path."""
        result = await dependency_service.discover_code_dependencies(['/nonexistent/path'])
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_analyze_python_file(self, dependency_service, temp_python_file):
        """Test analyzing Python file for dependencies."""
        dependencies = await dependency_service._analyze_python_file(temp_python_file)
        
        # Should find sqlalchemy dependency
        sqlalchemy_deps = [d for d in dependencies if d.get('target_service') == 'sqlalchemy']
        assert len(sqlalchemy_deps) > 0
        
        # Should find database dependencies
        db_deps = [d for d in dependencies if d.get('dependency_type') == DependencyType.DATABASE]
        assert len(db_deps) > 0
        
        # Check for SQLite dependency
        sqlite_deps = [d for d in dependencies if 'violentutf_api.db' in str(d.get('target_database', ''))]
        assert len(sqlite_deps) > 0
        
        # Check for DuckDB dependency
        duckdb_deps = [d for d in dependencies if 'duckdb' in str(d.get('target_database', ''))]
        assert len(duckdb_deps) > 0
    
    def test_get_service_from_path(self, dependency_service):
        """Test determining service name from file path."""
        # Test violentutf_api path
        api_path = Path('/project/violentutf_api/fastapi_app/main.py')
        assert dependency_service._get_service_from_path(api_path) == 'violentutf-api'
        
        # Test streamlit path
        streamlit_path = Path('/project/violentutf/Home.py')
        assert dependency_service._get_service_from_path(streamlit_path) == 'streamlit-app'
        
        # Test keycloak path
        keycloak_path = Path('/project/keycloak/config.py')
        assert dependency_service._get_service_from_path(keycloak_path) == 'keycloak'
        
        # Test unknown path
        unknown_path = Path('/project/other/file.py')
        assert dependency_service._get_service_from_path(unknown_path) == 'unknown-service'
    
    def test_assess_criticality(self, dependency_service):
        """Test criticality assessment for database dependencies."""
        # Critical dependencies
        assert dependency_service._assess_criticality('sqlite', 'violentutf_api.db') == CriticalityLevel.CRITICAL
        assert dependency_service._assess_criticality('postgresql', 'keycloak.db') == CriticalityLevel.CRITICAL
        
        # High criticality
        assert dependency_service._assess_criticality('sqlite', 'other.db') == CriticalityLevel.HIGH
        assert dependency_service._assess_criticality('postgresql', 'other.db') == CriticalityLevel.HIGH
        
        # Medium criticality
        assert dependency_service._assess_criticality('duckdb', 'memory.duckdb') == CriticalityLevel.MEDIUM
        
        # Low criticality
        assert dependency_service._assess_criticality('redis', 'cache.db') == CriticalityLevel.LOW
    
    def test_assess_service_criticality(self, dependency_service):
        """Test criticality assessment for service dependencies."""
        # Critical services
        assert dependency_service._assess_service_criticality('localhost:8000/api') == CriticalityLevel.CRITICAL
        assert dependency_service._assess_service_criticality('localhost:8080/keycloak') == CriticalityLevel.CRITICAL
        
        # High criticality
        assert dependency_service._assess_service_criticality('localhost:8501') == CriticalityLevel.HIGH
        
        # Medium criticality
        assert dependency_service._assess_service_criticality('external-service.com') == CriticalityLevel.MEDIUM
    
    def test_extract_service_name(self, dependency_service):
        """Test extracting service name from URL."""
        assert dependency_service._extract_service_name('localhost:8000/api') == 'violentutf-api'
        assert dependency_service._extract_service_name('localhost:8501') == 'streamlit-app'
        assert dependency_service._extract_service_name('localhost:8080/auth') == 'keycloak'
        assert dependency_service._extract_service_name('localhost:9080/status') == 'apisix'
        assert dependency_service._extract_service_name('external.com:3000') == 'external-service'
    
    def test_analyze_import_database_dependencies(self, dependency_service):
        """Test analyzing imports for database dependencies."""
        api_path = Path('/project/violentutf_api/main.py')
        
        # SQLAlchemy import
        sqlalchemy_dep = dependency_service._analyze_import('sqlalchemy', api_path)
        assert sqlalchemy_dep is not None
        assert sqlalchemy_dep['dependency_type'] == DependencyType.DATABASE
        assert sqlalchemy_dep['criticality'] == CriticalityLevel.CRITICAL
        
        # DuckDB import
        duckdb_dep = dependency_service._analyze_import('duckdb', api_path)
        assert duckdb_dep is not None
        assert duckdb_dep['dependency_type'] == DependencyType.DATABASE
        assert duckdb_dep['criticality'] == CriticalityLevel.HIGH
    
    def test_analyze_import_service_dependencies(self, dependency_service):
        """Test analyzing imports for service dependencies."""
        streamlit_path = Path('/project/violentutf/main.py')
        
        # Streamlit import
        streamlit_dep = dependency_service._analyze_import('streamlit', streamlit_path)
        assert streamlit_dep is not None
        assert streamlit_dep['dependency_type'] == DependencyType.SERVICE
        assert streamlit_dep['criticality'] == CriticalityLevel.HIGH
        
        # FastAPI import
        fastapi_dep = dependency_service._analyze_import('fastapi', streamlit_path)
        assert fastapi_dep is not None
        assert fastapi_dep['dependency_type'] == DependencyType.SERVICE
        assert fastapi_dep['criticality'] == CriticalityLevel.CRITICAL
    
    def test_analyze_import_api_dependencies(self, dependency_service):
        """Test analyzing imports for API dependencies."""
        api_path = Path('/project/violentutf_api/main.py')
        
        # Requests import
        requests_dep = dependency_service._analyze_import('requests', api_path)
        assert requests_dep is not None
        assert requests_dep['dependency_type'] == DependencyType.API
        assert requests_dep['criticality'] == CriticalityLevel.MEDIUM
        
        # Aiohttp import
        aiohttp_dep = dependency_service._analyze_import('aiohttp', api_path)
        assert aiohttp_dep is not None
        assert aiohttp_dep['dependency_type'] == DependencyType.API
        assert aiohttp_dep['criticality'] == CriticalityLevel.MEDIUM
    
    def test_analyze_import_auth_dependencies(self, dependency_service):
        """Test analyzing imports for authentication dependencies."""
        api_path = Path('/project/violentutf_api/main.py')
        
        # Keycloak import
        keycloak_dep = dependency_service._analyze_import('keycloak', api_path)
        assert keycloak_dep is not None
        assert keycloak_dep['dependency_type'] == DependencyType.AUTHENTICATION
        assert keycloak_dep['criticality'] == CriticalityLevel.CRITICAL
    
    def test_analyze_import_unknown_module(self, dependency_service):
        """Test analyzing imports for unknown modules."""
        api_path = Path('/project/violentutf_api/main.py')
        
        # Unknown module
        unknown_dep = dependency_service._analyze_import('unknown_module', api_path)
        assert unknown_dep is None
    
    @pytest.mark.asyncio
    async def test_discover_runtime_dependencies(self, dependency_service):
        """Test runtime dependency discovery."""
        with patch.object(dependency_service, '_store_dependency', new_callable=AsyncMock):
            dependencies = await dependency_service.discover_runtime_dependencies(60)
            
            assert isinstance(dependencies, list)
            assert len(dependencies) > 0
            
            # Check for expected runtime dependencies
            api_deps = [d for d in dependencies if d.get('target_service') == 'violentutf-api']
            assert len(api_deps) > 0
            
            db_deps = [d for d in dependencies if d.get('dependency_type') == DependencyType.DATABASE]
            assert len(db_deps) > 0
    
    @pytest.mark.asyncio
    async def test_discover_configuration_dependencies(self, dependency_service):
        """Test configuration dependency discovery."""
        scan_paths = ['/test/path']
        
        with patch.object(dependency_service, '_parse_yaml_config', return_value=[]):
            with patch.object(dependency_service, '_parse_json_config', return_value=[]):
                with patch.object(dependency_service, '_parse_env_config', return_value=[]):
                    with patch.object(dependency_service, '_parse_docker_compose', return_value=[]):
                        
                        dependencies = await dependency_service.discover_configuration_dependencies(scan_paths)
                        assert isinstance(dependencies, list)
    
    @pytest.mark.asyncio
    async def test_discover_service_health_success(self, dependency_service):
        """Test successful service health discovery."""
        mock_response = Mock()
        mock_response.status = 200
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response
            
            with patch.object(dependency_service, '_update_service_health', new_callable=AsyncMock) as mock_update:
                await dependency_service.discover_service_health(30)
                
                # Should have called update for each service
                assert mock_update.call_count == len(dependency_service.service_registry)
                
                # Check that healthy status was set
                for call in mock_update.call_args_list:
                    args, kwargs = call
                    assert kwargs['health_status'] == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_discover_service_health_failure(self, dependency_service):
        """Test service health discovery with failures."""
        with patch('aiohttp.ClientSession.get', side_effect=Exception("Connection failed")):
            with patch.object(dependency_service, '_update_service_health', new_callable=AsyncMock) as mock_update:
                await dependency_service.discover_service_health(30)
                
                # Should have called update for each service
                assert mock_update.call_count == len(dependency_service.service_registry)
                
                # Check that down status was set
                for call in mock_update.call_args_list:
                    args, kwargs = call
                    assert kwargs['health_status'] == HealthStatus.DOWN
                    assert 'Connection failed' in kwargs['error_message']
    
    @pytest.mark.asyncio
    async def test_store_dependency(self, dependency_service):
        """Test storing dependency in database."""
        mock_session = AsyncMock()
        
        dep_data = {
            'source_service': 'test-service',
            'target_database': 'test.db',
            'dependency_type': DependencyType.DATABASE,
            'criticality': CriticalityLevel.MEDIUM,
            'discovery_method': DiscoveryMethod.CODE_ANALYSIS,
            'metadata': {'test': 'data'}
        }
        
        await dependency_service._store_dependency(mock_session, dep_data)
        
        # Verify session.add was called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        
        # Check the dependency object that was added
        added_dependency = mock_session.add.call_args[0][0]
        assert added_dependency.source_service == 'test-service'
        assert added_dependency.target_database == 'test.db'
        assert added_dependency.dependency_type == DependencyType.DATABASE
    
    @pytest.mark.asyncio
    async def test_update_service_health_new_record(self, dependency_service):
        """Test updating service health for new service."""
        mock_session = AsyncMock()
        mock_session.get.return_value = None  # No existing record
        
        with patch('violentutf_api.fastapi_app.app.services.dependency_mapping.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            await dependency_service._update_service_health(
                service_name='test-service',
                health_status=HealthStatus.HEALTHY,
                response_time_ms=100,
                endpoint_url='http://test:8000/health'
            )
            
            # Should add new health record
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_service_health_existing_record(self, dependency_service):
        """Test updating service health for existing service."""
        mock_health_record = Mock()
        mock_session = AsyncMock()
        mock_session.get.return_value = mock_health_record
        
        with patch('violentutf_api.fastapi_app.app.services.dependency_mapping.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            await dependency_service._update_service_health(
                service_name='existing-service',
                health_status=HealthStatus.DEGRADED,
                response_time_ms=2000,
                error_message='Slow response'
            )
            
            # Should update existing record
            assert mock_health_record.health_status == HealthStatus.DEGRADED
            assert mock_health_record.response_time_ms == 2000
            assert mock_health_record.error_message == 'Slow response'
            
            # Should not add new record
            mock_session.add.assert_not_called()
            mock_session.commit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])