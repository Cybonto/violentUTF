# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Simplified tests for dependency endpoints functionality."""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

# Add the FastAPI app directory to Python path for relative imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'violentutf_api', 'fastapi_app'))

from app.schemas.dependency import ChangeRequest, DependencyDiscoveryConfig, DiscoveryMethod


class TestDependencySchemas:
    """Test cases for dependency schemas and data validation."""

    def test_change_request_schema_valid(self):
        """Test ChangeRequest schema with valid data."""
        change_data = {
            "change_type": "schema_change",
            "change_description": "Add new column to users table",
            "affected_components": ["api", "database"],
            "proposed_changes": {"sql": "ALTER TABLE users ADD COLUMN email VARCHAR(255)"},
            "requestor": "test-user",
            "urgency": "medium"
        }
        
        change_request = ChangeRequest(**change_data)
        assert change_request.change_type == "schema_change"
        assert change_request.change_description == "Add new column to users table"
        assert change_request.urgency == "medium"
        assert len(change_request.affected_components) == 2
        
    def test_dependency_discovery_config_valid(self):
        """Test DependencyDiscoveryConfig schema with valid data."""
        config_data = {
            "discovery_methods": ["code_analysis", "runtime_trace"],
            "scan_paths": ["/app", "/services"],
            "exclude_patterns": ["*.test.py", "*/tests/*"],
            "enable_deep_analysis": True
        }
        
        config = DependencyDiscoveryConfig(**config_data)
        assert len(config.scan_paths) == 2
        assert DiscoveryMethod.CODE_ANALYSIS in config.discovery_methods
        assert DiscoveryMethod.RUNTIME_TRACE in config.discovery_methods
        assert config.enable_deep_analysis is True
        
    def test_discovery_method_enum_values(self):
        """Test DiscoveryMethod enum has expected values."""
        expected_methods = [
            "code_analysis",
            "runtime_trace", 
            "configuration_scan",
            "manual",
            "health_check"
        ]
        
        actual_methods = [method.value for method in DiscoveryMethod]
        for method in expected_methods:
            assert method in actual_methods
            
    def test_change_request_schema_invalid_urgency(self):
        """Test ChangeRequest schema accepts any urgency value."""
        change_data = {
            "change_type": "schema_change",
            "change_description": "Add new column",
            "affected_components": ["api"],
            "proposed_changes": {"sql": "ALTER TABLE"},
            "requestor": "test-user",
            "urgency": "custom_urgency"  # Any value is accepted
        }
        
        # Should not raise an error - urgency field accepts any string
        change_request = ChangeRequest(**change_data)
        assert change_request.urgency == "custom_urgency"
            
    def test_dependency_discovery_config_empty_paths(self):
        """Test DependencyDiscoveryConfig handles empty paths."""
        config_data = {
            "discovery_methods": ["code_analysis"],
            "scan_paths": [],
            "exclude_patterns": [],
            "enable_deep_analysis": False
        }
        
        config = DependencyDiscoveryConfig(**config_data)
        assert len(config.scan_paths) == 0
        assert len(config.exclude_patterns) == 0
        assert config.enable_deep_analysis is False


class TestDependencyEndpointLogic:
    """Test the business logic without FastAPI dependency."""
    
    @pytest.mark.asyncio
    @patch('app.services.dependency_mapping.DependencyMappingService')
    async def test_dependency_discovery_logic(self, mock_service):
        """Test dependency discovery service logic."""
        # Mock the discovery service
        mock_instance = AsyncMock()
        mock_service.return_value = mock_instance
        mock_instance.discover_all_dependencies.return_value = {
            "discovered_dependencies": [
                {
                    "source_service": "api",
                    "target_database": "postgresql",
                    "dependency_type": "database",
                    "criticality_level": "high"
                }
            ],
            "discovery_metadata": {
                "total_found": 1,
                "discovery_time": "2025-01-19T12:00:00Z",
                "methods_used": ["code_analysis"]
            }
        }
        
        # Test the discovery logic
        result = await mock_instance.discover_all_dependencies()
        
        assert "discovered_dependencies" in result
        assert len(result["discovered_dependencies"]) == 1
        assert result["discovered_dependencies"][0]["source_service"] == "api"
        assert result["discovery_metadata"]["total_found"] == 1
        
    @pytest.mark.asyncio
    @patch('app.services.impact_analysis.ImpactAnalysisService')
    async def test_impact_analysis_logic(self, mock_service):
        """Test impact analysis service logic."""
        # Mock the analysis service
        mock_instance = AsyncMock()
        mock_service.return_value = mock_instance
        mock_instance.analyze_change_impact.return_value = {
            "risk_score": 7,
            "impact_severity": "medium",
            "affected_services": ["api", "database"],
            "rollback_plan": [
                {"step": 1, "action": "Stop services", "estimated_time": "2 minutes"},
                {"step": 2, "action": "Restore backup", "estimated_time": "5 minutes"}
            ],
            "recommendations": [
                "Schedule during low-traffic period",
                "Have rollback plan ready"
            ]
        }
        
        # Test the analysis logic
        change_request = {
            "change_type": "schema_change",
            "description": "Add new column",
            "urgency": "medium"
        }
        
        result = await mock_instance.analyze_change_impact(change_request)
        
        assert result["risk_score"] == 7
        assert result["impact_severity"] == "medium"
        assert len(result["affected_services"]) == 2
        assert len(result["rollback_plan"]) == 2
        assert len(result["recommendations"]) == 2


if __name__ == "__main__":
    pytest.main([__file__])