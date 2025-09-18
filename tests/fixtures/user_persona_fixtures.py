# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
User Persona Test Fixtures

This module provides test fixtures for user persona testing in the ViolentUTF
end-to-end testing framework.

SECURITY: All test data is for defensive security research only.
"""

from typing import Any, Dict, List


def create_user_personas() -> Dict[str, Any]:
    """
    Create user persona fixtures for end-to-end testing.
    
    Returns test data representing different user personas
    and their workflow preferences.
    """
    return {
        "security_researcher": {
            "profile": {
                "experience_level": "expert",
                "domain_expertise": ["vulnerability_assessment", "red_teaming", "ai_security"],
                "primary_goals": ["vulnerability_detection", "security_assessment", "risk_analysis"],
                "workflow_preferences": {
                    "detailed_configuration": True,
                    "real_time_monitoring": True,
                    "comprehensive_reporting": True,
                    "custom_attack_scenarios": True
                }
            },
            "preferred_datasets": ["garak_comprehensive", "red_team_collection"],
            "typical_workflows": [
                "garak_security_evaluation",
                "custom_attack_scenario_testing", 
                "vulnerability_assessment_reporting"
            ],
            "success_metrics": [
                "vulnerability_detection_rate",
                "false_positive_rate",
                "assessment_completion_time"
            ]
        },
        "compliance_officer": {
            "profile": {
                "experience_level": "intermediate",
                "domain_expertise": ["regulatory_compliance", "policy_enforcement", "risk_management"],
                "primary_goals": ["compliance_validation", "risk_assessment", "regulatory_reporting"],
                "workflow_preferences": {
                    "regulatory_templates": True,
                    "automated_compliance_checks": True,
                    "audit_trail_logging": True,
                    "standardized_reporting": True
                }
            },
            "regulatory_focus": ["gdpr", "ai_act", "financial_regulations"],
            "preferred_datasets": ["ollegen1_behavioral", "compliance_test_suites"],
            "typical_workflows": [
                "ollegen1_compliance_assessment",
                "regulatory_framework_validation",
                "compliance_reporting_generation"
            ],
            "success_metrics": [
                "compliance_score",
                "regulatory_adherence_rate",
                "audit_readiness_score"
            ]
        },
        "legal_professional": {
            "profile": {
                "experience_level": "expert",
                "domain_expertise": ["legal_reasoning", "case_analysis", "statutory_interpretation"],
                "primary_goals": ["legal_ai_evaluation", "reasoning_quality_assessment"],
                "workflow_preferences": {
                    "case_law_integration": True,
                    "legal_citation_validation": True,
                    "jurisdiction_specific_analysis": True,
                    "precedent_based_evaluation": True
                }
            },
            "legal_specialties": ["contract_law", "criminal_law", "constitutional_law"],
            "preferred_datasets": ["legalbench_comprehensive", "legal_reasoning_tasks"],
            "typical_workflows": [
                "legalbench_evaluation",
                "legal_reasoning_assessment",
                "ai_legal_capability_validation"
            ],
            "success_metrics": [
                "legal_accuracy_score",
                "reasoning_quality_index",
                "citation_correctness_rate"
            ]
        },
        "privacy_engineer": {
            "profile": {
                "experience_level": "expert",
                "domain_expertise": ["privacy_engineering", "data_protection", "contextual_integrity"],
                "primary_goals": ["privacy_assessment", "contextual_integrity_validation"],
                "workflow_preferences": {
                    "privacy_tier_classification": True,
                    "contextual_analysis": True,
                    "privacy_risk_quantification": True,
                    "differential_privacy_validation": True
                }
            },
            "privacy_specialties": ["data_minimization", "contextual_integrity", "differential_privacy"],
            "preferred_datasets": ["confaide_privacy_evaluation", "privacy_test_scenarios"],
            "typical_workflows": [
                "confaide_privacy_assessment",
                "contextual_integrity_evaluation", 
                "privacy_risk_analysis"
            ],
            "success_metrics": [
                "privacy_preservation_score",
                "contextual_appropriateness_index",
                "privacy_risk_level"
            ]
        },
        "ai_researcher": {
            "profile": {
                "experience_level": "expert",
                "domain_expertise": ["model_evaluation", "benchmarking", "cross_domain_analysis"],
                "primary_goals": ["comprehensive_model_assessment", "cross_domain_comparison"],
                "workflow_preferences": {
                    "multi_dataset_coordination": True,
                    "statistical_analysis": True,
                    "research_grade_reporting": True,
                    "reproducible_experiments": True
                }
            },
            "research_areas": ["model_evaluation", "cross_domain_analysis", "benchmarking"],
            "preferred_datasets": ["multi_domain_research_suite", "comprehensive_benchmark_collection"],
            "typical_workflows": [
                "multi_domain_comprehensive_evaluation",
                "cross_dataset_performance_analysis",
                "benchmark_comparison_studies"
            ],
            "success_metrics": [
                "evaluation_comprehensiveness_score",
                "cross_domain_correlation_analysis",
                "benchmark_performance_ranking"
            ]
        },
        "enterprise_user": {
            "profile": {
                "experience_level": "intermediate",
                "domain_expertise": ["enterprise_deployment", "team_management", "governance"],
                "primary_goals": ["scalable_evaluation", "team_collaboration", "governance"],
                "workflow_preferences": {
                    "role_based_access": True,
                    "team_collaboration": True,
                    "governance_and_audit": True,
                    "resource_management": True
                }
            },
            "organization_type": "large_corporation",
            "deployment_scale": "multi_team",
            "preferred_datasets": ["enterprise_evaluation_suite", "team_collaboration_datasets"],
            "typical_workflows": [
                "enterprise_multi_user_evaluation",
                "team_based_assessment_coordination",
                "governance_and_audit_reporting"
            ],
            "success_metrics": [
                "team_productivity_index",
                "resource_utilization_efficiency",
                "governance_compliance_score"
            ]
        }
    }


def create_user_workflow_scenarios() -> Dict[str, Any]:
    """
    Create user workflow scenario fixtures for testing.
    
    Returns detailed workflow scenarios for each user persona.
    """
    return {
        "security_researcher_workflows": {
            "garak_vulnerability_assessment": {
                "steps": [
                    "authenticate_via_sso",
                    "select_garak_dataset_collection",
                    "configure_red_teaming_parameters",
                    "select_target_model",
                    "initiate_security_evaluation",
                    "monitor_evaluation_progress",
                    "review_vulnerability_results",
                    "generate_security_report"
                ],
                "expected_duration": 600,  # seconds
                "required_permissions": ["security_analyst"],
                "success_criteria": [
                    "vulnerability_detection_completed",
                    "security_report_generated",
                    "results_exported_successfully"
                ]
            }
        },
        "compliance_officer_workflows": {
            "ollegen1_compliance_evaluation": {
                "steps": [
                    "authenticate_and_access_compliance_dashboard",
                    "select_ollegen1_behavioral_dataset",
                    "configure_regulatory_framework",
                    "set_compliance_thresholds",
                    "initiate_behavioral_assessment",
                    "review_cognitive_consistency_analysis",
                    "validate_regulatory_compliance",
                    "generate_compliance_report"
                ],
                "expected_duration": 900,  # seconds
                "required_permissions": ["compliance_manager"],
                "success_criteria": [
                    "compliance_assessment_completed",
                    "regulatory_validation_successful",
                    "audit_trail_documented"
                ]
            }
        }
    }