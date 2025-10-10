# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Professional Jinja2-based template engine for ViolentUTF security reports.

This module provides comprehensive template rendering capabilities with security features,
configuration management, and integration with existing ViolentUTF analytics functions.
"""

import html
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import yaml
from jinja2 import (
    Environment,
    FileSystemLoader,
    Template,
    TemplateError,
    TemplateNotFound,
    Undefined,
    select_autoescape,
)

# Handle different Jinja2 versions for Markup import
try:
    from jinja2 import Markup  # type: ignore[attr-defined] # pylint: disable=unused-import
except ImportError:
    try:
        from markupsafe import Markup
    except ImportError:
        # Fallback for older versions
        class MarkupFallback(str):
            """Fallback Markup class for compatibility."""

            def __new__(cls, value: str) -> "MarkupFallback":
                """Create new MarkupFallback instance."""
                return str.__new__(cls, value)

        Markup = MarkupFallback
from jinja2.sandbox import SandboxedEnvironment

from violentutf.utils.logging import get_logger

logger = get_logger(__name__)


class TemplateValidationError(Exception):
    """Raised when template validation fails."""


class TemplateSecurityError(Exception):
    """Raised when template security validation fails."""


@dataclass
class TestResult:
    """Result object for template rendering tests."""

    success: bool
    is_valid: bool
    message: str
    rendered_output: Optional[str] = None
    errors: Optional[List[str]] = None


@dataclass
class ValidationResult:
    """Result object for template variable validation."""

    is_valid: bool
    missing_variables: List[str]
    extra_variables: List[str]
    warnings: List[str]


class TemplateEngine:
    """Professional Jinja2-based template engine with security features."""

    def __init__(self, template_dir: str, secure_mode: bool = True, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the template engine.

        Args:
            template_dir: Directory containing template files
            secure_mode: Whether to enable security sandbox features
            config: Optional configuration dictionary
        """
        self.template_dir = template_dir
        self.secure_mode = secure_mode
        self.config = config or self._load_default_config()

        # Initialize Jinja2 environment
        self.jinja_env = self._create_jinja_environment()

        # Custom filters
        self._register_custom_filters()

        logger.info("Template engine initialized with directory: %s", template_dir)

    def _create_jinja_environment(self) -> Environment:
        """Create Jinja2 environment with appropriate security settings."""
        if self.secure_mode:
            # Use sandboxed environment for security with undefined variables handled gracefully
            env: Union[SandboxedEnvironment, Environment] = SandboxedEnvironment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(["html", "xml"]),
                undefined=Undefined,  # Allow undefined variables to render as empty
            )
        else:
            env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(["html", "xml"]),
                undefined=Undefined,  # Allow undefined variables to render as empty
            )

        return env

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration for template engine."""
        return {
            "reporting": {
                "generate_report": True,
                "report_format": "HTML",
                "include_sections": ["executive_summary", "security_metrics", "performance_analytics"],
            },
            "styling": {"color_scheme": "professional", "font_family": "Arial, sans-serif"},
            "security": {"sanitize_input": True, "escape_html": True, "validate_templates": True},
        }

    def _register_custom_filters(self) -> None:
        """Register custom Jinja2 filters for report generation."""
        self.jinja_env.filters["percentage"] = lambda x: f"{x:.1f}%" if x is not None else "0.0%"
        self.jinja_env.filters["round_float"] = lambda x, decimals=2: (
            round(float(x), decimals) if x is not None else 0.0
        )
        self.jinja_env.filters["format_timestamp"] = lambda x: (
            datetime.fromisoformat(x.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S") if x else ""
        )
        self.jinja_env.filters["severity_color"] = self._get_severity_color

    def add_custom_filter(self, name: str, filter_func: Callable) -> None:
        """Add a custom Jinja2 filter.

        Args:
            name: Name of the filter
            filter_func: Function to use as filter
        """
        self.jinja_env.filters[name] = filter_func
        logger.debug("Added custom filter: %s", name)

    def _get_severity_color(self, severity: str) -> str:
        """Get color code for severity level."""
        color_map = {
            "critical": "#8B0000",
            "high": "#DC143C",
            "medium": "#FF8C00",
            "low": "#FFD700",
            "minimal": "#32CD32",
            "unknown": "#808080",
        }
        return color_map.get(severity, "#808080")

    def load_template(self, template_name: str) -> Template:
        """Load a template file.

        Args:
            template_name: Name of the template file to load

        Returns:
            Loaded Jinja2 template object

        Raises:
            TemplateValidationError: If template cannot be loaded
        """
        try:
            # Validate template path for security
            self._validate_template_path(template_name)

            template = self.jinja_env.get_template(template_name)
            logger.debug("Successfully loaded template: %s", template_name)
            return template

        except TemplateNotFound as e:
            error_msg = f"Template not found: {template_name}"
            logger.error(error_msg)
            raise TemplateValidationError(error_msg) from e
        except TemplateError as e:
            error_msg = f"Template error loading {template_name}: {e}"
            logger.error(error_msg)
            raise TemplateValidationError(error_msg) from e

    def _validate_template_path(self, template_name: str) -> None:
        """Validate template path for security (prevent directory traversal).

        Args:
            template_name: Template filename to validate

        Raises:
            TemplateSecurityError: If path is invalid or dangerous
        """
        # Prevent directory traversal attacks
        if ".." in template_name or template_name.startswith("/"):
            raise TemplateSecurityError(f"Invalid template path: {template_name}")

        # Ensure path is within template directory
        full_path = os.path.join(self.template_dir, template_name)
        resolved_path = os.path.abspath(full_path)
        template_dir_abs = os.path.abspath(self.template_dir)

        if not resolved_path.startswith(template_dir_abs):
            raise TemplateSecurityError(f"Template path outside allowed directory: {template_name}")

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with the provided context.

        Args:
            template_name: Name of the template to render
            context: Dictionary of variables for template rendering

        Returns:
            Rendered template as string

        Raises:
            TemplateValidationError: If rendering fails
        """
        try:
            # Sanitize input if security mode is enabled
            if self.secure_mode and self.config.get("security", {}).get("sanitize_input", True):
                context = self._sanitize_context(context)

            template = self.load_template(template_name)
            rendered = template.render(context)

            logger.debug("Successfully rendered template: %s", template_name)
            return rendered

        except Exception as e:
            error_msg = f"Failed to render template {template_name}: {e}"
            logger.error(error_msg)
            raise TemplateValidationError(error_msg) from e

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context variables for security.

        Args:
            context: Original context dictionary

        Returns:
            Sanitized context dictionary
        """
        sanitized: Dict[str, Any] = {}
        for key, value in context.items():
            if isinstance(value, str) and key != "content":  # Don't escape already-rendered HTML content
                # HTML escape string values
                sanitized[key] = html.escape(value)
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = self._sanitize_context(value)
            elif isinstance(value, list):
                # Sanitize list items
                sanitized[key] = [html.escape(item) if isinstance(item, str) else item for item in value]
            else:
                # Keep non-string values as-is
                sanitized[key] = value

        return sanitized

    def load_template_config(self, config_path: str) -> Dict[str, Any]:
        """Load template configuration from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Configuration dictionary

        Raises:
            Exception: If configuration cannot be loaded or parsed
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            logger.info("Loaded template configuration from: %s", config_path)
            return config

        except FileNotFoundError as e:
            error_msg = f"Configuration file not found: {config_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg) from e
        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML in configuration file {config_path}: {e}"
            logger.error(error_msg)
            raise yaml.YAMLError(error_msg) from e

    def validate_template_variables(self, template_name: str, context: Dict[str, Any]) -> Union[bool, ValidationResult]:
        """Validate template variables against provided context.

        Args:
            template_name: Name of template to validate
            context: Context variables to validate

        Returns:
            True if validation passes, ValidationResult object with details
        """
        try:
            template = self.load_template(template_name)

            # Get template source for analysis
            template_source = template.source if hasattr(template, "source") else ""
            if not template_source:
                # Try to read template source from file
                template_path = os.path.join(self.template_dir, template_name)
                with open(template_path, "r", encoding="utf-8") as f:
                    template_source = f.read()

            # Extract variables from template using simple regex
            # This is a simplified approach - a full parser would be more accurate
            variable_pattern = r"{{\s*([^}|\s]+)(?:\s*\|[^}]*)?\s*}}"
            found_variables = set(re.findall(variable_pattern, template_source))

            # Filter out Jinja2 built-ins and functions
            template_variables = {var for var in found_variables if not var.startswith("_") and "(" not in var}

            provided_variables = set(context.keys())
            missing_variables = list(template_variables - provided_variables)
            extra_variables = list(provided_variables - template_variables)

            # For simple validation, return True if no missing required variables
            if not missing_variables:
                return True

            # Return detailed validation result
            return ValidationResult(
                is_valid=len(missing_variables) == 0,
                missing_variables=missing_variables,
                extra_variables=extra_variables,
                warnings=[],
            )

        except Exception as e:
            logger.error("Template validation failed for %s: %s", template_name, e)
            return ValidationResult(
                is_valid=False, missing_variables=[], extra_variables=[], warnings=[f"Validation error: {e}"]
            )

    def test_template_rendering(self, template_name: str, sample_data: Dict[str, Any]) -> TestResult:
        """Test template rendering with sample data.

        Args:
            template_name: Name of template to test
            sample_data: Sample data for testing

        Returns:
            TestResult object with test outcome
        """
        try:
            # Attempt to render template with sample data
            rendered = self.render_template(template_name, sample_data)

            # Basic validation checks
            errors: List[str] = []
            warnings: List[str] = []

            # Check if output contains basic HTML structure
            if template_name.endswith(".html") and "<html>" not in rendered.lower():
                warnings.append("Template output does not contain HTML structure")

            # Check for unrendered variables (basic check)
            if "{{" in rendered or "}}" in rendered:
                warnings.append("Template may contain unrendered variables")

            # Determine success based on no errors
            success = len(errors) == 0

            return TestResult(
                success=success,
                is_valid=success and len(warnings) == 0,
                message="Template test completed successfully" if success else "Template test failed",
                rendered_output=rendered[:1000] if len(rendered) > 1000 else rendered,  # Truncate long output
                errors=errors if errors else None,
            )

        except Exception as e:
            logger.error("Template test failed for %s: %s", template_name, e)
            return TestResult(
                success=False,
                is_valid=False,
                message=f"Template test failed: {e}",
                rendered_output=None,
                errors=[str(e)],
            )

    def get_available_templates(self) -> List[str]:
        """Get list of available template files.

        Returns:
            List of template filenames
        """
        try:
            template_path = Path(self.template_dir)
            templates = []

            for file_path in template_path.rglob("*.html"):
                relative_path = file_path.relative_to(template_path)
                templates.append(str(relative_path))

            logger.debug("Found %d templates in %s", len(templates), self.template_dir)
            return sorted(templates)

        except Exception as e:
            logger.error("Failed to list templates: %s", e)
            return []

    def create_default_templates(self) -> None:
        """Create default template files if they don't exist."""
        templates_to_create = {
            "base.html": self._get_base_template(),
            "executive_summary.html": self._get_executive_summary_template(),
            "security_metrics.html": self._get_security_metrics_template(),
            "components/charts.html": self._get_charts_template(),
            "components/tables.html": self._get_tables_template(),
            "components/headers.html": self._get_headers_template(),
        }

        for template_name, template_content in templates_to_create.items():
            template_path = os.path.join(self.template_dir, template_name)

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(template_path), exist_ok=True)

            # Only create if doesn't exist
            if not os.path.exists(template_path):
                with open(template_path, "w", encoding="utf-8") as f:
                    f.write(template_content)
                logger.info("Created default template: %s", template_name)

    def _get_base_template(self) -> str:
        """Get base template content."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title | default("ViolentUTF Security Report") }}</title>
    <style>
        /* Professional styling for security reports */
        body {
            font-family: {{ font_family | default("Arial, sans-serif") }};
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1, h2, h3 { color: #333; }
        .header { border-bottom: 3px solid #007acc; margin-bottom: 30px; }
        .footer { border-top: 1px solid #ddd; margin-top: 30px; padding-top: 20px; }
        .severity-critical { color: #8B0000; font-weight: bold; }
        .severity-high { color: #DC143C; font-weight: bold; }
        .severity-medium { color: #FF8C00; }
        .severity-low { color: #FFD700; }
        .severity-minimal { color: #32CD32; }
    </style>
    {% block additional_css %}{% endblock %}
</head>
<body>
    <div class="container">
        {% block header %}
        <div class="header">
            <h1>{{ title | default("ViolentUTF Security Assessment Report") }}</h1>
            {% if company_name %}
            <h2>{{ company_name }}</h2>
            {% endif %}
            <p>Generated on {{ generation_date | default(moment().format("YYYY-MM-DD HH:mm:ss")) }}</p>
        </div>
        {% endblock %}

        {% block content %}
        <main>{{ content | default("No content provided") }}</main>
        {% endblock %}

        {% block footer %}
        <div class="footer">
            <p><small>Generated by ViolentUTF - AI Red Teaming Platform</small></p>
        </div>
        {% endblock %}
    </div>
</body>
</html>"""

    def _get_executive_summary_template(self) -> str:
        """Get executive summary template content."""
        return """{% extends "base.html" %}

{% block content %}
<section class="executive-summary">
    <h2>Executive Summary</h2>

    <div class="summary-metrics">
        <div class="metric-item">
            <h3>Total Executions</h3>
            <span class="metric-value">{{ total_executions | default(0) }}</span>
        </div>
        <div class="metric-item">
            <h3>Violation Rate</h3>
            <span class="metric-value severity-{{ violation_severity | default('unknown') }}">
                {{ violation_rate | percentage }}
            </span>
        </div>
        <div class="metric-item">
            <h3>Risk Level</h3>
            <span class="metric-value severity-{{ overall_risk | default('unknown') }}">
                {{ overall_risk | default('Unknown') | title }}
            </span>
        </div>
    </div>

    <div class="summary-text">
        <p>{{ executive_summary | default("No executive summary provided.") }}</p>
    </div>
</section>
{% endblock %}"""

    def _get_security_metrics_template(self) -> str:
        """Get security metrics template content."""
        return """{% extends "base.html" %}

{% block content %}
<section class="security-metrics">
    <h2>Security Metrics</h2>

    {% if severity_breakdown %}
    <div class="severity-breakdown">
        <h3>Vulnerability Severity Distribution</h3>
        <table class="metrics-table">
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Count</th>
                    <th>Percentage</th>
                </tr>
            </thead>
            <tbody>
                {% for severity, count in severity_breakdown.items() %}
                <tr>
                    <td class="severity-{{ severity }}">{{ severity | title }}</td>
                    <td>{{ count }}</td>
                    <td>{{ (count / total_scores * 100) | round_float(1) }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if scorer_performance %}
    <div class="scorer-performance">
        <h3>Scorer Performance</h3>
        <table class="metrics-table">
            <thead>
                <tr>
                    <th>Scorer</th>
                    <th>Total Tests</th>
                    <th>Violations</th>
                    <th>Violation Rate</th>
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
    </div>
    {% endif %}
</section>
{% endblock %}"""

    def _get_charts_template(self) -> str:
        """Get charts component template."""
        return """<!-- Chart rendering component -->
<div class="chart-container">
    {% if chart_type == 'bar' %}
        <canvas id="{{ chart_id }}" class="bar-chart"></canvas>
    {% elif chart_type == 'pie' %}
        <canvas id="{{ chart_id }}" class="pie-chart"></canvas>
    {% elif chart_type == 'line' %}
        <canvas id="{{ chart_id }}" class="line-chart"></canvas>
    {% else %}
        <div class="chart-placeholder">Chart: {{ chart_title }}</div>
    {% endif %}
</div>"""

    def _get_tables_template(self) -> str:
        """Get tables component template."""
        return """<!-- Table rendering component -->
<table class="data-table">
    {% if headers %}
    <thead>
        <tr>
            {% for header in headers %}
            <th>{{ header }}</th>
            {% endfor %}
        </tr>
    </thead>
    {% endif %}
    <tbody>
        {% for row in data %}
        <tr>
            {% for cell in row %}
            <td>{{ cell }}</td>
            {% endfor %}
        </tr>
        {% endfor %}
    </tbody>
</table>"""

    def _get_headers_template(self) -> str:
        """Get headers component template."""
        return """<!-- Header component -->
<header class="report-header">
    {% if logo_url %}
    <img src="{{ logo_url }}" alt="Company Logo" class="company-logo">
    {% endif %}

    <div class="header-content">
        <h1>{{ report_title | default("Security Assessment Report") }}</h1>
        {% if company_name %}
        <h2>{{ company_name }}</h2>
        {% endif %}

        <div class="report-meta">
            <p><strong>Generated:</strong> {{ generation_date | format_timestamp }}</p>
            <p><strong>Report ID:</strong> {{ report_id | default("N/A") }}</p>
            {% if classification %}
            <p><strong>Classification:</strong> <span class="classification">{{ classification }}</span></p>
            {% endif %}
        </div>
    </div>
</header>"""
