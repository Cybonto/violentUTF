# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Regression Test Fixtures

This module provides test fixtures for regression testing in the ViolentUTF
end-to-end testing framework.

SECURITY: All test data is for defensive security research only.
"""

from typing import Any, Dict, List


def create_regression_test_data() -> Dict[str, Any]:
    """
    Create regression test data fixtures for end-to-end testing.
    
    Returns test data specifically designed for regression testing
    and baseline comparison validation.
    """
    return {
        "conversion_test_datasets": {
            "garak_test_collection": {
                "dataset_files": ["test_jailbreak.jsonl", "test_injection.jsonl"],
                "expected_accuracy": 0.95,
                "baseline_metrics": {
                    "template_extraction_accuracy": 0.96,
                    "attack_classification_accuracy": 0.94,
                    "metadata_preservation": 0.98
                }
            },
            "ollegen1_test_scenarios": {
                "dataset_files": ["test_scenarios.csv"],
                "expected_accuracy": 0.92,
                "baseline_metrics": {
                    "person_profile_extraction": 0.93,
                    "scenario_parsing_accuracy": 0.91,
                    "data_completeness": 0.97
                }
            },
            "acpbench_test_problems": {
                "dataset_files": ["test_reasoning.json"],
                "expected_accuracy": 0.97,
                "baseline_metrics": {
                    "problem_parsing_accuracy": 0.98,
                    "answer_format_compliance": 0.96,
                    "reasoning_structure_preservation": 0.97
                }
            },
            "confaide_test_scenarios": {
                "dataset_files": ["test_privacy.json"],
                "expected_accuracy": 0.94,
                "baseline_metrics": {
                    "privacy_tier_classification": 0.95,
                    "context_extraction_accuracy": 0.93,
                    "scenario_completeness": 0.96
                }
            }
        },
        "performance_test_operations": {
            "dataset_conversions": [
                {"operation": "garak_conversion", "baseline_time": 25, "dataset_size_mb": 10},
                {"operation": "ollegen1_conversion", "baseline_time": 480, "dataset_size_mb": 120},
                {"operation": "acpbench_conversion", "baseline_time": 90, "dataset_size_mb": 40},
                {"operation": "confaide_conversion", "baseline_time": 150, "dataset_size_mb": 25}
            ],
            "api_operations": [
                {"endpoint": "/api/v1/datasets", "method": "GET", "baseline_response_time": 150},
                {"endpoint": "/api/v1/converters/status", "method": "GET", "baseline_response_time": 80},
                {"endpoint": "/api/v1/evaluations/results", "method": "GET", "baseline_response_time": 300}
            ],
            "workflow_operations": [
                {"workflow": "garak_security_evaluation", "baseline_steps": 8, "baseline_time": 300},
                {"workflow": "ollegen1_cognitive_evaluation", "baseline_steps": 6, "baseline_time": 600},
                {"workflow": "cross_domain_evaluation", "baseline_steps": 12, "baseline_time": 900}
            ]
        },
        "integrity_test_data": {
            "checksum_validation_data": {
                "input_checksums": {
                    "garak_test_file.jsonl": "sha256:abc123def456",
                    "ollegen1_test_file.csv": "sha256:def456ghi789",
                    "acpbench_test_file.json": "sha256:ghi789jkl012"
                },
                "expected_output_checksums": {
                    "garak_converted.json": "sha256:jkl012mno345",
                    "ollegen1_converted.json": "sha256:mno345pqr678",
                    "acpbench_converted.json": "sha256:pqr678stu901"
                }
            },
            "schema_compliance_data": {
                "pyrit_schema_version": "1.0",
                "required_fields": ["id", "template", "metadata", "conversation_data"],
                "field_type_validation": True,
                "schema_evolution_compatibility": "backward_compatible"
            },
            "data_completeness_validation": {
                "expected_record_counts": {
                    "garak_test_conversion": 150,
                    "ollegen1_test_conversion": 75,
                    "acpbench_test_conversion": 200,
                    "confaide_test_conversion": 100
                },
                "completeness_threshold": 0.99
            }
        },
        "baseline_storage_data": {
            "baseline_versions": {
                "v1.0.0": {
                    "timestamp": "2025-01-01T00:00:00Z",
                    "performance_baselines": {
                        "garak_conversion": {"time": 25, "memory": 400, "accuracy": 0.95},
                        "ollegen1_conversion": {"time": 480, "memory": 1500, "accuracy": 0.92}
                    },
                    "quality_baselines": {
                        "overall_quality_score": 0.94,
                        "conversion_accuracy": 0.95,
                        "data_integrity": 0.98
                    }
                },
                "v1.1.0": {
                    "timestamp": "2025-01-15T00:00:00Z",
                    "performance_baselines": {
                        "garak_conversion": {"time": 23, "memory": 380, "accuracy": 0.96},
                        "ollegen1_conversion": {"time": 460, "memory": 1450, "accuracy": 0.93}
                    },
                    "quality_baselines": {
                        "overall_quality_score": 0.95,
                        "conversion_accuracy": 0.96,
                        "data_integrity": 0.98
                    }
                }
            },
            "baseline_comparison_thresholds": {
                "performance_degradation_alert": 0.10,  # 10%
                "accuracy_degradation_alert": 0.02,     # 2%
                "critical_regression_threshold": 0.05   # 5%
            }
        }
    }


def create_regression_validation_scenarios() -> Dict[str, Any]:
    """
    Create regression validation scenario fixtures.
    
    Returns test scenarios for validating different types of regressions
    across system components and functionality.
    """
    return {
        "conversion_accuracy_scenarios": [
            {
                "scenario_name": "garak_template_extraction_regression",
                "dataset_type": "garak",
                "baseline_accuracy": 0.96,
                "test_files": ["garak_template_test_1.jsonl", "garak_template_test_2.jsonl"],
                "validation_metrics": ["template_accuracy", "metadata_preservation", "format_compliance"]
            },
            {
                "scenario_name": "ollegen1_profile_parsing_regression",
                "dataset_type": "ollegen1",
                "baseline_accuracy": 0.93,
                "test_files": ["ollegen1_profile_test.csv"],
                "validation_metrics": ["profile_extraction", "scenario_parsing", "data_completeness"]
            }
        ],
        "performance_regression_scenarios": [
            {
                "scenario_name": "conversion_time_regression",
                "operation_type": "dataset_conversion",
                "baseline_metrics": {
                    "garak_conversion_time": 25,
                    "ollegen1_conversion_time": 480,
                    "memory_usage_baseline": 1500
                },
                "acceptable_degradation": 0.10,
                "critical_threshold": 0.20
            },
            {
                "scenario_name": "api_response_time_regression",
                "operation_type": "api_performance",
                "baseline_metrics": {
                    "dataset_list_response": 150,
                    "conversion_status_response": 80,
                    "results_retrieval_response": 300
                },
                "acceptable_degradation": 0.15,
                "critical_threshold": 0.30
            }
        ],
        "workflow_consistency_scenarios": [
            {
                "scenario_name": "security_evaluation_workflow_regression",
                "workflow_type": "security_evaluation",
                "baseline_workflow": {
                    "steps": ["auth", "dataset_select", "configure", "execute", "analyze", "report"],
                    "success_rate": 0.95,
                    "completion_time": 300
                },
                "consistency_requirements": {
                    "step_sequence_stable": True,
                    "outcome_predictable": True,
                    "error_handling_consistent": True
                }
            }
        ]
    }