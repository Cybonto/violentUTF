# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.

"""
Integration module for end-to-end workflow management.

This module provides integration components for complete dataset
workflow orchestration across all supported dataset types.
"""

from .e2e_workflow_manager import (
    DatasetProcessingMetrics,
    E2EWorkflowRequest,
    E2EWorkflowResult,
    EndToEndWorkflowManager,
    WorkflowExecutionError,
    WorkflowExecutionStatus,
    WorkflowValidationError,
)
from .performance_monitor import (
    APIPerformanceMetrics,
    ConcurrentOperationManager,
    DatasetPerformanceMonitor,
    PerformanceBenchmark,
    SystemResourceMetrics,
)
from .user_scenario_manager import (
    UserAcceptanceTestManager,
    UserPersonaConfig,
    UserScenarioExecution,
    UserScenarioManager,
)

__all__ = [
    "EndToEndWorkflowManager",
    "WorkflowExecutionError",
    "WorkflowValidationError",
    "E2EWorkflowRequest",
    "E2EWorkflowResult",
    "WorkflowExecutionStatus",
    "DatasetProcessingMetrics",
    "UserScenarioManager",
    "UserAcceptanceTestManager",
    "UserPersonaConfig",
    "UserScenarioExecution",
    "DatasetPerformanceMonitor",
    "ConcurrentOperationManager",
    "PerformanceBenchmark",
    "SystemResourceMetrics",
    "APIPerformanceMetrics",
]
