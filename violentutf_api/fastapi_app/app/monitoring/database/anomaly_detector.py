# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Anomaly Detector for Issue #270

Detects performance anomalies using statistical methods including z-score
analysis, IQR detection, and trend analysis.
"""

import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from violentutf_api.fastapi_app.app.monitoring.database.baseline_analyzer import (
    PerformanceBaseline,
)


class AnomalyType(str, Enum):
    """Types of performance anomalies"""

    SPIKE = "spike"  # Sudden increase
    DROP = "drop"  # Sudden decrease
    DEGRADATION = "degradation"  # Gradual performance degradation
    RECOVERY = "recovery"  # Recovery from anomaly


@dataclass
class Anomaly:
    """Container for detected anomaly data"""

    timestamp: datetime
    metric_type: str
    current_value: float
    baseline_value: float
    deviation: float
    magnitude: float  # How many std devs or x times baseline
    anomaly_type: AnomalyType
    severity: str  # info, warning, critical
    description: str
    asset_id: Optional[str] = None
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert anomaly to dictionary format"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["anomaly_type"] = self.anomaly_type.value
        return data


class AnomalyDetector:
    """
    Detects performance anomalies using statistical methods.

    Supports multiple detection methods:
    - Z-score: Statistical deviation from mean
    - IQR: Interquartile range outlier detection
    - Trend analysis: Gradual degradation detection
    """

    def __init__(
        self,
        sensitivity: str = "medium",
        detection_method: str = "zscore",
        consecutive_threshold: int = 1,
    ) -> None:
        """
        Initialize anomaly detector.

        Args:
            sensitivity: Detection sensitivity (low, medium, high)
            detection_method: Method to use (zscore, iqr)
            consecutive_threshold: Number of consecutive anomalies required
        """
        self.detection_method = detection_method
        self.consecutive_threshold = consecutive_threshold

        # Set z-score threshold based on sensitivity
        sensitivity_map = {
            "low": 3.5,  # More tolerant
            "medium": 3.0,  # Standard
            "high": 2.5,  # More sensitive
        }
        self.z_score_threshold = sensitivity_map.get(sensitivity, 3.0)

        # IQR multiplier for outlier detection
        self.iqr_multiplier = 1.5

        # State tracking
        self._in_anomaly_state = False
        self._consecutive_count = 0
        self._metric_states: Dict[str, Dict[str, Any]] = {}

    def detect_anomaly(
        self,
        current_value: float,
        baseline: Optional[PerformanceBaseline],
        metric_type: str,
        asset_id: Optional[str] = None,
        historical_values: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Anomaly]:
        """
        Detect anomaly in current metric value.

        Args:
            current_value: Current metric value
            baseline: Performance baseline for comparison
            metric_type: Type of metric being evaluated
            asset_id: Database/asset identifier
            historical_values: Recent historical values for trend analysis

        Returns:
            Anomaly: Detected anomaly or None if normal
        """
        # Cannot detect without baseline
        if baseline is None:
            return None

        # Check if baseline is still valid
        if not baseline.is_valid():
            return None

        # Get or initialize state for this metric
        state_key = f"{asset_id}:{metric_type}" if asset_id else metric_type
        if state_key not in self._metric_states:
            self._metric_states[state_key] = {
                "consecutive_anomalies": 0,
                "in_anomaly": False,
            }

        state = self._metric_states[state_key]

        # Detect anomaly using configured method
        if self.detection_method == "zscore":
            is_anomaly, deviation, magnitude = self._detect_zscore(current_value, baseline)
        elif self.detection_method == "iqr":
            is_anomaly, deviation, magnitude = self._detect_iqr(current_value, baseline)
        else:
            is_anomaly, deviation, magnitude = self._detect_zscore(current_value, baseline)

        # Check for trends if historical values provided
        has_degradation_trend = False
        if historical_values and len(historical_values) > 5:
            has_degradation_trend = self._analyze_trend(historical_values)

        # Update consecutive count
        if is_anomaly or has_degradation_trend:
            state["consecutive_anomalies"] += 1
        else:
            # Check for recovery
            if state["in_anomaly"]:
                state["in_anomaly"] = False
                state["consecutive_anomalies"] = 0
                self._in_anomaly_state = False
                return self._create_recovery_anomaly(current_value, baseline, metric_type, asset_id)
            state["consecutive_anomalies"] = 0
            return None

        # Check if we have enough consecutive anomalies
        if state["consecutive_anomalies"] < self.consecutive_threshold:
            return None

        # Mark as in anomaly state
        state["in_anomaly"] = True
        self._in_anomaly_state = True

        # Determine anomaly type
        if has_degradation_trend:
            anomaly_type = AnomalyType.DEGRADATION
        elif current_value > baseline.baseline_value:
            anomaly_type = AnomalyType.SPIKE
        else:
            anomaly_type = AnomalyType.DROP

        # Determine severity based on magnitude
        if magnitude > 5.0 or abs(deviation) > 5 * baseline.std_deviation:
            severity = "critical"
        elif magnitude > 3.0 or abs(deviation) > 3 * baseline.std_deviation:
            severity = "warning"
        else:
            severity = "info"

        # Create description
        description = self._create_description(anomaly_type, metric_type, current_value, baseline, magnitude)

        return Anomaly(
            timestamp=datetime.now(timezone.utc),
            metric_type=metric_type,
            current_value=round(current_value, 4),
            baseline_value=round(baseline.baseline_value, 4),
            deviation=round(deviation, 4),
            magnitude=round(magnitude, 4),
            anomaly_type=anomaly_type,
            severity=severity,
            description=description,
            asset_id=asset_id,
        )

    def _detect_zscore(self, current_value: float, baseline: PerformanceBaseline) -> tuple:
        """
        Detect anomaly using z-score method.

        Returns:
            tuple: (is_anomaly, deviation, magnitude)
        """
        deviation = current_value - baseline.baseline_value

        if baseline.std_deviation == 0:
            # Handle zero std deviation
            is_anomaly = abs(deviation) > 0
            magnitude = abs(deviation) / baseline.baseline_value if baseline.baseline_value > 0 else 0
        else:
            z_score = abs(deviation) / baseline.std_deviation
            is_anomaly = z_score > self.z_score_threshold
            magnitude = z_score

        return is_anomaly, deviation, magnitude

    def _detect_iqr(self, current_value: float, baseline: PerformanceBaseline) -> tuple:
        """
        Detect anomaly using IQR method.

        Returns:
            tuple: (is_anomaly, deviation, magnitude)
        """
        # Use percentiles from baseline if available
        if baseline.percentile_5 is not None and baseline.percentile_95 is not None:
            iqr = baseline.percentile_95 - baseline.percentile_5
            lower_bound = baseline.percentile_5 - (self.iqr_multiplier * iqr)
            upper_bound = baseline.percentile_95 + (self.iqr_multiplier * iqr)
        else:
            # Fall back to normal range
            lower_bound = baseline.normal_range_min or baseline.min_value
            upper_bound = baseline.normal_range_max or baseline.max_value

        is_anomaly = current_value < lower_bound or current_value > upper_bound
        deviation = current_value - baseline.baseline_value
        magnitude = abs(deviation) / baseline.std_deviation if baseline.std_deviation > 0 else 0

        return is_anomaly, deviation, magnitude

    def _analyze_trend(self, historical_values: List[Dict[str, Any]]) -> bool:
        """
        Analyze trend in historical values.

        Args:
            historical_values: List of dicts with 'timestamp' and 'value'

        Returns:
            bool: True if degrading trend detected
        """
        if len(historical_values) < 6:
            return False

        # Sort by timestamp (oldest first)
        sorted_values = sorted(historical_values, key=lambda x: x["timestamp"])

        # Extract values
        values = [v["value"] for v in sorted_values]

        # Simple linear trend detection
        # Check if values are generally increasing
        n = len(values)
        increases = sum(1 for i in range(n - 1) if values[i + 1] > values[i])

        # If more than 60% of intervals show increase, it's a trend
        trend_threshold = 0.6
        has_trend = (increases / (n - 1)) > trend_threshold

        # Additional check: significant overall increase
        if has_trend:
            first_half_avg = statistics.mean(values[: n // 2])
            second_half_avg = statistics.mean(values[n // 2 :])
            # At least 5% increase (more sensitive)
            significant_increase = second_half_avg > first_half_avg * 1.05
            return significant_increase

        return False

    def _create_recovery_anomaly(
        self,
        current_value: float,
        baseline: PerformanceBaseline,
        metric_type: str,
        asset_id: Optional[str],
    ) -> Optional[Anomaly]:
        """Create recovery anomaly notification"""
        return Anomaly(
            timestamp=datetime.now(timezone.utc),
            metric_type=metric_type,
            current_value=round(current_value, 4),
            baseline_value=round(baseline.baseline_value, 4),
            deviation=round(current_value - baseline.baseline_value, 4),
            magnitude=0.0,
            anomaly_type=AnomalyType.RECOVERY,
            severity="info",
            description=f"{metric_type} has returned to normal levels",
            asset_id=asset_id,
        )

    def _create_description(
        self,
        anomaly_type: AnomalyType,
        metric_type: str,
        current_value: float,
        baseline: PerformanceBaseline,
        magnitude: float,
    ) -> str:
        """Create human-readable description of anomaly"""
        if anomaly_type == AnomalyType.SPIKE:
            return (
                f"{metric_type} spike detected: {current_value:.2f} "
                f"(baseline: {baseline.baseline_value:.2f}, "
                f"{magnitude:.1f}x deviation)"
            )
        elif anomaly_type == AnomalyType.DROP:
            return (
                f"{metric_type} drop detected: {current_value:.2f} "
                f"(baseline: {baseline.baseline_value:.2f}, "
                f"{magnitude:.1f}x deviation)"
            )
        elif anomaly_type == AnomalyType.DEGRADATION:
            return (
                f"{metric_type} gradual degradation detected: "
                f"trending upward from baseline {baseline.baseline_value:.2f}"
            )
        else:
            return f"{metric_type} anomaly detected"
