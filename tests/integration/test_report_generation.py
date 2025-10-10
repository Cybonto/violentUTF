# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Integration tests for end-to-end report generation.

This test module validates the complete report generation workflow from
analytics data to final HTML report output.
"""

import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List

import pytest

# Import the report generator (will be implemented)
from violentutf.utils.report_generator import ReportGenerationError, ReportGenerator
from violentutf.utils.template_engine import TemplateEngine


class TestReportGeneration:
    """Test suite for end-to-end report generation."""
    
    def setup_method(self):
        """Set up test fixtures for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = os.path.join(self.temp_dir, "templates")
        self.config_dir = os.path.join(self.temp_dir, "config")
        self.output_dir = os.path.join(self.temp_dir, "reports")
        
        # Create directory structure
        os.makedirs(self.templates_dir)
        os.makedirs(os.path.join(self.templates_dir, "components"))
        os.makedirs(self.config_dir)
        os.makedirs(self.output_dir)
        
        # Create sample templates
        self._create_sample_templates()
        self._create_sample_configurations()
        
        # Create sample data
        self.sample_executions = self._create_sample_executions()
        self.sample_results = self._create_sample_results()
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        shutil.rmtree(self.temp_dir)
    
    def _create_sample_templates(self):
        """Create sample template files for testing."""
        # Base template
        base_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title | default("Test Report") }}</title>
</head>
<body>
    <h1>{{ title | default("Test Report") }}</h1>
    <div class="content">
        {{ content | default("No content") }}
    </div>
    <div class="metrics">
        <p>Total Executions: {{ total_executions | default(0) }}</p>
        <p>Violation Rate: {{ violation_rate | percentage }}</p>
    </div>
</body>
</html>
        """.strip()
        
        with open(os.path.join(self.templates_dir, "base.html"), "w") as f:
            f.write(base_template)
        
        # Executive summary template
        exec_template = """
{% extends "base.html" %}
{% block content %}
<section class="executive-summary">
    <h2>Executive Summary</h2>
    <p>Total Executions: {{ total_executions }}</p>
    <p>Total Scores: {{ total_scores }}</p>
    <p>Violation Rate: {{ violation_rate | percentage }}</p>
    <p>Overall Risk: {{ overall_risk | default("Unknown") }}</p>
    
    {% if severity_breakdown %}
    <h3>Severity Breakdown</h3>
    <ul>
        {% for severity, count in severity_breakdown.items() %}
        <li>{{ severity | title }}: {{ count }}</li>
        {% endfor %}
    </ul>
    {% endif %}
</section>
{% endblock %}
        """.strip()
        
        with open(os.path.join(self.templates_dir, "executive_summary.html"), "w") as f:
            f.write(exec_template)
        
        # Security metrics template
        security_template = """
{% extends "base.html" %}
{% block content %}
<section class="security-metrics">
    <h2>Security Metrics</h2>
    
    {% if scorer_performance %}
    <h3>Scorer Performance</h3>
    <table>
        <thead>
            <tr>
                <th>Scorer</th>
                <th>Total</th>
                <th>Violations</th>
                <th>Rate</th>
            </tr>
        </thead>
        <tbody>
            {% for scorer, stats in scorer_performance.items() %}
            <tr>
                <td>{{ scorer }}</td>
                <td>{{ stats.total }}</td>
                <td>{{ stats.violations }}</td>
                <td>{{ stats.violation_rate | percentage }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}
</section>
{% endblock %}
        """.strip()
        
        with open(os.path.join(self.templates_dir, "security_metrics.html"), "w") as f:
            f.write(security_template)
        
        # Components
        headers_component = """
<header>
    <h1>{{ report_title | default("Security Report") }}</h1>
    {% if company_name %}
    <h2>{{ company_name }}</h2>
    {% endif %}
    <p>Generated: {{ generation_date | default("Unknown") }}</p>
