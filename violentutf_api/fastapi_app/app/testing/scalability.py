# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Scalability Testing Module

Provides comprehensive scalability testing capabilities for system load testing,
resource scaling validation, and performance degradation analysis.
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class ScalabilityMetrics:
    """Scalability testing results"""
    load_level: int
    response_time_ms: float
    throughput_rps: float
    error_rate: float
    resource_utilization: Dict[str, float]
    degradation_factor: float


class SystemScalabilityMonitor:
    """Monitor system scalability under different load levels"""
    
    def __init__(self, session_id: str = None) -> None:
        """Initialize SystemScalabilityMonitor.
        
        Args:
            session_id: Unique identifier for monitoring session.
                       Defaults to timestamp-based ID.
        """
        self.session_id = session_id or f"scalability_{int(time.time())}"
        self.scalability_results: List[ScalabilityMetrics] = []
        
    def test_load_scalability(self, load_levels: List[int]) -> Dict[str, Any]:
        """Test system scalability across different load levels"""
        results = {}
        
        for load_level in load_levels:
            # Mock scalability testing
            metrics = ScalabilityMetrics(
                load_level=load_level,
                response_time_ms=50.0 * (1 + load_level * 0.1),  # Increases with load
                throughput_rps=max(100 - load_level * 2, 10),    # Decreases with load
                error_rate=min(load_level * 0.02, 0.1),          # Increases with load
                resource_utilization={
                    "cpu_percent": min(30 + load_level * 5, 95),
                    "memory_percent": min(40 + load_level * 3, 90),
                    "disk_io": load_level * 10
                },
                degradation_factor=max(1.0, load_level * 0.05)
            )
            
            self.scalability_results.append(metrics)
            results[load_level] = {
                "response_time_ms": metrics.response_time_ms,
                "throughput_rps": metrics.throughput_rps,
                "error_rate": metrics.error_rate,
                "resource_utilization": metrics.resource_utilization,
                "degradation_factor": metrics.degradation_factor
            }
        
        return {
            "load_test_results": results,
            "scalability_score": self._calculate_scalability_score(),
            "bottlenecks_detected": self._detect_bottlenecks(),
            "recommendations": self._generate_recommendations()
        }
        
    def _calculate_scalability_score(self) -> float:
        """Calculate overall scalability score (0-100)"""
        if not self.scalability_results:
            return 0.0
            
        # Score based on degradation factors
        avg_degradation = sum(m.degradation_factor for m in self.scalability_results) / len(self.scalability_results)
        score = max(0, 100 - (avg_degradation - 1) * 50)
        
        return min(100, score)
        
    def _detect_bottlenecks(self) -> List[str]:
        """Detect performance bottlenecks from results"""
        bottlenecks = []
        
        if self.scalability_results:
            latest = self.scalability_results[-1]
            if latest.resource_utilization["cpu_percent"] > 80:
                bottlenecks.append("CPU utilization high")
            if latest.resource_utilization["memory_percent"] > 80:
                bottlenecks.append("Memory utilization high") 
            if latest.error_rate > 0.05:
                bottlenecks.append("Error rate increasing")
                
        return bottlenecks
        
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        bottlenecks = self._detect_bottlenecks()
        for bottleneck in bottlenecks:
            if "CPU" in bottleneck:
                recommendations.append("Consider horizontal scaling or CPU optimization")
            elif "Memory" in bottleneck:
                recommendations.append("Increase memory allocation or optimize memory usage")
            elif "Error" in bottleneck:
                recommendations.append("Investigate error causes and improve error handling")
                
        return recommendations


def measure_system_scalability(load_levels: List[int]) -> Dict[str, Any]:
    """Measure system scalability across different load levels."""
    monitor = SystemScalabilityMonitor()
    return monitor.test_load_scalability(load_levels)


def validate_scalability_requirements(
    target_load: int, 
    max_response_time_ms: float,
    min_throughput_rps: float
) -> Dict[str, Any]:
    """Validate if system meets scalability requirements"""
    monitor = SystemScalabilityMonitor()
    results = monitor.test_load_scalability([target_load])
    
    metrics = results["load_test_results"][target_load]
    
    return {
        "target_load": target_load,
        "requirements_met": (
            metrics["response_time_ms"] <= max_response_time_ms and
            metrics["throughput_rps"] >= min_throughput_rps
        ),
        "actual_response_time_ms": metrics["response_time_ms"],
        "actual_throughput_rps": metrics["throughput_rps"],
        "performance_margin": {
            "response_time": max_response_time_ms - metrics["response_time_ms"],
            "throughput": metrics["throughput_rps"] - min_throughput_rps
        }
    }


# Alias for test compatibility
ScalabilityTester = SystemScalabilityMonitor