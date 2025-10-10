# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""GraphWalk Service Layer (Issue #128).

Provides business logic integration for GraphWalk dataset conversion with massive file handling,
async job management, and progress tracking. Follows the established service layer pattern
consistent with other dataset converters.

SECURITY: All processing includes proper validation for defensive security research.
"""
import asyncio
import logging
import os
import uuid
from typing import Any, Dict, Optional

from app.core.converters.graphwalk_converter import GraphWalkConverter
from app.schemas.graphwalk_datasets import (
    GraphWalkConversionConfig,
    QuestionAnsweringDataset,
)


class GraphWalkService:
    """Service for GraphWalk dataset conversion with async job management."""

    def __init__(self) -> None:
        """Initialize GraphWalk service."""
        self.logger = logging.getLogger(__name__)
        self._active_jobs: Dict[str, Dict[str, Any]] = {}

    async def convert_dataset_async(
        self, file_path: str, config: Optional[GraphWalkConversionConfig] = None, job_id: Optional[str] = None
    ) -> str:
        """Start async conversion job for GraphWalk dataset.

        Args:
            file_path: Path to GraphWalk dataset file
            config: Optional conversion configuration
            job_id: Optional job ID, generated if not provided

        Returns:
            Job ID for tracking conversion progress
        """
        if not job_id:
            job_id = str(uuid.uuid4())

        self.logger.info("Starting async GraphWalk conversion job %s for %s", job_id, file_path)

        # Initialize job tracking
        self._active_jobs[job_id] = {
            "status": "started",
            "progress": 0.0,
            "file_path": file_path,
            "config": config,
            "result": None,
            "error": None,
            "created_at": asyncio.get_event_loop().time(),
            "updated_at": asyncio.get_event_loop().time(),
        }

        # Start conversion task
        asyncio.create_task(self._run_conversion_job(job_id, file_path, config))

        return job_id

    async def _run_conversion_job(
        self, job_id: str, file_path: str, config: Optional[GraphWalkConversionConfig]
    ) -> None:
        """Run the actual conversion job with progress tracking.

        Args:
            job_id: Job identifier
            file_path: Path to file to convert
            config: Conversion configuration
        """
        try:
            # Update job status
            self._update_job_status(job_id, "running", 0.1)

            # Initialize converter
            converter = GraphWalkConverter(config)

            # Check file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Dataset file not found: {file_path}")

            self._update_job_status(job_id, "analyzing", 0.2)

            # Analyze file to determine processing strategy
            file_info = converter.analyze_massive_file(file_path)
            self.logger.info(
                "Job %s: File analysis complete - %.1fMB, strategy: %s",
                job_id,
                file_info.size_mb,
                file_info.processing_strategy,
            )

            self._update_job_status(job_id, "converting", 0.3)

            # Run conversion with progress callbacks
            result = await self._run_conversion_with_progress(converter, file_path, job_id)

            # Job completed successfully
            self._active_jobs[job_id].update(
                {
                    "status": "completed",
                    "progress": 1.0,
                    "result": result,
                    "updated_at": asyncio.get_event_loop().time(),
                }
            )

            self.logger.info("Job %s completed successfully - %s questions converted", job_id, len(result.questions))

        except Exception as e:
            # Job failed
            self.logger.error("Job %s failed: %s", job_id, e)
            self._active_jobs[job_id].update(
                {"status": "failed", "error": str(e), "updated_at": asyncio.get_event_loop().time()}
            )

    async def _run_conversion_with_progress(
        self, converter: GraphWalkConverter, file_path: str, job_id: str
    ) -> QuestionAnsweringDataset:
        """Run conversion in thread pool with progress updates.

        Args:
            converter: GraphWalk converter instance
            file_path: Path to file
            job_id: Job ID for progress tracking

        Returns:
            Converted QuestionAnsweringDataset
        """
        loop = asyncio.get_event_loop()

        # Set up periodic progress updates for long-running jobs
        async def update_progress_periodically() -> None:
            base_progress = 0.3
            while self._active_jobs.get(job_id, {}).get("status") == "converting":
                current_progress = self._active_jobs.get(job_id, {}).get("progress", base_progress)
                if current_progress < 0.8:  # Don't exceed 80% until actually done
                    new_progress = min(current_progress + 0.05, 0.8)
                    self._update_job_status(job_id, "converting", new_progress)
                await asyncio.sleep(5)  # Update every 5 seconds

        # Start periodic updates
        progress_task = asyncio.create_task(update_progress_periodically())

        try:
            # Run conversion in thread pool to avoid blocking
            result = await loop.run_in_executor(None, converter.convert, file_path)

            # Cancel progress updates
            progress_task.cancel()

            # Final progress update
            self._update_job_status(job_id, "finalizing", 0.9)

            return result

        except Exception as e:
            progress_task.cancel()
            raise e

    def _update_job_status(
        self, job_id: str, status: str, progress: float, additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update job status and progress.

        Args:
            job_id: Job identifier
            status: New status
            progress: Progress value (0.0-1.0)
            additional_data: Optional additional data to store
        """
        if job_id in self._active_jobs:
            self._active_jobs[job_id].update(
                {"status": status, "progress": progress, "updated_at": asyncio.get_event_loop().time()}
            )

            if additional_data:
                self._active_jobs[job_id].update(additional_data)

            self.logger.debug("Job %s: %s (%.1f%%)", job_id, status, progress * 100)

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current job status and progress.

        Args:
            job_id: Job identifier

        Returns:
            Job status dictionary or None if not found
        """
        return self._active_jobs.get(job_id)

    def get_job_result(self, job_id: str) -> Optional[QuestionAnsweringDataset]:
        """Get job result if completed.

        Args:
            job_id: Job identifier

        Returns:
            Conversion result or None if not completed
        """
        job_data = self._active_jobs.get(job_id)
        if job_data and job_data.get("status") == "completed":
            return job_data.get("result")
        return None

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.

        Args:
            job_id: Job identifier

        Returns:
            True if job was cancelled, False if not found or not cancellable
        """
        if job_id in self._active_jobs:
            job_status = self._active_jobs[job_id].get("status")
            if job_status in ["started", "running", "analyzing", "converting"]:
                self._active_jobs[job_id].update({"status": "cancelled", "updated_at": asyncio.get_event_loop().time()})
                self.logger.info("Job %s cancelled", job_id)
                return True
        return False

    def cleanup_completed_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed jobs.

        Args:
            max_age_hours: Maximum age in hours for job retention

        Returns:
            Number of jobs cleaned up
        """
        current_time = asyncio.get_event_loop().time()
        max_age_seconds = max_age_hours * 3600

        jobs_to_remove = []
        for job_id, job_data in self._active_jobs.items():
            age = current_time - job_data.get("created_at", current_time)
            status = job_data.get("status")

            if age > max_age_seconds and status in ["completed", "failed", "cancelled"]:
                jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self._active_jobs[job_id]

        if jobs_to_remove:
            self.logger.info("Cleaned up %s old jobs", len(jobs_to_remove))

        return len(jobs_to_remove)

    def list_active_jobs(self) -> Dict[str, Dict[str, Any]]:
        """List all active jobs.

        Returns:
            Dictionary of job IDs to job status
        """
        return {
            job_id: {
                "status": job_data.get("status"),
                "progress": job_data.get("progress"),
                "file_path": job_data.get("file_path"),
                "created_at": job_data.get("created_at"),
                "updated_at": job_data.get("updated_at"),
            }
            for job_id, job_data in self._active_jobs.items()
        }

    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get service processing statistics.

        Returns:
            Dictionary with processing statistics
        """
        total_jobs = len(self._active_jobs)
        completed_jobs = sum(1 for job in self._active_jobs.values() if job.get("status") == "completed")
        failed_jobs = sum(1 for job in self._active_jobs.values() if job.get("status") == "failed")
        active_jobs = sum(
            1
            for job in self._active_jobs.values()
            if job.get("status") in ["started", "running", "analyzing", "converting"]
        )

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "active_jobs": active_jobs,
            "success_rate": completed_jobs / total_jobs if total_jobs > 0 else 0.0,
        }


# Global service instance
graphwalk_service = GraphWalkService()


# Export for convenient importing
__all__ = [
    "GraphWalkService",
    "graphwalk_service",
]
