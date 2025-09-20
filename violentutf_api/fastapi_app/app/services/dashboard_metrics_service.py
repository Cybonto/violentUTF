#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Dashboard Metrics Service for Issue #284

This service provides dashboard-specific metrics aggregation and KPI calculations
for the database asset management dashboard system.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetModel, CriticalityLevel
from app.models.compliance import ComplianceStatusModel
from app.models.risk_assessment import RiskAssessmentModel, RiskLevel
from app.services.asset_management.asset_service import AssetService
from app.services.compliance_monitoring_service import ComplianceMonitoringService
from app.services.risk_assessment_service import RiskAssessmentService

logger = logging.getLogger(__name__)


class DashboardMetricsService:
    """Service for calculating dashboard metrics and KPIs"""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize dashboard metrics service"""
        self.db = db
        self.asset_service = AssetService(db)
        self.risk_service = RiskAssessmentService(db)
        self.compliance_service = ComplianceMonitoringService(db)

    async def get_asset_inventory_metrics(self) -> Dict[str, Any]:
        """Get comprehensive asset inventory dashboard metrics"""
        try:
            # Get total asset count
            total_assets_query = select(func.count(AssetModel.id))
            total_assets_result = await self.db.execute(total_assets_query)
            total_assets = total_assets_result.scalar() or 0

            # Get assets by type
            assets_by_type_query = select(AssetModel.asset_type, func.count(AssetModel.id)).group_by(
                AssetModel.asset_type
            )
            assets_by_type_result = await self.db.execute(assets_by_type_query)
            assets_by_type = {asset_type.value: count for asset_type, count in assets_by_type_result.fetchall()}

            # Get assets by environment
            assets_by_env_query = select(AssetModel.environment, func.count(AssetModel.id)).group_by(
                AssetModel.environment
            )
            assets_by_env_result = await self.db.execute(assets_by_env_query)
            assets_by_environment = {env.value: count for env, count in assets_by_env_result.fetchall()}

            # Get critical assets count
            critical_assets_query = select(func.count(AssetModel.id)).where(
                AssetModel.criticality_level == CriticalityLevel.CRITICAL
            )
            critical_assets_result = await self.db.execute(critical_assets_query)
            critical_assets = critical_assets_result.scalar() or 0

            # Get high-risk assets count (risk score > 15)
            high_risk_subquery = (
                select(RiskAssessmentModel.asset_id).where(RiskAssessmentModel.risk_score > 15.0).distinct()
            )
            high_risk_assets_query = select(func.count()).select_from(
                select(AssetModel.id).where(AssetModel.id.in_(high_risk_subquery)).subquery()
            )
            high_risk_assets_result = await self.db.execute(high_risk_assets_query)
            high_risk_assets = high_risk_assets_result.scalar() or 0

            # Calculate average compliance score
            compliance_avg_query = select(func.avg(ComplianceStatusModel.overall_score))
            compliance_avg_result = await self.db.execute(compliance_avg_query)
            compliance_score = float(compliance_avg_result.scalar() or 0.0)

            # Calculate monitoring coverage (assets with recent risk assessments)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            monitored_assets_query = select(func.count(RiskAssessmentModel.asset_id.distinct())).where(
                RiskAssessmentModel.assessment_date >= thirty_days_ago
            )
            monitored_assets_result = await self.db.execute(monitored_assets_query)
            monitored_assets = monitored_assets_result.scalar() or 0
            monitoring_coverage = (monitored_assets / total_assets * 100) if total_assets > 0 else 0.0

            return {
                "total_assets": total_assets,
                "assets_by_type": assets_by_type,
                "assets_by_environment": assets_by_environment,
                "critical_assets": critical_assets,
                "high_risk_assets": high_risk_assets,
                "compliance_score": round(compliance_score, 1),
                "monitoring_coverage": round(monitoring_coverage, 1),
            }

        except Exception as e:
            logger.error("Error calculating asset inventory metrics: %s", e)
            raise

    async def get_risk_dashboard_metrics(self) -> Dict[str, Any]:
        """Get risk dashboard metrics and trends"""
        try:
            # Calculate average risk score
            avg_risk_query = select(func.avg(RiskAssessmentModel.risk_score))
            avg_risk_result = await self.db.execute(avg_risk_query)
            average_risk_score = float(avg_risk_result.scalar() or 0.0)

            # Get risk distribution
            risk_dist_query = select(RiskAssessmentModel.risk_level, func.count(RiskAssessmentModel.id)).group_by(
                RiskAssessmentModel.risk_level
            )
            risk_dist_result = await self.db.execute(risk_dist_query)
            risk_distribution = {risk_level.value: count for risk_level, count in risk_dist_result.fetchall()}

            # Calculate risk velocity (change over last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)

            # Current average risk
            current_avg_query = select(func.avg(RiskAssessmentModel.risk_score)).where(
                RiskAssessmentModel.assessment_date >= thirty_days_ago
            )
            current_avg_result = await self.db.execute(current_avg_query)
            current_avg = float(current_avg_result.scalar() or 0.0)

            # Previous period average risk
            sixty_days_ago = datetime.utcnow() - timedelta(days=60)
            previous_avg_query = select(func.avg(RiskAssessmentModel.risk_score)).where(
                and_(
                    RiskAssessmentModel.assessment_date >= sixty_days_ago,
                    RiskAssessmentModel.assessment_date < thirty_days_ago,
                )
            )
            previous_avg_result = await self.db.execute(previous_avg_query)
            previous_avg = float(previous_avg_result.scalar() or 0.0)

            risk_velocity = (current_avg - previous_avg) / 30 if previous_avg > 0 else 0.0

            # Get predicted 30-day change (simplified prediction)
            predicted_30_day_change = risk_velocity * 30

            # Get high priority vulnerabilities count
            high_vuln_query = select(func.sum(RiskAssessmentModel.vulnerability_count)).where(
                RiskAssessmentModel.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL])
            )
            high_vuln_result = await self.db.execute(high_vuln_query)
            high_priority_vulnerabilities = int(high_vuln_result.scalar() or 0)

            # Get assets requiring attention (high risk)
            high_risk_assets_query = (
                select(AssetModel.id, AssetModel.name, RiskAssessmentModel.risk_score)
                .select_from(AssetModel.__table__.join(RiskAssessmentModel))
                .where(RiskAssessmentModel.risk_score > 15.0)
                .order_by(RiskAssessmentModel.risk_score.desc())
                .limit(10)
            )

            high_risk_assets_result = await self.db.execute(high_risk_assets_query)
            assets_requiring_attention = [
                {"asset_id": asset_id, "asset_name": asset_name, "risk_score": float(risk_score)}
                for asset_id, asset_name, risk_score in high_risk_assets_result.fetchall()
            ]

            return {
                "average_risk_score": round(average_risk_score, 1),
                "risk_distribution": risk_distribution,
                "risk_velocity": round(risk_velocity, 3),
                "predicted_30_day_change": round(predicted_30_day_change, 1),
                "high_priority_vulnerabilities": high_priority_vulnerabilities,
                "assets_requiring_attention": assets_requiring_attention,
            }

        except Exception as e:
            logger.error("Error calculating risk dashboard metrics: %s", e)
            raise

    async def get_executive_report_data(self) -> Dict[str, Any]:
        """Get executive-level dashboard data and KPIs"""
        try:
            # Get basic summary metrics
            total_assets_query = select(func.count(AssetModel.id))
            total_assets_result = await self.db.execute(total_assets_query)
            total_assets = total_assets_result.scalar() or 0

            # Calculate security posture score (weighted average of risk and compliance)
            avg_risk_query = select(func.avg(RiskAssessmentModel.risk_score))
            avg_risk_result = await self.db.execute(avg_risk_query)
            avg_risk = float(avg_risk_result.scalar() or 0.0)

            avg_compliance_query = select(func.avg(ComplianceStatusModel.overall_score))
            avg_compliance_result = await self.db.execute(avg_compliance_query)
            avg_compliance = float(avg_compliance_result.scalar() or 0.0)

            # Security posture score (inverse of risk + compliance)
            security_posture_score = ((25 - avg_risk) / 25 * 50) + (avg_compliance / 100 * 50)

            # Get critical findings count
            critical_findings_query = select(func.count(RiskAssessmentModel.id)).where(
                RiskAssessmentModel.risk_level == RiskLevel.CRITICAL
            )
            critical_findings_result = await self.db.execute(critical_findings_query)
            critical_findings = critical_findings_result.scalar() or 0

            # Calculate trends (30-day comparison)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            sixty_days_ago = datetime.utcnow() - timedelta(days=60)

            # Security improvement trend
            current_period_risk = await self._get_average_risk_for_period(thirty_days_ago, datetime.utcnow())
            previous_period_risk = await self._get_average_risk_for_period(sixty_days_ago, thirty_days_ago)

            security_improvement = (
                ((previous_period_risk - current_period_risk) / previous_period_risk * 100)
                if previous_period_risk > 0
                else 0.0
            )

            # New assets in last 30 days
            new_assets_query = select(func.count(AssetModel.id)).where(AssetModel.created_at >= thirty_days_ago)
            new_assets_result = await self.db.execute(new_assets_query)
            new_assets_30_days = new_assets_result.scalar() or 0

            # Mock data for demonstration (in real implementation, these would come from vulnerability tracking)
            resolved_vulnerabilities = 23
            compliance_improvement = 2.1

            # Generate recommendations based on current data
            recommendations = await self._generate_recommendations()

            # Cost impact analysis (simplified)
            cost_impact = {"security_investment": 150000, "potential_savings": 2500000, "roi_percentage": 1667}

            return {
                "summary": {
                    "total_assets": total_assets,
                    "security_posture_score": round(security_posture_score, 1),
                    "compliance_percentage": round(avg_compliance, 1),
                    "critical_findings": critical_findings,
                },
                "trends": {
                    "security_improvement": round(security_improvement, 1),
                    "new_assets_30_days": new_assets_30_days,
                    "resolved_vulnerabilities": resolved_vulnerabilities,
                    "compliance_improvement": compliance_improvement,
                },
                "recommendations": recommendations,
                "cost_impact": cost_impact,
            }

        except Exception as e:
            logger.error("Error generating executive report data: %s", e)
            raise

    async def get_operational_dashboard_metrics(self) -> Dict[str, Any]:
        """Get operational dashboard metrics for system monitoring"""
        try:
            # System health metrics (simplified - in real implementation would integrate with monitoring systems)
            system_health = {
                "api_response_time": 150,  # milliseconds
                "database_connections": 45,
                "error_rate": 0.02,  # 2%
                "uptime_percentage": 99.95,
            }

            # Get recent alerts (simplified)
            alerts = [
                {
                    "severity": "HIGH",
                    "message": "High risk asset requires immediate attention",
                    "timestamp": datetime.utcnow().isoformat(),
                    "asset_id": "asset-123",
                }
            ]

            # Performance metrics
            performance_metrics = {
                "avg_query_time": 45,  # milliseconds
                "throughput_requests_per_second": 1250,
                "memory_usage_percentage": 75.2,
            }

            return {"system_health": system_health, "alerts": alerts, "performance_metrics": performance_metrics}

        except Exception as e:
            logger.error("Error getting operational dashboard metrics: %s", e)
            raise

    async def _get_average_risk_for_period(self, start_date: datetime, end_date: datetime) -> float:
        """Get average risk score for a specific time period"""
        avg_query = select(func.avg(RiskAssessmentModel.risk_score)).where(
            and_(RiskAssessmentModel.assessment_date >= start_date, RiskAssessmentModel.assessment_date < end_date)
        )
        result = await self.db.execute(avg_query)
        return float(result.scalar() or 0.0)

    async def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate recommendations based on current metrics"""
        recommendations = []

        # Check for high-risk assets
        high_risk_count_query = select(func.count(RiskAssessmentModel.id)).where(RiskAssessmentModel.risk_score > 20.0)
        high_risk_count_result = await self.db.execute(high_risk_count_query)
        high_risk_count = high_risk_count_result.scalar() or 0

        if high_risk_count > 0:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "title": f"Address {high_risk_count} critical risk assets",
                    "impact": "Reduce security risk by 15%",
                    "effort": "2-4 weeks",
                }
            )

        # Check for compliance gaps
        low_compliance_query = select(func.count(ComplianceStatusModel.id)).where(
            ComplianceStatusModel.overall_score < 80.0
        )
        low_compliance_result = await self.db.execute(low_compliance_query)
        low_compliance_count = low_compliance_result.scalar() or 0

        if low_compliance_count > 0:
            recommendations.append(
                {
                    "priority": "MEDIUM",
                    "title": f"Improve compliance for {low_compliance_count} assets",
                    "impact": "Increase compliance score by 10%",
                    "effort": "3-6 weeks",
                }
            )

        return recommendations
