# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Change Metrics Collection.

Collects and tracks metrics for change management processes.
"""

from datetime import datetime
from typing import Any, Dict


class ChangeMetrics:
    """Collects change management metrics."""

    def __init__(self) -> None:
        """Initialize change metrics collector."""
        self.metrics: Dict[str, Dict[str, Any]] = {}

    def collect_change_metrics(self, request_id: str) -> Dict[str, Any]:
        """
        Collect metrics for change request.

        Args:
            request_id: Change request ID

        Returns:
            Metrics data
        """
        if request_id not in self.metrics:
            self.metrics[request_id] = {
                "request_id": request_id,
                "created_at": datetime.utcnow().isoformat(),
                "approval_time": 0,
                "change_type": "unknown",
                "status": "pending",
            }

        return self.metrics[request_id]

    def record_approval_time(self, request_id: str, approval_time_minutes: float) -> None:
        """Record approval time for change request."""
        if request_id not in self.metrics:
            self.metrics[request_id] = {}

        self.metrics[request_id]["approval_time"] = approval_time_minutes
