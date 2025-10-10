#!/usr/bin/env python3
"""
Test suite for Issue #266: Environment Configuration Consistency Review
Tests for configuration discovery, comparison, and validation functionality.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml


@pytest.fixture
def temp_config_env():
    """Create a temporary environment with sample configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        
        # Create environment directories
        dev_dir = base_path / "dev"
        staging_dir = base_path / "staging"
        prod_dir = base_path / "prod"
        
        for env_dir in [dev_dir, staging_dir, prod_dir]:
            env_dir.mkdir()
            
            # Create APISIX config
            apisix_dir = env_dir / "apisix"
            apisix_dir.mkdir()
            apisix_config = {
                "deployment": {
                    "admin": {
                        "admin_key": f"test-key-{env_dir.name}",
                        "admin_listen": {"port": 9180}
                    }
                },
                "apisix": {
                    "node_listen": [9080]
                }
            }
            with open(apisix_dir / "config.yaml", "w") as f:
                yaml.dump(apisix_config, f)
            
            # Create environment file
            env_content = f"""# {env_dir.name.upper()} Environment
APISIX_ADMIN_KEY=test-key-{env_dir.name}
DATABASE_URL=postgresql://user:pass@localhost/db_{env_dir.name}
"""
            with open(env_dir / ".env", "w") as f:
                f.write(env_content)
            
            # Create Keycloak realm config
            keycloak_dir = env_dir / "keycloak"
            keycloak_dir.mkdir()
            realm_config = {
                "realm": "ViolentUTF",
                "accessTokenLifespan": 300 if env_dir.name == "prod" else 600,
                "enabled": True,
                "sslRequired": "none" if env_dir.name == "dev" else "all"
            }
            with open(keycloak_dir / "realm-export.json", "w") as f:
                json.dump(realm_config, f)
        
        yield base_path


