# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""Reporting service for database discovery results."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.discovery import DiscoveredDatabase as DBDiscoveredDatabase
from ...models.discovery import DiscoveryExecution as DBDiscoveryExecution
from ...models.discovery import DiscoveryReport as DBDiscoveryReport
from ...models.discovery import SecurityFinding as DBSecurityFinding
from ...schemas.discovery import DiscoveredDatabase, DiscoveryReport, DiscoveryReportWithDatabases


class ReportingService:
    """Service for generating and managing discovery reports."""

    def __init__(self) -> None:
        """Initialize the reporting service."""
        self.logger = logging.getLogger(__name__)

    async def get_reports(self, db: AsyncSession, limit: int = 50, offset: int = 0) -> List[DiscoveryReport]:
        """Get discovery reports."""
        query = select(DBDiscoveryReport).order_by(DBDiscoveryReport.generated_at.desc()).offset(offset).limit(limit)

        result = await db.execute(query)
        db_reports = result.scalars().all()

        return [DiscoveryReport.model_validate(report) for report in db_reports]

    async def get_report_by_id(
        self, db: AsyncSession, report_id: str, include_databases: bool = False
    ) -> Optional[DiscoveryReport]:
        """Get a specific report by ID."""
        query = select(DBDiscoveryReport).where(DBDiscoveryReport.report_id == report_id)
        result = await db.execute(query)
        db_report = result.scalar_one_or_none()

        if not db_report:
            return None

        if include_databases:
            # Get associated databases
            db_query = select(DBDiscoveredDatabase).where(
                DBDiscoveredDatabase.discovered_at >= db_report.generated_at - timedelta(minutes=5),
                DBDiscoveredDatabase.discovered_at <= db_report.generated_at + timedelta(minutes=5),
            )
            db_result = await db.execute(db_query)
            databases = [DiscoveredDatabase.model_validate(db) for db in db_result.scalars().all()]

            report_data = DiscoveryReportWithDatabases.model_validate(db_report)
            report_data.databases = databases
            return report_data

        return DiscoveryReport.model_validate(db_report)

    async def delete_report(self, db: AsyncSession, report_id: str) -> bool:
        """Delete a discovery report."""
        query = select(DBDiscoveryReport).where(DBDiscoveryReport.report_id == report_id)
        result = await db.execute(query)
        db_report = result.scalar_one_or_none()

        if not db_report:
            return False

        await db.delete(db_report)
        await db.commit()

        return True

    async def generate_summary_report(self, db: AsyncSession, days_back: int = 30) -> Dict[str, Any]:
        """Generate a summary report of discovery activity."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get discovery counts over time
        discovery_counts = await self._get_discovery_counts_over_time(db, cutoff_date)

        # Get database type trends
        type_trends = await self._get_database_type_trends(db, cutoff_date)

        # Get security findings summary
        security_summary = await self._get_security_findings_summary(db, cutoff_date)

        # Get execution statistics
        execution_stats = await self._get_execution_statistics(db, cutoff_date)

        # Get top discovered databases
        top_databases = await self._get_top_databases(db, cutoff_date)

        return {
            "report_generated_at": datetime.utcnow().isoformat(),
            "period_days": days_back,
            "discovery_counts": discovery_counts,
            "database_type_trends": type_trends,
            "security_summary": security_summary,
            "execution_statistics": execution_stats,
            "top_databases": top_databases,
        }

    async def _get_discovery_counts_over_time(self, db: AsyncSession, cutoff_date: datetime) -> List[Dict[str, Any]]:
        """Get discovery counts grouped by day."""
        query = (
            select(
                func.date(DBDiscoveredDatabase.discovered_at).label("date"),
                func.count(DBDiscoveredDatabase.id).label("count"),
            )
            .where(DBDiscoveredDatabase.discovered_at >= cutoff_date)
            .group_by(func.date(DBDiscoveredDatabase.discovered_at))
            .order_by("date")
        )

        result = await db.execute(query)

        return [{"date": row.date.isoformat(), "count": row.count} for row in result]

    async def _get_database_type_trends(self, db: AsyncSession, cutoff_date: datetime) -> Dict[str, Any]:
        """Get database type distribution trends."""
        # Current distribution
        current_query = (
            select(DBDiscoveredDatabase.database_type, func.count(DBDiscoveredDatabase.id).label("count"))
            .where(DBDiscoveredDatabase.discovered_at >= cutoff_date)
            .group_by(DBDiscoveredDatabase.database_type)
        )

        current_result = await db.execute(current_query)
        current_distribution = {row.database_type: row.count for row in current_result}

        # Historical comparison (if we have older data)
        historical_cutoff = cutoff_date - timedelta(days=30)
        historical_query = (
            select(DBDiscoveredDatabase.database_type, func.count(DBDiscoveredDatabase.id).label("count"))
            .where(
                and_(
                    DBDiscoveredDatabase.discovered_at >= historical_cutoff,
                    DBDiscoveredDatabase.discovered_at < cutoff_date,
                )
            )
            .group_by(DBDiscoveredDatabase.database_type)
        )

        historical_result = await db.execute(historical_query)
        historical_distribution = {row.database_type: row.count for row in historical_result}

        return {
            "current_period": current_distribution,
            "previous_period": historical_distribution,
            "changes": {
                db_type: current_distribution.get(db_type, 0) - historical_distribution.get(db_type, 0)
                for db_type in set(list(current_distribution.keys()) + list(historical_distribution.keys()))
            },
        }

    async def _get_security_findings_summary(self, db: AsyncSession, cutoff_date: datetime) -> Dict[str, Any]:
        """Get security findings summary."""
        # Total findings
        total_query = select(func.count(DBSecurityFinding.id)).where(DBSecurityFinding.created_at >= cutoff_date)
        total_result = await db.execute(total_query)
        total_findings = total_result.scalar()

        # Findings by severity
        severity_query = (
            select(DBSecurityFinding.severity, func.count(DBSecurityFinding.id).label("count"))
            .where(DBSecurityFinding.created_at >= cutoff_date)
            .group_by(DBSecurityFinding.severity)
        )

        severity_result = await db.execute(severity_query)
        severity_distribution = {row.severity: row.count for row in severity_result}

        # Findings by type
        type_query = (
            select(DBSecurityFinding.finding_type, func.count(DBSecurityFinding.id).label("count"))
            .where(DBSecurityFinding.created_at >= cutoff_date)
            .group_by(DBSecurityFinding.finding_type)
        )

        type_result = await db.execute(type_query)
        type_distribution = {row.finding_type: row.count for row in type_result}

        # False positive rate
        false_positive_query = select(
            func.count(DBSecurityFinding.id).label("total"),
            func.sum(func.cast(DBSecurityFinding.is_false_positive, "integer")).label("false_positives"),
        ).where(DBSecurityFinding.created_at >= cutoff_date)

        fp_result = await db.execute(false_positive_query)
        fp_row = fp_result.first()
        false_positive_rate = (fp_row.false_positives / fp_row.total * 100) if fp_row.total > 0 else 0

        return {
            "total_findings": total_findings,
            "severity_distribution": severity_distribution,
            "type_distribution": type_distribution,
            "false_positive_rate": round(false_positive_rate, 2),
        }

    async def _get_execution_statistics(self, db: AsyncSession, cutoff_date: datetime) -> Dict[str, Any]:
        """Get discovery execution statistics."""
        # Total executions
        total_query = select(func.count(DBDiscoveryExecution.id)).where(DBDiscoveryExecution.started_at >= cutoff_date)
        total_result = await db.execute(total_query)
        total_executions = total_result.scalar()

        # Success rate
        success_query = select(
            func.count(DBDiscoveryExecution.id).label("total"),
            func.sum(func.case((DBDiscoveryExecution.status == "completed", 1), else_=0)).label("successful"),
        ).where(DBDiscoveryExecution.started_at >= cutoff_date)

        success_result = await db.execute(success_query)
        success_row = success_result.first()
        success_rate = (success_row.successful / success_row.total * 100) if success_row.total > 0 else 0

        # Average execution time
        avg_time_query = select(func.avg(DBDiscoveryExecution.execution_time_seconds)).where(
            and_(
                DBDiscoveryExecution.started_at >= cutoff_date, DBDiscoveryExecution.execution_time_seconds.isnot(None)
            )
        )

        avg_time_result = await db.execute(avg_time_query)
        avg_execution_time = avg_time_result.scalar() or 0

        # Average discoveries per execution
        avg_discoveries_query = select(func.avg(DBDiscoveryExecution.discoveries_found)).where(
            DBDiscoveryExecution.started_at >= cutoff_date
        )

        avg_discoveries_result = await db.execute(avg_discoveries_query)
        avg_discoveries = avg_discoveries_result.scalar() or 0

        return {
            "total_executions": total_executions,
            "success_rate": round(success_rate, 2),
            "average_execution_time_seconds": round(avg_execution_time, 2),
            "average_discoveries_per_execution": round(avg_discoveries, 2),
        }

    async def _get_top_databases(
        self, db: AsyncSession, cutoff_date: datetime, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top discovered databases by confidence score."""
        query = (
            select(
                DBDiscoveredDatabase.database_id,
                DBDiscoveredDatabase.name,
                DBDiscoveredDatabase.database_type,
                DBDiscoveredDatabase.confidence_score,
                DBDiscoveredDatabase.discovery_method,
                DBDiscoveredDatabase.discovered_at,
            )
            .where(DBDiscoveredDatabase.discovered_at >= cutoff_date)
            .order_by(DBDiscoveredDatabase.confidence_score.desc(), DBDiscoveredDatabase.discovered_at.desc())
            .limit(limit)
        )

        result = await db.execute(query)

        return [
            {
                "database_id": row.database_id,
                "name": row.name,
                "database_type": row.database_type,
                "confidence_score": row.confidence_score,
                "discovery_method": row.discovery_method,
                "discovered_at": row.discovered_at.isoformat(),
            }
            for row in result
        ]

    async def export_report_to_json(self, db: AsyncSession, report_id: str, output_path: Optional[str] = None) -> str:
        """Export a report to JSON file."""
        report = await self.get_report_by_id(db, report_id, include_databases=True)

        if not report:
            raise ValueError(f"Report {report_id} not found")

        # Convert to JSON
        report_json = report.model_dump(mode="json")

        # Determine output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"discovery_report_{report_id}_{timestamp}.json"

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2, default=str)

        self.logger.info("Report exported to: %s", output_file)
        return str(output_file)

    async def export_report_to_markdown(
        self, db: AsyncSession, report_id: str, output_path: Optional[str] = None
    ) -> str:
        """Export a report to Markdown file."""
        report = await self.get_report_by_id(db, report_id, include_databases=True)

        if not report:
            raise ValueError(f"Report {report_id} not found")

        # Generate Markdown content
        markdown_content = self._generate_markdown_report(report)

        # Determine output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"discovery_report_{report_id}_{timestamp}.md"

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write Markdown file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        self.logger.info("Report exported to: %s", output_file)
        return str(output_file)

    def _generate_markdown_report(self, report: DiscoveryReportWithDatabases) -> str:
        """Generate Markdown content for a report."""
        md = f"""# Database Discovery Report

**Report ID:** {report.report_id}
**Generated:** {report.generated_at.isoformat()}
**Execution Time:** {report.execution_time_seconds:.2f} seconds

## Executive Summary

- **Total Databases Found:** {report.total_discoveries}
- **Security Findings:** {report.security_findings_count}
- **Credential Exposures:** {report.credential_exposures}
- **High Severity Issues:** {report.high_severity_findings}
- **Validated Discoveries:** {report.validated_discoveries}

## Database Types

"""

        for db_type, count in report.type_counts.items():
            md += f"- **{db_type.title()}:** {count}\n"

        md += "\n## Discovery Methods\n\n"

        for method, count in report.method_counts.items():
            md += f"- **{method.replace('_', ' ').title()}:** {count}\n"

        md += "\n## Confidence Distribution\n\n"

        for confidence, count in report.confidence_distribution.items():
            md += f"- **{confidence.title()}:** {count}\n"

        if hasattr(report, "databases") and report.databases:
            md += "\n## Discovered Databases\n\n"

            for i, discovery in enumerate(report.databases, 1):
                md += f"### {i}. {discovery.name}\n\n"
                md += f"- **Type:** {discovery.database_type}\n"
                md += f"- **Method:** {discovery.discovery_method}\n"
                md += f"- **Confidence:** {discovery.confidence_level} ({discovery.confidence_score:.2f})\n"
                md += f"- **Active:** {'Yes' if discovery.is_active else 'No'}\n"
                md += f"- **Validated:** {'Yes' if discovery.is_validated else 'No'}\n"

                if discovery.host:
                    md += f"- **Host:** {discovery.host}\n"
                if discovery.port:
                    md += f"- **Port:** {discovery.port}\n"
                if discovery.file_path:
                    md += f"- **File:** {discovery.file_path}\n"

                if discovery.security_findings:
                    md += f"- **Security Findings:** {len(discovery.security_findings)}\n"
                    for finding in discovery.security_findings[:3]:  # Show first 3
                        md += f"  - {finding.severity.upper()}: {finding.description}\n"
                    if len(discovery.security_findings) > 3:
                        md += f"  - ... and {len(discovery.security_findings) - 3} more\n"

                if discovery.tags:
                    md += f"- **Tags:** {', '.join(discovery.tags)}\n"

                md += "\n"

        if report.security_findings_count > 0:
            md += "\n## Security Summary\n\n"
            md += f"- **Total Security Findings:** {report.security_findings_count}\n"
            md += f"- **Credential Exposures:** {report.credential_exposures}\n"
            md += f"- **High Severity:** {report.high_severity_findings}\n"

        md += "\n## Configuration\n\n"
        for scope_item in report.discovery_scope:
            md += f"- {scope_item}\n"

        if report.processing_stats:
            md += "\n## Performance Metrics\n\n"
            for metric, value in report.processing_stats.items():
                if isinstance(value, float):
                    md += f"- **{metric.replace('_', ' ').title()}:** {value:.2f}s\n"
                else:
                    md += f"- **{metric.replace('_', ' ').title()}:** {value}\n"

        return md

    async def cleanup_old_reports(self, db: AsyncSession, days_to_keep: int = 90) -> int:
        """Clean up old discovery reports."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        # Count reports to delete
        count_query = select(func.count(DBDiscoveryReport.id)).where(DBDiscoveryReport.generated_at < cutoff_date)
        count_result = await db.execute(count_query)
        reports_to_delete = count_result.scalar()

        if reports_to_delete == 0:
            return 0

        # Delete old reports
        delete_query = select(DBDiscoveryReport).where(DBDiscoveryReport.generated_at < cutoff_date)
        delete_result = await db.execute(delete_query)
        old_reports = delete_result.scalars().all()

        for report in old_reports:
            await db.delete(report)

        await db.commit()

        self.logger.info("Cleaned up %d old discovery reports", reports_to_delete)
        return reports_to_delete
