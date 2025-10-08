# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Baseline Analyzer for Issue #270

Calculates performance baselines and normal operating ranges for database
metrics using statistical methods.
"""

import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


@dataclass
class PerformanceBaseline:
    """Container for performance baseline data"""

    metric_type: str
    baseline_value: float
    std_deviation: float
    min_value: float
    max_value: float
    sample_size: int
    calculation_window_hours: int
    created_at: datetime
    valid_until: datetime
    asset_id: Optional[str] = None
    normal_range_min: Optional[float] = None
    normal_range_max: Optional[float] = None
    percentile_5: Optional[float] = None
    percentile_95: Optional[float] = None
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert baseline to dictionary format"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["valid_until"] = self.valid_until.isoformat()
        return data

    @classmethod
    def from_dict(cls: type["PerformanceBaseline"], data: Dict[str, Any]) -> "PerformanceBaseline":
        """Create baseline from dictionary"""
        # Parse datetime strings
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data["valid_until"], str):
            data["valid_until"] = datetime.fromisoformat(data["valid_until"])

        return cls(**data)

    def is_valid(self, current_time: Optional[datetime] = None) -> bool:
        """Check if baseline is still valid"""
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        return current_time < self.valid_until


class BaselineAnalyzer:
    """
    Analyzer for calculating performance baselines from historical metrics.

    Uses statistical methods to establish normal operating ranges and
    detect performance anomalies.
    """

    def __init__(self) -> None:
        """Initialize baseline analyzer"""
        self.default_window_hours = 168  # 7 days
        self.default_validity_hours = 24  # Baseline valid for 24 hours

    def calculate_baseline(
        self,
        metrics: List[Dict[str, Any]],
        metric_type: str,
        window_hours: Optional[int] = None,
        min_samples: int = 100,
        remove_outliers: bool = False,
        range_method: str = "sigma",  # "sigma" or "percentile"
        asset_id: Optional[str] = None,
        confidence_level: float = 0.95,
        current_time: Optional[datetime] = None,
    ) -> PerformanceBaseline:
        """
        Calculate performance baseline from historical metrics.

        Args:
            metrics: List of metric dicts with 'value', 'timestamp',
                'metric_type'
            metric_type: Type of metric to calculate baseline for
            window_hours: Time window in hours (default: 168 = 7 days)
            min_samples: Minimum number of samples required
            remove_outliers: Whether to remove outliers before calculation
            range_method: Method for calculating normal range
                ("sigma" or "percentile")
            asset_id: Database/asset identifier for this baseline
            confidence_level: Confidence level for confidence interval (0-1)
            current_time: Current time for filtering (default: now)

        Returns:
            PerformanceBaseline: Calculated baseline with statistics

        Raises:
            ValueError: If insufficient data or invalid parameters
        """
        if not metrics:
            raise ValueError("No metrics provided for baseline calculation")

        if current_time is None:
            current_time = datetime.now(timezone.utc)

        if window_hours is None:
            window_hours = self.default_window_hours

        # Filter metrics by type and time window
        filtered_metrics = self._filter_metrics(metrics, metric_type, window_hours, current_time)

        if len(filtered_metrics) < min_samples:
            raise ValueError(
                f"Insufficient data for baseline calculation: "
                f"{len(filtered_metrics)} samples (minimum: {min_samples})"
            )

        # Extract values
        values = [m["value"] for m in filtered_metrics]

        # Remove outliers if requested
        if remove_outliers:
            values = self._remove_outliers(values)

            if len(values) < min_samples:
                raise ValueError(
                    f"Insufficient data after outlier removal: " f"{len(values)} samples (minimum: {min_samples})"
                )

        # Calculate statistics
        baseline_value = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        min_val = min(values)
        max_val = max(values)

        # Calculate normal range
        if range_method == "sigma":
            normal_min = baseline_value - (2 * std_dev)
            normal_max = baseline_value + (2 * std_dev)
        elif range_method == "percentile":
            normal_min = self._percentile(values, 5)
            normal_max = self._percentile(values, 95)
        else:
            raise ValueError(f"Invalid range_method: {range_method}")

        # Calculate percentiles
        p5 = self._percentile(values, 5)
        p95 = self._percentile(values, 95)

        # Calculate confidence interval
        ci_lower, ci_upper = self._confidence_interval(values, baseline_value, std_dev, confidence_level)

        # Set validity period
        created_at = current_time
        valid_until = created_at + timedelta(hours=self.default_validity_hours)

        return PerformanceBaseline(
            metric_type=metric_type,
            baseline_value=round(baseline_value, 4),
            std_deviation=round(std_dev, 4),
            min_value=round(min_val, 4),
            max_value=round(max_val, 4),
            sample_size=len(values),
            calculation_window_hours=window_hours,
            created_at=created_at,
            valid_until=valid_until,
            asset_id=asset_id,
            normal_range_min=round(normal_min, 4),
            normal_range_max=round(normal_max, 4),
            percentile_5=round(p5, 4),
            percentile_95=round(p95, 4),
            confidence_interval_lower=round(ci_lower, 4),
            confidence_interval_upper=round(ci_upper, 4),
        )

    def should_update_baseline(self, baseline: PerformanceBaseline, current_time: Optional[datetime] = None) -> bool:
        """
        Check if baseline should be updated.

        Args:
            baseline: Existing baseline
            current_time: Current time for comparison

        Returns:
            bool: True if baseline should be recalculated
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        return not baseline.is_valid(current_time)

    def _filter_metrics(
        self,
        metrics: List[Dict[str, Any]],
        metric_type: str,
        window_hours: int,
        current_time: datetime,
    ) -> List[Dict[str, Any]]:
        """Filter metrics by type and time window"""
        cutoff_time = current_time - timedelta(hours=window_hours)

        filtered = []
        for metric in metrics:
            if metric.get("metric_type") != metric_type:
                continue

            timestamp = metric.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            if timestamp >= cutoff_time:
                filtered.append(metric)

        return filtered

    def _remove_outliers(self, values: List[float], iqr_multiplier: float = 1.5) -> List[float]:
        """
        Remove outliers using IQR method.

        Args:
            values: List of values
            iqr_multiplier: Multiplier for IQR range (default: 1.5)

        Returns:
            List[float]: Values with outliers removed
        """
        if len(values) < 4:
            return values

        # Calculate quartiles
        sorted_values = sorted(values)
        q1 = self._percentile(sorted_values, 25)
        q3 = self._percentile(sorted_values, 75)

        iqr = q3 - q1
        lower_bound = q1 - (iqr_multiplier * iqr)
        upper_bound = q3 + (iqr_multiplier * iqr)

        # Filter outliers
        return [v for v in values if lower_bound <= v <= upper_bound]

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        k = (len(sorted_values) - 1) * (percentile / 100)
        f = int(k)
        c = k - f

        if f + 1 < len(sorted_values):
            return sorted_values[f] + c * (sorted_values[f + 1] - sorted_values[f])
        else:
            return sorted_values[f]

    def _confidence_interval(
        self,
        values: List[float],
        mean: float,
        std_dev: float,
        confidence_level: float,
    ) -> tuple:
        """
        Calculate confidence interval for the mean.

        Args:
            values: List of values
            mean: Mean value
            std_dev: Standard deviation
            confidence_level: Confidence level (0-1)

        Returns:
            tuple: (lower_bound, upper_bound)
        """
        if len(values) < 2:
            return (mean, mean)

        # Use t-distribution for small samples, normal for large
        import math

        n = len(values)

        if n < 30:
            # For small samples, use simplified t-value approximation
            # For 95% confidence, t ≈ 2.0 (conservative)
            t_value = 2.0
        else:
            # For large samples, use z-score
            # For 95% confidence, z ≈ 1.96
            z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
            t_value = z_scores.get(confidence_level, 1.96)

        margin_of_error = t_value * (std_dev / math.sqrt(n))

        return (mean - margin_of_error, mean + margin_of_error)
