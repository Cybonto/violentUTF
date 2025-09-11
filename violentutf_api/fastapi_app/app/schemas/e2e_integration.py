# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
E2E Integration Schema for Issue #132 - Complete Integration Validation

This module defines Pydantic schemas for end-to-end integration workflows,
supporting complete validation and monitoring across all dataset types.

GREEN Phase Implementation:
- Complete workflow request and response schemas
- Status tracking and monitoring schemas
- Performance metrics and validation schemas
- User workflow execution schemas

SECURITY: All schema operations are for defensive security research only.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowExecutionStatus(str, Enum):
    """Enumeration of workflow execution statuses."""

    INITIALIZING = "initializing"
    VALIDATING = "validating"
    LOADING = "loading"
    CONVERTING = "converting"
    ORCHESTRATING = "orchestrating"
    EVALUATING = "evaluating"
    GENERATING_RESULTS = "generating_results"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DatasetProcessingMetrics(BaseModel):
    """Metrics for dataset processing operations."""

    processing_time: float = Field(description="Total processing time in seconds")
    memory_usage_mb: float = Field(description="Peak memory usage in MB")
    conversion_success_rate: float = Field(ge=0.0, le=1.0, description="Successful conversion rate (0.0 to 1.0)")
    validation_errors: List[str] = Field(default=[], description="Validation errors encountered")
    performance_score: float = Field(ge=0.0, le=1.0, description="Overall performance score (0.0 to 1.0)")
    dataset_items_processed: int = Field(default=0, description="Number of dataset items processed")
    successful_conversions: int = Field(default=0, description="Number of successful conversions")
    failed_conversions: int = Field(default=0, description="Number of failed conversions")


class WorkflowExecutionStatusModel(BaseModel):
    """Status tracking for workflow execution."""

    workflow_id: str = Field(description="Unique workflow identifier")
    status: WorkflowExecutionStatus = Field(description="Current workflow status")
    progress_percentage: float = Field(ge=0.0, le=100.0, description="Execution progress percentage (0-100)")
    current_step: str = Field(description="Current execution step")
    steps_completed: List[str] = Field(default=[], description="Completed steps")
    steps_remaining: List[str] = Field(default=[], description="Remaining steps")
    estimated_completion_time: Optional[str] = Field(None, description="Estimated completion time (ISO format)")
    start_time: str = Field(description="Workflow start time (ISO format)")
    last_update_time: str = Field(description="Last status update time (ISO format)")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")
    metrics: Optional[DatasetProcessingMetrics] = Field(None, description="Processing metrics")


class E2EWorkflowRequest(BaseModel):
    """Request model for end-to-end workflow execution."""

    dataset_type: str = Field(description="Type of dataset to process")
    dataset_collection: str = Field(description="Dataset collection identifier")
    conversion_strategy: str = Field(description="Conversion strategy to use")
    orchestrator_type: str = Field(description="PyRIT orchestrator type")
    evaluation_target: str = Field(description="Evaluation target model")
    scoring_config: Dict[str, Any] = Field(description="Scoring configuration")
    user_context: Optional[Dict[str, Any]] = Field(None, description="User context information")
    workflow_options: Optional[Dict[str, Any]] = Field(None, description="Additional workflow options")
    notification_settings: Optional[Dict[str, str]] = Field(None, description="Notification preferences")


class E2EWorkflowResult(BaseModel):
    """Result model for end-to-end workflow execution."""

    workflow_id: str = Field(description="Workflow identifier")
    dataset_type: str = Field(description="Dataset type processed")
    execution_status: WorkflowExecutionStatus = Field(description="Final execution status")
    processing_metrics: DatasetProcessingMetrics = Field(description="Processing metrics")
    evaluation_results: Dict[str, Any] = Field(description="Evaluation results")
    generated_files: List[str] = Field(default=[], description="Generated file paths")
    report_urls: List[str] = Field(default=[], description="Generated report URLs")
    error_details: Optional[str] = Field(None, description="Error details if failed")
    execution_time: float = Field(description="Total execution time in seconds")
    timestamp: str = Field(description="Completion timestamp (ISO format)")
    quality_assessment: Optional[Dict[str, Any]] = Field(None, description="Quality assessment results")
    recommendations: List[str] = Field(default=[], description="Workflow recommendations")


class UserScenarioRequest(BaseModel):
    """Request model for user scenario execution."""

    persona_type: str = Field(description="User persona type")
    scenario_name: str = Field(description="Scenario name")
    dataset_selections: List[str] = Field(description="Selected datasets for scenario")
    evaluation_preferences: Dict[str, Any] = Field(description="User evaluation preferences")
    workflow_customizations: Optional[Dict[str, Any]] = Field(None, description="Workflow customizations")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_context: Optional[Dict[str, Any]] = Field(None, description="Session context")


