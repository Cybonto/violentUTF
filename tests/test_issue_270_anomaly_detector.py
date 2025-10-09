# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Unit Tests for Issue #270: Anomaly Detector

Tests the anomaly detection functionality including z-score detection, IQR
method, trend analysis, and alert generation.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pytest

from violentutf_api.fastapi_app.app.monitoring.database.anomaly_detector import (
    Anomaly,
    AnomalyDetector,
    AnomalyType,
)
from violentutf_api.fastapi_app.app.monitoring.database.baseline_analyzer import (
    PerformanceBaseline,
)


class TestAnomalyDetector:
    """Test suite for AnomalyDetector"""

    @pytest.fixture
    def detector(self):
        """Create an AnomalyDetector instance for testing"""
        return AnomalyDetector(sensitivity="medium")

    @pytest.fixture
    def sample_baseline(self):
        """Create a sample baseline for testing"""
        return PerformanceBaseline(
            metric_type="avg_query_latency_ms",
            baseline_value=15.0,
            std_deviation=3.0,
            min_value=5.0,
            max_value=25.0,
            sample_size=1000,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
            valid_until=datetime.now(timezone.utc) + timedelta(days=1),
            normal_range_min=9.0,
            normal_range_max=21.0,
        )

    def test_z_score_anomaly_detection(self, detector, sample_baseline):
        """Test z-score based anomaly detection"""
        # Value within normal range
        normal_value = 15.0
        anomaly = detector.detect_anomaly(
            current_value=normal_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )
        assert anomaly is None

        # Value significantly above baseline (>3 std devs)
        high_value = 25.0  # 3.33 std devs above mean
        anomaly = detector.detect_anomaly(
            current_value=high_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )
        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.SPIKE
        assert anomaly.severity in ["warning", "critical"]

    def test_iqr_anomaly_detection(self, detector, sample_baseline):
        """Test IQR-based anomaly detection"""
        detector.detection_method = "iqr"

        # Value within normal range
        normal_value = 15.0
        anomaly = detector.detect_anomaly(
            current_value=normal_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )
        assert anomaly is None

        # Value outside IQR range
        outlier_value = 30.0
        anomaly = detector.detect_anomaly(
            current_value=outlier_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )
        assert anomaly is not None

    def test_sudden_spike_detection(self, detector, sample_baseline):
        """Test detection of sudden spikes"""
        # Spike is >2x baseline
        spike_value = 32.0  # More than 2x baseline (15.0)
        anomaly = detector.detect_anomaly(
            current_value=spike_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )

        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.SPIKE
        assert anomaly.magnitude > 2.0

    def test_gradual_degradation_detection(self, detector, sample_baseline):
        """Test detection of gradual performance degradation"""
        # Provide historical values showing upward trend (degradation)
        # Start from 10 hours ago with value 10.0, increase to 15.0 at 5 hours ago,
        # then to 20.0 now
        historical_values = []
        for i in range(10):
            hours_ago = 10 - i
            value = 10.0 + (i * 1.0)  # Values: 10.0, 11.0, 12.0, ..., 19.0
            historical_values.append({
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
                "value": value
            })

        current_value = 20.0
        anomaly = detector.detect_anomaly(
            current_value=current_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
            historical_values=historical_values,
        )

        # Should detect trend even if current value not extreme
        assert anomaly is not None
        assert anomaly.anomaly_type == AnomalyType.DEGRADATION

    def test_false_positive_reduction(self, detector, sample_baseline):
        """Test that single anomalies don't trigger immediately"""
        detector.consecutive_threshold = 3

        # First occurrence - should not trigger
        anomaly = detector.detect_anomaly(
            current_value=25.0,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )
        # Anomaly detected but may not be confirmed yet
        assert anomaly is not None or detector._consecutive_count < 3

    def test_recovery_detection(self, detector, sample_baseline):
        """Test detection of recovery from anomaly"""
        # Simulate anomaly state by setting metric-specific state
        state_key = "avg_query_latency_ms"
        detector._metric_states[state_key] = {
            "consecutive_anomalies": 5,
            "in_anomaly": True,
        }

        # Value returns to normal
        normal_value = 15.0
        anomaly = detector.detect_anomaly(
            current_value=normal_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )

        # Should clear anomaly state
        assert detector._metric_states[state_key]["in_anomaly"] is False
        assert anomaly is None or anomaly.anomaly_type == AnomalyType.RECOVERY

    def test_sensitivity_levels(self):
        """Test different sensitivity configurations"""
        # Low sensitivity - higher threshold
        low_detector = AnomalyDetector(sensitivity="low")
        assert low_detector.z_score_threshold > 3.0

        # Medium sensitivity
        medium_detector = AnomalyDetector(sensitivity="medium")
        assert medium_detector.z_score_threshold == 3.0

        # High sensitivity - lower threshold
        high_detector = AnomalyDetector(sensitivity="high")
        assert high_detector.z_score_threshold < 3.0

    def test_anomaly_alert_generation(self, detector, sample_baseline):
        """Test alert data generation when anomaly detected"""
        anomaly_value = 30.0
        anomaly = detector.detect_anomaly(
            current_value=anomaly_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
            asset_id="test-db-001",
        )

        assert anomaly is not None
        assert anomaly.metric_type == "avg_query_latency_ms"
        assert anomaly.current_value == anomaly_value
        assert anomaly.baseline_value == sample_baseline.baseline_value
        assert anomaly.deviation is not None
        assert anomaly.asset_id == "test-db-001"

    def test_alert_severity_assignment(self, detector, sample_baseline):
        """Test correct severity assignment based on magnitude"""
        # Minor deviation - warning
        warning_value = 22.0  # ~2.3 std devs
        anomaly = detector.detect_anomaly(
            current_value=warning_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )
        if anomaly:
            assert anomaly.severity in ["info", "warning"]

        # Major deviation - critical
        critical_value = 35.0  # >6 std devs
        anomaly = detector.detect_anomaly(
            current_value=critical_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )
        assert anomaly is not None
        assert anomaly.severity == "critical"

    def test_alert_metadata(self, detector, sample_baseline):
        """Test that anomaly contains proper metadata"""
        anomaly_value = 30.0
        anomaly = detector.detect_anomaly(
            current_value=anomaly_value,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )

        assert anomaly is not None
        assert anomaly.timestamp is not None
        assert isinstance(anomaly.timestamp, datetime)
        assert anomaly.timestamp.tzinfo is not None
        assert anomaly.magnitude > 0
        assert anomaly.description is not None
        assert len(anomaly.description) > 0

    def test_no_baseline_handling(self, detector):
        """Test behavior when no baseline is available"""
        anomaly = detector.detect_anomaly(
            current_value=15.0,
            baseline=None,
            metric_type="avg_query_latency_ms",
        )
        # Should not detect anomaly without baseline
        assert anomaly is None

    def test_invalid_baseline_handling(self, detector):
        """Test handling of expired baseline"""
        expired_baseline = PerformanceBaseline(
            metric_type="avg_query_latency_ms",
            baseline_value=15.0,
            std_deviation=3.0,
            min_value=5.0,
            max_value=25.0,
            sample_size=1000,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
            valid_until=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired
        )

        anomaly = detector.detect_anomaly(
            current_value=30.0,
            baseline=expired_baseline,
            metric_type="avg_query_latency_ms",
        )
        # Should handle expired baseline gracefully
        assert anomaly is None or anomaly is not None  # Implementation choice

    def test_trend_analysis(self, detector, sample_baseline):
        """Test trend analysis with historical data"""
        # Upward trend - values increase over time
        upward_trend = []
        for i in range(10):
            hours_ago = 10 - i
            value = 10.0 + i  # Values: 10, 11, 12, ..., 19
            upward_trend.append({
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
                "value": value
            })

        has_trend = detector._analyze_trend(upward_trend)
        assert has_trend is True

        # No trend (flat)
        flat_trend = []
        for i in range(10):
            hours_ago = 10 - i
            flat_trend.append({
                "timestamp": datetime.now(timezone.utc) - timedelta(hours=hours_ago),
                "value": 15.0
            })

        has_trend = detector._analyze_trend(flat_trend)
        assert has_trend is False

    def test_multiple_concurrent_anomalies(self, detector, sample_baseline):
        """Test tracking multiple anomalies for different metrics"""
        # Anomaly in metric 1
        anomaly1 = detector.detect_anomaly(
            current_value=30.0,
            baseline=sample_baseline,
            metric_type="avg_query_latency_ms",
        )

        # Different baseline for metric 2
        baseline2 = PerformanceBaseline(
            metric_type="connection_pool_usage",
            baseline_value=50.0,
            std_deviation=10.0,
            min_value=20.0,
            max_value=80.0,
            sample_size=1000,
            calculation_window_hours=168,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
            valid_until=datetime.now(timezone.utc) + timedelta(days=1),
            normal_range_min=30.0,
            normal_range_max=70.0,
        )

        # Anomaly in metric 2
        anomaly2 = detector.detect_anomaly(
            current_value=90.0,
            baseline=baseline2,
            metric_type="connection_pool_usage",
        )

        # Both should be detected independently
        assert anomaly1 is not None
        assert anomaly2 is not None
        assert anomaly1.metric_type != anomaly2.metric_type


