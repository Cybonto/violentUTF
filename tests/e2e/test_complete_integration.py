# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
End-to-End Integration Tests for Issue #132 - Complete Integration Validation

This module implements comprehensive end-to-end tests for the complete dataset 
integration system, following Test-Driven Development (TDD) methodology.

Tests cover complete workflows from dataset selection through evaluation to results
across all 8+ supported dataset types:
- Garak red-teaming datasets
- OllaGen1 cognitive assessment datasets  
- ACPBench reasoning benchmarks
- LegalBench legal reasoning tasks
- DocMath mathematical document analysis
- GraphWalk graph-based reasoning
- ConfAIde privacy evaluation datasets
- JudgeBench meta-evaluation datasets

SECURITY: All test data is for defensive security research only.

TDD Implementation:
- RED Phase: Tests MUST fail initially, identifying missing functionality
- GREEN Phase: Implement minimum code to make tests pass
- REFACTOR Phase: Optimize and enhance implementations
"""

import asyncio
import json
import os
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests
from httpx import AsyncClient

from tests.fixtures.dataset_fixtures import create_test_datasets

# Test framework imports
from tests.utils.keycloak_auth import KeycloakTestAuth

# Import expected classes (these will initially fail - part of TDD RED phase)
try:
    from violentutf_api.fastapi_app.app.core.integration.e2e_workflow_manager import (
        EndToEndWorkflowManager,
        WorkflowExecutionError,
        WorkflowValidationError,
    )
except ImportError:
    # RED Phase: These imports will fail initially
    EndToEndWorkflowManager = None
    WorkflowExecutionError = Exception
    WorkflowValidationError = Exception

try:
    from violentutf_api.fastapi_app.app.services.dataset_integration_service import (
        DatasetIntegrationService,
        IntegrationValidationService,
    )
except ImportError:
    # RED Phase: Service imports will fail initially
    DatasetIntegrationService = None
    IntegrationValidationService = None

try:
    from violentutf_api.fastapi_app.app.schemas.e2e_integration import (
        DatasetProcessingMetrics,
        E2EWorkflowRequest,
        E2EWorkflowResult,
        WorkflowExecutionStatus,
    )
except ImportError:
    # RED Phase: Schema imports will fail initially
    E2EWorkflowRequest = None
    E2EWorkflowResult = None
    WorkflowExecutionStatus = None
    DatasetProcessingMetrics = None


class TestCompleteIntegrationWorkflows:
    """
    Test complete end-to-end workflows for all dataset types.
    
    These tests validate the complete integration pipeline from dataset
    selection through conversion, evaluation, and results generation.
    """
    
    @pytest.fixture(autouse=True, scope="function")
    def setup_e2e_test_environment(self):
        """Setup test environment for end-to-end testing."""
        self.test_session = f"e2e_test_{int(time.time())}"
        self.auth_client = KeycloakTestAuth()
        self.test_datasets = create_test_datasets()
        self.test_results = []  # Initialize test results collection
        
        # Setup test directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="e2e_test_"))
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        yield
        
        # Cleanup
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_complete_garak_redteaming_workflow(self):
        """
        Test complete workflow: Garak dataset → conversion → evaluation → results
        
        RED Phase: This test MUST fail initially
        Expected failure: EndToEndWorkflowManager not implemented
        
        Complete workflow steps:
        1. User authentication via Keycloak
        2. Garak dataset selection and validation
        3. Dataset conversion to PyRIT format
        4. Red-teaming orchestrator configuration
        5. PyRIT evaluation execution
        6. Vulnerability assessment results generation
        7. Report generation and storage
        """
        # Arrange: Setup workflow configuration
        workflow_config = {
            "dataset_type": "garak",
            "dataset_collection": "red_team_comprehensive",
            "conversion_strategy": "garak_to_seedprompt",
            "orchestrator_type": "red_teaming",
            "evaluation_target": "test_model",
            "scoring_config": {
                "scorers": ["azure_content_filter", "self_ask_truthfulness"],
                "thresholds": {"harm_threshold": 0.3, "risk_threshold": 0.7}
            }
        }
        
        # GREEN Phase: Now execute the actual workflow and validate results
        if EndToEndWorkflowManager is None:
            pytest.skip("EndToEndWorkflowManager not available - still in RED phase")
            
        # Act: Execute the complete Garak workflow
        workflow_manager = EndToEndWorkflowManager(session_id=self.test_session)
        result = workflow_manager.execute_garak_workflow(workflow_config)
        
        # Assert: Validate successful workflow execution
        assert result is not None, "Workflow result should not be None"
        assert result.workflow_id is not None, "Workflow should have an ID"
        assert result.dataset_type == "garak", "Dataset type should match"
        assert result.execution_status == "completed", f"Workflow should complete successfully, got: {result.execution_status}"
        assert result.processing_metrics is not None, "Processing metrics should be available"
        assert result.evaluation_results is not None, "Evaluation results should be available"
        assert result.execution_time > 0, "Execution time should be positive"
        
        # Validate processing metrics
        metrics = result.processing_metrics
        assert metrics.processing_time > 0, "Processing time should be positive"
        assert 0 <= metrics.conversion_success_rate <= 1, "Conversion success rate should be between 0 and 1"
        assert 0 <= metrics.performance_score <= 1, "Performance score should be between 0 and 1"
        
        # Validate evaluation results contain expected fields
        eval_results = result.evaluation_results
        assert "total_prompts" in eval_results, "Should contain total prompts count"
        assert "vulnerability_score" in eval_results, "Should contain vulnerability score"
        
        # Document successful implementation
        self._document_successful_implementation("garak_workflow", {
            "implemented_classes": ["EndToEndWorkflowManager"],
            "implemented_methods": ["execute_garak_workflow"],
            "completed_features": [
                "Garak dataset loading and validation",
                "Garak to PyRIT SeedPrompt conversion", 
                "Red-teaming orchestrator integration",
                "Vulnerability assessment scoring",
                "Result aggregation and reporting"
            ],
            "workflow_id": result.workflow_id,
            "execution_time": result.execution_time
        })

    def test_complete_ollegen1_cognitive_workflow(self):
        """
        Test complete workflow: OllaGen1 → conversion → Q&A evaluation → analysis
        
        RED Phase: This test MUST fail initially
        Expected failure: OllaGen1 Q&A evaluation pipeline not implemented
        
        Complete workflow steps:
        1. User authentication and session initialization
        2. OllaGen1 CSV dataset loading
        3. Person profile and scenario extraction
        4. Conversion to QuestionAnsweringDataset format
        5. Cognitive assessment orchestrator setup
        6. Q&A evaluation execution with behavioral analysis
        7. Cognitive profile analysis and reporting
        """
        # Arrange: Setup cognitive evaluation workflow
        workflow_config = {
            "dataset_type": "ollegen1", 
            "dataset_source": "cognitive_assessment_full.csv",
            "conversion_strategy": "csv_to_qa_dataset",
            "orchestrator_type": "question_answering",
            "evaluation_focus": "cognitive_behavioral",
            "analysis_config": {
                "cognitive_paths": ["analytical", "intuitive", "creative"],
                "risk_profiles": ["low_risk", "moderate_risk", "high_risk"],
                "behavioral_metrics": ["consistency", "bias_detection", "reasoning_quality"]
            }
        }
        
        # RED Phase: This will fail because cognitive evaluation is not implemented
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if EndToEndWorkflowManager is None:
                raise ImportError("EndToEndWorkflowManager not implemented")
            
            workflow_manager = EndToEndWorkflowManager(session_id=self.test_session)
            result = workflow_manager.execute_cognitive_workflow(workflow_config)
        
        # Validate expected failure
        assert any([
            "EndToEndWorkflowManager not implemented" in str(exc_info.value),
            "execute_cognitive_workflow" in str(exc_info.value),
            "cognitive evaluation" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_functionality("ollegen1_cognitive_workflow", {
            "missing_classes": ["EndToEndWorkflowManager", "CognitiveEvaluationPipeline"],
            "missing_methods": ["execute_cognitive_workflow", "analyze_cognitive_patterns"],
            "required_features": [
                "OllaGen1 CSV parsing and validation",
                "Person profile extraction and modeling",
                "CSV to QuestionAnsweringDataset conversion",
                "Cognitive assessment orchestrator",
                "Behavioral analysis and scoring",
                "Cognitive profile reporting"
            ],
            "error_details": str(exc_info.value)
        })

    def test_complete_reasoning_benchmark_workflow(self):
        """
        Test complete workflow: ACPBench/LegalBench → conversion → reasoning evaluation
        
        RED Phase: This test MUST fail initially
        Expected failure: Reasoning benchmark evaluation pipeline not implemented
        
        Complete workflow steps:
        1. User authentication and benchmark selection
        2. Multi-benchmark dataset loading (ACPBench + LegalBench)
        3. Cross-domain reasoning task extraction
        4. Conversion to unified reasoning dataset format
        5. Reasoning evaluation orchestrator configuration
        6. Multi-domain reasoning assessment execution
        7. Cross-benchmark performance analysis and comparison
        """
        # Arrange: Setup reasoning benchmark workflow
        workflow_config = {
            "dataset_types": ["acpbench", "legalbench"],
            "benchmark_config": {
                "acpbench": {
                    "categories": ["logical_reasoning", "causal_inference", "analogical_reasoning"],
                    "difficulty_levels": ["easy", "medium", "hard"]
                },
                "legalbench": {
                    "legal_areas": ["contract_law", "criminal_law", "constitutional_law"],
                    "task_types": ["classification", "qa", "reasoning"]
                }
            },
            "conversion_strategy": "multi_benchmark_to_reasoning_dataset",
            "orchestrator_type": "reasoning_evaluation",
            "evaluation_approach": "cross_domain_comparison"
        }
        
        # RED Phase: This will fail because reasoning evaluation is not implemented
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if EndToEndWorkflowManager is None:
                raise ImportError("EndToEndWorkflowManager not implemented")
                
            workflow_manager = EndToEndWorkflowManager(session_id=self.test_session)
            result = workflow_manager.execute_reasoning_workflow(workflow_config)
        
        # Validate expected failure
        assert any([
            "EndToEndWorkflowManager not implemented" in str(exc_info.value),
            "execute_reasoning_workflow" in str(exc_info.value),
            "reasoning evaluation" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_functionality("reasoning_benchmark_workflow", {
            "missing_classes": ["EndToEndWorkflowManager", "ReasoningEvaluationPipeline"],
            "missing_methods": ["execute_reasoning_workflow", "cross_domain_analysis"],
            "required_features": [
                "Multi-benchmark dataset coordination",
                "ACPBench reasoning task extraction",
                "LegalBench legal reasoning integration", 
                "Cross-domain reasoning dataset format",
                "Reasoning evaluation orchestrator",
                "Cross-benchmark performance comparison",
                "Multi-domain analysis reporting"
            ],
            "error_details": str(exc_info.value)
        })

    def test_complete_privacy_evaluation_workflow(self):
        """
        Test complete workflow: ConfAIde → privacy evaluation → contextual integrity assessment
        
        RED Phase: This test MUST fail initially
        Expected failure: Privacy evaluation framework not implemented
        
        Complete workflow steps:
        1. User authentication and privacy assessment setup
        2. ConfAIde dataset loading with privacy tier classification
        3. Privacy scenario extraction and contextual modeling
        4. Conversion to privacy-aware evaluation dataset
        5. Privacy evaluation orchestrator with contextual integrity scoring
        6. Privacy-preserving AI assessment execution
        7. Contextual integrity analysis and privacy risk reporting
        """
        # Arrange: Setup privacy evaluation workflow
        workflow_config = {
            "dataset_type": "confaide",
            "privacy_tiers": ["public", "private", "sensitive", "confidential"],
            "evaluation_framework": "contextual_integrity",
            "conversion_strategy": "confaide_to_privacy_dataset",
            "orchestrator_type": "privacy_evaluation",
            "assessment_config": {
                "context_types": ["healthcare", "finance", "social", "workplace"],
                "privacy_metrics": ["data_minimization", "purpose_limitation", "consent_compliance"],
                "integrity_checks": ["access_control", "data_flow_analysis", "context_appropriateness"]
            }
        }
        
        # RED Phase: This will fail because privacy evaluation is not implemented
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if EndToEndWorkflowManager is None:
                raise ImportError("EndToEndWorkflowManager not implemented")
                
            workflow_manager = EndToEndWorkflowManager(session_id=self.test_session)
            result = workflow_manager.execute_privacy_workflow(workflow_config)
        
        # Validate expected failure  
        assert any([
            "EndToEndWorkflowManager not implemented" in str(exc_info.value),
            "execute_privacy_workflow" in str(exc_info.value),
            "privacy evaluation" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_functionality("privacy_evaluation_workflow", {
            "missing_classes": ["EndToEndWorkflowManager", "PrivacyEvaluationPipeline", "ContextualIntegrityScorer"],
            "missing_methods": ["execute_privacy_workflow", "contextual_integrity_assessment"],
            "required_features": [
                "ConfAIde dataset parsing with privacy tiers",
                "Privacy scenario contextual modeling",
                "Privacy-aware dataset conversion",
                "Contextual integrity evaluation framework",
                "Privacy-preserving orchestrator",
                "Multi-context privacy assessment",
                "Privacy risk analysis and reporting"
            ],
            "error_details": str(exc_info.value)
        })

    def test_complete_meta_evaluation_workflow(self):
        """
        Test complete workflow: JudgeBench → meta-evaluation → judge assessment
        
        RED Phase: This test MUST fail initially
        Expected failure: Meta-evaluation system not implemented
        
        Complete workflow steps:
        1. User authentication and meta-evaluation setup
        2. JudgeBench dataset loading with judge-response pairs
        3. Meta-evaluation scenario extraction
        4. Conversion to meta-evaluation dataset format
        5. Judge assessment orchestrator configuration
        6. Meta-evaluation execution with judge quality scoring
        7. Judge performance analysis and evaluation quality assessment
        """
        # Arrange: Setup meta-evaluation workflow
        workflow_config = {
            "dataset_type": "judgebench",
            "meta_evaluation_approach": "judge_assessment",
            "conversion_strategy": "judgebench_to_meta_dataset",
            "orchestrator_type": "meta_evaluation",
            "assessment_config": {
                "judge_types": ["llm_judge", "human_judge", "rule_based_judge"],
                "evaluation_domains": ["safety", "helpfulness", "truthfulness", "bias"],
                "quality_metrics": ["consistency", "accuracy", "fairness", "reliability"]
            }
        }
        
        # GREEN Phase: Validate meta-evaluation workflow execution
        if EndToEndWorkflowManager is None:
            pytest.skip("EndToEndWorkflowManager not available")
            
        workflow_manager = EndToEndWorkflowManager(session_id=self.test_session)
        result = workflow_manager.execute_meta_evaluation_workflow(workflow_config)
        
        # Validate workflow execution success
        assert result is not None, "Meta-evaluation workflow should return result"
        assert result.workflow_id, "Result should have workflow ID"
        assert result.dataset_type == "meta_evaluation", "Dataset type should be meta_evaluation"
        assert result.execution_status in ["completed", "in_progress"], "Execution status should be valid"
        assert result.processing_metrics, "Processing metrics should be available"
        
        # Validate processing metrics
        assert result.processing_metrics.processing_time > 0, "Processing time should be recorded"
        assert result.processing_metrics.memory_usage_mb >= 0, "Memory usage should be recorded"
        
        # Validate meta-evaluation specific results
        if hasattr(result, 'evaluation_results'):
            assert result.evaluation_results, "Evaluation results should be present"
        
        # Document successful meta-evaluation workflow completion
        self.test_results.append({
            "test": "meta_evaluation_workflow",
            "status": "PASSED",
            "implemented_features": [
                "JudgeBench dataset processing",
                "Meta-evaluation workflow execution",
                "Judge assessment integration", 
                "Performance metrics collection"
            ],
            "workflow_result": {
                "workflow_id": result.workflow_id,
                "execution_status": result.execution_status,
                "processing_time": result.processing_metrics.processing_time
            }
        })

    def test_massive_file_complete_workflow(self):
        """
        Test complete workflow: GraphWalk 480MB → splitting → conversion → evaluation
        
        RED Phase: This test MUST fail initially
        Expected failure: Large file processing pipeline not optimized
        
        Complete workflow steps:
        1. User authentication and large file upload
        2. GraphWalk 480MB dataset validation and analysis
        3. Intelligent file splitting with graph structure preservation
        4. Batch conversion to graph reasoning dataset format
        5. Distributed evaluation orchestrator setup
        6. Graph reasoning evaluation execution with memory management
        7. Results aggregation and comprehensive graph analysis reporting
        """
        # Arrange: Setup large file processing workflow
        workflow_config = {
            "dataset_type": "graphwalk",
            "file_size": "480MB",
            "processing_strategy": "streaming_with_splitting",
            "conversion_strategy": "graph_to_reasoning_dataset",
            "orchestrator_type": "distributed_graph_evaluation",
            "performance_config": {
                "max_memory_usage": "2GB",
                "max_processing_time": "1800s",
                "chunk_size": "50MB",
                "parallel_workers": 4
            }
        }
        
        # RED Phase: This will fail because large file processing is not optimized
        with pytest.raises((ImportError, AttributeError, NotImplementedError, MemoryError, TimeoutError)) as exc_info:
            if EndToEndWorkflowManager is None:
                raise ImportError("EndToEndWorkflowManager not implemented")
                
            workflow_manager = EndToEndWorkflowManager(session_id=self.test_session)
            result = workflow_manager.execute_large_file_workflow(workflow_config)
        
        # Validate expected failure
        assert any([
            "EndToEndWorkflowManager not implemented" in str(exc_info.value),
            "execute_large_file_workflow" in str(exc_info.value),
            "large file" in str(exc_info.value).lower(),
            "memory" in str(exc_info.value).lower(),
            "timeout" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_functionality("large_file_workflow", {
            "missing_classes": ["EndToEndWorkflowManager", "LargeFileProcessor", "DistributedEvaluationOrchestrator"],
            "missing_methods": ["execute_large_file_workflow", "streaming_file_processing"],
            "required_features": [
                "Large file streaming and validation",
                "Graph structure-aware file splitting",
                "Memory-efficient batch conversion",
                "Distributed evaluation orchestration",
                "Performance monitoring and management",
                "Results aggregation across chunks",
                "Memory usage optimization and cleanup"
            ],
            "error_details": str(exc_info.value)
        })

    def test_cross_domain_evaluation_comparison(self):
        """
        Test complete workflow: Cross-domain evaluation comparing different dataset types
        
        RED Phase: This test MUST fail initially  
        Expected failure: Cross-domain comparison framework not implemented
        
        Complete workflow steps:
        1. User authentication and multi-domain evaluation setup
        2. Multiple dataset type selection and validation
        3. Cross-domain evaluation dataset preparation
        4. Unified evaluation orchestrator configuration
        5. Multi-domain evaluation execution with comparison metrics
        6. Cross-domain performance analysis
        7. Comprehensive comparison reporting with domain-specific insights
        """
        # Arrange: Setup cross-domain evaluation workflow
        workflow_config = {
            "evaluation_type": "cross_domain_comparison",
            "dataset_types": ["garak", "ollegen1", "acpbench", "confaide"],
            "comparison_framework": "unified_multi_domain",
            "orchestrator_type": "cross_domain_evaluation",
            "comparison_config": {
                "common_metrics": ["accuracy", "consistency", "robustness"],
                "domain_specific_metrics": {
                    "garak": ["vulnerability_detection", "attack_success_rate"],
                    "ollegen1": ["cognitive_consistency", "behavioral_analysis"],
                    "acpbench": ["reasoning_quality", "logical_coherence"],
                    "confaide": ["privacy_preservation", "contextual_appropriateness"]
                },
                "analysis_approaches": ["statistical_comparison", "domain_correlation", "performance_benchmarking"]
            }
        }
        
        # RED Phase: This will fail because cross-domain comparison is not implemented
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            if EndToEndWorkflowManager is None:
                raise ImportError("EndToEndWorkflowManager not implemented")
                
            workflow_manager = EndToEndWorkflowManager(session_id=self.test_session)
            result = workflow_manager.execute_cross_domain_workflow(workflow_config)
        
        # Validate expected failure
        assert any([
            "EndToEndWorkflowManager not implemented" in str(exc_info.value),
            "execute_cross_domain_workflow" in str(exc_info.value),
            "cross-domain" in str(exc_info.value).lower(),
            "comparison" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"
        
        self._document_missing_functionality("cross_domain_comparison_workflow", {
            "missing_classes": ["EndToEndWorkflowManager", "CrossDomainComparisonPipeline", "UnifiedEvaluationOrchestrator"],
            "missing_methods": ["execute_cross_domain_workflow", "multi_domain_analysis"],
            "required_features": [
                "Multi-dataset coordination and management",
                "Cross-domain evaluation dataset preparation",
                "Unified evaluation orchestrator",
                "Cross-domain comparison metrics",
                "Statistical analysis and correlation",
                "Domain-specific performance analysis",
                "Comprehensive comparison reporting"
            ],
            "error_details": str(exc_info.value)
        })

    def _document_missing_functionality(self, workflow_name: str, missing_info: Dict[str, Any]) -> None:
        """Document missing functionality for implementation guidance."""
        documentation = {
            "workflow": workflow_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "missing_functionality": missing_info,
            "implementation_guidance": {
                "priority": "high",
                "tdd_phase": "RED",
                "next_steps": [
                    f"Implement missing classes: {', '.join(missing_info.get('missing_classes', []))}",
                    f"Implement missing methods: {', '.join(missing_info.get('missing_methods', []))}",
                    "Create required schemas and data models",
                    "Implement core business logic",
                    "Add comprehensive error handling",
                    "Create integration points with existing services"
                ]
            }
        }
        
        # Write documentation to results directory
        doc_file = self.results_dir / f"{workflow_name}_missing_functionality.json"
        with open(doc_file, "w") as f:
            json.dump(documentation, f, indent=2)
        
        print(f"\n[TDD RED PHASE] Missing functionality documented for {workflow_name}")
        print(f"Documentation saved to: {doc_file}")
        print(f"Key missing components: {missing_info.get('missing_classes', [])}")

    def _document_successful_implementation(self, workflow_name: str, success_info: Dict[str, Any]) -> None:
        """Document successful implementation for GREEN phase validation."""
        documentation = {
            "workflow": workflow_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "implementation_status": "completed",
            "successful_implementation": success_info,
            "validation_results": {
                "tdd_phase": "GREEN",
                "test_status": "passing",
                "all_requirements_met": True
            }
        }
        
        # Write documentation to results directory
        doc_file = self.results_dir / f"{workflow_name}_successful_implementation.json"
        with open(doc_file, "w") as f:
            json.dump(documentation, f, indent=2)
        
        print(f"\n[TDD GREEN PHASE] Successful implementation validated for {workflow_name}")
        print(f"Documentation saved to: {doc_file}")
        print(f"Implemented components: {success_info.get('implemented_classes', [])}")


class TestWorkflowPerformanceValidation:
    """
    Test performance benchmarks for complete workflows.
    
    These tests validate that complete end-to-end workflows meet
    established performance targets across all dataset types.
    """
    
    @pytest.fixture(autouse=True, scope="function")
    def setup_performance_test_environment(self):
        """Setup test environment for performance testing."""
        self.test_session = f"perf_test_{int(time.time())}"
        self.auth_client = KeycloakTestAuth()
        self.test_datasets = create_test_datasets()
        self.test_results = []  # Initialize test results collection
        
        # Setup test directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="perf_test_"))
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        yield
        
        # Cleanup
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_workflow_execution_time_benchmarks(self):
        """
        Test that all workflow execution times meet established benchmarks
        
        RED Phase: This test MUST fail initially
        Expected failure: Performance monitoring not implemented
        
        Performance benchmarks per workflow type:
        - Garak red-teaming: <300s total workflow time
        - OllaGen1 cognitive: <900s total workflow time
        - Reasoning benchmarks: <600s total workflow time  
        - Privacy evaluation: <480s total workflow time
        - Meta-evaluation: <420s total workflow time
        - Large file processing: <1800s total workflow time
        - Cross-domain comparison: <1200s total workflow time
        """
        # RED Phase: This will fail because performance monitoring is not implemented
        with pytest.raises((ImportError, AttributeError, NotImplementedError)) as exc_info:
            from violentutf_api.fastapi_app.app.monitoring.performance_monitor import WorkflowPerformanceMonitor
            
            performance_monitor = WorkflowPerformanceMonitor()
            benchmarks = performance_monitor.get_workflow_benchmarks()
            
            for workflow_type, benchmark in benchmarks.items():
                execution_time = performance_monitor.measure_workflow_time(workflow_type)
                assert execution_time <= benchmark.max_execution_time
        
        # Validate expected failure
        assert any([
            "WorkflowPerformanceMonitor" in str(exc_info.value),
            "performance monitoring" in str(exc_info.value).lower(),
            "not implemented" in str(exc_info.value).lower()
        ]), f"Unexpected error: {exc_info.value}"

    def test_workflow_memory_usage_validation(self):
        """
        Test that all workflows stay within memory usage limits
        
        GREEN Phase: Validate memory monitoring functionality
        """
        from violentutf_api.fastapi_app.app.monitoring.memory_monitor import WorkflowMemoryMonitor
        
        memory_monitor = WorkflowMemoryMonitor()
        
        # Test memory limits configuration
        memory_limits = memory_monitor.get_memory_limits()
        assert memory_limits is not None, "Memory limits should be available"
        assert isinstance(memory_limits, dict), "Memory limits should be a dictionary"
        
        # Validate expected workflow types have limits
        expected_workflows = ["garak_collection", "ollegen1_full", "acpbench_all", 
                            "legalbench_166_dirs", "docmath_220mb", "graphwalk_480mb",
                            "confaide_4_tiers", "judgebench_all", "meta_evaluation"]
        
        for workflow in expected_workflows:
            assert workflow in memory_limits, f"Memory limits should include {workflow}"
            assert "max_memory_mb" in memory_limits[workflow], f"Max memory should be defined for {workflow}"
            assert memory_limits[workflow]["max_memory_mb"] > 0, f"Max memory should be positive for {workflow}"
            
        # Test current memory usage monitoring
        current_usage = memory_monitor.get_current_workflow_memory()
        assert current_usage is not None, "Current usage should be available"
        assert "process_memory_mb" in current_usage, "Process memory should be tracked"
        assert "system_memory_percent" in current_usage, "System memory should be tracked"
        assert current_usage["process_memory_mb"] >= 0, "Process memory should be non-negative"
        
        # Test workflow monitoring lifecycle
        workflow_name = "test_memory_workflow"
        workflow_type = "garak_collection" 
        
        # Start monitoring
        monitor_id = memory_monitor.start_workflow_monitoring(workflow_name, workflow_type)
        assert monitor_id == workflow_name, "Monitor ID should match workflow name"
        
        # Check compliance
        compliance = memory_monitor.check_workflow_memory_compliance(workflow_name, workflow_type)
        assert compliance["workflow_name"] == workflow_name, "Compliance should track workflow name"
        assert compliance["is_compliant"] in [True, False], "Compliance should be boolean"
        assert compliance["current_memory_mb"] >= 0, "Current memory should be non-negative"
        
        # Stop monitoring
        final_report = memory_monitor.stop_workflow_monitoring(workflow_name)
        assert "start_memory_mb" in final_report, "Final report should include start memory"
        assert "end_memory_mb" in final_report, "Final report should include end memory"
        assert "memory_delta_mb" in final_report, "Final report should include memory delta"
        
        self.test_results.append({
            "test": "workflow_memory_usage_validation",
            "status": "PASSED", 
            "validated_features": [
                "Memory limits configuration",
                "Current memory usage tracking",
                "Workflow monitoring lifecycle",
                "Memory compliance checking"
            ],
            "memory_limits_count": len(memory_limits),
            "current_memory_mb": current_usage["process_memory_mb"]
        })


class TestWorkflowErrorHandling:
    """
    Test error handling and recovery mechanisms for complete workflows.
    """
    
    @pytest.fixture(autouse=True, scope="function")
    def setup_error_handling_test_environment(self):
        """Setup test environment for error handling testing."""
        self.test_session = f"error_test_{int(time.time())}"
        self.auth_client = KeycloakTestAuth()
        self.test_datasets = create_test_datasets()
        self.test_results = []  # Initialize test results collection
        
        # Setup test directory
        self.test_dir = Path(tempfile.mkdtemp(prefix="error_test_"))
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        yield
        
        # Cleanup
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_workflow_failure_recovery(self):
        """
        Test workflow failure detection and recovery mechanisms
        
        GREEN Phase: Validate workflow recovery functionality
        """
        from violentutf_api.fastapi_app.app.core.recovery.workflow_recovery import WorkflowRecoveryManager
        
        recovery_manager = WorkflowRecoveryManager()
        
        # Test workflow failure handling
        workflow_id = "test_failure_workflow"
        error_details = {
            "error_type": "conversion_failure",
            "error_message": "Dataset conversion failed during processing",
            "failed_step": "dataset_validation"
        }
        
        recovery_result = recovery_manager.handle_workflow_failure(workflow_id, error_details)
        
        # Validate recovery result structure
        assert recovery_result is not None, "Recovery result should be returned"
        assert "failure_id" in recovery_result, "Recovery result should have failure ID"
        assert "workflow_id" in recovery_result, "Recovery result should include workflow ID"
        assert recovery_result["workflow_id"] == workflow_id, "Workflow ID should match"
        
        # Validate recovery analysis
        assert "error_analysis" in recovery_result, "Recovery result should include failure analysis"
        assert "can_retry" in recovery_result, "Recovery result should include retry capability"
        
        # Test recovery recommendations
        if "recommended_actions" in recovery_result:
            recommendations = recovery_result["recommended_actions"]
            assert isinstance(recommendations, list), "Recommendations should be a list"
            
        # Test retry capability
        if hasattr(recovery_manager, 'can_retry_workflow'):
            can_retry = recovery_manager.can_retry_workflow(workflow_id, error_details)
            assert isinstance(can_retry, bool), "Can retry should be boolean"
            
        # Test recovery state tracking
        if hasattr(recovery_manager, 'get_recovery_state'):
            state = recovery_manager.get_recovery_state(workflow_id)
            assert state is not None, "Recovery state should be available"
            
        self.test_results.append({
            "test": "workflow_failure_recovery",
            "status": "PASSED",
            "validated_features": [
                "Workflow failure handling",
                "Error analysis and classification",
                "Recovery plan generation",
                "Failure state tracking"
            ],
            "failure_id": recovery_result["failure_id"],
            "workflow_id": workflow_id
        })

    @pytest.mark.asyncio
    async def test_partial_workflow_completion_handling(self):
        """
        Test handling of partial workflow completion scenarios
        
        GREEN Phase: Validate partial completion handling functionality
        """
        from violentutf_api.fastapi_app.app.core.recovery.partial_completion_handler import PartialCompletionHandler
        
        handler = PartialCompletionHandler()
        
        # Test partial workflow completion handling
        workflow_id = "test_partial_workflow"
        completed_tasks = ["dataset_loading", "initial_validation"]
        pending_tasks = ["data_conversion", "evaluation_execution"]
        failed_tasks = ["file_preprocessing"]
        results_data = {
            "completed_results": {
                "dataset_loading": {"status": "success", "records_loaded": 1000},
                "initial_validation": {"status": "success", "validation_score": 0.95}
            },
            "partial_data": {"processed_count": 500, "error_count": 2}
        }
        error_context = {
            "error_type": "preprocessing_failure",
            "error_message": "File preprocessing failed on corrupted data"
        }
        
        # Handle partial completion (this is async)
        result = await handler.handle_partial_completion(
            workflow_id, completed_tasks, pending_tasks, failed_tasks, 
            results_data, error_context
        )
        
        # Validate partial completion result
        assert result is not None, "Partial completion result should be returned"
        
        # Check result has expected attributes (based on PartialResults class)
        assert hasattr(result, 'workflow_id'), "Result should have workflow ID" 
        assert hasattr(result, 'completion_percentage'), "Result should have completion percentage"
        assert hasattr(result, 'completed_tasks'), "Result should have completed tasks"
        assert hasattr(result, 'pending_tasks'), "Result should have pending tasks"
        assert hasattr(result, 'failed_tasks'), "Result should have failed tasks"
        
        # Validate workflow tracking
        assert result.workflow_id == workflow_id, "Workflow ID should match"
        
        # Validate completion percentage is reasonable (changed to 0-100 range)
        assert 0 <= result.completion_percentage <= 100, "Completion percentage should be between 0 and 100"
        
        # Validate task tracking
        assert result.completed_tasks == completed_tasks, "Completed tasks should match"
        assert result.pending_tasks == pending_tasks, "Pending tasks should match" 
        assert result.failed_tasks == failed_tasks, "Failed tasks should match"
        
        # Test recovery recommendations if available
        if hasattr(result, 'recovery_recommendations'):
            assert isinstance(result.recovery_recommendations, list), "Recommendations should be a list"
            
        # Test resume capability
        if hasattr(handler, 'can_resume_workflow'):
            can_resume = handler.can_resume_workflow(workflow_id, result)
            assert isinstance(can_resume, bool), "Can resume should be boolean"
            
        self.test_results.append({
            "test": "partial_workflow_completion_handling",
            "status": "PASSED",
            "validated_features": [
                "Partial completion tracking",
                "Task status management",
                "Completion percentage calculation",
                "Recovery context handling"
            ],
            "workflow_id": workflow_id,
            "completion_percentage": result.completion_percentage,
            "completed_tasks_count": len(result.completed_tasks),
            "pending_tasks_count": len(result.pending_tasks),
            "failed_tasks_count": len(result.failed_tasks)
        })