class UserScenarioResult(BaseModel):
    """Result model for user scenario execution."""

    scenario_id: str = Field(description="Scenario execution identifier")
    persona_type: str = Field(description="User persona type")
    scenario_name: str = Field(description="Scenario name")
    execution_status: WorkflowExecutionStatus = Field(description="Scenario execution status")
    workflow_results: List[E2EWorkflowResult] = Field(description="Individual workflow results")
    scenario_metrics: Dict[str, Any] = Field(description="Scenario-level metrics")
    user_satisfaction_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="User satisfaction score")
    completion_time: float = Field(description="Total scenario completion time")
    timestamp: str = Field(description="Scenario completion timestamp")


class PerformanceBenchmark(BaseModel):
    """Performance benchmark definition and results."""

    benchmark_name: str = Field(description="Benchmark name")
    dataset_type: str = Field(description="Dataset type being benchmarked")
    target_processing_time: float = Field(description="Target processing time in seconds")
    target_memory_usage: float = Field(description="Target memory usage in MB")
    target_success_rate: float = Field(ge=0.0, le=1.0, description="Target success rate")
    actual_processing_time: Optional[float] = Field(None, description="Actual processing time")
    actual_memory_usage: Optional[float] = Field(None, description="Actual memory usage")
    actual_success_rate: Optional[float] = Field(None, description="Actual success rate")
    benchmark_passed: Optional[bool] = Field(None, description="Whether benchmark passed")
    performance_deviation: Optional[Dict[str, float]] = Field(None, description="Performance deviation from targets")


class SystemIntegrationTest(BaseModel):
    """System integration test definition and results."""

    test_name: str = Field(description="Integration test name")
    component_type: str = Field(description="System component being tested")
    integration_points: List[str] = Field(description="Integration points tested")
    test_configuration: Dict[str, Any] = Field(description="Test configuration")
    test_status: str = Field(description="Test execution status")
    test_results: Dict[str, Any] = Field(description="Test results")
    integration_success: bool = Field(description="Whether integration test passed")
    performance_impact: Optional[Dict[str, float]] = Field(None, description="Performance impact measurement")
    error_details: Optional[List[str]] = Field(None, description="Error details if failed")


class LoadTestConfiguration(BaseModel):
    """Load test configuration and parameters."""

    test_name: str = Field(description="Load test name")
    concurrent_users: int = Field(description="Number of concurrent users")
    concurrent_operations: int = Field(description="Number of concurrent operations")
    test_duration_seconds: int = Field(description="Test duration in seconds")
    target_throughput: float = Field(description="Target operations per second")
    resource_limits: Dict[str, float] = Field(description="Resource usage limits")
    dataset_configurations: List[Dict[str, Any]] = Field(description="Dataset configurations for load testing")


class LoadTestResult(BaseModel):
    """Load test execution results."""

    test_id: str = Field(description="Load test identifier")
    configuration: LoadTestConfiguration = Field(description="Test configuration used")
    execution_status: str = Field(description="Test execution status")
    actual_throughput: float = Field(description="Actual operations per second achieved")
    peak_memory_usage: float = Field(description="Peak memory usage during test")
    average_response_time: float = Field(description="Average response time in seconds")
    error_rate: float = Field(ge=0.0, le=1.0, description="Error rate during test")
    system_stability: bool = Field(description="Whether system remained stable")
    bottlenecks_identified: List[str] = Field(description="Identified performance bottlenecks")
    scalability_assessment: Dict[str, Any] = Field(description="Scalability assessment results")


class RegressionTestResult(BaseModel):
    """Regression test execution results."""

    test_id: str = Field(description="Regression test identifier")
    baseline_version: str = Field(description="Baseline version for comparison")
    current_version: str = Field(description="Current version being tested")
    regression_detected: bool = Field(description="Whether regression was detected")
    performance_comparison: Dict[str, Dict[str, float]] = Field(description="Performance comparison between versions")
    functionality_comparison: Dict[str, bool] = Field(description="Functionality comparison results")
    quality_score_change: float = Field(description="Quality score change")
    critical_regressions: List[str] = Field(description="Critical regressions identified")
    minor_regressions: List[str] = Field(description="Minor regressions identified")