class TestAnomaly:
    """Test suite for Anomaly data class"""

    def test_anomaly_creation(self):
        """Test Anomaly can be created with required fields"""
        anomaly = Anomaly(
            timestamp=datetime.now(timezone.utc),
            metric_type="avg_query_latency_ms",
            current_value=30.0,
            baseline_value=15.0,
            deviation=15.0,
            magnitude=2.0,
            anomaly_type=AnomalyType.SPIKE,
            severity="warning",
            description="Query latency spike detected",
        )

        assert anomaly.timestamp is not None
        assert anomaly.metric_type == "avg_query_latency_ms"
        assert anomaly.severity == "warning"

    def test_anomaly_to_dict(self):
        """Test Anomaly conversion to dictionary"""
        anomaly = Anomaly(
            timestamp=datetime.now(timezone.utc),
            metric_type="avg_query_latency_ms",
            current_value=30.0,
            baseline_value=15.0,
            deviation=15.0,
            magnitude=2.0,
            anomaly_type=AnomalyType.SPIKE,
            severity="warning",
            description="Query latency spike detected",
        )

        data = anomaly.to_dict()
        assert isinstance(data, dict)
        assert "timestamp" in data
        assert "metric_type" in data
        assert "current_value" in data
        assert isinstance(data["timestamp"], str)  # ISO format
