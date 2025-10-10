# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
User Acceptance Test Fixtures

This module provides test fixtures for user acceptance testing in the ViolentUTF
end-to-end testing framework.

SECURITY: All test data is for defensive security research only.
"""

from typing import Any, Dict, List


def create_acceptance_test_data() -> Dict[str, Any]:
    """
    Create user acceptance test data fixtures for end-to-end testing.
    
    Returns test data specifically designed for user acceptance validation
    and usability testing across all user personas and workflows.
    """
    return {
        "test_user_personas": {
            "security_researcher": {
                "experience_level": "expert",
                "technical_background": "cybersecurity",
                "primary_tasks": ["vulnerability_assessment", "threat_analysis", "security_reporting"],
                "usability_expectations": {
                    "task_completion_efficiency": "high",
                    "technical_detail_preference": "comprehensive",
                    "error_tolerance": "low"
                }
            },
            "compliance_officer": {
                "experience_level": "intermediate",
                "technical_background": "regulatory_compliance",
                "primary_tasks": ["compliance_validation", "risk_assessment", "audit_reporting"],
                "usability_expectations": {
                    "task_completion_efficiency": "moderate",
                    "guidance_preference": "detailed_with_templates",
                    "error_tolerance": "very_low"
                }
            },
            "ai_researcher": {
                "experience_level": "expert",
                "technical_background": "machine_learning_research",
                "primary_tasks": ["model_evaluation", "benchmark_analysis", "research_validation"],
                "usability_expectations": {
                    "task_completion_efficiency": "very_high",
                    "customization_preference": "extensive",
                    "error_tolerance": "moderate"
                }
            },
            "enterprise_user": {
                "experience_level": "beginner_to_intermediate",
                "technical_background": "business_operations",
                "primary_tasks": ["team_coordination", "resource_management", "reporting"],
                "usability_expectations": {
                    "task_completion_efficiency": "moderate",
                    "simplicity_preference": "high",
                    "error_tolerance": "very_low"
                }
            }
        },
        "evaluation_workflows": {
            "garak_security_evaluation": {
                "workflow_steps": [
                    {"step": "authentication", "expected_time": 30, "complexity": "low"},
                    {"step": "dataset_selection", "expected_time": 60, "complexity": "medium"},
                    {"step": "configuration", "expected_time": 120, "complexity": "medium"},
                    {"step": "execution", "expected_time": 300, "complexity": "low"},
                    {"step": "results_review", "expected_time": 180, "complexity": "high"},
                    {"step": "report_generation", "expected_time": 90, "complexity": "medium"}
                ],
                "user_personas": ["security_researcher", "ai_researcher"],
                "success_criteria": {
                    "completion_rate": 0.90,
                    "average_satisfaction": 4.0,
                    "error_rate": 0.05
                }
            },
            "ollegen1_compliance_evaluation": {
                "workflow_steps": [
                    {"step": "authentication", "expected_time": 30, "complexity": "low"},
                    {"step": "dataset_upload", "expected_time": 90, "complexity": "medium"},
                    {"step": "regulatory_framework_selection", "expected_time": 60, "complexity": "high"},
                    {"step": "compliance_configuration", "expected_time": 180, "complexity": "high"},
                    {"step": "evaluation_execution", "expected_time": 600, "complexity": "medium"},
                    {"step": "compliance_report_generation", "expected_time": 120, "complexity": "medium"}
                ],
                "user_personas": ["compliance_officer", "enterprise_user"],
                "success_criteria": {
                    "completion_rate": 0.85,
                    "average_satisfaction": 4.1,
                    "error_rate": 0.03
                }
            },
            "cross_domain_research_evaluation": {
                "workflow_steps": [
                    {"step": "authentication", "expected_time": 30, "complexity": "low"},
                    {"step": "multi_dataset_selection", "expected_time": 180, "complexity": "high"},
                    {"step": "comparative_configuration", "expected_time": 240, "complexity": "very_high"},
                    {"step": "parallel_evaluation_execution", "expected_time": 900, "complexity": "high"},
                    {"step": "cross_domain_analysis", "expected_time": 300, "complexity": "very_high"},
                    {"step": "research_report_compilation", "expected_time": 180, "complexity": "high"}
                ],
                "user_personas": ["ai_researcher"],
                "success_criteria": {
                    "completion_rate": 0.75,
                    "average_satisfaction": 4.2,
                    "error_rate": 0.08
                }
            }
        },
        "sample_evaluation_results": {
            "garak_security_assessment_results": {
                "result_structure": {
                    "executive_summary": {
                        "vulnerability_score": 7.2,
                        "risk_level": "high",
                        "critical_findings_count": 3
                    },
                    "detailed_analysis": {
                        "attack_success_rates": {"jailbreak": 0.15, "prompt_injection": 0.08, "adversarial": 0.12},
                        "vulnerability_categories": ["prompt_manipulation", "context_exploitation", "safety_bypass"]
                    },
                    "recommendations": [
                        "Implement additional prompt filtering",
                        "Strengthen context validation",
                        "Add safety guardrails for sensitive topics"
                    ]
                },
                "presentation_requirements": {
                    "visual_hierarchy": "executive_summary_first",
                    "action_items_highlighted": True,
                    "drill_down_capability": True
                }
            },
            "ollegen1_cognitive_evaluation_results": {
                "result_structure": {
                    "behavioral_summary": {
                        "cognitive_consistency_score": 8.1,
                        "behavioral_pattern_classification": "analytical_dominant",
                        "risk_assessment": "moderate"
                    },
                    "detailed_metrics": {
                        "cognitive_paths": {"analytical": 0.65, "intuitive": 0.25, "creative": 0.10},
                        "consistency_across_scenarios": 0.81,
                        "bias_detection_results": {"confirmation_bias": 0.12, "anchoring_bias": 0.08}
                    },
                    "compliance_indicators": {
                        "regulatory_alignment": "compliant",
                        "risk_thresholds": "within_acceptable_limits",
                        "audit_readiness": "ready"
                    }
                }
            }
        },
        "error_test_scenarios": {
            "network_connection_errors": [
                {
                    "error_type": "connection_timeout",
                    "context": "dataset_conversion_api_call",
                    "error_message": "Connection timeout while converting dataset. Please check your network connection and try again.",
                    "recovery_options": ["retry_operation", "check_network", "contact_support"],
                    "expected_user_action": "retry_after_network_check"
                },
                {
                    "error_type": "service_unavailable",
                    "context": "evaluation_execution",
                    "error_message": "Evaluation service is temporarily unavailable. Your work has been saved and you can resume when the service is restored.",
                    "recovery_options": ["wait_and_retry", "save_current_work", "check_service_status"],
                    "expected_user_action": "wait_for_service_restoration"
                }
            ],
            "data_validation_errors": [
                {
                    "error_type": "invalid_dataset_format",
                    "context": "dataset_upload",
                    "error_message": "The uploaded file does not match the expected format for Garak datasets. Please ensure your file is in JSONL format with required fields.",
                    "recovery_options": ["fix_file_format", "use_template", "view_format_guide"],
                    "expected_user_action": "correct_file_format_and_reupload"
                }
            ],
            "system_resource_errors": [
                {
                    "error_type": "memory_exhausted",
                    "context": "large_dataset_processing",
                    "error_message": "Processing this large dataset requires more memory than currently available. Consider splitting the dataset or trying during off-peak hours.",
                    "recovery_options": ["split_dataset", "retry_later", "contact_admin"],
                    "expected_user_action": "split_dataset_or_retry_later"
                }
            ]
        },
        "usability_test_scenarios": {
            "dataset_selection_tasks": [
                {
                    "task": "find_garak_dataset_for_jailbreak_testing",
                    "user_persona": "security_researcher",
                    "success_criteria": {
                        "task_completion_time": 90,  # seconds
                        "clicks_to_completion": 5,
                        "error_count": 0
                    },
                    "difficulty_level": "easy"
                },
                {
                    "task": "configure_ollegen1_for_compliance_assessment",
                    "user_persona": "compliance_officer",
                    "success_criteria": {
                        "task_completion_time": 300,  # seconds
                        "configuration_accuracy": 0.95,
                        "help_documentation_usage": True
                    },
                    "difficulty_level": "medium"
                },
                {
                    "task": "setup_cross_domain_evaluation_comparison",
                    "user_persona": "ai_researcher",
                    "success_criteria": {
                        "task_completion_time": 600,  # seconds
                        "configuration_completeness": 0.90,
                        "advanced_features_usage": True
                    },
                    "difficulty_level": "hard"
                }
            ],
            "workflow_execution_tasks": [
                {
                    "task": "execute_complete_security_evaluation_workflow",
                    "workflow": "garak_security_evaluation",
                    "success_criteria": {
                        "workflow_completion": True,
                        "understanding_of_progress": True,
                        "successful_error_recovery": True
                    }
                }
            ]
        },
        "satisfaction_metrics": {
            "measurement_scales": {
                "satisfaction_scale": {"min": 1, "max": 5, "labels": ["Very Unsatisfied", "Unsatisfied", "Neutral", "Satisfied", "Very Satisfied"]},
                "ease_of_use_scale": {"min": 1, "max": 5, "labels": ["Very Difficult", "Difficult", "Neutral", "Easy", "Very Easy"]},
                "confidence_scale": {"min": 1, "max": 5, "labels": ["No Confidence", "Low Confidence", "Some Confidence", "Confident", "Very Confident"]}
            },
            "benchmark_scores": {
                "minimum_acceptable_satisfaction": 3.5,
                "target_satisfaction": 4.0,
                "excellent_satisfaction": 4.5,
                "minimum_task_completion_rate": 0.80,
                "target_task_completion_rate": 0.90
            }
        }
    }