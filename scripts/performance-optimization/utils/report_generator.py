# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Report generation utilities for performance optimization."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict


class ReportGenerator:
    """Generate performance optimization reports."""

    def __init__(self: ReportGenerator) -> None:
        """Initialize report generator."""
        self.report_data: Dict[str, Any] = {}

    def generate_json_report(self: ReportGenerator, data: Dict[str, Any], output_path: str) -> None:
        """Generate JSON format report.

        Args:
            data: Report data
            output_path: Path to save report
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Add metadata
        report = {
            "generated_at": datetime.now().isoformat(),
            "version": "1.0.0",
            "data": data,
        }

        # Write report
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

    def generate_markdown_report(self: ReportGenerator, data: Dict[str, Any], output_path: str) -> None:
        """Generate Markdown format report.

        Args:
            data: Report data
            output_path: Path to save report
        """
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        lines = [
            "# Performance Optimization Report",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
        ]

        # Add sections based on data
        if "metrics" in data:
            lines.extend(self._format_metrics_section(data["metrics"]))

        if "queries" in data:
            lines.extend(self._format_queries_section(data["queries"]))

        if "indexes" in data:
            lines.extend(self._format_indexes_section(data["indexes"]))

        # Write report
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _format_metrics_section(self: ReportGenerator, metrics: Dict[str, Any]) -> list:
        """Format metrics section.

        Args:
            metrics: Metrics data

        Returns:
            List of formatted lines
        """
        lines = ["## Performance Metrics", ""]

        for key, value in metrics.items():
            lines.append(f"- **{key}**: {value}")

        lines.append("")
        return lines

    def _format_queries_section(self: ReportGenerator, queries: list) -> list:
        """Format queries section.

        Args:
            queries: List of query data

        Returns:
            List of formatted lines
        """
        lines = ["## Query Analysis", ""]

        for i, query in enumerate(queries, 1):
            lines.append(f"### Query {i}")
            lines.append("")
            if "query" in query:
                lines.append(f"```sql\n{query['query']}\n```")
                lines.append("")
            if "time" in query:
                lines.append(f"- Execution time: {query['time']} ms")
            lines.append("")

        return lines

    def _format_indexes_section(self: ReportGenerator, indexes: list) -> list:
        """Format indexes section.

        Args:
            indexes: List of index data

        Returns:
            List of formatted lines
        """
        lines = ["## Index Analysis", ""]

        for index in indexes:
            if "name" in index:
                lines.append(f"### {index['name']}")
                lines.append("")
                if "table" in index:
                    lines.append(f"- Table: {index['table']}")
                if "columns" in index:
                    lines.append(f"- Columns: {', '.join(index['columns'])}")
                lines.append("")

        return lines

    def compare_reports(self: ReportGenerator, baseline_path: str, current_path: str, output_path: str) -> None:
        """Generate comparison report.

        Args:
            baseline_path: Path to baseline report
            current_path: Path to current report
            output_path: Path to save comparison report
        """
        # Load reports
        with open(baseline_path, encoding="utf-8") as f:
            baseline = json.load(f)

        with open(current_path, encoding="utf-8") as f:
            current = json.load(f)

        # Generate comparison
        comparison = {
            "baseline_generated": baseline.get("generated_at"),
            "current_generated": current.get("generated_at"),
            "improvements": self._calculate_improvements(baseline.get("data", {}), current.get("data", {})),
        }

        # Save comparison
        self.generate_json_report(comparison, output_path)

    def _calculate_improvements(
        self: ReportGenerator, baseline: Dict[str, Any], current: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate improvements between baseline and current.

        Args:
            baseline: Baseline metrics
            current: Current metrics

        Returns:
            Dictionary of improvements
        """
        improvements = {}

        # Compare metrics if available
        if "metrics" in baseline and "metrics" in current:
            baseline_metrics = baseline["metrics"]
            current_metrics = current["metrics"]

            for key in baseline_metrics:
                if key in current_metrics:
                    if isinstance(baseline_metrics[key], (int, float)):
                        baseline_val = baseline_metrics[key]
                        current_val = current_metrics[key]

                        # Calculate percentage improvement
                        if baseline_val != 0:
                            improvement = ((current_val - baseline_val) / baseline_val) * 100
                            improvements[key] = {
                                "baseline": baseline_val,
                                "current": current_val,
                                "improvement_percent": improvement,
                            }

        return improvements
