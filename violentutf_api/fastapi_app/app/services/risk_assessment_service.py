#!/usr/bin/env python3
# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Risk Assessment Service for Issue #284

This service provides risk assessment functionality for the database asset
management dashboard system.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import AssetModel
from app.models.risk_assessment import RiskAssessmentModel

logger = logging.getLogger(__name__)


class RiskAssessmentService:
    """Service for managing risk assessments"""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize risk assessment service"""
        self.db = db

    async def create_assessment(self, assessment_data: Dict[str, Any]) -> RiskAssessmentModel:
        """Create a new risk assessment"""
        try:
            assessment = RiskAssessmentModel(**assessment_data)
            self.db.add(assessment)
            await self.db.commit()
            await self.db.refresh(assessment)
            return assessment
        except Exception as e:
            await self.db.rollback()
            logger.error("Error creating risk assessment: %s", e)
            raise

    async def get_latest_assessment(self, asset_id: str) -> Optional[RiskAssessmentModel]:
        """Get the latest risk assessment for an asset"""
        try:
            query = (
                select(RiskAssessmentModel)
                .where(RiskAssessmentModel.asset_id == asset_id)
                .order_by(desc(RiskAssessmentModel.assessment_date))
                .limit(1)
            )

            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Error getting latest assessment for asset %s: %s", asset_id, e)
            raise

    async def get_risk_trends(self, asset_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get risk trend data for an asset over time"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            query = (
                select(RiskAssessmentModel)
                .where(
                    and_(RiskAssessmentModel.asset_id == asset_id, RiskAssessmentModel.assessment_date >= start_date)
                )
                .order_by(RiskAssessmentModel.assessment_date)
            )

            result = await self.db.execute(query)
            assessments = result.scalars().all()

            trend_data = []
            for assessment in assessments:
                trend_data.append(
                    {
                        "date": assessment.assessment_date.strftime("%Y-%m-%d"),
                        "risk_score": float(assessment.risk_score),
                        "vulnerability_count": assessment.vulnerability_count,
                        "risk_level": assessment.risk_level.value,
                    }
                )

            return trend_data
        except Exception as e:
            logger.error("Error getting risk trends for asset %s: %s", asset_id, e)
            raise

    async def get_risk_predictions(self, asset_id: str) -> Dict[str, Any]:
        """Get risk predictions for an asset"""
        try:
            # Get recent assessments for trend analysis
            recent_assessments = await self.get_risk_trends(asset_id, days=90)

            if len(recent_assessments) < 2:
                return {
                    "asset_id": asset_id,
                    "current_risk": 0.0,
                    "predicted_risk_30_days": 0.0,
                    "confidence": 0.0,
                    "risk_factors_trending": [],
                    "recommended_actions": [],
                }

            # Simple linear trend prediction
            current_risk = recent_assessments[-1]["risk_score"]
            previous_risk = recent_assessments[-2]["risk_score"]
            trend = current_risk - previous_risk

            # Predict 30-day change
            predicted_risk = current_risk + (trend * 30)
            predicted_risk = max(0.0, min(25.0, predicted_risk))  # Clamp to valid range

            # Calculate confidence based on data consistency
            confidence = min(0.95, 0.5 + (len(recent_assessments) / 90) * 0.45)

            # Mock risk factors and recommendations
            risk_factors_trending = []
            if trend > 0:
                risk_factors_trending = ["increasing_vulnerabilities", "network_exposure"]

            recommended_actions = []
            if predicted_risk > 15.0:
                recommended_actions = [
                    "Update security patches",
                    "Implement network segmentation",
                    "Increase monitoring frequency",
                ]

            return {
                "asset_id": asset_id,
                "current_risk": current_risk,
                "predicted_risk_30_days": predicted_risk,
                "confidence": confidence,
                "risk_factors_trending": risk_factors_trending,
                "recommended_actions": recommended_actions,
            }
        except Exception as e:
            logger.error("Error getting risk predictions for asset %s: %s", asset_id, e)
            raise

    async def bulk_assess_risks(self, asset_ids: List[str]) -> List[Dict[str, Any]]:
        """Perform bulk risk assessment for multiple assets"""
        try:
            assessments = []

            for asset_id in asset_ids:
                # Get latest assessment
                latest = await self.get_latest_assessment(asset_id)

                if latest:
                    assessments.append(
                        {
                            "asset_id": asset_id,
                            "risk_score": float(latest.risk_score),
                            "risk_level": latest.risk_level.value,
                            "vulnerability_count": latest.vulnerability_count,
                            "assessment_date": latest.assessment_date.isoformat(),
                        }
                    )
                else:
                    # Create mock assessment for assets without data
                    assessments.append(
                        {
                            "asset_id": asset_id,
                            "risk_score": 10.0,
                            "risk_level": "MEDIUM",
                            "vulnerability_count": 0,
                            "assessment_date": datetime.utcnow().isoformat(),
                        }
                    )

            return assessments
        except Exception as e:
            logger.error("Error performing bulk risk assessment: %s", e)
            raise

    async def get_high_risk_assets(self, threshold: float = 15.0) -> List[Dict[str, Any]]:
        """Get assets with risk scores above threshold"""
        try:
            # Get latest assessments for each asset
            subquery = (
                select(RiskAssessmentModel.asset_id, func.max(RiskAssessmentModel.assessment_date).label("latest_date"))
                .group_by(RiskAssessmentModel.asset_id)
                .subquery()
            )

            query = (
                select(RiskAssessmentModel, AssetModel.name)
                .select_from(
                    RiskAssessmentModel.__table__.join(
                        subquery,
                        and_(
                            RiskAssessmentModel.asset_id == subquery.c.asset_id,
                            RiskAssessmentModel.assessment_date == subquery.c.latest_date,
                        ),
                    ).join(AssetModel)
                )
                .where(RiskAssessmentModel.risk_score > threshold)
                .order_by(desc(RiskAssessmentModel.risk_score))
            )

            result = await self.db.execute(query)
            high_risk_data = []

            for assessment, asset_name in result.fetchall():
                high_risk_data.append(
                    {
                        "asset_id": assessment.asset_id,
                        "asset_name": asset_name,
                        "risk_score": float(assessment.risk_score),
                        "risk_level": assessment.risk_level.value,
                        "vulnerability_count": assessment.vulnerability_count,
                        "assessment_date": assessment.assessment_date.isoformat(),
                    }
                )

            return high_risk_data
        except Exception as e:
            logger.error("Error getting high-risk assets: %s", e)
            raise

    async def calculate_risk_velocity(self, days: int = 30) -> float:
        """Calculate overall risk velocity (change in average risk over time)"""
        try:
            # Get current period average
            current_start = datetime.utcnow() - timedelta(days=days)
            current_avg_query = select(func.avg(RiskAssessmentModel.risk_score)).where(
                RiskAssessmentModel.assessment_date >= current_start
            )
            current_avg_result = await self.db.execute(current_avg_query)
            current_avg = float(current_avg_result.scalar() or 0.0)

            # Get previous period average
            previous_start = datetime.utcnow() - timedelta(days=days * 2)
            previous_end = current_start
            previous_avg_query = select(func.avg(RiskAssessmentModel.risk_score)).where(
                and_(
                    RiskAssessmentModel.assessment_date >= previous_start,
                    RiskAssessmentModel.assessment_date < previous_end,
                )
            )
            previous_avg_result = await self.db.execute(previous_avg_query)
            previous_avg = float(previous_avg_result.scalar() or 0.0)

            # Calculate velocity (change per day)
            if previous_avg > 0:
                velocity = (current_avg - previous_avg) / days
            else:
                velocity = 0.0

            return velocity
        except Exception as e:
            logger.error("Error calculating risk velocity: %s", e)
            raise
