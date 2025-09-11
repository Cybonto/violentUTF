# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Partial Completion Handler Module

Handles partial workflow completion scenarios, allowing workflows to resume
from intermediate states and manage partial success conditions.

Key Components:
- PartialCompletionHandler: Core partial completion management
- WorkflowCheckpoint: Workflow state checkpoint management
- PartialResults: Partial result data structures
- ResumableWorkflow: Workflow resumption capabilities

SECURITY: All workflow data is for defensive security research only.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type


class CompletionStatus(Enum):
    """Workflow completion status levels"""

    NONE = "none"
    PARTIAL = "partial"
    SUBSTANTIAL = "substantial"
    COMPLETE = "complete"
    FAILED = "failed"


class CheckpointType(Enum):
    """Types of workflow checkpoints"""

    INITIALIZATION = "initialization"
    PRE_PROCESSING = "pre_processing"
    CONVERSION = "conversion"
    VALIDATION = "validation"
    POST_PROCESSING = "post_processing"
    COMPLETION = "completion"
    ERROR_STATE = "error_state"


@dataclass
class WorkflowCheckpoint:
    """Represents a workflow state checkpoint for resumption"""

    checkpoint_id: str
    workflow_id: str
    checkpoint_type: CheckpointType
    timestamp: datetime
    completion_percentage: float
    state_data: Dict[str, Any]
    results_partial: Dict[str, Any]
    next_steps: List[str]
    dependencies_completed: Set[str]
    dependencies_pending: Set[str]
    error_context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def completion_status(self) -> CompletionStatus:
        """Determine completion status from percentage"""
        if self.completion_percentage >= 100:
            return CompletionStatus.COMPLETE
        elif self.completion_percentage >= 75:
            return CompletionStatus.SUBSTANTIAL
        elif self.completion_percentage >= 25:
            return CompletionStatus.PARTIAL
        elif self.completion_percentage > 0:
            return CompletionStatus.PARTIAL
        else:
            return CompletionStatus.NONE

    def can_resume(self) -> bool:
        """Check if workflow can be resumed from this checkpoint"""
        return (
            self.checkpoint_type != CheckpointType.ERROR_STATE or self.error_context is not None
        ) and self.completion_percentage < 100

    def serialize(self) -> Dict[str, Any]:
        """Serialize checkpoint for storage"""
        return {
            "checkpoint_id": self.checkpoint_id,
            "workflow_id": self.workflow_id,
            "checkpoint_type": self.checkpoint_type.value,
            "timestamp": self.timestamp.isoformat(),
            "completion_percentage": self.completion_percentage,
            "state_data": self.state_data,
            "results_partial": self.results_partial,
            "next_steps": self.next_steps,
            "dependencies_completed": list(self.dependencies_completed),
            "dependencies_pending": list(self.dependencies_pending),
            "error_context": self.error_context,
            "metadata": self.metadata,
        }

    @classmethod
    def deserialize(cls: Type["WorkflowCheckpoint"], data: Dict[str, Any]) -> "WorkflowCheckpoint":
        """Deserialize checkpoint from storage"""
        return cls(
            checkpoint_id=data["checkpoint_id"],
            workflow_id=data["workflow_id"],
            checkpoint_type=CheckpointType(data["checkpoint_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            completion_percentage=data["completion_percentage"],
            state_data=data["state_data"],
            results_partial=data["results_partial"],
            next_steps=data["next_steps"],
            dependencies_completed=set(data["dependencies_completed"]),
            dependencies_pending=set(data["dependencies_pending"]),
            error_context=data.get("error_context"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class PartialResults:
    """Container for partial workflow results"""

    workflow_id: str
    results_data: Dict[str, Any]
    completion_percentage: float
    completed_tasks: List[str]
    pending_tasks: List[str]
    failed_tasks: List[str]
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_usable_results(self) -> bool:
        """Check if partial results are usable"""
        return len(self.completed_tasks) > 0 and self.completion_percentage >= 25.0 and len(self.results_data) > 0

    @property
    def quality_score(self) -> float:
        """Calculate quality score for partial results (0-100)"""
        base_score = self.completion_percentage

        # Penalty for failed tasks
        if self.failed_tasks:
            failure_penalty = min(20, len(self.failed_tasks) * 5)
            base_score -= failure_penalty

        # Penalty for errors
        if self.errors:
            error_penalty = min(15, len(self.errors) * 3)
            base_score -= error_penalty

        # Bonus for comprehensive results
        if len(self.results_data) > 10:
            base_score += 5

        return max(0, min(100, base_score))


class ResumableWorkflow:
    """Base class for workflows that support partial completion and resumption"""

    def __init__(self, workflow_id: str, workflow_type: str) -> None:
        """Initialize ResumableWorkflow.

        Args:
            workflow_id: Unique identifier for the workflow
            workflow_type: Type/category of the workflow
        """
        self.workflow_id = workflow_id
        self.workflow_type = workflow_type
        self.checkpoints: Dict[str, WorkflowCheckpoint] = {}
        self.current_checkpoint: Optional[WorkflowCheckpoint] = None
        self.completion_handlers: List[Callable[[PartialResults], None]] = []
        self.logger = logging.getLogger(__name__)

    def add_checkpoint(
        self,
        checkpoint_type: CheckpointType,
        completion_percentage: float,
        state_data: Dict[str, Any],
        results_partial: Optional[Dict[str, Any]] = None,
        next_steps: Optional[List[str]] = None,
    ) -> WorkflowCheckpoint:
        """Add a checkpoint to the workflow"""
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=str(uuid.uuid4()),
            workflow_id=self.workflow_id,
            checkpoint_type=checkpoint_type,
            timestamp=datetime.now(timezone.utc),
            completion_percentage=completion_percentage,
            state_data=state_data,
            results_partial=results_partial or {},
            next_steps=next_steps or [],
            dependencies_completed=set(),
            dependencies_pending=set(),
        )

        self.checkpoints[checkpoint.checkpoint_id] = checkpoint
        self.current_checkpoint = checkpoint
        return checkpoint

    def get_latest_checkpoint(self) -> Optional[WorkflowCheckpoint]:
        """Get the most recent checkpoint"""
        if not self.checkpoints:
            return None

        return max(self.checkpoints.values(), key=lambda c: c.timestamp)

    def get_resumable_checkpoint(self) -> Optional[WorkflowCheckpoint]:
        """Get the best checkpoint for resumption"""
        resumable_checkpoints = [checkpoint for checkpoint in self.checkpoints.values() if checkpoint.can_resume()]

        if not resumable_checkpoints:
            return None

        # Return checkpoint with highest completion percentage
        return max(resumable_checkpoints, key=lambda c: c.completion_percentage)

    def add_completion_handler(self, handler: Callable[[PartialResults], None]) -> None:
        """Add handler for partial completion events"""
        self.completion_handlers.append(handler)

    def trigger_completion_handlers(self, partial_results: PartialResults) -> None:
        """Trigger all registered completion handlers"""
        for handler in self.completion_handlers:
            try:
                handler(partial_results)
            except Exception as e:
                self.logger.error("Completion handler error: %s", e)


class PartialCompletionHandler:
    """
    Main handler for partial workflow completion scenarios

    Manages workflow checkpoints, partial results, and resumption capabilities
    for dataset conversion and evaluation workflows.
    """

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        """Initialize PartialCompletionHandler.

        Args:
            storage_path: Directory path for storing workflow checkpoints.
                         Defaults to './workflow_checkpoints'.
        """
        self.storage_path = storage_path or Path("./workflow_checkpoints")
        self.storage_path.mkdir(exist_ok=True)

        self.active_workflows: Dict[str, ResumableWorkflow] = {}
        self.checkpoint_store: Dict[str, WorkflowCheckpoint] = {}
        self.completion_thresholds = {"minimum_usable": 25.0, "substantial_completion": 75.0, "near_complete": 90.0}
        self.logger = logging.getLogger(__name__)

    async def handle_partial_completion(
        self,
        workflow_id: str,
        completed_tasks: List[str],
        pending_tasks: List[str],
        failed_tasks: List[str],
        results_data: Dict[str, Any],
        error_context: Optional[Dict[str, Any]] = None,
    ) -> PartialResults:
        """
        Handle partial workflow completion

        Args:
            workflow_id: Unique workflow identifier
            completed_tasks: List of successfully completed tasks
            pending_tasks: List of tasks still pending
            failed_tasks: List of tasks that failed
            results_data: Partial results data
            error_context: Context information about any errors

        Returns:
            PartialResults: Structured partial results
        """
        total_tasks = len(completed_tasks) + len(pending_tasks) + len(failed_tasks)
        completion_percentage = (len(completed_tasks) / total_tasks) * 100 if total_tasks > 0 else 0

        # Create partial results
        partial_results = PartialResults(
            workflow_id=workflow_id,
            results_data=results_data,
            completion_percentage=completion_percentage,
            completed_tasks=completed_tasks,
            pending_tasks=pending_tasks,
            failed_tasks=failed_tasks,
            errors=error_context.get("errors", []) if error_context else [],
            warnings=error_context.get("warnings", []) if error_context else [],
        )

        # Create checkpoint for resumption
        if workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            checkpoint_type = self._determine_checkpoint_type(completion_percentage, failed_tasks)

            checkpoint = workflow.add_checkpoint(
                checkpoint_type=checkpoint_type,
                completion_percentage=completion_percentage,
                state_data={
                    "completed_tasks": completed_tasks,
                    "pending_tasks": pending_tasks,
                    "failed_tasks": failed_tasks,
                },
                results_partial=results_data,
                next_steps=pending_tasks,
            )

            if error_context:
                checkpoint.error_context = error_context

            # Store checkpoint persistently
            await self._store_checkpoint(checkpoint)

            # Trigger completion handlers
            workflow.trigger_completion_handlers(partial_results)

        return partial_results

    def _determine_checkpoint_type(self, completion_percentage: float, failed_tasks: List[str]) -> CheckpointType:
        """Determine appropriate checkpoint type based on completion state"""
        if failed_tasks:
            return CheckpointType.ERROR_STATE
        elif completion_percentage >= 100:
            return CheckpointType.COMPLETION
        elif completion_percentage >= 75:
            return CheckpointType.POST_PROCESSING
        elif completion_percentage >= 50:
            return CheckpointType.VALIDATION
        elif completion_percentage >= 25:
            return CheckpointType.CONVERSION
        else:
            return CheckpointType.PRE_PROCESSING

    async def create_resumable_workflow(
        self, workflow_id: str, workflow_type: str, initial_state: Dict[str, Any]
    ) -> ResumableWorkflow:
        """Create a new resumable workflow"""
        workflow = ResumableWorkflow(workflow_id, workflow_type)

        # Add initial checkpoint
        workflow.add_checkpoint(
            checkpoint_type=CheckpointType.INITIALIZATION,
            completion_percentage=0.0,
            state_data=initial_state,
            next_steps=initial_state.get("planned_tasks", []),
        )

        self.active_workflows[workflow_id] = workflow
        return workflow

    async def resume_workflow(
        self, workflow_id: str, resume_checkpoint_id: Optional[str] = None
    ) -> Tuple[bool, Optional[WorkflowCheckpoint], List[str]]:
        """
        Resume a workflow from a checkpoint

        Returns:
            Tuple[bool, Optional[WorkflowCheckpoint], List[str]]:
            (success, checkpoint, remaining_tasks)
        """
        # Load workflow if not active
        if workflow_id not in self.active_workflows:
            success = await self._load_workflow_from_storage(workflow_id)
            if not success:
                return False, None, ["Workflow not found or could not be loaded"]

        workflow = self.active_workflows[workflow_id]

        # Determine which checkpoint to resume from
        if resume_checkpoint_id:
            checkpoint = workflow.checkpoints.get(resume_checkpoint_id)
        else:
            checkpoint = workflow.get_resumable_checkpoint()

        if not checkpoint:
            return False, None, ["No resumable checkpoint found"]

        if not checkpoint.can_resume():
            return False, checkpoint, ["Checkpoint is not resumable"]

        return True, checkpoint, checkpoint.next_steps

    async def validate_partial_completion_quality(
        self, partial_results: PartialResults, minimum_quality_score: float = 50.0
    ) -> Tuple[bool, Dict[str, Any]]:
        """Validate the quality of partial completion results"""
        quality_score = partial_results.quality_score
        quality_report = {
            "quality_score": quality_score,
            "meets_minimum": quality_score >= minimum_quality_score,
            "has_usable_results": partial_results.has_usable_results,
            "completion_percentage": partial_results.completion_percentage,
            "completed_tasks_count": len(partial_results.completed_tasks),
            "failed_tasks_count": len(partial_results.failed_tasks),
            "error_count": len(partial_results.errors),
            "warning_count": len(partial_results.warnings),
        }

        # Additional quality checks
        quality_issues = []
        if partial_results.completion_percentage < self.completion_thresholds["minimum_usable"]:
            quality_issues.append("Completion percentage below minimum usable threshold")

        if len(partial_results.failed_tasks) > len(partial_results.completed_tasks):
            quality_issues.append("More tasks failed than completed")

        if len(partial_results.errors) > 5:
            quality_issues.append("Excessive error count")

        quality_report["quality_issues"] = quality_issues
        quality_report["is_acceptable"] = len(quality_issues) == 0 and quality_score >= minimum_quality_score

        return quality_report["is_acceptable"], quality_report

    async def cleanup_completed_workflows(self, max_age_hours: int = 24) -> int:
        """Clean up completed workflows older than specified age"""
        cleanup_count = 0
        current_time = datetime.now(timezone.utc)

        workflows_to_remove = []
        for workflow_id, workflow in self.active_workflows.items():
            latest_checkpoint = workflow.get_latest_checkpoint()
            if not latest_checkpoint:
                continue

            age_hours = (current_time - latest_checkpoint.timestamp).total_seconds() / 3600
            if age_hours > max_age_hours and latest_checkpoint.checkpoint_type == CheckpointType.COMPLETION:
                workflows_to_remove.append(workflow_id)
                cleanup_count += 1

        # Remove workflows and their storage
        for workflow_id in workflows_to_remove:
            await self._remove_workflow_storage(workflow_id)
            del self.active_workflows[workflow_id]

        return cleanup_count

    async def _store_checkpoint(self, checkpoint: WorkflowCheckpoint) -> None:
        """Store checkpoint persistently"""
        checkpoint_file = self.storage_path / f"{checkpoint.workflow_id}_{checkpoint.checkpoint_id}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint.serialize(), f, indent=2)

    async def _load_workflow_from_storage(self, workflow_id: str) -> bool:
        """Load workflow from persistent storage"""
        try:
            checkpoint_files = list(self.storage_path.glob(f"{workflow_id}_*.json"))
            if not checkpoint_files:
                return False

            # Create workflow and load checkpoints
            workflow = ResumableWorkflow(workflow_id, "loaded_from_storage")

            for checkpoint_file in checkpoint_files:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    checkpoint_data = json.load(f)
                    checkpoint = WorkflowCheckpoint.deserialize(checkpoint_data)
                    workflow.checkpoints[checkpoint.checkpoint_id] = checkpoint

            self.active_workflows[workflow_id] = workflow
            return True

        except Exception as e:
            self.logger.error("Error loading workflow %s: %s", workflow_id, e)
            return False

    async def _remove_workflow_storage(self, workflow_id: str) -> None:
        """Remove all storage files for a workflow"""
        checkpoint_files = list(self.storage_path.glob(f"{workflow_id}_*.json"))
        for checkpoint_file in checkpoint_files:
            checkpoint_file.unlink()

    def get_partial_completion_summary(self) -> Dict[str, Any]:
        """Get summary of partial completion handling status"""
        active_count = len(self.active_workflows)
        total_checkpoints = sum(len(w.checkpoints) for w in self.active_workflows.values())

        completion_stats = {"none": 0, "partial": 0, "substantial": 0, "complete": 0, "failed": 0}

        for workflow in self.active_workflows.values():
            latest_checkpoint = workflow.get_latest_checkpoint()
            if latest_checkpoint:
                completion_stats[latest_checkpoint.completion_status.value] += 1

        return {
            "active_workflows": active_count,
            "total_checkpoints": total_checkpoints,
            "completion_distribution": completion_stats,
            "storage_path": str(self.storage_path),
            "completion_thresholds": self.completion_thresholds,
        }
