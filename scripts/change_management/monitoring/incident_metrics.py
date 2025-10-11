# Copyright (c) 2025 ViolentUTF Contributors.
# Licensed under the MIT License.
#
# This file is part of ViolentUTF - An AI Red Teaming Platform.
# See LICENSE file in the project root for license information.

"""
Incident Metrics Collection.

Collects and tracks metrics for incident response.
"""

from datetime import datetime
from typing import Any, Dict


class IncidentMetrics:
    """Collects incident response metrics."""

    def __init__(self) -> None:
        """Initialize incident metrics collector."""
        self.incidents: Dict[str, Dict[str, Any]] = {}

    def record_incident_start(self, incident_id: str) -> None:
        """Record incident start time."""
        self.incidents[incident_id] = {
            "incident_id": incident_id,
            "started_at": datetime.utcnow(),
            "resolved_at": None,
        }

    def record_incident_resolution(self, incident_id: str) -> None:
        """Record incident resolution time."""
        if incident_id in self.incidents:
            self.incidents[incident_id]["resolved_at"] = datetime.utcnow()

    def get_incident_metrics(self, incident_id: str) -> Dict[str, Any]:
        """
        Get metrics for incident.

        Args:
            incident_id: Incident ID

        Returns:
            Incident metrics including MTTR
        """
        if incident_id not in self.incidents:
            return {}

        incident = self.incidents[incident_id]

        # Calculate MTTR if resolved
        mttr = None
        if incident["resolved_at"]:
            duration = incident["resolved_at"] - incident["started_at"]
            mttr = duration.total_seconds() / 60  # Minutes

        return {
            "incident_id": incident_id,
            "started_at": incident["started_at"].isoformat(),
            "resolved_at": incident["resolved_at"].isoformat() if incident["resolved_at"] else None,
            "mttr": mttr,
        }
