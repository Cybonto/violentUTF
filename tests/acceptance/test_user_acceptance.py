# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
User Acceptance Testing for Issue #132 - End-to-End Testing Framework

This module implements comprehensive user acceptance testing following
Test-Driven Development (TDD) methodology. Tests validate user acceptance
criteria across all workflows and user personas.

User Acceptance Testing Areas:
- Ease of dataset selection and configuration
- Evaluation workflow intuitiveness and usability
- Results interpretation clarity and usefulness
- Error handling and user experience quality
- Performance and user satisfaction validation
- Documentation and help system usability

SECURITY: All test data is for defensive security research only.

TDD Implementation:
- RED Phase: Tests MUST fail initially, identifying missing user acceptance validation
- GREEN Phase: Implement minimum user acceptance testing capability
- REFACTOR Phase: Optimize user experience and acceptance validation
"""

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# Test framework imports
from tests.utils.keycloak_auth import KeycloakTestAuth
from tests.fixtures.acceptance_fixtures import create_acceptance_test_data

# Import expected classes (these will initially fail - part of TDD RED phase)
try:
    from violentutf_api.fastapi_app.app.testing.user_acceptance import (
        UserAcceptanceTestManager,
        AcceptanceValidationError,
        UsabilityTestingError,
    )
except ImportError:
    # RED Phase: These imports will fail initially
    UserAcceptanceTestManager = None
    AcceptanceValidationError = Exception
    UsabilityTestingError = Exception

try:
    from violentutf_api.fastapi_app.app.services.user_experience_service import (
        UserExperienceService,
        UsabilityTestingService,
    )
except ImportError:
    # RED Phase: Service imports will fail initially
    UserExperienceService = None
    UsabilityTestingService = None

try:
    from violentutf_api.fastapi_app.app.schemas.user_acceptance import (
        UserAcceptanceTestRequest,
        UserAcceptanceResult,
        UsabilityMetrics,
        UserSatisfactionScore,
    )
except ImportError:
    # RED Phase: Schema imports will fail initially
    UserAcceptanceTestRequest = None
    UserAcceptanceResult = None
    UsabilityMetrics = None
    UserSatisfactionScore = None


class TestUserAcceptance:
    """
    Test user acceptance criteria for all workflows and personas.
    
    These tests validate that the ViolentUTF platform meets user expectations
    and provides an intuitive, effective user experience across all
    dataset evaluation workflows.
    """
    
    @pytest.fixture(autouse=True, scope="function")
    def setup_acceptance_test_environment(self):
        """Setup test environment for user acceptance testing."""
        self.test_session = f"acceptance_test_{int(time.time())}"
        self.auth_client = KeycloakTestAuth()
        self.acceptance_test_data = create_acceptance_test_data()
        
        # Setup test directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="acceptance_test_"))
        self.acceptance_results_dir = self.test_dir / "acceptance_results"
        self.usability_metrics_dir = self.test_dir / "usability_metrics"
        self.acceptance_results_dir.mkdir(exist_ok=True)
        self.usability_metrics_dir.mkdir(exist_ok=True)
        
        yield
        
        # Cleanup
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_ease_of_dataset_selection_and_configuration(self):
        """
        Test user ease of selecting and configuring datasets
        
        RED Phase: This test MUST fail initially
        Expected failure: UserAcceptanceTestManager not implemented
        
        User acceptance criteria for dataset selection:
        1. Dataset browsing and discovery is intuitive
        2. Dataset information and metadata is clearly presented
        3. Configuration options are self-explanatory
        4. Help and guidance is contextually available
        5. Selection process is efficient and error-free
        6. Advanced configuration is accessible but not overwhelming
        """
        # Arrange: Setup dataset selection acceptance test
        dataset_selection_criteria = {
            "usability_requirements": {
                "dataset_discovery_ease": {
                    "target_score": 4.0,  # out of 5.0
                    "measurement": "user_task_completion_rating",
                    "success_criteria": "users_can_find_relevant_datasets_within_30_seconds"
                },
                "configuration_intuitiveness": {
                    "target_score": 4.2,  # out of 5.0
                    "measurement": "configuration_completion_without_help",
                    "success_criteria": "80_percent_users_configure_without_documentation"
                },
                "information_clarity": {
                    "target_score": 4.5,  # out of 5.0
                    "measurement": "dataset_information_comprehension_rating",
                    "success_criteria": "users_understand_dataset_purpose_and_content"
                }
            },
            "task_scenarios": [
                {
                    "scenario": "security_researcher_selects_garak_dataset",
                    "user_persona": "security_researcher",
                    "task": "find_and_configure_garak_red_teaming_dataset",
                    "success_metrics": ["task_completion_time", "error_count", "user_satisfaction"]
                },
                {
                    "scenario": "compliance_officer_configures_ollegen1",
                    "user_persona": "compliance_officer",
                    "task": "configure_ollegen1_for_behavioral_assessment",
                    "success_metrics": ["configuration_accuracy", "completion_confidence", "help_usage"]
                }
            ],
            "acceptance_thresholds": {
                "task_completion_rate": 0.90,  # 90% of users complete successfully
                "average_satisfaction_score": 4.0,  # out of 5.0
                "maximum_task_time_minutes": 5  # maximum time for dataset selection
            }
        }
        
        # RED Phase: This will fail because UserAcceptanceTestManager is not implemented
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if UserAcceptanceTestManager is None:
                raise ImportError("UserAcceptanceTestManager not implemented")
            
            acceptance_manager = UserAcceptanceTestManager(session_id=self.test_session)
            selection_result = acceptance_manager.test_dataset_selection_usability(
                criteria=dataset_selection_criteria,
                test_users=self.acceptance_test_data["test_user_personas"]
            )
            
            # Validate acceptance criteria are met
            assert selection_result.task_completion_rate >= dataset_selection_criteria["acceptance_thresholds"]["task_completion_rate"]
            assert selection_result.average_satisfaction_score >= dataset_selection_criteria["acceptance_thresholds"]["average_satisfaction_score"]
            assert selection_result.average_task_time <= dataset_selection_criteria["acceptance_thresholds"]["maximum_task_time_minutes"] * 60
        
        # Validate expected failure
        assert any([
            "UserAcceptanceTestManager not implemented" in str(exc_info.value),
            "test_dataset_selection_usability" in str(exc_info.value),
            "user acceptance" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_acceptance_functionality("dataset_selection_usability", {
            "missing_classes": ["UserAcceptanceTestManager", "DatasetSelectionUsabilityTester"],
            "missing_methods": ["test_dataset_selection_usability", "measure_selection_efficiency"],
            "required_acceptance_features": [
                "Dataset browsing and discovery usability testing",
                "Configuration interface intuitiveness measurement",
                "User task completion time and success rate tracking",
                "User satisfaction and confidence scoring",
                "Contextual help and guidance effectiveness testing",
                "Error prevention and recovery usability validation"
            ],
            "usability_criteria": dataset_selection_criteria,
            "error_details": str(exc_info.value)
        })

    def test_evaluation_workflow_intuitiveness(self):
        """
        Test intuitiveness of evaluation workflows across all dataset types
        
        RED Phase: This test MUST fail initially
        Expected failure: Workflow usability testing not automated
        
        User acceptance criteria for evaluation workflows:
        1. Workflow steps are logical and predictable
        2. Progress indication is clear and accurate
        3. User can understand current status at any time
        4. Workflow can be paused and resumed intuitively
        5. Error states are clearly communicated with recovery options
        6. Results are presented clearly and actionably
        """
        # Arrange: Setup evaluation workflow acceptance test
        workflow_intuitiveness_criteria = {
            "workflow_usability_requirements": {
                "step_flow_logic": {
                    "target_score": 4.3,  # out of 5.0
                    "measurement": "workflow_logic_comprehension_rating",
                    "success_criteria": "users_predict_next_steps_accurately"
                },
                "progress_clarity": {
                    "target_score": 4.1,  # out of 5.0
                    "measurement": "progress_understanding_rating",
                    "success_criteria": "users_understand_completion_status_and_time"
                },
                "error_handling_clarity": {
                    "target_score": 3.8,  # out of 5.0
                    "measurement": "error_recovery_success_rate",
                    "success_criteria": "users_recover_from_errors_without_support"
                }
            },
            "workflow_scenarios": [
                {
                    "workflow": "garak_security_evaluation_workflow",
                    "user_personas": ["security_researcher", "ai_researcher"],
                    "complexity_level": "intermediate",
                    "expected_completion_time": 600  # seconds
                },
                {
                    "workflow": "ollegen1_compliance_evaluation_workflow",
                    "user_personas": ["compliance_officer", "enterprise_user"],
                    "complexity_level": "advanced",
                    "expected_completion_time": 900  # seconds
                },
                {
                    "workflow": "cross_domain_research_workflow",
                    "user_personas": ["ai_researcher"],
                    "complexity_level": "expert",
                    "expected_completion_time": 1200  # seconds
                }
            ],
            "acceptance_benchmarks": {
                "workflow_completion_rate": 0.85,  # 85% complete without assistance
                "step_prediction_accuracy": 0.75,  # 75% predict next step correctly
                "error_recovery_rate": 0.70,       # 70% recover from errors independently
                "overall_workflow_satisfaction": 4.0  # out of 5.0
            }
        }
        
        # RED Phase: This will fail because workflow usability testing is not automated
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if UserAcceptanceTestManager is None:
                raise ImportError("UserAcceptanceTestManager not implemented")
            
            acceptance_manager = UserAcceptanceTestManager(session_id=self.test_session)
            workflow_result = acceptance_manager.test_workflow_intuitiveness(
                criteria=workflow_intuitiveness_criteria,
                test_workflows=self.acceptance_test_data["evaluation_workflows"]
            )
            
            # Validate workflow intuitiveness acceptance criteria
            assert workflow_result.completion_rate >= workflow_intuitiveness_criteria["acceptance_benchmarks"]["workflow_completion_rate"]
            assert workflow_result.step_prediction_accuracy >= workflow_intuitiveness_criteria["acceptance_benchmarks"]["step_prediction_accuracy"]
            assert workflow_result.overall_satisfaction >= workflow_intuitiveness_criteria["acceptance_benchmarks"]["overall_workflow_satisfaction"]
        
        # Validate expected failure
        assert any([
            "UserAcceptanceTestManager not implemented" in str(exc_info.value),
            "test_workflow_intuitiveness" in str(exc_info.value),
            "workflow usability" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_acceptance_functionality("workflow_intuitiveness", {
            "missing_classes": ["UserAcceptanceTestManager", "WorkflowUsabilityTester"],
            "missing_methods": ["test_workflow_intuitiveness", "measure_workflow_usability"],
            "required_acceptance_features": [
                "Workflow step logic and flow usability testing",
                "Progress indication clarity and accuracy validation",
                "Error handling and recovery usability assessment",
                "Workflow completion and success rate measurement",
                "User satisfaction and confidence tracking",
                "Cross-workflow usability comparison and optimization"
            ],
            "workflow_criteria": workflow_intuitiveness_criteria,
            "error_details": str(exc_info.value)
        })

    def test_results_interpretation_clarity(self):
        """
        Test clarity and interpretability of evaluation results
        
        RED Phase: This test MUST fail initially
        Expected failure: Results presentation testing not implemented
        
        User acceptance criteria for results interpretation:
        1. Results are presented in a clear, organized manner
        2. Key findings are highlighted and easily identifiable
        3. Detailed data is accessible but not overwhelming
        4. Visualizations are informative and accurate
        5. Export and sharing options are intuitive
        6. Results can be compared across evaluations
        """
        # Arrange: Setup results interpretation acceptance test
        results_clarity_criteria = {
            "results_presentation_requirements": {
                "information_hierarchy": {
                    "target_score": 4.4,  # out of 5.0
                    "measurement": "results_scanning_efficiency",
                    "success_criteria": "users_identify_key_findings_within_30_seconds"
                },
                "visualization_effectiveness": {
                    "target_score": 4.0,  # out of 5.0
                    "measurement": "chart_interpretation_accuracy",
                    "success_criteria": "users_correctly_interpret_80_percent_of_visualizations"
                },
                "actionability": {
                    "target_score": 4.2,  # out of 5.0
                    "measurement": "next_steps_identification_rate",
                    "success_criteria": "users_identify_actionable_insights_from_results"
                }
            },
            "results_scenarios": [
                {
                    "result_type": "garak_security_assessment_results",
                    "complexity": "moderate",
                    "key_metrics": ["vulnerability_count", "risk_score", "attack_success_rate"],
                    "expected_interpretation_time": 120  # seconds
                },
                {
                    "result_type": "ollegen1_cognitive_evaluation_results",
                    "complexity": "high",
                    "key_metrics": ["cognitive_consistency", "behavioral_patterns", "risk_assessment"],
                    "expected_interpretation_time": 180  # seconds
                },
                {
                    "result_type": "cross_domain_comparison_results",
                    "complexity": "expert",
                    "key_metrics": ["domain_performance", "correlation_analysis", "benchmark_ranking"],
                    "expected_interpretation_time": 240  # seconds
                }
            ],
            "clarity_benchmarks": {
                "key_findings_identification_rate": 0.90,  # 90% identify key findings quickly
                "visualization_interpretation_accuracy": 0.80,  # 80% interpret charts correctly
                "actionable_insights_extraction_rate": 0.75,    # 75% extract actionable insights
                "results_satisfaction_score": 4.1             # out of 5.0
            }
        }
        
        # RED Phase: This will fail because results presentation testing is not implemented
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if UserAcceptanceTestManager is None:
                raise ImportError("UserAcceptanceTestManager not implemented")
            
            acceptance_manager = UserAcceptanceTestManager(session_id=self.test_session)
            results_clarity_result = acceptance_manager.test_results_interpretation_clarity(
                criteria=results_clarity_criteria,
                test_results=self.acceptance_test_data["sample_evaluation_results"]
            )
            
            # Validate results clarity acceptance criteria
            assert results_clarity_result.key_findings_identification_rate >= results_clarity_criteria["clarity_benchmarks"]["key_findings_identification_rate"]
            assert results_clarity_result.visualization_accuracy >= results_clarity_criteria["clarity_benchmarks"]["visualization_interpretation_accuracy"]
            assert results_clarity_result.satisfaction_score >= results_clarity_criteria["clarity_benchmarks"]["results_satisfaction_score"]
        
        # Validate expected failure
        assert any([
            "UserAcceptanceTestManager not implemented" in str(exc_info.value),
            "test_results_interpretation_clarity" in str(exc_info.value),
            "results presentation" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_acceptance_functionality("results_interpretation_clarity", {
            "missing_classes": ["UserAcceptanceTestManager", "ResultsPresentationTester"],
            "missing_methods": ["test_results_interpretation_clarity", "measure_results_usability"],
            "required_acceptance_features": [
                "Results presentation hierarchy and organization testing",
                "Visualization effectiveness and accuracy validation",
                "Key findings identification and highlighting assessment",
                "Actionable insights extraction rate measurement",
                "Results comparison and analysis usability testing",
                "Export and sharing functionality usability validation"
            ],
            "results_criteria": results_clarity_criteria,
            "error_details": str(exc_info.value)
        })

    def test_error_handling_user_experience(self):
        """
        Test user experience during error conditions and recovery
        
        RED Phase: This test MUST fail initially
        Expected failure: Error UX testing not automated
        
        User acceptance criteria for error handling:
        1. Error messages are clear and helpful
        2. Recovery options are clearly presented
        3. System maintains state during error recovery
        4. Users receive appropriate guidance for error resolution
        5. Error prevention is effective where possible
        6. Critical errors don't result in data loss
        """
        # Arrange: Setup error handling UX acceptance test
        error_handling_criteria = {
            "error_ux_requirements": {
                "error_message_clarity": {
                    "target_score": 3.8,  # out of 5.0
                    "measurement": "error_understanding_rate",
                    "success_criteria": "users_understand_error_cause_and_solution"
                },
                "recovery_guidance": {
                    "target_score": 4.0,  # out of 5.0
                    "measurement": "successful_error_recovery_rate",
                    "success_criteria": "users_recover_from_errors_without_external_help"
                },
                "state_preservation": {
                    "target_score": 4.5,  # out of 5.0
                    "measurement": "work_preservation_during_errors",
                    "success_criteria": "no_data_loss_during_error_recovery"
                }
            },
            "error_scenarios": [
                {
                    "error_type": "network_connection_failure",
                    "context": "during_dataset_conversion",
                    "expected_recovery_time": 60,  # seconds
                    "recovery_success_rate": 0.85
                },
                {
                    "error_type": "invalid_dataset_format",
                    "context": "dataset_upload_and_validation",
                    "expected_recovery_time": 90,  # seconds
                    "recovery_success_rate": 0.90
                },
                {
                    "error_type": "evaluation_timeout",
                    "context": "long_running_evaluation",
                    "expected_recovery_time": 120,  # seconds
                    "recovery_success_rate": 0.75
                }
            ],
            "error_ux_benchmarks": {
                "error_comprehension_rate": 0.80,      # 80% understand error messages
                "recovery_success_rate": 0.75,         # 75% recover successfully
                "error_prevention_effectiveness": 0.70,  # 70% of preventable errors avoided
                "error_handling_satisfaction": 3.5     # out of 5.0
            }
        }
        
        # RED Phase: This will fail because error UX testing is not automated
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if UserAcceptanceTestManager is None:
                raise ImportError("UserAcceptanceTestManager not implemented")
            
            acceptance_manager = UserAcceptanceTestManager(session_id=self.test_session)
            error_ux_result = acceptance_manager.test_error_handling_user_experience(
                criteria=error_handling_criteria,
                error_scenarios=self.acceptance_test_data["error_test_scenarios"]
            )
            
            # Validate error handling UX acceptance criteria
            assert error_ux_result.error_comprehension_rate >= error_handling_criteria["error_ux_benchmarks"]["error_comprehension_rate"]
            assert error_ux_result.recovery_success_rate >= error_handling_criteria["error_ux_benchmarks"]["recovery_success_rate"]
            assert error_ux_result.satisfaction_score >= error_handling_criteria["error_ux_benchmarks"]["error_handling_satisfaction"]
        
        # Validate expected failure
        assert any([
            "UserAcceptanceTestManager not implemented" in str(exc_info.value),
            "test_error_handling_user_experience" in str(exc_info.value),
            "error ux testing" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_acceptance_functionality("error_handling_ux", {
            "missing_classes": ["UserAcceptanceTestManager", "ErrorHandlingUXTester"],
            "missing_methods": ["test_error_handling_user_experience", "measure_error_recovery_usability"],
            "required_acceptance_features": [
                "Error message clarity and helpfulness assessment",
                "Error recovery guidance effectiveness testing",
                "System state preservation during errors validation",
                "Error prevention effectiveness measurement",
                "Recovery success rate and user satisfaction tracking",
                "Critical error data protection validation"
            ],
            "error_handling_criteria": error_handling_criteria,
            "error_details": str(exc_info.value)
        })

    def test_performance_user_satisfaction(self):
        """
        Test user satisfaction with system performance and responsiveness
        
        RED Phase: This test MUST fail initially
        Expected failure: Performance satisfaction testing not implemented
        """
        # Arrange: Setup performance satisfaction test
        performance_satisfaction_criteria = {
            "performance_ux_requirements": {
                "response_time_satisfaction": {
                    "target_score": 4.0,  # out of 5.0
                    "measurement": "response_time_acceptability_rating",
                    "success_criteria": "users_satisfied_with_system_responsiveness"
                },
                "loading_feedback_clarity": {
                    "target_score": 4.2,  # out of 5.0
                    "measurement": "loading_state_understanding_rate",
                    "success_criteria": "users_understand_system_progress_clearly"
                },
                "overall_performance_satisfaction": {
                    "target_score": 4.1,  # out of 5.0
                    "measurement": "performance_satisfaction_survey",
                    "success_criteria": "users_satisfied_with_overall_performance"
                }
            }
        }
        
        # RED Phase: This will fail because performance satisfaction testing is not implemented
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if UserAcceptanceTestManager is None:
                raise ImportError("UserAcceptanceTestManager not implemented")
            
            acceptance_manager = UserAcceptanceTestManager(session_id=self.test_session)
            performance_satisfaction_result = acceptance_manager.test_performance_user_satisfaction(
                criteria=performance_satisfaction_criteria
            )
        
        # Validate expected failure
        assert "not implemented" in str(exc_info.value).lower()
        
        self._document_missing_acceptance_functionality("performance_user_satisfaction", {
            "missing_classes": ["UserAcceptanceTestManager", "PerformanceSatisfactionTester"],
            "missing_methods": ["test_performance_user_satisfaction", "measure_performance_ux"],
            "required_acceptance_features": [
                "System response time user satisfaction measurement",
                "Loading state and progress feedback effectiveness testing",
                "Overall performance satisfaction survey and analysis",
                "Performance expectation vs reality gap analysis",
                "Performance improvement impact on user satisfaction tracking"
            ],
            "error_details": str(exc_info.value)
        })

    def _document_missing_acceptance_functionality(self, acceptance_area: str, missing_info: Dict[str, Any]) -> None:
        """Document missing user acceptance functionality for implementation guidance."""
        documentation = {
            "acceptance_area": acceptance_area,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "missing_functionality": missing_info,
            "user_acceptance_requirements": {
                "usability": "intuitive_and_efficient_user_interface_design",
                "satisfaction": "high_user_satisfaction_across_all_workflows",
                "effectiveness": "users_achieve_goals_efficiently_and_accurately",
                "learnability": "new_users_become_productive_quickly",
                "accessibility": "interface_accessible_to_users_with_disabilities"
            },
            "implementation_guidance": {
                "priority": "high",
                "tdd_phase": "RED",
                "acceptance_focus": [
                    "User task completion efficiency and success rate",
                    "User satisfaction and confidence measurement",
                    "Interface usability and intuitiveness validation",
                    "Error handling and recovery user experience",
                    "Performance impact on user satisfaction"
                ]
            }
        }
        
        # Write documentation to acceptance results directory
        doc_file = self.acceptance_results_dir / f"{acceptance_area}_missing_functionality.json"
        with open(doc_file, "w") as f:
            json.dump(documentation, f, indent=2)
        
        print(f"\n[TDD RED PHASE] Missing acceptance functionality documented for {acceptance_area}")
        print(f"Documentation saved to: {doc_file}")
        print(f"Key missing acceptance features: {missing_info.get('required_acceptance_features', [])[:3]}")


class TestUsabilityMetrics:
    """
    Test usability metrics collection and analysis across the platform.
    """
    
    def test_task_completion_rate_measurement(self):
        """
        Test automated task completion rate measurement
        
        RED Phase: This test MUST fail initially
        Expected failure: Task completion tracking not implemented
        """
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            from violentutf_api.fastapi_app.app.services.usability_metrics import TaskCompletionTracker
            
            completion_tracker = TaskCompletionTracker()
            completion_rates = completion_tracker.measure_task_completion_rates()
            
        assert "not implemented" in str(exc_info.value).lower()

    def test_user_satisfaction_scoring(self):
        """
        Test user satisfaction scoring and feedback collection
        
        RED Phase: This test MUST fail initially
        Expected failure: User satisfaction measurement not implemented
        """
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            from violentutf_api.fastapi_app.app.services.satisfaction_scoring import UserSatisfactionScorer
            
            satisfaction_scorer = UserSatisfactionScorer()
            satisfaction_scores = satisfaction_scorer.collect_and_analyze_satisfaction()
            
        assert "not implemented" in str(exc_info.value).lower()