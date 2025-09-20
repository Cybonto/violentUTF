#!/usr/bin/env python3
"""
Simple validation test for Issue #284 implementation
Tests basic functionality without complex dependencies
"""

import pytest
import sys
import os

# Add the violentutf directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'violentutf'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'violentutf_api', 'fastapi_app'))

def test_dashboard_utils_import():
    """Test that dashboard utilities can be imported"""
    try:
        from violentutf.utils.dashboard_utils import calculate_asset_metrics
        assert callable(calculate_asset_metrics)
    except ImportError as e:
        pytest.fail(f"Failed to import dashboard_utils: {e}")

def test_visualization_utils_import():
    """Test that visualization utilities can be imported"""
    try:
        from violentutf.utils.visualization_utils import create_asset_type_chart
        assert callable(create_asset_type_chart)
    except ImportError as e:
        pytest.fail(f"Failed to import visualization_utils: {e}")

def test_api_client_import():
    """Test that API client can be imported"""
    try:
        from violentutf.utils.api_client import DashboardAPIClient
        assert DashboardAPIClient is not None
    except ImportError as e:
        pytest.fail(f"Failed to import api_client: {e}")

def test_dashboard_components_import():
    """Test that dashboard components can be imported"""
    try:
        from violentutf.components.dashboard_components import display_asset_details
        assert callable(display_asset_details)
    except ImportError as e:
        pytest.fail(f"Failed to import dashboard_components: {e}")

def test_calculate_asset_metrics():
    """Test asset metrics calculation"""
    from violentutf.utils.dashboard_utils import calculate_asset_metrics
    
    # Test with sample data
    sample_assets = [
        {'criticality_level': 'CRITICAL', 'risk_score': 20, 'compliance_score': 85},
        {'criticality_level': 'HIGH', 'risk_score': 15, 'compliance_score': 90},
        {'criticality_level': 'MEDIUM', 'risk_score': 10, 'compliance_score': 80}
    ]
    
    metrics = calculate_asset_metrics(sample_assets)
    
    assert metrics['total_assets'] == 3
    assert metrics['critical_assets'] == 1
    assert metrics['avg_risk_score'] == 15.0
    assert metrics['avg_compliance_score'] == 85.0

def test_asset_filtering():
    """Test asset filtering functionality"""
    from violentutf.utils.dashboard_utils import apply_asset_filters
    
    sample_assets = [
        {'asset_type': 'POSTGRESQL', 'environment': 'PRODUCTION', 'criticality_level': 'HIGH'},
        {'asset_type': 'SQLITE', 'environment': 'DEVELOPMENT', 'criticality_level': 'LOW'},
        {'asset_type': 'POSTGRESQL', 'environment': 'STAGING', 'criticality_level': 'MEDIUM'}
    ]
    
    filters = {
        'asset_types': ['POSTGRESQL'],
        'environments': ['PRODUCTION', 'STAGING']
    }
    
    filtered = apply_asset_filters(sample_assets, filters)
    
    assert len(filtered) == 2
    assert all(asset['asset_type'] == 'POSTGRESQL' for asset in filtered)

def test_risk_level_conversion():
    """Test risk score to risk level conversion"""
    from violentutf.utils.dashboard_utils import get_risk_level_from_score
    
    assert get_risk_level_from_score(25) == 'CRITICAL'
    assert get_risk_level_from_score(18) == 'VERY_HIGH'
    assert get_risk_level_from_score(12) == 'HIGH'
    assert get_risk_level_from_score(7) == 'MEDIUM'
    assert get_risk_level_from_score(3) == 'LOW'

def test_dashboard_api_client():
    """Test dashboard API client initialization"""
    from violentutf.utils.api_client import DashboardAPIClient
    
    client = DashboardAPIClient()
    assert client.base_url == "http://localhost:9080/api/v1"
    
    # Test getting metrics (should return mock data on connection failure)
    metrics = client.get_asset_inventory_metrics()
    assert 'total_assets' in metrics
    assert 'critical_assets' in metrics

def test_backend_service_imports():
    """Test that backend services can be imported"""
    try:
        from app.services.dashboard_metrics_service import DashboardMetricsService
        assert DashboardMetricsService is not None
    except ImportError as e:
        pytest.fail(f"Failed to import DashboardMetricsService: {e}")
    
    try:
        from app.services.risk_assessment_service import RiskAssessmentService
        assert RiskAssessmentService is not None
    except ImportError as e:
        pytest.fail(f"Failed to import RiskAssessmentService: {e}")
    
    try:
        from app.services.compliance_monitoring_service import ComplianceMonitoringService
        assert ComplianceMonitoringService is not None
    except ImportError as e:
        pytest.fail(f"Failed to import ComplianceMonitoringService: {e}")

def test_dashboard_endpoints_import():
    """Test that dashboard API endpoints can be imported"""
    try:
        from app.api.v1.dashboard import router
        assert router is not None
    except ImportError as e:
        pytest.fail(f"Failed to import dashboard API router: {e}")

def test_create_asset_type_chart():
    """Test asset type chart creation"""
    from violentutf.utils.visualization_utils import create_asset_type_chart
    
    sample_assets = [
        {'asset_type': 'POSTGRESQL'},
        {'asset_type': 'POSTGRESQL'},
        {'asset_type': 'SQLITE'},
        {'asset_type': 'DUCKDB'}
    ]
    
    fig = create_asset_type_chart(sample_assets)
    assert fig is not None
    assert len(fig.data) > 0

def test_compliance_metrics_calculation():
    """Test compliance metrics calculation"""
    from violentutf.utils.dashboard_utils import calculate_compliance_metrics
    
    sample_compliance = [
        {'overall_score': 85, 'compliant': True, 'gaps': []},
        {'overall_score': 75, 'compliant': False, 'gaps': [{'severity': 'HIGH'}]},
        {'overall_score': 90, 'compliant': True, 'gaps': []}
    ]
    
    metrics = calculate_compliance_metrics(sample_compliance)
    
    assert metrics['overall_compliance_score'] == 83.3  # (85+75+90)/3
    assert metrics['compliant_assets'] == 2
    assert metrics['high_priority_gaps'] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])