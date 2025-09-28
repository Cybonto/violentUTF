#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""
Recovery Reporting Module - Issue #268

Comprehensive recovery reporting and compliance tracking system.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ComplianceMetrics:
    """Compliance metrics for a specific database type."""

    database_type: str
    rto_target_minutes: float
    rpo_target_minutes: float
    rto_compliance_rate: float = 0.0
    rpo_compliance_rate: float = 0.0
    average_rto: float = 0.0
    average_rpo: float = 0.0
    test_count: int = 0
    last_test_date: Optional[str] = None
    trend: str = "stable"  # improving, degrading, stable

    @property
    def overall_compliant(self) -> bool:
        """Check if both RTO and RPO are compliant."""
        return self.rto_compliance_rate >= 90.0 and self.rpo_compliance_rate >= 90.0


class ComplianceTracker:
    """Track RTO/RPO compliance over time with detailed analytics."""

    def __init__(self, report_directory: str = "docs/reports/recovery") -> None:
        """
        Initialize compliance tracker.

        Args:
            report_directory: Directory to store compliance reports
        """
        self.report_directory = Path(report_directory)
        self.report_directory.mkdir(parents=True, exist_ok=True)
        self.compliance_history = []
        self.thresholds = {
            "rto_compliance_minimum": 90.0,
            "rpo_compliance_minimum": 90.0,
            "trend_analysis_days": 30,
        }

    def track_test_result(self, test_result: Dict[str, Any]) -> None:
        """
        Track a single test result for compliance analysis.

        Args:
            test_result: Recovery test result dictionary
        """
        database_type = test_result.get("database_type")
        if not database_type:
            return

        compliance_entry = {
            "database_type": database_type,
            "test_date": test_result.get("end_time", datetime.now().isoformat()),
            "rto_actual": test_result.get("rto_actual", 0.0),
            "rto_target": test_result.get("rto_target", 0.0),
            "rpo_actual": test_result.get("rpo_actual"),
            "rpo_target": test_result.get("rpo_target"),
            "rto_compliant": test_result.get("rto_compliant", False),
            "rpo_compliant": test_result.get("rpo_compliant"),
            "data_integrity": test_result.get("data_integrity", True),
            "test_status": test_result.get("status", "unknown"),
        }

        self.compliance_history.append(compliance_entry)

    def calculate_compliance_metrics(self, database_type: str, days_back: int = 30) -> ComplianceMetrics:
        """
        Calculate compliance metrics for a specific database type.

        Args:
            database_type: Database type to analyze
            days_back: Number of days to look back for analysis

        Returns:
            ComplianceMetrics object with calculated metrics
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)

        # Filter relevant test results
        relevant_tests = [
            test
            for test in self.compliance_history
            if test.get("database_type") == database_type
            and datetime.fromisoformat(test.get("test_date", "1970-01-01")) >= cutoff_date
        ]

        if not relevant_tests:
            # Return default metrics if no data
            return ComplianceMetrics(
                database_type=database_type,
                rto_target_minutes=self._get_default_rto_target(database_type),
                rpo_target_minutes=self._get_default_rpo_target(database_type),
            )

        # Calculate RTO metrics
        rto_compliant_tests = [test for test in relevant_tests if test.get("rto_compliant", False)]
        rto_compliance_rate = (len(rto_compliant_tests) / len(relevant_tests)) * 100

        # Calculate RPO metrics
        rpo_tests = [test for test in relevant_tests if test.get("rpo_compliant") is not None]
        rpo_compliant_tests = [test for test in rpo_tests if test.get("rpo_compliant", False)]
        rpo_compliance_rate = (len(rpo_compliant_tests) / max(1, len(rpo_tests))) * 100 if rpo_tests else 0

        # Calculate averages
        rto_values = [test.get("rto_actual", 0) for test in relevant_tests if test.get("rto_actual") is not None]
        rpo_values = [test.get("rpo_actual", 0) for test in relevant_tests if test.get("rpo_actual") is not None]

        average_rto = sum(rto_values) / len(rto_values) if rto_values else 0.0
        average_rpo = sum(rpo_values) / len(rpo_values) if rpo_values else 0.0

        # Determine trend
        trend = self._calculate_trend(relevant_tests, "rto_actual")

        return ComplianceMetrics(
            database_type=database_type,
            rto_target_minutes=relevant_tests[0].get("rto_target", self._get_default_rto_target(database_type)),
            rpo_target_minutes=relevant_tests[0].get("rpo_target", self._get_default_rpo_target(database_type)),
            rto_compliance_rate=rto_compliance_rate,
            rpo_compliance_rate=rpo_compliance_rate,
            average_rto=average_rto,
            average_rpo=average_rpo,
            test_count=len(relevant_tests),
            last_test_date=max(test.get("test_date", "") for test in relevant_tests),
            trend=trend,
        )

    def generate_compliance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report.

        Returns:
            Complete compliance report with analytics
        """
        report_timestamp = datetime.now()
        database_types = ["postgresql", "sqlite", "duckdb"]

        # Calculate metrics for each database type
        database_metrics = {}
        for db_type in database_types:
            database_metrics[db_type] = self.calculate_compliance_metrics(db_type)

        # Calculate overall system compliance
        overall_rto_compliance = (
            sum(metrics.rto_compliance_rate for metrics in database_metrics.values()) / len(database_metrics)
            if database_metrics
            else 0.0
        )

        rpo_compliant_metrics = [m for m in database_metrics.values() if m.rpo_compliance_rate > 0]
        if rpo_compliant_metrics:
            overall_rpo_compliance = sum(metrics.rpo_compliance_rate for metrics in rpo_compliant_metrics) / len(
                rpo_compliant_metrics
            )
        else:
            overall_rpo_compliance = 0.0

        # Identify critical issues
        critical_issues = []
        for db_type, metrics in database_metrics.items():
            if metrics.rto_compliance_rate < self.thresholds["rto_compliance_minimum"]:
                critical_issues.append(f"{db_type} RTO compliance below threshold: {metrics.rto_compliance_rate:.1f}%")
            if (
                metrics.rpo_compliance_rate > 0
                and metrics.rpo_compliance_rate < self.thresholds["rpo_compliance_minimum"]
            ):
                critical_issues.append(f"{db_type} RPO compliance below threshold: {metrics.rpo_compliance_rate:.1f}%")

        # Generate recommendations
        recommendations = self._generate_compliance_recommendations(database_metrics)

        report = {
            "report_metadata": {
                "report_type": "compliance_analysis",
                "generated_at": report_timestamp.isoformat(),
                "analysis_period_days": self.thresholds["trend_analysis_days"],
                "total_tests_analyzed": len(self.compliance_history),
            },
            "executive_summary": {
                "overall_rto_compliance": overall_rto_compliance,
                "overall_rpo_compliance": overall_rpo_compliance,
                "systems_meeting_targets": len([m for m in database_metrics.values() if m.overall_compliant]),
                "total_systems": len(database_metrics),
                "critical_issues_count": len(critical_issues),
            },
            "database_compliance": {
                db_type: {
                    "rto_target_minutes": metrics.rto_target_minutes,
                    "rpo_target_minutes": metrics.rpo_target_minutes,
                    "rto_compliance_rate": metrics.rto_compliance_rate,
                    "rpo_compliance_rate": metrics.rpo_compliance_rate,
                    "average_rto": metrics.average_rto,
                    "average_rpo": metrics.average_rpo,
                    "test_count": metrics.test_count,
                    "last_test_date": metrics.last_test_date,
                    "trend": metrics.trend,
                    "overall_compliant": metrics.overall_compliant,
                }
                for db_type, metrics in database_metrics.items()
            },
            "critical_issues": critical_issues,
            "recommendations": recommendations,
            "next_analysis_date": (report_timestamp + timedelta(days=7)).isoformat(),
        }

        # Save report
        report_filename = f"compliance_report_{report_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        report_path = self.report_directory / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info("Compliance report saved to %s", report_path)

        return report

    def _get_default_rto_target(self, database_type: str) -> float:
        """Get default RTO target for database type."""
        targets = {"postgresql": 15.0, "sqlite": 5.0, "duckdb": 30.0}  # minutes
        return targets.get(database_type, 15.0)

    def _get_default_rpo_target(self, database_type: str) -> float:
        """Get default RPO target for database type."""
        targets = {
            "postgresql": 60.0,
            "sqlite": 30.0,
            "duckdb": 1440.0,
        }  # minutes  # 24 hours
        return targets.get(database_type, 60.0)

    def _calculate_trend(self, test_results: List[Dict[str, Any]], metric_key: str) -> str:
        """Calculate trend for a specific metric."""
        if len(test_results) < 3:
            return "insufficient_data"

        # Sort by date
        sorted_results = sorted(test_results, key=lambda x: x.get("test_date", "1970-01-01"))

        values = [test.get(metric_key, 0) for test in sorted_results if test.get(metric_key) is not None]

        if len(values) < 3:
            return "insufficient_data"

        # Calculate trend using linear regression (simplified)
        n = len(values)
        x_values = list(range(n))

        # Calculate slope
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n

        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Classify trend
        if abs(slope) < 0.1:  # Threshold for considering stable
            return "stable"
        elif slope > 0:
            return "degrading"  # Increasing RTO/RPO is degrading
        else:
            return "improving"

    def _generate_compliance_recommendations(self, database_metrics: Dict[str, ComplianceMetrics]) -> List[str]:
        """Generate recommendations based on compliance analysis."""
        recommendations = []

        for db_type, metrics in database_metrics.items():
            if metrics.rto_compliance_rate < self.thresholds["rto_compliance_minimum"]:
                recommendations.append(
                    f"Urgent: Improve {db_type} RTO performance - "
                    f"current compliance: {metrics.rto_compliance_rate:.1f}%, "
                    f"target: {self.thresholds['rto_compliance_minimum']}%"
                )

            if (
                metrics.rpo_compliance_rate > 0
                and metrics.rpo_compliance_rate < self.thresholds["rpo_compliance_minimum"]
            ):
                recommendations.append(
                    f"Review {db_type} backup frequency - "
                    f"current RPO compliance: {metrics.rpo_compliance_rate:.1f}%"
                )

            if metrics.trend == "degrading":
                recommendations.append(f"Monitor {db_type} performance trend - showing degradation over time")

            if metrics.test_count < 5:  # Less than 5 tests in analysis period
                recommendations.append(
                    f"Increase {db_type} recovery testing frequency - "
                    f"only {metrics.test_count} tests in last {self.thresholds['trend_analysis_days']} days"
                )

        # Overall recommendations
        compliant_systems = len([m for m in database_metrics.values() if m.overall_compliant])
        total_systems = len(database_metrics)

        if compliant_systems < total_systems:
            recommendations.append(
                f"System-wide compliance review needed - "
                f"only {compliant_systems}/{total_systems} systems fully compliant"
            )

        if not recommendations:
            recommendations.append("All systems meeting compliance targets - continue current monitoring schedule")

        return recommendations

    def export_historical_data(self, output_file: Optional[str] = None) -> str:
        """
        Export historical compliance data to JSON file.

        Args:
            output_file: Optional output filename

        Returns:
            Path to exported file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"compliance_history_{timestamp}.json"

        output_path = self.report_directory / output_file

        export_data = {
            "export_metadata": {
                "exported_at": datetime.now().isoformat(),
                "total_records": len(self.compliance_history),
                "date_range": self._get_date_range(),
            },
            "compliance_history": self.compliance_history,
            "thresholds": self.thresholds,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info("Historical data exported to %s", output_path)
        return str(output_path)

    def _get_date_range(self) -> Dict[str, str]:
        """Get date range of historical data."""
        if not self.compliance_history:
            return {"start": "no_data", "end": "no_data"}

        dates = [entry.get("test_date", "") for entry in self.compliance_history if entry.get("test_date")]

        if not dates:
            return {"start": "no_data", "end": "no_data"}

        return {"start": min(dates), "end": max(dates)}


class RecoveryReporter:
    """Enhanced recovery reporter with compliance tracking integration."""

    def __init__(self) -> None:
        """Initialize recovery reporter with compliance tracker."""
        self.compliance_tracker = ComplianceTracker()
        self.report_templates = {}

    def generate_report(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate basic recovery test report.

        Args:
            test_results: Results from recovery testing

        Returns:
            Recovery test report
        """
        # Basic report generation logic
        report_timestamp = datetime.now()

        # Process test results
        processed_results = []
        overall_success_rate = 0.0
        total_tests = 0

        for db_type, results in test_results.items():
            processed_result = {
                "database_type": db_type,
                "test_status": results.get("status", "unknown"),
                "rto_compliance": results.get("rto_actual", 0) <= results.get("rto_target", float("inf")),
                "rpo_compliance": results.get("rpo_actual", 0) <= results.get("rpo_target", float("inf")),
                "data_integrity": results.get("data_integrity", False),
                "recovery_method": results.get("recovery_method", "unknown"),
                "performance_metrics": {
                    "rto_actual": results.get("rto_actual", 0),
                    "rto_target": results.get("rto_target", 0),
                    "rpo_actual": results.get("rpo_actual", 0),
                    "rpo_target": results.get("rpo_target", 0),
                    "test_duration": results.get("test_duration", 0),
                },
            }
            processed_results.append(processed_result)

            if results.get("status") == "success":
                overall_success_rate += 1
            elif results.get("status") == "partial_success":
                overall_success_rate += 0.8  # Partial success counts as 80%
            total_tests += 1

        if total_tests > 0:
            overall_success_rate = (overall_success_rate / total_tests) * 100

        return {
            "report_metadata": {
                "report_type": "recovery_test_report",
                "generated_at": report_timestamp.isoformat(),
                "test_execution_date": report_timestamp.isoformat(),
            },
            "overall_status": (
                "success"
                if overall_success_rate >= 80
                else "partial_success" if overall_success_rate >= 50 else "failed"
            ),
            "rto_compliance": {r["database_type"]: r["rto_compliance"] for r in processed_results},
            "rpo_compliance": {r["database_type"]: r["rpo_compliance"] for r in processed_results},
            "executive_summary": {
                "overall_success_rate": overall_success_rate,
                "total_databases_tested": total_tests,
                "critical_issues_count": sum(1 for r in processed_results if not r["data_integrity"]),
                "rto_compliance_rate": (
                    sum(1 for r in processed_results if r["rto_compliance"]) / total_tests * 100
                    if total_tests > 0
                    else 0
                ),
            },
            "detailed_results": processed_results,
            "recommendations": self._generate_recommendations(processed_results),
            "next_test_schedule": (datetime.now() + timedelta(days=7)).isoformat(),  # Weekly testing schedule
        }

    def _generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        for result in results:
            if not result["rto_compliance"]:
                recommendations.append(f"Improve {result['database_type']} RTO performance")
            if not result["rpo_compliance"]:
                recommendations.append(f"Improve {result['database_type']} RPO performance")
            if not result["data_integrity"]:
                recommendations.append(f"Address {result['database_type']} data integrity issues")

        if not recommendations:
            recommendations.append("All systems performing within acceptable parameters")

        return recommendations

    def generate_comprehensive_report(
        self, test_results: Dict[str, Any], validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive report combining test and validation results.

        Args:
            test_results: Results from recovery testing
            validation_results: Results from validation testing

        Returns:
            Comprehensive recovery report
        """
        # Track test results for compliance
        for result in test_results.get("results", []):
            self.compliance_tracker.track_test_result(result)

        # Generate compliance report
        compliance_report = self.compliance_tracker.generate_compliance_report()

        # Generate basic test report (inline to avoid circular dependency)
        basic_processed_results = []
        for db_type, results in test_results.items():
            basic_processed_results.append(
                {
                    "database_type": db_type,
                    "test_status": results.get("status", "unknown"),
                    "rto_compliance": results.get("rto_actual", 0) <= results.get("rto_target", float("inf")),
                    "rpo_compliance": results.get("rpo_actual", 0) <= results.get("rpo_target", float("inf")),
                    "data_integrity": results.get("data_integrity", False),
                }
            )

        test_report = {
            "executive_summary": {
                "total_databases_tested": len(test_results),
                "overall_success_rate": (
                    sum(1 for r in basic_processed_results if r["test_status"] == "success") / len(test_results) * 100
                    if test_results
                    else 0
                ),
            },
            "detailed_results": basic_processed_results,
        }

        # Combine reports
        comprehensive_report = {
            "report_metadata": {
                "report_type": "comprehensive_recovery_analysis",
                "generated_at": datetime.now().isoformat(),
                "includes_compliance_tracking": True,
            },
            "test_cycle_status": "completed",
            "executive_summary": {
                "test_summary": test_report.get("executive_summary", {}),
                "validation_summary": validation_results.get("system_status", "unknown"),
                "compliance_summary": compliance_report.get("executive_summary", {}),
            },
            "detailed_results": {
                "recovery_tests": test_report.get("detailed_results", []),
                "system_validation": validation_results,
                "compliance_analysis": compliance_report,
            },
            "compliance_status": {
                "overall_compliant": compliance_report.get("executive_summary", {}).get("systems_meeting_targets", 0)
                > 0,
                "critical_issues": compliance_report.get("critical_issues", []),
                "database_compliance": compliance_report.get("database_compliance", {}),
            },
            "consolidated_recommendations": self._consolidate_recommendations(
                test_report.get("recommendations", []),
                validation_results.get("recommendations", []),
                compliance_report.get("recommendations", []),
            ),
            "next_test_schedule": test_report.get("next_test_date", ""),
            "generated_at": datetime.now().isoformat(),
        }

        return comprehensive_report

    def _consolidate_recommendations(
        self,
        test_recs: List[str],
        validation_recs: List[str],
        compliance_recs: List[str],
    ) -> List[str]:
        """Consolidate recommendations from different sources."""
        all_recs = []

        # Add source prefixes and combine
        all_recs.extend([f"[Testing] {rec}" for rec in test_recs])
        all_recs.extend([f"[Validation] {rec}" for rec in validation_recs])
        all_recs.extend([f"[Compliance] {rec}" for rec in compliance_recs])

        # Remove duplicates while preserving order
        seen = set()
        unique_recs = []
        for rec in all_recs:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)

        return unique_recs
