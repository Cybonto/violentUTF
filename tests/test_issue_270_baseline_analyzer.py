# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Unit Tests for Issue #270: Baseline Analyzer

Tests the baseline analyzer functionality including statistical baseline
calculation, rolling window analysis, and normal range determination.
"""

import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from violentutf_api.fastapi_app.app.monitoring.database.baseline_analyzer import (
    BaselineAnalyzer,
    PerformanceBaseline,
)


class TestBaselineAnalyzer:
    """Test suite for BaselineAnalyzer"""

    @pytest.fixture
    def analyzer(self):
        """Create a BaselineAnalyzer instance for testing"""
        return BaselineAnalyzer()

    @pytest.fixture
    def sample_metrics(self) -> List[Dict[str, Any]]:
        """Generate sample metrics for testing"""
        base_time = datetime.now(timezone.utc) - timedelta(days=7)
        metrics = []

        for i in range(1000):
            timestamp = base_time + timedelta(minutes=i * 10)
            metrics.append(
                {
                    "metric_type": "avg_query_time_ms",
                    "value": 15.0 + (i % 10) * 0.5,  # Values between 15.0 and 19.5
                    "timestamp": timestamp,
                }
            )

        return metrics

    @pytest.fixture
    def normal_distribution_metrics(self) -> List[Dict[str, Any]]:
        """Generate normally distributed metrics"""
        import random

        base_time = datetime.now(timezone.utc) - timedelta(days=7)
        metrics = []

        random.seed(42)  # For reproducibility
        for i in range(1000):
            timestamp = base_time + timedelta(minutes=i * 10)
            value = random.gauss(15.0, 3.0)  # Mean=15, StdDev=3
            metrics.append(
                {
                    "metric_type": "avg_query_time_ms",
                    "value": value,
                    "timestamp": timestamp,
                }
            )

        return metrics

    def test_calculate_statistical_baseline(self, analyzer, sample_metrics):
        """Test statistical baseline calculation with mean, std dev, min, max"""
        baseline = analyzer.calculate_baseline(sample_metrics, "avg_query_time_ms")

        assert isinstance(baseline, PerformanceBaseline)
        assert baseline.metric_type == "avg_query_time_ms"
        assert baseline.baseline_value > 0
        assert baseline.std_deviation >= 0
        assert baseline.min_value <= baseline.baseline_value <= baseline.max_value
        assert baseline.sample_size >= 900  # Allow for time window filtering

    def test_rolling_window_baseline(self, analyzer, sample_metrics):
        """Test 7-day rolling average baseline calculation"""
        baseline = analyzer.calculate_baseline(
            sample_metrics, "avg_query_time_ms", window_hours=168  # 7 days
        )

        assert baseline.calculation_window_hours == 168
        assert baseline.sample_size > 0

    def test_baseline_with_insufficient_data(self, analyzer):
        """Test handling of cases with < 100 samples"""
        # Create metrics with only 50 samples
        base_time = datetime.now(timezone.utc)
        metrics = [
            {
                "metric_type": "test_metric",
                "value": float(i),
                "timestamp": base_time + timedelta(minutes=i),
            }
            for i in range(50)
        ]

        with pytest.raises(ValueError, match="Insufficient data"):
            analyzer.calculate_baseline(metrics, "test_metric", min_samples=100)

    def test_outlier_filtering(self, analyzer):
        """Test outlier removal before baseline calculation"""
        # Create metrics with outliers
        base_time = datetime.now(timezone.utc)
        metrics = []

        # Add normal values
        for i in range(100):
            metrics.append(
                {
                    "metric_type": "test_metric",
                    "value": 15.0 + (i % 5),  # Values 15-19
                    "timestamp": base_time + timedelta(minutes=i),
                }
            )

        # Add outliers
        metrics.extend(
            [
                {
                    "metric_type": "test_metric",
                    "value": 1000.0,  # Extreme outlier
                    "timestamp": base_time + timedelta(minutes=100),
                },
                {
                    "metric_type": "test_metric",
                    "value": 0.01,  # Extreme outlier
                    "timestamp": base_time + timedelta(minutes=101),
                },
            ]
        )

        baseline = analyzer.calculate_baseline(
            metrics, "test_metric", remove_outliers=True
        )

        # Baseline should not be significantly affected by outliers
        assert 14.0 <= baseline.baseline_value <= 20.0
        assert baseline.std_deviation < 10.0

    def test_baseline_update_logic(self, analyzer, sample_metrics):
        """Test baseline recalculation triggers"""
        # Calculate initial baseline
        baseline1 = analyzer.calculate_baseline(sample_metrics, "avg_query_time_ms")

        # Check if update is needed (should be False for recent baseline)
        assert not analyzer.should_update_baseline(baseline1)

        # Create old baseline (more than 24 hours old)
        old_baseline = PerformanceBaseline(
            metric_type="avg_query_time_ms",
            baseline_value=15.0,
            std_deviation=2.0,
            min_value=10.0,
            max_value=20.0,
            sample_size=1000,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc) - timedelta(hours=25),
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        # Should need update
        assert analyzer.should_update_baseline(old_baseline)

    def test_multi_metric_baseline(self, analyzer):
        """Test baseline calculation for multiple metric types"""
        base_time = datetime.now(timezone.utc)
        metrics = []

        # Add different metric types
        for i in range(100):
            timestamp = base_time + timedelta(minutes=i)
            metrics.extend(
                [
                    {
                        "metric_type": "query_time",
                        "value": 15.0 + i % 5,
                        "timestamp": timestamp,
                    },
                    {
                        "metric_type": "connection_count",
                        "value": 50.0 + i % 10,
                        "timestamp": timestamp,
                    },
                ]
            )

        query_baseline = analyzer.calculate_baseline(metrics, "query_time")
        conn_baseline = analyzer.calculate_baseline(metrics, "connection_count")

        assert query_baseline.metric_type == "query_time"
        assert conn_baseline.metric_type == "connection_count"
        assert query_baseline.baseline_value != conn_baseline.baseline_value

    def test_database_specific_baselines(self, analyzer, sample_metrics):
        """Test separate baselines per database"""
        # Add database identifier to metrics
        for metric in sample_metrics:
            metric["asset_id"] = "postgres-keycloak"

        baseline = analyzer.calculate_baseline(
            sample_metrics, "avg_query_time_ms", asset_id="postgres-keycloak"
        )

        assert baseline.asset_id == "postgres-keycloak"

    def test_normal_range_calculation_2sigma(self, analyzer, normal_distribution_metrics):
        """Test normal range determination using ±2σ"""
        baseline = analyzer.calculate_baseline(
            normal_distribution_metrics, "avg_query_time_ms"
        )

        # Calculate expected range (mean ± 2*std_dev)
        expected_min = baseline.baseline_value - (2 * baseline.std_deviation)
        expected_max = baseline.baseline_value + (2 * baseline.std_deviation)

        assert baseline.normal_range_min == pytest.approx(expected_min, rel=0.1)
        assert baseline.normal_range_max == pytest.approx(expected_max, rel=0.1)

    def test_percentile_based_range(self, analyzer, sample_metrics):
        """Test P5-P95 range calculation"""
        baseline = analyzer.calculate_baseline(
            sample_metrics, "avg_query_time_ms", range_method="percentile"
        )

        # Check that percentile range is calculated
        assert hasattr(baseline, "percentile_5")
        assert hasattr(baseline, "percentile_95")
        assert baseline.percentile_5 < baseline.baseline_value < baseline.percentile_95

    def test_skewed_distribution_handling(self, analyzer):
        """Test handling of non-normal (skewed) distributions"""
        # Create right-skewed distribution
        base_time = datetime.now(timezone.utc)
        metrics = []

        # Most values low, few values very high
        for i in range(100):
            value = 10.0 if i < 90 else 100.0
            metrics.append(
                {
                    "metric_type": "skewed_metric",
                    "value": value,
                    "timestamp": base_time + timedelta(minutes=i),
                }
            )

        baseline = analyzer.calculate_baseline(
            metrics, "skewed_metric", range_method="percentile"
        )

        # Percentile method should handle skewness better
        assert baseline.percentile_5 < baseline.percentile_95
        assert baseline.baseline_value > 0

    def test_range_validation(self, analyzer, sample_metrics):
        """Test that calculated ranges are logical (min < max)"""
        baseline = analyzer.calculate_baseline(sample_metrics, "avg_query_time_ms")

        assert baseline.min_value < baseline.max_value
        assert baseline.normal_range_min < baseline.normal_range_max
        # Note: normal_range can extend beyond min/max for 2-sigma calculation
        # This is correct statistical behavior

    def test_edge_case_no_data(self, analyzer):
        """Test handling of empty metrics list"""
        with pytest.raises(ValueError, match="No metrics provided"):
            analyzer.calculate_baseline([], "test_metric")

    def test_edge_case_single_data_point(self, analyzer):
        """Test handling of single data point"""
        metrics = [
            {
                "metric_type": "test_metric",
                "value": 15.0,
                "timestamp": datetime.now(timezone.utc),
            }
        ]

        with pytest.raises(ValueError, match="Insufficient data"):
            analyzer.calculate_baseline(metrics, "test_metric", min_samples=2)

    def test_edge_case_all_identical_values(self, analyzer):
        """Test handling of all identical metric values"""
        base_time = datetime.now(timezone.utc)
        metrics = [
            {
                "metric_type": "constant_metric",
                "value": 15.0,
                "timestamp": base_time + timedelta(minutes=i),
            }
            for i in range(100)
        ]

        baseline = analyzer.calculate_baseline(metrics, "constant_metric")

        assert baseline.baseline_value == 15.0
        assert baseline.std_deviation == 0.0
        assert baseline.min_value == 15.0
        assert baseline.max_value == 15.0

    def test_baseline_calculation_performance(self, analyzer):
        """Test that baseline calculation completes in < 5 seconds for 10,000 samples"""
        import time

        # Generate large dataset
        base_time = datetime.now(timezone.utc)
        metrics = [
            {
                "metric_type": "perf_test",
                "value": 15.0 + (i % 100) * 0.1,
                "timestamp": base_time + timedelta(seconds=i),
            }
            for i in range(10000)
        ]

        start = time.time()
        baseline = analyzer.calculate_baseline(metrics, "perf_test")
        duration = time.time() - start

        assert duration < 5.0, f"Calculation took {duration:.2f}s, expected < 5s"
        assert baseline.sample_size == 10000

    def test_baseline_persistence(self, analyzer, sample_metrics):
        """Test baseline can be serialized and deserialized"""
        baseline = analyzer.calculate_baseline(sample_metrics, "avg_query_time_ms")

        # Convert to dict
        baseline_dict = baseline.to_dict()
        assert isinstance(baseline_dict, dict)
        assert "metric_type" in baseline_dict
        assert "baseline_value" in baseline_dict

        # Recreate from dict
        restored_baseline = PerformanceBaseline.from_dict(baseline_dict)
        assert restored_baseline.metric_type == baseline.metric_type
        assert restored_baseline.baseline_value == baseline.baseline_value

    def test_confidence_interval_calculation(self, analyzer, normal_distribution_metrics):
        """Test confidence interval calculation for baseline"""
        baseline = analyzer.calculate_baseline(
            normal_distribution_metrics, "avg_query_time_ms", confidence_level=0.95
        )

        # Check confidence interval is calculated
        assert hasattr(baseline, "confidence_interval_lower")
        assert hasattr(baseline, "confidence_interval_upper")
        assert (
            baseline.confidence_interval_lower
            < baseline.baseline_value
            < baseline.confidence_interval_upper
        )

    def test_baseline_metadata(self, analyzer, sample_metrics):
        """Test baseline includes proper metadata"""
        baseline = analyzer.calculate_baseline(sample_metrics, "avg_query_time_ms")

        assert baseline.created_at is not None
        assert baseline.valid_until is not None
        assert baseline.created_at < baseline.valid_until
        assert baseline.calculation_window_hours > 0

    def test_filter_by_time_window(self, analyzer):
        """Test filtering metrics by time window"""
        now = datetime.now(timezone.utc)
        metrics = []

        # Add metrics spanning 14 days (every hour = 336 metrics)
        for i in range(336):
            timestamp = now - timedelta(days=14) + timedelta(hours=i)
            metrics.append(
                {
                    "metric_type": "test_metric",
                    "value": float(i),
                    "timestamp": timestamp,
                }
            )

        # Calculate baseline for last 7 days (168 hours)
        baseline = analyzer.calculate_baseline(
            metrics, "test_metric", window_hours=168, current_time=now, min_samples=100
        )

        # Should only use metrics from last 7 days (roughly half)
        assert baseline.sample_size < 200
        assert baseline.sample_size >= 100


class TestPerformanceBaseline:
    """Test suite for PerformanceBaseline data class"""

    def test_baseline_creation(self):
        """Test PerformanceBaseline can be created with required fields"""
        baseline = PerformanceBaseline(
            metric_type="avg_query_time_ms",
            baseline_value=15.5,
            std_deviation=2.3,
            min_value=10.0,
            max_value=25.0,
            sample_size=1000,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=1),
        )

        assert baseline.metric_type == "avg_query_time_ms"
        assert baseline.baseline_value == 15.5
        assert baseline.sample_size == 1000

    def test_baseline_to_dict(self):
        """Test PerformanceBaseline can be serialized to dict"""
        baseline = PerformanceBaseline(
            metric_type="avg_query_time_ms",
            baseline_value=15.5,
            std_deviation=2.3,
            min_value=10.0,
            max_value=25.0,
            sample_size=1000,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(days=1),
        )

        data = baseline.to_dict()
        assert isinstance(data, dict)
        assert data["metric_type"] == "avg_query_time_ms"
        assert data["baseline_value"] == 15.5

    def test_baseline_from_dict(self):
        """Test PerformanceBaseline can be created from dict"""
        data = {
            "metric_type": "avg_query_time_ms",
            "baseline_value": 15.5,
            "std_deviation": 2.3,
            "min_value": 10.0,
            "max_value": 25.0,
            "sample_size": 1000,
            "calculation_window_hours": 168,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }

        baseline = PerformanceBaseline.from_dict(data)
        assert baseline.metric_type == "avg_query_time_ms"
        assert baseline.baseline_value == 15.5

    def test_baseline_is_valid(self):
        """Test baseline validity checking"""
        # Valid baseline
        valid_baseline = PerformanceBaseline(
            metric_type="test",
            baseline_value=15.0,
            std_deviation=2.0,
            min_value=10.0,
            max_value=20.0,
            sample_size=100,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc),
            valid_until=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert valid_baseline.is_valid()

        # Expired baseline
        expired_baseline = PerformanceBaseline(
            metric_type="test",
            baseline_value=15.0,
            std_deviation=2.0,
            min_value=10.0,
            max_value=20.0,
            sample_size=100,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert not expired_baseline.is_valid()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
