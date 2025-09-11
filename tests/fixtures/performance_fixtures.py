# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Performance Test Fixtures

This module provides test fixtures for performance testing in the ViolentUTF
end-to-end testing framework.

SECURITY: All test data is for defensive security research only.
"""

from typing import Dict, List, Any
import time


def create_performance_test_data() -> Dict[str, Any]:
    """
    Create performance test data fixtures for end-to-end testing.
    
    Returns test data specifically designed for performance validation
    across all dataset types and operations.
    """
    return {
        "performance_benchmarks": {
            "dataset_conversion_benchmarks": {
                "garak_collection": {
                    "target_processing_time_seconds": 30,
                    "target_memory_usage_mb": 500,
                    "target_cpu_utilization_percent": 80,
                    "dataset_size_estimate_mb": 25,
                    "operation_complexity": "medium"
                },
                "ollegen1_full": {
                    "target_processing_time_seconds": 600,
                    "target_memory_usage_mb": 2048,
                    "target_cpu_utilization_percent": 85,
                    "dataset_size_estimate_mb": 150,
                    "operation_complexity": "high"
                },
                "acpbench_all": {
                    "target_processing_time_seconds": 120,
                    "target_memory_usage_mb": 500,
                    "target_cpu_utilization_percent": 75,
                    "dataset_size_estimate_mb": 50,
                    "operation_complexity": "medium"
                },
                "legalbench_166_dirs": {
                    "target_processing_time_seconds": 600,
                    "target_memory_usage_mb": 1024,
                    "target_cpu_utilization_percent": 80,
                    "dataset_size_estimate_mb": 100,
                    "operation_complexity": "high"
                },
                "docmath_220mb": {
                    "target_processing_time_seconds": 1800,
                    "target_memory_usage_mb": 2048,
                    "target_cpu_utilization_percent": 90,
                    "dataset_size_estimate_mb": 220,
                    "operation_complexity": "very_high"
                },
                "graphwalk_480mb": {
                    "target_processing_time_seconds": 1800,
                    "target_memory_usage_mb": 2048,
                    "target_cpu_utilization_percent": 85,
                    "dataset_size_estimate_mb": 480,
                    "operation_complexity": "very_high"
                },
                "confaide_4_tiers": {
                    "target_processing_time_seconds": 180,
                    "target_memory_usage_mb": 500,
                    "target_cpu_utilization_percent": 70,
                    "dataset_size_estimate_mb": 30,
                    "operation_complexity": "medium"
                },
                "judgebench_all": {
                    "target_processing_time_seconds": 300,
                    "target_memory_usage_mb": 1024,
                    "target_cpu_utilization_percent": 80,
                    "dataset_size_estimate_mb": 75,
                    "operation_complexity": "high"
                }
            },
            "api_performance_benchmarks": {
                "authentication_endpoints": {
                    "target_response_time_ms": 200,
                    "concurrent_user_capacity": 10,
                    "throughput_requests_per_second": 50
                },
                "dataset_management_endpoints": {
                    "target_response_time_ms": 500,
                    "concurrent_user_capacity": 5,
                    "throughput_requests_per_second": 20
                },
                "conversion_endpoints": {
                    "target_response_time_ms": 300,
                    "concurrent_user_capacity": 3,
                    "throughput_requests_per_second": 10
                },
                "evaluation_endpoints": {
                    "target_response_time_ms": 1000,
                    "concurrent_user_capacity": 5,
                    "throughput_requests_per_second": 15
                }
            }
        },
        "load_test_scenarios": {
            "concurrent_conversion_scenarios": [
                {
                    "scenario_name": "light_concurrent_load",
                    "concurrent_operations": 3,
                    "dataset_types": ["garak", "acpbench", "confaide"],
                    "expected_completion_time": 300,
                    "resource_usage_target": "moderate"
                },
                {
                    "scenario_name": "medium_concurrent_load",
                    "concurrent_operations": 5,
                    "dataset_types": ["garak", "ollegen1", "acpbench", "legalbench", "confaide"],
                    "expected_completion_time": 900,
                    "resource_usage_target": "high"
                },
                {
                    "scenario_name": "heavy_concurrent_load",
                    "concurrent_operations": 8,
                    "dataset_types": ["all_types_including_large_files"],
                    "expected_completion_time": 1800,
                    "resource_usage_target": "maximum"
                }
            ],
            "user_load_scenarios": [
                {
                    "scenario_name": "multi_user_light_load",
                    "concurrent_users": 5,
                    "operations_per_user": 2,
                    "user_types": ["security_researcher", "compliance_officer"],
                    "session_duration": 600
                },
                {
                    "scenario_name": "multi_user_moderate_load", 
                    "concurrent_users": 10,
                    "operations_per_user": 3,
                    "user_types": ["all_user_types"],
                    "session_duration": 900
                },
                {
                    "scenario_name": "enterprise_scale_load",
                    "concurrent_users": 20,
                    "operations_per_user": 4,
                    "user_types": ["enterprise_mixed"],
                    "session_duration": 1200
                }
            ]
        },
        "system_resource_targets": {
            "cpu_utilization": {
                "optimal_range_percent": [60, 80],
                "maximum_acceptable_percent": 90,
                "sustained_load_threshold": 85
            },
            "memory_utilization": {
                "optimal_range_percent": [50, 75],
                "maximum_acceptable_percent": 85,
                "memory_cleanup_target_percent": 95
            },
            "disk_io_performance": {
                "read_throughput_target_mbps": 100,
                "write_throughput_target_mbps": 80,
                "iops_target": 1000
            },
            "network_performance": {
                "api_throughput_target_mbps": 50,
                "concurrent_connection_capacity": 100,
                "response_time_target_ms": 500
            }
        }
    }


def create_stress_test_scenarios() -> Dict[str, Any]:
    """
    Create stress test scenarios for extreme load testing.
    
    Returns test scenarios designed to push system limits
    and validate failure handling.
    """
    return {
        "memory_stress_scenarios": {
            "gradual_memory_increase": {
                "start_memory_mb": 1000,
                "increment_memory_mb": 500,
                "max_memory_mb": 8000,
                "increment_interval_seconds": 60
            },
            "rapid_memory_allocation": {
                "target_memory_mb": 6000,
                "allocation_rate_mbps": 100,
                "hold_duration_seconds": 300
            }
        },
        "cpu_stress_scenarios": {
            "sustained_high_cpu": {
                "target_cpu_percent": 95,
                "duration_seconds": 600,
                "core_utilization": "all_cores"
            },
            "cpu_spike_patterns": {
                "spike_cpu_percent": 100,
                "spike_duration_seconds": 30,
                "interval_between_spikes": 60,
                "total_test_duration": 900
            }
        },
        "disk_stress_scenarios": {
            "high_io_throughput": {
                "read_rate_mbps": 200,
                "write_rate_mbps": 150,
                "duration_seconds": 300
            },
            "large_file_operations": {
                "file_size_gb": 5,
                "concurrent_file_operations": 3,
                "operation_types": ["read", "write", "delete"]
            }
        }
    }