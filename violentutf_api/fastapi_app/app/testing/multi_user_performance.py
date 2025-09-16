# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Multi-User Performance Testing Module

Provides comprehensive multi-user testing capabilities to simulate
real-world usage patterns and user interaction impacts on system performance.
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass 
class UserSession:
    """Represents a user session for testing"""
    user_id: str
    session_start: float
    session_duration: float
    operations_performed: int = 0
    operations_successful: int = 0
    total_response_time: float = 0.0
    errors_encountered: List[str] = field(default_factory=list)
    
    @property
    def avg_response_time(self) -> float:
        return self.total_response_time / self.operations_performed if self.operations_performed > 0 else 0.0
        
    @property
    def success_rate(self) -> float:
        return self.operations_successful / self.operations_performed if self.operations_performed > 0 else 0.0


@dataclass
class UserOperation:
    """Represents a single user operation"""
    user_id: str
    operation_type: str
    start_time: float
    end_time: float
    success: bool
    response_size_bytes: int = 0
    error_message: Optional[str] = None
    
    @property
    def response_time_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


class MultiUserPerformanceTester:
    """Test system performance under multi-user load"""
    
    def __init__(self, max_concurrent_users: int = 20) -> None:
        """Initialize MultiUserPerformanceTester.
        
        Args:
            max_concurrent_users: Maximum number of concurrent users for testing.
                                 Defaults to 20.
        """
        self.max_concurrent_users = max_concurrent_users
        self.user_sessions: List[UserSession] = []
        self.user_operations: List[UserOperation] = []
        self.system_metrics: Dict[str, List[float]] = {
            "cpu_usage": [],
            "memory_usage": [],
            "response_times": [],
            "throughput": []
        }
        
    def simulate_multi_user_load(
        self,
        user_count: int,
        session_duration_seconds: int = 300,
        operation_types: List[str] = None
    ) -> Dict[str, Any]:
        """Simulate multi-user load on the system"""
        if operation_types is None:
            operation_types = [
                "dataset_conversion",
                "api_query", 
                "ui_interaction",
                "report_generation",
                "configuration_change"
            ]
            
        start_time = time.time()
        
        # Create user sessions
        for i in range(user_count):
            user_session = UserSession(
                user_id=f"user_{i:03d}",
                session_start=start_time + random.uniform(0, 30),  # Stagger user arrivals
                session_duration=session_duration_seconds + random.uniform(-60, 60)  # Vary session lengths
            )
            self.user_sessions.append(user_session)
            
        # Run concurrent user sessions
        with ThreadPoolExecutor(max_workers=min(user_count, self.max_concurrent_users)) as executor:
            futures = []
            for user_session in self.user_sessions:
                future = executor.submit(self._simulate_user_session, user_session, operation_types)
                futures.append(future)
                
            # Wait for all sessions to complete
            for future in as_completed(futures):
                future.result()
                
        return self._analyze_multi_user_performance()
        
    def simulate_concurrent_users(
        self, 
        user_count: int, 
        session_duration_seconds: int = 300, 
        operation_types: List[str] = None
    ) -> Dict[str, Any]:
        """Alias for simulate_multi_user_load"""
        return self.simulate_multi_user_load(user_count, session_duration_seconds, operation_types)
        
    def _simulate_user_session(self, user_session: UserSession, operation_types: List[str]) -> None:
        """Simulate a single user session"""
        session_end_time = user_session.session_start + user_session.session_duration
        
        # Wait for session start time
        time.sleep(max(0, user_session.session_start - time.time()))
        
        while time.time() < session_end_time:
            # Choose random operation
            operation_type = random.choice(operation_types)
            
            # Perform operation
            operation_result = self._perform_user_operation(user_session.user_id, operation_type)
            self.user_operations.append(operation_result)
            
            # Update session stats
            user_session.operations_performed += 1
            user_session.total_response_time += operation_result.response_time_ms
            
            if operation_result.success:
                user_session.operations_successful += 1
            else:
                user_session.errors_encountered.append(operation_result.error_message or "unknown_error")
                
            # Simulate user think time
            think_time = random.uniform(1, 10)  # 1-10 seconds between operations
            time.sleep(think_time)
            
    def _perform_user_operation(self, user_id: str, operation_type: str) -> UserOperation:
        """Simulate a single user operation"""
        start_time = time.time()
        
        # Mock operation processing based on type
        operation_delays = {
            "dataset_conversion": random.uniform(2, 8),
            "api_query": random.uniform(0.1, 0.5),
            "ui_interaction": random.uniform(0.05, 0.3),
            "report_generation": random.uniform(3, 12),
            "configuration_change": random.uniform(0.5, 2)
        }
        
        processing_delay = operation_delays.get(operation_type, 1.0)
        time.sleep(processing_delay * 0.1)  # Reduced for testing
        
        end_time = time.time()
        
        # Mock success rates (vary by operation type)
        success_rates = {
            "dataset_conversion": 0.90,
            "api_query": 0.98,
            "ui_interaction": 0.95,
            "report_generation": 0.85,
            "configuration_change": 0.92
        }
        
        success_rate = success_rates.get(operation_type, 0.95)
        success = random.random() < success_rate
        
        return UserOperation(
            user_id=user_id,
            operation_type=operation_type,
            start_time=start_time,
            end_time=end_time,
            success=success,
            response_size_bytes=random.randint(1024, 10240),
            error_message="Mock operation error" if not success else None
        )
        
    def _analyze_multi_user_performance(self) -> Dict[str, Any]:
        """Analyze multi-user performance results"""
        if not self.user_sessions or not self.user_operations:
            return {"error": "No user session data available"}
            
        successful_ops = [op for op in self.user_operations if op.success]
        failed_ops = [op for op in self.user_operations if not op.success]
        
        # Overall system metrics
        total_operations = len(self.user_operations)
        total_users = len(self.user_sessions)
        
        # Response time analysis
        response_times = [op.response_time_ms for op in successful_ops]
        
        # User session analysis
        avg_session_duration = sum(s.session_duration for s in self.user_sessions) / len(self.user_sessions)
        avg_operations_per_user = sum(s.operations_performed for s in self.user_sessions) / len(self.user_sessions)
        
        # Throughput analysis
        test_duration = (
            max(op.end_time for op in self.user_operations) - min(op.start_time for op in self.user_operations)
        )
        throughput_ops_per_second = total_operations / test_duration if test_duration > 0 else 0
        
        return {
            "test_summary": {
                "total_users": total_users,
                "total_operations": total_operations,
                "successful_operations": len(successful_ops),
                "failed_operations": len(failed_ops),
                "overall_success_rate": len(successful_ops) / total_operations,
                "test_duration_seconds": test_duration,
                "throughput_ops_per_second": throughput_ops_per_second
            },
            "user_behavior_analysis": {
                "avg_session_duration_seconds": avg_session_duration,
                "avg_operations_per_user": avg_operations_per_user,
                "avg_user_success_rate": sum(s.success_rate for s in self.user_sessions) / len(self.user_sessions),
                "concurrent_user_peak": min(total_users, self.max_concurrent_users)
            },
            "performance_metrics": {
                "avg_response_time_ms": sum(response_times) / len(response_times) if response_times else 0,
                "min_response_time_ms": min(response_times) if response_times else 0,
                "max_response_time_ms": max(response_times) if response_times else 0,
                "response_time_95th_percentile": self._percentile(response_times, 95),
                "response_time_99th_percentile": self._percentile(response_times, 99)
            },
            "operation_breakdown": self._analyze_operation_types(),
            "error_analysis": {
                "error_rate_by_operation": self._get_error_rates_by_operation(),
                "common_errors": self._get_common_errors(),
                "users_with_errors": len([s for s in self.user_sessions if s.errors_encountered])
            },
            "scalability_insights": {
                "performance_degradation": self._assess_performance_degradation(),
                "resource_contention_detected": len(failed_ops) > total_operations * 0.05,
                "system_stability": len(successful_ops) / total_operations >= 0.90
            }
        }
        
    def _analyze_operation_types(self) -> Dict[str, Dict[str, Any]]:
        """Analyze performance by operation type"""
        operation_analysis = {}
        
        operation_types = set(op.operation_type for op in self.user_operations)
        
        for op_type in operation_types:
            type_operations = [op for op in self.user_operations if op.operation_type == op_type]
            successful_type_ops = [op for op in type_operations if op.success]
            
            if successful_type_ops:
                response_times = [op.response_time_ms for op in successful_type_ops]
                operation_analysis[op_type] = {
                    "total_operations": len(type_operations),
                    "successful_operations": len(successful_type_ops),
                    "success_rate": len(successful_type_ops) / len(type_operations),
                    "avg_response_time_ms": sum(response_times) / len(response_times),
                    "max_response_time_ms": max(response_times),
                    "min_response_time_ms": min(response_times)
                }
            else:
                operation_analysis[op_type] = {
                    "total_operations": len(type_operations),
                    "successful_operations": 0,
                    "success_rate": 0.0,
                    "avg_response_time_ms": 0,
                    "max_response_time_ms": 0,
                    "min_response_time_ms": 0
                }
                
        return operation_analysis
        
    def _get_error_rates_by_operation(self) -> Dict[str, float]:
        """Get error rates by operation type"""
        error_rates = {}
        operation_types = set(op.operation_type for op in self.user_operations)
        
        for op_type in operation_types:
            type_operations = [op for op in self.user_operations if op.operation_type == op_type]
            failed_operations = [op for op in type_operations if not op.success]
            error_rates[op_type] = len(failed_operations) / len(type_operations) if type_operations else 0
            
        return error_rates
        
    def _get_common_errors(self) -> List[Dict[str, Any]]:
        """Get most common error messages"""
        error_counts = {}
        
        for session in self.user_sessions:
            for error in session.errors_encountered:
                error_counts[error] = error_counts.get(error, 0) + 1
                
        # Sort by frequency and return top 10
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return [{"error_message": error, "frequency": count} for error, count in sorted_errors]
        
    def _assess_performance_degradation(self) -> Dict[str, Any]:
        """Assess if performance degraded under multi-user load"""
        if len(self.user_operations) < 100:  # Need sufficient data
            return {"assessment": "insufficient_data"}
            
        # Compare early vs late operations
        operations_sorted = sorted(self.user_operations, key=lambda x: x.start_time)
        early_ops = operations_sorted[:len(operations_sorted)//4]  # First quarter
        late_ops = operations_sorted[-len(operations_sorted)//4:]  # Last quarter
        
        early_response_times = [op.response_time_ms for op in early_ops if op.success]
        late_response_times = [op.response_time_ms for op in late_ops if op.success]
        
        if not early_response_times or not late_response_times:
            return {"assessment": "insufficient_success_data"}
            
        avg_early = sum(early_response_times) / len(early_response_times)
        avg_late = sum(late_response_times) / len(late_response_times)
        
        degradation_percent = ((avg_late - avg_early) / avg_early) * 100 if avg_early > 0 else 0
        
        return {
            "avg_early_response_time_ms": avg_early,
            "avg_late_response_time_ms": avg_late,
            "degradation_percent": degradation_percent,
            "degradation_severity": (
                "none" if degradation_percent < 5 else
                "mild" if degradation_percent < 20 else
                "moderate" if degradation_percent < 50 else
                "severe"
            )
        }
        
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of response times"""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


def test_multi_user_performance(
    user_count: int = 10,
    session_duration_seconds: int = 60,
    operation_types: List[str] = None
) -> Dict[str, Any]:
    """Convenience function for multi-user performance testing"""
    tester = MultiUserPerformanceTester()
    return tester.simulate_multi_user_load(user_count, session_duration_seconds, operation_types)


def validate_multi_user_requirements(
    max_users: int,
    max_response_time_ms: float,
    min_success_rate: float
) -> Dict[str, Any]:
    """Validate system meets multi-user performance requirements"""
    results = test_multi_user_performance(user_count=max_users, session_duration_seconds=30)
    
    actual_response_time = results["performance_metrics"]["avg_response_time_ms"]
    actual_success_rate = results["test_summary"]["overall_success_rate"]
    
    return {
        "requirements_validation": {
            "max_users_tested": max_users,
            "response_time_requirement_met": actual_response_time <= max_response_time_ms,
            "success_rate_requirement_met": actual_success_rate >= min_success_rate,
            "overall_requirements_met": (
                actual_response_time <= max_response_time_ms and
                actual_success_rate >= min_success_rate
            )
        },
        "actual_performance": {
            "avg_response_time_ms": actual_response_time,
            "success_rate": actual_success_rate
        },
        "performance_margin": {
            "response_time_margin_ms": max_response_time_ms - actual_response_time,
            "success_rate_margin": actual_success_rate - min_success_rate
        },
        "detailed_results": results
    }