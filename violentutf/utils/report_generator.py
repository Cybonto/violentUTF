# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Report generator that integrates template engine with dashboard analytics.

This module provides comprehensive report generation capabilities by combining
the template engine with existing ViolentUTF dashboard analytics functions.
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from typing_extensions import Self

from violentutf.utils.logging import get_logger
from violentutf.utils.template_engine import TemplateEngine, TemplateValidationError

# Import existing dashboard functions for data integration
dashboard_5: Optional[Any] = None
try:
    # Import specific functions we need from the dashboard
    import sys

    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "pages")
    if dashboard_path not in sys.path:
        sys.path.insert(0, dashboard_path)

    # Import the dashboard module
    import importlib.util

    spec = importlib.util.spec_from_file_location("dashboard_5", os.path.join(dashboard_path, "5_Dashboard.py"))
    if spec and spec.loader:
        dashboard_5 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dashboard_5)
    else:
        dashboard_5 = None

except Exception:
    dashboard_5 = None

logger = get_logger(__name__)


class ReportGenerationError(Exception):
    """Raised when report generation fails."""


class ReportGenerator:
    """Professional report generator integrating with ViolentUTF analytics."""

    def __init__(
        self: Self,
        template_dir: Optional[str] = None,
        config_dir: Optional[str] = None,
        output_dir: str = "reports",
    ) -> None:
        """Initialize the report generator.

        Args:
            template_dir: Directory containing template files
            config_dir: Directory containing configuration files
            output_dir: Directory for generated reports
        """
        # Set default paths
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(__file__), "..", "parameters", "reporting")

        self.template_dir = os.path.abspath(template_dir)
        self.config_dir = os.path.abspath(config_dir)
        self.output_dir = os.path.abspath(output_dir)

        # Initialize template engine
        self.template_engine = TemplateEngine(self.template_dir, secure_mode=True)

        # Load configuration
        self.config = self._load_configuration()

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info("Report generator initialized with templates: %s", self.template_dir)

    def _load_configuration(self: Self) -> Dict[str, Any]:
        """Load reporting configuration from YAML files."""
        try:
            default_config_path = os.path.join(self.config_dir, "default_config.yaml")
            template_settings_path = os.path.join(self.config_dir, "template_settings.yaml")
            branding_config_path = os.path.join(self.config_dir, "branding_config.yaml")

            config = {}

            # Load default configuration
            if os.path.exists(default_config_path):
                default_config = self.template_engine.load_template_config(default_config_path)
                config.update(default_config)

            # Load template settings
            if os.path.exists(template_settings_path):
                template_config = self.template_engine.load_template_config(template_settings_path)
                config["templates"] = template_config.get("templates", {})
                config["variable_mappings"] = template_config.get("variable_mappings", {})

            # Load branding configuration
            if os.path.exists(branding_config_path):
                branding_config = self.template_engine.load_template_config(branding_config_path)
                config["branding"] = branding_config.get("branding", {})
                config["styling"] = branding_config.get("styling", {})

            return config

        except Exception as e:
            logger.error("Failed to load configuration: %s", e)
            return self._get_default_config()

    def _get_default_config(self: Self) -> Dict[str, Any]:
        """Get default configuration if loading fails."""
        return {
            "reporting": {
                "generate_report": True,
                "report_format": "HTML",
                "include_sections": ["executive_summary", "security_metrics"],
                "output_directory": self.output_dir,
            },
            "styling": {"color_scheme": "professional"},
            "branding": {"company_name": "", "report_title_prefix": "ViolentUTF Security Assessment"},
        }

    def generate_report_from_dashboard_data(
        self: Self,
        days_back: int = 30,
        custom_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a comprehensive security report using dashboard data loading functions.

        This method integrates with the existing load_orchestrator_executions_with_results
        function from 5_Dashboard.py for consistency.

        Args:
            days_back: Number of days to look back for data
            custom_context: Additional context variables

        Returns:
            Path to generated report file

        Raises:
            ReportGenerationError: If report generation fails
        """
        try:
            # Use existing dashboard data loading function
            if dashboard_5 and hasattr(dashboard_5, "load_orchestrator_executions_with_results"):
                logger.info("Using existing dashboard load_orchestrator_executions_with_results function")
                executions_data, results_data = dashboard_5.load_orchestrator_executions_with_results(days_back)
            else:
                logger.warning("Dashboard data loading function not available")
                executions_data, results_data = [], []

            return self.generate_comprehensive_report(executions_data, results_data, custom_context)

        except Exception as e:
            error_msg = f"Failed to generate report from dashboard data: {e}"
            logger.error(error_msg)
            raise ReportGenerationError(error_msg) from e

    def generate_comprehensive_report(
        self: Self,
        executions_data: List[Dict[str, Any]],
        results_data: List[Dict[str, Any]],
        custom_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a comprehensive security report.

        Args:
            executions_data: Orchestrator execution data
            results_data: Security scorer results data
            custom_context: Additional context variables

        Returns:
            Path to generated report file

        Raises:
            ReportGenerationError: If report generation fails
        """
        try:
            # Generate comprehensive metrics compatible with templates
            metrics = self.calculate_template_compatible_metrics(results_data)

            # Create template context
            context = self._create_report_context(metrics, executions_data, results_data, custom_context)

            # Generate report sections
            report_sections = self._generate_report_sections(context)

            # Combine sections into content and mark as safe HTML
            try:
                from jinja2 import Markup
            except ImportError:
                try:
                    from markupsafe import Markup
                except ImportError:
                    # Fallback for older versions
                    class MarkupFallback(str):
                        def __new__(cls, value: str) -> "MarkupFallback":
                            return str.__new__(cls, value)  # type: ignore

                    Markup = MarkupFallback

            sections_content = ""
            for _, section_html in report_sections.items():
                sections_content += section_html + "\n"

            # Mark HTML content as safe to prevent escaping
            # This is safe as content comes from trusted template rendering
            safe_content = Markup(sections_content)  # nosec B704

            # Combine sections into full report context
            full_context = {**context, "content": safe_content, "report_sections": report_sections}

            # Generate final report
            report_content = self.template_engine.render_template("base.html", full_context)

            # Save report to file
            report_filename = self._generate_report_filename()
            report_path = os.path.join(self.output_dir, report_filename)

            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            logger.info("Report generated successfully: %s", report_path)
            return report_path

        except Exception as e:
            error_msg = f"Failed to generate comprehensive report: {e}"
            logger.error(error_msg)
            raise ReportGenerationError(error_msg) from e

    def calculate_template_compatible_metrics(self: Self, results_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive metrics using existing dashboard functions.

        This integrates with the existing calculate_comprehensive_metrics function
        from 5_Dashboard.py to provide template-compatible data structures.

        Args:
            results_data: Security scorer results

        Returns:
            Template-compatible metrics dictionary
        """
        if not results_data:
            return self._get_empty_metrics()

        # Use existing dashboard function for consistency
        try:
            if dashboard_5 and hasattr(dashboard_5, "calculate_comprehensive_metrics"):
                logger.info("Using existing dashboard calculate_comprehensive_metrics function")
                base_metrics = dashboard_5.calculate_comprehensive_metrics(results_data)
            else:
                logger.warning("Dashboard function not available, using fallback calculation")
                base_metrics = self._calculate_metrics_locally(results_data)
        except Exception as e:
            logger.error("Failed to use dashboard function, falling back to local calculation: %s", e)
            base_metrics = self._calculate_metrics_locally(results_data)

        # Enhance metrics for template compatibility
        enhanced_metrics = self._enhance_metrics_for_templates(base_metrics, results_data)

        return enhanced_metrics

    def _calculate_metrics_locally(self: Self, results_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback implementation of metrics calculation.

        This method provides basic metrics calculation when the dashboard
        calculate_comprehensive_metrics function is not available (e.g., in tests
        or isolated environments). The primary implementation now uses the
        existing dashboard function for consistency.
        """
        from collections import Counter, defaultdict

        total_scores = len(results_data)
        unique_scorers = len(set(r["scorer_name"] for r in results_data))
        unique_generators = len(set(r["generator_name"] for r in results_data))
        unique_datasets = len(set(r["dataset_name"] for r in results_data))
        unique_executions = len(set(r["execution_id"] for r in results_data))

        # Violation analysis
        violations = 0
        for result in results_data:
            if result["score_type"] == "true_false" and result["score_value"] is True:
                violations += 1
            elif result["score_type"] == "float_scale" and result["score_value"] >= 0.6:
                violations += 1
            elif result["score_type"] == "str" and result["severity"] in ["high", "critical"]:
                violations += 1

        violation_rate = (violations / total_scores * 100) if total_scores > 0 else 0

        # Severity breakdown
        severity_counts = Counter(r["severity"] for r in results_data)
        severity_breakdown = dict(severity_counts)

        # Scorer performance
        scorer_performance: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"total": 0, "violations": 0, "avg_score": 0}
        )
        for result in results_data:
            scorer = result["scorer_name"]
            scorer_performance[scorer]["total"] += 1

            if result["score_type"] == "true_false" and result["score_value"] is True:
                scorer_performance[scorer]["violations"] += 1
            elif result["score_type"] == "float_scale":
                scorer_performance[scorer]["avg_score"] += result["score_value"]

        # Calculate averages
        for scorer, stats in scorer_performance.items():
            if stats["total"] > 0:
                stats["violation_rate"] = stats["violations"] / stats["total"] * 100
                if stats["avg_score"] > 0:
                    stats["avg_score"] = float(stats["avg_score"]) / stats["total"]

        # Generator risk profile
        generator_risk: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0})
        for result in results_data:
            generator = result["generator_name"]
            generator_risk[generator]["total"] += 1
            if result["severity"] == "critical":
                generator_risk[generator]["critical"] += 1
            elif result["severity"] == "high":
                generator_risk[generator]["high"] += 1

        return {
            "total_executions": unique_executions,
            "total_scores": total_scores,
            "unique_scorers": unique_scorers,
            "unique_generators": unique_generators,
            "unique_datasets": unique_datasets,
            "violation_rate": violation_rate,
            "severity_breakdown": severity_breakdown,
            "scorer_performance": dict(scorer_performance),
            "generator_risk_profile": dict(generator_risk),
            "temporal_patterns": {},
        }

    def _enhance_metrics_for_templates(
        self: Self, base_metrics: Dict[str, Any], results_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Enhance base metrics with template-specific data structures."""
        enhanced = base_metrics.copy()

        # Add template-specific enhancements
        enhanced["violation_severity"] = self._determine_violation_severity(enhanced["violation_rate"])
        enhanced["overall_risk"] = self._calculate_overall_risk(enhanced["severity_breakdown"])
        enhanced["compliance_score"] = self._calculate_compliance_score(enhanced["violation_rate"])
        enhanced["risk_score"] = self._calculate_risk_score(enhanced["severity_breakdown"])

        # Add attack category analysis if available
        enhanced["attack_categories"] = self._analyze_attack_categories(results_data)

        # Add critical vulnerabilities list
        enhanced["critical_vulnerabilities"] = self._extract_critical_vulnerabilities(results_data)

        # Add recommendations based on findings
        enhanced["recommendations_summary"] = self._generate_recommendations_summary(enhanced)

        # Add assessment scope
        enhanced["assessment_scope"] = self._create_assessment_scope(enhanced)

        # Add key findings
        enhanced["key_findings"] = self._extract_key_findings(enhanced, results_data)

        # Add performance analytics data for template compatibility
        enhanced["execution_times"] = self._extract_execution_times(results_data)
        enhanced["throughput_metrics"] = self._calculate_throughput_metrics(results_data)
        enhanced["resource_recommendations"] = self._generate_performance_recommendations(enhanced)

        return enhanced

    def _determine_violation_severity(self: Self, violation_rate: float) -> str:
        """Determine severity level based on violation rate."""
        if violation_rate >= 30:
            return "critical"
        elif violation_rate >= 20:
            return "high"
        elif violation_rate >= 10:
            return "medium"
        elif violation_rate >= 5:
            return "low"
        else:
            return "minimal"

    def _calculate_overall_risk(self: Self, severity_breakdown: Dict[str, int]) -> str:
        """Calculate overall risk level from severity breakdown."""
        if severity_breakdown.get("critical", 0) > 0:
            return "critical"
        elif severity_breakdown.get("high", 0) > 2:
            return "high"
        elif severity_breakdown.get("high", 0) > 0 or severity_breakdown.get("medium", 0) > 5:
            return "medium"
        else:
            return "low"

    def _calculate_compliance_score(self: Self, violation_rate: float) -> float:
        """Calculate compliance score as inverse of violation rate."""
        return max(0, 100 - violation_rate)

    def _calculate_risk_score(self: Self, severity_breakdown: Dict[str, int]) -> float:
        """Calculate numerical risk score."""
        weights = {"critical": 10, "high": 5, "medium": 3, "low": 1, "minimal": 0.5}
        total_weighted = sum(count * weights.get(severity, 1) for severity, count in severity_breakdown.items())
        total_issues = sum(severity_breakdown.values())

        if total_issues == 0:
            return 0.0

        return min(10.0, total_weighted / total_issues)

    def _analyze_attack_categories(self: Self, results_data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Analyze attack patterns by category."""
        from collections import defaultdict

        categories: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"attempts": 0, "successful": 0, "severities": []})

        for result in results_data:
            category = result.get("score_category", "unknown")
            categories[category]["attempts"] += 1

            # Consider high/critical severity as successful attacks
            if result.get("severity") in ["high", "critical"]:
                categories[category]["successful"] += 1

            categories[category]["severities"].append(result.get("severity", "unknown"))

        # Calculate average severity for each category
        for category, stats in categories.items():
            if stats["severities"]:
                severity_weights = {"critical": 5, "high": 4, "medium": 3, "low": 2, "minimal": 1, "unknown": 0}
                avg_weight = sum(severity_weights.get(s, 0) for s in stats["severities"]) / len(stats["severities"])

                if avg_weight >= 4.5:
                    stats["avg_severity"] = "critical"
                elif avg_weight >= 3.5:
                    stats["avg_severity"] = "high"
                elif avg_weight >= 2.5:
                    stats["avg_severity"] = "medium"
                elif avg_weight >= 1.5:
                    stats["avg_severity"] = "low"
                else:
                    stats["avg_severity"] = "minimal"
            else:
                stats["avg_severity"] = "unknown"

            del stats["severities"]  # Remove intermediate data

        return dict(categories)

    def _extract_critical_vulnerabilities(self: Self, results_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract critical vulnerabilities for highlighting."""
        critical_vulns = []

        for result in results_data:
            if result.get("severity") == "critical":
                vuln = {
                    "title": f"Critical {result.get('score_category', 'Vulnerability')}",
                    "severity": "critical",
                    "category": result.get("score_category", "Unknown"),
                    "description": result.get("score_rationale", "Critical security vulnerability detected"),
                    "scorer": result.get("scorer_name", "Unknown"),
                    "generator": result.get("generator_name", "Unknown"),
                }
                critical_vulns.append(vuln)

        return critical_vulns[:10]  # Limit to top 10 critical vulnerabilities

    def _generate_recommendations_summary(self: Self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate summary recommendations based on findings."""
        recommendations = []

        if metrics.get("severity_breakdown", {}).get("critical", 0) > 0:
            recommendations.append(
                {
                    "text": "Immediately address all critical security vulnerabilities identified in the assessment",
                    "priority": "high",
                }
            )

        if metrics.get("violation_rate", 0) > 20:
            recommendations.append(
                {
                    "text": "Implement comprehensive security controls to reduce the high violation rate",
                    "priority": "high",
                }
            )

        if metrics.get("severity_breakdown", {}).get("high", 0) > 0:
            recommendations.append(
                {"text": "Prioritize remediation of high-severity security issues within 30 days", "priority": "medium"}
            )

        # Add general recommendations
        recommendations.extend(
            [
                {"text": "Establish regular security assessments and continuous monitoring", "priority": "medium"},
                {"text": "Implement security awareness training for development teams", "priority": "medium"},
                {"text": "Review and update security policies based on assessment findings", "priority": "low"},
            ]
        )

        return recommendations[:5]  # Limit to top 5 recommendations

    def _create_assessment_scope(self: Self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Create assessment scope information."""
        return {
            "models": list(metrics.get("generator_risk_profile", {}).keys())[:10],
            "scorers": list(metrics.get("scorer_performance", {}).keys())[:10],
            "datasets": [f"Dataset {i+1}" for i in range(metrics.get("unique_datasets", 0))],
            "total_executions": metrics.get("total_executions", 0),
            "total_scores": metrics.get("total_scores", 0),
        }

    def _extract_key_findings(
        self: Self, metrics: Dict[str, Any], results_data: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Extract key findings from the assessment."""
        findings = []

        # Critical findings
        if metrics.get("severity_breakdown", {}).get("critical", 0) > 0:
            findings.append(
                {
                    "title": "Critical Security Vulnerabilities Detected",
                    "severity": "critical",
                    "description": (
                        f"{metrics['severity_breakdown']['critical']} critical vulnerabilities "
                        "require immediate attention"
                    ),
                }
            )

        # High violation rate
        if metrics.get("violation_rate", 0) > 25:
            findings.append(
                {
                    "title": "High Violation Rate",
                    "severity": "high",
                    "description": (
                        f"Violation rate of {metrics['violation_rate']:.1f}% indicates " "significant security concerns"
                    ),
                }
            )

        # Positive findings
        if metrics.get("violation_rate", 0) < 5:
            findings.append(
                {
                    "title": "Low Violation Rate",
                    "severity": "minimal",
                    "description": (
                        f"Low violation rate of {metrics['violation_rate']:.1f}% indicates " "strong security posture"
                    ),
                }
            )

        return findings[:5]  # Limit to top 5 findings

    def _extract_execution_times(self: Self, results_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract execution time metrics from results data."""
        # Group by execution_id to calculate execution-level timing
        from collections import defaultdict

        execution_times: Dict[str, List[datetime]] = defaultdict(list)

        for result in results_data:
            execution_id = result.get("execution_id")
            timestamp = result.get("timestamp")
            if execution_id and timestamp:
                try:
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    execution_times[execution_id].append(timestamp)
                except (ValueError, TypeError):
                    continue

        # Calculate timing metrics
        durations = []
        for execution_id, timestamps in execution_times.items():
            if len(timestamps) > 1:
                sorted_times = sorted(timestamps)
                duration = (sorted_times[-1] - sorted_times[0]).total_seconds()
                durations.append(duration)

        if not durations:
            return {"average_time": 0.0, "min_time": 0.0, "max_time": 0.0, "total_time": 0.0}

        return {
            "average_time": sum(durations) / len(durations),
            "min_time": min(durations),
            "max_time": max(durations),
            "total_time": sum(durations),
        }

    def _calculate_throughput_metrics(self: Self, results_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate throughput metrics from results data."""
        if not results_data:
            return {
                "scores_per_second": 0.0,
                "tests_per_minute": 0.0,
                "peak_throughput": 0.0,
                "concurrent_executions": 0,
            }

        # Calculate time span
        timestamps = []
        for result in results_data:
            timestamp = result.get("timestamp")
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamps.append(timestamp)
                except (ValueError, TypeError):
                    continue

        if len(timestamps) < 2:
            return {
                "scores_per_second": 0.0,
                "tests_per_minute": 0.0,
                "peak_throughput": 0.0,
                "concurrent_executions": len(set(r.get("execution_id") for r in results_data if r.get("execution_id"))),
            }

        time_span = (max(timestamps) - min(timestamps)).total_seconds()
        if time_span == 0:
            time_span = 1  # Avoid division by zero

        total_scores = len(results_data)
        unique_executions = len(set(r.get("execution_id") for r in results_data if r.get("execution_id")))

        return {
            "scores_per_second": total_scores / time_span,
            "tests_per_minute": (unique_executions / time_span) * 60,
            "peak_throughput": total_scores / time_span,  # Simplified calculation
            "concurrent_executions": unique_executions,
        }

    def _generate_performance_recommendations(self: Self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate performance-focused recommendations."""
        recommendations = []

        execution_times = metrics.get("execution_times", {})
        throughput_metrics = metrics.get("throughput_metrics", {})

        # Check execution time performance
        avg_time = execution_times.get("average_time", 0)
        if avg_time > 300:  # > 5 minutes
            recommendations.append(
                {
                    "title": "Long Execution Times",
                    "text": (
                        f"Average execution time of {avg_time:.1f}s is high. "
                        "Consider optimizing test parameters or increasing parallel processing."
                    ),
                    "priority": "high",
                }
            )

        # Check throughput performance
        scores_per_sec = throughput_metrics.get("scores_per_second", 0)
        if scores_per_sec < 1:
            recommendations.append(
                {
                    "title": "Low Processing Throughput",
                    "text": (
                        f"Processing {scores_per_sec:.2f} scores per second. "
                        "Consider optimizing scorer implementations or increasing concurrency."
                    ),
                    "priority": "medium",
                }
            )

        # General performance recommendations
        if not recommendations:
            recommendations.append(
                {
                    "title": "Performance Monitoring",
                    "text": "Continue monitoring execution times and throughput metrics for performance trends.",
                    "priority": "low",
                }
            )

        return recommendations[:5]

    def _create_report_context(
        self: Self,
        metrics: Dict[str, Any],
        executions_data: List[Dict[str, Any]],
        results_data: List[Dict[str, Any]],
        custom_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create comprehensive template context."""
        # Base context from configuration
        context = {
            "generation_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "report_id": str(uuid.uuid4())[:8],
            "title": self.config.get("branding", {}).get(
                "report_title_prefix", "ViolentUTF Security Assessment Report"
            ),
            "company_name": self.config.get("branding", {}).get("company_name", ""),
            "company_logo": self.config.get("branding", {}).get("company_logo_url", ""),
            "classification": self.config.get("branding", {}).get("default_classification", ""),
            "prepared_by": "ViolentUTF AI Red Team Platform",
        }

        # Add metrics to context
        context.update(metrics)

        # Add custom context if provided
        if custom_context:
            context.update(custom_context)

        return context

    def _generate_report_sections(self: Self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate individual report sections."""
        sections = {}
        include_sections = self.config.get("reporting", {}).get("include_sections", ["executive_summary"])

        for section in include_sections:
            try:
                if section == "executive_summary":
                    sections[section] = self.template_engine.render_template("executive_summary.html", context)
                elif section == "security_metrics":
                    sections[section] = self.template_engine.render_template("security_metrics.html", context)
                # Add other sections as needed

            except TemplateValidationError as e:
                logger.error("Failed to render section %s: %s", section, e)
                sections[section] = f"<p>Error rendering {section}: {e}</p>"

        return sections

    def _generate_report_filename(self: Self) -> str:
        """Generate unique report filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"violentutf_security_report_{timestamp}.html"

    def _get_empty_metrics(self: Self) -> Dict[str, Any]:
        """Get empty metrics structure for when no data is available."""
        return {
            "total_executions": 0,
            "total_scores": 0,
            "unique_scorers": 0,
            "unique_generators": 0,
            "unique_datasets": 0,
            "violation_rate": 0.0,
            "severity_breakdown": {},
            "scorer_performance": {},
            "generator_risk_profile": {},
            "overall_risk": "unknown",
            "violation_severity": "unknown",
            "compliance_score": 100.0,
            "risk_score": 0.0,
            "attack_categories": {},
            "critical_vulnerabilities": [],
            "recommendations_summary": [],
            "assessment_scope": {},
            "key_findings": [],
        }

    def get_available_templates(self: Self) -> List[str]:
        """Get list of available report templates."""
        return self.template_engine.get_available_templates()

    def validate_template(self: Self, template_name: str, sample_data: Optional[Dict[str, Any]] = None) -> bool:
        """Validate a template with optional sample data."""
        try:
            if sample_data is None:
                sample_data = self._get_empty_metrics()

            result = self.template_engine.test_template_rendering(template_name, sample_data)
            return result.success

        except Exception as e:
            logger.error("Template validation failed for %s: %s", template_name, e)
            return False
