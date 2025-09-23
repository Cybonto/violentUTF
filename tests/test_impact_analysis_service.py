# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Tests for impact analysis service."""

import pytest
import uuid
from unittest.mock import AsyncMock, patch

from violentutf_api.fastapi_app.app.services.impact_analysis import ImpactAnalysisService
from violentutf_api.fastapi_app.app.schemas.dependency import ChangeRequest, ImpactAnalysisResult


class TestImpactAnalysisService:
    """Test cases for ImpactAnalysisService."""
    
    @pytest.fixture
    def analysis_service(self):
        """Create impact analysis service instance."""
        return ImpactAnalysisService()
    
    @pytest.fixture
    def sample_change_request(self):
        """Sample change request for testing."""
        return ChangeRequest(
            change_type="schema_change",
            change_description="Add new table for dependency tracking",
            affected_components=["violentutf_api.db"],
            proposed_changes={
                "table": "dependency_relationships",
                "columns": ["id", "source_service", "target_database", "criticality"]
            },
            requestor="test-user",
            urgency="medium"
        )
    
    def test_service_initialization(self, analysis_service):
        """Test impact analysis service initialization."""
        assert analysis_service is not None
        assert hasattr(analysis_service, 'risk_factors')
        assert 'database_schema' in analysis_service.risk_factors
        assert 'critical_service' in analysis_service.risk_factors
        assert 'authentication' in analysis_service.risk_factors
    
    def test_risk_factors_configuration(self, analysis_service):
        """Test risk factors are properly configured."""
        risk_factors = analysis_service.risk_factors
        assert risk_factors['database_schema'] == 8
        assert risk_factors['critical_service'] == 7
        assert risk_factors['authentication'] == 9
        assert risk_factors['configuration'] == 5
        assert risk_factors['network'] == 6
    
    @pytest.mark.asyncio
    async def test_analyze_change_impact_schema_change(self, analysis_service, sample_change_request):
        """Test impact analysis for schema change."""
        with patch.object(analysis_service, '_get_affected_dependencies', return_value=[
            {
                'id': 'dep-001',
                'source_service': 'violentutf-api',
                'target_database': 'violentutf_api.db',
                'dependency_type': 'database',
                'criticality': 'critical'
            }
        ]):
            with patch.object(analysis_service, '_store_impact_analysis', new_callable=AsyncMock):
                result = await analysis_service.analyze_change_impact(sample_change_request)
                
                assert isinstance(result, ImpactAnalysisResult)
                assert result.analysis_id is not None
                assert result.change_request == sample_change_request
                assert result.risk_score >= 1 and result.risk_score <= 10
                assert len(result.affected_services) > 0
                assert len(result.affected_dependencies) > 0
                assert result.impact_severity in ['high', 'medium', 'low']
                assert result.rollback_complexity in ['high', 'medium', 'low']
                assert len(result.rollback_plan) > 0
                assert len(result.deployment_sequence) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_change_impact_service_change(self, analysis_service):
        """Test impact analysis for service change."""
        service_change_request = ChangeRequest(
            change_type="service_change",
            change_description="Update API endpoints",
            affected_components=["violentutf-api"],
            proposed_changes={"endpoints": ["/api/v1/new-endpoint"]},
            requestor="test-user",
            urgency="low"
        )
        
        with patch.object(analysis_service, '_get_affected_dependencies', return_value=[
            {
                'id': 'dep-002',
                'source_service': 'streamlit-app',
                'target_service': 'violentutf-api',
                'dependency_type': 'api',
                'criticality': 'high'
            }
        ]):
            with patch.object(analysis_service, '_store_impact_analysis', new_callable=AsyncMock):
                result = await analysis_service.analyze_change_impact(service_change_request)
                
                assert result.risk_score < 8  # Service changes should be lower risk than schema
                assert result.rollback_complexity == 'low'  # Service changes should be easier to rollback
                assert len(result.rollback_plan) >= 2  # Should have deployment and verification steps
    
    @pytest.mark.asyncio
    async def test_analyze_change_impact_critical_urgency(self, analysis_service):
        """Test impact analysis for critical urgency changes."""
        critical_change_request = ChangeRequest(
            change_type="security_change",
            change_description="Update authentication mechanism",
            affected_components=["keycloak", "violentutf-api"],
            proposed_changes={"auth_method": "oauth2"},
            requestor="security-team",
            urgency="critical"
        )
        
        with patch.object(analysis_service, '_get_affected_dependencies', return_value=[
            {
                'id': 'dep-003',
                'source_service': 'violentutf-api',
                'target_service': 'keycloak',
                'dependency_type': 'authentication',
                'criticality': 'critical'
            }
        ]):
            with patch.object(analysis_service, '_store_impact_analysis', new_callable=AsyncMock):
                result = await analysis_service.analyze_change_impact(critical_change_request)
                
                assert result.risk_score >= 8  # Critical security changes should be high risk
                assert "Critical urgency" in ' '.join(result.warnings)
                assert "Schedule during maintenance window" in result.recommendations
    
    @pytest.mark.asyncio
    async def test_get_affected_dependencies(self, analysis_service):
        """Test getting affected dependencies."""
        affected_components = ["violentutf_api.db", "keycloak.db"]
        
        dependencies = await analysis_service._get_affected_dependencies(affected_components)
        
        assert isinstance(dependencies, list)
        assert len(dependencies) == len(affected_components)
        for dep in dependencies:
            assert 'id' in dep
            assert 'source_service' in dep
            assert 'target_database' in dep
            assert 'dependency_type' in dep
            assert 'criticality' in dep
    
    @pytest.mark.asyncio
    async def test_calculate_risk_score_schema_change(self, analysis_service, sample_change_request):
        """Test risk score calculation for schema changes."""
        affected_dependencies = [
            {'criticality': 'critical'},
            {'criticality': 'high'},
            {'criticality': 'medium'}
        ]
        
        risk_score = await analysis_service._calculate_risk_score(
            sample_change_request, affected_dependencies
        )
        
        assert risk_score >= 7  # Schema changes should have higher base score
        assert risk_score <= 10  # Should not exceed maximum
    
    @pytest.mark.asyncio
    async def test_calculate_risk_score_low_risk_change(self, analysis_service):
        """Test risk score calculation for low-risk changes."""
        low_risk_request = ChangeRequest(
            change_type="configuration_change",
            change_description="Update log level",
            affected_components=["app_config"],
            proposed_changes={"log_level": "INFO"},
            requestor="dev-team",
            urgency="low"
        )
        
        affected_dependencies = [
            {'criticality': 'low'}
        ]
        
        risk_score = await analysis_service._calculate_risk_score(
            low_risk_request, affected_dependencies
        )
        
        assert risk_score <= 5  # Configuration changes should be lower risk
        assert risk_score >= 1  # Should not be below minimum
    
    @pytest.mark.asyncio
    async def test_identify_affected_services(self, analysis_service):
        """Test identifying affected services from dependencies."""
        dependencies = [
            {'source_service': 'streamlit-app', 'target_service': 'violentutf-api'},
            {'source_service': 'violentutf-api', 'target_database': 'violentutf_api.db'},
            {'source_service': 'keycloak', 'target_database': 'keycloak.db'}
        ]
        
        affected_services = await analysis_service._identify_affected_services(dependencies)
        
        assert isinstance(affected_services, list)
        assert 'streamlit-app' in affected_services
        assert 'violentutf-api' in affected_services
        assert 'keycloak' in affected_services
    
    @pytest.mark.asyncio
    async def test_generate_rollback_plan_schema_change(self, analysis_service, sample_change_request):
        """Test rollback plan generation for schema changes."""
        dependencies = [
            {'source_service': 'violentutf-api', 'target_database': 'violentutf_api.db'}
        ]
        
        rollback_plan = await analysis_service._generate_rollback_plan(
            sample_change_request, dependencies
        )
        
        assert isinstance(rollback_plan, list)
        assert len(rollback_plan) >= 4  # Should have multiple steps for schema changes
        
        # Check for expected rollback steps
        step_actions = [step['action'] for step in rollback_plan]
        assert 'Stop application services' in step_actions
        assert 'Restore database backup' in step_actions
        assert 'Restart services' in step_actions
        assert 'Verify functionality' in step_actions
        
        # Check step ordering
        assert rollback_plan[0]['step'] == 1
        assert rollback_plan[-1]['step'] == len(rollback_plan)
    
    @pytest.mark.asyncio
    async def test_generate_rollback_plan_service_change(self, analysis_service):
        """Test rollback plan generation for service changes."""
        service_change_request = ChangeRequest(
            change_type="service_change",
            change_description="Deploy new API version",
            affected_components=["violentutf-api"],
            proposed_changes={"version": "v2.0"},
            requestor="dev-team",
            urgency="medium"
        )
        
        dependencies = [
            {'source_service': 'streamlit-app', 'target_service': 'violentutf-api'}
        ]
        
        rollback_plan = await analysis_service._generate_rollback_plan(
            service_change_request, dependencies
        )
        
        assert isinstance(rollback_plan, list)
        assert len(rollback_plan) >= 2  # Should have fewer steps for service changes
        
        # Check for expected rollback steps
        step_actions = [step['action'] for step in rollback_plan]
        assert 'Deploy previous version' in step_actions
        assert 'Verify deployment' in step_actions
    
    @pytest.mark.asyncio
    async def test_create_deployment_sequence_schema_change(self, analysis_service, sample_change_request):
        """Test deployment sequence creation for schema changes."""
        dependencies = [
            {'source_service': 'violentutf-api', 'target_database': 'violentutf_api.db'}
        ]
        
        deployment_sequence = await analysis_service._create_deployment_sequence(
            sample_change_request, dependencies
        )
        
        assert isinstance(deployment_sequence, list)
        assert len(deployment_sequence) >= 5  # Should have multiple steps for schema changes
        
        # Check for expected deployment steps
        step_actions = [step['action'] for step in deployment_sequence]
        assert 'Create database backup' in step_actions
        assert 'Stop dependent services' in step_actions
        assert 'Apply schema changes' in step_actions
        assert 'Start services' in step_actions
        assert 'Verify deployment' in step_actions
    
    def test_generate_recommendations_high_risk(self, analysis_service, sample_change_request):
        """Test recommendation generation for high-risk changes."""
        recommendations = analysis_service._generate_recommendations(sample_change_request, 9)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert 'Schedule during maintenance window' in recommendations
        assert 'Have senior engineer available during deployment' in recommendations
        assert 'Test migrations on staging environment first' in recommendations
    
    def test_generate_recommendations_medium_risk(self, analysis_service, sample_change_request):
        """Test recommendation generation for medium-risk changes."""
        recommendations = analysis_service._generate_recommendations(sample_change_request, 6)
        
        assert isinstance(recommendations, list)
        assert 'Schedule during low-traffic period' in recommendations
        assert 'Ensure backup procedures are tested' in recommendations
    
    def test_generate_recommendations_low_risk(self, analysis_service, sample_change_request):
        """Test recommendation generation for low-risk changes."""
        recommendations = analysis_service._generate_recommendations(sample_change_request, 3)
        
        assert isinstance(recommendations, list)
        assert 'Can be deployed during business hours' in recommendations
        assert 'Standard monitoring procedures sufficient' in recommendations
    
    def test_generate_warnings_critical_dependencies(self, analysis_service, sample_change_request):
        """Test warning generation for changes affecting critical dependencies."""
        dependencies = [
            {'criticality': 'critical'},
            {'criticality': 'critical'},
            {'criticality': 'high'}
        ]
        
        warnings = analysis_service._generate_warnings(sample_change_request, dependencies)
        
        assert isinstance(warnings, list)
        assert 'Change affects 2 critical dependencies' in warnings
        assert 'Database schema changes may require extended downtime' in warnings
    
    def test_generate_warnings_critical_urgency(self, analysis_service):
        """Test warning generation for critical urgency changes."""
        critical_change_request = ChangeRequest(
            change_type="service_change",
            change_description="Emergency fix",
            affected_components=["violentutf-api"],
            proposed_changes={"fix": "security_patch"},
            requestor="security-team",
            urgency="critical"
        )
        
        warnings = analysis_service._generate_warnings(critical_change_request, [])
        
        assert 'Critical urgency may limit testing time' in warnings
    
    def test_determine_impact_severity(self, analysis_service):
        """Test impact severity determination."""
        assert analysis_service._determine_impact_severity(9) == 'high'
        assert analysis_service._determine_impact_severity(6) == 'medium'
        assert analysis_service._determine_impact_severity(3) == 'low'
        assert analysis_service._determine_impact_severity(10) == 'high'
        assert analysis_service._determine_impact_severity(1) == 'low'
    
    def test_estimate_downtime(self, analysis_service, sample_change_request):
        """Test downtime estimation."""
        # Schema change with multiple services
        downtime = analysis_service._estimate_downtime(sample_change_request, ['service1', 'service2'])
        assert downtime == '10-20 minutes'
        
        # Service change with multiple services
        service_change_request = ChangeRequest(
            change_type="service_change",
            change_description="Update service",
            affected_components=["service1"],
            proposed_changes={},
            requestor="dev-team"
        )
        downtime = analysis_service._estimate_downtime(service_change_request, ['service1', 'service2', 'service3'])
        assert downtime == '5-10 minutes'
        
        # Change with few services
        downtime = analysis_service._estimate_downtime(service_change_request, ['service1'])
        assert downtime == '2-5 minutes'
        
        # Change with no affected services
        downtime = analysis_service._estimate_downtime(service_change_request, [])
        assert downtime is None
    
    def test_assess_rollback_complexity(self, analysis_service, sample_change_request):
        """Test rollback complexity assessment."""
        # Schema change should be high complexity
        complexity = analysis_service._assess_rollback_complexity(sample_change_request, [])
        assert complexity == 'high'
        
        # Service change with many dependencies should be medium complexity
        service_change_request = ChangeRequest(
            change_type="service_change",
            change_description="Update service",
            affected_components=["service1"],
            proposed_changes={},
            requestor="dev-team"
        )
        many_dependencies = [{'id': f'dep-{i}'} for i in range(7)]
        complexity = analysis_service._assess_rollback_complexity(service_change_request, many_dependencies)
        assert complexity == 'medium'
        
        # Service change with few dependencies should be low complexity
        few_dependencies = [{'id': 'dep-1'}, {'id': 'dep-2'}]
        complexity = analysis_service._assess_rollback_complexity(service_change_request, few_dependencies)
        assert complexity == 'low'
    
    @pytest.mark.asyncio
    async def test_store_impact_analysis(self, analysis_service, sample_change_request):
        """Test storing impact analysis record."""
        # Initialize database first
        from violentutf_api.fastapi_app.app.db.database import init_db
        await init_db()
        
        risk_score = 7
        affected_services = ['violentutf-api', 'streamlit-app']
        rollback_plan = [{'step': 1, 'action': 'Test action'}]
        deployment_sequence = [{'step': 1, 'action': 'Deploy change'}]
        
        # Test the actual implementation instead of mocking
        # Use a unique ID for each test run
        unique_analysis_id = f'test-analysis-{uuid.uuid4()}'
        
        try:
            await analysis_service._store_impact_analysis(
                analysis_id=unique_analysis_id,
                change_request=sample_change_request,
                risk_score=risk_score,
                affected_services=affected_services,
                rollback_plan=rollback_plan,
                deployment_sequence=deployment_sequence
            )
            # If we get here, the store was successful
            assert True
        except Exception as e:
            pytest.fail(f"Failed to store impact analysis: {e}")


if __name__ == "__main__":
    pytest.main([__file__])