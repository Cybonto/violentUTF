# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Load Test Fixtures

This module provides test fixtures for load testing in the ViolentUTF
end-to-end testing framework.

SECURITY: All test data is for defensive security research only.
"""

from typing import Dict, List, Any


def create_load_test_data() -> Dict[str, Any]:
    """
    Create load test data fixtures for end-to-end testing.
    
    Returns test data specifically designed for load testing
    and concurrent operation validation.
    """
    return {
        "concurrent_operation_scenarios": {
            "light_load": {
                "concurrent_conversions": 3,
                "dataset_types": ["garak", "acpbench", "confaide"],
                "expected_completion_time": 300,
                "resource_limits": {
                    "max_cpu_percent": 70,
                    "max_memory_percent": 60,
                    "max_disk_io_mbps": 50
                }
            },
            "moderate_load": {
                "concurrent_conversions": 5,
                "dataset_types": ["garak", "ollegen1", "acpbench", "legalbench", "confaide"],
                "expected_completion_time": 600,
                "resource_limits": {
                    "max_cpu_percent": 80,
                    "max_memory_percent": 75,
                    "max_disk_io_mbps": 80
                }
            },
            "heavy_load": {
                "concurrent_conversions": 8,
                "dataset_types": ["all_dataset_types_including_large"],
                "expected_completion_time": 1200,
                "resource_limits": {
                    "max_cpu_percent": 90,
                    "max_memory_percent": 85,
                    "max_disk_io_mbps": 100
                }
            }
        },
        "user_load_scenarios": {
            "multi_user_light": {
                "concurrent_users": 5,
                "user_types": ["security_researcher", "compliance_officer"],
                "operations_per_user": 2,
                "session_duration": 600
            },
            "multi_user_moderate": {
                "concurrent_users": 10,
                "user_types": ["security_researcher", "compliance_officer", "ai_researcher"],
                "operations_per_user": 3,
                "session_duration": 900
            },
            "enterprise_scale": {
                "concurrent_users": 20,
                "user_types": ["all_user_types"],
                "operations_per_user": 4,
                "session_duration": 1200
            }
        },
        "stress_test_configurations": {
            "memory_stress": {
                "target_memory_usage_percent": 90,
                "memory_allocation_rate_mbps": 100,
                "duration_seconds": 300
            },
            "cpu_stress": {
                "target_cpu_usage_percent": 95,
                "cpu_intensive_operations": True,
                "duration_seconds": 600
            },
            "io_stress": {
                "target_io_throughput_mbps": 150,
                "concurrent_file_operations": 10,
                "duration_seconds": 480
            }
        }
    }