class UserAcceptanceTest(BaseModel):
    """User acceptance test definition and results."""

    test_id: str = Field(description="User acceptance test identifier")
    acceptance_criteria: List[str] = Field(description="Acceptance criteria being tested")
    test_scenario: str = Field(description="Test scenario description")
    user_persona: str = Field(description="Target user persona")
    test_status: str = Field(description="Test execution status")
    criteria_results: Dict[str, bool] = Field(description="Results for each acceptance criteria")
    user_satisfaction_metrics: Dict[str, float] = Field(description="User satisfaction measurements")
    usability_score: float = Field(ge=0.0, le=1.0, description="Overall usability score")
    acceptance_passed: bool = Field(description="Whether acceptance test passed")
    feedback_notes: List[str] = Field(description="User feedback and notes")


class MonitoringAlert(BaseModel):
    """Monitoring system alert definition."""

    alert_id: str = Field(description="Alert identifier")
    alert_type: str = Field(description="Type of alert")
    severity: str = Field(description="Alert severity level")
    component: str = Field(description="Component that triggered alert")
    metric_name: str = Field(description="Metric that triggered alert")
    threshold_value: float = Field(description="Threshold value that was exceeded")
    actual_value: float = Field(description="Actual value that triggered alert")
    alert_message: str = Field(description="Alert message")
    timestamp: str = Field(description="Alert timestamp")
    resolved: bool = Field(default=False, description="Whether alert has been resolved")
    resolution_time: Optional[str] = Field(None, description="Alert resolution timestamp")


class DatasetOperationMonitoring(BaseModel):
    """Monitoring data for dataset operations."""

    operation_id: str = Field(description="Operation identifier")
    operation_type: str = Field(description="Type of dataset operation")
    dataset_type: str = Field(description="Dataset type being processed")
    start_time: str = Field(description="Operation start time")
    end_time: Optional[str] = Field(None, description="Operation end time")
    duration_seconds: Optional[float] = Field(None, description="Operation duration")
    memory_usage_mb: float = Field(description="Memory usage during operation")
    cpu_usage_percent: float = Field(description="CPU usage during operation")
    disk_usage_mb: float = Field(description="Disk usage during operation")
    network_io_mb: float = Field(description="Network I/O during operation")
    success: bool = Field(description="Whether operation succeeded")
    error_details: Optional[str] = Field(None, description="Error details if failed")
    performance_metrics: Optional[DatasetProcessingMetrics] = Field(None, description="Detailed performance metrics")


# Response models for API endpoints


class WorkflowListResponse(BaseModel):
    """Response model for listing workflows."""

    workflows: List[WorkflowExecutionStatusModel] = Field(description="List of workflows")
    total_count: int = Field(description="Total number of workflows")
    active_workflows: int = Field(description="Number of active workflows")
    completed_workflows: int = Field(description="Number of completed workflows")
    failed_workflows: int = Field(description="Number of failed workflows")


class PerformanceReportResponse(BaseModel):
    """Response model for performance reports."""

    report_id: str = Field(description="Performance report identifier")
    benchmarks: List[PerformanceBenchmark] = Field(description="Performance benchmarks")
    overall_performance_score: float = Field(ge=0.0, le=1.0, description="Overall performance score")
    performance_trends: Dict[str, List[float]] = Field(description="Performance trend data over time")
    recommendations: List[str] = Field(description="Performance improvement recommendations")
    generated_time: str = Field(description="Report generation timestamp")


class SystemHealthResponse(BaseModel):
    """Response model for system health status."""

    overall_health: str = Field(description="Overall system health status")
    component_health: Dict[str, str] = Field(description="Health status of each component")
    active_alerts: List[MonitoringAlert] = Field(description="Active monitoring alerts")
    performance_summary: Dict[str, float] = Field(description="Performance summary metrics")
    resource_usage: Dict[str, float] = Field(description="Current resource usage")
    uptime_seconds: float = Field(description="System uptime in seconds")
    last_health_check: str = Field(description="Last health check timestamp")


# Request validation models


class WorkflowValidationRequest(BaseModel):
    """Request model for workflow validation."""

    workflow_request: E2EWorkflowRequest = Field(description="Workflow request to validate")
    validation_level: str = Field(default="standard", description="Validation level (basic, standard, strict)")
    check_dependencies: bool = Field(default=True, description="Whether to check system dependencies")


class WorkflowValidationResponse(BaseModel):
    """Response model for workflow validation."""

    is_valid: bool = Field(description="Whether workflow request is valid")
    validation_errors: List[str] = Field(description="Validation errors found")
    validation_warnings: List[str] = Field(description="Validation warnings")
    estimated_resources: Dict[str, float] = Field(description="Estimated resource requirements")
    estimated_duration: float = Field(description="Estimated execution duration in seconds")
    compatibility_check: Dict[str, bool] = Field(description="System compatibility results")
    recommendations: List[str] = Field(description="Optimization recommendations")