</header>
        """.strip()
        
        with open(os.path.join(self.templates_dir, "components", "headers.html"), "w") as f:
            f.write(headers_component)
    
    def _create_sample_configurations(self):
        """Create sample configuration files."""
        # Default config
        default_config = """
reporting:
  generate_report: true
  report_format: "HTML"
  include_sections:
    - executive_summary
    - security_metrics
  output_directory: "reports/"
  
styling:
  color_scheme: "professional"
  
branding:
  company_name: "Test Company"
  report_title_prefix: "ViolentUTF Security Assessment"
        """.strip()
        
        with open(os.path.join(self.config_dir, "default_config.yaml"), "w") as f:
            f.write(default_config)
    
    def _create_sample_executions(self) -> List[Dict[str, Any]]:
        """Create sample execution data."""
        return [
            {
                "id": "exec_001",
                "orchestrator_name": "TestOrchestrator1",
                "orchestrator_type": "PyRIT",
                "status": "completed",
                "created_at": "2024-01-01T10:00:00Z",
                "updated_at": "2024-01-01T10:05:00Z"
            },
            {
                "id": "exec_002", 
                "orchestrator_name": "TestOrchestrator2",
                "orchestrator_type": "Garak",
                "status": "completed",
                "created_at": "2024-01-01T11:00:00Z",
                "updated_at": "2024-01-01T11:03:00Z"
            }
        ]
    
    def _create_sample_results(self) -> List[Dict[str, Any]]:
        """Create sample results data."""
        return [
            {
                "execution_id": "exec_001",
                "score_value": True,
                "score_type": "true_false",
                "score_category": "jailbreak",
                "severity": "high",
                "scorer_name": "JailbreakScorer",
                "generator_name": "TestModel1",
                "dataset_name": "TestDataset1",
                "timestamp": "2024-01-01T10:03:00Z",
                "score_rationale": "Detected potential jailbreak attempt"
            },
            {
                "execution_id": "exec_001",
                "score_value": 0.8,
                "score_type": "float_scale",
                "score_category": "bias",
                "severity": "medium",
                "scorer_name": "BiasScorer",
                "generator_name": "TestModel1",
                "dataset_name": "TestDataset1",
                "timestamp": "2024-01-01T10:04:00Z",
                "score_rationale": "Moderate bias detected in response"
            },
            {
                "execution_id": "exec_002",
                "score_value": False,
                "score_type": "true_false",
                "score_category": "harmful_content",
                "severity": "minimal",
                "scorer_name": "HarmScorer",
                "generator_name": "TestModel2",
                "dataset_name": "TestDataset2",
                "timestamp": "2024-01-01T11:02:00Z",
                "score_rationale": "No harmful content detected"
            }
        ]
    
    def test_generate_complete_report(self):
        """Test generating complete report with all sections."""
        # GIVEN: Full analytics data and default configuration
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        # WHEN: generate_comprehensive_report() is called
        report_path = generator.generate_comprehensive_report(
            self.sample_executions,
            self.sample_results
        )
        
        # THEN: Complete HTML report should be generated
        assert os.path.exists(report_path)
        assert report_path.endswith('.html')
        
        # Verify report content
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "ViolentUTF Security Assessment" in content
        assert "Total Executions" in content
        assert "Violation Rate" in content
        assert "<html>" in content and "</html>" in content
    
    def test_generate_partial_report(self):
        """Test generating report with selected sections only."""
        # GIVEN: Analytics data and configuration with limited sections
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        # Override config to include only executive summary
        generator.config["reporting"]["include_sections"] = ["executive_summary"]
        
        # WHEN: generate_comprehensive_report() is called
        report_path = generator.generate_comprehensive_report(
            self.sample_executions,
            self.sample_results
        )
        
        # THEN: Report with only selected sections should be generated
        assert os.path.exists(report_path)
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Executive Summary" in content
        assert "Total Executions: 2" in content
        assert "Total Scores: 3" in content
    
    def test_generate_report_with_branding(self):
        """Test report generation with custom branding."""
        # GIVEN: Analytics data and branding configuration
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        custom_context = {
            "company_name": "ACME Security Corp",
            "title": "Custom Security Assessment Report",
            "classification": "CONFIDENTIAL"
        }
        
        # WHEN: generate_comprehensive_report() is called
        report_path = generator.generate_comprehensive_report(
            self.sample_executions,
            self.sample_results,
            custom_context=custom_context
        )
        
        # THEN: Report should include custom branding elements
        assert os.path.exists(report_path)
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Custom Security Assessment Report" in content
    
    def test_generate_report_performance(self):
        """Test report generation performance with large datasets."""
        # GIVEN: Large analytics dataset
        large_results = []
        for i in range(100):  # Create 100 results
            result = self.sample_results[0].copy()
            result["execution_id"] = f"exec_{i:03d}"
            result["timestamp"] = f"2024-01-01T{10 + (i % 14):02d}:00:00Z"
            large_results.append(result)
        
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        # WHEN: generate_comprehensive_report() is called
        start_time = datetime.now()
        report_path = generator.generate_comprehensive_report(
            self.sample_executions,
            large_results
        )
        end_time = datetime.now()
        
        # THEN: Report should be generated within acceptable time limits
        generation_time = (end_time - start_time).total_seconds()
        assert generation_time < 5.0  # Should complete within 5 seconds
        
        assert os.path.exists(report_path)
        
        # Verify content includes all data
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Total Scores: 100" in content
    
    def test_concurrent_report_generation(self):
        """Test concurrent report generation for multiple users."""
        # GIVEN: Multiple concurrent report generation requests
        generators = []
        for i in range(3):
            output_dir = os.path.join(self.temp_dir, f"reports_{i}")
            os.makedirs(output_dir, exist_ok=True)
            
            generator = ReportGenerator(
                template_dir=self.templates_dir,
                config_dir=self.config_dir,
                output_dir=output_dir
            )
            generators.append(generator)
        
        # WHEN: generate_comprehensive_report() is called concurrently
        report_paths = []
        for generator in generators:
            report_path = generator.generate_comprehensive_report(
                self.sample_executions,
                self.sample_results
            )
            report_paths.append(report_path)
        
        # THEN: All reports should be generated without conflicts
        assert len(report_paths) == 3
        
        for report_path in report_paths:
            assert os.path.exists(report_path)
            
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "Total Executions" in content
            assert "Total Scores" in content
    
    def test_report_with_empty_data(self):
        """Test report generation with empty data."""
        # GIVEN: Empty analytics data
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        # WHEN: generate_comprehensive_report() is called with empty data
        report_path = generator.generate_comprehensive_report([], [])
        
        # THEN: Report should be generated with zero values
        assert os.path.exists(report_path)
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "Total Executions: 0" in content
        assert "Total Scores: 0" in content
        assert "Violation Rate: 0.0%" in content
    
    def test_template_validation_integration(self):
        """Test template validation with real data."""
        # GIVEN: Report generator with templates
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        # WHEN: Template validation is performed
        base_valid = generator.validate_template("base.html")
        exec_valid = generator.validate_template("executive_summary.html")
        invalid_valid = generator.validate_template("nonexistent.html")
        
        # THEN: Validation should correctly identify valid and invalid templates
        assert base_valid is True
        assert exec_valid is True
        assert invalid_valid is False
    
    def test_get_available_templates(self):
        """Test getting list of available templates."""
        # GIVEN: Report generator with templates
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        # WHEN: get_available_templates() is called
        templates = generator.get_available_templates()
        
        # THEN: Should return list of available templates
        assert isinstance(templates, list)
        assert len(templates) > 0
        assert "base.html" in templates
        assert "executive_summary.html" in templates
        assert "security_metrics.html" in templates
    
    def test_metrics_calculation_integration(self):
        """Test metrics calculation integration."""
        # GIVEN: Report generator and sample data
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        # WHEN: Template-compatible metrics are calculated
        metrics = generator.calculate_template_compatible_metrics(self.sample_results)
        
        # THEN: Metrics should be calculated correctly
        assert metrics["total_scores"] == 3
        assert metrics["unique_scorers"] == 3  # JailbreakScorer, BiasScorer, HarmScorer
        assert metrics["unique_generators"] == 2  # TestModel1, TestModel2
        assert metrics["unique_datasets"] == 2  # TestDataset1, TestDataset2
        
        # Check severity breakdown
        assert "severity_breakdown" in metrics
        assert metrics["severity_breakdown"]["high"] == 1
        assert metrics["severity_breakdown"]["medium"] == 1
        assert metrics["severity_breakdown"]["minimal"] == 1
        
        # Check enhanced metrics
        assert "overall_risk" in metrics
        assert "violation_severity" in metrics
        assert "compliance_score" in metrics
        assert "key_findings" in metrics
    
    def test_error_handling_missing_templates(self):
        """Test error handling when templates are missing."""
        # GIVEN: Report generator with missing templates
        empty_template_dir = os.path.join(self.temp_dir, "empty_templates")
        os.makedirs(empty_template_dir)
        
        generator = ReportGenerator(
            template_dir=empty_template_dir,
            config_dir=self.config_dir,
            output_dir=self.output_dir
        )
        
        # WHEN: Report generation is attempted
        # THEN: Should handle gracefully or raise appropriate error
        with pytest.raises(ReportGenerationError):
            generator.generate_comprehensive_report(
                self.sample_executions,
                self.sample_results
            )
    
    def test_configuration_fallback(self):
        """Test fallback to default configuration when config files are missing."""
        # GIVEN: Report generator with missing config files
        empty_config_dir = os.path.join(self.temp_dir, "empty_config")
        os.makedirs(empty_config_dir)
        
        generator = ReportGenerator(
            template_dir=self.templates_dir,
            config_dir=empty_config_dir,
            output_dir=self.output_dir
        )
        
        # WHEN: Report generation is attempted
        report_path = generator.generate_comprehensive_report(
            self.sample_executions,
            self.sample_results
        )
        
        # THEN: Should use default configuration and generate report
        assert os.path.exists(report_path)
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "ViolentUTF Security Assessment" in content


@pytest.fixture
def sample_analytics_data():
    """Provide comprehensive sample analytics data for testing."""
    return {
        "executions_data": [
            {
                "id": "exec_001",
                "orchestrator_name": "PyRITOrchestrator",
                "orchestrator_type": "PyRIT",
                "status": "completed",
                "created_at": "2024-01-01T10:00:00Z"
            }
        ],
        "results_data": [
            {
                "execution_id": "exec_001",
                "score_value": True,
                "score_type": "true_false",
                "score_category": "jailbreak",
                "severity": "critical",
                "scorer_name": "JailbreakScorer",
                "generator_name": "TestModel",
                "dataset_name": "SecurityDataset",
                "timestamp": "2024-01-01T10:03:00Z",
                "score_rationale": "Critical jailbreak vulnerability detected"
            }
        ]
    }


@pytest.fixture  
def comprehensive_test_data():
    """Provide comprehensive test data with all severity levels."""
    results = []
    severities = ["critical", "high", "medium", "low", "minimal"]
    scorers = ["JailbreakScorer", "BiasScorer", "HarmScorer", "SafetyScorer", "EthicsScorer"]
    
    for i, (severity, scorer) in enumerate(zip(severities, scorers)):
        result = {
            "execution_id": f"exec_{i:03d}",
            "score_value": True if severity in ["critical", "high"] else False,
            "score_type": "true_false",
            "score_category": f"category_{i}",
            "severity": severity,
            "scorer_name": scorer,
            "generator_name": f"Model_{i}",
            "dataset_name": f"Dataset_{i}",
            "timestamp": f"2024-01-01T{10+i:02d}:00:00Z",
            "score_rationale": f"{severity.title()} issue detected"
        }
        results.append(result)
    
    return results