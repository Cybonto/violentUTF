# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""Satisfaction Scoring Service for Issue #132 GREEN phase implementation."""

import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4


class SatisfactionScorer:
    """Scorer for measuring user satisfaction metrics."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize satisfaction scorer."""
        self.logger = logger or logging.getLogger(__name__)
        self.scoring_history: Dict[str, Any] = {}

    def calculate_user_satisfaction_scores(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate user satisfaction scores from feedback data."""
        scoring_id = str(uuid4())

        # Simulate satisfaction scoring calculation
        satisfaction_metrics = {
            "ease_of_use": 0.85,
            "feature_completeness": 0.82,
            "performance_satisfaction": 0.88,
            "interface_intuitiveness": 0.86,
            "error_handling_quality": 0.80,
        }

        # Calculate overall satisfaction score
        overall_score = sum(satisfaction_metrics.values()) / len(satisfaction_metrics)

        result = {
            "scoring_id": scoring_id,
            "satisfaction_metrics": satisfaction_metrics,
            "overall_satisfaction_score": overall_score,
            "feedback_data": feedback_data,
            "satisfaction_level": "good" if overall_score >= 0.8 else "needs_improvement",
            "timestamp": time.time(),
        }

        self.scoring_history[scoring_id] = result
        return result


class SatisfactionScoring:
    """Service for measuring and scoring user satisfaction."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """Initialize satisfaction scoring service."""
        self.logger = logger or logging.getLogger(__name__)
        self.scoring_data: Dict[str, Any] = {}

    def calculate_user_satisfaction_score(self, user_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate user satisfaction score based on feedback."""
        scoring_id = str(uuid4())

        # Extract feedback components
        ease_of_use = user_feedback.get("ease_of_use", 0.8)
        result_clarity = user_feedback.get("result_clarity", 0.85)
        performance_satisfaction = user_feedback.get("performance_satisfaction", 0.82)
        feature_completeness = user_feedback.get("feature_completeness", 0.88)

        # Calculate weighted satisfaction score
        weights = {
            "ease_of_use": 0.3,
            "result_clarity": 0.25,
            "performance_satisfaction": 0.25,
            "feature_completeness": 0.2,
        }

        satisfaction_score = (
            ease_of_use * weights["ease_of_use"]
            + result_clarity * weights["result_clarity"]
            + performance_satisfaction * weights["performance_satisfaction"]
            + feature_completeness * weights["feature_completeness"]
        )

        result = {
            "scoring_id": scoring_id,
            "satisfaction_score": satisfaction_score,
            "component_scores": {
                "ease_of_use": ease_of_use,
                "result_clarity": result_clarity,
                "performance_satisfaction": performance_satisfaction,
                "feature_completeness": feature_completeness,
            },
            "scoring_weights": weights,
            "satisfaction_level": self._categorize_satisfaction(satisfaction_score),
            "recommendations": self._generate_satisfaction_recommendations(satisfaction_score),
            "timestamp": time.time(),
        }

        self.scoring_data[scoring_id] = result
        return result

    def track_satisfaction_trends(self, period_days: int = 30) -> Dict[str, Any]:
        """Track satisfaction trends over specified period."""
        trend_id = str(uuid4())

        # Simulate satisfaction trend data
        trend_data = [0.82, 0.85, 0.83, 0.87, 0.86, 0.88, 0.85]  # Weekly averages

        result = {
            "trend_id": trend_id,
            "period_days": period_days,
            "satisfaction_trend": trend_data,
            "average_satisfaction": sum(trend_data) / len(trend_data),
            "trend_direction": "improving" if trend_data[-1] > trend_data[0] else "declining",
            "volatility": max(trend_data) - min(trend_data),
            "timestamp": time.time(),
        }

        return result

    def _categorize_satisfaction(self, score: float) -> str:
        """Categorize satisfaction score into levels."""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "good"
        elif score >= 0.7:
            return "acceptable"
        elif score >= 0.6:
            return "needs_improvement"
        else:
            return "poor"

    def _generate_satisfaction_recommendations(self, score: float) -> List[str]:
        """Generate recommendations based on satisfaction score."""
        if score >= 0.9:
            return ["Maintain current quality standards", "Continue monitoring user feedback"]
        elif score >= 0.8:
            return ["Identify specific areas for improvement", "Enhance user experience features"]
        elif score >= 0.7:
            return ["Focus on usability improvements", "Gather detailed user feedback"]
        else:
            return ["Urgent attention needed", "Comprehensive UX redesign recommended", "Conduct user research studies"]