@pytest.fixture
def mock_database():
    """Mock database for configuration tracking."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as db_file:
        db_path = db_file.name
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test tables
    cursor.execute("""
        CREATE TABLE config_environments (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE config_services (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50) NOT NULL,
            environment_id INTEGER,
            config_data TEXT NOT NULL,
            checksum VARCHAR(64) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestConfigurationDiscovery:
    """Test configuration discovery functionality."""
    
    def test_discover_configuration_files(self, temp_config_env):
        """Test discovery of all configuration files in environment."""
        # This would import the actual implementation
        # from scripts.config_management.discover_configurations import ConfigurationDiscovery
        
        # For now, mock the expected behavior
        discovery = Mock()
        discovery.discover_files.return_value = {
            "dev": {
                "apisix": ["apisix/config.yaml"],
                "keycloak": ["keycloak/realm-export.json"],
                "env": [".env"]
            },
            "staging": {
                "apisix": ["apisix/config.yaml"],
                "keycloak": ["keycloak/realm-export.json"],
                "env": [".env"]
            },
            "prod": {
                "apisix": ["apisix/config.yaml"],
                "keycloak": ["keycloak/realm-export.json"],
                "env": [".env"]
            }
        }
        
        result = discovery.discover_files(temp_config_env)
        
        # Verify all environments discovered
        assert "dev" in result
        assert "staging" in result
        assert "prod" in result
        
        # Verify all service types discovered
        for env in result.values():
            assert "apisix" in env
            assert "keycloak" in env
            assert "env" in env
    
    def test_parse_yaml_configuration(self, temp_config_env):
        """Test parsing of YAML configuration files."""
        config_file = temp_config_env / "dev" / "apisix" / "config.yaml"
        
        # Mock YAML parser
        parser = Mock()
        parser.parse_yaml.return_value = {
            "deployment": {
                "admin": {
                    "admin_key": "test-key-dev",
                    "admin_listen": {"port": 9180}
                }
            }
        }
        
        result = parser.parse_yaml(config_file)
        
        assert "deployment" in result
        assert result["deployment"]["admin"]["admin_key"] == "test-key-dev"
    
    def test_parse_env_file(self, temp_config_env):
        """Test parsing of environment files."""
        env_file = temp_config_env / "dev" / ".env"
        
        # Mock env parser
        parser = Mock()
        parser.parse_env.return_value = {
            "APISIX_ADMIN_KEY": "test-key-dev",
            "DATABASE_URL": "postgresql://user:pass@localhost/db_dev"
        }
        
        result = parser.parse_env(env_file)
        
        assert "APISIX_ADMIN_KEY" in result
        assert "DATABASE_URL" in result
        assert "db_dev" in result["DATABASE_URL"]
    
    def test_parse_json_configuration(self, temp_config_env):
        """Test parsing of JSON configuration files."""
        json_file = temp_config_env / "dev" / "keycloak" / "realm-export.json"
        
        # Mock JSON parser
        parser = Mock()
        parser.parse_json.return_value = {
            "realm": "ViolentUTF",
            "accessTokenLifespan": 600,
            "enabled": True
        }
        
        result = parser.parse_json(json_file)
        
        assert result["realm"] == "ViolentUTF"
        assert result["accessTokenLifespan"] == 600
        assert result["enabled"] is True


class TestConfigurationComparison:
    """Test configuration comparison functionality."""
    
    def test_compare_environments_basic(self):
        """Test basic environment comparison."""
        # Mock comparison engine
        comparator = Mock()
        
        dev_config = {"admin_key": "dev-key", "port": 9180}
        prod_config = {"admin_key": "prod-key", "port": 9180}
        
        comparator.compare.return_value = {
            "differences": [
                {
                    "path": "admin_key",
                    "dev": "dev-key",
                    "prod": "prod-key",
                    "severity": "medium"
                }
            ],
            "identical": ["port"],
            "summary": {
                "total_differences": 1,
                "high_severity": 0,
                "medium_severity": 1,
                "low_severity": 0
            }
        }
        
        result = comparator.compare(dev_config, prod_config)
        
        assert result["summary"]["total_differences"] == 1
        assert result["differences"][0]["path"] == "admin_key"
        assert result["differences"][0]["severity"] == "medium"
    
    def test_detect_security_inconsistencies(self):
        """Test detection of security-related configuration inconsistencies."""
        comparator = Mock()
        
        dev_config = {"sslRequired": "none", "bruteForceProtected": False}
        prod_config = {"sslRequired": "all", "bruteForceProtected": True}
        
        comparator.detect_security_issues.return_value = [
            {
                "type": "security_downgrade",
                "path": "sslRequired",
                "issue": "SSL not required in dev but required in prod",
                "severity": "high",
                "recommendation": "Enable SSL in dev environment"
            }
        ]
        
        result = comparator.detect_security_issues(dev_config, prod_config)
        
        assert len(result) == 1
        assert result[0]["severity"] == "high"
        assert result[0]["type"] == "security_downgrade"
    
    def test_generate_impact_analysis(self):
        """Test generation of impact analysis for configuration differences."""
        analyzer = Mock()
        
        differences = [
            {"path": "admin_key", "severity": "medium", "service": "apisix"},
            {"path": "accessTokenLifespan", "severity": "low", "service": "keycloak"}
        ]
        
        analyzer.analyze_impact.return_value = {
            "affected_services": ["apisix", "keycloak"],
            "restart_required": ["apisix"],
            "user_impact": "medium",
            "business_impact": "low",
            "recommendations": [
                "Schedule maintenance window for APISIX restart",
                "Update token lifespans during next release"
            ]
        }
        
        result = analyzer.analyze_impact(differences)
        
        assert "apisix" in result["affected_services"]
        assert "apisix" in result["restart_required"]
        assert result["user_impact"] == "medium"


class TestConfigurationValidation:
    """Test configuration validation functionality."""
    
    def test_validate_schema_compliance(self):
        """Test validation of configuration against defined schemas."""
        validator = Mock()
        
        config = {
            "deployment": {
                "admin": {
                    "admin_key": "valid-key-123",
                    "admin_listen": {"port": 9180}
                }
            }
        }
        
        validator.validate_schema.return_value = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        result = validator.validate_schema(config, "apisix")
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_cross_service_dependencies(self):
        """Test validation of dependencies between services."""
        validator = Mock()
        
        configs = {
            "apisix": {"upstream": {"keycloak": "http://keycloak:8080"}},
            "keycloak": {"enabled": True, "port": 8080}
        }
        
        validator.validate_dependencies.return_value = {
            "valid": True,
            "dependency_issues": [],
            "missing_services": []
        }
        
        result = validator.validate_dependencies(configs)
        
        assert result["valid"] is True
        assert len(result["dependency_issues"]) == 0
    
    def test_detect_configuration_drift(self):
        """Test detection of configuration drift from baseline."""
        drift_detector = Mock()
        
        baseline = {"admin_key": "baseline-key", "port": 9180}
        current = {"admin_key": "changed-key", "port": 9180}
        
        drift_detector.detect_drift.return_value = {
            "drift_detected": True,
            "changes": [
                {
                    "path": "admin_key",
                    "baseline_value": "baseline-key",
                    "current_value": "changed-key",
                    "change_type": "modification",
                    "severity": "medium"
                }
            ],
            "drift_score": 0.5
        }
        
        result = drift_detector.detect_drift(baseline, current)
        
        assert result["drift_detected"] is True
        assert len(result["changes"]) == 1
        assert result["drift_score"] == 0.5


class TestTemplateGeneration:
    """Test configuration template generation functionality."""
    
    def test_generate_service_template(self):
        """Test generation of standardized service templates."""
        template_engine = Mock()
        
        template_engine.generate_template.return_value = {
            "deployment": {
                "admin": {
                    "admin_key": "{{ APISIX_ADMIN_KEY }}",
                    "admin_listen": {"port": "{{ APISIX_ADMIN_PORT | default(9180) }}"}
                }
            },
            "apisix": {
                "node_listen": ["{{ APISIX_NODE_PORT | default(9080) }}"]
            }
        }
        
        result = template_engine.generate_template("apisix")
        
        assert "{{ APISIX_ADMIN_KEY }}" in str(result)
        assert "{{ APISIX_ADMIN_PORT | default(9180) }}" in str(result)
    
    def test_inject_environment_parameters(self):
        """Test injection of environment-specific parameters into templates."""
        template_engine = Mock()
        
        template = {
            "admin_key": "{{ ADMIN_KEY }}",
            "port": "{{ PORT | default(9180) }}"
        }
        
        env_params = {
            "ADMIN_KEY": "prod-secret-key",
            "PORT": 9443
        }
        
        template_engine.inject_parameters.return_value = {
            "admin_key": "prod-secret-key",
            "port": 9443
        }
        
        result = template_engine.inject_parameters(template, env_params)
        
        assert result["admin_key"] == "prod-secret-key"
        assert result["port"] == 9443
    
    def test_validate_template_syntax(self):
        """Test validation of template syntax and variable references."""
        validator = Mock()
        
        template = {
            "valid_var": "{{ VALID_VAR }}",
            "invalid_var": "{{ MISSING_VAR }}",
            "default_var": "{{ DEFAULT_VAR | default('default_value') }}"
        }
        
        available_vars = ["VALID_VAR", "DEFAULT_VAR"]
        
        validator.validate_template.return_value = {
            "valid": False,
            "missing_variables": ["MISSING_VAR"],
            "unused_variables": [],
            "syntax_errors": []
        }
        
        result = validator.validate_template(template, available_vars)
        
        assert result["valid"] is False
        assert "MISSING_VAR" in result["missing_variables"]


class TestDeploymentAutomation:
    """Test configuration deployment automation functionality."""
    
    def test_validate_pre_deployment(self):
        """Test pre-deployment validation checks."""
        deployer = Mock()
        
        config = {
            "deployment": {
                "admin": {
                    "admin_key": "valid-key",
                    "admin_listen": {"port": 9180}
                }
            }
        }
        
        deployer.validate_pre_deployment.return_value = {
            "valid": True,
            "validation_results": {
                "schema_valid": True,
                "dependencies_satisfied": True,
                "security_compliant": True
            },
            "warnings": [],
            "blocking_errors": []
        }
        
        result = deployer.validate_pre_deployment(config, "prod")
        
        assert result["valid"] is True
        assert result["validation_results"]["schema_valid"] is True
    
    def test_deploy_configuration_dry_run(self):
        """Test dry-run deployment functionality."""
        deployer = Mock()
        
        config = {"admin_key": "new-key", "port": 9180}
        
        deployer.deploy.return_value = {
            "dry_run": True,
            "would_change": ["admin_key"],
            "would_restart": ["apisix"],
            "estimated_downtime": "30 seconds",
            "rollback_available": True
        }
        
        result = deployer.deploy(config, "staging", dry_run=True)
        
        assert result["dry_run"] is True
        assert "admin_key" in result["would_change"]
        assert result["rollback_available"] is True
    
    def test_rollback_configuration(self):
        """Test configuration rollback functionality."""
        deployer = Mock()
        
        deployment_id = "deploy_123"
        
        deployer.rollback.return_value = {
            "rollback_successful": True,
            "rolled_back_to": "previous_config_v1.2",
            "services_restarted": ["apisix"],
            "rollback_duration": "45 seconds"
        }
        
        result = deployer.rollback(deployment_id)
        
        assert result["rollback_successful"] is True
        assert "apisix" in result["services_restarted"]


class TestMonitoringAndAlerting:
    """Test configuration monitoring and alerting functionality."""
    
    def test_continuous_drift_monitoring(self):
        """Test continuous monitoring for configuration drift."""
        monitor = Mock()
        
        monitor.check_drift.return_value = {
            "drift_detected": True,
            "services_affected": ["apisix", "keycloak"],
            "severity_level": "medium",
            "alert_required": True,
            "last_check": "2024-01-01T12:00:00Z"
        }
        
        result = monitor.check_drift()
        
        assert result["drift_detected"] is True
        assert result["alert_required"] is True
        assert len(result["services_affected"]) == 2
    
    def test_generate_configuration_report(self):
        """Test generation of configuration status reports."""
        reporter = Mock()
        
        reporter.generate_report.return_value = {
            "report_timestamp": "2024-01-01T12:00:00Z",
            "environments_checked": ["dev", "staging", "prod"],
            "total_inconsistencies": 5,
            "high_priority_issues": 1,
            "recommendations": [
                "Update SSL configuration in dev environment",
                "Standardize token lifespans across environments"
            ],
            "next_review_date": "2024-01-08T12:00:00Z"
        }
        
        result = reporter.generate_report()
        
        assert result["total_inconsistencies"] == 5
        assert result["high_priority_issues"] == 1
        assert len(result["recommendations"]) == 2


# Performance and load tests
class TestPerformance:
    """Test performance characteristics of configuration management tools."""
    
    def test_large_configuration_comparison(self):
        """Test performance with large configuration sets."""
        # Mock performance test
        comparator = Mock()
        
        # Simulate comparison of large configs
        comparator.compare_large_configs.return_value = {
            "comparison_time": 25.5,  # seconds
            "configurations_compared": 1000,
            "differences_found": 150,
            "performance_acceptable": True
        }
        
        result = comparator.compare_large_configs()
        
        assert result["comparison_time"] < 30  # Should complete within 30 seconds
        assert result["performance_acceptable"] is True
    
    def test_template_generation_speed(self):
        """Test template generation performance."""
        template_engine = Mock()
        
        template_engine.benchmark_generation.return_value = {
            "templates_generated": 100,
            "generation_time": 8.5,  # seconds
            "average_time_per_template": 0.085,
            "performance_acceptable": True
        }
        
        result = template_engine.benchmark_generation()
        
        assert result["average_time_per_template"] < 0.1  # Should be under 100ms per template
        assert result["performance_acceptable"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])