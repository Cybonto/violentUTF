#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Compliance Monitoring Service for Issue #284

This service provides compliance monitoring and assessment functionality
for the database asset management dashboard system.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceFramework, ComplianceStatusModel

logger = logging.getLogger(__name__)


class ComplianceMonitoringService:
    """Service for managing compliance monitoring and assessments"""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize compliance monitoring service"""
        self.db = db

    async def get_compliance_status(self, asset_id: str, framework: str) -> Optional[ComplianceStatusModel]:
        """Get compliance status for an asset and framework"""
        try:
            framework_enum = ComplianceFramework(framework)

            query = (
                select(ComplianceStatusModel)
                .where(
                    and_(ComplianceStatusModel.asset_id == asset_id, ComplianceStatusModel.framework == framework_enum)
                )
                .order_by(desc(ComplianceStatusModel.assessment_date))
                .limit(1)
            )

            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting compliance status for asset %s, framework %s: %s", asset_id, framework, e)
            raise

    async def run_assessment(self, assessment_request: Dict[str, Any]) -> Dict[str, Any]:
        """Run a new compliance assessment"""
        try:
            asset_id = assessment_request["asset_id"]
            framework = assessment_request["framework"]
            include_recommendations = assessment_request.get("include_recommendations", False)

            # Mock compliance assessment logic
            # In a real implementation, this would integrate with compliance scanning tools

            if framework == "GDPR":
                overall_score = 78.5
                compliant = False
                gaps = [
                    {
                        "control_id": "Article 32",
                        "description": "Security of processing",
                        "status": "NON_COMPLIANT",
                        "severity": "HIGH",
                    }
                ]
            elif framework == "SOC2":
                overall_score = 85.5
                compliant = True
                gaps = [
                    {
                        "control_id": "CC6.1",
                        "description": "Logical access controls",
                        "status": "NON_COMPLIANT",
                        "severity": "MEDIUM",
                    }
                ]
            else:  # Default case
                overall_score = 80.0
                compliant = True
                gaps = []

            # Save assessment to database
            compliance_status = ComplianceStatusModel(
                asset_id=asset_id,
                framework=ComplianceFramework(framework),
                overall_score=overall_score,
                compliant=compliant,
                assessment_date=datetime.utcnow(),
                gaps=gaps,
            )

            self.db.add(compliance_status)
            await self.db.commit()
            await self.db.refresh(compliance_status)

            result = {
                "assessment_id": str(compliance_status.id),
                "asset_id": asset_id,
                "framework": framework,
                "overall_score": overall_score,
                "compliant": compliant,
                "gaps": gaps,
            }

            if include_recommendations:
                result["recommendations"] = await self._generate_recommendations(gaps)

            return result
        except Exception as e:
            await self.db.rollback()
            logger.error("Error running compliance assessment: %s", e)
            raise

    async def get_compliance_gaps(self, asset_id: str) -> List[Dict[str, Any]]:
        """Get compliance gaps and remediation recommendations for an asset"""
        try:
            # Get latest compliance assessments for all frameworks
            query = (
                select(ComplianceStatusModel)
                .where(ComplianceStatusModel.asset_id == asset_id)
                .order_by(desc(ComplianceStatusModel.assessment_date))
            )

            result = await self.db.execute(query)
            assessments = result.scalars().all()

            gaps = []
            for assessment in assessments:
                if assessment.gaps:
                    for gap in assessment.gaps:
                        gap_info = {
                            "asset_id": asset_id,
                            "framework": assessment.framework.value,
                            "control_id": gap.get("control_id"),
                            "description": gap.get("description"),
                            "severity": gap.get("severity"),
                            "remediation_steps": await self._get_remediation_steps(gap),
                            "estimated_effort": await self._estimate_remediation_effort(gap),
                        }
                        gaps.append(gap_info)

            return gaps
        except Exception as e:
            logger.error("Error getting compliance gaps for asset %s: %s", asset_id, e)
            raise

    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard-specific compliance data"""
        try:
            # Calculate overall compliance score
            overall_score_query = select(func.avg(ComplianceStatusModel.overall_score))
            overall_score_result = await self.db.execute(overall_score_query)
            overall_compliance_score = float(overall_score_result.scalar() or 0.0)

            # Get framework breakdown
            frameworks = {}
            for framework in ComplianceFramework:
                framework_query = select(
                    func.avg(ComplianceStatusModel.overall_score),
                    func.count(ComplianceStatusModel.id),
                    func.sum(func.case([(ComplianceStatusModel.compliant.is_(True), 1)], else_=0)),
                ).where(ComplianceStatusModel.framework == framework)

                framework_result = await self.db.execute(framework_query)
                avg_score, total_assessments, compliant_count = framework_result.fetchone()

                if total_assessments > 0:
                    # Count gaps for this framework
                    gaps_count = await self._count_gaps_for_framework(framework)

                    frameworks[framework.value] = {
                        "score": float(avg_score or 0.0),
                        "compliant": compliant_count == total_assessments,
                        "gaps": gaps_count,
                    }

            # Calculate trending information
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            sixty_days_ago = datetime.utcnow() - timedelta(days=60)

            # Current period average
            current_avg_query = select(func.avg(ComplianceStatusModel.overall_score)).where(
                ComplianceStatusModel.assessment_date >= thirty_days_ago
            )
            current_avg_result = await self.db.execute(current_avg_query)
            current_avg = float(current_avg_result.scalar() or 0.0)

            # Previous period average
            previous_avg_query = select(func.avg(ComplianceStatusModel.overall_score)).where(
                and_(
                    ComplianceStatusModel.assessment_date >= sixty_days_ago,
                    ComplianceStatusModel.assessment_date < thirty_days_ago,
                )
            )
            previous_avg_result = await self.db.execute(previous_avg_query)
            previous_avg = float(previous_avg_result.scalar() or 0.0)

            # Calculate trend
            if previous_avg > 0:
                change_percentage = ((current_avg - previous_avg) / previous_avg) * 100
                direction = "improving" if change_percentage > 0 else "declining"
            else:
                change_percentage = 0.0
                direction = "stable"

            # Count high priority gaps
            high_priority_gaps = await self._count_high_priority_gaps()

            # Count total assessed assets
            total_assets_query = select(func.count(ComplianceStatusModel.asset_id.distinct()))
            total_assets_result = await self.db.execute(total_assets_query)
            total_assets_assessed = total_assets_result.scalar() or 0

            return {
                "overall_compliance_score": round(overall_compliance_score, 1),
                "frameworks": frameworks,
                "trending": {
                    "direction": direction,
                    "change_percentage": round(change_percentage, 1),
                    "period": "30_days",
                },
                "high_priority_gaps": high_priority_gaps,
                "total_assets_assessed": total_assets_assessed,
            }

        except Exception as e:
            logger.error("Error getting compliance dashboard data: %s", e)
            raise

    async def _generate_recommendations(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate recommendations based on compliance gaps"""
        recommendations = []

        for gap in gaps:
            if gap.get("severity") == "HIGH":
                recommendations.append(
                    {
                        "priority": "HIGH",
                        "title": f"Address {gap.get('control_id')} compliance gap",
                        "description": f"Implement controls for {gap.get('description')}",
                        "estimated_effort": "2-4 weeks",
                    }
                )
            elif gap.get("severity") == "MEDIUM":
                recommendations.append(
                    {
                        "priority": "MEDIUM",
                        "title": f"Improve {gap.get('control_id')} compliance",
                        "description": f"Enhance controls for {gap.get('description')}",
                        "estimated_effort": "1-2 weeks",
                    }
                )

        return recommendations

    async def _get_remediation_steps(self, gap: Dict[str, Any]) -> List[str]:
        """Get remediation steps for a compliance gap"""
        control_id = gap.get("control_id", "")

        if "access" in control_id.lower() or "CC6" in control_id:
            return ["Implement multi-factor authentication", "Review user access permissions", "Enable audit logging"]
        elif "security" in gap.get("description", "").lower() or "Article 32" in control_id:
            return ["Implement encryption at rest", "Enable network security controls", "Conduct security assessments"]
        else:
            return ["Review compliance requirements", "Implement necessary controls", "Document compliance procedures"]

    async def _estimate_remediation_effort(self, gap: Dict[str, Any]) -> str:
        """Estimate effort required for remediation"""
        severity = gap.get("severity", "MEDIUM")

        if severity == "HIGH":
            return "2-4 weeks"
        elif severity == "MEDIUM":
            return "1-2 weeks"
        else:
            return "2-5 days"

    async def _count_gaps_for_framework(self, framework: ComplianceFramework) -> int:
        """Count gaps for a specific framework"""
        try:
            # This would query the database for gap counts
            # For now, return mock data
            return 2 if framework == ComplianceFramework.SOC2 else 5
        except Exception as e:
            logger.error("Error counting gaps for framework %s: %s", framework, e)
            return 0

    async def _count_high_priority_gaps(self) -> int:
        """Count high priority compliance gaps"""
        try:
            # This would query the database for high priority gaps
            # For now, return mock data
            return 3
        except Exception as e:
            logger.error("Error counting high priority gaps: %s", e)
            return 0
